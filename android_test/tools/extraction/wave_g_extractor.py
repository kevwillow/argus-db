#!/usr/bin/env python3
"""
Wave G pre-v1 vendor companion APK identifier extractor.

Single-file Python module that:
  1. Walks jadx_out/ + apktool_out/ for a vendor.
  2. Applies extraction patterns A-F per WAVE_G_RUNBOOK.md §4.4.
  3. Applies disambiguation FP filters per §4.5.
  4. Emits candidates.json (post-disambig survivors) + fp_findings.json
     (everything caught by the FP filters, for SAR-11 calibration).
  5. Returns counts dict for inclusion in analysis_log.md.

Discipline anchors:
  - §11 #1: every candidate carries source_file + source_line + source_excerpt.
  - §11 #7: source_excerpt clipped to <=200 chars verbatim. Overflow drops with skip-log.
  - §11 #8: NO database writes, NO promotion. JSON deliverables only.

Usage:
  python3 wave_g_extractor.py \
    --jadx-out /tmp/wave_g_decompile.XXXX/jadx_out \
    --apktool-out /tmp/wave_g_decompile.XXXX/apktool_out \
    --vendor "Flock Safety" \
    --package com.flocksafety.sweetwater \
    --version 1.64.0 \
    --apk-sha256 <full-sha> \
    --output-dir /home/kev/argus/android_test/extraction_outputs/wave_g_pre_v1/per_vendor/flock_safety_<short>/ \
    [--vendor-prefix Flock] \
    [--product-family-keywords Falcon Talon Raven Sparrow]
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

# -------------------------- Pattern constants --------------------------

# Pattern A: full 128-bit BLE UUIDs.
RE_UUID_128 = re.compile(
    r'\b([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\b'
)

# Pattern B: 16-bit BLE service UUIDs in BLE-context lines. Match a short hex
# like 0xFD5A only when the same line mentions a BLE keyword.
RE_BLE_SHORT_UUID = re.compile(
    r'\b(?:ParcelUuid|BluetoothGatt|BluetoothGattService|BluetoothLeScanner|'
    r'ScanFilter|UUID\.fromString|GATT_SERVICE|GATT_CHAR)\b.*?'
    r'(0x[0-9a-fA-F]{4})\b',
    re.IGNORECASE,
)

# Pattern D: MAC OUI (xx:xx:xx) — too noisy alone; we keep only when context
# suggests a MAC validation (.startsWith / .equals / matches).
RE_OUI = re.compile(
    r'(?:startsWith|equals|matches|prefix|OUI|mac).*?'
    r'(["\']?(?:[0-9a-fA-F]{2}[:\-]){2}[0-9a-fA-F]{2}["\']?)',
    re.IGNORECASE,
)

# Pattern E: default credentials. Conservative: hardcoded literal next to
# password-like assignment.
RE_CRED = re.compile(
    r'(?:password|passwd|pwd|secret|token|api_?key|admin)\s*[:=]\s*'
    r'["\']([^"\']{4,80})["\']',
    re.IGNORECASE,
)

# -------------------------- FP filter constants --------------------------

# Standard Bluetooth SIG GATT services (template: xxxxxxxx-0000-1000-8000-00805f9b34fb).
# These are NEVER vendor-specific.
SIG_SUFFIX = '-0000-1000-8000-00805f9b34fb'
KNOWN_STANDARD_GATT = {
    '00001800', '00001801', '00001802', '00001803', '00001804', '00001805',
    '00001806', '00001807', '00001808', '00001809', '0000180a', '0000180d',
    '0000180e', '0000180f', '00001810', '00001811', '00001812', '00001813',
    '00001814', '00001815', '00001816', '00001818', '00001819', '0000181a',
    '0000181b', '0000181c', '0000181d', '0000181e', '0000181f', '00001820',
    '00001821', '00001822', '00001823', '00001824', '00001825', '00001826',
    '0000fe9f',  # Google
    '0000fd5a',  # Apple Find My
    '0000feaa',  # Eddystone (Google beacon)
    '0000fef3',  # Google Fast Pair
    '0000fe2c',  # Google
    '0000fe70',  # Google
    '0000fef4',  # Google
}

# SAR-11 calibration additions (post-Flock vendor 1 first-pass).
# These are exact-match UUIDs that surfaced as FPs in vendor 1 and warrant
# their own FP class names so Validator can codify them in the morning.
RFC6455_WEBSOCKET_GUID = {
    '258eafa5-e914-47da-95ca-c5ab0dc85b11',  # RFC 6455 WebSocket Accept GUID
}
# Android AudioEffect framework UUIDs — used by WebRtc / Android AudioEffect
# to identify built-in effects (NS, AGC, AEC, AINS, etc.). Never BLE.
ANDROID_AUDIOEFFECT_UUIDS = {
    'bb392ec0-8d4d-11e0-a896-0002a5d5c51b',  # Mobile Noise Suppression (NS)
    'c06c8400-8e06-11e0-9cb6-0002a5d5c51b',  # Mobile Acoustic Echo Canceler (AEC)
    'aa8130e0-66fc-11e0-bad0-0002a5d5c51b',  # Mobile Auto Gain Control (AGC)
    '7b491460-8d4d-11e0-bf6c-0002a5d5c51b',  # Other AudioEffect
}
# androidx.work WorkManager internal UUIDs (workspec IDs, etc.).
ANDROIDX_WORK_UUIDS = {
    '95ed6082-b8e9-46e8-a73f-ff56f00f5d9d',  # androidx.work Data placeholder
}

# Context tokens that indicate a UUID is a third-party SDK / build / config
# identifier rather than a BLE service UUID. If any of these appears in the
# same source line as a UUID match, drop the candidate as analytics/SDK noise.
ANALYTICS_SDK_CONTEXT_TOKENS = (
    'BUILD_ID', 'build_id',
    'APPLICATION_ID', 'application_id',
    'PROJECT_ID', 'project_id',
    'CLIENT_ID', 'client_id',
    'API_KEY', 'api_key', 'apiKey',
    'SDK_KEY', 'sdk_key', 'sdkKey',
    'APP_ID', 'app_id', 'appId',
    'DATADOG_', 'FULLSTORY_', 'LAUNCH_DARKLY_', 'LAUNCHDARKLY_',
    'AMPLITUDE_', 'MIXPANEL_', 'SEGMENT_', 'BUGSNAG_',
    'SENTRY_', 'INTERCOM_', 'PENDO_', 'AUTH0_',
    'FIREBASE_', 'CRASHLYTICS_', 'BRANCH_',
    'INSTANCE_ID', 'INSTALLATION_ID',
    'tracking_id', 'TRACKING_ID',
    'MAPBOX_TOKEN', 'mapboxToken',
    'CLIENT_TOKEN', 'clientToken',
    'TOKEN_ENDPOINT', 'tokenEndpoint',
    'GOOGLE_APP_ID', 'gcm_defaultSenderId',
)

# Apple framework UUIDs.
APPLE_UUIDS = {
    'd0611e78-bbb4-4591-a5f8-487910ae4366',  # Apple Continuity
    '9fa480e0-4967-4542-9390-d343dc5d04ae',  # Apple Notification Center
    '7905f431-b5ce-4e99-a40f-4b1e122d00d0',  # Apple ANCS
    '8667556c-9a37-4c91-84ed-54ee27d90049',  # Apple Continuity
}

# Third-party BLE library UUIDs that are NOT vendor-specific.
THIRD_PARTY_BLE_LIB = {
    '6e400001-b5a3-f393-e0a9-e50e24dcca9e',  # Nordic UART Service
    '6e400002-b5a3-f393-e0a9-e50e24dcca9e',  # Nordic UART RX
    '6e400003-b5a3-f393-e0a9-e50e24dcca9e',  # Nordic UART TX
    '0000ffe0-0000-1000-8000-00805f9b34fb',  # HM-10 / generic CC2541
    '0000ffe1-0000-1000-8000-00805f9b34fb',  # HM-10 char
    '0000ff00-0000-1000-8000-00805f9b34fb',  # Generic CC2540
    'f000aa00-0451-4000-b000-000000000000',  # TI SensorTag
    '0000fff0-0000-1000-8000-00805f9b34fb',  # Generic vendor-template (often library-default)
}

# RFC 4122 / SDK UUID examples — show up in random places, never BLE.
RFC4122_DUDS = {
    '00000000-0000-0000-0000-000000000000',
    '11111111-1111-1111-1111-111111111111',
    'ffffffff-ffff-ffff-ffff-ffffffffffff',
    '01010101-0101-0101-0101-010101010101',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
}

# Path patterns that mark a hit as test/build artifact (drop, log to FP).
PATH_FP_MARKERS = (
    '/test/', '/tests/', '/Test/', '__tests__',
    'BuildConfig.java', 'BuildConfig.kt',
    '/firebase/', '/crashlytics/', '/amplitude/',
    '/braze/', '/segment/', '/mixpanel/',
)

# Packages that ship their own BLE UUIDs but are not vendor surveillance gear.
THIRD_PARTY_LIB_PACKAGE_PREFIXES = (
    'com.google.', 'com.android.',
    'com.facebook.', 'com.amazon.',
    'io.sentry.', 'io.branch.',
    'androidx.', 'kotlinx.',
    'com.squareup.', 'okhttp3.', 'okio.',
    'retrofit2.', 'rx.', 'io.reactivex.',
    'org.bouncycastle.', 'org.spongycastle.',
    'com.crashlytics.', 'com.amplitude.',
    'com.appsflyer.', 'com.adjust.',
    'com.mixpanel.', 'com.segment.',
    'com.urbanairship.', 'com.airship.',
    'com.intercom.', 'io.intercom.', 'com.zendesk.',
    'com.datadog.', 'com.bugsnag.',
    'com.auth0.', 'com.fullstory.',
    'com.launchdarkly.', 'sdk.pendo.',
    'com.pendo.',
    'io.antmedia.', 'io.livekit.',
    'org.webrtc.', 'com.twilio.', 'io.agora.',
    'com.mapbox.', 'com.mparticle.',
    'android.gov.nist.', 'gov.nist.',
    'com.airbnb.lottie.',
    'androidx.compose.', 'androidx.work.',
    'com.transistorsoft.',  # cordova-background-geolocation + related
    'org.apache.cordova.',
    'com.cordova.',
    'org.crosswalk.',
)

# -------------------------- Helpers --------------------------

def short_hash(s: str, n: int = 10) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:n]


def truncate_excerpt(line: str, max_len: int = 200) -> tuple[str, bool]:
    """Return (excerpt, was_truncated). Per §11 #7, candidates with overflow
    are dropped; we record `was_truncated` so the caller can drop + skip-log."""
    line = line.rstrip('\n').rstrip('\r')
    if len(line) <= max_len:
        return line, False
    return line[:max_len], True


def looks_like_third_party_lib(rel_path: str) -> str | None:
    """If path lives under a known third-party SDK package, return the
    matching prefix; else None. Used as FP filter signal.

    Checks both jadx-style (sources/com/foo/...) and apktool smali-style
    (smali_classesN/com/foo/...) layouts, with or without leading slash.
    """
    p = rel_path.lower().replace('\\', '/')
    for prefix in THIRD_PARTY_LIB_PACKAGE_PREFIXES:
        path_form = prefix.replace('.', '/')
        # jadx layout: "sources/<pkg>/..."
        if f'sources/{path_form}' in p:
            return prefix
        # apktool smali layout: "smali_classes<N>/<pkg>/..." or "smali/<pkg>/..."
        if f'/{path_form}' in p:
            return prefix
        # Path STARTING with the package (rare but happens).
        if p.startswith(path_form):
            return prefix
        # Resource-side: livekit/ + tvo/ + similar bundled forks of webrtc
        # show up as "sources/livekit/org/webrtc/..." — caught by the
        # 'org/webrtc/' check below.
    return None


# Bundled forks of WebRTC / common library code that ship under non-standard
# top-level package names (LiveKit's vendored webrtc fork, Telecom-vision-org's
# 'tvo' fork, etc.). Treat as third-party leakage.
BUNDLED_FORK_MARKERS = (
    'sources/livekit/org/webrtc/',
    'sources/tvo/webrtc/',
    'sources/io/livekit/',
    'sources/org/webrtc/',
    'sources/com/twilio/',
    'sources/io/agora/',
)


def looks_like_bundled_fork(rel_path: str) -> str | None:
    p = rel_path.lower().replace('\\', '/')
    for marker in BUNDLED_FORK_MARKERS:
        if marker in p:
            return marker.rstrip('/').split('/')[-2] + '_bundled_fork'
    return None


def looks_like_test_or_build_artifact(rel_path: str) -> str | None:
    for marker in PATH_FP_MARKERS:
        if marker in rel_path:
            return marker
    return None


def classify_uuid_fp(uuid_lower: str) -> str | None:
    """Return FP class name if UUID matches a known FP class, else None."""
    if uuid_lower in RFC4122_DUDS:
        return 'rfc4122_placeholder_or_zeros'
    if uuid_lower.endswith(SIG_SUFFIX):
        prefix8 = uuid_lower[:8]
        if prefix8 in KNOWN_STANDARD_GATT:
            return 'bluetooth_sig_standard_gatt_service'
        # Any UUID matching the SIG template with an unknown prefix is also
        # almost-certainly-SIG-registered. Keep but mark as low-priority.
        return 'bluetooth_sig_template_unknown_prefix'
    if uuid_lower in APPLE_UUIDS:
        return 'apple_framework_uuid'
    if uuid_lower in THIRD_PARTY_BLE_LIB:
        return 'third_party_ble_library_uuid'
    if uuid_lower in RFC6455_WEBSOCKET_GUID:
        return 'rfc6455_websocket_accept_magic'
    if uuid_lower in ANDROID_AUDIOEFFECT_UUIDS:
        return 'android_audioeffect_framework_uuid'
    if uuid_lower in ANDROIDX_WORK_UUIDS:
        return 'androidx_work_workmanager_internal_uuid'
    return None


# -------------------------- Walker --------------------------

def iter_candidate_files(*roots: Path) -> Iterable[tuple[Path, Path]]:
    """Yield (root, file_path) pairs for every file we should grep through."""
    skip_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp',
                       '.ico', '.svg', '.ttf', '.otf', '.woff', '.woff2',
                       '.mp3', '.mp4', '.m4a', '.ogg', '.wav', '.webm',
                       '.zip', '.jar', '.dex', '.so', '.bin', '.dat',
                       '.pdf', '.lottie'}
    skip_names = {'R.java', 'BuildConfig.java'}  # noisy resource refs / build constants
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob('*'):
            if not path.is_file():
                continue
            if path.suffix.lower() in skip_extensions:
                continue
            if path.name in skip_names:
                continue
            try:
                if path.stat().st_size > 5 * 1024 * 1024:  # skip files >5 MiB
                    continue
            except OSError:
                continue
            yield root, path


# -------------------------- Extraction --------------------------

def extract_uuids(jadx_out: Path, apktool_out: Path) -> tuple[list[dict], list[dict], int]:
    """Pattern A. Returns (candidates, fp_findings, source_excerpt_overflow_dropped)."""
    candidates = []
    fp_findings = []
    overflow_dropped = 0
    seen_value_path = set()
    for root, path in iter_candidate_files(jadx_out, apktool_out):
        try:
            with path.open('r', encoding='utf-8', errors='replace') as fh:
                for lineno, line in enumerate(fh, start=1):
                    for match in RE_UUID_128.finditer(line):
                        uuid = match.group(1).lower()
                        rel = str(path.relative_to(root))
                        excerpt, truncated = truncate_excerpt(line)
                        if truncated:
                            overflow_dropped += 1
                            continue
                        # Build the dedup key on (uuid, file:line) so we
                        # capture each distinct call-site once.
                        key = (uuid, rel, lineno)
                        if key in seen_value_path:
                            continue
                        seen_value_path.add(key)
                        record_base = {
                            'value': uuid,
                            'value_class': 'ble_service_uuid',
                            'source_root': root.name,
                            'source_file_relative': rel,
                            'source_line': lineno,
                            'source_excerpt': excerpt,
                        }
                        # FP classification.
                        fp_class = classify_uuid_fp(uuid)
                        third_party = looks_like_third_party_lib(rel)
                        bundled_fork = looks_like_bundled_fork(rel)
                        path_artifact = looks_like_test_or_build_artifact(rel)
                        # Analytics-SDK context drop: if line OR FILENAME
                        # contains an SDK/build/config token (BUILD_ID,
                        # APPLICATION_ID, API_KEY, LAUNCH_DARKLY_KEY,
                        # datadog.buildId, etc.), drop as analytics noise
                        # rather than treating as BLE.
                        analytics_token = None
                        for tok in ANALYTICS_SDK_CONTEXT_TOKENS:
                            if tok in line:
                                analytics_token = tok
                                break
                        if not analytics_token:
                            # Also check the file path/name. Some assets
                            # are single-line UUID files where the token
                            # appears only in the filename:
                            #   resources/assets/datadog.buildId
                            #   resources/assets/sentry.dsn
                            rel_lower = rel.lower()
                            for tok in ('buildid', 'build_id', '.dsn',
                                        '.appid', '.app_id', 'fullstory',
                                        'datadog', 'launchdarkly',
                                        'sentry', 'mixpanel', 'amplitude',
                                        'pendo', 'intercom', 'auth0',
                                        'mapbox'):
                                if tok in rel_lower:
                                    analytics_token = f'filename:{tok}'
                                    break
                        if fp_class or third_party or bundled_fork or path_artifact or analytics_token:
                            fp_record = dict(record_base)
                            if fp_class:
                                fp_record['fp_class'] = fp_class
                            elif analytics_token:
                                fp_record['fp_class'] = f'third_party_analytics_sdk_application_id:{analytics_token}'
                            elif bundled_fork:
                                fp_record['fp_class'] = f'bundled_fork:{bundled_fork}'
                            elif third_party:
                                fp_record['fp_class'] = f'third_party_lib:{third_party}'
                            else:
                                fp_record['fp_class'] = f'path_artifact:{path_artifact}'
                            fp_findings.append(fp_record)
                            continue
                        # Survives disambig — stage as candidate.
                        cand = dict(record_base)
                        cand['proposed_confidence_band'] = '80-95'
                        cand['fp_filters_applied'] = [
                            'standard_gatt_drop',
                            'apple_framework_drop',
                            'third_party_ble_lib_drop',
                            'rfc4122_placeholder_drop',
                            'rfc6455_websocket_guid_drop',
                            'android_audioeffect_uuid_drop',
                            'androidx_work_internal_uuid_drop',
                            'third_party_sdk_path_drop',
                            'bundled_fork_path_drop',
                            'test_or_build_artifact_drop',
                        ]
                        cand['vendor_proximity_signals'] = []
                        candidates.append(cand)
        except Exception as exc:
            # Quietly skip unreadable files; record one diagnostic at the end.
            sys.stderr.write(f'SKIP {path}: {exc}\n')
    return candidates, fp_findings, overflow_dropped


DECOMPILER_CONCAT_ARTIFACT_RE = re.compile(
    r"^\s*\+\s|"           # leading "+ " — typical of `"foo" + var + "bar"` decomp output
    r"\s+\+\s*$|"          # trailing " +"
    r"^\s*\+\s*this\.|"    # "+ this.foo" inside the value
    r"\s\+\s\w+\s\+\s|"    # " + identifier + " inside the value
    r"^\$\{|^\#\{"         # template-literal placeholder
)
# Constant-key names that look like credentials but are SharedPreferences /
# JSON / header keys. These are field names, not credential VALUES.
CRED_KEY_NAME_RE = re.compile(
    r'^[A-Za-z][A-Za-z0-9]*(?:[._-][A-Za-z][A-Za-z0-9]*)*$'
)
# Library namespace constants — values prefixed with com.X.Y or similar.
LIBRARY_NAMESPACE_PREFIXES = (
    'com.google.', 'com.android.', 'com.auth0.',
    'com.facebook.', 'com.amazon.', 'com.flocksafety.',
    'com.shotspotter.', 'com.dji.', 'com.skydio.',
    'com.axon.', 'com.motorolasolutions.', 'com.brinc.',
    'com.parrot.', 'com.autel.', 'com.cradlepoint.',
    'com.sierrawireless.', 'com.hak5.', 'com.genetec.',
    'com.avigilon.', 'com.rekor.', 'com.vigilantsolutions.',
    'androidx.', 'org.', 'io.', 'sdk.',
)


def extract_credentials(jadx_out: Path, apktool_out: Path) -> tuple[list[dict], list[dict], int]:
    candidates = []
    fp_findings = []
    overflow_dropped = 0
    seen = set()
    # Common library/test FP values to drop at the credential layer.
    cred_value_fp = {
        'password', 'admin', 'changeme', 'test', 'example',
        '12345', '123456', 'qwerty', 'replace_me', 'your-password-here',
        '<password>', '${password}', 'newpassword', 'oldpassword',
    }
    for root, path in iter_candidate_files(jadx_out, apktool_out):
        try:
            with path.open('r', encoding='utf-8', errors='replace') as fh:
                for lineno, line in enumerate(fh, start=1):
                    for match in RE_CRED.finditer(line):
                        value = match.group(1)
                        rel = str(path.relative_to(root))
                        excerpt, truncated = truncate_excerpt(line)
                        if truncated:
                            overflow_dropped += 1
                            continue
                        key = (value, rel, lineno)
                        if key in seen:
                            continue
                        seen.add(key)
                        record_base = {
                            'value': value,
                            'value_class': 'credential',
                            'source_root': root.name,
                            'source_file_relative': rel,
                            'source_line': lineno,
                            'source_excerpt': excerpt,
                        }
                        third_party = looks_like_third_party_lib(rel)
                        bundled_fork = looks_like_bundled_fork(rel)
                        path_artifact = looks_like_test_or_build_artifact(rel)
                        # Drop decompiler concat artifacts: strings like
                        # "+ this.token +", "+ var +" — these are byproducts
                        # of decompilation, not real credentials.
                        if DECOMPILER_CONCAT_ARTIFACT_RE.search(value):
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = 'decompiler_string_concat_artifact'
                            fp_findings.append(fp_record)
                            continue
                        # Drop obvious placeholder values.
                        if value.lower() in cred_value_fp:
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = 'placeholder_credential_value'
                            fp_findings.append(fp_record)
                            continue
                        # Drop library namespace constants.
                        if any(value.lower().startswith(p) for p in LIBRARY_NAMESPACE_PREFIXES):
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = 'library_namespace_constant'
                            fp_findings.append(fp_record)
                            continue
                        # Drop SharedPreferences / JSON / header KEY NAMES.
                        # Heuristic A: short identifier-like value matched on
                        # field declaration / preference key context.
                        if (len(value) <= 40
                            and ' ' not in value
                            and CRED_KEY_NAME_RE.match(value)
                            and not re.search(r'[^A-Za-z0-9._-]', value)
                            and re.search(
                                r'(KEY|key|getString|putString|name|FIELD|HEADER|"key"|@SerializedName|@JsonProperty|EXTRA_)',
                                line,
                            )
                        ):
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = 'shared_preferences_or_json_key_name'
                            fp_findings.append(fp_record)
                            continue
                        # Heuristic B: SCREAMING_SNAKE_CASE constant
                        # declaration where the variable name equals the
                        # string literal (Java idiom for SharedPreferences
                        # / JSON key constants):
                        #   final String FOO_BAR = "FOO_BAR";
                        #   final String FOO_BAR = "foo_bar";
                        screaming_decl = re.search(
                            r'(?:static\s+final\s+String|val\s+|const\s+val\s+)\s+([A-Z][A-Z0-9_]{3,})\s*[:=]',
                            line,
                        )
                        if screaming_decl and (
                            value == screaming_decl.group(1)
                            or value.upper().replace('-', '_') == screaming_decl.group(1)
                            or value.lower() == screaming_decl.group(1).lower()
                        ):
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = 'screaming_snake_case_constant_name'
                            fp_findings.append(fp_record)
                            continue
                        # Heuristic C: standalone SCREAMING_SNAKE_CASE
                        # value (>= 8 chars, all uppercase + digits + _,
                        # underscored). Almost always a constant/key, not
                        # a credential.
                        if (re.fullmatch(r'[A-Z][A-Z0-9_]{7,}', value)
                            and '_' in value):
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = 'screaming_snake_case_constant_value'
                            fp_findings.append(fp_record)
                            continue
                        if third_party or bundled_fork or path_artifact:
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = (
                                f'bundled_fork:{bundled_fork}' if bundled_fork
                                else (f'third_party_lib:{third_party}' if third_party
                                      else f'path_artifact:{path_artifact}')
                            )
                            fp_findings.append(fp_record)
                            continue
                        cand = dict(record_base)
                        cand['proposed_confidence_band'] = '60-80'
                        cand['fp_filters_applied'] = [
                            'placeholder_value_drop',
                            'decompiler_concat_artifact_drop',
                            'library_namespace_constant_drop',
                            'shared_prefs_key_name_drop',
                            'third_party_sdk_path_drop',
                            'bundled_fork_path_drop',
                            'test_or_build_artifact_drop',
                        ]
                        cand['vendor_proximity_signals'] = []
                        candidates.append(cand)
        except Exception:
            pass
    return candidates, fp_findings, overflow_dropped


SSID_WIFI_CONTEXT_RE = re.compile(
    r'\b(SSID|ssid|WifiConfiguration|WifiManager|WifiNetworkSpecifier|'
    r'WifiNetworkSuggestion|ScanResult|WiFi|wifi|Wifi|setSsid|'
    r'getSsid|networkPrefix|\.ssid|"ssid")\b'
)
# Compose composable function names + Kotlin/Java identifier shapes that
# match SSID prefix but are NOT WiFi names. Heuristic: pure-CamelCase token
# with no separator (no `-`, no `_`, no space) and ends with common UI
# / framework suffixes.
COMPOSABLE_SUFFIXES = (
    'card', 'cardcontent', 'screen', 'detail', 'overview', 'container',
    'snackbar', 'chip', 'toolbar', 'action', 'icon', 'preview',
    'content', 'hit', 'pushhit', 'alertcard', 'alerttypemap',
    'alertdetail', 'alertoverview', 'alertcontent', 'preparedalertcard',
    'alertcardinfo', 'alertcardgovworxpreview', 'darkblue', 'darkgreen',
    'green', 'greenbright', 'greentransparent', 'snackbarcontent',
    'filterchip', 'filterchipdownarrow', 'floatingtoolbar',
    'floatingtoolbarcontent', 'floatingtoolbaraction',
    'floatingtoolbaractionicon', 'floatingtoolbarprimaryaction',
    'theme', 'colors', 'shapes', 'typography',
)
COMPOSE_KEYWORDS_RE = re.compile(
    r'\b(Composable|@Composable|fun [A-Z]|androidx\.compose|'
    r'ComposableLambda|composableLambda|Modifier|MaterialTheme|'
    r'Color\(|Brush\.|Shape|TextStyle|Density|LocalContent|'
    r'rememberSaveable|stringResource|painterResource)\b'
)


def extract_ssids(jadx_out: Path, apktool_out: Path, vendor_prefix: str | None) -> tuple[list[dict], list[dict], int]:
    if not vendor_prefix:
        return [], [], 0
    # Match "<Prefix>-XXXX" or "<Prefix>_XXXX" or "<Prefix>XXXX" SSID patterns.
    pattern = re.compile(
        rf'["\']({re.escape(vendor_prefix)}[-_ ]?[A-Za-z0-9_-]{{2,32}})["\']'
    )
    candidates = []
    fp_findings = []
    overflow_dropped = 0
    seen = set()
    for root, path in iter_candidate_files(jadx_out, apktool_out):
        try:
            with path.open('r', encoding='utf-8', errors='replace') as fh:
                for lineno, line in enumerate(fh, start=1):
                    for match in pattern.finditer(line):
                        value = match.group(1)
                        rel = str(path.relative_to(root))
                        excerpt, truncated = truncate_excerpt(line)
                        if truncated:
                            overflow_dropped += 1
                            continue
                        key = (value, rel, lineno)
                        if key in seen:
                            continue
                        seen.add(key)
                        record_base = {
                            'value': value,
                            'value_class': 'ssid',
                            'source_root': root.name,
                            'source_file_relative': rel,
                            'source_line': lineno,
                            'source_excerpt': excerpt,
                        }
                        # Common path-based FPs.
                        third_party = looks_like_third_party_lib(rel)
                        bundled_fork = looks_like_bundled_fork(rel)
                        path_artifact = looks_like_test_or_build_artifact(rel)
                        # Drop class-name lookalikes (e.g., FlockMainActivity).
                        if value.lower().endswith(('activity', 'fragment',
                                                   'service', 'controller',
                                                   'manager', 'helper',
                                                   'state', 'event',
                                                   'screen', 'theme')):
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = 'class_name_lookalike'
                            fp_findings.append(fp_record)
                            continue
                        # Compose composable name pattern: pure-CamelCase
                        # identifier (no separator) that ends with a known UI
                        # suffix OR appears in a line with Compose keywords.
                        is_camelcase_no_sep = (
                            re.fullmatch(r'[A-Za-z][A-Za-z0-9]+', value)
                            is not None
                        )
                        if is_camelcase_no_sep and (
                            value.lower().endswith(COMPOSABLE_SUFFIXES)
                            or COMPOSE_KEYWORDS_RE.search(line)
                            or rel.endswith('.smali')
                            or '/smali_classes' in rel
                            or '/res/values/' in rel  # XML resource keys
                        ):
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = 'kotlin_compose_composable_or_identifier_name'
                            fp_findings.append(fp_record)
                            continue
                        # Require WiFi-context keyword in the same line for
                        # the candidate to survive (genuine SSIDs almost
                        # always appear next to WifiConfiguration / SSID api).
                        if not SSID_WIFI_CONTEXT_RE.search(line):
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = 'no_wifi_api_context_in_line'
                            fp_findings.append(fp_record)
                            continue
                        if third_party or bundled_fork or path_artifact:
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = (
                                f'bundled_fork:{bundled_fork}' if bundled_fork
                                else (f'third_party_lib:{third_party}' if third_party
                                      else f'path_artifact:{path_artifact}')
                            )
                            fp_findings.append(fp_record)
                            continue
                        cand = dict(record_base)
                        cand['proposed_confidence_band'] = '70-85'
                        cand['fp_filters_applied'] = [
                            'class_name_lookalike_drop',
                            'kotlin_compose_composable_drop',
                            'wifi_api_context_required',
                            'third_party_sdk_path_drop',
                            'bundled_fork_path_drop',
                            'test_or_build_artifact_drop',
                        ]
                        cand['vendor_proximity_signals'] = []
                        candidates.append(cand)
        except Exception:
            pass
    return candidates, fp_findings, overflow_dropped


def extract_oui(jadx_out: Path, apktool_out: Path) -> tuple[list[dict], list[dict], int]:
    candidates = []
    fp_findings = []
    overflow_dropped = 0
    seen = set()
    for root, path in iter_candidate_files(jadx_out, apktool_out):
        try:
            with path.open('r', encoding='utf-8', errors='replace') as fh:
                for lineno, line in enumerate(fh, start=1):
                    for match in RE_OUI.finditer(line):
                        raw = match.group(1).strip('"\'')
                        # Normalize to xx:xx:xx lowercase
                        normalized = raw.lower().replace('-', ':')
                        if not re.fullmatch(r'[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}', normalized):
                            continue
                        rel = str(path.relative_to(root))
                        excerpt, truncated = truncate_excerpt(line)
                        if truncated:
                            overflow_dropped += 1
                            continue
                        key = (normalized, rel, lineno)
                        if key in seen:
                            continue
                        seen.add(key)
                        record_base = {
                            'value': normalized,
                            'value_class': 'oui',
                            'source_root': root.name,
                            'source_file_relative': rel,
                            'source_line': lineno,
                            'source_excerpt': excerpt,
                        }
                        third_party = looks_like_third_party_lib(rel)
                        bundled_fork = looks_like_bundled_fork(rel)
                        path_artifact = looks_like_test_or_build_artifact(rel)
                        if third_party or bundled_fork or path_artifact:
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = (
                                f'bundled_fork:{bundled_fork}' if bundled_fork
                                else (f'third_party_lib:{third_party}' if third_party
                                      else f'path_artifact:{path_artifact}')
                            )
                            fp_findings.append(fp_record)
                            continue
                        cand = dict(record_base)
                        cand['proposed_confidence_band'] = '75-90'
                        cand['fp_filters_applied'] = [
                            'third_party_sdk_path_drop',
                            'bundled_fork_path_drop',
                            'test_or_build_artifact_drop',
                            'requires_validation_keyword_context',
                        ]
                        cand['vendor_proximity_signals'] = []
                        candidates.append(cand)
        except Exception:
            pass
    return candidates, fp_findings, overflow_dropped


def extract_product_taxonomy(
    jadx_out: Path,
    apktool_out: Path,
    keywords: list[str] | None,
) -> tuple[list[dict], list[dict], int]:
    if not keywords:
        return [], [], 0
    pattern = re.compile(r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b')
    candidates = []
    fp_findings = []
    overflow_dropped = 0
    seen = set()
    for root, path in iter_candidate_files(jadx_out, apktool_out):
        try:
            with path.open('r', encoding='utf-8', errors='replace') as fh:
                for lineno, line in enumerate(fh, start=1):
                    for match in pattern.finditer(line):
                        value = match.group(1)
                        rel = str(path.relative_to(root))
                        excerpt, truncated = truncate_excerpt(line)
                        if truncated:
                            overflow_dropped += 1
                            continue
                        key = (value, rel, lineno)
                        if key in seen:
                            continue
                        seen.add(key)
                        record_base = {
                            'value': value,
                            'value_class': 'product_family',
                            'source_root': root.name,
                            'source_file_relative': rel,
                            'source_line': lineno,
                            'source_excerpt': excerpt,
                        }
                        third_party = looks_like_third_party_lib(rel)
                        bundled_fork = looks_like_bundled_fork(rel)
                        path_artifact = looks_like_test_or_build_artifact(rel)
                        if third_party or bundled_fork or path_artifact:
                            fp_record = dict(record_base)
                            fp_record['fp_class'] = (
                                f'bundled_fork:{bundled_fork}' if bundled_fork
                                else (f'third_party_lib:{third_party}' if third_party
                                      else f'path_artifact:{path_artifact}')
                            )
                            fp_findings.append(fp_record)
                            continue
                        cand = dict(record_base)
                        cand['proposed_confidence_band'] = '90-95'
                        cand['fp_filters_applied'] = [
                            'third_party_sdk_path_drop',
                            'bundled_fork_path_drop',
                            'test_or_build_artifact_drop',
                        ]
                        cand['vendor_proximity_signals'] = []
                        candidates.append(cand)
        except Exception:
            pass
    return candidates, fp_findings, overflow_dropped


# -------------------------- Main --------------------------

def annotate_vendor_proximity(cands: list[dict], package: str, vendor: str) -> None:
    """Decorate each candidate with vendor_proximity_signals deduced from the
    file path. Helps Validator triage in the morning."""
    pkg_path = '/' + package.replace('.', '/') + '/'
    vendor_token = vendor.lower().split()[0]
    for c in cands:
        signals = c['vendor_proximity_signals']
        rel = c['source_file_relative'].lower()
        if pkg_path in c['source_file_relative']:
            signals.append('vendor_package_path')
        if vendor_token in rel:
            signals.append('vendor_token_in_path')


def propagate_value_level_fps(
    cands: list[dict],
    fps: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Cross-site FP propagation. If a (value_class, value) pair has been
    classified FP at *any* site, demote all candidates with the same pair to
    FP. Reason: a UUID cannot simultaneously be a Datadog application ID and
    a BLE service UUID; if any site flags it as analytics, the same value at
    a different call-site is the same identifier.

    Returns (surviving_cands, expanded_fps).
    """
    fp_value_keys = {(f['value_class'], f['value']): f['fp_class'] for f in fps}
    survivors = []
    promoted_fps = list(fps)
    for c in cands:
        key = (c['value_class'], c['value'])
        if key in fp_value_keys:
            fp_record = dict(c)
            fp_record['fp_class'] = (
                f'value_level_propagated:{fp_value_keys[key]}'
            )
            promoted_fps.append(fp_record)
        else:
            survivors.append(c)
    return survivors, promoted_fps


def assign_candidate_ids(cands: list[dict], vendor: str) -> None:
    vendor_slug = re.sub(r'[^a-z0-9]+', '_', vendor.lower()).strip('_')
    for c in cands:
        c['candidate_id'] = (
            f"{vendor_slug}_{c['value_class']}_"
            f"{short_hash(c['value'] + c['source_file_relative'] + str(c['source_line']))}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--jadx-out', required=True, type=Path)
    parser.add_argument('--apktool-out', required=True, type=Path)
    parser.add_argument('--vendor', required=True)
    parser.add_argument('--package', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--apk-sha256', required=True)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--vendor-prefix', default=None,
                        help='SSID prefix for pattern C (e.g., Flock, Axon)')
    parser.add_argument('--product-family-keywords', nargs='*', default=None,
                        help='Pattern F keywords (e.g., Falcon Talon Raven)')
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

    uuid_cands, uuid_fps, uuid_dropped = extract_uuids(args.jadx_out, args.apktool_out)
    ssid_cands, ssid_fps, ssid_dropped = extract_ssids(args.jadx_out, args.apktool_out, args.vendor_prefix)
    cred_cands, cred_fps, cred_dropped = extract_credentials(args.jadx_out, args.apktool_out)
    oui_cands, oui_fps, oui_dropped = extract_oui(args.jadx_out, args.apktool_out)
    fam_cands, fam_fps, fam_dropped = extract_product_taxonomy(
        args.jadx_out, args.apktool_out, args.product_family_keywords)

    all_cands = uuid_cands + ssid_cands + cred_cands + oui_cands + fam_cands
    all_fps = uuid_fps + ssid_fps + cred_fps + oui_fps + fam_fps
    # Cross-site FP propagation: a value flagged FP at any site is FP everywhere.
    all_cands, all_fps = propagate_value_level_fps(all_cands, all_fps)
    annotate_vendor_proximity(all_cands, args.package, args.vendor)
    assign_candidate_ids(all_cands, args.vendor)

    finished = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

    candidates_doc = {
        'vendor': args.vendor,
        'apk_sha256': args.apk_sha256,
        'apk_package': args.package,
        'apk_version': args.version,
        'extraction_timestamp_utc': started,
        'extraction_finished_utc': finished,
        'candidates': all_cands,
    }
    fps_doc = {
        'vendor': args.vendor,
        'apk_sha256': args.apk_sha256,
        'apk_package': args.package,
        'apk_version': args.version,
        'extraction_timestamp_utc': started,
        'fp_findings': all_fps,
    }
    counts = {
        'extraction_started_utc': started,
        'extraction_finished_utc': finished,
        'candidates_total': len(all_cands),
        'fp_findings_total': len(all_fps),
        'source_excerpt_overflow_dropped_total': (
            uuid_dropped + ssid_dropped + cred_dropped + oui_dropped + fam_dropped
        ),
        'by_class': {
            'ble_service_uuid': {
                'candidates': len(uuid_cands),
                'fp_findings': len(uuid_fps),
                'overflow_dropped': uuid_dropped,
            },
            'ssid': {
                'candidates': len(ssid_cands),
                'fp_findings': len(ssid_fps),
                'overflow_dropped': ssid_dropped,
            },
            'credential': {
                'candidates': len(cred_cands),
                'fp_findings': len(cred_fps),
                'overflow_dropped': cred_dropped,
            },
            'oui': {
                'candidates': len(oui_cands),
                'fp_findings': len(oui_fps),
                'overflow_dropped': oui_dropped,
            },
            'product_family': {
                'candidates': len(fam_cands),
                'fp_findings': len(fam_fps),
                'overflow_dropped': fam_dropped,
            },
        },
    }

    (args.output_dir / 'candidates.json').write_text(
        json.dumps(candidates_doc, indent=2))
    (args.output_dir / 'fp_findings.json').write_text(
        json.dumps(fps_doc, indent=2))
    (args.output_dir / 'extraction_counts.json').write_text(
        json.dumps(counts, indent=2))

    print(json.dumps(counts, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
