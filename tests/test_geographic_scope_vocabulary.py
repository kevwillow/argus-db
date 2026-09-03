"""MAC-742 — `identifiers.geographic_scope` vocabulary, both halves.

The ratified vocabulary is {ISO-3166 alpha-2, 'global', NULL} (CEO ruling
1c34bdf7-76e2-41f9-9b65-38b56093b240, §0 of
``operator_review/MAC-726/F3_geographic_scope_proposal.md``). It is enforced in
TWO places on purpose, and the split is the point of this file:

    migration 0061  CHECK (... OR geographic_scope GLOB '[A-Z][A-Z]')
                    -- SHAPE. Amending it costs a full table recreate: 43,892
                    -- rows, 7 indexes, 6 FK-referencing tables, an AUTOINCREMENT
                    -- sequence. So it carries only the rule that cannot go
                    -- stale: an ISO-3166 alpha-2 code is two uppercase letters,
                    -- true by definition of the standard.

    this file       the ENUMERATED allow-list.
                    -- Which of the 676 two-letter pairs are actually assigned is
                    -- the volatile half — ISO has revised it (CS, AN, SS) within
                    -- living memory. It belongs where amending it is a one-line
                    -- diff with no data movement.

The residual the CHECK cannot see is ~427 unassigned pairs: 'XX', 'ZZ', 'CB'
have the right shape and are not countries. ``test_active_domain_is_assigned_iso``
is what closes that gap, and it is the reason the CHECK was left permissive
rather than being loaded with 249 tokens.

Also covers the ``--continent-filter`` rollup (MAC-742 item 3).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db.validation.export_lynceus import (
    CONTINENT_ISO3166_ALPHA2,
    DEFAULT_GEOGRAPHIC_SCOPE_FILTER,
    _passes_geographic_scope,
    expand_continent_filter,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "db" / "argus.db"

# ISO-3166-1 alpha-2, currently-assigned. Amend HERE when ISO does, not in the
# migration. Derived as the union of the continent map, which is the same source
# of truth the rollup uses — so a code admissible in the column and a code the
# rollup can produce cannot drift apart.
ASSIGNED_ISO_ALPHA2 = frozenset(
    code for codes in CONTINENT_ISO3166_ALPHA2.values() for code in codes
)

# The non-ISO members of the ratified vocabulary.
NON_ISO_VOCABULARY = frozenset({"global"})


def _scope_domain(where: str = "1=1") -> dict[str | None, int]:
    if not DB_PATH.exists():
        pytest.skip(f"canonical DB absent at {DB_PATH}")
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        return dict(
            con.execute(
                "SELECT geographic_scope, COUNT(*) FROM identifiers "
                f"WHERE {where} GROUP BY 1"
            ).fetchall()
        )
    finally:
        con.close()


def _migration_0061_applied() -> bool:
    """True once the CHECK is on the table in canonical.

    Keyed on the stored DDL — the one thing migration 0061 definitively changes,
    and the same condition its own POST-7 asserts. NOT keyed on the absence of
    'US-CBP': gating the US-CBP regression pin on US-CBP being gone would be a
    guard that can never fail, which is worse than no guard.
    """
    if not DB_PATH.exists():
        return False
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        ddl = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='identifiers'"
        ).fetchone()
        return bool(ddl) and "geographic_scope  TEXT CHECK" in ddl[0]
    finally:
        con.close()


# The three canonical-state assertions below are the POST-apply pins for
# migration 0061. 0061 is STAGED, not applied — the same disposition 0059 and
# 0060 are in — so until the board applies it they would fail against a DB that
# is simply not there yet. They skip on that exact condition and become live the
# moment the migration lands, with no edit required. They are not skipped on
# anything the migration cannot change.
requires_0061 = pytest.mark.skipif(
    not _migration_0061_applied(),
    reason=(
        "migration 0061 (MAC-742) is staged, not applied to db/argus.db. "
        "Apply via operator_review/MAC-742/RUNBOOK.md, then these become live."
    ),
)


# ---------------------------------------------------------------------------
# The enumerated half — what the CHECK's shape rule deliberately cannot enforce.
# ---------------------------------------------------------------------------


@requires_0061
def test_active_domain_is_assigned_iso_or_global_or_null():
    """Every ACTIVE row's scope is NULL, 'global', or an ASSIGNED ISO code.

    This is the assertion the GLOB shape rule cannot make. 'XX' would satisfy
    the CHECK and fail here, which is exactly the division of labour intended.
    """
    domain = _scope_domain("superseded_by IS NULL")
    offenders = {
        value: n
        for value, n in domain.items()
        if value is not None
        and value not in NON_ISO_VOCABULARY
        and value not in ASSIGNED_ISO_ALPHA2
    }
    assert offenders == {}, (
        f"active rows carry scope values outside the ratified vocabulary: {offenders}. "
        "Either the value is wrong, or ISO assigned a new code and "
        "CONTINENT_ISO3166_ALPHA2 needs it."
    )


@requires_0061
def test_whole_table_domain_including_superseded():
    """Same rule over EVERY row, superseded included.

    A CHECK constraint binds every row in the table, not the active slice. A
    superseded row holding a bad value would block a future table recreate and be
    invisible to any active-only assertion — which is how the 'US-CBP' pair
    survived: it was measured against the active denominator only.
    """
    domain = _scope_domain()
    offenders = {
        value: n
        for value, n in domain.items()
        if value is not None
        and value not in NON_ISO_VOCABULARY
        and value not in ASSIGNED_ISO_ALPHA2
    }
    assert offenders == {}, f"non-vocabulary scope values table-wide: {offenders}"


@requires_0061
def test_us_cbp_is_gone():
    """The specific defect MAC-742 carried. Regression pin, by value."""
    assert "US-CBP" not in _scope_domain(), (
        "'US-CBP' is back in identifiers.geographic_scope — an agency string in a "
        "country column. See migration 0061 / MAC-742."
    )


# ---------------------------------------------------------------------------
# The shape half — the predicate the migration's CHECK actually encodes.
# ---------------------------------------------------------------------------


def _check_predicate(value: str | None) -> bool:
    """Python mirror of the migration-0061 CHECK clause."""
    if value is None:
        return True
    if value == "global":
        return True
    return len(value) == 2 and value.isascii() and value.isupper() and value.isalpha()


@pytest.mark.parametrize("bad", ["US-CBP", "us", "USA", "", "U", "U1", "us-cbp", "GLOBAL"])
def test_check_shape_rejects(bad):
    assert not _check_predicate(bad)


@pytest.mark.parametrize("good", ["US", "GB", "DE", "global", None])
def test_check_shape_admits(good):
    assert _check_predicate(good)


def test_every_assigned_iso_code_satisfies_the_check():
    """The allow-list must be a SUBSET of what the CHECK admits.

    If these two ever disagree, a code this file calls valid could not be written
    to the column at all — the layering would be broken rather than merely
    redundant.
    """
    rejected = sorted(c for c in ASSIGNED_ISO_ALPHA2 if not _check_predicate(c))
    assert rejected == [], f"allow-list entries the CHECK would reject: {rejected}"


# ---------------------------------------------------------------------------
# MAC-742 item 3 — the continent rollup.
# ---------------------------------------------------------------------------


def test_continent_map_is_well_formed():
    for continent, codes in CONTINENT_ISO3166_ALPHA2.items():
        assert _check_predicate(continent), f"continent key {continent!r} is not 2 upper alpha"
        assert len(codes) == len(set(codes)), f"{continent} has duplicate members"
        for code in codes:
            assert _check_predicate(code), f"{continent} member {code!r} is not a valid ISO shape"


def test_no_country_belongs_to_two_continents():
    seen: dict[str, str] = {}
    for continent, codes in CONTINENT_ISO3166_ALPHA2.items():
        for code in codes:
            assert code not in seen, (
                f"{code} is in both {seen[code]} and {continent}; the rollup would "
                "double-count it"
            )
            seen[code] = continent


def test_expansion_is_sorted_deduped_and_stable():
    """Byte-stability matters: this tuple lands in the export's `_meta`."""
    once = expand_continent_filter(("EU",))
    assert once == tuple(sorted(set(once)))
    assert once == expand_continent_filter(("EU",))
    # Overlapping requests must not produce duplicates.
    both = expand_continent_filter(("EU", "NA"))
    assert len(both) == len(set(both))
    assert set(both) == set(expand_continent_filter(("EU",))) | set(
        expand_continent_filter(("NA",))
    )


def test_expansion_contains_expected_members():
    assert "GB" in expand_continent_filter(("EU",))
    assert "DE" in expand_continent_filter(("EU",))
    assert "US" in expand_continent_filter(("NA",))
    assert "US" not in expand_continent_filter(("EU",))
    assert "BR" in expand_continent_filter(("SA",))


def test_unknown_continent_raises():
    with pytest.raises(KeyError):
        expand_continent_filter(("XX",))


def test_continent_token_never_reaches_the_row_comparison():
    """The rejected design, pinned as a test.

    A row stamped with a continent token does not match a filter of ISO codes,
    and a row stamped with an ISO code does not match a filter of continent
    tokens. Continent-as-stored-value fails in BOTH directions — which is why the
    rollup expands before `_passes_geographic_scope` is ever called.
    """

    class _Row:
        def __init__(self, scope):
            self.geographic_scope = scope

    # A row stamped 'EU' does not match a filter of European ISO codes.
    assert not _passes_geographic_scope(
        _Row("EU"), geographic_scope_filter=("GB", "DE", "FR"), is_high_confidence=True
    )
    # A row stamped 'DE' does not match a filter of ('EU',).
    assert not _passes_geographic_scope(
        _Row("DE"), geographic_scope_filter=("EU",), is_high_confidence=True
    )
    # But 'DE' DOES match the expansion of ('EU',) — the rollup is what bridges them.
    assert _passes_geographic_scope(
        _Row("DE"),
        geographic_scope_filter=expand_continent_filter(("EU",)),
        is_high_confidence=True,
    )


@pytest.mark.canonical_db
def test_rollup_yield_against_canonical_is_zero():
    """MAC-742 said to build it and be honest that it yields nothing. Measured.

    Not a fixture: this asks canonical directly. If it ever fails, the registry
    has acquired its first non-US geography-gated row and the parameter has
    stopped being theoretical — which is a result worth failing a test to
    surface.
    """
    domain = _scope_domain("superseded_by IS NULL")
    every_iso = ASSIGNED_ISO_ALPHA2
    non_us_iso_rows = sum(
        n
        for value, n in domain.items()
        if value in every_iso and value not in DEFAULT_GEOGRAPHIC_SCOPE_FILTER
    )
    assert non_us_iso_rows == 1, (
        f"expected exactly 1 non-US ISO-scoped active row (GB, id 23042), got "
        f"{non_us_iso_rows}. The --continent-filter yield claim needs re-measuring."
    )
