# DATA_DICTIONARY.md — Argus schema reference

## TL;DR

The schema reference for Argus's SQLite database. Lists every table, every column, every CHECK constraint, every enum value, and every per-source row in human-readable form.

Current schema_version: **31** (post-mig-0031 CP39, **v1.6.3 ship state** — the mig-0031 column add originated in the v1.6.2.1 narrow-fork (CP39 severity column + §7.5 Flock-hunt floor carve-out) and was rolled into v1.6.3 per the board's "hold and push as v1.6.3" directive; v1.6.2.1 was never separately tagged. The v1.6.3 ship adds **no further schema mutations** — CP40 (Lynceus chip-vendor OUI remediation), CP41 (§11 #20 ratification + Avigilon/Pelco arm-flip backfill), and CP42 §1+§2 (export-correctness fixes) are all data / notes / code mutations, not schema mutations. `identifiers.severity` is an optional enum column, `'high'`/`'medium'`/`'low'`/`NULL`, default `NULL`. Narrow scope at v1.6.2.1 narrow-fork: 292 Flock-attested rows labeled `'high'`; post-CP40 Lynceus chip-vendor OUI remediation at v1.6.3 ship: **255 active `severity='high'` rows** (`SELECT COUNT(*) FROM identifiers WHERE severity='high' AND superseded_by IS NULL` live 2026-06-03 HEAD `7d3276e`); everything else `NULL` pending future cycles. See `BIBLE_AMENDMENTS.md` Correction Pass 39 for the rule body, Correction Pass 40 for the chip-vendor OUI remediation identifier-specificity gate, Correction Pass 41 for the §11 #20 Operator-DML-override ratification + Avigilon/Pelco arm-flip paper-trail closure, and Correction Pass 42 §1+§2 for the `imei_tac` Lynceus §4.4 disposition restoration + `DROPPED_REASONS` identity-keyed convention restoration. Prior schema_version 30 was the post-mig-0030 CP37 / v1.6.0 ship state and carried unchanged through the v1.6.2 stack). `identifier_type` enum: **58** values (unchanged at v1.6.3). `device_category` enum: **17** values (post-CP37 `+network_surveillance`; dual-table; unchanged at v1.6.3). `pair_kind` enum: 5 values (unchanged). `source_type` enum: **13** values (now dual-table — `sources.source_type` AND `identifiers.source_type` both 13 post-CP36; unchanged at v1.6.3). **`severity` enum (v1.6.2.1 narrow-fork; rolled in at v1.6.3 ship): 3 values (`high`/`medium`/`low`) + `NULL`.** Manufacturer arm rows: **8** (Avigilon id=6 under Motorola Solutions id=3; Parrot Automotive id=222 under Parrot id=25; Pelco id=254 under Motorola Solutions id=3; + v1.6.0 CP31 arm-splits — Grayshift id=281 under Magnet Forensics id=29; Anduril Anvil id=264 / Lattice OS id=265 / Roadrunner id=266 / Sentry Tower id=267 under Anduril Industries id=223). Two of these arm rows (id=6 Avigilon + id=254 Pelco) now carry `notes.arm_flip_history` per the v1.6.3 CP41 sibling backfill. Migration ledger: **0001 through 0031** (plus the `Na_` sub-slot addendum 0026a from CP32).

Intended audience: contributors writing migrations, validators reviewing schema-shape drift, consumers ingesting the exports programmatically, and downstream-tool authors building against the canonical row shape. The dictionary title preserves the historical v1.0.0 baseline anchor; subsequent Correction Pass refreshes layer the cumulative schema state forward.

For the user-facing dataset overview, see [`../USER_GUIDE.md`](../USER_GUIDE.md). For the formal canonical specification, see [`PROJECT_BIBLE.md`](PROJECT_BIBLE.md). For the per-amendment change log, see [`BIBLE_AMENDMENTS.md`](BIBLE_AMENDMENTS.md).

---

## §1. Introduction

This document is the canonical schema reference for the Argus SQLite database (`db/argus.db`). It enumerates every table, every column, every CHECK-constraint enum value, and every foreign-key relationship in the v1.0.0 ship. It is the operational companion to [METHODOLOGY.md](METHODOLOGY.md) (which covers the *semantics* — how confidence is assigned, how dedup works, how provenance binds) and [CREDITS.md](../../CREDITS.md) (which covers upstream attribution + license-chain).

**Audience:** downstream operators integrating Argus's exports, external researchers auditing the dataset, contributors adding new identifier candidates or methodology refinements, vendors reviewing how their equipment is represented.

**Scope:** v1.0.0 schema reference, cumulative through `schema_version=30` (live verification 2026-05-29 against `db/argus.db` at HEAD `def7b95`). The dictionary title preserves the historical v1.0.0 baseline anchor; subsequent CP refreshes carry the cumulative schema state forward. Future schema migrations land as paired commits per project amendment-log discipline; this document updates in lockstep.

**Last refresh anchor (v1.6.2 stack, 2026-05-29):** the **MAC-279 Phase-6 corrected-promote landing** ([MAC-288](/MAC/issues/MAC-288)) added 116 INSERT rows + 8 UPDATE confidence-or-provenance lifts (range id 42593–42708 contiguous), and the **MAC-291 §11 #1 strip** ([MAC-291](/MAC/issues/MAC-291)) demoted 36 Wave G/H v1 CCTV placeholder rows (15 OUI `00:00:00` + 2 OUI `01:01:01` + 1 OUI `ff:ff:ff` + 18 NDPP buckets across `224.0.0.251`/`1900`/`5353`/`8000`). Both are **data-only**: schema_version stays at 30; enum CHECK literals unchanged. Net v1.6.2 active delta: +80 (41,428 → 41,508). **Last schema-mutating refresh: Correction Pass 37 (2026-05-25)** — migration 0030 (`0030_cp37_device_category_network_surveillance`) — extends `identifiers.device_category` and `behavioral_signatures.device_category` CHECK from 16 → 17 values (`+network_surveillance` — dual-table CHECK literal sweep continuing the CP32 §1 / CP33 §2 precedent) for the Wave K + Wave L lawful-intercept cohort (Cognyte, Pen-Link, Polaris Wireless, SS8 Networks, Trovicor, Utimaco; **404 active `network_surveillance` rows** at the v1.6.2 stack — live 2026-05-29 `SELECT COUNT(*) FROM identifiers WHERE device_category='network_surveillance' AND superseded_by IS NULL`). `schema_version` 29 → 30. GATE-2: Anduril Lattice OS admitted under the existing `unknown` device_category (no new software-substrate enum value). **Ledger-token reconciliation (MAC-262):** the `cp35`→`cp36` `schema_version` row-29 `name` re-stamp remains **OPEN** at v1.6.2 (deferred DB mutation; structural schema is correct, only the descriptive CP-token diverges — see the row-29 footnote in §4.13). CP38 (FlockYou crowdsourced-ssid reconcile) is a data-only reclassification with **no schema mutation** (no `schema_version` bump). **Prior refresh Correction Pass 36 (2026-05-24)** — migration 0029 (`0029_cp36_identifiers_source_type_enum_parity`) — extends `identifiers.source_type` CHECK from 10 → 13 values (`+judicial_filing`, `+disclosure_filing`, `+procurement_disclosure`) for parity with `sources.source_type` (CP23/mig-0020). Closes the CPN-A enum-parity gap surfaced at MAC-249 Phase G; 116 J-5 CourtListener RECAP rows relabeled `foia`→`judicial_filing` (data-only sibling `0029_cp36_j5_proxy_relabel.sql`). See Finding F-A re: ledger CP-token. **Prior refresh Correction Pass 34 (2026-05-23)** — migration 0028 (`0028_cp34_network_discovery_protocol_pattern_identifier_type`) — extends `identifiers.identifier_type` CHECK from 57 → 58 values (`+network_discovery_protocol_pattern`; Wave G/H v1 CCTV installer cohort — Hikvision SADP, Dahua AirKiss/SmartConfig, Tiandy SADP-style, Axis ONVIF WS-Discovery; 18 high-conf promoted, 627 staged for next-cycle review). CP35 reserved for the standing NDPP §4.4 Lynceus-mapping draft (see F-A). Prior refresh **Correction Pass 33 (2026-05-22)** — migration 0027 (`0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac`) — extends `identifiers.device_category` and `behavioral_signatures.device_category` CHECK from 13 → 16 values (`+cctv_camera`, `+persistent_surveillance`, `+through_wall_radar` — second dual-table CHECK literal sweep continuing the CP32 §1 precedent) and `identifiers.identifier_type` CHECK from 56 → 57 values (`+imei_tac` forward-compatible admission per gate G-C; 0 promoted rows at v1.5.0 ship — schema slot opens for future Wave G/H companion-app extraction). v1.5.0 lexicon-expansion wave (Two-Session Parallel Dispatch; dispatch [MAC-232](/MAC/issues/MAC-232)) admitted **40 net-new manufacturers** (52 → 92) across 7 surveillance cohorts plus 2 §11 #10 multi-purpose carveouts; second multi-arm `hidden_arm` row (Pelco id=254 under Motorola Solutions id=3 per gate G-A). 31 retroactive cctv_camera recategorizations per gate G-B. SAR-16 + SAR-17 + SAR-18 codified. Two new sources admitted (sid=72 GitHub Code Search REST API; sid=73 adsb.lol v2). Schema-truth drift discipline: SAR-18 classifier-predicate parity extends SAR-13 PRAGMA-verify to runtime classifiers (coverage_matrix.py + export_lynceus.py share `_classify_row` predicates). Prior refresh **Correction Pass 32 (2026-05-21)** — migration 0026 (`identifiers.device_category` + `behavioral_signatures.device_category` dual-table CHECK enum extension 12 → 13 values; `+automotive_telematics` per CP32 §1 — the framework's first dual-table CHECK literal sweep in a single migration for enum parity); migration 0026a (first `Na_` sub-slot data-only addendum precedent — 5 INSERT OR IGNORE rows admitting sids 67-71 vendor APK sources via [MAC-204](/MAC/issues/MAC-204) Phase 10b admit-then-rebind; no schema mutation, no `schema_version` bump). CP32 codifies 10 sub-sections covering §1 schema landing + 9 narrative/discipline amendments (the `Na_` sub-slot convention itself, `superseded_by` tri-state semantics, §11 #3 export-time PII generator post-condition guard pattern, Lynceus exports per-bundle regen cadence, multi-arm vendor backlog admission cadence, §11 #17 session-bounded admission carve-out, sandbox-absence HALT-fast-path default sub-rule, MAC-206 carve-out export-drop attribution rule, future `identifiers.manufacturer_id` FK architectural binding). [MAC-219](/MAC/issues/MAC-219) / [MAC-220](/MAC/issues/MAC-220) Stage 2 ratification. Prior refresh **Correction Pass 31 (2026-05-20)** — migration 0025 (`identifiers.identifier_type` CHECK enum extension 54 → 56 values; CP31 FCC EAS identifier-type cluster — `fcc_grantee_code`, `equipment_class_code`; `identifiers.pair_kind` CHECK enum extension 4 → 5 — `fcc_grantee_equipment_class`; `manufacturers` schema +3 columns — `parent_manufacturer_id`, `is_arm`, `query_default`; first multi-arm hub-and-spoke admission with Parrot Automotive arm row id=222 inline conversion; [MAC-197](/MAC/issues/MAC-197) / [MAC-198](/MAC/issues/MAC-198) / [MAC-199](/MAC/issues/MAC-199) Stage 1 ratification). Prior refresh Correction Pass 29 (2026-05-20) — migration 0024 (`identifiers.identifier_type` CHECK enum extension 51 → 54 values; CP29 vendor cloud-infrastructure hostname corpus cluster — `vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`; MAC-183 v1.4.0 release sweep / Wave I/I.5/I.6/I.7 vendor cloud-infrastructure hostname corpus integration; SAR-13 + SAR-13.5 sibling-codified). Prior refresh Correction Pass 28 (2026-05-18) — migration 0023 (`identifiers.identifier_type` CHECK enum extension 48 → 51 values; Wave H desktop-axis vendor-registered non-BLE cluster — `windows_installer_productcode_vendor_registered`, `windows_com_clsid_vendor_registered`, `vendor_document_uuid_cloud_reference`; MAC-181 v1.3.0 release sweep / Wave H pre-v1 promotion). Prior refresh Correction Pass 27 (2026-05-18) — migration 0022 (`fcc_citation_deferred_queue` staging table, MAC-178 cycle-7 wave Priority 1 deliverable; persists the 671-row deferred FCC.gov re-citation backlog under the dual-citation-pair convention from CP26 + MAC-178 P1+P2). MAC-178 P7 ratified CP27 §2.4 (Empirical-Premise Verification Precondition). Prior refresh Correction Pass 23 (2026-05-17) — migrations 0020 (`sources.source_type` CHECK extension; 10 → 13 values) + 0021 (`procurement_records.vendor_canonical_normalized` column + index + backfill).

**Conventions:**
- Column shape: `name TYPE NOT NULL DEFAULT … CHECK(…)` notation matches the migration source-of-truth at `db/migrations/*.sql`.
- Enum values: enumerated in the column's CHECK constraint at the migration that introduced them.
- Foreign keys: notated as `→ table.column` per SQL convention.
- Cross-references to METHODOLOGY: `METHODOLOGY §X` (public-OSS-shipped artifact at repo root).
- Cross-references to BIBLE_AMENDMENTS.md (amendment entries): part of the audit trail; `BIBLE_AMENDMENTS.md` ships in repo.

**Source-of-truth precedence at any disagreement:** (1) the on-disk schema at `db/argus.db` (PRAGMA table_info verifies live column shape), (2) the migration SQL at `db/migrations/*.sql` (immutable historical record), (3) `PROJECT_BIBLE.md` schema-section canonical enum roster, (4) this DATA_DICTIONARY (derived narrative).

## §2. Glossary — database / dataset / pipeline

Throughout this document and the Argus project:

- **Database** refers to the queryable SQLite file at `db/argus.db`. It contains all tables documented in §4 of this file. Re-runs of the pipeline reproduce the database from upstream sources; the database file itself is regenerable, not the source-of-truth (the pipeline + upstream sources are).
- **Dataset** refers to the exported JSON/CSV artifacts at `exports/` (`argus_export.json`, `argus_export_high_confidence.json`, `argus_export.csv`). These are derived from the database via the export worker (METHODOLOGY §5 export thresholds). The dataset is what downstream scanners (e.g., Lynceus) consume; the database is the canonical Argus-internal state.
- **Pipeline** refers to the migration + source-loader + extraction + validator + export code that reproduces the database from upstream sources. The pipeline is licensed under AGPL-3.0-or-later per [LICENSE](../../LICENSE); the dataset is licensed under ODbL-1.0 per [LICENSE-DATA](../../LICENSE-DATA); documentation (this file, METHODOLOGY, README, etc.) is licensed under CC-BY-SA-4.0 per [LICENSE-DOCS](../../LICENSE-DOCS).

## §3. Schema overview

The v1.0.0 schema carries **15 tables**; cumulative through `schema_version=30` (post-CP37; the v1.6.0 ship-state). They group into four functional categories:

### §3.1 Canonical-state tables (Layer 1)

- **`identifiers`** — the canonical identifier table. Every row is an identifier-to-attribution binding promoted from `raw_observations` per the promotion-gate hard rule. 17 columns; see §4.1.

### §3.2 Provenance + source tables

- **`raw_observations`** — the provenance source-of-truth per METHODOLOGY §7.1. 15 columns; see §4.2.
- **`sources`** — the source registry. 8 columns; see §4.3.
- **`manufacturers`** — vendor metadata lookup. 7 columns; see §4.4.

### §3.3 Layer 2 + supporting tables

- **`deployment_observations`** — Layer 2 deployment-location records. 22 columns; see §4.5.
- **`procurement_records`** — procurement records. 14 columns; see §4.6.
- **`fcc_grantees`** — FCC EAS bulk-load grantee registry. 19 columns; see §4.7.
- **`council_minutes_matters`** — municipal Granicus Legistar matters. 27 columns; see §4.8.
- **`wigle_anchor_priority`** — WiGLE planning state (disabled in v1.0.0). 10 columns; see §4.9.
- **`behavioral_signatures`** — parametric metadata for behavioral signatures. 13 columns; see §4.10.

### §3.4 Operational tables

- **`conflicts`** — validator-side disputed rows. 9 columns; see §4.11.
- **`extraction_runs`** — per-run telemetry. 10 columns; see §4.12.
- **`schema_version`** — migration ledger. 3 columns; see §4.13.
- **`source_reclassifications`** — per-row source-band reclassification audit (added migration 0017 for the post-CP15 `primary_registry` band-correction sweeps). 13 columns; see §4.14.
- **`fcc_citation_deferred_queue`** — fccid.io discovery-row dual-citation-pair queue (added migration 0022 for the MAC-178 cycle-7 wave Priority 1 deliverable). 14 columns; see §4.15.

### §3.4.1 Live row counts

Verified against `db/argus.db` 2026-05-29 at HEAD `def7b95` (post-MAC-279 Phase-6 + MAC-291 §11 #1 strip; v1.6.2 stack):

| Table | Row count | Notes |
|---|---:|---|
| `identifiers` | **41,508 active** + 342 chained-superseded + 40 self-loop withdrawn-no-successor (4 pre-MAC-217 PII demotes + 36 MAC-291 §11 #1 strip demotes) | active = `superseded_by IS NULL` = **41,508**; total = **41,890**; demoted = 382 (= 346 pre-MAC-291 baseline + 36 MAC-291 strip). CP32 §9 tri-state semantic preserved (`NULL` = active / `<other_id>` = superseded by successor / `<self_id>` = withdrawn-no-successor PII-demote or §11 #1 strip-demote). Cumulative active deltas: +1 in v1.1.0 (Johnson Matthey PLC); +16 in v1.2.0 (MAC-178 P3); +12,239 in v1.4.0 (Wave I/I.5/I.6/I.7 hostname corpus); +172 in v1.4.1 (Stage 1 SAR-15.5 PASS); +848 in v1.5.0 (Stage 1 Step 5 promotions via [MAC-232](/MAC/issues/MAC-232) lexicon-expansion wave); +146 in v1.5.2 (CCTV cohort); +1,843 in v1.5.3 (Phase H, [MAC-250](/MAC/issues/MAC-250)); +3,627 in v1.6.0 (Wave K + Wave L combined ship, [MAC-275](/MAC/issues/MAC-275)); **+116 in v1.6.2 ([MAC-288](/MAC/issues/MAC-288) MAC-279 Phase-6 substantive promotion: range id 42593–42708 contiguous)**; **−36 in v1.6.2 ([MAC-291](/MAC/issues/MAC-291) §11 #1 strip demotion of Wave G/H v1 CCTV placeholder rows; 18 OUI + 18 NDPP)** — net v1.6.2 = +80 |
| `raw_observations` | **147,421** (append-only) | provenance source-of-truth |
| `sources` | **74** | source registry (+2 in v1.5.0: sid=72 GitHub Code Search REST API + sid=73 adsb.lol v2 FAA-registry-derived aircraft tracking; admitted under the v1.5.0 lexicon-expansion wave per [MAC-232](/MAC/issues/MAC-232) and CP33 §1. Cumulative: +5 in v1.4.1 vendor APK sources via mig-0026a — sids 67-71; +1 in v1.6.0: sid=77 CISA KEV — sids 74–76 are unassigned staging gaps, so the live row count is 74) |
| `manufacturers` | **126** | vendor metadata lookup (+34 net in v1.6.0 across the face_recog / spyware / lawful-intercept / forensic / counter-UAS cohorts, incl. 5 CP31 arm-splits. **8 arm rows total** at v1.6.2 (live `SELECT COUNT(*) FROM manufacturers WHERE is_arm=1`): Avigilon id=6 under Motorola Solutions id=3 (`cctv_camera`); Parrot Automotive id=222 under Parrot id=25 (v1.4.1; `automotive_telematics`); Pelco id=254 under Motorola Solutions id=3 (v1.5.0 per gate G-A; `cctv_camera`); Grayshift id=281 under Magnet Forensics id=29 (v1.6.0; `hacking_tool`); Anduril Anvil id=264 (`drone_detect`), Anduril Lattice OS id=265 (`unknown`), Anduril Roadrunner id=266 (`drone_detect`), Anduril Sentry Tower id=267 (`persistent_surveillance`) — all under Anduril Industries id=223 (v1.6.0). All 8 carry `query_default='hidden_arm'`. Retroactive cctv_camera recategorization per gate G-B Step 6 flipped 7 existing vendors (Hikvision/Dahua/Axis/Avigilon/Verkada/Eagle Eye Networks/Rhombus Systems) to `primary_category='cctv_camera'`; 31 identifier rows recategorized |
| `deployment_observations` | **116,774** | Layer 2 deployment-location records |
| `procurement_records` | **50,492** | analytical-only (never exported to Lynceus per §11 #14); +2,560 net-new in v1.1.0 via the MAC-172 USAspending deep-extension; further admissions across v1.2.x–v1.6.x bring the live total to 50,492 |
| `fcc_grantees` | **50,153** | FCC EAS bulk-load |
| `council_minutes_matters` | **3** | low-volume per format-fit cap discipline |
| `wigle_anchor_priority` | **80,697** | pre-computed query priority; WiGLE API integration itself disabled in v1.0.0 pending operator quota grant |
| `behavioral_signatures` | **201** | parametric metadata (added migration 0010); CP33 §2 mig-0027 extended `device_category` CHECK enum 13 → 16 (`+cctv_camera`, `+persistent_surveillance`, `+through_wall_radar`); CP37 mig-0030 further extended it 16 → 17 (`+network_surveillance`) — dual-table CHECK literal sweeps continuing the CP32 §1 precedent; 0 row promotions land through v1.6.2 (schema slots open for future evidence-arrival) |
| `conflicts` | **36** | validator-side disputed rows |
| `extraction_runs` | **121 rows / MAX(id)=126** | per-run telemetry. v1.6.2 stack added extraction_runs.id=125 (MAC-279 Phase-6 promote) + id=126 (MAC-291 strip) |
| `source_reclassifications` | **809** | per-row band-correction audit; added migration 0017 |
| `fcc_citation_deferred_queue` | **671** | dual-citation-pair queue, fccid.io discovery-half (added migration 0022); 0 promoted, 671 awaiting async FCC.gov re-citation pass |
| `schema_version` | **30** | migration ledger; one row per applied schema-mutating migration. mig-0026a (v1.4.1 `Na_` sub-slot data-only addendum) does NOT bump `schema_version` (filename↔schema_version 1:1 holds for schema-mutating migrations only); mig-0028 (CP34) + mig-0029 (CP36) + mig-0030 (CP37) are the post-v1.5.0 schema-mutating migrations (CP38 FlockYou reconcile is data-only — no `schema_version` bump; v1.6.2 stack MAC-279 Phase-6 + MAC-291 §11 #1 strip are likewise data-only) |

### §3.5 Relationship summary

```
raw_observations.source_id              → sources.id
raw_observations.extraction_run_id      → extraction_runs.id
raw_observations.promoted_identifier_id → identifiers.id
identifiers.superseded_by               → identifiers.id (self-reference)
identifiers.paired_identifier_id        → identifiers.id (self-reference)
deployment_observations.source_id       → sources.id
deployment_observations.extraction_run_id → extraction_runs.id
procurement_records.linked_identifier_id → identifiers.id
fcc_grantees.source_id                  → sources.id
council_minutes_matters.source_id       → sources.id
council_minutes_matters.linked_identifier_id → identifiers.id
wigle_anchor_priority.deployment_id     → deployment_observations.id (CASCADE)
behavioral_signatures.source_id         → sources.id (RESTRICT)
conflicts.identifier_a_id               → identifiers.id (CASCADE)
conflicts.identifier_b_id               → identifiers.id (CASCADE)
conflicts.raw_observation_id            → raw_observations.id (CASCADE)
fcc_citation_deferred_queue.promoted_raw_observation_id → raw_observations.id (SET NULL)
```

`identifiers.manufacturer` is matched by string equality to `manufacturers.canonical_name` (or the JSON-array `aliases` column); logical FK, not enforced.

## §4. Tables

### §4.1. `identifiers` (Layer 1 canonical)

The canonical Argus identifier table. Every row represents one identifier-to-attribution binding. Row count verified live 2026-05-29 at HEAD `def7b95` (post-MAC-279 Phase-6 + MAC-291 §11 #1 strip; v1.6.2 stack): **41,508 active** (`superseded_by IS NULL`); 342 chained-superseded (`superseded_by` points at a successor row) + 40 self-loop withdrawn-no-successor (`superseded_by = id`; 4 pre-MAC-217 PII-demotes + 36 MAC-291 §11 #1 strip-demotes) preserved per the CP32 §9 tri-state semantic. Total = 41,890; demoted total = 382. v1.6.2 net delta: +80 active = +116 from MAC-279 Phase-6 substantive promotion (MAC-288; range id 42593–42708 contiguous) − 36 from MAC-291 §11 #1 strip (18 OUI placeholder demotes + 18 NDPP placeholder demotes).

**`superseded_by` tri-state semantic (CP32 §9):** `NULL` = active / `<other_id>` = superseded by successor (canonical merge / dedup / deprecation) / `<self_id>` (self-loop) = withdrawn without successor (§11 #3 PII-demote OR §11 #1 strip-demote — both populate the self-loop case). Active-set query convention unchanged: `WHERE superseded_by IS NULL`. Withdrawn-without-successor query: `WHERE superseded_by = id`. The schema column itself (`superseded_by INTEGER REFERENCES identifiers(id) ON DELETE SET NULL`) has always admitted all three cases; CP32 §9 makes the semantic explicit so future consumer audits, JOIN logic, and active-set queries handle all three cases correctly. The §11 #1 strip-demote case is recorded on `notes.strip_audit` for each row.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. Stable per row; not directly exported to downstream consumers (consumer-facing stable identifier is `argus_record_id`, a 16-hex-char SHA-256 prefix; algorithm documented in [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) — see Canonical sources at end). |
| `identifier` | TEXT | yes | — | The identifier value itself (e.g., `aa:bb:cc:dd:ee:ff` MAC, `aa:bb:cc` OUI, `1581Fxxx` FAA RID drone prefix, `0x004C` BLE manufacturer ID, BLE service UUID, vendor SSID pattern). Normalization rules per identifier_type documented in METHODOLOGY §6.1 dedup-key normalization. |
| `identifier_type` | TEXT | yes | — | Enum extended cumulatively across migrations 0001–0028 (**58 canonical values at `schema_version=30`** — unchanged by mig-0029/0030; the v1.6.0 ship state). Baseline migration 0001: `oui`, `mac`, `mac_range`, `bssid`, `ssid_exact`, `ssid_pattern`, `ble_uuid`, `ble_service`, `device_fingerprint`. Migration 0009: `ble_local_name`, `ble_characteristic`, `product_family_codename`. Migration 0011: `ble_manufacturer_id`. Migration 0013: `drone_id_prefix`, `icao_24bit_address`, `rf_channel`, `burst_cadence_ms`, `bandwidth_mhz`, `device_class_id`, `rf_burst_duration`, `rf_protocol_constant`, `wifi_aware_service_name`, `wifi_ie_element_id`, `bluetooth_le_pdu_type`, `wifi_frame_control_subtype`, `wifi_nan_param_signature`. Migration 0014: `alpr_model`. Migration 0018: `ble_protocol_byte_table`, `ble_service_uuid`, `ble_company_id`, `frequency_band`, `ble_protocol_byte`, `operator_profile`, `x509_cert_sha256_prefix`, `ble_adv_interval`, `ble_payload_offset`, `firmware_sha256_hash`, `network_endpoint`, `firmware_image_variant`, `qualcomm_chip_format_id`, `firmware_branded_string`. Migration 0019 (CP21 round-2 vocab): `asdstan_message_type`, `asdstan_enum_value`, `dji_protocol_struct_format`, `gpt_partition_uuid`, `chipset_codename`, `firmware_build_string`, `firmware_build_uuid`. Migration 0023 (CP28 Wave H desktop-axis): `windows_installer_productcode_vendor_registered`, `windows_com_clsid_vendor_registered`, `vendor_document_uuid_cloud_reference`. Migration 0024 (CP29 Wave I vendor cloud-infrastructure hostname corpus): `vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`. Migration 0025 (CP31 FCC EAS identifier-type cluster): `fcc_grantee_code`, `equipment_class_code` — both DROPPED per §4.4 default at `device_category='unknown'` (CP32 §3 codified the disposition + landed DROPPED stubs in `db/validation/export_lynceus.py:DROPPED_REASONS`). **Migration 0027 (CP33 §2): `imei_tac`** — 8-digit IMEI Type Allocation Code; GSMA-allocated per manufacturer/model; structurally distinct from `device_class_id` at the RF protocol level and `firmware_branded_string` post-hoc strings; forward-compatible admission per gate G-C with 0 promoted rows at v1.5.0 ship — schema slot opens for future Wave G/H companion-app extraction surface. **Migration 0028 (CP34): `network_discovery_protocol_pattern`** — camera-discovery protocol pattern (Hikvision SADP port 8000, Dahua AirKiss/SmartConfig multicast, Tiandy SADP-style, Axis ONVIF WS-Discovery); 18 high-confidence rows promoted at CP34 (live `network_discovery_protocol_pattern` active count = 18); 627 lower-conf staged to `disambig_review_queue.json` for next-cycle review. The forward-codified `vendor_template_namespace_uuid` value (per the vendor-companion-app sub-banding amendment) is not in the current CHECK; it lands at first-promotion-time per the forward-looking-codification caveat. |
| `device_category` | TEXT | yes | — | Enum (**17 values** per on-disk CHECK constraint, post-mig-0030 / CP37): `alpr`, `imsi_catcher`, `body_cam`, `police_radio`, `drone`, `gunshot_detect`, `hacking_tool`, `covert_cam`, `gps_tracker`, `face_recog`, `drone_detect`, `unknown`, **`automotive_telematics`** (CP32 §1 — admitted via mig-0026 for enum parity with `manufacturers.primary_category` on the Parrot Automotive arm id=222), **`cctv_camera`** (CP33 §2 — admitted via mig-0027 for enum parity with the v1.5.0 camera_vms cohort manufacturers + retroactive cctv_camera recategorization (gate G-B) on 7 existing vendors with 31 identifier rows recategorized), **`persistent_surveillance`** (CP33 §2 — aerostat / lighter-than-air persistent platforms + tower-mounted persistent imaging + strategic-altitude aerial persistent surveillance), **`through_wall_radar`** (CP33 §2 — UWB through-wall radar systems; FCC §15.519 ultra-wideband regulatory carveout), **`network_surveillance`** (CP37 / mig-0030 — lawful-intercept / network-surveillance vendor cohort: Cognyte, Pen-Link, Polaris Wireless, SS8 Networks, Trovicor, Utimaco; 131 active rows at v1.6.0 ship, **404 active rows at the v1.6.2 stack** — live 2026-05-29 `SELECT COUNT(*) FROM identifiers WHERE device_category='network_surveillance' AND superseded_by IS NULL`). `unknown` rows are excluded from the Lynceus export per the multi-purpose-vendor discipline (canonical-only). Note: `behavioral_signatures.device_category` shares the same 17-value enum via the mig-0030 dual-table CHECK literal sweep (continuing the CP32 §1 / CP33 §2 precedent — CP21 cumulative-full-enum spirit applied across two separate CHECK literals in a single migration); 0 row promotions to `network_surveillance` on `behavioral_signatures` through the v1.6.2 stack (schema slot open for future evidence-arrival). |
| `manufacturer` | TEXT | no | NULL | Vendor name in canonical form. Logical FK to `manufacturers.canonical_name` (not enforced). |
| `model` | TEXT | no | NULL | Vendor's product name in marketing or internal form. Composes with METHODOLOGY §5.4 product-family taxonomy. |
| `confidence` | INTEGER | no | NULL | Integer per schema-level CHECK `BETWEEN 0 AND 100`. **Operational cap at 99** per METHODOLOGY §5 confidence model: the corroboration-boost formula `min(99, max(...) + 5)` + the §5.6 ceiling rule cap effective confidence at 99 (humility-margin invariant). Schema-level CHECK permits 0-100 to give the operational layer flexibility; the 99-cap is enforced at write-time by the validator/dedup pass, not the schema. |
| `source_url` | TEXT | yes | — | Working URL where the identifier was extracted. Per METHODOLOGY §7.2: direct citation, no aggregators. |
| `source_type` | TEXT | yes | — | Enum (**13 values**): `official`, `regulatory`, `procurement`, `academic`, `foia`, `crowdsourced`, `inferred`, `manufacturer_doc` (baseline); `manufacturer_app` (migration 0009); `primary_registry` (migration 0015); **`judicial_filing`, `disclosure_filing`, `procurement_disclosure` (CP36 / migration 0029 — enum parity with `sources.source_type`, closing the CPN-A gap from MAC-249 Phase G)**. Drives confidence band per METHODOLOGY §5.1. Live: 116 rows carry `judicial_filing` (J-5 CourtListener RECAP); `disclosure_filing` + `procurement_disclosure` are forward-compat (0 identifier rows). |
| `source_excerpt` | TEXT | no | NULL | Verbatim excerpt. Schema-level CHECK: `IS NULL OR length(source_excerpt) <= 200`. PII-sanitized per the no-PII hard rule. |
| `geographic_scope` | TEXT | no | NULL | Country-level scope: `US`, `EU`, `UK`, `global`, `unknown`, or specific ISO-3166 country code. Default export-time filter: `['US']`. |
| `first_seen` | DATETIME | no | NULL | UTC timestamp of first ingest. |
| `last_verified` | DATETIME | no | NULL | UTC timestamp of most-recent re-verification. |
| `notes` | TEXT | no | NULL | JSON blob carrying per-row metadata. **CP24 sub-rule (b) audit-trail conventions:** `notes.confidence_history[]` — required append-only audit-trail when `confidence` is UPDATED post-INSERT; each entry shape `{at_utc, from, to, rationale, dispatch, cp_anchor}`. `notes.corroborations[]` + `notes.corroboration_sessions[]` — provenance enrichment for within-source re-extraction (breadth-not-strength signal; does NOT lift confidence per §11 #8 sub-rule). `notes.cross_source_corroboration[]` — per-row cross-source corroboration markers from genuinely independent collectors (qualifies for §5.2 +5 lift). **CP25 §1 audit-trail convention:** `notes.cross_source_corroboration_reversals[]` — required append-only audit-trail when a `cross_source_corroboration[]` marker is retracted under §11 #1 or §11 #8 review; each entry shape `{at_utc, marker_key, rationale, dispatch, cp_anchor}`. The original corroboration-array entry is REMOVED (not soft-deleted); the reversal-array IS the audit-trail. First consumer: MAC-171 id=86738 SEC×USAspending recount drop. **CP39 / v1.6.2.1 narrow-fork field (rolled into v1.6.3 ship): `notes.crowdsourced_breadth_tier`** — per-row tier label (`'high'`/`'medium'`/`'low'`) tagging the §7.5 floor-carve-out tier assigned to Flock-hunt cohort rows at promotion / lift time. Emitted only on rows that fall under the CP39 §7.5 Flock-hunt floor carve-out (10 named Flock-hunt project sources — DeFlock, the `flock-you` family, GainSec's Flock research repos, etc.). Tier label drives the `severity` column assignment (`high` tier ⇒ `severity='high'`). Scope at v1.6.2.1 narrow-fork landing: 124 rows lifted at `severity='high'`; post-CP40 chip-vendor OUI remediation (v1.6.3): the 37-row Lynceus FP slice has been flipped out of `severity='high'` and now carries `notes.cp40_marker` (apply-time post-mutation audit anchor; see BIBLE_AMENDMENTS.md CP40). **CP40 audit-trail field (v1.6.3):** `notes.cp40_marker` / `$.cp40_audit` — apply-time post-mutation audit anchor on the 37-row Lynceus chip-vendor OUI remediation slice; records the identifier-specificity gate evaluation outcome that flipped each row out of `severity='high'`. See BIBLE_AMENDMENTS.md CP40 for the canonical schema. **Note on `notes` validity:** ~52,628 legacy plain-text rows pre-date the JSON-notes convention (MAC-44 era), and an additional ~106 rows carry a CP39-marker text-suffix appended after a JSON literal (`json_valid()=0`); both classes are tracked for wholesale-migration in a future CP slot (see PLANNED_AND_FUTURE_UPDATES.md v1.6.3 Patch Backlog). Downstream `json_set` / `json_extract` callers MUST `json_valid()`-check or scope-exclude legacy non-JSON rows. |
| `superseded_by` | INTEGER | no | NULL | Self-reference FK: if non-NULL, this row was superseded per METHODOLOGY §6.4. Exports filter on `superseded_by IS NULL`. |
| `paired_identifier_id` | INTEGER | no | NULL | Self-reference FK to a paired identifier per `pair_kind`. |
| `pair_kind` | TEXT | no | NULL | Enum (**5 non-NULL values + NULL** per on-disk CHECK constraint, post-mig-0025 / CP31): `la_bit_flip`, `frdid_sibling`, `vendor_as_container`, `firmware_generation` (all from migration 0012); **`fcc_grantee_equipment_class`** (CP31 mig-0025; extends CP14 paired-identifier discipline to regulatory entity pairing — `grantee_code` row is one identifier; `equipment_class_code` is a sibling row with `paired_identifier_id` pointing back to the grantee row and `pair_kind='fcc_grantee_equipment_class'`). `static_mac_tracker` is a deferred item (queued for future canonical-bible §-text codification) and is NOT currently in the enum. |

#### Indexes

Indexes follow the standard `idx_<table>_<column>` naming convention; primary lookup paths include `(identifier, identifier_type)`, active-set partial index on `(superseded_by IS NULL)`, `(manufacturer)`, and `(source_type, confidence)`. See `db/migrations/0001_initial.sql` and subsequent migration files for the full set.

#### Composition with METHODOLOGY rules

- Confidence integer is per METHODOLOGY §5 confidence model (default by `source_type`, corroboration boost per §5.2, ceiling rule per §5.6).
- `superseded_by` pointer semantics per METHODOLOGY §6.4 superseded-row preservation.
- `paired_identifier_id` + `pair_kind` semantics per the canonical-bible pairing discipline (LA-bit pairing, vendor-as-container, firmware-generation, FRDID pairing).

### §4.2. `raw_observations` (provenance source-of-truth)

Provenance layer per METHODOLOGY §7.1. Every promoted `identifiers` row is anchored to one or more `raw_observations` rows. Row count verified live 2026-05-29 at HEAD `def7b95`: **147,421** (cumulative through the v1.6.2 stack; +691 in v1.2.0 via MAC-178 P2 fccid.io discovery-row admission, of which 671 are paired to `fcc_citation_deferred_queue` per the dual-citation-pair convention; citation-half emission deferred to async re-citation pass). Append-only invariant: rows do not mutate post-ingest (validator processing updates `processed_at` + `promoted_identifier_id` + `notes` only; never the source-evidence fields).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `source_id` | INTEGER | no | NULL | FK → `sources.id`. |
| `extraction_run_id` | INTEGER | no | NULL | FK → `extraction_runs.id`. |
| `source_url` | TEXT | yes | — | Working URL fetched at ingest time. |
| `raw_payload` | TEXT | no | NULL | Verbatim source bytes (or JSON-encoded). PII-sanitized at ingest. |
| `candidate_identifier` | TEXT | no | NULL | Extracted identifier value. NULL when row is non-identifier metadata. |
| `candidate_type` | TEXT | no | NULL | Proposed `identifier_type`. |
| `candidate_category` | TEXT | no | NULL | Proposed `device_category`. |
| `candidate_manufacturer` | TEXT | no | NULL | Proposed manufacturer name. |
| `source_excerpt` | TEXT | no | NULL | Verbatim excerpt from `source_url`. Sized per the source-excerpt discipline: ≤200 chars baseline, with the broader window-around-match option (with `excerpt_type` field) for source-line >200 chars. (Distinct from the promotion-gate "no promotion without provenance" rule.) PII-sanitized per the no-PII hard rule. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of ingest. |
| `processed_at` | DATETIME | no | NULL | UTC timestamp of validator-side processing. NULL = not-yet-processed. |
| `promoted_identifier_id` | INTEGER | no | NULL | FK → `identifiers.id`. Non-NULL if promoted. |
| `notes` | TEXT | no | NULL | JSON blob: per-row metadata, archive-snapshot URLs, validator disposition notes. |
| `source_row_key` | TEXT | no | NULL | Idempotency anchor for re-ingest; deterministic hash over (`source_id`, structurally-significant fields). |

#### Indexes

Primary on `(id)`. Additional indexes on `(source_id, source_row_key)` for idempotency check and `(promoted_identifier_id)` partial index for canonical-row-to-provenance lookup.

#### Composition with METHODOLOGY rules

- Append-only per METHODOLOGY §7.1; rows never mutate post-ingest.
- Direct citation per METHODOLOGY §7.2 (no aggregators); archive snapshots in `notes`.
- No fabrication per the no-fabrication hard rule: extraction yielding no concrete value routes to `conflicts` (§4.11), not to a synthetic `raw_observations` row.
- PII-sanitization at ingest per the no-PII hard rule.

### §4.3. `sources` (upstream source registry)

Source registry. FK target for `raw_observations.source_id`. Row count verified live 2026-05-29 at HEAD `def7b95`: **74** (+7 in v1.1.0; +2 in v1.2.0: fccid.io sid=51 + FCC Equipment Authorization System — Filings sid=52; +1 in v1.3.0: Wave H sid=53; +13 in v1.4.0: Wave I cumulative source admissions sids 54-66; +5 in v1.4.1: vendor companion APK admissions sids 67-71 via mig-0026a `Na_` sub-slot; +2 in v1.5.0: sid=72 GitHub Code Search REST API (`crowdsourced`, tier 3) + sid=73 adsb.lol v2 FAA-registry-derived aircraft tracking (`regulatory`, tier 3), both admitted via the v1.5.0 lexicon-expansion wave per [MAC-232](/MAC/issues/MAC-232) and CP33 §1; **+1 in v1.6.0**: sid=77 CISA KEV (Wave L admission per [MAC-275](/MAC/issues/MAC-275)). Live count is 74 — sids 74–76 are unassigned staging gaps. Two existing sources cited heavily but NOT re-admitted per §11 #11 dedup-merge discipline: sid=51 fccid.io (60 v1.5.0 citations) + sid=54 crt.sh aggregator (747 v1.5.0 citations).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. Sources 1-3 are IEEE OUI registries (MA-L / MA-M / MA-S); the forward-looking source-level migration to `primary_registry` is deferred (queued as a post-ship batch task). |
| `name` | TEXT | yes | — | Human-readable source name. |
| `url` | TEXT | yes | — | Primary upstream URL. |
| `source_type` | TEXT | yes | — | Source-band classification. **CHECK constraint** post-migration 0020: 13 values — `'official'`, `'regulatory'`, `'procurement'`, `'academic'`, `'foia'`, `'crowdsourced'`, `'inferred'`, `'manufacturer_doc'`, `'manufacturer_app'`, `'primary_registry'`, plus **CP23 additions** `'judicial_filing'`, `'disclosure_filing'`, `'procurement_disclosure'`. Sources 1-3 (IEEE OUI) currently `'regulatory'` pending the deferred source-level reclassification. The 3 CP23 values are sources-tier taxonomy only; identifier-row promotion still binds on the separate `identifiers.source_type` enum (10 values, NOT extended in CP23). |
| `tier` | INTEGER | no | NULL | Tier classification per the canonical-bible source-tier hierarchy. |
| `last_fetched_at` | DATETIME | no | NULL | UTC timestamp of most-recent fetch. |
| `last_status` | TEXT | no | NULL | Status of most-recent fetch. |
| `notes` | TEXT | no | NULL | JSON blob: per-source metadata + license fields. **CP23 license-into-notes folding contract:** `notes.license` + `notes.license_attribution` + `notes.license_posture` + `notes.access_mode` + per-admission audit fields live INSIDE `notes`, NOT as top-level columns. Registered `notes.license` vocabulary (CP23 initial set; not a CHECK constraint, free-form for future extension): `OGL-3.0` (UK Companies House), `PUBLIC_DOMAIN` (US federal-gov per 17 USC §105), `US_STATE_PUBLIC_RECORDS` (DE/CA/TX SoS), `CC0` (CourtListener / Free Law Project), plus per-source declared postures (`MIT`, `AGPL-3.0_declared`, `CC-BY-NC-SA-4.0`, `ODbL-1.0`, `NO_LICENSE_DECLARED`, …). Registered `notes.access_mode` vocabulary (CP23): `automated_api`, `automated_html_parse`, `automated_with_auth`, `mixed_automated_manual`, `operator_manual_only`. Absent-access_mode is equivalent to `automated_api` per backward-compat. **CP26 partial-cycle admission contract:** `notes.cycle_completion_state` controlled vocabulary — `(absent)` (complete; backward-compat default), `partial_pre_day1` (admission before first full sweep — SAM.gov sid=50 cycle-5 day-0 first consumer), `partial_pacing_in_flight` (mid-multi-day pacing), `partial_pacing_exhausted` (pacing terminated short of completion). When non-absent, three companion fields REQUIRED: `next_cycle_dispatch_scheduled_for_utc` (ISO-8601 UTC), `next_cycle_dispatch_runguide_path` (relative path to dispatch artifact), `partial_yield_metrics_at_admission` (JSON snapshot of yield-at-admission). Orthogonal to `access_mode` (temporal-vs-mechanism). First-class column promotion deferred until value-set stabilizes per CP23 `access_mode` precedent. **`notes.candidate_findings_for_future_cp_or_sar[]` convention (CP25 §3 + CP26 §8):** array-of-objects describing held FP-classes where n<3 occurrences have been observed; held in this field until n≥3 occurrences elevate to a recognized §11 sub-rule. Per-entry shape: `{finding_id, observed_occurrences, first_seen_utc, sources_observed[], note}`. Promotion trail: BRINC `rico_co_defendant_not_customer_relationship` + `court_filing_fee_not_contract_value` entries staged on `sources[sid=48].notes` at MAC-174 P6 pushed the cumulative count to n=4, triggering CP26 §8 codification of "text-pattern match + semantic-relationship validation as default §4 match-scoring step"; held entries remain in the array as the historical audit-trail anchor (append-don't-mutate per source_reclassifications precedent). |

#### Indexes

Primary on `(id)`. Unique on `(name)`.

#### Composition with METHODOLOGY rules

- `sources.source_type` drives default confidence band for derived `raw_observations` per METHODOLOGY §5.1.
- Source-level reclassification (changing `sources.source_type`) does NOT retroactively reclassify `identifiers` rows whose direct provenance is third-party — per the third-party-citation-lineage boundary (METHODOLOGY §5.3 row-level discipline; §7.4 third-party-citation-lineage detail).

### §4.4. `manufacturers` (vendor metadata lookup)

Vendor metadata + alias canonicalization. Row count verified live 2026-05-29 at HEAD `def7b95`: **126** total (live `SELECT COUNT(*) FROM manufacturers`); 8 `query_default='hidden_arm'` (arm rows) + 118 `query_default='visible'` (hub rows). Cumulative: +1 in v1.1.0 (Johnson Matthey PLC); +14 in v1.2.0 (MAC-178 wave); +2 in v1.3.0 (Wave H Cohort A stubs — Eagle Eye Networks, Rhombus Systems); +1 in v1.4.1 (Parrot Automotive id=222 — first multi-arm `hidden_arm` row under CP31 hub-and-spoke schema); +40 net in v1.5.0 (21 Session 1 military/federal + 19 Session 2 commercial/consumer; Pelco id=254 admitted as second multi-arm `hidden_arm` row under Motorola Solutions id=3 per gate G-A); **+34 net in v1.6.0** (face_recog / spyware / lawful-intercept / forensic / counter-UAS cohorts per [MAC-275](/MAC/issues/MAC-275)), including 5 CP31 arm-splits (Grayshift id=281 under Magnet Forensics id=29; Anduril Anvil id=264 / Anduril Lattice OS id=265 / Anduril Roadrunner id=266 / Anduril Sentry Tower id=267 under Anduril Industries id=223). The 8 arm rows at v1.6.2 (live `SELECT id, canonical_name, parent_manufacturer_id, primary_category FROM manufacturers WHERE is_arm=1 ORDER BY id`): id=6 Avigilon (parent=3, `cctv_camera`); id=222 Parrot Automotive (parent=25, `automotive_telematics`); id=254 Pelco (parent=3, `cctv_camera`); id=264 Anduril Anvil (parent=223, `drone_detect`); id=265 Anduril Lattice OS (parent=223, `unknown`); id=266 Anduril Roadrunner (parent=223, `drone_detect`); id=267 Anduril Sentry Tower (parent=223, `persistent_surveillance`); id=281 Grayshift (parent=29, `hacking_tool`). Retroactive cctv_camera recategorization per gate G-B Step 6 flipped 7 existing manufacturers (Hikvision/Dahua/Axis/Avigilon/Verkada/Eagle Eye Networks/Rhombus Systems) to `primary_category='cctv_camera'`; 31 identifier rows recategorized. BriefCam (id=31) DEFERRED per board (analytics-layer ambiguity); `primary_category='face_recog'` unchanged.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. FK target for `procurement_records.manufacturer_id`. (Future-FK from `identifiers.manufacturer_id` is BINDING-only at v1.4.1 per CP32 §2; not yet a live column.) |
| `canonical_name` | TEXT | yes | — | Canonical vendor name. String-match target for `identifiers.manufacturer`. Word-boundary discipline: match `\bMotorola Solutions\b`, not `\bMotorola\b`. |
| `aliases` | TEXT | no | NULL | **Comma-separated TEXT string** of vendor-name aliases (e.g., `'Avigilon,Avigilon Corp,Avigilon Inc.,Avigilon Corporation'`); NOT a JSON array. Schema-truth formalized at Correction Pass 23 (wide-net cycle-3 §1 finding #1 + cycle-4 §1 finding #1). There is NO separate `manufacturers_aliases` table. Append semantics: `aliases = CASE WHEN aliases IS NULL OR aliases = '' THEN ? ELSE aliases || ',' || ? END WHERE id = ?`. Lookup semantics: `WHERE aliases LIKE '%term%' OR LOWER(canonical_name) = LOWER(?)`. |
| `primary_category` | TEXT | no | NULL | Primary `device_category` enum value (mirrors `identifiers.device_category` vocabulary; **17 values post-CP37**). NULL for multi-purpose vendors. Note: this column carries NO CHECK constraint (MAC-198 SKIP decision); the v1.4.1 Parrot Automotive arm row's `primary_category='automotive_telematics'` was admissible before mig-0026 landed the matching `identifiers.device_category` enum value (CP32 §1), establishing precedent for forward-codified primary_category populations. v1.5.0 cohort_prediction admissions use the same forward-codified pattern: 13 manufacturers populated at `primary_category='cctv_camera'`, 4 at `persistent_surveillance`, 3 at `through_wall_radar` ahead of mig-0027's schema admission of the matching identifiers.device_category enum values. |
| `source_url` | TEXT | yes | — | Primary attribution URL. |
| `notes` | TEXT | no | NULL | JSON blob: per-vendor metadata, corporate-split history (vendor-disambiguation discipline), absence-investigation records (`notes.admission_basis='documented_absence_only'`), ACS division / cert-supply-chain enrichment (`notes.honeywell_acs_division_attestation` per [MAC-195](/MAC/issues/MAC-195)). **CP41 / v1.6.3 field: `notes.arm_flip_history`** — paper-trail audit object for arm rows whose `is_arm` flag was flipped post-original-admission via the §11 #20 Operator-DML-override pattern. Shape: `{at_utc, from_state, to_state, dispatch, cp_anchor, operator_authorization, backup_file_sha256, predicate}`. The field closes the paper-trail loop for arm-flips that landed before the §11 #20 ratification (id=6 Avigilon under id=3 Motorola Solutions per CP33 §7; id=254 Pelco under id=3 Motorola Solutions per gate G-A). Live consumers at v1.6.3 ship: 2 rows (id=6 + id=254). Future post-admission arm-flips MUST populate this field per CP41 / §11 #20. See BIBLE_AMENDMENTS.md CP41 for the canonical schema. |
| `added_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of first registration. |
| `parent_manufacturer_id` | INTEGER | no | NULL | **CP31 mig-0025: multi-arm hub-and-spoke.** Self-reference FK → `manufacturers(id)`. Hub rows carry `parent_manufacturer_id IS NULL`; arm rows point at their hub. Parrot Automotive id=222 is the first arm row, pointing at the Parrot hub id=25. |
| `is_arm` | BOOLEAN | yes | `0` | **CP31 mig-0025.** `is_arm=0` for hub rows (the default; 51 rows at v1.4.1); `is_arm=1` for arm rows (1 row at v1.4.1: Parrot Automotive id=222). Composes with `query_default` for default-query filtering. |
| `query_default` | TEXT | yes | `'visible'` | **CP31 mig-0025.** CHECK enum 2 values: `'visible'` (hub rows + admitted-as-canonical arm rows; default) or `'hidden_arm'` (arm rows requiring explicit-opt-in for surfacing). **Default queries against `manufacturers` MUST filter `WHERE query_default = 'visible'` unless explicitly auditing arm rows.** Three explicit-opt-in paths surface arm rows: (1) explicit `WHERE query_default IN ('visible','hidden_arm')` audit query; (2) JOIN through `parent_manufacturer_id` for parent-child traversal; (3) direct FK reference from a future `identifiers.manufacturer_id` (CP32 §2 architectural binding — not a live column at v1.4.1). |

#### Indexes

Primary on `(id)`. Unique on `(canonical_name)`.

#### Composition with METHODOLOGY rules

- Multi-purpose-vendor discipline: `primary_category=NULL` cannot lift `device_category` off `unknown` at OUI level. Model-level evidence required.
- Corporate-split disambiguation (Motorola Mobility / Motorola Solutions etc.) per the vendor-disambiguation discipline; alias-iteration per the once-per-canonical iteration sub-rule.

### §4.5. `deployment_observations` (Layer 2 deployment-location records)

Layer 2 deployment-location records (Atlas of Surveillance + DeFlock). Row count verified live 2026-05-29 at HEAD `def7b95`: **116,774** (v1.0.0 baseline 116,668 = Atlas 15,071 + DeFlock 101,597; minor cumulative drift since). Per METHODOLOGY §7.5 and the no-PII hard rule, agency-level identification only; never individual-officer level.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `source_id` | INTEGER | no | NULL | FK → `sources.id`. |
| `extraction_run_id` | INTEGER | no | NULL | FK → `extraction_runs.id`. |
| `source_url` | TEXT | yes | — | Working URL. |
| `source_row_key` | TEXT | yes | — | Idempotency anchor. |
| `agency_name` | TEXT | no | NULL | Deploying agency name. |
| `agency_type` | TEXT | no | NULL | Agency classification per upstream taxonomy. |
| `juris_type` | TEXT | no | NULL | Jurisdiction shape. |
| `city` | TEXT | no | NULL | City name. |
| `county` | TEXT | no | NULL | County name. |
| `state` | TEXT | no | NULL | US state postal code or ISO subdivision. |
| `country` | TEXT | no | NULL | ISO-3166 country code. |
| `lat` | REAL | no | NULL | Latitude WGS84. |
| `lon` | REAL | no | NULL | Longitude WGS84. |
| `technology_category` | TEXT | no | NULL | **Free-text** (no CHECK constraint) passing upstream-taxonomy values through. v1.0.0 DB carries 13 distinct values: `ALPR` (DeFlock; 101,597 rows), and 12 Atlas-classified categories (`Body-worn Cameras`, `Automated License Plate Readers`, `Drones`, `Third-party Investigative Platforms`, `Face Recognition`, `Camera Registry`, `Gunshot Detection`, `Real-Time Crime Center`, `Predictive Policing`, `Video Analytics`, `Cell-site Simulator`, `Fusion Center`). Note: `ALPR` (DeFlock) and `Automated License Plate Readers` (Atlas) are semantically equivalent — downstream consumers reconciling across both upstreams should treat them as the same category. |
| `vendor_raw` | TEXT | no | NULL | Vendor name as recorded upstream (raw). Canonicalization deferred to query-time. |
| `citation_url` | TEXT | no | NULL | Secondary citation URL. |
| `source_excerpt` | TEXT | no | NULL | Verbatim excerpt. Schema-level CHECK enforces ≤200 chars at INSERT. The extraction-time source-excerpt discipline applies in addition (distinct from the promotion-gate hard rule). PII-sanitized per the no-PII hard rule. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of ingest. |
| `processed_at` | DATETIME | no | NULL | UTC timestamp of validator-side processing. |
| `notes` | TEXT | no | NULL | JSON blob. |
| `license` | TEXT | yes | — | Upstream license. **CHECK constraint** enumerates 5 values: `'ODbL-1.0'` (DeFlock; source_id=6), `'CC-BY-NC-SA-4.0'` (EFF Atlas; source_id=5), `'public-domain'` (reserved for future US-gov-public-domain ingest), `'foia'` (FOIA-released data per the canonical-bible FOIA discipline), `'unspecified'` (default for rows ingested pre-migration-0016 or license unknown at ingest). Migration 0016 added this column. Per CREDITS.md upstream-license-chain: Atlas-derived rows quarantine under the NC clause; downstream derivatives filtering on `license != 'CC-BY-NC-SA-4.0'` produce ODbL-1.0-compatible derivatives. |

#### Indexes (7 indexes per current schema)

Primary on `(id)`. Unique on `(source_id, source_row_key)` (idempotency). Additional on `(technology_category)`, `(vendor_raw)`, `(state)`, `(extraction_run_id)`, `(source_id)`.

#### Composition with METHODOLOGY rules

- **License carry-forward** per CREDITS.md: Atlas (source_id=5) rows quarantine under CC-BY-NC-SA-4.0 per upstream NC clause; the `license` column (migration 0016) is the operational hook.
- **Agency-only individuation** per the no-PII hard rule.
- **Procurement-vs-deployment caveat** per METHODOLOGY §5 and the canonical-bible deployment-evidence discipline.
- **Disambiguation discipline** per the codified vendor-disambiguation rule.
- **Vendor canonicalization deferred to query-time** per the alias-iteration sub-rules.

### §4.6. `procurement_records` (vendor-agency procurement records)

Vendor-to-agency purchase records. Row count verified live 2026-05-29 at HEAD `def7b95`: **50,492** (v1.1.0 baseline 46,043 = v1.0.0 43,483 + 2,560 net-new via the MAC-172 USAspending deep-extension cycle; cumulative additions across v1.2.x–v1.6.x bring the live total to 50,492). Procurement records prove *purchase*, NOT *deployment*; procurement-only records are excluded from the Lynceus export (canonical-only).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `agency_name` | TEXT | yes | — | Purchasing agency name. **Concatenated `"Awarding Agency / Awarding Sub Agency"`** per upstream USAspending shape (CP23 — cycle-3 §1 finding #5 schema-truth formalization). Split on `" / "` for hierarchical use. Per the no-PII hard rule: PII-sanitized at ingest (individual contracting-officer names stripped). |
| `agency_geographic_scope` | TEXT | no | NULL | ISO country/region code. |
| `vendor_canonical_name` | TEXT | yes | — | **Upstream USAspending verbatim recipient name** (CP23 — cycle-3 §1 finding #4 schema-truth formalization). NOT Argus-canonical. Often inconsistent across awards for the same vendor (e.g., `'AXON ENTERPRISE INC'` vs `'Axon Enterprise, Inc.'` vs `'AXON ENT INC'` all map to the same canonical entity). Cross-validation queries MUST use the companion `vendor_canonical_normalized` join key or an alias-aware JOIN against `manufacturers` (see `vendor_canonical_normalized` description below). |
| `vendor_canonical_normalized` | TEXT | yes | `''` | **Deterministic alias-collapse join key** (added migration 0021 at CP23). NOT NULL DEFAULT `''`. Materialized via `db/normalize_vendor.py::normalize_vendor_name`. Normalization algorithm (apply in order): (1) `LOWER()`; (2) strip ALL punctuation chars `. , ; : ' " ( ) [ ] { } / \ \`​ ~ ! @ # $ % ^ & * + = | < > ?`; (3) collapse runs of whitespace → single space; (4) strip leading/trailing whitespace; (5) repeatedly strip trailing whole-word suffix tokens (`inc`, `incorporated`, `corp`, `corporation`, `llc`, `l l c`, `ltd`, `limited`, `plc`, `co`, `company`, `lp`, `llp`, `gmbh`, `ag`, `sa`, `pty`, `bv`); (6) re-strip whitespace; (7) empty result stores `''`. Examples: `'AXON ENTERPRISE, INC.'` → `'axon enterprise'`; `'BERLA CORPORATION'` → `'berla'`; `'L3HARRIS TECHNOLOGIES, INC.'` → `'l3harris technologies'`. Live collapse evidence post-backfill: 1,157 distinct raw → 1,141 distinct normalized (0.9862 ratio); top wins `motorola solutions` (3 raw variants), `cellebrite`/`dedrone defense`/`engility`/`general dynamics information technology` (2 raw variants each). |
| `product_family` | TEXT | no | NULL | Vendor product family identifier. |
| `contract_amount_usd` | REAL | no | NULL | Contract dollar amount (USD). |
| `contract_date` | DATE | no | NULL | Contract execution date. |
| `source_url` | TEXT | yes | — | Per the canonical-bible provenance discipline. |
| `source_type` | TEXT | yes | — | **CHECK constraint** enumerates 4 values: `'procurement'`, `'foia'`, `'regulatory'`, `'official'`. Narrower subset than `identifiers.source_type` (10 values). |
| `source_excerpt` | TEXT | no | NULL | Schema-level CHECK enforces ≤200 chars. PII-sanitized per the no-PII hard rule. |
| `confidence` | INTEGER | no | NULL | Integer 0–100 per **CHECK constraint** (`confidence BETWEEN 0 AND 100`). Note: range diverges from `identifiers.confidence` operational cap (99) — procurement records are not subject to the METHODOLOGY §5 humility-margin invariant (identifier-attribution requires the residual-1-of-fabrication-risk margin; procurement records are about contract execution, a discrete event). See §6 confidence-shape divergence sub-section for the cross-table synthesis. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of ingest. |
| `linked_identifier_id` | INTEGER | no | NULL | FK → `identifiers.id` (`ON DELETE SET NULL`). |
| `notes` | TEXT | no | NULL | JSON blob. **CP24 sub-rule (b) audit-trail conventions (spirit-extension to procurement rows):** `notes.confidence_history[]` — required append-only audit-trail when `confidence` is UPDATED post-INSERT; shape `{at_utc, from, to, rationale, dispatch, cp_anchor}`. Live consumer: 180 rows rolled back 90→85 per CP24 strict-independence reading of §11 #8 (the MAC-172 USAspending deep-extension was within-source re-extraction, not cross-source corroboration). `notes.corroborations[]` + `notes.corroboration_sessions[]` — within-source re-extraction provenance enrichment (no confidence lift). `notes.cross_source_corroboration[]` — per-row cross-source corroboration markers from genuinely independent collectors (qualifies for §5.2 +5 lift); 9,623 UPDATEs landed in v1.1.0 from the MAC-175 SAM.gov cycle (Vigilant 56 + Motorola 9,545 + Genetec 22). `notes.cross_source_corroboration_reversals[]` — required audit-trail when a corroboration marker is retracted under §11 #1 or §11 #8 review (CP25 §1). |

#### Indexes

Primary on `(id)`. Additional on `(vendor_canonical_name)`, `(agency_name)`, `(linked_identifier_id)`, and (CP23 — migration 0021) **`(vendor_canonical_normalized)`** for alias-collapse join coverage.

#### Composition with METHODOLOGY + bible rules

- **Excluded from the Lynceus export**: procurement records with no concrete identifier are NEVER exported to Lynceus.
- **Procurement-vs-deployment caveat**: procurement proves *purchase*, not *deployment*.
- **Cross-table confidence cap at 85** per METHODOLOGY §5 + the canonical-bible procurement-corroboration rule when procurement records corroborate `identifiers` rows.
- **PII-sanitization** per the no-PII hard rule.
- **Alias-aware-join discipline (CP23)**: cross-validation queries against `procurement_records` MUST use the `vendor_canonical_normalized` join key or an alias-aware JOIN against `manufacturers.canonical_name` + `manufacturers.aliases`. Direct equality on `vendor_canonical_name` misses legitimate matches because the column carries upstream USAspending verbatim recipient names with vendor-side inconsistency across awards.

### §4.7. `fcc_grantees` (FCC EAS bulk-load grantee registry)

FCC Equipment Authorization System (EAS) grantee registry. Row count at v1.0.0: **50,153**. Used as the allowlist for `fcc_id_anchored` disambiguation (50,153-row corporate-registrant allowlist + CVE/CWE/NVD stop-list).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `source_id` | INTEGER | yes | — | FK → `sources.id`. |
| `extraction_run_id` | INTEGER | yes | — | FK → `extraction_runs.id`. |
| `source_url` | TEXT | yes | — | Working URL for FCC EAS upstream. |
| `source_row_key` | TEXT | yes | — | Idempotency anchor = `grantee_code`. |
| `grantee_code` | TEXT | yes | — | FCC-assigned 3-5 char alphanumeric grantee prefix (e.g., `'2APLW'` Flock Safety, `'2ADIY'` DJI). |
| `grantee_name` | TEXT | yes | — | Corporate registrant name. Word-boundary discipline applies. |
| `mailing_address` | TEXT | no | NULL | Corporate mailing address (public record). |
| `po_box` | TEXT | no | NULL | PO box. |
| `city` | TEXT | no | NULL | Registrant city. |
| `state` | TEXT | no | NULL | US state name or `N/A`. |
| `country` | TEXT | no | NULL | Country name. |
| `zip_code` | TEXT | no | NULL | Registrant ZIP. |
| `contact_name` | TEXT | no | NULL | Corporate compliance contact — corporate role only; individual operational-personnel names are not in this column per the no-PII hard rule. |
| `date_received` | TEXT | yes | — | ISO date. |
| `source_excerpt` | TEXT | no | NULL | Schema-level CHECK ≤200 chars. |
| `notes` | TEXT | no | NULL | JSON blob: raw row + Phase-5 hooks. |
| `captured_at` | TEXT | yes | `datetime('now')` | UTC timestamp (TEXT not DATETIME per FCC EAS migration convention). |
| `processed_at` | TEXT | no | NULL | UTC timestamp of validator-side processing. |

#### Constraints

`UNIQUE (source_id, source_row_key)` — idempotency-by-grantee_code.

#### Indexes (5 indexes per current schema)

Primary on `(id)`. Implicit unique on `(source_id, source_row_key)`. Additional on `(grantee_code)`, `(grantee_name)`, `(state)`.

#### Composition with METHODOLOGY + bible rules

- **`drone_id_prefix` composition** per the canonical-bible: FCC EAS grantees compose with FAA RID `drone_id_prefix` identifier-type at promotion.
- **FCC-ID disambiguation allowlist** for vendor attribution.
- **Vendor-name word-boundary discipline** per the codified vendor-disambiguation rule.
- **No PII promotion** per the no-PII hard rule: corporate compliance role only.

### §4.8. `council_minutes_matters` (municipal Granicus Legistar matters)

Municipal council / legislative matters where vendor procurement decisions are documented. Sourced from Granicus Legistar instances. Row count at v1.0.0: **3** (low-volume per the format-fit cap discipline). Largest table by column count in v1.0.0 (27 columns).

Per the canonical-bible no-fabrication hard rule and the Legistar-specific status-discipline sub-rule: only `matter_status='Passed'` rows are staged. PII-sanitization at ingest per the no-PII hard rule.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `source_id` | INTEGER | yes | — | FK → `sources.id`. |
| `extraction_run_id` | INTEGER | no | NULL | FK → `extraction_runs.id`. |
| `source_row_key` | TEXT | yes | — | Idempotency = `{legistar_client}:{matter_id}`. |
| `legistar_client` | TEXT | yes | — | Granicus Legistar instance: `'chicago'`, `'sfgov'`, `'detroit'`, `'hampton'`, `'cabq'` (5 jurisdictions; `cabq` = City of ALBuQuerque). |
| `agency_name` | TEXT | yes | — | Display name. |
| `agency_geographic_scope` | TEXT | no | NULL | ISO-shaped scope. |
| `matter_id` | INTEGER | yes | — | Legistar `MatterId` (jurisdiction-scoped). |
| `matter_guid` | TEXT | no | NULL | Legistar `MatterGuid`. |
| `matter_file` | TEXT | no | NULL | Human-readable matter file identifier. |
| `matter_title` | TEXT | yes | — | Matter title verbatim. PII-redacted at staging per the no-PII hard rule and the Legistar-specific staging sub-rule. |
| `matter_type_name` | TEXT | no | NULL | Legistar matter classification (free-text). |
| `matter_body_name` | TEXT | no | NULL | Deliberating body. |
| `matter_status_name` | TEXT | yes | — | Status name. Only `'Passed'` rows staged per the no-fabrication hard rule and the Legistar status-discipline sub-rule. Single-value-by-discipline; not CHECK-enforced for future expansion-flexibility. |
| `matter_intro_date` | DATE | no | NULL | Date introduced. |
| `matter_passed_date` | DATE | no | NULL | Date passed. |
| `matter_enactment_date` | DATE | no | NULL | Effective date. |
| `matter_cost` | TEXT | no | NULL | Dollar amount raw (Legistar TEXT shape). |
| `matched_vendor_label` | TEXT | yes | — | Canonical vendor label after disambiguation. |
| `vendor_canonical_name` | TEXT | yes | — | Vendor name as recorded upstream (raw); canonicalization deferred to query-time. |
| `source_url` | TEXT | yes | — | Per-matter Legistar UI URL. |
| `source_type` | TEXT | yes | — | **CHECK constraint** 3 values: `'procurement'`, `'foia'`, `'official'` (narrower than procurement_records 4-value enum). |
| `source_excerpt` | TEXT | no | NULL | Schema-level CHECK ≤200 chars. |
| `confidence` | INTEGER | yes | — | **Discrete CHECK constraint** `IN (70, 75, 80)` per the Legistar item-grading sub-rule. Distinct from continuous-range confidence in other tables. |
| `linked_identifier_id` | INTEGER | no | NULL | FK → `identifiers.id`. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of ingest. |
| `notes` | TEXT | no | NULL | JSON blob. |

#### Constraints

`UNIQUE (source_id, source_row_key)`.

#### Indexes (7 indexes per current schema)

Primary on `(id)`. Implicit unique on `(source_id, source_row_key)`. Additional on `(linked_identifier_id)`, `(extraction_run_id)`, `(matter_passed_date)`, `(matched_vendor_label)`, `(legistar_client)`.

#### Composition with METHODOLOGY + bible rules

- **Status-discipline**: only `'Passed'` rows staged.
- **PII-sanitization** at staging per the no-PII hard rule.
- **Canonical-label composition** with raw-upstream preservation.
- **Cross-table contribution to identifiers** per METHODOLOGY §5 corroboration-boost formula.

### §4.9. `wigle_anchor_priority` (WiGLE planning state; disabled in v1.0.0)

Pre-computed WiGLE-query priority rankings for `deployment_observations` rows. Row count at v1.0.0: **80,697**. **Operationally inert at v1.0.0 ship**: the WiGLE API integration itself is disabled pending the user's own WiGLE quota grant (per WiGLE Terms of Service).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `deployment_id` | INTEGER | yes | — | FK → `deployment_observations.id` (`ON DELETE CASCADE`). One-to-one via `UNIQUE (deployment_id)`. |
| `extraction_run_id` | INTEGER | no | NULL | FK → `extraction_runs.id`. |
| `priority_tier` | INTEGER | yes | — | **CHECK constraint** 1-5: T1 highest-priority US state-coded, T2 intermediate US state-coded, T3 lower-priority US state-coded, T4 US territory (PR/USVI/GU/AS/MP), T5 international (ISO 3166 alpha-2 country code). |
| `state_or_country` | TEXT | yes | — | Geographic anchor. T1-T4 US codes; T5 ISO 3166 alpha-2. |
| `intra_tier_rank` | INTEGER | yes | — | 1-based rank within `(priority_tier, state_or_country)`. |
| `tier_rationale` | TEXT | no | NULL | Short string explaining tier+rank choice. |
| `derivation_method` | TEXT | yes | — | **CHECK constraint** 2 values: `'atlas_state_column'` (Atlas direct), `'deflock_reverse_geocode'` (DeFlock via reverse_geocoder admin1 lookup). |
| `derivation_notes` | TEXT | no | NULL | Debug-trace metadata. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp. |

#### Constraints

`UNIQUE (deployment_id)`. CASCADE delete via `deployment_id` FK.

#### Indexes (6 indexes per current schema)

Primary on `(id)`. Implicit unique on `(deployment_id)`. Additional on `(extraction_run_id)`, `(derivation_method)`, `(state_or_country)`, `(priority_tier)`.

#### Composition with METHODOLOGY + bible rules

- **WiGLE disabled in v1.0.0** pending user WiGLE-quota grant (per WiGLE Terms of Service).
- **Pre-computation discipline**: rankings computed at v1.0.0 ship so post-grant activation is one-step.
- **`atlas_state_column` vs `deflock_reverse_geocode` derivation_method asymmetry**: Atlas provides state directly; DeFlock requires reverse-geocoding via the `reverse_geocoder` pip package (bbox+centroid alternative tested at 24.6% multi-match prevalence; Amarillo TX canary case demonstrates reverse_geocoder admin1 lookup is correct).
- **Disabled-but-materialized rationale**: rankings populated so post-grant activation is one-step.

### §4.10. `behavioral_signatures` (parametric metadata for behavioral signatures)

Parametric metadata for behavioral-class detection signatures. Introduced in migration 0010. Row count **201** (live `SELECT COUNT(*) FROM behavioral_signatures` 2026-05-29 at HEAD `def7b95`; unchanged from v1.4.1 through the v1.6.2 stack; v1.0.0 baseline 131 from the Marlin NDSS 2025 corpus + subsequent Wave I.x backfills carried into v1.4.x; CP33 §2 mig-0027 extended `device_category` CHECK enum 13 → 16 for `+cctv_camera`, `+persistent_surveillance`, `+through_wall_radar`, and **CP37 mig-0030 extended it 16 → 17 for `+network_surveillance`** — both dual-table sweeps maintain parity with `identifiers.device_category`, but 0 row promotions to any of these four values land on `behavioral_signatures` through the v1.6.2 stack — the schema slots open for future evidence-arrival).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `signature_name` | TEXT | yes | — | Signature identity. One `signature_name` per layer per Phase-2 self-review §2.4 staging-style (folds N code paths per signature). |
| `cellular_generation` | TEXT | no | NULL | **CHECK constraint** 4 values + NULL: `'2G'`, `'3G'`, `'4G'`, `'5G_NSA'`. |
| `threshold_json` | TEXT | no | NULL | **CHECK constraint** `json_valid()`. Structured thresholds. |
| `evidence_json` | TEXT | no | NULL | **CHECK constraint** `json_valid()`. Evidence dossier per the no-fabrication hard rule. |
| `source_id` | INTEGER | yes | — | FK → `sources.id` (`ON DELETE RESTRICT`). |
| `source_file_relative` | TEXT | no | NULL | File path relative to source repo. |
| `source_line` | INTEGER | no | NULL | Line number. |
| `confidence` | INTEGER | no | NULL | **CHECK constraint** `BETWEEN 0 AND 100`. The intake-time false-positive-class allowlist sub-rule applies. |
| `device_category` | TEXT | yes | — | **CHECK constraint** 17 values mirroring `identifiers.device_category` post-mig-0030 / CP37: `alpr`, `imsi_catcher`, `body_cam`, `police_radio`, `drone`, `gunshot_detect`, `hacking_tool`, `covert_cam`, `gps_tracker`, `face_recog`, `drone_detect`, `unknown`, `automotive_telematics`, `cctv_camera`, `persistent_surveillance`, `through_wall_radar`, `network_surveillance`. The CP37 / mig-0030 dual-table CHECK literal sweep (continuing the CP32 §1 / CP33 §2 precedent) maintains enum parity with `identifiers.device_category`; downstream consumers (Lynceus, exports, coverage matrix) treat `device_category` as a single conceptual vocabulary regardless of host table. |
| `notes` | TEXT | no | NULL | JSON or free-text. |
| `created_at` | DATETIME | no | `CURRENT_TIMESTAMP` | UTC timestamp. |
| `updated_at` | DATETIME | no | `CURRENT_TIMESTAMP` | UTC timestamp of last update. |

#### Constraints

`UNIQUE (signature_name, source_id, cellular_generation)` — 3-tuple (forward-proof; SQLite UNIQUE treats multiple NULLs as distinct).

#### Indexes (5 indexes per current schema)

Primary on `(id)`. Implicit unique on `(signature_name, source_id, cellular_generation)`. Additional on `(cellular_generation)`, `(device_category)`, `(signature_name)`.

#### Composition with METHODOLOGY + bible rules

- **Evidence dossier**: every row carries `evidence_json` traceability per the no-fabrication hard rule.
- **Unknown-category exclusion**: `device_category='unknown'` rows are excluded from the Lynceus export per the multi-purpose-vendor discipline.
- **Intake-time false-positive-class allowlist** applies at confidence assignment.

### §4.11. `conflicts` (validator-side disputed rows)

validator-side disputed rows awaiting manual disposition. Row count verified live 2026-05-29 at HEAD `def7b95`: **36** (cumulative through the v1.6.2 stack).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `identifier_a_id` | INTEGER | no | NULL | FK → `identifiers.id` (`ON DELETE CASCADE`). First conflicting identifier. |
| `identifier_b_id` | INTEGER | no | NULL | FK → `identifiers.id` (`ON DELETE CASCADE`). Second conflicting identifier (NULL for single-row conflicts). |
| `raw_observation_id` | INTEGER | no | NULL | FK → `raw_observations.id` (`ON DELETE CASCADE`). |
| `reason` | TEXT | yes | — | Conflict classification (free-text; common values: `'known_fake_pattern'`, `'category_disagreement'`, `'vendor_attribution_split'`, `'la_bit_sibling_vendor_mismatch'`). No CHECK constraint. |
| `detected_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp. |
| `resolved_at` | DATETIME | no | NULL | UTC timestamp of resolution. NULL = unresolved. |
| `resolved_by` | TEXT | no | NULL | Agent id or human. |
| `resolution_notes` | TEXT | no | NULL | Resolution narrative. |

#### Indexes (4 indexes per current schema)

Primary on `(id)`. Additional on `(identifier_a_id)`, `(identifier_b_id)`, partial on `(resolved_at) WHERE resolved_at IS NULL` (unresolved-queue).

#### Composition with METHODOLOGY + bible rules

- **No-fabrication**: uncertain extractions route to `conflicts` per METHODOLOGY §7.3.
- **Amendment-log discipline**: unresolved conflicts touching canonical-bible amendments halt new work until resolved.
- **Vendor-disambiguation false-positive class**: `'vendor_attribution_split'` is the canonical reason.
- **LA-bit sibling pairing mismatch**: `'la_bit_sibling_vendor_mismatch'` per the canonical-bible LA-bit pairing rule.
- **Cascade-delete protection** on all three FK columns prevents orphan conflicts.

### §4.12. `extraction_runs` (per-run telemetry)

Per-run telemetry: worker / source / records-in / records-out / status / notes for each extraction batch. Row count verified live 2026-05-29 at HEAD `def7b95`: **121 rows / MAX(id) = 126**. The v1.6.2 stack added id=125 (MAC-279 Phase-6 promote, agent `da137694…`, records_in=151 / records_out=124, status `completed`) + id=126 (MAC-291 §11 #1 strip — 36-row CCTV placeholder demotion).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. FK target for `raw_observations.extraction_run_id`, `deployment_observations.extraction_run_id`, `fcc_grantees.extraction_run_id`, `council_minutes_matters.extraction_run_id`, `wigle_anchor_priority.extraction_run_id`, `behavioral_signatures.extraction_run_id`. |
| `agent_id` | TEXT | yes | — | Agent identifier of the worker that ran the extraction (typically a UUID per Paperclip agent identity). |
| `source_id` | INTEGER | no | NULL | FK → `sources.id` (`ON DELETE SET NULL`). Source the extraction ran against. NULL for cross-source runs. |
| `started_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of run start. |
| `finished_at` | DATETIME | no | NULL | UTC timestamp of run completion. NULL = still running. |
| `records_in` | INTEGER | no | 0 | Count of input records read from the upstream source. |
| `records_out` | INTEGER | no | 0 | Count of `raw_observations` rows produced. |
| `errors` | INTEGER | no | 0 | Count of per-row errors during the run. |
| `status` | TEXT | no | NULL | Run status: `'running'`, `'ok'`, `'failed'`, `'partial'`. Free-text (no CHECK constraint). |
| `notes` | TEXT | no | NULL | JSON or free-text run notes (commit SHAs, run context, etc.). |

#### Indexes (3 indexes per current schema)

Primary on `(id)`. Additional on `(agent_id)`, `(source_id)`.

#### Composition with METHODOLOGY + bible rules

- **Append-only invariant per §7.1 composition**: rows do not mutate post-completion; `finished_at` + `status` + `records_out` + `errors` set at run completion. Notes may be amended for post-hoc audit (e.g., commit SHA cross-reference).
- **Per-run telemetry** ties every downstream artifact (`raw_observations`, `deployment_observations`, etc.) to a specific run for replay + audit.

### §4.13. `schema_version` (migration ledger)

Migration ledger: every applied migration has one row.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `version` | INTEGER | yes (PK) | — | Migration version number (sequential; current `MAX(version)=30` at the v1.6.2 stack, verified live 2026-05-29 at HEAD `def7b95`). |
| `name` | TEXT | yes | — | Human-readable migration name (e.g., `'0030_cp37_device_category_network_surveillance'`, `'0029_cp35_identifiers_source_type_enum_parity'`, `'0028_cp34_network_discovery_protocol_pattern_identifier_type'`, `'0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac'`, `'0026_cp32_device_category_automotive_telematics'`, `'0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke'`, `'0024_cp29_vendor_hostname_corpus_value_classes'`, `'0023_identifier_type_check_extension_cp28'`, …). Full ledger **0001–0030** enumerated below. Data-only addendum migrations using the `Na_` sub-slot convention (e.g., `0026a_phase10_vendor_apk_sources_admission`) do NOT register a `schema_version` row — they apply alongside the schema-mutating `N_` migration sharing the same numeric slot and modify data only. |
| `applied_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of migration application. |

Live migration ledger at `schema_version=30` (verified live 2026-05-29 at HEAD `def7b95`):

| version | name | applied_at |
|---:|---|---|
| 1 | `0001_initial` | 2026-05-04T03:29:04Z |
| 2 | `0002_deployment_observations` | 2026-05-04T05:07:21Z |
| 3 | `0003_fcc_grantees` | 2026-05-04T14:41:33Z |
| 4 | `0004_wigle_anchor_priority` | 2026-05-04T18:53:58Z |
| 5 | `0005_council_minutes_matters` | 2026-05-04T19:12:50Z |
| 6 | `0006_raw_observations_source_row_key` | 2026-05-05T12:53:35Z |
| 7 | `0007_motorola_solutions_aliases_rescope` | 2026-05-06T18:25:16Z |
| 8 | `0008_cp7_cp10_v01_cutover` | 2026-05-07T17:30:49Z |
| 9 | `0009_manufacturer_app_and_identifier_type_extensions` | 2026-05-10T20:40:15Z |
| 10 | `0010_behavioral_signatures` | 2026-05-11T17:13:55Z |
| 11 | `0011_ble_manufacturer_id_identifier_type_extension` | 2026-05-11T17:14:09Z |
| 12 | `0012_paired_identifier_id` | 2026-05-11T17:14:26Z |
| 13 | `0013_drone_rid_and_proprietary_protocol_identifier_types_extension` | 2026-05-11T17:14:50Z |
| 14 | `0014_surveillance_metadata_identifier_types_extension` | 2026-05-11T17:15:09Z |
| 15 | `0015_primary_registry_source_type_extension` | 2026-05-11T23:10:37Z |
| 16 | `0016_license_column` | 2026-05-12T17:41:41Z |
| 17 | `0017_source_reclassifications` | 2026-05-14T02:22:23Z |
| 18 | `0018_identifier_types_extension_batch` | 2026-05-14T05:47:15Z |
| 19 | `0019_identifier_types_round2` | 2026-05-14T17:24:59Z |
| 20 | `0020_source_type_enum_extension` | 2026-05-17T05:07:17Z |
| 21 | `0021_procurement_vendor_canonical_normalized` | 2026-05-17T05:07:32Z |
| 22 | `0022_fcc_citation_deferred_queue` | 2026-05-18T14:58:12Z |
| 23 | `0023_identifier_type_check_extension_cp28` | 2026-05-19T00:35:33Z |
| 24 | `0024_cp29_vendor_hostname_corpus_value_classes` | 2026-05-20T00:22:56Z |
| 25 | `0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke` | 2026-05-20T22:03:01Z |
| 26 | `0026_cp32_device_category_automotive_telematics` | 2026-05-21T16:54:12Z |
| 27 | `0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac` | 2026-05-22 |
| 28 | `0028_cp34_network_discovery_protocol_pattern_identifier_type` | 2026-05-23T02:32:32Z |
| 29 | `0029_cp35_identifiers_source_type_enum_parity` | 2026-05-24T02:40:36Z |
| 30 | `0030_cp37_device_category_network_surveillance` | 2026-05-25T01:26:01Z |

> **Ledger-token footnote (row 30, CP37):** unlike row 29, the row-30 `name` (`0030_cp37_device_category_network_surveillance`) matches its on-disk migration file verbatim — **no CP-token drift** at this slot. CP37 is correctly anchored at both the DB ledger and the file. (The CP35→CP36 row-29 re-stamp remains the only open ledger-token reconciliation; see the row-29 footnote.)

> **Ledger-token footnote (row 29):** the live `schema_version` row 29 `name` is enumerated verbatim above as `0029_cp35_identifiers_source_type_enum_parity` — the DB carries the pre-re-anchor **`cp35`** token. The on-disk migration files are `0029_cp36_identifiers_source_type_enum_parity.sql` + `0029_cp36_j5_proxy_relabel.sql`; the slot was re-anchored **CP35 → CP36** (CP35 reserved for the standing NDPP §4.4 Lynceus-mapping draft per [MAC-251](/MAC/issues/MAC-251)). The DB was stamped at apply-time before the re-anchor; the migration footer's `INSERT OR IGNORE` is keyed on `version` PK 29, so re-running the corrected `cp36` file is a no-op and the `cp35` name persists. Structural schema is correct (version 29; the `_identifiers_source_type_enum_parity` suffix + 13-value set match the file); only the descriptive CP-token diverges. The optional one-row `UPDATE schema_version SET name='0029_cp36_identifiers_source_type_enum_parity' WHERE version=29` re-stamp is a deferred DB mutation tracked at [MAC-262](/MAC/issues/MAC-262) — **still OPEN at the v1.6.0 ship** (not closed by Wave K+L; row-30/CP37 landed cleanly above without disturbing this slot). See BIBLE_AMENDMENTS.md "Correction Pass 36" + Finding F-A.

**Plus** `0026a_phase10_vendor_apk_sources_admission` — first `Na_` sub-slot data-only addendum precedent (codified at CP32 §1). Shares numeric slot 26 with the schema-mutating 0026 migration; admits 5 INSERT OR IGNORE rows into `sources` (sids 67-71) for the [MAC-204](/MAC/issues/MAC-204) Phase 10b admit-then-rebind disposition. No schema mutation, no `schema_version` ledger row.

**v1.5.0 mig-0027 detail:** extends `identifiers.device_category` and `behavioral_signatures.device_category` CHECK from 13 → 16 values (`+cctv_camera`, `+persistent_surveillance`, `+through_wall_radar` — second dual-table CHECK literal sweep continuing the CP32 §1 precedent), and extends `identifiers.identifier_type` CHECK from 56 → 57 values (`+imei_tac` forward-compatible admission per gate G-C; 0 promoted rows at v1.5.0 ship — future Wave G/H companion-app extraction surface will populate). Schema-truth drift discipline: `identifiers.pair_kind` enum value count = **5** (NOT 4 as the v1.5.0 dispatch's initial claim suggested); gate G-E disposition confirmed via direct `sqlite_master.sql` DDL read per [[feedback_pragma_alone_insufficient_for_sar13]]; `fcc_grantee_equipment_class` was already present from CP30 (mig-0024); pair_kind enum unchanged in mig-0027.

**mig-0028 (CP34) detail:** extends `identifiers.identifier_type` CHECK 57 → 58 (`+network_discovery_protocol_pattern`); `device_category`/`source_type`/`pair_kind` unchanged; `behavioral_signatures` untouched. **mig-0029 (CP36) detail:** extends `identifiers.source_type` CHECK 10 → 13 (`+judicial_filing`/`+disclosure_filing`/`+procurement_disclosure`) for parity with `sources.source_type`; identifier_type stays 58; data-only sibling `0029_cp36_j5_proxy_relabel.sql` relabels 116 J-5 rows `foia`→`judicial_filing` (no schema_version bump). **mig-0030 (CP37) detail:** extends `identifiers.device_category` and `behavioral_signatures.device_category` CHECK 16 → 17 (`+network_surveillance` — third dual-table CHECK literal sweep, continuing the CP32 §1 / CP33 §2 precedent) for the Wave K+L lawful-intercept cohort; `identifier_type` stays 58; `source_type`/`pair_kind` unchanged; **404 active `network_surveillance` rows on `identifiers` at v1.6.2 stack** (live 2026-05-29; v1.6.0 ship count was 131, with intervening promotions in the v1.6.x line surfacing additional rows), 0 on `behavioral_signatures` (schema slot open). CP38 (FlockYou crowdsourced-ssid reconcile) is data-only — no schema mutation, no `schema_version` bump. **v1.6.2 stack data-only changes** (MAC-279 Phase-6 promote + MAC-291 §11 #1 strip) likewise do NOT bump `schema_version`.

#### Indexes (1 index per current schema)

Primary on `(version)`. No additional indexes (small ledger; full-table scan acceptable).

#### Composition with METHODOLOGY + bible rules

- **Amendment-log discipline composition**: every schema-changing migration lands paired with a `BIBLE_AMENDMENTS.md` entry; the `schema_version` row is the runtime record of which migrations have been applied.
- **Forward-only invariant**: migrations are never rolled back; version monotonically increases.

### §4.14. `source_reclassifications` (band-correction audit)

Per-row source-band reclassification audit, added by migration 0017 to support the post-CP15 `primary_registry` band-correction sweeps (canonical case study: MAC-94+sweeps moving Wave-A FAA RID rows from `crowdsourced` → `primary_registry` per CP15 §8.2 strict reading). Append-only — corrective sub-sweeps land with distinct `sweep_event_id` values rather than mutating parent-sweep audit rows. Row count verified live 2026-05-29 at HEAD `def7b95`: **809** (stable since 2026-05-15).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `identifier_id` | INTEGER | yes | — | FK → `identifiers(id)` ON DELETE CASCADE. The reclassified row. |
| `sweep_event_id` | TEXT | yes | — | Groups all rows in one sweep dispatch (e.g., `'MAC-94-sweep-1'`). Same shape convention as `argus_run_id` for exports. Corrective sub-sweeps use a distinct `sweep_event_id` per the audit-table append-don't-mutate sub-rule. |
| `pre_source_url` | TEXT | yes | — | Source URL at sweep-start (snapshot). |
| `post_source_url` | TEXT | yes | — | Source URL after reclassification. |
| `pre_source_type` | TEXT | yes | — | Source-type band at sweep-start. |
| `post_source_type` | TEXT | yes | — | Source-type band after reclassification. |
| `pre_confidence` | INTEGER | yes | — | CHECK `BETWEEN 0 AND 100`. Confidence at sweep-start. |
| `post_confidence` | INTEGER | yes | — | CHECK `BETWEEN 0 AND 100`. Confidence after reclassification. |
| `reclassification_reason` | TEXT | yes | — | Per-row substantive rationale. Convention (NOT schema-enforced beyond NOT NULL): self-explanatory at row-level WITHOUT cross-referencing the dispatch — board's MAC-88 a1dab600 §2 refinement. |
| `reclassification_anchor` | TEXT | yes | — | CP / bible commit / dispatch citation (audit anchor). |
| `reclassified_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of the reclassification. |
| `notes` | TEXT | no | NULL | Optional additional context. |

#### Composition with METHODOLOGY + bible rules

- **§11 #8 (no confidence drift) audit composition**: every confidence/source-band correction lands one row per affected identifier; the audit record proves the correction was deliberate + substantively justified rather than confidence drift.
- **Append-don't-mutate sub-rule**: corrective sub-sweeps (when a CEO refinement comment races a worker commit) MUST use a distinct `sweep_event_id` and append new rows rather than mutating parent-sweep audit rows. Codified at MAC-96→MAC-98 c121bec→c12bedd. See `BIBLE_AMENDMENTS.md` SAR-13 §S.3 for the per-shape mapper precedent.

### §4.15. `fcc_citation_deferred_queue` (dual-citation-pair staging queue)

Persists the discovery-half of the dual-citation pair for FCC IDs surfaced from fccid.io (sid=51) when FCC.gov egress (apps.fcc.gov / Akamai-edge HTTP/2 INTERNAL_ERROR class) is blocked from the extraction host. Each row holds the fccid.io anchor + queue metadata the validator's async re-citation pass needs to emit the paired regulatory-band raw_observations row when FCC.gov egress is restored. Added by migration 0022 (MAC-178 cycle-7 wave Priority 1 deliverable, applied 2026-05-18T14:58:12Z). Row count verified live 2026-05-18T20:42:55Z: **671** (all unpromoted; 0 paired-citation emissions to date).

The dual-citation-pair convention itself was codified at CP26 (within-source corroboration sub-rule + MAC-174 P6 audit-trail precedent) and operationalized at MAC-178 P1+P2 (this table + the 671-row P2 admission of fccid.io discovery rows into `raw_observations`).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `fcc_id` | TEXT | yes (UNIQUE) | — | FCC equipment ID (e.g., `'2AG6IMPPU2'`). UNIQUE constraint enforces one queue entry per FCC ID. |
| `fccid_io_source_url` | TEXT | yes | — | fccid.io discovery-row URL (e.g., `'https://fccid.io/2AG6IMPPU2'`). The discovery-half anchor of the dual-citation pair per the CP26 within-source corroboration sub-rule. |
| `fccid_io_html_sha256` | TEXT | yes | — | SHA-256 of the fetched fccid.io HTML at discovery-time. Provenance integrity anchor per §11 #7. |
| `fcc_gov_unreachable_reason` | TEXT | yes | — | Verbatim failure mode prose explaining why FCC.gov was unreachable from the extraction host at discovery-time (e.g., `'http_code=000 + curl exit 92 (HTTP/2 INTERNAL_ERROR). Same failure mode observed in pre-flight; Akamai-edge access to apps.fcc.gov properties blocked from this host…'`). Per §11 #1 no-fabrication: the deferred-queue path exists precisely because the citation-half is unreachable; this column documents that condition rather than fabricating a citation. |
| `deferred_at_utc` | DATETIME | yes | — | UTC timestamp when the row was deferred (i.e., when the discovery row was emitted to `raw_observations` and the citation-half deferred to this queue). |
| `discovery_row_provisional_ids` | TEXT | no | NULL | JSON array of `raw_observations.id` values for the discovery rows this queue entry is paired with. Populated at MAC-178 P2 admission time. |
| `expected_citation_row_emission` | TEXT | no | NULL | Predicate prose describing what the async re-citation pass is expected to emit when FCC.gov egress is restored. Forward-documented at queue-load time so the async pass can verify it produced the expected shape. |
| `opportunistic_enrichment` | TEXT | no | NULL | JSON blob carrying queue-time-derivable metadata (e.g., `{"fcc_grant_ids": [...], "extraction_method": "fccid_io_html_v1", …}`). Opportunistic per the "discovery-row half does not mint identifier values" discipline — these enrichments stage to companion `raw_observations` rows, not derived identifier values. |
| `fcc_grant_ids_csv` | TEXT | no | NULL | Denormalized CSV of FCC grant IDs from `opportunistic_enrichment.fcc_grant_ids[]`. Indexed for grant-ID lookup. |
| `created_at` | DATETIME | no | `CURRENT_TIMESTAMP` | UTC timestamp of row insert. |
| `promoted_at` | DATETIME | no | NULL | UTC timestamp of paired-citation-emission. Non-NULL after the async re-citation pass emits the citation-half `raw_observations` row. NULL = still queued. |
| `promoted_raw_observation_id` | INTEGER | no | NULL | FK → `raw_observations.id` (`ON DELETE SET NULL`). The citation-half `raw_observations` row emitted by the async re-citation pass. Non-NULL paired with non-NULL `promoted_at`. |
| `notes` | TEXT | no | NULL | JSON or free-text — extraction-method-version anchors, post-promotion audit notes, etc. |

#### Constraints

`UNIQUE (fcc_id)` — implicit unique index `sqlite_autoindex_fcc_citation_deferred_queue_1`.

#### Indexes (3 indexes per current schema)

- Primary on `(id)`.
- `idx_fcc_citation_deferred_queue_pending` — partial index on `(promoted_at)` `WHERE promoted_at IS NULL`. Optimizes the drain-queue access pattern (the async re-citation pass iterates unpromoted rows).
- `idx_fcc_citation_deferred_queue_fcc_grant_ids` — on `(fcc_grant_ids_csv)` for grant-ID lookup joins.

#### Composition with METHODOLOGY + bible rules

- **§11 #1 no-fabrication**: queue holds verbatim discovery-row anchors + queue metadata; no derived identifier values are minted at queue-load time. Citation-half emission awaits the async pass against the actual FCC.gov source.
- **§11 #7 provenance**: `fccid_io_source_url` + `fccid_io_html_sha256` form the discovery-half anchors of the dual-citation pair. The citation-half (FCC.gov URL + content hash) is what the async pass adds via the paired `raw_observations` row. Provenance integrity is preserved across the deferred-emission boundary by the SHA-256 anchor.
- **§11 #8 no confidence drift**: staging-only — the queue table has no `confidence` column. Drained rows become regulatory-band `raw_observations` only when the async re-citation pass emits the paired citation row; confidence assignment happens at that promotion-time, not at queue-load.
- **CP26 within-source corroboration sub-rule (dual-citation-pair convention)**: the queue is the operationalization of CP26's "discovery + citation pair from the same source-class but distinct URLs" requirement. fccid.io is the discovery surface (community-aggregated); FCC.gov is the citation surface (regulatory-of-record). Both are required for promotion; this queue persists the gap.
- **CP27 §2.4 Empirical-Premise Verification Precondition (MAC-178 P7)**: the `fcc_gov_unreachable_reason` column carries the verbatim premise-verification artifact that justifies routing through the deferred queue rather than emitting a single citation directly.
- **No promotion sourced from queue rows alone**: the queue is operational state, not a source-of-truth for identifier promotion. Per §11 #8 strict reading, identifier rows promoted from the dual-citation pair derive their confidence from the citation-half `raw_observations` band, not from queue presence.

## §5. Enum reference (consolidated)

Canonical enum-value rosters across the schema, verified on-disk via `sqlite_master.sql` CHECK-extract (SAR-13 PRAGMA-alone-insufficient discipline — DDL read is authoritative; PRAGMA table_info hides CHECK enums) at the post-CP37 v1.6.2 stack (`schema_version=30`, verified live 2026-05-29 at HEAD `def7b95`). Migration 0027 (CP33 §2) extends `identifiers.identifier_type` CHECK from 56 → 57 values (`+imei_tac` forward-compatible admission per gate G-C) and `identifiers.device_category` + `behavioral_signatures.device_category` CHECK from 13 → 16 values (`+cctv_camera`, `+persistent_surveillance`, `+through_wall_radar`) in a second dual-table sweep continuing the CP32 §1 precedent. Migration 0026 (CP32 §1) extended `device_category` 12 → 13 (`+automotive_telematics`) in the first dual-table sweep; migration 0025 (CP31) extended `identifier_type` 54 → 56 (`fcc_grantee_code`, `equipment_class_code`). Migration 0028 (CP34) extended `identifier_type` 57 → 58 (`+network_discovery_protocol_pattern`). Migration 0029 (CP36) extended `identifiers.source_type` 10 → 13 (`+judicial_filing`/`+disclosure_filing`/`+procurement_disclosure`). Migration 0030 (CP37) extended `identifiers.device_category` + `behavioral_signatures.device_category` 16 → 17 (`+network_surveillance`) in a third dual-table sweep.

### §5.1. `identifiers.identifier_type` — 58 values

The cumulative roster across migrations 0001–0028 (58 values; unchanged through `schema_version=30`). The CP33 §2 net-new value (`imei_tac`) added at mig-0027 carries **0 promoted rows at v1.5.0 ship** (forward-compatible admission per gate G-C — 8-digit IMEI Type Allocation Code; GSMA-allocated per manufacturer/model; structurally distinct from `device_class_id` at the RF protocol level and `firmware_branded_string` post-hoc strings); future Wave G/H companion-app extraction will populate. The CP31 net-new values (`fcc_grantee_code`, `equipment_class_code`) added at mig-0025 carry first-row promotion at v1.4.1 — `fcc_grantee_code` × 17 rows + `equipment_class_code` × 41 rows per the [MAC-201](/MAC/issues/MAC-201) §7.5-bis structural-anchor lift cycle. CP29's `vendor_cloud_endpoint_url` carried 1 first-row promotion in the v1.4.x cycle. Remaining values are codified at the schema layer; promotion lands per evidence-arrival.

Baseline (migration 0001): `oui`, `mac`, `mac_range`, `bssid`, `ssid_exact`, `ssid_pattern`, `ble_uuid`, `ble_service`, `device_fingerprint`.

Migration 0009: `ble_local_name`, `ble_characteristic`, `product_family_codename`.

Migration 0011: `ble_manufacturer_id`.

Migration 0013: `drone_id_prefix`, `icao_24bit_address`, `rf_channel`, `burst_cadence_ms`, `bandwidth_mhz`, `device_class_id`, `rf_burst_duration`, `rf_protocol_constant`, `wifi_aware_service_name`, `wifi_ie_element_id`, `bluetooth_le_pdu_type`, `wifi_frame_control_subtype`, `wifi_nan_param_signature`.

Migration 0014: `alpr_model`.

Migration 0018 (CP21 round-1): `ble_protocol_byte_table`, `ble_service_uuid`, `ble_company_id`, `frequency_band`, `ble_protocol_byte`, `operator_profile`, `x509_cert_sha256_prefix`, `ble_adv_interval`, `ble_payload_offset`, `firmware_sha256_hash`, `network_endpoint`, `firmware_image_variant`, `qualcomm_chip_format_id`, `firmware_branded_string`.

Migration 0019 (CP21 round-2): `asdstan_message_type`, `asdstan_enum_value`, `dji_protocol_struct_format`, `gpt_partition_uuid`, `chipset_codename`, `firmware_build_string`, `firmware_build_uuid`.

Migration 0023 (CP28 Wave H desktop-axis vendor-registered non-BLE cluster — §8.2 sub-band ladder 75–90 / 75–90 / 80–95 per BIBLE_AMENDMENTS CP28(c); §4.4 posture DROPPED / DROPPED / MAP respectively): `windows_installer_productcode_vendor_registered`, `windows_com_clsid_vendor_registered`, `vendor_document_uuid_cloud_reference`.

Migration 0024 (CP29 vendor cloud-infrastructure hostname corpus — Wave I/I.5/I.6/I.7 cumulative; CP29 §2 ladder 75-90 default / 85-95 cross-source / 95-99 firmware-cert ceiling for hostname; 80-90 / 90-97 for url; 80-87 for deprecated; §4.4 posture MAP / MAP / DROPPED-for-active-scan-MAP-for-historical-attribution respectively): `vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`.

Migration 0025 (CP31 FCC EAS identifier-type cluster — both DROPPED per §4.4 default at `device_category='unknown'` per CP32 §3; landed DROPPED stubs in `db/validation/export_lynceus.py:DROPPED_REASONS`): `fcc_grantee_code` (3-5 char FCC EAS grantee prefix; regulatory entity identifier), `equipment_class_code` (3-char FCC EAS equipment-class code; paired with grantee via `pair_kind='fcc_grantee_equipment_class'`).

Migration 0027 (CP33 §2 — forward-compatible admission per gate G-C; 0 promoted rows at v1.5.0 ship — schema slot opens for future Wave G/H companion-app extraction surface): `imei_tac` (8-digit IMEI Type Allocation Code; GSMA-allocated per manufacturer/model; structurally distinct from `device_class_id` at the RF protocol level and `firmware_branded_string` post-hoc strings).

Migration 0028 (CP34 — Wave G/H v1 CCTV installer cohort; 18 high-conf promoted, 627 staged for next-cycle review): `network_discovery_protocol_pattern` (camera-discovery protocol pattern — Hikvision SADP, Dahua AirKiss/SmartConfig, Tiandy SADP-style, Axis ONVIF WS-Discovery).

Forward-codified (NOT in current CHECK): `vendor_template_namespace_uuid` per the forward-looking-codification caveat in the vendor-companion-app sub-banding amendment; `vendor_asn_prefix` + `vendor_controlled_ip` per CP29 §3 deferral (0 empirical observations through Wave I.x cumulative; **CP30 reservation slot preserved** — CP31 + CP32 + CP33 all skipped CP30 to hold the reservation; admission criteria gate on Wave I-prime ASN-prefix observation surfacing and/or cert IP-SAN surface yielding non-zero).

### §5.2. `identifiers.device_category` + `behavioral_signatures.device_category` — 17 values

`alpr`, `imsi_catcher`, `body_cam`, `police_radio`, `drone`, `gunshot_detect`, `hacking_tool`, `covert_cam`, `gps_tracker`, `face_recog`, `drone_detect`, `unknown`, **`automotive_telematics`** (CP32 §1 — mig-0026 dual-table CHECK literal sweep; the framework's first such sweep), **`cctv_camera`** (CP33 §2 — mig-0027 dual-table CHECK literal sweep; IP-CCTV / closed-circuit camera category — Hikvision, Dahua, Axis, Avigilon, Verkada, Eagle Eye, Rhombus, Hanwha, Milestone, Pelco, Uniview, Tiandy, Vivotek), **`persistent_surveillance`** (CP33 §2 — aerostat / lighter-than-air persistent platforms + tower-mounted persistent imaging + strategic-altitude aerial persistent surveillance — TCOM 74M aerostat, Anduril Sentry Tower, Elbit IFT, General Atomics MQ-9 for CBP AMO, Persistent Surveillance Systems), **`through_wall_radar`** (CP33 §2 — UWB through-wall radar systems — Camero Xaver, NIITEK Chemring VMR, TiaLinx Eagle-NV; FCC §15.519 ultra-wideband regulatory carveout — operationally restricted to law-enforcement use), **`network_surveillance`** (CP37 / mig-0030 — lawful-intercept / network-surveillance vendors: Cognyte, Pen-Link, Polaris Wireless, SS8 Networks, Trovicor, Utimaco; 131 active `identifiers.device_category` rows at v1.6.0 ship; **404 active rows at the v1.6.2 stack**). Cross-reference BIBLE_AMENDMENTS.md CP33 §2 + CP37 for full per-value definitions and admission rationale. 0 row promotions to `behavioral_signatures.device_category` for the 3 new CP33 §2 values nor `network_surveillance` (CP37) through the v1.6.2 stack (the schema slots open; future cycles populate).

### §5.3. `identifiers.source_type` — 13 values (post-mig-0029 / CP36)

`official`, `regulatory`, `procurement`, `academic`, `foia`, `crowdsourced`, `inferred`, `manufacturer_doc`, `manufacturer_app`, `primary_registry`, **`judicial_filing`, `disclosure_filing`, `procurement_disclosure`**.

The CP23 trio originally landed on `sources.source_type` only (mig-0020); **CP36/mig-0029 brought `identifiers.source_type` to parity** after MAC-249 Phase G CPN-A surfaced the gap (J-5 RECAP rows had been proxied to `foia`). Identifier rows now bind directly: 116 `judicial_filing` live; `disclosure_filing`/`procurement_disclosure` forward-compat (0 rows).

### §5.3a. `sources.source_type` — 13 values (post-migration 0020)

`official`, `regulatory`, `procurement`, `academic`, `foia`, `crowdsourced`, `inferred`, `manufacturer_doc`, `manufacturer_app`, `primary_registry`, **`judicial_filing`** (CP23 — CourtListener / RECAP-class), **`disclosure_filing`** (CP23 — SEC EDGAR / corporate-disclosure), **`procurement_disclosure`** (CP23 — supplier-self-disclosure / vendor-side procurement artifacts).

### §5.4. `procurement_records.source_type` — 4-value subset

`procurement`, `foia`, `regulatory`, `official`.

### §5.5. `council_minutes_matters.source_type` — 3-value subset

`procurement`, `foia`, `official`.

### §5.6. `deployment_observations.license` — 5 values

`ODbL-1.0`, `CC-BY-NC-SA-4.0`, `public-domain`, `foia`, `unspecified`.

### §5.7. `identifiers.pair_kind` — 5 non-NULL values + NULL

`la_bit_flip`, `frdid_sibling`, `vendor_as_container`, `firmware_generation` (all from migration 0012), **`fcc_grantee_equipment_class`** (CP31 mig-0025 — extends CP14 paired-identifier discipline to FCC EAS regulatory entity pairing), NULL. (CP31 mig-0025 admitted `fcc_grantee_equipment_class` at v1.4.1 ship; the v1.5.0 cycle gate G-E disposition confirmed the 5-value count via direct `sqlite_master.sql` DDL read after a PRAGMA-output reading error initially suggested 4 — no migration needed; pair_kind enum unchanged in mig-0027.)

Forward-codified (NOT in current CHECK): `static_mac_tracker` is a deferred item; lands at future canonical-bible §-text codification.

### §5.8. `behavioral_signatures.cellular_generation` — 4 non-NULL values + NULL

`2G`, `3G`, `4G`, `5G_NSA`, NULL.

### §5.9. `wigle_anchor_priority.priority_tier` + `derivation_method`

- `priority_tier`: 1, 2, 3, 4, 5 (CHECK `BETWEEN 1 AND 5`).
- `derivation_method`: `atlas_state_column`, `deflock_reverse_geocode`.

### §5.10. Confidence-shape divergence

See §6.2 for the cross-table confidence-shape divergence synthesis (4 shapes: identifiers / procurement_records / council_minutes_matters / behavioral_signatures).

## §6. Cross-references to METHODOLOGY

### §6.1. Provenance + confidence

- METHODOLOGY §5 (Confidence model): source-type bands + corroboration boost + ceiling rule define how `identifiers.confidence` and cross-table corroboration contributions compose.
- METHODOLOGY §6 (Dedup logic): how duplicate rows collapse to a canonical row; superseded-row preservation per §6.4.
- METHODOLOGY §7 (Provenance discipline): `raw_observations` as source-of-truth (§7.1); `source_url` discipline (§7.2); no-fabrication (§7.3); third-party-citation-lineage boundary (§7.4); no-PII (§7.5); amendment-log discipline (§7.6).

### §6.2. Confidence-shape divergence across tables

Four confidence shapes ship in v1.0.0, each defensible per its domain. Two-axis distinction: schema-level CHECK constraint vs operational cap.

| Table | Schema-level CHECK | Operational cap | Rationale |
|---|---|---|---|
| `identifiers.confidence` | `BETWEEN 0 AND 100` | **99** (METHODOLOGY §5 humility-margin invariant; enforced at corroboration-boost + ceiling-rule layers) | Identifier-attribution carries fabrication-risk residual; perfect-certainty never claimed |
| `procurement_records.confidence` | `BETWEEN 0 AND 100` | 100 (no operational cap below schema) | Contract-execution is discrete event; no humility-margin needed |
| `council_minutes_matters.confidence` | discrete `IN (70, 75, 80)` | (schema-level; no operational adjustment) | Legistar item-grading sub-rule; discrete tier reflects matter shape + vendor-specificity |
| `behavioral_signatures.confidence` | `BETWEEN 0 AND 100` | TBD at promotion per the intake-time false-positive-class allowlist | (covered in §4.10) |

**Cross-table corroboration semantics**: when non-identifier-table rows (procurement / council_minutes / behavioral_signatures) corroborate `identifiers.confidence` per METHODOLOGY §5.2, the contributing-source-type ceiling applies. Per METHODOLOGY §5.6 and the canonical-bible procurement-corroboration rule: procurement records cap cross-table corroboration at confidence 85 ("Procurement records add geographic context but never raise an identifier above 85 confidence by themselves"). Council-matters contribute at the matter's discrete-grading value (70/75/80) but cap at the source-type ceiling per `source_type` band (procurement / foia / official).

### §6.3. Export shape composition

- `argus_export.json` (METHODOLOGY §5.5 standard export, ≥30 confidence): wire-observable rows excluding `device_category='unknown'` per the multi-purpose-vendor discipline.
- `argus_export_high_confidence.json` (≥70 confidence): same exclusions + the default `geographic_scope` filter (`['US']`).
- `argus_export.csv` (rich-import feed): all active rows including analytical-only.

## §7. Maintenance posture

This document updates in lockstep with schema migrations and canonical-bible amendments:

- **Schema migrations** (any `db/migrations/NNNN_*.sql` landing): the affected table sub-section in §4 updates; §5 enum reference roster updates if CHECK constraints change.
- **Canonical-bible amendments** to the schema-section enum roster: documented in `BIBLE_AMENDMENTS.md`; this document inherits via the §5 enum reference roster.
- **METHODOLOGY refinements** (any §5 confidence model, §6 dedup, §7 provenance change): §6 cross-references update; specific column descriptions in §4 may update if operational composition changes.
- **Verification discipline** at every update: `PRAGMA table_info()` + `sqlite_master.sql` CHECK-extract regex against the on-disk database. Per the 4-tier source-of-truth precedence in §1, this document is tier (4) — derived narrative — and must faithfully reflect tier (1) on-disk schema state.

Contributions touching schema or DATA_DICTIONARY content land via the standard project PR process per [CONTRIBUTING.md](CONTRIBUTING.md); substantive schema-changing PRs carry a `BIBLE_AMENDMENTS.md` entry per the amendment-log discipline.

---

## Canonical sources

Descriptive references used in this document map to canonical bible
anchors as follows. The canonical bible (`PROJECT_BIBLE.md` and the
amendment ledger `BIBLE_AMENDMENTS.md`) holds the authoritative
specification; this DATA_DICTIONARY is the derived schema-reference
narrative.

| Descriptive reference (as used in this doc) | Canonical source |
|---|---|
| promotion-gate hard rule | `PROJECT_BIBLE.md` §11 #7 |
| no-fabrication hard rule | `PROJECT_BIBLE.md` §11 #1 |
| no-PII hard rule | `PROJECT_BIBLE.md` §11 #3 |
| confidence-ceiling hard rule / third-party-citation-lineage boundary | `PROJECT_BIBLE.md` §11 #8 |
| multi-purpose-vendor discipline | `PROJECT_BIBLE.md` §11 #10 + §11 #13 |
| amendment-log discipline | `PROJECT_BIBLE.md` §11 #11 |
| Feist facts-only / canonical sentinel-key | `PROJECT_BIBLE.md` §11 #16 |
| canonical-bible LA-bit pairing rule / vendor-as-container / firmware-generation | `PROJECT_BIBLE.md` §8.4 + `BIBLE_AMENDMENTS.md` CP14 |
| canonical-bible procurement-corroboration / deployment-evidence rule | `PROJECT_BIBLE.md` §8.4 |
| FOIA discipline | `PROJECT_BIBLE.md` §11 #6 |
| source-tier hierarchy | `PROJECT_BIBLE.md` §1 + §6 |
| canonical-bible provenance discipline | `PROJECT_BIBLE.md` §8.1 |
| `source_type='primary_registry'` band introduction | `BIBLE_AMENDMENTS.md` CP15 |
| `geographic_scope` filter (default `['US']`) | `BIBLE_AMENDMENTS.md` CP7 |
| identifier-type extension cluster (migrations 0008–0010) | `BIBLE_AMENDMENTS.md` CP13 |
| migration 0011 `ble_manufacturer_id` enum extension | `BIBLE_AMENDMENTS.md` CP14 |
| forward-looking-codification caveat (vendor-companion-app sub-banding) | `BIBLE_AMENDMENTS.md` CP17 |
| vendor-disambiguation discipline | `BIBLE_AMENDMENTS.md` SAR-8 + SAR-9 |
| Legistar status-discipline / item-grading / staging sub-rules | `BIBLE_AMENDMENTS.md` SAR-5 |
| intake-time false-positive-class allowlist | `BIBLE_AMENDMENTS.md` SAR-7 |
| `argus_record_id` stable-identifier algorithm | `BIBLE_AMENDMENTS.md` SAR-10 |
| framework-string sub-rule (extraction-time FP discipline) | `BIBLE_AMENDMENTS.md` SAR-11 |
