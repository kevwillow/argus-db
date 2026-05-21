# §5.6 sierrawireless slug merge log — MAC-191 Phase 5
Captured: 2026-05-20T19:27:42.853694+00:00

## Pre-state
  canonical slug 'sierra_wireless' active count = 126
  slug-form 'sierrawireless' rows = 2
    id=35300 identifier='developer.sierrawireless.com' type=vendor_controlled_hostname source_url=wave_i_aggregate://wave_i_7_delta/I_github_source/developer.sierrawireless.com
    id=35301 identifier='sierrawireless.github.com' type=vendor_controlled_hostname source_url=wave_i_aggregate://wave_i_7_delta/I_github_source/sierrawireless.github.com
  TitleCase 'Sierra Wireless' active count = 6 (out-of-scope; Stage 2)

## Halt check — vendor-identity verification
  id=35300 identifier='developer.sierrawireless.com' — sierrawireless.com domain references Sierra Wireless ✓
  id=35301 identifier='sierrawireless.github.com' — sierrawireless.com domain references Sierra Wireless ✓

## Apply merge
  APPLY id=35300: 'sierrawireless' → 'sierra_wireless'
    notes.slug_duplication_review: 'see_phase_5' → 'resolved_phase_5_mac191'
    notes.manufacturer_text_history[] +1 audit entry
  APPLY id=35301: 'sierrawireless' → 'sierra_wireless'
    notes.slug_duplication_review: None → 'resolved_phase_5_mac191'
    notes.manufacturer_text_history[] +1 audit entry
  COMMIT: 2 rows updated

## Post-state
  canonical slug 'sierra_wireless' active count = 127 (was 126; expect +2)
  slug-form 'sierrawireless' rows = 0 (was 2; expect 0)
  WARN: canonical count delta != merged count

## Stage 2 candidates surfaced
- TitleCase 'Sierra Wireless' rows (6) are out-of-scope for §5.6 (slug-form merge).
  These rows differ in case+format and may merit a separate canonical-form normalization
  in v1.5.0. Surface for CEO ratification.