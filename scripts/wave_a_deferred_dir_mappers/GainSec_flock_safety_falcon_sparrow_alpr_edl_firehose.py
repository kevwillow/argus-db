"""MAC-101 Item C Phase 1 mapper — GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose (Wave-A Phase 6ε).

Shape: firmware-binary-analysis; ALPR-DDR-FIREHOSE.mbn dissection.
- firmware sha256, soc chipset list (39), build version strings (3), x509 cert chain (3),
  network endpoints (1; CRL URL), single Flock-branded string, image_variant/chip_format codenames.
sources.id: CEO §2 disposition pending (recommended NEW row, NO LICENSE flag);
reads SOURCE_ID env at run time.
"""
import json, hashlib, os

SLUG = "GainSec_flock-safety-falcon-sparrow-alpr-edl-firehose"
REPO_URL = "https://github.com/GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose"
IN_PATH = f"raw/wave_a/{SLUG}/20260511T053109Z.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url, ctype, cident):
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s, n=200):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def emit(source_id: int):
    d = json.load(open(IN_PATH))
    captured_at = d.get("run_metadata", {}).get("iso8601_utc")
    out = []
    fb = d.get("firmware_binary", {})
    fb_filename = fb.get("filename")
    fb_sha = fb.get("sha256")
    binary_path = f"{REPO_URL}/blob/main/{fb_filename}" if fb_filename else REPO_URL

    # 1) firmware sha256 — the binary itself
    if fb_sha:
        ctype = "firmware_sha256_hash"
        out.append({
            "source_id": source_id,
            "source_url": binary_path,
            "candidate_identifier": fb_sha,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"firmware {fb_filename} sha256={fb_sha} size={fb.get('size_bytes')}B {fb.get('file_type','')}"),
            "source_row_key": row_key(binary_path, ctype, fb_sha),
            "raw_payload": json.dumps(fb),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "firmware_binary.sha256",
                "candidate_type_proposed": True,
                "filename": fb_filename,
                "size_bytes": fb.get("size_bytes"),
                "format_class": fb.get("format_class"),
                "entry_point_hex": fb.get("entry_point_hex"),
                "load_address_hex": fb.get("load_address_hex"),
            },
            "captured_at": captured_at,
        })

    # 2) soc_chipset_support_list — 39 chipset codenames (per §11 #13 → category='unknown', not single-product binding)
    for chipset in d.get("soc_chipset_support_list", []):
        ctype = "chipset_codename"
        doc_url = f"{REPO_URL}#soc_chipset_support_list"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": chipset,
            "candidate_type": ctype,
            "candidate_category": "unknown",
            "candidate_manufacturer": "Qualcomm",
            "source_excerpt": trunc(f"firmware soc_chipset_support_list[]: {chipset}"),
            "source_row_key": row_key(doc_url, ctype, chipset),
            "raw_payload": json.dumps({"chipset": chipset}),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "soc_chipset_support_list[]",
                "candidate_type_proposed": True,
                "generic_chipset_no_product_binding": True,
                "rule_11_13": "category_unknown_until_validator_pairs_with_product_line",
            },
            "captured_at": captured_at,
        })

    # 3) build_version_identifiers (3)
    for r in d.get("build_version_identifiers", []):
        val = r.get("value")
        if not val:
            continue
        ctype = r.get("candidate_type") or "firmware_build_string"
        doc_url = f"{REPO_URL}#build_version_identifiers"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": "Qualcomm",
            "source_excerpt": trunc(f"firmware build_version key={r.get('key')} value={val} interp={r.get('interpretation','')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "build_version_identifiers[]",
                "candidate_type_proposed": True,
                "key": r.get("key"),
                "interpretation": r.get("interpretation"),
                "build_timestamp_utc": r.get("build_timestamp_utc"),
                "build_codename": r.get("build_codename"),
                "build_guid": r.get("build_guid"),
                "confidence_hint": r.get("confidence"),
            },
            "captured_at": captured_at,
        })

    # 4) x509_cert_chain_fingerprints (3) — emit each as own observation
    for r in d.get("x509_cert_chain_fingerprints", []):
        val = r.get("sha256_first_8_bytes_hex")
        if not val:
            continue
        ctype = "x509_cert_sha256_prefix"
        doc_url = f"{binary_path}#x509_cert_offset_{r.get('offset_in_binary_hex','unknown')}"
        cn = r.get("subject_common_name")
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "unknown",
            "candidate_manufacturer": r.get("subject_org"),
            "source_excerpt": trunc(f"x509 {r.get('position_in_chain')} cn='{cn}' issuer='{r.get('issuer_common_name')}' sha256_prefix={val}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "x509_cert_chain_fingerprints[]",
                "candidate_type_proposed": True,
                "position_in_chain": r.get("position_in_chain"),
                "subject_common_name": cn,
                "subject_org": r.get("subject_org"),
                "subject_locality": r.get("subject_locality"),
                "issuer_common_name": r.get("issuer_common_name"),
                "validity_not_before": r.get("validity_not_before"),
                "validity_not_after": r.get("validity_not_after"),
                "crl_distribution_url": r.get("crl_distribution_url"),
                "self_signed": r.get("self_signed"),
            },
            "captured_at": captured_at,
        })

    # 5) network_endpoints (1; CRL URL embedded in cert)
    for r in d.get("network_endpoints", []):
        val = r.get("value")
        if not val:
            continue
        ctype = "network_endpoint"
        doc_url = f"{binary_path}#network_endpoints"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "unknown",
            "candidate_manufacturer": r.get("vendor"),
            "source_excerpt": trunc(f"network endpoint '{val}' purpose={r.get('purpose','')} lens={r.get('lens')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "network_endpoints[]",
                "candidate_type_proposed": True,
                "purpose": r.get("purpose"),
                "lens": r.get("lens"),
                "host": r.get("host"),
                "scheme": r.get("scheme"),
                "confidence_hint": r.get("confidence"),
            },
            "captured_at": captured_at,
        })

    # 6) image_variant + chip_format_id_example — firmware identity fingerprints
    fs = d.get("falcon_sparrow_model_identifiers", {}) or {}
    for key, ctype in (("image_variant", "firmware_image_variant"),
                       ("chip_format_id_example", "qualcomm_chip_format_id")):
        v = fs.get(key)
        if not v or not isinstance(v, str):
            continue
        doc_url = f"{binary_path}#falcon_sparrow_model_identifiers.{key}"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": v,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": "Qualcomm",
            "source_excerpt": trunc(f"firmware {key}='{v}'; soc_family='{fs.get('target_soc_family','')}'"),
            "source_row_key": row_key(doc_url, ctype, v),
            "raw_payload": json.dumps({"key": key, "value": v, "fs_context": fs}),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": f"falcon_sparrow_model_identifiers.{key}",
                "candidate_type_proposed": True,
                "target_soc_family": fs.get("target_soc_family"),
                "target_pmic_pair": fs.get("target_pmic_pair"),
            },
            "captured_at": captured_at,
        })

    # 7) flock_branded_strings_found (1; "usb:force_eDL")
    for s in fs.get("flock_branded_strings_found", []) or []:
        if not s:
            continue
        ctype = "firmware_branded_string"
        doc_url = f"{binary_path}#flock_branded_strings_found"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": s,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": "Flock Safety",
            "source_excerpt": trunc(f"Flock-branded string in firmware binary: '{s}'"),
            "source_row_key": row_key(doc_url, ctype, s),
            "raw_payload": json.dumps({"value": s}),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "falcon_sparrow_model_identifiers.flock_branded_strings_found[]",
                "candidate_type_proposed": True,
                "headline_finding": fs.get("headline_finding"),
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
