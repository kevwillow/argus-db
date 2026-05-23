-- ============================================================================
-- Migration: 0028_cp34_network_discovery_protocol_pattern_identifier_type
-- Purpose:   CP34 — extend `identifiers.identifier_type` CHECK enum +1 net-new
--            value (58 → 59 cumulative):
--                - `network_discovery_protocol_pattern`
--
-- Surfaced:  Wave G/H v1 CCTV installer cohort (Track A). 645 raw discovery-
--            protocol findings across 8 vendors; 18 high-confidence after
--            disambig. Concrete evidence:
--                - Hikvision SADP port 8000 (7× hits in
--                  `RouterSadpDeviceInfo.java`)
--                - Hikvision JmDNS multicast 224.0.0.251
--                - Tiandy SADP-style port references (9 high-conf)
--                - Axis ONVIF/WS-Discovery in `com.axis.companion`
--                - Dahua `libSmartConfig.so` (AirKiss/SmartConfig WiFi
--                  provisioning via multicast credential push)
--
-- Authority: MAC-239 Wave G/H v1 integration cycle.
--            Board ratification 2026-05-23 (comment 50ffacc8): Gate I-3(a) —
--            inline mig-0028 admission this cycle; only 18 high-conf ship;
--            627 lower-conf → disambig_review_queue.json for next-cycle
--            review (see
--            `~/argus-internal/wave_g_h_v1_integration/staged/disambig_review_queue.json`).
--
-- Bible:     §11 #1   no fabrication — only 18 high-confidence promoted; 627
--                     low/medium/dropped-FP staged for queue review.
--            §11 #11  amendment-log discipline — CP34 entry to be appended to
--                     BIBLE_AMENDMENTS.md at integration close.
--            SAR-13   PRAGMA-first → sqlite_master.sql-first discipline:
--                     CHECK enum verified via sqlite_master DDL read pre-
--                     migration.
--
-- Pattern:   SQLite table-rebuild (CP21 cumulative-full-enum). Vanilla SQLite
--            cannot ALTER CHECK in place; identifiers rebuilt. Foreign keys
--            disabled outside transaction; new table created with extended
--            enum + ALL prior CHECK constraints preserved verbatim
--            (identifier_type 58→59 enum POST-extension; pair_kind 5-value
--            enum unchanged from CP31; source_type 10-value enum unchanged
--            from CP15); column-preserving INSERT via SELECT *; DROP old;
--            RENAME new; recreate indexes; foreign_key_check; schema_version
--            bump. behavioral_signatures untouched (no enum change there).
--
-- Idempotency:
--   - INSERT OR IGNORE INTO schema_version at footer makes version bump idempotent.
--   - Re-running against schema=28 DB produces identical sqlite_master strings
--     and identical row counts.
--
-- Migration-slot allocation:
--   0025  = CP31 FCC EAS identifier_type cluster + hub-and-spoke
--   0026  = CP32 §1 device_category enum extension automotive_telematics
--   0026a = MAC-204 phase10 vendor APK source admissions (data-only)
--   0027  = CP33 §1-§2 — cctv_camera + persistent_surveillance + through_wall_radar + imei_tac
--   0028  = CP34 — this migration (network_discovery_protocol_pattern)
-- ============================================================================

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- CHECK enum on identifier_type extended +1 (58 → 59 cumulative). ALL other
-- CHECK constraints (device_category 16-value enum from CP33, source_type
-- 10-value enum from CP15, confidence range, pair_kind 5-value enum from CP31)
-- preserved verbatim. Column shape unchanged from post-CP33 state.
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
                          -- CP34 (migration 0028 — this migration) — Wave G/H v1
                          -- CCTV cohort camera-discovery protocol pattern
                          -- (Hikvision SADP, Dahua AirKiss/SmartConfig, Tiandy
                          -- SADP-style, Axis ONVIF WS-Discovery). 18 high-conf
                          -- promoted at CP34; 627 low/medium/dropped-FP staged
                          -- for next-cycle review.
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
                          'through_wall_radar'
                      )),
    manufacturer      TEXT,
    model             TEXT,
    confidence        INTEGER CHECK (confidence BETWEEN 0 AND 100),
    source_url        TEXT NOT NULL,
    source_type       TEXT NOT NULL CHECK (source_type IN (
                          'official', 'regulatory', 'procurement',
                          'academic', 'foia', 'crowdsourced',
                          'inferred', 'manufacturer_doc',
                          'manufacturer_app',
                          -- CP15 (migration 0015) — primary_registry
                          'primary_registry'
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

-- Column-preserving copy. All columns implicit via SELECT *; only the
-- identifier_type CHECK enum changes vs the pre-rebuild table.
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate identifiers indexes (carry forward verbatim from 0027) ────────
CREATE INDEX IF NOT EXISTS idx_identifiers_identifier
    ON identifiers(identifier);
CREATE INDEX IF NOT EXISTS idx_identifiers_type
    ON identifiers(identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_category
    ON identifiers(device_category);
CREATE INDEX IF NOT EXISTS idx_identifiers_superseded
    ON identifiers(superseded_by);
CREATE INDEX IF NOT EXISTS idx_identifiers_ident_type
    ON identifiers(identifier, identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_paired
    ON identifiers(paired_identifier_id);

-- ─── Schema version bump ────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (28, '0028_cp34_network_discovery_protocol_pattern_identifier_type');

COMMIT;

-- Post-migration foreign-key integrity check (outside transaction per SQLite docs).
PRAGMA foreign_key_check;

PRAGMA foreign_keys = ON;

-- ============================================================================
-- Post-migration state (expected):
--   - schema_version row (28, '0028_cp34_network_discovery_protocol_pattern_identifier_type')
--   - identifiers.identifier_type CHECK accepts 59 values (58 prior + 1 new)
--   - identifiers row count unchanged (column-preserving INSERT SELECT *)
--   - All 6 identifiers indexes recreated
--   - behavioral_signatures untouched
-- ============================================================================
