-- ============================================================================
-- Script:    0035_mac486_dahua_d54ace3f_ble_service_uuid_fp_supersession.sql
-- Status:    STAGED — NOT APPLIED. Lands ONLY at the MAC-477 board gate,
--            alongside MAC-478 mig-0034. Drop into db/migrations/0035_*.sql at
--            apply time (slot 0035 is free — verified by direct working-tree
--            read; highest live = 0033, 0034 reserved by MAC-478).
-- Ordering:  Decoupled from 0034 — this migration touches ONLY out-of-cohort
--            id 23046 and asserts only about id 23046, so it is correct in
--            either apply order. (0034 withdraws cohort rows 36627/36629; this
--            withdraws the entangled out-of-cohort sibling that carries the
--            same value into the feed.)
-- Purpose:   Withdraw 1 pre-existing false-positive `ble_service_uuid` row
--            (id 23046, Dahua d54ace3f-8e27-4718-aa17-019f0e318e14, cctv_camera,
--            confidence 92, active). Source: com.mm.android.DMSS APK. The
--            captured cite is a bare obfuscated string-pool FIELD
--            (`public String f54889f = "d54ace3f-..."` in sources/en/f.java:30)
--            — NO GATT service binding. Same FP class as MAC-478 cohort rows
--            36627/36629 (subclass string_pool_field). This is the 24th of 24
--            cohort `d54ace3f` value: mig-0034 withdraws the two cohort copies
--            but §8.3 dedup leaves d54ace3f live in the Lynceus feed via THIS
--            out-of-cohort row. Withdrawing 23046 removes d54ace3f from the feed
--            entirely.
-- Authority: MAC-486 CTO ratification. Discovery: MAC-478 cctv_installer_v1
--            re-audit (spun out — entangled §8.3 cross-axis pairing made folding
--            it into mig-0034 an unreviewed one-way door).
-- §8.3 note: id 23046 was lifted 87->92 via MAC-190/CP24 "§8.3 cross_axis_lift"
--            pair=(27426,23046): hostname api.dahuasecurity.com (id 27426,
--            vendor_controlled_hostname_deprecated) corroborating a BLE UUID.
--            That lift was itself a hub-and-spoke misapplication (SAME vendor,
--            DIFFERENT identifier types != value-level corroboration across
--            independent issuers). Moot here — the row is withdrawn wholesale
--            (confidence -> 0), so the +5 lift is discarded, not unwound.
-- 27426:     RE-EVALUATED, no correction. id 27426.notes."§8.3_lift_applied" =
--            false (cite-paste verified) — the lift was UNIDIRECTIONAL
--            (27426 -> 23046). id 27426 was the corroborator, never a recipient;
--            its confidence 87 stands on CP29 §2 deprecated-default band (80-87,
--            NXDOMAIN-verified Wave I.6) independent of this pairing. Withdrawing
--            23046 does NOT drop 27426. 27426 is untouched by this migration.
-- Mechanism: CP32 §9 'withdrawn-without-successor' tri-state — set
--            superseded_by = id (self-loop) + confidence = 0; the canonical
--            active-set filter `WHERE superseded_by IS NULL` drops it from the
--            Lynceus feed. Mirror of MAC-478 mig-0034. No row is deleted — full
--            provenance + cite preserved for audit (§11 #1).
-- Re-apply safety: the UPDATE pins superseded_by IS NULL; the pre-guard blocks
--            re-application (0 of 1 expected active rows remain on 2nd run ->
--            CHECK(ok=1) fails -> full rollback, zero mutation). Verified on a
--            throwaway copy: 1st run exit0 (1 withdrawn); 2nd run aborts.
-- json_valid: id 23046 notes is valid JSON (swept pre-stage, json_valid=1);
--            json_set merges a new $.fp_supersession key, preserving all 17
--            existing top-level keys (§11 #17).
-- §11 envelope: #1 no fabrication (withdraws non-truth; row+cite retained) ·
--            #8 no confidence drift up (demote-to-0 is the §9 withdrawal signal) ·
--            #17 carve-out audit invariant (json_set sentinel key, existing notes
--            preserved verbatim).
-- ============================================================================
-- APPLY-TIME PRECONDITION (operator): back up canonical first —
--   cp db/argus.db db/argus.db.pre_mig0035.$(date -u +%Y%m%dT%H%M%SZ) && sha256sum that copy.
-- ============================================================================

BEGIN TRANSACTION;

-- ---- strict pre-condition guard (all-or-nothing) ------------------------
-- Aborts the whole transaction unless EXACTLY 1 active, conf=92, matching
-- target row is present right now (CHECK(ok=1) fails -> constraint error).
CREATE TEMP TABLE _mig0035_pre (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0035_pre(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE id = 23046
     AND identifier_type = 'ble_service_uuid'
     AND identifier = 'd54ace3f-8e27-4718-aa17-019f0e318e14'
     AND superseded_by IS NULL
     AND confidence = 92
) = 1 THEN 1 ELSE 0 END;

-- [string_pool_field] 1 row · value: d54ace3f-8e27-4718-aa17-019f0e318e14
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-486','discovery_issue','MAC-478',
        'cp_anchor','CP49','mig','0035_mac486_dahua_d54ace3f_ble_service_uuid_fp_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'subclass','string_pool_field',
        'reason','Bare obfuscated private String field (public String f54889f = "d54ace3f-..." in sources/en/f.java:30) in com.mm.android.DMSS. No GATT service binding captured (admission burden unmet under CP49). Same FP class and same value as MAC-478 cohort rows 36627/36629 (subclass string_pool_field). 24th of 24 cohort d54ace3f value: mig-0034 withdraws the cohort copies; this out-of-cohort row is what kept d54ace3f in the feed via §8.3 dedup. Withdrawal removes d54ace3f from the Lynceus feed entirely.',
        'prior_confidence', 92,
        'lift_discarded', json_object(
            'prior_lift','87->92 via MAC-190/CP24 §8.3 cross_axis_lift pair=(27426,23046)',
            'lift_validity','hub_and_spoke_misapplication: vendor hostname (id 27426 api.dahuasecurity.com) + BLE UUID (id 23046 d54ace3f) = SAME vendor, DIFFERENT identifier types, NOT value-level corroboration across independent issuers',
            'note','moot — row withdrawn wholesale (confidence 0), lift discarded not unwound'),
        'paired_row_27426_disposition', json_object(
            'action','no_correction',
            'cite','id 27426.notes."§8.3_lift_applied"=false; lift was unidirectional 27426->23046',
            'rationale','27426 was the corroborator, never a recipient; confidence 87 stands on CP29 §2 deprecated-default band (80-87, NXDOMAIN-verified) independent of this pairing. Withdrawing 23046 does not drop 27426.'),
        'date','2026-06-20'))
WHERE id = 23046
  AND identifier_type = 'ble_service_uuid'
  AND identifier = 'd54ace3f-8e27-4718-aa17-019f0e318e14'
  AND superseded_by IS NULL;

-- ---- strict post-condition guard ---------------------------------------
-- Exactly id 23046 now withdrawn (superseded_by=id, conf=0). Scoped to 23046
-- only (decoupled from mig-0034 ordering). Else abort.
CREATE TEMP TABLE _mig0035_post (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0035_post(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE id = 23046
     AND identifier_type = 'ble_service_uuid'
     AND superseded_by = 23046
     AND confidence = 0
) = 1 THEN 1 ELSE 0 END;

DROP TABLE _mig0035_pre;
DROP TABLE _mig0035_post;

COMMIT;

-- Post-apply expected state:
--   id 23046: superseded_by=23046, confidence=0 — dropped from Lynceus feed.
--   With mig-0034 also applied: 0 active rows carry d54ace3f -> value fully
--   removed from the feed (24 of 24 cohort FP service-UUID values gone).
--   id 27426: UNCHANGED (confidence 87) — re-evaluated, no correction warranted.
