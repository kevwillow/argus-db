# Cohort A3 absence documentation (Wave-A Step-2 / MAC-25)

**Per dispatch §16 + Bible §11 #1 (no fabrication):** A3 absence-documented unconditionally based on Step-1.5b corpus-shape ground truth. No `raw_observations` rows staged from cohort_A3.

## Verbatim re-quote of Step-1.5b corpus-shape evidence

From `logs/mac23_step1.5b_byte_level_survey_20260505T234132Z.txt`:

```
cohort        files      bytes  mac_anch  ble_uuid  fcc_t  ssid_kw  cred_kw  pii  repos
cohort_A3        10     124954         0         3      0        0        0    0     10
```

## Disambig regression (Ratifications 1+2 codified) applied to A3

From `logs/mac25_step2_0_disambig_regression_20260505T235749Z.json`:

- 3 ble_uuid_anchored hits in A3 corpus surface, all FP-class (URL-context excluded by Ratification 2)
  - Drop reasons: `url_context_excluder:/assets/` (GitHub asset URLs from Hak5 community payload-fork repos)
- 0 mac_anch / 0 fcc_id_anchored / 0 ssid_kw / 0 cred_kw → 0 anchored identifiers post-disambig

## Methodology finding

A3 cohort = 10 Hak5/community payload-fork repos (Flipper-Zero-BadUSB,
my-flipper-shits, PowerShell-for-Hackers, bashbunny-payloads,
usbrubberducky-payloads, omg-payloads, wifipineapple-modules,
lanturtle-modules, packetsquirrel-payloads, sharkjack-payloads).

Corpus-reality: payload-fork READMEs reference the parent Hak5 product
families but DO NOT carry vendor-side hardware identifiers (MAC/OUI/UUID/
FCC-ID/default credentials). 100% of regex surface is GitHub asset FP class
(image previews, social-preview asset URLs).

Hak5 first-party identifier-bearing surface (e.g., `wifipineapple-openwrt`,
`pineapple-modules`, `bashbunny-payloads`/library) is captured via Wave-B2
[MAC-19](/MAC/issues/MAC-19) Cohort 3 (Hak5 Wayback) — NOT re-extracted at
Wave-A per anti-roll-forward discipline.

## extraction_runs.notes

No `extraction_runs` row staged for A3 (no LLM call fired; nothing to log).
This `_absence_documentation.md` file IS the audit trail per Bible §11 #1.

## Refs

- [MAC-25](/MAC/issues/MAC-25) dispatch §16 (A3 + A4 absence-documented unconditional)
- [MAC-23](/MAC/issues/MAC-23) Step-1.5b survey (`logs/mac23_step1.5b_byte_level_survey_20260505T234132Z.{txt,json}`)
- Codified disambig: `db/extraction/ble_uuid_disambig.py` (Ratification 2)
- Disambig regression artifact: `logs/mac25_step2_0_disambig_regression_20260505T235749Z.json`
- Wave-B2 Hak5 corpus: [MAC-19](/MAC/issues/MAC-19) cohort 3 Wayback
