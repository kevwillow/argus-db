# Changelog

All notable changes to Argus are documented in this file. The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project does not yet adopt semantic-versioning for the dataset shape itself — see "Schema versioning" below for the migration-ledger discipline.

## [Unreleased]

### Conventions

- **Staging-JSON-vs-schema-column naming convention codified** (2026-05-17, patch cycle 1.6.C): staging JSON shapes emitted under `extraction_outputs/{runguide_slug}/` use `candidate_value` for human readability during validator review; the promoted `raw_observations` schema column is `candidate_identifier`. Validator handles the rename at promotion (one-to-one, no transformation). Documented in patch cycle 1 against the source-admission wave (10 runguides, MAC-101 through MAC-110). Re-evaluation trigger: if validator pushback at handoff makes the rename-at-promotion step error-prone, Patch 2.x can align the staging shape to the schema; default-if-silent is to hold the convention.

## [v1.2.0] — 2026-05-18

### What's new in v1.2.0

Argus v1.2.0 lands the cycle-7 autonomous-overnight-wave integration. The wave brought **two new authoritative data sources** for the US FCC equipment-authorization ecosystem (fccid.io as a community aggregator + the official FCC EAS Filings UI as a distinct primary-registry source), **671 FCC ID discovery rows** staged under a new dual-citation-pair convention (the citation half awaits a separate async re-citation pass when FCC.gov egress is restored), and **16 net-new identifiers** from a static-analysis pass against four LE-adjacency vendor companion apps (Hikvision Hik-Connect, Dahua DMSS, Motorola WAVE PTT, Parrot FreeFlight 6). We also admitted **fourteen new manufacturer rows** — four for vendors whose identifiers we positively extracted (Hikvision, Dahua, Autel Robotics, Cisco Meraki) and ten stub rows for vendors whose identity we confirmed via absence-investigation (Verkada, Honeywell, Lenel, BluePoint Alert, PIPS Technology, Wolfcom, Utility Inc, Coban Technologies, Digital Ally, Aerodome).

Alongside the data lands, the wave produced a **bible-amendment proposal codifying empirical-premise verification as a runguide precondition** — five separate web-scrape runguides (MAC-102 ISED, MAC-103 BT SIG, MAC-105 USPTO Patents, MAC-107 GitHub Code Search, MAC-110 Ofcom) plus one internal extraction pass (MAC-101 PC1.7's `application_id`-vs-`grant_id` discovery) all surfaced load-bearing-premise failures during the same 8-hour autonomous window. The amendment proposes a new `§2.4 Empirical-Premise Verification Precondition` requiring runguides to ship a `§3.0` verification-probe section that completes CLEAN before any `§3.1` bulk dispatch fires. **The amendment was drafted in this release but is held pending CEO + operator ratification** on the [MAC-178](/MAC/issues/MAC-178) issue thread; it will land in a follow-on commit once ratified.

The headline outcomes for downstream consumers: **22,549 active identifiers** (up from 22,533, +16 from MAC-104 wave-G v2 promotion), **52 sources** (up from 50; +1 crowdsourced fccid.io + 1 regulatory FCC EAS Filings), **49 manufacturers** in the canonical vendor lexicon (up from 35), **133,825 raw_observations** rows (up from 133,134), and a schema bumped from version 21 to **version 22** via one forward-only migration (the new `fcc_citation_deferred_queue` staging table for the dual-citation pair pattern).

### New data sources

Two sources joined Argus in this release, bringing the source count from 50 to 52:

- **fccid.io** (sid=51, `crowdsourced` tier 2) — a third-party aggregator of US FCC Equipment Authorization System filings. fccid.io mirrors the FCC's public filings catalog with a more navigable surface than the official `apps.fcc.gov` UI, but the upstream license is `NO_LICENSE_DECLARED` — Argus extracts facts under the Feist v. Rural Telephone facts-not-copyrightable doctrine, not via license inheritance. Compilation arrangement is not republished. This source feeds the new dual-citation-pair pattern (see below).

- **FCC Equipment Authorization System — Filings** (sid=52, `regulatory` tier 1) — the official FCC EAS Filings UI at `apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm`. Distinct from the existing FCC EAS grantee-registration data file (source 7); the Filings UI gives per-FCC-ID filing surfaces (test reports, internal photos, RF exposure data) that the grantee CSV doesn't expose. **The source was admitted under a degraded-mode posture**: at extraction time FCC.gov egress was unreachable from the runtime host (Akamai-edge HTTP/2 INTERNAL_ERROR across `apps.fcc.gov`), so the 671 fccid.io discovery rows were staged with their FCC citation half deferred to an asynchronous re-citation pass. The source exists; the citation rows accumulate when egress is restored.

### Dual-citation deferred queue (new staging convention)

The cycle-7 wave introduces a **dual-citation pair pattern** for sources where the discovery surface (an aggregator) is distinct from the primary surface (the regulator). Each FCC ID observed at fccid.io carries a `notes.dual_citation_pair_id` field pointing to a row in the new `fcc_citation_deferred_queue` table. The queue row holds the discovery anchor (`fccid_io_source_url` + SHA-256 of the served HTML) and an opportunistic enrichment field (`fcc_grant_ids[]` — 564 of 671 queue rows carry these, extracted from the fccid.io page's grant-bold-content block; this lets a future async re-citation pass shortcut FCC.gov navigation from 5-step lookup to 1-step). When FCC.gov egress is restored, the validator's async re-citation pass drains the queue and emits paired regulatory-band citation rows. Until then, the discovery rows stay at the `crowdsourced` 50-75 confidence band; no confidence drift on the discovery anchor alone.

### MAC-104 Wave-G v2 net-new identifiers

The wave ran a static-analysis extraction pass against four LE-adjacency vendor companion apps (downloaded from apk-pure; decompiled with jadx + apktool; structured field extractions only — no decompiled source ever enters the DB per §11 #15). Net-new identifier yield:

- **Hikvision Hik-Connect** (`com.hikvision.hikconnect`) — 1 BLE service UUID + 2 BLE characteristics, all anchored in the app's `HcpBluetoothServer` class. The Hik-Connect app is operator-cohort (cloud VMS / video doorbell), but the BLE pairing code path is installer-quality — vendor-named classes, paired `BluetoothGattService.equals(...)` / `getCharacteristic(...)` confirmations across multiple files.
- **Dahua DMSS** (`com.mm.android.DMSS`) — 1 BLE service UUID + 1 BLE characteristic, paired in obfuscated class `sources/en/f.java`. Dahua DMSS substituted for the legacy `com.mm.android.direct.gdmsphone` (gDMSS Plus) which is documented-absent on both apk-pure and apk-mirror.
- **Motorola WAVE PTT** (`com.motorolasolutions.wave`) — 2 BLE service UUIDs (one custom 128-bit, one 16-bit SIG-template) + 2 BLE characteristics, all anchored in `BluetoothLowEnergyPttValues` for the Milicom PTT Button accessory.
- **Parrot FreeFlight 6** (`com.parrot.freeflight6`) — 1 BT SIG company-ID (67 / 0x0043 = Parrot SA) + 4 ASD-STAN drone-RID enums (`FR_30_OCTETS`, `ANSI_CTA_2063`, `FRENCH`, `EN4709_002`) + 1 ARSDK DRI feature class ID (41984 / 0xA400) + 1 ARSDK DRI command UID set. All anchored in `com/parrot/drone/sdkcore/arsdk/ArsdkFeatureDri.java` — clear-text Java, 262 lines; Parrot is the canonical drone vendor for which the entire ARSDK protocol + Drone-RID code path surfaces under Java decompilation.

All 16 promoted identifiers carry `confidence ∈ {75, 85, 87}` per CP17 manufacturer_app sub-banding (installer-cohort 80-95 → 87; CP14 drone-RID class hits → 85; 16-bit SIG-template lower anchor → 75). All single-source at promotion (`notes.single_source_at_promotion=true`); no §5.6 cross-source uplift applied (verified: no pre-existing rows match any candidate identifier).

**Four additional candidates held for SAR-12 schema-extension review:**
- 2 default credentials (`lc2014` LeChange SDK default password, `terminal` DMSS OAuth client_secret) — no `default_credential` enum slot at v22 schema
- 1 vendor namespace UUID (Parrot Skyward UTM `0045b822-...`) — handoff explicitly flags as NOT-a-BLE-service-UUID; no clean enum fit
- 1 DJI RTK serial-number template (`1APDF7Q0010001` from DJI Pilot NRTK setup default) — handoff explicitly not-promoted-flagged; no `serial_number_template` enum slot

Each held row stages in `raw_observations` with `notes.hold_reason` + `notes.validator_review_recommendation`.

### Manufacturer enrichments

Fourteen new manufacturer rows joined the canonical lexicon (from 35 to 49):

- **Hikvision** (id=209) and **Dahua** (id=208) — both admitted with NDAA Section 889 note (state/local LE deployments persist outside the federal-procurement bar; runguide §0 scope).
- **Autel Robotics** (id=206, primary_category=drone) and **Cisco Meraki** (id=207) — positive-extraction admissions from MAC-104b/d.
- **Stub admissions** (10 vendors, primary_category set where the vendor's product line is unambiguous): Verkada, Honeywell, Lenel, BluePoint Alert, PIPS Technology, Wolfcom, Utility Inc, Coban Technologies, Digital Ally, Aerodome. Each carries `notes.admission_basis='documented_absence_only'` — the manufacturer identity was verified via absence-investigation (apk-pure 404 + apk-mirror "no results" + cohort-prediction reasoning) but no positive identifier extraction this wave.

**34 product-family taxonomy entries** added to seven manufacturers' `notes.product_family_taxonomy[]` arrays (additive; cross-APK observations of the same string are corroborating mentions and get separate entries — e.g. DJI "Mavic" appears once for DJI Fly + once for DJI Pilot = 2 entries, 1 distinct value). Distinct values: DJI (10), Hikvision (5), Motorola Solutions (4), Dahua (4), Parrot (3), Autel Robotics (2), Cisco Meraki (1).

**22 `documented_absence` JSON entries** applied to `manufacturers.notes.documented_absence[]` across 21 distinct vendor rows (DJI gets two entries: legacy `com.dji.go` + standalone `com.dji.mavicmini` folded into DJI Fly). Each entry carries `investigation_date_utc`, `investigation_dispatch_ref`, `channels_probed`, `outcome=categorical_absent`, `rationale` (one of `LE_only_distribution` / `federal_enterprise_managed` / `vendor_direct_NDA` / `controlled_distribution`), and the staging vendor_canonical for alias-trace continuity. Distribution: LE-only-distribution 9, federal-enterprise-managed 9, vendor-direct-NDA 3, controlled-distribution 1 (DroneShield RfPatrol — C-UAS / ITAR-adjacent; flagged for operator legal review before alt-channel pursuit).

### SAR-11 FP-class registry additions

Nineteen new SAR-11 FP-class proposals were baked into the canonical `proposed_fp_classes.json` registry per CEO §3 #5 ratification: **14 clean bulk-adds** (Docker/Jenkins build-host UUIDs, APK test fixtures, Motorola WAVE license GUID, Microsoft AppCenter / PDFBox / RN-Keychain library labels, NASA WorldWind constants, Autel password regex templates, Apache HttpClient context keys, RxJava build-host UUIDs, AndroidAnnotations cacerts default, XML layout TextView labels, Adobe XMP image metadata UUIDs) + **5 selective adds with `operator_review_note: "Hikvision/Dahua/drone-cohort overlap; flagged at MAC-104 cycle-7"`** (Alibaba Taobao security cipher key, Microsoft XML namespace UUID, Hikvision HTML doc-routing GUID, AMap location-SDK placeholder MACs, DJI api_debug.txt key). Each edge entry carries explicit `overlap_risk` prose so v3 extractor calibration applies exact-value-match-only, not generalization.

### Bible amendment (DRAFTED pending ratification)

The wave's six concrete failure-mode anchors (5 external runguides + 1 internal extraction pass) produced a proposal for **`§2.4 Empirical-Premise Verification Precondition`** — a new bible subsection requiring runguides to ship a `§3.0` verification-probe section that completes CLEAN POSITIVE or CLEAN NEGATIVE before any `§3.1` bulk dispatch fires. INCONCLUSIVE outcomes halt the runguide; CEO disposition required. The amendment also defines retroactive binding rules for runguides drafted-but-not-dispatched and runguides being re-dispatched.

The amendment text + downstream-consumer audit (10 runguides identified for retroactive `§3.0` adoption) was posted on [MAC-178](/MAC/issues/MAC-178) for CEO + operator ratification. **It is NOT landed in this release.** Once ratified, it will land as `Correction Pass 27` (or whatever slot the CEO assigns) in a follow-on commit + a `§2.4` insert into `PROJECT_BIBLE.md`. The CHANGELOG will be updated to add the final commit hash at ratification time.

### Schema changes

One new migration landed this release (schema version 21 → 22):

- **0022 — `fcc_citation_deferred_queue` staging table.** New table holds the discovery-row half of the dual-citation pair pattern (one row per FCC ID; `fcc_id` UNIQUE; `promoted_at NULL` = pending drain by the validator's async re-citation pass; index on `(promoted_at)` partial WHERE NULL for drain queries; index on `fcc_grant_ids_csv` for grant-ID-shortcut lookup). 671 rows seeded from the MAC-101 partial-deliverable wave.

### Refreshed exports

All four canonical exports were regenerated against the post-cycle-7 active set:

| Export | Pre-cycle-7 | Post-cycle-7 | Delta |
|---|---|---|---|
| `argus_export.csv` (rich-import, all canonical rows) | 22,533 | **22,549** | +16 |
| `argus_export.json` (Lynceus, ≥30 confidence + §4.4 mapping) | 494 | 494 | +0 |
| `argus_export_high_confidence.json` (Lynceus, ≥70 + non-{crowdsourced, inferred}) | 113 | 113 | +0 |
| `argus_export_behavioral_signatures.json` (Rayhunter; unchanged this wave) | 55 | 55 | unchanged |

**Note on the JSON-export +0 delta:** the 16 MAC-104-promoted identifier_types (`ble_service_uuid`, `ble_characteristic`, `ble_company_id`, `asdstan_enum_value`, `device_class_id`, `rf_protocol_constant`) are all `§4.4 DROPPED-class` per CP16 / CP19 (mig-0018 cluster) / MAC-117 (mig-0019 round-2). Per the bible, DROPPED-class identifier_types are carried in the canonical DB (and the CSV rich-import feed) but NOT in the Lynceus pattern-table JSON exports — by design. The brief author's forecast of +20 standard-export rows + +6 to +14 high-confidence rows didn't account for this disposition. Whether to MAP some/all of these types into Lynceus is a separate `§4.4` amendment surface for a future CP cycle.

Also new: `exports/_export_manifest.json` ships the per-file size + SHA-256 + entry-count manifest with a delta-vs-forecast block, generation timestamp, and the §4.4 reasoning surfaced for downstream consumers.

## [v1.1.0] — 2026-05-17

### What's new in v1.1.0

Argus v1.1.0 broadens the project beyond pure equipment-identifier registries and into the corporate, judicial, and procurement records that anchor surveillance vendors to real-world entities. We added **seven new authoritative data sources** (taking the project from 43 sources to 50), **expanded our federal procurement coverage** by 2,560 net-new contract records, and **closed our first held entity** — Johnson Matthey PLC — by cross-checking it against the UK's official corporate registry.

Along the way we found and fixed seven small inconsistencies between our documentation and the actual database schema. These are codified in the amendment ledger so the next round of contributors doesn't trip over the same edges. We also introduced two new operating conventions: an explicit `access_mode` tag for sources we can't auto-scrape in one session (CAPTCHA-walled state corporate registries, paid-tier government databases), and a `cycle_completion_state` tag for sources that take multiple days to fully ingest. Both are described in plain language below.

The headline outcomes for downstream consumers: **22,533 active identifiers** (up from 22,532), **46,043 procurement records** (up from 43,483), **35 manufacturers** in the canonical vendor lexicon (Johnson Matthey is new), and a schema bumped from version 19 to **version 21** via two forward-only migrations.

### New data sources

Seven sources joined Argus in this release, bringing the source count from 43 to 50:

- **UK Companies House** (sid=44) — the United Kingdom's official corporate registry, released under the Open Government Licence v3.0. We use it to confirm the corporate identity of UK-incorporated surveillance vendors against a primary government record. **This source enabled our first Class B hold closure: Johnson Matthey PLC (UK company #00033774), a London-headquartered chemistry and precious-metals firm**, was confirmed via Companies House cross-check and admitted to the canonical 35-entry manufacturer lexicon. Access is fully automated via the Companies House API.

- **Delaware Division of Corporations** (sid=45) — Delaware is the registration state of record for a disproportionate share of US technology companies, so the Delaware corporate registry is a high-leverage source for vendor verification. The state's NameSearch web form is CAPTCHA-gated, so this source is recorded under the new `operator_manual_only` access convention: lookups happen via human-operated browser sessions rather than scripts.

- **California Secretary of State — Bizfile** (sid=46) — California's corporate registry, the second-most-relevant US state for surveillance vendor lookups after Delaware. The Bizfile portal is gated by an Incapsula bot-challenge wall, so this is also an `operator_manual_only` source.

- **Texas Secretary of State SOSDirect** (sid=47) — the Texas corporate registry. Useful for Texas-headquartered surveillance vendors. Access requires paid-tier authentication, so this is again `operator_manual_only`.

- **CourtListener / RECAP (Free Law Project)** (sid=48) — a free, comprehensive judicial filings database covering US federal and state courts. CourtListener surfaces lawsuits, contract disputes, and federal court records that name surveillance vendors as parties. Metadata is dedicated to the public domain under CC0; full-text search requires an authenticated Bearer token.

- **SEC EDGAR** (sid=49) — the US Securities and Exchange Commission's corporate-disclosure filings database. Public companies routinely name their major customers in 10-K annual reports and Item 1A risk-factor narratives; for surveillance vendors that file with the SEC, this lets us corroborate vendor-customer relationships against a primary public-domain regulatory source. EDGAR is automated via HTML parsing.

- **SAM.gov Entity Registration** (sid=50) — the US federal procurement contractor-registration database. SAM.gov is the authoritative source for "is this vendor an active US federal contractor and what are their registered NAICS codes?" — exactly the question that determines whether procurement evidence is admissible. Access is automated via the SAM.gov API. This source is recorded under the new `partial_pre_day1` cycle-completion convention because we hit the SAM.gov non-Federal-individual-account daily rate ceiling (~10 requests/day) before the first full sweep finished. Remaining queries continue across subsequent days; the source row was admitted at first-batch completion.

### Expanded federal procurement coverage

Federal procurement records grew by **2,560 net-new entries** (from 43,483 to 46,043) via a deep-extension pass against USAspending.gov, the canonical federal contract-award database. This nearly closes the previously-known gap between Argus's surveillance-vendor coverage and USAspending's actual surface area for those vendors.

Alongside the new rows, we landed **9,623 cross-source corroborations** from the SAM.gov ingestion cycle. **A corroboration here means: a fact we already had (a vendor's federal contract record) is now independently confirmed against a second, structurally different source (SAM.gov's contractor registration database).** When two independent sources agree on a fact, our confidence in that fact increases, and the corroboration is recorded in a per-row audit trail so downstream consumers can see the evidence chain.

Note for downstream consumers: alongside the +2,560 net-new procurement records, we **rolled 180 procurement_record confidence values back from 90 to 85**. These rows had been corroborated by a second pass against USAspending itself — but that's the same source observed twice, not two independent sources, so the confidence boost wasn't earned. The full audit trail is preserved per row in `notes.confidence_history[]`. This is exactly the kind of self-correction the audit trail is designed to surface.

### Schema changes

Two new migrations landed this release (schema version 19 → 21):

- **Migration 0020 (`source_type_enum_extension`)** — extends the `sources.source_type` enum with three new values (`judicial_filing`, `disclosure_filing`, `procurement_disclosure`) to properly classify the new judicial, SEC, and SAM.gov sources. Previously these would have fallen back silently to the generic `regulatory` bucket; now each source class has its own named tier.

- **Migration 0021 (`procurement_vendor_canonical_normalized`)** — adds a new `procurement_records.vendor_canonical_normalized` column. This is a deterministic, query-friendly normalization of each procurement record's vendor name: lowercased, punctuation stripped, corporate suffixes (`INC`, `CORP`, `LLC`, `LTD`, `PLC`) removed. For example, `'AXON ENTERPRISE, INC.'`, `'Axon Enterprise, Inc.'`, and `'AXON ENT INC'` now all collapse to `axon enterprise`, making cross-validation joins against the manufacturer lexicon dramatically more reliable. The column was backfilled across all 46,043 procurement records.

**What this means for downstream consumers:** check `MAX(version) FROM schema_version` at runtime; it should now read 21. If you query the `sources` table by `source_type`, you may now see three additional enum values. If you join against `procurement_records.vendor_canonical_name`, prefer the new `vendor_canonical_normalized` column instead — same data, dramatically better join semantics across 46k rows.

### New discipline conventions

Two new operating conventions were introduced. Both live in the `sources.notes` JSON field today and are described below in user terms; they may be promoted to first-class schema columns in a future release once the vocabulary stabilizes.

- **`access_mode`** — describes how Argus fetches a given source. Values: `automated_api` (queried via documented API), `automated_html_parse` (scraped from HTML without an anti-bot wall), `automated_with_auth` (automated but requires a token), `mixed_automated_manual` (some candidates automated, some manual), and `operator_manual_only` (all access is via a human-operated browser session, because the source is CAPTCHA-walled, bot-challenged, or otherwise structurally hostile to automation). **Important: the access mode is a mechanism descriptor, not a quality signal.** Operator-manual sources carry identical confidence bands and provenance discipline to automated sources. The four state-registry sources added this release (DE / CA / TX) and three secondary state holds are flagged `operator_manual_only`.

- **`cycle_completion_state`** — describes whether a source's data has been fully ingested or whether ingestion is paced across multiple days. Values: absent (source is complete; default reading), `partial_pre_day1` (admission landed before the first sweep finished), `partial_pacing_in_flight` (multi-day pacing run still active), `partial_pacing_exhausted` (multi-day pacing terminated short of completion). When this field is set, the source row also carries `next_cycle_dispatch_scheduled_for_utc`, `next_cycle_dispatch_runguide_path`, and `partial_yield_metrics_at_admission` so downstream consumers can see exactly where the partial state sits and when the next cycle is scheduled. **SAM.gov (sid=50) is the first consumer**, recorded as `partial_pre_day1`.

### Known limitations + what's coming

Argus's coverage is still **intentionally narrow at this baseline** — broader categories of surveillance equipment remain out of scope. The roadmap below frames what's queued.

**Currently held items:**

- **11 US state Secretary-of-State corporate holds** remain queued for operator-manual review against the DE / CA / TX registries.
- **Approximately 22 international corporate holds** remain queued. Bounded paths to closure are documented per jurisdiction.
- **3 operator-review items** surfaced from the SAM.gov ingestion cycle: a Vigilant Solutions inactive-registration probe, a Flock Safety brittle-alias normalization disagreement (Flock Safety vs "Funny Flock Farms LLC"), and a Motorola multi-entity disambiguation probe. All three are staged to the operator-review queue with full audit context.

**Carry-forward from v1.0.0:** the previously-documented v1.0.0 held items (31 behavioral_signatures pending second-source corroboration, 62 Class B sustained holds, 133 IEEE Private permanent holds, 142 round-2 vocabulary candidates) remain held under the same rationale, less the one Johnson Matthey closure this release. The v1.0.0 documented sources-row metadata discrepancy on sources 1/2/3/7 is unchanged.

**Note: a small number of `identifiers.notes` rows contain malformed JSON; downstream consumers using `json_extract()` against this column should fall back to JSON-text-LIKE patterns. Tracked for future fix.**

**Coming next:**

- Continued multi-day SAM.gov ingestion (cycle-6 dispatch scheduled).
- Continued operator-manual review against state corporate registries to close the 11 remaining US state holds and ~22 international holds.
- Additional community-source-acquisition waves, deferred from v1.0.0.
- iOS vendor companion-app coverage, deferred from v1.0.0.
- Skydio Enterprise alt-channel scope, deferred from v1.0.0.

### Internal architecture notes

This section preserves the discipline-architecture audit trail for the v1.1.0 release in the project's canonical idiom. The narrative is the body above; the ledger below is the binding contract.

**Bible amendment ledger (this release):**

- **CP23** @ bible HEAD ratification — coordinated amendment: wide-net cycle-{1,3,4} schema-contract patches + migrations 0020 + 0021 + downstream-consumer audit. Folds seven schema-contract drift findings (PROJECT_BIBLE.md §4.2 / §4.3 / §8.2 / §8.3 §-text additions; `manufacturers.aliases` comma-string clarification; source_excerpt per-table CHECK constraint cap table; `notes.access_mode` notes_json convention; license-into-notes folding contract; cross-validation column-name normalizations) and the two migrations into a single bible commit per the §11 #11 amendment-log discipline. Source patches: `new data 5.16/schema_contract_patch_cycle3.md`, `new data 5.16/schema_contract_patch_cycle4.md`, `new data 5.16/schema_contract_patch_notes_license.md`.
- **CP24** @ bible HEAD — §11 #8 within-source-re-extraction sub-rule + CP19 spirit-extension to `procurement_records` row-level audit-trail (`notes.confidence_history[]` convention) + "§5.2 +5 boost" citation hygiene correction. Within-source re-extraction (same upstream registry queried at two times by the same or different extraction sessions) is **not** a "second independent source" for §8.3 lift purposes. Provenance enrichment via `notes.corroborations[]` + `notes.corroboration_sessions[]` stays; confidence does not lift. The 180-row MAC-172 P4 USAspending deep-extension lift rollback (85 → 90 → 85) is the first consumer with full per-row audit-trail.
- **CP25** @ bible HEAD `2803ae1` — `cross_source_corroboration_reversals[]` audit-trail convention + CP24 §12 `n` recount supersession (SEC EDGAR × USAspending drops 2 → 0 after §11 #1 semantic review of MAC-171 P3 RG5 findings) + within-source-FP discipline-evolution carry-forward. First consumer is the MAC-171 id=86738 reversal UPDATE.
- **CP26** @ bible HEAD `64f381c` — SAM.gov cycle-5 day-0 partial fold (seven runguide-correction findings: probe-template UEI freshness, empirical rate ceiling, no-proactive-rate-limit-headers extraction discipline, operator-manual-queue file-format clarification, NAICS code revision drift, single-token alias fanout brittleness, snapshot-freshness pre-flight) + `cycle_completion_state` notes_json convention codification + within-source-FP discipline n=4 codification (text-pattern match + semantic-relationship validation as a default §4 match-scoring step). Source patch: `extraction_outputs/sam_gov_admission/STOP_THE_LINE_rate_ceiling.md`.

**Migration ledger entries (cumulative 1 → 21):**

- **0020 `source_type_enum_extension`** (applied 2026-05-17 05:07:17) — `sources.source_type` CHECK enum 10 → 13 values: net-new `judicial_filing`, `disclosure_filing`, `procurement_disclosure`. Per CP23 / cycle-3 §1 finding #2. Table-rebuild per the 0009 / 0015 / 0018 / 0019 precedent. The 3 new bands are sources-tier taxonomy only; identifier-row promotion-pipeline confidence bands (§8.2) are unchanged.
- **0021 `procurement_vendor_canonical_normalized`** (applied 2026-05-17 05:07:32) — `procurement_records.vendor_canonical_normalized TEXT NOT NULL DEFAULT ''` column + supporting B-tree index. Per CP23 / cycle-3 §1 finding #4 + CEO Path B ruling. Backfill populated all 46,043 rows; collapse ratio 0.9862 (1,157 distinct raw vendor_canonical_name values collapse to 1,141 distinct normalized values). Normalization algorithm canonical reference: `db/normalize_vendor.py::normalize_vendor_name` (pure function).

**MAC issue dispatch references:**

- **MAC-101** — baseline aggregate state (v1.0.0 reference).
- **MAC-168** — paperclip integration of CP23 (wide-net cycle-{1,3,4} schema-contract patches).
- **MAC-169 through MAC-174** — admission cycle dispatches (UK Companies House P2; SEC EDGAR P3; USAspending deep-extension P4; state SoS P5; CourtListener V4 P6).
- **MAC-172** — USAspending deep-extension P4 ingest (+2,560 net-new procurement_records; partial-ratify rollback of the 180-row lift; CP24 codification).
- **MAC-175** — SAM.gov cycle-5 admission close (sid=50 INSERT + 9,623-row cross-source corroboration UPDATE batch: Vigilant 56 + Motorola 9,545 + Genetec 22; CP26 codification).

**Source-tier license-posture vocabulary additions (CP23):**

- `OGL-3.0` — UK Companies House (sid=44).
- `PUBLIC_DOMAIN` — SEC EDGAR (sid=49), SAM.gov (sid=50).
- `US_STATE_PUBLIC_RECORDS` — Delaware / California / Texas SoS (sid=45 / 46 / 47).
- `CC0` — CourtListener / Free Law Project (sid=48).

All four compose with the pre-existing CP21 `notes.upstream_license_posture` canonical sentinel-key for per-row license-aware downstream consumer filtering. License lives inside `notes_json.license` (the contract refers to this as `notes_json`; the underlying column is `sources.notes` TEXT containing JSON), NOT as a top-level column — codified per the cycle-1 patch finding #1.

**Live-state verification (paste-not-cite per S.7):**

Verified 2026-05-17 against `db/argus.db`:

```
schema_version              = 21   (0021_procurement_vendor_canonical_normalized,  2026-05-17 05:07:32)
                                   (0020_source_type_enum_extension,               2026-05-17 05:07:17)
sources                     = 50   (was 43 in v1.0.0; +7 this release)
identifiers active          = 22,533  (superseded_by IS NULL; total rows 22,613 incl. 80 superseded)
procurement_records         = 46,043  (+2,560 net-new this release)
manufacturers               = 35   (+1: Johnson Matthey PLC, UK CH #00033774)
behavioral_signatures       = 131  (unchanged)
source_reclassifications    = 809  (unchanged this MAC-175 close)
PRAGMA integrity_check      = ok
```

**Cross-source corroboration accounting (this release):**

- **9,623 cross-source corroboration UPDATEs** landed from the SAM.gov cycle-5 admission (Vigilant 56 + Motorola 9,545 + Genetec 22). All UPDATEs honor CP24 sub-rule (b)'s `notes.confidence_history[]` per-row audit-trail.
- **180 within-source-reextraction rollbacks** (90 → 85) applied per CP24 §11 #8 sub-rule #1 (the USAspending deep-extension is the same source observed at two times, not a genuinely independent collector). Full per-row audit per CP24 sub-rule (b).
- **2 RG5 cross-corroboration markers** flagged at MAC-172 P4 ingest; 1 reversed at MAC-171 P3 ratification per CP25 §1 (id=86738; SEC × USAspending pair recount drops 2 → 0). The remaining marker is deferred to operator review pending fuller filing context.

**Open §12 questions surfaced this release (queued for future CP candidacy):**

- `access_mode` first-class column migration — gated on value-set stabilization (~1-2 more cycles of new-source evidence).
- Partial-cycle source-admission discipline first-class-column promotion (`cycle_completion_state`) — gated on at least 2 distinct sources using non-absent values.
- Empirical-ceiling-probe runguide template — CP26 §3 candidate.
- `procurement_reclassifications` audit table promotion — gated on forensic-query pattern emergence at scale (current row-local `notes.confidence_history[]` convention is canonical).

---
## [v1.0.0] — TBD release date

### What's included

Argus v1.0.0 ships the canonical surveillance-equipment-identifier database as a queryable SQLite artifact (`db/argus.db`, schema_version=19) plus four derived dataset exports under three licenses:

- **Pipeline** (AGPL-3.0-or-later) — the migration + source-loader + extraction + validator + export code that reproduces the database from upstream sources.
- **Database / dataset** (ODbL-1.0; Atlas-derived rows quarantined under CC-BY-NC-SA-4.0 per upstream NC clause; per-row LICENSE column at `deployment_observations.LICENSE` enables downstream license-aware filtering) — the canonical SQLite DB + the JSON/CSV exports at `exports/`.
- **Documentation** (CC-BY-SA-4.0) — README, METHODOLOGY, DATA_DICTIONARY, CREDITS, SECURITY, THREAT_MODEL, LEGAL_POSTURE, CONTRIBUTING, CODE_OF_CONDUCT, this CHANGELOG.

#### Database content

- **14 user tables** at schema_version=19 (full schema reference in [DATA_DICTIONARY.md](DATA_DICTIONARY.md)):
  - **Canonical-state**: `identifiers` (Layer 1 — the main table; 22,532 active rows + 80 superseded)
  - **Provenance + source**: `raw_observations` (133,134 rows), `sources` (43 sources), `manufacturers` (34-entry surveillance-tech vendor lexicon)
  - **Layer 2 + supporting**: `deployment_observations` (116,668 rows with per-row LICENSE column per migration 0016), `procurement_records` (43,483 rows), `fcc_grantees` (50,153 rows), `council_minutes_matters` (3 rows), `wigle_anchor_priority` (80,697 rows), `behavioral_signatures` (131 rows)
  - **Audit-trail**: `source_reclassifications` (809 rows — row-level reclassification audit table)
  - **Operational**: `conflicts` (20 rows), `extraction_runs` (106 rows), `schema_version` (migration ledger 1 → 19)
- **Active identifier rows by class** (22,532 total active):
  - **IEEE-anchored mac_range / OUI** rows at `primary_registry` band: ~17,800 rows across IEEE OUI MA-L / MA-M / MA-S + IEEE IAB registries
  - **FAA Remote ID `drone_id_prefix`** rows at `primary_registry` band: 427 rows (from alphafox02/DragonSync + post-validation promotion cycle)
  - **Bluetooth SIG `ble_manufacturer_id`** rows at `primary_registry` band (per migration 0011): 3,971 rows
  - **Community-research crowdsourced** rows: ~534 rows across drone Remote ID + BLE tracker catalogs + IMSI-catcher detection + ALPR-camera profiles
  - **Vendor companion-app `manufacturer_app`** rows (Hak5 / Flock Safety FS Installer / Getac BWC Viewer via vendor-app static analysis): 21 rows
  - **Inferred / cross-validation** rows: 4 rows (vendor-disambiguation + corroboration math)
- **Provenance rows** (`raw_observations`): 133,134 rows; every active identifier traceable to at least one source citation per METHODOLOGY §7 provenance discipline.
- **Deployment-location rows** (`deployment_observations`): 116,668 rows from EFF Atlas of Surveillance (15,071 CC-BY-NC-SA-4.0) + DeFlock (101,597 ODbL-1.0) with per-row LICENSE column quarantine.
- **Behavioral signatures** (`behavioral_signatures`): 131 rows (55 Marlin NDSS 2025 IMSI-catcher signatures + 38 backfilled from community IMSI-detector research + 38 round-2 review extensions).

#### Source families integrated

- **IEEE OUI registries** (MA-L 24-bit + MA-M 28-bit + MA-S 36-bit) at `primary_registry` band — vendor-to-OUI mappings; factual public registry data.
- **IEEE IAB registry** (36-bit legacy) at `primary_registry` band — predecessor allocations.
- **FCC EAS Equipment Authorization Grantee Registrations** at `primary_registry` band — 50,153-grantee corporate registrant lookup table; allowlist for `fcc_id_anchored` disambiguation and the vendor-disambiguation predicate.
- **FAA ANSI/CTA-2063-A Remote ID prefix registry** at `primary_registry` band — drone-class identifier-to-vendor attribution.
- **Bluetooth SIG company-identifier registry** at `primary_registry` band — BLE `ble_manufacturer_id` clusters.
- **EFF Atlas of Surveillance** (CC-BY-NC-SA-4.0 quarantine; NC clause carries forward) — 15,071 deployment-location observations.
- **DeFlock** (ODbL-1.0; license-compatible with compilation license) — 101,597 ALPR camera deployment-location observations.
- **USAspending.gov + Granicus Legistar** — federal/state/municipal procurement records (43,483 + 3 rows respectively).
- **Wireshark `manuf` file** — community-maintained OUI cross-reference for vendor-name curation.
- **NDSS 2025 Marlin IMSI-catcher research** at `academic` band — 53 behavioral-signature rows for cellular-detection signatures.
- **Vendor companion applications** (Hak5 docs / Flock Safety FS Installer / Getac BWC Viewer) at `manufacturer_app` band — BLE service UUIDs + default credentials + product-family taxonomy extracted via static analysis under the 17 USC §1201(j) + 37 CFR §201.40(b) security-research exemption.
- **22 canonical community-research GitHub repositories** at `crowdsourced` or `manufacturer_doc` band — drone Remote ID + BLE tracker catalogs + IMSI-catcher detection + ALPR-camera + flock-detection cohorts.
- **5 secondary-batch repositories** at `crowdsourced` or `academic` band with explicit license-posture annotations (AGPL-3.0 inherited / AGPL-3.0 declared / NO_LICENSE_DECLARED under the Feist facts-only doctrine / CC-BY-NC-ND-4.0 with research-use clause).

Full per-source attribution + upstream-license chain in [CREDITS.md](CREDITS.md).

### Methodology

[METHODOLOGY.md](METHODOLOGY.md) documents the methodology behind v1.0.0:

- **§3 Sources and source-type hierarchy** — 10-value `source_type` enum (`primary_registry` / `inferred` / `manufacturer_app` / `crowdsourced` / `official` / `manufacturer_doc` / `regulatory` / `procurement` / `academic` / `foia`) with confidence bands per source-class. The `primary_registry` band covers IEEE OUI / FCC EAS / FAA RID / Bluetooth SIG registry-class allocators with a 70-85 single-source ceiling.
- **§4 Identifier types** — 48-value `identifier_type` enum across three structural categories: wire-observable (route to Lynceus-bound JSON exports), parametric / sub-protocol / forensic (DROPPED-class — analytical only, CSV export only), and alias-collapse (route to existing pattern_type).
- **§5 Confidence model** — calibrated integer 0-99 (humility-margin invariant; schema-CHECK permits 0-100 with operational cap at 99) with source-type bands, `+5` corroboration boost, lowest-contributing-ceiling rule, `primary_registry` sub-banding, and `manufacturer_app` per-class sub-banding. Discrete confidence shapes diverge for `procurement_records` (continuous 0-100, no humility margin) and `council_minutes_matters` (discrete 70/75/80 per item-grading); see DATA_DICTIONARY §6.2.
- **§6 Dedup + reclassification logic** — collapses N citations of the same identifier to a single canonical row with corroboration chain preservation; superseded-row preservation discipline (`identifiers.superseded_by` pointer chain). Row-level reclassifications (band/confidence/source_url changes) land an entry in `source_reclassifications` with `sweep_event_id` grouping + pre/post snapshot + rationale anchor.
- **§7 Provenance discipline** — `raw_observations` as source-of-truth; `source_url` must be working at ingest + verbatim-preserved post-fetch (pinned-SHA + line-anchored URL template, e.g., `/blob/<sha>/<path>#<anchor>`); no-fabrication hard rule; third-party-citation-lineage boundary; no-PII discipline; amendment-log discipline.
- **Feist facts-only promotion** — public-but-unlicensed sources (NO_LICENSE_DECLARED) qualify for facts-only extraction under *Feist v. Rural Telephone Service* (499 U.S. 340 (1991)). Argus extracts factual claims (identifier values, manufacturer attributions); Argus does NOT republish the source's compilation arrangement. Per-row canonical sentinel: `notes.upstream_license_posture='NO_LICENSE_DECLARED'`.

### License posture

- **Code:** AGPL-3.0-or-later ([LICENSE](LICENSE)) — network-use copyleft preserves source-availability for derivative scanners; AGPL-3.0 inheritance-compatible with community-contributed sources at `sources.id` 38/40/43.
- **Dataset:** ODbL-1.0 ([LICENSE-DATA](LICENSE-DATA)) with three-layer per-row license-posture composition:
  - **Layer 1** `sources.notes.license_posture` (per-source declaration; 6 distinct posture classes documented in LICENSE-DATA §2.1)
  - **Layer 2** `deployment_observations.LICENSE` (per-row NOT NULL column, migration 0016; Atlas rows quarantined under CC-BY-NC-SA-4.0 NC clause; DeFlock rows under ODbL-1.0)
  - **Layer 3** `identifiers.notes.upstream_license_posture` (per-promoted-identifier canonical sentinel key)
- **Documentation:** CC-BY-SA-4.0 ([LICENSE-DOCS](LICENSE-DOCS)) — ShareAlike preserves the discipline-architecture open-availability for derivative documentation.
- **DMCA / takedown posture:** project-side doctrinal grounding is Feist factual-data + 17 USC §1201(j) security-research exemption + 37 CFR §201.40(b) + nominative fair use. Vendor attribution disputes route through a GitHub issue.

### Schema versioning

The migration ledger (`schema_version` table) tracks every applied migration. v1.0.0 ships at `MAX(version)=19`. Migrations are forward-only (no rollback); schema-changing PRs land paired with the project's amendment-log discipline ([BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md)). Downstream consumers should check `schema_version` at runtime when integrating against a downloaded `argus.db`.

**Migration ledger summary (1 → 19):**

- **0001** initial schema — `identifiers` + `raw_observations` + `sources` + `manufacturers` + `extraction_runs` + `conflicts` + `schema_version` + 5 enum CHECK constraints
- **0002-0005** supporting tables — `procurement_records`, `fcc_grantees`, `council_minutes_matters`, `wigle_anchor_priority`, `deployment_observations`
- **0006** PDF/SDK/FCC-report corpus support
- **0007** vendor companion app static analysis support
- **0008-0010** identifier-type extensions (`product_family_codename`, `ble_local_name`, `ble_characteristic`) + `behavioral_signatures` table + `ble_manufacturer_id` enum extension
- **0012-0014** LA-bit pairing (`paired_identifier_id` + `pair_kind`) + Drone-RID identifier_type cluster + ALPR/camera `alpr_model`
- **0015** `source_type='primary_registry'` band for IEEE OUI / FCC EAS / FAA RID / Bluetooth SIG registries
- **0016** `deployment_observations.LICENSE` per-row license tag (Atlas CC-BY-NC-SA-4.0 + DeFlock ODbL-1.0 quarantine)
- **0017** `source_reclassifications` audit table (row-level reclassification ledger)
- **0018** identifier_type enum extension (14 net-new types from community-research dir Phase 1)
- **0019** identifier_type enum extension (7 net-new types from round-2 vocabulary review; cumulative CHECK enum 41 → 48)

### Amendment ledger (v1.0.0 substantive amendments)

The full amendment log lives in [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md). Below is the substantive-amendment summary for v1.0.0 release.

**Schema / data-shape amendments:**

- **`identifier_type` enum extension cluster** — added `product_family_codename`, `ble_local_name`, `ble_characteristic`.
- **LA-bit pairing** — added `paired_identifier_id` + `pair_kind` columns; Drone-RID identifier_type cluster; ALPR/camera `alpr_model` taxonomy.
- **`source_type='primary_registry'` band** — added for registry-class allocators (IEEE OUI / FCC EAS / FAA RID / Bluetooth SIG) with 70–85 single-source ceiling.
- **`source_type='manufacturer_app'` sub-banding** — vendor companion-app per-class confidence bands + cohort distinction (operator-facing vs installer/pairing-flow apps).
- **`behavioral_signatures` sibling export** — added `argus_export_behavioral_signatures.json` (Rayhunter-consumable).
- **`source_reclassifications` audit table** — added row-level reclassification ledger (`sweep_event_id` grouping + pre/post snapshot + rationale).
- **Lynceus mapping table updates** — populated the Lynceus identifier-type mapping entries for added `identifier_type` values.
- **`identifier_type` enum extensions** — added 14 net-new types from community-research dir Phase 1 + 7 net-new types from round-2 vocabulary review (cumulative CHECK enum 41 → 48).
- **`deployment_observations.LICENSE` per-row column** — added (NOT NULL; Atlas CC-BY-NC-SA-4.0 + DeFlock ODbL-1.0 quarantine).
- **`notes.upstream_license_posture` canonical sentinel-key** — established for facts-only promoted rows (`'NO_LICENSE_DECLARED'`).

**Integration / consumer-facing amendments:**

- **`argus_record_id` stable-identifier algorithm** — `sha256('<identifier_type>|<normalized_identifier>')[:16]`. Stable across re-runs, source-attribution changes, and confidence drift.
- **`geographic_scope` filter** — applied at export time.
- **Severity ownership** — moved operator-side via `severity_overrides.yaml`. Argus ships factual data; downstream consumers own alerting policy.
- **Multi-purpose-vendor carveout** — `device_category='unknown'` excluded from high-confidence Lynceus export.
- **Provenance discipline** — source-url-direct hard rule + per-shape mapper URL template (pinned-SHA + line-anchored).
- **Feist facts-only doctrine** — codified for public-but-unlicensed sources.

**Discipline-evolution amendments:**

- **"Argus identifies; Lynceus correlates"** — architectural boundary: Argus ships factual attribution data; downstream scanners own correlation and alerting.
- **Confidence-band ceiling rule** — corroborated confidence is bounded by the lowest contributing source-type band ceiling.
- **Vendor-disambiguation predicate** — Motorola Mobility / Solutions canonical split; WatchGuard Video / Technologies split.
- **LAA-bit confidence penalty** — locally-administered MAC addresses receive reduced confidence.
- **CVE false-positive allowlist + framework-UUID SDO-attestation discipline** — extraction-time false-positive classification.
- **Amendment-log discipline** — coordinated commits pair canonical-bible edits with this CHANGELOG and the per-row audit trail.
- **No-PII default-to-HOLD** — individual-attributed names without corporate-entity confirmation stay held.

### Pre-v1.0.0 history (major milestones)

The dataset was built over roughly two weeks of intensive multi-agent orchestration. Major milestones, in chronological order:

- **2026-05-04** — Argus working name confirmed; Tier-1 source acquisition complete (Atlas of Surveillance + DeFlock + IEEE OUI + Wireshark `manuf`).
- **2026-05-05 to 05-07** — PDF/HTML extraction waves; the architectural boundary between Argus and Lynceus codified (Argus ships factual attribution; Lynceus owns correlation); coordinated Lynceus integration commits (geographic_scope filter; severity operator-side; `argus_record_id`; multi-purpose-vendor carveout).
- **2026-05-08** — Vendor companion app static analysis admitted as a source class (under the 17 USC §1201(j) + 37 CFR §201.40(b) security-research exemption).
- **2026-05-11** — Community-research GitHub corpus acquired (24 repos); identifier-type extensions for LA-bit pairing, Drone Remote ID, and ALPR/camera taxonomy landed; promotion-cycle-1 closed.
- **2026-05-12** — Promotion-cycle-2 closed (~423 promotions); `primary_registry` source-type band introduced for registry-class allocators; 481 FAA RID drone_id_prefix promotions; Lynceus mapping populated for new identifier_types.
- **2026-05-13** — `manufacturer_app` sub-banding for vendor companion apps; behavioral_signatures sibling export (`argus_export_behavioral_signatures.json`); first behavioral_signatures population (0 → 55 from Marlin NDSS 2025); sources reclassification sweep (808 reclassifications); `source_reclassifications` audit table introduced.
- **2026-05-14** — Final release-readiness pass: IEEE PII triage and promotion (3,446 Class A); community-research deferred-dir Phase 2 close (145 promotions + 38 behavioral-signature backfills); Feist facts-only doctrine codified for public-but-unlicensed sources; final pre-release cleanup; v1.0.0 ship-readiness verified.

### Known limitations + post-v1.0.0 roadmap

Argus's v1.0.0 coverage is **intentionally narrow at this baseline** — do not assume comprehensive coverage of any specific surveillance equipment category. Expansion comes via the community contribution flow (standard GitHub PR + issue process) plus the following queued post-v1.0.0 work:

**Documented held items with rationale** (framed as "known held items; contribution welcome" not "incomplete data"):

- **31 behavioral_signatures** held pending second-source corroboration (substantive research-and-scrape work). Currently HELD with explicit rationale at `behavioral_signatures.notes`.
- **62 Class B sustained holds** (IEEE-derived individual-attributed-pii_sustain rows with `notes.registry_xcheck_attempted=true`) — sustained per the PII default-to-HOLD rule; predominantly Lumiplan Duhamel ×9 (French digital-signage corporate; no FCC registration), individual-shaped names, and ~50 unique singletons with no surveillance-tech-vendor or FCC-grantee evidence.
- **133 IEEE Private permanent holds** (`pii_review_disposition='ieee_private_registrant_permanent_hold'`) — IEEE OUI registrations declared as private at the registry source; ownership cannot be confirmed.
- **142 round-2 held rows** (107 vocabulary-extension candidates + 19 behavioral-signature deferred + 15 CVE false-positive entries filed to the conflicts table + 1 attribution-pending Motorola/Vigilant).
- **Known sources-row metadata discrepancy** — sources 1/2/3/7 carry historic `source_type='regulatory'` metadata pre-dating the source-type taxonomy refinement; identifier-row data is correctly labeled `primary_registry`. Cleanup queued post-ship. Downstream consumers filtering on `sources.source_type='primary_registry'` should also include `sources.id IN (1,2,3,7)` until the cleanup lands.

**Future-enrichment hooks (operationally inert at v1.0.0):**

- **WiGLE integration** — the `wigle_anchor_priority` table ships at v1.0.0 populated with 80,697 pre-computed priority rankings but operationally inert (WiGLE API gated on user's own quota grant per WiGLE Terms of Service). Post-grant, the WiGLE integration activates without re-derivation.

**Substantive expansion areas (planned post-v1.0.0):**

- **Future community-source-acquisition waves** — additional crowdsourced + community-OSINT + court/FOIA + news/forum source families pending admission-review under the project's source-admission workflow.
- **iOS vendor companion app coverage** — vendor companion app static analysis extended to iOS APK/IPA binaries (v1.0.0 was Android-first; iOS adds vendors with iOS-exclusive companion apps).
- **Skydio Enterprise alt-channel scope** — `com.skydio.enterprise` Android package is law-enforcement-only distribution; alt-channel sourcing approach is a future scope proposal.
- **107 round-2 vocabulary held candidates** — the operator may extend the `identifier_type` enum or accept the candidates as out-of-scope at a future amendment boundary.
- **Lynceus MAP extensions for net-new identifier_types** — `ble_service_uuid` and `ble_company_id` are already aliased to existing pattern_types; other net-new types are currently DROPPED-class. Lynceus integrators may surface specific MAP needs in v1.x patch releases.
- **License-posture composition extensions** — additional downstream-consumer guidance may emerge if new license-posture classes surface.

### Build process

Argus v1.0.0 was built using a multi-agent orchestration platform (Paperclip) with bible-as-contract discipline. Build-process detail in [METHODOLOGY.md §8](METHODOLOGY.md). Commit metadata reflects the agent-ensemble + human-operator authorship per the project's authorship discipline; full identity attribution lives in the git log + [CREDITS.md](CREDITS.md) "Build authorship" section.

**Reproducibility:** the migrations and source-loaders in this repo deterministically reproduce the database from upstream public sources; the agent ensemble is not required at runtime. Re-running the build against current upstream snapshots will yield drift from the v1.0.0-tagged DB because upstream sources change. **Tagged DB releases (downloadable from GitHub Releases) are the canonical artifact for downstream consumers.**

### Acknowledgments

Argus v1.0.0 is the product of public-record research and aggregation across 43 upstream sources + the canonical 34-entry surveillance-tech vendor lexicon. See [CREDITS.md](CREDITS.md) for full per-source attribution.

Particular thanks to the upstream data sources whose licenses make this work possible:

- **EFF + UNLV Reynolds School of Journalism Atlas of Surveillance** (CC-BY-NC-SA-4.0) — the largest single deployment-observation corpus integrated (15,071 rows).
- **DeFlock** (ODbL-1.0) — ALPR-camera deployment observations integrated under license-compatible terms (101,597 rows).
- **IEEE Standards Association OUI registries** — public factual data anchoring the entire OUI→manufacturer attribution chain (~70,000 rows across MA-L/MA-M/MA-S/IAB).
- **FCC Equipment Authorization System** — public regulatory data anchoring the `fcc_id_anchored` disambig allowlist (50,153 grantees).
- **FAA Remote ID public registry** — public registry data anchoring the drone-class `drone_id_prefix` identifier-type cluster (427 active rows).
- **Bluetooth SIG company-identifier registry** — `ble_manufacturer_id` allocations (3,971 active rows).
- **NDSS 2025 Marlin: Detecting IMSI-Catchers by Characterizing Identity Exposing Messages in Cellular Traffic** — academic foundation for the `behavioral_signatures` table (53 raw observations contributing 55+38=93 corroborated signatures).
- **22 canonical community-OSINT contributors** + **5 secondary-batch contributors** — public open-source-intelligence research repositories listed at [CREDITS.md §5](CREDITS.md).
- **GainSec / anti-crime-ecosystem-research + flock-safety-falcon-sparrow-alpr-edl-firehose** — firmware-binary-anchored extracts (CC-BY-NC-ND-4.0 with research-use clause + NO_LICENSE_DECLARED under the Feist facts-only regime).
- **Wireshark community** — `manuf` file cross-reference for vendor-name curation.

### Integrating with v1.0.0

This is the first tagged release; there is no prior version to migrate from. Downstream consumers integrating Argus for the first time:

1. Download the `argus.db` release artifact from this release's GitHub Releases page (canonical), or build-from-source per [SETUP.md](SETUP.md).
2. Verify `schema_version=19` via `python3 argus_cli.py status` (or directly: `SELECT MAX(version) FROM schema_version;`).
3. Read [METHODOLOGY.md §5](METHODOLOGY.md) (confidence model) before threshold-filtering rows for downstream-scanner watchlists.
4. Read [DATA_DICTIONARY.md §6.2](DATA_DICTIONARY.md) (confidence-shape divergence) before integrating cross-table corroboration logic.
5. Read [LICENSE-DATA §2.1 + §4](LICENSE-DATA) for per-row license-posture handling (CC-BY-NC-SA-4.0 NC clause carry-forward; ODbL-1.0 ShareAlike; Feist facts-only regime; AGPL-3.0 inheritance).
6. Implement the JSON/CSV consumer per the export shapes documented at METHODOLOGY §5.5; bind to `argus_record_id` (16-hex-char SHA-256 prefix, `sha256('<identifier_type>|<normalized_identifier>')[:16]`) as the stable consumer-facing identifier across re-runs.
7. Filter `deployment_observations` on the `LICENSE` column for derivative-use compliance:
   - Commercial deployments: exclude `WHERE LICENSE = 'CC-BY-NC-SA-4.0'` (Atlas rows; non-commercial use only)
   - Standard ODbL ShareAlike compliance: include all (DeFlock + Atlas non-commercial use is licensed)
8. For consumers using `csv.DictReader` against `argus_export.csv`: line 1 is a `# meta:` comment with schema/timestamp/record count; line 2 is the column header. Skip line 1 or use a sniffer-aware reader (e.g., `pd.read_csv(comment='#')`).

---

## Future releases

The project will tag releases when substantive new data, new source families, or schema-impacting changes land. Notable post-v1.0.0 work queued (per "Known limitations + post-v1.0.0 roadmap" above):

- **v1.0.x patch releases** — refresh post-integration of any new public-record source family that completes the source-admission workflow during the post-v1.0.0 cycle; refresh post-resolution of held items (behavioral_signatures second-source corroboration; Class B re-triage if new registries become available).
- **v1.1.0** — projected to ship iOS vendor companion app coverage + future community-source-acquisition waves + Skydio Enterprise alt-channel resolution.

Release cadence: tagged releases when substantive change accumulates; no fixed schedule. Higher-major-version releases (v2.x+) are not projected at the v1.0.0 baseline; they would be documented at the time the change set triggering them is approved.

---

## Canonical sources

Descriptive references used in this document map to canonical bible
anchors as follows. The canonical bible (`PROJECT_BIBLE.md` and the
amendment ledger `BIBLE_AMENDMENTS.md`) holds the authoritative
specification; this CHANGELOG is the public-facing summary.

| Descriptive reference (as used in this doc) | Canonical source |
|---|---|
| canonical 34-entry surveillance-tech vendor lexicon | `PROJECT_BIBLE.md` §2.1 |
| source-type ten-value enum / confidence-band ceilings | `PROJECT_BIBLE.md` §8.2 |
| `+5` corroboration boost / corroboration math | `PROJECT_BIBLE.md` §8.3 |
| confidence model | `PROJECT_BIBLE.md` §5 |
| Lynceus identifier-type mapping | `PROJECT_BIBLE.md` §4.4 |
| export-shape contract | `PROJECT_BIBLE.md` §7.5 |
| hard-rule set (source-url-direct, no-PII, provenance, confidence-ceiling, amendment-log, Feist facts-only) | `PROJECT_BIBLE.md` §11 |
| Feist facts-only doctrine / canonical sentinel-key | `PROJECT_BIBLE.md` §11 #16 |
| `source_type='primary_registry'` band introduction | `BIBLE_AMENDMENTS.md` CP15 |
| `identifier_type` extension cluster (`product_family_codename` + `ble_local_name` + `ble_characteristic`) | `BIBLE_AMENDMENTS.md` CP13 |
| LA-bit pairing + Drone-RID + ALPR/camera taxonomy | `BIBLE_AMENDMENTS.md` CP14 |
| `manufacturer_app` sub-banding + cohort distinction | `BIBLE_AMENDMENTS.md` CP17 |
| behavioral_signatures sibling export | `BIBLE_AMENDMENTS.md` CP18 |
| `source_reclassifications` audit table | `BIBLE_AMENDMENTS.md` CP19 |
| `argus_record_id` stable-identifier algorithm | `BIBLE_AMENDMENTS.md` SAR-10 |
| framework-UUID false-positive class catalog | `BIBLE_AMENDMENTS.md` SAR-11 |
| per-shape mapper precedent (per-shape mapper / URL template / identifier_type-vs-behavioral_signatures routing) | `BIBLE_AMENDMENTS.md` SAR-13 |
