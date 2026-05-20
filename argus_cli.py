"""Argus operational CLI (Phase 1 surface).

Subcommands per PROJECT_BIBLE.md §6 Phase 1 step 2:

  status              Print row counts per table, schema version, and current
                      project phase pulled from PROJECT_STATE.md.
  query <identifier>  Look up a normalized identifier in the `identifiers`
                      table. Tries exact match first, then OUI-prefix match.
  export              Stub — full implementation lands in Phase 5 (§7.5).
  validate            Stub — full implementation lands in Phase 5 (§7.4).

Usage:
    python3 argus_cli.py status
    python3 argus_cli.py query aa:bb:cc:dd:ee:ff
    python3 argus_cli.py export
    python3 argus_cli.py validate
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_STATE_PATH = REPO_ROOT / "PROJECT_STATE.md"

# Tables we expect to exist after the 0001 migration. Order chosen so
# `status` output reads naturally (canonical first, then registries, then logs).
EXPECTED_TABLES = (
    "identifiers",
    "procurement_records",
    "manufacturers",
    "sources",
    "raw_observations",
    "deployment_observations",
    "extraction_runs",
    "conflicts",
    "schema_version",
)


# ─── helpers ───────────────────────────────────────────────────────────────


def _open(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(
            f"argus_cli: database not found at {db_path}. "
            "Run `python3 -m db.init_db` first."
        )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _read_phase_from_state(state_path: Path) -> str:
    if not state_path.exists():
        return "(PROJECT_STATE.md not found)"
    for line in state_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\*\*Current phase:\*\*\s*(.+?)\s*$", line)
        if m:
            # Return only the phase marker (first sentence) — the trailing
            # prose in PROJECT_STATE.md historically embedded schema_version
            # and identifier counts that drifted out of sync with the live DB.
            # The empirical anchors are now derived in cmd_status via SQL.
            full = m.group(1)
            first_sentence_end = full.find(". ")
            return full[:first_sentence_end + 1] if first_sentence_end > 0 else full
    return "(phase not found in PROJECT_STATE.md)"


def _normalize_identifier(value: str) -> str:
    return value.strip().lower()


# ─── subcommands ───────────────────────────────────────────────────────────


def cmd_status(args: argparse.Namespace) -> int:
    db_path: Path = args.db_path
    state_path: Path = args.state_path
    conn = _open(db_path)
    try:
        existing = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        version_row = conn.execute(
            "SELECT version, name, applied_at "
            "FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()

        # Active vs. total identifier counts — SQL-derived per §6.4 (active =
        # superseded_by IS NULL). These anchors are computed live to prevent
        # the prose-drift class (v1.0.0 → v1.4.x).
        identifiers_active = 0
        identifiers_total = 0
        if "identifiers" in existing:
            identifiers_active = conn.execute(
                "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
            ).fetchone()[0]
            identifiers_total = conn.execute(
                "SELECT COUNT(*) FROM identifiers"
            ).fetchone()[0]

        # Manufacturers hub+arm split (CP31 / migration 0025). The
        # `query_default` column gates default-visibility filtering: hubs
        # carry 'visible' (default queries surface them); arms carry
        # 'hidden_arm' (default queries filter them out via
        # `WHERE query_default = 'visible'`). Reported only when the
        # post-CP31 columns are present so the CLI degrades gracefully
        # against a pre-CP31 backup DB.
        manufacturers_hubs: int | None = None
        manufacturers_arms: int | None = None
        if "manufacturers" in existing:
            mfr_cols = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(manufacturers)")
            }
            if {"is_arm", "query_default"}.issubset(mfr_cols):
                manufacturers_hubs = conn.execute(
                    "SELECT COUNT(*) FROM manufacturers "
                    "WHERE query_default = 'visible'"
                ).fetchone()[0]
                manufacturers_arms = conn.execute(
                    "SELECT COUNT(*) FROM manufacturers "
                    "WHERE query_default = 'hidden_arm'"
                ).fetchone()[0]

        last_run = conn.execute(
            "SELECT id, agent_id, source_id, started_at, finished_at, status "
            "FROM extraction_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()

        print(f"Argus DB: {db_path}")
        if version_row is not None:
            print(
                f"Schema version: {version_row['version']} "
                f"({version_row['name']}, applied {version_row['applied_at']})"
            )
        else:
            print("Schema version: (none — migrations not applied)")
        print(
            f"Identifiers: {identifiers_active} active / "
            f"{identifiers_total} total (active = superseded_by IS NULL)"
        )
        if manufacturers_hubs is not None and manufacturers_arms is not None:
            print(
                f"Manufacturers: {manufacturers_hubs} visible (hub) + "
                f"{manufacturers_arms} hidden (arm) = "
                f"{manufacturers_hubs + manufacturers_arms} total"
            )
        print(f"Current phase: {_read_phase_from_state(state_path)}")
        print()

        print("Row counts:")
        for name in EXPECTED_TABLES:
            if name not in existing:
                print(f"  {name}: (table missing)")
                continue
            count = conn.execute(f"SELECT COUNT(*) AS n FROM {name}").fetchone()["n"]
            print(f"  {name}: {count}")

        print()
        if last_run is not None:
            print(
                "Last extraction run: "
                f"id={last_run['id']} agent={last_run['agent_id']} "
                f"started={last_run['started_at']} "
                f"finished={last_run['finished_at']} "
                f"status={last_run['status']}"
            )
        else:
            print("Last extraction run: (none yet)")
    finally:
        conn.close()
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    db_path: Path = args.db_path
    needle = _normalize_identifier(args.identifier)
    conn = _open(db_path)
    try:
        # Exact-match lookup (case-insensitive via LOWER).
        rows = conn.execute(
            """
            SELECT id, identifier, identifier_type, device_category,
                   manufacturer, model, confidence, source_url, source_type,
                   source_excerpt, geographic_scope, first_seen, last_verified,
                   notes, superseded_by
              FROM identifiers
             WHERE LOWER(identifier) = ?
             ORDER BY id
            """,
            (needle,),
        ).fetchall()

        # If the user supplied a MAC and there's an OUI parent, surface it too.
        oui_rows: list[sqlite3.Row] = []
        if re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", needle):
            oui_prefix = ":".join(needle.split(":")[:3])
            oui_rows = conn.execute(
                """
                SELECT id, identifier, identifier_type, device_category,
                       manufacturer, model, confidence, source_url, source_type
                  FROM identifiers
                 WHERE identifier_type = 'oui'
                   AND LOWER(identifier) = ?
                 ORDER BY id
                """,
                (oui_prefix,),
            ).fetchall()

        if not rows and not oui_rows:
            print(f"No records for identifier: {args.identifier}")
            return 1

        if rows:
            print(f"{len(rows)} exact match(es) for {args.identifier}:")
            for r in rows:
                _print_identifier_row(r)
        if oui_rows:
            print(
                f"\n{len(oui_rows)} OUI parent match(es) "
                f"({':'.join(needle.split(':')[:3])}):"
            )
            for r in oui_rows:
                _print_identifier_row(r)
    finally:
        conn.close()
    return 0


def _print_identifier_row(r: sqlite3.Row) -> None:
    print(f"  id={r['id']} type={r['identifier_type']} "
          f"category={r['device_category']} "
          f"manufacturer={r['manufacturer']} "
          f"confidence={r['confidence']}")
    print(f"    source_url={r['source_url']} "
          f"source_type={r['source_type']}")
    if "superseded_by" in r.keys() and r["superseded_by"] is not None:
        print(f"    superseded_by={r['superseded_by']}")


def cmd_export(args: argparse.Namespace) -> int:
    print("export: not implemented in Phase 1 — see PROJECT_BIBLE.md §6 "
          "Phase 5 / §7.5 for the export worker spec.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    print("validate: not implemented in Phase 1 — see PROJECT_BIBLE.md §6 "
          "Phase 5 / §7.4 for the validator spec.")
    return 0


# ─── argparse wiring ───────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="argus_cli",
        description="Argus operational CLI (Phase 1 surface).",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to the Argus SQLite DB (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help=f"Path to PROJECT_STATE.md (default: {DEFAULT_STATE_PATH})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("status", help="row counts, schema version, current phase")
    s.set_defaults(func=cmd_status)

    q = sub.add_parser("query", help="look up an identifier")
    q.add_argument("identifier", help="normalized identifier to search for")
    q.set_defaults(func=cmd_query)

    e = sub.add_parser("export", help="(Phase 5 stub)")
    e.set_defaults(func=cmd_export)

    v = sub.add_parser("validate", help="(Phase 5 stub)")
    v.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
