-- ============================================================================
-- Migration: 0042_mac542_procurement_boundary_quarantine.sql
-- Status:    STAGED — data-only quarantine for MAC-542 T1.
--
-- Purpose:   Preserve, in place, the 9,065 procurement_records rows that match
--            no known vendor at any entity boundary. The rows remain analytical
--            history and are marked through notes JSON; no row is deleted and no
--            schema column or schema_version entry is added.
--
-- Authority: operator_review/MAC-542/PROOF.md, T1_withdraw_ids.txt, and the
--            MAC-545 dispatch. The target ID file is the exact 9,065-row input.
--
-- Mechanism: notes.mac542_boundary_rematch is merged by property with json_set:
--            {"verdict":"quarantined","asserted_keyword":[...],"basis":"none"}
--            Empty or NULL notes are normalized to {} before the merge. Existing
--            valid notes are preserved by json_set; non-empty malformed notes are
--            rejected by the precondition rather than overwritten.
--
-- Re-apply safety: the precondition requires the property to be absent on every
--            target, and the UPDATE also requires it to be absent. A second apply
--            therefore performs zero writes and fails its strict change-count
--            guard; the apply runner must rollback that attempt.
--
-- Apply discipline: run from the repository root with an executor that checks
--            each statement and rolls back on any error. The sqlite3 CLI does not
--            support a -bail option; do not treat a clean process exit alone as
--            proof that this migration applied.
--
-- schema_version: unchanged at 33 because this migration has no DDL.
-- ============================================================================

BEGIN IMMEDIATE;

CREATE TEMP TABLE _mig0042_source_ids (
    id INTEGER PRIMARY KEY
);

-- The migration consumes the ratified one-ID-per-line artifact. readfile() is
-- available in the sqlite3 CLI used by the repository's migration workflow.
WITH RECURSIVE
input(rest) AS (
    SELECT readfile('operator_review/MAC-542/T1_withdraw_ids.txt') || char(10)
),
lines(line, rest) AS (
    SELECT '', rest FROM input
    UNION ALL
    SELECT substr(rest, 1, instr(rest, char(10)) - 1),
           substr(rest, instr(rest, char(10)) + 1)
      FROM lines
     WHERE rest <> ''
)
INSERT INTO _mig0042_source_ids(id)
SELECT CAST(trim(line) AS INTEGER)
  FROM lines
 WHERE trim(line) <> '';

CREATE TEMP TABLE _mig0042_pre (
    ok INTEGER CHECK (ok = 1)
);

-- Strict scope and source-artifact guards.
INSERT INTO _mig0042_pre(ok)
SELECT CASE WHEN (SELECT COUNT(*) FROM procurement_records) = 50499
            THEN 1 ELSE 0 END;

INSERT INTO _mig0042_pre(ok)
SELECT CASE WHEN (SELECT COUNT(*) FROM _mig0042_source_ids) = 9065
            THEN 1 ELSE 0 END;

INSERT INTO _mig0042_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0042_source_ids s
      JOIN procurement_records p ON p.id = s.id
) = 9065 THEN 1 ELSE 0 END;

INSERT INTO _mig0042_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0042_source_ids s
      JOIN procurement_records p ON p.id = s.id
     WHERE p.source_type = 'procurement'
) = 9065 THEN 1 ELSE 0 END;

-- Full mutation-scope JSON sweep: empty/NULL notes are allowed and normalized;
-- every non-empty note must already be valid JSON.
INSERT INTO _mig0042_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0042_source_ids s
      JOIN procurement_records p ON p.id = s.id
     WHERE p.notes IS NOT NULL
       AND p.notes <> ''
       AND json_valid(p.notes) = 0
) = 0 THEN 1 ELSE 0 END;

INSERT INTO _mig0042_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0042_source_ids s
      JOIN procurement_records p ON p.id = s.id
     WHERE p.notes IS NULL OR p.notes = ''
) = 3925 THEN 1 ELSE 0 END;

INSERT INTO _mig0042_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0042_source_ids s
      JOIN procurement_records p ON p.id = s.id
     WHERE p.notes IS NOT NULL
       AND p.notes <> ''
       AND json_valid(p.notes) = 1
) = 5140 THEN 1 ELSE 0 END;

-- No target may already carry this property. This blocks partial or repeated
-- application before any row update is attempted.
INSERT INTO _mig0042_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0042_source_ids s
      JOIN procurement_records p ON p.id = s.id
     WHERE json_type(
               COALESCE(NULLIF(p.notes, ''), '{}'),
               '$.mac542_boundary_rematch'
           ) IS NOT NULL
) = 0 THEN 1 ELSE 0 END;

-- Re-match artifact parity: 3,925 no-provenance rows carry [], while the 5,140
-- rows with provenance carry either keyword_match[] or matched_query_name.
INSERT INTO _mig0042_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0042_source_ids s
      JOIN procurement_records p ON p.id = s.id
     WHERE p.notes IS NOT NULL
       AND p.notes <> ''
       AND (
           json_type(p.notes, '$.keyword_match') = 'array'
           OR json_extract(p.notes, '$.matched_query_name') IS NOT NULL
       )
) = 5140 THEN 1 ELSE 0 END;

UPDATE procurement_records AS p
   SET notes = json_set(
       COALESCE(NULLIF(p.notes, ''), '{}'),
       '$.mac542_boundary_rematch',
       json_object(
           'verdict', 'quarantined',
           'asserted_keyword', json(
               CASE
                   WHEN json_valid(p.notes) = 1
                    AND json_type(p.notes, '$.keyword_match') = 'array'
                   THEN json_extract(p.notes, '$.keyword_match')
                   WHEN json_valid(p.notes) = 1
                    AND json_extract(p.notes, '$.matched_query_name') IS NOT NULL
                   THEN json_array(json_extract(p.notes, '$.matched_query_name'))
                   ELSE '[]'
               END
           ),
           'basis', 'none'
       )
   )
 WHERE p.id IN (SELECT id FROM _mig0042_source_ids)
   AND json_type(
           COALESCE(NULLIF(p.notes, ''), '{}'),
           '$.mac542_boundary_rematch'
       ) IS NULL;

CREATE TEMP TABLE _mig0042_post (
    ok INTEGER CHECK (ok = 1)
);

INSERT INTO _mig0042_post(ok)
SELECT CASE WHEN changes() = 9065 THEN 1 ELSE 0 END;

INSERT INTO _mig0042_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0042_source_ids s
      JOIN procurement_records p ON p.id = s.id
     WHERE json_valid(p.notes) = 1
       AND json_extract(p.notes, '$.mac542_boundary_rematch.verdict') = 'quarantined'
       AND json_extract(p.notes, '$.mac542_boundary_rematch.basis') = 'none'
       AND json_type(p.notes, '$.mac542_boundary_rematch.asserted_keyword') = 'array'
) = 9065 THEN 1 ELSE 0 END;

INSERT INTO _mig0042_post(ok)
SELECT CASE WHEN (
    SELECT COUNT(*)
      FROM _mig0042_source_ids s
      JOIN procurement_records p ON p.id = s.id
     WHERE json_valid(p.notes) = 1
       AND (
           json_type(p.notes, '$.keyword_match') = 'array'
           OR json_extract(p.notes, '$.matched_query_name') IS NOT NULL
           OR json_extract(p.notes, '$.mac542_boundary_rematch.asserted_keyword') = '[]'
       )
) = 9065 THEN 1 ELSE 0 END;

INSERT INTO _mig0042_post(ok)
SELECT CASE WHEN (SELECT COUNT(*) FROM procurement_records) = 50499
            THEN 1 ELSE 0 END;

DROP TABLE _mig0042_post;
DROP TABLE _mig0042_pre;
DROP TABLE _mig0042_source_ids;

COMMIT;
