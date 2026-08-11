#!/usr/bin/env python3
"""MAC-663 G5 — prove mig-0054's write gate is fail-closed and METHOD-INDEPENDENT.

CEO_RATIFICATION.md §6 G5: "The write gate must be method-independent ... Prove the
gate on a scratch copy first: a blocked write must leave the file byte-identical by
sha256."

The hazard being tested (MAC-535 -> MAC-642 -> MAC-661): a `CHECK(ok=1)` on a TEMP
table aborts only its own INSERT. The CLI then walks on to COMMIT and the migration
half-applies while its stderr reads as if it stopped. `.bail on` closes that on the
sqlite3 CLI path ONLY -- it is a dot-command and a no-op under
`conn.executescript()`, which is the path scripts/mac419_*, mac569_*, mac580_* use.
So arm 3 (`COUNT(*) FROM _mac663_go = 1` on every write) is what has to hold, and it
has to hold on BOTH runners.

Four arms, because a negative control alone cannot tell "the gate blocked it" from
"nothing would have been written anyway" (a vacuous PASS):

  A  POSITIVE CONTROL, CLI      clean copy, `sqlite3 db < mig`     -> MUST apply, 11 rows
  B  NEGATIVE CONTROL, CLI      seeded-bad copy, same command      -> MUST block, byte-identical
  C  NEGATIVE CONTROL, script   seeded-bad copy, executescript()   -> MUST block, byte-identical
  D  POSITIVE CONTROL, script   clean copy, executescript()        -> MUST apply, 11 rows

A and D prove the file is not inert. B and C prove the gate stops it. Without A/D,
B/C would pass against a migration that writes nothing at all.

The seeded defect breaks PRE-1 (scope size 11 -> 10) by scoring ONE of the 11 rows
out of scope. That is the realistic failure: canonical moved under the migration.

Usage:
    python3 scripts/mac663_gate_proof.py --work <scratch-dir>
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CANONICAL = REPO / "db" / "argus.db"
MIGRATION = REPO / "db" / "migrations" / "0054_mac663_admit_sig_member_uuid_11.sql"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def applied_count(db: Path) -> int:
    """Rows carrying the migration's own provenance marker -- the post-state query.

    Counted from the DB, never from a process exit code: a sqlite3 exit of 1 fires
    both when it stopped and when it committed through failed guards (MAC-661).
    """
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return con.execute(
            "SELECT COUNT(*) FROM identifiers WHERE json_valid(notes) "
            "AND json_extract(notes,'$.mac663_admit.issue')='MAC-663'"
        ).fetchone()[0]
    finally:
        con.close()


def seed_defect(db: Path) -> None:
    """Break PRE-1: move one of the 11 out of the mutation scope (scope 11 -> 10)."""
    con = sqlite3.connect(db)
    try:
        con.execute("UPDATE identifiers SET confidence = 50 WHERE id = 42990")
        con.commit()
    finally:
        con.close()


def run_cli(db: Path) -> int:
    p = subprocess.run(f'sqlite3 "{db}" < "{MIGRATION}"', shell=True,
                       capture_output=True, text=True)
    return p.returncode


def run_executescript(db: Path) -> int:
    """The runner where `.bail on` is a no-op. Strip it -- it is a syntax error here."""
    sql = "\n".join(l for l in MIGRATION.read_text().splitlines()
                    if l.strip() != ".bail on")
    con = sqlite3.connect(db)
    try:
        con.executescript(sql)
        con.commit()
        return 0
    except sqlite3.Error:
        return 1
    finally:
        con.close()


def arm(name: str, work: Path, runner, seeded: bool, expect_applied: int) -> bool:
    db = work / f"{name}.db"
    shutil.copy2(CANONICAL, db)
    if seeded:
        seed_defect(db)
    before = sha256(db)
    rc = runner(db)
    after = sha256(db)
    n = applied_count(db)

    identical = before == after
    ok = (n == expect_applied)
    if expect_applied == 0:
        ok = ok and identical

    print(f"\n  [{name}] seeded={seeded} runner={runner.__name__}")
    print(f"    exit code        : {rc}   (NOT the verdict -- see MAC-661)")
    print(f"    sha before       : {before}")
    print(f"    sha after        : {after}")
    print(f"    byte-identical   : {identical}")
    print(f"    rows marked      : {n}   (expected {expect_applied})")
    print(f"    -> {'PASS' if ok else 'FAIL'}")
    db.unlink()
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True, type=Path)
    args = ap.parse_args()
    work: Path = args.work
    work.mkdir(parents=True, exist_ok=True)

    print(f"migration : {MIGRATION.name}")
    print(f"canonical : {CANONICAL}  sha256 {sha256(CANONICAL)}")

    results = {
        "A_positive_cli": arm("A_positive_cli", work, run_cli, False, 11),
        "B_negative_cli": arm("B_negative_cli", work, run_cli, True, 0),
        "C_negative_executescript": arm("C_negative_executescript", work,
                                        run_executescript, True, 0),
        "D_positive_executescript": arm("D_positive_executescript", work,
                                        run_executescript, False, 11),
    }
    print("\n  ---- G5 verdict ----")
    for k, v in results.items():
        print(f"    {k:28s} {'PASS' if v else 'FAIL'}")
    allok = all(results.values())
    print(f"\n  G5 {'PASS' if allok else 'FAIL'} — gate is fail-closed on BOTH runners, "
          f"and the migration is proven non-inert by the positive arms.")
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())
