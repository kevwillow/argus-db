# Wave H pre-v1 — HANDOFF TO VALIDATOR (partial-cohort close-out, session 1 + 2 final)

**Session dates UTC:** 2026-05-18 (session 1) + 2026-05-18 (session 2 continuation)
**Runguide:** `new data 5.18/wave_h_desktop_setup_app_runguide.md`
**Authority chain:** MAC-1 → ... → CP27 §-text amendment → MAC-179 (this wave) → partial-cycle close-out per CP26 §9.
**Cycle completion state:** `partial_cohort_set_complete`
**Schema baseline at handoff:** `schema_version=22` (read-only; no writes performed; re-verified at start of session 2 — unchanged).

---

## §9 closing-loop summary fields

| Metric | Value |
|---|---|
| Cohorts substantively processed | **2** (Cohort A descoped per CP17 finding; Cohort D + F calibration windows opened) |
| Cohort A | DESCOPED — 6 documented_absence rows; CP17 thesis preliminary recorded |
| Cohort D (drone tooling) | **calibration window CLOSED on the empirical-maximum record**: 1 independent vendor (DJI) × 2 product-family variants (Mavic + FPV; cross-product attested per CP24) + 1 documented_absence (Skydio; P11 CLEAN NEGATIVE) + 1 H2 FP-control (FileZilla). Cohort D freeze timestamp: 2026-05-18T23:55:00Z |
| Cohort F (sanctioned vendor) | vendor 1 complete (Hikvision iVMS-4200) with **CP26 §8 re-class to MSI ProductCode (not BLE)**; vendor 2 acquisition still blocked (Dahua / Uniview) — Cohort F window OPEN |
| Cohorts B / C / E / G / H | NOT STARTED — defer to Wave H Continuation |
| Vendors processed (real extraction) | **3 vendors, 4 binaries** (Hikvision + DJI×2 + FileZilla-as-FP-control) |
| Vendors emitted as `documented_absence` | 7 (6 Cohort A + 1 Skydio Cohort D) |
| Binaries acquired | 4 (45.7 + 220 + 241 + 12 MB = 519 MB; SHA-256 + provenance recorded each) |
| Binaries failed acquisition | 0 |
| Total candidates emitted (post-final-filter) | **133** |
| Total FP findings | **188** |
| **Unique candidate BLE UUIDs across all vendors (validator action required)** | **1** — `f4d4dbf5-ba4b-40db-9a44-f8395f3728cf` (DJI, surfaces in `https://duss.djicorp.com/functional-document/...`; cross-product attested between Mavic + FPV; semantic-validation re-class to `vendor_document_uuid_cloud_reference`) |
| **Net "genuine BLE service UUID" candidates** | **0** — after CP26 §8 semantic-validation, all surviving UUIDs across all 3 real-vendor binaries are NOT genuine BLE service UUIDs. They are either re-classed (DJI's `f4d4dbf5-...` = document UUID in cloud URL) or filtered (Hikvision MSI ProductCodes; DJI COM CLSID; Windows DEVCLASS/COM-IID/SXS-publicKey FPs) |
| Novel FP classes codified into wrapper (SAR-12 final roster) | **7** — see §6 below |
| Cross-vendor attestations | 1 (DJI Mavic ↔ DJI FPV; CP24 within-vendor-cross-product; resolved at validation as 1 genuine cross-product overlap + multiple Windows-platform-FP overlaps) |
| Cross-source corroborations | 0 (only 1 independent-vendor calibration vendor in Cohort D — Skydio absent; no cross-vendor independent-source overlap to test) |
| EULA-posture disposition counts | category_a:0, b:0, **c:3** (Hikvision + DJI + FileZilla all standard or open-source per §3.6 c-band), d:0 |
| Sanctioned-vendor Cohort F findings | 1 vendor (Hikvision) acquired + audited; CP28 candidate (b) sentinel `sanctioned_vendor_public_distribution_facts_only` empirical anchor moves from "BLE UUID yield" to "EULA + acquisition workflow clearance" |
| **Operator-vs-installer cohort thesis (CP17) generalization finding** | **Confirmed AND refined — see §10 below for the marquee policy paragraph** |
| Calibration freeze timestamps | Cohort A: DESCOPED (no window); Cohort D: 2026-05-18T23:55:00Z (post-H2 disambig); Cohort F: OPEN |

---

## §1 What got done across sessions 1 + 2

### Session 1 (initial extraction)

1. §2 precondition gates all PASS (post operator dispositions D1.a + D2.a + D3.a).
2. §3.0 CP27 P1-P10 probe AUTHORIZED dispatch (with operator-D2.a search-for-current-URL fallback).
3. `wave_h_wrapper.py` written as D3.a adapter (v4 untouched). P4 spot-test pass.
4. Toolchain on SSD: asar 4.2.0, dotnet 8.0.421, ilspycmd 9.1.0.7988, Ghidra 12.1, binwalk 2.3.4 (sudo), Playwright + Chromium 148.
5. Cohort A descoped — 6 documented_absence rows; CP17 thesis preliminary.
6. Acquired + extracted 3 binaries: Hikvision iVMS-4200 v3.13.0.5_Multilingual, DJI Assistant 2 For Mavic v2.0.14, DJI Assistant 2 (DJI FPV series) v2.1.2.
7. Pre-innoextract / pre-final-filter yield: 18 candidates with 5/5 Mavic-FPV UUID overlap.
8. Codified 3 SAR-12 FP classes (WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS / WINDOWS_COM_INTERFACE_GUIDS / WINDOWS_SXS_PUBLICKEYTOKEN).

### Session 1.5 (operator-provided unrar + innoextract installs)

9. `unrar` installed → Hikvision RAR payload extracted (209 MB Qt translations only; revealed bootstrap-installer pattern — app DLLs are not in this binary).
10. `innoextract` installed → DJI Mavic + FPV InnoSetup payloads extracted (617 MB / 693 MB respectively; revealed actual application DLLs: DJIService.exe, DJIDevice.dll, DJI_guidance.dll, etc.).
11. Yield jumped from 18 candidates pre-innoextract → 369 candidates post-innoextract, then filtered to 139 post-v3 (4 unique BLE UUIDs survived).
12. Codified 4 more SAR-12 FP classes (WINDOWS_DEVCLASS_SETUP_GUIDS / LIBUSB_ASCII_IDENTIFIERS / THIRD_PARTY_DLL_PATH_PREFIXES / value-level propagation).

### Session 2 (continuation: audit + closure)

13. **§1 Hikvision CP26 §8 audit:** both surviving Hikvision BLE UUID candidates (`9a25302d-...`, `ce2f96d0-...`) re-classed as **`windows_installer_productcode_in_msi_context`** — MSI/InstallShield ProductCodes (the iVMS-4200 main package + Multilingual Wizard sub-package). Codified the 7th SAR-12 FP class with context-substring-based detection (catches the `\{` bracket form, MSI Uninstall registry paths, InstallShield Wizard markers).
14. **§2 H2 disambig via FileZilla 3.70.5_win64:** confirmed the 5 `<supportedOS>` UUIDs are vendor-agnostic Windows-application-manifest framework FPs (present in FileZilla NSIS installer at the exact same XML manifest location). No new SAR-12 classes needed.
15. **§3 Skydio Pilot:** P11 CLEAN NEGATIVE (Skydio has no desktop "Pilot" application; mobile + hardware-controller + cloud only). documented_absence row emitted. Cohort D calibration window closed on the empirical-maximum record (DJI cross-product + Skydio absence + FileZilla FP-control).
16. Re-ran all 3 real-vendor binaries against the v4-with-session-2-MSI-context filter — yield converged.

---

## §6 SAR-12 final roster (7 codified Wave H supplemental FP classes)

| # | Class | Wave H seed entries | Scope |
|---|---|---|---|
| 1 | `WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS` | 5 (Vista / 7 / 8 / 8.1 / 10) | Microsoft application-manifest compatibility GUIDs — every Windows installer embeds. Validated by DJI (both variants) + FileZilla. |
| 2 | `WINDOWS_COM_INTERFACE_GUIDS` | 1 seed (`IID_IShellLinkA`) | Microsoft Windows SDK COM IIDs. Predicted by runguide §3.5; confirmed at Hikvision. **Validator: bulk-seed from Windows SDK `combase.h`, `shobjidl.h`, `objidl.h`, `oaidl.h`, `unknwn.h` headers — expected ~500-2000 IIDs.** |
| 3 | `WINDOWS_DEVCLASS_SETUP_GUIDS` | 11 (USB / Media / Modem / Net / HID / 1394 / Image / MTP / USB_DEVICE / WCEUSBS / BUS_TYPE_USB) | SetupAPI device-class GUIDs. Surfaced ~104 times across DJI binaries — single largest FP class. |
| 4 | `LIBUSB_ASCII_IDENTIFIERS` | 1 (libusb-win32-WDF as ASCII-embedded UUID) | UUID-shaped ASCII strings inside libraries. Specific to libusb-win32. |
| 5 | `THIRD_PARTY_DLL_PATH_PREFIXES` | ~26 prefixes (Qt5*, libcrypto-*, libssl-*, libeay32, msvcp*, msvcr*, vcruntime, libusb0, libusb-1.0, d3dcompiler_*, libegl, libglesv2, sqlite3, icu*, iconv, libffi, libxml2, zlib) | Any UUID-class candidate whose source_file_relative path leaf starts with these 3rd-party library names is filtered as framework noise. |
| 6 | `WINDOWS_SXS_PUBLICKEYTOKEN` | 3 (Microsoft.Windows.Common-Controls / public assemblies / .NET Framework defaults) | 16-char hex publicKeyTokens in `<assemblyIdentity>` XML manifests; caught by v4 credential regex. |
| 7 | `windows_installer_productcode_in_msi_context` | Context-substring based (8 markers including `\{`, `\Uninstall\{`, `InstallShield Wizard`) | MSI/InstallShield ProductCode GUIDs in Windows Installer registry contexts. Codified post-Hikvision-CP26-§8-audit. |

**Aggregate effect:** Wave H pipeline catches **188 FPs across 4 binaries** that v4 alone would have promoted to candidates. After CP26 §8 semantic-validation of the 4 unique surviving UUIDs, **0 net genuine `ble_service_uuid` candidates remain** — all 4 re-class as different identifier classes (MSI ProductCode × 2, COM CLSID × 1, document UUID × 1).

---

## §7 Per-vendor final metrics

```
per_vendor/hikvision_ivms_4200/             ← 10 cands, 12 fps; 0 genuine BLE UUIDs (2 → MSI ProductCode FP)
per_vendor/dji_assistant_2_mavic/           ← 64 cands, 88 fps; 1 candidate UUID (f4d4dbf5-... → vendor_document_uuid_cloud_reference)
per_vendor/dji_assistant_2_fpv/             ← 59 cands, 88 fps; 1 candidate UUID (same; cross-product attested)
per_vendor/filezilla_fp_disambig/           ← 0 cands, 0 fps (H2 control; 4 supportedOS UUIDs hit overflow_dropped before reaching FP filter — known wrapper-behavior detail documented in h2_disambig_filezilla_run.md)
per_vendor/_cohort_a_documented_absence.json ← 6 Cohort A vendors
per_vendor/skydio_pilot_documented_absence.json ← 1 Cohort D vendor 2 (P11 CLEAN NEGATIVE)
```

---

## §8 Cross-vendor attestations + cross-source corroborations (CP24 bucket discipline)

**`cross_vendor_attestations.json` (CP24 within-vendor-cross-product):** 1 attestation — DJI Mavic + FPV cross-product overlap (post-final-filter: 1 vendor-specific UUID `f4d4dbf5-...` + the pre-filter 5 supportedOS GUIDs that drove H1/H2 disambig).

**`cross_source_corroborations.json` (CP24 independent-source / §8.3 lift candidates):** EMPTY — only 1 independent-vendor in Cohort D (DJI). Skydio absent prevented Cohort D cross-source corroboration test. **The `duss.djicorp.com` hostname is itself a finding worth cross-referencing in validator's downstream pass against FCC EAS DJI Mavic filings + USAspending DJI procurement filings + court records.**

No `vendor_internal_reextractions.json` emitted — the DJI Mavic ↔ FPV overlap is CP24 within-vendor-cross-product (cross_vendor_attestations bucket), not within-vendor-same-product-different-version (vendor_internal_reextraction bucket). No version-cross-vendor test attempted this session.

---

## §9 CP26 §9 partial-cycle close-out — admission metadata

```json
{
  "name": "Vendor Desktop Application Static Analysis — Wave H",
  "url": null,
  "source_type": "vendor_documentation",
  "tier": 1,
  "license": "per_vendor",
  "license_attribution": "Hikvision iVMS-4200 EULA (download-agreement modal) + DJI EULA + FileZilla GPLv2 — all §3.6 (c) include.",
  "notes_json": {
    "session_admission": "wave_h_pre_v1",
    "session_count": 2,
    "admission_date_utc": "2026-05-18T00:00:00Z",
    "runguide_path": "new data 5.18/wave_h_desktop_setup_app_runguide.md",
    "cycle_completion_state": "partial_cohort_set_complete",
    "next_cycle_dispatch_scheduled_for_utc": "TBD_post_v1_3_0",
    "next_cycle_dispatch_runguide_path": "new data 5.18/wave_h_continuation.md",
    "partial_yield_metrics_at_admission": {
      "cohorts_calibration_closed": ["D_drone_firmware_tooling (empirical-maximum record: 1 independent vendor + cross-product + 1 documented_absence + 1 FP control)"],
      "cohorts_calibration_open": ["F_sanctioned_vendor (vendor 1 only — Hikvision; vendor 2 acquisition still blocked at Dahua/Uniview Cloudflare)"],
      "cohorts_descoped": ["A_electron (CP17 thesis-finding-driven)"],
      "cohorts_not_started": ["B_dotnet", "C_native_cpp", "E_firmware_images", "G_adjacent_vms", "H_forensics_acoustic_drone_detection"],
      "vendors_processed": 3,
      "vendors_documented_absence": 7,
      "binaries_acquired": 4,
      "candidates_total_post_audit": 133,
      "candidates_by_class_post_audit": {
        "ble_service_uuid_unique": 1,
        "ble_service_uuid_after_cp26_8_reclass": 0,
        "product_family": 4,
        "snmp_enterprise_oid_unique_pre_validator_pass": 24,
        "update_endpoint_url_unique_pre_validator_pass": 5
      },
      "fp_findings_total": 188,
      "sar_12_fp_classes_codified": [
        "WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS",
        "WINDOWS_COM_INTERFACE_GUIDS",
        "WINDOWS_DEVCLASS_SETUP_GUIDS",
        "LIBUSB_ASCII_IDENTIFIERS",
        "THIRD_PARTY_DLL_PATH_PREFIXES",
        "WINDOWS_SXS_PUBLICKEYTOKEN",
        "windows_installer_productcode_in_msi_context"
      ],
      "cp17_thesis_finding": "BIFURCATED — see §10 below. Operator-cohort dissolved into web/mobile (Skydio absent + Cohort A descope). Installer-cohort desktop binaries DO exist (DJI, Hikvision) but yield NON-BLE identifier classes (MSI ProductCode, COM CLSID, document UUID in cloud URL) rather than BLE service UUIDs. Wave G mobile axis vs Wave H desktop axis differ on identifier-class surface, not just cohort presence.",
      "h2_disambig_outcome": "CONFIRMED via FileZilla control: WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS are vendor-agnostic framework FPs.",
      "cp24_within_vendor_cross_product_buckets": {
        "dji_mavic_fpv": "1 vendor-specific UUID (f4d4dbf5-... vendor_document_uuid_cloud_reference) cross-product attested"
      },
      "cp28_candidate_flags_surfaced": ["see §11 below"],
      "tooling_installed_to_ssd": [
        "asar@4.2.0", "dotnet@8.0.421_SDK", "ilspycmd@9.1.0.7988",
        "ghidra@12.1_PUBLIC", "binwalk@2.3.4 (system, sudo)",
        "unrar@7.00 (system, sudo)", "innoextract@1.9 (system, sudo)",
        "playwright_chromium@148.0.7778.96"
      ],
      "extraction_tools_used_per_binary": {
        "hikvision_ivms_4200": ["7z@23.01", "binwalk@2.3.4", "unrar@7.00", "strings (GNU binutils)", "wave_h_wrapper.py"],
        "dji_assistant_2_mavic": ["7z@23.01", "binwalk@2.3.4", "innoextract@1.9", "strings", "wave_h_wrapper.py"],
        "dji_assistant_2_fpv": ["same as Mavic"],
        "filezilla_fp_disambig": ["7z@23.01", "strings", "wave_h_wrapper.py"]
      }
    },
    "license_posture": "per_vendor",
    "upstream_license_posture": "no_license_declared_facts_only (default per CP21); Hikvision pending CP28 candidate (b) sanctioned_vendor_public_distribution_facts_only sentinel — anchor weakened post-§1 audit (see §11)",
    "access_mode": "public_download_no_auth (3 vendors); FileZilla also public_download_no_auth (control); Skydio absent",
    "vendors_processed_with_real_extraction": 3,
    "calibration_freeze_timestamp_per_cohort": {
      "A_electron": "DESCOPED_NO_WINDOW_FIRED_per_cp17",
      "D_drone_firmware_tooling": "2026-05-18T23:55:00Z (closed on empirical-maximum record post-H2-disambig + Skydio P11 CLEAN NEGATIVE)",
      "F_sanctioned_vendor": "OPEN_vendor_2_acquisition_blocked_at_dahua_uniview_cloudflare"
    },
    "eula_posture_disposition_counts": {"category_a_drop": 0, "category_b_board_review": 0, "category_c_include": 3, "category_d_drop": 0},
    "sanctioned_vendor_findings_count_post_audit": 0,
    "sanctioned_vendor_acquisition_workflow_validated": true
  },
  "last_fetched_at": "2026-05-18T23:50:19Z",
  "last_status": "partial_cycle_handoff_session_2_complete_cp26_8_audit_done_h2_disambig_done_skydio_p11_negative"
}
```

**Validator: do NOT insert this row into `sources` table until Wave H Continuation closes Cohort F + at least one of Cohort B/C.** The methodology + 7 SAR-12 FP classes are now stable; what's pending is breadth across cohorts B/C/E/G/H.

---

## §10 CP17 desktop-axis thesis bifurcation finding (marquee policy output for board)

The original CP17 cohort thesis (Wave G mobile origin) predicted that the operator-vs-installer cohort split would generalize from mobile to desktop. Wave H sessions 1 + 2 empirically refine this in two distinct dimensions:

**Dimension 1 — cohort presence:** the operator-cohort desktop class has structurally dissolved into web/mobile across modern VMS + drone-tooling vendors. Session 1 confirmed this for VMS (5 of 6 Cohort A targets were web-only or UWP-MSIX, not Electron desktop). Session 2 §3 confirms this for drone tooling (Skydio Pilot does not exist as a desktop application — Skydio's distribution is mobile + hardware-controller + cloud). The installer-cohort desktop class persists (DJI Assistant 2 ships a desktop installer, Hikvision iVMS-4200 ships a desktop installer) but the operator-cohort class is empirically absent at the desktop axis in 2026.

**Dimension 2 — identifier-class surface:** this is the NEW Wave H finding that was not predicted in the runguide. Even within installer-cohort desktop binaries that DO exist (DJI, Hikvision), the identifier-class surface differs from what Wave G mobile-axis extraction surfaced:

- **Wave G mobile binaries yield genuine BLE service UUIDs** because the mobile companion is the BLE peripheral pairing endpoint. The phone IS the BLE central; the vendor app contains BLE service/characteristic UUIDs in code.
- **Wave H desktop binaries yield MSI ProductCodes + COM CLSIDs + cloud-document UUIDs + vendor-cloud-endpoint hostnames** — not BLE protocol identifiers. The desktop client is for camera/drone management; the BLE pairing surface is in the camera/drone firmware (Cohort E) or in the mobile app (Wave G), not in the desktop client.

**Policy implication for Lynceus + Talos:** Wave H desktop findings should be consumed as a different identifier-class surface than Wave G mobile findings. The two axes are not just operator-vs-installer-cohort sliced — they're also different identifier-class surfaces by execution model. A "BLE UUID + SSID" yield expectation that worked for Wave G mobile does NOT apply to Wave H desktop. Wave H desktop's value-add is in the **vendor cloud-endpoint discovery** layer (e.g., the `duss.djicorp.com` hostname surfaced from DJI Assistant 2 binaries — that's a vendor-controlled hostname useful for FCC EAS / USAspending / SEC EDGAR cross-source corroboration), the **installer-time configuration surface** (MSI ProductCode + COM CLSID = vendor-controlled OS-integration identifiers; useful for endpoint-fleet detection downstream), and **the absence-as-finding** (CP17 operator-cohort dissolution itself is a vendor-architectural-shift observation worth codifying).

**Wave I scoping implication:** future Wave I desktop-axis runguides should not assume BLE UUID yield as the headline metric. Re-scope to vendor cloud-endpoint discovery + installer-config surface as the substantive yield; treat BLE UUIDs as an opportunistic-extras find when they do surface (e.g., from firmware imagery in Cohort E).

---

## §11 CP28 candidate flags surfaced for post-Wave-H bible-amendment sweep

### (a) `vendor_application_static_analysis` source_type enum value

Wave G mobile (Android APKs) + Wave H desktop both land under `vendor_documentation` per CP15 source-type ceiling. With ~20+ vendors now extracted across Wave G + Wave H via static-analysis methodology, the band has empirical density. If Lynceus operationally wants Wave G + Wave H findings filterable as a class (separate from generic FCC/SEC/SAM-vendor-doc admissions), codify dedicated enum value. **Recommendation: lift to bible-amendment for the v1.3.0 sweep.**

### (b) `sanctioned_vendor_public_distribution_facts_only` license-posture sentinel

Originally proposed in session 1 with empirical anchor of "Hikvision iVMS-4200 surfaces real BLE UUIDs that benefit from the new posture sentinel." **Session 2 §1 CP26 §8 audit weakened this anchor** — the 2 surviving Hikvision UUIDs re-class as MSI ProductCodes, not BLE. The sentinel's empirical anchor now rests on the FACT that Hikvision distributes publicly via .com (not .cn) AND the EULA-posture + sanctioned-vendor sub-gate workflow was cleared per CP20 §11 #16, NOT on identifier yield. **Recommendation: codify the sentinel anyway** — the workflow-clearance audit anchor is valid (sanctioned-vendor public-distribution distinction matters operationally for Lynceus consumers regardless of identifier yield at that specific vendor), but the empirical density is thinner than session 1 suggested. May want to defer until Dahua + Uniview also acquired before locking the codification.

### (c) `windows_com_clsid_vendor_registered` + `vendor_document_uuid_cloud_reference` + `windows_installer_productcode_vendor_registered` as first-class identifier_type values

Wave H session 1 + 2 surfaced these three vendor-registered-but-not-BLE identifier classes empirically:
- DJI `054aae20-...` = COM CLSID for DJIBrowser LocalServer32 (now filtered by `\{` substring match, but the **value is a vendor-registered identifier worth promoting under a non-BLE class**)
- DJI `f4d4dbf5-...` = document UUID embedded in `duss.djicorp.com/functional-document/...` URL
- Hikvision `9a25302d-...` + `ce2f96d0-...` = MSI ProductCodes for iVMS-4200 main + Multilingual Wizard

Currently the wrapper FILTERS these (correctly, from a "genuine BLE UUID" perspective) but they ARE vendor-controlled identifiers with potential downstream value (endpoint-fleet detection: a deployed iVMS-4200 instance reports its MSI ProductCode through enterprise management tooling; a deployed DJI Assistant 2 instance leaves the DJIBrowser COM CLSID registered in the Windows registry; both are detectable signals). **Recommendation: codify as 3 new `identifier_type` enum values + the existing pipeline emits them to a NEW per-vendor `non_ble_vendor_identifiers.json` rather than filtering to `fp_findings.json`.** Bible amendment would need §4.4 mapping disposition for each of the 3 new identifier types. Reasonably high priority for the v1.3.0 sweep — the Wave H signal that does exist lives almost entirely in this class, and forcing it into fp_findings.json loses operational value.

---

## §12 Output artifacts (final)

```
/home/kev/argus-internal/desktop_test/extraction_outputs/wave_h_pre_v1/
├── HANDOFF_TO_VALIDATOR.md                            (this document)
├── STOP_THE_LINE_probe_p1_p2_p3_negative_plus_toolchain_2026-05-18.md
├── _probe_log.md                                      (CP27 §2.4 audit anchor; P1-P10 final)
├── cross_vendor_attestations.json                     (CP24 within-vendor-cross-product; DJI Mavic+FPV)
├── calibration/
│   └── calibration_window_findings.md                 (session-1 calibration; SAR-12 codification record)
└── per_vendor/
    ├── _cohort_a_documented_absence.json              (6 Cohort A documented_absence + CP17 thesis preliminary)
    ├── skydio_pilot_documented_absence.json           (Cohort D vendor 2 P11 CLEAN NEGATIVE)
    ├── hikvision_ivms_4200/
    │   ├── _provenance.json
    │   ├── candidates.json (10 cands; 0 BLE post-audit)
    │   ├── fp_findings.json (12 fps incl. 2 MSI ProductCode re-class)
    │   ├── extraction_counts.json
    │   ├── analysis_log.md (session 1)
    │   ├── hikvision_cp26_8_audit.md (session 2 ★ marquee disposition)
    │   └── source_excerpts/
    ├── dji_assistant_2_mavic/
    │   ├── _provenance.json
    │   ├── candidates.json (64 cands; 1 BLE candidate UUID f4d4dbf5)
    │   ├── fp_findings.json (88 fps)
    │   ├── extraction_counts.json
    │   ├── analysis_log.md (session 1)
    │   └── source_excerpts/
    ├── dji_assistant_2_fpv/
    │   ├── _provenance.json
    │   ├── candidates.json (59 cands; 1 BLE candidate UUID — same f4d4dbf5; cross-product attested)
    │   ├── fp_findings.json (88 fps)
    │   ├── extraction_counts.json
    │   └── source_excerpts/
    └── filezilla_fp_disambig/
        ├── _provenance.json
        ├── candidates.json (0 cands — H2 control)
        ├── fp_findings.json (0 fps — all hit overflow_dropped)
        ├── extraction_counts.json
        └── h2_disambig_filezilla_run.md (session 2)
```

**SSD anchors (gitignored / outside any git repo):**
- `/media/kev/Extreme SSD/argus/desktop_test/raw/vendor_desktop/{hikvision,dji,filezilla}/` (4 binaries, 519 MB total + provenance)
- `/media/kev/Extreme SSD/argus/desktop_test/scratch/{hikvision,dji,filezilla}/` (decompile + strings dumps)
- `/media/kev/Extreme SSD/argus/desktop_test/tools/` (Ghidra, dotnet, ilspycmd, asar, playwright-browsers — ~2.4 GB total)

**Wave H wrapper canonical location:** `/home/kev/argus-internal/argus.retired.20260518/android_test/tools/extraction/wave_h_wrapper.py` (v0.2_post_session_2; 7 SAR-12 FP classes codified; v4 extractor untouched per D3.a).

---

## §13 Recommended Wave H Continuation path

### Continuation A — Cohort F vendor 2 + at least 1 Cohort C (4-6 hours; operator-light)

1. Operator manually fetches Dahua SmartPSS or Uniview EZStation (Cloudflare bot-block prevents Playwright auto-acquisition) → closes Cohort F calibration window.
2. Acquire Avigilon ACC Client OR Axis Camera Station via Playwright + form-driven click-through → opens Cohort C calibration window with vendor 1.
3. Run both through pipeline; CP26 §8 audit each surviving UUID.

### Continuation B — Cohort B (.NET) trial-gated vendors (4-8 hours; operator-heavy)

4. Operator self-issues trial accounts for Milestone XProtect + Genetec Security Desk.
5. Acquire + extract + run wrapper (ilspycmd already installed for the .NET extraction path).

### Continuation C — Cohort E firmware images (4-8 hours; high EULA-gate risk)

6. §3.0 P7 Cradlepoint firmware re-probe (likely CLEAN NEGATIVE — Salesforce-gated kb per Wave-B2 MAC-18).
7. Hak5 firmware acquisition (Hak5 is research-toolkit-vendor; permissive posture).
8. Axis Device Manager firmware images.

### Wave I scoping (longer-horizon)

Per §10 CP17 thesis bifurcation finding: **re-scope desktop-axis runguides to vendor-cloud-endpoint discovery + installer-config surface as headline metrics, not BLE UUIDs**. Wave I should plan around the 3 new identifier_type values proposed in CP28 (c).

---

*End of HANDOFF. Wave H pre-v1 closes session 2 as `partial_cohort_set_complete` per CP26 §9. Cohort D calibration window closed on empirical-maximum record. Cohort F calibration window remains open pending vendor 2 acquisition unblock.*
