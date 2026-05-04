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
5. **Police drones** — DJI Matrice (LE configurations), Skydio X-series, BRINC LEMUR, Parrot ANAFI USA
6. **Acoustic gunshot detection** — SoundThinking (formerly ShotSpotter) sensors
7. **Hacking / forensics gear** — Hak5 (WiFi Pineapple, Bash Bunny, Packet Squirrel), Cellebrite UFED, Magnet GrayKey, Berla iVe
8. **Covert / surveillance cameras** — pole cameras, body-worn covert, common LE-deployed IP cam models
9. **GPS trackers and tags** — common LE-deployed tracker models (covert vehicle trackers); also AirTag/Tile/SmartTag for the recurrence-detection feature
10. **Facial recognition / video analytics** — BriefCam, Rekor, Clearview-deployed endpoints (where detectable)
11. **Drone detection systems** — Dedrone, DroneShield (these are themselves wireless emitters)

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
| `device_category` | TEXT NOT NULL | enum from §2.1 (alpr, imsi_catcher, body_cam, police_radio, drone, gunshot_detect, hacking_tool, covert_cam, gps_tracker, face_recog, drone_detect) |
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
- **`raw_observations`** — staging table; raw extracted records before normalization (preserve forever for audit)
- **`extraction_runs`** — log of every extraction job: agent id, source, started_at, finished_at, records_in, records_out, errors
- **`conflicts`** — when two sources disagree on the same identifier; reviewed and resolved by CEO

### 4.3 Normalization rules

- MAC addresses: lowercase, colon-separated (`aa:bb:cc:dd:ee:ff`)
- OUIs: lowercase, colon-separated 3 octets (`aa:bb:cc`)
- BLE UUIDs: lowercase, hyphenated 8-4-4-4-12 format
- SSIDs: stored exactly as broadcast; pattern fields use POSIX regex
- Manufacturer names: matched against a canonical list maintained in `manufacturers` table; new vendors added explicitly

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

Dispatch **Source Workers** for:

- WiGLE API: query around every DeFlock-mapped Flock camera (500m radius), every Atlas of Surveillance entry. Mine BSSIDs that appear consistently across deployments.







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
   - `argus_export.json` (full export, scanner-consumable)
   - `argus_export_high_confidence.json` (confidence ≥ 70 only — recommended default for scanner)
   - `argus_export.csv` (human-readable)
   - `coverage_report.md` (the matrix and gap analysis)



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
- Reject obviously fake/example data (`aa:bb:cc:dd:ee:ff`, `00:11:22:33:44:55`, RFC 7042 documentation ranges).
**Don'ts:**
- Do not hallucinate identifiers. If the document doesn't contain one, return empty.
- Do not assume a manufacturer's gear is law-enforcement-only without evidence.

### 7.4 Validator

**Goal:** Sanity-check records before promotion to main table.
**Checks:**
- Identifier format valid for its type
- Identifier not in known-fake list (RFC 7042, common doc examples, IEEE reserved)
- Manufacturer matches `manufacturers` canonical list (or flag for addition)
- `source_url` resolves and contains the claimed `source_excerpt` (spot-check 10% via re-fetch)
- Confidence score consistent with source_type (§8.2)
- No duplicate against existing main-table records (if dup, route to dedup logic)
**Outputs:** Approved records → main table. Rejected records → `conflicts` table with reason. Borderline → human review queue.

### 7.5 Export Worker

**Goal:** Produce final exports per §6 Phase 5.
**Outputs:** Files in `exports/` directory, each with a header comment (in JSON: `_meta` field; in CSV: top-line `# meta`) including: export timestamp, record count, schema version, confidence threshold applied.
**Don'ts:**
- Do not include the `raw_observations` table in exports
- Do not include `superseded_by` pointers in exports (resolve them first)
- Do not export records with `confidence < 30` to the high-confidence file

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
- **Procurement ≠ deployment.** An agency buying a Stingray doesn't put one on every patrol car. Procurement records add geographic context but never raise an identifier above 85 confidence by themselves.
- **MAC randomization warning.** Modern phones and some modern surveillance gear randomize MACs. Note this in the export readme so the scanner doesn't generate false alerts on randomized devices.
- **Test data filter.** Reject identifiers matching known documentation/example ranges (RFC 7042, locally administered ranges with obvious patterns, vendor demo addresses).

---

## 9. Deliverables / Definition of Done

This run is "done" when all of the following are true:

1. `db/argus.db` exists, schema matches §4, all phases complete
2. `exports/` contains the four files specified in §6 Phase 5
3. `coverage_report.md` exists and shows category coverage with honest gap analysis
4. Every record in the main table has a working source_url
5. The validator has run a final pass and `conflicts` table is empty (or every entry is human-resolved)
6. The `argus_cli.py` utility works for `status`, `query`, `export`, `validate`
7. README.md at the project root describes: what the database is, how to consume the export, the schema, the confidence scoring, the limitations, and the legal/ethical scope (§2.2 + §11)


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

---

## 12. Open Questions



- **WiGLE API credentials.** Human needs to provide an API key. Argus is useless without it for Phase 3.
- **Whether to query MuckRock's API or just their search.** API has rate limits; search has different ones.
- **Confidence threshold for the default scanner export.** Bible currently says 70. Confirm before Phase 5.
- **How aggressive on inference?** Bible says inferences are capped at 70 confidence. Confirm acceptable, or lower.
- **Output file naming convention** if the scanner project has expectations. (Worth asking before Phase 5.)
- **Project name.** "Argus" is a working name. Confirm or replace before README is written.

Add new questions to this section as they arise. Do not invent answers.

---

*End of bible. Re-read Section 0 if you've forgotten how to use this document.*
