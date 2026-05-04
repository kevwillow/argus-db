-- Argus migration 0005: council_minutes_matters staging table.
--
-- Source of truth: PROJECT_BIBLE.md §6 Phase 3 (Tier 2) + §4.2 supporting-
-- table convention + §4.5 procurement-only carveout + §11 #14 (no Talos
-- export). Ratified at MAC-11 Step 1 by CEO (comment `bbb58e70`,
-- 2026-05-04T18:56Z; migration-slot correction `633421cc`, 2026-05-04T19:01Z).
-- Worker DDL sketch + ratification clauses combined here.
--
-- ─────────────────────────────────────────────────────────────────────────
-- Table scope (CEO-ratified items (a)-(g) at MAC-11 Step 1)
-- ─────────────────────────────────────────────────────────────────────────
-- Schema-fit — option (ii): new staging table over option (i) extending
--   `procurement_records`. Pattern-fit precedent: CP1 `procurement_records`,
--   CP4 `deployment_observations`, CP6 `fcc_grantees`, MAC-9 `wigle_anchor_priority`
--   — separate staging table per source-or-source-class with distinct
--   lifecycle. CEO rationale (verbatim from `bbb58e70` item 6): matter-
--   shape columns (matter_file / matter_type_name / matter_body_name /
--   matter_status_name / matter_passed_date / matter_cost / matched_vendor_label)
--   are load-bearing for confidence subdivision and matter-vs-procurement
--   disambiguation; do not fit cleanly as nullable extensions to
--   `procurement_records`.
--
-- Migration-slot allocation chain of record (per CEO comment `633421cc`):
--   0004 = MAC-9 wigle_anchor_priority (committed in `2b094d0`)
--   0005 = MAC-11 council_minutes_matters (this migration)
--   0006 = DBArchitect device_category CHECK extension (deferred standing
--          recall, queued for Phase 4/5 per `PROJECT_STATE.md`)
-- Schema-version bump 4 -> 5.
--
-- Item (b) vendor-search shape: 24-vendor MAC-8 Group A + Group B canonical
--   labels per SAR-5 Rule 3. Per-vendor HTTP call (NOT OR-combined) —
--   `matched_vendor_label` carries the matched canonical label per row;
--   `vendor_canonical_name` carries Recipient/Matter raw vendor text per
--   MAC-8 Q1 staging-as-raw discipline. Word-boundary `\b{label}\b`
--   case-insensitive post-filter applied client-side after OData
--   `substringof()` server-side query (mirrors MAC-5/MAC-6/MAC-8 codified
--   discipline; bare-`Flock` would hit "Christian Fellowship Flock" /
--   "Wild Parrots ... flock" false positives, so canonical-label is
--   load-bearing).
--
-- Item (e) confidence sub-grading (CHECK enforced):
--   80 = passed Resolution + named vendor + numeric MatterCost
--   75 = passed Resolution + named vendor without cost
--   70 = authorize-negotiations-only matters
--   Failed/Withdrawn/mention-only NOT staged per §11 #1 (insert-side filter
--   on MatterStatusName='Passed' enforced in Python at staging time).
--   Below MAC-8 USAspending top-of-band (85) per worker rationale (council
--   attestation < executed contract).
--
-- Item (g) source_type='procurement' per MAC-4 precedent (existing §4.1
--   enum value; §8.2 procurement band 70-85 fits; new value rejected).
--
-- ─────────────────────────────────────────────────────────────────────────
-- Idempotency
-- ─────────────────────────────────────────────────────────────────────────
-- * Every CREATE uses IF NOT EXISTS.
-- * UNIQUE(source_id, source_row_key) enforces one row per (jurisdiction
--   x matter) across re-runs. `source_row_key=f"{client}:{matter_id}"`
--   per CEO ratification. Build path uses delete-by-source_id +
--   bulk-insert pattern from MAC-3 / MAC-4 / MAC-5 / MAC-6 / MAC-7 / MAC-8;
--   the unique index is the structural backstop.
--
-- ─────────────────────────────────────────────────────────────────────────
-- Identifier columns deliberately absent (§4.2 + §11 #1 + §11 #7 + §11 #14)
-- ─────────────────────────────────────────────────────────────────────────
-- This table does NOT carry MAC/OUI/BSSID/SSID/UUID. Council-resolution
-- attestations are vendor-purchase authorizations without per-device
-- identifiers (mirrors `procurement_records` shape). Phase-5 reconcile
-- attaches `linked_identifier_id` if a downstream source surfaces a
-- concrete identifier for the same vendor-jurisdiction-matter triple.
-- Per §11 #14: NEVER exported to Talos (analytical only).
--
-- ─────────────────────────────────────────────────────────────────────────
-- PII redaction (§11 #3 + SAR-5 Rule 5 + board ratification `7e827dca`)
-- ─────────────────────────────────────────────────────────────────────────
-- * `matter_title` is staged WITH PII redaction applied (default-redact
--   per board ratification "stands as written, no amendment, sub-clause:
--   any human name in council-minutes context = redact-by-default
--   regardless of role; ambiguous → CEO; better to over-redact than to
--   leak"). Redaction happens at staging time via the three-regex stack
--   (rank-token / title-prefix / public-comment-attribution); replacement
--   token `[REDACTED PII]`.
-- * Raw un-redacted artifacts preserved under
--   `raw/council_minutes/<UTC-ts>/legistar/<client>/matters_<slug>.json`
--   per §7.2 audit trail. Never exported per §11 #14.
-- * Redaction counts + sanitized site descriptors logged in
--   `extraction_runs.notes.pii_redaction_counts` and
--   `extraction_runs.notes.ambiguous_pii_samples[]`. Never raw redacted
--   strings.

PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO schema_version (version, name)
    VALUES (5, '0005_council_minutes_matters');

CREATE TABLE IF NOT EXISTS council_minutes_matters (
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

CREATE INDEX IF NOT EXISTS idx_council_matters_client
    ON council_minutes_matters (legistar_client);
CREATE INDEX IF NOT EXISTS idx_council_matters_vendor
    ON council_minutes_matters (matched_vendor_label);
CREATE INDEX IF NOT EXISTS idx_council_matters_passed
    ON council_minutes_matters (matter_passed_date);
CREATE INDEX IF NOT EXISTS idx_council_matters_run
    ON council_minutes_matters (extraction_run_id);
CREATE INDEX IF NOT EXISTS idx_council_matters_linked
    ON council_minutes_matters (linked_identifier_id);
