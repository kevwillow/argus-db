# Phase 7-bis §7.5-bis — Cross-attestation lift evaluation

**Dispatch:** [MAC-201](/MAC/issues/MAC-201) §7.5-bis
**Bible §11 #8 stance:** Validator PROPOSES; CEO ratifies. **NO LIFTS APPLIED.**

## Summary

| Sweep | Eligible rows | Lifts proposed | Notes |
|---|---:|---:|---|
| Within-identifiers cross-source (fccid.io ↔ non-fccid identifier row) | 0 / 58 | 0 | All 34 within-table cross-references are fccid.io-internal (equipment_class codes DTS/PCB/JBP/NII/DSS shared across vendors via same `sid=51`). Per CP24 (PROJECT_BIBLE.md L993), within-source re-extraction is NOT §8.3 corroboration. |
| Structural anchor (fcc_grantees `sid=7`) for grantee_code rows | 14 / 17 | 14 (proposed) | 14 grantee codes have FCC.gov EAS open-data CSV anchor (sid=7, primary_registry per CP21 line 805). |
| Structural anchor for equipment_class_code rows | 0 / 41 | 0 | No structured `equipment_class_codes` table exists. Rule-part labels (47 CFR §§15/22/90/95) live in regulation text, not in an argus authoritative table. |

## Methodology

### Independence test (CP24)

Per PROJECT_BIBLE.md L993–994 (CP24 sub-rule):

> Lift requires a genuinely independent collector — different upstream registry, different methodology

- `fccid.io` (sid=51) — third-party scrape of FCC filings; `source_type='crowdsourced'`; ceiling **75** per CP15
- `fcc_grantees` (sid=7) — FCC.gov EAS open-data CSV (`opendata.fcc.gov/resource/3b3k-34jp.csv`); primary registry of issuance per CP21 line 805; `primary_registry` band **70–85** per CP15 §8.2

Different collector (third-party scrape vs official issuer), different methodology (HTML-scrape vs CSV-export). Independence holds.

### Lift formula

Per PROJECT_BIBLE.md L795 (CP15 §8.2 sub-banding):

> When a `primary_registry` row is additionally corroborated by `regulatory` or `manufacturer_doc` sources, §8.3 corroboration formula `min(99, max(originals) + 5)` applies.

By symmetry, when a `crowdsourced` row is corroborated by a `primary_registry` anchor:

```
proposed_conf = min(99, max(75, 85) + 5) = min(99, 90) = 90
```

### Why I don't auto-apply

The 14 lifts depend on the methodology question:

> Does a STRUCTURAL anchor row (in `fcc_grantees` table) count as a §8.3 corroborating "source" the same way a parallel `identifiers` row would?

The CP31 §1 item 5 wording (PROJECT_BIBLE.md L845) says:

> §8.3 corroboration lift requires a non-fccid independent source per CP24 cross-source independence.

That sentence is **permissive** — IF there's a non-fccid independent source, lift can apply. It does NOT specify the source must be a parallel `identifiers` row. fcc_grantees(sid=7) qualifies as "non-fccid independent source" by every CP24 independence test, BUT this is the first lift case under CP31 §1 item 5 and is precedent-setting. §11 #8 cardinal rule applies: Validator proposes, CEO ratifies.

## 14 lift candidates (proposed conf=75 → 90)

| identifier_id | grantee_code | manufacturer | fcc_grantees grantee_name (sid=7 anchor) |
|--------------:|:-------------|:-------------|:-----------------------------------------|
| 35684 | ABY | Motorola Solutions | Motorola Solutions, Inc. |
| 35686 | ABZ | Motorola Solutions | Motorola Solutions, Inc. |
| 35690 | ARQ | Motorola Solutions | Motorola Solutions, Inc. |
| 35693 | MKM | Motorola Solutions | Motorola Solutions, Inc. |
| 35695 | N7N | Sierra Wireless | Sierra Wireless Inc. |
| 35711 | EL5 | Harris | Harris Corporation |
| 35713 | LL9 | Sierra Wireless | Sierra Wireless Inc |
| 35715 | PNF | Sierra Wireless | Sierra Wireless, Inc |
| 35718 | NK7 | Harris | Harris Corporation |
| 35720 | QQL | Sierra Wireless | Sierra Wireless, Inc. |
| 35723 | TWV | Sierra Wireless | Sierra Wireless, Inc. |
| 35725 | UXX | Cradlepoint | Cradlepoint, Inc. |
| 35731 | X4G | Axon | Axon Enterprise, Inc |
| 35737 | YJV | WatchGuard | Enforcement Video, LLC (d.b.a. WatchGuard Video) |

All 14 fcc_grantees(sid=7) rows reference `https://opendata.fcc.gov/resource/3b3k-34jp.csv?$limit=20000` — the FCC.gov EAS open-data CSV anchor.

## 3 grantee_code rows with NO lift

| identifier_id | grantee_code | manufacturer | Reason |
|--------------:|:-------------|:-------------|:-------|
| 35699 | 2AG | Parrot Automotive | Not in fcc_grantees (5-char modern grantee; section_7_2_halt_surface.md L55 flagged 2AG/2AH/2AL as net-new) |
| 35704 | 2AH | DJI | Same — not in fcc_grantees |
| 35707 | 2AL | Reveal | Same — not in fcc_grantees |

Stay at conf=75 (CP15 single-source crowdsourced ceiling). Lift becomes available if/when a future dispatch ingests the 3 missing grantee codes into fcc_grantees.

## 41 equipment_class_code rows — no lift

No structural anchor table for FCC EAS rule-part codes (TBC/CYY/DXX/etc.) exists in argus. The equivalent authoritative anchor would be the relevant FCC rule (47 CFR §15.247 for `DTS`, etc.) — these live in the CFR text, not in a structured argus table. All 41 rows stay at conf=75.

## CEO ratification asks

1. **Methodology Q:** does a `fcc_grantees`-table structural anchor count as a §8.3 corroborating source for a same-grantee_code `identifiers` row? (Validator's read: yes, per CP24 independence test + CP31 §1 item 5 permissive wording. But this is the first precedent.)
2. **Lift target Q:** if yes, is 90 the right target? Formula `min(99, max(75, 85) + 5) = 90` assumes the fcc_grantees anchor is treated as primary_registry @ 85 (top of band). Alternative readings: 80 (mid-band), 85 (ceiling, no +5 lift), 90 (full +5 lift).
3. **2AG/2AH/2AL Q:** ratify they stay at 75 pending fcc_grantees ingest of those 3 codes (no action needed today).
4. **Equipment_class Q:** ratify no-lift policy for equipment_class_code rows in absence of a structured argus anchor table.

If ratified, lifts are applied by a follow-on transaction with §11 #8 audit trail in `notes.confidence_history[]`.

## Provenance & re-runnability

- This evaluation reads only from existing `identifiers` + `fcc_grantees` + `raw_observations` rows; zero writes to DB.
- Output: `_phase_7_bis_fccid/lift_evaluation_proposal.json` (machine-readable proposal).
- Re-running this script produces identical proposal output (idempotent read).
