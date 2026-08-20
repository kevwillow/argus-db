-- ============================================================================
-- Migration: 0060_mac737_strict_8_4_amendment_landing.sql
-- Status:    STAGED — strict-8.4 amendment landing set, 7 row UPDATEs.
-- Slot:      0060, allocated by DISPATCH CLAIM after a working-tree read.
--            next_migration_slot.py re-derivation at write time: 0060.
--            Highest file on disk: 0059 (MAC-731 wave9.0 carveout, UNAPPLIED).
--            Gaps below 0059: 0046, 0047, 0050 (DRAFT), 0053 (RELEASED),
--            0056 (DRAFT), 0058 — all bound to other issues, none reusable
--            here. 0059 reserved for MAC-731's lane_w/lane_n carveout, so
--            this amendment lands at 0060.
-- Issue:     MAC-737 (F1 of MAC-726).
-- Issue pair: MAC-733 (the ADOPTED amendment draft — see §1 below).
-- Reversing:  CP46 HOLD (MAC-419) on Nest OUIs 64:16:66 / 18:b4:30 reversed
--            by interaction f69a79a6 q3=q3a (board ruling). Recorded inline
--            in W7_strict_8.4_amendment_draft.md §11 (this commit) and
--            struck from BIBLE_AMENDMENTS.md:5957, MAC-419's history.
--
-- Authority:  This migration lands the 7 (identifier, identifier_type) pairs
--            enumerated in operator_review/MAC-726/W7_strict_8.4_amendment_draft.md
--            §6 (Manifest of bound rows) under the strict-8.4 amendment
--            ratified by board at interaction f69a79a6 q3=q3a. The amendment
--            authorizes:
--              - device_category: unknown -> (smart_lock | smart_home_hub |
--                                  cctv_camera) per the bound pair
--              - notes.mac731_amend_basis = "MAC-733 amend_first" stamp
--            The amendment does NOT authorize:
--              - any vendor-wide propagation
--              - any alias-based stamping
--              - any other row, any other category
--              - any change to confidence, source_url, source_excerpt
--
-- Contracts:  Read ONLY operator_review/MAC-737/landing_set_7.jsonl. The file
--            is built by THIS commit and is byte-identical to the §6
--            manifest in the amendment draft. Live CHECK enum values are
--            re-read from sqlite_master at write time (NOT from any
--            previous report) and stored at operator_review/MAC-737/_live_enums.json
--            by the wrapper operator_review/MAC-737/apply_migration.py.
--
-- Live DDL CHECK re-read:  device_category/identifier_type live CHECK
--            values are re-read from the SQLite database at the moment the
--            migration is applied (NOT W1's report, NOT how I remember them).
--            The wrapper operator_review/MAC-737/apply_migration.py:
--              1. Connects to the scratch DB (mode=rw).
--              2. SELECTs `sql` from sqlite_master WHERE name='identifiers'.
--              3. Regex-extracts the device_category CHECK IN (...) set from
--                 the live DDL and writes it to _live_enums.json (side file,
--                 NOT in the contract path).
--              4. Validates every contract row's category/identifier_type
--                 against the live DDL. ANY miss aborts the migration.
--              5. Applies the migration via sqlite3.
--            The migration itself ALSO checks the live DDL via the `_live_enums`
--            TEMP table populated from the side file. Both arms must hold.
--
-- Scope:     UPDATE exactly 7 existing live rows (`superseded_by IS NULL`):
--              1. 0000fd3d-0000-1000-8000-00805f9b34fb (ble_uuid)
--                 device_category -> smart_lock
--              2. 0x0969 (ble_manufacturer_id)
--                 device_category -> smart_lock
--              3. 0000fe24-0000-1000-8000-00805f9b34fb (ble_uuid)
--                 device_category -> smart_lock
--              4. 0x01D1 (ble_manufacturer_id)
--                 device_category -> smart_lock
--              5. 00:04:63 (oui)
--                 device_category -> smart_home_hub
--              6. 18:b4:30 (oui)
--                 device_category -> cctv_camera (CP46 HOLD REVERSED)
--              7. 64:16:66 (oui)
--                 device_category -> cctv_camera (CP46 HOLD REVERSED)
--            No row is INSERTed, no row is superseded, no row is deleted.
--            Active row count is UNCHANGED (DELTA = 0).
--            The amendment is pair-bound; no vendor-wide propagation.
--
-- Safety:    Fail closed unless canonical pre-state is exactly:
--              - 7 contract rows are present in canonical under normalized
--                comparison
--              - All 7 carry device_category = 'unknown'
--              - All 7 carry superseded_by IS NULL
--              - No row already has notes.mac731_amend_basis set
--              - All 7 device_category values are in the LIVE DDL CHECK
--              - All 7 source_type / identifier_type values are in the
--                LIVE DDL CHECK
--              - Schema version = 35
--              - All 7 rows match the amendment draft's §6 manifest
--
-- DDL:       None. schema_version remains 35.
-- Exports:   Regenerated separately by MAC-737 W5 phase 4.
-- Re-apply:  A second run fails the pre-state guards (rows no longer
--            device_category='unknown') and rolls back WITHOUT mutation.
--            Proven with sha256 byte-identical of the scratch DB before
--            and after run 2.
-- ============================================================================

.bail on

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- ---------------------------------------------------------------------------
-- Pre-state snapshot. Every post-condition below is a DELTA against this row.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _pre AS SELECT
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)               AS active,
    (SELECT COUNT(*) FROM identifiers)                                           AS total,
    (SELECT MAX(version) FROM schema_version)                                    AS sv_max,
    (SELECT COUNT(*) FROM identifiers
       WHERE superseded_by IS NULL
         AND device_category = 'unknown'
         AND ((identifier = '0000fd3d-0000-1000-8000-00805f9b34fb'
               AND identifier_type = 'ble_uuid')
           OR (identifier = '0x0969'
               AND identifier_type = 'ble_manufacturer_id')
           OR (identifier = '0000fe24-0000-1000-8000-00805f9b34fb'
               AND identifier_type = 'ble_uuid')
           OR (identifier = '0x01D1'
               AND identifier_type = 'ble_manufacturer_id')
           OR (identifier = '00:04:63'
               AND identifier_type = 'oui')
           OR (identifier = '18:b4:30'
               AND identifier_type = 'oui')
           OR (identifier = '64:16:66'
               AND identifier_type = 'oui')))                                      AS seven_unknown,
    (SELECT COUNT(*) FROM identifiers
       WHERE superseded_by IS NULL
         AND json_valid(notes) = 1
         AND json_extract(notes, '$.mac731_amend_basis') = 'MAC-733 amend_first')  AS already_amended;

-- ---------------------------------------------------------------------------
-- Load the live DDL CHECK values from the side file. The wrapper has already
-- extracted them from sqlite_master.sql at write time. A triple fallback
-- (file exists, parses as JSON, has the two keys) is required.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _live_enums (
    column_name TEXT NOT NULL,
    value       TEXT NOT NULL,
    PRIMARY KEY (column_name, value)
);

INSERT INTO _live_enums(column_name, value)
SELECT 'device_category', value
  FROM json_each(readfile('operator_review/MAC-737/_live_enums.json'),
                 '$.device_category');

INSERT INTO _live_enums(column_name, value)
SELECT 'identifier_type', value
  FROM json_each(readfile('operator_review/MAC-737/_live_enums.json'),
                 '$.identifier_type');

-- Sanity: the live DDL must yield a non-empty set for each. If any of these
-- two is empty, the side file is bad and the migration must abort.
CREATE TEMP TABLE _live_enums_check (ok INTEGER CHECK (ok = 1));
INSERT INTO _live_enums_check(ok)
SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _live_enums WHERE column_name = 'device_category') >= 1
   AND (SELECT COUNT(*) FROM _live_enums WHERE column_name = 'identifier_type') >= 1)
  THEN 1 ELSE 0 END;

-- ---------------------------------------------------------------------------
-- Contract load. Read the JSONL file from disk, parse it, and stage every row
-- into a TEMP table. Lines with `trim(line) <> ''` are kept; blank lines are
-- skipped so a trailing newline does not crash the parse.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _mig0060_contract (
    manifest_bin      TEXT NOT NULL,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL,
    device_category   TEXT NOT NULL,
    ha_domain         TEXT NOT NULL,
    ha_source_url     TEXT NOT NULL,
    ha_sha256         TEXT NOT NULL,
    amend_draft       TEXT NOT NULL,
    reversing_auth    TEXT NOT NULL
);

WITH RECURSIVE
input(rest) AS (
    SELECT CAST(readfile('operator_review/MAC-737/landing_set_7.jsonl') AS TEXT) || char(10)
),
lines(line, rest) AS (
    SELECT '', rest FROM input
    UNION ALL
    SELECT substr(rest, 1, instr(rest, char(10)) - 1),
           substr(rest, instr(rest, char(10)) + 1)
      FROM lines
     WHERE rest <> ''
)
INSERT INTO _mig0060_contract (
    manifest_bin, identifier, identifier_type, device_category,
    ha_domain, ha_source_url, ha_sha256, amend_draft, reversing_auth
)
SELECT json_extract(line, '$._manifest_bin'),
       json_extract(line, '$.identifier'),
       json_extract(line, '$.identifier_type'),
       json_extract(line, '$.device_category'),
       json_extract(line, '$.ha_domain'),
       json_extract(line, '$.ha_source_url'),
       json_extract(line, '$.ha_sha256'),
       json_extract(line, '$.amend_draft'),
       json_extract(line, '$.reversing_authority')
  FROM lines
 WHERE trim(line) <> '';

-- ---------------------------------------------------------------------------
-- PRECONDITIONS. Each is phrased so that ok=0 means THE FINDING MOVED.
-- ---------------------------------------------------------------------------

-- PRE-1 FAIL: canonical is not the DB this migration was measured against.
CREATE TEMP TABLE _mac737_pre_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_1fail(ok) SELECT CASE WHEN (
       (SELECT sv_max FROM _pre) <> 35)
  THEN 0 ELSE 1 END;

-- PRE-2 FAIL: the contract file is not what we parsed. Track EXACT count = 7.
CREATE TEMP TABLE _mac737_pre_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_2fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0060_contract) <> 7
    OR (SELECT COUNT(*) FROM _mig0060_contract
         WHERE manifest_bin = 'mac737_strict_8_4_amend') <> 7)
  THEN 0 ELSE 1 END;

-- PRE-3 FAIL: the contract rows are not distinct under normalized comparison.
CREATE TEMP TABLE _mac737_pre_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_3fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(DISTINCT identifier_type || '|' || lower(identifier))
          FROM _mig0060_contract) <> 7)
  THEN 0 ELSE 1 END;

-- PRE-4 FAIL: every row's `device_category` is in the LIVE DDL CHECK.
CREATE TEMP TABLE _mac737_pre_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_4fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0060_contract c
         WHERE NOT EXISTS (
             SELECT 1 FROM _live_enums
              WHERE column_name = 'device_category'
                AND value = c.device_category)) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-5 FAIL: every row's `identifier_type` is in the LIVE DDL CHECK.
CREATE TEMP TABLE _mac737_pre_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_5fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0060_contract c
         WHERE NOT EXISTS (
             SELECT 1 FROM _live_enums
              WHERE column_name = 'identifier_type'
                AND value = c.identifier_type)) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-6 FAIL: all 7 contract rows are present in canonical (active, by id+type).
CREATE TEMP TABLE _mac737_pre_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_6fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*)
          FROM _mig0060_contract c
         WHERE NOT EXISTS (
             SELECT 1 FROM identifiers i
              WHERE i.identifier = c.identifier
                AND i.identifier_type = c.identifier_type
                AND i.superseded_by IS NULL)) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-7 FAIL: all 7 contract rows currently carry device_category='unknown'.
CREATE TEMP TABLE _mac737_pre_7fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_7fail(ok) SELECT CASE WHEN (
       (SELECT seven_unknown FROM _pre) <> 7)
  THEN 0 ELSE 1 END;

-- PRE-8 FAIL: NO row in canonical is already marked amended (idempotency).
-- A second run of this migration would either re-stamp the marker (drift) or
-- mutate already-mutated rows (silent re-write). Both fail closed.
CREATE TEMP TABLE _mac737_pre_8fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_8fail(ok) SELECT CASE WHEN (
       (SELECT already_amended FROM _pre) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-9 FAIL: contract envelopes are well-formed (every required field non-empty).
CREATE TEMP TABLE _mac737_pre_9fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_9fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0060_contract
         WHERE length(ha_source_url) = 0
            OR length(ha_sha256) = 0
            OR length(amend_draft) = 0
            OR length(reversing_auth) = 0) <> 0)
  THEN 0 ELSE 1 END;

-- PRE-10 FAIL: the HA domain must resolve to a row in DOMAIN_CATEGORY. The
-- amendment's source-bound clause requires that the HA `domain` resolves to
-- a row in DOMAIN_CATEGORY (lines 47-67 of build_candidates.py). The
-- contract carries the same domain string. A domain outside the table
-- disqualifies the row.
CREATE TEMP TABLE _mac737_pre_10fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_pre_10fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mig0060_contract c
         WHERE c.ha_domain NOT IN ('axis','reolink','ring','blink','nest',
                                   'dlink','onvif','unifi_discovery',
                                   'august','yale','yalexs_ble','nuki',
                                   'switchbot','keymitt_ble','dormakaba_dkey',
                                   'bosch_alarm','simplisafe','verisure',
                                   'teltonika')) <> 0)
  THEN 0 ELSE 1 END;

-- ARM 3. `_mac737_go` holds exactly 1 row iff EVERY precondition above holds.
CREATE TEMP TABLE _mac737_go AS
SELECT 1 AS ok WHERE
       (SELECT sv_max FROM _pre) = 35
   AND (SELECT COUNT(*) FROM _live_enums_check) = 1
   AND (SELECT ok FROM _live_enums_check) = 1
   AND (SELECT COUNT(*) FROM _mig0060_contract) = 7
   AND (SELECT COUNT(*) FROM _mig0060_contract
         WHERE manifest_bin = 'mac737_strict_8_4_amend') = 7
   AND (SELECT COUNT(DISTINCT identifier_type || '|' || lower(identifier))
          FROM _mig0060_contract) = 7
   AND (SELECT COUNT(*) FROM _mig0060_contract c
         WHERE EXISTS (SELECT 1 FROM _live_enums
                        WHERE column_name = 'device_category'
                          AND value = c.device_category)) = 7
   AND (SELECT COUNT(*) FROM _mig0060_contract c
         WHERE EXISTS (SELECT 1 FROM _live_enums
                        WHERE column_name = 'identifier_type'
                          AND value = c.identifier_type)) = 7
   AND (SELECT COUNT(*) FROM _mig0060_contract c
         WHERE EXISTS (SELECT 1 FROM identifiers i
                        WHERE i.identifier = c.identifier
                          AND i.identifier_type = c.identifier_type
                          AND i.superseded_by IS NULL)) = 7
   AND (SELECT seven_unknown FROM _pre) = 7
   AND (SELECT already_amended FROM _pre) = 0
   AND (SELECT COUNT(*) FROM _mig0060_contract
         WHERE length(ha_source_url) > 0
           AND length(ha_sha256) > 0
           AND length(amend_draft) > 0
           AND length(reversing_auth) > 0) = 7
   AND (SELECT COUNT(*) FROM _mig0060_contract c
         WHERE c.ha_domain IN ('axis','reolink','ring','blink','nest',
                               'dlink','onvif','unifi_discovery',
                               'august','yale','yalexs_ble','nuki',
                               'switchbot','keymitt_ble','dormakaba_dkey',
                               'bosch_alarm','simplisafe','verisure',
                               'teltonika')) = 7;

-- ---------------------------------------------------------------------------
-- THE WRITE. Per-write gate. The UPDATE carries a `(SELECT COUNT(*) FROM
-- _mac737_go) = 1` arm so the write cannot land unless every precondition
-- held. Without that arm, a `CHECK (ok = 1)` on a TEMP table aborts the
-- STATEMENT, not the migration, and the CLI walks on to COMMIT. With both
-- arms, the write is fail-closed.
--
-- UPDATE shapes device_category per the contract and stamps
-- notes.mac731_amend_basis = "MAC-733 amend_first" while preserving the
-- existing notes envelope (json_set if valid, json_object if absent/invalid).
-- ---------------------------------------------------------------------------
UPDATE identifiers
   SET device_category = (
         SELECT c.device_category
           FROM _mig0060_contract c
          WHERE c.identifier = identifiers.identifier
            AND c.identifier_type = identifiers.identifier_type
       ),
       notes = (
         SELECT
           CASE
             WHEN identifiers.notes IS NULL OR identifiers.notes = ''
                  OR json_valid(identifiers.notes) = 0
                  OR json_type(identifiers.notes) <> 'object'
             THEN json_object(
                    'mac731_amend_basis', 'MAC-733 amend_first',
                    'cohort', 'mac737_strict_8_4_amendment',
                    'amend_draft', c.amend_draft,
                    'reversing_authority', c.reversing_auth)
             ELSE json_set(
                    identifiers.notes,
                    '$.mac731_amend_basis', 'MAC-733 amend_first',
                    '$.cohort', 'mac737_strict_8_4_amendment',
                    '$.amend_draft', c.amend_draft,
                    '$.reversing_authority', c.reversing_auth)
           END
           FROM _mig0060_contract c
          WHERE c.identifier = identifiers.identifier
            AND c.identifier_type = identifiers.identifier_type
       )
 WHERE (SELECT COUNT(*) FROM _mac737_go) = 1
   AND EXISTS (
         SELECT 1 FROM _mig0060_contract c
          WHERE c.identifier = identifiers.identifier
            AND c.identifier_type = identifiers.identifier_type
       )
   AND identifiers.superseded_by IS NULL
   AND identifiers.device_category = 'unknown';

-- ---------------------------------------------------------------------------
-- POST-CONDITIONS. Deltas against `_pre`. These are deliberately NOT
-- restatements of the UPDATE; what is asserted is the POPULATION effect
-- and the ABSENCE of collateral change.
-- ---------------------------------------------------------------------------

-- POST-1 FAIL: the schema_version moved. The brief says no DDL. A bump here
-- would mean someone else ran between PRE-1 and the write.
CREATE TEMP TABLE _mac737_post_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_post_1fail(ok) SELECT CASE WHEN (
       (SELECT MAX(version) FROM schema_version) <> 35)
  THEN 0 ELSE 1 END;

-- POST-2 FAIL: active population did not move (DELTA = 0 for an UPDATE-only
-- migration). A bump here would mean an INSERT or supersession that the brief
-- forbids.
CREATE TEMP TABLE _mac737_post_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_post_2fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)
         <> (SELECT active FROM _pre))
  THEN 0 ELSE 1 END;

-- POST-3 FAIL: total population did not move.
CREATE TEMP TABLE _mac737_post_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_post_3fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers)
         <> (SELECT total FROM _pre))
  THEN 0 ELSE 1 END;

-- POST-4 FAIL: ALL 7 rows now carry a non-'unknown' device_category, exactly
-- the category in the contract, and the marker stamp. This is the load-bearing
-- post-condition: the amendment authorizes exactly these 7 assignments.
CREATE TEMP TABLE _mac737_post_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_post_4fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers i
         JOIN _mig0060_contract c
           ON i.identifier = c.identifier
          AND i.identifier_type = c.identifier_type
        WHERE i.superseded_by IS NULL
          AND i.device_category = c.device_category
          AND json_valid(i.notes) = 1
          AND json_extract(i.notes, '$.mac731_amend_basis') = 'MAC-733 amend_first') <> 7)
  THEN 0 ELSE 1 END;

-- POST-5 FAIL: the amendment is pair-bound. A row carrying the marker must
-- be in the contract. Any row with the marker stamp that is NOT in the 7
-- is a defect.
CREATE TEMP TABLE _mac737_post_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_post_5fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers i
         WHERE i.superseded_by IS NULL
           AND json_valid(i.notes) = 1
           AND json_extract(i.notes, '$.mac731_amend_basis') = 'MAC-733 amend_first'
           AND NOT EXISTS (
               SELECT 1 FROM _mig0060_contract c
                WHERE c.identifier = i.identifier
                  AND c.identifier_type = i.identifier_type)) <> 0)
  THEN 0 ELSE 1 END;

-- POST-6 FAIL: every device_category value in the 7 mutated rows is still in
-- the LIVE DDL CHECK. Prevents a post-write mutation from smuggling a value
-- outside the live enum.
CREATE TEMP TABLE _mac737_post_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_post_6fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers i
         JOIN _mig0060_contract c
           ON i.identifier = c.identifier
          AND i.identifier_type = c.identifier_type
        WHERE i.superseded_by IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM _live_enums le
               WHERE le.column_name = 'device_category'
                 AND le.value = i.device_category)) <> 0)
  THEN 0 ELSE 1 END;

-- POST-7 FAIL: confidence, source_url, source_type, source_excerpt, manufacturer
-- were preserved on every mutated row. The amendment authorizes only
-- device_category and notes.mac731_amend_basis; nothing else changes.
CREATE TEMP TABLE _mac737_post_7fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_post_7fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers i
         WHERE i.superseded_by IS NULL
           AND json_valid(i.notes) = 1
           AND json_extract(i.notes, '$.mac731_amend_basis') = 'MAC-733 amend_first'
           AND (i.confidence IS NULL
                OR i.source_url IS NULL OR length(i.source_url) = 0
                OR i.source_type IS NULL OR length(i.source_type) = 0
                OR i.source_excerpt IS NULL OR length(i.source_excerpt) = 0
                OR i.manufacturer IS NULL OR length(i.manufacturer) = 0)) <> 0)
  THEN 0 ELSE 1 END;

-- POST-8 FAIL: supersession topology did not change. The brief is explicit
-- that this migration is UPDATE-only — no fold, no supersede.
CREATE TEMP TABLE _mac737_post_8fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac737_post_8fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NOT NULL)
         <> (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NOT NULL))
  THEN 0 ELSE 1 END;

DROP TABLE _mac737_post_8fail;
DROP TABLE _mac737_post_7fail;
DROP TABLE _mac737_post_6fail;
DROP TABLE _mac737_post_5fail;
DROP TABLE _mac737_post_4fail;
DROP TABLE _mac737_post_3fail;
DROP TABLE _mac737_post_2fail;
DROP TABLE _mac737_post_1fail;
DROP TABLE _mac737_pre_10fail;
DROP TABLE _mac737_pre_9fail;
DROP TABLE _mac737_pre_8fail;
DROP TABLE _mac737_pre_7fail;
DROP TABLE _mac737_pre_6fail;
DROP TABLE _mac737_pre_5fail;
DROP TABLE _mac737_pre_4fail;
DROP TABLE _mac737_pre_3fail;
DROP TABLE _mac737_pre_2fail;
DROP TABLE _mac737_pre_1fail;
DROP TABLE _mac737_go;
DROP TABLE _live_enums_check;
DROP TABLE _live_enums;
DROP TABLE _mig0060_contract;
DROP TABLE _pre;

COMMIT;