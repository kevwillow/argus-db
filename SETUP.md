# SETUP.md — Argus

This document walks through getting Argus running on a fresh machine. Audience: someone who just cloned the repo and wants to query, export, or extend the database. Could be a downstream consumer (Lynceus, Rayhunter, another scanner), a research collaborator, or a curious developer.

For the full picture of *what* Argus is and *why*, read [README.md](README.md). For the *semantics* (confidence bands, dedup logic, provenance discipline), read [METHODOLOGY.md](METHODOLOGY.md). For the *schema* (every table + every column), read [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

Verified-working as of 2026-05-15 against `schema_version=19` (commit `33dc318`). Time-to-setup for a first-time user with Python 3.11+ already installed: ~2 minutes for the database-init path, ~5 minutes if you want to regenerate the exports yourself.

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

The repo ships with `db/argus.db` already populated (`schema_version=19`, 22,532 active identifiers) and the four canonical exports already generated under `exports/`. You can query and consume Argus immediately without running any pipeline steps.

## §3. Verify the shipped database

Confirm the cloned database is intact:

```sh
python3 argus_cli.py status
```

Expected output (row counts as of `schema_version=19`):

```
Argus DB: <repo>/db/argus.db
Schema version: 19 (0019_identifier_types_round2, applied 2026-05-14 17:24:59)
…
Row counts:
  identifiers: 22612
  procurement_records: 43483
  manufacturers: 34
  sources: 43
  raw_observations: 133134
  deployment_observations: 116668
  extraction_runs: 106
  conflicts: 20
  schema_version: 19
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

This applies all 19 migrations idempotently. Confirm the resulting `schema_version`:

```sh
python3 -c "import sqlite3; print(sqlite3.connect('/tmp/argus_fresh.db').execute('SELECT MAX(version) FROM schema_version').fetchone()[0])"
```

Expected output: `19`.

The migration files live at `db/migrations/0001_initial.sql` through `db/migrations/0019_identifier_types_round2.sql`; full ledger with applied-at timestamps is in [DATA_DICTIONARY.md](DATA_DICTIONARY.md) §4.13.

## §5. Re-running the source-ingest pipeline (advanced)

Argus's identifier rows derive from public upstream sources (IEEE OUI registry, FCC EAS, FAA Remote ID public DOC API, Bluetooth SIG company-identifier registry, EFF Atlas of Surveillance, DeFlock, etc.). Each source has its own loader under `db/sources/` plus extractor logic under `db/extraction/`. Re-running the pipeline from scratch requires per-source dependencies and (for some sources) operator-side API keys or quota grants.

Per-source ingest discipline, confidence bands, and the promotion-gate hard rule are documented in [METHODOLOGY.md](METHODOLOGY.md) §3 (sources hierarchy), §5 (confidence model), and §7 (provenance discipline). Per-source license posture is at [CREDITS.md](CREDITS.md).

The two source families that ship pinned dependency files:

```sh
pip install -r requirements-vendor-docs.txt   # vendor-companion-app static-analysis ingest
pip install -r requirements-wigle.txt         # WiGLE planning state (currently inert; awaits operator-side WiGLE quota grant)
```

There is no single `lynceus-style` "load all sources" command in v1.0.0 — source-loading is per-source per-runbook, since most sources require operator decisions (which OUIs to ingest, which FCC grantee filters to apply, etc.). For a first-time user, the shipped `db/argus.db` is the v1.0.0 release artifact; regenerating from upstream is a separate research project rather than a setup step.

## §6. Regenerate the exports

The four canonical exports under `exports/` are produced by the export worker at `db/validation/export_lynceus.py`. To regenerate them against the current database:

```sh
python3 -m db.validation.export_lynceus
```

Expected: a JSON summary showing record counts for each emitted file. Inspect the regenerated artifacts:

```sh
ls -la exports/argus_export.csv exports/argus_export.json \
       exports/argus_export_high_confidence.json \
       exports/argus_export_behavioral_signatures.json
```

At `schema_version=19` against the shipped DB:

| File | Records | Notes |
|---|---:|---|
| `argus_export.json` | 494 | standard alert-feed (≥30 confidence; CP7 US scope filter) |
| `argus_export_high_confidence.json` | 113 | ≥70 confidence + CP19 source_type exclusion (excludes `inferred` / `crowdsourced`) |
| `argus_export_behavioral_signatures.json` | 55 | sibling export for behavioral-signature consumers (Rayhunter target) |
| `argus_export.csv` | 22,532 | rich-import feed; unfiltered active rows; consumers apply geographic / category / confidence filters at import |

The contract for each export is codified in [PROJECT_BIBLE.md](PROJECT_BIBLE.md) §7.5 (CP11 dual-artifact + CP18 behavioral_signatures sibling + CP19 high-conf source_type exclusion + CP22 canonical timestamp format).

## §7. Run the test suite (optional)

The test suite is the highest-fidelity verification that the install works end-to-end. From the repo root:

```sh
python3 -m pytest tests/ -q
```

Expected at `schema_version=19`: **507 tests pass.** If any test fails, the install has drifted from the verified ship state — file an issue with the test name + traceback.

## §8. Downstream consumption pattern (Lynceus / Rayhunter / other scanners)

Downstream consumers read the JSON exports (alert-feed shape) and/or the CSV (rich-import shape) per [PROJECT_BIBLE.md](PROJECT_BIBLE.md) §7.5 dual-artifact contract:

- **Alert-feed consumers** (runtime scanners): pull `argus_export_high_confidence.json` on startup or per refresh cycle. Match on `pattern` + `pattern_type` against observed identifiers; enrich alerts with `description` + `argus_record_id` (the SAR-10 16-hex stable hash).
- **Rich-import consumers** (watchlist hydration): pull `argus_export.csv` on first install + on Argus version bumps. Apply consumer-side filters (geographic scope, device category, confidence floor) at import per `Lynceus_integration_spec_for_Argus.txt` Section 7.
- **Behavioral-signature consumers** (cellular-band scanners): pull `argus_export_behavioral_signatures.json`. Distinct from the wire-pattern-keyed Lynceus exports; threshold-rule shape per CP18 directive.

For the canonical Lynceus integration shape (file paths, refresh cadence, `severity_overrides.yaml` operator-side override pattern), the v0.3 integration handoff bundle is referenced from [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) Correction Pass 7 / 8 / 9 / 10 / 11 / SAR-10. The post-CP22 canonical CSV timestamp format is ISO-8601 UTC with `Z` suffix (e.g. `2026-05-14T22:34:07Z`).

## §9. Cross-references

- [README.md](README.md) — what Argus is + status snapshot + data sources
- [METHODOLOGY.md](METHODOLOGY.md) — confidence model + dedup logic + provenance discipline
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — full schema reference, every table + column + enum
- [PROJECT_BIBLE.md](PROJECT_BIBLE.md) — canonical specification (the source-of-truth at any disagreement; see §1 precedence)
- [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) — amendment ledger (Correction Pass entries + SAR series)
- [CHANGELOG.md](CHANGELOG.md) — release ledger (v1.0.0 ship state + post-ship CP entries)
- [CREDITS.md](CREDITS.md) — per-source attribution + upstream license chain

## §10. Known surfaces (operator finding flag)

Authoring this SETUP.md surfaced one minor inconsistency worth noting:

- **README.md Quickstart references `requirements.txt`** which does not exist at the repo root. The two pinned-dependency files (`requirements-vendor-docs.txt`, `requirements-wigle.txt`) are domain-specific (vendor-app static analysis + WiGLE planning) and are not required for the read-path or for export regeneration. The Quickstart `pip install -r requirements.txt` line will fail; the read-path described in §3 of this document does not require any pip install.

This is flagged for follow-up — either the README's Quickstart should drop the `pip install -r requirements.txt` line (no general requirements file is needed for Argus's read-path), or a `requirements.txt` file should be authored aggregating the two domain-specific requirements files. SETUP.md (this document) avoids the inconsistency by not referencing a non-existent `requirements.txt` and by being explicit that no install is required for §3 verification.
