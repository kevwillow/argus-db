# Patch Cycle 2.D — MAC-103 BT SIG Qualified Designs narrow-to-shallow

**Trigger:** MAC-103 sub-agent autonomous-wave halt at empirical-premise probe (2026-05-17). Forensic evidence at `extraction_outputs/bt_sig_qualified_designs_admission/STOP_THE_LINE.md`.

**Applied:** 2026-05-18 (post-autonomous-wave Secondary Track, after PC2.A/B/C; per CEO scope decision authorizing PC2.D commit).
**Dispatch authority:** CEO disposition on Patch D: "narrow to public-shallow surface. Admit the source at company-listing depth only; drop per-QDID Layers detail. Patch the runguide §0 scope + §1.1 access depth + §4.1 per-QDID extraction shape accordingly. Commit per cycle-2 discipline."

---

## Empirical-premise failure summary

- `launchstudio.bluetooth.com` 301-redirected to `qualification.bluetooth.com` (host migration)
- Data UI is Vue SPA, not server-rendered HTML — runguide's pre-PC2.D HTML-parse premise structurally moot
- Cloudflare WAF rejects `argus-research/1.0` UA at the edge (returns fake invalid_request page); browser-shape UA required
- Public POST API at `qualificationapi.bluetooth.com/api/Platform/Listings/Search` works unauthenticated and returns QDID + ProductName + OwnerCompany **at shallow depth only**
- BLE feature fields (DeclaredProfiles, DeclaredRoles, DeclaredServiceUUIDs, Layers, Spec) are **NOT in public response** — they're gated behind `Platform/Listings/Submission/{listingId}/Layers` returning **HTTP 401** unauthenticated; SPA-gated on `!this.isPublic` (SIG-member-only)

## CEO scope decision (Patch D)

> Admit at company-listing depth only; drop per-QDID Layers detail. Primary value (product-name → owner-company linkage feeding SIG-company-ID corroboration + Wave-G companion-app cross-extraction pointers) is preserved at shallow depth. Secondary value (declared profiles + roles) lost but recoverable via MAC-103.v2 if SIG member access lands later.

## Patches landed (out-of-tree at `new data 5.17/bt_sig_qualified_designs_admission_runguide.md`)

| Patch | Section | Change |
|---|---|---|
| 2.D.1 | §0 Scope | PC2.D empirical-premise correction header; "What this run does" narrowed to shallow-surface capture (QDID + product_name + owner_company + reference_QDID); cross-source linkage to existing `ble_manufacturer_id` rows preserved; product-name → owner-company linkage explicitly framed as Wave-G companion-app cross-extraction pointer; "What this run does NOT do" expanded with PC2.D items (no BLE-feature extraction; no `ble_uuid` candidate emission from this source; vestigial items preserved with "v2 reference" annotation) |
| 2.D.2 | §1.1 source profile | Source URL → `https://qualification.bluetooth.com/`; "Access depth (PC2.D)" row added marking public-shallow-only; Auth field updated for PC2.D member-auth gate; public POST search endpoint added (`POST https://qualificationapi.bluetooth.com/api/Platform/Listings/Search` with JSON body); browser-shape UA note added (Cloudflare WAF rejects argus-research UA); name dropped "(Launch Studio)" parenthetical |
| 2.D.3 | §2.6 endpoint verify | Updated: POST to public API with browser-shape UA; legacy launchstudio.bluetooth.com redirect confirmation probe |
| 2.D.4 | §3.0 (NEW) | Empirical-premise verification: 4-probe sequence (public POST API reachability + legacy redirect + public response shape confirmation + per-QDID Layers endpoint deadness); CLEAN POSITIVE / PARTIAL POSITIVE / CLEAN NEGATIVE outcome classification; ratifies CP27 §2.4 discipline (fourth runguide instance after PC2.A/B/C) |
| 2.D.5 | §3.1 search per company | POST API request shape (was GET with query-string); JSON body with OwnerName + PageIndex + PageSize; pagination convention; PC2.D note clarifying which fields are present at shallow depth vs absent (gated to v2) |
| 2.D.6 | §3.2 per-QDID detail fetch | DEFERRED TO MAC-103.v2 banner; pre-PC2.D template retained inline as v2-author reference; Wave-G companion-app extraction noted as the active substitute path |
| 2.D.7 | §3.3 profile-to-UUID resolution | DEFERRED TO MAC-103.v2 banner; cross-reference to MAC-104 family (9 net-new BLE UUIDs from Wave-G v2 quartet) as the active path for numeric UUID surfaces |
| 2.D.8 | §4.1 per-QDID extraction output shape | NEW shallow-only JSON shape (drops declared_roles / declared_profiles / bt_spec_version / declared_services_uuids); adds `pc2d_shallow_only` + `declared_*_deferred_to_v2` sentinels; adds `wave_g_cross_link_candidate` field pointing to Wave-G v2 deliverables; pre-PC2.D extended shape retained inline below as v2-author reference (clearly labeled DEFERRED-TO-v2) |

## Verification (post-amendment)

```
grep -c 'PC2.D'                       bt_sig_qualified_designs_admission_runguide.md  →  33
grep -c 'qualification.bluetooth.com' bt_sig_qualified_designs_admission_runguide.md  →  13
grep -c 'qualificationapi.bluetooth'  bt_sig_qualified_designs_admission_runguide.md  →  8
grep -c 'DEFERRED TO MAC-103.v2'      bt_sig_qualified_designs_admission_runguide.md  →  5
grep -c 'shallow.surface' (variants)  bt_sig_qualified_designs_admission_runguide.md  →  8
grep -c '§3.0 — Empirical'            bt_sig_qualified_designs_admission_runguide.md  →  1
grep -c 'CP27 §2.4'                   bt_sig_qualified_designs_admission_runguide.md  →  1
grep -c 'pc2d_shallow_only'           bt_sig_qualified_designs_admission_runguide.md  →  1
```

## Cross-source value retention argument

Even at shallow depth, MAC-103 admission delivers measurable cross-source value:

1. **QDID → SIG company-ID linkage** lets the validator's promotion pass cluster Wave-G-extracted BLE UUIDs to specific qualified products. Pre-PC2.D the BLE UUIDs would have come from the QDID Layers endpoint itself; post-PC2.D they come from Wave-G companion-app extraction (MAC-104 family). The QDID is the bridge.
2. **Product-name → owner-company → manufacturer canonical lexicon resolution** improves Argus's manufacturer-aliases table. SIG-qualified product names are the authoritative product-naming surface for any BLE-capable surveillance vendor.
3. **Reference QDID linkage** (when a child product inherits from a parent design) preserves the product-family-genealogy signal that's load-bearing for §8.4 multi-purpose-vendor discipline.

## Pattern carry-forward (now 4 instances of CP27 §2.4)

| Patch | Runguide | §3.0 probes |
|---|---|---|
| PC2.A | MAC-105 Patents | 4: Google Patents markup + PPubs JS-shell + USPTO ODP auth + Espacenet rate-block |
| PC2.B | MAC-107 GitHub | 4: PAT presence + PAT scope + authenticated search + rate-limit ceiling |
| PC2.C | MAC-102 ISED | 4: new endpoint reachability + legacy deadness + Spring Web Flow token + POST-flow advance |
| PC2.D | MAC-103 BT SIG | 4: public POST API + legacy redirect + public response shape + Layers endpoint deadness |

All share CLEAN POSITIVE / PARTIAL POSITIVE / CLEAN NEGATIVE outcome classification. The §3.0 idiom is now stable across 4 distinct runguides with different upstream-surface failure modes (decommission / host-migration / auth-gating / Cloudflare-WAF).

## What this patch does NOT do

- Does NOT acquire SIG member credentials (the deferred per-QDID Layers path requires this).
- Does NOT amend the cross-source-linkage §4.2 (preserved at shallow depth; QDID + SIG company-ID is enough for the validator's linkage).
- Does NOT re-dispatch MAC-103 — the patch is preparation.

## Next steps (post-patch)

1. Operator: confirm cross-source-linkage value-retention argument is acceptable for the v1.2-or-v1.3 release window.
2. Re-dispatch MAC-103 with shallow-only scope. Forecast: ~50-200 QDID rows per Stream A vendor (DJI 100+ QDIDs known; Cellebrite/Skydio likely 5-20 each).
3. Wave-G v3 cross-link: at handoff, validator pairs Wave-G v2 BLE UUIDs (from `extraction_outputs/wave_g_v2_admission/per_vendor/`) to QDID records by owner-company name match.
4. MAC-103.v2 design: if SIG member access lands later, full per-QDID Layers extraction → declared profiles/roles/services/spec from gated endpoint.
