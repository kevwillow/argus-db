#!/usr/bin/env python3
"""MAC-663 G1 — measure the TWO-COLUMN feed delta on scratch copies of canonical.

CEO_RATIFICATION.md §6 G1: the approved mutation sets `confidence` AND
`geographic_scope` on the 11 rows 42986-42996. PROOF.md §4 measured a
`confidence`-only mutation, so the approved delta is UNMEASURED. This produces it.

Method is PROOF.md §4's, unchanged: canonical copied to scratch, `coverage_matrix.py`
then `export_lynceus.py` over a baseline copy and a mutated copy, entry sets diffed on
`(pattern_type, pattern)`. `exports/` is never written -- every output path is under
--work.

Verdict is on SET IDENTITY, never on a count (G2/G3). A count-only check passes when
11 rows enter and 11 unrelated rows leave.

Usage:
    python3 scripts/mac663_delta_probe.py --work <scratch-dir>
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CANONICAL = REPO / "db" / "argus.db"

# The 11 under test, pinned as literal strings (R3: fixed keys are literals, never described).
TARGET_IDS = tuple(range(42986, 42997))
TARGET_VALUES = (
    "0000fc6d-0000-1000-8000-00805f9b34fb",
    "0000fc70-0000-1000-8000-00805f9b34fb",
    "0000fc81-0000-1000-8000-00805f9b34fb",
    "0000fc86-0000-1000-8000-00805f9b34fb",
    "0000fc87-0000-1000-8000-00805f9b34fb",
    "0000fce4-0000-1000-8000-00805f9b34fb",
    "0000fce5-0000-1000-8000-00805f9b34fb",
    "0000fd3a-0000-1000-8000-00805f9b34fb",
    "0000fd3b-0000-1000-8000-00805f9b34fb",
    "0000fda9-0000-1000-8000-00805f9b34fb",
    "0000fe9b-0000-1000-8000-00805f9b34fb",
)
TARGET_ENTRIES = frozenset(("ble_uuid", v) for v in TARGET_VALUES)


def run_pipeline(db: Path, out: Path) -> tuple[frozenset, frozenset]:
    """coverage_matrix -> export_lynceus over `db`, all artifacts under `out`."""
    out.mkdir(parents=True, exist_ok=True)
    _run([sys.executable, "db/validation/coverage_matrix.py",
          "--db", str(db), "--out-dir", str(out)])
    _run([sys.executable, "db/validation/export_lynceus.py",
          "--db", str(db), "--exports-dir", str(out),
          # coverage_matrix.py --out-dir emits `coverage_matrix_report.json`, NOT
          # `coverage_matrix.json`. Naming it wrong makes export_lynceus Halt at Step-6.
          "--coverage-matrix-report", str(out / "coverage_matrix_report.json"),
          "--coverage-matrix-md", str(out / "coverage_matrix.md")])
    return _entries(out / "argus_export.json"), _entries(out / "argus_export_high_confidence.json")


def _run(cmd: list[str]) -> None:
    """Run a pipeline step, surfacing stderr on failure.

    `capture_output` + `check=True` alone raises a CalledProcessError whose message
    carries the argv and the exit code but NOT the traceback, so a Halt reads as an
    opaque `exit status 1`. The diagnostic has to be printed to be usable.
    """
    import os
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(REPO)})
    if p.returncode != 0:
        print(f"\nSTEP FAILED rc={p.returncode}: {' '.join(cmd)}")
        print((p.stderr or p.stdout or "<no output>").strip()[-3000:])
        raise SystemExit(3)


def _entries(path: Path) -> frozenset:
    doc = json.loads(path.read_text())
    return frozenset((e["pattern_type"], e["pattern"]) for e in doc["entries"])


def mutate(db: Path) -> int:
    """Apply the APPROVED two-column mutation. Returns rows changed."""
    con = sqlite3.connect(db)
    try:
        cur = con.execute(
            "UPDATE identifiers SET confidence = 75, geographic_scope = 'global' "
            "WHERE id BETWEEN 42986 AND 42996 AND identifier_type = 'ble_uuid' "
            "AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL"
        )
        n = cur.rowcount
        con.commit()
        return n
    finally:
        con.close()


def report(label: str, base: frozenset, mut: frozenset) -> dict:
    added, removed = mut - base, base - mut
    print(f"\n  {label}: {len(base)} -> {len(mut)}   ADDED {len(added)}  REMOVED {len(removed)}")
    for kind, s in (("ADDED", added), ("REMOVED", removed)):
        for t, v in sorted(s):
            inside = "IN-11" if (t, v) in TARGET_ENTRIES else "*** OUTSIDE THE 11 ***"
            print(f"    {kind:8s} {t:12s} {v}   {inside}")
    return {
        "base_n": len(base), "mut_n": len(mut),
        "added": sorted(added), "removed": sorted(removed),
        "added_outside_11": sorted(added - TARGET_ENTRIES),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, type=Path)
    args = ap.parse_args()
    work: Path = args.work
    work.mkdir(parents=True, exist_ok=True)

    base_db, mut_db = work / "base.db", work / "mut.db"
    print(f"canonical : {CANONICAL}")
    shutil.copy2(CANONICAL, base_db)
    shutil.copy2(CANONICAL, mut_db)

    changed = mutate(mut_db)
    print(f"mutated   : {changed} rows set confidence=75, geographic_scope='global'")
    if changed != 11:
        print(f"ABORT: expected 11 rows mutated, got {changed}")
        return 2

    print("running pipeline over BASELINE ...")
    b_std, b_hc = run_pipeline(base_db, work / "out_base")
    print("running pipeline over MUTATED ...")
    m_std, m_hc = run_pipeline(mut_db, work / "out_mut")

    std = report("standard      ", b_std, m_std)
    hc = report("high_confidence", b_hc, m_hc)

    # ---- G2 / G3 verdicts, on set identity ----
    g2 = (frozenset(map(tuple, std["added"])) == TARGET_ENTRIES) and not std["removed"]
    hc_added = frozenset(map(tuple, hc["added"]))
    g3 = (not hc["removed"]) and hc_added <= TARGET_ENTRIES and len(hc_added) in (0, 11)

    print("\n  G2 standard ADDED == exactly the 11 (set identity) AND REMOVED 0 :",
          "PASS" if g2 else "FAIL")
    print("  G3 high-conf REMOVED 0 AND every ADDED inside the 11 AND |ADDED| in {0,11} :",
          "PASS" if g3 else "FAIL")

    (work / "delta.json").write_text(json.dumps(
        {"standard": std, "high_confidence": hc, "G2": g2, "G3": g3}, indent=2))
    print(f"\n  written: {work / 'delta.json'}")
    return 0 if (g2 and g3) else 1


if __name__ == "__main__":
    raise SystemExit(main())
