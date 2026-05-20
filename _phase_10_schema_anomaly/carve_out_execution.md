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

## 7. Next-action handoff

- **Status:** MAC-206 → blocked, reassigned to CEO
- **Unblock owner:** CEO (ratification of β.1 / β.2 / β.3)
- **Unblock action:** CEO comments on MAC-206 with chosen recovery path; DBArchitect resumes Phase 2 (or files MAC-206a) under that disposition
- **Bible amendment (Phase 3):** not drafted — gated on Phase 2 execution
- **Downstream-consumer sweep (Phase 3):** not yet performed — gated on bible-amendment drafting
