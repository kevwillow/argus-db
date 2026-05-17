-- ============================================================================
-- Migration: 0020_source_type_enum_extension
-- Purpose:   Extend `sources.source_type` CHECK enum with 3 net-new values
--            per CP23 §-text addition + CEO Path B ruling (wide-net cycle 3
--            schema-contract patch finding #2):
--              - 'judicial_filing'        — CourtListener / RECAP-class
--                                            judicial-discovery sources
--                                            (replaces silent fallback to
--                                            'regulatory')
--              - 'disclosure_filing'       — SEC EDGAR / corporate-disclosure
--                                            class
--              - 'procurement_disclosure'  — supplier-self-disclosure /
--                                            vendor-side procurement
--                                            artifact class
--            Final CHECK cardinality: 10 prior + 3 net-new = 13 values
--            cumulatively (sources.source_type only — identifiers.source_type
--            is NOT extended because the 3 new classes are source-level
--            taxonomy, not identifier-row promotion bands. Promotions from
--            these sources still land under existing identifier source_type
--            bands per §8.2 strict reading).
-- Surfaced:  ~/argus-internal/new data 5.16/schema_contract_patch_cycle3.md
--            §1 finding #2 (2026-05-16 US-domestic pivot mega-session). CEO
--            ruling Path B at MAC-169 dispatch 2026-05-17.
-- Authority: CEO MAC-169 dispatch (CP23 coordinated amendment).
-- Bible:     §11 #11 — schema changes are CEO-only ratification post-board.
--            CP23 BIBLE_AMENDMENTS entry is the §-text + amendment-log pairing
--            for this migration in the coordinated commit set.
-- Pattern:   SQLite table-rebuild per 0009 / 0015 / 0018 / 0019 precedent.
--            PRAGMA foreign_keys=OFF outside transaction; CREATE _new with
--            extended CHECK; INSERT SELECT * (column-preserving copy); DROP
--            old; RENAME _new → old; recreate `idx_sources_url`;
--            foreign_key_check; schema_version bump; COMMIT;
--            foreign_keys=ON.
-- Risk:      Low. Pure additive enum extension. Column shape unchanged from
--            0015 post-rebuild state (7 columns: id, name, url, source_type,
--            tier, last_fetched_at, last_status, notes). Active 43 rows
--            preserved via column-list-preserving INSERT SELECT.
-- ============================================================================
--
-- Migration-slot allocation chain of record:
--   0001-0017  see 0018 header for the full chain
--   0018 = identifier_types extension batch — CP20 SAR-13 §S.3 routing
--   0019 = identifier_types round-2 — MAC-117 §1 routing slate
--   0020 = source_type enum extension — CP23 cycle-3 §1 finding #2 (this
--          migration; 3 net-new values; 13-value cumulative CHECK)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative CHECK enum (10 prior + 3 net-new = 13 values total)
-- ─────────────────────────────────────────────────────────────────────────────
-- The 10 prior values are paste-verified verbatim against the live `sources`
-- table CHECK clause from migration 0015 (10 values; identical to live DB at
-- schema_version=19). Per
-- `feedback_cumulative_check_enum_across_sequenced_migrations.md`, the
-- rebuild-pattern migration MUST carry forward ALL prior CHECK enum values,
-- not just its own delta.
--
-- Live enum verification (2026-05-17 against db/argus.db, schema_version=19):
--   'official', 'regulatory', 'procurement', 'academic', 'foia',
--   'crowdsourced', 'inferred', 'manufacturer_doc', 'manufacturer_app',
--   'primary_registry'   = 10 values
--
-- The 3 net-new types (CP23 §-text addition; CEO Path B ruling):
--   1. `judicial_filing`        — Court records and RECAP-class artifacts
--                                  (CourtListener V4 admission cycle-3 RG3).
--                                  Replaces the silent fallback to
--                                  'regulatory' applied during cycle-3 staging.
--   2. `disclosure_filing`      — SEC EDGAR + analogous corporate-disclosure
--                                  filings (wide-net cycle-1 RG5 admission).
--                                  Distinguishes corporate-self-disclosure
--                                  from equipment-authorization regulatory
--                                  records.
--   3. `procurement_disclosure` — Supplier-self-disclosure / vendor-side
--                                  procurement artifacts (future runguides).
--                                  Distinguishes vendor-disclosed contracts
--                                  from agency-side procurement records
--                                  (existing 'procurement' band).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Bible §11 hard-rule discipline
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 #1  no fabrication — the 3 new classes are taxonomy refinements over
--   existing source admission categories; no row writes in this migration.
--   Sources rows admitted under these new bands going forward must carry
--   per-row source_url citing the issuer directly (CourtListener's docket
--   URL, SEC EDGAR's filing URL, vendor-publication URL).
-- §11 #7  no main-table promotion without provenance — schema-only; zero
--   row writes. Identifier-row promotions from sources of these 3 new
--   classes still land under existing identifiers.source_type bands per
--   §8.2 strict reading. Promotion-pipeline confidence bands (§8.2) bind
--   on the identifier-row source_type, not the sources-row source_type;
--   the new taxonomy is informational at the sources tier only.
-- §11 #8  no confidence drift — no confidence-column writes. Reclassification
--   of any existing sources row from a prior band to one of the 3 new bands
--   is a future Validator-side audit decision; CP23 ratifies the taxonomy,
--   not retroactive reclassification of admitted sources rows.
-- §11 #11 amendment-log discipline — this migration is the schema-sibling
--   to CP23 BIBLE_AMENDMENTS.md entry (coordinated commit). Bible HEAD bumps
--   to the CP23 commit.
--
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── sources table rebuild ──────────────────────────────────────────────────
-- Cumulative state: source_type extended to 13 values (CP23); column shape
-- unchanged from 0015 post-rebuild state (7 columns + id).
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
                        -- CP15 (migration 0015)
                        'primary_registry',
                        -- CP23 (this migration) — cycle-3 §1 finding #2
                        'judicial_filing',
                        'disclosure_filing',
                        'procurement_disclosure'
                    )),
    tier            INTEGER CHECK (tier IN (1, 2, 3, 4)),
    last_fetched_at DATETIME,
    last_status     TEXT,
    notes           TEXT
);

INSERT INTO sources_new SELECT * FROM sources;

DROP TABLE sources;

ALTER TABLE sources_new RENAME TO sources;

-- Recreate the single index from live state (verified via PRAGMA index_list).
CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);

-- ─── FK integrity assertion ─────────────────────────────────────────────────
-- sources is referenced by:
--   - raw_observations.source_id (ON DELETE SET NULL)
--   - extraction_runs.source_id  (varies)
--   - behavioral_signatures.source_id (ON DELETE RESTRICT)
--   - council_minutes_matters.source_id (no action)
--   - source_reclassifications (varies)
-- Modern SQLite (≥3.25; legacy_alter_table=OFF) updates FK references through
-- RENAME during the foreign_keys=OFF window, per 0009 / 0015 precedent.
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (20, '0020_source_type_enum_extension');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - BIBLE_AMENDMENTS.md CP23 entry (coordinated commit — schema-sibling
--   reference; CP23 §-text addition documents the 3 new bands in PROJECT_BIBLE.md
--   §-text)
-- - ~/argus-internal/new data 5.16/schema_contract_patch_cycle3.md §1 finding
--   #2 (cycle-3 source-of-truth for the taxonomy gap and Path B recommendation)
-- - ~/argus-internal/new data 5.16/schema_contract_patch_notes_license.md
--   (cycle-1 sibling — license-into-notes folding precedes this taxonomy
--   extension chronologically)
-- - feedback_cumulative_check_enum_across_sequenced_migrations.md (cumulative
--   CHECK-enum discipline — binding for this migration's authoring)
-- - db/migrations/0015_primary_registry_source_type_extension.sql (most
--   recent sources-table rebuild precedent; preserved column shape verbatim
--   in this migration's sources_new)
