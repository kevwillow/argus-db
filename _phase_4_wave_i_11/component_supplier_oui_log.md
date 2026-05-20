# §4.5 Component-supplier OUI enrichment log — MAC-190 Phase 4
Captured: 2026-05-20T19:00:15.442619+00:00

## Autel Robotics (id=206)
  - pre: existing component_supplier_ouis = []
  - **APPLY**: appended OUI 00:01:22 (Trend Communications, Ltd.)
  - post: component_supplier_ouis count=1
## Hikvision (id=209)
  - pre: existing component_supplier_ouis = []
  - **APPLY**: appended OUI 00:05:00 (Cisco Systems, Inc)
  - post: component_supplier_ouis count=1

## Verification readback
- mid=206 Autel Robotics: component_supplier_ouis = [{"oui":"00:01:22","supplier_organization":"Trend Communications, Ltd.","ieee_registry":"MA-L","component_context":"WiFi/networking chipset embedded reference","evidence_source":"Wave I.10 binary string extraction","evidence_run_id":"wave_i_10_continuation","framing":"supply-chain metadata; NOT a vendor identifier \u2014 supplier OUI is the silicon/chipset vendor, not the integrating cohort vendor","integration_dispatch":"MAC-190","cp_anchor":"phase_4_\u00a74.5_component_supplier_metadata","integration_at_utc":"2026-05-20T19:00:15.442619+00:00"}]
- mid=209 Hikvision: component_supplier_ouis = [{"oui":"00:05:00","supplier_organization":"Cisco Systems, Inc","ieee_registry":"MA-L","component_context":"WiFi/networking chipset embedded reference","evidence_source":"Wave I.10 binary string extraction","evidence_run_id":"wave_i_10_continuation","framing":"supply-chain metadata; NOT a vendor identifier \u2014 supplier OUI is the silicon/chipset vendor, not the integrating cohort vendor","integration_dispatch":"MAC-190","cp_anchor":"phase_4_\u00a74.5_component_supplier_metadata","integration_at_utc":"2026-05-20T19:00:15.442619+00:00"}]