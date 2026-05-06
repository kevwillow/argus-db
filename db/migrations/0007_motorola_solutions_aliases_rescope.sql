-- Argus migration 0007 — §2.1 Motorola Solutions aliases re-scope (SAR-9 #1).
--
-- Source of truth: BIBLE_AMENDMENTS.md SAR-9 (commit fa89dfc, 2026-05-06).
-- Board ratification: MAC-1 / MAC-41 [`234faaa7`](/MAC/approvals/
-- 234faaa7-e1c0-40fd-a247-f82cb588fc23) approved 2026-05-06T18:05:53Z.
-- Validator dispatch: MAC-44.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Migration-slot allocation chain of record
-- ─────────────────────────────────────────────────────────────────────────────
--   0001 = initial schema (Phase 1)
--   0002 = deployment_observations (Phase 2 — DeFlock / EFF Atlas)
--   0003 = fcc_grantees (Phase 3 — MAC-7)
--   0004 = wigle_anchor_priority (Phase 3 — MAC-9)
--   0005 = council_minutes_matters (Phase 3 — MAC-11)
--   0006 = raw_observations source_row_key (Phase 4 — MAC-12/15)
--   0007 = Motorola Solutions aliases re-scope (Phase 5 Step-4 follow-on² — MAC-44)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- The change
-- ─────────────────────────────────────────────────────────────────────────────
-- The seeded Motorola Solutions row in `manufacturers` (loaded by
-- 0001_initial.sql) carries aliases:
--
--     'Motorola, Motorola Vigilant, Motorola APX, Motorola V300, Motorola V500'
--
-- Per SAR-9 #1, bare `Motorola` is dropped (post-2011 corporate split between
-- Motorola Solutions / police radios and Motorola Mobility / Lenovo / consumer
-- smartphones makes the bare token ambiguous). Bare-token resolution is
-- handed off to the SAR-9 disambig predicate's flag_for_review path.
-- Model-line aliases (Motorola APX / V300 / V500 / Vigilant) remain as they
-- carry unambiguous Solutions-vendor evidence.
--
-- Post-migration aliases:
--
--     'Motorola Vigilant, Motorola APX, Motorola V300, Motorola V500'
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Idempotency
-- ─────────────────────────────────────────────────────────────────────────────
-- The UPDATE matches on the pre-migration aliases string verbatim. Re-running
-- the migration after it has applied is a no-op (the WHERE clause won't
-- match the post-migration string). The schema_version row uses
-- INSERT OR IGNORE so re-runs don't conflict.

PRAGMA foreign_keys = ON;

UPDATE manufacturers
   SET aliases = 'Motorola Vigilant, Motorola APX, Motorola V300, Motorola V500'
 WHERE canonical_name = 'Motorola Solutions'
   AND aliases = 'Motorola, Motorola Vigilant, Motorola APX, Motorola V300, Motorola V500';

INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (7, '0007_motorola_solutions_aliases_rescope');
