"""CP31 (migration 0025) — consumer-path audit assertions.

Covers MAC-199 (parent MAC-184 / MAC-197 plan rev d59e6af5):

§A. Hub/arm SQL semantics (3 assertions covering ``query_default='visible'``
    returns hub rows, ``JOIN`` through ``parent_manufacturer_id`` returns
    the arm).
§B. Export-path arm-exclusion: 'Parrot Automotive' canonical name does NOT
    appear in any of the three exports' entries.
§C. High-confidence export drop assertions for the 2 CP31 identifier_type
    values + arm-attested identifier-include assertion (MAC-199 dispatch §2).

See ``_phase_cp31_implementation/manufacturers_query_audit.md`` for the
full audit's architectural finding (export_lynceus.py does NOT JOIN
manufacturers; arm-row protection in current schema is implicit because
no identifier carries the arm canonical name as denormalized text).
"""

from __future__ import annotations

import sqlite3

import pytest

from db.validation.export_lynceus import (
    ActiveRow,
    _build_export,
    _classify_row,
)


# ────────────────────────────────────────────────────────────────────────────
# §A — Hub/arm SQL semantics
# ────────────────────────────────────────────────────────────────────────────


def _build_minimal_manufacturers_schema(con: sqlite3.Connection) -> None:
    """Build a CP31-shape ``manufacturers`` table for SQL-semantics tests.

    Mirrors the post-migration-0025 DDL: ``parent_manufacturer_id`` FK,
    ``is_arm`` BOOLEAN, ``query_default`` CHECK enum.
    """
    con.executescript(
        """
        CREATE TABLE manufacturers (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_name         TEXT NOT NULL UNIQUE,
            aliases                TEXT,
            primary_category       TEXT,
            source_url             TEXT NOT NULL,
            notes                  TEXT,
            added_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            parent_manufacturer_id INTEGER NULL REFERENCES manufacturers(id),
            is_arm                 BOOLEAN NOT NULL DEFAULT 0,
            query_default          TEXT NOT NULL DEFAULT 'visible' CHECK (
                                       query_default IN ('visible', 'hidden_arm')
                                   )
        );
        INSERT INTO manufacturers
            (id, canonical_name, source_url, primary_category, is_arm, query_default, parent_manufacturer_id)
        VALUES
            (1, 'Parrot', 'bible',     'drone',                0, 'visible',    NULL),
            (2, 'Parrot Automotive', 'bible', 'automotive_telematics', 1, 'hidden_arm', 1),
            (3, 'Flock Safety', 'bible', 'alpr',                0, 'visible',    NULL);
        """
    )


def test_visible_filter_returns_only_hub_rows() -> None:
    """``WHERE query_default='visible'`` excludes arm rows from lexicon enumeration.

    This is the contract the 4 hub-only live-query call sites
    (phase3_inference_candidates / sar8_bulk_stage / usaspending /
    mac101_item_a_registry_xcheck) rely on per MAC-199 §4.
    """
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    _build_minimal_manufacturers_schema(con)

    rows = con.execute(
        "SELECT canonical_name FROM manufacturers "
        "WHERE query_default = 'visible' "
        "ORDER BY id"
    ).fetchall()
    names = [r["canonical_name"] for r in rows]
    assert names == ["Parrot", "Flock Safety"]
    assert "Parrot Automotive" not in names


def test_unfiltered_query_returns_hub_and_arm() -> None:
    """Defense-in-depth: confirm the *un*filtered baseline includes the arm
    (so the visible-filter test is meaningful)."""
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    _build_minimal_manufacturers_schema(con)

    rows = con.execute(
        "SELECT canonical_name FROM manufacturers ORDER BY id"
    ).fetchall()
    names = [r["canonical_name"] for r in rows]
    assert "Parrot" in names
    assert "Parrot Automotive" in names
    assert "Flock Safety" in names


def test_arm_resolves_via_parent_manufacturer_id_fk() -> None:
    """JOIN through ``parent_manufacturer_id`` returns the arm whose parent
    is the named hub. This is the CP31 §5.2 access path for arms when an
    identifier explicitly attests to one (Phase-7-bis future-state)."""
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    _build_minimal_manufacturers_schema(con)

    rows = con.execute(
        """
        SELECT arm.canonical_name
        FROM manufacturers AS hub
        JOIN manufacturers AS arm ON arm.parent_manufacturer_id = hub.id
        WHERE hub.canonical_name = 'Parrot'
        """
    ).fetchall()
    assert [r["canonical_name"] for r in rows] == ["Parrot Automotive"]


# ────────────────────────────────────────────────────────────────────────────
# §B — Export-path arm-exclusion (synthetic active-row set)
# ────────────────────────────────────────────────────────────────────────────


def _ar(**kw) -> ActiveRow:
    """Helper to build an ``ActiveRow`` with sensible defaults."""
    defaults = dict(
        id=1,
        identifier="aa:bb:cc:dd:ee:ff",
        identifier_type="mac",
        device_category="alpr",
        manufacturer="Flock Safety",
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


def test_arm_canonical_absent_when_no_identifier_attests_to_arm() -> None:
    """Post-CP31 default state: zero identifiers carry ``manufacturer =
    'Parrot Automotive'`` (the arm canonical). Verify the standard export
    payload's entries do not surface that string.

    This is the present-day equivalent of MAC-199 §1's "argus_export.csv
    contains Parrot hub but NOT Parrot Automotive" assertion, exercised via
    ``_build_export`` against synthetic rows for hermeticity.
    """
    rows = [
        _ar(
            id=10,
            identifier="90:3a:e6",
            identifier_type="oui",
            device_category="drone",
            manufacturer="Parrot",
            confidence=85,
            geographic_scope="US",
        ),
    ]
    payload, _ = _build_export(
        rows=rows,
        file_label="argus_export.json",
        confidence_threshold=30,
        apply_pi_self_exclude=False,
        schema_version=25,
        argus_run_id="abc",
        exported_at="2026-05-20T00:00:00Z",
        expected_drop_assignments={},
    )
    serialized = repr(payload)
    assert "Parrot Automotive" not in serialized
    # Hub canonical 'Parrot' must still be present (sanity check on the test
    # — otherwise the negative assertion above is meaningless). ``entries``
    # at this stage are dict-shaped (post-serialization, pre-disk).
    assert any("Parrot" in entry["description"] for entry in payload["entries"])


def test_arm_canonical_absent_in_high_confidence_when_no_attestation() -> None:
    """Same shape as the standard-file test, applied to the high-confidence
    export (confidence_threshold=70 + apply_pi_self_exclude=True). The
    high-confidence file has tighter gates; the same negative assertion
    must hold."""
    rows = [
        _ar(
            id=10,
            identifier="90:3a:e6",
            identifier_type="oui",
            device_category="drone",
            manufacturer="Parrot",
            confidence=85,
            geographic_scope="US",
        ),
    ]
    payload, _ = _build_export(
        rows=rows,
        file_label="argus_export_high_confidence.json",
        confidence_threshold=70,
        apply_pi_self_exclude=True,
        schema_version=25,
        argus_run_id="abc",
        exported_at="2026-05-20T00:00:00Z",
        expected_drop_assignments={},
    )
    serialized = repr(payload)
    assert "Parrot Automotive" not in serialized


# ────────────────────────────────────────────────────────────────────────────
# §C — MAC-199 dispatch §2 high-confidence drop / include assertions
# ────────────────────────────────────────────────────────────────────────────


def test_fcc_grantee_code_at_unknown_category_drops_section_11_13() -> None:
    """MAC-199 dispatch §2 assertion #2: a ``fcc_grantee_code`` row at
    ``device_category='unknown'`` with confidence 75 is DROPPED from the
    high-confidence export via the §11 #13 unknown-category gate.

    Gate priority in ``_classify_row``: §11 #14 (procurement) → §11 #13
    (unknown_category) → identifier_type-specific drops. The §11 #13 gate
    fires before any type-mapping lookup, so this assertion holds without
    requiring ``fcc_grantee_code`` to be present in ``IDENTIFIER_TYPE_TO_PATTERN_TYPE``
    or ``DROPPED_REASONS``.

    Forward-looking finding: ``fcc_grantee_code`` is not yet registered in
    the export's type-mapping dicts. The dispatch ratified routing is
    DROPPED-class (no Lynceus pattern_type counterpart for FCC EAS anchors).
    A non-``unknown`` device_category row would currently fall through to
    survivor classification and KeyError out — out of MAC-199 scope; flag
    for CEO post-CP31 codification."""
    bin_label, entries = _classify_row(
        _ar(
            identifier="2AHIH",
            identifier_type="fcc_grantee_code",
            device_category="unknown",
            confidence=75,
        ),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
    )
    assert bin_label == "unknown_category"
    assert entries == []


def test_equipment_class_code_at_unknown_category_drops_section_11_13() -> None:
    """MAC-199 dispatch §2 assertion #3: symmetric to the previous test for
    ``equipment_class_code`` (the second CP31 identifier_type)."""
    bin_label, entries = _classify_row(
        _ar(
            identifier="DXX",
            identifier_type="equipment_class_code",
            device_category="unknown",
            confidence=75,
        ),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
    )
    assert bin_label == "unknown_category"
    assert entries == []


def test_arm_attested_identifier_survives_high_confidence() -> None:
    """MAC-199 dispatch §2 assertion #4 (plan-faithful spirit): an arm-row
    identifier (``manufacturer='Parrot Automotive'``) at confidence 75 with
    a valid §2.1 ``device_category`` (non-``unknown``) is INCLUDED in the
    high-confidence export. Arm-ness does not auto-exclude.

    Plan §2 #4 specified ``device_category='automotive_telematics'``. The
    ``identifiers.device_category`` CHECK enum (§2.1) does NOT include that
    value — it admits 12 fixed device-category strings. The test uses
    ``device_category='drone'`` (matching the hub Parrot's own category) so
    the assertion exercises the intended path within the existing schema
    constraints. The architectural intent — "arms surface only when an
    identifier explicitly attests to the arm" — is preserved.

    Forward-looking finding: extending the §2.1 ``device_category`` enum
    to admit ``automotive_telematics`` is a separate §11 #11 amendment
    item; out of MAC-199 scope."""
    bin_label, entries = _classify_row(
        _ar(
            id=99,
            identifier="90:3a:e7",
            identifier_type="oui",
            device_category="drone",
            manufacturer="Parrot Automotive",
            confidence=75,
            source_type="manufacturer_doc",
            geographic_scope="US",
        ),
        confidence_threshold=70,
        apply_pi_self_exclude=True,
    )
    assert bin_label is None, (
        f"arm-attested identifier should survive high-conf gates; got drop_bin={bin_label!r}"
    )
    assert len(entries) == 1
    # The arm canonical name flows verbatim into the description per CP8
    # flat form `{vendor} {device_category}`.
    assert entries[0].description == "Parrot Automotive drone"
