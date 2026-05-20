# Phase 7 §7.2 — HALT-surface: identifier_type CHECK enum gap

**Dispatch ref:** [MAC-194](/MAC/issues/MAC-194) §7.2
**Halt criterion:** dispatch §Halt-criteria item 3 — *"New identifier_type proposed (e.g., `equipment_class_code`) NOT in CHECK enum → halt + surface (no auto-extend)"*
**Discipline:** §11 #11 (amendment-log discipline) — surface to CEO who handles the amendment.
**Validator stance:** HALT 177/177 §7.2 fccid.io grantee+equipment-class attestations (53 V2 + 124 V3). Do NOT auto-extend the CHECK enum.

## What the plan inputs propose

| Plan | Promotion count | Field carrying identifier_type intent | Distinct value(s) observed |
|------|----------------:|---------------------------------------|----------------------------|
| Wave I.14b `EXTRACTION_PLAN_V2` `.fccid_io_content_promotions[]` | 53 | `candidate_type` | `fcc_equipment_class_attestation` |
| Wave I.14c `EXTRACTION_PLAN_V3` `.fccid_io_extended_promotions[]` | 124 | (implicit: `equipment_class_code` + `grantee_code_3char` columns; no explicit `candidate_type` field) | `equipment_class_code` (implicit) |

Both plans converge on the same semantic — an attestation tying an FCC-EAS grantee code (3-char prefix) plus an equipment class code (3-char EAS rule-part code such as `TNB`/`PCB`/`DTS`) to a vendor. Neither shape exists in the current `identifiers.identifier_type` CHECK enum.

## CHECK enum current state (verbatim from `sqlite_master`)

`identifiers.identifier_type` admits, as of v1.4.1-integration-stage-1 head:

- Pre-CP13 (migration 0001): `oui, mac, mac_range, bssid, ssid_exact, ssid_pattern, ble_uuid, ble_service, device_fingerprint`
- CP13 (migration 0009): `ble_local_name, ble_characteristic, product_family_codename`
- CP14 (migrations 0011 + 0013 + 0014): `ble_manufacturer_id`; Drone-RID + proprietary protocol cluster (13); `alpr_model`
- CP20 (migration 0018): SAR-13 §S.3 vendor-anchored / device-naming cluster (14) — `ble_protocol_byte_table, ble_service_uuid, ble_company_id, frequency_band, ble_protocol_byte, operator_profile, x509_cert_sha256_prefix, ble_adv_interval, ble_payload_offset, firmware_sha256_hash, network_endpoint, firmware_image_variant, qualcomm_chip_format_id, firmware_branded_string`
- MAC-117 (migration 0019): round-2 vocab extension (7) — `asdstan_message_type, asdstan_enum_value, dji_protocol_struct_format, gpt_partition_uuid, chipset_codename, firmware_build_string, firmware_build_uuid`
- CP28 (migration 0023): Wave H desktop-axis vendor-registered non-BLE cluster (3) — `windows_installer_productcode_vendor_registered, windows_com_clsid_vendor_registered, vendor_document_uuid_cloud_reference`
- CP29 (migration 0024): Wave I vendor cloud-infrastructure hostname corpus (3) — `vendor_controlled_hostname, vendor_cloud_endpoint_url, vendor_controlled_hostname_deprecated`

**Neither** `fcc_grantee_code` / `equipment_class_code` / `fcc_equipment_class_attestation` is admitted.

## Cohort inventory (for CEO + board sizing of the CP31-class amendment)

### Grantee codes (3-char prefix) observed across V2+V3 (17 distinct)

```
2AG  PARROT DRONE SAS / PARROT FAURECIA AUTOMOTIVE SAS  (V3)
2AH  SZ DJI BaiWang Technology Co.,Ltd                  (V3)
2AL  Reveal Media Limited                               (V3)
ABY  Motorola Solutions, Inc.                           (V2)
ABZ  Motorola Solutions, Inc.                           (V2)
ARQ  Motorola Solutions, Inc.                           (V2)
EL5  Harris Corporation                                 (V3)
LL9  Sierra Wireless Inc                                (V3)
MKM  Motorola Solutions, Inc.                           (V2)
N7N  Sierra Wireless Inc.                               (V2+V3)
NK7  Harris Corporation                                 (V3)
PNF  Sierra Wireless, Inc                               (V3)
QQL  Sierra Wireless, Inc.                              (V3)
TWV  Sierra Wireless, Inc.                              (V3)
UXX  Cradlepoint, Inc.                                  (V3)
X4G  Axon Enterprise, Inc                               (V3)
YJV  Enforcement Video, LLC (d.b.a. WatchGuard Video)   (V3)
```

14 of 17 grantee codes already exist as authoritative rows in the local `fcc_grantees` table (sid=7 FCC EAS open-data CSV anchor). 3 do not (2AG, 2AH, 2AL) — those would be net-new fcc_grantees rows alongside any new identifier_type admission.

### Equipment class codes observed (17 distinct)

```
AMP  CBE  CPA  CPB  CYY  DSS  DTS  DXX  JBP  NII
PCB  PCE  PCT  TBC  TNB  TNT  TBC
```

(EAS rule-part codes; e.g. `DTS`=Digital Transmission System, `TNB`=Licensed Land Mobile Transmitter for Non-Broadcast use, etc.)

## Independent constraints that compound the halt

Even if the CHECK enum were extended, the §7.2 cohort would still bump into one further halt under the current discipline envelope:

- **`Numerex Corporation` (9 V3 rows) is NOT in the canonical `manufacturers` lexicon.** Per dispatch halt criterion #4 (manufacturer not in canonical lexicon → halt + surface; no auto-admit, per Honeywell precedent), those 9 rows would also need a separate admission ratification.
- **`PARROT FAURECIA AUTOMOTIVE SAS` (subset of 2AG) is the automotive-electronics arm of Parrot, not the drone arm.** Mapping to canonical `Parrot` (currently `primary_category='drone'`) without filing-level disambiguation would push automotive identifiers onto the drone manufacturer row — a §4 device-category provenance issue worth surfacing alongside the CP31-class amendment.

## Recommended CEO+board ratification path (proposal — NOT acted on by Validator)

Validator surfaces; CEO+board decides. Proposal sketch:

1. **CP31-class amendment** (or whichever CP number is next) — extend `identifiers.identifier_type` CHECK enum (migration 0025-class) to admit two new types:
   - `fcc_grantee_code` — 3- to 5-char FCC EAS grantee prefix
   - `equipment_class_code` — 3-char FCC EAS equipment-class code (always paired with a grantee via §11 #7 provenance)
   The paired-identifier discipline (CP14 / migration 0012) already supports the pairing semantics via `paired_identifier_id` + `pair_kind`; a `pair_kind='fcc_grantee_equipment_class'` admission would also be required.
2. **CP15 source_type ceiling re-attestation** for fccid.io as `crowdsourced` (sid=51 already crowdsourced) — paste-not-cite the ceiling that applies to the 177-row cohort.
3. **Numerex admission ratification** (separate dispatch, mirrors the Honeywell precedent in `_phase_6_wave_i_14a/honeywell_staged_for_phase_8.md`).
4. **2AG split / Parrot automotive vs drone device_category** — guidance.

After ratification, the 177-row cohort can be re-dispatched as a sequenced Phase 7-bis (or rolled into v1.4.2 / v1.5.0).

## What did NOT halt (executed in this heartbeat)

- §7.0 — 1 row (`api.dbeta.me` `vendor_controlled_hostname` conf=85) — applied; see `api_dbeta_me_staging_log.md`.
- §7.3 — 1 stub absence (Parrot Drone SAS / `2AG6IWCH01`) — applied to `manufacturers.notes.fcc_grantee_documented_absences[]`; see `stub_absence_log.md`.
- §7.4 — 947 filing URL inventory (709 V2 + 238 V3) — staged to `manufacturers.notes.v1_5_0_filing_url_inventory[]`; see `filing_url_inventory_log.md`.

§7.0/§7.3/§7.4 do NOT depend on the CHECK enum because they do not promote `fcc_grantee_code`/`equipment_class_code` identifiers — they stage informational JSON on existing `manufacturers` rows (which has no CHECK constraint on notes) plus one `vendor_controlled_hostname` that IS in the enum.

## §11 discipline scoring

| Rule | Outcome |
|------|---------|
| §11 #1 (no fabrication) | Honored — halt instead of fabricating an enum extension. |
| §11 #7 (provenance) | Honored — provenance preserved by holding the 177-row cohort; no orphan promotions. |
| §11 #8 (no confidence drift) | Honored — no confidence assignment without admitted identifier_type. |
| §11 #11 (amendment-log discipline) | Honored — surfaced to CEO; Validator does not write to `BIBLE_AMENDMENTS.md`. |
