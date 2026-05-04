"""Unit tests for db/dedup.py against synthetic data per PROJECT_BIBLE.md §8.3.

Required cases (per the Phase 1 brief):
  1. identical-identifier merge
  2. MAC-within-OUI subset merge
  3. confidence-bonus capping at 99
  4. supersedes pointer correctness
  5. conflicting-source notes append
"""

from __future__ import annotations

import pytest

from db.dedup import (
    DedupResult,
    IdentifierRow,
    dedup,
    find_duplicate_clusters,
    is_duplicate,
    merge_cluster,
)


# ─── helpers ───────────────────────────────────────────────────────────────


def row(
    id_: int,
    identifier: str,
    identifier_type: str = "mac",
    confidence: int = 70,
    source_url: str = "https://example.test/source",
    source_excerpt: str | None = None,
    notes: str | None = None,
    superseded_by: int | None = None,
) -> IdentifierRow:
    return IdentifierRow(
        id=id_,
        identifier=identifier,
        identifier_type=identifier_type,
        confidence=confidence,
        source_url=source_url,
        source_excerpt=source_excerpt,
        notes=notes,
        superseded_by=superseded_by,
    )


# ─── 1. identical-identifier merge ─────────────────────────────────────────


def test_identical_identifier_pair_is_duplicate():
    a = row(1, "aa:bb:cc:dd:ee:ff", confidence=70, source_url="https://src.a/")
    b = row(2, "aa:bb:cc:dd:ee:ff", confidence=80, source_url="https://src.b/")
    assert is_duplicate(a, b) is True


def test_identical_identifier_merge_picks_higher_confidence_canonical():
    a = row(1, "aa:bb:cc:dd:ee:ff", confidence=70, source_url="https://src.a/")
    b = row(2, "aa:bb:cc:dd:ee:ff", confidence=80, source_url="https://src.b/")
    result = merge_cluster([a, b])
    assert result.canonical.id == 2
    assert result.canonical.confidence == 85  # min(99, 80 + 5)
    assert len(result.superseded) == 1
    assert result.superseded[0].id == 1


def test_normalization_handles_uppercase_and_whitespace():
    a = row(1, "AA:BB:CC:DD:EE:FF", confidence=60)
    b = row(2, " aa:bb:cc:dd:ee:ff ", confidence=70)
    assert is_duplicate(a, b) is True


def test_different_identifiers_not_duplicate():
    a = row(1, "aa:bb:cc:dd:ee:ff", confidence=70)
    b = row(2, "aa:bb:cc:dd:ee:00", confidence=70)
    assert is_duplicate(a, b) is False


def test_same_identifier_different_type_not_duplicate():
    # OUI vs ssid_exact happens to share string but different type with no
    # subset relationship → NOT a duplicate.
    a = row(1, "aa:bb:cc", identifier_type="oui", confidence=70)
    b = row(2, "aa:bb:cc", identifier_type="ssid_exact", confidence=70)
    assert is_duplicate(a, b) is False


# ─── 2. MAC-within-OUI subset merge ────────────────────────────────────────


def test_mac_within_oui_is_duplicate():
    oui_row = row(1, "aa:bb:cc", identifier_type="oui", confidence=90)
    mac_row = row(2, "aa:bb:cc:dd:ee:ff", identifier_type="mac", confidence=80)
    assert is_duplicate(oui_row, mac_row) is True
    # symmetric
    assert is_duplicate(mac_row, oui_row) is True


def test_bssid_within_oui_is_duplicate():
    oui_row = row(1, "aa:bb:cc", identifier_type="oui", confidence=90)
    bssid_row = row(2, "aa:bb:cc:11:22:33", identifier_type="bssid", confidence=70)
    assert is_duplicate(oui_row, bssid_row) is True


def test_mac_outside_oui_not_duplicate():
    oui_row = row(1, "aa:bb:cc", identifier_type="oui", confidence=90)
    mac_row = row(2, "aa:bb:00:dd:ee:ff", identifier_type="mac", confidence=80)
    assert is_duplicate(oui_row, mac_row) is False


def test_mac_within_oui_merge_canonical_is_higher_confidence():
    oui_row = row(1, "aa:bb:cc", identifier_type="oui", confidence=90,
                  source_url="https://ieee.org/oui")
    mac_row = row(2, "aa:bb:cc:dd:ee:ff", identifier_type="mac", confidence=80,
                  source_url="https://wigle.net/mac")
    result = merge_cluster([oui_row, mac_row])
    # OUI has higher confidence → it wins as canonical.
    assert result.canonical.id == 1
    assert result.canonical.identifier_type == "oui"
    assert result.canonical.confidence == 95  # min(99, 90 + 5)
    assert result.superseded[0].id == 2
    assert result.superseded[0].superseded_by == 1


def test_mac_within_oui_merge_when_mac_has_higher_confidence():
    oui_row = row(1, "aa:bb:cc", identifier_type="oui", confidence=60)
    mac_row = row(2, "aa:bb:cc:dd:ee:ff", identifier_type="mac", confidence=85)
    result = merge_cluster([oui_row, mac_row])
    # MAC wins because confidence is higher; OUI gets superseded.
    assert result.canonical.id == 2
    assert result.canonical.identifier_type == "mac"
    assert result.canonical.confidence == 90  # min(99, 85 + 5)
    assert result.superseded[0].id == 1
    assert result.superseded[0].superseded_by == 2


# ─── 3. confidence-bonus capping at 99 ─────────────────────────────────────


@pytest.mark.parametrize(
    "originals,expected",
    [
        ([70, 80], 85),     # straightforward: max + 5
        ([95, 90], 99),     # max+5 = 100 → cap to 99
        ([99, 99], 99),     # already at cap
        ([100, 50], 99),    # max+5 = 105 → cap to 99
        ([50, 50, 50], 55),
    ],
)
def test_confidence_bonus_capped_at_99(originals, expected):
    rows = [row(i + 1, "aa:bb:cc:dd:ee:ff", confidence=c)
            for i, c in enumerate(originals)]
    result = merge_cluster(rows)
    assert result.canonical.confidence == expected


# ─── 4. supersedes pointer correctness ─────────────────────────────────────


def test_superseded_by_points_to_canonical_id_for_all_losers():
    rows = [
        row(1, "aa:bb:cc:dd:ee:ff", confidence=70, source_url="https://src1/"),
        row(2, "aa:bb:cc:dd:ee:ff", confidence=85, source_url="https://src2/"),
        row(3, "aa:bb:cc:dd:ee:ff", confidence=60, source_url="https://src3/"),
    ]
    result = merge_cluster(rows)
    assert result.canonical.id == 2
    assert {r.id for r in result.superseded} == {1, 3}
    for loser in result.superseded:
        assert loser.superseded_by == result.canonical.id


def test_canonical_does_not_set_its_own_superseded_by():
    a = row(1, "aa:bb:cc:dd:ee:ff", confidence=70)
    b = row(2, "aa:bb:cc:dd:ee:ff", confidence=80)
    result = merge_cluster([a, b])
    assert result.canonical.superseded_by is None


def test_singleton_returns_unchanged():
    only = row(1, "aa:bb:cc:dd:ee:ff", confidence=70)
    result = merge_cluster([only])
    assert result.canonical == only
    assert result.superseded == ()


def test_empty_cluster_raises():
    with pytest.raises(ValueError):
        merge_cluster([])


def test_canonical_must_have_id():
    a = IdentifierRow(
        id=None,
        identifier="aa:bb:cc:dd:ee:ff",
        identifier_type="mac",
        confidence=80,
        source_url="https://src/",
    )
    b = row(1, "aa:bb:cc:dd:ee:ff", confidence=70)
    # `a` has no id but higher confidence → would be canonical → error.
    with pytest.raises(ValueError):
        merge_cluster([a, b])


# ─── 5. conflicting-source notes append ────────────────────────────────────


def test_loser_source_url_and_excerpt_are_appended_to_notes():
    canonical_in = row(
        1,
        "aa:bb:cc:dd:ee:ff",
        confidence=85,
        source_url="https://canonical.src/",
        source_excerpt="seen on official vendor docs",
        notes="initial canonical note",
    )
    loser_a = row(
        2,
        "aa:bb:cc:dd:ee:ff",
        confidence=60,
        source_url="https://loser-a.src/",
        source_excerpt="forum mention",
    )
    loser_b = row(
        3,
        "aa:bb:cc:dd:ee:ff",
        confidence=55,
        source_url="https://loser-b.src/",
        # no excerpt
    )
    result = merge_cluster([canonical_in, loser_a, loser_b])
    notes = result.canonical.notes
    assert notes is not None
    # canonical's prior notes preserved
    assert "initial canonical note" in notes
    # both losers' source_urls appear
    assert "https://loser-a.src/" in notes
    assert "https://loser-b.src/" in notes
    # loser-a's excerpt appears; loser-b's absence does not error
    assert "forum mention" in notes
    # loser ids are recorded so audit can backtrack
    assert "merged_from_id=2" in notes
    assert "merged_from_id=3" in notes


def test_notes_have_one_line_per_loser():
    rows = [
        row(1, "aa:bb:cc:dd:ee:ff", confidence=85,
            source_url="https://canonical/"),
        row(2, "aa:bb:cc:dd:ee:ff", confidence=70,
            source_url="https://loser-a/"),
        row(3, "aa:bb:cc:dd:ee:ff", confidence=70,
            source_url="https://loser-b/"),
    ]
    result = merge_cluster(rows)
    # Two loser lines (no canonical prior notes here).
    assert result.canonical.notes is not None
    assert result.canonical.notes.count("\n") == 1
    assert result.canonical.notes.startswith("merged_from_id=")


def test_canonical_with_no_prior_notes_starts_with_loser_line():
    a = row(1, "aa:bb:cc:dd:ee:ff", confidence=80,
            source_url="https://a/")
    b = row(2, "aa:bb:cc:dd:ee:ff", confidence=70,
            source_url="https://b/")
    result = merge_cluster([a, b])
    assert result.canonical.notes is not None
    assert result.canonical.notes.startswith("merged_from_id=2")


# ─── batch dedup over a flat list ──────────────────────────────────────────


def test_dedup_groups_transitive_subset_chain():
    # OUI ⊃ MAC1 and OUI ⊃ MAC2 → all three cluster together via OUI.
    records = [
        row(10, "aa:bb:cc", identifier_type="oui", confidence=92,
            source_url="https://ieee.org/oui"),
        row(20, "aa:bb:cc:11:22:33", identifier_type="mac", confidence=70),
        row(30, "aa:bb:cc:44:55:66", identifier_type="mac", confidence=65),
        # unrelated record
        row(40, "11:22:33", identifier_type="oui", confidence=80),
    ]
    canonical_updates, superseded = dedup(records)
    assert len(canonical_updates) == 1
    assert canonical_updates[0].id == 10
    assert {r.id for r in superseded} == {20, 30}


def test_find_duplicate_clusters_excludes_singletons():
    records = [
        row(1, "aa:bb:cc:dd:ee:ff"),
        row(2, "aa:bb:cc:dd:ee:00"),
        row(3, "aa:bb:cc:dd:ee:ff"),
    ]
    clusters = find_duplicate_clusters(records)
    assert len(clusters) == 1
    assert {r.id for r in clusters[0]} == {1, 3}
