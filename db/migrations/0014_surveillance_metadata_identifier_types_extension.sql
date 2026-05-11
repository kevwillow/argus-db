-- ============================================================================
-- DRAFT MIGRATION — NOT APPLIED — QUEUED FOR CEO RATIFICATION
-- ============================================================================
-- Filename intentionally ends in `.sql.draft`. CEO promotes to
-- `0014_surveillance_metadata_identifier_types_extension.sql` at Phase 3
-- application time.
--
-- Migration: 0014_surveillance_metadata_identifier_types_extension
-- Purpose:   Extend `identifiers.identifier_type` CHECK enum with one new
--            type: `alpr_model` (manufacturer-grained ALPR/camera product
--            profile). Scope-trimmed per board ratification bbb71be5
--            2026-05-11:
--              - `alpr_model` LANDS this migration
--              - `product_family_codename` already in enum since CP13 (0009)
--              - `operator_profile` HELD as new gate G-17 (operators-table
--                vs identifier-type architectural call deferred to
--                validator-side review)
-- Surfaced:  Wave-A Phase 3c (FoggedLens/deflock-app — 11 alpr_model
--            instances + 3 operator_profile + 1 product_family_codename)
--            +Phase 2a Pigvision carry-over.
-- Authority: CEO Wave-A Ratification Run dispatch 2026-05-11 §3.1.5 + board
--            comment bbb71be5 (operator_profile HOLD as G-17 confirmed).
-- Bible:     §11 #11 — schema changes are CEO-only ratification. This draft
--            is a proposal, not an application.
-- Pattern:   SQLite table-rebuild per 0009 precedent.
-- Risk:      Low. Pure additive enum extension (one new value).
-- ============================================================================
--
-- Migration-slot allocation chain of record (CP14 batch — final entry):
--   0010 = behavioral_signatures NEW TABLE (CP14)
--   0011 = ble_manufacturer_id identifier_type extension (CP14)
--   0012 = paired_identifier_id column on identifiers (CP14)
--   0013 = drone-RID + proprietary-protocol identifier_types extension
--          (CP14 — 13-type fold-in)
--   0014 = surveillance-metadata identifier_types extension (CP14 — this
--          migration; alpr_model only)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- alpr_model rationale (per gates queue G-10 + Wave-A 3c surfacing)
-- ─────────────────────────────────────────────────────────────────────────────
-- Manufacturer-grained ALPR/camera product profile. Example values:
--   "Flock Safety Falcon", "Motorola Vigilant", "Genetec AutoVu",
--   "Axis Q6010-E", "Leonardo ELSAG ELSAG MR-2".
-- Differs from `oui`/`mac`/`fcc_id` in that the value is product-name-shaped
-- rather than identifier-bytes-shaped, but it anchors to a specific
-- deployable surveillance product the way an FCC ID does. Companion type
-- to the existing `product_family_codename` (added by CP13/0009).
--
-- Phase-4 promotion-cycle-1 targets for alpr_model rows:
--   - 11 instances staged from FoggedLens/deflock-app (3c)
--   - Subject to standard §8.2 source-banding (deflock-app =
--     `crowdsourced` 50–75)
--   - Eligible for §8.2 corroboration formula with manufacturer_doc /
--     regulatory cross-references where they exist
--
-- ─────────────────────────────────────────────────────────────────────────────
-- operator_profile HOLD (G-17) — structural rationale
-- ─────────────────────────────────────────────────────────────────────────────
-- Per dispatch §3.1.5 + board comment bbb71be5:
--   "operator_profile HOLD as G-17 confirmed."
-- Reason: operator_profile is structurally an *entity* (a corporation that
-- DEPLOYS surveillance hardware — e.g., Lowe's Q1373493, Home Depot
-- Q864407, Simon Property Group Q2287759), not a *product*. The right
-- shape may be a new `operators` table parallel to `manufacturers` +
-- `procurement_records`, NOT a sub-flavor of identifier_type.
--
-- Gates queue G-17 entry appended in this same CP14 batch (see
-- `raw/wave_a/_ceo_gates_queue_2026-05-11.md` G-17). Decision deferred
-- to validator-side review post-Wave-A close.
--
-- Phase-A Wave-A 3c staging for the 3 operator_profile instances:
--   - Continue staging under raw_observations `candidate_type='operator_profile'`
--   - DO NOT promote to identifiers until G-17 resolves
--   - Wave-D (court+FOIA records) and Wave-E (news+forums) will surface
--     more operator_profile candidates; G-17 resolution probably gates
--     on Wave-D/E aggregate volume + entity-vs-product disposition call
--
-- §11 hard-rule discipline (cite verbatim per 0009 precedent header):
--   §11 #1  no fabrication — every promoted row has source_url +
--             source_excerpt + raw_observations ancestor
--   §11 #7  schema-only here; promotion happens in Phase 4
--   §11 #8  no confidence drift
--   §11 #11 amendment-log discipline — coordinated commit pairs with
--             BIBLE_AMENDMENTS.md CP14 entry
--
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Cumulative CHECK enum: post-0013 26 values + `alpr_model` = 27 values.
-- Column shape preserved (16 columns post-0012 including paired_identifier_id
-- + pair_kind).
CREATE TABLE identifiers_new (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL CHECK (identifier_type IN (
                          -- Pre-CP13 (0001 initial)
                          'oui', 'mac', 'mac_range', 'bssid',
                          'ssid_exact', 'ssid_pattern',
                          'ble_uuid', 'ble_service',
                          'device_fingerprint',
                          -- CP13 (migration 0009) — Wave G structural fidelity
                          'ble_local_name', 'ble_characteristic',
                          'product_family_codename',
                          -- CP14 (migration 0011) — G-3 BLE SIG manufacturer IDs
                          'ble_manufacturer_id',
                          -- CP14 (migration 0013) — Drone-RID + proprietary
                          -- protocol cluster (13 values from 0013 fold-in)
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
                          -- CP14 (migration 0014 — this migration) — G-10
                          -- surveillance metadata (alpr_model only;
                          -- operator_profile HELD as G-17)
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
                          'official', 'regulatory', 'procurement',
                          'academic', 'foia', 'crowdsourced',
                          'inferred', 'manufacturer_doc',
                          'manufacturer_app'
                      )),
    source_excerpt    TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    geographic_scope  TEXT,
    first_seen        DATETIME,
    last_verified     DATETIME,
    notes             TEXT,
    superseded_by     INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
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

-- Column-preserving copy (16 columns).
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate indexes (carry forward from 0013) ─────────────────────────────
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
    (14, '0014_surveillance_metadata_identifier_types_extension');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - raw/wave_a/_phase3_aggregation_2026-05-11.md (3c FoggedLens/deflock-app
--   surfacing; 11 alpr_model staging detail)
-- - raw/wave_a/_phase2_aggregation_2026-05-11.md (Pigvision codename
--   carry-over)
-- - raw/wave_a/_ceo_gates_queue_2026-05-11.md G-10 + G-17 (G-17 appended
--   in CP14 batch for operator_profile HOLD)
-- - raw/wave_a/_phase2_self_review_2026-05-11.md (board ratification anchor)
-- - db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql
--   (table-rebuild precedent)
-- - db/migrations/_drafts/0013_drone_rid_and_proprietary_protocol_identifier_types_extension.sql.draft
--   (immediate predecessor; cumulative-enum carry-forward)
