"""MAC-101 Item C Phase 1 mapper — RUB-SysSec/DroneSecurity (Wave-A 4d; NDSS DJI Drone-ID academic).

Shape: ALREADY canonical-flat `raw_observations` (76 rows). Pass through with provenance
wrapping (assign source_id, source_row_key) and notes augmentation.
sources.id: CEO §2 disposition pending (recommended NEW row, AGPL-3.0); reads SOURCE_ID env at run time.
"""
import json, hashlib, os

SLUG = "RUB-SysSec_DroneSecurity"
REPO_URL = "https://github.com/RUB-SysSec/DroneSecurity"
IN_PATH = f"raw/wave_a/{SLUG}/2026-05-11T05-21-38Z.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url, ctype, cident):
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s, n=200):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def emit(source_id: int):
    d = json.load(open(IN_PATH))
    captured_at = d.get("extracted_at_utc")
    head_sha = d.get("source", {}).get("head_sha")
    ro = d.get("raw_observations", [])
    out = []
    for r in ro:
        val = r.get("candidate_identifier")
        ctype = r.get("identifier_type")
        if not val or not ctype:
            continue
        excerpt_raw = r.get("source_excerpt", "")
        # Derive doc_url from excerpt's leading "src/foo.py:LINE" if possible
        doc_url = REPO_URL
        if excerpt_raw and ":" in excerpt_raw.split()[0] and head_sha:
            anchor = excerpt_raw.split()[0]  # e.g. "src/droneid_receiver_live.py:147"
            if "/" in anchor and ":" in anchor:
                fpath, _, lineno = anchor.rpartition(":")
                if lineno.isdigit():
                    doc_url = f"{REPO_URL}/blob/{head_sha}/{fpath}#L{lineno}"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": r.get("candidate_category") or "drone",
            "candidate_manufacturer": r.get("candidate_manufacturer"),
            "source_excerpt": trunc(excerpt_raw),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "raw_observations[] (already canonical Path B)",
                "obs_id": r.get("obs_id"),
                "rub_notes_passthrough": r.get("notes"),
                "academic_class": True,
                "license_spdx": "AGPL-3.0-only",
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
