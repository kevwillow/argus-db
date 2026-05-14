"""MAC-101 Item C Phase 1 mapper — eylonK14/IMSICatcherDetector (Wave-A 6β).

Shape: dict-of-typed-lists under `identifiers` key. Empty buckets skipped.
sources.id = 31 (pre-resolved per issue §2).
"""
import json, hashlib, os, sys

SLUG = "eylonK14_IMSICatcherDetector"
SOURCE_ID = 31
REPO_URL = "https://github.com/eylonK14/IMSICatcherDetector"
IN_PATH = f"raw/wave_a/{SLUG}/20260511T052945Z.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url: str, ctype: str, cident: str) -> str:
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s: str, n: int = 200) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def emit() -> list[dict]:
    d = json.load(open(IN_PATH))
    captured_at = d.get("timestamp_utc")
    out: list[dict] = []
    ids = d.get("identifiers", {})

    # frequency_band — 4 rows
    for r in ids.get("frequency_band", []):
        val = r.get("value")
        if not val:
            continue
        file_ = r.get("file"); line = r.get("line")
        doc_url = f"{REPO_URL}/blob/main/{file_}#L{line}" if file_ else REPO_URL
        ctype = "frequency_band"
        out.append({
            "source_id": SOURCE_ID,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "imsi_catcher",
            "candidate_manufacturer": None,
            "source_excerpt": trunc(f"{file_}:{line} {r.get('context','')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "identifiers.frequency_band[]",
                "candidate_type_proposed": True,
                "generation": r.get("generation"),
                "lens": r.get("lens"),
            },
            "captured_at": captured_at,
        })

    # protocol_filter_field — 7 rows (Wireshark display filter strings)
    for r in ids.get("protocol_filter_field", []):
        val = r.get("value")
        if not val:
            continue
        file_ = r.get("file"); line = r.get("line")
        doc_url = f"{REPO_URL}/blob/main/{file_}#L{line}" if file_ else REPO_URL
        ctype = "wireshark_field"
        out.append({
            "source_id": SOURCE_ID,
            "source_url": doc_url,
            "candidate_identifier": val,
            "candidate_type": ctype,
            "candidate_category": "imsi_catcher",
            "candidate_manufacturer": None,
            "source_excerpt": trunc(f"{file_}:{line} {r.get('context','')}"),
            "source_row_key": row_key(doc_url, ctype, val),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "identifiers.protocol_filter_field[]",
                "candidate_type_proposed": True,
                "generation": r.get("generation"),
            },
            "captured_at": captured_at,
        })

    # behavioral_heuristic — 5 rows (per MAC-58 Option B; Phase 6 gate-lifted)
    for r in ids.get("behavioral_heuristic", []):
        name = r.get("name") or r.get("value")
        if not name:
            continue
        file_ = r.get("file"); line = r.get("line_range") or r.get("line")
        doc_url = f"{REPO_URL}/blob/main/{file_}#L{str(line).split('-')[0]}" if file_ else REPO_URL
        ctype = "behavioral_signature"
        out.append({
            "source_id": SOURCE_ID,
            "source_url": doc_url,
            "candidate_identifier": name,
            "candidate_type": ctype,
            "candidate_category": "imsi_catcher",
            "candidate_manufacturer": None,
            "source_excerpt": trunc(f"{file_}:{line} {r.get('logic','')}"),
            "source_row_key": row_key(doc_url, ctype, name),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "identifiers.behavioral_heuristic[]",
                "mac58_option_b": True,
                "phase_6_gate_lifted": True,
                "no_promotion_phase2": True,
                "lens": r.get("lens"),
                "generation": r.get("generation"),
                "marlin_correlation": r.get("marlin_correlation"),
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
