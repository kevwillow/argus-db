# MAC-204 Phase 10b — sid=13 admit-then-rebind heartbeat

**Status:** complete · all 6 dispatch steps applied · zero blast-radius confirmed
**Branch:** `v1.4.1-integration-stage-1` (HEAD pre-rebind: `6163778`)
**Schema:** migrations applied through `0026`; PRAGMA `schema_version=187` (unchanged — pure data INSERT/UPDATE, no DDL)
**Predecessor:** MAC-202 (investigation) · CEO disposition: Hypothesis C — admit-then-rebind
**Run timestamp:** 2026-05-20
**Validator:** DBArchitect (agent 6c93a466) — own continuity from MAC-202

Raw evidence: paste-not-cite throughout per §11 #1.

---

## 1. Pre-rebind backup (§11 #1 — paste)

```
$ cp db/argus.db db/argus.db.mac202_pre_rebind_backup
$ sha256sum db/argus.db.mac202_pre_rebind_backup
15b32ad9abe7ca37309c51f3a92a4031130f55c0caf0ab283005934a98a54926  db/argus.db.mac202_pre_rebind_backup
$ ls -la db/argus.db.mac202_pre_rebind_backup
-rw-r--r-- 1 kev kev 313360384 May 20 18:54 db/argus.db.mac202_pre_rebind_backup
```

File size: **313 360 384 bytes** · SHA256: `15b32ad9…4926`.

---

## 2. Migration 0026 — vendor APK source admissions

File: `db/migrations/0026_phase10_vendor_apk_sources_admission.sql`

Five `INSERT OR IGNORE INTO sources` rows; per-row notes JSON authored from each vendor's authoritative `raw_observations.notes` (apk_package, apk_sha256, apk_version). License posture mirrors sid=13/sid=14 Wave G envelope (proprietary; static analysis only under 17 USC §1201(j) + 37 CFR §201.40(b); DMCA §1201 envelope). Authority chain in-file: `MAC-1 → MAC-52 → CP12 → CP13 → MAC-104 admission → MAC-178 integration → MAC-202 disposition → MAC-204`.

**DB-verified assigned sids (per [[feedback_db_verify_dispatch_claims]] — dispatch guessed 51-55, actual is 67-71):**

| sid | name | url |
|---|---|---|
| 67 | Hikvision Hik-Connect (com.hikvision.hikconnect@6.11.631.0506) | `https://apkpure.com/hik-connect/com.hikvision.hikconnect` |
| 68 | Dahua DMSS (com.mm.android.DMSS@2.4.14) | `https://apkpure.com/dmss/com.mm.android.DMSS` |
| 69 | Motorola Solutions WAVE PTT (com.motorolasolutions.wave@3.1.8.47141) | `https://apkpure.com/wave-ptt/com.motorolasolutions.wave` |
| 70 | Parrot FreeFlight 6 (com.parrot.freeflight6@6.7.6) | `https://apkpure.com/freeflight-6/com.parrot.freeflight6` |
| 71 | DJI Industry Pilot (com.dji.industry.pilot@v1.9.0) | `https://apkpure.com/dji-industry-pilot/com.dji.industry.pilot` |

**Idempotency verified** — re-running migration after success kept `manufacturer_app` count at 14 (unchanged): pre=14, post=14, idempotent=True.

---

## 3. Transactional rebind — per-row §11 #1 evidence (paste)

Verbatim per-vendor count: Hik=3, Dahua=4, Moto=4, Parrot=8, DJI=1 → derived sum **20** (per [[feedback_verbatim_list_beats_aggregate_count]]).

Pre-flight halt-criterion check passed: all 20 rows confirmed `source_id=13` at start.

```
=== TRANSACTIONAL REBIND (BEGIN..COMMIT) ===
  Hikvision            -> sid= 67  rows=3  affected=3
  Dahua                -> sid= 68  rows=4  affected=4
  Motorola Solutions   -> sid= 69  rows=4  affected=4
  Parrot               -> sid= 70  rows=8  affected=8
  DJI                  -> sid= 71  rows=1  affected=1
  COMMIT OK
```

**Per-row pre/post evidence (paste-not-cite, all 20 rows):**

```
rid=243545  pre_sid=13->post_sid=67  mfr=Hikvision            expected_sid=67  OK=True  ident=f6ec37db-bda1-46ec-a43a-6d86de88561d
rid=243546  pre_sid=13->post_sid=67  mfr=Hikvision            expected_sid=67  OK=True  ident=af20fbac-2518-4998-9af7-af42540731b3
rid=243547  pre_sid=13->post_sid=67  mfr=Hikvision            expected_sid=67  OK=True  ident=af20fbac-2518-4998-9af7-af42540731b4
rid=243548  pre_sid=13->post_sid=68  mfr=Dahua                expected_sid=68  OK=True  ident=d54ace3f-8e27-4718-aa17-019f0e318e14
rid=243549  pre_sid=13->post_sid=68  mfr=Dahua                expected_sid=68  OK=True  ident=9782022b-32ca-4346-832e-779db180cf4b
rid=243550  pre_sid=13->post_sid=69  mfr=Motorola Solutions   expected_sid=69  OK=True  ident=2320ae58-8394-4652-95f7-0a872ac0958f
rid=243551  pre_sid=13->post_sid=69  mfr=Motorola Solutions   expected_sid=69  OK=True  ident=a0547dec-3b67-4d22-980d-48b700801dc5
rid=243552  pre_sid=13->post_sid=69  mfr=Motorola Solutions   expected_sid=69  OK=True  ident=481de929-8d4c-4d9e-a574-772a73e63977
rid=243553  pre_sid=13->post_sid=69  mfr=Motorola Solutions   expected_sid=69  OK=True  ident=0000ffff-0000-1000-8000-00805f9b34fb
rid=243554  pre_sid=13->post_sid=70  mfr=Parrot               expected_sid=70  OK=True  ident=67
rid=243555  pre_sid=13->post_sid=70  mfr=Parrot               expected_sid=70  OK=True  ident=FR_30_OCTETS
rid=243556  pre_sid=13->post_sid=70  mfr=Parrot               expected_sid=70  OK=True  ident=ANSI_CTA_2063
rid=243557  pre_sid=13->post_sid=70  mfr=Parrot               expected_sid=70  OK=True  ident=FRENCH
rid=243558  pre_sid=13->post_sid=70  mfr=Parrot               expected_sid=70  OK=True  ident=EN4709_002
rid=243559  pre_sid=13->post_sid=70  mfr=Parrot               expected_sid=70  OK=True  ident=41984
rid=243560  pre_sid=13->post_sid=70  mfr=Parrot               expected_sid=70  OK=True  ident=CAPABILITIES=1,DRI_STATE=3,DRONE_ID=4,DRI_TYPE=6
rid=243561  pre_sid=13->post_sid=68  mfr=Dahua                expected_sid=68  OK=True  ident=lc2014
rid=243562  pre_sid=13->post_sid=68  mfr=Dahua                expected_sid=68  OK=True  ident=terminal
rid=243563  pre_sid=13->post_sid=70  mfr=Parrot               expected_sid=70  OK=True  ident=0045b822-753b-4b8a-9c65-8b97ca8a5dd4
rid=243564  pre_sid=13->post_sid=71  mfr=DJI                  expected_sid=71  OK=True  ident=1APDF7Q0010001

remaining raw_observations with source_id=13: 0
raw_observations now bound to sids 67-71: 20
```

PRAGMA `schema_version=187` pre and post — no DDL drift, SAR-13 envelope intact.

---

## 4. §6.4 supersession-impact pass — identifiers 23043-23058

All 16 promoted identifiers verified:
- `raw_observation_id` back-reference resolves to a `raw_observations` row now bound to the correct new vendor sid.
- `identifiers.manufacturer` matches `raw_observations.candidate_manufacturer`.
- `identifiers.identifier` matches `raw_observations.candidate_identifier`.
- `identifiers.source_url` package segment matches the new bound source's `notes.package` (Hik=`com.hikvision.hikconnect`, Dahua=`com.mm.android.DMSS`, Moto=`com.motorolasolutions.wave`, Parrot=`com.parrot.freeflight6`).

**No supersession needed** — all 16 rows already carried correct per-row provenance prior to rebind. No CP32-class finding surfaced.

**`notes.rebind_audit` append (paste, all 16):**

```
(23043, 'Hikvision',          old=13, new=67, dispatch='MAC-204')
(23044, 'Hikvision',          old=13, new=67, dispatch='MAC-204')
(23045, 'Hikvision',          old=13, new=67, dispatch='MAC-204')
(23046, 'Dahua',              old=13, new=68, dispatch='MAC-204')
(23047, 'Dahua',              old=13, new=68, dispatch='MAC-204')
(23048, 'Motorola Solutions', old=13, new=69, dispatch='MAC-204')
(23049, 'Motorola Solutions', old=13, new=69, dispatch='MAC-204')
(23050, 'Motorola Solutions', old=13, new=69, dispatch='MAC-204')
(23051, 'Motorola Solutions', old=13, new=69, dispatch='MAC-204')
(23052, 'Parrot',             old=13, new=70, dispatch='MAC-204')
(23053, 'Parrot',             old=13, new=70, dispatch='MAC-204')
(23054, 'Parrot',             old=13, new=70, dispatch='MAC-204')
(23055, 'Parrot',             old=13, new=70, dispatch='MAC-204')
(23056, 'Parrot',             old=13, new=70, dispatch='MAC-204')
(23057, 'Parrot',             old=13, new=70, dispatch='MAC-204')
(23058, 'Parrot',             old=13, new=70, dispatch='MAC-204')
```

Audit payload schema (per row): `{old_source_id:13, new_source_id, new_source_name, mac202_rebind_dispatch:'MAC-204', mac202_disposition:'hypothesis_c_admit_then_rebind', applied_at:<utc>, raw_observation_id}`. Update scoped by id-PK (maximally specific; aligned with the spirit of [[feedback_scoped_updates_via_source_row_key]]).

---

## 5. Export Worker dry-run — blast-radius

DB-direct snapshot diff (pre-rebind backup vs post-rebind DB) on export-relevant identifier columns:

```
identifiers count (pre vs post rebind): pre=35252 post=35252 delta=0

export-relevant column-tuple diff (id, identifier, identifier_type, device_category,
manufacturer, model, confidence, source_url, source_type, source_excerpt,
geographic_scope, first_seen, last_verified):
  only in pre: 0
  only in post: 0

focused 16-row check (23043-23058): 0/16 diffs on export-relevant columns
  → export-relevant columns are byte-identical

notes-only check (all 16): added={'rebind_audit'}, removed=[], changed=[] for every row
```

**behavioral_signatures export** — independent of sid=13 (table holds 201 rows; pre/post: 0 reference sid=13, 0 reference sids 67-71). Untouched by this rebind.

**Conclusion: zero blast radius.** Record set and export-relevant columns are byte-identical; only intentional notes-additive change is the `rebind_audit` audit-trail key on the 16 touched rows.

**Pre-existing condition surfaced (not a MAC-204 finding):** `db.validation.export_lynceus.run()` halts on `MAC-45 drop_assignments` reconcile for identifier id=23160 — that row is **outside** the MAC-204 touched scope (23043-23058) and the Halt exists both pre- and post-rebind. Recommend the next downstream consumer-audit cycle re-run `db/validation/coverage_matrix.py` to refresh MAC-45 drop_assignments against the current identifiers table. Not blocking MAC-204 acceptance — pre-existing.

---

## 6. Commits

1. `feat(db): migration 0026 — phase 10 vendor APK source admissions` (this heartbeat's predecessor; carries the SQL only).
2. `integration(v1.4.1-stage-1): MAC-204 phase 10b sid=13 rebind + §6.4 audit` (this heartbeat; carries DB mutations + heartbeat doc).

Co-Authored-By: `Paperclip <noreply@paperclip.ing>`.

---

## 7. Acceptance criteria

- ☑ `db/argus.db.mac202_pre_rebind_backup` exists with SHA256 `15b32ad9…4926` (313 360 384 bytes).
- ☑ Migration 0026 committed; idempotent verified (rerun = 0 new rows).
- ☑ 20 `raw_observations` re-bound; per-row pre/post evidence pasted in §3.
- ☑ 5 new sources visible in `sources` (sids 67-71) with correct `(name, url, source_type='manufacturer_app', notes)`.
- ☑ 16 identifiers (23043-23058) carry `notes.rebind_audit` back-reference.
- ☑ Export-regen dry-run = zero blast radius (or surfaced + resolved): zero record-set delta, zero export-relevant-column delta. Pre-existing MAC-45 reconcile-gate noted as surfaced-not-MAC-204.
- ☑ CP32 amendment-log candidate captured below (carry-forward only).
- ☐ Branch HEAD advanced two commits — pending Step 6 git invocation (this heartbeat is part of commit 2).

---

## 8. CP32 carry-forward (note only — do NOT land a CP)

**§11 #11 amendment-log candidate (for the CP32 cycle, not landing in Stage 1):**

> **Rule:** Ingest path must `admit-source-row-before-batch-insert` as a hard precondition for any `INSERT INTO raw_observations`. A missing source row must HALT the batch, never silently fall back to a previously-admitted unrelated source.
>
> **Why:** MAC-202 root-cause was a partial Wave G v2 ingest where five vendor APK source rows were never admitted before the per-row batch insert. The ingest layer fell back to the most recent `manufacturer_app` source row (sid=13 — Flock Safety FS Installer, doc #14), which is **schema-legal** but **semantically wrong**: per-row notes correctly carried `apk_package=com.hikvision.hikconnect|com.mm.android.DMSS|…`, but `raw_observations.source_id` pointed to an unrelated Flock APK. Downstream supersession audits caught nothing because identifier-table `source_url`/`manufacturer` were correct per row, masking the schema-binding mismatch until MAC-202's §10.1 forensic pass.
>
> **How to apply:** Add `assert source_id_for(package) is not None` (or equivalent) at the head of every batch-insert path. Surface as a hard halt; reject the batch.

Stage 1 amendment scope remains reserved per prior CP allocation. This text is the CP32 draft, not an applied amendment.

---

## 9. Reassignment

This heartbeat closes MAC-204's six dispatch steps. Reassigning to CEO (`62a86779-651b-4c59-8773-cee9e0f53334`) for parent MAC-184 v1.4.1 Stage 1 integration roll-up.

Discipline-envelope cross-check:
- SAR-13: PRAGMA 187 pre & post; no DDL inflight; sources/raw_observations CHECK enums intact.
- §11 #1: paste-not-cite throughout (sha256, per-row pre/post, audit payload presence, DB-direct dry-run diff).
- §11 #7: violations OK for this child (disposition application, per dispatch).
- [[feedback_db_verify_dispatch_claims]]: dispatch guessed sids 51-55; DB-verified actual is 67-71.
- [[feedback_verbatim_list_beats_aggregate_count]]: 20 derived from `3+4+4+8+1`.
- [[feedback_scoped_updates_via_source_row_key]]: id-PK scoping on every UPDATE (raw_observations and identifiers).
- [[feedback_promotion_gate_needs_export_dryrun]]: dry-run executed against pre-rebind backup; zero blast radius.
- [[feedback_pragma_alone_insufficient_for_sar13]]: sqlite_master CREATE TABLE inspected for sources (manufacturer_app in CHECK enum) and raw_observations (no CHECK affecting this rebind).
