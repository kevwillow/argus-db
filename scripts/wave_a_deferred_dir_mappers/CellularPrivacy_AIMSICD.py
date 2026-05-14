"""MAC-101 Item C Phase 1 mapper — CellularPrivacy/AIMSICD (Wave-A 6γ).

Shape: dict-of-typed-lists under `identifiers` with 12 typed buckets;
non-empty: behavioral_signature (8), tunable_threshold (9), logcat_detection_string (6),
modem_attack_surface_path (5), oem_service_mode_command (5), threat_level_enum (6).
sources.id = 32 (pre-resolved).
"""
import json, hashlib, os

SLUG = "CellularPrivacy_AIMSICD"
SOURCE_ID = 32
REPO_URL = "https://github.com/CellularPrivacy/Android-IMSI-Catcher-Detector"
IN_PATH = f"raw/wave_a/{SLUG}/20260511T053209Z.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url, ctype, cident):
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s, n=200):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# Bucket → (candidate_type, is_behavioral_signature_class)
BUCKETS = [
    ("behavioral_signature",  "behavioral_signature",   True),
    ("tunable_threshold",     "tunable_threshold",      False),
    ("logcat_detection_string","logcat_detection_string",False),
    ("modem_attack_surface_path","modem_device_path",   False),
    ("oem_service_mode_command","oem_service_mode_command",False),
    ("threat_level_enum",     "threat_level_enum",      False),
]


def emit():
    d = json.load(open(IN_PATH))
    captured_at = d.get("timestamp_utc")
    ids = d.get("identifiers", {})
    out = []
    for bucket_key, ctype, is_bs in BUCKETS:
        # Sibling-row inheritance: when an enum bucket lists its file/line only on
        # the first member, later siblings inherit it (matches upstream extraction shape).
        last_file = None; last_line = None
        for r in ids.get(bucket_key, []):
            val = r.get("value")
            if not val:
                continue
            file_ = r.get("file") or last_file
            line = r.get("line") or last_line
            if r.get("file"): last_file = r.get("file")
            if r.get("line"): last_line = r.get("line")
            doc_url = f"{REPO_URL}/blob/master/{file_}#L{str(line).split('-')[0]}" if file_ and line else (
                f"{REPO_URL}/blob/master/{file_}" if file_ else REPO_URL
            )
            # cell categorization: AIMSICD is an Android IMSI-catcher detection app
            category = "imsi_catcher"
            excerpt_src = r.get("logic") or r.get("purpose") or r.get("role") or r.get("df_description") or ""
            out.append({
                "source_id": SOURCE_ID,
                "source_url": doc_url,
                "candidate_identifier": val,
                "candidate_type": ctype,
                "candidate_category": category,
                "candidate_manufacturer": r.get("vendor"),
                "source_excerpt": trunc(f"{file_}:{line} {excerpt_src}"),
                "source_row_key": row_key(doc_url, ctype, val),
                "raw_payload": json.dumps(r),
                "notes": {
                    "wave": "A_deferred_dir",
                    "mapper_slug": SLUG,
                    "mapper_run_id": "MAC-101 Item C Phase 1",
                    "shape_origin": f"identifiers.{bucket_key}[]",
                    "candidate_type_proposed": ctype != "behavioral_signature",
                    "mac58_option_b": is_bs,
                    "phase_6_gate_lifted": is_bs,
                    "no_promotion_phase2": is_bs,
                    "detection_flag_id": r.get("detection_flag_id"),
                    "raised_status": r.get("raised_status"),
                    "default_value": r.get("default"),
                    "units": r.get("units"),
                    "lens": r.get("lens"),
                    "sms_type_classification": r.get("sms_type_classification"),
                    "color": r.get("color"),
                    "ordinal": r.get("ordinal"),
                    "raw_byte": r.get("raw_byte"),
                },
                "captured_at": captured_at,
            })

    return out


if __name__ == "__main__":
    rows = emit()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"{SLUG}: emitted {len(rows)} rows → {OUT_PATH}")
