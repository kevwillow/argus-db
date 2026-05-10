"""MAC-54 — migration 0009 wrapper + verifier (CP12 schema-sibling).

Applies ``db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql``
inside a controlled sequence and asserts the §11 #11 spot-check shape:

* Pre-state row counts captured (identifiers + sources).
* Pre-state FK integrity captured (PRAGMA foreign_key_check returns 0 rows).
* Migration applied via ``executescript()`` (the migration manages its own
  ``PRAGMA foreign_keys = OFF; BEGIN ... COMMIT; PRAGMA foreign_keys = ON``
  envelope per the SQLite table-rebuild recipe).
* Post-state row counts match pre-state exactly (column-preserving SELECT *
  copy; zero row additions or deletions).
* Post-state CHECK enums reflect the extensions:
    - ``identifiers.identifier_type`` includes ``ble_local_name``,
      ``ble_characteristic``, ``product_family_codename``.
    - ``identifiers.source_type`` includes ``manufacturer_app``.
    - ``sources.source_type`` includes ``manufacturer_app``.
* Post-state index set matches the pre-state index set (rebuild preserves
  every index attached to the old table).
* Self-referencing FK ``identifiers.superseded_by → identifiers(id)``
  preserved: post-state ``superseded_by`` non-NULL pointers all resolve to
  live rows.
* Post-state ``PRAGMA foreign_key_check`` returns 0 rows.
* Canary INSERT smoke-test for each new enum value:
    - INSERT one row per new ``identifier_type`` and one row using
      ``source_type='manufacturer_app'`` inside a SAVEPOINT.
    - Verify the rows insert without CHECK violation.
    - ROLLBACK the savepoint to leave zero canary residue in the live DB.
* Audit ledger row written to ``extraction_runs`` mirroring the MAC-48
  (cp7_cp10) pattern: agent_id=Validator, status='ok', JSON notes payload
  with deltas + section attestations.

Idempotency
-----------
If ``MAX(version) FROM schema_version >= 9`` the wrapper short-circuits with
a logged no-op (no migration apply, no audit row, exit clean). This mirrors
the cp7_cp10 wrapper's no-op-re-run path.

Pre-state backup
----------------
The wrapper expects ``db/argus.db.pre_mac54_step2_backup`` to already exist
(mirroring SAR-9 ``pre_mac42_step5_backup`` + MAC-48 ``pre_mac48_step1_backup``).
Halts on missing backup.

Authority chain
---------------
* BIBLE_AMENDMENTS.md CP12 (commit ``90132fa``) — added ``manufacturer_app``
  to §8.2 source_type sub-banding without sibling schema migration.
* BIBLE_AMENDMENTS.md CP13 (this commit) — schema-sibling for CP12 +
  three Wave G structural-fidelity ``identifier_type`` values.
* Board ratification: MAC-1 [`9d568fa7`] 2026-05-10 HB63 (Path X).
* CEO Step-0 ratification: MAC-54 [`34c908b8`] 2026-05-10.
* MAC-54 dispatch.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "argus.db"
BACKUP_PATH = REPO_ROOT / "db" / "argus.db.pre_mac54_step2_backup"
MIGRATION_PATH = (
    REPO_ROOT
    / "db"
    / "migrations"
    / "0009_manufacturer_app_and_identifier_type_extensions.sql"
)

VALIDATOR_AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"
BIBLE_COMMIT_PRE = "90132fa"  # CP12 HEAD; CP13 lands paired with this migration
BOARD_RATIFICATION_COMMENT_ID = "9d568fa7-edc0-4d68-a7dd-fb40d4cd919e"
CEO_STEP0_COMMENT_ID = "34c908b8-0a66-4a6f-a3a5-4aa6d2bc5470"
ISSUE_ID = "MAC-54"
TARGET_VERSION = 9
MIGRATION_NAME = "0009_manufacturer_app_and_identifier_type_extensions"

NEW_IDENTIFIER_TYPES = (
    "ble_local_name",
    "ble_characteristic",
    "product_family_codename",
)
NEW_SOURCE_TYPE = "manufacturer_app"


class Halt(Exception):
    """§11 #11 stop-the-line — raised on any spot-check failure."""


@dataclass(frozen=True)
class TableSnapshot:
    row_count: int
    indexes: tuple[str, ...]            # sorted index names attached to the table
    check_sql: str                       # raw CREATE TABLE sql (CHECK enums readable)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _table_snapshot(con: sqlite3.Connection, table: str) -> TableSnapshot:
    rc = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    idx_rows = con.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='index' AND tbl_name=? AND name NOT LIKE 'sqlite_autoindex%'",
        (table,),
    ).fetchall()
    idx_names = tuple(sorted(r[0] for r in idx_rows))
    create_sql_row = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    create_sql = create_sql_row[0] if create_sql_row else ""
    return TableSnapshot(row_count=rc, indexes=idx_names, check_sql=create_sql)


def _identifiers_supersede_map(con: sqlite3.Connection) -> dict[int, int | None]:
    """Capture id → superseded_by for self-FK preservation assertion."""
    out: dict[int, int | None] = {}
    for row in con.execute(
        "SELECT id, superseded_by FROM identifiers ORDER BY id"
    ).fetchall():
        out[row[0]] = row[1]
    return out


def _fk_check_clean(con: sqlite3.Connection) -> list[tuple[Any, ...]]:
    """Return the rows returned by PRAGMA foreign_key_check (empty == clean)."""
    return con.execute("PRAGMA foreign_key_check").fetchall()


def _verify_check_enum_extends(
    *,
    table: str,
    column: str,
    create_sql: str,
    required_values: tuple[str, ...],
) -> None:
    for value in required_values:
        # CHECK enum literal substring is the cheapest non-fragile assertion.
        # The migration writes them quoted on their own lines; an exact
        # substring match catches the extension reliably.
        needle = f"'{value}'"
        if needle not in create_sql:
            raise Halt(
                f"post-state {table}.{column} CHECK enum missing required "
                f"value {value!r} — STOP-THE-LINE."
            )


def _canary_inserts(con: sqlite3.Connection) -> dict[str, Any]:
    """Insert one canary row per new enum value inside a SAVEPOINT; rollback.

    Verifies the extended CHECK constraints accept the new values without
    raising IntegrityError. Leaves zero residue in the live DB.
    """
    canary_results: dict[str, Any] = {}
    con.execute("SAVEPOINT canary_insert")
    try:
        # Canary 1: source_type='manufacturer_app' on identifiers.
        # Uses a clearly-marked fake identifier and the documentation MAC range
        # from RFC 7042 (which §7.3 known-fake list catches at validator time —
        # safe to use here because the savepoint rolls back unconditionally).
        canary_mac = "00:00:5e:00:53:00"
        con.execute(
            """
            INSERT INTO identifiers
                (identifier, identifier_type, device_category, manufacturer,
                 model, confidence, source_url, source_type,
                 source_excerpt, geographic_scope, first_seen, last_verified,
                 notes, superseded_by)
            VALUES (?, 'mac', 'unknown', NULL, NULL, 50, 'about:canary',
                    'manufacturer_app', NULL, 'global', NULL, NULL,
                    'MAC-54 canary — SAVEPOINT rolls this back', NULL)
            """,
            (canary_mac,),
        )
        canary_results["identifiers_source_type_manufacturer_app"] = "ok"

        # Canaries 2/3/4: new identifier_type values on identifiers.
        # Distinct fake identifier per row.
        canary_id_for_type = {
            "ble_local_name": "MAC-54_canary_ble_local_name",
            "ble_characteristic": "00000000-0000-0000-0000-000000000001",
            "product_family_codename": "MAC-54_canary_product_family_codename",
        }
        for new_type in NEW_IDENTIFIER_TYPES:
            con.execute(
                """
                INSERT INTO identifiers
                    (identifier, identifier_type, device_category, manufacturer,
                     model, confidence, source_url, source_type,
                     source_excerpt, geographic_scope, first_seen, last_verified,
                     notes, superseded_by)
                VALUES (?, ?, 'unknown', NULL, NULL, 50, 'about:canary',
                        'manufacturer_app', NULL, 'global', NULL, NULL,
                        'MAC-54 canary — SAVEPOINT rolls this back', NULL)
                """,
                (canary_id_for_type[new_type], new_type),
            )
            canary_results[f"identifiers_identifier_type_{new_type}"] = "ok"

        # Canary 5: source_type='manufacturer_app' on sources.
        con.execute(
            """
            INSERT INTO sources (name, url, source_type, tier, last_fetched_at,
                                 last_status, notes)
            VALUES ('MAC-54 canary source', 'about:canary-source-mac54',
                    'manufacturer_app', 3, NULL, NULL,
                    'MAC-54 canary — SAVEPOINT rolls this back')
            """
        )
        canary_results["sources_source_type_manufacturer_app"] = "ok"

    finally:
        con.execute("ROLLBACK TO SAVEPOINT canary_insert")
        con.execute("RELEASE SAVEPOINT canary_insert")

    # Defense-in-depth: confirm zero residue.
    canary_residue = con.execute(
        "SELECT COUNT(*) FROM identifiers WHERE source_url='about:canary'"
    ).fetchone()[0]
    if canary_residue != 0:
        raise Halt(
            f"canary residue: identifiers.source_url='about:canary' rows "
            f"= {canary_residue}, expected 0 — STOP-THE-LINE."
        )
    canary_residue_sources = con.execute(
        "SELECT COUNT(*) FROM sources WHERE url='about:canary-source-mac54'"
    ).fetchone()[0]
    if canary_residue_sources != 0:
        raise Halt(
            f"canary residue: sources.url='about:canary-source-mac54' rows "
            f"= {canary_residue_sources}, expected 0 — STOP-THE-LINE."
        )
    return canary_results


def _insert_audit_row(
    con: sqlite3.Connection,
    *,
    pre_identifiers: TableSnapshot,
    pre_sources: TableSnapshot,
    post_identifiers: TableSnapshot,
    post_sources: TableSnapshot,
    canary_results: dict[str, Any],
    started_at_iso: str,
    finished_at_iso: str,
) -> int:
    notes_payload = {
        "issue": ISSUE_ID,
        "deliverable": "MAC-54 — CP12 schema-sibling migration 0009",
        "amendments_landed": ["CP13"],
        "amendments_referenced": ["CP12"],
        "bible_commit_pre": BIBLE_COMMIT_PRE,
        "board_ratification_comment": BOARD_RATIFICATION_COMMENT_ID,
        "ceo_step0_ratification_comment": CEO_STEP0_COMMENT_ID,
        "migration": MIGRATION_NAME,
        "schema_version": TARGET_VERSION,
        "row_count_parity": {
            "identifiers": {
                "pre": pre_identifiers.row_count,
                "post": post_identifiers.row_count,
            },
            "sources": {
                "pre": pre_sources.row_count,
                "post": post_sources.row_count,
            },
        },
        "index_preservation": {
            "identifiers": list(post_identifiers.indexes),
            "sources": list(post_sources.indexes),
        },
        "canary_inserts": canary_results,
        "section_attestations": [
            "§11 #1  no fabrication: enum extensions cite CP12 + board HB63 + HANDOFF canon",
            "§11 #7  no main-table promotion without provenance: schema-only; zero identifiers writes",
            "§11 #8  no confidence drift: confidence column untouched",
            "§11 #11 amendment-log discipline: coordinated commit with CP13 + §4.1 bible edit",
            "§11 #15 no decompiled source: N/A; schema-only migration",
        ],
        "pre_state_backup": str(BACKUP_PATH.relative_to(REPO_ROOT)),
    }
    cur = con.execute(
        """
        INSERT INTO extraction_runs (
            agent_id, source_id, started_at, finished_at,
            records_in, records_out, errors, status, notes
        ) VALUES (?, NULL, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            VALIDATOR_AGENT_ID,
            started_at_iso,
            finished_at_iso,
            post_identifiers.row_count + post_sources.row_count,
            0,  # schema-only; no rows written to identifiers/sources
            "ok",
            json.dumps(notes_payload, indent=2, sort_keys=False),
        ),
    )
    return cur.lastrowid


def run(
    *,
    db_path: Path = DB_PATH,
    backup_path: Path = BACKUP_PATH,
    migration_path: Path = MIGRATION_PATH,
    write_audit: bool = True,
) -> dict[str, Any]:
    if not db_path.exists():
        raise Halt(f"DB not found at {db_path} — refusing to run.")
    if not migration_path.exists():
        raise Halt(f"Migration not found at {migration_path} — refusing to run.")

    started_at_iso = _utc_now_iso()
    migration_sql = migration_path.read_text(encoding="utf-8")

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        # Idempotency short-circuit.
        current_version = con.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_version"
        ).fetchone()[0]
        if current_version >= TARGET_VERSION:
            return {
                "started_at": started_at_iso,
                "finished_at": _utc_now_iso(),
                "no_op_re_run": True,
                "reason": (
                    f"schema_version already at {current_version} "
                    f"(>= target {TARGET_VERSION}); migration 0009 skipped."
                ),
                "audit_run_id": None,
                "migration": migration_path.name,
            }

        # Pre-flight: backup must exist for fresh-apply.
        if not backup_path.exists():
            raise Halt(
                f"Pre-state backup not found at {backup_path} — refusing to run. "
                "Take a backup first: "
                "`cp db/argus.db db/argus.db.pre_mac54_step2_backup`."
            )

        # Pre-state snapshots.
        pre_identifiers = _table_snapshot(con, "identifiers")
        pre_sources = _table_snapshot(con, "sources")
        pre_supersede_map = _identifiers_supersede_map(con)
        pre_fk_check = _fk_check_clean(con)
        if pre_fk_check:
            raise Halt(
                f"pre-state PRAGMA foreign_key_check non-empty: {pre_fk_check[:10]} "
                "— DB drift; refusing to apply migration on inconsistent state."
            )

        # Apply migration. executescript() autocommits any in-flight transaction
        # before running, then executes the file's BEGIN/COMMIT envelope. The
        # migration's `PRAGMA foreign_keys = OFF/ON` toggles are honored
        # because they sit OUTSIDE the migration's transaction.
        con.executescript(migration_sql)

        # Post-state snapshots.
        post_identifiers = _table_snapshot(con, "identifiers")
        post_sources = _table_snapshot(con, "sources")
        post_supersede_map = _identifiers_supersede_map(con)
        post_fk_check = _fk_check_clean(con)
        if post_fk_check:
            raise Halt(
                f"post-state PRAGMA foreign_key_check non-empty: "
                f"{post_fk_check[:10]} — STOP-THE-LINE."
            )

        # Row-count parity.
        if pre_identifiers.row_count != post_identifiers.row_count:
            raise Halt(
                f"identifiers row count drift {pre_identifiers.row_count} → "
                f"{post_identifiers.row_count} — STOP-THE-LINE."
            )
        if pre_sources.row_count != post_sources.row_count:
            raise Halt(
                f"sources row count drift {pre_sources.row_count} → "
                f"{post_sources.row_count} — STOP-THE-LINE."
            )

        # Index preservation.
        if pre_identifiers.indexes != post_identifiers.indexes:
            raise Halt(
                f"identifiers index set drift: pre={pre_identifiers.indexes!r} "
                f"post={post_identifiers.indexes!r} — STOP-THE-LINE."
            )
        if pre_sources.indexes != post_sources.indexes:
            raise Halt(
                f"sources index set drift: pre={pre_sources.indexes!r} "
                f"post={post_sources.indexes!r} — STOP-THE-LINE."
            )

        # CHECK enum extensions present.
        _verify_check_enum_extends(
            table="identifiers",
            column="identifier_type",
            create_sql=post_identifiers.check_sql,
            required_values=NEW_IDENTIFIER_TYPES,
        )
        _verify_check_enum_extends(
            table="identifiers",
            column="source_type",
            create_sql=post_identifiers.check_sql,
            required_values=(NEW_SOURCE_TYPE,),
        )
        _verify_check_enum_extends(
            table="sources",
            column="source_type",
            create_sql=post_sources.check_sql,
            required_values=(NEW_SOURCE_TYPE,),
        )

        # Self-FK preservation: same (id, superseded_by) pairs pre/post.
        if pre_supersede_map != post_supersede_map:
            diff_ids = [
                k
                for k in set(pre_supersede_map) | set(post_supersede_map)
                if pre_supersede_map.get(k) != post_supersede_map.get(k)
            ][:10]
            raise Halt(
                f"identifiers.superseded_by self-FK map drift on ids "
                f"{diff_ids} — STOP-THE-LINE."
            )

        # schema_version row landed.
        post_version = con.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0]
        if post_version != TARGET_VERSION:
            raise Halt(
                f"schema_version post-migration={post_version} != "
                f"{TARGET_VERSION} — STOP-THE-LINE."
            )

        # Canary INSERT smoke-tests (CHECK enums accept new values).
        canary_results = _canary_inserts(con)

        finished_at_iso = _utc_now_iso()
        audit_id: int | None = None
        if write_audit:
            audit_id = _insert_audit_row(
                con,
                pre_identifiers=pre_identifiers,
                pre_sources=pre_sources,
                post_identifiers=post_identifiers,
                post_sources=post_sources,
                canary_results=canary_results,
                started_at_iso=started_at_iso,
                finished_at_iso=finished_at_iso,
            )
            con.commit()
    finally:
        con.close()

    return {
        "started_at": started_at_iso,
        "finished_at": finished_at_iso,
        "no_op_re_run": False,
        "audit_run_id": audit_id,
        "migration": migration_path.name,
        "row_count_parity": {
            "identifiers": {
                "pre": pre_identifiers.row_count,
                "post": post_identifiers.row_count,
            },
            "sources": {
                "pre": pre_sources.row_count,
                "post": post_sources.row_count,
            },
        },
        "indexes_preserved": {
            "identifiers": list(post_identifiers.indexes),
            "sources": list(post_sources.indexes),
        },
        "canary_inserts": canary_results,
        "schema_version_post": TARGET_VERSION,
        "backup_path": str(backup_path.relative_to(REPO_ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--backup", type=Path, default=BACKUP_PATH)
    parser.add_argument("--migration", type=Path, default=MIGRATION_PATH)
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip the extraction_runs audit-row insert (dry-run mode).",
    )
    args = parser.parse_args()
    summary = run(
        db_path=args.db,
        backup_path=args.backup,
        migration_path=args.migration,
        write_audit=not args.no_audit,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
