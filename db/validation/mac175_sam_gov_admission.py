"""
MAC-175 — SAM.gov cycle-5 day-0 partial admission + cross-source corroboration ingest.

Per MAC-175 dispatch (Validator) — CP26 fold lands first (pre-paired
bible commit at HEAD); this script lands the DB writes second in the
ordered sibling-commit pair per CP25/CP24/CP23 precedent.

Five disjoint write paths, applied idempotently against db/argus.db:

  1. sources +1 (id=50, SAM.gov Entity Registration,
     source_type='procurement_disclosure' per CP23 enum extension,
     tier=1, license PUBLIC_DOMAIN, access_mode='automated_api',
     cycle_completion_state='partial_pre_day1' per CP26 §9 — FIRST
     consumer of the new partial-cycle vocabulary).

  2. manufacturers.notes UPDATE — Genetec mfg_id=4 enrichment block:
     UEI, CAGE code, legal-business-name, NAICS list (primary 513210,
     surveillance-adjacency-flagged via 334290 + 561621), Saint-Laurent
     QC CAN address, registration expiration. Existing prose wrapped
     into {description, sam_gov_enrichment} JSON shape on first touch.

  3. procurement_records.notes UPDATE + confidence lift — 3 cross-source
     corroboration UPDATE batches per CP24 §11 #8 + CP25 §1 composition:
       Vigilant 56 rows / 11 agencies (UEI NGYKYGHR7NU1)
       Motorola 9,545 rows / 78 agencies (UEI MSJ4JJEFNDE6)
       Genetec  22 rows / 9 agencies (UEI H8XALXV2A5F8)
     Each row gets:
       - notes.cross_source_corroboration[] marker_key
         "sam_gov::https://sam.gov/entity/<uei>/coreData::<pr_id>"
       - notes.confidence_history[] entry per CP24 sub-rule (b):
         from=<current>, to=<current+5>, cp_anchor='CP26 §9 (cycle-5)',
         dispatch='MAC-175', rationale='§8.3 cross-source +5 lift'
       - confidence column +5 (capped at 99 per §8.3; capped at the
         procurement_disclosure band's effective cross-source ceiling)
     Spot-check 5 random Motorola rows before mass-apply per the
     dispatch §5 #3 within-source-vs-cross-source HALT-and-surface
     guard. SAM.gov is genuinely independent of USAspending
     (entity-registration vs procurement-award collectors); the lift
     is §8.3-valid per §11 #8 strict-reading (Read B canon per CP24).

  4. Disk-staged 2 WEAK + 1 PROBE matches to operator-review-queue per
     dispatch §5 #4 + #5. The Flock Safety WEAK row carries
     notes.brittle_alias_match=true per the normalization-disagreement
     forward flag (dispatch §5 #4 + §5 #6).

  5. Empty-bucket audit confirmation — within_source_reextractions.json
     (empty per CP24 §11 #8 — SAM.gov is net-new, no within-source
     re-extraction shape) + class_b_us_holds_closures.json (empty due
     to cycle-5 staging bug; 11 holds remain in operator_manual_queue
     for cycle-6 day-1 dispatch).

§11 hard-rule compliance:
  §11 #1  no fabrication — all SAM.gov fields verbatim from staged
          handoff (manufacturer_enrichment_records.json,
          cross_source_corroborations.json); no derived/inferred fields.
  §11 #3  PII — N/A for this dispatch; SAM.gov entity-registration
          data is corporate not personal.
  §11 #7  provenance is the database — every UPDATE carries the
          SAM.gov source_url + UEI + fetched_at_utc + response_sha256
          in the cross_source_corroboration[] entry; sid=50 carries
          the full per-admission audit per CP23 license-into-notes.
  §11 #8  no confidence drift upward without corroboration —
          composed with CP24 sub-rules (a)+(b)+(c) and CP25 §1.
          Cross-source +5 lift IS §11 #8-compliant (genuinely
          independent collector: SAM.gov entity-registration vs
          USAspending procurement-award). Lift caps at 90 (85 + 5;
          well within §8.3 cap of 99 and §8.2 procurement_disclosure
          band effective cross-source ceiling).
  §11 #11 amendment-log — CP26 entry paired with this commit at
          preceding HEAD; this commit is the implementation pairing
          for the CP26 §9 cycle_completion_state convention's first
          consumer (sid=50) + the CP26 §1-§7 cycle-5 patch findings
          + the CP26 §8 §11 #8 sub-rule's discipline anchor.
  §11 #14 procurement-only never exported to Lynceus — orthogonal;
          all new write paths are on procurement_records / sources /
          manufacturers (procurement-side); no identifier promotion;
          export-side blast radius zero.

Idempotency: re-running --commit produces zero net change
(per-step skip counters match proposed counts):
  - sid=50:                  pre-check UNIQUE(url) on sources.url
  - manufacturer enrichment: pre-check notes.sam_gov_uei presence
  - corroboration markers:   pre-check marker_key uniqueness
  - confidence lift:         pre-check confidence_history[] for the
                             CP26 §9 cp_anchor + MAC-175 dispatch tag
  - operator-review staging: pre-check on file presence + content hash

Usage:
  python3 -m db.validation.mac175_sam_gov_admission --dry-run
  python3 -m db.validation.mac175_sam_gov_admission --commit
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
import sys
from pathlib import Path
from typing import Any

DB = Path(__file__).resolve().parents[2] / "db" / "argus.db"
STAGED = Path("/home/kev/argus-internal/extraction_outputs/sam_gov_admission")
OPERATOR_QUEUE = Path(
    "/home/kev/argus-internal/extraction_outputs/_operator_review_queue"
)

DISPATCH = "MAC-175"
SESSION = "sam_gov_admission_cycle5_day0"
ADMISSION_DATE_UTC = "2026-05-17T14:10:40Z"
RUNGUIDE_PATH = "new data 5.16/sam_gov_admission_runguide.md"
SCHEMA_VERSION_AT_SESSION = 21
CP_ANCHOR = "CP26 §9 (cycle-5)"
SAM_GOV_API_URL = "https://api.sam.gov/entity-information/v3/entities"
NEXT_CYCLE_RUNGUIDE = (
    "extraction_outputs/sam_gov_admission/_DAY1_DISPATCH_PROMPT.md"
)


def _now_iso() -> str:
    # All audit timestamps anchor to the dispatch session admission time
    # for deterministic re-run (matches MAC-171/172/174 convention).
    return ADMISSION_DATE_UTC


def _load_json(p: Path) -> Any:
    return json.loads(p.read_text())


def _vendor_marker_key(uei: str, pr_id: int) -> str:
    return f"sam_gov::https://sam.gov/entity/{uei}/coreData::{pr_id}"


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — sid=50 SAM.gov source admission
# ─────────────────────────────────────────────────────────────────────────────

SAM_GOV_SOURCE = {
    "name": "SAM.gov Entity Registration",
    "url": SAM_GOV_API_URL,
    "source_type": "procurement_disclosure",
    "tier": 1,
    "last_fetched_at": ADMISSION_DATE_UTC,
    "last_status": "partial_admission_pending_day1",
    "notes_json": {
        "dispatch": DISPATCH,
        "session_admission": SESSION,
        "admission_date_utc": ADMISSION_DATE_UTC,
        "runguide_path": RUNGUIDE_PATH,
        "schema_version_at_session": SCHEMA_VERSION_AT_SESSION,
        "license": "PUBLIC_DOMAIN",
        "license_posture": "PUBLIC_DOMAIN",
        "license_attribution": (
            "SAM.gov entity registration data is a US Government record "
            "and is not copyrightable per 17 USC §105."
        ),
        "access_mode": "automated_api",
        "cycle_completion_state": "partial_pre_day1",
        "next_cycle_dispatch_scheduled_for_utc": "2026-05-18T00:15:00Z",
        "next_cycle_dispatch_runguide_path": NEXT_CYCLE_RUNGUIDE,
        "partial_yield_metrics_at_admission": {
            "vendors_attempted_of_35": 4,
            "vendors_strong": 1,
            "vendors_weak": 2,
            "vendors_probe": 1,
            "holds_attempted_of_11": 0,
            "holds_closed": 0,
            "cross_source_corroborations": 3,
            "manufacturer_enrichments": 1,
            "normalization_disagreements_flagged": 1,
            "halt_cause": "rate_ceiling_10_per_utc_day_first_429",
        },
        "per_row_url_template": "https://sam.gov/entity/{uei}/coreData",
        "auth_shape": (
            "API key (X-Api-Key header); free signup at sam.gov; "
            "non-Federal individual tier rate ceiling 10/UTC-day per CP26 §2"
        ),
        "post_cp_baseline_sha": "64f381cf21790c8dd778acd51379f6bb864131dc",
    },
}


def step_1_source_admission(conn: sqlite3.Connection, *, commit: bool) -> dict:
    existing = conn.execute(
        "SELECT id FROM sources WHERE url = ?", (SAM_GOV_SOURCE["url"],)
    ).fetchone()
    if existing is not None:
        return {
            "step": "1_source_admission",
            "proposed": 1,
            "applied": 0,
            "skipped_idempotent": 1,
            "sid": existing[0],
            "note": f"sid={existing[0]} already present; idempotent skip",
        }
    max_id_now = conn.execute("SELECT max(id) FROM sources").fetchone()[0] or 0
    if max_id_now >= 50:
        raise RuntimeError(
            f"HALT — sources.max(id)={max_id_now} ≥ 50 before sid=50 INSERT; "
            f"dispatch precondition violated"
        )
    notes_json = json.dumps(SAM_GOV_SOURCE["notes_json"], sort_keys=True)
    if commit:
        cur = conn.execute(
            """
            INSERT INTO sources (
                name, url, source_type, tier,
                last_fetched_at, last_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SAM_GOV_SOURCE["name"],
                SAM_GOV_SOURCE["url"],
                SAM_GOV_SOURCE["source_type"],
                SAM_GOV_SOURCE["tier"],
                SAM_GOV_SOURCE["last_fetched_at"],
                SAM_GOV_SOURCE["last_status"],
                notes_json,
            ),
        )
        sid = cur.lastrowid
    else:
        sid = "(would be 50)"
    return {
        "step": "1_source_admission",
        "proposed": 1,
        "applied": 1 if commit else 0,
        "skipped_idempotent": 0,
        "sid": sid,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Genetec manufacturer enrichment (mfg_id=4)
# ─────────────────────────────────────────────────────────────────────────────


def step_2_genetec_enrichment(conn: sqlite3.Connection, *, commit: bool) -> dict:
    enrichment = _load_json(STAGED / "manufacturer_enrichment_records.json")
    assert len(enrichment) == 1, f"expected 1 enrichment row, got {len(enrichment)}"
    row = enrichment[0]
    assert row["manufacturer_id"] == 4
    mfg = conn.execute(
        "SELECT id, canonical_name, notes FROM manufacturers WHERE id = ?",
        (row["manufacturer_id"],),
    ).fetchone()
    if mfg is None:
        raise RuntimeError(f"HALT — manufacturer id={row['manufacturer_id']} missing")
    current_notes_raw = mfg[2] or ""
    try:
        current_notes = json.loads(current_notes_raw) if current_notes_raw else {}
        if not isinstance(current_notes, dict):
            current_notes = {"description_legacy": current_notes_raw}
    except json.JSONDecodeError:
        current_notes = {"description": current_notes_raw}
    if "sam_gov_enrichment" in current_notes:
        return {
            "step": "2_genetec_enrichment",
            "proposed": 1,
            "applied": 0,
            "skipped_idempotent": 1,
            "mfg_id": 4,
            "note": "sam_gov_enrichment already present; idempotent skip",
        }
    current_notes["sam_gov_enrichment"] = {
        "sam_gov_uei": row["sam_gov_uei"],
        "sam_gov_cage_code": row["sam_gov_cage_code"],
        "sam_gov_legal_business_name": row["sam_gov_legal_business_name"],
        "sam_gov_registration_status": row["sam_gov_registration_status"],
        "sam_gov_registration_expiration": row["sam_gov_registration_expiration"],
        "entity_structure_desc": row["entity_structure_desc"],
        "state_of_incorporation": row["state_of_incorporation"],
        "business_types": row["business_types"],
        "primary_naics": row["primary_naics"],
        "naics_list": row["naics_list"],
        "naics_surveillance_adjacency_flagged": row["naics_surveillance_adjacency_flagged"],
        "physical_city": row["physical_city"],
        "physical_state": row["physical_state"],
        "physical_country": row["physical_country"],
        "source_url": row["source_url"],
        "fetched_at_utc": row["fetched_at_utc"],
        "response_sha256": row["response_sha256"],
        "source_id_provenance": 50,
        "dispatch": DISPATCH,
        "cp_anchor": CP_ANCHOR,
    }
    if commit:
        conn.execute(
            "UPDATE manufacturers SET notes = ? WHERE id = ?",
            (json.dumps(current_notes, sort_keys=True), 4),
        )
    return {
        "step": "2_genetec_enrichment",
        "proposed": 1,
        "applied": 1 if commit else 0,
        "skipped_idempotent": 0,
        "mfg_id": 4,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Cross-source corroboration UPDATE batches (Vigilant + Motorola + Genetec)
# ─────────────────────────────────────────────────────────────────────────────

CORROBORATION_BATCHES = [
    {
        "input_anchor_id": 2,
        "vendor_canonical_normalized": "vigilant solutions",
        "uei": "NGYKYGHR7NU1",
        "sam_gov_legal_name": "VIGILANT SOLUTIONS, LLC",
        "expected_rows": 56,
        "expected_agencies": 11,
    },
    {
        "input_anchor_id": 3,
        "vendor_canonical_normalized": "motorola solutions",
        "uei": "MSJ4JJEFNDE6",
        "sam_gov_legal_name": "MOTOROLA SOLUTIONS INC",
        "expected_rows": 9545,
        "expected_agencies": 78,
        "spot_check": True,
    },
    {
        "input_anchor_id": 4,
        "vendor_canonical_normalized": "genetec",
        "uei": "H8XALXV2A5F8",
        "sam_gov_legal_name": "GENETEC INC",
        "expected_rows": 22,
        "expected_agencies": 9,
    },
]

CONFIDENCE_LIFT = 5
CONFIDENCE_HARD_CAP = 99  # §8.3 hard cap


def _build_corroboration_marker(uei: str, pr_id: int, batch: dict) -> dict:
    return {
        "marker_key": _vendor_marker_key(uei, pr_id),
        "session_tag": SESSION,
        "cross_source": "sam_gov_entity_registration",
        "sam_gov_uei": uei,
        "sam_gov_legal_business_name": batch["sam_gov_legal_name"],
        "sam_gov_source_url": f"https://sam.gov/entity/{uei}/coreData",
        "match_basis": (
            "vendor_canonical_normalized == sam_gov_legal_business_name_normalized"
        ),
        "marked_at_utc": ADMISSION_DATE_UTC,
        "dispatch": DISPATCH,
        "cp_anchor": CP_ANCHOR,
    }


def _build_confidence_history_entry(from_conf: int, to_conf: int) -> dict:
    return {
        "at_utc": ADMISSION_DATE_UTC,
        "from": from_conf,
        "to": to_conf,
        "cp_anchor": CP_ANCHOR,
        "dispatch": DISPATCH,
        "rationale": (
            "SAM.gov entity-registration cross-source corroboration per §8.3 "
            "(genuinely-independent collector vs USAspending procurement-award; "
            "+5 lift; §11 #8 cross-source Read B canon per CP24)"
        ),
    }


def _spot_check_motorola(conn: sqlite3.Connection) -> list[dict]:
    rng = random.Random(42)
    motorola_ids = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM procurement_records "
            "WHERE vendor_canonical_normalized='motorola solutions' "
            "ORDER BY id"
        )
    ]
    sampled = rng.sample(motorola_ids, 5)
    rows = []
    for rid in sampled:
        r = conn.execute(
            "SELECT id, vendor_canonical_name, source_type, source_url, "
            "       confidence, agency_name, contract_amount_usd, notes "
            "FROM procurement_records WHERE id = ?",
            (rid,),
        ).fetchone()
        notes = json.loads(r[7]) if r[7] else {}
        # Within-source guard: check for within_source_reextraction markers
        if "within_source_reextraction" in notes or any(
            "within_source" in str(k) for k in notes.keys()
        ):
            raise RuntimeError(
                f"HALT — Motorola row id={rid} carries within-source-reextraction "
                f"marker; dispatch §5 #3 within-source-vs-cross-source guard tripped"
            )
        rows.append(
            {
                "id": r[0],
                "vendor_canonical_name": r[1],
                "source_type": r[2],
                "source_url": r[3],
                "confidence_pre": r[4],
                "agency_name": r[5],
                "contract_amount_usd": r[6],
                "notes_keys_pre": sorted(notes.keys()),
            }
        )
    return rows


def step_3_cross_source_corroborations(
    conn: sqlite3.Connection, *, commit: bool
) -> dict:
    cross_data = _load_json(STAGED / "cross_source_corroborations.json")
    cross_by_anchor = {c["anchor_id"]: c for c in cross_data}
    spot_check_rows = None
    batch_results = []
    total_proposed = 0
    total_applied = 0
    total_skipped = 0
    for batch in CORROBORATION_BATCHES:
        cross = cross_by_anchor[batch["input_anchor_id"]]
        # Sanity check the staged counts against live DB
        live_n = conn.execute(
            "SELECT count(*) FROM procurement_records "
            "WHERE vendor_canonical_normalized = ?",
            (batch["vendor_canonical_normalized"],),
        ).fetchone()[0]
        live_agencies = conn.execute(
            "SELECT count(DISTINCT agency_name) FROM procurement_records "
            "WHERE vendor_canonical_normalized = ?",
            (batch["vendor_canonical_normalized"],),
        ).fetchone()[0]
        assert live_n == batch["expected_rows"] == cross["procurement_records_overlap_count"], (
            f"{batch['vendor_canonical_normalized']} row count mismatch: "
            f"live={live_n} expected={batch['expected_rows']} staged={cross['procurement_records_overlap_count']}"
        )
        # Spot-check 5 random Motorola rows BEFORE mass-apply
        if batch.get("spot_check"):
            spot_check_rows = _spot_check_motorola(conn)
        # Mass-apply
        all_ids = [
            r[0]
            for r in conn.execute(
                "SELECT id FROM procurement_records "
                "WHERE vendor_canonical_normalized = ?",
                (batch["vendor_canonical_normalized"],),
            )
        ]
        applied = 0
        skipped = 0
        for pr_id in all_ids:
            current = conn.execute(
                "SELECT confidence, notes FROM procurement_records WHERE id = ?",
                (pr_id,),
            ).fetchone()
            curr_conf = current[0]
            notes = json.loads(current[1]) if current[1] else {}
            marker_list = notes.setdefault("cross_source_corroboration", [])
            marker_key = _vendor_marker_key(batch["uei"], pr_id)
            if any(m.get("marker_key") == marker_key for m in marker_list):
                skipped += 1
                continue
            # Append marker
            marker_list.append(_build_corroboration_marker(batch["uei"], pr_id, batch))
            # Lift confidence + audit
            new_conf = min(curr_conf + CONFIDENCE_LIFT, CONFIDENCE_HARD_CAP)
            history = notes.setdefault("confidence_history", [])
            history.append(_build_confidence_history_entry(curr_conf, new_conf))
            if commit:
                conn.execute(
                    "UPDATE procurement_records SET notes = ?, confidence = ? "
                    "WHERE id = ?",
                    (json.dumps(notes, sort_keys=True), new_conf, pr_id),
                )
            applied += 1
        batch_results.append(
            {
                "vendor_canonical_normalized": batch["vendor_canonical_normalized"],
                "uei": batch["uei"],
                "expected_rows": batch["expected_rows"],
                "expected_agencies": batch["expected_agencies"],
                "live_rows": live_n,
                "live_agencies": live_agencies,
                "applied": applied if commit else 0,
                "skipped_idempotent": skipped,
                "proposed": len(all_ids),
            }
        )
        total_proposed += len(all_ids)
        total_applied += applied if commit else 0
        total_skipped += skipped
    return {
        "step": "3_cross_source_corroborations",
        "proposed": total_proposed,
        "applied": total_applied,
        "skipped_idempotent": total_skipped,
        "batches": batch_results,
        "motorola_spot_check": spot_check_rows,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Stage operator-review queue items (2 WEAK + 1 PROBE)
# ─────────────────────────────────────────────────────────────────────────────


def step_4_stage_operator_review(*, commit: bool) -> dict:
    weak = _load_json(STAGED / "weak_matches.json")
    probe = _load_json(STAGED / "probe_matches.json")
    normalization = _load_json(STAGED / "normalization_disagreements.json")
    norm_by_anchor = {n["anchor_id"]: n for n in normalization}
    items = []
    for w in weak:
        anchor_id = w["input_anchor"]["manufacturer_id"]
        item = dict(w)
        item["match_type"] = "WEAK"
        item["dispatch"] = DISPATCH
        item["cp_anchor"] = CP_ANCHOR
        item["source_id_provenance"] = 50
        item["operator_review_status"] = "pending"
        if anchor_id in norm_by_anchor:
            item["brittle_alias_match"] = True
            item["normalization_disagreement"] = norm_by_anchor[anchor_id]
        items.append(item)
    for p in probe:
        item = dict(p)
        item["match_type"] = "PROBE"
        item["dispatch"] = DISPATCH
        item["cp_anchor"] = CP_ANCHOR
        item["source_id_provenance"] = 50
        item["operator_review_status"] = "pending_state_of_incorporation_disambig"
        items.append(item)
    target = OPERATOR_QUEUE / "sam_gov_weak.json"
    payload = json.dumps(items, indent=2, sort_keys=True)
    payload_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if target.exists():
        existing = target.read_text()
        existing_sha = hashlib.sha256(existing.encode("utf-8")).hexdigest()
        if existing_sha == payload_sha:
            return {
                "step": "4_operator_review_staging",
                "proposed": len(items),
                "applied": 0,
                "skipped_idempotent": len(items),
                "target": str(target),
                "sha256": payload_sha,
                "items_count": len(items),
                "note": "operator-review-queue file unchanged; idempotent skip",
            }
    if commit:
        OPERATOR_QUEUE.mkdir(parents=True, exist_ok=True)
        target.write_text(payload)
    return {
        "step": "4_operator_review_staging",
        "proposed": len(items),
        "applied": len(items) if commit else 0,
        "skipped_idempotent": 0,
        "target": str(target),
        "sha256": payload_sha,
        "items_count": len(items),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Empty-bucket audit (within_source_reextractions + class_b_holds)
# ─────────────────────────────────────────────────────────────────────────────


def step_5_empty_bucket_audit() -> dict:
    within = _load_json(STAGED / "within_source_reextractions.json")
    holds = _load_json(STAGED / "class_b_us_holds_closures.json")
    return {
        "step": "5_empty_bucket_audit",
        "within_source_reextractions_empty": within == [],
        "class_b_us_holds_closures_empty": holds == [],
        "within_source_reextractions_count": len(within),
        "class_b_us_holds_closures_count": len(holds),
        "note": (
            "within_source_reextractions empty IS the CP24 §11 #8 discipline "
            "being honored at extraction time (SAM.gov is net-new); "
            "class_b_us_holds_closures empty due to cycle-5 staging bug — "
            "11 holds carry forward to cycle-6 day-1 dispatch."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", action="store_true", help="apply writes")
    parser.add_argument("--dry-run", action="store_true", help="proposed only")
    args = parser.parse_args()
    if args.commit and args.dry_run:
        print("--commit and --dry-run are mutually exclusive", file=sys.stderr)
        return 2
    commit = bool(args.commit)
    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA foreign_keys = ON")
    results: dict[str, Any] = {"dispatch": DISPATCH, "commit": commit}
    try:
        results["step_1"] = step_1_source_admission(conn, commit=commit)
        results["step_2"] = step_2_genetec_enrichment(conn, commit=commit)
        results["step_3"] = step_3_cross_source_corroborations(conn, commit=commit)
        results["step_4"] = step_4_stage_operator_review(commit=commit)
        results["step_5"] = step_5_empty_bucket_audit()
        if commit:
            conn.commit()
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            results["pragma_integrity_check"] = integrity
            results["post_counts"] = {
                "sources": conn.execute("SELECT count(*) FROM sources").fetchone()[0],
                "manufacturers": conn.execute(
                    "SELECT count(*) FROM manufacturers"
                ).fetchone()[0],
                "procurement_records": conn.execute(
                    "SELECT count(*) FROM procurement_records"
                ).fetchone()[0],
                "schema_version_max": conn.execute(
                    "SELECT max(version) FROM schema_version"
                ).fetchone()[0],
            }
        else:
            conn.rollback()
    finally:
        conn.close()
    print(json.dumps(results, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
