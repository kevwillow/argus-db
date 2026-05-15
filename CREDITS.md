# Argus — Upstream Attribution and Credits

Argus integrates data derived from 43 upstream sources (canonical registries, procurement data, public-records databases, academic research, community-research repositories, and vendor-published documentation) plus a canonical lexicon of 34 surveillance-technology vendors. This document attributes every upstream contribution, names the integration shape, and records license-carry-forward obligations downstream consumers must honor.

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

**License posture:** all primary_registry sources are factual public-allocation data. No copyright carry-forward chain; per-source attribution at the `sources` table + per-row in `identifiers.source_url`. Database-rights regime jurisdictions (EU sui generis): the registries themselves are protected; Argus's compiled extraction is governed by Argus's ODbL-1.0 compilation license per LICENSE-DATA.

---

## 2 — Tier 1/2 public-records and procurement data

- **[EFF Atlas of Surveillance](https://atlasofsurveillance.org/)** (sources.id=5) — Electronic Frontier Foundation + UNLV Reynolds School of Journalism's collaborative deployment-mapping project. 15,071 `deployment_observations` rows. **License: CC-BY-NC-SA-4.0**. **DOWNSTREAM COMMERCIAL CAUTION:** the NC (NonCommercial) clause prohibits commercial redistribution of these rows or their derivatives. See LICENSE-DATA §2.1 + §4.1 for the per-row LICENSE column quarantine mechanism. Non-commercial / research / journalist use is licensed.
- **[DeFlock](https://deflock.me/)** (sources.id=6) — Community-curated ALPR camera location database, OSM-mirrored via `cdn.deflock.me`. 101,597 `deployment_observations` rows. **License: ODbL-1.0**. Compatible with Argus's ODbL-1.0 compilation license. ShareAlike applies to derivative databases.
- **[USAspending.gov](https://api.usaspending.gov/api/v2/search/spending_by_award/)** (sources.id=8) — US federal procurement award database (public domain). 43,483 `procurement_records` rows.
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

Two sources (`sources.id` 39 + 42) publish material publicly on GitHub without a LICENSE file or explicit license declaration. Argus's promotion regime under these sources operates under the [Feist v. Rural Telephone Service (499 U.S. 340 (1991))](https://supreme.justia.com/cases/federal/us/499/340/) facts-not-copyrightable doctrine, with the canonical composition discipline defined in `PROJECT_BIBLE.md` (see Canonical sources at end of this document).

- **sources.id=39 EthanThePhoenix38/flock-you-camera-detector** — 20 raw observations contribute 19 promoted identifiers. 1 row rejected as a known-fake (cc:cc:cc all-identical-octet OUI).
- **sources.id=42 GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose** — 50 raw observations contribute 8 promoted identifiers (firmware-binary mining).

**What Argus extracts** (facts; not copyrighted): identifier values, manufacturer attributions, pinned source URL citations.

**What Argus does NOT republish** (compilation arrangement; copyrighted): list-snippet verbatim, repository structure mirror, selection/organization beyond single-fact citation.

**Per-promoted-row sentinel:** `identifiers.notes.upstream_license_posture='NO_LICENSE_DECLARED'` (canonical sentinel-key).

Downstream consumers redistributing Argus's database content inherit the same facts-only posture for these rows.

---

## 7 — Surveillance-technology vendor lexicon (manufacturers table; 34 canonical entries)

The `manufacturers` table is the canonical lexicon of surveillance-technology vendors used as the Tier-2/3 device_category inference allowlist. Each entry contributes vendor attribution to identifier rows. This is NOT a data source in the registry sense above; it's an internal curated lexicon used at promotion time. Listed alphabetically:

| Vendor | Canonical category |
|---|---|
| Avigilon | alpr |
| Axis Communications | alpr |
| Axon | body_cam |
| BRINC | drone |
| Berla | hacking_tool |
| BriefCam | face_recog |
| Cellebrite | hacking_tool |
| Clearview AI | face_recog |
| Cradlepoint | (uncategorized — multi-purpose-vendor carveout) |
| DJI | drone |
| Dedrone | drone_detect |
| Digital Receiver Technology | imsi_catcher |
| DroneShield | drone_detect |
| Engility | imsi_catcher |
| Flock Safety | alpr |
| Genetec | alpr |
| Getac | body_cam |
| Hak5 | hacking_tool |
| Harris | imsi_catcher |
| Jacobs | imsi_catcher |
| Kenwood | police_radio |
| KeyW | imsi_catcher |
| L3Harris | (uncategorized — multi-purpose-vendor) |
| Magnet Forensics | hacking_tool |
| Motorola Solutions | (uncategorized — multi-purpose-vendor carveout) |
| Parrot | drone |
| Rekor | alpr |
| Reveal | body_cam |
| Septier | imsi_catcher |
| Sierra Wireless | (uncategorized — multi-purpose-vendor) |
| Skydio | drone |
| SoundThinking (ShotSpotter) | gunshot_detect |
| Vigilant Solutions | alpr |
| WatchGuard | body_cam |

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
- **Per-identifier `notes.upstream_license_posture`**: NO_LICENSE_DECLARED facts-only sources (`sources.id` 39, 42; 27 promoted rows total) inherit the Feist regime — derivatives operate under Feist facts-not-copyrightable; no upstream license obligation.
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
