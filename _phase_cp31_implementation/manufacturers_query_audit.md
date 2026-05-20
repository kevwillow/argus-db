# CP31 — `manufacturers` consumer-path audit (4 paths + SAR-13 post-attestation)

**Date:** 2026-05-20
**Author:** Validator (agent da137694-2efe-4589-8150-828dcab881fb)
**Issue:** [MAC-199](/MAC/issues/MAC-199)
**Parent:** [MAC-184](/MAC/issues/MAC-184) (v1.4.1 Stage 1 integration) / [MAC-197](/MAC/issues/MAC-197) (CP31 plan accept `d59e6af5`)
**Predecessor:** [MAC-198](/MAC/issues/MAC-198) (DBArchitect migration 0025 landed at commit `40b166e`)

## SAR-13 post-migration pre-flight (paste-not-cite)

Schema state on branch `v1.4.1-integration-stage-1` post-`40b166e`:

```
PRAGMA table_info(manufacturers):
(0, 'id', 'INTEGER', 0, None, 1)
(1, 'canonical_name', 'TEXT', 1, None, 0)
(2, 'aliases', 'TEXT', 0, None, 0)
(3, 'primary_category', 'TEXT', 0, None, 0)
(4, 'source_url', 'TEXT', 1, None, 0)
(5, 'notes', 'TEXT', 0, None, 0)
(6, 'added_at', 'DATETIME', 1, 'CURRENT_TIMESTAMP', 0)
(7, 'parent_manufacturer_id', 'INTEGER', 0, None, 0)
(8, 'is_arm', 'BOOLEAN', 1, '0', 0)
(9, 'query_default', 'TEXT', 1, "'visible'", 0)
```

3 new columns present (`parent_manufacturer_id`, `is_arm`, `query_default`) ✓.

`identifiers.identifier_type` CHECK enum values (counted from live DDL):
**56 total** (54 pre-CP31 + 2 CP31). MAC-197 plan stated "53 (51 CP29 + 2 CP31)";
**actual pre-CP31 count was 54**, so post-CP31 count is 56, not 53. CP31's
own 2-value addition (`fcc_grantee_code`, `equipment_class_code`) is correct
and uncontested — only the pre-CP31 baseline was misstated. Surfaced for
CEO informational record; not blocking.

`identifiers.pair_kind` CHECK enum: 5 values (`la_bit_flip`, `frdid_sibling`,
`vendor_as_container`, `firmware_generation`, `fcc_grantee_equipment_class`) ✓.

`manufacturers.primary_category`: still no CHECK constraint per DBArchitect
SKIP decision in `_phase_cp31_implementation/primary_category_enum_decision.md`.
Live distinct values:

```
12  NULL
 8  body_cam
 7  alpr
 6  drone
 6  imsi_catcher
 4  hacking_tool
 2  drone_detect
 2  face_recog
 2  unknown
 1  automotive_telematics  ← Parrot Automotive arm
 1  gunshot_detect
 1  police_radio
```

`SELECT COUNT(*) FROM manufacturers WHERE is_arm = 1` → 1 ✓
`Parrot` (id=25, drone, is_arm=0, query_default=visible, parent=NULL) ✓
`Parrot Automotive` (id=222, automotive_telematics, is_arm=1, query_default=hidden_arm, parent=25) ✓

## Consumer-path intent classification

Source: `rg -l 'FROM manufacturers|JOIN manufacturers'` returned 28 files.
Classified by usage-shape, not by literal SQL string:

### A. Admission / promotion scripts (one-shot, NOT live queries — no filter needed)

These read manufacturers to admit / update rows. Arms participate by design;
adding a `WHERE query_default='visible'` would break them. **Skip filter.**

- `_phase_4_wave_i_11/apply_4_5_component_oui.py`
- `_phase_5_wave_i_12/apply_5_2_alias_enrichments.py`
- `_phase_5_wave_i_12/apply_5_3_neither_axis.py`
- `_phase_5_wave_i_12/apply_5_5_fcc_absences.py`
- `_phase_5_wave_i_12/run_preflight.py`
- `_phase_6_wave_i_14a/apply_6_2_identifier_promotions.py`
- `_phase_6_wave_i_14a/apply_6_4_alias_enrichments.py`
- `_phase_6_wave_i_14a/apply_6_5_cert_supply_chain.py`
- `_phase_7_fccid_attestations/apply_7_3_stub_absence.py`
- `_phase_7_fccid_attestations/apply_7_4_filing_url_inventory.py`
- `_phase_8_honeywell_admission/apply_phase_8_honeywell_landing.py`
- `_numerex_admission/apply_mac196_numerex_alias.py`
- `db/integrations/mac178_priority4.py`
- `db/integrations/mac178_priority5.py`
- `db/validation/mac171_sec_edgar_admission.py`
- `db/validation/mac175_sam_gov_admission.py`
- `scripts/mac181_wave_h_promotion.py`

### B. Migration + tests (not in live-query scope)

- `db/migrations/0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql`
- `tests/test_migration_0025.py`

### C. Documentation (no code change)

- `METHODOLOGY.md` (line 324)
- `PROJECT_BIBLE.md` (line 839)

### D. Live query sites — intent analysis (4 hub-only + 2 by-name + 1 cross-attest)

| File:line | Shape | Intent | Action |
| --- | --- | --- | --- |
| `db/validation/phase3_inference_candidates.py:730` | lexicon enumeration | **HUB-ONLY** — inference lexicon; arms participate via FK, not by canonical-name matching | **FILTER ADDED** |
| `db/validation/sar8_bulk_stage.py:134` | lexicon enumeration | **HUB-ONLY** — vendor-name disambig; arm canonicals would create FP matches | **FILTER ADDED** |
| `db/sources/usaspending.py:391` | lexicon enumeration | **HUB-ONLY** — USAspending API keyword list; arms searched through hub | **FILTER ADDED** |
| `db/validation/mac101_item_a_registry_xcheck.py:135` | §2.1 lexicon enumeration | **HUB-ONLY** — §2.1 reference lexicon | **FILTER ADDED** |
| `db/validation/coverage_matrix.py:412` | single-row lookup by canonical_name | **BY-NAME / NEUTRAL** — caller iterates over `identifiers.manufacturer` text and looks up alias tokens; works for either hub or arm name | Skip — neutral |
| `db/validation/wave_a_first_promotion.py:90` | single-row lookup by canonical_name | **BY-NAME / NEUTRAL** — caller passes a specific canonical_name | Skip — neutral |
| `argus_cli.py:130,134` | COUNT(*) per query_default | **HUB + ARM split** — reports both intentionally (MAC-198 added this) | Already correct — verified ✓ |

### E. Export path (§1 + §2 of MAC-199 dispatch) — architectural finding

**Finding:** `db/validation/export_lynceus.py` (which generates
`argus_export.csv`, `argus_export.json`, and `argus_export_high_confidence.json`)
**does NOT join `manufacturers`.** Its sole query against the canonical row
set is `_load_active_rows`:

```python
SELECT id, identifier, identifier_type, device_category, manufacturer,
       model, confidence, source_type, source_url, source_excerpt,
       notes, geographic_scope, first_seen, last_verified
FROM identifiers
WHERE superseded_by IS NULL
ORDER BY id ASC
```

`identifiers.manufacturer` is denormalized TEXT (column 4 in
`PRAGMA table_info(identifiers)`); there is **no `manufacturer_id` FK**.
The export reads the embedded text verbatim.

This means the dispatch's premise — "argus_export.csv joins identifiers ↔
manufacturers" — is **architecturally untrue today**. Arm-row protection is
implicit:

1. Today, no identifier carries `manufacturer = 'Parrot Automotive'` (verified:
   `SELECT … WHERE manufacturer LIKE 'Parrot%'` returns 80+ rows, all variants
   of `Parrot` / `PARROT` / `parrot`, zero on the arm canonical).
2. Therefore the arm canonical name **cannot leak into any of the three
   exports** in the current schema state.
3. Adding `WHERE query_default='visible'` to a JOIN that does not exist would
   be code without effect (and risks future surprise when a FK migration adds
   the JOIN and the predicate then over-filters).

**Forward-looking risk for CEO:** when a future migration introduces
`identifiers.manufacturer_id` as a FK to `manufacturers(id)` and the export
path migrates from denormalized text to JOIN — the arm-row filter MUST be
re-established at that time. The CP31 hub-and-spoke columns make this future
migration possible; this MAC-199 audit pre-stages the architectural
expectation so that future FK migration cannot land without a paired filter.

Recommend bible §4 + §8.2 CP31 entry note this two-state architecture
explicitly (denormalized text today; FK-with-filter post-FK-migration).

### F. `project_knowledge_search` query path (§4 of dispatch)

No callers of a literal `project_knowledge_search` symbol exist in the
repo — that interface is the LLM-context bible/methodology surface, which
is documentation, not code. The §4 audit reduces to the live-query
classification above (D). No additional filter sites identified.

## Decisions

1. **4 filters added** (D row 1-4 above). Each with an inline `CP31` comment
   citing migration 0025 + the hub-only rationale.
2. **2 by-name sites skipped** (D row 5-6) — caller controls intent.
3. **`argus_cli.py` confirmed** — MAC-198 already added correct hub+arm
   split reporting.
4. **Export path finding documented** (E) — surfaced to CEO as forward-looking
   architectural item; no code change to export_lynceus.py in CP31 scope.
5. **Tests added** — `tests/test_cp31_consumer_audit.py` exercises the
   filter-applied query semantics + the export-path arm-exclusion assertion.
   Extends `tests/test_export_lynceus.py` with the 3 future-state high-conf
   filter assertions from MAC-199 dispatch §2.

## Halt criteria — disposition

| Halt | Status |
| --- | --- |
| Migration 0025 hasn't landed (MAC-198 in flight) | Resolved — MAC-198 committed at `40b166e`; schema attested above |
| Any consumer surfaces arm-row exposure intent-analysis can't resolve | Not triggered — all 28 sites classified |
| Test assertion fails post-implementation | Pending test execution |

## Reporting reference

Argus CLI status confirms the wire-form per dispatch §3:

```
Manufacturers: 51 visible (hub) + 1 hidden (arm) = 52 total
Identifiers: 34910 active / 35252 total (active = superseded_by IS NULL)
```

## Side findings for CEO (out of MAC-199 scope; non-blocking)

1. **Stale type-mapping test.** `tests/test_export_lynceus.py::test_type_mapping_covers_every_identifier_type`
   was pre-existing failing before MAC-199 began. The `expected` set is
   locked at mig-0019 (MAC-117); it has never been extended for CP20 (mig
   0018), CP28 (mig 0023), CP29 (mig 0024), or CP31 (mig 0025).
   `IDENTIFIER_TYPE_TO_PATTERN_TYPE | DROPPED_REASONS` is currently
   missing **5 types** vs the post-CP31 enum: the 3 CP29 hostname types
   (`vendor_controlled_hostname`, `vendor_cloud_endpoint_url`,
   `vendor_controlled_hostname_deprecated`) and the 2 CP31 FCC EAS types
   (`fcc_grantee_code`, `equipment_class_code`). Currently masked
   because every row of those types in the active set has
   `device_category='unknown'` and routes via the §11 #13 gate (which
   fires before the type-mapping lookup). A non-`unknown` row of any of
   these types would KeyError out at the survivor-branch entry construction.
   **Recommend:** CP31-completion follow-up to add CP29/CP31 types to
   `DROPPED_REASONS` and refresh the test's `expected` set.

2. **`exports/` files are stale.** Current `argus_export.json._meta`:
   `source_record_count=34792`, `exported_at=2026-05-20T00:43:59Z`. Current
   DB active set: 34910 (delta = +118 from MAC-196 Numerex landing +
   CP31 schema-only migration). The exports have not been regenerated
   since MAC-196 / CP31 landed. Regenerating would also require
   refreshing `extraction_outputs/mac45/coverage_matrix_report.json`
   (the drop-assignments map driving the reconciliation gate).
   **Recommend:** schedule a coverage-matrix + export refresh pass before
   v1.4.1 cuts (likely the existing Phase 7-bis dispatch will trigger
   this anyway).

3. **Bible §2.1 `device_category` enum vs `manufacturers.primary_category`.**
   `primary_category='automotive_telematics'` is a free-form value
   (DBArchitect SKIP decision in `primary_category_enum_decision.md`).
   The §2.1 `identifiers.device_category` CHECK enum does NOT admit
   `automotive_telematics`. Plan §2 #4 assumed it would. This means
   future arm-attested identifiers pointing at Parrot Automotive cannot
   currently carry a category that semantically matches the arm's
   primary category — they'd have to fall back to existing values
   (`gps_tracker`, `drone`, `unknown`, etc.). **Recommend:** §11 #11
   amendment item — extend §2.1 `device_category` enum to admit
   `automotive_telematics` (or formalize an "infotainment / vehicle
   telematics" bucket) as a separate CP item.

4. **Future-state architectural item.** `identifiers.manufacturer` is
   denormalized TEXT today. CP31's hub-and-spoke columns make a future
   FK migration (`identifiers.manufacturer_id`) viable. When that
   migration lands, the export-path JOIN must include either:
   - `WHERE m.query_default = 'visible' OR id.manufacturer_id = m.id`
     (arm rows survive only when explicitly attested), or
   - the equivalent two-pass query
   This is the only architectural treatment that satisfies CP31 §5.2's
   "arm rows surface only when an identifier explicitly attests to the
   arm" contract under a FK schema. CP31 itself does not require this
   migration; it pre-stages the schema for it.
