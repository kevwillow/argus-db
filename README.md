# Argus

> Open-source database of surveillance equipment identifiers

[![watching the watchers](https://img.shields.io/badge/watching-the%20watchers-black.svg)](#what-is-argus)
[![flock around, find out](https://img.shields.io/badge/flock%20around-find%20out-red.svg)](#what-is-argus)
[![argus never blinks](https://img.shields.io/badge/argus-never%20blinks-black.svg)](#what-is-argus)
[![zero flocks given](https://img.shields.io/badge/zero-flocks%20given-red.svg)](#what-is-argus)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](LICENSE)

> **New here?** Start with [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for a plain-language overview of what Argus is and how to use the data. This README is a project summary; the user guide walks through concrete usage.

## What is Argus

Argus tracks the model numbers, MAC ranges, FCC grantee codes, hostnames, certificate identifiers, and BLE company IDs of surveillance equipment used by US law enforcement and adjacent operators — like **Hikvision CCTV cameras**, **Cellebrite forensic extraction devices**, **Anduril counter-drone systems**, **Flock Safety license plate readers**, **Geotab fleet telematics**, **Rohde & Schwarz IMSI catchers**, and dozens of other surveillance vendor categories.

It's a database, not a real-time monitor. Argus enumerates the wireless and regulatory fingerprints of fixed and mobile surveillance equipment so that downstream tools — Lynceus, Rayhunter, or any other RF scanner — can alert when a matching device is detected nearby. Every entry is derived from public sources: regulatory registries, public-records procurement data, open-source intelligence repositories, manufacturer documentation, and academic research.

Tools to surveil people are abundant; tools to detect surveillance are not. The asymmetry favors the surveillor. Argus narrows the gap by making vendor identifiers queryable in a single place with full provenance for every row.

**Argus is for *detection* of public-record-derived surveillance equipment identifiers — NOT for evasion of legitimate law-enforcement interaction.** Argus operates as a passive identification database: identifiers and metadata only, no active interference, no jamming, no attack tooling, no deanonymization of individual officers or agencies. The scope is *equipment categories*, not people.

## What's in the dataset

At v1.5.2 (pending tag — Wave G/H v1 integration close):

- **35,958 active canonical identifiers** — the things you actually query against (MAC ranges, BLE service UUIDs, FCC grantee codes, vendor-controlled hostnames, etc.)
- **92 manufacturers** — surveillance vendors classified by what they make
- **73 upstream sources** — every identifier traces back to at least one of these public sources, with a direct URL citation
- **16 device categories** — what kind of surveillance equipment each identifier is associated with (ALPR, IMSI catcher, body cam, drone, CCTV camera, fleet telematics, etc.)
- **58 identifier types** — the kinds of identifiers tracked (MAC, OUI, FCC grantee code, hostname, BLE UUID, IMEI TAC, network discovery protocol pattern, etc.)
- **201 behavioral signatures** — cellular-control-plane patterns associated with IMSI-catcher detection

An *identifier* is a piece of data that uniquely identifies a vendor's hardware on a wire or radio band — like an OUI (the first 24 bits of a MAC address that maps to a manufacturer), a BLE service UUID broadcast by a device, an FCC grantee code on a regulatory filing, or a hostname embedded in a vendor's companion app. When a downstream scanner observes one of these in the wild, it can use Argus to identify what vendor and what device category produced it.

A *manufacturer* is a vendor that ships surveillance equipment. A *device category* is the kind of equipment (ALPR, body cam, etc.). A *source* is a public dataset that contributed observations to Argus.

## How to use the exports

Argus ships four export files for downstream consumption. Pick the one that matches your use case.

| Export | Records | Best for |
|---|---:|---|
| `exports/argus_export_high_confidence.json` | 119 | Runtime scanners (Lynceus). Strict confidence floor (≥70); excludes crowdsourced/inferred sources. |
| `exports/argus_export.json` | 536 | Broader scanner watchlists. Looser confidence floor (≥30); US scope filter. |
| `exports/argus_export.csv` | 39,832 | Bulk import, analysis, or re-derivation. All active rows. Apply your own filters at import. |
| `exports/argus_export_behavioral_signatures.json` | 125 | Cellular-band scanners (Rayhunter). Sibling export with threshold rules. |

**Confidence scores in plain language:** confidence is on a 0-99 scale. Anything ≥70 is strong attribution from at least one canonical source. Anything ≥85 has been cross-corroborated by an independent second source. The high-confidence export is what you ship to a scanner that's going to alert; the rich CSV is what you query against when you want all the context.

**Stable identifier across exports:** `argus_record_id` is a 16-hex-char stable hash. Bind to it when you need to track a specific row across export versions or source-attribution changes.

For walkthroughs (querying the CSV, building a watchlist, integrating with a scanner), see [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md). For the engineering setup, see [`docs/engineering/SETUP.md`](docs/engineering/SETUP.md).

## Coverage scope (honest)

Argus covers surveillance equipment used by US law enforcement and adjacent operators, organized across these device categories:

- **ALPR (automated license plate readers)** — Flock Safety, Genetec, Rekor, Vigilant Solutions
- **IMSI catchers** — Harris, Digital Receiver Technology, Engility, KeyW, Jacobs, Septier, Rohde & Schwarz
- **Body cameras** — Axon, Getac, Reveal, WatchGuard Video
- **Police radios** — Kenwood, Motorola Solutions (multi-purpose subset)
- **Drones** — DJI, Parrot, BRINC, Skydio
- **Counter-drone systems** — Anduril, Dedrone, DroneShield, Fortem, Citadel Defense, Black Sage, D-Fend, AeroDefense, Echodyne, Liteye, Robin Radar, MyDefence, Sensofusion
- **CCTV / IP cameras** — Hikvision, Dahua, Axis, Avigilon, Verkada, Eagle Eye Networks, Rhombus, Hanwha, Milestone, Pelco, Uniview, Tiandy, Vivotek (NDAA §889 attribution preserved on Hikvision/Dahua/Uniview/Tiandy)
- **Persistent surveillance** — Elbit Systems of America, General Atomics, TCOM, Persistent Surveillance Systems (aerostats, towers, strategic-altitude platforms)
- **Through-wall radar** — Camero, NIITEK, TiaLinx (UWB; FCC §15.519 LE-only carveout)
- **Fleet telematics** — Geotab, Verizon Connect, Samsara, Motive, Lytx, Omnitracs
- **Electronic monitoring (ankle monitors)** — BI Incorporated, Attenti, STOP, Sentinel Offender Services, Track Group
- **Gunshot detection** — SoundThinking (ShotSpotter)
- **Forensic extraction tools** — Cellebrite, Magnet Forensics, Berla, Hak5
- **Face recognition** — Clearview AI, BriefCam
- **Concealed surveillance cameras**
- **Multi-purpose vendors** — when a vendor's equipment can't cleanly map to a single device category (e.g., Cradlepoint, Sierra Wireless, L3Harris, Northrop Grumman, Lockheed Martin, Trimble, Bosch Security Systems), they're flagged `device_category='unknown'` and excluded from the high-confidence Lynceus export to avoid false-positive risk.

**What's NOT covered:**

- Consumer electronics (router OUIs, phone IMEIs, smart home devices) — these aren't surveillance equipment.
- Military signals intelligence beyond what's discoverable via public regulatory and procurement records.
- Real-time deployment status. Argus tells you what an identifier *is*; not whether it's currently deployed near you. That's the downstream scanner's job.
- Vendors whose surveillance offering isn't public-record attestable. If we can't trace it back to a citable source, it doesn't ship.

Coverage is intentionally narrow at the per-category baseline — Argus has 92 vendors, but most categories have 3-13 vendors in the lexicon, not hundreds. Expansion comes via community contributions and future research waves.

## Most recent release

**v1.5.2** (pending tag — Wave G/H v1 integration close) integrates the parallel-dispatch CCTV cohort + IMEI TAC mission cycle:

- 146 net-new active identifiers (85 BLE service UUIDs, 43 OUIs, 18 network discovery protocol patterns) across 6 CCTV vendors (Hikvision, Tiandy, Axis, Verkada, Avigilon, Dahua)
- 1 new identifier type added (`network_discovery_protocol_pattern` — vendor camera-discovery protocol signatures including Hikvision SADP, Dahua AirKiss/SmartConfig, Axis ONVIF WS-Discovery, Tiandy SADP-style)
- Canonical extractor v4 → v5 additive merge (filename preserved): IMEI TAC sub-extractor with structural PII truncation guarantee (9/9 proofs both pre- and post-merge), 4 cycle-discovered FP filters (bitmask, R8 XOR, NR/LTE TAC collision, word-boundary token anchor), and a 43-token CELLULAR_MODEM_CONTEXT_TOKENS expansion
- New canonical utility `select_base_apk_from_bundle.py` for xapk/apkm/apks bundle base-APK selection by manifest (replaces the silently-failing largest-apk heuristic)
- IMEI TAC mission negative result codified — 25-vendor effective sample yielded 0 unique TACs; companion-app sweeps are structurally unproductive in 2026 Android (runtime `TelephonyManager`, server-side device-model dispatch, R8 string encryption); mission redirect documented for future cycles
- Schema 27 → 28 (mig-0028 CHECK enum extension)

See [`CHANGELOG.md`](CHANGELOG.md) for the version-by-version history, and [`docs/engineering/BIBLE_AMENDMENTS.md`](docs/engineering/BIBLE_AMENDMENTS.md) for the formal change record (Correction Pass 34; CP35 + SAR-19 + §11 #18 staged pending).

## Quickstart

```bash
git clone https://github.com/kevwillow/argus-db.git
cd argus
python3 argus_cli.py status                        # show DB path, schema version, row counts
python3 argus_cli.py query e4:aa:ea:80:a1:9b       # lookup a Flock Safety ALPR MAC
```

The repo ships with `db/argus.db` and the export files already populated; the read-path needs no `pip install`. See [`docs/engineering/SETUP.md`](docs/engineering/SETUP.md) for fresh-DB rebuild from migrations, source-ingest pipeline dependencies, and optional API keys.

## How to contribute

External contribution is welcome:

- **New identifiers / new sources** — submit a GitHub PR with per-row source citations. Every observation needs a concrete file path (e.g., `https://github.com/Owner/Repo/blob/<sha>/<path>#L<line>`), not just a bare repo URL.
- **No PII** — Argus identifies *equipment*, not people. Officer names, badge numbers, home addresses don't ship.
- **Provenance-first** — promotion to the canonical state requires a `raw_observations` ancestor + cited source band. The discipline framework is documented in [`docs/engineering/PROJECT_BIBLE.md`](docs/engineering/PROJECT_BIBLE.md) and [`docs/engineering/BIBLE_AMENDMENTS.md`](docs/engineering/BIBLE_AMENDMENTS.md).
- **Vendor attribution disputes** — open a GitHub issue. Argus's doctrinal grounding is Feist factual-data + 17 USC §1201(j) security-research exemption + 37 CFR §201.40(b) + nominative fair use.

For schema-impacting changes (new tables, new `identifier_type` enum values, new `source_type` bands), coordinate with the amendment process documented in [`docs/engineering/BIBLE_AMENDMENTS.md`](docs/engineering/BIBLE_AMENDMENTS.md) — schema changes pair with formal amendment entries.

## Documentation map

- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) — start here. Plain-language overview, walkthroughs, coverage caveats.
- [`CHANGELOG.md`](CHANGELOG.md) — version-by-version history (v1.0.0 through v1.5.2).
- [`CREDITS.md`](CREDITS.md) — per-source attribution and per-vendor lexicon.
- [`docs/engineering/SETUP.md`](docs/engineering/SETUP.md) — developer setup (clone, verify, migrations, tests).
- [`docs/engineering/METHODOLOGY.md`](docs/engineering/METHODOLOGY.md) — how Argus integrates sources, confidence model, dedup logic.
- [`docs/engineering/DATA_DICTIONARY.md`](docs/engineering/DATA_DICTIONARY.md) — schema reference for every table, column, enum value.
- [`docs/engineering/PROJECT_BIBLE.md`](docs/engineering/PROJECT_BIBLE.md) — formal canonical specification.
- [`docs/engineering/BIBLE_AMENDMENTS.md`](docs/engineering/BIBLE_AMENDMENTS.md) — append-only amendment log (Correction Pass + SAR entries).

## Downstream consumers

Argus is designed as a producer of detection data for downstream RF-scanner consumers:

- **[Lynceus](https://github.com/kevwillow/lynceus-warden)** (Raspberry-Pi-class RF security monitor) — consumes the JSON exports; matches on `{pattern, pattern_type}` against live RF observations.
- **[Rayhunter](https://github.com/EFForg/rayhunter)** (cellular IMSI-catcher detector on supported modems) — consumes the behavioral signatures export.
- **Operator-side combined deployment** — an operator may run Lynceus + Rayhunter together; the two exports are non-overlapping (wire-observable patterns vs cellular-control-plane behavior).

**Operator-stack self-exclusion**: Argus operator-side hardware MUST NOT appear in the high-confidence export — that covers Lynceus host hardware (Raspberry Pi OUIs) and Rayhunter-supported modems (Orbic RC400L, FY UZ801, PinePhone Quectel, Wingtech CT2MHS01, T-Mobile TMOHS1, TP-Link M7350/M7310). This is mandatory regardless of source confidence.

## License

Argus ships under three licenses by artifact class:

- **Code:** [AGPL-3.0-or-later](LICENSE) — network-use copyleft for derivative scanners.
- **Dataset:** [ODbL-1.0](LICENSE-DATA) with three-layer per-row license-posture composition.
- **Documentation:** [CC-BY-SA-4.0](LICENSE-DOCS) — ShareAlike for derivative documentation.

**For users producing derived datasets:** honor the upstream license carry-forward chain. Commercial deployments MUST exclude `deployment_observations.LICENSE='CC-BY-NC-SA-4.0'` rows (the EFF Atlas of Surveillance non-commercial clause); standard ODbL ShareAlike applies otherwise. See [`CREDITS.md`](CREDITS.md) §9 for the re-derivation discipline.

**DMCA / takedown posture:** Argus's grounding is Feist factual-data (*Feist v. Rural Telephone Service* 499 U.S. 340 (1991)) + 17 USC §1201(j) security-research exemption + 37 CFR §201.40(b) + nominative fair use. Vendor attribution disputes route through a GitHub issue.

## Provenance discipline

Every active identifier traces back to:

1. **At least one `raw_observations` row** with `source_url` citing the upstream source verbatim (pinned-SHA + line-anchored where the source supports it)
2. **A `source_type` band** with a calibrated confidence ceiling per band
3. **A `confidence` integer** in 0-99 with corroboration-lift math when independent second sources arrive
4. **Per-row `notes` JSON** carrying license posture, promotion-time citation, and audit-trail anchors

**No fabrication.** If a source doesn't yield concrete evidence, the answer is "no record" — not "plausible record." See [`docs/engineering/METHODOLOGY.md`](docs/engineering/METHODOLOGY.md) §7 for the full discipline.

---

## How I built this

Argus is the result of many long days and longer nights of iterative work across multiple machines — Windows dev boxes for some scraping and analysis work, Linux dev machines and a Linux server for the database, orchestration, and most agent work. The build process spans research, scraping, validation, schema design, license posture, discipline framework, and the audit trail that backs every promotion. The substantive growth from a 514-row baseline to over 35,000 active identifiers happened across roughly five weeks of compressed work; the architectural framework that makes those promotions trustworthy took longer.

### Operator-led orchestration

I plan and orchestrate this project myself, using Claude chat as a strategic-planning collaborator, paperclipai as the agent orchestration layer, and Claude Code as the execution agent across multiple specialist roles (extraction worker, source worker, validator, database architect, orchestrator). I have final decision authority on everything that lands in this repo. Strategic direction, architectural decisions, source-admission disputes, license posture, schema changes, and discipline-framework evolution are all operator-ratified before they commit.

The AI agents are highly capable executors with substantial scoping autonomy inside the constraints I set. They surface findings, propose decompositions, escalate when something needs ratification, and run extensive verification work I couldn't do at scale manually. But they don't decide canonical contract. I do.

This was not vibe-coded. Argus has 34 documented amendments to its canonical contract and 18 sub-agent rules governing how the build process itself operates. Every active identifier traces back to a verifiable public source via the audit trail. The discipline framework exists precisely because building a surveillance-equipment identification database is the kind of work where "looks roughly right" isn't good enough — provenance, confidence, and false-positive resistance all need to be load-bearing, not afterthoughts.

### Notable technical work

Two areas surfaced data that wasn't otherwise aggregated anywhere queryable:

**Vendor app decompilation.** I downloaded Android APKs of setup and admin apps published by surveillance-equipment vendors (Flock Safety, Hikvision Hik-Connect, Dahua DMSS, Motorola WAVE PTT, Parrot FreeFlight 6, DJI Industry Pilot) and analyzed the binaries for embedded identifier patterns — BLE service UUIDs, MAC address prefixes, vendor-specific protocol fields, default device names. Vendor setup apps need to recognize and connect to their own equipment, so they ship with the identifiers needed to do that. Decompiling public app-store binaries surfaced this information directly. This is legal reverse-engineering of publicly-distributed software under 17 USC §1201(j) + 37 CFR §201.40(b), but it required actually doing the work rather than waiting for vendors to publish identifier schemas (they don't).

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
