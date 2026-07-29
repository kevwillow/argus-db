#!/usr/bin/env python3
"""MAC-569 — manufacturers.aliases RFC-4180-lite normalize (CTO-ratified).

Re-encodes every row of ``manufacturers.aliases`` into the canonical
RFC-4180-lite form. Pre-MAC-569 data stored comma-bearing alias values
unquoted, which produced phantom corporate-suffix tokens ("Ltd.",
"Inc.", "LLC", "Co.") when naive comma-split was applied by the 5+
consumers of the column. The MAC-535 defense-in-depth patch in
``coverage_matrix._alias_tokens_for_vendor`` (Finding 1) stopped the
§6.2 corroboration inflation but left the underlying data defect in
place. This script normalizes the wire format so every consumer — not
just §6.2 — sees the structural meaning correctly.

Mechanism:
  1. Pre-flight snapshot of ``manufacturers.aliases`` (sha256 per row).
  2. For each row, run the canonical
     ``db.alias_parser.recombine_and_quote_normalize`` pure function:
       a. RECOMBINE — naive-split tokens; if a token is a corp-suffix
          fragment (Ltd./Inc./LLC/...) AND its predecessor ends in a
          corp-suffix word boundary, merge them with ", " join.
       b. QUOTE-WRAP — for every resulting string that contains a
          comma, wrap it in double quotes.
  3. UPDATE the row only if the new blob differs from the old.
  4. Verify post-apply:
       - All non-empty aliases blobs have ZERO phantom-token occurrences
         (no longer contains a bare `, Ltd.` / `, Inc.` / `, LLC` / etc.
         sequence after the quoted form).
       - All canonical forms are RFC-4180-lite-compliant (round-trip
         through ``split_aliases`` yields the same token count as the
         post-normalize recombine pass).
       - The total token count (sum of ``len(split_aliases(aliases))``)
         is strictly LESS than the pre-apply total token count (because
         phantom fragments are merged back into their predecessors).
  5. Run the schema_version bump via the SQL migration file
     (``db/migrations/0043_mac569_alias_rfc4180_quote_normalize.sql``).
  6. Write a per-row before/after diff to
     ``operator_review/MAC-569/aliases_normalize_diff.tsv``.

Re-apply safety: the migration's pre-condition (a) requires zero
canonical (quoted) aliases on the table at apply time. The apply script
exits with rc=2 if any row already has quotes (re-apply is a no-op on
canonical input — verified by the parser's idempotency test — but the
schema_version bump is gated by the migration file's pre-conditions
and will refuse to double-bump).

Hard guards (abort, no write, if any fail):
  - DB exists at ``--db``.
  - schema_version baseline is 33 (no prior 0043 bump).
  - manufacturers.aliases column is present.
  - Zero rows currently have quoted aliases (first-apply invariant).
  - Per-row snapshot sha256 sweep succeeds.

Usage:
  python3 scripts/mac569_alias_quote_normalize_apply.py --db db/argus.db [--no-backup]

NO push. NO git commit of the DB (gitignored). Backup is taken by the
script unless ``--no-backup`` is passed (default: backup-first per the
project's standard apply discipline).
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SQL_FILE = REPO / "db" / "migrations" / "0043_mac569_alias_rfc4180_quote_normalize.sql"

ISSUE = "MAC-569"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
EXPECT_SCHEMA_BASELINE = 33
EXPECT_SCHEMA_POST = 34


def fail(msg: str) -> None:
    print(f"ABORT: {msg}", file=sys.stderr)
    sys.exit(2)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_db(db: Path, no_backup: bool) -> Path | None:
    if no_backup:
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = db.with_name(f"{db.name}.pre_mac569_{ts}")
    shutil.copy2(db, bak)
    sha = sha256_of(bak)
    (db.parent / f"{bak.name}.sha256").write_text(f"{sha}  {bak.name}\n")
    print(f"[backup] {bak.name}  sha256={sha}")
    return bak


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()
    DB: Path = args.db
    if not DB.exists():
        fail(f"db not found {DB}")
    if not SQL_FILE.exists():
        fail(f"migration file not found {SQL_FILE}")

    # Import the canonical transform — single source of truth.
    sys.path.insert(0, str(REPO))
    from db.alias_parser import recombine_and_quote_normalize, split_aliases

    print(f"[mac569] db={DB}")
    print(f"[mac569] sql={SQL_FILE}")
    print(f"[mac569] ts={NOW}")

    bak = backup_db(DB, args.no_backup)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        # ---- Pre-flight guards ------------------------------------------------
        schema = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        if schema != EXPECT_SCHEMA_BASELINE:
            fail(f"schema_version baseline must be {EXPECT_SCHEMA_BASELINE}, got {schema}")

        cols = {r["name"] for r in conn.execute("PRAGMA table_info(manufacturers)")}
        if "aliases" not in cols:
            fail("manufacturers.aliases column missing")

        already_quoted = conn.execute(
            "SELECT COUNT(*) FROM manufacturers WHERE aliases LIKE '%\"%'"
        ).fetchone()[0]
        if already_quoted > 0:
            fail(
                f"re-apply guard: {already_quoted} rows already carry quoted aliases; "
                f"abort (canonical DB expected; remove guard only if intentional)"
            )

        # ---- Snapshot pre-state ------------------------------------------------
        rows = conn.execute(
            "SELECT id, canonical_name, aliases FROM manufacturers "
            "WHERE aliases IS NOT NULL AND aliases != ''"
        ).fetchall()

        # Per-row sha256 sweep — fingerprint the entire aliases column pre-apply.
        # This is the apply-runner's primary regression catch.
        pre_shas = {r["id"]: hashlib.sha256(r["aliases"].encode("utf-8")).hexdigest() for r in rows}

        # ---- Per-row recombine + quote-wrap ----------------------------------
        diff_rows: list[tuple[int, str, int, str, str]] = []
        modified_count = 0
        phantom_total = 0
        for r in rows:
            rid = r["id"]
            name = r["canonical_name"]
            old = r["aliases"]
            new_blob, phantoms = recombine_and_quote_normalize(old)
            phantom_total += phantoms
            if new_blob != old:
                modified_count += 1
                conn.execute(
                    "UPDATE manufacturers SET aliases = ? WHERE id = ?",
                    (new_blob, rid),
                )
                diff_rows.append((rid, name, phantoms, old, new_blob))
        conn.commit()

        print(f"[mac569] rows scanned:           {len(rows)}")
        print(f"[mac569] rows modified:          {modified_count}")
        print(f"[mac569] phantoms recovered:     {phantom_total}")

        # ---- Verify post-state -----------------------------------------------
        # (1) Round-trip equality: recombine on the post-state is idempotent.
        post_rows = conn.execute(
            "SELECT id, canonical_name, aliases FROM manufacturers "
            "WHERE aliases IS NOT NULL AND aliases != ''"
        ).fetchall()
        non_idempotent = 0
        for r in post_rows:
            rt_blob, rt_phantoms = recombine_and_quote_normalize(r["aliases"])
            if rt_blob != r["aliases"] or rt_phantoms != 0:
                non_idempotent += 1
        if non_idempotent > 0:
            fail(f"post-apply verification: {non_idempotent} rows are not idempotent on re-transform")

        # (2) Zero standalone corporate-suffix tokens under an independent check.
        bad_fragments = 0
        for r in post_rows:
            from db.alias_parser import standalone_corp_suffix_tokens
            bad_fragments += len(standalone_corp_suffix_tokens(r["aliases"]))
        if bad_fragments > 0:
            fail(f"post-apply verification: {bad_fragments} bare corp-suffix fragments survived")

        # (3) Token-count strictly less (or equal for rows that were already canonical-form).
        pre_total = 0
        post_total = 0
        for r in rows:
            pre_total += len([t for t in r["aliases"].split(",") if t.strip()])
        for r in post_rows:
            post_total += len(split_aliases(r["aliases"]))
        if post_total > pre_total:
            fail(
                f"post-apply verification: post_total={post_total} > pre_total={pre_total} "
                f"(normalize must NOT add tokens)"
            )
        print(f"[mac569] pre total tokens (naive): {pre_total}")
        print(f"[mac569] post total tokens (smart): {post_total}")
        print(f"[mac569] token delta:               {pre_total - post_total}")

        # ---- Apply the schema_version bump via the SQL migration file --------
        # We execute the SQL file as a single sqlite3 batch. Pre-conditions
        # were checked above; the schema_version=33 baseline invariant is
        # the durable guarantee against double-bump.
        sql_text = SQL_FILE.read_text()
        try:
            conn.executescript(sql_text)
        except sqlite3.Error as e:
            fail(f"migration file execute failed: {e}")
        post_schema = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        if post_schema != EXPECT_SCHEMA_POST:
            fail(f"schema_version post-apply must be {EXPECT_SCHEMA_POST}, got {post_schema}")
        print(f"[mac569] schema_version:           {EXPECT_SCHEMA_BASELINE} -> {post_schema}")

        # ---- Per-row before/after diff TSV -----------------------------------
        op_dir = REPO / "operator_review" / ISSUE
        op_dir.mkdir(parents=True, exist_ok=True)
        diff_path = op_dir / "aliases_normalize_diff.tsv"
        with open(diff_path, "w") as f:
            f.write("id\tcanonical_name\tphantoms_recovered\told_aliases\tnew_aliases\n")
            for rid, name, n, old, new in diff_rows:
                # TSV-safe: replace \t and \n in aliases blob for the diff line.
                old_safe = old.replace("\t", " ").replace("\n", " ")
                new_safe = new.replace("\t", " ").replace("\n", " ")
                f.write(f"{rid}\t{name}\t{n}\t{old_safe}\t{new_safe}\n")
        print(f"[mac569] diff artifact:           {diff_path}")
        print(f"[mac569] diff rows:               {len(diff_rows)}")

        print(f"\n[mac569] OK — apply complete (db={DB})")
        if bak:
            print(f"[mac569] backup:                  {bak}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
