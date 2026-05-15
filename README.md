# Argus

> Open-source database of surveillance equipment identifiers

[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Data License: ODbL-1.0](https://img.shields.io/badge/Data-ODbL--1.0-orange.svg)](LICENSE-DATA)
[![Docs License: CC-BY-SA-4.0](https://img.shields.io/badge/Docs-CC--BY--SA--4.0-yellow.svg)](LICENSE-DOCS)
[![GitHub release](https://img.shields.io/github/v/release/CascadeForge/argus?label=release)](../../releases)
[![CI](https://img.shields.io/github/actions/workflow/status/CascadeForge/argus/ci.yml?branch=main&label=CI)](../../actions)

## What Argus is

Argus is a consolidated, well-attributed, queryable database of wireless identifiers — MAC addresses, OUIs, BSSIDs, SSID patterns, BLE UUIDs, FAA Remote ID prefixes, Bluetooth SIG company IDs, vendor-app BLE service UUIDs, and behavioral-signature heuristics — for **surveillance and law-enforcement-adjacent equipment, derived entirely from public sources**. It ships as three artifacts under three licenses: a pipeline (AGPL-3.0-or-later), a dataset (ODbL-1.0, with Atlas-derived rows quarantined under CC-BY-NC-SA-4.0 per upstream NC clause), and documentation (CC-BY-SA-4.0).

Throughout this README: *database* refers to the queryable SQLite file (`db/argus.db`); *dataset* refers to the exported JSON/CSV artifacts derived from it; *pipeline* refers to the migration + source-loader code that reproduces the database from upstream sources.

Tools to surveil people are abundant; tools to detect surveillance are not. The asymmetry favors the surveillor. Argus narrows the gap by enumerating the wireless fingerprints of fixed ALPRs, IMSI catchers, body cameras, police drones, and related equipment, so that a downstream scanner (Rayhunter, Lynceus, or another consumer) can alert when matching devices are detected nearby.

**Argus is for *detection* of public-record-derived surveillance equipment identifiers — NOT for evasion of legitimate law-enforcement interaction.** Argus operates as a passive identification database: identifiers and metadata only, no active interference, no jamming, no attack tooling, no deanonymization of individual officers or agencies. The scope is *equipment categories*, not people. Identifiers are derived exclusively from public sources — regulatory registries, public-records procurement data, open-source intelligence repositories, manufacturer-published documentation, and academic research.

## Quickstart

```bash
git clone https://github.com/CascadeForge/argus.git
cd argus
python3 argus_cli.py status                        # show DB path, schema version, row counts
python3 argus_cli.py query e4:aa:ea:80:a1:9b       # lookup a Flock Safety ALPR MAC (id=1)
```

The repo ships with `db/argus.db` and the four canonical exports under `exports/` already populated; the read-path needs no `pip install`. See [SETUP.md](SETUP.md) for fresh-DB-init from migrations, source-ingest pipeline dependencies (per-domain pinned in `requirements-vendor-docs.txt` and `requirements-wigle.txt`), optional API keys, and WiGLE-grant gating.

## Status (v1.0.0)

Argus **v1.0.0** ships at schema_version=19 with:

- **22,532 active canonical identifiers** + 80 superseded (kept for audit-trail) across 14 user tables
- **131 behavioral_signatures** (IMSI-catcher detection heuristics + community-research detector-internal patterns)
- **133,134 raw observations** with per-row source provenance (every active identifier traceable to at least one source citation)
- **116,668 deployment_observations** from EFF Atlas of Surveillance + DeFlock with per-row LICENSE column for downstream license-aware filtering
- **43 upstream sources** across canonical registries, procurement data, academic research, manufacturer documentation, and community-OSINT GitHub repositories
- **34 surveillance-tech vendors** in the canonical lexicon

**Coverage is intentionally narrow at this baseline** — do not assume comprehensive coverage of any specific surveillance equipment category. Expansion comes via community contributions and future research waves (see [Known held items](#known-held-items-contribution-welcome) below).

Release cadence: tagged releases when substantive new data, new source families, or schema-impacting changes land. See [CHANGELOG.md](CHANGELOG.md) for the v1.0.0 ledger including the full amendment history and migration ledger 1 → 19.

## Twelve device categories

Argus categorizes identifiers per the canonical 12-value vocabulary (enum on the `identifiers.device_category` column):

| Category | What it covers | Example v1.0.0 vendors |
|---|---|---|
| `alpr` | Automated License Plate Reader systems | Flock Safety, Genetec, Rekor, Vigilant Solutions, Avigilon, Axis Communications |
| `imsi_catcher` | Cellular IMSI / IMEI / TMSI collection devices | Harris, Digital Receiver Technology, Engility, KeyW, Jacobs, Septier |
| `body_cam` | Body-worn cameras + adjacent | Axon, Getac, Reveal, WatchGuard Video |
| `police_radio` | Encrypted police radios | Kenwood (and Motorola Solutions multi-purpose subset) |
| `drone` | Surveillance drones + remote-pilot aircraft | DJI, Parrot, BRINC, Skydio |
| `gunshot_detect` | Acoustic gunshot detection | SoundThinking (ShotSpotter) |
| `hacking_tool` | Forensic device-extraction tools | Cellebrite, Magnet Forensics, Berla, Hak5 |
| `covert_cam` | Concealed surveillance cameras | (broad class; v1.0.0 has placeholder rows) |
| `gps_tracker` | Covert GPS asset trackers | (broad class; v1.0.0 has placeholder rows) |
| `face_recog` | Face-recognition systems | Clearview AI, BriefCam |
| `drone_detect` | Counter-drone detection systems | Dedrone, DroneShield |
| `unknown` | OUI- or registry-level identifier without single-product attribution; multi-purpose-vendor carveout | Cradlepoint, Sierra Wireless, L3Harris, Motorola Solutions (when OUI-only) |

The 12-value enum and per-vendor categorization rationale are documented in [PROJECT_BIBLE.md](PROJECT_BIBLE.md) (canonical anchors in the Canonical sources table at end of this document). The "unknown" category is **not exported to Lynceus** per the multi-purpose-vendor discipline. See `manufacturers` table at runtime for the full canonical lexicon.

## Data sources

Argus integrates data from 43 upstream sources organized across five tiers. Full per-source attribution + upstream-license chain at [CREDITS.md](CREDITS.md).

**Tier 1 — Canonical allocation registries** (`source_type='primary_registry'`):

- **IEEE OUI / MA-L / MA-M / MA-S / IAB registries** — vendor-to-OUI mappings; ~70,000 active identifier rows
- **FCC EAS Equipment Authorization Grantee Registrations** — 50,153-grantee corporate registrant lookup
- **FAA UAS Remote-ID Public DOC API (DETAIL endpoint)** — 427 active drone-class `drone_id_prefix` identifiers
- **Bluetooth SIG company-identifier registry** — 3,971 active `ble_manufacturer_id` allocations

**Tier 1/2 — Public records + procurement data**:

- **EFF Atlas of Surveillance** (CC-BY-NC-SA-4.0; NC clause carries forward) — 15,071 deployment_observations
- **DeFlock** (ODbL-1.0; license-compatible with compilation license) — 101,597 ALPR camera deployment_observations
- **USAspending.gov + Granicus Legistar** — federal/state/municipal procurement records (43,483 + 3)
- **Wireshark `manuf` file** — community-maintained OUI vendor-name cross-reference
- **WiGLE.net** — disabled by default in v1.0.0 (gated on user's WiGLE-grant quota; see [SETUP.md](SETUP.md))

**Tier 1 — Academic research** (`source_type='academic'`):

- **Marlin: Detecting IMSI-Catchers (NDSS Symposium 2025)** — academic foundation for behavioral_signatures table
- **RUB-SysSec/DroneSecurity (AGPL-3.0)** — Ruhr-University Bochum DJI Drone-ID research
- **GainSec/anti-crime-ecosystem-research (CC-BY-NC-ND-4.0 with research-use clause)** — CVE-anchored white paper

**Tier 2-3 — Vendor companion applications** (`source_type='manufacturer_app'` + `manufacturer_doc'`):

- **Hak5 product documentation, Flock Safety FS Installer, Getac BWC Viewer** — vendor companion apps statically analyzed under the 17 USC §1201(j) + 37 CFR §201.40(b) security-research exemption; decompiled source NOT redistributed per the decompiled-output non-redistribution rule

**Tier 1-3 — Community-research repositories** (`source_type='crowdsourced'` or `'academic'`):

22 canonical + 5 secondary-batch GitHub repositories contributing corroborating identifier observations across drone Remote ID, BLE tracker catalogs, IMSI-catcher detection, ALPR-camera profiles, and flock-detection cohorts. Two sources (GainSec anti-crime-ecosystem + GainSec falcon-sparrow-alpr-edl-firehose firmware) operate under the Feist facts-only promotion regime (NO_LICENSE_DECLARED public-but-unlicensed; factual extraction permitted per *Feist v. Rural Telephone Service* 499 U.S. 340 (1991); compilation arrangement NOT republished). Per-row sentinel `notes.upstream_license_posture='NO_LICENSE_DECLARED'` on these promoted rows.

## Output shape

Argus produces five canonical artifacts at v1.0.0:

| Artifact | Format | Content | Consumer |
|---|---|---|---|
| `db/argus.db` | SQLite | Canonical database (14 user tables; schema_version=19) | direct query / re-derivation |
| `exports/argus_export.json` | JSON | Standard Lynceus export (`{pattern, pattern_type, description, argus_record_id}` per row) | scanner-side watchlist (confidence ≥30) |
| `exports/argus_export_high_confidence.json` | JSON | High-confidence Lynceus export (same shape, confidence ≥70, `source_type` excludes `crowdsourced`+`inferred`) | scanner-side watchlist (operator-strict) |
| `exports/argus_export_behavioral_signatures.json` | JSON | Rayhunter-bound sibling export (`{signature_name, cellular_generation, threshold_json, confidence, argus_record_id}` per row) | RF-detection scanners |
| `exports/argus_export.csv` | CSV | Rich-import feed (15 columns; all active rows incl. `device_category='unknown'`) | analytical consumption / downstream re-derivation |

**Stable consumer-facing identifier:** `argus_record_id` is a 16-hex-char SHA-256 prefix: `sha256('<identifier_type>|<normalized_identifier>')[:16]`. Stable across re-runs, source-attribution changes, and confidence drift. Bind to this for cross-export consistency.

**CSV consumer note:** `argus_export.csv` line 1 is a `# meta:` comment with schema version / export timestamp / record count / confidence threshold. Line 2 is the column header. Consumers using `csv.DictReader` should skip line 1 or use a sniffer-aware reader (e.g., `pd.read_csv(comment='#')`).

## Provenance discipline

Every active `identifiers` row is traceable to:

1. **At least one `raw_observations` row** with `source_url` citing the upstream source verbatim (per the source-url-direct discipline; URLs are pinned-SHA + line-anchored, e.g., `https://example.com/path/to/file.ext#L<line>` or canonical `<repo>/blob/<sha>/<path>#<anchor>`)
2. **A `source_type` band** per the ten-value enum (`primary_registry` / `regulatory` / `manufacturer_doc` / `manufacturer_app` / `academic` / `foia` / `crowdsourced` / `inferred` / `procurement` / `official`) with calibrated confidence ceiling per band
3. **A `confidence` integer** in 0–99 (humility-margin invariant); corroboration math `min(99, max(originals) + 5)` per the corroboration-lift rule
4. **Per-row `notes` JSON** carrying license posture (`notes.upstream_license_posture` is the canonical sentinel-key for upstream license tracking), promotion-time citation, and audit-trail anchors

**Row-level reclassifications** (band changes, confidence changes, source_url upgrades) land an entry in the `source_reclassifications` audit table with `sweep_event_id` grouping + pre/post snapshot + rationale anchor. Forensic query: "show me every identifier ever reclassified, when, why, and by which sweep" is an O(1) query.

**Per-row license-tag handling** (migration 0016): `deployment_observations.LICENSE` is NOT NULL; carries the upstream source's license verbatim (Atlas rows: `'CC-BY-NC-SA-4.0'`; DeFlock rows: `'ODbL-1.0'`). Downstream consumers integrating Argus for commercial scanner deployments MUST honor the per-row LICENSE column. See [LICENSE-DATA §4.1](LICENSE-DATA) for the per-source taxonomy and downstream consumer guidance.

**No fabrication.** Hard-rule: identifiers and metadata derive from cited upstream sources only. No agent invents data; if a source doesn't yield concrete evidence, the answer is "no record" not "plausible record". See [METHODOLOGY.md §7](METHODOLOGY.md) for the full provenance discipline including third-party-citation-lineage boundary, no-PII discipline, and amendment-log discipline.

## Downstream consumers

Argus is designed as a producer of detection data for downstream RF-scanner consumers. The intended downstream architecture:

- **[Lynceus](https://github.com/...) (Raspberry-Pi-class RF security monitor)** — consumes `argus_export.json` (standard) or `argus_export_high_confidence.json` (operator-strict). Matches on `{pattern, pattern_type}` against live RF observations; alerts on match. Severity is owned operator-side via `severity_overrides.yaml`. Geographic-scope filter applied at export time.
- **[Rayhunter](https://github.com/EFForg/rayhunter) (cellular IMSI-catcher detector on supported modems)** — consumes `argus_export_behavioral_signatures.json` (Rayhunter-bound sibling export). Matches on `{signature_name, threshold_json}` against live cellular-control-plane observations.
- **Operator-side combined deployment** — an operator may run Lynceus + Rayhunter together on the same hardware; the two exports are non-overlapping (Lynceus = wire-observable patterns; Rayhunter = behavioral signatures).

**Operator-stack self-exclude discipline**: Argus operator-side hardware MUST NOT appear in the Lynceus high-confidence export. This covers (a) Lynceus host hardware (Raspberry Pi OUIs); and (b) Defensive-tool hardware (Rayhunter-supported modems including Orbic RC400L USB VID:PID `05c6:f601`/`f626`/`f622`, FY UZ801, PinePhone Quectel, Wingtech CT2MHS01, T-Mobile TMOHS1, TP-Link M7350/M7310). The exclusion is mandatory regardless of source confidence. Standard-export inclusion at `severity='low'` is permitted.

**Future v1.x consumer extensions** include scope proposals for additional scanner classes; per-scanner integration guidance is added to [METHODOLOGY.md §5.5](METHODOLOGY.md) when new export shapes are approved through the canonical-bible amendment process.

## Known held items (contribution welcome)

Argus's v1.0.0 baseline includes several explicitly-documented held items where data is known to exist but is intentionally not yet promoted to canonical state. **These are NOT incomplete data; they are known held items pending the right additional evidence to admit them.** Future contributors may be exactly the right people to help unlock them.

- **31 behavioral_signatures pending second-source corroboration.** IMSI-catcher behavioral patterns surfaced during initial extraction (AIMSICD, eylonK14 IMSI Catcher Detector, and adjacent community-research sources) that have single-source provenance and require independent second-source per the corroboration math. Contribution path: surface a second independent academic/regulatory source citing the same behavioral pattern.
- **62 Class B sustained holds** (IEEE-derived `raw_observations` with `notes.pii_review_disposition='individual_attributed_pii_sustain'` AND `notes.registry_xcheck_attempted=true`). Under the PII default-to-HOLD rule, individual-shaped names without corporate-entity confirmation stay held. Predominantly: Lumiplan Duhamel ×9 (French digital-signage corporate; no FCC registration), individual-shaped names (Yuval Fichman, Rudy Tellert, Walter Grotkasten, etc.), ~50 unique singletons with no surveillance-tech-vendor or FCC-grantee evidence. Contribution path: surface alternate corporate-entity registry (international corporate registries beyond US FCC) that confirms the entity-class.
- **133 IEEE Private permanent holds** (`pii_review_disposition='ieee_private_registrant_permanent_hold'`). IEEE OUI registrations declared as private at the registry source; cannot confirm ownership. Permanent HOLD by the PII discipline + IEEE-Private rule.
- **142 round-2 held rows** (107 vocabulary-extension candidates pending future enum extension + 19 behavioral-signature deferred + 15 CVE false-positive entries filed to the conflicts table + 1 attribution-pending Motorola/Vigilant). Contribution path varies per sub-class: vocabulary-extension candidates need a future `identifier_type` enum extension (canonical-bible amendment); deferred behavioral-signature candidates need additional research; Motorola/Vigilant attribution-conflict needs manufacturer-aliasing verification.
- **Known sources-row metadata discrepancy** — sources 1/2/3/7 carry historic `source_type='regulatory'` metadata pre-dating the source-type taxonomy refinement; identifier-row data is correctly labeled `primary_registry`. Cleanup queued post-ship. Downstream consumers filtering on `sources.source_type='primary_registry'` should also include `sources.id IN (1,2,3,7)` until the cleanup lands.

See [CHANGELOG.md "Known limitations + post-v1.0.0 roadmap"](CHANGELOG.md) for the full forward-roadmap including future community-source-acquisition waves, iOS coverage expansion, and Skydio Enterprise alt-channel scope.

## Contribution guidance

External contribution is welcome under the discipline framework codified in [PROJECT_BIBLE.md](PROJECT_BIBLE.md) (hard-rule set) and the sub-agent-rule additions in [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md). Specifically:

**For new sources** (community-OSINT GitHub repos, academic papers, regulatory registries, vendor docs):

- **Source-url-direct.** Every observation must cite a concrete file path within the source (e.g., `https://github.com/Owner/Repo/blob/<sha>/<path>#L<line>`). Bare repo URLs without per-row anchors are insufficient.
- **No PII.** Argus identifies *equipment categories*, not people. Officer names, badge numbers, home addresses — strip them. Per-row gate: `notes.pii_review_disposition='deferred_for_human_pii_review'` for any ambiguous case.
- **Provenance is the database.** Promotion to canonical state requires a `raw_observations` ancestor + `source_url` + cited `source_type` band per the source-type ceiling rules.
- **Confidence ceiling per source band.** No confidence drift upward without second-source corroboration per the corroboration math. Row-level reclassifications land in the `source_reclassifications` audit table.
- **Feist facts-only.** Public-but-unlicensed sources qualify for facts-only extraction; compilation arrangement (list-snippet verbatim copies; repository structure mirrors) is NOT republished. Per-row sentinel `notes.upstream_license_posture='NO_LICENSE_DECLARED'`.

**For new identifiers** (extending vendor coverage, new device categories, new behavioral signatures): submit via the standard GitHub PR process. Substantive contributions carry per-row provenance, source-band classification, and confidence rationale per the discipline framework above.

**For schema-impacting changes** (new tables, new `identifier_type` enum values, new `source_type` bands): coordinate with the canonical-bible amendment process documented at [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) — schema changes pair with `BIBLE_AMENDMENTS.md` entries per the amendment-log discipline.

**For vendor attribution disputes** (a vendor disagrees with their inclusion or categorization): open a GitHub issue describing the dispute. Argus's posture (Feist factual data + 17 USC §1201(j) + 37 CFR §201.40(b) + nominative fair use) governs the data-discipline response.

## Documentation

- [METHODOLOGY.md](METHODOLOGY.md) — methodology, provenance discipline, source-tier hierarchy, agent-orchestrated build process
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — schema reference for every table, column, and enum value
- [SETUP.md](SETUP.md) — local install, dependencies, optional API keys
- [CREDITS.md](CREDITS.md) — upstream attribution + 43 data-source credits + 34-entry surveillance-tech vendor lexicon
- [CHANGELOG.md](CHANGELOG.md) — version history from v1.0.0 including the full amendment ledger, migration ledger 1 → 19, and pre-v1.0.0 history timeline
- [PROJECT_BIBLE.md](PROJECT_BIBLE.md) — discipline architecture (hard rules, device_category vocabulary, Lynceus mapping, export shape)
- [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) — append-only amendment log with full case-study anchors
- [LICENSE](LICENSE) / [LICENSE-DATA](LICENSE-DATA) / [LICENSE-DOCS](LICENSE-DOCS) — three license texts (AGPL-3.0-or-later / ODbL-1.0 / CC-BY-SA-4.0) + Argus-specific preambles documenting scope-of-coverage + 3-layer per-row license-posture composition

## License

Argus ships under three licenses by artifact class:

- **Code:** [AGPL-3.0-or-later](LICENSE) — network-use copyleft preserves source-availability for derivative scanners; AGPL-3.0 inheritance-compatible with community-contributed sources at `sources.id` 38/40/43
- **Dataset:** [ODbL-1.0](LICENSE-DATA) with three-layer per-row license-posture composition:
  - Layer 1: `sources.notes.license_posture` (per-source declaration; 6 license-posture classes)
  - Layer 2: `deployment_observations.LICENSE` (per-row NOT NULL column; Atlas rows quarantined under CC-BY-NC-SA-4.0 NC clause)
  - Layer 3: `identifiers.notes.upstream_license_posture` (per-promoted-identifier canonical sentinel-key)
- **Documentation:** [CC-BY-SA-4.0](LICENSE-DOCS) — ShareAlike preserves discipline-architecture open-availability for derivative documentation

**For users producing derived datasets:** honor the upstream license carry-forward chain. Commercial deployments MUST exclude `deployment_observations.LICENSE='CC-BY-NC-SA-4.0'` rows (Atlas NC clause); standard ODbL ShareAlike applies otherwise. See [CREDITS.md §9](CREDITS.md) for the 4-layer re-derivation discipline + [LICENSE-DATA §4](LICENSE-DATA) for downstream consumer integration guidance.

**DMCA / takedown posture:** Argus's doctrinal grounding is Feist factual-data + 17 USC §1201(j) security-research exemption + 37 CFR §201.40(b) + nominative fair use. Vendor attribution disputes route through a GitHub issue.

---

## Canonical sources

Descriptive references used in this document map to canonical bible
anchors as follows. The canonical bible (`PROJECT_BIBLE.md` and the
amendment ledger `BIBLE_AMENDMENTS.md`) holds the authoritative
specification; this document is the public-facing summary.

| Descriptive reference (as used in this doc) | Canonical source |
|---|---|
| hard-rule set | `PROJECT_BIBLE.md` §11 |
| canonical 12-value `device_category` vocabulary / canonical lexicon | `PROJECT_BIBLE.md` §2.1 |
| multi-purpose-vendor carveout / multi-purpose-vendor discipline | `PROJECT_BIBLE.md` §11 #10, §11 #13 |
| decompiled-output non-redistribution rule | `PROJECT_BIBLE.md` §11 #15 |
| Feist facts-only promotion regime / Feist facts-only | `PROJECT_BIBLE.md` §11 #16 |
| canonical sentinel-key (`notes.upstream_license_posture`) | `PROJECT_BIBLE.md` §11 #16 |
| source-url-direct discipline | `PROJECT_BIBLE.md` §11 #1 |
| no-PII discipline / PII default-to-HOLD | `PROJECT_BIBLE.md` §11 #3 |
| amendment-log discipline | `PROJECT_BIBLE.md` §11 #11 |
| operator-stack self-exclude discipline | `PROJECT_BIBLE.md` §11 #12 + §8.4 |
| source-type ten-value enum / source-type ceiling rules | `PROJECT_BIBLE.md` §8.2 |
| confidence model | `PROJECT_BIBLE.md` §5 |
| corroboration math / corroboration-lift rule | `PROJECT_BIBLE.md` §8.3 |
| Lynceus mapping | `PROJECT_BIBLE.md` §4.4 |
| export shape | `PROJECT_BIBLE.md` §7.5 |
| source-type taxonomy refinement (registry-vs-regulatory) | `BIBLE_AMENDMENTS.md` CP15 |
| behavioral_signatures sibling export | `BIBLE_AMENDMENTS.md` CP18 |
