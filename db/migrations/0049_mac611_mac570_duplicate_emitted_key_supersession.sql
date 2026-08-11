-- ============================================================================
-- Script:    0049_mac611_mac570_duplicate_emitted_key_supersession.sql
-- Status:    STAGED + APPLIED to the canonical db/argus.db in the same staged
--            commit that regenerates exports. STAGE ONLY — no push, no tag.
--            The board reserves all pushes (MAC-424 standing rule).
-- Slot:      0049. THREE prior slots are claimed-but-absent-from-disk, so a
--            "highest file on disk + 1" read collides with live claims:
--              0046 — MAC-574 (`operator_review/MAC-574/residue_write_plan.md:272`
--                     proposes `0046_mac574_t2_residue_drop.sql`, not yet written)
--              0047 — MAC-598 (`operator_review/MAC-598/PROOF.md:198` —
--                     "MAC-598 reserves `0047`")
--              0048 — MAC-537 (`operator_review/MAC-537/ingest_manifest/
--                     INGEST_DISPATCH.md:93` — "## 6. Migration slot — `0048`",
--                     landed in commit 825fc6a)
--            This file originally took 0048: at the time it was written that
--            slot was genuinely free, and MAC-537's claim landed in a CONCURRENT
--            commit minutes later. Re-queried at commit time and moved to 0049.
--            A slot verified at write time is not a slot verified at COMMIT time.
-- schema_version: NOT bumped (data-only supersession + one category
--            correction; no DDL). Stays at 35 (row 35 = 0045_mac580).
--
-- Purpose:   Remediate MAC-570 at canonical scope. The shipped Lynceus feed
--            emits 20 redundant entries under 12 shared emitted keys because
--            12 canonical (identifier_type, identifier) groups each carry more
--            than one ACTIVE row. Every group is folded to a single active row
--            using CP32 §9 <other_id> SUCCESSOR semantics.
--
-- Authority: MAC-570 triage (`operator_review/MAC-570/duplicate_triage.jsonl`,
--            12 lines) + `operator_review/MAC-570/gate_proposal.md`, both
--            CEO-ratified. MAC-611 implements; it does not re-derive the triage.
--            Brief law: `operator_review/BRIEF_STANDARDS.md` (standing, cited).
--
-- superseded_by SEMANTICS — stated explicitly per the tri-semantic rule
--            (NULL = active / <other_id> = successor / self-loop = withdrawn):
--            EVERY one of the 20 rows below uses <other_id> SUCCESSOR
--            semantics. There is NOT ONE self-loop in this migration. Each
--            superseded row has a surviving twin that carries the same
--            normalized identifier, so a withdrawal-without-successor
--            self-loop would be the wrong tri-state and would lose the
--            fold-target.
--
-- Scope:     20 rows superseded across 12 groups (32 rows in, 12 active out).
--            Group completeness re-queried at write time: for each of the 12
--            (identifier_type, identifier) values, the count of ACTIVE rows
--            equals the count named in the triage, and ZERO out-of-scope active
--            rows share any of the 12 values. The triage's "count + one
--            illustrative row" was re-run as an aggregate, not trusted.
--
--   Lane A — ATTRIBUTED_VS_NULL_VENDOR (8 groups, 9 rows superseded)
--        Both sides carry the same OUI / identifier_type / device_category;
--        the keeper is attributed from the IEEE primary registry
--        (https://standards-oui.ieee.org/oui/oui.csv) and the loser has
--        manufacturer NULL. An unattributed twin is order-dependent export
--        noise, not a distinct canonical identity.
--          22837 -> 438  (00:12:1c, PARROT SA)
--          22840 -> 457  (00:26:7e, PARROT SA)
--          22834 -> 447  (34:d2:62, SZ DJI TECHNOLOGY CO.,LTD)
--          22833 -> 421  (48:1c:b9, SZ DJI TECHNOLOGY CO.,LTD)
--          22832 -> 431  (60:60:1f, SZ DJI TECHNOLOGY CO.,LTD)
--          22838 -> 439  (90:03:b7, PARROT SA)
--          22831 -> 416  (90:3a:e6, PARROT SA)
--          22836 -> 416  (90:3a:e6, PARROT SA — 3-row group)
--          22839 -> 440  (a0:14:3d, PARROT SA)
--        Per the triage, the 90:3a:e6 group's ASD-STAN-reserved vs
--        Parrot-negative-fixture disagreement is preserved as REJECTED
--        provenance, not corroboration. NO §8.3 confidence uplift anywhere in
--        this lane — the keeper confidences are untouched.
--
--   Lane B — DEDUP_MISS (2 groups, 9 rows superseded)
--          565   -> 35666 (ble_local_name 'FS Ext Battery'; keeper conf 85)
--          36588, 36591, 36597, 36600, 36603, 36609, 36612, 36615 -> 23043
--                (ble_service_uuid f6ec37db-bda1-46ec-a43a-6d86de88561d;
--                 keeper conf 95). The eight lower rows are repeated
--                code-path observations of the same Hikvision HcpBluetoothServer
--                constant, NOT an independent-source basis. §8.3 selects the
--                highest-confidence row; no uplift is proposed or applied.
--
--   Lane C — CATEGORY_CONTRADICTION (2 groups, 2 rows superseded + recategorized)
--          22908 -> 22771 (ssid_exact 'Flock')
--          22909 -> 22772 (ssid_exact 'Flock-230503')
--        RULED FROM SOURCE, not by confidence / recency / averaging. Both
--        `alpr` rows contradict their OWN stored evidence. Cite-paste of
--        identifiers.source_excerpt at write time, byte-exact:
--          id 22908: "SSID string 'Flock' device=Raven Gunshot Detection (NVS
--                     fallback when LTE unavailable); OVERLAPS Argus
--                     identifiers.id=560 (ssid_pattern 'Flock', conf 60). NEW:
--                     this is exact-string evidence as a lite…"
--          id 22909: "SSID string 'Flock-230503' device=Raven Gunshot Detection
--                     (NVS fallback - secondary);"
--        The trailing `…` on 22908 is an upstream ingest truncation artifact.
--        It is NOT a MAC-570 defect and is deliberately NOT repaired here (per
--        the MAC-611 dispatch); the operative clause survives intact.
--        `device_category` is corrected to `gunshot_detect` on the superseded
--        row as well as folded, so the archived row no longer carries a claim
--        its own cite refutes. Confidence stays 85 on both sides — the two
--        cites are the same upstream project, so this is correction + dedup,
--        NOT independent corroboration and NOT a §8.3 uplift.
--
-- CONFIDENCE — deliberate deviation from mig-0037 / mig-0040 precedent:
--        those migrations set `confidence = 0` on withdrawn rows. This one does
--        NOT touch confidence on ANY row. The ratified dispositions say "leave
--        confidence at 85" / "leave confidence unchanged" and never instruct a
--        confidence change on the superseded side; `superseded_by IS NOT NULL`
--        already removes the row from the active set, so zeroing confidence
--        would be a second, uninstructed mutation that destroys the prior-band
--        signal. Called out here so the board can strike this choice explicitly
--        rather than discover it.
--
-- json_valid SWEEP over the mutation scope (run before writing this file):
--        Lane A (9 rows) + Lane B (9 rows) = 18 rows, ALL json_valid(notes) = 1.
--        Lane C (22908, 22909): json_valid(notes) = 0 — BOTH carry a CP39
--        text suffix appended after the JSON object:
--            ' | cp39_conf_lift:65->85 (Flock-hunt source carve-out — sid=41 …)'
--        `json_set` on those values does not return NULL, it raises
--        "malformed JSON" and would abort this transaction. So Lane C writes NO
--        notes key at all — a documented carve-out, not a silent skip. Its
--        provenance lives in this header and in
--        `operator_review/MAC-611/PROOF.md`. Repairing the CP39 suffix is a
--        separate, separately ratified change (see MAC-611 hand-back) and is
--        explicitly out of scope here: byte-rewriting a corrupt notes column to
--        attach audit metadata is a worse trade than an documented gap.
--        NOTE: 9 of the 12 KEEPER rows also carry CP39-suffixed notes
--        (438, 457, 447, 421, 431, 439, 440, 22771, 22772), which is why no
--        provenance is merged into keepers either — the audit key goes on the
--        superseded side, matching mig-0037 / mig-0040.
--
-- Fan-out: re-queried at write time — 0 rows reference any of the 20 via
--        `superseded_by`, and 0 via `paired_identifier_id`.
--
-- Reversibility: to revert a Lane A/B row: `superseded_by = NULL` and remove
--        the `$.mac611_supersession` key. To revert a Lane C row:
--        `superseded_by = NULL, device_category = 'alpr'`. No row is deleted;
--        no confidence is altered; every cite is retained (§11 #1).
--        Backup taken before apply (integrity_check ok):
--        /home/kev/argus-backups/argus.db.mac611_pre_mig0049_20260729T045417Z.bak
--        source sha256 89b9ccc18f3fb201796b2844aa4f6875ba03b82901b4be3ebf43463e7b0bb832
--
-- Re-apply safety: every UPDATE pins `superseded_by IS NULL`, and the strict
--        pre-guard requires EXACTLY 20 active targets — a second run finds 0
--        and CHECK(ok=1) fails, rolling the whole transaction back with zero
--        mutation.
--        CORRECTION (MAC-661, 2026-08-11): until this commit that sentence was
--        FALSE, and so was the "(all-or-nothing)" label on the pre-condition
--        guard below. `CHECK(ok=1)` aborts only the offending INSERT — not the
--        transaction and not the script — and `sqlite3 db < file` does not stop
--        on error. The guard printed to stderr and every UPDATE below then
--        committed anyway. The claim is true only because of the `.bail on` and
--        the per-write gate added below; it was never true of the idiom alone.
--        Left in place rather than deleted so the retraction is not orphaned.
-- ============================================================================

-- `.bail on` IS LOAD-BEARING, NOT COSMETIC — MAC-661.
--
-- `sqlite3 db < file` does not stop on error by default, and the assertion
-- idiom used below (`CREATE TEMP TABLE t(ok INTEGER CHECK (ok = 1))` +
-- `INSERT ... SELECT CASE`) raises a CHECK-constraint failure that aborts ONLY
-- the offending INSERT. Without this line a FAILED PRECONDITION prints one line
-- to stderr and then the 13 UPDATEs below run and COMMIT — which is strictly
-- worse than having no precondition at all, because the artifact reads as
-- protected. Not theoretical: MAC-642 hit the identical exposure in its own
-- draft and reproduced it empirically (`operator_review/MAC-642/PROOF.md` §6.2),
-- and this file's own fail-closed behaviour is proven in
-- `operator_review/MAC-661/PROOF.md` — cell D applies this migration IN FULL on
-- top of a deliberately failed PRE-2 with this line removed.
--
-- `.bail on` is a sqlite3 CLI dot-command and binds the CLI apply path only. It
-- is a no-op under any client that does not parse dot-commands, which is why
-- every UPDATE below ALSO carries `(SELECT COUNT(*) FROM _mig0049_pre) = 1` as
-- a second, SQL-level arm. A failed pre-guard leaves that temp table empty, so
-- the writes match zero rows even where this line is ignored or stripped. The
-- two arms are proven independently in the PROOF (cells C and C2).
.bail on

BEGIN TRANSACTION;

-- ---- apply-time baseline capture -------------------------------------------
-- Captured BEFORE any UPDATE so post-conditions (6) and (8) can assert a DELTA
-- against this run's own starting state instead of a number pinned from the
-- snapshot the file was authored against.
--
-- Why this exists (CEO finding, 2026-07-30): (8) originally read
-- `COUNT(*) WHERE superseded_by IS NULL = 43104`, i.e. 43124 - 20 measured at
-- write time. MAC-537's ingest then landed, canonical moved to 43160 active,
-- and the CHECK failed — the migration aborted inside its own transaction with
-- zero collateral. It failed safe, but it failed. An absolute total is a
-- correctness claim about every OTHER writer's behaviour, which this migration
-- has no business asserting; the only thing it should promise is its own delta.
--
-- Neither number below is load-bearing any more. Recorded for provenance only:
--   at write time      43124 active -> 43104 expected
--   at 2026-07-30      43160 active -> 43140 expected
CREATE TEMP TABLE _mig0049_baseline AS
  SELECT (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL) AS active_before;

-- Per-row confidence baseline over the full 32-row scope. Post-condition (6)
-- promises the exact (id, confidence) MULTISET is unchanged; asserting that
-- needs the per-row values, not an aggregate. See (6) for why the previous
-- `SUM(confidence) = 2550` did not implement the promise it was written under.
CREATE TEMP TABLE _mig0049_conf_before AS
  SELECT id, confidence FROM identifiers
   WHERE id IN (565,35666,23043,36588,36591,36597,36600,36603,36609,
                36612,36615,438,22837,457,22840,447,22834,421,22833,
                431,22832,439,22838,416,22831,22836,440,22839,22771,
                22908,22772,22909);

-- ---- strict pre-condition guard (all-or-nothing) ---------------------------
-- "all-or-nothing" is a claim about the ENFORCEMENT MECHANISM, not about this
-- CASE expression. What makes it true is `.bail on` above plus the
-- `(SELECT COUNT(*) FROM _mig0049_pre) = 1` gate carried by each of the 13
-- UPDATEs. On its own, a failing CHECK here aborts this INSERT and nothing
-- else. See the MAC-661 correction in the header.
-- (1) exactly 20 active target rows,
-- (2) exactly 12 active keeper rows,
-- (3) both Lane C rows still carry the contradicted 'alpr' category,
-- (4) all 18 Lane A/B rows still have valid-JSON notes — this is the guard that
--     makes the json_set calls below safe, and it is NOT a restatement of them,
-- (5) both Lane C rows still have INVALID-JSON notes: if the CP39 suffix has
--     been repaired upstream since this file was written, the notes carve-out
--     below is no longer the right call and this migration must be revisited
--     rather than silently skipping provenance it could now have written.
CREATE TEMP TABLE _mig0049_pre (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0049_pre(ok) SELECT CASE WHEN (
      (SELECT COUNT(*) FROM identifiers
        WHERE id IN (22837,22840,22834,22833,22832,22838,22831,22836,22839,
                     565,36588,36591,36597,36600,36603,36609,36612,36615,
                     22908,22909)
          AND superseded_by IS NULL) = 20
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id IN (438,457,447,421,431,439,416,440,35666,23043,22771,22772)
          AND superseded_by IS NULL) = 12
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id IN (22908,22909) AND device_category = 'alpr') = 2
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id IN (22837,22840,22834,22833,22832,22838,22831,22836,22839,
                     565,36588,36591,36597,36600,36603,36609,36612,36615)
          AND json_valid(notes) = 1) = 18
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id IN (22908,22909) AND json_valid(notes) = 0) = 2
) THEN 1 ELSE 0 END;

-- ==== Lane A — ATTRIBUTED_VS_NULL_VENDOR (9 rows -> 8 keepers) ===============
-- One UPDATE per successor so each fold target is legible in the diff.

UPDATE identifiers SET superseded_by = 438,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',438,'lane','A_attributed_vs_null_vendor',
    'collision_class','ATTRIBUTED_VS_NULL_VENDOR',
    'emitted_key','oui|00:12:1c','argus_record_id','b5dd85cdbeb03302',
    'reason','Same OUI/identifier_type/device_category as the surviving row 438, but manufacturer NULL. The IEEE primary registry attributes 00:12:1C to PARROT SA, so the unattributed twin is order-dependent export noise, not a distinct canonical identity.',
    'keeper_cite','https://standards-oui.ieee.org/oui/oui.csv',
    'keeper_cite_paste','MA-L,00121C,PARROT SA,174 Quai de Jemmapes Paris  FR 75010 ',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 22837 AND identifier_type = 'oui' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

UPDATE identifiers SET superseded_by = 457,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',457,'lane','A_attributed_vs_null_vendor',
    'collision_class','ATTRIBUTED_VS_NULL_VENDOR',
    'emitted_key','oui|00:26:7e','argus_record_id','0e6ef5183f5a20a6',
    'reason','Same OUI/identifier_type/device_category as the surviving row 457, but manufacturer NULL. The IEEE primary registry attributes 00:26:7E to PARROT SA, so the unattributed twin is order-dependent export noise, not a distinct canonical identity.',
    'keeper_cite','https://standards-oui.ieee.org/oui/oui.csv',
    'keeper_cite_paste','MA-L,00267E,PARROT SA,174 Quai de Jemmapes Paris  FR 75010 ',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 22840 AND identifier_type = 'oui' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

UPDATE identifiers SET superseded_by = 447,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',447,'lane','A_attributed_vs_null_vendor',
    'collision_class','ATTRIBUTED_VS_NULL_VENDOR',
    'emitted_key','oui|34:d2:62','argus_record_id','99696ff1930ae2c6',
    'reason','Same OUI/identifier_type/device_category as the surviving row 447, but manufacturer NULL. The IEEE primary registry attributes 34:D2:62 to SZ DJI TECHNOLOGY CO.,LTD, so the unattributed twin is order-dependent export noise, not a distinct canonical identity.',
    'keeper_cite','https://standards-oui.ieee.org/oui/oui.csv',
    'keeper_cite_paste','MA-L,34D262,"SZ DJI TECHNOLOGY CO.,LTD","DJI Sky City, No55 Xianyuan Road, Nanshan District Shenzhen Guangdong CN 518057 "',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 22834 AND identifier_type = 'oui' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

UPDATE identifiers SET superseded_by = 421,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',421,'lane','A_attributed_vs_null_vendor',
    'collision_class','ATTRIBUTED_VS_NULL_VENDOR',
    'emitted_key','oui|48:1c:b9','argus_record_id','2fde1a991a0cd103',
    'reason','Same OUI/identifier_type/device_category as the surviving row 421, but manufacturer NULL. The IEEE primary registry attributes 48:1C:B9 to SZ DJI TECHNOLOGY CO.,LTD, so the unattributed twin is order-dependent export noise, not a distinct canonical identity.',
    'keeper_cite','https://standards-oui.ieee.org/oui/oui.csv',
    'keeper_cite_paste','MA-L,481CB9,"SZ DJI TECHNOLOGY CO.,LTD","DJI Sky City, No55 Xianyuan Road, Nanshan District Shenzhen Guangdong CN 518057 "',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 22833 AND identifier_type = 'oui' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

UPDATE identifiers SET superseded_by = 431,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',431,'lane','A_attributed_vs_null_vendor',
    'collision_class','ATTRIBUTED_VS_NULL_VENDOR',
    'emitted_key','oui|60:60:1f','argus_record_id','8f6d7a48b568c851',
    'reason','Same OUI/identifier_type/device_category as the surviving row 431, but manufacturer NULL. The IEEE primary registry attributes 60:60:1F to SZ DJI TECHNOLOGY CO.,LTD, so the unattributed twin is order-dependent export noise, not a distinct canonical identity.',
    'keeper_cite','https://standards-oui.ieee.org/oui/oui.csv',
    'keeper_cite_paste','MA-L,60601F,"SZ DJI TECHNOLOGY CO.,LTD","DJI Sky City, No55 Xianyuan Road, Nanshan District Shenzhen Guangdong CN 518057 "',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 22832 AND identifier_type = 'oui' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

UPDATE identifiers SET superseded_by = 439,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',439,'lane','A_attributed_vs_null_vendor',
    'collision_class','ATTRIBUTED_VS_NULL_VENDOR',
    'emitted_key','oui|90:03:b7','argus_record_id','3680762fce7effc7',
    'reason','Same OUI/identifier_type/device_category as the surviving row 439, but manufacturer NULL. The IEEE primary registry attributes 90:03:B7 to PARROT SA, so the unattributed twin is order-dependent export noise, not a distinct canonical identity.',
    'keeper_cite','https://standards-oui.ieee.org/oui/oui.csv',
    'keeper_cite_paste','MA-L,9003B7,PARROT SA,174 Quai de Jemmapes Paris  FR 75010 ',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 22838 AND identifier_type = 'oui' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

-- 90:3a:e6 is the only 3-row group in Lane A. Both losers fold to 416. The
-- ASD-STAN-reserved (22831) vs Parrot-negative-fixture (22836) disagreement is
-- retained as REJECTED provenance — it is not corroboration and supports
-- neither a second active row nor a §8.3 uplift.
UPDATE identifiers SET superseded_by = 416,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',416,'lane','A_attributed_vs_null_vendor',
    'collision_class','ATTRIBUTED_VS_NULL_VENDOR',
    'emitted_key','oui|90:3a:e6','argus_record_id','1c452b196c10dab1',
    'reason','Same OUI/identifier_type/device_category as the surviving row 416, but manufacturer NULL. The IEEE primary registry attributes 90:3A:E6 to PARROT SA. This row and 22836 disagree with each other (ASD-STAN-reserved vs Parrot negative fixture); that disagreement is retained as REJECTED provenance, not corroboration.',
    'keeper_cite','https://standards-oui.ieee.org/oui/oui.csv',
    'keeper_cite_paste','MA-L,903AE6,PARROT SA,174 Quai de Jemmapes Paris  FR 75010 ',
    'group_disposition','3-row group: 22831 and 22836 both fold to 416',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 22831 AND identifier_type = 'oui' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

UPDATE identifiers SET superseded_by = 416,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',416,'lane','A_attributed_vs_null_vendor',
    'collision_class','ATTRIBUTED_VS_NULL_VENDOR',
    'emitted_key','oui|90:3a:e6','argus_record_id','1c452b196c10dab1',
    'reason','Same OUI/identifier_type/device_category as the surviving row 416, but manufacturer NULL. The IEEE primary registry attributes 90:3A:E6 to PARROT SA. This row and 22831 disagree with each other (Parrot negative fixture vs ASD-STAN-reserved); that disagreement is retained as REJECTED provenance, not corroboration.',
    'keeper_cite','https://standards-oui.ieee.org/oui/oui.csv',
    'keeper_cite_paste','MA-L,903AE6,PARROT SA,174 Quai de Jemmapes Paris  FR 75010 ',
    'group_disposition','3-row group: 22831 and 22836 both fold to 416',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 22836 AND identifier_type = 'oui' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

UPDATE identifiers SET superseded_by = 440,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',440,'lane','A_attributed_vs_null_vendor',
    'collision_class','ATTRIBUTED_VS_NULL_VENDOR',
    'emitted_key','oui|a0:14:3d','argus_record_id','e6f69467b726c22c',
    'reason','Same OUI/identifier_type/device_category as the surviving row 440, but manufacturer NULL. The IEEE primary registry attributes A0:14:3D to PARROT SA, so the unattributed twin is order-dependent export noise, not a distinct canonical identity.',
    'keeper_cite','https://standards-oui.ieee.org/oui/oui.csv',
    'keeper_cite_paste','MA-L,A0143D,PARROT SA,174 Quai de Jemmapes Paris  FR 75010 ',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 22839 AND identifier_type = 'oui' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

-- ==== Lane B — DEDUP_MISS (9 rows -> 2 keepers) ==============================

UPDATE identifiers SET superseded_by = 35666,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',35666,'lane','B_dedup_miss',
    'collision_class','DEDUP_MISS',
    'emitted_key','ble_local_name|FS Ext Battery','argus_record_id','a2d37fb799db170f',
    'reason','Identical normalized identifier, identifier_type, manufacturer and device_category to the surviving row 35666. §8.3 selects the higher-confidence row (35666, conf 85) as canonical. Source independence was NOT adjudicated in the MAC-570 triage, so §11 #8 proposes no confidence uplift.',
    'keeper_cite','https://github.com/colonelpanichacks/flock-you/blob/64f9b9e7cf116b6c40af8d4def85e4eebc1f28f8/datasets/FS+Ext+Battery_20240530_105846.csv#L2',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id = 565 AND identifier_type = 'ble_local_name' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

-- Eight repeated observations of the SAME Hikvision HcpBluetoothServer code
-- path. Repetition of one code path is not an independent-source basis, so
-- §8.3 selects the highest-confidence row (23043, conf 95) with no drift.
UPDATE identifiers SET superseded_by = 23043,
  notes = json_set(notes, '$.mac611_supersession', json_object(
    'audit_issue','MAC-611','source_issue','MAC-570',
    'mig','0049_mac611_mac570_duplicate_emitted_key_supersession',
    'mechanism','cp32_sec9_superseded_with_successor_other_id',
    'successor_id',23043,'lane','B_dedup_miss',
    'collision_class','DEDUP_MISS',
    'emitted_key','ble_uuid|f6ec37db-bda1-46ec-a43a-6d86de88561d',
    'argus_record_id','d8262380d0f525b4',
    'reason','Same normalized identifier and identifier_type as the surviving row 23043, with identical Hikvision / cctv_camera attribution. All nine rows are repeated observations of one code path, not nine independent sources. §8.3 selects 23043 (conf 95); no §11 #8 uplift.',
    'keeper_cite','https://apkpure.com/p/com.hikvision.hikconnect',
    'keeper_cite_paste','UUID.fromString("f6ec37db-bda1-46ec-a43a-6d86de88561d") in sources/defpackage/ge1.java:299 — anchored in com.hikvision.hikconnect.devicesetting.bluetooth.HcpBluetoothServer',
    'group_disposition','9-row group: 36588,36591,36597,36600,36603,36609,36612,36615 all fold to 23043',
    'confidence_uplift','none','date','2026-07-29'))
WHERE id IN (36588,36591,36597,36600,36603,36609,36612,36615)
  AND identifier_type = 'ble_service_uuid' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

-- ==== Lane C — CATEGORY_CONTRADICTION (2 rows) ==============================
-- NO notes write: both rows carry a CP39 text suffix after their JSON object,
-- so json_valid(notes) = 0 and json_set would raise "malformed JSON" and abort
-- this transaction. See the json_valid sweep in the header. Provenance for
-- these two rows lives in this file and in operator_review/MAC-611/PROOF.md.

UPDATE identifiers SET superseded_by = 22771, device_category = 'gunshot_detect'
WHERE id = 22908 AND identifier_type = 'ssid_exact' AND identifier = 'Flock'
  AND device_category = 'alpr' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

UPDATE identifiers SET superseded_by = 22772, device_category = 'gunshot_detect'
WHERE id = 22909 AND identifier_type = 'ssid_exact' AND identifier = 'Flock-230503'
  AND device_category = 'alpr' AND superseded_by IS NULL
  AND (SELECT COUNT(*) FROM _mig0049_pre) = 1;

-- ---- strict post-condition guard -------------------------------------------
-- These predicates are deliberately NOT a restatement of the UPDATEs above. A
-- post-condition that mirrors its own transform ("count rows where
-- superseded_by = <the value I just set>") is vacuous. What is asserted here is
-- the EMERGENT property the migration exists to create, plus the invariants it
-- promised not to disturb:
--
--   (1) DEFECT CLASS GONE — across the 32 in-scope rows there is now no
--       (identifier_type, identifier) value with more than one ACTIVE row.
--       Expressed as a GROUP BY ... HAVING aggregate over the active set.
--   (2) Exactly 12 of the 32 remain active (one per group) — catches an
--       over-fold that leaves a group with zero survivors.
--   (3) Every one of the 12 named keepers is specifically the survivor.
--   (4) NOT ONE self-loop was created (tri-semantic correctness): zero rows in
--       scope have superseded_by = id.
--   (5) Both Lane C rows now read gunshot_detect.
--   (6) CONFIDENCE UNTOUCHED across the whole 32-row scope — the exact
--       multiset of (id, confidence) is unchanged from pre-apply, asserted as a
--       symmetric EXCEPT against the `_mig0049_conf_before` baseline plus a
--       cardinality pin. This previously read `SUM(confidence) = 2550`, which
--       did NOT implement the promise directly above it: a sum cannot see
--       compensating edits (-5 on one row, +5 on another nets to zero), and the
--       pinned total went stale the moment any in-scope confidence changed. The
--       comment asserted a multiset; the code checked an aggregate.
--   (7) notes stayed valid JSON on all 18 rows that were json_set, and the two
--       Lane C rows were left byte-untouched (still invalid JSON, i.e. not
--       silently rewritten).
--   (8) No collateral: the total active-row count fell by exactly 20, asserted
--       as `active_before - 20` against the `_mig0049_baseline` captured in this
--       same transaction. NOT a pinned absolute — see the baseline block for the
--       CEO finding that killed the pinned form.
CREATE TEMP TABLE _mig0049_post (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0049_post(ok) SELECT CASE WHEN (
      (SELECT COUNT(*) FROM (
          SELECT identifier_type, identifier
            FROM identifiers
           WHERE superseded_by IS NULL
             AND id IN (565,35666,23043,36588,36591,36597,36600,36603,36609,
                        36612,36615,438,22837,457,22840,447,22834,421,22833,
                        431,22832,439,22838,416,22831,22836,440,22839,22771,
                        22908,22772,22909)
           GROUP BY identifier_type, identifier
          HAVING COUNT(*) > 1)) = 0
  AND (SELECT COUNT(*) FROM identifiers
        WHERE superseded_by IS NULL
          AND id IN (565,35666,23043,36588,36591,36597,36600,36603,36609,
                     36612,36615,438,22837,457,22840,447,22834,421,22833,
                     431,22832,439,22838,416,22831,22836,440,22839,22771,
                     22908,22772,22909)) = 12
  AND (SELECT COUNT(*) FROM identifiers
        WHERE superseded_by IS NULL
          AND id IN (438,457,447,421,431,439,416,440,35666,23043,22771,22772)) = 12
  AND (SELECT COUNT(*) FROM identifiers
        WHERE superseded_by = id
          AND id IN (565,35666,23043,36588,36591,36597,36600,36603,36609,
                     36612,36615,438,22837,457,22840,447,22834,421,22833,
                     431,22832,439,22838,416,22831,22836,440,22839,22771,
                     22908,22772,22909)) = 0
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id IN (22908,22909) AND device_category = 'gunshot_detect') = 2
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id IN (22837,22840,22834,22833,22832,22838,22831,22836,22839,
                     565,36588,36591,36597,36600,36603,36609,36612,36615)
          AND json_valid(notes) = 1
          AND json_extract(notes, '$.mac611_supersession.successor_id') IS NOT NULL) = 18
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id IN (22908,22909) AND json_valid(notes) = 0) = 2
  AND (SELECT COUNT(*) FROM (
          SELECT id, confidence FROM _mig0049_conf_before
          EXCEPT
          SELECT id, confidence FROM identifiers
           WHERE id IN (565,35666,23043,36588,36591,36597,36600,36603,36609,
                        36612,36615,438,22837,457,22840,447,22834,421,22833,
                        431,22832,439,22838,416,22831,22836,440,22839,22771,
                        22908,22772,22909))) = 0
  AND (SELECT COUNT(*) FROM (
          SELECT id, confidence FROM identifiers
           WHERE id IN (565,35666,23043,36588,36591,36597,36600,36603,36609,
                        36612,36615,438,22837,457,22840,447,22834,421,22833,
                        431,22832,439,22838,416,22831,22836,440,22839,22771,
                        22908,22772,22909)
          EXCEPT
          SELECT id, confidence FROM _mig0049_conf_before)) = 0
  AND (SELECT COUNT(*) FROM _mig0049_conf_before) = 32
  AND (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL)
      = (SELECT active_before FROM _mig0049_baseline) - 20
) THEN 1 ELSE 0 END;

DROP TABLE _mig0049_pre;
DROP TABLE _mig0049_post;
DROP TABLE _mig0049_baseline;
DROP TABLE _mig0049_conf_before;

COMMIT;

-- Post-apply expected state:
--   Active identifiers 43124 -> 43104 (exactly −20).
--   12 canonical duplicate groups collapsed to 12 single active rows.
--   Lynceus feed: 981 entries / 961 distinct keys -> 961 entries, both the
--   argus_record_id index and the (pattern_type, pattern) index unique.
--   No schema change (schema_version stays 35). No confidence altered.
--   Every superseded row uses <other_id> SUCCESSOR semantics; zero self-loops.
