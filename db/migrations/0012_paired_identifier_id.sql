-- ============================================================================
-- DRAFT MIGRATION — NOT APPLIED — QUEUED FOR CEO RATIFICATION
-- ============================================================================
-- Filename intentionally ends in `.sql.draft` (not `.sql`). CEO promotes to
-- `0012_paired_identifier_id.sql` at Phase 3 application time.
--
-- Migration: 0012_paired_identifier_id
-- Purpose:   Extend `identifiers` with two new columns supporting Wave-A's
--            paired-identifier discipline:
--              1. `paired_identifier_id INTEGER REFERENCES identifiers(id)
--                 ON DELETE SET NULL` — self-FK parallel to existing
--                 `superseded_by`.
--              2. `pair_kind TEXT` — discriminator for the kind of pairing
--                 (la_bit_flip / frdid_sibling / vendor_as_container /
--                 firmware_generation / NULL).
--            Together these structurally model G-4 (LA-bit U/L-flip),
--            G-2 (FRDID sibling annotation), G-1 (Parrot vendor-as-container
--            dual-lens), and G-13.3 (Falcon firmware-generation pairing)
--            without notes-JSON sidecars.
-- Surfaced:  G-4 LA-bit sub-agent draft 2026-05-11 §5; multi-gate enabler
--            also serving G-1 (protocol-container OUI lens), G-2 (FRDID
--            sibling), G-13.3 (Falcon-gen1/gen2 hardware-anchor pairing).
-- Authority: CEO autonomous-run dispatch 2026-05-11 §1.2.
-- Bible:     §11 #11 — schema changes are CEO-only ratification. Draft only.
-- Pattern:   SQLite table-rebuild (PRAGMA foreign_keys OFF / new table /
--            INSERT SELECT / DROP / RENAME / reindex / foreign_key_check /
--            version-bump). Mirrors 0009 verbatim.
-- Risk:      Medium-low. Table rebuild touches every existing identifiers
--            row (column-preserving SELECT * INSERT). Existing
--            `superseded_by` self-FK survives via PRAGMA foreign_keys=OFF
--            during DROP+RENAME (modern SQLite ≥3.25, default
--            legacy_alter_table=OFF, updates FK references through rename).
--            `paired_identifier_id` starts NULL for every existing row;
--            the FK check at step (foreign_key_check) asserts the
--            superseded_by self-FK still resolves.
-- ============================================================================
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Bible §11 hard-rule discipline
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 #1   no fabrication — both columns map to concrete Wave-A findings:
--            G-4 sub-agent draft §3.2 (la_pair notes-JSON form being
--            promoted to first-class column); G-1 dispatch §1.3 (Parrot
--            dual-lens); G-2 gates-queue (FRDID sibling); G-13.3 dispatch
--            §1.3 (Falcon-gen1/gen2 firmware lineage).
-- §11 #7   no main-table promotion without provenance — schema-only; zero
--            row writes. paired_identifier_id values land via subsequent
--            promotion-cycle INSERTs/UPDATEs (Phase 4).
-- §11 #8   no confidence drift — no confidence-column touches.
-- §11 #11  amendment-log discipline — part of CP14 coordinated commit;
--            BIBLE_AMENDMENTS.md CP14 entry references this migration as
--            the structural sibling to the four §8.4 amendments (G-1 / G-4
--            / G-13.3 / G-15).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- pair_kind enum scope (Phase-2 self-review §2.5 disposition codified)
-- ─────────────────────────────────────────────────────────────────────────────
-- Four values + NULL:
--   * 'la_bit_flip'         — G-4. LA OUI ↔ IEEE-assigned sibling pairing
--                             (validator promotes via §8.4 amendment;
--                             pair_kind set at promotion).
--   * 'frdid_sibling'       — G-2. FRDID `6A:5C:35` ↔ ASD-STAN `FA:0B:BC`
--                             cross-IEEE-OUI annotation (both U/L=0).
--   * 'vendor_as_container' — G-1. Parrot OUI dual-lens (product-vendor
--                             + protocol-container) — pair the two rows
--                             so the validator picks lens by use-context.
--   * 'firmware_generation' — G-13.3. Falcon-gen1 (Snapdragon 625) ↔
--                             Falcon-gen2 (Snapdragon 650) chipset-anchor
--                             pairing.
--   * NULL                  — unpaired identifier (the default for every
--                             existing row).
--
-- Static-MAC tracker sub-class (Tile/Chipolo/Pebblebee per Wave-A 3b
-- AirGuard surfacing) is INTENTIONALLY EXCLUDED from pair_kind. Per
-- dispatch §2.5: "do NOT add static_mac_tracker to pair_kind yet — that's
-- a different security architecture, handle via notes-JSON until a third
-- sub-class is needed." Static-MAC tracker is an observation-class
-- distinction (lack of MAC rotation is itself a signature), not a
-- structural pairing across two identifier rows. Different axis.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Forward-compatibility note
-- ─────────────────────────────────────────────────────────────────────────────
-- Existing notes-JSON `la_pair:` form per G-4 amendment §3.3 is forward-
-- compatible. Backfill from notes to column (run after this migration
-- but before Phase 4 promotion-cycle-1):
--   UPDATE identifiers
--      SET paired_identifier_id = CAST(
--             json_extract(notes, '$.la_pair.sibling_id') AS INTEGER),
--          pair_kind = 'la_bit_flip'
--    WHERE notes IS NOT NULL
--      AND json_valid(notes)
--      AND json_extract(notes, '$.la_pair.sibling_id') IS NOT NULL;
-- (Pre-Wave-A this matches zero rows — no la_pair notes have been written
-- yet. Backfill is a no-op in the current state but ratifies the path.)
--
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column list verbatim from 0009 post-rebuild state, extended with the two
-- new columns at the tail (post-superseded_by). Column order preserved for
-- the `INSERT INTO identifiers_new SELECT * FROM identifiers` to map by
-- position; the two new columns default NULL (no SELECT projection
-- needed for them).
CREATE TABLE identifiers_new (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL CHECK (identifier_type IN (
                          'oui', 'mac', 'mac_range', 'bssid',
                          'ssid_exact', 'ssid_pattern',
                          'ble_uuid', 'ble_service',
                          'device_fingerprint',
                          -- CP13 (migration 0009) — Wave G structural fidelity
                          'ble_local_name', 'ble_characteristic',
                          'product_family_codename',
                          -- CP14 (migration 0011) — BLE SIG 16-bit manufacturer IDs
                          -- (G-3 from Wave-A gates queue). Included here because
                          -- 0011 runs immediately before 0012 in the Phase-3
                          -- application sequence; the cumulative enum must
                          -- carry forward through every subsequent identifiers
                          -- table-rebuild.
                          'ble_manufacturer_id'
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
                          -- CP13 (migration 0009) — CP12 §8.2 schema sibling
                          'manufacturer_app'
                      )),
    source_excerpt    TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    geographic_scope  TEXT,
    first_seen        DATETIME,
    last_verified     DATETIME,
    notes             TEXT,
    superseded_by     INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
    -- CP14 (migration 0012) — paired-identifier discipline
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

-- Preserve all existing rows. The two new columns get NULL by default
-- (column-list INSERT names only the old columns; new tail columns
-- receive their CREATE-TABLE-default of NULL).
INSERT INTO identifiers_new (
    id, identifier, identifier_type, device_category,
    manufacturer, model, confidence, source_url, source_type,
    source_excerpt, geographic_scope, first_seen, last_verified,
    notes, superseded_by
)
SELECT
    id, identifier, identifier_type, device_category,
    manufacturer, model, confidence, source_url, source_type,
    source_excerpt, geographic_scope, first_seen, last_verified,
    notes, superseded_by
FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate all indexes (from 0009 + one new for paired_identifier_id) ────
CREATE INDEX IF NOT EXISTS idx_identifiers_identifier
    ON identifiers(identifier);
CREATE INDEX IF NOT EXISTS idx_identifiers_type
    ON identifiers(identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_category
    ON identifiers(device_category);
CREATE INDEX IF NOT EXISTS idx_identifiers_superseded
    ON identifiers(superseded_by);
CREATE INDEX IF NOT EXISTS idx_identifiers_ident_type
    ON identifiers(identifier, identifier_type);
-- CP14 (this migration): index on paired_identifier_id for sibling-resolution
-- lookups in the validator promotion path.
CREATE INDEX IF NOT EXISTS idx_identifiers_paired
    ON identifiers(paired_identifier_id);

-- ─── FK integrity assertion ──────────────────────────────────────────────────
-- foreign_key_check returns one row per FK violation (table, rowid, parent,
-- fkid). Clean rebuild returns zero rows. Both self-FKs (superseded_by +
-- paired_identifier_id) are exercised: superseded_by values must resolve
-- (and paired_identifier_id is all-NULL post-this-migration so trivially
-- passes). The wrapper at db/validation/migration_0012_verify.py is the
-- canonical idempotency boundary (short-circuit on
-- `MAX(version) FROM schema_version >= 12`; mirrors the
-- migration_0009_verify.py precedent).
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (12, '0012_paired_identifier_id');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - raw/wave_a/_bible_amendment_la_bit_draft_2026-05-11.md §5 (column proposal)
-- - raw/wave_a/_ceo_gates_queue_2026-05-11.md G-7 (multi-gate enabler)
-- - db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql
--   (table-rebuild precedent — copy mechanics verbatim)
-- - PROJECT_BIBLE.md §8.4 (FP-prevention discipline; this column lands the
--   structural slot for the §8.4 LA-bit / FRDID / vendor-as-container /
--   firmware-generation pairing rules)
