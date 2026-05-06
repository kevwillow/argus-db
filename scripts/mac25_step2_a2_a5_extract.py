"""MAC-25 Wave-A Step-2 A2 + A5 extraction driver.

Per CEO ratification of MAC-25 Step-2.0 (option (c)):
- A2 single-shard LLM extraction (4 yielding repos in cohort_A2 corpus,
  ~138KB clean, projected ~3-12 staged rows; Mid 110 / trip ≤55)
- A5 per-vendor shards (17 issue-thread refs; comment-body fetch first
  via core endpoint ~50-100 calls, then per-vendor regex+LLM shards;
  projected ~0-5 staged rows; Mid 50 / trip ≤25)
- A3 + A4 absence-documented per §11 #1 (unconditional; corpus-shape-zero)

Architecture (binds verbatim per dispatch §6 + MAC-18 ratified):
- Hybrid regex-first / LLM-second
- LLM under `claude_local` adapter — agent-context classification, no
  external Anthropic API call (per board-signed-off `bce8a0ab` 2026-05-05T14:00Z
  + `requirements-vendor-docs.txt` codification)
- Per-row confidence (§8.2 75-95 manufacturer_doc band)
- §11 #7 source_excerpt ≤200 chars (drop on overflow)
- §11 #8 NO promotion to identifiers — raw_observations ONLY
- §11 #14 source_type=manufacturer_doc, one sources row per yielding repo
- SAR-5 PII redaction at extraction time (count-not-name)
- Disambig disciplines (Ratifications 1+2) bind at regex pre-filter:
  ble_uuid_disambig + fcc_grantees_allowlist (codified in db.extraction.*)

This driver wraps `db.sources.vendor_docs` for cohort_A2 + cohort_A5
manifest shapes, applies post-regex disambig, hands candidates to the
LLM-in-context, then applies classifications.

Usage:
  # Build A2 manifest + run regex pass
  python scripts/mac25_step2_a2_a5_extract.py a2-regex-pass \\
      --out-candidates extraction_outputs/mac25/a2_candidates.json \\
      --out-drops      extraction_outputs/mac25/a2_drops.json

  # After LLM classifications.json is produced (in-context):
  python scripts/mac25_step2_a2_a5_extract.py a2-apply \\
      --candidates       extraction_outputs/mac25/a2_candidates.json \\
      --classifications  extraction_outputs/mac25/a2_classifications.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/home/kev/argus")
sys.path.insert(0, str(REPO_ROOT))

import hashlib
import re

from db.extraction.ble_uuid_disambig import validate_ble_uuid_match
from db.extraction.fcc_grantees_allowlist import validate_fcc_id_match
from db.sources import vendor_docs

WAVE_A_RUN_TS = "20260505T200235Z"
WAVE_A_ROOT = REPO_ROOT / "raw" / "github" / WAVE_A_RUN_TS

EXTRACTION_OUT_DIR = REPO_ROOT / "extraction_outputs" / "mac25"
A2_CANDIDATES_PATH = EXTRACTION_OUT_DIR / "a2_candidates.json"
A2_DROPS_PATH = EXTRACTION_OUT_DIR / "a2_drops.json"
A2_CLASSIFICATIONS_PATH = EXTRACTION_OUT_DIR / "a2_classifications.json"
A2_MANIFEST_PATH = EXTRACTION_OUT_DIR / "a2_vendor_docs_manifest.json"


def build_vendor_docs_manifest_from_cohort_summary(
    cohort_dir: Path, cohort_name: str
) -> dict[str, Any]:
    """Translate a Wave-A cohort summary into vendor_docs-shape manifest.

    vendor_docs.run_regex_pass expects:
      manifest["cohorts"][cohort]["entries"] = [
        {"status": 200, "raw_path_relative": "...", "content_type": "...",
         "final_url": "...", "doc_url": "..."},
        ...
      ]
    """
    summary_path = cohort_dir / "_cohort_summary.json"
    summary = json.loads(summary_path.read_text())
    entries: list[dict[str, Any]] = []
    for repo in summary.get("repos", []):
        for f in repo.get("files", []):
            if f.get("kind") not in ("file",):
                continue
            if f.get("status") != 200:
                continue
            saved_to = f.get("saved_to")
            if not saved_to:
                continue
            entries.append({
                "status": 200,
                "raw_path_relative": saved_to,
                "content_type": f.get("content_type", ""),
                "final_url": f.get("final_url", "") or f.get("url", ""),
                "doc_url": f.get("final_url", "") or f.get("url", ""),
                "repo_full_name": repo.get("repo"),
                "vendor_target": repo.get("vendor_target"),
            })
    return {
        "cohorts": {
            cohort_name: {
                "entries": entries,
                "repos_count": len(summary.get("repos", [])),
                "files_count": len(entries),
                "vendor_targets": sorted({
                    repo.get("vendor_target")
                    for repo in summary.get("repos", [])
                    if repo.get("vendor_target")
                }),
            },
        },
    }


# ─── Wave-A vendor-proximity regex pass (mirrors MAC-23 Step-1.5b) ─────────
#
# vendor_docs.regex_pass_one_file uses keyword-anchor (±200ch window must
# contain `\b(?:mac\s*address|oui|hardware\s*address|bssid|...)\b`). This
# is too strict for Wave-A GitHub corpus where probe-emitter scanner logs
# write tokens like `MATCH(oui_flock)` (oui as a sub-token, not bare word).
#
# Wave-A regex pass uses the Step-1.5b methodology: vendor-proximity gate
# at ±50ch (vendor name token must appear in window). This matches the
# dispatch §13 projected surface ("regex pre-filter surfaces
# mac_unique=['e4:aa:ea:80:a1:9b']").
#
# Disambig disciplines (Ratifications 1+2) bind via post_filter_disambig.

REGEX_MAC = re.compile(r"\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b")
REGEX_BLE_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
REGEX_FCC_TIGHT = re.compile(r"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b")
REGEX_SSID_LINE = vendor_docs.SSID_LINE_RE
REGEX_SSID_QUOTED = vendor_docs.QUOTED_SSID_RE
REGEX_SSID_PRODUCT = vendor_docs.SSID_PRODUCT_PATTERN_RE
REGEX_CRED_VALUE = vendor_docs.CRED_VALUE_RE
REGEX_ROOT_AT = vendor_docs.ROOT_AT_RE


def vendor_tokens(vendor: str) -> list[str]:
    """Mirror MAC-23 Step-1.5b vendor token derivation."""
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
    """±50ch vendor-name proximity gate (Step-1.5b methodology)."""
    toks = vendor_tokens(vendor)
    if not toks:
        return False
    win = text[max(0, match_start - 50):match_end + 50].lower()
    return any(t in win for t in toks)


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def wave_a_regex_pass_one_file(
    *, cohort: str, file_relpath: str, doc_url: str,
    text: str, vendor: str,
) -> tuple[list[dict], list[dict]]:
    """Wave-A regex pass: vendor-proximity gating per Step-1.5b.

    Returns (candidates, drops) in vendor_docs Candidate-asdict shape.
    Disambig disciplines applied post-pass via post_filter_disambig.
    """
    candidates: list[dict] = []
    drops: list[dict] = []

    def _make(*, ident: str, pass_kind: str, suggested_type: str,
              match_start: int, match_end: int) -> None:
        if not in_vendor_proximity(text, match_start, match_end, vendor):
            drops.append({
                "kind": pass_kind, "reason": "no_vendor_proximity",
                "file": file_relpath, "offset": match_start,
                "ident_preview": ident[:60],
            })
            return
        excerpt, offset, overflow = vendor_docs._trim_excerpt(
            text, match_start, match_end
        )
        if not excerpt:
            drops.append({
                "kind": pass_kind, "reason": "excerpt_overflow",
                "file": file_relpath, "offset": match_start,
                "ident_preview": ident[:60],
            })
            return
        redacted_excerpt, hits = vendor_docs.redact_pii(excerpt)
        if len(redacted_excerpt) > vendor_docs.EXCERPT_MAX:
            drops.append({
                "kind": pass_kind, "reason": "post_redaction_overflow",
                "file": file_relpath, "offset": match_start,
                "ident_preview": ident[:60],
            })
            return
        cand_id = _hash_id(doc_url, pass_kind, ident, str(match_start))
        candidates.append({
            "candidate_id": cand_id,
            "cohort": cohort,
            "file_relpath": file_relpath,
            "doc_url": doc_url,
            "candidate_identifier": ident,
            "pass_kind": pass_kind,
            "suggested_candidate_type": suggested_type,
            "anchor_keyword": "vendor_proximity",
            "source_excerpt": redacted_excerpt,
            "excerpt_offset": offset,
            "excerpt_overflow_pretrim": overflow,
            "pii_hits": hits,
        })

    # MAC (vendor-prox-gated)
    for m in REGEX_MAC.finditer(text):
        _make(ident=m.group(0).lower(), pass_kind="mac_anchored",
              suggested_type="mac",
              match_start=m.start(), match_end=m.end())
    # BLE UUID (vendor-prox-gated; disambig disciplines applied post-pass)
    for m in REGEX_BLE_UUID.finditer(text):
        _make(ident=m.group(0).lower(), pass_kind="uuid_anchored",
              suggested_type="ble_uuid",
              match_start=m.start(), match_end=m.end())
    # FCC ID tight (vendor-prox-gated; allowlist applied post-pass)
    for m in REGEX_FCC_TIGHT.finditer(text):
        _make(ident=m.group(0), pass_kind="fcc_id_anchored",
              suggested_type="ble_uuid",  # placeholder; LLM reclassifies
              match_start=m.start(), match_end=m.end())
    # SSID line (self-anchoring keyword in match)
    for m in REGEX_SSID_LINE.finditer(text):
        _make(ident=m.group(1), pass_kind="ssid_line",
              suggested_type="ssid_exact",
              match_start=m.start(), match_end=m.end())
    # SSID product pattern (Pineapple_X4Y2 etc.)
    for m in REGEX_SSID_PRODUCT.finditer(text):
        _make(ident=m.group(0), pass_kind="ssid_product",
              suggested_type="ssid_pattern",
              match_start=m.start(), match_end=m.end())
    # SSID quoted ("connect to" / "join")
    for m in REGEX_SSID_QUOTED.finditer(text):
        _make(ident=m.group(1).strip(), pass_kind="ssid_quoted",
              suggested_type="ssid_exact",
              match_start=m.start(1), match_end=m.end(1))
    # Credential value
    for m in REGEX_CRED_VALUE.finditer(text):
        _make(ident=m.group(1), pass_kind="cred_value",
              suggested_type="device_fingerprint",
              match_start=m.start(), match_end=m.end())
    # root@host
    for m in REGEX_ROOT_AT.finditer(text):
        _make(ident=m.group(1), pass_kind="root_at",
              suggested_type="device_fingerprint",
              match_start=m.start(), match_end=m.end())
    return candidates, drops


def post_filter_disambig(candidates_raw: list[dict]) -> tuple[list[dict], list[dict]]:
    """Apply codified Ratifications 1+2 to regex-pass output.

    UUID-anchored candidates pass through validate_ble_uuid_match
    (URL-context exclusion + protocol-context inclusion at ±50ch).
    Returns (kept_candidates, additional_drops_with_reason).
    """
    kept: list[dict] = []
    drops: list[dict] = []
    for c in candidates_raw:
        kind = c.get("pass_kind")
        ident = c.get("candidate_identifier", "")
        text_excerpt = c.get("source_excerpt", "")
        try:
            idx = text_excerpt.lower().index(ident.lower())
        except ValueError:
            idx = 0
        if kind == "uuid_anchored":
            ok, reason = validate_ble_uuid_match(
                ident, text=text_excerpt,
                match_start=idx, match_end=idx + len(ident),
            )
            if ok:
                kept.append(c)
            else:
                drops.append({
                    "kind": "uuid_anchored",
                    "reason": f"disambig_drop:{reason}",
                    "ident_preview": ident[:60],
                    "candidate_id": c.get("candidate_id"),
                })
        elif kind == "fcc_id_anchored":
            ok, reason = validate_fcc_id_match(ident)
            if ok:
                kept.append(c)
            else:
                drops.append({
                    "kind": "fcc_id_anchored",
                    "reason": f"disambig_drop:{reason}",
                    "ident_preview": ident[:60],
                    "candidate_id": c.get("candidate_id"),
                })
        else:
            kept.append(c)
    return kept, drops


# ─── A2 regex pass ─────────────────────────────────────────────────────────


def cmd_a2_regex_pass(args: argparse.Namespace) -> int:
    """A2 cohort regex pass — Wave-A vendor-proximity methodology.

    Per dispatch §13: regex pre-filter expected to surface
    `mac_unique=['e4:aa:ea:80:a1:9b']` + ssid_kw + cred_kw. The Wave-B2
    keyword-anchor methodology in vendor_docs.regex_pass_one_file misses
    the dispatch-expected MAC because it lives in `MATCH(oui_flock)`
    tokens, not bare-word `oui` contexts. Wave-A uses Step-1.5b
    vendor-proximity gating mirrored here.
    """
    cohort_dir = WAVE_A_ROOT / "cohort_A2"
    EXTRACTION_OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = build_vendor_docs_manifest_from_cohort_summary(cohort_dir, "cohort_A2")
    A2_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

    all_cands: list[dict] = []
    all_drops: list[dict] = []
    files_seen = 0
    for entry in manifest["cohorts"]["cohort_A2"]["entries"]:
        rel = entry["raw_path_relative"]
        f = REPO_ROOT / rel
        if not f.exists() or f.stat().st_size == 0:
            continue
        text = vendor_docs.clean_text(
            f.read_bytes(), entry.get("content_type", ""), f
        )
        files_seen += 1
        cands, drops = wave_a_regex_pass_one_file(
            cohort="cohort_A2",
            file_relpath=rel,
            doc_url=entry.get("final_url") or entry.get("doc_url"),
            text=text,
            vendor=entry.get("vendor_target", ""),
        )
        all_cands.extend(cands)
        all_drops.extend(drops)

    # Apply codified Ratifications 1+2 (BLE UUID + FCC ID disambig)
    kept, additional_drops = post_filter_disambig(all_cands)
    A2_CANDIDATES_PATH.write_text(json.dumps(kept, indent=2))
    all_drops.extend(additional_drops)
    A2_DROPS_PATH.write_text(json.dumps(all_drops, indent=2))

    # Per-pass-kind breakdown
    from collections import Counter
    kept_by_kind = Counter(c["pass_kind"] for c in kept)
    drops_by_reason = Counter(d["reason"] for d in all_drops)

    summary = {
        "cohort": "cohort_A2",
        "files_seen": files_seen,
        "candidates_post_disambig": len(kept),
        "drops_total": len(all_drops),
        "disambig_additional_drops": len(additional_drops),
        "kept_by_pass_kind": dict(kept_by_kind),
        "drops_by_reason_top10": dict(drops_by_reason.most_common(10)),
        "candidates_path": str(A2_CANDIDATES_PATH.relative_to(REPO_ROOT)),
        "drops_path": str(A2_DROPS_PATH.relative_to(REPO_ROOT)),
        "manifest_path": str(A2_MANIFEST_PATH.relative_to(REPO_ROOT)),
    }
    print(json.dumps(summary, indent=2))
    return 0


# ─── A2 apply (after LLM classifications produced in-context) ─────────────


def cmd_a2_apply(args: argparse.Namespace) -> int:
    """Apply LLM classifications and stage to raw_observations.

    Per dispatch §14 / §11 #14: one `sources` row per yielding repo —
    NOT per cohort. We loop applies, one per yielding repo whose
    candidates have ≥1 keep=True classification.
    """
    cands = json.loads(A2_CANDIDATES_PATH.read_text())
    if args.classifications:
        classes = json.loads(Path(args.classifications).read_text())
    else:
        classes = json.loads(A2_CLASSIFICATIONS_PATH.read_text())

    # Group candidates by repo (doc_url first segment after raw.githubusercontent.com)
    by_repo: dict[str, list[dict]] = {}
    for c in cands:
        # doc_url shape: https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>
        u = c.get("doc_url", "")
        parts = u.replace("https://raw.githubusercontent.com/", "").split("/", 3)
        if len(parts) >= 2:
            repo_full = f"{parts[0]}/{parts[1]}"
        else:
            repo_full = u
        by_repo.setdefault(repo_full, []).append(c)

    classes_by_id = {c["candidate_id"]: c for c in classes}
    all_results: list[dict] = []
    db_path = REPO_ROOT / "db" / "argus.db"

    for repo, repo_cands in by_repo.items():
        # Skip repos with NO keeps (per §11 #14 — only stage `sources` row
        # for repos that actually yield).
        keeps_in_repo = [
            c for c in repo_cands
            if classes_by_id.get(c["candidate_id"], {}).get("keep")
        ]
        if not keeps_in_repo:
            print(f"SKIP repo={repo} — 0 keeps after LLM classification")
            continue

        # Stage candidates + classifications for this repo via vendor_docs.apply_classifications.
        repo_cands_path = EXTRACTION_OUT_DIR / f"a2_{repo.replace('/', '__')}_candidates.json"
        repo_class_path = EXTRACTION_OUT_DIR / f"a2_{repo.replace('/', '__')}_classifications.json"
        repo_cands_path.write_text(json.dumps(repo_cands, indent=2))
        repo_class_path.write_text(json.dumps(
            [classes_by_id[c["candidate_id"]] for c in repo_cands if c["candidate_id"] in classes_by_id],
            indent=2,
        ))
        result = vendor_docs.apply_classifications(
            candidates_path=repo_cands_path,
            classifications_path=repo_class_path,
            db_path=db_path,
            agent_id="1347736c-16de-444c-9b2c-434321c2b025",
            source_name=f"GitHub: {repo} (Wave-A A2 cohort)",
            source_url=f"https://github.com/{repo}",
            source_notes=(
                f"Wave-A Phase-4 Step-2 A2 cohort extraction. "
                f"Hybrid regex+LLM under claude_local. Disambig "
                f"(fcc_grantees_allowlist + ble_uuid_disambig) applied "
                f"at regex post-filter."
            ),
            run_notes_extra={
                "wave": "A",
                "cohort": "cohort_A2",
                "step": "Step-2 A2 ExtractionWorker (MAC-25)",
                "disambig_modules_codified": [
                    "db.extraction.fcc_grantees_allowlist (Ratification 1)",
                    "db.extraction.ble_uuid_disambig (Ratification 2)",
                ],
            },
        )
        result["repo"] = repo
        all_results.append(result)
        print(f"REPO repo={repo} run_id={result['run_id']} source_id={result['source_id']} "
              f"rows_staged={result['rows_staged']} pii_hits={result['pii_redaction_hits_total']}")

    out_path = EXTRACTION_OUT_DIR / "a2_apply_results.json"
    out_path.write_text(json.dumps(all_results, indent=2))
    print(f"--- {len(all_results)} repos staged; results → {out_path.relative_to(REPO_ROOT)} ---")
    return 0


# ─── A5 driver (issue-thread comment-body fetch + per-vendor regex+LLM) ───

import time
import urllib.error
import urllib.parse
import urllib.request
import ssl
from datetime import datetime, timezone

A5_RAW_DIR = REPO_ROOT / "raw" / "github_step2_a5"
A5_CANDIDATES_DIR = EXTRACTION_OUT_DIR / "a5_per_vendor"
A5_DEFAULT_BRANCH = "main"

CORE_MIN_GAP_S = 0.75
CORE_RL_BUFFER = 200
PACER_LEDGER = REPO_ROOT / "logs" / "github_pacer.json"
ENV_PATH = REPO_ROOT / ".env" / ".env"


def _load_pat() -> str:
    if not ENV_PATH.exists():
        raise RuntimeError(f"PAT env file missing: {ENV_PATH}")
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == "GITHUB_PAT":
            return v.strip().strip('"').strip("'")
    raise RuntimeError("GITHUB_PAT missing")


def _http_get_paced(url: str, pat: str) -> dict:
    """Single-shot paced core HTTP call. Returns dict with status/body/etc.

    Mirrors mac23_step1_wave_a_fetch.fetch_paced for the core bucket only.
    NO retries on 429/403-rate-limit (dispatch §3 #5).
    """
    # Pacer load
    state = json.loads(PACER_LEDGER.read_text())
    core = state["buckets"]["core"]
    now = datetime.now(timezone.utc)
    # Min-gap check
    if core.get("last_query_at_iso"):
        last = datetime.strptime(core["last_query_at_iso"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        elapsed = (now - last).total_seconds()
        if elapsed < CORE_MIN_GAP_S:
            time.sleep(CORE_MIN_GAP_S - elapsed)
    # RL buffer check
    if core.get("rl_remaining_last") is not None and core["rl_remaining_last"] <= CORE_RL_BUFFER:
        if core.get("rl_reset_last_iso"):
            try:
                reset = datetime.strptime(core["rl_reset_last_iso"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                wait = max(0, int((reset - now).total_seconds()) + 5)
                if wait > 0:
                    print(f"  [pacer] core RL_remaining={core['rl_remaining_last']} ≤ {CORE_RL_BUFFER}, sleeping {wait}s until reset")
                    time.sleep(min(wait, 300))
            except ValueError:
                pass
    # Fire
    headers = {
        "User-Agent": "ArgusExtractionWorker/0.1 (Phase4 Wave-A Step-2 A5 issue-thread fetch)",
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {pat}",
    }
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    t0 = time.time()
    rl_rem = None
    rl_reset_iso = None
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            body = r.read()
            hdr = dict(r.headers)
            rl_rem_raw = hdr.get("X-RateLimit-Remaining") or hdr.get("x-ratelimit-remaining")
            rl_reset_raw = hdr.get("X-RateLimit-Reset") or hdr.get("x-ratelimit-reset")
            if rl_rem_raw:
                rl_rem = int(rl_rem_raw)
            if rl_reset_raw:
                rl_reset_iso = datetime.fromtimestamp(int(rl_reset_raw), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            status = r.status
            elapsed = time.time() - t0
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        hdr = dict(e.headers) if hasattr(e, "headers") else {}
        rl_rem_raw = hdr.get("X-RateLimit-Remaining") or hdr.get("x-ratelimit-remaining")
        if rl_rem_raw:
            rl_rem = int(rl_rem_raw)
        rl_reset_raw = hdr.get("X-RateLimit-Reset") or hdr.get("x-ratelimit-reset")
        if rl_reset_raw:
            rl_reset_iso = datetime.fromtimestamp(int(rl_reset_raw), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = e.code
        elapsed = time.time() - t0
    # Pacer save
    state["buckets"]["core"] = {
        "last_query_at_iso": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "today_count": int(core.get("today_count", 0)) + 1,
        "all_time_count": int(core.get("all_time_count", 0)) + 1,
        "rl_remaining_last": rl_rem,
        "rl_reset_last_iso": rl_reset_iso,
    }
    state["wave_a_total_calls"] = int(state.get("wave_a_total_calls", 0)) + 1
    PACER_LEDGER.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    return {
        "status": status,
        "body": body,
        "rl_remaining": rl_rem,
        "rl_reset_iso": rl_reset_iso,
        "elapsed_s": round(elapsed, 3),
        "url": url,
    }


def cmd_a5_fetch_comments(args: argparse.Namespace) -> int:
    """Fetch issue-thread comment bodies via core API.

    Per dispatch §14: ~50-100 core calls expected. Inventory shows
    16 unique threads + ~441 total comments. With 100/page, ~18 fetches
    needed (most threads <100 comments, 2 threads need 2 pages).
    """
    A5_RAW_DIR.mkdir(parents=True, exist_ok=True)
    cohort_a5 = WAVE_A_ROOT / "cohort_A5"
    threads_seen: dict[tuple[str, int], dict] = {}
    for f in sorted(cohort_a5.rglob("issues_search.json")):
        vendor = f.parent.parent.name
        keyword = f.parent.name
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for it in (d.get("items") or []):
            repo = (it.get("repository_url") or "").replace("https://api.github.com/repos/", "")
            num = it.get("number")
            if not repo or num is None:
                continue
            key = (repo, num)
            if key in threads_seen:
                threads_seen[key]["keywords"].append(keyword)
                continue
            threads_seen[key] = {
                "vendor_search_slug": vendor,
                "keywords": [keyword],
                "repo_full_name": repo,
                "issue_number": num,
                "comments_url": it.get("comments_url"),
                "comments_n_expected": it.get("comments", 0),
                "title": it.get("title"),
                "body": it.get("body") or "",
                "state": it.get("state"),
            }
    print(f"[A5] {len(threads_seen)} unique threads inventoried")

    pat = _load_pat()
    fetch_log: list[dict] = []
    for (repo, num), th in threads_seen.items():
        # Slugify for path
        repo_slug = repo.replace("/", "__")
        thread_dir = A5_RAW_DIR / th["vendor_search_slug"] / repo_slug / f"issue_{num}"
        thread_dir.mkdir(parents=True, exist_ok=True)
        # Save the inventoried metadata + body up front
        (thread_dir / "_thread.json").write_text(json.dumps(th, indent=2))
        # Fetch comments — paginate /repos/{repo}/issues/{num}/comments?per_page=100&page=N
        page = 1
        while True:
            url = f"https://api.github.com/repos/{repo}/issues/{num}/comments?per_page=100&page={page}"
            print(f"  [fetch] {repo}#{num} page={page}")
            resp = _http_get_paced(url, pat)
            fname = thread_dir / f"comments_p{page:02d}.json"
            fname.write_bytes(resp["body"])
            fetch_log.append({
                "repo": repo, "issue_number": num, "page": page,
                "url": url, "status": resp["status"],
                "rl_remaining": resp["rl_remaining"], "rl_reset_iso": resp["rl_reset_iso"],
                "saved_to": str(fname.relative_to(REPO_ROOT)),
                "elapsed_s": resp["elapsed_s"],
            })
            if resp["status"] != 200:
                print(f"    !! status={resp['status']}; halting page loop")
                break
            try:
                items = json.loads(resp["body"])
                if len(items) < 100:
                    # Last page
                    break
            except Exception:
                break
            page += 1
            if page > 5:
                # Defensive cap; no thread should have >500 comments
                print(f"    !! page cap (5) reached")
                break

    log_path = A5_RAW_DIR / "_fetch_log.json"
    log_path.write_text(json.dumps(fetch_log, indent=2))
    print(f"[A5] {len(fetch_log)} fetches logged → {log_path.relative_to(REPO_ROOT)}")
    return 0


def cmd_a5_regex_pass(args: argparse.Namespace) -> int:
    """Regex pass over A5 corpus (issue body + all comment bodies)."""
    EXTRACTION_OUT_DIR.mkdir(parents=True, exist_ok=True)
    A5_CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)

    # Map vendor_search_slug → canonical vendor name
    VENDOR_MAP = {
        "cradlepoint": "Cradlepoint",
        "sierra_wireless": "Sierra Wireless",
        "motorola_solutions": "Motorola Solutions",
        "flock_safety": "Flock Safety",
    }

    per_vendor_cands: dict[str, list[dict]] = {v: [] for v in VENDOR_MAP.values()}
    per_vendor_drops: dict[str, list[dict]] = {v: [] for v in VENDOR_MAP.values()}

    for vendor_dir in sorted(A5_RAW_DIR.iterdir()):
        if not vendor_dir.is_dir():
            continue
        vendor_canonical = VENDOR_MAP.get(vendor_dir.name, vendor_dir.name)
        for repo_dir in sorted(vendor_dir.iterdir()):
            if not repo_dir.is_dir():
                continue
            for issue_dir in sorted(repo_dir.iterdir()):
                if not issue_dir.is_dir():
                    continue
                thread_meta_path = issue_dir / "_thread.json"
                if not thread_meta_path.exists():
                    continue
                th = json.loads(thread_meta_path.read_text())
                # Concatenate issue body + all comment bodies
                texts: list[tuple[str, str]] = [("issue_body", th.get("body") or "")]
                for cf in sorted(issue_dir.glob("comments_p*.json")):
                    try:
                        comments = json.loads(cf.read_text())
                    except Exception:
                        continue
                    if not isinstance(comments, list):
                        continue
                    for cm in comments:
                        cb = cm.get("body") or ""
                        texts.append((f"comment#{cm.get('id', '?')}", cb))
                # Run Wave-A regex over each text segment
                rel_doc = f"https://github.com/{th['repo_full_name']}/issues/{th['issue_number']}"
                for source_label, text in texts:
                    if not text:
                        continue
                    cands, drops = wave_a_regex_pass_one_file(
                        cohort="cohort_A5",
                        file_relpath=str(thread_meta_path.relative_to(REPO_ROOT)) + f"#{source_label}",
                        doc_url=rel_doc,
                        text=text,
                        vendor=vendor_canonical,
                    )
                    per_vendor_cands[vendor_canonical].extend(cands)
                    per_vendor_drops[vendor_canonical].extend(drops)

    # Apply codified Ratifications 1+2 per vendor
    summary: dict = {}
    for vendor, cands in per_vendor_cands.items():
        kept, additional = post_filter_disambig(cands)
        per_vendor_drops[vendor].extend(additional)
        cands_path = A5_CANDIDATES_DIR / f"{vendor.replace(' ', '_').lower()}_candidates.json"
        drops_path = A5_CANDIDATES_DIR / f"{vendor.replace(' ', '_').lower()}_drops.json"
        cands_path.write_text(json.dumps(kept, indent=2))
        drops_path.write_text(json.dumps(per_vendor_drops[vendor], indent=2))
        summary[vendor] = {
            "candidates_post_disambig": len(kept),
            "drops_total": len(per_vendor_drops[vendor]),
            "candidates_path": str(cands_path.relative_to(REPO_ROOT)),
            "drops_path": str(drops_path.relative_to(REPO_ROOT)),
        }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_a5_apply(args: argparse.Namespace) -> int:
    """Apply per-vendor classifications to raw_observations + sources."""
    db_path = REPO_ROOT / "db" / "argus.db"
    all_results: list[dict] = []
    for vendor_slug in ("cradlepoint", "sierra_wireless", "motorola_solutions", "flock_safety"):
        cands_path = A5_CANDIDATES_DIR / f"{vendor_slug}_candidates.json"
        class_path = A5_CANDIDATES_DIR / f"{vendor_slug}_classifications.json"
        if not cands_path.exists() or not class_path.exists():
            continue
        cands = json.loads(cands_path.read_text())
        classes = json.loads(class_path.read_text())
        if not cands or not classes:
            print(f"SKIP vendor={vendor_slug} (no candidates or classifications)")
            continue
        # Group by repo (one sources row per yielding repo per §11 #14)
        classes_by_id = {c["candidate_id"]: c for c in classes}
        by_repo: dict[str, list[dict]] = {}
        for c in cands:
            doc_url = c.get("doc_url", "")
            # doc_url shape: https://github.com/<owner>/<repo>/issues/<n>
            parts = doc_url.replace("https://github.com/", "").split("/")
            repo_full = "/".join(parts[:2]) if len(parts) >= 2 else doc_url
            by_repo.setdefault(repo_full, []).append(c)
        for repo, repo_cands in by_repo.items():
            keeps = [c for c in repo_cands if classes_by_id.get(c["candidate_id"], {}).get("keep")]
            if not keeps:
                continue
            repo_cands_path = A5_CANDIDATES_DIR / f"{vendor_slug}_{repo.replace('/', '__')}_candidates.json"
            repo_class_path = A5_CANDIDATES_DIR / f"{vendor_slug}_{repo.replace('/', '__')}_classifications.json"
            repo_cands_path.write_text(json.dumps(repo_cands, indent=2))
            repo_class_path.write_text(json.dumps(
                [classes_by_id[c["candidate_id"]] for c in repo_cands if c["candidate_id"] in classes_by_id],
                indent=2,
            ))
            result = vendor_docs.apply_classifications(
                candidates_path=repo_cands_path,
                classifications_path=repo_class_path,
                db_path=db_path,
                agent_id="1347736c-16de-444c-9b2c-434321c2b025",
                source_name=f"GitHub: {repo} (Wave-A A5 cohort)",
                source_url=f"https://github.com/{repo}",
                source_notes=(
                    f"Wave-A Phase-4 Step-2 A5 issue-thread extraction. "
                    f"Hybrid regex+LLM under claude_local. "
                    f"vendor_search_slug={vendor_slug}."
                ),
                run_notes_extra={
                    "wave": "A", "cohort": "cohort_A5",
                    "step": "Step-2 A5 ExtractionWorker (MAC-25)",
                    "vendor_target": vendor_slug,
                    "disambig_modules_codified": [
                        "db.extraction.fcc_grantees_allowlist",
                        "db.extraction.ble_uuid_disambig",
                    ],
                },
            )
            result["repo"] = repo
            result["vendor_slug"] = vendor_slug
            all_results.append(result)
            print(f"REPO {vendor_slug}/{repo} run_id={result['run_id']} rows_staged={result['rows_staged']}")
    out_path = EXTRACTION_OUT_DIR / "a5_apply_results.json"
    out_path.write_text(json.dumps(all_results, indent=2))
    print(f"--- {len(all_results)} repos staged → {out_path.relative_to(REPO_ROOT)} ---")
    return 0


# ─── CLI ───────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("a2-regex-pass")
    pa = sub.add_parser("a2-apply")
    pa.add_argument("--classifications", default=str(A2_CLASSIFICATIONS_PATH))
    sub.add_parser("a5-fetch-comments")
    sub.add_parser("a5-regex-pass")
    sub.add_parser("a5-apply")
    args = p.parse_args(argv)
    if args.cmd == "a2-regex-pass":
        return cmd_a2_regex_pass(args)
    if args.cmd == "a2-apply":
        return cmd_a2_apply(args)
    if args.cmd == "a5-fetch-comments":
        return cmd_a5_fetch_comments(args)
    if args.cmd == "a5-regex-pass":
        return cmd_a5_regex_pass(args)
    if args.cmd == "a5-apply":
        return cmd_a5_apply(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
