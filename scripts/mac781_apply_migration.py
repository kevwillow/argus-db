#!/usr/bin/env python3
"""Apply 0064_mac781_argus_export_anchor_repair.sql to a scratch DB.

Run 1: applies the migration on a scratch copy of db/argus.db. Captures
sha256 of the scratch DB before and after, plus row counts and the new
gate (scripts/check_mac781_anchor_clause.py) end-to-end with rc=0.

Run 2: re-runs the same migration against the same scratch DB AFTER run 1
landed. Pre-state guards fail closed (PRE-7: 0 rows already stamped with
mac781_audit; PRE-8: 0 rows already carry the new cite substring). The DB
is unchanged -- proven by sha256 byte-identical hash of the scratch DB
before and after run 2.

Hard rules (from brief):
  - Read /home/kev/argus/db/argus.db in mode=ro for the source copy.
  - Use a scratch copy at SCRATCH_DB so canonical is never touched.
  - schema_version must be unchanged at 35.
  - active / total row counts must be unchanged at DELTA = 0.
  - POST-8: scripts/check_mac781_anchor_clause.py exits 0 against the
    post-migration canonical (anchor resolves to 1 line, clause matches,
    9 migrated rows present).
  - Re-run (run 2) leaves the scratch DB byte-identical to post-run-1.

RELOCATION (Rev 3). Originally at `operator_review/MAC-781/apply_migration.py`,
which MAC-764 rewrites from the working tree. Copied here to
`scripts/mac781_apply_migration.py` so the wrapper survives the MAC-764
path purge. Source of truth is this copy; the operator_review copy will
be removed by the MAC-764 rewrite. The CEO ruling at MAC-781 comment
103cbe96 reversed the original "staged behind MAC-764" sequencing, so
the migration now runs BEFORE the MAC-764 force-push (so the corrected
export rides the release), not after.
"""
import argparse
import hashlib
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "db" / "argus.db"
SCRATCH_DIR = ROOT / "scratch_mac781"
MIGRATION = ROOT / "db/migrations/0064_mac781_argus_export_anchor_repair.sql"
GATE = ROOT / "scripts/check_mac781_anchor_clause.py"

CLAUSE_SUBSTRING = (
    "Distinguishes general-purpose CCTV from existing `covert_cam`"
)
NEW_ANCHOR_SUBSTRING = (
    "docs/engineering/BIBLE_AMENDMENTS.md#mac781-cp33-s2-1-cctv_camera"
)


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _row_count(db: pathlib.Path, sql: str) -> int:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return con.execute(sql).fetchone()[0]
    finally:
        con.close()


def _schema_version(db: pathlib.Path) -> int:
    return _row_count(db, "SELECT MAX(version) FROM schema_version") \
        if _row_count(db, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='schema_version'") \
        else 0


def _run_sqlite(db: pathlib.Path, sql_file: pathlib.Path) -> int:
    """Run a .sql file via the sqlite3 CLI against the given DB."""
    proc = subprocess.run(
        ["sqlite3", str(db), f".read {sql_file}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"  sqlite3 rc={proc.returncode}")
        print(f"  stdout: {proc.stdout}")
        print(f"  stderr: {proc.stderr}")
    return proc.returncode


def _run_gate(db: pathlib.Path) -> int:
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--db", str(db),
            "--expected-clause", CLAUSE_SUBSTRING,
            "--new-anchor", NEW_ANCHOR_SUBSTRING,
        ],
        capture_output=True,
        text=True,
    )
    print(f"  gate rc={proc.returncode}")
    print(f"  gate stdout:\n{proc.stdout}")
    if proc.stderr:
        print(f"  gate stderr: {proc.stderr}")
    return proc.returncode


def _assert_invariants(label: str, db: pathlib.Path, expected_active: int, expected_total: int) -> None:
    active = _row_count(db, "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL")
    total = _row_count(db, "SELECT COUNT(*) FROM identifiers")
    sv = _schema_version(db)
    print(f"  [{label}] schema_version={sv}  active={active}  total={total}")
    assert sv == 35, f"schema_version changed: {sv}"
    assert active == expected_active, f"active row count moved: {active} vs {expected_active}"
    assert total == expected_total, f"total row count moved: {total} vs {expected_total}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run", choices=["1", "2", "both"], default="both")
    parser.add_argument("--db", default=str(CANONICAL),
                        help="Source DB to copy from (default: canonical). Run 2 "
                             "ignores this and uses the post-run-1 scratch.")
    args = parser.parse_args()

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    scratch = SCRATCH_DIR / "argus.db"
    post1_sha = None

    if args.run in ("1", "both"):
        source = pathlib.Path(args.db)
        if not source.exists():
            print(f"ERROR: source DB not found: {source}", file=sys.stderr)
            return 2

        print(f"copying {source} -> {scratch}")
        shutil.copy2(source, scratch)

        pre_active = _row_count(scratch, "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL")
        pre_total = _row_count(scratch, "SELECT COUNT(*) FROM identifiers")
        pre_sha = _sha256(scratch)
        print(f"  pre-run sha256: {pre_sha}")
        print(f"  pre-run active: {pre_active}")
        print(f"  pre-run total:  {pre_total}")
        _assert_invariants("pre-run", scratch, pre_active, pre_total)

        print(f"\n=== RUN 1: applying {MIGRATION.name} ===")
        rc = _run_sqlite(scratch, MIGRATION)
        if rc != 0:
            print(f"FAIL: sqlite3 returned {rc} on run 1")
            return rc or 1

        post1_sha = _sha256(scratch)
        print(f"  post-run-1 sha256: {post1_sha}")
        _assert_invariants("post-run-1", scratch, pre_active, pre_total)

        if post1_sha == pre_sha:
            print("FAIL: post-run-1 sha256 unchanged -- migration had no effect")
            return 1

        print("\n=== POST-8: running check_mac781_anchor_clause gate ===")
        gate_rc = _run_gate(scratch)
        if gate_rc != 0:
            print(f"FAIL: gate returned {gate_rc}")
            return 1

        if args.run == "1":
            return 0

    if args.run in ("2", "both"):
        if post1_sha is None:
            # User asked for run 2 only -- load the scratch as-is
            if not scratch.exists():
                print(f"ERROR: scratch DB not found: {scratch}; run --run 1 first", file=sys.stderr)
                return 2
            post1_sha = _sha256(scratch)
        print(f"\n=== RUN 2: re-applying {MIGRATION.name} against post-run-1 ===")
        rc = _run_sqlite(scratch, MIGRATION)
        # Run 2 must FAIL closed -- pre-state guards catch the already-mutated
        # state. sqlite3 exits non-zero on the .bail on directive.
        if rc == 0:
            print("FAIL: run 2 exited 0; pre-state guards did not fail closed")
            return 1
        print(f"  run 2 sqlite3 rc={rc} (expected non-zero -- guards caught the re-run)")

        post2_sha = _sha256(scratch)
        print(f"  post-run-2 sha256: {post2_sha}")
        if post2_sha != post1_sha:
            print(f"FAIL: post-run-2 sha256 moved: {post2_sha} vs {post1_sha}")
            return 1
        print(f"  sha256 byte-identical after re-run: PASS")

    print("\nALL INVARIANTS HELD.")
    return 0


if __name__ == "__main__":
    sys.exit(main())