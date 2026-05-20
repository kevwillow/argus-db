# §6.2 identifier promotion log — MAC-192 Phase 6 Wave I.14a
Captured: 2026-05-20T19:46:10.153378+00:00

  HALT-SURFACE wave_i_13 api.dbeta.me: plan-input lacks source_url + raw_obs_id; held per §11 #1

## §6.2-identifierrow (113 actionable candidates)

  per-outcome counts: {'inserted': 113, 'skip_already_promoted': 0, 'skip_idempotent': 0, 'honeywell_staged': 0, 'halt_unresolved_mfr': 0, 'halt_missing_raw_obs': 0, 'halt_missing_source': 0}

## §6.2-android (15 Flock device-side android packages → manufacturers.notes.android_packages; mfr_id=1 canonical='Flock Safety')
  appended: 15; post-state count: 15

## §6.2-apisurfaces (12 Collins REST + 15 CVEs → manufacturers.notes for mfr_id=1 'Flock Safety')
  api_surfaces.collins appended: 12; cve_inventory appended: 15

## §6.2-typevocabgap (10 items)
  applied mfr='Parrot' (id=25): 2 items; post-state count=2
  applied mfr='DJI' (id=22): 7 items; post-state count=7
  applied mfr='Flock Safety' (id=1): 1 items; post-state count=1

## Post-state readback
- identifiers active total: 34909
- identifiers active with MAC-192 tag: 113

## Section summary
- §6.2-identifierrow: {'inserted': 113, 'skip_already_promoted': 0, 'skip_idempotent': 0, 'honeywell_staged': 0, 'halt_unresolved_mfr': 0, 'halt_missing_raw_obs': 0, 'halt_missing_source': 0}
- §6.2-android: appended=15
- §6.2-apisurfaces: api=12 cve=15
- §6.2-typevocabgap: appended=10