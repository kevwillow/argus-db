# Phase 3b §3.4 §8.3 lift application log

**Dispatch:** [MAC-189](/MAC/issues/MAC-189) (v1.4.1 Stage 1 — Phase 3b)
**Parent:** [MAC-184](/MAC/issues/MAC-184)
**Predecessors:** [MAC-188](/MAC/issues/MAC-188) Phase 2.5 hostname-corpus FP audit COMPLETE (262 demotions); [MAC-187](/MAC/issues/MAC-187) Phase 3a Wave I.9 ingest COMPLETE (4 net-new + 26 raw_obs + 16 conflicts)
**Synthesis source:** `~/argus-internal/wave_i_pre_v1/wave_i_9_continuation/wave_i_9_lift_candidates_synthesis.json` (132 candidates total)
**Branch:** `v1.4.1-integration-stage-1`
**Schema:** 24
**Date:** 2026-05-20
**DB backup:** `db/argus.db.mac189_pre_lift_backup`

## Algorithm (per dispatch §3.4)

1. **Identifier resolution** — lookup by (`identifier`, `identifier_type` ∈ {`vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`}, `manufacturer` = vendor slug verbatim per identifiers-table convention).
2. **CP24 cross-source independence** — verify ≥2 distinct source_classes per synthesis. All 132 candidates pass (distribution: 118 with 2 classes, 10 with 3, 3 with 4, 1 with 5; **zero single-class candidates**).
3. **Lift computation** — `new_confidence = min(99, max(current_confidence, lift_evidence_confidence) + 5)` where `lift_evidence_confidence` = upper of synthesis `candidate_confidence_band_default` (typically 88–90).
4. **Ceiling cap** — applied per CP29 §8.2 (`BIBLE_AMENDMENTS.md` §3322–3326):

   | value_class | Single-source default | Cross-source | Firmware-cert |
   |---|---:|---:|---:|
   | `vendor_controlled_hostname` | 75–90 | 85–95 | 95–99 |
   | `vendor_cloud_endpoint_url` | 80–90 | 90–97 | — |
   | `vendor_controlled_hostname_deprecated` | 80–87 | — | — |

   Phase 3b applies the **cross-source ceiling** (95 / 97 / 87 respectively); firmware-cert tier requires crypto-anchored evidence not represented in this lift cohort. `value_class_ceilings` SQLite table absent — DATA_DICTIONARY.md / BIBLE_AMENDMENTS.md ceilings used per dispatch fallback.
5. **Apply** — `UPDATE identifiers SET confidence = ?, notes = ? WHERE id = ? AND superseded_by IS NULL` only if new > current. Wrapped in `BEGIN ... COMMIT` per manufacturer.

## Pre-flight (SAR-13)

- `PRAGMA table_info(identifiers)` verified — 17 columns; `confidence INTEGER NOT NULL [BETWEEN 0 AND 100]`; `notes TEXT` carrying JSON blob per CP24 sub-rule (b).
- `value_class_ceilings` table absent — confirmed via `SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%ceiling%'` returning 0 rows. Ceilings sourced from canonical `BIBLE_AMENDMENTS.md` per dispatch fallback.

## Per-candidate disposition (132 candidates → outcomes)

| Outcome | Count | Notes |
|---|---:|---|
| **Lifts applied** | **5** | confidence-history audit-trail + cross_source_corroboration marker appended; per-mfr transactions committed |
| **No-op (already at/above ceiling)** | **108** | All currently at conf=97 (cross-source ceiling 95 < current); lift formula computes 95, no UPDATE |
| **Unresolved (not in canonical)** | **18** | Third-party platform hosts (`waveshare.com`, `espressif.com`, `zendesk.com`, `medium.com`, `slideshare.net`, etc.) — never promoted, mostly FP-dropped during Wave I integration |
| **Skipped — demoted in Phase 2.5** | **1** | `terra-sz-hc1pro-cloudapi.oss-cn-shenzhen.aliyuncs.com` (id=35305) — superseded by id=35441 with `fp_class='third_party_oss_sdk_root'` per [MAC-188](/MAC/issues/MAC-188); see `skipped_demoted.md` |
| **Halt — single-source-class** | 0 | All candidates have ≥2 source_classes |
| **Halt — value_class ceiling exceeded** | 0 | All computed new_conf within ceiling |
| **Halt — no-mfr-mapping** | 0 | vendor slug = manufacturer column verbatim |
| **TOTAL** | **132** | reconciles with synthesis JSON `lift_candidates_count: 132` |

## Lifts applied — per-row detail

### 1. `cellebrite.com` (id=26656, mfr=cellebrite)

- **Current → new:** 85 → 95
- **Lift basis:** `section_8_3_cross_source_corroboration`
- **Source classes (synthesis):** `B`, `I_github_source_new_orgs`, `I_github_subsidiary_source`
- **CP24 independence (strict source_type-level):** B (sid=54 `primary_registry` crt.sh CT-logs) × I_github_* (sid=66 `manufacturer_app` Wave-I vendor cloud-infrastructure hostname corpus). Two distinct source_type values. **PASS strict CP24.**
- **Source_excerpt:** `https://crt.sh/?q=%25.cellebrite.com&output=json` (verbatim)
- **Ceiling:** 95 (`vendor_controlled_hostname` cross-source band upper)
- **Waves:** wave_i_8_delta + wave_i_9_delta + wave_i_pre_v1

### 2. `enterprise.dji.com` (id=27746, mfr=dji)

- **Current → new:** 85 → 95
- **Lift basis:** `section_8_3_cross_source_corroboration`
- **Source classes (synthesis):** `B`, `I_github_source_new_orgs`, `I_github_subsidiary_source`
- **CP24 independence (strict source_type-level):** B (sid=54 `primary_registry`) × I_github_* (sid=66 `manufacturer_app`). Two source_types per DB raw_observations chain. **PASS strict CP24.** Phase 3a Halt-3 inserted the 2 corroborating I_github_* raw_observations into DB (no identifier mutation at Phase 3a — lift deferred to Phase 3b per dispatch).
- **Source_excerpt:** `https://crt.sh/?q=%25.dji.com&output=json` (verbatim)
- **Ceiling:** 95
- **Waves:** wave_i_8_delta + wave_i_9_delta + wave_i_pre_v1

### 3. `firmware.parrot.com` (id=34615, mfr=parrot)

- **Current → new:** 85 → 95
- **Lift basis:** `section_8_3_cross_source_corroboration`
- **Source classes (synthesis):** `B`, `I_github_source_new_orgs`
- **CP24 independence (strict source_type-level):** B (sid=54 `primary_registry`) × I_github_source_new_orgs (sid=66 `manufacturer_app`). **PASS strict CP24.**
- **Source_excerpt:** `https://crt.sh/?q=%25.parrot.com&output=json` (verbatim)
- **Ceiling:** 95
- **Waves:** wave_i_9_delta + wave_i_pre_v1

### 4. `forum.developer.parrot.com` (id=34617, mfr=parrot)

- **Current → new:** 85 → 95
- **Lift basis:** `section_8_3_cross_source_corroboration`
- **Source classes (synthesis):** `B`, `I_github_source_new_orgs`
- **CP24 independence (strict source_type-level):** B (sid=54) × I_github_source_new_orgs (sid=66). **PASS strict CP24.**
- **Source_excerpt:** `https://crt.sh/?q=%25.parrot.com&output=json` (verbatim)
- **Ceiling:** 95
- **Waves:** wave_i_9_delta + wave_i_pre_v1

### 5. `fh.dji.com` (id=35304, mfr=dji)

- **Current → new:** 90 → 95
- **Lift basis:** `section_8_3_cross_source_corroboration`
- **Source classes (synthesis):** `I_github_source_new_orgs`, `I_github_subsidiary_source`
- **CP24 independence (Phase-3a-precedent reading):** Both classes under sid=66 (`manufacturer_app`); same source_type at strict reading, but Phase 3a CEO-ratified Halt-3 treats source_class umbrella labels as the independence unit for §8.3 lift. Operational precedent followed.
- **CP24 strict-reading nuance (§11 #8 surfacing for CEO awareness):** Under a strict source_type-level reading, both source_classes share `source_type=manufacturer_app` → would fail CP24. Phase 3a Halt-3 ratification established the source_class-as-independence-unit precedent which this lift inherits. Stage 2 codification candidate: clarify whether `source_class` umbrella labels constitute "independent at the source_type level" for §8.3 lift purposes when umbrella-rooted at same source_id.
- **Phase 3a precedent:** Row was promoted in Phase 3a at conf=90 with `lift_basis='cp29_s1_cross_source_attestation'` and `source_classes_attesting=[I_github_source_new_orgs, I_github_subsidiary_source]`. Phase 3a placed at default-band-upper (75–90); Phase 3b lifts to cross-source-band-upper (95).
- **Source_excerpt:** `wave_i_aggregate://wave_i_9_delta/I_github_source_new_orgs/fh.dji.com`
- **Ceiling:** 95
- **Waves:** wave_i_8_delta + wave_i_9_delta

## Audit-trail notes mutation (CP24 §3 sub-rule b — append-only)

All 5 rows received the following `notes` JSON enrichments:

1. **`notes.confidence_history[]`** — one entry per row with shape:
   ```json
   {
     "at_utc": "<ISO-8601 UTC of commit>",
     "from": <pre_confidence>,
     "to": <post_confidence>,
     "rationale": "phase_3b_§3.4_§8.3_lift: cross-class corroboration via source_classes=<list>",
     "dispatch": "MAC-189",
     "cp_anchor": "CP29_§8.2_cross_source_lift"
   }
   ```
2. **`notes.cross_source_corroboration[]`** — one entry per row with shape:
   ```json
   {
     "at_utc": "<ISO-8601 UTC of commit>",
     "lift_basis": "section_8_3_cross_source_corroboration",
     "source_classes_independent": <list>,
     "waves_involved": <list>,
     "dispatch": "MAC-189",
     "phase": "v1.4.1_stage_1_phase_3b"
   }
   ```

All other `notes` fields preserved verbatim. No `source_url` / `source_excerpt` / `source_type` mutations (§11 #7 — provenance preserved through lift).

## Transaction trace

| Manufacturer | Lifts | Transaction status |
|---|---:|---|
| cellebrite | 1 | committed |
| dji | 2 | committed |
| parrot | 2 | committed |
| **TOTAL** | **5** | **3/3 committed** |

Race-condition guard: pre-apply re-read of `(notes, confidence)` for each `identifier_id` and assertion that confidence at apply-time == confidence at eval-time. No race fired.

## Pre/post confidence distribution shift (vendor_controlled_hostname + vendor_cloud_endpoint_url + vendor_controlled_hostname_deprecated)

| confidence | pre | post | Δ |
|---:|---:|---:|---:|
| 0 (sentinel) | 262 | 262 | 0 |
| 85 | 11,306 | 11,302 | −4 |
| 87 | 565 | 565 | 0 |
| 90 | 1 | 0 | −1 |
| 95 | 0 | **5** | **+5** |
| 97 | 108 | 108 | 0 |
| 99 | 1 | 1 | 0 |

The 262 conf=0 rows are MAC-188 Phase 2.5 supersession sentinels (mfr=NULL, hostname-corpus FP demotions). Active set unchanged; only the 5 lifted rows moved 85→95 / 90→95.

## CP24 §3 sub-rule (b) compliance

✅ `notes.confidence_history[]` entry appended (5 rows; new array initialized where absent)
✅ `notes.cross_source_corroboration[]` entry appended (5 rows; new array initialized where absent)
✅ Each entry carries `at_utc`, `dispatch`, `cp_anchor` per canonical shape

## §11 envelope compliance

- ✅ **§11 #1 (no fabrication)** — All lift evidence per synthesis JSON's documented per-lift evidence inventory; verbatim source_class labels preserved
- ✅ **§11 #3 (no PII)** — Hostnames are vendor-controlled cloud-infrastructure (corporate-domain artifacts); no PII; no PII in audit-trail notes
- ✅ **§11 #6 (ToS + robots.txt)** — No fetches issued (lift-only operation on staged synthesis)
- ✅ **§11 #7 (provenance is the DB)** — `source_url` + `source_excerpt` preserved on all 5 lifted rows; `raw_observations` chain unchanged
- ✅ **§11 #8 (no confidence drift)** — Cross-source independence verified per CP24; only +5 lift per the §8.3 corroboration formula; ceilings respected (95 ≤ 95); no row exceeds value_class ceiling
- ✅ **§11 #9 (no skip checkpoints)** — Phase 3b sits under [MAC-184](/MAC/issues/MAC-184) Stage 1 umbrella, gated on MAC-188 close ✓
- ✅ **§11 #11 (amendment-log discipline)** — `fh.dji.com` CP24 source_class-vs-source_type ambiguity surfaced for Stage 2 amendment consideration (not codified by this validator)

## Stage 2 amendment candidates (forward-looking, surfaced not codified)

1. **CP24 §3 source_class-level vs source_type-level independence clarification.** The dispatch §3.4 step 2 reads "independent at the source_type level". The Phase 3a Halt-3 CEO ratification operationally adopts "independent at the source_class umbrella label level" — accepting `I_github_source_new_orgs` × `I_github_subsidiary_source` as cross-source independent despite both sitting under sid=66 `source_type=manufacturer_app`. `fh.dji.com` lift in Phase 3b inherits this precedent. Stage 2 codification candidate: explicit bible-level decision on the independence-unit semantics for §8.3 lifts.
2. **§8.3 lift idempotency contract.** `fh.dji.com` received Phase 3a placement at conf=90 (cross-source-attestation lift_basis applied at placement) + Phase 3b lift to conf=95 (additional +5 using the same source_class evidence pool). Stage 2 codification candidate: clarify whether the +5 lift applies "once per evidence pool" or "stepwise band-by-band" — current applied logic implements stepwise.
3. **terra-sz reclassification audit-trail.** Phase 3a promoted `terra-sz-hc1pro-cloudapi.oss-cn-shenzhen.aliyuncs.com` at conf=90 as `vendor_cloud_endpoint_url` with hostname-shape variance carve-out; Phase 2.5 demoted to FP sentinel with `classifier_reason='third_party_cloud_no_vendor_tenant::aliyuncs.com'`. These two readings are substantively contradictory; the second reading prevailed. Stage 2 codification candidate: clarify whether `aliyuncs.com`-shape vendor-tenant URLs admit as `vendor_cloud_endpoint_url` per CP29 §2 (or are blanket-FP per CP31-candidate `third_party_oss_sdk_root` class).

## Next action

- Write `_heartbeats/hb_003b_lift_application_complete.md` heartbeat
- Comment on MAC-189 with paste-not-cite heartbeat
- Set MAC-189 status `done`; parent MAC-184 wakes CEO for Phase 4 dispatch
