# MAC-192 Phase 6 — Preflight SAR-13 + sub-rule §3399

Captured: 2026-05-20

## PRAGMAs
- journal_mode: delete
- foreign_keys: 0 (off — same as Phase 5 baseline)
- busy_timeout: 5000
- synchronous: 2 (FULL)

## DB checkpoint (matches dispatch baseline)
- identifiers WHERE superseded_by IS NULL: **34,796** ✓
- identifiers total: **35,138** ✓
- raw_observations: **146,218** ✓
- behavioral_signatures: **131** ✓
- manufacturers: **51** ✓
- conflicts: **36** ✓
- PRAGMA integrity_check: **ok** ✓

## Schema CHECK-enum re-attestation
- `identifiers.identifier_type` admits: oui, ssid_pattern, ble_local_name, ble_service_uuid, product_family_codename, rf_channel, bandwidth_mhz, vendor_controlled_hostname (all 7 + CP29 hostname). All 114 candidate types covered ✓
- `identifiers.device_category`: 12-value enum (alpr, imsi_catcher, body_cam, police_radio, drone, gunshot_detect, hacking_tool, covert_cam, gps_tracker, face_recog, drone_detect, unknown). raw_observations.candidate_category uses non-canonical labels (surveillance_camera, fleet_router, gunshot_sensor, forensics, in_car_camera, …) — applying convention mapping per existing Hikvision/Sierra/Cellebrite/SoundThinking/Axon canonical rows (surveillance_camera→unknown, fleet_router→unknown, gunshot_sensor→gunshot_detect, body_cam_trigger/in_car_camera→body_cam, forensics→hacking_tool) ✓
- `identifiers.source_type`: candidates from sid 15/16/18/20/21/22/23/24/26/28/30/31/32/33 = `crowdsourced`; sid 37/41/43 = `academic`. Inheritance resolved at apply-time from `sources.source_type` ✓
- `behavioral_signatures` column list verified: id, signature_name, cellular_generation, threshold_json, evidence_json, source_id, source_file_relative, source_line, confidence, device_category, notes, created_at, updated_at + UNIQUE(signature_name, source_id, cellular_generation) ✓
- `manufacturers.notes` is TEXT (json-capable); existing rows have JSON blobs ✓

## Canonical manufacturer resolution
All 47 unique manufacturers (14 from 114 candidates + 47 from cert-issuer enrichment, deduped) resolve to existing canonical rows. ZERO unresolved. No auto-admission required.

Notable: `Honeywell` exists in canonical (admitted MAC-178, `notes.admission_basis='documented_absence_only'` stub). Per dispatch §6.5 + envelope, Honeywell-targeted rows are STAGED to `honeywell_staged_for_phase_8.md` — the MAC-178 stub row is NOT modified in Phase 6.

## Halt surface — Wave I.13 api.dbeta.me (1 of 114)
The Wave I.13 `api.dbeta.me` candidate (DJI vendor_controlled_hostname) lacks `source_url` + `raw_obs_id` in the plan input (only `evidence_source` prose). Per §11 #1 strict read ("halt if any candidate lacks source_excerpt + source_url"), this candidate is HELD. Sibling hosts (`account.dbeta.me`, `r-m.dbeta.me`, `repair.dbeta.me`, `test-app-h5.dbeta.me`) already exist in identifiers at confidence=85 via sid=66 wave_i_aggregate. Surfacing for CEO to authorize a Wave I.13 staging path (stage raw_observation first, then promote).

## Effective §6.2 identifierrow count
**113** of 114 will promote in this heartbeat. The api.dbeta.me halt is surfaced; no fabrication.

## Backup
`db/argus.db.mac192_pre_phase6_backup` created (291 MB, identical to live).
