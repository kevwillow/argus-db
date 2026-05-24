# Argus — Upstream Attribution and Credits

Argus integrates data derived from **73 upstream sources** (canonical registries, procurement data, public-records databases, academic research, community-research repositories, vendor-published documentation, international corporate registries, US state Secretary-of-State registries, judicial filings, federal disclosure / entity-registration sources, FCC Equipment Authorization aggregators and primary surfaces, the Wave H desktop-axis vendor-application static-analysis methodology source, the Wave I/I.5/I.6/I.7 13-source vendor cloud-infrastructure hostname corpus admission, 5 vendor companion APK sources [Hikvision Hik-Connect, Dahua DMSS, Motorola Solutions WAVE PTT, Parrot FreeFlight 6, DJI Industry Pilot] admitted in v1.4.1 via [MAC-204](/MAC/issues/MAC-204) Phase 10b admit-then-rebind disposition under the sid=13 envelope, and — new in **v1.5.0** — 2 additional sources from the lexicon-expansion wave [GitHub Code Search REST API sid=72; adsb.lol v2 FAA-registry-derived aircraft tracking sid=73]) plus a canonical lexicon of **92 surveillance-technology vendor entries** (51 hub-visible canonicals from v1.4.1 + 1 multi-arm `hidden_arm` row — Parrot Automotive id=222 — + 39 net-new cohort_prediction admissions from the v1.5.0 lexicon-expansion wave + 1 new multi-arm `hidden_arm` row — Pelco id=254 under Motorola Solutions id=3 — = **92 total** in the v1.5.0 lexicon). This document attributes every upstream contribution, names the integration shape, and records license-carry-forward obligations downstream consumers must honor.

For the binding license terms, see [LICENSE](LICENSE) (AGPL-3.0-or-later — code), [LICENSE-DATA](LICENSE-DATA) (ODbL-1.0 — database), and [LICENSE-DOCS](LICENSE-DOCS) (CC-BY-SA-4.0 — documentation). The LICENSE-DATA §2.1 per-source license-posture taxonomy is the structural anchor for the source enumerations below.

---

## How to read this document

CREDITS.md has two halves: the per-source attribution roster (§1 through §8 below) and the per-vendor canonical lexicon (the manufacturer cohort sections at the bottom). New readers should skim this preamble first, then jump to whichever section answers their question.

**The per-source attribution roster** names every upstream dataset Argus integrates and records the legal posture for downstream consumers. Sources are organized into tiers by `source_type` band: `primary_registry` (canonical allocation registries like IEEE/FCC/FAA), `regulatory` (regulatory disclosure surfaces), `academic` (peer-reviewed research), `crowdsourced` (community researcher repositories), `manufacturer_app` and `manufacturer_doc` (vendor-published documentation and APKs), `judicial_filing` / `disclosure_filing` / `procurement_disclosure` (judicial records, SEC EDGAR, SAM.gov, and similar), and `inferred` (cohort-prediction admissions where attestation is pending). Per-source license posture controls how downstream consumers can redistribute data derived from that source.

**The per-vendor canonical lexicon** lists all 92 surveillance-technology manufacturers Argus tracks at v1.5.0. Vendors are admitted to the canonical state when at least one structural anchor (an FCC grantee record, an IEEE OUI allocation, an SEC Exhibit 21 subsidiary disclosure, a verified academic identification, etc.) attests to their existence and surveillance-equipment scope. Vendors without an attestable structural anchor are not admitted — Argus has no fabricated rows.

**A few details worth knowing:**

- **Multi-purpose carveouts (§11 #10).** Some vendors make both surveillance equipment and unrelated commercial products at scale (Northrop Grumman, Lockheed Martin, Trimble, Bosch Security Systems, etc.). These are admitted at `device_category='unknown'` rather than forced into a single surveillance category they don't cleanly map to. Their identifier rows are excluded from the high-confidence Lynceus export by design — pointing a runtime scanner at a Lockheed OUI would generate vast false-positive volume.

- **Hub-and-spoke arm rows (CP31 hub-and-spoke schema).** When a vendor operates a wholly-owned subsidiary with a distinct surveillance product line (e.g., Pelco under Motorola Solutions, Parrot Automotive under Parrot), the subsidiary is admitted as an arm row pointing back to the parent via `parent_manufacturer_id`. Default queries against `manufacturers` filter `WHERE query_default='visible'` and do NOT surface arm rows; explicit audit queries opt in. At v1.5.0 there are 2 arm rows: Parrot Automotive (id=222) under Parrot (id=25), and Pelco (id=254) under Motorola Solutions (id=3). Future arm splits ship only on concrete identifier evidence — Cisco/Meraki, Harris RF vs Harris Aerial, Honeywell ACS division, Avigilon, and WatchGuard remain backlogged for evidence-driven splits.

- **Per-cohort headline counts at v1.5.0 admission:** counter-UAS (11 vendors + 2 carveouts under `unknown`); persistent surveillance (4 vendors + 2 carveouts); through-wall radar (3 vendors; FCC §15.519 UWB-LE-only regulatory carveout); CCTV/IP camera (13 vendors including retroactive recategorization of 7 prior face_recog/multi-purpose vendors and the Pelco arm row); electronic monitoring / ankle-monitor (5 vendors; Geo Group arm split queued for v1.5.x); fleet telematics (6 vendors + 1 multi-purpose carveout under Trimble); IMSI catcher (1 new addition — Rohde & Schwarz — joining the existing 6-vendor roster); IMSI-catcher behavioral signatures (201 patterns, integrated from the Marlin academic foundation and adjacent community research).

- **For the formal v1.5.0 admission record**, see [`docs/engineering/BIBLE_AMENDMENTS.md`](docs/engineering/BIBLE_AMENDMENTS.md) Correction Pass 33 — that's where each cohort's admission decisions, structural anchors, deferred items, and SAR-16/17/18 discipline-rule codifications are recorded with case-study anchors.

- **For a plain-language tour of what Argus is and how to use the exports**, see [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md). This document (CREDITS.md) is dense by design — it's the legal-and-attribution surface, not the introductory overview.

---

## 1 — Tier 1 canonical registries

These sources are authoritative allocation-class registries operated by standards bodies or regulatory authorities. Argus treats them as canonical allocation-class registries for confidence-band purposes; the live-DB `source_type` values are mixed — sids 35/36/34/7/44 carry `source_type='primary_registry'`, while sids 1/2/3 retain a historical `source_type='regulatory'` vestige (see the §9 reconciliation note).

- **[IEEE OUI registry MA-L 24-bit](https://standards-oui.ieee.org/oui/oui.csv)** (sources.id=1) — IEEE-SA's canonical OUI allocation database (Organizationally Unique Identifier, 24-bit prefix). 39,355 raw observations contribute 54 promoted identifiers. Per-source attribution: [IEEE Standards Association](https://standards.ieee.org/products-services/regauth/oui/).
- **[IEEE OUI-28 registry MA-M 28-bit](https://standards-oui.ieee.org/oui28/mam.csv)** (sources.id=2) — MA-M (Medium) sub-allocations. 12,779 raw observations contribute 6,309 promoted identifiers.
- **[IEEE OUI-36 registry MA-S 36-bit](https://standards-oui.ieee.org/oui36/oui36.csv)** (sources.id=3) — MA-S (Small) sub-allocations. 13,999 raw observations contribute 6,947 promoted identifiers.
- **[IEEE IAB registry (36-bit legacy)](https://standards-oui.ieee.org/iab/iab.csv)** (sources.id=35) — Individual Address Block registry (predecessor to MA-S). 4,575 raw observations contribute 4,534 promoted identifiers. Re-pulled 2026-05-13 for primary_registry-band canonicalization.
- **[FCC EAS Equipment Authorization Grantee Registrations](https://opendata.fcc.gov/resource/3b3k-34jp.csv)** (sources.id=7) — US Federal Communications Commission's grantee registry (50,153 corporate registrants). Indexed at `fcc_grantees` table; used as the alias-disambiguation registry for facts-only corporate-entity confirmation (multi-registry cross-check predicate). **Upstream staleness (per `sources.notes.staleness_warning`):** the Socrata bulk (`dataset_id=3b3k-34jp`) is frozen at `dataset_freeze_date=2021-03-22` — grantees registered after that date are absent, so downstream consumers should treat grantee coverage as a 2021-03 snapshot.
- **[FAA UAS Remote-ID Public DOC API — DETAIL endpoint](https://uasdoc.faa.gov/api/v1/publicDOCRev/)** (sources.id=36) — US Federal Aviation Administration's ANSI/CTA-2063-A drone Remote ID prefix registry. 103 raw observations contribute 102 promoted identifiers. Canonical primary_registry re-pull.
- **[Bluetooth SIG company-identifier registry](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)** (sources.id=34) — Bluetooth SIG's canonical YAML of 2-byte company-ID allocations. 3,971 raw observations contribute 3,971 promoted `ble_manufacturer_id` identifiers (per migration 0011 schema introduction of the `ble_manufacturer_id` identifier type). **Wave J (J-1)** additionally promoted **705 net-new `ble_company_id` identifiers** (the `ble_company_id` slot grew 8 → 714) via the CP14 re-route from `member_uuids.yaml`; the `ble_manufacturer_id` slot is unchanged (different provenance).
- **[UK Companies House](https://api.company-information.service.gov.uk/)** (sources.id=44) — UK government's authoritative registrar of UK companies under the Companies Act 2006. Used as the corporate-entity confirmation source for IEEE OUI / MA-M registrations whose registrant name lacks a recognized corporate suffix (Class B sustained holds). Per-row URL template: `https://find-and-update.company-information.service.gov.uk/company/{company_number}`. Endpoints used: `/search/companies`, `/company/{company_number}`. Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: `/officers`, `/persons-with-significant-control`. **License: Open Government Licence v3.0 (OGL-3.0)** — https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/. Attribution string: *"This information is licensed under the terms of the Open Government Licence v3.0 — https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"*. Admitted via session `uk_companies_house_admission` (handoff package at `extraction_outputs/uk_ch_admission/HANDOFF_TO_VALIDATOR.md`); MAC-170 P2 promotion cycle landed 1 identifier (Johnson Matthey PLC #00033774).

**License posture:** primary_registry sources are factual public-allocation data. IEEE/FAA/Bluetooth SIG/FCC EAS carry no copyright carry-forward chain (per-source attribution at the `sources` table + per-row in `identifiers.source_url`); the UK Companies House row additionally carries OGL-3.0 attribution-required posture downstream (the attribution string above must accompany any downstream redistribution of UK CH-derived identifier rows). Database-rights regime jurisdictions (EU sui generis): the registries themselves are protected; Argus's compiled extraction is governed by Argus's ODbL-1.0 compilation license per LICENSE-DATA.

### v1.1.0 additions — US state Secretary-of-State registries (primary_registry, operator_manual_only)

Three US-state corporate registries were admitted in v1.1.0 as `primary_registry` sources under the new `access_mode='operator_manual_only'` convention (CP23): the source surfaces are structurally hostile to automation (CAPTCHA / Incapsula bot-challenge / paid-tier auth), so lookups happen via operator-driven browser sessions queued on the consolidated `extraction_outputs/us_state_sos_admission/operator_manual_queue.json`. Per-row provenance discipline and confidence-band ceilings are identical to automated sources — `access_mode` is a mechanism descriptor, not a quality signal.

- **[Delaware Division of Corporations](https://icis.corp.delaware.gov/Ecorp/EntitySearch/NameSearch.aspx)** (sources.id=45) — Delaware Secretary of State's Division of Corporations ICIS public entity-search portal. `source_type='primary_registry'`; `access_mode='operator_manual_only'` (CAPTCHA on `NameSearch.aspx`). Per-row URL template: `https://icis.corp.delaware.gov/Ecorp/EntitySearch/Details.aspx?FileNumber={file_number}`. Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: registered-agent / officer-director / shareholder-member lookups. **License: US_STATE_PUBLIC_RECORDS** (Delaware Code Title 8 §374; Title 29 Chapter 100 — Delaware FOIA). Attribution string (verbatim from `sources.notes.license_attribution`): *"Delaware public corporate records under Title 8 of the Delaware Code; public records under the Delaware Freedom of Information Act (Title 29 Chapter 100). No license-restricted reuse."* Admitted via session `us_state_sos_admission` (dispatch MAC-173; admission_date_utc `2026-05-16T23:57:07Z`). **Why included:** Delaware is the dominant US corporate-domicile jurisdiction for surveillance-vendor LLCs and US public companies; admission registers the source with `operator_manual_only` posture pending CAPTCHA workaround so per-row lookups can be queued without violating the §11 #3 automated-access discipline.
- **[California Secretary of State — Bizfile](https://bizfileonline.sos.ca.gov/)** (sources.id=46) — California Secretary of State's Bizfile Online business-entity search. `source_type='primary_registry'`; `access_mode='operator_manual_only'` (Incapsula/Imperva anti-bot wall). Per-row URL template: `https://bizfileonline.sos.ca.gov/search/business?filter%5Bentity_number%5D={entity_number}`. The posture may relax under registered API-key access (`CA_BIZFILE_API_KEY`) per `state_sos_access_mode_admission_addendum.md` §3.2 — not provisioned this cycle. Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: registered-agent / officer-director / shareholder-member lookups. **License: US_STATE_PUBLIC_RECORDS** (California Government Code §6253). Attribution string: *"California public corporate records under Government Code §6253 (California Public Records Act). No license-restricted reuse."* Admitted via session `us_state_sos_admission` (dispatch MAC-173; admission_date_utc `2026-05-16T23:57:07Z`). **Why included:** California is the dominant west-coast incorporation jurisdiction for surveillance-technology vendors (Flock Safety, Vigilant Solutions, Rekor regional subsidiaries, BriefCam, Skydio); admission reserves the relaxation path to `automated_with_auth` once the optional API key is provisioned.
- **[Texas Secretary of State SOSDirect](https://direct.sos.state.tx.us/)** (sources.id=47) — Texas Secretary of State SOSDirect business-entity search. `source_type='primary_registry'`; `access_mode='operator_manual_only'` (302 redirect on anonymous GET; paid SOSDirect tier required for non-trivial queries). Per-row URL template: TBD — TX SoS does not expose stable per-entity URLs (operator captures search-result-detail URL at lookup time). Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: registered-agent / officer-director / shareholder-member lookups. **License: US_STATE_PUBLIC_RECORDS** (Texas Business Organizations Code Chapter 22; Texas Government Code §552 — Public Information Act). Attribution string: *"Texas public business records under Business Organizations Code Chapter 22; public records under the Texas Government Code §552 (Public Information Act). No license-restricted reuse."* Admitted via session `us_state_sos_admission` (dispatch MAC-173; admission_date_utc `2026-05-16T23:57:07Z`). **Why included:** Texas is the dominant south-central US incorporation jurisdiction (Axon historical operations, body-cam OEMs, regional ALPR resellers); paid-tier-auth flagged as the relaxation precondition for any future automated access.

### v1.1.0 additions — Judicial filings, disclosure filings, and procurement disclosures (new source_type classes)

Three new `source_type` enum values were admitted in v1.1.0 via migration 0020 (CP23): `judicial_filing`, `disclosure_filing`, and `procurement_disclosure`. These distinguish judicial-record sources, regulatory disclosure-document sources, and vendor-side entity-registration disclosure sources from the existing 10-value enum bands. See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for the full 13-value roster; see [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP23 for the §-finding rationale.

- **[CourtListener / RECAP (Free Law Project)](https://www.courtlistener.com/)** (sources.id=48) — Free Law Project's open-access mirror of US federal court filings (RECAP archive of PACER documents + CourtListener-curated dockets and opinions). `source_type='judicial_filing'` (new source-type class admitted this release); `access_mode='automated_with_auth'` (Bearer token mandatory — anonymous tier revoked 2026-05-16). Per-row stable URL templates: `https://www.courtlistener.com/docket/{docket_id}/`, `/opinion/{opinion_id}/`, `/recap-document/{rd_id}/`. Endpoints used: `/api/rest/v4/courts/`, `/api/rest/v4/search/?type=r&q=...`. Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: `/api/rest/v4/people/`, `/api/rest/v4/judges/`, `/api/rest/v4/audio/`. Rate limit observed: 5 search requests per 60-second window (authenticated tier); self-paced at 13s/search-call. Auth handling: Bearer token loaded from `argus/.env/.env`; value never logged; length-only verification (40 chars). Yield this cycle: 47 search calls; 391 filings across 34 vendors searched; promotion outcome 0 identifiers / 0 procurement_records this dispatch (the cycle was structurally a discovery + disambiguation pass). **Post-Wave-J update (J-5):** this source now anchors **116 promoted `judicial_filing` identifiers** (the Wave J J-5 RECAP cohort: 109 `product_family_codename` + 7 `firmware_branded_string`), promoted at Phase H / [MAC-250](/MAC/issues/MAC-250) at confidence=75, re-typed to `source_type='judicial_filing'` by CP36 / mig-0029 / MAC-251 (per-class ceiling 85 per CP36-extension / MAC-256); all 116 carry `source_url LIKE '%courtlistener%'`. Cycle surfaced two candidate FP-class findings staged at `notes.candidate_findings_for_future_cp_or_sar[]`: `rico_co_defendant_not_customer_relationship` and `court_filing_fee_not_contract_value`; both helped cycle composition reach n=4 for CP26 §8 codification. **License: CC0-1.0** (Free Law Project metadata dedication). Attribution string: *"Free Law Project releases CourtListener metadata under CC0-1.0. Underlying federal court filings are public records (Feist + 17 USC §105 for US government works)."* Admitted via session `courtlistener_admission` (dispatch MAC-174; admission_date_utc `2026-05-17T03:55:52Z`). **Why included:** CourtListener / RECAP is the canonical open-access mirror of federal-court filings against surveillance-technology vendors; admission enables litigation-based corroboration of vendor/customer relationships and surfaces FP-class findings that strengthen the §5.2 source_excerpt-must-support-claim discipline. (Cross-listed in §5 below as a community-research Tier-1 organization — Free Law Project is a 501(c)(3) non-profit, parallel to the EFF treatment in §2.)
- **[SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar)** (sources.id=49) — US Securities and Exchange Commission's EDGAR system; the authoritative repository for publicly-traded-company disclosure filings. `source_type='disclosure_filing'` (new source-type class admitted this release); `access_mode='automated_html_parse'`. Per-row stable URL: `https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes_removed}/{filename}`. Endpoints used: `/files/company_tickers.json`, `/submissions/CIK{cik}.json`, `/Archives/edgar/data/{cik_no_pad}/{accession_no_dashes_removed}/{primary_doc}`. Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: Form 4 / insider transactions; Form 11-K / employee benefit plans; 20-F foreign-private filings (out of scope per runguide §0). Rate limit observed: ≤2 req/sec self-enforced (SEC policy ≤10). User-Agent sanitized at integration per MAC-171 §A. Yield this cycle: 4 filings extracted (4× 10-K); 28 aggregate concentration disclosures; 24 product families disclosed; 9 named government customers; 2 USAspending cross-source corroborations. **License: PUBLIC_DOMAIN** (US government work product per 17 USC §105). Attribution string: *"SEC filings are US government records and are not copyrightable per 17 USC §105."* Admitted via session `sec_edgar_admission` (dispatch MAC-171; admission_date_utc `2026-05-16T20:32:53Z`). **Why included:** the canonical structured-disclosure source for publicly-traded surveillance-technology vendors (Axon, Motorola Solutions, Rekor, Magnet Forensics, Cellebrite); produces named-government-customer claims that cross-corroborate USAspending procurement records.
- **[SAM.gov Entity Registration](https://api.sam.gov/entity-information/v3/entities)** (sources.id=50) — US GSA's System for Award Management; the authoritative procurement-eligibility entity-registration database for US federal awards. `source_type='procurement_disclosure'` (new source-type class admitted this release); `access_mode='automated_api'`. Per-row URL template: `https://sam.gov/entity/{uei}/coreData`. Auth shape: API key (`X-Api-Key` header); free signup at sam.gov; non-Federal individual tier rate ceiling **10 requests per UTC day** per CP26 §2 (empirically observed at cycle-5; documented "1,000/hour authenticated" applies only to Federal accounts). Cycle completion state: **`partial_pre_day1`** (admitted with partial yield at MAC-175 P0 — rate-ceiling 429 hit before day-1 multi-day cycle; next-cycle dispatch scheduled `2026-05-18T00:15:00Z` at `extraction_outputs/sam_gov_admission/_DAY1_DISPATCH_PROMPT.md`). Partial yield this cycle: 4 of 35 vendors attempted; 1 strong + 2 weak + 1 probe match; 1 manufacturer enrichment; 1 normalization disagreement flagged (Flock single-token-alias fanout); 3 cross-source corroborations; +9,623 cross-source corroboration UPDATEs landed against existing USAspending rows (Vigilant 56 + Motorola 9,545 + Genetec 22). **License: PUBLIC_DOMAIN** (US government work product per 17 USC §105). Attribution string: *"SAM.gov entity registration data is a US Government record and is not copyrightable per 17 USC §105."* Admitted via session `sam_gov_admission_cycle5_day0` (dispatch MAC-175; admission_date_utc `2026-05-17T14:10:40Z`). **Why included:** SAM.gov entity records are the procurement-eligibility canonicalizer (UEI is the post-DUNS federal-procurement vendor key); enables UEI-based cross-source corroboration with USAspending awards and SEC EDGAR named-government-customer claims, and seeds the multi-day cycle dispatch architecture (CP26 partial-pre-day1 admission posture).

**License-attribution carry-forward summary (v1.1.0 additions):** OGL-3.0 (sid 44 UK CH) is attribution-required — carry the verbatim attribution string above on any downstream redistribution of UK CH-derived rows. US_STATE_PUBLIC_RECORDS (sids 45/46/47) carry no license-restricted reuse per state-public-records statutes; per-row `source_url` citation discipline still applies. CC0-1.0 (sid 48 CourtListener) carries no attribution-required obligation at the metadata layer; per-row `courtlistener.com` source_url citation discipline still applies per §11 #2. PUBLIC_DOMAIN (sids 49/50, plus the sid 8 USAspending extension) carries no attribution-required obligation per 17 USC §105; per-row `source_url` citation discipline still applies.

### v1.1.0 admission ledger summary

| sid | Name | source_type | License | access_mode | admission_date_utc |
|---|---|---|---|---|---|
| 44 | UK Companies House | primary_registry | OGL-3.0 | automated_api | 2026-05-16T19:00:28Z |
| 45 | Delaware Division of Corporations | primary_registry | US_STATE_PUBLIC_RECORDS | operator_manual_only | 2026-05-16T23:57:07Z |
| 46 | California Secretary of State — Bizfile | primary_registry | US_STATE_PUBLIC_RECORDS | operator_manual_only | 2026-05-16T23:57:07Z |
| 47 | Texas Secretary of State SOSDirect | primary_registry | US_STATE_PUBLIC_RECORDS | operator_manual_only | 2026-05-16T23:57:07Z |
| 48 | CourtListener / RECAP (Free Law Project) | judicial_filing | CC0-1.0 | automated_with_auth | 2026-05-17T03:55:52Z |
| 49 | SEC EDGAR | disclosure_filing | PUBLIC_DOMAIN | automated_html_parse | 2026-05-16T20:32:53Z |
| 50 | SAM.gov Entity Registration | procurement_disclosure | PUBLIC_DOMAIN | automated_api (cycle_completion_state=`partial_pre_day1`) | 2026-05-17T14:10:40Z |

### v1.2.0 additions — FCC Equipment Authorization aggregator + primary surface (crowdsourced + regulatory)

Two FCC-ecosystem sources were admitted in v1.2.0 via the MAC-101 / MAC-178 wave: a community aggregator surfacing FCC ID filings under a NO_LICENSE_DECLARED Feist regime, paired with the official FCC EAS Filings UI as a distinct primary surface from the existing FCC EAS Grantee Registrations source (sid=7). The pair introduces a new dual-citation-pair convention (the discovery surface is the aggregator; the citation surface is the regulator) recorded via the new `fcc_citation_deferred_queue` staging table (migration 0022; 671 rows seeded). When FCC.gov egress is restored, the async re-citation pass will drain the queue and emit paired regulatory-band citation rows.

- **[fccid.io](https://fccid.io/)** (sources.id=51) — a third-party aggregator of US FCC Equipment Authorization System filings. fccid.io mirrors the FCC's public filings catalog with a more navigable surface than the official `apps.fcc.gov` UI. `source_type='crowdsourced'` (tier 2); `access_mode='automated_html_parse'`. Per-row URL template: `https://fccid.io/{grantee_code}-{product_code}`. **License: NO_LICENSE_DECLARED** — the upstream aggregator carries no declared license. Argus extracts identifier facts (FCC ID values, grantee-code linkages, product-code linkages) under the *Feist v. Rural Telephone Service* (499 U.S. 340 (1991)) facts-not-copyrightable doctrine; compilation arrangement (the aggregator's per-page layout, navigation structure, selection-and-organization) is NOT republished. Per-promoted-row sentinel: `identifiers.notes.upstream_license_posture='NO_LICENSE_DECLARED'` (canonical sentinel-key). Yield this cycle: 671 raw_observations staged as discovery rows under the dual-citation-pair pattern; promotion deferred to the async FCC.gov re-citation pass (citation half pending). **Post-Wave-J update (J-2):** the Wave J J-2 FCC-OET cohort promoted **687 net-new identifiers** (646 `equipment_class_code` + 41 `fcc_grantee_code`) at confidence=75, each carrying `identifiers.notes.upstream_license_posture='NO_LICENSE_DECLARED'` (the license posture is unchanged); the 671-row `fcc_citation_deferred_queue` remains seeded pending the async FCC.gov re-citation pass. Admitted via session `fccid_io_admission` (dispatch MAC-101; admission_date_utc `2026-05-18T04:27:14Z`). **Why included:** fccid.io is the dominant community surface for navigating FCC EAS filings; its discovery shape (one URL per `{grantee_code}-{product_code}`) lets the validator's async re-citation pass shortcut FCC.gov navigation from a 5-step lookup to a 1-step lookup when the discovery row carries the opportunistic `fcc_grant_ids[]` enrichment field (564 of 671 queue rows do).
- **[FCC Equipment Authorization System — Filings](https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm)** (sources.id=52) — the official FCC EAS Filings UI. Distinct from the existing FCC EAS Grantee Registrations data file (sid=7); the Filings UI gives per-FCC-ID filing surfaces (test reports, internal photos, RF exposure data) that the grantee CSV doesn't expose. `source_type='regulatory'` (tier 1); `access_mode='automated_html_parse'`. **License: PUBLIC_DOMAIN** (US government work product per 17 USC §105). Attribution string: *"FCC Equipment Authorization System filings are US government records and are not copyrightable per 17 USC §105."* Admitted under a degraded-mode posture: at MAC-101 extraction time, FCC.gov egress was unreachable from the runtime host (Akamai-edge HTTP/2 INTERNAL_ERROR across `apps.fcc.gov`), so the source row was admitted (the source EXISTS) but the citation-half of the 671 discovery rows was deferred to an asynchronous re-citation pass. The source exists; the citation rows accumulate when egress is restored. Admitted via session `fccid_io_admission` (dispatch MAC-101; admission_date_utc `2026-05-18T04:27:14Z`). **Why included:** the official primary surface for FCC ID filing material (test reports, photos, RF exposure data) — distinct from the grantee-registration CSV; the dual-citation-pair pattern (sid=51 discovery → sid=52 citation) is the bible-canon shape for aggregator-paired-with-regulator source admissions.

**License-attribution carry-forward summary (v1.2.0 additions):** NO_LICENSE_DECLARED (sid 51 fccid.io) inherits the Feist facts-only regime per §6 below — `identifiers.notes.upstream_license_posture='NO_LICENSE_DECLARED'` on every promoted row; downstream consumers redistributing Argus's database content inherit the same facts-only posture. PUBLIC_DOMAIN (sid 52 FCC EAS Filings) carries no attribution-required obligation per 17 USC §105; per-row `apps.fcc.gov` source_url citation discipline applies once the async re-citation pass drains the deferred queue.

### v1.2.0 admission ledger summary

| sid | Name | source_type | License | access_mode | admission_date_utc |
|---|---|---|---|---|---|
| 51 | fccid.io | crowdsourced | NO_LICENSE_DECLARED | automated_html_parse | 2026-05-18T04:27:14Z |
| 52 | FCC Equipment Authorization System — Filings | regulatory | PUBLIC_DOMAIN | automated_html_parse (degraded_mode_admission) | 2026-05-18T04:27:14Z |

### v1.3.0 additions — Vendor Desktop Application Static Analysis (Wave H pre-v1)

One source was admitted in v1.3.0 via the MAC-181 / MAC-177 Wave H pre-v1 wave: a vendor-desktop-application static-analysis methodology surfacing vendor-registered identifiers under per-vendor EULA postures. The wave processed 3 vendor desktop binaries + 1 FP-control binary (Hikvision iVMS-4200 + DJI Assistant 2 Mavic + DJI Assistant 2 FPV + FileZilla as FP-control) and yielded 4 vendor-attested non-BLE identifiers under the three new CP28(c) `identifier_type` classes (`windows_installer_productcode_vendor_registered`, `windows_com_clsid_vendor_registered`, `vendor_document_uuid_cloud_reference`). See [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP28 for the empirical-anchor + §8.2 sub-band ladder + §4.4 MAP/DROPPED posture per identifier class.

- **Vendor Desktop Application Static Analysis — Wave H** (sources.id=53) — the methodology covers publicly-downloadable vendor desktop applications across Windows / macOS / Linux. `source_type='manufacturer_app'` (tier 1; admitted under the existing Wave G `manufacturer_app` enum per CP15 source-type ceiling — the proposed `vendor_application_static_analysis` enum value is CP28(a) DEFERRED per CEO disposition; the operational band-distinction is encoded via the §8.2 sub-band ladder + `notes.session_admission='wave_h_pre_v1'`). `access_mode='per_vendor_public_download_no_auth'` (3 vendors: Hikvision .com download + DJI .com download + FileZilla .org download — all anonymous-public; no auth required; EULA-click-through navigated session-1 / session-2). **License: per_vendor** with `upstream_license_posture='no_license_declared_facts_only'` default per CP21. Per-vendor EULA-posture disposition counts at admission: `category_c` (include) 3 — Hikvision iVMS-4200 EULA (download-agreement modal) + DJI EULA + FileZilla GPLv2 all §3.6 (c) include; `category_a/b/d` 0 each. Per-binary attribution stored in `notes_json` (vendor + binary_sha256 + version + cohort_label + EULA disposition). Cohort F (sanctioned-vendor) sub-gate cleared per CP20 §11 #16 workflow audit (Hikvision iVMS-4200 admitted with NDAA Section 889 note; state/local LE deployments persist outside the federal-procurement bar — runguide §0 scope). Yield this cycle: 4 promoted identifiers + 7 documented_absence rows (6 Cohort A descope + 1 Skydio Cohort D P11 CLEAN NEGATIVE). Cycle completion state: `partial_cohort_set_complete` per CP26 §9 (Cohort D calibration window closed 2026-05-18T23:55:00Z on empirical-maximum record; Cohort F window OPEN pending Dahua + Uniview acquisition unblock). Admitted via session `wave_h_pre_v1` (dispatch [MAC-181](/MAC/issues/MAC-181); admission_date_utc `2026-05-18T00:00:00Z`). **Why included:** Wave H is the first generalization of the Wave G mobile-axis vendor-companion-app static-analysis methodology to the desktop axis (Windows / macOS / Linux). The methodology's empirical surface — captured under the CP17 desktop-axis thesis bifurcation finding (HANDOFF §10) — is **vendor cloud-endpoint discovery + installer-config surface + absence-as-finding**, not BLE service UUIDs (net-BLE = 0 post-CP26-§8 audit). The 4 vendor-attested non-BLE identifiers + the methodology's SAR-12 7-FP-class roster (`WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS`, `WINDOWS_COM_INTERFACE_GUIDS`, `WINDOWS_DEVCLASS_SETUP_GUIDS`, `LIBUSB_ASCII_IDENTIFIERS`, `THIRD_PARTY_DLL_PATH_PREFIXES`, `WINDOWS_SXS_PUBLICKEYTOKEN`, `windows_installer_productcode_in_msi_context`) form the foundation for future Wave H Continuation + Wave I desktop-axis dispatches.

**License-attribution carry-forward summary (v1.3.0 additions):** per_vendor license (sid 53) — the four per-vendor EULA postures are recorded per-binary in `notes_json`; downstream redistribution of Argus rows derived from Wave H carries `identifiers.notes.upstream_license_posture='no_license_declared_facts_only'` (canonical sentinel-key per [[feedback_license_posture_canonical_key]]). Feist facts-only doctrine applies at row-level: Argus extracts identifier facts (registry-context UUIDs, cloud-document UUIDs) from publicly-distributed vendor binaries under the *Feist v. Rural Telephone Service* facts-not-copyrightable doctrine; no decompiled vendor source enters the git index per §11 #15 (extracted binary contents remain SSD-only per HANDOFF §12).

### v1.3.0 admission ledger summary

| sid | Name | source_type | License | access_mode | admission_date_utc |
|---|---|---|---|---|---|
| 53 | Vendor Desktop Application Static Analysis — Wave H | manufacturer_app | per_vendor (no_license_declared_facts_only) | per_vendor_public_download_no_auth (cycle_completion_state=`partial_cohort_set_complete`) | 2026-05-18T00:00:00Z |

### v1.4.1 additions — Vendor companion APK admissions (manufacturer_app)

Five vendor companion APK sources were admitted in v1.4.1 via mig-0026a (the first `Na_` sub-slot data-only addendum precedent under CP32 §1). Admitted under [MAC-204](/MAC/issues/MAC-204) Phase 10b Hypothesis C admit-then-rebind disposition per CEO ratification on MAC-202: the 5 vendor APKs share license posture + analysis envelope with the existing sid=13 (Flock Safety FS Installer) row — static analysis under 17 USC §1201(j) + 37 CFR §201.40(b) security-research exemption; per-row sentinel `identifiers.notes.upstream_license_posture='no_license_declared_facts_only'` applies. Source rows seeded at v1.4.1; row admissions promoting identifiers anchored to these sids land at future Stage-2 validator phases as evidence-arrival propagates them through the Phase-5 promotion gate.

- **[Hikvision Hik-Connect](https://hikconnect.com)** (sources.id=67; `com.hikvision.hikconnect@6.11.631.0506`) — vendor companion app; cloud VMS / video doorbell; admitted with NDAA Section 889 note (state/local LE deployments persist outside the federal-procurement bar).
- **[Dahua DMSS](https://www.dahuasecurity.com)** (sources.id=68; `com.mm.android.DMSS@2.4.14`) — vendor companion app; cloud VMS / camera management; admitted with NDAA Section 889 note.
- **[Motorola Solutions WAVE PTT](https://www.motorolasolutions.com)** (sources.id=69; `com.motorolasolutions.wave@3.1.8.47141`) — vendor companion app; push-to-talk radio + Milicom PTT Button accessory pairing surface.
- **[Parrot FreeFlight 6](https://www.parrot.com/en/freeflight-6)** (sources.id=70; `com.parrot.freeflight6@6.7.6`) — vendor companion app; drone flight + ARSDK + ASD-STAN Drone-RID protocol surface.
- **[DJI Industry Pilot](https://www.dji.com)** (sources.id=71; `com.dji.industry.pilot@v1.9.0`) — vendor companion app; DJI enterprise pilot console.

### v1.4.1 additions — Manufacturer lexicon (1 hidden_arm row)

The CP31 multi-arm hub-and-spoke schema landed at v1.4.1 (mig-0025; commit `40b166e`) admits its first arm canonical:

- **Parrot Automotive** (manufacturers.id=222) — admitted as a `hidden_arm` row under the existing Parrot hub (id=25). `is_arm=1, parent_manufacturer_id=25, query_default='hidden_arm', primary_category='automotive_telematics', aliases='PARROT FAURECIA AUTOMOTIVE SAS,Parrot Faurecia Automotive S.A.S'`. Default queries against `manufacturers` filter `WHERE query_default = 'visible'` and do not surface this arm; explicit-opt-in audit queries surface it (see [DATA_DICTIONARY.md §4.4](DATA_DICTIONARY.md) for the three explicit-opt-in paths). The arm is admitted in anticipation of the Phase 7-bis 177-row fccid.io 2AG-attested cohort promotion (deferred to v1.4.2 — first v1.4.2 work item).

### v1.4.1 additions — Honeywell ACS division attestation completion

The [MAC-195](/MAC/issues/MAC-195) Phase 8 wave (Stage 1 sub-pass 43) completed the Honeywell admission via ACS division enrichment — appending the `Honeywell.notes.honeywell_acs_division_attestation` key with CT45 + CT40 device-model attestations + the `dubai_android_releasekey` code-signing branch attribution. The enrichment was anchored on 7 Honeywell OTA signing certs recovered from CT40 + CT45 Android firmware (Honeywell CodeSign RSA CA / OU=ACS / O=Honeywell International Inc.). The §44.3 product-nomenclature-corpus enrichment from the Wave I.14a runguide was DEFERRED at [MAC-203](/MAC/issues/MAC-203) per Path 1 (intentional scope narrowing — no surviving §11 #7 evidence trail at v1.4.1; see [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) Deferral Note 1).

### v1.4.1 — Numerex Corporation alias resolution (not a separate admission)

[MAC-196](/MAC/issues/MAC-196) resolved Numerex Corporation as **Sierra Wireless acquisition aliases** rather than as a separate manufacturer admission — the candidate Numerex rows merge into the Sierra Wireless canonical via the alias-aware JOIN discipline. No `manufacturers` row count delta for Numerex.

### v1.4.1 admission ledger summary

| sid | Name | source_type | License | access_mode | admission_date_utc |
|---|---|---|---|---|---|
| 67 | Hikvision Hik-Connect (com.hikvision.hikconnect@6.11.631.0506) | manufacturer_app | per_vendor (no_license_declared_facts_only) | per_vendor_public_download_no_auth | 2026-05-21 |
| 68 | Dahua DMSS (com.mm.android.DMSS@2.4.14) | manufacturer_app | per_vendor (no_license_declared_facts_only) | per_vendor_public_download_no_auth | 2026-05-21 |
| 69 | Motorola Solutions WAVE PTT (com.motorolasolutions.wave@3.1.8.47141) | manufacturer_app | per_vendor (no_license_declared_facts_only) | per_vendor_public_download_no_auth | 2026-05-21 |
| 70 | Parrot FreeFlight 6 (com.parrot.freeflight6@6.7.6) | manufacturer_app | per_vendor (no_license_declared_facts_only) | per_vendor_public_download_no_auth | 2026-05-21 |
| 71 | DJI Industry Pilot (com.dji.industry.pilot@v1.9.0) | manufacturer_app | per_vendor (no_license_declared_facts_only) | per_vendor_public_download_no_auth | 2026-05-21 |

### v1.5.0 additions — Lexicon-Expansion Wave source admissions (2 new sources + 2 dedup-merge citations)

The v1.5.0 cycle admitted two new sources alongside the +40 net-new manufacturer cohort_prediction admissions (`+39` ordinary cohort plus the Pelco `hidden_arm` row under Motorola Solutions). Two existing sources (sid=51 fccid.io + sid=54 crt.sh aggregator) were cited heavily during the wave (747 + 60 v1.5.0 citations respectively) but were NOT re-admitted; per §11 #11 dedup-merge discipline established at integration-time reconciliation, identifier rows from a previously-admitted source-row update their existing sid rather than spawning duplicates.

- **[GitHub Code Search REST API](https://api.github.com/search/code)** (sources.id=72) — GitHub's public code-search API (`GET /search/code` per https://docs.github.com/en/rest/search/search#search-code). `source_type='crowdsourced'` (tier 3); `access_mode='automated_api'`. Per-finding URL template: `https://github.com/{owner}/{repo}/blob/{sha}/{path}#L{line}` (pinned-SHA + line-anchored per §11 #1 source-url-direct). **License: NO_LICENSE_DECLARED** — the GitHub Code Search API itself carries no declared license; per-repo license declarations vary across hits. Argus extracts identifier facts (filename, line, SHA, URL) under the *Feist v. Rural Telephone Service* (499 U.S. 340 (1991)) facts-not-copyrightable doctrine per §11 #16; per-repo licenses inherit at the per-finding level but compilation arrangement (search-result ranking, snippet extraction, navigation surface) is NOT republished. Per-promoted-row sentinel: `identifiers.notes.upstream_license_posture='NO_LICENSE_DECLARED'`. Admitted via session `wave_v1_5_lexicon_expansion` (dispatch [MAC-232](/MAC/issues/MAC-232); see [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP33 §1). **Why included:** the code-search surface is the dominant first-party crowdsourced extraction surface for the v1.5.0 cohort_prediction wave (counter-UAS, persistent-surveillance, through-wall-radar, CCTV/VMS, electronic-monitoring vendors); per-finding factual extraction supports the cohort_prediction admission discipline under SAR-15 pre-load + SAR-16 alias-length-floor + SAR-17 no-generic-product-aliases.
- **[adsb.lol v2 (FAA-registry-derived aircraft tracking)](https://api.adsb.lol/v2/)** (sources.id=73) — community-operated aircraft-tracking surface derived from live ADS-B broadcasts cross-referenced against the FAA Civil Aviation Registry (14 CFR Part 47 public record). `source_type='regulatory'` (tier 3 — the upstream FAA Part 47 registry is regulatory-of-record; the adsb.lol surface re-publishes the public-record portions verbatim with live ADS-B broadcast cross-reference). `access_mode='automated_api'`. Per-row URL templates: `https://api.adsb.lol/v2/icao/{icao24}` + `https://api.adsb.lol/v2/registration/{n_number}`. **License: PUBLIC_DOMAIN_EQUIVALENT** (FAA Civil Aviation Registry is 14 CFR Part 47 public record; live ADS-B broadcasts are public spectrum emissions under FCC Part 87 with no copyright on factual position/identification data per Feist). Attribution string: *"Aircraft-tracking data derived from FAA Civil Aviation Registry (14 CFR Part 47 public record) and live ADS-B broadcasts. The compilation surface is operated by adsb.lol; the underlying data is public-domain factual."* Admitted via session `wave_v1_5_lexicon_expansion` (dispatch [MAC-232](/MAC/issues/MAC-232); see [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP33 §1). **Why included:** the persistent-surveillance cohort (Elbit Systems of America, General Atomics, TCOM, Persistent Surveillance Systems) requires aircraft-axis identifier surfaces (ICAO-24 hex, N-number, registry-operator chain) for cohort_prediction admissions; adsb.lol's FAA-registry-derived surface is the canonical public-domain-equivalent aircraft-tracking source.

**Integration-time dedup-merge note (per §11 #11):** sid=54 (Certificate Transparency Logs — crt.sh aggregator) was cited 747 times across the v1.5.0 cohort_prediction wave (cross-source corroboration anchor for vendor-controlled-hostname identifiers across counter-UAS / CCTV / persistent-surveillance vendors); sid=51 (fccid.io) was cited 60 times (FCC EAS grantee-code / equipment-class corroboration). Neither was re-admitted as a new sid — both inherit the v1.2.0 / v1.4.0 admission posture verbatim, and integration-time dedup-merge per §11 #11 collapses any candidate duplicate sid rows into the existing sids. The v1.5.0 source-row count delta is +2 net (71 → 73), not +4.

**License-attribution carry-forward summary (v1.5.0 additions):** NO_LICENSE_DECLARED (sid 72 GitHub Code Search REST API) inherits the Feist facts-only regime per §6 below — `identifiers.notes.upstream_license_posture='NO_LICENSE_DECLARED'` on every promoted row; downstream consumers redistributing Argus's database content inherit the same facts-only posture for these rows. PUBLIC_DOMAIN_EQUIVALENT (sid 73 adsb.lol v2) carries no attribution-required obligation per the upstream FAA Part 47 public-record posture + Feist on the live-ADS-B portion; per-row `api.adsb.lol` source_url citation discipline still applies per §11 #2 source-url-direct.

### v1.5.0 admission ledger summary

| sid | Name | source_type | License | access_mode | admission_date_utc |
|---|---|---|---|---|---|
| 72 | GitHub Code Search REST API | crowdsourced | NO_LICENSE_DECLARED (per_finding_factual_extraction_only_per_feist_facts_only) | automated_api | 2026-05-22 |
| 73 | adsb.lol v2 (FAA-registry-derived aircraft tracking) | regulatory | PUBLIC_DOMAIN_EQUIVALENT (FAA Part 47 + Feist on live ADS-B) | automated_api | 2026-05-22 |

### v1.5.0 lexicon-expansion wave — Manufacturer cohort admissions (+40 net; 52 → 92 total)

The v1.5.0 lexicon-expansion wave (dispatch [MAC-232](/MAC/issues/MAC-232); Two-Session Parallel Dispatch) admitted **40 net-new manufacturer canonicals** across 7 surveillance cohorts plus the multi-purpose §11 #10 carveout cohort. Per the integration-time counting reconciliation: 21 Session 1 (military/federal) + 19 Session 2 (commercial/consumer; the Pelco arm row counts within the Session 2 camera_vms cohort, not as a separate +1) = 40. The full per-vendor breakdown is canonicalized in `manufacturers` rows ids 223-262; CP33 §3 in BIBLE_AMENDMENTS.md carries the §-finding rationale.

The cohort_prediction admission discipline composes with SAR-15 GENERIC_RISK_CANONICALS pre-load (per-vendor probe-scope discipline from v1.4.0), SAR-16 alias-length-floor (formal codification from the lockheed-LM n=134 substring-collision driving case), and SAR-17 no-generic-product-aliases (formal codification from the mydefence-EAGLE n=41 substring-collision driving case). The wave also introduces three new `identifiers.device_category` enum values via mig-0027 / CP33 §2: `cctv_camera`, `persistent_surveillance`, `through_wall_radar` (dual-table CHECK literal sweep continuing the CP32 §1 precedent).

#### Counter-drone / counter-UAS cohort (11 new vendors)

The existing counter-drone section (Dedrone + DroneShield in the v1.0.0 baseline) extends with 11 cohort_prediction admissions from the v1.5.0 Session 1 military/federal wave:

- **Anduril Industries** (manufacturers.id=223) — admitted as multi-product hub (`notes.multi_product_admission=true`); future CP31-style arm-split candidates queued for v1.5.x — Sentry Tower → persistent_surveillance, Anvil → drone_detect, Lattice OS → unknown_software_substrate, Roadrunner → drone_detect, Sentinel → drone_detect.
- **Fortem Technologies** (id=224), **Citadel Defense** (id=225), **Black Sage Technologies** (id=226), **D-Fend Solutions** (id=227), **AeroDefense** (id=228), **Echodyne** (id=229), **Liteye Systems** (id=230), **Robin Radar Systems** (id=231), **MyDefence Communications** (id=232), **Sensofusion** (id=233) — all admitted at `primary_category='drone_detect'` per cohort_prediction discipline. Citadel Defense, Black Sage Technologies, Echodyne, and Robin Radar Systems carry `notes.sar15_disambig_required=true` + `notes.sar15_high_risk_canonical=true` flag fields per Schema-truth-drift #3 (168 Elbit-class FCC disambig deferred to v1.5.x Elbit sub-cycle).

#### Border / persistent-surveillance cohort (NEW SECTION — 4 new vendors + 2 multi-purpose §11 #10 carveouts)

The v1.5.0 wave introduces the persistent-surveillance cohort and the CP33 §2 `identifiers.device_category='persistent_surveillance'` enum value. Cohort scope covers aerostat / lighter-than-air persistent platforms + tower-mounted persistent imaging + strategic-altitude aerial persistent surveillance:

- **Elbit Systems of America** (id=234), **General Atomics** (id=237), **TCOM** (id=238), **Persistent Surveillance Systems** (id=239) — all admitted at `primary_category='persistent_surveillance'`. General Atomics, TCOM, and Persistent Surveillance Systems carry the SAR-15 disambig flag.
- **Multi-purpose §11 #10 carveouts** (admitted at `primary_category='unknown'`; high-confidence Lynceus export excludes per §11 #13): **Northrop Grumman** (id=235), **Lockheed Martin** (id=236). Standardized footnote: *"admitted at `device_category='unknown'` per §11 #10 multi-purpose-vendor carveout; high-confidence Lynceus export excludes per §11 #13"*. Both vendors have substantial surveillance-adjacent product portfolios (aerostat platforms, persistent ISR, sensor packages) alongside broader IoT/defense product lines that disqualify primary_category at this admission cycle.

#### Through-wall radar cohort (NEW SECTION — 3 new vendors)

The v1.5.0 wave introduces the through-wall radar cohort and the CP33 §2 `identifiers.device_category='through_wall_radar'` enum value. The cohort is regulatorily distinct via FCC §15.519 UWB-LE-only carveout (operationally restricted to law-enforcement use):

- **Camero** (id=240) — admitted at `primary_category='through_wall_radar'`; SAR-15 disambig flag present.
- **NIITEK** (id=241) — admitted at `primary_category='through_wall_radar'` on cohort_prediction basis with **zero-source attestation** after wide-net sweep (Chemring through-wall radar subsidiary, intentionally low-profile US government vendor); `notes.zero_source_admission=true` + `notes.low_confidence_flag=true`; future v1.5.x cycle should re-attempt source attestation.
- **TiaLinx** (id=242) — admitted at `primary_category='through_wall_radar'`.

#### IMSI catcher cohort (existing section; +1 new vendor)

- **Rohde & Schwarz** (id=243) — appended to the existing IMSI catcher section (Harris, Digital Receiver Technology, Engility, KeyW, Jacobs, Septier) at `primary_category='imsi_catcher'`.

#### Fleet telematics cohort (NEW SECTION — 6 new vendors + 1 multi-purpose §11 #10 carveout)

The v1.5.0 wave introduces the fleet-telematics cohort under the CP32 §1 `identifiers.device_category='automotive_telematics'` enum value (admitted in v1.4.1 mig-0026; first cohort_prediction populations land here):

- **Geotab** (id=244), **Verizon Connect** (id=245), **Samsara** (id=246), **Motive** (id=247), **Lytx** (id=248), **Omnitracs** (id=249) — all admitted at `primary_category='automotive_telematics'`.
- **Multi-purpose §11 #10 carveout**: **Trimble** (id=250) — admitted at `primary_category='unknown'` (surveillance-adjacent via fleet-management products but Trimble's broader IoT/auto/agriculture/geospatial presence dominates); high-confidence Lynceus export excludes per §11 #13.

#### CCTV camera / VMS cohort (NEW SECTION — 6 new vendors + 1 hidden_arm + 1 multi-purpose §11 #10 carveout)

The v1.5.0 wave introduces the CCTV camera / VMS cohort under the CP33 §2 `identifiers.device_category='cctv_camera'` enum value:

- **Hanwha Vision** (id=251), **Milestone Systems** (id=253), **Vivotek** (id=257) — all admitted at `primary_category='cctv_camera'`.
- **Pelco, Inc.** (id=254) — admitted as the framework's **second multi-arm `hidden_arm` row** under the CP31 hub-and-spoke schema (`parent_manufacturer_id=3` Motorola Solutions, `is_arm=1`, `query_default='hidden_arm'`, `primary_category='cctv_camera'`); evidence chain: MSI 10-K FY2025 Exhibit 21 (Pelco acquired by Motorola Solutions 2020; Delaware). Under Motorola Solutions canonical section (id=3), Pelco is a `hidden_arm` per CP31 §4.6 hub-and-spoke precedent (the first such precedent landed Parrot Automotive id=222 under Parrot id=25 at v1.4.1). Default queries against `manufacturers` filter `WHERE query_default = 'visible'` and do not surface this arm; explicit-opt-in audit queries surface it per CP31 §4.6.
- **NDAA §889 cohort** (admitted with the standardized note *"NDAA §889 federal procurement bar applies; state/local LE deployments persist outside the federal-procurement bar (runguide §0 scope)"*): **Uniview** (id=255), **Tiandy** (id=256). Both carry the dual-format `notes.ndaa_section_889_note` (canonical) + `notes.ndaa_section_889_affected` (S2-staged) + `notes.ndaa_attribution_note` (S2-staged) per the v1.5.0 Step 4 schema-truth observation (Schema-truth-drift #2: Hikvision + Dahua use only the canonical `ndaa_section_889_note`; Uniview + Tiandy carry both the canonical and S2-staged forms for forward-compatibility).
- **Multi-purpose §11 #10 carveout**: **Bosch Security Systems** (id=252) — admitted at `primary_category='unknown'` (broader Bosch IoT / automotive / industrial presence dominates); high-confidence Lynceus export excludes per §11 #13.

**Retroactive cctv_camera recategorization (Stage 1 Step 6 / gate G-B):** seven existing v1.0.0 / v1.2.0 / v1.3.0 vendor canonicals flipped to `primary_category='cctv_camera'` to align with the new CP33 §2 enum value: **Hikvision** (id=209), **Dahua** (id=208), **Axis Communications** (id=7), **Avigilon** (id=6), **Verkada** (id=210), **Eagle Eye Networks** (id=220), **Rhombus Systems** (id=221). NDAA §889 attribution preserved verbatim on Hikvision (id=209) and Dahua (id=208) via the canonical `notes.ndaa_section_889_note` key. BriefCam (id=31) was **DEFERRED** per board (analytics-layer ambiguity: BriefCam is a video-analytics overlay on top of arbitrary CCTV/VMS, not itself a CCTV camera); `primary_category='face_recog'` unchanged. Total identifier rows recategorized: **31** (14 Hikvision + 8 Dahua + 6 Axis + 1 Avigilon + 1 Eagle Eye Networks + 1 Rhombus + 0 Verkada).

#### Electronic monitoring cohort (NEW SECTION — 5 new vendors; standalone admission for v1.5.0)

The v1.5.0 wave introduces the electronic-monitoring cohort under the existing `identifiers.device_category='gps_tracker'` enum value:

- **BI Incorporated** (id=258) — admitted as **standalone for v1.5.0** (Geo Group parent admission deferred to v1.5.x per gate G-F; future arm-split shape: `is_arm=1, parent_manufacturer_id=<new Geo Group id>, query_default='hidden_arm'`).
- **Attenti** (id=259), **STOP** (id=260), **Sentinel Offender Services** (id=261), **Track Group** (id=262) — all admitted at `primary_category='gps_tracker'`. STOP (id=260) and Sentinel Offender Services (id=261) carry `notes.sar15_disambig_required='multi-anchor confirmation before cross-source attribution lift'` per the per-vendor probe-scope discipline.

#### v1.5.0 SAR codifications (BIBLE_AMENDMENTS.md)

The v1.5.0 cycle codified three new SAR entries from in-cycle empirical anchors:

- **SAR-16 — Alias-length-floor discipline** (BIBLE_AMENDMENTS.md line 4682): driving case lockheed-LM n=134 substring collisions; formal codification per BIBLE_AMENDMENTS.md.
- **SAR-17 — No-generic-product-aliases discipline** (BIBLE_AMENDMENTS.md line 4701): driving case mydefence-EAGLE n=41 substring collisions; formal codification per BIBLE_AMENDMENTS.md.
- **SAR-18 — Classifier-Predicate Parity Discipline** (BIBLE_AMENDMENTS.md line 4752): oversized_mac_range exemplar (Step 9 halt at id=9404 Eagle Eye Networks size=256); `coverage_matrix.py` and `export_lynceus.py` classifiers MUST share runtime predicates; future `_classify_row` rule additions require dual-table parity check at PR time.

---

## 2 — Tier 1/2 public-records and procurement data

- **[EFF Atlas of Surveillance](https://atlasofsurveillance.org/)** (sources.id=5) — Electronic Frontier Foundation + UNLV Reynolds School of Journalism's collaborative deployment-mapping project. 15,071 `deployment_observations` rows. **License: CC-BY-NC-SA-4.0**. **DOWNSTREAM COMMERCIAL CAUTION:** the NC (NonCommercial) clause prohibits commercial redistribution of these rows or their derivatives. See LICENSE-DATA §2.1 + §4.1 for the per-row LICENSE column quarantine mechanism. Non-commercial / research / journalist use is licensed.
- **[DeFlock](https://deflock.me/)** (sources.id=6) — Community-curated ALPR camera location database, OSM-mirrored via `cdn.deflock.me`. 101,597 `deployment_observations` rows. **License: ODbL-1.0**. Compatible with Argus's ODbL-1.0 compilation license. ShareAlike applies to derivative databases. DeFlock is a thin frontend (its own repo metadata is MIT) that reads from and writes to OpenStreetMap; the data layer is OSM/ODbL-1.0. **Required attribution (verbatim, carry on downstream redistribution of DeFlock-derived rows):** *"© OpenStreetMap contributors. Data available under the Open Database License (ODbL) 1.0. https://www.openstreetmap.org/copyright"*.
- **[USAspending.gov](https://api.usaspending.gov/api/v2/search/spending_by_award/)** (sources.id=8) — US federal procurement award database (public domain). 46,043 `procurement_records` rows (43,483 at v1.0.0; +2,560 net-new via the v1.1.0 deep-extension session `usaspending_deep_admission` MAC-172). The deep-extension cycle fanned out across the full 34-vendor canonical lexicon (extending the v1.0.0 narrative-extracted scope which was limited to 5–6 SEC-filing vendors via SEC EDGAR RG5); covered 2021-01-01 through 2026-05-16 with award type codes A/B/C/D; total net-new federal award value covered USD $2,095,345,219.58. The v1.1.0 SAM.gov admission cycle (MAC-175, sources.id=50) landed an additional +9,623 cross-source corroboration UPDATEs against existing USAspending rows per §5.2 cross-source confidence-lift discipline.
- **[Granicus Legistar Web API](https://webapi.legistar.com/v1/)** (sources.id=10) — municipal legislative-matter retrieval across 5 token-free starting-batch clients (chicago, sfgov, detroit, hampton, cabq). 3 `council_minutes_matters` rows. Each row sources to a specific municipality's public-records system; per-row attribution at `notes.source_url`. License: public records under FOIA / state public-records statutes.
- **[Wireshark `manuf` file](https://www.wireshark.org/download/automated/data/manuf)** (sources.id=4) — community-maintained OUI vendor-name file. 57,009 raw observations; historically used primarily as a vendor-name curation cross-reference. **Post-Wave-J update (J-3):** the Wave J J-3 cohort promoted **303 net-new identifiers** (291 `oui` + 9 `mac_range` + 3 §5.2 M&A-relabel `oui`) at confidence=75, and surfaced 3 IEEE↔Wireshark vendor-relabel signals (00:03:74 Schneider Electric ← Control Microsystems; 00:05:21 paired OUI; 70:23:93 Polytech A/S ← fos4X GmbH). License: GPL-2.0-or-later (Wireshark itself); the OUI data file is informationally derived from IEEE public registries.
- **[WiGLE.net wireless network database](https://api.wigle.net/api/v2/network/search)** (sources.id=9) — community-contributed wireless network observations. 100 raw observations staged at v1.0.0 (pipeline built; DRY_RUN ON pending operator-side credential gating). Future-enrichment hook. **Phase-3-gated (bible §11 #6):** `sources.last_status='live_ok'` diverges from the DRY_RUN prose above — status reconciliation deferred to the Phase-3 owner.

---

## 3 — Tier 1 academic research

- **[Marlin: Detecting IMSI-Catchers by Characterizing Identity Exposing Messages in Cellular Traffic](https://www.ndss-symposium.org/wp-content/uploads/2025-1115-paper.pdf)** (sources.id=37) — NDSS Symposium 2025 paper. 53 raw observations contribute 55 promoted behavioral_signatures (corroborated through cross-source review). Academic citation per author attribution; original publication: Network and Distributed System Security (NDSS) Symposium 2025.
- **[RUB-SysSec/DroneSecurity](https://github.com/RUB-SysSec/DroneSecurity)** (sources.id=43) — Ruhr-University Bochum Systems Security Group's DJI Drone-ID research; NDSS-track paper. 76 raw observations contribute 71 promoted identifiers. **License: AGPL-3.0** (declared); the AGPL-3.0 obligation propagates only if downstream redistribute the upstream compilation arrangement (which Argus does NOT republish — see LICENSE-DATA §3 for the Feist facts-only handling).
- **[GainSec/anti-crime-ecosystem-research](https://github.com/GainSec/anti-crime-ecosystem-research)** (sources.id=41) — CVE-anchored white paper analyzing surveillance device firmware. 70 raw observations contribute 14 promoted identifiers. **License: CC-BY-NC-ND-4.0 with research-use clause**. Downstream commercial / derivative-modification use restricted; research/educational use licensed under the upstream clause.

---

## 4 — Tier 2-3 manufacturer companion documentation

- **[Hak5 product documentation](https://docs.hak5.org/)** (sources.id=11) — vendor-published product reference material (Wayback snapshots also retained). Tier 2 manufacturer_doc.
- **[Flock Safety FS Installer](https://apkpure.com/flock-safety-device-app/com.flocksafety.hazyhiwire)** (sources.id=13) — vendor companion app (`com.flocksafety.hazyhiwire@2.4.0`), statically analyzed for embedded BLE service UUIDs, default credentials, pairing protocol identifiers. Tier 3 manufacturer_app.
- **[Getac BWC Viewer](https://apkpure.com/getac-bwc-viewer/com.getac.android.mobileappBWC)** (sources.id=14) — vendor companion app (`com.getac.android.mobileappBWC@1.0.20`), statically analyzed for body-worn camera identifiers. Tier 3 manufacturer_app.

**Decompiled vendor app source code is NOT redistributed** per the decompiled-output non-redistribution rule + LICENSE-DATA §3 (Feist facts-only handling). Argus extracts identifier candidates (value + relative file path within the decompile output) into `raw_observations`; the git index never contains vendor-proprietary source. Raw APK/IPA binaries are gitignored.

---

## 5 — Community-research GitHub repositories (Tier 1-3 crowdsourced/manufacturer_doc)

The community-research corpus (~24 repos) contributed corroborating identifier observations across drone Remote ID, BLE tracker catalogs, IMSI-catcher detection, ALPR-camera profiles, and surveillance-equipment categories.

**Canonical repos** (sources.id 12 + 15-33; 20 repos with stable contributor-authored license declarations):

| sources.id | Repository | Notes | License |
|---|---|---|---|
| 12 | [0xXyc/flock-you-wifi-recon](https://github.com/0xXyc/flock-you-wifi-recon) | | per repo LICENSE |
| 15 | [NSM-Barii/flock-back](https://github.com/NSM-Barii/flock-back) | | **MIT** (DB-recorded: *"MIT License Copyright (c) 2025 Jabari Lucien…"*) |
| 16 | [MaxwellDPS/Flock-You-Android](https://github.com/MaxwellDPS/Flock-You-Android) | | per repo LICENSE |
| 17 | [judcrandall/lookout.py](https://github.com/judcrandall/lookout.py) | | per repo LICENSE |
| 18 | [tesorrells/RF-Drone-Detection](https://github.com/tesorrells/RF-Drone-Detection) | | per repo LICENSE |
| 19 | [opendroneid/opendroneid-core-c](https://github.com/opendroneid/opendroneid-core-c) | ASTM/ASD-STAN reference impl | per repo LICENSE |
| 20 | [colonelpanichacks/flock-you](https://github.com/colonelpanichacks/flock-you) | | per repo LICENSE |
| 21 | [colonelpanichacks/oui-spy](https://github.com/colonelpanichacks/oui-spy) | | per repo LICENSE |
| 22 | [colonelpanichacks/Sky-Spy](https://github.com/colonelpanichacks/Sky-Spy) | | per repo LICENSE |
| 23 | [alphafox02/DragonSync](https://github.com/alphafox02/DragonSync) + FAA RID lookup submodule | | per repo LICENSE |
| 24 | [seemoo-lab/AirGuard](https://github.com/seemoo-lab/AirGuard) | multi-tracker BLE catalog | per repo LICENSE |
| 25 | [opendroneid/receiver-android](https://github.com/opendroneid/receiver-android) | | per repo LICENSE |
| 26 | [opendroneid/wireshark-dissector](https://github.com/opendroneid/wireshark-dissector) | | per repo LICENSE |
| 27 | [cyber-defence-campus/RemoteIDReceiver](https://github.com/cyber-defence-campus/RemoteIDReceiver) | HSLU thesis | per repo LICENSE |
| 28 | [proto17/dji_droneid](https://github.com/proto17/dji_droneid) | | per repo LICENSE |
| 29 | [nixxxo/tagfinder](https://github.com/nixxxo/tagfinder) | | per repo LICENSE |
| 30 | [EFForg/rayhunter](https://github.com/EFForg/rayhunter) | defensive_tool | per repo LICENSE |
| 31 | [eylonK14/IMSICatcherDetector](https://github.com/eylonK14/IMSICatcherDetector) | README-aspirational | per repo LICENSE |
| 32 | [CellularPrivacy/AIMSICD](https://github.com/CellularPrivacy/AIMSICD) | IMSI-detector cluster | per repo LICENSE |
| 33 | [GainSec/Flock-Safety-Trap-Shooter-Sniffer-Alarm](https://github.com/GainSec/Flock-Safety-Trap-Shooter-Sniffer-Alarm) | | per repo LICENSE |

**Deferred-dir secondary-batch repos** (sources.id 38-42; 5 repos added with explicit license-posture annotations):

| sources.id | Repository | Notes | License posture (per `sources.notes.license_posture`) |
|---|---|---|---|
| 38 | [DeflockJoplin/flock-you](https://github.com/DeflockJoplin/flock-you) (fork of `sources.id=20`) | net-new-id fork divergence | AGPL-3.0 inherited from upstream id=20 |
| 39 | [EthanThePhoenix38/flock-you-camera-detector](https://github.com/EthanThePhoenix38/flock-you-camera-detector) | negative-evidence | **NO_LICENSE_DECLARED** (flagged for validator review; Feist facts-only regime applies; see §6 below) |
| 40 | [FoggedLens/deflock-app](https://github.com/FoggedLens/deflock-app) | mobile companion | AGPL-3.0 declared |
| 41 | [GainSec/anti-crime-ecosystem-research](https://github.com/GainSec/anti-crime-ecosystem-research) | CVE-anchored white paper | CC-BY-NC-ND-4.0 with research-use clause (also enumerated under §3 academic research above) |
| 42 | [GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose](https://github.com/GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose) | firmware-binary distribution | **NO_LICENSE_DECLARED** (flagged for validator review; Feist facts-only regime applies; see §6 below) |

---

## 6 — NO_LICENSE_DECLARED Feist-defensible sources

Three sources (`sources.id` 39, 42, and — new in v1.2.0 — 51) publish material publicly without a LICENSE file or explicit license declaration. Argus's promotion regime under these sources operates under the [Feist v. Rural Telephone Service (499 U.S. 340 (1991))](https://supreme.justia.com/cases/federal/us/499/340/) facts-not-copyrightable doctrine, with the canonical composition discipline defined in `PROJECT_BIBLE.md` (see Canonical sources at end of this document).

- **sources.id=39 EthanThePhoenix38/flock-you-camera-detector** — 20 raw observations contribute 19 promoted identifiers. 1 row rejected as a known-fake (cc:cc:cc all-identical-octet OUI).
- **sources.id=42 GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose** — 50 raw observations contribute 8 promoted identifiers (firmware-binary mining).
- **sources.id=51 fccid.io** (new in v1.2.0) — 671 raw_observations staged as dual-citation-pair discovery rows; promotion deferred to the async FCC.gov re-citation pass under the MAC-101 partial-deliverable admission posture. No identifier promotions this release; the rows hold at `crowdsourced` 50-75 confidence band until paired with their sid=52 regulatory citation half.

**What Argus extracts** (facts; not copyrighted): identifier values, manufacturer attributions, pinned source URL citations.

**What Argus does NOT republish** (compilation arrangement; copyrighted): list-snippet verbatim, repository structure mirror, selection/organization beyond single-fact citation.

**Per-promoted-row sentinel:** `identifiers.notes.upstream_license_posture='NO_LICENSE_DECLARED'` (canonical sentinel-key).

Downstream consumers redistributing Argus's database content inherit the same facts-only posture for these rows.

---

## 7 — Surveillance-technology vendor lexicon (manufacturers table; 92 canonical entries at v1.5.0: 51 v1.4.1 hub-visible + 1 v1.4.1 hidden_arm (Parrot Automotive id=222) + 39 v1.5.0 net-new cohort_prediction admissions + 1 v1.5.0 hidden_arm (Pelco id=254 under Motorola Solutions))

The `manufacturers` table is the canonical lexicon of surveillance-technology vendors used as the Tier-2/3 device_category inference allowlist. Each entry contributes vendor attribution to identifier rows. This is NOT a data source in the registry sense above; it's an internal curated lexicon used at promotion time. Listed alphabetically:

| Vendor | Canonical category |
|---|---|
| AeroDefense | drone_detect *(v1.5.0 counter_uas cohort)* |
| Aerodome | drone |
| Anduril Industries | drone_detect *(v1.5.0 counter_uas cohort; **multi-product hub admission** — `notes.multi_product_admission=true`; 5 future arm-split candidates queued for v1.5.x: Sentry Tower → persistent_surveillance, Anvil → drone_detect, Lattice OS → unknown_software_substrate, Roadrunner → drone_detect, Sentinel → drone_detect)* |
| Attenti | gps_tracker *(v1.5.0 electronic_monitoring cohort)* |
| Autel Robotics | drone |
| Avigilon | cctv_camera *(v1.5.0 retroactive recat from `alpr` per gate G-B Step 6 retroactive cctv_camera recategorization; NDAA §889 not applicable)* |
| Axis Communications | cctv_camera *(v1.5.0 retroactive recat from `alpr` per gate G-B; NDAA §889 not applicable)* |
| Axon | body_cam |
| Berla | hacking_tool |
| BI Incorporated | gps_tracker *(v1.5.0 electronic_monitoring cohort; **standalone for v1.5.0** — Geo Group parent admission deferred to v1.5.x per gate G-F)* |
| Black Sage Technologies | drone_detect *(v1.5.0 counter_uas cohort; `notes.sar15_disambig_required=true`)* |
| BluePoint Alert | (uncategorized — documented_absence stub admission, v1.2.0) |
| Bosch Security Systems | (uncategorized — **multi-purpose §11 #10 carveout**, v1.5.0 camera_vms cohort; admitted at `device_category='unknown'`; high-confidence Lynceus export excludes per §11 #13) |
| BriefCam | face_recog *(NOT recategorized to cctv_camera per gate G-B — analytics-layer ambiguity: BriefCam is a video-analytics overlay on top of arbitrary CCTV/VMS, not itself a CCTV camera; `primary_category='face_recog'` unchanged)* |
| BRINC | drone |
| Camero | through_wall_radar *(v1.5.0 through_wall_radar cohort; FCC §15.519 UWB-LE-only regulatory carveout — operationally restricted to law-enforcement use; `notes.sar15_disambig_required=true`)* |
| Cellebrite | hacking_tool |
| Cisco Meraki | (uncategorized — positive-extraction admission, v1.2.0) |
| Citadel Defense | drone_detect *(v1.5.0 counter_uas cohort; `notes.sar15_disambig_required=true`)* |
| Clearview AI | face_recog |
| Coban Technologies | body_cam |
| Cradlepoint | (uncategorized — multi-purpose-vendor carveout) |
| Dahua | cctv_camera *(v1.5.0 retroactive recat from `(uncategorized)` per gate G-B; NDAA §889 federal procurement bar applies; state/local LE deployments persist outside the federal-procurement bar (runguide §0 scope); canonical `notes.ndaa_section_889_note`)* |
| Dedrone | drone_detect |
| D-Fend Solutions | drone_detect *(v1.5.0 counter_uas cohort)* |
| Digital Ally | body_cam |
| Digital Receiver Technology | imsi_catcher |
| DJI | drone |
| DroneShield | drone_detect |
| Eagle Eye Networks | cctv_camera *(v1.5.0 retroactive recat from `(uncategorized — documented_absence stub admission, v1.3.0)` per gate G-B)* |
| Echodyne | drone_detect *(v1.5.0 counter_uas cohort; `notes.sar15_disambig_required=true`)* |
| Elbit Systems of America | persistent_surveillance *(v1.5.0 border_persistent_surveillance cohort)* |
| Engility | imsi_catcher |
| Flock Safety | alpr |
| Fortem Technologies | drone_detect *(v1.5.0 counter_uas cohort)* |
| General Atomics | persistent_surveillance *(v1.5.0 border_persistent_surveillance cohort; `notes.sar15_disambig_required=true`)* |
| Genetec | alpr |
| Geotab | automotive_telematics *(v1.5.0 fleet_telematics cohort)* |
| Getac | body_cam |
| Hak5 | hacking_tool |
| Hanwha Vision | cctv_camera *(v1.5.0 camera_vms cohort)* |
| Harris | imsi_catcher |
| Hikvision | cctv_camera *(v1.5.0 retroactive recat from `(uncategorized)` per gate G-B; NDAA §889 federal procurement bar applies; state/local LE deployments persist outside the federal-procurement bar (runguide §0 scope); canonical `notes.ndaa_section_889_note`)* |
| Honeywell | (uncategorized — documented_absence stub admission, v1.2.0; v1.4.1 ACS division attestation completion via MAC-195) |
| Jacobs | imsi_catcher |
| Johnson Matthey PLC | (uncategorized — v1.1.0 closed Class B hold via UK Companies House #00033774; chemistry/precious-metals; no surveillance-adjacency) |
| Kenwood | police_radio |
| KeyW | imsi_catcher |
| L3Harris | (uncategorized — multi-purpose-vendor) |
| Lenel | (uncategorized — documented_absence stub admission, v1.2.0) |
| Liteye Systems | drone_detect *(v1.5.0 counter_uas cohort)* |
| Lockheed Martin | (uncategorized — **multi-purpose §11 #10 carveout**, v1.5.0 multi_purpose_carveout cohort; admitted at `device_category='unknown'`; high-confidence Lynceus export excludes per §11 #13) |
| Lytx | automotive_telematics *(v1.5.0 fleet_telematics cohort)* |
| Magnet Forensics | hacking_tool |
| Milestone Systems | cctv_camera *(v1.5.0 camera_vms cohort)* |
| Motive | automotive_telematics *(v1.5.0 fleet_telematics cohort)* |
| Motorola Solutions | (uncategorized — multi-purpose-vendor carveout; v1.5.0 hub-and-spoke parent for new Pelco `hidden_arm` id=254 per gate G-A) |
| MyDefence Communications | drone_detect *(v1.5.0 counter_uas cohort)* |
| NIITEK | through_wall_radar *(v1.5.0 through_wall_radar cohort; **zero-source admission** on cohort_prediction basis after wide-net sweep — Chemring through-wall radar subsidiary, intentionally low-profile US government vendor; `notes.zero_source_admission=true` + `notes.low_confidence_flag=true`; future v1.5.x cycle should re-attempt source attestation)* |
| Northrop Grumman | (uncategorized — **multi-purpose §11 #10 carveout**, v1.5.0 multi_purpose_carveout cohort; admitted at `device_category='unknown'`; high-confidence Lynceus export excludes per §11 #13) |
| Omnitracs | automotive_telematics *(v1.5.0 fleet_telematics cohort)* |
| Parrot | drone |
| Parrot Automotive | automotive_telematics *(v1.4.1 — first multi-arm `hidden_arm` row under CP31 hub-and-spoke schema; `is_arm=1, parent_manufacturer_id=25 [Parrot hub], query_default='hidden_arm'`)* |
| Pelco | cctv_camera *(v1.5.0 — second multi-arm `hidden_arm` row under CP31 hub-and-spoke schema, gate G-A; `is_arm=1, parent_manufacturer_id=3 [Motorola Solutions hub], query_default='hidden_arm'`; SEC Ex21 FY2025 evidence chain — Pelco, Inc. acquired 2020, Delaware)* |
| Persistent Surveillance Systems | persistent_surveillance *(v1.5.0 border_persistent_surveillance cohort; `notes.sar15_disambig_required=true`)* |
| PIPS Technology | alpr |
| Rekor | alpr |
| Reveal | body_cam |
| Rhombus Systems | cctv_camera *(v1.5.0 retroactive recat from `(uncategorized — documented_absence stub admission, v1.3.0)` per gate G-B)* |
| Robin Radar Systems | drone_detect *(v1.5.0 counter_uas cohort; `notes.sar15_disambig_required=true`)* |
| Rohde & Schwarz | imsi_catcher *(v1.5.0 imsi_catcher cohort)* |
| Samsara | automotive_telematics *(v1.5.0 fleet_telematics cohort)* |
| Sensofusion | drone_detect *(v1.5.0 counter_uas cohort)* |
| Sentinel Offender Services | gps_tracker *(v1.5.0 electronic_monitoring cohort; `notes.sar15_disambig_required='multi-anchor confirmation before cross-source attribution lift'`)* |
| Septier | imsi_catcher |
| Sierra Wireless | (uncategorized — multi-purpose-vendor) |
| Skydio | drone |
| SoundThinking (ShotSpotter) | gunshot_detect |
| STOP | gps_tracker *(v1.5.0 electronic_monitoring cohort; `notes.sar15_disambig_required='multi-anchor confirmation before cross-source attribution lift'`)* |
| TCOM | persistent_surveillance *(v1.5.0 border_persistent_surveillance cohort; `notes.sar15_disambig_required=true`)* |
| Tiandy | cctv_camera *(v1.5.0 camera_vms cohort; NDAA §889 federal procurement bar applies; state/local LE deployments persist outside the federal-procurement bar (runguide §0 scope); dual-format `notes.ndaa_section_889_note` (canonical) + `notes.ndaa_section_889_affected` (S2-staged) + `notes.ndaa_attribution_note` (S2-staged))* |
| TiaLinx | through_wall_radar *(v1.5.0 through_wall_radar cohort; FCC §15.519 UWB-LE-only regulatory carveout)* |
| Track Group | gps_tracker *(v1.5.0 electronic_monitoring cohort)* |
| Trimble | (uncategorized — **multi-purpose §11 #10 carveout**, v1.5.0 fleet_telematics cohort; admitted at `device_category='unknown'`; broader IoT/auto/agriculture/geospatial presence dominates; high-confidence Lynceus export excludes per §11 #13) |
| Uniview | cctv_camera *(v1.5.0 camera_vms cohort; NDAA §889 federal procurement bar applies; state/local LE deployments persist outside the federal-procurement bar (runguide §0 scope); dual-format `notes.ndaa_section_889_note` (canonical) + `notes.ndaa_section_889_affected` (S2-staged) + `notes.ndaa_attribution_note` (S2-staged))* |
| Utility Inc | body_cam |
| Verizon Connect | automotive_telematics *(v1.5.0 fleet_telematics cohort)* |
| Verkada | cctv_camera *(v1.5.0 retroactive recat from `(uncategorized — documented_absence stub admission, v1.2.0)` per gate G-B; 0 identifier rows currently at cctv_camera — manufacturer flip only)* |
| Vigilant Solutions | alpr |
| Vivotek | cctv_camera *(v1.5.0 camera_vms cohort)* |
| WatchGuard | body_cam |
| Wolfcom | body_cam |

**v1.2.0 lexicon additions (14 vendors, from 35 to 49):** 4 positive-extraction admissions from the MAC-104 Wave-G v2 PlayStore companion-app extraction pass — **Hikvision** and **Dahua** (both admitted with NDAA Section 889 note: state/local LE deployments persist outside the federal-procurement bar), **Autel Robotics**, and **Cisco Meraki**. 10 stub admissions from absence-investigation cycles (apk-pure 404 + apk-mirror "no results" + cohort-prediction reasoning) — **Verkada, Honeywell, Lenel, BluePoint Alert, PIPS Technology, Wolfcom, Utility Inc, Coban Technologies, Digital Ally, Aerodome** — each carries `notes.admission_basis='documented_absence_only'`.

**v1.3.0 lexicon additions (2 vendors, from 49 to 51):** 2 Cohort A stub admissions from Wave H pre-v1 desktop-axis absence-investigation — **Eagle Eye Networks** (Cohort A descope: EEN Viewer ships as a UWP MSIX package via Microsoft Store, not an Electron-class desktop client) and **Rhombus Systems** (Cohort A descope: Rhombus Console is a web app only; no desktop client distributed). Each carries `notes.documented_absence[]` with the absence-investigation findings; both are cloud-VMS / cloud-camera surveillance-tech vendors with structurally-absent desktop-axis client surface in 2026, anchoring the CP17 desktop-axis bifurcation thesis (cohort-presence dissolution dimension). Methodology source-of-truth: the Wave H wrapper at [`android_test/tools/extraction/wave_h_wrapper.py`](android_test/tools/extraction/wave_h_wrapper.py) (sibling to `wave_g_extractor.py`) carries the SAR-12 7-FP-class roster + the ±90-char windowed-clipping discipline.

**v1.4.1 lexicon addition (1 arm row, from 51 to 52 total — 51 hub-visible + 1 hidden_arm):** **Parrot Automotive** (id=222) admitted as the framework's first multi-arm `hidden_arm` row under the CP31 hub-and-spoke schema (mig-0025). `parent_manufacturer_id=25, is_arm=1, query_default='hidden_arm', primary_category='automotive_telematics', aliases='PARROT FAURECIA AUTOMOTIVE SAS,Parrot Faurecia Automotive S.A.S'`. The existing Parrot hub row (id=25, `primary_category='drone'`) is preserved unchanged. Default queries against `manufacturers` filter `WHERE query_default = 'visible'` and do NOT surface the arm; explicit-opt-in audit queries (e.g., `WHERE query_default IN ('visible','hidden_arm')`) surface it. The multi-arm vendor backlog (Cisco/Meraki, Motorola Solutions, Harris RF vs Harris Aerial, Honeywell ACS division) is queued for evidence-driven arm splits at v1.4.2+ per CP32 §4 admission-cadence sub-rule.

**v1.5.0 lexicon additions (40 net-new vendors, from 52 to 92 total — 51 v1.4.1 hub-visible + 1 v1.4.1 hidden_arm + 39 v1.5.0 cohort_prediction + 1 v1.5.0 hidden_arm):** the v1.5.0 lexicon-expansion wave admitted 40 net-new manufacturer canonicals (21 Session 1 military/federal + 19 Session 2 commercial/consumer, with Pelco arm counted within the Session 2 camera_vms cohort) across 7 surveillance cohorts plus 2 multi-purpose §11 #10 carveouts. The wave introduced 3 new `identifiers.device_category` enum values (`cctv_camera`, `persistent_surveillance`, `through_wall_radar`) via mig-0027 / CP33 §2, and admitted the framework's second multi-arm `hidden_arm` row — **Pelco** (id=254) under Motorola Solutions hub (id=3) per gate G-A — extending the CP31 hub-and-spoke precedent first applied to Parrot Automotive in v1.4.1. Stage 1 Step 6 (gate G-B) also flipped 7 existing vendors (Hikvision, Dahua, Axis Communications, Avigilon, Verkada, Eagle Eye Networks, Rhombus Systems) to `primary_category='cctv_camera'` (31 identifier rows recategorized; NDAA §889 attribution preserved on Hikvision + Dahua). Three SAR codifications anchored the wave: SAR-16 (alias-length-floor), SAR-17 (no-generic-product-aliases), SAR-18 (classifier-predicate parity). Per CP33 §7 v1.5.x/v1.6.0 backlog: arm-split candidates Avigilon-under-MSI + WatchGuard-under-MSI queued for v1.5.x; Geo Group admission + BI Incorporated arm-split queued for v1.5.x; 168-entry Elbit FCC grantee disambig queued for v1.5.x sub-cycle.

Lexicon evolution is documented in the amendment ledger at [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md). Aliases tracked per-vendor in `manufacturers.aliases`; multi-purpose-vendor carveouts are documented in `PROJECT_BIBLE.md` (see Canonical sources).

---

## 8 — Methodology, tooling, and pipeline credits

- **Argus code pipeline**: AGPL-3.0-or-later (see [LICENSE](LICENSE))
- **Argus database + dataset exports**: ODbL-1.0 (see [LICENSE-DATA](LICENSE-DATA)), with per-row license-tag carry-forward via the `deployment_observations.LICENSE` column (migration 0016) and per-source license posture at `sources.notes.license_posture`
- **Argus documentation**: CC-BY-SA-4.0 (see [LICENSE-DOCS](LICENSE-DOCS))

Methodology + bible-as-contract architecture: [METHODOLOGY.md](METHODOLOGY.md) §8 + [PROJECT_BIBLE.md](PROJECT_BIBLE.md).

---

## 9 — Re-derivation discipline

When producing derived datasets from Argus, honor the upstream license carry-forward chain at each layer:

- **Compilation license** (ODbL-1.0): standard ShareAlike attribution applies to derivative databases. EU database-rights regime jurisdictions: the database-rights protection extends to compilation-level derivatives.
- **Per-row LICENSE column** (`deployment_observations.LICENSE`): downstream consumers MUST honor per-row license tag.
  - Atlas-derived rows (`LICENSE='CC-BY-NC-SA-4.0'`, sid=5, 15,071 rows): **exclude from commercial derivative datasets** per upstream NC clause; non-commercial / research / journalist use is licensed.
  - DeFlock-derived rows (`LICENSE='ODbL-1.0'`, sid=6, 101,597 rows): compatible with ODbL-1.0 compilation license; standard ShareAlike applies.
- **Per-identifier `notes.upstream_license_posture`**: NO_LICENSE_DECLARED facts-only sources inherit the Feist regime — derivatives operate under Feist facts-not-copyrightable; no upstream license obligation. As of v1.5.x (post-Wave-J) this set spans `sources.id` 39 (19 rows) + 42 (8 rows) + sid 51 fccid.io (**687 Wave J J-2 promotions**: 646 `equipment_class_code` + 41 `fcc_grantee_code`, beyond the still-seeded 671-row deferred-citation queue) + sid 72 GitHub Code Search REST API (0 promotions). The prior "27 promoted rows total" figure predates the J-2 fccid.io promotions and is superseded; an exact recount of NO_LICENSE_DECLARED-tagged promoted rows was not performed this pass.
- **AGPL-3.0 source attribution** (`sources.id` 38, 40, 43, plus the implicit AGPL inheritance pattern in Argus's own code per LICENSE): research-derived factual claims do NOT trigger AGPL-3.0 copyleft; redistribution of the upstream compilation arrangement WOULD trigger it (and Argus does NOT republish such arrangements).
- **CC-BY-NC-ND-4.0 source attribution** (`sources.id=41` GainSec anti-crime-ecosystem-research): derivative-modification restricted per the ND clause; research-use clause permits Argus's factual extraction; downstream derivative-modification consumers must evaluate the ND clause separately.

For sources-row metadata discrepancy callout (sources **1/2/3** carry a historical `source_type='regulatory'` vestige; identifiers-row data is correctly labeled `primary_registry`): see [LICENSE-DATA §4.4](LICENSE-DATA) and [README.md](README.md). *(The prior "1/2/3/7" framing is corrected here: sid=7 FCC EAS Grantee now carries `source_type='primary_registry'` in the live DB per CP19/MAC-88.)*

---

## 10 — Build authorship

Argus v1.0.0 was built using a multi-agent orchestration approach
with human operator direction. The build methodology is documented in
[METHODOLOGY.md §8](METHODOLOGY.md) and [PROJECT_BIBLE.md](PROJECT_BIBLE.md).

Commit metadata reflects the agent ensemble plus the human operator
per the project's authorship discipline; full identity attribution
lives in the git log. Co-authored commits carry the
`Co-Authored-By: Paperclip <noreply@paperclip.ing>` trailer per
project convention.

**Human contributors:** the project's human operator directs
strategic decisions, approves canonical-bible amendments, raises new
discipline questions, and operates the runtime. Per-decision
authorship lives in the issue-thread audit trail.

**External contribution:** if you submit identifier candidates, new
sources, or discipline refinements via pull request, your
contribution credit is recorded in this file at the next
documentation refresh. See README.md "Contribution guidance" and the
hard-rule set in `PROJECT_BIBLE.md` (covering source-url-direct
provenance, PII discipline, promotion-gate provenance,
confidence-band ceilings, and the Feist facts-only doctrine) for
contribution discipline.

---

## Canonical sources

Descriptive references used in this document map to canonical bible
anchors as follows. The canonical bible (`PROJECT_BIBLE.md` and the
amendment ledger `BIBLE_AMENDMENTS.md`) holds the authoritative
specification; this document is the public-facing summary.

| Descriptive reference (as used in this doc) | Canonical source |
|---|---|
| source-type confidence-band ceiling rule | `PROJECT_BIBLE.md` §8.2 |
| facts-only doctrine / Feist facts-only regime / facts-only composition discipline | `PROJECT_BIBLE.md` §11 #16 |
| canonical sentinel-key (`notes.upstream_license_posture='NO_LICENSE_DECLARED'`) | `PROJECT_BIBLE.md` §11 #16 |
| decompiled-output non-redistribution rule | `PROJECT_BIBLE.md` §11 #15 |
| multi-purpose-vendor carveout | `PROJECT_BIBLE.md` §11 #10 + `BIBLE_AMENDMENTS.md` CP10 |
| manufacturers-lexicon canonical entries | `PROJECT_BIBLE.md` §2.1 |
| migration 0011 introduction of `ble_manufacturer_id` identifier type | `BIBLE_AMENDMENTS.md` CP14 |
| hard-rule set (§11) — source-url-direct provenance, PII discipline, promotion-gate provenance, confidence-band ceilings, Feist facts-only doctrine | `PROJECT_BIBLE.md` §11 |
| manufacturers-lexicon evolution amendments | `BIBLE_AMENDMENTS.md` CP3, CP4, CP10, SAR-9 |

---

## v1.4.0 — Wave I/I.5/I.6/I.7 cumulative attribution

This release integrates the vendor cloud-infrastructure hostname corpus (the Wave I corpus parent, `sources.id=66`; license_posture (verbatim `sources.notes.license_posture`): *"per_artifact_per_vendor"*) extracted across four autonomous sub-passes (Wave I main + I.5 deep extension + I.6 continuation + I.7 continuation). The following sources are admitted into the canonical lexicon for the first time at v1.4.0:

### Public certificate transparency

- **crt.sh** (`sources.id=54`; license_posture (verbatim `sources.notes.license_posture`): *"public_ct_log_observations"*) — public Certificate Transparency log aggregator (Sectigo). 11,551 hostname attestations across 51 canonical vendors via RFC 6962 public CT log observation. https://crt.sh/

### Public archive

- **Internet Archive Wayback Machine — CDX** (`sources.id=55`; license_posture (verbatim `sources.notes.license_posture`): *"archive_org_public_index"*) — temporal hostname-historical attestation. https://web.archive.org/cdx/

### Vendor first-party

- **GitHub vendor-organization content** (`sources.id=56`; license_posture (verbatim `sources.notes.license_posture`): *"per_repo"*) — raw README + source-file content from vendor-owned GitHub organizations per published LICENSE; 21 surviving Wave I hostname attestations post-scrub. https://github.com/

### Regional Internet Registries (infrastructure admission)

- **ARIN** (`sources.id=57`; license_posture (verbatim `sources.notes.license_posture`, shared by all five RIRs): *"public_internet_registry"*) — RDAP (North America). https://rdap.arin.net/registry/
- **RIPE NCC** (`sources.id=58`) — RDAP (Europe/Middle East/Central Asia). https://rdap.db.ripe.net/
- **APNIC** (`sources.id=59`) — RDAP (Asia-Pacific). https://rdap.apnic.net/
- **LACNIC** (`sources.id=60`) — RDAP (Latin America/Caribbean). https://rdap.lacnic.net/
- **AFRINIC** (`sources.id=61`) — RDAP (Africa). https://rdap.afrinic.net/

(All 5 admitted with 0 observations this cycle — Wave I class G halted with `url_pattern_issue` carry-forward; admission provides infrastructure for Wave I-prime ASN-prefix observation.)

### Public package registries

- **npm Registry** (`sources.id=62`; license_posture (verbatim `sources.notes.license_posture`): *"per_package"*) — https://registry.npmjs.org/
- **PyPI** (`sources.id=63`; license_posture (verbatim `sources.notes.license_posture`): *"per_package"*) — https://pypi.org/
- **RubyGems** (`sources.id=64`; license_posture (verbatim `sources.notes.license_posture`): *"per_gem"*) — https://rubygems.org/

### Vendor public cloud-storage payload

- **Honeywell firmware bucket (CT40 Android OTA)** (`sources.id=65`; license_posture (verbatim `sources.notes.license_posture`): *"vendor_open_bucket_observation"*) — `honeywell-firmware` public S3-class bucket payload providing CT40-O / CT40-P firmware ZIPs containing `META-INF/com/android/otacert` Honeywell-signed OTA certificates. Subject DN `O=Honeywell International Inc., OU=ACS, CN=Honeywell CodeSign RSA CA`. Single confirmed bucket admission per SAR-13.5 attribution-gate-binding methodology.

### Acknowledgements

The 568 NXDOMAIN-verified deprecated hostnames (565 promoted into canonical at v1.4.0) are attribution anchors retained per CP29 §1's `vendor_controlled_hostname_deprecated` value class — these hostnames were once publicly resolvable vendor infrastructure and now stand as historical attribution + supersession-chain pivots. Source: Wave I.6 sub-pass 7 `deprecated_hostname_verified.json`.

The §8.3 lift framework's 108 v1.4.0 applications (anchored against `wave_i_lift_candidates_synthesis.json` from Wave I.7 sub-pass 15) honor CP24 cross-source independence: lifts apply only when ≥2 distinct extraction source-classes from genuinely independent providers corroborate the hostname.
