#!/usr/bin/env python3
"""MAC-707 — survivor-dominance gate for supersession folds.

A fold (`superseded_by = <successor>`) is *information-preserving* only if the
survivor reaches every Lynceus feed the folded row reached. `mig-0049` (MAC-611)
folded 20 rows without ever proving that; MAC-706 found one that regressed
(565 -> 35666 dropped `geographic_scope='US'`, so the survivor fails the CP7
high-confidence gate at `export_lynceus.py:1054-1056`).

This gate makes that proof runnable and re-runnable.

DESIGN — the gates are IMPORTED, never reimplemented
    `_classify_row` and `_passes_geographic_scope` are imported from
    `db/validation/export_lynceus.py`. A hand-rolled copy of the gate is an
    attestation about the exporter, not a measurement of it, and it drifts
    silently the first time CP7 or the CP39 carve-out list moves.

TWO DISTINCT MEASURES — a fold can pass one and fail the other
    worse             ROW level. The folded row reached feed F and the survivor
                      does not. This is the dominance defect itself.
    coverage_lost     EMITTED-KEY level. The folded row contributed emitted key
                      K to feed F and, in the post-fold active set, NO active
                      row contributes K to F. This is the shipped detection loss.

    They are not the same number and neither implies the other. A row can be
    `worse` while coverage holds, because a sibling active row on the SAME
    emitted key still carries it -- that is exactly the `FS Ext Battery` case,
    where `ssid_pattern` id 562 keeps the *pattern string* in the feed while the
    `ble_local_name` match path is lost. Reporting only `coverage_lost` would
    have called mig-0049 clean; reporting only `worse` would overstate the loss
    as the pattern vanishing. Both print.

Usage:
    python3 scripts/check_supersession_dominance.py --db db/argus.db --cohort c1
    python3 scripts/check_supersession_dominance.py --db db/argus.db --pairs-json <file>

Exit codes:
    0  every fold in the cohort is dominant (worse = 0, coverage_lost = 0)
    1  at least one non-dominant fold
    2  the gate could not run (empty cohort, unreadable DB, import failure) --
       never conflated with a clean pass. A zero-yield gate needs a positive
       control; an empty cohort is a broken gate, not a passing one.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from db.validation.export_lynceus import (  # noqa: E402
    DEFAULT_GEOGRAPHIC_SCOPE_FILTER,
    ActiveRow,
    Halt,
    _classify_row,
    _passes_geographic_scope,
)

# Per-feed flags, transcribed from the real call sites in
# `export_lynceus.py::run_export` (standard at 2116-2126, high-conf at 2131-2144).
# Kept as data so a drift in either call site is a one-line fix here.
FEEDS = {
    "standard": {
        "confidence_threshold": 30,
        "apply_pi_self_exclude": False,
        "apply_excluded_source_type": False,
    },
    "high_confidence": {
        "confidence_threshold": 70,
        "apply_pi_self_exclude": True,
        "apply_excluded_source_type": True,
    },
}

# C1 -- the 20 folds mig-0049 actually wrote. Derived from the file's UPDATE
# targets, NOT from its prose header: the header is a restatement and the
# migration moved slots once (0048 -> 0049) after it was written.
# db/migrations/0049_mac611_mac570_duplicate_emitted_key_supersession.sql
C1_PAIRS: tuple[tuple[int, int], ...] = (
    (22837, 438),   # L244  oui 00:12:1c
    (22840, 457),   # L259  oui 00:26:7e
    (22834, 447),   # L274  oui 34:d2:62
    (22833, 421),   # L289  oui 48:1c:b9
    (22832, 431),   # L304  oui 60:60:1f
    (22838, 439),   # L319  oui 90:03:b7
    (22831, 416),   # L338  oui 90:3a:e6
    (22836, 416),   # L354  oui 90:3a:e6 (3-row group)
    (22839, 440),   # L370  oui a0:14:3d
    (565, 35666),   # L387  ble_local_name 'FS Ext Battery'  <-- MAC-706 defect
    (36588, 23043), # L404  ble_service_uuid f6ec37db-...
    (36591, 23043),
    (36597, 23043),
    (36600, 23043),
    (36603, 23043),
    (36609, 23043),
    (36612, 23043),
    (36615, 23043),
    (22908, 22771), # L428  ssid_exact 'Flock'
    (22909, 22772), # L433  ssid_exact 'Flock-230503'
)

ROW_COLUMNS = (
    "id, identifier, identifier_type, device_category, manufacturer, model, "
    "confidence, source_type, source_url, source_excerpt, notes, "
    "geographic_scope, first_seen, last_verified"
)


def load_rows(db_path: Path) -> tuple[dict[int, ActiveRow], list[ActiveRow]]:
    """Return (every row by id, the ACTIVE row list).

    Both are needed and they are not interchangeable. Dominance is evaluated on
    the folded row's stored columns, which are only reachable via the all-rows
    map because the fold already made that row inactive. Coverage is evaluated
    against the active set, because that is what the exporter actually reads.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        every: dict[int, ActiveRow] = {}
        active: list[ActiveRow] = []
        for r in conn.execute(
            f"SELECT {ROW_COLUMNS}, superseded_by FROM identifiers"
        ):
            row = ActiveRow(
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
            every[row.id] = row
            if r["superseded_by"] is None:
                active.append(row)
        return every, active
    finally:
        conn.close()


def reach(row: ActiveRow, feed: str, scope_filter: tuple[str, ...]) -> set[tuple[str, str]]:
    """Emitted keys this row contributes to `feed`; empty set if it is dropped.

    Mirrors the exporter's real order: `_classify_row` first (confidence,
    source-type, type-MAP, suppression), then the CP7 scope gate, which the
    exporter applies AFTER classification at line 1493-1509.
    """
    cfg = FEEDS[feed]
    try:
        drop_bin, entries = _classify_row(
            row,
            confidence_threshold=cfg["confidence_threshold"],
            apply_pi_self_exclude=cfg["apply_pi_self_exclude"],
            apply_excluded_source_type=cfg["apply_excluded_source_type"],
        )
    except Halt:
        # A Halt is the exporter refusing to classify; treat as no contribution
        # rather than crashing the sweep, and let the caller see it as a loss.
        return set()
    if drop_bin is not None:
        return set()
    if not _passes_geographic_scope(
        row,
        geographic_scope_filter=scope_filter,
        is_high_confidence=cfg["confidence_threshold"] >= 70,
    ):
        return set()
    return {_key(e) for e in entries}


def _key(entry) -> tuple[str, str]:
    """Emitted key. ssid_pattern is folded NOCASE because CP51 dedups it that
    way whole-file (`export_lynceus.py:1512-1520`); comparing it case-sensitively
    would invent coverage losses that the exporter never emits."""
    if entry.pattern_type == "ssid_pattern":
        return (entry.pattern_type, entry.pattern.lower())
    return (entry.pattern_type, entry.pattern)


def run(db_path: Path, pairs: list[tuple[int, int]], scope_filter, label: str) -> int:
    if not pairs:
        print(f"UNEVALUATED — cohort '{label}' is empty. A gate with no cohort "
              f"proves nothing; refusing to print PASS.", file=sys.stderr)
        return 2

    every, active = load_rows(db_path)

    # Post-fold coverage basis: every emitted key any ACTIVE row contributes.
    covered: dict[str, set[tuple[str, str]]] = {}
    for feed in FEEDS:
        keys: set[tuple[str, str]] = set()
        for row in active:
            keys |= reach(row, feed, scope_filter)
        covered[feed] = keys

    worse: list[dict] = []
    coverage_lost: list[dict] = []
    missing: list[tuple[int, int]] = []

    for folded_id, surv_id in pairs:
        folded, surv = every.get(folded_id), every.get(surv_id)
        if folded is None or surv is None:
            missing.append((folded_id, surv_id))
            continue
        for feed in FEEDS:
            f_keys = reach(folded, feed, scope_filter)
            s_keys = reach(surv, feed, scope_filter)
            lost = f_keys - s_keys
            if lost:
                worse.append({
                    "folded": folded_id, "survivor": surv_id, "feed": feed,
                    "lost_keys": sorted(lost),
                    "folded_geo": folded.geographic_scope,
                    "survivor_geo": surv.geographic_scope,
                    "folded_conf": folded.confidence,
                    "survivor_conf": surv.confidence,
                })
                for k in sorted(lost):
                    if k not in covered[feed]:
                        coverage_lost.append(
                            {"folded": folded_id, "survivor": surv_id,
                             "feed": feed, "key": k}
                        )

    print(f"cohort            = {label}")
    print(f"db                = {db_path}")
    print(f"pairs evaluated   = {len(pairs) - len(missing)} of {len(pairs)}")
    if missing:
        print(f"MISSING ROW IDS   = {missing}")
    print(f"worse             = {len(worse)}")
    print(f"coverage lost     = {len(coverage_lost)}")
    hc_lost = [c for c in coverage_lost if c["feed"] == "high_confidence"]
    print(f"  of which high-confidence coverage lost = {len(hc_lost)}")

    for w in worse:
        print(f"  WORSE  {w['folded']} -> {w['survivor']}  feed={w['feed']}  "
              f"geo {w['folded_geo']!r} -> {w['survivor_geo']!r}  "
              f"conf {w['folded_conf']} -> {w['survivor_conf']}  "
              f"lost={w['lost_keys']}")
    for c in coverage_lost:
        print(f"  COVERAGE LOST  feed={c['feed']}  key={c['key']}  "
              f"(no active row emits it)")

    if missing:
        return 2
    return 0 if not worse and not coverage_lost else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=REPO_ROOT / "db" / "argus.db")
    ap.add_argument("--cohort", choices=("c1",))
    ap.add_argument("--pairs-json", type=Path,
                    help="JSON list of [folded_id, survivor_id] pairs")
    ap.add_argument("--label", default=None)
    ap.add_argument("--scope-filter", default=",".join(DEFAULT_GEOGRAPHIC_SCOPE_FILTER))
    args = ap.parse_args()

    if args.cohort == "c1":
        pairs, label = list(C1_PAIRS), args.label or "C1 (mig-0049, 20 folds)"
    elif args.pairs_json:
        raw = json.loads(args.pairs_json.read_text())
        pairs = [(int(a), int(b)) for a, b in raw]
        label = args.label or f"custom ({args.pairs_json.name})"
    else:
        print("need --cohort or --pairs-json", file=sys.stderr)
        return 2

    scope_filter = tuple(s.strip() for s in args.scope_filter.split(",") if s.strip())
    return run(args.db, pairs, scope_filter, label)


if __name__ == "__main__":
    raise SystemExit(main())
