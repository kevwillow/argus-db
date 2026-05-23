# Changelog

All notable changes to Argus are documented in this file. The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project does not yet adopt semantic-versioning for the dataset shape itself — see "Schema versioning" below for the migration-ledger discipline.

## TL;DR

**Argus tracks surveillance vendor identifiers** — MAC ranges, FCC grantee codes, hostnames, certificate SANs, BLE company IDs, IMEI Type Allocation Codes, and dozens of other identifier classes — used by US law enforcement and adjacent surveillance deployments.

**Each version (v1.X.Y) bundles** a cycle of source admissions, manufacturer admissions, schema migrations, and bible-amendment ratifications. Headline metrics per version: schema_version, source count, manufacturer count, active identifier count, Lynceus high-confidence export count.

**To read entries below:** find your version of interest; the `### Schema` section lists migration deltas; the `### Data` section lists count deltas; the `### Bible amendments` section lists the formal discipline codifications (Correction Passes + SAR rules); the `### Halts encountered` section lists any halt-class issues that surfaced during the cycle and their ratifications.

**For the user-facing overview** of what Argus is and how to use the exports, start with [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

---

## [Unreleased]

(No unreleased changes since v1.5.2.)

[v1.5.2] — 2026-05-23
This release closes a parallel work cycle covering CCTV camera vendors (Track A) and IMEI TAC research (Track B), and folds in the v1.5.1 documentation restructure.
Highlights

Added 146 new active identifiers across 8 CCTV camera vendors
New identifier type: network_discovery_protocol_pattern, covering vendor camera-discovery protocols (Hikvision SADP, Dahua AirKiss/SmartConfig, Axis ONVIF WS-Discovery, Tiandy SADP-style)
Extractor upgraded to v5 with safer IMEI TAC handling, four new false-positive filters, and 43 additional cellular-modem vocabulary tokens
New utility for correctly extracting base APKs from .xapk, .apkm, and .apks bundles (replaces a heuristic that was silently picking the wrong file)

Schema

schema_version: 27 → 28
identifier_type enum: 57 → 58 values

Data

Sources: 73 (unchanged)
Manufacturers: 92 (unchanged)
Active identifiers: 35,812 → 35,958 (+146)
Behavioral signatures: 201 (unchanged)

Per-vendor identifier additions
Hikvision 46 · Tiandy 53 · Axis 21 · Verkada 10 · Avigilon 9 · Dahua 7
IMEI TAC research: notable negative result
A 25-vendor sweep across cellular gateways, fleet telematics, mobile ID apps, trail cameras, ankle monitors, consumer GPS trackers, and drone pilot apps yielded zero unique IMEI TACs.
The reason matters: modern Android apps fetch TACs at runtime, dispatch them server-side, or hide numeric literals in encrypted strings. Companion-app analysis is no longer a productive way to harvest TACs.
Future TAC work will pivot to four better-suited sources:

GSMA TAC API and public TAC list mirrors
FCC OET authorization grant filings (grantee + product codes map to TAC ranges)
OTA firmware analysis of cellular modules (Quectel, Sierra, u-blox)
Android apps that bundle TAC lookup tables as assets (TacDB, IMEI Info, Phone INFO Samsung)

Documentation
README, CHANGELOG, and project state docs refreshed and verified against the live database.

[v1.5.0] — 2026-05-22
This release significantly expands the manufacturer lexicon through parallel sessions covering military/federal and commercial/consumer device makers.
Highlights

Manufacturer lexicon: 52 → 92 vendors
Three new device categories: cctv_camera, persistent_surveillance, through_wall_radar
848 new active identifiers
New imei_tac identifier type (admitted for future use; no rows promoted this cycle)
Most directly deployable additions: 35 FCC grantee codes and 2 ICAO 24-bit Mode-S addresses for CBP MQ-9 aircraft (via adsb.lol)

Schema

schema_version: 26 → 27
device_category enum: 13 → 16 (in both identifiers and behavioral_signatures)
identifier_type enum: 56 → 57

Data

Sources: 71 → 73 (added GitHub Code Search REST API and adsb.lol v2)
Manufacturers: 52 → 92 (+40)
Active identifiers: 34,964 → 35,812 (+848)

New manufacturer cohorts

Counter-drone / counter-UAS (11): Anduril, Fortem, Citadel Defense, Black Sage, D-Fend, AeroDefense, Echodyne, Liteye, Robin Radar, MyDefence, Sensofusion
Border / persistent surveillance (6): Elbit Systems of America, General Atomics, TCOM, Persistent Surveillance Systems, Northrop Grumman, Lockheed Martin
Through-wall radar (3): Camero, NIITEK, TiaLinx
IMSI catcher (1): Rohde & Schwarz
Fleet telematics (7): Geotab, Verizon Connect, Samsara, Motive, Lytx, Omnitracs, Trimble
CCTV camera / VMS (7): Hanwha Vision, Bosch Security Systems, Milestone Systems, Pelco, Uniview, Tiandy, Vivotek
Electronic monitoring (5): BI Incorporated, Attenti, STOP, Sentinel Offender Services, Track Group

Retroactive recategorization
Seven existing camera vendors moved to the new cctv_camera primary category: Hikvision, Dahua, Axis Communications, Avigilon, Verkada, Eagle Eye Networks, Rhombus Systems.
Documentation
README, CHANGELOG, data dictionary, credits, methodology, and project state docs all refreshed.

[v1.4.1] — 2026-05-21
This release adds automotive telematics as a tracked device category and introduces schema support for multi-arm manufacturer relationships (parent/subsidiary structure).
Highlights

New automotive_telematics device category
Added FCC Equipment Authorization System identifier types
First multi-arm vendor admission: Parrot Automotive as a hidden arm of Parrot

Schema

schema_version: 25 → 26
device_category enum: 12 → 13 (across both identifiers and behavioral_signatures tables)
identifier_type enum: 54 → 56 (added fcc_grantee_code, equipment_class_code)
pair_kind enum: 4 → 5 (added fcc_grantee_equipment_class)
manufacturers table: 3 new columns for parent/arm relationships (parent_manufacturer_id, is_arm, query_default)

Data

Sources: 66 → 71 (added 5 manufacturer apps: Hikvision Hik-Connect, Dahua DMSS, Motorola Solutions WAVE PTT, Parrot FreeFlight 6, DJI Industry Pilot)
Manufacturers: 51 → 52 (+ Parrot Automotive)
Active identifiers: 34,792 → 34,964 (+172)
Raw observations: ~146,573

Documentation

New: docs/lynceus_handoff_v1_4_1.md — integration handoff for downstream consumers
README, CHANGELOG, data dictionary, credits, and methodology refreshed for v1.4.1


## [v1.4.0] — 2026-05-20

### What's new in v1.4.0

Argus v1.4.0 lands the **vendor cloud-infrastructure hostname corpus** from the 4-wave Wave I/I.5/I.6/I.7 autonomous extraction effort. 12,590 cumulative unique hostnames flowed from 8 extraction source-classes through Phase 2 FP-scrub (97.21% survivor rate, flagged for manual top-50 GitHub-sourced calibration as carry-forward) into 12,239 net-new identifiers (11,674 `vendor_controlled_hostname` + 565 `vendor_controlled_hostname_deprecated`) across all 51 canonical vendors. Net active identifier count grows 22,553 → **34,792** (+54.3%); raw_observations 133,830 → 146,188 (+12,358 with full provenance lineage); sources 53 → 66 (+13: crt.sh CT logs + Wayback CDX + GitHub vendor first-party + 5 RIR RDAP endpoints + npm/PyPI/RubyGems + bucket payload class + Wave I extraction methodology umbrella).

The headline marquee finding is **`hppki.honeywell.com` promoted at confidence=99** (firmware-cert ceiling) via 4-source independent corroboration: 2 Honeywell OTA signing certificates recovered from CT40 Android firmware META-INF/com/android/otacert (issuer `C=US, O=Honeywell International Inc., OU=ACS, CN=Honeywell CodeSign RSA CA`; sha256 `60a8cf8feeb33926366776b395d6c8d9334bd8b42038b85563622ce0a1d0745b`) + crt.sh CT log attestation + binary Class A extraction + bucket payload Class A_bucket_payload_firmware. This is the strongest possible attribution chain in the Argus framework — firmware-embedded cert + vendor-signed code-signing CA + multi-source-class corroboration.

Migration 0024 extends the `identifier_type` CHECK enum 51 → 54 with three CP29 value classes (`vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`). Two candidate CP29 value classes deferred per conservative ≥1-evidence gate: `vendor_asn_prefix` (Wave I class G halted url_pattern_issue; 0 findings) and `vendor_controlled_ip` (cert IP-SAN sub-passes 0/0/0 across Wave I.5/I.6/I.7). Both reserved for CP30 / migration 0025 when empirical observation surfaces.

### Source admissions (13 new)

| sid | name | source_type | source_class |
|---|---|---|---|
| 54 | Certificate Transparency Logs — crt.sh aggregator | primary_registry | B (CT log aggregator) |
| 55 | Internet Archive Wayback Machine — CDX | crowdsourced | K (public archive temporal) |
| 56 | GitHub — vendor first-party content | manufacturer_app | I (vendor source/README) |
| 57-61 | ARIN/RIPE/APNIC/LACNIC/AFRINIC RDAP | primary_registry | G (RIR; infrastructure-only admission for Wave I-prime) |
| 62-64 | npm Registry / PyPI / RubyGems | manufacturer_app | J (public package registry) |
| 65 | Vendor Public Cloud-Storage Bucket Payload (S3-class) | manufacturer_app | A_bucket_payload (SAR-13.5 attribution-gate-binding) |
| 66 | Wave I — Vendor Cloud-Infrastructure Hostname Corpus Extraction | manufacturer_app | A/C/D/F umbrella (extraction methodology) |

Each admission carries `ratification_band` + `source_class_full_name` + admission metadata in `sources.notes` JSON per CP14/CP16 pattern. Source_type CHECK enum maps to closest existing value (no source_type enum extension this release; CP30 candidate for 5 new enum values deferred to Wave I-prime).

### Confidence-band ladder per CP29 §2

- **`vendor_controlled_hostname`**: 75-90 single-source default; 85-95 cross-source (CP24 independence); 95-99 firmware-embedded cert chain
- **`vendor_cloud_endpoint_url`**: 80-90 default; 90-97 with binary + CT log + sitemap multi-source corroboration
- **`vendor_controlled_hostname_deprecated`**: 80-87 default (NXDOMAIN-verified at extraction time)

### Phase 5 promotion empirical anchors (v1.4.0)

```
inserted identifiers:                  12,239
  vendor_controlled_hostname:          11,674
  vendor_controlled_hostname_deprecated:   565
per confidence band:
  conf=99 (firmware-cert ceiling):          1   (hppki.honeywell.com)
  conf=97 (cross-source + §8.3 lift):     108   (lifted candidates per CP24 independence)
  conf=87 (deprecated default high):      565   (NXDOMAIN-verified)
  conf=85 (default high single-source): 11,565   (most common — single CT-log attestation)
§8.3 lifts applied:                       108   (per wave_i_lift_candidates_synthesis.json)
raw_observations FK-chained:           12,358
```

### Manufacturer alias enrichment

6 novel Subject DN O / firmware-cert observations appended to canonical manufacturers.aliases:

- **Autel Robotics** (mfg_id=206): appended `Autel Intelligent Technology Corp.` (3 live-cert observations)
- **Axis Communications** (mfg_id=7): appended `Axis Communications AB` (2 live-cert observations)
- **Cisco Meraki** (mfg_id=207): appended `Meraki LLC` (2 live-cert observations)
- **Getac** (mfg_id=18): appended `Getac Technology Corporation` (1 live-cert observation)
- **Jacobs** (mfg_id=13): appended `Jacobs Solutions Inc.` (1 live-cert observation)
- **Honeywell** (mfg_id=211): appended `Honeywell International Inc.` (firmware OTA cert — added in post-ship corrective pass; the main Phase 6 enrichment script omitted Honeywell from its vendor-key-to-canonical mapping)

**Honeywell International Inc.** observed in firmware-embedded code-signing cert. Honeywell IS already in the canonical 51-vendor lexicon (mfg_id=211, canonical_name "Honeywell" with aliases "Honeywell Pro-Watch, Honeywell International, Honeywell Building Technologies"); the firmware-derived legal-entity string `Honeywell International Inc.` has been appended as a 4th alias to that row. (Post-ship corrective: the original Phase 6 enrichment script omitted `honeywell` from its vendor-key-to-canonical mapping and so missed this alias-merge during the main pass.)

### Bible amendments

- **CP29** — vendor hostname corpus value_classes (3 codified, 2 deferred)
- **SAR-13** — runguide-schema-fabrication discipline (PRAGMA-verify all column names + types prior to any SQL drafting against canonical schema)
- **SAR-13.5** — bucket attribution discipline (content-based attribution gate before any public-bucket-derived promotion; three-state classification: confirmed / rejected_slug_collision / ambiguous_operator_review_required)
- **SAR-15** *(post-ship codification, board comment 2026-05-20)* — per-vendor probe-scope discipline (per-vendor extraction passes must respect the rationale of the vendor's canonical admission; surfaced by 252 Johnson Matthey corporate-IT hostnames that surfaced from a vendor admitted for industrial-MAC-cohort completeness, not surveillance-axis hostname extraction; 252 rows flagged via `notes.scope_review_required=true` for Wave I-prime / v1.4.1 operator review per SAR-15)
- **SAR-15.5** *(post-ship codification, board comment 2026-05-20)* — Validator-role independent close-out audit discipline for large-ship cycles (≥10 phases / ≥10k promotions / ≥3 new sources / ≥1 new migration); surfaced by the Honeywell-in-lexicon miss the main self-executed pass missed

### Lynceus export disposition

`argus_export.json` (Lynceus, conf floor 30) and `argus_export_high_confidence.json` (Lynceus, conf floor 70) sizes are unchanged vs v1.3.0. All 12,239 v1.4.0 cloud-infrastructure hostnames carry `device_category='unknown'` (these are vendor attribution anchors, not device-pairable identifiers per §11 #13 ban) and are correctly DROPPED from Lynceus export at the §11 #13 device-category-unknown gate. They appear in `argus_export.csv` (full unfiltered corpus, now 34,792 records / 21 MB).

### Carry-forward queue (post-v1.4.0)

- payload.bin Android A/B OTA extraction tool for Wave I-prime access to inner-filesystem certs (only OTA-update certs recovered this cycle)
- GITHUB_TOKEN-authenticated rerun for higher rate posture on GitHub source mining
- Wayback CDX connectivity remediation
- `vendor_asn_prefix` + `vendor_controlled_ip` value-class observation (currently 0 empirical evidence; CP30/migration 0025 admission criteria)
- Manual top-50 GitHub-sourced calibration FP-rate anchor (Phase 2 §2.5)
- Honeywell International Inc. canonical-manufacturer admission decision (firmware-cert evidence in hand; operator ratification needed)
- CP30 source_type enum extension (5 candidate values: certificate_transparency_log, public_archive, vendor_first_party_source_code, public_package_registry, vendor_cloud_storage_payload)

### Schema migrations

- **0024**: identifier_type CHECK enum 51 → 54 (CP29 cluster) — table-rebuild pattern per 0009/0011/0013/0014/0018/0019/0023 precedent; 22,633 rows preserved via INSERT SELECT *; 6 indexes recreated; FK integrity preserved.

## [v1.3.0] — 2026-05-18

### What's new in v1.3.0

Argus v1.3.0 lands the **Wave H pre-v1 desktop-axis static-analysis integration** — the first release in which the vendor-companion-app extraction methodology generalizes from the Wave G Android mobile axis to Windows / macOS / Linux desktop application binaries. Three vendor desktop applications + one FP-control binary (519 MB acquired total) ran through a thin `wave_h_wrapper.py` adapter over the unmodified Wave G regex-extraction core (per the CP27 §3.0 P4 disposition — v4 untouched), with extraction outputs surfaced as a partial-cohort wave covering Cohort D (drone tooling: DJI Assistant 2 Mavic + DJI Assistant 2 FPV; Skydio P11 CLEAN NEGATIVE = documented_absence) + Cohort F (sanctioned-vendor v1: Hikvision iVMS-4200) + an H2-disambig FP-control (FileZilla 3.70.5).

The headline empirical finding is **Wave H's identifier-class surface differs from Wave G's** even within installer-cohort vendors that DO have desktop binaries. After the CP26 §8 semantic-validation audit pass, **net genuine `ble_service_uuid` candidates = 0** across all three real-vendor binaries. The 4 unique surviving UUID-shaped values all re-class as different identifier classes: 2× MSI ProductCodes (Hikvision iVMS-4200 main package + Multilingual Wizard sub-package), 1× COM CLSID (DJI Assistant 2 DJIBrowser LocalServer32), 1× cloud-document UUID (DJI Mavic + FPV cross-product attested in `https://duss.djicorp.com/functional-document/<UUID>`). These are vendor-controlled identifiers with empirical density worth promoting — they would be lost if the wrapper continued to filter them as "not genuine BLE UUIDs". CP28 codifies the three identifier-classes as first-class `identifier_type` enum values + migration 0023 extends the CHECK enum 48 → 51 to receive them.

The headline outcomes for downstream consumers: **22,553 active identifiers** (up from 22,549, +4 from Wave H promotion), **53 sources** (up from 52; +1 `manufacturer_app` Wave H Vendor Desktop Application Static Analysis admission), **51 manufacturers** (up from 49; +2 stub admissions per MAC-178 P5 precedent — Eagle Eye Networks + Rhombus Systems via Cohort A absence-investigation), and a schema bumped from version 22 to **version 23** via one forward-only migration (the new `identifier_type` CHECK enum extension for the CP28 Wave H non-BLE cluster).

### Wave H methodology — Vendor Desktop Application Static Analysis

Wave H extends the Wave G APK static-analysis methodology to publicly downloadable desktop vendor applications across Windows / macOS / Linux. The methodology probes vendor binaries for: BLE service UUIDs, default SSID patterns, MAC OUI validation patterns, product-family taxonomy, ONVIF capability strings, SNMP enterprise OIDs, mDNS service types, and network-protocol magic bytes. The wrapper applies 7 supplemental SAR-12 FP-class filters codified across sessions 1 + 2 to suppress 188 desktop-platform-wide false positives that the v4 core alone would have promoted:

| # | SAR-12 FP class | Scope |
|---|---|---|
| 1 | `WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS` | Microsoft application-manifest compatibility GUIDs (Vista / 7 / 8 / 8.1 / 10) — every Windows installer embeds. |
| 2 | `WINDOWS_COM_INTERFACE_GUIDS` | Microsoft Windows SDK COM IIDs (`IID_IShellLinkA` + bulk-seeded from `combase.h`, `shobjidl.h`, `objidl.h`, `oaidl.h`, `unknwn.h`). |
| 3 | `WINDOWS_DEVCLASS_SETUP_GUIDS` | SetupAPI device-class GUIDs (USB / Media / Modem / Net / HID / 1394 / Image / MTP / etc.). |
| 4 | `LIBUSB_ASCII_IDENTIFIERS` | UUID-shaped ASCII strings inside libusb-win32-WDF library binary. |
| 5 | `THIRD_PARTY_DLL_PATH_PREFIXES` | UUID-class candidates whose `source_file_relative` path leaf starts with 3rd-party library prefixes (Qt5*, libcrypto-*, libssl-*, libeay32, msvcp*, msvcr*, vcruntime, libusb0, libusb-1.0, d3dcompiler_*, libegl, libglesv2, sqlite3, icu*, iconv, libffi, libxml2, zlib). |
| 6 | `WINDOWS_SXS_PUBLICKEYTOKEN` | 16-char hex publicKeyTokens in `<assemblyIdentity>` XML manifests. |
| 7 | `windows_installer_productcode_in_msi_context` | MSI/InstallShield ProductCode GUIDs in Windows Installer registry contexts (8 context markers incl. `\{`, `\Uninstall\{`, `InstallShield Wizard`). Codified post-Hikvision-CP26-§8-audit. |

The wrapper canonical path is `android_test/tools/extraction/wave_h_wrapper.py` (sibling to `wave_g_extractor.py`); the Wave H runguide is `android_test/WAVE_H_RUNGUIDE.md` (sibling to `WAVE_G_RUNBOOK.md`). Wave H pre-v1 extraction outputs are staged at `extraction_outputs/wave_h_pre_v1/` (HANDOFF + per-vendor candidates/fp_findings + cohort-absence rows + calibration findings).

### CP17 desktop-axis thesis bifurcation finding (marquee policy output)

The original CP17 cohort thesis (Wave G mobile origin) predicted that the operator-vs-installer cohort split would generalize from mobile to desktop. Wave H sessions 1 + 2 empirically refine this finding in two distinct dimensions:

**Dimension 1 — cohort presence.** The operator-cohort desktop class has structurally dissolved into web/mobile across modern VMS + drone-tooling vendors. Session 1 confirmed this for VMS (5 of 6 Cohort A targets were web-only or UWP-MSIX, not Electron desktop — Cohort A descoped). Session 2 §3 confirms this for drone tooling (Skydio Pilot does not exist as a desktop application — Skydio's distribution is mobile + hardware-controller + cloud; documented_absence emitted). The installer-cohort desktop class persists (DJI Assistant 2 ships a desktop installer; Hikvision iVMS-4200 ships a desktop installer) but the operator-cohort class is empirically absent at the desktop axis in 2026.

**Dimension 2 — identifier-class surface.** This is the NEW Wave H finding the runguide did not predict. Even within installer-cohort desktop binaries that DO exist, the identifier-class surface differs from what Wave G mobile-axis extraction surfaced:

- **Wave G mobile binaries yield genuine BLE service UUIDs** because the mobile companion is the BLE peripheral pairing endpoint. The phone IS the BLE central; the vendor app contains BLE service/characteristic UUIDs in code.
- **Wave H desktop binaries yield MSI ProductCodes + COM CLSIDs + cloud-document UUIDs + vendor-cloud-endpoint hostnames** — not BLE protocol identifiers. The desktop client is for camera/drone management; the BLE pairing surface is in the camera/drone firmware (Cohort E) or in the mobile app (Wave G), not in the desktop client.

**Policy implication for Lynceus + Talos:** Wave H desktop findings should be consumed as a different identifier-class surface than Wave G mobile findings. A "BLE UUID + SSID" yield expectation that worked for Wave G mobile does NOT apply to Wave H desktop. Wave H desktop's value-add is in the **vendor cloud-endpoint discovery** layer (e.g., the `duss.djicorp.com` hostname surfaced from DJI Assistant 2 binaries), the **installer-time configuration surface** (MSI ProductCode + COM CLSID = vendor-controlled OS-integration identifiers), and **the absence-as-finding** (CP17 operator-cohort dissolution itself is a vendor-architectural-shift observation worth codifying). Future Wave I desktop-axis runguides should re-scope to vendor cloud-endpoint discovery + installer-config surface as headline metrics, not BLE UUIDs.

### Net new identifiers — the four CP28(c) Wave H promotions

The 4 vendor-attested non-BLE UUIDs that CP26 §8 audit re-classed promote at the §8.2 sub-band ladder per CP28(c):

- **DJI `f4d4dbf5-ba4b-40db-9a44-f8395f3728cf`** (`vendor_document_uuid_cloud_reference`) — cloud-document UUID embedded in DJI's `https://duss.djicorp.com/functional-document/f4d4dbf5-...` URL. Cross-product attested across DJI Assistant 2 Mavic 2.0.14 + DJI Assistant 2 FPV 2.1.2 (CP24 within-vendor-cross-product). Confidence 90 per the 80-95 sub-band ladder. §4.4 posture: **MAP** — the cloud-hostname half lifts into Lynceus's relevance window as a passively-scannable vendor cloud endpoint signature.

- **DJI `054aae20-4bea-4347-8a35-64a533254a9d`** (`windows_com_clsid_vendor_registered`) — Windows COM Class ID for the DJIBrowser LocalServer32, surfaced from `Software\Classes\CLSID\{054AAE20-...}\LocalServer32` registry context in DJI Assistant 2 Mavic 2.0.14. Confidence 85 per the 75-90 sub-band ladder. §4.4 posture: **DROPPED** — install/registry context only; low passive-scan utility.

- **Hikvision `9a25302d-30c0-39d9-bd6f-21e6ec160475`** (`windows_installer_productcode_vendor_registered`) — MSI ProductCode for iVMS-4200 v3.13.0.5_Multilingual main package, surfaced from `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{9A25302D-...}` registry context. Confidence 85 per the 75-90 sub-band ladder. §4.4 posture: **DROPPED**.

- **Hikvision `ce2f96d0-63d2-4b9c-a8d6-0d1a60840bd8`** (`windows_installer_productcode_vendor_registered`) — MSI ProductCode for iVMS-4200 Multilingual Wizard sub-package, surfaced from `\{CE2F96D0-...}` registry context. Confidence 85 per the 75-90 sub-band ladder. §4.4 posture: **DROPPED**.

All 4 promoted identifiers carry single-source-at-promotion provenance (no §8.3 lift triggers fire — Cohort D's only independent vendor 2 was Skydio, which is P11 CLEAN NEGATIVE / documented_absence; no cross-vendor independent-source overlap to test). Per §11 #8, confidence stays at the §8.2 sub-band's empirical anchor; no drift.

### Documented absences — Wave H Cohort A + Skydio Cohort D

Wave H session 1's Cohort A descope yielded **6 documented_absence rows** (Verkada Command, Genetec Citilog, Avigilon ACC Client, Axis Camera Station, Milestone XProtect, Honeywell Pro-Watch) anchored on the empirical observation that these vendors' "operator" client class has structurally dissolved into web/mobile distribution in 2026. Session 2 §3 added **1 Cohort D documented_absence row** (Skydio Pilot — P11 CLEAN NEGATIVE; Skydio's distribution is mobile + hardware-controller + cloud only; no desktop application). All 7 documented_absence rows are staged at `extraction_outputs/wave_h_pre_v1/per_vendor/_cohort_a_documented_absence.json` and `.../skydio_pilot_documented_absence.json`; they land in the appropriate canonical-state surface per current schema convention (the `documented_absence` first-class-table promotion remains held below the §3 #6 ≥30 cumulative-wave threshold per the CP27 surfacing).

### New data source

One source joined Argus in this release, bringing the source count from 52 to 53:

- **Vendor Desktop Application Static Analysis — Wave H** (sid=53, `source_type='manufacturer_app'`, tier 1) — the methodology covers publicly-downloadable vendor desktop applications across Windows / macOS / Linux. Admitted under the existing Wave G `manufacturer_app` enum per CP15 source-type ceiling (the proposed `vendor_application_static_analysis` enum value is CP28(a) DEFERRED per CEO disposition — the operational band-distinction is encoded via the §8.2 sub-band ladder + `notes.session_admission='wave_h_pre_v1'`). License posture: `per_vendor` + `upstream_license_posture='no_license_declared_facts_only'` defaults per CP21. Session 1 + 2 EULA disposition counts: category_a 0, category_b 0, category_c 3, category_d 0 (Hikvision iVMS-4200 download-agreement modal + DJI EULA + FileZilla GPLv2 all §3.6 (c) include).

### Bible amendment — Correction Pass 28 (CP28(c) identifier_type cluster + CP28(a)/(b) deferrals + SAR-12 7-FP-class codification + wrapper §-fragment)

The Wave H pre-v1 wave's three CP28 candidate flags ratified as **`Correction Pass 28`**:

- **CP28(c)** — three new `identifier_type` CHECK enum values: `windows_installer_productcode_vendor_registered`, `windows_com_clsid_vendor_registered`, `vendor_document_uuid_cloud_reference`. §8.2 sub-band ladder 75-90 / 75-90 / 80-95; §4.4 posture DROPPED / DROPPED / MAP respectively. Schema landed via migration 0023.
- **CP28(a)** `vendor_application_static_analysis` source_type enum — **DEFERRED** per CEO disposition; band-distinction encoded via §8.2 sub-band ladder + `notes.session_admission`. Re-fire candidate post-Wave-H-Continuation + Wave-I close.
- **CP28(b)** `sanctioned_vendor_public_distribution_facts_only` license-posture sentinel — **DEFERRED** per CEO disposition; empirical anchor weakened post-CP26 §8 audit. Re-fire candidate post-Cohort-F completion as CP-of-its-own (currently Dahua + Uniview acquisition blocked at Cloudflare).
- **Wrapper §-fragment** — ±90-char per-match windowed clipping discipline at the candidate-walk layer codified for next-runguide-template fold-in. Whole-line-with-overflow_dropped behavior deprecated for candidate-walk extraction.
- **SAR-12 7-FP-class roster codification** — the wrapper's final 7-class roster (listed above in the methodology section) is canonized for cross-wave consumption (source-of-truth remains the wrapper).

CP28 lands as the bible-amendment sibling of migration 0023 in the MAC-181 v1.3.0 release sweep cycle. CP-anchor: migration commit `2795ebba7866ad164121668321e213308aa87936` + [MAC-181](/MAC/issues/MAC-181) child issue ID. Bible HEAD bumps from the CP27 commit to the CP28 commit landed alongside this entry. Ratification surface: [MAC-177 disposition `comment-0d15de7b`](/MAC/issues/MAC-177#comment-0d15de7b-25a9-4f1e-bb40-65f00bc30fce) §7 "approve full path".

### Schema changes

One new migration landed this release (schema version 22 → 23):

- **0023 — `identifier_type` CHECK enum extension CP28.** Pure additive enum extension (48 → 51 values) using the SQLite table-rebuild pattern from 0009 / 0011 / 0013 / 0014 / 0018 / 0019. Cumulative-CHECK discipline carries forward all 48 prior values verbatim + adds the 3 net-new CP28(c) values. PRAGMA integrity_check + quick_check both ok at apply time; 22,549 active rows preserved via INSERT SELECT *.

### Tracked follow-ons (post-v1.3.0)

- **Cohort F post-CP28 re-fire** (Dahua + Uniview; option 2 per [MAC-177 disposition](/MAC/issues/MAC-177#comment-0d15de7b-25a9-4f1e-bb40-65f00bc30fce) §5) — queued as a separate child issue.
- **Wave I scope discussion** — hostname corpus → web SPA → iOS ranking ratified; separate child issue after v1.3.0 ships.
- **CP28(b) sentinel re-anchor** at Cohort F completion as CP-of-its-own.
- **CP28(a) re-fire** if Lynceus operationally requests filterable `vendor_application_static_analysis` source_type class post-Wave-I.

## [v1.2.0] — 2026-05-18

### What's new in v1.2.0

Argus v1.2.0 lands the cycle-7 autonomous-overnight-wave integration. The wave brought **two new authoritative data sources** for the US FCC equipment-authorization ecosystem (fccid.io as a community aggregator + the official FCC EAS Filings UI as a distinct primary-registry source), **671 FCC ID discovery rows** staged under a new dual-citation-pair convention (the citation half awaits a separate async re-citation pass when FCC.gov egress is restored), and **16 net-new identifiers** from a static-analysis pass against four LE-adjacency vendor companion apps (Hikvision Hik-Connect, Dahua DMSS, Motorola WAVE PTT, Parrot FreeFlight 6). We also admitted **fourteen new manufacturer rows** — four for vendors whose identifiers we positively extracted (Hikvision, Dahua, Autel Robotics, Cisco Meraki) and ten stub rows for vendors whose identity we confirmed via absence-investigation (Verkada, Honeywell, Lenel, BluePoint Alert, PIPS Technology, Wolfcom, Utility Inc, Coban Technologies, Digital Ally, Aerodome).

Alongside the data lands, the wave produced a **bible amendment codifying empirical-premise verification as a runguide precondition** — five separate web-scrape runguides (MAC-102 ISED, MAC-103 BT SIG, MAC-105 USPTO Patents, MAC-107 GitHub Code Search, MAC-110 Ofcom) plus one internal extraction pass (MAC-101 PC1.7's `application_id`-vs-`grant_id` discovery) all surfaced load-bearing-premise failures during the same 8-hour autonomous window. The amendment introduces a new `§2.4 Empirical-Premise Verification Precondition` requiring runguides to ship a `§3.0` verification-probe section that completes CLEAN before any `§3.1` bulk dispatch fires. **The amendment landed in a follow-on commit as `Correction Pass 27`** after CEO + operator ratification on the [MAC-178](/MAC/issues/MAC-178) issue thread.

The headline outcomes for downstream consumers: **22,549 active identifiers** (up from 22,533, +16 from MAC-104 wave-G v2 promotion), **52 sources** (up from 50; +1 crowdsourced fccid.io + 1 regulatory FCC EAS Filings), **49 manufacturers** in the canonical vendor lexicon (up from 35), **133,825 raw_observations** rows (up from 133,134), and a schema bumped from version 21 to **version 22** via one forward-only migration (the new `fcc_citation_deferred_queue` staging table for the dual-citation pair pattern).

### New data sources

Two sources joined Argus in this release, bringing the source count from 50 to 52:

- **fccid.io** (sid=51, `crowdsourced` tier 2) — a third-party aggregator of US FCC Equipment Authorization System filings. fccid.io mirrors the FCC's public filings catalog with a more navigable surface than the official `apps.fcc.gov` UI, but the upstream license is `NO_LICENSE_DECLARED` — Argus extracts facts under the Feist v. Rural Telephone facts-not-copyrightable doctrine, not via license inheritance. Compilation arrangement is not republished. This source feeds the new dual-citation-pair pattern (see below).

- **FCC Equipment Authorization System — Filings** (sid=52, `regulatory` tier 1) — the official FCC EAS Filings UI at `apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm`. Distinct from the existing FCC EAS grantee-registration data file (source 7); the Filings UI gives per-FCC-ID filing surfaces (test reports, internal photos, RF exposure data) that the grantee CSV doesn't expose. **The source was admitted under a degraded-mode posture**: at extraction time FCC.gov egress was unreachable from the runtime host (Akamai-edge HTTP/2 INTERNAL_ERROR across `apps.fcc.gov`), so the 671 fccid.io discovery rows were staged with their FCC citation half deferred to an asynchronous re-citation pass. The source exists; the citation rows accumulate when egress is restored.

### Dual-citation deferred queue (new staging convention)

The cycle-7 wave introduces a **dual-citation pair pattern** for sources where the discovery surface (an aggregator) is distinct from the primary surface (the regulator). Each FCC ID observed at fccid.io carries a `notes.dual_citation_pair_id` field pointing to a row in the new `fcc_citation_deferred_queue` table. The queue row holds the discovery anchor (`fccid_io_source_url` + SHA-256 of the served HTML) and an opportunistic enrichment field (`fcc_grant_ids[]` — 564 of 671 queue rows carry these, extracted from the fccid.io page's grant-bold-content block; this lets a future async re-citation pass shortcut FCC.gov navigation from 5-step lookup to 1-step). When FCC.gov egress is restored, the validator's async re-citation pass drains the queue and emits paired regulatory-band citation rows. Until then, the discovery rows stay at the `crowdsourced` 50-75 confidence band; no confidence drift on the discovery anchor alone.

### MAC-104 Wave-G v2 net-new identifiers

The wave ran a static-analysis extraction pass against four LE-adjacency vendor companion apps (downloaded from apk-pure; decompiled with jadx + apktool; structured field extractions only — no decompiled source ever enters the DB per §11 #15). Net-new identifier yield:

- **Hikvision Hik-Connect** (`com.hikvision.hikconnect`) — 1 BLE service UUID + 2 BLE characteristics, all anchored in the app's `HcpBluetoothServer` class. The Hik-Connect app is operator-cohort (cloud VMS / video doorbell), but the BLE pairing code path is installer-quality — vendor-named classes, paired `BluetoothGattService.equals(...)` / `getCharacteristic(...)` confirmations across multiple files.
- **Dahua DMSS** (`com.mm.android.DMSS`) — 1 BLE service UUID + 1 BLE characteristic, paired in obfuscated class `sources/en/f.java`. Dahua DMSS substituted for the legacy `com.mm.android.direct.gdmsphone` (gDMSS Plus) which is documented-absent on both apk-pure and apk-mirror.
- **Motorola WAVE PTT** (`com.motorolasolutions.wave`) — 2 BLE service UUIDs (one custom 128-bit, one 16-bit SIG-template) + 2 BLE characteristics, all anchored in `BluetoothLowEnergyPttValues` for the Milicom PTT Button accessory.
- **Parrot FreeFlight 6** (`com.parrot.freeflight6`) — 1 BT SIG company-ID (67 / 0x0043 = Parrot SA) + 4 ASD-STAN drone-RID enums (`FR_30_OCTETS`, `ANSI_CTA_2063`, `FRENCH`, `EN4709_002`) + 1 ARSDK DRI feature class ID (41984 / 0xA400) + 1 ARSDK DRI command UID set. All anchored in `com/parrot/drone/sdkcore/arsdk/ArsdkFeatureDri.java` — clear-text Java, 262 lines; Parrot is the canonical drone vendor for which the entire ARSDK protocol + Drone-RID code path surfaces under Java decompilation.

All 16 promoted identifiers carry `confidence ∈ {75, 85, 87}` per CP17 manufacturer_app sub-banding (installer-cohort 80-95 → 87; CP14 drone-RID class hits → 85; 16-bit SIG-template lower anchor → 75). All single-source at promotion (`notes.single_source_at_promotion=true`); no §5.6 cross-source uplift applied (verified: no pre-existing rows match any candidate identifier).

**Four additional candidates held for SAR-12 schema-extension review:**
- 2 default credentials (`lc2014` LeChange SDK default password, `terminal` DMSS OAuth client_secret) — no `default_credential` enum slot at v22 schema
- 1 vendor namespace UUID (Parrot Skyward UTM `0045b822-...`) — handoff explicitly flags as NOT-a-BLE-service-UUID; no clean enum fit
- 1 DJI RTK serial-number template (`1APDF7Q0010001` from DJI Pilot NRTK setup default) — handoff explicitly not-promoted-flagged; no `serial_number_template` enum slot

Each held row stages in `raw_observations` with `notes.hold_reason` + `notes.validator_review_recommendation`.

### Manufacturer enrichments

Fourteen new manufacturer rows joined the canonical lexicon (from 35 to 49):

- **Hikvision** (id=209) and **Dahua** (id=208) — both admitted with NDAA Section 889 note (state/local LE deployments persist outside the federal-procurement bar; runguide §0 scope).
- **Autel Robotics** (id=206, primary_category=drone) and **Cisco Meraki** (id=207) — positive-extraction admissions from MAC-104b/d.
- **Stub admissions** (10 vendors, primary_category set where the vendor's product line is unambiguous): Verkada, Honeywell, Lenel, BluePoint Alert, PIPS Technology, Wolfcom, Utility Inc, Coban Technologies, Digital Ally, Aerodome. Each carries `notes.admission_basis='documented_absence_only'` — the manufacturer identity was verified via absence-investigation (apk-pure 404 + apk-mirror "no results" + cohort-prediction reasoning) but no positive identifier extraction this wave.

**34 product-family taxonomy entries** added to seven manufacturers' `notes.product_family_taxonomy[]` arrays (additive; cross-APK observations of the same string are corroborating mentions and get separate entries — e.g. DJI "Mavic" appears once for DJI Fly + once for DJI Pilot = 2 entries, 1 distinct value). Distinct values: DJI (10), Hikvision (5), Motorola Solutions (4), Dahua (4), Parrot (3), Autel Robotics (2), Cisco Meraki (1).

**22 `documented_absence` JSON entries** applied to `manufacturers.notes.documented_absence[]` across 21 distinct vendor rows (DJI gets two entries: legacy `com.dji.go` + standalone `com.dji.mavicmini` folded into DJI Fly). Each entry carries `investigation_date_utc`, `investigation_dispatch_ref`, `channels_probed`, `outcome=categorical_absent`, `rationale` (one of `LE_only_distribution` / `federal_enterprise_managed` / `vendor_direct_NDA` / `controlled_distribution`), and the staging vendor_canonical for alias-trace continuity. Distribution: LE-only-distribution 9, federal-enterprise-managed 9, vendor-direct-NDA 3, controlled-distribution 1 (DroneShield RfPatrol — C-UAS / ITAR-adjacent; flagged for operator legal review before alt-channel pursuit).

### SAR-11 FP-class registry additions

Nineteen new SAR-11 FP-class proposals were baked into the canonical `proposed_fp_classes.json` registry per CEO §3 #5 ratification: **14 clean bulk-adds** (Docker/Jenkins build-host UUIDs, APK test fixtures, Motorola WAVE license GUID, Microsoft AppCenter / PDFBox / RN-Keychain library labels, NASA WorldWind constants, Autel password regex templates, Apache HttpClient context keys, RxJava build-host UUIDs, AndroidAnnotations cacerts default, XML layout TextView labels, Adobe XMP image metadata UUIDs) + **5 selective adds with `operator_review_note: "Hikvision/Dahua/drone-cohort overlap; flagged at MAC-104 cycle-7"`** (Alibaba Taobao security cipher key, Microsoft XML namespace UUID, Hikvision HTML doc-routing GUID, AMap location-SDK placeholder MACs, DJI api_debug.txt key). Each edge entry carries explicit `overlap_risk` prose so v3 extractor calibration applies exact-value-match-only, not generalization.

### Bible amendment — Correction Pass 27 (`§2.4` Empirical-Premise Verification Precondition)

The wave's six concrete failure-mode anchors (5 external runguides + 1 internal extraction pass) ratified as **`Correction Pass 27` — `§2.4 Empirical-Premise Verification Precondition`**: a new bible subsection requiring every runguide to ship a `§3.0` verification-probe section that completes CLEAN POSITIVE or CLEAN NEGATIVE before any `§3.1` bulk dispatch fires. INCONCLUSIVE outcomes halt the runguide; CEO disposition is required for any re-fire. The amendment also defines retroactive binding rules for runguides drafted-but-not-dispatched and runguides being re-dispatched.

CP27 landed as a single follow-on commit covering the `BIBLE_AMENDMENTS.md` CP27 entry, the `§2.4` insert into `PROJECT_BIBLE.md` (placed after `§2.3 A Note on Ambition`; before `§3 Architecture`), and this CHANGELOG flip. Schema version unchanged (CP27 is `§`-text only — no migration, no notes_json convention, no code-path sibling). Downstream-consumer audit: 10 runguides identified for retroactive `§3.0` adoption (8 "Must" cases enforced naturally at each runguide's next dispatch-firing gate per `§2.4`'s halt-before-fire contract; 2 "Should" cases fire lazily next time the completed runguides are touched). No separate tracking issue created — the discipline is structurally self-enforcing. Ratification surface: [MAC-178 disposition](/MAC/issues/MAC-178#comment-3029e567-c4e7-4dac-aff8-cd03b8c9a48a) (response to Validator draft [60301e62](/MAC/issues/MAC-178#comment-60301e62-da2e-4007-b975-b40caaf2c923)).

### Schema changes

One new migration landed this release (schema version 21 → 22):

- **0022 — `fcc_citation_deferred_queue` staging table.** New table holds the discovery-row half of the dual-citation pair pattern (one row per FCC ID; `fcc_id` UNIQUE; `promoted_at NULL` = pending drain by the validator's async re-citation pass; index on `(promoted_at)` partial WHERE NULL for drain queries; index on `fcc_grant_ids_csv` for grant-ID-shortcut lookup). 671 rows seeded from the MAC-101 partial-deliverable wave.

### Conventions

- **Staging-JSON-vs-schema-column naming convention codified** (2026-05-17, patch cycle 1.6.C): staging JSON shapes emitted under `extraction_outputs/{runguide_slug}/` use `candidate_value` for human readability during validator review; the promoted `raw_observations` schema column is `candidate_identifier`. Validator handles the rename at promotion (one-to-one, no transformation). Documented in patch cycle 1 against the source-admission wave (10 runguides, MAC-101 through MAC-110). The patch cycle 2 wave (PC2.A through PC2.D) did not surface rename-at-promotion error pressure; the convention holds as written.

### Refreshed exports

All four canonical exports were regenerated against the post-cycle-7 active set:

| Export | Pre-cycle-7 | Post-cycle-7 | Delta |
|---|---|---|---|
| `argus_export.csv` (rich-import, all canonical rows) | 22,533 | **22,549** | +16 |
| `argus_export.json` (Lynceus, ≥30 confidence + §4.4 mapping) | 494 | 494 | +0 |
| `argus_export_high_confidence.json` (Lynceus, ≥70 + non-{crowdsourced, inferred}) | 113 | 113 | +0 |
| `argus_export_behavioral_signatures.json` (Rayhunter; unchanged this wave) | 55 | 55 | unchanged |

**Note on the JSON-export +0 delta:** the 16 MAC-104-promoted identifier_types (`ble_service_uuid`, `ble_characteristic`, `ble_company_id`, `asdstan_enum_value`, `device_class_id`, `rf_protocol_constant`) are all `§4.4 DROPPED-class` per CP16 / CP19 (mig-0018 cluster) / MAC-117 (mig-0019 round-2). Per the bible, DROPPED-class identifier_types are carried in the canonical DB (and the CSV rich-import feed) but NOT in the Lynceus pattern-table JSON exports — by design. The brief author's forecast of +20 standard-export rows + +6 to +14 high-confidence rows didn't account for this disposition. Whether to MAP some/all of these types into Lynceus is a separate `§4.4` amendment surface for a future CP cycle.

Also new: `exports/_export_manifest.json` ships the per-file size + SHA-256 + entry-count manifest with a delta-vs-forecast block, generation timestamp, and the §4.4 reasoning surfaced for downstream consumers.

### Post-CP27 runguide migrations (Patch Cycle 2)

Following the CP27 ratification, four web-scrape runguides identified at the CP27 §2.4 audit were migrated through Patch Cycle 2 (PC2.A through PC2.D) as in-repo summary commits accompanying out-of-tree runguide-file edits. All four are docs/runguide-internal only — no sources, identifiers, manufacturers, raw_observations, schema, or license posture changed. Each landed a `§3.0` empirical-premise verification block (CP27 §2.4 compliance) alongside the upstream-surface migration:

- **PC2.A — MAC-105 USPTO Patent Public Search migration** (`348f514`) — legacy `patft.uspto.gov` decommissioned; runguide migrated to `ppubs.uspto.gov/pubwebapp/` + the authenticated `data.uspto.gov/api/manage` ODP endpoint (`USPTO_ODP_API_KEY` env-var convention). 4-probe `§3.0` verification block (Google Patents + PPubs JS-shell + USPTO ODP authenticated + Espacenet rate-block detection).
- **PC2.B — MAC-107 GitHub Code Search auth-required correction** (`fa967b1`) — runguide corrected to reflect mandatory authentication for all `/search/*` queries since GitHub's 2022 GA change; rate limit clarified as 30 req/min on `/search/*`; 4-row SQL column-drift fix (`identifier_value → identifier`, `manufacturer_canonical_name → manufacturer`); 4-probe `§3.0` verification block with PAT scope sanity + account-identity capture for §11 #3 audit-log provenance.
- **PC2.C — MAC-102 ISED REL Spring Web Flow migration** (`164ceb2`) — legacy `apc-cap.ic.gc.ca` Oracle PL/SQL endpoint decommissioned; runguide migrated to `sms-sgs.ic.gc.ca/equipmentSearch/searchRadioEquipments` Spring Web Flow surface; per-row + bulk-data URL templates deferred to v2 runguide (continuation-token discovery + POST-flow advance not yet captured); 4-probe `§3.0` verification block. OGL-Canada-2.0 license posture unchanged.
- **PC2.D — MAC-103 BT SIG Qualified Designs narrow-to-shallow** (`d66f986`) — runguide narrowed from full-Wave-G companion-app linkage to shallow-surface QDID capture (`QDID + product_name + owner_company + reference_QDID`); cross-source linkage to `ble_manufacturer_id` preserved; Cloudflare WAF UA-shape rejection documented (browser-shape UA required; `argus-research/*` UA rejected); public POST search at `qualificationapi.bluetooth.com/api/Platform/Listings/Search`; SIG member gate noted for deeper surfaces.

The four-instance pattern (PC2.A through PC2.D, covering decommission / host-migration / auth-gating / Cloudflare-WAF failure modes) is documented at `extraction_outputs/_patch_cycle_2/pc2_d_summary.md` as empirical evidence supporting CP27 §2.4's halt-before-fire contract.

## [v1.1.0] — 2026-05-17

### What's new in v1.1.0

Argus v1.1.0 broadens the project beyond pure equipment-identifier registries and into the corporate, judicial, and procurement records that anchor surveillance vendors to real-world entities. We added **seven new authoritative data sources** (taking the project from 43 sources to 50), **expanded our federal procurement coverage** by 2,560 net-new contract records, and **closed our first held entity** — Johnson Matthey PLC — by cross-checking it against the UK's official corporate registry.

Along the way we found and fixed seven small inconsistencies between our documentation and the actual database schema. These are codified in the amendment ledger so the next round of contributors doesn't trip over the same edges. We also introduced two new operating conventions: an explicit `access_mode` tag for sources we can't auto-scrape in one session (CAPTCHA-walled state corporate registries, paid-tier government databases), and a `cycle_completion_state` tag for sources that take multiple days to fully ingest. Both are described in plain language below.

The headline outcomes for downstream consumers: **22,533 active identifiers** (up from 22,532), **46,043 procurement records** (up from 43,483), **35 manufacturers** in the canonical vendor lexicon (Johnson Matthey is new), and a schema bumped from version 19 to **version 21** via two forward-only migrations.

### New data sources

Seven sources joined Argus in this release, bringing the source count from 43 to 50:

- **UK Companies House** (sid=44) — the United Kingdom's official corporate registry, released under the Open Government Licence v3.0. We use it to confirm the corporate identity of UK-incorporated surveillance vendors against a primary government record. **This source enabled our first Class B hold closure: Johnson Matthey PLC (UK company #00033774), a London-headquartered chemistry and precious-metals firm**, was confirmed via Companies House cross-check and admitted to the canonical 35-entry manufacturer lexicon. Access is fully automated via the Companies House API.

- **Delaware Division of Corporations** (sid=45) — Delaware is the registration state of record for a disproportionate share of US technology companies, so the Delaware corporate registry is a high-leverage source for vendor verification. The state's NameSearch web form is CAPTCHA-gated, so this source is recorded under the new `operator_manual_only` access convention: lookups happen via human-operated browser sessions rather than scripts.

- **California Secretary of State — Bizfile** (sid=46) — California's corporate registry, the second-most-relevant US state for surveillance vendor lookups after Delaware. The Bizfile portal is gated by an Incapsula bot-challenge wall, so this is also an `operator_manual_only` source.

- **Texas Secretary of State SOSDirect** (sid=47) — the Texas corporate registry. Useful for Texas-headquartered surveillance vendors. Access requires paid-tier authentication, so this is again `operator_manual_only`.

- **CourtListener / RECAP (Free Law Project)** (sid=48) — a free, comprehensive judicial filings database covering US federal and state courts. CourtListener surfaces lawsuits, contract disputes, and federal court records that name surveillance vendors as parties. Metadata is dedicated to the public domain under CC0; full-text search requires an authenticated Bearer token.

- **SEC EDGAR** (sid=49) — the US Securities and Exchange Commission's corporate-disclosure filings database. Public companies routinely name their major customers in 10-K annual reports and Item 1A risk-factor narratives; for surveillance vendors that file with the SEC, this lets us corroborate vendor-customer relationships against a primary public-domain regulatory source. EDGAR is automated via HTML parsing.

- **SAM.gov Entity Registration** (sid=50) — the US federal procurement contractor-registration database. SAM.gov is the authoritative source for "is this vendor an active US federal contractor and what are their registered NAICS codes?" — exactly the question that determines whether procurement evidence is admissible. Access is automated via the SAM.gov API. This source is recorded under the new `partial_pre_day1` cycle-completion convention because we hit the SAM.gov non-Federal-individual-account daily rate ceiling (~10 requests/day) before the first full sweep finished. Remaining queries continue across subsequent days; the source row was admitted at first-batch completion.

### Expanded federal procurement coverage

Federal procurement records grew by **2,560 net-new entries** (from 43,483 to 46,043) via a deep-extension pass against USAspending.gov, the canonical federal contract-award database. This nearly closes the previously-known gap between Argus's surveillance-vendor coverage and USAspending's actual surface area for those vendors.

Alongside the new rows, we landed **9,623 cross-source corroborations** from the SAM.gov ingestion cycle. **A corroboration here means: a fact we already had (a vendor's federal contract record) is now independently confirmed against a second, structurally different source (SAM.gov's contractor registration database).** When two independent sources agree on a fact, our confidence in that fact increases, and the corroboration is recorded in a per-row audit trail so downstream consumers can see the evidence chain.

Note for downstream consumers: alongside the +2,560 net-new procurement records, we **rolled 180 procurement_record confidence values back from 90 to 85**. These rows had been corroborated by a second pass against USAspending itself — but that's the same source observed twice, not two independent sources, so the confidence boost wasn't earned. The full audit trail is preserved per row in `notes.confidence_history[]`. This is exactly the kind of self-correction the audit trail is designed to surface.

### Schema changes

Two new migrations landed this release (schema version 19 → 21):

- **Migration 0020 (`source_type_enum_extension`)** — extends the `sources.source_type` enum with three new values (`judicial_filing`, `disclosure_filing`, `procurement_disclosure`) to properly classify the new judicial, SEC, and SAM.gov sources. Previously these would have fallen back silently to the generic `regulatory` bucket; now each source class has its own named tier.

- **Migration 0021 (`procurement_vendor_canonical_normalized`)** — adds a new `procurement_records.vendor_canonical_normalized` column. This is a deterministic, query-friendly normalization of each procurement record's vendor name: lowercased, punctuation stripped, corporate suffixes (`INC`, `CORP`, `LLC`, `LTD`, `PLC`) removed. For example, `'AXON ENTERPRISE, INC.'`, `'Axon Enterprise, Inc.'`, and `'AXON ENT INC'` now all collapse to `axon enterprise`, making cross-validation joins against the manufacturer lexicon dramatically more reliable. The column was backfilled across all 46,043 procurement records.

**What this means for downstream consumers:** check `MAX(version) FROM schema_version` at runtime; it should now read 21. If you query the `sources` table by `source_type`, you may now see three additional enum values. If you join against `procurement_records.vendor_canonical_name`, prefer the new `vendor_canonical_normalized` column instead — same data, dramatically better join semantics across 46k rows.

### New discipline conventions

Two new operating conventions were introduced. Both live in the `sources.notes` JSON field today and are described below in user terms; they may be promoted to first-class schema columns in a future release once the vocabulary stabilizes.

- **`access_mode`** — describes how Argus fetches a given source. Values: `automated_api` (queried via documented API), `automated_html_parse` (scraped from HTML without an anti-bot wall), `automated_with_auth` (automated but requires a token), `mixed_automated_manual` (some candidates automated, some manual), and `operator_manual_only` (all access is via a human-operated browser session, because the source is CAPTCHA-walled, bot-challenged, or otherwise structurally hostile to automation). **Important: the access mode is a mechanism descriptor, not a quality signal.** Operator-manual sources carry identical confidence bands and provenance discipline to automated sources. The four state-registry sources added this release (DE / CA / TX) and three secondary state holds are flagged `operator_manual_only`.

- **`cycle_completion_state`** — describes whether a source's data has been fully ingested or whether ingestion is paced across multiple days. Values: absent (source is complete; default reading), `partial_pre_day1` (admission landed before the first sweep finished), `partial_pacing_in_flight` (multi-day pacing run still active), `partial_pacing_exhausted` (multi-day pacing terminated short of completion). When this field is set, the source row also carries `next_cycle_dispatch_scheduled_for_utc`, `next_cycle_dispatch_runguide_path`, and `partial_yield_metrics_at_admission` so downstream consumers can see exactly where the partial state sits and when the next cycle is scheduled. **SAM.gov (sid=50) is the first consumer**, recorded as `partial_pre_day1`.

### Known limitations + what's coming

Argus's coverage is still **intentionally narrow at this baseline** — broader categories of surveillance equipment remain out of scope. The roadmap below frames what's queued.

**Currently held items:**

- **11 US state Secretary-of-State corporate holds** remain queued for operator-manual review against the DE / CA / TX registries.
- **Approximately 22 international corporate holds** remain queued. Bounded paths to closure are documented per jurisdiction.
- **3 operator-review items** surfaced from the SAM.gov ingestion cycle: a Vigilant Solutions inactive-registration probe, a Flock Safety brittle-alias normalization disagreement (Flock Safety vs "Funny Flock Farms LLC"), and a Motorola multi-entity disambiguation probe. All three are staged to the operator-review queue with full audit context.

**Carry-forward from v1.0.0:** the previously-documented v1.0.0 held items (31 behavioral_signatures pending second-source corroboration, 62 Class B sustained holds, 133 IEEE Private permanent holds, 142 round-2 vocabulary candidates) remain held under the same rationale, less the one Johnson Matthey closure this release. The v1.0.0 documented sources-row metadata discrepancy on sources 1/2/3/7 is unchanged.

**Note: a small number of `identifiers.notes` rows contain malformed JSON; downstream consumers using `json_extract()` against this column should fall back to JSON-text-LIKE patterns. Tracked for future fix.**

**Coming next:**

- Continued multi-day SAM.gov ingestion (cycle-6 dispatch scheduled).
- Continued operator-manual review against state corporate registries to close the 11 remaining US state holds and ~22 international holds.
- Additional community-source-acquisition waves, deferred from v1.0.0.
- iOS vendor companion-app coverage, deferred from v1.0.0.
- Skydio Enterprise alt-channel scope, deferred from v1.0.0.

### Internal architecture notes

This section preserves the discipline-architecture audit trail for the v1.1.0 release in the project's canonical idiom. The narrative is the body above; the ledger below is the binding contract.

**Bible amendment ledger (this release):**

- **CP23** @ bible HEAD ratification — coordinated amendment: wide-net cycle-{1,3,4} schema-contract patches + migrations 0020 + 0021 + downstream-consumer audit. Folds seven schema-contract drift findings (PROJECT_BIBLE.md §4.2 / §4.3 / §8.2 / §8.3 §-text additions; `manufacturers.aliases` comma-string clarification; source_excerpt per-table CHECK constraint cap table; `notes.access_mode` notes_json convention; license-into-notes folding contract; cross-validation column-name normalizations) and the two migrations into a single bible commit per the §11 #11 amendment-log discipline. Source patches: `new data 5.16/schema_contract_patch_cycle3.md`, `new data 5.16/schema_contract_patch_cycle4.md`, `new data 5.16/schema_contract_patch_notes_license.md`.
- **CP24** @ bible HEAD — §11 #8 within-source-re-extraction sub-rule + CP19 spirit-extension to `procurement_records` row-level audit-trail (`notes.confidence_history[]` convention) + "§5.2 +5 boost" citation hygiene correction. Within-source re-extraction (same upstream registry queried at two times by the same or different extraction sessions) is **not** a "second independent source" for §8.3 lift purposes. Provenance enrichment via `notes.corroborations[]` + `notes.corroboration_sessions[]` stays; confidence does not lift. The 180-row MAC-172 P4 USAspending deep-extension lift rollback (85 → 90 → 85) is the first consumer with full per-row audit-trail.
- **CP25** @ bible HEAD `2803ae1` — `cross_source_corroboration_reversals[]` audit-trail convention + CP24 §12 `n` recount supersession (SEC EDGAR × USAspending drops 2 → 0 after §11 #1 semantic review of MAC-171 P3 RG5 findings) + within-source-FP discipline-evolution carry-forward. First consumer is the MAC-171 id=86738 reversal UPDATE.
- **CP26** @ bible HEAD `64f381c` — SAM.gov cycle-5 day-0 partial fold (seven runguide-correction findings: probe-template UEI freshness, empirical rate ceiling, no-proactive-rate-limit-headers extraction discipline, operator-manual-queue file-format clarification, NAICS code revision drift, single-token alias fanout brittleness, snapshot-freshness pre-flight) + `cycle_completion_state` notes_json convention codification + within-source-FP discipline n=4 codification (text-pattern match + semantic-relationship validation as a default §4 match-scoring step). Source patch: `extraction_outputs/sam_gov_admission/STOP_THE_LINE_rate_ceiling.md`.

**Migration ledger entries (cumulative 1 → 21):**

- **0020 `source_type_enum_extension`** (applied 2026-05-17 05:07:17) — `sources.source_type` CHECK enum 10 → 13 values: net-new `judicial_filing`, `disclosure_filing`, `procurement_disclosure`. Per CP23 / cycle-3 §1 finding #2. Table-rebuild per the 0009 / 0015 / 0018 / 0019 precedent. The 3 new bands are sources-tier taxonomy only; identifier-row promotion-pipeline confidence bands (§8.2) are unchanged.
- **0021 `procurement_vendor_canonical_normalized`** (applied 2026-05-17 05:07:32) — `procurement_records.vendor_canonical_normalized TEXT NOT NULL DEFAULT ''` column + supporting B-tree index. Per CP23 / cycle-3 §1 finding #4 + CEO Path B ruling. Backfill populated all 46,043 rows; collapse ratio 0.9862 (1,157 distinct raw vendor_canonical_name values collapse to 1,141 distinct normalized values). Normalization algorithm canonical reference: `db/normalize_vendor.py::normalize_vendor_name` (pure function).

**MAC issue dispatch references:**

- **MAC-101** — baseline aggregate state (v1.0.0 reference).
- **MAC-168** — paperclip integration of CP23 (wide-net cycle-{1,3,4} schema-contract patches).
- **MAC-169 through MAC-174** — admission cycle dispatches (UK Companies House P2; SEC EDGAR P3; USAspending deep-extension P4; state SoS P5; CourtListener V4 P6).
- **MAC-172** — USAspending deep-extension P4 ingest (+2,560 net-new procurement_records; partial-ratify rollback of the 180-row lift; CP24 codification).
- **MAC-175** — SAM.gov cycle-5 admission close (sid=50 INSERT + 9,623-row cross-source corroboration UPDATE batch: Vigilant 56 + Motorola 9,545 + Genetec 22; CP26 codification).

**Source-tier license-posture vocabulary additions (CP23):**

- `OGL-3.0` — UK Companies House (sid=44).
- `PUBLIC_DOMAIN` — SEC EDGAR (sid=49), SAM.gov (sid=50).
- `US_STATE_PUBLIC_RECORDS` — Delaware / California / Texas SoS (sid=45 / 46 / 47).
- `CC0` — CourtListener / Free Law Project (sid=48).

All four compose with the pre-existing CP21 `notes.upstream_license_posture` canonical sentinel-key for per-row license-aware downstream consumer filtering. License lives inside `notes_json.license` (the contract refers to this as `notes_json`; the underlying column is `sources.notes` TEXT containing JSON), NOT as a top-level column — codified per the cycle-1 patch finding #1.

**Live-state verification (paste-not-cite per S.7):**

Verified 2026-05-17 against `db/argus.db`:

```
schema_version              = 21   (0021_procurement_vendor_canonical_normalized,  2026-05-17 05:07:32)
                                   (0020_source_type_enum_extension,               2026-05-17 05:07:17)
sources                     = 50   (was 43 in v1.0.0; +7 this release)
identifiers active          = 22,533  (superseded_by IS NULL; total rows 22,613 incl. 80 superseded)
procurement_records         = 46,043  (+2,560 net-new this release)
manufacturers               = 35   (+1: Johnson Matthey PLC, UK CH #00033774)
behavioral_signatures       = 131  (unchanged)
source_reclassifications    = 809  (unchanged this MAC-175 close)
PRAGMA integrity_check      = ok
```

**Cross-source corroboration accounting (this release):**

- **9,623 cross-source corroboration UPDATEs** landed from the SAM.gov cycle-5 admission (Vigilant 56 + Motorola 9,545 + Genetec 22). All UPDATEs honor CP24 sub-rule (b)'s `notes.confidence_history[]` per-row audit-trail.
- **180 within-source-reextraction rollbacks** (90 → 85) applied per CP24 §11 #8 sub-rule #1 (the USAspending deep-extension is the same source observed at two times, not a genuinely independent collector). Full per-row audit per CP24 sub-rule (b).
- **2 RG5 cross-corroboration markers** flagged at MAC-172 P4 ingest; 1 reversed at MAC-171 P3 ratification per CP25 §1 (id=86738; SEC × USAspending pair recount drops 2 → 0). The remaining marker is deferred to operator review pending fuller filing context.

**Open §12 questions surfaced this release (queued for future CP candidacy):**

- `access_mode` first-class column migration — gated on value-set stabilization (~1-2 more cycles of new-source evidence).
- Partial-cycle source-admission discipline first-class-column promotion (`cycle_completion_state`) — gated on at least 2 distinct sources using non-absent values.
- Empirical-ceiling-probe runguide template — CP26 §3 candidate.
- `procurement_reclassifications` audit table promotion — gated on forensic-query pattern emergence at scale (current row-local `notes.confidence_history[]` convention is canonical).

---
## [v1.0.0] — TBD release date

### What's included

Argus v1.0.0 ships the canonical surveillance-equipment-identifier database as a queryable SQLite artifact (`db/argus.db`, schema_version=19) plus four derived dataset exports under three licenses:

- **Pipeline** (AGPL-3.0-or-later) — the migration + source-loader + extraction + validator + export code that reproduces the database from upstream sources.
- **Database / dataset** (ODbL-1.0; Atlas-derived rows quarantined under CC-BY-NC-SA-4.0 per upstream NC clause; per-row LICENSE column at `deployment_observations.LICENSE` enables downstream license-aware filtering) — the canonical SQLite DB + the JSON/CSV exports at `exports/`.
- **Documentation** (CC-BY-SA-4.0) — README, METHODOLOGY, DATA_DICTIONARY, CREDITS, SECURITY, THREAT_MODEL, LEGAL_POSTURE, CONTRIBUTING, CODE_OF_CONDUCT, this CHANGELOG.

#### Database content

- **14 user tables** at schema_version=19 (full schema reference in [DATA_DICTIONARY.md](DATA_DICTIONARY.md)):
  - **Canonical-state**: `identifiers` (Layer 1 — the main table; 22,532 active rows + 80 superseded)
  - **Provenance + source**: `raw_observations` (133,134 rows), `sources` (43 sources), `manufacturers` (34-entry surveillance-tech vendor lexicon)
  - **Layer 2 + supporting**: `deployment_observations` (116,668 rows with per-row LICENSE column per migration 0016), `procurement_records` (43,483 rows), `fcc_grantees` (50,153 rows), `council_minutes_matters` (3 rows), `wigle_anchor_priority` (80,697 rows), `behavioral_signatures` (131 rows)
  - **Audit-trail**: `source_reclassifications` (809 rows — row-level reclassification audit table)
  - **Operational**: `conflicts` (20 rows), `extraction_runs` (106 rows), `schema_version` (migration ledger 1 → 19)
- **Active identifier rows by class** (22,532 total active):
  - **IEEE-anchored mac_range / OUI** rows at `primary_registry` band: ~17,800 rows across IEEE OUI MA-L / MA-M / MA-S + IEEE IAB registries
  - **FAA Remote ID `drone_id_prefix`** rows at `primary_registry` band: 427 rows (from alphafox02/DragonSync + post-validation promotion cycle)
  - **Bluetooth SIG `ble_manufacturer_id`** rows at `primary_registry` band (per migration 0011): 3,971 rows
  - **Community-research crowdsourced** rows: ~534 rows across drone Remote ID + BLE tracker catalogs + IMSI-catcher detection + ALPR-camera profiles
  - **Vendor companion-app `manufacturer_app`** rows (Hak5 / Flock Safety FS Installer / Getac BWC Viewer via vendor-app static analysis): 21 rows
  - **Inferred / cross-validation** rows: 4 rows (vendor-disambiguation + corroboration math)
- **Provenance rows** (`raw_observations`): 133,134 rows; every active identifier traceable to at least one source citation per METHODOLOGY §7 provenance discipline.
- **Deployment-location rows** (`deployment_observations`): 116,668 rows from EFF Atlas of Surveillance (15,071 CC-BY-NC-SA-4.0) + DeFlock (101,597 ODbL-1.0) with per-row LICENSE column quarantine.
- **Behavioral signatures** (`behavioral_signatures`): 131 rows (55 Marlin NDSS 2025 IMSI-catcher signatures + 38 backfilled from community IMSI-detector research + 38 round-2 review extensions).

#### Source families integrated

- **IEEE OUI registries** (MA-L 24-bit + MA-M 28-bit + MA-S 36-bit) at `primary_registry` band — vendor-to-OUI mappings; factual public registry data.
- **IEEE IAB registry** (36-bit legacy) at `primary_registry` band — predecessor allocations.
- **FCC EAS Equipment Authorization Grantee Registrations** at `primary_registry` band — 50,153-grantee corporate registrant lookup table; allowlist for `fcc_id_anchored` disambiguation and the vendor-disambiguation predicate.
- **FAA ANSI/CTA-2063-A Remote ID prefix registry** at `primary_registry` band — drone-class identifier-to-vendor attribution.
- **Bluetooth SIG company-identifier registry** at `primary_registry` band — BLE `ble_manufacturer_id` clusters.
- **EFF Atlas of Surveillance** (CC-BY-NC-SA-4.0 quarantine; NC clause carries forward) — 15,071 deployment-location observations.
- **DeFlock** (ODbL-1.0; license-compatible with compilation license) — 101,597 ALPR camera deployment-location observations.
- **USAspending.gov + Granicus Legistar** — federal/state/municipal procurement records (43,483 + 3 rows respectively).
- **Wireshark `manuf` file** — community-maintained OUI cross-reference for vendor-name curation.
- **NDSS 2025 Marlin IMSI-catcher research** at `academic` band — 53 behavioral-signature rows for cellular-detection signatures.
- **Vendor companion applications** (Hak5 docs / Flock Safety FS Installer / Getac BWC Viewer) at `manufacturer_app` band — BLE service UUIDs + default credentials + product-family taxonomy extracted via static analysis under the 17 USC §1201(j) + 37 CFR §201.40(b) security-research exemption.
- **22 canonical community-research GitHub repositories** at `crowdsourced` or `manufacturer_doc` band — drone Remote ID + BLE tracker catalogs + IMSI-catcher detection + ALPR-camera + flock-detection cohorts.
- **5 secondary-batch repositories** at `crowdsourced` or `academic` band with explicit license-posture annotations (AGPL-3.0 inherited / AGPL-3.0 declared / NO_LICENSE_DECLARED under the Feist facts-only doctrine / CC-BY-NC-ND-4.0 with research-use clause).

Full per-source attribution + upstream-license chain in [CREDITS.md](CREDITS.md).

### Methodology

[METHODOLOGY.md](METHODOLOGY.md) documents the methodology behind v1.0.0:

- **§3 Sources and source-type hierarchy** — 10-value `source_type` enum (`primary_registry` / `inferred` / `manufacturer_app` / `crowdsourced` / `official` / `manufacturer_doc` / `regulatory` / `procurement` / `academic` / `foia`) with confidence bands per source-class. The `primary_registry` band covers IEEE OUI / FCC EAS / FAA RID / Bluetooth SIG registry-class allocators with a 70-85 single-source ceiling.
- **§4 Identifier types** — 48-value `identifier_type` enum across three structural categories: wire-observable (route to Lynceus-bound JSON exports), parametric / sub-protocol / forensic (DROPPED-class — analytical only, CSV export only), and alias-collapse (route to existing pattern_type).
- **§5 Confidence model** — calibrated integer 0-99 (humility-margin invariant; schema-CHECK permits 0-100 with operational cap at 99) with source-type bands, `+5` corroboration boost, lowest-contributing-ceiling rule, `primary_registry` sub-banding, and `manufacturer_app` per-class sub-banding. Discrete confidence shapes diverge for `procurement_records` (continuous 0-100, no humility margin) and `council_minutes_matters` (discrete 70/75/80 per item-grading); see DATA_DICTIONARY §6.2.
- **§6 Dedup + reclassification logic** — collapses N citations of the same identifier to a single canonical row with corroboration chain preservation; superseded-row preservation discipline (`identifiers.superseded_by` pointer chain). Row-level reclassifications (band/confidence/source_url changes) land an entry in `source_reclassifications` with `sweep_event_id` grouping + pre/post snapshot + rationale anchor.
- **§7 Provenance discipline** — `raw_observations` as source-of-truth; `source_url` must be working at ingest + verbatim-preserved post-fetch (pinned-SHA + line-anchored URL template, e.g., `/blob/<sha>/<path>#<anchor>`); no-fabrication hard rule; third-party-citation-lineage boundary; no-PII discipline; amendment-log discipline.
- **Feist facts-only promotion** — public-but-unlicensed sources (NO_LICENSE_DECLARED) qualify for facts-only extraction under *Feist v. Rural Telephone Service* (499 U.S. 340 (1991)). Argus extracts factual claims (identifier values, manufacturer attributions); Argus does NOT republish the source's compilation arrangement. Per-row canonical sentinel: `notes.upstream_license_posture='NO_LICENSE_DECLARED'`.

### License posture

- **Code:** AGPL-3.0-or-later ([LICENSE](LICENSE)) — network-use copyleft preserves source-availability for derivative scanners; AGPL-3.0 inheritance-compatible with community-contributed sources at `sources.id` 38/40/43.
- **Dataset:** ODbL-1.0 ([LICENSE-DATA](LICENSE-DATA)) with three-layer per-row license-posture composition:
  - **Layer 1** `sources.notes.license_posture` (per-source declaration; 6 distinct posture classes documented in LICENSE-DATA §2.1)
  - **Layer 2** `deployment_observations.LICENSE` (per-row NOT NULL column, migration 0016; Atlas rows quarantined under CC-BY-NC-SA-4.0 NC clause; DeFlock rows under ODbL-1.0)
  - **Layer 3** `identifiers.notes.upstream_license_posture` (per-promoted-identifier canonical sentinel key)
- **Documentation:** CC-BY-SA-4.0 ([LICENSE-DOCS](LICENSE-DOCS)) — ShareAlike preserves the discipline-architecture open-availability for derivative documentation.
- **DMCA / takedown posture:** project-side doctrinal grounding is Feist factual-data + 17 USC §1201(j) security-research exemption + 37 CFR §201.40(b) + nominative fair use. Vendor attribution disputes route through a GitHub issue.

### Schema versioning

The migration ledger (`schema_version` table) tracks every applied migration. v1.0.0 ships at `MAX(version)=19`. Migrations are forward-only (no rollback); schema-changing PRs land paired with the project's amendment-log discipline ([BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md)). Downstream consumers should check `schema_version` at runtime when integrating against a downloaded `argus.db`.

**Migration ledger summary (1 → 19):**

- **0001** initial schema — `identifiers` + `raw_observations` + `sources` + `manufacturers` + `extraction_runs` + `conflicts` + `schema_version` + 5 enum CHECK constraints
- **0002-0005** supporting tables — `procurement_records`, `fcc_grantees`, `council_minutes_matters`, `wigle_anchor_priority`, `deployment_observations`
- **0006** PDF/SDK/FCC-report corpus support
- **0007** vendor companion app static analysis support
- **0008-0010** identifier-type extensions (`product_family_codename`, `ble_local_name`, `ble_characteristic`) + `behavioral_signatures` table + `ble_manufacturer_id` enum extension
- **0012-0014** LA-bit pairing (`paired_identifier_id` + `pair_kind`) + Drone-RID identifier_type cluster + ALPR/camera `alpr_model`
- **0015** `source_type='primary_registry'` band for IEEE OUI / FCC EAS / FAA RID / Bluetooth SIG registries
- **0016** `deployment_observations.LICENSE` per-row license tag (Atlas CC-BY-NC-SA-4.0 + DeFlock ODbL-1.0 quarantine)
- **0017** `source_reclassifications` audit table (row-level reclassification ledger)
- **0018** identifier_type enum extension (14 net-new types from community-research dir Phase 1)
- **0019** identifier_type enum extension (7 net-new types from round-2 vocabulary review; cumulative CHECK enum 41 → 48)

### Amendment ledger (v1.0.0 substantive amendments)

The full amendment log lives in [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md). Below is the substantive-amendment summary for v1.0.0 release.

**Schema / data-shape amendments:**

- **`identifier_type` enum extension cluster** — added `product_family_codename`, `ble_local_name`, `ble_characteristic`.
- **LA-bit pairing** — added `paired_identifier_id` + `pair_kind` columns; Drone-RID identifier_type cluster; ALPR/camera `alpr_model` taxonomy.
- **`source_type='primary_registry'` band** — added for registry-class allocators (IEEE OUI / FCC EAS / FAA RID / Bluetooth SIG) with 70–85 single-source ceiling.
- **`source_type='manufacturer_app'` sub-banding** — vendor companion-app per-class confidence bands + cohort distinction (operator-facing vs installer/pairing-flow apps).
- **`behavioral_signatures` sibling export** — added `argus_export_behavioral_signatures.json` (Rayhunter-consumable).
- **`source_reclassifications` audit table** — added row-level reclassification ledger (`sweep_event_id` grouping + pre/post snapshot + rationale).
- **Lynceus mapping table updates** — populated the Lynceus identifier-type mapping entries for added `identifier_type` values.
- **`identifier_type` enum extensions** — added 14 net-new types from community-research dir Phase 1 + 7 net-new types from round-2 vocabulary review (cumulative CHECK enum 41 → 48).
- **`deployment_observations.LICENSE` per-row column** — added (NOT NULL; Atlas CC-BY-NC-SA-4.0 + DeFlock ODbL-1.0 quarantine).
- **`notes.upstream_license_posture` canonical sentinel-key** — established for facts-only promoted rows (`'NO_LICENSE_DECLARED'`).

**Integration / consumer-facing amendments:**

- **`argus_record_id` stable-identifier algorithm** — `sha256('<identifier_type>|<normalized_identifier>')[:16]`. Stable across re-runs, source-attribution changes, and confidence drift.
- **`geographic_scope` filter** — applied at export time.
- **Severity ownership** — moved operator-side via `severity_overrides.yaml`. Argus ships factual data; downstream consumers own alerting policy.
- **Multi-purpose-vendor carveout** — `device_category='unknown'` excluded from high-confidence Lynceus export.
- **Provenance discipline** — source-url-direct hard rule + per-shape mapper URL template (pinned-SHA + line-anchored).
- **Feist facts-only doctrine** — codified for public-but-unlicensed sources.

**Discipline-evolution amendments:**

- **"Argus identifies; Lynceus correlates"** — architectural boundary: Argus ships factual attribution data; downstream scanners own correlation and alerting.
- **Confidence-band ceiling rule** — corroborated confidence is bounded by the lowest contributing source-type band ceiling.
- **Vendor-disambiguation predicate** — Motorola Mobility / Solutions canonical split; WatchGuard Video / Technologies split.
- **LAA-bit confidence penalty** — locally-administered MAC addresses receive reduced confidence.
- **CVE false-positive allowlist + framework-UUID SDO-attestation discipline** — extraction-time false-positive classification.
- **Amendment-log discipline** — coordinated commits pair canonical-bible edits with this CHANGELOG and the per-row audit trail.
- **No-PII default-to-HOLD** — individual-attributed names without corporate-entity confirmation stay held.

### Pre-v1.0.0 history (major milestones)

The dataset was built over roughly two weeks of intensive multi-agent orchestration. Major milestones, in chronological order:

- **2026-05-04** — Argus working name confirmed; Tier-1 source acquisition complete (Atlas of Surveillance + DeFlock + IEEE OUI + Wireshark `manuf`).
- **2026-05-05 to 05-07** — PDF/HTML extraction waves; the architectural boundary between Argus and Lynceus codified (Argus ships factual attribution; Lynceus owns correlation); coordinated Lynceus integration commits (geographic_scope filter; severity operator-side; `argus_record_id`; multi-purpose-vendor carveout).
- **2026-05-08** — Vendor companion app static analysis admitted as a source class (under the 17 USC §1201(j) + 37 CFR §201.40(b) security-research exemption).
- **2026-05-11** — Community-research GitHub corpus acquired (24 repos); identifier-type extensions for LA-bit pairing, Drone Remote ID, and ALPR/camera taxonomy landed; promotion-cycle-1 closed.
- **2026-05-12** — Promotion-cycle-2 closed (~423 promotions); `primary_registry` source-type band introduced for registry-class allocators; 481 FAA RID drone_id_prefix promotions; Lynceus mapping populated for new identifier_types.
- **2026-05-13** — `manufacturer_app` sub-banding for vendor companion apps; behavioral_signatures sibling export (`argus_export_behavioral_signatures.json`); first behavioral_signatures population (0 → 55 from Marlin NDSS 2025); sources reclassification sweep (808 reclassifications); `source_reclassifications` audit table introduced.
- **2026-05-14** — Final release-readiness pass: IEEE PII triage and promotion (3,446 Class A); community-research deferred-dir Phase 2 close (145 promotions + 38 behavioral-signature backfills); Feist facts-only doctrine codified for public-but-unlicensed sources; final pre-release cleanup; v1.0.0 ship-readiness verified.

### Known limitations + post-v1.0.0 roadmap

Argus's v1.0.0 coverage is **intentionally narrow at this baseline** — do not assume comprehensive coverage of any specific surveillance equipment category. Expansion comes via the community contribution flow (standard GitHub PR + issue process) plus the following queued post-v1.0.0 work:

**Documented held items with rationale** (framed as "known held items; contribution welcome" not "incomplete data"):

- **31 behavioral_signatures** held pending second-source corroboration (substantive research-and-scrape work). Currently HELD with explicit rationale at `behavioral_signatures.notes`.
- **62 Class B sustained holds** (IEEE-derived individual-attributed-pii_sustain rows with `notes.registry_xcheck_attempted=true`) — sustained per the PII default-to-HOLD rule; predominantly Lumiplan Duhamel ×9 (French digital-signage corporate; no FCC registration), individual-shaped names, and ~50 unique singletons with no surveillance-tech-vendor or FCC-grantee evidence.
- **133 IEEE Private permanent holds** (`pii_review_disposition='ieee_private_registrant_permanent_hold'`) — IEEE OUI registrations declared as private at the registry source; ownership cannot be confirmed.
- **142 round-2 held rows** (107 vocabulary-extension candidates + 19 behavioral-signature deferred + 15 CVE false-positive entries filed to the conflicts table + 1 attribution-pending Motorola/Vigilant).
- **Known sources-row metadata discrepancy** — sources 1/2/3/7 carry historic `source_type='regulatory'` metadata pre-dating the source-type taxonomy refinement; identifier-row data is correctly labeled `primary_registry`. Cleanup queued post-ship. Downstream consumers filtering on `sources.source_type='primary_registry'` should also include `sources.id IN (1,2,3,7)` until the cleanup lands.

**Future-enrichment hooks (operationally inert at v1.0.0):**

- **WiGLE integration** — the `wigle_anchor_priority` table ships at v1.0.0 populated with 80,697 pre-computed priority rankings but operationally inert (WiGLE API gated on user's own quota grant per WiGLE Terms of Service). Post-grant, the WiGLE integration activates without re-derivation.

**Substantive expansion areas (planned post-v1.0.0):**

- **Future community-source-acquisition waves** — additional crowdsourced + community-OSINT + court/FOIA + news/forum source families pending admission-review under the project's source-admission workflow.
- **iOS vendor companion app coverage** — vendor companion app static analysis extended to iOS APK/IPA binaries (v1.0.0 was Android-first; iOS adds vendors with iOS-exclusive companion apps).
- **Skydio Enterprise alt-channel scope** — `com.skydio.enterprise` Android package is law-enforcement-only distribution; alt-channel sourcing approach is a future scope proposal.
- **107 round-2 vocabulary held candidates** — the operator may extend the `identifier_type` enum or accept the candidates as out-of-scope at a future amendment boundary.
- **Lynceus MAP extensions for net-new identifier_types** — `ble_service_uuid` and `ble_company_id` are already aliased to existing pattern_types; other net-new types are currently DROPPED-class. Lynceus integrators may surface specific MAP needs in v1.x patch releases.
- **License-posture composition extensions** — additional downstream-consumer guidance may emerge if new license-posture classes surface.

### Build process

Argus v1.0.0 was built using a multi-agent orchestration platform (Paperclip) with bible-as-contract discipline. Build-process detail in [METHODOLOGY.md §8](METHODOLOGY.md). Commit metadata reflects the agent-ensemble + human-operator authorship per the project's authorship discipline; full identity attribution lives in the git log + [CREDITS.md](CREDITS.md) "Build authorship" section.

**Reproducibility:** the migrations and source-loaders in this repo deterministically reproduce the database from upstream public sources; the agent ensemble is not required at runtime. Re-running the build against current upstream snapshots will yield drift from the v1.0.0-tagged DB because upstream sources change. **Tagged DB releases (downloadable from GitHub Releases) are the canonical artifact for downstream consumers.**

### Acknowledgments

Argus v1.0.0 is the product of public-record research and aggregation across 43 upstream sources + the canonical 34-entry surveillance-tech vendor lexicon. See [CREDITS.md](CREDITS.md) for full per-source attribution.

Particular thanks to the upstream data sources whose licenses make this work possible:

- **EFF + UNLV Reynolds School of Journalism Atlas of Surveillance** (CC-BY-NC-SA-4.0) — the largest single deployment-observation corpus integrated (15,071 rows).
- **DeFlock** (ODbL-1.0) — ALPR-camera deployment observations integrated under license-compatible terms (101,597 rows).
- **IEEE Standards Association OUI registries** — public factual data anchoring the entire OUI→manufacturer attribution chain (~70,000 rows across MA-L/MA-M/MA-S/IAB).
- **FCC Equipment Authorization System** — public regulatory data anchoring the `fcc_id_anchored` disambig allowlist (50,153 grantees).
- **FAA Remote ID public registry** — public registry data anchoring the drone-class `drone_id_prefix` identifier-type cluster (427 active rows).
- **Bluetooth SIG company-identifier registry** — `ble_manufacturer_id` allocations (3,971 active rows).
- **NDSS 2025 Marlin: Detecting IMSI-Catchers by Characterizing Identity Exposing Messages in Cellular Traffic** — academic foundation for the `behavioral_signatures` table (53 raw observations contributing 55+38=93 corroborated signatures).
- **22 canonical community-OSINT contributors** + **5 secondary-batch contributors** — public open-source-intelligence research repositories listed at [CREDITS.md §5](CREDITS.md).
- **GainSec / anti-crime-ecosystem-research + flock-safety-falcon-sparrow-alpr-edl-firehose** — firmware-binary-anchored extracts (CC-BY-NC-ND-4.0 with research-use clause + NO_LICENSE_DECLARED under the Feist facts-only regime).
- **Wireshark community** — `manuf` file cross-reference for vendor-name curation.

### Integrating with v1.0.0

This is the first tagged release; there is no prior version to migrate from. Downstream consumers integrating Argus for the first time:

1. Download the `argus.db` release artifact from this release's GitHub Releases page (canonical), or build-from-source per [SETUP.md](SETUP.md).
2. Verify `schema_version=19` via `python3 argus_cli.py status` (or directly: `SELECT MAX(version) FROM schema_version;`).
3. Read [METHODOLOGY.md §5](METHODOLOGY.md) (confidence model) before threshold-filtering rows for downstream-scanner watchlists.
4. Read [DATA_DICTIONARY.md §6.2](DATA_DICTIONARY.md) (confidence-shape divergence) before integrating cross-table corroboration logic.
5. Read [LICENSE-DATA §2.1 + §4](LICENSE-DATA) for per-row license-posture handling (CC-BY-NC-SA-4.0 NC clause carry-forward; ODbL-1.0 ShareAlike; Feist facts-only regime; AGPL-3.0 inheritance).
6. Implement the JSON/CSV consumer per the export shapes documented at METHODOLOGY §5.5; bind to `argus_record_id` (16-hex-char SHA-256 prefix, `sha256('<identifier_type>|<normalized_identifier>')[:16]`) as the stable consumer-facing identifier across re-runs.
7. Filter `deployment_observations` on the `LICENSE` column for derivative-use compliance:
   - Commercial deployments: exclude `WHERE LICENSE = 'CC-BY-NC-SA-4.0'` (Atlas rows; non-commercial use only)
   - Standard ODbL ShareAlike compliance: include all (DeFlock + Atlas non-commercial use is licensed)
8. For consumers using `csv.DictReader` against `argus_export.csv`: line 1 is a `# meta:` comment with schema/timestamp/record count; line 2 is the column header. Skip line 1 or use a sniffer-aware reader (e.g., `pd.read_csv(comment='#')`).

---

## Future releases

The project will tag releases when substantive new data, new source families, or schema-impacting changes land. Notable post-v1.0.0 work queued (per "Known limitations + post-v1.0.0 roadmap" above):

- **v1.0.x patch releases** — refresh post-integration of any new public-record source family that completes the source-admission workflow during the post-v1.0.0 cycle; refresh post-resolution of held items (behavioral_signatures second-source corroboration; Class B re-triage if new registries become available).
- **v1.1.0** — projected to ship iOS vendor companion app coverage + future community-source-acquisition waves + Skydio Enterprise alt-channel resolution.

Release cadence: tagged releases when substantive change accumulates; no fixed schedule. Higher-major-version releases (v2.x+) are not projected at the v1.0.0 baseline; they would be documented at the time the change set triggering them is approved.

---

## Canonical sources

Descriptive references used in this document map to canonical bible
anchors as follows. The canonical bible (`PROJECT_BIBLE.md` and the
amendment ledger `BIBLE_AMENDMENTS.md`) holds the authoritative
specification; this CHANGELOG is the public-facing summary.

| Descriptive reference (as used in this doc) | Canonical source |
|---|---|
| canonical 34-entry surveillance-tech vendor lexicon | `PROJECT_BIBLE.md` §2.1 |
| source-type ten-value enum / confidence-band ceilings | `PROJECT_BIBLE.md` §8.2 |
| `+5` corroboration boost / corroboration math | `PROJECT_BIBLE.md` §8.3 |
| confidence model | `PROJECT_BIBLE.md` §5 |
| Lynceus identifier-type mapping | `PROJECT_BIBLE.md` §4.4 |
| export-shape contract | `PROJECT_BIBLE.md` §7.5 |
| hard-rule set (source-url-direct, no-PII, provenance, confidence-ceiling, amendment-log, Feist facts-only) | `PROJECT_BIBLE.md` §11 |
| Feist facts-only doctrine / canonical sentinel-key | `PROJECT_BIBLE.md` §11 #16 |
| `source_type='primary_registry'` band introduction | `BIBLE_AMENDMENTS.md` CP15 |
| `identifier_type` extension cluster (`product_family_codename` + `ble_local_name` + `ble_characteristic`) | `BIBLE_AMENDMENTS.md` CP13 |
| LA-bit pairing + Drone-RID + ALPR/camera taxonomy | `BIBLE_AMENDMENTS.md` CP14 |
| `manufacturer_app` sub-banding + cohort distinction | `BIBLE_AMENDMENTS.md` CP17 |
| behavioral_signatures sibling export | `BIBLE_AMENDMENTS.md` CP18 |
| `source_reclassifications` audit table | `BIBLE_AMENDMENTS.md` CP19 |
| `argus_record_id` stable-identifier algorithm | `BIBLE_AMENDMENTS.md` SAR-10 |
| framework-UUID false-positive class catalog | `BIBLE_AMENDMENTS.md` SAR-11 |
| per-shape mapper precedent (per-shape mapper / URL template / identifier_type-vs-behavioral_signatures routing) | `BIBLE_AMENDMENTS.md` SAR-13 |
