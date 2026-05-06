"""Phase-5 Step-5 dedup pass executor (MAC-42).

Loads the active ``identifiers`` set (rows with ``superseded_by IS NULL``),
runs §8.3 cluster detection via :mod:`db.dedup`, applies the §11 #8
*independent corroboration* rule by tracing each identifier back to its
``raw_observations.source_id``, persists canonical/superseded mutations
atomically inside a single transaction, and returns a structured delta
report so the CEO ratification heartbeat can audit every decision.

Authority chain
---------------
- Bible §6 Phase 5 #2 — "Run dedup pass: merge duplicate identifiers
  across sources, raising confidence and combining provenance."
- Bible §8.3 verbatim — duplicate predicate, canonical = highest-confidence,
  append urls/excerpts to ``notes``, ``superseded_by = canonical.id``,
  ``min(99, max(originals) + 5)`` corroboration bonus.
- Bible §11 #8 — confidence only rises on a *second independent source*.
  Same-``source_id`` clusters merge provenance + supersede but DO NOT
  uplift confidence.
- Bible §8.2 — confidence-band ceilings per ``source_type``. A cross-source
  uplift that pushes the canonical row above its source-type ceiling is a
  HALT condition; the orchestrator surfaces it without writing.
- MAC-42 dispatch (HB33) + envelope refresh comment ``c81196ea`` (HB34).

Idempotency
-----------
The pass loads only rows with ``superseded_by IS NULL``. After a successful
run, all losers carry a non-null ``superseded_by`` so they fall out of the
active set on a re-run. Re-running on the unchanged set is therefore a
no-op (zero clusters detected). Confidence uplift only happens once per
canonical row per cluster — reruns cannot stack uplifts.

Stop-the-line clauses (raised as :class:`HaltCondition`)
--------------------------------------------------------
- ``§11_hard_rule_trip`` — any §11 rule violation.
- ``new_dedup_class`` — a cluster that doesn't match the §8.3 identical /
  strict-subset classes (defense-in-depth; ``find_duplicate_clusters``
  shouldn't produce these by construction).
- ``ceiling_breach`` — uplifted confidence > §8.2 ceiling for canonical's
  ``source_type``.
- ``wave_a_supersession`` — ``identifiers.id=1`` (Wave-A canonical) being
  superseded by anything; per dispatch "do NOT silently proceed".

When a halt fires, the transaction is rolled back and the caller receives
the halt details so the CEO ratification path can decide.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable, Optional, Sequence

from db.dedup import (
    DedupResult,
    IdentifierRow,
    find_duplicate_clusters,
    is_duplicate,
    merge_cluster,
)

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"

VALIDATOR_AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"

# §8.2 confidence-band ceilings (max of each range). A cross-source uplift
# that would push a canonical row above its source-type ceiling halts the
# pass for CEO ratification.
SOURCE_TYPE_CEILINGS: dict[str, int] = {
    "official": 100,
    "regulatory": 95,
    "manufacturer_doc": 90,
    "procurement": 85,
    "academic": 90,
    "foia": 85,
    "crowdsourced": 75,
    "inferred": 70,
    "news_forum": 50,
}

# Wave-A canonical row id (per MAC-38 promotion). Supersession of this row
# is a halt-the-line event regardless of dedup mechanics.
WAVE_A_CANONICAL_ID = 1


@dataclass(frozen=True)
class HaltCondition:
    """Stop-the-line marker. Pass aborts; caller surfaces to CEO."""

    kind: str
    detail: str
    cluster_member_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ClusterDecision:
    """Per-cluster audit record for the delta report."""

    canonical_id: int
    canonical_pre_confidence: int
    canonical_post_confidence: int
    superseded_ids: tuple[int, ...]
    member_ids: tuple[int, ...]
    member_source_ids: tuple[int, ...]
    cross_source: bool
    uplifted: bool
    dedup_class: str  # "identical" | "strict_subset" | "mixed"
    canonical_source_type: str


@dataclass(frozen=True)
class DedupPassReport:
    pre_active_count: int
    clusters_detected: int
    rows_superseded: int
    rows_uplifted: int
    rows_no_uplift_same_source: int
    post_active_count: int
    cluster_decisions: tuple[ClusterDecision, ...]
    halts: tuple[HaltCondition, ...]
    dry_run: bool


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _load_active_identifiers(
    conn: sqlite3.Connection,
) -> tuple[list[IdentifierRow], dict[int, str]]:
    """Return (rows, source_type_by_id) for all ``superseded_by IS NULL`` rows."""
    cur = conn.execute(
        "SELECT id, identifier, identifier_type, confidence, source_url, "
        "source_excerpt, notes, superseded_by, source_type "
        "FROM identifiers WHERE superseded_by IS NULL ORDER BY id"
    )
    rows: list[IdentifierRow] = []
    source_type_by_id: dict[int, str] = {}
    for r in cur.fetchall():
        rows.append(
            IdentifierRow(
                id=r["id"],
                identifier=r["identifier"],
                identifier_type=r["identifier_type"],
                confidence=r["confidence"] or 0,
                source_url=r["source_url"] or "",
                source_excerpt=r["source_excerpt"],
                notes=r["notes"],
                superseded_by=r["superseded_by"],
            )
        )
        source_type_by_id[r["id"]] = r["source_type"] or ""
    return rows, source_type_by_id


def _load_source_id_map(
    conn: sqlite3.Connection, identifier_ids: Iterable[int]
) -> dict[int, set[int]]:
    """Map ``identifier_id`` → set of distinct ``source_id``s in raw_observations."""
    ids = list(identifier_ids)
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    cur = conn.execute(
        f"SELECT promoted_identifier_id, source_id FROM raw_observations "
        f"WHERE promoted_identifier_id IN ({placeholders})",
        ids,
    )
    out: dict[int, set[int]] = defaultdict(set)
    for iid, sid in cur.fetchall():
        if iid is not None and sid is not None:
            out[iid].add(sid)
    return dict(out)


def _classify_cluster(cluster: Sequence[IdentifierRow]) -> str:
    """Classify the cluster against the §8.3 dedup classes."""
    types = {r.identifier_type for r in cluster}
    if len(types) == 1:
        return "identical"
    if types <= {"oui", "mac", "bssid"} and "oui" in types:
        return "strict_subset"
    return "mixed"


def _check_dedup_class(
    cluster: Sequence[IdentifierRow], dedup_class: str
) -> Optional[HaltCondition]:
    """Halt if cluster doesn't match a §8.3 class. Defensive — by construction
    ``find_duplicate_clusters`` only emits §8.3-class clusters.
    """
    if dedup_class in ("identical", "strict_subset"):
        return None
    return HaltCondition(
        kind="new_dedup_class",
        detail=(
            f"Cluster member types {sorted({r.identifier_type for r in cluster})} "
            f"do not match §8.3 identical or strict-subset classes; SAR-N candidate."
        ),
        cluster_member_ids=tuple(r.id for r in cluster if r.id is not None),
    )


def _check_ceiling(
    canonical: IdentifierRow, source_type: str, uplifted: bool
) -> Optional[HaltCondition]:
    """Halt if cross-source uplift pushed canonical past §8.2 ceiling."""
    if not uplifted:
        return None
    ceiling = SOURCE_TYPE_CEILINGS.get(source_type)
    if ceiling is None:
        return HaltCondition(
            kind="unknown_source_type",
            detail=(
                f"Canonical id={canonical.id} source_type='{source_type}' has no §8.2 "
                f"ceiling mapping; cannot validate uplift safety."
            ),
            cluster_member_ids=(canonical.id,) if canonical.id is not None else (),
        )
    if (canonical.confidence or 0) > ceiling:
        return HaltCondition(
            kind="ceiling_breach",
            detail=(
                f"Cross-source uplift pushed id={canonical.id} ({source_type}) to "
                f"confidence={canonical.confidence}, exceeding §8.2 ceiling={ceiling}; "
                f"CEO ratifies the band-cross."
            ),
            cluster_member_ids=(canonical.id,) if canonical.id is not None else (),
        )
    return None


def _check_wave_a_supersession(
    canonical_id: int, superseded_ids: Iterable[int]
) -> Optional[HaltCondition]:
    if WAVE_A_CANONICAL_ID in set(superseded_ids):
        return HaltCondition(
            kind="wave_a_supersession",
            detail=(
                f"Wave-A canonical id={WAVE_A_CANONICAL_ID} would be superseded by "
                f"id={canonical_id}; per dispatch stop-the-line — surface for CEO."
            ),
            cluster_member_ids=(WAVE_A_CANONICAL_ID, canonical_id),
        )
    return None


def _persist(
    conn: sqlite3.Connection,
    canonical_writes: list[IdentifierRow],
    superseded_writes: list[IdentifierRow],
) -> None:
    """Apply mutations inside the caller's transaction (caller commits/rolls back)."""
    for c in canonical_writes:
        conn.execute(
            "UPDATE identifiers "
            "SET confidence = ?, notes = ? "
            "WHERE id = ?",
            (c.confidence, c.notes, c.id),
        )
    for s in superseded_writes:
        conn.execute(
            "UPDATE identifiers SET superseded_by = ? WHERE id = ?",
            (s.superseded_by, s.id),
        )


def _ledger_notes(report: DedupPassReport) -> str:
    return (
        f"Phase-5 Step-5 dedup pass (MAC-42). "
        f"pre_active={report.pre_active_count}, "
        f"clusters={report.clusters_detected}, "
        f"superseded={report.rows_superseded}, "
        f"uplifted={report.rows_uplifted}, "
        f"no_uplift_same_source={report.rows_no_uplift_same_source}, "
        f"post_active={report.post_active_count}, "
        f"halts={len(report.halts)}. "
        f"§8.3 verbatim + §11 #8 cross-source independence."
    )


def _write_ledger(conn: sqlite3.Connection, report: DedupPassReport) -> int:
    cur = conn.execute(
        """INSERT INTO extraction_runs
             (agent_id, source_id, finished_at, records_in, records_out,
              errors, status, notes)
           VALUES (?, NULL, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)""",
        (
            VALIDATOR_AGENT_ID,
            report.pre_active_count,
            report.post_active_count,
            len(report.halts),
            "halted" if report.halts else "ok",
            _ledger_notes(report),
        ),
    )
    return cur.lastrowid


def run_dedup(
    conn: sqlite3.Connection,
    *,
    dry_run: bool = False,
    write_ledger: bool = True,
) -> DedupPassReport:
    """Run the dedup pass against the active identifiers set on ``conn``.

    On halt: rolls back any pending writes from this pass and returns the
    report with ``halts`` populated. On clean run: writes mutations and
    inserts an ``extraction_runs`` ledger row (unless ``write_ledger=False``).

    ``dry_run=True`` short-circuits all writes regardless of halts.
    """
    rows, source_type_by_id = _load_active_identifiers(conn)
    pre_count = len(rows)

    clusters = find_duplicate_clusters(rows)

    cluster_member_ids = [
        [r.id for r in c if r.id is not None] for c in clusters
    ]
    flat_ids = [iid for sub in cluster_member_ids for iid in sub]
    source_id_map = _load_source_id_map(conn, flat_ids)

    decisions: list[ClusterDecision] = []
    halts: list[HaltCondition] = []
    canonical_writes: list[IdentifierRow] = []
    superseded_writes: list[IdentifierRow] = []

    for cluster in clusters:
        dedup_class = _classify_cluster(cluster)
        halt = _check_dedup_class(cluster, dedup_class)
        if halt is not None:
            halts.append(halt)
            continue

        member_source_ids: set[int] = set()
        for r in cluster:
            if r.id is not None:
                member_source_ids |= source_id_map.get(r.id, set())
        cross_source = len(member_source_ids) >= 2
        max_conf = max((r.confidence or 0) for r in cluster)

        result = merge_cluster(
            cluster, independent_corroboration=cross_source
        )

        canonical_source_type = source_type_by_id.get(result.canonical.id, "")
        ceiling_halt = _check_ceiling(
            result.canonical, canonical_source_type, uplifted=cross_source
        )
        if ceiling_halt is not None:
            halts.append(ceiling_halt)
            continue

        wave_a_halt = _check_wave_a_supersession(
            result.canonical.id,
            (s.id for s in result.superseded if s.id is not None),
        )
        if wave_a_halt is not None:
            halts.append(wave_a_halt)
            continue

        canonical_writes.append(result.canonical)
        superseded_writes.extend(result.superseded)

        decisions.append(
            ClusterDecision(
                canonical_id=result.canonical.id,
                canonical_pre_confidence=max_conf,
                canonical_post_confidence=result.canonical.confidence or 0,
                superseded_ids=tuple(
                    s.id for s in result.superseded if s.id is not None
                ),
                member_ids=tuple(r.id for r in cluster if r.id is not None),
                member_source_ids=tuple(sorted(member_source_ids)),
                cross_source=cross_source,
                uplifted=cross_source,
                dedup_class=dedup_class,
                canonical_source_type=canonical_source_type,
            )
        )

    report = DedupPassReport(
        pre_active_count=pre_count,
        clusters_detected=len(clusters),
        rows_superseded=len(superseded_writes),
        rows_uplifted=sum(1 for d in decisions if d.uplifted),
        rows_no_uplift_same_source=sum(
            1 for d in decisions if not d.cross_source
        ),
        post_active_count=pre_count - len(superseded_writes),
        cluster_decisions=tuple(decisions),
        halts=tuple(halts),
        dry_run=dry_run,
    )

    if dry_run:
        return report

    if halts:
        # Don't persist anything if any cluster halted.
        conn.rollback()
        return report

    _persist(conn, canonical_writes, superseded_writes)
    if write_ledger:
        _write_ledger(conn, report)
    conn.commit()
    return report


def report_to_dict(report: DedupPassReport) -> dict:
    return {
        "pre_active_count": report.pre_active_count,
        "clusters_detected": report.clusters_detected,
        "rows_superseded": report.rows_superseded,
        "rows_uplifted": report.rows_uplifted,
        "rows_no_uplift_same_source": report.rows_no_uplift_same_source,
        "post_active_count": report.post_active_count,
        "dry_run": report.dry_run,
        "halts": [asdict(h) for h in report.halts],
        "cluster_decisions": [asdict(d) for d in report.cluster_decisions],
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", default=str(DB_PATH), help="Path to argus.db"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the dedup delta without writing.",
    )
    parser.add_argument(
        "--no-ledger",
        action="store_true",
        help="Skip the extraction_runs ledger row (still commits identifier mutations).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full report as JSON instead of the summary table.",
    )
    args = parser.parse_args(argv)

    conn = _connect(Path(args.db))
    try:
        report = run_dedup(
            conn, dry_run=args.dry_run, write_ledger=not args.no_ledger
        )
    finally:
        conn.close()

    payload = report_to_dict(report)
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"Pre-active identifiers:        {report.pre_active_count}")
        print(f"Clusters detected:             {report.clusters_detected}")
        print(f"Rows superseded:               {report.rows_superseded}")
        print(f"Rows uplifted (cross-source):  {report.rows_uplifted}")
        print(f"Rows held (same-source):       {report.rows_no_uplift_same_source}")
        print(f"Post-active identifiers:       {report.post_active_count}")
        print(f"Halts raised:                  {len(report.halts)}")
        if report.halts:
            for h in report.halts:
                print(f"  HALT [{h.kind}]: {h.detail}")
        print(f"Dry run:                       {report.dry_run}")

    return 1 if report.halts else 0


if __name__ == "__main__":
    raise SystemExit(main())
