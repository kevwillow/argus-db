"""MAC-110 — MAC-104 close-out (Stage 1 Q3/Q4/Q5/Q7 + Stage 2 re-triage).

Two stages — single defensive backup + idempotent per stage.

Stage 1 (Q3+Q4+Q5+Q7, ~24 row-ops):
  - Q3: supersede prior-lens MAC-107 promotions id=22749..22751 (src=38 MACs)
        with new rows under MAC-104-ratified product-vendor lens
        (mfr='Flock Safety', dc='alpr', conf=65). Preserves IEEE-registry
        attribution (Liteon) in notes.oui_registry_assignee.
  - Q4: supersede prior-lens MAC-107 promotions id=22752..22769 (src=39 OUIs,
        ex e4:aa:ea which goes to Q5 leg 2) under §11 #16 facts-only +
        product-vendor lens (mfr='Flock Safety', dc='alpr', conf=65).
        Excerpt: Argus-authored minimal per §1 #6 NO_LICENSE_DECLARED trim
        + §11 #16 Feist arrangement-not-copied discipline.
  - Q5 leg 1: §8.3 corroboration uplift on id=1 (conf 65→70). CP19 audit
        entry MANDATORY in source_reclassifications in the same transaction.
  - Q5 leg 2: supersede id=22770 (e4:aa:ea OUI) with new OUI under ratified
        lens at conf=70 (corroborated by src=38 + src=39 + id=1 per §8.3
        formula min(99, max(65)+5)).
  - Q7: INSERT conflicts row for raw_id=242677 (src=40 Motorola/Vigilant
        attribution); update raw_observations.notes.hold_reason to
        'filed_to_conflicts_pending_ma_verification'.

Stage 2 (post-MAC-108 / MAC-109 re-triage):
  - 198 mapper-corrected rows (src=27 + 41 + 42 + 43 + 40-other) — re-triage
    cascade. Promote candidate_types matching CHECK enum (post-0018);
    HOLD un-CHECK-mapped types with hold_reason='id_type_vocab_round2_pending';
    file CVE-FP rows to conflicts per SAR-7 #1; apply §4.3 normalization
    (mac_oui→oui, ssid→ssid_exact, rf_bandwidth→bandwidth_mhz).
  - 69 vocab-cleared rows (post-MAC-109 migration 0018) — promote.
    NOTE: dispatch estimated 85; actual 69 after subtracting 38 bx_sig-routed
    (per SAR-13 §S.3) from the 107-row identifier_type_vocab_extension_pending
    pool. Reported as architectural delta in §E.
  - 38 detector-internal rows (src=31 wireshark_field; src=32 tunable_threshold
    + threat_level_enum + logcat_detection_string + oem_service_mode_command +
    modem_device_path) — backfill into behavioral_signatures per SAR-13 §S.3.

Idempotency: re-running produces zero new identifiers/conflicts/bx_sig rows.
Markers used:
  - identifiers.notes.mac110_supersedes_identifier_id (supersedure idempotency)
  - identifiers.notes.mac110_promotion_idempotency_key (mapper-corrected pool)
  - behavioral_signatures.notes.mac110_promotion_idempotency_key
  - source_reclassifications.sweep_event_id (CP19 audit idempotency)
  - conflicts.reason 'attribution_history_pending_ma_verification' on
    raw_observation_id=242677
  - raw_observations.promoted_identifier_id (existing canonical marker)

Bible citations:
  §7.4 Validator scope
  §4.3 normalization rules
  §8.3 multi-source corroboration formula
  §8.4 dual-lens attribution / hardware-anchor sub-rule
  §11 #1 no fabrication
  §11 #7 provenance is the database
  §11 #8 no confidence drift / CP19 audit sub-rule
  §11 #16 Feist facts-only promotion (NO_LICENSE_DECLARED)
  CP4 §4.3 Wave-A first-row precedent
  CP19 source_reclassifications audit discipline
  CP20 + SAR-13 §S.3 detector-internal bx_sig routing
  SAR-7 #1 CVE-FP allowlist
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = "db/argus.db"

NOW = datetime.now(timezone.utc).isoformat()
DISPATCH_CITE = "MAC-110"
RATIFIED_AT_MAC = "MAC-104"
# MAC-711: the `RATIFIED_AT_COMMIT = "8de7309"` constant was dropped here, along with the
# `+ bible commit {RATIFIED_AT_COMMIT}` clause of RECLASS_ANCHOR below and all nine payload
# keys that carried it (`ratified_at_commit` ×8, `bible_commit` ×1). That sha was minted
# before the pre-v1.0.0 history rewrite and no longer resolves.
#
# The RECLASS_ANCHOR clause was the costliest of the ten: it rendered to the bare-prose
# form `bible <the-word-commit> <the-sha>`, the one shape in this file that the MAC-704
# gate selector actually matches — so a re-run would have written a cite that reads as
# live to the gate and resolves to nothing. (Spelled around here on purpose: quoting
# those bytes verbatim would re-mint the very cite this edit removes, and the gate reads
# this file. The dropped value is on the constant line above, which the selector cannot
# see.) The durable anchors all survive:
# RATIFIED_AT_MAC (MAC-104), the CP20 + SAR-13 amendment numbers, DISPATCH_CITE (MAC-110),
# and the board comment id. See BIBLE_AMENDMENTS.md *Citing a commit in this ledger*.
#
# `3daf49f0` is retained deliberately: it is a Paperclip board comment id, not a git object,
# so the history rewrite never touched it and the sha-cite rule does not reach it.
RECLASS_ANCHOR = f"{RATIFIED_AT_MAC} CEO ratification comment 3daf49f0 (CP20 + SAR-13)"
SWEEP_EVENT_Q5 = "mac110_q5_eaaaea_uplift"
SWEEP_EVENT_STAGE1 = "mac110_stage1_supersede"

CONF_FLOOR = 65  # Wave-A id=1 precedent floor
CONF_Q5_UPLIFT = 70  # §8.3 min(99, max(65)+5)

GEO_SCOPE_DEFAULT = "US"

VALID_DEVICE_CATEGORIES = {
    "alpr", "imsi_catcher", "body_cam", "police_radio",
    "drone", "gunshot_detect", "hacking_tool",
    "covert_cam", "gps_tracker", "face_recog",
    "drone_detect", "unknown",
}

# CHECK enum from db/migrations/0018 — must match the schema CHECK constraint
# verbatim. Any candidate_type not in this set is HELD for round-2 vocab
# extension (CEO-class question) and surfaced in §E.
VALID_IDENTIFIER_TYPES = {
    "oui", "mac", "mac_range", "bssid",
    "ssid_exact", "ssid_pattern",
    "ble_uuid", "ble_service",
    "device_fingerprint",
    "ble_local_name", "ble_characteristic",
    "product_family_codename",
    "ble_manufacturer_id",
    "drone_id_prefix", "icao_24bit_address",
    "rf_channel", "burst_cadence_ms", "bandwidth_mhz",
    "device_class_id", "rf_burst_duration", "rf_protocol_constant",
    "wifi_aware_service_name", "wifi_ie_element_id",
    "bluetooth_le_pdu_type", "wifi_frame_control_subtype",
    "wifi_nan_param_signature", "alpr_model",
    "ble_protocol_byte_table", "ble_service_uuid", "ble_company_id",
    "frequency_band", "ble_protocol_byte", "operator_profile",
    "x509_cert_sha256_prefix", "ble_adv_interval", "ble_payload_offset",
    "firmware_sha256_hash", "network_endpoint",
    "firmware_image_variant", "qualcomm_chip_format_id",
    "firmware_branded_string",
}

# §4.3 normalization — candidate_type → identifier_type
CANDIDATE_TYPE_NORMALIZE = {
    "mac_oui": "oui",
    "mac": "mac",
    "ssid": "ssid_exact",
    "rf_bandwidth": "bandwidth_mhz",
}

# SAR-7 #1 — CVE-FP allowlist patterns
CVE_FP_RE = re.compile(r"^CVE-\d{4}(-\d{4,7})?$", re.I)
CWE_FP_RE = re.compile(r"^CWE-\d{1,4}$", re.I)

# §7.3 known-fake (subset re-checked at validation time)
KNOWN_FAKE_OUIS_LITERAL = {
    "aa:bb:cc", "00:11:22", "12:34:56", "de:ad:be",
    "ca:fe:ba", "ba:db:00", "00:00:00", "ff:ff:ff",
    # all-identical-octet sentinel (caught by predicate too)
}


def is_known_fake_oui(value: str) -> bool:
    v = value.lower().strip()
    if v in KNOWN_FAKE_OUIS_LITERAL:
        return True
    octs = v.split(":")
    if len(octs) == 3 and len(set(octs)) == 1:
        return True
    return False


def normalize_mac(raw: str) -> str:
    return raw.lower().strip()


def normalize_oui(raw: str) -> str:
    v = raw.lower().strip()
    parts = v.split(":")
    if len(parts) == 6:
        return ":".join(parts[:3])
    return v


def normalize_identifier(itype: str, value: str) -> str:
    if itype in ("mac", "bssid"):
        return normalize_mac(value)
    if itype == "oui":
        return normalize_oui(value)
    if itype.startswith("ble_") and "uuid" in itype:
        return value.lower().strip()
    return value


def trim_excerpt_minimal(raw_excerpt: str | None, max_len: int = 80) -> str | None:
    """§11 #16 minimal-factual excerpt (Argus-authored vibe, not list-copy)."""
    if raw_excerpt is None:
        return None
    s = raw_excerpt.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def cur_notes(notes_raw: str | None) -> dict:
    if not notes_raw:
        return {}
    try:
        return json.loads(notes_raw)
    except Exception:
        return {"_parse_error": True, "_raw": notes_raw[:200]}


def write_back_notes(cur, raw_id: int, new_notes: dict) -> None:
    cur.execute(
        "UPDATE raw_observations SET notes=? WHERE id=?",
        (json.dumps(new_notes, separators=(",", ":")), raw_id),
    )


# ---------------------------------------------------------------------------
# Stage 1 — Q3 + Q4 + Q5 + Q7
# ---------------------------------------------------------------------------

def execute_stage1(cur) -> dict:
    """Stage 1 — single transaction (caller wraps BEGIN/COMMIT)."""
    out = {"q3": [], "q4": [], "q5": [], "q7": []}

    # ---------- Q3 — src=38 MACs (3) ----------
    cur.execute(
        """SELECT id, candidate_identifier, source_url, source_excerpt, promoted_identifier_id, notes
           FROM raw_observations WHERE source_id=38 ORDER BY id"""
    )
    src38_rows = cur.fetchall()
    for raw_id, cand, url, exc, old_pid, raw_notes_raw in src38_rows:
        # Idempotency: skip if raw_observations row already marked as repointed
        # to a MAC-110 ratified-lens identifier (stable per-row marker)
        rn_pre = cur_notes(raw_notes_raw)
        if rn_pre.get("mac110_repointed_to_identifier_id"):
            out["q3"].append({"raw_id": raw_id, "new_id": rn_pre["mac110_repointed_to_identifier_id"], "skipped": "idempotent"})
            continue
        # Capture the ORIGINAL MAC-107 promotion id for supersedure (the
        # current promoted_identifier_id is the MAC-107 lens row).
        original_mac107_id = old_pid

        new_identifier = normalize_mac(cand)
        new_notes = {
            "oui_registry_assignee": "Liteon Technology Corporation",
            "attribution_lens": "product-vendor",
            "ratified_at_mac": RATIFIED_AT_MAC,
            "mac110_supersedes_identifier_id": original_mac107_id,
            "supersedes_reason": (
                "prior-lens MAC-107 promotion at mfr='Liteon Technology Corporation' "
                "dc='alpr' under IEEE-registry attribution; MAC-104 ratification "
                "reclassifies to product-vendor lens (Flock Safety + dc='alpr') "
                "per Wave-A id=1 precedent (CP4 §4.3 + §8.4 dual-lens)."
            ),
            "raw_observation_id": raw_id,
            "wave": "A_deferred_dir",
            "stage": "mac110_stage1_q3",
        }
        cur.execute(
            """INSERT INTO identifiers
                 (identifier, identifier_type, device_category, manufacturer, model,
                  confidence, source_url, source_type, source_excerpt, geographic_scope,
                  first_seen, last_verified, notes)
               VALUES (?, 'mac', 'alpr', 'Flock Safety', 'unknown',
                       ?, ?, 'crowdsourced', ?, ?,
                       ?, ?, ?)""",
            (
                new_identifier, CONF_FLOOR, url, (exc or "")[:200], GEO_SCOPE_DEFAULT,
                NOW, NOW, json.dumps(new_notes, separators=(",", ":")),
            ),
        )
        new_id = cur.lastrowid
        # Supersede the original MAC-107 lens row
        cur.execute(
            "UPDATE identifiers SET superseded_by=? WHERE id=?",
            (new_id, original_mac107_id),
        )
        # Repoint raw_observations + clear hold_reason
        rn = rn_pre
        rn.pop("hold_reason", None)
        rn["mac110_supersede_old_promotion_id"] = original_mac107_id
        rn["mac110_repointed_to_identifier_id"] = new_id
        rn["mac110_repointed_at"] = NOW
        cur.execute(
            "UPDATE raw_observations SET promoted_identifier_id=?, notes=? WHERE id=?",
            (new_id, json.dumps(rn, separators=(",", ":")), raw_id),
        )
        out["q3"].append({"raw_id": raw_id, "new_id": new_id, "old_id": original_mac107_id, "value": new_identifier})

    # ---------- Q4 — src=39 OUIs (18, ex raw_id=242662 which goes to Q5) ----------
    cur.execute(
        """SELECT id, candidate_identifier, source_url, source_excerpt, promoted_identifier_id, notes
           FROM raw_observations WHERE source_id=39 ORDER BY id"""
    )
    src39_rows = cur.fetchall()
    for raw_id, cand, url, exc, old_pid, raw_notes_raw in src39_rows:
        if raw_id == 242644:
            continue  # already filed to conflicts id=4 (cc:cc:cc §7.3 reject)
        if raw_id == 242662:
            continue  # handled in Q5 leg 2 (e4:aa:ea corroboration uplift)
        if old_pid is None:
            continue  # unexpected; skip

        # Idempotency: skip if raw_observations row already repointed
        rn_pre = cur_notes(raw_notes_raw)
        if rn_pre.get("mac110_repointed_to_identifier_id"):
            out["q4"].append({"raw_id": raw_id, "new_id": rn_pre["mac110_repointed_to_identifier_id"], "skipped": "idempotent"})
            continue
        original_mac107_id = old_pid

        new_identifier = normalize_oui(cand)
        # Argus-authored minimal excerpt per §1 #6 + §11 #16 (NOT a list-copy)
        minimal_excerpt = (
            f"OUI {new_identifier} — Flock-context active-prefix list entry "
            f"(NO_LICENSE_DECLARED upstream; Feist facts-only promotion per §11 #16)."
        )[:200]
        new_notes = {
            "upstream_license_posture": "NO_LICENSE_DECLARED",
            "license_posture_excerpt_trim_applied": True,
            "attribution_lens": "product-vendor",
            "device_category_rationale": (
                "Flock-context observation source (EthanThePhoenix38/flock-you-camera-detector "
                "active_mac_prefixes_array) — operational-context lens places this OUI in the "
                "Flock Safety ALPR ecosystem per Wave-A id=1 precedent (CP4 §4.3 + §8.4)."
            ),
            "ratified_at_mac": RATIFIED_AT_MAC,
            "mac110_supersedes_identifier_id": original_mac107_id,
            "supersedes_reason": (
                "prior-lens MAC-107 promotion at mfr=NULL dc='unknown' (§8.4 OUI-level "
                "multi-purpose-vendor default); MAC-104 ratification reclassifies to "
                "product-vendor lens Flock Safety + dc='alpr' per §11 #16 facts-only "
                "+ Wave-A id=1 precedent."
            ),
            "raw_observation_id": raw_id,
            "wave": "A_deferred_dir",
            "stage": "mac110_stage1_q4",
        }
        cur.execute(
            """INSERT INTO identifiers
                 (identifier, identifier_type, device_category, manufacturer, model,
                  confidence, source_url, source_type, source_excerpt, geographic_scope,
                  first_seen, last_verified, notes)
               VALUES (?, 'oui', 'alpr', 'Flock Safety', NULL,
                       ?, ?, 'crowdsourced', ?, ?,
                       ?, ?, ?)""",
            (
                new_identifier, CONF_FLOOR, url, minimal_excerpt, GEO_SCOPE_DEFAULT,
                NOW, NOW, json.dumps(new_notes, separators=(",", ":")),
            ),
        )
        new_id = cur.lastrowid
        cur.execute(
            "UPDATE identifiers SET superseded_by=? WHERE id=?",
            (new_id, original_mac107_id),
        )
        rn = rn_pre
        rn.pop("hold_reason", None)
        rn["mac110_supersede_old_promotion_id"] = original_mac107_id
        rn["mac110_repointed_to_identifier_id"] = new_id
        rn["mac110_repointed_at"] = NOW
        cur.execute(
            "UPDATE raw_observations SET promoted_identifier_id=?, notes=? WHERE id=?",
            (new_id, json.dumps(rn, separators=(",", ":")), raw_id),
        )
        out["q4"].append({"raw_id": raw_id, "new_id": new_id, "old_id": original_mac107_id, "value": new_identifier})

    # ---------- Q5 leg 1 — id=1 uplift 65→70 + CP19 audit ----------
    cur.execute(
        "SELECT source_url, source_type, confidence, notes FROM identifiers WHERE id=1"
    )
    id1_row = cur.fetchone()
    if id1_row is None:
        raise RuntimeError("identifiers.id=1 missing — Wave-A precedent row not found")
    pre_url, pre_st, pre_conf, pre_notes_raw = id1_row

    # Idempotency: skip if audit entry already exists for this sweep_event
    cur.execute(
        "SELECT id FROM source_reclassifications WHERE sweep_event_id=?",
        (SWEEP_EVENT_Q5,),
    )
    if cur.fetchone():
        out["q5"].append({"leg": 1, "skipped": "idempotent_audit_present"})
    else:
        if pre_conf != CONF_FLOOR:
            raise RuntimeError(
                f"Q5 precondition: id=1 expected conf={CONF_FLOOR}, found {pre_conf}"
            )
        id1_notes = cur_notes(pre_notes_raw)
        id1_notes.setdefault("audit", {})
        id1_notes["mac110_q5_uplift"] = {
            "pre_confidence": pre_conf,
            "post_confidence": CONF_Q5_UPLIFT,
            "formula": "§8.3 min(99, max(65)+5)",
            "corroborating_sources": [
                "raw_observations.src=38 (DeflockJoplin/flock-you cumulative_detections.pkl)",
                "raw_observations.src=39 (EthanThePhoenix38/flock-you-camera-detector main.cpp)",
                "MAC-104 ratified — CEO comment 3daf49f0",
            ],
            "last_verified_at_uplift": NOW,
            "ratified_at_mac": RATIFIED_AT_MAC,
        }
        cur.execute(
            "UPDATE identifiers SET confidence=?, last_verified=?, notes=? WHERE id=1",
            (CONF_Q5_UPLIFT, NOW, json.dumps(id1_notes, separators=(",", ":"))),
        )
        cur.execute(
            """INSERT INTO source_reclassifications
                 (identifier_id, sweep_event_id,
                  pre_source_url, post_source_url,
                  pre_source_type, post_source_type,
                  pre_confidence, post_confidence,
                  reclassification_reason, reclassification_anchor,
                  reclassified_at, notes)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                SWEEP_EVENT_Q5,
                pre_url, pre_url,  # source_url unchanged
                pre_st, pre_st,    # source_type unchanged (crowdsourced)
                pre_conf, CONF_Q5_UPLIFT,
                (
                    "§8.3 corroboration uplift from src=38 (DeflockJoplin/flock-you "
                    "cumulative_detections.pkl, OUI E4:AA:EA observed 11 hits in 53s) "
                    "+ src=39 (EthanThePhoenix38/flock-you-camera-detector main.cpp "
                    "active_mac_prefixes_array entry e4:aa:ea) multi-source "
                    "Flock-context observation per MAC-104 Q5 CEO ratification at "
                    "comment 3daf49f0. Formula: min(99, max(65)+5) = 70."
                ),
                RECLASS_ANCHOR,
                NOW,
                json.dumps({
                    "stage": "mac110_stage1_q5_leg1",
                    "dispatch_anchor": DISPATCH_CITE,
                }, separators=(",", ":")),
            ),
        )
        out["q5"].append({"leg": 1, "pre_conf": pre_conf, "post_conf": CONF_Q5_UPLIFT})

    # ---------- Q5 leg 2 — supersede id=22770 with new e4:aa:ea OUI at conf=70 ----------
    cur.execute(
        "SELECT id, source_url, source_excerpt, notes FROM raw_observations WHERE id=242662"
    )
    r2 = cur.fetchone()
    raw_id, url, exc, raw_notes_raw = r2
    rn_pre = cur_notes(raw_notes_raw)
    if rn_pre.get("mac110_repointed_to_identifier_id"):
        out["q5"].append({"leg": 2, "new_id": rn_pre["mac110_repointed_to_identifier_id"], "skipped": "idempotent"})
    else:
        minimal_excerpt = (
            "OUI e4:aa:ea — Flock Safety product-vendor lens; corroborated by src=38 "
            "(cumulative_detections.pkl) + src=39 (active_mac_prefixes_array)."
        )[:200]
        new_notes = {
            "upstream_license_posture": "NO_LICENSE_DECLARED",
            "license_posture_excerpt_trim_applied": True,
            "attribution_lens": "product-vendor",
            "corroborating_sources": [
                "raw_observations.src=38",
                "raw_observations.src=39",
                "identifiers.id=1 (e4:aa:ea:80:a1:9b MAC, Wave-A precedent)",
            ],
            "corroboration_formula": "§8.3 min(99, max(65)+5) = 70",
            "cross_validation_pending_wigle_anchors": True,
            "ratified_at_mac": RATIFIED_AT_MAC,
            "mac110_supersedes_identifier_id": 22770,
            "supersedes_reason": (
                "prior-lens MAC-107 promotion at mfr=NULL dc='unknown' conf=65; "
                "MAC-104 Q5 ratification reclassifies to product-vendor lens "
                "(Flock Safety + dc='alpr') + corroboration-uplift to conf=70 "
                "per §8.3."
            ),
            "raw_observation_id": raw_id,
            "wave": "A_deferred_dir",
            "stage": "mac110_stage1_q5_leg2",
        }
        cur.execute(
            """INSERT INTO identifiers
                 (identifier, identifier_type, device_category, manufacturer, model,
                  confidence, source_url, source_type, source_excerpt, geographic_scope,
                  first_seen, last_verified, notes)
               VALUES ('e4:aa:ea', 'oui', 'alpr', 'Flock Safety', NULL,
                       ?, ?, 'crowdsourced', ?, ?,
                       ?, ?, ?)""",
            (
                CONF_Q5_UPLIFT, url, minimal_excerpt, GEO_SCOPE_DEFAULT,
                NOW, NOW, json.dumps(new_notes, separators=(",", ":")),
            ),
        )
        new_id = cur.lastrowid
        cur.execute("UPDATE identifiers SET superseded_by=? WHERE id=22770", (new_id,))
        rn = rn_pre
        rn.pop("hold_reason", None)
        rn["mac110_supersede_old_promotion_id"] = 22770
        rn["mac110_repointed_to_identifier_id"] = new_id
        rn["mac110_repointed_at"] = NOW
        cur.execute(
            "UPDATE raw_observations SET promoted_identifier_id=?, notes=? WHERE id=242662",
            (new_id, json.dumps(rn, separators=(",", ":"))),
        )
        out["q5"].append({"leg": 2, "new_id": new_id, "old_id": 22770})

    # ---------- Q7 — src=40 raw_id=242677 attribution conflict file ----------
    cur.execute(
        "SELECT id FROM conflicts WHERE raw_observation_id=242677 AND reason=?",
        ("attribution_history_pending_ma_verification",),
    )
    existing_conflict = cur.fetchone()
    if existing_conflict:
        out["q7"].append({"raw_id": 242677, "conflict_id": existing_conflict[0], "skipped": "idempotent"})
    else:
        cur.execute(
            "SELECT source_url, source_excerpt, notes FROM raw_observations WHERE id=242677"
        )
        r7 = cur.fetchone()
        url, exc, raw_notes_raw = r7
        rn = cur_notes(raw_notes_raw)
        deflock_app_position = rn.get("deflock_app_position", "(missing)")
        argus_position = rn.get("argus_position", "(missing)")
        resolution_notes = json.dumps({
            "disposition": "MAC-104 Q7 disposition (a)+(c) hybrid — file to conflicts + defer to standing M&A verification pass",
            "claim_verbatim": {
                "deflock_app_position": deflock_app_position,
                "argus_position": argus_position,
            },
            "memory_cite": "feedback_agent_asserted_history_needs_verification.md",
            "ratified_at_mac": RATIFIED_AT_MAC,
            "stage": "mac110_stage1_q7",
            "next_action": "standing M&A verification pass — verify Motorola-Vigilant 2019 acquisition timing vs pre-2019 attribution discipline (§8.4 audit-fidelity).",
        }, separators=(",", ":"))
        cur.execute(
            """INSERT INTO conflicts
                 (identifier_a_id, identifier_b_id, raw_observation_id,
                  reason, detected_at, resolved_at, resolved_by, resolution_notes)
               VALUES (NULL, NULL, 242677,
                       'attribution_history_pending_ma_verification', ?,
                       NULL, NULL, ?)""",
            (NOW, resolution_notes),
        )
        conflict_id = cur.lastrowid
        rn["hold_reason"] = "filed_to_conflicts_pending_ma_verification"
        rn["mac110_conflict_id"] = conflict_id
        rn["mac110_filed_at"] = NOW
        cur.execute(
            "UPDATE raw_observations SET notes=? WHERE id=242677",
            (json.dumps(rn, separators=(",", ":")),),
        )
        out["q7"].append({"raw_id": 242677, "conflict_id": conflict_id})

    return out


# ---------------------------------------------------------------------------
# Stage 2 — re-triage 198 mapper-corrected + 69 vocab-cleared + 38 bx_sig
# ---------------------------------------------------------------------------

# Per SAR-13 §S.3 routing: candidate_types that map to behavioral_signatures
BX_SIG_ROUTED_TYPES = {
    "wireshark_field",
    "tunable_threshold",
    "logcat_detection_string",
    "threat_level_enum",
    "modem_device_path",
    "oem_service_mode_command",
}

# Cellular generation hints for AIMSICD / IMSICatcherDetector bx_sig rows
def derive_cellular_generation(src_id: int, candidate: str, excerpt: str | None) -> str | None:
    text = (excerpt or "") + " " + (candidate or "")
    if re.search(r"\b(GSM|MWI|TMSI|gsm_)", text, re.I):
        return "2G"
    if re.search(r"\b(UMTS|RRC|f9|UTRAN)", text, re.I):
        return "3G"
    if re.search(r"\b(LTE|EUTRAN|EEA|EIA)", text, re.I):
        return "4G"
    if re.search(r"\b5G\b", text, re.I):
        return "5G_NSA"
    return None


def derive_bx_sig_device_category(src_id: int, candidate_type: str) -> str:
    # src=31 IMSICatcherDetector + src=32 AIMSICD → imsi_catcher per SAR-13 §S.3
    if src_id in (31, 32):
        return "imsi_catcher"
    return "unknown"


def stage2_bx_sig_backfill(cur) -> dict:
    """Backfill src=31 wireshark_field + src=32 (5 types) into behavioral_signatures."""
    out = {"inserted": [], "skipped_idempotent": [], "errors": []}
    cur.execute(
        """SELECT id, source_id, candidate_identifier, candidate_type,
                  source_url, source_excerpt, notes
           FROM raw_observations
           WHERE source_id IN (31, 32)
             AND candidate_type IN ('wireshark_field','tunable_threshold',
                                    'logcat_detection_string','threat_level_enum',
                                    'modem_device_path','oem_service_mode_command')
             AND promoted_identifier_id IS NULL
           ORDER BY id"""
    )
    rows = cur.fetchall()
    for raw_id, sid, cand, ctype, url, exc, raw_notes_raw in rows:
        rn = cur_notes(raw_notes_raw)
        # Idempotency: skip if mac110_promoted_to_bx_sig_id already set
        if rn.get("mac110_promoted_to_bx_sig_id") or rn.get("promoted_to_behavioral_signatures_id"):
            out["skipped_idempotent"].append({"raw_id": raw_id})
            continue
        cellular_gen = derive_cellular_generation(sid, cand, exc)
        device_cat = derive_bx_sig_device_category(sid, ctype)

        # Threshold/evidence JSON
        threshold_json = None
        evidence_json_payload = {
            "candidate_type": ctype,
            "source_id": sid,
            "raw_observation_id": raw_id,
            "source_excerpt": exc,
            "source_url": url,
            "ratified_at_mac": RATIFIED_AT_MAC,
            "sar13_routing": "§S.3 detector-internal class — routed to behavioral_signatures",
        }
        if ctype == "tunable_threshold":
            threshold_json = json.dumps({
                "tunable_name": cand,
                "source_excerpt": exc,
                "source_url": url,
            }, separators=(",", ":"))

        notes_b = {
            "stage": "mac110_stage2_bx_sig_backfill",
            "candidate_type": ctype,
            "raw_observation_id": raw_id,
            "ratified_at_mac": RATIFIED_AT_MAC,
            "sar13_routing_cite": "SAR-13 §S.3 detector-internal class",
        }

        try:
            cur.execute(
                """INSERT INTO behavioral_signatures
                     (signature_name, cellular_generation, threshold_json,
                      evidence_json, source_id, source_file_relative, source_line,
                      confidence, device_category, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?)""",
                (
                    cand[:200], cellular_gen, threshold_json,
                    json.dumps(evidence_json_payload, separators=(",", ":")),
                    sid, CONF_FLOOR, device_cat,
                    json.dumps(notes_b, separators=(",", ":")), NOW, NOW,
                ),
            )
            new_bx_id = cur.lastrowid
        except sqlite3.IntegrityError as e:
            # UNIQUE collision (signature_name, source_id, cellular_generation)
            cur.execute(
                """SELECT id FROM behavioral_signatures
                   WHERE signature_name=? AND source_id=?
                     AND (cellular_generation IS ? OR cellular_generation=?)""",
                (cand[:200], sid, cellular_gen, cellular_gen),
            )
            ex = cur.fetchone()
            new_bx_id = ex[0] if ex else None
            out["errors"].append({"raw_id": raw_id, "err": str(e), "fallback_bx_id": new_bx_id})
            if new_bx_id is None:
                continue

        # Update raw_observations.notes with the bx_sig backfill marker (do NOT
        # set promoted_identifier_id — bx_sig is a separate target table)
        rn.pop("hold_reason", None)
        rn["mac110_promoted_to_bx_sig_id"] = new_bx_id
        rn["promoted_to_behavioral_signatures_id"] = new_bx_id  # SAR-13 §S.3 canonical
        rn["mac110_backfilled_at"] = NOW
        cur.execute(
            "UPDATE raw_observations SET notes=? WHERE id=?",
            (json.dumps(rn, separators=(",", ":")), raw_id),
        )
        out["inserted"].append({"raw_id": raw_id, "bx_id": new_bx_id, "ctype": ctype})

    return out


def determine_device_category(src_id: int, candidate_type: str, excerpt: str | None) -> str:
    """Conservative dc inference per §11 #13. Source-scope hints only."""
    # src=27 (RUB-SysSec / cyber-defence-campus ASD-STAN / DJI parser) → drone
    if src_id == 27:
        return "drone"
    # src=40 (FoggedLens deflock-app) → alpr
    if src_id == 40:
        return "alpr"
    # src=41 (GainSec anti-crime) — Flock-context heuristic
    if src_id == 41:
        if excerpt and re.search(r"flock|alpr|falcon|sparrow|raven", excerpt, re.I):
            return "alpr"
        return "alpr"  # GainSec corpus is Flock-anchored
    # src=42 (GainSec ALPR firmware) → alpr
    if src_id == 42:
        return "alpr"
    # src=43 (RUB-SysSec DroneSecurity) → drone
    if src_id == 43:
        return "drone"
    # src=29 (Wave-D / Wave-G BLE) — typically unknown without manufacturer evidence
    if src_id == 29:
        return "unknown"
    if src_id == 31:
        return "imsi_catcher"
    if src_id == 32:
        return "imsi_catcher"
    return "unknown"


def determine_manufacturer(src_id: int, excerpt: str | None) -> str | None:
    """Conservative manufacturer inference per §8.4 hardware-anchor sub-rule."""
    if src_id == 27:
        return None  # ASD-STAN protocol identifiers; no single manufacturer
    if src_id == 40:
        return "Flock Safety"  # deflock-app is Flock-specific surveillance tooling
    if src_id == 41:
        return "Flock Safety"  # GainSec Flock-anchored
    if src_id == 42:
        return "Flock Safety"  # ALPR firmware extraction
    if src_id == 43:
        return "DJI"
    return None


def stage2_mapper_corrected_and_vocab_cleared(cur) -> dict:
    """Re-triage all unpromoted A_deferred_dir rows (199 + 69), apply cascade."""
    out = {
        "promoted": [],
        "held_id_type_vocab_round2_pending": [],
        "filed_to_conflicts_cve_fp": [],
        "filed_to_conflicts_known_fake": [],
        "skipped_mac58_deferred": [],
        "skipped_bx_sig_already_routed": [],
        "skipped_already_promoted": [],
    }
    cur.execute(
        """SELECT id, source_id, candidate_identifier, candidate_type,
                  source_url, source_excerpt, notes, promoted_identifier_id
           FROM raw_observations
           WHERE source_id IN (27, 29, 31, 32, 40, 41, 42, 43)
             AND promoted_identifier_id IS NULL
           ORDER BY source_id, id"""
    )
    rows = cur.fetchall()
    for raw_id, sid, cand, ctype, url, exc, raw_notes_raw, prev_pid in rows:
        rn = cur_notes(raw_notes_raw)
        hold = rn.get("hold_reason")

        # Skip mac58 deferred bx_sig (NOT in MAC-110 scope per
        # project_mac58_behavioral_signatures_option_b.md)
        if hold == "mac58_option_b_phase_6_deferred":
            out["skipped_mac58_deferred"].append({"raw_id": raw_id, "ctype": ctype})
            continue
        # bx_sig already routed via stage2_bx_sig_backfill
        if rn.get("mac110_promoted_to_bx_sig_id") or rn.get("promoted_to_behavioral_signatures_id"):
            out["skipped_bx_sig_already_routed"].append({"raw_id": raw_id})
            continue
        if ctype in BX_SIG_ROUTED_TYPES:
            # Should have been picked up by stage2_bx_sig_backfill — defensive skip
            out["skipped_bx_sig_already_routed"].append({"raw_id": raw_id, "note": "bx_sig_routed_type_not_yet_backfilled"})
            continue

        # CVE-FP allowlist (SAR-7 #1)
        if ctype == "cve_reference" or CVE_FP_RE.match(cand) or CWE_FP_RE.match(cand):
            cur.execute(
                "SELECT id FROM conflicts WHERE raw_observation_id=? AND reason='known_fake_pattern'",
                (raw_id,),
            )
            if cur.fetchone():
                out["skipped_already_promoted"].append({"raw_id": raw_id, "note": "conflict_present"})
                continue
            cur.execute(
                """INSERT INTO conflicts
                     (identifier_a_id, identifier_b_id, raw_observation_id,
                      reason, detected_at, resolved_at, resolved_by, resolution_notes)
                   VALUES (NULL, NULL, ?, 'known_fake_pattern', ?, NULL, NULL, ?)""",
                (
                    raw_id, NOW,
                    json.dumps({
                        "reject_reason": "cve_reference candidate matches CVE/CWE shape — SAR-7 #1 CVE-FP allowlist",
                        "candidate": cand,
                        "candidate_type": ctype,
                        "stage": "mac110_stage2_sar7_cve_fp",
                        "ratified_at_mac": RATIFIED_AT_MAC,
                        "rule_cite": "SAR-7 #1 + §11 #11",
                    }, separators=(",", ":")),
                ),
            )
            conflict_id = cur.lastrowid
            rn["hold_reason"] = "filed_to_conflicts_cve_fp"
            rn["mac110_conflict_id"] = conflict_id
            rn["mac110_filed_at"] = NOW
            cur.execute(
                "UPDATE raw_observations SET notes=? WHERE id=?",
                (json.dumps(rn, separators=(",", ":")), raw_id),
            )
            out["filed_to_conflicts_cve_fp"].append({"raw_id": raw_id, "conflict_id": conflict_id})
            continue

        # §4.3 normalization candidate_type → identifier_type
        target_itype = CANDIDATE_TYPE_NORMALIZE.get(ctype, ctype)

        # §11 #13 / CHECK enum gate
        if target_itype not in VALID_IDENTIFIER_TYPES:
            rn["hold_reason"] = "id_type_vocab_round2_pending"
            rn["mac110_held_for"] = (
                f"candidate_type={ctype} not in identifier_type CHECK enum "
                f"(post-0018, 41 cumulative); HOLD pending round-2 vocab "
                f"extension review by CEO/board."
            )
            rn["mac110_triage_at"] = NOW
            cur.execute(
                "UPDATE raw_observations SET notes=? WHERE id=?",
                (json.dumps(rn, separators=(",", ":")), raw_id),
            )
            out["held_id_type_vocab_round2_pending"].append({
                "raw_id": raw_id, "src": sid, "ctype": ctype, "cand": cand[:60],
            })
            continue

        # §7.3 known-fake gate (OUI level)
        norm_value = normalize_identifier(target_itype, cand)
        if target_itype == "oui" and is_known_fake_oui(norm_value):
            cur.execute(
                "SELECT id FROM conflicts WHERE raw_observation_id=? AND reason='known_fake_pattern'",
                (raw_id,),
            )
            if cur.fetchone():
                continue
            cur.execute(
                """INSERT INTO conflicts
                     (identifier_a_id, identifier_b_id, raw_observation_id,
                      reason, detected_at, resolved_at, resolved_by, resolution_notes)
                   VALUES (NULL, NULL, ?, 'known_fake_pattern', ?, NULL, NULL, ?)""",
                (
                    raw_id, NOW,
                    json.dumps({
                        "reject_reason": "known_fake_pattern",
                        "candidate": cand,
                        "rule_cite": "§7.3 known-fake enumeration applied to OUI per §7.4",
                        "stage": "mac110_stage2_known_fake",
                    }, separators=(",", ":")),
                ),
            )
            conflict_id = cur.lastrowid
            rn["hold_reason"] = "filed_to_conflicts_known_fake"
            rn["mac110_conflict_id"] = conflict_id
            cur.execute(
                "UPDATE raw_observations SET notes=? WHERE id=?",
                (json.dumps(rn, separators=(",", ":")), raw_id),
            )
            out["filed_to_conflicts_known_fake"].append({"raw_id": raw_id, "conflict_id": conflict_id})
            continue

        # Promote — facts-only per §11 #16 at conf=65 (Wave-A precedent floor)
        dc = determine_device_category(sid, ctype, exc)
        mfr = determine_manufacturer(sid, exc)
        excerpt_capped = (exc or "")[:200] if exc else None
        new_notes = {
            "stage": "mac110_stage2_promote",
            "candidate_type": ctype,
            "raw_observation_id": raw_id,
            "wave": "A_deferred_dir",
            "ratified_at_mac": RATIFIED_AT_MAC,
            "facts_only_basis": "§11 #16 Feist facts-only promotion (NO_LICENSE_DECLARED / public-but-unlicensed)",
            "src_band_basis": "§8.2 crowdsourced 50–75 cap (≤70 dispatch ratification ceiling); Wave-A precedent floor 65",
            "id_type_normalize": (
                f"candidate_type={ctype} → identifier_type={target_itype} per §4.3"
                if ctype != target_itype else f"identifier_type={target_itype} (no normalization needed)"
            ),
        }

        # Idempotency: skip if any active identifier carries this raw_observation_id marker
        cur.execute(
            "SELECT id FROM identifiers WHERE notes LIKE ? AND superseded_by IS NULL",
            (f'%"raw_observation_id":{raw_id},"wave":"A_deferred_dir","ratified_at_mac":"{RATIFIED_AT_MAC}"%',),
        )
        ex = cur.fetchone()
        if ex:
            out["skipped_already_promoted"].append({"raw_id": raw_id, "id": ex[0]})
            continue

        try:
            cur.execute(
                """INSERT INTO identifiers
                     (identifier, identifier_type, device_category, manufacturer, model,
                      confidence, source_url, source_type, source_excerpt, geographic_scope,
                      first_seen, last_verified, notes)
                   VALUES (?, ?, ?, ?, NULL,
                           ?, ?, 'crowdsourced', ?, ?,
                           ?, ?, ?)""",
                (
                    norm_value, target_itype, dc, mfr,
                    CONF_FLOOR, url, excerpt_capped, GEO_SCOPE_DEFAULT,
                    NOW, NOW, json.dumps(new_notes, separators=(",", ":")),
                ),
            )
            new_id = cur.lastrowid
        except sqlite3.IntegrityError as e:
            # CHECK violation or similar — HOLD with parse-error tag
            rn["hold_reason"] = "id_type_vocab_round2_pending"
            rn["mac110_check_constraint_error"] = str(e)
            rn["mac110_triage_at"] = NOW
            cur.execute(
                "UPDATE raw_observations SET notes=? WHERE id=?",
                (json.dumps(rn, separators=(",", ":")), raw_id),
            )
            out["held_id_type_vocab_round2_pending"].append({
                "raw_id": raw_id, "src": sid, "ctype": ctype, "cand": cand[:60],
                "check_err": str(e),
            })
            continue
        # Repoint raw_observations + clear hold_reason
        rn.pop("hold_reason", None)
        rn["mac110_promoted_to_identifier_id"] = new_id
        rn["mac110_promoted_at"] = NOW
        cur.execute(
            "UPDATE raw_observations SET promoted_identifier_id=?, notes=? WHERE id=?",
            (new_id, json.dumps(rn, separators=(",", ":")), raw_id),
        )
        out["promoted"].append({
            "raw_id": raw_id, "src": sid, "id_type": target_itype,
            "value": norm_value[:60], "new_id": new_id, "dc": dc,
        })

    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run() -> dict:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    summary: dict = {}
    try:
        cur = con.cursor()

        # Stage 1 — single transaction
        cur.execute("BEGIN IMMEDIATE")
        summary["stage1"] = execute_stage1(cur)
        con.commit()

        # Stage 2a — bx_sig backfill (separate transaction; lighter risk)
        cur.execute("BEGIN IMMEDIATE")
        summary["stage2_bx_sig"] = stage2_bx_sig_backfill(cur)
        con.commit()

        # Stage 2b — mapper-corrected + vocab-cleared re-triage
        cur.execute("BEGIN IMMEDIATE")
        summary["stage2_main"] = stage2_mapper_corrected_and_vocab_cleared(cur)
        con.commit()
    finally:
        con.close()
    return summary


def main() -> int:
    summary = run()
    print(json.dumps({"summary_counts": {
        "stage1_q3": len(summary["stage1"]["q3"]),
        "stage1_q4": len(summary["stage1"]["q4"]),
        "stage1_q5": len(summary["stage1"]["q5"]),
        "stage1_q7": len(summary["stage1"]["q7"]),
        "stage2_bx_sig_inserted": len(summary["stage2_bx_sig"]["inserted"]),
        "stage2_bx_sig_skipped": len(summary["stage2_bx_sig"]["skipped_idempotent"]),
        "stage2_promoted": len(summary["stage2_main"]["promoted"]),
        "stage2_held_round2": len(summary["stage2_main"]["held_id_type_vocab_round2_pending"]),
        "stage2_cve_fp": len(summary["stage2_main"]["filed_to_conflicts_cve_fp"]),
        "stage2_known_fake": len(summary["stage2_main"]["filed_to_conflicts_known_fake"]),
        "stage2_skipped_mac58": len(summary["stage2_main"]["skipped_mac58_deferred"]),
    }}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
