# MAC-192 §6.6 — Scope-expansion (19 BLE-tracker / chip-vendor / consumer-OEM vendors) DEFERRED

Captured: 2026-05-20

**Per dispatch §6.6**: Stage 1 does NOT admit BLE-tracker vendors. These 19 manufacturers were surfaced by Wave I.14a sub-pass 42 (sid=24 AirGuard catalog + sid=16 unknown-mfr tail) but fall outside current ARGUS surveillance-equipment scope per `paperclip_integration_decisions_pending[0]` (decision: "Defer. Current scope is surveillance-equipment-not-people-trackers.").

Cumulative candidate count across the 19 vendors: **70** (sample candidates only enumerated in plan; full lists in `RECONCILIATION_PLAN_V3.community_repo_remine_promotion_candidates.scope_expansion_deferred[]`).

## Vendors deferred (Stage 2 carry-forward candidate per board decision)

| Vendor                                       | Candidate Count |
|----------------------------------------------|-----------------|
| Samsung                                      | 10              |
| EFF (Rayhunter)                              | 9               |
| Apple                                        | 8               |
| Espressif                                    | 5               |
| Google                                       | 5               |
| Xiaomi/YI                                    | 3               |
| Raspberry Pi Foundation                      | 3               |
| Whelen Engineering                           | 3               |
| Qualcomm                                     | 3               |
| Pebblebee                                    | 3               |
| Vivotek                                      | 2               |
| Wyze Labs                                    | 2               |
| Quectel                                      | 2               |
| Telit                                        | 2               |
| Nordic Semiconductor                         | 2               |
| Tile (Life360)                               | 2               |
| Chipolo                                      | 2               |
| Flipper Devices                              | 2               |
| Orbic / Kajeet RC400L (alternate USB mode)   | 2               |
| **TOTAL**                                    | **70**          |

## Reopening criteria (Stage 2)

The board should re-evaluate at v1.5.x:
- BLE trackers as surveillance: legitimate scope-expansion case (covert tracking via consumer trackers planted on persons/vehicles is in scope-spirit even if not in current §2.1 categories).
- Chip vendors (Espressif, Qualcomm, Nordic Semi, Quectel, Telit): cross-cut multiple device-vendor product lines — admitting them admits a much broader downstream identifier surface.
- EFF (Rayhunter): tool author rather than equipment vendor — could be admitted under a `defensive_tool` carveout (precedent: source-classification only, not a manufacturer identity).

## Discipline

- §11 #1 no fabrication: ✓ — no inferred admissions.
- §11 #8 no confidence drift: N/A — no promotions in this section.
- §11 #11 amendment-log: this defer is plan-source-authored, no new amendment.
