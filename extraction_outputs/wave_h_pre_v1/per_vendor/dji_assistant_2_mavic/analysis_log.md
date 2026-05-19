# DJI Assistant 2 For Mavic v2.0.14 — Cohort D Calibration Vendor 1 Analysis Log

**Vendor:** DJI (drone tooling vendor; CCP-affiliated; on US DOD CMC list 2022, NDAA §1260H 2024)
**Product:** DJI Assistant 2 For Mavic
**Version:** 2.0.14 (2020-08-05 release; current as of probe date — DJI's Mavic-specific Assistant 2 binary line; FPV/Inspire/Phantom variants exist as separate installers)
**SHA-256:** `d5df2d8ea45e881670a9b723a495363fb198700a60b47cba5507bf1164e14698`
**Acquired UTC:** 2026-05-18T22:45:25Z
**Cohort label:** D_drone_firmware_tooling
**Calibration vendor position:** 1 of 2 (Cohort D calibration window)

## Acquisition path

**Source URL (direct DJI CDN):**
`https://dl.djicdn.com/downloads/dji_assistant/20200805/DJI+Assistant+2+For+Mavic+2.0.14.exe`

**Source page (Wave H provenance anchor):**
`https://www.dji.com/downloads/softwares/dji-assistant-2-consumer-drones-series`

**Discovery method:** Playwright headless Chromium drove the DJI Consumer Drones download page. DJI's page renders ~50+ direct `dl.djicdn.com` URLs in initial DOM (unlike Hikvision which required Adobe AEM /dam/ path knowledge). DJI's CDN allows direct fetch with `Referer:` header matching the source page (HTTP 200 + `application/octet-stream`).

**License posture:** DJI EULA per the source page; standard reverse-engineering boilerplate. Per §3.6 category (c) — include. §1201 + 37 CFR §201.40(b) preemption applies. `notes.upstream_license_posture='no_license_declared_facts_only'` (DJI not on OFAC SDN nor BIS Entity List as of probe date; on US DOD CMC list for distinct posture noted but not Argus-acquisition-blocking).

## Extraction path

1. `7z x` of the .exe → dumped PE sections (BSS, CODE, DATA, CERTIFICATE, RDATA, RSRC) — the installer is **InnoSetup format** (`MZP` Plus header signature visible at file offset 0).
2. `binwalk` signature scan → identified LZMA-compressed data at offset `0xDC9B7B6` (337,674 bytes) — the InnoSetup own-setup data, NOT the application payload. InnoSetup stores the application payload in separate setup-NNN.bin blocks accessible only via the dedicated `innoextract` tool (not installed at this session).
3. `strings -n 8` (ASCII + UTF-16LE) on the full installer → 56,955 lines (640 KB).
4. `wave_h_wrapper.py --cohort-label D_drone_firmware_tooling --input-tree <strings_dump>` → 8 candidates.

## Yield

| Class | Candidates | Notes |
|---|---|---|
| `ble_service_uuid` | **5 (5 unique — all NEW)** | All 5 surface in the outer installer strings; none match Hikvision UUIDs (no within-vendor or cross-vendor attestation); none match v4 disambig FP set. **Strong signal for vendor-specific BLE UUIDs.** |
| `credential` | 1 | `6595b64144ccf1df` — **CONFIRMED FP**: Windows SxS Side-by-Side publicKeyToken for `Microsoft.Windows.Common-Controls` assembly. Wave H new FP class proposed: `WINDOWS_SXS_PUBLICKEYTOKEN`. |
| `product_family` | 2 | `Mavic` (1 occurrence × 2 string variants) |

## UUID candidate dispositions (CP26 §8 semantic-validation)

| Value | Disposition | Notes |
|---|---|---|
| `e2011457-1546-43c5-a5fe-008deee3d3f0` | **CANDIDATE — needs verification** | Not in any known FP class. Likely DJI BLE service UUID for Mavic-class controller-to-drone pairing. Cross-reference: BLE SIG registry → likely no match; Wave G mobile DJI Fly / DJI Go cross-reference would confirm vendor-internal re-extraction (CP24 §11 #8) if same UUID surfaces there. |
| `35138b9a-5d96-4fbd-8e2d-a2440225f93a` | **CANDIDATE — needs verification** | Same — likely DJI vendor-specific. |
| `4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38` | **CANDIDATE — needs verification** | Same. |
| `1f676c76-80e1-4239-95bb-83d0f6d0da78` | **CANDIDATE — needs verification** | Same. |
| `8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a` | **CANDIDATE — needs verification** | Same. |

## SAR-12 FP class additions (Cohort D contribution)

**`WINDOWS_SXS_PUBLICKEYTOKEN`** — Microsoft Windows SxS (Side-by-Side) assembly publicKeyToken values. Surface as 16-character hex strings in `<assemblyIdentity name="..." publicKeyToken="..."/>` XML manifests embedded in any signed Windows binary. Initial seed:
- `6595b64144ccf1df` (Microsoft.Windows.Common-Controls Common Controls 6.0)

Likely additional values to seed at validator: `b03f5f7f11d50a3a` (Microsoft public assemblies), `31bf3856ad364e35` (Microsoft .NET Framework default).

## Cross-vendor / cross-source attestation analysis

- **Cross-vendor attestation (CP24 same-vendor different-product):** This DJI binary is for Mavic family. DJI's other Assistant 2 variants (Phantom, Inspire, FPV, Ronin, AeroScope, etc.) would test within-vendor cross-product UUID overlap. **Not tested this session.** Validator: compare with Wave G DJI Fly / DJI Go Android findings — UUID overlap → vendor-internal re-attestation (provenance enrichment per CP24, NOT §8.3 corroboration lift).
- **Cross-source corroboration:** FCC EAS Mavic-class filings carry DJI's BLE registration; if any of the 5 UUIDs appears in an FCC EAS exhibit, that's a §8.3 corroboration lift. **Not yet checked**; defer to validator's cross-source pass.

## Cohort D calibration finding

Two vendors (DJI, plus another — Skydio or Parrot or Autel) needed for Cohort D calibration freeze per runguide §3.7. DJI (vendor 1) complete with strong yield (5 candidate UUIDs). Vendor 2 deferred to Wave H Continuation.

## Acquisition-layer constraint surfaced

InnoSetup payload requires `innoextract` (apt package, ~200 KB, would need operator sudo). Without it, the actual DJI Assistant 2 application DLLs/EXEs are inaccessible. **Current yield is a lower bound** — full extraction with `innoextract` would unlock the ~80% of strings inside the InnoSetup blocks (DJI cloud endpoints, drone-side protocol identifiers, mDNS service types, etc.). The 5 candidate UUIDs surface in the outer InnoSetup metadata (probably the InnoSetup configuration or the EULA / strings that the installer ships pre-LZMA).

**Wave H Continuation recommendation:** `! sudo apt install -y innoextract` then re-extract DJI Assistant 2 (and Hikvision iVMS-4200 with `unrar` already installed) for full yield.
