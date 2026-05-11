-- Argus schema dump — post-CP14 (migrations 0010-0014 applied)
-- Generated 2026-05-11 by Phase 3 application heartbeat
-- schema_version=14; 154 identifiers rows; 0 behavioral_signatures rows
-- Cumulative identifier_type enum: 27 values
-- Cumulative pair_kind enum: 4 values + NULL
--
-- This file is an AUDIT ARTIFACT only — it is NOT a migration.
-- Reproduce via: python3 -c 'import sqlite3; ... migrations apply 0001-0014'

-- TABLE: behavioral_signatures
CREATE TABLE behavioral_signatures (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identity
    signature_name         TEXT NOT NULL,

    -- Categorical context
    cellular_generation    TEXT CHECK (
                               cellular_generation IS NULL
                               OR cellular_generation IN ('2G','3G','4G','5G_NSA')
                           ),

    -- Structured thresholds (e.g. AIMSICD's RSSI deviation gate, 30s idle
    -- accelerometer gate, or NEA0 null-cipher trigger configuration).
    -- Nullable for qualitative signatures (patterns without numeric thresholds).
    threshold_json         TEXT CHECK (
                               threshold_json IS NULL
                               OR json_valid(threshold_json)
                           ),

    -- Evidence dossier: paper citation, upstream repo SHA, file/line
    -- provenance. Per §11 #1 every row must trace back to a concrete source.
    -- Structured JSON for queryability; example shape:
    --   {"paper_cite": "NDSS 2025 Marlin §4.2",
    --    "repo_sha": "<40-hex>",
    --    "files": [{"path": "src/foo.kt", "lines": [36, 37]}]}
    evidence_json          TEXT CHECK (
                               evidence_json IS NULL
                               OR json_valid(evidence_json)
                           ),

    -- Provenance (FK to sources; same shape as existing tables).
    source_id              INTEGER NOT NULL REFERENCES sources(id)
                                ON DELETE RESTRICT,
    source_file_relative   TEXT,
    source_line            INTEGER,

    -- Confidence — same SAR-7 §7.3 intake-side rules apply.
    confidence             INTEGER CHECK (confidence BETWEEN 0 AND 100),

    -- Device category — REUSES the identifiers.device_category enum
    -- verbatim from migration 0009 (the 12-value canonical enum).
    -- Behavioral signatures inherit the same §11 #13 unknown-category
    -- carveout discipline.
    device_category        TEXT NOT NULL CHECK (device_category IN (
                               'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                               'drone', 'gunshot_detect', 'hacking_tool',
                               'covert_cam', 'gps_tracker', 'face_recog',
                               'drone_detect', 'unknown'
                           )),

    notes                  TEXT,

    -- Audit timestamps
    created_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Dedup: same signature emitted by the same source under the same
    -- cellular_generation is one row, not N. Re-extraction of the same
    -- source repo produces UPSERT-shape behavior in the validator
    -- (DELETE-by-source_id is the existing idempotency pattern; see
    -- db/sources/deflock.py precedent).
    --
    -- Phase-2 self-review §2.4 disposition (2026-05-11): UNIQUE is the
    -- 3-tuple including cellular_generation. The dispatch §1.1 spec was
    -- 2-tuple (signature_name, source_id); Phase 2 verified against the
    -- rayhunter 6α surfacing that staging style is one signature_name
    -- per layer (e.g., "RRC Null Cipher (EEA0) multi-path" is ONE row
    -- folding 5 code paths; "NAS Null Cipher (EMM Security-Mode-Command
    -- EEA0/NEA0)" is a SEPARATE row). 2-tuple suffices today, but the
    -- 3-tuple is forward-proof for staging-style evolution where future
    -- Wave-B/C surfacings may split a multi-cellular_gen signature into
    -- per-gen rows. SQLite UNIQUE treats multiple NULL values as
    -- distinct, which is the desired behavior for multi-gen rows
    -- (cellular_generation=NULL means "applies to multiple gens or N/A";
    -- two such rows with same signature_name + same source_id would be a
    -- legitimate duplication only if signature_name granularity fails,
    -- which it shouldn't).
    UNIQUE (signature_name, source_id, cellular_generation)
);

-- TABLE: conflicts
CREATE TABLE conflicts (
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

-- TABLE: council_minutes_matters
CREATE TABLE council_minutes_matters (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id             INTEGER NOT NULL REFERENCES sources(id),
    extraction_run_id     INTEGER REFERENCES extraction_runs(id) ON DELETE SET NULL,
    -- Idempotency key: f"{legistar_client}:{matter_id}"
    source_row_key        TEXT NOT NULL,

    -- Jurisdiction
    legistar_client       TEXT NOT NULL,            -- e.g. 'chicago', 'sfgov', 'detroit', 'hampton', 'cabq'
    agency_name           TEXT NOT NULL,            -- display, e.g. 'City of Chicago' / 'City and County of San Francisco'
    agency_geographic_scope TEXT,                   -- ISO-shaped 'US-IL' / 'US-CA' / 'US-MI' / 'US-VA' / 'US-NM'

    -- Matter native shape (Legistar fields verbatim)
    matter_id             INTEGER NOT NULL,         -- Legistar MatterId (jurisdiction-scoped)
    matter_guid           TEXT,                     -- Legistar MatterGuid
    matter_file           TEXT,                     -- e.g. 'O2014-5474', '16-0079'
    matter_title          TEXT NOT NULL,            -- PII-redacted at staging time per §11 #3 + SAR-5 Rule 5
    matter_type_name      TEXT,                     -- 'Resolution' / 'Ordinance' / 'Resolution-Budget' / etc.
    matter_body_name      TEXT,                     -- 'City Council' / 'Board of Supervisors' / etc.
    matter_status_name    TEXT NOT NULL,            -- only 'Passed' rows are staged per §11 #1
    matter_intro_date     DATE,
    matter_passed_date    DATE,
    matter_enactment_date DATE,
    matter_cost           TEXT,                     -- raw — Legistar stores as TEXT (e.g. '$1,234,567' or NULL)

    -- Vendor attribution
    matched_vendor_label  TEXT NOT NULL,            -- canonical-label from MAC-8 Group A+B that matched
    vendor_canonical_name TEXT NOT NULL,            -- raw verbatim per MAC-8 Q1 staging-as-raw discipline (echoes matched label since Legistar matters surface vendor in the title itself)

    -- Provenance (§8.1 non-negotiable)
    source_url            TEXT NOT NULL,            -- per-matter Legistar UI URL (https://{client}.legistar.com/LegislationDetail.aspx?ID={matter_id})
    source_type           TEXT NOT NULL CHECK (source_type IN ('procurement', 'foia', 'official')),
    source_excerpt        TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    -- Confidence sub-grading per item (f) — 70/75/80
    confidence            INTEGER NOT NULL CHECK (confidence IN (70, 75, 80)),

    -- Phase-5 link path
    linked_identifier_id  INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,

    captured_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                 TEXT,                     -- JSON: full Legistar matter row, redaction counts, etc.

    UNIQUE (source_id, source_row_key)
);

-- TABLE: deployment_observations
CREATE TABLE deployment_observations (
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

-- TABLE: extraction_runs
CREATE TABLE extraction_runs (
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

-- TABLE: fcc_grantees
CREATE TABLE fcc_grantees (
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

-- TABLE: identifiers
CREATE TABLE "identifiers" (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL CHECK (identifier_type IN (
                          -- Pre-CP13 (0001 initial)
                          'oui', 'mac', 'mac_range', 'bssid',
                          'ssid_exact', 'ssid_pattern',
                          'ble_uuid', 'ble_service',
                          'device_fingerprint',
                          -- CP13 (migration 0009) — Wave G structural fidelity
                          'ble_local_name', 'ble_characteristic',
                          'product_family_codename',
                          -- CP14 (migration 0011) — G-3 BLE SIG manufacturer IDs
                          'ble_manufacturer_id',
                          -- CP14 (migration 0013) — Drone-RID + proprietary
                          -- protocol cluster (13 values from 0013 fold-in)
                          'drone_id_prefix',
                          'icao_24bit_address',
                          'rf_channel',
                          'burst_cadence_ms',
                          'bandwidth_mhz',
                          'device_class_id',
                          'rf_burst_duration',
                          'rf_protocol_constant',
                          'wifi_aware_service_name',
                          'wifi_ie_element_id',
                          'bluetooth_le_pdu_type',
                          'wifi_frame_control_subtype',
                          'wifi_nan_param_signature',
                          -- CP14 (migration 0014 — this migration) — G-10
                          -- surveillance metadata (alpr_model only;
                          -- operator_profile HELD as G-17)
                          'alpr_model'
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
                          'inferred', 'manufacturer_doc',
                          'manufacturer_app'
                      )),
    source_excerpt    TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    geographic_scope  TEXT,
    first_seen        DATETIME,
    last_verified     DATETIME,
    notes             TEXT,
    superseded_by     INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
    paired_identifier_id INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
    pair_kind            TEXT CHECK (
                             pair_kind IS NULL
                             OR pair_kind IN (
                                 'la_bit_flip',
                                 'frdid_sibling',
                                 'vendor_as_container',
                                 'firmware_generation'
                             )
                         )
);

-- TABLE: manufacturers
CREATE TABLE manufacturers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name  TEXT NOT NULL UNIQUE,
    aliases         TEXT,           -- comma-separated alternate names
    primary_category TEXT,          -- best-fit §2.1 category, NULL when multi-purpose
    source_url      TEXT NOT NULL,  -- where the canonical name comes from (bible itself is fine)
    notes           TEXT,
    added_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- TABLE: procurement_records
CREATE TABLE procurement_records (
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

-- TABLE: raw_observations
CREATE TABLE raw_observations (
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
, source_row_key TEXT);

-- TABLE: schema_version
CREATE TABLE schema_version (
    version       INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    applied_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- TABLE: sources
CREATE TABLE "sources" (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL UNIQUE,
    source_type     TEXT NOT NULL CHECK (source_type IN (
                        'official', 'regulatory', 'procurement',
                        'academic', 'foia', 'crowdsourced',
                        'inferred', 'manufacturer_doc',
                        -- CP13 (migration 0009) — CP12 §8.2 schema sibling
                        'manufacturer_app'
                    )),
    tier            INTEGER CHECK (tier IN (1, 2, 3, 4)),  -- bible §5
    last_fetched_at DATETIME,
    last_status     TEXT,    -- e.g. 'ok', 'http_404', 'rate_limited'
    notes           TEXT
);

-- TABLE: wigle_anchor_priority
CREATE TABLE wigle_anchor_priority (
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

-- INDEX: idx_behavioral_signatures_category
CREATE INDEX idx_behavioral_signatures_category
    ON behavioral_signatures(device_category);

-- INDEX: idx_behavioral_signatures_cellular_gen
CREATE INDEX idx_behavioral_signatures_cellular_gen
    ON behavioral_signatures(cellular_generation);

-- INDEX: idx_behavioral_signatures_name
CREATE INDEX idx_behavioral_signatures_name
    ON behavioral_signatures(signature_name);

-- INDEX: idx_conflicts_a
CREATE INDEX idx_conflicts_a ON conflicts(identifier_a_id);

-- INDEX: idx_conflicts_b
CREATE INDEX idx_conflicts_b ON conflicts(identifier_b_id);

-- INDEX: idx_conflicts_unresolved
CREATE INDEX idx_conflicts_unresolved
    ON conflicts(resolved_at) WHERE resolved_at IS NULL;

-- INDEX: idx_council_matters_client
CREATE INDEX idx_council_matters_client
    ON council_minutes_matters (legistar_client);

-- INDEX: idx_council_matters_linked
CREATE INDEX idx_council_matters_linked
    ON council_minutes_matters (linked_identifier_id);

-- INDEX: idx_council_matters_passed
CREATE INDEX idx_council_matters_passed
    ON council_minutes_matters (matter_passed_date);

-- INDEX: idx_council_matters_run
CREATE INDEX idx_council_matters_run
    ON council_minutes_matters (extraction_run_id);

-- INDEX: idx_council_matters_vendor
CREATE INDEX idx_council_matters_vendor
    ON council_minutes_matters (matched_vendor_label);

-- INDEX: idx_deployment_obs_run
CREATE INDEX idx_deployment_obs_run
    ON deployment_observations(extraction_run_id);

-- INDEX: idx_deployment_obs_source
CREATE INDEX idx_deployment_obs_source
    ON deployment_observations(source_id);

-- INDEX: idx_deployment_obs_source_row
CREATE UNIQUE INDEX idx_deployment_obs_source_row
    ON deployment_observations(source_id, source_row_key);

-- INDEX: idx_deployment_obs_state
CREATE INDEX idx_deployment_obs_state
    ON deployment_observations(state);

-- INDEX: idx_deployment_obs_tech
CREATE INDEX idx_deployment_obs_tech
    ON deployment_observations(technology_category);

-- INDEX: idx_deployment_obs_vendor
CREATE INDEX idx_deployment_obs_vendor
    ON deployment_observations(vendor_raw);

-- INDEX: idx_fcc_grantees_country_state
CREATE INDEX idx_fcc_grantees_country_state
    ON fcc_grantees (country, state);

-- INDEX: idx_fcc_grantees_date_received
CREATE INDEX idx_fcc_grantees_date_received
    ON fcc_grantees (date_received);

-- INDEX: idx_fcc_grantees_grantee_code
CREATE INDEX idx_fcc_grantees_grantee_code
    ON fcc_grantees (grantee_code);

-- INDEX: idx_fcc_grantees_grantee_name
CREATE INDEX idx_fcc_grantees_grantee_name
    ON fcc_grantees (grantee_name);

-- INDEX: idx_identifiers_category
CREATE INDEX idx_identifiers_category
    ON identifiers(device_category);

-- INDEX: idx_identifiers_ident_type
CREATE INDEX idx_identifiers_ident_type
    ON identifiers(identifier, identifier_type);

-- INDEX: idx_identifiers_identifier
CREATE INDEX idx_identifiers_identifier
    ON identifiers(identifier);

-- INDEX: idx_identifiers_paired
CREATE INDEX idx_identifiers_paired
    ON identifiers(paired_identifier_id);

-- INDEX: idx_identifiers_superseded
CREATE INDEX idx_identifiers_superseded
    ON identifiers(superseded_by);

-- INDEX: idx_identifiers_type
CREATE INDEX idx_identifiers_type
    ON identifiers(identifier_type);

-- INDEX: idx_manufacturers_name
CREATE INDEX idx_manufacturers_name
    ON manufacturers(canonical_name);

-- INDEX: idx_procurement_agency
CREATE INDEX idx_procurement_agency ON procurement_records(agency_name);

-- INDEX: idx_procurement_linked
CREATE INDEX idx_procurement_linked ON procurement_records(linked_identifier_id);

-- INDEX: idx_procurement_vendor
CREATE INDEX idx_procurement_vendor ON procurement_records(vendor_canonical_name);

-- INDEX: idx_raw_obs_run
CREATE INDEX idx_raw_obs_run ON raw_observations(extraction_run_id);

-- INDEX: idx_raw_obs_source
CREATE INDEX idx_raw_obs_source ON raw_observations(source_id);

-- INDEX: idx_raw_obs_source_row
CREATE UNIQUE INDEX idx_raw_obs_source_row
    ON raw_observations(source_id, source_row_key)
    WHERE source_row_key IS NOT NULL;

-- INDEX: idx_runs_agent
CREATE INDEX idx_runs_agent ON extraction_runs(agent_id);

-- INDEX: idx_runs_source
CREATE INDEX idx_runs_source ON extraction_runs(source_id);

-- INDEX: idx_sources_url
CREATE INDEX idx_sources_url ON sources(url);

-- INDEX: idx_wigle_anchor_priority_method
CREATE INDEX idx_wigle_anchor_priority_method
    ON wigle_anchor_priority (derivation_method);

-- INDEX: idx_wigle_anchor_priority_run
CREATE INDEX idx_wigle_anchor_priority_run
    ON wigle_anchor_priority (extraction_run_id);

-- INDEX: idx_wigle_anchor_priority_state
CREATE INDEX idx_wigle_anchor_priority_state
    ON wigle_anchor_priority (state_or_country);

-- INDEX: idx_wigle_anchor_priority_tier
CREATE INDEX idx_wigle_anchor_priority_tier
    ON wigle_anchor_priority (priority_tier, intra_tier_rank);

-- ─────────────────────────────────────────────────────────────────────────────
-- schema_version table contents (audit reference)
-- ─────────────────────────────────────────────────────────────────────────────
-- v1: 0001_initial
-- v2: 0002_deployment_observations
-- v3: 0003_fcc_grantees
-- v4: 0004_wigle_anchor_priority
-- v5: 0005_council_minutes_matters
-- v6: 0006_raw_observations_source_row_key
-- v7: 0007_motorola_solutions_aliases_rescope
-- v8: 0008_cp7_cp10_v01_cutover
-- v9: 0009_manufacturer_app_and_identifier_type_extensions
-- v10: 0010_behavioral_signatures
-- v11: 0011_ble_manufacturer_id_identifier_type_extension
-- v12: 0012_paired_identifier_id
-- v13: 0013_drone_rid_and_proprietary_protocol_identifier_types_extension
-- v14: 0014_surveillance_metadata_identifier_types_extension
