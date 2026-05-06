"""Pure-function dedup logic per PROJECT_BIBLE.md §8.3.

Two records are duplicates if:
  - Identical normalized `identifier` AND `identifier_type`, OR
  - One record's identifier is a strict subset of the other (e.g., MAC
    within an OUI range).

On dedup:
  - Keep the record with highest confidence as canonical.
  - Append all `source_url`s and `source_excerpt`s into the canonical's notes.
  - Mark the other record `superseded_by = canonical.id`.
  - Recompute confidence: `min(99, max(originals) + 5)` for corroboration bonus.

This module is intentionally DB-free so it can be exercised from unit tests
without a live SQLite connection. Callers are responsible for persisting
the returned canonical/superseded rows.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Optional, Sequence


@dataclass(frozen=True)
class IdentifierRow:
    """A subset of the §4.1 `identifiers` row that dedup needs to operate on.

    `id` may be `None` for synthetic rows in tests, but real rows from the DB
    will always carry a row id.
    """

    id: Optional[int]
    identifier: str
    identifier_type: str
    confidence: int
    source_url: str
    source_excerpt: Optional[str] = None
    notes: Optional[str] = None
    superseded_by: Optional[int] = None


@dataclass(frozen=True)
class DedupResult:
    """Output of `merge_cluster`.

    `canonical` is the surviving row with confidence/notes updated per §8.3.
    `superseded` are the losing rows with `superseded_by` set to canonical.id.
    """

    canonical: IdentifierRow
    superseded: tuple[IdentifierRow, ...]


_OUI_HOSTS = frozenset({"mac", "bssid"})


def _normalize(value: str) -> str:
    """§4.3 normalization for the identifier text used in comparison.

    MAC addresses, OUIs, BLE UUIDs are all lowercase per the bible. SSIDs are
    case-sensitive but for dedup comparison we still strip surrounding
    whitespace; case differences in SSIDs intentionally do NOT collapse, since
    the bible says "stored exactly as broadcast".
    """
    return value.strip()


def _normalize_for_compare(value: str, identifier_type: str) -> str:
    v = _normalize(value)
    if identifier_type in ("ssid_exact", "ssid_pattern"):
        return v
    return v.lower()


def is_duplicate(a: IdentifierRow, b: IdentifierRow) -> bool:
    """Return True if records `a` and `b` are duplicates per §8.3."""
    a_ident = _normalize_for_compare(a.identifier, a.identifier_type)
    b_ident = _normalize_for_compare(b.identifier, b.identifier_type)

    # Same identifier + same type.
    if a.identifier_type == b.identifier_type and a_ident == b_ident:
        return True

    # OUI ⊃ MAC/BSSID strict subset (bible's explicit example).
    if a.identifier_type == "oui" and b.identifier_type in _OUI_HOSTS:
        return b_ident.startswith(a_ident + ":")
    if b.identifier_type == "oui" and a.identifier_type in _OUI_HOSTS:
        return a_ident.startswith(b_ident + ":")

    return False


def _stable_canonical(records: Sequence[IdentifierRow]) -> IdentifierRow:
    """Pick canonical = highest confidence; tiebreak on lowest id for stability.

    A `None` id is treated as larger than any real id so DB-loaded rows win
    over synthetic candidates with no row id.
    """
    def key(r: IdentifierRow) -> tuple[int, int]:
        ident_id = r.id if r.id is not None else 10**12
        return (-(r.confidence or 0), ident_id)

    return min(records, key=key)


def _append_source_to_notes(
    canonical_notes: Optional[str],
    losers: Sequence[IdentifierRow],
) -> Optional[str]:
    """Build a notes string that preserves canonical notes and appends a
    source-merged line per loser. Each loser line records its id, source_url,
    and (if present) source_excerpt — the bible's "append all source_urls and
    source_excerpts into the canonical record's notes" rule.
    """
    lines: list[str] = []
    if canonical_notes and canonical_notes.strip():
        lines.append(canonical_notes.strip())
    for loser in losers:
        parts = [f"merged_from_id={loser.id}", f"source_url={loser.source_url}"]
        if loser.source_excerpt:
            excerpt = loser.source_excerpt.strip()
            if excerpt:
                parts.append(f"source_excerpt={excerpt}")
        lines.append("; ".join(parts))
    return "\n".join(lines) if lines else None


def merge_cluster(
    records: Sequence[IdentifierRow],
    *,
    independent_corroboration: bool = True,
) -> DedupResult:
    """Merge a cluster of records that have already been determined duplicates.

    Pure: no DB writes, no global state. Returns the updated canonical row
    (new confidence, appended notes) and the superseded rows with their
    `superseded_by` field set to canonical.id.

    `independent_corroboration` enforces §11 #8: confidence only rises when
    a *second independent source* confirms. Default True preserves bible
    §8.3 verbatim semantics. Pass False when all cluster members trace to
    the same `raw_observations.source_id` — provenance is still combined
    and `superseded_by` set, but confidence is held at `max(originals)`.
    """
    if not records:
        raise ValueError("merge_cluster() requires at least one record")
    if len(records) == 1:
        return DedupResult(canonical=records[0], superseded=())

    canonical = _stable_canonical(records)
    if canonical.id is None:
        raise ValueError(
            "merge_cluster(): canonical record must have a non-None id "
            "(superseded_by is a row-id FK)"
        )

    losers = tuple(r for r in records if r is not canonical)

    max_conf = max((r.confidence or 0) for r in records)
    if independent_corroboration:
        new_confidence = min(99, max_conf + 5)  # §8.3 corroboration bonus
    else:
        new_confidence = max_conf  # §11 #8: same-source = no uplift

    canonical_updated = replace(
        canonical,
        confidence=new_confidence,
        notes=_append_source_to_notes(canonical.notes, losers),
    )
    superseded_updated = tuple(replace(l, superseded_by=canonical.id) for l in losers)
    return DedupResult(canonical=canonical_updated, superseded=superseded_updated)


def find_duplicate_clusters(
    records: Sequence[IdentifierRow],
) -> list[list[IdentifierRow]]:
    """Group records into clusters of mutual duplicates via transitive closure.

    Returns only clusters of size ≥ 2 (singletons are not reported). Order
    within a cluster preserves insertion order from `records`.
    """
    n = len(records)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if is_duplicate(records[i], records[j]):
                union(i, j)

    buckets: dict[int, list[IdentifierRow]] = {}
    for i, row in enumerate(records):
        buckets.setdefault(find(i), []).append(row)
    return [cluster for cluster in buckets.values() if len(cluster) > 1]


def dedup(
    records: Sequence[IdentifierRow],
) -> tuple[list[IdentifierRow], list[IdentifierRow]]:
    """Convenience: run cluster detection + merge over a flat record list.

    Returns (canonical_updates, superseded_updates). Singleton records are
    NOT included in canonical_updates — only rows whose state changed.
    """
    canonical_updates: list[IdentifierRow] = []
    superseded_updates: list[IdentifierRow] = []
    for cluster in find_duplicate_clusters(records):
        result = merge_cluster(cluster)
        canonical_updates.append(result.canonical)
        superseded_updates.extend(result.superseded)
    return canonical_updates, superseded_updates


__all__ = [
    "IdentifierRow",
    "DedupResult",
    "is_duplicate",
    "merge_cluster",
    "find_duplicate_clusters",
    "dedup",
]
