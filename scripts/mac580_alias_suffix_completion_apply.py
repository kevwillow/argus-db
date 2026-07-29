#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SQL_FILE = REPO / "db/migrations/0045_mac580_alias_suffix_completion.sql"
EXPECTED_SCHEMA_BASELINE = 34
EXPECTED_SCHEMA_POST = 35


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True, type=Path)
    args = parser.parse_args()
    db = args.db
    if not db.exists():
        raise SystemExit(f"missing database: {db}")

    sys.path.insert(0, str(REPO))
    from db.alias_parser import recombine_and_quote_normalize, standalone_corp_suffix_tokens

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = db.with_name(f"{db.name}.pre_mac580_{timestamp}")
    shutil.copy2(db, backup)
    backup_sha = sha256_file(backup)
    backup.with_suffix(backup.suffix + ".sha256").write_text(
        f"{backup_sha}  {backup.name}\n", encoding="utf-8"
    )

    connection = sqlite3.connect(db)
    try:
        schema = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        if schema != EXPECTED_SCHEMA_BASELINE:
            raise RuntimeError(f"schema baseline must be {EXPECTED_SCHEMA_BASELINE}, got {schema}")

        pre_rows = connection.execute(
            "SELECT id, canonical_name, aliases FROM manufacturers ORDER BY id"
        ).fetchall()
        identifiers_before = connection.execute("SELECT COUNT(*) FROM identifiers").fetchone()[0]
        expected = {
            row[0]: recombine_and_quote_normalize(row[2])[0] if row[2] else row[2]
            for row in pre_rows
        }
        changed_ids = {row[0] for row in pre_rows if expected[row[0]] != row[2]}

        connection.execute("BEGIN IMMEDIATE")
        for row_id in sorted(changed_ids):
            connection.execute(
                "UPDATE manufacturers SET aliases = ? WHERE id = ?",
                (expected[row_id], row_id),
            )

        post_rows = connection.execute(
            "SELECT id, canonical_name, aliases FROM manufacturers ORDER BY id"
        ).fetchall()
        post_by_id = {row[0]: row for row in post_rows}
        actual_changed_ids = {
            before[0]
            for before in pre_rows
            if before[2] != post_by_id[before[0]][2]
        }
        if actual_changed_ids != changed_ids:
            raise RuntimeError("modified-row set differs from transform prediction")
        if any(post_by_id[row_id][2] != expected[row_id] for row_id in expected):
            raise RuntimeError("post-state differs from byte-exact transform")
        if any(row[2] and recombine_and_quote_normalize(row[2]) != (row[2], 0) for row in post_rows):
            raise RuntimeError("transform is not idempotent on post-state")
        if any(before[1] != post_by_id[before[0]][1] for before in pre_rows):
            raise RuntimeError("canonical_name drift detected")
        identifiers_after = connection.execute("SELECT COUNT(*) FROM identifiers").fetchone()[0]
        if identifiers_after != identifiers_before:
            raise RuntimeError("identifiers row count changed")
        survivors = [
            (row[0], row[1], token)
            for row in post_rows
            for token in standalone_corp_suffix_tokens(row[2])
        ]
        if survivors:
            raise RuntimeError(f"standalone corporate suffixes survived: {survivors!r}")

        pre_total = sum(len(r["aliases"].split(",")) if r["aliases"] else 0 for r in pre_rows)
        post_total = sum(len(split_aliases(r["aliases"])) for r in post_rows)
        phantom_total = sum(
            recombine_and_quote_normalize(before[2])[1] if before[2] else 0
            for before in pre_rows
            if before[2] != post_by_id[before[0]][2]
        )

        connection.commit()
        connection.executescript(SQL_FILE.read_text(encoding="utf-8"))
        post_schema = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        if post_schema != EXPECTED_SCHEMA_POST:
            raise RuntimeError(f"schema post-version must be {EXPECTED_SCHEMA_POST}, got {post_schema}")

        print(f"[mac580] backup={backup}")
        print(f"[mac580] backup_sha256={backup_sha}")
        print(f"[mac580] rows total:               {len(pre_rows)}")
        print(f"[mac580] rows modified:            {len(changed_ids)}")
        print(f"[mac580] modified ids:             {','.join(map(str, sorted(changed_ids)))}")
        print(f"[mac580] phantoms recovered:       {phantom_total}")
        print(f"[mac580] pre total tokens (naive): {pre_total}")
        print(f"[mac580] post total tokens (smart): {post_total}")
        print(f"[mac580] token delta:               {pre_total - post_total}")
        print("[mac580] reconstruction mismatches: 0")
        print("[mac580] non-idempotent rows:        0")
        print("[mac580] canonical_name drift:       0")
        print(f"[mac580] identifiers before:         {identifiers_before}")
        print(f"[mac580] identifiers after:          {identifiers_after}")
        print("[mac580] standalone corp suffixes:   0")
        print(f"[mac580] schema_version:             {EXPECTED_SCHEMA_BASELINE} -> {post_schema}")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
