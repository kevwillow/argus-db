"""MAC-101 Item C Phase 1 mapper — cyber-defence-campus/RemoteIDReceiver (Wave-A 4c).

Shape: typed-bucket under `identifiers_by_type` with OUI lists + ASD-STAN enum dicts +
DJI struct-format fingerprints. Many entries are corroborations.
sources.id = 27 (pre-resolved).
"""
import json, hashlib, os

SLUG = "cyber-defence-campus_RemoteIDReceiver"
SOURCE_ID = 27
REPO_URL = "https://github.com/cyber-defence-campus/RemoteIDReceiver"
IN_PATH = f"raw/wave_a/{SLUG}/2026-05-11T01-21-41.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url, ctype, cident):
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s, n=200):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def emit():
    d = json.load(open(IN_PATH))
    captured_at = d.get("run_iso")
    ib = d.get("identifiers_by_type", {})
    out = []

    # OUI lists — 4 buckets
    oui_buckets = [
        ("ouis_asdstan", "ASD-STAN reserved OUI block", "drone", None),
        ("ouis_dji_legitimate", "DJI registered OUI", "drone", "DJI"),
        ("ouis_dji_spoof_marker", "DJI Drone-ID spoof marker (well-known fake)", "drone", "DJI"),
        ("ouis_parrot_negative_fixture", "Parrot OUI (negative fixture — explicitly NOT registered for ASD-STAN)", "drone", "Parrot"),
    ]
    for bkey, label, category, vendor in oui_buckets:
        for oui in ib.get(bkey, []):
            ctype = "mac_oui"
            doc_url = f"{REPO_URL}#identifiers_by_type.{bkey}"
            out.append({
                "source_id": SOURCE_ID,
                "source_url": doc_url,
                "candidate_identifier": oui,
                "candidate_type": ctype,
                "candidate_category": category,
                "candidate_manufacturer": vendor,
                "source_excerpt": trunc(f"identifiers_by_type.{bkey}: {label}"),
                "source_row_key": row_key(doc_url, ctype, oui),
                "raw_payload": json.dumps({"bucket": bkey, "oui": oui}),
                "notes": {
                    "wave": "A_deferred_dir",
                    "mapper_slug": SLUG,
                    "mapper_run_id": "MAC-101 Item C Phase 1",
                    "shape_origin": f"identifiers_by_type.{bkey}",
                    "bucket_label": label,
                    "is_negative_fixture": bkey == "ouis_parrot_negative_fixture",
                    "is_spoof_marker": bkey == "ouis_dji_spoof_marker",
                },
                "captured_at": captured_at,
            })

    # ASD-STAN message types (7) — enum values
    for mt in ib.get("asdstan_message_types", []):
        ctype = "asdstan_message_type"
        doc_url = f"{REPO_URL}#asdstan_message_types"
        cv = f"asdstan_msg_type_{mt}"
        out.append({
            "source_id": SOURCE_ID,
            "source_url": doc_url,
            "candidate_identifier": cv,
            "candidate_type": ctype,
            "candidate_category": "drone",
            "candidate_manufacturer": None,
            "source_excerpt": trunc(f"ASD-STAN Remote-ID message type enum value: {mt}"),
            "source_row_key": row_key(doc_url, ctype, cv),
            "raw_payload": json.dumps({"message_type": mt}),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "identifiers_by_type.asdstan_message_types[]",
                "candidate_type_proposed": True,
                "enum_value": mt,
            },
            "captured_at": captured_at,
        })

    # ASD-STAN id_type / height_type / location_source enum value dicts
    for dict_key, label in [
        ("asdstan_id_type_values", "ID type enum"),
        ("asdstan_height_type_enum", "Height type enum"),
        ("asdstan_location_source_enum", "Location source enum"),
        ("asdstan_ua_category_enum", "UA category enum"),
    ]:
        for k, v in ib.get(dict_key, {}).items():
            ctype = "asdstan_enum_value"
            cv = f"{dict_key}.{k}={v}"
            doc_url = f"{REPO_URL}#{dict_key}"
            out.append({
                "source_id": SOURCE_ID,
                "source_url": doc_url,
                "candidate_identifier": cv,
                "candidate_type": ctype,
                "candidate_category": "drone",
                "candidate_manufacturer": None,
                "source_excerpt": trunc(f"{label}: value={k} meaning='{v}'"),
                "source_row_key": row_key(doc_url, ctype, cv),
                "raw_payload": json.dumps({"dict_key": dict_key, "k": k, "v": v}),
                "notes": {
                    "wave": "A_deferred_dir",
                    "mapper_slug": SLUG,
                    "mapper_run_id": "MAC-101 Item C Phase 1",
                    "shape_origin": f"identifiers_by_type.{dict_key}",
                    "candidate_type_proposed": True,
                    "label": label,
                },
                "captured_at": captured_at,
            })

    # DJI struct-format strings — protocol fingerprints
    for sf_key, ver in [("dji_v1_struct_format", "v1"), ("dji_v2_struct_format", "v2")]:
        sf = ib.get(sf_key)
        if not sf:
            continue
        ctype = "dji_protocol_struct_format"
        doc_url = f"{REPO_URL}#{sf_key}"
        cv = f"dji_{ver}:{sf}"
        out.append({
            "source_id": SOURCE_ID,
            "source_url": doc_url,
            "candidate_identifier": cv,
            "candidate_type": ctype,
            "candidate_category": "drone",
            "candidate_manufacturer": "DJI",
            "source_excerpt": trunc(f"DJI Drone-ID {ver} struct format: {sf}"),
            "source_row_key": row_key(doc_url, ctype, cv),
            "raw_payload": json.dumps({"version": ver, "struct_format": sf}),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": f"identifiers_by_type.{sf_key}",
                "candidate_type_proposed": True,
                "protocol_version": ver,
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
