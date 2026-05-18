-- ============================================================================
-- Migration: 0022_fcc_citation_deferred_queue
-- Purpose:   Create `fcc_citation_deferred_queue` integration staging table
--            to persist the MAC-101 §3 deliverable's deferred-citation
--            backlog (671 entries cumulative across the partial-ABZ + D1
--            narrow cycle). Each row holds the discovery-row half of the
--            dual-citation pair (fccid.io anchor) and the metadata the
--            validator's async re-citation pass needs when FCC.gov egress
--            is restored to emit the paired regulatory-band citation row.
-- Surfaced:  ~/argus-internal/new data 5.17/paperclip_overnight_wave_integration_brief.md
--            §1.1 (entry shape) + Priority 1 (persist queue to staging table).
-- Authority: CEO MAC-178 cycle-7 dispatch (post-CP4 framework, brief §3 #1:
--            dual-citation pair held in `notes.dual_citation_pair_id`; this
--            table is the queue-half of that pattern, not a first-class
--            identifier surface).
-- Bible:     §11 #1  no fabrication — table holds verbatim discovery-row
--                    anchors + queue metadata; no derived identifier values
--                    minted.
--            §11 #7  provenance — `fccid_io_source_url` + `fccid_io_html_sha256`
--                    are the dual-citation pair's discovery-half anchors;
--                    citation-half awaits async pass.
--            §11 #8  no confidence drift — staging-only; no confidence-column
--                    writes. Drained rows become regulatory-band citation
--                    raw_observations when async re-citation pass completes.
--            §11 #11 amendment-log discipline — schema-sibling to CP24
--                    candidate amendment (empirical-premise-verification §2.X),
--                    drafted for ratification in this cycle; CP24 is the
--                    amendment-log entry for the broader wave-pattern. The
--                    dual-citation queue table itself is a brief-documented
--                    structural artifact, not an amendment-grade rule change.
-- Pattern:   New table (no ALTER); fcc_id UNIQUE constraint enforces
--            one-entry-per-FCC-ID. Two indexes for the queue's expected
--            access patterns (drain by promoted_at IS NULL; lookup by fcc_id).
-- Risk:      Low. New table, no existing data; 0 backfill rows; INSERTs
--            land via Priority 1 of the cycle-7 wave.
-- ============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS fcc_citation_deferred_queue (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    fcc_id                          TEXT NOT NULL UNIQUE,
    fccid_io_source_url             TEXT NOT NULL,
    fccid_io_html_sha256            TEXT NOT NULL,
    fcc_gov_unreachable_reason      TEXT NOT NULL,
    deferred_at_utc                 DATETIME NOT NULL,
    discovery_row_provisional_ids   TEXT,        -- JSON array of raw_observations.id
    expected_citation_row_emission  TEXT,        -- predicate prose
    opportunistic_enrichment        TEXT,        -- JSON blob (fcc_grant_ids[], extraction_method, etc.)
    fcc_grant_ids_csv               TEXT,        -- denormalized for index lookup
    created_at                      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    promoted_at                     DATETIME,    -- non-NULL after async re-citation pass emits paired row
    promoted_raw_observation_id     INTEGER REFERENCES raw_observations(id) ON DELETE SET NULL,
    notes                           TEXT
);

CREATE INDEX IF NOT EXISTS idx_fcc_citation_deferred_queue_pending
    ON fcc_citation_deferred_queue (promoted_at) WHERE promoted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_fcc_citation_deferred_queue_fcc_grant_ids
    ON fcc_citation_deferred_queue (fcc_grant_ids_csv);

INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (22, '0022_fcc_citation_deferred_queue');

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - paperclip_overnight_wave_integration_brief.md §1.1 (entry shape spec)
-- - paperclip_overnight_wave_integration_brief.md §2 Priority 1 (load mechanic)
-- - extraction_outputs/fccid_io_admission/fcc_citation_deferred_queue.json
--   (671-entry source file; PC1.7.D.1 schema_version)
-- - BIBLE_AMENDMENTS.md CP24 entry (empirical-premise-verification §2.X —
--   drafted for ratification in MAC-178; HALTED at brief §3 #3)
