# §7.5-bis 14-row 75→85 lift — application log

**Issue:** [MAC-201](/MAC/issues/MAC-201) — Phase 7-bis Wave I.14b+I.14c re-dispatch
**CEO ratification:** MAC-201 comment `2af00858-6848-4602-ac96-0a25f5e11a1d` at 2026-05-20T23:15:31Z
**Apply script:** `_phase_7_bis_fccid/apply_section_7_5_bis_lift.py`
**Sub-rule:** §8.3 structural-anchor (anchor_conf=80) — first precedent, queued for CP32 codification
**Formula:** §8.3 = `min(99, max(75, anchor_conf) + 5)` → 75 → 85

## Pre / post

| Metric | Pre | Post | Δ |
|---|---:|---:|---:|
| `fcc_grantee_code` @ conf=75 | 17 | 3 | −14 |
| `fcc_grantee_code` @ conf=85 | 0 | **14** | **+14** |
| `fcc_grantee_code` total active | 17 | 17 | 0 |
| identifiers total active | 34,968 | 34,968 | 0 |
| Rows with `notes.section_8_3_lift.anchor_table='fcc_grantees'` | 0 | **14** | **+14** |

## 14 lifted rows (anchor_grantee_name from fcc_grantees join)

| identifier | conf | anchor_grantee_name |
|---|---:|---|
| ABY | 85 | `Motorola Solutions, Inc.` |
| ABZ | 85 | `Motorola Solutions, Inc.` |
| ARQ | 85 | `Motorola Solutions, Inc.` |
| MKM | 85 | `Motorola Solutions, Inc.` |
| N7N | 85 | `Sierra Wireless Inc.` |
| LL9 | 85 | `Sierra Wireless Inc` |
| PNF | 85 | `Sierra Wireless, Inc` |
| QQL | 85 | `Sierra Wireless, Inc.` |
| TWV | 85 | `Sierra Wireless, Inc.` |
| EL5 | 85 | `Harris Corporation` |
| NK7 | 85 | `Harris Corporation` |
| UXX | 85 | `Cradlepoint, Inc.` |
| X4G | 85 | `Axon Enterprise, Inc` |
| YJV | 85 | `Enforcement Video, LLC (d.b.a. WatchGuard Video)` |

Names sourced live from `fcc_grantees.grantee_name` via the `anchor_grantee_name` subquery in the UPDATE; exact strings (with their varying punctuation/suffix conventions across FCC submissions) persisted into `notes.section_8_3_lift.anchor_grantee_name` per row. Five distinct Sierra Wireless name variants confirm SAR-9 canonical+alias resolution correctness — the routing rule absorbs `Inc`/`Inc.`/`, Inc`/`, Inc.` permutations.

## 3 codes excluded (no fcc_grantees anchor)

| identifier | conf | reason |
|---|---:|---|
| 2AG | 75 | net-new grantee; not in fcc_grantees today (CP31 §6 follow-up) |
| 2AH | 75 | net-new grantee; not in fcc_grantees today |
| 2AL | 75 | net-new grantee; not in fcc_grantees today |

If a future FCC opendata re-ingest brings 2AG/2AH/2AL into `fcc_grantees`, they become §7.5-bis candidates at that time.

## 0 lifts on equipment_class_code

41 `equipment_class_code` rows stay at conf=75. No `equipment_class_codes` structural anchor table exists in argus (CFR rule-parts live in regulation prose, not a structured registry). Ratified as-is.

## Audit-trail JSON (spot-check on ABY)

```json
{
  "lift_at_utc": "2026-05-20 23:17:32",
  "pre_conf": 75,
  "post_conf": 85,
  "anchor_table": "fcc_grantees",
  "anchor_source_id": 7,
  "anchor_grantee_code": "ABY",
  "anchor_grantee_name": "Motorola Solutions, Inc.",
  "sub_rule": "structural_anchor (anchor_conf=80)",
  "cp_anchor": "CP32-pending",
  "ratification_issue": "MAC-201",
  "precedent_class": "first_section_7_5_bis_lift"
}
```

## Idempotency

Re-applying `apply_section_7_5_bis_lift.py` after the first commit affects 0 rows. The `WHERE confidence = 75` guard combined with `superseded_by IS NULL` prevents double-application; the `json_set` payload remains stable across re-runs because all 14 candidates have already moved off `confidence=75`.

## Discipline envelope

| Rule | Outcome |
|------|---------|
| §11 #1 (no fabrication) | Honored — `anchor_grantee_name` sourced from live `fcc_grantees` join, not hand-coded. |
| §11 #7 (provenance) | Honored — each lifted row retains its existing `raw_observations` chain (sid=51) AND now carries an audit trail of the anchor (`anchor_table`, `anchor_source_id`, `anchor_grantee_code`, `anchor_grantee_name`). |
| §11 #8 (no confidence drift) | Honored — lift is CEO-ratified at MAC-201 comment `2af00858`. Formula-bound (§8.3 with anchor_conf=80). 3 unsupported codes correctly excluded. |
| §11 #11 (amendment-log) | New sub-rule surfaced; ratifier (CEO) queued for CP32 codification per the ratification comment. |
| CP15 ceiling | Respected — 14 rows now at 85 reflect §8.3 lift, not a CP15 breach. The 3 unsupported rows remain at the CP15 single-source ceiling. |

## Next action

Validator: comment back to MAC-201 with post-commit counts + SHA + idempotency confirmation, then close MAC-201.
