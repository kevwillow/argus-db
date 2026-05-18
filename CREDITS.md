# Argus — Upstream Attribution and Credits

Argus integrates data derived from 52 upstream sources (canonical registries, procurement data, public-records databases, academic research, community-research repositories, vendor-published documentation, international corporate registries, US state Secretary-of-State registries, judicial filings, federal disclosure / entity-registration sources, and — new in v1.2.0 — the fccid.io community aggregator + the official FCC Equipment Authorization System Filings UI as a distinct primary surface) plus a canonical lexicon of 49 surveillance-technology vendors. This document attributes every upstream contribution, names the integration shape, and records license-carry-forward obligations downstream consumers must honor.

For the binding license terms, see [LICENSE](LICENSE) (AGPL-3.0-or-later — code), [LICENSE-DATA](LICENSE-DATA) (ODbL-1.0 — database), and [LICENSE-DOCS](LICENSE-DOCS) (CC-BY-SA-4.0 — documentation). The LICENSE-DATA §2.1 per-source license-posture taxonomy is the structural anchor for the source enumerations below.

---

## 1 — Tier 1 canonical registries (primary_registry)

These sources are authoritative allocation-class registries operated by standards bodies or regulatory authorities. Argus treats them as `source_type='primary_registry'` per the source-type confidence-band ceiling rule.

- **[IEEE OUI registry MA-L 24-bit](https://standards-oui.ieee.org/oui/oui.csv)** (sources.id=1) — IEEE-SA's canonical OUI allocation database (Organizationally Unique Identifier, 24-bit prefix). 39,355 raw observations contribute 54 promoted identifiers. Per-source attribution: [IEEE Standards Association](https://standards.ieee.org/products-services/regauth/oui/).
- **[IEEE OUI-28 registry MA-M 28-bit](https://standards-oui.ieee.org/oui28/mam.csv)** (sources.id=2) — MA-M (Medium) sub-allocations. 12,779 raw observations contribute 6,309 promoted identifiers.
- **[IEEE OUI-36 registry MA-S 36-bit](https://standards-oui.ieee.org/oui36/oui36.csv)** (sources.id=3) — MA-S (Small) sub-allocations. 13,999 raw observations contribute 6,947 promoted identifiers.
- **[IEEE IAB registry (36-bit legacy)](https://standards-oui.ieee.org/iab/iab.csv)** (sources.id=35) — Individual Address Block registry (predecessor to MA-S). 4,575 raw observations contribute 4,534 promoted identifiers. Re-pulled 2026-05-13 for primary_registry-band canonicalization.
- **[FCC EAS Equipment Authorization Grantee Registrations](https://opendata.fcc.gov/resource/3b3k-34jp.csv)** (sources.id=7) — US Federal Communications Commission's grantee registry (50,153 corporate registrants). Indexed at `fcc_grantees` table; used as the alias-disambiguation registry for facts-only corporate-entity confirmation (multi-registry cross-check predicate).
- **[FAA UAS Remote-ID Public DOC API — DETAIL endpoint](https://uasdoc.faa.gov/api/v1/publicDOCRev/)** (sources.id=36) — US Federal Aviation Administration's ANSI/CTA-2063-A drone Remote ID prefix registry. 103 raw observations contribute 102 promoted identifiers. Canonical primary_registry re-pull.
- **[Bluetooth SIG company-identifier registry](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)** (sources.id=34) — Bluetooth SIG's canonical YAML of 2-byte company-ID allocations. 3,971 raw observations contribute 3,971 promoted `ble_manufacturer_id` identifiers (per migration 0011 schema introduction of the `ble_manufacturer_id` identifier type).
- **[UK Companies House](https://api.company-information.service.gov.uk/)** (sources.id=44) — UK government's authoritative registrar of UK companies under the Companies Act 2006. Used as the corporate-entity confirmation source for IEEE OUI / MA-M registrations whose registrant name lacks a recognized corporate suffix (Class B sustained holds). Per-row URL template: `https://find-and-update.company-information.service.gov.uk/company/{company_number}`. Endpoints used: `/search/companies`, `/company/{company_number}`. Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: `/officers`, `/persons-with-significant-control`. **License: Open Government Licence v3.0 (OGL-3.0)** — https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/. Attribution string: *"This information is licensed under the terms of the Open Government Licence v3.0 — https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"*. Admitted via session `uk_companies_house_admission` (handoff package at `extraction_outputs/uk_ch_admission/HANDOFF_TO_VALIDATOR.md`); MAC-170 P2 promotion cycle landed 1 identifier (Johnson Matthey PLC #00033774).

**License posture:** primary_registry sources are factual public-allocation data. IEEE/FAA/Bluetooth SIG/FCC EAS carry no copyright carry-forward chain (per-source attribution at the `sources` table + per-row in `identifiers.source_url`); the UK Companies House row additionally carries OGL-3.0 attribution-required posture downstream (the attribution string above must accompany any downstream redistribution of UK CH-derived identifier rows). Database-rights regime jurisdictions (EU sui generis): the registries themselves are protected; Argus's compiled extraction is governed by Argus's ODbL-1.0 compilation license per LICENSE-DATA.

### v1.1.0 additions — US state Secretary-of-State registries (primary_registry, operator_manual_only)

Three US-state corporate registries were admitted in v1.1.0 as `primary_registry` sources under the new `access_mode='operator_manual_only'` convention (CP23): the source surfaces are structurally hostile to automation (CAPTCHA / Incapsula bot-challenge / paid-tier auth), so lookups happen via operator-driven browser sessions queued on the consolidated `extraction_outputs/us_state_sos_admission/operator_manual_queue.json`. Per-row provenance discipline and confidence-band ceilings are identical to automated sources — `access_mode` is a mechanism descriptor, not a quality signal.

- **[Delaware Division of Corporations](https://icis.corp.delaware.gov/Ecorp/EntitySearch/NameSearch.aspx)** (sources.id=45) — Delaware Secretary of State's Division of Corporations ICIS public entity-search portal. `source_type='primary_registry'`; `access_mode='operator_manual_only'` (CAPTCHA on `NameSearch.aspx`). Per-row URL template: `https://icis.corp.delaware.gov/Ecorp/EntitySearch/Details.aspx?FileNumber={file_number}`. Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: registered-agent / officer-director / shareholder-member lookups. **License: US_STATE_PUBLIC_RECORDS** (Delaware Code Title 8 §374; Title 29 Chapter 100 — Delaware FOIA). Attribution string (verbatim from `sources.notes.license_attribution`): *"Delaware public corporate records under Title 8 of the Delaware Code; public records under the Delaware Freedom of Information Act (Title 29 Chapter 100). No license-restricted reuse."* Admitted via session `us_state_sos_admission` (dispatch MAC-173; admission_date_utc `2026-05-16T23:57:07Z`). **Why included:** Delaware is the dominant US corporate-domicile jurisdiction for surveillance-vendor LLCs and US public companies; admission registers the source with `operator_manual_only` posture pending CAPTCHA workaround so per-row lookups can be queued without violating the §11 #3 automated-access discipline.
- **[California Secretary of State — Bizfile](https://bizfileonline.sos.ca.gov/)** (sources.id=46) — California Secretary of State's Bizfile Online business-entity search. `source_type='primary_registry'`; `access_mode='operator_manual_only'` (Incapsula/Imperva anti-bot wall). Per-row URL template: `https://bizfileonline.sos.ca.gov/search/business?filter%5Bentity_number%5D={entity_number}`. The posture may relax under registered API-key access (`CA_BIZFILE_API_KEY`) per `state_sos_access_mode_admission_addendum.md` §3.2 — not provisioned this cycle. Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: registered-agent / officer-director / shareholder-member lookups. **License: US_STATE_PUBLIC_RECORDS** (California Government Code §6253). Attribution string: *"California public corporate records under Government Code §6253 (California Public Records Act). No license-restricted reuse."* Admitted via session `us_state_sos_admission` (dispatch MAC-173; admission_date_utc `2026-05-16T23:57:07Z`). **Why included:** California is the dominant west-coast incorporation jurisdiction for surveillance-technology vendors (Flock Safety, Vigilant Solutions, Rekor regional subsidiaries, BriefCam, Skydio); admission reserves the relaxation path to `automated_with_auth` once the optional API key is provisioned.
- **[Texas Secretary of State SOSDirect](https://direct.sos.state.tx.us/)** (sources.id=47) — Texas Secretary of State SOSDirect business-entity search. `source_type='primary_registry'`; `access_mode='operator_manual_only'` (302 redirect on anonymous GET; paid SOSDirect tier required for non-trivial queries). Per-row URL template: TBD — TX SoS does not expose stable per-entity URLs (operator captures search-result-detail URL at lookup time). Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: registered-agent / officer-director / shareholder-member lookups. **License: US_STATE_PUBLIC_RECORDS** (Texas Business Organizations Code Chapter 22; Texas Government Code §552 — Public Information Act). Attribution string: *"Texas public business records under Business Organizations Code Chapter 22; public records under the Texas Government Code §552 (Public Information Act). No license-restricted reuse."* Admitted via session `us_state_sos_admission` (dispatch MAC-173; admission_date_utc `2026-05-16T23:57:07Z`). **Why included:** Texas is the dominant south-central US incorporation jurisdiction (Axon historical operations, body-cam OEMs, regional ALPR resellers); paid-tier-auth flagged as the relaxation precondition for any future automated access.

### v1.1.0 additions — Judicial filings, disclosure filings, and procurement disclosures (new source_type classes)

Three new `source_type` enum values were admitted in v1.1.0 via migration 0020 (CP23): `judicial_filing`, `disclosure_filing`, and `procurement_disclosure`. These distinguish judicial-record sources, regulatory disclosure-document sources, and vendor-side entity-registration disclosure sources from the existing 10-value enum bands. See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for the full 13-value roster; see [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) CP23 for the §-finding rationale.

- **[CourtListener / RECAP (Free Law Project)](https://www.courtlistener.com/)** (sources.id=48) — Free Law Project's open-access mirror of US federal court filings (RECAP archive of PACER documents + CourtListener-curated dockets and opinions). `source_type='judicial_filing'` (new source-type class admitted this release); `access_mode='automated_with_auth'` (Bearer token mandatory — anonymous tier revoked 2026-05-16). Per-row stable URL templates: `https://www.courtlistener.com/docket/{docket_id}/`, `/opinion/{opinion_id}/`, `/recap-document/{rd_id}/`. Endpoints used: `/api/rest/v4/courts/`, `/api/rest/v4/search/?type=r&q=...`. Endpoints explicitly avoided per §11 #3 + §7.5 PII discipline: `/api/rest/v4/people/`, `/api/rest/v4/judges/`, `/api/rest/v4/audio/`. Rate limit observed: 5 search requests per 60-second window (authenticated tier); self-paced at 13s/search-call. Auth handling: Bearer token loaded from `argus/.env/.env`; value never logged; length-only verification (40 chars). Yield this cycle: 47 search calls; 391 filings across 34 vendors searched; promotion outcome 0 identifiers / 0 procurement_records this dispatch (the cycle was structurally a discovery + disambiguation pass). Cycle surfaced two candidate FP-class findings staged at `notes.candidate_findings_for_future_cp_or_sar[]`: `rico_co_defendant_not_customer_relationship` and `court_filing_fee_not_contract_value`; both helped cycle composition reach n=4 for CP26 §8 codification. **License: CC0-1.0** (Free Law Project metadata dedication). Attribution string: *"Free Law Project releases CourtListener metadata under CC0-1.0. Underlying federal court filings are public records (Feist + 17 USC §105 for US government works)."* Admitted via session `courtlistener_admission` (dispatch MAC-174; admission_date_utc `2026-05-17T03:55:52Z`). **Why included:** CourtListener / RECAP is the canonical open-access mirror of federal-court filings against surveillance-technology vendors; admission enables litigation-based corroboration of vendor/customer relationships and surfaces FP-class findings that strengthen the §5.2 source_excerpt-must-support-claim discipline. (Cross-listed in §5 below as a community-research Tier-1 organization — Free Law Project is a 501(c)(3) non-profit, parallel to the EFF treatment in §2.)
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

- **[fccid.io](https://fccid.io/)** (sources.id=51) — a third-party aggregator of US FCC Equipment Authorization System filings. fccid.io mirrors the FCC's public filings catalog with a more navigable surface than the official `apps.fcc.gov` UI. `source_type='crowdsourced'` (tier 2); `access_mode='automated_html_parse'`. Per-row URL template: `https://fccid.io/{grantee_code}-{product_code}`. **License: NO_LICENSE_DECLARED** — the upstream aggregator carries no declared license. Argus extracts identifier facts (FCC ID values, grantee-code linkages, product-code linkages) under the *Feist v. Rural Telephone Service* (499 U.S. 340 (1991)) facts-not-copyrightable doctrine; compilation arrangement (the aggregator's per-page layout, navigation structure, selection-and-organization) is NOT republished. Per-promoted-row sentinel: `identifiers.notes.upstream_license_posture='NO_LICENSE_DECLARED'` (canonical sentinel-key). Yield this cycle: 671 raw_observations staged as discovery rows under the dual-citation-pair pattern; promotion deferred to the async FCC.gov re-citation pass (citation half pending). Admitted via session `fccid_io_admission` (dispatch MAC-101; admission_date_utc `2026-05-18T04:27:14Z`). **Why included:** fccid.io is the dominant community surface for navigating FCC EAS filings; its discovery shape (one URL per `{grantee_code}-{product_code}`) lets the validator's async re-citation pass shortcut FCC.gov navigation from a 5-step lookup to a 1-step lookup when the discovery row carries the opportunistic `fcc_grant_ids[]` enrichment field (564 of 671 queue rows do).
- **[FCC Equipment Authorization System — Filings](https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm)** (sources.id=52) — the official FCC EAS Filings UI. Distinct from the existing FCC EAS Grantee Registrations data file (sid=7); the Filings UI gives per-FCC-ID filing surfaces (test reports, internal photos, RF exposure data) that the grantee CSV doesn't expose. `source_type='regulatory'` (tier 1); `access_mode='automated_html_parse'`. **License: PUBLIC_DOMAIN** (US government work product per 17 USC §105). Attribution string: *"FCC Equipment Authorization System filings are US government records and are not copyrightable per 17 USC §105."* Admitted under a degraded-mode posture: at MAC-101 extraction time, FCC.gov egress was unreachable from the runtime host (Akamai-edge HTTP/2 INTERNAL_ERROR across `apps.fcc.gov`), so the source row was admitted (the source EXISTS) but the citation-half of the 671 discovery rows was deferred to an asynchronous re-citation pass. The source exists; the citation rows accumulate when egress is restored. Admitted via session `fccid_io_admission` (dispatch MAC-101; admission_date_utc `2026-05-18T04:27:14Z`). **Why included:** the official primary surface for FCC ID filing material (test reports, photos, RF exposure data) — distinct from the grantee-registration CSV; the dual-citation-pair pattern (sid=51 discovery → sid=52 citation) is the bible-canon shape for aggregator-paired-with-regulator source admissions.

**License-attribution carry-forward summary (v1.2.0 additions):** NO_LICENSE_DECLARED (sid 51 fccid.io) inherits the Feist facts-only regime per §6 below — `identifiers.notes.upstream_license_posture='NO_LICENSE_DECLARED'` on every promoted row; downstream consumers redistributing Argus's database content inherit the same facts-only posture. PUBLIC_DOMAIN (sid 52 FCC EAS Filings) carries no attribution-required obligation per 17 USC §105; per-row `apps.fcc.gov` source_url citation discipline applies once the async re-citation pass drains the deferred queue.

### v1.2.0 admission ledger summary

| sid | Name | source_type | License | access_mode | admission_date_utc |
|---|---|---|---|---|---|
| 51 | fccid.io | crowdsourced | NO_LICENSE_DECLARED | automated_html_parse | 2026-05-18T04:27:14Z |
| 52 | FCC Equipment Authorization System — Filings | regulatory | PUBLIC_DOMAIN | automated_html_parse (degraded_mode_admission) | 2026-05-18T04:27:14Z |

---

## 2 — Tier 1/2 public-records and procurement data

- **[EFF Atlas of Surveillance](https://atlasofsurveillance.org/)** (sources.id=5) — Electronic Frontier Foundation + UNLV Reynolds School of Journalism's collaborative deployment-mapping project. 15,071 `deployment_observations` rows. **License: CC-BY-NC-SA-4.0**. **DOWNSTREAM COMMERCIAL CAUTION:** the NC (NonCommercial) clause prohibits commercial redistribution of these rows or their derivatives. See LICENSE-DATA §2.1 + §4.1 for the per-row LICENSE column quarantine mechanism. Non-commercial / research / journalist use is licensed.
- **[DeFlock](https://deflock.me/)** (sources.id=6) — Community-curated ALPR camera location database, OSM-mirrored via `cdn.deflock.me`. 101,597 `deployment_observations` rows. **License: ODbL-1.0**. Compatible with Argus's ODbL-1.0 compilation license. ShareAlike applies to derivative databases.
- **[USAspending.gov](https://api.usaspending.gov/api/v2/search/spending_by_award/)** (sources.id=8) — US federal procurement award database (public domain). 46,043 `procurement_records` rows (43,483 at v1.0.0; +2,560 net-new via the v1.1.0 deep-extension session `usaspending_deep_admission` MAC-172). The deep-extension cycle fanned out across the full 34-vendor canonical lexicon (extending the v1.0.0 narrative-extracted scope which was limited to 5–6 SEC-filing vendors via SEC EDGAR RG5); covered 2021-01-01 through 2026-05-16 with award type codes A/B/C/D; total net-new federal award value covered USD $2,095,345,219.58. The v1.1.0 SAM.gov admission cycle (MAC-175, sources.id=50) landed an additional +9,623 cross-source corroboration UPDATEs against existing USAspending rows per §5.2 cross-source confidence-lift discipline.
- **[Granicus Legistar Web API](https://webapi.legistar.com/v1/)** (sources.id=10) — municipal legislative-matter retrieval across 5 token-free starting-batch clients (chicago, sfgov, detroit, hampton, cabq). 3 `council_minutes_matters` rows. Each row sources to a specific municipality's public-records system; per-row attribution at `notes.source_url`. License: public records under FOIA / state public-records statutes.
- **[Wireshark `manuf` file](https://www.wireshark.org/download/automated/data/manuf)** (sources.id=4) — community-maintained OUI vendor-name file. 57,009 raw observations; primarily a vendor-name curation cross-reference. License: GPL-2.0-or-later (Wireshark itself); the OUI data file is informationally derived from IEEE public registries.
- **[WiGLE.net wireless network database](https://api.wigle.net/api/v2/network/search)** (sources.id=9) — community-contributed wireless network observations. 100 raw observations staged at v1.0.0 (pipeline built; DRY_RUN ON pending operator-side credential gating). Future-enrichment hook.

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
| 15 | [NSM-Barii/flock-back](https://github.com/NSM-Barii/flock-back) | | per repo LICENSE |
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

## 7 — Surveillance-technology vendor lexicon (manufacturers table; 49 canonical entries)

The `manufacturers` table is the canonical lexicon of surveillance-technology vendors used as the Tier-2/3 device_category inference allowlist. Each entry contributes vendor attribution to identifier rows. This is NOT a data source in the registry sense above; it's an internal curated lexicon used at promotion time. Listed alphabetically:

| Vendor | Canonical category |
|---|---|
| Aerodome | drone |
| Autel Robotics | drone |
| Avigilon | alpr |
| Axis Communications | alpr |
| Axon | body_cam |
| Berla | hacking_tool |
| BluePoint Alert | (uncategorized — documented_absence stub admission, v1.2.0) |
| BriefCam | face_recog |
| BRINC | drone |
| Cellebrite | hacking_tool |
| Cisco Meraki | (uncategorized — positive-extraction admission, v1.2.0) |
| Clearview AI | face_recog |
| Coban Technologies | body_cam |
| Cradlepoint | (uncategorized — multi-purpose-vendor carveout) |
| Dahua | (uncategorized — positive-extraction admission with NDAA §889 note, v1.2.0) |
| Dedrone | drone_detect |
| Digital Ally | body_cam |
| Digital Receiver Technology | imsi_catcher |
| DJI | drone |
| DroneShield | drone_detect |
| Engility | imsi_catcher |
| Flock Safety | alpr |
| Genetec | alpr |
| Getac | body_cam |
| Hak5 | hacking_tool |
| Harris | imsi_catcher |
| Hikvision | (uncategorized — positive-extraction admission with NDAA §889 note, v1.2.0) |
| Honeywell | (uncategorized — documented_absence stub admission, v1.2.0) |
| Jacobs | imsi_catcher |
| Johnson Matthey PLC | (uncategorized — v1.1.0 closed Class B hold via UK Companies House #00033774; chemistry/precious-metals; no surveillance-adjacency) |
| Kenwood | police_radio |
| KeyW | imsi_catcher |
| L3Harris | (uncategorized — multi-purpose-vendor) |
| Lenel | (uncategorized — documented_absence stub admission, v1.2.0) |
| Magnet Forensics | hacking_tool |
| Motorola Solutions | (uncategorized — multi-purpose-vendor carveout) |
| Parrot | drone |
| PIPS Technology | alpr |
| Rekor | alpr |
| Reveal | body_cam |
| Septier | imsi_catcher |
| Sierra Wireless | (uncategorized — multi-purpose-vendor) |
| Skydio | drone |
| SoundThinking (ShotSpotter) | gunshot_detect |
| Utility Inc | body_cam |
| Verkada | (uncategorized — documented_absence stub admission, v1.2.0) |
| Vigilant Solutions | alpr |
| WatchGuard | body_cam |
| Wolfcom | body_cam |

**v1.2.0 lexicon additions (14 vendors, from 35 to 49):** 4 positive-extraction admissions from the MAC-104 Wave-G v2 PlayStore companion-app extraction pass — **Hikvision** and **Dahua** (both admitted with NDAA Section 889 note: state/local LE deployments persist outside the federal-procurement bar), **Autel Robotics**, and **Cisco Meraki**. 10 stub admissions from absence-investigation cycles (apk-pure 404 + apk-mirror "no results" + cohort-prediction reasoning) — **Verkada, Honeywell, Lenel, BluePoint Alert, PIPS Technology, Wolfcom, Utility Inc, Coban Technologies, Digital Ally, Aerodome** — each carries `notes.admission_basis='documented_absence_only'`.

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
- **Per-identifier `notes.upstream_license_posture`**: NO_LICENSE_DECLARED facts-only sources (`sources.id` 39, 42; 27 promoted rows total; plus sid 51 fccid.io v1.2.0 admission carrying 671 raw_observations staged but not yet promoted pending the async FCC.gov re-citation pass) inherit the Feist regime — derivatives operate under Feist facts-not-copyrightable; no upstream license obligation.
- **AGPL-3.0 source attribution** (`sources.id` 38, 40, 43, plus the implicit AGPL inheritance pattern in Argus's own code per LICENSE): research-derived factual claims do NOT trigger AGPL-3.0 copyleft; redistribution of the upstream compilation arrangement WOULD trigger it (and Argus does NOT republish such arrangements).
- **CC-BY-NC-ND-4.0 source attribution** (`sources.id=41` GainSec anti-crime-ecosystem-research): derivative-modification restricted per the ND clause; research-use clause permits Argus's factual extraction; downstream derivative-modification consumers must evaluate the ND clause separately.

For sources-row metadata discrepancy callout (sources 1/2/3/7 carry a historical `source_type='regulatory'` vestige; identifiers-row data is correctly labeled `primary_registry`): see [LICENSE-DATA §4.4](LICENSE-DATA) and [README.md](README.md).

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
