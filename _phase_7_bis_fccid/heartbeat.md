# Phase 7-bis fccid.io 177-row re-dispatch — heartbeat

**Dispatch:** [MAC-201](/MAC/issues/MAC-201) v1.4.1 Stage 1 — Phase 7-bis Wave I.14b + I.14c
**Parent:** [MAC-184](/MAC/issues/MAC-184) v1.4.1 Stage 1 integration
**Carved-out source:** [MAC-194](/MAC/issues/MAC-194) §7.2 halt (177 fccid.io attestations held pending CP31)
**CP31 ratification:** [MAC-197](/MAC/issues/MAC-197); migration 0025 at `40b166e`
**Numerex precedent:** [MAC-196](/MAC/issues/MAC-196) closed at `1344f5d`
**Pre-apply DB backup:** `db/argus.db.mac201_pre_phase7bis_backup`
**Validator:** `da137694-2efe-4589-8150-828dcab881fb`
**Date:** 2026-05-20

## Pre / Post counts

| Metric | Pre | Post | Δ |
|--------|---:|----:|---:|
| identifiers active (`superseded_by IS NULL`) | 34,910 | **34,968** | **+58** |
| raw_observations | 146,219 | **146,573** | **+354** |
| `fcc_grantee_code` identifiers | 0 | **17** | +17 |
| `equipment_class_code` identifiers | 0 | **41** | +41 |
| Parrot Automotive (id=222) identifiers | 0 | **5** | +5 |
| Phase 7-bis `raw_observations` (sid=51, MAC-201-tagged) | 0 | **354** | +354 |
| Plan rows applied: V2 + V3 = 53 + 124 = **177** | — | **177** | 0 halts |

## §7.2-bis per-Wave breakdown

| Wave | Plan rows | grantee promoted (reused) | equip promoted (reused) | raw_obs | arm-routed (id=222) | halts |
|---|---:|---:|---:|---:|---:|---:|
| **I.14b (V2)** | 53 | 5 (48) | 12 (41) | 106 | 0 | **0** |
| **I.14c (V3)** | 124 | 12 (112) | 29 (95) | 248 | **19** | **0** |
| **Total** | **177** | **17 (160)** | **41 (136)** | **354** | **19** | **0** |

`extraction_runs` ids: 112 (Wave I.14b), 113 (Wave I.14c), 114+115 (idempotency-verification no-ops, kind=`idempotency_verification_noop`).

## Idempotency verified

Re-running `apply_7bis_177_fccid.py` immediately after first apply produced Δ=0/0 (zero new identifier rows, zero new raw_observations). Pre-warmed caches reuse all 17 grantee + 41 equip identifier rows; `INSERT OR IGNORE` on raw_observations skips collisions on the `(source_id, source_row_key)` UNIQUE constraint with `source_row_key = f'{fcc_id}::{candidate_type}'` composition.

## §7.5-bis cross-attestation lift evaluation — PROPOSAL ONLY (§11 #8)

See `lift_evaluation_log.md` + `lift_evaluation_proposal.json`. Headline:

| Sweep | Eligible | Proposed lifts | Notes |
|---|---:|---:|---|
| Within-identifiers cross-source | 0 / 58 | 0 | All 34 within-table cross-refs are fccid.io-internal (CP24 same-source ≠ corroboration). |
| Structural anchor `fcc_grantees` (sid=7) | 14 / 17 | 14 proposed @ conf 75 → 90 | First precedent for "structural anchor as §8.3 corroboration" — surfacing for CEO. |
| Structural anchor for `equipment_class_code` | 0 / 41 | 0 | No `equipment_class_codes` table in argus (CFR rule-parts live in regulation text). |

**14 lift candidates** (conf 75 → 90 if ratified, via §8.3 = `min(99, max(75, 85) + 5)`): ABY, ABZ, ARQ, MKM (Motorola Solutions); N7N, LL9, PNF, QQL, TWV (Sierra Wireless); EL5, NK7 (Harris); UXX (Cradlepoint); X4G (Axon); YJV (WatchGuard).

**3 grantee codes with no fcc_grantees anchor** stay at conf=75: 2AG (Parrot Automotive), 2AH (DJI), 2AL (Reveal). Section_7_2_halt_surface.md L55 flagged these as net-new grantee codes pre-CP31; future dispatch could ingest them into fcc_grantees.

## §11 #11 surfaces — clarifications / amendment-log candidates

1. **device_category=`unknown` applied to 2AG cohort.** Dispatch §11 #13 specifies `device_category='unknown'` as the default; dispatch §11 #14 (`2AG-cohort exception`) calls for `device_category='automotive_telematics'` for the 19 Parrot Automotive rows. The dispatch text presupposes the value is admitted by `identifiers.device_category` CHECK enum — **it is NOT.** CP31 §6 follow-up item 1 (PROJECT_BIBLE.md L3589 + L3541) explicitly defers this enum extension to a future CP32 cycle. Live `identifiers.device_category` CHECK admits only: `alpr, imsi_catcher, body_cam, police_radio, drone, gunshot_detect, hacking_tool, covert_cam, gps_tracker, face_recog, drone_detect, unknown`. Per §11 #1 (no fabrication), all 19 2AG rows applied with `device_category='unknown'`. Net effect: per §11 #13 default, all 177 Phase 7-bis rows DROP from Lynceus high-conf export (consistent with CP31 §5.2 framing); dispatch §11 #14 exception sentence is not currently achievable. **No fix needed today** (CP32-deferred per CP31 ratification); flagging for amendment-log continuity.

2. **Manufacturer-resolution surface — alias enrichment opportunity.** The 1 V3 row for `Ericsson Enterprise Wireless Solutions, Inc.` (grantee=UXX) routes to `Cradlepoint` (id=20) per the Ericsson 2020 acquisition (Cradlepoint id=20 already carries alias `Ericsson Cradlepoint`). The full grantee_name `Ericsson Enterprise Wireless Solutions, Inc.` is NOT in any manufacturer alias today; resolution succeeded via Validator-coded routing rule. CEO may want to enrich Cradlepoint id=20 aliases with the full string for future SAR-9 strict-lookup; surfaced as non-blocking §11 #11 item.

3. **§4 device-category provenance issue (2AG split).** The 18 V3 PARROT DRONE SAS rows attest to drone products (Parrot DISCO, ANAFI, etc.) but per CP31 routing rule (PROJECT_BIBLE.md L3541) all route to Parrot Automotive id=222 (automotive_telematics arm), not Parrot id=25 (drone hub). This is the §4 device-category provenance question section_7_2_halt_surface.md L71 originally surfaced. CP31 amendment took the routing position; this heartbeat applies it. CEO may want CP32 to introduce per-grantee_name disambiguation when an arm/hub registers under both names (PARROT DRONE SAS for drones, PARROT FAURECIA AUTOMOTIVE SAS for automotive).

## Manufacturer histogram (Phase 7-bis 58 identifier rows)

| Manufacturer | rows | manufacturer_id |
|---|---:|---:|
| Sierra Wireless | 14 | 21 |
| Motorola Solutions | 13 | 3 |
| Cradlepoint | 6 | 20 |
| Axon | 6 | 15 |
| Parrot Automotive | 5 | 222 (arm) |
| Reveal | 4 | 16 |
| Harris | 4 | 8 |
| WatchGuard | 3 | 17 |
| DJI | 3 | 22 |

All 9 manufacturers resolve to existing canonical rows (no new manufacturer admissions; Honeywell + Numerex precedents honored). Numerex Corporation (9 V3 rows) resolved to Sierra Wireless id=21 per MAC-196 `1344f5d`.

## Discipline envelope scorecard

| Rule | Outcome |
|------|---------|
| §11 #1 (no fabrication) | Honored — plan inputs quoted verbatim; HALT on manufacturer-not-resolved (0 halts; all 177 resolved). |
| §11 #6 (ToS / robots.txt) | Honored — operated only on already-fetched plan JSONs from SSD archive `/media/kev/Extreme SSD/argus-archive-2026-05-20/`; zero new fetches. |
| §11 #7 (provenance) | Honored — every identifier row chains to ≥1 raw_observations row via `promoted_identifier_id`; full source_url + source_excerpt preserved per row. Verified: 0 orphan identifiers. |
| §11 #8 (no confidence drift) | Honored — all 58 rows at CP15 ceiling 75; 14 lift candidates PROPOSED, not applied. |
| §11 #11 (amendment-log) | Honored — three surfaces above (CP32 enum gap, alias enrichment, 2AG split) routed to CEO. |
| §11 #13 (device_category=`unknown` default) | Applied — all 177 rows have `device_category='unknown'`; will DROP from Lynceus high-conf export (intended CP31 §5.2 behavior). |
| §11 #14 (procurement-only) | N/A — no procurement rows; all 177 from fccid.io crowdsourced. |
| CP15 single-source crowdsourced ceiling | Honored — conf=75 across all 58 rows. |
| SAR-9 canonical+alias resolution | Honored — all 9 vendors via canonical_name + alias + suffix-strip + ratified routing rules (CP31 2AG / MAC-196 Numerex). |
| CP31 §2 arm-routing | Honored — all 19 2AG rows route to Parrot Automotive id=222 (verified via Parrot Automotive identifier count = 5 distinct (gc/ec, mfr) tuples). |
| Pair integrity | Honored — 41/41 equip rows paired (`pair_kind='fcc_grantee_equipment_class'`, target=grantee row, same manufacturer). 0 broken pairs. |

## Artifacts (canonical paths)

```
_phase_7_bis_fccid/
├── apply_7bis_177_fccid.py          # idempotent promotion script (370 lines)
├── heartbeat.md                      # this file
├── lift_evaluation_log.md            # §7.5-bis CEO-ratification narrative
├── lift_evaluation_proposal.json     # machine-readable lift proposal
├── preflight_pragma.md               # SAR-13 + §3399 pre-flight (CHECK enums + arm row + sid=51)
├── promotions_log.md                 # per-row apply log (Wave I.14b + I.14c)
└── promotions_summary.json           # machine-readable apply summary
```

## Next action

CEO ratification of:
1. The 58 Phase 7-bis identifier-row promotions (177 plan rows × 2 ÷ dedup = 58 active rows) — these are already in DB pre-CEO-ratification per the dispatch-as-authorization framing (CP31 unblocked + dispatch §7.2-bis explicit promote instruction). Confirming the work meets discipline envelope.
2. The 14-row §7.5-bis structural-anchor lift proposal (75 → 90 if ratified). Includes the precedent-setting methodology question on fcc_grantees-table-as-corroboration-source. Validator does NOT auto-apply per §11 #8 cardinal rule.
3. The three §11 #11 surfaces (device_category CP32 deferred, Ericsson alias enrichment, 2AG split disambiguation) — all non-blocking.
