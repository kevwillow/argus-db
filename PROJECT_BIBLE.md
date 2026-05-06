# Argus — Surveillance Identifier Intelligence Database

**Working name:** Argus (the many-eyed watcher; intel layer that feeds the scanner project)

**Companion project:** the Raspberry Pi wireless scanner (consumes Argus exports)

---

## 0. How to Read This Document



- **Sections 1–5** are context and reference. Re-read relevant sections before each phase.




- **Sections 10–12** are operating principles, hard rules, and human checkpoints.



---

## 1. Vision & Mission

**Vision:** A consolidated, well-attributed, queryable database of wireless identifiers (MAC addresses, OUIs, BSSIDs, SSID patterns, BLE UUIDs, device fingerprints) for surveillance and law-enforcement-adjacent equipment, derived entirely from public sources.

**Mission for this run:** Build the database, populate it from every viable public source, and produce a clean export consumable by a downstream Raspberry Pi scanner that alerts when matching devices are detected nearby.

**Why this exists:** Tools to surveil people are abundant; tools to detect surveillance are not. The asymmetry favors the surveillor. Argus narrows the gap.

---

## 2. Scope

### 2.1 In Scope (Device Categories)

The database must aim to cover, in priority order:

1. **Fixed ALPR / camera systems** — Flock Safety, Vigilant Solutions, Motorola Vigilant, Genetec, Rekor, Avigilon, Axis traffic cams
2. **IMSI catchers / cell-site simulators** — Harris StingRay/Hailstorm/Crossbow, Digital Receiver Technology DRTBox, Septier, KeyW, Jacobs/Engility variants
3. **Body cameras** — Axon (Body 2/3/4), Motorola Solutions V300/V500, Reveal, WatchGuard, Getac
4. **Police radios** — Motorola APX series (APX 6000/8000/N70), L3Harris XL series, Kenwood VP/NX series (when used by LE)
5. **In-vehicle LTE/WiFi routers** — Cradlepoint (IBR900/R1900-class mobile routers), Sierra Wireless (MG90 / AirLink GX/RV-class). Distinct from police radios in §2.1 #4: these are LTE backhaul + in-cabin WiFi routers, not P25/VHF voice radios. Every modern patrol car carries one as the data link for laptops, dashcams, and body-cam offload. Added in Correction Pass 3 (BIBLE_AMENDMENTS).
6. **Police drones** — DJI Matrice (LE configurations), Skydio X-series, BRINC LEMUR, Parrot ANAFI USA
7. **Acoustic gunshot detection** — SoundThinking (formerly ShotSpotter) sensors
8. **Hacking / forensics gear** — Hak5 (WiFi Pineapple, Bash Bunny, Packet Squirrel), Cellebrite UFED, Magnet GrayKey, Berla iVe
9. **Covert / surveillance cameras** — pole cameras, body-worn covert, common LE-deployed IP cam models
10. **GPS trackers and tags** — common LE-deployed tracker models (covert vehicle trackers); also AirTag/Tile/SmartTag for the recurrence-detection feature
11. **Facial recognition / video analytics** — BriefCam, Rekor, Clearview-deployed endpoints (where detectable)
12. **Drone detection systems** — Dedrone, DroneShield (these are themselves wireless emitters)

### 2.2 Out of Scope

- Anything requiring private data, leaks, or non-public access
- Real-time deanonymization of individual officers or agencies (we identify *equipment categories*, not people)
- Active interference, jamming, or attack tooling — Argus is a passive identification database only
- Detection logic itself (that lives in the scanner project; Argus only produces identifiers + metadata)
- Cellular IMSI/IMEI databases (different problem space, legal complexity, out of scope)
- Anything where the underlying source is classified or restricted

### 2.3 A Note on Ambition

The human chose "everything in one shot" for v1. Honor that, but be honest in progress reports about coverage. It is better to have 200 high-confidence Flock records than 5,000 low-confidence guesses across 15 categories. If a category has no good public sources, document that and move on rather than fabricating coverage.

---

## 3. Architecture

### 3.1 Pipeline Topology

```
┌─────────────────────────────────────────────────┐
│                                                 │
│                                                 │
│                                                 │
│  - Handles dedup, conflict resolution, exports  │
└─────────────────┬───────────────────────────────┘
                  │
       ┌──────────┼──────────┬──────────┬─────────┐
       ▼          ▼          ▼          ▼         ▼
   ┌───────┐  ┌───────┐  ┌────────┐  ┌──────┐  ┌──────┐
   │  DB   │  │Source │  │Extract │  │Valid-│  │Export│
   │Archi- │  │Workers│  │Workers │  │ator  │  │Worker│
   │ tect  │  │(many) │  │(LLM)   │  │      │  │      │
   └───────┘  └───────┘  └────────┘  └──────┘  └──────┘
```

### 3.2 Data Flow

```
Source → Source Worker → Staging Table → Extraction (if needed)
       → Normalization → Validation → Dedup → Main Table
       → Export Worker → SQLite + JSON + CSV
```

Every record carries provenance from staging through export. No record loses its source URL.

---

## 4. Data Schema

The schema is the contract. All sub-agents output rows conforming to this.

### 4.1 Main table: `identifiers`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | autoincrement |
| `identifier` | TEXT NOT NULL | the actual MAC/OUI/UUID/SSID/BSSID, normalized |
| `identifier_type` | TEXT NOT NULL | enum: `oui`, `mac`, `mac_range`, `bssid`, `ssid_exact`, `ssid_pattern`, `ble_uuid`, `ble_service`, `device_fingerprint` |
| `device_category` | TEXT NOT NULL | enum from §2.1 (alpr, imsi_catcher, body_cam, police_radio, in_vehicle_router, drone, gunshot_detect, hacking_tool, covert_cam, gps_tracker, face_recog, drone_detect) |
| `manufacturer` | TEXT | normalized vendor name |
| `model` | TEXT | when known |
| `confidence` | INTEGER | 0–100, see §8.2 |
| `source_url` | TEXT NOT NULL | direct URL to the evidence |
| `source_type` | TEXT NOT NULL | enum: `official`, `regulatory`, `procurement`, `academic`, `foia`, `crowdsourced`, `inferred`, `manufacturer_doc` |
| `source_excerpt` | TEXT | short quoted/paraphrased justification (≤200 chars) |
| `geographic_scope` | TEXT | ISO country/region codes, comma-sep, or `global` |
| `first_seen` | DATETIME | when we first ingested this record |
| `last_verified` | DATETIME | when a source-check last confirmed |
| `notes` | TEXT | free text |
| `superseded_by` | INTEGER | FK to `identifiers.id` if this record was merged into another |

### 4.2 Supporting tables

- **`sources`** — registry of every source crawled, with last-fetch timestamp and status
- **`raw_observations`** — staging table; raw extracted records before normalization (preserve forever for audit). Holds rows that carry an actual or candidate identifier (MAC/OUI/BSSID/SSID/UUID) in `candidate_identifier` keyed by §4.1 `identifier_type`.
- **`deployment_observations`** — staging table for Tier 1 sources that yield agency × technology × location × vendor metadata but **no** MAC/OUI/SSID/UUID identifier (EFF Atlas of Surveillance, DeFlock). Identifier columns intentionally absent — promotion to `identifiers` requires a Phase 3+ inference linking a deployment to a concrete identifier candidate (§11 #1). Idempotency keyed by `(source_id, source_row_key)` where `source_row_key` is the source's stable per-row natural key (e.g. Atlas's `AOSNUMBER`). Added in Correction Pass 4 (BIBLE_AMENDMENTS).
- **`procurement_records`** — staging table for Tier 2/3 procurement-only rows (SAM.gov, city council minutes, FOIA-released procurement docs) that name an agency × vendor purchase but carry **no** MAC/OUI/SSID/UUID identifier. Schema includes a nullable `linked_identifier_id` FK back to `identifiers` for the upgrade path when a later source attaches a concrete identifier to the same purchase. Per §4.5 procurement-only carveout / §11 #14, these rows are NEVER exported to Talos — they are analytical only. Created in MAC-2 / Phase 1 (signed off at Checkpoint 1); documented in §4.2 in Correction Pass 5 (BIBLE_AMENDMENTS).
- **`fcc_grantees`** — staging table for FCC EAS grantee registrations (Phase 3 / MAC-7; first source = opendata.fcc.gov dataset `3b3k-34jp`, USGOV_WORKS public domain). Holds grantee_code → entity-name + mailing/contact metadata + date_received. Identifier columns intentionally absent — `grantee_code` is a regulatory entity prefix, not a per-device identifier (per-device FCC IDs are formed `grantee_code + product_code`, owned by Phase 4 `fcc_equipment_filings` if/when created). Idempotency keyed by `(source_id, source_row_key=grantee_code)`. Stale-mirror sources: `sources.notes` MUST carry `dataset_freeze_date` + `staleness_warning` when the upstream mirror is documented stale (3b3k-34jp is frozen at 2021-03-22; Flock Safety + post-2020 grantees absent — Phase 4 owns the gap). Added in Correction Pass 6 (BIBLE_AMENDMENTS).
- **`extraction_runs`** — log of every extraction job: agent id, source, started_at, finished_at, records_in, records_out, errors
- **`conflicts`** — when two sources disagree on the same identifier; reviewed and resolved by CEO

### 4.3 Normalization rules

- MAC addresses: lowercase, colon-separated (`aa:bb:cc:dd:ee:ff`)
- OUIs: lowercase, colon-separated 3 octets (`aa:bb:cc`)
- BLE UUIDs: lowercase, hyphenated 8-4-4-4-12 format
- SSIDs: stored exactly as broadcast; pattern fields use POSIX regex
- Manufacturer names: matched against a canonical list maintained in `manufacturers` table; new vendors added explicitly

### 4.4 Talos export mapping

The downstream consumer (Talos, the Raspberry Pi RF security monitor) has a fixed, minimal watchlist schema with `pattern_type ∈ {mac, oui, ssid, ble_uuid}`. Argus's richer `identifier_type` enum must be collapsed at export time. Talos cannot be modified to accept Argus's richer enum; Argus does the collapsing. The export worker (§7.5) applies exactly this mapping:

| Argus `identifier_type` | Talos `pattern_type` | Notes |
|---|---|---|
| `oui` | `oui` | direct pass |
| `mac` | `mac` | direct pass |
| `bssid` | `mac` | a BSSID *is* a MAC for Talos's purposes |
| `ssid_exact` | `ssid` | direct pass |
| `ssid_pattern` | (DROPPED) | Talos has no regex support in v0.2; record in coverage report |
| `ble_uuid` | `ble_uuid` | direct pass |
| `ble_service` | `ble_uuid` | collapsed; BLE service UUIDs *are* UUIDs for Talos |
| `mac_range` | (expand or DROP) | expand into individual MACs at export ONLY if range ≤256 entries; otherwise drop and note in coverage report |
| `device_fingerprint` | (DROPPED) | Talos has no fingerprint matching; analytical-only |

Records that drop out of the Talos export remain in the canonical Argus database for analytical purposes. The coverage report MUST tally Argus-only records by category so the human knows what's not flowing downstream.

See §4.5 for severity derivation, §7.5 for the export-file shape and per-record description format, and §8.4 for additional drop rules (unknown category, Pi self-exclude, procurement-only).

### 4.5 Severity for Talos export

Talos requires a `severity ∈ {low, med, high}` per record. Argus has `confidence` (0–100) but not severity. **Severity is NOT confidence.** Severity expresses "how alarming is it that this device is near me," which is a function of `device_category`, not how sure we are about the identifier.

The export worker (§7.5) derives Talos severity from Argus `device_category` using exactly this mapping:

| `device_category` | Talos `severity` | Reasoning |
|---|---|---|
| `imsi_catcher` | `high` | highest threat to personal privacy |
| `alpr` | `high` | always-on tracking infrastructure |
| `covert_cam` | `high` | covert by definition |
| `hacking_tool` | `high` | hostile gear in personal threat model |
| `gps_tracker` | `high` | literal stalking equipment |
| `face_recog` | `high` | |
| `drone_detect` | `med` | emits, but defensive equipment |
| `body_cam` | `med` | worn by visible LE; less alarming than covert |
| `drone` | `med` | |
| `police_radio` | `low` | routine LE presence |
| `in_vehicle_router` | `low` | routine LE infrastructure (data backhaul, not covert and not personal-threat-model) |
| `gunshot_detect` | `low` | fixed infrastructure, informational |

**Confidence vs. severity rule.** Confidence affects whether a record is exported (threshold 70 for the high-confidence file — see §6 Phase 5 and §7.5), not severity. A high-severity record at confidence 50 is dropped from the high-confidence export entirely; it is NOT downgraded to low severity.

**Procurement-only carveout.** Procurement-only records (`source_type='procurement'` with no MAC/OUI/UUID, only an agency-bought-vendor mapping) are NEVER exported to Talos. They are analytical only. The Talos export contains only records with concrete identifiers. (See also §8.4 and §11 #14.)

---

## 5. Source Catalog

Sources are tiered by structure. Don't try to mine an unstructured source like an academic paper with a generic scraper; route it to the extraction worker.

### Tier 1 — Structured (highest priority, machine-readable)

| Source | What we get | Method |
|---|---|---|
| IEEE OUI registry | All OUIs with vendor names | Direct download (oui.txt, oui.csv from IEEE) |
| Wireshark `manuf` file | Curated OUI extensions, sometimes more granular than IEEE | GitHub raw fetch from wireshark/wireshark |
| EFF Atlas of Surveillance | Deployment locations by agency and type (no MACs but tells us *where* to look) | Site has data exports / API |
| DeFlock | Crowdsourced Flock camera locations | Site has exports |

### Tier 2 — Semi-structured (APIs and queryable databases)

| Source | What we get | Method |
|---|---|---|
| WiGLE.net API | Crowdsourced WiFi/BT observations with geolocation | Authenticated API; rate-limited |
| FCC ID database | Device filings: frequencies, internal photos, sometimes MAC ranges | Searchable by manufacturer/grantee code |
| SAM.gov | Federal procurement records (what agencies bought from whom) | API + bulk export |
| State procurement portals | State/local procurement records | Per-state, varies wildly |

### Tier 3 — Unstructured (mine with extraction worker)

| Source | What we get | Method |
|---|---|---|
| GitHub | Hardcoded identifiers in detection projects, research code | Targeted repo search; mine constants |
| Manufacturer docs / spec sheets | Sometimes leak MAC ranges, BLE service UUIDs, default SSIDs | Targeted PDF/HTML scrape per vendor |
| Academic papers | DEF CON, Black Hat, USENIX, IEEE S&P — characterizations of specific gear | Search Google Scholar, arXiv; read PDFs |
| Conference talk videos / slides | Same as papers, often with specific identifiers shown on screen | Slides easier to mine than video |
| Court filings | FOIA-released documents, motion exhibits, sometimes contain device specs | MuckRock, CourtListener, PACER |
| FOIA archives | MuckRock, GovernmentAttic, Distributed Denial of Secrets | Search aggregators |
| News reporting | Sometimes specific model numbers in investigative pieces | Targeted search per vendor/category |
| Reddit / forums | Low signal but occasionally high-value disclosures (e.g. r/AmateurRadio, r/policeradio) | Search; treat as low confidence |

### Tier 4 — Inferential (derived, not directly sourced)

These are records we *generate* by combining sources, not pulling raw:

- "OUI X is owned by Manufacturer Y, and Manufacturer Y's only product is body cameras → flag as body_cam category"
- "WiGLE shows BSSID pattern Z appearing within 100m of every DeFlock-mapped Flock camera but rarely elsewhere → flag as likely Flock"

Inferred records always have `source_type='inferred'`, capped confidence (≤70), and notes explaining the inference chain.

---

## 6. Acquisition Phases



### Phase 0 — Bootstrap


   ```









   ```





### Phase 1 — Schema & Foundation







### Phase 2 — Tier 1 Structured Sources



- IEEE OUI registry → all OUIs, no category yet (category is filled by inference in Phase 5)
- Wireshark manuf → same
- EFF Atlas of Surveillance → location/agency/category metadata, no identifiers yet
- DeFlock → Flock camera locations (geolocation only at this stage)





### Phase 3 — Tier 2 Semi-structured Sources


























### Phase 4 — Tier 3 Unstructured Mining



**Wave A — GitHub mining:**



**Wave B — Manufacturer documentation:**
- Per-vendor PDF/HTML scrape of public spec sheets, integration guides, FCC filings already pulled in Phase 3.


**Wave C — Academic / conference:**



**Wave D — Court / FOIA:**
- MuckRock, CourtListener targeted searches.


**Wave E — News / forums:**




### Phase 5 — Validation, Dedup, Inference, Export






   - `argus.db` (canonical SQLite)
   - `argus_export.json` (Talos-consumable, all confidences ≥30; applies §4.4 type mapping and §4.5 severity)
   - `argus_export_high_confidence.json` (Talos-consumable, confidence ≥70; recommended default for the scanner)
   - `argus_export.csv` (human-readable, all canonical records)
   - `coverage_report.md` (the matrix, gap analysis, and the §9 item 9 "Dropped from Talos export" tallies)



---

## 7. Pipeline Role Contracts



### 7.1 DB Architect

**Goal:** Initialize SQLite database matching §4 exactly.

**Outputs:** `db/argus.db` with empty tables, schema migrations file, seeded `manufacturers` table.
**Don'ts:** Do not invent extra columns. Do not seed fake data. Do not use ORM if a plain `sqlite3` script suffices.

### 7.2 Source Worker (template)

**Goal:** Pull data from one specific source into the staging table.
**Inputs:** Source URL/API spec, schema for staging, rate-limit guidance.
**Outputs:** Records in `raw_observations` with full provenance, plus a row in `sources` with fetch metadata.
**Behaviors:**
- Always preserve raw response in `raw/<source_name>/<timestamp>.{json,html,csv}` before parsing
- On failure, log to `logs/` and report error; do not silently retry forever
- Respect robots.txt, rate limits, and ToS — if a source forbids scraping, skip it and document why
**Don'ts:**
- Do not invent records when the source is unreachable
- Do not normalize during ingest (that's a separate step)
- Do not deduplicate during ingest

### 7.3 Extraction Worker (LLM)

**Goal:** Pull structured records out of unstructured text/PDF/HTML.
**Inputs:** Document path, target schema fields, examples of valid extractions.
**Outputs:** JSON array of candidate records, each with `source_excerpt` quoting the supporting passage.
**Behaviors:**
- Conservative extraction. If unsure whether a string is a real MAC or an example placeholder, mark `confidence ≤ 40` and note it.
- Always include `source_excerpt` so the validator can audit.
- **Reject identifiers in any of these known-fake/documentation ranges (case-insensitive throughout):**

    *RFC 7042 IPv4 documentation:*
    - `00:00:5e:00:53:00` through `00:00:5e:00:53:ff`

    *RFC 7042 IPv6 documentation:*
    - `02:00:5e:10:00:00:00:01` through `02:00:5e:10:00:00:00:ff`

    *Common documentation/example patterns:*
    - `aa:bb:cc:dd:ee:ff`
    - `00:11:22:33:44:55`
    - `12:34:56:78:9a:bc`
    - `de:ad:be:ef:*:*`
    - `ca:fe:ba:be:*:*`
    - `ba:db:00:b5:*:*`
    - `00:00:00:00:00:00`
    - `ff:ff:ff:ff:ff:ff`
    - any MAC where all 6 octets are identical (`00:00:00:00:00:00`, `11:11:11:11:11:11`, …)
    - any MAC where octets follow a strictly monotonic +1 sequence (`01:02:03:04:05:06`)

    Apply the same patterns to OUIs (3-octet versions of the above). Records matching any of these are rejected by the extractor and routed to the `conflicts` table by the validator (§7.4) with `reason='known_fake_pattern'`.

- **LAA-bit confidence penalty.** For scraped MAC addresses where the locally-administered bit is set (bit 1 of the first octet — i.e., the first octet matches the binary pattern `xxxxxx1x`; examples: `02:*`, `06:*`, `0a:*`, `ae:*`, etc.), apply a confidence penalty:
    - If the source explicitly states this MAC is the device's actual broadcast address: no penalty.
    - If the MAC appears in a code listing, paper, or document without that explicit attestation: cap `confidence ≤ 40` and add a note `lab_bit_set — likely synthetic/randomized`.

  Modern MAC randomization (iOS 14+, Android 10+) and many surveillance devices deliberately use locally-administered MACs. A scraped LAA MAC without strong provenance is more likely an example or a randomized observation than a stable identifier.

**Don'ts:**
- Do not hallucinate identifiers. If the document doesn't contain one, return empty.
- Do not assume a manufacturer's gear is law-enforcement-only without evidence.

### 7.4 Validator

**Goal:** Sanity-check records before promotion to main table.
**Checks:**
- Identifier format valid for its type
- **Identifier not in the known-fake list.** Apply exactly the same enumerated list specified in §7.3 (RFC 7042 IPv4 doc range `00:00:5e:00:53:00`–`ff`, RFC 7042 IPv6 doc range `02:00:5e:10:00:00:00:01`–`ff`, common doc/example patterns `aa:bb:cc:dd:ee:ff`, `00:11:22:33:44:55`, `12:34:56:78:9a:bc`, `de:ad:be:ef:*:*`, `ca:fe:ba:be:*:*`, `ba:db:00:b5:*:*`, `00:00:00:00:00:00`, `ff:ff:ff:ff:ff:ff`, all-identical-octet MACs, strictly monotonic +1 octet sequences). Apply the same patterns to OUIs at the 3-octet level. Matches route to `conflicts` with `reason='known_fake_pattern'`.
- Manufacturer matches `manufacturers` canonical list (or flag for addition)
- `source_url` resolves and contains the claimed `source_excerpt` (spot-check 10% via re-fetch)
- Confidence score consistent with source_type (§8.2)
- No duplicate against existing main-table records (if dup, route to dedup logic)
**Outputs:** Approved records → main table. Rejected records → `conflicts` table with reason. Borderline → human review queue.

### 7.5 Export Worker

**Goal:** Produce final exports per §6 Phase 5. The Talos-bound files (`argus_export.json`, `argus_export_high_confidence.json`) must apply the §4.4 type mapping and §4.5 severity derivation before writing entries.
**Outputs:** Files in `exports/` directory, each with a header comment (in JSON: `_meta` field; in CSV: top-line `# meta`) including: export timestamp, record count, schema version, confidence threshold applied.

**Per-record description format (Talos exports only).** For `argus_export.json` and `argus_export_high_confidence.json`, descriptions must be self-contained and readable as a phone notification. Constraints:

- Maximum 80 characters
- No "see source" references
- No URLs
- No `source_excerpt` fragments — those stay in the canonical DB only
- Format: `{vendor} {product family or generic name} ({short context})`
- Examples:
    - GOOD: `Hak5 WiFi Pineapple (pentest gear)`
    - GOOD: `Axon Body 3 body camera`
    - GOOD: `Apple Find My / AirTag service`
    - BAD: `Hak5 - see source for details`
    - BAD: `Device manufactured by Hak5 LLC, used for wireless penetration testing as documented in https://...`

If a record cannot be described in 80 chars without losing meaning, the canonical record stays but the Talos export uses a generic description like `{category} device` and notes the truncation in the coverage report.

**Talos export file shape (`argus_export.json` and `argus_export_high_confidence.json`).** Both files conform to:

```json
{
  "_meta": {
    "argus_version": "<schema version>",
    "exported_at": "<ISO8601 UTC timestamp>",
    "record_count": 0,
    "confidence_threshold": 0,
    "argus_run_id": "<UUID for this export run>",
    "source_record_count": 0,
    "dropped_in_export": {
      "unknown_category": 0,
      "ssid_pattern": 0,
      "device_fingerprint": 0,
      "oversized_mac_range": 0,
      "procurement_only": 0,
      "self_exclude_oui": 0,
      "below_confidence_threshold": 0
    }
  },
  "entries": [
    {
      "pattern": "<normalized identifier>",
      "pattern_type": "<mac|oui|ssid|ble_uuid>",
      "severity": "<low|med|high>",
      "description": "<≤80 char self-contained description>",
      "argus_record_id": 0
    }
  ]
}
```

`confidence_threshold` is `0` for `argus_export.json` (full export, all confidences ≥30 per §6 Phase 5 / §9) and `70` for `argus_export_high_confidence.json`. The `argus_record_id` field is required and stable across re-runs of the same canonical record; the downstream Talos seeder uses it for upsert semantics (update-existing vs. insert-new) when re-importing later Argus versions. The `dropped_in_export` tallies must reconcile with the coverage report (§9 item 9) such that `source_record_count − sum(dropped_in_export) = entries.length`.

**Don'ts:**
- Do not include the `raw_observations` table in exports
- Do not include `superseded_by` pointers in exports (resolve them first)
- Do not export records with `confidence < 30` to any Talos export file. The floor for `argus_export.json` is `confidence ≥ 30`; the threshold for `argus_export_high_confidence.json` is `confidence ≥ 70`. Records below 30 are tallied as `below_confidence_threshold` in the coverage report.
- Do not export records with `device_category='unknown'` to Talos under any confidence threshold (see §8.4 and §11 #13)
- Do not export procurement-only records (no concrete identifier) to Talos (see §4.5 and §11 #14)
- Do not include OUIs from the Pi self-exclude list (§8.4) in `argus_export_high_confidence.json`

---

## 8. Quality Controls

### 8.1 Provenance is non-negotiable

Every record in the main table has a working `source_url`. Records without provenance are rejected. Period. This is not bureaucracy; it's the difference between a useful database and a liability.

### 8.2 Confidence scoring

| Source type | Default confidence range |
|---|---|
| `official` (IEEE registry, FCC filing) | 90–100 |
| `regulatory` (gov't filing, court order text) | 80–95 |
| `manufacturer_doc` (vendor spec sheet) | 75–90 |
| `procurement` (SAM.gov, state portals) | 70–85 (proves *purchase*, not *deployment*) |
| `academic` (peer-reviewed or conference) | 70–90 |
| `foia` (released documents) | 65–85 |
| `crowdsourced` (WiGLE, DeFlock) | 50–75 |
| `inferred` (derived) | 30–70, capped |
| News, forums, unverified | 20–50 |

Adjust within range based on specificity, recency, and corroboration. Two independent sources at 70 each can corroborate to a single record at 85.

### 8.3 Dedup logic

Two records are duplicates if:
- Identical normalized `identifier` AND `identifier_type`, OR
- One record's identifier is a strict subset of the other (e.g., MAC within an OUI range)

On dedup:
- Keep the record with highest confidence as canonical
- Append all `source_url`s and `source_excerpt`s into the canonical record's notes
- Mark the other record `superseded_by = canonical.id`
- Recompute confidence: `min(99, max(originals) + 5)` for corroboration bonus

### 8.4 False-positive prevention

The single biggest risk to this database is over-claiming. Specific guardrails:

- **Multi-purpose vendors are not categorized at the OUI level.** Motorola Solutions makes police radios *and* hospital pagers *and* warehouse scanners. An OUI alone never gets a `device_category` other than `unknown`. Category requires model-level evidence.
  - **Unknown-category Talos carveout.** Records with `device_category='unknown'` (the multi-purpose vendor case) are NEVER exported to Talos under any confidence level. Talos cannot do anything useful with "unknown category" records — they would either be dropped (silently losing data) or fire as low-severity noise (training the user to ignore alerts). They remain in the canonical Argus database for analytical purposes only. The coverage report must tally these as "analytical-only records" separately from "exported records." (See also §11 #13.)
- **Procurement ≠ deployment.** An agency buying a Stingray doesn't put one on every patrol car. Procurement records add geographic context but never raise an identifier above 85 confidence by themselves.
- **MAC randomization warning.** Modern phones and some modern surveillance gear randomize MACs. Note this in the export readme so the scanner doesn't generate false alerts on randomized devices.
- **Test data filter.** Reject identifiers matching known documentation/example ranges (RFC 7042, locally administered ranges with obvious patterns, vendor demo addresses). The full reject list is enumerated in §7.3 and applied by the validator (§7.4).
- **Pi self-exclude list (running scanner's own hardware).** Talos runs on a Raspberry Pi, which has well-known OUIs:
  - `b8:27:eb` (older Pi boards)
  - `dc:a6:32` (Pi 4 era)
  - `e4:5f:01` (recent boards)
  - `28:cd:c1` (more recent)

  These OUIs MUST NOT appear in the Talos high-confidence export, regardless of source confidence. They appear in the standard export (`argus_export.json`) with `severity='low'` and a description noting "informational — common in DIY hardware." This exclusion list is hard-coded in the export worker (§7.5) and tallied in the coverage report under `self_exclude_oui`. (See also §11 #12.)

---

## 9. Deliverables / Definition of Done

This run is "done" when all of the following are true:

1. `db/argus.db` exists, schema matches §4, all phases complete
2. `exports/` contains:
   - `argus.db` (canonical SQLite)
   - `argus_export.json` (Talos-consumable, all confidences ≥30)
   - `argus_export_high_confidence.json` (Talos-consumable, confidence ≥70)
   - `argus_export.csv` (human-readable, all canonical records)
   - `coverage_report.md`

   Each Talos-consumable JSON file conforms to the schema in §7.5 (including the §4.4 type mapping, §4.5 severity derivation, and the description-format constraints). Each is independently parseable and includes a complete `_meta` block.
3. `coverage_report.md` exists and shows category coverage with honest gap analysis
4. Every record in the main table has a working source_url
5. The validator has run a final pass and `conflicts` table is empty (or every entry is human-resolved)
6. The `argus_cli.py` utility works for `status`, `query`, `export`, `validate`
7. README.md at the project root describes: what the database is, how to consume the export, the schema, the confidence scoring, the limitations, and the legal/ethical scope (§2.2 + §11)

9. Coverage report includes a "Dropped from Talos export" section tallying records held back by category: `unknown_category`, `ssid_pattern`, `device_fingerprint`, `oversized_mac_range`, `procurement_only`, `self_exclude_oui`, `below_confidence_threshold`. Tallies must sum correctly: `source_record_count − sum(dropped) = exported entries count` for each Talos-bound JSON file (matching the `_meta.dropped_in_export` block defined in §7.5).

---

## 10. Operating Principles

- **Ship narrow, then widen.** A working pipeline for one category is more valuable than a half-broken pipeline for ten. Even though scope is "everything," internal sequencing should still go category-by-category within each phase.
- **Prefer fewer high-quality records to many low-quality ones.** The downstream scanner alerts on matches. Every false positive trains the user to ignore alerts. Precision over recall.




---

## 11. Critical Don'ts

These are hard rules. Violating any of these is a stop-the-line event.

1. **Do not fabricate identifiers.** If a source doesn't yield concrete data, the answer is "no records," not "plausible records."
2. **Do not access non-public data.** No leaked databases, no cracked APIs, no scraping authenticated content the human isn't entitled to.
3. **Do not include personally identifying information.** This database is about *equipment*, not *people*. If a source mentions an officer's name, badge, home address — strip it. We identify *categories of devices*, not *individuals*.
4. **Do not generate detection logic.** That's the scanner project's job. Argus produces identifiers and metadata; rules live downstream.
5. **Do not include active-attack tooling guidance.** No jamming techniques, no spoofing, no evasion playbooks. Identification only.
6. **Do not violate ToS or scrape sources that explicitly forbid it.** Document the skip in `coverage_report.md` instead. WiGLE in particular: respect their API ToS — they're allies, not adversaries.
7. **Do not promote a record to the main table without provenance.** Provenance is the database. Without it, we have a rumor.
8. **Do not let confidence drift upward without corroboration.** Confidence only rises when a second independent source confirms.
9. **Do not skip checkpoints.** Even if a phase looks easy, stop and report.
10. **Do not categorize at the OUI level for multi-purpose vendors** (see §8.4).
11. **Do not skip the `BIBLE_AMENDMENTS.md` log entry when making in-place bible edits or adding sub-agent-level rules.** The git diff is the source of truth, but the amendment log is the human-readable trail. An undocumented amendment is a process violation regardless of whether the edit itself is correct.
12. **Do not export OUIs that match the running scanner's hardware family** (Raspberry Pi OUIs as enumerated in §8.4) in the high-confidence Talos export. They go in the standard export at `severity='low'` only.
13. **Do not export records with `device_category='unknown'` to Talos** under any confidence level. They remain canonical-only (see §8.4).
14. **Do not export procurement-only records (no concrete identifier) to Talos.** Procurement records establish vendor-agency relationships, not device presence. They are analytical only (see §4.5).

---

## 12. Open Questions



**Open**

- **WiGLE API credentials.** Human needs to provide an API key. Argus is useless without it for Phase 3. Required before the Phase 3 Step-0 budget estimate fires (§6 Phase 3 / Checkpoint 3a). (Status at CP5: pitch-behavior binding holds verbatim through 2026-05-18; carries forward unchanged.)
- **Configurable `geographic_scope` filter for the high-confidence Talos export.** Should the high-confidence export filter records by configurable geographic scope (e.g., default = `US`)? Two adjacent realities surfaced this question at Checkpoint 2: (a) DeFlock ingest holds ~849 international ALPR nodes (Netherlands, Australia, Italy, Denmark, plus Polizia/Politie blocks) — Talos is currently a US-deployed scanner, so non-US deployment records are dead weight in the watchlist; (b) DeFlock also holds private-sector retail ALPR records (HOA / shopping-mall installations) which the Phase-2 board call placed out-of-scope for V1 but kept in-staging for potential V2 reconsideration. A single export-time categorical filter (geographic + sector) handles both axes without separate ingestion paths. Records stay in `deployment_observations` regardless; export shape is the only thing that changes. Decide at Phase 5 alongside the Talos export design. (Added by Correction Pass 5. Status at CP5: CEO-recommended path is configurable string column on `identifiers`, default US, filter at export-time — would land as Correction Pass 7. Held for explicit board direction; Wave-A row currently at NULL placeholder. Deferrable to Talos integration handoff.)

**Deferred at CP5 sign-off (2026-05-06) — revisit at Wave-F / Phase-6**

- **Single-product §2.1 vendor OUI categorization at export time — narrow §11 #10 / §5 Tier 4 reading vs strict §8.4.** CP5 row-count visibility per disposition surfaced (CP5_BRIEF §3.1): under narrow-read carve-out, ~18 of 62 inferred rows would flip out of `unknown` — `DJI=13`, `Flock Safety=1` inferred, `Skydio=1`, `Cellebrite=1`, `SoundThinking=1`, with all 17 inferred rows still below the conf=70 high-confidence band so they stay standard-export-only. Board ratified CEO path-(a): accept v0.1 with strict §8.4. The narrow-read carve-out is queued for Wave-F / Phase-6 once model-level evidence sweeps raise a vendor cluster's per-row band into 70-cap territory. (CP5 sign-off via approval [`71ef8139`](/MAC/approvals/71ef8139-c76c-4b1b-8971-b22720b7363d) 2026-05-06T20:17:10Z.)
- **§4.4 256-entry `mac_range` expansion ceiling — OUI-prefix routing without expansion.** All 8 active `mac_range` rows are OUI-28 / OUI-36 sub-allocations vastly exceeding §4.4's expansion ceiling, so even if §3.1 narrow-read flipped their `device_category`, they'd re-fall to `oversized_mac_range`. Board ratified CEO path-(c): defer routing semantics to Talos integration handoff (jointly bound between Argus export shape and Talos seeder protocol). (CP5_BRIEF §3.2; CP5 sign-off 2026-05-06.)

**Bound to Talos integration handoff (post-CP5)**

- **`argus_record_id` upsert semantics in Talos seeder.** Argus-side stable-id is in place (`argus_run_id` deterministic UUID5 over the active-set fingerprint; `argus_record_id` = `identifiers.id`, stable across re-runs). Talos-side upsert vs destructive drop-and-reload protocol is the open piece. SAR-2 lean (upsert) holds as intended direction; binding decision is bilateral with Talos team. (CP5 carries this forward to integration handoff per CP5_BRIEF §4 #2.)

**Resolved at CP5 sign-off (2026-05-06)**

Board ratification via approval [`71ef8139`](/MAC/approvals/71ef8139-c76c-4b1b-8971-b22720b7363d) 2026-05-06T20:17:10Z (CP5_BRIEF, commit `28bab20`, [MAC-47](/MAC/issues/MAC-47)).

- ~~**Project name.** "Argus" working name; final confirm at Checkpoint 5 alongside the coverage matrix.~~ Resolved: **"Argus" is the final v1 name.** Boundary: Argus owns identifier-canonical-state + Talos-bound exports; Talos owns scanner-side scanning + correlation. "MAC" is the Paperclip issue-prefix only.
- ~~**`device_cluster_id` for vehicle / operator correlation.**~~ Resolved: **SAR-3 lean confirmed final** — Argus identifies, Talos correlates. No Argus-side schema change; correlation logic owned by Talos team.
- ~~**Whether to query MuckRock's API or just their search.**~~ Resolved at Phase-4 Wave-D path-(a) early-cut ([MAC-31](/MAC/issues/MAC-31)): search was used; corpus-ceiling held at 0; question moot.
- ~~**How aggressive on inference?** Bible says inferences are capped at 70 confidence.~~ Resolved: **70-cap binding for inferred rows confirmed final.** No current row pressure on the cap (all Phase-5 inferred rows landed at 50–55 per SAR-1 LAA-bit penalty + strict §8.4 conf=50 starting band).

**Resolved during 2026-05-04 correction pass**

- ~~**Confidence threshold for the default scanner export.**~~ Resolved at Checkpoint 0 (default = 70). Reconfirmed by Correction 2 (§4.5) and Correction 8 (§7.5): `argus_export_high_confidence.json` uses `confidence ≥ 70`; `argus_export.json` uses `confidence ≥ 30`.
- ~~**Output file naming convention.**~~ Resolved by Correction 8 / §7.5 / §9 item 2: `argus_export.json` and `argus_export_high_confidence.json` are the canonical Talos-bound names; `argus.db` and `argus_export.csv` round out the export set.

Add new questions to this section as they arise. Do not invent answers.

---

*End of bible. Re-read Section 0 if you've forgotten how to use this document.*
