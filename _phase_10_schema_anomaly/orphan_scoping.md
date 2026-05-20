# MAC-205 Phase 10c — orphan scoping (sid=13 + sid=14 direct-admission-bypass)

**Status:** Phase 1 scoping complete · CEO disposition pending · no rows mutated (§11 #7)
**Branch:** `v1.4.1-integration-stage-1` @ `a2aa75a`
**Schema:** migrations applied through `0026`
**Run timestamp:** 2026-05-20
**Validator:** DBArchitect (agent 6c93a466)
**Sibling thread:** MAC-202 (investigation) + MAC-204 (rebind execution) — see `_phase_10_schema_anomaly/heartbeat.md` and `rebind_heartbeat.md`

Raw evidence: paste-not-cite (§11 #1) from `db/argus.db`, no LLM citation.

---

## 1. Headline (CEO read first)

The dispatch scoped this as "**19 identifiers (533-553) admitted to sid=13 via direct-admission-bypass with zero `raw_observations` predecessors**." Phase 1 scoping confirms the orphan premise but finds two scope corrections worth surfacing before disposition:

- **Range [533,553] contains 21 identifiers, not 19** — the count of 19 was a *manufacturer-filtered* count (Flock-only). The full range is **19 Flock Safety + 2 Getac** (ids 537, 538 are Getac BWC Viewer attached to sid=14, not sid=13).
- **Both sids (13, 14) share the same admission session** (`wave_g_pre_v1`) with **identical `authority_chain`**: `MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c (migration 0009 manufacturer_app enum)`. The direct-admission is **explicitly pre-authorized** under `sources.notes.mac_55_step_2_run = "pre-auth 3 mechanical promotion 2026-05-11"`. Direct-admission was **intentional**, not a bypass bug.
- **No `extraction_runs` row** exists for sid=13 or sid=14. The wave_g_pre_v1 admission path bypassed both `raw_observations` AND `extraction_runs` — confirming that the entire dual-table provenance trail was structurally absent at admission time, not merely lost or mis-bound.

The 19 Flock + 2 Getac identifiers all carry **full per-row provenance** at the `identifiers` table level (`source_url`, `manufacturer`, `notes.apk_package`, `notes.apk_version`, `notes.sub_band`) plus admission-session provenance at the `sources` table level (`xapk_sha256`, `apk_sha256`, `version_code`, `extraction_session_reference`, `authority_chain`, `mac_55_step_2_run`). Provenance is intact end-to-end — only the `raw_observations` audit-trail layer is absent.

**Recommended disposition:** **β (codify direct-admission carve-out)**. Reasoning in §5 below.

---

## 2. Halt criteria check

| Criterion | Status | Note |
|---|---|---|
| Scope changes during scoping (not 19, or scope spills into other sids) | **TRIGGERED** | Range is 21, not 19; 2 rows belong to sid=14 (Getac BWC Viewer), not sid=13. Surfacing before disposition. |
| `raw_observations.promoted_identifier_id IN [533..553]` returns nonzero | passed | returns **0** — bypass premise confirmed |
| Any of the 19 has been superseded/downgraded | passed | zero `superseded_by` set across all 21 rows |

Halt-trigger #1 is what this document surfaces. The scope-correction is small (+2 Getac rows under same dispositional umbrella) but bible §11 #7 requires the surface before any disposition is applied.

---

## 3. Paste-not-cite — all 21 identifiers in range [533,553]

| id  | type                     | identifier (first 36c)                  | manufacturer  | source_url-host               | conf | sup_by | promotion_dispatch_ref |
|----:|--------------------------|-----------------------------------------|---------------|-------------------------------|-----:|--------|------------------------|
| 533 | ble_service              | 20c944c1-add2-42d7-a638-967ee9a26ff6    | Flock Safety  | apkpure.com/flock-safety...   | 87   | None   | none in identifiers.notes |
| 534 | ble_characteristic       | 9b51c418-d3d6-4dab-95a6-a22f3c…         | Flock Safety  | apkpure.com/flock-safety...   | 87   | None   | none |
| 535 | ble_service              | e8ccbb38-9532-46a8-9fe5-1814df…         | Flock Safety  | apkpure.com/flock-safety...   | 87   | None   | none |
| 536 | ble_characteristic       | 628913a6-8701-40ff-a3ce-8f453f…         | Flock Safety  | apkpure.com/flock-safety...   | 87   | None   | none |
| **537** | **ble_service**      | **00000000-0000-1000-1b7f-430ea1…**     | **Getac**     | **apkpure.com/getac-bwc...**  | 87   | None   | none |
| **538** | **ble_characteristic** | **0000200b-0000-1000-1b7f-430ea1…**   | **Getac**     | **apkpure.com/getac-bwc...**  | 87   | None   | none |
| 539 | ble_local_name           | Penguin                                 | Flock Safety  | apkpure.com/flock-safety...   | 82   | None   | none |
| 540 | product_family_codename  | AVICORE                                 | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 541 | product_family_codename  | CONDOR                                  | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 542 | product_family_codename  | DRONEDOCKINGSTATION                     | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 543 | product_family_codename  | DRONERADAR                              | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 544 | product_family_codename  | FALCON                                  | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 545 | product_family_codename  | FALCONHIGHWAY                           | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 546 | product_family_codename  | OWL                                     | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 547 | product_family_codename  | PICARD                                  | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 548 | product_family_codename  | PICARDPTZ                               | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 549 | product_family_codename  | RAVEN                                   | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 550 | product_family_codename  | SPARROW                                 | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 551 | product_family_codename  | TALKDOWN                                | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 552 | product_family_codename  | TRAILER                                 | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |
| 553 | product_family_codename  | WING                                    | Flock Safety  | apkpure.com/flock-safety...   | 92   | None   | none |

(**Bold rows** = Getac scope-spill outside issue's framing.)

**Aggregate partition:**

- Flock Safety: 19 rows — `[533, 534, 535, 536, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553]` (matches issue's count)
- Getac: 2 rows — `[537, 538]` (interleaved within range; bypass-pattern siblings)

**`identifier_type` breakdown across 21 rows:** 3× ble_service, 3× ble_characteristic, 1× ble_local_name, 14× product_family_codename.

---

## 4. Bypass-premise cross-checks (orphan confirmation)

| Check | SQL | Result |
|---|---|---|
| Any raw_observations FK to range | `SELECT COUNT(*) FROM raw_observations WHERE promoted_identifier_id BETWEEN 533 AND 553` | **0** ✓ |
| Any raw_observations for sid=13 | `SELECT COUNT(*) FROM raw_observations WHERE source_id=13` | **0** ✓ |
| Any raw_observations for sid=14 | `SELECT COUNT(*) FROM raw_observations WHERE source_id=14` | **0** ✓ (paste-not-cite — verified independently) |
| Any extraction_runs for sid=13 | `SELECT * FROM extraction_runs WHERE source_id=13` | **0 rows** ✓ |
| Any extraction_runs for sid=14 | `SELECT * FROM extraction_runs WHERE source_id=14` | **0 rows** ✓ |
| Any superseded/demoted rows in range | `SELECT id FROM identifiers WHERE id BETWEEN 533 AND 553 AND superseded_by IS NOT NULL` | **0 rows** ✓ |

The bypass premise is confirmed: **the entire dual-table observation+run audit trail is structurally absent for both sids**, not merely incomplete.

---

## 5. Authoring dispatch + intentionality determination

Both sources share identical admission signatures (paste-not-cite from `sources.notes`):

| field | sid=13 (Flock) | sid=14 (Getac) |
|---|---|---|
| `session_admission` | `wave_g_pre_v1` | `wave_g_pre_v1` |
| `admission_date_utc` | `2026-05-10` | `2026-05-10` |
| `extraction_session_reference` | `wave_g_pre_v1` | `wave_g_pre_v1` |
| `authority_chain` | `MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c (migration 0009 manufacturer_app enum)` | (identical) |
| `mac_55_step_2_run` | `pre-auth 3 mechanical promotion 2026-05-11` | (identical) |
| `eula_posture` | `standard-RE-clause` | (identical) |

**Determination: direct-admission was intentional and pre-authorized**, not a bypass bug.

- `mac_55_step_2_run = "pre-auth 3 mechanical promotion 2026-05-11"` is an **explicit admission-policy stamp** indicating these rows were promoted via a sanctioned mechanical-promotion path that did not pass through `raw_observations`.
- The `authority_chain` terminates at `CP13 (migration 0009 manufacturer_app enum)` — i.e., these rows were admitted *as the enum landed*, not from an observation cohort that pre-existed it.
- The pattern is **confined to wave_g_pre_v1**: of 37 apkpure-sourced identifiers in the DB, the 16 admitted *outside* the wave_g_pre_v1 session (ids 23043–23058: Hikvision, Dahua, Motorola Solutions, Parrot) all DO have `raw_observations` predecessors. The canonical pipeline exists; the wave_g_pre_v1 session explicitly opted out of it.

This is **not** a CP12-era policy carve-out per se — it is a wave_g_pre_v1 session-scoped mechanical-promotion pathway, narrower than the issue's hypothesis suggested.

---

## 6. Provenance preservation evidence (per-row + per-source)

Despite the missing `raw_observations` layer, full provenance is preserved on two complementary surfaces:

**Per-row (`identifiers.notes`):**
- `apk_package` — e.g., `com.flocksafety.hazyhiwire`
- `apk_version` — e.g., `2.4.0`
- `sub_band` — e.g., `80-95 (manufacturer_app hardcoded BLE service UUID)`
- For codenames: `category_rationale`, `marketing_name`, `firmware_codename`
- For BLE pairs: `label`, `paired_service`
- `candidate_id` (Flock-side only) — links to wave_g extraction batch keys

**Per-source (`sources.notes`):**
- `xapk_sha256` / `apk_sha256` / `xapk_size_bytes` / `apk_size_bytes` — content integrity
- `version_code`, `package_role`, `download_channel`, `apk_path_relative` — extraction artifact pointers
- `extraction_session_reference` + `authority_chain` — admission lineage
- `license` + `license_attribution` — license posture
- `mac_55_step_2_run` — admission-policy stamp

This means a future auditor can recompute the equivalent of a `raw_observations` row from `(identifiers.source_url + identifiers.notes.apk_package + identifiers.notes.apk_version + sources[matching].notes.apk_sha256)` — the data exists, only the row-shape is absent.

---

## 7. CEO disposition fork — recommendation

The issue lists three dispositions (α retro-admit / β codify carve-out / γ hybrid). Phase 1 scoping recommends:

### Recommendation: **Disposition β (codify direct-admission carve-out)**

**Reasoning:**

1. **Historical truth preservation.** The wave_g_pre_v1 session explicitly opted out of `raw_observations` under a sanctioned admission stamp (`mac_55_step_2_run = "pre-auth 3 mechanical promotion 2026-05-11"`). Retro-admit (α) would require **fabricating** `raw_observations` rows — captured_at, source_row_key, raw_payload — that the original admission structurally never produced. Per §11 #1 paste-not-cite, fabricating audit-trail rows is the wrong direction.

2. **No provenance gap to close.** All 21 rows carry full provenance at the `identifiers.notes` + `sources.notes` level. Downstream consumers (validator, exports, lynceus) see correct `source_url` + `manufacturer` + `confidence`. The audit gap is **only at the `raw_observations` row level**, which is an internal-pipeline audit-trail, not a downstream-consumer contract.

3. **Hybrid (γ) collapses to β** under inspection. The hybrid would retro-admit "rows missing source_url provenance" — but **no rows in this set are missing source_url provenance**. Every row has a valid `source_url`. So γ ⇒ β in practice.

4. **Bible amendment is the right surface.** The `raw_observations` invariant "every identifier has a raw_obs predecessor" is the right invariant for the canonical pipeline; the wave_g_pre_v1 carve-out is a one-time historical exception that should be **explicit and bounded**, not retroactively erased. Bible §11 #11 (Stage 2 amendment-log candidate) is exactly the right slot.

### Proposed carve-out shape (CEO ratifies)

If β accepted, the carve-out mechanism would be:

- **identifiers.notes** gains key `direct_admission_carve_out` with shape:
  ```json
  {
    "direct_admission_carve_out": true,
    "session_admission": "wave_g_pre_v1",
    "authority_chain": "MAC-1 ddc193cd → MAC-52 → CP12 90132fa → CP13 4e8a29c",
    "mac_55_step_2_run": "pre-auth 3 mechanical promotion 2026-05-11",
    "provenance_path": "sources.id={13|14}.notes"
  }
  ```
- Scope is bounded explicitly to the 21 rows enumerated in §3, plus a bible §4.5-adjacent paragraph encoding the carve-out as a session-scoped historical exception (not a future admission pathway).
- Audit invariant amended to: *"Every identifier has a `raw_observations` predecessor **OR** carries `notes.direct_admission_carve_out=true` referencing its `sources.notes`-level provenance."*

This would be executed as a Phase 10d child issue if CEO ratifies β (a small NOTES-only `UPDATE` on 21 rows, idempotent, plus a bible amendment-log entry).

### Recommendation against α (retro-admit)

Listing for completeness: α would require synthesizing 21 `raw_observations` rows with fabricated `captured_at`, `source_row_key`, and `raw_payload`. The captured_at would have to be back-dated (or set to current `now()` which falsifies the temporal ordering), and `raw_payload` would either be empty (defeating the audit-trail purpose) or a synthesized echo of `identifiers.notes` (a fabrication). Both are §11 #1 violations.

---

## 8. Scope-spill handling (sid=14 / Getac)

Phase 1 surfaces that the bypass-pattern spans **2 sids (13, 14)** with identical session attribution. CEO has two options:

- **Option A (recommended):** Extend MAC-205 scope to cover all 21 rows under one disposition. The defect class is identical, the admission session is identical, the disposition mechanism (carve-out flag) applies uniformly. +2 rows is trivial overhead.
- **Option B:** Spin off a parallel MAC-205a for the 2 Getac rows. Functionally identical work, two tickets, no benefit beyond paper-trail granularity.

Default recommendation: **A**.

---

## 9. No-mutation attestation

This heartbeat document is the only artifact produced by Phase 1 scoping. No `UPDATE`, `INSERT`, `DELETE`, or migration operations were issued against `db/argus.db`. No backups were taken (none required for a read-only scoping pass). `git status` confirms no staged or working-tree changes to schema or data files.

---

## 10. Next-action handoff

- **Status:** done
- **Disposition pending:** CEO ratifies α / β (recommended) / γ + scope-spill handling (A recommended / B)
- **If β + A ratified:** CEO creates MAC-205d child issue scoped to a single `UPDATE` over the 21 rows + bible amendment-log entry. DBArchitect is the right owner.
- **If α ratified:** CEO creates MAC-205d child issue for retro-admission of 21 synthesized raw_observations rows. DBArchitect would push back on §11 #1 grounds before executing.
- **No further DBArchitect action required this heartbeat.**
