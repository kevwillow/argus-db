"""
Phase 7 §7.0 — api.dbeta.me wave_i_aggregate staging + promotion.

Folded from MAC-192 CEO ratification (item 1). Staging pattern mirrors 4
sibling DJI dbeta.me hosts (ids 27658/27890/27898/27931 promoted at
conf=85 via source_id=66 wave_i_aggregate).

Single-transaction:
  1. INSERT raw_observations (source_id=66, source_url=wave_i_aggregate://...).
  2. INSERT identifiers (vendor_controlled_hostname, manufacturer=dji, conf=85).
  3. UPDATE raw_observations.promoted_identifier_id.

Dispatch ref: MAC-194 §7.0 (CEO ratification on MAC-192).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path("/home/kev/argus/db/argus.db")
LOG_PATH = Path("/home/kev/argus/_phase_7_fccid_attestations/api_dbeta_me_staging_log.md")

IDENTIFIER = "api.dbeta.me"
SOURCE_ID_WAVE_I_AGGREGATE = 66  # verified
SOURCE_URL = "wave_i_aggregate://wave_i_main/A/api.dbeta.me"
SOURCE_ROW_KEY = "wave_i_v1.4.1:wave_i_main:A:api.dbeta.me"

# Identifiers.source_excerpt is CHECK <=200 chars. Trim verbatim plan-input
# prose to fit. Plan source: wave_i_14a RECONCILIATION_PLAN_V3 net-new
# promotion proposal #0 (Wave I.13 carry-forward).
IDENT_SOURCE_EXCERPT = (
    "api.dbeta.me — DJI debug-mode API endpoint in dji.go.v5.apk "
    "assets/api_debug.txt; DJI uses .dbeta.me as alt vendor-controlled "
    "domain alongside .dji.com (Wave I.13 carry-forward, MAC-192 ratified)"
)
assert len(IDENT_SOURCE_EXCERPT) <= 200, f"excerpt {len(IDENT_SOURCE_EXCERPT)}>200"

RAW_OBS_NOTES = {
    "wave": "wave_i_main",
    "source_class": "A",
    "value_class": "vendor_controlled_hostname",
    "value_class_alternates": [],
    "upstream_license_posture": "VENDOR_BINARY_FACTS_ONLY",
    "bucket_origin": None,
    "carry_forward_from": "wave_i_13",
    "ratification_ref": "MAC-192 CEO ratification item 1 → MAC-194 §7.0",
    "plan_input_evidence_verbatim": (
        "Debug/demo endpoint baked into DJI desktop installers "
        "(api.dbeta.me / fmdemo.aasky.net / account.dbeta.me). "
        "DJI uses .dbeta.me and .aasky.net as alternate vendor-controlled "
        "domains alongside primary .dji.com."
    ),
}

IDENT_NOTES = {
    "session_admission": "wave_i_pre_v1_carry_forward",
    "wave": "wave_i_v1_4_1_phase_7_fold",
    "cp29_value_class": "vendor_controlled_hostname",
    "cp29_confidence_band": "default",
    "cp29_band_rationale": "vendor_controlled_hostname: default (single source)",
    "§8.3_lift_applied": False,
    "source_classes_observed": ["A"],
    "attestation_count": 1,
    "upstream_license_posture": "VENDOR_BINARY_FACTS_ONLY",
    "bucket_origin": None,
    "value_class_alternates": [],
    "carry_forward_from": "wave_i_13",
    "ratification_ref": "MAC-192 CEO ratification item 1 → MAC-194 §7.0",
}


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("SELECT id FROM identifiers WHERE identifier=? AND identifier_type='vendor_controlled_hostname'", (IDENTIFIER,))
    existing = cur.fetchone()
    if existing:
        msg = f"HALT-IDEMPOTENT: api.dbeta.me already promoted as id={existing[0]}"
        print(msg)
        LOG_PATH.write_text(msg + "\n", encoding="utf-8")
        return

    cur.execute("SELECT id FROM raw_observations WHERE source_url=?", (SOURCE_URL,))
    existing_obs = cur.fetchone()
    if existing_obs:
        msg = f"HALT-IDEMPOTENT: raw_observations source_url already present: id={existing_obs[0]}"
        print(msg)
        LOG_PATH.write_text(msg + "\n", encoding="utf-8")
        return

    try:
        cur.execute("BEGIN")

        cur.execute(
            """
            INSERT INTO raw_observations
              (source_id, source_url, candidate_identifier, candidate_type,
               candidate_category, candidate_manufacturer, source_excerpt,
               notes, source_row_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SOURCE_ID_WAVE_I_AGGREGATE,
                SOURCE_URL,
                IDENTIFIER,
                "vendor_controlled_hostname",
                "unknown",
                "dji",
                RAW_OBS_NOTES["plan_input_evidence_verbatim"],
                json.dumps(RAW_OBS_NOTES),
                SOURCE_ROW_KEY,
            ),
        )
        raw_obs_id = cur.lastrowid

        cur.execute(
            """
            INSERT INTO identifiers
              (identifier, identifier_type, device_category, manufacturer,
               confidence, source_url, source_type, source_excerpt,
               first_seen, last_verified, notes)
            VALUES
              (?, 'vendor_controlled_hostname', 'unknown', 'dji', 85,
               ?, 'manufacturer_app', ?,
               datetime('now'), datetime('now'), ?)
            """,
            (
                IDENTIFIER,
                SOURCE_URL,
                IDENT_SOURCE_EXCERPT,
                json.dumps(IDENT_NOTES),
            ),
        )
        ident_id = cur.lastrowid

        cur.execute(
            "UPDATE raw_observations SET promoted_identifier_id=?, processed_at=datetime('now') WHERE id=?",
            (ident_id, raw_obs_id),
        )

        cur.execute("COMMIT")
    except sqlite3.Error as exc:
        cur.execute("ROLLBACK")
        raise SystemExit(f"§7.0 transaction failed: {exc}")

    log_lines = [
        "# Phase 7 §7.0 — api.dbeta.me staging + promotion log",
        "",
        "**Dispatch ref:** MAC-194 §7.0 (folded from MAC-192 CEO ratification item 1)",
        "**Predecessor halt:** Phase 6 strict-§11 #1 hold (per `_phase_6_wave_i_14a/preflight_pragma.md` §Halt-surface).",
        "**Pattern:** wave_i_aggregate (mirrors 4 sibling DJI dbeta.me hosts ids 27658 / 27890 / 27898 / 27931).",
        "",
        "## Result",
        "",
        f"- raw_observations.id = {raw_obs_id}",
        f"- identifiers.id      = {ident_id}",
        f"- identifier          = {IDENTIFIER}",
        "- identifier_type     = vendor_controlled_hostname",
        "- manufacturer        = dji",
        "- device_category     = unknown",
        "- confidence          = 85 (single-source default; cp29 vendor_controlled_hostname band)",
        f"- source_id           = {SOURCE_ID_WAVE_I_AGGREGATE} (Wave I — Vendor Cloud-Infrastructure Hostname Corpus Extraction)",
        "- source_type         = manufacturer_app",
        f"- source_url          = {SOURCE_URL}",
        f"- source_row_key      = {SOURCE_ROW_KEY}",
        "",
        "## Provenance",
        "",
        "Plan-input evidence verbatim (Wave I.13 / wave_i_14a `RECONCILIATION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json` §wave_i_13_dji_hikvision_endpoints.net_new_promotion_proposals[0]):",
        "",
        "> " + RAW_OBS_NOTES["plan_input_evidence_verbatim"],
        "",
        "## §11 discipline",
        "",
        "- §11 #1 (no fabrication) — plan-input evidence verbatim attached; source_url anchored in wave_i_aggregate canonical.",
        "- §11 #7 (provenance) — raw_observations.id chained to identifiers.id via promoted_identifier_id.",
        "- §11 #8 (no confidence drift) — confidence=85 per cp29 vendor_controlled_hostname default band; single source; no §8.3 lift applied.",
        "",
    ]
    LOG_PATH.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"§7.0 OK: raw_obs={raw_obs_id} ident={ident_id} log={LOG_PATH}")


if __name__ == "__main__":
    main()
