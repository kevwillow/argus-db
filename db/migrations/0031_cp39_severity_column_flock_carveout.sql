-- ============================================================================
-- Migration: 0031_cp39_severity_column_flock_carveout
-- Issue:     MAC-292 / MAC-305 (v1.6.2.1 — Flock-hunt promotion + severity)
-- Author:    CEO (claude_local) · Board approval `61b382a3` 2026-05-30
-- CP:        CP39 — adds `severity` column to `identifiers` AND establishes the
--            §7.5 floor carve-out for Flock-hunt-project-attested rows (named
--            sids 6/15/16/20/33/38/39/40/42). See BIBLE_AMENDMENTS.md CP39 entry
--            for the rule body and ratification chain.
-- Purpose:   Add one optional `severity` column (enum: 'high'/'medium'/'low' OR NULL,
--            default NULL) to `identifiers`. NARROW SCOPE per board direction
--            (`61b382a3`): Flock-attested rows get severity='high' in the same
--            v1.6.2.1 cycle; everything else stays severity=NULL. Future cycles
--            can backfill by category as orthogonal CPs.
-- Pattern:   SQLite table-rebuild (CP21 cumulative-full-enum), mirrors 0030/0027/0026.
--            All prior CHECK constraints carried forward verbatim from migration 0030.
-- Bible:     §11 #1 — no fabrication: severity is purely a labeling axis; existing
--                    confidence/source_type/manufacturer/category fields unchanged.
--            §11 #11 — paired with a CP39 entry in docs/engineering/BIBLE_AMENDMENTS.md
--                     (no silent CP).
--            §7.5 (carve-out) — rows from Flock-hunt sids (6/15/16/20/33/38/39/40/42)
--                  may be admitted at confidence ≥85 with severity='high', notwith-
--                  standing the standard "excludes crowdsourced/inferred" export
--                  floor. Justification: upstream project release + active user base
--                  is sufficient external verification for these named sources.
--            SAR-13 — sqlite_master-first: the _new DDL below was re-verified against
--                  the LIVE post-mig-0030 sqlite_master at apply-time.
-- Idempotency: apply-once. schema_version insert is OR IGNORE.
-- ============================================================================

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild (+1 column: severity) ─────────────────────────
CREATE TABLE identifiers_new (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL CHECK (identifier_type IN (
                          -- Pre-CP13 (0001 initial) — 9 values
                          'oui', 'mac', 'mac_range', 'bssid',
                          'ssid_exact', 'ssid_pattern',
                          'ble_uuid', 'ble_service',
                          'device_fingerprint',
                          -- CP13 (migration 0009) — Wave G structural fidelity (3)
                          'ble_local_name', 'ble_characteristic',
                          'product_family_codename',
                          -- CP14 (migration 0011) — G-3 BLE SIG manufacturer IDs (1)
                          'ble_manufacturer_id',
                          -- CP14 (migration 0013) — Drone-RID + proprietary
                          -- protocol cluster (13)
                          'drone_id_prefix',
                          'icao_24bit_address',
                          'rf_channel',
                          'burst_cadence_ms',
                          'bandwidth_mhz',
                          'device_class_id',
                          'rf_burst_duration',
                          'rf_protocol_constant',
                          'wifi_aware_service_name',
                          'wifi_ie_element_id',
                          'bluetooth_le_pdu_type',
                          'wifi_frame_control_subtype',
                          'wifi_nan_param_signature',
                          -- CP14 (migration 0014) — surveillance metadata (1)
                          'alpr_model',
                          -- CP20 (migration 0018) — SAR-13 §S.3 vendor-anchored
                          -- / device-naming cluster (14)
                          'ble_protocol_byte_table',
                          'ble_service_uuid',
                          'ble_company_id',
                          'frequency_band',
                          'ble_protocol_byte',
                          'operator_profile',
                          'x509_cert_sha256_prefix',
                          'ble_adv_interval',
                          'ble_payload_offset',
                          'firmware_sha256_hash',
                          'network_endpoint',
                          'firmware_image_variant',
                          'qualcomm_chip_format_id',
                          'firmware_branded_string',
                          -- MAC-117 (migration 0019) — round-2 vocab
                          -- extension (7) per §1 routing slate (A)
                          'asdstan_message_type',
                          'asdstan_enum_value',
                          'dji_protocol_struct_format',
                          'gpt_partition_uuid',
                          'chipset_codename',
                          'firmware_build_string',
                          'firmware_build_uuid',
                          -- CP28 (migration 0023) — Wave H desktop-axis vendor-
                          -- registered non-BLE cluster (3)
                          'windows_installer_productcode_vendor_registered',
                          'windows_com_clsid_vendor_registered',
                          'vendor_document_uuid_cloud_reference',
                          -- CP29 (migration 0024) — Wave I/I.5/I.6/I.7 vendor
                          -- cloud-infrastructure hostname corpus (3)
                          'vendor_controlled_hostname',
                          'vendor_cloud_endpoint_url',
                          'vendor_controlled_hostname_deprecated',
                          -- CP31 (migration 0025) — FCC EAS identifier-type
                          -- cluster (2)
                          'fcc_grantee_code',
                          'equipment_class_code',
                          -- CP33 (migration 0027) — GSMA TAC cluster (1)
                          'imei_tac',
                          -- CP34 (migration 0028) — Wave G/H v1 CCTV camera-
                          -- discovery protocol pattern (1)
                          'network_discovery_protocol_pattern'
                      )),
    device_category   TEXT NOT NULL CHECK (device_category IN (
                          -- 0001 initial — 12 values
                          'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                          'drone', 'gunshot_detect', 'hacking_tool',
                          'covert_cam', 'gps_tracker', 'face_recog',
                          'drone_detect', 'unknown',
                          -- CP32 (migration 0026) — automotive telematics arm cluster
                          'automotive_telematics',
                          -- CP33 (migration 0027) — v1.5.0 cohort lexicon expansion (+3)
                          'cctv_camera',
                          'persistent_surveillance',
                          'through_wall_radar',
                          -- CP37 (migration 0030) — Wave K cohort 3 lawful-intercept /
                          -- network-surveillance platforms
                          'network_surveillance'
                      )),
    manufacturer      TEXT,
    model             TEXT,
    confidence        INTEGER CHECK (confidence BETWEEN 0 AND 100),
    source_url        TEXT NOT NULL,
    source_type       TEXT NOT NULL CHECK (source_type IN (
                          -- Pre-CP13 (0001 initial; 8 values)
                          'official', 'regulatory', 'procurement',
                          'academic', 'foia', 'crowdsourced',
                          'inferred', 'manufacturer_doc',
                          -- CP13 (migration 0009)
                          'manufacturer_app',
                          -- CP15 (migration 0015)
                          'primary_registry',
                          -- CP35 (migration 0029) — enum parity with sources.source_type
                          'judicial_filing',
                          'disclosure_filing',
                          'procurement_disclosure'
                      )),
    source_excerpt    TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    geographic_scope  TEXT,
    first_seen        DATETIME,
    last_verified     DATETIME,
    notes             TEXT,
    superseded_by     INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
    -- CP14 (migration 0012) — paired-identifier discipline
    paired_identifier_id INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
    pair_kind            TEXT CHECK (
                             pair_kind IS NULL
                             OR pair_kind IN (
                                 'la_bit_flip',
                                 'frdid_sibling',
                                 'vendor_as_container',
                                 'firmware_generation',
                                 -- CP31 (migration 0025) — FCC EAS structural pairing
                                 'fcc_grantee_equipment_class'
                             )
                         ),
    -- ─── CP39 (THIS migration) — severity column ──────────────────────────────
    -- Orthogonal axis to confidence. Confidence = identifier-veracity (intake side).
    -- Severity = surveillance-impact class (downstream consumer side). NARROW scope
    -- this cycle: only Flock-attested rows are labeled in mig-0031's accompanying
    -- data-pass; everything else stays NULL pending future CPs. The CHECK enum is
    -- pre-baked with the 3 intended values to avoid a follow-on enum-extension CP
    -- when broader backfills land.
    severity             TEXT CHECK (
                             severity IS NULL
                             OR severity IN ('high', 'medium', 'low')
                         )
);

-- Column-explicit INSERT — the new severity column gets NULL for all existing rows
-- (the accompanying data-pass UPDATEs the Flock-attested subset to 'high').
INSERT INTO identifiers_new (
    id, identifier, identifier_type, device_category,
    manufacturer, model, confidence,
    source_url, source_type, source_excerpt, geographic_scope,
    first_seen, last_verified, notes,
    superseded_by, paired_identifier_id, pair_kind
)
SELECT
    id, identifier, identifier_type, device_category,
    manufacturer, model, confidence,
    source_url, source_type, source_excerpt, geographic_scope,
    first_seen, last_verified, notes,
    superseded_by, paired_identifier_id, pair_kind
FROM identifiers;

DROP TABLE identifiers;
ALTER TABLE identifiers_new RENAME TO identifiers;

CREATE INDEX IF NOT EXISTS idx_identifiers_identifier ON identifiers(identifier);
CREATE INDEX IF NOT EXISTS idx_identifiers_type       ON identifiers(identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_category   ON identifiers(device_category);
CREATE INDEX IF NOT EXISTS idx_identifiers_superseded ON identifiers(superseded_by);
CREATE INDEX IF NOT EXISTS idx_identifiers_ident_type ON identifiers(identifier, identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_paired     ON identifiers(paired_identifier_id);
-- CP39 — new index on severity for consumer-side filtering
CREATE INDEX IF NOT EXISTS idx_identifiers_severity   ON identifiers(severity);

PRAGMA foreign_key_check;

-- Version bump — CP39 / file 0031.
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (31, '0031_cp39_severity_column_flock_carveout');

COMMIT;

PRAGMA foreign_keys = ON;
