# Phase 2.5 hostname-corpus FP audit — index

Dispatch: MAC-188. Population: 12,243 active hostname-corpus rows (`vendor_controlled_hostname` + `vendor_cloud_endpoint_url` + `vendor_controlled_hostname_deprecated` where `superseded_by IS NULL`).

Classifier: `_phase_2_5_hostname_fp_audit/classifier.py`. Methodology:
TP = vendor-owned root match; FP = known third-party / synthetic-pattern / CN-tech-giant cross-attribution / malformed extraction artifact; AMBIGUOUS = no confident match either way.

Bands per SAR-14 calibration discipline (strict-FP-rate basis): 
≤10% well-calibrated · 10-30% sweep-demote band · >30% HALT.

## Per-manufacturer disposition

| Manufacturer | N | TP | FP | AMB | strict-FP% | worst-case-FP% | band (strict) |
|---|---:|---:|---:|---:|---:|---:|---|
| axon | 2436 | 2423 | 6 | 7 | 0.25% | 0.53% | ≤10% (well-calibrated) |
| honeywell | 1742 | 1733 | 7 | 2 | 0.4% | 0.52% | ≤10% (well-calibrated) |
| jacobs | 1257 | 1252 | 5 | 0 | 0.4% | 0.4% | ≤10% (well-calibrated) |
| l3harris | 846 | 846 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| axis_communications | 815 | 815 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| harris | 700 | 698 | 2 | 0 | 0.29% | 0.29% | ≤10% (well-calibrated) |
| motorola_solutions | 521 | 515 | 0 | 6 | 0.0% | 1.15% | ≤10% (well-calibrated) |
| hikvision | 460 | 344 | 16 | 100 | 3.48% | 25.22% | ≤10% (well-calibrated) |
| dji | 436 | 241 | 83 | 112 | 19.04% | 44.72% | 10-30% (moderate over-promotion → demote sweep) |
| cellebrite | 386 | 386 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| cisco_meraki | 333 | 289 | 19 | 25 | 5.71% | 13.21% | ≤10% (well-calibrated) |
| johnson_matthey | 252 | 252 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| skydio | 211 | 211 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| genetec | 192 | 191 | 1 | 0 | 0.52% | 0.52% | ≤10% (well-calibrated) |
| soundthinking | 138 | 138 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| getac | 133 | 131 | 2 | 0 | 1.5% | 1.5% | ≤10% (well-calibrated) |
| dedrone | 132 | 132 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| sierra_wireless | 126 | 126 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| kenwood | 118 | 118 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| cradlepoint | 103 | 103 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| dahua | 101 | 75 | 13 | 13 | 12.87% | 25.74% | 10-30% (moderate over-promotion → demote sweep) |
| magnet_forensics | 81 | 81 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| brinc | 76 | 75 | 1 | 0 | 1.32% | 1.32% | ≤10% (well-calibrated) |
| keyw | 76 | 76 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| parrot | 75 | 62 | 13 | 0 | 17.33% | 17.33% | 10-30% (moderate over-promotion → demote sweep) |
| flock_safety | 67 | 67 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| autel_robotics | 61 | 50 | 8 | 3 | 13.11% | 18.03% | 10-30% (moderate over-promotion → demote sweep) |
| hak5 | 40 | 39 | 0 | 1 | 0.0% | 2.5% | ≤10% (well-calibrated) |
| rhombus_systems | 39 | 38 | 0 | 1 | 0.0% | 2.56% | ≤10% (well-calibrated) |
| rekor | 36 | 35 | 1 | 0 | 2.78% | 2.78% | ≤10% (well-calibrated) |
| briefcam | 31 | 31 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| clearview_ai | 24 | 24 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| eagle_eye_networks | 24 | 23 | 0 | 1 | 0.0% | 4.17% | ≤10% (well-calibrated) |
| watchguard | 19 | 19 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| septier | 17 | 17 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| vigilant_solutions | 16 | 16 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| engility | 15 | 15 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| utility_inc | 15 | 15 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| drt | 13 | 0 | 10 | 3 | 76.92% | 100.0% | >30% (HALT) |
| berla | 12 | 12 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| avigilon | 10 | 8 | 1 | 1 | 10.0% | 20.0% | ≤10% (well-calibrated) |
| bluepoint_alert | 10 | 10 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| droneshield | 10 | 10 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| verkada | 9 | 6 | 3 | 0 | 33.33% | 33.33% | >30% (HALT) |
| digital_ally | 8 | 8 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| coban_technologies | 6 | 6 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| lenel | 4 | 2 | 2 | 0 | 50.0% | 50.0% | >30% (HALT) |
| reveal | 4 | 0 | 4 | 0 | 100.0% | 100.0% | >30% (HALT) |
| pips_technology | 2 | 2 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| sierrawireless | 2 | 1 | 1 | 0 | 50.0% | 50.0% | >30% (HALT) |
| wolfcom | 2 | 2 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
| meraki | 1 | 1 | 0 | 0 | 0.0% | 0.0% | ≤10% (well-calibrated) |
