-- ============================================================================
-- Migration 0026 — Phase 10b sid=13 mis-binding rebind: vendor APK source admissions
-- ============================================================================
--
-- Authority chain:
--   MAC-1 → MAC-52 → CP12 → CP13 (migration 0009 manufacturer_app enum)
--   → MAC-178 wave-G v2 integration (per-row staged with correct per-row notes)
--   → MAC-202 schema-binding investigation (Hypothesis C disposition ratified)
--   → MAC-204 (this migration) — admit-then-rebind
--
-- Discipline envelope:
--   §11 #1 paste-not-cite verified — see _phase_10_schema_anomaly/rebind_heartbeat.md
--   §11 #7 violations OK — this is a CEO-ratified disposition application, not a
--   policy invention.
--
-- Phase-1 procurement-record question (legacy §4.5 callout): N/A here — these are
-- legitimate manufacturer_app rows with proper per-row identifier provenance; the
-- admission gap is mid-pipeline (no sister source row was admitted before the
-- batch INSERT). CP32 candidate is to make admit-source-row-before-batch-insert
-- a hard ingest precondition (carry-forward note in heartbeat; CP32 itself is
-- not landing here).
--
-- Selection rationale (Hypothesis C, not A or B):
--   - Hypothesis A (rebind to existing sister sources) — not directly executable:
--     no sister source exists for any of the 5 packages (verified via name/url/
--     notes LIKE against all of sources prior to this migration).
--   - Hypothesis B (rewrite sid=13's metadata to match observations) — rejected:
--     sid=13's authored metadata (com.flocksafety.hazyhiwire@2.4.0, Wave G pre-v1
--     admission 2026-05-10, doc #14 in CREDITS.md draft) is legitimate single-APK
--     authorship and is referenced by chronological landing records — rewriting
--     in place would corrupt the original Flock Safety attestation.
--   - Hypothesis C (this migration) — admit 5 new manufacturer_app sources whose
--     authored metadata matches each vendor's per-row notes, then rebind
--     raw_observations.source_id from 13 → assigned new sid. Per-row notes already
--     carry correct apk_package/apk_sha256/apk_version, so the data is conserved
--     across this migration's two-step (admit + rebind).
--
-- Idempotency:
--   - INSERT OR IGNORE on UNIQUE(url) → rerunning this migration after success
--     produces zero changes (each url is unique per vendor APK package).
--   - The rebind UPDATE statements live in the integration commit, NOT this
--     migration, to keep migration scope narrowly schema/seed only (and to make
--     re-applicability of the migration trivially safe even on a partially-
--     rolled-back DB).
--
-- License posture (mirrors sid=13/sid=14 Wave G pre-v1 envelope):
--   proprietary; static analysis only under 17 USC §1201(j) + 37 CFR §201.40(b);
--   no source code redistribution; identifier values only; DMCA §1201 envelope.
--
-- ============================================================================

-- Hikvision Hik-Connect
INSERT OR IGNORE INTO sources (name, url, source_type, tier, last_status, notes) VALUES (
    'Hikvision Hik-Connect (com.hikvision.hikconnect@6.11.631.0506)',
    'https://apkpure.com/hik-connect/com.hikvision.hikconnect',
    'manufacturer_app',
    3,
    'success',
    json('{"session_admission":"wave_g_v2","admission_date_utc":"2026-05-10","package":"com.hikvision.hikconnect","package_role":"operator with installer ble code path (Hik-Connect operator-facing app embeds installer BLE pairing path)","version":"6.11.631.0506","download_channel":"apk-pure (via apkeep 1.0.0 from EFForg)","apk_sha256":"6ee6129f5a9f108f79342790f8d7e89a18f7ed1405492792b39078e27d7ed349","cohort_classification":"operator_with_installer_ble_code_path","static_analysis_framework":"17 USC §1201(j) + 37 CFR §201.40(b)","eula_posture":"standard-RE-clause","license":"proprietary (vendor app under standard-RE-clause posture; static analysis only; DMCA §1201 envelope)","license_attribution":"Hikvision Hik-Connect (com.hikvision.hikconnect@6.11.631.0506); ingested via static analysis under standard-RE-clause posture; no source code redistribution; identifier values only.","authority_chain":"MAC-1 → MAC-52 → CP12 → CP13 (migration 0009 manufacturer_app enum) → MAC-104 admission → MAC-178 integration → MAC-202 disposition → MAC-204 (this migration)","admission_dispatch_ref":"MAC-104","integration_dispatch_ref":"MAC-178","schema_binding_rebind_ref":"MAC-204","mac202_disposition":"hypothesis_c_admit_then_rebind"}')
);

-- Dahua DMSS
INSERT OR IGNORE INTO sources (name, url, source_type, tier, last_status, notes) VALUES (
    'Dahua DMSS (com.mm.android.DMSS@2.4.14)',
    'https://apkpure.com/dmss/com.mm.android.DMSS',
    'manufacturer_app',
    3,
    'success',
    json('{"session_admission":"wave_g_v2","admission_date_utc":"2026-05-10","package":"com.mm.android.DMSS","package_role":"operator + likely installer (DMSS is Dahua''s primary mobile control app, used for both end-user view and tech-assisted onboarding)","version":"2.4.14","download_channel":"apk-pure (via apkeep 1.0.0 from EFForg)","apk_sha256":"d30abda0495351d3bd6b7345aa4c89fff5b135a28a7c002073dcd295da9e1efb","cohort_classification":"operator_plus_likely_installer","static_analysis_framework":"17 USC §1201(j) + 37 CFR §201.40(b)","eula_posture":"standard-RE-clause","license":"proprietary (vendor app under standard-RE-clause posture; static analysis only; DMCA §1201 envelope)","license_attribution":"Dahua DMSS (com.mm.android.DMSS@2.4.14); ingested via static analysis under standard-RE-clause posture; no source code redistribution; identifier values only.","authority_chain":"MAC-1 → MAC-52 → CP12 → CP13 (migration 0009 manufacturer_app enum) → MAC-104 admission → MAC-178 integration → MAC-202 disposition → MAC-204 (this migration)","admission_dispatch_ref":"MAC-104","integration_dispatch_ref":"MAC-178","schema_binding_rebind_ref":"MAC-204","mac202_disposition":"hypothesis_c_admit_then_rebind"}')
);

-- Motorola Solutions WAVE PTT
INSERT OR IGNORE INTO sources (name, url, source_type, tier, last_status, notes) VALUES (
    'Motorola Solutions WAVE PTT (com.motorolasolutions.wave@3.1.8.47141)',
    'https://apkpure.com/wave-ptt/com.motorolasolutions.wave',
    'manufacturer_app',
    3,
    'success',
    json('{"session_admission":"wave_g_v2","admission_date_utc":"2026-05-10","package":"com.motorolasolutions.wave","package_role":"installer / first-responder configuration app for Motorola WAVE push-to-talk handhelds and gateways","version":"3.1.8.47141","download_channel":"apk-pure (via apkeep 1.0.0 from EFForg)","apk_sha256":"24b01b218052430c2b40a103827937fc4e58b7f4378a099fc6768a83dfc7e897","cohort_classification":"installer","static_analysis_framework":"17 USC §1201(j) + 37 CFR §201.40(b)","eula_posture":"standard-RE-clause","license":"proprietary (vendor app under standard-RE-clause posture; static analysis only; DMCA §1201 envelope)","license_attribution":"Motorola Solutions WAVE PTT (com.motorolasolutions.wave@3.1.8.47141); ingested via static analysis under standard-RE-clause posture; no source code redistribution; identifier values only.","authority_chain":"MAC-1 → MAC-52 → CP12 → CP13 (migration 0009 manufacturer_app enum) → MAC-104b admission → MAC-178 integration → MAC-202 disposition → MAC-204 (this migration)","admission_dispatch_ref":"MAC-104b","integration_dispatch_ref":"MAC-178","schema_binding_rebind_ref":"MAC-204","mac202_disposition":"hypothesis_c_admit_then_rebind"}')
);

-- Parrot FreeFlight 6
INSERT OR IGNORE INTO sources (name, url, source_type, tier, last_status, notes) VALUES (
    'Parrot FreeFlight 6 (com.parrot.freeflight6@6.7.6)',
    'https://apkpure.com/freeflight-6/com.parrot.freeflight6',
    'manufacturer_app',
    3,
    'success',
    json('{"session_admission":"wave_g_v2","admission_date_utc":"2026-05-10","package":"com.parrot.freeflight6","package_role":"installer + operator (FreeFlight 6 binds Parrot drones during setup and is the primary flight-control / RID configuration surface)","version":"6.7.6","download_channel":"apk-pure (via apkeep 1.0.0 from EFForg)","apk_sha256":"a105b0815e26c46f2e8ff4d9f3f83509c0b1e5e4f0731df8775681657f18db73","cohort_classification":"installer_plus_operator","static_analysis_framework":"17 USC §1201(j) + 37 CFR §201.40(b)","eula_posture":"standard-RE-clause","license":"proprietary (vendor app under standard-RE-clause posture; static analysis only; DMCA §1201 envelope)","license_attribution":"Parrot FreeFlight 6 (com.parrot.freeflight6@6.7.6); ingested via static analysis under standard-RE-clause posture; no source code redistribution; identifier values only.","authority_chain":"MAC-1 → MAC-52 → CP12 → CP13 (migration 0009 manufacturer_app enum) → MAC-104d admission → MAC-178 integration → MAC-202 disposition → MAC-204 (this migration)","admission_dispatch_ref":"MAC-104d","integration_dispatch_ref":"MAC-178","schema_binding_rebind_ref":"MAC-204","mac202_disposition":"hypothesis_c_admit_then_rebind"}')
);

-- DJI Industry Pilot (RTK / enterprise tier)
INSERT OR IGNORE INTO sources (name, url, source_type, tier, last_status, notes) VALUES (
    'DJI Industry Pilot (com.dji.industry.pilot@v1.9.0)',
    'https://apkpure.com/dji-industry-pilot/com.dji.industry.pilot',
    'manufacturer_app',
    3,
    'success',
    json('{"session_admission":"wave_g_v2","admission_date_utc":"2026-05-10","package":"com.dji.industry.pilot","package_role":"operator + installer (DJI Pilot industry edition — enterprise RTK / Matrice / Mavic 3 Enterprise control surface)","version":"v1.9.0","download_channel":"apk-pure (via apkeep 1.0.0 from EFForg)","apk_sha256":"9334b0474300e24ca44209ef5a60eb7cc58b1a7637c4d4954bc09668b16812be","cohort_classification":"operator_plus_installer","static_analysis_framework":"17 USC §1201(j) + 37 CFR §201.40(b)","eula_posture":"standard-RE-clause","license":"proprietary (vendor app under standard-RE-clause posture; static analysis only; DMCA §1201 envelope)","license_attribution":"DJI Industry Pilot (com.dji.industry.pilot@v1.9.0); ingested via static analysis under standard-RE-clause posture; no source code redistribution; identifier values only.","authority_chain":"MAC-1 → MAC-52 → CP12 → CP13 (migration 0009 manufacturer_app enum) → MAC-104 admission → MAC-178 integration → MAC-202 disposition → MAC-204 (this migration)","admission_dispatch_ref":"MAC-104","integration_dispatch_ref":"MAC-178","schema_binding_rebind_ref":"MAC-204","mac202_disposition":"hypothesis_c_admit_then_rebind"}')
);
