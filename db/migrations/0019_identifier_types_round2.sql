-- ============================================================================
-- Migration: 0019_identifier_types_round2
-- Purpose:   Extend `identifiers.identifier_type` CHECK enum with 7 net-new
--            types per MAC-117 §1 routing slate (round-2 vocab extension,
--            CEO-ratified 2026-05-14 on the MAC-117 confirmation card with
--            no amendments to the slate). Final CHECK cardinality:
--            41 prior + 7 net-new = 48 values cumulatively.
-- Surfaced:  MAC-110 §E.4 — 107 round-2 vocab candidates pending board
--            decision (HOLD `id_type_vocab_round2_pending`, disposition
--            `pending_validator_retriage_mac107`). MAC-117 §1 routing
--            slate filed (A)/(B)/(C) bifurcation per SAR-13 §S.3: 7 types
--            (68 rows) → identifier_type via this migration; 5 labels
--            (38 rows) → behavioral_signatures.signature_name; 1 row
--            (attribution_conflict) → HOLD out_of_scope_v1 (already in
--            conflicts.id=5).
-- Authority: CEO ratification at MAC-117 confirmation interaction
--            `218b091a-b9e5-4d4f-a39b-5923c5f6892f` accepted 2026-05-14
--            (no slate amendments). Routing slate captured in MAC-117
--            issue document `routing_slate` rev 1
--            (`877c76b9-ec96-46f9-9a33-717095d260bd`).
-- Bible:     §11 #11 — schema changes are CEO-only ratification post-board.
--            SAR-13 §S.3 routing principle (broadcast-class device identifier
--            → identifier_type; detector-internal heuristic → behavioral_
--            signatures.signature_name; out-of-scope → HOLD/conflicts).
-- Pattern:   SQLite table-rebuild per 0009 / 0011 / 0013 / 0014 / 0018
--            precedent. PRAGMA foreign_keys=OFF outside transaction; CREATE
--            _new with extended CHECK; INSERT SELECT * (column-preserving
--            copy); DROP old; RENAME _new → old; recreate indexes;
--            foreign_key_check; schema_version bump; COMMIT;
--            foreign_keys=ON.
-- Risk:      Low. Pure additive enum extension. Column shape unchanged
--            from 0018 (16 columns: id, identifier, identifier_type,
--            device_category, manufacturer, model, confidence, source_url,
--            source_type, source_excerpt, geographic_scope, first_seen,
--            last_verified, notes, superseded_by, paired_identifier_id,
--            pair_kind). Active 22,464 / total — preserved via
--            column-list-preserving INSERT SELECT.
-- ============================================================================
--
-- Migration-slot allocation chain of record:
--   0001-0017  see 0018 header for the full chain
--   0018 = identifier_types extension batch — CP20 SAR-13 §S.3 routing
--          (14 net-new values; 41-value cumulative CHECK)
--   0019 = identifier_types round-2 — MAC-117 §1 routing slate
--          (this migration; 7 net-new values; 48-value cumulative CHECK)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative CHECK enum (41 prior + 7 net-new = 48 values total)
-- ─────────────────────────────────────────────────────────────────────────────
-- The 41 prior values are paste-verified verbatim against the live `identifiers`
-- table CHECK clause from migrations 0001 (9) + 0009 (3) + 0011 (1) + 0013
-- (13) + 0014 (1) + 0018 (14). Per
-- `feedback_cumulative_check_enum_across_sequenced_migrations.md`, the
-- rebuild-pattern migration MUST carry forward ALL prior CHECK enum values,
-- not just its own delta.
--
-- The 7 net-new types (MAC-117 §1 (A) slate, rationale from routing_slate
-- doc rev 1; CEO ratification 2026-05-14):
--   1. `asdstan_message_type`        — ASTM Remote ID protocol broadcast
--                                       message-type enum class. Devices emit
--                                       over RF; detectors look for. (src=27
--                                       cyber-defence-campus/RemoteIDReceiver,
--                                       7 rows.)
--   2. `asdstan_enum_value`          — ASTM Remote ID field-encoded enum
--                                       values (ua_category / id_type /
--                                       height_type / location_source).
--                                       Broadcast in messages as discrete
--                                       codes; class-precedent matches
--                                       `device_class_id` and
--                                       `wifi_aware_service_name`. Single
--                                       umbrella type; specific enum
--                                       instance in `identifier`. (src=27,
--                                       14 rows.)
--   3. `dji_protocol_struct_format`  — DJI Drone-ID broadcast struct format
--                                       string (v1, v2). Device-emitted
--                                       protocol-struct fidelity; precedent:
--                                       `qualcomm_chip_format_id` (mig 0018).
--                                       (src=27, 2 rows.)
--   4. `gpt_partition_uuid`          — Device-side storage layout identifier
--                                       (Qualcomm GPT partition UUIDs on
--                                       Picard/Bravo Compute Box).
--                                       Structural-fidelity device class;
--                                       precedent: `firmware_image_variant`
--                                       (mig 0018). (src=41, 3 rows.)
--   5. `chipset_codename`            — Firmware-anchored device model class
--                                       (Qualcomm SoC codenames: APQ8009,
--                                       etc.). Device-side hardware
--                                       identifier; precedent:
--                                       `qualcomm_chip_format_id` (mig 0018).
--                                       (src=42, 39 rows.)
--   6. `firmware_build_string`       — Qualcomm BOOT/SBL build version string
--                                       (e.g., `BOOT.BF.3.3-00163`).
--                                       Device-side firmware identity;
--                                       sibling-distinct from
--                                       `firmware_branded_string` (mig 0018)
--                                       — branded marketing vs build branch
--                                       semantics. CEO confirmed keep
--                                       distinct on slate ratification.
--                                       (src=42, 2 rows.)
--   7. `firmware_build_uuid`         — Firmware build GUID (binary-unique
--                                       identifier per build). Device-side
--                                       firmware-anchored identifier;
--                                       precedent: `firmware_sha256_hash`
--                                       (mig 0018). (src=42, 1 row.)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- behavioral_signatures routing principle — round-2 (MAC-117 §1 (B) slate)
-- (NO SCHEMA CHANGE for this footnote — documented here for handoff to the
-- post-migration routing-execution step within MAC-117)
-- ─────────────────────────────────────────────────────────────────────────────
-- The 5 detector-internal candidate labels route to
-- `behavioral_signatures.signature_name` (free TEXT; no enum constraint;
-- added by migration 0010_behavioral_signatures.sql). Schema accepts the
-- 38-row backfill semantics without further migration:
--
-- | candidate_type        | rows | rationale (MAC-117 §1 (B))
-- |--- |--- |---
-- | android_package_name  | 15 | device-side string but operator-side queried via Android APIs (not RF-broadcast); `oem_service_mode_command` precedent at MAC-110
-- | rest_endpoint         | 13 | operator-side admin surface (REST API paths); detector-internal heuristic
-- | cloud_endpoint_fqdn   |  4 | operator-side scanner backend FQDNs; not device-emitted
-- | boot_log_signature    |  4 | forensic post-hoc pattern (ESP32 ROM boot strings); detection-heuristic class
-- | lan_endpoint_url      |  2 | hardcoded scanner-side URL; not device-emitted
--
-- Routing execution (post-migration step within MAC-117) executes the 38-row
-- backfill as `behavioral_signatures` INSERTs with confidence=65,
-- device_category per candidate context (alpr for Flock-anchored src=41),
-- `promoted_to_behavioral_signatures_id` set in raw_observations.notes +
-- `promoted_identifier_id` stays NULL — matching MAC-110 5f1bf2e precedent.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- (C) HOLD residue — MAC-117 §1 (C) slate (1 row)
-- ─────────────────────────────────────────────────────────────────────────────
-- 1 row (src=40 FoggedLens/deflock-app, candidate_type=attribution_conflict)
-- already filed in conflicts.id=5 (Motorola/Vigilant single-profile merge).
-- Out_of_scope_v1 per bible §4.4; no identifier_type extension needed.
-- Post-migration routing-execution step updates raw_observations.notes with
-- `round_2_disposition_class='out_of_scope_v1'` for forensic traceability.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 hard-rule discipline (cite verbatim per 0009 / 0011 / 0013 / 0014 / 0018)
-- ─────────────────────────────────────────────────────────────────────────────
--   §11 #1   no fabrication — every new CHECK enum value cites canon:
--              MAC-117 §1 routing slate (routing_slate doc rev 1); each (A)
--              type's rationale anchored to a mig-0018 precedent type.
--   §11 #7   no main-table promotion without provenance — schema-only here;
--              promotion of the 68 (A) rows happens in MAC-117 routing-
--              execution step.
--   §11 #8   no confidence drift — confidence column unchanged.
--   §11 #11  amendment-log discipline — this migration is the schema-sibling
--              of MAC-117 §1 routing-slate ratification.
--   §11 #15  no decompiled vendor source in git index — N/A; schema-only.
--   §11 #16  facts-only promotion from public-but-unlicensed sources —
--              binds row-level provenance at routing-execution time, not at
--              schema-extension time.
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column list reflects post-0018 state (16 columns; paired_identifier_id +
-- pair_kind from 0012 preserved verbatim). CHECK enum carries forward all 41
-- prior values + adds 7 net-new (48 cumulative values).
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
                          -- MAC-117 (migration 0019 — this migration) — round-2
                          -- vocab extension (7 net-new) per §1 routing slate (A)
                          'asdstan_message_type',
                          'asdstan_enum_value',
                          'dji_protocol_struct_format',
                          'gpt_partition_uuid',
                          'chipset_codename',
                          'firmware_build_string',
                          'firmware_build_uuid'
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

-- ─── Recreate indexes (carry forward from 0018) ─────────────────────────────
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
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (19, '0019_identifier_types_round2');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - MAC-117 §1 routing slate (routing_slate doc rev 1
--   `877c76b9-ec96-46f9-9a33-717095d260bd`)
-- - MAC-117 confirmation interaction `218b091a-b9e5-4d4f-a39b-5923c5f6892f`
--   (CEO-ratified 2026-05-14, no amendments)
-- - MAC-110 §E.4 (round-2 cohort surfacing)
-- - MAC-101 Stream 1 §2.4 (this dispatch's parent)
-- - db/migrations/0018_identifier_types_extension_batch.sql (immediate-prior
--   identifier_type enum extension; cumulative CHECK carry-forward source)
-- - db/migrations/0010_behavioral_signatures.sql (free-TEXT signature_name
--   surface for §S.3 detector-internal routing — used by (B) backfill)
-- - feedback_cumulative_check_enum_across_sequenced_migrations.md
-- - feedback_enum_amendment_needs_schema_migration_sibling.md
