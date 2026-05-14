# WiGLE — isolated subsystem (out of Argus active Paperclip scope)

WiGLE.net wireless network database ingestion has been **extracted from Argus's active Paperclip orchestration scope** at the architectural pivot of 2026-05-05 (board decision at MAC-1 [`4df426c7`](https://paperclip.example/MAC/issues/MAC-1#comment-4df426c7-78e0-4e7d-807e-711ca4e64664)).

**Why isolated:** WiGLE ingestion is sustained scheduled API calls with no per-call judgment — cron-shaped work, not agent-shaped work. Wrapping each paced query in an LLM heartbeat (or replicating cron via Paperclip routines) is structurally inefficient. Codified as `feedback_paperclip_vs_cron_workload_shape.md`.

**Status: HALTED in Paperclip context.** [MAC-9](https://paperclip.example/MAC/issues/MAC-9) closed `done` with disposition note. Pipeline remains intact and reusable. Future cron-based ingestion will resume against the same canonical DB tables.

---

## What's in this folder

```
wigle/
├── README.md          ← this file
├── grant_response.md  ← WiGLE-admin elevated-quota grant provenance (100/day, 2026-05-05)
├── pacer.json         ← cross-heartbeat pacing ledger (live ledger from first-fire 17:43:48Z)
├── docs/
│   └── swagger/
│       └── 20260504T181515Z/
│           └── swagger.json  ← v3.1 API spec snapshot (sha256 a66f00f9...)
├── raw/
│   ├── 20260504T185500Z/
│   │   └── manifest_step2.json    ← MAC-9 Step 2 dry-run anchor manifest
│   └── t1_md/
│       └── 20260505T174348Z/
│           └── anchor-321157.json ← First-fire raw artifact (1 query / 100 rows / sha256 1f35b3e504a0da51...)
└── tests/
    └── test_wigle_module.py  ← 65 passed + 2 skipped (run via `pytest wigle/tests/`)
```

## What's NOT in this folder (intentional — board decision)

- **`db/sources/wigle.py`** — the ingestion module stays at its original Python-import path (`from db.sources import wigle`). Code is callable from anywhere; module location preserves import compatibility for any callsite (existing or future cron).
- **`requirements-wigle.txt`** — already isolated by filename at repo root; left in place.
- **DB tables and rows** — canonical Argus data, NOT moved:
  - `sources.id=9` (`crowdsourced` / tier=2 / `last_status='live_ok'` / last_fetched 2026-05-05T17:43:49Z)
  - `wigle_anchor_priority` (80,697 rows, prioritized by tier × state × intra-tier rank)
  - `raw_observations` rows from `source_id=9` (100 rows from sole live-fire batch at 2026-05-05T17:43:48Z)
  - `extraction_runs` row 26 (records_in=1, records_out=100, status=ok)
  - migration `0004_wigle_anchor_priority.sql` (schema_version=4 baseline)

Future cron-based ingestion appends to the same tables.

## How to re-engage WiGLE in a cron context

The full pipeline is built and tested. Cron context steps:

1. **Auth:** load `GITHUB_PAT`-equivalent — `WIGLE_API_NAME` + `WIGLE_API_TOKEN` from `<repo>/.env/.env`. HTTP Basic auth per WiGLE's swagger `securityDefinitions.basic`.
2. **Module import:** `from db.sources import wigle` (works from any Python invocation rooted at `<repo>/`).
3. **Path constants** in `db/sources/wigle.py` already point at this folder:
   - `DEFAULT_RAW_ROOT = REPO_ROOT / "wigle" / "raw"`
   - `DEFAULT_PACER_LEDGER = REPO_ROOT / "wigle" / "pacer.json"`
   - `DEFAULT_DOCS_SNAPSHOT = REPO_ROOT / "wigle" / "docs" / "swagger" / "20260504T181515Z" / "swagger.json"`
4. **CLI entry:** `python -m db.sources.wigle ...` — supports `--live-fire-t1-md` + `--confirm "I-AUTHORIZE-T1-MD-LIVE-FIRE-2026-05-05"` token gate (per-invocation DRY_RUN flip per `feedback_pitch_behavior_binding.md`).
5. **Pacer:** existing `wigle/pacer.json` is live ledger state — cross-heartbeat persistence already works; cron will read+update on each fire.
6. **Quota:** 100 queries/day per grant (see `grant_response.md`); 4 q/hour pacing rule; ~15-min minimum gap; NO retries on 429; response-header `X-RateLimit-Remaining` / `X-RateLimit-Reset` check binding (when WiGLE starts emitting them).

## Carry-forwards (binding through cron-context handoff)

These disciplines apply to ANY future WiGLE engagement, including cron-based:

1. **Pitch-behavior binding** (`feedback_pitch_behavior_binding.md`) — holds verbatim through 2026-05-18 minimum. Outbound pitch claims (rate-limit posture, no-burst discipline, public-source grounding, v1 private repo, shareable-with-trusted-people) carry forward; cron-based system inherits the discipline.
2. **51-row `(?i)\bFlock\b` broadening — INCLUDE recommendation stands.** Per FP analysis at MAC-9 [`a4c8f80f`](https://paperclip.example/MAC/issues/MAC-9#comment-a4c8f80f-53e5-403e-adc6-982b04970a30) (0/51 FP via cross-field disambig). Re-staging timing now applies to whenever WiGLE re-engagement happens (T2 transition or Phase-5 reconcile in the cron context).
3. **Phase 5 export "WiGLE-optional symmetric handling"** stays binding. Argus v1 ships with whatever WiGLE rows have been ingested by Phase-5 close; ships clean if zero.
4. **3 minor ride-along blemishes** (carry-forward to first cron-based execution):
   - (a) `assert ver==4` test-fragility in `test_wigle_module.py` (bumps when DBArchitect extends `identifiers.device_category` CHECK to 13 values for `in_vehicle_router`)
   - (b) `skipped_samples` label imprecision (semantic clean-up)
   - (c) `(?i)` flag — RESOLVED per FP analysis above; re-staging gate fires on next WiGLE engagement
5. **3 first-fire structural findings** (carry-forward as Step-1.5b ratification surface in cron context):
   - **(a) Pagination decision** — anchor 321157 returned `totalResults=147, resultCount=100, searchAfter=...` (47 results left on table). Three options surfaced: (A) single-page-only / (B) paginate-to-completion / (C) paginate-with-cap N pages. CEO recommendation deferred until 5–10 anchors empirical pagination distribution; cron context decides at first sustained execution.
   - **(b) WiGLE response headers do NOT expose quota counters.** No `X-RateLimit-*` / `Retry-After` headers in observed response. Pacer-only tracking is sole quota signal until 429 lands. Defensive `parse_quota_signal` in module already handles `Retry-After` if it appears.
   - **(c)' Atlas rank-1 NULL-geo `wap_id=321156`** auto-skipped at SQL loader (`do.lat IS NOT NULL AND do.lon IS NOT NULL`); net WiGLE-queryable T1 MD = 548 of 549 staged anchors. Documented per §11 #1 absence.

## Audit-trail pointers

- **Architectural pivot:** MAC-1 [`4df426c7`](https://paperclip.example/MAC/issues/MAC-1#comment-4df426c7-78e0-4e7d-807e-711ca4e64664) (board) + this README + `feedback_paperclip_vs_cron_workload_shape.md`
- **Closure:** MAC-9 [`{mac9-close-comment}`](https://paperclip.example/MAC/issues/MAC-9) at 2026-05-05T22:50:58Z (status `done`)
- **Grant provenance:** `wigle/grant_response.md`
- **Step 0 budget estimate:** MAC-9 [`bcbb8494`](https://paperclip.example/MAC/issues/MAC-9#comment-bcbb8494-d461-42d8-b495-46cf2ed1ac0b)
- **Step 1 schema-fit ratification:** MAC-9 [`ea4db5e2`](https://paperclip.example/MAC/issues/MAC-9#comment-ea4db5e2-1735-42d6-950c-099ef8e6842b)
- **Step 2 module + 80,697 anchors:** MAC-9 [`7f91b6da`](https://paperclip.example/MAC/issues/MAC-9#comment-7f91b6da-56a6-4667-8d04-51786e3ed5cf) (DRY_RUN ON during Step 2)
- **Fresh ratification (post-grant):** MAC-9 [`3d9bb72f`](https://paperclip.example/MAC/issues/MAC-9#comment-3d9bb72f-2dbb-4ccd-9283-e775eb6b5857) — board ratified at [`59bc2678`](https://paperclip.example/MAC/issues/MAC-9#comment-59bc2678-1d2d-4a5f-ac29-2c20e714ea6e)
- **First-fire dispatch contract:** MAC-9 [`251a65f3`](https://paperclip.example/MAC/issues/MAC-9#comment-251a65f3-1d2d-4a5f-ac29-2c20e714ea6e)
- **First-fire readiness checklist:** MAC-9 [`d0230a91`](https://paperclip.example/MAC/issues/MAC-9#comment-d0230a91-9c28-402c-b3bd-a77d70eaad3e)
- **First-fire heartbeat report (1 query / 100 rows / NO deviations):** MAC-9 [`0c98a7ed`](https://paperclip.example/MAC/issues/MAC-9#comment-0c98a7ed-bb18-41a4-bdcc-efb2400060d9)
- **Bible:** `<repo>/PROJECT_BIBLE.md` (HEAD `35900f0`) §6 Phase 3 + §11 #2/#6 + Phase 5 export shape
- **SAR-1** (LAA-bit penalty), **SAR-4** (robots.txt routing), **SAR-5** (PII redaction), **SAR-6** (per-wave checkpoint discipline) — all apply to cron-context fires
