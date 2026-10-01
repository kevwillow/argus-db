-- ============================================================================
-- Migration: 0067_v2_ct_hostname_landing.sql
-- Status:    STAGED — v2 honest-increment, 2601 vendor_controlled_hostname INSERTs.
-- Slot:      0067. Applies AFTER 0065+0066 (pre-state anchor = 43,208 / 44,012).
-- Issue:     v2 honest-increment. Runbook: operator_review/v2_honest_increment/RUNBOOK.md
-- Authority: Lands the 2601 (vendor_controlled_hostname, unknown) pairs in
--            operator_review/MAC-v2-0067/contract_0067.jsonl — vendor cloud
--            hostnames observed in Certificate Transparency logs (ct_corroboration
--            lane). vch is an EXPORT-DROPPED type: these enter DB + CSV + operator
--            watchlist ONLY, never the JSON feed (feed delta stays 0). device_category
--            ='unknown' (a hostname alone does not evidence a device class);
--            source_type='primary_registry' (CT is a public append-only log);
--            source_url = per-host crt.sh CT search. PII-shaped hosts excluded
--            (7 dropped); dedup vs canonical active vch.
-- Live DDL CHECK re-read: via wrapper operator_review/MAC-v2-0067/apply_migration.py
--            -> _live_enums.json, re-asserted here. geographic_scope by table CHECK.
-- Determinism: literals from contract; fixed date literals; no DDL; sv stays 35.
--            Idempotent (PRE-7 fails closed on re-apply).
-- ============================================================================

.bail on

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

CREATE TEMP TABLE _pre AS SELECT
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL) AS active,
    (SELECT COUNT(*) FROM identifiers)                             AS total,
    (SELECT MAX(version) FROM schema_version)                      AS sv_max;

CREATE TEMP TABLE _live_enums (
    column_name TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY (column_name, value));
INSERT INTO _live_enums(column_name, value)
SELECT 'device_category', value FROM json_each(
    readfile('operator_review/MAC-v2-0067/_live_enums.json'), '$.device_category');
INSERT INTO _live_enums(column_name, value)
SELECT 'identifier_type', value FROM json_each(
    readfile('operator_review/MAC-v2-0067/_live_enums.json'), '$.identifier_type');
INSERT INTO _live_enums(column_name, value)
SELECT 'source_type', value FROM json_each(
    readfile('operator_review/MAC-v2-0067/_live_enums.json'), '$.source_type');

CREATE TEMP TABLE _live_enums_check (ok INTEGER CHECK (ok = 1));
INSERT INTO _live_enums_check(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _live_enums WHERE column_name='device_category') >= 1
   AND (SELECT COUNT(*) FROM _live_enums WHERE column_name='identifier_type') >= 1
   AND (SELECT COUNT(*) FROM _live_enums WHERE column_name='source_type') >= 1)
  THEN 1 ELSE 0 END;

CREATE TEMP TABLE _c (
    manifest_bin TEXT, identifier TEXT, identifier_type TEXT, device_category TEXT,
    manufacturer TEXT, confidence INTEGER, source_url TEXT, source_type TEXT,
    geographic_scope TEXT, source_excerpt TEXT);
INSERT INTO _c
WITH RECURSIVE
input(rest) AS (SELECT CAST(readfile('operator_review/MAC-v2-0067/contract_0067.jsonl') AS TEXT) || char(10)),
lines(line, rest) AS (
    SELECT '', rest FROM input
    UNION ALL
    SELECT substr(rest,1,instr(rest,char(10))-1), substr(rest,instr(rest,char(10))+1)
      FROM lines WHERE rest <> '')
SELECT json_extract(line,'$._manifest_bin'), json_extract(line,'$.identifier'),
       json_extract(line,'$.identifier_type'), json_extract(line,'$.device_category'),
       json_extract(line,'$.manufacturer'), json_extract(line,'$.confidence'),
       json_extract(line,'$.source_url'), json_extract(line,'$.source_type'),
       json_extract(line,'$.geographic_scope'), json_extract(line,'$.source_excerpt')
  FROM lines WHERE trim(line) <> '';

CREATE TEMP TABLE _p1 (ok INTEGER CHECK (ok=1));  -- pre-state (post-0066)
INSERT INTO _p1(ok) SELECT CASE WHEN ((SELECT active FROM _pre)=43208
   AND (SELECT total FROM _pre)=44012 AND (SELECT sv_max FROM _pre)=35) THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p2 (ok INTEGER CHECK (ok=1));  -- contract count exact
INSERT INTO _p2(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _c)=2601
   AND (SELECT COUNT(*) FROM _c WHERE manifest_bin='v2_0067_ct_vch')=2601) THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p3 (ok INTEGER CHECK (ok=1));  -- distinct
INSERT INTO _p3(ok) SELECT CASE WHEN (
   (SELECT COUNT(DISTINCT identifier_type||'|'||lower(identifier)) FROM _c)=2601) THEN 1 ELSE 0 END;

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
     AND i.identifier_type=_c.identifier_type AND i.superseded_by IS NULL))=0) THEN 1 ELSE 0 END;

CREATE TEMP TABLE _p8 (ok INTEGER CHECK (ok=1));  -- envelopes well-formed
INSERT INTO _p8(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _c
   WHERE length(source_url)=0 OR length(source_type)=0 OR length(device_category)=0
      OR length(identifier)=0 OR confidence IS NULL OR length(source_excerpt)>200)=0)
  THEN 1 ELSE 0 END;

CREATE TEMP TABLE _go AS SELECT 1 AS ok WHERE
       (SELECT active FROM _pre)=43208 AND (SELECT total FROM _pre)=44012
   AND (SELECT sv_max FROM _pre)=35
   AND (SELECT ok FROM _live_enums_check)=1
   AND (SELECT COUNT(*) FROM _c)=2601
   AND (SELECT COUNT(*) FROM _c WHERE manifest_bin='v2_0067_ct_vch')=2601
   AND (SELECT COUNT(DISTINCT identifier_type||'|'||lower(identifier)) FROM _c)=2601
   AND (SELECT COUNT(*) FROM _c WHERE EXISTS(SELECT 1 FROM _live_enums
         WHERE column_name='device_category' AND value=_c.device_category))=2601
   AND (SELECT COUNT(*) FROM _c WHERE EXISTS(SELECT 1 FROM _live_enums
         WHERE column_name='identifier_type' AND value=_c.identifier_type))=2601
   AND (SELECT COUNT(*) FROM _c WHERE EXISTS(SELECT 1 FROM _live_enums
         WHERE column_name='source_type' AND value=_c.source_type))=2601
   AND (SELECT COUNT(*) FROM _c WHERE EXISTS(SELECT 1 FROM identifiers i
         WHERE i.identifier=_c.identifier AND i.identifier_type=_c.identifier_type
           AND i.superseded_by IS NULL))=0
   AND (SELECT COUNT(*) FROM _c WHERE length(source_url)>0 AND length(source_type)>0
         AND length(device_category)>0 AND length(identifier)>0 AND confidence IS NOT NULL
         AND length(source_excerpt)<=200)=2601;

INSERT INTO identifiers
    (identifier, identifier_type, device_category, manufacturer, confidence,
     source_url, source_type, geographic_scope, source_excerpt, notes,
     first_seen, last_verified)
SELECT c.identifier, c.identifier_type, c.device_category, c.manufacturer, c.confidence,
       c.source_url, c.source_type, c.geographic_scope, c.source_excerpt,
       json_object('issue','v2-0067','lane','ct_corroboration','src_registry','ct_log'),
       '2026-09-30T00:00:00Z', '2026-09-30T00:00:00Z'
  FROM _c c
 WHERE (SELECT COUNT(*) FROM _go) = 1;

CREATE TEMP TABLE _post1 (ok INTEGER CHECK (ok=1));
INSERT INTO _post1(ok) SELECT CASE WHEN (
   (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL) = (SELECT active FROM _pre)+2601
   AND (SELECT COUNT(*) FROM identifiers) = (SELECT total FROM _pre)+2601) THEN 1 ELSE 0 END;

COMMIT;
