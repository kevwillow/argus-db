#!/usr/bin/env python3
"""MAC-755 negative control — prove every repointed cohort file can still go red.

Repointing the cohort tests at a frozen extraction-time snapshot made them pass.
That proves nothing on its own: a test that has been quietly re-baselined into a
change-detector also passes.  So for each repointed file this driver perturbs the
**extractor's output** and requires the file to FAIL.

A file that stays green under a perturbation is reported as a HOLE — the gate is
not actually load-bearing for that class of defect.

Modes (see tests/_mac755_perturb.py):
  drop     — remove one promoted candidate  (catches counts re-baselined to 0)
  verdict  — flip a net-new verdict to held (catches the net-new gate going vacuous)
  cite     — corrupt an identifier/byte-form (catches cite-faithfulness going vacuous)

Usage:
    python3 scripts/mac755_negative_control.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"

FILES = [
    "test_cohort1_ble_trackers.py",
    "test_cohort2_alpr_copcar.py",
    "test_cohort3_bletracker.py",
    "test_cohort3_drones.py",
    "test_cohort4_smartlock.py",
    "test_cohort5_consumer.py",
    "test_cohort6_petkid.py",
]
MODES = ["drop", "verdict", "cite"]


def run(path: str, mode: str) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"
    env["MAC755_PERTURB"] = mode
    # the plugin lives in tests/, which is not a package
    env["PYTHONPATH"] = str(TESTS) + os.pathsep + env.get("PYTHONPATH", "")
    p = subprocess.run(
        [sys.executable, "-m", "pytest", f"tests/{path}", "-p", "_mac755_perturb",
         "-q", "--tb=no", "--no-header"],
        cwd=REPO, env=env, capture_output=True, text=True)
    # name the first failing test, as evidence of WHICH gate caught it
    caught = ""
    for line in p.stdout.splitlines():
        if line.startswith(("FAILED ", "ERROR ")):
            caught = line.split(" ")[1].split("::")[-1]
            break
    return p.returncode, caught


def main() -> int:
    print("MAC-755 negative control — each cell must go RED\n")
    header = f"{'file':32s}" + "".join(f"{m:>26s}" for m in MODES)
    print(header)
    print("-" * len(header))
    holes = []
    for f in FILES:
        row = f"{f:32s}"
        for mode in MODES:
            rc, caught = run(f, mode)
            if rc != 0:
                row += f"{'RED ' + (caught[:20] or ''):>26s}"
            else:
                row += f"{'*** STAYED GREEN ***':>26s}"
                holes.append((f, mode))
        print(row)
    print()
    if holes:
        print(f"{len(holes)} HOLE(S) — these gates are not load-bearing:")
        for f, m in holes:
            print(f"  {f}  mode={m}")
        return 1
    print(f"All {len(FILES) * len(MODES)} perturbations caught. "
          "Every repointed file is still a live gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
