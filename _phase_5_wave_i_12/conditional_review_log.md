# §5.4 Conditional matches review — MAC-191 Phase 5

**Dispatch:** [MAC-191](/MAC/issues/MAC-191) §5.4
**Plan input:** `~/argus-internal/wave_i_pre_v1/wave_i_12_reconciliation_v2/RECONCILIATION_PLAN_V2_FOR_PAPERCLIP_V1_4_1.json`
**Captured:** 2026-05-20

## Discipline envelope

- SAR-15 GENERIC_RISK_CANONICALS guard binding. Expanded list (Wave I.11+I.12 combined):
  Harris, Dahua, Axis, Flock, Rhombus, Parrot, Reveal, Lenel, Axon, Vigilant Solutions,
  Clearview AI, Magnet Forensics, Engility.
- Tier 1-2 (exact / exact-alias) — accept unconditionally (none in this set; all conditional are tier 3-4).
- Tier 3-4 (substring) — require **industry-domain context predicate** (industry-domain keyword in the
  alias name OR direct-citation evidence of canonical identity).
- Phase 4 §4.2 precedent: PROMOTE only when name carries an explicit industry-domain phrase
  ("Government Communications", "Drone"); generic corporate suffixes (LLC, Inc, Ltd, Services, Group)
  are NOT industry-domain context.

## Plan-vs-dispatch count divergence (§11 #11 amendment-log candidate)

- Dispatch §0 says "68 conditional"; plan_v2 `manufacturer_aliases_enrichment_proposals.by_axis[*].proposals[operator_review_required=true]`
  sums to **77** (25 fcc + 25 usaspending + 27 deployment). Plan controls per Phase 4 precedent.
- Stage 2 amendment-log entry: dispatch §0 narrative under-counted conditional matches by 9 (cosmetic).

## Decisions

### FCC grantees axis (25 conditional → 2 PROMOTE / 23 DEFER)

| # | mid | Canonical | Proposed alias | Tier | grantee_rows | Decision | Rationale |
|---|---:|---|---|---:|---:|---|---|
| 1 | 7 | Axis Communications | `AXIS TECHNOLOGY` | 4 | 1 | DEFER | Generic; no industry-domain phrase. |
| 2 | 15 | Axon | `AXON Systems, Ltd.` | 3 | 1 | DEFER | "Systems Ltd" generic. |
| 3 | 7 | Axis Communications | `Axis Integrated Systems Inc` | 4 | 1 | DEFER | Generic LLC. |
| 4 | 7 | Axis Communications | `Axis Micro Device Corp` | 4 | 1 | DEFER | Generic. |
| 5 | 7 | Axis Communications | `Axis Network Technology Limited` | 4 | 1 | DEFER | Sweden-based Axis Communications AB is the canonical; "Axis Network Technology Limited" lacks direct identity evidence. |
| 6 | 15 | Axon | `Axon Enterprise, Inc` | 3 | 1 | **PROMOTE** | Axon Enterprise is the **official corporate name** of the canonical body-cam vendor (formerly TASER International). Phase 4 precedent: explicit corporate identity. |
| 7 | 15 | Axon | `Axon Labs` | 3 | 1 | DEFER | No industry-domain phrase. |
| 8 | 15 | Axon | `Axon Networks` | 3 | 1 | DEFER | Generic "Networks". |
| 9 | 15 | Axon | `Axon Product Partners, LLC` | 3 | 1 | DEFER | Generic LLC. |
| 10 | 8 | Harris | `BMO HARRIS BANK` | 3 | 1 | DEFER | Banking, NOT defense/IMSI. |
| 11 | 8 | Harris | `Bmoh Harris bank` | 3 | 1 | DEFER | Banking. |
| 12 | 8 | Harris | `GE Harris Aviation Information Solutions, LLC` | 3 | 1 | DEFER | Aviation IT, not IMSI. |
| 13 | 8 | Harris | `GE Harris Railway Electronics, L.L.C.` | 3 | 1 | DEFER | Railway, not IMSI. |
| 14 | 8 | Harris | `Harris 3M Products Inc` | 3 | 1 | DEFER | 3M partnership; unclear domain. |
| 15 | 8 | Harris | `Harris Canada Inc` | 3 | 1 | DEFER | Subsidiary plausible but no direct identity evidence. |
| 16 | 8 | Harris | `Harris Corporation Farinon Division` | 3 | 1 | DEFER | Farinon was Harris's microwave-radio division; RF-adjacent but lacks Phase-4-style explicit "Government Communications"/"Defense" phrase. Conservative under Phase 4 precedent. |
| 17 | 8 | Harris | `Harris Corporation Long Range Division` | 3 | 1 | DEFER | "Long Range Division" ambiguous (broadcast vs comms vs marine). DEFER. |
| 18 | 8 | Harris | `Harris Corportion Mobile Telephone Division` | 3 | 1 | DEFER | Pre-cellular mobile-telephone; not IMSI-catcher domain. Note typo "Corportion" — upstream data-quality concern. |
| 19 | 29 | Magnet Forensics | `MAGNET SYSTEMS IKE` | 4 | 1 | DEFER | Generic; "IKE" unclear. |
| 20 | 29 | Magnet Forensics | `MS Magnet Solutions Ltd.` | 4 | 1 | DEFER | Generic. |
| 21 | 7 | Axis Communications | `Main Axis S.r.l.` | 4 | 1 | DEFER | Italian S.r.l., no domain context. |
| 22 | 25 | Parrot | `PARROT DRONE SAS` | 3 | 1 | **PROMOTE** | Explicit "DRONE" domain matches Parrot canonical (drone manufacturer). Phase 4 precedent: "Parrot Sa" drone context promoted. |
| 23 | 25 | Parrot | `Parrot Electronics Ltd` | 3 | 1 | DEFER | Generic "Electronics Ltd". |
| 24 | 16 | Reveal | `Reveal Computer Products Inc` | 3 | 1 | DEFER | Generic computer products. |
| 25 | 2 | Vigilant Solutions | `Vigilant Systems Inc` | 4 | 1 | DEFER | Generic "Systems Inc". |

**FCC PROMOTE list (2):** Axon Enterprise, Inc (id=15); PARROT DRONE SAS (id=25).

### USAspending axis (25 conditional → 1 PROMOTE / 24 DEFER)

| # | mid | Canonical | Proposed alias | Tier | proc_rows | usd | Decision | Rationale |
|---|---:|---|---|---:|---:|---:|---|---|
| 1 | 14 | Engility | `ENGILITY SERVICES, LLC` | 3 | 1915 | 5.10B | DEFER | "Services LLC" generic suffix; 1915 rows + $5.1B impressive but plan flagged as conditional because Engility is GENERIC_RISK_CANONICAL. Need NAICS/contract-description evidence. Phase 4 precedent: explicit industry-domain phrase required. |
| 2 | 15 | Axon | `AXON ENTERPRISE, INC.` | 3 | 550 | 389M | **PROMOTE** | Official corporate name of Axon. Same rationale as FCC #6. |
| 3 | 16 | Reveal | `REVEAL IMAGING TECHNOLOGIES, INC.` | 3 | 20 | 132M | DEFER | "Imaging Technologies" is a domain phrase but Reveal canonical category in bible is not surveillance imaging; ambiguous fit. DEFER. |
| 4 | 16 | Reveal | `REVEAL GLOBAL CONSULTING LLC` | 3 | 34 | 110M | DEFER | "Global Consulting LLC" generic. |
| 5 | 7 | Axis Communications | `VISUAL AXIS LLC` | 4 | 1 | 18M | DEFER | Generic. |
| 6 | 16 | Reveal | `REVEAL TECHNOLOGY, INC.` | 3 | 5 | 13M | DEFER | Generic. |
| 7 | 7 | Axis Communications | `AXIS MANAGEMENT GROUP, LLC` | 4 | 26 | 13M | DEFER | Management consulting. |
| 8 | 7 | Axis Communications | `AXIS CONSULTANT GROUP AND ASSOCIATES LLC` | 4 | 1 | 10M | DEFER | Consulting. |
| 9 | 2 | Vigilant Solutions | `VIGILANT CYBER SYSTEMS, INC.` | 4 | 10 | 8.4M | DEFER | "Cyber Systems" — Vigilant canonical is ALPR not cyber. |
| 10 | 2 | Vigilant Solutions | `VIGILANT WATCH INTEGRATION INC` | 4 | 3 | 8.2M | DEFER | "Watch Integration" surveillance-adjacent but no direct identity. |
| 11 | 2 | Vigilant Solutions | `VIGILANT SERVICES CORPORATION` | 4 | 3 | 4.5M | DEFER | Generic. |
| 12 | 15 | Axon | `THE AXON GROUP, LTD` | 3 | 50 | 4.1M | DEFER | "Group Ltd" generic. |
| 13 | 7 | Axis Communications | `AXIS GLOBAL ENTERPRISES, INC.` | 4 | 9 | 3.1M | DEFER | Generic. |
| 14 | 2 | Vigilant Solutions | `VIGILANT AEROSPACE SYSTEMS, INC.` | 4 | 4 | 2.8M | DEFER | Aerospace, not ALPR. |
| 15 | 29 | Magnet Forensics | `ADVANCED MAGNET LAB, INC.` | 4 | 2 | 2.4M | DEFER | Physics lab. |
| 16 | 16 | Reveal | `REVEAL BIOSCIENCES INC` | 3 | 6 | 2.2M | DEFER | Biosciences. |
| 17 | 8 | Harris | `HARRIS LARRY` | 3 | 43 | 1.0M | DEFER + §11 #3 flag | **PII risk**: this is a person's name, not corporate. Surface as Stage 2 amendment-log candidate for USAspending ingestion PII filter. |
| 18 | 7 | Axis Communications | `AXIS LANGUAGE SOLUTIONS LIMITED` | 4 | 7 | 0.97M | DEFER | Language services. |
| 19 | 7 | Axis Communications | `AXIS GEOSPATIAL LLC` | 4 | 4 | 0.94M | DEFER | Geospatial; no direct identity. |
| 20 | 7 | Axis Communications | `AXIS PROSTHETICS AND ORTHOTICS, INC.` | 4 | 32 | 0.74M | DEFER | Medical. |
| 21 | 32 | Clearview AI | `CLEARVIEW CLEANING LLC` | 4 | 2 | 0.69M | DEFER | Cleaning services. |
| 22 | 32 | Clearview AI | `CLEARVIEW WINDOWS, INC.` | 4 | 2 | 0.42M | DEFER | Windows. |
| 23 | 7 | Axis Communications | `AXIS FLIGHT SCHOOL LLC` | 4 | 3 | 0.38M | DEFER | Flight school. |
| 24 | 7 | Axis Communications | `ALL AXIS PRECISION LLC` | 4 | 6 | 0.34M | DEFER | Precision tooling. |
| 25 | 32 | Clearview AI | `CLEARVIEW CENTERS, LLC` | 4 | 3 | 0.31M | DEFER | Generic. |

**USAspending PROMOTE list (1):** AXON ENTERPRISE, INC. (id=15).

**§11 #3 PII surfacing:** HARRIS LARRY (proc_rows=43; $1M procurement) is a person's name and should not enter the aliases column. Stage 2 amendment-log candidate: USAspending ingestion should apply PII-name filter to `vendor_canonical_normalized` field. The proposal itself is auto-filtered by SAR-15 DEFER discipline; documenting for upstream calibration.

### Deployment observations axis (27 conditional → 8 PROMOTE / 19 DEFER)

The deployment_observations axis already carries implicit "surveillance/LE deployment" domain context.
SAR-15 gate here: alias value must be a corporate variant (incl. typo / product-model) of the canonical,
NOT a multi-vendor co-deployment string.

| # | mid | Canonical | Proposed alias | Tier | dep_count | Decision | Rationale |
|---|---:|---|---|---:|---:|---|---|
| 1 | 1 | Flock Safety | `Flock Group Inc.` | 4 | 490 | **PROMOTE** | 490 ALPR-domain deployments + corporate-name shape; matches Flock canonical. |
| 2 | 15 | Axon | `Axon Enterprise` | 3 | 62 | **PROMOTE** | Official Axon corporate name without "Inc". |
| 3 | 8 | Harris | `Harris Corp.` | 3 | 20 | **PROMOTE** | Corporate abbreviation of Harris Corporation; 20 deployments in canonical domain. |
| 4 | 2 | Vigilant Solutions | `Flock Safety, Vigilant Solutions` | 3 | 3 | DEFER | Multi-vendor string; adding as alias for single canonical pollutes resolution. Semantic concern. |
| 5 | 1 | Flock Safety | `Flock Surveillance` | 4 | 3 | **PROMOTE** | "Surveillance" is the canonical domain; matches Flock Safety. |
| 6 | 25 | Parrot | `DJI, Loki, Parrot` | 3 | 2 | DEFER | Multi-vendor. |
| 7 | 25 | Parrot | `DJI, Parrot` | 3 | 2 | DEFER | Multi-vendor. |
| 8 | 15 | Axon | `Axon Body-2` | 3 | 1 | **PROMOTE** | Axon product model; matches established Motorola APX-style product-model alias precedent (Motorola id=3 aliases include APX, V300, V500). |
| 9 | 15 | Axon | `Axon Flex` | 3 | 1 | **PROMOTE** | Axon Flex is a known Axon body-cam product. |
| 10 | 15 | Axon | `DJI, Albatross, Autel Robotics, Skydio, Remotec Andros, Axon` | 3 | 1 | DEFER | Multi-vendor. |
| 11 | 8 | Harris | `DJI, Applied Aeronautics, Aurelia Aerospace, Autel Robotics, Black Swift Technologies, Harris Aerial, Parrot, Wingtra` | 3 | 1 | DEFER | Multi-vendor. PLUS "Harris Aerial" inside the string = unresolved canonical-lexicon-admission candidate from Phase 4. |
| 12 | 25 | Parrot | `DJI, Autel Robotics, Parrot` | 3 | 1 | DEFER | Multi-vendor. |
| 13 | 2 | Vigilant Solutions | `ELSAG, Vigilant Solutions` | 3 | 1 | DEFER | Multi-vendor. |
| 14 | 1 | Flock Safety | `Flock / LiveView Technologies` | 4 | 1 | DEFER | Multi-vendor. |
| 15 | 1 | Flock Safety | `Flock Safetu` | 4 | 1 | **PROMOTE** | Typo variant of Flock Safety; promoting normalizes future field-data. |
| 16 | 1 | Flock Safety | `Flock Saftey` | 4 | 1 | **PROMOTE** | Typo variant. |
| 17 | 2 | Vigilant Solutions | `Genetec, Vigilant Solutions` | 3 | 1 | DEFER | Multi-vendor. |
| 18 | 15 | Axon | `Motorola Solutions, Axon` | 3 | 1 | DEFER | Multi-vendor. |
| 19 | 2 | Vigilant Solutions | `PIPS, Vigilant Solutions` | 3 | 1 | DEFER | Multi-vendor. |
| 20 | 15 | Axon | `Possibly Axon` | 3 | 1 | DEFER | Low-confidence "Possibly" prefix; adds noise to canonical aliases. |
| 21 | 16 | Reveal | `Reveal D3` | 3 | 1 | DEFER | Product code; canonical Reveal category in bible unclear. |
| 22 | 15 | Axon | `Skydio / Axon` | 3 | 1 | DEFER | Multi-vendor. |
| 23 | 15 | Axon | `Vigilant Solutions, Axon` | 3 | 1 | DEFER | Multi-vendor. |
| 24 | 2 | Vigilant Solutions | `Vigilant Solutions, Dataworks` | 4 | 1 | DEFER | Multi-vendor. |
| 25 | 2 | Vigilant Solutions | `Vigilant Solutions, NDI Recognition Systems` | 4 | 1 | DEFER | Multi-vendor. |
| 26 | 2 | Vigilant Solutions | `Vigilant Solutions, Neology/PIPS` | 4 | 1 | DEFER | Multi-vendor. |
| 27 | 15 | Axon | `WatchGuard, Axon` | 3 | 1 | DEFER | Multi-vendor. |

**Deployment PROMOTE list (8):**
- Flock Group Inc. (id=1)
- Axon Enterprise (id=15)
- Harris Corp. (id=8)
- Flock Surveillance (id=1)
- Axon Body-2 (id=15)
- Axon Flex (id=15)
- Flock Safetu (id=1)
- Flock Saftey (id=1)

## Summary

| Axis | Conditional | PROMOTE | DEFER |
|---|---:|---:|---:|
| fcc_grantees | 25 | 2 | 23 |
| usaspending | 25 | 1 | 24 |
| deployment_observations_variants | 27 | 8 | 19 |
| **Total** | **77** | **11** | **66** |

11 conditional PROMOTEs feed into §5.2 alias-application loop. 66 DEFERs carry-forward to v1.5.0.

## Stage 2 amendment-log candidates surfaced

1. Dispatch §0 conditional-count divergence: narrative said "68"; plan summary sums to 77 (off by 9).
2. USAspending PII filter gap: HARRIS LARRY person-name appeared in `vendor_canonical_normalized`;
   downstream USAspending ingestion should PII-filter person-name rows.
3. Harris Corporation internal-division taxonomy (Farinon / Long Range / Mobile Telephone Divisions):
   ambiguous fit to canonical Harris (IMSI catcher); needs explicit subsidiary lineage research.
4. Reveal canonical (id=16) category in bible §2.1 unclear; ambiguity caused several DEFER decisions.
5. Engility Services LLC ($5.1B procurement) is plausibly the canonical Engility entity but lacks
   explicit IT/defense industry-domain phrase; NAICS/contract-description corroboration needed.
6. Harris Aerial appears inside a multi-vendor deployment row; reinforces Phase 4 admission candidate.
