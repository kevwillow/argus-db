#!/usr/bin/env python3
"""MAC-706/707 — survivor-dominance gate over supersession folds.

The defect class
----------------
A fold ratified without a dominance proof can silently remove a detection path.
`mig-0049` is one instance: survivor 35666 dropped `geographic_scope`, and
`export_lynceus._passes_geographic_scope` treats an empty scope as passing the
standard feed and FAILING the high-confidence feed. The row kept its key, kept
its confidence, and still fell out of one feed on a single NULL column.

So the gate tests against each feed's admission floor SEPARATELY, not against
the emitted key. It reuses `export_lynceus`'s own predicates rather than
reimplementing them, because a reimplemented floor drifts from the real one and
a post-condition that mirrors its own transform proves nothing.

Two distinct verdicts, deliberately not merged
----------------------------------------------
* ``coverage_lost`` — an emitted key the folded row carried into feed F is no
  longer emitted by ANY active admitted row. This is a real detection loss.
* ``worse`` — the survivor is worse than the folded row on some field. Losing
  multiplicity is expected and fine; losing a field is what G2 asks about.

A fold where the survivor drops a key but another active row still emits it is
a multiplicity reduction, NOT a coverage loss. Conflating the two makes the
gate scream on every legitimate dedup.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from db.validation.export_lynceus import (  # noqa: E402
    DEFAULT_GEOGRAPHIC_SCOPE_FILTER,
    ActiveRow,
    Halt,
    _assert_ble_registry_type,
    _classify_row,
    _passes_geographic_scope,
)

# Exactly the two feed configurations `export_lynceus.main` builds
# (db/validation/export_lynceus.py:2115-2142). Kept as data so a drift in the
# real exporter shows up as a diff here rather than as a silent disagreement.
FEEDS: dict[str, dict[str, object]] = {
    "argus_export.json": {
        "confidence_threshold": 30,
        "apply_pi_self_exclude": False,
        "apply_excluded_source_type": False,
    },
    "argus_export_high_confidence.json": {
        "confidence_threshold": 70,
        "apply_pi_self_exclude": True,
        "apply_excluded_source_type": True,
    },
}

ROW_COLS = (
    "id, identifier, identifier_type, device_category, manufacturer, model, "
    "confidence, source_type, source_url, source_excerpt, notes, "
    "geographic_scope, first_seen, last_verified"
)

SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def to_active_row(r: sqlite3.Row) -> ActiveRow:
    return ActiveRow(
        id=r["id"],
        identifier=r["identifier"],
        identifier_type=r["identifier_type"],
        device_category=r["device_category"],
        manufacturer=r["manufacturer"],
        model=r["model"],
        confidence=r["confidence"],
        source_type=r["source_type"],
        source_url=r["source_url"],
        source_excerpt=r["source_excerpt"],
        notes=r["notes"],
        geographic_scope=r["geographic_scope"],
        first_seen=r["first_seen"],
        last_verified=r["last_verified"],
    )


def norm_key(pattern_type: str, pattern: str) -> tuple[str, str]:
    """Feed-level identity of an emitted entry.

    CP51 dedups `ssid_pattern` substrings case-insensitively at whole-file
    scope, so two rows differing only in case collapse to one feed record.
    Comparing those case-sensitively would report a phantom coverage loss.
    """
    if pattern_type == "ssid_pattern":
        return (pattern_type, pattern.lower())
    return (pattern_type, pattern)


def emitted_keys(row: ActiveRow, feed: str) -> tuple[set[tuple[str, str]], str | None]:
    """Keys `row` would emit into `feed`, plus the drop reason if it emits none."""
    cfg = FEEDS[feed]
    try:
        _assert_ble_registry_type(row)
    except Halt as exc:
        return set(), f"halt:{exc}"
    drop_bin, entries = _classify_row(
        row,
        confidence_threshold=cfg["confidence_threshold"],
        apply_pi_self_exclude=cfg["apply_pi_self_exclude"],
        apply_excluded_source_type=cfg["apply_excluded_source_type"],
    )
    if drop_bin is not None:
        return set(), drop_bin
    if not _passes_geographic_scope(
        row,
        geographic_scope_filter=DEFAULT_GEOGRAPHIC_SCOPE_FILTER,
        is_high_confidence=cfg["confidence_threshold"] >= 70,
    ):
        return set(), "geographic_scope_mismatch"
    return {norm_key(e.pattern_type, e.pattern) for e in entries}, None


def field_regressions(
    folded: sqlite3.Row, surv: sqlite3.Row, folded_feeds: set[str]
) -> list[str]:
    """Fields on which the survivor is strictly worse than the row it replaced.

    ``folded_feeds`` is the set of feeds the folded row actually emitted into.
    G2's subject is "every baseline ENTRY whose multiplicity drops" — a row that
    was never admitted to a feed has no entry there to regress, so a geo change
    on it costs nothing. Evaluating the geo predicate in isolation from the rest
    of the admission pipeline reports a loss for rows the exporter had already
    dropped (or halted on) several gates earlier.
    """
    out: list[str] = []

    fc, sc = folded["confidence"], surv["confidence"]
    if (fc is not None) and (sc is None or sc < fc):
        out.append(f"confidence {fc}->{sc}")

    # geographic_scope: only a regression if it costs a feed the folded row was
    # actually in. 'US'->'global' widens; 'US'->NULL costs high-confidence.
    fg = (folded["geographic_scope"] or "").strip()
    sg = (surv["geographic_scope"] or "").strip()
    if fg != sg:
        for feed in FEEDS:
            if feed not in folded_feeds:
                continue
            hc = FEEDS[feed]["confidence_threshold"] >= 70
            f_ok = _passes_geographic_scope(
                to_active_row(folded),
                geographic_scope_filter=DEFAULT_GEOGRAPHIC_SCOPE_FILTER,
                is_high_confidence=hc,
            )
            s_ok = _passes_geographic_scope(
                to_active_row(surv),
                geographic_scope_filter=DEFAULT_GEOGRAPHIC_SCOPE_FILTER,
                is_high_confidence=hc,
            )
            if f_ok and not s_ok:
                out.append(
                    f"geographic_scope {fg or 'NULL'}->{sg or 'NULL'} "
                    f"(loses {feed})"
                )
                break

    if folded["device_category"] != surv["device_category"] and surv[
        "device_category"
    ] in (None, "unknown"):
        out.append(f"device_category {folded['device_category']}->{surv['device_category']}")

    fr = SEVERITY_RANK.get((folded["severity"] or "").lower())
    sr = SEVERITY_RANK.get((surv["severity"] or "").lower())
    if fr is not None and sr is not None and sr < fr:
        out.append(f"severity {folded['severity']}->{surv['severity']}")

    for col in ("manufacturer", "model", "source_excerpt", "source_url"):
        if (folded[col] or "").strip() and not (surv[col] or "").strip():
            out.append(f"{col} lost")

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(REPO_ROOT / "db" / "argus.db"))
    ap.add_argument(
        "--edges",
        required=True,
        help="JSON file from mac707_supersession_edges.py",
    )
    ap.add_argument(
        "--edge-key",
        default="db_confirmed",
        help="Which edge list to sweep: db_confirmed (C2 frame) or "
        "all_canonical_folds (superset control).",
    )
    ap.add_argument("--label", default="sweep")
    args = ap.parse_args()

    payload = json.loads(Path(args.edges).read_text(encoding="utf-8"))
    edges = [tuple(e) for e in payload[args.edge_key]]

    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    # Live coverage: every key emitted into each feed by the CURRENT active set.
    # This is what makes the check coverage-level rather than row-level.
    active = con.execute(
        f"SELECT {ROW_COLS} FROM identifiers WHERE superseded_by IS NULL ORDER BY id"
    ).fetchall()
    live: dict[str, set[tuple[str, str]]] = {}
    for feed in FEEDS:
        acc: set[tuple[str, str]] = set()
        for r in active:
            keys, _ = emitted_keys(to_active_row(r), feed)
            acc |= keys
        live[feed] = acc

    print("=" * 74)
    print(f"SURVIVOR-DOMINANCE SWEEP — {args.label}")
    print("=" * 74)
    print(f"db            : {args.db}")
    print(f"edge list     : {args.edge_key}")
    print(f"DENOMINATOR   : {len(edges)} folds")
    print(f"active rows   : {len(active)}")
    for feed in FEEDS:
        print(f"live coverage : {len(live[feed]):>6} distinct keys  {feed}")
    print("-" * 74)

    coverage_lost: list[dict] = []
    worse: list[dict] = []
    worse_out_of_feed: list[dict] = []
    multiplicity_only = 0
    skipped_missing = 0
    halting_folded: set[int] = set()

    for fid, sid in edges:
        fr = con.execute(
            f"SELECT {ROW_COLS}, severity, superseded_by FROM identifiers WHERE id = ?",
            (fid,),
        ).fetchone()
        sr = con.execute(
            f"SELECT {ROW_COLS}, severity, superseded_by FROM identifiers WHERE id = ?",
            (sid,),
        ).fetchone()
        if fr is None or sr is None:
            skipped_missing += 1
            print(f"  ! edge {fid}->{sid}: row missing, skipped")
            continue

        f_row, s_row = to_active_row(fr), to_active_row(sr)
        dropped_any = False
        folded_feeds: set[str] = set()
        for feed in FEEDS:
            f_keys, f_drop = emitted_keys(f_row, feed)
            s_keys, s_drop = emitted_keys(s_row, feed)
            if f_keys:
                folded_feeds.add(feed)
            if f_drop and f_drop.startswith("halt:"):
                halting_folded.add(fid)
            orphaned = f_keys - s_keys
            if orphaned:
                dropped_any = True
            lost = {k for k in orphaned if k not in live[feed]}
            if lost:
                coverage_lost.append(
                    {
                        "folded": fid,
                        "survivor": sid,
                        "feed": feed,
                        "keys": sorted(lost),
                        "survivor_drop_reason": s_drop,
                    }
                )
                for k in sorted(lost):
                    print(
                        f"  COVERAGE LOST  {fid}->{sid}  {feed}\n"
                        f"                 key={k}  survivor_drop={s_drop}"
                    )
        regs = field_regressions(fr, sr, folded_feeds)
        if regs:
            rec = {
                "folded": fid,
                "survivor": sid,
                "regressions": regs,
                "folded_feeds": sorted(folded_feeds),
            }
            if folded_feeds:
                worse.append(rec)
                print(f"  WORSE          {fid}->{sid}  {'; '.join(regs)}")
            else:
                # Folded row emitted into no feed at all, so it had no baseline
                # entry to regress. Reported, never counted against the gate.
                worse_out_of_feed.append(rec)
        if dropped_any and not regs:
            multiplicity_only += 1

    print("-" * 74)
    print(f"DENOMINATOR swept .................. {len(edges)}")
    print(f"rows missing (skipped) ............. {skipped_missing}")
    print(
        f"folded rows that HALT the exporter . {len(halting_folded)}"
        "  (distinct rows; feed-absent by construction)"
    )
    print(f"multiplicity-only reductions ....... {multiplicity_only}")
    print(f"regressions on feed-ABSENT folds ... {len(worse_out_of_feed)}  (informational)")
    print("")
    print(f"  coverage lost .................... {len(coverage_lost)}")
    print(f"  worse ........................... {len(worse)}")
    print("=" * 74)

    if worse_out_of_feed:
        print("Feed-absent regressions (folded row emitted into no feed):")
        for r in worse_out_of_feed:
            print(f"  - {r['folded']}->{r['survivor']}: {'; '.join(r['regressions'])}")
        print("=" * 74)

    con.close()
    return 0 if not coverage_lost and not worse else 1


if __name__ == "__main__":
    sys.exit(main())
