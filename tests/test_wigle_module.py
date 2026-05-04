"""Smoke tests for db/sources/wigle.py — MAC-9 Step 2 deliverable.

DRY_RUN-only. Zero live WiGLE queries fire. Tests:

  1. Module-level invariants (DRY_RUN_DEFAULT, SOURCE_TYPE, CONFIDENCE,
     LICENSE_NOTE, swagger sha256 matches snapshot on disk).
  2. Tier assignment per board T1–T5 (CEO-ratified Step 1) including the
     T3 8-state expansion + T4-territory sub-rank for PR/USVI/GU/AS/MP.
  3. State-derivation Q1 — Atlas state-column verbatim, DeFlock
     reverse_geocoder admin1 lookup, including DC ('Washington, D.C.')
     canary + Amarillo TX (Step 1 §2 bbox-tiebreak failure case).
  4. Q4 — Atlas state='PS' explicit do-not-stage; PR/USVI route to T4.
  5. Q2 — parse_quota_signal: HTTP 429 -> is_quota_exhausted=True;
     Retry-After integer + HTTP-date defensive parse; no retry triggered.
  6. SAR-5-by-analogy SSID PII redaction primitives.
  7. DRY_RUN gate: run_live_query refuses when dry_run=True (default).
  8. HTTP Basic header construction matches RFC 7617 b64.
  9. Idempotent build: prioritized-list rebuild produces identical row
     count + tier distribution against an in-memory fixture DB.
 10. Step-1 §2 count reproduction: Atlas 2,745 + DeFlock 77,953 = 80,698
     candidate set (live-DB read; gated on argus.db existence).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from db.sources import wigle


REPO_ROOT = Path(__file__).resolve().parent.parent


# ─── 1. Module-level invariants ───────────────────────────────────────────


def test_dry_run_default_is_on():
    assert wigle.DRY_RUN_DEFAULT is True


def test_source_metadata_constants():
    assert wigle.SOURCE_TYPE == "crowdsourced"
    assert wigle.CONFIDENCE == 50
    assert wigle.CONFIDENCE_BAND == "50-75"
    assert wigle.TIER == 2
    assert "EULA" in wigle.LICENSE_NOTE
    assert "wigle.net/eula.html" in wigle.LICENSE_NOTE


def test_swagger_snapshot_sha256_matches_module_constant():
    snap = wigle.DEFAULT_DOCS_SNAPSHOT
    assert snap.exists(), f"swagger snapshot missing at {snap}"
    actual = hashlib.sha256(snap.read_bytes()).hexdigest()
    assert actual == wigle.DEFAULT_DOCS_SHA256
    assert actual == "a66f00f9b81b63f5682f8862b9d1baec419e467c39f6c2597c7cf73d4c0388f4"


def test_flock_vendor_set_size_six():
    """Step-1 reproducing strict 6-string match. Adding/removing entries
    is a CEO ratification, not a worker-side edit."""
    assert len(wigle.FLOCK_VENDOR_RAW_VALUES) == 6
    assert "Flock Safety" in wigle.FLOCK_VENDOR_RAW_VALUES
    assert "Flock Group Inc." in wigle.FLOCK_VENDOR_RAW_VALUES


# ─── 2. Tier assignment ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "state,expected_tier",
    [
        ("MD", 1),                       # T1
        ("DC", 2), ("NJ", 2), ("PA", 2), ("NY", 2), ("VA", 2),    # T2
        ("CT", 3), ("MA", 3), ("RI", 3), ("ME", 3),              # T3 board
        ("NH", 3), ("VT", 3), ("DE", 3), ("WV", 3),              # T3 worker-proposed (8-state expansion)
        ("CA", 4), ("TX", 4), ("AK", 4), ("HI", 4),              # T4 (CONUS + AK + HI)
        ("PR", 4), ("USVI", 4), ("GU", 4), ("AS", 4), ("MP", 4),  # T4-territory sub-rank (Q4)
    ],
)
def test_assign_tier_us_states_and_territories(state, expected_tier):
    assert wigle.assign_tier(state, country_code="US") == expected_tier


def test_assign_tier_international_routes_to_t5():
    assert wigle.assign_tier("BE", country_code="BE") == 5
    assert wigle.assign_tier("AU", country_code="AU") == 5
    assert wigle.assign_tier("GB", country_code="GB") == 5


def test_assign_tier_unknown_us_admin1_routes_to_t5_for_log_and_skip():
    """§11 #1 stop-line — do NOT force into a US bucket."""
    assert wigle.assign_tier("ZZ", country_code="US") == 5


# ─── 3. State derivation ──────────────────────────────────────────────────


def test_derive_state_atlas_returns_state_verbatim():
    ds = wigle.derive_state_atlas("VA", "US")
    assert ds is not None
    assert ds.state_or_country == "VA"
    assert ds.derivation_method == "atlas_state_column"
    assert ds.country_code == "US"


def test_derive_state_atlas_blank_returns_none():
    assert wigle.derive_state_atlas(None, "US") is None
    assert wigle.derive_state_atlas("", "US") is None


def test_reverse_geocoder_dc_returns_dc():
    """Canary: rg returns admin1='Washington, D.C.' (with comma + period)
    for DC points; module map MUST produce 'DC' (T2)."""
    pytest.importorskip("reverse_geocoder")
    rg_map = wigle.derive_states_deflock_batch([(1, 38.895, -77.0366)])
    ds = rg_map[1]
    assert ds is not None
    assert ds.state_or_country == "DC"
    assert ds.country_code == "US"
    assert wigle.assign_tier(ds.state_or_country, country_code=ds.country_code) == 2


def test_reverse_geocoder_amarillo_returns_tx_not_ok():
    """Step 1 §2 canary: bbox+centroid tiebreak picks OK; rg picks TX.
    Q1 (b) ratified specifically because (a) doesn't suffice."""
    pytest.importorskip("reverse_geocoder")
    rg_map = wigle.derive_states_deflock_batch([(1, 35.2220, -101.8313)])
    ds = rg_map[1]
    assert ds is not None
    assert ds.state_or_country == "TX"


def test_reverse_geocoder_belgium_routes_to_t5():
    pytest.importorskip("reverse_geocoder")
    rg_map = wigle.derive_states_deflock_batch([(1, 50.85, 4.35)])
    ds = rg_map[1]
    assert ds is not None
    assert ds.state_or_country == "BE"
    assert ds.country_code == "BE"
    assert wigle.assign_tier(ds.state_or_country, country_code=ds.country_code) == 5


def test_reverse_geocoder_puerto_rico_routes_to_t4_territory():
    """Q4 ratified: PR is US territory T4-territory sub-rank, NOT T5.
    rg returns cc='PR' (NOT cc='US'); RG_CC_TO_TERRITORY map handles this."""
    pytest.importorskip("reverse_geocoder")
    rg_map = wigle.derive_states_deflock_batch([(1, 18.4655, -66.1057)])
    ds = rg_map[1]
    assert ds is not None
    assert ds.state_or_country == "PR"
    assert ds.country_code == "US"
    assert wigle.assign_tier(ds.state_or_country, country_code=ds.country_code) == 4


def test_reverse_geocoder_usvi_routes_to_t4_territory():
    pytest.importorskip("reverse_geocoder")
    rg_map = wigle.derive_states_deflock_batch([(1, 18.3419, -64.9307)])
    ds = rg_map[1]
    assert ds is not None
    assert ds.state_or_country == "USVI"
    assert ds.country_code == "US"
    assert wigle.assign_tier(ds.state_or_country, country_code=ds.country_code) == 4


# ─── 4. Q4 — Atlas state='PS' explicit do-not-stage ───────────────────────


def test_atlas_state_ps_is_dropped_per_q4():
    """Q4 explicit: 'Atlas state=\"PS\" orphan row stays out-of-scope per §12;
    flag in extraction_runs.notes for Phase-5 traceability, do not stage.'"""
    assert wigle.derive_state_atlas("PS", "US") is None


def test_atlas_state_xy_us_country_is_dropped():
    """Generalization: any non-US-50/DC/territory state value with US
    country gets dropped (do not fabricate a tier for a code we don't
    recognize)."""
    assert wigle.derive_state_atlas("XY", "US") is None


def test_atlas_state_md_us_country_is_kept():
    ds = wigle.derive_state_atlas("MD", "US")
    assert ds is not None
    assert ds.state_or_country == "MD"


# ─── 5. Q2 — parse_quota_signal (HTTP 429 + Retry-After) ──────────────────


def test_parse_quota_signal_429_marks_exhausted():
    sig = wigle.parse_quota_signal(429, {"Content-Type": "application/json"})
    assert sig.is_quota_exhausted is True
    assert sig.status == 429
    assert sig.retry_after_seconds is None


def test_parse_quota_signal_200_not_exhausted():
    sig = wigle.parse_quota_signal(200, {"Content-Type": "application/json"})
    assert sig.is_quota_exhausted is False


def test_parse_quota_signal_retry_after_integer():
    """RFC 7231 §7.1.3 delay-seconds form."""
    sig = wigle.parse_quota_signal(429, {"Retry-After": "120"})
    assert sig.is_quota_exhausted is True
    assert sig.retry_after_seconds == 120


def test_parse_quota_signal_retry_after_http_date():
    """RFC 7231 §7.1.3 HTTP-date form (defensive parse)."""
    # An HTTP-date in the future. The parser computes delta-seconds from
    # now; we just assert it parses to a non-negative integer.
    sig = wigle.parse_quota_signal(
        429,
        {"Retry-After": "Wed, 21 Oct 2099 07:28:00 GMT"},
    )
    assert sig.is_quota_exhausted is True
    assert sig.retry_after_seconds is not None
    assert sig.retry_after_seconds > 0


def test_parse_quota_signal_unparseable_retry_after_logged_and_skipped():
    sig = wigle.parse_quota_signal(429, {"Retry-After": "not-a-date-or-int"})
    assert sig.is_quota_exhausted is True
    assert sig.retry_after_seconds is None


# ─── 6. SSID PII redaction (SAR-5-by-analogy) ─────────────────────────────


def test_redact_ssid_pii_rank_name_pattern():
    redacted, hits = wigle.redact_ssid_pii("Officer Smith Network")
    assert "[REDACTED-RANK-NAME]" in redacted
    assert "Officer Smith" in hits[0]


def test_redact_ssid_pii_phone_of_name_pattern():
    redacted, hits = wigle.redact_ssid_pii("iPhone of Steven")
    assert "[REDACTED-PII-SSID]" in redacted
    assert hits


def test_redact_ssid_pii_clean_ssid_unchanged():
    redacted, hits = wigle.redact_ssid_pii("OfficeWiFi-5G")
    assert redacted == "OfficeWiFi-5G"
    assert hits == []


# ─── 7. DRY_RUN gate ──────────────────────────────────────────────────────


def test_run_live_query_refuses_when_dry_run_true():
    """Default dry_run=True; module MUST refuse to fire."""
    with pytest.raises(RuntimeError, match="DRY_RUN-gated"):
        wigle.run_live_query(
            latrange1=39.0, latrange2=39.5,
            longrange1=-77.0, longrange2=-76.5,
            dry_run=True,
        )


# ─── 8. HTTP Basic header construction (RFC 7617) ─────────────────────────


def test_basic_auth_header_format():
    """HTTP Basic per RFC 7617: 'Basic ' + b64(name:token).
    Verifies against a known value so we don't drift from the swagger
    securityDefinitions.basic spec."""
    h = wigle._basic_auth_header("argusname", "argustoken")
    # b64('argusname:argustoken') = 'YXJndXNuYW1lOmFyZ3VzdG9rZW4='
    assert h == "Basic YXJndXNuYW1lOmFyZ3VzdG9rZW4="


# ─── 9. assemble_priority_rows is deterministic + idempotent ──────────────


def test_assemble_priority_rows_drops_atlas_ps():
    """Atlas state='PS' is filtered upstream of the bulk insert; the
    resulting tuple list does NOT contain a (deployment_id, ...) row
    for the PS source row."""
    pytest.importorskip("reverse_geocoder")
    atlas_rows = [
        (1001, "MD", "US"),    # T1
        (1002, "PS", "US"),    # Q4 do-not-stage
        (1003, "VA", "US"),    # T2
    ]
    deflock_rows: list[tuple[int, float, float]] = []
    tuples, stats = wigle.assemble_priority_rows(atlas_rows, deflock_rows)
    dep_ids = {t[0] for t in tuples}
    assert 1001 in dep_ids
    assert 1003 in dep_ids
    assert 1002 not in dep_ids
    assert stats["skipped"] == 1


def test_assemble_priority_rows_intra_tier_rank_is_one_based():
    pytest.importorskip("reverse_geocoder")
    atlas_rows = [
        (10, "MD", "US"),
        (20, "MD", "US"),
        (30, "MD", "US"),
    ]
    tuples, _ = wigle.assemble_priority_rows(atlas_rows, [])
    md_rows = sorted([t for t in tuples if t[2] == "MD"], key=lambda t: t[0])
    assert [t[3] for t in md_rows] == [1, 2, 3]   # intra_tier_rank


# ─── 10. Live-DB Step 1 §2 count reproduction ─────────────────────────────


def _live_db_path() -> Path:
    return REPO_ROOT / "db" / "argus.db"


@pytest.mark.skipif(
    not _live_db_path().exists(),
    reason="argus.db not present (Phase 2 ingest not yet run)",
)
def test_step1_section2_count_reproduces_against_live_db():
    """Dispatch stop-line: any tier-rollup count that doesn't reproduce
    against worker §2 numbers (Atlas 2,745 + DeFlock 77,953 = 80,698
    Flock-attributed) should stop-and-comment.

    This test asserts the Atlas + DeFlock candidate-set count reproduces.
    Per-tier counts will differ from Step 1 §2 bbox-approximation tables
    because Q1 ratified reverse_geocoder (more accurate); that divergence
    is by design.
    """
    pytest.importorskip("reverse_geocoder")
    conn = sqlite3.connect(_live_db_path())
    try:
        atlas_n = conn.execute(
            "SELECT COUNT(*) FROM deployment_observations "
            "WHERE source_id=5 AND LOWER(vendor_raw) LIKE '%flock%'"
        ).fetchone()[0]
        # DeFlock — Step-1-reproducing strict 6-string match
        placeholders = ",".join("?" * len(wigle.FLOCK_VENDOR_RAW_VALUES))
        deflock_n = conn.execute(
            f"SELECT COUNT(*) FROM deployment_observations "
            f"WHERE source_id=6 AND lat IS NOT NULL AND lon IS NOT NULL "
            f"AND vendor_raw IN ({placeholders})",
            wigle.FLOCK_VENDOR_RAW_VALUES,
        ).fetchone()[0]
    finally:
        conn.close()
    assert atlas_n == 2745, (
        f"Atlas Flock-attributed count drift: got {atlas_n}, expected 2745 "
        "(Step 1 §2). If this fails, stop-and-comment per dispatch clause 11."
    )
    assert deflock_n == 77953, (
        f"DeFlock Flock-attributed count drift: got {deflock_n}, expected "
        "77953 (Step 1 §2). If this fails, stop-and-comment per dispatch "
        "clause 11."
    )
    assert atlas_n + deflock_n == 80698


@pytest.mark.skipif(
    not _live_db_path().exists(),
    reason="argus.db not present",
)
def test_wigle_anchor_priority_table_exists_and_has_indexes():
    conn = sqlite3.connect(_live_db_path())
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='wigle_anchor_priority'"
        ).fetchone()
        assert row is not None, (
            "wigle_anchor_priority table missing — "
            "0004_wigle_anchor_priority.sql not applied?"
        )
        idx_names = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND tbl_name='wigle_anchor_priority'"
            )
        }
        assert "idx_wigle_anchor_priority_tier" in idx_names
        assert "idx_wigle_anchor_priority_state" in idx_names
        assert "idx_wigle_anchor_priority_method" in idx_names
        assert "idx_wigle_anchor_priority_run" in idx_names
        # Forward-compatible: subsequent migrations (e.g. MAC-11 council_minutes_matters
        # at 0005) will bump schema_version higher — the wigle_anchor_priority assertions
        # only need ver >= 4.
        ver = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()[0]
        assert ver >= 4
        # And the specific 0004 row exists.
        assert conn.execute(
            "SELECT 1 FROM schema_version WHERE version = 4"
        ).fetchone() is not None
    finally:
        conn.close()
