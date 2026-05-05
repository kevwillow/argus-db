-- Argus migration 0006 — raw_observations source_row_key (Phase 4 Wave B prep).
--
-- Source of truth: BIBLE_AMENDMENTS.md SAR-6 (Phase 4 per-wave checkpoint
-- discipline) + MAC-12 Step-0 ratification 3310563e + MAC-15 Step 2.0
-- ratification 1169a064 (2026-05-05).
--
-- Adds the (source_id, source_row_key) idempotency constraint that mirrors the
-- staging-table precedent set by 0002 (deployment_observations), 0003
-- (fcc_grantees), and 0005 (council_minutes_matters). Wave B Extraction
-- Worker computes source_row_key = sha256("doc_url|candidate_type|candidate_identifier")
-- so re-running extraction over the same Step-1 manifest produces zero new
-- raw_observations rows (UNIQUE-violation skipped).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Migration-slot allocation chain of record
-- ─────────────────────────────────────────────────────────────────────────────
--   0001 = initial schema (Phase 1)
--   0002 = deployment_observations (Phase 2 — DeFlock / EFF Atlas)
--   0003 = fcc_grantees (Phase 3 — MAC-7)
--   0004 = wigle_anchor_priority (Phase 3 — MAC-9)
--   0005 = council_minutes_matters (Phase 3 — MAC-11)
--   0006 = raw_observations source_row_key (Phase 4 Wave B — THIS MIGRATION)
--
-- Supersedes the 0005-line-26 standing reservation
-- ("0006 = DBArchitect device_category CHECK extension (deferred standing
-- recall, queued for Phase 4/5 per PROJECT_STATE.md)") per MAC-15 ratification
-- decision #2: the device_category CHECK extension was a queued-no-dispatch
-- standing reservation; Wave B is in flight with active worker, so it claims
-- 0006. The device_category extension shifts to the next available slot when
-- DBArchitect dispatches.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- App-level vs DB-level enforcement
-- ─────────────────────────────────────────────────────────────────────────────
-- §7.3 + §11 #7 source_excerpt ≤200-char enforcement is APP-LEVEL
-- (db/sources/vendor_docs.py raises ValueError + drops candidate on overflow),
-- NOT codified as a column-level CHECK. Verified gap: 0001 declares
-- raw_observations.source_excerpt as plain TEXT (no length constraint).
-- Module enforces at insert via raise-on-overflow + positive/negative/boundary
-- tests at 199/200/201 chars. Hard raise + drop (NOT truncate) preserves the
-- §11 #7 verbatim-quote guarantee.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Nullable column + partial index design
-- ─────────────────────────────────────────────────────────────────────────────
-- source_row_key is nullable (NOT NOT NULL) so existing raw_observations rows
-- (zero today, but the schema must tolerate any back-compat shape) don't fail
-- the ALTER. The UNIQUE index uses WHERE source_row_key IS NOT NULL (SQLite
-- partial index) so legacy NULLs don't collide. New Wave-B writes always carry
-- a non-NULL source_row_key per the worker's idempotent insert path.

PRAGMA foreign_keys = ON;

ALTER TABLE raw_observations ADD COLUMN source_row_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_obs_source_row
    ON raw_observations(source_id, source_row_key)
    WHERE source_row_key IS NOT NULL;

INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (6, '0006_raw_observations_source_row_key');
