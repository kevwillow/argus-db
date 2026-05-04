-- Argus migration 0002: deployment_observations supporting table.
--
-- Source of truth: PROJECT_BIBLE.md §4.2 (post-Correction-Pass-4) — see
-- BIBLE_AMENDMENTS.md CP4 entry (commit d81de3b) for the full rationale,
-- ratified DDL shape, and the bundled operational decisions
-- (`source_type='crowdsourced'`, §11 #3 PII redaction in `notes` JSON,
-- `source_url=dataset URL` with `citation_url` separate for per-row
-- external citations).
--
-- Table scope (bible §4.2 verbatim):
--   "staging table for Tier 1 sources that yield agency × technology ×
--    location × vendor metadata but **no** MAC/OUI/SSID/UUID identifier
--    (EFF Atlas of Surveillance, DeFlock). Identifier columns intentionally
--    absent — promotion to `identifiers` requires a Phase 3+ inference
--    linking a deployment to a concrete identifier candidate (§11 #1).
--    Idempotency keyed by `(source_id, source_row_key)` where
--    `source_row_key` is the source's stable per-row natural key
--    (e.g. Atlas's `AOSNUMBER`)."
--
-- Idempotency:
--   * Every CREATE uses IF NOT EXISTS.
--   * `UNIQUE(source_id, source_row_key)` enforces one row per Atlas/DeFlock
--     source-row across re-runs. Ingests use the delete-by-source_id +
--     bulk-insert pattern from MAC-3/MAC-4 to keep `extraction_runs`
--     readable; the unique index is the structural backstop.
--
-- Why not extend `raw_observations`:
--   `raw_observations.candidate_identifier` is a pre-normalization
--   identifier from the §4.1 enum. Atlas rows have no identifiers (§11 #1),
--   so stuffing `eff_atlas:AOS000001` into `candidate_identifier` is a
--   category error. Separate-table option (B) was ratified at MAC-5 / CP4;
--   precedent from `procurement_records` at MAC-2 / Phase 1 (same shape:
--   schema follows source shape, staging is not a single bag).
--
-- No CHECK on `technology_category` or `vendor_raw`:
--   raw category strings vary across sources; canonical-name matching is
--   Phase 5 inference, not staging-time coercion (§7.2 "do not normalize
--   during ingest").
--
-- Identifier columns deliberately absent:
--   Per §11 #1 (no fabrication) and the bible §4.2 wording, this table
--   does NOT carry MAC/OUI/SSID/UUID. Promotion to `identifiers` is a
--   Phase 3+ inference step keyed off geographic/agency/vendor joins
--   against §4.1 identifier-bearing tables (e.g. WiGLE radius queries
--   around Atlas deployments → BSSID corroboration).
-- ─────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_version (version, name)
    VALUES (2, '0002_deployment_observations');

CREATE TABLE IF NOT EXISTS deployment_observations (
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
    notes                 TEXT                    -- JSON: extra source columns (PII-redacted summary, link 2/3, …)
);

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

-- Idempotency backstop: re-running ingest cannot duplicate per-source rows.
CREATE UNIQUE INDEX IF NOT EXISTS idx_deployment_obs_source_row
    ON deployment_observations(source_id, source_row_key);
