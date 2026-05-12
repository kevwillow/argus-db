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
| `identifier_type` | TEXT NOT NULL | enum: `oui`, `mac`, `mac_range`, `bssid`, `ssid_exact`, `ssid_pattern`, `ble_uuid`, `ble_service`, `device_fingerprint`, `ble_local_name`, `ble_characteristic`, `product_family_codename` (last three added Correction Pass 13 — Wave G structural fidelity) |
| `device_category` | TEXT NOT NULL | enum from §2.1 (alpr, imsi_catcher, body_cam, police_radio, in_vehicle_router, drone, gunshot_detect, hacking_tool, covert_cam, gps_tracker, face_recog, drone_detect) |
| `manufacturer` | TEXT | normalized vendor name |
| `model` | TEXT | when known |
| `confidence` | INTEGER | 0–100, see §8.2 |
| `source_url` | TEXT NOT NULL | direct URL to the evidence |
| `source_type` | TEXT NOT NULL | enum: `official`, `regulatory`, `procurement`, `academic`, `foia`, `crowdsourced`, `inferred`, `manufacturer_doc`, `manufacturer_app` (last added Correction Pass 13 — CP12 §8.2 schema sibling) |
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
- **`procurement_records`** — staging table for Tier 2/3 procurement-only rows (SAM.gov, city council minutes, FOIA-released procurement docs) that name an agency × vendor purchase but carry **no** MAC/OUI/SSID/UUID identifier. Schema includes a nullable `linked_identifier_id` FK back to `identifiers` for the upgrade path when a later source attaches a concrete identifier to the same purchase. Per §4.5 procurement-only carveout / §11 #14, these rows are NEVER exported to Lynceus — they are analytical only. Created in MAC-2 / Phase 1 (signed off at Checkpoint 1); documented in §4.2 in Correction Pass 5 (BIBLE_AMENDMENTS).
- **`fcc_grantees`** — staging table for FCC EAS grantee registrations (Phase 3 / MAC-7; first source = opendata.fcc.gov dataset `3b3k-34jp`, USGOV_WORKS public domain). Holds grantee_code → entity-name + mailing/contact metadata + date_received. Identifier columns intentionally absent — `grantee_code` is a regulatory entity prefix, not a per-device identifier (per-device FCC IDs are formed `grantee_code + product_code`, owned by Phase 4 `fcc_equipment_filings` if/when created). Idempotency keyed by `(source_id, source_row_key=grantee_code)`. Stale-mirror sources: `sources.notes` MUST carry `dataset_freeze_date` + `staleness_warning` when the upstream mirror is documented stale (3b3k-34jp is frozen at 2021-03-22; Flock Safety + post-2020 grantees absent — Phase 4 owns the gap). Added in Correction Pass 6 (BIBLE_AMENDMENTS).
- **`extraction_runs`** — log of every extraction job: agent id, source, started_at, finished_at, records_in, records_out, errors
- **`conflicts`** — when two sources disagree on the same identifier; reviewed and resolved by CEO

### 4.3 Normalization rules

- MAC addresses: lowercase, colon-separated (`aa:bb:cc:dd:ee:ff`)
- OUIs: lowercase, colon-separated 3 octets (`aa:bb:cc`)
- BLE UUIDs: lowercase, hyphenated 8-4-4-4-12 format
- SSIDs: stored exactly as broadcast; pattern fields use POSIX regex
- Manufacturer names: matched against a canonical list maintained in `manufacturers` table; new vendors added explicitly

### 4.4 Lynceus export mapping

The downstream consumer (Lynceus, the Raspberry Pi RF security monitor) has a fixed, minimal watchlist schema with `pattern_type ∈ {mac, oui, ssid, ble_uuid}`. Argus's richer `identifier_type` enum must be collapsed at export time. Lynceus cannot be modified to accept Argus's richer enum; Argus does the collapsing. The export worker (§7.5) applies exactly this mapping:

| Argus `identifier_type` | Lynceus `pattern_type` | Notes |
|---|---|---|
| `oui` | `oui` | direct pass |
| `mac` | `mac` | direct pass |
| `bssid` | `mac` | a BSSID *is* a MAC for Lynceus's purposes |
| `ssid_exact` | `ssid` | direct pass |
| `ssid_pattern` | (DROPPED) | Lynceus has no regex support in v0.2; record in coverage report |
| `ble_uuid` | `ble_uuid` | direct pass |
| `ble_service` | `ble_uuid` | collapsed; BLE service UUIDs *are* UUIDs for Lynceus |
| `mac_range` | (expand or DROP) | expand into individual MACs at export ONLY if range ≤256 entries; otherwise drop and note in coverage report |
| `device_fingerprint` | (DROPPED) | Lynceus has no fingerprint matching; analytical-only |
| `ble_local_name` | (DROPPED) | added Correction Pass 13; Lynceus has no GAP local-name match in v0.3; analytical-only |
| `ble_characteristic` | (DROPPED) | added Correction Pass 13; Lynceus discovers by service UUID (`ble_service` / `ble_uuid`), not characteristic; analytical-only |
| `product_family_codename` | (DROPPED) | added Correction Pass 13; vendor-internal taxonomy / cohort strings (e.g. Flock `DeviceType` enum values); analytical-only |
| `ble_manufacturer_id` | `ble_manufacturer_id` | added Correction Pass 16; **new pattern_type** — Lynceus scanner parses 2-byte SIG company ID from BLE advertising manufacturer-specific data field. Canonical match surface for the post-CP15 BLE manufacturer-ID cluster (Apple `0x004C`, XUNTONG `0x09C8`, etc.) |
| `drone_id_prefix` | `drone_id_prefix` | added Correction Pass 16; **new pattern_type** — Lynceus scanner parses ASTM F3411-22a Remote ID frames across WiFi NAN action / WiFi Beacon vendor IE / BLE Legacy 4.x advertising. **Current-hardware capability boundary:** BLE5 LE Coded PHY decode is a baseline-Pi-BLE-chipset limitation; coverage on baseline hardware is dominated by the WiFi-NAN/Beacon Remote ID variants. Documented as current-hardware-not-permanent; future-chipset-capable operators gain coverage automatically without §4.4 amendment. |
| `icao_24bit_address` | (DROPPED) | added Correction Pass 16; **out-of-band RF.** ADS-B operates at 1090 MHz; Lynceus baseline Pi BLE/WiFi scanner cannot observe without an additional receiver. **Current-hardware DROPPED** — RTL-SDR upgrade path unlocks observability for future operators. |
| `rf_channel` | (DROPPED) | added Correction Pass 16; **parametric metadata.** RF channel is a derived property of an observation, structurally not a wire-observable identifier string. Lynceus `pattern_type` shape requires discrete match values. |
| `burst_cadence_ms` | (DROPPED) | added Correction Pass 16; parametric metadata (temporal property of an emitter, not a match value). |
| `bandwidth_mhz` | (DROPPED) | added Correction Pass 16; parametric metadata (spectral-occupancy property of a signal, not a match value). |
| `device_class_id` | (DROPPED) | added Correction Pass 16; semantic enum (proprietary-protocol device-class label, categorization-time attribute, not a wire-observable identifier string). |
| `rf_burst_duration` | (DROPPED) | added Correction Pass 16; parametric metadata (temporal property of a burst, not a match value). |
| `rf_protocol_constant` | (DROPPED) | added Correction Pass 16; **sub-protocol-level / requires SDR.** PHY-layer constants (sync words, frame markers) are not surfaced by the Linux WiFi/BT subsystem to userspace at the baseline Pi capability envelope. SDR-based scanning (RTL-SDR, HackRF) unlocks PHY-layer match for future hardware-upgraded operators. |
| `wifi_aware_service_name` | `wifi_aware_service_name` | added Correction Pass 16; **new pattern_type** — Lynceus scanner parses WiFi NAN service-discovery frames, matches UTF-8 service-name strings. Capability-gated by Lynceus-side NAN support; Argus exports unconditionally per the consumer-carries-capability-state posture (hardware-cannot-observe is the DROPPED criterion at §4.4, operator-might-not-have-enabled is not). |
| `wifi_ie_element_id` | (DROPPED) | added Correction Pass 16; **overly-coarse / sub-protocol-level.** The 1-byte IE tag (0–255) alone is structurally too coarse to function as a Lynceus pattern match value. A future richer `pattern_type` (e.g., `wifi_ie_payload_fingerprint`) covering element_id + content fingerprint would be a different type. |
| `bluetooth_le_pdu_type` | (DROPPED) | added Correction Pass 16; overly-coarse 4-bit link-layer enum (ADV_IND / ADV_NONCONN_IND / SCAN_REQ etc.); structurally not a useful match value on its own. |
| `wifi_frame_control_subtype` | (DROPPED) | added Correction Pass 16; overly-coarse 802.11 frame-control subtype enum; same shape rationale as `bluetooth_le_pdu_type`. |
| `wifi_nan_param_signature` | (DROPPED) | added Correction Pass 16; derived multi-field aggregate over NAN service-info fields, not a discrete match value. Lynceus's pattern engine matches single identifier strings, not multi-field signature aggregates. Future Lynceus signature-matching capability would be a new `pattern_type`. |
| `alpr_model` | (DROPPED) | added Correction Pass 16; **vendor-internal taxonomy, not RF-broadcast.** Values are product-name strings ("Flock Safety Falcon", "Motorola Vigilant", "Genetec AutoVu", etc.) sourced from deflock-app reports / vendor docs / visual identification. Companion type to the already-DROPPED `product_family_codename` (CP13 §4.4); both classes are analytical-only. Concrete ALPR-camera identifier rows flow via `oui` / `mac` / `bssid` / `ssid_exact` types where present; `alpr_model` is the analytical taxonomy column. |

**CP16 new `pattern_type` values (Lynceus integration team call-out).** This amendment introduces three new `pattern_type` values: `ble_manufacturer_id`, `drone_id_prefix`, and `wifi_aware_service_name`. **Architectural separation — Argus and Lynceus are parallel tracks, not a serial dependency.** CP16 ratification on the Argus side unblocks promotion-cycle-2 (415 FAA RID `drone_id_prefix` rows + 2 SIG `ble_manufacturer_id` rows) and the post-promotion export-regen immediately. Those rows ride the export at apply time regardless of Lynceus-side scanner-code state. If a running Lynceus instance does not yet support a new `pattern_type` at scan time, the entries are silently unmatched at runtime per Lynceus's own scanner contract — consumer-side unknown-pattern handling. The export pipeline does not error; the entries are not dropped on the Argus side; canonical Argus DB carries the full promotion. Lynceus integration team can sequence the three pattern_types independently for runtime match coverage.

Records that drop out of the Lynceus export remain in the canonical Argus database for analytical purposes. The coverage report MUST tally Argus-only records by category so the human knows what's not flowing downstream.

**Geographic-scope filter (CP7).** The Lynceus export applies an export-time `geographic_scope_filter` against `identifiers.geographic_scope` (§4.1). Default = `["US"]` for both standard and high-confidence exports (US-deployed Lynceus instances). Records with `geographic_scope` matching ANY filter element pass; records with `global` pass unconditionally; records with `unknown` pass into the standard export but NOT the high-confidence export. Records filtered out are tallied in `_meta.dropped_in_export` under `geographic_scope_mismatch`. Operators in non-US jurisdictions configure via export CLI flag; Argus does NOT bake the filter into the canonical DB. (See §7.5 for the export-shape contract and §12 #1 disposition.)

See §7.5 for the export-file shape and per-record description format, and §8.4 for additional drop rules (unknown category, Pi self-exclude, procurement-only). Severity is no longer Argus-emitted — see §4.5 superseded banner + CP8.

### 4.5 Severity for Lynceus export *(superseded — see CP8)*

> **⚠️ Superseded as of CP8 (2026-05-07): severity is owned operator-side via Lynceus's `severity_overrides.yaml` file. Argus does NOT emit `severity` in the export shape. Section retained below verbatim for audit-trail / historical-reasoning continuity. Future export modules MUST NOT consult §4.5 for severity values.**

Lynceus requires a `severity ∈ {low, med, high}` per record. Argus has `confidence` (0–100) but not severity. **Severity is NOT confidence.** Severity expresses "how alarming is it that this device is near me," which is a function of `device_category`, not how sure we are about the identifier.

The export worker (§7.5) derives Lynceus severity from Argus `device_category` using exactly this mapping:

| `device_category` | Lynceus `severity` | Reasoning |
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

**Procurement-only carveout.** Procurement-only records (`source_type='procurement'` with no MAC/OUI/UUID, only an agency-bought-vendor mapping) are NEVER exported to Lynceus. They are analytical only. The Lynceus export contains only records with concrete identifiers. (See also §8.4 and §11 #14.)

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
   - `argus_export.json` (Lynceus-consumable, all confidences ≥30; applies §4.4 type mapping and §4.5 severity)
   - `argus_export_high_confidence.json` (Lynceus-consumable, confidence ≥70; recommended default for the scanner)
   - `argus_export.csv` (rich-import feed per CP11; 15 columns; all active records, unfiltered)
   - `coverage_report.md` (the matrix, gap analysis, and the §9 item 9 "Dropped from Lynceus export" tallies)



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

**Goal:** Produce final exports per §6 Phase 5. The Lynceus-bound files (`argus_export.json`, `argus_export_high_confidence.json`) must apply the §4.4 type mapping and §4.5 severity derivation before writing entries.
**Outputs:** Files in `exports/` directory, each with a header comment (in JSON: `_meta` field; in CSV: top-line `# meta`) including: export timestamp, record count, schema version, confidence threshold applied.

**Per-record description format (Lynceus exports only) — CP8 (2026-05-07) directive.** For `argus_export.json` and `argus_export_high_confidence.json`, descriptions must be self-contained and readable as a phone notification. Constraints:

- Maximum 80 characters
- No "see source" references
- No URLs
- No `source_excerpt` fragments — those stay in the canonical DB only
- **Format (flat per CP8):** `{vendor} {device_category}` — flat, no parentheticals, no rich product-family seed.
- **Fallback patterns:**
    - Vendor known, category unknown: `"{vendor} unknown"`.
    - Vendor unknown (e.g. inferred from OUI without canonical-name match): `"Unattributed identifier"`.
- Examples:
    - GOOD: `Flock Safety alpr`
    - GOOD: `Hak5 hacking_tool`
    - GOOD: `Axon body_cam`
    - GOOD: `Apple ble_service`
    - GOOD: `DJI drone`
    - BAD: `Hak5 - see source for details`
    - BAD: `Hak5 WiFi Pineapple (pentest gear)`  *(rich-seed superseded by CP8)*
    - BAD: `Device manufactured by Hak5 LLC, used for wireless penetration testing as documented in https://...`

If a record cannot be described in 80 chars without losing meaning (rare under flat template), the canonical record stays but the Lynceus export uses `"{category} device"` and notes the truncation in the coverage report.

**Lynceus export file shape (`argus_export.json` and `argus_export_high_confidence.json`) — CP7 + CP8 + SAR-10 (2026-05-07) directive.** Both files conform to:

```json
{
  "_meta": {
    "argus_version": "<schema version>",
    "exported_at": "<ISO8601 UTC timestamp>",
    "record_count": 0,
    "confidence_threshold": 0,
    "argus_run_id": "<UUID for this export run>",
    "geographic_scope_filter": ["US"],
    "source_record_count": 0,
    "dropped_in_export": {
      "unknown_category": 0,
      "ssid_pattern": 0,
      "device_fingerprint": 0,
      "oversized_mac_range": 0,
      "procurement_only": 0,
      "self_exclude_oui": 0,
      "below_confidence_threshold": 0,
      "geographic_scope_mismatch": 0
    }
  },
  "entries": [
    {
      "pattern": "<normalized identifier>",
      "pattern_type": "<mac|oui|ssid|ble_uuid>",
      "description": "<≤80 char flat {vendor} {device_category} per CP8>",
      "argus_record_id": "<16 hex chars: sha256(type|identifier)[:16] per SAR-10>"
    }
  ]
}
```

**Field notes:**
- `confidence_threshold` is `0` for `argus_export.json` (full export, all confidences ≥30 per §6 Phase 5 / §9) and `70` for `argus_export_high_confidence.json`.
- `geographic_scope_filter` is the export-time CLI parameter (CP7); default `["US"]`. `"global"` records pass unconditionally; `"unknown"` records pass into standard but not high-confidence (§4.4).
- `argus_record_id` is computed per **SAR-10** as `sha256(f"{identifier_type}|{normalized_identifier}").hexdigest()[:16]`. Stable under §8.3 dedup events: re-runs / confidence drift / source edits / vendor reattribution all yield identical hash. The Lynceus seeder uses it as the upsert key (update-existing vs. insert-new) when re-importing later Argus versions.
- **`severity` field intentionally absent** (CP8). Severity is owned operator-side via Lynceus's `severity_overrides.yaml` file. §4.5 retained as superseded historical reasoning only.
- The `dropped_in_export` tallies must reconcile with the coverage report (§9 item 9) such that `source_record_count − sum(dropped_in_export) = entries.length`.

**Lynceus integration shape: dual-artifact contract — CP11 (2026-05-07) directive.**

The v0.1 export ships two consumer-grade artifacts targeting distinct Lynceus consumer-side use cases:

1. **`argus_export.json`** — operational alert feed. Minimal entry shape `{pattern, pattern_type, description, argus_record_id}` per row (per the §-text above). Designed for low-bandwidth / streaming / alert-oriented ingest. CP7 `geographic_scope_filter` applied (default `("US",)` plus `global` unconditional pass). CP8 ≤80-char flat description applied. Severity owned operator-side per CP8 sub-B. Companion file `argus_export_high_confidence.json` follows the same shape with `confidence_threshold=70`.

2. **`argus_export.csv`** — rich-import feed. Full canonical row shape with 15 columns: `argus_record_id, id, identifier, identifier_type, device_category, manufacturer, model, confidence, source_type, source_url, source_excerpt, geographic_scope, description, first_seen, last_verified, notes`. **Unfiltered** — all active rows regardless of CP7 filter. Operators apply geographic / category / confidence filters at Lynceus-side import time.

The split exists because: (a) JSON is sized for runtime alert-feed consumption where small payloads matter; (b) CSV carries full provenance for the import-once / store-in-watchlist_metadata workflow per Lynceus v0.3 schema migration 004. Together the two artifacts satisfy `Lynceus_integration_spec_for_Argus.txt` Section 2's "no lossy conversion" principle without bloating the alert-feed JSON. Symbol-table fields not present in either artifact (`fcc_id` requires JOIN against `fcc_grantees`): deferred to v1.1+ as identified-need surfaces.

**CSV population logic (CP11 sub-A).**
- `argus_record_id` — call `db.export.argus_record_id.argus_record_id(row.identifier_type, row.identifier)` per SAR-10. 16-char hex.
- `description` — call shared `_format_description(row)` (CP8 ≤80-char flat) — same function powers JSON and CSV; single source of truth.
- `first_seen` / `last_verified` — direct from `identifiers` table columns.

**Don'ts:**
- Do not include the `raw_observations` table in exports
- Do not include `superseded_by` pointers in exports (resolve them first)
- Do not export records with `confidence < 30` to any Lynceus export file. The floor for `argus_export.json` is `confidence ≥ 30`; the threshold for `argus_export_high_confidence.json` is `confidence ≥ 70`. Records below 30 are tallied as `below_confidence_threshold` in the coverage report.
- Do not export records with `device_category='unknown'` to Lynceus under any confidence threshold (see §8.4 and §11 #13)
- Do not export procurement-only records (no concrete identifier) to Lynceus (see §4.5 and §11 #14)
- Do not include OUIs from the Pi self-exclude list (§8.4) in `argus_export_high_confidence.json`

---

## 8. Quality Controls

### 8.1 Provenance is non-negotiable

Every record in the main table has a working `source_url`. Records without provenance are rejected. Period. This is not bureaucracy; it's the difference between a useful database and a liability.

### 8.2 Confidence scoring

| Source type | Default confidence range |
|---|---|
| `official` (court-verifiable government filings — FCC EAS, FAA enforcement orders, court-ordered disclosures) | 90–100 |
| `primary_registry` (authoritative numerical-allocation registries — see §8.2 sub-rule below) | 70–85 single-source; up to 95 with cross-band corroboration |
| `regulatory` (gov't filing, court order text — non-`official`-tier regulatory provenance) | 80–95 |
| `manufacturer_doc` (vendor spec sheet) | 75–90 |
| `procurement` (SAM.gov, state portals) | 70–85 (proves *purchase*, not *deployment*) |
| `academic` (peer-reviewed or conference) | 70–90 |
| `foia` (released documents) | 65–85 |
| `crowdsourced` (WiGLE, DeFlock) | 50–75 |
| `manufacturer_app` (vendor companion APK/IPA static-analysis extract) | 60–95 (sub-banded by identifier class — see below) |
| `inferred` (derived) | 30–70, capped |
| News, forums, unverified | 20–50 |

Adjust within range based on specificity, recency, and corroboration. Two independent sources at 70 each can corroborate to a single record at 85.

**`primary_registry` sub-banding** (added Correction Pass 15 for the FAA RID + Bluetooth SIG + IEEE OUI registry cluster).

`primary_registry` covers authoritative numerical-allocation registries maintained by standards bodies, standards-development organizations (SDOs), or regulatory authorities where the registry IS the source-of-truth for what the identifier means. Canonical examples:

- **IEEE OUI registry** (MA-L 24-bit, MA-M 28-bit, MA-S 36-bit). IEEE assigns OUI blocks; the registry record IS the canonical attribution of OUI → manufacturer. (Migrates FROM `official` band into `primary_registry`.)
- **Bluetooth SIG company-identifier registry.** SIG assigns 16-bit BLE company IDs; the registry IS the canonical attribution of `0x004C` → Apple, etc.
- **FAA ANSI/CTA-2063-A RID registry.** FAA assigns drone serial-number prefixes; the registry IS the canonical attribution of `1581Fxxx` → DJI, `1748xxxx` → Autel, etc.
- **IANA assignments.** When Argus eventually ingests IANA-managed namespaces (port numbers, protocol numbers, etc.), they land here.

**Distinguishing test (apply at ingest time):** ask "is this source the source-of-truth for what the identifier *means*, or is it a third-party assertion about meaning?"

- Registry-as-issuer → `primary_registry`.
- Third-party citing the registry → `crowdsourced` (50–75 band) or `manufacturer_doc` (75–90 band) per existing rules.
- Court-verifiable government filing about a deployed instance → `regulatory` (80–95 band) or `official` (90–100 band).

**Confidence ceiling rationale:**

- **70–85 single-source** for `primary_registry`. The floor of 70 sits above `crowdsourced`'s ceiling of 75 (registry issuance carries more authority than community curation). The ceiling of 85 sits below `regulatory`'s 95 (registries are issuer-of-record but not court-verifiable in the regulatory-filing sense) and below `manufacturer_doc`'s 90 (the registry can name a manufacturer, but the manufacturer's own spec sheet may carry additional model-level detail the registry doesn't capture).
- **Up to 95 with cross-band corroboration.** When a `primary_registry` row is additionally corroborated by `regulatory` or `manufacturer_doc` sources, §8.3 corroboration formula (`min(99, max(originals) + 5)`) applies. Example: IEEE OUI registry (primary_registry, 85) + FCC EAS test report citing the same OUI (regulatory, 90) corroborates to a single record at confidence min(99, max(85,90)+5) = 95.

**Waiver of ≥3-independent-sources cut-off for `primary_registry`.** The Phase-4 promotion-cycle cut-off requiring `independent_source_count ≥ 3` does NOT apply to `primary_registry` rows. The waiver is `primary_registry`-only — other source-band cut-off rules remain in force. Justification: asking for "three independent sources" of what `1581Fxxx` means at FAA is structurally ill-defined — FAA's registry IS the source of truth, and there is no parallel source-of-truth to corroborate against. A single primary_registry citation IS sufficient evidence under §11 #1 (no fabrication) because the registry's own publication is verifiable.

**Reclassification discipline (§11 #8 boundary).** Reclassification of an existing `identifiers` row from `crowdsourced` / `inferred` to `primary_registry` is permissible ONLY when the row's existing `source_url` already points DIRECTLY at the registry issuer's own publication (FAA's database URL, SIG's company-identifier registry URL, IEEE's MA-L assignment record URL, etc.). If the `source_url` points at a third-party citation — community repo, blog post, aggregator, even an academic paper that cites the registry — the row stays in its current band. To establish `primary_registry` classification, a new `raw_observations` row citing the registry directly is required, per §11 #1 provenance discipline. Reclassification is a band-correction within preserved provenance, NOT a provenance shortcut. The §11 #8 "no confidence drift" rule composes: band-correction with the new ceiling re-applies to a row whose direct provenance qualifies; rows whose direct provenance is third-party stay capped at their current band's ceiling regardless of upstream-registry ancestry.

**Multi-registry edge case.** Rare case: an identifier appears in two primary registries (e.g., an IEEE-issued OUI also referenced in an FAA filing as part of a drone-prefix assignment). Validator-side disposition: take the most-direct registry citation (the registry that ISSUES the identifier value) as `primary_registry`; secondary citations classify per their own source nature.

**Edge sub-case NOT covered by CP15:** registry-internal reassignment (e.g., IEEE reassigns a defunct company's OUI to a successor). Route such cases to the `conflicts` table with `reason='registry_reassignment'` for human-CEO disposition. A future CP may codify reassignment-discipline if frequency warrants. CP15 explicitly does NOT legislate this case.

**Composition with §8.4 lenses (CP14 cross-references):**

- **G-1 protocol-container OUI lens.** SDO-assigned OUIs (`FA:0B:BC` ASD-STAN, `50:6F:9A` Wi-Fi Alliance) classify as `primary_registry` when sourced from the SDO's own registry, and as `crowdsourced` when sourced from a community repo citing the SDO. CP15 + G-1 compose: protocol-container lens governs `device_category` semantics; `primary_registry` band governs confidence.
- **G-3 `ble_manufacturer_id`.** SIG-assigned values like `0x004C` Apple + `0x09C8` XUNTONG are `primary_registry` when sourced from the SIG company-identifier registry. Wave-A community-repo citations remain `crowdsourced` 50–75; SIG-registry direct citation lifts to `primary_registry` 70–85.
- **G-7 `paired_identifier_id` + `pair_kind`.** Independent. Pairing discipline operates on identifier structure (LA-bit flip, vendor-as-container, firmware-generation); source-band classification is orthogonal.
- **G-9 `drone_id_prefix`.** FAA RID is the canonical `primary_registry` case driving CP15. The 481-row FAA RID batch HELD from Phase-4 promotion-cycle-1 promotes at confidence 85 per `primary_registry` single-source rule once CP15 ratifies.

**`manufacturer_app` sub-banding** (added Correction Pass 12 for Wave G — Phase 6 vendor companion app static analysis). The 60–95 outer band breaks down per identifier class, because vendor apps yield different attestation strength per class:

| Identifier class extracted from vendor app | Sub-band | Rationale |
|---|---|---|
| Hardcoded BLE service UUID (128-bit or 16-bit-in-context) | 80–95 | BLE specs require service UUID for discovery; vendor app must contain the canonical value. Highest tier. |
| Default SSID pattern (vendor-prefix WiFi name) | 70–85 | Clear vendor attestation in code; hardware match TBV at scan time. |
| Default credential string (plaintext) | 60–80 | Vendor-attested at app version, but firmware may have rotated. Encoded/hashed values dropped (require runtime analysis). |
| MAC OUI from validation code path | 75–90 | Confirms OUI assignment; cross-checks against IEEE Tier-1 registry. Disagreement → manual flag. |
| Product-family taxonomy (model names, internal hardware IDs) | 90–95 | Vendor's own product naming inside their own app is near-canonical; primarily feeds aliases / inference candidates. |

Default per-row confidence at extraction time = midpoint of the relevant sub-band. SAR-7 / SAR-8 / SAR-9 corroboration adjusts up; framework-string proximity, single-app-only surfacing, or cross-vendor-default appearance adjusts down. SAR-11 (proposed; gated on Step-2 calibration of first 2 vendor apps) handles framework-UUID and third-party-BLE-library FP classes if calibration shows >5% FP rate from those sources. §8.4 strict-promotion rule (≥80) applies as written.

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

- **Multi-purpose vendors are not categorized at the OUI level.** Motorola Solutions makes police radios *and* hospital pagers *and* warehouse scanners. An OUI alone never gets a `device_category` other than `unknown`. **Category requires model-level evidence** — see the model-level evidence sub-rule below for what counts.
  - **Unknown-category Lynceus carveout.** Records with `device_category='unknown'` (the multi-purpose vendor case) are NEVER exported to Lynceus under any confidence level. Lynceus cannot do anything useful with "unknown category" records — they would either be dropped (silently losing data) or fire as low-severity noise (training the user to ignore alerts). They remain in the canonical Argus database for analytical purposes only. The coverage report must tally these as "analytical-only records" separately from "exported records." (See also §11 #13.)
- **Model-level evidence — what counts (hardware-anchor sub-rule).** Acceptable forms of "model-level evidence" for lifting `device_category` beyond OUI-level `unknown`:
  - **Direct firmware-binary inspection.** Chipset / SoC / PMIC constants extracted from a vendor-signed firmware binary running on the device (Qualcomm MBN, Mediatek SCATTER, NXP MFBL, etc.). The binary IS the artifact running on hardware; the chipset string is a first-hand observation. Provenance classification (per §8.2): the *attribution chain* (binary → product) is community-sourced when the binary is community-redistributed (e.g., GainSec repo) and `crowdsourced`-banded (50–75); regulatory-sourced when the binary is recovered via FCC test report and `regulatory`-banded (80–95); manufacturer-sourced when obtained directly from vendor documentation and `manufacturer_doc`-banded (75–90). Phase-4 promotion confidence MUST honor the §8.2 source-band ceiling — the binary-inspection observation does NOT itself lift confidence above its source-band cap.
  - **Paper / report inference.** Chipset inference from indirect evidence (NVS partition string analysis, schematic/diagram OCR, teardown reportage, white-paper analysis). One step removed from the device. Classified per §8.2 same as above (community paper = `crowdsourced` 50–75; peer-reviewed = `academic` 70–90; regulatory disclosure = `regulatory` 80–95).
  - **Community attribution / forum claim.** Unverified attribution from a community source classifies as `crowdsourced` or `News, forums, unverified` (20–50) per §8.2. Set `rationale_pending_verification` flag for the 20–50 case.

  **No parallel tier system.** The hardware-anchor sub-rule composes with §8.2 source-bands; it does not introduce a parallel ceiling structure. Confidence at promotion = §8.2 band cap, lifted by §8.2 corroboration formula (`min(99, max(originals) + 5)`) when independent sources corroborate.

  **Generation pairing.** When hardware-anchor evidence identifies multiple chipsets associated with successive product generations of the same vendor (e.g., Falcon-gen1 Snapdragon 625 + Falcon-gen2 Snapdragon 650), the rows MUST be paired via `paired_identifier_id` with `pair_kind='firmware_generation'` (per migration 0012). The paired-identifier discipline lets validator queries return both generations when the vendor + product-family is the query target.

  **Identifier-type for hardware-anchor rows.** Chipset / PMIC anchors are NOT `oui` / `mac` rows. They are `device_fingerprint` type rows with the chipset designation as the `identifier` value (e.g., `'MSM8953'` / `'PM8953'`) and `manufacturer='Qualcomm'`, `model=<vendor>-<gen>` (e.g., `'Flock Falcon gen1'`). The vendor whose product anchors the chipset is the `model` field, NOT the `manufacturer` (which stays Qualcomm — the chipset maker is the canonical IEEE-registrant analogue here). (CP14 — G-13.3.)
- **Procurement ≠ deployment.** An agency buying a Stingray doesn't put one on every patrol car. Procurement records add geographic context but never raise an identifier above 85 confidence by themselves.
- **MAC randomization warning.** Modern phones and some modern surveillance gear randomize MACs. Note this in the export readme so the scanner doesn't generate false alerts on randomized devices.
- **Protocol-container OUI lens (third-lens discipline).** Some OUIs are IEEE-assigned to standards bodies or protocol working groups rather than to device-manufacturing vendors. When such an OUI is observed it identifies the **encapsulation format of a payload**, not the **identity of the emitting device**. The validator MUST distinguish three lenses at promotion time:
  - **Chip-vendor lens** — OUI identifies the silicon (e.g., Qualcomm, Broadcom). `device_category='unknown'` unless model-level evidence; multi-purpose-vendor discipline applies.
  - **Product-vendor lens** — OUI identifies the deployable product (e.g., DJI's `60:60:1F`). `device_category` set by attribution; subject to §8.3 corroboration.
  - **Protocol-container lens** — OUI is a standards-body / SDO assignment used as a prefix wrapping a payload format (e.g., ASD-STAN Beacon `FA:0B:BC`, Wi-Fi Alliance NAN `50:6F:9A`). `device_category` reflects the **payload protocol's typical emitter class** (e.g., `drone` for a Drone-RID protocol-container) and `manufacturer` is set to the SDO/working-group name (`'ASD-STAN'`, `'Wi-Fi Alliance'`), NOT to a device vendor. Multiple device vendors emit through the same protocol-container OUI; high-confidence individual-product attribution requires a second identifier (paired vendor OUI, device fingerprint, or model-level evidence per §8.2).

  **Dual-lens case (vendor-as-container).** Some vendor OUIs carry BOTH lenses simultaneously — the OUI is product-vendor-assigned AND is used by that vendor as the encapsulation prefix for a Drone-RID or BLE-NAN payload. Parrot's `90:3A:E6` is the canonical example (Parrot products use the OUI as a MAC prefix AND as a vendor-IE prefix wrapping Drone-RID payloads). The validator records two paired identifiers rows linked via `paired_identifier_id` with `pair_kind='vendor_as_container'`: one row carries the product-vendor lens (`device_category=<product class>`), the other carries the protocol-container lens (`device_category=<payload protocol class>`). The validator picks the lens by observation context at query time.

  **Within-lens corroboration discipline.** The protocol-container lens is a *category-level* rule (the lens exists); specific OUIs within the category each carry their own §8.3 corroboration counts. `FA:0B:BC` (n=5 Wave-A sources) is promotion-ready under the lens; `6A:5C:35` (FRDID, n=1 Wave-A source) is HELD at the §7.3 single-source confidence floor regardless of the lens's existence — promotion requires a second independent EU/FR transmitter-firmware source. (CP14 — G-1.)
- **Locally-administered (U/L=1) OUI pairing discipline.** When the validator promotes a staged OUI whose first octet has bit-1 set (`xxxxxx1x`, i.e., locally-administered per IEEE 802), it MUST first check whether the **U/L=0 sibling** (same OUI with bit-1 of the first octet cleared, mask `& 0xFD`) is already an IEEE-assigned record in `identifiers`. Three dispositions:
  - **Sibling present, same vendor context as the staged LA OUI** → promote the LA variant as a *paired identifier* linked to the IEEE-assigned parent via `paired_identifier_id` with `pair_kind='la_bit_flip'` (per migration 0012). Both rows persist. Confidence for the LA child inherits the §7.3 intake penalty (cap ≤ 40 unless the source attests broadcast use) but the corroboration bonus from the paired IEEE sibling may raise it up to the source-type ceiling per §8.2.
  - **Sibling absent in Argus** → hold the LA OUI at the §7.3 intake confidence (≤ 40) with `rationale_pending_verification`. Promote only when a second independent source corroborates the same LA OUI in the same vendor context (§8.2 corroboration rule). Do not synthesize an IEEE-sibling row from the LA OUI alone.
  - **Sibling present but assigned to a different vendor than the staged LA OUI's attributed context** → route the staged LA OUI to the `conflicts` table per §4.2 with `reason='la_bit_sibling_vendor_mismatch'`. Resolution requires manual review; do not auto-promote.

  The U/L-flip relationship is *necessary but not sufficient* for pairing: bit-1 of an LA OUI is a 1-bit fact, not an attestation that the device firmware deterministically emits the LA variant. A second observation in the same vendor context (or vendor documentation attesting the LA variant) is required before the paired-identifier disposition fires. Without that second observation, the disposition is "hold at low confidence" — single-observation LA OUIs do not promote on the strength of the bit-flip alone.

  **Precedence with protocol-container lens.** When classifying an LA OUI, check the protocol-container lens FIRST (look up SDO registry / known protocol-container catalog); if matched, route as `pair_kind=NULL` (protocol-container OUI; no LA-bit pairing) rather than `pair_kind='la_bit_flip'` — protocol-container LAs are typically self-assigned by the SDO and have no IEEE-assigned sibling. (CP14 — G-4.)
- **Test data filter.** Reject identifiers matching known documentation/example ranges (RFC 7042, locally administered ranges with obvious patterns, vendor demo addresses). The full reject list is enumerated in §7.3 and applied by the validator (§7.4).
- **Pi self-exclude list (running scanner's own hardware).** Lynceus runs on a Raspberry Pi, which has well-known OUIs:
  - `b8:27:eb` (older Pi boards)
  - `dc:a6:32` (Pi 4 era)
  - `e4:5f:01` (recent boards)
  - `28:cd:c1` (more recent)

  These OUIs MUST NOT appear in the Lynceus high-confidence export, regardless of source confidence. They appear in the standard export (`argus_export.json`) with `severity='low'` and a description noting "informational — common in DIY hardware." This exclusion list is hard-coded in the export worker (§7.5) and tallied in the coverage report under `self_exclude_oui`. (See also §11 #12.)
- **Defensive-tool operator-side hardware self-exclude.** Hardware used by Argus operators to RUN defensive-tool software (e.g., Rayhunter for IMSI-catcher detection) must NOT appear in the Lynceus high-confidence export, regardless of source confidence. The Argus operator stack is by definition not a surveillance target. Three-layer exclusion list:
  - **Modem hardware identifiers (USB VID:PID + diag interface):**
    - `usb_vid_pid: 05c6:f601` — Orbic RC400L (Verizon) primary modem mode and Kajeet rebrand (same hardware).
    - `usb_vid_pid: 05c6:f626` — Orbic RC400L alt mode A.
    - `usb_vid_pid: 05c6:f622` — Orbic RC400L alt mode B.
    - `usb_vid_pid: 05c6:90b6` — FY UZ801 (Qualcomm WCN36xx PRONTO).
    - `usb_vid_pid: 2c7c:0125` — PinePhone / PinePhone Pro (Quectel EG25-G).
    - `device_path: /dev/diag` — Qualcomm modem diagnostic char device (signals vendor-debug-mode modem; not specific to one OEM).
  - **Rayhunter-supported modem family — firmware-version / hardware-rev anchored** (no specific VID:PID surfaced yet; route via `device_fingerprint`):
    - Wingtech CT2MHS01 (firmware `CT2MHS01_0.04.55` at `/etc/wt_version`)
    - T-Mobile TMOHS1 (firmware `TMOHS1_00.05.20`; Wingtech OEM)
    - TP-Link M7350 (hardware revs v3/v5/v9)
    - TP-Link M7310 (hardware rev v1)
  - **List forward-proofs to mirror Rayhunter upstream curation** — when Rayhunter adds a new supported modem (with concrete VID:PID or firmware-version-anchored identifier), Argus mirrors it at the next ingest cycle without re-ratification.

  **Disposition mechanics (mirrors Pi self-exclude precedent):**
  - These identifiers MUST NOT appear in the Lynceus high-confidence export under any confidence level.
  - They appear in the standard export (`argus_export.json`) with `severity='low'` and a description noting "informational — Argus operator-side defensive-tool hardware (Rayhunter target list); not a surveillance target."
  - The exclusion list is hard-coded in the export worker (§7.5) and tallied in the coverage report under `self_exclude_defensive_tool` (separate bucket from `self_exclude_oui` for the Pi list).
  - When a new identifier matches the Rayhunter-supported list at promotion time, it routes to this self-exclude bucket automatically — no manual review required. (CP14 — G-15. See also §11 #12 below.)

---

## 9. Deliverables / Definition of Done

This run is "done" when all of the following are true:

1. `db/argus.db` exists, schema matches §4, all phases complete
2. `exports/` contains:
   - `argus.db` (canonical SQLite)
   - `argus_export.json` (Lynceus-consumable, all confidences ≥30)
   - `argus_export_high_confidence.json` (Lynceus-consumable, confidence ≥70)
   - `argus_export.csv` (rich-import feed per CP11; 15 columns; all active records, unfiltered)
   - `coverage_report.md`

   Each Lynceus-consumable JSON file conforms to the schema in §7.5 (including the §4.4 type mapping, §4.5 severity derivation, and the description-format constraints). Each is independently parseable and includes a complete `_meta` block.
3. `coverage_report.md` exists and shows category coverage with honest gap analysis
4. Every record in the main table has a working source_url
5. The validator has run a final pass and `conflicts` table is empty (or every entry is human-resolved)
6. The `argus_cli.py` utility works for `status`, `query`, `export`, `validate`
7. README.md at the project root describes: what the database is, how to consume the export, the schema, the confidence scoring, the limitations, and the legal/ethical scope (§2.2 + §11)

9. Coverage report includes a "Dropped from Lynceus export" section tallying records held back by category: `unknown_category`, `ssid_pattern`, `device_fingerprint`, `oversized_mac_range`, `procurement_only`, `self_exclude_oui`, `below_confidence_threshold`. Tallies must sum correctly: `source_record_count − sum(dropped) = exported entries count` for each Lynceus-bound JSON file (matching the `_meta.dropped_in_export` block defined in §7.5).

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
10. **Do not categorize at the OUI level for multi-purpose vendors** (see §8.4). *(Reframed by CP10 (2026-05-07): narrow-read carve-out — Argus-side categorization of single-product-line §2.1 vendors whose entire product line falls within the canonical surveillance category is permitted, regardless of whether the vendor also makes consumer/commercial variants of that category. FP-suppression for multi-purpose vendors is delegated to the Lynceus operator-override layer (`severity_overrides.yaml`), not Argus-side gatekeeping. Argus ships factual vendor-attribution; Lynceus operators tune alert behavior per their threat model. See CP10 in BIBLE_AMENDMENTS.md for the 17-row v0.1 cutover slate and the operator-override-as-FP-layer architecture.)*
11. **Do not skip the `BIBLE_AMENDMENTS.md` log entry when making in-place bible edits or adding sub-agent-level rules.** The git diff is the source of truth, but the amendment log is the human-readable trail. An undocumented amendment is a process violation regardless of whether the edit itself is correct.
12. **Operator-stack self-exclude.** Argus operator-side hardware MUST NOT appear in the Lynceus high-confidence export. This covers (a) **Lynceus host hardware** — Raspberry Pi OUIs as enumerated in §8.4 Pi self-exclude bullet; and (b) **Defensive-tool hardware** — Rayhunter-supported modems as enumerated in §8.4 defensive-tool self-exclude bullet, including the CEO's Orbic RC400L (USB VID:PID `05c6:f601`/`f626`/`f622`) and the broader supported-modem family (FY UZ801, PinePhone Quectel, Wingtech CT2MHS01, T-Mobile TMOHS1, TP-Link M7350/M7310). The exclusion is mandatory regardless of source confidence. Standard-export inclusion at `severity='low'` is permitted and documented per §8.4. (CP14 — G-15 expansion of original Pi-only rule.)
13. **Do not export records with `device_category='unknown'` to Lynceus** under any confidence level. They remain canonical-only (see §8.4).
14. **Do not export procurement-only records (no concrete identifier) to Lynceus.** Procurement records establish vendor-agency relationships, not device presence. They are analytical only (see §4.5).
15. **Do not commit decompiled vendor app source code, raw APK/IPA contents, or extracted decompile artifacts to the git index.** (Added Correction Pass 12, Wave G — Phase 6 license-posture confirmation per board direction 2026-05-08.) Raw APK/IPA binaries land at `raw/vendor_apps/<vendor>/<app_package_id>/<version>/<sha256>.{apk,ipa}` for provenance only and are gitignored. Decompiled `.java` / smali / dumped Mach-O headers live in workspace-only scratch directories during ExtractionWorker runs and are cleaned at end of run. Only extracted identifier *candidates* (value + relative file path within the decompile output) land in `raw_observations`. The git index never contains vendor-proprietary source. (See §11 #2 — this rule operationalizes the access/license posture for the vendor companion app corpus, mirroring the §1201 + §201.40(b) reverse-engineering exemption boundary: research is permitted, redistribution of decompiled source is not.)

---

## 12. Open Questions



**Open**

- **WiGLE API credentials.** Human needs to provide an API key. Argus is useless without it for Phase 3. Required before the Phase 3 Step-0 budget estimate fires (§6 Phase 3 / Checkpoint 3a). (Status at CP5: pitch-behavior binding holds verbatim through 2026-05-18; carries forward unchanged.)

**Wave-A (CP14) — board-ratified 2026-05-11, queued for resolution**

- **Static-MAC tracker sub-class architecture.** Phase 3b (`seemoo-lab/AirGuard`) surfaced a distinct opposite-pattern sub-class to G-4 LA-bit pairing: Tile, Chipolo (own-network mode), and Pebblebee emit STATIC MACs by design. AirGuard's risk-evaluation algorithm (`RiskLevelEvaluator.kt:36-37`) treats them as a first-class architecture distinction ("dynamic-MAC tracker" vs "static-MAC tracker"). CP14 migration 0012's `pair_kind` enum INTENTIONALLY EXCLUDES `static_mac_tracker` per dispatch §2.5 disposition ("different security architecture; handle via notes-JSON until a third sub-class is needed"). At what `n` of static-MAC observations does Argus introduce a structural `pair_kind` value or a separate identifier shape? Currently `n=3` (Tile + Chipolo + Pebblebee). Forward expectation: Wave-D / Wave-E may surface additional static-MAC ecosystems (LoRa-side trackers, industrial asset trackers) that push the question.
- **`operator_profile` architecture (G-17).** Three corporate operators surfaced in Wave-A Phase 3c (Lowe's Q1373493, Home Depot Q864407, Simon Property Group Q2287759) deploy surveillance hardware but don't manufacture it. CP14 migration 0014 HELD `operator_profile` from `identifier_type` extension; deferred to validator-side review. Options: (A) new `identifier_type` value (rejected — shape mismatch; operators are entities not products); (B) new `operators` table parallel to `manufacturers` + `procurement_records` (CEO recommendation); (C) fold into `procurement_records` (rejected — conflates buys with deploys). Trigger for resolution: Wave-D or Wave-E surfaces ≥10 `operator_profile` candidates OR Lynceus integration team requests operators-table support.
- **`§8.2 source_type` band for FAA RID-class primary-source registries.** Wave-A Phase 3a staged 481 `drone_id_prefix` instances from the FAA RID lookup (4783-record SQLite at FAA publicDOCRev 2025-11-28 build). The dispatch §4.1 cut-off rules require `independent_source_count ≥ 3` for Phase-4 promotion. FAA RID is structurally an authoritative numerical-allocation registry — closer to IEEE OUI assignments than to FCC filings or vendor spec sheets. Asking for "three independent sources" of what `1581Fxxx` means is structurally ill-defined because FAA's registry IS the source of truth. The cleaner structural question (board reframe at MAC-63 [`fe2beeee`](/MAC/issues/MAC-63#comment-fe2beeee-2571-475e-86f6-edc99f99ecad) 2026-05-11): should §8.2 grow a new `source_type='primary_registry'` band (parallel to but distinct from `regulatory` and `manufacturer_doc`; ceiling ~85–90, below `regulatory`'s court-verifiable ceiling but above `manufacturer_doc`)? If yes, FAA RID promotes single-source under that band and the ≥3-source cut-off rule remains untouched for the cases it's actually right for. 481 rows currently HELD pending Phase-5 human-CEO disposition. **RESOLVED by CP15 2026-05-11** — §8.2 grew the `primary_registry` band (70–85 single-source; up to 95 cross-band corroboration); ≥3-source cut-off waived for `primary_registry` only; FAA RID 481 rows + Apple `0x004C` + XUNTONG `0x09C8` (483 rows total) promote in promotion-cycle-2 at conf=85 single-source. Bible HEAD bumps to the CP15 commit; see `BIBLE_AMENDMENTS.md` CP15 entry.

**Wave G (Phase 6) — board-ratified 2026-05-08, queued for execution post-v1.0.0 ship** (added Correction Pass 12)

- **DMCA-takedown counter-notice template.** If a vendor issues a DMCA takedown for a Wave G finding in Argus's published exports, posture is: identifiers are facts (Feist), not copyrightable expression; Argus does not republish vendor source. Reliance: 17 USC §1201 security-research exemption + 37 CFR §201.40(b) implementing regulation. Pre-draft a counter-notice template under §512(g) for the file `wave_g/LEGAL_POSTURE.md`. Cross-reference from `THREAT_MODEL.md` at public-release prep so external readers understand the legal grounding. Surface for board review at Wave G Step 0 close.
- **EULA-conflict-policy.** Per-vendor judgment criteria for app-EULA conflicts with reverse-engineering: (a) hostile EULA + low yield-value → exclude; (b) hostile EULA + high yield-value → surface to board for explicit risk-acceptance; (c) standard reverse-engineering clause + standard yield-value → include (boilerplate prohibition is preempted by §1201 in US); (d) anti-circumvention clause specifically targeting security research → exclude (rare). Borderline cases come back to board. Surface specific vendor EULA concerns as Step-0 ground-truth deliverable.
- **Wave-G-vs-Wave-G.5 iOS deferral rationale.** Wave G is Android-first because Apple FairPlay encrypts most app binaries (decryption requires jailbroken iOS device) and most surveillance vendors with iOS apps also publish Android — Android-first captures the same vendor coverage at lower legal/operational cost. Wave G.5 / Phase 7 surfaces as a separate board-class proposal *after* Wave G Steps 1+2 complete and Android yield is empirically known. Specific Wave G.5 trigger: Step 0 surfaces a vendor that has *only* iOS app and significant yield-value (e.g., body-cam vendor exclusive to iOS) — flag for targeted Wave G.5 dispatch with vendor-specific scope.

**Deferred at CP5 sign-off (2026-05-06) — revisit at Wave-F / Phase-6**

- **§4.4 256-entry `mac_range` expansion ceiling — OUI-prefix routing without expansion.** All 8 active `mac_range` rows are OUI-28 / OUI-36 sub-allocations vastly exceeding §4.4's expansion ceiling, so even if §3.1 narrow-read flipped their `device_category`, they'd re-fall to `oversized_mac_range`. Board ratified CEO path-(c): defer routing semantics to Lynceus integration handoff (jointly bound between Argus export shape and Lynceus seeder protocol). (CP5_BRIEF §3.2; CP5 sign-off 2026-05-06.)

**Resolved at CP7 / CP8 / CP10 / SAR-10 (2026-05-07)**

Board ratification via comment [`4f075253`](/MAC/issues/MAC-1#comment-4f075253-2eae-4ea3-9db5-c67c6f02e012) 2026-05-07T17:10:13Z (six-pick + two-halt-flag bundle approved as recommended; bundled handoff [`f6c6e206`](/MAC/issues/MAC-1#comment-f6c6e206-51f5-4bee-a7db-b062d96cdf41) + doc [`lynceus_v03_integration`](/MAC/issues/MAC-1#document-lynceus_v03_integration)).

- ~~**Configurable `geographic_scope` filter for the high-confidence Lynceus export.**~~ Resolved at **CP7**: export-time categorical filter on `identifiers.geographic_scope`, default `["US"]` for both standard and high-confidence exports, configurable via export CLI flag. Records remain in canonical DB regardless; only the export shape filters. Schema unchanged (`identifiers.geographic_scope TEXT` exists in 0001 since CP-0). `_meta.dropped_in_export.geographic_scope_mismatch` tally added. Wave-A row backfilled to `US` (Flock Safety US-headquartered, US-deployed). See §4.4 + §7.5 + BIBLE_AMENDMENTS.md CP7.
- ~~**Single-product §2.1 vendor OUI categorization at export time — narrow §11 #10 / §5 Tier 4 reading vs strict §8.4.**~~ Resolved at **CP10**: narrow-read v0.1 cutover via Lynceus's `severity_overrides.yaml` operator-side architecture making FP-suppression revisable space. **17 rows flip** `device_category` from `unknown` to specific category at v0.1 cutover (DJI=13 drone, Flock Safety=1 alpr, Skydio=1 drone, Cellebrite=1 hacking_tool, SoundThinking=1 gunshot_detect; Hak5 prospective). All 17 stay below conf=70 (standard export only). Operator-override-as-FP-layer principle codified: Argus ships factual vendor-attribution; Lynceus owns alerting policy. DJI explicit FP-risk callout for Lynceus integration documentation. See §11 #10 carry-forward + BIBLE_AMENDMENTS.md CP10.
- ~~**`argus_record_id` upsert semantics in Lynceus seeder.**~~ Resolved at **SAR-10**: `argus_record_id = sha256(f"{identifier_type}|{normalized_identifier}").hexdigest()[:16]`. Hashes the §8.3 dedup key; stable under re-runs / confidence drift / source edits / vendor reattribution. Replaces prior integer-PK plan (which fails Lynceus's "stable across vendor reattribution" expected event under §8.3). One Wave-A test artifact (`d4bfc29b7d63f7b1`) re-imports under the new hash; notify Lynceus engineer in integration test cycle. See §7.5 + BIBLE_AMENDMENTS.md SAR-10.
- ~~**Severity for Lynceus export.**~~ Resolved at **CP8**: severity is owned operator-side via Lynceus's `severity_overrides.yaml` file. Argus does NOT emit `severity` in the export shape. §4.5 retained as superseded historical reasoning only (audit-trail discipline). Description format also tightened: ≤80 char flat `{vendor} {device_category}` (drops rich product-family seed); fallbacks `"{vendor} unknown"` / `"Unattributed identifier"`. See §4.5 superseded banner + §7.5 + BIBLE_AMENDMENTS.md CP8.
- ~~**Working-name "Talos" → final-name "Lynceus".**~~ Resolved at **CP9**: bible §-text rename throughout (Talos → Lynceus). File names UNCHANGED (`argus_export.json` / `argus_export_high_confidence.json` / `argus_export.csv` retain existing convention). Historical record (BIBLE_AMENDMENTS.md prior entries, CP4_BRIEF.md, CP5_BRIEF.md, PROJECT_STATE.md prior heartbeats) NOT retroactively renamed. See BIBLE_AMENDMENTS.md CP9.

**Resolved at CP5 sign-off (2026-05-06)**

Board ratification via approval [`71ef8139`](/MAC/approvals/71ef8139-c76c-4b1b-8971-b22720b7363d) 2026-05-06T20:17:10Z (CP5_BRIEF, commit `28bab20`, [MAC-47](/MAC/issues/MAC-47)).

- ~~**Project name.** "Argus" working name; final confirm at Checkpoint 5 alongside the coverage matrix.~~ Resolved: **"Argus" is the final v1 name.** Boundary: Argus owns identifier-canonical-state + Lynceus-bound exports; Lynceus owns scanner-side scanning + correlation. "MAC" is the Paperclip issue-prefix only.
- ~~**`device_cluster_id` for vehicle / operator correlation.**~~ Resolved: **SAR-3 lean confirmed final** — Argus identifies, Lynceus correlates. No Argus-side schema change; correlation logic owned by Lynceus team.
- ~~**Whether to query MuckRock's API or just their search.**~~ Resolved at Phase-4 Wave-D path-(a) early-cut ([MAC-31](/MAC/issues/MAC-31)): search was used; corpus-ceiling held at 0; question moot.
- ~~**How aggressive on inference?** Bible says inferences are capped at 70 confidence.~~ Resolved: **70-cap binding for inferred rows confirmed final.** No current row pressure on the cap (all Phase-5 inferred rows landed at 50–55 per SAR-1 LAA-bit penalty + strict §8.4 conf=50 starting band).

**Resolved during 2026-05-04 correction pass**

- ~~**Confidence threshold for the default scanner export.**~~ Resolved at Checkpoint 0 (default = 70). Reconfirmed by Correction 2 (§4.5) and Correction 8 (§7.5): `argus_export_high_confidence.json` uses `confidence ≥ 70`; `argus_export.json` uses `confidence ≥ 30`.
- ~~**Output file naming convention.**~~ Resolved by Correction 8 / §7.5 / §9 item 2: `argus_export.json` and `argus_export_high_confidence.json` are the canonical Lynceus-bound names; `argus.db` and `argus_export.csv` round out the export set.

Add new questions to this section as they arise. Do not invent answers.

---

*End of bible. Re-read Section 0 if you've forgotten how to use this document.*
