# Phase 3 — Wave I.9 net-new hostname FP scrub log

**Dispatch:** [MAC-187](/MAC/issues/MAC-187) (v1.4.1 Stage 1 Phase 3 — Wave I.9 deltas ingest)
**Parent:** [MAC-184](/MAC/issues/MAC-184)
**Branch:** `v1.4.1-integration-stage-1`
**Date:** 2026-05-20

## Scope

`hostname_candidates_wave_i_9_delta.json` — 18 candidates with `novel_vs_prior=true`. Disambig predicate: CP29 §1 `vendor_controlled_hostname` semantic ("Vendor-owned cloud-infrastructure hostname"). Survivor iff hostname matches vendor-owned root (vendor apex or vendor-known subsidiary brand domain) OR is a vendor-named subdomain hosted on a third-party platform that the vendor actually owns/operates (ReadTheDocs/Zendesk/etc.).

## Vendor-owned root markers (paste-not-cite)

```
dji          : dji.com, djicorp.com, djicdn.com, djiservice.org, robomaster.com
parrot       : parrot.com
cellebrite   : cellebrite.com
clearview_ai : clearview.ai, clearview.team
```

DJI also has vendor-named third-party subdomain pattern: `^(robomaster|dji)[-.][a-z0-9-]*\.(rtfd\.io|readthedocs\.io|zendesk\.com)$`.

## Per-candidate disposition

| hostname | vendor | disposition | reason |
|---|---|---|---|
| www.waveshare.net | dji | **DROP** | Waveshare Electronics (Shenzhen) — hardware reseller; not DJI-owned |
| registry.npmmirror.com | dji | **DROP** | NPM China mirror; not DJI-owned |
| registry.nlark.com | dji | **DROP** | Alibaba/Yuque infrastructure; not DJI-owned |
| wxpython.org | dji | **DROP** | wxPython library project site; not DJI-owned |
| www.robomaster.com | dji | **SURVIVOR** | DJI RoboMaster brand apex |
| robomaster-dev.rtfd.io | dji | **DROP (validator judgment per CEO ratification)** | DJI RoboMaster docs on third-party ReadTheDocs (`rtfd.io` apex Read the Docs Inc.-owned, not DJI). For consistency with the same strict CP29 §1 reading used to drop `cocoapods.org`/`cmake.org`/etc., vendor-named subdomain on a third-party apex does not satisfy "Vendor-owned cloud-infrastructure hostname". Carry-forward to CP30 if a future value_class for "vendor-named-subdomain-on-third-party-platform" is admitted. |
| badges.gitter.im | dji | **DROP** | Gitter chat badge service; not DJI-owned |
| gitee.com | dji | **DROP** | Chinese GitHub clone (OSChina); not DJI-owned |
| cocoapods.org | dji | **DROP** | iOS dependency manager website; not DJI-owned |
| forum.dji.com | dji | **SURVIVOR** | DJI official user forum (`.dji.com` apex) |
| travis-ci.com | dji | **DROP** | Travis CI hosted CI service; not DJI-owned |
| ms.portal.azure.com | dji | **DROP** | Microsoft Azure portal; not DJI-owned |
| code.visualstudio.com | dji | **DROP** | Microsoft VS Code; not DJI-owned |
| www.chromium.org | parrot | **DROP** | Google Chromium project; not Parrot-owned |
| www.cmake.org | parrot | **DROP** | CMake build system; not Parrot-owned |
| software.intel.com | parrot | **DROP** | Intel developer site; not Parrot-owned |
| www.drmemory.org | parrot | **DROP** | Dr. Memory (memory debugger); not Parrot-owned |
| www.ccoderun.ca | parrot | **DROP** | C-Coder community personal site; not Parrot-owned |

## Counts (post-CEO-ratification + validator judgment)

| Metric | Value |
|---|---:|
| Total candidates | 18 |
| Survivors (vendor-owned) | **2** (`www.robomaster.com`, `forum.dji.com`) |
| Drops (third-party platform / tooling / distribution / community) | **16** |
| Survivor rate | **11.11%** |
| CP29 §5 benchmark (Wave I main extraction-time pre-scrub) | 97.21% |
| Delta vs benchmark | **−86.10 pp** |

Original heartbeat hb_003 reported 3 survivors / 15 drops (16.67%) before validator judgment dropped `robomaster-dev.rtfd.io`. CEO ratified that as a validator call per Halt-1 acceptance comment ("If you judge `rtfd.io` root not vendor-owned per strict CP29 §1, drop it too").

## Disposition (Phase 3a — CEO ratified)

CEO ratified Halt 1 (drop 15 + accept survivors) and ratified validator judgment to also drop `robomaster-dev.rtfd.io` → final 16 drops + 2 survivors. Phase 3a committed in single transaction (see `_phase_3_wave_i_9_ingest/transaction_log.md` / hb_003a):

| Action | Count | Target | Notes |
|---|---:|---|---|
| identifiers INSERT (survivor) | 2 | `www.robomaster.com`, `forum.dji.com` | conf=85, source_type=manufacturer_app, value_class=`vendor_controlled_hostname` |
| identifiers INSERT (cross-attested net-new, Halt 3) | 2 | `fh.dji.com` (VCH), `terra-sz-…` (`vendor_cloud_endpoint_url`) | conf=90 lifted band |
| raw_observations INSERT (promotion evidence) | 6 | survivors + Halt-3 net-new | per-source-class rows |
| raw_observations INSERT (corroboration for existing) | 4 | `developer.dji.com` (id=23066) + `enterprise.dji.com` (id=27746) | 2 per host (2 source classes); no identifier mutation |
| raw_observations INSERT (FP-drop evidence) | 16 | drop list above | `promoted_identifier_id=NULL`, notes carry `fp_reason='wave_i_9_third_party_tooling_host_fp'` |
| conflicts INSERT (FP) | 16 | drop list above | `reason='wave_i_9_third_party_tooling_host_fp'`, `resolved_by='validator_da137694'` |
| sources UPDATE (Halt 2 umbrella) | 1 | sid=66 | added `I_github_source_new_orgs` + `I_github_subsidiary_source` to `notes.source_class_umbrella_for` with `umbrella_extensions_log` entry |

Pre→post: `identifiers active 34,792 → 34,796 (+4)`, `identifiers total 34,872 → 34,876 (+4)`, `raw_observations 146,188 → 146,214 (+26)`, `conflicts 20 → 36 (+16)`. §3.4 §8.3 lift application **deferred to [MAC-189](/MAC/issues/MAC-189) Phase 3b** per CEO rescope; [MAC-188](/MAC/issues/MAC-188) Phase 2.5 hostname-corpus SAR-14 audit runs between Phase 3a and Phase 3b.

## SAR-13 + SAR-15 envelope

- SAR-13 PRAGMA + CHECK enum surfaced — CP29 enum values `vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated` confirmed live in `identifiers.identifier_type` CHECK clause (migration 0024 schema_version 24).
- SAR-15 GENERIC_RISK_CANONICALS guard — vendor lexicon hits resolved at full corporate name (`DJI` / `Parrot` / `Cellebrite` / `Clearview AI`); not substring-tier; guard inert.
