-- Argus migration 0009 — CP12 schema-sibling (CP13).
--
-- Source of truth: BIBLE_AMENDMENTS.md CP12 (commit `90132fa`, 2026-05-08) +
--   Board ratification at MAC-1 [`9d568fa7`](/MAC/issues/MAC-1#comment-
--   9d568fa7-edc0-4d68-a7dd-fb40d4cd919e) 2026-05-10 HB63 (Path X — single
--   coordinated migration). CEO Step-0 ratification of this dispatch at
--   MAC-54 [`34c908b8`](/MAC/issues/MAC-54#comment-34c908b8-0a66-4a6f-a3a5-
--   4aa6d2bc5470) 2026-05-10.
-- Validator dispatch: MAC-54.
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
--   0009 = manufacturer_app source_type + Wave G identifier_type extensions
--          (CP12 schema-sibling — MAC-54; this migration)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- The change
-- ─────────────────────────────────────────────────────────────────────────────
-- CP12 added `manufacturer_app` to bible §8.2 source_type sub-banding without
-- a sibling schema migration; the `identifiers.source_type` and
-- `sources.source_type` CHECK constraints from 0001_initial.sql still reject
-- the value, blocking Wave G narrow-scope promotion. Board HB63 ratified Path X
-- (single coordinated migration) to land:
--
--   1. `identifiers.source_type` enum  ← add `'manufacturer_app'`
--   2. `sources.source_type` enum      ← add `'manufacturer_app'` (parity)
--   3. `identifiers.identifier_type` enum  ← add three Wave G structural-
--        fidelity values: `'ble_local_name'`, `'ble_characteristic'`,
--        `'product_family_codename'`.
--
-- Schema-only. NO `identifiers` row writes; NO promotion. Promotion of the
-- 21 Wave G narrow-scope candidates is the SUBSEQUENT MAC-55 dispatch.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Rationale per new identifier_type (HANDOFF_TO_VALIDATOR.md
-- android_test/extraction_outputs/wave_g_pre_v1/, §"Headline findings")
-- ─────────────────────────────────────────────────────────────────────────────
--  * `ble_local_name`         — BLE GAP "local name" advertised over scan
--      response (distinct from a service or characteristic UUID). Wave G
--      Penguin pairing-flow surfaced one — the literal string `Penguin`
--      broadcast as the local name; collapsing to `ble_uuid` or
--      `ssid_pattern` would falsify the structural surface.
--  * `ble_characteristic`     — BLE GATT *characteristic* UUID, distinct
--      from a *service* UUID (`ble_service`/`ble_uuid`). The paired
--      service/characteristic UUIDs surfaced in Wave G (HANDOFF lines
--      78–82, 100–104) are structurally distinct surfaces; preserving
--      the distinction is consistent with bible §4.4's DROPPED-class
--      Lynceus contract (analytical-only fidelity).
--  * `product_family_codename` — internal vendor product-family / cohort
--      taxonomy strings (e.g. Flock's `DeviceType` enum values surfaced
--      from the operator app static analysis). Vendor's own product
--      naming inside their own app per §8.2 sub-banding (90–95 band).
--
-- Bible §4.4 Lynceus mapping for the three new types is owned by the
-- subsequent BIBLE_AMENDMENTS.md CP13 entry + bible §4.1/§4.4 amendments
-- landing in this same coordinated commit (all three → DROPPED-class,
-- analytical-only).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Migration mechanics — SQLite table-rebuild pattern
-- ─────────────────────────────────────────────────────────────────────────────
-- SQLite CHECK constraints are table-level and cannot be modified in-place.
-- Standard rebuild recipe (per https://sqlite.org/lang_altertable.html
-- section 7):
--   1. PRAGMA foreign_keys = OFF        — toggled OUTSIDE transaction
--   2. BEGIN
--   3. CREATE TABLE <X>_new (…extended CHECKs…)
--   4. INSERT INTO <X>_new SELECT * FROM <X>     — column order preserved
--   5. DROP TABLE <X>
--   6. ALTER TABLE <X>_new RENAME TO <X>
--   7. recreate all indexes attached to the old <X>
--   8. PRAGMA foreign_key_check          — verify integrity before commit
--   9. COMMIT
--  10. PRAGMA foreign_keys = ON
--
-- Self-referencing FK `identifiers.superseded_by REFERENCES identifiers(id)`
-- survives the rebuild: with `foreign_keys = OFF` the FK is parked during
-- DROP + RENAME; modern SQLite (≥3.25, default `legacy_alter_table = OFF`)
-- updates FK references through the rename. `PRAGMA foreign_key_check` at
-- step 8 asserts every `superseded_by` value still resolves to a live row
-- (id space preserved by the literal `SELECT *` copy).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Idempotency
-- ─────────────────────────────────────────────────────────────────────────────
-- The companion wrapper `db/validation/migration_0009_verify.py` is the
-- idempotency boundary: it short-circuits with a no-op message when
-- `MAX(version) FROM schema_version >= 9`, mirroring the
-- `db/validation/cp7_cp10_v01_cutover.py` (MAC-48) precedent. Direct
-- application of this SQL on a post-migration DB is structurally safe — the
-- rebuild reapplies (same CHECK extensions; same column order; same
-- data), and the `INSERT OR IGNORE` on `schema_version` is a no-op for
-- version 9 — but the wrapper is the canonical path.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 hard-rule discipline (cite verbatim from PROJECT_BIBLE.md
-- bible HEAD `90132fa` lines 626 / 632 / 633 / 636 / 640)
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 #1  no fabrication — every new CHECK enum value cites canon:
--   `manufacturer_app` from CP12 §8.2 + BIBLE_AMENDMENTS.md CP12 entry;
--   `ble_local_name` / `ble_characteristic` / `product_family_codename`
--   from `android_test/extraction_outputs/wave_g_pre_v1/HANDOFF_TO_VALIDATOR.md`
--   §"Headline findings" + board HB63 Path X ratification.
-- §11 #7  provenance / no main-table promotion without provenance —
--   schema-only; zero `identifiers` row writes. The 21 narrow-scope
--   Wave G candidates promote in the subsequent MAC-55 dispatch under
--   the §11 #7 gate.
-- §11 #8  no confidence drift — no `confidence` column writes; no rows
--   touched beyond the column-preserving rebuild copy.
-- §11 #11 amendment-log discipline — coordinated commit pairs this
--   migration with BIBLE_AMENDMENTS.md CP13 entry + PROJECT_BIBLE.md §4.1
--   enum-row updates. The amendment log captures CP12's missed schema-
--   sibling and operationalizes the §11 #11 rule per board HB63.
-- §11 #15 no decompiled vendor source in git index — N/A; schema-only.

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
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
                          'product_family_codename'
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
    superseded_by     INTEGER REFERENCES identifiers(id) ON DELETE SET NULL
);

INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

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

-- ─── sources table rebuild ──────────────────────────────────────────────────
CREATE TABLE sources_new (
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

INSERT INTO sources_new SELECT * FROM sources;

DROP TABLE sources;

ALTER TABLE sources_new RENAME TO sources;

CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);

-- ─── FK integrity assertion ─────────────────────────────────────────────────
-- foreign_key_check returns one row per FK violation (table, rowid, parent,
-- fkid). A clean rebuild returns zero rows. Trigger ABORT-via-RAISE if any
-- row surfaces. Implemented in the wrapper (db/validation/
-- migration_0009_verify.py) because raw SQL has no clean way to fail-fast
-- on a multi-row PRAGMA result; PRAGMA is still emitted here so that
-- direct `executescript()` use exercises the check.
PRAGMA foreign_key_check;

-- ─── version bump ───────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (9, '0009_manufacturer_app_and_identifier_type_extensions');

COMMIT;

PRAGMA foreign_keys = ON;
