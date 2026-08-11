#!/usr/bin/env python3
"""MAC-707 — derive the supersession-edge denominator for the C2 dominance sweep.

Why this exists
---------------
`schema_version` cannot frame the sweep: it tops out at version 35
(`0045_mac580_alias_suffix_completion`, applied 2026-07-29 03:48:57), so
migrations 0048, 0049, 0051, 0052, 0054 and 0055 are absent from the ledger even
though their effects are present in the data. Notes parsing cannot frame it
either: 330 of the 804 supersession edges in canonical carry no `macNNN` tag.

So the instrument is the migration files' actual UPDATE targets, each edge then
confirmed DB-side. This module derives that set and reports what it could not
parse rather than silently dropping it.

Statement splitting is tokenizer-based, not `str.split(";")`. A scanner that
splits on a bare semicolon mis-slices any statement containing a `;` inside a
string literal or a comment, which silently drops edges.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Migrations whose git author date is on/after the 2026-07-29 ruling. Derived by
# `git log -1 --format=%ad --date=short -- <path>`; 0043/0044/0045 are 2026-07-28
# and therefore out of frame.
IN_FRAME_MIGRATIONS = (
    "0048_mac537_ratified_harvest_ingest.sql",
    "0049_mac611_mac570_duplicate_emitted_key_supersession.sql",
    "0051_mac642_sig_member_uuid_retype.sql",
    "0052_mac641_mac586_tranche1_manufacturer_admission.sql",
    "0054_mac663_admit_sig_member_uuid_11.sql",
    "0055_mac691_vendor_flag_anchor_and_dts_withdraw.sql",
)


def split_statements(sql: str) -> list[str]:
    """Split SQL into statements, respecting string literals and comments.

    Handles: `'...'` (with `''` escape), `--` line comments, `/* */` block
    comments. Only a `;` seen outside all of those terminates a statement.
    """
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if ch == "'":
            buf.append(ch)
            i += 1
            while i < n:
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":  # escaped quote
                        buf.append("''")
                        i += 2
                        continue
                    buf.append("'")
                    i += 1
                    break
                buf.append(sql[i])
                i += 1
            continue
        if ch == "-" and nxt == "-":
            while i < n and sql[i] != "\n":
                i += 1
            continue
        if ch == "/" and nxt == "*":
            i += 2
            while i < n - 1 and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if ch == ";":
            statements.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if "".join(buf).strip():
        statements.append("".join(buf))
    return [s for s in statements if s.strip()]


_SET_SUPERSEDED = re.compile(r"superseded_by\s*=\s*(\d+)", re.IGNORECASE)
_WHERE_ID_EQ = re.compile(r"\bid\s*=\s*(\d+)", re.IGNORECASE)
_WHERE_ID_IN = re.compile(r"\bid\s+IN\s*\(([^)]*)\)", re.IGNORECASE)


def extract_edges(path: Path) -> tuple[list[tuple[int, int]], list[str]]:
    """Return (edges, unparsed) for one migration file.

    An edge is `(folded_id, survivor_id)`: the row being superseded and the row
    it points at. Statements that set `superseded_by` to a non-literal (a
    subquery, NULL, or a column reference) are returned in `unparsed` so they
    are reported, never silently dropped.
    """
    sql = path.read_text(encoding="utf-8")
    edges: list[tuple[int, int]] = []
    unparsed: list[str] = []
    for stmt in split_statements(sql):
        s = stmt.strip()
        if not re.match(r"^\s*UPDATE\s+identifiers\b", s, re.IGNORECASE):
            continue
        if "superseded_by" not in s.lower():
            continue
        # Only the SET clause assigns; a WHERE `superseded_by IS NULL` guard
        # carries no `=` and so never matches the assignment regex.
        set_part = s
        wpos = re.search(r"\bWHERE\b", s, re.IGNORECASE)
        where_part = s[wpos.end():] if wpos else ""
        if wpos:
            set_part = s[: wpos.start()]
        surv = _SET_SUPERSEDED.search(set_part)
        if not surv:
            if re.search(r"superseded_by\s*=", set_part, re.IGNORECASE):
                unparsed.append(" ".join(s.split())[:200])
            continue
        survivor = int(surv.group(1))
        ids: list[int] = []
        m_in = _WHERE_ID_IN.search(where_part)
        if m_in:
            ids = [int(x) for x in re.findall(r"\d+", m_in.group(1))]
        else:
            m_eq = _WHERE_ID_EQ.search(where_part)
            if m_eq:
                ids = [int(m_eq.group(1))]
        if not ids:
            unparsed.append(" ".join(s.split())[:200])
            continue
        for fid in ids:
            edges.append((fid, survivor))
    return edges, unparsed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(REPO_ROOT / "db" / "argus.db"))
    ap.add_argument("--migrations-dir", default=str(REPO_ROOT / "db" / "migrations"))
    ap.add_argument("--json-out", default=None)
    ap.add_argument(
        "--all-canonical",
        action="store_true",
        help="Also emit every supersession edge in canonical (superset control).",
    )
    args = ap.parse_args()

    mig_dir = Path(args.migrations_dir)
    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    print("=" * 72)
    print("C2 DENOMINATOR — supersession edges from in-frame migration files")
    print("=" * 72)

    all_edges: list[tuple[int, int]] = []
    per_file: dict[str, int] = {}
    total_unparsed: list[str] = []
    for name in IN_FRAME_MIGRATIONS:
        p = mig_dir / name
        if not p.exists():
            print(f"  MISSING {name}")
            continue
        edges, unparsed = extract_edges(p)
        per_file[name] = len(edges)
        all_edges.extend(edges)
        total_unparsed.extend(f"{name}: {u}" for u in unparsed)
        print(f"  {len(edges):>4} edges  {name}")
    if total_unparsed:
        print(f"\n  UNPARSED superseded_by assignments ({len(total_unparsed)}):")
        for u in total_unparsed:
            print(f"    ! {u}")

    # Dedup: the same edge asserted twice in one file is one edge.
    uniq = sorted(set(all_edges))
    print(f"\n  file-derived edges: {len(all_edges)} raw, {len(uniq)} distinct")

    # Confirm each edge DB-side. A file-asserted edge that is not present in
    # canonical was not applied (or was later reverted) and must not inflate
    # the denominator.
    confirmed: list[tuple[int, int]] = []
    missing: list[tuple[int, int]] = []
    for fid, sid in uniq:
        r = con.execute(
            "SELECT superseded_by FROM identifiers WHERE id = ?", (fid,)
        ).fetchone()
        if r is not None and r["superseded_by"] == sid:
            confirmed.append((fid, sid))
        else:
            got = None if r is None else r["superseded_by"]
            missing.append((fid, sid))
            print(f"    ! edge {fid}->{sid} NOT confirmed DB-side (actual: {got})")
    print(f"  DB-confirmed edges: {len(confirmed)}  (unconfirmed: {len(missing)})")

    payload: dict[str, object] = {
        "in_frame_migrations": list(IN_FRAME_MIGRATIONS),
        "per_file_edge_counts": per_file,
        "file_derived_distinct": len(uniq),
        "db_confirmed": [list(e) for e in confirmed],
        "db_confirmed_count": len(confirmed),
        "unconfirmed": [list(e) for e in missing],
        "unparsed": total_unparsed,
    }

    if args.all_canonical:
        cur = con.execute(
            "SELECT id, superseded_by FROM identifiers "
            "WHERE superseded_by IS NOT NULL ORDER BY id"
        )
        every = [(r["id"], r["superseded_by"]) for r in cur.fetchall()]
        # A self-loop is a withdrawal (tri-semantic), not a fold; it has no
        # distinct survivor to dominate, so it is reported separately.
        folds = [(f, s) for f, s in every if f != s]
        loops = [(f, s) for f, s in every if f == s]
        print(f"\n  ALL canonical supersession edges: {len(every)}")
        print(f"    folds (folded != survivor): {len(folds)}")
        print(f"    self-loops (withdrawals):   {len(loops)}")
        payload["all_canonical_count"] = len(every)
        payload["all_canonical_folds"] = [list(e) for e in folds]
        payload["all_canonical_selfloops"] = [list(e) for e in loops]

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\n  wrote {args.json_out}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
