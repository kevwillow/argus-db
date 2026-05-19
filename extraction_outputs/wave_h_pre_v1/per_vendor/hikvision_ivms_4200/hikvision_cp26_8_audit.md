# Hikvision iVMS-4200 v3.13.0.5 — CP26 §8 Semantic-Validation Audit

**Session:** wave_h_pre_v1 (continuation session 2)
**Audit date UTC:** 2026-05-18
**Audit scope:** session-1 surviving Hikvision BLE UUID candidates (2 unique values)
**Disposition:** **both re-class as `windows_installer_productcode_vendor_registered` (NOT genuine BLE)**

---

## Per-UUID disposition

### UUID 1 — `9a25302d-30c0-39d9-bd6f-21e6ec160475`

**Surrounding lines from `full_installer_strings.txt` (lines 1069-1078):**
```
1069: RARCloseArchive
1070: RARProcessFile
1071: RARReadHeaderEx
1072: RARReadHeader
1073: RARSetCallback
1074: SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{9A25302D-30C0-39D9-BD6F-21E6EC160475}
1075: SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{9A25302D-30C0-39D9-BD6F-21E6EC160475}
1076: vector<T> too long
1077: Disk Space Remaining  %2.2f GB
1078: license.rtf
```

**CP26 §8 disposition:** `windows_installer_productcode_vendor_registered`

This is the Windows Installer **ProductCode** for iVMS-4200 (main package). It surfaces as:
- `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{9A25302D-...}` (64-bit registry view)
- `HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{9A25302D-...}` (32-bit-on-64-bit registry view)

This is a **vendor-registered Hikvision identifier** (Hikvision controls this ProductCode), but it is **NOT a BLE service UUID**. The v4 Pattern A regex matched it on UUID shape alone; semantic context places it firmly in the MSI/InstallShield ProductCode class predicted by runguide §3.5 under `WIX_INSTALLER_GUIDS` (extended here to InstallShield, which uses the same Windows Installer ProductCode mechanism).

### UUID 2 — `ce2f96d0-63d2-4b9c-a8d6-0d1a60840bd8`

**Surrounding lines from `full_installer_strings.txt` (lines 1125-1135):**
```
1125: Tools Manager.exe
1126: vcredist_x86.exe
1127: Multilingual Package
1128: \Tools Manager.lnk
1129: uninstall.exe
1130: CE2F96D0-63D2-4B9C-A8D6-0D1A60840BD8
1131: \{CE2F96D0-63D2-4B9C-A8D6-0D1A60840BD8}
1132: Multilingual Package InstallShield Wizard
1133: Space Required  150MB
1134: Install Multilingual Package to
1135: Custom Installation  >
```

**CP26 §8 disposition:** `windows_installer_productcode_vendor_registered`

This is the Windows Installer ProductCode for the iVMS-4200 **Multilingual Package InstallShield Wizard** component. Same identifier class as UUID 1, but specifically scoped to the multilingual wizard sub-package rather than the main client. Surrounded by InstallShield-Wizard-class strings (`vcredist_x86.exe`, `uninstall.exe`, `Multilingual Package InstallShield Wizard`, `Install Multilingual Package to`, etc.).

Vendor-registered Hikvision identifier; NOT a BLE service UUID.

---

## Wrapper update — SAR-12 codification

Codified post-audit at `wave_h_wrapper.py` via the new `windows_installer_productcode_in_msi_context` FP class. The filter is context-substring-based (not value-based), matching any of:

```
\Uninstall\{
\uninstall\{
currentversion\uninstall
CurrentVersion\Uninstall
Wow6432Node\Microsoft\Windows
InstallShield Wizard
InstallShield Installation
Multilingual Package InstallShield
\{                                  <- strong InstallShield/MSI bracket signal
```

The `\{` substring is the strongest single-token signal — InstallShield/MSI ProductCode references always use this bracket form (`\{<UUID>}`), and the bracket-prefix with backslash is rarely if ever present in BLE-related code paths.

**Re-run validation post-codification:**
- Hikvision iVMS-4200: 0 surviving BLE UUID candidates (was 2 — both filtered as MSI ProductCode)
- DJI Mavic Assistant 2: 1 surviving BLE UUID (was 2 — the COM CLSID `054aae20-...` was also caught by the new `\{` substring match because its source line contained `Software\Classes\CLSID\{054AAE20-...}\LocalServer32`; correct disposition — COM CLSIDs are NOT BLE UUIDs either)
- DJI FPV Assistant 2: same as Mavic — 1 surviving UUID (`f4d4dbf5-...`)

**Only `f4d4dbf5-ba4b-40db-9a44-f8395f3728cf` survives the post-audit filter across all 3 Wave H binaries.** That UUID surfaces as a document-UUID component of `https://duss.djicorp.com/functional-document/f4d4dbf5-...` — a DJI corporate cloud-URL path. It is a vendor-registered DJI identifier but is also **not a BLE service UUID** — it's a document-identifier in a URL context. CP26 §8 re-class disposition: `vendor_document_uuid_cloud_reference` (already codified in `cross_vendor_attestations.json` from session 1).

---

## Cohort F empirical-anchor finding

**Cohort F (sanctioned-vendor) has zero net real BLE service UUIDs from Hikvision iVMS-4200 v3.13.0.5_Multilingual.** The vendor-specific identifiers surfaced (2 MSI ProductCodes) are valid Hikvision-registered identifiers, but they are MSI/InstallShield ProductCodes, not BLE service UUIDs.

**Impact on CP28 candidate (b) — `sanctioned_vendor_public_distribution_facts_only` license-posture sentinel:**

The sentinel was proposed in session 1 with the empirical anchor of "Hikvision iVMS-4200 acquisition surfaces real BLE UUIDs that benefit from the new posture sentinel." Post-CP26-§8 audit, that anchor evaporates — Hikvision iVMS-4200 surfaces zero genuine BLE UUIDs.

The sentinel may still be worth codifying for future Cohort F vendors (Dahua, Uniview) where the OFAC/BIS posture is a real downstream filter for Lynceus/Talos consumers — but the **empirical anchor in session 1+2 is the FACT that Hikvision distributes a multilingual installer publicly via .com (not .cn), and the EULA-posture + sanctioned-vendor sub-gate disposition was cleared per CP20 §11 #16**, not the identifier yield. That's still a useful empirical anchor for the sentinel — it tests the §3.6 sanctioned-vendor sub-gate workflow even though it doesn't yield BLE candidates.

**Cohort F operational finding:** the BLE/over-the-air protocol surface for Hikvision lives in the camera/NVR firmware images, not in the iVMS-4200 desktop client. The desktop client is for camera management; BLE pairing (where Hikvision uses it, e.g. for Hik-Connect mobile flows) happens elsewhere — in the Wave G mobile app or in firmware (Cohort E). Cohort F desktop yield is fundamentally limited by where in the vendor's software stack the BLE logic actually lives.

This extends and refines the **CP17 desktop-axis thesis bifurcation finding**: even within installer-cohort desktop binaries that DO retain rich UIs (Cohorts B/C/D/F), the **identifier surface is different from what mobile-axis Wave G surfaced**. Desktop binaries yield installer/registration identifiers (MSI ProductCode, COM CLSID, document UUIDs in cloud URLs); mobile binaries yield BLE protocol identifiers. The two axes are not just operator-vs-installer-cohort sliced — they're also **different identifier-class surfaces by execution model**.

---

## Updated counts

`per_vendor/hikvision_ivms_4200/candidates.json` + `fp_findings.json` regenerated post-filter:

| Metric | Pre-audit | Post-audit (this session) |
|---|---|---|
| Hikvision candidates_total | 14 | 10 |
| Hikvision fp_findings_total | 8 | 12 |
| Hikvision unique BLE UUID candidates | 2 | **0** |

Both Hikvision UUIDs migrated from `candidates.json` (ble_service_uuid class) to `fp_findings.json` (`windows_installer_productcode_in_msi_context` class).

`product_family` candidates for Hikvision (`iVMS`) remain at 10 unfiltered — these are not in scope for this CP26 §8 audit and remain as candidates per the runguide §3.4 product-family class definition.
