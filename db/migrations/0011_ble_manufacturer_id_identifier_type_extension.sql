-- ============================================================================
-- DRAFT MIGRATION — NOT APPLIED — QUEUED FOR CEO RATIFICATION
-- ============================================================================
-- Filename intentionally ends in `.sql.draft`. CEO promotes to
-- `0011_ble_manufacturer_id_identifier_type_extension.sql` at Phase 3
-- application time.
--
-- Migration: 0011_ble_manufacturer_id_identifier_type_extension
-- Purpose:   Extend `identifiers.identifier_type` CHECK enum with
--            `ble_manufacturer_id` — the SIG-assigned 16-bit BLE company
--            identifier (structurally distinct from 128-bit `ble_uuid`).
-- Surfaced:  Wave-A Phase 1a (MaxwellDPS/Flock-You-Android — 22 instances)
--            + Phase 2 (colonelpanichacks trio — additional staging incl.
--            XUNTONG 0x09C8) + Phase 3b (seemoo-lab/AirGuard tracker
--            ecosystem) + Phase 6γ (AIMSICD IMSI-detector cluster).
--            Cumulative Wave-A staging ~30+ ble_manufacturer_id observations.
-- Authority: CEO Wave-A Ratification Run dispatch 2026-05-11 §1 + Phase-2
--            self-review ratification by board comment bbb71be5 2026-05-11.
-- Bible:     §11 #11 — schema changes are CEO-only ratification. This draft
--            is a proposal, not an application.
-- Pattern:   SQLite table-rebuild per 0009 precedent. Mirrors mechanics
--            verbatim (PRAGMA foreign_keys = OFF / BEGIN / CREATE
--            identifiers_new / INSERT SELECT / DROP / RENAME / reindex /
--            PRAGMA foreign_key_check / INSERT schema_version / COMMIT /
--            PRAGMA foreign_keys = ON).
-- Risk:      Low. Pure additive enum extension. No existing-row impact.
--            154 identifiers rows preserved via column-list-preserving
--            INSERT SELECT. The `superseded_by` self-FK survives
--            via foreign_keys=OFF during DROP+RENAME (modern SQLite ≥3.25
--            default legacy_alter_table=OFF updates FK references through
--            rename per 0009 precedent).
-- ============================================================================
--
-- Migration-slot allocation chain of record (CP14 batch update):
--   0001-0009 = existing migrations (see 0009 header for the full chain)
--   0010 = behavioral_signatures NEW TABLE (CP14)
--   0011 = ble_manufacturer_id identifier_type extension (CP14 — this migration)
--   0012 = paired_identifier_id column on identifiers (CP14)
--   0013 = drone-RID + proprietary-protocol identifier_types extension (CP14
--          — 13-type fold-in)
--   0014 = surveillance-metadata identifier_types extension (CP14 — alpr_model
--          only; operator_profile HELD as G-17)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Rationale (per CEO at Wave-A handoff, board-ratified Phase 2 bbb71be5)
-- ─────────────────────────────────────────────────────────────────────────────
-- "2-byte SIG company ID vs 128-bit UUID — structural difference." A
-- SIG-assigned 16-bit BLE company identifier is a distinct namespace from
-- a 128-bit BLE service UUID; collapsing them as a sub-flavor would lose
-- query-precision and complicate future BLE-spec extensions.
--
-- §8.2 source-banding for ble_manufacturer_id rows:
--   * Apple `0x004C` (6+ Wave-A sources) → corroborated across multiple
--     `crowdsourced` sources; lifts via §8.2 corroboration formula
--   * XUNTONG `0x09C8` (5+ Wave-A sources) → same shape
--   * Phase-4 promotion-cycle-1 sweeps these per dispatch §4.1 expected targets
--
-- §11 hard-rule discipline:
--   §11 #1  no fabrication — every promoted ble_manufacturer_id row has
--             source_url + source_excerpt + raw_observations ancestor
--   §11 #7  no main-table promotion without provenance — schema-only here;
--             promotion happens in Phase 4
--   §11 #8  no confidence drift — confidence column unchanged; same
--             §7.3 intake-side discipline
--   §11 #11 amendment-log discipline — coordinated commit pairs this
--             migration with BIBLE_AMENDMENTS.md CP14 entry
--
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column list verbatim from 0009 post-rebuild state. CHECK enum extended
-- with one new value: 'ble_manufacturer_id'.
CREATE TABLE identifiers_new (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL CHECK (identifier_type IN (
                          'oui', 'mac', 'mac_range', 'bssid',
                          'ssid_exact', 'ssid_pattern',
                          'ble_uuid', 'ble_service',
                          'device_fingerprint',
                          -- CP13 (migration 0009) — Wave G structural fidelity
                          'ble_local_name', 'ble_characteristic',
                          'product_family_codename',
                          -- CP14 (migration 0011 — this migration) — G-3
                          'ble_manufacturer_id'
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
                          -- CP13 (migration 0009) — CP12 §8.2 schema sibling
                          'manufacturer_app'
                      )),
    source_excerpt    TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    geographic_scope  TEXT,
    first_seen        DATETIME,
    last_verified     DATETIME,
    notes             TEXT,
    superseded_by     INTEGER REFERENCES identifiers(id) ON DELETE SET NULL
);

-- Column-preserving copy (all 14 columns enumerated; the new value is
-- only in the CHECK constraint, not a new column).
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate indexes (verbatim from 0009 post-rebuild) ─────────────────────
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

-- ─── FK integrity assertion ──────────────────────────────────────────────────
-- foreign_key_check returns zero rows for a clean rebuild. The wrapper at
-- db/validation/migration_0011_verify.py is the canonical idempotency
-- boundary (short-circuit on `MAX(version) FROM schema_version >= 11`;
-- mirrors the migration_0009_verify.py precedent).
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (11, '0011_ble_manufacturer_id_identifier_type_extension');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - raw/wave_a/_phase1_aggregation_2026-05-11.md §4.4 (G-3 surfacing)
-- - raw/wave_a/_ceo_gates_queue_2026-05-11.md G-3
-- - raw/wave_a/_phase2_self_review_2026-05-11.md §2.5 (board ratification anchor)
-- - db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql
--   (table-rebuild precedent — copied verbatim mechanics)
-- - db/migrations/_drafts/0012_paired_identifier_id.sql.draft (cumulative-enum
--   sibling — 0012 carries ble_manufacturer_id forward in its CHECK)
