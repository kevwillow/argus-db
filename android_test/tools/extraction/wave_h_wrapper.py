#!/usr/bin/env python3
"""
Wave H thin adapter over wave_g_extractor.py v4 (D3.a; v4 untouched).

Adapts the v4 candidate-walk regex layer (parser-agnostic per CP27 §3.0 P4) to
single-tree desktop input (Electron asar_out / .NET ilspycmd_out / native
strings_dump / firmware filesystem walk). Adds:
  - --input-tree (single decompiled-source tree path)
  - --cohort-label (A_electron / B_dotnet / C_native_cpp / D_drone_firmware_tooling
                    / E_firmware_images / F_sanctioned_vendor / G_adjacent_vms
                    / H_forensics_acoustic_drone_detection)
  - --product / --binary-sha256 (replace --package / --apk-sha256 for desktop)
  - 5 new Wave H identifier-class extractors per runguide §3.4:
      onvif_capability_string
      snmp_enterprise_oid
      mdns_service_type
      update_endpoint_url
    (network_protocol_magic_bytes deferred — requires a cross-reference pass
    rather than pure regex; runguide §3.4 acknowledges 70-85 sub-band w/ ≥2
    cross-refs requirement.)

The v4 regex layer is invoked by importing wave_g_extractor and passing the
single input_tree as jadx_out, with a non-existent path as apktool_out so
iter_candidate_files's `if not root.exists(): continue` silently skips it.
This yields each input_tree file exactly once with the input_tree as the
root for relative-path computation.

Discipline anchors (mirrored from v4):
  - §11 #1: every candidate carries source_file + source_line + source_excerpt.
  - §11 #7 / CP23: source_excerpt clipped to <=200 chars for identifiers tier.
  - §11 #8: NO database writes, NO promotion. JSON deliverables only.
  - CP24: cohort_label set on every candidate for cross-vendor-attestation
    bucketing at staging-aggregation time.

Usage:
  python3 wave_h_wrapper.py \\
    --input-tree /media/.../desktop_test/scratch/<vendor>/asar_out/ \\
    --vendor "Verkada" \\
    --product "command_connector" \\
    --version 1.2.3 \\
    --binary-sha256 <full-sha> \\
    --cohort-label A_electron \\
    --output-dir /home/.../desktop_test/extraction_outputs/wave_h_pre_v1/per_vendor/verkada/ \\
    [--vendor-prefix Verkada] \\
    [--product-family-keywords ...]
"""

import argparse
import datetime
import importlib.util
import json
import re
import sys
from pathlib import Path

WAVE_G_EXTRACTOR_PATH = Path(__file__).parent / 'wave_g_extractor.py'


# -------------------------- Wave H supplemental FP classes --------------------------
# SAR-12 calibration findings — Windows-platform-wide GUIDs that appear in
# every native Windows binary and are NOT vendor identifiers.

# Microsoft <supportedOS> application-manifest compatibility GUIDs (well-documented in MSDN).
# Every Windows installer embeds these for OS-compatibility declaration.
WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS = {
    'e2011457-1546-43c5-a5fe-008deee3d3f0',  # Windows Vista
    '35138b9a-5d96-4fbd-8e2d-a2440225f93a',  # Windows 7
    '4a2f28e3-53b9-4441-ba9c-d69d4a4a6e38',  # Windows 8
    '1f676c76-80e1-4239-95bb-83d0f6d0da78',  # Windows 8.1
    '8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a',  # Windows 10
}

# Windows COM/OLE interface IIDs that appear in any native Windows binary's
# strings dump because of standard COM library imports. Seeded from Hikvision
# iVMS-4200 v3.13.0.5 calibration; expected to grow.
WINDOWS_COM_INTERFACE_GUIDS = {
    '6f9619ff-8b86-d011-b42d-00c04fc964ff',  # IID_IShellLinkA (shobjidl.h)
}

# Windows SetupAPI device-class setup GUIDs. Every Windows binary that
# interacts with device enumeration (USB, HID, Net, etc.) embeds these.
# Seeded from DJI Assistant 2 Mavic + FPV calibration cross-product overlap.
WINDOWS_DEVCLASS_SETUP_GUIDS = {
    '36fc9e60-c465-11cf-8056-444553540000',  # GUID_DEVCLASS_USB
    '4d36e96c-e325-11ce-bfc1-08002be10318',  # GUID_DEVCLASS_MEDIA
    '4d36e96d-e325-11ce-bfc1-08002be10318',  # GUID_DEVCLASS_MODEM
    '4d36e972-e325-11ce-bfc1-08002be10318',  # GUID_DEVCLASS_NET
    '50dd5230-ba8a-11d1-bf5d-0000f805f530',  # GUID_DEVCLASS_HIDCLASS
    '6bdd1fc6-810f-11d0-bec7-08002be2092f',  # GUID_DEVCLASS_1394
    '745a17a0-74d3-11d0-b6fe-00a0c90f57da',  # GUID_DEVCLASS_IMAGE
    '7e667f5d-a661-495e-a512-f55686dda178',  # GUID_DEVCLASS_MTP
    'a5dcbf10-6530-11d2-901f-00c04fb951ed',  # GUID_DEVINTERFACE_USB_DEVICE
    'c77e7400-738a-11d2-9add-0020af0a3278',  # GUID_DEVCLASS_WCEUSBS
    'c15730e2-145c-4c5e-b005-3bc753f42475',  # GUID_BUS_TYPE_USB
}

# UUID-shaped ASCII strings caught by Pattern A regex but actually plaintext
# embedded in libraries (libusb-win32 in particular ships an ASCII identifier
# that hex-decodes to "libusb-win32-WDF").
LIBUSB_ASCII_IDENTIFIERS = {
    '6c696275-7362-2d77-696e-33322d574446',  # "libus-bs2d-wins-2-d-WDF"
}

# 3rd-party DLL file-path prefixes whose UUIDs are framework noise, not vendor
# identifiers. If a candidate's source_file_relative path starts with any of
# these, the candidate is filtered as `THIRD_PARTY_DLL_FRAMEWORK_NOISE`.
THIRD_PARTY_DLL_PATH_PREFIXES = (
    'qt5core.dll',
    'qt5network.dll',
    'qt5gui.dll',
    'qt5widgets.dll',
    'qt5quick.dll',
    'qt5qml.dll',
    'qt5xml.dll',
    'qt5svg.dll',
    'libcrypto-',
    'libssl-',
    'libeay32.dll',
    'ssleay32.dll',
    'msvcp',
    'msvcr',
    'vcruntime',
    'libusb0',
    'libusb-1.0',
    'd3dcompiler_',
    'libegl.dll',
    'libglesv2.dll',
    'sqlite3.dll',
    'icudt',
    'icuin',
    'icuuc',
    'iconv.dll',
    'libffi',
    'libxml2',
    'zlib.dll',
)

# SAR-12 codified post-Hikvision-CP26-§8-audit (session 2):
# context-substring patterns that, when present in source_excerpt, demote a UUID
# to the `windows_installer_productcode_in_msi_context` FP class. These match
# Windows Installer / InstallShield ProductCode and UpgradeCode GUID usage,
# which are vendor-registered identifiers BUT never BLE service UUIDs.
MSI_INSTALLER_CONTEXT_SUBSTRINGS = (
    r'\Uninstall\{',
    r'\uninstall\{',
    r'currentversion\uninstall',
    'CurrentVersion\\Uninstall',
    'Wow6432Node\\Microsoft\\Windows',
    'InstallShield Wizard',
    'InstallShield Installation',
    'Multilingual Package InstallShield',
    # Bare-bracket InstallShield/MSI GUID form: e.g. "\{CE2F96D0-...}" is a
    # strong MSI/InstallShield ProductCode signal (BLE UUIDs never appear in
    # backslash-leftbrace context). Catches stripped strings where the only
    # surviving context is the bracket delimiters.
    '\\{',
)

# Value-level propagation: any UUID that surfaces ONCE in MSI context is MSI
# at every occurrence. Populated at runtime from the first pass; consulted on
# the second pass via _stamp_value_level_msi_fps.
_RUNTIME_MSI_VALUE_SET: set[str] = set()

# Windows SxS Side-by-Side assembly publicKeyToken values (16-char hex).
# Wave H new FP class — extract_credentials regex catches these as credential-shaped.
WINDOWS_SXS_PUBLICKEYTOKEN = {
    '6595b64144ccf1df',  # Microsoft.Windows.Common-Controls
    'b03f5f7f11d50a3a',  # Microsoft public assemblies
    '31bf3856ad364e35',  # Microsoft .NET Framework default
}


def _is_wave_h_known_fp(value, value_class, source_file_relative='', source_excerpt=''):
    """Wave H-only FP filter (composes with v4 disambig).

    Inspects the value + source_file path + source_excerpt context. If the
    candidate is in any known FP set OR the source context matches a known
    framework / installer pattern, returns (fp_class, reason). Otherwise None.
    """
    if value_class == 'ble_service_uuid':
        v = value.lower()
        if v in WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS:
            return ('windows_supportedos_manifest_guid', f'Windows <supportedOS> compatibility manifest GUID ({v})')
        if v in WINDOWS_COM_INTERFACE_GUIDS:
            return ('windows_com_interface_guid', f'Windows COM/OLE interface IID ({v})')
        if v in WINDOWS_DEVCLASS_SETUP_GUIDS:
            return ('windows_devclass_setup_guid', f'Windows SetupAPI device-class setup GUID ({v})')
        if v in LIBUSB_ASCII_IDENTIFIERS:
            return ('libusb_ascii_identifier', f'libusb-win32 ASCII identifier embedded in UUID form ({v})')
        # SAR-12 session-2 calibration: MSI / InstallShield ProductCode in
        # Uninstall registry context. Vendor-registered, but NOT a BLE UUID.
        for marker in MSI_INSTALLER_CONTEXT_SUBSTRINGS:
            if marker in source_excerpt:
                return ('windows_installer_productcode_in_msi_context',
                        f'UUID surfaces in MSI/InstallShield installer context ({marker!r}); '
                        f'vendor-registered ProductCode/UpgradeCode, not a BLE service UUID')
    if value_class == 'credential':
        if value.lower() in WINDOWS_SXS_PUBLICKEYTOKEN:
            return ('windows_sxs_publickeytoken', f'Windows SxS assembly publicKeyToken ({value})')
    # 3rd-party DLL path-prefix filter — applies to ANY value_class.
    fn = source_file_relative.lower()
    leaf = fn.split('/')[-1] if '/' in fn else fn
    for prefix in THIRD_PARTY_DLL_PATH_PREFIXES:
        if prefix in leaf:
            return ('third_party_dll_framework_noise', f'Source file matches 3rd-party DLL framework prefix ({prefix}); not a vendor identifier')
    return None


def _load_v4():
    spec = importlib.util.spec_from_file_location('wave_g_extractor', WAVE_G_EXTRACTOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -------------------------- Wave H new patterns --------------------------

# ONVIF capability strings:
# - "Profile S", "Profile T", "Profile G", "Profile A", "Profile Q", "Profile M",
#   "Profile C" — ONVIF profile literals (https://www.onvif.org/profiles/)
# - ONVIF namespace URIs http://www.onvif.org/ver10/... / ver20/...
RE_ONVIF_PROFILE = re.compile(
    r'\bProfile\s+([STGAQMC])\b'
)
RE_ONVIF_NAMESPACE = re.compile(
    r'(http://www\.onvif\.org/ver\d{2}/[A-Za-z0-9/_.-]+)'
)

# SNMP enterprise OIDs: IANA-registered private enterprise tree
# .1.3.6.1.4.1.<enterprise_number>(.<subtree>)*
# Require enterprise_number not in well-known stdlib OIDs.
RE_SNMP_ENTERPRISE_OID = re.compile(
    r'\b(1\.3\.6\.1\.4\.1\.(\d+)(?:\.\d+){1,16})\b'
)

# mDNS / DNS-SD service types: _<service>._<proto>
# proto must be tcp or udp; service is alphanumeric + dash + underscore.
RE_MDNS_SERVICE_TYPE = re.compile(
    r'\b(_[a-z][a-z0-9_-]{2,40})\._(?:tcp|udp)\b'
)

# Update / OTA endpoint URLs: https?://host[/path] where the URL or
# surrounding line mentions update / upgrade / ota / firmware.
RE_URL_ANY = re.compile(
    r'(https?://[A-Za-z0-9._/?=&:%@#+~-]{6,400})'
)
UPDATE_CONTEXT_TOKENS = ('update', 'upgrade', 'ota', 'firmware', 'download',
                          'patch', 'release', 'autoupdate')


# -------------------------- Wave H extractors --------------------------

def _truncate_excerpt(line, v4):
    """Delegate to v4's truncate_excerpt for byte-perfect parity."""
    if hasattr(v4, 'truncate_excerpt'):
        return v4.truncate_excerpt(line)
    line = line.rstrip('\n')
    if len(line) <= 200:
        return line, False
    return line[:200], True


def extract_onvif(input_tree: Path, v4) -> tuple[list[dict], list[dict], int]:
    candidates, fps, overflow_dropped = [], [], 0
    seen = set()
    for root, path in v4.iter_candidate_files(input_tree):
        try:
            with path.open('r', encoding='utf-8', errors='replace') as fh:
                for lineno, line in enumerate(fh, start=1):
                    matches = []
                    for m in RE_ONVIF_PROFILE.finditer(line):
                        matches.append(('profile', m.group(0)))
                    for m in RE_ONVIF_NAMESPACE.finditer(line):
                        matches.append(('namespace', m.group(1)))
                    if not matches:
                        continue
                    excerpt, truncated = _truncate_excerpt(line, v4)
                    if truncated:
                        overflow_dropped += 1
                        continue
                    rel = str(path.relative_to(root))
                    for kind, val in matches:
                        key = (val, rel, lineno)
                        if key in seen:
                            continue
                        seen.add(key)
                        candidates.append({
                            'value_class': 'onvif_capability_string',
                            'value': val,
                            'subkind': kind,
                            'source_file_relative': rel,
                            'source_line': lineno,
                            'source_excerpt': excerpt,
                            'vendor_proximity_signals': [],
                        })
        except (OSError, UnicodeError):
            continue
    return candidates, fps, overflow_dropped


def extract_snmp_oids(input_tree: Path, v4) -> tuple[list[dict], list[dict], int]:
    candidates, fps, overflow_dropped = [], [], 0
    seen = set()
    for root, path in v4.iter_candidate_files(input_tree):
        try:
            with path.open('r', encoding='utf-8', errors='replace') as fh:
                for lineno, line in enumerate(fh, start=1):
                    for m in RE_SNMP_ENTERPRISE_OID.finditer(line):
                        val = m.group(1)
                        enterprise_num = int(m.group(2))
                        excerpt, truncated = _truncate_excerpt(line, v4)
                        if truncated:
                            overflow_dropped += 1
                            continue
                        rel = str(path.relative_to(root))
                        key = (val, rel, lineno)
                        if key in seen:
                            continue
                        seen.add(key)
                        candidates.append({
                            'value_class': 'snmp_enterprise_oid',
                            'value': val,
                            'enterprise_number': enterprise_num,
                            'source_file_relative': rel,
                            'source_line': lineno,
                            'source_excerpt': excerpt,
                            'vendor_proximity_signals': [],
                        })
        except (OSError, UnicodeError):
            continue
    return candidates, fps, overflow_dropped


def extract_mdns(input_tree: Path, v4) -> tuple[list[dict], list[dict], int]:
    candidates, fps, overflow_dropped = [], [], 0
    seen = set()
    for root, path in v4.iter_candidate_files(input_tree):
        try:
            with path.open('r', encoding='utf-8', errors='replace') as fh:
                for lineno, line in enumerate(fh, start=1):
                    for m in RE_MDNS_SERVICE_TYPE.finditer(line):
                        val = m.group(0)
                        excerpt, truncated = _truncate_excerpt(line, v4)
                        if truncated:
                            overflow_dropped += 1
                            continue
                        rel = str(path.relative_to(root))
                        key = (val, rel, lineno)
                        if key in seen:
                            continue
                        seen.add(key)
                        candidates.append({
                            'value_class': 'mdns_service_type',
                            'value': val,
                            'source_file_relative': rel,
                            'source_line': lineno,
                            'source_excerpt': excerpt,
                            'vendor_proximity_signals': [],
                        })
        except (OSError, UnicodeError):
            continue
    return candidates, fps, overflow_dropped


def extract_update_endpoints(input_tree: Path, v4) -> tuple[list[dict], list[dict], int]:
    candidates, fps, overflow_dropped = [], [], 0
    seen = set()
    for root, path in v4.iter_candidate_files(input_tree):
        try:
            with path.open('r', encoding='utf-8', errors='replace') as fh:
                for lineno, line in enumerate(fh, start=1):
                    line_lower = line.lower()
                    if not any(tok in line_lower for tok in UPDATE_CONTEXT_TOKENS):
                        continue
                    for m in RE_URL_ANY.finditer(line):
                        url = m.group(1).rstrip('\'",;)]}')
                        excerpt, truncated = _truncate_excerpt(line, v4)
                        if truncated:
                            overflow_dropped += 1
                            continue
                        rel = str(path.relative_to(root))
                        key = (url, rel, lineno)
                        if key in seen:
                            continue
                        seen.add(key)
                        candidates.append({
                            'value_class': 'update_endpoint_url',
                            'value': url,
                            'source_file_relative': rel,
                            'source_line': lineno,
                            'source_excerpt': excerpt,
                            'vendor_proximity_signals': [],
                        })
        except (OSError, UnicodeError):
            continue
    return candidates, fps, overflow_dropped


# -------------------------- Adapter for v4 patterns --------------------------

def _run_v4_patterns(input_tree, vendor_prefix, kw, v4):
    dummy = Path('/__nonexistent_apktool_out_path__')
    uuid_c, uuid_f, uuid_d = v4.extract_uuids(input_tree, dummy)
    ssid_c, ssid_f, ssid_d = v4.extract_ssids(input_tree, dummy, vendor_prefix)
    cred_c, cred_f, cred_d = v4.extract_credentials(input_tree, dummy)
    oui_c, oui_f, oui_d = v4.extract_oui(input_tree, dummy)
    fam_c, fam_f, fam_d = v4.extract_product_taxonomy(input_tree, dummy, kw)
    return {
        'uuid': (uuid_c, uuid_f, uuid_d),
        'ssid': (ssid_c, ssid_f, ssid_d),
        'cred': (cred_c, cred_f, cred_d),
        'oui':  (oui_c,  oui_f,  oui_d),
        'fam':  (fam_c,  fam_f,  fam_d),
    }


def _stamp_cohort(candidates, cohort_label):
    for c in candidates:
        c['cohort_label'] = cohort_label


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-tree', required=True, type=Path,
                        help='Single decompiled-source tree (asar_out/dotnet_out/strings_dump/fs_walk).')
    parser.add_argument('--vendor', required=True)
    parser.add_argument('--product', required=True,
                        help='Wave H product name (replaces --package).')
    parser.add_argument('--version', required=True)
    parser.add_argument('--binary-sha256', required=True,
                        help='Wave H binary SHA256 (replaces --apk-sha256).')
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--cohort-label', required=True,
                        choices=['A_electron', 'B_dotnet', 'C_native_cpp',
                                 'D_drone_firmware_tooling', 'E_firmware_images',
                                 'F_sanctioned_vendor', 'G_adjacent_vms',
                                 'H_forensics_acoustic_drone_detection'])
    parser.add_argument('--vendor-prefix', default=None)
    parser.add_argument('--product-family-keywords', nargs='*', default=None)
    args = parser.parse_args()

    if not args.input_tree.exists():
        print(f'ERROR: --input-tree {args.input_tree} does not exist', file=sys.stderr)
        return 2

    v4 = _load_v4()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

    # v4 patterns A-F (UUID, SSID, cred, OUI, taxonomy)
    v4_results = _run_v4_patterns(args.input_tree, args.vendor_prefix,
                                  args.product_family_keywords, v4)

    # Wave H new patterns
    onvif_c, onvif_f, onvif_d = extract_onvif(args.input_tree, v4)
    snmp_c,  snmp_f,  snmp_d  = extract_snmp_oids(args.input_tree, v4)
    mdns_c,  mdns_f,  mdns_d  = extract_mdns(args.input_tree, v4)
    upd_c,   upd_f,   upd_d   = extract_update_endpoints(args.input_tree, v4)

    all_cands = (
        v4_results['uuid'][0] + v4_results['ssid'][0] + v4_results['cred'][0] +
        v4_results['oui'][0]  + v4_results['fam'][0]  +
        onvif_c + snmp_c + mdns_c + upd_c
    )
    all_fps = (
        v4_results['uuid'][1] + v4_results['ssid'][1] + v4_results['cred'][1] +
        v4_results['oui'][1]  + v4_results['fam'][1]  +
        onvif_f + snmp_f + mdns_f + upd_f
    )
    overflow_total = (
        v4_results['uuid'][2] + v4_results['ssid'][2] + v4_results['cred'][2] +
        v4_results['oui'][2]  + v4_results['fam'][2]  +
        onvif_d + snmp_d + mdns_d + upd_d
    )

    # Wave H supplemental FP filter — applied BEFORE v4 propagate so that
    # the cross-site value-level FP propagation can carry these forward.
    wave_h_filtered_cands = []
    for c in all_cands:
        hit = _is_wave_h_known_fp(c['value'], c['value_class'],
                                  c.get('source_file_relative', ''),
                                  c.get('source_excerpt', ''))
        if hit:
            fp_class, reason = hit
            fp_finding = dict(c)
            fp_finding['fp_class'] = fp_class
            fp_finding['fp_reason'] = reason
            fp_finding['fp_filter'] = 'wave_h_supplemental'
            all_fps.append(fp_finding)
        else:
            wave_h_filtered_cands.append(c)
    all_cands = wave_h_filtered_cands

    # v4 helper: cross-site FP propagation + vendor-proximity annotation + IDs.
    all_cands, all_fps = v4.propagate_value_level_fps(all_cands, all_fps)
    v4.annotate_vendor_proximity(all_cands, args.product, args.vendor)
    v4.assign_candidate_ids(all_cands, args.vendor)
    _stamp_cohort(all_cands, args.cohort_label)
    _stamp_cohort(all_fps, args.cohort_label)

    finished = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

    candidates_doc = {
        'vendor': args.vendor,
        'binary_sha256': args.binary_sha256,
        'product': args.product,
        'version': args.version,
        'cohort_label': args.cohort_label,
        'extraction_timestamp_utc': started,
        'extraction_finished_utc': finished,
        'extractor': 'wave_h_wrapper.py over wave_g_extractor.py v4',
        'candidates': all_cands,
    }
    fps_doc = {
        'vendor': args.vendor,
        'binary_sha256': args.binary_sha256,
        'product': args.product,
        'version': args.version,
        'cohort_label': args.cohort_label,
        'extraction_timestamp_utc': started,
        'fp_findings': all_fps,
    }
    counts = {
        'extraction_started_utc': started,
        'extraction_finished_utc': finished,
        'cohort_label': args.cohort_label,
        'candidates_total': len(all_cands),
        'fp_findings_total': len(all_fps),
        'source_excerpt_overflow_dropped_total': overflow_total,
        'by_class': {
            'ble_service_uuid':           {'candidates': len(v4_results['uuid'][0]),  'fp_findings': len(v4_results['uuid'][1])},
            'ssid':                       {'candidates': len(v4_results['ssid'][0]),  'fp_findings': len(v4_results['ssid'][1])},
            'credential':                 {'candidates': len(v4_results['cred'][0]),  'fp_findings': len(v4_results['cred'][1])},
            'oui':                        {'candidates': len(v4_results['oui'][0]),   'fp_findings': len(v4_results['oui'][1])},
            'product_family':             {'candidates': len(v4_results['fam'][0]),   'fp_findings': len(v4_results['fam'][1])},
            'onvif_capability_string':    {'candidates': len(onvif_c),                'fp_findings': len(onvif_f)},
            'snmp_enterprise_oid':        {'candidates': len(snmp_c),                 'fp_findings': len(snmp_f)},
            'mdns_service_type':          {'candidates': len(mdns_c),                 'fp_findings': len(mdns_f)},
            'update_endpoint_url':        {'candidates': len(upd_c),                  'fp_findings': len(upd_f)},
        },
    }

    (args.output_dir / 'candidates.json').write_text(json.dumps(candidates_doc, indent=2))
    (args.output_dir / 'fp_findings.json').write_text(json.dumps(fps_doc, indent=2))
    (args.output_dir / 'extraction_counts.json').write_text(json.dumps(counts, indent=2))

    print(f'wave_h_wrapper: {args.vendor}/{args.product} {args.cohort_label} '
          f'-> {len(all_cands)} candidates, {len(all_fps)} fp_findings '
          f'(overflow_dropped={overflow_total})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
