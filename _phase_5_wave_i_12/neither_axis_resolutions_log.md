# §5.3 Neither-axis resolutions log — MAC-191 Phase 5
Captured: 2026-05-20T19:25:35.246783+00:00

## SAR-15 evidence-direction discipline
All 5 resolutions are direct-citation (procurement_records.vendor_canonical_normalized or
deployment_observations.vendor_raw); NOT substring-tier matches.

## §11 #11 text-wrap migration discipline
manufacturers.notes is mixed-shape across the 51-row table (30 JSON / 21 text-shape).
Dispatch §5.5 SQL template `COALESCE(notes, '{}')` assumes JSON shape; text-shape rows
would fail `json_set`. Conservative discipline: text-shape rows get wrapped into
`{"description": <prior-text>}` (matching established schema convention id=2,3,4,5,6 etc.)
atomically as part of the same UPDATE. Text content is preserved verbatim. Wrap-migrations
are flagged in per-row log entries.

## id=2 "Vigilant Solutions"
  resolved_via: USAspending sub-pass B
  axis: procurement+deployment
  evidence: 56 procurement rows, $2.9M + 133 deployments
  GENERIC_RISK_CANONICAL: True
  APPLY: appended neither_axis_resolution entry
  post: notes.neither_axis_resolution[] count = 1
## id=29 "Magnet Forensics"
  resolved_via: USAspending sub-pass B
  axis: procurement
  evidence: 308 procurement rows, $58.3M
  GENERIC_RISK_CANONICAL: True
  TEXT-WRAP MIGRATION: prior text-notes wrapped into description field
  APPLY: appended neither_axis_resolution entry
  post: notes.neither_axis_resolution[] count = 1
## id=32 "Clearview AI"
  resolved_via: USAspending sub-pass B
  axis: procurement
  evidence: 20 procurement rows, $8.3M
  GENERIC_RISK_CANONICAL: True
  TEXT-WRAP MIGRATION: prior text-notes wrapped into description field
  APPLY: appended neither_axis_resolution entry
  post: notes.neither_axis_resolution[] count = 1
## id=218 "Digital Ally"
  resolved_via: deployment_observations sub-pass E
  axis: deployment
  evidence: 11 deployments
  GENERIC_RISK_CANONICAL: True
  APPLY: appended neither_axis_resolution entry
  post: notes.neither_axis_resolution[] count = 1
## id=219 "Aerodome"
  resolved_via: deployment_observations sub-pass E
  axis: deployment
  evidence: 1 deployment
  GENERIC_RISK_CANONICAL: False
  APPLY: appended neither_axis_resolution entry
  post: notes.neither_axis_resolution[] count = 1

## Post-state readback
  id=2 "Vigilant Solutions": neither_axis_resolution = [{"resolved_via":"USAspending sub-pass B","axis":"procurement+deployment","evidence_text":"56 procurement rows, $2.9M + 133 deployments","evidence_fields":{"usaspending_procurement_rows":56,"usaspendi...
  id=29 "Magnet Forensics": neither_axis_resolution = [{"resolved_via":"USAspending sub-pass B","axis":"procurement","evidence_text":"308 procurement rows, $58.3M","evidence_fields":{"usaspending_procurement_rows":308,"usaspending_total_award_usd_approx"...
  id=32 "Clearview AI": neither_axis_resolution = [{"resolved_via":"USAspending sub-pass B","axis":"procurement","evidence_text":"20 procurement rows, $8.3M","evidence_fields":{"usaspending_procurement_rows":20,"usaspending_total_award_usd_approx":83...
  id=218 "Digital Ally": neither_axis_resolution = [{"resolved_via":"deployment_observations sub-pass E","axis":"deployment","evidence_text":"11 deployments","evidence_fields":{"deployment_observations_count":11},"sar_15_evidence_direction":"direct_ci...
  id=219 "Aerodome": neither_axis_resolution = [{"resolved_via":"deployment_observations sub-pass E","axis":"deployment","evidence_text":"1 deployment","evidence_fields":{"deployment_observations_count":1},"sar_15_evidence_direction":"direct_citat...

## Totals
  applied = 5
  text-wrap migrations = 2
  halted = 0