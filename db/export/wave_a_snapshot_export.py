"""Wave-A-snapshot early export — Phase 4 pre-deliverable for Lynceus integration testing.

Produces argus_export_wave_a_snapshot_<run-timestamp>.json per bible §7.5
export contract. Distinct from Phase-5 v1 export via phase_marker.

Authority: MAC-22 (Phase-4 pre-deliverable); Wave-A close at MAC-25 + MAC-26 (2026-05-06T~00:44Z); board
ask at MAC-1 [`972afd90`] for Lynceus smoke-test ingest.

Output shape:
    {
      "_meta": {
        "argus_run_id": "<fresh UUID per export run>",
        "bible_head_commit": "<git short-hash>",
        "bible_amendments_through": "<git short-hash of BIBLE_AMENDMENTS.md>",
        "schema_version": <int>,
        "phase_marker": "phase_4_wave_a_snapshot",
        "confidence_threshold": 0,
        "wave_a_yield_summary": {...},
        "dropped_in_export": {...},
        "exported_at": "<ISO8601 UTC>"
      },
      "entries": [
        {"argus_record_id": "<stable sha256 truncated>", ...},
        ...
      ]
    }

Stability: `argus_record_id` is deterministic SHA-256 truncated hex of
`(source_id, candidate_identifier, candidate_type)`. Re-running the
exporter against the same source rows yields the same `argus_record_id`
set per SAR-2 upsert lean.

Phase-5 Validator NOT required for snapshot — entries carry per-row
confidence per regex/LLM extraction; Lynceus consumer treats rows as
"not Validator-vetted" via phase_marker distinguishing from `phase_5_v1`.

Per §11 #1 / #7 / #8: every exported row carries verbatim source_url +
source_excerpt; no fabrication; ≤200-char excerpt enforced; no promotion
to identifiers happens at snapshot time.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_EXPORT_DIR = REPO_ROOT / "exports"
PHASE_MARKER = "phase_4_wave_a_snapshot"


def _short_hash(repo: Path, ref: str = "HEAD") -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "--short", ref], text=True
    ).strip()


def _file_blob_short(repo: Path, path: str) -> str:
    """Return short SHA of the file's current blob (tracks file content, not commit)."""
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", f"HEAD:{path}"], text=True
    ).strip()[:7]


def _argus_record_id(source_id: int, identifier: str, candidate_type: str) -> str:
    """Deterministic hash → stable across re-runs per SAR-2 upsert lean."""
    payload = f"{source_id}|{candidate_type}|{identifier}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _excerpt_truncate(s: str, max_chars: int = 200) -> str:
    if not s:
        return s
    return s if len(s) <= max_chars else s[:max_chars]


def collect_wave_a_rows(conn: sqlite3.Connection) -> list[dict]:
    """Wave-A staged rows = `extraction_runs.notes` carries `wave: A` marker."""
    rows = conn.execute(
        """
        SELECT
            ro.id,
            ro.source_id,
            ro.extraction_run_id,
            ro.source_url,
            ro.raw_payload,
            ro.candidate_identifier,
            ro.candidate_type,
            ro.candidate_category,
            ro.candidate_manufacturer,
            ro.source_excerpt,
            ro.captured_at,
            ro.notes,
            er.notes AS extraction_run_notes,
            s.name AS source_name,
            s.source_type
        FROM raw_observations ro
        JOIN extraction_runs er ON er.id = ro.extraction_run_id
        JOIN sources s ON s.id = ro.source_id
        WHERE
            er.notes IS NOT NULL
            AND substr(er.notes, 1, 1) = '{'
            AND json_extract(er.notes, '$.wave') = 'A'
        ORDER BY ro.id
        """
    ).fetchall()

    cols = ["id", "source_id", "extraction_run_id", "source_url", "raw_payload",
            "candidate_identifier", "candidate_type", "candidate_category",
            "candidate_manufacturer", "source_excerpt", "captured_at", "notes",
            "extraction_run_notes", "source_name", "source_type"]
    return [dict(zip(cols, r)) for r in rows]


def build_entries(rows: list[dict]) -> tuple[list[dict], dict]:
    """Convert raw rows to export entries; track dropped_in_export tallies."""
    entries: list[dict] = []
    dropped = {
        "no_identifier": 0,
        "excerpt_overflow_after_truncate": 0,  # tracked but should be 0 since we truncate, not drop
        "schema_invalid": 0,
    }

    for row in rows:
        if not row.get("candidate_identifier"):
            dropped["no_identifier"] += 1
            continue

        # Pull confidence from extraction-run notes (per-row in raw_payload.llm_confidence
        # or extraction_runs.notes.kept_by_confidence_band)
        try:
            payload = json.loads(row.get("raw_payload") or "{}")
        except (json.JSONDecodeError, TypeError):
            payload = {}
        confidence = payload.get("llm_confidence", 0)

        excerpt = _excerpt_truncate(row.get("source_excerpt") or "")

        entry = {
            "argus_record_id": _argus_record_id(
                row["source_id"],
                row["candidate_identifier"],
                row["candidate_type"],
            ),
            "identifier_type": row["candidate_type"],
            "identifier": row["candidate_identifier"],
            "manufacturer": row.get("candidate_manufacturer"),
            "device_category": row.get("candidate_category"),
            "model": None,  # not staged at Wave-A; Phase-5 Validator may add
            "confidence": confidence,
            "source_url": row.get("source_url"),
            "source_excerpt": excerpt,
            "source_name": row["source_name"],
            "source_type": row["source_type"],
            "captured_at": row.get("captured_at"),
            "extraction_module": payload.get("extraction_module"),
            "extraction_run_id": row.get("extraction_run_id"),
        }
        entries.append(entry)

    return entries, dropped


def build_meta(entries: list[dict], rows: list[dict], dropped: dict, run_timestamp: str) -> dict:
    """Build _meta block per bible §7.5 + MAC-22 acceptance criteria."""
    bible_head = _short_hash(REPO_ROOT)
    try:
        amendments_blob = _file_blob_short(REPO_ROOT, "BIBLE_AMENDMENTS.md")
    except subprocess.CalledProcessError:
        amendments_blob = "<untracked>"

    # Schema version
    with sqlite3.connect(DEFAULT_DB_PATH) as conn:
        sv = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]

    # Wave-A yield summary
    cohorts_seen: set[str] = set()
    confidence_bands = {"75_89": 0, "90_99": 0, "below_75": 0}
    for row in rows:
        try:
            er_notes = json.loads(row.get("extraction_run_notes") or "{}")
        except (json.JSONDecodeError, TypeError):
            er_notes = {}
        if er_notes.get("cohort"):
            cohorts_seen.add(er_notes["cohort"])
        for band in (er_notes.get("kept_by_confidence_band") or {}):
            confidence_bands[band] = (
                confidence_bands.get(band, 0)
                + (er_notes["kept_by_confidence_band"][band] or 0)
            )

    return {
        "argus_run_id": str(uuid.uuid4()),
        "bible_head_commit": bible_head,
        "bible_amendments_through": amendments_blob,
        "schema_version": sv,
        "phase_marker": PHASE_MARKER,
        "confidence_threshold": 0,
        "wave_a_yield_summary": {
            "rows_staged": len(rows),
            "rows_exported": len(entries),
            "cohorts_with_extractions": sorted(cohorts_seen),
            "confidence_bands": confidence_bands,
            "wave_a_close_at": "2026-05-06T00:44:56Z",  # MAC-25 close
            "wave_a_dispatch_at": "2026-05-05T16:16:10Z",  # MAC-21 creation
        },
        "dropped_in_export": dropped,
        "exported_at": run_timestamp,
        "reconciliation": {
            "source_record_count": len(rows),
            "entries_count": len(entries),
            "dropped_total": sum(dropped.values()),
            "check": (
                "source_record_count − sum(dropped_in_export) = entries_count"
                if (len(rows) - sum(dropped.values())) == len(entries)
                else "RECONCILIATION_MISMATCH"
            ),
        },
        "audit_trail": {
            "mac22_issue": "MAC-22",
            "mac21_step0": "MAC-21",
            "mac23_step1": "MAC-23",
            "mac25_step2": "MAC-25",
            "mac26_step25": "MAC-26",
            "feedback_memories": [
                "feedback_vendor_public_materials_marketing_not_technical.md",
                "feedback_per_cohort_trip_line_multi_cohort_waves.md",
                "feedback_calibration_window_inverse_yield_certainty.md",
                "feedback_fp_rate_cross_field_disambig.md",
            ],
        },
    }


def main() -> int:
    run_dt = datetime.now(timezone.utc)
    run_timestamp = run_dt.strftime("%Y%m%dT%H%M%SZ")
    run_iso = run_dt.isoformat().replace("+00:00", "Z")

    DEFAULT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DEFAULT_EXPORT_DIR / f"argus_export_wave_a_snapshot_{run_timestamp}.json"

    with sqlite3.connect(DEFAULT_DB_PATH) as conn:
        rows = collect_wave_a_rows(conn)

    entries, dropped = build_entries(rows)
    meta = build_meta(entries, rows, dropped, run_iso)
    payload = {"_meta": meta, "entries": entries}

    out_path.write_text(json.dumps(payload, indent=2, default=str))

    # Reconciliation print
    print(f"Wave-A snapshot export written: {out_path.relative_to(REPO_ROOT)}")
    print(f"  schema_version: {meta['schema_version']}")
    print(f"  bible_head_commit: {meta['bible_head_commit']}")
    print(f"  argus_run_id: {meta['argus_run_id']}")
    print(f"  rows staged in DB: {len(rows)}")
    print(f"  entries exported: {len(entries)}")
    print(f"  dropped: {dropped}")
    print(f"  reconciliation: {meta['reconciliation']['check']}")
    if entries:
        print(f"  argus_record_ids: {[e['argus_record_id'] for e in entries]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
