# Phase 7-bis — Pre-flight (SAR-13 + sub-rule §3399, post-CP31)

**Dispatch:** [MAC-201](/MAC/issues/MAC-201)
**Branch HEAD:** `cbb0cd7` (`v1.4.1-integration-stage-1`)
**Pre-apply DB backup:** `db/argus.db.mac201_pre_phase7bis_backup` (313,360,384 bytes)

## §11 #1 — paste-not-cite live state

### identifier_type CHECK enum (56 values total — CP31 ratified)

Captured verbatim from `sqlite_master.sql` for `identifiers`:

```
'oui', 'mac', 'mac_range', 'bssid',
'ssid_exact', 'ssid_pattern',
'ble_uuid', 'ble_service',
'device_fingerprint',
'ble_local_name', 'ble_characteristic',
'product_family_codename',
'ble_manufacturer_id',
'drone_id_prefix','icao_24bit_address','rf_channel','burst_cadence_ms',
'bandwidth_mhz','device_class_id','rf_burst_duration','rf_protocol_constant',
'wifi_aware_service_name','wifi_ie_element_id','bluetooth_le_pdu_type',
'wifi_frame_control_subtype','wifi_nan_param_signature',
'alpr_model',
'ble_protocol_byte_table','ble_service_uuid','ble_company_id','frequency_band',
'ble_protocol_byte','operator_profile','x509_cert_sha256_prefix','ble_adv_interval',
'ble_payload_offset','firmware_sha256_hash','network_endpoint','firmware_image_variant',
'qualcomm_chip_format_id','firmware_branded_string',
'asdstan_message_type','asdstan_enum_value','dji_protocol_struct_format','gpt_partition_uuid',
'chipset_codename','firmware_build_string','firmware_build_uuid',
'windows_installer_productcode_vendor_registered',
'windows_com_clsid_vendor_registered',
'vendor_document_uuid_cloud_reference',
'vendor_controlled_hostname','vendor_cloud_endpoint_url','vendor_controlled_hostname_deprecated',
'fcc_grantee_code','equipment_class_code'
```

Count verified: **56 values**. CP31 cluster present:
- `fcc_grantee_code` ✓ admitted
- `equipment_class_code` ✓ admitted

### pair_kind CHECK enum (5 values total)

```
pair_kind IS NULL
  OR pair_kind IN (
      'la_bit_flip',
      'frdid_sibling',
      'vendor_as_container',
      'firmware_generation',
      'fcc_grantee_equipment_class'    -- CP31 (migration 0025)
  )
```

`fcc_grantee_equipment_class` ✓ admitted.

### sources sid=51

```
(51, 'fccid.io', 'crowdsourced')
```

source_type='crowdsourced' → CP15 ceiling 75 binding for single-source rows.

### manufacturers id=222 (Parrot Automotive arm) + id=25 (Parrot hub)

```
id=222: ('Parrot Automotive', primary_category='automotive_telematics',
         is_arm=1, query_default='hidden_arm', parent_manufacturer_id=25)
id=25:  ('Parrot',            primary_category='drone',
         is_arm=0, query_default='visible')
```

✓ Hub-and-spoke confirmed: 2AG-attested rows route to id=222 (NOT id=25).

### Predecessor counts

| Metric | Live value | Issue claim | Match |
|--------|-----------:|------------:|:-----:|
| identifiers (all) | 35,252 | — | n/a |
| identifiers active (superseded_by IS NULL) | **34,910** | 34,910 | ✓ |
| raw_observations | 146,219 | — | n/a |

All discipline-envelope gates pass. Proceeding to plan-input ingestion.
