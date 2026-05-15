# DATA_DICTIONARY.md — Argus v1.0.0 schema reference

## §1. Introduction

This document is the canonical schema reference for the Argus SQLite database (`db/argus.db`). It enumerates every table, every column, every CHECK-constraint enum value, and every foreign-key relationship in the v1.0.0 ship. It is the operational companion to [METHODOLOGY.md](METHODOLOGY.md) (which covers the *semantics* — how confidence is assigned, how dedup works, how provenance binds) and [CREDITS.md](CREDITS.md) (which covers upstream attribution + license-chain).

**Audience:** downstream operators integrating Argus's exports, external researchers auditing the dataset, contributors adding new identifier candidates or methodology refinements, vendors reviewing how their equipment is represented.

**Scope:** v1.0.0 schema (`schema_version=19` as of 2026-05-15; live verification timestamp 2026-05-15T01:57:18Z against `db/argus.db`). Future schema migrations land as paired commits per project amendment-log discipline; this document updates in lockstep.

**Conventions:**
- Column shape: `name TYPE NOT NULL DEFAULT … CHECK(…)` notation matches the migration source-of-truth at `db/migrations/*.sql`.
- Enum values: enumerated in the column's CHECK constraint at the migration that introduced them.
- Foreign keys: notated as `→ table.column` per SQL convention.
- Cross-references to METHODOLOGY: `METHODOLOGY §X` (public-OSS-shipped artifact at repo root).
- Cross-references to BIBLE_AMENDMENTS.md (amendment entries): part of the audit trail; `BIBLE_AMENDMENTS.md` ships in repo.

**Source-of-truth precedence at any disagreement:** (1) the on-disk schema at `db/argus.db` (PRAGMA table_info verifies live column shape), (2) the migration SQL at `db/migrations/*.sql` (immutable historical record), (3) `PROJECT_BIBLE.md` schema-section canonical enum roster, (4) this DATA_DICTIONARY (derived narrative).

## §2. Glossary — database / dataset / pipeline

Throughout this document and the Argus project:

- **Database** refers to the queryable SQLite file at `db/argus.db`. It contains all tables documented in §4 of this file. Re-runs of the pipeline reproduce the database from upstream sources; the database file itself is regenerable, not the source-of-truth (the pipeline + upstream sources are).
- **Dataset** refers to the exported JSON/CSV artifacts at `exports/` (`argus_export.json`, `argus_export_high_confidence.json`, `argus_export.csv`). These are derived from the database via the export worker (METHODOLOGY §5 export thresholds). The dataset is what downstream scanners (e.g., Lynceus) consume; the database is the canonical Argus-internal state.
- **Pipeline** refers to the migration + source-loader + extraction + validator + export code that reproduces the database from upstream sources. The pipeline is licensed under AGPL-3.0-or-later per [LICENSE](LICENSE); the dataset is licensed under ODbL-1.0 per [LICENSE-DATA](LICENSE-DATA); documentation (this file, METHODOLOGY, README, etc.) is licensed under CC-BY-SA-4.0 per [LICENSE-DOCS](LICENSE-DOCS).

## §3. Schema overview

The v1.0.0 schema carries **14 tables** at `schema_version=19`. They group into four functional categories:

### §3.1 Canonical-state tables (Layer 1)

- **`identifiers`** — the canonical identifier table. Every row is an identifier-to-attribution binding promoted from `raw_observations` per the promotion-gate hard rule. 17 columns; see §4.1.

### §3.2 Provenance + source tables

- **`raw_observations`** — the provenance source-of-truth per METHODOLOGY §7.1. 15 columns; see §4.2.
- **`sources`** — the source registry. 8 columns; see §4.3.
- **`manufacturers`** — vendor metadata lookup. 7 columns; see §4.4.

### §3.3 Layer 2 + supporting tables

- **`deployment_observations`** — Layer 2 deployment-location records. 22 columns; see §4.5.
- **`procurement_records`** — procurement records. 14 columns; see §4.6.
- **`fcc_grantees`** — FCC EAS bulk-load grantee registry. 19 columns; see §4.7.
- **`council_minutes_matters`** — municipal Granicus Legistar matters. 27 columns; see §4.8.
- **`wigle_anchor_priority`** — WiGLE planning state (disabled in v1.0.0). 10 columns; see §4.9.
- **`behavioral_signatures`** — parametric metadata for behavioral signatures. 13 columns; see §4.10.

### §3.4 Operational tables

- **`conflicts`** — validator-side disputed rows. 9 columns; see §4.11.
- **`extraction_runs`** — per-run telemetry. 10 columns; see §4.12.
- **`schema_version`** — migration ledger. 3 columns; see §4.13.
- **`source_reclassifications`** — per-row source-band reclassification audit (added migration 0017 for the post-CP15 `primary_registry` band-correction sweeps). 13 columns; see §4.14.

### §3.4.1 Live row counts

Verified against `db/argus.db` at 2026-05-15T01:57:18Z (`SELECT COUNT(*)` over each table):

| Table | Row count | Notes |
|---|---:|---|
| `identifiers` | **22,612** total = **22,532 active** + **80 superseded** | active = `superseded_by IS NULL` |
| `raw_observations` | **133,134** | append-only provenance source-of-truth |
| `sources` | **43** | source registry |
| `manufacturers` | **34** | vendor metadata lookup |
| `deployment_observations` | **116,668** | Layer 2 deployment-location records |
| `procurement_records` | **43,483** | analytical-only (never exported to Lynceus per §11 #14) |
| `fcc_grantees` | **50,153** | FCC EAS bulk-load |
| `council_minutes_matters` | **3** | low-volume per format-fit cap discipline |
| `wigle_anchor_priority` | **80,697** | pre-computed query priority; WiGLE API integration itself disabled in v1.0.0 pending operator quota grant |
| `behavioral_signatures` | **131** | parametric metadata (added migration 0010) |
| `conflicts` | **20** | validator-side disputed rows |
| `extraction_runs` | **106** | per-run telemetry |
| `source_reclassifications` | **809** | per-row band-correction audit (added migration 0017) |
| `schema_version` | **19** | migration ledger; one row per applied migration |

### §3.5 Relationship summary

```
raw_observations.source_id              → sources.id
raw_observations.extraction_run_id      → extraction_runs.id
raw_observations.promoted_identifier_id → identifiers.id
identifiers.superseded_by               → identifiers.id (self-reference)
identifiers.paired_identifier_id        → identifiers.id (self-reference)
deployment_observations.source_id       → sources.id
deployment_observations.extraction_run_id → extraction_runs.id
procurement_records.linked_identifier_id → identifiers.id
fcc_grantees.source_id                  → sources.id
council_minutes_matters.source_id       → sources.id
council_minutes_matters.linked_identifier_id → identifiers.id
wigle_anchor_priority.deployment_id     → deployment_observations.id (CASCADE)
behavioral_signatures.source_id         → sources.id (RESTRICT)
conflicts.identifier_a_id               → identifiers.id (CASCADE)
conflicts.identifier_b_id               → identifiers.id (CASCADE)
conflicts.raw_observation_id            → raw_observations.id (CASCADE)
```

`identifiers.manufacturer` is matched by string equality to `manufacturers.canonical_name` (or the JSON-array `aliases` column); logical FK, not enforced.

## §4. Tables

### §4.1. `identifiers` (Layer 1 canonical)

The canonical Argus identifier table. Every row represents one identifier-to-attribution binding. Row count verified live 2026-05-15T01:57:18Z: **22,532 active** (`superseded_by IS NULL`) + **80 superseded** = **22,612 total**.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. Stable per row; not directly exported to downstream consumers (consumer-facing stable identifier is `argus_record_id`, a 16-hex-char SHA-256 prefix; algorithm documented in [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) — see Canonical sources at end). |
| `identifier` | TEXT | yes | — | The identifier value itself (e.g., `aa:bb:cc:dd:ee:ff` MAC, `aa:bb:cc` OUI, `1581Fxxx` FAA RID drone prefix, `0x004C` BLE manufacturer ID, BLE service UUID, vendor SSID pattern). Normalization rules per identifier_type documented in METHODOLOGY §6.1 dedup-key normalization. |
| `identifier_type` | TEXT | yes | — | Enum extended cumulatively across migrations 0001–0019 (full roster in §5.1; 48 canonical values at `schema_version=19`). Baseline migration 0001: `oui`, `mac`, `mac_range`, `bssid`, `ssid_exact`, `ssid_pattern`, `ble_uuid`, `ble_service`, `device_fingerprint`. Migration 0009: `ble_local_name`, `ble_characteristic`, `product_family_codename`. Migration 0011: `ble_manufacturer_id`. Migration 0013: `drone_id_prefix`, `icao_24bit_address`, `rf_channel`, `burst_cadence_ms`, `bandwidth_mhz`, `device_class_id`, `rf_burst_duration`, `rf_protocol_constant`, `wifi_aware_service_name`, `wifi_ie_element_id`, `bluetooth_le_pdu_type`, `wifi_frame_control_subtype`, `wifi_nan_param_signature`. Migration 0014: `alpr_model`. Migration 0018: `ble_protocol_byte_table`, `ble_service_uuid`, `ble_company_id`, `frequency_band`, `ble_protocol_byte`, `operator_profile`, `x509_cert_sha256_prefix`, `ble_adv_interval`, `ble_payload_offset`, `firmware_sha256_hash`, `network_endpoint`, `firmware_image_variant`, `qualcomm_chip_format_id`, `firmware_branded_string`. Migration 0019 (CP21 round-2 vocab): `asdstan_message_type`, `asdstan_enum_value`, `dji_protocol_struct_format`, `gpt_partition_uuid`, `chipset_codename`, `firmware_build_string`, `firmware_build_uuid`. The forward-codified `vendor_template_namespace_uuid` value (per the vendor-companion-app sub-banding amendment) is not in the current CHECK; it lands at first-promotion-time per the forward-looking-codification caveat. |
| `device_category` | TEXT | yes | — | Enum (12 values per on-disk CHECK constraint): `alpr`, `imsi_catcher`, `body_cam`, `police_radio`, `drone`, `gunshot_detect`, `hacking_tool`, `covert_cam`, `gps_tracker`, `face_recog`, `drone_detect`, `unknown`. `unknown` rows are excluded from the Lynceus export per the multi-purpose-vendor discipline (canonical-only). |
| `manufacturer` | TEXT | no | NULL | Vendor name in canonical form. Logical FK to `manufacturers.canonical_name` (not enforced). |
| `model` | TEXT | no | NULL | Vendor's product name in marketing or internal form. Composes with METHODOLOGY §5.4 product-family taxonomy. |
| `confidence` | INTEGER | no | NULL | Integer per schema-level CHECK `BETWEEN 0 AND 100`. **Operational cap at 99** per METHODOLOGY §5 confidence model: the corroboration-boost formula `min(99, max(...) + 5)` + the §5.6 ceiling rule cap effective confidence at 99 (humility-margin invariant). Schema-level CHECK permits 0-100 to give the operational layer flexibility; the 99-cap is enforced at write-time by the validator/dedup pass, not the schema. |
| `source_url` | TEXT | yes | — | Working URL where the identifier was extracted. Per METHODOLOGY §7.2: direct citation, no aggregators. |
| `source_type` | TEXT | yes | — | Enum (10 values): `official`, `regulatory`, `procurement`, `academic`, `foia`, `crowdsourced`, `inferred`, `manufacturer_doc` (baseline); `manufacturer_app` (migration 0009); `primary_registry` (migration 0015). Drives confidence band per METHODOLOGY §5.1. |
| `source_excerpt` | TEXT | no | NULL | Verbatim excerpt. Schema-level CHECK: `IS NULL OR length(source_excerpt) <= 200`. PII-sanitized per the no-PII hard rule. |
| `geographic_scope` | TEXT | no | NULL | Country-level scope: `US`, `EU`, `UK`, `global`, `unknown`, or specific ISO-3166 country code. Default export-time filter: `['US']`. |
| `first_seen` | DATETIME | no | NULL | UTC timestamp of first ingest. |
| `last_verified` | DATETIME | no | NULL | UTC timestamp of most-recent re-verification. |
| `notes` | TEXT | no | NULL | JSON blob carrying per-row metadata. |
| `superseded_by` | INTEGER | no | NULL | Self-reference FK: if non-NULL, this row was superseded per METHODOLOGY §6.4. Exports filter on `superseded_by IS NULL`. |
| `paired_identifier_id` | INTEGER | no | NULL | Self-reference FK to a paired identifier per `pair_kind`. |
| `pair_kind` | TEXT | no | NULL | Enum (4 non-NULL values + NULL per on-disk CHECK constraint): `la_bit_flip`, `frdid_sibling`, `vendor_as_container`, `firmware_generation`. Pairing-discipline values from migration 0012. `static_mac_tracker` is a deferred item (queued for future canonical-bible §-text codification) and is NOT currently in the enum. |

#### Indexes

Indexes follow the standard `idx_<table>_<column>` naming convention; primary lookup paths include `(identifier, identifier_type)`, active-set partial index on `(superseded_by IS NULL)`, `(manufacturer)`, and `(source_type, confidence)`. See `db/migrations/0001_initial.sql` and subsequent migration files for the full set.

#### Composition with METHODOLOGY rules

- Confidence integer is per METHODOLOGY §5 confidence model (default by `source_type`, corroboration boost per §5.2, ceiling rule per §5.6).
- `superseded_by` pointer semantics per METHODOLOGY §6.4 superseded-row preservation.
- `paired_identifier_id` + `pair_kind` semantics per the canonical-bible pairing discipline (LA-bit pairing, vendor-as-container, firmware-generation, FRDID pairing).

### §4.2. `raw_observations` (provenance source-of-truth)

Provenance layer per METHODOLOGY §7.1. Every promoted `identifiers` row is anchored to one or more `raw_observations` rows. Row count verified live 2026-05-15T01:57:18Z: **133,134**. Append-only invariant: rows do not mutate post-ingest (validator processing updates `processed_at` + `promoted_identifier_id` + `notes` only; never the source-evidence fields).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `source_id` | INTEGER | no | NULL | FK → `sources.id`. |
| `extraction_run_id` | INTEGER | no | NULL | FK → `extraction_runs.id`. |
| `source_url` | TEXT | yes | — | Working URL fetched at ingest time. |
| `raw_payload` | TEXT | no | NULL | Verbatim source bytes (or JSON-encoded). PII-sanitized at ingest. |
| `candidate_identifier` | TEXT | no | NULL | Extracted identifier value. NULL when row is non-identifier metadata. |
| `candidate_type` | TEXT | no | NULL | Proposed `identifier_type`. |
| `candidate_category` | TEXT | no | NULL | Proposed `device_category`. |
| `candidate_manufacturer` | TEXT | no | NULL | Proposed manufacturer name. |
| `source_excerpt` | TEXT | no | NULL | Verbatim excerpt from `source_url`. Sized per the source-excerpt discipline: ≤200 chars baseline, with the broader window-around-match option (with `excerpt_type` field) for source-line >200 chars. (Distinct from the promotion-gate "no promotion without provenance" rule.) PII-sanitized per the no-PII hard rule. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of ingest. |
| `processed_at` | DATETIME | no | NULL | UTC timestamp of validator-side processing. NULL = not-yet-processed. |
| `promoted_identifier_id` | INTEGER | no | NULL | FK → `identifiers.id`. Non-NULL if promoted. |
| `notes` | TEXT | no | NULL | JSON blob: per-row metadata, archive-snapshot URLs, validator disposition notes. |
| `source_row_key` | TEXT | no | NULL | Idempotency anchor for re-ingest; deterministic hash over (`source_id`, structurally-significant fields). |

#### Indexes

Primary on `(id)`. Additional indexes on `(source_id, source_row_key)` for idempotency check and `(promoted_identifier_id)` partial index for canonical-row-to-provenance lookup.

#### Composition with METHODOLOGY rules

- Append-only per METHODOLOGY §7.1; rows never mutate post-ingest.
- Direct citation per METHODOLOGY §7.2 (no aggregators); archive snapshots in `notes`.
- No fabrication per the no-fabrication hard rule: extraction yielding no concrete value routes to `conflicts` (§4.11), not to a synthetic `raw_observations` row.
- PII-sanitization at ingest per the no-PII hard rule.

### §4.3. `sources` (upstream source registry)

Source registry. FK target for `raw_observations.source_id`. Row count verified live 2026-05-15T01:57:18Z: **43**.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. Sources 1-3 are IEEE OUI registries (MA-L / MA-M / MA-S); the forward-looking source-level migration to `primary_registry` is deferred (queued as a post-ship batch task). |
| `name` | TEXT | yes | — | Human-readable source name. |
| `url` | TEXT | yes | — | Primary upstream URL. |
| `source_type` | TEXT | yes | — | Source-band classification; enum matches `identifiers.source_type`. Sources 1-3 (IEEE OUI) currently `'regulatory'` pending the deferred source-level reclassification. |
| `tier` | INTEGER | no | NULL | Tier classification per the canonical-bible source-tier hierarchy. |
| `last_fetched_at` | DATETIME | no | NULL | UTC timestamp of most-recent fetch. |
| `last_status` | TEXT | no | NULL | Status of most-recent fetch. |
| `notes` | TEXT | no | NULL | JSON blob: per-source metadata, license attribution. |

#### Indexes

Primary on `(id)`. Unique on `(name)`.

#### Composition with METHODOLOGY rules

- `sources.source_type` drives default confidence band for derived `raw_observations` per METHODOLOGY §5.1.
- Source-level reclassification (changing `sources.source_type`) does NOT retroactively reclassify `identifiers` rows whose direct provenance is third-party — per the third-party-citation-lineage boundary (METHODOLOGY §5.3 row-level discipline; §7.4 third-party-citation-lineage detail).

### §4.4. `manufacturers` (vendor metadata lookup)

Vendor metadata + alias canonicalization. Row count at v1.0.0: **34**.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. FK target for `procurement_records.manufacturer_id`. |
| `canonical_name` | TEXT | yes | — | Canonical vendor name. String-match target for `identifiers.manufacturer`. Word-boundary discipline: match `\bMotorola Solutions\b`, not `\bMotorola\b`. |
| `aliases` | TEXT | no | NULL | JSON array of vendor-name aliases. |
| `primary_category` | TEXT | no | NULL | Primary `device_category` enum value. NULL for multi-purpose vendors. |
| `source_url` | TEXT | yes | — | Primary attribution URL. |
| `notes` | TEXT | no | NULL | JSON blob: per-vendor metadata, corporate-split history (vendor-disambiguation discipline). |
| `added_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of first registration. |

#### Indexes

Primary on `(id)`. Unique on `(canonical_name)`.

#### Composition with METHODOLOGY rules

- Multi-purpose-vendor discipline: `primary_category=NULL` cannot lift `device_category` off `unknown` at OUI level. Model-level evidence required.
- Corporate-split disambiguation (Motorola Mobility / Motorola Solutions etc.) per the vendor-disambiguation discipline; alias-iteration per the once-per-canonical iteration sub-rule.

### §4.5. `deployment_observations` (Layer 2 deployment-location records)

Layer 2 deployment-location records (Atlas of Surveillance + DeFlock). Row count at v1.0.0: **116,668** (Atlas 15,071 + DeFlock 101,597). Per METHODOLOGY §7.5 and the no-PII hard rule, agency-level identification only; never individual-officer level.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `source_id` | INTEGER | no | NULL | FK → `sources.id`. |
| `extraction_run_id` | INTEGER | no | NULL | FK → `extraction_runs.id`. |
| `source_url` | TEXT | yes | — | Working URL. |
| `source_row_key` | TEXT | yes | — | Idempotency anchor. |
| `agency_name` | TEXT | no | NULL | Deploying agency name. |
| `agency_type` | TEXT | no | NULL | Agency classification per upstream taxonomy. |
| `juris_type` | TEXT | no | NULL | Jurisdiction shape. |
| `city` | TEXT | no | NULL | City name. |
| `county` | TEXT | no | NULL | County name. |
| `state` | TEXT | no | NULL | US state postal code or ISO subdivision. |
| `country` | TEXT | no | NULL | ISO-3166 country code. |
| `lat` | REAL | no | NULL | Latitude WGS84. |
| `lon` | REAL | no | NULL | Longitude WGS84. |
| `technology_category` | TEXT | no | NULL | **Free-text** (no CHECK constraint) passing upstream-taxonomy values through. v1.0.0 DB carries 13 distinct values: `ALPR` (DeFlock; 101,597 rows), and 12 Atlas-classified categories (`Body-worn Cameras`, `Automated License Plate Readers`, `Drones`, `Third-party Investigative Platforms`, `Face Recognition`, `Camera Registry`, `Gunshot Detection`, `Real-Time Crime Center`, `Predictive Policing`, `Video Analytics`, `Cell-site Simulator`, `Fusion Center`). Note: `ALPR` (DeFlock) and `Automated License Plate Readers` (Atlas) are semantically equivalent — downstream consumers reconciling across both upstreams should treat them as the same category. |
| `vendor_raw` | TEXT | no | NULL | Vendor name as recorded upstream (raw). Canonicalization deferred to query-time. |
| `citation_url` | TEXT | no | NULL | Secondary citation URL. |
| `source_excerpt` | TEXT | no | NULL | Verbatim excerpt. Schema-level CHECK enforces ≤200 chars at INSERT. The extraction-time source-excerpt discipline applies in addition (distinct from the promotion-gate hard rule). PII-sanitized per the no-PII hard rule. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of ingest. |
| `processed_at` | DATETIME | no | NULL | UTC timestamp of validator-side processing. |
| `notes` | TEXT | no | NULL | JSON blob. |
| `license` | TEXT | yes | — | Upstream license. **CHECK constraint** enumerates 5 values: `'ODbL-1.0'` (DeFlock; source_id=6), `'CC-BY-NC-SA-4.0'` (EFF Atlas; source_id=5), `'public-domain'` (reserved for future US-gov-public-domain ingest), `'foia'` (FOIA-released data per the canonical-bible FOIA discipline), `'unspecified'` (default for rows ingested pre-migration-0016 or license unknown at ingest). Migration 0016 added this column. Per CREDITS.md upstream-license-chain: Atlas-derived rows quarantine under the NC clause; downstream derivatives filtering on `license != 'CC-BY-NC-SA-4.0'` produce ODbL-1.0-compatible derivatives. |

#### Indexes (7 indexes per current schema)

Primary on `(id)`. Unique on `(source_id, source_row_key)` (idempotency). Additional on `(technology_category)`, `(vendor_raw)`, `(state)`, `(extraction_run_id)`, `(source_id)`.

#### Composition with METHODOLOGY rules

- **License carry-forward** per CREDITS.md: Atlas (source_id=5) rows quarantine under CC-BY-NC-SA-4.0 per upstream NC clause; the `license` column (migration 0016) is the operational hook.
- **Agency-only individuation** per the no-PII hard rule.
- **Procurement-vs-deployment caveat** per METHODOLOGY §5 and the canonical-bible deployment-evidence discipline.
- **Disambiguation discipline** per the codified vendor-disambiguation rule.
- **Vendor canonicalization deferred to query-time** per the alias-iteration sub-rules.

### §4.6. `procurement_records` (vendor-agency procurement records)

Vendor-to-agency purchase records. Row count at v1.0.0: **43,483**. Procurement records prove *purchase*, NOT *deployment*; procurement-only records are excluded from the Lynceus export (canonical-only).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `agency_name` | TEXT | yes | — | Purchasing agency name. Per the no-PII hard rule: PII-sanitized at ingest (individual contracting-officer names stripped). |
| `agency_geographic_scope` | TEXT | no | NULL | ISO country/region code. |
| `vendor_canonical_name` | TEXT | yes | — | Vendor canonical name. |
| `product_family` | TEXT | no | NULL | Vendor product family identifier. |
| `contract_amount_usd` | REAL | no | NULL | Contract dollar amount (USD). |
| `contract_date` | DATE | no | NULL | Contract execution date. |
| `source_url` | TEXT | yes | — | Per the canonical-bible provenance discipline. |
| `source_type` | TEXT | yes | — | **CHECK constraint** enumerates 4 values: `'procurement'`, `'foia'`, `'regulatory'`, `'official'`. Narrower subset than `identifiers.source_type` (10 values). |
| `source_excerpt` | TEXT | no | NULL | Schema-level CHECK enforces ≤200 chars. PII-sanitized per the no-PII hard rule. |
| `confidence` | INTEGER | no | NULL | Integer 0–100 per **CHECK constraint** (`confidence BETWEEN 0 AND 100`). Note: range diverges from `identifiers.confidence` operational cap (99) — procurement records are not subject to the METHODOLOGY §5 humility-margin invariant (identifier-attribution requires the residual-1-of-fabrication-risk margin; procurement records are about contract execution, a discrete event). See §6 confidence-shape divergence sub-section for the cross-table synthesis. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of ingest. |
| `linked_identifier_id` | INTEGER | no | NULL | FK → `identifiers.id` (`ON DELETE SET NULL`). |
| `notes` | TEXT | no | NULL | JSON blob. |

#### Indexes

Primary on `(id)`. Additional on `(vendor_canonical_name)`, `(agency_name)`.

#### Composition with METHODOLOGY + bible rules

- **Excluded from the Lynceus export**: procurement records with no concrete identifier are NEVER exported to Lynceus.
- **Procurement-vs-deployment caveat**: procurement proves *purchase*, not *deployment*.
- **Cross-table confidence cap at 85** per METHODOLOGY §5 + the canonical-bible procurement-corroboration rule when procurement records corroborate `identifiers` rows.
- **PII-sanitization** per the no-PII hard rule.

### §4.7. `fcc_grantees` (FCC EAS bulk-load grantee registry)

FCC Equipment Authorization System (EAS) grantee registry. Row count at v1.0.0: **50,153**. Used as the allowlist for `fcc_id_anchored` disambiguation (50,153-row corporate-registrant allowlist + CVE/CWE/NVD stop-list).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `source_id` | INTEGER | yes | — | FK → `sources.id`. |
| `extraction_run_id` | INTEGER | yes | — | FK → `extraction_runs.id`. |
| `source_url` | TEXT | yes | — | Working URL for FCC EAS upstream. |
| `source_row_key` | TEXT | yes | — | Idempotency anchor = `grantee_code`. |
| `grantee_code` | TEXT | yes | — | FCC-assigned 3-5 char alphanumeric grantee prefix (e.g., `'2APLW'` Flock Safety, `'2ADIY'` DJI). |
| `grantee_name` | TEXT | yes | — | Corporate registrant name. Word-boundary discipline applies. |
| `mailing_address` | TEXT | no | NULL | Corporate mailing address (public record). |
| `po_box` | TEXT | no | NULL | PO box. |
| `city` | TEXT | no | NULL | Registrant city. |
| `state` | TEXT | no | NULL | US state name or `N/A`. |
| `country` | TEXT | no | NULL | Country name. |
| `zip_code` | TEXT | no | NULL | Registrant ZIP. |
| `contact_name` | TEXT | no | NULL | Corporate compliance contact — corporate role only; individual operational-personnel names are not in this column per the no-PII hard rule. |
| `date_received` | TEXT | yes | — | ISO date. |
| `source_excerpt` | TEXT | no | NULL | Schema-level CHECK ≤200 chars. |
| `notes` | TEXT | no | NULL | JSON blob: raw row + Phase-5 hooks. |
| `captured_at` | TEXT | yes | `datetime('now')` | UTC timestamp (TEXT not DATETIME per FCC EAS migration convention). |
| `processed_at` | TEXT | no | NULL | UTC timestamp of validator-side processing. |

#### Constraints

`UNIQUE (source_id, source_row_key)` — idempotency-by-grantee_code.

#### Indexes (5 indexes per current schema)

Primary on `(id)`. Implicit unique on `(source_id, source_row_key)`. Additional on `(grantee_code)`, `(grantee_name)`, `(state)`.

#### Composition with METHODOLOGY + bible rules

- **`drone_id_prefix` composition** per the canonical-bible: FCC EAS grantees compose with FAA RID `drone_id_prefix` identifier-type at promotion.
- **FCC-ID disambiguation allowlist** for vendor attribution.
- **Vendor-name word-boundary discipline** per the codified vendor-disambiguation rule.
- **No PII promotion** per the no-PII hard rule: corporate compliance role only.

### §4.8. `council_minutes_matters` (municipal Granicus Legistar matters)

Municipal council / legislative matters where vendor procurement decisions are documented. Sourced from Granicus Legistar instances. Row count at v1.0.0: **3** (low-volume per the format-fit cap discipline). Largest table by column count in v1.0.0 (27 columns).

Per the canonical-bible no-fabrication hard rule and the Legistar-specific status-discipline sub-rule: only `matter_status='Passed'` rows are staged. PII-sanitization at ingest per the no-PII hard rule.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `source_id` | INTEGER | yes | — | FK → `sources.id`. |
| `extraction_run_id` | INTEGER | no | NULL | FK → `extraction_runs.id`. |
| `source_row_key` | TEXT | yes | — | Idempotency = `{legistar_client}:{matter_id}`. |
| `legistar_client` | TEXT | yes | — | Granicus Legistar instance: `'chicago'`, `'sfgov'`, `'detroit'`, `'hampton'`, `'cabq'` (5 jurisdictions; `cabq` = City of ALBuQuerque). |
| `agency_name` | TEXT | yes | — | Display name. |
| `agency_geographic_scope` | TEXT | no | NULL | ISO-shaped scope. |
| `matter_id` | INTEGER | yes | — | Legistar `MatterId` (jurisdiction-scoped). |
| `matter_guid` | TEXT | no | NULL | Legistar `MatterGuid`. |
| `matter_file` | TEXT | no | NULL | Human-readable matter file identifier. |
| `matter_title` | TEXT | yes | — | Matter title verbatim. PII-redacted at staging per the no-PII hard rule and the Legistar-specific staging sub-rule. |
| `matter_type_name` | TEXT | no | NULL | Legistar matter classification (free-text). |
| `matter_body_name` | TEXT | no | NULL | Deliberating body. |
| `matter_status_name` | TEXT | yes | — | Status name. Only `'Passed'` rows staged per the no-fabrication hard rule and the Legistar status-discipline sub-rule. Single-value-by-discipline; not CHECK-enforced for future expansion-flexibility. |
| `matter_intro_date` | DATE | no | NULL | Date introduced. |
| `matter_passed_date` | DATE | no | NULL | Date passed. |
| `matter_enactment_date` | DATE | no | NULL | Effective date. |
| `matter_cost` | TEXT | no | NULL | Dollar amount raw (Legistar TEXT shape). |
| `matched_vendor_label` | TEXT | yes | — | Canonical vendor label after disambiguation. |
| `vendor_canonical_name` | TEXT | yes | — | Vendor name as recorded upstream (raw); canonicalization deferred to query-time. |
| `source_url` | TEXT | yes | — | Per-matter Legistar UI URL. |
| `source_type` | TEXT | yes | — | **CHECK constraint** 3 values: `'procurement'`, `'foia'`, `'official'` (narrower than procurement_records 4-value enum). |
| `source_excerpt` | TEXT | no | NULL | Schema-level CHECK ≤200 chars. |
| `confidence` | INTEGER | yes | — | **Discrete CHECK constraint** `IN (70, 75, 80)` per the Legistar item-grading sub-rule. Distinct from continuous-range confidence in other tables. |
| `linked_identifier_id` | INTEGER | no | NULL | FK → `identifiers.id`. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of ingest. |
| `notes` | TEXT | no | NULL | JSON blob. |

#### Constraints

`UNIQUE (source_id, source_row_key)`.

#### Indexes (7 indexes per current schema)

Primary on `(id)`. Implicit unique on `(source_id, source_row_key)`. Additional on `(linked_identifier_id)`, `(extraction_run_id)`, `(matter_passed_date)`, `(matched_vendor_label)`, `(legistar_client)`.

#### Composition with METHODOLOGY + bible rules

- **Status-discipline**: only `'Passed'` rows staged.
- **PII-sanitization** at staging per the no-PII hard rule.
- **Canonical-label composition** with raw-upstream preservation.
- **Cross-table contribution to identifiers** per METHODOLOGY §5 corroboration-boost formula.

### §4.9. `wigle_anchor_priority` (WiGLE planning state; disabled in v1.0.0)

Pre-computed WiGLE-query priority rankings for `deployment_observations` rows. Row count at v1.0.0: **80,697**. **Operationally inert at v1.0.0 ship**: the WiGLE API integration itself is disabled pending the user's own WiGLE quota grant (per WiGLE Terms of Service).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `deployment_id` | INTEGER | yes | — | FK → `deployment_observations.id` (`ON DELETE CASCADE`). One-to-one via `UNIQUE (deployment_id)`. |
| `extraction_run_id` | INTEGER | no | NULL | FK → `extraction_runs.id`. |
| `priority_tier` | INTEGER | yes | — | **CHECK constraint** 1-5: T1 highest-priority US state-coded, T2 intermediate US state-coded, T3 lower-priority US state-coded, T4 US territory (PR/USVI/GU/AS/MP), T5 international (ISO 3166 alpha-2 country code). |
| `state_or_country` | TEXT | yes | — | Geographic anchor. T1-T4 US codes; T5 ISO 3166 alpha-2. |
| `intra_tier_rank` | INTEGER | yes | — | 1-based rank within `(priority_tier, state_or_country)`. |
| `tier_rationale` | TEXT | no | NULL | Short string explaining tier+rank choice. |
| `derivation_method` | TEXT | yes | — | **CHECK constraint** 2 values: `'atlas_state_column'` (Atlas direct), `'deflock_reverse_geocode'` (DeFlock via reverse_geocoder admin1 lookup). |
| `derivation_notes` | TEXT | no | NULL | Debug-trace metadata. |
| `captured_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp. |

#### Constraints

`UNIQUE (deployment_id)`. CASCADE delete via `deployment_id` FK.

#### Indexes (6 indexes per current schema)

Primary on `(id)`. Implicit unique on `(deployment_id)`. Additional on `(extraction_run_id)`, `(derivation_method)`, `(state_or_country)`, `(priority_tier)`.

#### Composition with METHODOLOGY + bible rules

- **WiGLE disabled in v1.0.0** pending user WiGLE-quota grant (per WiGLE Terms of Service).
- **Pre-computation discipline**: rankings computed at v1.0.0 ship so post-grant activation is one-step.
- **`atlas_state_column` vs `deflock_reverse_geocode` derivation_method asymmetry**: Atlas provides state directly; DeFlock requires reverse-geocoding via the `reverse_geocoder` pip package (bbox+centroid alternative tested at 24.6% multi-match prevalence; Amarillo TX canary case demonstrates reverse_geocoder admin1 lookup is correct).
- **Disabled-but-materialized rationale**: rankings populated so post-grant activation is one-step.

### §4.10. `behavioral_signatures` (parametric metadata for behavioral signatures)

Parametric metadata for behavioral-class detection signatures. Introduced in migration 0010. Row count at v1.0.0: **131** (per CHANGELOG; the v1.0.0 ship populated this table from the Marlin NDSS 2025 corpus and subsequent backfills).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `signature_name` | TEXT | yes | — | Signature identity. One `signature_name` per layer per Phase-2 self-review §2.4 staging-style (folds N code paths per signature). |
| `cellular_generation` | TEXT | no | NULL | **CHECK constraint** 4 values + NULL: `'2G'`, `'3G'`, `'4G'`, `'5G_NSA'`. |
| `threshold_json` | TEXT | no | NULL | **CHECK constraint** `json_valid()`. Structured thresholds. |
| `evidence_json` | TEXT | no | NULL | **CHECK constraint** `json_valid()`. Evidence dossier per the no-fabrication hard rule. |
| `source_id` | INTEGER | yes | — | FK → `sources.id` (`ON DELETE RESTRICT`). |
| `source_file_relative` | TEXT | no | NULL | File path relative to source repo. |
| `source_line` | INTEGER | no | NULL | Line number. |
| `confidence` | INTEGER | no | NULL | **CHECK constraint** `BETWEEN 0 AND 100`. The intake-time false-positive-class allowlist sub-rule applies. |
| `device_category` | TEXT | yes | — | **CHECK constraint** 12 values mirroring `identifiers.device_category`: `alpr`, `imsi_catcher`, `body_cam`, `police_radio`, `drone`, `gunshot_detect`, `hacking_tool`, `covert_cam`, `gps_tracker`, `face_recog`, `drone_detect`, `unknown`. |
| `notes` | TEXT | no | NULL | JSON or free-text. |
| `created_at` | DATETIME | no | `CURRENT_TIMESTAMP` | UTC timestamp. |
| `updated_at` | DATETIME | no | `CURRENT_TIMESTAMP` | UTC timestamp of last update. |

#### Constraints

`UNIQUE (signature_name, source_id, cellular_generation)` — 3-tuple (forward-proof; SQLite UNIQUE treats multiple NULLs as distinct).

#### Indexes (5 indexes per current schema)

Primary on `(id)`. Implicit unique on `(signature_name, source_id, cellular_generation)`. Additional on `(cellular_generation)`, `(device_category)`, `(signature_name)`.

#### Composition with METHODOLOGY + bible rules

- **Evidence dossier**: every row carries `evidence_json` traceability per the no-fabrication hard rule.
- **Unknown-category exclusion**: `device_category='unknown'` rows are excluded from the Lynceus export per the multi-purpose-vendor discipline.
- **Intake-time false-positive-class allowlist** applies at confidence assignment.

### §4.11. `conflicts` (validator-side disputed rows)

validator-side disputed rows awaiting manual disposition. Row count verified live 2026-05-15T01:57:18Z: **20** (matches CHANGELOG; the previously-deferred refresh per the §7 maintenance posture has now landed).

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `identifier_a_id` | INTEGER | no | NULL | FK → `identifiers.id` (`ON DELETE CASCADE`). First conflicting identifier. |
| `identifier_b_id` | INTEGER | no | NULL | FK → `identifiers.id` (`ON DELETE CASCADE`). Second conflicting identifier (NULL for single-row conflicts). |
| `raw_observation_id` | INTEGER | no | NULL | FK → `raw_observations.id` (`ON DELETE CASCADE`). |
| `reason` | TEXT | yes | — | Conflict classification (free-text; common values: `'known_fake_pattern'`, `'category_disagreement'`, `'vendor_attribution_split'`, `'la_bit_sibling_vendor_mismatch'`). No CHECK constraint. |
| `detected_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp. |
| `resolved_at` | DATETIME | no | NULL | UTC timestamp of resolution. NULL = unresolved. |
| `resolved_by` | TEXT | no | NULL | Agent id or human. |
| `resolution_notes` | TEXT | no | NULL | Resolution narrative. |

#### Indexes (4 indexes per current schema)

Primary on `(id)`. Additional on `(identifier_a_id)`, `(identifier_b_id)`, partial on `(resolved_at) WHERE resolved_at IS NULL` (unresolved-queue).

#### Composition with METHODOLOGY + bible rules

- **No-fabrication**: uncertain extractions route to `conflicts` per METHODOLOGY §7.3.
- **Amendment-log discipline**: unresolved conflicts touching canonical-bible amendments halt new work until resolved.
- **Vendor-disambiguation false-positive class**: `'vendor_attribution_split'` is the canonical reason.
- **LA-bit sibling pairing mismatch**: `'la_bit_sibling_vendor_mismatch'` per the canonical-bible LA-bit pairing rule.
- **Cascade-delete protection** on all three FK columns prevents orphan conflicts.

### §4.12. `extraction_runs` (per-run telemetry)

Per-run telemetry: worker / source / records-in / records-out / status / notes for each extraction batch. Row count verified live 2026-05-15T01:57:18Z: **106 runs**.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. FK target for `raw_observations.extraction_run_id`, `deployment_observations.extraction_run_id`, `fcc_grantees.extraction_run_id`, `council_minutes_matters.extraction_run_id`, `wigle_anchor_priority.extraction_run_id`, `behavioral_signatures.extraction_run_id`. |
| `agent_id` | TEXT | yes | — | Agent identifier of the worker that ran the extraction (typically a UUID per Paperclip agent identity). |
| `source_id` | INTEGER | no | NULL | FK → `sources.id` (`ON DELETE SET NULL`). Source the extraction ran against. NULL for cross-source runs. |
| `started_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of run start. |
| `finished_at` | DATETIME | no | NULL | UTC timestamp of run completion. NULL = still running. |
| `records_in` | INTEGER | no | 0 | Count of input records read from the upstream source. |
| `records_out` | INTEGER | no | 0 | Count of `raw_observations` rows produced. |
| `errors` | INTEGER | no | 0 | Count of per-row errors during the run. |
| `status` | TEXT | no | NULL | Run status: `'running'`, `'ok'`, `'failed'`, `'partial'`. Free-text (no CHECK constraint). |
| `notes` | TEXT | no | NULL | JSON or free-text run notes (commit SHAs, run context, etc.). |

#### Indexes (3 indexes per current schema)

Primary on `(id)`. Additional on `(agent_id)`, `(source_id)`.

#### Composition with METHODOLOGY + bible rules

- **Append-only invariant per §7.1 composition**: rows do not mutate post-completion; `finished_at` + `status` + `records_out` + `errors` set at run completion. Notes may be amended for post-hoc audit (e.g., commit SHA cross-reference).
- **Per-run telemetry** ties every downstream artifact (`raw_observations`, `deployment_observations`, etc.) to a specific run for replay + audit.

### §4.13. `schema_version` (migration ledger)

Migration ledger: every applied migration has one row.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `version` | INTEGER | yes (PK) | — | Migration version number (sequential; current `MAX(version)=19` at the post-CP21-round-2 v1.0.0 state, verified live 2026-05-15T01:57:18Z). |
| `name` | TEXT | yes | — | Human-readable migration name (e.g., `'0019_identifier_types_round2'`, `'0017_source_reclassifications'`, `'0016_license_column'`). Full ledger 0001–0019 enumerated below. |
| `applied_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of migration application. |

Live migration ledger at `schema_version=19` (verified live 2026-05-15T01:57:18Z):

| version | name | applied_at |
|---:|---|---|
| 1 | `0001_initial` | 2026-05-04T03:29:04Z |
| 2 | `0002_deployment_observations` | 2026-05-04T05:07:21Z |
| 3 | `0003_fcc_grantees` | 2026-05-04T14:41:33Z |
| 4 | `0004_wigle_anchor_priority` | 2026-05-04T18:53:58Z |
| 5 | `0005_council_minutes_matters` | 2026-05-04T19:12:50Z |
| 6 | `0006_raw_observations_source_row_key` | 2026-05-05T12:53:35Z |
| 7 | `0007_motorola_solutions_aliases_rescope` | 2026-05-06T18:25:16Z |
| 8 | `0008_cp7_cp10_v01_cutover` | 2026-05-07T17:30:49Z |
| 9 | `0009_manufacturer_app_and_identifier_type_extensions` | 2026-05-10T20:40:15Z |
| 10 | `0010_behavioral_signatures` | 2026-05-11T17:13:55Z |
| 11 | `0011_ble_manufacturer_id_identifier_type_extension` | 2026-05-11T17:14:09Z |
| 12 | `0012_paired_identifier_id` | 2026-05-11T17:14:26Z |
| 13 | `0013_drone_rid_and_proprietary_protocol_identifier_types_extension` | 2026-05-11T17:14:50Z |
| 14 | `0014_surveillance_metadata_identifier_types_extension` | 2026-05-11T17:15:09Z |
| 15 | `0015_primary_registry_source_type_extension` | 2026-05-11T23:10:37Z |
| 16 | `0016_license_column` | 2026-05-12T17:41:41Z |
| 17 | `0017_source_reclassifications` | 2026-05-14T02:22:23Z |
| 18 | `0018_identifier_types_extension_batch` | 2026-05-14T05:47:15Z |
| 19 | `0019_identifier_types_round2` | 2026-05-14T17:24:59Z |

#### Indexes (1 index per current schema)

Primary on `(version)`. No additional indexes (small ledger; full-table scan acceptable).

#### Composition with METHODOLOGY + bible rules

- **Amendment-log discipline composition**: every schema-changing migration lands paired with a `BIBLE_AMENDMENTS.md` entry; the `schema_version` row is the runtime record of which migrations have been applied.
- **Forward-only invariant**: migrations are never rolled back; version monotonically increases.

### §4.14. `source_reclassifications` (band-correction audit)

Per-row source-band reclassification audit, added by migration 0017 to support the post-CP15 `primary_registry` band-correction sweeps (canonical case study: MAC-94+sweeps moving Wave-A FAA RID rows from `crowdsourced` → `primary_registry` per CP15 §8.2 strict reading). Append-only — corrective sub-sweeps land with distinct `sweep_event_id` values rather than mutating parent-sweep audit rows. Row count verified live 2026-05-15T01:57:18Z: **809**.

#### Columns

| Column | Type | NOT NULL | Default | Description |
|---|---|---|---|---|
| `id` | INTEGER | yes (PK) | autoincrement | Primary key. |
| `identifier_id` | INTEGER | yes | — | FK → `identifiers(id)` ON DELETE CASCADE. The reclassified row. |
| `sweep_event_id` | TEXT | yes | — | Groups all rows in one sweep dispatch (e.g., `'MAC-94-sweep-1'`). Same shape convention as `argus_run_id` for exports. Corrective sub-sweeps use a distinct `sweep_event_id` per the audit-table append-don't-mutate sub-rule. |
| `pre_source_url` | TEXT | yes | — | Source URL at sweep-start (snapshot). |
| `post_source_url` | TEXT | yes | — | Source URL after reclassification. |
| `pre_source_type` | TEXT | yes | — | Source-type band at sweep-start. |
| `post_source_type` | TEXT | yes | — | Source-type band after reclassification. |
| `pre_confidence` | INTEGER | yes | — | CHECK `BETWEEN 0 AND 100`. Confidence at sweep-start. |
| `post_confidence` | INTEGER | yes | — | CHECK `BETWEEN 0 AND 100`. Confidence after reclassification. |
| `reclassification_reason` | TEXT | yes | — | Per-row substantive rationale. Convention (NOT schema-enforced beyond NOT NULL): self-explanatory at row-level WITHOUT cross-referencing the dispatch — board's MAC-88 a1dab600 §2 refinement. |
| `reclassification_anchor` | TEXT | yes | — | CP / bible commit / dispatch citation (audit anchor). |
| `reclassified_at` | DATETIME | yes | `CURRENT_TIMESTAMP` | UTC timestamp of the reclassification. |
| `notes` | TEXT | no | NULL | Optional additional context. |

#### Composition with METHODOLOGY + bible rules

- **§11 #8 (no confidence drift) audit composition**: every confidence/source-band correction lands one row per affected identifier; the audit record proves the correction was deliberate + substantively justified rather than confidence drift.
- **Append-don't-mutate sub-rule**: corrective sub-sweeps (when a CEO refinement comment races a worker commit) MUST use a distinct `sweep_event_id` and append new rows rather than mutating parent-sweep audit rows. Codified at MAC-96→MAC-98 c121bec→c12bedd. See `BIBLE_AMENDMENTS.md` SAR-13 §S.3 for the per-shape mapper precedent.

## §5. Enum reference (consolidated)

Canonical enum-value rosters across the schema, verified on-disk via `PRAGMA table_info()` + CHECK-extract from `sqlite_master.sql` at the post-CP21-round-2 v1.0.0 state (`schema_version=19`, verified live 2026-05-15T01:57:18Z).

### §5.1. `identifiers.identifier_type` — 48 values

The cumulative roster across migrations 0001–0019 (matches the bible §4.4 Lynceus mapping table at CP21 close — 48 entries). Distinct values currently present in `identifiers` (post-promotion): 38 of the 48 (the remaining 10 are codified at the schema layer but have not yet promoted any rows; CP14/CP16/CP21 architectural-separation posture lets the enum extend ahead of first-promotion).

Baseline (migration 0001): `oui`, `mac`, `mac_range`, `bssid`, `ssid_exact`, `ssid_pattern`, `ble_uuid`, `ble_service`, `device_fingerprint`.

Migration 0009: `ble_local_name`, `ble_characteristic`, `product_family_codename`.

Migration 0011: `ble_manufacturer_id`.

Migration 0013: `drone_id_prefix`, `icao_24bit_address`, `rf_channel`, `burst_cadence_ms`, `bandwidth_mhz`, `device_class_id`, `rf_burst_duration`, `rf_protocol_constant`, `wifi_aware_service_name`, `wifi_ie_element_id`, `bluetooth_le_pdu_type`, `wifi_frame_control_subtype`, `wifi_nan_param_signature`.

Migration 0014: `alpr_model`.

Migration 0018 (CP21 round-1): `ble_protocol_byte_table`, `ble_service_uuid`, `ble_company_id`, `frequency_band`, `ble_protocol_byte`, `operator_profile`, `x509_cert_sha256_prefix`, `ble_adv_interval`, `ble_payload_offset`, `firmware_sha256_hash`, `network_endpoint`, `firmware_image_variant`, `qualcomm_chip_format_id`, `firmware_branded_string`.

Migration 0019 (CP21 round-2): `asdstan_message_type`, `asdstan_enum_value`, `dji_protocol_struct_format`, `gpt_partition_uuid`, `chipset_codename`, `firmware_build_string`, `firmware_build_uuid`.

Forward-codified (NOT in current CHECK): `vendor_template_namespace_uuid` per the forward-looking-codification caveat in the vendor-companion-app sub-banding amendment; lands at first-promotion-time.

### §5.2. `identifiers.device_category` + `behavioral_signatures.device_category` — 12 values

`alpr`, `imsi_catcher`, `body_cam`, `police_radio`, `drone`, `gunshot_detect`, `hacking_tool`, `covert_cam`, `gps_tracker`, `face_recog`, `drone_detect`, `unknown`.

### §5.3. `identifiers.source_type` + `raw_observations.source_type` (mirror) — 10 values

`official`, `regulatory`, `procurement`, `academic`, `foia`, `crowdsourced`, `inferred`, `manufacturer_doc`, `manufacturer_app`, `primary_registry`.

### §5.4. `procurement_records.source_type` — 4-value subset

`procurement`, `foia`, `regulatory`, `official`.

### §5.5. `council_minutes_matters.source_type` — 3-value subset

`procurement`, `foia`, `official`.

### §5.6. `deployment_observations.license` — 5 values

`ODbL-1.0`, `CC-BY-NC-SA-4.0`, `public-domain`, `foia`, `unspecified`.

### §5.7. `identifiers.pair_kind` — 4 non-NULL values + NULL

`la_bit_flip`, `frdid_sibling`, `vendor_as_container`, `firmware_generation`, NULL.

Forward-codified (NOT in current CHECK): `static_mac_tracker` is a deferred item; lands at future canonical-bible §-text codification.

### §5.8. `behavioral_signatures.cellular_generation` — 4 non-NULL values + NULL

`2G`, `3G`, `4G`, `5G_NSA`, NULL.

### §5.9. `wigle_anchor_priority.priority_tier` + `derivation_method`

- `priority_tier`: 1, 2, 3, 4, 5 (CHECK `BETWEEN 1 AND 5`).
- `derivation_method`: `atlas_state_column`, `deflock_reverse_geocode`.

### §5.10. Confidence-shape divergence

See §6.2 for the cross-table confidence-shape divergence synthesis (4 shapes: identifiers / procurement_records / council_minutes_matters / behavioral_signatures).

## §6. Cross-references to METHODOLOGY

### §6.1. Provenance + confidence

- METHODOLOGY §5 (Confidence model): source-type bands + corroboration boost + ceiling rule define how `identifiers.confidence` and cross-table corroboration contributions compose.
- METHODOLOGY §6 (Dedup logic): how duplicate rows collapse to a canonical row; superseded-row preservation per §6.4.
- METHODOLOGY §7 (Provenance discipline): `raw_observations` as source-of-truth (§7.1); `source_url` discipline (§7.2); no-fabrication (§7.3); third-party-citation-lineage boundary (§7.4); no-PII (§7.5); amendment-log discipline (§7.6).

### §6.2. Confidence-shape divergence across tables

Four confidence shapes ship in v1.0.0, each defensible per its domain. Two-axis distinction: schema-level CHECK constraint vs operational cap.

| Table | Schema-level CHECK | Operational cap | Rationale |
|---|---|---|---|
| `identifiers.confidence` | `BETWEEN 0 AND 100` | **99** (METHODOLOGY §5 humility-margin invariant; enforced at corroboration-boost + ceiling-rule layers) | Identifier-attribution carries fabrication-risk residual; perfect-certainty never claimed |
| `procurement_records.confidence` | `BETWEEN 0 AND 100` | 100 (no operational cap below schema) | Contract-execution is discrete event; no humility-margin needed |
| `council_minutes_matters.confidence` | discrete `IN (70, 75, 80)` | (schema-level; no operational adjustment) | Legistar item-grading sub-rule; discrete tier reflects matter shape + vendor-specificity |
| `behavioral_signatures.confidence` | `BETWEEN 0 AND 100` | TBD at promotion per the intake-time false-positive-class allowlist | (covered in §4.10) |

**Cross-table corroboration semantics**: when non-identifier-table rows (procurement / council_minutes / behavioral_signatures) corroborate `identifiers.confidence` per METHODOLOGY §5.2, the contributing-source-type ceiling applies. Per METHODOLOGY §5.6 and the canonical-bible procurement-corroboration rule: procurement records cap cross-table corroboration at confidence 85 ("Procurement records add geographic context but never raise an identifier above 85 confidence by themselves"). Council-matters contribute at the matter's discrete-grading value (70/75/80) but cap at the source-type ceiling per `source_type` band (procurement / foia / official).

### §6.3. Export shape composition

- `argus_export.json` (METHODOLOGY §5.5 standard export, ≥30 confidence): wire-observable rows excluding `device_category='unknown'` per the multi-purpose-vendor discipline.
- `argus_export_high_confidence.json` (≥70 confidence): same exclusions + the default `geographic_scope` filter (`['US']`).
- `argus_export.csv` (rich-import feed): all active rows including analytical-only.

## §7. Maintenance posture

This document updates in lockstep with schema migrations and canonical-bible amendments:

- **Schema migrations** (any `db/migrations/NNNN_*.sql` landing): the affected table sub-section in §4 updates; §5 enum reference roster updates if CHECK constraints change.
- **Canonical-bible amendments** to the schema-section enum roster: documented in `BIBLE_AMENDMENTS.md`; this document inherits via the §5 enum reference roster.
- **METHODOLOGY refinements** (any §5 confidence model, §6 dedup, §7 provenance change): §6 cross-references update; specific column descriptions in §4 may update if operational composition changes.
- **Verification discipline** at every update: `PRAGMA table_info()` + `sqlite_master.sql` CHECK-extract regex against the on-disk database. Per the 4-tier source-of-truth precedence in §1, this document is tier (4) — derived narrative — and must faithfully reflect tier (1) on-disk schema state.

Contributions touching schema or DATA_DICTIONARY content land via the standard project PR process per [CONTRIBUTING.md](CONTRIBUTING.md); substantive schema-changing PRs carry a `BIBLE_AMENDMENTS.md` entry per the amendment-log discipline.

---

## Canonical sources

Descriptive references used in this document map to canonical bible
anchors as follows. The canonical bible (`PROJECT_BIBLE.md` and the
amendment ledger `BIBLE_AMENDMENTS.md`) holds the authoritative
specification; this DATA_DICTIONARY is the derived schema-reference
narrative.

| Descriptive reference (as used in this doc) | Canonical source |
|---|---|
| promotion-gate hard rule | `PROJECT_BIBLE.md` §11 #7 |
| no-fabrication hard rule | `PROJECT_BIBLE.md` §11 #1 |
| no-PII hard rule | `PROJECT_BIBLE.md` §11 #3 |
| confidence-ceiling hard rule / third-party-citation-lineage boundary | `PROJECT_BIBLE.md` §11 #8 |
| multi-purpose-vendor discipline | `PROJECT_BIBLE.md` §11 #10 + §11 #13 |
| amendment-log discipline | `PROJECT_BIBLE.md` §11 #11 |
| Feist facts-only / canonical sentinel-key | `PROJECT_BIBLE.md` §11 #16 |
| canonical-bible LA-bit pairing rule / vendor-as-container / firmware-generation | `PROJECT_BIBLE.md` §8.4 + `BIBLE_AMENDMENTS.md` CP14 |
| canonical-bible procurement-corroboration / deployment-evidence rule | `PROJECT_BIBLE.md` §8.4 |
| FOIA discipline | `PROJECT_BIBLE.md` §11 #6 |
| source-tier hierarchy | `PROJECT_BIBLE.md` §1 + §6 |
| canonical-bible provenance discipline | `PROJECT_BIBLE.md` §8.1 |
| `source_type='primary_registry'` band introduction | `BIBLE_AMENDMENTS.md` CP15 |
| `geographic_scope` filter (default `['US']`) | `BIBLE_AMENDMENTS.md` CP7 |
| identifier-type extension cluster (migrations 0008–0010) | `BIBLE_AMENDMENTS.md` CP13 |
| migration 0011 `ble_manufacturer_id` enum extension | `BIBLE_AMENDMENTS.md` CP14 |
| forward-looking-codification caveat (vendor-companion-app sub-banding) | `BIBLE_AMENDMENTS.md` CP17 |
| vendor-disambiguation discipline | `BIBLE_AMENDMENTS.md` SAR-8 + SAR-9 |
| Legistar status-discipline / item-grading / staging sub-rules | `BIBLE_AMENDMENTS.md` SAR-5 |
| intake-time false-positive-class allowlist | `BIBLE_AMENDMENTS.md` SAR-7 |
| `argus_record_id` stable-identifier algorithm | `BIBLE_AMENDMENTS.md` SAR-10 |
| framework-string sub-rule (extraction-time FP discipline) | `BIBLE_AMENDMENTS.md` SAR-11 |
