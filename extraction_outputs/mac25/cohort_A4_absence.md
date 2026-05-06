# Cohort A4 absence documentation (Wave-A Step-2 / MAC-25)

**Per dispatch §16 + Bible §11 #1 (no fabrication):** A4 absence-documented unconditionally based on Step-1.5b corpus-shape ground truth. No `raw_observations` rows staged from cohort_A4. Phase-5 reconcile owns potential A4 reopen if A2+A5 yields exceed projection (per dispatch §"Step-2.1 ratification proposal candidates" #1).

## Verbatim re-quote of Step-1.5b corpus-shape evidence

From `logs/mac23_step1.5b_byte_level_survey_20260505T234132Z.txt`:

```
cohort        files      bytes  mac_anch  ble_uuid  fcc_t  ssid_kw  cred_kw  pii  repos
cohort_A4        93     458494         0         3      0        4        3   13     93
```

## Disambig regression (Ratifications 1+2 codified) applied to A4

From `logs/mac25_step2_0_disambig_regression_20260505T235749Z.json`:

- 3 ble_uuid_anchored hits in A4 corpus surface, all FP-class (URL-context excluded by Ratification 2)
  - Drop reasons: `url_context_excluder:/assets/` (GitHub asset URLs)
- 0 mac_anch (vendor-prox-gated)
- 0 fcc_id_anchored
- **4 ssid_kw + 3 cred_kw raw counts** — keyword-only, NOT anchored
  identifier matches. These would surface only as keyword-context
  candidates without an actual identifier value attached.

## Methodology finding

A4 cohort = 93 generic-vendor-search repos × top-3 file shortlist. Broader
sweep beyond cop-car cluster A1 / third-party-recon A2 / Hak5-community A3.

Corpus-reality: 100% of regex surface is GitHub-asset FP class
(per-Step-1.5b methodology), 4 ssid_kw + 3 cred_kw are keyword-only counts
without paired identifier values. Per dispatch §16: A4 raw `ssid_kw=4` +
`cred_kw=3` reopen DEFERRED to Phase-5 reconcile if A2+A5 yields exceed
projection.

## A2+A5 actual yield vs Phase-5 reopen condition

| cohort | mid | trip | actual | trip evaluation |
|---|---:|---:|---:|---|
| A2 | 110 | ≤55 | 1 row | TRIPPED (below floor) |
| A5 | 50 | ≤25 | 0 rows | TRIPPED (below floor) |

A2+A5 yields are FAR BELOW projection. The Phase-5 A4 reopen condition
("A2+A5 yields exceed projection") is NOT met. A4 absence-documentation
stands.

## extraction_runs.notes

No `extraction_runs` row staged for A4. This file IS the audit trail
per Bible §11 #1.

## Refs

- [MAC-25](/MAC/issues/MAC-25) dispatch §16 (A4 absence-documented unconditional) + Step-2.1 ratification proposal #1
- [MAC-23](/MAC/issues/MAC-23) Step-1.5b survey (`logs/mac23_step1.5b_byte_level_survey_20260505T234132Z.{txt,json}`)
- Codified disambig: `db/extraction/ble_uuid_disambig.py` (Ratification 2) + `db/extraction/fcc_grantees_allowlist.py` (Ratification 1)
- Disambig regression artifact: `logs/mac25_step2_0_disambig_regression_20260505T235749Z.json`
