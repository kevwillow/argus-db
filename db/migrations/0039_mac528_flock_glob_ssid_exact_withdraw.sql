-- ============================================================================
-- Script:    0039_mac528_flock_glob_ssid_exact_withdraw.sql
-- Status:    STAGED — NOT APPLIED. Unlike 0037/0038 this migration is NOT
--            applied to canonical db/argus.db at write time. Per the CEO
--            directive on MAC-528 ("fold it into the next data cycle
--            v1.6.16 / Wave-6; do not open a release just for this") it is
--            held unapplied until the Wave-6 ingest cycle runs, so the
--            canonical DB does not drift a second un-shipped mutation ahead
--            of the armed v1.6.15 push gate (HEAD 599817c).
--            Slot 0039 is free — verified by direct working-tree read
--            (highest live = 0038, MAC-527; `git status --porcelain
--            db/migrations/` empty, so no sibling dispatch holds the slot).
--            schema_version is NOT bumped (data-only withdrawal; no DDL) —
--            stays at 33.
--
-- Purpose:   Withdraw ONE dead `ssid_exact` row: id 22910, identifier
--            `Flock-*` (device_category alpr, confidence 85, active).
--
-- Why it is dead (cite-paste, HEAD):
--   * `docs/engineering/PROJECT_BIBLE.md:179` — "`ssid_exact` matches by exact
--     equality".
--   * `db/validation/export_lynceus.py:96` — `"ssid_exact": "ssid",` — the row
--     is MAPPED (not dropped), so it reaches the feed.
--   The stored `*` is therefore a LITERAL character, not a glob. No SSID is
--   ever literally broadcast as `Flock-*`, so the row can never match. It is
--   inert, not a false positive: it ships in both feeds and fires on nothing.
--     - exports/argus_export.json:2831              "pattern": "Flock-*"
--     - exports/argus_export_high_confidence.json:1487  "pattern": "Flock-*"
--     - exports/argus_export.csv:26415              22910,Flock-*,ssid_exact,...
--
-- Root cause: the upstream source used `Flock-*` as GLOB SHORTHAND in prose.
--   The row's own source_excerpt reads: "SSID string 'Flock-*' device=
--   Picard/Bravo + Falcon/Sparrow/Flex LPR hotspot (Finding 29 ...)". The
--   shorthand was ingested verbatim as an exact identifier at MAC-104 /
--   Wave-A (`stage: mac110_stage2_promote`, `ratified_at_commit: 8de7309`).
--   Pre-existing since well before v1.6.14 — NOT a v1.6.15 regression.
--
-- Disposition: WITHDRAW (not retype). Retyping to `ssid_pattern` was
--   considered and REJECTED: `export_lynceus.py::_ssid_pattern_to_substring`
--   would reduce it to the bare substring `Flock-`, and under the Lynceus
--   0.9.2 case-insensitive substring matcher that is precisely the FP-magnet
--   class MAC-527 just withdrew (`flock` x3 -> "Schneeflocke"). The concrete
--   device SSID is already covered by `Flock-230503` (ids 22772, 22909).
--
-- Marquee-coverage guard (rule 3 — never drop the last identifier for a
--   marquee vendor). Flock Safety RETAINS, live-DB verified post-withdraw:
--     38 oui, 4 mac, 1 mac_range, 10 ble_local_name (incl. `Flock` id 564,
--     `Flock-` id 35668, `FS Ext Battery` ids 565/35666), 7 ble_service,
--     1 ble_service_uuid, 2 fcc_grantee_code, 11 alpr_model, and the FOUR
--     real `ssid_exact` rows:
--       22771 `Flock`        gunshot_detect
--       22772 `Flock-230503` gunshot_detect
--       22908 `Flock`        alpr
--       22909 `Flock-230503` alpr
--   Flock stays fully detectable. Coverage is UNCHANGED by this migration
--   because the withdrawn row contributed zero matches.
--
-- Notes column: NOT modified — deliberate, following the 0038 precedent
--   (§11 #17). Row 22910 carries CP39 text-suffix corruption:
--     `... "sources.id=41 + MAC-118 F2 ratification"} | cp39_conf_lift:65->85
--      (Flock-hunt source carve-out — sid=41 GainSec/..., extraction_runs.id=127)`
--   `json_valid(notes)` = 0 (swept pre-stage, this issue), so a `json_set`
--   merge copied from 0037 would abort the transaction with "malformed JSON".
--   Verified directly: `SELECT json_set(notes,'$.probe',1) FROM identifiers
--   WHERE id=22910;` -> `Error: stepping, malformed JSON`. 62 active rows
--   repo-wide carry this suffix. This migration file is the audit trail.
--
-- Fan-out: verified 0 rows reference 22910 via `superseded_by` or
--   `paired_identifier_id` (aggregate check, empty result).
--
-- Feed delta on apply (to be re-proven at v1.6.16 regen time, not asserted):
--   active identifiers  -1  (43,125 -> 43,124 off the v1.6.15 isolated base)
--   standard feed       -1  (979 -> 978)   -- ssid_exact is MAPPED
--   high-confidence     -1  (479 -> 478)   -- conf 85 >= 70 floor
--   behavioral            0  (132 unchanged)
--
-- DOWNSTREAM DOC OBLIGATION (binding, must land in the same v1.6.16 cycle):
--   `CHANGELOG.md:21` (v1.6.15, "Marquee coverage (binding)") cites
--   "`ssid_exact Flock-*`" as one of Flock's retained WORKING identifiers, as
--   does `docs/engineering/BIBLE_AMENDMENTS.md:6028` (CP52) and
--   `db/migrations/0038_...sql:71`. That citation is wrong — the row is inert.
--   The CONCLUSION still holds (Flock is covered by 38 oui + BLE + the four
--   real ssid_exact rows), so v1.6.15 is NOT blocked and the shipped prose is
--   NOT edited in place (apply-time-correction discipline). The v1.6.16
--   CHANGELOG must carry the correction and re-cite Flock's retained set as
--   `Flock` / `Flock-230503`.
--
-- Re-apply safety: the UPDATE pins `superseded_by IS NULL`; the strict
--   pre-guard aborts unless exactly the one expected active row is present.
-- ============================================================================
-- APPLY-TIME PRECONDITION (operator): back up the canonical DB first —
--   cp db/argus.db ~/argus-backups/argus.db.mac528_pre0039_$(date -u +%Y%m%dT%H%M%SZ).bak
-- ============================================================================

BEGIN TRANSACTION;

-- ---- strict pre-condition guard (all-or-nothing) --------------------------
-- Aborts the whole transaction unless EXACTLY 1 active target row is present
-- right now, with the exact value/type/category/confidence expected.
-- CHECK(ok=1) fails -> rollback.
CREATE TEMP TABLE _mig0039_pre (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0039_pre(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE id = 22910
     AND identifier = 'Flock-*'
     AND identifier_type = 'ssid_exact'
     AND device_category = 'alpr'
     AND confidence = 85
     AND superseded_by IS NULL
) = 1 THEN 1 ELSE 0 END;

-- ---- guard 2: the four real Flock ssid_exact rows must still be active ----
-- Marquee-coverage rule 3 enforced IN the transaction: refuse to withdraw the
-- glob row if the concrete Flock SSIDs are not there to carry coverage.
CREATE TEMP TABLE _mig0039_cov (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0039_cov(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE id IN (22771, 22772, 22908, 22909)
     AND identifier_type = 'ssid_exact'
     AND superseded_by IS NULL
) = 4 THEN 1 ELSE 0 END;

-- ==== Withdraw the dead glob row ==========================================
-- CP32 §9 "withdrawn without successor" self-loop: superseded_by = id.
-- confidence = 0 so the row drops out of the feed even for a consumer that
-- ignores superseded_by.
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 22910
    AND identifier = 'Flock-*'
    AND identifier_type = 'ssid_exact'
    AND superseded_by IS NULL;

-- ---- strict post-condition guard -----------------------------------------
-- 22910 withdrawn (self-loop, conf 0) AND the four real rows untouched.
CREATE TEMP TABLE _mig0039_post (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0039_post(ok) SELECT CASE WHEN (
  (SELECT COUNT(*) FROM identifiers
     WHERE id = 22910 AND superseded_by = 22910 AND confidence = 0) = 1
  AND
  (SELECT COUNT(*) FROM identifiers
     WHERE id IN (22771, 22772, 22908, 22909)
       AND superseded_by IS NULL AND confidence = 85) = 4
  AND
  (SELECT COUNT(*) FROM identifiers
     WHERE identifier_type = 'ssid_exact' AND identifier LIKE 'Flock%'
       AND superseded_by IS NULL) = 4
) THEN 1 ELSE 0 END;

DROP TABLE _mig0039_pre;
DROP TABLE _mig0039_cov;
DROP TABLE _mig0039_post;

COMMIT;
