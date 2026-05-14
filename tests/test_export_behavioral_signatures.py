"""Tests for ``db/validation/export_behavioral_signatures.py`` — CP18 sibling.

Coverage parallel to ``tests/test_export_lynceus.py`` for the sibling export:

- §7.5 CP18 shape: ``_meta`` keys + ``entries[]`` per-record key set.
- §7.5 CP18 confidence-threshold filter (≥70).
- §11 #13 ``device_category='unknown'`` drop bin.
- Drop bin priority (``unknown_category`` above ``below_confidence_threshold``).
- ``argus_record_id`` recipe verbatim — literal ``"NULL"`` for NULL
  ``cellular_generation``; 16-char lowercase hex; uniqueness across the
  sibling-export survivor set (defense for migration 0010 UNIQUE 3-tuple).
- ``cellular_generation`` exports as JSON-null for ``None`` rows (NOT the
  string ``"NULL"`` — that string is only used in the hash recipe).
- ``threshold_json`` exports as parsed JSON value (object/array/scalar),
  not as a stringified payload.
- Reconciliation invariant ``source − sum(dropped) = entries.length``.
- ``argus_run_id`` deterministic UUID5 stability across re-runs.
- Read-only contract (``PRAGMA query_only = ON``).
- ``coverage_report.md`` BEGIN/END marker injection + idempotent replace.
- End-to-end first-run shape against the live DB.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from db.validation.export_behavioral_signatures import (
    ARGUS_RUN_ID_NAMESPACE,
    CONFIDENCE_THRESHOLD,
    COVERAGE_SECTION_BEGIN,
    COVERAGE_SECTION_END,
    BehavioralSignatureRow,
    Halt,
    _build_payload,
    _classify_row,
    _derive_argus_run_id,
    _open_readonly,
    _parse_threshold_json,
    argus_record_id,
    build_coverage_section,
    patch_coverage_report,
    run,
)

# Schema DDL mirroring migrations 0010 + 0016 (license_column has no
# behavioral_signatures bearing). Only the columns the exporter reads.
SCHEMA_DDL = """
CREATE TABLE schema_version (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  applied_at DATETIME
);
INSERT INTO schema_version (version, name) VALUES (16, '0016_license_column');

CREATE TABLE sources (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  source_url TEXT,
  source_type TEXT,
  notes TEXT
);
INSERT INTO sources (id, name, source_type) VALUES (1, 'test_source', 'academic');

CREATE TABLE behavioral_signatures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  signature_name TEXT NOT NULL,
  cellular_generation TEXT,
  threshold_json TEXT,
  evidence_json TEXT,
  source_id INTEGER NOT NULL REFERENCES sources(id),
  source_file_relative TEXT,
  source_line INTEGER,
  confidence INTEGER,
  device_category TEXT NOT NULL,
  notes TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (signature_name, source_id, cellular_generation)
);
"""


def _row(**kw) -> BehavioralSignatureRow:
    defaults = dict(
        id=1,
        signature_name="Identity Request",
        cellular_generation=None,
        threshold_json='{"foo": 1}',
        confidence=80,
        source_id=37,
        device_category="imsi_catcher",
    )
    defaults.update(kw)
    return BehavioralSignatureRow(**defaults)


# ────────────────────────────────────────────────────────────────────────────
# §7.5 CP18 argus_record_id recipe — verbatim
# ────────────────────────────────────────────────────────────────────────────


def test_argus_record_id_uses_literal_NULL_string_when_cellgen_is_none() -> None:
    """The CP18 field-note specifies the literal string ``"NULL"`` — not
    Python ``None`` and not JSON ``null`` — when cellular_generation is NULL.
    """
    got = argus_record_id("Identity Request", 37, None)
    expected_input = "behavioral_signature|Identity Request|37|NULL"
    expected = hashlib.sha256(expected_input.encode("utf-8")).hexdigest()[:16]
    assert got == expected
    assert len(got) == 16
    assert got == got.lower()  # lowercase hex


def test_argus_record_id_uses_scalar_string_when_cellgen_set() -> None:
    got = argus_record_id("Tracking Area Update Reject Cause #12", 37, "4G")
    expected_input = (
        "behavioral_signature|Tracking Area Update Reject Cause #12|37|4G"
    )
    expected = hashlib.sha256(expected_input.encode("utf-8")).hexdigest()[:16]
    assert got == expected


def test_argus_record_id_distinguishes_NULL_vs_4G() -> None:
    """Same signature_name + source_id but different cellular_generation
    must produce different argus_record_ids (UNIQUE 3-tuple stability)."""
    a = argus_record_id("Identity Request", 37, None)
    b = argus_record_id("Identity Request", 37, "4G")
    assert a != b


# ────────────────────────────────────────────────────────────────────────────
# §7.5 CP18 classification
# ────────────────────────────────────────────────────────────────────────────


def test_classify_survivor_returns_none() -> None:
    assert _classify_row(_row(confidence=80, device_category="imsi_catcher")) is None


def test_classify_below_confidence_threshold() -> None:
    assert _classify_row(_row(confidence=69)) == "below_confidence_threshold"


def test_classify_at_threshold_passes() -> None:
    """Floor is ≥70 inclusive."""
    assert _classify_row(_row(confidence=70)) is None


def test_classify_unknown_category_drops() -> None:
    assert _classify_row(_row(device_category="unknown")) == "unknown_category"


def test_classify_unknown_category_takes_priority_over_below_confidence() -> None:
    """Bin priority: unknown_category > below_confidence_threshold."""
    row = _row(device_category="unknown", confidence=10)
    assert _classify_row(row) == "unknown_category"


# ────────────────────────────────────────────────────────────────────────────
# §7.5 CP18 threshold_json — parsed verbatim, not stringified
# ────────────────────────────────────────────────────────────────────────────


def test_parse_threshold_json_returns_dict_not_string() -> None:
    got = _parse_threshold_json('{"message_type": "Identity Request"}')
    assert got == {"message_type": "Identity Request"}
    assert isinstance(got, dict)


def test_parse_threshold_json_handles_null() -> None:
    assert _parse_threshold_json(None) is None


def test_parse_threshold_json_halts_on_invalid() -> None:
    """If a row somehow has invalid JSON (DB CHECK bypassed) → Halt."""
    with pytest.raises(Halt, match="threshold_json failed JSON parse"):
        _parse_threshold_json("{not json")


# ────────────────────────────────────────────────────────────────────────────
# §7.5 CP18 payload shape
# ────────────────────────────────────────────────────────────────────────────


def test_build_payload_meta_keys_exact() -> None:
    rows = [_row(id=1)]
    payload = _build_payload(
        rows,
        schema_version=16,
        exported_at="2026-05-13T23:59:00Z",
        argus_run_id_val="00000000-0000-5000-8000-000000000000",
    )
    expected_meta_keys = {
        "argus_version",
        "exported_at",
        "record_count",
        "confidence_threshold",
        "argus_run_id",
        "source_record_count",
        "dropped_in_export",
    }
    assert set(payload["_meta"].keys()) == expected_meta_keys


def test_build_payload_dropped_in_export_has_exactly_two_keys() -> None:
    """§7.5 CP18: only ``below_confidence_threshold`` + ``unknown_category``.

    The §4.4 wire-pattern-specific bins (``ssid_pattern`` etc.) do NOT apply
    per CP18 — the sibling shape is intentionally two-key.
    """
    rows = [_row(id=1)]
    payload = _build_payload(
        rows,
        schema_version=16,
        exported_at="2026-05-13T23:59:00Z",
        argus_run_id_val="00000000-0000-5000-8000-000000000000",
    )
    assert set(payload["_meta"]["dropped_in_export"].keys()) == {
        "below_confidence_threshold",
        "unknown_category",
    }


def test_build_payload_entries_per_record_keys_exact() -> None:
    rows = [_row(id=1)]
    payload = _build_payload(
        rows,
        schema_version=16,
        exported_at="2026-05-13T23:59:00Z",
        argus_run_id_val="00000000-0000-5000-8000-000000000000",
    )
    assert len(payload["entries"]) == 1
    expected_entry_keys = {
        "signature_name",
        "cellular_generation",
        "threshold_json",
        "confidence",
        "argus_record_id",
    }
    assert set(payload["entries"][0].keys()) == expected_entry_keys


def test_build_payload_cellular_generation_exports_as_jsonnull_when_none() -> None:
    """Per CP18 field-note: scalar JSON null for NULL rows, NOT string 'NULL'.

    The string 'NULL' is only used inside the argus_record_id hash input.
    """
    rows = [_row(id=1, cellular_generation=None)]
    payload = _build_payload(
        rows,
        schema_version=16,
        exported_at="2026-05-13T23:59:00Z",
        argus_run_id_val="00000000-0000-5000-8000-000000000000",
    )
    assert payload["entries"][0]["cellular_generation"] is None
    # Round-trip via JSON to verify it serializes as `null`, not `"NULL"`.
    serialized = json.dumps(payload["entries"][0])
    assert '"cellular_generation": null' in serialized
    assert '"cellular_generation": "NULL"' not in serialized


def test_build_payload_threshold_json_is_parsed_value_not_string() -> None:
    rows = [_row(id=1, threshold_json='{"message_type": "Identity Request"}')]
    payload = _build_payload(
        rows,
        schema_version=16,
        exported_at="2026-05-13T23:59:00Z",
        argus_run_id_val="00000000-0000-5000-8000-000000000000",
    )
    entry = payload["entries"][0]
    assert isinstance(entry["threshold_json"], dict)
    assert entry["threshold_json"] == {"message_type": "Identity Request"}


def test_build_payload_reconciliation_invariant() -> None:
    """source_record_count − sum(dropped) = record_count."""
    rows = [
        _row(id=1, confidence=80),  # survivor
        _row(id=2, confidence=10, signature_name="bad_low_conf"),  # below_conf
        _row(id=3, device_category="unknown", signature_name="bad_unknown"),  # unknown_cat
    ]
    payload = _build_payload(
        rows,
        schema_version=16,
        exported_at="2026-05-13T23:59:00Z",
        argus_run_id_val="00000000-0000-5000-8000-000000000000",
    )
    meta = payload["_meta"]
    assert meta["source_record_count"] == 3
    assert meta["record_count"] == 1
    assert meta["dropped_in_export"]["below_confidence_threshold"] == 1
    assert meta["dropped_in_export"]["unknown_category"] == 1
    assert (
        meta["source_record_count"] - sum(meta["dropped_in_export"].values())
        == meta["record_count"]
    )


def test_build_payload_halts_on_argus_record_id_collision() -> None:
    """If somehow two survivors land with the same (signature_name, source_id,
    cellular_generation) hash, halt the line. This is a defense against
    UNIQUE-constraint logic mismatch (the migration 0010 UNIQUE 3-tuple is
    supposed to prevent the upstream collision)."""
    rows = [
        _row(id=1, signature_name="dup_sig", cellular_generation=None, source_id=1),
        _row(id=2, signature_name="dup_sig", cellular_generation=None, source_id=1),
    ]
    with pytest.raises(Halt, match="argus_record_id collision"):
        _build_payload(
            rows,
            schema_version=16,
            exported_at="2026-05-13T23:59:00Z",
            argus_run_id_val="00000000-0000-5000-8000-000000000000",
        )


def test_build_payload_confidence_threshold_in_meta_is_integer_70() -> None:
    """§2.1 dispatch instruction: `confidence_threshold` is `70` (int, not 70.0)."""
    rows = [_row(id=1)]
    payload = _build_payload(
        rows,
        schema_version=16,
        exported_at="2026-05-13T23:59:00Z",
        argus_run_id_val="00000000-0000-5000-8000-000000000000",
    )
    assert payload["_meta"]["confidence_threshold"] == 70
    assert isinstance(payload["_meta"]["confidence_threshold"], int)
    assert payload["_meta"]["confidence_threshold"] == CONFIDENCE_THRESHOLD


def test_build_payload_entries_sorted_by_argus_record_id() -> None:
    """Stable ordering for byte-identical re-runs."""
    rows = [
        _row(id=i, signature_name=f"sig_{i}", source_id=1)
        for i in range(1, 11)
    ]
    payload = _build_payload(
        rows,
        schema_version=16,
        exported_at="2026-05-13T23:59:00Z",
        argus_run_id_val="00000000-0000-5000-8000-000000000000",
    )
    ids = [e["argus_record_id"] for e in payload["entries"]]
    assert ids == sorted(ids)


# ────────────────────────────────────────────────────────────────────────────
# argus_run_id determinism
# ────────────────────────────────────────────────────────────────────────────


def test_argus_run_id_is_deterministic_uuid5() -> None:
    rows = [_row(id=1), _row(id=2, signature_name="sig_2")]
    a = _derive_argus_run_id(rows)
    b = _derive_argus_run_id(rows)
    assert a == b


def test_argus_run_id_changes_when_data_changes() -> None:
    a = _derive_argus_run_id([_row(id=1, confidence=80)])
    b = _derive_argus_run_id([_row(id=1, confidence=70)])
    assert a != b


def test_argus_run_id_namespace_distinct_from_lynceus() -> None:
    """The behavioral_signatures namespace must NOT collide with the Lynceus
    exporter's namespace (so a hypothetical fingerprint collision can't
    produce identical run-ids across the two exporters)."""
    from db.validation.export_lynceus import (
        ARGUS_RUN_ID_NAMESPACE as LYNCEUS_NAMESPACE,
    )
    assert ARGUS_RUN_ID_NAMESPACE != LYNCEUS_NAMESPACE


# ────────────────────────────────────────────────────────────────────────────
# Read-only contract (PRAGMA query_only = ON)
# ────────────────────────────────────────────────────────────────────────────


def _build_test_db(tmp_path: Path, rows: list[dict]) -> Path:
    db_path = tmp_path / "test.db"
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA_DDL)
    for r in rows:
        con.execute(
            """
            INSERT INTO behavioral_signatures
                (signature_name, cellular_generation, threshold_json,
                 confidence, source_id, device_category)
            VALUES (:signature_name, :cellular_generation, :threshold_json,
                    :confidence, :source_id, :device_category)
            """,
            {
                "signature_name": r.get("signature_name", "Identity Request"),
                "cellular_generation": r.get("cellular_generation"),
                "threshold_json": r.get("threshold_json", '{"k": 1}'),
                "confidence": r.get("confidence", 80),
                "source_id": r.get("source_id", 1),
                "device_category": r.get("device_category", "imsi_catcher"),
            },
        )
    con.commit()
    con.close()
    return db_path


def test_open_readonly_blocks_writes(tmp_path: Path) -> None:
    db_path = _build_test_db(tmp_path, [{"signature_name": "Identity Request"}])
    con = _open_readonly(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            con.execute(
                "INSERT INTO behavioral_signatures "
                "(signature_name, source_id, confidence, device_category) "
                "VALUES ('writebait', 1, 80, 'imsi_catcher')"
            )
    finally:
        con.close()


# ────────────────────────────────────────────────────────────────────────────
# End-to-end run() against a synthetic DB
# ────────────────────────────────────────────────────────────────────────────


def test_run_end_to_end_writes_json_with_55_row_shape(tmp_path: Path) -> None:
    db_path = _build_test_db(
        tmp_path,
        [
            {"signature_name": "Identity Request", "cellular_generation": None},
            {"signature_name": "Authentication Reject", "cellular_generation": "4G"},
            {"signature_name": "TAU Reject 12", "cellular_generation": "4G",
             "confidence": 65},  # below floor → dropped
            {"signature_name": "Future Wave-D row",
             "device_category": "unknown"},  # unknown_cat → dropped
        ],
    )
    out_path = tmp_path / "out.json"
    payload = run(
        db_path=db_path,
        output_path=out_path,
        coverage_report_path=None,
        exported_at="2026-05-13T23:59:00Z",
    )
    assert out_path.exists()
    meta = payload["_meta"]
    assert meta["source_record_count"] == 4
    assert meta["record_count"] == 2
    assert meta["dropped_in_export"] == {
        "below_confidence_threshold": 1,
        "unknown_category": 1,
    }
    assert len(payload["entries"]) == 2


def test_run_byte_identical_modulo_exported_at(tmp_path: Path) -> None:
    """Re-running over unchanged DB produces byte-identical files modulo
    the ``exported_at`` field (CP18 idempotency property)."""
    db_path = _build_test_db(
        tmp_path,
        [
            {"signature_name": "sig_a", "cellular_generation": "4G"},
            {"signature_name": "sig_b", "cellular_generation": None},
        ],
    )
    out_a = tmp_path / "a.json"
    out_b = tmp_path / "b.json"
    run(
        db_path=db_path, output_path=out_a, coverage_report_path=None,
        exported_at="2026-05-13T23:59:00Z",
    )
    run(
        db_path=db_path, output_path=out_b, coverage_report_path=None,
        exported_at="2026-05-13T23:59:00Z",
    )
    assert out_a.read_text(encoding="utf-8") == out_b.read_text(encoding="utf-8")


# ────────────────────────────────────────────────────────────────────────────
# coverage_report.md patching — BEGIN/END marker idempotency
# ────────────────────────────────────────────────────────────────────────────


def _sample_payload() -> dict:
    return {
        "_meta": {
            "argus_version": "16",
            "exported_at": "2026-05-13T23:59:00Z",
            "record_count": 53,
            "confidence_threshold": 70,
            "argus_run_id": "00000000-0000-5000-8000-000000000000",
            "source_record_count": 55,
            "dropped_in_export": {
                "below_confidence_threshold": 1,
                "unknown_category": 1,
            },
        },
        "entries": [],
    }


def test_build_coverage_section_contains_markers_and_reconciliation() -> None:
    section = build_coverage_section(_sample_payload())
    assert COVERAGE_SECTION_BEGIN in section
    assert COVERAGE_SECTION_END in section
    assert "Behavioral-signatures export reconciliation" in section
    assert "55 source − 2 dropped = 53 entries" in section


def test_patch_coverage_report_appends_when_no_existing_section(tmp_path: Path) -> None:
    report_path = tmp_path / "coverage_report.md"
    report_path.write_text("# Existing report\n\nbase content\n", encoding="utf-8")
    patch_coverage_report(report_path, build_coverage_section(_sample_payload()))
    text = report_path.read_text(encoding="utf-8")
    assert "base content" in text
    assert COVERAGE_SECTION_BEGIN in text
    assert COVERAGE_SECTION_END in text


def test_patch_coverage_report_idempotent_replace(tmp_path: Path) -> None:
    """Re-running patch_coverage_report with the same payload produces
    a byte-identical file (no double-append)."""
    report_path = tmp_path / "coverage_report.md"
    report_path.write_text("# Existing report\n\nbase content\n", encoding="utf-8")
    patch_coverage_report(report_path, build_coverage_section(_sample_payload()))
    first = report_path.read_text(encoding="utf-8")
    patch_coverage_report(report_path, build_coverage_section(_sample_payload()))
    second = report_path.read_text(encoding="utf-8")
    assert first == second
    # Verify only one BEGIN marker present (no append-duplication).
    assert first.count(COVERAGE_SECTION_BEGIN) == 1
    assert first.count(COVERAGE_SECTION_END) == 1


def test_patch_coverage_report_replaces_stale_section(tmp_path: Path) -> None:
    """If the marked section already exists, patching replaces it in-place
    rather than appending. Demonstrates the idempotent-update property."""
    report_path = tmp_path / "coverage_report.md"
    stale_payload = _sample_payload()
    stale_payload["_meta"]["record_count"] = 99  # different from fresh
    stale_payload["_meta"]["source_record_count"] = 99
    stale_payload["_meta"]["dropped_in_export"] = {
        "below_confidence_threshold": 0,
        "unknown_category": 0,
    }
    report_path.write_text(
        "# Existing report\n\nbase content\n\n"
        + build_coverage_section(stale_payload)
        + "\n## suffix section\n\nsuffix content\n",
        encoding="utf-8",
    )
    fresh = _sample_payload()
    patch_coverage_report(report_path, build_coverage_section(fresh))
    text = report_path.read_text(encoding="utf-8")
    assert text.count(COVERAGE_SECTION_BEGIN) == 1
    assert "55 source − 2 dropped = 53 entries" in text
    assert "99 source" not in text
    # Suffix preserved.
    assert "suffix section" in text
    assert "suffix content" in text


def test_patch_coverage_report_halts_when_file_missing(tmp_path: Path) -> None:
    with pytest.raises(Halt, match="coverage_report.md missing"):
        patch_coverage_report(
            tmp_path / "nonexistent.md", build_coverage_section(_sample_payload())
        )
