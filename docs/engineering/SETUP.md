# SETUP.md — Argus

> **TL;DR.** Argus ships with a populated SQLite database (`db/argus.db`) and four pre-generated export files. You don't need to run any pipeline to use it — clone the repo and start querying. This document covers the developer setup path: clone, verify the shipped database, optionally rebuild from migrations, run the tests, and regenerate the exports. If you just want to use the data, the [USER_GUIDE.md](../USER_GUIDE.md) is a better starting point; this document is for contributors and downstream-integration developers.

Audience: someone who just cloned the repo and wants to query, export, or extend the database. This includes downstream consumers (Lynceus, Rayhunter, other scanners), research collaborators, and developers extending Argus.

Verified-working against `schema_version=27` (v1.5.0 ship state, CP33 ratified). Time-to-setup for a first-time user with Python 3.11+ already installed: about 2 minutes for the database verification path, about 5 minutes if you want to regenerate the exports yourself.

For semantics (confidence bands, dedup logic, provenance discipline), read [METHODOLOGY.md](METHODOLOGY.md). For the schema (every table + every column), read [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

---

## §1. Prerequisites

- **Python 3.11+** (`python3 --version` should show ≥ 3.11). Argus is verified against CPython 3.11 and 3.12; the codebase uses standard-library features through 3.11 (no f-string-pinning, no PEP 695 generics).
- **SQLite 3.x** (bundled with Python's `sqlite3` stdlib module; no separate install needed for the read-path).
- **Git** to clone.

No external system packages required for the read-path (querying the shipped DB or regenerating the exports). The optional source-ingest pipeline (re-running upstream-data extraction from scratch) requires additional dependencies — see §5 below.

## §2. Clone

```sh
git clone https://github.com/kevwillow/argus-db.git
cd argus
```

The repo ships with `db/argus.db` already populated (`schema_version=27`, 35,812 active identifiers) and the canonical exports already generated under `exports/`. You can query and consume Argus immediately without running any pipeline steps.

## §3. Verify the shipped database

Confirm the cloned database is intact:

```sh
python3 argus_cli.py status
```

Expected output (row counts as of `schema_version=27`, v1.5.0 ship state):

```
Argus DB: <repo>/db/argus.db
Schema version: 27 (0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac)
…
Row counts:
  identifiers: 36158 (35812 active)
  procurement_records: 46043
  manufacturers: 92
  sources: 73
  raw_observations: 147421
  deployment_observations: 116774
  extraction_runs: 119
  conflicts: 36
  behavioral_signatures: 201
  schema_version: 27
```

Sample query against a known identifier (Flock Safety ALPR MAC, `id=1`):

```sh
python3 argus_cli.py query e4:aa:ea:80:a1:9b
```

Expected first line: `1 exact match(es) for e4:aa:ea:80:a1:9b:` followed by a row showing `manufacturer=Flock Safety` + `category=alpr`.

If both commands succeed, the shipped database works end-to-end. You can stop here for read-only consumption.

## §4. Regenerate the database from migrations (optional)

If you want to verify the migration pipeline produces the same shape, or you're preparing to extend the schema, you can rebuild a fresh DB from the migration ledger.

> **Warning.** This creates a *fresh, empty* database — no row data. The ingest pipeline that populates rows from upstream sources is a separate step (§5). Don't overwrite `db/argus.db` unless you're prepared to re-run the ingest.

Build into a throwaway path first:

```sh
python3 -m db.init_db --db-path /tmp/argus_fresh.db
```

This applies all 27 migrations idempotently. Confirm the resulting `schema_version`:

```sh
python3 -c "import sqlite3; print(sqlite3.connect('/tmp/argus_fresh.db').execute('SELECT MAX(version) FROM schema_version').fetchone()[0])"
```

Expected output: `27`.

The migration files live at `db/migrations/0001_initial.sql` through `db/migrations/0027_cp33_*.sql`; the full ledger with applied-at timestamps is in [DATA_DICTIONARY.md](DATA_DICTIONARY.md) §4.13.

## §5. Re-running the source-ingest pipeline (advanced)

Argus's identifier rows derive from public upstream sources (IEEE OUI registry, FCC EAS, FAA Remote ID public DOC API, Bluetooth SIG company-identifier registry, EFF Atlas of Surveillance, DeFlock, SAM.gov procurement disclosure, USAspending.gov, SEC EDGAR, vendor companion-app static analysis, etc.). Each source has its own loader under `db/sources/` plus extractor logic under `db/extraction/`. Re-running the pipeline from scratch requires per-source dependencies and (for some sources) operator-side API keys or quota grants.

Per-source ingest discipline, confidence bands, and the promotion-gate hard rule are documented in [METHODOLOGY.md](METHODOLOGY.md) §3 (sources hierarchy), §5 (confidence model), and §7 (provenance discipline). Per-source license posture is at [CREDITS.md](../../CREDITS.md).

The source families that ship pinned dependency files:

```sh
pip install -r requirements-vendor-docs.txt   # vendor-companion-app static-analysis ingest
pip install -r requirements-wigle.txt         # WiGLE planning state (currently inert; awaits operator-side WiGLE quota grant)
```

There is no single "load all sources" command — source-loading is per-source per-runbook, since most sources require operator decisions (which OUIs to ingest, which FCC grantee filters to apply, etc.). For a first-time user, the shipped `db/argus.db` is the v1.5.0 release artifact; regenerating from upstream is a separate research project rather than a setup step.

## §6. Regenerate the exports

The canonical exports under `exports/` are produced by the export worker at `db/validation/export_lynceus.py`. To regenerate them against the current database:

```sh
python3 -m db.validation.export_lynceus
```

Expected: a JSON summary showing record counts for each emitted file. Inspect the regenerated artifacts:

```sh
ls -la exports/argus_export.csv exports/argus_export.json \
       exports/argus_export_high_confidence.json \
       exports/argus_export_behavioral_signatures.json
```

At `schema_version=27` against the shipped DB:

| File | Records | Notes |
|---|---:|---|
| `argus_export.json` | 536 | standard alert-feed (≥30 confidence; CP7 US scope filter) |
| `argus_export_high_confidence.json` | 119 | ≥70 confidence + CP19 source_type exclusion (excludes `inferred` / `crowdsourced`) |
| `argus_export_behavioral_signatures.json` | 125 | sibling export for behavioral-signature consumers (Rayhunter target) |
| `argus_export.csv` | 39,832 | rich-import feed; unfiltered active rows; consumers apply geographic / category / confidence filters at import |

The contract for each export is codified in [PROJECT_BIBLE.md](PROJECT_BIBLE.md) §7.5 (CP11 dual-artifact + CP18 behavioral_signatures sibling + CP19 high-conf source_type exclusion + CP22 canonical timestamp format).

## §7. Run the test suite (optional)

The test suite is the highest-fidelity verification that the install works end-to-end. From the repo root:

```sh
python3 -m pytest tests/ -q
```

A clean run reports all tests passing. If any test fails, the install has drifted from the verified ship state — file an issue with the test name + traceback.

## §8. Downstream consumption pattern (Lynceus / Rayhunter / other scanners)

Downstream consumers read the JSON exports (alert-feed shape) and/or the CSV (rich-import shape) per [PROJECT_BIBLE.md](PROJECT_BIBLE.md) §7.5 dual-artifact contract:

- **Alert-feed consumers** (runtime scanners): pull `argus_export_high_confidence.json` on startup or per refresh cycle. Match on `pattern` + `pattern_type` against observed identifiers; enrich alerts with `description` + `argus_record_id` (the SAR-10 16-hex stable hash).
- **Rich-import consumers** (watchlist hydration): pull `argus_export.csv` on first install + on Argus version bumps. Apply consumer-side filters (geographic scope, device category, confidence floor) at import per the Lynceus integration spec Section 7.
- **Behavioral-signature consumers** (cellular-band scanners): pull `argus_export_behavioral_signatures.json`. Distinct from the wire-pattern-keyed Lynceus exports; threshold-rule shape per CP18 directive.

For the canonical Lynceus integration shape (file paths, refresh cadence, `severity_overrides.yaml` operator-side override pattern), the integration handoff bundle is referenced from [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) Correction Pass 7 / 8 / 9 / 10 / 11 / SAR-10. The post-CP22 canonical CSV timestamp format is ISO-8601 UTC with `Z` suffix (e.g. `2026-05-14T22:34:07Z`).

## §9. Cross-references

- [USER_GUIDE.md](../USER_GUIDE.md) — what Argus is + how to use the exports (start here for users)
- [README.md](../../README.md) — project overview + headline metrics
- [METHODOLOGY.md](METHODOLOGY.md) — confidence model + dedup logic + provenance discipline
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — full schema reference, every table + column + enum
- [PROJECT_BIBLE.md](PROJECT_BIBLE.md) — canonical specification (source-of-truth at any disagreement)
- [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) — amendment ledger (Correction Pass entries + SAR series)
- [CHANGELOG.md](../../CHANGELOG.md) — release ledger (v1.0.0 through v1.5.0 ship state + post-ship CP entries)
- [CREDITS.md](../../CREDITS.md) — per-source attribution + upstream license chain

## §10. Common gotchas

- **README.md Quickstart references `requirements.txt`** which does not exist at the repo root. The two pinned-dependency files (`requirements-vendor-docs.txt`, `requirements-wigle.txt`) are domain-specific (vendor-app static analysis + WiGLE planning) and are not required for the read-path or for export regeneration. If you hit a `pip install -r requirements.txt` failure, skip that step — the read-path in §3 requires no install.
- **Migration count grows per release**: at v1.0.0 there were 19 migrations; at v1.5.0 there are 27. Migration numbering is sequential and append-only; older migrations don't change.
- **`identifier_type` and `device_category` enums are CHECK-constrained**: 57 identifier_type values and 16 device_category values as of v1.5.0. Adding new values requires a rebuild-pattern migration; see [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) Correction Pass entries (CP13/CP14/CP20/CP28/CP29/CP31/CP33) for the canonical examples.
- **Active vs total identifiers**: the `superseded_by` column tracks soft-deletes. Active rows are `superseded_by IS NULL`. Total = 36,158; active = 35,812; the gap is rows demoted via §11 #3 procedures.

---

## Footnote — historical schema-version reference

This document was originally authored against `schema_version=19` (v1.0.0 ship state, 2026-05-15, commit `33dc318`) with 22,532 active identifiers across 34 manufacturers and 43 sources. The post-v1.0.0 ship cycles (CP20 through CP33) substantially expanded the source corpus (+30 sources), manufacturer cohort (+58 manufacturers), and identifier-type vocabulary (+30 identifier_type enum values). The verified-working anchors above reflect v1.5.0 (`schema_version=27`) ship state.
