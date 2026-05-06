"""MAC-26 Step-2.5b byte-level survey — Wave-A Step-2.5 first-party SDK corpus.

Per dispatch §"Byte-level survey (Step-2.5b — mirror of Step-1.5b methodology)":
- Mirror `scripts/mac23_step1_5b_survey.py` adapted for the
  `raw/github_step2_5/{run_ts}/cohort_A1_extension/` corpus path.
- Apply the codified disambig modules at survey time:
    * db/extraction/fcc_grantees_allowlist.py  (Ratification 1)
    * db/extraction/ble_uuid_disambig.py       (Ratification 2)
- Output: logs/mac25_step2_5b_byte_level_survey_{run_ts}.{txt,json}
  (filename per dispatch §15 — "mac25_" prefix, not "mac26_").
- Mirror MAC-23 Step-1.5b output schema for downstream tooling parity.
- Trip-line: ≥31 anchored unique hits = stop-the-line per dispatch §16.
- Zero-anchored outcome: §11 #1 absence-documented, no ExtractionWorker
  dispatch needed.

§7.x SourceWorker scope: survey is byte-level counting only, NOT extraction.
NO LLM. NO raw_observations writes. NO identifiers promotion.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root on path so db.extraction.* import works.
REPO_ROOT = Path("/home/kev/argus")
sys.path.insert(0, str(REPO_ROOT))
from db.extraction.fcc_grantees_allowlist import (  # type: ignore
    validate_fcc_id_match,
)
from db.extraction.ble_uuid_disambig import (  # type: ignore
    validate_ble_uuid_match,
)

# ─── Regex anchors (mirror Step-1.5b precedent verbatim) ──────────────────

REGEX_MAC = re.compile(r"\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b")
REGEX_BLE = re.compile(
    r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b"
)
REGEX_FCC_TIGHT = re.compile(r"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b")
REGEX_SSID = re.compile(r"\bssid\b", re.IGNORECASE)
DEFAULT_CRED_KW = (
    "default password", "default credential", "default login",
    "default user", "factory reset", "default passphrase",
    "wpa2 password", "default ssid",
)
ROLE_PREFIX_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sergeant|Sgt|Detective|Lt|Lieutenant|"
    r"Captain|Cpt|Officer|Trooper|Chief|Major|Colonel|General|Sheriff)\.?\s+"
    r"[A-Z][a-zA-Z'\-]{2,30}",
    re.IGNORECASE,
)

# Owner-slug → vendor mapping for the 11 repos in this dispatch.
VENDOR_MAP = {
    "cradlepoint": "Cradlepoint",
    "sierrawireless": "Sierra Wireless",
    "dji-sdk": "DJI",
}

CONTEXT_WINDOW_CHARS = 50  # ±50ch vendor-proximity (Step-1.5b parity)


def vendor_tokens(vendor: str) -> list[str]:
    if not vendor or vendor == "?":
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


def in_vendor_proximity(text_lower: str, m_start: int, m_end: int,
                         vendor: str) -> bool:
    toks = vendor_tokens(vendor)
    if not toks:
        return False
    win = text_lower[max(0, m_start - CONTEXT_WINDOW_CHARS):
                     m_end + CONTEXT_WINDOW_CHARS]
    return any(t in win for t in toks)


# ─── Per-file scan ───────────────────────────────────────────────────────


def scan_file(text: str, vendor: str) -> dict:
    """Return per-file counts + unique sets of disambig-passed identifiers."""
    text_l = text.lower()
    out = {
        "mac_anchored": 0,
        "ble_uuid_anchored_pre_disambig": 0,
        "ble_uuid_anchored_post_disambig": 0,
        "fcc_id_anchored_pre_disambig": 0,
        "fcc_id_anchored_post_disambig": 0,
        "ssid_kw": 0,
        "cred_kw": 0,
        "pii": 0,
        "unique_macs": set(),
        "unique_ble": set(),
        "unique_fcc": set(),
        "ble_disambig_drops": [],   # list of (uuid, reason)
        "fcc_disambig_drops": [],   # list of (fcc_id, reason)
    }

    # MAC: vendor-prox-gated
    for m in REGEX_MAC.finditer(text):
        if in_vendor_proximity(text_l, m.start(), m.end(), vendor):
            out["mac_anchored"] += 1
            out["unique_macs"].add(m.group().lower())

    # BLE UUID: regex hit → vendor-prox → disambig module
    for m in REGEX_BLE.finditer(text):
        if not in_vendor_proximity(text_l, m.start(), m.end(), vendor):
            continue
        out["ble_uuid_anchored_pre_disambig"] += 1
        ok, reason = validate_ble_uuid_match(
            m.group(), text=text,
            match_start=m.start(), match_end=m.end(),
        )
        if ok:
            out["ble_uuid_anchored_post_disambig"] += 1
            out["unique_ble"].add(m.group().lower())
        else:
            out["ble_disambig_drops"].append((m.group(), reason))

    # FCC ID: regex → vendor-prox → grantee-allowlist module
    for m in REGEX_FCC_TIGHT.finditer(text):
        if not in_vendor_proximity(text_l, m.start(), m.end(), vendor):
            continue
        out["fcc_id_anchored_pre_disambig"] += 1
        ok, reason = validate_fcc_id_match(m.group())
        if ok:
            out["fcc_id_anchored_post_disambig"] += 1
            out["unique_fcc"].add(m.group())
        else:
            out["fcc_id_anchored_post_disambig"] += 0
            out["fcc_disambig_drops"].append((m.group(), reason))

    out["ssid_kw"] = len(REGEX_SSID.findall(text))
    out["cred_kw"] = sum(text_l.count(k) for k in DEFAULT_CRED_KW)
    out["pii"] = len(ROLE_PREFIX_RE.findall(text))
    return out


# ─── Cohort walk ─────────────────────────────────────────────────────────


def walk_corpus(corpus_root: Path) -> dict:
    per_repo: dict[str, dict] = {}
    per_vendor: dict[str, dict] = defaultdict(lambda: {
        "files": 0, "bytes": 0,
        "mac_anchored": 0,
        "ble_uuid_anchored_pre_disambig": 0,
        "ble_uuid_anchored_post_disambig": 0,
        "fcc_id_anchored_pre_disambig": 0,
        "fcc_id_anchored_post_disambig": 0,
        "ssid_kw": 0, "cred_kw": 0, "pii": 0,
        "repos": set(),
    })
    cohort_agg = {
        "files": 0, "bytes": 0,
        "mac_anchored": 0,
        "ble_uuid_anchored_pre_disambig": 0,
        "ble_uuid_anchored_post_disambig": 0,
        "fcc_id_anchored_pre_disambig": 0,
        "fcc_id_anchored_post_disambig": 0,
        "ssid_kw": 0, "cred_kw": 0, "pii": 0,
    }
    unique_macs: set[str] = set()
    unique_ble: set[str] = set()
    unique_fcc: set[str] = set()
    ble_disambig_drops: list[dict] = []
    fcc_disambig_drops: list[dict] = []

    for repo_dir in sorted(corpus_root.iterdir()):
        if not repo_dir.is_dir():
            continue
        owner_slug = repo_dir.name.split("__", 1)[0].lower()
        vendor = VENDOR_MAP.get(owner_slug, "?")
        repo_rec = {
            "vendor": vendor,
            "files": 0, "bytes": 0,
            "mac_anchored": 0,
            "ble_uuid_anchored_pre_disambig": 0,
            "ble_uuid_anchored_post_disambig": 0,
            "fcc_id_anchored_pre_disambig": 0,
            "fcc_id_anchored_post_disambig": 0,
            "ssid_kw": 0, "cred_kw": 0, "pii": 0,
            "per_file": [],
        }
        for f in sorted(repo_dir.iterdir()):
            if not f.is_file():
                continue
            # Skip the API-response control files.
            if f.name.startswith("_") and f.suffix == ".json":
                continue
            try:
                txt = f.read_text(errors="replace")
            except Exception:
                continue
            sc = scan_file(txt, vendor)
            byte_count = len(txt.encode("utf-8", errors="replace"))
            repo_rec["files"] += 1
            repo_rec["bytes"] += byte_count
            for k in (
                "mac_anchored",
                "ble_uuid_anchored_pre_disambig",
                "ble_uuid_anchored_post_disambig",
                "fcc_id_anchored_pre_disambig",
                "fcc_id_anchored_post_disambig",
                "ssid_kw", "cred_kw", "pii",
            ):
                repo_rec[k] += sc[k]
                cohort_agg[k] += sc[k]
                per_vendor[vendor][k] += sc[k]
            cohort_agg["files"] += 1
            cohort_agg["bytes"] += byte_count
            per_vendor[vendor]["files"] += 1
            per_vendor[vendor]["bytes"] += byte_count
            per_vendor[vendor]["repos"].add(repo_dir.name)
            unique_macs |= sc["unique_macs"]
            unique_ble |= sc["unique_ble"]
            unique_fcc |= sc["unique_fcc"]
            for u, why in sc["ble_disambig_drops"]:
                ble_disambig_drops.append({
                    "uuid": u, "reason": why,
                    "file": str(f.relative_to(REPO_ROOT)),
                })
            for u, why in sc["fcc_disambig_drops"]:
                fcc_disambig_drops.append({
                    "fcc_id": u, "reason": why,
                    "file": str(f.relative_to(REPO_ROOT)),
                })
            repo_rec["per_file"].append({
                "name": f.name, "bytes": byte_count,
                **{k: sc[k] for k in (
                    "mac_anchored",
                    "ble_uuid_anchored_pre_disambig",
                    "ble_uuid_anchored_post_disambig",
                    "fcc_id_anchored_pre_disambig",
                    "fcc_id_anchored_post_disambig",
                    "ssid_kw", "cred_kw", "pii",
                )},
            })
        per_repo[repo_dir.name] = repo_rec

    return {
        "per_repo": per_repo,
        "per_vendor": {
            v: {**rec, "repos": sorted(rec["repos"])}
            for v, rec in per_vendor.items()
        },
        "cohort_aggregate": cohort_agg,
        "unique_anchored_post_disambig": {
            "mac": sorted(unique_macs),
            "ble_uuid": sorted(unique_ble),
            "fcc_id": sorted(unique_fcc),
        },
        "ble_disambig_drops_first50": ble_disambig_drops[:50],
        "fcc_disambig_drops_first50": fcc_disambig_drops[:50],
        "ble_disambig_drops_total": len(ble_disambig_drops),
        "fcc_disambig_drops_total": len(fcc_disambig_drops),
    }


# ─── Output writers ──────────────────────────────────────────────────────


def write_outputs(survey: dict, out_run_ts: str, corpus_run_ts: str) -> tuple[Path, Path]:
    out_dir = REPO_ROOT / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"mac25_step2_5b_byte_level_survey_{out_run_ts}.json"
    txt_path = out_dir / f"mac25_step2_5b_byte_level_survey_{out_run_ts}.txt"

    unique = survey["unique_anchored_post_disambig"]
    total_unique_anchored = (
        len(unique["mac"]) + len(unique["ble_uuid"]) + len(unique["fcc_id"])
    )
    cohort = survey["cohort_aggregate"]
    pre_total = (
        cohort["mac_anchored"]
        + cohort["ble_uuid_anchored_pre_disambig"]
        + cohort["fcc_id_anchored_pre_disambig"]
    )
    post_total = (
        cohort["mac_anchored"]
        + cohort["ble_uuid_anchored_post_disambig"]
        + cohort["fcc_id_anchored_post_disambig"]
    )

    trip_line_floor = 31    # dispatch §16 — ≥31 stops the line
    trip_line_tripped = total_unique_anchored >= trip_line_floor

    out = {
        "issue": "MAC-26",
        "phase": "4 / Wave-A / Step 2.5b byte-level survey (first-party SDK corpus)",
        "survey_run_ts": out_run_ts,
        "corpus_run_ts": corpus_run_ts,
        "corpus_root": f"raw/github_step2_5/{corpus_run_ts}/cohort_A1_extension",
        "methodology": {
            "regex_mac_anchored": (
                r"\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b "
                "+ vendor-proximity ±50ch"
            ),
            "regex_ble_uuid_anchored": (
                r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}"
                r"[0-9a-fA-F]{12}\b "
                "+ vendor-proximity ±50ch + ble_uuid_disambig.py "
                "(URL-context excluder + BLE-protocol-context includer)"
            ),
            "regex_fcc_id_anchored_TIGHTENED_per_MAC21_§9_11": (
                r"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b "
                "(mandatory hyphen) + vendor-proximity ±50ch + "
                "fcc_grantees_allowlist.py (stop-list + grantee-prefix gate)"
            ),
            "ssid_kw": "raw count of \\bssid\\b case-insensitive",
            "default_creds_kw": (
                "raw count of default-cred tokens "
                "(default password, factory reset, etc.)"
            ),
            "pii_role_prefix": (
                "§11 #3 + SAR-5 PII redaction count (count-not-name)"
            ),
            "vendor_proximity": (
                "first-word-token + ≥4-char-non-stopword vendor name "
                "within ±50ch window"
            ),
            "vendor_map": VENDOR_MAP,
        },
        "per_repo": survey["per_repo"],
        "per_vendor": survey["per_vendor"],
        "cohort_aggregate": cohort,
        "unique_anchored_post_disambig": unique,
        "unique_anchored_total_post_disambig": total_unique_anchored,
        "anchored_pre_disambig_total": pre_total,
        "anchored_post_disambig_total": post_total,
        "ble_disambig_drops": {
            "total": survey["ble_disambig_drops_total"],
            "first50": survey["ble_disambig_drops_first50"],
        },
        "fcc_disambig_drops": {
            "total": survey["fcc_disambig_drops_total"],
            "first50": survey["fcc_disambig_drops_first50"],
        },
        "trip_line_evaluation": {
            "floor_per_dispatch_§16": trip_line_floor,
            "observed_unique_anchored_post_disambig": total_unique_anchored,
            "tripped": trip_line_tripped,
            "zero_anchored_post_disambig": (post_total == 0),
            "verdict_per_dispatch_§17": (
                "ZERO-ANCHORED: A1 reverts to absence-documented per §11 #1 "
                "(no ExtractionWorker dispatch needed). Reassign in_review "
                "with absence-documentation comment."
                if post_total == 0
                else (
                    "STOP-THE-LINE: ≥31 unique anchored — A1 cohort needs "
                    "sub-shard splitting at extraction time."
                    if trip_line_tripped
                    else (
                        "WITHIN-BAND: 1 ≤ unique_anchored ≤ 30 — proceed to "
                        "A1 ExtractionWorker dispatch (separate MAC-N) "
                        "after CEO ratification."
                    )
                )
            ),
        },
    }

    json_path.write_text(json.dumps(out, indent=2, sort_keys=True, default=str))

    # Build txt summary (Step-1.5b parity)
    lines = []
    lines.append("MAC-26 Step-2.5b byte-level survey — Wave-A first-party SDK corpus")
    lines.append(f"Run: {out_run_ts}")
    lines.append(f"Corpus: {out['corpus_root']} (corpus run-ts {corpus_run_ts})")
    lines.append("")
    lines.append("=== PER-REPO (vendor-prox-gated, tightened regex, disambig applied) ===")
    lines.append(
        f"{'repo':<40} {'files':>5} {'bytes':>9} "
        f"{'mac':>4} {'bleP':>5} {'bleD':>5} {'fccP':>5} {'fccD':>5} "
        f"{'ssid':>5} {'cred':>5} {'pii':>4}"
    )
    for repo, r in sorted(out["per_repo"].items()):
        lines.append(
            f"{repo:<40} {r['files']:>5} {r['bytes']:>9} "
            f"{r['mac_anchored']:>4} "
            f"{r['ble_uuid_anchored_pre_disambig']:>5} "
            f"{r['ble_uuid_anchored_post_disambig']:>5} "
            f"{r['fcc_id_anchored_pre_disambig']:>5} "
            f"{r['fcc_id_anchored_post_disambig']:>5} "
            f"{r['ssid_kw']:>5} {r['cred_kw']:>5} {r['pii']:>4}"
        )
    lines.append("")
    lines.append("=== PER-VENDOR (cross-repo aggregate) ===")
    lines.append(
        f"{'vendor':<20} {'files':>5} {'bytes':>9} "
        f"{'mac':>4} {'bleP':>5} {'bleD':>5} {'fccP':>5} {'fccD':>5} "
        f"{'ssid':>5} {'cred':>5} {'pii':>4} {'repos':>5}"
    )
    for v, r in sorted(out["per_vendor"].items()):
        lines.append(
            f"{v:<20} {r['files']:>5} {r['bytes']:>9} "
            f"{r['mac_anchored']:>4} "
            f"{r['ble_uuid_anchored_pre_disambig']:>5} "
            f"{r['ble_uuid_anchored_post_disambig']:>5} "
            f"{r['fcc_id_anchored_pre_disambig']:>5} "
            f"{r['fcc_id_anchored_post_disambig']:>5} "
            f"{r['ssid_kw']:>5} {r['cred_kw']:>5} {r['pii']:>4} {len(r['repos']):>5}"
        )
    lines.append("")
    lines.append(
        f"COHORT-AGG: files={cohort['files']} bytes={cohort['bytes']} "
        f"mac={cohort['mac_anchored']} "
        f"ble_pre={cohort['ble_uuid_anchored_pre_disambig']} "
        f"ble_post={cohort['ble_uuid_anchored_post_disambig']} "
        f"fcc_pre={cohort['fcc_id_anchored_pre_disambig']} "
        f"fcc_post={cohort['fcc_id_anchored_post_disambig']} "
        f"ssid_kw={cohort['ssid_kw']} cred_kw={cohort['cred_kw']} "
        f"pii={cohort['pii']}"
    )
    lines.append("")
    lines.append(
        f"PRE-DISAMBIG anchored total (mac+ble+fcc): {pre_total}"
    )
    lines.append(
        f"POST-DISAMBIG anchored total (mac+ble+fcc): {post_total}"
    )
    lines.append(
        f"UNIQUE anchored POST-disambig: "
        f"mac={len(unique['mac'])} ble={len(unique['ble_uuid'])} "
        f"fcc={len(unique['fcc_id'])} → total={total_unique_anchored}"
    )
    lines.append("")
    lines.append("Unique anchored identifiers (vendor-prox-gated, disambig-passed):")
    lines.append(f"  mac:       {unique['mac']}")
    lines.append(f"  ble_uuid:  {unique['ble_uuid']}")
    lines.append(f"  fcc_id:    {unique['fcc_id']}")
    lines.append("")
    lines.append(
        f"BLE-disambig drops: {survey['ble_disambig_drops_total']} "
        f"(URL-excluder OR no_ble_protocol_anchor)"
    )
    lines.append(
        f"FCC-disambig drops: {survey['fcc_disambig_drops_total']} "
        f"(stop-list OR prefix_not_in_fcc_grantees)"
    )
    lines.append("")
    lines.append("=== TRIP-LINE EVALUATION (dispatch §§16–17) ===")
    lines.append(
        f"Floor: ≥{trip_line_floor} unique anchored post-disambig = stop-the-line"
    )
    lines.append(
        f"Observed: {total_unique_anchored} unique anchored post-disambig"
    )
    lines.append(
        f"Trip-line tripped: {trip_line_tripped}"
    )
    lines.append(
        f"Zero-anchored: {(post_total == 0)}"
    )
    lines.append(f"Verdict: {out['trip_line_evaluation']['verdict_per_dispatch_§17']}")
    txt_path.write_text("\n".join(lines) + "\n")
    return json_path, txt_path


# ─── CLI entry ───────────────────────────────────────────────────────────


def _main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "MAC-26 Step-2.5b byte-level survey driver — mirror of "
            "Step-1.5b methodology, applies fcc_grantees_allowlist + "
            "ble_uuid_disambig modules at survey time."
        )
    )
    p.add_argument(
        "--corpus-run-ts", required=True,
        help=(
            "Corpus run timestamp (e.g. '20260506T002813Z') — survey will "
            "walk raw/github_step2_5/{ts}/cohort_A1_extension/"
        ),
    )
    args = p.parse_args()

    corpus_root = (
        REPO_ROOT / "raw" / "github_step2_5" / args.corpus_run_ts
        / "cohort_A1_extension"
    )
    if not corpus_root.is_dir():
        print(f"REFUSED: corpus root not found: {corpus_root}",
              file=sys.stderr)
        return 2

    survey = walk_corpus(corpus_root)
    out_run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path, txt_path = write_outputs(survey, out_run_ts, args.corpus_run_ts)
    print(f"Wrote:\n  {json_path.relative_to(REPO_ROOT)}")
    print(f"  {txt_path.relative_to(REPO_ROOT)}")
    print()
    print(txt_path.read_text())
    return 0


if __name__ == "__main__":
    sys.exit(_main())
