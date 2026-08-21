# METHODOLOGY.md: Argus

## TL;DR

How Argus integrates upstream sources into the canonical lexicon. Covers source-class confidence-band ceilings (the per-band caps codified at CP15), the §8.3 cross-source corroboration lift rule, the §11 #13 unknown-category Lynceus carveout, retroactive recategorization discipline (§11 #11 amendment-log), the dedup-and-supersession path, the no-PII discipline, the §11 #3 export-time PII generator post-condition guard (CP32 §10, codified at `BIBLE_AMENDMENTS.md` line 5235+), the Feist facts-only promotion regime, and the SAR roster: including SAR-16 (alias-length-floor), SAR-17 (no-generic-product-aliases), and SAR-18 (classifier-predicate parity), all codified at v1.5.0. The CP ladder extends to **CP37** at v1.6.2 ship anchor (mig-0030 `device_category` enum +1 `network_surveillance`**: lawful-intercept / monitoring-center vendors), with **CP38** (Step-2.3 codified: crowdsourced-detection-app `ssid_pattern`s default to `inferred/50`**: FlockYou full-enum sweep) as the highest CP token referenced at bible HEAD (data-only, no `schema_version` bump). The SAR ratified-cap is **SAR-18** (SAR-19 marked DRAFT pending ratification per `BIBLE_AMENDMENTS.md` line 4925: "Bible HEAD `PROJECT_BIBLE.md` NOT amended by this entry").

Intended audience: contributors adding new sources or vendor cohorts, validators ratifying cycle promotions, and security researchers verifying the methodology behind specific identifier promotions. Originally authored against the v1.0.0 ship state; substantively layered through CP15 → CP38 amendments at v1.6.2 ship anchor (HEAD `def7b95`). Cross-references to numbered clauses (`§N`) point at [`PROJECT_BIBLE.md`](PROJECT_BIBLE.md); cross-references to `CP N` or `SAR-N` point at [`BIBLE_AMENDMENTS.md`](BIBLE_AMENDMENTS.md).

To use the Argus exports, start with [`../USER_GUIDE.md`](../USER_GUIDE.md). For developer setup, see [`SETUP.md`](SETUP.md).

---

## §1. What this document covers

Argus is an open-source database of public-record-derived surveillance equipment identifiers (Bluetooth MACs, BLE service UUIDs, FCC grantee codes, default SSIDs, IMSI patterns, RID transmitter IDs, and related fingerprints). This document describes the methodology that was anchored at v1.0.0 and substantively layered through CP15 → CP38 amendments at v1.6.2 ship: how identifiers are sourced, how confidence scores are assigned, how duplicate observations are corroborated, and how the dataset is built. **v1.6.2 ship-state snapshot at bible HEAD `def7b95`:** schema_version 30; 41,508 active identifiers (41,890 total, 382 superseded via the §6.4 supersession discipline); 74 sources; 126 manufacturers; 201 behavioral signatures; 58-value `identifier_type` CHECK enum (49 populated); 17-value `device_category` CHECK enum (16 populated, post-CP37 `network_surveillance` admission); 13-value `source_type` CHECK enum on both `identifiers` and `sources` (CP36 dual-table parity).

METHODOLOGY.md is the public-OSS distillation of an internal project bible used to coordinate the build. For column-level reference, see [DATA_DICTIONARY.md](DATA_DICTIONARY.md). For onboarding and quickstart, see [README.md](../../README.md). For threat-model and adversarial-posture detail, see THREAT_MODEL.md (not yet present in repo; pre-existing forward reference).

**Glossary anchor:** Throughout this document, *database* refers to the queryable SQLite artifact (`argus.db`); *dataset* refers to exported JSON/CSV artifacts (`argus_export.json`, `argus_export_high_confidence.json`, `argus_export.csv`); *pipeline* refers to the migration + source-loader scripts that deterministically reproduce the database from upstream sources.

## §2. Mission and scope

Argus catalogs equipment identifiers, not people. Every row describes a piece of equipment: a Flock Safety camera MAC prefix, a DJI drone manufacturer OUI, an Axon body-camera Bluetooth identifier, a Cradlepoint in-vehicle router model, plus the public-record evidence linking that identifier to a manufacturer, operator, or deployment context. No row identifies an individual person. Operator names appear only where they are themselves public record (e.g., a city PD purchase order for Flock cameras).

Argus is **public-record-derived**: every identifier in v1.0.0 is sourced from publicly available material: FCC equipment authorization grants, federal procurement contracts (USAspending.gov), crowdsourced deployment maps (EFF Atlas of Surveillance, DeFlock), municipal council minutes, manufacturer documentation, and public research artifacts. Sources, source-type bands, and per-source confidence caps are documented in §3 and §5.

**What Argus is for:** Argus gives researchers, journalists, civil-society monitors, and field operators a queryable reference for "what is this identifier?" A Bluetooth MAC observed in a parking lot maps to "this is a Flock Safety camera, here's the FCC grantee, here's the procurement contract that put it there." The dataset is **operator-side-readable**: downstream consumers apply their own severity overrides and suppression filters (see §5 for the confidence-vs-severity separation).

**Argus does:** fingerprint-to-equipment-context lookup. It does not perform real-time tracking, individual identification, active interception, or produce live observations.

## §3. Sources and source-type hierarchy

Argus organizes sources by **`source_type`**, a schema-level enum that determines the confidence ceiling each source can contribute (see §5 for confidence bands). The v1.0.0 schema enum carried 10 values; CP23 added three judicial/corporate-disclosure/vendor-procurement-disclosure source-types, and CP36 closed the `identifiers.source_type` ↔ `sources.source_type` enum-parity gap. Both tables carry the same 13-value CHECK at v1.6.2 ship (verified: 13/13; 9 populated on `identifiers`, 10 on `sources`). Listed in descending order of active-identifier representation at v1.0.0:

- **`primary_registry`**: authoritative registries operated by the entity that owns the identifier namespace itself: FAA Remote ID registration, Bluetooth SIG company-identifier assignments. Distinguishing test: the registry IS the authoritative source-of-truth for what the identifier means; analogous to a CA/PKI root for fingerprint provenance. Confidence band: **70 to 85 single-source; up to 95 with cross-band corroboration per §5.2**. *v1.0.0 active identifiers: **417 (81.1%)** from Bluetooth SIG company-identifier registry + FAA RID prefix registry.*
- **`inferred`**: derived or computed identifiers that lack direct source citation in the artifact itself: identifier-to-manufacturer attributions computed from an upstream registry record (e.g., OUI→manufacturer inference from an IEEE registry walk) rather than copied verbatim from a source row. Confidence band: **30 to 70, capped**. *v1.0.0 active identifiers: **62 (12.1%)**. IEEE OUI promotion-cycle-1 outputs.*
- **`manufacturer_app`**: vendor mobile/desktop companion applications statically analyzed for embedded identifiers (BLE service UUIDs, default credentials, pairing codes). Confidence band: **60 to 95, sub-banded by identifier class; highest tier 80 to 95 for hardcoded BLE service UUIDs**. Operator-app vs installer-app sub-banding applies, installer/pairing-flow apps yield BLE/SSID/credential identifiers; operator apps yield product-family taxonomy only. *v1.0.0 active identifiers: **21 (4.1%)** from Flock Safety FS Installer + Getac BWC Viewer companion apps.*
- **`crowdsourced`**: community-curated deployment maps where contributors submit observations of physical equipment in the field. Tier-1 sources at v1.0.0: EFF Atlas of Surveillance, DeFlock. Confidence band: **50 to 75**. Community-curated sources classify here, not as a separate "community" tier (single canonical naming). *v1.0.0 active identifiers: **14 (2.7%)**.*
- **`official`**: court-verifiable government records distinct from regulatory filings: FCC EAS equipment authorization grants, FAA enforcement orders, court-ordered disclosures. Confidence band: **90 to 100**. *v1.0.0 sources: 1 (FCC EAS Equipment Authorization Grantee Registrations). No active identifiers promoted at v1.0.0: the FCC EAS corpus is staged in `raw_observations` for Phase-4+ extraction.*
- **`manufacturer_doc`**: manufacturer-published technical documentation (datasheets, integration guides, SDK documentation, technical reference manuals). Confidence band: **75 to 90**. *v1.0.0 sources: 2 (Hak5 product documentation Wayback snapshots; 0xXyc/flock-you-wifi-recon community repo). No active identifiers promoted at v1.0.0.*
- **`regulatory`**: government regulatory filings: FOIA-released equipment lists, court-verifiable government records, IEEE OUI registry (MA-L / MA-M / MA-S blocks) at v1.0.0¹. Confidence band: **80 to 95**. *v1.0.0 sources: 3 (IEEE OUI MA-L + MA-M + MA-S registry rows). No active identifiers promoted directly at v1.0.0: derived OUI→manufacturer inferences are classified `inferred` per the third-party-citation-lineage boundary (see §7.4 below).*
- **`procurement`**: federal/state/local procurement records: USAspending.gov contract awards, municipal purchase orders, vendor-agency contracts. Confidence band: **70 to 85** (proves *purchase*, not *deployment*). *v1.0.0 sources: 2 (USAspending.gov spending_by_award API; Granicus Legistar council/legislative-matters API). No active identifiers promoted at v1.0.0.*
- **`academic`**: peer-reviewed or conference-published research artifacts. Confidence band: **70 to 90**. *No v1.0.0 sources. Reserved for future ingest of academic-conference papers, thesis artifacts, peer-reviewed catalog publications.*
- **`foia`**: FOIA-released documents from federal/state/local FOIA requests. Confidence band: **65 to 85**. *No v1.0.0 sources. Reserved for future ingest of FOIA-released equipment manifests, contract records, and operational documents.*
- **`judicial_filing`** *(added migration 0020, CP23, 2026-05-17)*: court records and RECAP-class judicial artifacts (CourtListener V4 admissions). Confidence sub-banding inherits from the `regulatory` band: **80 to 95**, for promotion-pipeline purposes per CP23's reading that the new bands are source-tier taxonomy only and do not lift any confidence ceiling. *v1.1.0 sources: 1 (sid=48 CourtListener / RECAP via Free Law Project).*
- **`disclosure_filing`** *(added migration 0020, CP23, 2026-05-17)*: SEC EDGAR + analogous corporate-disclosure filings (wide-net cycle-1 RG5 admission). Confidence sub-banding inherits from the `regulatory` band: **80 to 95**. Distinguishes corporate-self-disclosure from equipment-authorization regulatory records (FCC EAS, FAA enforcement orders) which remain under `regulatory` / `official` per their pre-existing classification. *v1.1.0 sources: 1 (sid=49 SEC EDGAR).*
- **`procurement_disclosure`** *(added migration 0020, CP23, 2026-05-17)*: supplier-self-disclosure / vendor-side procurement artifacts (SAM.gov). Explicit confidence band: **80 to 95**. Distinguishes vendor-disclosed contracts (entity-registration self-attestations) from the agency-side bid/award records that the existing `procurement` band covers; the band is lifted above `procurement`'s 70 to 85 single-source band, but not to `regulatory`'s ceiling, because the disclosure is self-attestation rather than third-party verification. *v1.1.0 sources: 1 (sid=50 SAM.gov Entity Registration).*

**Rationale for the v1.1.0 enum extension** (per CP23 cycle-3 §1 finding #2): These three document-classes didn't fit the v1.0.0 ten-value enum cleanly. Routing CourtListener judicial filings or SEC EDGAR corporate disclosures to `regulatory` collapsed taxonomic distinctions load-bearing at confidence-band differentiation time. The equipment-authorization registries (FCC EAS, FAA enforcement orders) anchoring the `regulatory` band's 80 to 95 ceiling shouldn't share confidence headroom with judicial discovery filings whose evidentiary weight is materially different. Vendor self-disclosure on SAM.gov needed a distinct band from generic `procurement`, which is reserved for agency-side bid/award records. The two source-classes differ in evidentiary footing (self-attestation vs third-party transaction record) and corroboration profile (single-vendor-controlled vs multi-agency-witnessed). The 13-value enum is the post-CP23 canonical state; the new bands are source-tier taxonomy only. The `identifiers.source_type` enum is unchanged at CP23; identifier rows promoted from sources of these classes land under the existing §5.1 confidence-band ceilings.

¹ *IEEE OUI sources are classified as `regulatory` at v1.0.0 ship. The internal project bible specifies `primary_registry` as the canonical destination band; reclassification of the IEEE OUI source rows is a documented post-v1.0.0 batch task.*

**Source-vs-`source_type` distinction:** A single `source_type` may have multiple `sources` entries. Each `sources` row carries its own license metadata, license attribution, and source-class confidence ceiling within the `source_type` band.

**Provenance gate (prose form of the promotion-gate hard rule):** Every row in the live `identifiers` table carries traceable provenance: a `source_url` pointing at the upstream artifact and a `source_excerpt` capturing the relevant text. Provenance discipline is absolute and universal: a candidate without ancestry in a fetched source artifact does not promote, regardless of source-type or apparent corroboration. *"Provenance is the database. Without it, we have a rumor."*

**Corroboration & single-source eligibility:** Most source-types require independent-source corroboration for promotion. A candidate identifier observed in only one source remains staged in `raw_observations` until a second source from a different `source_type` confirms the same identifier-to-manufacturer binding. A `crowdsourced` observation alone does not promote; paired with `regulatory` or `manufacturer_doc`, it does. **`primary_registry` carveout:** A single `primary_registry` citation suffices for promotion at confidence 85, because the registry IS the authoritative source-of-truth for the identifier. Asking for "three independent sources" of what FAA Remote ID block `1581Fxxx` means is structurally ill-defined; FAA's registry is the source of truth with no parallel source-of-truth to corroborate against. Cross-band corroboration with `regulatory` or `manufacturer_doc` lifts up to 95 per §5.2. The carveout applies to `primary_registry` only; other source-types' corroboration cut-offs remain in force.

**Confidence ceiling rule (prose form of the confidence-ceiling hard rule):** Within those eligibility rules, no identifier's confidence may exceed the lowest source-type band ceiling among its contributing sources. A `regulatory` (ceiling 95) + `crowdsourced` (ceiling 75) corroboration produces a row with confidence ≤ 75: the lowest contributing band wins. The corroboration boost from §5.2 (multi-source dedup, `min(99, max(originals) + 5)`) is applied within the ceiling, not over it.

## §4. Identifier types and the `identifier_type` enum

Argus distinguishes between identifiers that a wire-observing scanner (e.g., Lynceus, the canonical downstream consumer) can match against broadcast traffic, identifiers that exist only as analytical cross-reference taxonomy, and parametric metadata that describes a property of an emission rather than a discrete match value. The schema's **`identifier_type`** enum makes this distinction explicit at row-creation time, so downstream consumers know exactly which entries flow into scanner watchlists and which are analytical-only.

### §4.1 Three categories

Every `identifier_type` enum value falls into one of three structural categories:

1. **Wire-observable**: values a scanner can read off a broadcast frame and match against a fixed pattern. Examples: a 6-byte MAC address, a 3-byte OUI, a BLE service UUID, an SSID broadcast in a Probe Response, a Remote ID drone identifier prefix. These ride the Lynceus export and become live scanner-watchlist entries.

2. **Analytical-only**: taxonomy values, vendor-internal cohort labels, fingerprint cluster identifiers, and structurally-wire-observable identifiers whose downstream-consumer support is not yet implemented at the v1.0.0 ship version of Lynceus. Captured to cross-reference and disambiguate identifier rows, but never exported as a scanner pattern at v1.0.0. Examples: a Flock Safety `DeviceType` enum string (`product_family_codename`), a fingerprint cluster label (`device_fingerprint`), an ALPR vendor-product name (`alpr_model`), a BLE GAP local-name string (`ble_local_name`; structurally wire-observable but Lynceus v0.3 lacks GAP local-name match support), an ICAO 24-bit aircraft address (`icao_24bit_address`; structurally wire-observable but out-of-band RF for the baseline Pi BLE/WiFi scanner, RTL-SDR upgrade unlocks observability).

3. **Parametric metadata**: properties of an emission rather than discrete match values: an RF channel number, a burst cadence in milliseconds, a bandwidth in megahertz, a sub-protocol-level fragment that is structurally too coarse or too composite to function as a Lynceus watchlist pattern. These are captured during analysis to drive triage and category-attribution heuristics but are never exported, scanner-side or analytical-side, as a pattern-match value.

The category determines export fate; the per-type semantics determine extraction rules, confidence-band ceilings, and disambiguation criteria. Forward-extensibility: as the Lynceus consumer adds capability (GAP local-name matching, characteristic-discovery, RTL-SDR ADS-B decode, etc.), structurally-wire-observable identifiers currently classified analytical-only re-categorize to `wire-observable` at the Argus version that lands the consumer-side capability. The category column on a row reflects the v1.0.0 export fate, not the structural nature of the identifier.

### §4.2 The v1.0.0 enum (and v1.6.2 layer)

At v1.0.0, the `identifier_type` enum carried 26 values. Eleven are foundational (added in initial schema + Wave G structural-fidelity extensions); fifteen were added in subsequent extensions to accommodate RF-layer, parametric, and sub-protocol identifier classes surfaced during vendor companion-app static analysis + FAA RID drone registry + BLE SIG manufacturer-ID clusters. The live CHECK enum at v1.6.2 ship anchor carries **58 values** (verified at `db/argus.db` HEAD; 49 populated). The v1.0.0 cluster is preserved verbatim below; the 32 net-new types added between v1.1.0 and v1.6.2 (CP20 SAR-13 §S.3 vendor-anchored cluster +14, MAC-117 mig-0019 +7, CP28 mig-0023 +3, CP29 mig-0024 +3 hostname-corpus, CP31 mig-0025 FCC EAS +2, CP33 mig-0027 GSMA TAC +1, CP34 mig-0028 `network_discovery_protocol_pattern` +1, plus additional G-3 / mig-0011 + mig-0013 / mig-0014 surveillance-metadata batches) live in the schema CHECK and the per-type semantics are documented at [DATA_DICTIONARY.md §3](DATA_DICTIONARY.md).

**Foundational types:**

| Type | Category | Semantics |
|---|---|---|
| `oui` | wire-observable | IEEE-allocated 3-octet vendor prefix (e.g., `aa:bb:cc`). Matches the first three octets of any MAC address. |
| `mac` | wire-observable | Full 6-octet MAC address. Matches a specific device. |
| `mac_range` | wire-observable | OUI-28 / OUI-36 sub-allocation block. Expanded to individual MACs at export time only if range size ≤ 256; otherwise dropped from Lynceus export and noted in the coverage report. |
| `bssid` | wire-observable | Wireless access point MAC, broadcast in 802.11 Beacon and Probe Response frames. Maps to Lynceus `pattern_type=mac` at export time. |
| `ssid_exact` | wire-observable | Exact-string SSID match. Broadcast in 802.11 Beacon frames or returned in Probe Response. |
| `ssid_pattern` | analytical-only | POSIX regex SSID pattern. Dropped from Lynceus v0.3 export (no regex support in the consumer scanner); analytical-only at v1.0.0. |
| `ble_uuid` | wire-observable | Bluetooth Low Energy service or characteristic UUID, broadcast in BLE GAP advertising frames. |
| `ble_service` | wire-observable | BLE service UUID specifically (subset of `ble_uuid` typing for analytical clarity). Maps to Lynceus `pattern_type=ble_uuid` at export time. |
| `device_fingerprint` | analytical-only | Hardware fingerprint cluster label. v0.3 Lynceus has no fingerprint matching; analytical-only. |
| `ble_local_name` | analytical-only | BLE GAP Local Name field string. Structurally wire-observable (broadcast in BLE GAP advertising frames); analytical-only at v1.0.0 because Lynceus v0.3 lacks GAP local-name match support. Re-categorizes to `wire-observable` at the Argus version that lands a Lynceus release with GAP local-name matching. |
| `ble_characteristic` | analytical-only | BLE characteristic UUID. Structurally wire-observable but analytical-only at v1.0.0 because Lynceus discovers devices by service UUID, not by characteristic; characteristic-discovery is a consumer-side capability gap. Re-categorizes to `wire-observable` when Lynceus adds characteristic-discovery. |
| `product_family_codename` | analytical-only | Vendor-internal cohort identifier: e.g., a Flock Safety `DeviceType` enum value (`FALCON_LR3`, `RAVEN_R6`). Vendor-internal taxonomy; never matched by a wire scanner. |

**RF / parametric / sub-protocol additions:**

| Type | Category | Semantics |
|---|---|---|
| `ble_manufacturer_id` | wire-observable | 2-byte Bluetooth SIG company-identifier value embedded in BLE manufacturer-specific advertising data (e.g., Apple `0x004C`, XUNTONG `0x09C8`). |
| `drone_id_prefix` | wire-observable | ASTM F3411-22a Remote ID frame prefix (e.g., FAA RID `1581Fxxx` block). Broadcast across WiFi NAN action frames, WiFi Beacon vendor IE, and BLE Legacy 4.x advertising. BLE5 LE Coded PHY decode is a baseline-Pi-BLE-chipset limitation; coverage on baseline hardware is dominated by the WiFi-NAN / Beacon variants. |
| `wifi_aware_service_name` | wire-observable | WiFi NAN (Neighbor Awareness Networking) service-discovery service-name string. Capability-gated by Lynceus-side NAN support; Argus exports unconditionally per the consumer-carries-capability-state posture. |
| `icao_24bit_address` | analytical-only | 24-bit ICAO aircraft / drone Mode S address broadcast in 1090MHz ADS-B Out frames. Structurally wire-observable but analytical-only at v1.0.0 because ADS-B is out-of-band for the baseline Pi BLE/WiFi scanner; an RTL-SDR upgrade path unlocks observability. Re-categorizes to `wire-observable` for ADS-B-equipped scanners at the Lynceus version that lands RTL-SDR ADS-B decode support. |
| `alpr_model` | analytical-only | Vendor-product taxonomy string (e.g., "Flock Safety Falcon", "Motorola Vigilant", "Genetec AutoVu"). Concrete ALPR-camera identifiers flow via `oui`/`mac`/`bssid`/`ssid_exact`; `alpr_model` is the analytical taxonomy column. |
| `rf_channel`, `burst_cadence_ms`, `bandwidth_mhz`, `rf_burst_duration` | parametric metadata | Temporal and spectral-occupancy properties of an observation. Captured for analytical triage and category attribution, never exported. |
| `device_class_id` | parametric metadata | Proprietary-protocol device-class enum label. A categorization-time attribute, not a wire-observable identifier string. |
| `rf_protocol_constant` | parametric metadata | PHY-layer constants (sync words, frame markers) not surfaced by the Linux WiFi/BT subsystem to userspace at the baseline Pi capability envelope. |
| `wifi_ie_element_id` | parametric metadata | 1-byte 802.11 Information-Element tag (0 to 255), structurally too coarse to function as a watchlist pattern alone. |
| `bluetooth_le_pdu_type`, `wifi_frame_control_subtype` | parametric metadata | Link-layer / frame-control enum values (4-bit BLE PDU type, 802.11 frame-control subtype). |
| `wifi_nan_param_signature` | parametric metadata | Derived signature over multiple NAN service-info fields. Lynceus's pattern engine matches single identifier strings, not multi-field aggregates; future Lynceus signature-matching capability would be a new `pattern_type`. |

### §4.3 Why three categories matter for downstream consumers

The three-category split makes the export contract explicit: a wire-observable row of confidence ≥ 70 will appear in `argus_export_high_confidence.json` (subject to the `device_category='unknown'` carveout and the geographic-scope filter); an analytical-only row never enters the Lynceus scanner JSON regardless of confidence; a parametric metadata row enters neither the scanner JSON nor the analytical CSV (it lives in the canonical database and the coverage report only).

Consumers building integrations should anchor on the `identifier_type` column when deciding match logic. A row with `identifier_type='product_family_codename'` is a vendor-internal taxonomy label; matching against device traffic is structurally undefined. A row with `identifier_type='mac_range'` requires range-expansion logic on the consumer side or use of the pre-expanded Lynceus shape.

### §4.4 Match-scoring discipline for short-name vendors against text-pattern sources (CP26, 2026-05-17)

Match-scoring against textual sources (regulatory filings, judicial filings, news/forum, FOIA documents, vendor-disclosure narratives) is structurally different from match-scoring against structured-API sources. Text-pattern match: vendor-token co-occurs with agency-token within an N-word window: is necessary but NOT sufficient for STRONG promotion when the vendor name is short (≤6 characters or single-word) or shares vocabulary with non-vendor surface forms (given names, common adjectives, statutory-amount idioms).

**Per CP26 §8** (n=4 codification, 2026-05-17): any match-scoring §4 step against a textual source MUST validate the semantic relationship between the vendor-token and the surrounding-context anchor (customer, contractor, vendor, defendant, etc.) BEFORE promoting the match. The semantic-validation step is a default §4 sub-step: punting to validator-time review is no longer the canonical pattern.

**Anchored case studies:**

- **Berla collision** (cycle-3 RG3 CourtListener): the vendor token `Berla` (5 chars, single-word) STRONG-matched against CourtListener's `"Berla Kay Strong v. Thomas Wesley Strong"`, a family-court matter where "Berla" is a given name, not the digital-forensics vendor. Three cases STRONG-matched on text-pattern; zero survived semantic-relationship validation.
- **Flock single-token-alias fanout** (SAM.gov cycle-5, the finding that surfaced the n=4 threshold): the alias fanout for Flock Safety (`aliases[0]='Flock'`, 5 chars) matched `"Funny Flock Farms LLC"` on whole-word substring containment in the candidate's normalized legal name. The match was correctly graded WEAK at staging: surfacing the structural brittleness: but exposed that single-token short-alias fanouts are not safe for STRONG promotion without additional semantic-relationship triangulation (vendor ↔ product-family ↔ NAICS adjacency, or vendor ↔ contracting-agency ↔ contract-value coherence).

**Disambiguation options** (in declining preference, per §6.7 + CP26 §8 composition):

1. **Co-occurrence filter**: require the matched query token to appear alongside another vendor-specific token (product-family name, industry-anchor term, NAICS-adjacent vocabulary) within N words. Cheapest at extraction time; runs against the source's own returned snippet/description.
2. **Entity-type tagging**: if the source exposes party-role metadata (defendant vs plaintiff, corporate vs natural-person, contractor vs co-defendant), filter to corporate-party-only or contractor-party-only matches. Source-dependent; CourtListener V4 exposes `party[]` at the docket level; SAM.gov exposes entity-type at the registration level.
3. **Semantic-relationship triangulation**: vendor ↔ product-family ↔ NAICS coherence check (e.g., a short-name vendor matched against an agency without surveillance-adjacent NAICS overlap fails the triangulation regardless of text-pattern co-occurrence; alias-length ≥4 chars with whole-word containment is necessary but not sufficient for STRONG promotion per CP26 §6).
4. **Operator review of WEAK/STRONG candidates** for short vendor names (≤6 chars or single-word) before promotion: manual fallback when steps (1) to (3) are not available.

**Documented FP classes at codification** (CP26 §8; non-exhaustive, for runguide §-text hints): risk-factor-narrative co-occurrence, compliance-attestation co-occurrence, competitor-data-sharing co-occurrence, co-defendant co-presence (BRINC 57-co-defendant pro-se RICO pattern), statutory-amount co-occurrence (BRINC $405 = 28 USC §1914 filing fee, not vendor contract value).

The discipline composes with §6.7 (short-vendor-name disambiguation at the dedup-pass layer): §4.4 catches short-name FPs at extraction time; §6.7 catches them at dedup time when the extraction-side filter has already passed. Both gate against premature confidence-band assignment.

## §5. Confidence model

Argus assigns a numeric `confidence` to every row in the `identifiers` table: an integer representing the strength of the evidence binding the identifier to its claimed attribution (manufacturer, device category, operator, deployment-locality fact). Downstream consumers use this value to threshold what enters scanner watchlists, what enters the analytical export only, and what stays staged for review.

Confidence is not a probability. It is a calibrated band representing the underlying source-type's reliability adjusted for corroboration, specificity, and recency. The operational scale is bounded at 99 (never 100); perfect certainty is never claimed. The residual 1 is a humility margin for fabrication, transcription, or registry-mutation risk that no public-source-derived value can fully retire. (Schema-level CHECK constraint permits 0-100; the 99 cap is enforced operationally at the corroboration-boost + ceiling-rule layers.)

### §5.1 Default confidence comes from `source_type`

Each row's default confidence sits within the source-type's band, per the table below (ordered by band ceiling descending, this is the confidence-hierarchy view; §3's source_type framing orders the same enumeration by v1.0.0 active-row count for the dataset-composition view). Within a band, the exact value is adjusted up for specificity (full-octet vs. OUI-only, hardcoded vs. configuration-derivable), recency (citation within the past 24 months vs. >5 years old), and corroboration (independent second-source agreement); adjusted down for known-FP-class proximity (framework-string sub-rule), staleness, or thin extraction context.

| Source type | Default confidence band |
|---|---|
| `official` (court-verifiable government filings, FCC EAS, FAA enforcement orders, court-ordered disclosures) | 90 to 100¹ |
| `primary_registry` (authoritative numerical-allocation registries, see §5.3 sub-banding) | 70 to 85 single-source; up to 95 with cross-band corroboration |
| `regulatory` (gov't filings + court order text, non-`official`-tier regulatory provenance) | 80 to 95 |
| `judicial_filing` (CourtListener / RECAP-class judicial records, CP23, added 2026-05-17) | Inherits `regulatory` sub-banding: 80 to 95 |
| `disclosure_filing` (SEC EDGAR + corporate-disclosure filings, CP23, added 2026-05-17) | Inherits `regulatory` sub-banding: 80 to 95 |
| `procurement_disclosure` (SAM.gov + vendor-side procurement self-disclosure, CP23, added 2026-05-17) | 80 to 95 (distinct from generic `procurement` band per §3 rationale) |
| `manufacturer_doc` (vendor spec sheet, datasheet, integration guide) | 75 to 90 |
| `manufacturer_app` (vendor companion APK/IPA static-analysis extract, see §5.4 sub-banding) | 60 to 95, sub-banded by identifier class |
| `procurement` (SAM.gov, USAspending.gov, state portals) | 70 to 85 (proves *purchase*, not *deployment*) |
| `academic` (peer-reviewed or conference) | 70 to 90 |
| `foia` (FOIA-released documents) | 65 to 85 |
| `crowdsourced` (community-curated deployment maps: WiGLE, DeFlock, EFF Atlas) | 50 to 75 |
| `inferred` (computed from upstream registry records) | 30 to 70, capped |

¹ Band ceilings listed represent each source-type's theoretical maximum. Actual per-row confidence is capped at 99 (never 100) via the §5.2 corroboration formula and the §5.6 ceiling rule.

### §5.2 Corroboration boost: multi-source dedup

When two independent sources independently attest the same identifier-to-attribution binding, Argus's dedup pass (§6) collapses them into a single canonical row and applies a corroboration boost. The formula:

> `confidence_canonical = min(99, max(confidence_originals) + 5)`

Two independent `crowdsourced` sources at 70 each corroborate to a single canonical row at 75. A `crowdsourced` at 70 plus a `regulatory` at 90: the boost formula yields `min(99, max(70,90)+5) = 95`, but §5.6's ceiling rule caps confidence at the lowest contributing band ceiling: `crowdsourced`'s 75. Final canonical confidence: **75**. See §5.6 for the ceiling-rule rationale.

The +5 boost is a single bonus per dedup pass, not compounding per additional source; a row corroborated by five sources gets +5 once, not +25. The corroboration boost composes within the §5.6 ceiling rule, never over it.

**Within-source re-extraction is NOT cross-source corroboration (CP24 §11 #8 sub-rule, 2026-05-17).** Re-querying the same upstream registry at two different times: whether under the same extraction session or a deeper-extension session against the same API: does NOT satisfy the §5.2 / §6.3 independence test for the +5 corroboration boost. Re-extraction validates extraction-time fidelity, coverage breadth, and upstream-record persistence; it does NOT independently confirm the underlying fact. The +5 lift requires a genuinely independent collector, different upstream registry, different methodology. Within-source re-extraction merges provenance into `notes.corroborations[]` (a breadth-not-strength signal); confidence does not lift. The canonical evidence at codification: the MAC-172 USAspending deep-extension session lifted 180 procurement_records rows 85→90 under a misreading of §11 #8; a ratification (Read B) rolled all 180 rows back to confidence=85, preserving the provenance merge and the `notes.corroboration_sessions[]` session-tag audit-trail. Future deeper-extraction runguides MUST classify their outputs as "provenance enrichment cycle" (within-source re-extraction; notes-only merge; no lift) vs "cross-source corroboration cycle" (genuinely independent collector; +5 lift via §5.2 within the §5.6 ceiling) at runguide §-text time.

**Citation hygiene (CP24, 2026-05-17):** the "+5 boost" formula `confidence_canonical = min(99, max(confidence_originals) + 5)` is anchored in METHODOLOGY §5.2 (this document's internal heading); the bible-side canonical anchor is PROJECT_BIBLE.md §8.3 + §11 #8. Forward-looking handoffs, runguides, and dispatch templates cite "§8.3 + §11 #8" for the corroboration-lift rule; the METHODOLOGY-internal "§5.2" heading remains valid as a cross-document reference within this document's structure.

**N-occurrence promotion threshold (CP25, 2026-05-17):** a false-positive class (FP-class) surfaced during validator-time review is eligible for promotion to a recognized confidence-band-affecting discipline after n=2 independent corroborations (was implicit prior to CP25; now explicit). The threshold composes with the §11 sub-rule codification path codified at CP25 §3: at n=2 the FP-class is captured at `sources.notes.candidate_findings_for_future_cp_or_sar[]`; at n=3 the FP-class is eligible for dedicated §11 sub-rule codification; at n≥4 the codification trigger is mandatory (CP26 §8 codification path).

**Text-pattern n=4 codification (CP26 §8, 2026-05-17):** a text-pattern match against any §3 source-type becomes a default-strength corroboration ONLY after n=4 independent occurrences combined with semantic-relationship validation per §4.4. Below n=4, text-pattern matches against textual sources stage to operator-review-queue rather than promoting at default strength; the codification follows the CP25 §3 stated evolution path from "carve-out observed in one dispatch" (n=1) → "candidate sub-rule queued at `notes.candidate_findings_for_future_cp_or_sar[]`" (n≥2) → "dedicated §11 sub-rule codified" (n≥3, mandatory at n≥4).

### §5.3 `primary_registry`: single-source-sufficient with sub-band

Authoritative numerical-allocation registries: IEEE OUI registry, Bluetooth SIG company-identifier registry, FAA ANSI/CTA-2063-A Remote ID registry: get a special carveout: a single citation from the registry IS sufficient evidence for promotion, because the registry IS the authoritative source-of-truth for what the identifier means.

The 70 to 85 single-source band's ceiling (85) reaches above `crowdsourced`'s ceiling (75); registry issuance carries more authority than community curation. The same band's ceiling (85) sits below `regulatory`'s 95: registries are issuer-of-record but not court-verifiable in the regulatory-filing sense. Cross-band corroboration with `regulatory` or `manufacturer_doc` lifts up to 95 per §5.2 with §5.6 composition.

**Reclassification discipline** (row-level discipline, distinct from source-level migration): A row in the `identifiers` table reclassifies from `crowdsourced` or `inferred` to `primary_registry` only when its existing `source_url` already points DIRECTLY at the registry issuer's own publication (FAA's database URL, SIG's company-identifier registry URL, IEEE's MA-L assignment record URL). If the `source_url` points at a third-party citation: community repo, blog post, aggregator, academic paper that cites the registry: the row stays in its current band. To establish `primary_registry` classification with the higher confidence band, a new `raw_observations` row citing the registry directly is required.

### §5.4 `manufacturer_app`: sub-banded by identifier class

The `manufacturer_app` 60 to 95 outer band breaks down per identifier class:

| Identifier class extracted from vendor app | Sub-band | Rationale | Typical cohort |
|---|---|---|---|
| Hardcoded BLE service UUID (128-bit or 16-bit-in-context) | 80 to 95 | BLE specs require the service UUID for discovery; the vendor app must contain the canonical value. | installer/pairing |
| `vendor_template_namespace_uuid` | 75 to 90 | Vendor-chosen UUID-suffix namespace (e.g., Getac's `-1b7f-430ea194e6cf` suffix). Below hardcoded-BLE-service tier because individual values are inferred-by-pattern. | installer/pairing |
| Default SSID pattern (vendor-prefix WiFi name) | 70 to 85 | Clear vendor attestation in code; hardware match TBV at scan time. | installer/pairing |
| Default credential string (plaintext) | 60 to 80 | Vendor-attested at app version, but firmware may have rotated. | installer/pairing |
| MAC OUI from validation code path | 75 to 90 | Confirms OUI assignment; cross-checks against IEEE Tier-1 registry. | installer/pairing |
| Product-family taxonomy: `marketing_name` | 90 to 95 | Vendor's own marketing product naming inside their own app. | both cohorts |
| Product-family taxonomy: `internal_codename` | 90 to 95 | Engineering-internal naming surfacing in app code. | both cohorts |
| Product-family taxonomy: `device_type_enum_value` | 90 to 95 | Authoritative product-family taxonomy from vendor's own enum declaration. Highest specificity tier. | both cohorts |

**Cohort distinction:** Operator-facing apps yield product-family taxonomy ONLY (empirical evidence from vendor-app static analysis: 8 operator/pilot apps surveyed yielded 0 BLE UUIDs). Installer/pairing-flow apps yield BLE service UUIDs + SSID patterns + credentials + product-family taxonomy (empirical evidence: 2 installer/pairing apps yielded 6 unique vendor BLE UUIDs + complete DeviceType taxonomy). Extraction queue ordering should prioritize the installer/pairing-flow cohort for non-product-family identifiers.

### §5.5 Export thresholds

Downstream consumers pull from one of two wire-observable JSON export shapes (Lynceus) plus the analytical CSV (Lynceus rich-feed) plus the cellular-band behavioral-signatures JSON (Rayhunter). Per bible §7.5 (the `_meta` + `entries` shape is bible-canon at `PROJECT_BIBLE.md` lines 629-668):

- **`argus_export.json` (standard export, Lynceus alert-feed)**: all active wire-observable rows with `confidence ≥ 30`, subject to the `device_category='unknown'` carveout (§11 #13) and the geographic-scope filter (CP7, default `("US",)` plus `global` unconditional pass). **At v1.6.2 ship anchor: 592 entries** drawn from 41,508 active identifiers (`_meta.source_record_count=41508`, `_meta.record_count=592`, `_meta.confidence_threshold=30`; the `_meta.dropped_in_export` tallies sum 40,916 with `41,508 − 40,916 = 592` matching `entries.length` per the §7.5 reconciliation contract). v1.0.0 ship row count: **443** (historical anchor; composition: 415 FAA RID `drone_id_prefix` + 28 pre-cycle-2 calibration survivors). Two `ble_manufacturer_id` rows (Apple `0x004C` + XUNTONG `0x09C8`) classified `primary_registry` at the source-type level but `device_category='unknown'` at the row level are excluded per the unknown-category carveout; 62 IEEE OUI promotion-cycle-1 outputs are classified `inferred` per the third-party-citation-lineage boundary.
- **`argus_export_high_confidence.json` (high-confidence export, Lynceus default scanner watchlist)**: all active wire-observable rows with `confidence ≥ 70` (per bible §7.5 canonical floor at `PROJECT_BIBLE.md` line 664: `"confidence_threshold` is `0` for `argus_export.json` ... and `70` for `argus_export_high_confidence.json`"; the operator-side floor is **never ≥ 80**), excluding rows with `device_category='unknown'` AND additional CP19 `crowdsourced` exclusion. **At v1.6.2 ship anchor: 146 entries** (`_meta.record_count=146`, `_meta.confidence_threshold=70`, drop tallies sum 41,362; `41,508 − 41,362 = 146`).
- **`argus_export.csv` (analytical CSV, rich-feed)**: all active rows (wire-observable + analytical-only) regardless of confidence, with the full per-row column set including license, scope, and provenance fields per CP11 sub-A. **At v1.6.2 ship anchor: 41,508 data rows** (CSV `# meta:` line carries `record_count=41508, confidence_threshold=0`; physical line count differs from data-row count due to embedded newlines in quoted `notes` / `source_excerpt` fields). v1.0.0 ship row count: **514** (historical).
- **`argus_export_behavioral_signatures.json` (cellular-band IMSI-catcher behavioral signatures, Rayhunter feed)**: added v1.3.0 via the §7.5 CP18 sub-bundle (see §16 below). At v1.6.2 ship: **125 entries** drawn from 201 behavioral_signatures rows (`_meta.confidence_threshold=70`, drop tallies cover `below_confidence_threshold` + `unknown_category`).

The standard-export ≥ 30 floor exists to drop rows where the underlying evidence is structurally thin while still allowing operators with their own filtering logic to consume the broader set. The high-confidence-export ≥ 70 floor is calibrated to surface rows that an operator running an unattended scanner can act on without per-row review.

**§11 #3 export-time PII generator post-condition guard (CP32 §10**: codified at `BIBLE_AMENDMENTS.md` line 5235+).** Every export emission call site MUST invoke `_assert_no_email_pii(path)` after the file is written; the guard re-reads the written file and `Halt`s on any RFC-shape email match per the regex `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b`. The pattern lives at `db/validation/export_lynceus.py` (3 call sites: standard JSON, high-conf JSON, coverage_report.md) + `db/validation/export_behavioral_signatures.py` (1 call site). Defense-in-depth rationale per §15 below.

### §5.6 The ceiling rule (prose form)

Within the corroboration boost (§5.2) and per-band defaults (§5.1), no identifier's final confidence may exceed the **lowest** source-type band ceiling among its contributing sources.

A `regulatory` (ceiling 95) row corroborated by a `crowdsourced` (ceiling 75) row produces a canonical record at confidence ≤ 75: the corroboration is real evidence, but the binding has not been independently established by a higher-band source. The corroboration boost from §5.2 applies WITHIN the ceiling, not OVER it: `min(99, max(originals) + 5)` is bounded above by the lowest contributing band's ceiling.

**Why the lowest-ceiling-wins rule:** if a `crowdsourced` claim is the only `crowdsourced` evidence for a binding, that binding's evidence is no stronger than `crowdsourced` evidence alone: the higher-band corroborator is corroborating a `crowdsourced`-class observation, not creating an independent higher-band attestation. The ceiling reflects the weakest contributor, because the binding's evidence quality is gated by its weakest source. To lift the ceiling, an independent higher-band source must directly attest the identifier-to-attribution binding (not corroborate a lower-band claim about it).

### §5.7 Confidence is calibrated, not Bayesian

Argus does not run a Bayesian update over heterogeneous evidence sources. The confidence model is a deliberately simple calibration scheme: source-type band + corroboration boost + per-class sub-bands + ceiling rule: chosen for auditability over expressiveness. A reader of the database can reproduce any row's confidence from its `source_type`, its corroboration count, and the §5.2/§5.4/§5.6 rules, without consulting opaque internal weights. The trade-off is real: the scheme cannot represent fine-grained per-source reliability differences within a band, and corroboration is treated as a single +5 boost rather than a more nuanced per-pair weighting.

Future-version refinements (per-source-class reliability priors, identifier-class-specific corroboration boosts, decay-over-time models) are out of scope for v1.0.0. The auditable simple-calibration model ships first; refinements gate on a documented operator-class need.

### §5.8 Cross-source corroboration audit-trail discipline (CP25, 2026-05-17)

Per CP25 §1, any retraction of a previously-recorded cross-source corroboration marker MUST leave a parallel forensic-trail entry. The convention applies to both the `identifiers.notes` JSON (for promoted-row corroboration markers) and the `procurement_records.notes` JSON (for procurement-record corroboration markers per CP24 sub-rule (b) spirit-extension).

**`cross_source_corroboration_reversals[]` array convention:** when a `notes.cross_source_corroboration[]` marker is retracted post-validation under §11 #1 or §11 #8 review, the retraction MUST append a parallel `notes.cross_source_corroboration_reversals[]` array entry in the same transaction as the corroboration-array UPDATE. Each reversal entry carries five required keys:

- `at_utc`: ISO-8601 timestamp of the reversal UPDATE
- `marker_key`: the original `cross_source_corroboration[]` entry's `marker_key`, copied verbatim (preserves forensic recoverability without scanning the live corroboration-array)
- `rationale`: short prose citing the §11 hard rule that triggered the retraction + the §-anchor evidence
- `dispatch`: the MAC-NNN issue identifier of the retracting dispatch
- `cp_anchor`: canonical CP citation (e.g., `"CP25 §1"`)

The original `notes.cross_source_corroboration[]` entry is REMOVED from the array (not soft-deleted; the reversal-array IS the audit-trail). For forensic-grade traceability, any historical 85→90→85 confidence transition that traces to a now-retracted cross-source corroboration is reconstructable by joining the reversal-array entry's `marker_key` to the row's separate `notes.confidence_history[]` audit-trail (CP24 sub-rule (b): every `procurement_records.confidence` UPDATE outside of initial INSERT appends a `{at_utc, from, to, rationale, dispatch, cp_anchor}` entry).

**Composition:** §5.8 (retraction-audit) is the complement to CP24 sub-rule (b)'s lift-audit pattern. The two are parallel: lift-audit answers "when did confidence go up and why?"; retraction-audit answers "when was a corroboration marker pulled and why?". Same forensic shape, different trigger.

**Live discipline applied this release:** the 90→85 confidence rollback discipline (CP24 strict-independence reading of §11 #8) was applied to 180 `procurement_records` rows that had been lifted by a within-USAspending re-extraction misread; each rolled-back row carries a `notes.confidence_history[0]` audit entry citing CP24. The MAC-171 id=86738 cross-source corroboration retraction (Congressional IG-investigation reference erroneously read as a customer-relationship attestation) is the first consumer of the §5.8 reversal-array convention.

## §6. Dedup logic

The dedup pass is the single most consequential transformation in the Argus pipeline. It is the operation that takes the raw multi-source observation stream: N citations of the same identifier across N different upstream sources: and collapses it to a single canonical row in the `identifiers` table with appropriately accumulated provenance, corroboration boost, and superseded-row trail. Get dedup wrong and the database either over-counts (the same identifier appears N times under different `id` values) or under-counts (independent corroborating sources are silently merged without the +5 boost).

Dedup runs at promotion time and at re-ingest time when a new `raw_observations` row arrives whose normalized identifier matches an existing canonical `identifiers` row.

### §6.1 Dedup key

Two `raw_observations` records are duplicates if:

- Their `identifier_type` values are identical, AND their normalized `identifier` values are identical, OR
- One record's identifier is a strict subset of the other (e.g., a full MAC `aa:bb:cc:dd:ee:ff` within an OUI range `aa:bb:cc:00:00:00/24`).

**Normalization rules** (applied at ingest, before dedup):

- MAC addresses: lowercased, colon-separated, zero-padded to canonical octet form.
- OUI / OUI-28 / OUI-36 prefixes: lowercased, colon-separated, with explicit `/N` mask notation for sub-OUI allocations.
- SSIDs and BLE local names: case-sensitive (vendor casing is identifying); whitespace trimmed; non-printable bytes hex-escaped.
- Numeric registry IDs (FAA RID prefix, Bluetooth SIG company ID, IEEE OUI binary): canonical numeric or canonical hex form per identifier_type.
- UUIDs: lowercased, hyphen-separated, no `0x` prefix; canonical form per RFC 4122.

Normalization is identifier-type-specific and applied **at ingest** by the ingest worker, not at dedup time. The dedup pass assumes its inputs are already normalized and operates on byte-for-byte equality of normalized values.

### §6.2 Dedup mechanics: which row wins canonical

When two records match the dedup key, Argus selects the canonical record using the following ordered tiebreakers:

1. **Higher source-type band ceiling first.** A `primary_registry` row outranks a `crowdsourced` row regardless of timestamp. The intuition: the higher-band citation is the more authoritative attribution of identifier-to-meaning; the canonical row should bear that attribution. **In the rare `primary_registry`-vs-`regulatory` edge case** (e.g., an IEEE OUI directly cited in both the IEEE registry and an FCC test report citing the same OUI), the band-ceiling rule fires `regulatory`-wins per the ordered ceiling (95 > 85); the registry-of-record reading is NOT a canonical-attribution override. The rule is band-ceiling-strict; reader intuitions about "registry should be canonical" are addressed at the corroboration boost (§5.2) and the §5.6 ceiling rule, where `primary_registry`'s band-extension to 95 with cross-band corroboration applies.
2. **Higher per-row confidence within the same band.** A `crowdsourced` row at confidence 70 outranks a `crowdsourced` row at confidence 55.
3. **Earlier `first_seen` timestamp.** When source-type and confidence tie, the older row wins canonical (preserves Argus's evidence-history continuity).
4. **Lower `identifiers.id` (creation order).** Final tiebreaker for deterministic re-runs.

On dedup:

- Keep the canonical-winning row in `identifiers` with its original `id`; it stays at its current `source_type` and `device_category`.
- Append all source URLs and source excerpts from the superseded row's lineage into the canonical row's `notes` JSON under `corroboration_chain` (keyed by superseded row id, with each entry preserving `source_id` / `source_url` / `source_excerpt` / `raw_observation_id`).
- Mark the losing row's `superseded_by = <canonical.id>` and `superseded_at = <utc_now>`; the row stays in the `identifiers` table for audit-trail purposes but is filtered out of all exports and active-row queries via the `superseded_by IS NULL` predicate.
- Recompute the canonical row's confidence per §5.2 / §5.6: `confidence_canonical = min(99, min(lowest_band_ceiling, max(confidence_originals) + 5))`.

### §6.3 Independent-source-count vs raw-observation-count

The `+5` corroboration boost applies when the dedup pass detects two or more **independent** source citations: meaning two distinct `sources.id` values, each with its own `source_type`, contributed to the corroborated canonical row's lineage. Multiple `raw_observations` rows from the same `sources.id` are NOT independent corroboration; they count as a single source for the +5 calculation.

The `identifiers.independent_source_count` column tallies the distinct `sources.id` values feeding the canonical row's corroboration chain (initially 1; incremented at each dedup pass that adds a new `sources.id`). The promotion-cycle cut-off for non-`primary_registry` source-types requires `independent_source_count ≥ 3`; `primary_registry` waives the count cut-off per §5.3. The `+5` boost fires on the first new independent source (count 1 → 2); subsequent independent sources beyond the second do not compound the boost.

### §6.4 Superseded-row preservation discipline

Argus does NOT delete superseded rows. The `identifiers` table retains the full historical lineage under `superseded_by IS NOT NULL`, with every superseded row preserving its original `source_type`, `confidence`, `first_seen`, and `notes.source_excerpt`. The reasoning is auditability: a downstream consumer (or a future Argus operator validating a flagged false-positive) can trace a canonical row's full corroboration history without re-querying upstream sources. Exports filter on `superseded_by IS NULL` unconditionally: the operational scanner consumes the active set only.

### §6.5 The strict-subset case: MAC within OUI range

The strict-subset case (one identifier is a normalized prefix of the other) is the most subtle dedup discipline. Example: an OUI-24 row `aa:bb:cc:00:00:00/24` and a full MAC row `aa:bb:cc:dd:ee:ff`. The full MAC's first three octets match the OUI's prefix. These are NOT automatically merged at the canonical-row level:

- The full MAC row and the OUI-prefix row remain **separate canonical rows** in `identifiers`. They represent different observation granularities and carry independent provenance.
- The full MAC row inherits the OUI-prefix row's `manufacturer` / `device_category` attribution via the validator's prefix-lookup pass, preserved on the full-MAC row's `notes.prefix_attribution_source_id`.
- The dedup +5 corroboration boost does NOT fire on the prefix-relationship alone: bit-pattern containment is structural, not evidentiary. The boost requires two independent `sources.id` values each directly attesting the full identifier.
- When the full-MAC row promotes and the OUI-prefix row already exists, the full-MAC row's confidence is computed from its own direct provenance, capped by the §5.6 ceiling rule.

This discipline keeps the active set's row count honest: full-MAC observations and OUI-prefix attributions are counted separately rather than collapsing the full-MAC count into the OUI-prefix tally.

### §6.6 Cross-validation alias-aware-join discipline (CP23, 2026-05-17)

Cross-validation queries against `procurement_records` MUST use the `vendor_canonical_normalized` join key (added migration 0021 at CP23) OR an alias-aware JOIN against `manufacturers.canonical_name` and `manufacturers.aliases`. Direct equality on `vendor_canonical_name` misses legitimate matches because the column carries upstream USAspending verbatim recipient names with vendor-side inconsistency across awards.

**Algorithmic basis** (per `db/normalize_vendor.py::normalize_vendor_name`; canonical source for both the migration backfill and runtime cross-validation):

1. `LOWER()`
2. Strip ALL punctuation
3. Collapse runs of whitespace → single space
4. Strip leading/trailing whitespace
5. Repeatedly strip trailing whole-word suffix tokens (`inc`, `incorporated`, `corp`, `corporation`, `llc`, `l l c`, `ltd`, `limited`, `plc`, `co`, `company`, `lp`, `llp`, `gmbh`, `ag`, `sa`, `pty`, `bv`)
6. Re-strip whitespace
7. Empty result returns `''`

**Preferred query pattern** (cheapest at the 43k+ row scale; index-covered):

```sql
SELECT p.*
FROM procurement_records p
JOIN manufacturers m
  ON p.vendor_canonical_normalized = LOWER(m.canonical_name)
   OR m.aliases LIKE '%' || p.vendor_canonical_normalized || '%'
WHERE m.canonical_name = ?;
```

**`manufacturers.aliases` shape**: comma-separated TEXT string on the `manufacturers` table; there is NO separate `manufacturers_aliases` table. Append semantics: `aliases = CASE WHEN aliases IS NULL OR aliases = '' THEN ? ELSE aliases || ',' || ? END WHERE id = ?`. Lookup semantics: `WHERE aliases LIKE '%term%' OR LOWER(canonical_name) = LOWER(?)`. Schema-truth formalized at CP23.

**`agency_name` concatenation**: `procurement_records.agency_name` carries the upstream USAspending concatenation `"Awarding Agency / Awarding Sub Agency"`. Split on `" / "` for hierarchical use when an analytic needs the awarding-vs-sub-agency distinction (per CP23, cycle-3 §1 finding #5).

### §6.7 Short-vendor-name disambiguation discipline (CP23, 2026-05-17, text-pattern sources)

Short vendor names (≤6 chars or single-word) in text-pattern-matching sources without entity disambiguation produce false-positive STRONG matches against unrelated cases with overlapping vocabulary. Canonical case study: the **Berla collision**, 3 cases STRONG-matched for `Berla` against CourtListener returned `"Berla Kay Strong v. Thomas Wesley Strong"`, a family-court matter where "Berla" is a given name, NOT the digital-forensics vendor.

Future text-pattern-source runguides MUST bake disambiguation into §4 match scoring at extraction time, NOT punt to integration-time review. Disambiguation options (in declining preference):

1. **Co-occurrence filter**: require the matched query token to appear alongside another known vendor-specific token (product family name, industry term) within N words. Cheapest at extraction time; runs against the source's own returned snippet/description.
2. **Entity-type tagging**: if the source exposes party-role metadata (defendant vs plaintiff, corporate vs natural-person), filter to corporate-party-only matches. Source-dependent; CourtListener V4 exposes `party[]` at the docket level.
3. **Operator review of WEAK/STRONG candidates** for short vendor names (≤6 chars or single-word) before promotion: manual fallback when (1) and (2) are not available.

The discipline composes with §8.4 multi-purpose-vendor categorization restraint (PROJECT_BIBLE.md §8.4): short-name false positives are an **extraction-time** concern; multi-purpose-vendor categorization restraint is a **promotion-time** concern. Both gate against premature confidence-band assignment.

## §7. Provenance discipline

Provenance is the database. The phrase is from the canonical-bible's promotion-gate hard rule: *"Do not promote a record to the main table without provenance. Provenance is the database. Without it, we have a rumor."* The principle is load-bearing: Argus's value to a downstream scanner operator is not the identifier list (any vendor catalog has those) but the auditable evidence chain binding each identifier to its claimed attribution. A row whose provenance is broken: dead link, scrubbed excerpt, paraphrased citation: is not a low-quality row; it is not a row at all.

### §7.1 `raw_observations` is the source-of-truth

Every active `identifiers` row in Argus is anchored to one or more rows in `raw_observations`, each preserving the *original* source citation as it appeared at ingest time: `source_id`, `source_url`, `source_excerpt`, `extracted_at`, `extraction_method` (regex / structured-API / vendor-app-static-analysis / human-OSINT).

The `identifiers` table is *derived* from `raw_observations` via the dedup pass (§6) and the promotion pass. A row in `identifiers` can always be reconstructed from its `raw_observations` lineage; the inverse is not true. When provenance reconciliation surfaces a discrepancy (a canonical row's claimed source no longer matches the underlying `raw_observations` excerpt), the canonical row is treated as drifted and routed to the `conflicts` table for re-evaluation: `raw_observations` is the source of truth, not `identifiers`.

**Per-table source_excerpt CHECK constraint actuals** (CP23, 2026-05-17, DB-verified against `db/argus.db` post-migration 0020). The cycle-3 patch §1 finding #3 source_excerpt cap claims have been superseded by DB-verified actuals; the CP23 table below is the canonical reference:

- `identifiers.source_excerpt`: `CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)`. The cap is the live state post-0001 initial schema + the CP14 batch rebuilds (each rebuild preserved the 200-char ceiling).
- `procurement_records.source_excerpt`: `CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)`.
- `council_minutes_matters.source_excerpt`: `CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)` (verified at CP23; cycle-3 finding #3 had this as TBD-verify).
- `raw_observations.source_excerpt`: **NO CHECK constraint** (plain TEXT). App-level enforcement at 200 chars via the `db/sources/vendor_docs.py::raise_on_overflow` path; the column itself does not carry a length CHECK at the schema level. This is DB-truth at CP23; cycle-3 finding #3 had claimed ≤500.
- `behavioral_signatures`: **the `source_excerpt` column does not exist**. Provenance for behavioral signatures is captured via `source_id` + `source_file_relative` + `source_line` + `evidence_json` per the migration 0010 schema. This is DB-truth at CP23; cycle-3 finding #3 had this as TBD-verify.

Future runguide §-text MUST consult the CP23 BIBLE_AMENDMENTS.md cap table for the canonical per-table cap; the cycle-3 patch document is legacy schema-truth-as-of-2026-05-16-with-known-drift on this single sub-item.

### §7.2 `source_url` must be working at ingest time and preserved verbatim

Every `raw_observations` row must carry a `source_url` that:

- Was fetched and yielded a 200 OK at extraction time.
- Contains the verbatim text from which the identifier was extracted (re-fetching the URL must return content containing the `source_excerpt`, modulo upstream content-rotation; if the upstream rotates content, an archive snapshot URL is added as `source_url_archive`).
- Points DIRECTLY at the source: no aggregator URLs, no redirect chains, no shortened-URL services.

When a `source_url` is later confirmed dead (404 / domain expiration / paywall) at re-verification time, the original `source_url` is preserved verbatim and an archive snapshot URL (preferably Internet Archive `web.archive.org`) is added as `source_url_archive`. Dead-link rows are not deleted; their canonical attribution stays in `identifiers` with `last_verified` updated and the archive-snapshot URL serving as the working citation.

### §7.3 No-fabrication rule

Argus does not synthesize plausible identifiers. The hard rule: *"If a source doesn't yield concrete data, the answer is 'no records,' not 'plausible records.'"*

Concrete examples of what this rule rejects:

- A vendor's marketing page mentions a product family but does not enumerate per-model MAC OUIs. The output is "no MAC OUIs for this product family", NOT "plausible MAC OUIs inferred from vendor naming conventions."
- A regulatory filing lists a model number but does not include the firmware version. The output is `firmware_version = NULL`, NOT a plausible-firmware-version guess.
- A vendor app's binary contains a UUID pattern that looks BLE-service-shaped but is not used in a discovery context. The output is "candidate, route to manual review", NOT "promoted to `identifiers` with `manufacturer_app` source_type."

The validator's `conflicts` table absorbs the borderline cases: any extraction step that produces a value the validator cannot cleanly attribute is routed to `conflicts` for human disposition.

### §7.4 Third-party-citation-lineage boundary

Argus's evidence discipline composes upward: a row's confidence ceiling is gated by its **direct** provenance, not by upstream ancestry. *Rows whose direct provenance is third-party stay capped at their current band's ceiling regardless of upstream-registry ancestry.*

Operational consequence: a community OSINT GitHub repository citing the IEEE OUI registry is NOT a `primary_registry` source for the `identifiers` rows promoted from it. The rows' direct provenance is the GitHub repository (a community curation = `crowdsourced` or `inferred`); the IEEE registry is upstream ancestry. To establish a `primary_registry` row for the same OUI, a new `raw_observations` row citing IEEE's MA-L assignment record URL directly is required.

The boundary is what keeps confidence honest at scale. Without it, every row citing an aggregator that cites a registry would inflate to the registry's band: the band would lose its discriminating power.

### §7.5 No PII

Argus is about *equipment*, not *people*. *"This database is about equipment, not people. If a source mentions an officer's name, badge, home address: strip it. We identify categories of devices, not individuals."*

Operational discipline:

- `source_excerpt` is sanitized at ingest: names, badge numbers, home addresses, license-plate numbers, and individual-identifying personal references are redacted (replaced with `[REDACTED-PII]` token) before the excerpt lands in `raw_observations`.
- Identifier columns themselves (`identifier`, `manufacturer`, `model`, `device_category`, `geographic_scope`) are equipment-categorical by design and cannot carry PII per the schema constraints.
- When a procurement record names an individual (purchasing officer, contracting officer), only the agency-level identifier is retained; the individual's name is dropped at ingest.

The export shape never carries personal references. Downstream consumers can correlate identifier-to-deployment-locality at the agency level (e.g., "this OUI is deployed by Houston PD"), never at the individual-officer level.

### §7.6 Amendment-log discipline

Every in-place change to `PROJECT_BIBLE.md` or to a sub-agent-level rule carries a corresponding entry in `BIBLE_AMENDMENTS.md`. The git diff is the source of truth, but the amendment log is the human-readable trail. *"An undocumented amendment is a process violation regardless of whether the edit itself is correct."*

Operational mechanics:

- Every CP-class commit (Correction Pass) lands as a coordinated commit touching `PROJECT_BIBLE.md` + `BIBLE_AMENDMENTS.md` + any schema migration / verify-wrapper / sibling artifact. The amendment-log entry cross-references the migration slot, the commit SHA, the originating issue identifier, and the verbatim §-text diff.
- Every SAR-class (Sub-Agent Rule) and every CP carries a §-citation back to the bible row it modifies; readers can trace any rule's origin via the amendment log.
- The `BIBLE_AMENDMENTS.md` log is append-only in practice (entries are never rewritten); historical entries preserve the project's evidentiary trail even as the live bible text evolves.

The discipline composes with §7.1 (`raw_observations` as source-of-truth): the bible amendment log is to the bible what `raw_observations` is to `identifiers`, the immutable evidence record from which the live document is derived.

### §7.7 `sources.notes` is JSON; controlled-vocabulary conventions (CP23 + CP26, 2026-05-17)

The `sources.notes` column holds free-form TEXT that the runguide-validator contract treats as JSON. Per the cycle-1 wide-net finding #1 formalized at CP23 §11, **license metadata lives inside `notes_json.license`, not as a top-level column on `sources`**; the canonical sources-row JSON contract carries top-level keys `name`, `url`, `source_type`, `tier`, `notes_json`, `last_fetched_at`, `last_status`. The translator script `extraction_outputs/_tooling/translate_license_to_notes.py` (cycle-1 patch §2) covers retroactive translation of any already-staged outputs authored before CP23.

**`notes_json.access_mode` convention (CP23, 2026-05-17).** Controlled vocabulary for how a source is fetched at extraction time. Initial set (open for future extension; first-class-column promotion deferred until value-set stabilizes per the cycle-3 addendum §6 default recommendation):

- `automated_api`: source queried via documented API; end-to-end automated
- `automated_html_parse`: source queried via automated HTML scraping; no anti-bot wall
- `automated_with_auth`: automated, but requires API key / token / user-agent
- `mixed_automated_manual`: some candidates automated, some operator-manual (e.g., the intl_registries cycle-2 mix)
- `operator_manual_only`: all access is operator-manual via browser; automation structurally blocked (CAPTCHA, anti-bot wall, session gates)

Discipline guarantees (uniform across access modes): per-row provenance discipline + promotion-gate confidence band are IDENTICAL regardless of `access_mode`. The field is informational/operational only, NOT a confidence modifier. Operator-manual findings carry `notes.fetch_mechanism="operator_manual_browser"` per-row (row-level, complementing the source-level `access_mode`). Sources admitted prior to CP23 do NOT require backfill: absent-`access_mode` is equivalent to `automated_api` per backward-compat.

**`notes_json.cycle_completion_state` convention (CP26, 2026-05-17).** Controlled vocabulary for whether a source admission landed mid-cycle vs at canonical completion. The field is absent for the canonical-complete state (the default backward-compat reading); non-absent values are explicit incomplete-state flags:

- (field absent): source is complete; canonical state (default backward-compat reading)
- `partial_pre_day1`: source admission landed before its first full data sweep completed; explicit incomplete-state flag pending next-cycle dispatch
- `partial_pacing_in_flight`: source is mid-multi-day pacing run; additional data expected in subsequent cycles
- `partial_pacing_exhausted`: source's multi-day pacing terminated short of completion; deferred to future cycle

Composition with `access_mode`: orthogonal: `cycle_completion_state` is a temporal state, `access_mode` is a mechanism state. The first consumer (CP26 §3 reference): the SAM.gov sid=50 admission carries `access_mode="automated_api"` + `cycle_completion_state="partial_pre_day1"` per the cycle-5 day-0 rate-ceiling halt.

**Companion fields REQUIRED when `cycle_completion_state` is non-absent** (per CP26 §9):

- `next_cycle_dispatch_scheduled_for_utc`: ISO-8601 UTC timestamp of the next planned dispatch
- `next_cycle_dispatch_runguide_path`: relative path to the dispatch artifact
- `partial_yield_metrics_at_admission`: JSON snapshot of yield-at-admission for post-completion audit comparison

First-class column promotion deferred to a future CP once the `cycle_completion_state` value-set stabilizes (per CP23 `access_mode` precedent: deferred until at least 2 distinct sources have exercised non-absent values).

**`notes_json.candidate_findings_for_future_cp_or_sar[]` convention (CP25 §3 + CP26 §8 composition).** For n<3 held FP-classes: false-positive classes surfaced at validator-time but below the n=3 threshold for dedicated §11 sub-rule codification: the per-source `notes.candidate_findings_for_future_cp_or_sar[]` array carries the held instances pending threshold-met carry-forward. The convention preserves the discipline-evolution audit-trail across CPs without prematurely codifying a sub-rule that lacks recurrence evidence. CP25 §3 originating evidence (cumulative n=2) was held in this array until CP26 §8 codification at n=4. The array is the canonical placement for between-codification-cycles FP-class staging.

## §8. Build process and agent-orchestrated disclosure

**Argus v1.0.0 was built using a multi-agent orchestration platform (Paperclip)** where specialist agents coordinate over an issue tracker and a single canonical "project bible" document that defines schema, source-type bands, confidence rules, and per-phase exit criteria. Commit metadata reflects this orchestration: Paperclip-platform agents and the human operator appear in commit history + CREDITS attribution per the project's authorship discipline.

The build process was **bible-as-contract**: amendments to the canonical bible (in-place edits to its §-text) and additions to the sub-agent rule set (operational rules that bind agents without amending bible §-text) are operator-approved before implementation. Every promotion of a candidate identifier to the live database is gated on the bible's promotion-rule section at the version current at promotion-time. This document distills the methodology to public-OSS prose; the bible itself remains an internal orchestration artifact and is not part of v1.0.0 release.

**Reproducibility:** the migrations and source-loaders in this repo deterministically reproduce the live database from upstream public sources; the agent ensemble is not required at runtime. Re-running the build today against current upstream snapshots will yield drift from the v1.0.0-tagged DB because upstream sources change. Tagged DB releases (downloadable from GitHub Releases) are the canonical artifact for downstream consumers.

---

## Canonical sources

Descriptive references used in this document map to canonical bible
anchors as follows. The canonical bible (`PROJECT_BIBLE.md` and the
amendment ledger `BIBLE_AMENDMENTS.md`) holds the authoritative
specification; this document is the public-facing methodology
distillation.

| Descriptive reference (as used in this doc) | Canonical source |
|---|---|
| promotion-gate hard rule / provenance gate ("provenance is the database") | `PROJECT_BIBLE.md` §11 #7 |
| confidence-ceiling hard rule (lowest-band-wins) | `PROJECT_BIBLE.md` §11 #8 |
| third-party-citation-lineage boundary | `PROJECT_BIBLE.md` §11 #8 |
| no-PII discipline | `PROJECT_BIBLE.md` §11 #3 |
| amendment-log discipline | `PROJECT_BIBLE.md` §11 #11 |
| Feist facts-only / canonical sentinel-key | `PROJECT_BIBLE.md` §11 #16 |
| bible's promotion-rule section (the hard-rule set) | `PROJECT_BIBLE.md` §11 |
| framework-string sub-rule (extraction-time false-positive discipline) | `BIBLE_AMENDMENTS.md` SAR-11 |

---

## §11. Vendor cloud-infrastructure hostname corpus extraction (Wave I)

Added in v1.4.0. This section documents the 4-wave Wave I/I.5/I.6/I.7 methodology that produced the vendor cloud-infrastructure hostname corpus (12,590 cumulative unique hostnames → 12,239 net-new canonical identifiers).

### §11.1: Extraction source-classes

The Wave I cumulative extraction operated across 8 source-classes per the Wave I runguide (`~/argus-internal/wave_i_pre_v1/runguide.md`):

- **B (crt.sh aggregator)**: RFC 6962 public CT log observation; vendor-apex subdomain queries via `crt.sh/?q=%25.<vendor_apex>`. 11,551 hostnames in cumulative output; 92% of corpus by volume.
- **A (binary static analysis)**: extraction from vendor mobile + desktop binaries (Wave G + Wave H wrapper methodology pipeline). 587 hostnames cumulative (post Class-A 481 extraction-time FP-drop).
- **I_github_readme + I_github_source**: vendor GitHub organization README + source file content (Wave I.6 sub-pass 8 + Wave I.7 sub-pass 14); ~24% retention rate estimated; manual top-50 calibration carry-forward.
- **F (subdomain enumeration)**: passive DNS + subdomain wordlist probes against vendor-apex domains.
- **D + D_bucket_enum_deep**: S3-class public bucket misconfiguration probes; SAR-13.5 bucket-attribution gate binds per-row promotion.
- **C (cloud doc URL space)**: cloud-document URL-pattern enumeration (CP28 `vendor_document_uuid_cloud_reference` sibling methodology).
- **A_bucket_payload_firmware**: payload extraction from confirmed vendor public buckets (Honeywell firmware OTA cert chain marquee).
- **J (public package registries)**: npm + PyPI + RubyGems package metadata for vendor-published package surfaces.
- **K (Wayback CDX)**: Internet Archive temporal hostname observation for deprecated-hostname enrichment + carry-forward.
- **G (RDAP RIRs)**: Regional Internet Registry ASN/IP-block enumeration; halted in Wave I class G with `url_pattern_issue` carry-forward (0 findings cumulative).

### §11.2: CP29 confidence-band ladder

Per BIBLE_AMENDMENTS.md CP29 §2:

- **`vendor_controlled_hostname`**: 75-90 single-source default / 85-95 cross-source (CP24 independence) / 95-99 firmware-embedded cert ceiling
- **`vendor_cloud_endpoint_url`**: 80-90 single-source / 90-97 binary + CT log + sitemap multi-source
- **`vendor_controlled_hostname_deprecated`**: 80-87 NXDOMAIN-verified default

### §11.3: Phase 2 FP scrub disposition

The dispatch §2 FP scrub applies 7 disambig classes (CDN / analytics / update-framework / license-auth / standards-IANA / OS-SDK-vendor / installer-wrapper) + SAR-13.5 bucket attribution gate + §4.2 cross-vendor demotion + GitHub-sourced calibration. v1.4.0 survivor rate: 97.21% (above 50% PROCEED-but-FLAG gate). The high survivor rate reflects Wave I's extraction-time pre-scrub (Class B 5% calibration FP rate; Class A 481 fp_dropped at extraction). Carry-forward: manual top-50 GitHub-sourced calibration review post-v1.4.0 to anchor empirical FP rate.

### §11.4: Marquee anchor: `hppki.honeywell.com`

The strongest possible attribution chain in the framework: promoted at confidence=99 (firmware-cert ceiling) via 4-source independent corroboration:

1. **Firmware OTA signing cert** (sha256 `60a8cf8feeb33926366776b395d6c8d9334bd8b42038b85563622ce0a1d0745b`) recovered from CT40 Android firmware `META-INF/com/android/otacert`; issuer DN `C=US, O=Honeywell International Inc., OU=ACS, CN=Honeywell CodeSign RSA CA`
2. **crt.sh CT log** attestation
3. **Class A binary** extraction
4. **A_bucket_payload_firmware** Honeywell-firmware-bucket payload

Per CP24 cross-source independence, these 4 source-classes are genuinely independent (different providers; different methodologies). Per CP29 §2's firmware-cert ceiling, the 95-99 ladder applies.

### §11.5: SAR-13 + SAR-13.5 sibling codification

Wave I integration codified two SAR-class disciplines as bible-amendment siblings:

- **SAR-13**: runguide-schema-fabrication discipline (PRAGMA-verify column names + types + CHECK enums against live `~/argus/db/argus.db` prior to any SQL drafting).
- **SAR-13.5**: bucket attribution discipline (content-based attribution gate before promotion; three-state classification confirmed / rejected_slug_collision / ambiguous_operator_review_required; 57% misattribution observed in slug-discovery without content gate).

See BIBLE_AMENDMENTS.md SAR-13 + SAR-13.5 entries for full discipline-evolution narrative and empirical anchors.

## §12: Wave I.9 → I.14c reconciliation cycle (v1.4.1 narrative)

The v1.4.1 ship integrates the **Wave I.9 → I.14c reconciliation cycle**, seven sub-waves (I.9 + I.11 + I.12 + I.13-carry-forward + I.14a + I.14b + I.14c) of academic-corpus, community-research, certificate-transparency, and hard-ID-falsification reconciliation work that closed evidence loops left open by Wave I/I.5/I.6/I.7 v1.4.0 ship. The cycle methodology pattern:

1. **Academic + community repo retroactive promotion (Wave I.9 / I.11 / I.12)**: surface unpromoted academic-paper and community-repo evidence that had been documented during Wave I.5-I.7 surveys but not promoted because the v1.4.0 ship cut closed the cycle before validator review fired. Stage 1 walks the surveys, re-fires §7.4 validation against each unpromoted candidate, and either promotes (when source-band ceiling + §8.2/§8.3 composition allow) or files a documented-absence under the existing absence-investigation convention.
2. **crt.sh Distinguished-Name extraction**: re-mine the existing crt.sh CT-log corpus (sid 54 admission at v1.4.0; 11,551 attestation rows) for Subject DN O fields not surfaced by the v1.4.0 first-pass Common-Name-only extraction. The DN-O pass surfaces additional vendor-name aliases (e.g., `Honeywell International Inc.` recovered from firmware-OTA cert chain at MAC-195 ACS division enrichment).
3. **Wave I.13 hard-ID falsification empirical anchors**: load-bearing empirical-evidence cohort for the CP30 reservation (`vendor_asn_prefix` + `vendor_controlled_ip`). Wave I.13 fired the falsification probes; both candidate identifier_type classes returned 0 empirical observations. CP30 reservation footnote held verbatim through CP31 + CP32 (both skipped CP30 numerically to preserve the reservation slot).
4. **Phase 2.5 hostname-corpus FP audit** ([MAC-188](/MAC/issues/MAC-188)): cumulative third-party-OSS / SDK-root FP-class demote sweep against the v1.4.0 hostname corpus (12,239 promoted rows). 262 rows demoted via the §8.3 supersession path across 9 manufacturers. The DJI cohort dropped from 410 → 242 rows post-cleanup; the demoted rows preserve provenance in `notes.supersession_audit[]` per the CP25 reversal-array discipline.

The reconciliation cycle composes with the §5 confidence model and §6 dedup logic unchanged: the cycle is a **provenance-density** cycle (filling out evidence chains that were under-attested at v1.4.0) rather than a confidence-uplift cycle. Net active identifier delta: +172 rows. The cycle's discipline-output is the v1.4.1 CP31 + CP32 bible-amendment bundle codifying the multi-arm hub-and-spoke schema + the ten-section CP32 narrative/discipline bundle.

## §13: SAR-15.5 first activation (v1.4.1 narrative)

The Stage 1 close-out of the v1.4.1 cycle was the first activation of the **SAR-15.5 independent close-out audit discipline** (post-ship codified at v1.4.0; first applied at v1.4.1). SAR-15.5 fires automatically on any ship cycle that crosses ≥10 phases / ≥10k row promotions / ≥3 new sources / ≥1 new migration, empirically, "large-ship" cycles where the Validator-role main pass has historically had a chance to miss something the operator would catch on a second-pass review.

The first activation surfaced **the Honeywell-in-lexicon miss**: the main Phase 6 enrichment script omitted `honeywell` from its vendor-key-to-canonical mapping table, so the firmware-derived legal-entity string `Honeywell International Inc.` had not been appended to the canonical Honeywell row (id=211, which exists per the v1.0.0 baseline). SAR-15.5 surfaced the miss; a post-ship corrective sub-pass landed the missing alias under the same `sweep_event_id` audit-trail discipline as the parent sweep. Net Stage 1 SAR-15.5 verdict: **PASS** (verdict was conditioned on the corrective sub-pass landing pre-tag; corrective sub-pass landed pre-tag; PASS issued).

SAR-15.5 is the discipline framework's first dedicated "Validator-role-checks-Validator-role" audit pattern. Codified anchor: BIBLE_AMENDMENTS.md SAR-15.5 entry (post-ship corrective codification on the v1.4.0 comment thread 2026-05-20).

## §13.5: SAR-16 / SAR-17 / SAR-18 cohort-disambiguation codifications (v1.5.0 narrative)

The v1.5.0 lexicon-expansion wave (dispatch [MAC-232](/MAC/issues/MAC-232); Two-Session Parallel Dispatch) anchored three new SAR codifications addressing cohort-disambiguation discipline:

- **SAR-16**: Alias-length-floor discipline** (BIBLE_AMENDMENTS.md line 4682; formal codification): driving case lockheed-LM n=134 substring collisions in the Session 1 military/federal extraction wave. Short / ambiguous canonical aliases produce false-positive STRONG matches against unrelated vendor surfaces. **Discipline rule:** alias-length-floor, aliases below the empirical floor MUST be paired with disambiguation predicates at extraction time, NOT punted to integration-time review. SAR-16 extends SAR-15's per-vendor probe-scope discipline (v1.4.0) and the §6.7 short-vendor-name disambiguation rule (CP23) to the alias-length axis. Composes with CP25 §3 typed-enrichment (`product_family_codenames`).
- **SAR-17**: No-generic-product-aliases discipline** (BIBLE_AMENDMENTS.md line 4701; formal codification): driving case mydefence-EAGLE n=41 substring collisions. Generic product-family aliases (e.g., "EAGLE") produce mass false-positive hits across unrelated vendor surfaces using the same English word. **Discipline rule:** no-generic-product-aliases, product-family codenames matching common-English-word patterns MUST be promoted to typed`notes.product_family_codenames[]` enrichment (CP25 §3) and DEMOTED from the `manufacturers.aliases` comma-separated string at admission time. SAR-17 is the SAR-16 sibling on the semantic-content axis (vs SAR-16's length-axis).
- **SAR-18**: Classifier-Predicate Parity Discipline** (BIBLE_AMENDMENTS.md line 4752; oversized_mac_range case study): driving case Step 9 halt at id=9404 Eagle Eye Networks `size=256` (predicate mismatch between the export-side `_classify_row` and the coverage-matrix-side `_classify_row`**: coverage_matrix.py classified the row at one tier; export_lynceus.py rejected the same row at a different tier). **Discipline rule:** coverage_matrix.py + export_lynceus.py classifiers MUST share runtime predicates. Future `_classify_row` rule additions require dual-table parity check at PR time. SAR-18 extends CP21's cumulative-full-enum sweep spirit (CHECK constraint parity across migrations) to runtime classifier predicates: both are "implicit contract held in two places that must stay in sync." CP34 §4.4 candidate (`mac_range expansion-ceiling-boundary disposition`) narrowed by SAR-18; revisit when Lynceus v0.4+ ships its expansion strategy.

The three SARs compose: SAR-15 (per-vendor probe-scope, v1.4.0) → SAR-16 (alias-length-floor, v1.5.0) → SAR-17 (no-generic-product-aliases, v1.5.0) form the cohort-disambiguation discipline trio at the extraction-time layer; SAR-18 (classifier-predicate parity) handles the export-time / coverage-matrix-time runtime-predicate sync layer. All three are codified in BIBLE_AMENDMENTS.md alongside CP33 §6 (v1.5.0 Stage 1 Step 7 disambig + FP-class triage).

## §14: `Na_` sub-slot migration convention (CP32 §1, first application at v1.4.1)

Mig-0026a (`db/migrations/0026a_phase10_vendor_apk_sources_admission.sql`) is the framework's first application of the **`Na_` sub-slot migration convention** codified inline at CP32 §1 (renamed from `0026_phase10_vendor_apk_sources_admission.sql` at commit `c1ec6a5`):

> **Data-only addendum migrations sharing a numeric slot with a schema-mutating migration use a sub-letter suffix (`Na_…`) and apply after the main `N_` slot (lexical: `_` < `a`).**

The convention frees the `0026_` slot for the schema-mutating CP32 §1 migration without renumbering downstream cycles. Filename↔schema_version 1:1 holds for schema-mutating migrations (`N_…`); data-only addenda live alongside via `Na_/Nb_/…` and do NOT register a `schema_version` ledger row.

Pre-CP32-§1, the framework's filename convention required strict numeric-monotonic ordering with no sub-slots. Mig-0026a demonstrates that a data-only addendum sharing a numeric slot is admissible without breaking the convention: it cannot conflict with the schema-mutating migration at the same numeric slot because lexically `0026_…` < `0026a_…`, and the migration runner applies in lexical order. Future data-only addenda (Nb_, Nc_, …) compose the same way.

No retroactive sweep of prior data-only entries is implied: the convention applies from CP32 onward; the v1.4.1 ship is the precedent-setting application.

## §15: §7.5 + §11 #3 export-time PII generator post-condition guard (CP32 §10, v1.4.1)

CP32 §10 codified the **export-time PII generator post-condition guard pattern** as a framework-level discipline rule. The pattern applies to every Lynceus-export emission call site:

```python
# canonical template per CP32 §10
def _emit_export(path: Path, rows: list[dict]) -> None:
    write_export(path, rows)        # row-classification gate already filtered PII
    _assert_no_email_pii(path)      # post-condition guard re-reads the file and Halts on regex match
```

`_assert_no_email_pii(path)` re-reads the written file from disk, applies the regex predicate `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b`, and raises `Halt` (not return-false) if any match survives. The guard is defense-in-depth: it catches BOTH (a) classification-gate bugs (a stale `_classify_row` predicate would leak PII at the row-emission layer if the guard didn't fire); and (b) new-code-path bypasses (a custom export script that bypasses the gate would still be caught at write-time).

**Forward-looking sub-rule (CP32 §10):** any §11 hard-rule that constrains export content shape SHOULD have a paired `_assert_no_<rule>_<violation>(path)` post-condition guard at every emission call site. The pattern lives at `db/validation/export_lynceus.py` + `db/validation/export_behavioral_signatures.py` (7 live call sites at v1.4.1; commit `214f20f`); it composes with the existing row-classification gate per a defense-in-depth pattern.

**Empirical anchor:** `argus_export.csv` regex-scan returns **0 email-shape matches** at v1.4.1 ship: the guard is active and clean.

**Companion §11 #3 PII discipline composition:** [MAC-217](/MAC/issues/MAC-217) Track B demoted 4 Jacobs `*.escg.jacobs.com` rows during the §8.2 PII-strip when cert-subject personal email PII was discovered. The 4 rows are now `superseded_by = id` (self-loop) per the CP32 §9 tri-state semantic: the "withdrawn-without-successor" semantic, distinct from canonical-merge supersession. The PII row is REMOVED from any active-set query (`WHERE superseded_by IS NULL` excludes it) AND the row's self-loop signals "no successor exists" for forensic-grade audit-trail purposes. The defense composes: §11 #3 demoted the rows, CP32 §9 codified the self-loop semantic, CP32 §10 added the export-time post-condition guard.

## §16: v1.6.0 → v1.6.2 layer (CP35 → CP38 + SAR-19 DRAFT)

The post-v1.5.0 layer added four CP amendments and one DRAFT SAR. Anchored at bible HEAD `def7b95`; cite-pasted bible-line references are §-line markers, not file paths.

- **CP35**: §4.4 Lynceus mapping for `network_discovery_protocol_pattern` (mig-0028 / CP34 Wave G/H v1 admission) ratified at option (b) DROP. Codified at `BIBLE_AMENDMENTS.md` line 4836+. The DROP disposition routes `network_discovery_protocol_pattern` rows to a Lynceus v0.3 scanner-support drop bucket (`NDPP_pending_lynceus_v0_3_scanner_support` in the `_meta.dropped_in_export` reconciliation) pending a v0.4+ MAP option uplift; the rows persist in the canonical DB with full provenance.
- **CP36**: `identifiers.source_type` CHECK enum parity with `sources.source_type` (mig-0029) + 116-row J-5 (CourtListener RECAP, sid=48) `source_type='foia'` → `source_type='judicial_filing'` proxy relabel. Codified at `BIBLE_AMENDMENTS.md` line 5088+. The CP-slot disambiguation (CP36 not CP35) is recorded in the amendment header; the known ledger-vs-file CP offset (schema_version row 29 stamped `cp35` while the on-disk migration FILE is `0029_cp36_*`) is benign and tracked at `DATA_DICTIONARY.md` §4.13.
- **CP37**: `device_category` CHECK enum +1 `network_surveillance` on both `identifiers` and `behavioral_signatures` host tables (mig-0030 / Wave K cohort 3 admission). Codified at `BIBLE_AMENDMENTS.md` line 5235+. The new value is the canonical lawful-intercept / monitoring-center / mediation / geolocation surveillance class (Pen-Link, SS8 Networks, Cognyte, Utimaco LIMS, Polaris Wireless, Trovicor); `hacking_tool` stays reserved for offensive-exploitation vendors (NSO / Cytrox / etc.). v1.6.2 ship-state: 17-value `device_category` enum (16 populated; `network_surveillance` admitted as a PROMOTING category per §11 #13, excluded-when-unknown does NOT apply).
- **CP38**: Step-2.3 codified: crowdsourced-detection-app `ssid_pattern`s default to `inferred/50` (FlockYou full-enum sweep, MAC-274 dispatch close at commit `8a89816`). Codified at `BIBLE_AMENDMENTS.md` line 5278+. **Data-only amendment, no `schema_version` bump** (`schema_version` stays at 30; the highest CP token referenced at bible HEAD = CP38 but the highest schema-mutating CP = CP37). The 19 FlockYou `ssid_pattern` rows demoted to `inferred/50` per §11 #8 ceiling-rule + §4.4 Lynceus-export NDPP-pending sibling-discipline (`ssid_pattern` excluded from both Lynceus JSON exports per §4.4 NDPP-style ladder, zero export-membership impact for the demotes).
- **SAR-19 (DRAFT)**: Dispatch-time pre-authorized DML requires corpus-wide diagnostic predicate (DBArchitect surface). Codified-as-DRAFT at `BIBLE_AMENDMENTS.md` line 4925+; the header carries the explicit notation "Bible HEAD `PROJECT_BIBLE.md` NOT amended by this entry"; SAR-19 has NOT been ratified into bible §-text. The SAR ratified-cap is SAR-18. Future dispatches MUST cite SAR-18 as the SAR roster anchor; SAR-19 citations are draft-only and gate on the next CP-cycle ratification trigger.

**Post-v1.5.0 strip work** ([MAC-291](/MAC/issues/MAC-291); commit `def7b95`): the v1.6.2 → HEAD increment removed 36 Wave G/H v1 CCTV placeholder rows via the §11 #1 strip discipline (15 OUI `00:00:00` + 2 OUI `01:01:01` + 1 OUI `ff:ff:ff` + 3 NDPP `224.0.0.251` + 2 NDPP `1900` + 1 NDPP `5353` + 12 NDPP `8000`). The 36 rows are now `superseded_by = id` (self-loop / withdrawn-without-successor per CP32 §9); active count dropped 41,544 → 41,508 in lockstep. The strip was a §11 #1 quality discipline (placeholder values that look identifier-shaped but are not concrete device identifiers, multicast addresses, all-zero/all-one OUI sentinels, port-number-shaped strings); no §8.2 confidence drift, no provenance breakage.

**§11 envelope count at HEAD:** the §11 hard-rule list at `PROJECT_BIBLE.md` lines 1008-1049 enumerates **19 numbered items** (1: no fabrication; 2: no non-public data; 3: no PII; 4: no detection logic; 5: no active-attack tooling; 6: ToS / robots; 7: provenance-or-no-promotion; 8: no confidence drift; 9: no skip checkpoints; 10: no OUI-level categorization for multi-purpose vendors; 11: amendment-log discipline; 12: operator-stack self-exclude; 13: no `device_category='unknown'` export to Lynceus; 14: no procurement-only export to Lynceus; 15: no decompiled vendor app source in git index; 16: public-but-unlicensed facts-only promotion; 17: direct-admission carve-out + JSON-validity-invariant applicability scope; 18: dispatch plan-input sandbox-absence HALT-fast-path default; 19: §11 #3 export-time generator post-condition guard pattern). Items 18 and 19 were folded in at CP32 (§7 and §10 respectively). Future docs citing the §11 envelope MUST anchor to 19 items at v1.6.2 HEAD.
