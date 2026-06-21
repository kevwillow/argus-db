-- ============================================================================
-- Script:    0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession.sql
-- Status:    STAGED — NOT APPLIED. Lands ONLY at the MAC-477 board gate.
--            Drop into db/migrations/0034_*.sql at apply time (slot 0034 is
--            free — verified by direct working-tree read; highest live = 0033).
-- Purpose:   Withdraw 77 false-positive `ble_service_uuid` rows wrongly admitted
--            into cohort `cctv_installer_v1` (cycle wave_g_h_v1_integration) by
--            bare string-pool UUID grep. 8 Avigilon MSAL (pre-confirmed MAC-476)
--            + 69 re-audit FPs (non-BLE constants / wrong-binding characteristics).
-- Authority: MAC-478 CTO re-audit. Discovery: MAC-476 ratification.
-- Keeps:     8 rows of the 1 genuine GATT service UUID f6ec37db-...-561d
--            (ids 36588,36591,36597,36600,36603,36609,36612,36615) — untouched.
-- Mechanism: CP32 §9 'withdrawn-without-successor' tri-state — set
--            superseded_by = id (self-loop) + confidence = 0; the canonical
--            active-set filter `WHERE superseded_by IS NULL` drops them from the
--            Lynceus feed. Precedent: MAC-217 Track B PII demotes. No row is
--            deleted — full provenance + cite is preserved for audit (§11 #1).
-- Re-apply safety: each UPDATE pins superseded_by IS NULL, and the pre-guard
--            blocks re-application (only 0 of 77 expected active rows remain ->
--            CHECK(ok=1) fails -> full rollback, zero mutation). Verified on a
--            throwaway copy: 1st run exit0 (8 keep / 77 withdrawn); 2nd run aborts.
-- json_valid: all 85 cohort notes are valid JSON (swept pre-stage); json_set
--            merges a new $.fp_supersession key, preserving existing keys (§11 #17).
-- §11 envelope: #1 no fabrication (withdraws non-truth; row+cite retained) ·
--            #8 no confidence drift up (demote-to-0 is the §9 withdrawal signal) ·
--            #17 carve-out audit invariant (json_set sentinel key, existing notes
--            preserved verbatim).
-- OUT OF SCOPE (flagged, follow-up): pre-existing entangled row id 23046
--            (Dahua d54ace3f, §8.3-paired to active id 27426) keeps that one
--            value in the feed until separately superseded. NOT folded here —
--            an entangled cross-axis row needs its own pairing re-eval.
-- ============================================================================
-- APPLY-TIME PRECONDITION (operator): back up canonical first —
--   cp db/argus.db db/argus.db.pre_mig0034.$(date -u +%Y%m%dT%H%M%SZ) && sha256sum that copy.
-- ============================================================================

BEGIN TRANSACTION;

-- ---- strict pre-condition guard (all-or-nothing) ------------------------
-- Aborts the whole transaction unless EXACTLY 77 active, conf=85, in-cohort
-- target rows are present right now (CHECK(ok=1) fails -> constraint error).
CREATE TEMP TABLE _mig0034_pre (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0034_pre(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE id IN (36589,36590,36592,36593,36594,36595,36596,36598,36599,36601,36602,36604,36605,36606,36607,36608,36610,36611,36613,36614,36616,36617,36618,36619,36620,36621,36626,36627,36628,36629,36630,36631,36633,36634,36635,36636,36637,36638,36639,36640,36641,36642,36643,36644,36645,36646,36647,36648,36649,36650,36651,36652,36653,36654,36655,36656,36657,36658,36659,36660,36661,36662,36663,36664,36665,36666,36667,36668,36669,36670,36672,36673,36674,36675,36676,36677,36678)
     AND identifier_type='ble_service_uuid'
     AND json_extract(notes,'$.cohort')='cctv_installer_v1'
     AND superseded_by IS NULL AND confidence=85
) = 77 THEN 1 ELSE 0 END;

-- [characteristic_not_service] 16 rows · values: af20fbac-2518-4998-9af7-af42540731b3, af20fbac-2518-4998-9af7-af42540731b4
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','characteristic_not_service',
        'reason','GATT CHARACTERISTIC (getCharacteristic(...)), not a service UUID. CP13: Lynceus discovers by service UUID; characteristics are feed-dropped. Mis-typed as ble_service_uuid.',
        'date','2026-06-19'))
WHERE id IN (36589,36590,36592,36593,36598,36599,36601,36602,36604,36605,36610,36611,36613,36614,36616,36617)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [doc_url_guid] 6 rows · values: 1aa0ec25-954c-4e73-8371-386f9b8184a1
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','doc_url_guid',
        'reason','Help-doc HTML filename GUID (GUID-1AA0EC25-...html) in arouter ActivityUtilsServiceImpl. Non-BLE.',
        'date','2026-06-19'))
WHERE id IN (36594,36595,36596,36618,36619,36620)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [asset_filename] 2 rows · values: 5a8a3ad7-78a2-4a6b-b713-946637f7f554
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','asset_filename',
        'reason','Image asset filename (assets/images/5A8A3AD7-...png). Non-BLE.',
        'date','2026-06-19'))
WHERE id IN (36606,36607)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [push_payload] 1 rows · values: 4b5868d0-63be-11f0-8000-aa1d8e44bfb4
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','push_payload',
        'reason','Push-message CSV payload field in HcPushReceiverHandler. Non-BLE.',
        'date','2026-06-19'))
WHERE id IN (36608)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [upload_token] 1 rows · values: f85299bc-d1b3-11f0-9b91-0242ac11000d
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','upload_token',
        'reason','Upload token string (qam-for-app-f85299bc-...) in DevFileUploader. Non-BLE.',
        'date','2026-06-19'))
WHERE id IN (36621)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [ci_build_host] 2 rows · values: 7634ec5f-11ac-4d0f-ac92-2fe172437739
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','ci_build_host',
        'reason','Travis CI build-host job id (rxjava.properties Build-Host=travis-job-7634ec5f-...). Build artifact, non-BLE.',
        'date','2026-06-19'))
WHERE id IN (36626,36631)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [string_pool_field] 4 rows · values: 9782022b-32ca-4346-832e-779db180cf4b, d54ace3f-8e27-4718-aa17-019f0e318e14
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','string_pool_field',
        'reason','Bare private String field in com.mm.buss.commonmodule.device.d. No GATT service binding captured (admission burden unmet). NOTE: same value also lives out-of-cohort as active id 23046 (entangled §8.3 pair) -> separate follow-up; value stays in feed until that lands.',
        'date','2026-06-19'))
WHERE id IN (36627,36628,36629,36630)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [auth_key] 2 rows · values: bf38d296-fae7-31c8-bfd4-3f60ca5a52e6
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','auth_key',
        'reason','Auth constant PIAKey in AuthenticationPreferences. Non-BLE.',
        'date','2026-06-19'))
WHERE id IN (36633,36640)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [rbac_role_id] 6 rows · values: db231d97-107c-4292-a036-78a491c2fe06, e7acfed7-4196-43a7-89b6-3512ebbeff19, f7fe7e93-f741-4c06-bbc8-f4989d4d94d0
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','rbac_role_id',
        'reason','RBAC UserRole id (ADMIN) in connectapi.UserRole. Non-BLE.',
        'date','2026-06-19'))
WHERE id IN (36634,36635,36636,36637,36638,36639)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [aws_arn] 12 rows · values: 103d9fa3-fbb5-46ae-87e5-18d43978b593, 53272adb-37be-4ccb-b8d4-991bbc675bb1, 88a570cc-f103-4d0b-b41e-014203163326, 8a1d1027-ac73-4cd7-a851-cb8aff0c6494
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','aws_arn',
        'reason','AWS ARN resource-group id (generated Swagger MES model). Non-BLE.',
        'date','2026-06-19'))
WHERE id IN (36641,36642,36643,36644,36645,36646,36647,36648,36649,36650,36651,36652)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [app_domain_id] 14 rows · values: 78988e14-2cba-4b69-a0f0-c89b31e3db1d, 962ba181-4591-404a-833e-46d6aae2967e, bb0990cc-5e84-4503-a438-a0138df04bd5, dbf464c1-b43c-4966-bd11-67eb3e5bca27
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','app_domain_id',
        'reason','FeedbackLabel value-class id (Verkada feedback UI). Non-BLE.',
        'date','2026-06-19'))
WHERE id IN (36653,36654,36655,36656,36657,36658,36659,36660,36661,36662,36673,36674,36675,36676)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [msal_constant] 8 rows · values: 87749df4-7ccf-48f8-aa87-704bad0e0e16, 9188040d-6c67-4c5b-b112-36a304b66dad
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','msal_constant',
        'reason','Microsoft MSAL MSA_MEGA_TENANT_ID (Azure AD). Non-BLE, not Avigilon-owned. Pre-confirmed FP at MAC-476 baksmali.',
        'date','2026-06-19'))
WHERE id IN (36663,36664,36665,36666,36667,36668,36669,36670)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- [bt_classic_rfcomm] 3 rows · values: eb3e0af3-57f4-4789-ab55-86508580296a
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-478','discovery_issue','MAC-476',
        'cp_anchor','CP49','mig','0034_mac478_cctv_installer_v1_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','bt_classic_rfcomm',
        'reason','UUID_RFCOMM = Bluetooth CLASSIC SPP constant in 3rd-party Alibaba AILabs IoT SDK (com.alibaba.ailabs.iot.aisbase.Constants). Not a BLE GATT service UUID.',
        'date','2026-06-19'))
WHERE id IN (36672,36677,36678)
  AND identifier_type='ble_service_uuid'
  AND json_extract(notes,'$.cohort')='cctv_installer_v1'
  AND superseded_by IS NULL;

-- ---- strict post-condition guard ---------------------------------------
-- Exactly 77 cohort rows now withdrawn (superseded_by=id, conf=0) AND exactly
-- 8 cohort rows remain active (the f6ec37db KEEPs). Else abort.
CREATE TEMP TABLE _mig0034_post (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0034_post(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE identifier_type='ble_service_uuid'
     AND json_extract(notes,'$.cohort')='cctv_installer_v1'
     AND superseded_by = id AND confidence = 0
) = 77 AND (
  SELECT COUNT(*) FROM identifiers
   WHERE identifier_type='ble_service_uuid'
     AND json_extract(notes,'$.cohort')='cctv_installer_v1'
     AND superseded_by IS NULL
) = 8 THEN 1 ELSE 0 END;

DROP TABLE _mig0034_pre;
DROP TABLE _mig0034_post;

COMMIT;

-- Post-apply expected state:
--   cohort active ble_service_uuid rows: 8 (all f6ec37db) — feed shows 1 entry.
--   cohort withdrawn rows: 77 (superseded_by=id, confidence=0).
--   Lynceus feed: 23 of 24 cohort FP service-UUID values removed; d54ace3f
--   persists via out-of-cohort id 23046 until its follow-up supersession lands.
