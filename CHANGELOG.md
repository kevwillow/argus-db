# Changelog

All notable changes to Argus are documented in this file. The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project does not yet adopt semantic-versioning for the dataset shape itself — see "Schema versioning" below for the migration-ledger discipline.

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
