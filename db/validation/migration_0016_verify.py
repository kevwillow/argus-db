"""HB77 — migration 0016 wrapper + verifier (§4 chunk 1 LICENSE column).

Applies ``db/migrations/0016_license_column.sql`` inside a controlled sequence
and asserts the §11 #11 spot-check shape against ``deployment_observations``:

* Pre-state row counts captured (deployment_observations + wigle_anchor_priority).
* Pre-state FK integrity captured (PRAGMA foreign_key_check returns 0 rows).
* Pre-state row mix captured for backfill verification:
    - source_id=5 (Atlas) count
    - source_id=6 (DeFlock) count
    - source_id NOT IN (5,6) count (expected 0 at apply time)
* Migration applied via ``executescript()`` (the migration manages its own
  ``PRAGMA foreign_keys = OFF; BEGIN ... COMMIT; PRAGMA foreign_keys = ON``
  envelope per the SQLite table-rebuild recipe).
* Post-state row count parity: deployment_observations pre == post.
* Post-state CHECK enum reflects the new column: license CHECK contains all
  five enum literals (ODbL-1.0, CC-BY-NC-SA-4.0, public-domain, foia,
  unspecified).
* Post-state index set matches the pre-state index set (rebuild preserves
  all 6 named indexes).
* Inbound FK preservation: every wigle_anchor_priority.deployment_id resolves
  to a live deployment_observations.id post-rename.
* Backfill correctness:
    - 100% of source_id=5 rows carry license='CC-BY-NC-SA-4.0'
    - 100% of source_id=6 rows carry license='ODbL-1.0'
    - 0 rows carry license='unspecified' (escape-hatch unused at apply time)
* Post-state ``PRAGMA foreign_key_check`` returns 0 rows.
* Canary INSERT smoke-test for each of the 5 enum values inside a SAVEPOINT
  (verifies CHECK accepts each value); plus one negative-test INSERT with
  an invalid license value asserting CHECK rejects it. All canaries rolled
  back via SAVEPOINT.
* Audit ledger row written to ``extraction_runs`` mirroring the MAC-54
  (0009 verify) pattern: agent_id=CEO, status='ok', JSON notes payload
  with deltas + section attestations.

Idempotency
-----------
If ``MAX(version) FROM schema_version >= 16`` the wrapper short-circuits with
a logged no-op (no migration apply, no audit row, exit clean).

Pre-state backup
----------------
The wrapper expects ``db/argus.db.pre_mac0016_step_backup`` to already exist.
Halts on missing backup.

Authority chain
---------------
* HB75 board ratification [`3f478a6d`] — §4 chunk 1 Q3 LICENSE column at slot
  0016.
* HB76 board ratification [`81f0cce7`] — CREDITS.md + LICENSE / LICENSE-DATA /
  LICENSE-DOCS verbatim.
* HB76 board ratification [`<HB77-ack-id>`] — migration 0016 scope ratified
  as drafted with two non-blocking observations (SPDX enum readability /
  downstream consumer pre-flight).
* Bible §11 #11 — schema changes are CEO-only ratification post-board-scope.
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
BACKUP_PATH = REPO_ROOT / "db" / "argus.db.pre_mac0016_step_backup"
MIGRATION_PATH = REPO_ROOT / "db" / "migrations" / "0016_license_column.sql"

CEO_AGENT_ID = "62a86779-651b-4c59-8773-cee9e0f53334"
HB75_RATIFICATION_COMMENT_ID = "3f478a6d-ad80-4a23-9019-fb5b851a9c49"
HB76_RATIFICATION_COMMENT_ID = "81f0cce7-1ddc-4275-a8ec-8d7253876c9a"
ISSUE_ID = "MAC-1"
TARGET_VERSION = 16
MIGRATION_NAME = "0016_license_column"

ENUM_VALUES = (
    "ODbL-1.0",
    "CC-BY-NC-SA-4.0",
    "public-domain",
    "foia",
    "unspecified",
)

ATLAS_SOURCE_ID = 5
ATLAS_LICENSE = "CC-BY-NC-SA-4.0"
DEFLOCK_SOURCE_ID = 6
DEFLOCK_LICENSE = "ODbL-1.0"


class Halt(Exception):
    """§11 #11 stop-the-line — raised on any spot-check failure."""


@dataclass(frozen=True)
class TableSnapshot:
    row_count: int
    indexes: tuple[str, ...]
    check_sql: str


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


def _source_id_mix(con: sqlite3.Connection) -> dict[str, int]:
    out: dict[str, int] = {}
    for label, src_id in (("atlas", ATLAS_SOURCE_ID), ("deflock", DEFLOCK_SOURCE_ID)):
        out[label] = con.execute(
            "SELECT COUNT(*) FROM deployment_observations WHERE source_id=?",
            (src_id,),
        ).fetchone()[0]
    out["other"] = con.execute(
        "SELECT COUNT(*) FROM deployment_observations "
        f"WHERE source_id NOT IN ({ATLAS_SOURCE_ID}, {DEFLOCK_SOURCE_ID}) "
        "OR source_id IS NULL"
    ).fetchone()[0]
    return out


def _fk_check_clean(con: sqlite3.Connection) -> list[tuple[Any, ...]]:
    return con.execute("PRAGMA foreign_key_check").fetchall()


def _inbound_fk_integrity(con: sqlite3.Connection) -> dict[str, int]:
    """Verify wigle_anchor_priority.deployment_id refs resolve."""
    total = con.execute("SELECT COUNT(*) FROM wigle_anchor_priority").fetchone()[0]
    orphan = con.execute(
        "SELECT COUNT(*) FROM wigle_anchor_priority wap "
        "LEFT JOIN deployment_observations d ON d.id = wap.deployment_id "
        "WHERE wap.deployment_id IS NOT NULL AND d.id IS NULL"
    ).fetchone()[0]
    return {"total": total, "orphan_refs": orphan}


def _verify_check_enum_contains(create_sql: str, required: tuple[str, ...]) -> None:
    for value in required:
        needle = f"'{value}'"
        if needle not in create_sql:
            raise Halt(
                f"post-state deployment_observations.license CHECK enum missing "
                f"required value {value!r} — STOP-THE-LINE."
            )


def _verify_backfill(con: sqlite3.Connection) -> dict[str, Any]:
    atlas_total = con.execute(
        "SELECT COUNT(*) FROM deployment_observations WHERE source_id=?",
        (ATLAS_SOURCE_ID,),
    ).fetchone()[0]
    atlas_correct = con.execute(
        "SELECT COUNT(*) FROM deployment_observations "
        "WHERE source_id=? AND license=?",
        (ATLAS_SOURCE_ID, ATLAS_LICENSE),
    ).fetchone()[0]
    if atlas_total != atlas_correct:
        raise Halt(
            f"Atlas backfill drift: {atlas_correct}/{atlas_total} carry "
            f"license={ATLAS_LICENSE!r}; expected 100% — STOP-THE-LINE."
        )

    deflock_total = con.execute(
        "SELECT COUNT(*) FROM deployment_observations WHERE source_id=?",
        (DEFLOCK_SOURCE_ID,),
    ).fetchone()[0]
    deflock_correct = con.execute(
        "SELECT COUNT(*) FROM deployment_observations "
        "WHERE source_id=? AND license=?",
        (DEFLOCK_SOURCE_ID, DEFLOCK_LICENSE),
    ).fetchone()[0]
    if deflock_total != deflock_correct:
        raise Halt(
            f"DeFlock backfill drift: {deflock_correct}/{deflock_total} carry "
            f"license={DEFLOCK_LICENSE!r}; expected 100% — STOP-THE-LINE."
        )

    unspecified_count = con.execute(
        "SELECT COUNT(*) FROM deployment_observations WHERE license='unspecified'"
    ).fetchone()[0]
    if unspecified_count != 0:
        raise Halt(
            f"Unexpected backfill: {unspecified_count} rows carry "
            f"license='unspecified' (escape hatch); expected 0 — STOP-THE-LINE."
        )

    return {
        "atlas": {"rows": atlas_total, "license": ATLAS_LICENSE},
        "deflock": {"rows": deflock_total, "license": DEFLOCK_LICENSE},
        "unspecified": unspecified_count,
    }


def _canary_inserts(con: sqlite3.Connection) -> dict[str, Any]:
    """Insert one canary row per enum value (5 canaries) + 1 negative canary
    asserting CHECK rejects an invalid value. All inside a SAVEPOINT; rollback.
    """
    canary_results: dict[str, Any] = {}
    con.execute("SAVEPOINT canary_insert")
    try:
        for value in ENUM_VALUES:
            con.execute(
                """
                INSERT INTO deployment_observations
                    (source_id, source_url, source_row_key, license, notes)
                VALUES (NULL, 'about:canary-mac0016',
                        ?,
                        ?,
                        'HB77 canary — SAVEPOINT rolls this back')
                """,
                (f"canary_{value}", value),
            )
            canary_results[f"insert_license_{value}"] = "ok"

        # Negative-test: invalid value must be rejected by CHECK.
        try:
            con.execute(
                """
                INSERT INTO deployment_observations
                    (source_id, source_url, source_row_key, license, notes)
                VALUES (NULL, 'about:canary-mac0016', 'canary_invalid',
                        'BOGUS-NOT-IN-ENUM',
                        'HB77 negative canary — SAVEPOINT rolls this back')
                """
            )
        except sqlite3.IntegrityError:
            canary_results["reject_invalid_license"] = "ok"
        else:
            raise Halt(
                "CHECK constraint failed to reject license='BOGUS-NOT-IN-ENUM' "
                "— STOP-THE-LINE."
            )
    finally:
        con.execute("ROLLBACK TO SAVEPOINT canary_insert")
        con.execute("RELEASE SAVEPOINT canary_insert")

    residue = con.execute(
        "SELECT COUNT(*) FROM deployment_observations "
        "WHERE source_url='about:canary-mac0016'"
    ).fetchone()[0]
    if residue != 0:
        raise Halt(
            f"canary residue: deployment_observations.source_url="
            f"'about:canary-mac0016' rows = {residue}, expected 0 — STOP-THE-LINE."
        )
    return canary_results


def _insert_audit_row(
    con: sqlite3.Connection,
    *,
    pre_obs: TableSnapshot,
    post_obs: TableSnapshot,
    pre_mix: dict[str, int],
    backfill: dict[str, Any],
    inbound_pre: dict[str, int],
    inbound_post: dict[str, int],
    canary_results: dict[str, Any],
    started_at_iso: str,
    finished_at_iso: str,
) -> int:
    notes_payload = {
        "issue": ISSUE_ID,
        "deliverable": "HB77 — §4 chunk 1 LICENSE column on deployment_observations",
        "amendments_landed": [],
        "amendments_referenced": [],
        "board_ratifications": {
            "hb75_scope": HB75_RATIFICATION_COMMENT_ID,
            "hb76_affirmation": HB76_RATIFICATION_COMMENT_ID,
        },
        "migration": MIGRATION_NAME,
        "schema_version": TARGET_VERSION,
        "row_count_parity": {
            "deployment_observations": {
                "pre": pre_obs.row_count,
                "post": post_obs.row_count,
            }
        },
        "pre_state_source_mix": pre_mix,
        "backfill": backfill,
        "index_preservation": list(post_obs.indexes),
        "inbound_fk": {"pre": inbound_pre, "post": inbound_post},
        "canary_inserts": canary_results,
        "section_attestations": [
            "§11 #1  no fabrication: backfill is deterministic CASE on source_id; "
            "Atlas (5)→CC-BY-NC-SA-4.0 per upstream EFF; DeFlock (6)→ODbL-1.0 per OSM-mirror",
            "§11 #7  no main-table promotion without provenance: schema-only; zero identifiers writes",
            "§11 #8  no confidence drift: confidence column untouched",
            "§11 #11 amendment-log discipline: no bible §-amendment sibling required "
            "(LICENSE = attribution-fidelity column, not §-text framework)",
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
            CEO_AGENT_ID,
            started_at_iso,
            finished_at_iso,
            post_obs.row_count,
            0,
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
                    f"(>= target {TARGET_VERSION}); migration 0016 skipped."
                ),
                "audit_run_id": None,
                "migration": migration_path.name,
            }

        if not backup_path.exists():
            raise Halt(
                f"Pre-state backup not found at {backup_path} — refusing to run. "
                "Take a backup first: "
                "`cp db/argus.db db/argus.db.pre_mac0016_step_backup`."
            )

        pre_obs = _table_snapshot(con, "deployment_observations")
        pre_mix = _source_id_mix(con)
        pre_fk_check = _fk_check_clean(con)
        if pre_fk_check:
            raise Halt(
                f"pre-state PRAGMA foreign_key_check non-empty: "
                f"{pre_fk_check[:10]} — DB drift; refusing to apply migration."
            )
        inbound_pre = _inbound_fk_integrity(con)

        # license column must NOT yet exist on deployment_observations pre-apply.
        if "license" in pre_obs.check_sql.lower():
            raise Halt(
                "pre-state deployment_observations create_sql already contains "
                "'license' — migration may have partially applied. STOP-THE-LINE."
            )

        con.executescript(migration_sql)

        post_obs = _table_snapshot(con, "deployment_observations")
        post_fk_check = _fk_check_clean(con)
        if post_fk_check:
            raise Halt(
                f"post-state PRAGMA foreign_key_check non-empty: "
                f"{post_fk_check[:10]} — STOP-THE-LINE."
            )
        inbound_post = _inbound_fk_integrity(con)
        if inbound_post["orphan_refs"] != 0:
            raise Halt(
                f"inbound FK drift: wigle_anchor_priority has "
                f"{inbound_post['orphan_refs']} orphan deployment_id refs — "
                "STOP-THE-LINE."
            )
        if inbound_pre["total"] != inbound_post["total"]:
            raise Halt(
                f"wigle_anchor_priority row count drift "
                f"{inbound_pre['total']} → {inbound_post['total']} — "
                "STOP-THE-LINE."
            )

        if pre_obs.row_count != post_obs.row_count:
            raise Halt(
                f"deployment_observations row count drift {pre_obs.row_count} → "
                f"{post_obs.row_count} — STOP-THE-LINE."
            )

        if pre_obs.indexes != post_obs.indexes:
            raise Halt(
                f"deployment_observations index set drift: "
                f"pre={pre_obs.indexes!r} post={post_obs.indexes!r} — STOP-THE-LINE."
            )

        _verify_check_enum_contains(post_obs.check_sql, ENUM_VALUES)

        post_version = con.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0]
        if post_version != TARGET_VERSION:
            raise Halt(
                f"schema_version post-migration={post_version} != "
                f"{TARGET_VERSION} — STOP-THE-LINE."
            )

        backfill = _verify_backfill(con)
        canary_results = _canary_inserts(con)

        finished_at_iso = _utc_now_iso()
        audit_id: int | None = None
        if write_audit:
            audit_id = _insert_audit_row(
                con,
                pre_obs=pre_obs,
                post_obs=post_obs,
                pre_mix=pre_mix,
                backfill=backfill,
                inbound_pre=inbound_pre,
                inbound_post=inbound_post,
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
            "deployment_observations": {
                "pre": pre_obs.row_count,
                "post": post_obs.row_count,
            }
        },
        "pre_state_source_mix": pre_mix,
        "backfill": backfill,
        "indexes_preserved": list(post_obs.indexes),
        "inbound_fk": {"pre": inbound_pre, "post": inbound_post},
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
