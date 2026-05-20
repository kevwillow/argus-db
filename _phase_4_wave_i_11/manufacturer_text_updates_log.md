# §4.3 Manufacturer-text UPDATE log — MAC-190 Phase 4 Wave I.11
Captured: 2026-05-20T18:55:19.528049+00:00Z

## Per-entry application log

### Axis: ieee_oui_registries

- **APPLY** raw='Honeywell Safety Products USA, Inc' -> Honeywell (canonical id=211, tier=3, methodology=canonical_substring)
  - id=5520 old='Honeywell Safety Products USA, Inc' -> new='Honeywell' ✓
  - id=13043 old='Honeywell Safety Products USA, Inc' -> new='Honeywell' ✓
- **APPLY** raw='Jacobs Technology, Inc.' -> Jacobs (canonical id=13, tier=3, methodology=canonical_substring)
  - id=9008 old='Jacobs Technology, Inc.' -> new='Jacobs' ✓
  - id=11348 old='Jacobs Technology, Inc.' -> new='Jacobs' ✓
- **APPLY** raw='Autel Robotics USA LLC' -> Autel Robotics (canonical id=206, tier=3, methodology=canonical_substring)
  - id=6883 old='Autel Robotics USA LLC' -> new='Autel Robotics' ✓
- **APPLY** raw='Genetec Inc.' -> Genetec (canonical id=4, tier=3, methodology=canonical_substring)
  - id=17151 old='Genetec Inc.' -> new='Genetec' ✓
- **DEFER** raw='Harris Designs of NRV, Inc.' rows_in_plan=1 -> Harris | reason: SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md
- **APPLY** raw='Honeywell Analytics Ltd' -> Honeywell (canonical id=211, tier=3, methodology=canonical_substring)
  - id=6352 old='Honeywell Analytics Ltd' -> new='Honeywell' ✓
- **APPLY** raw='Honeywell GNO' -> Honeywell (canonical id=211, tier=3, methodology=canonical_substring)
  - id=22509 old='Honeywell GNO' -> new='Honeywell' ✓
- **APPLY** raw='Honeywell Sensotec' -> Honeywell (canonical id=211, tier=3, methodology=canonical_substring)
  - id=21915 old='Honeywell Sensotec' -> new='Honeywell' ✓
- **APPLY** raw='Honeywell spol. s.r.o. HTS CZ o.z.' -> Honeywell (canonical id=211, tier=3, methodology=canonical_substring)
  - id=19756 old='Honeywell spol. s.r.o. HTS CZ o.z.' -> new='Honeywell' ✓
- **APPLY** raw='Septier Communication Ltd' -> Septier (canonical id=11, tier=3, methodology=canonical_substring)
  - id=19170 old='Septier Communication Ltd' -> new='Septier' ✓
- **DEFER** raw='Shanghai Dahua Scale Factory' rows_in_plan=1 -> Dahua | reason: SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md
- **DEFER** raw='AXIS CORPORATION' rows_in_plan=1 -> Axis Communications | reason: SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md
- **DEFER** raw='AXIS Sp z o.o.' rows_in_plan=1 -> Axis Communications | reason: SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md
- **DEFER** raw='Ace Axis Limited' rows_in_plan=1 -> Axis Communications | reason: SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md
- **APPLY** raw='Autel lntelligent Technology Corp.,Ltd' -> Autel Robotics (canonical id=206, tier=4, methodology=alias_substring)
  - id=8294 old='Autel lntelligent Technology Corp.,Ltd' -> new='Autel Robotics' ✓
- **DEFER** raw='Axis Electronics' rows_in_plan=1 -> Axis Communications | reason: SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md
- **APPLY** raw='Eagle Eye Networks, Inc' -> Eagle Eye Networks (canonical id=220, tier=4, methodology=alias_substring)
  - id=9404 old='Eagle Eye Networks, Inc' -> new='Eagle Eye Networks' ✓
- **DEFER** raw='Flock Audio Inc.' rows_in_plan=1 -> Flock Safety | reason: SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md
- **DEFER** raw='Rhombus Europe' rows_in_plan=1 -> Rhombus Systems | reason: SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md

### Axis: bluetooth_sig

- **APPLY** raw='Hangzhou Hikvision Digital Technology Co., Ltd.' -> Hikvision (canonical id=209, tier=3, methodology=canonical_substring)
  - id=1549 old='Hangzhou Hikvision Digital Technology Co., Ltd.' -> new='Hikvision' ✓
- **APPLY** raw='JVC KENWOOD Corporation' -> Kenwood (canonical id=19, tier=3, methodology=canonical_substring)
  - id=1817 old='JVC KENWOOD Corporation' -> new='Kenwood' ✓
- **APPLY** raw='PARROT AUTOMOTIVE SAS' -> Parrot (canonical id=25, tier=3, methodology=canonical_substring)
  - id=4884 old='PARROT AUTOMOTIVE SAS' -> new='Parrot' ✓
- **APPLY** raw='SZ DJI TECHNOLOGY CO.,LTD' -> DJI (canonical id=22, tier=3, methodology=canonical_substring)
  - id=2872 old='SZ DJI TECHNOLOGY CO.,LTD' -> new='DJI' ✓
- **APPLY** raw='RHOMBUS SYSTEMS, INC.' -> Rhombus Systems (canonical id=221, tier=4, methodology=alias_substring)
  - id=3189 old='RHOMBUS SYSTEMS, INC.' -> new='Rhombus Systems' ✓

### Axis: faa_remote_id

- **DEFER** raw='Harris Aerial' rows_in_plan=2 -> Harris | reason: SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md

### Axis: wireshark_manuf

- **DEFER** raw='Autel Robotics USA LLC' rows_in_plan=1 -> Autel Robotics | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Avigilon Alta' rows_in_plan=1 -> Avigilon | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Axis Communications AB' rows_in_plan=4 -> Axis Communications | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Axon Enterprise, Inc.' rows_in_plan=1 -> Axon | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Axon Networks Inc.' rows_in_plan=2 -> Axon | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Axon Networks, Inc.' rows_in_plan=1 -> Axon | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='CelleBrite Mobile Synchronization' rows_in_plan=1 -> Cellebrite | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Cisco Meraki' rows_in_plan=55 -> Cisco Meraki | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Digital Receiver Technology' rows_in_plan=1 -> Digital Receiver Technology | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Dji Baiwang Technology Co Ltd' rows_in_plan=2 -> DJI | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Flock Safety' rows_in_plan=1 -> Flock Safety | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='GENETEC Corporation' rows_in_plan=1 -> Genetec | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Genetec Inc.' rows_in_plan=3 -> Genetec | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Hangzhou Hikvision Digital Technology Co.,Ltd.' rows_in_plan=82 -> Hikvision | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Harris Adacom Corporation' rows_in_plan=1 -> Harris | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Harris Corporation' rows_in_plan=3 -> Harris | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Harris Designs of NRV, Inc.' rows_in_plan=1 -> Harris | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Harris Government Communications' rows_in_plan=1 -> Harris | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell' rows_in_plan=16 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell (China) Co., LTD' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Analytics' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Analytics Ltd' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell CMSS' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Co., Ltd. (KOREA)' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Connected Building' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Environmental & Combustion Controls' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Environmental & Combustion Controls (Tianjin) Co., Ltd.' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Fire System (Shanghai) Co,. Ltd.' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell GNO' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell GmbH' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell International' rows_in_plan=2 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell International Inc' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Life Safety' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell SPS' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Safety Products (Shanghai) Co.,Ltd' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Safety Products USA, Inc' rows_in_plan=2 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Security (China) Co., Ltd.' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Sensotec' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell Video Systems' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Honeywell spol. s.r.o. HTS CZ o.z.' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='JVC KENWOOD Corporation' rows_in_plan=1 -> Kenwood | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Jacobs Technology, Inc.' rows_in_plan=2 -> Jacobs | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Johnson Matthey' rows_in_plan=1 -> Johnson Matthey PLC | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Kenwood Corporation' rows_in_plan=1 -> Kenwood | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='KeyW Corporation' rows_in_plan=1 -> KeyW | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Motorola Solutions Inc.' rows_in_plan=4 -> Motorola Solutions | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Motorola Solutions Malaysia Sdn. Bhd.' rows_in_plan=3 -> Motorola Solutions | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Neology' rows_in_plan=1 -> PIPS Technology | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Parrot Sa' rows_in_plan=5 -> Parrot | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Prama Hikvision India Private Limited' rows_in_plan=2 -> Hikvision | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Rhombus Systems' rows_in_plan=1 -> Rhombus Systems | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='SZ DJI Ronin Technology Co., Ltd.' rows_in_plan=1 -> DJI | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Securite Communications / Honeywell' rows_in_plan=1 -> Honeywell | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Septier Communication Ltd' rows_in_plan=1 -> Septier | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Shanghai Dahua Scale Factory' rows_in_plan=1 -> Dahua | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Skydio Inc.' rows_in_plan=1 -> Skydio | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Sz Dji Technology Co.,Ltd' rows_in_plan=10 -> DJI | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Verkada Inc' rows_in_plan=1 -> Verkada | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='WatchGuard Technologies, Inc.' rows_in_plan=2 -> WatchGuard | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='WatchGuard Video' rows_in_plan=1 -> WatchGuard | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Zhejiang Dahua Technology Co., Ltd.' rows_in_plan=27 -> Dahua | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Zhejiang Dahua Technologyco.,Ltd' rows_in_plan=4 -> Dahua | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11
- **DEFER** raw='Zhejiang Dahua Zhilian Co.,Ltd' rows_in_plan=1 -> Dahua | reason: spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11

## Summary

- applied row UPDATEs: 18
- skipped sentinel rows: 0
- skipped not-found entries: 0
- skipped superseded rows: 0
- deferred entries: 72
- deferred rows (in-plan rows_affected sum): 284

## Verification queries (post-apply)

- id=5520: manufacturer='Honeywell' (post-update)
- id=13043: manufacturer='Honeywell' (post-update)
- id=6883: manufacturer='Autel Robotics' (post-update)
- id=17151: manufacturer='Genetec' (post-update)
- id=1549: manufacturer='Hikvision' (post-update)
- id=1817: manufacturer='Kenwood' (post-update)
- id=2872: manufacturer='DJI' (post-update)
- id=3189: manufacturer='Rhombus Systems' (post-update)