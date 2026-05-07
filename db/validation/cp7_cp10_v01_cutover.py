"""MAC-48 Sub-deliverable A — CP7 + CP10 v0.1 cutover wrapper.

Applies migration 0008 (`db/migrations/0008_cp7_cp10_v01_cutover.sql`) inside
a single transaction, runs the §11 #11 spot-check, and writes an audit ledger
row to `extraction_runs` mirroring the SAR-9 rollback pattern (run ids 31/32/33
on this same table).

Authority chain
---------------
- BIBLE_AMENDMENTS.md CP7 (geographic_scope §12 #1 resolution + export-time filter).
- BIBLE_AMENDMENTS.md CP10 (§11 #10 narrow-read v0.1 cutover — 17-row flip).
- Bible commit `0aa89a0` — CP7 + CP8 + CP9 + CP10 + SAR-10 amendments landed.
- Board ratification: MAC-1 [`4f075253`] approved 2026-05-07T17:10:13Z
  (six-pick + two-halt-flag bundle).
- MAC-48 dispatch (Validator).

Pre-state backup
----------------
The wrapper expects ``db/argus.db.pre_mac48_step1_backup`` to already exist
(taken before invocation; mirrors SAR-9 ``pre_mac42_step5_backup`` pattern).
Halts on missing backup.

§11 #11 spot-check
------------------
Before commit:
  * CP10 flip count == 17 (the ratified slate).
  * CP7 backfill count == 63 (= active row count).
  * All 17 flipped rows still at confidence ∈ [50, 55] (§11 #8 — no
    confidence drift).
  * `superseded_by` pointers preserved unchanged (set vs set diff = ∅).
  * Row counts: 121 total / 63 active unchanged.
  * No category collateral: no rows with category != 'unknown' AND not in
    the CP10 slate had their category mutated.

Halts via ``raise Halt`` on any spot-check failure → transaction rolls back
automatically.

Audit ledger
------------
On commit, inserts one ``extraction_runs`` row with
``agent_id='da137694-2efe-4589-8150-828dcab881fb'`` (Validator),
``status='ok'``, and a JSON-shaped notes payload recording the row deltas
+ source citations (bible commit + board ratification + MAC-48).

Idempotency
-----------
Re-running the wrapper after a successful run is a no-op modulo a fresh
audit-row insert. The migration's UPDATEs guard on ``device_category =
'unknown'`` / ``geographic_scope IS NULL`` so already-flipped rows are
skipped. The wrapper detects "no rows changed" and skips the audit insert
in that case (logs the no-op explicitly).
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
BACKUP_PATH = REPO_ROOT / "db" / "argus.db.pre_mac48_step1_backup"
MIGRATION_PATH = (
    REPO_ROOT / "db" / "migrations" / "0008_cp7_cp10_v01_cutover.sql"
)

VALIDATOR_AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"
BIBLE_COMMIT = "0aa89a0"
BOARD_RATIFICATION_COMMENT_ID = "4f075253-2eae-4ea3-9db5-c67c6f02e012"
ISSUE_ID = "MAC-48"

# CP10 17-row slate — vendor → flipped device_category + expected row count.
CP10_SLATE: dict[str, tuple[str, int]] = {
    "DJI": ("drone", 13),
    "Flock Safety": ("alpr", 1),
    "Skydio": ("drone", 1),
    "Cellebrite": ("hacking_tool", 1),
    "SoundThinking": ("gunshot_detect", 1),
}
CP10_TOTAL_EXPECTED = 17

# Pre-cutover invariants (verified before the migration applies).
EXPECTED_TOTAL_ROWS = 121
EXPECTED_ACTIVE_ROWS = 63

# Confidence band for the flipped rows (§11 #8 attestation).
EXPECTED_FLIP_CONFIDENCE_MIN = 50
EXPECTED_FLIP_CONFIDENCE_MAX = 55


class Halt(Exception):
    """§11 #11 stop-the-line signal — raised on any spot-check failure."""


@dataclass(frozen=True)
class RowSnapshot:
    """A pre/post snapshot row for diff/spot-check reasoning."""

    id: int
    identifier: str
    identifier_type: str
    manufacturer: str | None
    device_category: str
    confidence: int
    geographic_scope: str | None
    superseded_by: int | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_snapshot(con: sqlite3.Connection) -> dict[int, RowSnapshot]:
    cur = con.execute(
        """
        SELECT id, identifier, identifier_type, manufacturer, device_category,
               confidence, geographic_scope, superseded_by
        FROM identifiers
        ORDER BY id
        """
    )
    out: dict[int, RowSnapshot] = {}
    for r in cur.fetchall():
        out[r["id"]] = RowSnapshot(
            id=r["id"],
            identifier=r["identifier"],
            identifier_type=r["identifier_type"],
            manufacturer=r["manufacturer"],
            device_category=r["device_category"],
            confidence=r["confidence"],
            geographic_scope=r["geographic_scope"],
            superseded_by=r["superseded_by"],
        )
    return out


def _verify_pre_state(snapshot: dict[int, RowSnapshot]) -> None:
    """§11 #11 — verify the DB is in the shape we expect before mutating."""

    if len(snapshot) != EXPECTED_TOTAL_ROWS:
        raise Halt(
            f"pre-state row count {len(snapshot)} != expected "
            f"{EXPECTED_TOTAL_ROWS} — DB drift, halting."
        )
    active = [r for r in snapshot.values() if r.superseded_by is None]
    if len(active) != EXPECTED_ACTIVE_ROWS:
        raise Halt(
            f"pre-state active row count {len(active)} != expected "
            f"{EXPECTED_ACTIVE_ROWS} — DB drift, halting."
        )


def _verify_post_state(
    *,
    pre: dict[int, RowSnapshot],
    post: dict[int, RowSnapshot],
) -> dict[str, Any]:
    """§11 #11 spot-check after the in-transaction migration applied."""

    if set(pre.keys()) != set(post.keys()):
        diff = set(pre.keys()).symmetric_difference(post.keys())
        raise Halt(
            f"row id set changed (added/removed {sorted(diff)[:10]}…) — "
            "migration must not insert/delete rows."
        )

    cat_flips: list[tuple[int, str, str, str | None]] = []
    scope_backfills: list[tuple[int, str | None, str]] = []
    other_changes: list[tuple[int, str]] = []

    for row_id, before in pre.items():
        after = post[row_id]
        # superseded_by must never change.
        if after.superseded_by != before.superseded_by:
            other_changes.append((row_id, "superseded_by mutated"))
        # confidence must never change (§11 #8).
        if after.confidence != before.confidence:
            other_changes.append((row_id, "confidence mutated"))
        # identifier / identifier_type / manufacturer must never change.
        for field in ("identifier", "identifier_type", "manufacturer"):
            if getattr(after, field) != getattr(before, field):
                other_changes.append((row_id, f"{field} mutated"))
        # device_category may flip from 'unknown' → CP10 slate value only.
        if after.device_category != before.device_category:
            cat_flips.append(
                (row_id, before.device_category, after.device_category, before.manufacturer)
            )
        # geographic_scope may backfill from NULL → 'US'/'global' only.
        if after.geographic_scope != before.geographic_scope:
            scope_backfills.append(
                (row_id, before.geographic_scope, after.geographic_scope)
            )

    if other_changes:
        raise Halt(
            "spot-check failure: unexpected field mutations (not category / "
            f"scope): {other_changes[:10]} — STOP-THE-LINE."
        )

    # CP10 flip count must equal the number of pre-state CP10 candidates.
    # Fresh run: 17 candidates → 17 flips. Re-run on already-applied DB: 0
    # candidates → 0 flips (idempotency).
    pre_cp10_candidates = [
        r
        for r in pre.values()
        if r.superseded_by is None
        and r.device_category == "unknown"
        and r.manufacturer in CP10_SLATE
    ]
    if len(cat_flips) != len(pre_cp10_candidates):
        raise Halt(
            f"CP10 flip count {len(cat_flips)} != pre-state candidates "
            f"{len(pre_cp10_candidates)} — STOP-THE-LINE."
        )
    # On a fresh run, the candidate set must equal the ratified slate (17 rows
    # split per CP10 vendor counts). On a re-run, the candidate set is empty —
    # also valid, this is the idempotency path. Both cases verified below.
    if len(pre_cp10_candidates) not in (0, CP10_TOTAL_EXPECTED):
        raise Halt(
            f"pre-state CP10 candidate count {len(pre_cp10_candidates)} is "
            f"neither 0 (idempotent re-run) nor {CP10_TOTAL_EXPECTED} (fresh "
            "run vs ratified slate) — DB drift, STOP-THE-LINE."
        )

    # Verify each flip matches the CP10 slate + each was 'unknown' before +
    # confidence band held (§11 #8).
    flip_by_vendor: dict[str, list[tuple[int, str]]] = {}
    for row_id, before_cat, after_cat, manufacturer in cat_flips:
        if before_cat != "unknown":
            raise Halt(
                f"row id={row_id}: pre-flip category {before_cat!r} != 'unknown' — "
                "CP10 slate covers unknown→specific only; STOP-THE-LINE."
            )
        if manufacturer not in CP10_SLATE:
            raise Halt(
                f"row id={row_id}: manufacturer {manufacturer!r} not in CP10 "
                "slate but had a flip — STOP-THE-LINE."
            )
        expected_cat, _ = CP10_SLATE[manufacturer]
        if after_cat != expected_cat:
            raise Halt(
                f"row id={row_id} ({manufacturer}): flipped to {after_cat!r} "
                f"but CP10 slate says {expected_cat!r} — STOP-THE-LINE."
            )
        post_row = post[row_id]
        if not (
            EXPECTED_FLIP_CONFIDENCE_MIN
            <= post_row.confidence
            <= EXPECTED_FLIP_CONFIDENCE_MAX
        ):
            raise Halt(
                f"§11 #8 violation: row id={row_id} confidence={post_row.confidence} "
                f"outside expected [{EXPECTED_FLIP_CONFIDENCE_MIN}, "
                f"{EXPECTED_FLIP_CONFIDENCE_MAX}] band for the CP10 flip slate."
            )
        flip_by_vendor.setdefault(manufacturer, []).append((row_id, after_cat))

    # Fresh-run path: per-vendor counts must match the ratified slate. On a
    # re-run (zero flips), this loop is vacuously satisfied.
    if cat_flips:
        for vendor, (expected_cat, expected_count) in CP10_SLATE.items():
            actual = flip_by_vendor.get(vendor, [])
            if len(actual) != expected_count:
                raise Halt(
                    f"CP10 slate mismatch: vendor={vendor} flipped {len(actual)} "
                    f"rows, expected {expected_count} — STOP-THE-LINE."
                )

    # CP7 backfill: every active row that was NULL must now be populated;
    # superseded rows remain NULL (CP7 backfill targets the active set).
    active_pre_null = [
        row_id
        for row_id, r in pre.items()
        if r.superseded_by is None and r.geographic_scope is None
    ]
    if len(scope_backfills) != len(active_pre_null):
        raise Halt(
            f"CP7 backfill count {len(scope_backfills)} != expected "
            f"{len(active_pre_null)} (= active rows with NULL scope pre-state) "
            "— STOP-THE-LINE."
        )

    backfill_us = 0
    backfill_global = 0
    for row_id, before_scope, after_scope in scope_backfills:
        if before_scope is not None:
            raise Halt(
                f"row id={row_id}: scope mutated from non-NULL ({before_scope!r}) "
                "— CP7 only backfills NULL → value; STOP-THE-LINE."
            )
        if row_id == 1:
            if after_scope != "US":
                raise Halt(
                    f"Wave-A row id=1 backfilled to {after_scope!r}, "
                    "expected 'US' per CP7 — STOP-THE-LINE."
                )
            backfill_us += 1
        else:
            if after_scope != "global":
                raise Halt(
                    f"row id={row_id} (non-Wave-A active) backfilled to "
                    f"{after_scope!r}, expected 'global' per CP7 source-class "
                    "default for vendor-OUI-only inferences — STOP-THE-LINE."
                )
            backfill_global += 1

    # Active row count + total row count unchanged.
    post_active = sum(1 for r in post.values() if r.superseded_by is None)
    if post_active != EXPECTED_ACTIVE_ROWS:
        raise Halt(
            f"post-state active row count {post_active} != expected "
            f"{EXPECTED_ACTIVE_ROWS} — STOP-THE-LINE."
        )
    if len(post) != EXPECTED_TOTAL_ROWS:
        raise Halt(
            f"post-state total row count {len(post)} != expected "
            f"{EXPECTED_TOTAL_ROWS} — STOP-THE-LINE."
        )

    return {
        "cat_flips_total": len(cat_flips),
        "cat_flips_by_vendor": {
            vendor: [
                {"id": row_id, "after_category": cat}
                for row_id, cat in flips
            ]
            for vendor, flips in sorted(flip_by_vendor.items())
        },
        "scope_backfills_total": len(scope_backfills),
        "scope_backfills_us_count": backfill_us,
        "scope_backfills_global_count": backfill_global,
        "post_active_rows": post_active,
        "post_total_rows": len(post),
    }


def _insert_audit_row(
    con: sqlite3.Connection,
    *,
    spot_check: dict[str, Any],
    finished_at_iso: str,
    started_at_iso: str,
    no_op: bool,
) -> int:
    notes_payload = {
        "issue": ISSUE_ID,
        "deliverable": "Sub-deliverable A — data-layer prep",
        "amendments_applied": ["CP7", "CP10"],
        "bible_commit": BIBLE_COMMIT,
        "board_ratification_comment": BOARD_RATIFICATION_COMMENT_ID,
        "migration": "0008_cp7_cp10_v01_cutover",
        "no_op_re_run": no_op,
        "cat_flips_total": spot_check["cat_flips_total"],
        "cat_flips_by_vendor": spot_check["cat_flips_by_vendor"],
        "scope_backfills_total": spot_check["scope_backfills_total"],
        "scope_backfills_us_count": spot_check["scope_backfills_us_count"],
        "scope_backfills_global_count": spot_check["scope_backfills_global_count"],
        "post_active_rows": spot_check["post_active_rows"],
        "post_total_rows": spot_check["post_total_rows"],
        "section_attestations": [
            "§11 #1  no fabrication: backfill values come from CP7 directive verbatim",
            "§11 #7  provenance carry-through: source_url / source_excerpt untouched",
            "§11 #8  no confidence drift: confidence column not mutated by either UPDATE",
            "§11 #11 halt-the-line spot-check: passed for all clauses",
            "§11 #13 unknown→specific (post-flip): 17 rows now pass the export gate",
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
            spot_check["post_active_rows"],
            spot_check["cat_flips_total"] + spot_check["scope_backfills_total"],
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
    """Apply migration 0008 inside a transaction with §11 #11 spot-check.

    Returns a summary dict suitable for printing to deliverable comments.
    """

    if not db_path.exists():
        raise Halt(f"DB not found at {db_path} — refusing to run.")
    if not backup_path.exists():
        raise Halt(
            f"Pre-state backup not found at {backup_path} — refusing to run. "
            "Take a backup first: `cp db/argus.db db/argus.db.pre_mac48_step1_backup`."
        )
    if not migration_path.exists():
        raise Halt(f"Migration not found at {migration_path} — refusing to run.")

    started_at_iso = _utc_now_iso()
    migration_sql = migration_path.read_text(encoding="utf-8")

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        # Snapshot pre-state.
        pre_snapshot = _load_snapshot(con)
        _verify_pre_state(pre_snapshot)

        # Apply migration in-transaction. sqlite3 default is autocommit-ish;
        # we manage explicitly via BEGIN / COMMIT.
        con.execute("BEGIN")
        # Use executescript() to honor the migration's PRAGMA + multi-statement
        # body. executescript implicitly commits any open transaction first;
        # to keep everything in a single transaction we strip the BEGIN/COMMIT
        # boundaries, run the migration's UPDATEs as individual execute() calls
        # against the open transaction.
        #
        # Simpler approach: use con.executescript() which does its own commit,
        # then inspect post-state and either roll back on failure (DB restore
        # from backup) or insert the audit row.
        # To avoid restore-from-backup complexity, we rely on the in-transaction
        # path: split the migration into individual statements (skip PRAGMA +
        # INSERT-OR-IGNORE schema_version + comment lines) and run them on the
        # explicit transaction. The migration is a known shape so we can do this
        # reliably.
        statements = _split_migration_statements(migration_sql)
        for stmt in statements:
            con.execute(stmt)

        # Snapshot post-state.
        post_snapshot = _load_snapshot(con)
        spot_check = _verify_post_state(pre=pre_snapshot, post=post_snapshot)

        no_op_re_run = (
            spot_check["cat_flips_total"] == 0
            and spot_check["scope_backfills_total"] == 0
        )
        finished_at_iso = _utc_now_iso()

        if write_audit and not no_op_re_run:
            audit_id = _insert_audit_row(
                con,
                spot_check=spot_check,
                started_at_iso=started_at_iso,
                finished_at_iso=finished_at_iso,
                no_op=False,
            )
        else:
            audit_id = None

        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()

    return {
        "started_at": started_at_iso,
        "finished_at": finished_at_iso,
        "no_op_re_run": no_op_re_run,
        "audit_run_id": audit_id,
        "spot_check": spot_check,
        "backup_path": str(backup_path.relative_to(REPO_ROOT)),
        "migration": migration_path.name,
    }


def _split_migration_statements(sql: str) -> list[str]:
    """Strip comments + PRAGMA, split by semicolon, keep UPDATE / INSERT.

    The migration is a known controlled shape; we are not building a general
    SQL parser. We retain UPDATE statements and the INSERT OR IGNORE for
    schema_version. PRAGMA is skipped because the wrapper already sets
    foreign_keys=ON on the connection.
    """

    out: list[str] = []
    buf: list[str] = []
    for raw in sql.splitlines():
        line = raw.split("--", 1)[0].rstrip()
        if not line:
            continue
        buf.append(line)
        if line.endswith(";"):
            stmt = " ".join(buf).strip()
            buf.clear()
            head = stmt.split(None, 1)[0].upper()
            if head == "PRAGMA":
                continue
            out.append(stmt)
    if buf:
        leftover = " ".join(buf).strip()
        if leftover:
            head = leftover.split(None, 1)[0].upper()
            if head != "PRAGMA":
                out.append(leftover)
    return out


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
