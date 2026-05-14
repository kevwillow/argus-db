-- ============================================================================
-- Migration: 0018_identifier_types_extension_batch
-- Purpose:   Extend `identifiers.identifier_type` CHECK enum with 14 net-new
--            types per CP20 SAR-13 §S.3 (vendor-anchored / device-naming
--            cluster) — the Q1 Validator surface-back 18-type slate, minus
--            4 entries (`rf_channel`, `alpr_model`, `rf_protocol_constant`,
--            `rf_burst_duration`) that are already present in the cumulative
--            CHECK enum from migrations 0013 / 0014. Final CHECK cardinality:
--            27 prior + 14 net-new = 41 values cumulatively.
-- Surfaced:  MAC-104 Validator surface-back
--            [`3e34d5d0`](/MAC/issues/MAC-104#comment-3e34d5d0-c5b6-4e88-b5aa-220266c3cc04)
--            §6.4 Q1 vocab-extension slate (Wave-A deferred-dir cohort:
--            src=29 imp1sec/qcsuper, src=30 osmocom/osmo-bts-stuff, src=31
--            tshark filters, src=32 AIMSICD, src=33 Marlin et al., src=34
--            Pelo Cybersecurity firmware-mining, src=35 chrysn x509,
--            src=36 OEM service-mode catalog).
-- Authority: CEO ratification at MAC-104 close 2026-05-14 (CP20 bible
--            commit [`8de7309`](/MAC/issues/MAC-104) §A SAR-13 + Sequencing
--            #3). Dispatch under MAC-109 (this migration) +
--            blocked-downstream MAC-110 (Validator close-out).
-- Bible:     §11 #11 — schema changes are CEO-only ratification post-board.
--            CP20 §A SAR-13 §S.3 codifies the routing principle that 18
--            vendor-anchored / device-naming candidate types land in the
--            CHECK enum via this migration, while 6 detector-internal
--            candidate types (`tunable_threshold`, `wireshark_field`,
--            `logcat_detection_string`, `threat_level_enum`,
--            `modem_device_path`, `oem_service_mode_command`) route to
--            `behavioral_signatures.signature_name` (free TEXT; no schema
--            change required — see §"behavioral_signatures routing
--            principle" footer below).
-- Pattern:   SQLite table-rebuild per 0009 / 0011 / 0013 / 0014 precedent.
--            PRAGMA foreign_keys=OFF outside transaction; CREATE _new with
--            extended CHECK; INSERT SELECT * (column-preserving copy);
--            DROP old; RENAME _new → old; recreate indexes; foreign_key_check;
--            schema_version bump; COMMIT; foreign_keys=ON.
-- Risk:      Low. Pure additive enum extension. Column shape unchanged
--            (16 columns post-0012; carries paired_identifier_id + pair_kind
--            forward verbatim). Active 22,319 / total 22,377 / superseded 58
--            preserved via column-list-preserving INSERT SELECT.
-- ============================================================================
--
-- Migration-slot allocation chain of record:
--   0001-0009  see 0009 header for the full chain
--   0010 = behavioral_signatures NEW TABLE (CP14)
--   0011 = ble_manufacturer_id identifier_type extension (CP14)
--   0012 = paired_identifier_id + pair_kind columns (CP14)
--   0013 = drone-RID + proprietary-protocol identifier_types (CP14)
--   0014 = surveillance-metadata identifier_types (CP14)
--   0015 = primary_registry source_type extension (CP15)
--   0016 = deployment_observations LICENSE column (HB75 §4 chunk 1)
--   0017 = source_reclassifications NEW TABLE (CP19)
--   0018 = identifier_types extension batch — CP20 SAR-13 §S.3 routing
--          (this migration; 14 net-new values; 41-value cumulative CHECK)
--
-- File-slot naming note: the MAC-109 dispatch + bible CP20 §A "Sequencing"
-- #3 both reference "Migration 0011" by legacy naming. Slot 0011 is occupied
-- by `0011_ble_manufacturer_id_identifier_type_extension.sql` (applied as
-- schema_version=11). The next free slot is 0018, which matches the
-- dispatch step 4 assertion `schema_version 17 → 18`. Filename and
-- schema_version version are aligned at 0018 per the established
-- 0001-0017 convention.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative CHECK enum (27 prior + 14 net-new = 41 values total)
-- ─────────────────────────────────────────────────────────────────────────────
-- The 27 prior values are paste-verified verbatim against the live `identifiers`
-- table CHECK clause from migrations 0001 (9 values) + 0009 (3 values) + 0011
-- (1 value) + 0013 (13 values) + 0014 (1 value). Per
-- `feedback_cumulative_check_enum_across_sequenced_migrations.md` (cited by
-- bible CP20 §A "Sequencing" #3), the rebuild-pattern migration MUST carry
-- forward ALL prior CHECK enum values, not just its own delta.
--
-- Of the 18 types in the MAC-109 dispatch §A Q1 slate, four are already in
-- the cumulative CHECK enum from migrations 0013 / 0014 and therefore appear
-- only once (no behavior change vs the cumulative carry-forward):
--   * `rf_channel`            (already added by migration 0013 — Drone-RID cluster)
--   * `alpr_model`            (already added by migration 0014 — surveillance metadata)
--   * `rf_protocol_constant`  (already added by migration 0013 — proprietary-protocol)
--   * `rf_burst_duration`     (already added by migration 0013 — proprietary-protocol)
--
-- The 14 net-new types (CP20 SAR-13 §S.3 vendor-anchored / device-naming
-- cluster) added by this migration:
--   1.  `ble_protocol_byte_table`    — BLE protocol byte table (vendor-shipped
--                                       protocol descriptor surface; src=29 qcsuper).
--   2.  `ble_service_uuid`           — BLE GATT service UUID, distinct namespace
--                                       from pre-CP13 `ble_service` (which was the
--                                       128-bit service UUID name shape) and from
--                                       `ble_uuid` (generic). Disambiguates per
--                                       CP20 SAR-13 §S.3 vendor-anchored boundary.
--   3.  `ble_company_id`             — BLE SIG company identifier surfaced from
--                                       vendor-shipped firmware (chip-vendor lens).
--                                       Distinct from `ble_manufacturer_id`
--                                       (CP14/0011) which is the runtime advertising
--                                       company-ID byte sequence as observed on the
--                                       wire — `ble_company_id` is the
--                                       vendor-static binding.
--   4.  `frequency_band`             — Vendor-anchored RF frequency band name
--                                       (e.g., LTE B5, GSM 850, 5GHz UNII-3).
--   5.  `ble_protocol_byte`          — Single BLE protocol byte value (PDU type
--                                       discriminator at byte-level granularity).
--   6.  `operator_profile`           — Surveillance-operator profile string. G-17
--                                       HOLD (migration 0014 header) resolved at
--                                       CP20 §A "Q1 vocab-extension slate routing —
--                                       RESOLVED at SAR-13 S.3 (18 → identifier_type
--                                       via migration 0011)" — operator_profile
--                                       binds to identifier_type per CEO ratification.
--   7.  `x509_cert_sha256_prefix`    — x.509 certificate SHA-256 hash prefix
--                                       embedded in vendor firmware (chrysn surfacing).
--   8.  `ble_adv_interval`           — BLE advertising interval (ms) value with
--                                       vendor-anchored binding.
--   9.  `ble_payload_offset`         — BLE advertising payload byte offset
--                                       (vendor-specific field-position binding).
--  10. `firmware_sha256_hash`        — Firmware image SHA-256 hash
--                                       (vendor/firmware-version anchor).
--  11. `network_endpoint`            — Vendor-anchored network endpoint
--                                       (URL / IP:port / FQDN) that vendor firmware
--                                       talks to as control/telemetry surface.
--  12. `firmware_image_variant`      — Vendor firmware build variant string
--                                       (e.g., DEBUG vs RELEASE, region SKU).
--  13. `qualcomm_chip_format_id`     — Qualcomm chip format identifier surfaced
--                                       from MBN binary mining (src=29 qcsuper +
--                                       Pelo Cybersecurity firmware-mining).
--  14. `firmware_branded_string`     — Vendor-branded string embedded in firmware
--                                       binaries (model name, SKU, etc.).
--  15. `rf_channel`                  — DROPPED — already in CHECK from migration 0013.
--  16. `alpr_model`                  — DROPPED — already in CHECK from migration 0014.
--  17. `rf_protocol_constant`        — DROPPED — already in CHECK from migration 0013.
--  18. `rf_burst_duration`           — DROPPED — already in CHECK from migration 0013.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- behavioral_signatures routing principle (CP20 SAR-13 §S.3) — codification
-- (NO SCHEMA CHANGE for this footnote — documented here for Validator handoff)
-- ─────────────────────────────────────────────────────────────────────────────
-- The 6 detector-internal candidate types route to
-- `behavioral_signatures.signature_name` (free TEXT; no enum constraint;
-- added by migration 0010_behavioral_signatures.sql). Schema accepts the
-- 38-row backfill semantics without further migration:
--
-- | candidate_type             | rows | rationale (CP20 §A SAR-13 §S.3)
-- |--- |--- |---
-- | tunable_threshold          | 9 | src=32 AIMSICD signal-strength deltas; detector tuning, not device naming
-- | wireshark_field            | 7 | src=31 tshark display filters; detector-side traffic patterns
-- | logcat_detection_string    | 6 | src=32 AIMSICD SMS-pattern signatures; detector observation surface
-- | threat_level_enum          | 6 | src=32 AIMSICD Status state machine; detector internal state
-- | modem_device_path          | 5 | src=32 /dev/smd* AT-command paths; detector probe surface
-- | oem_service_mode_command   | 5 | src=32 Samsung MulticlientRil OEM hooks; detector probe command
--
-- Validator executes the 38-row backfill under MAC-110 as
-- `behavioral_signatures` INSERTs (populating `signature_name`, `device_category`
-- — likely `imsi_catcher` for src=32; per-row Validator judgment for src=31 —
-- `threshold_json` or `evidence_json` capturing the detector-side parameter,
-- `confidence` ≤70 per §8.2 crowdsourced band).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 hard-rule discipline (cite verbatim per 0009 / 0011 / 0013 / 0014 precedent)
-- ─────────────────────────────────────────────────────────────────────────────
--   §11 #1   no fabrication — every new CHECK enum value cites canon: CP20 §A
--              SAR-13 §S.3 Q1 vocab-extension slate (MAC-104 Validator
--              surface-back 3e34d5d0 §6.4 Q1; 4-shape Phase-1 cohort surfacing
--              under SAR-13 §S.1).
--   §11 #7   no main-table promotion without provenance — schema-only here;
--              promotion of the 18-type-banded rows happens under MAC-110
--              Validator close-out (38 detector-internal rows route to
--              behavioral_signatures per §S.3; remaining vendor-anchored rows
--              land in identifiers via this migration's enum).
--   §11 #8   no confidence drift — confidence column unchanged; same
--              §7.3 intake-side discipline.
--   §11 #11  amendment-log discipline — coordinated commit pairs this migration
--              with bible CP20 §A SAR-13 §S.3 amendment-log entry (commit
--              8de7309 2026-05-14).
--   §11 #15  no decompiled vendor source in git index — N/A; schema-only.
--   §11 #16  facts-only promotion from public-but-unlicensed sources —
--              orthogonal to this migration; binds row-level provenance
--              discipline at Validator promotion time (MAC-110), not at
--              schema-extension time.
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column list reflects post-0012 state (paired_identifier_id + pair_kind
-- added by 0012; preserved verbatim). CHECK enum carries forward all 27
-- prior values + adds 14 net-new (41 cumulative values).
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
                          -- CP20 (migration 0018 — this migration) — SAR-13 §S.3
                          -- vendor-anchored / device-naming cluster (14 net-new;
                          -- 4 dispatch entries — rf_channel, alpr_model,
                          -- rf_protocol_constant, rf_burst_duration — were
                          -- already present from migrations 0013/0014 above
                          -- and are not re-listed here)
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
                          'firmware_branded_string'
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
                                 'firmware_generation'
                             )
                         )
);

-- Column-preserving copy. All 16 columns enumerated implicitly via SELECT *;
-- only the CHECK enum changes vs the pre-rebuild table.
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate indexes (carry forward from 0014) ─────────────────────────────
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

-- ─── FK integrity assertion ──────────────────────────────────────────────────
-- foreign_key_check returns zero rows for a clean rebuild. The wrapper at
-- db/validation/migration_0018_verify.py (if added) is the canonical
-- idempotency boundary mirroring migration_0009_verify.py precedent;
-- direct executescript() on a post-migration DB is structurally safe
-- (rebuild is column-and-data-preserving; INSERT OR IGNORE on schema_version
-- is a no-op for version 18).
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (18, '0018_identifier_types_extension_batch');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - PROJECT_BIBLE.md §11 #16 + BIBLE_AMENDMENTS.md CP20 §A SAR-13 §S.3
--   (this migration's schema-sibling)
-- - MAC-104 Validator surface-back 3e34d5d0 §6.4 Q1 (vocab-extension slate)
-- - MAC-109 (this migration's dispatch issue)
-- - MAC-110 (Validator close-out — bx_sig 38-row backfill blocked by this
--   migration landing)
-- - db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql
--   (table-rebuild precedent)
-- - db/migrations/0010_behavioral_signatures.sql (free-TEXT signature_name
--   surface for §S.3 detector-internal routing)
-- - db/migrations/0014_surveillance_metadata_identifier_types_extension.sql
--   (immediate-prior identifier_type enum extension; operator_profile G-17
--   HOLD resolved here under CP20 §A)
-- - feedback_cumulative_check_enum_across_sequenced_migrations.md
--   (cumulative carry-forward discipline)
-- - feedback_verify_enum_lists_against_migration_in_mac_dispatches.md
--   (paste-verify discipline)
-- - feedback_enum_amendment_needs_schema_migration_sibling.md
--   (this migration IS the schema-sibling per §11 #11)
