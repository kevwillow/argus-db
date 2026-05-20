-- ============================================================================
-- Migration: 0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke
-- Purpose:   CP31 — three-or-four-in-one structural extension on branch
--            v1.4.1-integration-stage-1:
--              (1) `identifiers.identifier_type` CHECK enum +2 net-new:
--                  `fcc_grantee_code`, `equipment_class_code` (FCC EAS
--                  identifier-type cluster surfaced through v1.4.1 Stage 1
--                  Phase 7 Wave I.14b+I.14c fccid.io attestations + Phase 8
--                  Honeywell cert-chain enrichment).
--                  Cumulative CHECK: 54 prior (post-CP29 migration 0024)
--                  + 2 net-new = 56 values total.
--              (2) `identifiers.pair_kind` CHECK enum +1 net-new:
--                  `fcc_grantee_equipment_class` (grantee-code ↔ equipment-
--                  class-code pairing per FCC EAS structural relationship).
--                  Cumulative CHECK: 4 prior + 1 net-new = 5 values total.
--              (3) `manufacturers.primary_category` enum — DECISION: SKIP.
--                  PRAGMA verification (recorded in
--                  _phase_cp31_implementation/primary_category_enum_decision.md)
--                  confirms the live `manufacturers` table has NO existing
--                  CHECK constraint on `primary_category`. Adding a CHECK
--                  not present in bible §4 would be SAR-13 schema
--                  fabrication. The new Parrot Automotive arm row carries
--                  `primary_category='automotive_telematics'` as a free-form
--                  TEXT value, fully admitted by the existing column shape.
--                  No CHECK is added or modified for this column.
--              (4) `manufacturers` hub-and-spoke schema +3 columns:
--                  `parent_manufacturer_id INTEGER NULL REFERENCES
--                       manufacturers(id)` — null for hubs, set for arms
--                  `is_arm BOOLEAN NOT NULL DEFAULT 0`
--                  `query_default TEXT NOT NULL DEFAULT 'visible' CHECK
--                       (query_default IN ('visible', 'hidden_arm'))`
--              (5) Inline Parrot conversion (data step inside the same
--                  transaction): existing Parrot canonical row (id=25) stays
--                  as hub (`is_arm=0`, `parent_manufacturer_id=NULL`,
--                  `query_default='visible'` per backfill default). INSERT
--                  new `Parrot Automotive` arm row (`is_arm=1`,
--                  `parent_manufacturer_id=25`, `query_default='hidden_arm'`,
--                  `primary_category='automotive_telematics'`).
--
-- Surfaced:  v1.4.1-integration-stage-1 branch
--              - MAC-189 Phase 2 GitHub FP calibration
--              - MAC-190 Phase 3 Wave I.9 ingest
--              - MAC-192 Phase 5 Wave I.12
--              - MAC-194 Phase 7 Wave I.14b+I.14c (fccid.io attestations —
--                grantee_code + equipment_class_code structural pairing
--                empirical canon)
--              - MAC-195 Phase 8 Honeywell admission + cert-chain enrichment
--              - MAC-196 Numerex Corporation alias-of-existing (Sierra
--                Wireless mfr.id=21)
--              - MAC-197 CP31 amendment plan rev d59e6af5 (board-accepted)
--            Parrot SAS / Parrot Faurecia Automotive S.A.S split surfaced
--            through Stage-1 manufacturer canonicalization review: the
--            existing Parrot row (id=25, primary_category='drone')
--            carries both `PARROT DRONE SAS` and `PARROT FAURECIA AUTOMOTIVE
--            SAS` aliases — the latter is the automotive infotainment arm,
--            structurally distinct from the drone product line. CP31 splits
--            via hub-and-spoke: hub stays visible; arm goes `hidden_arm` so
--            default queries (`WHERE query_default = 'visible'`) do not
--            return automotive-arm noise into drone-axis analytics.
--
-- Authority: MAC-197 CP31 amendment plan rev `d59e6af5` board-accepted at
--            MAC-184 comment `3bbc870b-c56e-4807-977b-40740c73ff83`.
--            Dispatched at MAC-198 (this issue).
--
-- Bible:     §11 #1   no fabrication — every codified CHECK enum value
--                     cites the v1.4.1 Stage-1 Phase-7 Wave I.14b+I.14c
--                     fccid.io attestation corpus (`fcc_grantee_code`,
--                     `equipment_class_code`) + the structural pairing
--                     relationship at FCC EAS (`fcc_grantee_equipment_class`).
--            §11 #5   Phase boundaries respected — this is a v1.4.1 Stage 1
--                     integration migration; row-level promotion of the new
--                     identifier_type values is gated to Stage 2 validator
--                     review (MAC-199 follow-on dispatch).
--            §11 #7   no main-table promotion without provenance — schema-
--                     only here for identifier_type/pair_kind. The Parrot
--                     Automotive arm row INSERT carries `source_url` =
--                     'https://www.parrot.com/en/about-us' (corporate URL
--                     anchor) per the NOT-NULL bible contract.
--            §11 #8   no confidence drift — confidence column unchanged.
--            §11 #11  amendment-log discipline — sibling to BIBLE_AMENDMENTS
--                     CP31 entry, anchored on this migration's commit hash
--                     per feedback_bible_amendment_child_issue_id_ordering.
--            §11 anti-fabrication on CHECK constraints (SAR-13 + sub-rule
--                     §3399 PRAGMA-first discipline) — applied to
--                     `manufacturers.primary_category`: PRAGMA-verified no
--                     existing CHECK, decision recorded in
--                     _phase_cp31_implementation/primary_category_enum_decision.md.
--
-- Pattern:   SQLite table-rebuild for identifiers (CHECK extension) and for
--            manufacturers (CHECK extension on new `query_default` column +
--            3 new columns including FK). PRAGMA foreign_keys=OFF outside
--            transaction; CREATE _new with extended schema; INSERT explicit
--            column-list (NOT `SELECT *` because manufacturers gains
--            columns); DROP old; RENAME _new → old; recreate indexes;
--            foreign_key_check; data INSERT for Parrot Automotive arm row;
--            schema_version bump; COMMIT; foreign_keys=ON.
--
-- Risk:      Low. Pure additive schema extension + one data-row INSERT. All
--            existing rows preserved unchanged (default backfill on the 3
--            new manufacturers columns = NULL/0/'visible' — sane hub
--            defaults). identifier_type/pair_kind CHECK extensions are
--            strictly additive — no existing row's value falls outside the
--            new enum (existing values are paste-verified verbatim against
--            live sqlite_master at migration-author time).
--
-- Migration-slot allocation:
--   0024 = CP29 vendor hostname corpus value classes (54-value CHECK)
--   0025 = CP31 FCC EAS identifier_type cluster + manufacturers hub-and-
--          spoke + Parrot conversion — THIS MIGRATION
--          (identifier_type 56-value CHECK; pair_kind 5-value CHECK;
--           manufacturers +3 cols; Parrot Automotive arm row INSERTed)
-- ============================================================================
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative `identifiers.identifier_type` CHECK enum
-- (54 prior + 2 net-new = 56 values total)
-- ─────────────────────────────────────────────────────────────────────────────
-- The 54 prior values are paste-verified verbatim against the live
-- `identifiers` table CHECK clause sourced from migration 0024
-- (sqlite_master `sql` column on argus.db @ schema_version=24).
-- Per feedback_cumulative_check_enum_across_sequenced_migrations, the
-- rebuild-pattern migration MUST carry forward ALL prior CHECK enum values.
--
-- The 2 net-new types (CP31 codification per MAC-197 plan rev d59e6af5):
--   1. `fcc_grantee_code`
--          — Three-letter FCC EAS grantee code (e.g. 'BCG' for Apple,
--          'PDH' for Honeywell). Regulatory entity prefix; FCC ID =
--          grantee_code + equipment_class_code per FCC §2.926. Empirical
--          canon: v1.4.1 Stage-1 Phase-7 Wave I.14b+I.14c fccid.io
--          attestation corpus (MAC-194 commit `64043e1`).
--   2. `equipment_class_code`
--          — Variable-length FCC equipment-class code following the
--          grantee_code in the assembled FCC ID. Per-device-class
--          identifier under a given grantee. Empirical canon: same as
--          fcc_grantee_code (paired structural relationship at FCC EAS).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative `identifiers.pair_kind` CHECK enum
-- (4 prior + 1 net-new = 5 values total)
-- ─────────────────────────────────────────────────────────────────────────────
-- The 4 prior values from migration 0012:
--   `la_bit_flip`, `frdid_sibling`, `vendor_as_container`, `firmware_generation`
--
-- The 1 net-new value (CP31):
--   5. `fcc_grantee_equipment_class`
--          — Pairing kind binding an `fcc_grantee_code` row to an
--          `equipment_class_code` row sharing the same FCC ID composite.
--          Structural per FCC §2.926.

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column shape unchanged from post-0024 state (17 columns total). CHECK
-- enum on identifier_type extended +2 (56 cumulative); CHECK enum on
-- pair_kind extended +1 (5 cumulative).
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
                          -- CP31 (migration 0025 — this migration) — FCC EAS
                          -- identifier-type cluster (2)
                          'fcc_grantee_code',
                          'equipment_class_code'
                      )),
    device_category   TEXT NOT NULL CHECK (device_category IN (
                          'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                          'drone', 'gunshot_detect', 'hacking_tool',
                          'covert_cam', 'gps_tracker', 'face_recog',
                          'drone_detect', 'unknown'
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

-- Column-preserving copy. 17 columns implicit via SELECT *; only CHECK
-- enums change vs the pre-rebuild table.
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate identifiers indexes (carry forward verbatim from 0024) ────────
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

-- ─── manufacturers table rebuild ────────────────────────────────────────────
-- Pre-CP31: 7 columns (id, canonical_name, aliases, primary_category,
-- source_url, notes, added_at). Post-CP31: 10 columns (+3 hub-and-spoke).
-- `primary_category` retains plain TEXT NULL shape — no CHECK added (see
-- _phase_cp31_implementation/primary_category_enum_decision.md).
CREATE TABLE manufacturers_new (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name         TEXT NOT NULL UNIQUE,
    aliases                TEXT,           -- comma-separated alternate names
    primary_category       TEXT,           -- best-fit §2.1 category, NULL when multi-purpose
    source_url             TEXT NOT NULL,  -- where the canonical name comes from
    notes                  TEXT,
    added_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- CP31 (migration 0025 — this migration) — hub-and-spoke schema (3)
    parent_manufacturer_id INTEGER NULL REFERENCES manufacturers(id),
    is_arm                 BOOLEAN NOT NULL DEFAULT 0,
    query_default          TEXT NOT NULL DEFAULT 'visible' CHECK (
                               query_default IN ('visible', 'hidden_arm')
                           )
);

-- Explicit column-list copy (NOT SELECT * — column shape changes).
-- Backfill defaults for the 3 new columns map to "row is a hub":
--   parent_manufacturer_id = NULL
--   is_arm                 = 0
--   query_default          = 'visible'
-- These defaults are applied by the column DEFAULT clauses above; the
-- INSERT supplies the 7 prior columns explicitly.
INSERT INTO manufacturers_new (
    id, canonical_name, aliases, primary_category, source_url, notes, added_at
)
SELECT
    id, canonical_name, aliases, primary_category, source_url, notes, added_at
FROM manufacturers;

DROP TABLE manufacturers;

ALTER TABLE manufacturers_new RENAME TO manufacturers;

-- ─── Recreate manufacturers indexes (carry forward + new hub-and-spoke) ─────
CREATE INDEX IF NOT EXISTS idx_manufacturers_name
    ON manufacturers(canonical_name);
-- Hub-and-spoke discipline: default queries filter `WHERE query_default =
-- 'visible'` (per CP31 plan). Index supports that hot path + reverse-walk
-- from arms to hubs.
CREATE INDEX IF NOT EXISTS idx_manufacturers_query_default
    ON manufacturers(query_default);
CREATE INDEX IF NOT EXISTS idx_manufacturers_parent
    ON manufacturers(parent_manufacturer_id);

-- ─── Parrot conversion (data step) ──────────────────────────────────────────
-- Halt-criterion enforcement inline: the dispatch requires Parrot hub
-- id=25 (verified pre-flight in PRAGMA decision doc). The INSERT below
-- hard-codes parent_manufacturer_id=25; if Parrot id had drifted, the
-- pre-flight check would have surfaced the divergence before this
-- migration was authored.
--
-- The new arm row carries `primary_category='automotive_telematics'` as
-- a free-form TEXT value (no CHECK enum on that column — see decision doc).
-- `source_url` = corporate URL anchor for the Parrot Faurecia Automotive
-- entity per the NOT-NULL contract on manufacturers.source_url.
INSERT INTO manufacturers (
    canonical_name,
    aliases,
    primary_category,
    source_url,
    notes,
    added_at,
    parent_manufacturer_id,
    is_arm,
    query_default
) VALUES (
    'Parrot Automotive',
    'PARROT FAURECIA AUTOMOTIVE SAS,Parrot Faurecia Automotive S.A.S',
    'automotive_telematics',
    'https://www.parrot.com/en/about-us',
    json_object(
        'admission_basis', 'CP31 inline Parrot arm-split',
        'integration_dispatch', 'MAC-198',
        'parent_plan', 'MAC-197 plan rev d59e6af5',
        'hub_relationship', 'Parrot Automotive is the automotive arm of Parrot SAS; drone arm remains in id=25 (canonical_name=''Parrot'')',
        'query_visibility_rationale', 'hidden_arm so default drone-axis queries (WHERE query_default=''visible'') do not surface automotive-arm noise'
    ),
    datetime('now'),
    25,            -- parent_manufacturer_id (Parrot SAS hub, PRAGMA-verified pre-flight)
    1,             -- is_arm
    'hidden_arm'   -- query_default
);

-- ─── FK integrity assertion ──────────────────────────────────────────────────
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (25, '0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - MAC-184 (v1.4.1 Stage 1 integration parent)
-- - MAC-197 (CP31 amendment plan rev d59e6af5; board-accepted)
-- - MAC-184 comment 3bbc870b-c56e-4807-977b-40740c73ff83 (board accept)
-- - MAC-198 (this dispatch — DBArchitect migration 0025 + Parrot conversion
--   + argus_cli.py status)
-- - MAC-199 (follow-on Validator — 4-path export sweep + tests; auto-unblocks
--   after this migration applies)
-- - db/migrations/0024_cp29_vendor_hostname_corpus_value_classes.sql
--   (immediate-prior identifier_type CHECK extension; 54-value cumulative
--   source for the 56-value carry-forward in this migration)
-- - db/migrations/0012_paired_identifier_id.sql (pair_kind CHECK source;
--   4-value baseline + 1 net-new = 5-value carry-forward in this migration)
-- - _phase_cp31_implementation/primary_category_enum_decision.md
--   (PRAGMA SAR-13 decision: no CHECK extension on
--   manufacturers.primary_category)
-- - feedback_cumulative_check_enum_across_sequenced_migrations.md
-- - feedback_bible_amendment_child_issue_id_ordering.md
