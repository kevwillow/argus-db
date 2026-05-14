"""MAC-25 Step-2.0 — `/search/code` probe driver (≤30 calls, ≤4/vendor).

Per MAC-25 dispatch §17 + §3 + §17 binding:
- Hard cap: 30 `/search/code` calls total.
- ≤4 queries per vendor.
- Bucket: code_search (api.github.com/search/code).
- Min-gap: ≥2.1s (28/min ≈ 93% of 30/min nominal).
- RL_REMAINING_BUFFER[code_search]=3 (codified per dispatch §3, fix vs
  prior MAC-23 driver value of 2 — buffer must be < bucket budget per
  carry-forward finding #8 from MAC-23 close).
- NO retries on 429 / 403-rate-limit (parity with MAC-23 §3 #5).
- Pacer ledger continuity: writes to logs/github_pacer.json (same shape
  + path as MAC-23 driver). PAT-quota-burn supplementary count rolls
  forward as 379 + ≤30 = ≤409 / 2,500 = ≤16.4%.
- PAT loaded from <repo>/.env/.env (key GITHUB_PAT).

Vendors per dispatch §17 (cop-car cluster + first-party A1):
    cradlepoint, sierra-wireless, sierrawireless, dji, dji-sdk,
    hak5, hak5darren, watchguard, motorola, motorola-solutions,
    axon, axoninc, cellebrite, flock-safety, flocksafety
The driver dedupes by canonical vendor and rotates query templates
within the 4-query cap per vendor.

Outputs:
  raw/github_step2/<run-ts>/probe/<vendor_slug>/<query_idx>.json
  raw/github_step2/<run-ts>/_probe_manifest.json   (per-call accounting)
  logs/mac25_step2_0_probe_<run-ts>.log

Usage:
  # Dry-run (no HTTP, validate plan)
  python scripts/mac25_step2_0_probe.py --dry-run

  # Live fire (writes to logs/github_pacer.json + raw/github_step2)
  python scripts/mac25_step2_0_probe.py --live-fire-step2-0 \\
      --confirm "I-AUTHORIZE-MAC25-STEP-2-0-PROBE-2026-05-05" \\
      --max-queries 30
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = REPO_ROOT / ".env" / ".env"
DEFAULT_PACER_LEDGER = REPO_ROOT / "logs" / "github_pacer.json"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "github_step2"

UA = (
    "ArgusExtractionWorker/0.1 "
    "(Phase4 Wave-A Step-2.0 /search/code probe; "
    "+https://github.com/argus-project)"
)
TIMEOUT_S = 30

# Hard cap per dispatch §17.
PROBE_HARD_CAP = 30
PER_VENDOR_QUERY_CAP = 4

# Pacing — code_search bucket only.
BUCKET_CODE_SEARCH = "code_search"
MIN_GAP_S = 2.1
RL_REMAINING_BUFFER_CODE_SEARCH = 3  # Dispatch §3 codified fix (was 2).

DRY_RUN_DEFAULT = True
PROBE_CONFIRM_TOKEN = "I-AUTHORIZE-MAC25-STEP-2-0-PROBE-2026-05-05"

LOG = logging.getLogger("mac25_step2_0_probe")


# ─── Vendor query plan ────────────────────────────────────────────────────

# (canonical_vendor, [github_org_slug variants], [language tokens to try])
# Per dispatch §17 query shape:
#   org:<vendor-org> <ssid|default|password|bluetooth|service-uuid>
#   language:<java|python|swift|kotlin|c|cpp>
# We pick the 4 highest-yield (keyword, language) crosses per vendor.

VENDOR_PLAN: list[dict] = [
    # Cop-car cluster
    {
        "vendor": "Cradlepoint",
        "orgs": ["cradlepoint"],
        "queries": [
            ("default", "python"),
            ("ssid", "python"),
            ("password", "python"),
            ("bluetooth", "python"),
        ],
    },
    {
        "vendor": "Sierra Wireless",
        "orgs": ["sierrawireless"],
        "queries": [
            ("default", "c"),
            ("ssid", "c"),
            ("password", "c"),
            ("bluetooth", "c"),
        ],
    },
    {
        "vendor": "DJI",
        "orgs": ["dji-sdk"],
        "queries": [
            ("bluetooth", "java"),
            ("service-uuid", "java"),
            ("default", "java"),
            ("ssid", "swift"),
        ],
    },
    {
        "vendor": "Hak5",
        "orgs": ["hak5"],
        "queries": [
            ("ssid", "shell"),
            ("default", "python"),
            ("password", "python"),
            ("bluetooth", "c"),
        ],
    },
    {
        "vendor": "WatchGuard",
        "orgs": ["WatchGuard"],
        "queries": [
            ("default", "c"),
            ("ssid", "c"),
            ("password", "c"),
            ("bluetooth", "c"),
        ],
    },
    {
        "vendor": "Motorola Solutions",
        "orgs": ["MotorolaSolutions"],
        "queries": [
            ("default", "java"),
            ("ssid", "java"),
            ("password", "java"),
            ("bluetooth", "java"),
        ],
    },
    {
        "vendor": "Axon",
        "orgs": ["axoninc"],
        "queries": [
            ("default", "swift"),
            ("ssid", "swift"),
            ("bluetooth", "swift"),
            ("service-uuid", "swift"),
        ],
    },
    # Cellebrite — public org existence not confirmed; queries tolerated.
    {
        "vendor": "Cellebrite",
        "orgs": ["cellebrite"],
        "queries": [
            ("default", "c"),
            ("ssid", "c"),
            ("password", "c"),
            ("bluetooth", "c"),
        ],
    },
    {
        "vendor": "Flock Safety",
        "orgs": ["FlockSafety"],
        "queries": [
            ("default", "python"),
            ("ssid", "python"),
            ("password", "python"),
            ("bluetooth", "python"),
        ],
    },
]


def total_planned_queries() -> int:
    """Sum across all vendors, capped per-vendor at PER_VENDOR_QUERY_CAP."""
    return sum(min(len(v["queries"]), PER_VENDOR_QUERY_CAP) for v in VENDOR_PLAN)


# ─── PAT loading ──────────────────────────────────────────────────────────


def load_github_pat(env_path: Path = DEFAULT_ENV_PATH) -> str:
    """Read GITHUB_PAT from .env/.env. Value never logged."""
    if not env_path.exists():
        raise RuntimeError(f"GitHub PAT env file not found at {env_path}")
    pat: Optional[str] = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k == "GITHUB_PAT":
            pat = v
    if not pat:
        raise RuntimeError(f"GITHUB_PAT missing from {env_path}")
    return pat


# ─── PacerState (code_search bucket only) ─────────────────────────────────


@dataclass
class BucketState:
    last_query_at_iso: Optional[str] = None
    today_count: int = 0
    all_time_count: int = 0
    rl_remaining_last: Optional[int] = None
    rl_reset_last_iso: Optional[str] = None


@dataclass
class PacerState:
    """Same shape as MAC-23 driver writes; we ONLY mutate the code_search
    bucket on this script's runs to preserve cross-driver continuity."""
    schema_version: int = 1
    today_utc_iso: Optional[str] = None
    wave_a_run_ts: Optional[str] = None
    wave_a_total_calls: int = 0
    buckets: dict[str, BucketState] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = DEFAULT_PACER_LEDGER) -> "PacerState":
        if not path.exists():
            return cls(buckets={
                "core": BucketState(),
                "search": BucketState(),
                BUCKET_CODE_SEARCH: BucketState(),
            })
        raw = json.loads(path.read_text(encoding="utf-8"))
        buckets = {}
        for b in ("core", "search", BUCKET_CODE_SEARCH):
            d = (raw.get("buckets") or {}).get(b) or {}
            buckets[b] = BucketState(
                last_query_at_iso=d.get("last_query_at_iso"),
                today_count=int(d.get("today_count", 0)),
                all_time_count=int(d.get("all_time_count", 0)),
                rl_remaining_last=d.get("rl_remaining_last"),
                rl_reset_last_iso=d.get("rl_reset_last_iso"),
            )
        return cls(
            schema_version=int(raw.get("schema_version", 1)),
            today_utc_iso=raw.get("today_utc_iso"),
            wave_a_run_ts=raw.get("wave_a_run_ts"),
            wave_a_total_calls=int(raw.get("wave_a_total_calls", 0)),
            buckets=buckets,
        )

    def save(self, path: Path = DEFAULT_PACER_LEDGER) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        d = {
            "schema_version": self.schema_version,
            "today_utc_iso": self.today_utc_iso,
            "wave_a_run_ts": self.wave_a_run_ts,
            "wave_a_total_calls": self.wave_a_total_calls,
            "buckets": {
                b: {
                    "last_query_at_iso": st.last_query_at_iso,
                    "today_count": st.today_count,
                    "all_time_count": st.all_time_count,
                    "rl_remaining_last": st.rl_remaining_last,
                    "rl_reset_last_iso": st.rl_reset_last_iso,
                }
                for b, st in self.buckets.items()
            },
        }
        path.write_text(
            json.dumps(d, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def evaluate_code_search_pacer(
    state: PacerState, *, now: Optional[datetime] = None
) -> tuple[bool, str, int]:
    """Returns (can_fire, reason, seconds_until_ok). code_search-only."""
    if now is None:
        now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    st = state.buckets.get(BUCKET_CODE_SEARCH)
    if st is None:
        return False, "no_code_search_bucket", 0
    # Day rollover
    if state.today_utc_iso != today:
        st = BucketState(
            last_query_at_iso=st.last_query_at_iso,
            today_count=0,
            all_time_count=st.all_time_count,
            rl_remaining_last=st.rl_remaining_last,
            rl_reset_last_iso=st.rl_reset_last_iso,
        )
    # RL-buffer check. Only enforce when the reset boundary is still in the
    # future — once reset has elapsed, the cached rl_remaining_last is
    # stale and the next fire will refresh it from response headers.
    if (
        st.rl_remaining_last is not None
        and st.rl_remaining_last <= RL_REMAINING_BUFFER_CODE_SEARCH
        and st.rl_reset_last_iso
    ):
        try:
            reset = datetime.strptime(
                st.rl_reset_last_iso, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            wait = int((reset - now).total_seconds()) + 5
            if wait > 0:
                return False, (
                    f"rl_remaining_below_buffer "
                    f"({st.rl_remaining_last} ≤ {RL_REMAINING_BUFFER_CODE_SEARCH}, "
                    f"reset_in={wait}s)"
                ), wait
            # else: reset has elapsed; cached rl_remaining is stale — fall
            # through to min-gap check.
        except ValueError:
            pass
    # Min-gap
    if st.last_query_at_iso:
        try:
            last = datetime.strptime(
                st.last_query_at_iso, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            elapsed = (now - last).total_seconds()
            if elapsed < MIN_GAP_S:
                return False, (
                    f"min_gap_not_met (elapsed={elapsed:.2f}s, need {MIN_GAP_S}s)"
                ), int(MIN_GAP_S - elapsed) + 1
        except ValueError:
            pass
    return True, "ok", 0


def record_code_search_fire(
    state: PacerState,
    *,
    rl_remaining: Optional[int],
    rl_reset_iso: Optional[str],
    now: Optional[datetime] = None,
) -> PacerState:
    if now is None:
        now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    new_buckets = dict(state.buckets)
    cs = new_buckets.get(BUCKET_CODE_SEARCH, BucketState())
    today_count = 0 if state.today_utc_iso != today else cs.today_count
    new_buckets[BUCKET_CODE_SEARCH] = BucketState(
        last_query_at_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        today_count=today_count + 1,
        all_time_count=cs.all_time_count + 1,
        rl_remaining_last=rl_remaining,
        rl_reset_last_iso=rl_reset_iso,
    )
    # Other buckets unchanged
    return PacerState(
        schema_version=state.schema_version,
        today_utc_iso=today,
        wave_a_run_ts=state.wave_a_run_ts,
        wave_a_total_calls=state.wave_a_total_calls + 1,
        buckets=new_buckets,
    )


# ─── HTTP layer ────────────────────────────────────────────────────────────


@dataclass
class HttpResponse:
    status: Optional[int]
    final_url: str
    content_type: str
    headers: dict[str, str]
    body: bytes
    byte_count: int
    sha256: str
    elapsed_s: float
    error: Optional[str]
    rl_remaining: Optional[int]
    rl_reset_iso: Optional[str]
    is_quota_signal: bool


def _parse_rl(headers: dict[str, str]) -> tuple[Optional[int], Optional[str]]:
    rem = headers.get("X-RateLimit-Remaining") or headers.get("x-ratelimit-remaining")
    reset = headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")
    rl_remaining: Optional[int] = None
    rl_reset_iso: Optional[str] = None
    try:
        if rem is not None:
            rl_remaining = int(rem)
    except (TypeError, ValueError):
        pass
    try:
        if reset is not None:
            ts = int(reset)
            rl_reset_iso = (
                datetime.fromtimestamp(ts, timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
            )
    except (TypeError, ValueError):
        pass
    return rl_remaining, rl_reset_iso


def http_get(url: str, *, pat: str) -> HttpResponse:
    headers = {
        "User-Agent": UA,
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {pat}",
    }
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as r:
            body = r.read()
            hdr = dict(r.headers)
            rem, reset = _parse_rl(hdr)
            return HttpResponse(
                status=r.status, final_url=r.geturl(),
                content_type=hdr.get("Content-Type", ""),
                headers=hdr, body=body, byte_count=len(body),
                sha256=hashlib.sha256(body).hexdigest(),
                elapsed_s=round(time.time() - t0, 3),
                error=None, rl_remaining=rem, rl_reset_iso=reset,
                is_quota_signal=False,
            )
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        hdr = dict(e.headers) if hasattr(e, "headers") else {}
        rem, reset = _parse_rl(hdr)
        is_quota = e.code == 429 or (
            e.code == 403 and rem is not None and rem == 0
        )
        return HttpResponse(
            status=e.code, final_url=url,
            content_type=hdr.get("Content-Type", ""),
            headers=hdr, body=body, byte_count=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            elapsed_s=round(time.time() - t0, 3),
            error=f"HTTPError {e.code}",
            rl_remaining=rem, rl_reset_iso=reset,
            is_quota_signal=is_quota,
        )
    except Exception as e:
        return HttpResponse(
            status=None, final_url=url, content_type="",
            headers={}, body=b"", byte_count=0, sha256="",
            elapsed_s=round(time.time() - t0, 3),
            error=repr(e),
            rl_remaining=None, rl_reset_iso=None, is_quota_signal=False,
        )


# ─── Probe driver ──────────────────────────────────────────────────────────


def build_query_url(org: str, keyword: str, language: str) -> str:
    """Construct /search/code query URL."""
    q = f"org:{org} {keyword} language:{language}"
    return (
        "https://api.github.com/search/code"
        f"?q={urllib.parse.quote(q)}&per_page=30"
    )


def slugify(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s).strip("_").lower()


def run_probe(
    *,
    pacer_path: Path,
    raw_root: Path,
    pat: str,
    dry_run: bool,
    max_queries: int,
    log_path: Path,
    skip_vendors: list[str] | None = None,
) -> dict:
    """Execute the /search/code probe within hard caps + per-vendor caps.

    Returns a manifest dict with per-call accounting.
    """
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = raw_root / run_ts / "probe"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "run_ts": run_ts,
        "dry_run": dry_run,
        "max_queries_arg": max_queries,
        "hard_cap": PROBE_HARD_CAP,
        "per_vendor_cap": PER_VENDOR_QUERY_CAP,
        "min_gap_s": MIN_GAP_S,
        "rl_remaining_buffer": RL_REMAINING_BUFFER_CODE_SEARCH,
        "calls": [],
        "vendor_yield_summary": {},
        "halted_reason": None,
    }

    queries_fired = 0
    queries_attempted = 0
    cap = min(max_queries, PROBE_HARD_CAP)
    skip_set = {v.lower() for v in (skip_vendors or [])}

    for plan in VENDOR_PLAN:
        if plan["vendor"].lower() in skip_set:
            LOG.info("SKIP vendor=%s (per --skip-vendors)", plan["vendor"])
            manifest["vendor_yield_summary"][plan["vendor"]] = {
                "vendor": plan["vendor"], "skipped": True,
                "queries_fired": 0, "queries_attempted": 0,
                "total_count_returned": 0, "queries": [],
            }
            continue
        if queries_fired >= cap:
            manifest["halted_reason"] = "probe_hard_cap_reached"
            break
        vendor = plan["vendor"]
        vendor_slug = slugify(vendor)
        vendor_dir = out_dir / vendor_slug
        vendor_yield: dict = {
            "vendor": vendor,
            "queries_attempted": 0,
            "queries_fired": 0,
            "total_count_returned": 0,
            "anchored_hits_post_disambig": 0,
            "queries": [],
        }
        for org in plan["orgs"]:
            for q_idx, (keyword, language) in enumerate(plan["queries"][:PER_VENDOR_QUERY_CAP]):
                if vendor_yield["queries_fired"] >= PER_VENDOR_QUERY_CAP:
                    break
                if queries_fired >= cap:
                    manifest["halted_reason"] = "probe_hard_cap_reached"
                    break
                url = build_query_url(org, keyword, language)
                queries_attempted += 1
                vendor_yield["queries_attempted"] += 1
                if dry_run:
                    LOG.info("DRY-RUN would-fire org=%s kw=%s lang=%s",
                             org, keyword, language)
                    vendor_yield["queries"].append({
                        "url": url, "dry_run": True,
                        "org": org, "keyword": keyword, "language": language,
                    })
                    manifest["calls"].append({
                        "url": url, "vendor": vendor, "dry_run": True,
                    })
                    continue
                # PACER: load + evaluate. Loop the sleep-then-reevaluate
                # cycle up to MAX_PACER_LOOPS times (each loop sleeps the
                # current wait_s value, capped at 300s) before halting. This
                # handles the case where reset boundary keeps shifting by a
                # few seconds across consecutive evaluations.
                state = PacerState.load(pacer_path)
                can, reason, wait_s = evaluate_code_search_pacer(state)
                slept_s = 0.0
                MAX_PACER_LOOPS = 4
                loops = 0
                while not can and wait_s > 0 and loops < MAX_PACER_LOOPS:
                    capped = min(wait_s, 300)
                    LOG.info("pacer veto: %s — sleeping %ds (loop %d/%d)",
                             reason, capped, loops + 1, MAX_PACER_LOOPS)
                    time.sleep(capped)
                    slept_s += float(capped)
                    state = PacerState.load(pacer_path)
                    can, reason, wait_s = evaluate_code_search_pacer(state)
                    loops += 1
                if not can:
                    LOG.warning("pacer still vetoing after %d loops: %s — halt",
                                loops, reason)
                    manifest["halted_reason"] = f"pacer_veto:{reason}"
                    break
                LOG.info("FETCH %s", url)
                resp = http_get(url, pat=pat)
                state = PacerState.load(pacer_path)
                state = record_code_search_fire(
                    state, rl_remaining=resp.rl_remaining,
                    rl_reset_iso=resp.rl_reset_iso,
                )
                state.save(pacer_path)
                queries_fired += 1
                vendor_yield["queries_fired"] += 1
                # Save body
                vendor_dir.mkdir(parents=True, exist_ok=True)
                fname = f"{q_idx:02d}_{slugify(keyword)}_{slugify(language)}.json"
                body_path = vendor_dir / fname
                body_path.write_bytes(resp.body)
                # Per-call record
                count_returned = 0
                items_meta: list[dict] = []
                if resp.status == 200:
                    try:
                        d = json.loads(resp.body.decode("utf-8", "replace"))
                        count_returned = int(d.get("total_count", 0) or 0)
                        for it in (d.get("items") or [])[:30]:
                            items_meta.append({
                                "name": it.get("name"),
                                "path": it.get("path"),
                                "html_url": it.get("html_url"),
                                "repository_full_name": (
                                    it.get("repository", {}) or {}
                                ).get("full_name"),
                            })
                    except Exception as e:
                        LOG.warning("JSON parse fail: %s", e)
                vendor_yield["total_count_returned"] += count_returned
                call_rec = {
                    "url": url,
                    "vendor": vendor,
                    "org": org,
                    "keyword": keyword,
                    "language": language,
                    "status": resp.status,
                    "byte_count": resp.byte_count,
                    "sha256": resp.sha256,
                    "saved_to": str(body_path.relative_to(REPO_ROOT)),
                    "elapsed_s": resp.elapsed_s,
                    "error": resp.error,
                    "rl_remaining": resp.rl_remaining,
                    "rl_reset_iso": resp.rl_reset_iso,
                    "slept_s_pre": slept_s,
                    "total_count_returned": count_returned,
                    "items_first30_meta": items_meta,
                    "is_quota_signal": resp.is_quota_signal,
                }
                manifest["calls"].append(call_rec)
                vendor_yield["queries"].append(call_rec)
                if resp.is_quota_signal:
                    LOG.error("QUOTA SIGNAL — halting per dispatch §3 #5")
                    manifest["halted_reason"] = "quota_signal"
                    break
                if resp.status == 403 and resp.rl_remaining == 0:
                    LOG.error("403 + RL=0 — halting")
                    manifest["halted_reason"] = "403_rl_zero"
                    break
            if manifest["halted_reason"]:
                break
        manifest["vendor_yield_summary"][vendor] = vendor_yield
        if manifest["halted_reason"]:
            break

    manifest["queries_attempted"] = queries_attempted
    manifest["queries_fired"] = queries_fired
    # Persist manifest
    man_path = out_dir.parent / "_probe_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2))
    return manifest


# ─── CLI ───────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true",
                   help="No HTTP, validate plan only")
    p.add_argument("--live-fire-step2-0", action="store_true",
                   help="Authorize live fire (also requires --confirm)")
    p.add_argument("--confirm", default="",
                   help="Live-fire confirm token")
    p.add_argument("--max-queries", type=int, default=PROBE_HARD_CAP)
    p.add_argument("--skip-vendors", default="",
                   help="Comma-separated vendor names to skip (e.g. 'Cradlepoint,Sierra Wireless')")
    p.add_argument("--pacer", type=Path, default=DEFAULT_PACER_LEDGER)
    p.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    p.add_argument("--env-path", type=Path, default=DEFAULT_ENV_PATH)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args(argv)

    log_path = REPO_ROOT / "logs" / f"mac25_step2_0_probe_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    dry_run = True
    if args.live_fire_step2_0:
        if args.confirm != PROBE_CONFIRM_TOKEN:
            LOG.error("--live-fire-step2-0 requires --confirm '%s'",
                      PROBE_CONFIRM_TOKEN)
            return 2
        dry_run = False
    elif args.dry_run:
        dry_run = True
    else:
        LOG.error("must pass either --dry-run or --live-fire-step2-0 + --confirm")
        return 2

    LOG.info(
        "MAC-25 Step-2.0 probe — dry_run=%s max_queries=%d hard_cap=%d "
        "per_vendor_cap=%d min_gap_s=%.1f rl_buffer=%d",
        dry_run, args.max_queries, PROBE_HARD_CAP,
        PER_VENDOR_QUERY_CAP, MIN_GAP_S, RL_REMAINING_BUFFER_CODE_SEARCH,
    )
    LOG.info("Vendors planned: %d  total planned queries: %d",
             len(VENDOR_PLAN), total_planned_queries())

    pat = ""
    if not dry_run:
        pat = load_github_pat(args.env_path)
        LOG.info("PAT loaded (length=%d)", len(pat))

    skip_vendors = [s.strip() for s in args.skip_vendors.split(",") if s.strip()]
    manifest = run_probe(
        pacer_path=args.pacer,
        raw_root=args.raw_root,
        pat=pat,
        dry_run=dry_run,
        max_queries=args.max_queries,
        log_path=log_path,
        skip_vendors=skip_vendors,
    )
    LOG.info(
        "Probe complete — fired=%d attempted=%d halted=%s",
        manifest["queries_fired"], manifest["queries_attempted"],
        manifest["halted_reason"],
    )
    print(json.dumps({
        "queries_fired": manifest["queries_fired"],
        "queries_attempted": manifest["queries_attempted"],
        "halted_reason": manifest["halted_reason"],
        "vendor_summary": {
            v: {
                "queries_fired": s["queries_fired"],
                "total_count_returned": s["total_count_returned"],
            }
            for v, s in manifest["vendor_yield_summary"].items()
        },
        "log_path": str(log_path.relative_to(REPO_ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
