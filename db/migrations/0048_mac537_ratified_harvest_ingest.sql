-- ============================================================================
-- Migration: 0048_mac537_ratified_harvest_ingest.sql
-- Status:    STAGED — data-only ingest for MAC-614 / MAC-537.
-- Slot:      0048, reserved by MAC-537 and explicitly authorized by the CEO.
--
-- Contract:  Read ONLY operator_review/MAC-537/ingest_manifest/
--            ratified_ingest_36.jsonl. The three source bins are deliberately
--            not read because pending_category_adjudication.jsonl is stale.
--
-- Scope:     Promote exactly 36 distinct, net-new OUI rows:
--              3 ratify_feed_reaching
--             25 hold_unknown
--              8 pending_category_adjudication, ratified to unknown by MAC-558
--            Device categories must be exactly unknown=33, alpr=2,
--            cctv_camera=1. Manufacturer is the IEEE registrant verbatim;
--            brand and lineage remain in notes.
--
-- Safety:    Fail closed unless canonical pre-state is exactly 43,124 active /
--            43,856 total identifiers at schema_version 35, all contract rows
--            are distinct and absent under normalized identifier comparison,
--            all notes are JSON objects, and all ratified field invariants hold.
--
-- DDL:       None. schema_version remains 35.
-- Exports:   Not regenerated; MAC-530 owns consolidated release regeneration.
-- Re-apply:  A second run fails the strict pre-state and collision guards and
--            rolls back without mutation.
-- ============================================================================

BEGIN IMMEDIATE;

CREATE TEMP TABLE _mig0048_contract (
    manifest_bin TEXT NOT NULL,
    identifier TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    device_category TEXT NOT NULL,
    manufacturer TEXT NOT NULL,
    model TEXT,
    confidence INTEGER NOT NULL,
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_excerpt TEXT NOT NULL,
    geographic_scope TEXT NOT NULL,
    notes TEXT NOT NULL
);

WITH RECURSIVE
input(rest) AS (
    SELECT CAST(readfile('operator_review/MAC-537/ingest_manifest/ratified_ingest_36.jsonl') AS TEXT) || char(10)
),
lines(line, rest) AS (
    SELECT '', rest FROM input
    UNION ALL
    SELECT substr(rest, 1, instr(rest, char(10)) - 1),
           substr(rest, instr(rest, char(10)) + 1)
      FROM lines
     WHERE rest <> ''
)
INSERT INTO _mig0048_contract (
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

CREATE TEMP TABLE _mig0048_pre (ok INTEGER CHECK (ok = 1));

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (SELECT COUNT(*) FROM identifiers) = 43856 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL
) = 43124 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (SELECT MAX(version) FROM schema_version) = 35 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (SELECT COUNT(*) FROM _mig0048_contract) = 36 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(DISTINCT identifier_type || '|' || lower(identifier))
      FROM _mig0048_contract
) = 36 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM _mig0048_contract
     WHERE identifier_type = 'oui'
       AND source_type = 'primary_registry'
       AND geographic_scope = 'global'
       AND confidence IN (80, 85)
       AND json_valid(notes) = 1
       AND json_type(notes) = 'object'
       AND json_extract(notes, '$.cohort') = 'mac537_v170_additional_harvest'
       AND json_extract(notes, '$.ieee_registrant') = manufacturer
       AND json_extract(notes, '$.mac537_ingest_bin') = manifest_bin
) = 36 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM _mig0048_contract
     WHERE manifest_bin = 'ratify_feed_reaching'
) = 3 AND (
    SELECT COUNT(*) FROM _mig0048_contract
     WHERE manifest_bin = 'hold_unknown'
) = 25 AND (
    SELECT COUNT(*) FROM _mig0048_contract
     WHERE manifest_bin = 'pending_category_adjudication'
) = 8 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM _mig0048_contract WHERE device_category = 'unknown'
) = 33 AND (
    SELECT COUNT(*) FROM _mig0048_contract WHERE device_category = 'alpr'
) = 2 AND (
    SELECT COUNT(*) FROM _mig0048_contract WHERE device_category = 'cctv_camera'
) = 1 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM _mig0048_contract
     WHERE manifest_bin = 'pending_category_adjudication'
       AND device_category = 'unknown'
       AND json_extract(notes, '$.category_ratified_by') LIKE 'MAC-558%'
) = 8 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM _mig0048_contract
     WHERE (identifier = '94:7b:be' AND manufacturer = 'Ubicquia LLC'
            AND device_category = 'alpr' AND confidence = 85)
        OR (identifier = '00:24:ae' AND manufacturer = 'IDEMIA PUBLIC SECURITY FRANCE'
            AND device_category = 'alpr' AND confidence = 85)
        OR (identifier = '88:23:64' AND manufacturer = 'Watchnet DVR Inc'
            AND device_category = 'cctv_camera' AND confidence = 80)
) = 3 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM _mig0048_contract
     WHERE manufacturer = 'Intelbras S.A. (de C.V.)'
) = 0 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM identifiers i
      JOIN _mig0048_contract c
        ON lower(replace(replace(replace(replace(i.identifier, ':', ''), '-', ''), '.', ''), ' ', ''))
         = lower(replace(replace(replace(replace(c.identifier, ':', ''), '-', ''), '.', ''), ' ', ''))
) = 0 THEN 1 ELSE 0 END;

INSERT INTO identifiers (
    identifier, identifier_type, device_category, manufacturer, model,
    confidence, source_url, source_type, source_excerpt, geographic_scope, notes
)
SELECT identifier, identifier_type, device_category, manufacturer, model,
       confidence, source_url, source_type, source_excerpt, geographic_scope, notes
  FROM _mig0048_contract
 ORDER BY rowid;

CREATE TEMP TABLE _mig0048_post (ok INTEGER CHECK (ok = 1));

INSERT INTO _mig0048_post(ok)
SELECT CASE WHEN changes() = 36 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_post(ok)
SELECT CASE WHEN (SELECT COUNT(*) FROM identifiers) = 43892 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL
) = 43160 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_post(ok)
SELECT CASE WHEN (SELECT MAX(version) FROM schema_version) = 35 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM identifiers
     WHERE superseded_by IS NULL
       AND json_valid(notes) = 1
       AND json_extract(notes, '$.cohort') = 'mac537_v170_additional_harvest'
) = 36 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM identifiers i
      JOIN _mig0048_contract c
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
) = 36 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM identifiers
     WHERE superseded_by IS NULL
       AND json_valid(notes) = 1
       AND json_extract(notes, '$.cohort') = 'mac537_v170_additional_harvest'
       AND device_category = 'unknown'
) = 33 AND (
    SELECT COUNT(*) FROM identifiers
     WHERE superseded_by IS NULL
       AND json_valid(notes) = 1
       AND json_extract(notes, '$.cohort') = 'mac537_v170_additional_harvest'
       AND device_category = 'alpr'
) = 2 AND (
    SELECT COUNT(*) FROM identifiers
     WHERE superseded_by IS NULL
       AND json_valid(notes) = 1
       AND json_extract(notes, '$.cohort') = 'mac537_v170_additional_harvest'
       AND device_category = 'cctv_camera'
) = 1 THEN 1 ELSE 0 END;

INSERT INTO _mig0048_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM identifiers
     WHERE superseded_by IS NULL
       AND json_valid(notes) = 1
       AND json_extract(notes, '$.cohort') = 'mac537_v170_additional_harvest'
       AND manufacturer = 'Intelbras S.A. (de C.V.)'
) = 0 THEN 1 ELSE 0 END;

DROP TABLE _mig0048_post;
DROP TABLE _mig0048_pre;
DROP TABLE _mig0048_contract;

COMMIT;
