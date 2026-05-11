-- ============================================================================
-- DRAFT MIGRATION — NOT APPLIED — QUEUED FOR CEO RATIFICATION
-- ============================================================================
-- Filename intentionally ends in `.sql.draft` (not `.sql`) so the active
-- migration runner does NOT pick it up. CEO promotes to `0010_behavioral_signatures.sql`
-- at ratification time (Phase 3 of the Wave-A ratification run).
--
-- Migration: 0010_behavioral_signatures
-- Purpose:   New TABLE `behavioral_signatures` to land the 42 Wave-A staged
--            behavioral_signatures (cellular protocol anomalies, BLE
--            advertising-pattern shapes, RF-burst cadences, etc.) that
--            cannot be modelled cleanly as `identifiers` rows (which key on
--            an identifier *value*; behavioral signatures key on a
--            *pattern*).
-- Surfaced:  Wave-A Phases 6α (EFForg/rayhunter cellular anomalies),
--            6γ (AIMSICD detector thresholds), 4d (RUB-SysSec DroneSecurity
--            CRC/seed constants), 4e (proto17/dji_droneid RF cadences),
--            6δ (GainSec white paper threshold/cadence catalog), 6β (NDSS
--            2025 Marlin research_lead — pending Wave-B second-source).
--            42 signatures staged total; all HELD from promotion this cycle
--            (single-source per §8.3 — wait Wave-B second source).
-- Authority: CEO autonomous-run dispatch 2026-05-11 §1.1 (Wave-A
--            ratification run, MAC-58 §5 Option B board decision
--            2026-05-09 "new table, not identifiers row overload").
-- Bible:     §11 #11 — schema changes are CEO-only ratification. This draft
--            is a proposal, not an application.
-- Pattern:   Standard CREATE TABLE (no rebuild — new table, no existing
--            row-copy). Mirrors `manufacturers` + `procurement_records`
--            structural shape. FK `source_id → sources(id)` cascades on
--            source deletion in the same way `identifiers.source_url`
--            ties to source provenance.
-- Risk:      Low. New table; no impact on existing rows or queries.
--            Promotion of staged behavioral_signature rows happens in a
--            SUBSEQUENT cycle (Wave-B second-source corroboration gate);
--            this migration only opens the structural slot.
-- ============================================================================
--
-- Migration-slot allocation chain of record (updated for Wave-A CP14):
--   0001 = initial schema (Phase 1)
--   0002 = deployment_observations (Phase 2 — DeFlock / EFF Atlas)
--   0003 = fcc_grantees (Phase 3 — MAC-7)
--   0004 = wigle_anchor_priority (Phase 3 — MAC-9)
--   0005 = council_minutes_matters (Phase 3 — MAC-11)
--   0006 = raw_observations source_row_key (Phase 4 — MAC-12/15)
--   0007 = Motorola Solutions aliases re-scope (SAR-9 #1 — MAC-44)
--   0008 = CP7 + CP10 v0.1 cutover (data-layer prep — MAC-48)
--   0009 = manufacturer_app source_type + Wave G identifier_type extensions
--          (CP13 — MAC-54)
--   0010 = behavioral_signatures table (CP14 — this migration; G-? gate)
--   0011 = ble_manufacturer_id identifier_type extension (CP14 — G-3)
--   0012 = paired_identifier_id column on identifiers (CP14 — G-7)
--   0013 = drone-RID identifier_types + RF-behavioral types (CP14 — G-9 +
--          §2 fold-in: device_class_id, rf_burst_duration,
--          rf_protocol_constant, wifi_aware_service_name,
--          wifi_ie_element_id, bluetooth_le_pdu_type,
--          wifi_frame_control_subtype, wifi_nan_param_signature)
--   0014 = surveillance-metadata identifier_types (CP14 — G-10
--          alpr_model + product_family_codename ONLY; operator_profile
--          HELD as new gate per dispatch §3.1.5)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Bible §11 hard-rule discipline
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 #1  no fabrication — every column maps to concrete Wave-A finding:
--           signature_name + threshold_json: AIMSICD `RiskLevelEvaluator.kt`
--             threshold constants (6γ); rayhunter NEA0/RRC patterns (6α);
--           cellular_generation: rayhunter LTE r12/r15 + 2G/3G coverage;
--           evidence_json: paper cite (Marlin / NDSS), repo SHA, file:line
--             provenance per §11 #1 mandate;
--           source_file_relative + source_line: from Wave-A surfacing JSON
--             rows; carries forward the §7.2 audit-trail invariant.
-- §11 #7  no main-table promotion without provenance — `behavioral_signatures`
--           is a separate table from `identifiers`; same provenance
--           discipline applies (every row has source_id FK + source_file_relative
--           + source_line).
-- §11 #8  no confidence drift — confidence column gated 0–100 with the
--           same SAR-7 §7.3 intake-side discipline as `identifiers`.
-- §11 #11 amendment-log discipline — this migration is part of CP14
--           coordinated commit batch; landing pairs with BIBLE_AMENDMENTS.md
--           CP14 entry citing MAC-58 §5 Option B board decision.
-- §11 #13 unknown-category Lynceus carveout — `device_category='unknown'`
--           rows are analytical-only, never exported (same CHECK + same
--           validator-side discipline as `identifiers`).
--
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

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

-- ─── Indexes ─────────────────────────────────────────────────────────────────
-- Same index density pattern as identifiers — name + categorical + cardinal.
CREATE INDEX IF NOT EXISTS idx_behavioral_signatures_name
    ON behavioral_signatures(signature_name);
CREATE INDEX IF NOT EXISTS idx_behavioral_signatures_category
    ON behavioral_signatures(device_category);
CREATE INDEX IF NOT EXISTS idx_behavioral_signatures_cellular_gen
    ON behavioral_signatures(cellular_generation);

-- ─── FK integrity assertion ──────────────────────────────────────────────────
-- New table (no existing rows to violate FKs), but PRAGMA still emitted so
-- direct `executescript()` use exercises the check.
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (10, '0010_behavioral_signatures');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Notes for CEO review (Phase-2 self-review resolved §2.4 forward-proofing question)
-- ─────────────────────────────────────────────────────────────────────────────
-- 1. UNIQUE-constraint shape RESOLVED 2026-05-11 Phase 2: 3-tuple
--    (signature_name, source_id, cellular_generation). Phase 2 verified
--    that rayhunter 6α staging uses per-layer signature_names (RRC and
--    NAS are SEPARATE signature_name values, not one collapsed name with
--    cellular_generation differentiating), so the 2-tuple would actually
--    suffice today. The 3-tuple is forward-proofing for future staging
--    style evolution. See raw/wave_a/_phase2_self_review_2026-05-11.md
--    §2.4 for the full reasoning.
--
-- 2. Forward expectation: Wave-B (NDSS 2025 Marlin paper + Rayhunter PCAPs)
--    will provide second-source corroboration for many of the 42 staged
--    signatures, lifting them through the §8.3 single-source promotion gate.
--    No schema change expected at Wave-B close.
--
-- 3. Cross-references:
--    - MAC-58 §5 Option B board decision (2026-05-09): "behavioral signatures
--      live in a new table, not as overloaded identifier-type rows on
--      identifiers."
--    - Wave-A `_phase4_aggregation_2026-05-11.md` (4d/4e RF-behavioral
--      catalogs)
--    - Wave-A `_phase6_aggregation_2026-05-11.md` (6α/6γ/6δ cellular +
--      cellular-detector catalogs)
--    - raw/wave_a/_ceo_gates_queue_2026-05-11.md (G-? — implicit; this
--      migration closes the structural slot the gates queue assumed open).
