-- ============================================================================
-- Migration: 0026_cp32_device_category_automotive_telematics
-- Purpose:   CP32 §1 — extend `device_category` CHECK enum by +1 net-new
--            value (`automotive_telematics`) on BOTH host tables:
--              (1) `identifiers.device_category`        (12 → 13 values)
--              (2) `behavioral_signatures.device_category` (12 → 13 values)
--            Per CEO pre-clearance (Phase 0 evidence): CP32 dual-table
--            enum-parity sweep — `behavioral_signatures.device_category` is
--            a SEPARATE CHECK literal (not an FK to identifiers), and
--            downstream consumers (Lynceus, exports, coverage matrix) treat
--            device_category as a single conceptual vocabulary regardless of
--            host table. Keeping the two CHECK literals in lockstep is the
--            CP21 cumulative-full-enum sweep spirit.
--
-- Surfaced:  v1.4.1 Stage 1 — CP31 (mig-0025) inline Parrot Automotive arm
--            INSERT carried `primary_category='automotive_telematics'` as a
--            free-form TEXT value on `manufacturers.primary_category` (no
--            CHECK constraint there per the SAR-13 decision in 0025). The
--            CP32 dispatch codifies `automotive_telematics` as a first-class
--            `device_category` value, opening the door for future arm-row
--            identifier promotions (e.g. Parrot Automotive infotainment
--            telematics) to use category='automotive_telematics' instead of
--            the §11 #13 'unknown' carve-out.
--
-- Phase 1:   No row-level admission of automotive_telematics-category rows in
--            this Stage 2 Phase 1. The schema slot opens; promotions are a
--            future v1.4.x/v1.5.0 evidence-arrival concern.
--
-- Authority: MAC-219 (Stage 2 parent) → MAC-220 (Phase 1 — this migration)
--            CEO pre-clearance: dual-table extend (Phase 0 evidence file
--            `_preflight/preflight_evidence.md`); Option A-minimal disposition
--            per MAC-220 comment 5bb44924 ('Na_' sub-slot convention codifies
--            the 0026a_phase10 rename for the prior slot occupant).
--
-- Bible:     §11 #1   no fabrication — `automotive_telematics` cites the
--                     CP31 (mig-0025) Parrot Automotive arm row admission.
--            §11 #5   Phase boundaries respected — schema slot only; no row
--                     promotions land in this migration. Row-level use of
--                     the new category is a v1.4.x+ Stage-2 validator
--                     concern (future dispatch).
--            §11 #7   no main-table promotion without provenance — schema-
--                     only here. The CP31 Parrot Automotive arm row's
--                     `primary_category='automotive_telematics'` lives on
--                     `manufacturers.primary_category` (free-form TEXT, no
--                     CHECK extension scope on this migration).
--            §11 #8   no confidence drift — confidence column unchanged.
--            §11 #11  amendment-log discipline — sibling to BIBLE_AMENDMENTS
--                     CP32 entry (bundled 10-sub-section codification).
--            §11 anti-fabrication on CHECK constraints (SAR-13 §3399 PRAGMA-
--                     first discipline) — applied: pre-migration sqlite_master
--                     capture in `_phase_1_cp32_codification/sqlite_master_before.txt`
--                     verifies the 12-value baseline on BOTH tables.
--
-- Pattern:   SQLite table-rebuild (CP21 cumulative-full-enum). Vanilla
--            SQLite cannot ALTER CHECK in place; both tables must be
--            rebuilt. Foreign keys disabled outside transaction; new tables
--            created with the extended 13-value enum + ALL prior CHECK
--            constraints preserved verbatim (identifier_type 56-value enum,
--            pair_kind 5-value enum, source_type 10-value enum, cellular_
--            generation 4-value enum); column-preserving INSERT via SELECT *;
--            DROP old; RENAME new; recreate indexes (incl. the UNIQUE
--            constraint on behavioral_signatures); foreign_key_check;
--            schema_version bump; COMMIT.
--
-- Idempotency:
--   - INSERT OR IGNORE INTO schema_version at the migration footer makes the
--     version bump idempotent.
--   - The rebuild is structurally idempotent-by-end-state: re-running
--     against a schema=26 DB produces identical sqlite_master strings and
--     identical row counts (verified by Phase 1 audit deliverable
--     `_phase_1_cp32_codification/idempotency_2nd_run.txt`).
--
-- Migration-slot allocation:
--   0024  = CP29 vendor hostname corpus value classes
--   0025  = CP31 FCC EAS identifier_type cluster + hub-and-spoke + Parrot
--           Automotive arm INSERT
--   0026  = CP32 §1 device_category enum extension automotive_telematics
--           (this migration)
--   0026a = MAC-204 phase10 vendor APK source admissions (data-only, no
--           schema_version bump; renamed from 0026_phase10_*.sql per the
--           Na_ sub-slot convention codified in CP32 §1 narrative — see
--           BIBLE_AMENDMENTS.md)
-- ============================================================================

-- Idempotency guard (informational): if version=26 is already in
-- schema_version, the rebuild that follows produces the same end-state
-- (identical sqlite_master + identical row counts) and the INSERT OR IGNORE
-- INTO schema_version footer is a no-op. The 2nd-run audit deliverable
-- compares before/after dumps and confirms zero functional changes.

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column shape unchanged from post-0025 state (17 columns total).
-- CHECK enum on device_category extended +1 (12 → 13 cumulative).
-- ALL other CHECK enums preserved verbatim from the post-0025 sqlite_master:
--   - identifier_type: 56-value CP31 cumulative enum
--   - source_type:     10-value CP15 cumulative enum
--   - source_excerpt:  length(<=200) constraint
--   - confidence:      BETWEEN 0 AND 100
--   - pair_kind:        5-value CP31 cumulative enum
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
                          'equipment_class_code'
                      )),
    device_category   TEXT NOT NULL CHECK (device_category IN (
                          -- 0001 initial — 12 values
                          'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                          'drone', 'gunshot_detect', 'hacking_tool',
                          'covert_cam', 'gps_tracker', 'face_recog',
                          'drone_detect', 'unknown',
                          -- CP32 (migration 0026 — this migration) — automotive
                          -- telematics arm cluster (+1 net-new)
                          'automotive_telematics'
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
-- device_category CHECK enum changes vs the pre-rebuild table.
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate identifiers indexes (carry forward verbatim from 0025) ────────
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
-- Column shape unchanged from post-0010 (MAC-58) state. CHECK enum on
-- device_category extended +1 (12 → 13 cumulative). ALL other CHECK
-- constraints (cellular_generation 4-value enum, threshold_json/evidence_json
-- json_valid, confidence range) preserved verbatim. UNIQUE 3-tuple preserved.
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

    -- Device category — CP32 (migration 0026 — this migration) extends to
    -- 13 values to maintain enum parity with identifiers.device_category.
    -- Behavioral signatures inherit the same §11 #13 unknown-category
    -- carveout discipline.
    device_category        TEXT NOT NULL CHECK (device_category IN (
                               -- 0010 initial (MAC-58) — 12 values
                               'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                               'drone', 'gunshot_detect', 'hacking_tool',
                               'covert_cam', 'gps_tracker', 'face_recog',
                               'drone_detect', 'unknown',
                               -- CP32 (migration 0026 — this migration) — automotive
                               -- telematics arm cluster (+1 net-new); parity with
                               -- identifiers.device_category extension
                               'automotive_telematics'
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

-- ─── Recreate behavioral_signatures indexes (carry forward from 0010) ───────
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
    (26, '0026_cp32_device_category_automotive_telematics');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - MAC-219 (v1.4.1 Stage 2 — CP32 + Docs + Final Tag parent)
-- - MAC-220 (this dispatch — CP32 codification + mig-0026 + test refactor + bible)
-- - MAC-220 comment 5bb44924 (CEO Option A-minimal disposition: 0026a_ rename)
-- - db/migrations/0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql
--   (immediate-prior identifier_type/pair_kind/manufacturers extension; baseline
--    for the device_category sweep)
-- - db/migrations/0026a_phase10_vendor_apk_sources_admission.sql (data-only
--   addendum applying after this migration in the same numeric band per the
--   Na_ sub-slot convention)
-- - db/migrations/0010_*.sql (MAC-58 behavioral_signatures Option B — baseline
--   for the 12-value device_category enum on the second host table)
