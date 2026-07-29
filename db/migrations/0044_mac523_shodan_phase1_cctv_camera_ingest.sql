-- ============================================================================
-- Migration: 0044_mac523_shodan_phase1_cctv_camera_ingest.sql
-- Status:    STAGED — data-only ingest for MAC-523 Phase 1.
--
-- Purpose:   Promote the 8 CTO-ratified cctv_camera OUI rows from
--            operator_review/MAC-523/ratified_promote.jsonl without re-deriving
--            or modifying any contracted field.
--
-- Safety:    Fail closed unless canonical pre-state is exactly 43,116 active /
--            43,848 total identifiers, schema_version remains 33, all 8 values
--            are absent under hex-normalized comparison across every type and
--            lifecycle state, and the contract contains exactly 8 valid rows.
--
-- Notes:     notes is inserted as the complete JSON object serialized by
--            json_extract(). No text concatenation or merge is performed.
--
-- DDL:       None. schema_version is intentionally unchanged at 33.
-- Exports:   Not regenerated; MAC-530 owns consolidated release regeneration.
-- ============================================================================

BEGIN IMMEDIATE;

CREATE TEMP TABLE _mig0044_contract (
    identifier TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    device_category TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    confidence INTEGER,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_excerpt TEXT,
    geographic_scope TEXT,
    notes TEXT NOT NULL
);

WITH RECURSIVE
input(rest) AS (
    SELECT CAST(readfile('operator_review/MAC-523/ratified_promote.jsonl') AS TEXT) || char(10)
),
lines(line, rest) AS (
    SELECT '', rest FROM input
    UNION ALL
    SELECT substr(rest, 1, instr(rest, char(10)) - 1),
           substr(rest, instr(rest, char(10)) + 1)
      FROM lines
     WHERE rest <> ''
)
INSERT INTO _mig0044_contract (
    identifier, identifier_type, device_category, manufacturer, model,
    confidence, source_url, source_type, source_excerpt, geographic_scope, notes
)
SELECT json_extract(line, '$.identifier'),
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

CREATE TEMP TABLE _mig0044_pre (ok INTEGER CHECK (ok = 1));

INSERT INTO _mig0044_pre(ok)
SELECT CASE WHEN (SELECT COUNT(*) FROM identifiers) = 43848 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL
) = 43116 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_pre(ok)
SELECT CASE WHEN (
    SELECT MAX(version) FROM schema_version
) = 33 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_pre(ok)
SELECT CASE WHEN (SELECT COUNT(*) FROM _mig0044_contract) = 8 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(DISTINCT lower(replace(identifier, ':', '')))
      FROM _mig0044_contract
) = 8 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0044_contract
     WHERE identifier_type = 'oui'
       AND device_category = 'cctv_camera'
       AND confidence = 80
       AND source_type = 'primary_registry'
       AND source_url = 'https://standards-oui.ieee.org/oui/oui.csv'
       AND json_valid(notes) = 1
       AND json_extract(notes, '$.wave') = 'mac523_shodan_phase1'
) = 8 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM identifiers i
      JOIN _mig0044_contract c
        ON lower(replace(replace(replace(replace(i.identifier, ':', ''), '-', ''), '.', ''), ' ', ''))
         = lower(replace(replace(replace(replace(c.identifier, ':', ''), '-', ''), '.', ''), ' ', ''))
) = 0 THEN 1 ELSE 0 END;

INSERT INTO identifiers (
    identifier, identifier_type, device_category, manufacturer, model,
    confidence, source_url, source_type, source_excerpt, geographic_scope, notes
)
SELECT identifier, identifier_type, device_category, manufacturer, model,
       confidence, source_url, source_type, source_excerpt, geographic_scope, notes
  FROM _mig0044_contract
 ORDER BY rowid;

CREATE TEMP TABLE _mig0044_post (ok INTEGER CHECK (ok = 1));

INSERT INTO _mig0044_post(ok)
SELECT CASE WHEN changes() = 8 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_post(ok)
SELECT CASE WHEN (SELECT COUNT(*) FROM identifiers) = 43856 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL
) = 43124 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_post(ok)
SELECT CASE WHEN (
    SELECT MAX(version) FROM schema_version
) = 33 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM identifiers
     WHERE json_valid(notes) = 1
       AND json_extract(notes, '$.wave') = 'mac523_shodan_phase1'
       AND superseded_by IS NULL
) = 8 THEN 1 ELSE 0 END;

INSERT INTO _mig0044_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM identifiers i
      JOIN _mig0044_contract c
        ON i.identifier = c.identifier
       AND i.identifier_type = c.identifier_type
       AND i.device_category = c.device_category
       AND i.manufacturer = c.manufacturer
       AND i.model IS c.model
       AND i.confidence = c.confidence
       AND i.source_url = c.source_url
       AND i.source_type = c.source_type
       AND i.source_excerpt = c.source_excerpt
       AND i.geographic_scope = c.geographic_scope
       AND i.notes = c.notes
       AND i.superseded_by IS NULL
) = 8 THEN 1 ELSE 0 END;

DROP TABLE _mig0044_post;
DROP TABLE _mig0044_pre;
DROP TABLE _mig0044_contract;

COMMIT;
