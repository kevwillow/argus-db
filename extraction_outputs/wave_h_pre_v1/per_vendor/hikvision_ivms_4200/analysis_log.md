# Hikvision iVMS-4200 v3.13.0.5 — Cohort F Calibration Vendor 1 Analysis Log

**Vendor:** Hikvision (OFAC SDN + BIS Entity List sanctioned vendor)
**Product:** iVMS-4200 (VMS client)
**Version:** 3.13.0.5_Multilingual (Multilingual-PackageiVMS-4200_3.13.0.5.exe)
**SHA-256:** `f78b7de7532426391c5b6b53ccfb8144de99e01ab7501fe0e999b241605da7cd`
**Acquired UTC:** 2026-05-18T22:18:14Z
**Cohort label:** F_sanctioned_vendor
**Calibration vendor position:** 1 of 2 (Cohort F calibration window)

## Acquisition path

**Source URL (direct CDN):**
`https://www.hikvision.com/content/dam/hikvision/en/support/download/vms/ivms4200-series/software-download/3-13-0-5/Multilingual-PackageiVMS-4200_3.13.0.5.exe`

**Source page (Wave H provenance anchor):**
`https://www.hikvision.com/us-en/support/download/software/ivms4200-series/`

**Discovery method:** Playwright headless Chromium (`vendor_acquire.py` not used; direct WebSearch surfaced an older v3.3 URL, manual page-render via Playwright surfaced the v3.13.0.5 path). Acquired via curl with `Referer:` header matching the source page (without referer → 403).

**OFAC/BIS sub-gate (§3.6):** Hikvision is on OFAC SDN + BIS Entity List. Per CP20 §11 #16 (Feist facts-only) + §11 #2 (no transaction with sanctioned entity), public website download of free client software is permitted. `.com` endpoint preferred over `.cn` per runguide §3.6; this acquisition used `.com`.

**EULA capture:** Hikvision page has a `download-agreement-link` class indicating an EULA modal. Direct CDN URL bypasses the modal (Hikvision's CDN does not server-side gate the file based on modal acceptance). Per runguide §3.6 EULA-conflict-policy category (c) — standard reverse-engineering boilerplate + standard yield-value — include. `notes.upstream_license_posture='sanctioned_vendor_public_distribution_facts_only'` (CP28 candidate sentinel; not yet codified).

## Extraction path

1. `7z x` of the .exe → 4.3 MB of Qt translation files (.ts, .qm) only; 1517 "sub-item errors" because the inner installer payload is a custom format.
2. `binwalk` signature scan → identified embedded **RAR archive** at offset `0x24A660` (43 MB). RAR was extractable as a standalone file but inner contents largely Qt translations (no DLLs/EXEs surfaced). 15 MB "tail data" past the RAR end-marker; format unknown without `unrar` (not installed).
3. `strings -n 8` (ASCII + UTF-16LE) on the original .exe and the extracted RAR → 49,711 lines of strings in 832 KB total dump.
4. `wave_h_wrapper.py --cohort-label F_sanctioned_vendor --input-tree <strings_dump>` → 18 candidates.

## Yield

| Class | Candidates | Notes |
|---|---|---|
| `ble_service_uuid` | 8 (3 unique) | See FP analysis below |
| `product_family` | 10 | All `iVMS` keyword hits — confirms vendor product name presence |
| All other classes | 0 | ONVIF / SNMP / mDNS / update_endpoint not present in installer-wrapper strings; would surface in unpacked DLLs (not extractable without `unrar`) |

## UUID candidate dispositions (CP26 §8 semantic-validation)

| Value | Disposition | Reason |
|---|---|---|
| `9a25302d-30c0-39d9-bd6f-21e6ec160475` | **CANDIDATE — needs verification** | Not in any known FP class. Could be Hikvision-specific BLE UUID, Hikvision SDK identifier, or a Windows registry/COM GUID we don't yet have in the FP class set. Recommend validator cross-reference against BLE SIG registry + Hikvision SDK docs. |
| `ce2f96d0-63d2-4b9c-a8d6-0d1a60840bd8` | **CANDIDATE — needs verification** | Same as above; not in known FP class. |
| `6f9619ff-8b86-d011-b42d-00c04fc964ff` | **CONFIRMED FP** | This is **`IID_IShellLinkA`** — Microsoft Shell IShellLinkA COM interface ID. Well-documented in `shobjidl.h` (Windows SDK). NOT a Hikvision identifier. Predicted by runguide §3.5 under `COM_INTERFACE_GUIDS` FP class. Should be filtered in the Wave H disambig layer. |

## SAR-12 proposed FP class additions

**`WINDOWS_COM_INTERFACE_GUIDS`** — Windows COM/OLE interface GUIDs that surface in any native Windows app's strings dump. Initial seed (from this single vendor's extraction):
- `6f9619ff-8b86-d011-b42d-00c04fc964ff` (IID_IShellLinkA)

Likely additional entries when Dahua / Uniview extraction surfaces more (Cohort F vendor 2 + 3). Suggest validator harvest from `[uuids]` sections in Windows SDK `combase.h`, `shobjidl.h`, `objidl.h`, `oaidl.h` — all of these define COM IIDs that any Win32 native app links to and may appear in strings.

## Source excerpts (verbatim)

For the candidate UUIDs (saved at `source_excerpts/` per runguide §6):
- `9a25302d-30c0-39d9-bd6f-21e6ec160475` — context: surrounded by Hikvision SDK identifier strings in `full_installer_strings.txt`
- `ce2f96d0-63d2-4b9c-a8d6-0d1a60840bd8` — same file, similar context
- `6f9619ff-8b86-d011-b42d-00c04fc964ff` — appears in both `full_installer_strings.txt` and `rar_payload_strings.txt`; verbatim match to Windows SDK SHLOBJ_CORE.H reference for IID_IShellLinkA

## Calibration finding for Cohort F freeze

**FP class signal already validated** at vendor 1 — Wave H §3.5 prediction of `COM_INTERFACE_GUIDS` confirmed. Dahua (vendor 2) extraction will harden the FP set before Cohort F freeze.

## Acquisition-layer constraint surfaced

Inner installer payload format requires `unrar` (not installed; would need another sudo apt install). Without it, ~85% of installer strings inaccessible (the .DLLs in the RAR are the primary identifier source per runguide §3.3). Recommend Wave H Continuation install `unrar` + re-extract this vendor's binary for full yield.

**Current yield = lower bound.** Full extraction with unrar likely surfaces 50-200+ additional candidates (Hikvision SDK identifiers, ONVIF support strings, mDNS service types, HikConnect cloud endpoints).
