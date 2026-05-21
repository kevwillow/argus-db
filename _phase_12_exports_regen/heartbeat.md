# MAC-209 Phase 12 — exports regeneration heartbeat

**Dispatch:** [MAC-209](/MAC/issues/MAC-209) — v1.4.1 Stage 1 Phase 12 exports regen (final pre-rc1 Stage 1 child)
**Parent:** [MAC-184](/MAC/issues/MAC-184) — v1.4.1 Stage 1 integration umbrella
**Branch:** `v1.4.1-integration-stage-1`
**Predecessor commit:** `1080b5c` (MAC-207 Phase 11 close — Option A all-73 DROP + CP32 cand #7)
**Heartbeat at:** 2026-05-21T01:00–01:15Z

## Phase 1 — pre-flight (paste-not-cite, no mutations)

### HEAD + branch confirmation

```
$ git rev-parse HEAD
1080b5c133d4b2231779dad372f9a29e5bcdbb77
$ git rev-parse --abbrev-ref HEAD
v1.4.1-integration-stage-1
```

Predecessor `d125025` (MAC-206) → `1080b5c` (MAC-207 docs) chain intact:

```
1080b5c docs(v1.4.1-stage-1): MAC-207 Phase 11 close — Option A all-73 DROP + CP32 candidate #7
d125025 feat(v1.4.1-stage-1): MAC-206 Phase 10d β.3c — direct-admission carve-out (21 rows) + bible §11 #17 + id=539 sibling repair
e61ffae research(v1.4.1-stage-1): MAC-206 Phase 1.5 scan HALT — β.3 fork triggered (52,635 non-JSON notes)
d394a29 docs(bible): MAC-203 Deferral Note 1 — §44.3 Honeywell product nomenclature corpus (no surviving §11 #7 evidence)
b1b0be2 research(v1.4.1-stage-1): MAC-206 Phase 10d pre-flight HALT — id=539 notes malformed JSON
```

### Canonical state (`PRAGMA query_only = ON`)

| Field | Dispatch target | DB read | Match |
|---|---|---|---|
| `PRAGMA integrity_check` | ok | ok | ✓ |
| `schema_version` (MAX) | 25 | 25 | ✓ |
| `identifiers` (total) | 35,310 | 35,310 | ✓ |
| `identifiers` (active) | 34,968 | 34,968 | ✓ |
| `sources` | 71 | 71 | ✓ |
| `manufacturers` | 52 | 52 | ✓ |
| `raw_observations` | 146,573 | 146,573 | ✓ |

### SAR-13 sub-rule — CHECK enum read from sqlite_master CREATE TABLE

CP31 enum extension confirmed live (verbatim from `sqlite_master`):

```sql
identifier_type IN (
    ...
    -- CP31 (migration 0025 — this migration) — FCC EAS
    -- identifier-type cluster (2)
    'fcc_grantee_code',
    'equipment_class_code'
)
```

```sql
pair_kind IN (
    'la_bit_flip',
    'frdid_sibling',
    'vendor_as_container',
    'firmware_generation',
    -- CP31 (migration 0025) — FCC EAS structural pairing
    'fcc_grantee_equipment_class'
)
```

### Prior baseline (delta arithmetic source)

`exports/_export_manifest.json` v1.4.0 baseline fields captured:

| Field | v1.4.0 value |
|---|---|
| `canonical_count_post_v1_4_0` | 34,872 |
| `active_count_post_v1_4_0` | 34,792 |
| `sources_post_v1_4_0` | 66 |
| `manufacturers_post_v1_4_0` | 51 |
| `raw_observations_post_v1_4_0` | 146,188 |
| `schema_version_post_v1_4_0` | 24 |

## Phase 2 — regenerate exports

### First export_lynceus run — HALT, recovered via v1.4.0 precedent

Initial `python3 -m db.validation.export_lynceus` run halted with:

```
Halt: argus_export.json: row id=23160 writer-classified as None but MAC-45
drop_assignments map says 'unknown_category' — STOP-THE-LINE per dispatch
(do NOT silently re-tally).
```

**Root cause:** `extraction_outputs/mac45/coverage_matrix_report.json` is the
input drop-assignments map; it was generated 2026-05-19 against the v1.4.0
DB state. Since then, MAC-188's FP demote cycle superseded 262 active rows
(including id=23160 `air.aloft.rocks` `vendor_controlled_hostname`, demoted
2026-05-20T18:27:49Z to superseder id=35533 with
`classifier_reason:"known_fp_root::aloft.rocks"`). The MAC-45 map referenced
id=23160 as active; the writer correctly excluded it (superseded), causing
the reconciliation mismatch.

**Resolution path:** v1.4.0 precedent commit
`300e51b "exports: regenerate at v1.4.0 — 34,792 active identifiers / 21MB CSV"`
explicitly stated:

> `coverage_matrix_report.json` regenerated to bin-classify the 12,239 net-new
> identifier IDs (23063-35302) — the export script's MAC-45 reconciliation
> gate requires every active id to have a bin assignment.

i.e. `coverage_matrix.py` regeneration is standard practice in an export
pass, not "silent script patching". The module's docstring confirms it is
read-only against `identifiers` ("performs ZERO writes against
identifiers"). The dispatch's omission of an explicit
`db.validation.coverage_matrix` step is a doc gap absorbed by the
v1.4.0 precedent.

`coverage_matrix.py` re-run output:

```
Pre-active identifiers:                       34968
Cells (12 dc × 27 it = 324):                  324
Non-empty cells:                              36
Vendor corroboration entries:                 18127
Standard export survivors (≥30): 514  (dropped: 34454)
High-conf export survivors (≥70): 114  (dropped: 34854)
Halts:                                        0
```

### Second export_lynceus run — clean exit

`exit=0`. Stdout summary (high-conf dropped_in_export tally):

```
"argus_export_high_confidence.json": {
  "path": "/home/kev/argus/exports/argus_export_high_confidence.json",
  "size_bytes": 20951,
  "record_count": 114,
  "dropped_in_export": {
    "unknown_category": 34216,
    "ssid_pattern": 13,
    "ble_local_name": 20,
    "ble_characteristic": 5,
    "product_family_codename": 21,
    "rf_channel": 24,
    "device_class_id": 50,
    "ble_service_uuid": 32,
    "asdstan_enum_value": 18,
    "alpr_model": 11,
    "below_confidence_threshold": 39,
    "excluded_source_type": 361,
    ...
  }
}
```

### export_behavioral_signatures run — clean exit

```
$ venv/bin/python3 -m db.validation.export_behavioral_signatures
Wrote /home/kev/argus/exports/argus_export_behavioral_signatures.json: record_count=125 source_record_count=201 argus_run_id=28e57d53-32e6-5026-9a04-267feaafcd82
Patched /home/kev/argus/exports/coverage_report.md CP18 section.
```

**Discrepancy with dispatch — surfaced (not a halt):** dispatch claimed
"bx_sig DB count is unchanged from v1.4.0 baseline (131 per memory)". DB
query (`SELECT COUNT(*) FROM behavioral_signatures`) returns **201** rows.
The +70 delta is real (Stage 1 work added bx_sig rows). Per
[[feedback_db_verify_dispatch_claims]] — verify dispatch claims by query
before pasting; the dispatch memory was stale, the export reflects the
current DB state truthfully.

### Pre/post file sizes (5 deliverables)

| File | v1.4.0 (bytes) | post-Phase-12 (bytes) | Δ |
|---|---|---|---|
| `argus_export.json` | 85,769 | 88,747 | +2,978 |
| `argus_export_high_confidence.json` | 20,948 | 20,951 | +3 |
| `argus_export.csv` | 21,066,238 | 21,395,866 | +329,628 |
| `argus_export_behavioral_signatures.json` | 55,065 | 69,361 | +14,296 |
| `coverage_report.md` | 1,522,058 | 1,522,766 | +708 |

All 5 files mtime'd `2026-05-20 21:00` (= 2026-05-21T01:00Z local).

## Phase 3 — verification spot-checks

### CP31 propagation

| identifier_type | CSV count | std JSON count | high-conf JSON count | Disposition |
|---|---|---|---|---|
| `fcc_grantee_code` | 17 | 0 | 0 | All carry `device_category='unknown'` → DROP at §11 #13 in both Lynceus exports; CSV-only |
| `equipment_class_code` | 41 | 0 | 0 | Same — unknown_category, §11 #13 ban |

**MAC-201 §7.5-bis lift in high-conf export — explicit confirmation:**
the 14 lifted codes (ABY/ABZ/ARQ/MKM/N7N/LL9/PNF/QQL/TWV/EL5/NK7/UXX/X4G/YJV @
conf=85) DROP from `argus_export_high_confidence.json` not because the
≥70 floor would reject them (conf=85 clears the floor) but because their
`device_category='unknown'` trips §11 #13 BEFORE the floor evaluation.
This is the §4.5+§11 #13 design intent — fcc_grantee_code is a vendor
attribution anchor identifier_type, not a device-pairable Lynceus pattern.
The lift posture is preserved in CSV notes verbatim — sample (ABY row,
notes.section_8_3_lift parsed):

```json
{
  "lift_at_utc": "2026-05-20 23:17:32",
  "pre_conf": 75,
  "post_conf": 85,
  "anchor_table": "fcc_grantees",
  "anchor_source_id": 7,
  "anchor_grantee_code": "ABY",
  "anchor_grantee_name": "Motorola Solutions, Inc.",
  "sub_rule": "structural_anchor (anchor_conf=80)",
  "cp_anchor": "CP32-pending",
  "ratification_issue": "MAC-201",
  "precedent_class": "first_section_7_5_bis_lift"
}
```

**Parrot Automotive arm row:** present in CSV (`manufacturer='Parrot Automotive'`).
The manufacturers id=222 / parent_manufacturer_id=25 structure is on the DB
side; the export shape preserves `manufacturer` as a string field, so
the arm metadata propagates via the canonical name string.

### MAC-206 carve-out disposition (21 rows, ids 533–553)

| Export shape | carve-out rows present | Expected per dispatch | Halt-criterion |
|---|---|---|---|
| `argus_export.csv` | 21/21 (ids 533–553 all present) | "likely appear in CSV (no filter)" | ✓ |
| `argus_export.json` | 0/21 | "may or may not appear depending on conf floor" | n/a |
| `argus_export_high_confidence.json` | 0/21 | "do NOT promote into ≥70 high-conf export" | ✓ |

**Carve-out Lynceus drop rationale (not the dispatch's §8.2-crowdsourced-
ceiling path):** dispatch text claimed the carve-out rows are "Flock Safety
+ Getac apkpure-sourced at conf ≤ 75 sub-band (per `notes.sub_band`)" and
that the CP19 crowdsourced-ceiling rule would block them from high-conf
export. **DB reality (paste-not-cite):** the 21 rows are
`source_type='manufacturer_app'` (not `'crowdsourced'`) at confidence
**82, 87, 92** — above the ≥70 floor. They DROP at §4.4 type-mapping gate
because their identifier_types (`ble_service`, `ble_characteristic`,
`ble_local_name`, `product_family_codename`) are not in the Lynceus
`pattern_type` map. The dropped_in_export tally accounts for them
(`ble_local_name: 20`, `ble_characteristic: 5`, `product_family_codename: 21`,
`ble_service_uuid: 32` in high-conf). The high-conf halt-criterion ("MAC-206
carve-out rows surface in high-conf export") is honored — they correctly
drop, but via §4.4 type-mapping, not via the dispatch-described CP19/§8.2
path. **Surfaced for CEO awareness** — no halt because the user-facing
behavior is what the halt-criterion describes (carve-out absent from
high-conf), but the dispatch's reasoning chain warrants a clarification
in any §11 amendment-log entry that codifies the carve-out export posture.

### Lynceus `argus_record_id` stability (3-sample spot-check)

`argus_record_id = sha256(f"{identifier_type}|{normalized_identifier}").hexdigest()[:16]`
(SAR-10 / CP18 form). Three samples covering prior v1.4.0 + CP31 + MAC-206
carve-out:

| id | identifier_type | identifier | recomputed | CSV value | Match |
|---|---|---|---|---|---|
| 1 | mac | `e4:aa:ea:80:a1:9b` | `eea6f74486eea9c0` | `eea6f74486eea9c0` | ✓ |
| 35682 | fcc_grantee_code | `ABY` | `2debaa47e623b44b` | `2debaa47e623b44b` | ✓ |
| 540 | product_family_codename | `AVICORE` | `a72a124244fe4728` | `a72a124244fe4728` | ✓ |

F6 stability contract honored — re-import from v1.4.0 exports → v1.4.1
exports is idempotent on the prior-baseline id=1 row.

### `_meta.dropped_in_export` reconciliation

| Export | `source_record_count` | `record_count` | Σ `dropped_in_export` | Σ matches expected delta |
|---|---|---|---|---|
| `argus_export.json` (std) | 34,968 | 514 | 34,454 | ✓ (34,968 − 514 = 34,454) |
| `argus_export_high_confidence.json` | 34,968 | 114 | 34,854 | ✓ (34,968 − 114 = 34,854) |

### Halt-criteria audit (all PASS)

| Criterion | Status | Notes |
|---|---|---|
| HEAD/branch pre-flight | ✓ PASS | 1080b5c on v1.4.1-integration-stage-1 |
| Canonical state drift | ✓ PASS | All 6 values verbatim match dispatch table |
| CP31 enum extension live | ✓ PASS | sqlite_master CREATE TABLE confirms both identifier_types + pair_kind |
| Export script uncaught exception | ✓ RECOVERED | Initial MAC-45 staleness halt resolved via v1.4.0 precedent (coverage_matrix.py re-run); no script patched silently |
| `_meta.dropped_in_export` reconcile (std) | ✓ PASS | 34,968 − 514 = 34,454 |
| `_meta.dropped_in_export` reconcile (hc) | ✓ PASS | 34,968 − 114 = 34,854 |
| device_category=unknown in high-conf | ✓ PASS | 0 rows |
| source_type=procurement in high-conf | ✓ PASS | 0 rows |
| MAC-206 carve-out in high-conf | ✓ PASS | 0 rows (drops via §4.4 type-mapping) |
| `argus_record_id` collision/drift | ✓ PASS | 3/3 sample sha256 recomputations match CSV |

## §11 envelope attestation

- **§11 #1 paste-not-cite:** all DB counts + sample rows pasted verbatim from `PRAGMA query_only = ON` reads; dispatch's stale "131 bx_sig" memory corrected by query (now 201) per [[feedback_db_verify_dispatch_claims]].
- **§11 #6 read-only DB pass:** `PRAGMA query_only = ON` enforced by all three modules (`export_lynceus.py`, `export_behavioral_signatures.py`, `coverage_matrix.py` per their docstrings); no mutations made.
- **§11 #11 amendment-log discipline:** Phase 12 is exports-metadata; no bible-amendment entries written this phase. CP31 was codified pre-Phase-12; the new manifest references `cp_anchor='CP32-pending'` on the MAC-201 lift as audit metadata only.
- **SAR-13 + §3399 PRAGMA:** verified against `sqlite_master` CREATE TABLE (not just `PRAGMA table_info`) per [[feedback_pragma_alone_insufficient_for_sar13]].
- **Canonical Argus repo:** `~/argus/` per [[feedback_argus_working_repo_canonical_path]] — `~/argus-internal/argus/` retired per [[project_mac177_v1_2_0_shipped]].
- **High-conf floor:** ≥70 per script constants + §7.5 spec; no ≥80 variant introduced per [[feedback_high_confidence_export_floor]].

## Next action

Commit on `v1.4.1-integration-stage-1`, PATCH MAC-209 → `done`, MAC-184 wakes
CEO via `issue_children_completed` for Phase 13 (rc1 + STAGE_1_FINAL_REPORT
+ SAR-15.5 close-out audit) dispatch.
