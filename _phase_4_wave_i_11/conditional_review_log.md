# §4.2 Conditional Matches Review — Wave I.11 Reconciliation

**Issue:** [MAC-190](/MAC/issues/MAC-190) v1.4.1 Stage 1 Phase 4
**Plan ref:** `RECONCILIATION_PLAN_FOR_PAPERCLIP_V1_4_1.json` → `manufacturer_text_attribution_updates.updates.*[operator_review_required=true]`
**Guard applied:** SAR-15 GENERIC_RISK_CANONICALS — tier 3–4 substring requires context predicate (industry-domain keyword in surrounding tokens) before promotion.
**Date:** 2026-05-20

## Dispatch divergence (§11 #11 candidate)

The dispatch §0 narrative + issue scope says "9 conditional flagged". The actual plan-input has **13 conditional entries** (operator_review_required=true). Per-axis breakdown:

- IEEE: 8 conditional (Harris Designs NRV, Shanghai Dahua Scale, AXIS CORPORATION, AXIS Sp z o.o., Ace Axis, Axis Electronics, Flock Audio, Rhombus Europe)
- FAA: 1 conditional (Harris Aerial — 2 rows)
- Wireshark: 4 conditional (Harris Designs NRV, Harris Government Communications, Parrot Sa, Shanghai Dahua Scale)

Issue's summary_counts JSON confirms 13: `8+0+1+4=13`. The "9" in the narrative is stale prose. Surface as Stage 2 amendment-log note for CEO.

## Per-condition decisions

| # | axis | raw_manufacturer_text | rows | sample_ids | canonical | decision | rationale |
|---|---|---|---:|---|---|---|---|
| 1 | ieee_oui_registries | Harris Designs of NRV, Inc. | 1 | [18175] | Harris (id=8, imsi_catcher) | **DEFER** | NRV=New River Valley VA sign-design business per report. Canonical Harris is L3Harris RF/IMSI (HQ Melbourne FL). No RF/comms context in source_excerpt. |
| 2 | ieee_oui_registries | Shanghai Dahua Scale Factory | 1 | [19343] | Dahua (id=208, surveillance) | **DEFER** | Weighing-scale factory at Pudong Shanghai. Distinct from Hangzhou Dahua Technology (surveillance). No surveillance context. |
| 3 | ieee_oui_registries | AXIS CORPORATION | 1 | [15199] | Axis Communications (id=7, alpr) | **DEFER** | Japanese entity at Saitama. Canonical is Swedish Axis Communications AB. No camera/ALPR context. |
| 4 | ieee_oui_registries | AXIS Sp z o.o. | 1 | [20539] | Axis Communications (id=7) | **DEFER** | Polish entity at Gdańsk. Full Axis Communications subsidiary name is "Axis Communications Sp. z o.o."; raw lacks "Communications" qualifier. No camera/ALPR context. |
| 5 | ieee_oui_registries | Ace Axis Limited | 1 | [17579] | Axis Communications (id=7) | **DEFER** | UK entity at Swindon. "Ace Axis Limited" reads as distinct trading name. No camera/ALPR context. |
| 6 | ieee_oui_registries | Axis Electronics | 1 | [17612] | Axis Communications (id=7) | **DEFER** | UK entity at Bedford. Axis Electronics is a contract-EMS company, not surveillance cameras. No camera/ALPR context. |
| 7 | ieee_oui_registries | Flock Audio Inc. | 1 | [11240] | Flock Safety (id=1, alpr) | **DEFER** | Pro-audio gear at Fort Worth TX. Per report, distinct from Flock Safety ALPR. No ALPR/surveillance context. |
| 8 | ieee_oui_registries | Rhombus Europe | 1 | [21223] | Rhombus Systems (id=221, unknown) | **DEFER** | Bulgarian entity at Razlog/Blagoevgrad. Canonical Rhombus Systems is San Mateo CA surveillance. No surveillance context. Bulgarian subsidiary not documented in canonical aliases (`Rhombus`). |
| 9 | faa_remote_id | Harris Aerial | 2 | [694, 776] | Harris (id=8, imsi_catcher) | **DEFER** | drone_id_prefix records for "Harris Aerial Carrier H6/H8E". Harris Aerial is a Florida hybrid-drone manufacturer, NOT L3Harris RF/IMSI. Canonical Harris is imsi_catcher category; rows are drone category — category-mismatch. Surface as Stage 2 candidate for new canonical "Harris Aerial" admission. |
| 10 | wireshark_manuf | Harris Designs of NRV, Inc. | 1 | [] | Harris (id=8) | **DEFER** | Same logic as #1. |
| 11 | wireshark_manuf | Harris Government Communications | 1 | [] | Harris (id=8) | **PROMOTE** | "Government Communications" is L3Harris's documented business line (RF/comms). Context predicate satisfied: "government communications" is the actual surveillance/RF domain. |
| 12 | wireshark_manuf | Parrot Sa | 5 | [] | Parrot (id=25, drone) | **PROMOTE** | "Sa" = Société Anonyme, French corporate form. Parrot SA is the documented French drone manufacturer (canonical category=drone matches). Context predicate satisfied. |
| 13 | wireshark_manuf | Shanghai Dahua Scale Factory | 1 | [] | Dahua (id=208) | **DEFER** | Same logic as #2. |

## Totals

- **PROMOTE:** 2 entries (Harris Government Communications, Parrot Sa)
- **DEFER:** 11 entries (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 13)

## Effect on §4.3 plan execution

- §4.3 applies 88 entries total in plan.
- After §4.2 deferrals: 88 − 11 DEFER = **77 entries to apply**.
- Conditional PROMOTEs (2) merge with high_confidence_included (75) → 77 total.
- 11 DEFER entries logged here; rows untouched in this Phase 4. Surface to CEO for CP-precedent ratification (potential new canonicals: Harris Aerial; potential canonical-alias additions for European subsidiaries).
