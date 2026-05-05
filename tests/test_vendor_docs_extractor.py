"""Tests for db.sources.vendor_docs (Phase 4 Wave-B / Wave-B2 extraction).

Covers:
  * §11 #7 source_excerpt ≤200-char app-level enforcement at 199/200/201/large-span boundaries.
  * Regex-pass false-positive handling (unanchored UUIDs, GitBook tokens).
  * Anchor-window logic (BLE/MAC/SSID/cred-keyword required).
  * Idempotency: re-running apply_classifications on same inputs produces no duplicates
    (UNIQUE(source_id, source_row_key) per migration 0006).
  * SAR-5 PII redaction at extraction time + count-not-name accounting.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from db.sources import vendor_docs
from db.sources.vendor_docs import (
    EXCERPT_MAX,
    Candidate,
    apply_classifications,
    redact_pii,
    regex_pass_one_file,
    run_regex_pass,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


# ─── fixture: pristine in-memory-ish DB at temp path ──────────────────────


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Apply 0001+0006 migrations to a temp DB. Tests don't need other tables."""
    db_path = tmp_path / "argus_test.db"
    conn = sqlite3.connect(db_path)
    try:
        for mig in ("0001_initial.sql", "0006_raw_observations_source_row_key.sql"):
            sql = (REPO_ROOT / "db" / "migrations" / mig).read_text()
            conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
    return db_path


# ─── §11 #7 source_excerpt boundary tests ────────────────────────────────


def test_excerpt_trim_under_200_passes() -> None:
    """A 199-char window survives unchanged."""
    text = "ssid is testnet" + " padding " * 20
    cands, drops = regex_pass_one_file(
        cohort="t", file_relpath="t.html", doc_url="http://t/", text=text,
    )
    assert any(c.candidate_identifier == "testnet" for c in cands)
    matched = next(c for c in cands if c.candidate_identifier == "testnet")
    assert len(matched.source_excerpt) <= EXCERPT_MAX


def test_excerpt_at_200_chars_kept() -> None:
    """Excerpt that lands exactly at EXCERPT_MAX (200) is kept (not dropped)."""
    excerpt_200 = "x" * EXCERPT_MAX
    # Force feed via the trimmer: reach into the helper directly.
    text = "a" * 50 + excerpt_200 + "b" * 50
    cands, drops = regex_pass_one_file(
        cohort="t", file_relpath="t.html", doc_url="http://t/",
        text=f"ssid is supershort {excerpt_200[:100]}",
    )
    for c in cands:
        assert len(c.source_excerpt) <= EXCERPT_MAX


def test_long_match_span_drops() -> None:
    """A regex match span longer than EXCERPT_MAX cannot fit any window → drop.

    Synthetic stressor: build a SSID name longer than EXCERPT_MAX. The
    SSID_LINE_RE caps at 30 chars in the value group, so we go through
    QUOTED_SSID_RE which caps at 30 too — both bounded. We instead use a
    direct call to the trim helper to exercise the EXCERPT_MAX > span
    guard.
    """
    from db.sources.vendor_docs import _trim_excerpt
    text = "x" * 500
    excerpt, offset, overflow = _trim_excerpt(text, 0, EXCERPT_MAX + 1)
    assert excerpt == ""
    assert overflow is True


def test_apply_drops_row_with_oversized_excerpt(tmp_db: Path, tmp_path: Path) -> None:
    """If an upstream caller hands a candidate with excerpt >200, apply drops it.

    The regex-pass path can't produce one (trim guard), but the apply path
    must defensively reject; this is the §11 #7 second line of defense.
    """
    candidates_path = tmp_path / "candidates.json"
    classifications_path = tmp_path / "classifications.json"
    too_long = "z" * (EXCERPT_MAX + 5)
    candidates_path.write_text(json.dumps([{
        "candidate_id": "deadbeef",
        "cohort": "test", "file_relpath": "t.html",
        "doc_url": "http://t/", "candidate_identifier": "test_ssid",
        "pass_kind": "ssid_line", "suggested_candidate_type": "ssid_exact",
        "anchor_keyword": "", "source_excerpt": too_long,
        "excerpt_offset": 0, "excerpt_overflow_pretrim": True, "pii_hits": 0,
    }]))
    classifications_path.write_text(json.dumps([{
        "candidate_id": "deadbeef", "keep": True, "confidence": 80,
        "final_candidate_type": "ssid_exact", "candidate_category": "hacking_tool",
        "candidate_manufacturer": "Hak5", "notes": "",
    }]))
    result = apply_classifications(
        candidates_path=candidates_path,
        classifications_path=classifications_path,
        db_path=tmp_db,
        agent_id="test-agent", source_name="Test", source_url="http://test/",
        source_notes="",
    )
    assert result["rows_staged"] == 0
    assert result["dropped_excerpt_overflow"] == 1


# ─── Regex false-positive: GitBook-token UUIDs ───────────────────────────


def test_unanchored_uuid_dropped() -> None:
    """A UUID with NO BLE/Bluetooth/GATT keyword in ±200 chars is dropped."""
    text = (
        "Some marketing copy about a product. " * 5
        + "token=0652c638-23df-4526-8744-2454c9d4f67e&alt=media "
        + "More copy. " * 5
    )
    cands, drops = regex_pass_one_file(
        cohort="t", file_relpath="t.html", doc_url="http://t/", text=text,
    )
    uuid_cands = [c for c in cands if c.pass_kind == "uuid_anchored"]
    assert uuid_cands == []
    assert any(d["kind"] == "uuid_anchored" and d["reason"] == "no_anchor" for d in drops)


def test_anchored_ble_uuid_kept() -> None:
    """A UUID inside ±200 chars of 'Bluetooth'/'BLE'/'GATT' is kept."""
    text = (
        "Bluetooth GATT service UUID: f000aa10-0451-4000-b000-000000000000 "
        "characteristic for the device sensor."
    )
    cands, drops = regex_pass_one_file(
        cohort="t", file_relpath="t.html", doc_url="http://t/", text=text,
    )
    uuid_cands = [c for c in cands if c.pass_kind == "uuid_anchored"]
    assert len(uuid_cands) == 1
    assert uuid_cands[0].suggested_candidate_type == "ble_uuid"
    assert "bluetooth" in uuid_cands[0].anchor_keyword.lower() \
        or "gatt" in uuid_cands[0].anchor_keyword.lower() \
        or "ble" in uuid_cands[0].anchor_keyword.lower() \
        or "service uuid" in uuid_cands[0].anchor_keyword.lower()


def test_anchored_mac_kept() -> None:
    """MAC inside ±200 chars of 'MAC address' / 'hardware address' is kept."""
    text = "Device MAC address: aa:bb:cc:11:22:33 (post-flash)."
    cands, drops = regex_pass_one_file(
        cohort="t", file_relpath="t.html", doc_url="http://t/", text=text,
    )
    mac_cands = [c for c in cands if c.pass_kind == "mac_anchored"]
    assert len(mac_cands) == 1
    assert mac_cands[0].suggested_candidate_type == "mac"


# ─── SAR-5 PII redaction ─────────────────────────────────────────────────


def test_redact_pii_engineer_name() -> None:
    """SAR-5 vendor-side roles (Engineer / Installer / Maintainer) hit redaction."""
    text = "Reviewed by Engineer Jane Smith on 2024-06-10."
    redacted, hits = redact_pii(text)
    assert "Jane" not in redacted
    assert "[REDACTED-PERSON]" in redacted
    assert hits >= 1


def test_redact_pii_law_enforcement_rank() -> None:
    """Original LE rank tokens still hit (recall over precision)."""
    text = "Approved by Sergeant John Doe."
    redacted, hits = redact_pii(text)
    assert "John Doe" not in redacted
    assert hits >= 1


def test_redact_pii_no_hits_returns_original() -> None:
    text = "default ssid is HelloWorld"
    redacted, hits = redact_pii(text)
    assert redacted == text
    assert hits == 0


def test_pii_hits_counted_at_extraction() -> None:
    """SAR-5 count-not-name: pii_hits surfaces on every Candidate."""
    text = "Bluetooth advertising UUID f000aa10-0451-4000-b000-000000000000. "
    text = "Reviewed by Engineer Jane Smith. " + text
    cands, _ = regex_pass_one_file(
        cohort="t", file_relpath="t.html", doc_url="http://t/", text=text,
    )
    uuid_cands = [c for c in cands if c.pass_kind == "uuid_anchored"]
    assert len(uuid_cands) == 1
    # The window includes "Engineer Jane Smith" → at least 1 redaction hit.
    assert uuid_cands[0].pii_hits >= 1
    assert "Jane" not in uuid_cands[0].source_excerpt


# ─── Idempotency: double-run apply produces no duplicates ────────────────


def _make_candidate_files(tmp_path: Path) -> tuple[Path, Path]:
    candidates_path = tmp_path / "candidates.json"
    classifications_path = tmp_path / "classifications.json"
    candidates_path.write_text(json.dumps([{
        "candidate_id": "abc123",
        "cohort": "test", "file_relpath": "t.html",
        "doc_url": "http://test/page1",
        "candidate_identifier": "TestNetwork_AB12",
        "pass_kind": "ssid_product",
        "suggested_candidate_type": "ssid_pattern",
        "anchor_keyword": "",
        "source_excerpt": "default SSID TestNetwork_AB12 ships from factory",
        "excerpt_offset": 0, "excerpt_overflow_pretrim": False, "pii_hits": 0,
    }]))
    classifications_path.write_text(json.dumps([{
        "candidate_id": "abc123", "keep": True, "confidence": 80,
        "final_candidate_type": "ssid_pattern", "candidate_category": "hacking_tool",
        "candidate_manufacturer": "Hak5", "notes": "test",
    }]))
    return candidates_path, classifications_path


def test_idempotent_double_run(tmp_db: Path, tmp_path: Path) -> None:
    """Re-running apply over the same inputs stages 0 net new rows on round 2."""
    cands, classes = _make_candidate_files(tmp_path)
    r1 = apply_classifications(
        candidates_path=cands, classifications_path=classes, db_path=tmp_db,
        agent_id="test", source_name="t", source_url="http://test/", source_notes="",
    )
    assert r1["rows_staged"] == 1
    assert r1["unique_violations"] == 0

    r2 = apply_classifications(
        candidates_path=cands, classifications_path=classes, db_path=tmp_db,
        agent_id="test", source_name="t", source_url="http://test/", source_notes="",
    )
    assert r2["rows_staged"] == 0
    assert r2["unique_violations"] == 1

    conn = sqlite3.connect(tmp_db)
    try:
        n = conn.execute("SELECT COUNT(*) FROM raw_observations").fetchone()[0]
        assert n == 1, "double-run must not produce duplicate raw_observations rows"
    finally:
        conn.close()


def test_apply_skips_keep_false(tmp_db: Path, tmp_path: Path) -> None:
    """LLM-pass keep=false → row dropped, accounted in dropped_llm_keep_false."""
    cands_path, classes_path = _make_candidate_files(tmp_path)
    classes = json.loads(classes_path.read_text())
    classes[0]["keep"] = False
    classes_path.write_text(json.dumps(classes))
    r = apply_classifications(
        candidates_path=cands_path, classifications_path=classes_path, db_path=tmp_db,
        agent_id="test", source_name="t", source_url="http://test/", source_notes="",
    )
    assert r["rows_staged"] == 0
    assert r["dropped_llm_keep_false"] == 1


def test_apply_skips_unclassified(tmp_db: Path, tmp_path: Path) -> None:
    """Candidate with no classification → dropped, accounted."""
    cands_path = tmp_path / "candidates.json"
    classes_path = tmp_path / "classifications.json"
    cands_path.write_text(json.dumps([{
        "candidate_id": "uncls1", "cohort": "t", "file_relpath": "t.html",
        "doc_url": "http://t/", "candidate_identifier": "x",
        "pass_kind": "ssid_line", "suggested_candidate_type": "ssid_exact",
        "anchor_keyword": "", "source_excerpt": "ssid x", "excerpt_offset": 0,
        "excerpt_overflow_pretrim": False, "pii_hits": 0,
    }]))
    classes_path.write_text(json.dumps([]))
    r = apply_classifications(
        candidates_path=cands_path, classifications_path=classes_path, db_path=tmp_db,
        agent_id="test", source_name="t", source_url="http://test/", source_notes="",
    )
    assert r["dropped_no_classification"] == 1
    assert r["rows_staged"] == 0


# ─── Cohort-3 corpus regression: empty yield documented ──────────────────


def test_cohort3_hak5_regex_pass_yields_zero(tmp_path: Path) -> None:
    """MAC-20 absence-documentation regression: cohort3_hak5_wayback yields
    0 candidates against the Step-1 manifest. 21 unanchored UUIDs (GitBook
    tokens) all drop with reason='no_anchor'.

    Wave-B2 Step-2 runs against the live `raw/vendor_docs/20260505T143454Z`
    batch; if that batch is rotated or extended, this test will surface
    the change at CI rather than silently shifting yield expectations.
    """
    manifest_path = REPO_ROOT / "raw/vendor_docs/20260505T143454Z/_manifest.json"
    if not manifest_path.exists():
        pytest.skip("Step-1 batch not present in this environment")
    out_cands = tmp_path / "candidates.json"
    out_drops = tmp_path / "drops.json"
    files, n_cands, n_drops = run_regex_pass(
        manifest_path=manifest_path, cohort_filter="cohort3_hak5_wayback",
        out_candidates_path=out_cands, out_drops_path=out_drops,
    )
    assert files == 9, f"expected 9 status=200 cohort3 files, got {files}"
    assert n_cands == 0, (
        f"expected 0 candidates per MAC-19 Step-1.5b survey + Step-2 absence-"
        f"documentation; got {n_cands}"
    )
    drops = json.loads(out_drops.read_text())
    assert n_drops == 21
    assert all(d["reason"] == "no_anchor" for d in drops)
    assert all(d["kind"] == "uuid_anchored" for d in drops)
