"""MAC-117 routing execution — round-2 vocab extension (A)/(B)/(C) per SAR-13 §S.3.

CEO-ratified slate at MAC-117 confirmation interaction
`218b091a-b9e5-4d4f-a39b-5923c5f6892f` (accepted 2026-05-14, no amendments).
Routing slate captured in MAC-117 issue document `routing_slate` rev 1
(`877c76b9-ec96-46f9-9a33-717095d260bd`).

Cohort: 107 unpromoted raw_observations rows with
  notes.disposition='pending_validator_retriage_mac107'
  AND notes.hold_reason='id_type_vocab_round2_pending'.

Routing legs:
- (A) 68 rows → identifiers (7 net-new identifier_types added by mig 0019)
- (B) 38 rows → behavioral_signatures (5 detector-internal labels per §S.3)
- (C)  1 row → HOLD with round_2_disposition_class='out_of_scope_v1'
        (already filed in conflicts.id=5 — attribution_conflict)

Confidence: 65 (Wave-A precedent / MAC-110 5f1bf2e floor, §11 #16 facts-only).
source_type for identifiers: 'crowdsourced' (Wave-A precedent).
device_category per source context:
  - src=27 (RemoteIDReceiver — asdstan/DJI Drone-ID broadcast) → 'drone'
  - src=41 (GainSec anti-crime — Flock LPR + Picard/Bravo Compute Box) → 'alpr'
  - src=42 (GainSec flock-safety-falcon-sparrow-alpr-edl-firehose):
     - chipset_codename rows → 'unknown' per mapper notes.rule_11_13
       (`category_unknown_until_validator_pairs_with_product_line`)
     - firmware_build_string / firmware_build_uuid → 'alpr' (Flock-anchored)

manufacturer per source context:
  - asdstan_message_type / asdstan_enum_value (industry-standard ASTM) → NULL
  - dji_protocol_struct_format → 'DJI'
  - gpt_partition_uuid (src=41 Flock Picard/Bravo) → 'Flock Safety'
  - chipset_codename (src=42 generic Qualcomm SoC) → NULL
  - firmware_build_string / firmware_build_uuid (src=42 Flock firmware) → 'Flock Safety'

License posture (per feedback_license_posture_canonical_key.md, sentinel-key
`notes.upstream_license_posture`):
  - src=27 → 'NO_LICENSE_DECLARED' (HSLU thesis repo, no LICENSE file declared)
  - src=41 → 'CC-BY-NC-ND-4.0_with_research_use_clause'
  - src=42 → 'NO_LICENSE_DECLARED_flagged_for_validator'

Idempotency:
- (A) raw_observations.promoted_identifier_id back-link is the marker.
- (B) raw_observations.notes.promoted_to_behavioral_signatures_id (matches
       MAC-110 5f1bf2e precedent marker).
- (C) raw_observations.notes.round_2_disposition_class='out_of_scope_v1'.
- Re-running over the same cohort produces 0 new identifier INSERTs,
  0 new bx_sig INSERTs, 0 note-updates beyond first-run.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = "db/argus.db"
NOW = datetime.now(timezone.utc).isoformat()
DISPATCH_CITE = "MAC-117"
CONFIRMATION_INTERACTION_ID = "218b091a-b9e5-4d4f-a39b-5923c5f6892f"
ROUTING_SLATE_REVISION_ID = "877c76b9-ec96-46f9-9a33-717095d260bd"
WAVE_A_PRECEDENT_CONFIDENCE = 65
WAVE_A_PRECEDENT_SOURCE_TYPE = "crowdsourced"
GEO_SCOPE_DEFAULT = "US"

# (A) candidate_type → identifier_type. 1:1 (mig 0019 added each
# candidate_type verbatim as an identifier_type).
A_CAND_TO_ITYPE = {
    "asdstan_message_type": "asdstan_message_type",
    "asdstan_enum_value": "asdstan_enum_value",
    "dji_protocol_struct_format": "dji_protocol_struct_format",
    "gpt_partition_uuid": "gpt_partition_uuid",
    "chipset_codename": "chipset_codename",
    "firmware_build_string": "firmware_build_string",
    "firmware_build_uuid": "firmware_build_uuid",
}

# (B) candidate_type → bx_sig device_category (per source context).
B_TYPES = {
    "android_package_name",
    "rest_endpoint",
    "cloud_endpoint_fqdn",
    "boot_log_signature",
    "lan_endpoint_url",
}

# (C) candidate_type — HOLD with round_2_disposition_class='out_of_scope_v1'.
C_TYPES = {"attribution_conflict"}

# Per-source license posture sentinel for notes.upstream_license_posture.
UPSTREAM_LICENSE_POSTURE = {
    27: "NO_LICENSE_DECLARED",
    41: "CC-BY-NC-ND-4.0_with_research_use_clause",
    42: "NO_LICENSE_DECLARED_flagged_for_validator",
    40: "AGPL-3.0_declared",
}


def derive_device_category_and_mfr(src: int, cand_type: str) -> tuple[str, str | None]:
    """Return (device_category, manufacturer) per MAC-117 routing slate."""
    if src == 27:
        # ASTM Remote ID + DJI Drone-ID broadcast — drone device class.
        if cand_type == "dji_protocol_struct_format":
            return "drone", "DJI"
        # asdstan_* — industry-standard, multi-vendor ASTM Remote ID protocol.
        return "drone", None
    if src == 41:
        # GainSec anti-crime / Flock LPR + Picard/Bravo Compute Box.
        return "alpr", "Flock Safety"
    if src == 42:
        # Flock Safety falcon/sparrow ALPR EDL firehose firmware.
        if cand_type == "chipset_codename":
            # Generic Qualcomm SoC codename — mapper flagged
            # `generic_chipset_no_product_binding`; §11 #13 carve-out.
            return "unknown", None
        # firmware_build_string / firmware_build_uuid → Flock-anchored.
        return "alpr", "Flock Safety"
    raise ValueError(f"unmapped source {src} for cand_type {cand_type}")


def build_identifier_notes(
    *,
    rid: int,
    src: int,
    cand_type: str,
    raw_notes: dict,
    source_row_key: str | None,
) -> str:
    notes: dict = {
        "promotion_dispatch": DISPATCH_CITE,
        "promotion_phase": "MAC-117_routing_execution_A",
        "promotion_run_at": NOW,
        "raw_observation_id": rid,
        "source_row_key": source_row_key,
        "cohort_label": f"mac117_round2_A_{cand_type}",
        "sar13_routing_cite": "SAR-13 §S.3 (A) — broadcast-class device identifier → identifier_type",
        "mac117_confirmation_interaction_id": CONFIRMATION_INTERACTION_ID,
        "mac117_routing_slate_revision_id": ROUTING_SLATE_REVISION_ID,
        "upstream_license_posture": UPSTREAM_LICENSE_POSTURE.get(src),
        "wave_a_precedent_cite": "MAC-110 5f1bf2e — Wave-A id=1 conf=65 floor",
        "lynceus_export_disposition": "§4.4 mig0019 DROPPED — pending §4.4 MAP ratification at next CP21 round",
    }
    # Preserve per-row mapper context (carry-forward).
    for k in (
        "enum_value", "label", "protocol_version", "partition_name", "device",
        "confidence_hint", "key", "interpretation", "build_timestamp_utc",
        "build_codename", "build_guid", "apk_sha256_unit1", "apk_sha256_unit2",
        "service", "function", "rule_11_13", "generic_chipset_no_product_binding",
    ):
        if k in raw_notes:
            notes[f"mapper_{k}"] = raw_notes[k]
    return json.dumps(notes, sort_keys=False)


def build_bx_sig_notes(rid: int, src: int, cand_type: str, raw_notes: dict) -> str:
    notes: dict = {
        "stage": "mac117_routing_execution_B_bx_sig_backfill",
        "candidate_type": cand_type,
        "raw_observation_id": rid,
        "ratified_at_mac": DISPATCH_CITE,
        "mac117_confirmation_interaction_id": CONFIRMATION_INTERACTION_ID,
        "mac117_routing_slate_revision_id": ROUTING_SLATE_REVISION_ID,
        "sar13_routing_cite": "SAR-13 §S.3 (B) — detector-internal heuristic → behavioral_signatures.signature_name",
        "upstream_license_posture": UPSTREAM_LICENSE_POSTURE.get(src),
        "wave_a_precedent_cite": "MAC-110 5f1bf2e — bx_sig backfill at conf=65",
        "backfilled_at": NOW,
    }
    for k in ("device", "confidence_hint", "service", "function",
              "apk_sha256_unit1", "apk_sha256_unit2"):
        if k in raw_notes:
            notes[f"mapper_{k}"] = raw_notes[k]
    return json.dumps(notes, sort_keys=False)


def build_bx_sig_evidence(
    *,
    rid: int,
    src: int,
    cand_type: str,
    source_excerpt: str | None,
    source_url: str | None,
    source_row_key: str | None,
) -> str:
    return json.dumps(
        {
            "candidate_type": cand_type,
            "source_id": src,
            "raw_observation_id": rid,
            "source_excerpt": source_excerpt,
            "source_url": source_url,
            "source_row_key": source_row_key,
        },
        sort_keys=False,
    )


def run(apply: bool) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """SELECT id, source_id, candidate_type, candidate_identifier, candidate_category,
                  candidate_manufacturer, source_url, source_excerpt, notes, source_row_key,
                  promoted_identifier_id
           FROM raw_observations
           WHERE promoted_identifier_id IS NULL
             AND notes LIKE '%round_2%'
             AND notes LIKE '%id_type_vocab_round2_pending%'
           ORDER BY source_id, id"""
    )

    a_rows: list[tuple] = []
    b_rows: list[tuple] = []
    c_rows: list[tuple] = []
    skipped_already_routed: int = 0
    for row in cur.fetchall():
        rid, sid, ctype = row[0], row[1], row[2]
        notes = json.loads(row[8]) if row[8] else {}
        # Idempotency check — skip rows already routed in a prior apply.
        if any(
            k in notes
            for k in (
                "mac117_promoted_to_identifier_id",
                "mac117_promoted_to_behavioral_signatures_id",
                "round_2_disposition_class",
            )
        ):
            skipped_already_routed += 1
            continue
        if ctype in A_CAND_TO_ITYPE:
            a_rows.append((row, notes))
        elif ctype in B_TYPES:
            b_rows.append((row, notes))
        elif ctype in C_TYPES:
            c_rows.append((row, notes))
        else:
            print(f"WARN unmapped cand_type={ctype} src={sid} rid={rid}", file=sys.stderr)

    print(f"=== MAC-117 routing partition ===")
    print(f"  (A) identifier promotions:    {len(a_rows)}")
    print(f"  (B) bx_sig backfills:         {len(b_rows)}")
    print(f"  (C) HOLD disposition updates: {len(c_rows)}")
    print(f"  (skipped — already routed):   {skipped_already_routed}")
    print(f"  TOTAL:                        {len(a_rows)+len(b_rows)+len(c_rows)}")

    if not apply:
        print("\nDRY RUN — pass --apply to persist.")
        return 0

    cur.execute("BEGIN")
    promoted = 0
    bx_sig_inserted = 0
    hold_updated = 0
    try:
        # ─── (A) identifier promotions ───────────────────────────────────────
        for row, raw_notes in a_rows:
            (rid, sid, ctype, candidate_identifier, _cand_cat, _cand_manu,
             source_url, source_excerpt, _, source_row_key, _) = row
            itype = A_CAND_TO_ITYPE[ctype]
            device_category, manufacturer = derive_device_category_and_mfr(sid, ctype)
            # source_excerpt CHECK ≤200 chars
            trimmed_excerpt = source_excerpt[:200] if source_excerpt else None
            notes_json = build_identifier_notes(
                rid=rid, src=sid, cand_type=ctype, raw_notes=raw_notes,
                source_row_key=source_row_key,
            )
            cur.execute(
                """INSERT INTO identifiers (
                       identifier, identifier_type, device_category, manufacturer, model,
                       confidence, source_url, source_type, source_excerpt,
                       geographic_scope, first_seen, last_verified, notes
                   ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    candidate_identifier, itype, device_category, manufacturer,
                    WAVE_A_PRECEDENT_CONFIDENCE,
                    source_url, WAVE_A_PRECEDENT_SOURCE_TYPE, trimmed_excerpt,
                    GEO_SCOPE_DEFAULT, NOW, NOW, notes_json,
                ),
            )
            new_id = cur.lastrowid
            raw_notes_updated = dict(raw_notes)
            raw_notes_updated["round_2_disposition_class"] = "promoted_to_identifier"
            raw_notes_updated["mac117_promoted_to_identifier_id"] = new_id
            raw_notes_updated["mac117_routed_at"] = NOW
            cur.execute(
                """UPDATE raw_observations
                   SET notes=?, processed_at=?, promoted_identifier_id=?
                   WHERE id=?""",
                (json.dumps(raw_notes_updated), NOW, new_id, rid),
            )
            promoted += 1

        # ─── (B) bx_sig backfills ────────────────────────────────────────────
        for row, raw_notes in b_rows:
            (rid, sid, ctype, candidate_identifier, _cand_cat, _cand_manu,
             source_url, source_excerpt, _, source_row_key, _) = row
            # device_category per (B) source: src=41 → 'alpr' (Flock LPR ecosystem).
            device_category = "alpr" if sid == 41 else "unknown"
            bx_notes_json = build_bx_sig_notes(rid, sid, ctype, raw_notes)
            bx_evidence_json = build_bx_sig_evidence(
                rid=rid, src=sid, cand_type=ctype,
                source_excerpt=source_excerpt, source_url=source_url,
                source_row_key=source_row_key,
            )
            cur.execute(
                """INSERT INTO behavioral_signatures (
                       signature_name, cellular_generation, threshold_json,
                       evidence_json, source_id, source_file_relative, source_line,
                       confidence, device_category, notes, created_at, updated_at
                   ) VALUES (?, NULL, NULL, ?, ?, NULL, NULL, ?, ?, ?, ?, ?)""",
                (
                    candidate_identifier, bx_evidence_json, sid,
                    WAVE_A_PRECEDENT_CONFIDENCE, device_category,
                    bx_notes_json, NOW, NOW,
                ),
            )
            new_bx_id = cur.lastrowid
            raw_notes_updated = dict(raw_notes)
            raw_notes_updated["round_2_disposition_class"] = "routed_to_behavioral_signatures"
            raw_notes_updated["mac117_promoted_to_behavioral_signatures_id"] = new_bx_id
            raw_notes_updated["mac117_routed_at"] = NOW
            # promoted_identifier_id stays NULL per SAR-13 §S.3 routing.
            cur.execute(
                """UPDATE raw_observations
                   SET notes=?, processed_at=?
                   WHERE id=?""",
                (json.dumps(raw_notes_updated), NOW, rid),
            )
            bx_sig_inserted += 1

        # ─── (C) HOLD disposition updates ────────────────────────────────────
        for row, raw_notes in c_rows:
            rid = row[0]
            raw_notes_updated = dict(raw_notes)
            raw_notes_updated["round_2_disposition_class"] = "out_of_scope_v1"
            raw_notes_updated["mac117_hold_rationale"] = (
                "attribution_conflict — already filed in conflicts.id=5 "
                "(Motorola/Vigilant single-profile merge); not a vocab "
                "candidate per MAC-117 §1 (C) routing. Preserved here for "
                "forensic traceability per bible §4.4."
            )
            raw_notes_updated["mac117_routed_at"] = NOW
            cur.execute(
                """UPDATE raw_observations
                   SET notes=?, processed_at=?
                   WHERE id=?""",
                (json.dumps(raw_notes_updated), NOW, rid),
            )
            hold_updated += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    print(f"\n=== Applied ===")
    print(f"  (A) identifiers inserted:    {promoted}")
    print(f"  (B) bx_sig inserted:         {bx_sig_inserted}")
    print(f"  (C) HOLD updates:            {hold_updated}")
    return 0


def main() -> int:
    apply = "--apply" in sys.argv
    return run(apply)


if __name__ == "__main__":
    raise SystemExit(main())
