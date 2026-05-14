"""MAC-101 Item C Phase 1 mapper — nixxxo/tagfinder (Wave-A 4h).

Shape: flat-list `identifiers` (20 rows) — pre-annotated with id, value_hex, file, line.
Plus 1 behavioral_signature under phase_6_behavioral_signatures.confidence_scoring_logic.
sources.id = 29 (pre-resolved).
"""
import json, hashlib, os

SLUG = "nixxxo_tagfinder"
SOURCE_ID = 29
REPO_URL = "https://github.com/nixxxo/tagfinder"
IN_PATH = f"raw/wave_a/{SLUG}/20260511T052138Z.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url, ctype, cident):
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s, n=200):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# Per-row type assignment based on id-name semantics (see issue §3 vocab + analysis at mapper time).
ID_TO_TYPE = {
    "apple_company_id_msb": "ble_company_id",
    "apple_company_id_full": "ble_company_id",
    "airtag_adv_type_unregistered": "ble_protocol_byte",
    "airtag_adv_type_registered": "ble_protocol_byte",
    "airtag_protocol_byte_1": "ble_protocol_byte",
    "airtag_type_byte": "ble_protocol_byte",
    "apple_adv_type_table": "ble_protocol_byte_table",
    "airtag_status_bits": "ble_protocol_byte_table",
    "airtag_battery_status": "ble_protocol_byte_table",
    "airtag_p224_pubkey_layout": "ble_payload_offset",  # ambiguous, low conf
    "samsung_smarttag_uuid": "ble_service_uuid",
    "tile_tracker": "ble_service_uuid",
    "chipolo_company_id": "ble_company_id",
    "pebblebee_company_id": "ble_company_id",
    "itag_company_id": "ble_company_id",
    "nutale_company_id": "ble_company_id",
    "nut_company_id": "ble_company_id",
    "apple_findmy_service_uuids": "ble_service_uuid",
    "airtag_timing_registered": "ble_adv_interval",
    "airtag_timing_unregistered": "ble_adv_interval",
}

# Vendor mapping (single-product-line/single-vendor binding → category override allowed)
ID_TO_VENDOR = {
    "apple_company_id_msb": "Apple",
    "apple_company_id_full": "Apple",
    "airtag_adv_type_unregistered": "Apple",
    "airtag_adv_type_registered": "Apple",
    "airtag_protocol_byte_1": "Apple",
    "airtag_type_byte": "Apple",
    "apple_adv_type_table": "Apple",
    "airtag_status_bits": "Apple",
    "airtag_battery_status": "Apple",
    "airtag_p224_pubkey_layout": "Apple",
    "samsung_smarttag_uuid": "Samsung",
    "tile_tracker": "Tile",
    "chipolo_company_id": "Chipolo",
    "pebblebee_company_id": "Pebblebee",
    "itag_company_id": "iTag",
    "nutale_company_id": "Nutale",
    "nut_company_id": "Nut",
    "apple_findmy_service_uuids": "Apple",
    "airtag_timing_registered": "Apple",
    "airtag_timing_unregistered": "Apple",
}


def emit():
    d = json.load(open(IN_PATH))
    captured_at = d.get("extraction_timestamp_utc")
    out = []

    for r in d.get("identifiers", []):
        ident_name = r.get("id")
        val = r.get("value_hex")
        if not val or not ident_name:
            continue
        # Split multi-value rows (comma-separated) into multiple observations
        candidates = [v.strip() for v in str(val).split(",")] if "," in str(val) and "/" not in str(val) else [str(val)]
        # Multi-UUID rows like apple_findmy_service_uuids
        if ident_name == "apple_findmy_service_uuids":
            candidates = [v.strip() for v in str(val).split(",")]
        for cv in candidates:
            ctype = ID_TO_TYPE.get(ident_name, "ble_protocol_byte")
            file_ = r.get("file")
            # Some rows use `lines` (plural list) rather than singular `line`;
            # use the first listed line so the URL still anchors a concrete location.
            line = r.get("line")
            if not line:
                lines = r.get("lines")
                if isinstance(lines, list) and lines:
                    line = lines[0]
            doc_url = f"{REPO_URL}/blob/main/{file_}#L{line}" if file_ and line else (
                f"{REPO_URL}/blob/main/{file_}" if file_ else REPO_URL
            )
            vendor = ID_TO_VENDOR.get(ident_name)
            # category: BLE-tracker class is closer to `gps_tracker` than `unknown` per §3.1
            category = "gps_tracker" if vendor else "unknown"
            ambig = ident_name in ("airtag_p224_pubkey_layout",)
            out.append({
                "source_id": SOURCE_ID,
                "source_url": doc_url,
                "candidate_identifier": cv,
                "candidate_type": ctype,
                "candidate_category": category,
                "candidate_manufacturer": vendor,
                "source_excerpt": trunc(f"{file_}:{line} {r.get('snippet') or r.get('context','')}"),
                "source_row_key": row_key(doc_url, ctype, cv),
                "raw_payload": json.dumps(r),
                "notes": {
                    "wave": "A_deferred_dir",
                    "mapper_slug": SLUG,
                    "mapper_run_id": "MAC-101 Item C Phase 1",
                    "shape_origin": "identifiers[]",
                    "ident_name": ident_name,
                    "cross_validates_with": r.get("cross_validates_with"),
                    "candidate_type_proposed": ctype in (
                        "ble_protocol_byte", "ble_protocol_byte_table",
                        "ble_payload_offset", "ble_adv_interval",
                    ),
                    "ambiguous_extraction": ambig,
                },
                "captured_at": captured_at,
            })

    # phase_6_behavioral_signatures.confidence_scoring_logic → 1 behavioral signature row
    bs = d.get("phase_6_behavioral_signatures", {}).get("confidence_scoring_logic", {})
    if bs.get("function"):
        fn = bs["function"]; file_ = bs.get("file"); line = bs.get("line")
        doc_url = f"{REPO_URL}/blob/main/{file_}#L{line}" if file_ and line else REPO_URL
        ctype = "behavioral_signature"
        out.append({
            "source_id": SOURCE_ID,
            "source_url": doc_url,
            "candidate_identifier": fn,
            "candidate_type": ctype,
            "candidate_category": "gps_tracker",
            "candidate_manufacturer": "Apple",
            "source_excerpt": trunc(f"{file_}:{line} {bs.get('scheme','')}"),
            "source_row_key": row_key(doc_url, ctype, fn),
            "raw_payload": json.dumps(bs),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "phase_6_behavioral_signatures.confidence_scoring_logic",
                "mac58_option_b": True,
                "phase_6_gate_lifted": True,
                "no_promotion_phase2": True,
                "lineage": bs.get("lineage"),
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
