# Patch Cycle 2.B — MAC-107 GitHub Code Search auth-required correction

**Trigger:** MAC-107 sub-agent autonomous-wave halt at empirical-premise probe (2026-05-17). Forensic evidence at `extraction_outputs/github_mass_search_admission/STOP_THE_LINE.md`.

**Applied:** 2026-05-18 (post-autonomous-wave Secondary Track, after PC2.A).
**Dispatch authority:** dispatch said "Default patch sequence: SECONDARY-A → SECONDARY-B → SECONDARY-C... CC has autonomy on... Secondary Track Patches A/B/C."

---

## Empirical-premise failures (2 distinct, both surfaced at autonomous-wave probe)

**Failure 1 — auth-required-since-2022:** GitHub Code Search API returns `401 "Requires authentication"` for ALL unauthenticated requests, regardless of whether the target content is public. Has been this way since the 2022 GA rollout of "new code search." Runguide §0 said "unauthenticated/non-Enterprise queries" works — anachronistic; that path was removed at GA. Runguide §1 framed PAT as "raises rate limit" — implies optional; truth is required.

**Failure 2 — §2.7 SQL column drift:** runguide's preflight SQL referenced `identifier_value` and `manufacturer_canonical_name` columns on the `identifiers` table. Actual columns are `identifier` and `manufacturer`. Pre-PC2.B SQL would fail at runtime with `"no such column: identifier_value"`. Sub-agent reproduced empirically with the corrected SQL — 132 distinct query targets at confidence ≥ 80, distribution 70% drone_id_prefix / 41% oui / 0% ble_uuid / 0% ssid_*.

## Patches landed (out-of-tree at `new data 5.17/github_mass_search_admission_runguide.md`)

| Patch | Section | Change |
|---|---|---|
| 2.B.1 | §0 "What this run does NOT do" | Replaced anachronistic "unauthenticated/non-Enterprise queries" framing with empirically-correct "REQUIRED authentication for ALL queries since 2022 GA"; cited the autonomous-wave probe |
| 2.B.2 | §1 Auth field | Made PAT REQUIRED unambiguous (was framed as rate-limit-only previously); 30 req/min on `/search/*`, 5000 req/hr on `/core`; legacy "10 req/min unauthenticated" claim removed |
| 2.B.3 | §2.7 SQL | Column-drift fix: `identifier_value` → `identifier`, `manufacturer_canonical_name` → `manufacturer` (4 SQL UNION ALL branches); PC2.B explanatory comment block documenting the fix; distribution-aware note carry-forward citing the 132-target empirical count + future re-skew when Wave-G v2 BLE UUIDs promote |
| 2.B.4 | §3.0 (NEW) | Empirical-premise verification step: PAT-presence + PAT-scope sanity + authenticated search probe + rate-limit baseline confirmation; CLEAN POSITIVE / PARTIAL POSITIVE / CLEAN NEGATIVE outcome classification; account-identity capture for §11 #3 audit-log provenance (mirrors PC2.A §3.0 pattern; ratifies CP27 §2.4 discipline) |

## Verification (post-amendment)

```
grep -c 'PC2.B'                       github_mass_search_admission_runguide.md  →  7
grep -c 'REQUIRED for all queries'    github_mass_search_admission_runguide.md  →  1
grep -c 'since 2022 GA'               github_mass_search_admission_runguide.md  →  2
grep -c 'identifier_value'            github_mass_search_admission_runguide.md  →  2  (in PC2.B explanatory comment only)
grep -c 'manufacturer_canonical_name' github_mass_search_admission_runguide.md  →  1  (in PC2.B explanatory comment only)
grep -c '§3.0 — Empirical'            github_mass_search_admission_runguide.md  →  1
grep -c 'CP27 §2.4'                   github_mass_search_admission_runguide.md  →  1
```

All 3 remaining drift-references are inside the PC2.B explanatory comment block (intentional documentation of the fix; active SQL uses corrected column names).

## Pattern carry-forward

PC2.B is the second runguide amendment instantiating CP27 §2.4 empirical-premise-verification (PC2.A was the first). The §3.0 idiom is now stable across 2 instances:

- **PC2.A (MAC-105 Patents):** 4 probes — Google Patents markup + PPubs JS-shell + USPTO ODP API auth + EPO Espacenet rate-block
- **PC2.B (MAC-107 GitHub):** 4 probes — PAT presence + PAT scope (account identity) + authenticated search response shape + rate-limit ceiling

Both share the CLEAN POSITIVE / PARTIAL POSITIVE / CLEAN NEGATIVE outcome classification. Both write `_section_3_0_empirical_premise_evidence.json` for audit trail.

## In-repo artifacts in this commit

- `extraction_outputs/_patch_cycle_2/pc2_b_summary.md` — this file

## Out-of-tree edits applied alongside this commit

- `new data 5.17/github_mass_search_admission_runguide.md` — Patches 2.B.1 through 2.B.4 applied per find/replace specifications (verified by grep above)

## What this patch does NOT do

- Does NOT provision `GITHUB_API_TOKEN` env var (operator-onboarding step).
- Does NOT decide PAT account identity (recommendation: dedicated `argus-research` account vs personal `kevlattice` — operator call per §11 #3 audit-log provenance discussion in STOP_THE_LINE).
- Does NOT re-dispatch MAC-107 — the patch is preparation.

## Next steps (post-patch)

1. Operator: provision `GITHUB_API_TOKEN` (recommend dedicated argus-research account; `public_repo` scope minimum).
2. Re-dispatch MAC-107 with the new §3.0 probe sequence + corrected §2.7 SQL.
3. With column drift fixed, the 132-target distribution will become visible; CEO may want to re-cut the §2.7 "top-50 priority" heuristic given the 70/41 drone-RID/OUI split.
