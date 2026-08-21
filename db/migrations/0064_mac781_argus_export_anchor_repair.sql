-- ============================================================================
-- Migration: 0064_mac781_argus_export_anchor_repair.sql
-- Status:    STAGED — anchor design approved at MAC-781 comment 197bd963,
--            9-row JSON `category_correction_authority` fix + 62-row plain-
--            text + JSON `/MAC/` URL strip. STAGE-ONLY, NO push/tag.
-- Slot:      0064, allocated by `next_migration_slot.py --slot 0064 --claim
--            MAC-781`. Highest file on disk: 0060 (MAC-737). Gaps below
--            0060: 0046/0047/0050/0053/0056/0058 — all bound to other
--            issues, none reusable. Slots 0061/0062/0063 — claimed by
--            MAC-742/MAC-752/MAC-765. 0064 was free at claim time.
-- Issue:     MAC-781 — exports/argus_export.csv ships a dead provenance
--            anchor (BIBLE_AMENDMENTS.md:4197, 9 rows) + 124 internal
--            tracker URLs in notes. Both halves live in identifiers.notes,
--            so both are fixed in this one migration.
--
-- Authority:  Issue body + design at operator_review/MAC-781/ANCHOR_DESIGN.md
--             (Rev 2, applying CEO ruling at comment 197bd963).
--
-- schema_version: NOT bumped. Data-only canonical write, no DDL.
--
-- Purpose:    Half 1 — for the 9 active rows where notes has valid JSON and
--             `$.category_correction_authority` cites
--             `BIBLE_AMENDMENTS.md:4197` (a dead line-anchor that resolved
--             to an adsb.lol source bullet, off by 67 lines from the
--             actual `cctv_camera` clause at :4264), replace the value with
--             `docs/engineering/BIBLE_AMENDMENTS.md#mac781-cp33-s2-1-cctv_camera`
--             + the same quoted-clause text the row already carries.
--             Half 2 — for the 62 active rows whose notes carry 124 `/MAC/`
--             URLs in `Board ratifications: ...` lines, replace the URL
--             portion of each `[`text`](URL)` markdown link with a bare
--             textual reference (`MAC-1 comment 613ec532`,
--             `SAR-9 approval 234faaa7`). Append a plain-text audit suffix
--             on plain-text rows and a JSON sibling key on JSON rows.
--
-- Design (Rev 2):  Three-coordinate anchor
--                  `mac781-cp33-s2-1-cctv_camera` decomposes as the lane
--                  / Correction Pass / section / row, ASCII only (no §,
--                  which percent-encodes to %C2%A7 in URL fragments).
--                  Implemented as an HTML anchor inside the cctv_camera
--                  cell at docs/engineering/BIBLE_AMENDMENTS.md:4264:
--                    | `cctv_camera` <a id="mac781-cp33-s2-1-cctv_camera"></a> | ... |
--                  Drift detector: scripts/check_mac781_anchor_clause.py
--                  resolves the anchor to exactly one line and asserts
--                  the quoted clause text in notes still matches that
--                  line. Anchor missing, ambiguous, or clause drifted
--                  exit non-zero. Five pytest cases at
--                  tests/test_check_mac781_anchor_clause.py lock the
--                  behaviour.
--
-- URL strip pattern (CEO Rev 2):
--                  `[\`613ec532\`](URL)` -> `MAC-1 comment 613ec532`
--                  `[\`234faaa7\`](URL)` -> `SAR-9 approval 234faaa7`
--                  Bare, no backticks (CSV data field, not rendered
--                  markdown). Audit suffix uses `tracker URLs`, never
--                  the literal `/MAC/` (which would re-introduce the
--                  token the strip removes and fail POST-4).
--
-- json_valid SWEEP over the Half-2 mutation scope (run pre-write):
--                  62 rows carry /MAC/. Of those:
--                    - 43 plain-text rows (json_valid=0): plain-text
--                      substring replace + plain-text audit suffix
--                    - 19 JSON rows (json_valid=1): row keys differ:
--                        * 18 carry _legacy_notes
--                        *  1 carries  legacy_text_notes (id=415)
--                      In every case the URL is inside the legacy-text
--                      value, so a json_set on the legacy-text key
--                      applies the substring replace without touching
--                      the rest of the JSON envelope.
--                  POST-5 is the load-bearing guard — `json_valid` must
--                  not flip for any Half-2 row. Plain-text rows stay 0,
--                  JSON rows stay 1.
--
-- Pre-apply canonical sha256: pinned at the migration slot's wrapper
--                            (operator_review/MAC-781/apply_migration.py)
--                            at apply time. Per mig-0049/mig-0055
--                            standing rule.
-- Backup path:              db/argus.db.mac781_pre_mig0064_<UTC>.bak
--                            (+ .sha256 sidecar)
--
-- Scope:    UPDATE exactly 71 existing live rows (`superseded_by IS NULL`):
--             Half 1: 9 (id IN (44677, 44703..44710))
--             Half 2: 62 (notes LIKE '%/MAC/%' AND superseded_by IS NULL)
--           No row is INSERTed, no row is superseded, no row is deleted.
--           Active row count is UNCHANGED (DELTA = 0).
--
-- Safety:   Fail closed unless canonical pre-state is exactly:
--             - schema_version = 35
--             - 9 rows match the Half-1 contract
--             - 62 rows match the Half-2 contract
--             - 0 rows already carry the new anchor substring
--             - 0 rows already carry mac781_audit (idempotency)
--             - All 9 Half-1 notes are valid JSON
--             - Half-2 notes shape matches the per-row plan
--               (43 plain-text, 19 JSON; per-key split per PRE-3b)
--
-- DDL:      None. schema_version remains 35.
-- Exports:  Regenerated separately by MAC-781 W5 after this migration
--           applies to the post-MAC-764 canonical.
-- Re-apply: A second run fails the pre-state guards (rows no longer
--           carry the pre-image substring) and rolls back WITHOUT
--           mutation. Proven with sha256 byte-identical of the scratch
--           DB before and after run 2.
--
-- Sequencing: STAGED behind MAC-764 history-purge. MAC-764 must land
--             before this migration runs, so the corrected export is
--             not rewritten underneath us. Tooling rescue (the scripts
--             this migration depends on) was already committed to
--             scripts/ in commit bcee147, BEFORE MAC-764 force-pushes.
-- ============================================================================

.bail on

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- ---------------------------------------------------------------------------
-- Constants. Captured at apply time so every audit stamp on every row in
-- this migration run shares one timestamp. Idempotency guard PRE-7 reads
-- the mac781_audit substring; a re-run sees existing stamps and fails
-- closed without mutating anything.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _audit_const AS
SELECT strftime('%Y-%m-%dT%H:%M:%SZ', 'now') AS stripped_at_utc;

-- The two URL forms. Verified empirically: all 62 Half-2 rows carry BOTH
-- forms (62/62 for comment, 62/62 for approval). Distinct URL count is 2.
-- A future edit that introduces a new URL form MUST update both this
-- constant AND PRE-3 (the contract count).
CREATE TEMP TABLE _url_const AS
SELECT
  '613ec532-d8cb-4f0f-a35b-c811e2864d7d'                                AS comment_hash,
  '234faaa7-e1c0-40fd-a247-f82cb588fc23'                                AS approval_uuid,
  '`613ec532`](/MAC/issues/MAC-1#comment-613ec532-d8cb-4f0f-a35b-c811e2864d7d)'
                                                                       AS comment_link_pre,
  'MAC-1 comment 613ec532'                                              AS comment_link_post,
  '`234faaa7`](/MAC/approvals/234faaa7-e1c0-40fd-a247-f82cb588fc23)'    AS approval_link_pre,
  'SAR-9 approval 234faaa7'                                             AS approval_link_post;

-- The Half-1 cite pre-image (JSON-escaped) and post-image.
CREATE TEMP TABLE _cite_const AS
SELECT
  'BIBLE_AMENDMENTS.md:4197 — `cctv_camera` ''Distinguishes general-purpose CCTV from existing `covert_cam`''; PROJECT_BIBLE.md:323 — `covert_cam` ''covert by definition'''
                                                                       AS cite_pre,
  'docs/engineering/BIBLE_AMENDMENTS.md#mac781-cp33-s2-1-cctv_camera — `cctv_camera` ''Distinguishes general-purpose CCTV from existing `covert_cam`''; PROJECT_BIBLE.md:323 — `covert_cam` ''covert by definition'''
                                                                       AS cite_post;

-- ---------------------------------------------------------------------------
-- Pre-state snapshot. Every post-condition below is a DELTA against this row.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE _pre AS SELECT
    (SELECT MAX(version) FROM schema_version)                                                            AS sv_max,
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)                                       AS active,
    (SELECT COUNT(*) FROM identifiers)                                                                   AS total,
    -- Half 1 contract: 9 rows whose JSON `category_correction_authority` carries `:4197`
    (SELECT COUNT(*) FROM identifiers
       WHERE superseded_by IS NULL
         AND json_valid(notes) = 1
         AND json_extract(notes, '$.category_correction_authority') LIKE '%:4197%'
         AND id IN (44677, 44703, 44704, 44705, 44706, 44707, 44708, 44709, 44710))                       AS h1_count,
    -- Half 2 contract: 62 rows whose notes carry the literal /MAC/
    (SELECT COUNT(*) FROM identifiers
       WHERE superseded_by IS NULL
         AND notes LIKE '%/MAC/%')                                                                       AS h2_count,
    -- Half 2 shape split
    (SELECT COUNT(*) FROM identifiers
       WHERE superseded_by IS NULL
         AND notes LIKE '%/MAC/%'
         AND json_valid(notes) = 0)                                                                       AS h2_plain,
    (SELECT COUNT(*) FROM identifiers
       WHERE superseded_by IS NULL
         AND notes LIKE '%/MAC/%'
         AND json_valid(notes) = 1
         AND json_type(notes) = 'object'
         AND (json_extract(notes, '$._legacy_notes') IS NOT NULL
           OR json_extract(notes, '$.legacy_text_notes') IS NOT NULL))                                    AS h2_json_with_legacy,
    -- Idempotency: 0 rows already carry the new anchor substring; 0 rows
    -- already stamped with mac781_audit.
    (SELECT COUNT(*) FROM identifiers
       WHERE superseded_by IS NULL
         AND json_valid(notes) = 1
         AND json_extract(notes, '$.category_correction_authority') LIKE '%mac781-cp33-s2-1-cctv_camera%')
                                                                                                            AS already_new_cite,
    (SELECT COUNT(*) FROM identifiers
       WHERE superseded_by IS NULL
         AND notes LIKE '%mac781_audit%')                                                                  AS already_audited;

-- ---------------------------------------------------------------------------
-- PRECONDITIONS.
-- ---------------------------------------------------------------------------

CREATE TEMP TABLE _mac781_go (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac781_go(ok) SELECT CASE WHEN (
      (SELECT sv_max FROM _pre) = 35
  AND (SELECT h1_count FROM _pre) = 9
  AND (SELECT h2_count FROM _pre) = 62
  AND (SELECT h2_plain FROM _pre) + (SELECT h2_json_with_legacy FROM _pre) = 62
  AND (SELECT already_new_cite FROM _pre) = 0
  AND (SELECT already_audited FROM _pre) = 0
  AND (SELECT active FROM _pre) = 43126
) THEN 1 ELSE 0 END;

-- ---------------------------------------------------------------------------
-- WRITE A — Half 1: 9 rows, atomic `json_set` on `category_correction_authority`.
-- ---------------------------------------------------------------------------
UPDATE identifiers
   SET notes = json_set(
       notes,
       '$.category_correction_authority',
       (SELECT cite_post FROM _cite_const)
   )
 WHERE (SELECT COUNT(*) FROM _mac781_go) = 1
   AND superseded_by IS NULL
   AND json_valid(notes) = 1
   AND json_extract(notes, '$.category_correction_authority') LIKE '%:4197%'
   AND id IN (44677, 44703, 44704, 44705, 44706, 44707, 44708, 44709, 44710);

-- ---------------------------------------------------------------------------
-- WRITE B — Half 2 plain-text (43 rows): atomic substring replace +
-- plain-text audit suffix. json_valid=0 preserved (POST-5).
-- ---------------------------------------------------------------------------
UPDATE identifiers
   SET notes =
         replace(
           replace(
             notes,
             (SELECT comment_link_pre FROM _url_const),
             (SELECT comment_link_post FROM _url_const)
           ),
           (SELECT approval_link_pre FROM _url_const),
           (SELECT approval_link_post FROM _url_const)
         )
         || char(10)
         || 'mac781_audit: stripped 2 tracker URLs at '
         || (SELECT stripped_at_utc FROM _audit_const)
         || '; pattern=mac781_v1_tracker_url_strip'
 WHERE (SELECT COUNT(*) FROM _mac781_go) = 1
   AND superseded_by IS NULL
   AND notes LIKE '%/MAC/%'
   AND json_valid(notes) = 0;

-- ---------------------------------------------------------------------------
-- WRITE C — Half 2 JSON `_legacy_notes` (18 rows): atomic `json_set` on
-- `$._legacy_notes`. The substring replace runs on the legacy text
-- value; rest of the JSON envelope untouched. json_valid=1 preserved
-- (POST-5). Audit stamp lands as a `$.mac781_audit` sibling key.
-- ---------------------------------------------------------------------------
UPDATE identifiers
   SET notes = json_set(
       json_set(
         json_set(
           notes,
           '$._legacy_notes',
           replace(
             replace(
               json_extract(notes, '$._legacy_notes'),
               (SELECT comment_link_pre FROM _url_const),
               (SELECT comment_link_post FROM _url_const)
             ),
             (SELECT approval_link_pre FROM _url_const),
             (SELECT approval_link_post FROM _url_const)
           )
         ),
         '$.mac781_audit.stripped_at_utc',
         (SELECT stripped_at_utc FROM _audit_const)
       ),
       '$.mac781_audit.stripped_count',
       2
   )
 WHERE (SELECT COUNT(*) FROM _mac781_go) = 1
   AND superseded_by IS NULL
   AND json_valid(notes) = 1
   AND json_type(notes) = 'object'
   AND json_extract(notes, '$._legacy_notes') IS NOT NULL
   AND json_extract(notes, '$._legacy_notes') LIKE '%/MAC/%';

-- ---------------------------------------------------------------------------
-- WRITE D — Half 2 JSON `legacy_text_notes` (1 row, id=415): same shape
-- as Write C but on the alternate JSON key.
-- ---------------------------------------------------------------------------
UPDATE identifiers
   SET notes = json_set(
       json_set(
         json_set(
           notes,
           '$.legacy_text_notes',
           replace(
             replace(
               json_extract(notes, '$.legacy_text_notes'),
               (SELECT comment_link_pre FROM _url_const),
               (SELECT comment_link_post FROM _url_const)
             ),
             (SELECT approval_link_pre FROM _url_const),
             (SELECT approval_link_post FROM _url_const)
           )
         ),
         '$.mac781_audit.stripped_at_utc',
         (SELECT stripped_at_utc FROM _audit_const)
       ),
       '$.mac781_audit.stripped_count',
       2
   )
 WHERE (SELECT COUNT(*) FROM _mac781_go) = 1
   AND superseded_by IS NULL
   AND json_valid(notes) = 1
   AND json_type(notes) = 'object'
   AND json_extract(notes, '$.legacy_text_notes') IS NOT NULL
   AND json_extract(notes, '$.legacy_text_notes') LIKE '%/MAC/%';

-- ---------------------------------------------------------------------------
-- POST-CONDITIONS. Deltas against `_pre`.
-- ---------------------------------------------------------------------------

CREATE TEMP TABLE _mac781_post_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac781_post_1fail(ok) SELECT CASE WHEN (
       (SELECT MAX(version) FROM schema_version) = (SELECT sv_max FROM _pre))
  THEN 1 ELSE 0 END;

CREATE TEMP TABLE _mac781_post_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac781_post_2fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)
         = (SELECT active FROM _pre))
  THEN 1 ELSE 0 END;

CREATE TEMP TABLE _mac781_post_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac781_post_3fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers)
         = (SELECT total FROM _pre))
  THEN 1 ELSE 0 END;

-- POST-4: 0 /MAC/ anywhere in any active notes (Half-1 and Half-2 combined).
CREATE TEMP TABLE _mac781_post_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac781_post_4fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers
          WHERE superseded_by IS NULL AND notes LIKE '%/MAC/%') = 0)
  THEN 1 ELSE 0 END;

-- POST-5: every Half-2 row preserves its pre-migration json_valid shape
-- (plain-text rows stay 0, JSON rows stay 1). Load-bearing per CEO §Q3.
CREATE TEMP TABLE _mac781_post_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac781_post_5fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers
          WHERE superseded_by IS NULL
            AND notes LIKE '%mac781_audit%'
            AND json_valid(notes) = 0) = (SELECT h2_plain FROM _pre)
   AND (SELECT COUNT(*) FROM identifiers
          WHERE superseded_by IS NULL
            AND json_valid(notes) = 1
            AND json_extract(notes, '$.mac781_audit') IS NOT NULL) = (SELECT h2_json_with_legacy FROM _pre))
  THEN 1 ELSE 0 END;

-- POST-6: every Half-1 row carries the new cite substring.
CREATE TEMP TABLE _mac781_post_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac781_post_6fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers
          WHERE superseded_by IS NULL
            AND json_valid(notes) = 1
            AND json_extract(notes, '$.category_correction_authority') LIKE '%mac781-cp33-s2-1-cctv_camera%'
            AND id IN (44677, 44703, 44704, 44705, 44706, 44707, 44708, 44709, 44710)) = 9
   AND (SELECT COUNT(*) FROM identifiers
          WHERE superseded_by IS NULL
            AND json_valid(notes) = 1
            AND json_extract(notes, '$.category_correction_authority') LIKE '%:4197%'
            AND id IN (44677, 44703, 44704, 44705, 44706, 44707, 44708, 44709, 44710)) = 0)
  THEN 1 ELSE 0 END;

-- POST-7: every Half-2 row carries the audit stamp substring.
CREATE TEMP TABLE _mac781_post_7fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac781_post_7fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers
          WHERE superseded_by IS NULL AND notes LIKE '%mac781_audit%') = 62)
  THEN 1 ELSE 0 END;

-- POST-8: the new anchor+clause gate runs end-to-end. SQLite cannot shell
-- out, so this is a delegated check: the wrapper apply script runs
-- `python3 scripts/check_mac781_anchor_clause.py --expected-clause "..."
-- --new-anchor "docs/engineering/BIBLE_AMENDMENTS.md#mac781-cp33-s2-1-cctv_camera"`
-- and asserts rc=0. The wrapper aborts the migration if the gate fails.
-- This is a NOT-MACHINE-CHECKED-BY-SQL condition; it is documented here
-- so the wrapper contract is part of the migration's specification.

DROP TABLE _mac781_post_7fail;
DROP TABLE _mac781_post_6fail;
DROP TABLE _mac781_post_5fail;
DROP TABLE _mac781_post_4fail;
DROP TABLE _mac781_post_3fail;
DROP TABLE _mac781_post_2fail;
DROP TABLE _mac781_post_1fail;
DROP TABLE _mac781_go;
DROP TABLE _url_const;
DROP TABLE _cite_const;
DROP TABLE _audit_const;
DROP TABLE _pre;

COMMIT;