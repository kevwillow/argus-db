# Phase 3b §3.4 — Lift candidates skipped due to Phase 2.5 demotion

**Dispatch:** [MAC-189](/MAC/issues/MAC-189) (v1.4.1 Stage 1 — Phase 3b)
**Predecessor demotion source:** [MAC-188](/MAC/issues/MAC-188) Phase 2.5 hostname-corpus FP audit (262 demotions across 9-mfr cohort)
**Date:** 2026-05-20

Per dispatch §3.4 step 1: candidates whose target identifier was demoted (`superseded_by IS NOT NULL`) during MAC-188 Phase 2.5 are skipped from lift application — confidence on a superseded row is not lifted.

## Skipped — 1 candidate

### `terra-sz-hc1pro-cloudapi.oss-cn-shenzhen.aliyuncs.com` (id=35305 → superseded by id=35441)

- **Pre-demotion state (Phase 3a):**
  - `manufacturer='dji'`, `identifier_type='vendor_cloud_endpoint_url'`, `confidence=90`, `source_type='manufacturer_app'` (sid=66)
  - `notes.lift_basis='cp29_s2_cross_source_attestation_hostname_shape_variance'`
  - `notes.value_class_shape_variance_note='hostname_only_no_path_url_shape'`
  - Phase 3a CEO-ratified Halt-1 disposition: promoted under CP29 §2 carve-out for vendor-tenant on third-party cloud platform (Alibaba OSS Shenzhen) with hostname-only shape
- **Phase 2.5 demotion (MAC-188):**
  - Superseded by id=35441 sentinel (`manufacturer=NULL`, `confidence=0`)
  - `notes.fp_class='third_party_oss_sdk_root'`
  - `notes.classifier_reason='third_party_cloud_no_vendor_tenant::aliyuncs.com'`
  - `notes.fp_demoted_at='2026-05-20T18:27:49Z'`
  - `notes.demoted_by_dispatch='MAC-188'`
- **Phase 3b synthesis lift candidate:**
  - source_classes = `[I_github_source_new_orgs, I_github_subsidiary_source]`
  - lift_basis = `section_8_3_cross_source_corroboration`
  - candidate_confidence_band_default = `[80, 90]`
  - candidate_confidence_band_lifted = `[85, 95]`
- **Phase 3b disposition: SKIP — target demoted.** Confidence on superseded row is not lifted per dispatch §3.4 step 1.

## §11 #11 surfacing — Phase 3a / Phase 2.5 reclassification discord

The Phase 3a CEO Halt-1 ratification promoted this row under a CP29 §2 hostname-shape-variance carve-out (vendor-tenant on third-party cloud admits as `vendor_cloud_endpoint_url`). The Phase 2.5 classifier demoted it as `third_party_cloud_no_vendor_tenant::aliyuncs.com`. These two readings are substantively contradictory; the Phase 2.5 demotion prevailed.

Stage 2 amendment-log candidate: clarify whether `<vendor-tenant-token>.<cloud-provider-apex>` URL shapes (e.g., `terra-sz-hc1pro-cloudapi.oss-cn-shenzhen.aliyuncs.com`) admit as `vendor_cloud_endpoint_url` per CP29 §2 or are blanket-FP per CP31-candidate `third_party_oss_sdk_root` class. Forward-looking codification needed; current state (Phase 2.5 demotion) is the operative truth at Phase 3b time.

## Halted-non-independent count

**0** — All 132 lift candidates have ≥2 distinct source_classes per synthesis (CP24 strict-reading passes for the source_class-as-independence-unit interpretation established by Phase 3a Halt-3 CEO ratification). One candidate (`fh.dji.com`) surfaced as a strict source_type-level CP24 nuance — applied under Phase 3a Halt-3 precedent. See `lift_application_log.md` §5 row detail + §"Stage 2 amendment candidates" §1.

## Halted-ceiling-exceeded count

**0** — All computed `new_confidence` values within value_class ceiling per CP29 §8.2.
