#!/usr/bin/env python3
"""
MAC-181 §8.8 — Wave H pre-v1 DB promotion (one-shot).

Lands the Wave H desktop-axis pre-v1 wave into the canonical DB:
  - 1 sources row (sid=53; vendor_documentation tier-1; CP15 ceiling)
  - 5 raw_observations rows (deduped per unique vendor-binary-value tuple)
  - 4 identifiers rows (CP28(c) sub-band ladder; §11 #8 single-source)
  - 5 documented_absence entries on existing manufacturer rows
  - 2 stub manufacturer admissions per MAC-178 P5 precedent
    (Eagle Eye Networks + Rhombus Systems; absence-only)

Idempotent: re-running over an already-applied state is a no-op (uses
INSERT OR IGNORE on natural keys + a check on existing rows).

Authority chain: MAC-181 cycle dispatch (§8.8 of the issue body); CEO
disposition on MAC-177 comment 0d15de7b §7 "approve full path"; CP28
amendment-log binding via BIBLE_AMENDMENTS.md.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = '/home/kev/argus/db/argus.db'
WAVE_H_DIR = '/home/kev/argus/extraction_outputs/wave_h_pre_v1'

NOW_UTC = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def insert_wave_h_source(cur):
    """Insert the Wave H sources row per HANDOFF §9."""
    name = 'Vendor Desktop Application Static Analysis — Wave H'
    cur.execute('SELECT id FROM sources WHERE name = ?', (name,))
    existing = cur.fetchone()
    if existing:
        print(f'  sources: row already exists at id={existing[0]} (idempotent skip)')
        return existing[0]

    notes_json = {
        'session_admission': 'wave_h_pre_v1',
        'session_count': 2,
        'admission_date_utc': '2026-05-18T00:00:00Z',
        'admission_dispatch_ref': 'MAC-181',
        'authority_chain': 'MAC-1 → … → MAC-177 disposition comment-0d15de7b §7 → MAC-181 (v1.3.0 release sweep)',
        'runguide_canonical_path': 'android_test/WAVE_H_RUNGUIDE.md',
        'wrapper_canonical_path': 'android_test/tools/extraction/wave_h_wrapper.py',
        'extraction_outputs_canonical_path': 'extraction_outputs/wave_h_pre_v1/',
        'cycle_completion_state': 'partial_cohort_set_complete',
        'next_cycle_dispatch_scheduled_for_utc': 'TBD_post_v1_3_0',
        'partial_yield_metrics_at_admission': {
            'cohorts_calibration_closed': [
                'D_drone_firmware_tooling (empirical-maximum record: 1 independent vendor + cross-product + 1 documented_absence + 1 FP control)'
            ],
            'cohorts_calibration_open': [
                'F_sanctioned_vendor (vendor 1 only — Hikvision; vendor 2 acquisition still blocked at Dahua/Uniview Cloudflare)'
            ],
            'cohorts_descoped': ['A_electron (CP17 thesis-finding-driven)'],
            'cohorts_not_started': [
                'B_dotnet', 'C_native_cpp', 'E_firmware_images',
                'G_adjacent_vms', 'H_forensics_acoustic_drone_detection',
            ],
            'vendors_processed_with_real_extraction': 3,
            'vendors_documented_absence': 7,
            'binaries_acquired': 4,
            'candidates_total_post_audit': 133,
            'candidates_by_class_post_audit': {
                'ble_service_uuid_unique': 1,
                'ble_service_uuid_after_cp26_8_reclass': 0,
                'product_family': 4,
                'snmp_enterprise_oid_unique_pre_validator_pass': 24,
                'update_endpoint_url_unique_pre_validator_pass': 5,
            },
            'fp_findings_total': 188,
            'sar_12_fp_classes_codified': [
                'WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS',
                'WINDOWS_COM_INTERFACE_GUIDS',
                'WINDOWS_DEVCLASS_SETUP_GUIDS',
                'LIBUSB_ASCII_IDENTIFIERS',
                'THIRD_PARTY_DLL_PATH_PREFIXES',
                'WINDOWS_SXS_PUBLICKEYTOKEN',
                'windows_installer_productcode_in_msi_context',
            ],
            'cp17_thesis_finding': (
                'BIFURCATED — see HANDOFF §10. Operator-cohort dissolved into '
                'web/mobile (Skydio absent + Cohort A descope). Installer-cohort '
                'desktop binaries DO exist (DJI, Hikvision) but yield NON-BLE '
                'identifier classes (MSI ProductCode, COM CLSID, document UUID '
                'in cloud URL) rather than BLE service UUIDs. Wave G mobile axis '
                'vs Wave H desktop axis differ on identifier-class surface, not '
                'just cohort presence.'
            ),
            'cp24_within_vendor_cross_product_buckets': {
                'dji_mavic_fpv': (
                    '1 vendor-specific UUID (f4d4dbf5-... vendor_document_uuid_cloud_reference) '
                    'cross-product attested'
                )
            },
            'cp28_resolution': {
                'cp28_c_ratified': [
                    'windows_installer_productcode_vendor_registered',
                    'windows_com_clsid_vendor_registered',
                    'vendor_document_uuid_cloud_reference',
                ],
                'cp28_a_deferred': (
                    'vendor_application_static_analysis source_type enum — '
                    'held under CP15 ceiling; band-distinction encoded via '
                    '§8.2 sub-band ladder + notes.session_admission'
                ),
                'cp28_b_deferred': (
                    'sanctioned_vendor_public_distribution_facts_only license-posture '
                    'sentinel — anchor weakened post-CP26 §8 audit; deferred to '
                    'post-Cohort-F completion as CP-of-its-own'
                ),
            },
            'eula_posture_disposition_counts': {
                'category_a_drop': 0,
                'category_b_board_review': 0,
                'category_c_include': 3,
                'category_d_drop': 0,
            },
            'calibration_freeze_timestamp_per_cohort': {
                'A_electron': 'DESCOPED_NO_WINDOW_FIRED_per_cp17',
                'D_drone_firmware_tooling': (
                    '2026-05-18T23:55:00Z (closed on empirical-maximum record '
                    'post-H2-disambig + Skydio P11 CLEAN NEGATIVE)'
                ),
                'F_sanctioned_vendor': (
                    'OPEN_vendor_2_acquisition_blocked_at_dahua_uniview_cloudflare'
                ),
            },
            'sanctioned_vendor_acquisition_workflow_validated': True,
        },
        'license_posture': 'per_vendor',
        'license_attribution': (
            'Hikvision iVMS-4200 EULA (download-agreement modal) + DJI EULA + '
            'FileZilla GPLv2 — all §3.6 (c) include.'
        ),
        'upstream_license_posture': 'no_license_declared_facts_only',
        'access_mode': 'per_vendor_public_download_no_auth',
        'last_status': (
            'partial_cycle_handoff_session_2_complete_cp26_8_audit_done_'
            'h2_disambig_done_skydio_p11_negative'
        ),
    }

    cur.execute('''
        INSERT INTO sources (name, url, source_type, tier, last_fetched_at,
                             last_status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        name,
        'argus-internal://wave_h_pre_v1/extraction_outputs',
        'manufacturer_app',
        1,
        '2026-05-18T23:50:19Z',
        notes_json['last_status'],
        json.dumps(notes_json, indent=2),
    ))
    sid = cur.lastrowid
    print(f'  sources: inserted Wave H source at id={sid}')
    return sid


def insert_raw_observations(cur, source_id):
    """Insert 5 raw_observations rows for the 4 promotion candidates.

    Each raw_observation captures one (vendor, value, binary) tuple.
    DJI f4d4dbf5 appears in BOTH Mavic and FPV (cross-product attested);
    we record it once per binary so the cross-product attestation is visible
    in the provenance trail.
    """
    rows = [
        # 1. DJI Mavic — f4d4dbf5 (vendor_document_uuid_cloud_reference)
        {
            'source_url': (
                'https://duss.djicorp.com/functional-document/'
                'f4d4dbf5-ba4b-40db-9a44-f8395f3728cf'
            ),
            'candidate_identifier': 'f4d4dbf5-ba4b-40db-9a44-f8395f3728cf',
            'candidate_type': 'vendor_document_uuid_cloud_reference',
            'candidate_category': 'drone',
            'candidate_manufacturer': 'DJI',
            'source_excerpt': (
                'https://duss.djicorp.com/functional-document/'
                'f4d4dbf5-ba4b-40db-9a44-f8395f3728cf'
            ),
            'source_row_key': 'wave_h_dji_assistant_2_mavic_f4d4dbf5',
            'binary': 'DJI Assistant 2 For Mavic v2.0.14',
            'binary_sha256': (
                'd5df2d8ea45e881670a9b723a495363fb198700a60b47cba5507bf1164e14698'
            ),
            'occurrence_count_in_binary': 4,  # appears in 4 separate DJI Service DLLs
        },
        # 2. DJI FPV — f4d4dbf5 (cross-product attested)
        {
            'source_url': (
                'https://duss.djicorp.com/functional-document/'
                'f4d4dbf5-ba4b-40db-9a44-f8395f3728cf'
            ),
            'candidate_identifier': 'f4d4dbf5-ba4b-40db-9a44-f8395f3728cf',
            'candidate_type': 'vendor_document_uuid_cloud_reference',
            'candidate_category': 'drone',
            'candidate_manufacturer': 'DJI',
            'source_excerpt': (
                'https://duss.djicorp.com/functional-document/'
                'f4d4dbf5-ba4b-40db-9a44-f8395f3728cf'
            ),
            'source_row_key': 'wave_h_dji_assistant_2_fpv_f4d4dbf5',
            'binary': 'DJI Assistant 2 (DJI FPV series) v2.1.2',
            'binary_sha256': 'tbd_per_provenance_json',
            'occurrence_count_in_binary': 4,
        },
        # 3. DJI Mavic — 054aae20 (windows_com_clsid_vendor_registered)
        {
            'source_url': (
                'argus-internal://wave_h_pre_v1/per_vendor/dji_assistant_2_mavic/'
                'fp_findings.json'
            ),
            'candidate_identifier': '054aae20-4bea-4347-8a35-64a533254a9d',
            'candidate_type': 'windows_com_clsid_vendor_registered',
            'candidate_category': 'drone',
            'candidate_manufacturer': 'DJI',
            'source_excerpt': (
                'Software\\Classes\\CLSID\\{054AAE20-4BEA-4347-8A35-64A533254A9D}\\'
                'LocalServer32'
            ),
            'source_row_key': 'wave_h_dji_assistant_2_mavic_054aae20',
            'binary': 'DJI Assistant 2 For Mavic v2.0.14',
            'binary_sha256': (
                'd5df2d8ea45e881670a9b723a495363fb198700a60b47cba5507bf1164e14698'
            ),
            'occurrence_count_in_binary': 1,
        },
        # 4. Hikvision iVMS-4200 — 9a25302d
        # (windows_installer_productcode_vendor_registered)
        {
            'source_url': (
                'argus-internal://wave_h_pre_v1/per_vendor/hikvision_ivms_4200/'
                'fp_findings.json'
            ),
            'candidate_identifier': '9a25302d-30c0-39d9-bd6f-21e6ec160475',
            'candidate_type': 'windows_installer_productcode_vendor_registered',
            'candidate_category': 'unknown',
            'candidate_manufacturer': 'Hikvision',
            'source_excerpt': (
                'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\'
                '{9A25302D-30C0-39D9-BD6F-21E6EC160475}'
            ),
            'source_row_key': 'wave_h_hikvision_ivms_4200_9a25302d',
            'binary': 'Hikvision iVMS-4200 v3.13.0.5_Multilingual',
            'binary_sha256': 'tbd_per_provenance_json',
            'occurrence_count_in_binary': 2,
        },
        # 5. Hikvision iVMS-4200 — ce2f96d0 (Multilingual Wizard sub-package)
        {
            'source_url': (
                'argus-internal://wave_h_pre_v1/per_vendor/hikvision_ivms_4200/'
                'fp_findings.json'
            ),
            'candidate_identifier': 'ce2f96d0-63d2-4b9c-a8d6-0d1a60840bd8',
            'candidate_type': 'windows_installer_productcode_vendor_registered',
            'candidate_category': 'unknown',
            'candidate_manufacturer': 'Hikvision',
            'source_excerpt': '\\{CE2F96D0-63D2-4B9C-A8D6-0D1A60840BD8}',
            'source_row_key': 'wave_h_hikvision_ivms_4200_ce2f96d0',
            'binary': 'Hikvision iVMS-4200 v3.13.0.5_Multilingual',
            'binary_sha256': 'tbd_per_provenance_json',
            'occurrence_count_in_binary': 2,
        },
    ]

    inserted = []
    for r in rows:
        cur.execute(
            'SELECT id FROM raw_observations WHERE source_row_key = ?',
            (r['source_row_key'],),
        )
        existing = cur.fetchone()
        if existing:
            print(
                f'  raw_observations: row already exists at id={existing[0]} '
                f'(key={r["source_row_key"]}; idempotent skip)'
            )
            inserted.append(existing[0])
            continue

        notes_json = {
            'binary': r['binary'],
            'binary_sha256': r['binary_sha256'],
            'occurrence_count_in_binary': r['occurrence_count_in_binary'],
            'wave': 'wave_h_pre_v1',
            'cp26_8_reclass_lineage': (
                'Originally surfaced as ble_service_uuid candidate by '
                'wave_g_extractor v4 regex layer; CP26 §8 semantic-validation '
                'audit re-classed to current candidate_type per HANDOFF §11(c).'
            ),
        }
        cur.execute('''
            INSERT INTO raw_observations
                (source_id, source_url, raw_payload, candidate_identifier,
                 candidate_type, candidate_category, candidate_manufacturer,
                 source_excerpt, captured_at, processed_at, notes,
                 source_row_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            source_id,
            r['source_url'],
            None,
            r['candidate_identifier'],
            r['candidate_type'],
            r['candidate_category'],
            r['candidate_manufacturer'],
            r['source_excerpt'],
            '2026-05-18T23:48:10Z',
            NOW_UTC,
            json.dumps(notes_json),
            r['source_row_key'],
        ))
        rid = cur.lastrowid
        inserted.append(rid)
        print(
            f'  raw_observations: inserted id={rid} '
            f'(key={r["source_row_key"]})'
        )
    return inserted


def promote_identifiers(cur, source_id, raw_obs_ids):
    """Promote the 4 vendor-attested non-BLE identifiers per CP28(c).

    raw_obs_ids order: [mavic_f4d4dbf5, fpv_f4d4dbf5, mavic_054aae20,
                        hik_9a25302d, hik_ce2f96d0]
    """
    promotions = [
        # 1. DJI vendor_document_uuid_cloud_reference (cross-product attested)
        #    — promote from Mavic raw_obs; FPV is the corroborating second
        #    occurrence within the same vendor (CP24 within-vendor-cross-
        #    product, not §8.3 cross-source lift since both are the same
        #    DJI source).
        {
            'identifier': 'f4d4dbf5-ba4b-40db-9a44-f8395f3728cf',
            'identifier_type': 'vendor_document_uuid_cloud_reference',
            'device_category': 'drone',
            'manufacturer': 'DJI',
            'model': 'DJI Assistant 2 (Mavic + FPV cross-product)',
            'confidence': 90,
            'source_url': (
                'https://duss.djicorp.com/functional-document/'
                'f4d4dbf5-ba4b-40db-9a44-f8395f3728cf'
            ),
            'source_type': 'manufacturer_app',
            'source_excerpt': (
                'https://duss.djicorp.com/functional-document/'
                'f4d4dbf5-ba4b-40db-9a44-f8395f3728cf '
                '(cross-product attested in DJI Mavic + FPV binaries)'
            ),
            'geographic_scope': 'global',
            'first_seen': '2026-05-18T23:48:10Z',
            'last_verified': '2026-05-18T23:48:10Z',
            'notes': {
                'session_admission': 'wave_h_pre_v1',
                'wave': 'wave_h_pre_v1',
                'cp28_band': 'vendor_document_uuid_cloud_reference 80-95',
                'cp24_within_vendor_cross_product': 'dji_mavic+fpv',
                'single_source_at_promotion': True,
                'upstream_license_posture': 'no_license_declared_facts_only',
                'cp26_8_reclass_lineage': (
                    'Originally surfaced as ble_service_uuid; re-classed to '
                    'vendor_document_uuid_cloud_reference at CP26 §8 audit.'
                ),
                'lynceus_mapping_posture': 'MAP',
            },
            'raw_obs_ids': [raw_obs_ids[0], raw_obs_ids[1]],
        },
        # 2. DJI windows_com_clsid_vendor_registered
        {
            'identifier': '054aae20-4bea-4347-8a35-64a533254a9d',
            'identifier_type': 'windows_com_clsid_vendor_registered',
            'device_category': 'drone',
            'manufacturer': 'DJI',
            'model': 'DJI Assistant 2 For Mavic v2.0.14 (DJIBrowser COM server)',
            'confidence': 85,
            'source_url': (
                'argus-internal://wave_h_pre_v1/per_vendor/dji_assistant_2_mavic/'
                'fp_findings.json'
            ),
            'source_type': 'manufacturer_app',
            'source_excerpt': (
                'Software\\Classes\\CLSID\\{054AAE20-4BEA-4347-8A35-64A533254A9D}\\'
                'LocalServer32 (DJIBrowser)'
            ),
            'geographic_scope': 'global',
            'first_seen': '2026-05-18T23:48:10Z',
            'last_verified': '2026-05-18T23:48:10Z',
            'notes': {
                'session_admission': 'wave_h_pre_v1',
                'wave': 'wave_h_pre_v1',
                'cp28_band': 'windows_com_clsid_vendor_registered 75-90',
                'single_source_at_promotion': True,
                'upstream_license_posture': 'no_license_declared_facts_only',
                'cp26_8_reclass_lineage': (
                    'Originally surfaced as ble_service_uuid; re-classed to '
                    'windows_com_clsid_vendor_registered at CP26 §8 audit.'
                ),
                'lynceus_mapping_posture': 'DROPPED',
            },
            'raw_obs_ids': [raw_obs_ids[2]],
        },
        # 3. Hikvision windows_installer_productcode_vendor_registered #1
        {
            'identifier': '9a25302d-30c0-39d9-bd6f-21e6ec160475',
            'identifier_type': 'windows_installer_productcode_vendor_registered',
            'device_category': 'unknown',
            'manufacturer': 'Hikvision',
            'model': 'iVMS-4200 v3.13.0.5_Multilingual (main package)',
            'confidence': 85,
            'source_url': (
                'argus-internal://wave_h_pre_v1/per_vendor/hikvision_ivms_4200/'
                'fp_findings.json'
            ),
            'source_type': 'manufacturer_app',
            'source_excerpt': (
                'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\'
                '{9A25302D-30C0-39D9-BD6F-21E6EC160475}'
            ),
            'geographic_scope': 'global',
            'first_seen': '2026-05-18T23:48:10Z',
            'last_verified': '2026-05-18T23:48:10Z',
            'notes': {
                'session_admission': 'wave_h_pre_v1',
                'wave': 'wave_h_pre_v1',
                'cp28_band': 'windows_installer_productcode_vendor_registered 75-90',
                'single_source_at_promotion': True,
                'upstream_license_posture': 'no_license_declared_facts_only',
                'cp26_8_reclass_lineage': (
                    'Originally surfaced as ble_service_uuid; re-classed to '
                    'windows_installer_productcode_vendor_registered at CP26 §8 audit.'
                ),
                'lynceus_mapping_posture': 'DROPPED',
                'ndaa_section_889_note': (
                    'NDAA Section 889 federally-restricted; state/local LE '
                    'deployments persist outside the federal-procurement bar.'
                ),
            },
            'raw_obs_ids': [raw_obs_ids[3]],
        },
        # 4. Hikvision windows_installer_productcode_vendor_registered #2
        {
            'identifier': 'ce2f96d0-63d2-4b9c-a8d6-0d1a60840bd8',
            'identifier_type': 'windows_installer_productcode_vendor_registered',
            'device_category': 'unknown',
            'manufacturer': 'Hikvision',
            'model': 'iVMS-4200 v3.13.0.5_Multilingual (Multilingual Wizard sub-package)',
            'confidence': 85,
            'source_url': (
                'argus-internal://wave_h_pre_v1/per_vendor/hikvision_ivms_4200/'
                'fp_findings.json'
            ),
            'source_type': 'manufacturer_app',
            'source_excerpt': '\\{CE2F96D0-63D2-4B9C-A8D6-0D1A60840BD8}',
            'geographic_scope': 'global',
            'first_seen': '2026-05-18T23:48:10Z',
            'last_verified': '2026-05-18T23:48:10Z',
            'notes': {
                'session_admission': 'wave_h_pre_v1',
                'wave': 'wave_h_pre_v1',
                'cp28_band': 'windows_installer_productcode_vendor_registered 75-90',
                'single_source_at_promotion': True,
                'upstream_license_posture': 'no_license_declared_facts_only',
                'cp26_8_reclass_lineage': (
                    'Originally surfaced as ble_service_uuid; re-classed to '
                    'windows_installer_productcode_vendor_registered at CP26 §8 audit.'
                ),
                'lynceus_mapping_posture': 'DROPPED',
                'ndaa_section_889_note': (
                    'NDAA Section 889 federally-restricted; state/local LE '
                    'deployments persist outside the federal-procurement bar.'
                ),
            },
            'raw_obs_ids': [raw_obs_ids[4]],
        },
    ]

    promoted = []
    for p in promotions:
        # Idempotency check: existing row at the same (identifier, identifier_type)
        # with a Wave H notes tag means we've already promoted.
        cur.execute(
            '''SELECT id, notes FROM identifiers
               WHERE identifier = ? AND identifier_type = ?''',
            (p['identifier'], p['identifier_type']),
        )
        existing = cur.fetchone()
        if existing and existing[1] and 'wave_h_pre_v1' in existing[1]:
            print(
                f'  identifiers: row already promoted at id={existing[0]} '
                f'(identifier={p["identifier"][:20]}...; idempotent skip)'
            )
            promoted.append(existing[0])
            continue

        cur.execute('''
            INSERT INTO identifiers (
                identifier, identifier_type, device_category, manufacturer,
                model, confidence, source_url, source_type, source_excerpt,
                geographic_scope, first_seen, last_verified, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            p['identifier'],
            p['identifier_type'],
            p['device_category'],
            p['manufacturer'],
            p['model'],
            p['confidence'],
            p['source_url'],
            p['source_type'],
            p['source_excerpt'],
            p['geographic_scope'],
            p['first_seen'],
            p['last_verified'],
            json.dumps(p['notes']),
        ))
        ident_id = cur.lastrowid
        promoted.append(ident_id)
        print(
            f'  identifiers: promoted id={ident_id} '
            f'({p["identifier_type"]} / {p["manufacturer"]} / conf={p["confidence"]})'
        )

        # Link raw_observations to the promoted identifier
        for raw_id in p['raw_obs_ids']:
            cur.execute(
                '''UPDATE raw_observations
                   SET promoted_identifier_id = ?
                   WHERE id = ?''',
                (ident_id, raw_id),
            )
    return promoted


def attach_documented_absences(cur):
    """Attach 5 documented_absence entries to existing manufacturer rows.

    Per MAC-178 P5 precedent: each entry is appended to
    `manufacturers.notes.documented_absence[]`.

    Vendors covered:
      - Verkada (id=210) × 2 (Command desktop + Command Connector Electron-class)
      - Avigilon (id=6) × 1 (Alta Aware cloud-first)
      - Skydio (id=23) × 2 (Pilot Electron variant + Pilot desktop P11)
    """
    absences = {
        'Verkada': [
            {
                'staging_vendor_canonical': 'Verkada',
                'product_intended': 'Command (desktop)',
                'absence_reason': 'web_app_only_no_desktop_client_2026_05',
                'channels_probed': ['vendor_documentation_https_verkada_com'],
                'binary_probed': '(none — no desktop client distributed)',
                'verification_url': 'https://www.verkada.com/command/',
                'rationale_prose': (
                    'Vendor documentation explicitly states users access '
                    'Command via web browser; no desktop client distributed.'
                ),
                'cohort_label': 'A_electron',
                'outcome': 'categorical_absent',
                'investigation_date_utc': '2026-05-18',
                'investigation_dispatch_ref': 'MAC-177',
                'integration_dispatch_ref': 'MAC-181',
            },
            {
                'staging_vendor_canonical': 'Verkada',
                'product_intended': 'Command Connector (Electron-class binary)',
                'absence_reason': (
                    'hardware_appliance_not_software_distribution_2026_05'
                ),
                'channels_probed': ['vendor_documentation_https_verkada_com'],
                'binary_probed': '(none — physical hardware appliance, not software)',
                'verification_url': 'https://www.verkada.com/command-connector/',
                'rationale_prose': (
                    'Command Connector is a physical hardware appliance shipped '
                    'as a Verkada-branded box; not a software distribution.'
                ),
                'cohort_label': 'A_electron',
                'outcome': 'categorical_absent',
                'investigation_date_utc': '2026-05-18',
                'investigation_dispatch_ref': 'MAC-177',
                'integration_dispatch_ref': 'MAC-181',
            },
        ],
        'Avigilon': [
            {
                'staging_vendor_canonical': 'Avigilon (Motorola)',
                'product_intended': 'Alta Aware',
                'absence_reason': (
                    'cloud_first_no_alta_aware_desktop_client_2026_05'
                ),
                'channels_probed': ['vendor_documentation_https_avigilon_com'],
                'binary_probed': '(none — cloud-first SaaS; no desktop client)',
                'verification_url': 'https://www.avigilon.com/alta',
                'rationale_prose': (
                    'Avigilon Alta (formerly Ava Security) is distributed as a '
                    'cloud-first SaaS platform; no Alta Aware desktop client.'
                ),
                'cohort_label': 'A_electron',
                'outcome': 'categorical_absent',
                'investigation_date_utc': '2026-05-18',
                'investigation_dispatch_ref': 'MAC-177',
                'integration_dispatch_ref': 'MAC-181',
            },
        ],
        'Skydio': [
            {
                'staging_vendor_canonical': 'Skydio',
                'product_intended': 'Pilot (Electron variant)',
                'absence_reason': 'no_electron_desktop_variant_2026_05',
                'channels_probed': ['cohort_a_prelim_descope'],
                'binary_probed': '(none — Electron variant not distributed)',
                'verification_url': 'https://www.skydio.com/software',
                'rationale_prose': (
                    'Cohort A descope finding: Skydio does not distribute an '
                    'Electron-class desktop variant of any operator client.'
                ),
                'cohort_label': 'A_electron_prelim',
                'outcome': 'categorical_absent',
                'investigation_date_utc': '2026-05-18',
                'investigation_dispatch_ref': 'MAC-177',
                'integration_dispatch_ref': 'MAC-181',
            },
            {
                'staging_vendor_canonical': 'Skydio',
                'product_intended': 'Skydio Pilot (desktop)',
                'absence_reason': 'no_desktop_client_distribution_2026_05_p11_clean_negative',
                'channels_probed': [
                    'curl_skydio_com_pilot_404',
                    'curl_skydio_com_pilot_download_404',
                    'curl_pilot_skydio_com_dns_no_response',
                    'websearch_skydio_pilot_desktop_application_no_results',
                ],
                'binary_probed': '(none — no Skydio Pilot desktop installer exists)',
                'verification_url': 'https://www.skydio.com/software',
                'rationale_prose': (
                    'Skydio P11 CLEAN NEGATIVE per Wave H session 2 probe: '
                    'product distribution model has no standalone desktop '
                    'application. Operator-axis software is split across '
                    'iOS/Android mobile apps, hardware-controller firmware '
                    '(X10 Controller integrated OS), and cloud-only enterprise '
                    'platforms (Skydio Cloud, Remote Flight Deck, DFR Command, '
                    'Fleet Manager). Confirms CP17 desktop-axis thesis '
                    'bifurcation finding for drone-tooling vendor cohort.'
                ),
                'cohort_label': 'D_drone_firmware_tooling',
                'outcome': 'categorical_absent_p11_clean_negative',
                'investigation_date_utc': '2026-05-18',
                'investigation_dispatch_ref': 'MAC-177',
                'integration_dispatch_ref': 'MAC-181',
            },
        ],
    }

    for vendor, vendor_absences in absences.items():
        cur.execute(
            'SELECT id, notes FROM manufacturers WHERE canonical_name = ?',
            (vendor,),
        )
        row = cur.fetchone()
        if not row:
            print(
                f'  documented_absence: WARNING — manufacturer {vendor} not '
                f'found; skipping {len(vendor_absences)} absence entries'
            )
            continue
        mfr_id, notes_text = row
        notes = json.loads(notes_text) if notes_text else {}
        existing_absences = notes.get('documented_absence', [])

        added = 0
        for absence in vendor_absences:
            # Idempotency: skip if this absence is already recorded by
            # (product_intended, absence_reason) tuple
            key = (absence['product_intended'], absence['absence_reason'])
            if any(
                (a.get('product_intended'), a.get('absence_reason')) == key
                for a in existing_absences
            ):
                print(
                    f'  documented_absence: {vendor}/{absence["product_intended"]} '
                    f'already recorded (idempotent skip)'
                )
                continue
            existing_absences.append(absence)
            added += 1

        if added:
            notes['documented_absence'] = existing_absences
            cur.execute(
                'UPDATE manufacturers SET notes = ? WHERE id = ?',
                (json.dumps(notes), mfr_id),
            )
            print(
                f'  documented_absence: appended {added} entries to {vendor} '
                f'(mfr_id={mfr_id})'
            )


def admit_stub_manufacturers(cur):
    """Admit 2 stub manufacturer rows per MAC-178 P5 precedent.

    Eagle Eye Networks + Rhombus Systems: documented_absence-only admissions
    with `notes.admission_basis='documented_absence_only'`.

    Per the §8.8 forecast, this is a +2 delta over the +0 forecast. Surface
    this delta-vs-forecast in the cycle-close comment.
    """
    stubs = [
        {
            'canonical_name': 'Eagle Eye Networks',
            'aliases': 'Eagle Eye',
            'primary_category': 'unknown',
            'source_url': 'https://www.een.com/',
            'notes': {
                'admission_basis': 'documented_absence_only',
                'description': (
                    'Admitted via Wave H pre-v1 Cohort A absence-investigation: '
                    'EEN Viewer ships as a UWP MSIX package (Microsoft Store), '
                    'not an Electron-class desktop client. Cohort A descope '
                    'finding 2026-05-18.'
                ),
                'admission_date_utc': '2026-05-18T23:55:00Z',
                'admission_dispatch_ref': 'MAC-177',
                'admission_integration_ref': 'MAC-181',
                'documented_absence': [
                    {
                        'staging_vendor_canonical': 'Eagle Eye Networks',
                        'product_intended': 'EEN Viewer',
                        'absence_reason': (
                            'microsoft_store_uwp_msix_not_electron_2026_05'
                        ),
                        'channels_probed': ['vendor_documentation_https_een_com'],
                        'binary_probed': (
                            '(MSIX package via Microsoft Store; not Electron — '
                            'Cohort A descoped, no extraction attempted)'
                        ),
                        'verification_url': 'https://www.een.com/',
                        'rationale_prose': (
                            'EEN Viewer is distributed as a Universal Windows '
                            'Platform (UWP) MSIX package through the Microsoft '
                            'Store, not an Electron-class desktop client.'
                        ),
                        'cohort_label': 'A_electron',
                        'outcome': 'categorical_absent',
                        'investigation_date_utc': '2026-05-18',
                        'investigation_dispatch_ref': 'MAC-177',
                        'integration_dispatch_ref': 'MAC-181',
                    },
                ],
            },
        },
        {
            'canonical_name': 'Rhombus Systems',
            'aliases': 'Rhombus',
            'primary_category': 'unknown',
            'source_url': 'https://www.rhombus.com/',
            'notes': {
                'admission_basis': 'documented_absence_only',
                'description': (
                    'Admitted via Wave H pre-v1 Cohort A absence-investigation: '
                    'Rhombus Console is a web app only; no desktop client '
                    'distributed. Cohort A descope finding 2026-05-18.'
                ),
                'admission_date_utc': '2026-05-18T23:55:00Z',
                'admission_dispatch_ref': 'MAC-177',
                'admission_integration_ref': 'MAC-181',
                'documented_absence': [
                    {
                        'staging_vendor_canonical': 'Rhombus Systems',
                        'product_intended': 'Console',
                        'absence_reason': 'web_app_only_no_desktop_client_2026_05',
                        'channels_probed': [
                            'vendor_documentation_https_rhombus_com'
                        ],
                        'binary_probed': '(none — web app only)',
                        'verification_url': 'https://www.rhombus.com/',
                        'rationale_prose': (
                            'Rhombus Console is distributed as a web '
                            'application only; no desktop client.'
                        ),
                        'cohort_label': 'A_electron',
                        'outcome': 'categorical_absent',
                        'investigation_date_utc': '2026-05-18',
                        'investigation_dispatch_ref': 'MAC-177',
                        'integration_dispatch_ref': 'MAC-181',
                    },
                ],
            },
        },
    ]

    for stub in stubs:
        cur.execute(
            'SELECT id FROM manufacturers WHERE canonical_name = ?',
            (stub['canonical_name'],),
        )
        if cur.fetchone():
            print(
                f'  manufacturers stub: {stub["canonical_name"]} already exists '
                f'(idempotent skip)'
            )
            continue
        cur.execute('''
            INSERT INTO manufacturers
                (canonical_name, aliases, primary_category, source_url, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            stub['canonical_name'],
            stub['aliases'],
            stub['primary_category'],
            stub['source_url'],
            json.dumps(stub['notes']),
        ))
        print(
            f'  manufacturers stub: admitted {stub["canonical_name"]} '
            f'at id={cur.lastrowid} (documented_absence_only)'
        )


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('PRAGMA foreign_keys = ON')

    print('=== MAC-181 §8.8 Wave H pre-v1 DB promotion ===')
    print(f'  DB: {DB_PATH}')
    print(f'  now: {NOW_UTC}')

    # Baseline
    cur.execute('SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL')
    pre_id_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM sources')
    pre_src_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM manufacturers')
    pre_mfr_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM raw_observations')
    pre_raw_count = cur.fetchone()[0]
    print(
        f'  baseline: identifiers={pre_id_count} sources={pre_src_count} '
        f'manufacturers={pre_mfr_count} raw_observations={pre_raw_count}'
    )

    print()
    print('  --- sources ---')
    sid = insert_wave_h_source(cur)
    print()
    print('  --- raw_observations ---')
    raw_ids = insert_raw_observations(cur, sid)
    print()
    print('  --- identifiers ---')
    promoted = promote_identifiers(cur, sid, raw_ids)
    print()
    print('  --- documented_absences (existing manufacturers) ---')
    attach_documented_absences(cur)
    print()
    print('  --- stub manufacturer admissions ---')
    admit_stub_manufacturers(cur)

    conn.commit()

    # Post-state
    print()
    cur.execute('SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL')
    post_id_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM sources')
    post_src_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM manufacturers')
    post_mfr_count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM raw_observations')
    post_raw_count = cur.fetchone()[0]
    print(
        f'  post:      identifiers={post_id_count} sources={post_src_count} '
        f'manufacturers={post_mfr_count} raw_observations={post_raw_count}'
    )
    print(
        f'  deltas:    identifiers={post_id_count - pre_id_count:+d} '
        f'sources={post_src_count - pre_src_count:+d} '
        f'manufacturers={post_mfr_count - pre_mfr_count:+d} '
        f'raw_observations={post_raw_count - pre_raw_count:+d}'
    )

    cur.execute('PRAGMA integrity_check')
    print(f'  PRAGMA integrity_check = {cur.fetchone()[0]}')
    cur.execute('PRAGMA quick_check')
    print(f'  PRAGMA quick_check = {cur.fetchone()[0]}')
    cur.execute('PRAGMA foreign_key_check')
    fks = cur.fetchall()
    print(f'  PRAGMA foreign_key_check = {"OK (empty)" if not fks else fks}')

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
