#!/usr/bin/env python3
"""MAC-178 Priority 6 — SAR-11 19 FP-class adds to canonical registry.

Bake 19 SAR-11 FP-class proposals from MAC-104 + 104b + 104d into the
canonical `android_test/extraction_outputs/wave_g_pre_v1/calibration/proposed_fp_classes.json`
registry under `novel_fp_classes_proposed_for_sar_11_codification`.

Per CEO §3 #5: bulk-ratify 14 clean; selective-ratify 5 edge cases with
`operator_review_note: "Hikvision/Dahua/drone-cohort overlap; flagged at
MAC-104 cycle-7"`.

Bulk-ratify 14:
 (MAC-104) docker_build_host_uuid_drop, apk_fixture_uuid_drop
 (MAC-104b) wave_license_guid_drop, microsoft_appcenter_app_secret_drop,
            pdf_annotation_label_drop, database_column_name_label_drop,
            react_native_keychain_enum_label_drop
 (MAC-104d) nasa_worldwind_avkey_constant_drop, autel_password_regex_template_drop,
            apache_httpclient_context_key_drop, rxjava_build_host_uuid_drop,
            androidannotations_https_default_passwd_drop,
            xml_layout_textview_label_drop, adobe_xmp_image_metadata_uuid_drop

Selective-ratify 5 (operator_review_note attached):
 taobao_security_cipher_uuid_drop  — Hikvision/Dahua Chinese-locale overlap
 microsoft_xml_namespace_uuid_drop — Hikvision/Dahua opensource.html docs
 html_doc_guid_drop                — Hikvision-specific routing GUID
 amap_smac_default_oui_drop        — Chinese-locale drone-cohort overlap
 dji_api_debug_key_drop            — DJI-specific drone-cohort overlap
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTRY = (
    REPO
    / "android_test"
    / "extraction_outputs"
    / "wave_g_pre_v1"
    / "calibration"
    / "proposed_fp_classes.json"
)

OPERATOR_REVIEW_NOTE = "Hikvision/Dahua/drone-cohort overlap; flagged at MAC-104 cycle-7"

# 14 clean bulk-ratify adds
CLEAN_BULK = [
    # --- MAC-104 (2 unique canonical clean) ---
    {
        "fp_class": "docker_build_host_uuid_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "Docker/Jenkins build-host UUIDs in META-INF/rxjava.properties "
            "Build-Host=testing-docker-* / Build-Host=testing-gce-* lines. "
            "Surface in any app shipping RxJava with stamped build metadata."
        ),
        "value_pattern": "<uuid> in Build-Host= line",
        "disambig_strategy": "path_substring(META-INF/rxjava.properties) + line_prefix(Build-Host=)",
        "source_dispatch": "MAC-104",
        "evidence_packages": ["com.mcu.iVMS"],
    },
    {
        "fp_class": "apk_fixture_uuid_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "UUIDs surfaced in test fixture files (assets/test.json, assets/test_*.json) "
            "shipped inside the APK. Not vendor-runtime BLE service UUIDs."
        ),
        "value_pattern": "<uuid> in assets/test*.json",
        "disambig_strategy": "path_substring(assets/test) + value_class=ble_service_uuid",
        "source_dispatch": "MAC-104",
        "evidence_packages": ["com.mcu.iVMS"],
    },
    # --- MAC-104b (5 clean) ---
    {
        "fp_class": "wave_license_guid_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "Windows-style brace-wrapped GUID labeled LICENSE_DEFAULT / "
            "WAVE_LICENSE_WTC_ANDROID (e030c868-e1fc-43e2-8cf1-85b977bd590c). "
            "WAVE Thin Client product license GUID, not BLE."
        ),
        "value_set": ["e030c868-e1fc-43e2-8cf1-85b977bd590c"],
        "disambig_strategy": "line_context_token_set(LICENSE_DEFAULT, WAVE_LICENSE_WTC_ANDROID)",
        "source_dispatch": "MAC-104b",
        "evidence_packages": ["com.motorolasolutions.wave"],
    },
    {
        "fp_class": "microsoft_appcenter_app_secret_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "Microsoft AppCenter app_secret UUID in assets/appcenter-config.json "
            "(analytics SDK build-time identifier). Cross-cuts any app using "
            "AppCenter for crash/usage analytics."
        ),
        "value_pattern": "<uuid> in app_secret field of appcenter-config.json",
        "disambig_strategy": "path_substring(assets/appcenter-config.json) + field_name(app_secret)",
        "source_dispatch": "MAC-104b",
        "evidence_packages": ["com.meraki.go"],
    },
    {
        "fp_class": "pdf_annotation_label_drop",
        "category": "credential",
        "rationale": (
            "NAME_* constants in PDFBox PDAnnotation* classes (Apache PDFBox "
            "library namespace). Field-name constants matching credential regex; "
            "cross-cuts any app using Apache PDFBox."
        ),
        "value_pattern": "NAME_<X> in PDAnnotation*.java/.kt",
        "disambig_strategy": "value_starts_with(NAME_) + path_match(PDAnnotation)",
        "source_dispatch": "MAC-104b",
        "evidence_packages": ["com.meraki.go"],
    },
    {
        "fp_class": "database_column_name_label_drop",
        "category": "credential",
        "rationale": (
            "COLUMN_* constants in AppCenter database / SQLite schemas. "
            "Cross-cuts any app using AppCenter or similar SDK-managed local DB."
        ),
        "value_pattern": "COLUMN_<X> constant",
        "disambig_strategy": "value_starts_with(COLUMN_)",
        "source_dispatch": "MAC-104b",
        "evidence_packages": ["com.meraki.go"],
    },
    {
        "fp_class": "react_native_keychain_enum_label_drop",
        "category": "credential",
        "rationale": (
            "KeychainModule enum-value constants in react-native-keychain. "
            "Cross-cuts any React Native app using the keychain plugin."
        ),
        "value_pattern": "enum value in KeychainModule",
        "disambig_strategy": "path_match(KeychainModule) + line_context_token(enum)",
        "source_dispatch": "MAC-104b",
        "evidence_packages": ["com.meraki.go"],
    },
    # --- MAC-104d (7 clean) ---
    {
        "fp_class": "nasa_worldwind_avkey_constant_drop",
        "category": "credential",
        "rationale": (
            "gov.nasa.worldwind.avkey.X field-name labels matching credential "
            "regex (NASA WorldWind aviation/map library). Cross-cuts any "
            "aviation/map app using WorldWind."
        ),
        "value_pattern": "gov.nasa.worldwind.avkey.<X>",
        "disambig_strategy": "value_starts_with(gov.nasa.worldwind.avkey)",
        "source_dispatch": "MAC-104d",
        "evidence_packages": ["com.parrot.freeflight6"],
    },
    {
        "fp_class": "autel_password_regex_template_drop",
        "category": "credential",
        "rationale": (
            "Password validation regex source strings being matched as credentials. "
            "Pattern templates like `[A-Za-z0-9]{8,}` interpreted as password literals."
        ),
        "value_pattern": "regex-shaped value in password validator context",
        "disambig_strategy": "value_matches_regex_template_shape + context_token(passwordRegex, ValidationRule)",
        "source_dispatch": "MAC-104d",
        "evidence_packages": ["com.autelrobotics.explorer"],
    },
    {
        "fp_class": "apache_httpclient_context_key_drop",
        "category": "credential",
        "rationale": (
            "http.user-token and similar Apache HttpClient context constants. "
            "Library namespace constants, not credential values."
        ),
        "value_set": ["http.user-token", "http.auth.credentials-provider", "http.auth.target-scope"],
        "disambig_strategy": "value_starts_with(http.)",
        "source_dispatch": "MAC-104d",
        "evidence_packages": ["com.autelrobotics.explorer"],
    },
    {
        "fp_class": "rxjava_build_host_uuid_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "Build-Host=testing-gce-<uuid> in META-INF/rxjava.properties. "
            "Generalization of docker_build_host_uuid_drop (covers GCE + Docker "
            "build hosts)."
        ),
        "value_pattern": "<uuid> in Build-Host=testing-*-<uuid> line",
        "disambig_strategy": "path_substring(META-INF/rxjava.properties) + value_pattern(Build-Host=testing-)",
        "source_dispatch": "MAC-104d",
        "evidence_packages": ["com.autelrobotics.explorer"],
        "supersedes": "docker_build_host_uuid_drop (MAC-104 iVMS) — generalize",
    },
    {
        "fp_class": "androidannotations_https_default_passwd_drop",
        "category": "credential",
        "rationale": (
            "Java cacerts default 'changeit' password in androidannotations "
            "HttpsClient. Library default; not a vendor credential."
        ),
        "value_set": ["changeit"],
        "disambig_strategy": "value_exact_match(changeit) + context_token(HttpsClient, KeyStore)",
        "source_dispatch": "MAC-104d",
        "evidence_packages": ["com.autelrobotics.explorer"],
    },
    {
        "fp_class": "xml_layout_textview_label_drop",
        "category": "credential",
        "rationale": (
            "XML res/layout <TextView android:text=\"Password:\"> UI labels "
            "matched by credential regex. UI string, not credential value."
        ),
        "value_pattern": "\"Password:\" or similar UI label in XML layout",
        "disambig_strategy": "path_substring(res/layout/) + xml_element(TextView) + attribute(android:text)",
        "source_dispatch": "MAC-104d",
        "evidence_packages": ["com.dji.industry.pilot"],
    },
    {
        "fp_class": "adobe_xmp_image_metadata_uuid_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "Adobe Photoshop / XMP metadata UUIDs (xmp.did:, xmp.iid:, "
            "adobe:docid:photoshop:) embedded in shipped image assets. "
            "Cross-cuts any app bundling Adobe-edited assets."
        ),
        "value_pattern": "uuid in (xmp.did:|xmp.iid:|adobe:docid:photoshop:) prefix",
        "disambig_strategy": "value_prefix_in(xmp.did:, xmp.iid:, adobe:docid:photoshop:)",
        "source_dispatch": "MAC-104d",
        "evidence_packages": ["dji.go.v5"],
    },
]

# 5 edge-case selective-ratify (Hikvision/Dahua/drone-cohort overlap)
EDGE_CASES = [
    {
        "fp_class": "taobao_security_cipher_uuid_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "Alibaba TAOBAO_SECURITY_CIPER_KEY in Constant.java (third-party "
            "push notification SDK). Cross-cuts any Chinese-locale app shipping "
            "Alibaba push SDK."
        ),
        "value_set": ["fc02cb6f-78ac-4e14-b2b3-da685d242216"],
        "disambig_strategy": "value_exact_match + context_token(TAOBAO_SECURITY_CIPER_KEY)",
        "source_dispatch": "MAC-104",
        "evidence_packages": ["com.mcu.iVMS"],
        "operator_review_note": OPERATOR_REVIEW_NOTE,
        "overlap_risk": (
            "Chinese-locale FP — Hikvision/Dahua vendor-custom UUIDs may "
            "coincidentally overlap with Alibaba push SDK identifiers; "
            "exact-value-match disambig is safe but generalization is risky."
        ),
    },
    {
        "fp_class": "microsoft_xml_namespace_uuid_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "c2f41010-65b3-11d1-a29f-00aa00c14882 is the Microsoft XML schema "
            "namespace UUID; surfaces in third-party opensource.html files."
        ),
        "value_set": ["c2f41010-65b3-11d1-a29f-00aa00c14882"],
        "disambig_strategy": "value_exact_match + path_substring(assets/declare/opensource.html)",
        "source_dispatch": "MAC-104",
        "evidence_packages": ["com.mm.android.DMSS"],
        "operator_review_note": OPERATOR_REVIEW_NOTE,
        "overlap_risk": (
            "Hikvision/Dahua bundle Microsoft library docs (opensource.html) — "
            "MS schema UUIDs appear in their APKs. Generalization to all "
            "Microsoft schema UUIDs needs review; current exact-value-match is safe."
        ),
    },
    {
        "fp_class": "html_doc_guid_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "Hik-Connect doc-routing GUID (1aa0ec25-954c-4e73-8371-386f9b8184a1) "
            "in HTML help documentation files. Documentation routing identifier, "
            "not BLE."
        ),
        "value_set": ["1aa0ec25-954c-4e73-8371-386f9b8184a1"],
        "disambig_strategy": "value_exact_match + path_substring(assets/help/)",
        "source_dispatch": "MAC-104",
        "evidence_packages": ["com.hikvision.hikconnect"],
        "operator_review_note": OPERATOR_REVIEW_NOTE,
        "overlap_risk": (
            "Hikvision-specific edge case. Generalizing to all HTML doc GUIDs "
            "needs vendor-survey before bulk application."
        ),
    },
    {
        "fp_class": "amap_smac_default_oui_drop",
        "category": "oui",
        "rationale": (
            "00:00:00:00:00:00 / 02:00:00:00:00:00 placeholder MACs in AMap "
            "(Autonavi location SDK). Cross-cuts all Chinese-locale apps "
            "shipping AMap."
        ),
        "value_set": ["00:00:00:00:00:00", "02:00:00:00:00:00"],
        "disambig_strategy": "value_exact_match + path_substring(com/amap/)",
        "source_dispatch": "MAC-104d",
        "evidence_packages": ["dji.go.v5", "com.dji.industry.pilot"],
        "operator_review_note": OPERATOR_REVIEW_NOTE,
        "overlap_risk": (
            "Chinese-locale drone-cohort overlap (AMap is China-mainland default "
            "for DJI Fly + DJI Pilot). All-zeros MAC is also a §7.3 known-fake "
            "pattern — disambig must not mask legitimate AMap-vendor identifier "
            "rows if they ever surface."
        ),
    },
    {
        "fp_class": "dji_api_debug_key_drop",
        "category": "ble_service_uuid",
        "rationale": (
            "UUID in DJI assets/api_debug.txt debug_key field. DJI-internal "
            "telemetry endpoint key, not BLE service UUID."
        ),
        "value_set": ["d721cdeb-b29f-410a-b5c6-80afa83f4461"],
        "disambig_strategy": "value_exact_match + path_substring(assets/api_debug.txt)",
        "source_dispatch": "MAC-104d",
        "evidence_packages": ["dji.go.v5"],
        "operator_review_note": OPERATOR_REVIEW_NOTE,
        "overlap_risk": (
            "DJI-specific drone-cohort edge case. Generalizing to all api_debug.txt "
            "UUIDs risks masking legitimate per-vendor BLE UUIDs in other vendors "
            "that ship debug-key files; exact-value-match is safe."
        ),
    },
]


def make_session_block() -> dict:
    return {
        "session": "MAC-104_wave_g_v2_cycle7",
        "integration_dispatch_ref": "MAC-178",
        "integration_date_utc": "2026-05-18T15:00:00Z",
        "ceo_ratification_basis": "CEO §3 #5 — bulk-ratify 14 clean + selective-ratify 5 edge with operator_review_note",
        "clean_bulk_count": 14,
        "edge_case_count": 5,
        "novel_fp_classes_proposed_for_sar_11_codification": CLEAN_BULK + EDGE_CASES,
    }


def main() -> int:
    print(f"Registry: {REGISTRY}")
    if not REGISTRY.exists():
        raise SystemExit(f"registry missing: {REGISTRY}")

    data = json.loads(REGISTRY.read_text())
    if "mac104_wave_g_v2_additions" in data:
        print("  mac104_wave_g_v2_additions already present — skipping (idempotent)")
        print(
            f"  prior addition count: {len(data['mac104_wave_g_v2_additions']['novel_fp_classes_proposed_for_sar_11_codification'])}"
        )
        return 0

    block = make_session_block()
    data["mac104_wave_g_v2_additions"] = block

    REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    print("\n=== Priority 6 verification ===")
    print(f"clean bulk-ratify entries added: {len(CLEAN_BULK)}")
    print(f"edge-case selective-ratify entries added: {len(EDGE_CASES)}")
    print(
        f"total FP-class proposals appended: {len(CLEAN_BULK) + len(EDGE_CASES)}"
    )
    print()
    print("=== bulk-ratify list ===")
    for c in CLEAN_BULK:
        print(f"  [{c['source_dispatch']:<10}] {c['fp_class']:<45} category={c['category']}")
    print()
    print("=== edge-case (operator_review_note) list ===")
    for c in EDGE_CASES:
        print(f"  [{c['source_dispatch']:<10}] {c['fp_class']:<45} category={c['category']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
