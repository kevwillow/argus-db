# MAC-202 Phase 10 — sid=13 schema-binding anomaly investigation log

**Parent:** MAC-184 v1.4.1 Stage 1 integration
**Branch:** `v1.4.1-integration-stage-1`
**HEAD at start:** `cbb0cd7`
**Schema:** migrations applied through `0025` (per dispatch); PRAGMA `schema_version=187`
**Validator:** DBArchitect (agent 6c93a466)
**Run timestamp:** 2026-05-20

This log captures **only raw query output and source-of-truth evidence**, per §11 #1 (paste-not-cite). Disposition recommendation lives in `heartbeat.md`. No rows mutated (§11 #7).

---

## 1. Discipline envelope — schema verification (SAR-13 / §3399 PRAGMA)

```
PRAGMA schema_version → 187
PRAGMA user_version → 0
```

`sources` schema:
```
0|id|INTEGER|0||1
1|name|TEXT|1||0
2|url|TEXT|1||0
3|source_type|TEXT|1||0
4|tier|INTEGER|0||0
5|last_fetched_at|DATETIME|0||0
6|last_status|TEXT|0||0
7|notes|TEXT|0||0
```

`raw_observations` schema:
```
0|id|INTEGER|0||1
1|source_id|INTEGER|0||0
2|extraction_run_id|INTEGER|0||0
3|source_url|TEXT|1||0
4|raw_payload|TEXT|0||0
5|candidate_identifier|TEXT|0||0
6|candidate_type|TEXT|0||0
7|candidate_category|TEXT|0||0
8|candidate_manufacturer|TEXT|0||0
9|source_excerpt|TEXT|0||0
10|captured_at|DATETIME|1|CURRENT_TIMESTAMP|0
11|processed_at|DATETIME|0||0
12|promoted_identifier_id|INTEGER|0||0
13|notes|TEXT|0||0
14|source_row_key|TEXT|0||0
```

Note: dispatch §10 references column `candidate_identifier_type`; actual column name is `candidate_type`. Investigation re-mapped accordingly.

---

## 2. sid=13 row (sources table)

```
id: 13
name: Flock Safety FS Installer (com.flocksafety.hazyhiwire@2.4.0)
url: https://apkpure.com/flock-safety-device-app/com.flocksafety.hazyhiwire
source_type: manufacturer_app
tier: 3
last_fetched_at: 2026-05-10T04:00:00Z
last_status: success
notes:
  session_admission: wave_g_pre_v1
  admission_date_utc: 2026-05-10
  package: com.flocksafety.hazyhiwire
  package_role: installer (technician-facing — pairs with cameras during professional installation)
  version: 2.4.0
  version_code: 2004000
  download_channel: apk-pure (via apkeep 1.0.0 from EFForg)
  apk_format_downloaded: xapk
  xapk_sha256: 8f0eea5ebb9727376b152260125dee05d3a657e8c9ca71a2cfa22cf4d94c6c6c
  apk_sha256: b46ea409d43529de8320ab0dfcc69d27d1040381090d05009c00d5d865a1cda8
  ...
  authority_chain: MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c (migration 0009 manufacturer_app enum)
  doc_numbering: #14 (chronological landing per CREDITS.md draft); sources.id auto-assigned at INSERT time
  license: proprietary (vendor app under standard-RE-clause posture; static analysis only; DMCA §1201 envelope)
  mac_55_step_2_run: pre-auth 3 mechanical promotion 2026-05-11
```

sid=13 explicitly identifies as a **single-app** source: the Flock Safety FS Installer apk (`com.flocksafety.hazyhiwire@2.4.0`, sha256 `b46ea409…cda8`). Notes carry one `apk_sha256` and one `package` — there is no umbrella-corpus framing.

---

## 3. Raw_observations on sid=13 — full inventory (20 rows)

`SELECT COUNT(*) FROM raw_observations WHERE source_id=13` → **20**

Breakdown by `candidate_manufacturer`:
```
Parrot              8
Motorola Solutions  4
Dahua               4
Hikvision           3
DJI                 1
                   --
                   20
```

Breakdown by `source_url`:
```
https://apkpure.com/p/com.parrot.freeflight6        8
https://apkpure.com/p/com.motorolasolutions.wave    4
https://apkpure.com/p/com.mm.android.DMSS           4
https://apkpure.com/p/com.hikvision.hikconnect      3
https://apkpure.com/p/com.dji.industry.pilot        1
                                                   --
                                                   20
```

Breakdown by `candidate_type`:
```
ble_characteristic           5
ble_service_uuid             4
default_credential           2
drone_rid_id_type_enum       2
dri_regulation_enum          2
arsdk_dri_command_uid_set    1
arsdk_feature_uid            1
ble_company_id               1
rtk_rc_serial_template       1
vendor_namespace_uuid        1
```

Capture timeline:
```
MIN(captured_at) = 2026-05-18 15:08:09
MAX(captured_at) = 2026-05-18 15:08:09
COUNT(DISTINCT captured_at) = 1
```
All 20 rows were inserted in a **single batch** on 2026-05-18 at 15:08:09Z (MAC-178 integration commit window per row notes).

`extraction_run_id` coverage on sid=13:
```
total=20, with_run_id=0
```
All 20 rows have `extraction_run_id IS NULL` — no extraction-run linkage.

### 3.1 Full per-row roster (20 rows)

```
(243545, 'f6ec37db-bda1-46ec-a43a-6d86de88561d',         'ble_service_uuid',          'Hikvision',          'apkpure.com/p/com.hikvision.hikconnect',     promoted=23043)
(243546, 'af20fbac-2518-4998-9af7-af42540731b3',         'ble_characteristic',        'Hikvision',          'apkpure.com/p/com.hikvision.hikconnect',     promoted=23044)
(243547, 'af20fbac-2518-4998-9af7-af42540731b4',         'ble_characteristic',        'Hikvision',          'apkpure.com/p/com.hikvision.hikconnect',     promoted=23045)
(243548, 'd54ace3f-8e27-4718-aa17-019f0e318e14',         'ble_service_uuid',          'Dahua',              'apkpure.com/p/com.mm.android.DMSS',          promoted=23046)
(243549, '9782022b-32ca-4346-832e-779db180cf4b',         'ble_characteristic',        'Dahua',              'apkpure.com/p/com.mm.android.DMSS',          promoted=23047)
(243550, '2320ae58-8394-4652-95f7-0a872ac0958f',         'ble_service_uuid',          'Motorola Solutions', 'apkpure.com/p/com.motorolasolutions.wave',   promoted=23048)
(243551, 'a0547dec-3b67-4d22-980d-48b700801dc5',         'ble_characteristic',        'Motorola Solutions', 'apkpure.com/p/com.motorolasolutions.wave',   promoted=23049)
(243552, '481de929-8d4c-4d9e-a574-772a73e63977',         'ble_characteristic',        'Motorola Solutions', 'apkpure.com/p/com.motorolasolutions.wave',   promoted=23050)
(243553, '0000ffff-0000-1000-8000-00805f9b34fb',         'ble_service_uuid',          'Motorola Solutions', 'apkpure.com/p/com.motorolasolutions.wave',   promoted=23051)
(243554, '67',                                            'ble_company_id',            'Parrot',             'apkpure.com/p/com.parrot.freeflight6',       promoted=23052)
(243555, 'FR_30_OCTETS',                                  'drone_rid_id_type_enum',    'Parrot',             'apkpure.com/p/com.parrot.freeflight6',       promoted=23053)
(243556, 'ANSI_CTA_2063',                                 'drone_rid_id_type_enum',    'Parrot',             'apkpure.com/p/com.parrot.freeflight6',       promoted=23054)
(243557, 'FRENCH',                                        'dri_regulation_enum',       'Parrot',             'apkpure.com/p/com.parrot.freeflight6',       promoted=23055)
(243558, 'EN4709_002',                                    'dri_regulation_enum',       'Parrot',             'apkpure.com/p/com.parrot.freeflight6',       promoted=23056)
(243559, '41984',                                         'arsdk_feature_uid',         'Parrot',             'apkpure.com/p/com.parrot.freeflight6',       promoted=23057)
(243560, 'CAPABILITIES=1,DRI_STATE=3,DRONE_ID=4,DRI_TYPE=6','arsdk_dri_command_uid_set','Parrot',             'apkpure.com/p/com.parrot.freeflight6',       promoted=23058)
(243561, 'lc2014',                                        'default_credential',        'Dahua',              'apkpure.com/p/com.mm.android.DMSS',          promoted=NULL)
(243562, 'terminal',                                      'default_credential',        'Dahua',              'apkpure.com/p/com.mm.android.DMSS',          promoted=NULL)
(243563, '0045b822-753b-4b8a-9c65-8b97ca8a5dd4',         'vendor_namespace_uuid',     'Parrot',             'apkpure.com/p/com.parrot.freeflight6',       promoted=NULL)
(243564, '1APDF7Q0010001',                                'rtk_rc_serial_template',    'DJI',                'apkpure.com/p/com.dji.industry.pilot',       promoted=NULL)
```

**Zero of the 20 rows have a `source_url` matching the Flock app described by sid=13.** All 20 point to one of five *other* vendor APKs.

### 3.2 Promotion state

```
promoted_identifier_id IS NOT NULL  → 16 rows (ids 23043…23058)
promoted_identifier_id IS NULL      →  4 rows (243561 Dahua creds, 243562 Dahua creds,
                                              243563 Parrot vendor_namespace_uuid, 243564 DJI rtk_rc_serial_template)
```

The 4 unpromoted rows carry `hold_reason` in notes:
- 243561, 243562 (Dahua creds) — `schema_gap_no_credential_enum_slot`
- 243563 (Parrot namespace UUID) — staging-only per validator review
- 243564 (DJI rtk template) — `handoff_explicitly_not_promoted_flagged`

### 3.3 Per-vendor APK fingerprint (extracted from notes JSON)

Each row's notes carry distinct `(apk_package, apk_sha256, apk_version)`:

```
DJI       com.dji.industry.pilot     9334b047…2be   v1.9.0          → 1 row  (243564)
Dahua     com.mm.android.DMSS        d30abda0…efb   2.4.14          → 4 rows (243548, 243549, 243561, 243562)
Hikvision com.hikvision.hikconnect   6ee6129f…349   6.11.631.0506   → 3 rows (243545, 243546, 243547)
Motorola  com.motorolasolutions.wave 24b01b21…897   3.1.8.47141     → 4 rows (243550–243553)
Parrot    com.parrot.freeflight6     a105b081…b73   6.7.6           → 8 rows (243554–243560, 243563)
```

All notes carry:
```
admission_dispatch_ref: MAC-104
integration_dispatch_ref: MAC-178
```

`apk_sha256` is **distinct from sid=13's own** (`b46ea409…cda8`). Every row's APK fingerprint mismatches the sid=13 sources-row APK fingerprint.

---

## 4. Sister-source query (per dispatch)

```sql
SELECT id, name, source_type, url FROM sources
WHERE LOWER(name) LIKE '%hikconnect%'
   OR LOWER(name) LIKE '%dmss%'
   OR LOWER(name) LIKE '%hikvision%'
   OR LOWER(name) LIKE '%dahua%'
   OR LOWER(url)  LIKE '%hikvision%'
   OR LOWER(url)  LIKE '%dahua%'
   OR LOWER(url)  LIKE '%dmss%'
   OR LOWER(url)  LIKE '%hikconnect%';
→ 0 rows
```

```sql
SELECT id, name, source_type, url FROM sources WHERE LOWER(url) LIKE '%apkpure%';
→ 2 rows:
  (13, 'Flock Safety FS Installer (com.flocksafety.hazyhiwire@2.4.0)', 'manufacturer_app', https://apkpure.com/flock-safety-device-app/com.flocksafety.hazyhiwire)
  (14, 'Getac BWC Viewer (com.getac.android.mobileappBWC@1.0.20)',     'manufacturer_app', https://apkpure.com/getac-bwc-viewer/com.getac.android.mobileappBWC)
```

**No sister source exists** for any of: Hikvision Hikconnect, Dahua DMSS, Motorola Solutions Wave, Parrot FreeFlight 6, DJI Industry Pilot. The entire population of vendor-APK sources on apkpure in the DB is sid=13 (Flock) + sid=14 (Getac).

```sql
SELECT DISTINCT source_id FROM raw_observations WHERE source_url LIKE '%com.<pkg>%' GROUP BY source_id;
```
Per vendor package, the only source_id that appears is sid=13 (with the per-vendor row counts above). No other source_id binds any of these 5 packages.

---

## 5. Downstream identifiers (16 promoted rows 23043–23058)

```
(23043, 'ble_service_uuid',            'f6ec37db…',  'Hikvision',          apkpure.com/p/com.hikvision.hikconnect,   conf=95)
(23044, 'ble_characteristic',          'af20fbac…b3','Hikvision',          apkpure.com/p/com.hikvision.hikconnect,   conf=87)
(23045, 'ble_characteristic',          'af20fbac…b4','Hikvision',          apkpure.com/p/com.hikvision.hikconnect,   conf=87)
(23046, 'ble_service_uuid',            'd54ace3f…',  'Dahua',              apkpure.com/p/com.mm.android.DMSS,        conf=92)
(23047, 'ble_characteristic',          '9782022b…',  'Dahua',              apkpure.com/p/com.mm.android.DMSS,        conf=87)
(23048, 'ble_service_uuid',            '2320ae58…',  'Motorola Solutions', apkpure.com/p/com.motorolasolutions.wave, conf=87)
(23049, 'ble_characteristic',          'a0547dec…',  'Motorola Solutions', apkpure.com/p/com.motorolasolutions.wave, conf=87)
(23050, 'ble_characteristic',          '481de929…',  'Motorola Solutions', apkpure.com/p/com.motorolasolutions.wave, conf=87)
(23051, 'ble_service_uuid',            '0000ffff…',  'Motorola Solutions', apkpure.com/p/com.motorolasolutions.wave, conf=75)
(23052, 'ble_company_id',              '67',         'Parrot',             apkpure.com/p/com.parrot.freeflight6,     conf=85)
(23053, 'asdstan_enum_value',          'FR_30_OCTETS','Parrot',            apkpure.com/p/com.parrot.freeflight6,     conf=85)
(23054, 'asdstan_enum_value',          'ANSI_CTA_2063','Parrot',           apkpure.com/p/com.parrot.freeflight6,     conf=85)
(23055, 'asdstan_enum_value',          'FRENCH',     'Parrot',             apkpure.com/p/com.parrot.freeflight6,     conf=85)
(23056, 'asdstan_enum_value',          'EN4709_002', 'Parrot',             apkpure.com/p/com.parrot.freeflight6,     conf=85)
(23057, 'device_class_id',             '41984',      'Parrot',             apkpure.com/p/com.parrot.freeflight6,     conf=85)
(23058, 'rf_protocol_constant',        'CAPABILITIES=…','Parrot',          apkpure.com/p/com.parrot.freeflight6,     conf=85)
```

All 16 have `superseded_by IS NULL`. `identifiers.source_url` correctly points to the per-vendor APK URL, and `identifiers.manufacturer` matches the candidate manufacturer of the originating raw_observation. **Downstream provenance in `identifiers` is intact**; only the `raw_observations.source_id` FK is wrong.

---

## 6. Sanity check — does the Flock app have any raw_observation backing on sid=13?

```sql
SELECT id, source_id, candidate_manufacturer, source_url FROM raw_observations
WHERE source_url LIKE '%flocksafety%' OR source_url LIKE '%hazyhiwire%';
```
→ 73 rows, **all on source_id IN (54, 66)** — vendor_controlled_hostname rows from crt.sh / wave_i_aggregate. **Zero raw_observations point to the Flock APK URL.**

```sql
SELECT id, identifier_type, manufacturer, source_url FROM identifiers
WHERE manufacturer='Flock Safety' AND source_type='manufacturer_app';
```
→ 19 rows (ids 533–553), all source_url = `https://apkpure.com/flock-safety-device-app/com.flocksafety.hazyhiwire`.

Search for raw_observations that promoted to identifiers 533–553:
```sql
SELECT * FROM raw_observations WHERE promoted_identifier_id BETWEEN 533 AND 553;
```
→ **0 rows.**

The 19 Flock identifiers (and the 2 Getac identifiers 537,538 in the same id-range) were inserted into `identifiers` via a **direct admission path that bypassed `raw_observations` entirely** (early-Wave-G pattern). The Flock APK that sid=13 advertises is represented only by those 19 identifier rows — there is no `raw_observations` trail for the Flock app.

---

## 7. Summary of the anomaly (facts only — disposition deferred to CEO)

1. sid=13 is a single-app source row for the **Flock Safety FS Installer** APK (sha256 `b46ea409…cda8`, version 2.4.0).
2. All **20** raw_observations bound to `source_id=13` carry `source_url`, `apk_package`, `apk_sha256`, `apk_version` and `candidate_manufacturer` for **five other vendor APKs**: DJI Industry Pilot, Dahua DMSS, Hikvision Hikconnect, Motorola Solutions Wave, Parrot FreeFlight 6. The Hikvision/Dahua subset called out in the dispatch is 7 of 20; the same anomaly affects all 20.
3. **No sister source row exists** in the `sources` table for any of those five vendor APKs. The only other apkpure-typed source is sid=14 (Getac).
4. 16 of 20 raw_observations have been promoted (`promoted_identifier_id` 23043–23058). The downstream `identifiers` rows are internally correct (their per-row `source_url` + `manufacturer` match the originating APK). The mis-binding is **confined to the `raw_observations.source_id` FK**.
5. The 19 Flock identifiers that sid=13 *should* back (`identifiers` ids 533–553) have **zero `raw_observations` rows backing them** (direct admission path).
6. All 20 rows were inserted in a single batch at `2026-05-18 15:08:09Z`, with `extraction_run_id IS NULL`, carrying `integration_dispatch_ref: MAC-178` and `admission_dispatch_ref: MAC-104`.

### 7.1 Halt-criterion check (per dispatch)

| Criterion | Result |
|---|---|
| sid=13 doesn't exist | FALSE — sid=13 exists. |
| Sister source_id ambiguity (multiple candidates per vendor) | NONE — zero sister sources for any of the five vendor APKs. This is the opposite halt condition: **complete absence** of a correct binding target. |
| Any of 20 rows is `promoted_identifier_id IS NOT NULL` | **TRUE — 16 of 20**. Flagged for §6.4 supersession-impact analysis if rebinding. |

### 7.2 Disposition framework recap

- **Hypothesis A (mis-binding):** rows belong to per-vendor sister sources that need to be **admitted first**, then `raw_observations.source_id` updated and `sid=13` re-narrowed to Flock alone.
- **Hypothesis B (umbrella source):** sid=13 was effectively used as the Wave G vendor-APK DEX corpus and its `name`/`notes` should be rewritten to reflect the umbrella scope; per-row `apk_package` + `apk_sha256` in notes preserve provenance.
- **Hypothesis C (validator-surfaced):** MAC-178 integration inserted multi-vendor rows under sid=13 as a **default/placeholder binding** because the per-vendor sister sources were never admitted; the resolution is admit-then-rebind (= effectively A, but the framing matters because the bug is in the MAC-178 ingest code path, not a mistake in any single row).

Validator's recommendation lives in `heartbeat.md`. No row mutations performed (§11 #7).
