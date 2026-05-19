# Wave H — Calibration Window Findings (SAR-12 candidates)

**Session:** wave_h_pre_v1
**Calibration vendors processed:**
- Cohort F: Hikvision iVMS-4200 v3.13.0.5_Multilingual (vendor 1 of 2 — window OPEN; vendor 2 deferred)
- Cohort D: DJI Mavic Assistant 2 v2.0.14 + DJI FPV Assistant 2 v2.1.2 (vendor 1 with cross-product attestation; vendor 2 deferred)

**Freeze timestamp:** 2026-05-18T23:00:00Z (post Wave H FP class additions; both DJI binaries re-run with filtered yield)

---

## Headline finding — `WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS` is a critical Wave H FP class

**Discovery path:** Cohort D DJI Mavic + DJI FPV cross-product attestation surfaced 100% UUID overlap (5/5). Source-excerpt inspection revealed all 5 UUIDs appear in `<supportedOS Id="{...}"/>` lines — Windows application manifest XML for OS compatibility declaration.

**The 5 UUIDs are well-documented Microsoft Windows compatibility manifest GUIDs:**

| UUID | Windows version |
|---|---|
| `e2011457-1546-43c5-a5fe-008deee3d3f0` | Windows Vista |
| `35138b9a-5d96-4fbd-8e2d-a2440225f93a` | Windows 7 |
| `4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38` | Windows 8 |
| `1f676c76-80e1-4239-95bb-83d0f6d0da78` | Windows 8.1 |
| `8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a` | Windows 10 |

**Every Windows-targeting installer embeds these** for OS-compatibility declaration. They are NOT vendor BLE UUIDs even though they pass the v4 Pattern A regex.

**Cohort D pre-filter yield was 100% FP. Post-filter yield is 0 BLE UUIDs from outer-installer strings.**

This was a **critical calibration finding** — without this FP class, every Wave H Cohort B/C/D/F vendor extraction would have promoted these 5 FPs as "vendor UUIDs," and cross-vendor attestation would have aggregated them into a Wave H "DJI-like-platform-identifier" finding that propagated as evidence into Lynceus/Talos. The calibration window prevented this propagation.

This corroborates the runguide §3.5 prediction: *"Wave H likely surfaces: `.NET_DEVCLASS_GUIDS`... `COM_INTERFACE_GUIDS`... `WIX_INSTALLER_GUIDS`"* — extends with `WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS` (not in original prediction list; Wave H discovery).

---

## Wave H supplemental FP classes proposed for SAR-12 codification

### (1) `WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS` — Microsoft compatibility manifest GUIDs

Codified at `wave_h_wrapper.py` post-calibration-freeze. Seed list: 5 entries (Vista / 7 / 8 / 8.1 / 10). Likely additional entries when Windows 11 manifest GUID lands; validator should monitor.

**Expected match rate:** Approximately 100% of Cohort B/C/D/F Wave H binaries should contain at least 3-5 of these GUIDs (any application manifested for OS compatibility on Vista+).

### (2) `WINDOWS_COM_INTERFACE_GUIDS` — Windows COM/OLE interface IIDs

Seed: 1 entry (`IID_IShellLinkA`). Surfaced from Hikvision Cohort F vendor 1 strings dump.

**Recommended validator harvest:** bulk-seed from Windows SDK headers (`combase.h`, `shobjidl.h`, `objidl.h`, `oaidl.h`, `unknwn.h`) — every defined COM IID. Expected ~500-2000 IIDs as a one-time seed.

### (3) `WINDOWS_SXS_PUBLICKEYTOKEN` — Windows SxS assembly publicKeyToken values

Seed: 3 entries (Microsoft.Windows.Common-Controls, Microsoft public assemblies, .NET Framework default). Surfaced from DJI Cohort D as a `credential` candidate FP (extract_credentials regex matches the 16-char hex publicKeyToken).

**Pattern signature:** 16-character hex string appearing in `<assemblyIdentity name="..." publicKeyToken="..."/>` XML manifests. Wave H credential regex catches them because they're hex strings of credential-shape length, but they're publicly documented Microsoft assembly signing keys.

**Expected match rate:** ~100% of Cohort B/C/D/F binaries that link Windows common controls or .NET runtime.

---

## Cohort F vendor 1 (Hikvision iVMS-4200) calibration result

**Pre-filter:** 20 candidates total (8 BLE UUIDs across 3 unique values, 10 iVMS product_family, etc.)
**Post-filter:** 14 candidates total (8 FP findings emitted)
**Post-filter unique BLE UUIDs:** 2 candidate UUIDs (Hikvision-specific, need validator cross-reference):
- `9a25302d-30c0-39d9-bd6f-21e6ec160475`
- `ce2f96d0-63d2-4b9c-a8d6-0d1a60840bd8`

Both UUIDs appear ONLY in the outer-installer strings (`full_installer_strings.txt`) and not in the carved-PE strings or RAR-payload strings — suggests they're Hikvision-config-stage identifiers (SDK manifest, license-server token, etc.). Need validator cross-reference against Wave G Hikvision mobile APK extraction (if any) for vendor-internal re-attestation (CP24).

## Cohort D vendor 1 (DJI Mavic + FPV) calibration result

**Pre-filter:** 16 candidates total across both DJI variants (10 BLE UUIDs × 2 variants, 1 credential × 2, 2 product_family × 2)
**Post-filter:** 4 candidates total (0 BLE UUIDs, 4 product_family — `Mavic` × 2, `FPV` × 2 implied)
**12 FP findings** (5 supportedOS GUIDs × 2 variants + 1 publicKeyToken × 2)

**Vendor-internal re-attestation (CP24):** Mavic + FPV share the 5 supportedOS GUIDs (FP class) and 1 SxS publicKeyToken — these are NOT DJI-specific attestations.

**Real DJI BLE UUIDs are unrecoverable from outer-installer strings.** The actual DJI Assistant 2 application identifiers live in the LZMA-compressed InnoSetup payload at offset 0xDC9B7B6+. Requires `innoextract` (apt package, ~200 KB; not installed this session). Recommend Wave H Continuation step.

---

## Calibration window status — DO NOT FREEZE YET

**Cohort F:** OPEN — vendor 2 (Dahua SmartPSS or Uniview EZStation) needed before formal extractor + FP set freeze. Dahua's `support.dahuasecurity.com` triggers Cloudflare bot detection even via Playwright. Uniview's URLs return 404 globally. Deferred to Wave H Continuation with operator manual-acquisition path.

**Cohort D:** OPEN — vendor 2 (Skydio, Parrot, Autel) needed. Skydio Pilot confirmed no desktop client (Wave G mobile only). Parrot/Autel not probed this session.

**Cohort A:** CLOSED with substantive descope per CP17 thesis finding.

**Cohorts B / C / E / G / H:** NOT STARTED. Defer to Wave H Continuation.

---

## Disambig + extractor freeze (provisional, pre-vendor-2)

Wave H supplemental FP filter at `wave_h_wrapper.py` lines added post-calibration. The filter runs BEFORE v4's cross-site value-level FP propagation — ensures Wave H FP findings get carried forward via the same mechanism v4 uses.

**Provisional freeze hash:** Updated wave_h_wrapper.py at `2026-05-18T23:00:00Z` (file mtime). Re-extraction of all 3 vendor binaries against post-filter wrapper recorded above.

---

## Validator handoff at calibration close

| Vendor / variant | Pre-filter cands | Post-filter cands | FP findings | Real BLE UUID candidates |
|---|---|---|---|---|
| Hikvision iVMS-4200 v3.13.0.5 | 20 | 14 | 8 | 2 (need cross-reference) |
| DJI Mavic Assistant 2 v2.0.14 | 8 | 2 | 6 | 0 (all FPs; need innoextract for real yield) |
| DJI FPV Assistant 2 v2.1.2 | 8 | 2 | 6 | 0 (same) |

**Net unique candidate BLE UUIDs across Wave H session:** 2 (both Hikvision).

**Wave H Continuation key actions for unlocked yield:**
1. `! sudo apt install -y innoextract` → unlock DJI payload → expected 20-50+ real DJI BLE UUIDs.
2. Manual or operator-assisted acquisition for Dahua SmartPSS + 1 more Cohort C native (Avigilon ACC Client via Playwright form-driven flow) → calibration window closes for both cohorts.
