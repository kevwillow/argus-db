# §6.5 cert-issuer supply-chain enrichment log — MAC-192 Phase 6
Captured: 2026-05-20T19:51:46.229608+00:00
Plan vendors: 47

## 'Autel Robotics'
  APPLY mfr='Autel Robotics' (id=206): cert_issuer_supply_chain count=1
## 'Axis Communications'
  APPLY mfr='Axis Communications' (id=7): cert_issuer_supply_chain count=1
## 'Axon'
  APPLY mfr='Axon' (id=15): cert_issuer_supply_chain count=1
## 'BRINC'
  APPLY mfr='BRINC' (id=24): cert_issuer_supply_chain count=1
## 'Berla'
  APPLY mfr='Berla' (id=30): cert_issuer_supply_chain count=1
## 'BluePoint Alert'
  APPLY mfr='BluePoint Alert' (id=213): cert_issuer_supply_chain count=1
## 'BriefCam'
  APPLY mfr='BriefCam' (id=31): cert_issuer_supply_chain count=1
## 'Cellebrite'
  APPLY mfr='Cellebrite' (id=28): cert_issuer_supply_chain count=1
## 'Cisco Meraki'
  APPLY mfr='Cisco Meraki' (id=207): cert_issuer_supply_chain count=1
## 'Clearview AI'
  APPLY mfr='Clearview AI' (id=32): cert_issuer_supply_chain count=1
## 'Coban Technologies'
  APPLY mfr='Coban Technologies' (id=217): cert_issuer_supply_chain count=1
## 'Cradlepoint'
  APPLY mfr='Cradlepoint' (id=20): cert_issuer_supply_chain count=1
## 'DJI'
  APPLY mfr='DJI' (id=22): cert_issuer_supply_chain count=1
## 'Dahua'
  APPLY mfr='Dahua' (id=208): cert_issuer_supply_chain count=1
## 'Dedrone'
  APPLY mfr='Dedrone' (id=33): cert_issuer_supply_chain count=1
## 'Digital Ally'
  APPLY mfr='Digital Ally' (id=218): cert_issuer_supply_chain count=1
## 'Digital Receiver Technology'
  APPLY mfr='Digital Receiver Technology' (id=10): cert_issuer_supply_chain count=1
## 'DroneShield'
  APPLY mfr='DroneShield' (id=34): cert_issuer_supply_chain count=1
## 'Eagle Eye Networks'
  APPLY mfr='Eagle Eye Networks' (id=220): cert_issuer_supply_chain count=1
## 'Engility'
  APPLY mfr='Engility' (id=14): cert_issuer_supply_chain count=1
## 'Flock Safety'
  APPLY mfr='Flock Safety' (id=1): cert_issuer_supply_chain count=1
## 'Genetec'
  APPLY mfr='Genetec' (id=4): cert_issuer_supply_chain count=1
## 'Getac'
  APPLY mfr='Getac' (id=18): cert_issuer_supply_chain count=1
## 'Hak5'
  APPLY mfr='Hak5' (id=27): cert_issuer_supply_chain count=1
## 'Harris'
  APPLY mfr='Harris' (id=8): cert_issuer_supply_chain count=1
## 'Hikvision'
  APPLY mfr='Hikvision' (id=209): cert_issuer_supply_chain count=1
## 'Honeywell'
  STAGED for Phase 8
## 'Jacobs'
  APPLY mfr='Jacobs' (id=13): cert_issuer_supply_chain count=1
## 'Johnson Matthey PLC'
  APPLY mfr='Johnson Matthey PLC' (id=205): cert_issuer_supply_chain count=1
## 'Kenwood'
  APPLY mfr='Kenwood' (id=19): cert_issuer_supply_chain count=1
## 'KeyW'
  APPLY mfr='KeyW' (id=12): cert_issuer_supply_chain count=1
## 'L3Harris'
  APPLY mfr='L3Harris' (id=9): cert_issuer_supply_chain count=1
## 'Magnet Forensics'
  APPLY mfr='Magnet Forensics' (id=29): cert_issuer_supply_chain count=1
## 'Motorola Solutions'
  APPLY mfr='Motorola Solutions' (id=3): cert_issuer_supply_chain count=1
## 'PIPS Technology'
  APPLY mfr='PIPS Technology' (id=214): cert_issuer_supply_chain count=1
## 'Parrot'
  APPLY mfr='Parrot' (id=25): cert_issuer_supply_chain count=1
## 'Rekor'
  APPLY mfr='Rekor' (id=5): cert_issuer_supply_chain count=1
## 'Rhombus Systems'
  APPLY mfr='Rhombus Systems' (id=221): cert_issuer_supply_chain count=1
## 'Septier'
  APPLY mfr='Septier' (id=11): cert_issuer_supply_chain count=1
## 'Sierra Wireless'
  APPLY mfr='Sierra Wireless' (id=21): cert_issuer_supply_chain count=1
## 'Skydio'
  APPLY mfr='Skydio' (id=23): cert_issuer_supply_chain count=1
## 'SoundThinking'
  APPLY mfr='SoundThinking' (id=26): cert_issuer_supply_chain count=1
## 'Utility Inc'
  APPLY mfr='Utility Inc' (id=216): cert_issuer_supply_chain count=1
## 'Verkada'
  APPLY mfr='Verkada' (id=210): cert_issuer_supply_chain count=1
## 'Vigilant Solutions'
  APPLY mfr='Vigilant Solutions' (id=2): cert_issuer_supply_chain count=1
## 'WatchGuard'
  APPLY mfr='WatchGuard' (id=17): cert_issuer_supply_chain count=1
## 'Wolfcom'
  APPLY mfr='Wolfcom' (id=215): cert_issuer_supply_chain count=1

## Per-outcome counts
  applied: 46
  skipped_idempotent: 0
  honeywell_staged_vendor: 1
  honeywell_staged_attestation: 1
  halt_unresolved: 0

## Post-state sample readback (cert_issuer_supply_chain)
  Autel Robotics (id=206): [{"ct_log_cert_total":1112,"top_5_issuer_organizations":[["Let's Encrypt",712],["Google Trust Services",147],["DigiCert Inc",133],["Amazon",32],["Sectigo Limite
  Axis Communications (id=7): [{"ct_log_cert_total":4791,"top_5_issuer_organizations":[["Let's Encrypt",3225],["Amazon",1242],["DigiCert Inc",263],["\"GoDaddy.com",26],["Thawte Consulting cc
  Axon (id=15): [{"ct_log_cert_total":6467,"top_5_issuer_organizations":[["Let's Encrypt",3041],["Sectigo Limited",2106],["DigiCert Inc",1092],["COMODO CA Limited",153],["GeoTr
  DJI (id=22): [{"ct_log_cert_total":997,"top_5_issuer_organizations":[["Amazon",233],["DigiCert Inc",205],["\"GoDaddy.com",151],["Let's Encrypt",137],["Google Trust Services"
  Hikvision (id=209): [{"ct_log_cert_total":3655,"top_5_issuer_organizations":[["Let's Encrypt",2587],["DigiCert Inc",267],["Google Trust Services",262],["GlobalSign nv-sa",168],["\"
  Honeywell (id=211): null