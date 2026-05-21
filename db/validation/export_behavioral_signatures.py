"""CP18 sibling export writer for ``behavioral_signatures``.

Generates ``exports/argus_export_behavioral_signatures.json`` per
PROJECT_BIBLE.md §7.5 CP18 (commit ``7993536``) — the Rayhunter-consumable
sibling to the Lynceus-bound ``argus_export*.json`` files.

The sibling file preserves the load-bearing
``{pattern, pattern_type, description, argus_record_id}`` Lynceus contract
purity by routing wire-pattern-less ``behavioral_signatures`` rows (e.g.
"Identity Request" + threshold_json) to a dedicated file with its own
``_meta.dropped_in_export`` reconciliation arithmetic.

Authority chain
---------------
- Bible §7.5 (CP18 amendment, lines 533-585) — file shape, field notes,
  reconciliation arithmetic.
- Bible §9 item 9 (CP18 extension) — coverage_report.md "Behavioral-
  signatures export reconciliation" section.
- Bible §11 #6 — read-only DB access during export pass
  (``PRAGMA query_only = ON``).
- Bible §11 #13 — ``device_category='unknown'`` carveout (inherited via
  the table's enum reuse from migration 0010).
- BIBLE_AMENDMENTS.md CP18 — sibling-file directive.
- ``feedback_high_confidence_export_floor.md`` — canonical ≥70 confidence
  floor (same floor governs this sibling export).
- MAC-93 dispatch (this work).

Read-only contract
------------------
``PRAGMA query_only = ON`` is set immediately after open. Re-running the
writer over an unchanged DB produces byte-identical files modulo the
``exported_at`` field. ``argus_run_id`` is a deterministic UUID5 derived
from the canonical-row fingerprint (own namespace, distinct from the
Lynceus exporter's so the two run-ids never collide).

argus_record_id recipe (§7.5 CP18 verbatim)
-------------------------------------------
``sha256(f"behavioral_signature|{signature_name}|{source_id}|{cellgen_or_NULL}").hexdigest()[:16]``

Uses the literal string ``"NULL"`` (not Python ``None`` / JSON ``null``)
when ``cellular_generation`` is NULL. The 3-tuple UNIQUE constraint on
``(signature_name, source_id, cellular_generation)`` from migration 0010
makes this hash stable under re-extraction + dedup events.

Stop-the-line clauses
---------------------
- ``argus_record_id`` collision in survivor set → ``Halt`` (would indicate
  a UNIQUE-constraint logic mismatch).
- Reconciliation arithmetic mismatch
  (``source_record_count − sum(dropped) != record_count``) → ``Halt``.
- ``threshold_json`` fails ``json.loads`` despite the DB-level
  ``json_valid()`` CHECK → ``Halt`` (DB-level corruption).
- ``coverage_report.md`` missing when ``patch_coverage_report`` is called
  → ``Halt`` (caller must run Lynceus exporter first).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "argus.db"
EXPORTS_DIR = REPO_ROOT / "exports"
EXPORT_FILE = EXPORTS_DIR / "argus_export_behavioral_signatures.json"
COVERAGE_REPORT_PATH = EXPORTS_DIR / "coverage_report.md"

# §7.5 CP18 confidence floor — matches the canonical ≥70 high-confidence
# floor (`feedback_high_confidence_export_floor.md`). All current Marlin
# rows land at conf=80 (post-§8.3 corroboration lift); single-source
# academic rows would land at 70-75 and still pass.
CONFIDENCE_THRESHOLD = 70

# Deterministic UUID5 namespace anchor — locks ``argus_run_id`` to the data
# fingerprint. Distinct from the Lynceus exporter's namespace so the same
# DB state never produces colliding run-ids across the two exporters.
ARGUS_RUN_ID_NAMESPACE: uuid.UUID = uuid.uuid5(
    uuid.NAMESPACE_DNS, "argus.export.behavioral_signatures.v1"
)

# Coverage-report section markers (idempotent BEGIN/END replace).
COVERAGE_SECTION_BEGIN = "<!-- BEGIN behavioral_signatures section (CP18) -->"
COVERAGE_SECTION_END = "<!-- END behavioral_signatures section (CP18) -->"


class Halt(Exception):
    """Stop-the-line signal raised on any §11 trip or reconciliation mismatch."""


@dataclass(frozen=True)
class BehavioralSignatureRow:
    """A single ``behavioral_signatures`` row pulled for export classification."""

    id: int
    signature_name: str
    cellular_generation: str | None
    threshold_json: str | None  # raw TEXT; json_valid() CHECK at INSERT
    confidence: int
    source_id: int
    device_category: str


@dataclass(frozen=True)
class BehavioralSignatureEntry:
    """A single entry written to ``argus_export_behavioral_signatures.json``."""

    signature_name: str
    cellular_generation: str | None  # JSON-null when None; scalar string otherwise
    threshold_json: Any  # parsed JSON value (dict / list / scalar / None)
    confidence: int
    argus_record_id: str


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON;")
    return con


def _load_rows(con: sqlite3.Connection) -> list[BehavioralSignatureRow]:
    cur = con.execute(
        """
        SELECT id, signature_name, cellular_generation, threshold_json,
               confidence, source_id, device_category
        FROM behavioral_signatures
        ORDER BY id ASC
        """
    )
    out: list[BehavioralSignatureRow] = []
    for r in cur.fetchall():
        out.append(
            BehavioralSignatureRow(
                id=int(r["id"]),
                signature_name=r["signature_name"],
                cellular_generation=r["cellular_generation"],
                threshold_json=r["threshold_json"],
                confidence=int(r["confidence"]),
                source_id=int(r["source_id"]),
                device_category=r["device_category"],
            )
        )
    return out


def _load_schema_version(con: sqlite3.Connection) -> int:
    cur = con.execute("SELECT MAX(version) AS v FROM schema_version")
    row = cur.fetchone()
    if row is None or row["v"] is None:
        raise Halt("schema_version table empty — refusing to write export.")
    return int(row["v"])


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def argus_record_id(
    signature_name: str,
    source_id: int,
    cellular_generation: str | None,
) -> str:
    """§7.5 CP18 argus_record_id recipe — 16-char lowercase-hex sha256 prefix.

    Uses the literal string ``"NULL"`` (not Python ``None`` / JSON ``null``)
    when ``cellular_generation`` is NULL, per the CP18 field-note. Stability
    is anchored by migration 0010's UNIQUE 3-tuple
    ``(signature_name, source_id, cellular_generation)``.
    """

    cellgen_literal = cellular_generation if cellular_generation is not None else "NULL"
    raw = f"behavioral_signature|{signature_name}|{source_id}|{cellgen_literal}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _classify_row(row: BehavioralSignatureRow) -> str | None:
    """Return drop-bin label or ``None`` (survivor).

    Priority order: ``unknown_category`` > ``below_confidence_threshold``.
    The §11 #13 unknown-category ban sits above the confidence floor, matching
    the Lynceus exporter's analogous priority. CP18 §7.5 declares only these
    two bins are in scope for the sibling export; the §4.4 wire-pattern-
    specific bins (``ssid_pattern`` etc.) do not apply because behavioral
    signatures are not wire-pattern-keyed.
    """

    if row.device_category == "unknown":
        return "unknown_category"
    if row.confidence < CONFIDENCE_THRESHOLD:
        return "below_confidence_threshold"
    return None


def _parse_threshold_json(raw: str | None) -> Any:
    """Parse ``threshold_json`` raw TEXT into JSON value.

    Per §7.5 CP18 field-note: "exports verbatim from the DB (no transformation;
    both ``json_valid()``-gated CHECK constraints prove the field is well-
    formed JSON at INSERT)". Halt if parsing fails — that's DB-level
    corruption since the CHECK should have rejected it.
    """

    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Halt(
            f"threshold_json failed JSON parse despite json_valid() CHECK; "
            f"DB-level corruption: {exc}"
        )


def _derive_argus_run_id(rows: list[BehavioralSignatureRow]) -> str:
    """Deterministic UUID5 from the canonical-row fingerprint.

    Same DB state ⇒ same UUID. The fingerprint binds id + signature_name +
    cellular_generation + source_id + confidence + device_category — the
    six fields whose mutation changes the export output.
    """

    fingerprint_parts = [
        f"{r.id}|{r.signature_name}|{r.cellular_generation or ''}|"
        f"{r.source_id}|{r.confidence}|{r.device_category}"
        for r in rows
    ]
    fingerprint = "\n".join(fingerprint_parts).encode("utf-8")
    digest = hashlib.sha256(fingerprint).hexdigest()
    return str(uuid.uuid5(ARGUS_RUN_ID_NAMESPACE, digest))


def _build_payload(
    rows: list[BehavioralSignatureRow],
    *,
    schema_version: int,
    exported_at: str,
    argus_run_id_val: str,
) -> dict[str, Any]:
    """Build the §7.5 CP18 sibling-export payload.

    Static gates only — no runtime parameters (Lynceus's CP7
    ``geographic_scope_filter`` doesn't apply; behavioral signatures are
    schema-derived and cross-jurisdictional by construction).
    """

    bins: dict[str, int] = {
        "below_confidence_threshold": 0,
        "unknown_category": 0,
    }
    entries: list[BehavioralSignatureEntry] = []
    for row in rows:
        drop_bin = _classify_row(row)
        if drop_bin is not None:
            bins[drop_bin] += 1
            continue
        entries.append(
            BehavioralSignatureEntry(
                signature_name=row.signature_name,
                cellular_generation=row.cellular_generation,
                threshold_json=_parse_threshold_json(row.threshold_json),
                confidence=row.confidence,
                argus_record_id=argus_record_id(
                    row.signature_name, row.source_id, row.cellular_generation
                ),
            )
        )

    # Defense-in-depth: the migration 0010 UNIQUE 3-tuple guarantees the
    # hash inputs are unique, so a collision here means either a sha256
    # collision (negligible) or a UNIQUE-constraint logic mismatch.
    ids_seen: set[str] = set()
    for e in entries:
        if e.argus_record_id in ids_seen:
            raise Halt(
                f"argus_record_id collision detected: {e.argus_record_id} for "
                f"signature_name={e.signature_name!r} — violates CP18 UNIQUE "
                f"3-tuple stability."
            )
        ids_seen.add(e.argus_record_id)

    record_count = len(entries)
    source_record_count = len(rows)
    if source_record_count - sum(bins.values()) != record_count:
        raise Halt(
            "behavioral_signatures export reconciliation mismatch: "
            f"source={source_record_count} dropped={sum(bins.values())} "
            f"record_count={record_count}"
        )

    meta = {
        "argus_version": str(schema_version),
        "exported_at": exported_at,
        "record_count": record_count,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "argus_run_id": argus_run_id_val,
        "source_record_count": source_record_count,
        "dropped_in_export": bins,
    }

    payload = {
        "_meta": meta,
        "entries": [
            {
                "signature_name": e.signature_name,
                "cellular_generation": e.cellular_generation,
                "threshold_json": e.threshold_json,
                "confidence": e.confidence,
                "argus_record_id": e.argus_record_id,
            }
            for e in sorted(entries, key=lambda e: e.argus_record_id)
        ],
    }
    return payload


# §11 #3 export-time email-shape guard (MAC-217). Defense-in-depth: future
# ingest leaks must not silently re-introduce PII into v1.4.1+ exports.
_PII_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _assert_no_email_pii(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    matches = _PII_EMAIL_RE.findall(text)
    if matches:
        sample = matches[:3]
        raise Halt(
            f"§11 #3 export-guard FAILED for {path.name}: {len(matches)} email-shape token(s) "
            f"found. Sample (up to 3): {sample}. Refusing to emit PII-bearing export."
        )


def _write_json(path: Path, payload: dict[str, Any]) -> int:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")
    _assert_no_email_pii(path)
    return len(text.encode("utf-8"))


def build_coverage_section(payload: dict[str, Any]) -> str:
    """Build the §9 item 9 (CP18) "Behavioral-signatures export reconciliation".

    Reconciliation arithmetic mirrors the Lynceus-bound section's shape:
    ``source_record_count − sum(dropped) = record_count``.
    """

    meta = payload["_meta"]
    source = meta["source_record_count"]
    dropped = meta["dropped_in_export"]
    record_count = meta["record_count"]
    dropped_sum = sum(dropped.values())
    lines = [
        COVERAGE_SECTION_BEGIN,
        "",
        "## Behavioral-signatures export reconciliation (§9 item 9, CP18)",
        "",
        "Sibling export `argus_export_behavioral_signatures.json` per §7.5 CP18.",
        f"`argus_run_id`: `{meta['argus_run_id']}` (deterministic UUID5; stable across re-runs).",
        "",
        f"- Source record count: **{source}** (rows in `behavioral_signatures` table)",
        f"- Confidence threshold: **≥ {meta['confidence_threshold']}**",
        f"- Exported entries: **{record_count}** (in `argus_export_behavioral_signatures.json`)",
        "",
        "### Dropped from sibling export",
        "",
        "| Bin | Count |",
        "|---|---|",
        f"| `below_confidence_threshold` | {dropped['below_confidence_threshold']} |",
        f"| `unknown_category` | {dropped['unknown_category']} |",
        f"| **TOTAL DROPPED** | **{dropped_sum}** |",
        "",
        f"Reconciliation: {source} source − {dropped_sum} dropped = {record_count} entries ✓",
        "",
        COVERAGE_SECTION_END,
    ]
    return "\n".join(lines) + "\n"


def patch_coverage_report(coverage_report_path: Path, section: str) -> None:
    """Inject (or replace) the BEGIN/END-marked CP18 section in coverage_report.md.

    Idempotent: re-running over the same input file produces byte-identical
    output modulo the section content. If the section already exists between
    markers, it is replaced in-place; otherwise it is appended at end.
    """

    if not coverage_report_path.exists():
        raise Halt(
            f"coverage_report.md missing at {coverage_report_path}; run "
            f"export_lynceus.py first to produce the base report."
        )

    text = coverage_report_path.read_text(encoding="utf-8")
    if COVERAGE_SECTION_BEGIN in text and COVERAGE_SECTION_END in text:
        begin_idx = text.index(COVERAGE_SECTION_BEGIN)
        end_idx = text.index(COVERAGE_SECTION_END) + len(COVERAGE_SECTION_END)
        prefix = text[:begin_idx].rstrip()
        suffix = text[end_idx:].lstrip()
        new_text = prefix + "\n\n" + section
        if suffix:
            new_text = new_text + "\n" + suffix
    else:
        new_text = text.rstrip() + "\n\n" + section
    coverage_report_path.write_text(new_text, encoding="utf-8")
    _assert_no_email_pii(coverage_report_path)


def run(
    db_path: Path = DB_PATH,
    *,
    output_path: Path = EXPORT_FILE,
    coverage_report_path: Path | None = None,
    exported_at: str | None = None,
) -> dict[str, Any]:
    """End-to-end run: load rows, build payload, write JSON, optionally patch report.

    Returns the payload dict for caller inspection / test assertions.
    """

    con = _open_readonly(db_path)
    try:
        rows = _load_rows(con)
        schema_version = _load_schema_version(con)
    finally:
        con.close()

    argus_run_id_val = _derive_argus_run_id(rows)
    payload = _build_payload(
        rows,
        schema_version=schema_version,
        exported_at=exported_at or _utc_now_iso(),
        argus_run_id_val=argus_run_id_val,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(output_path, payload)

    if coverage_report_path is not None:
        patch_coverage_report(coverage_report_path, build_coverage_section(payload))

    return payload


def _main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "CP18 sibling export writer for behavioral_signatures. "
            "Writes exports/argus_export_behavioral_signatures.json per §7.5 CP18."
        )
    )
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--out", type=Path, default=EXPORT_FILE)
    parser.add_argument(
        "--coverage-report",
        type=Path,
        default=COVERAGE_REPORT_PATH,
        help=(
            "Path to coverage_report.md to patch with the CP18 section. "
            "Pass --no-coverage-report to skip patching."
        ),
    )
    parser.add_argument(
        "--no-coverage-report",
        dest="patch_coverage_report",
        action="store_false",
        default=True,
        help="Skip coverage_report.md patching.",
    )
    args = parser.parse_args()
    coverage_path = args.coverage_report if args.patch_coverage_report else None
    payload = run(
        db_path=args.db,
        output_path=args.out,
        coverage_report_path=coverage_path,
    )
    meta = payload["_meta"]
    print(
        f"Wrote {args.out}: record_count={meta['record_count']} "
        f"source_record_count={meta['source_record_count']} "
        f"argus_run_id={meta['argus_run_id']}"
    )
    if coverage_path is not None:
        print(f"Patched {coverage_path} CP18 section.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
