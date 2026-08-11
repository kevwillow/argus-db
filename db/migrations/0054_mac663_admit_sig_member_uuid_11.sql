-- ============================================================================
-- Migration: 0054_mac663_admit_sig_member_uuid_11.sql
-- Issue:     MAC-663 — 11 adjudicated ble_uuid rows (Axon, Verkada, Rhombus,
--            Motive, Samsara) reach no export: confidence is NULL.
--
-- Status:    APPLIED to canonical `db/argus.db` on 2026-08-11T06:12Z.
--
--            The line below is the STAGED-state prose, preserved verbatim
--            because it is what was written before the apply. It is superseded
--            by the apply record that follows, not edited in place:
--
--              "STAGED, NOT APPLIED at write time. See the APPLY RECORD
--              appended below after the apply; this line is preserved verbatim
--              rather than edited in place."
--
--            APPLY RECORD
--            Applied with:  sqlite3 db/argus.db < db/migrations/0054_....sql
--            Pre-apply canonical sha256:
--              5f8f81db67027e75f667ac1c3f373df377b9f0996636d434732328f3c7e9c16d
--            Post-apply canonical sha256:
--              f6ba68eb828d1f0afc6184e801993938374322bcc86b7cb9fd22e1a7429e8616
--            The post-apply sha was PRE-REGISTERED, not observed after the
--            fact: G5 arms A and D applied this same file to two independent
--            scratch copies of canonical, via two different runners, and both
--            produced f6ba68eb…8616. Canonical landed on that exact value.
--
--            Verified by POST-STATE QUERY, never by `$?` — a sqlite3 exit code
--            is not a safety signal (MAC-661: exit 1 fires both when it stopped
--            and when it committed through failed guards). Measured:
--              rows mutated                 11   (markers = 11)
--              active            43089 -> 43089  (delta 0, as declared)
--              ble_uuid active     667 ->   667  (delta 0, as declared)
--              confidence IS NULL  185 ->   174  (delta -11, as declared)
--              ble_uuid 75+global  654 ->   665  (delta +11, as declared)
--              temp guard tables remaining   0
--
--            FEED DELTA RE-VERIFIED against APPLIED canonical, not carried over
--            from the scratch forecast:
--              standard         972 -> 983   ADDED 11 / REMOVED 0
--              high_confidence  489 -> 500   ADDED 11 / REMOVED 0
--            The APPLIED entry set is SET-IDENTICAL to the scratch-mutated
--            entry set on both files. `exports/` was never written — every
--            artifact went to a scratch dir.
--
--            Revert boundary — a file-copy snapshot OUTSIDE git, because
--            `db/argus.db` is a 314.4 MiB tracked blob and a commit cannot be
--            the revert boundary here (CEO gate G6):
--              5f8f81db67027e75f667ac1c3f373df377b9f0996636d434732328f3c7e9c16d
--                /home/kev/argus-backups/argus.db.mac663_pre_mig0054_20260811T061151Z.bak
--            `db/argus.db` is NOT committed by this lane.
--
--            STAGE ONLY — no push, no tag. The board reserves all pushes.
--
-- Authority: CEO ratification `operator_review/MAC-663/CEO_RATIFICATION.md`
--            (commit 51b8e30), verdict line 3: "APPROVED, with a widened column
--            set and a hard delta gate". §4 rules `confidence = 75`; §5 rules
--            `geographic_scope = 'global'`; §3 rules BOTH columns in scope
--            because one MAC-642 fold demoted the survivors on both, and
--            "fixing only `confidence` would land a migration that knowingly
--            leaves half the demotion in place".
--
--            This is a PROMOTION and it is a real feed change. It was decided
--            at the feed level by the CEO, not inferred here. It is NOT a
--            type-integrity correction (that was MAC-642 / mig-0051).
--
-- Slot:      0054, allocated by DISPATCH CLAIM, not by `ls db/migrations/` and
--            not by `scripts/next_migration_slot.py` — that tool floors its
--            claim scan at `highest_file` and handed one slot to three callers
--            (MAC-674, open). CEO_RATIFICATION.md §8 dispatch-claims 0054 for
--            MAC-663 and deliberately skips 0053, which holds the live
--            three-way collision.
--            Claim state at WRITE time (filename sweep over the whole tree plus
--            a tracked+untracked token grep for `0053`/`0054`):
--              0049 APPLIED  MAC-611
--              0050 CLAIMED  MAC-608  _drafts/0050_mac608_*.sql.draft
--              0051 APPLIED  MAC-642
--              0052 APPLIED  MAC-641
--              0053 CONTESTED — deliberately NOT taken (MAC-674)
--              0054 CLAIMED  MAC-663  this file — sole claimant, corroborated
--                            independently at operator_review/MAC-674/PROOF.md:155
--            A slot verified at WRITE time is not verified at COMMIT time.
--            Re-scan before committing; `ls` answers *applied*, never *claimed*.
--
-- schema_version: NOT bumped. Data-only, no DDL. Stays at 35.
--
-- Scope:     Exactly 11 rows, ids 42986-42996. Every write is pinned on BOTH
--            the id AND the literal identifier value, so an id drift cannot
--            silently retarget a write.
--
-- NOT in scope: the other 174 NULL-confidence rows of the same 185-row
--            widenet_gate1 cohort. They are not feed-reaching at any confidence
--            value — they drop at the §4.4 type gate, which sits BEFORE the
--            confidence floor. CEO_RATIFICATION.md §9 accepts them as residue.
--            Adjudication (vendor, device_category) is untouched here.
--
-- MEASURED FEED DELTA (CEO gate G1), two-column mutation, produced by
-- `scripts/mac663_delta_probe.py` over scratch copies of canonical. `exports/`
-- was never written:
--   standard         972 -> 983   ADDED 11 / REMOVED 0
--   high_confidence  489 -> 500   ADDED 11 / REMOVED 0
-- Both ADDED sets are EXACTLY the 11 under test, by set identity on
-- (pattern_type, pattern) — not by count. G2 PASS, G3 PASS. The high-confidence
-- +11 is the value pre-approved by CEO_RATIFICATION.md §6 G3.
--
-- Why high_confidence moves now and did not in PROOF.md §4: CP7
-- (`db/validation/export_lynceus.py`) fails a NULL `geographic_scope` for the
-- high-confidence export, so a confidence-only fix could never reach it at any
-- value through 99. Restoring `global` clears CP7; 75 clears the 70 floor.
--
-- ASSERTION MECHANISM: `CREATE TEMP TABLE t(ok INTEGER CHECK (ok=1))` +
-- `INSERT ... SELECT CASE`. NOT `SELECT CASE WHEN ... THEN RAISE(ABORT,...)`:
-- SQLite rejects RAISE() outside a trigger-program with a PARSE ERROR.
--
-- THREE ARMS, because a CHECK(ok=1) alone aborts its own INSERT and lets the
-- CLI walk on to COMMIT — an artifact that reads as protected while writing
-- everything (MAC-661: exit 1 both when it stopped and when it committed
-- through failed guards):
--   arm 1  `.bail on`                    — sqlite3 CLI only; a no-op under
--                                          conn.executescript()
--   arm 2  CHECK(ok=1) on each guard     — surfaces the failure
--   arm 3  `(SELECT COUNT(*) FROM _mac663_go) = 1` on EVERY canonical write —
--          portable, fail-closed under ANY runner. If any precondition failed,
--          `_mac663_go` is EMPTY and all 11 UPDATEs match zero rows.
-- Verify the apply by a POST-STATE QUERY, never by `$?`.
-- ============================================================================
.bail on

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- Pre-state snapshot. Every post-condition below is asserted as a DELTA against
-- this row (CEO gate G4), never as a pinned absolute total — an absolute rots
-- the moment a co-tenant lane applies anything.
CREATE TEMP TABLE _pre AS SELECT
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)                      AS active,
    (SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_uuid'
       AND superseded_by IS NULL)                                                       AS bu,
    (SELECT COUNT(*) FROM identifiers WHERE confidence IS NULL
       AND superseded_by IS NULL)                                                       AS nullconf,
    (SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_uuid'
       AND superseded_by IS NULL AND confidence=75 AND geographic_scope='global')        AS sib;

-- The mutation scope, defined ONCE by the same selector every write uses.
CREATE TEMP TABLE _scope AS
  SELECT id FROM identifiers
   WHERE id BETWEEN 42986 AND 42996
     AND identifier_type='ble_uuid'
     AND superseded_by IS NULL
     AND confidence IS NULL
     AND geographic_scope IS NULL;

-- PRE-1 FAIL: the mutation scope is not exactly the 11 rows this migration was
-- ratified against.
CREATE TEMP TABLE _mac663_pre_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_pre_1fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _scope) <> 11) THEN 0 ELSE 1 END;

-- PRE-2 FAIL: the 11 scope rows are not the 11 literal identifier values the
-- CEO ratified. Guards against an id-range drift retargeting the writes.
CREATE TEMP TABLE _mac663_pre_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_pre_2fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE id IN (SELECT id FROM _scope) AND identifier IN (
      '0000fc6d-0000-1000-8000-00805f9b34fb','0000fc70-0000-1000-8000-00805f9b34fb',
      '0000fc81-0000-1000-8000-00805f9b34fb','0000fc86-0000-1000-8000-00805f9b34fb',
      '0000fc87-0000-1000-8000-00805f9b34fb','0000fce4-0000-1000-8000-00805f9b34fb',
      '0000fce5-0000-1000-8000-00805f9b34fb','0000fd3a-0000-1000-8000-00805f9b34fb',
      '0000fd3b-0000-1000-8000-00805f9b34fb','0000fda9-0000-1000-8000-00805f9b34fb',
      '0000fe9b-0000-1000-8000-00805f9b34fb')) <> 11) THEN 0 ELSE 1 END;

-- PRE-3 FAIL: notes is not valid JSON across the mutation scope. json_set()
-- RAISES on a CP39-style text-suffixed blob, and 34 of 240 `manufacturers` rows
-- are json_valid=0 project-wide, so this is swept rather than assumed.
CREATE TEMP TABLE _mac663_pre_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_pre_3fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE id IN (SELECT id FROM _scope) AND notes IS NOT NULL AND json_valid(notes)) <> 11) THEN 0 ELSE 1 END;

-- PRE-4 FAIL: the fold twins that justify the restore are not in the state the
-- ratification measured. CEO_RATIFICATION.md §3/§5 anchor 1: the 11 superseded
-- ble_company_id rows carried confidence=75 AND geographic_scope='global'.
-- Making the justification a precondition means a changed basis stops the write.
CREATE TEMP TABLE _mac663_pre_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_pre_4fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE superseded_by IN (SELECT id FROM _scope)
      AND identifier_type='ble_company_id'
      AND confidence=75 AND geographic_scope='global') <> 11) THEN 0 ELSE 1 END;

-- PRE-5 FAIL: the sibling class anchor moved. CEO_RATIFICATION.md §4 anchor 3 /
-- §5 anchor 2: 654 active ble_uuid rows already carry 75 + 'global'.
CREATE TEMP TABLE _mac663_pre_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_pre_5fail(ok) SELECT CASE WHEN ((SELECT sib FROM _pre) <> 654) THEN 0 ELSE 1 END;

-- PRE-6 FAIL: canonical is not the DB this migration was measured against.
-- Pre-state pins (an absolute is correct HERE — it identifies the input state;
-- G4 governs the POST-conditions, which are deltas).
CREATE TEMP TABLE _mac663_pre_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_pre_6fail(ok) SELECT CASE WHEN (
       (SELECT active   FROM _pre) <> 43089
    OR (SELECT bu       FROM _pre) <> 667
    OR (SELECT nullconf FROM _pre) <> 185) THEN 0 ELSE 1 END;

-- THE GO GATE — `.bail on` ALONE IS NOT ENOUGH, AND THIS IS WHY.
-- `.bail on` is a sqlite3 CLI dot-command. It is a NO-OP under
-- `sqlite3.Connection.executescript()`, apsw, an ORM runner, or a copy-paste of
-- this SQL into a session — and `scripts/mac419_*`, `mac569_*`, `mac580_*` all
-- apply via executescript(). Under any of those a failed precondition aborts
-- only its own INSERT and every UPDATE below then runs and COMMITS.
-- So the gate is STRUCTURAL: `_mac663_go` holds exactly one row IFF all six
-- preconditions passed, and every write carries `COUNT(*) FROM _mac663_go = 1`.
-- If any failed, `_mac663_go` is EMPTY and all 11 writes match zero rows.
-- MAC-663 GO GATE FAIL: one or more preconditions PRE-1..PRE-6 did not pass
CREATE TEMP TABLE _mac663_go (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_go(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mac663_pre_1fail) = 1
   AND (SELECT COUNT(*) FROM _mac663_pre_2fail) = 1
   AND (SELECT COUNT(*) FROM _mac663_pre_3fail) = 1
   AND (SELECT COUNT(*) FROM _mac663_pre_4fail) = 1
   AND (SELECT COUNT(*) FROM _mac663_pre_5fail) = 1
   AND (SELECT COUNT(*) FROM _mac663_pre_6fail) = 1) THEN 1 ELSE 0 END;

-- ================================================================ THE WRITE (11 rows)
-- confidence NULL -> 75, geographic_scope NULL -> 'global'.
-- notes merged BY PROPERTY via json_set. Never text-suffix concatenation.
-- Each write is pinned on id AND the literal identifier value AND the NULL
-- pre-state of both columns, so re-running this file is a no-op rather than a
-- second mutation.
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42986 AND identifier='0000fc6d-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42987 AND identifier='0000fc70-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42988 AND identifier='0000fc81-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42989 AND identifier='0000fc86-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42990 AND identifier='0000fc87-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42991 AND identifier='0000fce4-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42992 AND identifier='0000fce5-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42993 AND identifier='0000fd3a-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42994 AND identifier='0000fd3b-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42995 AND identifier='0000fda9-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;
UPDATE identifiers SET confidence=75, geographic_scope='global', notes=json_set(notes,'$.mac663_admit',json_object('issue','MAC-663','authority','CEO_RATIFICATION.md 51b8e30 §4+§5','confidence_from','NULL','confidence_to',75,'geographic_scope_from','NULL','geographic_scope_to','global','basis','SIG member_uuids.yaml primary_registry; §8.2 band 70-85; restores the two columns demoted by the MAC-642 fold')) WHERE id=42996 AND identifier='0000fe9b-0000-1000-8000-00805f9b34fb' AND identifier_type='ble_uuid' AND superseded_by IS NULL AND confidence IS NULL AND geographic_scope IS NULL AND (SELECT COUNT(*) FROM _mac663_go) = 1;

-- ================================================================ POST-CONDITIONS
-- Asserted as DELTAS against `_pre` (CEO gate G4). The one absolute below is
-- the mutated-row count itself, which is the scope size, not a table total.

-- POST-1 FAIL: the 11 scope rows did not all land on 75 + 'global'.
CREATE TEMP TABLE _mac663_post_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_post_1fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE id IN (SELECT id FROM _scope)
      AND confidence=75 AND geographic_scope='global') <> 11) THEN 0 ELSE 1 END;

-- POST-2 FAIL: a NULL survived on either column anywhere in the id range. This
-- is the arm that would catch a partially-applied write.
CREATE TEMP TABLE _mac663_post_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_post_2fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE id BETWEEN 42986 AND 42996 AND superseded_by IS NULL
      AND (confidence IS NULL OR geographic_scope IS NULL)) <> 0) THEN 0 ELSE 1 END;

-- POST-3 FAIL: active row count moved. This migration mutates columns and
-- creates/supersedes nothing, so the delta is 0 — asserted against `_pre`,
-- never against the literal 43089.
CREATE TEMP TABLE _mac663_post_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_post_3fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE superseded_by IS NULL) <> (SELECT active FROM _pre)) THEN 0 ELSE 1 END;

-- POST-4 FAIL: the active ble_uuid population moved. No retype here; delta 0.
CREATE TEMP TABLE _mac663_post_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_post_4fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE identifier_type='ble_uuid' AND superseded_by IS NULL) <> (SELECT bu FROM _pre)) THEN 0 ELSE 1 END;

-- POST-5 FAIL: the whole-table NULL-confidence population did not fall by
-- exactly 11. Catches a write that scored rows outside the ratified scope.
CREATE TEMP TABLE _mac663_post_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_post_5fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE confidence IS NULL AND superseded_by IS NULL) <> (SELECT nullconf FROM _pre) - 11) THEN 0 ELSE 1 END;

-- POST-6 FAIL: the sibling class did not grow by exactly 11 (654 -> 665).
CREATE TEMP TABLE _mac663_post_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_post_6fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE identifier_type='ble_uuid' AND superseded_by IS NULL
      AND confidence=75 AND geographic_scope='global') <> (SELECT sib FROM _pre) + 11) THEN 0 ELSE 1 END;

-- POST-7 FAIL: json_set corrupted a notes blob, or the provenance marker is not
-- on exactly the 11 mutated rows.
CREATE TEMP TABLE _mac663_post_7fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_post_7fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE id IN (SELECT id FROM _scope)
          AND json_valid(notes)) <> 11
    OR (SELECT COUNT(*) FROM identifiers WHERE json_valid(notes)
          AND json_extract(notes,'$.mac663_admit.issue')='MAC-663') <> 11) THEN 0 ELSE 1 END;

-- POST-8 FAIL: adjudication moved. device_category and manufacturer are out of
-- scope for this migration and must be byte-identical to the ratified values.
CREATE TEMP TABLE _mac663_post_8fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac663_post_8fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
    WHERE id IN (SELECT id FROM _scope)
      AND device_category IN ('body_cam','cctv_camera','automotive_telematics')
      AND manufacturer IN ('Axon','Verkada','Rhombus Systems','Motive','Samsara')
      AND source_type='primary_registry') <> 11) THEN 0 ELSE 1 END;

DROP TABLE _pre;
DROP TABLE _scope;
DROP TABLE _mac663_go;
DROP TABLE _mac663_pre_1fail;
DROP TABLE _mac663_pre_2fail;
DROP TABLE _mac663_pre_3fail;
DROP TABLE _mac663_pre_4fail;
DROP TABLE _mac663_pre_5fail;
DROP TABLE _mac663_pre_6fail;
DROP TABLE _mac663_post_1fail;
DROP TABLE _mac663_post_2fail;
DROP TABLE _mac663_post_3fail;
DROP TABLE _mac663_post_4fail;
DROP TABLE _mac663_post_5fail;
DROP TABLE _mac663_post_6fail;
DROP TABLE _mac663_post_7fail;
DROP TABLE _mac663_post_8fail;
COMMIT;
-- ============================================================================
-- Expected post-state, stated as a DELTA against the pre-apply state because an
-- absolute count written here rots the moment a co-tenant lane applies anything:
--   rows mutated                            : 11
--   active                                  : (pre) + 0
--   ble_uuid active                         : (pre) + 0
--   confidence IS NULL active               : (pre) - 11   (185 -> 174)
--   ble_uuid @ 75 + 'global'                : (pre) + 11   (654 -> 665)
--   feed, standard export                   : ADDED 11 / REMOVED 0
--   feed, high_confidence export             : ADDED 11 / REMOVED 0
--
-- `exports/` is NOT regenerated by this migration. CEO_RATIFICATION.md §7 rules
-- that the v1.7.0 coverage matrix and exports must be generated from a DB in
-- which these 11 already carry both values — that regeneration belongs to the
-- release-assembly lane, which MAC-663 blocks.
--
-- STAGE ONLY — no push, no tag. The board reserves all pushes (MAC-424).
-- ============================================================================
