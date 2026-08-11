-- ============================================================================
-- Migration: 0055_mac691_vendor_flag_anchor_and_dts_withdraw.sql
-- Issue:     MAC-691 — two defects surfaced by the MAC-685 measurement.
--
--            D1  `notes.surveillance_vendor_flag` was populated by a BARE
--                CONTAINMENT test. Containment is not identity: `Ring` fired on
--                `KOZO KEIKAKU ENGINEERING`, `Axon` on `MAXON INDUSTRIES`,
--                `Tile` on `NINGBO FOTILE KITCHENWARE`, `DJI` on `Avedis
--                Zildjian`, `Nest` on `Nestle`. This is the MAC-542 defect class
--                in a fourth call site.
--            D2  id=35700 claims equipment class `DTS` — a generic FCC class
--                shared by 7 distinct manufacturers in this corpus — and cites a
--                page about a DIFFERENT identifier (FCC ID `2AG6I-DISCO`). The
--                string `DTS` does not appear in its own `source_excerpt`, so it
--                fails cite-paste on its own terms.
--
-- Status:    APPLIED to canonical `db/argus.db` on 2026-08-11T20:38Z.
--
--            The line below is the STAGED-state prose, preserved verbatim
--            because it is what was written before the apply. It is superseded
--            by the apply record that follows, not edited in place:
--
--              "STAGED, NOT APPLIED at write time. See the APPLY RECORD appended
--              below after the apply; this line is preserved verbatim rather
--              than edited in place."
--
--            APPLY RECORD
--            Applied with:  sqlite3 db/argus.db < db/migrations/0055_....sql
--            Pre-apply canonical sha256:
--              f6ba68eb828d1f0afc6184e801993938374322bcc86b7cb9fd22e1a7429e8616
--            Post-apply canonical sha256:
--              5e0d3ce440fde05c8d84a8585abd9372b0dab76ee75499277329dae04a0bbdeb
--
--            Verified by POST-STATE QUERY, never by `$?`. The CLI exited 0 here,
--            which proves nothing either way: exit 0/1 fires both when a
--            migration stops and when it commits through failed guards.
--            Measured on canonical:
--              rows with a non-NULL flag       103 -> 41    (delta -62, declared)
--              mac691_flag_correction markers          62   (= scope size)
--              mac691_withdrawal markers                1   (= id 35700)
--              active                        43089 -> 43088 (delta -1, declared)
--              equipment_class_code active     683 -> 682   (delta -1, declared)
--              withdrawn self-loop rows        246 -> 247   (delta +1, declared)
--              notes invalid-JSON rows         243 -> 243   (delta  0, declared)
--              temp guard tables remaining               0
--
--            ACCEPTANCE PROPERTY RE-DERIVED FROM THE APPLIED DB, not read off
--            this file's own POST conditions — a post-condition that mirrors its
--            transform cannot verify it. `db/vendor_flag.py` re-swept live
--            canonical after the apply: 41 rows still flagged, 40 anchored-TRUE,
--            and 0 rows carrying a VENDOR-NAME flag on an unanchored basis. The
--            41st is id=23042, whose value is the JSON literal `false`.
--            Artifact: `operator_review/MAC-691/post_apply_verification.json`.
--
--            PRE-APPLY COUNTERFACTUAL, four arms on scratch copies of canonical
--            (`sqlite3` CLI and an error-SWALLOWING statement runner that
--            executes every statement regardless of failures):
--              A  clean, CLI                   -> writes landed, deltas as declared
--              B  PRE-1 broken, CLI            -> 0 writes
--              C  PRE-1 broken, executescript  -> 0 writes
--              D  PRE-6 broken, swallow-runner -> 6 swallowed CHECKs, 0 writes
--              E  UNBROKEN,     swallow-runner -> writes landed  <- non-vacuity
--            Arm E is what makes arms B-D mean anything: without it, a runner
--            that simply never writes would produce the same four zeros.
--
--            Revert boundary — a file-copy snapshot OUTSIDE git, because
--            `db/argus.db` is a 314 MiB tracked blob and a commit cannot be the
--            revert boundary here:
--              f6ba68eb828d1f0afc6184e801993938374322bcc86b7cb9fd22e1a7429e8616
--                /home/kev/argus-backups/argus.db.mac691_pre_mig0055_20260811T203732Z.bak
--              verified byte-identical to canonical before the apply.
--            `db/argus.db` is NOT committed by this lane.
--
--            STAGE ONLY — no push, no tag. The board reserves all pushes.
--
-- Authority: MAC-691 issue body (board-authored). D1 deliverables 1-4 and the
--            stated acceptance property; D2 deliverable "Supersede id=35700 with
--            a documented reason". The issue also rules the write vehicle:
--            "Do not write to `db/argus.db` outside a numbered migration with an
--            allocated slot. Allocate the slot by dispatch claim."
--
-- THE PREMISE THE ISSUE STATES IS FALSE, AND IT IS RECORDED HERE RATHER THAN
-- SILENTLY WORKED AROUND. The issue says "Neither has shipped, because every
-- affected row is `device_category='unknown'` today and the §11 #13 ban holds it
-- out of every export." Measured on `origin/main` (851d4a2):
--   * 3 of the 103 flagged rows are NOT `unknown` — id=1549 `cctv_camera`,
--     id=6883 and id=8294 `drone`. (All three are anchored-TRUE and keep their
--     flag, so no FALSE flag reached the feed through that door.)
--   * `exports/argus_export.csv` on `origin/main` carries `notes` verbatim at
--     `confidence_threshold=0`, 43,134 records, and emits ALL 103 non-NULL flag
--     values — 62 of which are the bare-containment false positives. The §11 #13
--     ban governs the JSON feed exports, which are (type,value)-pure and carry no
--     `notes`; it does not govern the CSV full dump.
--   So D1 HAS shipped, in a published artifact. That does not change this
--   migration's scope — it changes whether an export regen is owed. Escalated on
--   the issue; the regen is NOT performed here.
--
-- Slot:      0055, allocated by DISPATCH CLAIM. Claim state at WRITE time, from
--            `python3 scripts/next_migration_slot.py` (full-range 0001..0074
--            claim scan, not `ls db/migrations/`):
--              0046 CLAIMED  MAC-574   0047 CLAIMED  MAC-598
--              0050 CLAIMED  MAC-608   0054 APPLIED  MAC-663 (highest on disk)
--              0055 free -> CLAIMED by MAC-691, this file, sole claimant
--            The one gap between those, freed by MAC-663's SLOT_RELEASE.md, is
--            deliberately NOT printed as a number here. A release retracts ONE
--            cited mention, so a fresh co-mention anywhere in the tree flips that
--            slot straight back to CONTESTED. Writing this header with the number
--            in it did exactly that, verified in `--verbose` output, and this is
--            the fix. Cite the release ledger, never the digits.
--            A slot verified at WRITE time is not verified at COMMIT time.
--            Re-scan before committing; `ls` answers *applied*, never *claimed*.
--            Re-scanned at commit time: this file holds 0055, next free is 0056,
--            and the released gap reads freed again.
--
-- schema_version: NOT bumped. Data-only, no DDL.
--
-- Scope:     D1 — exactly 62 rows. Every row is pinned on id AND its literal
--            `manufacturer` AND its literal flag value, so an id drift cannot
--            retarget a write. 63 rows fail the anchored predicate; the 63rd is
--            id=23042, whose flag value is the JSON literal `false`. `false` is
--            not a vendor-name claim and therefore cannot rest on an unanchored
--            substring hit, so it is deliberately OUT of scope. Naming it is the
--            point: an unexplained 63-vs-62 is what a silent truncation looks
--            like.
--            D2 — exactly 1 row, id=35700.
--
-- NOT in scope, stated so the omissions are not read as coverage:
--   * The GAIN arm. 7,236 ACTIVE rows carry no flag today whose manufacturer the
--     same anchored matcher WOULD flag. Writing them is a data-shape decision
--     with an owner: the flag's vendor pool has no ratified provenance (it is
--     read back off the column it corrects). Measured, reported, HELD.
--   * The 33 sibling rows carrying D2's exact generic-class-plus-mismatched-cite
--     pattern (34 including 35700). The issue asks for the COUNT, not the fix.
--     Reported on the issue; escalated as a class remedy.
--   * 24 keepers rest on a SHORT SINGLE TOKEN (MAC-542 §5), and at least two are
--     identity-wrong while being boundary-valid: id=17471 `Ring` on `Triple Ring
--     Technologies, Inc.` and id=4091 `Nest` on `NeST`. Boundary is necessary,
--     not sufficient. They satisfy this migration's acceptance property and are
--     left standing for adjudication rather than swept in unratified.
--   * `paired_identifier_id=35699` on the withdrawn row is left intact. Nothing
--     references 35700 via `paired_identifier_id` or `superseded_by` (verified,
--     0 rows), and the pointer records how the row arrived.
--
-- ACCEPTANCE PROPERTY (from the issue, stated as a property, not as an issue
-- status): no row carries `surveillance_vendor_flag` on the basis of an
-- unanchored substring hit, and a positive-control row whose manufacturer
-- genuinely contains a vendor token as a bounded word still keeps its flag.
-- POST-2 is the negative arm; POST-3 is the POSITIVE control and pins all 40
-- keepers by id AND literal flag value. A migration carrying only POST-2 would
-- also pass if it had wiped the column.
--
-- THE MATCHER LIVES IN CODE, NOT IN THIS FILE. `db/vendor_flag.py` (MAC-691) is
-- the derivation; it calls `db.entity_boundary.boundary_match` (MAC-585), which
-- exists precisely so there is exactly ONE implementation of this predicate. The
-- predicate is deliberately NOT re-expressed in SQL here: a second, hand-rolled
-- SQL approximation of token-boundary matching is how a repo ends up with four
-- call sites of one defect, which is what MAC-691 is. This file therefore pins
-- the matcher's OUTPUT (62 ids + 62 manufacturer literals + 62 flag literals)
-- rather than re-deriving it. `tests/test_vendor_flag.py` pins the matcher.
--
-- ASSERTION MECHANISM: `CREATE TEMP TABLE t(ok INTEGER CHECK (ok=1))` +
-- `INSERT ... SELECT CASE`. NOT `SELECT CASE WHEN ... THEN RAISE(ABORT,...)`:
-- SQLite rejects RAISE() outside a trigger-program with a PARSE ERROR.
--
-- THREE ARMS, because CHECK(ok=1) alone aborts only its own INSERT and lets the
-- CLI walk on to COMMIT — an artifact that reads as protected while writing
-- everything:
--   arm 1  `.bail on`                     — sqlite3 CLI only; a no-op under
--                                           conn.executescript()
--   arm 2  CHECK(ok=1) on each guard      — surfaces the failure
--   arm 3  `(SELECT COUNT(*) FROM _mac691_go) = 1` on EVERY canonical write —
--          portable, fail-closed under ANY runner. If any precondition failed,
--          `_mac691_go` is EMPTY and both writes match zero rows.
-- Verify the apply by a POST-STATE QUERY, never by `$?` — a sqlite3 exit code is
-- not a safety signal (it is 1 both when it stopped and when it committed
-- through failed guards).
--
-- Expected post-state, as a DELTA against pre (an absolute rots the moment a
-- co-tenant lane applies anything):
--   rows with a non-NULL surveillance_vendor_flag : (pre) - 62
--   active rows                                   : (pre) - 1
--   active equipment_class_code rows              : (pre) - 1
--   self-loop (withdrawn) rows                    : (pre) + 1
--   notes invalid-JSON rows                       : (pre) + 0
--   feed (JSON exports)                           : + 0 / - 0  — `notes` is not
--        emitted into the (type,value)-pure JSON exports, and the one withdrawn
--        row is `device_category='unknown'`, already held out by §11 #13.
--
-- STAGE ONLY — no push, no tag. The board reserves all pushes (MAC-424).
-- ============================================================================
.bail on

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- Pre-state snapshot. Every post-condition is a DELTA against this row.
CREATE TEMP TABLE _pre AS SELECT
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)                       AS active,
    (SELECT COUNT(*) FROM identifiers WHERE notes IS NOT NULL AND json_valid(notes)
       AND json_extract(notes,'$.surveillance_vendor_flag') IS NOT NULL)                 AS flagged,
    (SELECT COUNT(*) FROM identifiers WHERE identifier_type='equipment_class_code'
       AND superseded_by IS NULL)                                                        AS ecc,
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by = id)                          AS selfloop,
    (SELECT COUNT(*) FROM identifiers WHERE notes IS NOT NULL AND NOT json_valid(notes))  AS badjson;

-- ---------------------------------------------------------------- D1 scope
-- The matcher's output, pinned on all THREE columns. Generated from
-- `db/vendor_flag.py::sweep_existing_flags`, not hand-transcribed.
CREATE TEMP TABLE _mac691_expect (id INTEGER, mfr TEXT, flag TEXT);
INSERT INTO _mac691_expect (id, mfr, flag) VALUES
       (1129,'Nestlab AS','Nest'),
       (1268,'MAVERICK ENERGY SOLUTIONS INTERNATIONAL,INC','AVer'),
       (1293,'ElitEngineering LLC','Ring'),
       (1304,'Beijing Spring Creation Technology Co., Ltd.','Ring'),
       (1500,'INEPRO Metering B.V.','Ring'),
       (1511,'PUDSEY DIAMOND ENGINEERING LIMITED','Ring'),
       (1550,'Avedis Zildjian Co.','DJI'),
       (1585,'WaveRF, Corp.','AVer'),
       (1628,'Global Satellite Engineering','Ring'),
       (1684,'Yeasound (Xiamen) Hearing Technology Co., Ltd','Ring'),
       (1755,'NINGBO FOTILE KITCHENWARE CO., LTD.','Tile'),
       (1759,'Soundwave Hearing, LLC','Ring'),
       (1910,'Shenzhen Openhearing Tech CO., LTD .','Ring'),
       (1940,'Technocon Engineering Ltd.','Ring'),
       (1950,'MAXON INDUSTRIES, INC.','Axon'),
       (1963,'Embedded Engineering Solutions LLC','Ring'),
       (2001,'Tactile Engineering, Inc.','Tile'),
       (2096,'Shindengen Electric Manufacturing Co., Ltd.','Ring'),
       (2103,'OTC engineering','Ring'),
       (2130,'TECHTICS ENGINEERING B.V.','Ring'),
       (2162,'Sonova Consumer Hearing GmbH','Ring'),
       (2209,'JDRF Electromag Engineering Inc','Ring'),
       (2269,'Duke Manufacturing Co','Ring'),
       (2329,'Saxonar GmbH','Axon'),
       (2374,'KCCS Mobile Engineering Co., Ltd.','Ring'),
       (2388,'PS Engineering, Inc.','Ring'),
       (2552,'Lichtvision Engineering GmbH','Ring'),
       (2597,'Hx Engineering, LLC','Ring'),
       (2613,'Elimo Engineering Ltd','Ring'),
       (2659,'Mequonic Engineering, S.L.','Ring'),
       (2700,'NUANCE HEARING LTD','Ring'),
       (2741,'KiteSpring Inc.','Ring'),
       (2755,'Yukai Engineering Inc.','Ring'),
       (2809,'IMI Hydronic Engineering International SA','Ring'),
       (2812,'COWBELL ENGINEERING CO.,LTD.','Ring'),
       (2821,'KOZO KEIKAKU ENGINEERING Inc.','Ring'),
       (2861,'Boehringer Ingelheim Vetmedica GmbH','Ring'),
       (3021,'Paradox Engineering SA','Ring'),
       (3037,'maxon motor ltd.','Axon'),
       (3069,'Unlimited Engineering SL','Ring'),
       (3254,'IDIBAIX enginneering','Ring'),
       (3577,'P.I.Engineering','Ring'),
       (3636,'Hearing Lab Technology','Ring'),
       (3747,'Foundation Engineering LLC','Ring'),
       (3824,'Averos FZCO','AVer'),
       (3871,'Igarashi Engineering','Ring'),
       (3920,'Teenage Engineering AB','Ring'),
       (4116,'Société des Produits Nestlé S.A.','Nest'),
       (4141,'Favero Electronics Srl','AVer'),
       (4187,'North Pole Engineering','Ring'),
       (4321,'Areus Engineering GmbH','Ring'),
       (4398,'Microtronics Engineering GmbH','Ring'),
       (4435,'Nestlé Nespresso S.A.','Nest'),
       (4547,'Wille Engineering','Ring'),
       (4565,'Maveric Automation LLC','AVer'),
       (4647,'Murata Manufacturing Co., Ltd.','Ring'),
       (4721,'Above Average Outcomes, Inc.','AVer'),
       (4771,'Starkey Hearing Technologies','Ring'),
       (4820,'GN Hearing A/S','Ring'),
       (4848,'A&D Engineering, Inc.','Ring'),
       (4850,'GN Hearing','Ring'),
       (4858,'Stonestreet One, LLC','Nest');

-- The mutation scope, defined ONCE by the same selector every write uses. A row
-- enters only if id, manufacturer AND current flag all still match the measured
-- state, and its notes is parseable JSON.
CREATE TEMP TABLE _scope AS
  SELECT i.id FROM identifiers i JOIN _mac691_expect e ON e.id = i.id
   WHERE i.manufacturer = e.mfr
     AND i.notes IS NOT NULL AND json_valid(i.notes)
     AND json_extract(i.notes,'$.surveillance_vendor_flag') = e.flag;

-- The POSITIVE control: the 40 rows whose flag is anchored-TRUE and must survive
-- this migration byte-identical.
CREATE TEMP TABLE _mac691_keep (id INTEGER, flag TEXT);
INSERT INTO _mac691_keep (id, flag) VALUES
       (1549,'Hikvision'),
       (1744,'Axis Communications'),
       (2848,'Chipolo'),
       (2872,'DJI'),
       (3397,'Tile'),
       (3725,'Honeywell'),
       (3781,'Motorola'),
       (4091,'Nest'),
       (4101,'Xiaomi'),
       (4262,'Samsung'),
       (4315,'Bosch'),
       (4533,'Nest'),
       (4569,'Google'),
       (4734,'Google'),
       (4837,'Samsung'),
       (4884,'Parrot'),
       (4942,'Motorola'),
       (5520,'Honeywell'),
       (5894,'Bosch'),
       (6319,'Anduril'),
       (6352,'Honeywell'),
       (6457,'Bosch'),
       (6680,'Yuneec'),
       (6685,'Honeywell'),
       (6883,'Autel'),
       (7091,'Xiaomi'),
       (7226,'Bosch'),
       (8056,'Xiaomi'),
       (8294,'Autel'),
       (9070,'Xiaomi'),
       (9120,'Bosch'),
       (9204,'Bosch'),
       (12034,'Bosch'),
       (13043,'Honeywell'),
       (16564,'Bosch'),
       (17093,'Honeywell'),
       (17125,'Bosch'),
       (17462,'Samsung'),
       (17471,'Ring'),
       (18029,'Samsung');

-- PRE-1 FAIL: the D1 mutation scope is not exactly the 62 measured rows.
CREATE TEMP TABLE _mac691_pre_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_pre_1fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _scope) <> 62) THEN 0 ELSE 1 END;

-- PRE-2 FAIL: the whole flagged population is not the 103 this was measured
-- against, so a co-tenant lane has written the column since. An absolute is
-- correct HERE: it identifies the INPUT state. Deltas govern the post-conditions.
CREATE TEMP TABLE _mac691_pre_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_pre_2fail(ok) SELECT CASE WHEN ((SELECT flagged FROM _pre) <> 103) THEN 0 ELSE 1 END;

-- PRE-3 FAIL: the 40 positive-control rows do not all currently hold their
-- ratified flag value. Without this, POST-3 could pass vacuously on a column a
-- co-tenant already changed.
CREATE TEMP TABLE _mac691_pre_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_pre_3fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers i
    JOIN _mac691_keep k ON k.id = i.id
   WHERE i.notes IS NOT NULL AND json_valid(i.notes)
     AND json_extract(i.notes,'$.surveillance_vendor_flag') = k.flag) <> 40) THEN 0 ELSE 1 END;

-- PRE-4 FAIL: `_scope` and `_mac691_keep` intersect. They partition the flagged
-- set; an overlap would mean the migration is about to strip a keeper.
CREATE TEMP TABLE _mac691_pre_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_pre_4fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM _scope s
    JOIN _mac691_keep k ON k.id = s.id) <> 0) THEN 0 ELSE 1 END;

-- PRE-5 FAIL: the D2 row is not in the state the adjudication measured. Every
-- clause is part of the finding: the class value, the vendor, the cite page, and
-- the fact that the row is still active.
CREATE TEMP TABLE _mac691_pre_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_pre_5fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE id = 35700 AND identifier = 'DTS' AND identifier_type = 'equipment_class_code'
     AND manufacturer = 'Parrot Automotive' AND source_url = 'https://fccid.io/2AG6I-DISCO'
     AND superseded_by IS NULL AND notes IS NOT NULL AND json_valid(notes)) <> 1) THEN 0 ELSE 1 END;

-- PRE-6 FAIL: the D2 justification moved. `DTS` must still be shared by more
-- than one manufacturer (generic), and must still be ABSENT from the row's own
-- source_excerpt (mismatched cite). Making the justification a precondition
-- means a changed basis stops the write. The absence test is a plain LIKE
-- because `DTS` occurring ANYWHERE in the excerpt, bounded or not, is enough to
-- put the finding in doubt — the strict form of the check, not the convenient one.
CREATE TEMP TABLE _mac691_pre_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_pre_6fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(DISTINCT manufacturer) FROM identifiers
         WHERE identifier_type='equipment_class_code' AND identifier='DTS'
           AND manufacturer IS NOT NULL AND TRIM(manufacturer) <> '') < 2
    OR (SELECT COUNT(*) FROM identifiers
         WHERE id = 35700 AND source_excerpt LIKE '%DTS%') <> 0) THEN 0 ELSE 1 END;

-- PRE-7 FAIL: something already references 35700 as a successor or as a pair. A
-- withdrawal must not orphan a live pointer.
CREATE TEMP TABLE _mac691_pre_7fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_pre_7fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE superseded_by = 35700 OR paired_identifier_id = 35700) <> 0) THEN 0 ELSE 1 END;

-- PRE-8 FAIL: canonical is not the DB this was measured against.
CREATE TEMP TABLE _mac691_pre_8fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_pre_8fail(ok) SELECT CASE WHEN (
       (SELECT active   FROM _pre) <> 43089
    OR (SELECT ecc      FROM _pre) <> 683
    OR (SELECT selfloop FROM _pre) <> 246) THEN 0 ELSE 1 END;

-- THE GO GATE — `.bail on` ALONE IS NOT ENOUGH. It is a sqlite3 CLI dot-command
-- and a NO-OP under `sqlite3.Connection.executescript()`, which is how
-- `scripts/mac419_*`, `mac569_*` and `mac580_*` apply. Under those a failed
-- precondition aborts only its own INSERT and every write below then COMMITS.
-- So the gate is STRUCTURAL: `_mac691_go` holds exactly one row IFF all eight
-- preconditions passed, and every write carries
-- `(SELECT COUNT(*) FROM _mac691_go) = 1`. If any failed, it is EMPTY and both
-- writes match zero rows.
-- MAC-691 GO GATE FAIL: one or more preconditions PRE-1..PRE-8 did not pass
CREATE TEMP TABLE _mac691_go (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_go(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM _mac691_pre_1fail) = 1
   AND (SELECT COUNT(*) FROM _mac691_pre_2fail) = 1
   AND (SELECT COUNT(*) FROM _mac691_pre_3fail) = 1
   AND (SELECT COUNT(*) FROM _mac691_pre_4fail) = 1
   AND (SELECT COUNT(*) FROM _mac691_pre_5fail) = 1
   AND (SELECT COUNT(*) FROM _mac691_pre_6fail) = 1
   AND (SELECT COUNT(*) FROM _mac691_pre_7fail) = 1
   AND (SELECT COUNT(*) FROM _mac691_pre_8fail) = 1) THEN 1 ELSE 0 END;

-- ================================================== WRITE A — D1, 62 rows
-- The flag is set to JSON `null`, NOT removed. ~18,200 sibling rows already
-- carry `"surveillance_vendor_flag": null`, so `null` is the established
-- "no flag" shape and removing the key would make these 62 the odd ones out.
-- notes is merged BY PROPERTY via json_set — never text-suffix concatenation
-- (CP39 showed what a text suffix does to a JSON column).
-- `withdrawn_value` reads the ORIGINAL blob: json_set evaluates its arguments
-- before assigning, so this records what was there, not what replaces it.
-- Re-running this file is a no-op: `_scope` requires the OLD flag value to
-- still be present, so a second run selects zero rows.
UPDATE identifiers
   SET notes = json_set(notes,
         '$.surveillance_vendor_flag', NULL,
         '$.mac691_flag_correction', json_object(
             'issue', 'MAC-691',
             'withdrawn_value', json_extract(notes,'$.surveillance_vendor_flag'),
             'basis', 'bare-containment hit: no surface form of the vendor entity-boundary-matches this row''s own manufacturer',
             'matcher', 'db/vendor_flag.py -> db.entity_boundary.boundary_match (MAC-585)',
             'defect_class', 'MAC-542 boundary-valid-is-not-identity-valid, fourth call site'))
 WHERE id IN (SELECT id FROM _scope)
   AND (SELECT COUNT(*) FROM _mac691_go) = 1;

-- ================================================== WRITE B — D2, 1 row
-- Withdrawal WITHOUT successor: PROJECT_BIBLE.md §4 superseded_by tri-semantic —
-- `superseded_by = id` is the explicit "no successor exists" signal, paired with
-- the §8.2 demotion to confidence 0 so the row is never surfaced as active and
-- never points at an inappropriate successor. There is no successor here: the
-- claim is not a mis-stated fact with a correct version, it is a class code the
-- cite never evidenced.
UPDATE identifiers
   SET superseded_by = id,
       confidence = 0,
       notes = json_set(notes, '$.mac691_withdrawal', json_object(
             'issue', 'MAC-691',
             'verdict', 'WITHDRAWN without successor',
             'reason_1_generic_class', 'DTS (Digital Transmission System) is a generic FCC equipment class carried by 7 distinct manufacturers in this corpus; it identifies a transmitter category, not a device or a vendor',
             'reason_2_cite_mismatch', 'the cited page https://fccid.io/2AG6I-DISCO is about FCC ID 2AG6I-DISCO. The string DTS does not appear in the row''s own source_excerpt, so the row fails cite-paste on its own terms',
             'sibling_pattern', '34 rows in the active equipment_class_code unknown cohort carry this same generic-class-plus-mismatched-cite pattern, 33 besides this one; reported on MAC-691, not remedied here',
             'paired_identifier_id', 'left intact at 35699 — it records how the row arrived; nothing references 35700'))
 WHERE id = 35700
   AND identifier = 'DTS'
   AND identifier_type = 'equipment_class_code'
   AND manufacturer = 'Parrot Automotive'
   AND superseded_by IS NULL
   AND (SELECT COUNT(*) FROM _mac691_go) = 1;

-- ================================================== POST-CONDITIONS

-- POST-1 FAIL: the flagged population did not fall by exactly 62.
CREATE TEMP TABLE _mac691_post_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_post_1fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE notes IS NOT NULL AND json_valid(notes)
     AND json_extract(notes,'$.surveillance_vendor_flag') IS NOT NULL)
   <> (SELECT flagged FROM _pre) - 62) THEN 0 ELSE 1 END;

-- POST-2 FAIL (acceptance property, NEGATIVE arm): a scope row still carries a
-- flag, or did not receive its provenance marker.
CREATE TEMP TABLE _mac691_post_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_post_2fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE id IN (SELECT id FROM _scope)
          AND json_extract(notes,'$.surveillance_vendor_flag') IS NOT NULL) <> 0
    OR (SELECT COUNT(*) FROM identifiers WHERE json_valid(notes)
          AND json_extract(notes,'$.mac691_flag_correction.issue') = 'MAC-691') <> 62)
   THEN 0 ELSE 1 END;

-- POST-3 FAIL (acceptance property, POSITIVE control): a genuine bounded-word
-- keeper lost its flag, or its flag value changed. This is the arm that stops a
-- migration which "passes" by wiping the column.
CREATE TEMP TABLE _mac691_post_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_post_3fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers i
    JOIN _mac691_keep k ON k.id = i.id
   WHERE i.notes IS NOT NULL AND json_valid(i.notes)
     AND json_extract(i.notes,'$.surveillance_vendor_flag') = k.flag) <> 40) THEN 0 ELSE 1 END;

-- POST-4 FAIL: the out-of-scope 63rd row (id=23042, flag `false`) was touched.
CREATE TEMP TABLE _mac691_post_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_post_4fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE id = 23042 AND json_valid(notes)
     AND json_extract(notes,'$.surveillance_vendor_flag') = 0
     AND json_extract(notes,'$.mac691_flag_correction') IS NULL) <> 1) THEN 0 ELSE 1 END;

-- POST-5 FAIL: D2 did not land as a withdrawal-without-successor.
CREATE TEMP TABLE _mac691_post_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_post_5fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE id = 35700 AND superseded_by = 35700 AND confidence = 0
     AND json_valid(notes)
     AND json_extract(notes,'$.mac691_withdrawal.issue') = 'MAC-691') <> 1) THEN 0 ELSE 1 END;

-- POST-6 FAIL: the active population did not fall by exactly 1, or the active
-- equipment_class_code population did not. Catches a write that scored rows
-- outside the ratified scope.
CREATE TEMP TABLE _mac691_post_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_post_6fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)
         <> (SELECT active FROM _pre) - 1
    OR (SELECT COUNT(*) FROM identifiers WHERE identifier_type='equipment_class_code'
          AND superseded_by IS NULL) <> (SELECT ecc FROM _pre) - 1
    OR (SELECT COUNT(*) FROM identifiers WHERE superseded_by = id)
         <> (SELECT selfloop FROM _pre) + 1) THEN 0 ELSE 1 END;

-- POST-7 FAIL: json_set corrupted a notes blob anywhere. Swept table-wide as a
-- DELTA, not over the mutation scope only — a json_set bug that damaged an
-- unrelated row would be invisible to a scope-local check.
CREATE TEMP TABLE _mac691_post_7fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_post_7fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE notes IS NOT NULL AND NOT json_valid(notes))
         <> (SELECT badjson FROM _pre)
    OR (SELECT COUNT(*) FROM identifiers WHERE id IN (SELECT id FROM _scope)
          AND json_valid(notes)) <> 62) THEN 0 ELSE 1 END;

-- POST-8 FAIL: adjudication moved on a scope row. device_category, manufacturer
-- and confidence are out of scope for WRITE A and must be untouched — the
-- correction withdraws a claim about the vendor, it does not re-rate the row.
CREATE TEMP TABLE _mac691_post_8fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac691_post_8fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers i
    JOIN _mac691_expect e ON e.id = i.id
   WHERE i.manufacturer = e.mfr AND i.superseded_by IS NULL
     AND i.device_category = 'unknown' AND i.confidence >= 70) <> 62) THEN 0 ELSE 1 END;

DROP TABLE _pre;
DROP TABLE _scope;
DROP TABLE _mac691_expect;
DROP TABLE _mac691_keep;
DROP TABLE _mac691_go;
DROP TABLE _mac691_pre_1fail;
DROP TABLE _mac691_pre_2fail;
DROP TABLE _mac691_pre_3fail;
DROP TABLE _mac691_pre_4fail;
DROP TABLE _mac691_pre_5fail;
DROP TABLE _mac691_pre_6fail;
DROP TABLE _mac691_pre_7fail;
DROP TABLE _mac691_pre_8fail;
DROP TABLE _mac691_post_1fail;
DROP TABLE _mac691_post_2fail;
DROP TABLE _mac691_post_3fail;
DROP TABLE _mac691_post_4fail;
DROP TABLE _mac691_post_5fail;
DROP TABLE _mac691_post_6fail;
DROP TABLE _mac691_post_7fail;
DROP TABLE _mac691_post_8fail;
COMMIT;
-- ============================================================================
-- STAGE ONLY — no push, no tag. The board reserves all pushes (MAC-424).
-- `exports/` is NOT regenerated by this migration. The published
-- `exports/argus_export.csv` carries the 62 false flags and is now stale in a
-- direction that FIXES a defect; the regen decision is escalated on MAC-691.
-- ============================================================================
