"""Initialize the Argus SQLite database from migrations.

Usage:
    python -m db.init_db [--db-path db/argus.db] [--migrations db/migrations]

Idempotent: every CREATE in a migration file uses IF NOT EXISTS, and
seed inserts use INSERT OR IGNORE. Re-running on an empty or partially
migrated DB is safe.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"


def apply_migrations(db_path: Path, migrations_dir: Path) -> list[str]:
    """Apply every .sql file in migrations_dir in lexical order.

    Returns the list of applied migration filenames.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in migrations_dir.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"No migrations found in {migrations_dir}")

    applied: list[str] = []
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        for path in files:
            sql = path.read_text(encoding="utf-8")
            conn.executescript(sql)
            applied.append(path.name)
        conn.commit()
    finally:
        conn.close()
    return applied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--migrations", type=Path, default=DEFAULT_MIGRATIONS_DIR)
    args = parser.parse_args()

    applied = apply_migrations(args.db_path, args.migrations)
    print(f"Applied {len(applied)} migration(s) to {args.db_path}:")
    for name in applied:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
