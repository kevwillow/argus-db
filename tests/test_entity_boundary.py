"""MAC-585 — regression guard for the entity-boundary predicate.

Third instance of the containment bug class (after MAC-542 and MAC-535's
sibling finding). These tests exist so a fourth cannot land silently.

The load-bearing test is ``test_predicate_is_not_containment``: it asserts the
RESIDUE — the set of strings containment accepts and boundary must reject —
rather than restating the transform. A matcher that quietly degraded back to
``in`` would pass a boundary-shaped test that only checked true positives.
"""
from __future__ import annotations

import sqlite3

import pytest

from db.entity_boundary import (
    BoundaryCorpus,
    any_boundary_match,
    boundary_match,
    contiguous,
    is_short_single_token,
    tokenize,
)

# Real bytes from db/argus.db, cite-pasted in
# operator_review/MAC-585/RATIFICATION.md. Each is a string that
# `LIKE '%needle%'` accepts and the boundary predicate must reject.
CONTAINMENT_FALSE_POSITIVES = [
    ("DJI", "AEOPORT INTERNATIONAL DE DJIB OUTI"),
    ("DJI", "BEMIDJI AVIATION SERVICES, INC"),
    ("DJI", "Naldjian Bros Inc"),
    ("ALPR", "ALPRO SERVICE CO. INC."),
    ("Axon", "FAXON ENGINEERING CO INC"),
    ("Axon", "Axonics Modulation Technologies, Inc"),
    ("Magnet", "AJAX TOCCO MAGNETHERMIC CORP"),
    ("Magnet", "American Magnetics Corporation"),
    ("Axis", "ABAXIS, INC."),
    ("Axis", "MIAXIS BIOMETRICS CO.,LTD."),
    ("Arris", "L3HARRIS TECHNOLOGIES, INC."),
    ("Arris", "HARRIS CORPORATION"),
    ("yst", "3D Systems Corporation"),
    ("Flock", "SELFLOCK SCREW PRODUCTS COMPANY, INC."),
    ("Parrot", "PARROTT CANVAS COMPANY, INC."),
    ("Harris", "Harrison Precision Industrial Co Ltd"),
]

TRUE_POSITIVES = [
    ("DJI", "SZ DJI TECHNOLOGY CO., LTD"),
    ("Axon", "AXON ENTERPRISE, INC."),
    ("Harris", "HARRIS CORPORATION"),
    ("Flock Safety", "Flock Safety Inc"),
    # Token normalization crosses punctuation — this is the ADDED-set
    # mechanism from MAC-585 and is intended behaviour, not a leak.
    ("Controls Inc", "Automatic Bar Controls, Inc."),
]


@pytest.mark.parametrize("needle,haystack", CONTAINMENT_FALSE_POSITIVES)
def test_predicate_is_not_containment(needle, haystack):
    """The residue: containment accepts these, boundary must not.

    Non-vacuity is asserted in the same breath — if the fixture ever stopped
    being a containment hit, the test would be proving nothing.
    """
    assert needle.upper() in haystack.upper(), (
        f"fixture no longer exercises the defect: {needle!r} is not a "
        f"substring of {haystack!r}"
    )
    assert not boundary_match(needle, haystack)


@pytest.mark.parametrize("needle,haystack", TRUE_POSITIVES)
def test_real_vendor_matches_survive(needle, haystack):
    assert boundary_match(needle, haystack)


def test_tokenize_matches_mac542_reference():
    assert tokenize("SZ DJI TECHNOLOGY CO., LTD") == [
        "SZ", "DJI", "TECHNOLOGY", "CO", "LTD",
    ]
    assert tokenize(None) == []
    assert tokenize("") == []
    assert tokenize("AT&T") == ["AT", "T"]


def test_contiguous_requires_adjacency():
    hay = ["FLOCK", "GROUP", "SAFETY"]
    assert contiguous(["FLOCK"], hay)
    assert contiguous(["GROUP", "SAFETY"], hay)
    # Present but not adjacent — a \b-regex over the raw string would accept
    # "FLOCK ... SAFETY"; the token predicate must not.
    assert not contiguous(["FLOCK", "SAFETY"], hay)
    assert not contiguous([], hay)
    assert not contiguous(["A", "B", "C", "D"], hay)


def test_any_boundary_match_or_semantics():
    assert any_boundary_match(["Nope", "Axon"], "AXON ENTERPRISE, INC.")
    assert not any_boundary_match(["Nope", "Axon"], "FAXON ENGINEERING CO INC")
    assert not any_boundary_match([], "anything")


def test_is_short_single_token():
    # MAC-542 §5: len <= 6 and no space.
    assert is_short_single_token("Axis")
    assert is_short_single_token("Flock")
    assert is_short_single_token("Harris")
    assert not is_short_single_token("Motorola")
    assert not is_short_single_token("Flock Safety")


def _corpus(rows, column="v", table="t"):
    conn = sqlite3.connect(":memory:")
    conn.execute(f"CREATE TABLE {table} ({column} TEXT)")
    conn.executemany(f"INSERT INTO {table} VALUES (?)", [(r,) for r in rows])
    return BoundaryCorpus(conn, table, column)


def test_corpus_counts_rows_not_matches():
    """OR-semantics must not double-count a row hit by two tokens."""
    c = _corpus(["Axon Enterprise Axon Body-2"])
    assert c.count(["Axon", "Enterprise"]) == 1


def test_corpus_respects_row_frequency_and_nulls():
    c = _corpus(["AXON ENTERPRISE, INC.", "AXON ENTERPRISE, INC.", None,
                 "FAXON ENGINEERING CO INC"])
    assert c.count(["Axon"]) == 2
    assert c.count([]) == 0
    # NULL never matches, mirroring `NULL LIKE '%t%'` -> NULL -> not counted.
    assert c.count(["Faxon"]) == 1


def test_corpus_first_token_index_does_not_miss_interior_matches():
    """The postings index is a filter; a needle starting mid-value must hit."""
    c = _corpus(["SZ DJI TECHNOLOGY CO., LTD"])
    assert c.count(["DJI Technology"]) == 1
    assert c.count(["DJI"]) == 1
