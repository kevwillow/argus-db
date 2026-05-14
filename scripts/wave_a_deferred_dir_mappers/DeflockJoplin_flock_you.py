"""MAC-101 Item C Phase 1 mapper — DeflockJoplin/flock-you (Wave-A 2a fork).

Shape: diff-against-upstream; 3 net-new full-MAC observations under net_new_identifiers[].
sources.id: CEO §2 disposition pending (recommended NEW row); reads SOURCE_ID env at run time.
"""
import json, hashlib, os

SLUG = "DeflockJoplin_flock-you"
REPO_URL = "https://github.com/DeflockJoplin/flock-you"
IN_PATH = f"raw/wave_a/{SLUG}/20260511T052214Z.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url, ctype, cident):
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s, n=200):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def emit(source_id: int):
    d = json.load(open(IN_PATH))
    captured_at = d.get("extraction_ts_utc")
    out = []
    head_sha = d.get("repo", {}).get("sha")

    for r in d.get("net_new_identifiers", []):
        mac = r.get("wireless_identifier")
        if not mac:
            continue
        raw_src = r.get("raw_source") or ""  # e.g. "api/data/cumulative_detections.pkl id=1"
        repo_file_part = raw_src.split(" ")[0] if raw_src else ""
        doc_url = f"{REPO_URL}/blob/{head_sha}/{repo_file_part}" if head_sha and repo_file_part else REPO_URL
        ctype = "mac"
        # LA-bit penalty per SAR-1: la_bit==1 → cap confidence ≤ 40 in Phase 2 notes
        la_bit_set = bool(r.get("la_bit"))
        excerpt = f"net_new_identifiers[]: {mac} oui={r.get('oui')} vendor={r.get('vendor_per_capture')} hits={r.get('hit_count')} duration={r.get('duration_s')}s"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": mac,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": r.get("vendor_per_capture"),
            "source_excerpt": trunc(excerpt),
            "source_row_key": row_key(doc_url, ctype, mac),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "net_new_identifiers[]",
                "oui": r.get("oui"),
                "la_bit": r.get("la_bit"),
                "ig_bit": r.get("ig_bit"),
                "la_bit_class": r.get("la_bit_class"),
                "lab_bit_set_penalty_phase2": la_bit_set,
                "detection_method": r.get("detection_method"),
                "ssid": r.get("ssid"),
                "hit_count": r.get("hit_count"),
                "rssi_first": r.get("rssi_first"),
                "rssi_last": r.get("rssi_last"),
                "duration_s": r.get("duration_s"),
                "channels": r.get("channels"),
                "first_seen_utc": r.get("first_seen_utc"),
                "last_seen_utc": r.get("last_seen_utc"),
                "argus_value": r.get("argus_value"),
                "confidence_hint": r.get("confidence"),
                "fork_disposition": "Wave-A 2a fork of colonelpanichacks/flock-you (id=20); 1 fork-signature MAC (82:6b:f2 31st OUI)",
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
