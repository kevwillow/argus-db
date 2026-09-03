#!/usr/bin/env python3
"""Validate the shipped export artifacts against their documented contract.

Runs entirely on files tracked in git: no canonical DB, no raw/ artifacts, no
network. That is the point -- this is the part of Argus anyone can re-verify
from a fresh public clone.

Asserts the TRUE semantics of the artifacts, not the aspirational ones. In
particular ``argus_record_id`` is NOT asserted unique: it is a content-derived
pattern key, and 15 ids are shared by more than one row, covering 45 rows in
total (a surplus of 30 rows beyond one-per-id). All three of those numbers are
pinned separately, because pinning only the surplus is a weak detector and
because reading one of them as another is the exact error that shipped a false
number into four documents.

Exit status:
    0  every pinned fact still holds
    1  one or more contract violations
    2  an artifact is missing or structurally unreadable

Usage:
    python3 scripts/ci/check_export_contract.py
    python3 scripts/ci/check_export_contract.py --quiet          # only failures
    python3 scripts/ci/check_export_contract.py --exports DIR    # point at a fixture
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.export_contract import (  # noqa: E402
    EXPORTS_DIR,
    ExportPaths,
    Report,
    format_report,
    run_contract,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print only failing checks (still prints the summary line)",
    )
    parser.add_argument(
        "--exports",
        type=Path,
        default=EXPORTS_DIR,
        metavar="DIR",
        help=(
            "directory holding the four export artifacts (default: exports/). "
            "Point this at a fixture to prove the validator actually fails on a "
            "corrupted artifact -- a check never seen to fail is not known to work."
        ),
    )
    args = parser.parse_args(argv)

    paths = ExportPaths.for_dir(args.exports)

    missing = [str(p) for p in paths.all_paths() if not p.is_file()]
    if missing:
        print("check_export_contract: FAIL — export artifacts missing:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 2

    try:
        report = run_contract(paths)
    except (ValueError, OSError) as exc:
        print(f"check_export_contract: FAIL — artifact unreadable: {exc}", file=sys.stderr)
        return 2

    if args.quiet:
        format_report(Report(report.failures) if report.failures else Report([]))
    else:
        format_report(report)

    total = len(report.findings)
    failed = len(report.failures)
    print()
    print(
        f"check_export_contract: {total - failed} PASS, {failed} FAIL "
        f"(of {total} pinned facts)"
    )
    if failed:
        print()
        print("Contract violations — the shipped artifacts no longer match the "
              "documented shape:")
        for f in report.failures:
            print(f"  {f.check}: expected {f.expected}, measured {f.measured}")
            if f.detail:
                print(f"      {f.detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
