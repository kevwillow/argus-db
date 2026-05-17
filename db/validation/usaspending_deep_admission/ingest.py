"""MAC-172 P4 ingest — USAspending deep-extension admission.

Five disjoint write paths, applied in order against ``db/argus.db``:

  1. UPDATE ``sources`` row id=8 — merge ``notes_json_additions`` from
     ``source_admission_metadata.json`` into the existing notes JSON
     (keys deep-merge; existing keys preserved unless explicitly
     superseded).
  2. INSERT 2,555 net-new ``procurement_records`` rows from
     ``net_new_procurement_records.refined.json``. Idempotent on
     (source_url) — re-runs skip already-present rows.
  3. UPDATE 180 existing ``procurement_records`` rows (2,718 evidence rows
     merged into ``notes.corroborations[]``). One §8.3 +5 boost per
     target row, capped at min(99, current+5). Scoped UPDATE via the
     primary-key anchor ``cross_validation.existing_procurement_record_id``
     (SAR-13 §6 discipline — not pattern-match on candidate_identifier).
     Idempotent — re-runs skip rows already carrying this session's tag in
     ``notes.corroboration_sessions``.
  4. RG5 cross-corroboration markers — append
     ``notes.cross_source_corroboration[]`` to the two existing rows
     identified by the RG5 cross_corroborations artifact.
  5. Stage ``off_target_residue.json`` under
     ``operator_review/usaspending_deep_admission/`` (file copy + README
     pointer). No DB write.

§11 hard-rule compliance:
  - §11 #1 no fabrication — every row carries upstream USAspending verbatim
    fields; no synthetic data.
  - §11 #7 provenance is the database — every INSERT carries source_url +
    source_excerpt; every UPDATE carries the corroboration session tag +
    evidence subset in notes JSON.
  - §11 #8 no confidence drift — the +5 corroboration boost applies the
    §8.3 formula (`min(99, max(originals) + 5)`) against the dispatch-
    ratified scope. See VALIDATOR REPORT for the §11 #8 independence-
    question surface (within-source re-extraction debate flagged for CEO
    ratification).
  - §11 #14 procurement-only never exported to Talos — these rows stay
    procurement-side; no identifier-promotion happens here.

Run from repo root::

    python3 -m db.validation.usaspending_deep_admission.ingest \\
        --dry-run    # default — write nothing, emit per-step counts
        --commit     # write to argus.db; idempotent on re-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Repo-root resolution + companion canonical normalizer.
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

from db.normalize_vendor import normalize_vendor_name  # noqa: E402

DB_PATH = _REPO_ROOT / "db" / "argus.db"
ARTIFACT_DIR = (
    Path.home()
    / "argus-internal"
    / "extraction_outputs"
    / "usaspending_deep_admission"
)
OPERATOR_REVIEW_DIR = (
    _REPO_ROOT
    / "operator_review"
    / "usaspending_deep_admission"
)
SESSION_TAG = "usaspending_deep_admission_2026_05_16"
USASPENDING_SID = 8
SOURCE_EXCERPT_MAX = 200  # procurement_records.source_excerpt CHECK
CORROBORATION_BOOST = 5  # §8.3 corroboration formula bump
CONFIDENCE_CEILING = 99  # §8.3 min(99, max(originals) + 5)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp_excerpt(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    return text[:SOURCE_EXCERPT_MAX]


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@dataclass
class StepResult:
    name: str
    proposed: int
    applied: int
    skipped_idempotent: int
    notes: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.name,
            "proposed": self.proposed,
            "applied": self.applied,
            "skipped_idempotent": self.skipped_idempotent,
            "notes": self.notes,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — sources sid=8 notes_json merge
# ─────────────────────────────────────────────────────────────────────────────


def step_1_update_sources_sid8(conn: sqlite3.Connection, *, commit: bool) -> StepResult:
    meta = _load_json(ARTIFACT_DIR / "source_admission_metadata.json")
    assert meta["_update_target_source_id"] == USASPENDING_SID
    additions = meta["notes_json_additions"]

    row = conn.execute(
        "SELECT notes FROM sources WHERE id = ?", (USASPENDING_SID,)
    ).fetchone()
    if row is None:
        raise RuntimeError(f"sources row id={USASPENDING_SID} missing")

    existing_notes_raw = row["notes"] or "{}"
    existing_notes = json.loads(existing_notes_raw)

    # Idempotency: if the deeper_extraction_session key matches our session,
    # the merge has already landed.
    if existing_notes.get("deeper_extraction_session") == additions.get(
        "deeper_extraction_session"
    ):
        return StepResult(
            name="step_1_update_sources_sid8",
            proposed=1,
            applied=0,
            skipped_idempotent=1,
            notes=["sid=8 already carries deeper_extraction_session marker"],
        )

    # Deep-merge: additions override on key collision, but no existing keys
    # are dropped.
    merged = dict(existing_notes)
    merged.update(additions)
    merged["_paperclip_merge_at_utc"] = _now_iso()

    if commit:
        conn.execute(
            "UPDATE sources SET notes = ? WHERE id = ?",
            (json.dumps(merged, sort_keys=True), USASPENDING_SID),
        )

    return StepResult(
        name="step_1_update_sources_sid8",
        proposed=1,
        applied=1 if commit else 0,
        skipped_idempotent=0,
        notes=[f"merged {len(additions)} new keys into sid=8 notes JSON"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — INSERT 2,555 net-new procurement_records
# ─────────────────────────────────────────────────────────────────────────────


def _build_agency_name(row: dict[str, Any]) -> str:
    agency = (row.get("agency_name") or "").strip()
    sub = (row.get("sub_agency_name") or "").strip()
    if agency and sub:
        return f"{agency} / {sub}"
    return agency or sub


def _build_net_new_notes(row: dict[str, Any]) -> dict[str, Any]:
    award_id = row["award_id_usaspending"]
    return {
        "agency_slug": None,
        "award_id": award_id,
        "awarding_agency": row.get("agency_name"),
        "awarding_sub_agency": row.get("sub_agency_name"),
        "internal_id": row.get("internal_id"),
        "matched_query_name": row.get("matched_query_name"),
        "match_classification": row.get("match_classification"),
        "manufacturer_id_in_argus": row.get("manufacturer_id_in_argus"),
        "place_of_performance": {
            "state_code": row.get("place_of_performance_state"),
        },
        "period_of_performance": {
            "start_date": row.get("period_of_performance_start"),
            "end_date": row.get("period_of_performance_current_end"),
        },
        "naics_code": row.get("naics_code"),
        "psc_code": row.get("psc_code"),
        "award_type_code": row.get("award_type_code"),
        "registry": "usaspending",
        "source_id": USASPENDING_SID,
        "session_tag": SESSION_TAG,
        "fetched_at_utc": row.get("fetched_at_utc"),
        "upstream_recipient_name_verbatim": row.get(
            "upstream_recipient_name_verbatim"
        ),
        "vendor_canonical_label_at_extraction": row.get("vendor_canonical_name"),
    }


def step_2_insert_net_new(conn: sqlite3.Connection, *, commit: bool) -> StepResult:
    payload = _load_json(ARTIFACT_DIR / "net_new_procurement_records.refined.json")
    rows = payload["rows"]
    proposed = len(rows)
    applied = 0
    skipped = 0
    band_caps: list[str] = []

    # Pre-load existing source_urls for fast idempotency check.
    existing_urls = {
        r[0]
        for r in conn.execute(
            "SELECT source_url FROM procurement_records "
            "WHERE source_url LIKE 'https://www.usaspending.gov/award/%'"
        )
    }

    for row in rows:
        source_url = row["source_url"]
        # Strip trailing slash for canonical match (existing DB rows store
        # without the trailing slash; refined.json carries the trailing slash).
        canonical_url = source_url.rstrip("/")
        # Idempotency: skip if URL already present.
        if (
            source_url in existing_urls
            or canonical_url in existing_urls
            or (canonical_url + "/") in existing_urls
        ):
            skipped += 1
            continue

        upstream_vendor = row["upstream_recipient_name_verbatim"]
        agency = _build_agency_name(row)
        normalized = normalize_vendor_name(upstream_vendor)
        excerpt = _clamp_excerpt(row.get("description_verbatim"))
        # contract_date: prefer period_of_performance_start; else NULL
        contract_date = row.get("period_of_performance_start")
        if contract_date:
            # USAspending dates are 'YYYY-MM-DD HH:MM:SS' or just 'YYYY-MM-DD'
            contract_date = str(contract_date).split(" ")[0]
        confidence = row.get("proposed_confidence_at_promotion", 85)
        # §8.2 procurement band is 70-85 single-source. Enforce ceiling.
        if confidence > 85:
            band_caps.append(
                f"capped {source_url} from {confidence} to 85 (§8.2 procurement)"
            )
            confidence = 85
        notes = _build_net_new_notes(row)
        contract_amount = row.get("award_value")
        if contract_amount in (None, 0.0, 0):
            # USAspending occasionally returns award_value=0 for placeholder /
            # delivery-order parents. Keep as 0.0 to preserve upstream value.
            contract_amount = float(contract_amount) if contract_amount is not None else None

        if commit:
            conn.execute(
                """
                INSERT INTO procurement_records (
                    agency_name,
                    agency_geographic_scope,
                    vendor_canonical_name,
                    product_family,
                    contract_amount_usd,
                    contract_date,
                    source_url,
                    source_type,
                    source_excerpt,
                    confidence,
                    captured_at,
                    linked_identifier_id,
                    notes,
                    vendor_canonical_normalized
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'procurement', ?, ?, CURRENT_TIMESTAMP, NULL, ?, ?)
                """,
                (
                    agency,
                    row.get("place_of_performance_state"),
                    upstream_vendor,
                    None,
                    contract_amount,
                    contract_date,
                    canonical_url,
                    excerpt,
                    confidence,
                    json.dumps(notes, sort_keys=True),
                    normalized,
                ),
            )
        applied += 1
        existing_urls.add(canonical_url)

    notes_out = [
        f"net-new rows applied={applied} skipped_idempotent={skipped}",
        f"band-cap-on-insert events: {len(band_caps)}",
    ]
    if band_caps[:3]:
        notes_out.append(f"first cap events: {band_caps[:3]}")
    return StepResult(
        name="step_2_insert_net_new",
        proposed=proposed,
        applied=applied if commit else 0,
        skipped_idempotent=skipped,
        notes=notes_out,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — UPDATE existing rows with §8.3 corroboration
# ─────────────────────────────────────────────────────────────────────────────


def _evidence_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "award_id": row["award_id_usaspending"],
        "internal_id": row.get("internal_id"),
        "agency_name": row.get("agency_name"),
        "sub_agency_name": row.get("sub_agency_name"),
        "award_value": row.get("award_value"),
        "place_of_performance_state": row.get("place_of_performance_state"),
        "description_verbatim": (row.get("description_verbatim") or "")[
            :SOURCE_EXCERPT_MAX
        ],
        "source_url": row["source_url"].rstrip("/"),
        "match_classification": row.get("match_classification"),
        "matched_query_name": row.get("matched_query_name"),
        "fetched_at_utc": row.get("fetched_at_utc"),
    }


def step_3_update_corroborations(
    conn: sqlite3.Connection, *, commit: bool
) -> StepResult:
    payload = _load_json(ARTIFACT_DIR / "corroborations.refined.json")
    rows = payload["rows"]
    proposed_evidence = len(rows)

    # Bucket evidence rows by target existing_id.
    by_eid: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        eid = r["cross_validation"]["existing_procurement_record_id"]
        if eid is None:
            continue
        by_eid.setdefault(eid, []).append(r)

    applied_rows = 0
    skipped_rows = 0
    band_lifts: list[tuple[int, int, int]] = []
    evidence_merged = 0
    evidence_already_present = 0

    for eid, ev_list in by_eid.items():
        existing = conn.execute(
            "SELECT id, confidence, notes FROM procurement_records WHERE id = ?",
            (eid,),
        ).fetchone()
        if existing is None:
            raise RuntimeError(f"corroboration target eid={eid} not present in DB")
        notes_raw = existing["notes"] or "{}"
        notes = json.loads(notes_raw)
        sessions: list[str] = notes.setdefault("corroboration_sessions", [])
        # Idempotency: skip target row if this session already merged.
        if SESSION_TAG in sessions:
            skipped_rows += 1
            # Count evidence rows already present so the report reconciles.
            existing_award_ids = {
                e.get("award_id")
                for e in notes.get("corroborations", [])
            }
            for er in ev_list:
                if er["award_id_usaspending"] in existing_award_ids:
                    evidence_already_present += 1
            continue

        evidence_list = notes.setdefault("corroborations", [])
        existing_award_ids = {e.get("award_id") for e in evidence_list}
        new_evidence_for_row = 0
        for er in ev_list:
            if er["award_id_usaspending"] in existing_award_ids:
                evidence_already_present += 1
                continue
            evidence_list.append(_evidence_row(er))
            new_evidence_for_row += 1
        evidence_merged += new_evidence_for_row
        sessions.append(SESSION_TAG)

        # §8.3 corroboration formula: min(99, max(originals) + 5)
        old_conf = existing["confidence"]
        new_conf = min(CONFIDENCE_CEILING, old_conf + CORROBORATION_BOOST)
        if new_conf != old_conf:
            band_lifts.append((eid, old_conf, new_conf))

        notes["last_corroboration_at_utc"] = _now_iso()

        if commit:
            conn.execute(
                "UPDATE procurement_records SET notes = ?, confidence = ? WHERE id = ?",
                (json.dumps(notes, sort_keys=True), new_conf, eid),
            )
        applied_rows += 1

    notes_out = [
        f"target rows updated={applied_rows} skipped_idempotent={skipped_rows}",
        f"evidence rows merged={evidence_merged} already_present={evidence_already_present}",
        f"confidence lifts: {len(band_lifts)} rows (e.g. {band_lifts[:3]})",
        f"unique target eids: {len(by_eid)}",
    ]
    return StepResult(
        name="step_3_update_corroborations",
        proposed=proposed_evidence,
        applied=evidence_merged if commit else 0,
        skipped_idempotent=evidence_already_present,
        notes=notes_out,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — RG5 cross-source corroboration markers
# ─────────────────────────────────────────────────────────────────────────────


def step_4_rg5_cross_corroborations(
    conn: sqlite3.Connection, *, commit: bool
) -> StepResult:
    payload = _load_json(ARTIFACT_DIR / "rg5_cross_corroborations.json")
    rows = payload["rows"]
    proposed = len(rows)
    applied = 0
    skipped = 0
    # Each row carries a usaspending award_id; resolve eid via the
    # corroborations artifact mapping.
    corr = _load_json(ARTIFACT_DIR / "corroborations.refined.json")["rows"]
    award_to_eid = {
        c["award_id_usaspending"]: c["cross_validation"][
            "existing_procurement_record_id"
        ]
        for c in corr
        if c["cross_validation"]["existing_procurement_record_id"] is not None
    }

    for row in rows:
        award_id = row["usaspending_row"]["award_id"]
        eid = award_to_eid.get(award_id)
        if eid is None:
            raise RuntimeError(
                f"RG5 cross-corroboration award_id={award_id} not mapped"
            )
        existing = conn.execute(
            "SELECT notes FROM procurement_records WHERE id = ?", (eid,)
        ).fetchone()
        notes = json.loads(existing["notes"] or "{}")
        marker_list = notes.setdefault("cross_source_corroboration", [])
        marker_key = f"rg5_sec_edgar::{row['rg5_row']['source_url']}::{award_id}"
        if any(m.get("marker_key") == marker_key for m in marker_list):
            skipped += 1
            continue
        marker = {
            "marker_key": marker_key,
            "session_tag": SESSION_TAG,
            "cross_source": "rg5_sec_edgar",
            "rg5_source_url": row["rg5_row"]["source_url"],
            "rg5_section_ref": row["rg5_row"].get("section_ref"),
            "rg5_context_excerpt_30w": row["rg5_row"].get("context_excerpt_30w"),
            "match_basis": row["match_basis"],
            "matched_award_id": award_id,
            "marked_at_utc": _now_iso(),
        }
        marker_list.append(marker)
        if commit:
            conn.execute(
                "UPDATE procurement_records SET notes = ? WHERE id = ?",
                (json.dumps(notes, sort_keys=True), eid),
            )
        applied += 1
    return StepResult(
        name="step_4_rg5_cross_corroborations",
        proposed=proposed,
        applied=applied if commit else 0,
        skipped_idempotent=skipped,
        notes=[f"RG5 markers applied={applied} skipped_idempotent={skipped}"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — stage off-target residue for operator review
# ─────────────────────────────────────────────────────────────────────────────


def step_5_stage_off_target_residue(*, commit: bool) -> StepResult:
    src = ARTIFACT_DIR / "off_target_residue.json"
    payload = _load_json(src)
    if isinstance(payload, list):
        count = len(payload)
    elif isinstance(payload, dict):
        count = payload.get("row_count") or (
            payload.get("token_overlap_count", 0) + payload.get("off_target_count", 0)
        )
    else:
        count = 0
    OPERATOR_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    target = OPERATOR_REVIEW_DIR / "off_target_residue.json"
    readme = OPERATOR_REVIEW_DIR / "README.md"
    already = target.exists()
    if commit and not already:
        shutil.copy2(src, target)
        readme.write_text(
            "# USAspending deep-admission off-target residue\n\n"
            f"Source artifact: `{src}`  \n"
            f"Session tag: `{SESSION_TAG}`  \n"
            f"Rows: {count}\n\n"
            "USAspending's `recipient_search_text` is fuzzy/substring "
            "(see HANDOFF_TO_VALIDATOR.md §4). These TOKEN_OVERLAP + "
            "OFF_TARGET rows did not pass the EXACT/CONTAINS filter in the "
            "extraction worker's refinement pass and were routed here for "
            "operator review rather than auto-ingest. Operator promotes "
            "any false-negative entries (legitimate but surprising name "
            "form) back to the validator queue.\n\n"
            "No DB writes. No identifier promotion. Audit-trail only.\n",
            encoding="utf-8",
        )
    return StepResult(
        name="step_5_stage_off_target_residue",
        proposed=count,
        applied=0 if (already or not commit) else count,
        skipped_idempotent=count if already else 0,
        notes=[
            f"target: {target}",
            f"residue rows: {count}",
            f"already_staged={already}",
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Apply writes (DB UPDATE/INSERT + file staging). Without "
        "this flag the run is dry: counts and notes only.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=_REPO_ROOT
        / "extraction_outputs"
        / "mac172"
        / "ingest_report.json",
        help="Where to write the per-step report JSON.",
    )
    args = parser.parse_args(argv)

    conn = _connect()
    if args.commit:
        conn.execute("BEGIN")

    pre = {
        "procurement_records_count": conn.execute(
            "SELECT COUNT(*) FROM procurement_records"
        ).fetchone()[0],
        "procurement_records_max_id": conn.execute(
            "SELECT MAX(id) FROM procurement_records"
        ).fetchone()[0],
        "schema_version_max": conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0],
    }

    results: list[StepResult] = []
    try:
        results.append(step_1_update_sources_sid8(conn, commit=args.commit))
        results.append(step_2_insert_net_new(conn, commit=args.commit))
        results.append(step_3_update_corroborations(conn, commit=args.commit))
        results.append(step_4_rg5_cross_corroborations(conn, commit=args.commit))
        results.append(step_5_stage_off_target_residue(commit=args.commit))
    except Exception:
        if args.commit:
            conn.rollback()
        raise

    if args.commit:
        conn.commit()

    post = {
        "procurement_records_count": conn.execute(
            "SELECT COUNT(*) FROM procurement_records"
        ).fetchone()[0],
        "procurement_records_max_id": conn.execute(
            "SELECT MAX(id) FROM procurement_records"
        ).fetchone()[0],
        "procurement_confidence_distribution": dict(
            conn.execute(
                "SELECT confidence, COUNT(*) FROM procurement_records "
                "GROUP BY confidence ORDER BY confidence"
            ).fetchall()
        ),
    }

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "run_at_utc": _now_iso(),
        "session_tag": SESSION_TAG,
        "mode": "commit" if args.commit else "dry_run",
        "pre_state": pre,
        "post_state": post,
        "steps": [r.as_dict() for r in results],
    }
    args.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
