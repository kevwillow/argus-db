# Argus

> Open-source database of surveillance equipment identifiers

[![watching the watchers](https://img.shields.io/badge/watching-the%20watchers-black.svg)](#what-argus-is)
[![flock around, find out](https://img.shields.io/badge/flock%20around-find%20out-red.svg)](#what-argus-is)
[![argus never blinks](https://img.shields.io/badge/argus-never%20blinks-black.svg)](#what-argus-is)
[![zero flocks given](https://img.shields.io/badge/zero-flocks%20given-red.svg)](#what-argus-is)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](LICENSE)

## What Argus is

Argus is a consolidated, well-attributed, queryable database of wireless identifiers — MAC addresses, OUIs, BSSIDs, SSID patterns, BLE UUIDs, FAA Remote ID prefixes, Bluetooth SIG company IDs, vendor-app BLE service UUIDs, and behavioral-signature heuristics — for **surveillance and law-enforcement-adjacent equipment, derived entirely from public sources**. It ships as three artifacts under three licenses: a pipeline (AGPL-3.0-or-later), a dataset (ODbL-1.0), and documentation (CC-BY-SA-4.0).

Throughout this README: *database* refers to the queryable SQLite file (`db/argus.db`); *dataset* refers to the exported JSON/CSV artifacts derived from it; *pipeline* refers to the migration + source-loader code that reproduces the database from upstream sources.

Tools to surveil people are abundant; tools to detect surveillance are not. The asymmetry favors the surveillor. Argus narrows the gap by enumerating the wireless fingerprints of fixed ALPRs, IMSI catchers, body cameras, police drones, and related equipment, so that a downstream scanner (Rayhunter, Lynceus, or another consumer) can alert when matching devices are detected nearby.

**Argus is for *detection* of public-record-derived surveillance equipment identifiers — NOT for evasion of legitimate law-enforcement interaction.** Argus operates as a passive identification database: identifiers and metadata only, no active interference, no jamming, no attack tooling, no deanonymization of individual officers or agencies. The scope is *equipment categories*, not people. Identifiers are derived exclusively from public sources — regulatory registries, public-records procurement data, open-source intelligence repositories, manufacturer-published documentation, and academic research.

## Quickstart

```bash
git clone https://github.com/kevwillow/argus-db.git
cd argus
python3 argus_cli.py status                        # show DB path, schema version, row counts
python3 argus_cli.py query e4:aa:ea:80:a1:9b       # lookup a Flock Safety ALPR MAC (id=1)
```

The repo ships with `db/argus.db` and the four canonical exports under `exports/` already populated; the read-path needs no `pip install`. See [SETUP.md](SETUP.md) for fresh-DB-init from migrations, source-ingest pipeline dependencies (per-domain pinned in `requirements-vendor-docs.txt` and `requirements-wigle.txt`), optional API keys, and WiGLE-grant gating.

## Status (v1.5.0)

Argus **v1.5.0** ships at schema_version=27 with:

- **35,812 active canonical identifiers** (net +848 active vs v1.4.1 per the v1.5.0 lexicon-expansion wave Stage 1 Step 5 identifier promotions); chained-superseded + withdrawn-no-successor self-loops preserved per CP32 §9 tri-state semantic
- **201 behavioral_signatures** (unchanged this release; CP33 §2 mig-0027 extended `behavioral_signatures.device_category` 13 → 16 for enum parity with `identifiers.device_category` — `+cctv_camera`, `+persistent_surveillance`, `+through_wall_radar` — but 0 row promotions land at v1.5.0 ship; the schema slots open for future evidence-arrival)
- raw observations with per-row source provenance (append-only)
- **73 upstream sources** (+2 in v1.5.0: sid=72 GitHub Code Search REST API + sid=73 adsb.lol v2 FAA-registry-derived aircraft tracking — admitted via the v1.5.0 lexicon-expansion wave per [MAC-232](/MAC/issues/MAC-232) and CP33 §1; two existing sources cited heavily but NOT re-admitted per §11 #11 dedup-merge — sid=51 fccid.io 60 v1.5.0 citations + sid=54 crt.sh 747 v1.5.0 citations); see [Data sources](#data-sources) below for the full per-tier breakdown
- **92 manufacturers** in the canonical lexicon across 16 device categories (+40 net in v1.5.0: 21 Session 1 military/federal + 19 Session 2 commercial/consumer — Pelco id=254 admitted as the second multi-arm `hidden_arm` row under Motorola Solutions hub id=3 per gate G-A, extending the CP31 hub-and-spoke precedent first applied to Parrot Automotive at v1.4.1; 90 `query_default='visible'` + 2 `query_default='hidden_arm'`)

**CP33 seven-section v1.5.0 lexicon-expansion bundle codified in v1.5.0** (`db/migrations/0027_*`): the `device_category` CHECK enum extends 13 → 16 with `cctv_camera`, `persistent_surveillance`, `through_wall_radar`, applied to BOTH `identifiers.device_category` AND `behavioral_signatures.device_category` in a single migration (continuing the CP32 §1 dual-table CHECK literal sweep precedent). The `identifier_type` CHECK enum extends 56 → 57 with `imei_tac` (forward-compatible admission per gate G-C — 8-digit IMEI Type Allocation Code; GSMA-allocated per manufacturer/model; 0 promoted rows at v1.5.0 ship — schema slot opens for future Wave G/H companion-app extraction). 40 net-new manufacturer canonicals across 7 surveillance cohorts (counter_uas, border_persistent_surveillance, through_wall_radar, imsi_catcher, fleet_telematics, camera_vms, electronic_monitoring) + 2 multi-purpose §11 #10 carveouts (Northrop Grumman, Lockheed Martin, Trimble, Bosch Security Systems). Pelco id=254 admitted as the framework's second multi-arm `hidden_arm` row under Motorola Solutions hub id=3 per gate G-A (SEC Ex21 FY2025 evidence chain; Delaware; acquired 2020). Full text at [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP33; see [What's new in v1.5.0](#whats-new-in-v150) below for the integration narrative.

**CP31 multi-arm hub-and-spoke schema landed in v1.4.1** (`db/migrations/0025_*`): the `manufacturers` table gains three columns (`parent_manufacturer_id`, `is_arm`, `query_default`) and the `identifier_type` CHECK enum widens 54 → 56 with `fcc_grantee_code` + `equipment_class_code` (the FCC EAS grantee identifier cluster). `pair_kind` extends 4 → 5 with `fcc_grantee_equipment_class` per the CP14 paired-identifier discipline. Parrot was the first vendor converted to the hub-and-spoke structure at v1.4.1 (id=25 hub preserved; id=222 Parrot Automotive arm row admitted); Pelco joined as the second arm-row at v1.5.0 (id=254 under Motorola Solutions id=3). Cisco/Meraki, Harris RF vs Harris Aerial, and Honeywell ACS division remain backlogged for arm splits per CP32 §4 evidence-driven cadence (no calendar promotion); v1.5.x patch backlog adds Avigilon (id=6) + WatchGuard (id=17) under Motorola Solutions hub per MSI 10-K FY2025 Exhibit 21 evidence chains.

**CP32 ten-section bundle codified in v1.4.1** (`db/migrations/0026_*`): the `device_category` CHECK enum extends 12 → 13 with `automotive_telematics`, applied to BOTH `identifiers.device_category` AND `behavioral_signatures.device_category` in a single migration (the first dual-table CHECK literal sweep in the framework — CP21 cumulative-full-enum spirit; CP33 §2 mig-0027 continues this precedent at v1.5.0 with 3 additional values). Nine additional narrative/discipline sub-sections codify the `Na_` sub-slot migration convention (first applied at mig-0026a), `superseded_by` tri-state semantics, the §11 #3 export-time PII generator post-condition guard pattern, the Lynceus-export per-bundle regen cadence, and five other items folded from Stage 1 CP32 candidates. Full text at [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP31 + CP32.

**Coverage is intentionally narrow at this baseline** — do not assume comprehensive coverage of any specific surveillance equipment category. Expansion comes via community contributions and future research waves (see [Known held items](#known-held-items-contribution-welcome) below).

Release cadence: tagged releases when substantive new data, new source families, or schema-impacting changes land. See [CHANGELOG.md](CHANGELOG.md) for the v1.5.0 ledger and migration history; active backlog tracked at [PLANNED_AND_FUTURE_UPDATES.md](PLANNED_AND_FUTURE_UPDATES.md).

## What's new in v1.5.0

v1.5.0 integrates the lexicon-expansion wave (Two-Session Parallel Dispatch) into a single ship under [MAC-232](/MAC/issues/MAC-232). The release codifies CP33 (seven sections — source admissions + dedups, schema mig-0027, manufacturer admissions +40 net to 92 total, identifier promotions +848 active, retroactive cctv_camera recategorization gate G-B, disambig + FP-class triage gate G-D / G-E, v1.5.x/v1.6.0 backlog queue), lands one schema migration (mig-0027 — `0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac`), and admits two new sources (sid=72 GitHub Code Search REST API + sid=73 adsb.lol v2 FAA-registry-derived aircraft tracking).

**40 net-new manufacturers across 7 cohorts:** counter_uas (11 vendors — Anduril Industries admitted as multi-product hub with 5 future arm-split candidates queued for v1.5.x; Fortem, Citadel Defense, Black Sage, D-Fend, AeroDefense, Echodyne, Liteye, Robin Radar, MyDefence, Sensofusion); border_persistent_surveillance (4 vendors — Elbit Systems of America, General Atomics, TCOM, Persistent Surveillance Systems); through_wall_radar (3 vendors — Camero, NIITEK, TiaLinx; FCC §15.519 UWB-LE-only regulatory carveout; NIITEK admitted on cohort_prediction zero-source basis with `notes.zero_source_admission=true` flag for future cycle re-attestation); imsi_catcher (1 vendor — Rohde & Schwarz); fleet_telematics (6 vendors — Geotab, Verizon Connect, Samsara, Motive, Lytx, Omnitracs); camera_vms (6 vendors — Hanwha Vision, Milestone Systems, Pelco arm under MSI, Uniview + Tiandy with NDAA §889 attribution, Vivotek); electronic_monitoring (5 vendors — BI Incorporated standalone, Attenti, STOP, Sentinel Offender Services, Track Group). Plus 4 multi-purpose §11 #10 carveouts admitted at `device_category='unknown'`: Northrop Grumman + Lockheed Martin (persistent_surveillance-adjacent), Trimble (fleet_telematics-adjacent), Bosch Security Systems (camera_vms-adjacent). High-confidence Lynceus export excludes the carveouts per §11 #13.

**Three new device_category enum values + imei_tac forward-compatible:** CP33 §2 mig-0027 extends `identifiers.device_category` and `behavioral_signatures.device_category` CHECK from 13 → 16 (`+cctv_camera`, `+persistent_surveillance`, `+through_wall_radar` — second dual-table CHECK literal sweep continuing the CP32 §1 precedent); `identifiers.identifier_type` CHECK from 56 → 57 (`+imei_tac` per gate G-C; 0 promoted rows at ship).

**Retroactive cctv_camera recategorization (gate G-B Step 6):** 7 existing manufacturers flipped `primary_category` from prior categories to `cctv_camera` (Hikvision id=209, Dahua id=208, Axis Communications id=7, Avigilon id=6, Verkada id=210, Eagle Eye Networks id=220, Rhombus Systems id=221); 31 identifier rows recategorized. NDAA §889 attribution preserved verbatim on Hikvision (id=209) and Dahua (id=208) via the canonical `notes.ndaa_section_889_note` key. **BriefCam (id=31) DEFERRED** per board — analytics-layer ambiguity (BriefCam is a video-analytics overlay on top of arbitrary CCTV/VMS, not itself a CCTV camera); `primary_category='face_recog'` unchanged.

**Pelco multi-arm `hidden_arm` admission (gate G-A):** Pelco, Inc. (id=254) admitted as the framework's second `hidden_arm` row under the CP31 hub-and-spoke schema, with `parent_manufacturer_id=3` (Motorola Solutions hub) per the SEC Ex21 FY2025 evidence chain (Pelco acquired 2020; Delaware). Default queries against `manufacturers` filter `WHERE query_default='visible'` and do NOT surface the arm; explicit-opt-in audit queries surface it per CP31 §4.6.

**NDAA §889 dual-format key application:** Hikvision (id=209) and Dahua (id=208) use only the canonical `notes.ndaa_section_889_note` key (legacy v1.2.0 admission); Uniview (id=255) and Tiandy (id=256) carry BOTH the canonical `ndaa_section_889_note` AND the S2-staged `ndaa_section_889_affected` + `ndaa_attribution_note` keys per Schema-truth-drift #2 forward-compatibility resolution.

**SAR-16 / SAR-17 / SAR-18 cohort-disambiguation codifications:** SAR-16 (alias-length-floor; lockheed-LM n=134 substring-collision driving case), SAR-17 (no-generic-product-aliases; mydefence-EAGLE n=41 substring-collision driving case), SAR-18 (classifier-predicate parity; oversized_mac_range Step 9 halt at id=9404 Eagle Eye Networks size=256 exemplar — coverage_matrix.py and export_lynceus.py classifiers MUST share runtime predicates). See [METHODOLOGY.md §13.5](METHODOLOGY.md) and [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP33 §6 for the discipline-evolution narrative.

**Two new sources admitted (+2 net; integration-time dedup-merge per §11 #11):** sid=72 GitHub Code Search REST API (`source_type='crowdsourced'`, tier 3; NO_LICENSE_DECLARED per-finding factual extraction under Feist) — dominant first-party crowdsourced extraction surface for the v1.5.0 cohort_prediction wave; sid=73 adsb.lol v2 (`source_type='regulatory'`, tier 3; PUBLIC_DOMAIN_EQUIVALENT FAA Part 47 + Feist on live ADS-B) — aircraft-tracking surface required for persistent-surveillance cohort. Two existing sources cited heavily but NOT re-admitted per §11 #11 dedup-merge: sid=51 fccid.io (60 v1.5.0 citations) + sid=54 crt.sh aggregator (747 v1.5.0 citations).

**Carry-forward queue for v1.5.x (tracked at PLANNED_AND_FUTURE_UPDATES.md):**

- **Hub-and-spoke arm-split candidates** — Avigilon (id=6) + WatchGuard (id=17) under Motorola Solutions hub (id=3) per MSI 10-K FY2025 Exhibit 21 evidence chains; same shape as Pelco arm-split landed at v1.5.0 gate G-A.
- **Elbit FCC grantee disambig** — 168 candidate Elbit/Tadiran subsidiary grantee codes from v1.5.0 Session 1 disambig review queue; per-row anchor-verification (FCC EAS direct or fccid.io verbatim) before canonical promotion; estimated yield 5-20 confirmed.
- **DJI aliases hygiene amendment (G-D)** — strip procurement-bundling contaminants from `manufacturers.id=22 (DJI)` aliases comma-separated list; move legitimate product-family codenames to `notes.product_family_codenames[]` typed enrichment per CP25 §3 + SAR-17.
- **Geo Group admission + BI Incorporated arm-split (G-F)** — admit Geo Group as new manufacturer (corporate parent) and flip BI Incorporated (id=258) to `is_arm=1, parent_manufacturer_id=<new Geo Group id>, query_default='hidden_arm'`; SEC Exhibit 21 evidence (GEO 10-K FY2025).
- **NIITEK zero-source re-attestation** — future v1.5.x cycle should re-attempt source attestation for NIITEK (id=241) `notes.zero_source_admission=true` flag.
- **CP30 reservation** — `vendor_asn_prefix` + `vendor_controlled_ip` codification remains reserved (zero empirical evidence; CP31 + CP32 + CP33 all preserved the reservation footnote).

## What's new in v1.4.1

v1.4.1 integrates the Wave I.9 → I.14c reconciliation cycle — seven sub-waves of academic + community-research retroactive promotion, crt.sh Distinguished-Name extraction, Wave I.13 hard-ID falsification empirical anchors, and a Phase 2.5 hostname-corpus FP audit — into a single ship under Stage 1 + Stage 2 of [MAC-184](/MAC/issues/MAC-184) / [MAC-219](/MAC/issues/MAC-219). The release codifies two coordinated bible amendments (CP31 multi-arm hub-and-spoke + CP32 ten-section bundle), lands two schema migrations (mig-0025 + mig-0026) plus one `Na_` sub-slot data-only addendum (mig-0026a — the first sub-slot precedent), and ships +172 net-new active identifiers across SoundThinking BLE operational signatures, Flock BLE operational signatures, the Honeywell ACS division attestation completion, +5 ceiling-band vendor-controlled-hostname lifts (Cellebrite + DJI enterprise/firmware + Parrot firmware/developer-forum), and +14 `fcc_grantee_code` rows from the first §7.5-bis structural-anchor lift cycle ([MAC-201](/MAC/issues/MAC-201)).

**CP31 multi-arm hub-and-spoke schema** (mig-0025; commit `40b166e`) is the framework's first multi-arm vendor admission. The `manufacturers` table gains `parent_manufacturer_id` / `is_arm` / `query_default` columns; default queries against the lexicon filter `WHERE query_default = 'visible'` unless explicitly auditing arm rows. Parrot Automotive id=222 is the first arm canonical (`parent_manufacturer_id=25, is_arm=1, query_default='hidden_arm', primary_category='automotive_telematics'`). The CP31 plan documented a forward-looking architectural binding for a future `identifiers.manufacturer_id` FK migration: every export-path JOIN MUST re-establish the visible-filter as `WHERE m.query_default = 'visible' OR id.manufacturer_id = m.id` when that FK lands (v1.5.0+ scope). At v1.4.1 the arm-row protection is implicit — no canonical identifier carries `manufacturer = 'Parrot Automotive'` as denormalized TEXT — but CP31 makes the future binding explicit so the migration cannot silently regress. See [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP31 for the 4-path downstream consumer audit ratified at [MAC-199](/MAC/issues/MAC-199).

**CP32 ten-section bundled codification** (commit `9f76fd7`) folds three pending Stage 1 candidates (#6 / #7 / #8) plus six new amendments into a single bible commit:

- **CP32 §1 — `device_category` CHECK enum +1 `automotive_telematics`** applied to BOTH `identifiers.device_category` AND `behavioral_signatures.device_category` (mig-0026; first dual-table CHECK sweep). 0 row promotions land in v1.4.1; the schema slot opens for the Phase 7-bis 177-row fccid.io 2AG-attested cohort and other future evidence-arrival.
- **CP32 §2 — Future `identifiers.manufacturer_id` FK migration** (architectural binding only); no schema mutation in CP32.
- **CP32 §3 — Test refactor** retiring the stale `test_type_mapping_covers_every_identifier_type` hardcoded enum check; the new test reads the live CHECK enum from `sqlite_master` at runtime and asserts every value has a §4.4 disposition (MAP or DROPPED). 5 currently-missing values land as DROPPED stubs in `db/validation/export_lynceus.py:DROPPED_REASONS` (the 3 CP29 hostname types + 2 CP31 FCC EAS types). Full 524/524 repo suite passes post-refactor.
- **CP32 §4 — Multi-arm vendor backlog admission cadence** (narrative): arm splits ship only on concrete identifier evidence, not on a schedule. Cisco/Meraki, Motorola Solutions, Harris RF vs Harris Aerial, Honeywell ACS division remain backlogged.
- **CP32 §5 — Lynceus export regen cadence** (narrative): exports regenerate per v1.4.x bundle, not per data-touching commit.
- **CP32 §6 — §11 #17 session-bounded admission carve-out** + class-2 deferred → MAC-208 fork language (folded from MAC-206 Stage 1).
- **CP32 §7 — Sandbox-absence HALT-fast-path default sub-rule** (folded from MAC-207 Stage 1).
- **CP32 §8 — MAC-206 carve-out export-drop attribution rule** — the 21 wave_g_pre_v1 carve-out rows drop via the §4.4 identifier_type → pattern_type mapping gate (`_meta.dropped_in_export.type_mapping_unmapped`), NOT via CP19 §8.2 crowdsourced-ceiling.
- **CP32 §9 — `superseded_by` tri-state semantic clarification** (narrative): `NULL` = active (34,964 rows) / `<other_id>` = superseded by a successor (342 rows) / `<self_id>` self-loop = withdrawn-no-successor under §11 #3 PII demotion (4 rows; the [MAC-217](/MAC/issues/MAC-217) Track B Jacobs `*.escg.jacobs.com` demotes). Active-set query convention is unchanged: `WHERE superseded_by IS NULL`.
- **CP32 §10 — §11 #3 export-time generator post-condition guard pattern** — the framework's first export-time content-shape guard. `_assert_no_email_pii(path)` runs after every Lynceus-export emission, re-reads the file, and raises `Halt` on any email-shape PII match. 7 live call sites across `export_lynceus.py` + `export_behavioral_signatures.py`. **The guard is active — `argus_export.csv` regex-scan returns 0 email-shape matches.**

**Honeywell admission completion** — Wave I.14a sub-pass 43 backfilled the Honeywell admission via ACS division enrichment (`Honeywell.notes.honeywell_acs_division_attestation` keys via [MAC-195](/MAC/issues/MAC-195) Phase 8). The Stage 1 cycle closed the firmware-cert evidence loop (Honeywell CodeSign RSA CA / OU=ACS / CT45 + CT40 device-model attestations). The §44.3 product-nomenclature corpus enrichment from the Wave I.14a runguide was explicitly deferred at [MAC-203](/MAC/issues/MAC-203) per Path 1 (intentional scope narrowing) — see [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) Deferral Note 1 for the surviving-evidence trace.

**Phase 2.5 hostname-corpus FP audit** ([MAC-188](/MAC/issues/MAC-188)) demoted 262 third-party-OSS / SDK-root false-positive hostname rows across 9 manufacturers via the §8.3 supersession path (cycle reports as 262 third-party-OSS supersessions; manifest narrative carries a minor ±1 reconciliation delta noted in `_export_manifest.json`). The DJI cohort dropped from 410 → 242 rows post-cleanup.

**SoundThinking + Flock BLE operational signature expansion** — Stage 1 promoted 30 SoundThinking `ble_service_uuid` rows at `confidence=85, device_category=gunshot_detect, source_type=crowdsourced` (the Lynceus accept-list does not yet include `ble_service_uuid` as a shippable `pattern_type`, so they currently drop under `_meta.dropped_in_export.ble_service_uuid` per the §4.4 alias-confirm open question in the v1.4.2 queue). The current high-confidence export carries 1 SoundThinking `oui` row (`d4:11:d6`) + 3 Flock Safety BLE service rows mapped to `pattern_type=ble_uuid`.

**First export-time §11 #3 PII generator post-condition guard** — [MAC-217](/MAC/issues/MAC-217) Phase 5 landed the `_assert_no_email_pii(path)` defense-in-depth pattern alongside the §8.2 PII-strip (commit `50b8232`). The companion 4 Jacobs `*.escg.jacobs.com` demotes (cert-subject personal email PII discovered during the strip) became the first consumers of the CP32 §9 `superseded_by = id` self-loop withdrawn-no-successor semantic.

**SAR-15.5 first activation** — Stage 1 was the first cycle to fire the SAR-15.5 ≥10-phase / ≥10k-promotion independent close-out audit discipline. Verdict: PASS. The codification anchored Validator-role accountability for large-ship cycles and surfaced the Honeywell-in-lexicon miss that the main self-executed pass had missed (corrected pre-tag).

**Na_ sub-slot migration convention** — CP32 §1 codified the `Na_…` lexical-after suffix for data-only addendum migrations sharing a numeric slot with a schema-mutating migration. First application: `0026a_phase10_vendor_apk_sources_admission.sql` (renamed from `0026_phase10_*` at commit `398c8b8`) sharing slot 26 with the schema-mutating `0026_cp32_device_category_automotive_telematics.sql`. Filename↔schema_version 1:1 holds for schema-mutating migrations; data-only addenda live alongside via `Na_/Nb_/…`.

**Carry-forward queue for v1.4.2:**

- **Phase 7-bis 177-row fccid.io cohort** ([MAC-194](/MAC/issues/MAC-194)) — first v1.4.2 work item; HALT lifted now that CP30/CP31/CP32 codifications have all landed. Promotion would target the Parrot Automotive arm (id=222) at `device_category='automotive_telematics'` — the schema slot opened by CP32 §1.
- **[MAC-208](/MAC/issues/MAC-208) class-2 deferred carve-out follow-up** + **[MAC-218](/MAC/issues/MAC-218) IEEE-registry orphan 8 RO hygiene** — both backlogged.
- **`ble_service_uuid` Lynceus accept-list MAP** — 30 SoundThinking gunshot_detect BLE UUIDs await §4.4 alias confirm; decision driver for v1.4.2.
- **CP30 reservation** — `vendor_asn_prefix` + `vendor_controlled_ip` codification remains reserved (zero empirical evidence; CP31 + CP32 preserved the reservation footnote).

## What's new in v1.2.0

v1.2.0 lands the cycle-7 autonomous-overnight-wave integration: two new FCC equipment-authorization sources (fccid.io aggregator + the official FCC EAS Filings UI as a distinct primary surface), 671 dual-citation-pair discovery rows from the MAC-101 partial deliverable (citation half deferred to an async re-citation pass), 16 net-new identifiers from a static-analysis pass against four LE-adjacency vendor companion apps (Hikvision Hik-Connect, Dahua DMSS, Motorola WAVE PTT, Parrot FreeFlight 6), 14 new manufacturer rows (4 positive + 10 documented-absence stubs), 22 documented_absence intelligence entries, and 19 SAR-11 FP-class additions to the calibration registry. A bible amendment codifying empirical-premise verification as a runguide precondition landed as `Correction Pass 27` after CEO+operator ratification on the MAC-178 issue thread (new `§2.4` in `PROJECT_BIBLE.md`; `§3.0` verification-probe slot now required before any `§3.1` bulk dispatch). See [CHANGELOG.md](CHANGELOG.md) for the full v1.2.0 ledger.

## Sixteen device categories

Argus categorizes identifiers per the canonical 16-value vocabulary (enum on the `identifiers.device_category` column):

| Category | What it covers | Example vendors |
|---|---|---|
| `alpr` | Automated License Plate Reader systems | Flock Safety, Genetec, Rekor, Vigilant Solutions |
| `imsi_catcher` | Cellular IMSI / IMEI / TMSI collection devices | Harris, Digital Receiver Technology, Engility, KeyW, Jacobs, Septier, Rohde & Schwarz *(v1.5.0)* |
| `body_cam` | Body-worn cameras + adjacent | Axon, Getac, Reveal, WatchGuard Video |
| `police_radio` | Encrypted police radios | Kenwood (and Motorola Solutions multi-purpose subset) |
| `drone` | Surveillance drones + remote-pilot aircraft | DJI, Parrot, BRINC, Skydio |
| `gunshot_detect` | Acoustic gunshot detection | SoundThinking (ShotSpotter) |
| `hacking_tool` | Forensic device-extraction tools | Cellebrite, Magnet Forensics, Berla, Hak5 |
| `covert_cam` | Concealed surveillance cameras | (broad class; v1.0.0 has placeholder rows) |
| `gps_tracker` | Covert GPS asset trackers + electronic monitoring | BI Incorporated, Attenti, STOP, Sentinel Offender Services, Track Group *(v1.5.0 electronic_monitoring cohort)* |
| `face_recog` | Face-recognition systems | Clearview AI, BriefCam |
| `drone_detect` | Counter-drone detection systems | Dedrone, DroneShield, Anduril Industries, Fortem Technologies, Citadel Defense, Black Sage, D-Fend Solutions, AeroDefense, Echodyne, Liteye Systems, Robin Radar Systems, MyDefence Communications, Sensofusion *(v1.5.0 counter_uas cohort)* |
| `unknown` | OUI- or registry-level identifier without single-product attribution; multi-purpose-vendor carveout | Cradlepoint, Sierra Wireless, L3Harris, Motorola Solutions (when OUI-only), Northrop Grumman, Lockheed Martin, Trimble, Bosch Security Systems *(v1.5.0 §11 #10 multi-purpose carveouts)* |
| `automotive_telematics` *(v1.4.1 CP32 §1)* | Fleet telematics + connected-vehicle automotive surveillance | Parrot Automotive *(v1.4.1 hidden_arm)*, Geotab, Verizon Connect, Samsara, Motive, Lytx, Omnitracs *(v1.5.0 fleet_telematics cohort)* |
| `cctv_camera` *(v1.5.0 CP33 §2)* | IP-CCTV / closed-circuit camera systems | Hikvision *(NDAA §889)*, Dahua *(NDAA §889)*, Axis Communications, Avigilon, Verkada, Eagle Eye Networks, Rhombus Systems, Hanwha Vision, Milestone Systems, Pelco *(v1.5.0 hidden_arm under MSI)*, Uniview *(NDAA §889)*, Tiandy *(NDAA §889)*, Vivotek |
| `persistent_surveillance` *(v1.5.0 CP33 §2)* | Aerostat / lighter-than-air persistent platforms + tower-mounted persistent imaging + strategic-altitude aerial persistent surveillance | Elbit Systems of America, General Atomics, TCOM, Persistent Surveillance Systems |
| `through_wall_radar` *(v1.5.0 CP33 §2)* | UWB through-wall radar systems; FCC §15.519 UWB-LE-only regulatory carveout (operationally restricted to law-enforcement use) | Camero, NIITEK *(zero-source admission)*, TiaLinx |

The 16-value enum and per-vendor categorization rationale are documented in [PROJECT_BIBLE.md](PROJECT_BIBLE.md) (canonical anchors in the Canonical sources table at end of this document). The "unknown" category is **not exported to Lynceus** per the multi-purpose-vendor discipline (§11 #10 + §11 #13). See `manufacturers` table at runtime for the full canonical lexicon (92 vendors at v1.5.0; 51 v1.4.1 hub-visible + 1 v1.4.1 hidden_arm + 39 v1.5.0 cohort_prediction + 1 v1.5.0 hidden_arm).

## Data sources

Argus integrates data from **73 upstream sources** organized across five tiers, including (v1.1.0) UK Companies House, three US-state Secretary-of-State registries (Delaware / California / Texas), CourtListener / RECAP, SEC EDGAR, and SAM.gov Entity Registration, (v1.2.0) the fccid.io community aggregator + the official FCC Equipment Authorization System Filings UI, (v1.3.0) the Wave H Vendor Desktop Application Static Analysis methodology source, (v1.4.0) the Wave I/I.5/I.6/I.7 13-source cloud-infrastructure hostname corpus (crt.sh CT logs + Wayback CDX + GitHub vendor first-party + 5 Regional Internet Registry RDAP endpoints + NPM/PyPI/RubyGems + vendor cloud-storage payload class + Wave I extraction methodology umbrella), (v1.4.1) **5 vendor companion APK sources** (sids 67-71: Hikvision Hik-Connect, Dahua DMSS, Motorola Solutions WAVE PTT, Parrot FreeFlight 6, DJI Industry Pilot) admitted via [MAC-204](/MAC/issues/MAC-204) Phase 10b admit-then-rebind disposition under the sid=13 envelope (static analysis under 17 USC §1201(j) + 37 CFR §201.40(b)), and (new in **v1.5.0**) **2 lexicon-expansion-wave sources** (sid=72 GitHub Code Search REST API + sid=73 adsb.lol v2 FAA-registry-derived aircraft tracking) admitted via [MAC-232](/MAC/issues/MAC-232) and CP33 §1. Full per-source attribution + upstream-license chain at [CREDITS.md](CREDITS.md).

**Tier 1 — Canonical allocation registries** (`source_type='primary_registry'`):

- **IEEE OUI / MA-L / MA-M / MA-S / IAB registries** — vendor-to-OUI mappings; ~70,000 active identifier rows
- **FCC EAS Equipment Authorization Grantee Registrations** — 50,153-grantee corporate registrant lookup
- **FAA UAS Remote-ID Public DOC API (DETAIL endpoint)** — 427 active drone-class `drone_id_prefix` identifiers
- **Bluetooth SIG company-identifier registry** — 3,971 active `ble_manufacturer_id` allocations

**Tier 1/2 — Public records + procurement data**:

- **EFF Atlas of Surveillance** (CC-BY-NC-SA-4.0; NC clause carries forward) — 15,071 deployment_observations
- **DeFlock** (ODbL-1.0; license-compatible with compilation license) — 101,597 ALPR camera deployment_observations
- **USAspending.gov + Granicus Legistar** — federal/state/municipal procurement records (46,040 + 3); v1.1.0 expanded federal coverage by 2,560 records via a deep-extension cycle against USAspending.gov
- **Wireshark `manuf` file** — community-maintained OUI vendor-name cross-reference
- **WiGLE.net** — disabled by default in v1.0.0 (gated on user's WiGLE-grant quota; see [SETUP.md](SETUP.md))

**Tier 1 — Academic research** (`source_type='academic'`):

- **Marlin: Detecting IMSI-Catchers (NDSS Symposium 2025)** — academic foundation for behavioral_signatures table
- **RUB-SysSec/DroneSecurity (AGPL-3.0)** — Ruhr-University Bochum DJI Drone-ID research
- **GainSec/anti-crime-ecosystem-research (CC-BY-NC-ND-4.0 with research-use clause)** — CVE-anchored white paper

**Tier 2-3 — Vendor companion applications** (`source_type='manufacturer_app'` + `manufacturer_doc'`):

- **Hak5 product documentation, Flock Safety FS Installer, Getac BWC Viewer** — vendor companion apps statically analyzed under the 17 USC §1201(j) + 37 CFR §201.40(b) security-research exemption; decompiled source NOT redistributed per the decompiled-output non-redistribution rule

**Tier 1-3 — Community-research repositories** (`source_type='crowdsourced'` or `'academic'`):

22 canonical + 5 secondary-batch GitHub repositories contributing corroborating identifier observations across drone Remote ID, BLE tracker catalogs, IMSI-catcher detection, ALPR-camera profiles, and flock-detection cohorts. Two sources (GainSec anti-crime-ecosystem + GainSec falcon-sparrow-alpr-edl-firehose firmware) operate under the Feist facts-only promotion regime (NO_LICENSE_DECLARED public-but-unlicensed; factual extraction permitted per *Feist v. Rural Telephone Service* 499 U.S. 340 (1991); compilation arrangement NOT republished). Per-row sentinel `notes.upstream_license_posture='NO_LICENSE_DECLARED'` on these promoted rows.

**Tier 1 — Corporate registries** (`source_type='primary_registry'`; v1.1.0):

- **UK Companies House** (OGL-3.0; automated API) — international corporate-entity registry; first non-US primary registry. Used to close the Johnson Matthey PLC #00033774 Class B hold via international cross-check.
- **Delaware Division of Corporations** (operator_manual_only — CAPTCHA-gated) — US-shaped state registry; documented bounded operator path.
- **California Secretary of State — Bizfile** (operator_manual_only — Incapsula-gated) — US-shaped state registry; documented bounded operator path.
- **Texas Secretary of State SOSDirect** (operator_manual_only — paid-tier authentication) — US-shaped state registry; documented bounded operator path.

**Tier 1 — Judicial filings** (`source_type='judicial_filing'`; v1.1.0):

- **CourtListener / RECAP** (Free Law Project; CC0; automated with auth) — judicial-filing corpus for surveillance-procurement and challenge-case enrichment.

**Tier 1 — Federal disclosures** (`source_type='disclosure_filing'` + `'procurement_disclosure'`; v1.1.0):

- **SEC EDGAR** (PUBLIC_DOMAIN; automated HTML parse) — public-company disclosure filings.
- **SAM.gov Entity Registration** (PUBLIC_DOMAIN; automated API; cycle_completion_state=partial_pre_day1) — federal-procurement entity registry; first cycle landed 9,623 cross-source corroboration updates against existing rows (MAC-175).

**Tier 1/2 — FCC equipment-authorization expansion** (`source_type='regulatory'` + `'crowdsourced'`; v1.2.0):

- **fccid.io** (NO_LICENSE_DECLARED; automated HTML parse) — community aggregator of US FCC EAS filings; admitted under the Feist facts-only regime. 671 raw_observations staged under the new dual-citation-pair pattern; promotion deferred to the async FCC.gov re-citation pass.
- **FCC Equipment Authorization System — Filings** (PUBLIC_DOMAIN; automated HTML parse) — the official `apps.fcc.gov` Filings UI; distinct from the existing FCC EAS Grantee Registrations source. Admitted under a degraded-mode posture (Akamai-edge HTTP/2 INTERNAL_ERROR at extraction time); citation half of the 671-row deferred queue accumulates when egress is restored.

**Tier 3 — Lexicon-expansion-wave admissions** (v1.5.0; `source_type='crowdsourced'` + `'regulatory'`):

- **GitHub Code Search REST API** (sources.id=72; NO_LICENSE_DECLARED per-finding factual extraction under Feist; automated API) — GitHub's public code-search API (`GET /search/code`); per-finding URL template `https://github.com/{owner}/{repo}/blob/{sha}/{path}#L{line}` pinned-SHA + line-anchored per §11 #1 source-url-direct. Dominant first-party crowdsourced extraction surface for the v1.5.0 cohort_prediction wave.
- **adsb.lol v2 (FAA-registry-derived aircraft tracking)** (sources.id=73; PUBLIC_DOMAIN_EQUIVALENT FAA Part 47 + Feist on live ADS-B; automated API) — community-operated aircraft-tracking surface derived from live ADS-B broadcasts cross-referenced against the FAA Civil Aviation Registry (14 CFR Part 47 public record). Required for the persistent-surveillance cohort (aircraft-axis identifier surfaces — ICAO-24 hex, N-number, registry-operator chain).

## Output shape

Argus produces five canonical artifacts at v1.5.0:

| Artifact | Format | Content | Consumer |
|---|---|---|---|
| `db/argus.db` | SQLite | Canonical database (15 user tables; schema_version=27) | direct query / re-derivation |
| `exports/argus_export.json` | JSON | Standard Lynceus export (`{pattern, pattern_type, description, argus_record_id}` per row) | scanner-side watchlist (confidence ≥30) |
| `exports/argus_export_high_confidence.json` | JSON | High-confidence Lynceus export (same shape, confidence ≥70, `source_type` excludes `crowdsourced`+`inferred`) | scanner-side watchlist (operator-strict) |
| `exports/argus_export_behavioral_signatures.json` | JSON | Rayhunter-bound sibling export (`{signature_name, cellular_generation, threshold_json, confidence, argus_record_id}` per row) | RF-detection scanners |
| `exports/argus_export.csv` | CSV | Rich-import feed (15 columns; all active rows incl. `device_category='unknown'`) | analytical consumption / downstream re-derivation |

**Stable consumer-facing identifier:** `argus_record_id` is a 16-hex-char SHA-256 prefix: `sha256('<identifier_type>|<normalized_identifier>')[:16]`. Stable across re-runs, source-attribution changes, and confidence drift. Bind to this for cross-export consistency.

**CSV consumer note:** `argus_export.csv` line 1 is a `# meta:` comment with schema version / export timestamp / record count / confidence threshold. Line 2 is the column header. Consumers using `csv.DictReader` should skip line 1 or use a sniffer-aware reader (e.g., `pd.read_csv(comment='#')`).

## Provenance discipline

Every active `identifiers` row is traceable to:

1. **At least one `raw_observations` row** with `source_url` citing the upstream source verbatim (per the source-url-direct discipline; URLs are pinned-SHA + line-anchored, e.g., `https://example.com/path/to/file.ext#L<line>` or canonical `<repo>/blob/<sha>/<path>#<anchor>`)
2. **A `source_type` band** per the ten-value enum (`primary_registry` / `regulatory` / `manufacturer_doc` / `manufacturer_app` / `academic` / `foia` / `crowdsourced` / `inferred` / `procurement` / `official`) with calibrated confidence ceiling per band
3. **A `confidence` integer** in 0–99 (humility-margin invariant); corroboration math `min(99, max(originals) + 5)` per the corroboration-lift rule
4. **Per-row `notes` JSON** carrying license posture (`notes.upstream_license_posture` is the canonical sentinel-key for upstream license tracking), promotion-time citation, and audit-trail anchors

**Row-level reclassifications** (band changes, confidence changes, source_url upgrades) land an entry in the `source_reclassifications` audit table with `sweep_event_id` grouping + pre/post snapshot + rationale anchor. Forensic query: "show me every identifier ever reclassified, when, why, and by which sweep" is an O(1) query.

**Per-row license-tag handling** (migration 0016): `deployment_observations.LICENSE` is NOT NULL; carries the upstream source's license verbatim (Atlas rows: `'CC-BY-NC-SA-4.0'`; DeFlock rows: `'ODbL-1.0'`). Downstream consumers integrating Argus for commercial scanner deployments MUST honor the per-row LICENSE column. See [LICENSE-DATA §4.1](LICENSE-DATA) for the per-source taxonomy and downstream consumer guidance.

**No fabrication.** Hard-rule: identifiers and metadata derive from cited upstream sources only. No agent invents data; if a source doesn't yield concrete evidence, the answer is "no record" not "plausible record". See [METHODOLOGY.md §7](METHODOLOGY.md) for the full provenance discipline including third-party-citation-lineage boundary, no-PII discipline, and amendment-log discipline.

## Downstream consumers

Argus is designed as a producer of detection data for downstream RF-scanner consumers. The intended downstream architecture:

- **[Lynceus](https://github.com/kevwillow/lynceus-warden) (Raspberry-Pi-class RF security monitor)** — consumes `argus_export.json` (standard) or `argus_export_high_confidence.json` (operator-strict). Matches on `{pattern, pattern_type}` against live RF observations; alerts on match. Severity is owned operator-side via `severity_overrides.yaml`. Geographic-scope filter applied at export time.
- **[Rayhunter](https://github.com/EFForg/rayhunter) (cellular IMSI-catcher detector on supported modems)** — consumes `argus_export_behavioral_signatures.json` (Rayhunter-bound sibling export). Matches on `{signature_name, threshold_json}` against live cellular-control-plane observations.
- **Operator-side combined deployment** — an operator may run Lynceus + Rayhunter together on the same hardware; the two exports are non-overlapping (Lynceus = wire-observable patterns; Rayhunter = behavioral signatures).

**Operator-stack self-exclude discipline**: Argus operator-side hardware MUST NOT appear in the Lynceus high-confidence export. This covers (a) Lynceus host hardware (Raspberry Pi OUIs); and (b) Defensive-tool hardware (Rayhunter-supported modems including Orbic RC400L USB VID:PID `05c6:f601`/`f626`/`f622`, FY UZ801, PinePhone Quectel, Wingtech CT2MHS01, T-Mobile TMOHS1, TP-Link M7350/M7310). The exclusion is mandatory regardless of source confidence. Standard-export inclusion at `severity='low'` is permitted.

**Future v1.x consumer extensions** include scope proposals for additional scanner classes; per-scanner integration guidance is added to [METHODOLOGY.md §5.5](METHODOLOGY.md) when new export shapes are approved through the canonical-bible amendment process.

## Known held items (contribution welcome)

Argus's evolving canonical baseline includes several explicitly-documented held items where data is known to exist but is intentionally not yet promoted to canonical state. **These are NOT incomplete data; they are known held items pending the right additional evidence to admit them.** Future contributors may be exactly the right people to help unlock them. Items in this list closed since v1.0.0 are crossed off; new items surfaced during the v1.4.x / v1.5.0 cycles are added. The v1.5.x patch backlog + v1.6.0 deferred items queue is maintained at [PLANNED_AND_FUTURE_UPDATES.md](PLANNED_AND_FUTURE_UPDATES.md).

- **v1.5.x patch backlog items (per [PLANNED_AND_FUTURE_UPDATES.md](PLANNED_AND_FUTURE_UPDATES.md)):** Avigilon (id=6) + WatchGuard (id=17) arm-split under Motorola Solutions hub (per MSI 10-K FY2025 Exhibit 21 evidence chains; same shape as Pelco arm-split landed at v1.5.0 gate G-A); Geo Group admission + BI Incorporated (id=258) arm-split under new Geo Group hub (gate G-F deferred); 168-entry Elbit FCC grantee disambig sub-cycle (per-row anchor-verification before canonical promotion; estimated yield 5-20 confirmed); DJI aliases hygiene amendment (gate G-D — strip procurement-bundling contaminants from id=22 aliases comma-separated list; move legitimate product-family codenames to `notes.product_family_codenames[]` typed enrichment per CP25 §3 + SAR-17); NIITEK (id=241) zero-source re-attestation (`notes.zero_source_admission=true` flag for future cycle).
- **Phase 7-bis 177-row fccid.io cohort** ([MAC-194](/MAC/issues/MAC-194)) — HALT-released and queued. The cohort comprises 2AG-attested fccid.io rows pointing at the Parrot Automotive arm canonical (id=222) at `device_category='automotive_telematics'` (the schema slot opened by CP32 §1). Promotion is held; community contributions of cross-source corroboration for individual rows (independent of fccid.io) would unlock §8.3 lifts above the `crowdsourced` 75 ceiling. See [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP31 §5 for the structural context.
- **[MAC-218](/MAC/issues/MAC-218) — 8 orphan IEEE-registry `raw_observations` rows** awaiting hygiene-pass closure. No PII concern; structural cleanup. Backlogged for v1.5.x.
- **[MAC-208](/MAC/issues/MAC-208) — class-2 deferred carve-out follow-up.** CP32 §6 codified the wave_g_pre_v1 21-row carve-out as session-bounded (and explicitly NOT a future admission pathway); MAC-208 is the fork tracking the class-2 deferred subset. Backlogged.
- **CP30 reservation — `vendor_asn_prefix` + `vendor_controlled_ip` identifier_type codification** (Wave I.10 / I.13 falsified at zero empirical evidence). CP31 + CP32 + CP33 all preserved the reservation footnote. Permanent HOLD pending Wave I-prime ASN-prefix observation surfacing (RDAP url-pattern fix) and/or cert IP-SAN surface yielding non-zero in a future cycle.
- **`ble_service_uuid` Lynceus accept-list MAP question** — 30 SoundThinking `ble_service_uuid` rows at `confidence=85, device_category=gunshot_detect` are present in the canonical DB but currently drop under `_meta.dropped_in_export.ble_service_uuid` per the §4.4 alias-confirm open question (`db/validation/export_lynceus.py:152` "awaiting §4.4 alias confirm"). Decision driver for v1.5.x.
- **Multi-arm vendor backlog (CP32 §4 evidence-driven cadence)** — Cisco/Meraki, Harris RF vs Harris Aerial, Honeywell ACS division. v1.4.1 shipped Parrot Automotive (id=222) under Parrot (id=25); v1.5.0 shipped Pelco (id=254) under Motorola Solutions (id=3) per gate G-A. Future arm splits ship only when concrete identifier-row evidence attests to a specific arm; no calendar promotion.
- **NIITEK (id=241) zero-source admission** — admitted on cohort_prediction basis with zero-source attestation after wide-net sweep (Chemring through-wall radar subsidiary, intentionally low-profile US government vendor). `notes.zero_source_admission=true` + `notes.low_confidence_flag=true`; future v1.5.x cycle should re-attempt source attestation. Contribution path: surface any independent academic/regulatory source citing NIITEK product surface.
- **BriefCam (id=31) cctv_camera DEFERRED** — at v1.5.0 gate G-B retroactive recategorization, BriefCam was the sole face_recog/cctv-adjacent vendor NOT flipped to `primary_category='cctv_camera'` per board (analytics-layer ambiguity: BriefCam is a video-analytics overlay on top of arbitrary CCTV/VMS, not itself a CCTV camera). `primary_category='face_recog'` unchanged.
- **31 behavioral_signatures pending second-source corroboration.** IMSI-catcher behavioral patterns surfaced during initial extraction (AIMSICD, eylonK14 IMSI Catcher Detector, and adjacent community-research sources) that have single-source provenance and require independent second-source per the corroboration math. Contribution path: surface a second independent academic/regulatory source citing the same behavioral pattern.
- **61 Class B sustained holds remaining** (down from 62 at v1.0.0 — Johnson Matthey PLC #00033774 closed in v1.1.0 via UK Companies House cross-check; the Honeywell admission completion in v1.4.1 followed a similar evidence-arrival path via the [MAC-195](/MAC/issues/MAC-195) ACS division attestation rather than as a Class B hold closure). Under the PII default-to-HOLD rule, individual-shaped names without corporate-entity confirmation stay held. Contribution path: surface alternate corporate-entity registry citations.
- **133 IEEE Private permanent holds** (`pii_review_disposition='ieee_private_registrant_permanent_hold'`). IEEE OUI registrations declared as private at the registry source; cannot confirm ownership. Permanent HOLD by the PII discipline + IEEE-Private rule.
- **Known sources-row metadata discrepancy** — sources 1/2/3/7 carry historic `source_type='regulatory'` metadata pre-dating the source-type taxonomy refinement; identifier-row data is correctly labeled `primary_registry`. Cleanup queued post-ship. Downstream consumers filtering on `sources.source_type='primary_registry'` should also include `sources.id IN (1,2,3,7)` until the cleanup lands.

See [CHANGELOG.md "Known limitations + post-v1.0.0 roadmap"](CHANGELOG.md) for the full forward-roadmap including future community-source-acquisition waves, iOS coverage expansion, and Skydio Enterprise alt-channel scope.

## Contribution guidance

External contribution is welcome under the discipline framework codified in [PROJECT_BIBLE.md](PROJECT_BIBLE.md) (hard-rule set) and the sub-agent-rule additions in [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md). Specifically:

**For new sources** (community-OSINT GitHub repos, academic papers, regulatory registries, vendor docs):

- **Source-url-direct.** Every observation must cite a concrete file path within the source (e.g., `https://github.com/Owner/Repo/blob/<sha>/<path>#L<line>`). Bare repo URLs without per-row anchors are insufficient.
- **No PII.** Argus identifies *equipment categories*, not people. Officer names, badge numbers, home addresses — strip them. Per-row gate: `notes.pii_review_disposition='deferred_for_human_pii_review'` for any ambiguous case.
- **Provenance is the database.** Promotion to canonical state requires a `raw_observations` ancestor + `source_url` + cited `source_type` band per the source-type ceiling rules.
- **Confidence ceiling per source band.** No confidence drift upward without second-source corroboration per the corroboration math. Row-level reclassifications land in the `source_reclassifications` audit table.
- **Feist facts-only.** Public-but-unlicensed sources qualify for facts-only extraction; compilation arrangement (list-snippet verbatim copies; repository structure mirrors) is NOT republished. Per-row sentinel `notes.upstream_license_posture='NO_LICENSE_DECLARED'`.

**For new identifiers** (extending vendor coverage, new device categories, new behavioral signatures): submit via the standard GitHub PR process. Substantive contributions carry per-row provenance, source-band classification, and confidence rationale per the discipline framework above.

**For schema-impacting changes** (new tables, new `identifier_type` enum values, new `source_type` bands): coordinate with the canonical-bible amendment process documented at [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) — schema changes pair with `BIBLE_AMENDMENTS.md` entries per the amendment-log discipline.

**For vendor attribution disputes** (a vendor disagrees with their inclusion or categorization): open a GitHub issue describing the dispute. Argus's posture (Feist factual data + 17 USC §1201(j) + 37 CFR §201.40(b) + nominative fair use) governs the data-discipline response.

## Documentation

- [METHODOLOGY.md](METHODOLOGY.md) — methodology, provenance discipline, source-tier hierarchy, agent-orchestrated build process
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — schema reference for every table, column, and enum value
- [SETUP.md](SETUP.md) — local install, dependencies, optional API keys
- [CREDITS.md](CREDITS.md) — upstream attribution + 73 data-source credits + 92-entry surveillance-tech vendor lexicon
- [CHANGELOG.md](CHANGELOG.md) — version history from v1.0.0 → v1.5.0 including the full amendment ledger, migration ledger 1 → 27 (plus the v1.4.1 `Na_` sub-slot at 0026a), and pre-v1.0.0 history timeline
- [PLANNED_AND_FUTURE_UPDATES.md](PLANNED_AND_FUTURE_UPDATES.md) — v1.5.x patch backlog + v1.6.0 deferred items queue
- [PROJECT_BIBLE.md](PROJECT_BIBLE.md) — discipline architecture (hard rules, device_category vocabulary, Lynceus mapping, export shape)
- [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) — append-only amendment log with full case-study anchors
- [LICENSE](LICENSE) / [LICENSE-DATA](LICENSE-DATA) / [LICENSE-DOCS](LICENSE-DOCS) — three license texts (AGPL-3.0-or-later / ODbL-1.0 / CC-BY-SA-4.0) + Argus-specific preambles documenting scope-of-coverage + 3-layer per-row license-posture composition

## License

Argus ships under three licenses by artifact class:

- **Code:** [AGPL-3.0-or-later](LICENSE) — network-use copyleft preserves source-availability for derivative scanners; AGPL-3.0 inheritance-compatible with community-contributed sources at `sources.id` 38/40/43
- **Dataset:** [ODbL-1.0](LICENSE-DATA) with three-layer per-row license-posture composition:
  - Layer 1: `sources.notes.license_posture` (per-source declaration; 6 license-posture classes)
  - Layer 2: `deployment_observations.LICENSE` (per-row NOT NULL column; Atlas rows quarantined under CC-BY-NC-SA-4.0 NC clause)
  - Layer 3: `identifiers.notes.upstream_license_posture` (per-promoted-identifier canonical sentinel-key)
- **Documentation:** [CC-BY-SA-4.0](LICENSE-DOCS) — ShareAlike preserves discipline-architecture open-availability for derivative documentation

**For users producing derived datasets:** honor the upstream license carry-forward chain. Commercial deployments MUST exclude `deployment_observations.LICENSE='CC-BY-NC-SA-4.0'` rows (Atlas NC clause); standard ODbL ShareAlike applies otherwise. See [CREDITS.md §9](CREDITS.md) for the 4-layer re-derivation discipline + [LICENSE-DATA §4](LICENSE-DATA) for downstream consumer integration guidance.

**DMCA / takedown posture:** Argus's doctrinal grounding is Feist factual-data + 17 USC §1201(j) security-research exemption + 37 CFR §201.40(b) + nominative fair use. Vendor attribution disputes route through a GitHub issue.

---

## Canonical sources

Descriptive references used in this document map to canonical bible
anchors as follows. The canonical bible (`PROJECT_BIBLE.md` and the
amendment ledger `BIBLE_AMENDMENTS.md`) holds the authoritative
specification; this document is the public-facing summary.

| Descriptive reference (as used in this doc) | Canonical source |
|---|---|
| hard-rule set | `PROJECT_BIBLE.md` §11 |
| canonical 12-value `device_category` vocabulary / canonical lexicon | `PROJECT_BIBLE.md` §2.1 |
| multi-purpose-vendor carveout / multi-purpose-vendor discipline | `PROJECT_BIBLE.md` §11 #10, §11 #13 |
| decompiled-output non-redistribution rule | `PROJECT_BIBLE.md` §11 #15 |
| Feist facts-only promotion regime / Feist facts-only | `PROJECT_BIBLE.md` §11 #16 |
| canonical sentinel-key (`notes.upstream_license_posture`) | `PROJECT_BIBLE.md` §11 #16 |
| source-url-direct discipline | `PROJECT_BIBLE.md` §11 #1 |
| no-PII discipline / PII default-to-HOLD | `PROJECT_BIBLE.md` §11 #3 |
| amendment-log discipline | `PROJECT_BIBLE.md` §11 #11 |
| operator-stack self-exclude discipline | `PROJECT_BIBLE.md` §11 #12 + §8.4 |
| source-type ten-value enum / source-type ceiling rules | `PROJECT_BIBLE.md` §8.2 |
| confidence model | `PROJECT_BIBLE.md` §5 |
| corroboration math / corroboration-lift rule | `PROJECT_BIBLE.md` §8.3 |
| Lynceus mapping | `PROJECT_BIBLE.md` §4.4 |
| export shape | `PROJECT_BIBLE.md` §7.5 |
| source-type taxonomy refinement (registry-vs-regulatory) | `BIBLE_AMENDMENTS.md` CP15 |
| behavioral_signatures sibling export | `BIBLE_AMENDMENTS.md` CP18 |



## How I built this

Argus is the result of many long days and longer nights of iterative work across multiple machines — Windows dev boxes for some scraping and analysis work, Linux dev machines and a Linux server for the database, orchestration, and most agent work. The build process spans research, scraping, validation, schema design, license posture, discipline framework, and the audit trail that backs every promotion. The substantive growth from a 514-row baseline to over 35,000 active identifiers happened across roughly three weeks of compressed work; the architectural framework that makes those promotions trustworthy took longer.

### Operator-led orchestration

I plan and orchestrate this project myself, using Claude chat as a strategic-planning collaborator, paperclipai as the agent orchestration layer, and Claude Code as the execution agent across multiple specialist roles (extraction worker, source worker, validator, database architect, orchestrator). I have final decision authority on everything that lands in this repo. Strategic direction, architectural decisions, source-admission disputes, license posture, schema changes, and discipline-framework evolution are all operator-ratified before they commit.

The AI agents are highly capable executors with substantial scoping autonomy inside the constraints I set. They surface findings, propose decompositions, escalate when something needs ratification, and run extensive verification work I couldn't do at scale manually. But they don't decide canonical contract. I do.

This was not vibe-coded. Argus has 27 documented amendments to its canonical contract and 14 sub-agent rules governing how the build process itself operates. Every active identifier traces back to a verifiable public source via the audit trail. The discipline framework exists precisely because building a surveillance-equipment identification database is the kind of work where "looks roughly right" isn't good enough — provenance, confidence, and false-positive resistance all need to be load-bearing, not afterthoughts.

### Notable technical work

Two areas surfaced data that wasn't otherwise aggregated anywhere queryable:

**Vendor app decompilation.** I downloaded Android APKs of setup and admin apps published by surveillance-equipment vendors (Flock Safety being one substantive example) and analyzed the binaries for embedded identifier patterns — BLE service UUIDs, MAC address prefixes, vendor-specific protocol fields, default device names. Vendor setup apps need to recognize and connect to their own equipment, so they ship with the identifiers needed to do that. Decompiling public app-store binaries surfaced this information directly. This is legal reverse-engineering of publicly-distributed software, but it required actually doing the work rather than waiting for vendors to publish identifier schemas (they don't).

**GitHub researcher-repo aggregation.** Surveillance equipment has been studied by independent researchers for years — drone RID protocol work (alphafox02/DragonSync), cellular intercept detection (EFForg/rayhunter), BLE stalking-tracker research (seemoo-lab/AirGuard), FAA Remote ID database mirrors (jlrjr's wrapper), and more. The data exists across these projects but had never been pulled into a single queryable database with provenance discipline. Argus aggregates it: every identifier traces back to the specific researcher repo, the specific commit, the specific file path, with proper attribution under the original licenses. This is meta-research synthesis rather than primary discovery, but it makes a large amount of distributed researcher work actually usable.

### The discipline framework

The most substantive thing I built isn't the database. It's the framework that makes the database verifiable.

Every active identifier carries source attribution, confidence scoring, source-type classification, and a chain of corroboration. The framework includes hard rules that prevent fabrication (every identifier must trace to a concrete public source), PII discipline (individual-attributed registrations stay held, not promoted), and downstream-consumer protection (downstream scanners receive only high-confidence canonical data). The framework evolved with the work — each substantive amendment is documented with case studies showing what went wrong (or could have gone wrong) and why the rule exists.

Building this with AI tools is what made it possible at the scale and velocity it happened. Building it deliberately, with operator-final-say discipline and a binding correctness framework, is what makes the output trustworthy.



---

## Support the Project

This project was built as a hobby by one person, a couple computers, and a couple of LLMs. It burned through quite a bit of token cost and mass amounts of personal time — but it was worth it. If Argus saves you some time or you just think it's cool, consider tossing a few sats my way. No pressure, but coffee and compute aren't free.

- **Star this repo** — it's free and it helps others find the project
- **Submit an issue or PR** — bug reports and feature ideas welcome
- **Crypto donations** — if you're feeling generous:
  - **BTC** — `bc1qmtzjlc2cw2y45nea2jqf4deh946j8mq502zvsw`
  - **BTC (Unstoppable Domain)** — `gurutech.blockchain`
  - **LTC** — `ltc1qf32n038a90ulajlq6zz67r3n2myewpjlj2ej6w`
  - **ETH** — `0x9bf3311c4721fe37f58913dc57c2bf1722dc8a0f`
  - **BCH** — `bitcoincash:qr2l294kuve9cw48u7xek9nklhed066ycvjtj4ymq9`
  - **SOL** — `CuraE8usMpSrAhpY2QiWaQGoBjyJzkSaUNP6kRgAzscU`

- **Contact** — kev@gurutechnology.services
