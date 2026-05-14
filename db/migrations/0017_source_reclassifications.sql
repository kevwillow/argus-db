-- ============================================================================
-- Migration: 0017_source_reclassifications
-- Purpose:   Add `source_reclassifications` audit table — row-level forensic
--            surface for §11 #8 reclassification discipline (band downgrade,
--            source_url upgrade, source_type change, confidence drift).
-- Surfaced:  MAC-88 board ratification dispatch
--            [`a1dab600`](/MAC/issues/MAC-88#comment-a1dab600-e64b-4327-89b3-4a4e3ee4ef05)
--            §2 audit-trail framing Option α ratified 2026-05-14. Dispatched
--            for execution at MAC-95 (CP19 coordinated commit dispatch).
-- Authority: Board ratification at MAC-88 a1dab600 §2. CEO pre-flight surface
--            at [`99bb1438`](/MAC/issues/MAC-88#comment-99bb1438-30a5-4e69-9164-69cacbda649a).
-- Bible:     §11 #11 — schema changes are CEO-only ratification post-board.
--            §4.2 supporting-table addition + §11 #8 audit-trail sub-rule land
--            in the same CP19 coordinated commit (§-text amendment +
--            schema-migration sibling discipline).
-- Pattern:   Additive new table — no rebuild of any existing table. INSERT
--            into schema_version uses ON CONFLICT (version) DO NOTHING per
--            project convention; CREATE TABLE (no IF NOT EXISTS) per project
--            convention — if the table already exists, that's an
--            apply-state-error worth surfacing.
-- Risk:      Low. Additive new table; no existing column / FK / index
--            changes. CHECK constraints exercise INTEGER ranges only.
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
--   0016 = deployment_observations LICENSE column (HB75 §4 chunk 1)
--   0017 = source_reclassifications NEW TABLE (CP19 — this migration)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Open design question — Phase-1 procurement_records carveout (referenced)
-- ─────────────────────────────────────────────────────────────────────────────
-- Per the Phase-1 0001_initial.sql header carveout (§4.5 procurement-only
-- records cannot live in `identifiers` because identifier/identifier_type
-- are NOT NULL), supporting tables hang off `identifiers` rather than
-- extending its column set. `source_reclassifications` follows the same
-- shape: an audit-trail FK back-reference from identifier_id, not a column
-- on identifiers itself. Both decisions preserve the §11 hard-rule shape
-- of the canonical row table.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Row-level audit-trail rationale (CP19 framing)
-- ─────────────────────────────────────────────────────────────────────────────
-- Prior CPs produced new rows, new bands, or upward reclassification.
-- MAC-88 Wave-B+ sources reclassification sweep is the first row-level
-- DOWNGRADE pass on already-promoted canonical rows (335 FAA RID rows
-- from primary_registry band to crowdsourced per §11 #8 strict reading).
-- Existing audit surfaces (git history, extraction_runs log, bible
-- amendment-log) don't make per-row reclassification queryable forensically:
--
--   - git history: queryable by file but not by row-id; expensive scan
--   - extraction_runs: per-run aggregate, no per-row snapshot
--   - BIBLE_AMENDMENTS.md: governance-level, not row-level
--
-- `source_reclassifications` provides the O(1) "show me every row this sweep
-- touched + why" surface that complements the existing tools. Each row
-- captures pre/post snapshot of source_url + source_type + confidence,
-- groups under a sweep_event_id, records substantive per-row rationale
-- (board's a1dab600 §2 refinement: self-explanatory at row-level WITHOUT
-- cross-referencing the dispatch), and cites the CP/dispatch anchor.
--
-- The audit table is INSERT-only by convention — UPDATE / DELETE on
-- source_reclassifications is a discipline violation (not schema-enforced
-- to avoid coupling discipline-enforcement with apply-time tooling).
-- ON DELETE CASCADE on the identifier_id FK because if the identifier row
-- is hard-deleted (rare; the project prefers supersedes-pointer over
-- delete), the audit row's anchor is no longer meaningful.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Bible §11 hard-rule discipline
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 #1  no fabrication — pre/post snapshot columns mirror existing
--   identifiers row state at sweep time; reclassification_reason must be
--   substantive per-row (board's a1dab600 §2 refinement).
-- §11 #7  no promotion without provenance — N/A; this is an audit table,
--   not a promotion target. Identifier row provenance is unaffected by
--   audit row inserts.
-- §11 #8  audit-trail discipline EXTENSION — this migration is the
--   schema-sibling to the CP19 §11 #8 sub-rule (per the CP19 coordinated
--   commit). Row-level reclassifications MUST land an audit entry in the
--   SAME transaction as the identifier-row UPDATE — discipline-level not
--   schema-enforced (would require triggers; project convention is
--   discipline-enforced at writer-code level).
-- §11 #11 amendment-log discipline — this migration is the schema-sibling
--   to the CP19 §4.2 + §7.5 + §11 #8 amendment-log entries; coordinated
--   commit per board explicit bundling at MAC-88 a1dab600.
-- §11 #15 schema-sibling-on-§-amendment discipline — counterpart: NEW
--   §-amendment introducing a supporting-table addition requires sibling
--   migration. This migration IS that sibling. CP-counter: 18 → 19.
--
-- ─────────────────────────────────────────────────────────────────────────────

BEGIN;

CREATE TABLE source_reclassifications (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,

    -- The identifier row that was reclassified
    identifier_id               INTEGER NOT NULL REFERENCES identifiers(id) ON DELETE CASCADE,

    -- Groups all rows in one sweep dispatch (e.g., 'MAC-94-sweep-1' or
    -- similar per-dispatch event identifier). Same shape as argus_run_id
    -- for exports.
    sweep_event_id              TEXT NOT NULL,

    -- Pre-sweep state (snapshot at sweep-start)
    pre_source_url              TEXT NOT NULL,
    post_source_url             TEXT NOT NULL,
    pre_source_type             TEXT NOT NULL,
    post_source_type            TEXT NOT NULL,
    pre_confidence              INTEGER NOT NULL CHECK (pre_confidence BETWEEN 0 AND 100),
    post_confidence             INTEGER NOT NULL CHECK (post_confidence BETWEEN 0 AND 100),

    -- Per-row substantive rationale. Convention (NOT schema-enforced
    -- beyond NOT NULL): must be self-explanatory at row-level WITHOUT
    -- cross-referencing the dispatch — board's MAC-88 a1dab600 §2
    -- refinement. Example shape for a Scope 2 row: "Wave-A staging
    -- source (jlrjr wrapper field-observation aggregation,
    -- https://github.com/alphafox02/DragonSync); no current FAA-canonical
    -- equivalent. Per CP15 §11 #8 strict reading, primary_registry
    -- status requires source_url at FAA registry issuer publication;
    -- this row's lineage doesn't satisfy."
    reclassification_reason     TEXT NOT NULL,

    -- CP / bible commit / dispatch citation (audit anchor)
    reclassification_anchor     TEXT NOT NULL,

    reclassified_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Optional additional context (NOT NULL'd — keeps it optional vs the
    -- required reclassification_reason which carries the substantive
    -- per-row rationale)
    notes                       TEXT
);

CREATE INDEX idx_source_recl_identifier_id   ON source_reclassifications(identifier_id);
CREATE INDEX idx_source_recl_sweep_event     ON source_reclassifications(sweep_event_id);
CREATE INDEX idx_source_recl_reclassified_at ON source_reclassifications(reclassified_at);

INSERT INTO schema_version (version, name)
VALUES (17, '0017_source_reclassifications')
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - BIBLE_AMENDMENTS.md CP19 entry (this migration's schema-sibling)
-- - PROJECT_BIBLE.md §4.2 source_reclassifications supporting-table bullet
-- - PROJECT_BIBLE.md §7.5 source_type-exclusion sub-block + Don't bullet
-- - PROJECT_BIBLE.md §11 #8 audit-trail sub-rule (CP19 2026-05-14)
-- - MAC-88 board ratification a1dab600 §2 (audit-trail framing) + §5 (source_type exclusion)
-- - MAC-95 CP19 coordinated commit dispatch (this migration's authoring anchor)
-- - feedback_enum_amendment_needs_schema_migration_sibling.md (sibling-write discipline binding)
-- - feedback_bible_amendment_downstream_consumer_audit.md (downstream-consumer audit binding)
