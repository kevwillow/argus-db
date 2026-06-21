-- ============================================================================
-- Script:    0036_mac489_non_cohort_ble_service_uuid_fp_supersession.sql
-- Status:    STAGED — NOT APPLIED. Lands ONLY at the MAC-477 board gate,
--            alongside mig-0034 (MAC-478) and mig-0035 (MAC-486). Drop into
--            db/migrations/0036_*.sql at apply time (slot 0036 is free —
--            verified by direct working-tree read; highest live = 0033;
--            0034/0035 reserved by MAC-478/MAC-486).
-- Ordering:  Decoupled from 0034 + 0035 — this migration touches ONLY
--            out-of-cohort rows and asserts only about out-of-cohort state,
--            so it is correct in any apply order. (0034 withdraws 77 cctv_
--            installer_v1 cohort FPs; 0035 withdraws 1 entangled out-of-cohort
--            sibling id 23046; 0036 withdraws 30 distinct out-of-cohort FPs
--            under CP49.)
-- Purpose:   Withdraw 30 false-positive `ble_service_uuid` rows under the
--            CP49 standing rule (GATT service binding required; NOT a bare
--            string-pool occurrence, a GATT *characteristic*, a filename/ARN/
--            token GUID, or a 16-bit test placeholder). Scope = non-cohort
--            active rows in identifier_type='ble_service_uuid' where
--            notes.cohort != 'cctv_installer_v1' (the 85 cohort FPs are
--            handled separately by mig-0034; id 23046 is handled separately
--            by mig-0035).
-- Discovery: MAC-489 sweep (ask #3 of MAC-486, board-ratified via approval
--            bf95a897). Standing rule CP49 established by MAC-486 +
--            MAC-478 cohort re-audit (out-of-cohort application of the same
--            GATT-binding criterion). The 29 SoundThinking rows were
--            high-priority under the MAC-489 seed triage (Flork-You JSON
--            schema explicitly keys them as `characteristicUuid`).
--            1 Motorola MILICOM_SERVICE row is a 16-bit SIG-template 0xFFFF
--            reserved/test placeholder (CP49 standing rule explicitly
--            excludes "16-bit test placeholder").
-- Per-subclass counts:
--   - characteristic_not_service:        29 rows (SoundThinking Flock-You
--                                         rows, captured source_excerpt keys
--                                         them as GATT characteristics, not
--                                         service UUIDs)
--   - 16bit_sig_template_placeholder:     1 row  (Motorola 23051, MILICOM_
--                                         SERVICE 0xFFFF reserved/test UUID)
-- Authority: MAC-489 CTO ratification. Discovery: MAC-486 (ask #3) +
--            MAC-478 cohort re-audit pattern.
-- Out of scope: id 23046 (Dahua d54ace3f) — withdrawn by mig-0035 (MAC-486)
--            under FP class `string_pool_field` (separate from CP49
--            characteristic_not_service / 16bit_placeholder subclasses).
--            NOT folded here — would conflict with 0035 pre-guard.
-- Mechanism: CP32 §9 'withdrawn-without-successor' tri-state — set
--            superseded_by = id (self-loop) + confidence = 0; the canonical
--            active-set filter `WHERE superseded_by IS NULL` drops them
--            from the Lynceus feed. Mirror of MAC-478 mig-0034 + MAC-486
--            mig-0035. No row is deleted — full provenance + cite preserved
--            for audit (§11 #1).
-- Re-apply safety: each UPDATE pins superseded_by IS NULL; the pre-guard
--            blocks re-application (0 of 30 expected active rows remain
--            on 2nd run -> CHECK(ok=1) fails -> full rollback, zero
--            mutation). Verified on a throwaway copy: 1st run exit0
--            (30 withdrawn); 2nd run aborts.
-- json_valid: all 30 target rows notes are valid JSON (swept pre-stage);
--            json_set merges a new $.fp_supersession key, preserving all
--            existing top-level keys (§11 #17).
-- §11 envelope: #1 no fabrication (withdraws non-truth; row+cite retained) ·
--            #8 no confidence drift up (demote-to-0 is the §9 withdrawal
--            signal) · #17 carve-out audit invariant (json_set sentinel
--            key, existing notes preserved verbatim).
-- ============================================================================
-- APPLY-TIME PRECONDITION (operator): back up canonical first —
--   cp db/argus.db db/argus.db.pre_mig0036.$(date -u +%Y%m%dT%H%M%SZ) && sha256sum that copy.
-- ============================================================================

BEGIN TRANSACTION;

-- ---- strict pre-condition guard (all-or-nothing) ------------------------
-- Aborts the whole transaction unless EXACTLY 30 active target rows are
-- present right now: 29 SoundThinking (conf=85, cohort=(none), 16-bit
-- characteristic range 0x30xx-0x35xx) + 1 Motorola MILICOM_SERVICE
-- (conf=75, 0xFFFF). CHECK(ok=1) fails -> constraint error -> full rollback.
CREATE TEMP TABLE _mig0036_pre (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0036_pre(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE id IN (35636,35637,35638,35639,35640,35641,35642,35643,35644,35645,35646,35647,35648,35649,35650,35651,35652,35653,35654,35655,35656,35657,35658,35659,35660,35661,35662,35663,35664)
     AND identifier_type = 'ble_service_uuid'
     AND (json_extract(notes,'$.cohort') IS NULL OR json_extract(notes,'$.cohort') != 'cctv_installer_v1')
     AND superseded_by IS NULL
     AND confidence = 85
) = 29 AND (
  SELECT COUNT(*) FROM identifiers
   WHERE id = 23051
     AND identifier_type = 'ble_service_uuid'
     AND identifier = '0000ffff-0000-1000-8000-00805f9b34fb'
     AND superseded_by IS NULL
     AND confidence = 75
) = 1 THEN 1 ELSE 0 END;

-- [characteristic_not_service] 29 rows · values: 00003001, 00003002, 00003004,
-- 00003101, 00003102, 00003103, 00003201-00003205, 00003301-0000330A,
-- 00003401-00003403, 00003501-00003505 (all 0000XXXX-0000-1000-8000-00805f9b34fb
-- short-UUID form). Source: colonelpanichacks/flock-you
-- datasets/raven_configurations.json (Flock Safety detection tool). Captured
-- source_excerpt keys each row with `"characteristicUuid": "0000..."` (NOT
-- `serviceUuid`) — Part Number / Serial Number / MAC Address / GPS / LTE /
-- audio-upload counters / OTA failures / Identity Check / Heartbeat / etc.
-- These are GATT characteristics (data fields inside a GATT service), not
-- service UUIDs. CP13: Lynceus discovers by service UUID; characteristics
-- are feed-dropped. Mis-typed as ble_service_uuid. Same FP class as MAC-478
-- mig-0034 subclass `characteristic_not_service` (which withdrew 16 such
-- rows from cctv_installer_v1 cohort).
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-489','discovery_issue','MAC-486 ask #3',
        'cp_anchor','CP49','mig','0036_mac489_non_cohort_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','characteristic_not_service',
        'reason','GATT CHARACTERISTIC (not service UUID). Captured source_excerpt from colonelpanichacks/flock-you datasets/raven_configurations.json explicitly keys each row with the JSON field name "characteristicUuid" (NOT "serviceUuid"). Rows are Part Number / Serial Number / MAC Address / GPS Latitude/Longitude/Altitude / Board Temperature / Battery Voltage / Charge-Discharge Current / 10W Solar Voltage / Battery State / Last Connected / LTE Network Type+Operator+RSSI+RSRQ+RSRP+SINR / Last WiFi SSID / WiFi RSSI / Network Connection Status / Average Upload Time / Most Recent Upload Time / Audio Uploads Since Boot / Identity Check Failures / Status Update Failures / Heartbeat Failures / OTA Update Failures / Audio Upload Failures. These are GATT characteristic data fields inside a SoundThinking/ShotSpotter gunshot-detection device service — not advertised service UUIDs. CP13: Lynceus discovers by service UUID; characteristics are feed-dropped. Mis-typed as ble_service_uuid. CP49 standing rule: GATT *characteristic* is not a valid binding for the ble_service_uuid type. Same FP class as MAC-478 mig-0034 subclass `characteristic_not_service` (16 cctv_installer_v1 rows withdrawn there).',
        'source_artifact','colonelpanichacks/flock-you datasets/raven_configurations.json (commit 64f9b9e7cf116b6c40af8d4def85e4eebc1f28f8)',
        'source_manufacturer','SoundThinking',
        'source_device','SoundThinking/ShotSpotter Raven (gunshot detection)',
        'prior_confidence', 85,
        'date','2026-06-20'))
WHERE id IN (35636,35637,35638,35639,35640,35641,35642,35643,35644,35645,35646,35647,35648,35649,35650,35651,35652,35653,35654,35655,35656,35657,35658,35659,35660,35661,35662,35663,35664)
  AND identifier_type = 'ble_service_uuid'
  AND (json_extract(notes,'$.cohort') IS NULL OR json_extract(notes,'$.cohort') != 'cctv_installer_v1')
  AND superseded_by IS NULL;

-- [16bit_sig_template_placeholder] 1 row · value: 0000ffff-0000-1000-8000-00805f9b34fb
-- Source: com.motorolasolutions.wave (Motorola Solutions WAVE PTT, v3.1.8.47141).
-- Captured source_excerpt: `MILICOM_SERVICE 16-bit SIG-template (0xFFFF) in
-- BluetoothLowEnergyPttValues.populateUUIDs() — observable in BLE scans only
-- when paired with MILICOM_PRESS/RELEASE byte command sequence`. The 0xFFFF
-- value is a reserved/test placeholder in the Bluetooth SIG assigned-numbers
-- 16-bit UUID space (0xFFFF is reserved; never assigned to a real service).
-- Notes role=service_sig_template_16bit explicitly flags this as a non-service
-- template. CP49 standing rule explicitly excludes "16-bit test placeholder".
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-489','discovery_issue','MAC-486 ask #3',
        'cp_anchor','CP49','mig','0036_mac489_non_cohort_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','16bit_sig_template_placeholder',
        'reason','MILICOM_SERVICE 16-bit SIG-template (0xFFFF) reserved/test placeholder in BluetoothLowEnergyPttValues.populateUUIDs() (com.motorolasolutions.wave v3.1.8.47141). 0xFFFF is a RESERVED 16-bit UUID in the Bluetooth SIG assigned-numbers service-discovery space; it is never assigned to a real service and is used here as a paired-command template (observable in BLE scans only when paired with MILICOM_PRESS/RELEASE byte command sequence, not as a standalone service advertisement). Notes role=service_sig_template_16bit flags this as a non-service template. CP49 standing rule explicitly excludes "16-bit test placeholder". Brief seed (CTO inline): `id 23051 — MILICOM_SERVICE 16-bit SIG-template (0xFFFF) placeholder (reserved/test UUID) — candidate FP`.',
        'source_artifact','com.motorolasolutions.wave v3.1.8.47141 (apk_sha256 24b01b218052430c2b40a103827937fc4e58b7f4378a099fc6768a83dfc7e897, MAC-104b source dispatch)',
        'source_manufacturer','Motorola Solutions',
        'source_device','Motorola Solutions WAVE PTT (BluetoothLowEnergyPttValues MILICOM_SERVICE template)',
        'paired_row_disposition', json_object(
            'paired_id', 23048,
            'paired_identifier', '2320ae58-8394-4652-95f7-0a872ac0958f',
            'paired_status', 'KEEP (separate row; has explicit GATT service binding via milicomServiceId field name)'),
        'prior_confidence', 75,
        'date','2026-06-20'))
WHERE id = 23051
  AND identifier_type = 'ble_service_uuid'
  AND identifier = '0000ffff-0000-1000-8000-00805f9b34fb'
  AND superseded_by IS NULL;

-- ---- strict post-condition guard ---------------------------------------
-- Exactly 30 target rows now withdrawn (superseded_by=id, conf=0). The
-- 30 = 29 SoundThinking (conf=85 -> 0) + 1 Motorola (conf=75 -> 0).
-- Scoped to the 30 id-set only (decoupled from mig-0034/0035 ordering).
-- Else abort.
CREATE TEMP TABLE _mig0036_post (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0036_post(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE id IN (35636,35637,35638,35639,35640,35641,35642,35643,35644,35645,35646,35647,35648,35649,35650,35651,35652,35653,35654,35655,35656,35657,35658,35659,35660,35661,35662,35663,35664,23051)
     AND identifier_type = 'ble_service_uuid'
     AND superseded_by = id
     AND confidence = 0
) = 30 THEN 1 ELSE 0 END;

DROP TABLE _mig0036_pre;
DROP TABLE _mig0036_post;

COMMIT;

-- Post-apply expected state:
--   30 non-cohort ble_service_uuid rows: superseded_by=id, confidence=0 —
--   dropped from the Lynceus feed (active-set filter WHERE superseded_by IS NULL).
--   Per-subclass:
--     characteristic_not_service: 29 (SoundThinking, was conf=85)
--     16bit_sig_template_placeholder: 1 (Motorola 23051, was conf=75)
--   Companion migration effects:
--     - mig-0034 (MAC-478, 77 cctv_installer_v1 cohort FPs) — decoupled.
--     - mig-0035 (MAC-486, 1 out-of-cohort id 23046) — decoupled.
--   After all three migrations land: 23+1 SoundThinking characteristic FPs +
--   0xFFFF placeholder removed; id 23046 (Dahua d54ace3f) also removed by 0035.
