-- ============================================================================
-- DRAFT MIGRATION — NOT APPLIED — QUEUED FOR CEO RATIFICATION
-- ============================================================================
-- Filename intentionally ends in `.sql.draft`. CEO promotes to
-- `0015_primary_registry_source_type_extension.sql` at Phase-4 application
-- time per dispatch `c0e91b23` 2026-05-11.
--
-- Migration: 0015_primary_registry_source_type_extension
-- Purpose:   Add `primary_registry` to BOTH `identifiers.source_type` and
--            `sources.source_type` CHECK enums. Schema-sibling of CP15
--            §8.2 amendment (commit `1e83517`).
-- Surfaced:  MAC-63 Wave-A Phase 5 (CP15 draft) + reopened-via-comment
--            CP15 ratification dispatch [`c0e91b23`](/MAC/issues/MAC-63#comment-c0e91b23-ba74-4ebe-8d3e-e6fe94c67f0e)
--            2026-05-11.
-- Authority: CEO CP15 ratification run dispatch §2 Phase 3 + Phase-2
--            ratification at [`62a31d2c`](/MAC/issues/MAC-63#comment-62a31d2c-fd21-4935-8057-dac77b5402b9).
-- Bible:     §11 #11 — schema changes are CEO-only ratification.
-- Pattern:   SQLite table-rebuild per 0009 precedent. Two-table rebuild
--            within a single migration transaction (identifiers + sources;
--            both share the same 9-value pre-CP15 source_type enum per
--            Phase-3 enum-trace finding — outcome (a) PARITY).
-- Risk:      Medium-low. Two table rebuilds touch every existing row
--            (column-preserving INSERT SELECT). CHECK constraint extends
--            by 1 value on each table; column shape unchanged.
-- ============================================================================
--
-- Migration-slot allocation chain of record:
--   0001-0009 = existing migrations (see 0009 header for the full chain)
--   0010 = behavioral_signatures NEW TABLE (CP14)
--   0011 = ble_manufacturer_id identifier_type extension (CP14)
--   0012 = paired_identifier_id + pair_kind columns (CP14)
--   0013 = drone-RID + proprietary-protocol identifier_types (CP14)
--   0014 = surveillance-metadata identifier_types (CP14)
--   0015 = primary_registry source_type extension (CP15 — this migration)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Phase-3 enum-trace finding (outcome determination per board dispatch
-- `62a31d2c` 2026-05-11)
-- ─────────────────────────────────────────────────────────────────────────────
-- Per board direction, traced both tables' `source_type` CHECK enum history
-- separately (they may not have moved in lockstep through CP1-CP14):
--
--   identifiers.source_type (live post-CP14):
--     ['official', 'regulatory', 'procurement', 'academic', 'foia',
--      'crowdsourced', 'inferred', 'manufacturer_doc', 'manufacturer_app']
--     = 9 values
--
--   sources.source_type (live post-CP14):
--     ['official', 'regulatory', 'procurement', 'academic', 'foia',
--      'crowdsourced', 'inferred', 'manufacturer_doc', 'manufacturer_app']
--     = 9 values
--
-- OUTCOME (a) PARITY. Both tables have the identical 9-value enum.
-- CP15 cumulative for each = those 9 + primary_registry = 10 values.
-- No silent drift-fix needed; no G-18 reconciliation gate surfaced.
--
-- Migration-history trace (from db/migrations/*.sql):
--   - 0001_initial.sql: identifiers.source_type + sources.source_type
--     both at 8 values (added 'manufacturer_doc' to the base 7)
--   - 0009_manufacturer_app_and_identifier_type_extensions.sql: CP13
--     coordinated commit added 'manufacturer_app' to BOTH tables in
--     lockstep
--   - 0010-0014 (CP14 batch): identifiers source_type unchanged (these
--     migrations extended identifier_type, paired_identifier_id, etc.,
--     not source_type); sources table not rebuilt
--   - Net: both tables stayed in source_type parity since 0009/CP13
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative-CHECK-enum discipline (per feedback_migration_sequence_
-- cumulative_enum_carryforward.md, codified after CP14 Phase-3 DDL fold-in
-- caught a missing-enum-value bug)
-- ─────────────────────────────────────────────────────────────────────────────
-- Each table's source_type CHECK enum in this migration MUST include EVERY
-- prior CP's contribution + primary_registry. Cumulative state for both:
--
--   1. 'official'         — 0001 initial
--   2. 'regulatory'       — 0001 initial
--   3. 'procurement'      — 0001 initial
--   4. 'academic'         — 0001 initial
--   5. 'foia'             — 0001 initial
--   6. 'crowdsourced'     — 0001 initial
--   7. 'inferred'         — 0001 initial
--   8. 'manufacturer_doc' — 0001 initial
--   9. 'manufacturer_app' — CP13 (migration 0009)
--  10. 'primary_registry' — CP15 (this migration)
--
-- The identifiers table's identifier_type enum is 27 values post-CP14 and
-- the paired_identifier_id + pair_kind columns landed at 0012. Both are
-- carried forward verbatim in this migration's identifiers_new schema.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Bible §11 hard-rule discipline
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 #1  no fabrication — primary_registry is a legitimate §8.2 source-band
--   per CP15 amendment commit `1e83517`. Future row writes citing this band
--   must point source_url directly at the issuer's own publication (FAA's
--   database URL, SIG's company-identifier registry URL, IEEE's MA-L
--   assignment record URL, etc.) per CP15 §11 #8 reclassification discipline.
-- §11 #7  no main-table promotion without provenance — schema-only; zero
--   row writes. Promotion-cycle-2 (Phase 5/6 of this run) does the row
--   writes under the §11 #7 gate.
-- §11 #8  no confidence drift — no confidence-column writes. Reclassification
--   discipline per CP15 §8.2 sub-rule: only rows with direct registry
--   source_url qualify for primary_registry band; ancestry-chain
--   reclassification is closed-loop.
-- §11 #11 amendment-log discipline — this migration is the schema-sibling
--   to CP15 §8.2 amendment (commit `1e83517`); BIBLE_AMENDMENTS.md CP15
--   entry already pre-references this migration as the next deliverable.
--
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Cumulative state at this migration: identifier_type enum 27 values (post-
-- CP14 0014); source_type enum extended to 10 values (CP15); column shape
-- preserved (16 columns including paired_identifier_id + pair_kind from
-- 0012); all CHECK constraints carried forward.
CREATE TABLE identifiers_new (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL CHECK (identifier_type IN (
                          -- Pre-CP13 (0001 initial)
                          'oui', 'mac', 'mac_range', 'bssid',
                          'ssid_exact', 'ssid_pattern',
                          'ble_uuid', 'ble_service',
                          'device_fingerprint',
                          -- CP13 (migration 0009)
                          'ble_local_name', 'ble_characteristic',
                          'product_family_codename',
                          -- CP14 (migration 0011)
                          'ble_manufacturer_id',
                          -- CP14 (migration 0013) — Drone-RID + proprietary
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
                          -- CP14 (migration 0014)
                          'alpr_model'
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
                          -- Pre-CP13 (0001 initial; 8 values)
                          'official', 'regulatory', 'procurement',
                          'academic', 'foia', 'crowdsourced',
                          'inferred', 'manufacturer_doc',
                          -- CP13 (migration 0009)
                          'manufacturer_app',
                          -- CP15 (this migration)
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

INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- Recreate all 6 indexes (carry forward from CP14 0012/0014 state).
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

-- ─── sources table rebuild ──────────────────────────────────────────────────
-- Cumulative state: source_type extended to 10 values (CP15);
-- column shape unchanged from 0009 post-rebuild state.
CREATE TABLE sources_new (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL UNIQUE,
    source_type     TEXT NOT NULL CHECK (source_type IN (
                        -- Pre-CP13 (0001 initial; 8 values)
                        'official', 'regulatory', 'procurement',
                        'academic', 'foia', 'crowdsourced',
                        'inferred', 'manufacturer_doc',
                        -- CP13 (migration 0009)
                        'manufacturer_app',
                        -- CP15 (this migration)
                        'primary_registry'
                    )),
    tier            INTEGER CHECK (tier IN (1, 2, 3, 4)),
    last_fetched_at DATETIME,
    last_status     TEXT,
    notes           TEXT
);

INSERT INTO sources_new SELECT * FROM sources;

DROP TABLE sources;

ALTER TABLE sources_new RENAME TO sources;

CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);

-- ─── FK integrity assertion (after BOTH rebuilds) ───────────────────────────
-- Both tables have FK relationships:
--   - identifiers.superseded_by → identifiers(id)
--   - identifiers.paired_identifier_id → identifiers(id)
--   - raw_observations.source_id → sources(id)
--   - raw_observations.promoted_identifier_id → identifiers(id)
--   - behavioral_signatures.source_id → sources(id)
--   - extraction_runs.source_id → sources(id)
--   - conflicts.identifier_a_id / identifier_b_id → identifiers(id)
--   - conflicts.raw_observation_id → raw_observations(id)
-- All must survive the table rebuilds. Modern SQLite (≥3.25; default
-- legacy_alter_table=OFF) updates FK references through RENAME during the
-- foreign_keys=OFF window, per 0009 + 0012 precedent.
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (15, '0015_primary_registry_source_type_extension');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - BIBLE_AMENDMENTS.md CP15 entry (commit `1e83517` — schema-sibling
--   reference)
-- - raw/wave_a/_bible_amendment_cp15_primary_registry_draft_2026-05-11.md
--   (CP15 amendment-draft archive — moved to bible/history/cp15/)
-- - feedback_migration_sequence_cumulative_enum_carryforward.md (cumulative
--   CHECK-enum discipline — binding for this migration's authoring)
-- - db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql
--   (last migration to rebuild both tables in coordinated lockstep — CP13
--   precedent for the two-table-rebuild pattern in this migration)
-- - db/migrations/0014_surveillance_metadata_identifier_types_extension.sql
--   (most-recent identifiers rebuild; carries paired_identifier_id +
--   pair_kind columns + the 27-value identifier_type enum that 0015's
--   identifiers_new must preserve verbatim)
