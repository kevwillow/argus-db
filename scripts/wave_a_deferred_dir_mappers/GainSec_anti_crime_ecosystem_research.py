"""MAC-101 Item C Phase 1 mapper — GainSec/anti-crime-ecosystem-research (Wave-A Phase 6δ).

Shape: typed-bucket + CVE-list; 15 extracted_identifiers sub-buckets + 15 CVE refs +
NVS partition contents (Raven device-internal config).
sources.id: CEO §2 disposition pending (recommended NEW row); reads SOURCE_ID env at run time.
"""
import json, hashlib, os

SLUG = "GainSec_anti-crime-ecosystem-research"
REPO_URL = "https://github.com/GainSec/anti-crime-ecosystem-research"
IN_PATH = f"raw/wave_a/{SLUG}/2026-05-11T05-31-51Z.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url, ctype, cident):
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s, n=200):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# Device → §3.1 category mapping
DEVICE_CATEGORY = {
    "Raven": "gunshot_detect",
    "Raven Gunshot Detection": "gunshot_detect",
    "Raven Gunshot Detection (NVS fallback when LTE unavailable)": "gunshot_detect",
    "Raven (ESP32 ROM)": "gunshot_detect",
    "Picard": "alpr",
    "Bravo": "alpr",
    "Picard/Bravo Compute Box": "alpr",
    "LPR + Compute Box": "alpr",
    "FSInstaller app (com.flocksafety.hazyhiwire)": "alpr",
}


def cat(dev):
    return DEVICE_CATEGORY.get(dev, "unknown")


def emit(source_id: int):
    d = json.load(open(IN_PATH))
    captured_at = d.get("run_metadata", {}).get("extracted_at_utc")
    ei = d.get("extracted_identifiers", {})
    out = []

    # device_models_product_codenames (6)
    for r in ei.get("device_models_product_codenames", []):
        val = r.get("value")
        if not val:
            continue
        ctype = "product_family_codename"
        doc_url = f"{REPO_URL}#device_models_product_codenames"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": cat(r.get("device_type") or val),
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"product codename '{val}' device_type={r.get('device_type')} os={r.get('os')} fw_sha256={r.get('firmware_sha256')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "extracted_identifiers.device_models_product_codenames[]",
                "confidence_hint": r.get("confidence"),
                "cross_check": r.get("cross_check"),
                "device_type": r.get("device_type"),
                "os": r.get("os"),
                "model_number_per_paper": r.get("model_number_per_paper"),
            },
            "captured_at": captured_at,
        })

    # firmware_sha256_hashes (3)
    for r in ei.get("firmware_sha256_hashes", []):
        val = r.get("identifier")
        if not val:
            continue
        ctype = "firmware_sha256_hash"
        doc_url = f"{REPO_URL}#firmware_sha256_hashes"
        device = r.get("device")
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": cat(device),
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"firmware sha256 for {device}: {val}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "extracted_identifiers.firmware_sha256_hashes[]",
                "candidate_type_proposed": True,
                "device": device,
                "confidence_hint": r.get("confidence"),
            },
            "captured_at": captured_at,
        })

    # android_package_names (15)
    for r in ei.get("android_package_names", []):
        val = r.get("package")
        if not val:
            continue
        ctype = "android_package_name"
        doc_url = f"{REPO_URL}#android_package_names"
        device = r.get("device")
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": cat(device),
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"android package '{val}' device={device} v={r.get('version_unit1')}/{r.get('version_unit2')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "extracted_identifiers.android_package_names[]",
                "candidate_type_proposed": True,
                "device": device,
                "confidence_hint": r.get("confidence"),
                "apk_sha256_unit1": r.get("apk_sha256_unit1"),
                "apk_sha256_unit2": r.get("apk_sha256_unit2"),
            },
            "captured_at": captured_at,
        })

    # ssid_strings (3) — exact SSIDs stored in NVS
    for r in ei.get("ssid_strings", []):
        val = r.get("identifier")
        if not val:
            continue
        ctype = "ssid"
        doc_url = f"{REPO_URL}#ssid_strings"
        device = r.get("device")
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": cat(device),
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"SSID string '{val}' device={device}; {r.get('cross_check','')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "extracted_identifiers.ssid_strings[]",
                "device": device,
                "confidence_hint": r.get("confidence"),
                "cross_check": r.get("cross_check"),
            },
            "captured_at": captured_at,
        })

    # cloud_endpoints_subdomains (4)
    for r in ei.get("cloud_endpoints_subdomains", []):
        val = r.get("identifier")
        if not val:
            continue
        ctype = "cloud_endpoint_fqdn"
        doc_url = f"{REPO_URL}#cloud_endpoints_subdomains"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "unknown",
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"cloud endpoint '{val}' {r.get('note','')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "extracted_identifiers.cloud_endpoints_subdomains[]",
                "candidate_type_proposed": True,
                "confidence_hint": r.get("confidence"),
            },
            "captured_at": captured_at,
        })

    # rest_api_endpoints_collins (13)
    for r in ei.get("rest_api_endpoints_collins", []):
        val = r.get("endpoint")
        if not val:
            continue
        ctype = "rest_endpoint"
        doc_url = f"{REPO_URL}#rest_api_endpoints_collins"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"REST endpoint '{val}' service={r.get('service')} fn={r.get('function')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "extracted_identifiers.rest_api_endpoints_collins[]",
                "candidate_type_proposed": True,
                "service": r.get("service"),
                "function": r.get("function"),
            },
            "captured_at": captured_at,
        })

    # fsinstaller_hardcoded_urls (2)
    for r in ei.get("fsinstaller_hardcoded_urls", []):
        val = r.get("identifier")
        if not val:
            continue
        ctype = "lan_endpoint_url"
        doc_url = f"{REPO_URL}#fsinstaller_hardcoded_urls"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"FSInstaller hardcoded URL '{val}' {r.get('note','')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "extracted_identifiers.fsinstaller_hardcoded_urls[]",
                "candidate_type_proposed": True,
                "confidence_hint": r.get("confidence"),
            },
            "captured_at": captured_at,
        })

    # esp32_boot_log_signatures (4)
    for r in ei.get("esp32_boot_log_signatures", []):
        val = r.get("identifier")
        if not val:
            continue
        ctype = "boot_log_signature"
        doc_url = f"{REPO_URL}#esp32_boot_log_signatures"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "gunshot_detect",
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"esp32 boot log signature '{val}' {r.get('note','')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "extracted_identifiers.esp32_boot_log_signatures[]",
                "candidate_type_proposed": True,
                "device": r.get("device"),
                "confidence_hint": r.get("confidence"),
            },
            "captured_at": captured_at,
        })

    # picard_bravo_qualcomm_gpt_partition_uuids (3)
    for r in ei.get("picard_bravo_qualcomm_gpt_partition_uuids", []):
        val = r.get("uuid")
        if not val:
            continue
        ctype = "gpt_partition_uuid"
        doc_url = f"{REPO_URL}#picard_bravo_qualcomm_gpt_partition_uuids"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"GPT partition '{r.get('partition_name')}' uuid={val} device={r.get('device')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "extracted_identifiers.picard_bravo_qualcomm_gpt_partition_uuids[]",
                "candidate_type_proposed": True,
                "partition_name": r.get("partition_name"),
                "device": r.get("device"),
                "confidence_hint": r.get("confidence"),
            },
            "captured_at": captured_at,
        })

    # NVS partition contents — extract the decoded SSIDs (the password fields are PII-shaped → §11 #3 hold)
    nvs = ei.get("nvs_partition_contents_raven", {}) or {}
    nvs_doc_url = f"{REPO_URL}#nvs_partition_contents_raven"
    for k in ("decoded_ssid_1", "decoded_ssid_2"):
        v = nvs.get(k)
        if not v:
            continue
        ctype = "ssid"
        out.append({
            "source_id": source_id,
            "source_url": nvs_doc_url,
            "candidate_identifier": v,
            "candidate_type": ctype,
            "candidate_category": "gunshot_detect",
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"NVS partition decoded SSID '{v}' from Raven firmware NVS dump"),
            "source_row_key": row_key(nvs_doc_url, ctype, v),
            "raw_payload": json.dumps({"nvs_key": k, "value": v}),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": f"extracted_identifiers.nvs_partition_contents_raven.{k}",
                "pii_adjacent": "password_field_present_in_same_partition_redacted",
                "pii_review_disposition": "ssid_ok_password_held",
                "partition_name": nvs.get("partition_name"),
                "key_observed": nvs.get("key_observed"),
            },
            "captured_at": captured_at,
        })

    # cve_references_22_full_list (15)
    seen_cves = set()
    for r in d.get("cve_references_22_full_list", []):
        val = r.get("cve")
        if not val or val in seen_cves:
            continue
        seen_cves.add(val)
        ctype = "cve_reference"
        doc_url = f"{REPO_URL}#cve_references_22_full_list"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": cat(r.get("device")),
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"{val} '{r.get('title')}' device={r.get('device')} severity={r.get('severity')} cwe={r.get('cwe')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "cve_references_22_full_list[]",
                "candidate_type_proposed": True,
                "title": r.get("title"),
                "device": r.get("device"),
                "severity": r.get("severity"),
                "cvss_4": r.get("cvss_4"),
                "cwe": r.get("cwe"),
                "disclosure_date": r.get("disclosure_date"),
                "finding_id": r.get("finding_id"),
            },
            "captured_at": captured_at,
        })

    return out


if __name__ == "__main__":
    sid = int(os.environ.get("SOURCE_ID", "0"))
    if not sid:
        raise SystemExit("SOURCE_ID env var required (pending CEO §2 disposition)")
    rows = emit(sid)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"{SLUG}: emitted {len(rows)} rows → {OUT_PATH}")
