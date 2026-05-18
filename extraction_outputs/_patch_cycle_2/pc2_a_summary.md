# Patch Cycle 2.A — MAC-105 USPTO Patent Public Search migration

**Trigger:** MAC-105 sub-agent autonomous-wave halt at empirical-premise probe (2026-05-17). Forensic evidence at `extraction_outputs/patent_text_mining_admission/STOP_THE_LINE_uspto.md`.

**Applied:** 2026-05-18 (post-autonomous-wave Secondary Track).
**Dispatch authority:** dispatch said "Default patch sequence: SECONDARY-A → SECONDARY-B → SECONDARY-C... CC has autonomy on... Secondary Track Patches A/B/C."

---

## Empirical-premise failure summary

- `patft.uspto.gov` DNS NXDOMAIN — legacy PatFT/AppFT decommissioned ~Q3 2022
- `https://ppubs.uspto.gov/dirsearch-public/searches/searchPortal` returns 404 (path is JS-runtime endpoint, not server-rendered)
- `https://ppubs.uspto.gov/pubwebapp/` returns 1456-byte JS shell (the actual Patent Public Search SPA entry)
- All guessed XHR endpoints (`/api/search`, `/api/v1/search`) return 401 unauthenticated
- `patentsview.org` NXDOMAIN; `api.patentsview.org` serves USPTO Open Data Portal SPA shell (legacy bulk-JSON API gone)
- Replacement: USPTO Open Data Portal at `https://data.uspto.gov/api/` (API-key required, register at `data.uspto.gov/api/manage`)

## Patches landed (out-of-tree at `new data 5.17/patent_text_mining_admission_runguide.md`)

| Patch | Section | Change |
|---|---|---|
| 2.A.1 | §1.1 source profile | URL → `https://ppubs.uspto.gov/pubwebapp/`; Auth field rewritten: REQUIRED for programmatic access; `USPTO_ODP_API_KEY` env var convention introduced; Google Patents per-row stable URL stays (most reliable mirror); rate limits clarified |
| 2.A.2 | §2.6 endpoint verify | 4-probe block: Google Patents `<article>` markup; PPubs JS-shell byte-count confirmation; USPTO ODP authenticated probe if key present; EPO Espacenet rate-block detection |
| 2.A.3 | §3.0 (NEW) | Empirical-premise verification step inserted before §3.1; 4-probe sequence; CLEAN POSITIVE / PARTIAL POSITIVE / CLEAN NEGATIVE outcome classification; output deliverable `_section_3_0_empirical_premise_evidence.json` |
| 2.A.4 | §3.3 per-patent citation re-fetch | Legacy `patft.uspto.gov` removed from default flow; replaced with PPubs JS-shell URL (provenance-only) + ODP API path (preferred); EPO Espacenet 403 rate-block contingency noted; **degraded-mode posture** for when `USPTO_ODP_API_KEY` absent — citation pointer deferred to validator's async re-citation pass (analogous to MAC-101's `degraded_b_deferred_citation` pattern) |

## Verification (post-amendment)

```
grep -c 'PC2.A'             patent_text_mining_admission_runguide.md  →  12
grep -c 'ppubs\.uspto\.gov' patent_text_mining_admission_runguide.md  →  5  (vs 1 pre-patch)
grep -c 'USPTO_ODP_API_KEY' patent_text_mining_admission_runguide.md  →  8
grep -c '§3.0 — Empirical'  patent_text_mining_admission_runguide.md  →  1
grep -c 'data\.uspto\.gov'  patent_text_mining_admission_runguide.md  →  5
grep -c 'uspto_citation_deferred' patent_text_mining_admission_runguide.md  →  1
```

3 remaining `patft.uspto.gov` references are intentional — they appear in PC2.A explanatory text noting legacy URL decommission.

## Pattern carry-forward

This patch instantiates the empirical-premise-verification discipline (CP27 §2.4 amendment) for one specific runguide. Pattern is now established across MAC-101 (PC1.7 Step 0 Path C investigation) + MAC-105 (PC2.A §3.0 probe sequence). Future runguide amendments (PC2.B GitHub, PC2.C ISED, plus pending MAC-103/110 CEO scope decisions) inherit the same §3.0 idiom.

## In-repo artifacts in this commit

- `extraction_outputs/_autonomous_overnight/pc2_a_summary.md` — this file

## Out-of-tree edits applied alongside this commit

- `new data 5.17/patent_text_mining_admission_runguide.md` — Patches 2.A.1 through 2.A.4 applied per find/replace specifications (verified by grep above)

## What this patch does NOT do

- Does NOT register a USPTO ODP API key (operator-onboarding step; the patch documents the requirement but doesn't perform it).
- Does NOT register EPO OPS OAuth2 credentials (same posture).
- Does NOT re-dispatch MAC-105 — the patch is preparation; re-dispatch requires CEO authorization at next cycle.
- Does NOT touch EPO Espacenet §1.2 or Google Patents §1.3 source-profile rows (those weren't load-bearing-broken at autonomous-wave probe time; only §2.6 endpoint-verify needed amendment to cover all 3 sources empirically).

## Next steps (post-patch)

1. Operator: register `USPTO_ODP_API_KEY` at `data.uspto.gov/api/manage` and add to `.env`.
2. Optional operator: register EPO OPS OAuth2 client at `developers.epo.org` for 2.5 GB/week free quota.
3. Re-dispatch MAC-105 with the new §3.0 probe sequence active.
