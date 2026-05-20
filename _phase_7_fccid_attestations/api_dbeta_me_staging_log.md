# Phase 7 §7.0 — api.dbeta.me staging + promotion log

**Dispatch ref:** MAC-194 §7.0 (folded from MAC-192 CEO ratification item 1)
**Predecessor halt:** Phase 6 strict-§11 #1 hold (per `_phase_6_wave_i_14a/preflight_pragma.md` §Halt-surface).
**Pattern:** wave_i_aggregate (mirrors 4 sibling DJI dbeta.me hosts ids 27658 / 27890 / 27898 / 27931).

## Result

- raw_observations.id = 255958
- identifiers.id      = 35681
- identifier          = api.dbeta.me
- identifier_type     = vendor_controlled_hostname
- manufacturer        = dji
- device_category     = unknown
- confidence          = 85 (single-source default; cp29 vendor_controlled_hostname band)
- source_id           = 66 (Wave I — Vendor Cloud-Infrastructure Hostname Corpus Extraction)
- source_type         = manufacturer_app
- source_url          = wave_i_aggregate://wave_i_main/A/api.dbeta.me
- source_row_key      = wave_i_v1.4.1:wave_i_main:A:api.dbeta.me

## Provenance

Plan-input evidence verbatim (Wave I.13 / wave_i_14a `RECONCILIATION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json` §wave_i_13_dji_hikvision_endpoints.net_new_promotion_proposals[0]):

> Debug/demo endpoint baked into DJI desktop installers (api.dbeta.me / fmdemo.aasky.net / account.dbeta.me). DJI uses .dbeta.me and .aasky.net as alternate vendor-controlled domains alongside primary .dji.com.

## §11 discipline

- §11 #1 (no fabrication) — plan-input evidence verbatim attached; source_url anchored in wave_i_aggregate canonical.
- §11 #7 (provenance) — raw_observations.id chained to identifiers.id via promoted_identifier_id.
- §11 #8 (no confidence drift) — confidence=85 per cp29 vendor_controlled_hostname default band; single source; no §8.3 lift applied.
