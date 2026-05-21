# MAC-206 Phase 10d — direct-admission carve-out execution heartbeat (HALTED at pre-flight)

**Status:** HALT @ Phase 1 pre-flight · no mutations issued · MAC-206 → blocked, reassigned to CEO
**Parent:** MAC-205 (Phase 1 scoping — disposition β ratified)
**Grandparent:** MAC-184 (v1.4.1 Stage 1 integration umbrella)
**Branch:** `v1.4.1-integration-stage-1` @ `f02034e`
**Schema:** migrations applied through `0026`
**Run timestamp:** 2026-05-20
**Owner:** DBArchitect (agent 6c93a466)

Raw evidence: paste-not-cite (§11 #1) from `~/argus/db/argus.db`.

---

## 1. Headline (CEO read first)

Phase 1 pre-flight **HALTS** before any UPDATE. Two surface items, one is a hard blocker:

1. **Hard blocker — `identifiers.id=539` carries malformed `notes` JSON** (`{valid_json} | §8.3 freeform corroboration text`). The `json_patch()` and `json_extract()` functions raise `malformed JSON` on this row, which means the spec'd carve-out UPDATE will either error or silently skip id=539, breaking the `affected = 21` invariant. This is a **pre-existing** data-integrity defect, not caused by MAC-205/MAC-204 work, and was not caught by MAC-205 scoping because that pass used row-level SELECT, not `json_extract`.
2. **Soft surface — issue spec references `source_id` column on `identifiers`**; the actual schema (CREATE TABLE per `sqlite_master`) has no `source_id` FK — linkage is by `source_url ↔ sources.url`. Intent of the discipline guard is preserved by translating to `source_url IN (<flock_url>, <getac_url>)`. Disclosing per discipline; not a halt on its own.

**Provenance signatures on `sources.notes` for sid=13/14 are intact and match MAC-205 scoping verbatim** — `session_admission='wave_g_pre_v1'`, `authority_chain` and `mac_55_step_2_run` unchanged. The carve-out premise itself is sound; only the JSON-mutation mechanism is blocked on id=539.

---

## 2. Pre-flight steps executed (no DB mutations)

### 2a. Re-confirm scope at 21 rows + zero already-carved (paste-not-cite)

```
total identifiers WHERE id BETWEEN 533 AND 553            = 21
rows where source_url IN (flock_url, getac_url)           = 21  (all 21 match expected sids)
rows where json_extract(notes,'$.direct_admission_carve_out') IS NULL = 20 (one row errors)
rows already carved                                       = 0
rows with parseable notes JSON                            = 20  ← HALT TRIGGER
rows with un-parseable notes JSON                         = [539]
```

### 2b. Bypass-premise cross-checks (orphan confirmation unchanged since MAC-205)

```
raw_observations WHERE promoted_identifier_id BETWEEN 533 AND 553   = 0
raw_observations WHERE source_id = 13                                = 0
raw_observations WHERE source_id = 14                                = 0
extraction_runs  WHERE source_id = 13                                = 0
extraction_runs  WHERE source_id = 14                                = 0
identifiers WHERE id BETWEEN 533 AND 553 AND superseded_by IS NOT NULL = 0
```

Orphan premise + zero-supersession premise unchanged → no parallel landing since MAC-205.

### 2c. Source-side provenance signatures (per scoping doc §5 — these live on `sources.notes`, not `identifiers.notes`)

`sources` row for sid=13 (`Flock Safety FS Installer (com.flocksafety.hazyhiwire@2.4.0)`):

```
session_admission:            'wave_g_pre_v1'
admission_date_utc:           '2026-05-10'
extraction_session_reference: 'wave_g_pre_v1'
authority_chain:              'MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c (migration 0009 manufacturer_app enum)'
mac_55_step_2_run:            'pre-auth 3 mechanical promotion 2026-05-11'
eula_posture:                 'standard-RE-clause'
xapk_sha256:                  '8f0eea5ebb9727376b152260125dee05d3a657e8c9ca71a2cfa22cf4d94c6c6c'
apk_sha256:                   'b46ea409d43529de8320ab0dfcc69d27d1040381090d05009c00d5d865a1cda8'
version_code:                 '2004000'
```

`sources` row for sid=14 (`Getac BWC Viewer (com.getac.android.mobileappBWC@1.0.20)`):

```
session_admission:            'wave_g_pre_v1'
admission_date_utc:           '2026-05-10'
extraction_session_reference: 'wave_g_pre_v1'
authority_chain:              'MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c (migration 0009 manufacturer_app enum)'
mac_55_step_2_run:            'pre-auth 3 mechanical promotion 2026-05-11'
eula_posture:                 'standard-RE-clause'
xapk_sha256:                  NULL
apk_sha256:                   '6b6cc33f9033d04e129852f9f5a2985d784a1b989f6e89c828c229d2a1cb41af'
version_code:                 NULL
```

Both source-side signatures match MAC-205 scoping §5 verbatim. The carve-out's `authority_chain`, `mac_55_step_2_run`, and `session_admission='wave_g_pre_v1'` values are confirmed unchanged.

### 2d. PRAGMA / sqlite_master sanity (SAR-13 anchor)

`PRAGMA table_info(identifiers)` columns include `notes TEXT` and `source_url TEXT NOT NULL`. There is **no** `source_id` column on `identifiers`. The CREATE TABLE constraint set in `sqlite_master.sql` was read and exhibits the full enum vocabulary through CP31 (migration 0025) plus paired-identifier discipline. The carve-out is a `notes` JSON addition (no schema/enum change), so SAR-13 verification is a sanity step and passes.

### 2e. Backup

**Not taken** — the planned UPDATE was not executed. No mutations issued, so no backup required for this heartbeat. If CEO ratifies a recovery path that mutates data, a backup with sha256 will be the first step of that follow-up heartbeat.

---

## 3. The blocker — id=539 malformed `notes` (paste-not-cite)

```
sqlite> SELECT json_extract(notes,'$.session_admission')
   ...> FROM identifiers WHERE id=539;
Runtime error: malformed JSON

sqlite> SELECT notes FROM identifiers WHERE id=539;
```

Full blob (raw):

```
{"apk_package": "com.flocksafety.hazyhiwire", "apk_version": "2.4.0", "sub_band": "70-85 (manufacturer_app default SSID/BLE-local-name vendor-prefix)", "§8.3_boost_pending": "77→82 via B.3.4 second-source uplift in same transaction"} | §8.3 corroboration 2026-05-10: flock-back signatures.py:52 Penguin ble_local_name second-source uplift; +5 boost (77→82 below 85 sub-band ceiling); B.3.4 staged in raw_observations as provenance trail
```

Shape: a valid JSON object `{...}` followed by ` | §8.3 corroboration 2026-05-10: ...` plain-text suffix. SQLite refuses to parse the whole blob as JSON; the spec'd `UPDATE ... SET notes = json_patch(notes, ?)` will fail on this row.

**Diagnosis (provenance reconstruction):** the JSON object's `§8.3_boost_pending` key carries the same 77→82 / B.3.4 / second-source-uplift content; the plain-text suffix is a duplicate corroboration annotation appended by a non-canonical writer at or before MAC-205 scoping. Git-log search across `B.3.4`, `Penguin ble_local_name`, `77→82`, and `second-source uplift` finds **no commit** that wrote this suffix into the DB on `v1.4.1-integration-stage-1` (no `INSERT/UPDATE` SQL in tracked commits matches); the canonical §8.3 lift commit (`a6150dc` MAC-189) touched cellebrite/dji/parrot rows only. Most likely origin: an out-of-band `sqlite3` shell update made during Wave G or pre-MAC-189 that concatenated audit text onto an existing JSON blob rather than adding a JSON key.

The other 20 rows in [533,553] are parseable JSON with the expected `apk_package`/`apk_version`/`sub_band` shape and contain no `direct_admission_carve_out` key (counter = 0). They are eligible for the spec'd UPDATE as-is.

---

## 4. Halt-criterion mapping

The issue's halt criteria are:

| Criterion | Status |
|---|---|
| Pre-flight finds drift in any of the 21 rows' `notes.session_admission` or `authority_chain` | **TRIGGERED on id=539 by inability to read the keys at all** — strict reading is "those keys live on `sources.notes`, both intact"; spirit reading is "identifiers.notes structural drift blocks the planned `json_patch` mechanism" — spirit fires |
| Pre-flight finds nonzero `raw_observations.promoted_identifier_id BETWEEN 533 AND 553` | passed (0) |
| UPDATE affects any row count other than 21 (first run) or 0 (re-run) | **would trigger** at Phase 2 if executed — id=539 would either error the transaction or be silently skipped, breaking the 21-row invariant |
| Bible amendment downstream-consumer sweep finds any hard-requirer | not yet reached (Phase 3) |

---

## 5. CEO fork — recovery options (DBArchitect recommendation flagged)

### Option β.1 (recommended) — repair id=539 first as a sibling data-integrity step, then proceed with the 21-row carve-out

Pre-step: repair id=539 in a single audited `UPDATE` that preserves the freeform suffix as a new JSON-keyed field, then re-runs Phase 1 pre-flight (now 21/21 parseable) and proceeds to Phase 2 unchanged.

Proposed repair payload (NOT executed — awaiting CEO ratification):

```sql
UPDATE identifiers
SET notes = json_set(
    json_object(
        'apk_package', 'com.flocksafety.hazyhiwire',
        'apk_version', '2.4.0',
        'sub_band', '70-85 (manufacturer_app default SSID/BLE-local-name vendor-prefix)',
        '§8.3_boost_pending', '77→82 via B.3.4 second-source uplift in same transaction',
        'corroboration_note_2026_05_10',
            '§8.3 corroboration 2026-05-10: flock-back signatures.py:52 Penguin ble_local_name '
            'second-source uplift; +5 boost (77→82 below 85 sub-band ceiling); '
            'B.3.4 staged in raw_observations as provenance trail',
        'pre_carve_out_notes_repair', json_object(
            'repaired_at_utc', '2026-05-20',
            'repair_reason', 'pre-existing JSON+freeform-suffix concatenation blocked MAC-206 carve-out json_patch',
            'original_blob_sha256', '<computed at repair time>',
            'audit_ref', 'MAC-206 Phase 10d pre-flight'
        )
    ),
    '$.§8.3_boost_pending', '77→82 via B.3.4 second-source uplift in same transaction'
)
WHERE id = 539
  AND source_url = 'https://apkpure.com/flock-safety-device-app/com.flocksafety.hazyhiwire';
```

Pros: zero information loss (the freeform suffix is preserved verbatim in a new JSON key), 21/21 row parity restored, single small audited mutation, MAC-206 proceeds unchanged after.
Cons: a data mutation outside the original carve-out scope — needs CEO ratification before execution.

### Option β.2 — narrow carve-out to 20 rows; spin off id=539 as MAC-206a

Apply the carve-out to ids [533-538, 540-553] (20 rows), document id=539 as a separate data-integrity ticket scoped to: (a) JSON repair, (b) carve-out application after repair. Bible amendment proceeds against the 20-row enumeration; id=539 added via a follow-up amendment after MAC-206a closes.

Pros: keeps each ticket scoped to one concern.
Cons: bible amendment now references an inconsistent enumeration (20 of 21 rows carved, one pending); CP32 backlog gains an extra small ticket; "21 rows enumerated at MAC-205" language in the proposed bible invariant becomes wrong until MAC-206a closes.

### Option β.3 — defer MAC-206 entirely until a separate data-integrity sweep repairs all non-parseable `identifiers.notes` rows across the DB

Treat id=539 as one instance of a class of defects and audit the full table (`SELECT id FROM identifiers WHERE json_valid(notes)=0`) before any further `notes`-mutating work lands. MAC-206 → blocked-on-data-integrity-sweep.

Pros: discovers any other latent JSON-shape defects before they bite Phase 6+ work.
Cons: heaviest option; expands scope significantly; the carve-out is then gated on a much larger sweep.

**DBArchitect recommendation: β.1.** The defect is well-contained (1 row, well-understood shape, full information recoverable into a JSON-clean form), the repair is auditable in one UPDATE, and the MAC-206 carve-out proceeds with its discipline envelope intact afterward. β.3 is worth doing as a follow-up audit but should not block MAC-206 on its own.

A `json_valid` table-wide scan is cheap and I can run it as part of the CEO's β.1 ratification (i.e., disclose whether id=539 is the only defect or one of N, before executing the repair). I have not run it yet — that would be a read-only follow-up I can do under β.1 / β.3 dispositions without further authorization.

---

## 6. Non-mutation attestation

This heartbeat captures pre-flight reads only. No `UPDATE`, `INSERT`, `DELETE`, or migration was issued against `db/argus.db`. `git status` confirms only this new heartbeat file `_phase_10_schema_anomaly/carve_out_execution.md` is added.

---

## 7. Next-action handoff (run 1)

- **Status:** MAC-206 → blocked, reassigned to CEO
- **Unblock owner:** CEO (ratification of β.1 / β.2 / β.3)
- **Unblock action:** CEO comments on MAC-206 with chosen recovery path; DBArchitect resumes Phase 2 (or files MAC-206a) under that disposition
- **Bible amendment (Phase 3):** not drafted — gated on Phase 2 execution
- **Downstream-consumer sweep (Phase 3):** not yet performed — gated on bible-amendment drafting

---

# Run 2 — 2026-05-20 (β.1 ratified, Phase 1.5 scan executed → β.3 fork triggered)

**Status:** HALT @ Phase 1.5 · no mutations issued · MAC-206 → blocked, reassigning to CEO with β.3 fork request
**Branch:** `v1.4.1-integration-stage-1` @ `b1b0be2`
**Auth:** CEO ratified β.1 + Phase 1.5 read-only `json_valid(notes)=0` scan (MAC-206 comment 845582bd 2026-05-20T23:38)

## 1.5 Phase 1.5 scan — `json_valid(notes)=0` across `identifiers` / `sources` / `raw_observations`

SQL executed verbatim (read-only, no mutations):

```sql
SELECT id, COALESCE(source_url,'<n/a>'), length(notes), substr(notes, max(1, length(notes)-120))
FROM <table>
WHERE notes IS NOT NULL AND json_valid(notes)=0
ORDER BY id;
```

### 1.5.a `identifiers` — 112 defective rows

| shape | count | example id | sample head (≤200c, paste-not-cite) |
|---|---:|---:|---|
| `non-json-leading` (plain-text Phase-5 Step-4 follow-on² notes) | 106 | 413 | `Phase-5 Step-4 follow-on² (MAC-44). raw_observations.id=53738. SAR-9 disposition=accept via alias='Motorola Solutions'. candidate_manufacturer (raw)='Motorola Solutions Inc.'. §8.2 inferred 30–70; baseline 50…` |
| `json-truncated-or-noisy` (JSON + appended text, RAVEN_* services) | 5 | 554 | `{"raven_const_name": "RAVEN_GPS_SERVICE", "sub_band": "60-70 (crowdsourced Tier-3)", …}` then trailing free text `…Cat correction per §11 #1 (no fabrication). Conf 70->75 reflects Wave-A re-confirmation…` |
| `json-then-pipe-text` (id=539, the original blocker) | 1 | 539 | `{"apk_package": "com.flocksafety.hazyhiwire", "apk_version": "2.4.0", …, "§8.3_boost_pending": "77→82 via B.3.4…"} \| §8.3 corroboration 2026-05-10: …` |

id-range distribution: `[400-499] = 73 rows`, `[500-599] = 39 rows`. All 112 defective ids fall in the early single-digit and low-3-digit id range. Across the carve-out target window `[533,553]`, the **only defective row is id=539** — the other 20 target rows are JSON-clean.

### 1.5.b `sources` — 22 defective rows

| sid | length | head (paste-not-cite, ≤160c) |
|---:|---:|---|
| 7  | 1353 | `{"bulk_csv_byte_count": 8241406, "bulk_csv_sha256": "5cd60fbe…", "byte_count": 8241406, "content_sha256": …}` (tail: `…carry regulatory or official band independently per their own provenance.`) — JSON+text concat |
| 11 |   63 | `Wave-B2 cohort3_hak5_wayback (MAC-20) idempotency verify run 2.` — plain text |
| 12 |  164 | `Wave-A Phase-4 Step-2 A2 cohort extraction. Hybrid regex+LLM under claude_local. Disambig (…) applied at regex post-filter.` — plain text |
| 16 |  155 | `Wave-A repo registered 2026-05-11 via wave_a_ingest_to_raw_observations.py per MAC-63 board direction d3d1bbda (Path B). Slug: MaxwellDPS_Flock-You-Android` — plain text |
| 17 |  149 | (same template) `Slug: judcrandall_lookout.py` |
| 18 |  156 | (same template) `Slug: tesorrells_RF-Drone-Detection` |
| 19 |  157 | (same template) `Slug: opendroneid_opendroneid-core-c` |
| 20 |  154 | (same template) `Slug: colonelpanichacks_flock-you` |
| 21 |  152 | (same template) `Slug: colonelpanichacks_oui-spy` |
| 22 |  152 | (same template) `Slug: colonelpanichacks_Sky-Spy` |
| 23 |  148 | (same template) `Slug: alphafox02_DragonSync` |
| 24 |  146 | (same template) `Slug: seemoo-lab_AirGuard` |
| 25 |  155 | (same template) `Slug: opendroneid_receiver-android` |
| 26 |  158 | (same template) `Slug: opendroneid_wireshark-dissector` |
| 27 |  164 | (same template) `Slug: cyber-defence-campus_RemoteIDReceiver` |
| 28 |  146 | (same template) `Slug: proto17_dji_droneid` |
| 29 |  143 | (same template) `Slug: nixxxo_tagfinder` |
| 30 |  143 | (same template) `Slug: EFForg_rayhunter` |
| 31 |  155 | (same template) `Slug: eylonK14_IMSICatcherDetector` |
| 32 |  150 | (same template) `Slug: CellularPrivacy_AIMSICD` |
| 33 |  174 | (same template) `Slug: GainSec_Flock-Safety-Trap-Shooter-Sniffer-Alarm` |
| 34 |  266 | `Bluetooth SIG canonical machine-readable YAML for 16-bit company IDs. Public, no auth. Per CP15 §8.2 primary_registry sub-rule + §11 #8 tightening direct-issuer…` — plain text |

**Shape summary:** 1 `json+text-concat` (sid=7), 21 `plain-text-legacy` (sids 11, 12, 16–34). Neither sid=13 nor sid=14 (the MAC-206 carve-out source rows) is in the defective set — **the carve-out's source-side provenance reads stay clean**.

### 1.5.c `raw_observations` — 52,501 defective rows (35.9% of all rows with notes)

Aggregate: 39,241 on sid=1, 6,956 on sid=3, 6,303 on sid=2, 1 on sid=12. None on sid=13 / sid=14.

Shape: virtually all are postal-address strings (FCC/IEEE registration data) where the `notes` column was populated with raw address text during bulk ingest — e.g.:

```
rid=52746 sid=1 :: '100 CHEMIN DE BAILLOT MONTAUBAN  FR 82000'
rid=52728 sid=1 :: 'No.388 Ning Qiao Road,Jin Qiao Pudong Shanghai Shanghai   CN'
rid=52740 sid=1 :: '7760 France Ave S Suite 340 Bloomington MN US 55438'
rid=52905 sid=1 :: 'Via Lorenteggio nr. 240 Milan Italy IT 20147'
```

(Distribution by leading character: ~94 distinct categories, dominant ones are digit-prefixed street numbers and Latin/CJK street-name prefixes — full per-character tally available in `/tmp/phase15_classify.txt`. Not pasted here in full to keep heartbeat human-readable; sample above is representative.)

**Origin:** sids 1, 2, 3 are FCC EAS / IEEE OUI bulk-ingested registration sources where `notes` was populated with `address` field content from the upstream registry, not JSON metadata. This is **structural — the schema's `notes` column has always been used as free-form text on these sources**, not as JSON. The defects predate JSON-extract-based discipline.

Total `raw_observations` rows = 146,573; with `notes IS NOT NULL` = 146,346. So **35.9% of raw_observations.notes is non-JSON by long-standing convention**, not by corruption.

### 1.5.d Carve-out target window status (the only thing the MAC-206 mutation cares about)

| target ids | defective? |
|---|---|
| 533–538, 540–553 (20 rows) | clean — JSON-parseable |
| 539 (1 row) | defective — `json-then-pipe-text` (original blocker, recap from §3) |

The MAC-206 carve-out's 21-row target set is otherwise clean. Only the id=539 repair is in-scope-for-β.1.

## 1.5 Branch decision per CEO ratification rules

CEO branch rules from comment 845582bd:

> - **Only id=539** → execute Phase 1.6 sibling repair, then Phase 2 carve-out as spec'd. One heartbeat.
> - **id=539 + ≤5 additional rows of the same `{valid JSON} | <plain-text suffix>` shape on `identifiers`** → expand Phase 1.6, then Phase 2.
> - **>5 defects on `identifiers`, OR varied shapes that don't fit the template, OR any defects on `sources.notes` / `raw_observations.notes`** → HALT, surface, and we'll fork to β.3

**All three β.3 trigger conditions fire:**

- 112 defects on `identifiers` (vastly >5)
- Varied shapes (`plain-text-legacy` × 106, `json-truncated-or-noisy` × 5, `json-then-pipe-text` × 1)
- Defects on `sources.notes` (22) AND `raw_observations.notes` (52,501)

→ **HALT. Fork to β.3 per CEO ratification rule.** No mutations issued; MAC-206 remains in clean read-only state.

## 1.5 DBArchitect surface — β.3 framing question for CEO

The scan reveals that **most "defects" are not corruption — they are pre-JSON-convention plain-text notes** that have always been there:

- The 106 `Phase-5 Step-4 follow-on²` notes on identifiers were written as plain-text rationales (MAC-44 era) before the project adopted JSON-as-default for `notes`. Same for the 21 `Wave-A repo registered…` plain-text notes on sources (MAC-63 era) and effectively all of the 52,501 address strings on raw_observations sids 1/2/3 (FCC/IEEE bulk-ingest era).
- The only **true JSON corruption** — i.e., a row that was *intended* to carry structured JSON but ended up structurally broken — is id=539 (JSON-then-pipe-text concat) and the 5 RAVEN_* ids 554–558 (JSON-then-appended-text concat, similar shape). Plus possibly sid=7 (JSON-then-appended-text on sources).

**The β.3 fork is therefore not "repair 52,635 rows" — it is "decide whether the bible §11 invariant is supposed to apply to legacy plain-text notes at all, and if so, how much DB-wide repair work the v1.4.1 Stage 1 cycle is willing to absorb."**

Three sub-options for β.3 disposition (DBArchitect recommends β.3c):

### β.3a — full DB-wide JSON-repair sweep before MAC-206 proceeds

Scope: convert all 52,635 non-JSON `notes` blobs to JSON-clean form (either by wrapping plain text as `{"legacy_text_note": "..."}` or by a per-table convention). This is a **massive** undertaking: 52,501 raw_observations row UPDATEs, 106 identifiers wrapping operations, 21 sources wrapping operations, plus shape-classification work on the 6 likely-corruption rows (id=539, ids=554-558, sid=7).

Pros: makes bible §11 JSON-extract invariant globally true.
Cons: 52k+ row mutations on v1.4.1 Stage 1 is well outside the carve-out's scope; backup discipline non-trivial; downstream-consumer audit becomes a giant exercise; risks blocking v1.4.1 Stage 1 release for the duration.

### β.3b — repair only the 6 likely-corruption rows; accept legacy plain-text on the rest

Scope: repair id=539 + ids=554-558 (6 identifier rows) + sid=7 (1 source row). The 52,628 legacy plain-text rows are documented as "always-plain-text by convention" and the bible invariant is **read as not applying to them** (no change to bible language; reader's job to understand which rows the invariant targets).

Then resume MAC-206 carve-out on the 21 target rows as planned in β.1, since id=539 will be repaired as part of this step.

Pros: surgical; preserves MAC-206 sequencing; addresses only true corruption; keeps v1.4.1 Stage 1 release-able.
Cons: leaves the global-vs-scoped invariant question implicit; future readers might re-discover the 52k legacy rows and re-trigger this debate.

### β.3c — repair only id=539 (β.1 scope) + explicit bible amendment scoping the invariant to "rows that carry structured JSON metadata"

Scope: repair id=539 only (β.1 as originally ratified). Bible §11 amendment includes an explicit scoping clause: *"The audit invariant applies to identifiers rows whose `notes` carries structured JSON metadata. Legacy plain-text `notes` (pre-JSON-convention rows, primarily Phase-5 Step-4 follow-on² rationales and Wave-A repo-registration notes) are out of scope; the invariant does not require their backfill."* Defer the 5 RAVEN_* + sid=7 + raw_observations repair work to a separate data-integrity initiative (e.g., a CP33 candidate or a v1.4.2 hygiene cycle).

Pros: cleanest discipline — explicit scoping in the bible rather than implicit reader-convention; minimum mutation footprint (1 row); MAC-206 ships under its original scope; the 5 RAVEN_* + sid=7 rows become a separately-scoped follow-up issue with their own audit trail; v1.4.1 Stage 1 unblocked.
Cons: introduces an "applicability scope" clause to the bible invariant — but per [[feedback_bible_amendment_downstream_consumer_audit|S.6.1/S.7/S.8 amendment-ratification gate]] discipline, this is exactly the kind of scoping the downstream-consumer sweep is supposed to surface anyway, and it makes the existing legacy plain-text reality first-class.

**DBArchitect recommendation: β.3c.** The 52k+ raw_observations addresses are not "corruption" — they are a different schema convention from a different era. Forcing them through JSON repair is a category error. The bible amendment should acknowledge that the JSON-structured-notes invariant applies to rows that opt into the JSON convention, not to all rows globally. β.3c also keeps MAC-206 sized correctly and v1.4.1 Stage 1 unblocked.

If CEO disagrees and wants β.3b (the additional 6 likely-corruption-row repair) bundled into MAC-206, DBArchitect can execute that in the next heartbeat under the same backup; the audit per-row is small and the RAVEN_* repair template is the same as id=539's (`json_set` to add a recovered-suffix key with a dated phrase). Not the recommended path because it widens MAC-206 scope beyond carve-out, but cheaper than β.3a by orders of magnitude.

## 1.5 Audit-surface choice (disclosed but moot under HALT)

`sqlite_master` scan for audit/sweep/event/log tables returns only `source_reclassifications` — which the issue spec already says is the wrong table for this work (it's for source-class changes, not identifier-notes enrichment). **No existing cumulative audit table with a `sweep_event_id` column exists in the v1.4.1 Stage 1 DB.**

Per CEO guidance "prefer additive over net-new table this late in the cycle," the canonical surface for the carve-out + repair audit trail under β.1 (or any branch that proceeds with mutations) is **the per-row `notes` payload itself** — each mutated row gets a new JSON-keyed audit fragment with the `sweep_event_id`, mutation timestamp, ratification ref, and rationale. This satisfies "audit-append-don't-mutate" (§11 #7) without a schema change.

This choice is moot under the current HALT (no mutations to audit), but DBArchitect discloses it so the next heartbeat doesn't relitigate the surface choice if CEO ratifies β.3b/β.3c.

## 1.5 Non-mutation attestation (run 2)

Phase 1.5 was read-only (`SELECT … FROM identifiers/sources/raw_observations WHERE json_valid(notes)=0`). No `UPDATE`/`INSERT`/`DELETE`/migration was issued. No DB backup taken (none required — no mutations). `git status` confirms only this heartbeat file `_phase_10_schema_anomaly/carve_out_execution.md` is staged-for-modification this run.

## 1.5 Next-action handoff (run 2)

- **Status:** MAC-206 → blocked (re-blocked at Phase 1.5), reassigning to CEO
- **Unblock owner:** CEO (β.3a / β.3b / β.3c ratification)
- **Unblock action:** CEO comments on MAC-206 with chosen β.3 sub-disposition; DBArchitect resumes execution under that scope
- **DBArchitect recommendation:** β.3c — repair id=539 only, add explicit applicability-scoping clause to the bible §11 amendment, defer 5 RAVEN_* + sid=7 to a separate hygiene initiative
- **Bible amendment (Phase 3):** drafting deferred until β.3 disposition lands (because the applicability-scoping clause is the key open question)

---

# Run 3 — 2026-05-20 (β.3c ratified, full 7-step sequence executed in one heartbeat)

**Status:** ✅ EXECUTED · Phase 1.6 repair + Phase 2 carve-out + Phase 3 bible amendment all landed under one backup
**Branch:** `v1.4.1-integration-stage-1` @ `e61ffae` (pre-commit; new commit lands at heartbeat close)
**Auth:** CEO ratified β.3c at [MAC-206 comment 90e6b70f](/MAC/issues/MAC-206#comment-90e6b70f-9f4d-4374-9655-d498e56982d2) 2026-05-20T23:47:08Z (refined applicability clause + child-issue gate; verbatim language ratified)
**Pre-authorized 7-step sequence:** Backup → file child issue → id=539 repair → 21-row carve-out → bible amendment → heartbeat → close

## 3.1 Pre-flight re-verification (run 3, paste-not-cite)

All Run 2 §1.5.d invariants re-confirmed unchanged at run 3 start (no parallel landing between Run 2 and Run 3):

```
total identifiers WHERE id BETWEEN 533 AND 553                           = 21
by manufacturer:  Flock Safety = 19;  Getac = 2
raw_observations WHERE promoted_identifier_id BETWEEN 533 AND 553        = 0
raw_observations WHERE source_id = 13                                    = 0
raw_observations WHERE source_id = 14                                    = 0
extraction_runs  WHERE source_id = 13                                    = 0
extraction_runs  WHERE source_id = 14                                    = 0
identifiers WHERE id BETWEEN 533 AND 553 AND superseded_by IS NOT NULL   = 0
identifiers WHERE id BETWEEN 533 AND 553 AND direct_admission_carve_out=1 = 0  (no already-carved)
json_valid(notes) distribution: 1 row with jv=0 (id=539);  20 rows with jv=1
```

Source-side provenance signatures on `sources.notes` re-read for sid=13 + sid=14 — both carry verbatim:

```
sid=13: session_admission='wave_g_pre_v1'
        authority_chain='MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c (migration 0009 manufacturer_app enum)'
        mac_55_step_2_run='pre-auth 3 mechanical promotion 2026-05-11'
sid=14: (same triple, verbatim)
```

→ No drift since MAC-205 scoping. Halt criteria PASSED. Proceeding to mutations.

## 3.2 Step 1 — backup

```
$ cp db/argus.db db/argus.db.mac206_pre_carveout_backup
$ sha256sum db/argus.db.mac206_pre_carveout_backup
f346940861995b740c301fc520aab3500e2acebb158fcbe7aecb88f088c51bab  db/argus.db.mac206_pre_carveout_backup
```

## 3.3 Step 2 — file deferred-hygiene child issue (MAC-208)

POST `/api/companies/{co}/issues` → **HTTP 201**.

```
id:         5129d69a-6f88-4c39-b5ed-d341423e55c9
identifier: MAC-208
status:     backlog
priority:   low
parentId:   7f88ac7a-abbd-4317-8348-cae1ef0f5f0e   (= MAC-184 v1.4.1 Stage 1 umbrella)
title:      "v1.4.2 hygiene — repair 6 intended-JSON rows broken by `{json}<concat>text` defect
             (id=539 was forward-repaired in MAC-206; this issue covers ids 554-558 + sid=7)"
```

Body contains: scan paste-not-cite of the 5 RAVEN_* identifier rows + the 1 sid=7 sources row (heads + tails, length annotations), forward-reference to the bible §11 #17 applicability clause, the CEO's probe question ("are all 6 rows symptoms of one ingest-time mechanic or independent one-offs?"), explicit out-of-scope guard against bundling in the 52,628 convention-era rows, and the explicit non-blocker disclaimer. No `blockedByIssueIds` set linking MAC-206 → MAC-208 (per CEO instruction: MAC-208 is forward-looking, not a precondition).

## 3.4 Step 3 — Phase 1.6 id=539 sibling repair (sweep_event_id `mac206_id539_repair_2026_05_20`)

Pre-UPDATE id=539 `notes` (paste-not-cite):

```
length: 446 chars
sha256: 7855e94df59f0642390a6d66481e23a98577aed560b0673a706c036262783786
shape:  {"apk_package": "com.flocksafety.hazyhiwire", "apk_version": "2.4.0",
         "sub_band": "70-85 (manufacturer_app default SSID/BLE-local-name vendor-prefix)",
         "§8.3_boost_pending": "77→82 via B.3.4 second-source uplift in same transaction"}
         | §8.3 corroboration 2026-05-10: flock-back signatures.py:52 Penguin
           ble_local_name second-source uplift; +5 boost (77→82 below 85 sub-band ceiling);
           B.3.4 staged in raw_observations as provenance trail
```

UPDATE statement (single-row, composite WHERE + idempotency guard):

```sql
UPDATE identifiers
   SET notes = ?              -- repaired JSON-object form, see below
 WHERE id = 539
   AND source_url = 'https://apkpure.com/flock-safety-device-app/com.flocksafety.hazyhiwire'
   AND json_valid(notes) = 0  -- only repair if still defective (idempotency guard)
```

Mechanism: parse the JSON head (4 keys) verbatim; lift the freeform suffix (everything after ` | `) into a new key `corroboration_note_2026_05_10`; add a `repair_audit` JSON object with sweep_event_id + repaired_at_utc + repair_reason + original_blob_sha256 + original_blob_length_chars + suffix_lifted_into_key + related_event (forward-ref to the carve-out's sweep_event_id) + audit_ref (β.3c ratification anchor) + child_issue_ref (MAC-208). The mechanic preserves §11 #1 paste-not-cite — the suffix is verbatim, not paraphrased; the 4 existing keys are preserved bit-for-bit.

Post-UPDATE verify:

```
affected rows:                           1  ✓
json_valid(notes):                       1  ✓
$.apk_package                            = 'com.flocksafety.hazyhiwire'                      (preserved)
$.apk_version                            = '2.4.0'                                           (preserved)
$.sub_band                               = '70-85 (manufacturer_app default SSID/BLE-…)'     (preserved)
$."§8.3_boost_pending"                   = '77→82 via B.3.4 second-source uplift…'           (preserved; quoted-path syntax for non-ASCII key)
$.corroboration_note_2026_05_10          = '§8.3 corroboration 2026-05-10: flock-back…'      (NEW — suffix verbatim)
$.repair_audit.sweep_event_id            = 'mac206_id539_repair_2026_05_20'                  (NEW)
$.repair_audit.original_blob_sha256      = '7855e94df59f0642390a6d66481e23a98577aed560…'    (NEW)
$.repair_audit.related_event.sweep_event_id = 'mac206_wave_g_carveout_2026_05_20'            (NEW — forward-ref to Step 4 event)
post-UPDATE notes length:                1391 chars
```

## 3.5 Step 4 — Phase 2 carve-out UPDATE (sweep_event_id `mac206_wave_g_carveout_2026_05_20`)

Pre-execute confirmation that all 21 target rows are now json_valid=1 (Step 3's repair restored id=539 to the eligible set):

```
SELECT COUNT(*) FROM identifiers WHERE id BETWEEN 533 AND 553 AND json_valid(notes)=1   = 21  ✓
```

UPDATE statement (21-row, composite WHERE + idempotency guard, json_patch is additive):

```sql
UPDATE identifiers
   SET notes = json_patch(notes, ?)        -- carve-out payload below
 WHERE id IN (533,534,535,536,537,538,539,540,541,542,543,544,545,546,547,548,549,550,551,552,553)
   AND source_url IN ('https://apkpure.com/flock-safety-device-app/com.flocksafety.hazyhiwire',
                      'https://apkpure.com/getac-bwc-viewer/com.getac.android.mobileappBWC')
   AND json_extract(notes, '$.direct_admission_carve_out') IS NULL
```

Payload (1292 chars):

```json
{
  "direct_admission_carve_out": true,
  "session_admission": "wave_g_pre_v1",
  "authority_chain": "MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c (migration 0009 manufacturer_app enum)",
  "mac_55_step_2_run": "pre-auth 3 mechanical promotion 2026-05-11",
  "provenance_path": "sources.id={13|14}.notes",
  "ratification_ref": "MAC-205 CEO ratification 2026-05-20 + MAC-206 β.3c ratification 2026-05-20 (CEO comment 90e6b70f)",
  "carve_out_scope": "session-scoped historical exception; not a future admission pathway",
  "carve_out_audit": {
    "sweep_event_id": "mac206_wave_g_carveout_2026_05_20",
    "applied_at_utc": "2026-05-20",
    "applied_to_ids": [533,534,535,536,537,538,539,540,541,542,543,544,545,546,547,548,549,550,551,552,553],
    "applied_to_sids": [13, 14],
    "precondition_event": {
      "sweep_event_id": "mac206_id539_repair_2026_05_20",
      "kind": "id539_intended_json_sibling_repair",
      "role": "id=539's intended-JSON defect was repaired in same heartbeat AS PRECONDITION FOR this carve-out (json_patch requires json_valid=1 on target row)"
    },
    "child_issue_ref": "MAC-208 (v1.4.2 hygiene; tracks sibling deferred rows ids 554-558 + sid=7; this carve-out does NOT depend on MAC-208 closing)",
    "audit_ref": "MAC-206 Phase 10d Run 3 — β.3c ratified (CEO comment 90e6b70f 2026-05-20)"
  }
}
```

Post-UPDATE verify (paste-not-cite):

```
First-run affected rows:                              21  ✓
Idempotency re-run affected rows:                      0  ✓
SELECT COUNT(*) … direct_admission_carve_out=1:      21  ✓
```

Sample id=540 POST-carve-out notes (Flock, product_family_codename `AVICORE`):

```json
{
  "sub_band": "90-95",
  "apk_package": "com.flocksafety.hazyhiwire",
  "apk_version": "2.4.0",
  "direct_admission_carve_out": true,
  "session_admission": "wave_g_pre_v1",
  "authority_chain": "MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c (migration 0009 manufacturer_app enum)",
  "mac_55_step_2_run": "pre-auth 3 mechanical promotion 2026-05-11",
  "provenance_path": "sources.id={13|14}.notes",
  "ratification_ref": "MAC-205 CEO ratification 2026-05-20 + MAC-206 β.3c ratification 2026-05-20 (CEO comment 90e6b70f)",
  "carve_out_scope": "session-scoped historical exception; not a future admission pathway",
  "carve_out_audit": {
    "sweep_event_id": "mac206_wave_g_carveout_2026_05_20",
    "applied_at_utc": "2026-05-20",
    "applied_to_ids": [533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553],
    "applied_to_sids": [13, 14],
    "precondition_event": {
      "sweep_event_id": "mac206_id539_repair_2026_05_20",
      "kind": "id539_intended_json_sibling_repair",
      "role": "id=539's intended-JSON defect was repaired in same heartbeat AS PRECONDITION FOR this carve-out (json_patch requires json_valid=1 on target row)"
    },
    "child_issue_ref": "MAC-208 (v1.4.2 hygiene; tracks sibling deferred rows ids 554-558 + sid=7; this carve-out does NOT depend on MAC-208 closing)",
    "audit_ref": "MAC-206 Phase 10d Run 3 — β.3c ratified (CEO comment 90e6b70f 2026-05-20)"
  }
}
```

id=539's notes post-Step 4 carries BOTH the `repair_audit` key (from Step 3) AND the `carve_out_audit` key (from Step 4) — events cross-reference each other:

```
id=539 keys: ['apk_package', 'apk_version', 'authority_chain', 'carve_out_audit',
              'carve_out_scope', 'corroboration_note_2026_05_10', 'direct_admission_carve_out',
              'mac_55_step_2_run', 'provenance_path', 'ratification_ref', 'repair_audit',
              'session_admission', 'sub_band', '§8.3_boost_pending']
```

repair_audit.related_event.sweep_event_id → 'mac206_wave_g_carveout_2026_05_20'  (forward-ref)
carve_out_audit.precondition_event.sweep_event_id → 'mac206_id539_repair_2026_05_20'  (back-ref)

Future readers can reconstruct the event order from either direction.

## 3.6 Step 5 — bible §11 amendment + downstream-consumer sweep

**Downstream-consumer sweep (per [[feedback_bible_amendment_downstream_consumer_audit]] S.6.1/S.7/S.8 gate):**

Surveyed all known consumers of `identifiers.notes`:

| Consumer | Path | Treatment | Verdict |
|---|---|---|---|
| `argus_cli.py` query | reads `notes` as opaque string for print | `_print_identifier_row` does not call json_extract on identifiers.notes | TOLERATES non-JSON |
| `db/validation/export_lynceus.py` | reads `notes` as opaque string into `ActiveRow.notes` | downstream export passes it through; no json_extract on identifiers.notes | TOLERATES non-JSON |
| `db/validation/mac101_item_a_registry_xcheck.py` | guards with `WHERE json_valid(notes)` | only on raw_observations rows, not identifiers; defensive filter | TOLERATES non-JSON |
| `db/export/wave_a_snapshot_export.py` | calls `json_extract(er.notes,'$.wave')` | on `extraction_runs`, NOT identifiers | OUT OF SCOPE for §11 #17 applicability |
| (other consumers) | grep'd `json_extract.*notes` and `json_valid` across repo | no hard-requirer found globally on identifiers.notes | TOLERATES non-JSON |

**Sweep verdict:** No consumer hard-requires `json_valid(notes)=1` globally on `identifiers`. Bible commit lands clean. The 35.9% non-JSON `raw_observations.notes` rows that have existed since the FCC/IEEE bulk-ingest era pass through current consumers without conflict — this confirms the convention-era class-1 carve-out is empirically already-tolerated, not a new posture.

Per the CEO's verbatim language, the §11 amendment was applied as a **new numbered §11 #17 rule** with three stacked sub-bullets:

1. The carve-out clause itself (audit invariant amended; session-bounded; not a future admission pathway; CP32 candidate marker).
2. The applicability-scope sub-clause (Class 1 = convention; Class 2 = deferred to MAC-208; id=539 forward-repaired in MAC-206).
3. The downstream-consumer applicability sub-bullet (records the sweep finding + binds future consumers to guard with `WHERE json_valid(notes)` when adding json_extract calls on identifiers.notes).

`BIBLE_AMENDMENTS.md` gained a corresponding `## CP32 Candidate #6` entry (pending CP32 bundle landing) per §11 #11 self-binding. Both edits land in the same git commit on `v1.4.1-integration-stage-1`.

## 3.7 Step 6 — this heartbeat

This is the Run 3 heartbeat appended to `_phase_10_schema_anomaly/carve_out_execution.md`. Paste-not-cite throughout (sha256s, exact counts, payload samples). No paraphrasing of the CEO ratification language; verbatim quoted into §11 #17 sub-bullet 2.

## 3.8 Step 7 — handoff to CEO for close

Final actions next:

- PATCH MAC-206 → `status='done'` with paste-not-cite summary comment linking back to this heartbeat + MAC-208 + bible commit hash.
- Reassign MAC-206 → CEO for close-out review.
- MAC-208 stays `backlog` / unassigned (v1.4.2 cycle picks it up).

## 3.9 Halt criteria — none fired

| Criterion (from CEO comment 90e6b70f) | Status |
|---|---|
| id=539 repair UPDATE affects ≠1 row → HALT | passed (1) |
| Phase 2 affects ≠21 rows first run → HALT | passed (21) |
| Downstream-consumer sweep finds hard-requirer of `json_valid(notes)=1` globally → HALT bible commit | passed (none found) |
| Child-issue creation API errors → HALT bible commit | passed (HTTP 201 MAC-208) |

All four halt criteria passed. Bible commit + DB mutations + child issue + heartbeat all land in one heartbeat per CEO authorization.

## 3.10 Non-fabrication attestation

- id=539 freeform suffix lifted verbatim (not paraphrased).
- All 21 carve-out target rows' pre-existing JSON keys preserved bit-for-bit via `json_patch` (additive-only mechanic).
- All audit metadata is timestamped (2026-05-20), sweep_event_id-anchored, ratification-ref'd to the actual CEO comment id (90e6b70f), and cross-referenced between repair_audit ↔ carve_out_audit on id=539's row.
- No `raw_observations` row fabricated (α rejected; binding).
- No carve-out applied to any row outside the 21-row enumerated set; future apkpure-sourced identifiers (ids 23043-23058) admitted *outside* wave_g_pre_v1 continue to carry `raw_observations` predecessors per the canonical contract (§11 #17 explicitly notes this contrast).
- No schema/enum/migration mutation. The carve-out + repair are `notes`-JSON-key additions only.

## 3.11 Next-action handoff (run 3)

- **Status:** MAC-206 → `done`, reassigning to CEO
- **What landed:** bible §11 #17 (carve-out + applicability scope + downstream-consumer applicability) + BIBLE_AMENDMENTS.md CP32 Candidate #6 + 22 DB row mutations (1 repair + 21 carve-outs) + MAC-208 child issue (backlog).
- **What didn't land (deliberately):** no CP32 bundle close (this is candidate #6, not the bundle); no MAC-208 work (forward-looking v1.4.2 hygiene); no main-branch push (work lives on `v1.4.1-integration-stage-1` until v1.4.1 ships).
- **CEO close-out review:** verify bible §11 #17 language matches the verbatim ratified text; verify carve_out_audit / repair_audit shape; verify MAC-208 child issue body completeness; verify no halt criteria silently triggered. If all clean, MAC-206 stays `done` and CP32 bundle author can absorb candidate #6 into the bundle at landing time.
