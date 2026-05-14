"""MAC-101 Item C Phase 1 mapper — EthanThePhoenix38/flock-you-camera-detector (Wave-A 2a fork).

Shape: fork-delta; 20 active MAC OUI prefixes + 6 potentially-novel-vs-upstream OUIs.
Commented-out prefixes are EXCLUDED (they are explicitly disabled in fork's main.cpp).
sources.id: CEO §2 disposition pending (recommended NEW row); reads SOURCE_ID env at run time.
"""
import json, hashlib, os

SLUG = "EthanThePhoenix38_flock-you-camera-detector"
REPO_URL = "https://github.com/EthanThePhoenix38/flock-you-camera-detector"
IN_PATH = f"raw/wave_a/{SLUG}/2026-05-11T05-20-00Z.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url, ctype, cident):
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s, n=200):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def emit(source_id: int):
    d = json.load(open(IN_PATH))
    captured_at = d.get("extraction_ts_utc")
    head_sha = d.get("repo", {}).get("head_sha")
    inv = d.get("fork_main_cpp_identifier_inventory", {})
    novel = d.get("net_new_identifiers_vs_2a_extraction", {}).get("potentially_novel_oui_signal", {})
    novel_ouis = set(o.lower() for o in novel.get("ouis", []) or [])

    out = []
    doc_url_base = f"{REPO_URL}/blob/{head_sha}/src/main.cpp" if head_sha else f"{REPO_URL}/blob/main/src/main.cpp"

    for prefix in inv.get("active_mac_prefixes_array", []):
        ctype = "mac_oui"
        cv = prefix.lower()
        is_novel = cv in novel_ouis
        out.append({
            "source_id": source_id,
            "source_url": doc_url_base,
            "candidate_identifier": cv,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": None,
            "source_excerpt": trunc(f"src/main.cpp active_mac_prefixes_array[] entry: {prefix}"),
            "source_row_key": row_key(doc_url_base, ctype, cv),
            "raw_payload": json.dumps({"prefix": prefix, "active": True, "is_novel_vs_upstream_active": is_novel}),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "fork_main_cpp_identifier_inventory.active_mac_prefixes_array",
                "fork_disposition": "Wave-A 2a fork of colonelpanichacks/flock-you; 20 active OUIs; 13 confirmed-overlap with upstream, 7 not in upstream's active set",
                "is_potentially_novel_vs_upstream_active": is_novel,
                "corroboration_class": "fork_active_oui_in_upstream" if not is_novel else "fork_active_oui_not_in_upstream_active",
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
