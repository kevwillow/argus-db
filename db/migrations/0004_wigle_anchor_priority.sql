-- Argus migration 0004: wigle_anchor_priority staging table.
--
-- Source of truth: PROJECT_BIBLE.md §6 Phase 3 (Tier 2) WiGLE anchored
-- query plan + §4.2 supporting-table convention. Ratified at MAC-9 Step 1
-- by CEO (comment `ea4db5e2`, 2026-05-04T18:34Z) — schema-fit option (i)
-- new staging table over option (ii) additive-columns-on-deployment_observations.
--
-- ─────────────────────────────────────────────────────────────────────────
-- Table scope (CEO-ratified Q1–Q5 + schema-fit at MAC-9 Step 1)
-- ─────────────────────────────────────────────────────────────────────────
-- Schema-fit — option (i): operational-metadata table for the WiGLE
--   prioritized-anchor list. Pattern-fit precedent: CP1 `procurement_records`,
--   CP4 `deployment_observations`, CP6 `fcc_grantees` — separate staging
--   table per source-or-source-class with distinct lifecycle. CEO rationale
--   (verbatim): "rebuildability (DROP TABLE doesn't touch
--   deployment_observations); no write-amp on read-mostly Tier-1 staging;
--   promotion-path cleanliness (Step-2 BSSID hits land in `raw_observations`
--   per §4.2, not here)."
--
-- Q1 — state derivation methodology: `reverse_geocoder` PyPI for DeFlock
--   lat/lon -> admin1 (US state). Atlas rows use existing `state` column.
--   Bible §1 stdlib-first preference allows deps "when stdlib genuinely
--   doesn't suffice." See `derivation_method` CHECK below.
--
-- Q4 — Puerto Rico / OCONUS US territories: T4-territory sub-rank within
--   T4 (NOT T5 international). `state_or_country` carries the 2-letter
--   territory code (PR / USVI / GU / AS / MP).
--
-- Q5 — DDL slot 0004 verified free on disk at MAC-9 ratification time.
--   DBArchitect deferred work (`identifiers.device_category` CHECK
--   extension + Cradlepoint/Sierra `manufacturers.primary_category`
--   backfill) is queued for first-promotion at Phase 4/5 per
--   `PROJECT_STATE.md:11,81`, NOT actively claiming a slot. Schema-version
--   bump 3 -> 4.
--
-- Tier rollup — board-locked T1-T5 (CEO-ratified at Step 1 with worker-
-- proposed T3 expansion to 8 states):
--   T1 = MD (board home turf; ~996 combined Flock-attributed anchors)
--   T2 = DC, NJ, PA, NY, VA (East-coast Flock-heavy)
--   T3 = CT, MA, RI, ME + NH, VT, DE, WV (Census northeast +
--        remaining mid-Atlantic; ~1,924 combined)
--   T4 = the other 38 US states by anchor density (CONUS + AK + HI +
--        US territories at T4-territory sub-rank)
--   T5 = international per §12 geographic_scope open question
--
-- ─────────────────────────────────────────────────────────────────────────
-- Idempotency
-- ─────────────────────────────────────────────────────────────────────────
-- * Every CREATE uses IF NOT EXISTS.
-- * `UNIQUE(deployment_id)` enforces one prioritization row per anchor
--   across re-runs. Build path uses delete-by-extraction_run_id +
--   bulk-insert pattern from MAC-3/MAC-4/MAC-5/MAC-6/MAC-7/MAC-8; the
--   unique index is the structural backstop.
--
-- ─────────────────────────────────────────────────────────────────────────
-- Identifier columns deliberately absent
-- ─────────────────────────────────────────────────────────────────────────
-- Per §4.2 + §11 #1 + §11 #7, this table does NOT carry MAC/OUI/BSSID/SSID.
-- Step-2 WiGLE BSSID hits land in `raw_observations` per §4.2, NOT here.
-- This table is operational metadata derived from Atlas+DeFlock sources
-- via FK to `deployment_observations`; the upstream `source_id` chain is
-- still resolvable through the FK.
-- ─────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_version (version, name)
    VALUES (4, '0004_wigle_anchor_priority');

CREATE TABLE IF NOT EXISTS wigle_anchor_priority (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    deployment_id       INTEGER NOT NULL REFERENCES deployment_observations(id) ON DELETE CASCADE,
    extraction_run_id   INTEGER REFERENCES extraction_runs(id) ON DELETE SET NULL,
    priority_tier       INTEGER NOT NULL CHECK (priority_tier BETWEEN 1 AND 5),
    -- US 2-letter state code (e.g. 'MD', 'CA') OR
    -- US territory 2-letter code (PR / USVI / GU / AS / MP, T4-territory sub-rank per Q4) OR
    -- ISO 3166 alpha-2 country code (e.g. 'BE', 'AU' — T5 international per §12).
    -- Concretely: T1-T4 rows carry US-postal/territory codes;
    --             T5 rows carry ISO 3166 alpha-2 country codes.
    state_or_country    TEXT NOT NULL,
    intra_tier_rank     INTEGER NOT NULL,        -- 1-based within (priority_tier, state_or_country)
    tier_rationale      TEXT,                    -- short string explaining tier+rank choice
    derivation_method   TEXT NOT NULL CHECK (derivation_method IN (
                            'atlas_state_column',         -- Atlas: state from existing `state` column
                            'deflock_reverse_geocode'     -- DeFlock: state from reverse_geocoder admin1 lookup (Q1 ratified)
                        )),
    derivation_notes    TEXT,                    -- e.g. "rg: Amarillo, admin1=Texas, cc=US"
    captured_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (deployment_id)                       -- one prioritization row per anchor
);

CREATE INDEX IF NOT EXISTS idx_wigle_anchor_priority_tier
    ON wigle_anchor_priority (priority_tier, intra_tier_rank);
CREATE INDEX IF NOT EXISTS idx_wigle_anchor_priority_state
    ON wigle_anchor_priority (state_or_country);
CREATE INDEX IF NOT EXISTS idx_wigle_anchor_priority_method
    ON wigle_anchor_priority (derivation_method);
CREATE INDEX IF NOT EXISTS idx_wigle_anchor_priority_run
    ON wigle_anchor_priority (extraction_run_id);
