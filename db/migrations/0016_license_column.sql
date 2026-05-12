-- ============================================================================
-- DRAFT MIGRATION — NOT APPLIED — QUEUED FOR BOARD RATIFICATION
-- ============================================================================
-- Filename intentionally ends in `.sql.draft`. CEO promotes to
-- `0016_license_column.sql` post-board-ratification per HB75 §4 chunk 1 Q3
-- disposition [`3f478a6d`](/MAC/issues/MAC-1#comment-3f478a6d-ad80-4a23-9019-fb5b851a9c49)
-- 2026-05-12.
--
-- Migration: 0016_license_column
-- Purpose:   Add `LICENSE` column to `deployment_observations` carrying the
--            upstream-license enum for each row. Schema-sibling of §4
--            chunk 1 four-file composition (LICENSE / LICENSE-DATA /
--            LICENSE-DOCS / CREDITS.md) — encodes Atlas-derived row
--            quarantine flag for ODbL-derivative downstream consumers.
-- Surfaced:  MAC-1 HB76 ratification micro-chunk 2026-05-12.
-- Authority: Board ratification at HB75 [`3f478a6d`](/MAC/issues/MAC-1#comment-3f478a6d-ad80-4a23-9019-fb5b851a9c49)
--            §4 chunk 1 Q3: "(a) LICENSE column on `deployment_observations`;
--            slot **0016**". HB76 board affirmation at [`81f0cce7`](/MAC/issues/MAC-1#comment-81f0cce7-1ddc-4275-a8ec-8d7253876c9a).
-- Bible:     §11 #11 — schema changes are CEO-only ratification post-board.
-- Pattern:   SQLite table-rebuild per 0009 / 0015 precedent. Single-table
--            rebuild within a single migration transaction; CHECK
--            constraint adds a NEW column shape (NOT NULL with closed-enum
--            allowed-values list).
-- Risk:      Medium-low. Single table rebuild touches every existing row
--            (column-preserving INSERT SELECT with deterministic LICENSE
--            backfill via CASE on source_id). Backfill is closed-form:
--            source_id=5 (Atlas) → 'CC-BY-NC-SA-4.0'; source_id=6 (DeFlock)
--            → 'ODbL-1.0'; zero other source_id values currently populate
--            the table (verified 2026-05-12 against db/argus.db: 116,668
--            rows total = 15,071 Atlas + 101,597 DeFlock).
-- ============================================================================
--
-- Migration-slot allocation chain of record:
--   0001-0009 = existing migrations (see 0009 header for the full chain)
--   0010 = behavioral_signatures NEW TABLE (CP14)
--   0011 = ble_manufacturer_id identifier_type extension (CP14)
--   0012 = paired_identifier_id + pair_kind columns (CP14)
--   0013 = drone-RID + proprietary-protocol identifier_types (CP14)
--   0014 = surveillance-metadata identifier_types (CP14)
--   0015 = primary_registry source_type extension (CP15)
--   0016 = deployment_observations LICENSE column (HB75 §4 chunk 1 — this migration)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- LICENSE enum allowed-values rationale
-- ─────────────────────────────────────────────────────────────────────────────
-- Closed-enum at this migration covers the two upstream-license-bearing
-- sources currently writing to deployment_observations (Atlas + DeFlock).
-- Three additional values pre-staged for likely future ingestion:
--
--   1. 'ODbL-1.0'           — DeFlock (source_id=6); compatible with our
--                             dataset's ODbL-1.0 license. 101,597 rows.
--   2. 'CC-BY-NC-SA-4.0'    — EFF Atlas of Surveillance (source_id=5);
--                             NC clause carries forward to derivatives.
--                             15,071 rows. **QUARANTINE FLAG** for
--                             ODbL-derivative downstream consumers.
--   3. 'public-domain'      — pre-staged for US federal regulatory /
--                             procurement data (FCC EAS source_id=7,
--                             USAspending source_id=8) if those sources
--                             ever write deployment_observations rows
--                             (current population: 0). Zero rows at apply
--                             time.
--   4. 'foia'               — pre-staged for FOIA / state public-records
--                             rows (Granicus Legistar source_id=10) if
--                             those ever write deployment_observations
--                             rows. Zero rows at apply time.
--   5. 'unspecified'        — escape hatch for sources without a clear
--                             upstream license (e.g. crowdsourced OSINT
--                             repositories without per-repo license
--                             declaration). Zero rows at apply time.
--
-- New deployment_observations writers MUST set LICENSE explicitly to one
-- of these five values; default discipline lives in the source-loader code
-- per the source's known upstream license, not in this column's DEFAULT.
-- No DEFAULT clause (forces explicit setting at INSERT time).
--
-- Future additions to this enum require a new migration (NN_license_enum_
-- extension.sql) following the cumulative-enum carryforward discipline
-- (feedback_migration_sequence_cumulative_enum_carryforward.md).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative-CHECK-enum discipline (per feedback_migration_sequence_
-- cumulative_enum_carryforward.md)
-- ─────────────────────────────────────────────────────────────────────────────
-- This migration introduces the LICENSE column. No prior CP contributed
-- values to it. Cumulative state at this migration = the 5 values listed
-- above. Future CPs that extend the enum MUST carry forward all 5 verbatim.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Bible §11 hard-rule discipline
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 #1  no fabrication — backfill is closed-form deterministic on
--   source_id; Atlas (source_id=5) → CC-BY-NC-SA-4.0 per upstream EFF
--   Atlas license; DeFlock (source_id=6) → ODbL-1.0 per upstream OSM-
--   mirrored license. Both verified against upstream source pages.
-- §11 #7  no main-table promotion without provenance — N/A; schema-only
--   for deployment_observations, no identifiers row writes.
-- §11 #8  no confidence drift — N/A; no confidence-column changes.
-- §11 #11 amendment-log discipline — no bible §-amendment sibling
--   required for this migration. LICENSE column is an attribution-fidelity
--   field, not a §-text amendment. BIBLE_AMENDMENTS.md does not need a new
--   CP entry. CREDITS.md (HB75 §4 chunk 1 deliverable) references this
--   migration filename verbatim for the Atlas quarantine cross-reference.
-- §11 #15 schema-sibling-on-§-amendment discipline — counterpart: NEW §-
--   amendment introducing CHECK-backed enum requires sibling migration.
--   This migration does NOT introduce a §-amendment; it's a forward-
--   compatibility shim for downstream-derivative obligations. CP-counter
--   unchanged; live CPs 1-15 unchanged by this migration.
--
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── deployment_observations table rebuild ──────────────────────────────────
-- Cumulative state at this migration: 21 columns post-0002; column shape
-- preserved verbatim + 1 NEW column (LICENSE) appended. No CHECK constraints
-- on existing columns (only the source_excerpt length CHECK from 0002).
-- LICENSE column placed LAST in column order so existing SELECT * consumers
-- that don't yet know about LICENSE see deterministic column ordering.
CREATE TABLE deployment_observations_new (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id             INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    extraction_run_id     INTEGER REFERENCES extraction_runs(id) ON DELETE SET NULL,
    source_url            TEXT NOT NULL,
    source_row_key        TEXT NOT NULL,         -- e.g. Atlas AOSNUMBER, DeFlock per-row id
    agency_name           TEXT,
    agency_type           TEXT,                  -- e.g. Atlas "Type of LEA" (Police, Sheriff)
    juris_type            TEXT,                  -- e.g. Atlas "Type of Juris" (Municipal)
    city                  TEXT,
    county                TEXT,
    state                 TEXT,                  -- US state code or country subdivision
    country               TEXT,                  -- ISO country code; NULL falls to source default
    lat                   REAL,                  -- DeFlock-shaped; Atlas leaves NULL (no geo)
    lon                   REAL,                  -- DeFlock-shaped; Atlas leaves NULL
    technology_category   TEXT,                  -- Atlas "Technology" / DeFlock equivalent — raw
    vendor_raw            TEXT,                  -- Atlas "Vendor" / DeFlock equivalent — raw
    citation_url          TEXT,                  -- Atlas "Link 1" / DeFlock per-row citation
    source_excerpt        TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    captured_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at          DATETIME,
    notes                 TEXT,                   -- JSON: extra source columns (PII-redacted summary, link 2/3, …)
    -- NEW (CP — this migration; HB75 §4 chunk 1 Q3 ratification)
    license               TEXT NOT NULL CHECK (license IN (
                              'ODbL-1.0',
                              'CC-BY-NC-SA-4.0',
                              'public-domain',
                              'foia',
                              'unspecified'
                          ))
);

-- Column-preserving INSERT with deterministic LICENSE backfill per source_id.
-- CASE WHEN handles the two source_id values currently populating the table;
-- ELSE 'unspecified' covers the (currently empty) row classes that may
-- accumulate in future ingestion runs.
INSERT INTO deployment_observations_new (
    id, source_id, extraction_run_id, source_url, source_row_key,
    agency_name, agency_type, juris_type, city, county, state, country,
    lat, lon, technology_category, vendor_raw, citation_url, source_excerpt,
    captured_at, processed_at, notes, license
)
SELECT
    id, source_id, extraction_run_id, source_url, source_row_key,
    agency_name, agency_type, juris_type, city, county, state, country,
    lat, lon, technology_category, vendor_raw, citation_url, source_excerpt,
    captured_at, processed_at, notes,
    CASE
        WHEN source_id = 5 THEN 'CC-BY-NC-SA-4.0'  -- EFF Atlas of Surveillance
        WHEN source_id = 6 THEN 'ODbL-1.0'         -- DeFlock (OSM-mirrored)
        ELSE 'unspecified'                          -- escape hatch; 0 rows match
    END
FROM deployment_observations;

DROP TABLE deployment_observations;

ALTER TABLE deployment_observations_new RENAME TO deployment_observations;

-- Recreate all 6 indexes attached to the original deployment_observations
-- table (verified 2026-05-12 against live DB schema_master):
--   - idx_deployment_obs_source        on (source_id)                — non-unique
--   - idx_deployment_obs_run           on (extraction_run_id)        — non-unique
--   - idx_deployment_obs_state         on (state)                    — non-unique
--   - idx_deployment_obs_vendor        on (vendor_raw)               — non-unique
--   - idx_deployment_obs_tech          on (technology_category)      — non-unique
--   - idx_deployment_obs_source_row    on (source_id, source_row_key) — UNIQUE
-- Plus the PRIMARY KEY auto-index on id (recreated automatically by the
-- new CREATE TABLE).
CREATE INDEX IF NOT EXISTS idx_deployment_obs_source
    ON deployment_observations(source_id);
CREATE INDEX IF NOT EXISTS idx_deployment_obs_run
    ON deployment_observations(extraction_run_id);
CREATE INDEX IF NOT EXISTS idx_deployment_obs_state
    ON deployment_observations(state);
CREATE INDEX IF NOT EXISTS idx_deployment_obs_vendor
    ON deployment_observations(vendor_raw);
CREATE INDEX IF NOT EXISTS idx_deployment_obs_tech
    ON deployment_observations(technology_category);
CREATE UNIQUE INDEX IF NOT EXISTS idx_deployment_obs_source_row
    ON deployment_observations(source_id, source_row_key);

-- ─── FK integrity assertion ─────────────────────────────────────────────────
-- deployment_observations FK refs (verified 2026-05-12 against live DB):
--   Outbound:
--     - source_id → sources(id) ON DELETE SET NULL
--     - extraction_run_id → extraction_runs(id) ON DELETE SET NULL
--   Inbound:
--     - wigle_anchor_priority.deployment_id → deployment_observations(id)
--       ON DELETE CASCADE  (single inbound ref; must survive RENAME)
-- Modern SQLite (≥3.25; default legacy_alter_table=OFF) updates FK
-- references through RENAME during the foreign_keys=OFF window per 0009
-- + 0015 precedent. PRAGMA foreign_key_check below catches any residual
-- broken FK pointers post-rename.
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (16, '0016_license_column');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - HB75 [`3f478a6d`](/MAC/issues/MAC-1#comment-3f478a6d-ad80-4a23-9019-fb5b851a9c49) §4 chunk 1 Q3 — board ratification authorizing the
--   LICENSE column on `deployment_observations` at migration slot 0016.
-- - HB75 [`37232561`](/MAC/issues/MAC-1#comment-37232561-f485-4857-89e8-0b6e45df8da0) — CEO three-artifact ratification proposal
--   (CREDITS.md cross-references `0016_license_column.sql` filename verbatim).
-- - HB76 [`81f0cce7`](/MAC/issues/MAC-1#comment-81f0cce7-1ddc-4275-a8ec-8d7253876c9a) — board ratification of CREDITS.md verbatim
--   (Atlas row `notes` text references this migration filename).
-- - CREDITS.md at repo root (HB76 dropped uncommitted) — Atlas-row attribution
--   cell notes "migration `0016_license_column.sql` for the quarantine flag".
-- - db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql —
--   CP13 precedent for the table-rebuild + verify wrapper pattern.
-- - db/migrations/0015_primary_registry_source_type_extension.sql — CP15
--   most-recent migration; closed-form table-rebuild pattern + version-
--   bump pattern carried forward verbatim here.
-- - db/validation/migration_0009_verify.py — verify wrapper pattern;
--   migration_0016_verify.py to mirror this shape (skeleton in HB76
--   ratification proposal; full version on board scope ratify).
