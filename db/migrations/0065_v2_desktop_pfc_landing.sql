-- ============================================================================
-- Migration: 0065_v2_desktop_pfc_landing.sql
-- Status:    STAGED — v2 honest-increment, 79 product_family_codename INSERTs.
-- Slot:      0065, next_migration_slot.py re-derivation at write time: 0065.
--            Highest file on disk: 0064. Drafts below (0050/0056/0061/0062/0063)
--            bound to other issues, none reusable.
-- Issue:     v2 honest-increment landing (desktop_lane). Runbook:
--            operator_review/v2_honest_increment/RUNBOOK.md
-- Authority: Lands the 79 (identifier, product_family_codename) pairs in
--            operator_review/MAC-v2-0065/contract_0065.jsonl — DJI thermal-drone
--            model codenames (device_category='drone') + Digital Watchdog camera
--            model codenames (device_category='cctv_camera'), extracted from
--            desktop_lane static analysis (registered source id=53, tier 1).
--            product_family_codename is an EXPORT-DROPPED type: these rows enter
--            the DB + CSV + operator watchlist, NOT the JSON feed (verified by
--            regen: feed delta 0). No DDL change; schema_version stays 35.
-- Live DDL CHECK re-read: device_category / identifier_type / source_type live
--            CHECK values are re-read from sqlite_master at apply time by the
--            wrapper operator_review/MAC-v2-0065/apply_migration.py, written to
--            _live_enums.json (side file), and re-asserted here. Both arms hold.
-- Determinism: all inserted values are literals from the contract; first_seen /
--            last_verified are a fixed date literal so a re-apply is byte-identical.
-- Idempotency: PRE-7 fails closed if any contract pair is already active, so a
--            second run is a no-op (proven run1/run2 by the wrapper).
-- ============================================================================

.bail on

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- Pre-state snapshot. Every post-condition is a DELTA against this row.
CREATE TEMP TABLE _pre AS SELECT
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL) AS active,
    (SELECT COUNT(*) FROM identifiers)                             AS total,
    (SELECT MAX(version) FROM schema_version)                      AS sv_max;

-- Live DDL CHECK values from the wrapper-written side file.
CREATE TEMP TABLE _live_enums (
    column_name TEXT NOT NULL, value TEXT NOT NULL,
    PRIMARY KEY (column_name, value)
);
INSERT INTO _live_enums(column_name, value)
SELECT 'device_category', value FROM json_each(
    readfile('operator_review/MAC-v2-0065/_live_enums.json'), '$.device_category');
INSERT INTO _live_enums(column_name, value)
SELECT 'identifier_type', value FROM json_each(
    readfile('operator_review/MAC-v2-0065/_live_enums.json'), '$.identifier_type');
INSERT INTO _live_enums(column_name, value)
SELECT 'source_type', value FROM json_each(
    readfile('operator_review/MAC-v2-0065/_live_enums.json'), '$.source_type');

CREATE TEMP TABLE _live_enums_check (ok INTEGER CHECK (ok = 1));
INSERT INTO _live_enums_check(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _live_enums WHERE column_name='device_category') >= 1
   AND (SELECT COUNT(*) FROM _live_enums WHERE column_name='identifier_type') >= 1
   AND (SELECT COUNT(*) FROM _live_enums WHERE column_name='source_type') >= 1)
  THEN 1 ELSE 0 END;

-- Contract load (recursive line-split of the JSONL).
CREATE TEMP TABLE _c (
    manifest_bin TEXT, identifier TEXT, identifier_type TEXT, device_category TEXT,
    manufacturer TEXT, source_url TEXT, source_type TEXT, source_excerpt TEXT
);
INSERT INTO _c
WITH RECURSIVE
input(rest) AS (
    SELECT CAST(readfile('operator_review/MAC-v2-0065/contract_0065.jsonl') AS TEXT) || char(10)),
lines(line, rest) AS (
    SELECT '', rest FROM input
    UNION ALL
    SELECT substr(rest,1,instr(rest,char(10))-1), substr(rest,instr(rest,char(10))+1)
      FROM lines WHERE rest <> '')
SELECT json_extract(line,'$._manifest_bin'), json_extract(line,'$.identifier'),
       json_extract(line,'$.identifier_type'), json_extract(line,'$.device_category'),
       json_extract(line,'$.manufacturer'), json_extract(line,'$.source_url'),
       json_extract(line,'$.source_type'), json_extract(line,'$.source_excerpt')
  FROM lines WHERE trim(line) <> '';

-- PRECONDITIONS. ok=0 means the finding moved. Each aborts via CHECK(ok=1).
CREATE TEMP TABLE _p1 (ok INTEGER CHECK (ok=1));  -- pre-state DB
INSERT INTO _p1(ok) SELECT CASE WHEN ((SELECT active FROM _pre)=43126
   AND (SELECT total FROM _pre)=43930 AND (SELECT sv_max FROM _pre)=35) THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p2 (ok INTEGER CHECK (ok=1));  -- contract count exact
INSERT INTO _p2(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _c)=79
   AND (SELECT COUNT(*) FROM _c WHERE manifest_bin='v2_0065_desktop_pfc')=79) THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p3 (ok INTEGER CHECK (ok=1));  -- distinct
INSERT INTO _p3(ok) SELECT CASE WHEN (
   (SELECT COUNT(DISTINCT identifier_type||'|'||lower(identifier)) FROM _c)=79) THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p4 (ok INTEGER CHECK (ok=1));  -- device_category valid
INSERT INTO _p4(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _c WHERE NOT EXISTS(
   SELECT 1 FROM _live_enums WHERE column_name='device_category' AND value=_c.device_category))=0)
  THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p5 (ok INTEGER CHECK (ok=1));  -- identifier_type valid
INSERT INTO _p5(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _c WHERE NOT EXISTS(
   SELECT 1 FROM _live_enums WHERE column_name='identifier_type' AND value=_c.identifier_type))=0)
  THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p6 (ok INTEGER CHECK (ok=1));  -- source_type valid
INSERT INTO _p6(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _c WHERE NOT EXISTS(
   SELECT 1 FROM _live_enums WHERE column_name='source_type' AND value=_c.source_type))=0)
  THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p7 (ok INTEGER CHECK (ok=1));  -- NONE already active (idempotency)
INSERT INTO _p7(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _c WHERE EXISTS(
   SELECT 1 FROM identifiers i WHERE i.identifier=_c.identifier
     AND i.identifier_type=_c.identifier_type AND i.superseded_by IS NULL))=0)
  THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p8 (ok INTEGER CHECK (ok=1));  -- envelopes well-formed
INSERT INTO _p8(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _c
   WHERE length(source_url)=0 OR length(source_type)=0 OR length(device_category)=0
      OR length(identifier)=0 OR length(source_excerpt)>200)=0) THEN 1 ELSE 0 END;

-- GO gate: exactly 1 row iff every precondition holds.
CREATE TEMP TABLE _go AS SELECT 1 AS ok WHERE
       (SELECT active FROM _pre)=43126 AND (SELECT total FROM _pre)=43930
   AND (SELECT sv_max FROM _pre)=35
   AND (SELECT ok FROM _live_enums_check)=1
   AND (SELECT COUNT(*) FROM _c)=79
   AND (SELECT COUNT(*) FROM _c WHERE manifest_bin='v2_0065_desktop_pfc')=79
   AND (SELECT COUNT(DISTINCT identifier_type||'|'||lower(identifier)) FROM _c)=79
   AND (SELECT COUNT(*) FROM _c WHERE EXISTS(SELECT 1 FROM _live_enums
         WHERE column_name='device_category' AND value=_c.device_category))=79
   AND (SELECT COUNT(*) FROM _c WHERE EXISTS(SELECT 1 FROM _live_enums
         WHERE column_name='identifier_type' AND value=_c.identifier_type))=79
   AND (SELECT COUNT(*) FROM _c WHERE EXISTS(SELECT 1 FROM _live_enums
         WHERE column_name='source_type' AND value=_c.source_type))=79
   AND (SELECT COUNT(*) FROM _c WHERE EXISTS(SELECT 1 FROM identifiers i
         WHERE i.identifier=_c.identifier AND i.identifier_type=_c.identifier_type
           AND i.superseded_by IS NULL))=0
   AND (SELECT COUNT(*) FROM _c WHERE length(source_url)>0 AND length(source_type)>0
         AND length(device_category)>0 AND length(identifier)>0
         AND length(source_excerpt)<=200)=79;

-- THE WRITE. Gated on _go so it cannot land unless every precondition held.
INSERT INTO identifiers
    (identifier, identifier_type, device_category, manufacturer, confidence,
     source_url, source_type, geographic_scope, source_excerpt, notes,
     first_seen, last_verified)
SELECT c.identifier, c.identifier_type, c.device_category, c.manufacturer, 75,
       c.source_url, c.source_type, NULL, c.source_excerpt,
       json_object('issue','v2-0065','lane','desktop_lane','src_registry_id',53),
       '2026-09-29T00:00:00Z', '2026-09-29T00:00:00Z'
  FROM _c c
 WHERE (SELECT COUNT(*) FROM _go) = 1;

-- POST-conditions: exact deltas. Abort (CHECK) if the write did not land 79.
CREATE TEMP TABLE _post1 (ok INTEGER CHECK (ok=1));
INSERT INTO _post1(ok) SELECT CASE WHEN (
   (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL) = (SELECT active FROM _pre)+79
   AND (SELECT COUNT(*) FROM identifiers) = (SELECT total FROM _pre)+79) THEN 1 ELSE 0 END;

COMMIT;
