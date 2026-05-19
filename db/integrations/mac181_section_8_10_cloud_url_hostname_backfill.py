#!/usr/bin/env python3
"""MAC-181 §8.10 — backfill `notes.cloud_url_hostname` on the inaugural
`vendor_document_uuid_cloud_reference` row (id=23059) per the CP28 §4.1
canonical metadata-key convention.

Authority anchor: [MAC-182](MAC-182) operator final directive
2026-05-19T02:27:53Z; D1.a BACKFILL disposition aligning landed Wave H
state with CP28 §-text declared policy + pre-staging the Wave I
hostname-corpus join key.

Idempotent on re-run: uses ``json_set`` to set the field if absent or
overwrite with the canonical value if present.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"

# Single canonical backfill — one row, one field, one value.
ROW_ID = 23059
CANONICAL_HOSTNAME = "duss.djicorp.com"


def main() -> int:
    if not DB.exists():
        print(f"ERROR: DB not found at {DB}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        # Verify pre-state.
        pre = conn.execute(
            "SELECT id, identifier, identifier_type, notes FROM identifiers WHERE id = ?",
            (ROW_ID,),
        ).fetchone()
        if pre is None:
            print(f"ERROR: row id={ROW_ID} not found", file=sys.stderr)
            return 2
        if pre["identifier_type"] != "vendor_document_uuid_cloud_reference":
            print(
                f"ERROR: row id={ROW_ID} identifier_type is {pre['identifier_type']!r}, "
                f"expected 'vendor_document_uuid_cloud_reference'. Refusing to mutate.",
                file=sys.stderr,
            )
            return 3
        pre_notes = json.loads(pre["notes"])
        pre_value = pre_notes.get("cloud_url_hostname")

        # Apply backfill via json_set (idempotent: sets the key, overwriting if present).
        conn.execute(
            "UPDATE identifiers SET notes = json_set(notes, '$.cloud_url_hostname', ?) WHERE id = ?",
            (CANONICAL_HOSTNAME, ROW_ID),
        )
        conn.commit()

        # Verify post-state.
        post = conn.execute(
            "SELECT id, identifier, identifier_type, notes FROM identifiers WHERE id = ?",
            (ROW_ID,),
        ).fetchone()
        post_notes = json.loads(post["notes"])
        post_value = post_notes.get("cloud_url_hostname")

        print(f"row id={ROW_ID} ({post['identifier_type']})")
        print(f"  identifier: {post['identifier']}")
        print(f"  notes.cloud_url_hostname pre  = {pre_value!r}")
        print(f"  notes.cloud_url_hostname post = {post_value!r}")
        if post_value != CANONICAL_HOSTNAME:
            print("ERROR: post-backfill value mismatch", file=sys.stderr)
            return 4
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
