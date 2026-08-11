# SETUP.md: Argus

> **TL;DR.** Argus ships the pre-generated export files under `exports/`. It does **not** ship the SQLite database: `db/argus.db` is absent from the published tree, so a fresh clone has no database to query and `argus_cli.py` will not run until you supply one. The exports are the published data artifact and need no pipeline run, so clone the repo and read them. This document covers the developer setup path: clone, verify the shipped exports, build the schema from migrations, run the tests, and regenerate the exports against a database you supply. If you just want to use the data, the [USER_GUIDE.md](../USER_GUIDE.md) is a better starting point; this document is for contributors and downstream-integration developers.

Audience: someone who just cloned the repo and wants to read the exports, or to extend the database once they have one. This includes downstream consumers (Lynceus, Rayhunter, other scanners), research collaborators, and developers extending Argus.

Verified-working against `schema_version=30` (v1.6.2 ship state, CP37 ratified). Time-to-setup for a first-time user with Python 3.11+ already installed: about 2 minutes for the export verification path in §3. The paths that need a populated database (`argus_cli.py`, export regeneration in §6) are not reachable from a clone alone; see §3.1.

For semantics (confidence bands, dedup logic, provenance discipline), read [METHODOLOGY.md](METHODOLOGY.md). For the schema (every table + every column), read [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

---

## §1. Prerequisites

- **Python 3.11+** (`python3 --version` should show ≥ 3.11). Argus is verified against CPython 3.11 and 3.12; the codebase uses standard-library features through 3.11 (no f-string-pinning, no PEP 695 generics).
- **SQLite 3.x** (bundled with Python's `sqlite3` stdlib module; no separate install needed for the read-path).
- **Git** to clone.

No external system packages required for the read-path (reading the shipped exports). The optional source-ingest pipeline (re-running upstream-data extraction from scratch) requires additional dependencies; see §5 below.

## §2. Clone

```sh
git clone https://github.com/kevwillow/argus-db.git
cd argus
```

The repo ships the canonical exports already generated under `exports/`. You can consume Argus immediately from those files without running any pipeline steps.

The repo does **not** ship `db/argus.db`. The path is absent from the published tree, and has been for every release to date, so the clone above leaves you with no database. Confirm it for yourself against the published branch rather than taking this on trust:

```sh
git ls-tree -r --name-only origin/main -- db/ | grep -c 'argus\.db'   # 0
git ls-tree -r --name-only origin/main -- exports/                    # the shipped export set
```

## §3. Verify the shipped exports

The exports are what a clone actually gives you, so they are what there is to verify. Confirm the files are present and parse:

```sh
ls -la exports/
python3 - <<'PY'
import csv, json, pathlib
for name in ("argus_export.json", "argus_export_high_confidence.json",
             "argus_export_behavioral_signatures.json"):
    doc = json.loads(pathlib.Path("exports", name).read_text())
    print(f"{name}: {len(doc['entries'])} entries")
with open("exports/argus_export.csv", newline="") as fh:
    rows = list(csv.reader(fh))
# Row 0 is a "# meta:" provenance comment, NOT the column header; row 1 is the
# header. Counting data rows as len(rows) - 1 double-counts one and is wrong.
assert rows[0][0].startswith("# meta:"), f"unexpected first row: {rows[0][:1]}"
declared = [f for f in rows[0] if "record_count=" in f][0].split("=")[1]
print(f"argus_export.csv: {len(rows) - 2} data rows (meta declares {declared})")
PY
```

Each JSON file is an object with an `entries` list whose members carry `pattern` and `pattern_type`; the CSV is the rich-import shape described in §8. The CSV's actual data-row count and the `record_count` its own meta line declares should agree, and the snippet prints both so you can see that they do. Note that `notes` values contain embedded newlines, so the file has more physical lines than records; parse it with a real CSV reader rather than counting lines.

The per-file record counts for this release are in [CHANGELOG.md](../../CHANGELOG.md) under the release heading rather than repeated here, because they move every regeneration and a number copied into this file goes stale silently.

If the files are present and parse, the shipped data works end-to-end. You can stop here for read-only consumption; this is the whole read-path.

### §3.1. The database is not included, and what that rules out

`db/argus.db` is not distributed through this repository (§2). Two consequences worth stating plainly, because both look like installation faults and neither is one:

- **`argus_cli.py` will not run from a clone.** It defaults to `db/argus.db` (`argus_cli.py:29`) and raises `argus_cli: database not found at …` when the path is absent (`argus_cli.py:51-55`). This is expected on a fresh clone, not a broken install.
- **§6 export regeneration needs a database you supply.** The export worker reads canonical rows; it cannot reconstruct them from `exports/`.

There is no route in this repository that reproduces the populated database. §4 rebuilds the schema and yields a *fresh, empty* database, and §5's upstream ingest is a research project rather than a setup step, as that section says. If you need canonical rows, ask the maintainers; do not infer a download location from this document.

Once you have supplied a database at `db/argus.db`, the commands below apply. Expected output (row counts as of `schema_version=30`, v1.6.2 ship state):

```
Argus DB: <repo>/db/argus.db
Schema version: 30 (0030_cp37_device_category_network_surveillance, applied 2026-05-25 01:26:01)
Identifiers: 41508 active / 41890 total (active = superseded_by IS NULL)
Manufacturers: 118 visible (hub) + 8 hidden (arm) = 126 total
Current phase: …

Row counts:
  identifiers: 41890
  procurement_records: 50492
  manufacturers: 126
  sources: 74
  raw_observations: 147421
  deployment_observations: 116774
  extraction_runs: 121
  conflicts: 36
  schema_version: 30

Last extraction run: id=125 agent=… started=… finished=… status=completed
```

(Note: `behavioral_signatures` is queryable directly via `sqlite3 db/argus.db "SELECT COUNT(*) FROM behavioral_signatures;"`, live count at HEAD = 201. The `argus_cli.py status` row-counts listing does not include it.)

Sample query against a known identifier (Flock Safety ALPR MAC, `id=1`):

```sh
python3 argus_cli.py query e4:aa:ea:80:a1:9b
```

Expected first line: `1 exact match(es) for e4:aa:ea:80:a1:9b:` followed by a row showing `manufacturer=Flock Safety` + `category=alpr`.

If both commands succeed, the database you supplied is wired up correctly.

## §4. Regenerate the database from migrations (optional)

If you want to verify the migration pipeline produces the same shape, or you're preparing to extend the schema, you can rebuild a fresh DB from the migration ledger.

> **Warning.** This creates a *fresh, empty* database, no row data. The ingest pipeline that populates rows from upstream sources is a separate step (§5). Don't overwrite `db/argus.db` unless you're prepared to re-run the ingest.

Build into a throwaway path first:

```sh
python3 -m db.init_db --db-path /tmp/argus_fresh.db
```

This applies all 30 migrations idempotently (32 `.sql` files on disk; two slots: `0026` + `0026a` and `0029_cp36_identifiers_source_type_enum_parity` + `0029_cp36_j5_proxy_relabel` carry two files each, both applied at the same `schema_version` step). Confirm the resulting `schema_version`:

```sh
python3 -c "import sqlite3; print(sqlite3.connect('/tmp/argus_fresh.db').execute('SELECT MAX(version) FROM schema_version').fetchone()[0])"
```

Expected output: `30`.

The migration files live at `db/migrations/0001_initial.sql` through `db/migrations/0030_cp37_*.sql`; the full ledger with applied-at timestamps is in [DATA_DICTIONARY.md](DATA_DICTIONARY.md) §4.13.

## §5. Re-running the source-ingest pipeline (advanced)

Argus's identifier rows derive from public upstream sources (IEEE OUI registry, FCC EAS, FAA Remote ID public DOC API, Bluetooth SIG company-identifier registry, EFF Atlas of Surveillance, DeFlock, SAM.gov procurement disclosure, USAspending.gov, SEC EDGAR, vendor companion-app static analysis, etc.). Each source has its own loader under `db/sources/` plus extractor logic under `db/extraction/`. Re-running the pipeline from scratch requires per-source dependencies and (for some sources) operator-side API keys or quota grants.

Per-source ingest discipline, confidence bands, and the promotion-gate hard rule are documented in [METHODOLOGY.md](METHODOLOGY.md) §3 (sources hierarchy), §5 (confidence model), and §7 (provenance discipline). Per-source license posture is at [CREDITS.md](../../CREDITS.md).

The source families that ship pinned dependency files:

```sh
pip install -r requirements-vendor-docs.txt   # vendor-companion-app static-analysis ingest
pip install -r requirements-wigle.txt         # WiGLE planning state (currently inert; awaits operator-side WiGLE quota grant)
```

There is no single "load all sources" command. Source-loading is per-source per-runbook, since most sources require operator decisions (which OUIs to ingest, which FCC grantee filters to apply, etc.). Regenerating from upstream is a separate research project rather than a setup step, and it is not a supported way to obtain the canonical row set. For a first-time user the exports under `exports/` are the intended entry point (§3), not the database.

## §6. Regenerate the exports

The canonical exports under `exports/` are produced by the export worker at `db/validation/export_lynceus.py`. This step needs a populated database, which a clone does not include (§3.1); if you only want to read the exports, they are already in the tree and this section is not required. To regenerate them against a database you have supplied:

```sh
python3 -m db.validation.export_lynceus
```

Expected: a JSON summary showing record counts for each emitted file. Inspect the regenerated artifacts:

```sh
ls -la exports/argus_export.csv exports/argus_export.json \
       exports/argus_export_high_confidence.json \
       exports/argus_export_behavioral_signatures.json
```

At `schema_version=30`, against the v1.6.2 canonical database that produced that release's exports:

| File | Records | Notes |
|---|---:|---|
| `argus_export.json` | 592 | standard alert-feed (≥30 confidence; CP7 US scope filter) |
| `argus_export_high_confidence.json` | 146 | ≥70 confidence + CP19 source_type exclusion (excludes `inferred` / `crowdsourced`) |
| `argus_export_behavioral_signatures.json` | 125 | sibling export for behavioral-signature consumers (Rayhunter target) |
| `argus_export.csv` | 41,508 | rich-import feed; unfiltered active rows; consumers apply geographic / category / confidence filters at import |

That table is a v1.6.2 anchor, kept because it is the state the numbers above were measured against. For the counts the current release ships, read the `record_count` in each artifact's own meta block, or see the export table in [`../USER_GUIDE.md`](../USER_GUIDE.md) §2, which tracks the shipped release (v1.7.0: 983 standard, 501 high-confidence, 132 behavioral, 43,088 CSV rows).

The contract for each export is codified in [PROJECT_BIBLE.md](PROJECT_BIBLE.md) §7.5 (CP11 dual-artifact + CP18 behavioral_signatures sibling + CP19 high-conf source_type exclusion + CP22 canonical timestamp format).

## §7. Run the test suite (optional)

The test suite is the highest-fidelity verification that the install works end-to-end. `pytest` is not installed in the system Python; the repo ships a virtualenv at `.venv/` containing `pytest 9.0.3`. From the repo root:

```sh
.venv/bin/python -m pytest tests/ -q
```

(Or activate the venv first via `source .venv/bin/activate` and then run `pytest tests/ -q`.)

Expected at **v1.6.5 ship (MAC-321 data promotion)**: **522 passed, 2 skipped, 0 failed.** (The v1.6.3 ship line was 523 passed / 1 skipped; the +1 skip is the `tests/test_vendor_name_disambig.py` MAC-39 smoke check, which skips because the `extraction_outputs/mac39/` artifact directory was removed by the v1.6.3 repo-hygiene cleanup commit `817c475`, the test now self-skips when the artifact is absent, exactly as in a fresh clone. The other skip is the always-skipped `tests/test_vendor_docs_extractor.py` Step-1 batch smoke check, whose `raw/vendor_docs/` batch is never tracked. CP43 itself touches no test fixtures.) If you see any **failures**, the install has drifted from the verified ship state. File an issue with the test name + traceback.

## §8. Downstream consumption pattern (Lynceus / Rayhunter / other scanners)

Downstream consumers read the JSON exports (alert-feed shape) and/or the CSV (rich-import shape) per [PROJECT_BIBLE.md](PROJECT_BIBLE.md) §7.5 dual-artifact contract:

- **Alert-feed consumers** (runtime scanners): pull `argus_export_high_confidence.json` on startup or per refresh cycle. Match on `pattern` + `pattern_type` against observed identifiers; enrich alerts with `description` + `argus_record_id` (the SAR-10 16-hex stable hash).
- **Rich-import consumers** (watchlist hydration): pull `argus_export.csv` on first install + on Argus version bumps. Apply consumer-side filters (geographic scope, device category, confidence floor) at import per the Lynceus integration spec Section 7.
- **Behavioral-signature consumers** (cellular-band scanners): pull `argus_export_behavioral_signatures.json`. Distinct from the wire-pattern-keyed Lynceus exports; threshold-rule shape per CP18 directive.

For the canonical Lynceus integration shape (file paths, refresh cadence, `severity_overrides.yaml` operator-side override pattern), the integration handoff bundle is referenced from [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) Correction Pass 7 / 8 / 9 / 10 / 11 / SAR-10. The post-CP22 canonical CSV timestamp format is ISO-8601 UTC with `Z` suffix (e.g. `2026-05-14T22:34:07Z`).

## §9. Cross-references

- [USER_GUIDE.md](../USER_GUIDE.md): what Argus is + how to use the exports (start here for users)
- [README.md](../../README.md): project overview + headline metrics
- [METHODOLOGY.md](METHODOLOGY.md): confidence model + dedup logic + provenance discipline
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md): full schema reference, every table + column + enum
- [PROJECT_BIBLE.md](PROJECT_BIBLE.md): canonical specification (source-of-truth at any disagreement)
- [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md): amendment ledger (Correction Pass entries + SAR series)
- [CHANGELOG.md](../../CHANGELOG.md): release ledger (v1.0.0 through v1.6.2 ship state + post-ship CP entries)
- [CREDITS.md](../../CREDITS.md): per-source attribution + upstream license chain

## §10. Common gotchas

- **README.md Quickstart references `requirements.txt`** which does not exist at the repo root. The two pinned-dependency files (`requirements-vendor-docs.txt`, `requirements-wigle.txt`) are domain-specific (vendor-app static analysis + WiGLE planning) and are not required for the read-path or for export regeneration. If you hit a `pip install -r requirements.txt` failure, skip that step; the read-path in §3 requires no install.
- **Migration count grows per release**: at v1.0.0 there were 19 migrations; at v1.5.0 there were 27; at v1.6.2 there are 30 (32 `.sql` files; two slots: `0026`/`0026a` and `0029_cp36_identifiers_source_type_enum_parity`/`0029_cp36_j5_proxy_relabel` carry two files apiece). Migration numbering is sequential and append-only; older migrations don't change.
- **`identifier_type` and `device_category` enums are CHECK-constrained**: 58 `identifier_type` values and 17 `device_category` values (CHECK-enum cardinality) as of v1.6.2. Adding new values requires a rebuild-pattern migration; see [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md) Correction Pass entries (CP13/CP14/CP20/CP28/CP29/CP31/CP33/CP34/CP37) for the canonical examples. (See [`reference_readme_stats_enum_vs_populated.md`](../../docs_audit/) discipline: README/SETUP convention quotes CHECK-enum cardinality, not populated cardinality: live populated counts at HEAD are 49 / 16.)
- **Active vs total identifiers**: the `superseded_by` column tracks soft-deletes. Active rows are `superseded_by IS NULL`. Total = 41,890; active = 41,508; the gap (382 rows) is the post-MAC-217 tri-semantic mix: 342 successor-pointer demotes + 40 self-loop demotes (4 pre-MAC-217 PII self-loops + 36 MAC-291 §11 #1 strip self-loops). See [`docs/engineering/DATA_DICTIONARY.md`](DATA_DICTIONARY.md) §3.4.1.

---

## Footnote: historical schema-version reference

This document was originally authored against `schema_version=19` (v1.0.0 ship state, 2026-05-15) with 22,532 active identifiers across 34 manufacturers and 43 sources. The post-v1.0.0 ship cycles (CP20 through CP37) substantially expanded the source corpus (+31 sources to 74), manufacturer cohort (+92 manufacturers to 126), and identifier-type vocabulary (+31 enum values to 58 CHECK-constrained types). The verified-working anchors above reflect v1.6.2 (`schema_version=30`) ship state at HEAD `def7b95`.
