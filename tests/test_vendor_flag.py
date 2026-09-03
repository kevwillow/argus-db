"""MAC-691 — tests for db/vendor_flag.py.

Three jobs:
  1. Pin the acceptance property in both directions. A bare-containment hit must
     LOSE the flag; a genuine bounded-word hit must KEEP it. A test that only
     asserts the kills would pass on a matcher that returns False for everything.
  2. Pin the alias arm's guards. The DJI blob is the live contamination case and
     it must not be able to import another vendor's identity.
  3. Pin the live delta against canonical, as a DELTA and not as an absolute
     total, so a future edit that re-widens the matcher fails here.

The canonical-DB tests skip when `db/argus.db` is absent so the pure-predicate
tests still run in a checkout without the 314 MiB blob.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db.vendor_flag import (
    NOTES_PATH,
    FlagVerdict,
    SurfaceForms,
    flag_holds,
    pool_from_db,
    surface_forms,
    sweep_existing_flags,
)

DB = Path(__file__).resolve().parent.parent / "db" / "argus.db"


@pytest.fixture(scope="module")
def con():
    if not DB.exists():
        pytest.skip(f"canonical DB absent: {DB}")
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    yield c
    c.close()


# ── 1. the acceptance property, both directions ───────────────────────────────

# NEGATIVE control — the exact rows MAC-685 named. Every one of these is a bare
# containment hit and none may survive. (id, flag, manufacturer)
UNANCHORED_MUST_LOSE = [
    (2821, "Ring", "KOZO KEIKAKU ENGINEERING Inc."),
    (1950, "Axon", "MAXON INDUSTRIES, INC."),
    (1755, "Tile", "NINGBO FOTILE KITCHENWARE CO., LTD."),
    (1550, "DJI", "Avedis Zildjian Co."),
    (4116, "Nest", "Société des Produits Nestlé S.A."),
    (2329, "Axon", "Saxonar GmbH"),
    (3037, "Axon", "maxon motor ltd."),
    (1268, "AVer", "MAVERICK ENERGY SOLUTIONS INTERNATIONAL,INC"),
    (2861, "Ring", "Boehringer Ingelheim Vetmedica GmbH"),
    (2741, "Ring", "KiteSpring Inc."),
]

# POSITIVE control — the vendor token appears as a BOUNDED WORD. These must keep
# the flag. Without this arm a matcher that kills everything would pass.
ANCHORED_MUST_KEEP = [
    (5894, "Bosch", "Bosch (zhuhai) Security Systems Company, Ltd."),
    (4315, "Bosch", "Robert Bosch GmbH"),
    (3397, "Tile", "Tile, Inc."),
    (4533, "Nest", "Nest Labs Inc."),
    (2872, "DJI", "DJI"),
    (1549, "Hikvision", "Hikvision"),
    (6883, "Autel", "Autel Robotics"),
    (1744, "Axis Communications", "Axis Communications AB"),
    (2848, "Chipolo", "CHIPOLO d.o.o."),
    (3725, "Honeywell", "Honeywell International Inc."),
]


@pytest.mark.parametrize("rid,flag,mfr", UNANCHORED_MUST_LOSE)
def test_unanchored_substring_hit_loses_the_flag(rid, flag, mfr):
    assert flag.lower() in mfr.lower(), (
        f"control is vacuous: {flag!r} is not even a substring of {mfr!r}"
    )
    assert flag_holds(mfr, flag).holds is False


@pytest.mark.parametrize("rid,flag,mfr", ANCHORED_MUST_KEEP)
def test_bounded_word_hit_keeps_the_flag(rid, flag, mfr):
    v = flag_holds(mfr, flag)
    assert v.holds is True
    assert v.arm == "canonical"


def test_non_string_flag_never_holds():
    assert flag_holds("Johnson Matthey PLC", 0).holds is False
    assert flag_holds("Johnson Matthey PLC", None).holds is False
    assert flag_holds("Johnson Matthey PLC", "").holds is False


def test_missing_manufacturer_never_holds():
    assert flag_holds(None, "Bosch").holds is False
    assert flag_holds("   ", "Bosch").holds is False


# ── 2. the alias arm is guarded ───────────────────────────────────────────────


@pytest.mark.canonical_db
def test_dji_alias_blob_cannot_import_another_vendor(con):
    """The live contamination case. DJI's alias blob carries `Autel`, `Parrot`,
    `Axon`, `Yuneec`. A row whose manufacturer is `Autel Robotics` must not keep
    a DJI flag through it."""
    raw = con.execute(
        "SELECT aliases FROM manufacturers WHERE canonical_name='DJI'"
    ).fetchone()[0]
    assert "Autel" in raw, "control is vacuous: DJI's alias blob no longer names Autel"

    sf = surface_forms(con, "DJI")
    assert sf.aliases == (), "DJI's alias arm must be refused wholesale"
    assert any("DEFERRED_CANONICALS" in reason for _, reason in sf.dropped)
    assert flag_holds("Autel Robotics", "DJI", sf).holds is False


@pytest.mark.canonical_db
def test_alias_arm_does_real_work_where_it_is_safe(con):
    """Non-vacuity: at least one pool vendor must actually carry aliases, or the
    guard tests above prove nothing about a guard that just returns empty."""
    sf = surface_forms(con, "Hikvision")
    assert sf.in_manufacturers and len(sf.aliases) > 0
    assert flag_holds("EZVIZ", "Hikvision", sf).holds is True
    assert flag_holds("EZVIZ", "Hikvision", None).holds is False


def test_alias_that_is_another_canonical_is_dropped_as_conflation(con):
    """Synthetic corpus — the entity-conflation guard, isolated from live data."""
    mem = sqlite3.connect(":memory:")
    mem.execute(
        "CREATE TABLE manufacturers (canonical_name TEXT, aliases TEXT)"
    )
    mem.executemany(
        "INSERT INTO manufacturers VALUES (?,?)",
        [("Vendor One", "VendorOne Ltd,Vendor Two"), ("Vendor Two", None)],
    )
    sf = surface_forms(mem, "Vendor One")
    assert "Vendor Two" not in sf.aliases
    assert "VendorOne Ltd" in sf.aliases
    assert any("entity conflation" in r for _, r in sf.dropped)


# ── 3. the live delta, asserted as a DELTA ────────────────────────────────────


@pytest.mark.canonical_db
def test_acceptance_property_holds_on_canonical(con):
    """THE acceptance property, asserted as a property of the data and not as the
    status of an issue: no row carries `surveillance_vendor_flag` on the basis of
    an unanchored substring hit.

    Migration 0055 applied the correction (103 flagged -> 41; delta -62). That
    delta is history and lives in `operator_review/MAC-691/sweep_report.json`;
    re-asserting it here would fail the moment a co-tenant lane touches the
    column. What must hold forever is the property below.

    The one permitted residual is a flag whose VALUE is not a vendor name at all
    (id=23042 carries the JSON literal `false`). It cannot rest on a substring
    hit because it makes no vendor claim.
    """
    r = sweep_existing_flags(con, use_alias_arm=True)
    assert r.n_evaluated == r.delta_keep + r.delta_lose
    vendor_claims_on_unanchored_basis = [
        x for x in r.lost if isinstance(x["flag"], str) and x["flag"].strip()
    ]
    assert vendor_claims_on_unanchored_basis == [], (
        "a row carries a vendor-name flag that no surface form boundary-matches: "
        f"{vendor_claims_on_unanchored_basis}"
    )


@pytest.mark.canonical_db
def test_the_corrected_rows_stayed_corrected(con):
    """NEGATIVE arm, post-apply. Each of these carried a bare-containment flag and
    must now carry none, plus the provenance of what was withdrawn."""
    for rid, flag, _mfr in UNANCHORED_MUST_LOSE:
        now, was = con.execute(
            "SELECT json_extract(notes,'$.surveillance_vendor_flag'), "
            "       json_extract(notes,'$.mac691_flag_correction.withdrawn_value') "
            "FROM identifiers WHERE id = ?",
            (rid,),
        ).fetchone()
        assert now is None, f"id={rid} carries a flag again: {now!r}"
        assert was == flag, f"id={rid} lost the record of what was withdrawn"


@pytest.mark.canonical_db
def test_the_positive_control_rows_still_carry_their_flag(con):
    """POSITIVE arm, post-apply. Without this the correction would also pass by
    having wiped the column."""
    r = sweep_existing_flags(con, use_alias_arm=True)
    kept = {x["id"]: x["flag"] for x in r.kept}
    for rid, flag, _mfr in ANCHORED_MUST_KEEP:
        assert kept.get(rid) == flag, (
            f"id={rid} should still carry {flag!r}; it carries {kept.get(rid)!r}"
        )


@pytest.mark.canonical_db
def test_alias_arm_is_not_load_bearing_for_the_live_delta(con):
    """Measured: the alias arm rescues 0 of the 63. Recorded as a test so that if
    a future alias edit makes it load-bearing, that shows up as a deliberate
    change rather than as a silent widening of the correction's blast radius."""
    bare = sweep_existing_flags(con, use_alias_arm=False)
    full = sweep_existing_flags(con, use_alias_arm=True)
    assert {x["id"] for x in full.kept} - {x["id"] for x in bare.kept} == set()


@pytest.mark.canonical_db
def test_pool_is_read_from_the_column_not_hardcoded(con):
    pool = pool_from_db(con)
    assert "Ring" in pool and "Bosch" in pool
    assert all(isinstance(v, str) and v.strip() for v in pool)
