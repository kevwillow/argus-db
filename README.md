ARGUS IS IN ACTIVE DEVELOPMENT AND IS NOT COMPLETE. MAY NOT BE 100% ACCURATE AND MAY CONTAIN ANAMOLIES

# Argus

> Open-source database of surveillance equipment identifiers

[![watching the watchers](https://img.shields.io/badge/watching-the%20watchers-black.svg)](#what-is-argus)
[![flock around, find out](https://img.shields.io/badge/flock%20around-find%20out-red.svg)](#what-is-argus)
[![argus never blinks](https://img.shields.io/badge/argus-never%20blinks-black.svg)](#what-is-argus)
[![zero flocks given](https://img.shields.io/badge/zero-flocks%20given-red.svg)](#what-is-argus)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](LICENSE)

> **New here?** Start with [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for a plain-language overview of what Argus is and how to use the data. This README is a project summary; the user guide walks through concrete usage.

## What is Argus

Argus tracks the model numbers, MAC ranges, FCC grantee codes, hostnames, certificate identifiers, and BLE company IDs of surveillance equipment used by US law enforcement and adjacent operators. That includes **Hikvision CCTV cameras**, **Cellebrite forensic extraction devices**, **Anduril counter-drone systems**, **Flock Safety license plate readers**, **Geotab fleet telematics**, **Rohde & Schwarz IMSI catchers**, and dozens of other surveillance vendor categories.

Argus is a database rather than a real-time monitor. It lists the wireless and regulatory fingerprints of fixed and mobile surveillance equipment so that downstream tools (Lynceus, Rayhunter, or any other RF scanner) can alert when a matching device is detected nearby. Every entry comes from public sources: regulatory registries, public-records procurement data, open-source intelligence repositories, manufacturer documentation, and academic research.

Tools to surveil people are abundant; tools to detect surveillance are not. The asymmetry favors the surveillor. Argus narrows the gap by making vendor identifiers queryable in a single place with full provenance for every row.

**Argus is for *detection* of public-record-derived surveillance equipment identifiers, NOT for evasion of legitimate law-enforcement interaction.** Argus operates as a passive identification database: identifiers and metadata only, no active interference, no jamming, no attack tooling, no deanonymization of individual officers or agencies. The scope is *equipment categories*, not people.

## What's in the dataset

At v1.6.15:

- **43,125 active canonical identifiers**, the things you query against (MAC ranges, BLE service UUIDs, FCC grantee codes, vendor-controlled hostnames, and more). The most recent release (v1.6.15) is the CP52 `ssid_pattern` false-positive remediation (MAC-527): under Lynceus 0.9.2's case-insensitive substring matcher, 14 of the 32 `ssid_pattern` substrings shipped in v1.6.14 were false-positive magnets that mislabel ordinary WiFi as surveillance, so it withdraws 9 and refines 8 to delimiter-anchored device forms — active moves 43,134 → 43,125 (-9), standard feed 977 → 979, high-confidence 481 → 479, with every dropped/refined vendor keeping at least one working identifier. See the release notes below for the breakdown.
- **156 manufacturers**, surveillance vendors classified by what they make
- **95 upstream sources**, every identifier traces back to at least one of these public sources, with a direct URL citation
- **20 device categories**, what kind of surveillance equipment each identifier is associated with (ALPR, IMSI catcher, body cam, drone, CCTV camera, network surveillance, fleet telematics, Bluetooth tracker, smart lock, smart-home hub, etc.)
- **58 identifier types**, the kinds of identifiers tracked (MAC, OUI, FCC grantee code, hostname, BLE UUID, IMEI TAC, network discovery protocol pattern, etc.)
- **214 behavioral signatures**, cellular-control-plane patterns associated with IMSI-catcher detection

An *identifier* is a piece of data that pinpoints a vendor's hardware on a wire or radio band: an OUI (the first 24 bits of a MAC address, which maps to a manufacturer), a BLE service UUID broadcast by a device, an FCC grantee code on a regulatory filing, or a hostname embedded in a vendor's companion app. When a downstream scanner observes one of these in the wild, it can use Argus to identify what vendor and what device category produced it.

A *manufacturer* is a vendor that ships surveillance equipment. A *device category* is the kind of equipment (ALPR, body cam, etc.). A *source* is a public dataset that contributed observations to Argus.

## How to use the exports

Argus ships four export files for downstream consumption. Pick the one that matches your use case.

| Export | Records | Best for |
|---|---:|---|
| `exports/argus_export_high_confidence.json` | 479 | Runtime scanners (Lynceus). Strict confidence floor (≥70); excludes crowdsourced and inferred sources, except for named community Flock-hunt sources. Each row carries a `severity` field (`"high"` for Flock-attested rows, `null` otherwise). |
| `exports/argus_export.json` | 979 | Broader scanner watchlists. Looser confidence floor (≥30); US scope filter. |
| `exports/argus_export.csv` | 43,125 | Bulk import, analysis, or re-derivation. All active rows. Apply your own filters at import. |
| `exports/argus_export_behavioral_signatures.json` | 132 | Cellular-band scanners (Rayhunter). Sibling export with threshold rules. |

**Confidence scores in plain language:** confidence is on a 0-99 scale. Anything ≥70 is strong attribution from at least one canonical source. Anything ≥85 has been cross-corroborated by an independent second source. The high-confidence export is what you ship to a scanner that's going to alert; the rich CSV is what you query against when you want all the context.

**Stable identifier across exports:** `argus_record_id` is a 16-hex-char stable hash. Bind to it when you need to track a specific row across export versions or source-attribution changes.

For walkthroughs (querying the CSV, building a watchlist, integrating with a scanner), see [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md). For the engineering setup, see [`docs/engineering/SETUP.md`](docs/engineering/SETUP.md).

## Coverage scope (honest)

Argus covers surveillance equipment used by US law enforcement and adjacent operators, organized across these device categories:

- **ALPR (automated license plate readers)**, Flock Safety, Genetec, Rekor, Vigilant Solutions
- **IMSI catchers**, Harris, Digital Receiver Technology, Engility, KeyW, Jacobs, Septier, Rohde & Schwarz
- **Body cameras**, Axon, Getac, Reveal, WatchGuard Video
- **Police radios**, Kenwood, Motorola Solutions (multi-purpose subset)
- **Drones**, DJI, Parrot, BRINC, Skydio
- **Counter-drone systems**, Anduril, Dedrone, DroneShield, Fortem, Citadel Defense, Black Sage, D-Fend, AeroDefense, Echodyne, Liteye, Robin Radar, MyDefence, Sensofusion
- **CCTV / IP cameras**, Hikvision, Dahua, Axis, Avigilon, Verkada, Eagle Eye Networks, Rhombus, Hanwha, Milestone, Pelco, Uniview, Tiandy, Vivotek (NDAA §889 attribution preserved on Hikvision/Dahua/Uniview/Tiandy)
- **Persistent surveillance**, Elbit Systems of America, General Atomics, TCOM, Persistent Surveillance Systems (aerostats, towers, strategic-altitude platforms)
- **Through-wall radar**, Camero, NIITEK, TiaLinx (UWB; FCC §15.519 LE-only carveout)
- **Fleet telematics**, Geotab, Verizon Connect, Samsara, Motive, Lytx, Omnitracs
- **Electronic monitoring (ankle monitors)**, BI Incorporated, Attenti, STOP, Sentinel Offender Services, Track Group
- **Gunshot detection**, SoundThinking (ShotSpotter)
- **Forensic extraction tools**, Cellebrite, Magnet Forensics, Berla, Hak5
- **Face recognition**, Clearview AI, BriefCam
- **Concealed surveillance cameras**
- **Multi-purpose vendors**, when a vendor's equipment can't cleanly map to a single device category (e.g., Cradlepoint, Sierra Wireless, L3Harris, Northrop Grumman, Lockheed Martin, Trimble, Bosch Security Systems), they're flagged `device_category='unknown'` and excluded from the high-confidence Lynceus export to avoid false-positive risk.

**What's NOT covered:**

- Generic consumer electronics (router OUIs, phone IMEIs, undifferentiated smart-home noise) are not surveillance equipment and stay out of scope. The exception is the narrow set of consumer devices whose wireless signature is a documented surveillance or covert-tracking vector: BLE smart locks (`smart_lock`), smart-home hubs (`smart_home_hub`), pet and kid cellular trackers, and Bluetooth trackers are admitted for that reason, not as general IoT coverage.
- Military signals intelligence beyond what's discoverable via public regulatory and procurement records.
- Real-time deployment status. Argus tells you what an identifier *is*; not whether it's currently deployed near you. That's the downstream scanner's job.
- Vendors whose surveillance offering isn't public-record attestable. If we can't trace it back to a citable source, it doesn't ship.

Coverage is intentionally narrow per category. Argus has 156 vendors, but most categories list 3-13 vendors, not hundreds. Expansion comes from community contributions and future research.

## Most recent release

**v1.6.15** is the most recent release: the CP52 `ssid_pattern` false-positive remediation (MAC-527), isolated out of the in-flight Wave-6 gate (board call) so the fix ships alone and now rather than waiting on the Wave-6 data cycle, which regens into v1.6.16 next. Unlike the export-only v1.6.14 it is a **canonical data change** (migration `0038`, data-only, schema_version stays 33): it **withdraws 9 `ssid_pattern` rows by supersession and refines 8 in place** to remediate the 14 SEVERE false-positive magnets the MAC-522 WiGLE re-mine proved — under Lynceus 0.9.2's case-insensitive bare-substring matcher, 14 of the 32 substrings shipped in v1.6.14 mislabel ordinary home/business WiFi as surveillance (`flock` → "Schneeflocke", `dji` → "Fidji", `oxygen` → "Oxygen.Net", `iCSee` → "LogisticsEE"). Active identifiers move 43,134 → **43,125** (-9, all supersessions; total stays 43,840); the standard Lynceus feed moves **977 → 979** and the high-confidence feed **481 → 479** (`flock` + `Penguin` withdrawn); the behavioral feed holds at 132. The standard feed's `argus_run_id` moves to `221274e8-…` over the new active set. Every dropped or refined vendor keeps at least one working identifier (Flock, DJI, Parrot, Motorola stay detectable; `iCSee` / `V380` are refined, not dropped), and the CTO confirmed the 18 documented mine false-positives no longer match while real device SSIDs still do (FP-kill 0/18). Regenerated ISOLATED at the v1.6.14 / 43,134 baseline (Wave-6 excluded). **Consumer note:** the refined substring stems require **Lynceus 0.9.2 or newer**; they are delimiter-anchored, a near-term recall trade-off pending board matcher hardening (MAC-517 / MAC-356). See [`CHANGELOG.md`](CHANGELOG.md) for the full record.

### Prior release, v1.6.14

**v1.6.14** was the CP51 `ssid_pattern` export-layer capability flip (MAC-517), isolated out of the in-flight Wave-6 gate so it ships alone rather than riding a data cycle. It is **export-only** — zero admissions, zero withdrawals, no schema migration (schema_version stays 33), and no canonical write, so the database is byte-identical to v1.6.13 (DB post-sha `b406dff1...daa265`) and the standard feed's `argus_run_id` `10b46f03-3d3a-5646-9279-48cbb8d469aa` still matches the shipped v1.6.13 active set. CP51 re-pins the Lynceus `ssid_pattern` disposition from the stale "v0.2, no regex → DROP" assumption to **Lynceus 0.9.2 case-insensitive substring matching** (`? LIKE '%' || needle || '%' COLLATE NOCASE`, `db.py:1126`), after the board pinned the live matcher at 0.9.2 on MAC-516. Previously section-4.4 export-dropped `ssid_pattern` rows now ship as leading-literal substring stems: the standard Lynceus feed moves **945 → 977** (+32, 100% `ssid_pattern`) and the high-confidence feed **478 → 481** (+3); the behavioral feed holds at 132. Short or generic stems (`lpr`, `ibr`, `rv50`, `mp70`) are FP-held and confirmed absent from the feed. **Consumer note:** these substring rows require **Lynceus 0.9.2 or newer** to match; `ble_local_name` templates stay deferred to Lynceus v1.4.3+. See [`CHANGELOG.md`](CHANGELOG.md) for the full record.

### Prior release, v1.6.13

**v1.6.13** was the Wave-5 data-quality cleanup (MAC-511), staged as canonical write `937fefe`. It **withdraws 43 junk identifier rows by supersession** (migration 0037): 22 `network_endpoint` rows that were APK string-pool concatenation glue, and 21 `vendor_controlled_hostname` rows made up of 10 scrape-glue concatenations, 10 RFC-2606 reserved-placeholder (`example.com`) domains, and 1 Java class token mis-typed as a hostname. None were real vendor identifiers. There is no schema migration (schema_version stays 33), and nothing is deleted: the withdrawn rows stay in the registry as superseded history under the CP32 section 9 self-loop mechanism. Active identifiers move 43,177 → **43,134** (-43); total identifiers stay 43,840. All three Lynceus feeds hold flat (standard 945, high-confidence 478, behavioral 132) because `network_endpoint` and `vendor_controlled_hostname` are section-4.4 export-dropped types that never reach the v0.2 feeds, so the cleanup moves the active and CSV counts without touching a single feed entry. See [`CHANGELOG.md`](CHANGELOG.md) for the full record.

### Prior release, v1.6.12

**v1.6.12** was a quality-correction and sourcing cycle that bundled two staged commits under one tag: the MAC-477 correction (`8cfed9f`) and the Wave-4 ingest (MAC-493, `7d3652d`). The MAC-477 correction **withdrew 108 string-pool `ble_service_uuid` false positives** by supersession (migrations 0034/0035/0036), GATT characteristic-UUID mis-types that were never advertised service UUIDs, and Wave-4 **admitted 11 net-new identifiers** (ids 44648-44658): eight fleet-telematics OUIs (CalAmp, Zonar, Lytx ×4, Verizon Connect, Verizon Telematics), the Neology ALPR OUI `00:17:3d` plus its FCC grantee code `2AKNF`, and the RetailNext people-counting OUI `20:c3:a4`, with the ELSAG ALPR MAC range recategorized `unknown → alpr`. There was no schema migration (schema_version stayed 33). Active identifiers moved 43,274 → 43,177 (-97 net): the drop was the contamination cleanup, not a regression. The standard export moved 1,042 → 945 and the high-confidence export 469 → 478. The CP47 / CP50 export-layer Bible amendments proposed in v1.6.11 remain pending on MAC-492. See [`CHANGELOG.md`](CHANGELOG.md) for the full record.

### Prior release, v1.6.11

**v1.6.11** was the Wave-3 multi-lane sourcing cycle (MAC-490): it admitted **19 net-new identifiers** (ids 44629-44647) across six harvest lanes and shipped two export-layer changes, with no schema migration (schema_version 33). Active identifiers moved 43,255 → 43,274; the standard export grew 1,014 → 1,042 and the high-confidence export 464 → 469. The new rows were drone Remote ID surfaces (the ASTM F3411 `0xFFFA` service UUID and the `org.opendroneid.remoteid` Wi-Fi Aware service, plus Teal and uAvionix OUIs), a Bosch camera OUI, two Utility body-cam OUIs with the Flock Safety gunshot-detection service UUID, five smart-lock OUIs (August, ASSA ABLOY, iRevo, Unilock, Côte Picarde), five `unknown`-category smart-home OUIs (Nest, Lumi, SimpliSafe), and the Google Find My Device anti-stalking sound UUID. The CP50 `ble_local_name` literal split made 12 literal local-names feed-visible while holding 14 templates; the proposed B7 `mesh_radio` category was declined at the board ethics gate. See [`CHANGELOG.md`](CHANGELOG.md) for the full record.

### Prior release, v1.6.10

**v1.6.10** was the Wave-2 multi-cohort cycle (MAC-392), bundled under one tag with the board-ratified Axon body-cam GATT increment (MAC-352). It admits **132 net-new identifiers** across six device cohorts and mints two durable categories, `smart_lock` and `smart_home_hub` (migration 0033, CP46, schema_version 32 → 33). Active identifiers move 43,123 → 43,255; the standard export grows 900 → 1,014 and the high-confidence export 351 → 464. The new feed entries are smart locks (Kwikset, August, Ultraloq, Schlage, Yale; 56 rows), pet and kid cellular trackers (Fi, Whistle, Jiobit; 54 rows), a Samsung SmartThings hub, a Pebblebee Bluetooth tracker, and the two Axon body-cam service UUIDs. **Honest scope note:** the 10 cohort-1 spy-camera `ssid_pattern` families and the 5 cohort-6 `ble_local_name` rows are captured in the registry and the full CSV, but they do **not** reach the Lynceus JSON feeds under v0.2 (the writer drops regex and local-name patterns per `export_lynceus.py` §4.4), so a scanner does not alert on those spy-cam SSIDs today. Closing that gap is the deferred follow-up MAC-420. See [`CHANGELOG.md`](CHANGELOG.md) and `docs/engineering/BIBLE_AMENDMENTS.md` (CP46) for the full record.

### Prior release, v1.6.9

**v1.6.9** was the dedicated BLE-tracker fast-follow (MAC-387): it minted the `bluetooth_tracker` device category (schema_version 31 → 32) and made 46 captured tracker rows (AirTag, Tile, Samsung SmartTag, Chipolo, AirGuard) export-visible by absorbing the MAC-359 `ble_service_uuid → ble_uuid` map, with no net-new identifiers (active unchanged at 43,123). The standard export grew 737 → 900 and the high-confidence export 348 → 351. The Apple/Google Exposure-Notification UUID `0xFD6F`, a cross-vendor false-positive magnet, was caught in validation and held at `unknown`, absent from both feeds. See [`CHANGELOG.md`](CHANGELOG.md) for the detail.

### Prior release, v1.6.8

**v1.6.8** was the widest-net sourcing cycle the project has run: **81 net-new identifiers** across five device cohorts (Bluetooth trackers and stalkerware, ALPR and cop-car, drones, body cams and acoustic, consumer surveillance) plus a deferred-revival cleanup, with 25 bad OUIs withdrawn from the standard feed (active 43,213 → 43,123). The 26 consumer-camera OUIs (Ring, Wyze, Arlo, Blink) grew the high-confidence export 322 → 348; the Bluetooth-tracker rows landed captured-but-suppressed, with their feed-visibility deferred to the v1.6.9 fast-follow above. See [`CHANGELOG.md`](CHANGELOG.md) for the detail.

### Prior release, v1.6.7

**v1.6.7** layered +290 identifiers on v1.6.6 across two cohorts: the R2 SoC chipset set and the Flock/cop-car Android-app static-analysis cluster (active 42,923 → 43,213). The JSON feeds held flat because every new row was an Argus-internal type outside the Lynceus watchlist schema. See [`CHANGELOG.md`](CHANGELOG.md) for the detail.

### Prior release, v1.6.6

**v1.6.6** registered 15 new surveillance brands and brought in the deferred R2 new-vendor cohort (+1,022) plus Reolink firmware at full volume. See [`CHANGELOG.md`](CHANGELOG.md) for the breakdown.

## Quickstart

```bash
git clone https://github.com/kevwillow/argus-db.git
cd argus
python3 argus_cli.py status                        # show DB path, schema version, row counts
python3 argus_cli.py query e4:aa:ea:80:a1:9b       # lookup a Flock Safety ALPR MAC
```

The repo ships with `db/argus.db` and the export files already populated, so reading the data needs no `pip install`. See [`docs/engineering/SETUP.md`](docs/engineering/SETUP.md) for rebuilding the database from scratch, the source-ingest pipeline dependencies, and optional API keys.

## How to contribute

External contribution is welcome:

- **New identifiers / new sources**, submit a GitHub PR with per-row source citations. Every observation needs a concrete file path (e.g., `https://github.com/Owner/Repo/blob/<sha>/<path>#L<line>`), not just a bare repo URL.
- **No PII**, Argus identifies *equipment*, not people. Officer names, badge numbers, home addresses don't ship.
- **Provenance-first**, promotion to the canonical state requires a `raw_observations` ancestor + cited source band. The discipline framework is documented in [`docs/engineering/PROJECT_BIBLE.md`](docs/engineering/PROJECT_BIBLE.md) and [`docs/engineering/BIBLE_AMENDMENTS.md`](docs/engineering/BIBLE_AMENDMENTS.md).
- **Vendor attribution disputes**, open a GitHub issue. Argus's doctrinal grounding is Feist factual-data + 17 USC §1201(j) security-research exemption + 37 CFR §201.40(b) + nominative fair use.

For schema-impacting changes (new tables, new `identifier_type` enum values, new `source_type` bands), coordinate with the amendment process documented in [`docs/engineering/BIBLE_AMENDMENTS.md`](docs/engineering/BIBLE_AMENDMENTS.md), schema changes pair with formal amendment entries.

## Documentation map

- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md), start here. Plain-language overview, walkthroughs, coverage caveats.
- [`CHANGELOG.md`](CHANGELOG.md), version-by-version history (v1.0.0 through v1.6.15).
- [`CREDITS.md`](CREDITS.md), per-source attribution and per-vendor lexicon.
- [`docs/engineering/SETUP.md`](docs/engineering/SETUP.md), developer setup (clone, verify, migrations, tests).
- [`docs/engineering/METHODOLOGY.md`](docs/engineering/METHODOLOGY.md), how Argus integrates sources, confidence model, dedup logic.
- [`docs/engineering/DATA_DICTIONARY.md`](docs/engineering/DATA_DICTIONARY.md), schema reference for every table, column, enum value.
- [`docs/engineering/PROJECT_BIBLE.md`](docs/engineering/PROJECT_BIBLE.md), formal canonical specification.
- [`docs/engineering/BIBLE_AMENDMENTS.md`](docs/engineering/BIBLE_AMENDMENTS.md), append-only log of changes to the project's rules.

## Downstream consumers

Argus is designed as a producer of detection data for downstream RF-scanner consumers:

- **[Lynceus](https://github.com/kevwillow/lynceus-warden)** (Raspberry-Pi-class RF security monitor), consumes the JSON exports; matches on `{pattern, pattern_type}` against live RF observations.
- **[Rayhunter](https://github.com/EFForg/rayhunter)** (cellular IMSI-catcher detector on supported modems), consumes the behavioral signatures export.
- **Operator-side combined deployment**, an operator may run Lynceus + Rayhunter together; the two exports are non-overlapping (wire-observable patterns vs cellular-control-plane behavior).

**Operator-stack self-exclusion**: Argus operator-side hardware MUST NOT appear in the high-confidence export. That covers Lynceus host hardware (Raspberry Pi OUIs) and Rayhunter-supported modems (Orbic RC400L, FY UZ801, PinePhone Quectel, Wingtech CT2MHS01, T-Mobile TMOHS1, TP-Link M7350/M7310). This is mandatory regardless of source confidence.

## License

Argus ships under three licenses by artifact class:

- **Code:** [AGPL-3.0-or-later](LICENSE), network-use copyleft for derivative scanners.
- **Dataset:** [ODbL-1.0](LICENSE-DATA) with three-layer per-row license-posture composition.
- **Documentation:** [CC-BY-SA-4.0](LICENSE-DOCS), ShareAlike for derivative documentation.

**For users producing derived datasets:** honor the upstream license carry-forward chain. Commercial deployments MUST exclude `deployment_observations.LICENSE='CC-BY-NC-SA-4.0'` rows (the EFF Atlas of Surveillance non-commercial clause); standard ODbL ShareAlike applies otherwise. See [`CREDITS.md`](CREDITS.md) §9 for the re-derivation discipline.

**DMCA / takedown posture:** Argus's grounding is Feist factual-data (*Feist v. Rural Telephone Service* 499 U.S. 340 (1991)) + 17 USC §1201(j) security-research exemption + 37 CFR §201.40(b) + nominative fair use. Vendor attribution disputes route through a GitHub issue.

## Provenance discipline

Every active identifier traces back to:

1. **At least one `raw_observations` row** with `source_url` citing the upstream source verbatim (pinned-SHA + line-anchored where the source supports it)
2. **A `source_type` band** with a calibrated confidence ceiling per band
3. **A `confidence` integer** in 0-99 with corroboration-lift math when independent second sources arrive
4. **Per-row `notes` JSON** carrying license posture, promotion-time citation, and audit-trail anchors

**No fabrication.** If a source doesn't yield concrete evidence, the answer is "no record," not "plausible record." See [`docs/engineering/METHODOLOGY.md`](docs/engineering/METHODOLOGY.md) §7 for the full discipline.

---

## How I built this

Argus is the result of many long days and longer nights of iterative work across multiple machines: Windows dev boxes for some scraping and analysis, Linux dev machines and a Linux server for the database, orchestration, and most agent work. The build spans research, scraping, validation, schema design, license posture, the discipline framework, and the audit trail that backs every entry. The dataset grew from a 514-row baseline to over 41,000 active identifiers across roughly five-plus weeks of compressed work; the framework that makes those entries trustworthy took longer.

### Operator-led orchestration

I plan and orchestrate this project myself, using Claude chat as a strategic-planning collaborator, paperclipai as the agent orchestration layer, and Claude Code as the execution agent across several specialist roles (data extraction, source gathering, validation, schema design, and overall coordination). I have final decision authority on everything that lands in this repo. Strategic direction, architectural decisions, source-admission disputes, license posture, schema changes, and discipline-framework evolution are all operator-ratified before they commit.

The AI agents are highly capable executors with substantial scoping autonomy inside the constraints I set. They surface findings, propose decompositions, escalate when something needs ratification, and run extensive verification work I couldn't do at scale manually. But they don't decide canonical contract. I do.

This was not vibe-coded. Argus has 38 documented amendments to its canonical contract and 18 sub-agent rules governing how the build process itself operates. Every active identifier traces back to a verifiable public source via the audit trail. The discipline framework exists precisely because building a surveillance-equipment identification database is the kind of work where "looks roughly right" isn't good enough. Provenance, confidence, and false-positive resistance all need to be load-bearing, not afterthoughts.

### Notable technical work

Two areas surfaced data that wasn't otherwise aggregated anywhere queryable:

**Vendor app decompilation.** I downloaded Android APKs of setup and admin apps published by surveillance-equipment vendors (Flock Safety, Hikvision Hik-Connect, Dahua DMSS, Motorola WAVE PTT, Parrot FreeFlight 6, DJI Industry Pilot) and analyzed the binaries for embedded identifier patterns: BLE service UUIDs, MAC address prefixes, vendor-specific protocol fields, and default device names. Vendor setup apps need to recognize and connect to their own equipment, so they ship with the identifiers needed to do that. Decompiling public app-store binaries surfaced this information directly. This is legal reverse-engineering of publicly-distributed software under 17 USC §1201(j) + 37 CFR §201.40(b), but it required doing the work rather than waiting for vendors to publish identifier schemas (they don't).

**GitHub researcher-repo aggregation.** Surveillance equipment has been studied by independent researchers for years: drone RID protocol work (alphafox02/DragonSync), cellular intercept detection (EFForg/rayhunter), BLE stalking-tracker research (seemoo-lab/AirGuard), FAA Remote ID database mirrors (jlrjr's wrapper), and more. The data exists across these projects but had never been pulled into a single queryable database with provenance discipline. Argus aggregates it: every identifier traces back to the specific researcher repo, the specific commit, the specific file path, with proper attribution under the original licenses. This is meta-research synthesis rather than primary discovery, but it makes a large amount of distributed researcher work actually usable.

### The discipline framework

The most substantial thing I built is the framework that makes the database verifiable, more than the database itself.

Every active identifier carries source attribution, confidence scoring, source-type classification, and a chain of corroboration. The framework includes hard rules that prevent fabrication (every identifier must trace to a concrete public source), PII discipline (individual-attributed registrations stay held, not promoted), and downstream-consumer protection (downstream scanners receive only high-confidence canonical data). The framework evolved with the work, each substantive amendment is documented with case studies showing what went wrong (or could have gone wrong) and why the rule exists.

Building this with AI tools is what made it possible at the scale and velocity it happened. Building it deliberately, with operator-final-say discipline and a binding correctness framework, is what makes the output trustworthy.

---

## Support the Project

This project was built as a hobby by one person, a couple of computers, and a couple of LLMs. It burned through a fair bit of token cost and a lot of personal time, but it was worth it. If Argus saves you some time, or you just think it's cool, consider tossing a few sats my way. No pressure, but coffee and compute aren't free.

- **Star this repo**, it's free and it helps others find the project
- **Submit an issue or PR**, bug reports and feature ideas welcome
- **Crypto donations**, if you're feeling generous:
  - **BTC**, `bc1qmtzjlc2cw2y45nea2jqf4deh946j8mq502zvsw`
  - **BTC (Unstoppable Domain)**, `gurutech.blockchain`
  - **LTC**, `ltc1qf32n038a90ulajlq6zz67r3n2myewpjlj2ej6w`
  - **ETH**, `0x9bf3311c4721fe37f58913dc57c2bf1722dc8a0f`
  - **BCH**, `bitcoincash:qr2l294kuve9cw48u7xek9nklhed066ycvjtj4ymq9`
  - **SOL**, `CuraE8usMpSrAhpY2QiWaQGoBjyJzkSaUNP6kRgAzscU`

- **Contact**, kev@gurutechnology.services
