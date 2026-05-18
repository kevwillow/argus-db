# Patch Cycle 2.C — MAC-102 ISED REL Spring Web Flow migration

**Trigger:** MAC-102 sub-agent autonomous-wave halt at §2.6 endpoint-verify + empirical-premise probe (2026-05-17). Forensic evidence at `extraction_outputs/ised_rel_admission/STOP_THE_LINE.md`.

**Applied:** 2026-05-18 (post-autonomous-wave Secondary Track, after PC2.A + PC2.B).
**Dispatch authority:** dispatch said "Default patch sequence: SECONDARY-A → SECONDARY-B → SECONDARY-C... CC has autonomy on... Secondary Track Patches A/B/C."

---

## Empirical-premise failure summary

Legacy Oracle PL/SQL gateway at `apc-cap.ic.gc.ca/pls/apca/...` decommissioned. Every URL the pre-PC2.C runguide named was probed at autonomous-wave dispatch; every one returned 404. ISED migrated the entire REL workflow to a **Spring Web Flow application** at `sms-sgs.ic.gc.ca/equipmentSearch/...` with:

- Stateful POST + `execution=eNsM` continuation tokens (vs stateless GET-with-query-string)
- AJAX-polled async result rendering (vs synchronous HTML table return)
- Form-field renaming: `p_company_name` → `companyName`; `p_lang=E` (URL) → `lang=en` (URL); new structured fields `HVINModel`, `productMarketingName`, `hostMarketingName`, `companyNumber`, `approvalCategory`, `lowerFrequency_struct`, `upperFrequency_struct`
- Different host, path, HTTP method, session model, response shape

The pre-PC2.C runguide §3.1's `requests` + BeautifulSoup HTML parser approach is structurally incompatible. The STOP_THE_LINE author explicitly said: "Do not attempt to in-flight patch. This is a v1.0 → v2.0 platform migration."

## Patch scope (constrained per dispatch)

The dispatch said: "Patch scope: amend §1.1 URL template + §3.1 per-proponent search endpoint per the new Spring Web Flow paths". PC2.C captures the URL + auth surface + empirical-premise evidence; it does NOT include a full Spring Web Flow request-shape rewrite (that's v2 runguide authoring work — likely 2-4h authoring effort per the STOP doc).

## Patches landed (out-of-tree at `new data 5.17/ised_rel_admission_runguide.md`)

| Patch | Section | Change |
|---|---|---|
| 2.C.1 | §1.1 source profile | URL → `https://sms-sgs.ic.gc.ca/equipmentSearch/searchRadioEquipments?execution=e1s1&lang=en`; PC2.C empirical-premise correction header explaining Oracle PL/SQL → Spring Web Flow migration; per-row stable URL template + bulk-data URL template marked DEFERRED TO v2 RUNGUIDE (legacy paths dead; new path not yet captured) |
| 2.C.2 | §2.6 endpoint verify | 2-probe block: new endpoint reachability (`grep -c 'Radio Equipment Search'` — note "Search" suffix is new) + legacy endpoint deadness confirmation (HTTP code probe, expected 404) |
| 2.C.3 | §3.0 (NEW) | Empirical-premise verification with 4-probe sequence: new endpoint reachability + legacy deadness + Spring Web Flow continuation-token discovery + POST-flow advance probe; CLEAN POSITIVE outcome explicitly DOES NOT mean "execute §3.1 bulk under pre-PC2.C URLs"; pre-PC2.C URL templates explicitly deferred (mirrors PC2.A §3.0 pattern; ratifies CP27 §2.4 discipline) |
| 2.C.4 | §3.1 per-proponent enumeration | DEFERRED TO v2 RUNGUIDE status banner; pre-PC2.C URL template retained inline as v2-author reference; full Spring Web Flow request-shape spec deferred (stateful execution token bootstrap + form-field renames + AJAX-polling loop + per-result detail-URL extraction) |

## Verification (post-amendment)

```
grep -c 'PC2.C'              ised_rel_admission_runguide.md  →  13
grep -c 'sms-sgs.ic.gc.ca'   ised_rel_admission_runguide.md  →  4
grep -c 'Spring Web Flow'    ised_rel_admission_runguide.md  →  9
grep -c 'DEFERRED TO v2'     ised_rel_admission_runguide.md  →  3
grep -c 'execution=e1s1'     ised_rel_admission_runguide.md  →  ≥3
grep -c '§3.0 — Empirical'   ised_rel_admission_runguide.md  →  1
grep -c 'CP27 §2.4'          ised_rel_admission_runguide.md  →  1
```

## Pattern carry-forward (now 3 instances of CP27 §2.4 instantiation)

| Patch | Runguide | §3.0 probes |
|---|---|---|
| PC2.A | MAC-105 Patents | 4: Google Patents markup + PPubs JS-shell + USPTO ODP auth + Espacenet rate-block |
| PC2.B | MAC-107 GitHub | 4: PAT presence + PAT scope + authenticated search + rate-limit ceiling |
| PC2.C | MAC-102 ISED | 4: new endpoint reachability + legacy deadness + Spring Web Flow token + POST-flow advance |

All share CLEAN POSITIVE / PARTIAL POSITIVE / CLEAN NEGATIVE outcome classification. All write `_section_3_0_empirical_premise_evidence.json` for audit trail. The §3.0 idiom is now stable across 3 distinct runguides.

## In-repo artifacts in this commit

- `extraction_outputs/_patch_cycle_2/pc2_c_summary.md` — this file

## Out-of-tree edits applied alongside this commit

- `new data 5.17/ised_rel_admission_runguide.md` — Patches 2.C.1 through 2.C.4 applied per find/replace specifications (verified by grep above)

## What this patch does NOT do (intentionally constrained scope)

- Does NOT include the v2 Spring Web Flow request-shape spec for §3.1 (stateful token bootstrap + AJAX-polling loop + per-result detail-URL extraction); that's a 2-4h authoring effort deferred to v2 runguide cycle.
- Does NOT update §3.2 (per-cert detail page) or §3.3 (attachment download) — the new endpoints are unknown until §3.1's v2 rewrite captures real proponent-search results.
- Does NOT update §4.3 example URLs — same dependency on §3.1 rewrite.
- Does NOT identify replacement for `apc-cap.ic.gc.ca/datafiles/REL.zip` bulk dataset — operator should check `open.canada.ca/data` for current OGL-Canada-2.0 REL artifact.

## Next steps (post-patch)

1. Operator: confirm the OGL-Canada-2.0 license posture is unchanged on the new platform (ISED's Crown copyright is unchanged; technical access surface moved).
2. v2 runguide author: spec the Spring Web Flow request shape (execution token + AJAX-polling + new form fields) using the §3.0 probe evidence as starting point.
3. Spot-check `open.canada.ca/data/en/dataset?q=radio+equipment+list` for current REL bulk artifact; if found, populate §1.1 Bulk-data URL template; if not, drop §3.4 fallback entirely.
4. Re-dispatch MAC-102 with v2 runguide after authoring effort completes.

## Pattern observation for CEO consideration

PC2.A/B/C all share the same root-cause pattern: a runguide written 2024-2025 against the then-current upstream surface, which has since migrated/decommissioned/auth-gated. CP27 §2.4 codifies the empirical-premise verification discipline that catches these at preflight. The 3 patches together demonstrate the discipline IS working (each one took 5-25 min to apply and surfaces concrete next-step requirements for the next dispatch cycle), but they also confirm that web-scrape runguides have a 6-12 month freshness half-life and need re-verification before any bulk dispatch.

The local-tooling-extraction runguides (Wave-G family) do NOT face this freshness decay because their dependency is on local APK + decompile tooling (which the runguide owns), not on a remote upstream surface (which moves independently).
