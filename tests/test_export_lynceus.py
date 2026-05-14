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

from db.export.argus_record_id import argus_record_id as _sar10_hash
from db.validation.export_lynceus import (
    DEFAULT_GEOGRAPHIC_SCOPE_FILTER,
    DESCRIPTION_MAX_CHARS,
    DESCRIPTION_VENDOR_UNATTRIBUTED,
    DROPPED_REASONS,
    EXCLUDED_SOURCE_TYPES,
    IDENTIFIER_TYPE_TO_PATTERN_TYPE,
    PI_SELF_EXCLUDE_OUIS,
    ActiveRow,
    Halt,
    _build_export,
    _classify_row,
    _derive_argus_run_id,
    _format_description,
    _open_readonly,
    _passes_geographic_scope,
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
        first_seen=None,
        last_verified=None,
    )
    defaults.update(kw)
    return ActiveRow(**defaults)


# ────────────────────────────────────────────────────────────────────────────
# §4.4 / §4.5 mapping invariants
# ────────────────────────────────────────────────────────────────────────────


def test_type_mapping_covers_every_identifier_type() -> None:
    # Post-CP16: dispositions are split across IDENTIFIER_TYPE_TO_PATTERN_TYPE
    # (15 MAP cases) + DROPPED_REASONS (12 DROPPED cases) per CP16's lean-
    # refactor design (board direction at MAC-75 5b9212ce). Union must equal
    # the full post-CP14 identifier_type enum (27 values).
    expected = {
        # Pre-CP13 (migration 0001)
        "oui", "mac", "mac_range", "bssid",
        "ssid_exact", "ssid_pattern",
        "ble_uuid", "ble_service",
        "device_fingerprint",
        # CP13 (migration 0009) — Wave G analytical-only types
        "ble_local_name", "ble_characteristic", "product_family_codename",
        # CP14 (migration 0011) — G-3 BLE SIG manufacturer IDs
        "ble_manufacturer_id",
        # CP14 (migration 0013) — Drone-RID + proprietary-protocol cluster
        "drone_id_prefix", "icao_24bit_address",
        "rf_channel", "burst_cadence_ms", "bandwidth_mhz",
        "device_class_id", "rf_burst_duration", "rf_protocol_constant",
        "wifi_aware_service_name",
        "wifi_ie_element_id", "bluetooth_le_pdu_type",
        "wifi_frame_control_subtype", "wifi_nan_param_signature",
        # CP14 (migration 0014) — surveillance metadata
        "alpr_model",
    }
    assert (
        set(IDENTIFIER_TYPE_TO_PATTERN_TYPE.keys()) | set(DROPPED_REASONS.keys())
        == expected
    )
    # CP16 split-structure invariant — no key overlap between MAP dict and
    # DROPPED_REASONS (every type has exactly one disposition surface).
    assert (
        set(IDENTIFIER_TYPE_TO_PATTERN_TYPE.keys())
        & set(DROPPED_REASONS.keys())
        == set()
    )


def test_type_mapping_drops_match_44_verbatim() -> None:
    # Legacy DROPPED entries (still live in IDENTIFIER_TYPE_TO_PATTERN_TYPE per
    # CP16 board direction at MAC-75 5b9212ce: legacy branches preserved).
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["ssid_pattern"] is None
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["device_fingerprint"] is None
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["mac_range"] is None
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["bssid"] == "mac"
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["ble_service"] == "ble_uuid"
    # CP13 (§4.4) — all three Wave G analytical-only types are DROPPED.
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["ble_local_name"] is None
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["ble_characteristic"] is None
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["product_family_codename"] is None
    # CP16 (§4.4) — 3 new MAP entries flow through the dict (new pattern_types).
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["ble_manufacturer_id"] == "ble_manufacturer_id"
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["drone_id_prefix"] == "drone_id_prefix"
    assert IDENTIFIER_TYPE_TO_PATTERN_TYPE["wifi_aware_service_name"] == "wifi_aware_service_name"
    # CP16 (§4.4) — 12 new DROPPED entries live in DROPPED_REASONS with bin
    # labels matching identifier_type names (consistent with the legacy
    # ble_local_name / ble_characteristic / product_family_codename pattern).
    for k in DROPPED_REASONS:
        assert DROPPED_REASONS[k] == k


def test_severity_field_dropped_from_export_shape_per_cp8() -> None:
    """CP8 sub-correction B: severity is owned operator-side via Lynceus's
    ``severity_overrides.yaml``. The export shape MUST NOT emit `severity`."""
    from db.validation import export_lynceus as mod

    # The historical mapping is retained for audit-trail reasoning but is
    # explicitly underscored as a private symbol; future code MUST NOT
    # consult it for output shape decisions.
    assert hasattr(mod, "_DEVICE_CATEGORY_TO_SEVERITY_HISTORICAL")
    assert not hasattr(mod, "DEVICE_CATEGORY_TO_SEVERITY")


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


def test_classify_ble_local_name_drops_section_44_cp13() -> None:
    """CP13: ble_local_name is DROPPED-class (no GAP local-name match in Lynceus v0.3)."""
    bin_label, entries = _classify_row(
        _row(identifier="FlockLPR-A2", identifier_type="ble_local_name",
             device_category="alpr", manufacturer="Flock Safety", confidence=82),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "ble_local_name"
    assert entries == []


def test_classify_ble_local_name_drops_in_high_conf_too() -> None:
    """CP13 type-drop fires above the confidence-floor gate per priority order:
    a high-conf ble_local_name still drops to its type bin, never to
    `below_confidence_threshold` and never as a survivor."""
    bin_label, entries = _classify_row(
        _row(identifier="FlockLPR-A2", identifier_type="ble_local_name",
             device_category="alpr", manufacturer="Flock Safety", confidence=85),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
    )
    assert bin_label == "ble_local_name"
    assert entries == []


def test_classify_ble_characteristic_drops_section_44_cp13() -> None:
    """CP13: ble_characteristic is DROPPED-class (Lynceus discovers by service
    UUID, not characteristic)."""
    bin_label, entries = _classify_row(
        _row(identifier="0000aaaa-0000-1000-8000-00805f9b34fb",
             identifier_type="ble_characteristic",
             device_category="alpr", manufacturer="Flock Safety", confidence=87),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "ble_characteristic"
    assert entries == []


def test_classify_ble_characteristic_drops_in_high_conf_too() -> None:
    bin_label, _ = _classify_row(
        _row(identifier="0000aaaa-0000-1000-8000-00805f9b34fb",
             identifier_type="ble_characteristic",
             device_category="alpr", manufacturer="Flock Safety", confidence=87),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
    )
    assert bin_label == "ble_characteristic"


def test_classify_product_family_codename_drops_section_44_cp13() -> None:
    """CP13: product_family_codename is DROPPED-class (vendor-internal taxonomy
    / cohort strings, e.g. Flock `DeviceType` enum values)."""
    bin_label, entries = _classify_row(
        _row(identifier="WingmanCondor", identifier_type="product_family_codename",
             device_category="alpr", manufacturer="Flock Safety", confidence=92),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "product_family_codename"
    assert entries == []


def test_classify_product_family_codename_drops_in_high_conf_too() -> None:
    bin_label, _ = _classify_row(
        _row(identifier="WingmanCondor", identifier_type="product_family_codename",
             device_category="alpr", manufacturer="Flock Safety", confidence=92),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
    )
    assert bin_label == "product_family_codename"


def test_classify_cp13_type_drops_above_unknown_category_below_procurement() -> None:
    """Priority order regression: CP13 type-drop bins sit BELOW procurement_only
    and unknown_category but ABOVE confidence-floor / self-exclude. A row that's
    BOTH ble_characteristic AND unknown_category drops to unknown_category;
    a row that's BOTH ble_characteristic AND procurement drops to procurement_only."""
    # ble_characteristic + unknown_category → unknown_category (priority 2 wins).
    bin_label, _ = _classify_row(
        _row(identifier_type="ble_characteristic", device_category="unknown",
             confidence=87),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "unknown_category"
    # ble_characteristic + procurement → procurement_only (priority 1 wins).
    bin_label, _ = _classify_row(
        _row(identifier_type="ble_characteristic", source_type="procurement",
             device_category="alpr", confidence=87),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    assert bin_label == "procurement_only"


def test_classify_mac_range_drops_to_oversized_section_44() -> None:
    bin_label, _ = _classify_row(
        _row(identifier="00:50:c2:36:0", identifier_type="mac_range", device_category="alpr"),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
    )
    # mac_range has no Talos pattern_type post-§4.4 (expand-or-drop, but
    # all known active mac_range rows are oversized → drop).
    assert bin_label == "oversized_mac_range"


def test_classify_survivor_alpr_mac_emits_cp8_flat_and_sar10_hash() -> None:
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
    # CP8: flat description form, no severity field.
    assert e.description == "Flock Safety alpr"
    assert not hasattr(e, "severity")
    # SAR-10: argus_record_id is the 16-hex-char hash, not the integer PK.
    assert e.argus_record_id == _sar10_hash("mac", "e4:aa:ea:80:a1:9b")
    assert e.argus_record_id == "eea6f74486eea9c0"
    assert len(e.description) <= DESCRIPTION_MAX_CHARS


# ────────────────────────────────────────────────────────────────────────────
# Description-format gate
# ────────────────────────────────────────────────────────────────────────────


def test_description_cp8_flat_form_for_known_vendor_and_category() -> None:
    desc = _format_description(_row(manufacturer="Flock Safety", device_category="alpr"))
    assert desc == "Flock Safety alpr"
    assert len(desc) <= DESCRIPTION_MAX_CHARS


def test_description_cp8_flat_form_handles_arbitrary_known_pair() -> None:
    desc = _format_description(_row(manufacturer="Acme", device_category="alpr"))
    assert desc == "Acme alpr"
    assert len(desc) <= DESCRIPTION_MAX_CHARS


def test_description_cp8_unattributed_when_vendor_missing() -> None:
    desc = _format_description(_row(manufacturer=None, device_category="alpr"))
    assert desc == DESCRIPTION_VENDOR_UNATTRIBUTED


def test_description_cp8_vendor_unknown_form_when_category_unknown() -> None:
    """CP8 fallback: vendor known + category unknown → ``"{vendor} unknown"``.
    In practice §11 #13 drops device_category='unknown' before reaching
    `_format_description`, but the function ladder must implement the form."""
    desc = _format_description(_row(manufacturer="Acme", device_category="unknown"))
    assert desc == "Acme unknown"


def test_description_long_vendor_falls_back_to_unattributed_per_cp8() -> None:
    """Defense-in-depth: a synthetic 100-char vendor name overflows the 80-char
    ceiling for `{vendor} {category}`. The CP8 ladder falls back to
    `Unattributed identifier` rather than halting (the classifier still
    halts via `_classify_row` length check as a backstop). In real §2.1
    data this path is unreachable — all current vendor names + categories
    fit within 80 chars."""
    long_vendor = "X" * 100
    desc = _format_description(_row(manufacturer=long_vendor, device_category="alpr"))
    assert desc == DESCRIPTION_VENDOR_UNATTRIBUTED
    assert len(desc) <= DESCRIPTION_MAX_CHARS


def test_classify_halts_when_description_exceeds_80_chars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive backstop: if `_format_description` ever returns a >80-char
    string (would require both seed corruption AND fallback malfunction), the
    survivor-branch length-check halts the line per §7.5. The fallback chain
    in real code is unreachable with valid §4.1 enum values, but this gate
    is wired regardless."""
    import db.validation.export_lynceus as mod

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
             device_category="alpr", manufacturer="Flock Safety", confidence=60,
             geographic_scope="US"),
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
    assert payload["_meta"]["dropped_in_export"]["geographic_scope_mismatch"] == 0
    assert payload["_meta"]["geographic_scope_filter"] == ["US"]
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["argus_record_id"] == _sar10_hash(
        "mac", "e4:aa:ea:80:a1:9b"
    )
    assert "severity" not in payload["entries"][0]
    assert assignments == {20: "unknown_category", 21: None}


def test_build_export_meta_carries_cp13_drop_bins() -> None:
    """CP13: `_meta.dropped_in_export` must carry keys for the three new
    Wave G analytical-only types so MAC-45 reconciliation lines up
    bin-for-bin against the writer's tally."""
    rows = [
        _row(id=70, identifier="FlockLPR-A2", identifier_type="ble_local_name",
             device_category="alpr", manufacturer="Flock Safety", confidence=82,
             geographic_scope="US"),
        _row(id=71, identifier="0000aaaa-0000-1000-8000-00805f9b34fb",
             identifier_type="ble_characteristic", device_category="alpr",
             manufacturer="Flock Safety", confidence=87, geographic_scope="US"),
        _row(id=72, identifier="WingmanCondor", identifier_type="product_family_codename",
             device_category="alpr", manufacturer="Flock Safety", confidence=92,
             geographic_scope="US"),
    ]
    payload, assignments = _build_export(
        rows=rows,
        file_label="argus_export.json",
        confidence_threshold=30,
        apply_pi_self_exclude=False,
        schema_version=9,
        argus_run_id="abc",
        exported_at="2026-05-10T00:00:00Z",
        expected_drop_assignments={
            "70": "ble_local_name",
            "71": "ble_characteristic",
            "72": "product_family_codename",
        },
    )
    bins = payload["_meta"]["dropped_in_export"]
    assert bins["ble_local_name"] == 1
    assert bins["ble_characteristic"] == 1
    assert bins["product_family_codename"] == 1
    assert payload["_meta"]["record_count"] == 0
    assert payload["entries"] == []
    assert assignments == {
        70: "ble_local_name",
        71: "ble_characteristic",
        72: "product_family_codename",
    }


def test_build_export_cp13_rows_never_appear_in_entries() -> None:
    """CP13: a survivor `ble_service` row coexisting with CP13 DROPPED-class
    rows must produce exactly the survivor in `entries[]`. The CP13 rows
    must never bleed into the Lynceus pattern table — analytical-only."""
    rows = [
        # Survivor: ble_service is a proper Lynceus pattern_type.
        _row(id=80, identifier="0000fd6f-0000-1000-8000-00805f9b34fb",
             identifier_type="ble_service", device_category="alpr",
             manufacturer="Flock Safety", confidence=87, geographic_scope="US"),
        # All three CP13 DROPPED-class types.
        _row(id=81, identifier="FlockLPR-A2", identifier_type="ble_local_name",
             device_category="alpr", manufacturer="Flock Safety", confidence=82,
             geographic_scope="US"),
        _row(id=82, identifier="0000aaaa-0000-1000-8000-00805f9b34fb",
             identifier_type="ble_characteristic", device_category="alpr",
             manufacturer="Flock Safety", confidence=87, geographic_scope="US"),
        _row(id=83, identifier="WingmanCondor", identifier_type="product_family_codename",
             device_category="alpr", manufacturer="Flock Safety", confidence=92,
             geographic_scope="US"),
    ]
    payload, _ = _build_export(
        rows=rows,
        file_label="argus_export_high_confidence.json",
        confidence_threshold=70,
        apply_pi_self_exclude=True,
        schema_version=9,
        argus_run_id="abc",
        exported_at="2026-05-10T00:00:00Z",
        expected_drop_assignments={
            "81": "ble_local_name",
            "82": "ble_characteristic",
            "83": "product_family_codename",
        },
    )
    assert payload["_meta"]["record_count"] == 1
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["pattern_type"] == "ble_uuid"
    # CP13 rows must never appear in entries; only ble_service survives.
    cp13_identifiers = {"FlockLPR-A2", "0000aaaa-0000-1000-8000-00805f9b34fb", "WingmanCondor"}
    for entry in payload["entries"]:
        assert entry["pattern"] not in cp13_identifiers


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
# CP7 — geographic_scope export-time filter
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "scope,is_high,filter_codes,expected",
    [
        # `global` passes both files unconditionally.
        ("global", False, ("US",), True),
        ("global", True, ("US",), True),
        ("global", True, ("NL",), True),
        # ISO match passes; mismatch fails.
        ("US", False, ("US",), True),
        ("US", True, ("US",), True),
        ("US", False, ("NL",), False),
        ("US", True, ("NL",), False),
        # `unknown` / NULL: passes standard, fails high-confidence.
        ("unknown", False, ("US",), True),
        ("unknown", True, ("US",), False),
        (None, False, ("US",), True),
        (None, True, ("US",), False),
        # Comma-sep ISO list in row + filter.
        ("EU,GB", False, ("GB",), True),
        ("EU,GB", True, ("FR",), False),
    ],
)
def test_passes_geographic_scope_cp7(
    scope: str | None,
    is_high: bool,
    filter_codes: tuple[str, ...],
    expected: bool,
) -> None:
    row = _row(geographic_scope=scope)
    assert (
        _passes_geographic_scope(
            row, geographic_scope_filter=filter_codes, is_high_confidence=is_high
        )
        == expected
    )


def test_default_geographic_scope_filter_is_us() -> None:
    assert DEFAULT_GEOGRAPHIC_SCOPE_FILTER == ("US",)


def test_build_export_drops_to_geographic_scope_mismatch_for_non_us() -> None:
    """A NL-scoped row under default `["US"]` filter drops to mismatch bin."""
    rows = [
        _row(id=30, identifier="e4:aa:ea:80:a1:9b", identifier_type="mac",
             device_category="alpr", manufacturer="Flock Safety",
             confidence=80, geographic_scope="NL"),
    ]
    payload, assignments = _build_export(
        rows=rows,
        file_label="argus_export.json",
        confidence_threshold=30,
        apply_pi_self_exclude=False,
        schema_version=8,
        argus_run_id="abc",
        exported_at="2026-01-01T00:00:00Z",
        expected_drop_assignments={},  # static gates pass; CP7 is post-recon.
        geographic_scope_filter=("US",),
    )
    assert payload["_meta"]["dropped_in_export"]["geographic_scope_mismatch"] == 1
    assert payload["_meta"]["record_count"] == 0
    assert payload["entries"] == []
    assert assignments[30] == "geographic_scope_mismatch"


def test_build_export_global_scope_passes_all_files() -> None:
    """A `global`-scoped row under default `["US"]` filter survives both files."""
    rows = [
        _row(id=40, identifier="e4:aa:ea:80:a1:9b", identifier_type="mac",
             device_category="alpr", manufacturer="Flock Safety",
             confidence=80, geographic_scope="global"),
    ]
    standard_payload, _ = _build_export(
        rows=rows, file_label="argus_export.json", confidence_threshold=30,
        apply_pi_self_exclude=False, schema_version=8, argus_run_id="abc",
        exported_at="2026-01-01T00:00:00Z",
        expected_drop_assignments={}, geographic_scope_filter=("US",),
    )
    high_payload, _ = _build_export(
        rows=rows, file_label="argus_export_high_confidence.json",
        confidence_threshold=70, apply_pi_self_exclude=True,
        schema_version=8, argus_run_id="abc",
        exported_at="2026-01-01T00:00:00Z",
        expected_drop_assignments={}, geographic_scope_filter=("US",),
    )
    assert standard_payload["_meta"]["record_count"] == 1
    assert high_payload["_meta"]["record_count"] == 1
    assert standard_payload["_meta"]["dropped_in_export"]["geographic_scope_mismatch"] == 0
    assert high_payload["_meta"]["dropped_in_export"]["geographic_scope_mismatch"] == 0


def test_build_export_unknown_scope_high_conf_drops_per_cp7() -> None:
    """A NULL-scoped row passes standard but drops in high-confidence."""
    rows = [
        _row(id=50, identifier="e4:aa:ea:80:a1:9b", identifier_type="mac",
             device_category="alpr", manufacturer="Flock Safety",
             confidence=80, geographic_scope=None),
    ]
    standard_payload, _ = _build_export(
        rows=rows, file_label="argus_export.json", confidence_threshold=30,
        apply_pi_self_exclude=False, schema_version=8, argus_run_id="abc",
        exported_at="2026-01-01T00:00:00Z",
        expected_drop_assignments={}, geographic_scope_filter=("US",),
    )
    high_payload, _ = _build_export(
        rows=rows, file_label="argus_export_high_confidence.json",
        confidence_threshold=70, apply_pi_self_exclude=True,
        schema_version=8, argus_run_id="abc",
        exported_at="2026-01-01T00:00:00Z",
        expected_drop_assignments={}, geographic_scope_filter=("US",),
    )
    assert standard_payload["_meta"]["record_count"] == 1
    assert standard_payload["_meta"]["dropped_in_export"]["geographic_scope_mismatch"] == 0
    assert high_payload["_meta"]["record_count"] == 0
    assert high_payload["_meta"]["dropped_in_export"]["geographic_scope_mismatch"] == 1


# ────────────────────────────────────────────────────────────────────────────
# CP19 — source_type exclusion on high-confidence export
# ────────────────────────────────────────────────────────────────────────────


def test_excluded_source_types_constant_is_inferred_and_crowdsourced() -> None:
    """CP19 (§7.5): the set is exactly {'inferred', 'crowdsourced'} per the
    bible amendment. Mirrors the IDENTIFIER_TYPE_TO_PATTERN_TYPE.keys()
    set-assertion pattern (S.1 architectural invariant) — a future change to
    EXCLUDED_SOURCE_TYPES is a stop-the-line event for the export contract."""
    assert EXCLUDED_SOURCE_TYPES == frozenset({"inferred", "crowdsourced"})


def test_classify_excluded_source_type_drops_for_high_conf() -> None:
    """A row with `source_type='crowdsourced'` AND conf>=70 AND every other
    static gate passing drops to `excluded_source_type` in the high-conf file."""
    bin_label, entries = _classify_row(
        _row(source_type="crowdsourced", confidence=75, device_category="alpr"),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
        apply_excluded_source_type=True,
    )
    assert bin_label == "excluded_source_type"
    assert entries == []


def test_classify_excluded_source_type_drops_inferred_too() -> None:
    """`source_type='inferred'` falls into the same bin per CP19."""
    bin_label, _ = _classify_row(
        _row(source_type="inferred", confidence=85, device_category="alpr"),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
        apply_excluded_source_type=True,
    )
    assert bin_label == "excluded_source_type"


def test_classify_excluded_source_type_passes_in_standard_export() -> None:
    """CP19 is high-conf only: standard export passes crowdsourced/inferred
    through. The `apply_excluded_source_type=False` (default) ensures parity
    with pre-CP19 behavior on the standard export."""
    bin_label, entries = _classify_row(
        _row(source_type="crowdsourced", confidence=75, device_category="alpr",
             manufacturer="Acme"),
        confidence_threshold=30,
        apply_pi_self_exclude=False,
        apply_excluded_source_type=False,
    )
    assert bin_label is None
    assert len(entries) == 1


def test_classify_excluded_source_type_priority_below_confidence() -> None:
    """Priority order: a crowdsourced row with conf<70 attributes the drop
    to `below_confidence_threshold` (the more specific reason), NOT to
    `excluded_source_type`. The CP19 bin only catches rows that would have
    survived every prior gate."""
    bin_label, _ = _classify_row(
        _row(source_type="crowdsourced", confidence=50, device_category="alpr"),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
        apply_excluded_source_type=True,
    )
    assert bin_label == "below_confidence_threshold"


def test_classify_excluded_source_type_priority_below_unknown_category() -> None:
    """A crowdsourced row with `device_category='unknown'` attributes the
    drop to `unknown_category` (§11 #13 takes priority over CP19)."""
    bin_label, _ = _classify_row(
        _row(source_type="crowdsourced", confidence=75, device_category="unknown"),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
        apply_excluded_source_type=True,
    )
    assert bin_label == "unknown_category"


def test_build_export_high_conf_drops_crowdsourced_per_cp19() -> None:
    """End-to-end through `_build_export`: a crowdsourced row at conf=75
    drops to `excluded_source_type` in high-conf but survives in standard."""
    rows = [
        _row(id=600, identifier="e4:aa:ea:80:a1:9b", identifier_type="mac",
             device_category="alpr", manufacturer="Flock Safety",
             source_type="crowdsourced", confidence=75, geographic_scope="US"),
    ]
    high_payload, high_assignments = _build_export(
        rows=rows,
        file_label="argus_export_high_confidence.json",
        confidence_threshold=70,
        apply_pi_self_exclude=True,
        schema_version=17,
        argus_run_id="abc",
        exported_at="2026-05-13T00:00:00Z",
        expected_drop_assignments={"600": "excluded_source_type"},
        apply_excluded_source_type=True,
    )
    assert high_payload["_meta"]["record_count"] == 0
    assert high_payload["_meta"]["dropped_in_export"]["excluded_source_type"] == 1
    assert high_assignments[600] == "excluded_source_type"

    standard_payload, standard_assignments = _build_export(
        rows=rows,
        file_label="argus_export.json",
        confidence_threshold=30,
        apply_pi_self_exclude=False,
        schema_version=17,
        argus_run_id="abc",
        exported_at="2026-05-13T00:00:00Z",
        expected_drop_assignments={},
        apply_excluded_source_type=False,
    )
    assert standard_payload["_meta"]["record_count"] == 1
    assert standard_payload["_meta"]["dropped_in_export"]["excluded_source_type"] == 0
    assert standard_assignments[600] is None


def test_build_export_meta_carries_excluded_source_type_key_in_both_files() -> None:
    """CP19 contract: the `dropped_in_export` block carries the
    `excluded_source_type` key in BOTH files (zero in standard, populated in
    high-conf). Parallel dict shape simplifies downstream reconciliation
    arithmetic and matches the existing `geographic_scope_mismatch` pattern."""
    rows = [
        _row(id=601, identifier="e4:aa:ea:80:a1:9c", identifier_type="mac",
             device_category="alpr", manufacturer="Acme",
             source_type="manufacturer_doc", confidence=85,
             geographic_scope="US"),
    ]
    standard_payload, _ = _build_export(
        rows=rows, file_label="argus_export.json", confidence_threshold=30,
        apply_pi_self_exclude=False, schema_version=17, argus_run_id="abc",
        exported_at="2026-05-13T00:00:00Z",
        expected_drop_assignments={}, apply_excluded_source_type=False,
    )
    high_payload, _ = _build_export(
        rows=rows, file_label="argus_export_high_confidence.json",
        confidence_threshold=70, apply_pi_self_exclude=True, schema_version=17,
        argus_run_id="abc", exported_at="2026-05-13T00:00:00Z",
        expected_drop_assignments={}, apply_excluded_source_type=True,
    )
    assert "excluded_source_type" in standard_payload["_meta"]["dropped_in_export"]
    assert "excluded_source_type" in high_payload["_meta"]["dropped_in_export"]
    assert standard_payload["_meta"]["dropped_in_export"]["excluded_source_type"] == 0
    assert high_payload["_meta"]["dropped_in_export"]["excluded_source_type"] == 0


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
    # Wave-A canonical row — mirrors the real db/argus.db id=1 (first_seen
    # populated, last_verified NULL — see MAC-51 deliverable note on the
    # MAC-22-era last_verified discrepancy).
    con.execute(
        "INSERT INTO identifiers (id, identifier, identifier_type, "
        "device_category, manufacturer, confidence, source_url, source_type, "
        "geographic_scope, first_seen, last_verified) "
        "VALUES (1, 'e4:aa:ea:80:a1:9b', 'mac', 'alpr', 'Flock Safety', "
        "60, 'http://e', 'crowdsourced', 'US', "
        "'2026-05-06 00:30:28', NULL)"
    )
    con.execute(
        "INSERT INTO identifiers (id, identifier, identifier_type, "
        "device_category, manufacturer, confidence, source_url, source_type, "
        "geographic_scope) "
        "VALUES (2, '00:04:7d', 'oui', 'unknown', 'Motorola Solutions', "
        "55, 'http://e', 'inferred', 'global')"
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
                        "geographic_scope_mismatch": 0,
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
                        "geographic_scope_mismatch": 0,
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
    assert standard["_meta"]["geographic_scope_filter"] == ["US"]
    assert "geographic_scope_mismatch" in standard["_meta"]["dropped_in_export"]
    assert len(standard["entries"]) == 1
    # SAR-10 hash, not integer PK.
    assert standard["entries"][0]["argus_record_id"] == _sar10_hash(
        "mac", "e4:aa:ea:80:a1:9b"
    )
    assert standard["entries"][0]["pattern_type"] == "mac"
    # CP8: severity dropped from output shape.
    assert "severity" not in standard["entries"][0]
    # CP8: flat description form.
    assert standard["entries"][0]["description"] == "Flock Safety alpr"

    high = json.loads((exports_dir / "argus_export_high_confidence.json").read_text())
    assert high["_meta"]["record_count"] == 0
    assert high["_meta"]["confidence_threshold"] == 70
    assert high["_meta"]["geographic_scope_filter"] == ["US"]
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


# ────────────────────────────────────────────────────────────────────────────
# CP11 — argus_export.csv 15-column expansion (Lynceus rich-import feed)
# ────────────────────────────────────────────────────────────────────────────

CP11_CSV_FIELD_ORDER: tuple[str, ...] = (
    "argus_record_id",
    "id",
    "identifier",
    "identifier_type",
    "device_category",
    "manufacturer",
    "model",
    "confidence",
    "source_type",
    "source_url",
    "source_excerpt",
    "geographic_scope",
    "description",
    "first_seen",
    "last_verified",
    "notes",
)


def _make_cp11_synthetic_db(tmp_path: Path) -> Path:
    """Three-row fixture for CP11 verification clause #1 (Wave-A MAC + 2 OUIs)."""

    db_path = tmp_path / "argus.db"
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA_DDL)
    con.execute(
        "INSERT INTO identifiers (id, identifier, identifier_type, "
        "device_category, manufacturer, confidence, source_url, source_type, "
        "geographic_scope, first_seen, last_verified) "
        "VALUES (1, 'e4:aa:ea:80:a1:9b', 'mac', 'alpr', 'Flock Safety', "
        "60, 'http://e', 'crowdsourced', 'US', "
        "'2026-05-06 00:30:28', NULL)"
    )
    con.execute(
        "INSERT INTO identifiers (id, identifier, identifier_type, "
        "device_category, manufacturer, confidence, source_url, source_type, "
        "geographic_scope) "
        "VALUES (2, '00:04:7d', 'oui', 'unknown', 'Motorola Solutions', "
        "55, 'http://e', 'inferred', 'global')"
    )
    con.execute(
        "INSERT INTO identifiers (id, identifier, identifier_type, "
        "device_category, manufacturer, confidence, source_url, source_type, "
        "geographic_scope) "
        "VALUES (3, 'b8:27:eb', 'oui', 'unknown', 'Raspberry Pi Foundation', "
        "70, 'http://e', 'official', 'global')"
    )
    con.commit()
    con.close()
    return db_path


def _make_cp11_synthetic_mac45(tmp_path: Path) -> tuple[Path, Path]:
    """MAC-45 reconciliation map for the 3-row CP11 fixture."""

    matrix_md_path = tmp_path / "coverage_matrix.md"
    matrix_md_path.write_text("# matrix seed\n", encoding="utf-8")
    report_path = tmp_path / "coverage_matrix_report.json"
    report_path.write_text(
        json.dumps(
            {
                "drop_tally_standard": {
                    "drop_assignments": {
                        "2": "unknown_category",
                        "3": "unknown_category",
                    },
                    "bins": {
                        "unknown_category": 2,
                        "procurement_only": 0,
                        "self_exclude_oui": 0,
                        "below_confidence_threshold": 0,
                        "oversized_mac_range": 0,
                        "ssid_pattern": 0,
                        "device_fingerprint": 0,
                        "geographic_scope_mismatch": 0,
                    },
                    "survivors": 1,
                    "reconciles": 3,
                },
                "drop_tally_high_confidence": {
                    "drop_assignments": {
                        "1": "below_confidence_threshold",
                        "2": "unknown_category",
                        "3": "unknown_category",
                    },
                    "bins": {
                        "unknown_category": 2,
                        "procurement_only": 0,
                        "self_exclude_oui": 0,
                        "below_confidence_threshold": 1,
                        "oversized_mac_range": 0,
                        "ssid_pattern": 0,
                        "device_fingerprint": 0,
                        "geographic_scope_mismatch": 0,
                    },
                    "survivors": 0,
                    "reconciles": 3,
                },
            }
        ),
        encoding="utf-8",
    )
    return report_path, matrix_md_path


def _read_cp11_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Return (header, rows) from the CSV, skipping the leading meta comment."""

    import csv as _csv

    with path.open("r", encoding="utf-8", newline="") as fh:
        first = fh.readline()
        assert first.startswith("# meta:"), f"expected meta line, got {first!r}"
        reader = _csv.DictReader(fh)
        assert reader.fieldnames is not None
        return list(reader.fieldnames), list(reader)


def test_csv_header_is_cp11_15_columns_in_order(tmp_path: Path) -> None:
    """CP11 verification clause #1: CSV header row contains exactly 15 columns
    in the CP11-specified order. (Counting non-`notes` semantic columns; `notes`
    rides at the tail per the existing pattern, total 16 incl. notes.)"""

    db_path = _make_cp11_synthetic_db(tmp_path)
    report_path, matrix_md_path = _make_cp11_synthetic_mac45(tmp_path)
    exports_dir = tmp_path / "exports"
    run(
        db_path=db_path,
        exports_dir=exports_dir,
        coverage_matrix_report_path=report_path,
        coverage_matrix_md_path=matrix_md_path,
    )

    header, _ = _read_cp11_csv(exports_dir / "argus_export.csv")
    assert tuple(header) == CP11_CSV_FIELD_ORDER
    # CP11 sub-A directive specifies 15 NEW/EXISTING semantic columns; `notes`
    # rides at the end of the row (16 total). The 15 enumerated:
    cp11_enumerated = [c for c in CP11_CSV_FIELD_ORDER if c != "notes"]
    assert len(cp11_enumerated) == 15


def test_csv_argus_record_id_byte_stable_for_three_rows(tmp_path: Path) -> None:
    """CP11 verification clause #1 (sample 3 rows incl. Wave-A Flock MAC + 2 OUIs):
    each CSV row's `argus_record_id` matches `argus_record_id(type, identifier)`
    byte-for-byte."""

    db_path = _make_cp11_synthetic_db(tmp_path)
    report_path, matrix_md_path = _make_cp11_synthetic_mac45(tmp_path)
    exports_dir = tmp_path / "exports"
    run(
        db_path=db_path,
        exports_dir=exports_dir,
        coverage_matrix_report_path=report_path,
        coverage_matrix_md_path=matrix_md_path,
    )

    _, csv_rows = _read_cp11_csv(exports_dir / "argus_export.csv")
    assert len(csv_rows) == 3
    by_id = {row["id"]: row for row in csv_rows}

    # Wave-A Flock MAC: SAR-10 hash matches the canonical value asserted in
    # `test_classify_survivor_alpr_mac_emits_cp8_flat_and_sar10_hash`.
    assert by_id["1"]["argus_record_id"] == _sar10_hash("mac", "e4:aa:ea:80:a1:9b")
    assert by_id["1"]["argus_record_id"] == "eea6f74486eea9c0"
    # Motorola OUI.
    assert by_id["2"]["argus_record_id"] == _sar10_hash("oui", "00:04:7d")
    # Raspberry Pi OUI.
    assert by_id["3"]["argus_record_id"] == _sar10_hash("oui", "b8:27:eb")


def test_csv_description_byte_stable_for_three_rows(tmp_path: Path) -> None:
    """CP11 verification clause #1: each CSV row's `description` matches
    `_format_description(row)` byte-for-byte for the 3-row sample."""

    db_path = _make_cp11_synthetic_db(tmp_path)
    report_path, matrix_md_path = _make_cp11_synthetic_mac45(tmp_path)
    exports_dir = tmp_path / "exports"
    run(
        db_path=db_path,
        exports_dir=exports_dir,
        coverage_matrix_report_path=report_path,
        coverage_matrix_md_path=matrix_md_path,
    )

    _, csv_rows = _read_cp11_csv(exports_dir / "argus_export.csv")
    by_id = {row["id"]: row for row in csv_rows}

    # Wave-A Flock MAC — vendor + alpr → "Flock Safety alpr" (CP8 flat).
    assert by_id["1"]["description"] == _format_description(
        _row(manufacturer="Flock Safety", device_category="alpr")
    )
    assert by_id["1"]["description"] == "Flock Safety alpr"
    # Motorola OUI — vendor + unknown → "{vendor} unknown" (CP8 sub-A ladder).
    assert by_id["2"]["description"] == _format_description(
        _row(manufacturer="Motorola Solutions", device_category="unknown")
    )
    assert by_id["2"]["description"] == "Motorola Solutions unknown"
    # Raspberry Pi OUI — same ladder.
    assert by_id["3"]["description"] == _format_description(
        _row(manufacturer="Raspberry Pi Foundation", device_category="unknown")
    )
    assert by_id["3"]["description"] == "Raspberry Pi Foundation unknown"


def test_csv_first_seen_non_empty_for_wave_a_row(tmp_path: Path) -> None:
    """CP11 verification clause #1: `first_seen` is non-empty for the Wave-A
    row.

    Note (MAC-51 procedural): the dispatch claimed the Wave-A row also has a
    confirmed `last_verified` from the MAC-22 era; the current `db/argus.db`
    state shows `last_verified IS NULL` for ALL 63 active rows (including
    Wave-A). The test asserts the actual DB state — `first_seen` non-empty,
    `last_verified` empty-string — and does NOT regress on a missing column.
    Surfaced in the deliverable comment for CEO follow-up."""

    db_path = _make_cp11_synthetic_db(tmp_path)
    report_path, matrix_md_path = _make_cp11_synthetic_mac45(tmp_path)
    exports_dir = tmp_path / "exports"
    run(
        db_path=db_path,
        exports_dir=exports_dir,
        coverage_matrix_report_path=report_path,
        coverage_matrix_md_path=matrix_md_path,
    )

    _, csv_rows = _read_cp11_csv(exports_dir / "argus_export.csv")
    wave_a = next(row for row in csv_rows if row["id"] == "1")
    assert wave_a["first_seen"] == "2026-05-06 00:30:28"
    # NULL → "" per the existing `manufacturer or ""` handling pattern.
    assert wave_a["last_verified"] == ""
    # Other rows: both NULL → both empty.
    other_rows = [row for row in csv_rows if row["id"] != "1"]
    for row in other_rows:
        assert row["first_seen"] == ""
        assert row["last_verified"] == ""


def test_csv_description_matches_json_description_single_source_of_truth(
    tmp_path: Path,
) -> None:
    """CP11 single-source-of-truth: the CSV `description` column and the JSON
    `entries[].description` field MUST be byte-identical for any row that
    survives to both feeds. Both call `_format_description(row)`; this test
    cements the contract."""

    db_path = _make_cp11_synthetic_db(tmp_path)
    report_path, matrix_md_path = _make_cp11_synthetic_mac45(tmp_path)
    exports_dir = tmp_path / "exports"
    run(
        db_path=db_path,
        exports_dir=exports_dir,
        coverage_matrix_report_path=report_path,
        coverage_matrix_md_path=matrix_md_path,
    )

    _, csv_rows = _read_cp11_csv(exports_dir / "argus_export.csv")
    json_payload = json.loads((exports_dir / "argus_export.json").read_text())
    json_by_arid = {e["argus_record_id"]: e for e in json_payload["entries"]}

    matched = 0
    for csv_row in csv_rows:
        arid = csv_row["argus_record_id"]
        if arid in json_by_arid:
            assert csv_row["description"] == json_by_arid[arid]["description"], (
                f"CSV description {csv_row['description']!r} != JSON description "
                f"{json_by_arid[arid]['description']!r} for argus_record_id={arid}"
            )
            matched += 1
    # Wave-A Flock MAC survives to JSON; assert at least one match made.
    assert matched >= 1


def test_coverage_report_has_lynceus_dual_artifact_section(tmp_path: Path) -> None:
    """CP11 sub-B: coverage_report.md carries the
    'Lynceus integration: dual-artifact contract (CP11)' section."""

    db_path = _make_cp11_synthetic_db(tmp_path)
    report_path, matrix_md_path = _make_cp11_synthetic_mac45(tmp_path)
    exports_dir = tmp_path / "exports"
    run(
        db_path=db_path,
        exports_dir=exports_dir,
        coverage_matrix_report_path=report_path,
        coverage_matrix_md_path=matrix_md_path,
    )

    coverage = (exports_dir / "coverage_report.md").read_text()
    assert "## Lynceus integration: dual-artifact contract (CP11)" in coverage
    assert "operational alert feed" in coverage
    assert "rich-import feed" in coverage
    assert "no lossy conversion" in coverage
    assert "fcc_id` deferred to v1.1" in coverage
