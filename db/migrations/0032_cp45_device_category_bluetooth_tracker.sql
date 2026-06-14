-- ============================================================================
-- Migration: 0032_cp45_device_category_bluetooth_tracker
-- Issue:     MAC-388 (child of MAC-387) · Author: DBArchitect (6c93a466)
-- Applied:   2026-06-13 (staged write; CTO+CEO gate the commit — NO push)
-- CP:        CP45. Next-free CP above the landed maximum CP44 (the cross-vendor-
--            constant exclusion gate, §11 #21, landed at MAC-386 commit
--            8a4fab3). The MAC-351 cross-vendor draft was provisionally numbered
--            CP45 but was FOLDED into the consolidated CP44 at land time — per
--            the CP44 ledger Slot-disposition ("no separate CP45 lands for it"),
--            which FREES the CP45 slot. The MAC-321 WS-1 soft-reservation of a
--            CP44-tied `mig-0032 identifier_type` template explicitly left
--            "Migration 0032 / CP44 NOT consumed"; CP numbers are assigned at
--            land time as next-free, and the cross-vendor gate took CP44, so this
--            taxonomy migration (file 0032) takes CP45.
--            KNOWN LEDGER-VS-FILE OFFSET: migration FILE number (0032) and CP
--            number (CP45) drift independently in this repo (cf. mig-0025=CP31,
--            mig-0030=CP37). File = next-free file (0031 is last); CP = next-free
--            landed CP (CP44 is last landed). schema_version row = 32 (file 0032).
-- Purpose:   Extend `device_category` CHECK enum +1 net-new value on BOTH host
--            tables (identifiers + behavioral_signatures), maintaining the
--            CP32/CP33/CP37 dual-table parity invariant:
--              - `bluetooth_tracker`  (consumer/commercial BLE item-finder
--                 trackers: Apple AirTag / Find My network, Tile, Chipolo,
--                 Samsung SmartTag — the MAC-363 cohort-1 BLE-tracker cohort).
-- Rationale: These rows are item-finder BLE trackers whose surveillance-relevant
--            property is real-time location-following via crowdsourced finder
--            networks — a distinct device class from the existing categories.
--            They were ingested at `device_category='unknown'` (OUI-level multi-
--            purpose discipline / §11 #13) pending a model-level category; the
--            cohort-1 service-UUID / FindMy / SmartTag attribution IS the model-
--            level evidence (§8.4 hardware-anchor sub-rule). MAC-388 Part B
--            recategorizes the 47 cite-verified rows into this new value.
-- Bible:     §11 #1  no fabrication — `bluetooth_tracker` cites concrete vendors
--                     (Apple/Tile/Chipolo/Samsung) and only pre-existing,
--                     CTO-cite-verified rows are recategorized (Part B); this
--                     migration adds ZERO rows.
--            §11 #11 amendment-log discipline — paired with a CP45 entry in
--                     docs/engineering/BIBLE_AMENDMENTS.md (no silent CP).
--            §11 #13 Lynceus unknown-bucket carve-out NARROWING — `bluetooth_
--                     tracker` is a PROMOTING category: rows recategorized out of
--                     'unknown' into it are no longer barred by the §11 #13
--                     unknown-category export ban (mirrors the CP37 network_
--                     surveillance promoting-category precedent). Export
--                     eligibility still requires the §4.4 type-map (the
--                     ble_service_uuid→ble_uuid MAP is the MAC-359 absorb, Part C)
--                     and the confidence/source/geographic gates.
--            SAR-13 sqlite_master-first — the _new DDL below was reproduced
--                     column-for-column and CHECK-for-CHECK from the LIVE
--                     post-0031 sqlite_master at author time (18-col identifiers
--                     INCLUDING the CP39 `severity` column + idx_identifiers_
--                     severity; 13-col behavioral_signatures; identifier_type /
--                     source_type / pair_kind / severity / json_valid / UNIQUE
--                     constraints preserved verbatim). NOT copied from migration
--                     0030 (which predates the 0031 severity column).
-- Pattern:   SQLite table-rebuild (CP21 cumulative-full-enum), mirrors 0030.
-- Idempotency: apply-once on a schema_version=31 DB. schema_version insert is
--            OR IGNORE. Re-running on an already-32 DB re-applies the identical
--            rebuild (enum already contains bluetooth_tracker) — safe but
--            unnecessary; gate on schema_version externally.
-- ============================================================================

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild (device_category +1: bluetooth_tracker) ───────
-- Reproduced verbatim from LIVE post-0031 sqlite_master, +1 enum value.
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
                          'network_surveillance',
                          -- CP45 (migration 0032 — THIS migration) — MAC-363 cohort-1
                          -- consumer BLE item-finder trackers (Apple AirTag / Find My,
                          -- Tile, Chipolo, Samsung SmartTag). PROMOTING category:
                          -- §11 #13 unknown-export ban does NOT apply once a row is
                          -- recategorized into it (parity with network_surveillance).
                          'bluetooth_tracker'
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
    -- ─── CP39 (migration 0031) — severity column (carried verbatim) ───────────
    -- Orthogonal axis to confidence. Confidence = identifier-veracity (intake
    -- side). Severity = surveillance-impact class (downstream consumer side).
    severity             TEXT CHECK (
                             severity IS NULL
                             OR severity IN ('high', 'medium', 'low')
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
CREATE INDEX IF NOT EXISTS idx_identifiers_severity   ON identifiers(severity);

-- ─── behavioral_signatures table rebuild (device_category +1, parity) ────────
-- behavioral_signatures has NO tracker rows to recategorize (Part B touches
-- identifiers only); the enum is extended here solely to preserve the
-- CP32/CP33/CP37 dual-table parity invariant.
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
    -- precedent; CP45 (this migration) adds bluetooth_tracker (+1).
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
                               -- CP37 (migration 0030) — Wave K cohort 3 lawful-
                               -- intercept / network-surveillance platforms
                               'network_surveillance',
                               -- CP45 (migration 0032 — THIS migration) — MAC-363
                               -- cohort-1 consumer BLE item-finder trackers (parity
                               -- with identifiers extension; 0 rows in this table).
                               'bluetooth_tracker'
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

-- Version bump — CP45 / file 0032.
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (32, '0032_cp45_device_category_bluetooth_tracker');

COMMIT;

PRAGMA foreign_keys = ON;
