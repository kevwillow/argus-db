-- ============================================================================
-- Migration: 0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac
-- Purpose:   CP33 — extend two CHECK enums on canonical schema:
--            §1 `device_category` CHECK enum +3 net-new values on BOTH host tables:
--                (1) `identifiers.device_category`           (13 → 16 values)
--                (2) `behavioral_signatures.device_category` (13 → 16 values)
--              New values:
--                - `cctv_camera`             (S2 commercial/consumer cohort)
--                - `persistent_surveillance` (S1 military/federal cohort)
--                - `through_wall_radar`      (S1 military/federal cohort)
--            §2 `identifier_type` CHECK enum +1 net-new value on `identifiers`:
--                - `imei_tac`               (BOTH sessions proposed; merged single addition)
--
-- Surfaced:  Wave v1.5.0 lexicon expansion — two parallel sandbox sessions
--            (S1 military/federal + S2 commercial/consumer) staged identical
--            `imei_tac` proposals plus distinct device_category proposals.
--            Validator merged at MAC-232 v1.5.0 Stage 1 integration.
--
-- Authority: MAC-232 (v1.5.0 Stage 1 parent dispatch)
--            Board ratification 2026-05-22 (comment 0ba8150f): all 7 gates
--            G-A through G-G approved; G-B (retroactive cctv_camera recat
--            of 7 vendors) executes at Step 6 AFTER this mig lands;
--            G-C (imei_tac forward-compatible enum, 0 rows promoted this cycle).
--
-- Bible:     §11 #1   no fabrication — each new enum value cites concrete
--                     cohort vendors (S1 + S2 proposed_bible_amendment_additions.md).
--            §11 #11  amendment-log discipline — bundled BIBLE_AMENDMENTS.md
--                     CP33 entry covers the 4-value extension.
--            §11 #13  Lynceus unknown-bucket carveout — new categories are
--                     PROMOTING (excluded-when-unknown does NOT apply).
--            SAR-13   PRAGMA-first → sqlite_master.sql-first discipline:
--                     CHECK enums verified via sqlite_master DDL read; preflight
--                     evidence captured in `_phase_3_cp33_preflight/sqlite_master_before.txt`.
--
-- Pattern:   SQLite table-rebuild (CP21 cumulative-full-enum). Vanilla SQLite
--            cannot ALTER CHECK in place; both tables rebuilt. Foreign keys
--            disabled outside transaction; new tables created with extended
--            enum + ALL prior CHECK constraints preserved verbatim
--            (identifier_type 57-value enum POST-extension; pair_kind 5-value
--            enum unchanged from CP31; source_type 10-value enum unchanged
--            from CP15; cellular_generation 4-value enum unchanged from
--            MAC-58); column-preserving INSERT via SELECT *; DROP old;
--            RENAME new; recreate indexes (incl. UNIQUE constraint on
--            behavioral_signatures); foreign_key_check; schema_version bump.
--
-- Idempotency:
--   - INSERT OR IGNORE INTO schema_version at footer makes version bump idempotent.
--   - Re-running against schema=27 DB produces identical sqlite_master strings
--     and identical row counts.
--
-- Migration-slot allocation:
--   0024  = CP29 vendor hostname corpus value classes
--   0025  = CP31 FCC EAS identifier_type cluster + hub-and-spoke
--   0026  = CP32 §1 device_category enum extension automotive_telematics
--   0026a = MAC-204 phase10 vendor APK source admissions (data-only)
--   0027  = CP33 §1-§2 — this migration
-- ============================================================================

-- Idempotency guard (informational): if version=27 is already in
-- schema_version, the rebuild that follows produces the same end-state
-- (identical sqlite_master + identical row counts) and the INSERT OR IGNORE
-- INTO schema_version footer is a no-op.

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column shape unchanged from post-0026 state (17 columns total).
-- CHECK enum on device_category extended +3 (13 → 16 cumulative).
-- CHECK enum on identifier_type extended +1 (56 → 57 cumulative).
-- ALL other CHECK enums preserved verbatim from the post-0026 sqlite_master:
--   - source_type:     10-value CP15 cumulative enum
--   - source_excerpt:  length(<=200) constraint
--   - confidence:      BETWEEN 0 AND 100
--   - pair_kind:       5-value CP31 cumulative enum (unchanged; G-E confirmed
--                      dispatch's "4 values on disk" claim was stale)
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
                          -- CP33 (migration 0027 — this migration) — GSMA TAC
                          -- (8-digit IMEI Type Allocation Code) cluster;
                          -- admitted forward-compatible per G-C (0 rows
                          -- promoted this cycle; cohort backfill in future
                          -- v1.5.x). Dual-proposal merge: BOTH S1
                          -- (military/federal) and S2 (commercial/consumer)
                          -- sandbox sessions proposed identical addition.
                          'imei_tac'
                      )),
    device_category   TEXT NOT NULL CHECK (device_category IN (
                          -- 0001 initial — 12 values
                          'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                          'drone', 'gunshot_detect', 'hacking_tool',
                          'covert_cam', 'gps_tracker', 'face_recog',
                          'drone_detect', 'unknown',
                          -- CP32 (migration 0026) — automotive telematics arm cluster
                          'automotive_telematics',
                          -- CP33 (migration 0027 — this migration) — v1.5.0 cohort
                          -- lexicon expansion (+3 net-new)
                          'cctv_camera',              -- S2 commercial/consumer cohort
                          'persistent_surveillance',  -- S1 military/federal cohort
                          'through_wall_radar'        -- S1 military/federal cohort (FCC §15.519 UWB-LE-only)
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

-- Column-preserving copy. 17 columns implicit via SELECT *; only the
-- device_category + identifier_type CHECK enums change vs the pre-rebuild table.
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate identifiers indexes (carry forward verbatim from 0026) ────────
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

-- ─── behavioral_signatures table rebuild ────────────────────────────────────
-- Column shape unchanged from post-0026 (MAC-58 + CP32) state. CHECK enum on
-- device_category extended +3 (13 → 16 cumulative) to maintain parity with
-- identifiers.device_category per CP32 precedent. ALL other CHECK constraints
-- (cellular_generation 4-value enum, threshold_json/evidence_json json_valid,
-- confidence range) preserved verbatim. UNIQUE 3-tuple preserved.
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
    -- Structured JSON for queryability; example shape:
    --   {"paper_cite": "NDSS 2025 Marlin §4.2",
    --    "repo_sha": "<40-hex>",
    --    "files": [{"path": "src/foo.kt", "lines": [36, 37]}]}
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

    -- Device category — CP33 (migration 0027 — this migration) extends to
    -- 16 values to maintain enum parity with identifiers.device_category
    -- per CP32 precedent. Behavioral signatures inherit the same §11 #13
    -- unknown-category carveout discipline.
    device_category        TEXT NOT NULL CHECK (device_category IN (
                               -- 0010 initial (MAC-58) — 12 values
                               'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                               'drone', 'gunshot_detect', 'hacking_tool',
                               'covert_cam', 'gps_tracker', 'face_recog',
                               'drone_detect', 'unknown',
                               -- CP32 (migration 0026) — automotive telematics arm
                               'automotive_telematics',
                               -- CP33 (migration 0027 — this migration) — v1.5.0
                               -- cohort lexicon expansion (+3 net-new); parity with
                               -- identifiers.device_category extension per CP32
                               -- precedent
                               'cctv_camera',              -- S2 commercial/consumer cohort
                               'persistent_surveillance',  -- S1 military/federal cohort
                               'through_wall_radar'        -- S1 military/federal cohort (FCC §15.519 UWB-LE-only)
                           )),

    notes                  TEXT,

    -- Audit timestamps
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Dedup: same signature emitted by the same source under the same
    -- cellular_generation is one row, not N. Re-extraction of the same
    -- source repo produces UPSERT-shape behavior in the validator
    -- (DELETE-by-source_id is the existing idempotency pattern; see
    -- db/sources/deflock.py precedent).
    --
    -- Phase-2 self-review §2.4 disposition (2026-05-11): UNIQUE is the
    -- 3-tuple including cellular_generation. The dispatch §1.1 spec was
    -- 2-tuple (signature_name, source_id); Phase 2 verified against the
    -- rayhunter 6α surfacing that staging style is one signature_name
    -- per layer (e.g., "RRC Null Cipher (EEA0) multi-path" is ONE row
    -- folding 5 code paths; "NAS Null Cipher (EMM Security-Mode-Command
    -- EEA0/NEA0)" is a SEPARATE row). 2-tuple suffices today, but the
    -- 3-tuple is forward-proof for staging-style evolution where future
    -- Wave-B/C surfacings may split a multi-cellular_gen signature into
    -- per-gen rows. SQLite UNIQUE treats multiple NULL values as
    -- distinct, which is the desired behavior for multi-gen rows
    -- (cellular_generation=NULL means "applies to multiple gens or N/A";
    -- two such rows with same signature_name + same source_id would be a
    -- legitimate duplication only if signature_name granularity fails,
    -- which it shouldn't).
    UNIQUE (signature_name, source_id, cellular_generation)
);

-- Column-preserving copy. All columns implicit via SELECT *; only the
-- device_category CHECK enum changes vs the pre-rebuild table.
INSERT INTO behavioral_signatures_new SELECT * FROM behavioral_signatures;

DROP TABLE behavioral_signatures;

ALTER TABLE behavioral_signatures_new RENAME TO behavioral_signatures;

-- ─── Recreate behavioral_signatures indexes (carry forward from 0026) ───────
CREATE INDEX IF NOT EXISTS idx_behavioral_signatures_category
    ON behavioral_signatures(device_category);
CREATE INDEX IF NOT EXISTS idx_behavioral_signatures_cellular_gen
    ON behavioral_signatures(cellular_generation);
CREATE INDEX IF NOT EXISTS idx_behavioral_signatures_name
    ON behavioral_signatures(signature_name);

-- ─── FK integrity assertion ──────────────────────────────────────────────────
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (27, '0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - MAC-232 (v1.5.0 Stage 1 parent dispatch)
-- - Board ratification 2026-05-22 (comment 0ba8150f): G-A through G-G approved
-- - db/migrations/0026_cp32_device_category_automotive_telematics.sql
--   (immediate-prior device_category dual-table extension; baseline pattern
--    mirrored here for the +3 v1.5.0 lexicon expansion)
-- - db/migrations/0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql
--   (immediate-prior identifier_type extension; baseline 56-value enum
--    preserved verbatim + 1 net-new imei_tac slot appended)
-- - db/migrations/0010_*.sql (MAC-58 behavioral_signatures Option B — baseline
--   for the device_category enum on the second host table)
-- - _phase_3_cp33_preflight/sqlite_master_before.txt (SAR-13 preflight DDL
--   capture; baseline 56 / 13 / 13 / 5 value counts verified)
