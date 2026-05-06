"""MAC-26 Phase 4 Wave-A Step 2.5 — first-party SDK content fetch driver.

Per dispatch contract MAC-26 (description):
- §7.x SourceWorker scope: HTTP fetch + corpus write + byte-level survey only.
  NO LLM. NO `raw_observations` writes. NO `identifiers` promotion. NO
  `sources`-table writes (deferred to ExtractionWorker dispatch per §11 #14).
- ≤100 core HTTP calls hard cap (estimated ~66; 11 repos × ~6 calls each).
- NO `/search/code`, `/search/repositories`, `/search/issues` — repo set is
  fixed per the Step-2.0 probe canonical 11.
- Per-repo strategy: `GET /repos/{owner}/{repo}` (1 core) +
  `GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1` (1 core), then
  apply path heuristic → ≤8 contents fetches via `/contents/{path}?ref=`.
  Tree fallback to `/contents/{path}` walk if the recursive cap trips —
  halt + reassign rather than blow the ≤100 budget.
- Path heuristic per dispatch §11.
- 64KB per-file content cap (skip+log if a candidate exceeds — surface
  deviation in summary).
- Pacing: core bucket ≥0.75s gap, RL_REMAINING_BUFFER[core]=20 (reduced
  from precedent 200 per dispatch clause 3 carry-forward finding).
- NO retries on 429/403-rate-limit. Failure logged, query NOT reattempted.
- PAT loaded from /home/kev/argus/.env/.env (key `GITHUB_PAT`); never
  logged or surfaced.
- Idempotent: per-repo `_meta.json` short-circuits a re-run.
- Confirm-token gate parity with MAC-23 driver.

Outputs:
  raw/github_step2_5/{run_ts}/cohort_A1_extension/{owner}__{repo}/_meta.json
  raw/github_step2_5/{run_ts}/cohort_A1_extension/{owner}__{repo}/_tree.json
  raw/github_step2_5/{run_ts}/cohort_A1_extension/{owner}__{repo}/<flat_path>
  raw/github_step2_5/{run_ts}/_manifest.json   (call accounting + RL trace)
  logs/mac26_step2_5_fetch_{run_ts}.log
  logs/github_pacer.json   (cross-heartbeat 3-bucket pacer; updated in place)

Usage:
  # Smoke (no HTTP / no writes)
  python scripts/mac26_step2_5_fetch.py --dry-run

  # Live fire (≤100 core calls)
  python scripts/mac26_step2_5_fetch.py \\
      --live-fire-step25 \\
      --confirm "I-AUTHORIZE-STEP-2-5-LIVE-FIRE-2026-05-06" \\
      --max-queries 100 --sleep-to-meet-gap
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import logging
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Reuse the proven precedent's pacer + HTTP helpers.
sys.path.insert(0, str(Path(__file__).parent))
import mac23_step1_wave_a_fetch as _m23  # type: ignore
from mac23_step1_wave_a_fetch import (  # type: ignore
    BUCKET_CORE,
    DEFAULT_ENV_PATH,
    DEFAULT_PACER_LEDGER,
    HttpResponse,
    PacerState,
    REPO_ROOT,
    fetch_paced,
    load_github_pat,
)

# Dispatch clause 3: override the inherited core-bucket RL buffer.
# Precedent driver pinned core=200 (defensive belt-and-suspenders); MAC-23
# carry-forward finding #8 ratifies "buffer < bucket budget" — for core's
# 4,800/h budget, 20 is well-below and gives ~24,000 headroom. Keep search
# / code_search untouched (their buffers are already correctly sized).
_m23.RL_REMAINING_BUFFER[BUCKET_CORE] = 20

# ─── Constants ────────────────────────────────────────────────────────────

DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "github_step2_5"

STEP25_HARD_CAP_CORE = 100      # dispatch clause 1
STEP25_CONFIRM_TOKEN = "I-AUTHORIZE-STEP-2-5-LIVE-FIRE-2026-05-06"

PER_REPO_FILE_CAP = 8           # dispatch clause 11
PER_FILE_BYTE_CAP = 64 * 1024   # dispatch clause 11 — skip files > 64 KB

# Path heuristic — dispatch clause 11
INCLUDE_EXT = (
    ".java", ".c", ".h", ".py", ".kt", ".swift", ".m", ".mm",
    ".cpp", ".hpp", ".go", ".rs",
)
INCLUDE_PATH_RE = re.compile(
    r"(constants|bluetooth|\bble\b|wifi|ssid|default|config|"
    r"manufacturer|product|service|advertising|hardware|net|mac|"
    r"address|credential|password)",
    re.IGNORECASE,
)
EXCLUDE_PATH_RE = re.compile(
    r"(^|/)(test|tests|spec|specs|docs|samples|sample|example|examples|"
    r"fixture|fixtures|generated|build|node_modules|vendor|third_party|"
    r"3rdparty|\.gradle|\.idea)(/|$)",
    re.IGNORECASE,
)

# Canonical 11-repo list per probe manifests + dispatch §§7–9.
# (owner, repo, vendor_label) — branch is discovered from the meta call.
TARGET_REPOS: list[tuple[str, str, str]] = [
    # Cradlepoint × 2
    ("cradlepoint", "api-samples", "Cradlepoint"),
    ("cradlepoint", "sdk-samples", "Cradlepoint"),
    # Sierra Wireless × 3
    ("SierraWireless", "luasched", "Sierra Wireless"),
    ("SierraWireless", "octave-orp", "Sierra Wireless"),
    ("SierraWireless", "octave-orp-stm32", "Sierra Wireless"),
    # DJI × 6 (dispatch §9 + 2 from probe manifest)
    ("dji-sdk", "Mobile-SDK-Android", "DJI"),
    ("dji-sdk", "Mobile-SDK-Android-V5", "DJI"),
    ("dji-sdk", "DJI-Cloud-API-Demo", "DJI"),
    ("dji-sdk", "Mobile-UXSDK-Beta-Android", "DJI"),
    ("dji-sdk", "Android-Bridge-App", "DJI"),
    ("dji-sdk", "Mobile-UXSDK-Android", "DJI"),
]
assert len(TARGET_REPOS) == 11, "Step-2.5 dispatch is exactly 11 repos"

LOG = logging.getLogger("mac26_step25")


def configure_logging(log_path: Path, verbose: bool = False) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


# ─── Path heuristic ──────────────────────────────────────────────────────


def path_matches_heuristic(p: str) -> bool:
    """Dispatch clause 11: include if extension AND name/path matches the
    keyword regex AND is not in the exclude regex."""
    if EXCLUDE_PATH_RE.search(p):
        return False
    lower = p.lower()
    if not any(lower.endswith(ext) for ext in INCLUDE_EXT):
        return False
    return bool(INCLUDE_PATH_RE.search(p))


def select_files_from_tree(
    tree_items: list[dict], cap: int = PER_REPO_FILE_CAP
) -> tuple[list[dict], dict]:
    """Apply path heuristic to a /git/trees response. Return (chosen, info).

    info diagnostics:
        total_blobs, matches_post_heuristic, oversize_filtered_count,
        oversize_paths_first10, deviation (str|None).
    Selection rule per dispatch §11: priority by file-size descending,
    cap PER_REPO_FILE_CAP and PER_FILE_BYTE_CAP.
    """
    blobs = [it for it in tree_items if it.get("type") == "blob"]
    matches = [
        it for it in blobs if it.get("path") and path_matches_heuristic(it["path"])
    ]
    oversize = [it for it in matches if (it.get("size") or 0) > PER_FILE_BYTE_CAP]
    eligible = [it for it in matches if (it.get("size") or 0) <= PER_FILE_BYTE_CAP]
    eligible.sort(key=lambda it: (it.get("size") or 0), reverse=True)
    chosen = eligible[:cap]
    deviation: Optional[str] = None
    if matches and not eligible:
        deviation = (
            f"all_{len(matches)}_matches_exceed_64KB_cap; "
            "surface for ratification per dispatch §11"
        )
    elif not matches:
        deviation = "no_path_heuristic_matches_in_tree"
    info = {
        "total_blobs": len(blobs),
        "matches_post_heuristic": len(matches),
        "matches_eligible_under_64KB": len(eligible),
        "oversize_filtered_count": len(oversize),
        "oversize_paths_first10": [it.get("path") for it in oversize[:10]],
        "deviation": deviation,
    }
    return chosen, info


# ─── Per-repo fetch ──────────────────────────────────────────────────────


def _flat_path_for_disk(p: str, used: set[str]) -> str:
    flat = p.replace("/", "__")
    base = flat
    n = 0
    while flat in used:
        n += 1
        # Insert before extension if present.
        if "." in base:
            stem, dot, ext = base.rpartition(".")
            flat = f"{stem}__{n}.{ext}"
        else:
            flat = f"{base}__{n}"
    used.add(flat)
    return flat


def _save_response(
    out_dir: Path, name: str, resp: HttpResponse, url: str
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    body_path = out_dir / name
    body_path.write_bytes(resp.body)
    return {
        "url": url,
        "final_url": resp.final_url,
        "status": resp.status,
        "content_type": resp.content_type,
        "byte_count": resp.byte_count,
        "sha256": resp.sha256,
        "elapsed_s": resp.elapsed_s,
        "error": resp.error,
        "rl_remaining": resp.rl_remaining,
        "rl_reset_iso": resp.rl_reset_iso,
        "saved_to": str(body_path.relative_to(REPO_ROOT)),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_one_repo(
    owner: str,
    repo: str,
    vendor: str,
    cohort_dir: Path,
    *,
    pacer_path: Path,
    pat: str,
    dry_run: bool,
    sleep_to_meet_gap: bool,
    queries_remaining: int,
) -> tuple[dict, int, bool]:
    """Fetch metadata + recursive tree + ≤8 path-heuristic-matched files.

    Returns (per_repo_summary, queries_used, halt_signal).
    halt_signal=True means a stop-the-line condition fired (per dispatch §23)
    and the caller MUST stop the loop and surface the deviation.
    """
    repo_dir = cohort_dir / f"{owner}__{repo}"
    summary: dict = {
        "vendor": vendor,
        "repo": f"{owner}/{repo}",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }
    queries_used = 0

    # Idempotent: skip if both meta + tree already on disk
    meta_path = repo_dir / "_meta.json"
    tree_path = repo_dir / "_tree.json"
    if (
        not dry_run
        and meta_path.exists()
        and meta_path.stat().st_size > 0
        and tree_path.exists()
        and tree_path.stat().st_size > 0
    ):
        summary["skipped"] = "already_on_disk"
        summary["closed_at"] = datetime.now(timezone.utc).isoformat()
        return summary, 0, False

    # Step 1 — meta
    if queries_remaining - queries_used <= 0:
        summary["skipped"] = "queries_budget_meta"
        return summary, queries_used, False
    meta_url = f"https://api.github.com/repos/{owner}/{repo}"
    out = fetch_paced(
        meta_url, pacer_path=pacer_path, pat=pat,
        dry_run=dry_run, sleep_to_meet_gap=sleep_to_meet_gap,
    )
    if not out.fired and out.reason != "dry_run":
        summary["meta_skipped"] = out.reason
        return summary, queries_used, False
    if out.fired:
        queries_used += 1
        rec = _save_response(repo_dir, "_meta.json", out.response, meta_url)
        summary["meta"] = rec
        if out.response.is_quota_signal:
            LOG.error("QUOTA SIGNAL on meta %s; halting per dispatch clause 5",
                      meta_url)
            return summary, queries_used, True
        if out.response.status not in (200, 304):
            summary["meta_status_nonok"] = out.response.status
            # 403/404 = repo gone or private — surface but continue cohort.
            if out.response.status in (403, 404, 451):
                summary["halt_per_dispatch_§23"] = (
                    f"meta returned {out.response.status} "
                    "(403/404/451 systematic — likely archived/private)"
                )
                return summary, queries_used, True
            return summary, queries_used, False
    elif out.reason == "dry_run":
        summary["meta"] = {"url": meta_url, "dry_run": True}

    # Discover real default branch
    real_branch = "main"
    if out.fired and out.response.status == 200 and out.response.body:
        try:
            d = json.loads(out.response.body)
            real_branch = d.get("default_branch") or "main"
            summary["default_branch"] = real_branch
            summary["repo_meta_excerpt"] = {
                "size_kb": d.get("size"),
                "license_spdx": (d.get("license") or {}).get("spdx_id"),
                "stargazers_count": d.get("stargazers_count"),
                "topics": (d.get("topics") or [])[:10],
                "default_branch": real_branch,
                "archived": d.get("archived"),
                "disabled": d.get("disabled"),
                "pushed_at": d.get("pushed_at"),
            }
        except Exception as e:
            LOG.warning("meta parse failed for %s: %r", meta_url, e)

    # Step 2 — recursive tree
    if queries_remaining - queries_used <= 0:
        summary["tree_skipped"] = "queries_budget_tree"
        return summary, queries_used, False
    tree_url = (
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/"
        f"{urllib.parse.quote(real_branch)}?recursive=1"
    )
    out = fetch_paced(
        tree_url, pacer_path=pacer_path, pat=pat,
        dry_run=dry_run, sleep_to_meet_gap=sleep_to_meet_gap,
    )
    tree_items: list[dict] = []
    if out.fired:
        queries_used += 1
        rec = _save_response(repo_dir, "_tree.json", out.response, tree_url)
        summary["tree"] = rec
        if out.response.is_quota_signal:
            LOG.error("QUOTA SIGNAL on tree %s; halting", tree_url)
            return summary, queries_used, True
        if out.response.status == 200 and out.response.body:
            try:
                td = json.loads(out.response.body)
                tree_items = td.get("tree") or []
                summary["tree_truncated"] = bool(td.get("truncated"))
                if td.get("truncated"):
                    summary["halt_per_dispatch_§23"] = (
                        "tree response truncated by GitHub recursive-cap; "
                        "fallback to /contents/{path} walk would exceed ≤100 "
                        "core call budget — halt + reassign per §23"
                    )
                    return summary, queries_used, True
            except Exception as e:
                LOG.warning("tree parse failed for %s: %r", tree_url, e)
        else:
            summary["tree_status_nonok"] = out.response.status
            return summary, queries_used, False
    elif out.reason == "dry_run":
        summary["tree"] = {"url": tree_url, "dry_run": True}
        # Synthesize one synthetic tree-item for dry-run accounting parity.
        tree_items = [{
            "path": "DryRun/Constants/MockBleConstants.java",
            "type": "blob", "size": 1234,
        }]
    else:
        summary["tree_skipped"] = out.reason
        return summary, queries_used, False

    chosen, sel_info = select_files_from_tree(tree_items)
    summary["selection"] = sel_info
    summary["chosen_paths"] = [it.get("path") for it in chosen]

    # Step 3 — per-file contents fetch (≤8 files, each ≤64KB)
    used_disk_names: set[str] = set(["_meta.json", "_tree.json"])
    for it in chosen:
        if queries_remaining - queries_used <= 0:
            summary["files"].append({
                "path": it.get("path"), "skipped": "queries_budget_file",
            })
            break
        api_path = it["path"]
        ct_url = (
            f"https://api.github.com/repos/{owner}/{repo}/contents/"
            f"{urllib.parse.quote(api_path)}"
            f"?ref={urllib.parse.quote(real_branch)}"
        )
        out = fetch_paced(
            ct_url, pacer_path=pacer_path, pat=pat,
            dry_run=dry_run, sleep_to_meet_gap=sleep_to_meet_gap,
        )
        if not out.fired and out.reason != "dry_run":
            summary["files"].append({
                "path": api_path, "skipped": out.reason,
            })
            break
        if out.fired:
            queries_used += 1
            if out.response.is_quota_signal:
                LOG.error("QUOTA SIGNAL on contents %s; halting cohort", ct_url)
                summary["files"].append({
                    "path": api_path, "url": ct_url,
                    "quota_signal": True,
                    "status": out.response.status,
                })
                return summary, queries_used, True
            if out.response.status != 200:
                summary["files"].append({
                    "path": api_path, "url": ct_url,
                    "status": out.response.status,
                    "error": out.response.error,
                })
                continue
            # Decode base64 body
            try:
                payload = json.loads(out.response.body)
                encoding = payload.get("encoding")
                if encoding == "base64":
                    raw = base64.b64decode(payload.get("content") or "")
                else:
                    raw = (payload.get("content") or "").encode("utf-8")
                size_actual = len(raw)
                if size_actual > PER_FILE_BYTE_CAP:
                    # Defensive: tree size and actual decoded body diverged.
                    summary["files"].append({
                        "path": api_path, "url": ct_url,
                        "skipped": (
                            f"actual_decoded_size_{size_actual}_exceeds_64KB_cap"
                        ),
                        "size_actual": size_actual,
                        "size_from_tree": it.get("size"),
                    })
                    continue
                flat_name = _flat_path_for_disk(api_path, used_disk_names)
                target = repo_dir / flat_name
                target.write_bytes(raw)
                summary["files"].append({
                    "kind": "file",
                    "path": api_path,
                    "url": ct_url,
                    "encoding_in": encoding,
                    "size_from_tree": it.get("size"),
                    "byte_count_decoded": size_actual,
                    "sha256_decoded": hashlib.sha256(raw).hexdigest(),
                    "saved_to": str(target.relative_to(REPO_ROOT)),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "rl_remaining": out.response.rl_remaining,
                    "rl_reset_iso": out.response.rl_reset_iso,
                })
            except (binascii.Error, ValueError, json.JSONDecodeError) as e:
                summary["files"].append({
                    "path": api_path, "url": ct_url,
                    "decode_error": repr(e),
                })
        elif out.reason == "dry_run":
            summary["files"].append({
                "path": api_path, "url": ct_url, "dry_run": True,
            })

    summary["closed_at"] = datetime.now(timezone.utc).isoformat()
    summary["queries_used"] = queries_used
    return summary, queries_used, False


def write_manifest(
    out_root: Path,
    repo_summaries: list[dict],
    pacer_after: PacerState,
    queries_used_total: int,
    invocation_args: dict,
    halted_reason: Optional[str],
) -> Path:
    manifest_path = out_root / "_manifest.json"
    existing: dict = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
        except Exception:
            existing = {}
    invocations = existing.get("invocations", [])
    invocations.append({
        "invoked_at": datetime.now(timezone.utc).isoformat(),
        "args": invocation_args,
        "queries_used": queries_used_total,
        "halted_reason": halted_reason,
        "pacer_snapshot": {
            "wave_a_total_calls": pacer_after.wave_a_total_calls,
            "today_utc_iso": pacer_after.today_utc_iso,
            "buckets": {
                b: {
                    "today_count": st.today_count,
                    "all_time_count": st.all_time_count,
                    "rl_remaining_last": st.rl_remaining_last,
                    "rl_reset_last_iso": st.rl_reset_last_iso,
                    "last_query_at_iso": st.last_query_at_iso,
                }
                for b, st in pacer_after.buckets.items()
            },
        },
    })
    manifest = {
        "issue": "MAC-26",
        "phase": "4 / Wave-A / Step 2.5 SourceWorker first-party SDK content fetch",
        "auth_posture": "PAT (token; .env/.env GITHUB_PAT, never logged)",
        "hard_cap_core": STEP25_HARD_CAP_CORE,
        "pacer_path": str(DEFAULT_PACER_LEDGER.relative_to(REPO_ROOT)),
        "target_repos_canonical_11": [
            f"{o}/{r}" for o, r, _ in TARGET_REPOS
        ],
        "repo_summaries": repo_summaries,
        "invocations": invocations,
    }
    out_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest_path


# ─── CLI entry ───────────────────────────────────────────────────────────


def _main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "MAC-26 Wave-A Step 2.5 first-party SDK content fetch — "
            "≤100 core calls over the canonical 11 yielding repos."
        )
    )
    p.add_argument(
        "--live-fire-step25", action="store_true",
        help=(
            "Run live HTTP fetch. Requires --confirm token. Defaults to "
            "dry-run; this flag flips it OFF after token check."
        ),
    )
    p.add_argument(
        "--confirm", type=str, default="",
        help=f"Confirmation token; must equal {STEP25_CONFIRM_TOKEN!r}",
    )
    p.add_argument(
        "--max-queries", type=int, default=STEP25_HARD_CAP_CORE,
        help=(
            f"Upper bound on api.github.com calls this invocation "
            f"(default {STEP25_HARD_CAP_CORE} = dispatch hard cap)."
        ),
    )
    p.add_argument(
        "--repo-allowlist", type=str, default="",
        help=(
            "Comma-separated owner/repo allowlist (e.g., "
            "'cradlepoint/api-samples,cradlepoint/sdk-samples'). "
            "Empty = all 11 canonical."
        ),
    )
    p.add_argument(
        "--run-ts", type=str, default="",
        help="Override run timestamp (YYYYMMDDTHHMMSSZ). Default = now-utc.",
    )
    p.add_argument(
        "--sleep-to-meet-gap", action="store_true",
        help="Sleep to honor the pacer gap instead of skipping.",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Smoke-test orchestration without HTTP/disk writes.",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    if not args.dry_run and args.live_fire_step25:
        if args.confirm != STEP25_CONFIRM_TOKEN:
            print(
                "REFUSED: --live-fire-step25 requires --confirm exactly "
                f"{STEP25_CONFIRM_TOKEN!r}. Got: <redacted>",
                file=sys.stderr,
            )
            return 2
        dry_run = False
    else:
        dry_run = True

    if args.max_queries > STEP25_HARD_CAP_CORE:
        print(
            f"REFUSED: --max-queries={args.max_queries} exceeds dispatch "
            f"hard cap of {STEP25_HARD_CAP_CORE}", file=sys.stderr,
        )
        return 2

    run_ts = args.run_ts or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = DEFAULT_RAW_ROOT / run_ts
    cohort_dir = out_root / "cohort_A1_extension"
    log_path = REPO_ROOT / "logs" / f"mac26_step2_5_fetch_{run_ts}.log"
    configure_logging(log_path, verbose=args.verbose)
    LOG.info("MAC-26 Step-2.5 invocation; run_ts=%s out=%s dry_run=%s",
             run_ts, out_root, dry_run)
    LOG.info("max_queries=%s repo_allowlist=%r sleep_to_gap=%s",
             args.max_queries, args.repo_allowlist, args.sleep_to_meet_gap)

    pat = ""
    if not dry_run:
        pat = load_github_pat()
        LOG.info("PAT loaded from %s (value never logged)", DEFAULT_ENV_PATH)

    pacer_path = DEFAULT_PACER_LEDGER
    state = PacerState.load(pacer_path)
    LOG.info("Pacer pre-state: wave_a_total_calls=%d today_count(core)=%d",
             state.wave_a_total_calls,
             state.buckets[BUCKET_CORE].today_count)

    allow = (
        {s.strip() for s in args.repo_allowlist.split(",") if s.strip()}
        if args.repo_allowlist.strip() else None
    )

    queries_budget = args.max_queries
    queries_used_total = 0
    repo_summaries: list[dict] = []
    halted_reason: Optional[str] = None

    for owner, repo, vendor in TARGET_REPOS:
        full = f"{owner}/{repo}"
        if allow and full not in allow:
            LOG.info("Skipping %s (not in allowlist)", full)
            continue
        if queries_budget - queries_used_total <= 0:
            LOG.info("Budget exhausted before %s; halting cohort", full)
            halted_reason = "queries_budget_exhausted"
            break
        LOG.info("=== %s start (queries_remaining=%d) ===",
                 full, queries_budget - queries_used_total)
        summ, used, halt = fetch_one_repo(
            owner, repo, vendor, cohort_dir,
            pacer_path=pacer_path, pat=pat,
            dry_run=dry_run, sleep_to_meet_gap=args.sleep_to_meet_gap,
            queries_remaining=queries_budget - queries_used_total,
        )
        queries_used_total += used
        repo_summaries.append(summ)
        LOG.info("=== %s closed: queries_used=%d (cum=%d/%d) halt=%s ===",
                 full, used, queries_used_total, queries_budget, halt)
        if halt:
            halted_reason = (
                summ.get("halt_per_dispatch_§23")
                or "stop_the_line_per_dispatch_§23"
            )
            break

    pacer_after = PacerState.load(pacer_path)
    invocation_args = {
        "live_fire": args.live_fire_step25,
        "max_queries": args.max_queries,
        "repo_allowlist": sorted(allow) if allow else None,
        "dry_run": dry_run,
        "run_ts": run_ts,
        "sleep_to_meet_gap": args.sleep_to_meet_gap,
    }
    manifest_path = write_manifest(
        out_root, repo_summaries, pacer_after,
        queries_used_total, invocation_args, halted_reason,
    )
    LOG.info("Wrote manifest: %s", manifest_path)
    LOG.info("Pacer post-state: wave_a_total_calls=%d today_count(core)=%d",
             pacer_after.wave_a_total_calls,
             pacer_after.buckets[BUCKET_CORE].today_count)
    print(json.dumps({
        "run_ts": run_ts,
        "out_root": str(out_root.relative_to(REPO_ROOT)),
        "cohort_dir": str(cohort_dir.relative_to(REPO_ROOT)),
        "dry_run": dry_run,
        "queries_used_this_invocation": queries_used_total,
        "wave_a_total_calls": pacer_after.wave_a_total_calls,
        "step25_hard_cap_core": STEP25_HARD_CAP_CORE,
        "halted_reason": halted_reason,
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "log": str(log_path.relative_to(REPO_ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
