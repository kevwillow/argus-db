-- ============================================================================
-- Migration: 0030_cp37_device_category_network_surveillance
-- Issue:     MAC-273 (Wave K+L combined Phase H) · Author: DBArchitect (6c93a466)
-- Applied:   2026-05-24 (Phase H canonical write, CEO-ratified)
-- CP:        CP37 (operator/CEO-ratified Option A; GATE-1). Note: schema_version
--            row 29 is named cp35 in-ledger while the migration FILE is 0029_cp36_*
--            (a known ledger-vs-file CP offset, see MAC-273 memory). This migration
--            keeps the FILE convention: file 0030 / CP37 / schema_version row 30.
-- Purpose:   Extend `device_category` CHECK enum +1 net-new value on BOTH host
--            tables (identifiers + behavioral_signatures), maintaining the
--            CP32/CP33 dual-table parity invariant:
--              - `network_surveillance`  (Wave K cohort 3 — lawful intercept /
--                 network surveillance: Pen-Link, SS8 Networks, Cognyte, Utimaco
--                 LIMS, Polaris Wireless, Trovicor)
-- Rationale: hacking_tool (the cohort-2/cohort-4 home) denotes offensive
--            exploitation + forensic extraction. Cohort-3 lawful-intercept /
--            mediation / monitoring-center / geolocation platforms are a distinct
--            surveillance class; folding them under hacking_tool would blur the
--            offensive-vs-passive distinction downstream consumers rely on.
-- Bible:     §11 #1 no fabrication (each new value cites concrete cohort-3 vendors).
--            §11 #11 amendment-log discipline — paired with a CP37 entry in
--                    docs/engineering/BIBLE_AMENDMENTS.md (no silent CP).
--            §11 #13 Lynceus unknown-bucket carveout — network_surveillance is a
--                    PROMOTING category (excluded-when-unknown does NOT apply).
--            SAR-13 sqlite_master-first — the _new DDL below was re-verified
--                    column-for-column and CHECK-for-CHECK against the LIVE
--                    post-CP36 sqlite_master at apply-time (17-col identifiers,
--                    13-col behavioral_signatures; identifier_type / source_type /
--                    pair_kind / json_valid / UNIQUE constraints preserved verbatim).
-- Pattern:   SQLite table-rebuild (CP21 cumulative-full-enum), mirrors 0026/0027.
-- Idempotency: apply-once. schema_version insert is OR IGNORE.
-- ============================================================================

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild (device_category +1: network_surveillance) ────
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
                          -- CP33 (migration 0027) — GSMA TAC cluster (1; 0 rows
                          -- promoted at CP33; forward-compat carried forward)
                          'imei_tac',
                          -- CP34 (migration 0028) — Wave G/H v1 CCTV cohort
                          -- camera-discovery protocol pattern (Hikvision SADP,
                          -- Dahua AirKiss/SmartConfig, Tiandy SADP-style, Axis
                          -- ONVIF WS-Discovery). 18 high-conf promoted at CP34.
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
                          -- CP37 (migration 0030 — THIS migration) — Wave K cohort 3
                          -- lawful-intercept / network-surveillance platforms
                          -- (Pen-Link, SS8, Cognyte, Utimaco LIMS, Polaris Wireless,
                          -- Trovicor). hacking_tool reserved for offensive-
                          -- exploitation vendors (NSO/Cytrox/etc.).
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
                          -- CP35 (migration 0029) — enum parity with
                          -- sources.source_type per CP23 trio; closes the
                          -- gap surfaced at MAC-249 Phase G Validator CPN-A.
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
                         )
);

INSERT INTO identifiers_new SELECT * FROM identifiers;
DROP TABLE identifiers;
ALTER TABLE identifiers_new RENAME TO identifiers;

CREATE INDEX IF NOT EXISTS idx_identifiers_identifier ON identifiers(identifier);
CREATE INDEX IF NOT EXISTS idx_identifiers_type       ON identifiers(identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_category   ON identifiers(device_category);
CREATE INDEX IF NOT EXISTS idx_identifiers_superseded ON identifiers(superseded_by);
CREATE INDEX IF NOT EXISTS idx_identifiers_ident_type ON identifiers(identifier, identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_paired     ON identifiers(paired_identifier_id);

-- ─── behavioral_signatures table rebuild (device_category +1, parity) ────────
CREATE TABLE behavioral_signatures_new (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identity
    signature_name         TEXT NOT NULL,

    -- Categorical context
    cellular_generation    TEXT CHECK (
                               cellular_generation IS NULL
                               OR cellular_generation IN ('2G','3G','4G','5G_NSA')
                           ),

    -- Structured thresholds (e.g. AIMSICD's RSSI deviation gate, 30s idle
    -- accelerometer gate, or NEA0 null-cipher trigger configuration).
    -- Nullable for qualitative signatures (patterns without numeric thresholds).
    threshold_json         TEXT CHECK (
                               threshold_json IS NULL
                               OR json_valid(threshold_json)
                           ),

    -- Evidence dossier: paper citation, upstream repo SHA, file/line
    -- provenance. Per §11 #1 every row must trace back to a concrete source.
    evidence_json          TEXT CHECK (
                               evidence_json IS NULL
                               OR json_valid(evidence_json)
                           ),

    -- Provenance (FK to sources; same shape as existing tables).
    source_id              INTEGER NOT NULL REFERENCES sources(id)
                                ON DELETE RESTRICT,
    source_file_relative   TEXT,
    source_line            INTEGER,

    -- Confidence — same SAR-7 §7.3 intake-side rules apply.
    confidence             INTEGER CHECK (confidence BETWEEN 0 AND 100),

    -- Device category — parity with identifiers.device_category per CP32/CP33
    -- precedent; CP37 (this migration) adds network_surveillance (+1).
    device_category        TEXT NOT NULL CHECK (device_category IN (
                               -- 0010 initial (MAC-58) — 12 values
                               'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                               'drone', 'gunshot_detect', 'hacking_tool',
                               'covert_cam', 'gps_tracker', 'face_recog',
                               'drone_detect', 'unknown',
                               -- CP32 (migration 0026) — automotive telematics arm
                               'automotive_telematics',
                               -- CP33 (migration 0027) — v1.5.0 cohort lexicon (+3)
                               'cctv_camera',
                               'persistent_surveillance',
                               'through_wall_radar',
                               -- CP37 (migration 0030 — THIS migration) — Wave K
                               -- cohort 3 lawful-intercept / network-surveillance
                               -- platforms (parity with identifiers extension).
                               'network_surveillance'
                           )),

    notes                  TEXT,

    -- Audit timestamps
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Dedup UNIQUE 3-tuple (signature_name, source_id, cellular_generation);
    -- SQLite treats multiple NULL cellular_generation as distinct (desired for
    -- multi-gen rows). See migration 0027 for the full rationale.
    UNIQUE (signature_name, source_id, cellular_generation)
);

INSERT INTO behavioral_signatures_new SELECT * FROM behavioral_signatures;
DROP TABLE behavioral_signatures;
ALTER TABLE behavioral_signatures_new RENAME TO behavioral_signatures;

CREATE INDEX IF NOT EXISTS idx_behavioral_signatures_category     ON behavioral_signatures(device_category);
CREATE INDEX IF NOT EXISTS idx_behavioral_signatures_cellular_gen ON behavioral_signatures(cellular_generation);
CREATE INDEX IF NOT EXISTS idx_behavioral_signatures_name         ON behavioral_signatures(signature_name);

PRAGMA foreign_key_check;

-- Version bump — CP37 / file 0030.
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (30, '0030_cp37_device_category_network_surveillance');

COMMIT;

PRAGMA foreign_keys = ON;
