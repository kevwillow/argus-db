# Argus — Surveillance Identifier Intelligence Database

**Working name:** Argus (the many-eyed watcher; intel layer that feeds the scanner project)

**Companion project:** the Raspberry Pi wireless scanner (consumes Argus exports)

---

## TL;DR

Argus's formal specification. Defines the data shape (`identifiers`, `manufacturers`, `sources`, `raw_observations`, `deployment_observations`, `procurement_records`, `behavioral_signatures`, and the audit tables), the confidence-band ladder per source class, the §11 envelope (no-fabrication / amendment-log / no-PII / source-url-direct / Feist facts-only / and the rest of the hard-rule set), the migration discipline, and the canonical 16-value `device_category` vocabulary.

Intended audience: contributors writing migrations, validators ratifying cycle promotions, security-research consumers verifying provenance chains, and orchestrators dispatching extraction or admission cycles. The clause numbering (`§N` and `§N.M`) is load-bearing — every amendment in [`BIBLE_AMENDMENTS.md`](BIBLE_AMENDMENTS.md) and every SAR (Surprise Anti-Recurrence) entry references this document by `§N` anchor. Promotion gates, export-shape contracts, and downstream-consumer license carry-forward all bind on these clause anchors. Treat this document as the source-of-truth at any disagreement.

First-time readers should start with [`../USER_GUIDE.md`](../USER_GUIDE.md) for a plain-language overview, or [`../../README.md`](../../README.md) for the project summary. For the version-by-version release history, see [`../../CHANGELOG.md`](../../CHANGELOG.md). For the formal amendment log that lists every Correction Pass and every SAR rule layered onto this spec since the initial cut, see [`BIBLE_AMENDMENTS.md`](BIBLE_AMENDMENTS.md).

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
13. **Automotive telematics** — automotive infotainment/telematics arms of multi-arm vendors (e.g., Parrot Automotive — distinct from drone-arm Parrot SAS). Codified at CP32 §1 (migration 0026) for `device_category` enum parity with the §4.6 multi-arm hub-and-spoke schema. Schema slot opens v1.4.1 Stage 2; row-level promotions are future evidence-arrival concerns (no v1.4.1 row promotions land at CP32).

### 2.2 Out of Scope

- Anything requiring private data, leaks, or non-public access
- Real-time deanonymization of individual officers or agencies (we identify *equipment categories*, not people)
- Active interference, jamming, or attack tooling — Argus is a passive identification database only
- Detection logic itself (that lives in the scanner project; Argus only produces identifiers + metadata)
- Cellular IMSI/IMEI databases (different problem space, legal complexity, out of scope)
- Anything where the underlying source is classified or restricted

### 2.3 A Note on Ambition

The human chose "everything in one shot" for v1. Honor that, but be honest in progress reports about coverage. It is better to have 200 high-confidence Flock records than 5,000 low-confidence guesses across 15 categories. If a category has no good public sources, document that and move on rather than fabricating coverage.

### 2.4 Empirical-Premise Verification Precondition

Before any runguide's §3.1 bulk dispatch fires, the runguide's load-bearing premises MUST be empirically verified against the live source within the same calendar day as dispatch (24-hour staleness ceiling). Load-bearing premises include: URL templates, HTML/JSON response structure assumptions, authentication posture, rate-limit posture, identifier-pattern presence in the response surface, response-shape stability under documented filter / search parameter combinations, and the canonical identifier-field name (e.g. `application_id` vs `grant_id`) the §4 extraction expects.

Verification probes are documented in **§3.0 of the runguide** (per the MAC-101 PC1.7 pattern, which was the first canonical instance of a §3.0 verification probe section). §3.0 probes must complete with one of two clean outcomes before §3.1 fires:

- **CLEAN POSITIVE** — every load-bearing premise holds; §3.1 dispatch authorized.
- **CLEAN NEGATIVE** — at least one load-bearing premise is empirically false; §3.1 dispatch **halted** under §6 #5; runguide returns to drafting per the patch-cycle convention; **CEO disposition required** before re-fire.

**INCONCLUSIVE** outcomes (probe completed but result is ambiguous — e.g. partial reachability, response shape detected but not the expected schema, auth challenge surfaced but not fully diagnosed) **also halt** the runguide; CEO disposition required as for CLEAN NEGATIVE.

**Retroactive binding:**

- Runguides **drafted but not yet dispatched** are subject to §2.4 retroactively; add §3.0 verification-probe section to their published structure before any future dispatch fires.
- Pre-existing runguides being **re-dispatched** (after a halt + patch cycle) are subject to §2.4 at re-dispatch time; the verification probe is mandatory regardless of any prior calibration the runguide may carry.
- Runguides that have **completed successfully** (e.g. MAC-101 fccid.io) are not retroactively halted, but should have §3.0 formalized post-hoc to preserve the verification-probe lineage for future Wave-N' re-dispatches of the same source.

Codified at CP27 (`BIBLE_AMENDMENTS.md`) after the 2026-05-17→05-18 cycle-7 autonomous wave surfaced six concrete failure-mode anchors in a single 8-hour window (5 external runguides + 1 internal extraction pass — MAC-102 ISED, MAC-103 BT SIG, MAC-105 USPTO PatFT, MAC-107 GitHub Code Search, MAC-110 Ofcom, plus MAC-101 PC1.7).

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
| `identifier_type` | TEXT NOT NULL | enum: `oui`, `mac`, `mac_range`, `bssid`, `ssid_exact`, `ssid_pattern`, `ble_uuid`, `ble_service`, `device_fingerprint`, `ble_local_name`, `ble_characteristic`, `product_family_codename` (three above added Correction Pass 13 — Wave G structural fidelity), `ble_manufacturer_id` (added Correction Pass 14 — migration 0011 BLE SIG 16-bit company-identifier namespace), `drone_id_prefix`, `icao_24bit_address`, `rf_channel`, `burst_cadence_ms`, `bandwidth_mhz`, `device_class_id`, `rf_burst_duration`, `rf_protocol_constant`, `wifi_aware_service_name`, `wifi_ie_element_id`, `bluetooth_le_pdu_type`, `wifi_frame_control_subtype`, `wifi_nan_param_signature` (thirteen above added Correction Pass 14 — migration 0013 Drone-RID + proprietary RF-protocol cluster), `alpr_model` (last added Correction Pass 14 — migration 0014 surveillance metadata: ALPR/camera product profile) |
| `device_category` | TEXT NOT NULL | enum from §2.1: `alpr`, `imsi_catcher`, `body_cam`, `police_radio`, `drone`, `gunshot_detect`, `hacking_tool`, `covert_cam`, `gps_tracker`, `face_recog`, `drone_detect`, `unknown` (12 values; mirrors live CHECK constraint at migration 0001 verbatim). Note: §2.1 narrative #5 `in_vehicle_router` is an in-scope category per CP3 but its schema-migration sibling defers to first-promotion-time per `feedback_enum_amendment_needs_schema_migration_sibling.md` forward-looking-codification caveat; until promotion, Cradlepoint / Sierra Wireless rows use `device_category='unknown'` with §11 #13 carveout. **Canonical-form note:** `alpr` is the canonical value for license-plate-reader cameras (matches id=1 Flock Safety precedent + 80+ promoted rows). Common dispatch-typo form `alpr_camera` is NOT in the CHECK enum and will fail constraint validation; if a future dispatch spec asserts `alpr_camera`, workers MUST apply `alpr` per this precedent (binding clause). Surfaced at MAC-110 §E.4 close [`5f1bf2e`](https://github.com/kevwillow/argus-db/commit/5f1bf2e); codified per MAC-101 dispatch §2.1(a). |
| `manufacturer` | TEXT | normalized vendor name |
| `model` | TEXT | when known |
| `confidence` | INTEGER | 0–100, see §8.2 |
| `source_url` | TEXT NOT NULL | direct URL to the evidence |
| `source_type` | TEXT NOT NULL | enum: `official`, `regulatory`, `procurement`, `academic`, `foia`, `crowdsourced`, `inferred`, `manufacturer_doc`, `manufacturer_app` (added Correction Pass 13 — CP12 §8.2 schema sibling), `primary_registry` (last added Correction Pass 15 — §8.2 sub-banding for FAA RID + Bluetooth SIG + IEEE OUI cluster) |
| `source_excerpt` | TEXT | short quoted/paraphrased justification (≤200 chars) |
| `geographic_scope` | TEXT | ISO country/region codes, comma-sep, or `global` |
| `first_seen` | DATETIME | when we first ingested this record |
| `last_verified` | DATETIME | when a source-check last confirmed |
| `notes` | TEXT | free text |
| `superseded_by` | INTEGER | FK to `identifiers.id`; carries a tri-state semantic — see CP32 §9 note below |

**`superseded_by` tri-state semantic (CP32 §9, 2026-05-21).** The `superseded_by` column carries three distinct semantics:

- **`NULL`** — row is **active** (canonical contract; canonical active-set filter is `WHERE superseded_by IS NULL`).
- **`<other_id>`** — row is **superseded by a successor** identifier row (the canonical merge semantic — `superseded_by` points to the row that absorbed this one via §8.3 dedup-with-supersession, deprecated-MAC supersession, or analogous reattribution).
- **`<self_id>` (self-loop)** — row is **withdrawn without successor** (the §11 #3 PII-demotion semantic — row is `§8.2` demoted to `confidence=0` and self-loop-tagged so it is never surfaced as active and never points to an inappropriate successor; the self-loop is the explicit "no successor exists" signal). Surfaced at MAC-217 Track B (4 PII demotes: Jacobs `*.escg.jacobs.com` hostnames). Withdrawn-without-successor query convention: `WHERE superseded_by = id`.

The tri-state was implicit pre-MAC-217 and is now codified at CP32 §9. Consumer-side audits, JOIN logic, and active-set queries MUST handle all three cases correctly; both `<other_id>` and `<self_id>` rows are non-active. No schema mutation — the existing `superseded_by INTEGER REFERENCES identifiers(id) ON DELETE SET NULL` column has always admitted all three cases.

### 4.2 Supporting tables

- **`sources`** — registry of every source crawled, with last-fetch timestamp and status. `source_type` CHECK enum (live post-migration 0020 — 13 values): `official`, `regulatory`, `procurement`, `academic`, `foia`, `crowdsourced`, `inferred`, `manufacturer_doc`, `manufacturer_app` (added CP13 — migration 0009), `primary_registry` (added CP15 — migration 0015), `judicial_filing` / `disclosure_filing` / `procurement_disclosure` (last three added Correction Pass 23 — migration 0020; wide-net cycle-3 §1 finding #2 taxonomy refinement). The 3 CP23 values are sources-tier taxonomy only; identifier-row promotion still binds on the separate `identifiers.source_type` enum per §8.2. License + license_attribution + license_posture + access_mode + per-admission audit fields live INSIDE `notes_json` (Correction Pass 23 — cycle-1 finding #1 license-into-notes folding contract); no top-level license column on the `sources` row. Top-level columns: `id`, `name`, `url`, `source_type`, `tier`, `last_fetched_at`, `last_status`, `notes`.
- **`raw_observations`** — staging table; raw extracted records before normalization (preserve forever for audit). Holds rows that carry an actual or candidate identifier (MAC/OUI/BSSID/SSID/UUID) in `candidate_identifier` keyed by §4.1 `identifier_type`.
- **`deployment_observations`** — staging table for Tier 1 sources that yield agency × technology × location × vendor metadata but **no** MAC/OUI/SSID/UUID identifier (EFF Atlas of Surveillance, DeFlock). Identifier columns intentionally absent — promotion to `identifiers` requires a Phase 3+ inference linking a deployment to a concrete identifier candidate (§11 #1). Idempotency keyed by `(source_id, source_row_key)` where `source_row_key` is the source's stable per-row natural key (e.g. Atlas's `AOSNUMBER`). Added in Correction Pass 4 (BIBLE_AMENDMENTS).
- **`procurement_records`** — staging table for Tier 2/3 procurement-only rows (SAM.gov, city council minutes, FOIA-released procurement docs) that name an agency × vendor purchase but carry **no** MAC/OUI/SSID/UUID identifier. Schema includes a nullable `linked_identifier_id` FK back to `identifiers` for the upgrade path when a later source attaches a concrete identifier to the same purchase. Per §4.5 procurement-only carveout / §11 #14, these rows are NEVER exported to Lynceus — they are analytical only. Created in MAC-2 / Phase 1 (signed off at Checkpoint 1); documented in §4.2 in Correction Pass 5 (BIBLE_AMENDMENTS). **Vendor-matching discipline (CP23 — migration 0021):** `vendor_canonical_name` carries the upstream USAspending verbatim recipient name (often inconsistent across awards for the same vendor: `'AXON ENTERPRISE INC'` vs `'Axon Enterprise, Inc.'` vs `'AXON ENT INC'` all collapse to a single canonical entity). The companion column `vendor_canonical_normalized TEXT NOT NULL DEFAULT ''` (added migration 0021) materializes a deterministic alias-collapse key for cross-validation against `manufacturers.canonical_name` and `manufacturers.aliases`. Normalization algorithm: LOWER → strip ALL punctuation → collapse whitespace → strip leading/trailing whitespace → repeatedly strip trailing whole-word suffix tokens (`inc`, `incorporated`, `corp`, `corporation`, `llc`, `l l c`, `ltd`, `limited`, `plc`, `co`, `company`, `lp`, `llp`, `gmbh`, `ag`, `sa`, `pty`, `bv`) → re-strip whitespace → empty result stores `''`. Algorithm canonical reference: `db/normalize_vendor.py::normalize_vendor_name` (pure function; DATA_DICTIONARY.md §-procurement_records carries the prose for downstream consumers). Index: `idx_procurement_records_vendor_canonical_normalized`. **Agency-matching discipline (CP23 — cycle-3 §1 finding #5):** `agency_name` is the upstream USAspending concatenation `"Awarding Agency / Awarding Sub Agency"`; split on `" / "` for hierarchical use. **source_excerpt cap:** ≤200 chars per the live CHECK constraint (NOT ≤500; see §4.3 per-table cap table).
- **`fcc_grantees`** — staging table for FCC EAS grantee registrations (Phase 3 / MAC-7; first source = opendata.fcc.gov dataset `3b3k-34jp`, USGOV_WORKS public domain). Holds grantee_code → entity-name + mailing/contact metadata + date_received. Identifier columns intentionally absent — `grantee_code` is a regulatory entity prefix, not a per-device identifier (per-device FCC IDs are formed `grantee_code + product_code`, owned by Phase 4 `fcc_equipment_filings` if/when created). Idempotency keyed by `(source_id, source_row_key=grantee_code)`. Stale-mirror sources: `sources.notes` MUST carry `dataset_freeze_date` + `staleness_warning` when the upstream mirror is documented stale (3b3k-34jp is frozen at 2021-03-22; Flock Safety + post-2020 grantees absent — Phase 4 owns the gap). Added in Correction Pass 6 (BIBLE_AMENDMENTS).
- **`extraction_runs`** — log of every extraction job: agent id, source, started_at, finished_at, records_in, records_out, errors
- **`conflicts`** — when two sources disagree on the same identifier; reviewed and resolved by CEO
- **`source_reclassifications`** — audit table for row-level reclassification events on `identifiers` rows (band downgrade, source_url upgrade, source_type change). Codified at CP19 (2026-05-13) as the structural audit-trail surface for §11 #8 strict-reading sweeps and any future row-level band changes on already-promoted canonical rows. Per-row entry captures pre/post `source_url`, `source_type`, `confidence` snapshot + `sweep_event_id` grouping + substantive `reclassification_reason` (convention: self-explanatory at row-level without cross-referencing the dispatch) + `reclassification_anchor` citation. First population: MAC-88 Wave-B+ sources reclassification sweep (2026-05-14; 335 Scope 2 downgrades + 14 Scope 3 lifts of non-unknown rows). Added in Correction Pass 19 (BIBLE_AMENDMENTS).

### 4.3 Normalization rules

- MAC addresses: lowercase, colon-separated (`aa:bb:cc:dd:ee:ff`)
- OUIs: lowercase, colon-separated 3 octets (`aa:bb:cc`)
- BLE UUIDs: lowercase, hyphenated 8-4-4-4-12 format
- SSIDs: stored exactly as broadcast. `ssid_exact` matches by exact equality; `ssid_pattern` matches by **case-insensitive SUBSTRING containment** at the Lynceus consumer (`? LIKE '%' || needle || '%' COLLATE NOCASE`, Lynceus 0.9.2 `db.py:1126`) — **not** regex / PCRE / POSIX / glob (the earlier "POSIX regex" claim was wrong; corrected CP51 / MAC-517 after the board pinned Lynceus 0.9.2 at MAC-516). `%` and `_` in a pattern are NOT escaped and act as SQL wildcards (accepted edge case). Argus stores `ssid_pattern` values verbatim (including legacy `(?i)^…`, char-classes, `%`) and converts each to a Lynceus-safe leading-literal substring at export (`export_lynceus.py::_ssid_pattern_to_substring`); generic/short stems are FP-held. `ble_local_name` matches by **exact equality, case-SENSITIVE** in Lynceus 0.9.2 (literals only; substring/template matching deferred to Lynceus v1.4.3+).
- Manufacturer names: matched against a canonical list maintained in `manufacturers` table; new vendors added explicitly. **Aliases live as a comma-separated TEXT string on `manufacturers.aliases`** (CP23 — wide-net cycle-3 §1 finding #1 + cycle-4 §1 finding #1 formalization); there is NO `manufacturers_aliases` separate table. Append semantics: `aliases = CASE WHEN aliases IS NULL OR aliases = '' THEN ? ELSE aliases || ',' || ? END`. Lookup semantics: `WHERE aliases LIKE '%term%' OR LOWER(canonical_name) = LOWER(?)`.

**source_excerpt per-table CHECK constraint cap table (Correction Pass 23 — DB-verified actuals; supersedes any contradicting prior runguide language).** Per cycle-3 §1 finding #3 contradicted by live schema; CP23 codifies the authoritative table:

| Table | Live CHECK constraint |
|---|---|
| `identifiers` | `CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)` |
| `raw_observations` | no CHECK constraint (plain TEXT; app-level enforcement at 200 via `db/sources/vendor_docs.py::raise_on_overflow` per migration 0006 header) |
| `procurement_records` | `CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)` |
| `council_minutes_matters` | `CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)` |
| `behavioral_signatures` | column does not exist (provenance via `source_id` + `source_file_relative` + `source_line` + `evidence_json` per migration 0010) |

Future runguides MUST consult this CP23 table for the canonical per-table cap. Cycle-3 patch §1 finding #3 source_excerpt cap claims (≤500 for identifiers/raw_observations) are legacy schema-truth-as-of-2026-05-16-with-known-drift on this sub-item; the live actuals above govern.

**`sources.notes_json` JSON contract (Correction Pass 23 — cycle-1 finding #1 license-into-notes folding).** License + license_attribution + license_posture + access_mode + per-admission audit fields live INSIDE `notes_json`, NOT as top-level columns. Canonical sources-row top-level keys: `id`, `name`, `url`, `source_type`, `tier`, `notes` (JSON-serializing `notes_json`), `last_fetched_at`, `last_status`.

- `notes.license`              — short licence-posture identifier (vocabulary documented below; not a CHECK constraint, remains free-form for future extension)
- `notes.license_attribution`  — verbatim attribution text per the source's licence page (≤200 chars convention)
- `notes.license_posture`      — duplicates `notes.license` for downstream-consumer prose authoring; canonical surface for LICENSE-DATA prose + Validator promotion-time gates
- `notes.access_mode`          — source-tier access shape (vocabulary below)
- `notes.access_mode_reason`   — operator-facing explanation (informational)
- `notes.session_admission`    — admission session identifier
- `notes.admission_date_utc`   — admission timestamp
- `notes.runguide_path`        — path to the authoring runguide
- `notes.cycle_completion_state` — partial-cycle admission state (CP26 vocabulary below; absent = complete)
- `notes.next_cycle_dispatch_scheduled_for_utc` — ISO-8601 UTC timestamp of next planned dispatch (required when `cycle_completion_state` is non-absent)
- `notes.next_cycle_dispatch_runguide_path` — relative path to the dispatch artifact (required when `cycle_completion_state` is non-absent)
- `notes.partial_yield_metrics_at_admission` — JSON snapshot of yield-at-admission for audit comparison post-completion (required when `cycle_completion_state` is non-absent)
- per-admission audit fields per the specific runguide's §9 contract

**Registered `notes.license` vocabulary (Correction Pass 23 — initial set; open for future extension):**

| Value | Meaning |
|---|---|
| `OGL-3.0` | UK government Open Government Licence v3.0 (UK Companies House cycle-1 admission) |
| `PUBLIC_DOMAIN` | US federal-government work product per 17 USC §105 (SEC EDGAR cycle-1 admission) |
| `US_STATE_PUBLIC_RECORDS` | US state public-records statutes (DE Title 8 §391, CA Gov Code §6253, TX Bus Org Code Ch 22 — cycle-3 DE/CA/TX state SoS admissions) |
| `CC0` | CC0 1.0 Universal Public Domain Dedication (CourtListener cycle-4 admission; Free Law Project metadata) |
| `MIT`, `AGPL-3.0_declared`, `CC-BY-NC-SA-4.0`, `ODbL-1.0`, `NO_LICENSE_DECLARED`, … | per-source declared posture from upstream license file; sentinel forms documented at §11 #16 + CP21 canonical sentinel-key |

These compose with the per-promoted-identifier canonical sentinel key `notes.upstream_license_posture` documented at §11 #16 sub-rule (CP21 ratification). Source-tier `notes.license` documents the upstream posture; identifier-tier `notes.upstream_license_posture` carries it forward for downstream license-aware filtering.

**`notes.access_mode` vocabulary (Correction Pass 23 — cycle-3 addendum §1):**

| Value | Meaning |
|---|---|
| `automated_api` | Source queried via documented API; end-to-end automated |
| `automated_html_parse` | Source queried via automated HTML scraping; no anti-bot wall |
| `automated_with_auth` | Automated, but requires API key / token / user-agent |
| `mixed_automated_manual` | Some candidates automated, some operator-manual |
| `operator_manual_only` | All access is operator-manual via browser; automation structurally blocked (CAPTCHA, anti-bot wall, session gates) |

**Discipline guarantees (uniform across access_modes):** per-row provenance discipline + promotion-gate confidence band are IDENTICAL regardless of access_mode. The `access_mode` field is informational/operational only, NOT a confidence modifier. Operator-manual findings carry `notes.fetch_mechanism="operator_manual_browser"` per-row (row-level, complementing the source-level access_mode). Sources admitted prior to CP23 do NOT require backfill — absent-access_mode is equivalent to `automated_api` per backward compat. First-class column promotion deferred to a future CP once the value-set stabilizes (per cycle-3 addendum §6 default recommendation).

**`notes.cycle_completion_state` vocabulary (Correction Pass 26 — SAM.gov cycle-5 day-0 partial fold):**

| Value | Meaning |
|---|---|
| (field absent) | Source is complete; canonical state (default backward-compat reading) |
| `partial_pre_day1` | Source admission landed before its first full data sweep completed; explicit incomplete-state flag pending next-cycle dispatch |
| `partial_pacing_in_flight` | Source is mid-multi-day pacing run; additional data expected in subsequent cycles |
| `partial_pacing_exhausted` | Source's multi-day pacing terminated short of completion; deferred to future cycle |

**Composition with `access_mode` (CP26):** orthogonal — partial completion is a temporal state, access_mode is a mechanism state. SAM.gov sid=50 cycle-5 day-0 case is `access_mode="automated_api"` + `cycle_completion_state="partial_pre_day1"`. When `cycle_completion_state` is non-absent, three companion `notes_json` fields are REQUIRED: `next_cycle_dispatch_scheduled_for_utc` (ISO-8601 UTC), `next_cycle_dispatch_runguide_path` (relative path), `partial_yield_metrics_at_admission` (JSON snapshot of yield-at-admission). Absent-`cycle_completion_state` is equivalent to "complete" per backward compat — no migration of pre-CP26 sources required. First-class column promotion deferred until value-set stabilizes per the CP23 `access_mode` precedent (≥2 distinct sources consuming non-absent state).

### 4.4 Lynceus export mapping

The downstream consumer (Lynceus, the Raspberry Pi RF security monitor) has a fixed, minimal watchlist schema with `pattern_type ∈ {mac, oui, ssid, ble_uuid}`. Argus's richer `identifier_type` enum must be collapsed at export time. Lynceus cannot be modified to accept Argus's richer enum; Argus does the collapsing. The export worker (§7.5) applies exactly this mapping:

| Argus `identifier_type` | Lynceus `pattern_type` | Notes |
|---|---|---|
| `oui` | `oui` | direct pass |
| `mac` | `mac` | direct pass |
| `bssid` | `mac` | a BSSID *is* a MAC for Lynceus's purposes |
| `ssid_exact` | `ssid` | direct pass |
| `ssid_pattern` | `ssid_pattern` | **MAP** (CP51 / MAC-517) — Lynceus 0.9.2 `ssid_pattern` = case-insensitive substring (`LIKE '%'||needle||'%' COLLATE NOCASE`, `db.py:1126`), NOT regex. `export_lynceus.py::_ssid_pattern_to_substring` converts each value to its leading-literal substring(s) — strips `(?i)`/`^`, SPLITs a leading `(a|b)` alternation, takes the literal run up to the first metachar. FP-held (drop-bin `ssid_pattern_fp_hold`) when the stem is <3 chars or a generic device-class term (e.g. `lpr`). Superseded the stale "no regex in v0.2" DROP. |
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
| `ble_service_uuid` | `ble_uuid` | added Correction Pass 21 (migration 0018); **alias-collapse** to existing `ble_uuid` per the CP13 `ble_service → ble_uuid` precedent (same semantic: BLE service UUIDs ARE UUIDs for Lynceus). Single pattern_type per Lynceus contract; cleanest. Rationale at MAC-101 §2.5 CEO recommendation [`4367e10b`](/MAC/issues/MAC-101#comment-4367e10b) + board ratification [`e246a32a`](/MAC/issues/MAC-101#comment-e246a32a). |
| `ble_company_id` | `ble_manufacturer_id` | added Correction Pass 21 (migration 0018); **alias-collapse** to existing `ble_manufacturer_id` per the CP14 / migration 0011 precedent (same semantic: 2-byte SIG company-ID from BLE adv manufacturer-specific data; Lynceus scanner parses the same field). Single pattern_type per Lynceus contract; cleanest. Rationale at MAC-101 §2.5 + board ratification [`e246a32a`](/MAC/issues/MAC-101#comment-e246a32a). |
| `ble_protocol_byte_table` | (DROPPED) | added Correction Pass 21 (migration 0018); multi-byte protocol-byte structure pattern (AirTag/FindMy protocol byte tables per src=29 nixxxo/tagfinder); sub-protocol-level multi-field aggregate, NOT a single match value. Same shape rationale as `wifi_nan_param_signature` DROP (CP16). |
| `frequency_band` | (DROPPED) | added Correction Pass 21 (migration 0018); parametric metadata (spectral-occupancy property of an emitter, not a wire-observable identifier). Same shape rationale as `rf_channel` / `bandwidth_mhz` DROPS (CP16). |
| `ble_protocol_byte` | (DROPPED) | added Correction Pass 21 (migration 0018); sub-protocol-level single byte. Same shape rationale as `bluetooth_le_pdu_type` / `wifi_ie_element_id` DROPS (CP16) — too coarse to function as a discrete pattern match value. |
| `operator_profile` | (DROPPED) | added Correction Pass 21 (migration 0018); surveillance-operator entity attribution (Lowe's, Home Depot, Simon Property Group, etc. surfaced at Wave-A Phase 3c FoggedLens). Operator entities deploy hardware but don't broadcast operator-profile identifiers; analytical-only taxonomy. Same shape rationale as `product_family_codename` / `alpr_model` DROPS. |
| `x509_cert_sha256_prefix` | (DROPPED) | added Correction Pass 21 (migration 0018); device-side x509 certificate SHA-256 prefix extracted from firmware binary mining (src=42 GainSec falcon-sparrow Phase 6ε). NOT RF-broadcast in normal operation; forensic / firmware-anchored. |
| `ble_adv_interval` | (DROPPED) | added Correction Pass 21 (migration 0018); parametric metadata (BLE advertising temporal interval). Same shape rationale as `rf_burst_duration` / `burst_cadence_ms` DROPS (CP16) — temporal property, not a match value. |
| `ble_payload_offset` | (DROPPED) | added Correction Pass 21 (migration 0018); sub-protocol-level byte offset within BLE adv payload structure. Parametric metadata; not a discrete match value. |
| `firmware_sha256_hash` | (DROPPED) | added Correction Pass 21 (migration 0018); firmware-binary SHA-256 hash. NOT RF-broadcast; forensic-only identifier class extracted from firmware mining. |
| `network_endpoint` | (DROPPED) | added Correction Pass 21 (migration 0018); operator-side network endpoints (URLs/IPs/FQDNs of scanner backend infrastructure surfaced at src=41 GainSec anti-crime). NOT RF-broadcast; forensic / operator-side. |
| `firmware_image_variant` | (DROPPED) | added Correction Pass 21 (migration 0018); firmware build identifier strings (e.g., "Falcon-EDL-Firehose-v1.2.3"). NOT RF-broadcast; forensic / firmware-anchored. |
| `qualcomm_chip_format_id` | (DROPPED) | added Correction Pass 21 (migration 0018); Qualcomm chipset format identifier (hardware-anchor). NOT RF-broadcast; extracted from firmware binary mining. |
| `firmware_branded_string` | (DROPPED) | added Correction Pass 21 (migration 0018); branded marketing strings extracted from firmware binaries. NOT RF-broadcast; forensic / firmware-anchored. |
| `asdstan_message_type` | (DROPPED) | added Correction Pass 21 (migration 0019; MAC-117 round-2 vocab); ASTM Remote ID protocol broadcast message-type enum. Broadcast over RF in messages but as discrete enum values; not as a wire-observable single-string match value at the Lynceus pattern_type granularity. Same shape rationale as `device_class_id` DROP (CP16). |
| `asdstan_enum_value` | (DROPPED) | added Correction Pass 21 (migration 0019; MAC-117 round-2 vocab); ASTM Remote ID field-encoded enum values (ua_category, id_type, height_type, location_source). Broadcast in messages as discrete codes; sub-message-level enum-value granularity not within Lynceus pattern_type contract. Same shape rationale as `asdstan_message_type` DROP. |
| `dji_protocol_struct_format` | (DROPPED) | added Correction Pass 21 (migration 0019; MAC-117 round-2 vocab); DJI Drone-ID broadcast struct format string (v1, v2). Device-emitted protocol-struct format identifier; Lynceus matches on the broadcast payload contents (`drone_id_prefix` already MAP), not on the struct-format meta-identifier itself. Same shape rationale as `qualcomm_chip_format_id` DROP. |
| `gpt_partition_uuid` | (DROPPED) | added Correction Pass 21 (migration 0019; MAC-117 round-2 vocab); device-side storage layout identifier (Qualcomm GPT partition UUIDs on Picard/Bravo). NOT RF-broadcast; firmware-anchored. Same shape rationale as `firmware_image_variant` DROP. |
| `chipset_codename` | (DROPPED) | added Correction Pass 21 (migration 0019; MAC-117 round-2 vocab); firmware-anchored device model class (Qualcomm SoC codenames: APQ8009, etc.). NOT RF-broadcast at the model-class level (vendor OUI `oui` MAP captures device-vendor; chipset-codename is a sub-model attribute extracted from firmware). Same shape rationale as `qualcomm_chip_format_id` DROP. |
| `firmware_build_string` | (DROPPED) | added Correction Pass 21 (migration 0019; MAC-117 round-2 vocab); Qualcomm BOOT/SBL build version string (e.g., `BOOT.BF.3.3-00163`). Device-side firmware identity; NOT RF-broadcast. Same shape rationale as `firmware_branded_string` DROP. |
| `firmware_build_uuid` | (DROPPED) | added Correction Pass 21 (migration 0019; MAC-117 round-2 vocab); firmware build GUID (binary-unique identifier per build). NOT RF-broadcast; firmware-anchored. Same shape rationale as `firmware_sha256_hash` DROP. |
| `fcc_grantee_code` | (DROPPED) | added Correction Pass 31 (migration 0025); FCC EAS grantee code (3- to 5-char regulatory entity prefix assigned to manufacturers by FCC for equipment authorization). NOT an RF-broadcast identifier — it is the issuing-prefix of FCC IDs (`grantee_code + product_code` form). Paired with `equipment_class_code` via `pair_kind='fcc_grantee_equipment_class'` per CP14 paired-identifier discipline. Default DROP via §11 #13 at `device_category='unknown'`; high-conf-export INCLUDE requires explicit per-row `device_category` at a valid §2.1 enum value. |
| `equipment_class_code` | (DROPPED) | added Correction Pass 31 (migration 0025); FCC EAS equipment-class code (3-char regulatory code denoting device type within a grantee's EAS filings). Always paired with `fcc_grantee_code` per §11 #7 provenance. Same shape rationale as `fcc_grantee_code` DROP — regulatory metadata, not RF-broadcast. |
| `network_discovery_protocol_pattern` | (DROPPED — `NDPP_pending_lynceus_v0_3_scanner_support`) | added Correction Pass 35 (mig-0028 admission, CP35 §4.4 ratification at MAC-255); network-discovery protocol pattern strings (mDNS-SD / WS-Discovery / SSDP / ONVIF-WS-Discovery response substrings) extracted from companion-app static analysis of Bosch / Axis / Hanwha / Pelco / Avigilon CCTV families. 18 high-confidence rows on `device_category='cctv_camera'` admitted under CP34 (mig-0028). **Option (b) DROP** ratified at CP35: rows retained in canonical `identifiers` (no row loss; high-conf cohort preserved for future export-time admission); export-side surface gated until Lynceus v0.3 ships scanner-side `discovery_protocol_signature` pattern_type support (option (a) MAP requires sibling cross-repo Lynceus v0.3 scanner work outside the v1.5.3 ship-gate scope). Mirrors the CP16 default DROP posture (12 DROPPED vs 3 MAP for CP14 cluster). Promoted rows remain analytical evidence; lifting requires CP35-successor ratification after Lynceus v0.3 lands. |

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

### 4.6 Multi-arm manufacturer hub-and-spoke schema (CP31 — migration 0025)

CP31 added three columns to the `manufacturers` table to support multi-arm vendors — manufacturers with internal divisions that produce structurally distinct device classes (e.g., Parrot SAS's drone vs. automotive-telematics arms):

- `parent_manufacturer_id INTEGER NULL REFERENCES manufacturers(id)` — FK self-reference for arm → hub linkage. NULL on hubs; set to hub's id on arms.
- `is_arm BOOLEAN NOT NULL DEFAULT 0` — explicit arm flag. 0 on hubs (default backfill).
- `query_default TEXT NOT NULL DEFAULT 'visible' CHECK (query_default IN ('visible','hidden_arm'))` — default-query semantics. Hubs default to 'visible'; arms default to 'hidden_arm'.

**Default query rule.** All queries against `manufacturers` MUST filter `WHERE query_default = 'visible'` UNLESS the call site is explicitly auditing arm rows. Arm rows surface only via:

- Explicit `WHERE query_default IN ('visible','hidden_arm')` (audit query)
- JOIN through `parent_manufacturer_id` (parent-child traversal)
- Direct FK reference from `identifiers.manufacturer_id` (per-identifier attestation; future-FK migration pending — see CP31 §3 in BIBLE_AMENDMENTS)

**Current-state architectural caveat (v1.4.1).** `identifiers.manufacturer` is denormalized TEXT; no `manufacturer_id` FK exists yet on `identifiers`. Arm-row protection in exports is therefore IMPLICIT: identifiers attesting to arm canonicals would carry the arm's canonical name as TEXT, but with no identifier carrying an arm-canonical name in the current data shape, the visible-filter is a no-op against current export queries. CP31 codifies the hub-and-spoke columns as pre-stage for a future `identifiers.manufacturer_id` FK migration; when that lands, every export-path JOIN MUST re-establish the visible-filter as `WHERE m.query_default = 'visible' OR id.manufacturer_id = m.id`.

**Hub-arm precedent (v1.4.1 CP31).** Parrot SAS (id=25, hub; `primary_category='drone'`, `is_arm=0`, `query_default='visible'`) + Parrot Automotive (id=222, arm; `parent_manufacturer_id=25`, `is_arm=1`, `query_default='hidden_arm'`, `primary_category='automotive_telematics'`). Phase 7-bis 177-row §7.2 fccid.io cohort routes 2AG-attested rows to the arm id=222.

**Future arm-splits** (Honeywell ACS division, Cisco/Meraki, Motorola Solutions, Harris RF vs Harris Aerial) are backlogged for v1.4.2+ per evidence arrival; no urgency. CP31 ships schema + Parrot conversion only.

**Multi-arm admission cadence sub-rule (CP32 §4, 2026-05-21).** `hidden_arm` rows admit only when identifier-rows attest to specific arms — admission is **evidence-driven, not pre-emptive**. The backlog above (Cisco/Meraki, Motorola Solutions, Harris RF vs Harris Aerial, Honeywell ACS) does NOT auto-promote arm splits on a schedule; arm splits ship only when concrete identifier evidence surfaces attesting to a specific arm. CP31 shipped only Parrot because that was the only multi-arm case with concrete evidence (Parrot Faurecia Automotive S.A.S aliases on the existing Parrot id=25 row). Future arm splits follow the same evidence-driven cadence.

**Future `identifiers.manufacturer_id` FK migration (CP32 §2 — codified architectural binding).** When the future migration adds `identifiers.manufacturer_id INTEGER NULL REFERENCES manufacturers(id)`, every export-path JOIN MUST re-establish the visible-filter as `WHERE m.query_default = 'visible' OR id.manufacturer_id = m.id` per the canonical hub-and-spoke contract. CP32 §2 (2026-05-21) elevates this binding from CP31 carry-forward to first-class codified architectural commitment — migration-design proposals consuming `identifiers.manufacturer_id` MUST paste-not-cite this requirement in their dispatch §1. Status: BINDING only — FK migration target is v1.5.0+ (no v1.4.x migration consumes it; arm-row protection is implicit at v1.4.1 because no identifier row currently carries an arm-canonical manufacturer name).

**Downstream consumer audit (4 paths)** discipline codified at BIBLE_AMENDMENTS CP31 §3 — cross-referenced from `feedback_bible_amendment_downstream_consumer_audit`. Live-query hub-only lexicon enumeration sites (4 identified at MAC-199, commit `f9bcf22`) carry the `WHERE query_default = 'visible'` filter; export paths defer until future-FK migration lands.

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
- `first_seen` / `last_verified` — emitted in canonical timestamp format per the **CP22 sub-amend** below; CSV writer calls `_normalize_datetime()` against the underlying DB value before writing.

**CSV timestamp canonical format — CP22 (2026-05-14) directive.**

The `identifiers.first_seen` and `identifiers.last_verified` SQLite columns carry type `DATETIME` (typeless TEXT — no SQL-level format constraint), and historical write paths produced at least four distinct shapes across 22,532 rows: ISO-8601 with `Z`, ISO-8601 with explicit UTC offset (often with microseconds), space-separated `YYYY-MM-DD HH:MM:SS`, and date-only `YYYY-MM-DD`. The MAC-124 F6 smoke test (2026-05-14T22:17Z, board-authorized at MAC-124 [`330573f0`](/MAC/issues/MAC-124#comment-330573f0-97e5-40c5-9dcf-000af16c782e)) surfaced the resulting downstream-consumer impact: 53 of 103 Lynceus-recognized rows errored at `_parse_date` parse rather than importing.

**Canonical CSV emission format:** `"YYYY-MM-DDTHH:MM:SSZ"` (ISO-8601 UTC, `Z` suffix, seconds precision). Matches the precedent set by `_meta.exported_at` in the JSON exports (which already uses this form per `_utc_now_iso`). Microseconds are dropped at emission. Date-only DB rows project to `"YYYY-MM-DDT00:00:00Z"` (midnight UTC; preserves the only signal the row carries). Empty / `NULL` DB rows emit as the empty string `""`.

**Emission pipeline:** `db/validation/export_lynceus.py::_normalize_datetime(value)` is called against `row.first_seen` and `row.last_verified` immediately before `csv.DictWriter.writerow`. The helper is conservative: any value it cannot parse into one of the four accepted historical shapes raises `ValueError`, which surfaces as an export-time halt rather than silently producing a malformed CSV row (the F6 class of bug). A future write path emitting a fifth shape immediately fails the export rather than degrading the contract.

**Consumer-side disposition (Lynceus):** Lynceus's `_parse_date` is multi-format tolerant for backward compatibility with archived exports that pre-date the CP22 normalization landing — it accepts ISO-with-Z (canonical), ISO-with-offset, space-separated, and date-only in priority order. The defense-in-depth posture (Argus normalizes + Lynceus tolerates) lets archived pre-CP22 exports continue to import cleanly while new exports carry the canonical shape. Consumers building parsers against the v1.0+ contract should target the Z form per this directive.

**Companion §7.5-column shape-vs-format audit (CP22 surface; not fixed in this dispatch).** Authoring the CP22 timestamp normalization, the following adjacent §7.5 column shape questions surfaced as candidate findings — board may queue for future CPs as drift surfaces, none are ship-blocking for v1.0.0:

- **`identifier`** column normalization is type-specific per §4.4 but the CSV column itself has no canonical-form spec independent of identifier_type. SAR-10 hashing assumes the normalized form, so DB writes must already be canonical — but a CSV consumer that re-normalizes risks divergence. Codification candidate if a Lynceus-side normalization mismatch surfaces.
- **`manufacturer` / `model`** strings carry no codified casing / whitespace / Unicode normalization. Same vendor may surface as `"Apple"`, `"Apple Inc."`, `"APPLE"` across sources. Affects Lynceus operator-side `vendor_overrides.yaml` key matching (exact-string lookup per `import_argus.py::resolve_severity`). Codification candidate if vendor_override hit-rate complaints surface.
- **`source_url`** carries no scheme/trailing-slash/case canonicalization spec. Affects dedup if URL comparison is used as a key elsewhere.
- **`notes`** field carries heterogeneous structured content across CPs: facts-only basis citations (§11 #16), `upstream_license_posture` canonical key (CP21 + sid=41 MAC-118), and free-form prose. No JSON / structured-content parsing contract for downstream consumers. Codification candidate if a consumer parser ships against `notes` semantics.
- **`confidence`** range 0-100 is codified per §8.2 source-band rules but not restated in §7.5. Minor docs gap; format is structurally enforced via the §8.2 ladder and CP19 source_type exclusion.

These findings are surfaced now to bound the audit's scope; CP22 codifies the timestamp shape only. Future CPs may codify the others as drift surfaces.

**Behavioral-signatures sibling export — CP18 (2026-05-13) directive.**

Per Wave-B promotion-cycle-3 first-population of `behavioral_signatures` table at MAC-88 close (2026-05-13; 0 → 55 rows landed via MAC-91), behavioral_signatures rows export to a sibling file `argus_export_behavioral_signatures.json` rather than to the existing Lynceus-bound `argus_export.json` / `argus_export_high_confidence.json`. Justification: the §7.5 contract `{pattern, pattern_type, description, argus_record_id}` is wire-pattern-keyed by construction (per the §4.4 mapping); `behavioral_signatures` rows have no wire-pattern string (they're descriptive prose like "Identity Request" plus thresholded multi-message rules in `threshold_json`). The sibling file preserves the existing contract purity per the `argus_export.json` shape's load-bearing property while giving downstream consumers (Rayhunter) a stable schema-decoupled surface to read from rather than direct DB reads (direct reads couple consumers to schema; the CP14 migration 0010 design explicitly established `behavioral_signatures` as a canonical surface that downstream consumers should read from a stable contract).

**File shape (`argus_export_behavioral_signatures.json`):**

```json
{
  "_meta": {
    "argus_version": "<schema version>",
    "exported_at": "<ISO8601 UTC timestamp>",
    "record_count": 0,
    "confidence_threshold": 70,
    "argus_run_id": "<UUID for this export run>",
    "source_record_count": 0,
    "dropped_in_export": {
      "below_confidence_threshold": 0,
      "unknown_category": 0
    }
  },
  "entries": [
    {
      "signature_name": "<from behavioral_signatures.signature_name>",
      "cellular_generation": "<NULL or 2G|3G|4G|5G_NSA from behavioral_signatures.cellular_generation>",
      "threshold_json": <verbatim JSON value from behavioral_signatures.threshold_json>,
      "confidence": <integer 0-100>,
      "argus_record_id": "<16 hex chars: sha256('behavioral_signature|' + signature_name + '|' + source_id + '|' + cellular_generation_or_NULL_literal)[:16]>"
    }
  ]
}
```

**Field notes:**
- `confidence_threshold` is `70`, matching the canonical §7.5 high-confidence floor (per the codified floor-discipline; the academic-band §8.3 corroboration math lifts Marlin rows to 80, comfortably above the floor). Filters rows with `confidence < 70` per the floor rule. Consumer-side tighter filtering (e.g., Rayhunter limiting to conf ≥85 for strict-mode alerts) is operator-decided, not export-side gated.
- `argus_record_id` uses a behavioral_signatures-specific recipe: `sha256(f"behavioral_signature|{signature_name}|{source_id}|{cellular_generation if cellular_generation is not None else 'NULL'}").hexdigest()[:16]`. The 3-tuple UNIQUE constraint on `(signature_name, source_id, cellular_generation)` per CP14 migration 0010 makes this hash stable under re-extraction + dedup events (same stability property as SAR-10's `argus_record_id` for identifiers rows).
- `cellular_generation` exports as the scalar value (literal JSON `null`, `"2G"`, `"3G"`, `"4G"`, or `"5G_NSA"`). Path (b) cross-gen rows (scalar NULL with `cross_gen_membership` list in `threshold_json`) surface the cross-gen list via the `threshold_json` field — consumers read both fields.
- `threshold_json` exports verbatim from the DB (no transformation; both `json_valid()`-gated CHECK constraints prove the field is well-formed JSON at INSERT). Schema-stable enough that direct consumption is safe; CHECK-enum extension (5G_SA / 5G_FR1 / 5G_FR2) lands as a schema CHECK addition + this export file's enum docs update per the schema-migration-sibling discipline.
- `_meta.dropped_in_export` keys are smaller than `argus_export_high_confidence.json`'s 8-key set because the §4.4 wire-pattern-specific drop categories don't apply: behavioral_signatures don't have `ssid_pattern` / `device_fingerprint` / `oversized_mac_range` / `procurement_only` / `self_exclude_oui` / `geographic_scope_mismatch` patterns. Two keys suffice today: `below_confidence_threshold` (rows with conf < 70) + `unknown_category` (forward-proofing if Wave-C/D/E surfaces behavioral_signatures with `device_category='unknown'`; behavioral_signatures inherit the same §11 #13 unknown-category Lynceus carveout per the table's `device_category` enum reuse). Future drop categories add keys per the same coverage-report reconciliation arithmetic.
- The coverage report (§9 item 9) reconciliation arithmetic extends to this export file: `source_record_count − sum(dropped_in_export) = entries.length`.
- **Severity intentionally absent** matching the parent `argus_export_high_confidence.json`'s CP8 architecture. Severity is operator-side (Rayhunter / Lynceus consumer-side filtering via consumer-specific override files).

**Why the file is a sibling, not a discriminated-union extension to existing JSONs:**

Three alternatives were considered at MAC-88 surface-back; board selected the sibling-file approach over (1) status-quo "Rayhunter reads the table directly via TBD path" — which punts on the consumer integration problem and couples Rayhunter to schema, and (3) discriminated-union `entry_kind` field on the existing high-conf JSON — which is discouraged because the `{pattern, pattern_type, description, argus_record_id}` contract is load-bearing for §4.4 mapping consumers and shouldn't degrade to "may have shape X or shape Y depending on entry." The sibling file preserves contract purity AND gives Rayhunter a stable surface AND lets each export's `_meta` block carry its own reconciliation arithmetic without cross-file aggregation.

**High-confidence export source_type exclusion — CP19 (2026-05-14) directive.**

Beyond the ≥70 confidence floor codified at §7.5 + `feedback_high_confidence_export_floor.md`, `argus_export_high_confidence.json` excludes rows by `source_type` regardless of confidence value:

- `inferred` source_type — excluded from high-conf export
- `crowdsourced` source_type — excluded from high-conf export

Rationale: "high confidence" semantics couple to band-meaning (provenance strength), not just confidence-value-meaning. The `crowdsourced` ceiling is 75 per §8.2 (still ≥70 floor); the `inferred` ceiling is 70 (right at floor). Allowing rows in high-conf at 75 or 70 from those bands conflates band-strength with confidence-value. The CP19 exclusion makes high-conf export semantically "rows from official / regulatory / primary_registry / manufacturer_doc / academic / foia / procurement / manufacturer_app source_types AND confidence ≥ 70 AND device_category != 'unknown' AND geographic_scope passes CP7".

Standard export (`argus_export.json`) retains the existing ≥30 floor without source_type exclusion; CSV (`argus_export.csv`) is unfiltered per CP11. The behavioral_signatures sibling export (`argus_export_behavioral_signatures.json`) retains the CP18 ≥70 floor; CP19 source_type exclusion does not apply to behavioral_signatures (which have a distinct shape).

`_meta.dropped_in_export` gains a new key `excluded_source_type` capturing the count of rows dropped by this filter (parallel to the existing 8-key `dropped_in_export` block in §7.5).

First effect: MAC-88 CP19 sweep landing 335 Scope 2 downgrades from primary_registry → crowdsourced (which would otherwise stay in high-conf at conf=75 under the ≥70 floor alone) and dropping them out of high-conf.

**Don'ts:**
- Do not include the `raw_observations` table in exports
- Do not include `superseded_by` pointers in exports (resolve them first; cf. §4.1 tri-state semantic codified at CP32 §9)
- Do not export records with `confidence < 30` to any Lynceus export file. The floor for `argus_export.json` is `confidence ≥ 30`; the threshold for `argus_export_high_confidence.json` is `confidence ≥ 70`. Records below 30 are tallied as `below_confidence_threshold` in the coverage report.
- Do not export records with `device_category='unknown'` to Lynceus under any confidence threshold (see §8.4 and §11 #13)
- Do not export procurement-only records (no concrete identifier) to Lynceus (see §4.5 and §11 #14)
- Do not include OUIs from the Pi self-exclude list (§8.4) in `argus_export_high_confidence.json`
- Do not include `behavioral_signatures` rows in the Lynceus-bound exports (`argus_export.json` / `argus_export_high_confidence.json` / `argus_export.csv`). They export to the sibling file `argus_export_behavioral_signatures.json` per the CP18 directive above. Mixing them into the wire-pattern-keyed Lynceus exports would violate the load-bearing `{pattern, pattern_type, description, argus_record_id}` contract.
- Do not include records with `source_type IN ('inferred', 'crowdsourced')` in `argus_export_high_confidence.json`. Per CP19 (2026-05-14), high-conf export couples band-meaning to confidence-value-meaning; rows from those bands stay in standard export but not high-conf, tallied as `excluded_source_type` in coverage report. (Note this is orthogonal to but complementary with §11 #13 unknown-category exclusion.)

**Lynceus exports regen cadence sub-rule (CP32 §5, 2026-05-21).** `argus_export.csv` + `argus_export.json` + `argus_export_high_confidence.json` regenerate **per v1.4.x bundle**, not per data-touching commit. The per-bundle cadence avoids export-noise commits between substantive bundle landings; consumers can rely on a stable export shape that tracks the canonical-DB bundle close (not a moving target across mid-bundle micro-commits). Ship-prep at bundle close MUST include a final exports regen against the canonical DB; mid-bundle data commits do NOT trigger regen. Surfaced at [MAC-209](/MAC/issues/MAC-209) Phase 12.

**Drop-attribution rule sub-rule (CP32 §8, 2026-05-21).** Drop attributions in `_meta.dropped_in_export` carry a specific rule reference (e.g., `§4.4 type-mapping gate` vs `§8.2/CP19 crowdsourced-ceiling` vs `§11 #12 Pi OUI ban` vs `§11 #13 unknown-category` vs `§11 #14 procurement-only` vs `CP7 geographic_scope`). When a dispatch asserts "rows X drop from Lynceus export because of mechanism Y," it MUST cite the actual drop tally bucket in `_meta.dropped_in_export.*` and confirm via DB-query that the row's `source_type` + `identifier_type` + `confidence` align with mechanism Y's predicate, before baking the assertion into acceptance criteria. The discipline composes with `[[feedback_db_verify_dispatch_claims]]`; it flags Lynceus-export drop mechanisms specifically because they have **multiple superficially-applicable predicates** and the wrong attribution surfaces only at export-time spot-check, not at promotion-time. Canonical case study: MAC-209 spot-check found the MAC-206 dispatch's CP19 §8.2 crowdsourced-ceiling reasoning was wrong; the 21 carve-out rows actually drop via the §4.4 type-mapping gate (`source_type='manufacturer_app'`, not crowdsourced).

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

**Strict-reading acknowledgment (CP21 — 2026-05-14, MAC-116 §2.3(d) finding):** when historical assertions (CP19-prep notes, pre-CP15 dispatch projections, etc.) place a source in `regulatory` band but CP15 §8.2 strict reading produces `primary_registry`, the CP15 strict reading governs. Specifically: a source qualifies as `primary_registry` if it IS the issuance-of-record for the identifier values it publishes (e.g., IEEE OUI MA-L/MA-M/MA-S, FCC EAS Equipment Authorization grantee registrations, Bluetooth SIG company-identifier registry, FAA UAS Remote-ID Public DOC API DETAIL endpoint). Sources 1/2/3/7 carry historic `source_type='regulatory'` metadata in the `sources` table that pre-dates CP15's codification; the identifier-row data for ~70,000+ identifiers from these sources is already correctly labeled `source_type='primary_registry'` post-CP19 sweep + post-MAC-101 normalization. Sources-row metadata cleanup queued for single-purpose post-ship work per CEO recommendation + board ratification at MAC-101 [`dd7bd55c`](/MAC/issues/MAC-101#comment-dd7bd55c) (not ship-blocking; identifier-row data correctly labeled; exports unaffected). Surfaced at MAC-116 §2.3(d) sub-item finding (sources.id=7 FCC EAS direction-reversal: dispatch projected `regulatory`, strict reading produces `primary_registry`).

**Composition with §8.4 lenses (CP14 cross-references):**

- **G-1 protocol-container OUI lens.** SDO-assigned OUIs (`FA:0B:BC` ASD-STAN, `50:6F:9A` Wi-Fi Alliance) classify as `primary_registry` when sourced from the SDO's own registry, and as `crowdsourced` when sourced from a community repo citing the SDO. CP15 + G-1 compose: protocol-container lens governs `device_category` semantics; `primary_registry` band governs confidence.
- **G-3 `ble_manufacturer_id`.** SIG-assigned values like `0x004C` Apple + `0x09C8` XUNTONG are `primary_registry` when sourced from the SIG company-identifier registry. Wave-A community-repo citations remain `crowdsourced` 50–75; SIG-registry direct citation lifts to `primary_registry` 70–85.
- **G-7 `paired_identifier_id` + `pair_kind`.** Independent. Pairing discipline operates on identifier structure (LA-bit flip, vendor-as-container, firmware-generation); source-band classification is orthogonal.
- **G-9 `drone_id_prefix`.** FAA RID is the canonical `primary_registry` case driving CP15. The 481-row FAA RID batch HELD from Phase-4 promotion-cycle-1 promotes at confidence 85 per `primary_registry` single-source rule once CP15 ratifies.

**`manufacturer_app` sub-banding** (added Correction Pass 12 for Wave G — Phase 6 vendor companion app static analysis; expanded Correction Pass 17 with operator-vs-installer cohort distinction + `vendor_template_namespace_uuid` sub-class + product-family field formalization + SAR-11 codification reference update). The 60–95 outer band breaks down per identifier class, because vendor apps yield different attestation strength per class — and per cohort, because operator-facing apps and installer/pairing-flow apps yield structurally different identifier types.

**Cohort distinction (CP17 — Wave G macro thesis).** Vendor companion apps fall into two cohorts that yield different identifier shapes:

- **Operator-facing cohort** (pilot/control/monitor/dashboard/viewer apps used by the end operator). Yields **product-family taxonomy only** — marketing names, internal codenames, device-type enums for the operator's own equipment. Does NOT typically yield BLE service UUIDs, SSID patterns, or default credentials — those identifiers live on the device side and are not surfaced to the operator-facing app. Wave G evidence: 8 operator/pilot apps surveyed yielded 0 BLE UUIDs.
- **Installer / pairing-flow / technician cohort** (technician-facing setup apps, pairing flows, factory-mode tools). Yields **BLE service UUIDs + default SSID patterns + default credential strings + product-family taxonomy** — the full identifier set because pairing requires the installer app to know the device-side identifier values. Wave G evidence: 2 installer/pairing apps (Flock FS Installer + Getac BWC Viewer) yielded 6 unique vendor BLE UUIDs + complete DeviceType taxonomy.

ExtractionWorker queue ordering should prioritize the installer/pairing-flow cohort for non-product-family identifiers; operator-facing cohort processing produces product-family yield only.

| Identifier class extracted from vendor app | Sub-band | Rationale | Typical cohort |
|---|---|---|---|
| Hardcoded BLE service UUID (128-bit or 16-bit-in-context) | 80–95 | BLE specs require service UUID for discovery; vendor app must contain the canonical value. Highest tier. | installer/pairing |
| `vendor_template_namespace_uuid` (vendor-specific UUID-suffix template; see CP17 sub-amend below) | 75–90 | Vendor-chosen UUID-suffix namespace (e.g., Getac's `-1b7f-430ea194e6cf` suffix). Pattern observation: Validator can enumerate additional vendor UUIDs by walking short-IDs at this template's prefix once the suffix is identified. Below hardcoded-BLE-service tier because individual values are inferred-by-pattern rather than directly attested. | installer/pairing |
| Default SSID pattern (vendor-prefix WiFi name) | 70–85 | Clear vendor attestation in code; hardware match TBV at scan time. | installer/pairing |
| Default credential string (plaintext) | 60–80 | Vendor-attested at app version, but firmware may have rotated. Encoded/hashed values dropped (require runtime analysis). | installer/pairing |
| MAC OUI from validation code path | 75–90 | Confirms OUI assignment; cross-checks against IEEE Tier-1 registry. Disagreement → manual flag. | installer/pairing (validation paths are typically installer-side) |
| Product-family taxonomy — `marketing_name` (e.g., "Mavic Pro", "Inspire 2") | 90–95 | Vendor's own marketing product naming inside their own app is near-canonical. | both cohorts |
| Product-family taxonomy — `internal_codename` (e.g., Flock `AVICORE` / `FALCON` / `RAVEN`; DJI internal SKU codes) | 90–95 | Engineering-internal naming surfacing in app code (tracking analytics, debug paths, telemetry tags). Often more stable than marketing names across product revs. | both cohorts |
| Product-family taxonomy — `device_type_enum_value` (e.g., Flock `DeviceType.CONDOR` / `DeviceType.DRONEDOCKINGSTATION` / `DeviceType.PICARDPTZ`) | 90–95 | Authoritative product-family taxonomy from vendor's own enum declaration in app code. Highest specificity tier of product-family identifiers; primarily feeds aliases / inference candidates. | both cohorts |

**`vendor_template_namespace_uuid` sub-class** (CP17 sub-amend (b); Wave G evidence base). When a vendor's BLE UUIDs share a common non-standard suffix (e.g., Getac's `00000000-0000-1000-1b7f-430ea194e6cf` + `0000200b-0000-1000-1b7f-430ea194e6cf` both share `-1b7f-430ea194e6cf`), the suffix represents the vendor's UUID-namespace allocation. ExtractionWorker should:

1. Identify the template via cross-UUID suffix-match (≥2 UUIDs in the vendor's app sharing identical 12+ hex-char suffix).
2. Stage the template as a candidate `identifier_type='vendor_template_namespace_uuid'` row with `identifier=<suffix>` at confidence midpoint of 75–90 sub-band.
3. Stage individual UUID values matching the template at the standard hardcoded-BLE-service tier (80–95) per the existing rule — the template-namespace and individual-value rows compose, not exclude.
4. At Validator-promotion time, the template row enables short-ID-walking inference (test additional UUIDs at the same template prefix against on-device probes) without requiring binary-decompile evidence for each.

The Getac BWC Viewer 2-UUID pattern (Wave G HB56 deliverable) is the canonical evidence base. Future Wave G' / iOS surfaces may broaden the evidence base; SAR-11 candidate-FP-class enumeration applies to `vendor_template_namespace_uuid` extracts as it does to other UUID candidates.

Default per-row confidence at extraction time = midpoint of the relevant sub-band. SAR-7 / SAR-8 / SAR-9 corroboration adjusts up; framework-string proximity, single-app-only surfacing, or cross-vendor-default appearance adjusts down. **SAR-11 (ratified at Correction Pass 17, 2026-05-13)** handles framework-UUID and third-party-BLE-library FP classes per the chunked Priority A/B/C/D structure documented at BIBLE_AMENDMENTS.md SAR-11. §8.4 strict-promotion rule (≥80) applies as written.

**fccid.io source-band re-attestation (CP31 — paste-not-cite from CP15).** fccid.io (sid=51) is `crowdsourced` per the §8.2 table above; single-source ceiling stays at **conf=75** per CP15. The Phase 7-bis 177-row §7.2 fccid.io cohort (re-dispatched post-CP31 + MAC-196 Numerex close at `1344f5d`) lands at conf=75 per row. §8.3 corroboration lift requires a non-fccid independent source per CP24 cross-source independence. No band drift, no special-case lift for fccid.io shape — the crowdsourced ceiling holds.

### 8.3 Dedup logic

Two records are duplicates if:
- Identical normalized `identifier` AND `identifier_type`, OR
- One record's identifier is a strict subset of the other (e.g., MAC within an OUI range)

On dedup:
- Keep the record with highest confidence as canonical
- Append all `source_url`s and `source_excerpt`s into the canonical record's notes
- Mark the other record `superseded_by = canonical.id`
- Recompute confidence: `min(99, max(originals) + 5)` for corroboration bonus

**Vendor-matching alias-aware-join discipline (Correction Pass 23 — cycle-3 §1 finding #4).** Cross-validation queries against `procurement_records` MUST use the `vendor_canonical_normalized` join key (materialized at migration 0021) OR an alias-aware JOIN against `manufacturers.canonical_name` + `manufacturers.aliases`. Direct equality on `vendor_canonical_name` misses legitimate matches because the column carries upstream USAspending verbatim recipient names with vendor-side inconsistency across awards. Preferred query pattern:

```sql
-- Pre-computed normalized join (cheapest at 43k+ row scale)
SELECT p.*
FROM procurement_records p
JOIN manufacturers m
  ON p.vendor_canonical_normalized = LOWER(m.canonical_name)
   OR m.aliases LIKE '%' || p.vendor_canonical_normalized || '%'
WHERE m.canonical_name = ?;
```

Live collapse evidence (post-backfill): 1,157 distinct raw vendor_canonical_name values → 1,141 distinct normalized values (0.9862 collapse ratio); top alias-collapse wins include `motorola solutions` (3 raw variants), `cellebrite` / `dedrone defense` / `engility` / `general dynamics information technology` (2 raw variants each).

**Short-vendor-name disambiguation discipline (Correction Pass 23 — cycle-4 §1 finding #6 — Berla collision).** Short vendor names (≤6 chars or single-word) in text-pattern-matching sources without entity disambiguation produce false-positive STRONG matches against unrelated cases with overlapping vocabulary. Case study: "Berla Kay Strong v. Thomas Wesley Strong" is a family-court matter where "Berla" is a given name, NOT the digital-forensics vendor; CourtListener's BM25 search returned the case as a STRONG match for vendor `Berla`. Future text-pattern-source runguides MUST bake disambiguation into §4 match scoring rather than punting to integration-time review. Disambiguation options (apply at extraction time, NOT integration time):

1. **Co-occurrence filter** — require the matched query token to appear alongside another known vendor-specific token (product family name, industry term) within N words
2. **Entity-type tagging** — if the source exposes party-role metadata (defendant vs plaintiff; corporate vs natural-person), filter to corporate-party-only matches
3. **Operator review of WEAK/STRONG candidates** for short vendor names (≤6 chars or single-word) before promotion — non-default; reserved for cases where (1) + (2) are not available

The discipline composes with §8.4 (multi-purpose vendor categorization restraint): short-name false positives are an extraction-time concern; multi-purpose-vendor categorization restraint is a promotion-time concern. Both gate against premature confidence-band assignment.

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
   - `argus_export_behavioral_signatures.json` (Rayhunter-consumable sibling export per CP18; confidence ≥70; shape per §7.5 CP18 directive; behavioral_signatures table rows only)
   - `coverage_report.md`

   Each Lynceus-consumable JSON file conforms to the schema in §7.5 (including the §4.4 type mapping, §4.5 severity derivation, and the description-format constraints). Each is independently parseable and includes a complete `_meta` block. `argus_export_behavioral_signatures.json` conforms to the §7.5 CP18 sibling-export shape and reconciles independently of the Lynceus-bound files.
3. `coverage_report.md` exists and shows category coverage with honest gap analysis
4. Every record in the main table has a working source_url
5. The validator has run a final pass and `conflicts` table is empty (or every entry is human-resolved)
6. The `argus_cli.py` utility works for `status`, `query`, `export`, `validate`
7. README.md at the project root describes: what the database is, how to consume the export, the schema, the confidence scoring, the limitations, and the legal/ethical scope (§2.2 + §11)

9. Coverage report includes a "Dropped from Lynceus export" section tallying records held back by category: `unknown_category`, `ssid_pattern`, `device_fingerprint`, `oversized_mac_range`, `procurement_only`, `self_exclude_oui`, `below_confidence_threshold`. Tallies must sum correctly: `source_record_count − sum(dropped) = exported entries count` for each Lynceus-bound JSON file (matching the `_meta.dropped_in_export` block defined in §7.5). The coverage report ALSO includes a "Behavioral-signatures export reconciliation" section (added CP18) tallying `behavioral_signatures` source-record count − `below_confidence_threshold` − `unknown_category` = `argus_export_behavioral_signatures.json` `entries` count, matching the `_meta.dropped_in_export` two-key block defined in §7.5 CP18.

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
    - **CP19 sub-rule (2026-05-14):** Row-level reclassifications of `identifiers` rows — band changes (`source_type` UPDATE), confidence changes (UP or DOWN), or `source_url` upgrade/downgrade per §11 #8 strict reading — MUST land an entry in the `source_reclassifications` audit table (per §4.2 + migration 0017) in the SAME transaction as the identifier-row UPDATE. The audit entry captures the pre/post state snapshot + substantive per-row rationale (convention: self-explanatory at row-level without cross-referencing the dispatch) + `sweep_event_id` grouping + CP/dispatch citation anchor. The audit table is forensic: it answers "show me every identifier ever reclassified, when, why, and by which sweep" as an O(1) query, eliminating reliance on git-archaeology for this discipline-class question.
    - **CP24 sub-rule (2026-05-17) — within-source re-extraction is not "second independent source".** The §8.3 corroboration formula `min(99, max(originals) + 5)` and the §8.2 "two independent sources" example BOTH assume that the corroborating source is genuinely independent of the originating source. Re-querying the same upstream registry at two different times (e.g., USAspending v1.0.0 admission `20260504T154706Z` + deep-extension session `20260516T...`) is **not** a "second independent source" for §8.3 lift purposes. Such re-extraction validates extraction-time fidelity, coverage breadth (wider filter windows surface rows the first pass excluded), and upstream-record persistence — all genuinely useful provenance signals. It does **not** validate the §11 #8 cardinal test that an *independent collector observed the same fact via different methodology*. Discipline going forward: merge new evidence rows into `notes.corroborations[]` and tag the session in `notes.corroboration_sessions[]` (these stay; pure provenance enrichment), but confidence stays at the original source-band ceiling. Lift requires a genuinely independent collector — different upstream registry, different methodology — e.g., FCC EAS test report corroborating a USAspending procurement record; FOIA-released contract corroborating a SAM.gov record; SEC EDGAR disclosure corroborating a USAspending award (the canonical cross-source case at MAC-172 id=86738 SoundThinking × DHS USSS). Case study: MAC-172 P4 ingest surfaced this gap on the 180-row USAspending corroboration uplift at HEAD `4a3f6dd`; rolled back to 85 with per-row `notes.confidence_history[]` audit at the CP24 commit landing.
    - **CP24 sub-rule (2026-05-17) — `procurement_records` row-level confidence audit-trail (CP19 spirit-extension).** When a `procurement_records` row's `confidence` field changes (UP or DOWN) outside of initial INSERT, the row's `notes` JSON MUST gain an entry in `notes.confidence_history[]` capturing `{at_utc, from, to, rationale, dispatch, cp_anchor}` in the same transaction as the UPDATE. The CP19 literal wording is `identifiers`-scoped (binds the dedicated `source_reclassifications` audit table); CP24 carries the same forensic answer ("when, why, by which dispatch") to `procurement_records` via a row-local notes-array convention rather than a parallel audit table. Rationale: at the current ~46k-row scale, row-local audit-on-notes is cheaper than schema migration; if forensic-query patterns later demand it (e.g., "show every procurement_records row reclassified by dispatch X" at sub-millisecond latency), the audit array promotes to a `procurement_reclassifications` table mirroring `source_reclassifications` shape — but that is a future-CP decision, not a CP24-time obligation. The notes-array form is canonical for now.
    - **CP24 sub-rule (2026-05-17) — citation hygiene: "§5.2 +5 boost" is a miscite of the bible.** `PROJECT_BIBLE.md` §5 is "Source Catalog" with Tier subsections; there is no §5.2 in the bible. The +5 corroboration formula lives in §8.3 (dedup logic); the independence prerequisite lives in §11 #8 + §8.2. Future handoffs, runguides, and dispatch templates MUST cite **§8.3 + §11 #8** for the corroboration-lift rule. Strike "§5.2 +5 boost" wording from downstream artifacts on next touch. Operational impact of the past miscite is zero (the rule meant is unambiguous in context), but a future reader chasing "§5.2" would not find it. **METHODOLOGY.md** maintains its own internal numbering with a "§5.2 Corroboration boost — multi-source dedup" heading (METHODOLOGY-document-internal, not a bible citation); those references remain valid as cross-document internal anchors within METHODOLOGY's structure. The bible's canonical citations are §8.3 + §11 #8 across all forward dispatch/runguide/handoff prose.
9. **Do not skip checkpoints.** Even if a phase looks easy, stop and report.
10. **Do not categorize at the OUI level for multi-purpose vendors** (see §8.4). *(Reframed by CP10 (2026-05-07): narrow-read carve-out — Argus-side categorization of single-product-line §2.1 vendors whose entire product line falls within the canonical surveillance category is permitted, regardless of whether the vendor also makes consumer/commercial variants of that category. FP-suppression for multi-purpose vendors is delegated to the Lynceus operator-override layer (`severity_overrides.yaml`), not Argus-side gatekeeping. Argus ships factual vendor-attribution; Lynceus operators tune alert behavior per their threat model. See CP10 in BIBLE_AMENDMENTS.md for the 17-row v0.1 cutover slate and the operator-override-as-FP-layer architecture.)*
11. **Do not skip the `BIBLE_AMENDMENTS.md` log entry when making in-place bible edits or adding sub-agent-level rules.** The git diff is the source of truth, but the amendment log is the human-readable trail. An undocumented amendment is a process violation regardless of whether the edit itself is correct.
    - **CP36 (2026-05-24, MAC-251) — `identifiers.source_type` CHECK enum parity with `sources.source_type` (mig-0029) + 116-row J-5 proxy relabel.** Migration `0029_cp36_identifiers_source_type_enum_parity.sql` extends the `identifiers.source_type` CHECK enum +3 (`judicial_filing`, `disclosure_filing`, `procurement_disclosure`; 10 → 13 cumulative) to close the CP23 / mig-0020 parity gap surfaced at MAC-249 Phase G Validator CPN-A. Sibling script `0029_cp36_j5_proxy_relabel.sql` relabels 116 J-5 (CourtListener RECAP, sid=48) rows from `source_type='foia'` (§8.2 band-bucket proxy at MAC-250 Phase H) to canonical `source_type='judicial_filing'`; `notes.cpn_a_proxy_relabel` sentinel-key block preserves proxy-history audit trail per §11 #17. Confidence column untouched (§11 #8 invariant — all 116 rows stay at `confidence=75`). CP-slot ratified as CP36 (not CP35; CP35 remains reserved for the standing NDPP §4.4 Lynceus mapping draft entry) at MAC-251 wake comment `cb228e69-2c07-4062-9e92-06009f9f9c48`. See `BIBLE_AMENDMENTS.md` §"Correction Pass 36" for full entry.
12. **Operator-stack self-exclude.** Argus operator-side hardware MUST NOT appear in the Lynceus high-confidence export. This covers (a) **Lynceus host hardware** — Raspberry Pi OUIs as enumerated in §8.4 Pi self-exclude bullet; and (b) **Defensive-tool hardware** — Rayhunter-supported modems as enumerated in §8.4 defensive-tool self-exclude bullet, including the CEO's Orbic RC400L (USB VID:PID `05c6:f601`/`f626`/`f622`) and the broader supported-modem family (FY UZ801, PinePhone Quectel, Wingtech CT2MHS01, T-Mobile TMOHS1, TP-Link M7350/M7310). The exclusion is mandatory regardless of source confidence. Standard-export inclusion at `severity='low'` is permitted and documented per §8.4. (CP14 — G-15 expansion of original Pi-only rule.)
13. **Do not export records with `device_category='unknown'` to Lynceus** under any confidence level. They remain canonical-only (see §8.4).
14. **Do not export procurement-only records (no concrete identifier) to Lynceus.** Procurement records establish vendor-agency relationships, not device presence. They are analytical only (see §4.5).
15. **Do not commit decompiled vendor app source code, raw APK/IPA contents, or extracted decompile artifacts to the git index.** (Added Correction Pass 12, Wave G — Phase 6 license-posture confirmation per board direction 2026-05-08.) Raw APK/IPA binaries land at `raw/vendor_apps/<vendor>/<app_package_id>/<version>/<sha256>.{apk,ipa}` for provenance only and are gitignored. Decompiled `.java` / smali / dumped Mach-O headers live in workspace-only scratch directories during ExtractionWorker runs and are cleaned at end of run. Only extracted identifier *candidates* (value + relative file path within the decompile output) land in `raw_observations`. The git index never contains vendor-proprietary source. (See §11 #2 — this rule operationalizes the access/license posture for the vendor companion app corpus, mirroring the §1201 + §201.40(b) reverse-engineering exemption boundary: research is permitted, redistribution of decompiled source is not.)
16. **Public-but-unlicensed-source facts-only promotion.** When a public source (community GitHub repo, blog, forum) lacks an explicit license declaration (a `NO_LICENSE_DECLARED` sentinel or the absence of a `LICENSE` file), Argus MAY extract and promote *factual claims* (identifier values, manufacturer attributions, operational context) under the *Feist v. Rural Telephone Service* (499 U.S. 340 (1991)) facts-not-copyrightable doctrine. Argus MUST NOT redistribute the *compilation arrangement* (copying a list-snippet verbatim into `source_excerpt`, mirroring repository structure, or reproducing the source's selection/organization beyond what a single-fact citation requires). Per-row provenance discipline: `source_url` cites the upstream file at a pinned commit (per §11 #1); `source_excerpt` captures the minimal factual context needed for audit (typically the identifier value plus a single-sentence Argus-authored operational note); `notes.upstream_license_posture` records the source's declared posture (`'NO_LICENSE_DECLARED'`, `'MIT'`, etc.) for audit trail. Confidence ceiling follows §8.2 source-band rules (community = `crowdsourced` 50-75; ratification-required cases default to ≤70). This rule composes with §11 #2 (no non-public data — `NO_LICENSE_DECLARED` public repos remain public, so §11 #2 is satisfied) and §11 #15 (no decompiled vendor app source committed — applies orthogonally to any source class).
    - **Composition with migration 0016 `LICENSE` column on `deployment_observations` (CP21 — 2026-05-14, MAC-101 §2.1(b)):** Argus carries license posture at three structurally-distinct layers, each serving a different consumer-side concern. Downstream consumers (Lynceus / Rayhunter / future) handle these layers independently:
        - **Layer 1 — `sources.notes.license_posture`** (per-source declaration). Examples: sources 5 (`'CC-BY-NC-SA-4.0'`), 6 (`'ODbL-1.0'`), 38 (`'AGPL-3.0_inherited_from_upstream_id_20'`), 39 + 42 (`'NO_LICENSE_DECLARED_flagged_for_validator'`). This is the canonical license-posture surface for license-DATA prose authoring and for Validator promotion-time gates.
        - **Layer 2 — `deployment_observations.LICENSE` (migration 0016 column, NOT NULL).** Per-row LICENSE tag on deployment-observation rows; carries the upstream source's license verbatim (e.g., `'CC-BY-NC-SA-4.0'` for Atlas of Surveillance rows = sid=5 = 15,071 rows; `'ODbL-1.0'` for DeFlock rows = sid=6 = 101,597 rows). §11 #16 NO_LICENSE_DECLARED sources do NOT currently feed `deployment_observations` (sids 39 + 42 have zero deployment_obs rows; their content lands in `raw_observations` and promotes to `identifiers`). If a future §11 #16 source ever populates `deployment_observations`, the LICENSE column receives the literal `'NO_LICENSE_DECLARED'` value (NOT NULL satisfied; downstream consumers handle the sentinel per their own policy).
        - **Layer 3 — `identifiers.notes.upstream_license_posture`** (canonical sentinel key per Validator MAC-118 F1 + CEO ratification at MAC-118 [`7547e0d6`](/MAC/issues/MAC-118#comment-7547e0d6-1d2a-4c65-bc3e-1307344e3041)). When a §11 #16 source promotes an identifier, the identifier row carries the sentinel at this key (e.g., `notes.upstream_license_posture='NO_LICENSE_DECLARED'`). Both forms `notes.upstream_license_posture='NO_LICENSE_DECLARED'` and the equivalent `notes.facts_only_basis='§11 #16 Feist facts-only promotion (NO_LICENSE_DECLARED / public-but-unlicensed)'` are grep-target-clean and §11 #16-compliant; the canonical form is `upstream_license_posture` (more discoverable; literal posture-value semantics). The `facts_only_basis` form is preserved on extant rows (no rewrite) but new promotions land on the canonical form. The `identifiers` table does not have a top-level `LICENSE` column today — per-row license posture lives in `notes`. A future migration could lift `upstream_license_posture` to a top-level column if downstream consumer pressure warrants; absent that, the notes-key form is canonical.
    - **Downstream consumer guidance.** §11 #16 facts-only promotions flow to `argus_export.json` (standard) and `argus_export.csv` per the standard export discipline. Per CP19 + §7.5, they are EXCLUDED from `argus_export_high_confidence.json` because §11 #16 promotions are `source_type='crowdsourced'` by §8.2 ceiling-rule, and CP19 high-conf export excludes crowdsourced rows regardless of `confidence` band. This is the intended behavior: high-conf exports couple band-meaning to confidence-value-meaning, and §11 #16 facts-only rows are band-bounded crowdsourced even when their confidence ceiling reaches 70. Consumers wanting the broader (CP19-inclusive) view read `argus_export.json` (standard) or `argus_export.csv`. The CSV consumer-side filter `WHERE notes_json.upstream_license_posture='NO_LICENSE_DECLARED'` selects §11 #16 rows for downstream license-aware processing if needed.
    - **Canonical sentinel-key shape (CP21 — 2026-05-14, MAC-118 F1):** the canonical per-promoted-identifier sentinel key is **`notes.upstream_license_posture`** (the value is the license-posture string — `'NO_LICENSE_DECLARED'`, `'MIT'`, `'AGPL-3.0_declared'`, `'AGPL-3.0_inherited_from_upstream_id_<N>'`, `'CC-BY-NC-ND-4.0_with_research_use_clause'`, etc.). Rationale (per MAC-118 F1 CEO ratification at MAC-118 [`b012ac69`](/MAC/issues/MAC-118#comment-b012ac69-…) + board ratification at MAC-101 [`e246a32a`](/MAC/issues/MAC-101#comment-e246a32a-5a28-467d-b20e-72901a5a3d88)): more discoverable than alt-keys; alphabetically first in `notes` dict serializations; literal posture-value semantics. The alt-key form `notes.facts_only_basis='§11 #16 Feist facts-only promotion (NO_LICENSE_DECLARED / …)'` (used on 8 sid=42 promotions pre-canonicalization) is grep-target-clean and §11 #16-compliant; extant rows preserved verbatim under the both-forms-compliant rule. **New §11 #16 promotions (post-CP21) MUST use the canonical `notes.upstream_license_posture` key.** Both Phase-1 mappers and Validator-side promotion paths converge on the canonical form. No migration; no DB rewrite of extant rows; canonical-form convergence applies forward-only. (CP20 — 2026-05-14; composition addendum + canonical sentinel-key sub-rule CP21 — 2026-05-14.)
17. **Direct-admission carve-out (wave_g_pre_v1, 21 rows; session-bounded historical exception, NOT a future admission pathway).** The canonical promotion pipeline is `extraction_runs → raw_observations → identifiers`. **Audit invariant (amended):** Every `identifiers` row has a `raw_observations` predecessor **OR** carries `notes.direct_admission_carve_out=true` referencing its `sources.notes`-level provenance. The carve-out is **session-bounded** — currently limited to `session_admission='wave_g_pre_v1'` (sids 13, 14; 21 rows enumerated at [MAC-205](/MAC/issues/MAC-205), all carved at [MAC-206](/MAC/issues/MAC-206) Phase 10d with `notes.carve_out_audit.sweep_event_id='mac206_wave_g_carveout_2026_05_20'`) — and **not a future admission pathway**. New admissions MUST route through the canonical pipeline. Wave_g_pre_v1's intentionality is anchored at `sources.notes.mac_55_step_2_run='pre-auth 3 mechanical promotion 2026-05-11'` and `sources.notes.authority_chain='MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c (migration 0009 manufacturer_app enum)'`; the canonical pipeline applies to all 16 apkpure-sourced identifiers admitted *outside* wave_g_pre_v1 (e.g., ids 23043–23058: Hikvision, Dahua, Motorola Solutions, Parrot), which DO carry `raw_observations` predecessors per the canonical contract. (CP32 §6 — codified; see BIBLE_AMENDMENTS.md.)
    - **Applicability scope (added 2026-05-20 alongside the carve-out clause):** This invariant applies to `identifiers.notes` payloads that *intend* to carry structured JSON metadata (the post-CP12 convention). Two classes of rows are excluded from the JSON-validity precondition of the invariant:
        1. **Out-of-scope by era's convention.** 106 `identifiers` rows carrying `Phase-5 Step-4 follow-on² (MAC-44)`-era markdown rationales; 21 `sources` rows carrying MAC-63 Wave-A repo-registration template strings; ~52,501 `raw_observations` rows on sids 1, 2, 3 (FCC/IEEE bulk-ingest) where `notes` is used as a free-form address field. These rows are correct as written; **no backfill is required or authorized** — future migrations MUST NOT JSON-ify them.
        2. **Deferred intended-JSON repair.** 5 `identifiers` rows (ids 554-558, RAVEN_* services) and 1 `sources` row (sid=7), all carrying `{json}<concat>text` truncation/concatenation defects. These rows *intend* to be JSON; backfill is required but **deferred** to a separate hygiene initiative (see [MAC-208](/MAC/issues/MAC-208)). They do not gate v1.4.1 Stage 1.

        id=539 (Flock Safety, sid=13) belongs to class 2 but is repaired in [MAC-206](/MAC/issues/MAC-206) because the carve-out UPDATE mechanically requires `json_valid(notes)=1` on the target row. The repair lifted the freeform suffix verbatim into `notes.corroboration_note_2026_05_10` and added `notes.repair_audit.sweep_event_id='mac206_id539_repair_2026_05_20'`; the repair_audit + carve_out_audit events cross-reference each other on id=539's row.
    - **Downstream-consumer applicability (MAC-206 Phase 3 sweep, 2026-05-20):** the `argus_cli.py` query path, `db/validation/export_lynceus.py`, and `db/export/wave_a_snapshot_export.py` all read `identifiers.notes` as opaque-string (no `json_extract` calls on identifiers.notes); `db/validation/mac101_item_a_registry_xcheck.py` already guards with `WHERE json_valid(notes)` on raw_observations only (defensive, tolerates non-JSON). No consumer hard-requires `json_valid(notes)=1` globally on `identifiers`. The class-1 (convention) and class-2 (deferred) rows pass through all current consumers without §11 #17-applicability conflict. Any future consumer that adds a `json_extract(notes,'$.X')` call on a column where class-1 rows live MUST guard with `WHERE json_valid(notes)` first (operational sub-rule).

18. **Dispatch plan-input sandbox-absence HALT-fast-path default (CP32 §7 — 2026-05-21).** When a Stage 1+ phase plan-input lives in a cleaned `~/argus-internal/` (or analogous workspace-only) sandbox and was not snapshotted to a versioned location at dispatch time, the phase's HALT-fast-path becomes the **default disposition** (assuming the dispatch body anticipates this case with an explicit fast-path clause). The sandbox-clean condition is a discoverable precondition during pre-flight, not a mid-flight surprise; ratification can happen at HALT-comment time without per-record evidence enumeration. **Forward-looking sub-rule:** future dispatches that depend on `~/argus-internal/`-resident plan-inputs **SHOULD** (a) specify a snapshot path under a versioned location (the argus repo) at dispatch time — e.g., `~/argus/_phase_N_<topic>/inputs/<filename>.json` so the input is committed alongside the phase code; (b) include an explicit fallback fast-path clause in the dispatch body for the case where the snapshot was not captured. Pre-flight discipline: dispatches lacking either provision will surface the sandbox-absence as a HARD HALT without a fast-path default, forcing a full re-dispatch cycle rather than a clean ratification. This sub-rule is **operational guidance for dispatch authorship**, not a hard CHECK constraint — enforcement is at dispatch-authorship time (dispatcher discipline), not at schema-validation time. Precedent: [MAC-200](/MAC/issues/MAC-200) §9.2.c (informal exercise) + [MAC-207](/MAC/issues/MAC-207) Phase 11 ratification (codification trigger, [MAC-207 comment c4ec8740](/MAC/issues/MAC-207#comment-c4ec8740-36e4-42a9-bac6-cadd035bb110)).

19. **§11 #3 export-time generator post-condition guard pattern (CP32 §10 — 2026-05-21).** Export generators MUST include post-condition guards for hard-rule-bound content shapes. Canonical template: `_assert_no_email_pii(path)` per MAC-217 implementation at 6 emission call sites covering all 3 Lynceus export shapes × the both-floors-applied audit. The guard runs AFTER the export file is written, re-reads the file, and raises `Halt` if any post-write content violates the hard-rule predicate (in the canonical case, regex-detected email PII). **Forward-looking sub-rule:** any §11 hard-rule that constrains export content shape SHOULD have a paired `_assert_no_<rule>_<violation>(path)` post-condition guard at every emission call site. Defense-in-depth rationale: prior PII-bounded checks lived at the row-classification gate (`_classify_row` → drop bin), which is necessary but not sufficient — a bug in the classification gate or a future code-path that bypasses the gate (e.g., a custom export) would leak PII. The post-condition guard catches both classification-gate bugs AND new-code-path bypasses. Code pattern reference: `db/validation/export_lynceus.py` post commit `50b8232` (MAC-217 PII-strip + §11 #3 export guard landing). This is the first framework-level export-time generator post-condition guard codification; sibling-class hard-rules (§11 #12 OUI ban, §11 #13 unknown-category, §11 #14 procurement-only) are candidates for the same defense-in-depth pattern as future audit-discipline strengthens them.

20. **Operator-authorized in-cycle DML override.** When dispatch §0 baseline verification surfaces a drift that should-have-shipped in a prior v1.5.x patch and the in-flight cycle's §11 envelope is read-only (no schema migration, no `identifiers` writes), the operator may authorize a single-statement DML override against the canonical DB via in-session reply. The pattern is constrained as follows:

    1. **Authorization is per-statement and per-session.** Pre-authorization is not permitted. The operator must reply in the active dispatch session with explicit "patch it" (or equivalent) intent.
    2. **Single-statement scope.** Multi-DML batches require dispatch-class authorization (a new dispatch with explicit DML scope), not in-cycle override.
    3. **Drift-remediation only.** The override must address a baseline-drift discovered at §0 verification; it is not a vehicle for new feature work.
    4. **Mandatory pre-state and post-state capture** in an audit doc named `OPERATOR_AUTHORIZED_OVERRIDE_<TOPIC>.md` in the cycle's worktree. Must include the verbatim SQL, the row(s) affected, pre-state, post-state, and operator authorization timestamp.
    5. **Mandatory pre-patch backup.** Snapshot the canonical DB to `argus.db.pre_<topic>_<UTC-timestamp>` with sha256 captured.
    6. **Mandatory cross-reference in cycle handoff.** The cycle's `INTEGRATION_HANDOFF.md` and any session-summary doc must cite the override audit doc as `operator_authorized_exception[]`.
    7. **Read-only thereafter.** After the override executes, the cycle returns to read-only DB posture for the remainder of the run.

    (CP41 — 2026-06-03, MAC-301; staged at BIBLE_AMENDMENTS.md §11 #18-pending per MAC-239 Gate I-5 deferral 2026-05-23; ratified at this slot — see BIBLE_AMENDMENTS.md "Correction Pass 41" for slot-shift forensics.)

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
