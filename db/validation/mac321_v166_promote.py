"""MAC-321 v1.6.6 WS-1 promotion script.

Applies the operator-ratified
`operator_review/MAC-321/validation/validated_promotion_set.json` (208 rows,
all `promote_new`) to `db/argus.db` in a single transaction:

- 208 INSERT into `identifiers` (oui 133 / mac_range 19 / fcc_grantee_code 44 /
  vendor_controlled_hostname 5 / firmware_sha256_hash 3 / firmware_branded_string 2 /
  product_family_codename 2). Existing slots, 0 new sources, 0 new manufacturers
  (all 33 set manufacturers already registered; R2 new-vendor +1,112 DEFERRED to v1.6.7).
- 1 INSERT into `extraction_runs` tagged `MAC-321 v1.6.6`.

Operator ratification: MAC-321 Phase-D decision card interaction
`24a9de82-07dd-481b-942c-6be0e68341ef` answered `approve_clean`
(2026-06-06T16:35:52Z) by board user. Gated discipline mirrors v1.6.2 (MAC-292).
Bible HEAD `e412fe9`. Backup baseline taken pre-apply (see BACKUP_FILE/SHA env).

Per `feedback_notes_mutation_must_be_json_property_merge`: the per-row `notes`
JSON is parsed and a `mac321_v166_promotion` audit property is MERGED in (never
text-suffix). source_excerpt truncated to the 200-char schema CHECK with the full
pre-clip preserved in notes per §11 #7 (none exceed 200 in this set).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "argus.db"
PROMOTION_JSON = (
    REPO_ROOT / "operator_review" / "MAC-321" / "validation" / "validated_promotion_set.json"
)

AGENT_ID = os.environ.get("PAPERCLIP_AGENT_ID", "62a86779-651b-4c59-8773-cee9e0f53334")
DISPATCH_ISSUE = "MAC-321"
RATIFICATION_INTERACTION = "24a9de82-07dd-481b-942c-6be0e68341ef"
RATIFICATION_OPTION = "approve_clean"
BIBLE_HEAD = "e412fe9"
BACKUP_FILE = os.environ.get("MAC321_BACKUP_FILE", "")
BACKUP_SHA256 = os.environ.get("MAC321_BACKUP_SHA256", "")

EXPECTED_COUNT = 208


def _truncate_excerpt(excerpt: str | None) -> str | None:
    if not excerpt:
        return None
    return excerpt[:200]


def _build_insert_notes(entry: dict) -> str:
    raw = entry.get("notes") or "{}"
    try:
        notes_obj = json.loads(raw)
        if not isinstance(notes_obj, dict):
            notes_obj = {"_legacy_notes_value": notes_obj}
    except json.JSONDecodeError:
        notes_obj = {"_parse_error": True, "_raw": raw}

    audit = {
        "ratified_at_issue": DISPATCH_ISSUE,
        "ratified_at_interaction": RATIFICATION_INTERACTION,
        "ratified_option": RATIFICATION_OPTION,
        "bible_head": BIBLE_HEAD,
        "operator_backup": BACKUP_FILE,
        "operator_backup_sha256": BACKUP_SHA256,
        "disposition": "promote_new",
        "promotion_set": str(PROMOTION_JSON.relative_to(REPO_ROOT)),
    }
    original = entry.get("source_excerpt") or ""
    if len(original) > 200:
        audit["source_excerpt_full_pre_clip"] = original
    # JSON property merge — never overwrite the existing extraction-method keys.
    notes_obj["mac321_v166_promotion"] = audit
    return json.dumps(notes_obj, ensure_ascii=False)


def _load_rows() -> list[dict]:
    with PROMOTION_JSON.open() as f:
        doc = json.load(f)
    return doc["rows"]


def _preflight(conn: sqlite3.Connection, rows: list[dict]) -> None:
    cur = conn.cursor()
    issues: list[str] = []

    if len(rows) != EXPECTED_COUNT:
        issues.append(f"row count {len(rows)} != {EXPECTED_COUNT}")

    # No (identifier, identifier_type) collision with an active canonical row.
    for r in rows:
        cur.execute(
            "SELECT id FROM identifiers WHERE identifier=? AND identifier_type=? AND superseded_by IS NULL",
            (r["identifier"], r["identifier_type"]),
        )
        if cur.fetchone():
            issues.append(
                f"collision: {r['identifier_type']}={r['identifier']!r} already active"
            )

    # source_excerpt CHECK (<=200).
    for r in rows:
        ex = r.get("source_excerpt") or ""
        if len(ex) > 200 and not ex:  # truncation handles this; flag only impossible
            issues.append(f"excerpt too long uncaught: {r['identifier']!r}")

    if not BACKUP_FILE or not BACKUP_SHA256:
        issues.append("MAC321_BACKUP_FILE / MAC321_BACKUP_SHA256 env not set")

    if issues:
        raise SystemExit("PREFLIGHT FAILED — STOP_THE_LINE:\n  - " + "\n  - ".join(issues))


def _insert_row(conn: sqlite3.Connection, entry: dict, ts: str) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO identifiers (
            identifier, identifier_type, device_category, manufacturer, model,
            confidence, source_url, source_type, source_excerpt,
            geographic_scope, first_seen, last_verified, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry["identifier"],
            entry["identifier_type"],
            entry["device_category"],
            entry.get("manufacturer"),
            entry.get("model"),
            entry["confidence"],
            entry["source_url"],
            entry["source_type"],
            _truncate_excerpt(entry.get("source_excerpt")),
            entry.get("geographic_scope"),
            entry.get("first_seen") or ts,
            entry.get("last_verified") or ts,
            _build_insert_notes(entry),
        ),
    )
    return cur.lastrowid


def _insert_extraction_run(conn: sqlite3.Connection, ts: str, summary: dict) -> int:
    cur = conn.cursor()
    notes_payload = {
        "dispatch": DISPATCH_ISSUE,
        "ratification_interaction": RATIFICATION_INTERACTION,
        "ratified_option": RATIFICATION_OPTION,
        "bible_head": BIBLE_HEAD,
        "operator_backup": BACKUP_FILE,
        "operator_backup_sha256": BACKUP_SHA256,
        "promotion_set": str(PROMOTION_JSON.relative_to(REPO_ROOT)),
        "summary": summary,
    }
    cur.execute(
        """
        INSERT INTO extraction_runs (
            agent_id, source_id, started_at, finished_at,
            records_in, records_out, errors, status, notes
        ) VALUES (?, NULL, ?, ?, ?, ?, 0, 'completed', ?)
        """,
        (AGENT_ID, ts, ts, summary["records_in"], summary["records_out"],
         json.dumps(notes_payload, ensure_ascii=False)),
    )
    return cur.lastrowid


def main() -> int:
    rows = _load_rows()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _preflight(conn, rows)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        conn.execute("BEGIN")
        pre_active = conn.execute(
            "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
        ).fetchone()[0]

        new_ids = [_insert_row(conn, r, ts) for r in rows]

        post_active = conn.execute(
            "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
        ).fetchone()[0]

        by_type: dict[str, int] = {}
        for r in rows:
            by_type[r["identifier_type"]] = by_type.get(r["identifier_type"], 0) + 1

        summary = {
            "records_in": len(rows),
            "records_out": len(new_ids),
            "inserted_id_range": [min(new_ids), max(new_ids)],
            "by_identifier_type": by_type,
            "pre_active_count": pre_active,
            "post_active_count": post_active,
            "delta_active": post_active - pre_active,
        }
        run_id = _insert_extraction_run(conn, ts, summary)
        summary["extraction_runs_id"] = run_id
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
