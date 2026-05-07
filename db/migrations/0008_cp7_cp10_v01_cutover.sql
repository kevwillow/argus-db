-- Argus migration 0008 — CP7 + CP10 v0.1 cutover (data-layer prep, no schema change).
--
-- Source of truth: BIBLE_AMENDMENTS.md CP7 + CP10 (commit 0aa89a0, 2026-05-07).
-- Board ratification: MAC-1 [`4f075253`](/MAC/issues/MAC-1#comment-
--   4f075253-2eae-4ea3-9db5-c67c6f02e012) approved 2026-05-07T17:10:13Z
--   (six-pick + two-halt-flag bundle).
-- Validator dispatch: MAC-48 (Sub-deliverable A).
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
--   0007 = Motorola Solutions aliases re-scope (SAR-9 #1 — MAC-44)
--   0008 = CP7 + CP10 v0.1 cutover (data-layer prep — MAC-48)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- The change
-- ─────────────────────────────────────────────────────────────────────────────
-- Two CP-driven data updates against `identifiers` (active set only,
-- `superseded_by IS NULL`):
--
--   CP10 17-row narrow-read flip — `device_category` from `unknown` to specific
--     category for the §11 #10 narrow-read slate (BIBLE_AMENDMENTS.md CP10):
--       DJI            → drone           (13 rows)
--       Flock Safety   → alpr            (1  row, the inferred non-Wave-A row)
--       Skydio         → drone           (1  row)
--       Cellebrite     → hacking_tool    (1  row)
--       SoundThinking  → gunshot_detect  (1  row)
--     Total: 17 rows. CP10 is a category flip, not a confidence uplift —
--     all 17 stay at conf=50–55 per §11 #8 (no confidence drift).
--
--     The Wave-A canonical row (`identifiers.id=1`, conf=60, `alpr`) is
--     untouched — it already carries a specific category. The Flock Safety
--     OUI flip targets the inferred non-Wave-A row (id=449, OUI b4:1e:52).
--
--   CP7 geographic_scope backfill — populate `geographic_scope` per CP7
--     source-class defaults (BIBLE_AMENDMENTS.md CP7):
--       id=1 Wave-A Flock Safety MAC (DeFlock-style recon, US-deployed) → 'US'
--       all other 62 active rows are vendor-OUI-only inferences (IEEE OUI /
--         IEEE oui28 / IEEE oui36 / wireshark manuf) where deployment
--         geography is unknowable per CP7 directive          → 'global'
--     Total: 63 rows backfilled (1 → 'US', 62 → 'global').
--
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 hard-rule discipline
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 #1  no fabrication        — every backfill value derives from CP7 source-
--                                 class defaults; no fabricated geographies.
-- §11 #7  provenance carry-     — `source_url`, `source_excerpt`, and
--          through                `extraction_run_id` lineage untouched.
-- §11 #8  no confidence drift   — CP10 is a category flip, NOT a confidence
--                                 uplift; the `confidence` column is not
--                                 touched by either UPDATE.
-- §11 #11 halt-the-line         — A3 spot-check (run by the wrapper script
--                                 `db/validation/cp7_cp10_v01_cutover.py`)
--                                 verifies row counts before commit.
-- §11 #13 no unknown to Lynceus — post-flip, the 17 rows have specific
--                                 categories and pass §11 #13 at export time.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Idempotency
-- ─────────────────────────────────────────────────────────────────────────────
-- Every UPDATE carries an idempotency guard:
--   * CP10 flips guard on `device_category = 'unknown'` — a row already
--     flipped won't match the WHERE clause on a re-run.
--   * CP7 backfills guard on `geographic_scope IS NULL` — a row already
--     backfilled won't match.
-- The schema_version row uses INSERT OR IGNORE so re-runs don't conflict.
-- Re-running this migration on a post-migration DB is a verified no-op.

PRAGMA foreign_keys = ON;

-- ─── CP10 17-row flip ────────────────────────────────────────────────────────
-- DJI  → drone (13 rows expected)
UPDATE identifiers
   SET device_category = 'drone'
 WHERE manufacturer = 'DJI'
   AND device_category = 'unknown'
   AND superseded_by IS NULL;

-- Flock Safety → alpr (1 row expected; Wave-A id=1 is already 'alpr')
UPDATE identifiers
   SET device_category = 'alpr'
 WHERE manufacturer = 'Flock Safety'
   AND device_category = 'unknown'
   AND superseded_by IS NULL;

-- Skydio → drone (1 row expected)
UPDATE identifiers
   SET device_category = 'drone'
 WHERE manufacturer = 'Skydio'
   AND device_category = 'unknown'
   AND superseded_by IS NULL;

-- Cellebrite → hacking_tool (1 row expected)
UPDATE identifiers
   SET device_category = 'hacking_tool'
 WHERE manufacturer = 'Cellebrite'
   AND device_category = 'unknown'
   AND superseded_by IS NULL;

-- SoundThinking → gunshot_detect (1 row expected)
UPDATE identifiers
   SET device_category = 'gunshot_detect'
 WHERE manufacturer = 'SoundThinking'
   AND device_category = 'unknown'
   AND superseded_by IS NULL;

-- ─── CP7 geographic_scope backfill ──────────────────────────────────────────
-- Wave-A Flock Safety MAC (id=1, DeFlock-style recon, US-deployed) → 'US'
UPDATE identifiers
   SET geographic_scope = 'US'
 WHERE id = 1
   AND geographic_scope IS NULL
   AND superseded_by IS NULL;

-- All other active rows are vendor-OUI-only inferences with unknowable
-- deployment geography per CP7 directive → 'global'
UPDATE identifiers
   SET geographic_scope = 'global'
 WHERE geographic_scope IS NULL
   AND superseded_by IS NULL
   AND id != 1;

INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (8, '0008_cp7_cp10_v01_cutover');
