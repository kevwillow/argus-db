"""Argus operational CLI (Phase 1 surface).

Subcommands per PROJECT_BIBLE.md §6 Phase 1 step 2:

  status              Print row counts per table, schema version, and current
                      project phase pulled from PROJECT_STATE.md.
  query <identifier>  Look up a normalized identifier in the `identifiers`
                      table. Tries exact match first, then OUI-prefix match.
  export              Stub — full implementation lands in Phase 5 (§7.5).
  validate            Stub — full implementation lands in Phase 5 (§7.4).

Data source resolution (`--source`, default `auto`):

  auto      Probe the DEFAULT db/argus.db; when it is absent, fall back to
            the tracked exports/ directory and say so on stderr. A fresh
            public clone has no db/argus.db (it is gitignored), so `auto` is
            what makes `status` and `query` work out of the box.

            The fallback covers the DEFAULT PROBE ONLY. Naming a path with
            `--db-path` is an explicit demand for THAT database: a missing
            one hard-fails with the same "database not found" message the
            CLI gave before the fallback existed. Serving export data to
            someone who asked for a specific DB is the worst degradation
            available — the answer looks authoritative and came from
            somewhere else entirely.
  db        Require the canonical DB. Hard-fails if absent — existing
            DB-backed workflows keep their strict behaviour and never
            silently degrade.
  exports   Read exports/ even when the canonical DB is present.

Option abbreviation is DISABLED (`allow_abbrev=False`). The accepted option
surface is exactly what `--help` lists, so adding an option can never change
the meaning of an existing invocation. See build_parser() for the cost.

The exports fallback is strictly narrower than the DB: exports/ carries the
emitted identifier rows only, so per-table counts, the superseded tail, the
migration name and the extraction-run log are reported as
"unavailable (requires canonical DB)" rather than guessed at.

Usage:
    python3 argus_cli.py status
    python3 argus_cli.py query aa:bb:cc:dd:ee:ff
    python3 argus_cli.py --source exports status
    python3 argus_cli.py --source db status
    python3 argus_cli.py export
    python3 argus_cli.py validate
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_STATE_PATH = REPO_ROOT / "PROJECT_STATE.md"
DEFAULT_EXPORTS_DIR = REPO_ROOT / "exports"

SOURCE_CHOICES = ("auto", "db", "exports")

# The identifier feed the exports fallback reads. Line 1 is a `# meta:`
# comment, NOT the CSV header — see _csv_rows().
EXPORT_CSV_NAME = "argus_export.csv"
CSV_META_PREFIX = "# meta: "

# JSON feeds surfaced by `status` in exports mode. Every one is a top-level
# object of shape {"_meta": {...}, "entries": [...]} — never a bare list.
EXPORT_JSON_NAMES = (
    "argus_export.json",
    "argus_export_high_confidence.json",
    "argus_export_behavioral_signatures.json",
)

# Printed instead of a count the exports feed genuinely cannot see. A false
# zero reads as "measured and empty", which is worse than an honest gap.
UNAVAILABLE = "unavailable (requires canonical DB)"

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


# ─── exports fallback ──────────────────────────────────────────────────────
#
# A fresh public clone has exports/ (tracked) but no db/argus.db (gitignored)
# and no raw/ (gitignored). Everything below reads only tracked files.


def _resolve_source(args: argparse.Namespace) -> str:
    """Decide whether this invocation reads the DB or the shipped exports.

    Returns "db" or "exports". Never raises: the strict path is enforced
    later by _open(), which owns the canonical "database not found" message
    so its behaviour is byte-identical to the pre-fallback CLI.

    The decision has TWO inputs, not one. Whether db/argus.db exists is not
    enough — what matters first is whether the user NAMED a database:

      * `--db-path X` given   -> "user asked for X". Read X, or die saying
                                 X is missing. Never substitute exports/.
      * `--db-path` omitted   -> "default probe". Falling back is the whole
                                 point: it is what makes a fresh clone work.

    Reads `source` / `db_path_explicit` / `exports_dir` via getattr so that
    callers constructing a bare Namespace(db_path=..., state_path=...) — as
    tests/test_argus_cli_status.py does — keep working untouched. Such a
    Namespace has no `db_path_explicit`, and defaults to the probe.
    """
    requested = getattr(args, "source", "auto")
    db_path = Path(getattr(args, "db_path", DEFAULT_DB_PATH))
    db_path_named = bool(getattr(args, "db_path_explicit", False))

    if requested == "db":
        return "db"
    if requested == "exports":
        print(
            "argus_cli: --source exports: reading shipped exports/ "
            "(canonical DB not consulted).",
            file=sys.stderr,
        )
        return "exports"

    # auto
    if db_path_named:
        # An explicit --db-path is an explicit demand. Return "db" WITHOUT
        # testing existence: _open() then raises the canonical
        # "argus_cli: database not found at <path>" and the process exits 1,
        # exactly as at 9b32212. Testing existence here is the regression
        # this branch repairs — it turned a demand into a suggestion.
        return "db"
    if db_path.exists():
        return "db"
    print(
        "argus_cli: canonical DB not found, reading shipped exports/ instead "
        "(see docs/engineering/SETUP.md).",
        file=sys.stderr,
    )
    print(
        f"argus_cli: (looked for {db_path}; pass --source db to require it, "
        "--source exports to silence this.)",
        file=sys.stderr,
    )
    return "exports"


def _exports_dir(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "exports_dir", DEFAULT_EXPORTS_DIR))


def _require_export_csv(exports_dir: Path) -> Path:
    csv_path = exports_dir / EXPORT_CSV_NAME
    if not csv_path.exists():
        raise SystemExit(
            f"argus_cli: no canonical DB and no export feed at {csv_path}. "
            "Expected the tracked exports/ directory — see "
            "docs/engineering/SETUP.md."
        )
    return csv_path


def _parse_meta_line(line: str) -> dict[str, str]:
    """Parse the CSV's leading `# meta: k=v, k=v` comment into a dict.

    Returns {} for any line that is not a meta comment, which is the signal
    to treat line 1 as the header instead.
    """
    if not line.startswith(CSV_META_PREFIX):
        return {}
    out: dict[str, str] = {}
    for token in line[len(CSV_META_PREFIX):].strip().split(", "):
        if "=" in token:
            key, value = token.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def _csv_meta(csv_path: Path) -> dict[str, str]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        return _parse_meta_line(fh.readline())


def _csv_rows(csv_path: Path):
    """Yield the CSV's data rows as dicts, skipping the `# meta:` line.

    The skip is mandatory: without it csv.DictReader takes the meta comment
    as the header and produces 4 bogus columns, overflowing every 16-field
    data row into restkey. Fields (source_excerpt, notes) contain embedded
    newlines, so this must go through the csv module — never read line-wise.
    """
    with csv_path.open(newline="", encoding="utf-8") as fh:
        first = fh.readline()
        if not _parse_meta_line(first):
            fh.seek(0)  # no meta comment: line 1 really is the header
        yield from csv.DictReader(fh)


def _csv_record(row: dict) -> dict:
    """Normalize a CSV row for printing: empty string -> None.

    The CSV writes SQL NULL as an empty field (174 rows have a blank
    confidence, 35,510 a blank geographic_scope). Mapping "" back to None
    makes the exports path print `manufacturer=None` exactly as the DB path
    does, instead of a bare trailing `manufacturer=`.
    """
    return {k: (v if v not in ("", None) else None) for k, v in row.items()}


def _row_sort_key(record: dict):
    """Mirror the DB path's `ORDER BY id` over a text CSV column."""
    raw = record.get("id")
    try:
        return (0, int(raw))
    except (TypeError, ValueError):
        return (1, str(raw))


def _json_export_summary(path: Path) -> dict | None:
    """Return {'count', 'meta_count', 'exported_at'} for an export feed.

    None when the file is absent or unreadable — reported as unavailable
    rather than as a zero.
    """
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict):
        return None
    meta = doc.get("_meta")
    meta = meta if isinstance(meta, dict) else {}
    entries = doc.get("entries")
    return {
        "count": len(entries) if isinstance(entries, list) else None,
        "meta_count": meta.get("record_count"),
        "exported_at": meta.get("exported_at"),
    }


def _status_from_exports(args: argparse.Namespace) -> int:
    exports_dir = _exports_dir(args)
    state_path: Path = args.state_path
    csv_path = _require_export_csv(exports_dir)

    meta = _csv_meta(csv_path)
    csv_rows = sum(1 for _ in _csv_rows(csv_path))

    print("Argus source: shipped exports (no canonical DB consulted)")
    print(f"Exports dir: {exports_dir}")

    schema_version = meta.get("schema_version")
    if schema_version:
        print(
            f"Schema version: {schema_version} (from {EXPORT_CSV_NAME} meta "
            "line; migration name and applied_at require the canonical DB)"
        )
    else:
        print(f"Schema version: {UNAVAILABLE}")

    exported_at = meta.get("exported_at")
    print(
        f"Exported at: {exported_at} ({EXPORT_CSV_NAME})"
        if exported_at
        else f"Exported at: {UNAVAILABLE}"
    )

    # Only the emitted rows are visible here. The superseded/withdrawn tail
    # is not in the export at all, so the total is genuinely unknown.
    print(f"Identifiers: {csv_rows} rows in {EXPORT_CSV_NAME} / "
          f"total (incl. superseded) {UNAVAILABLE}")
    # Deliberately NOT derived from the CSV: `manufacturer` is free text per
    # identifier row (18,748 distinct strings) and is not the manufacturers
    # registry (261 rows); `source_url` (1,511 distinct) is not the sources
    # registry (98 rows). Printing either would be wrong by ~70x.
    print(f"Manufacturers: {UNAVAILABLE}")
    print(f"Sources: {UNAVAILABLE}")
    print(f"Current phase: {_read_phase_from_state(state_path)}")
    print()

    print("Export record counts:")
    meta_count = meta.get("record_count")
    suffix = ""
    if meta_count is not None and str(meta_count) != str(csv_rows):
        suffix = f"  [WARNING: meta line claims record_count={meta_count}]"
    print(f"  {EXPORT_CSV_NAME}: {csv_rows}{suffix}")
    for name in EXPORT_JSON_NAMES:
        summary = _json_export_summary(exports_dir / name)
        if summary is None or summary["count"] is None:
            print(f"  {name}: unavailable (file missing or unreadable)")
            continue
        stamp = summary["exported_at"]
        note = f" (exported_at {stamp})" if stamp else ""
        mismatch = ""
        if (summary["meta_count"] is not None
                and str(summary["meta_count"]) != str(summary["count"])):
            note_count = summary["meta_count"]
            mismatch = f"  [WARNING: meta line claims record_count={note_count}]"
        print(f"  {name}: {summary['count']}{note}{mismatch}")
    print()

    print("Row counts:")
    for name in EXPECTED_TABLES:
        print(f"  {name}: {UNAVAILABLE}")

    print()
    print(f"Last extraction run: {UNAVAILABLE}")
    return 0


def _query_from_exports(args: argparse.Namespace) -> int:
    exports_dir = _exports_dir(args)
    csv_path = _require_export_csv(exports_dir)
    needle = _normalize_identifier(args.identifier)

    # Same OUI gate as the DB path: exactly 6 colon-separated lowercase hex
    # octets, prefix = first 3.
    oui_prefix = None
    if re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", needle):
        oui_prefix = ":".join(needle.split(":")[:3])

    rows: list[dict] = []
    oui_rows: list[dict] = []
    for raw in _csv_rows(csv_path):
        identifier = (raw.get("identifier") or "").strip().lower()
        if identifier == needle:
            rows.append(_csv_record(raw))
        if (oui_prefix is not None
                and identifier == oui_prefix
                and (raw.get("identifier_type") or "") == "oui"):
            oui_rows.append(_csv_record(raw))

    rows.sort(key=_row_sort_key)
    oui_rows.sort(key=_row_sort_key)

    if not rows and not oui_rows:
        # Qualify the absence. The export feed carries the ACTIVE rows only;
        # superseded and withdrawn identifiers are not in it at all, so a
        # bare "No records for identifier: X" overstates what was searched.
        # It reads as "X is not in Argus" when the honest claim is "X is not
        # in the shipped export". No count is printed: the size of that gap
        # is a property of whichever export is on disk, and hard-coding a
        # number here would be a fabrication one regeneration from stale.
        print(f"No records for identifier: {args.identifier} "
              f"(searched {csv_path})")
        print("  Note: the shipped export carries active rows only — "
              "superseded and withdrawn identifiers are absent from it by "
              "construction. This is absence from the export, not from the "
              "canonical registry; search that with --source db (requires "
              "db/argus.db, which is not distributed).")
        return 1

    if rows:
        print(f"{len(rows)} exact match(es) for {args.identifier}:")
        for r in rows:
            _print_identifier_row(r)
    if oui_rows:
        print(f"\n{len(oui_rows)} OUI parent match(es) ({oui_prefix}):")
        for r in oui_rows:
            _print_identifier_row(r)
    return 0


# ─── subcommands ───────────────────────────────────────────────────────────


def cmd_status(args: argparse.Namespace) -> int:
    if _resolve_source(args) == "exports":
        return _status_from_exports(args)
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
    if _resolve_source(args) == "exports":
        return _query_from_exports(args)
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


class _RecordExplicit(argparse.Action):
    """Store the value AND record that the user actually typed the option.

    argparse cannot otherwise tell `--db-path <default>` from an omitted
    `--db-path`: both leave the same value in the Namespace. The exports
    fallback has to tell them apart — the default is a probe that may
    degrade, a typed path is a demand that may not — so the fact of the
    option appearing is recorded as `<dest>_explicit`.

    Comparing `args.db_path != DEFAULT_DB_PATH` would NOT do: a user who
    types the default path verbatim is still making a demand, and the
    comparison would silently downgrade it to a probe.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        setattr(namespace, self.dest + "_explicit", True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="argus_cli",
        description="Argus operational CLI (Phase 1 surface).",
        # Prefix abbreviation OFF. Adding `--source` made `--s` — an
        # unambiguous abbreviation of `--state-path` before it — an
        # "ambiguous option" error. That is the generic hazard of
        # abbreviation, not a one-off: with it on, every option NAME is part
        # of the contract, and any option added later can change what an
        # existing command line means.
        #
        # The cost, stated plainly: this is a WIDER break than the one it
        # repairs. `--db`, `--state`, `--exports`, `--sou` all stop working
        # too, and `--s` is NOT restored to its 9b32212 meaning — it becomes
        # a hard error instead of an ambiguous one. Worse, the diagnostic
        # depends on the form used (measured on CPython 3.12.3):
        #     `--s`  /  `--s=X`   -> "error: unrecognized arguments: --s"
        #     `--s X`             -> "error: argument command: invalid
        #                             choice: 'X'", because the orphaned
        #                             value is then eaten as the subcommand
        #                             and the message never names --s.
        # Measured blast radius inside this repo: zero call sites — no doc,
        # script, test or CI job invokes argus_cli with an abbreviated
        # option (git grep over *.py *.md *.sh finds only the three
        # canonical spellings, in this file). External callers relying on an
        # undocumented abbreviation must spell the option out.
        allow_abbrev=False,
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        action=_RecordExplicit,
        default=DEFAULT_DB_PATH,
        help=f"Path to the Argus SQLite DB (default: {DEFAULT_DB_PATH}). "
             "Naming a path here is a demand for that database: it is never "
             "degraded to the exports/ fallback, and a missing file is fatal.",
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help=f"Path to PROJECT_STATE.md (default: {DEFAULT_STATE_PATH})",
    )
    parser.add_argument(
        "--exports-dir",
        type=Path,
        default=DEFAULT_EXPORTS_DIR,
        help=f"Path to the shipped exports/ directory "
             f"(default: {DEFAULT_EXPORTS_DIR})",
    )
    parser.add_argument(
        "--source",
        choices=SOURCE_CHOICES,
        default="auto",
        help="Where status/query read from. 'auto' (default) uses the "
             "canonical DB when present and otherwise falls back to "
             "exports/; 'db' requires the canonical DB and hard-fails "
             "without it; 'exports' always reads exports/.",
    )
    # False unless _RecordExplicit fires. Read via getattr elsewhere so a
    # hand-built Namespace without the attribute behaves as a probe.
    parser.set_defaults(db_path_explicit=False)

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
