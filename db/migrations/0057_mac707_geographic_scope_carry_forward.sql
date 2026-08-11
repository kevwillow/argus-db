-- ============================================================================
-- Script:    0057_mac707_geographic_scope_carry_forward.sql
-- Issue:     MAC-707 (carrier) / MAC-706 (spec + measurement).
-- Status:    STAGE ONLY — no push, no tag. The board reserves all pushes
--            (MAC-424 standing rule).
--
-- Purpose:   Repair the one non-information-preserving fold in `mig-0049`.
--            0049 folded 565 -> 35666 (`ble_local_name` 'FS Ext Battery').
--            The folded row carried `geographic_scope='US'`; the survivor
--            carries NULL. `db/validation/export_lynceus.py` treats an empty
--            scope as passing the standard feed and FAILING the
--            high-confidence feed:
--
--                raw = (row.geographic_scope or "").strip()
--                if not raw or raw == "unknown":
--                    return not is_high_confidence
--
--            (`_passes_geographic_scope`, lines 1054-1056 at the HEAD this was
--            written against.) So the fold silently removed the
--            `ble_local_name` MATCH PATH for 'FS Ext Battery' from
--            `argus_export_high_confidence.json`.
--
-- Slot:      0057, allocated by DISPATCH CLAIM after a direct working-tree read.
--
--            NOT 0056. The MAC-707 dispatch claimed 0056 on the basis that the
--            highest file on disk is `0055_mac691...`. That read is of the
--            APPLIED directory only, and `ls` answers *applied*, never
--            *claimed*. `db/migrations/_drafts/` holds two live dispatch claims:
--                0050 — MAC-608 (`0050_mac608_watchguard_alias_entity_conflation.sql.draft`)
--                0056 — MAC-705 (`0056_mac705_dead_sha_drop_in_canonical_notes.sql.draft`,
--                       header: "Slot: 0056, allocated by DISPATCH CLAIM",
--                       awaiting CEO ratification)
--            Taking 0056 would have silently collided with MAC-705. 0055's own
--            header asserts "next free is 0056" — true when 0055 was written,
--            false now. A slot verified at write time is not a slot verified at
--            COMMIT time; this file re-queried at write time and takes 0057.
--            Every gap below the highest applied file is spoken for: 0046
--            (MAC-574), 0047 (MAC-598), 0050 (MAC-608), 0056 (MAC-705), plus
--            the gap `operator_review/MAC-663/SLOT_RELEASE.md` freed. None is
--            reusable here. That last one is cited through its release ledger
--            and deliberately NOT by its digits: `next_migration_slot.py`
--            matches digits, not intent, so a RELEASED slot is re-CONTESTED by
--            merely printing its number — even in a header describing the
--            release. An earlier draft of this line did exactly that and flipped
--            it back to `CONTESTED unresolved`. Caught by re-running the scanner
--            AFTER writing the header, which is the only time it can be caught.
--
-- schema_version: NOT bumped. Data-only, no DDL — same disposition as 0049.
--            The ledger currently tops out at version 35 (`0045_mac580`,
--            applied 2026-07-29 03:48:57) and does NOT record 0048, 0049,
--            0051, 0052, 0054 or 0055, even though their effects are present
--            in the data. Adding a row for 0057 alone would make the ledger
--            MORE misleading, not less: it would read as though 0057 followed
--            0045 directly. The gap is real and is carried to a named
--            successor issue rather than half-repaired here.
--
-- Value provenance — INHERITED, NOT INVENTED:
--            'US' is carried forward from row 565, the row 0049 superseded.
--            PRE-3 makes that row's existence and value a precondition, so if
--            the basis ever moves the write stops instead of inventing a scope.
--            Stored format is a bare scalar, not a JSON array: the active
--            distribution is NULL 35,473 / 'global' 6,141 / 'US' 1,471 /
--            'US-CBP' 2 / 'GB' 1. PRE-4 pins that the scalar form is still in
--            use so a format migration cannot be silently overwritten.
--
-- Scope:     EXACTLY ONE row updated (id 35666), one column (geographic_scope)
--            plus a provenance tag in `notes`. No supersession topology change,
--            no confidence change, no category change.
--
-- Expected effect on the feeds (stated as a DELTA, and as a REGENERATION
-- delta — the committed `exports/` artifact is stale and is NOT a witness for
-- post-fix state; it carries `_meta.exported_at = 2026-07-28T16:34:51Z` and
-- `source_record_count = 43116` against a current active count of 43,088, and
-- it predates every migration after 0045. Regeneration at the final SHA is
-- MAC-612's):
--   argus_export.json (standard)        : + 0 / - 0  — a NULL scope already
--        passes the standard feed, so this row was never missing from it.
--   argus_export_high_confidence.json   : + 1 / - 0. Stated as a DELTA only.
--        NO absolute entry total is asserted here, deliberately. The committed
--        artifact's 481 belongs to a stale export (see the paragraph above) and
--        is not a count of what canonical would emit today; measured against
--        canonical at this migration's basis the same gate reckons 500 -> 501
--        unique emitted keys, and neither absolute is authoritative because the
--        whole-file passes (emitted-key collision fold, CP51 ssid NOCASE dedup,
--        MAC-45 `_reconcile`) run only in a real regeneration, which is
--        MAC-612's. The DELTA is the claim; the absolute is MAC-612's to state.
--        The added entry is the `ble_local_name` match path for
--        'FS Ext Battery'. The `ssid_pattern` match path for the same string is
--        a DIFFERENT emitted key, is carried by active row 562
--        (geographic_scope='US', confidence 70), and was never lost. The
--        accurate claim is that the ble_local_name PATH returns, NOT that the
--        pattern 'FS Ext Battery' returns.
--   active row count                    : + 0 / - 0
--
-- Why this is not blocked by the CP19 source_type gate: both 565 and 35666 are
-- `source_type='crowdsourced'`, which IS in `EXCLUDED_SOURCE_TYPES`, so the
-- high-confidence feed would drop them regardless of scope — EXCEPT that both
-- clear the CP39 Flock-hunt carve-out on `source_url`
-- (`colonelpanichacks/flock-you` for 35666). Verified before writing this, so
-- the scope repair is not inert.
--
-- ASSERTION MODEL — three arms, because no single one aborts reliably:
--   1. `.bail on`            — stops the CLI on the FIRST error.
--   2. `CHECK (ok = 1)` on a TEMP table — a failing CHECK aborts the INSERT
--      statement, NOT the migration. On its own the CLI walks on to COMMIT.
--   3. a per-write `(SELECT COUNT(*) FROM _mac707_go) = 1` arm in the UPDATE's
--      WHERE clause — so even if arms 1 and 2 are both defeated, the write
--      itself cannot land unless every precondition held.
--   Post-conditions are DELTAS against `_pre`, never pinned absolute totals,
--   so this file does not go stale the moment canonical's total moves.
-- ============================================================================
.bail on

PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

-- Pre-state snapshot. Every post-condition below is a DELTA against this row.
CREATE TEMP TABLE _pre AS SELECT
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)              AS active,
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL
       AND geographic_scope = 'US')                                             AS us_active,
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL
       AND geographic_scope IS NULL)                                            AS null_active,
    (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NOT NULL)          AS edges,
    (SELECT COUNT(*) FROM identifiers WHERE notes IS NOT NULL
       AND NOT json_valid(notes))                                               AS badjson;

-- Full pre-image of the column being written. A path-set or scope-local check
-- is vacuous against an in-path sweep: if the UPDATE somehow scored extra rows,
-- a check that only looks at id 35666 would still print PASS. Only a
-- pre-image baseline over EVERY row can fire. POST-6 diffs against this.
CREATE TEMP TABLE _pre_scope AS SELECT id, geographic_scope FROM identifiers;

-- ---------------------------------------------------------------------------
-- PRECONDITIONS. Each is phrased so that ok=0 means THE FINDING MOVED.
-- ---------------------------------------------------------------------------

-- PRE-1 FAIL: canonical is not the DB this repair was measured against.
CREATE TEMP TABLE _mac707_pre_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_pre_1fail(ok) SELECT CASE WHEN (
       (SELECT active      FROM _pre) <> 43088
    OR (SELECT us_active   FROM _pre) <> 1471
    OR (SELECT null_active FROM _pre) <> 35473) THEN 0 ELSE 1 END;

-- PRE-2 FAIL: the survivor is not in the state MAC-706 measured. Every column
-- named in the measurement is part of the predicate, not just the one being
-- written — a row whose confidence or category has since moved is a different
-- adjudication and must stop the write.
CREATE TEMP TABLE _mac707_pre_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_pre_2fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE id = 35666
     AND identifier_type  = 'ble_local_name'
     AND identifier       = 'FS Ext Battery'
     AND device_category  = 'alpr'
     AND manufacturer     = 'Flock Safety'
     AND severity         = 'high'
     AND source_type      = 'crowdsourced'
     AND confidence       = 85
     AND geographic_scope IS NULL
     AND superseded_by    IS NULL
     AND notes IS NOT NULL AND json_valid(notes)) <> 1) THEN 0 ELSE 1 END;

-- PRE-3 FAIL: the provenance row is gone or no longer says 'US'. This is what
-- makes the written value INHERITED rather than invented. 565 must still be the
-- row 0049 folded into 35666, and must still carry the scope being carried.
CREATE TEMP TABLE _mac707_pre_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_pre_3fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE id = 565
     AND identifier_type  = 'ble_local_name'
     AND identifier       = 'FS Ext Battery'
     AND geographic_scope = 'US'
     AND superseded_by    = 35666) <> 1) THEN 0 ELSE 1 END;

-- PRE-4 FAIL: the storage format moved. If `geographic_scope` had been
-- migrated to JSON arrays, writing the bare scalar 'US' would be a format
-- regression that every scalar-shaped assertion here would still pass. Pinned
-- as a population fact, not a single-row fact.
CREATE TEMP TABLE _mac707_pre_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_pre_4fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers
         WHERE superseded_by IS NULL AND geographic_scope = 'US') < 1000
    OR (SELECT COUNT(*) FROM identifiers
         WHERE geographic_scope IS NOT NULL
           AND json_valid(geographic_scope)
           AND json_type(geographic_scope) = 'array') <> 0) THEN 0 ELSE 1 END;

-- PRE-5 FAIL: the write predicate is not single-valued. Guards N:M fan-out —
-- "count + one illustrative row" is exactly how 0049's own defect survived.
CREATE TEMP TABLE _mac707_pre_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_pre_5fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE id = 35666 AND geographic_scope IS NULL
     AND superseded_by IS NULL) <> 1) THEN 0 ELSE 1 END;

-- ARM 3. `_mac707_go` holds exactly one row iff EVERY precondition above holds.
-- The single UPDATE carries `(SELECT COUNT(*) FROM _mac707_go) = 1`, so the
-- write cannot land on a moved basis even if `.bail` and the CHECKs are both
-- defeated. Deliberately re-derived from the source predicates rather than
-- from the _pre_Nfail tables: reading those back would assert that the
-- assertions ran, not that the conditions hold.
CREATE TEMP TABLE _mac707_go AS
SELECT 1 AS ok WHERE
       (SELECT active      FROM _pre) = 43088
   AND (SELECT us_active   FROM _pre) = 1471
   AND (SELECT null_active FROM _pre) = 35473
   AND (SELECT COUNT(*) FROM identifiers
         WHERE id = 35666 AND identifier_type = 'ble_local_name'
           AND identifier = 'FS Ext Battery' AND device_category = 'alpr'
           AND manufacturer = 'Flock Safety' AND confidence = 85
           AND geographic_scope IS NULL AND superseded_by IS NULL
           AND notes IS NOT NULL AND json_valid(notes)) = 1
   AND (SELECT COUNT(*) FROM identifiers
         WHERE id = 565 AND geographic_scope = 'US'
           AND superseded_by = 35666) = 1;

-- ---------------------------------------------------------------------------
-- THE WRITE. One row, one column, plus a provenance tag.
-- `json_set` merges by property — never a text-suffix concat, which is how a
-- prior CP39 write corrupted a notes blob.
-- ---------------------------------------------------------------------------
UPDATE identifiers
   SET geographic_scope = 'US',
       notes = json_set(notes, '$.mac707_scope_carry', json_object(
                 'issue',          'MAC-707',
                 'spec_issue',     'MAC-706',
                 'carried_from',   565,
                 'value',          'US',
                 'basis',          'inherited from the row mig-0049 superseded; not invented',
                 'fold_migration', '0049_mac611_mac570_duplicate_emitted_key_supersession.sql',
                 'defect',         'fold dropped geographic_scope, removing the ble_local_name match path from the high-confidence feed',
                 'not_a_promotion', 1))
 WHERE id = 35666
   AND identifier_type  = 'ble_local_name'
   AND identifier       = 'FS Ext Battery'
   AND geographic_scope IS NULL
   AND superseded_by    IS NULL
   AND (SELECT COUNT(*) FROM _mac707_go) = 1;

-- ---------------------------------------------------------------------------
-- POST-CONDITIONS. Deltas against `_pre`. These are deliberately NOT a
-- restatement of the UPDATE: asserting "the row I just set to 'US' is 'US'"
-- mirrors the transform and is vacuous. What is asserted is the POPULATION
-- effect and the ABSENCE of collateral change.
-- ---------------------------------------------------------------------------

-- POST-1 FAIL: the write did not land, or landed without its provenance tag.
-- The tag is part of the deliverable: an inherited value with no record of what
-- it was inherited from is indistinguishable from an invented one.
CREATE TEMP TABLE _mac707_post_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_post_1fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE id = 35666
     AND geographic_scope = 'US'
     AND json_valid(notes)
     AND json_extract(notes,'$.mac707_scope_carry.issue')        = 'MAC-707'
     AND json_extract(notes,'$.mac707_scope_carry.carried_from') = 565) <> 1)
  THEN 0 ELSE 1 END;

-- POST-2 FAIL: the scope populations did not move by exactly one row, in
-- exactly the two expected buckets. DELTA, not a pinned total.
CREATE TEMP TABLE _mac707_post_2fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_post_2fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL
          AND geographic_scope = 'US')   <> (SELECT us_active   FROM _pre) + 1
    OR (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL
          AND geographic_scope IS NULL)  <> (SELECT null_active FROM _pre) - 1)
  THEN 0 ELSE 1 END;

-- POST-3 FAIL: this migration changed the active population or the supersession
-- topology. It must do neither — it is a column carry-forward, not a fold.
-- 565 must still point at 35666; 35666 must still be active.
CREATE TEMP TABLE _mac707_post_3fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_post_3fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)
         <> (SELECT active FROM _pre)
    OR (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NOT NULL)
         <> (SELECT edges  FROM _pre)
    OR (SELECT COUNT(*) FROM identifiers
         WHERE id = 565 AND superseded_by = 35666) <> 1) THEN 0 ELSE 1 END;

-- POST-4 FAIL: `json_set` corrupted a notes blob ANYWHERE. Swept table-wide as
-- a delta, not over the mutation scope — a json_set bug that damaged an
-- unrelated row is invisible to a scope-local check.
CREATE TEMP TABLE _mac707_post_4fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_post_4fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers WHERE notes IS NOT NULL
          AND NOT json_valid(notes)) <> (SELECT badjson FROM _pre)) THEN 0 ELSE 1 END;

-- POST-5 FAIL: a column outside the declared scope moved on the target row.
-- Confidence, category, type, identifier and manufacturer are all out of scope.
CREATE TEMP TABLE _mac707_post_5fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_post_5fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers
   WHERE id = 35666
     AND identifier_type = 'ble_local_name' AND identifier = 'FS Ext Battery'
     AND device_category = 'alpr' AND manufacturer = 'Flock Safety'
     AND severity = 'high' AND source_type = 'crowdsourced'
     AND confidence = 85 AND superseded_by IS NULL) <> 1) THEN 0 ELSE 1 END;

-- POST-6 FAIL: any row OTHER than 35666 changed geographic_scope. Diffed
-- against the full pre-image, so an in-path sweep cannot hide. `IS NOT` is the
-- null-safe comparison; `<>` would silently skip every NULL-valued row, which
-- is 35,473 of them.
CREATE TEMP TABLE _mac707_post_6fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_post_6fail(ok) SELECT CASE WHEN ((SELECT COUNT(*)
     FROM identifiers i JOIN _pre_scope p ON p.id = i.id
    WHERE i.id <> 35666
      AND i.geographic_scope IS NOT p.geographic_scope) <> 0) THEN 0 ELSE 1 END;

-- POST-7 FAIL: the row count itself moved (insert or delete). Nothing in this
-- migration inserts or deletes; a change here means something else ran.
CREATE TEMP TABLE _mac707_post_7fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _mac707_post_7fail(ok) SELECT CASE WHEN (
       (SELECT COUNT(*) FROM identifiers)
         <> (SELECT COUNT(*) FROM _pre_scope)) THEN 0 ELSE 1 END;

COMMIT;
