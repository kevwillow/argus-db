# §4.6 Wave I.9 cross-axis pre-attestation log — MAC-190 Phase 4
Captured: 2026-05-20T19:04:26.316547+00:00

## Mechanic
- Each Phase 3a Wave I.9 identifier row receives 1 INSERT raw_observations row attesting cross-axis pre-attestation evidence.
- Per-canonical pre-attestation aggregate (35 DJI / 12 Parrot / 11 Cellebrite = 58) captured in notes.
- Parrot/Cellebrite have 0 Phase 3a canonical rows → no INSERT possible (§11 #1); carry-forward as metadata-only.
- 35305 superseded → INSERT raw_observations carry-forward row but SKIP lift.

## DJI (mid=22)
- wave_i_9_hostname_count: 35
- existing_hard_id_axis_rows: 65
- cross_axis_pre_attested: True
- lift_eligible_at_promotion: True
- sample_hostnames_first_3: ['fh.dji.com', 'developer.dji.com', 'docs.docker.com']
- cross-axis hard_id evidence: row id=423 identifier='8c:58:23' type=oui conf=95 src=primary_registry
### Phase 3a target id=35302 `www.robomaster.com` (type=vendor_controlled_hostname, conf=85, src=manufacturer_app, sup=None)
- INSERT raw_observations promoted_identifier_id=35302 source_url='wave_i_aggregate://wave_i_11_reconciliation/cross_axis_pre_attestation/DJI/www.robomaster.com'
- **LIFT-APPLIED**: id=35302 conf 85→95 (formula=99, ceiling=95)
### Phase 3a target id=35303 `forum.dji.com` (type=vendor_controlled_hostname, conf=85, src=manufacturer_app, sup=None)
- INSERT raw_observations promoted_identifier_id=35303 source_url='wave_i_aggregate://wave_i_11_reconciliation/cross_axis_pre_attestation/DJI/forum.dji.com'
- **LIFT-APPLIED**: id=35303 conf 85→95 (formula=99, ceiling=95)
### Phase 3a target id=35304 `fh.dji.com` (type=vendor_controlled_hostname, conf=95, src=manufacturer_app, sup=None)
- INSERT raw_observations promoted_identifier_id=35304 source_url='wave_i_aggregate://wave_i_11_reconciliation/cross_axis_pre_attestation/DJI/fh.dji.com'
- no-op: current=95, formula=99, capped=95 (ceiling=95)
### Phase 3a target id=35305 `terra-sz-hc1pro-cloudapi.oss-cn-shenzhen.aliyuncs.com` (type=vendor_cloud_endpoint_url, conf=90, src=manufacturer_app, sup=35441)
- INSERT raw_observations promoted_identifier_id=35305 source_url='wave_i_aggregate://wave_i_11_reconciliation/cross_axis_pre_attestation/DJI/terra-sz-hc1pro-cloudapi.oss-cn-shenzhen.aliyuncs.com'
- **SKIP-DEMOTED**: target id=35305 superseded_by=35441; no lift per dispatch §4.6

## Parrot (mid=25)
- wave_i_9_hostname_count: 12
- existing_hard_id_axis_rows: 8
- cross_axis_pre_attested: True
- lift_eligible_at_promotion: True
- sample_hostnames_first_3: ['developer.parrot.com', 'forum.developer.parrot.com', 'www.chromium.org']
- **CARRY-FORWARD**: 0 Phase 3a canonical rows for `parrot`. 12 pre-attestations stored as plan-metadata only (no INSERT — §11 #1 / no identifier_id target to link).

## Cellebrite (mid=28)
- wave_i_9_hostname_count: 11
- existing_hard_id_axis_rows: 1
- cross_axis_pre_attested: True
- lift_eligible_at_promotion: True
- sample_hostnames_first_3: ['docs.hex-rays.com', 'hex-rays.com', 'arxiv.org']
- **CARRY-FORWARD**: 0 Phase 3a canonical rows for `cellebrite`. 11 pre-attestations stored as plan-metadata only (no INSERT — §11 #1 / no identifier_id target to link).

## Clearview AI (mid=32)
- wave_i_9_hostname_count: 8
- existing_hard_id_axis_rows: 0
- cross_axis_pre_attested: False
- lift_eligible_at_promotion: False
- sample_hostnames_first_3: ['developers.google.com', 'docs.aws.amazon.com', 'rootspace.app']
- **NO-OP**: not cross-axis pre-attested (no existing hard_id rows). No INSERT, no lift.

## Summary
- inserts: 4
- lifts_applied: 2
- lifts_no_op: 1
- skipped_demoted: 1
- carry_forward_no_canonical_target: 23
- targets_total: 4

## Note on '58 pre-attestation' headline count
- DJI: 35 underlying pre-attestation hostnames → 4 INSERTs (one per Phase 3a row); 3 lift fires + 1 superseded skip.
- Parrot: 12 pre-attestation hostnames → 0 INSERTs (no Phase 3a Parrot canonical row to link). Carry-forward metadata.
- Cellebrite: 11 pre-attestation hostnames → 0 INSERTs (no Phase 3a Cellebrite canonical row). Carry-forward metadata.
- Total INSERTs: 4 raw_observations rows representing 58 underlying pre-attestation hostnames per per-canonical aggregate captured in notes.
- Stage 2 amendment-log candidate: the '58 → 4 INSERTs' compression is a §4.6 mechanic-clarity question (per-attestation vs per-target). Surface for CEO ratification.