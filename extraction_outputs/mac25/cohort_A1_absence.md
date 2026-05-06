# Cohort A1 absence documentation (Wave-A Step-2 / MAC-25)

**Per dispatch §15 + CEO ratification of option (c) at Step-2.0 close (`4a18f118`):** A1 absence-documented at Step-2 close PER THE STEP-1 README CORPUS ONLY. Step-2.5 SourceWorker re-engagement spawned at [MAC-26](/MAC/issues/MAC-26) for A1 SDK content fetch over 11 yielding repos surfaced by Step-2.0 `/search/code` probe (Cradlepoint × 2, Sierra Wireless × 3, DJI × 6).

## Verbatim re-quote of Step-1.5b corpus-shape evidence (READMEs only)

From `logs/mac23_step1.5b_byte_level_survey_20260505T234132Z.txt`:

```
cohort        files      bytes  mac_anch  ble_uuid  fcc_t  ssid_kw  cred_kw  pii  repos
cohort_A1        45     279703         0         2      1        0        0   14     43
```

## Step-2.0 probe carry-forward — A1 first-party SDK code-surface (NEW evidence)

From `raw/github_step2/{20260506T000421Z, 20260506T000715Z, 20260506T000920Z}/_probe_manifest.json`
+ Step-2.0 deliverable comment [`1e3ef8a4`](/MAC/issues/MAC-25#comment-1e3ef8a4-2364-4016-be2a-07f532d7e57c):

| vendor | fires | total_count_returned | unique repos | A1 first-party? |
|---|---:|---:|---:|---|
| Cradlepoint | 4 | 215 | 2 (`api-samples`, `sdk-samples`) | yes |
| Sierra Wireless | 3 | 259 | 3 (`luasched`, `octave-orp`, `octave-orp-stm32`) | yes |
| DJI | 4 | 403 | 6 (`Mobile-SDK-Android`, `Mobile-SDK-Android-V5`, `DJI-Cloud-API-Demo`, +3) | yes |
| Hak5 | 3 | 279 | 9 | yes (already in [MAC-19](/MAC/issues/MAC-19) cohort 3) |
| WatchGuard | 4 | 0 | 0 | yes (zero-yield) |
| Motorola Solutions | 4 | 0 | 0 | yes (zero-yield) |
| Axon | 4 | 0 | 0 | yes (zero-yield) |
| Flock Safety | 4 | 0 | 0 | yes (zero-yield) |

**Total A1 keyword-surface (excl Hak5):** 877 hits across 11 NEW repos NOT in Wave-A Step-1 corpus (which contained READMEs only).

## §15 carry-forward decision (CEO-ratified at `4a18f118`)

Per dispatch §15: "If probe surfaces ≥1 anchored hit not already in Wave-A corpus, A1 reverts to extraction (new shard scope)."

Per CEO ratification: gate is *anchored*, not keyword-surface. Anchored confirmation requires content-fetch first (SourceWorker scope per Bible §7.1). Therefore:

- **Step-2 close (this issue):** A1 absence-documented per Step-1 README corpus ONLY (matching Step-1.5b survey numbers).
- **Step-2.5 ([MAC-26](/MAC/issues/MAC-26)):** SourceWorker re-engaged for A1 SDK content fetch — fresh `_meta.json` + likely-id-bearing path heuristic over `*.{java,c,h,py,kt,swift}` files (~66 estimated core calls, ≤100 budget).
- **Step-2.6 (post-MAC-26 close):** separate ExtractionWorker dispatch (own MAC-N issue, mirrors [MAC-23](/MAC/issues/MAC-23) → [MAC-25](/MAC/issues/MAC-25) flow).

## Zero-yield 4 vendors per Step-2.0 (WatchGuard, Motorola, Axon, Flock Safety)

Org-scoped `/search/code` returned 0 hits across all 4 keywords for all 4 vendors. Per dispatch §16 + CEO ratification §6 at `4a18f118`: **absence-documented unconditional**, no re-probe at this dispatch.

Methodology finding: org-scoped queries surfaced 0 — possible interpretations are (a) orgs have no public repos with our keyword surface, OR (b) repos exist but no code matches. Org-existence verification deferred (out-of-scope, would consume additional core calls). Phase-5 reconcile owns re-open if methodology disambiguation is needed.

## extraction_runs.notes

No `extraction_runs` row staged for A1 at this issue. The Step-2.0 probe is a `code_search` HTTP query layer (not extraction), and the staged-rows path waits for [MAC-26](/MAC/issues/MAC-26) → A1-extraction dispatch. This file IS the audit trail per Bible §11 #1.

## Refs

- Dispatch §15 + §17 + Step-2.0 deliverable [`1e3ef8a4`](/MAC/issues/MAC-25#comment-1e3ef8a4-2364-4016-be2a-07f532d7e57c)
- CEO ratification at `4a18f118` (option (c))
- [MAC-26](/MAC/issues/MAC-26) Wave-A Step-2.5 SourceWorker A1 content fetch (spawned)
- [MAC-23](/MAC/issues/MAC-23) Step-1.5b survey
- Codified disambig: `db/extraction/{fcc_grantees_allowlist,ble_uuid_disambig}.py`
- Disambig regression artifact: `logs/mac25_step2_0_disambig_regression_20260505T235749Z.json`
- Probe manifests: `raw/github_step2/{20260506T000421Z, 20260506T000715Z, 20260506T000920Z}/_probe_manifest.json`
