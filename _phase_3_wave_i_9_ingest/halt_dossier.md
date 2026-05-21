# Phase 3 — Wave I.9 ingest halt dossier

**Dispatch:** [MAC-187](/MAC/issues/MAC-187)
**Parent:** [MAC-184](/MAC/issues/MAC-184)
**Branch:** `v1.4.1-integration-stage-1` @ `bad749d`
**Schema:** 24 (CP29 / migration 0024)
**Date:** 2026-05-20

## Halt summary

Per dispatch §Halt-criteria list, **two halt conditions trip and one operator-decision condition surfaces**:

1. **§11 #1 fabrication + CP29 §1 semantic mismatch (CRITICAL)** — 15/18 net-new candidates are unambiguous third-party tooling/distribution/community/cloud-platform hostnames; auto-promoting them as `vendor_controlled_hostname` for DJI/Parrot would fabricate vendor ownership.
2. **Unmatched source name in plan vs canonical sources table (HIGH)** — Candidate JSON has no explicit `source` field; sid=66 umbrella (`source_class_umbrella_for: [A, A_bucket_payload_firmware, C, D, D_bucket_enum_deep, F]`) does **not** cover `I_github_source_new_orgs` / `I_github_subsidiary_source` source-classes used by Wave I.9 sub-pass 21.
3. **§3.2 corroboration target gap (MEDIUM, operator decision)** — 2 of 4 cross-source-attested hostnames in `cross_source_corroborations_wave_i_9_resynth.json` `specific_checks` lack an existing canonical identifier; dispatch text says corroboration is "for existing identifiers" but data does not match.

## Halt 1 — §11 #1 fabrication + CP29 §1 semantic mismatch

**Data:** see `scrub_log.md`. 16.67% survivor rate against CP29 §1 vendor-ownership semantics (3 survivors / 18 candidates), vs CP29 §5 benchmark of 97.21% Wave I main extraction-time pre-scrub.

**Root cause:** Wave I.9 sub-pass 21 ("5 new orgs source mining") extracted hostnames from README/source files in vendor-owned GitHub repos (dji-sdk, parrot-developers, parrot-opensource, cellebrite-labs, clearview) but did **not** apply a vendor-ownership filter to distinguish "vendor-owned hostname referenced in a vendor README" from "third-party tooling hostname referenced in a vendor README." Wave I main applied such filtering (per CP29 §5 known-limitations note); Wave I.9 sub-pass 21 did not.

**§11 #1 binding:** Promoting `cocoapods.org`, `www.cmake.org`, `software.intel.com`, `code.visualstudio.com`, `ms.portal.azure.com`, `www.chromium.org`, `travis-ci.com`, `registry.npmmirror.com`, `registry.nlark.com`, `wxpython.org`, `www.drmemory.org`, `www.ccoderun.ca`, `gitee.com`, `badges.gitter.im`, `www.waveshare.net` as `vendor_controlled_hostname` with `manufacturer ∈ {DJI, Parrot}` would assert vendor ownership the source does not support. §11 #1 stop-the-line.

**Recommended disposition (for CEO ratification):**
- Drop 15 from Phase 3 promotion pipeline.
- Route them to `conflicts` table with `reason='wave_i_9_third_party_tooling_host_fp'` (or analogous) — preserves audit trail without canonical pollution.
- Carry forward to Wave I.10 / v1.5.0 with an upstream-extractor vendor-ownership filter (matching the per-vendor root-marker list in `scrub_log.md`) applied at sub-pass 21 time.
- 3 survivors (`www.robomaster.com`, `robomaster-dev.rtfd.io`, `forum.dji.com`) eligible for promotion contingent on Halt 2 resolution.

## Halt 2 — Source admission gap (§3.2 unmatched source)

**Data:**
- `hostname_candidates_wave_i_9_delta.json` candidates carry `source_class='I_github_source_new_orgs'` plus per-candidate `source_repo` (e.g., `dji-sdk/FlightHub-2-Frontend-Standalone-Component`). No explicit `source` field naming a row in canonical `sources` table.
- `wave_i_9_lift_candidates_synthesis.json` candidates carry `source_classes` arrays including `I_github_source_new_orgs` and `I_github_subsidiary_source`.
- Canonical `sources.id=66` ("Wave I — Vendor Cloud-Infrastructure Hostname Corpus Extraction", `source_type=manufacturer_app`) `notes.source_class_umbrella_for = [A, A_bucket_payload_firmware, C, D, D_bucket_enum_deep, F]`. **`I_github_source_new_orgs` and `I_github_subsidiary_source` are NOT in this umbrella list.**
- Dispatch §3.2 binds: `source_id resolved by name from the plan's 'source' field (verify against canonical sources table; halt if unmatched)`.

**Operator paths forward (CEO + board to ratify):**
- **Path A (umbrella extension):** Amend sid=66 `notes.source_class_umbrella_for` to add `I_github_source_new_orgs` + `I_github_subsidiary_source`. Treat as CP-class amendment paired with a SAR-13.5-style attribution note since these are vendor-anchored (per-repo) rather than aggregate-anchored. Re-use sid=66 for all 22 lift basis citations + 18 candidate raw_observations.
- **Path B (new sid admissions):** Admit 1–2 new sources (`I_github_source_new_orgs` and/or `I_github_subsidiary_source`) under the same `ratification_band='extraction_methodology_umbrella'` pattern as sid=66, mirroring CP29 §4 source-admissions framework. Schema-side this would be an INSERT into `sources` with a CP30 entry in BIBLE_AMENDMENTS.md.
- **Path C (per-repo sids):** Per-repo sids (mirroring sid=23/40/42/etc. shape for individual GitHub repos cited as crowdsourced/academic sources). Heavier discipline; not recommended given sub-pass 21 already aggregates across orgs at the methodology level.

Recommend **Path A** for fastest unblock, paired with an explicit attribution note in sid=66's `notes` JSON capturing the new sub-pass methodology scope.

## Halt 3 — §3.2 corroboration target gap (operator decision)

**Data:** `cross_source_corroborations_wave_i_9_resynth.json` `specific_checks` shows 4 hostnames with `cross_source_attested=true`:

| hostname | canonical lookup | dispatch shape ("corroboration for existing identifier") |
|---|---|---|
| developer.dji.com | id=23066 (conf 97, source_type=manufacturer_app) | ✓ matches |
| enterprise.dji.com | id=27746 (conf 85, source_type=primary_registry) | ✓ matches |
| fh.dji.com | **NOT IN CANON** | ✗ data-shape mismatch |
| terra-sz-hc1pro-cloudapi.oss-cn-shenzhen.aliyuncs.com | **NOT IN CANON** | ✗ data-shape mismatch |

**Per dispatch §3.2 ("halt if not found or ambiguous"), the lookup gap for `fh.dji.com` and `terra-sz-...` is a halt.**

**Likely intent (for CEO ratification):** The 2 missing hostnames should be net-new promotions at the lifted band (cross-source-attested → 85–95 instead of 75–90 default `vendor_controlled_hostname` single-source band per CP29 §2). The dispatch text "4 corroborations for existing identifiers" is then describing the cross-attestation evidence (genre: two source-classes across organizationally-distinct extraction passes) not the identifier-already-exists property. If ratified, this would unblock at:

| hostname | proposed action | proposed initial band |
|---|---|---|
| developer.dji.com | corroboration raw_obs (existing id=23066) | n/a (already at 97) |
| enterprise.dji.com | corroboration raw_obs + §8.3 lift (existing id=27746 conf 85) | min(99, 85+5) = 90; cap 95 → 90 ✓ |
| fh.dji.com | **net-new INSERT** at lifted band | 90 (mid-lifted 85–95) |
| terra-sz-hc1pro-cloudapi.oss-cn-shenzhen.aliyuncs.com | **net-new INSERT** at lifted band | 90 (mid-lifted 85–95) |

Annex §5 explicitly flags both as Wave I.9 first-surfacings and the WAVE_I9_CONTINUATION_ANNEX §5 also notes: "both source classes are within the same evidence genre (GitHub source mining). §8.3 lift formally applies but the cross-attestation is between organizational scopes (main Wave I.6 orgs ↔ Wave I.9 subsidiary orgs), not between fundamentally different evidence types. **Integration-time decision on lift band.**" — this dispatch is exactly that integration-time decision and the dispatch text did not pre-resolve it.

## Observation (LOW; not a halt, surfaced for board awareness)

A spot survey of the existing canonical `vendor_controlled_hostname` population for `manufacturer='DJI'` (410 rows total) surfaces non-trivial prior FP pollution from Wave I main / v1.4.0 — sample (paste-not-cite from random LIMIT 30 query):

```
cubic-bezier.com        conf=85   (CSS demo tool, NOT DJI)
www.jcip.net            conf=85   (Java Concurrency in Practice, NOT DJI)
bugly.qq.com            conf=85   (Tencent Bugly, NOT DJI)
www.vivo.com.cn         conf=85   (Vivo smartphones, NOT DJI)
libcxx.llvm.org         conf=85   (LLVM libcxx, NOT DJI)
foo.com                 conf=85   (generic placeholder, NOT DJI)
home.earthlink.net      conf=85   (EarthLink ISP, NOT DJI)
developer.intel.com     conf=85   (Intel dev site, NOT DJI)
pki.intel.com           conf=85   (Intel PKI, NOT DJI)
g2.symcb.com0l          conf=85   (Symantec CRL with malformed suffix, NOT DJI)
```

This is the population the MAC-186 hb_002 §"Scope caveat" pre-flagged ("hostname-scoped re-run would directly test the SAR-14 anchor population; surfaced for CEO judgment; out of scope for this MAC-186 dispatch"). A board-class call on whether to:

1. Run a hostname-scoped Phase-2-style FP audit against existing canonical (likely demote / move-to-conflicts a meaningful chunk),
2. OR codify the looser-than-CP29 §1 semantics that Wave I main was actually applying (something like "hostname surfaced via vendor's binary/repo/cert chain regardless of underlying ownership") as a value_class refinement,

is now overdue.

**Validator recommendation:** Option 1 (audit + clean) — CP29 §1 should hold as written; the Wave I main FP pollution is the root cause Wave I.9 amplifies.

## Discipline checklist

- ✅ SAR-13 PRAGMA + CHECK enum surfaced before any SQL drafted (no SQL run this phase — halted at FP scrub)
- ✅ SAR-13.5 N/A (no bucket-payload promotion touched)
- ✅ SAR-15 GENERIC_RISK_CANONICALS audit run (DJI/Parrot/Cellebrite/Clearview AI all resolve at full corporate name — not substring-tier)
- ✅ §11 #1 no fabrication — halted exactly because promotion would fabricate
- ✅ §11 #7 provenance — halted before any raw_observations INSERT
- ✅ §11 #8 no confidence drift — no lifts attempted
- ✅ §11 #9 no skip checkpoints — escalating to CEO via blocked status
- ✅ §11 #11 amendment-log discipline — three operator decisions surfaced for CEO; not unilaterally codified

## Next action

Comment heartbeat onto MAC-187; set status `blocked`; CEO unblock owner; unblock action = ratify Halt 1 disposition (drop 15 / accept 3) + Halt 2 source admission path (recommend Path A) + Halt 3 corroboration-target interpretation (recommend net-new INSERT at lifted band for the 2 not-in-canon).
