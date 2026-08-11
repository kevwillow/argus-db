# Argus: Upstream Attribution and Credits

Argus is built from public data. It draws on **74 upstream sources** and tracks a curated list of **126 surveillance-technology vendors**. This file credits every source, explains in plain terms what Argus took from it, and records the license rules that anyone reusing Argus data has to follow.

Three licenses govern the project. The code is licensed under [AGPL-3.0-or-later](LICENSE). The database and dataset exports are licensed under [ODbL-1.0](LICENSE-DATA). The documentation is licensed under [CC-BY-SA-4.0](LICENSE-DOCS). Some individual sources add their own attribution or reuse rules on top of these. Where they do, the rule is spelled out next to the source below and again in the "Reusing Argus data" section near the end.

For a plain-language tour of what Argus is and how to use the exports, see the [User Guide](docs/USER_GUIDE.md). This file is the legal-and-attribution surface, so it is denser than the guide.

---

## How to read this document

The document has two halves.

The **data sources** half names every upstream dataset Argus integrates and records the reuse rules for each one. Sources fall into a few plain groups: official allocation registries, court and disclosure records, equipment-authorization filings, deployment maps, academic research, vendor documentation, and community-research repositories.

The **vendor list** half names the 126 surveillance-technology companies Argus tracks. A company earns a place on the list only when real evidence ties it to surveillance equipment, such as a radio-equipment authorization, a hardware-address allocation, or a corporate-disclosure filing. Argus never invents an entry.

A few things worth knowing before you read:

- **Some big companies make far more than surveillance gear.** Northrop Grumman, Lockheed Martin, Trimble, and Bosch Security Systems all sell surveillance-adjacent products alongside large unrelated product lines. Argus lists these as `unknown` rather than forcing them into one surveillance category, and it leaves them out of the high-confidence Lynceus export. Pointing a scanner at a Lockheed hardware-address prefix would produce a flood of false matches.
- **Subsidiaries are listed under their parent.** When a company owns a subsidiary with its own surveillance product line, Argus records the subsidiary as a separate row tied back to the parent, and hides it from the default vendor view. Eight of the 126 entries are subsidiary rows of this kind. They are listed at the foot of the vendor table.

---

## The data sources

### Official allocation registries

These are the authoritative registries run by standards bodies and regulators. They publish factual allocation data, so they carry no copyright chain. Argus cites each one per row through the source URL.

- **[IEEE OUI registry, MA-L 24-bit](https://standards-oui.ieee.org/oui/oui.csv)**: the IEEE Standards Association's master list of 24-bit hardware-address prefixes (Organizationally Unique Identifiers). Attribution: [IEEE Standards Association](https://standards.ieee.org/products-services/regauth/oui/).
- **[IEEE OUI-28 registry, MA-M 28-bit](https://standards-oui.ieee.org/oui28/mam.csv)**: the medium (28-bit) sub-allocation blocks.
- **[IEEE OUI-36 registry, MA-S 36-bit](https://standards-oui.ieee.org/oui36/oui36.csv)**: the small (36-bit) sub-allocation blocks.
- **[IEEE IAB registry](https://standards-oui.ieee.org/iab/iab.csv)**: the Individual Address Block registry, the predecessor to the small blocks above.
- **[FCC Equipment Authorization grantee registrations](https://opendata.fcc.gov/resource/3b3k-34jp.csv)**: the US Federal Communications Commission's registry of equipment-authorization grantees, used to confirm corporate identities. Note one limit: this bulk dataset is frozen at 2021-03-22, so any grantee registered after that date is missing. Treat its coverage as a March 2021 snapshot.
- **[FAA UAS Remote-ID public registry](https://uasdoc.faa.gov/api/v1/publicDOCRev/)**: the US Federal Aviation Administration's registry of drone Remote ID prefixes.
- **[Bluetooth SIG company-identifier registry](https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/company_identifiers/company_identifiers.yaml)**: the Bluetooth SIG's master list of two-byte company-ID allocations.
- **[Wireshark `manuf` file](https://www.wireshark.org/download/automated/data/manuf)**: a community-maintained file matching hardware-address prefixes to vendor names, derived from the IEEE registries above. Argus uses it mainly to cross-check vendor names. It also surfaced three cases where IEEE and Wireshark disagreed on a vendor after an acquisition (for example, the prefix `00:03:74` now reads Schneider Electric, formerly Control Microsystems). Wireshark itself is licensed GPL-2.0-or-later; the data file is informational and derived from the public IEEE registries.
- **[UK Companies House](https://api.company-information.service.gov.uk/)**: the UK government's official register of companies. Argus uses it to confirm corporate identities behind hardware-address registrations whose registrant name lacks a clear corporate suffix. To protect privacy, Argus never reads the officer, significant-control, or shareholder endpoints. **License: Open Government Licence v3.0 (OGL-3.0).** If you redistribute rows derived from this source, carry this exact attribution:

  ```
  "This information is licensed under the terms of the Open Government Licence v3.0 — https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
  ```

Three US state corporate registries are also registered, but their websites block automated access through CAPTCHAs, bot walls, or paid tiers. Lookups against them happen by hand through an operator-driven browser session, never by automation. The privacy rule is the same: no officer, agent, or shareholder lookups.

- **[Delaware Division of Corporations](https://icis.corp.delaware.gov/Ecorp/EntitySearch/NameSearch.aspx)**: Delaware is the dominant US incorporation state for surveillance-vendor companies, so its public register matters. **License: US state public records** (Delaware Code Title 8 §374; Title 29 Chapter 100, Delaware FOIA). No reuse restriction.
- **[California Secretary of State, Bizfile](https://bizfileonline.sos.ca.gov/)**: California is the leading west-coast incorporation state for surveillance-technology vendors such as Flock Safety, Vigilant Solutions, BriefCam, and Skydio. **License: US state public records** (California Government Code §6253). No reuse restriction.
- **[Texas Secretary of State, SOSDirect](https://direct.sos.state.tx.us/)**: Texas is a leading south-central incorporation state for body-camera makers and regional license-plate-reader resellers. **License: US state public records** (Texas Business Organizations Code Chapter 22; Texas Government Code §552). No reuse restriction.

### Court records, disclosures, and procurement data

- **[CourtListener and RECAP (Free Law Project)](https://www.courtlistener.com/)**: the Free Law Project's open mirror of US federal court filings. Argus uses it to corroborate vendor and customer relationships through litigation, and it never reads the people, judge, or audio endpoints. **License: CC0-1.0** for the Free Law Project metadata; the underlying court filings are public records. No attribution is required, though Argus still cites each row by URL.
- **[SEC EDGAR](https://www.sec.gov/cgi-bin/browse-edgar)**: the US Securities and Exchange Commission's repository of public-company disclosure filings, the canonical source for named-government-customer claims about publicly-traded vendors such as Axon, Motorola Solutions, Rekor, and Cellebrite. Argus stays out of insider-transaction and benefit-plan filings. **License: public domain** (17 USC §105).
- **[SAM.gov entity registration](https://api.sam.gov/entity-information/v3/entities)**: the US government's official registry of vendors eligible for federal awards, which lets Argus tie procurement records together by a common vendor key. **License: public domain** (17 USC §105).
- **[USAspending.gov](https://api.usaspending.gov/api/v2/search/spending_by_award/)**: the US federal procurement award database, cross-referenced against the SEC and SAM.gov records above. **License: public domain.**
- **[Granicus Legistar Web API](https://webapi.legistar.com/v1/)**: municipal legislative records from a small starting set of cities (Chicago, San Francisco, Detroit, Hampton, Albuquerque). Each record cites its city's public-records system. License: public records.

### FCC equipment-authorization filings

These two work as a pair. The first is an easy-to-navigate community mirror; the second is the official regulator surface that Argus treats as the citation of record.

- **[fccid.io](https://fccid.io/)**: a third-party mirror of FCC equipment-authorization filings, easier to browse than the official site. **License: none declared.** Argus extracts only the underlying facts (FCC ID values and their grantee and product-code links) under the *Feist v. Rural Telephone Service* doctrine, which holds that facts cannot be copyrighted. It does not republish the site's layout or organization. Every row derived from this source carries the marker `upstream_license_posture='NO_LICENSE_DECLARED'`, and downstream users inherit the same facts-only footing.
- **[FCC Equipment Authorization System filings](https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm)**: the official FCC filings interface, which exposes per-device test reports, photos, and RF-exposure data that the grantee dataset does not. **License: public domain** (17 USC §105). The FCC site was unreachable from the build host at admission time, so the source is registered and its citations are filled in as access is restored.

### Deployment maps and public-records databases

- **[EFF Atlas of Surveillance](https://atlasofsurveillance.org/)**: a deployment-mapping project from the Electronic Frontier Foundation and the UNLV Reynolds School of Journalism. Argus holds **15,071 deployment observations** from it. **License: CC-BY-NC-SA-4.0.** **Commercial caution:** the NonCommercial clause forbids commercial redistribution of these rows or anything derived from them. Non-commercial, research, and journalist use is allowed. See [LICENSE-DATA](LICENSE-DATA) for the per-row license tag that enforces this.
- **[DeFlock](https://deflock.me/)**: a community-curated database of license-plate-reader camera locations, mirrored from OpenStreetMap. Argus holds **101,597 deployment observations** from it. **License: ODbL-1.0**, which is compatible with Argus's own database license; the ShareAlike term applies to derivative databases. DeFlock is a thin front end over OpenStreetMap, so the data layer is OpenStreetMap's. If you redistribute DeFlock-derived rows, carry this exact attribution:
  > "© OpenStreetMap contributors. Data available under the Open Database License (ODbL) 1.0. https://www.openstreetmap.org/copyright"
- **[WiGLE.net](https://api.wigle.net/api/v2/network/search)**: a community wireless-network database. The pipeline is built but the source is staged, not yet drawn on. It waits behind operator-provided credentials and a later phase of the project.

### Academic research

- **[Marlin: Detecting IMSI-Catchers by Characterizing Identity Exposing Messages in Cellular Traffic](https://www.ndss-symposium.org/wp-content/uploads/2025-1115-paper.pdf)**: a paper from the 2025 Network and Distributed System Security (NDSS) Symposium. It is the foundation for Argus's cell-site-simulator behavioral signatures. Argus tracks **201 behavioral signatures** in total, built from this paper and adjacent community research. Credit the paper by its academic citation.
- **[RUB-SysSec/DroneSecurity](https://github.com/RUB-SysSec/DroneSecurity)**: DJI Drone-ID research from the Ruhr-University Bochum Systems Security Group. **License: AGPL-3.0.** That copyleft obligation only applies if you redistribute the upstream project's own arrangement, which Argus does not do; Argus keeps only the extracted facts.
- **[GainSec/anti-crime-ecosystem-research](https://github.com/GainSec/anti-crime-ecosystem-research)**: a white paper analyzing surveillance-device firmware, anchored on published CVEs. **License: CC-BY-NC-ND-4.0 with a research-use clause.** Commercial and derivative-modification use is restricted; research and educational use is allowed.

### Vendor documentation and companion apps

Argus reads publicly-downloadable vendor material to extract embedded hardware identifiers, default credentials, and pairing-protocol values. It never republishes decompiled vendor source code, and the raw app and firmware binaries are kept out of the repository.

- **[Hak5 product documentation](https://docs.hak5.org/)**: vendor-published product reference material.
- **[Flock Safety FS Installer](https://apkpure.com/flock-safety-device-app/com.flocksafety.hazyhiwire)**: the Flock Safety companion app, analyzed for embedded Bluetooth identifiers and pairing values.
- **[Getac BWC Viewer](https://apkpure.com/getac-bwc-viewer/com.getac.android.mobileappBWC)**: the Getac body-camera companion app, analyzed for body-camera identifiers.
- **Vendor companion apps**: five more companion apps were added together under a shared analysis posture: Hikvision Hik-Connect, Dahua DMSS, Motorola Solutions WAVE PTT, Parrot FreeFlight 6, and DJI Industry Pilot. The Hikvision and Dahua entries carry a note that NDAA Section 889 bars these vendors from federal procurement, though state and local law-enforcement deployments continue.
- **Vendor desktop-application static analysis**: a methodology that examines publicly-downloadable vendor desktop software across Windows, macOS, and Linux. It covered Hikvision iVMS-4200 and two DJI Assistant builds, with FileZilla used as a control. Each binary's license posture is recorded per file under the facts-only rule.

### Community-research repositories

About two dozen community GitHub repositories contributed corroborating observations across drone Remote ID, Bluetooth tracker catalogs, cell-site-simulator detection, license-plate-reader profiles, and other surveillance categories.

| Repository | License |
|---|---|
| [0xXyc/flock-you-wifi-recon](https://github.com/0xXyc/flock-you-wifi-recon) | per repo LICENSE |
| [NSM-Barii/flock-back](https://github.com/NSM-Barii/flock-back) | **MIT** |
| [MaxwellDPS/Flock-You-Android](https://github.com/MaxwellDPS/Flock-You-Android) | per repo LICENSE |
| [judcrandall/lookout.py](https://github.com/judcrandall/lookout.py) | per repo LICENSE |
| [tesorrells/RF-Drone-Detection](https://github.com/tesorrells/RF-Drone-Detection) | per repo LICENSE |
| [opendroneid/opendroneid-core-c](https://github.com/opendroneid/opendroneid-core-c) | per repo LICENSE |
| [colonelpanichacks/flock-you](https://github.com/colonelpanichacks/flock-you) | per repo LICENSE |
| [colonelpanichacks/oui-spy](https://github.com/colonelpanichacks/oui-spy) | per repo LICENSE |
| [colonelpanichacks/Sky-Spy](https://github.com/colonelpanichacks/Sky-Spy) | per repo LICENSE |
| [alphafox02/DragonSync](https://github.com/alphafox02/DragonSync) | per repo LICENSE |
| [seemoo-lab/AirGuard](https://github.com/seemoo-lab/AirGuard) | per repo LICENSE |
| [opendroneid/receiver-android](https://github.com/opendroneid/receiver-android) | per repo LICENSE |
| [opendroneid/wireshark-dissector](https://github.com/opendroneid/wireshark-dissector) | per repo LICENSE |
| [cyber-defence-campus/RemoteIDReceiver](https://github.com/cyber-defence-campus/RemoteIDReceiver) | per repo LICENSE |
| [proto17/dji_droneid](https://github.com/proto17/dji_droneid) | per repo LICENSE |
| [nixxxo/tagfinder](https://github.com/nixxxo/tagfinder) | per repo LICENSE |
| [EFForg/rayhunter](https://github.com/EFForg/rayhunter) | per repo LICENSE |
| [eylonK14/IMSICatcherDetector](https://github.com/eylonK14/IMSICatcherDetector) | per repo LICENSE |
| [CellularPrivacy/AIMSICD](https://github.com/CellularPrivacy/AIMSICD) | per repo LICENSE |
| [GainSec/Flock-Safety-Trap-Shooter-Sniffer-Alarm](https://github.com/GainSec/Flock-Safety-Trap-Shooter-Sniffer-Alarm) | per repo LICENSE |
| [DeflockJoplin/flock-you](https://github.com/DeflockJoplin/flock-you) | AGPL-3.0 (inherited from upstream) |
| [EthanThePhoenix38/flock-you-camera-detector](https://github.com/EthanThePhoenix38/flock-you-camera-detector) | **no license declared** (facts-only; see below) |
| [FoggedLens/deflock-app](https://github.com/FoggedLens/deflock-app) | AGPL-3.0 |
| [GainSec/anti-crime-ecosystem-research](https://github.com/GainSec/anti-crime-ecosystem-research) | CC-BY-NC-ND-4.0 with research-use clause |
| [GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose](https://github.com/GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose) | **no license declared** (facts-only; see below) |

### Sources without a declared license

Three sources publish material openly but ship no license file: the EthanThePhoenix38 and GainSec firehose repositories above, plus fccid.io. Argus handles them under the *Feist v. Rural Telephone Service* doctrine, which holds that facts cannot be copyrighted.

What Argus takes: identifier values, vendor attributions, and a pinned source URL for each. What Argus leaves behind: any verbatim list snippet, repository structure, or selection and organization beyond a single-fact citation. Every promoted row carries the marker `upstream_license_posture='NO_LICENSE_DECLARED'`, and downstream users inherit the same facts-only footing.

### Cloud-infrastructure and certificate sources

A further group of sources supports vendor-infrastructure attribution: matching vendor-controlled hostnames, certificates, and network ranges.

- **[crt.sh](https://crt.sh/)**: a public Certificate Transparency log aggregator operated by Sectigo, used to attest vendor-controlled hostnames.
- **[Internet Archive Wayback Machine (CDX)](https://web.archive.org/cdx/)**: historical hostname records over time.
- **GitHub vendor-organization content**: README and source-file content published by vendor-owned GitHub organizations, used under each repository's own license.
- **Regional Internet Registries**: ARIN (North America), RIPE NCC (Europe, Middle East, and Central Asia), APNIC (Asia-Pacific), LACNIC (Latin America and the Caribbean), and AFRINIC (Africa), all queried through their public RDAP services. These are registered to support future network-range observation.
- **Public package registries**: the [npm Registry](https://registry.npmjs.org/), [PyPI](https://pypi.org/), and [RubyGems](https://rubygems.org/), each used under per-package licenses.
- **Honeywell firmware bucket**: a publicly-readable Honeywell firmware storage bucket that supplied signed over-the-air certificates confirming Honeywell's identity.

### Confirmed-exploitation reference

- **[CISA Known Exploited Vulnerabilities Catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)**: the US Cybersecurity and Infrastructure Security Agency's machine-readable catalog of vulnerabilities confirmed to be exploited in the wild. Argus uses it to corroborate exploit tooling attributed to offensive-tool and spyware vendors such as Candiru, NSO Group, and Cytrox/Intellexa. **License: public domain** (17 U.S.C. §105). The catalog's landing page blocks automated reads, so Argus ingests the published machine feed instead.

---

## The surveillance-vendor list

This is the curated list of 126 surveillance-technology companies Argus tracks. It is not a data source. Argus uses it to label identifier rows with a likely vendor and device category. A company is added only when real evidence attests to it.

The category codes are short labels. Here is what they mean:

| Code | Meaning |
|---|---|
| alpr | automatic license-plate reader |
| automotive_telematics | fleet and vehicle telematics |
| body_cam | body-worn camera |
| cctv_camera | video surveillance camera or video-management system |
| drone | drone or unmanned aircraft |
| drone_detect | counter-drone detection |
| face_recog | face recognition |
| gps_tracker | GPS tracking and electronic monitoring |
| gunshot_detect | gunshot detection |
| hacking_tool | mobile-forensic and offensive tooling |
| imsi_catcher | cell-site simulator (IMSI catcher) |
| network_surveillance | lawful-intercept and network surveillance |
| persistent_surveillance | wide-area or persistent surveillance |
| police_radio | land-mobile police radio |
| through_wall_radar | through-wall radar |
| unknown / (uncategorized) | multi-purpose vendor, or not yet categorized |

| Vendor | Category |
|---|---|
| Aaronia AG | drone_detect |
| AeroDefense | drone_detect |
| Aerodome | drone |
| Anduril Industries | drone_detect |
| AnyVision / Oosto | face_recog |
| Attenti | gps_tracker |
| Autel Robotics | drone |
| Axis Communications | cctv_camera |
| Axon | body_cam |
| Berla | hacking_tool |
| BI Incorporated | gps_tracker |
| Black Sage Technologies | drone_detect |
| BluePoint Alert | (uncategorized) |
| Bosch Security Systems | unknown |
| BriefCam | face_recog |
| BRINC | drone |
| CACI SkyTracker | drone_detect |
| Camero | through_wall_radar |
| Candiru | hacking_tool |
| Cellebrite | hacking_tool |
| Cisco Meraki | (uncategorized) |
| Citadel Defense | drone_detect |
| Clearview AI | face_recog |
| Coban Technologies | body_cam |
| Cognitec Systems | face_recog |
| Cognyte | network_surveillance |
| Compelson | hacking_tool |
| Cradlepoint | (uncategorized) |
| Cytrox / Intellexa | hacking_tool |
| D-Fend Solutions | drone_detect |
| Dahua | cctv_camera |
| DataWorks Plus | face_recog |
| Dedrone | drone_detect |
| Detego | hacking_tool |
| Digital Ally | body_cam |
| Digital Receiver Technology | imsi_catcher |
| DJI | drone |
| DroneShield | drone_detect |
| Eagle Eye Networks | cctv_camera |
| Echodyne | drone_detect |
| Elbit Systems of America | persistent_surveillance |
| Engility | imsi_catcher |
| Epirus Inc. | drone_detect |
| FaceFirst | face_recog |
| Flipper Devices Inc. | hacking_tool |
| Flock Safety | alpr |
| Fortem Technologies | drone_detect |
| Gamma Group | hacking_tool |
| General Atomics | persistent_surveillance |
| Genetec | alpr |
| Geotab | automotive_telematics |
| Getac | body_cam |
| Hacking Team / Memento Labs | hacking_tool |
| Hak5 | hacking_tool |
| Hanwha Vision | cctv_camera |
| Harris | imsi_catcher |
| Hidden Level Inc. | drone_detect |
| Hikvision | cctv_camera |
| Honeywell | (uncategorized) |
| Idemia | face_recog |
| Jacobs | imsi_catcher |
| Johnson Matthey PLC | (uncategorized) |
| Kenwood | police_radio |
| KeyW | imsi_catcher |
| L3Harris | (uncategorized) |
| Lenel | (uncategorized) |
| Liteye Systems | drone_detect |
| Lockheed Martin | unknown |
| Lytx | automotive_telematics |
| Magnet Forensics | hacking_tool |
| Milestone Systems | cctv_camera |
| Motive | automotive_telematics |
| Motorola Solutions | (uncategorized) |
| MSAB | hacking_tool |
| MyDefence Communications | drone_detect |
| NEC NeoFace | face_recog |
| NIITEK | through_wall_radar |
| Northrop Grumman | unknown |
| NSO Group | hacking_tool |
| Omnitracs | automotive_telematics |
| Oxygen Forensics | hacking_tool |
| Paravision | face_recog |
| Parrot | drone |
| Pen-Link | network_surveillance |
| Persistent Surveillance Systems | persistent_surveillance |
| PIPS Technology | alpr |
| Polaris Wireless | network_surveillance |
| QuaDream | hacking_tool |
| Rank One Computing | face_recog |
| Rekor | alpr |
| Reveal | body_cam |
| Rhombus Systems | cctv_camera |
| Robin Radar Systems | drone_detect |
| Rohde & Schwarz | imsi_catcher |
| Samsara | automotive_telematics |
| Sensofusion | drone_detect |
| Sentinel Offender Services | gps_tracker |
| Septier | imsi_catcher |
| Sierra Wireless | (uncategorized) |
| Skydio | drone |
| SoundThinking | gunshot_detect |
| SS8 Networks | network_surveillance |
| STOP | gps_tracker |
| TCOM | persistent_surveillance |
| TiaLinx | through_wall_radar |
| Tiandy | cctv_camera |
| Track Group | gps_tracker |
| Trimble | unknown |
| Trovicor | network_surveillance |
| Uniview | cctv_camera |
| Utility Inc | body_cam |
| Utimaco | network_surveillance |
| Verizon Connect | automotive_telematics |
| Verkada | cctv_camera |
| Vigilant Solutions | alpr |
| Vivotek | cctv_camera |
| WatchGuard | body_cam |
| Wolfcom | body_cam |

The eight subsidiary rows are hidden from the default view and listed here under their parent companies:

| Subsidiary | Category | Parent |
|---|---|---|
| Parrot Automotive | automotive_telematics | Parrot |
| Pelco | cctv_camera | Motorola Solutions |
| Avigilon | cctv_camera | Motorola Solutions |
| Grayshift | hacking_tool | Magnet Forensics |
| Anduril Anvil | drone_detect | Anduril Industries |
| Anduril Lattice OS | unknown | Anduril Industries |
| Anduril Roadrunner | drone_detect | Anduril Industries |
| Anduril Sentry Tower | persistent_surveillance | Anduril Industries |

Hikvision, Dahua, Uniview, and Tiandy carry a note that NDAA Section 889 bars them from federal procurement, while state and local law-enforcement deployments continue.

---

## Reusing Argus data: license carry-forward

If you build a derived dataset from Argus, honor the upstream license chain at every layer.

The whole compilation is licensed under ODbL-1.0, so standard ShareAlike and attribution terms apply to any derivative database. In jurisdictions with database rights, that protection extends to compilation-level derivatives.

Some rows carry their own per-row license tag that you must honor:

- **Atlas of Surveillance rows** are tagged CC-BY-NC-SA-4.0. Leave them out of any commercial derivative dataset, per the NonCommercial clause. Non-commercial, research, and journalist use is allowed.
- **DeFlock rows** are tagged ODbL-1.0, which is compatible with the Argus compilation; standard ShareAlike applies, and the OpenStreetMap attribution above travels with them.

Sources with no declared license inherit the facts-only footing under *Feist*: there is no upstream license obligation, since facts cannot be copyrighted. AGPL-3.0 research sources do not trigger copyleft on the factual claims Argus extracts, because Argus never republishes their original arrangement. The GainSec anti-crime-ecosystem-research paper adds a no-derivatives clause that downstream modifiers must evaluate on their own; its research-use clause covers Argus's factual extraction.

---

## Build authorship and contributors

Argus was built with a multi-agent approach under human operator direction. The human operator sets strategy, approves changes to the project's governing rules, and runs the system. Commit metadata records both the automated build and the operator, and every co-authored commit carries the `Co-Authored-By: Paperclip <noreply@paperclip.ing>` trailer.

If you contribute identifier candidates, new sources, or refinements through a pull request, your credit is recorded here at the next documentation refresh. See [README.md](README.md) for contribution guidance.

A few specific contributions deserve naming:

- **[Lynceus-Warden](https://github.com/kevwillow/lynceus-warden)**, a downstream user of Argus's exports, reported that some general-purpose Wi-Fi chip-vendor hardware addresses were being over-attributed to Flock cameras. The chips sit inside Flock devices but are not specific to Flock, so flagging them as high-confidence Flock surveillance risked a flood of false matches for other downstream users. Argus corrected this in a later release. The find is notable because no internal review would have caught it; only a downstream user's per-device view made it visible.
- **[Lynceus](https://github.com/kevwillow/lynceus)** later shipped a notification update that shows the matched hardware-address prefix next to the Flock label, so a user can tell a Flock-specific match from a general Wi-Fi chip seen inside a Flock device. That change let Argus restore high confidence to a set of these rows without re-introducing the false matches. If Lynceus ever drops the prefix display, the original concern returns and that decision must be revisited. Other tools that surface these rows should provide equivalent user-side disambiguation.
- **[EthanThePhoenix38](https://github.com/EthanThePhoenix38/flock-you-camera-detector)** maintains a camera-detector repository whose careful negative-evidence curation, removing prefixes that match non-target devices, is the discipline that made the confidence restoration above defensible.

A recent data-acquisition cycle added 208 identifiers, all sourced from public registries and a read-only firmware survey, with no new sources or vendors and no live-device contact. Provenance is attributed per row to: the IEEE Registration Authority OUI registry for hardware-address prefixes; the [FCC Equipment Authorization System grantee dataset](https://opendata.fcc.gov/d/3b3k-34jp) and fccid.io for grantee codes and equipment authorizations; the Nordic Semiconductor Bluetooth company-ID database for Bluetooth company identifiers; and the CSA Distributed Compliance Ledger for Matter device-attestation data. Firmware identifiers came from the public Dahua open-firmware index and an Axis 206W image mirrored on archive.org, surveyed read-only with no DRM circumvention. The `nmap` and Wireshark `manuf` tools were used only to cross-check prefix-to-vendor matches; provenance for every prefix is attributed upstream to the IEEE registry, not to those tools.

---

## Where the authoritative rules live

This file is a plain-language summary. The authoritative specification lives in the engineering documentation: the [project bible](docs/engineering/PROJECT_BIBLE.md) holds the governing rules (source-citation discipline, privacy discipline, promotion gates, confidence ceilings, and the facts-only doctrine), and the [amendment ledger](docs/engineering/BIBLE_AMENDMENTS.md) records changes to them over time. The [methodology](docs/engineering/METHODOLOGY.md) describes how the data is gathered and promoted, and the [data dictionary](docs/engineering/DATA_DICTIONARY.md) defines the database fields and source types. Where this summary and the engineering docs ever disagree, the engineering docs win.
