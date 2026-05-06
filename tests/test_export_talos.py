"""Tests for ``db/validation/export_talos.py`` — Phase-5 Step-6 writer (MAC-46).

Coverage:
- §4.4 type-mapping enforcement: every survivor has a Talos pattern_type.
- §4.5 severity-derivation enforcement: every survivor has a Talos severity.
- §7.5 description-format ceiling (≤80 chars) — positive + halt-on-overflow.
- §11 #13 unknown_category bin assignment + survivor count.
- §11 #12 / §8.4 Pi self-exclude OUI ban applies to high-confidence file.
- §11 #14 procurement_only defense-in-depth bin.
- ``below_confidence_threshold`` bin for the high-confidence file.
- Drop-tally reconciliation halts on disagreement vs MAC-45 expected map.
- ``_meta`` shape conforms to §7.5 (record_count + source_record_count +
  ``dropped_in_export`` block + reconciliation invariant).
- Idempotency: re-running on identical DB state produces byte-identical
  files modulo the ``exported_at`` timestamp; ``argus_run_id`` is stable.
- Read-only contract: ``PRAGMA query_only = ON`` blocks writes.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from db.validation.export_talos import (
    DESCRIPTION_MAX_CHARS,
    DEVICE_CATEGORY_TO_SEVERITY,
    IDENTIFIER_TYPE_TO_PATTERN_TYPE,
    PI_SELF_EXCLUDE_OUIS,
    ActiveRow,
    Halt,
    _build_export,
    _classify_row,
    _derive_argus_run_id,
    _format_description,
    _open_readonly,
    run,
)

SCHEMA_DDL = """
CREATE TABLE identifiers (
  id INTEGER PRIMARY KEY,
  identifier TEXT NOT NULL,
  identifier_type TEXT NOT NULL,
  device_category TEXT NOT NULL,
  manufacturer TEXT,
  model TEXT,
  confidence INTEGER,
  source_url TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_excerpt TEXT,
  geographic_scope TEXT,
  first_seen DATETIME,
  last_verified DATETIME,
  notes TEXT,
  superseded_by INTEGER
);
CREATE TABLE schema_version (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  applied_at DATETIME
);
INSERT INTO schema_version (version, name) VALUES (1, '0001_initial');
INSERT INTO schema_version (version, name) VALUES (7, '0007_motorola_solutions_aliases_rescope');
"""


def _row(**kw) -> ActiveRow:
    defaults = dict(
        id=1,
        identifier="aa:bb:cc:dd:ee:ff",
        identifier_type="mac",
        device_category="alpr",
        manufacturer="Acme",
        model=None,
        confidence=80,
        source_type="manufacturer_doc",
        source_url="http://example/test",
        source_excerpt=None,
        notes=None,
        geographic_scope=None,
    )
    defaults.update(kw)
    return ActiveRow(**defaults)


# ────────────────────────────────────────────────────────────────────────────
# §4.4 / §4.5 mapping invariants
# ────────────────────────────────────────────────────────────────────────────


def test_type_mapping_covers_every_identifier_type() -> None:
    expected = {
        "oui",
        "mac",
        "mac_range",
        "bssid",
        "ssid_exact",
        "ssid_pattern",
        "ble_uuid",
        "ble_service",
        "device_fingerprint",
    }
    assert set(IDENTIFIER_TYPE_TO_PATTERN_TYPE.keys()) == expected


def test_type_mapping_drops_match_44_verbatim() -> None:
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["ssid_pattern"] is None
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["device_fingerprint"] is None
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["mac_range"] is None
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["bssid"] == "mac"
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["ble_service"] == "ble_uuid"


def test_severity_mapping_excludes_unknown_per_section_11_13() -> None:
    """`unknown` device_category MUST NOT have a severity mapping.

    Bible §11 #13 bans unknown-category Talos export; the writer halts before
    severity derivation. Including a severity row would invite accidental
    promotion through a code-path bug.
    """
    assert "unknown" not in DEVICE_CATEGORY_TO_SEVERITY


def test_severity_high_categories_per_section_45() -> None:
    for cat in ("imsi_catcher", "alpr", "covert_cam", "hacking_tool", "gps_tracker", "face_recog"):
        assert DEVICE_CATEGORY_TO_SEVERITY[cat] == "high"


# ────────────────────────────────────────────────────────────────────────────
# Drop-bin classification (priority order)
# ────────────────────────────────────────────────────────────────────────────


def test_classify_unknown_category_drops_section_11_13() -> None:
    bin_label, entries = _classify_row(
        _row(device_category="unknown"),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "unknown_category"
    assert entries == []


def test_classify_procurement_drops_section_11_14() -> None:
    bin_label, entries = _classify_row(
        _row(source_type="procurement", device_category="alpr"),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    # §11 #14 fires before §11 #13 per priority order.
    assert bin_label == "procurement_only"
    assert entries == []


def test_classify_procurement_takes_priority_over_unknown_category() -> None:
    """Defense-in-depth: a procurement-typed row still goes to procurement_only
    even if its device_category is unknown — the §11 #14 ban is the more
    fundamental rule (no concrete identifier in §4.5 design)."""
    bin_label, _ = _classify_row(
        _row(source_type="procurement", device_category="unknown"),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "procurement_only"


def test_classify_below_confidence_threshold() -> None:
    bin_label, _ = _classify_row(
        _row(confidence=60),
        confidence_threshold=70,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "below_confidence_threshold"


def test_classify_below_confidence_floor_30() -> None:
    bin_label, _ = _classify_row(
        _row(confidence=29),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "below_confidence_threshold"


def test_classify_pi_self_exclude_only_for_high_conf_file() -> None:
    """The Pi-OUI ban is only applied to the high-confidence file per §11 #12.
    The standard file lets the OUI through with description noting informational status."""
    pi_oui = next(iter(PI_SELF_EXCLUDE_OUIS))
    # Standard file: should NOT drop to self_exclude_oui.
    bin_label, _ = _classify_row(
        _row(identifier=pi_oui, identifier_type="oui", device_category="hacking_tool", confidence=80),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label is None  # survivor in standard
    # High-confidence file: should drop to self_exclude_oui.
    bin_label, _ = _classify_row(
        _row(identifier=pi_oui, identifier_type="oui", device_category="hacking_tool", confidence=80),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
    )
    assert bin_label == "self_exclude_oui"


def test_classify_ssid_pattern_drops_section_44() -> None:
    bin_label, _ = _classify_row(
        _row(identifier="^Flock-.*$", identifier_type="ssid_pattern", device_category="alpr"),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "ssid_pattern"


def test_classify_device_fingerprint_drops_section_44() -> None:
    bin_label, _ = _classify_row(
        _row(identifier="fingerprint-abc", identifier_type="device_fingerprint", device_category="alpr"),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "device_fingerprint"


def test_classify_mac_range_drops_to_oversized_section_44() -> None:
    bin_label, _ = _classify_row(
        _row(identifier="00:50:c2:36:0", identifier_type="mac_range", device_category="alpr"),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    # mac_range has no Talos pattern_type post-§4.4 (expand-or-drop, but
    # all known active mac_range rows are oversized → drop).
    assert bin_label == "oversized_mac_range"


def test_classify_survivor_alpr_mac() -> None:
    bin_label, entries = _classify_row(
        _row(identifier="e4:aa:ea:80:a1:9b", identifier_type="mac", device_category="alpr",
             manufacturer="Flock Safety", confidence=60),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label is None
    assert len(entries) == 1
    e = entries[0]
    assert e.pattern == "e4:aa:ea:80:a1:9b"
    assert e.pattern_type == "mac"
    assert e.severity == "high"
    assert e.description == "Flock Safety ALPR camera"
    assert e.argus_record_id == 1
    assert len(e.description) <= DESCRIPTION_MAX_CHARS


# ────────────────────────────────────────────────────────────────────────────
# Description-format gate
# ────────────────────────────────────────────────────────────────────────────


def test_description_seed_used_when_present() -> None:
    desc = _format_description(_row(manufacturer="Flock Safety", device_category="alpr"))
    assert desc == "Flock Safety ALPR camera"


def test_description_fallback_within_ceiling() -> None:
    desc = _format_description(_row(manufacturer="Acme", device_category="alpr"))
    assert desc == "Acme alpr device"
    assert len(desc) <= DESCRIPTION_MAX_CHARS


def test_description_generic_when_no_manufacturer() -> None:
    desc = _format_description(_row(manufacturer=None, device_category="alpr"))
    assert desc == "alpr device"


def test_description_long_vendor_falls_back_to_generic_per_section_75() -> None:
    """§7.5: 'If a record cannot be described in 80 chars without losing
    meaning, the canonical record stays but the Talos export uses a generic
    description like `{category} device`.' The writer must NOT halt on a
    long manufacturer; it must fall back to the generic form."""
    long_vendor = "X" * 100
    desc = _format_description(_row(manufacturer=long_vendor, device_category="alpr"))
    assert desc == "alpr device"
    assert len(desc) <= DESCRIPTION_MAX_CHARS


def test_classify_halts_when_description_exceeds_80_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive backstop: if `_format_description` ever returns a >80-char
    string (would require both seed corruption AND fallback malfunction), the
    survivor-branch length-check halts the line per §7.5. The fallback chain
    in real code is unreachable with valid §4.1 enum values, but this gate
    is wired regardless."""
    import db.validation.export_talos as mod

    monkeypatch.setattr(mod, "_format_description", lambda row: "Z" * 100)
    with pytest.raises(Halt, match="exceeds 80-char"):
        _classify_row(
            _row(manufacturer="Acme", device_category="alpr"),
            confidence_threshold=30,
            apply_pi_self_exclude=False,
        )


# ────────────────────────────────────────────────────────────────────────────
# Reconciliation halts vs MAC-45 expectations
# ────────────────────────────────────────────────────────────────────────────


def test_build_export_halts_on_drop_assignments_mismatch() -> None:
    """If MAC-45 says row X drops to bin Y but the writer says Z, halt."""
    rows = [_row(id=10, device_category="unknown")]
    # Writer will classify id=10 as unknown_category. Lie that MAC-45 expects
    # procurement_only — must halt.
    with pytest.raises(Halt, match="STOP-THE-LINE"):
        _build_export(
            rows=rows,
            file_label="argus_export.json",
            confidence_threshold=30,
            apply_pi_self_exclude=False,
            schema_version=7,
            argus_run_id="00000000-0000-0000-0000-000000000000",
            exported_at="2026-01-01T00:00:00Z",
            expected_drop_assignments={"10": "procurement_only"},
        )


def test_build_export_halts_on_extra_writer_drop() -> None:
    """If writer drops a row that MAC-45 expects to survive, halt."""
    rows = [_row(id=11, device_category="unknown")]
    with pytest.raises(Halt, match="STOP-THE-LINE"):
        _build_export(
            rows=rows,
            file_label="argus_export.json",
            confidence_threshold=30,
            apply_pi_self_exclude=False,
            schema_version=7,
            argus_run_id="00000000-0000-0000-0000-000000000000",
            exported_at="2026-01-01T00:00:00Z",
            expected_drop_assignments={},  # MAC-45 expects no drops
        )


def test_build_export_passes_when_assignments_align() -> None:
    rows = [
        _row(id=20, device_category="unknown"),
        _row(id=21, identifier="e4:aa:ea:80:a1:9b", identifier_type="mac",
             device_category="alpr", manufacturer="Flock Safety", confidence=60),
    ]
    payload, assignments = _build_export(
        rows=rows,
        file_label="argus_export.json",
        confidence_threshold=30,
        apply_pi_self_exclude=False,
        schema_version=7,
        argus_run_id="abc",
        exported_at="2026-01-01T00:00:00Z",
        expected_drop_assignments={"20": "unknown_category"},
    )
    assert payload["_meta"]["record_count"] == 1
    assert payload["_meta"]["source_record_count"] == 2
    assert payload["_meta"]["dropped_in_export"]["unknown_category"] == 1
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["argus_record_id"] == 21
    assert assignments == {20: "unknown_category", 21: None}


def test_meta_reconciliation_invariant() -> None:
    """§7.5: `source_record_count − sum(dropped_in_export) = entries.length`."""
    rows = [_row(id=i, device_category="unknown") for i in range(1, 4)]
    payload, _ = _build_export(
        rows=rows,
        file_label="argus_export.json",
        confidence_threshold=30,
        apply_pi_self_exclude=False,
        schema_version=7,
        argus_run_id="abc",
        exported_at="2026-01-01T00:00:00Z",
        expected_drop_assignments={"1": "unknown_category", "2": "unknown_category", "3": "unknown_category"},
    )
    meta = payload["_meta"]
    assert (
        meta["source_record_count"] - sum(meta["dropped_in_export"].values())
        == len(payload["entries"])
    )


# ────────────────────────────────────────────────────────────────────────────
# Idempotency + read-only invariants
# ────────────────────────────────────────────────────────────────────────────


def test_argus_run_id_deterministic_on_identical_input() -> None:
    rows1 = [_row(id=1), _row(id=2, identifier="11:22:33:44:55:66")]
    rows2 = [_row(id=1), _row(id=2, identifier="11:22:33:44:55:66")]
    assert _derive_argus_run_id(rows1) == _derive_argus_run_id(rows2)


def test_argus_run_id_changes_on_input_change() -> None:
    rows1 = [_row(id=1, confidence=60)]
    rows2 = [_row(id=1, confidence=70)]
    assert _derive_argus_run_id(rows1) != _derive_argus_run_id(rows2)


def test_open_readonly_blocks_writes(tmp_path: Path) -> None:
    """`PRAGMA query_only = ON` must reject INSERT/UPDATE/DELETE."""
    db_path = tmp_path / "test.db"
    setup = sqlite3.connect(str(db_path))
    setup.executescript(SCHEMA_DDL)
    setup.commit()
    setup.close()

    con = _open_readonly(db_path)
    with pytest.raises(sqlite3.OperationalError):
        con.execute(
            "INSERT INTO identifiers "
            "(id, identifier, identifier_type, device_category, "
            " confidence, source_url, source_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "aa:bb:cc", "oui", "alpr", 80, "http://e", "official"),
        )
    con.close()


# ────────────────────────────────────────────────────────────────────────────
# End-to-end run() against a synthetic DB
# ────────────────────────────────────────────────────────────────────────────


def _make_synthetic_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "argus.db"
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA_DDL)
    con.execute(
        "INSERT INTO identifiers (id, identifier, identifier_type, "
        "device_category, manufacturer, confidence, source_url, source_type) "
        "VALUES (1, 'e4:aa:ea:80:a1:9b', 'mac', 'alpr', 'Flock Safety', "
        "60, 'http://e', 'crowdsourced')"
    )
    con.execute(
        "INSERT INTO identifiers (id, identifier, identifier_type, "
        "device_category, manufacturer, confidence, source_url, source_type) "
        "VALUES (2, '00:04:7d', 'oui', 'unknown', 'Motorola Solutions', "
        "55, 'http://e', 'inferred')"
    )
    con.commit()
    con.close()
    return db_path


def _make_synthetic_mac45(tmp_path: Path) -> tuple[Path, Path]:
    matrix_md_path = tmp_path / "coverage_matrix.md"
    matrix_md_path.write_text("# matrix seed\n", encoding="utf-8")
    report_path = tmp_path / "coverage_matrix_report.json"
    report_path.write_text(
        json.dumps(
            {
                "drop_tally_standard": {
                    "drop_assignments": {"2": "unknown_category"},
                    "bins": {
                        "unknown_category": 1,
                        "procurement_only": 0,
                        "self_exclude_oui": 0,
                        "below_confidence_threshold": 0,
                        "oversized_mac_range": 0,
                        "ssid_pattern": 0,
                        "device_fingerprint": 0,
                    },
                    "survivors": 1,
                    "reconciles": 2,
                },
                "drop_tally_high_confidence": {
                    "drop_assignments": {"1": "below_confidence_threshold", "2": "unknown_category"},
                    "bins": {
                        "unknown_category": 1,
                        "procurement_only": 0,
                        "self_exclude_oui": 0,
                        "below_confidence_threshold": 1,
                        "oversized_mac_range": 0,
                        "ssid_pattern": 0,
                        "device_fingerprint": 0,
                    },
                    "survivors": 0,
                    "reconciles": 2,
                },
            }
        ),
        encoding="utf-8",
    )
    return report_path, matrix_md_path


def test_run_writes_all_four_files(tmp_path: Path) -> None:
    db_path = _make_synthetic_db(tmp_path)
    report_path, matrix_md_path = _make_synthetic_mac45(tmp_path)
    exports_dir = tmp_path / "exports"

    summary = run(
        db_path=db_path,
        exports_dir=exports_dir,
        coverage_matrix_report_path=report_path,
        coverage_matrix_md_path=matrix_md_path,
    )
    assert summary["active_row_count"] == 2

    standard = json.loads((exports_dir / "argus_export.json").read_text())
    assert standard["_meta"]["record_count"] == 1
    assert standard["_meta"]["source_record_count"] == 2
    assert standard["_meta"]["confidence_threshold"] == 30
    assert len(standard["entries"]) == 1
    assert standard["entries"][0]["argus_record_id"] == 1
    assert standard["entries"][0]["pattern_type"] == "mac"
    assert standard["entries"][0]["severity"] == "high"

    high = json.loads((exports_dir / "argus_export_high_confidence.json").read_text())
    assert high["_meta"]["record_count"] == 0
    assert high["_meta"]["confidence_threshold"] == 70
    assert high["_meta"]["dropped_in_export"]["below_confidence_threshold"] == 1
    assert high["entries"] == []

    csv_text = (exports_dir / "argus_export.csv").read_text()
    assert csv_text.startswith("# meta:")
    assert "e4:aa:ea:80:a1:9b" in csv_text
    assert "00:04:7d" in csv_text

    coverage = (exports_dir / "coverage_report.md").read_text()
    assert "# Argus Phase-5 coverage report" in coverage
    assert "argus_export.json" in coverage
    assert "argus_export_high_confidence.json" in coverage
    # MAC-45 verbatim-embedded matrix seed should appear.
    assert "# matrix seed" in coverage


def test_run_idempotent_modulo_exported_at(tmp_path: Path) -> None:
    db_path = _make_synthetic_db(tmp_path)
    report_path, matrix_md_path = _make_synthetic_mac45(tmp_path)
    exports_dir = tmp_path / "exports"

    summary1 = run(
        db_path=db_path,
        exports_dir=exports_dir,
        coverage_matrix_report_path=report_path,
        coverage_matrix_md_path=matrix_md_path,
    )
    standard1 = (exports_dir / "argus_export.json").read_text()

    summary2 = run(
        db_path=db_path,
        exports_dir=exports_dir,
        coverage_matrix_report_path=report_path,
        coverage_matrix_md_path=matrix_md_path,
    )
    standard2 = (exports_dir / "argus_export.json").read_text()

    # argus_run_id is deterministic; only exported_at varies.
    assert summary1["argus_run_id"] == summary2["argus_run_id"]
    line1 = [l for l in standard1.splitlines() if '"exported_at"' not in l]
    line2 = [l for l in standard2.splitlines() if '"exported_at"' not in l]
    assert line1 == line2


def test_run_halts_when_mac45_report_missing(tmp_path: Path) -> None:
    db_path = _make_synthetic_db(tmp_path)
    exports_dir = tmp_path / "exports"
    with pytest.raises(Halt, match="not found"):
        run(
            db_path=db_path,
            exports_dir=exports_dir,
            coverage_matrix_report_path=tmp_path / "missing.json",
            coverage_matrix_md_path=tmp_path / "missing.md",
        )
