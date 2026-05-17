# Schema-v21 Migration Audit — Patch Cycle 1, Patch 1.5

**Dispatch:** MAC-101 §2 pre-flight gate
**Audited at:** 2026-05-17 (wave dispatch day)
**DB:** `argus/db/argus.db`
**Schema version:** **21** (latest migration: `0021_procurement_vendor_canonical_normalized`, applied 2026-05-17 05:07:32 UTC)
**Auditor:** Claude Code (CC)
**Outcome:** **DRIFT DETECTED** — one Patch 1.2 blocker (HIGH), two doc-drift findings (LOW). CEO must draft Patch 1.6 before proceeding to Step 2 application of Patches 1.1–1.4 as written.

---

## §1 — Migration content review (0020 + 0021)

### 0020_source_type_enum_extension (applied 2026-05-17 05:07:17)

- **Effect:** SQLite table-rebuild of `sources` table. Adds 3 net-new values to the `source_type` CHECK enum.
- **Cumulative CHECK (13 values; verified verbatim against live schema):**
  - Pre-CP13 (8): `official, regulatory, procurement, academic, foia, crowdsourced, inferred, manufacturer_doc`
  - CP13 (1): `manufacturer_app`
  - CP15 (1): `primary_registry`
  - CP23 — this migration (3): `judicial_filing, disclosure_filing, procurement_disclosure`
- **Renames:** NONE. All 10 prior values preserved verbatim per `feedback_cumulative_check_enum_across_sequenced_migrations.md`.
- **Column shape:** unchanged from 0015 post-rebuild state. Sources table still has 7 columns + id (id, name, url, source_type, tier, last_fetched_at, last_status, notes).
- **Impact on this wave:** minimal. Every runguide uses `regulatory` and/or `crowdsourced` — both unchanged. New values may be relevant downstream for:
  - MAC-108 (Conference Proceedings) — academic vs the new judicial_filing distinction unlikely to bite
  - MAC-109 (MuckRock FOIA) — `foia` band unchanged; `procurement_disclosure` is forward-looking
  - No runguide currently writes to `judicial_filing` / `disclosure_filing` / `procurement_disclosure`.

### 0021_procurement_vendor_canonical_normalized (applied 2026-05-17 05:07:32)

- **Effect:** `ALTER TABLE procurement_records ADD COLUMN vendor_canonical_normalized TEXT NOT NULL DEFAULT ''` + supporting index `idx_procurement_records_vendor_canonical_normalized`.
- **Renames:** NONE. Critically: the migration filename "procurement_vendor_canonical_normalized" refers to the NEW column on `procurement_records`, **not** a rename of `manufacturers.canonical_name`. The filename was misleading at first read; full SQL inspection confirms no rename anywhere.
- **Impact on this wave:** minimal. MAC-109 (MuckRock FOIA) §4.2 may benefit from the new normalized join key for cross-validation against `manufacturers.canonical_name`/`aliases`. No MAC-101 impact.

---

## §2 — Patch 1.5 key-question answers

1. **Did 0020 add or rename any source_type CHECK enum values beyond CP23's set?**
   - **ADD** (3 net-new: `judicial_filing`, `disclosure_filing`, `procurement_disclosure`).
   - **NO renames.**

2. **Did 0021 rename `manufacturers.canonical_name`?**
   - **NO.** `manufacturers.canonical_name TEXT NOT NULL UNIQUE` is present verbatim. The migration filename hint was misleading.

3. **Did 0021 change `procurement_records` column shape?**
   - **YES, additive only.** +1 column `vendor_canonical_normalized TEXT NOT NULL DEFAULT ''`; +1 index. No existing column renamed or dropped.

4. **Are `fcc_grantees` columns (grantee_name, grantee_code, contact_address_state, contact_address_country) all present and named exactly as the §2.7 SQL (post-Patch-1.2) expects?**
   - **PARTIAL — DRIFT.** `grantee_name` ✓; `grantee_code` ✓; **`contact_address_state` DOES NOT EXIST**; **`contact_address_country` DOES NOT EXIST**. The actual columns are `state` and `country`. Patch 1.2's SQL block will fail with `no such column: contact_address_state` when executed against the live DB.

---

## §3 — Column-reference drift matrix

| Runguide reference | Schema-v21 truth | Drift class | Action |
|---|---|---|---|
| `schema_versions` table | `schema_version` (singular) | LOW — doc-drift | Already addressed by Patch 1.1 |
| `sources.source_type` enum (10 pre-CP23) | 13 values at v21 (10 prior + 3 net-new) | NONE — additive, no rename | Patch 1.5 OK |
| `manufacturers.canonical_name` | `TEXT NOT NULL UNIQUE` — present verbatim | NONE | OK |
| `manufacturers.aliases` | `TEXT` (comma-separated) — present verbatim | NONE | OK |
| `manufacturers.primary_category` | `TEXT` — present verbatim | NONE | OK |
| `manufacturers.notes` | `TEXT` — present verbatim | NONE | OK |
| `identifiers.identifier_type` enum | 48 values at v21 (last extensions migrations 0018/0019) | NONE in 0020/0021 | OK |
| `identifiers.manufacturer_id` (FK; per Patch 1.5 checklist) | **DOES NOT EXIST** — schema has `manufacturer TEXT` (free-form column), not an FK | LOW — doc-drift in Patch 1.5 audit checklist itself | Surface — checklist may have been forward-looking. No runguide §3 work depends on this. |
| `identifiers.confidence` | `INTEGER CHECK (confidence BETWEEN 0 AND 100)` — present | NONE | OK |
| `raw_observations.candidate_value` (per fccid.io §4.3 staging JSON) | Schema column is `candidate_identifier`, not `candidate_value` | LOW — naming mismatch in staging JSON vs schema, but the JSON is staging-only; validator handles mapping at promotion | Surface as future Patch 1.x — operator may want to align fccid.io §4.3 JSON field names with schema column names for clean promotion. Not §3-blocking. |
| `raw_observations.candidate_type, source_id, source_url, source_excerpt, notes` | All present verbatim | NONE | OK |
| `procurement_records.*` | +1 column from 0021 (vendor_canonical_normalized) | NONE — additive | OK; MAC-109 may want to read |
| `fcc_grantees.grantee_name` | present | NONE | OK |
| `fcc_grantees.grantee_code` | present | NONE | OK |
| `fcc_grantees.contact_address_state` (per Patch 1.2 SQL) | **DOES NOT EXIST** — actual column is `state` | **HIGH — blocks Patch 1.2** | **Patch 1.6 trigger** — amend Patch 1.2 SQL to use `state` |
| `fcc_grantees.contact_address_country` (per Patch 1.2 SQL) | **DOES NOT EXIST** — actual column is `country` | **HIGH — blocks Patch 1.2** | **Patch 1.6 trigger** — amend Patch 1.2 SQL to use `country` |

---

## §4 — fcc_grantees full column list (for Patch 1.6 reference)

```
id                  INTEGER PK
source_id           INTEGER NOT NULL → sources(id)
extraction_run_id   INTEGER NOT NULL → extraction_runs(id)
source_url          TEXT NOT NULL
source_row_key      TEXT NOT NULL                    -- = grantee_code (Q3)
grantee_code        TEXT NOT NULL                    -- 3-5 char alphanumeric prefix
grantee_name        TEXT NOT NULL                    -- corporate registrant
mailing_address     TEXT
po_box              TEXT
city                TEXT
state               TEXT                              -- US state name or N/A  ← was Patch-1.2-mis-named "contact_address_state"
country             TEXT                              -- country name (text, not ISO)  ← was Patch-1.2-mis-named "contact_address_country"
zip_code            TEXT
contact_name        TEXT                              -- corporate compliance contact (Q4 stage-as-is)
date_received       TEXT NOT NULL                    -- ISO date 'YYYY-MM-DD'
source_excerpt      TEXT (≤200 char CHECK)
notes               TEXT                              -- JSON: raw_row passthrough + Phase-5 hooks
captured_at         TEXT NOT NULL DEFAULT now()
processed_at        TEXT
UNIQUE (source_id, source_row_key)
```

Row count: **50,153** grantees.

---

## §5 — Patch 1.6 — recommended scope (CEO drafts)

Single mechanical SQL correction inside Patch 1.2's amended SQL block:

**Find (in Patch 1.2):**
```sql
SELECT grantee_code, grantee_name, contact_address_state, contact_address_country
FROM fcc_grantees
WHERE grantee_name LIKE '%Flock Safety%'
   OR ...
```

**Replace with:**
```sql
SELECT grantee_code, grantee_name, state, country
FROM fcc_grantees
WHERE grantee_name LIKE '%Flock Safety%'
   OR ...
```

Same correction applies inside the Patch 1.3 §2.7.1 disambiguation block (`SELECT grantee_code, grantee_name, contact_address_state, contact_address_country` → `state, country`).

The Patch 1.3 step-4 JSON shape (`address` as a single string) doesn't need amendment — that's a derived/concatenated value, not a direct column reference.

**Optional addendum** the CEO may want to bundle into Patch 1.6:
- Align the fccid.io §4.3 staging-JSON `candidate_value` field name with the schema column name `candidate_identifier`. Or document explicitly that staging-JSON uses denormalized names and validator handles the mapping. Either is fine; doc-drift only.
- Update the Patch 1.5 audit checklist's `identifiers.manufacturer_id` row — that column does not exist at v21; either replace with `identifiers.manufacturer` (the free-form TEXT column that does exist) or drop the row.

---

## §6 — Schema_version history (latest 10)

```
v 21  0021_procurement_vendor_canonical_normalized           2026-05-17 05:07:32
v 20  0020_source_type_enum_extension                        2026-05-17 05:07:17
v 19  0019_identifier_types_round2                           2026-05-14 17:24:59
v 18  0018_identifier_types_extension_batch                  2026-05-14 05:47:15
v 17  0017_source_reclassifications                          2026-05-14 02:22:23
v 16  0016_license_column                                    2026-05-12 17:41:41
v 15  0015_primary_registry_source_type_extension            2026-05-11 23:10:37
v 14  0014_surveillance_metadata_identifier_types_extension  2026-05-11 17:15:09
v 13  0013_drone_rid_and_proprietary_protocol_identifier_types_extension  2026-05-11 17:14:50
v 12  0012_paired_identifier_id                              2026-05-11 17:14:26
```

---

## §7 — DB rowcounts at audit time

| Table | Rows |
|---|---|
| sources | 50 |
| manufacturers | 35 |
| identifiers | 22,613 |
| raw_observations | 133,134 |
| procurement_records | 46,043 |
| fcc_grantees | 50,153 |

---

## §8 — Audit-procedure-drift note (non-blocking)

The Patch 1.5 dispatch dump command uses `migrations/0020_...` (relative path with no `db/` prefix). Actual location is `db/migrations/0020_...`. Worked around at audit time by reading the files directly; suggest amending the Patch 1.5 dump shell block to `cat db/migrations/0020_...` for future audit-procedure repeatability.

`sqlite3` CLI is also not on this host's PATH. Audit was executed via `python3 -c "import sqlite3; ..."`. The Patch 1.5 dump command's `.schema` calls and `sqlite3 db/argus.db "..."` calls would need either CLI install OR a python3 equivalent script wrapper.

---

## §9 — Halt decision

Per the Patch Cycle 1 dispatch's strict ordering:
> **STOP after Step 1 even if audit shows no drift. CEO check-in required: zero-drift means proceed to Step 2; drift means CEO drafts Patch 1.6.**

Audit shows **drift**. Halting per dispatch instruction. Step 2 application of Patches 1.1–1.4 should NOT proceed until Patch 1.6 amends the column references in Patch 1.2 + Patch 1.3 SQL blocks.

**CEO action required:** draft Patch 1.6 with the §5 column-reference correction (`contact_address_state`/`contact_address_country` → `state`/`country`); decide on optional addenda. Reply with the patch text or with "proceed under runtime alias-resolution" if you'd rather have CC translate the column names at SQL-build time.

**State after this halt:**
- `extraction_outputs/_patch_cycle_1/schema_v21_audit.md` — this file
- `extraction_outputs/_patch_cycle_1/` — directory exists, otherwise empty
- `.gitignore` — UNCHANGED (Step 3 not yet executed)
- `extraction_outputs/fccid_io_admission/` — does not yet exist (Step 4 disambig audit not yet executed)
- No git commits made (Step 2 not yet executed)
- No network traffic to fccid.io or FCC.gov since the §2.6 endpoint-verify in pre-flight
