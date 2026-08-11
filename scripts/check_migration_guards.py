#!/usr/bin/env python3
"""Gate: a migration's preconditions must be able to STOP its writes.

Background (MAC-535 -> MAC-642 -> MAC-661, CEO wake 208ce0f6 on MAC-661):

The house assertion idiom is

    CREATE TEMP TABLE _migNNNN_pre (ok INTEGER CHECK (ok = 1));
    INSERT INTO _migNNNN_pre(ok) SELECT CASE WHEN (<preconditions>) THEN 1 ELSE 0 END;

A failed precondition raises `CHECK constraint failed: ok = 1`. That aborts **the offending
INSERT only** -- not the transaction, and not the script. So on its own this idiom prints one
line to stderr and then every following write COMMITS anyway. That is strictly worse than no
guard, because the artifact reads as protected.

Two arms make it real, and a migration needs BOTH because the repo has two apply paths:

  arm 1  `.bail on`                          -- sqlite3 CLI only; a dot-command, and it is a
                                                SYNTAX ERROR under conn.executescript()
  arm 2  `AND (SELECT COUNT(*) FROM _migNNNN_pre) = <n>` on EVERY canonical write
                                             -- portable; a failed pre-guard leaves the temp
                                                table short, so every write matches zero rows

scripts/mac419_*, mac569_*, mac580_*_apply.py apply via conn.executescript(), so arm 1 alone
forfeits protection on the path this repo actually uses most.

Usage:
    python3 scripts/check_migration_guards.py            # gate new/unratified migrations
    python3 scripts/check_migration_guards.py --all      # include grandfathered, exit 0
    python3 scripts/check_migration_guards.py --drafts   # include db/migrations/_drafts/

Exit 1 if any non-grandfathered migration carries CHECK(ok=1) guards that cannot stop its
writes. Grandfathered files are already APPLIED; they are listed, never silently skipped.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sqlite3
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "db", "argus.db")

# Already applied to canonical before this gate existed. Re-editing an applied migration
# rewrites history that the DB no longer reflects, so these are recorded, not fixed.
# mig-0041 additionally carries its own `WARNING: NOT RE-APPLY-SAFE` banner at line 6.
GRANDFATHERED = {
    "0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession.sql",
    "0035_mac486_dahua_d54ace3f_ble_service_uuid_fp_supersession.sql",
    "0036_mac489_non_cohort_ble_service_uuid_fp_supersession.sql",
    "0037_mac511_wave5_dq_cleanup_supersession.sql",
    "0039_mac528_flock_glob_ssid_exact_withdraw.sql",
    "0040_mac531_v170_data_cleanup_supersession.sql",
    "0041_mac533_ipvm_public_directory_attribution_ingest.sql",
    "0042_mac542_procurement_boundary_quarantine.sql",
    "0043_mac569_alias_rfc4180_quote_normalize.sql",
    "0044_mac523_shodan_phase1_cctv_camera_ingest.sql",
    "0045_mac580_alias_suffix_completion.sql",
    "0048_mac537_ratified_harvest_ingest.sql",
}

GUARD_DECL = re.compile(r"CREATE\s+TEMP\s+TABLE\s+(\w+)\s*\(\s*ok\s+INTEGER\s+CHECK", re.I)
CHECK_OK = re.compile(r"CHECK\s*\(\s*ok\s*=\s*1\s*\)", re.I)
BAIL = re.compile(r"^\.bail\s+on\s*$", re.M)
WRITE = re.compile(r"^\s*(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+[\"']?(\w+)", re.I)


def strip_comments(sql: str) -> str:
    """Blank out -- and /* */ comments WITHOUT breaking string literals.

    Literal-aware on purpose: migration prose lives inside quoted JSON, and a naive
    line.split('--') both loses code and lets a table name mentioned in a comment leak
    into the guard-table set (which would mask a real unguarded write).
    Offsets and newlines are preserved so reported line numbers stay true.
    """
    out: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            out.append(sql[i : j + 1])
            i = j + 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", sql[i:j]))
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def statements(sql: str):
    """(start_line, text) per statement, split with sqlite3's own tokenizer.

    Required rather than splitting on ';': migration `reason` strings contain semicolons
    (e.g. "...negative fixture); that disagreement is retained..."), and a naive split
    severs a write from the count-guard on its own WHERE clause -- reporting a fully
    guarded migration as fragile.
    """
    buf, start, line = "", None, 1
    for raw in sql.split("\n"):
        # `not buf.strip()`, not `not buf`: after a yield the buffer accumulates the
        # blank separator lines, which are truthy and would pin start at None forever.
        if not buf.strip() and raw.strip():
            start = line
        buf += raw + "\n"
        if sqlite3.complete_statement(buf):
            yield start, buf
            buf, start = "", None
        line += 1
    if buf.strip():
        yield start or line, buf


def canonical_tables() -> set[str]:
    if not os.path.exists(DB):
        sys.exit(f"cannot resolve canonical tables: {DB} missing")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        return {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
    finally:
        con.close()


def analyze(path: str, canon: set[str]) -> dict | None:
    raw = open(path, encoding="utf-8").read()
    code = strip_comments(raw)
    if not CHECK_OK.search(code):
        return None
    guard_tbls = sorted(set(GUARD_DECL.findall(code)))
    alt = "|".join(map(re.escape, guard_tbls)) or "__no_guard_table__"
    grx = re.compile(r"COUNT\(\*\)\s*FROM\s+(?:%s)\s*\)\s*=\s*\d+" % alt, re.I)
    pre_inserts = {
        t: len(re.findall(r"INSERT\s+INTO\s+%s\s*\(\s*ok\s*\)" % re.escape(t), code, re.I))
        for t in guard_tbls
    }
    writes, guarded, unguarded = 0, 0, []
    for ln, stmt in statements(code):
        m = WRITE.match(stmt)
        if not m or m.group(2) not in canon:
            continue
        writes += 1
        if grx.search(stmt):
            guarded += 1
        else:
            unguarded.append(ln)
    return {
        "file": os.path.basename(path),
        "path": path,
        "bail": bool(BAIL.search(code)),
        "guard_tbls": guard_tbls,
        "pre_inserts": pre_inserts,
        "writes": writes,
        "guarded": guarded,
        "unguarded": unguarded,
    }


def verdict(r: dict) -> tuple[str, bool]:
    """-> (label, is_failure)"""
    if r["writes"] == 0:
        return "no canonical DML", False
    if r["unguarded"]:
        if r["bail"]:
            return (
                "CLI-ONLY — %d write(s) unguarded; no protection under executescript()"
                % len(r["unguarded"]),
                True,
            )
        return "FRAGILE — guards cannot stop %d write(s)" % len(r["unguarded"]), True
    if not r["bail"]:
        return "portable arm only — add `.bail on` for the CLI path", True
    return "FAIL-CLOSED (both arms)", False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="include grandfathered; always exit 0")
    ap.add_argument("--drafts", action="store_true", help="also scan db/migrations/_drafts/")
    args = ap.parse_args()

    canon = canonical_tables()
    paths = sorted(glob.glob(os.path.join(REPO, "db/migrations/*.sql")))
    if args.drafts:
        paths += sorted(glob.glob(os.path.join(REPO, "db/migrations/_drafts/*.draft")))

    results = [r for r in (analyze(p, canon) for p in paths) if r]
    failures = []

    print(f"{'MIGRATION':<62}{'BAIL':>5}{'WRITES':>7}{'GRD':>5}{'UNGRD':>6}  VERDICT")
    print("-" * 122)
    for r in results:
        label, failed = verdict(r)
        gf = r["file"] in GRANDFATHERED
        if failed and gf:
            label += "  [GRANDFATHERED — applied]"
        elif failed:
            failures.append(r)
        print(
            f"{r['file']:<62}{'yes' if r['bail'] else 'no':>5}{r['writes']:>7}"
            f"{r['guarded']:>5}{len(r['unguarded']):>6}  {label}"
        )
        if failed and r["unguarded"]:
            head = ", ".join(str(x) for x in r["unguarded"][:10])
            more = "" if len(r["unguarded"]) <= 10 else f", +{len(r['unguarded']) - 10} more"
            print(f"{'':<62}{'':>23}  unguarded write(s) at line {head}{more}")

    # Guard-constant sanity: COUNT(*)=<n> must equal the number of precondition INSERTs.
    # An off-by-one here is a silently vacuous guard -- it never matches, so the writes
    # never fire, or it always matches, so they always do.
    print("\nguard-constant check (COUNT(*) = n  vs  number of precondition INSERTs):")
    for r in results:
        code = strip_comments(open(r["path"], encoding="utf-8").read())
        for t, n in r["pre_inserts"].items():
            consts = sorted(set(
                int(c) for c in re.findall(
                    r"COUNT\(\*\)\s*FROM\s+%s\s*\)\s*=\s*(\d+)" % re.escape(t), code, re.I)))
            if not consts:
                continue
            ok = consts == [n]
            print(f"  {r['file']:<58} {t:<18} inserts={n} guard_consts={consts} "
                  f"{'OK' if ok else '*** MISMATCH ***'}")
            if not ok and r["file"] not in GRANDFATHERED:
                failures.append(r)

    print()
    if args.all:
        print(f"--all: reporting only. {len(failures)} non-grandfathered failure(s).")
        return 0
    if failures:
        print(f"FAIL — {len({f['file'] for f in failures})} migration(s) whose preconditions "
              f"cannot stop their writes:")
        for f in sorted({f["file"] for f in failures}):
            print(f"  - {f}")
        print("\nFix: gate every canonical write with "
              "`AND (SELECT COUNT(*) FROM _migNNNN_pre) = <n>` and add `.bail on`.")
        return 1
    print("PASS — every non-grandfathered migration fails closed on both arms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
