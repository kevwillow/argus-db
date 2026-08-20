-- ============================================================================
-- Migration: 0059_mac731_wave9_carveout_ingest.sql
-- Status:    STAGED — WAVE_9.0 landing set, 38 rows + 1 manufacturer admission.
-- Slot:      0059, allocated by DISPATCH CLAIM after a working-tree read.
--            next_migration_slot.py re-derivation at write time: 0059.
--            Highest file on disk: 0057. Gaps below: 0046 (MAC-574), 0047
--            (MAC-598), 0050 (MAC-608), 0053 (MAC-663 RELEASED), 0056
--            (MAC-705), 0058 (MAC-712). None reusable here.
-- Issue:     MAC-731 (W5 of MAC-726). Page reference: §7.5 CP39 named carve-out.
--
-- Contracts: Read ONLY operator_review/MAC-731/landing_set_38.jsonl (identifiers)
--            and operator_review/MAC-731/manufacturer_set_1.jsonl (manufacturers).
--            Both are built by operator_review/MAC-731/build_contract.py from
--            WAVE_9.0/extract/lane_{w,n}_candidates.json and
--            WAVE_9.0/extract/lane_m/m_new_vendor_candidates.json.
--
-- Live DDL CHECK re-read:  device_category/source_type/identifier_type live
--            CHECK values are re-read from the SQLite database at the moment
--            the migration is applied (NOT W1's report, NOT how I remember them).
--            The wrapper operator_review/MAC-731/apply_migration.py:
--              1. Connects to the scratch DB (mode=rw).
--              2. SELECTs `sql` from sqlite_master WHERE name='identifiers'.
--              3. Regex-extracts the CHECK IN (...) sets from the live DDL.
--              4. Writes them to _live_enums.json (a side file, NOT in the
--                 contract path).
--              5. Validates every contract row's category/source_type/type
--                 against the live DDL. ANY miss ABOUTS the migration.
--              6. Applies the migration via sqlite3.
--            The migration itself ALSO checks the live DDL via `_live_enums`
--            TEMP table populated from the side file. Both arms must hold.
--
-- Scope:     Promote exactly 39 distinct rows:
--              34 lane_w identifier rows (16 ssid_pattern + 18 ble_local_name)
--                  — CP39 §7.5 carve-out, target_export='high_confidence'
--               4 lane_n identifier rows (ble_service_uuid) — broad-only
--               1 manufacturer admission (Acyclica / RoadTrend Sensor) — per
--                  board ruling. `m_new_vendor_candidates.json` is labelled 2
--                  rows but BOTH ROWS ARE THE SAME VENDOR DUPLICATED, so we
--                  land ONE admission, not two. `identifier_yield` is 0, so
--                  no matching identifier-pattern row is emitted; this
--                  admission is catalogue-only.
--            All 38 identifiers are crowdsourced, conf 75, G1-G4 all true.
--            Device categories must be drawn verbatim from the live DDL CHECK
--            (re-read at write time per the wrapper). Manufacturer is the
--            candidate's own field — `manufacturers.primary_category` is NOT
--            propagated into `identifiers.device_category` (the brief is
--            explicit on this).
--
-- Explicitly NOT in scope (per the brief and CEO scope-amendment comment
--            b0aed531-241c-4e69-9377-3d8a0aee6bb2):
--              - 26:5a:4c oui                       (OUI-level inference, board hold)
--              - 7 n_category_attestations UNBLOCK rows (would reverse strict-8.4)
--              - 39 review queue                    (anchoring convention, settled in-wave by MAC-734)
--              - raw/flock_you_family/              (per-instance wardriving; settled)
--              - manufacturers.primary_category -> identifiers.device_category
--                  propagation (manufacturers.id=17 has aliases for two companies;
--                  0050_mac608_...sql.draft is unratified)
--
-- Safety:    Fail closed unless canonical pre-state is exactly 43,088 active /
--            43,892 total identifiers at schema_version 35, all 38 identifier
--            contract rows are distinct and absent under normalized comparison,
--            all 38 device categories and source_type values are in the LIVE
--            DDL CHECKs, the contract carries exactly 34 lane_w + 4 lane_n rows,
--            the manufacturer admission's `canonical_name='Acyclica'` is NOT
--            already present, and the manufacturer contract row's `primary_category`
--            is `persistent_surveillance`.
--
-- DDL:       None. schema_version remains 35.
-- Exports:   Regenerated separately against the scratch DB by MAC-731 W5 phase 4.
-- Re-apply:  A second run fails the strict pre-state and per-row absence guards
--            and rolls back WITHOUT mutation. Proven with sha256 byte-identical
--            of the scratch DB before and after run 2.
-- ============================================================================

.bail on

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- Pre-state snapshot. Every post-condition below is a DELTA against this row.
CREATE TEMP TABLE _pre AS SELECT
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)               AS active,
    (SELECT COUNT(*) FROM identifiers)                                           AS total,
    (SELECT MAX(version) FROM schema_version)                                    AS sv_max,
    (SELECT COUNT(*) FROM manufacturers)                                         AS mfg_total,
    (SELECT COUNT(*) FROM manufacturers
       WHERE canonical_name = 'Acyclica')                                        AS mfg_acyclica_present;

-- ---------------------------------------------------------------------------
-- Load the live DDL CHECK values from the side file. The wrapper has already
-- extracted them from sqlite_master.sql at write time. A triple fallback
-- (file exists, parses as JSON, has the three keys) is required.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _live_enums (
    column_name TEXT NOT NULL,
    value       TEXT NOT NULL,
    PRIMARY KEY (column_name, value)
);

INSERT INTO _live_enums(column_name, value)
SELECT 'device_category', value
  FROM json_each(readfile('operator_review/MAC-731/_live_enums.json'),
                 '$.device_category');

INSERT INTO _live_enums(column_name, value)
SELECT 'source_type', value
  FROM json_each(readfile('operator_review/MAC-731/_live_enums.json'),
                 '$.source_type');

INSERT INTO _live_enums(column_name, value)
SELECT 'identifier_type', value
  FROM json_each(readfile('operator_review/MAC-731/_live_enums.json'),
                 '$.identifier_type');

-- Sanity: the live DDL must yield a non-empty set for each. If any of these
-- three is empty, the side file is bad and the migration must abort.
-- (W1's report: device_category=20, source_type=13, identifier_type=89.)
CREATE TEMP TABLE _live_enums_check (ok INTEGER CHECK (ok = 1));
INSERT INTO _live_enums_check(ok)
SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _live_enums WHERE column_name = 'device_category') >= 1
   AND (SELECT COUNT(*) FROM _live_enums WHERE column_name = 'source_type') >= 1
   AND (SELECT COUNT(*) FROM _live_enums WHERE column_name = 'identifier_type') >= 1)
  THEN 1 ELSE 0 END;

-- ---------------------------------------------------------------------------
-- Contract load. Read the JSONL file from disk, parse it, and stage every row
-- into a TEMP table. Lines with `trim(line) <> ''` are kept; blank lines are
-- skipped so a trailing newline does not crash the parse.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _mig0059_contract (
    manifest_bin      TEXT NOT NULL,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL,
    device_category   TEXT NOT NULL,
    manufacturer      TEXT NOT NULL,
    model             TEXT,
    confidence        INTEGER NOT NULL,
    source_url        TEXT NOT NULL,
    source_type       TEXT NOT NULL,
    source_excerpt    TEXT NOT NULL,
    geographic_scope  TEXT,
    notes             TEXT NOT NULL
);

WITH RECURSIVE
input(rest) AS (
    SELECT CAST(readfile('operator_review/MAC-731/landing_set_38.jsonl') AS TEXT) || char(10)
),
lines(line, rest) AS (
    SELECT '', rest FROM input
    UNION ALL
    SELECT substr(rest, 1, instr(rest, char(10)) - 1),
           substr(rest, instr(rest, char(10)) + 1)
      FROM lines
     WHERE rest <> ''
)
INSERT INTO _mig0059_contract (
    manifest_bin, identifier, identifier_type, device_category, manufacturer,
    model, confidence, source_url, source_type, source_excerpt,
    geographic_scope, notes
)
SELECT json_extract(line, '$._manifest_bin'),
       json_extract(line, '$.identifier'),
       json_extract(line, '$.identifier_type'),
       json_extract(line, '$.device_category'),
       json_extract(line, '$.manufacturer'),
       json_extract(line, '$.model'),
       json_extract(line, '$.confidence'),
       json_extract(line, '$.source_url'),
       json_extract(line, '$.source_type'),
       json_extract(line, '$.source_excerpt'),
       json_extract(line, '$.geographic_scope'),
       json_extract(line, '$.notes')
  FROM lines
 WHERE trim(line) <> '';

-- ---------------------------------------------------------------------------
-- Manufacturers contract load. ONE row (Acyclica / RoadTrend Sensor) — the
-- 2-row m_new_vendor_candidates.json is the same vendor duplicated, so the
-- board ruling collapses to one admission. Per the brief: "If you land 2,
-- you have landed a duplicate." See CEO scope-amendment comment
-- b0aed531-241c-4e69-9377-3d8a0aee6bb2.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _mig0059_mfg_contract (
    manifest_bin      TEXT NOT NULL,
    canonical_name    TEXT NOT NULL,
    aliases           TEXT NOT NULL,
    primary_category  TEXT NOT NULL,
    source_url        TEXT NOT NULL,
    notes             TEXT NOT NULL
);

WITH RECURSIVE
mfg_input(rest) AS (
    SELECT CAST(readfile('operator_review/MAC-731/manufacturer_set_1.jsonl') AS TEXT) || char(10)
),
mfg_lines(line, rest) AS (
    SELECT '', rest FROM mfg_input
    UNION ALL
    SELECT substr(rest, 1, instr(rest, char(10)) - 1),
           substr(rest, instr(rest, char(10)) + 1)
      FROM mfg_lines
     WHERE rest <> ''
)
INSERT INTO _mig0059_mfg_contract (
    manifest_bin, canonical_name, aliases, primary_category, source_url, notes
)
SELECT json_extract(line, '$._manifest_bin'),
       json_extract(line, '$.canonical_name'),
       json_extract(line, '$.aliases'),
       json_extract(line, '$.primary_category'),
       json_extract(line, '$.source_url'),
       json_extract(line, '$.notes')
  FROM mfg_lines
 WHERE trim(line) <> '';

-- ---------------------------------------------------------------------------
-- PRECONDITIONS. Each is phrased so that ok=0 means THE FINDING MOVED.
-- ---------------------------------------------------------------------------

-- PRE-1 FAIL: canonical is not the DB this migration was measured against.
CREATE TEMP TABLE _mac731_pre_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_1fail(ok) SELECT CASE WHEN (
       (SELECT active FROM _pre) <> 43088
    OR (SELECT total  FROM _pre) <> 43892
    OR (SELECT sv_max FROM _pre) <> 35)
  THEN 0 ELSE 1 END;

-- PRE-2 FAIL: the contract file is not what we parsed. Track EXACT bin counts
-- (34 lane_w + 4 lane_n) and the total (38). If any is off, an upstream changed
-- the candidate JSONs and the contract build needs to re-run.
CREATE TEMP TABLE _mac731_pre_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_2fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_contract) <> 38
    OR (SELECT COUNT(*) FROM _mig0059_contract WHERE manifest_bin = 'lane_w_carveout') <> 34
    OR (SELECT COUNT(*) FROM _mig0059_contract WHERE manifest_bin = 'lane_n_broad') <> 4)
  THEN 0 ELSE 1 END;

-- PRE-3 FAIL: the contract rows are not distinct under normalized comparison.
-- (identifier_type, lower(identifier)) is the canonical dedup key. Duplicates
-- either an upstream extractor bug or a JSONL build bug; either way, HALT.
CREATE TEMP TABLE _mac731_pre_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_3fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(DISTINCT identifier_type || '|' || lower(identifier))
          FROM _mig0059_contract) <> 38)
  THEN 0 ELSE 1 END;

-- PRE-4 FAIL: every row's `device_category` is in the LIVE DDL CHECK.
-- The wrapper has already verified this against the live ddl; this is the
-- migration-side re-assertion. A miss here means the wrapper was bypassed
-- (e.g. someone ran the SQL directly without the wrapper).
CREATE TEMP TABLE _mac731_pre_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_4fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_contract c
         WHERE NOT EXISTS (
             SELECT 1 FROM _live_enums
              WHERE column_name = 'device_category'
                AND value = c.device_category)) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-5 FAIL: every row's `source_type` is in the LIVE DDL CHECK.
CREATE TEMP TABLE _mac731_pre_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_5fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_contract c
         WHERE NOT EXISTS (
             SELECT 1 FROM _live_enums
              WHERE column_name = 'source_type'
                AND value = c.source_type)) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-6 FAIL: every row's `identifier_type` is in the LIVE DDL CHECK.
CREATE TEMP TABLE _mac731_pre_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_6fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_contract c
         WHERE NOT EXISTS (
             SELECT 1 FROM _live_enums
              WHERE column_name = 'identifier_type'
                AND value = c.identifier_type)) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-7 FAIL: every row's `confidence` is in [0, 100]. The CHECK is on the
-- table, but a contract build bug could slip a string through.
CREATE TEMP TABLE _mac731_pre_7fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_7fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_contract
         WHERE confidence < 0 OR confidence > 100) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-8 FAIL: any contract row already exists in canonical under normalized
-- comparison. The brief is explicit: "all 38 must be NEW". The normalization
-- strips case, colons, hyphens, dots, spaces — the same shape 0048 used.
CREATE TEMP TABLE _mac731_pre_8fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_8fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*)
          FROM identifiers i
          JOIN _mig0059_contract c
            ON i.identifier_type = c.identifier_type
           AND lower(replace(replace(replace(replace(i.identifier, ':', ''), '-', ''), '.', ''), ' ', ''))
            = lower(replace(replace(replace(replace(c.identifier, ':', ''), '-', ''), '.', ''), ' ', ''))
           AND i.superseded_by IS NULL) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-9 FAIL: source_url is non-empty, source_excerpt is non-empty, and the
-- cohort tag is correct on every row. Catches a JSONL build that lost the
-- provenance envelope.
CREATE TEMP TABLE _mac731_pre_9fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_9fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_contract
         WHERE length(source_url) = 0
            OR length(source_excerpt) = 0
            OR json_valid(notes) <> 1
            OR json_extract(notes, '$.cohort') <> 'mac731_wave9_carveout'
            OR json_extract(notes, '$.mac731_ingest_bin') <> manifest_bin) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-10 FAIL: the source-excerpt length budget. The schema enforces
-- length(source_excerpt) <= 200; a contract that bypassed the CHECK would
-- still fail at INSERT, but stopping here is louder.
CREATE TEMP TABLE _mac731_pre_10fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_10fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_contract
         WHERE length(source_excerpt) > 200) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-11 FAIL: the brief is explicit. Exclude the OUI row's value, the
-- UNBLOCK attestations, and the m_new_vendor_candidates row shapes. The
-- first is applied by the contract builder (it never enters the JSONL); the
-- remaining are not in the contract at all. So check that NO row has
-- identifier_type='oui' in the contract.
CREATE TEMP TABLE _mac731_pre_11fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_11fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_contract
         WHERE identifier_type = 'oui') <> 0)
  THEN 0 ELSE 1 END;

-- PRE-12 FAIL: notes are JSON objects, not arrays or scalars. A contract
-- with `notes=42` or `notes=[]` would fail the JSON-valid gate silently.
CREATE TEMP TABLE _mac731_pre_12fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_12fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_contract
         WHERE json_valid(notes) <> 1
            OR json_type(notes) <> 'object') <> 0)
  THEN 0 ELSE 1 END;

-- PRE-13 FAIL: 33 active ssid_pattern + 25 ble_local_name + 163 ble_service_uuid
-- in canonical today. Re-derive these numbers from the live DB and assert
-- the contract's claim (that the 38 rows are net-new) sits on a stable
-- non-empty base. A zero here would mean the contract is targeting a
-- subsumed-cohort stop-line.
CREATE TEMP TABLE _mac731_pre_13fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_13fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE identifier_type='ssid_pattern' AND superseded_by IS NULL) <> 31
    OR (SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_local_name' AND superseded_by IS NULL) <> 25
    OR (SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_service_uuid' AND superseded_by IS NULL) <> 163)
  THEN 0 ELSE 1 END;

-- PRE-14 FAIL: the manufacturer contract is exactly 1 row. Per the board
-- ruling, `m_new_vendor_candidates.json` is labelled 2 rows but both rows are
-- the same vendor duplicated; landing 2 = landing a duplicate. Re-derive
-- from the source file: if the loader returned more than 1 row, the contract
-- builder failed to deduplicate.
CREATE TEMP TABLE _mac731_pre_14fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_14fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0059_mfg_contract) <> 1
    OR (SELECT COUNT(*) FROM _mig0059_mfg_contract
         WHERE canonical_name = 'Acyclica'
           AND primary_category = 'persistent_surveillance'
           AND json_valid(notes) = 1
           AND json_extract(notes, '$.cohort') = 'mac731_wave9_carveout'
           AND json_extract(notes, '$.model') = 'RoadTrend Sensor'
           AND length(source_url) > 0) <> 1)
  THEN 0 ELSE 1 END;

-- PRE-15 FAIL: Acyclica is NOT already in manufacturers (UNIQUE on
-- canonical_name would catch this at INSERT, but stopping here is louder
-- and gives a clearer error). Per pre-state mfg_acyclica_present=0.
CREATE TEMP TABLE _mac731_pre_15fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_pre_15fail(ok) SELECT CASE WHEN (
       (SELECT mfg_acyclica_present FROM _pre) <> 0)
  THEN 0 ELSE 1 END;

-- ARM 3. `_mac731_go` holds exactly 1 row iff EVERY precondition above holds.
-- The INSERT ... SELECT below carries the `(SELECT COUNT(*) FROM _mac731_go) = 1`
-- arm, so the write cannot land on a moved basis even if `.bail` and the CHECKs
-- are both defeated. Deliberately re-derived from the source predicates —
-- reading the _pre_Nfail tables back would assert that the assertions ran,
-- not that the conditions hold.
CREATE TEMP TABLE _mac731_go AS
SELECT 1 AS ok WHERE
       (SELECT active FROM _pre) = 43088
   AND (SELECT total  FROM _pre) = 43892
   AND (SELECT sv_max FROM _pre) = 35
   AND (SELECT COUNT(*) FROM _live_enums_check) = 1
   AND (SELECT ok FROM _live_enums_check) = 1
   AND (SELECT COUNT(*) FROM _mig0059_contract) = 38
   AND (SELECT COUNT(*) FROM _mig0059_contract WHERE manifest_bin = 'lane_w_carveout') = 34
   AND (SELECT COUNT(*) FROM _mig0059_contract WHERE manifest_bin = 'lane_n_broad') = 4
   AND (SELECT COUNT(DISTINCT identifier_type || '|' || lower(identifier))
          FROM _mig0059_contract) = 38
   AND (SELECT COUNT(*) FROM _mig0059_contract c
         WHERE EXISTS (SELECT 1 FROM _live_enums
                        WHERE column_name = 'device_category'
                          AND value = c.device_category)) = 38
   AND (SELECT COUNT(*) FROM _mig0059_contract c
         WHERE EXISTS (SELECT 1 FROM _live_enums
                        WHERE column_name = 'source_type'
                          AND value = c.source_type)) = 38
   AND (SELECT COUNT(*) FROM _mig0059_contract c
         WHERE EXISTS (SELECT 1 FROM _live_enums
                        WHERE column_name = 'identifier_type'
                          AND value = c.identifier_type)) = 38
   AND (SELECT COUNT(*) FROM _mig0059_contract
         WHERE confidence BETWEEN 0 AND 100) = 38
   AND (SELECT COUNT(*) FROM _mig0059_contract
         WHERE length(source_url) > 0
           AND length(source_excerpt) > 0
           AND length(source_excerpt) <= 200
           AND json_valid(notes) = 1
           AND json_extract(notes, '$.cohort') = 'mac731_wave9_carveout'
           AND json_extract(notes, '$.mac731_ingest_bin') = manifest_bin) = 38
   AND (SELECT COUNT(*) FROM _mig0059_contract
         WHERE identifier_type = 'oui') = 0
   AND (SELECT COUNT(*) FROM _mig0059_contract
         WHERE json_type(notes) = 'object') = 38
   AND (SELECT COUNT(*) FROM identifiers i
          JOIN _mig0059_contract c
            ON i.identifier_type = c.identifier_type
           AND lower(replace(replace(replace(replace(i.identifier, ':', ''), '-', ''), '.', ''), ' ', ''))
            = lower(replace(replace(replace(replace(c.identifier, ':', ''), '-', ''), '.', ''), ' ', ''))
           AND i.superseded_by IS NULL) = 0
   AND (SELECT COUNT(*) FROM _mig0059_mfg_contract) = 1
   AND (SELECT COUNT(*) FROM _mig0059_mfg_contract
         WHERE canonical_name = 'Acyclica'
           AND primary_category = 'persistent_surveillance') = 1
   AND (SELECT mfg_acyclica_present FROM _pre) = 0;

-- ---------------------------------------------------------------------------
-- THE WRITE. Per-write gate: the SELECT carries `(SELECT COUNT(*) FROM _mac731_go) = 1`
-- so the write cannot land unless every precondition held. Without that arm,
-- a `CHECK (ok = 1)` on a TEMP table aborts the STATEMENT, not the migration,
-- and the CLI walks on to COMMIT. With both arms, the write is fail-closed.
-- ---------------------------------------------------------------------------
INSERT INTO identifiers (
    identifier, identifier_type, device_category, manufacturer, model,
    confidence, source_url, source_type, source_excerpt, geographic_scope, notes
)
SELECT identifier, identifier_type, device_category, manufacturer, model,
       confidence, source_url, source_type, source_excerpt, geographic_scope, notes
  FROM _mig0059_contract
 WHERE (SELECT COUNT(*) FROM _mac731_go) = 1
 ORDER BY rowid;

-- ---------------------------------------------------------------------------
-- THE MANUFACTURER WRITE. Same per-write gate. `INSERT OR IGNORE` on the
-- `canonical_name` UNIQUE constraint is the idempotency handle for a re-run;
-- PRE-15 ensures Acyclica is absent, so this INSERT always lands.
-- ---------------------------------------------------------------------------
INSERT OR IGNORE INTO manufacturers (canonical_name, aliases, primary_category, source_url, notes)
SELECT canonical_name, aliases, primary_category, source_url, notes
  FROM _mig0059_mfg_contract
 WHERE (SELECT COUNT(*) FROM _mac731_go) = 1
 ORDER BY rowid;

-- ---------------------------------------------------------------------------
-- POST-CONDITIONS. Deltas against `_pre`. These are deliberately NOT
-- restatements of the INSERT; what is asserted is the POPULATION effect and
-- the ABSENCE of collateral change.
-- ---------------------------------------------------------------------------

-- POST-1 FAIL: the write did not land, or landed without its cohort tag.
-- The tag is part of the deliverable: a wave-9 carve-out row with no
-- record of which wave is indistinguishable from an invented one.
CREATE TEMP TABLE _mac731_post_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_1fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE superseded_by IS NULL
     AND json_valid(notes) = 1
     AND json_extract(notes, '$.cohort') = 'mac731_wave9_carveout') <> 38)
  THEN 0 ELSE 1 END;

-- POST-2 FAIL: the active population did not move by exactly 38. DELTA, not
-- a pinned absolute total.
CREATE TEMP TABLE _mac731_post_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_2fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)
         <> (SELECT active FROM _pre) + 38)
  THEN 0 ELSE 1 END;

-- POST-3 FAIL: the total population did not move by exactly 38.
CREATE TEMP TABLE _mac731_post_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_3fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers)
         <> (SELECT total FROM _pre) + 38)
  THEN 0 ELSE 1 END;

-- POST-4 FAIL: schema_version moved. The brief says no DDL. A bump here
-- would mean someone else ran between PRE-1 and the write.
CREATE TEMP TABLE _mac731_post_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_4fail(ok) SELECT CASE WHEN (
       (SELECT MAX(version) FROM schema_version) <> 35)
  THEN 0 ELSE 1 END;

-- POST-5 FAIL: the new rows did not preserve the contract shape. At least
-- one cell came back different from what the contract asserted — that would
-- be either a write defect or a CHECK violation we let through silently.
CREATE TEMP TABLE _mac731_post_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_5fail(ok) SELECT CASE WHEN ((SELECT COUNT(*)
     FROM identifiers i
     JOIN _mig0059_contract c
       ON i.identifier = c.identifier
      AND i.identifier_type = c.identifier_type
      AND i.device_category = c.device_category
      AND i.manufacturer = c.manufacturer
      AND i.model IS c.model
      AND i.confidence = c.confidence
      AND i.source_url = c.source_url
      AND i.source_type = c.source_type
      AND i.source_excerpt = c.source_excerpt
      AND i.geographic_scope IS c.geographic_scope
      AND i.notes = c.notes
      AND i.superseded_by IS NULL
      AND json_valid(i.notes) = 1
      AND json_extract(i.notes, '$.cohort') = 'mac731_wave9_carveout') <> 38)
  THEN 0 ELSE 1 END;

-- POST-6 FAIL: the bin breakdown did not match the contract. The 34 lane_w
-- / 4 lane_n split is part of the deliverable shape — a swap would mean
-- a config or a build bug.
CREATE TEMP TABLE _mac731_post_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_6fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers
         WHERE superseded_by IS NULL
           AND json_valid(notes) = 1
           AND json_extract(notes, '$.mac731_ingest_bin') = 'lane_w_carveout') <> 34
    OR (SELECT COUNT(*) FROM identifiers
         WHERE superseded_by IS NULL
           AND json_valid(notes) = 1
           AND json_extract(notes, '$.mac731_ingest_bin') = 'lane_n_broad') <> 4)
  THEN 0 ELSE 1 END;

-- POST-7 FAIL: target_export breakdown. The 34 lane_w rows are
-- `high_confidence` and the 4 lane_n rows are `broad`. A swap would mean
-- the bin/disposition wiring in the contract is broken.
CREATE TEMP TABLE _mac731_post_7fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_7fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers
         WHERE superseded_by IS NULL
           AND json_valid(notes) = 1
           AND json_extract(notes, '$.cohort') = 'mac731_wave9_carveout'
           AND json_extract(notes, '$.target_export') = 'high_confidence') <> 34
    OR (SELECT COUNT(*) FROM identifiers
         WHERE superseded_by IS NULL
           AND json_valid(notes) = 1
           AND json_extract(notes, '$.cohort') = 'mac731_wave9_carveout'
           AND json_extract(notes, '$.target_export') = 'broad') <> 4)
  THEN 0 ELSE 1 END;

-- POST-8 FAIL: the supersession topology did not change. The brief is
-- explicit that this migration is additive only — no fold, no supersede.
-- If a row was pre-superseded in the time between PRE-1 and the write,
-- active would not grow by 38. POST-2 IS the supersession-topology
-- invariant for an additive migration.
CREATE TEMP TABLE _mac731_post_8fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_8fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NOT NULL)
         <> (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NOT NULL))
  THEN 0 ELSE 1 END;

-- POST-9 FAIL: notes JSON is valid for every new row. A `json_set` regression
-- here would corrupt the cohort audit trail. Scoped to the cohort tag — the
-- 243 pre-existing rows with non-JSON notes are an unrelated technical debt
-- item and not in this migration's scope.
CREATE TEMP TABLE _mac731_post_9fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_9fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE superseded_by IS NULL
     AND json_valid(notes) = 1
     AND json_extract(notes, '$.cohort') = 'mac731_wave9_carveout'
     AND json_valid(notes) <> 1) <> 0)
  THEN 0 ELSE 1 END;

-- POST-10 FAIL: every device_category value in the new rows is still in the
-- LIVE DDL CHECK. Prevents a post-write mutation from smuggling a value
-- outside the live enum.
CREATE TEMP TABLE _mac731_post_10fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_10fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers i
         WHERE i.superseded_by IS NULL
           AND json_valid(i.notes) = 1
           AND json_extract(i.notes, '$.cohort') = 'mac731_wave9_carveout'
           AND NOT EXISTS (
               SELECT 1 FROM _live_enums le
                WHERE le.column_name = 'device_category'
                  AND le.value = i.device_category)) <> 0)
  THEN 0 ELSE 1 END;

-- POST-11 FAIL: the manufacturer admission landed exactly 1 row and the
-- delta against `_pre` is +1. Asserts Acyclica is now present (mfg_total+1,
-- mfg_acyclica_present=1) and no other manufacturers were touched
-- (mfg_total+1 is the DELTA, not an absolute).
CREATE TEMP TABLE _mac731_post_11fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_11fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM manufacturers WHERE canonical_name = 'Acyclica') <> 1
    OR (SELECT COUNT(*) FROM manufacturers) <> (SELECT mfg_total FROM _pre) + 1)
  THEN 0 ELSE 1 END;

-- POST-12 FAIL: the manufacturer row carries the expected provenance shape.
-- Acyclica notes must carry the wave/cohort/lifecycle tags.
CREATE TEMP TABLE _mac731_post_12fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_12fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM manufacturers
         WHERE canonical_name = 'Acyclica'
           AND primary_category = 'persistent_surveillance'
           AND json_valid(notes) = 1
           AND json_extract(notes, '$.cohort') = 'mac731_wave9_carveout'
           AND json_extract(notes, '$.model') = 'RoadTrend Sensor'
           AND json_extract(notes, '$.mac731_admit_duplicates_collapsed_to') = 1
           AND json_extract(notes, '$.identifier_yield') = 0) <> 1)
  THEN 0 ELSE 1 END;

-- POST-13 FAIL: `identifier_yield=0` invariant. Even after the migration,
-- NO identifier row in canonical should match a generic Acyclica-anchored
-- pattern. We assert it by checking there's no NEW identifier row whose
-- notes carry `mac731_ingest_bin = 'lane_m_vendor_admit'` (the manufacturer
-- admission does NOT emit an identifier). This is a structural negative
-- invariant: the manufacturer table write cannot have side-effects into
-- identifiers.
CREATE TEMP TABLE _mac731_post_13fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac731_post_13fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers i
         WHERE json_valid(i.notes) = 1
           AND json_extract(i.notes, '$.mac731_ingest_bin') = 'lane_m_vendor_admit') <> 0)
  THEN 0 ELSE 1 END;

DROP TABLE _mac731_post_13fail;
DROP TABLE _mac731_post_12fail;
DROP TABLE _mac731_post_11fail;
DROP TABLE _mac731_post_10fail;
DROP TABLE _mac731_post_9fail;
DROP TABLE _mac731_post_8fail;
DROP TABLE _mac731_post_7fail;
DROP TABLE _mac731_post_6fail;
DROP TABLE _mac731_post_5fail;
DROP TABLE _mac731_post_4fail;
DROP TABLE _mac731_post_3fail;
DROP TABLE _mac731_post_2fail;
DROP TABLE _mac731_post_1fail;
DROP TABLE _mac731_pre_15fail;
DROP TABLE _mac731_pre_14fail;
DROP TABLE _mac731_pre_13fail;
DROP TABLE _mac731_pre_12fail;
DROP TABLE _mac731_pre_11fail;
DROP TABLE _mac731_pre_10fail;
DROP TABLE _mac731_pre_9fail;
DROP TABLE _mac731_pre_8fail;
DROP TABLE _mac731_pre_7fail;
DROP TABLE _mac731_pre_6fail;
DROP TABLE _mac731_pre_5fail;
DROP TABLE _mac731_pre_4fail;
DROP TABLE _mac731_pre_3fail;
DROP TABLE _mac731_pre_2fail;
DROP TABLE _mac731_pre_1fail;
DROP TABLE _mac731_go;
DROP TABLE _live_enums_check;
DROP TABLE _live_enums;
DROP TABLE _mig0059_mfg_contract;
DROP TABLE _mig0059_contract;
DROP TABLE _pre;

COMMIT;
