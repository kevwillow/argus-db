"""Backfill `procurement_records.vendor_canonical_normalized` for CP23 / mig 0021.

Run once immediately after applying migration
0021_procurement_vendor_canonical_normalized. Idempotent: re-running the
script overwrites the column with the same deterministic value.

Usage:
    python -m db.backfill_0021 [--db-path db/argus.db]
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from db.normalize_vendor import normalize_vendor_name


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"


def backfill(db_path: Path) -> dict[str, int]:
    """Backfill vendor_canonical_normalized for all procurement_records rows.

    Returns a dict with counts of {total, updated, empty_input, blank_output}.
    """
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, vendor_canonical_name FROM procurement_records"
        )
        rows = cur.fetchall()

        total = len(rows)
        updated = 0
        empty_input = 0
        blank_output = 0

        for row_id, name in rows:
            if not name:
                empty_input += 1
            normalized = normalize_vendor_name(name)
            if not normalized:
                blank_output += 1
            cur.execute(
                "UPDATE procurement_records "
                "SET vendor_canonical_normalized = ? "
                "WHERE id = ?",
                (normalized, row_id),
            )
            updated += cur.rowcount

        conn.commit()
        return {
            "total": total,
            "updated": updated,
            "empty_input": empty_input,
            "blank_output": blank_output,
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    stats = backfill(args.db_path)
    print(f"Backfill complete on {args.db_path}:")
    for key, val in stats.items():
        print(f"  {key}: {val}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
