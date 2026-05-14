"""MAC-101 Item C Phase 1 mapper — FoggedLens/deflock-app (Wave-A 3c, AGPL-3.0).

Shape: G-17-lens structural; 11 alpr_model_candidates, 3 operator_profiles,
1 attribution_conflict_candidates entry (Motorola/Vigilant merge — re §8.4 audit-fidelity).
sources.id: CEO §2 disposition pending (recommended NEW row); reads SOURCE_ID env at run time.
"""
import json, hashlib, os

SLUG = "FoggedLens_deflock-app"
REPO_URL = "https://github.com/FoggedLens/deflock-app"
IN_PATH = f"raw/wave_a/{SLUG}/20260511T051115Z.json"
OUT_PATH = f"raw/wave_a/{SLUG}/_path_b_normalized.json"


def row_key(doc_url, ctype, cident):
    return hashlib.sha256(f"{doc_url}|{ctype}|{cident}".encode()).hexdigest()


def trunc(s, n=200):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def emit(source_id: int):
    d = json.load(open(IN_PATH))
    captured_at = d.get("extraction_timestamp_utc")
    head_sha = d.get("source_repo", {}).get("commit_sha")
    out = []

    # alpr_model_candidates — 11 rows
    for r in d.get("alpr_model_candidates", []):
        profile_id = r.get("profile_id")
        if not profile_id:
            continue
        prov = r.get("provenance", {})
        file_ = prov.get("file"); lines = prov.get("lines")
        doc_url = f"{REPO_URL}/blob/{head_sha}/{file_}#L{str(lines).split('-')[0]}" if head_sha and file_ else REPO_URL
        ctype = "alpr_model"  # existing identifier_type from migration 0014
        excerpt = f"{file_}:{lines} profile_id={profile_id} display_name='{r.get('display_name')}' manufacturer={r.get('candidate_manufacturer')} model={r.get('candidate_model')}"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": profile_id,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": r.get("candidate_manufacturer"),
            "source_excerpt": trunc(excerpt),
            "source_row_key": row_key(doc_url, ctype, profile_id),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "alpr_model_candidates[]",
                "display_name": r.get("display_name"),
                "candidate_model": r.get("candidate_model"),
                "candidate_kind": r.get("candidate_kind"),
                "osm_tags": r.get("osm_tags"),
                "submittable": r.get("submittable"),
                "requires_direction": r.get("requires_direction"),
                "argus_manufacturer_match": r.get("argus_manufacturer_match"),
                "validator_flag": r.get("validator_flag"),
            },
            "captured_at": captured_at,
        })

    # operator_profiles — 3 rows (NEW identifier_type: operator_profile — flag for Validator)
    for r in d.get("operator_profiles", []):
        profile_id = r.get("profile_id")
        if not profile_id:
            continue
        prov = r.get("provenance", {})
        file_ = prov.get("file"); lines = prov.get("lines")
        doc_url = f"{REPO_URL}/blob/{head_sha}/{file_}#L{str(lines).split('-')[0]}" if head_sha and file_ else REPO_URL
        ctype = "operator_profile"
        excerpt = f"{file_}:{lines} profile_id={profile_id} operator='{r.get('operator_name')}' wikidata_qid={r.get('wikidata_qid')}"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": profile_id,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": None,
            "source_excerpt": trunc(excerpt),
            "source_row_key": row_key(doc_url, ctype, profile_id),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "operator_profiles[]",
                "candidate_type_proposed": True,
                "operator_name": r.get("operator_name"),
                "wikidata_qid": r.get("wikidata_qid"),
                "operator_type": r.get("operator_type"),
                "argus_operator_match": r.get("argus_operator_match"),
            },
            "captured_at": captured_at,
        })

    # attribution_conflict_candidates — 1 row (audit-fidelity flag per §8.4)
    for r in d.get("attribution_conflict_candidates", []):
        conflict_label = r.get("conflict")
        if not conflict_label:
            continue
        ctype = "attribution_conflict"
        doc_url = f"{REPO_URL}#attribution_conflict_candidates"
        out.append({
            "source_id": source_id,
            "source_url": doc_url,
            "candidate_identifier": conflict_label,
            "candidate_type": ctype,
            "candidate_category": "alpr",
            "candidate_manufacturer": None,
            "source_excerpt": trunc(f"attribution_conflict: {conflict_label}"),
            "source_row_key": row_key(doc_url, ctype, conflict_label),
            "raw_payload": json.dumps(r),
            "notes": {
                "wave": "A_deferred_dir",
                "mapper_slug": SLUG,
                "mapper_run_id": "MAC-101 Item C Phase 1",
                "shape_origin": "attribution_conflict_candidates[]",
                "candidate_type_proposed": True,
                "no_promotion_phase2": True,
                "deflock_app_position": r.get("deflock_app_position"),
                "argus_position": r.get("argus_position"),
                "audit_fidelity_class": True,
                "agent_asserted_history_verify_per_memory": True,
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
