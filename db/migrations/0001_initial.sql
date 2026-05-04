-- Argus initial schema migration (0001).
-- Source of truth: PROJECT_BIBLE.md §4 (Data Schema), §4.2 (Supporting tables),
-- §4.3 (Normalization rules), §4.5 (Procurement-only carveout), §8.4 (False-positive
-- prevention — `device_category='unknown'` is a real value).
--
-- Idempotency: every CREATE uses IF NOT EXISTS. The seed step uses INSERT OR IGNORE
-- against UNIQUE(canonical_name). Re-running this script on an empty or partially
-- migrated DB is safe.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Procurement-only design decision (bible §4.5, §11 #14)
-- ─────────────────────────────────────────────────────────────────────────────
-- §4.5 references "procurement-only records (source_type='procurement' with no
-- MAC/OUI/UUID, only an agency-bought-vendor mapping)". §4.1 makes both
-- `identifier` and `identifier_type` NOT NULL on `identifiers`, which makes the
-- main table structurally hostile to such rows.
--
-- Decision: option (a) — separate `procurement_records` table.
--   * Distinct primary-key space (no FK collision with `identifiers.id`).
--   * Distinct lifecycle: procurement records can graduate to `identifiers` later
--     by linking via `procurement_records.linked_identifier_id`.
--   * Bible §11 #14 forbids exporting procurement-only records to Talos at all,
--     so isolating them prevents accidental promotion through dedup or export.
--   * Keeps the §4.1 `identifiers` schema literal — no nullable identifier columns.
--
-- Rejected alternatives:
--   (b) raw_observations only — would block any structured per-agency procurement
--       querying without a heavy parse step, and `raw_observations` is meant to
--       be an audit log not a queryable secondary table.
--   (c) escalate — straightforward enough that escalation costs more than just
--       documenting the choice here for CEO review at Checkpoint 1.
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = ON;

-- ─── schema_version ────────────────────────────────────────────────────────
-- Tracks applied migrations so `argus_cli.py status` can print the version.

CREATE TABLE IF NOT EXISTS schema_version (
    version       INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    applied_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_version (version, name) VALUES (1, '0001_initial');

-- ─── identifiers (main table, bible §4.1) ──────────────────────────────────
-- Every column listed in §4.1, types and NOT NULL flags as specified.
-- Enum CHECKs enforce the §4.1 enums for identifier_type and source_type and
-- the §2.1 + §8.4 enum for device_category. `confidence` clamped 0–100 per §8.2.

CREATE TABLE IF NOT EXISTS identifiers (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL CHECK (identifier_type IN (
                          'oui', 'mac', 'mac_range', 'bssid',
                          'ssid_exact', 'ssid_pattern',
                          'ble_uuid', 'ble_service',
                          'device_fingerprint'
                      )),
    device_category   TEXT NOT NULL CHECK (device_category IN (
                          'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                          'drone', 'gunshot_detect', 'hacking_tool',
                          'covert_cam', 'gps_tracker', 'face_recog',
                          'drone_detect', 'unknown'
                      )),
    manufacturer      TEXT,
    model             TEXT,
    confidence        INTEGER CHECK (confidence BETWEEN 0 AND 100),
    source_url        TEXT NOT NULL,
    source_type       TEXT NOT NULL CHECK (source_type IN (
                          'official', 'regulatory', 'procurement',
                          'academic', 'foia', 'crowdsourced',
                          'inferred', 'manufacturer_doc'
                      )),
    source_excerpt    TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    geographic_scope  TEXT,
    first_seen        DATETIME,
    last_verified     DATETIME,
    notes             TEXT,
    superseded_by     INTEGER REFERENCES identifiers(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_identifiers_identifier
    ON identifiers(identifier);
CREATE INDEX IF NOT EXISTS idx_identifiers_type
    ON identifiers(identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_category
    ON identifiers(device_category);
CREATE INDEX IF NOT EXISTS idx_identifiers_superseded
    ON identifiers(superseded_by);
-- Identical-identifier dup detection (bible §8.3) needs fast (identifier, type) lookup.
CREATE INDEX IF NOT EXISTS idx_identifiers_ident_type
    ON identifiers(identifier, identifier_type);

-- ─── manufacturers (canonical-name registry, bible §4.3) ───────────────────
-- "Manufacturer names: matched against a canonical list maintained in
-- `manufacturers` table; new vendors added explicitly."

CREATE TABLE IF NOT EXISTS manufacturers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name  TEXT NOT NULL UNIQUE,
    aliases         TEXT,           -- comma-separated alternate names
    primary_category TEXT,          -- best-fit §2.1 category, NULL when multi-purpose
    source_url      TEXT NOT NULL,  -- where the canonical name comes from (bible itself is fine)
    notes           TEXT,
    added_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_manufacturers_name
    ON manufacturers(canonical_name);

-- ─── sources (bible §4.2) ──────────────────────────────────────────────────
-- "registry of every source crawled, with last-fetch timestamp and status"

CREATE TABLE IF NOT EXISTS sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL UNIQUE,
    source_type     TEXT NOT NULL CHECK (source_type IN (
                        'official', 'regulatory', 'procurement',
                        'academic', 'foia', 'crowdsourced',
                        'inferred', 'manufacturer_doc'
                    )),
    tier            INTEGER CHECK (tier IN (1, 2, 3, 4)),  -- bible §5
    last_fetched_at DATETIME,
    last_status     TEXT,    -- e.g. 'ok', 'http_404', 'rate_limited'
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);

-- ─── extraction_runs (bible §4.2) ──────────────────────────────────────────
-- "log of every extraction job: agent id, source, started_at, finished_at,
-- records_in, records_out, errors"
-- Defined before raw_observations because raw_observations.extraction_run_id
-- references this table.

CREATE TABLE IF NOT EXISTS extraction_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL,
    source_id       INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    started_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at     DATETIME,
    records_in      INTEGER DEFAULT 0,
    records_out     INTEGER DEFAULT 0,
    errors          INTEGER DEFAULT 0,
    status          TEXT,    -- 'running', 'ok', 'failed', 'partial'
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_source ON extraction_runs(source_id);
CREATE INDEX IF NOT EXISTS idx_runs_agent ON extraction_runs(agent_id);

-- ─── raw_observations (bible §4.2) ─────────────────────────────────────────
-- "staging table; raw extracted records before normalization (preserve forever
-- for audit)". Body kept as-is; normalization happens in a later step.

CREATE TABLE IF NOT EXISTS raw_observations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id           INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    extraction_run_id   INTEGER REFERENCES extraction_runs(id) ON DELETE SET NULL,
    source_url          TEXT NOT NULL,
    raw_payload         TEXT,           -- raw extracted blob (JSON/TEXT)
    candidate_identifier TEXT,           -- pre-normalization
    candidate_type      TEXT,
    candidate_category  TEXT,
    candidate_manufacturer TEXT,
    source_excerpt      TEXT,
    captured_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at        DATETIME,
    promoted_identifier_id INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_obs_source ON raw_observations(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_obs_run ON raw_observations(extraction_run_id);

-- ─── conflicts (bible §4.2) ────────────────────────────────────────────────
-- "when two sources disagree on the same identifier; reviewed and resolved by CEO"
-- Also receives validator rejections per bible §7.4 with reason='known_fake_pattern'.

CREATE TABLE IF NOT EXISTS conflicts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier_a_id     INTEGER REFERENCES identifiers(id) ON DELETE CASCADE,
    identifier_b_id     INTEGER REFERENCES identifiers(id) ON DELETE CASCADE,
    raw_observation_id  INTEGER REFERENCES raw_observations(id) ON DELETE CASCADE,
    reason              TEXT NOT NULL,    -- e.g. 'known_fake_pattern', 'category_disagreement'
    detected_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at         DATETIME,
    resolved_by         TEXT,             -- agent id or human
    resolution_notes    TEXT
);

CREATE INDEX IF NOT EXISTS idx_conflicts_a ON conflicts(identifier_a_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_b ON conflicts(identifier_b_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved
    ON conflicts(resolved_at) WHERE resolved_at IS NULL;

-- ─── procurement_records (bible §4.5 carveout — see header decision) ──────
-- Holds agency-bought-vendor mappings that have no concrete MAC/OUI/UUID yet.
-- NEVER exported to Talos (bible §11 #14). Linkable to `identifiers` once a
-- concrete identifier is matched (`linked_identifier_id`).

CREATE TABLE IF NOT EXISTS procurement_records (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    agency_name           TEXT NOT NULL,
    agency_geographic_scope TEXT,           -- ISO country/region codes per §4.1
    vendor_canonical_name TEXT NOT NULL,    -- ideally matches manufacturers.canonical_name
    product_family        TEXT,
    contract_amount_usd   REAL,
    contract_date         DATE,
    source_url            TEXT NOT NULL,    -- §8.1 provenance is non-negotiable
    source_type           TEXT NOT NULL CHECK (source_type IN ('procurement', 'foia', 'regulatory', 'official')),
    source_excerpt        TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    confidence            INTEGER CHECK (confidence BETWEEN 0 AND 100),
    captured_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    linked_identifier_id  INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
    notes                 TEXT
);

CREATE INDEX IF NOT EXISTS idx_procurement_agency ON procurement_records(agency_name);
CREATE INDEX IF NOT EXISTS idx_procurement_vendor ON procurement_records(vendor_canonical_name);
CREATE INDEX IF NOT EXISTS idx_procurement_linked ON procurement_records(linked_identifier_id);

-- ─── seed: manufacturers (bible §2.1) ──────────────────────────────────────
-- Canonical vendor names sourced from PROJECT_BIBLE.md §2.1. Every row cites
-- the bible itself as `source_url` per §8.1 (provenance non-negotiable).
--
-- Vendor merges/splits applied (documented per bible §7.1 "Document any vendor
-- you split or merge"):
--   * "Motorola Vigilant" + "Motorola APX" + "Motorola V300/V500" → one row
--     `Motorola Solutions` with notes listing product families.
--   * "Harris" (legacy Stingray branding) and "L3Harris" (post-2019 merged
--     entity) kept as TWO rows — different corporate entities own different
--     legacy SKUs; merging would lose audit trail. Aliases cross-reference.
--   * "Magnet GrayKey" → row `Magnet Forensics` (canonical entity), GrayKey
--     listed as product family in notes.
--   * "Clearview-deployed endpoints" → row `Clearview AI` (canonical entity).
--   * "Axis traffic cams" → row `Axis Communications` (canonical entity).
--   * "Digital Receiver Technology DRTBox" → row `Digital Receiver Technology`
--     with DRTBox/DRT noted as aliases.
--   * "Jacobs/Engility variants" → `Jacobs` + `Engility` as separate rows; the
--     2018 acquisition does not retroactively rebrand pre-merger filings.

INSERT OR IGNORE INTO manufacturers (canonical_name, aliases, primary_category, source_url, notes) VALUES
    ('Flock Safety', 'Flock', 'alpr',
     'PROJECT_BIBLE.md#2.1', 'Fixed ALPR cameras (§2.1 #1).'),
    ('Vigilant Solutions', 'Vigilant', 'alpr',
     'PROJECT_BIBLE.md#2.1', 'ALPR network operator (§2.1 #1). Acquired by Motorola but retains brand on legacy gear.'),
    ('Motorola Solutions', 'Motorola, Motorola Vigilant, Motorola APX, Motorola V300, Motorola V500', NULL,
     'PROJECT_BIBLE.md#2.1',
     'Multi-purpose vendor — bible §8.4 says NEVER categorize at OUI level. Product families span ALPR (Vigilant), body cams (V300/V500), police radios (APX 6000/8000/N70).'),
    ('Genetec', NULL, 'alpr',
     'PROJECT_BIBLE.md#2.1', 'ALPR / video management (§2.1 #1).'),
    ('Rekor', NULL, 'alpr',
     'PROJECT_BIBLE.md#2.1', 'ALPR + face_recog (§2.1 #1, #11) — multi-category at vendor level.'),
    ('Avigilon', NULL, 'alpr',
     'PROJECT_BIBLE.md#2.1', 'Camera systems (§2.1 #1). Owned by Motorola Solutions; retains brand.'),
    ('Axis Communications', 'Axis', 'alpr',
     'PROJECT_BIBLE.md#2.1', 'Network cameras incl. traffic cams (§2.1 #1).'),
    ('Harris', 'Harris Corporation', 'imsi_catcher',
     'PROJECT_BIBLE.md#2.1',
     'Legacy IMSI-catcher SKUs StingRay / Hailstorm / Crossbow (§2.1 #2). Pre-2019 merger; see L3Harris for post-merger filings.'),
    ('L3Harris', 'L3Harris Technologies', NULL,
     'PROJECT_BIBLE.md#2.1',
     'Post-2019 merger entity. XL-series police radios (§2.1 #4). Multi-purpose — defense, IMSI, comms.'),
    ('Digital Receiver Technology', 'DRT, DRTBox, DRT Inc.', 'imsi_catcher',
     'PROJECT_BIBLE.md#2.1', 'DRTBox IMSI catcher (§2.1 #2).'),
    ('Septier', NULL, 'imsi_catcher',
     'PROJECT_BIBLE.md#2.1', 'IMSI catcher (§2.1 #2).'),
    ('KeyW', 'KeyW Corporation', 'imsi_catcher',
     'PROJECT_BIBLE.md#2.1', 'IMSI catcher (§2.1 #2).'),
    ('Jacobs', 'Jacobs Engineering', 'imsi_catcher',
     'PROJECT_BIBLE.md#2.1', 'IMSI catcher variants (§2.1 #2). Acquired Engility 2019.'),
    ('Engility', NULL, 'imsi_catcher',
     'PROJECT_BIBLE.md#2.1', 'IMSI catcher variants (§2.1 #2). Pre-2019 acquisition by Jacobs; retained for audit fidelity.'),
    ('Axon', 'TASER International (legacy)', 'body_cam',
     'PROJECT_BIBLE.md#2.1', 'Body 2/3/4 body cameras (§2.1 #3).'),
    ('Reveal', 'Reveal Media', 'body_cam',
     'PROJECT_BIBLE.md#2.1', 'Body cameras (§2.1 #3).'),
    ('WatchGuard', 'WatchGuard Video', 'body_cam',
     'PROJECT_BIBLE.md#2.1', 'Body cameras (§2.1 #3). Acquired by Motorola Solutions.'),
    ('Getac', NULL, 'body_cam',
     'PROJECT_BIBLE.md#2.1', 'Body cameras (§2.1 #3).'),
    ('Kenwood', NULL, 'police_radio',
     'PROJECT_BIBLE.md#2.1', 'VP/NX series radios when used by LE (§2.1 #4).'),
    -- §2.1 #5 — In-vehicle LTE/WiFi routers (added in Correction Pass 3).
    -- primary_category=NULL because the §4.1 device_category enum does not yet
    -- have an `in_vehicle_router` value. Surface as a future enum-extension
    -- decision when Phase 2/3 lands its first router OUI/MAC; until then,
    -- multi-purpose pattern (mirrors Motorola Solutions / L3Harris).
    ('Cradlepoint', 'Cradlepoint Inc., Ericsson Cradlepoint', NULL,
     'PROJECT_BIBLE.md#2.1',
     'In-vehicle LTE/WiFi routers — IBR900-series, R1900-series mobile routers (§2.1 #5). Standard data link in modern patrol cars (laptops, dashcams, body-cam offload). Acquired by Ericsson 2020; brand retained.'),
    ('Sierra Wireless', 'Sierra Wireless AirLink, Semtech Sierra', NULL,
     'PROJECT_BIBLE.md#2.1',
     'In-vehicle LTE/WiFi routers — AirLink GX, RV-series, MG90 mobile routers (§2.1 #5). Direct competitor to Cradlepoint in LE fleet deployments. Acquired by Semtech 2023; AirLink brand retained.'),
    ('DJI', 'Da-Jiang Innovations', 'drone',
     'PROJECT_BIBLE.md#2.1', 'Matrice series in LE configurations (§2.1 #6).'),
    ('Skydio', NULL, 'drone',
     'PROJECT_BIBLE.md#2.1', 'X-series LE drones (§2.1 #6).'),
    ('BRINC', 'BRINC Drones', 'drone',
     'PROJECT_BIBLE.md#2.1', 'LEMUR drone (§2.1 #6).'),
    ('Parrot', NULL, 'drone',
     'PROJECT_BIBLE.md#2.1', 'ANAFI USA (§2.1 #6).'),
    ('SoundThinking', 'ShotSpotter', 'gunshot_detect',
     'PROJECT_BIBLE.md#2.1', 'Acoustic gunshot detection (§2.1 #7). Renamed from ShotSpotter.'),
    ('Hak5', NULL, 'hacking_tool',
     'PROJECT_BIBLE.md#2.1', 'WiFi Pineapple, Bash Bunny, Packet Squirrel (§2.1 #8).'),
    ('Cellebrite', NULL, 'hacking_tool',
     'PROJECT_BIBLE.md#2.1', 'UFED forensics (§2.1 #8).'),
    ('Magnet Forensics', 'Magnet, GrayKey (product)', 'hacking_tool',
     'PROJECT_BIBLE.md#2.1', 'GrayKey forensics tool (§2.1 #8).'),
    ('Berla', NULL, 'hacking_tool',
     'PROJECT_BIBLE.md#2.1', 'iVe vehicle forensics (§2.1 #8).'),
    ('BriefCam', NULL, 'face_recog',
     'PROJECT_BIBLE.md#2.1', 'Video analytics / face_recog (§2.1 #11).'),
    ('Clearview AI', 'Clearview', 'face_recog',
     'PROJECT_BIBLE.md#2.1', 'Face_recog endpoints where detectable (§2.1 #11).'),
    ('Dedrone', NULL, 'drone_detect',
     'PROJECT_BIBLE.md#2.1', 'Drone detection systems — also wireless emitters (§2.1 #12).'),
    ('DroneShield', NULL, 'drone_detect',
     'PROJECT_BIBLE.md#2.1', 'Drone detection systems — also wireless emitters (§2.1 #12).');
