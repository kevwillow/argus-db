#!/usr/bin/env python3
"""MAC-178 Priority 3 — MAC-104 Wave-G v2 net-new identifier candidates.

Promotes the 16 clean-enum-fit candidates to `identifiers` per §11 #8 + CP17/CP14
sub-banding. Stages all 20 candidates in `raw_observations` for provenance.
Holds 4 schema-gap candidates (no clean enum slot) with documented reason.

Cross-source corroboration (§5.6): all 20 verified net-new — no existing
identifier matches → no uplift, no §5.6 ownership-mismatch surface.

Provenance per row anchored at the vendor app's apk-pure listing URL +
apk_sha256 + source_excerpt (verbatim from candidates.json, ≤200 chars per
identifiers.source_excerpt CHECK).

Idempotent: re-runs yield 0 new rows.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"


# ============================================================================
# Vendor app anchors (apk-pure listing URLs, captured at extraction time)
# ============================================================================

VENDOR_APPS = {
    "hikvision_hikconnect": {
        "manufacturer": "Hikvision",
        "package": "com.hikvision.hikconnect",
        "version": "6.11.631.0506",
        "apk_sha256": "6ee6129f5a9f108f79342790f8d7e89a18f7ed1405492792b39078e27d7ed349",
        "source_url": "https://apkpure.com/p/com.hikvision.hikconnect",
        "cohort": "operator_with_installer_ble_code_path",
        "device_category": "unknown",
    },
    "dahua_dmss": {
        "manufacturer": "Dahua",
        "package": "com.mm.android.DMSS",
        "version": "2.4.14",
        "apk_sha256": "d30abda0495351d3bd6b7345aa4c89fff5b135a28a7c002073dcd295da9e1efb",
        "source_url": "https://apkpure.com/p/com.mm.android.DMSS",
        "cohort": "operator_plus_likely_installer",
        "device_category": "unknown",
    },
    "motorola_wave_ptt": {
        "manufacturer": "Motorola Solutions",
        "package": "com.motorolasolutions.wave",
        "version": "3.1.8.47141",
        "apk_sha256": "24b01b218052430c2b40a103827937fc4e58b7f4378a099fc6768a83dfc7e897",
        "source_url": "https://apkpure.com/p/com.motorolasolutions.wave",
        "cohort": "installer",
        "device_category": "police_radio",
    },
    "parrot_freeflight6": {
        "manufacturer": "Parrot",
        "package": "com.parrot.freeflight6",
        "version": "6.7.6",
        "apk_sha256": "a105b0815e26c46f2e8ff4d9f3f83509c0b1e5e4f0731df8775681657f18db73",
        "source_url": "https://apkpure.com/p/com.parrot.freeflight6",
        "cohort": "installer_plus_operator",
        "device_category": "drone",
    },
}


# ============================================================================
# 16 PROMOTABLE candidates — clean enum fit per CP14/CP17/CP20 sub-banding
# Confidence: single-source manufacturer_app; CP17 installer-cohort BLE code
# paths anchored in vendor-named classes → 87 (matches existing Flock Safety /
# Getac convention from prior waves). 16-bit SIG-template → 75 (lower
# anchor-strength). Parrot company-id 67 (SIG-registered) → 85.
# Drone-RID class hits (CP14): 85 (clear-text Java in ArsdkFeatureDri.java;
# §5.6 EN 4709-002 / ASTM F3411-22a / ANSI CTA-2063 public-standard alignment).
# ============================================================================

PROMOTE = [
    # --- Hikvision Hik-Connect (3 BLE; installer-cohort code path) -----------
    {
        "kind": "promote",
        "vendor_key": "hikvision_hikconnect",
        "identifier": "f6ec37db-bda1-46ec-a43a-6d86de88561d",
        "identifier_type": "ble_service_uuid",
        "model": None,
        "confidence": 87,
        "source_excerpt": 'UUID.fromString("f6ec37db-bda1-46ec-a43a-6d86de88561d") in sources/defpackage/ge1.java:299 — anchored in com.hikvision.hikconnect.devicesetting.bluetooth.HcpBluetoothServer',
        "value_class": "ble_service_uuid",
        "role": "service",
    },
    {
        "kind": "promote",
        "vendor_key": "hikvision_hikconnect",
        "identifier": "af20fbac-2518-4998-9af7-af42540731b3",
        "identifier_type": "ble_characteristic",
        "model": None,
        "confidence": 87,
        "source_excerpt": "BluetoothGattService.equals(...) / getCharacteristic(af20fbac-2518-4998-9af7-af42540731b3) in HcpBluetoothServer (Hik-Connect installer BLE pairing path)",
        "value_class": "ble_characteristic",
        "role": "characteristic",
    },
    {
        "kind": "promote",
        "vendor_key": "hikvision_hikconnect",
        "identifier": "af20fbac-2518-4998-9af7-af42540731b4",
        "identifier_type": "ble_characteristic",
        "model": None,
        "confidence": 87,
        "source_excerpt": "notify-characteristic UUID af20fbac-2518-4998-9af7-af42540731b4 in os/cloudacs/bluetooth/server/BluetoothServer (Hik-Connect BLE notify path; paired with -b3 char)",
        "value_class": "ble_characteristic",
        "role": "notify_characteristic",
    },
    # --- Dahua DMSS (2 BLE; installer code path in obfuscated class) ---------
    {
        "kind": "promote",
        "vendor_key": "dahua_dmss",
        "identifier": "d54ace3f-8e27-4718-aa17-019f0e318e14",
        "identifier_type": "ble_service_uuid",
        "model": None,
        "confidence": 87,
        "source_excerpt": 'public String f54889f = "d54ace3f-8e27-4718-aa17-019f0e318e14"; in sources/en/f.java:30 (obfuscated; field paired with f54890g UUID below)',
        "value_class": "ble_service_uuid",
        "role": "service",
    },
    {
        "kind": "promote",
        "vendor_key": "dahua_dmss",
        "identifier": "9782022b-32ca-4346-832e-779db180cf4b",
        "identifier_type": "ble_characteristic",
        "model": None,
        "confidence": 87,
        "source_excerpt": 'public String f54890g = "9782022b-32ca-4346-832e-779db180cf4b"; in sources/en/f.java (obfuscated; paired with d54ace3f service UUID above)',
        "value_class": "ble_characteristic",
        "role": "characteristic",
    },
    # --- Motorola WAVE PTT (3 custom 128-bit + 1 16-bit SIG template) --------
    {
        "kind": "promote",
        "vendor_key": "motorola_wave_ptt",
        "identifier": "2320ae58-8394-4652-95f7-0a872ac0958f",
        "identifier_type": "ble_service_uuid",
        "model": "Milicom PTT Button",
        "confidence": 87,
        "source_excerpt": 'milicomServiceId = "2320ae58-8394-4652-95f7-0a872ac0958f" in BluetoothLowEnergyPttValues / WaveBluetoothManager$2 (parent GATT service for Milicom PTT Button)',
        "value_class": "ble_service_uuid",
        "role": "service",
    },
    {
        "kind": "promote",
        "vendor_key": "motorola_wave_ptt",
        "identifier": "a0547dec-3b67-4d22-980d-48b700801dc5",
        "identifier_type": "ble_characteristic",
        "model": "Milicom PTT Button",
        "confidence": 87,
        "source_excerpt": 'milicomCharacteristicId = "a0547dec-3b67-4d22-980d-48b700801dc5" in WaveBluetoothManager$2 (Milicom PTT Button BLE characteristic)',
        "value_class": "ble_characteristic",
        "role": "characteristic",
    },
    {
        "kind": "promote",
        "vendor_key": "motorola_wave_ptt",
        "identifier": "481de929-8d4c-4d9e-a574-772a73e63977",
        "identifier_type": "ble_characteristic",
        "model": "Milicom PTT Button",
        "confidence": 87,
        "source_excerpt": 'milicomDirectConnect = "481de929-8d4c-4d9e-a574-772a73e63977" in WaveBluetoothManager$2 (Milicom direct-connect characteristic; paired write endpoint)',
        "value_class": "ble_characteristic",
        "role": "characteristic_write",
    },
    {
        "kind": "promote",
        "vendor_key": "motorola_wave_ptt",
        "identifier": "0000ffff-0000-1000-8000-00805f9b34fb",
        "identifier_type": "ble_service_uuid",
        "model": "Milicom PTT Button",
        "confidence": 75,
        "source_excerpt": 'MILICOM_SERVICE 16-bit SIG-template (0xFFFF) in BluetoothLowEnergyPttValues.populateUUIDs() — observable in BLE scans only when paired with MILICOM_PRESS/RELEASE byte command sequence; ceiling 85 single-source',
        "value_class": "ble_service_uuid",
        "role": "service_sig_template_16bit",
    },
    # --- Parrot company ID (CP14 ble_company_id) -----------------------------
    {
        "kind": "promote",
        "vendor_key": "parrot_freeflight6",
        "identifier": "67",
        "identifier_type": "ble_company_id",
        "model": "ANAFI / Bebop / Disco",
        "confidence": 85,
        "source_excerpt": "ScanFilter.Builder().setManufacturerData(67, new byte[]{-49, 25, ...}) in ArsdkBleDiscovery.java:204 — BT SIG company ID 67 (0x0043) = Parrot SA + advert prefix 0xCF 0x19",
        "value_class": "ble_company_id",
        "role": "manufacturer_id",
    },
    # --- Parrot 6 Drone-RID class hits (CP14 cluster) ------------------------
    {
        "kind": "promote",
        "vendor_key": "parrot_freeflight6",
        "identifier": "FR_30_OCTETS",
        "identifier_type": "asdstan_enum_value",
        "model": "ANAFI USA",
        "confidence": 85,
        "source_excerpt": 'IdType.FR_30_OCTETS in com/parrot/drone/sdkcore/arsdk/ArsdkFeatureDri.java (France 30-octet UAS ID format; ASTM F3411-22a Type 1)',
        "value_class": "drone_rid_id_type_enum",
        "role": "uas_id_format",
    },
    {
        "kind": "promote",
        "vendor_key": "parrot_freeflight6",
        "identifier": "ANSI_CTA_2063",
        "identifier_type": "asdstan_enum_value",
        "model": "ANAFI USA",
        "confidence": 85,
        "source_excerpt": "IdType.ANSI_CTA_2063 in ArsdkFeatureDri.java (ANSI/CTA-2063 serial-number format; ASTM F3411-22a Type 1)",
        "value_class": "drone_rid_id_type_enum",
        "role": "uas_id_format",
    },
    {
        "kind": "promote",
        "vendor_key": "parrot_freeflight6",
        "identifier": "FRENCH",
        "identifier_type": "asdstan_enum_value",
        "model": "ANAFI",
        "confidence": 85,
        "source_excerpt": "DriType.FRENCH in ArsdkFeatureDri.java (France DGAC ED82 direct-broadcast regulation profile)",
        "value_class": "dri_regulation_enum",
        "role": "regulation_profile",
    },
    {
        "kind": "promote",
        "vendor_key": "parrot_freeflight6",
        "identifier": "EN4709_002",
        "identifier_type": "asdstan_enum_value",
        "model": "ANAFI",
        "confidence": 85,
        "source_excerpt": "DriType.EN4709_002 in ArsdkFeatureDri.java (EU EN 4709-002 direct broadcast Remote-ID regulation profile)",
        "value_class": "dri_regulation_enum",
        "role": "regulation_profile",
    },
    {
        "kind": "promote",
        "vendor_key": "parrot_freeflight6",
        "identifier": "41984",
        "identifier_type": "device_class_id",
        "model": "ANAFI",
        "confidence": 85,
        "source_excerpt": "arsdk_feature_uid=41984 (0xA400) in ArsdkFeatureDri.java — Parrot ARSDK DRI feature class identifier",
        "value_class": "arsdk_feature_uid",
        "role": "feature_class",
    },
    {
        "kind": "promote",
        "vendor_key": "parrot_freeflight6",
        "identifier": "CAPABILITIES=1,DRI_STATE=3,DRONE_ID=4,DRI_TYPE=6",
        "identifier_type": "rf_protocol_constant",
        "model": "ANAFI",
        "confidence": 85,
        "source_excerpt": "ArsdkFeatureDri command UID set: CAPABILITIES=1, DRI_STATE=3, DRONE_ID=4, DRI_TYPE=6 (Parrot DRI command opcode table)",
        "value_class": "arsdk_dri_command_uid_set",
        "role": "command_table",
    },
]


# ============================================================================
# 4 HOLD candidates — no clean enum slot or handoff-flagged-no-promote.
# Stage in raw_observations only; flag for SAR-12 / Validator-review.
# ============================================================================

HOLD = [
    {
        "kind": "hold",
        "vendor_key": "dahua_dmss",
        "identifier": "lc2014",
        "candidate_type": "default_credential",
        "hold_reason": "schema_gap_no_credential_enum_slot",
        "model": None,
        "proposed_confidence": 70,
        "source_excerpt": 'devLoginPassword = "lc2014" in com/open/opensdk/LCOpenSDK_PlayWindow.java:130 (LeChange SDK installer default password; cross-check vendor PSIRT before promotion)',
    },
    {
        "kind": "hold",
        "vendor_key": "dahua_dmss",
        "identifier": "terminal",
        "candidate_type": "default_credential",
        "hold_reason": "schema_gap_no_credential_enum_slot",
        "model": None,
        "proposed_confidence": 65,
        "source_excerpt": 'clientSecret = "terminal" in mobilecommon/entity/user/UniLoginInfo.java:14 (DMSS cloud OAuth client_secret; installer-cohort credential candidate)',
    },
    {
        "kind": "hold",
        "vendor_key": "parrot_freeflight6",
        "identifier": "0045b822-753b-4b8a-9c65-8b97ca8a5dd4",
        "candidate_type": "vendor_namespace_uuid",
        "hold_reason": "handoff_flagged_not_ble_service_uuid_no_enum_fit",
        "model": "ANAFI / Skyward",
        "proposed_confidence": 70,
        "source_excerpt": 'SKYWARD_ANAFI_SOURCE_UUID = "0045b822-753b-4b8a-9c65-8b97ca8a5dd4" in com/parrot/freeflight/util/ConstantsKt.java:102 (Verizon Skyward UTM source-attribution UUID; NOT a BLE service UUID)',
    },
    {
        "kind": "hold",
        # DJI Pilot RTK serial-number template — not in candidate file; canonical
        # source is HANDOFF_TO_USER_104d.md §-DJI Pilot
        "vendor_key": "dji_pilot",
        "identifier": "1APDF7Q0010001",
        "candidate_type": "rtk_rc_serial_template",
        "hold_reason": "handoff_explicitly_not_promoted_flagged",
        "model": "DJI RC NRTK base-station",
        "proposed_confidence": 60,
        "source_excerpt": '"1APDF7Q0010001" in res/layout/setting_ui_rtk_type_switch_layout.xml — DJI RC NRTK setup screen default. Prefix 1APDF7Q matches DJI manufacturer+product-code SN format; flag for CP14 RTK + RC subclass review',
    },
]

# DJI Pilot anchor for the held RTK template
DJI_PILOT_APP = {
    "manufacturer": "DJI",
    "package": "com.dji.industry.pilot",
    "version": "v1.9.0",
    "apk_sha256": "9334b0474300e24ca44209ef5a60eb7cc58b1a7637c4d4954bc09668b16812be",
    "source_url": "https://apkpure.com/p/com.dji.industry.pilot",
    "cohort": "operator_plus_installer",
    "device_category": "drone",
}


def find_source_id(db: sqlite3.Connection, source_type: str) -> int:
    # manufacturer_app is the source_type; we need a source row anchoring
    # vendor-app extractions. Wave-G v1 set this up; verify.
    r = db.execute(
        "SELECT id, name, url FROM sources WHERE source_type='manufacturer_app' ORDER BY id LIMIT 1"
    ).fetchone()
    if r is None:
        raise RuntimeError("no manufacturer_app source row exists; need Priority-0 cleanup")
    return r[0]


def main() -> int:
    print(f"DB: {DB}")
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    try:
        # Resolve a source_id for source_type='manufacturer_app'. The Wave-G v1
        # admission created a generic apk-pure source row; reuse it (the
        # source_url-per-row carries the precise vendor anchor).
        manufacturer_app_source_id = find_source_id(db, "manufacturer_app")
        print(f"  manufacturer_app source_id = {manufacturer_app_source_id}")

        db.execute("BEGIN")
        promoted = 0
        held = 0
        promoted_existing_corroboration_uplifts = 0

        all_rows = [(p, VENDOR_APPS[p["vendor_key"]]) for p in PROMOTE]
        all_rows += [
            (
                h,
                VENDOR_APPS[h["vendor_key"]] if h["vendor_key"] in VENDOR_APPS else DJI_PILOT_APP,
            )
            for h in HOLD
        ]

        for cand, vendor in all_rows:
            src_url = vendor["source_url"]
            manufacturer = vendor["manufacturer"]
            cohort = vendor["cohort"]
            device_cat = vendor["device_category"]
            identifier = cand["identifier"]
            value_class = cand.get("value_class") or cand.get("candidate_type")
            excerpt = cand["source_excerpt"][:200]

            # source_row_key: per-vendor+identifier deterministic
            source_row_key = (
                f"mac178:wave_g_v2:{cand['vendor_key']}:{value_class}:{identifier}"
            )

            # raw_observations idempotency
            existing_raw = db.execute(
                "SELECT id FROM raw_observations WHERE source_row_key=?",
                (source_row_key,),
            ).fetchone()
            raw_is_new = existing_raw is None
            if existing_raw:
                raw_id = existing_raw[0]
            else:
                notes_obj = {
                    "vendor_key": cand["vendor_key"],
                    "vendor_canonical": manufacturer,
                    "apk_package": vendor["package"],
                    "apk_version": vendor["version"],
                    "apk_sha256": vendor["apk_sha256"],
                    "cohort_classification": cohort,
                    "value_class": value_class,
                    "role": cand.get("role"),
                    "static_analysis_framework": "17 USC §1201(j) + 37 CFR §201.40(b)",
                    "admission_dispatch_ref": "MAC-104"
                    + ("d" if cand["vendor_key"] == "parrot_freeflight6" else "")
                    + ("b" if cand["vendor_key"] == "motorola_wave_ptt" else ""),
                    "integration_dispatch_ref": "MAC-178",
                    "promotion_disposition": cand["kind"],
                }
                if cand["kind"] == "hold":
                    notes_obj["hold_reason"] = cand["hold_reason"]
                    notes_obj["proposed_confidence"] = cand["proposed_confidence"]
                    notes_obj["validator_review_recommendation"] = (
                        "SAR-12 schema extension proposal: open enum slot for "
                        f"{value_class}; until then this row stays staging-only "
                        "and is excluded from exports per §11 #8."
                    )

                db.execute(
                    """
                    INSERT INTO raw_observations (
                        source_id, source_url, raw_payload, candidate_identifier,
                        candidate_type, candidate_category, candidate_manufacturer,
                        source_excerpt, source_row_key, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        manufacturer_app_source_id,
                        src_url,
                        None,
                        identifier,
                        value_class,
                        device_cat,
                        manufacturer,
                        excerpt,
                        source_row_key,
                        json.dumps(notes_obj, ensure_ascii=False, sort_keys=True),
                    ),
                )
                raw_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Identifier promotion (only PROMOTE kind, only if no existing row
            # at this identifier+type matches — §5.6 corroboration check).
            if cand["kind"] != "promote":
                held += 1
                continue

            # Idempotency gate: skip the promotion/uplift path entirely if
            # this raw_observation is a re-ingest of the same staging row.
            # §5.6 corroboration uplifts only fire on first-ingest of an
            # independent source; same staging row re-running is a no-op.
            if not raw_is_new:
                continue

            existing_id = db.execute(
                """
                SELECT id, confidence FROM identifiers
                WHERE LOWER(identifier)=LOWER(?) AND identifier_type=?
                  AND superseded_by IS NULL
                """,
                (identifier, cand["identifier_type"]),
            ).fetchone()
            if existing_id is not None:
                # §5.6 corroboration: independent source matches; uplift by +5
                # (cap 99). Note ownership-mismatch flag if manufacturer differs.
                old_conf = existing_id["confidence"] or 0
                new_conf = min(99, old_conf + 5)
                print(
                    f"  §5.6 UPLIFT existing id={existing_id['id']} confidence "
                    f"{old_conf} → {new_conf} (corroboration from {cand['vendor_key']})"
                )
                db.execute(
                    "UPDATE identifiers SET confidence=? WHERE id=?",
                    (new_conf, existing_id["id"]),
                )
                # Link the raw_observation to the existing identifier
                db.execute(
                    "UPDATE raw_observations SET promoted_identifier_id=? WHERE id=?",
                    (existing_id["id"], raw_id),
                )
                promoted_existing_corroboration_uplifts += 1
                continue

            # Net-new identifier — INSERT
            notes_obj_id = {
                "promotion_dispatch": "MAC-178",
                "source_dispatch": "MAC-104"
                + ("d" if cand["vendor_key"] == "parrot_freeflight6" else "")
                + ("b" if cand["vendor_key"] == "motorola_wave_ptt" else ""),
                "apk_sha256": vendor["apk_sha256"],
                "apk_package": vendor["package"],
                "apk_version": vendor["version"],
                "cohort_classification": cohort,
                "static_analysis_framework": "17 USC §1201(j) + 37 CFR §201.40(b)",
                "value_class_in_extraction": value_class,
                "role": cand.get("role"),
                "raw_observation_id": raw_id,
                "promotion_band_basis": "CP17 manufacturer_app sub-banding (installer-cohort code path)"
                if cand["vendor_key"] != "parrot_freeflight6"
                else "CP14 drone-RID class hit / ble_company_id (clear-text ArsdkFeatureDri Java)",
                "single_source_at_promotion": True,
            }
            db.execute(
                """
                INSERT INTO identifiers (
                    identifier, identifier_type, device_category, manufacturer,
                    model, confidence, source_url, source_type, source_excerpt,
                    geographic_scope, notes, first_seen, last_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'manufacturer_app', ?, 'US', ?,
                          CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    identifier,
                    cand["identifier_type"],
                    device_cat,
                    manufacturer,
                    cand.get("model"),
                    cand["confidence"],
                    src_url,
                    excerpt,
                    json.dumps(notes_obj_id, ensure_ascii=False, sort_keys=True),
                ),
            )
            new_id_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute(
                "UPDATE raw_observations SET promoted_identifier_id=? WHERE id=?",
                (new_id_id, raw_id),
            )
            promoted += 1

        db.commit()
        print("\nCOMMIT.")

        print("\n=== Priority 3 verification ===")
        print(f"identifiers promoted (net-new): {promoted}")
        print(f"identifiers uplifted via §5.6 corroboration: {promoted_existing_corroboration_uplifts}")
        print(f"candidates held (schema-gap / flagged): {held}")
        print()
        print("=== promotion class breakdown ===")
        for r in db.execute(
            """
            SELECT identifier_type, manufacturer, COUNT(*) c
            FROM identifiers
            WHERE notes LIKE '%MAC-178%' AND notes LIKE '%promotion_dispatch%'
            GROUP BY identifier_type, manufacturer
            ORDER BY manufacturer, identifier_type
            """
        ):
            print(f"  [{r['manufacturer']:<20}] {r['identifier_type']:<25} count={r['c']}")
        print()
        print("=== confidence distribution (MAC-178 rows) ===")
        for r in db.execute(
            """
            SELECT confidence, COUNT(*) c
            FROM identifiers
            WHERE notes LIKE '%MAC-178%' AND notes LIKE '%promotion_dispatch%'
            GROUP BY confidence
            ORDER BY confidence DESC
            """
        ):
            print(f"  confidence={r['confidence']}: {r['c']} rows")
        # High-conf eligible:
        hc = db.execute(
            """
            SELECT COUNT(*) FROM identifiers
            WHERE notes LIKE '%MAC-178%' AND notes LIKE '%promotion_dispatch%'
              AND confidence >= 70
              AND source_type NOT IN ('crowdsourced', 'inferred')
            """
        ).fetchone()[0]
        std = db.execute(
            """
            SELECT COUNT(*) FROM identifiers
            WHERE notes LIKE '%MAC-178%' AND notes LIKE '%promotion_dispatch%'
              AND confidence >= 30
            """
        ).fetchone()[0]
        print(f"\nstandard export eligible (≥30 conf): {std}")
        print(f"high-confidence export eligible (≥70 conf + non-crowdsourced/inferred): {hc}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
