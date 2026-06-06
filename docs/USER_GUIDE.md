# Argus User Guide

A plain-language tour of what Argus is, what's in the dataset, and how to use the exports.

If you've never used Argus before, this is the right place to start. For the project summary, see [`../README.md`](../README.md). For developer setup (cloning, running migrations, regenerating exports), see [`engineering/SETUP.md`](engineering/SETUP.md). For the formal specification, see [`engineering/PROJECT_BIBLE.md`](engineering/PROJECT_BIBLE.md).

---

## 1. What is Argus

Argus is an open-source database of **surveillance equipment identifiers** used by US law enforcement and adjacent operators. It tracks the wireless and regulatory fingerprints of vendor hardware — things like the OUI prefix on a Hikvision camera's MAC address, the FCC grantee code that identifies a Cellebrite forensic device, the BLE service UUID broadcast by a Flock Safety ALPR, the cloud hostname embedded in an Anduril counter-drone system's companion app, and the GSMA-allocated IMEI Type Allocation Code that identifies a vendor's specific phone or modem model.

Concrete examples of what's in the lexicon:

- **Hikvision** and **Dahua** — Chinese CCTV camera giants whose equipment is widely deployed across US law enforcement (and is the subject of the NDAA §889 federal procurement ban). Their NDAA attribution carries through into Argus.
- **Cellebrite** — Israeli forensic device-extraction vendor whose UFED tools are used to extract data from seized phones.
- **Anduril Industries** — counter-drone systems sold to CBP and DoD; added at v1.5.0, with several of its product lines set to be split into separate entries in future versions.
- **Flock Safety** — automated license plate reader (ALPR) cameras deployed across thousands of US municipalities; its e4:aa:ea:80:a1:9b MAC was the very first identifier Argus recorded.
- **Geotab**, **Verizon Connect**, **Samsara**, **Motive**, **Lytx**, **Omnitracs** — fleet telematics vendors that produce vehicle-tracking devices used in both commercial fleets and police vehicle deployments.
- **Rohde & Schwarz** — German signals-intelligence vendor whose products include IMSI catchers and adjacent cellular intercept equipment.
- **Elbit Systems of America**, **General Atomics**, **TCOM**, **Persistent Surveillance Systems** — aerostat and persistent aerial surveillance platforms.
- **Camero**, **NIITEK**, **TiaLinx** — through-wall UWB radar vendors operating under the FCC §15.519 law-enforcement-only regulatory carveout.
- **BI Incorporated**, **Attenti**, **STOP**, **Sentinel Offender Services**, **Track Group** — electronic monitoring / ankle-monitor vendors used in pretrial release, parole, and immigration detention contexts.

**Argus is a database, not a real-time monitor.** It tells you what an identifier *is* — which vendor made it, what category of equipment it's associated with, what confidence we have in that attribution, and where that information came from. It does not tell you whether a specific identifier is currently transmitting in your neighborhood. That part is the job of downstream scanners (Lynceus for RF, Rayhunter for cellular IMSI-catcher detection) that consume Argus's exports as their watchlist input.

**Argus is also a provenance database.** Every identifier traces back to a public source — an IEEE OUI allocation, an FCC grantee registration, a community researcher's GitHub repo, an academic paper, a vendor's published documentation, an SEC Exhibit 21 subsidiary disclosure, a court filing, a procurement record from USAspending.gov or SAM.gov. If a source doesn't yield concrete evidence, the row doesn't ship. The discipline framework that enforces this is documented in [`engineering/PROJECT_BIBLE.md`](engineering/PROJECT_BIBLE.md); the formal change log for the discipline framework lives in [`engineering/BIBLE_AMENDMENTS.md`](engineering/BIBLE_AMENDMENTS.md).

---

## 2. What's in the export

Argus ships four export files alongside the source SQLite database. Pick the one that matches your use case:

### `exports/argus_export_high_confidence.json` (146 rows at v1.6.2)

This is the strict export. It only contains rows where:

- The `confidence` score is **at least 70 on a 0-99 scale** (the high-confidence cutoff).
- The source isn't `crowdsourced` or `inferred` — community researcher repositories and cohort-prediction admissions are excluded from this export to keep the false-positive rate low.
- The `device_category` isn't `unknown` — multi-purpose vendors that don't map cleanly to a single surveillance category (for example, Northrop Grumman or Lockheed Martin) are excluded by design.

**Use this export when:** you're feeding a runtime scanner (Lynceus) that's going to alert on matches. You want the false-positive rate to be as close to zero as feasible.

### `exports/argus_export.json` (592 rows at v1.6.2)

The standard export. Same shape as the high-confidence export, but with a looser confidence floor (≥30) and a US-scope filter applied.

**Use this export when:** you want broader scanner coverage and you're willing to accept more false positives, or you're doing analytical work where you want to see the medium-confidence rows.

### `exports/argus_export.csv` (41,508 data rows at v1.6.2)

The rich-import export. All active rows, including the `device_category='unknown'` rows that don't ship in the JSON exports. Has 15 columns covering identifier, identifier_type, device_category, manufacturer, model, confidence, source_url, source_type, geographic_scope, first_seen, last_verified, and audit metadata.

**Use this export when:** you're hydrating a downstream watchlist with operator-side filters, doing analytical research, or building derivative tooling. Apply your own filters (geographic scope, device category, confidence floor) at import time — the CSV gives you everything and lets you decide what to keep.

**CSV consumer note:** line 1 of the CSV is a `# meta:` comment with schema version, export timestamp, and record counts (the `record_count=41508` field is the canonical data-row count; the physical file is longer because some quoted `notes` and `source_excerpt` fields contain embedded newlines). Line 2 is the column header. Use `csv.DictReader` with a sniffer or `pandas.read_csv(comment='#')` to handle it correctly.

### `exports/argus_export_behavioral_signatures.json` (125 rows at v1.6.2)

The sibling export for cellular-band scanners. Where the other three exports key on wire-observable patterns (MACs, OUIs, BLE UUIDs, and the like), this one keys on cellular-control-plane behavioral patterns associated with IMSI-catcher detection. Rayhunter consumes this format. It draws from the 201 active behavioral-signature patterns; the 125 that meet the threshold rules ship in this export.

### What each row represents

Every row in the JSON exports carries a stable shape:

```json
{
  "pattern": "e4:aa:ea:80:a1:9b",
  "pattern_type": "mac",
  "description": "Flock Safety ALPR camera",
  "argus_record_id": "1234abcd5678ef90",
  "confidence": 95,
  "device_category": "alpr",
  "source_type": "primary_registry"
}
```

- **`pattern`** is the actual identifier — the MAC, the OUI prefix, the BLE UUID, the FCC grantee code, the hostname, etc.
- **`pattern_type`** says what kind of identifier this is (`mac`, `oui`, `mac_range`, `bssid`, `ssid_exact`, `ble_uuid`, `ble_service`, `fcc_grantee_code`, `vendor_controlled_hostname`, etc. — **58 values total at v1.6.2**, of which 49 carry promoted rows).
- **`description`** is a human-readable label — usually "Vendor Name — model or category context".
- **`argus_record_id`** is a 16-hex-character stable identifier. It survives source-attribution changes, confidence drift, and most schema migrations. Bind to this when you need to track a specific row across export versions.
- **`confidence`** is the 0-99 confidence score. ≥70 = strong attribution from at least one canonical source. ≥85 = cross-corroborated by independent second source.
- **`device_category`** is what kind of equipment this is (`alpr`, `imsi_catcher`, `body_cam`, `drone`, `cctv_camera`, `persistent_surveillance`, `through_wall_radar`, `gps_tracker`, `network_surveillance` (added at v1.6.2 for lawful-intercept and monitoring-center vendors), and others — **17 values total at v1.6.2**, of which 16 carry promoted rows).
- **`source_type`** is the source-class band (`primary_registry`, `regulatory`, `academic`, `manufacturer_doc`, `manufacturer_app`, `crowdsourced`, `inferred`, `judicial_filing`, `disclosure_filing`, `procurement_disclosure`, and others — **13 values total at v1.6.2** on both the `identifiers` and `sources` tables). Different bands have different confidence ceilings.

---

## 3. How to use it

Three common usage patterns:

### Pattern A — "Is vendor X deployed near me?"

You ran a Wi-Fi scan or a Bluetooth scan in your neighborhood, and you want to know whether anything you observed is surveillance equipment.

1. Pull `argus_export.csv` and filter to the identifier types relevant to your scan: `mac`, `oui`, `mac_range`, `bssid`, `ssid_exact`, `ssid_pattern`, `ble_uuid`, `ble_service`, `ble_local_name`, etc.
2. For each MAC you observed, check whether its OUI prefix (the first 24 bits, e.g. `e4:aa:ea` from `e4:aa:ea:80:a1:9b`) matches anything in the lexicon. Many vendor identifications work at the OUI level, not the full MAC.
3. If you find a match, read the `description` and `confidence` columns. A confidence ≥85 row is reasonably trustworthy. A confidence 30-70 row is a "maybe — needs more evidence."
4. Cross-reference the `source_url` column to see where that attribution came from. If it's a single crowdsourced row at confidence 60, treat it more cautiously than a dual-cited primary_registry + academic row at confidence 90.

### Pattern B — "Build a watchlist for my scanner"

You're running Lynceus or a similar RF security monitor and you want to alert when Argus-listed equipment is detected nearby.

1. Pull `exports/argus_export_high_confidence.json` on your scanner's startup or per refresh cycle.
2. For each row, match `pattern` + `pattern_type` against your scanner's observed identifiers. The shape is designed for direct integration — no transformation needed.
3. Enrich alerts with `description` + `argus_record_id`. The `argus_record_id` is the stable handle for the row across Argus version bumps.
4. Apply severity rules operator-side via your scanner's configuration. Argus does not ship severity rankings — that's intentionally an operator decision (a Flock camera in a friendly neighborhood and one in a hostile context warrant different responses).
5. Honor the operator-stack self-exclude discipline: Argus operator-side hardware (Raspberry Pi OUIs, Rayhunter-supported modem VID:PIDs) MUST NOT appear in the high-confidence export and your scanner should NOT alert on its own hardware.

### Pattern C — "Cross-reference regulatory and procurement data"

You're researching what surveillance equipment a specific agency has procured.

1. Pull the `procurement_records` table from the SQLite database (not the exports — this data is in the DB, not exported to JSON/CSV).
2. Filter by `awarding_agency_name` or `awarding_subagency_name` to your agency of interest.
3. Cross-reference the vendor names against the `manufacturers` table to see which surveillance-equipment vendors that agency has procured from.
4. Pull `deployment_observations` for any direct deployment evidence (camera locations, ALPR placements) — note the `LICENSE` column on each row; commercial use of CC-BY-NC-SA-4.0 rows (EFF Atlas of Surveillance) requires honoring the non-commercial clause.

For Lynceus-specific integration shapes (file paths, refresh cadence, `severity_overrides.yaml`), see the integration handoff notes referenced from [`engineering/BIBLE_AMENDMENTS.md`](engineering/BIBLE_AMENDMENTS.md).

---

## 4. Coverage caveats (honest)

Argus is canonical-enrichment-strong and deployment-detection-modest. Here's what that means in practice.

**The lexicon is comprehensive.** At v1.6.2 there are **126 manufacturers** in the curated list (up from 92 at the v1.5.0 release). Every major surveillance category has multiple representative vendors: ALPR, IMSI catchers, body cams, drones, CCTV, ankle monitors, fleet telematics, counter-drone, persistent surveillance, through-wall radar, gunshot detection, face recognition, forensic extraction, and lawful-intercept / network surveillance (added as its own category at v1.6.2). An earlier expansion targeted under-represented categories: counter-drone vendors went from 4 to 13+, and fleet telematics from 0 to 6. A later round added Pen-Link, SS8 Networks, Cognyte, Utimaco LIMS, Polaris Wireless, and Trovicor under the new `network_surveillance` category.

**The deployment-detection surface is still modest.** Most identifiers in the canonical state are **FCC grantee codes**, **vendor-controlled hostnames**, **certificate SAN entries from crt.sh CT logs**, and **IEEE OUI allocations** — they confirm "this vendor exists and ships product" but they don't give a runtime scanner a wire-observable signature to alert on. The most-deployment-actionable identifier classes — full MACs, BSSIDs, SSID patterns, BLE service UUIDs, drone Remote-ID prefixes — represent a smaller fraction of the database. That gap is closing through ongoing companion-app analysis, but progress comes vendor by vendor.

**Why this is:** the most directly-deployable identifiers (BLE UUIDs, BSSIDs, SSID patterns) typically come from vendor companion-app decompilation, which is permitted but labor-intensive. Argus has decompiled the companion apps for Flock Safety, Hikvision Hik-Connect, Dahua DMSS, Motorola WAVE PTT, Parrot FreeFlight 6, DJI Industry Pilot, and a handful of others. There are many more vendors whose apps haven't been analyzed yet — that's where future research waves will land their gains.

**Coverage by category is uneven.** ALPR coverage is deep (DeFlock contributed 101,597 deployment observations). IMSI catcher behavioral signature coverage is moderate (201 patterns, mostly from the Marlin academic foundation). CCTV camera vendor coverage is broad but mostly at the FCC grantee + corporate-entity level, not the per-model-MAC level. Counter-drone coverage is broad at the vendor level (11 vendors as of v1.5.0) but thin at the identifier level, since these are mostly DoD and CBP suppliers without consumer-facing apps to decompile.

**Geographic scope is US-centric.** Argus's source-admission process applies a US-scope filter at the export level and prioritizes US-anchored sources (FCC EAS, FAA, SAM.gov, USAspending.gov, SEC EDGAR, and US state Secretary-of-State registries). International vendors are included when they ship to US law enforcement (Hikvision, Dahua, Cellebrite, Rohde & Schwarz, Elbit, Parrot, DJI), but the deployment data is primarily US.

---

## 5. What this is NOT

A few things Argus is deliberately not:

- **Not a real-time monitor.** Argus is the lexicon; the scanner is the monitor. If you want to know whether there's a Hikvision camera 30 meters from you right now, you need a scanner like Lynceus with Argus's exports loaded as its watchlist. Argus alone can't tell you what's nearby.
- **Not a "spy on my neighbor" tool.** Every row in the canonical database is keyed to *vendor and equipment category*, not to *individuals or specific deployments*. We can tell you that a given FCC grantee code maps to "Flock Safety, ALPR" — we don't track which neighborhoods Flock has cameras deployed in.
- **Not a deanonymization tool.** Argus has a strict no-PII rule. Officer names, badge numbers, home addresses, and registered agents listed at a residential address are all excluded by default. Ambiguous cases, where a name might belong to a person rather than a company, are held back rather than published.
- **Not exhaustive.** With **126 manufacturers** in the canonical curated list and **41,508 active identifiers** at v1.6.2 ship (vs 92 / 35,812 at v1.5.0), we miss many surveillance vendors that ship to US LE. Notable gaps include some smaller regional ALPR vendors, many of the long tail of body-cam OEMs, and most non-US drone vendors. Coverage expansion happens via community contribution and per-cycle research waves.
- **Not a fabrication machine.** If we don't have a citable public source for an identifier, the answer is "no record" — not "plausible record." The discipline framework prevents AI-driven fabrication; every entry must clear a source-attestation check before it is published.
- **Not authoritative for vendor disputes.** Vendors who disagree with their inclusion or categorization can open a GitHub issue. Argus's doctrinal grounding is *Feist v. Rural Telephone Service* (factual data not copyrightable) + 17 USC §1201(j) (security research exemption) + 37 CFR §201.40(b) + nominative fair use.

---

## 6. Where to learn more

- [`../README.md`](../README.md) — Project overview, headline metrics, downstream consumer architecture.
- [`../CHANGELOG.md`](../CHANGELOG.md) — Version-by-version release history (v1.0.0 through v1.6.6).
- [`../CREDITS.md`](../CREDITS.md) — Per-source attribution, per-vendor canonical lexicon, license posture for downstream consumers.
- [`engineering/METHODOLOGY.md`](engineering/METHODOLOGY.md) — How source admissions work, confidence model, dedup logic, provenance discipline.
- [`engineering/DATA_DICTIONARY.md`](engineering/DATA_DICTIONARY.md) — Schema reference (every table, column, enum value).
- [`engineering/PROJECT_BIBLE.md`](engineering/PROJECT_BIBLE.md) — Formal canonical specification (the source-of-truth at any disagreement).
- [`engineering/BIBLE_AMENDMENTS.md`](engineering/BIBLE_AMENDMENTS.md) — Append-only log of changes to the project's rules, with case studies.
- [`engineering/SETUP.md`](engineering/SETUP.md) — Developer setup (clone, verify, run migrations, regenerate exports).

---

## 7. How to contribute

External contribution is welcome. The discipline framework is documented in [`engineering/PROJECT_BIBLE.md`](engineering/PROJECT_BIBLE.md); the layered amendments are in [`engineering/BIBLE_AMENDMENTS.md`](engineering/BIBLE_AMENDMENTS.md). Concrete contribution paths:

- **New identifier rows.** Submit a GitHub PR adding `raw_observations` rows that cite a concrete file-path source URL (not a bare repo URL). Before a row becomes a canonical identifier, it must trace to that cited source and clear the confidence ceiling for its source type.
- **New sources.** Open a GitHub issue proposing the source. Argus distinguishes 13 source_type bands; each has a different confidence ceiling. Crowdsourced GitHub repositories are accepted under the Feist facts-only regime (NO_LICENSE_DECLARED permitted; compilation arrangement NOT republished).
- **New device categories or identifier types.** Schema-impacting changes coordinate with the amendment process: every new `device_category` or `identifier_type` value pairs with an amendment-log entry and a schema update.
- **Vendor attribution disputes.** Open a GitHub issue. Argus's discipline framework supports retroactive recategorization, supersession with audit trail, and per-row reclassification when new evidence arrives. The audit-trail tables (`source_reclassifications`, `confidence_history` in `notes`, `corroboration_chain` in `notes`) make every change reversible.
- **Test the exports.** Pull the JSON and CSV exports and run them against your own scanner setup. If you find a false positive, open an issue with the `argus_record_id`, your observed environment, and any context that helps determine whether the row should be demoted or kept.

For the formal specification of the contribution discipline (every contribution must trace to a concrete source URL with no PII, every promotion gates on band-ceiling + corroboration math, every schema change pairs with a `BIBLE_AMENDMENTS.md` entry), see [`engineering/PROJECT_BIBLE.md`](engineering/PROJECT_BIBLE.md).

For developer environment setup (cloning, running migrations, regenerating exports, running the test suite), see [`engineering/SETUP.md`](engineering/SETUP.md).
