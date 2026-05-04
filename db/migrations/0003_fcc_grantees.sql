-- Argus migration 0003: fcc_grantees supporting table.
--
-- Source of truth: PROJECT_BIBLE.md §6 Phase 3 (Tier 2) FCC ID grantee
-- harvest scope. Ratified at MAC-7 Step 2 (CEO ratification comment
-- 0e95c40a, 2026-05-04T14:34:12Z) — see BIBLE_AMENDMENTS.md CP6 ride-along
-- entry once landed for the §4.2 amendment + §11 #3 corporate-comms read
-- + staleness-ceiling pattern documentation.
--
-- ─────────────────────────────────────────────────────────────────────────
-- Table scope (CEO-ratified Q1–Q4 at MAC-7 Step 2)
-- ─────────────────────────────────────────────────────────────────────────
-- Q1 — Path call: (D-only) opendata.fcc.gov dataset 3b3k-34jp greenlit
--   for Phase 3 ingest. The Socrata mirror is FROZEN at 2021-03-22 (4 yr
--   2 mo stale). The 2021-04 → present grantee gap (incl. Flock Safety
--   scaling era) routes to the Phase 4 extraction worker — NOT ingested
--   here per §11 #1 (no fabrication). Staleness ceiling is a documented
--   permanent property of source 1/4, NOT unfit-for-purpose.
--
-- Q2 — Table name `fcc_grantees` (precise to scope). The CP4 Decision-3
--   umbrella name `fcc_filings` was retired on inspection because the
--   dataset is grantee-only (no `product_code` column, no equipment-class
--   metadata). Phase 4 equipment-filing rows would land in a separate
--   `fcc_equipment_filings` table — no retroactive `record_type`
--   discriminator. Precedent: CP4 `deployment_observations` (precise to
--   Atlas + DeFlock rather than `non_identifier_observations`); CP1-era
--   `procurement_records` (precise to procurement rather than
--   `regulatory_records`).
--
-- Q3 — `source_row_key = grantee_code` (data-shape driven). 50,153 distinct
--   grantee codes; one row per grantee. Phase-4 `fcc_equipment_filings`
--   would key on `grantee_code + '/' + product_code` (canonical FCC ID).
--
-- Q4 — `contact_name` staged as-is. §11 #3 verbatim text targets
--   law-enforcement officer/badge/home-address PII; FCC `contact_name` is
--   mandatory federal regulatory disclosure of corporate-comms compliance
--   contacts. Sample target-vendor contact_names verified verbatim against
--   raw CSV (Axon X4G "Elisabet Dominguez", Cradlepoint UXX "Steve Wood",
--   Sierra Wireless TWV "YING WANG", WatchGuard YJV "Jim Exner") — all
--   plain-name corporate compliance contacts, structurally distinct from
--   §11 #3 worked example. The MAC-5/MAC-6 `rank-token + name` regex
--   returns 2 false-positive corporate hits across 50,153 rows
--   ("Michael Chief Executive Officer", "Captain Giannakos") — zero
--   officer-shape PII. Phase-5 stricter PII gate hook logged in
--   `extraction_runs.notes` (mirrors MAC-4 `source_type='crowdsourced'`
--   reconsider pattern). Raw CSV preserved verbatim per §7.2 audit trail.
--
-- ─────────────────────────────────────────────────────────────────────────
-- Idempotency
-- ─────────────────────────────────────────────────────────────────────────
--   * Every CREATE uses IF NOT EXISTS.
--   * `UNIQUE(source_id, source_row_key)` enforces one row per grantee
--     across re-runs. Ingest uses the delete-by-source_id + bulk-insert
--     pattern from MAC-3/MAC-4/MAC-5/MAC-6; the unique index is the
--     structural backstop.
--
-- ─────────────────────────────────────────────────────────────────────────
-- Identifier columns deliberately absent
-- ─────────────────────────────────────────────────────────────────────────
-- Per §11 #1 + §11 #8, this table does NOT carry MAC/OUI/SSID/UUID.
-- Promotion to `identifiers` is Phase 4+ (test-report PDF mining via
-- the LLM extraction worker, after MAC-7 close). FCC EAS grantees are
-- corporate registrations — they map a grantee_code prefix to a vendor,
-- nothing more. The product/equipment rows under each grantee live in
-- a different FCC dataset (`apps.fcc.gov/oetcf/eas/reports/Generic*`)
-- which is currently Akamai-WAF blocked host-wide — Phase 4 territory.
-- ─────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_version (version, name)
    VALUES (3, '0003_fcc_grantees');

CREATE TABLE IF NOT EXISTS fcc_grantees (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id             INTEGER NOT NULL REFERENCES sources(id),
    extraction_run_id     INTEGER NOT NULL REFERENCES extraction_runs(id),
    source_url            TEXT NOT NULL,
    source_row_key        TEXT NOT NULL,        -- = grantee_code (Q3)
    grantee_code          TEXT NOT NULL,        -- 3-5 char alphanumeric prefix
    grantee_name          TEXT NOT NULL,        -- corporate registrant
    mailing_address       TEXT,
    po_box                TEXT,
    city                  TEXT,
    state                 TEXT,                  -- US state name or N/A
    country               TEXT,                  -- country name (text, not ISO)
    zip_code              TEXT,
    contact_name          TEXT,                  -- corporate compliance contact (Q4 stage-as-is)
    date_received         TEXT NOT NULL,         -- ISO date 'YYYY-MM-DD'
    source_excerpt        TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    notes                 TEXT,                  -- JSON: raw_row passthrough + Phase-5 hooks
    captured_at           TEXT NOT NULL DEFAULT (datetime('now')),
    processed_at          TEXT,
    UNIQUE (source_id, source_row_key)
);

CREATE INDEX IF NOT EXISTS idx_fcc_grantees_grantee_code
    ON fcc_grantees (grantee_code);
CREATE INDEX IF NOT EXISTS idx_fcc_grantees_grantee_name
    ON fcc_grantees (grantee_name);
CREATE INDEX IF NOT EXISTS idx_fcc_grantees_country_state
    ON fcc_grantees (country, state);
CREATE INDEX IF NOT EXISTS idx_fcc_grantees_date_received
    ON fcc_grantees (date_received);
