"""MAC-25 Step-2.0 — Pre-filter regression spot-check (Ratifications 1+2).

Per MAC-25 dispatch §12: re-run tightened regex against Wave-A Step-1.5b
corpus with codified disambig disciplines applied; expected outcome =
the 6 ble_uuid_unique + 2 fcc_id_unique drop to 0 (all FP-class).

If any survive disambig, surface deviation for CEO ratification BEFORE
A2 extraction fires.

Re-uses:
- mac23_step1_5b_survey regex shapes (REGEX_BLE, REGEX_FCC_TIGHT)
- mac23_step1_5b_survey vendor-proximity gate (vp_count)
- db.extraction.fcc_grantees_allowlist.validate_fcc_id_match
- db.extraction.ble_uuid_disambig.validate_ble_uuid_match
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from db.extraction.ble_uuid_disambig import validate_ble_uuid_match
from db.extraction.fcc_grantees_allowlist import validate_fcc_id_match

REGEX_BLE = re.compile(
    r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b"
)
REGEX_FCC_TIGHT = re.compile(r"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b")
REGEX_MAC = re.compile(r"\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b")

# Vendor map from mac23_step1_5b_survey.build_vendor_map (mirrored verbatim
# for parity).
VMAP = {
    "cradlepoint": "Cradlepoint", "sierrawireless": "Sierra Wireless",
    "motorolasolutions": "Motorola Solutions", "flocksafety": "Flock Safety",
    "dji-sdk": "DJI", "hak5": "Hak5", "watchguard": "WatchGuard",
    "parrot-developers": "Parrot", "skydio": "Skydio",
    "magnetforensics": "Magnet Forensics", "genetec": "Genetec",
    "axiscommunications": "Axis Communications", "l3harris": "L3Harris",
    "clearviewai": "Clearview AI", "avigilon": "Avigilon",
    "briefcam": "BriefCam", "soundthinking": "SoundThinking",
    "rekorai": "Rekor", "brinc-drones": "BRINC",
    "0xxyc": "Flock Safety", "f1yaw4y": "Flock Safety",
    "gainsec": "Flock Safety", "deflockyourcity": "Flock Safety",
    "zmattmanz": "Flock Safety",
    "vegantransistor": "Cradlepoint",
    "danielewood": "Sierra Wireless", "bkerler": "Sierra Wireless",
    "smcl": "Sierra Wireless",
    "o-gs": "DJI", "damiafuentes": "DJI",
    "levlesec": "Cellebrite", "dfirscience": "Cellebrite",
    "danielorf": "Axis Communications", "trunnion": "Axis Communications",
    "facelessg00n": "Berla",
    "i-am-jakoby": "Hak5", "aleff-github": "Hak5",
}

WAVE_ROOT = REPO_ROOT / "raw" / "github" / "20260505T200235Z"


def vendor_tokens(vendor: str) -> list[str]:
    if not vendor:
        return []
    parts = vendor.lower().split()
    out = [parts[0]] if parts else []
    for p in parts[1:]:
        if len(p) >= 4 and p not in (
            "safety", "wireless", "communications", "solutions",
            "forensics", "thinking",
        ):
            out.append(p)
    return out


def in_vendor_proximity(text: str, match_start: int, match_end: int, vendor: str) -> bool:
    toks = vendor_tokens(vendor)
    if not toks:
        return False
    win = text[max(0, match_start - 50):match_end + 50].lower()
    return any(t in win for t in toks)


def _scan(
    txt_clean: str,
    vendor: str,
    f: Path,
    c_ble_pre: set,
    c_ble_post: set,
    c_fcc_pre: set,
    c_fcc_post: set,
    c_drop_reasons: dict,
    c_kept_examples: dict,
    wave_ble_pre: set,
    wave_ble_post: set,
    wave_fcc_pre: set,
    wave_fcc_post: set,
    wave_drop_reasons: dict,
) -> None:
    """Apply BLE + FCC regex with vendor-proximity then disambig disciplines."""
    for m in REGEX_BLE.finditer(txt_clean):
        if not in_vendor_proximity(txt_clean, m.start(), m.end(), vendor):
            continue
        uid = m.group(0).lower()
        c_ble_pre.add(uid)
        wave_ble_pre.add(uid)
        ok, reason = validate_ble_uuid_match(
            uid, text=txt_clean,
            match_start=m.start(), match_end=m.end(),
        )
        if ok:
            c_ble_post.add(uid)
            wave_ble_post.add(uid)
            if len(c_kept_examples["ble"]) < 3:
                c_kept_examples["ble"].append({
                    "uuid": uid,
                    "vendor": vendor,
                    "file": str(f.relative_to(REPO_ROOT)),
                    "reason": reason,
                    "context_excerpt": txt_clean[
                        max(0, m.start() - 60):m.end() + 60
                    ][:200],
                })
        else:
            c_drop_reasons[f"ble:{reason}"] += 1
            wave_drop_reasons[f"ble:{reason}"] += 1

    for m in REGEX_FCC_TIGHT.finditer(txt_clean):
        if not in_vendor_proximity(txt_clean, m.start(), m.end(), vendor):
            continue
        fid = m.group(0)
        c_fcc_pre.add(fid)
        wave_fcc_pre.add(fid)
        ok, reason = validate_fcc_id_match(fid)
        if ok:
            c_fcc_post.add(fid)
            wave_fcc_post.add(fid)
            if len(c_kept_examples["fcc"]) < 3:
                c_kept_examples["fcc"].append({
                    "fcc_id": fid,
                    "vendor": vendor,
                    "file": str(f.relative_to(REPO_ROOT)),
                    "reason": reason,
                    "context_excerpt": txt_clean[
                        max(0, m.start() - 60):m.end() + 60
                    ][:200],
                })
        else:
            c_drop_reasons[f"fcc:{reason}"] += 1
            wave_drop_reasons[f"fcc:{reason}"] += 1


def main() -> int:
    cohort_dirs = sorted(
        [p for p in WAVE_ROOT.iterdir() if p.is_dir() and p.name.startswith("cohort_")]
    )
    # Augment VMAP from A4 cohort summary the same way Step-1.5b survey did
    # (so pre-counts reproduce the baseline 6 ble_uuid + 2 fcc_id).
    for c in cohort_dirs:
        s_path = c / "_cohort_summary.json"
        if not s_path.exists():
            continue
        try:
            s = json.loads(s_path.read_text())
        except Exception:
            continue
        for v, rec in s.get("vendors", {}).items():
            repos = rec.get("repos_fetched", []) if isinstance(rec, dict) else []
            if not isinstance(repos, list):
                continue
            for r in repos:
                if "repo" in r and "skipped" not in r:
                    owner = r["repo"].split("/", 1)[0].lower()
                    if owner not in VMAP:
                        VMAP[owner] = v

    # Tracked per cohort + wave-aggregate
    out: dict = {
        "run_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "wave_root": str(WAVE_ROOT.relative_to(REPO_ROOT)),
        "cohorts": {},
        "wave_aggregate": {},
        "step1_5b_baseline": {
            "ble_uuid_unique": [
                "2edd98e8-ffbc-4563-ac18-195382de3bce",
                "31ffe27e-667c-48ff-8a14-8029d44dfb66",
                "382e30a0-10c0-4ab0-88b4-db27e9331a23",
                "6f2a02e9-1e43-4820-bad1-905631856dc2",
                "b660370d-bc6e-4410-b8e4-0f8d48daffaf",
                "d3590ed6-52b3-4102-aeff-aad2292ab01c",
            ],
            "fcc_id_unique": ["CVE-2025", "NON-INFRINGEMENT"],
        },
    }

    wave_ble_pre: set[str] = set()
    wave_ble_post: set[str] = set()
    wave_fcc_pre: set[str] = set()
    wave_fcc_post: set[str] = set()
    wave_drop_reasons: dict[str, int] = defaultdict(int)
    wave_kept_examples: dict[str, list[dict]] = {"ble": [], "fcc": []}

    for cdir in cohort_dirs:
        cname = cdir.name
        c_ble_pre: set[str] = set()
        c_ble_post: set[str] = set()
        c_fcc_pre: set[str] = set()
        c_fcc_post: set[str] = set()
        c_drop_reasons: dict[str, int] = defaultdict(int)
        c_kept_examples: dict[str, list[dict]] = {"ble": [], "fcc": []}
        c_files = 0
        c_bytes = 0

        # Mirror Step-1.5b survey methodology exactly so pre-counts reproduce
        # the baseline:
        #   - A5: nested <vendor>/<kw>/issues_search.json — read items[*]
        #         title+body[:1000], NO tag-strip, NO whitespace-collapse.
        #   - A1-A4: <owner>__<repo>/<files>; skip *.json; non-recursive
        #         iterdir; raw text via read_text(errors='replace').
        for entry in cdir.iterdir():
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            if cname == "cohort_A5":
                vslug = entry.name  # vendor folder
                vendor = {
                    "cradlepoint": "Cradlepoint",
                    "sierra_wireless": "Sierra Wireless",
                    "motorola_solutions": "Motorola Solutions",
                    "flock_safety": "Flock Safety",
                }.get(vslug, "")
                for v_sub in entry.iterdir():
                    if not v_sub.is_dir():
                        continue
                    for f in v_sub.iterdir():
                        if not f.is_file() or f.suffix != ".json":
                            continue
                        try:
                            d = json.loads(f.read_text())
                        except Exception:
                            continue
                        items = d.get("items", []) if isinstance(d, dict) else []
                        for it in items:
                            corpus = (it.get("title", "") or "") + " " + (
                                it.get("body", "") or ""
                            )[:1000]
                            c_files += 1
                            c_bytes += len(corpus)
                            _scan(
                                corpus, vendor, f,
                                c_ble_pre, c_ble_post, c_fcc_pre, c_fcc_post,
                                c_drop_reasons, c_kept_examples,
                                wave_ble_pre, wave_ble_post,
                                wave_fcc_pre, wave_fcc_post, wave_drop_reasons,
                            )
                continue
            # A1-A4 path
            owner_slug = entry.name.split("__", 1)[0]
            vendor = VMAP.get(owner_slug.lower(), "")
            for f in entry.iterdir():
                if not f.is_file() or f.suffix == ".json":
                    continue
                try:
                    txt_clean = f.read_text(errors="replace")
                except Exception:
                    continue
                c_files += 1
                c_bytes += len(txt_clean)

                _scan(
                    txt_clean, vendor, f,
                    c_ble_pre, c_ble_post, c_fcc_pre, c_fcc_post,
                    c_drop_reasons, c_kept_examples,
                    wave_ble_pre, wave_ble_post,
                    wave_fcc_pre, wave_fcc_post, wave_drop_reasons,
                )

        out["cohorts"][cname] = {
            "files_seen": c_files,
            "bytes_seen": c_bytes,
            "ble_uuid_pre_count_unique": len(c_ble_pre),
            "ble_uuid_post_count_unique": len(c_ble_post),
            "ble_uuid_pre_unique_list": sorted(c_ble_pre),
            "ble_uuid_post_unique_list": sorted(c_ble_post),
            "fcc_id_pre_count_unique": len(c_fcc_pre),
            "fcc_id_post_count_unique": len(c_fcc_post),
            "fcc_id_pre_unique_list": sorted(c_fcc_pre),
            "fcc_id_post_unique_list": sorted(c_fcc_post),
            "drop_reasons": dict(c_drop_reasons),
            "kept_examples": c_kept_examples,
        }

    out["wave_aggregate"] = {
        "ble_uuid_pre_count_unique": len(wave_ble_pre),
        "ble_uuid_post_count_unique": len(wave_ble_post),
        "ble_uuid_pre_unique_list": sorted(wave_ble_pre),
        "ble_uuid_post_unique_list": sorted(wave_ble_post),
        "fcc_id_pre_count_unique": len(wave_fcc_pre),
        "fcc_id_post_count_unique": len(wave_fcc_post),
        "fcc_id_pre_unique_list": sorted(wave_fcc_pre),
        "fcc_id_post_unique_list": sorted(wave_fcc_post),
        "drop_reasons": dict(wave_drop_reasons),
    }

    # Compare against Step-1.5b baseline.
    pre_ble_match = (
        sorted(wave_ble_pre)
        == sorted(out["step1_5b_baseline"]["ble_uuid_unique"])
    )
    pre_fcc_match = (
        sorted(wave_fcc_pre)
        == sorted(out["step1_5b_baseline"]["fcc_id_unique"])
    )
    out["pre_filter_baseline_ble_match"] = pre_ble_match
    out["pre_filter_baseline_fcc_match"] = pre_fcc_match
    out["disambig_outcome"] = {
        "expected_ble_post": 0,
        "actual_ble_post": len(wave_ble_post),
        "ble_test_pass": len(wave_ble_post) == 0,
        "expected_fcc_post": 0,
        "actual_fcc_post": len(wave_fcc_post),
        "fcc_test_pass": len(wave_fcc_post) == 0,
    }

    # Persist artifact
    out_dir = REPO_ROOT / "logs"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"mac25_step2_0_disambig_regression_{out['run_ts'].replace(':','').replace('-','')}.json"
    out_path.write_text(json.dumps(out, indent=2))

    # Console summary
    print(f"=== MAC-25 Step-2.0 disambig regression ({out['run_ts']}) ===")
    print(f"Wave aggregate ble_uuid: pre={len(wave_ble_pre)} post={len(wave_ble_post)}")
    print(f"  pre  : {sorted(wave_ble_pre)}")
    print(f"  post : {sorted(wave_ble_post)}")
    print(f"Wave aggregate fcc_id : pre={len(wave_fcc_pre)} post={len(wave_fcc_post)}")
    print(f"  pre  : {sorted(wave_fcc_pre)}")
    print(f"  post : {sorted(wave_fcc_post)}")
    print(f"Drop reasons: {dict(wave_drop_reasons)}")
    print(f"Pre-filter BLE matches Step-1.5b baseline: {pre_ble_match}")
    print(f"Pre-filter FCC matches Step-1.5b baseline: {pre_fcc_match}")
    print(f"Disambig outcome: ble_pass={out['disambig_outcome']['ble_test_pass']} "
          f"fcc_pass={out['disambig_outcome']['fcc_test_pass']}")
    print(f"Artifact: {out_path.relative_to(REPO_ROOT)}")
    return 0 if (
        out["disambig_outcome"]["ble_test_pass"]
        and out["disambig_outcome"]["fcc_test_pass"]
    ) else 1


if __name__ == "__main__":
    sys.exit(main())
