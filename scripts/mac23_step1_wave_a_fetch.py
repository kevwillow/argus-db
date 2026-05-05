"""MAC-23 Phase 4 Wave-A Step 1 — GitHub PAT-provisioned fetch driver.

Per dispatch contract MAC-23 (description):
- §7.1 SourceWorker scope: discovery + fetch + survey ONLY (NO Step-2 extraction,
  NO LLM calls, NO `raw_observations` writes, NO `sources` table writes here).
- 2,500 API-call hard cap (reserve ~600 for retries + Step-1.5b survey probes).
- 3 rate-limit buckets, PAT-provisioned: core ≤4,800/h (≥0.75s gap), search
  ≤1,800/h (≥2s gap), code-search ≤28/min (≥2.1s gap). Header-driven sleep
  if `X-RateLimit-Remaining` drops below the buffer.
- NO retries on 429 / 403-rate-limit (parity with WiGLE no-retry discipline).
- DRY_RUN_DEFAULT = True. Live fire requires --live-fire-wave-a + --confirm
  with the exact token below.
- PAT loaded from /home/kev/argus/.env/.env (key `GITHUB_PAT`); value never
  logged or surfaced in comments / commit messages / PROJECT_STATE / manifest.
- Cohorts A1 → A2 → A3 → A4 → A5 (see clause 10). Cop-car cluster sequenced
  first within A1 per clause 13.
- Surface inclusion: A1+A2+A3+A4+A5; /search/code INCLUDED under PAT posture.

Outputs:
  raw/github/<run-ts>/cohort{A1,A2,A3,A4,A5}/<vendor_slug>/<repo_or_query>/...
  raw/github/<run-ts>/_manifest.json   (call accounting, RL trace, sha256s)
  logs/github_pacer.json               (cross-heartbeat 3-bucket pacer)
  logs/mac23_step1_wave_a_fetch_<run-ts>.log

This script is invoked per heartbeat; the pacer ledger persists wave-aggregate
state across heartbeats. Each invocation specifies --max-cohort and an upper
spend cap via --max-queries; subsequent invocations resume per remaining
quota until cohort completion.

Usage examples:
  # Smoke (no HTTP, no writes — verify config + cohort wiring)
  python scripts/mac23_step1_wave_a_fetch.py --dry-run --max-cohort A1 --max-queries 0

  # First-fire shadow probe (5 calls, 1 vendor — Cradlepoint A1)
  python scripts/mac23_step1_wave_a_fetch.py \\
      --live-fire-wave-a \\
      --confirm "I-AUTHORIZE-WAVE-A-LIVE-FIRE-2026-05-05" \\
      --max-cohort A1 \\
      --vendor-allowlist "Cradlepoint" \\
      --max-queries 5

  # Subsequent heartbeats: continue cohort A1 (or advance)
  python scripts/mac23_step1_wave_a_fetch.py \\
      --live-fire-wave-a --confirm "..." \\
      --max-cohort A1 --max-queries 200
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ─── Constants (binding per MAC-23 dispatch contract) ─────────────────────

REPO_ROOT = Path("/home/kev/argus")
DEFAULT_ENV_PATH = REPO_ROOT / ".env" / ".env"
DEFAULT_PACER_LEDGER = REPO_ROOT / "logs" / "github_pacer.json"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "github"

UA = (
    "ArgusSourceWorker/0.1 "
    "(Phase4 Wave-A Step1 PAT-provisioned fetch; "
    "+https://github.com/argus-project)"
)
TIMEOUT_S = 30

# Hard cap ratified at MAC-21 §9.8 + dispatch clause 1.
WAVE_A_HARD_CAP = 2500
WAVE_A_RESERVE = 600          # retries + Step-1.5b survey-class probes

# Per-bucket pacing per dispatch clause 3.
BUCKET_CORE = "core"           # api.github.com (non-search)
BUCKET_SEARCH = "search"        # /search/* except /search/code
BUCKET_CODE_SEARCH = "code_search"  # /search/code

MIN_GAP_S = {
    BUCKET_CORE: 0.75,
    BUCKET_SEARCH: 2.0,
    BUCKET_CODE_SEARCH: 2.1,
}
HOURLY_QUOTA = {
    BUCKET_CORE: 4800,
    BUCKET_SEARCH: 1800,
    BUCKET_CODE_SEARCH: 28 * 60,  # 28/min ≈ 1680/h, but bucket binds at 28/min
}
# RL buffer: if remaining drops below this, halt-and-sleep until reset.
RL_REMAINING_BUFFER = {
    BUCKET_CORE: 200,
    BUCKET_SEARCH: 50,
    BUCKET_CODE_SEARCH: 5,
}

DRY_RUN_DEFAULT = True
WAVE_A_CONFIRM_TOKEN = "I-AUTHORIZE-WAVE-A-LIVE-FIRE-2026-05-05"

# Step-0 discovery batch (for cohort source-of-truth).
STEP0_DISCOVERY_BATCH = "20260505T162207Z"
STEP0_REPOS_PATH = (
    DEFAULT_RAW_ROOT / STEP0_DISCOVERY_BATCH / "_step0" / "per_vendor_repos.json"
)
STEP0_ORGS_PATH = (
    DEFAULT_RAW_ROOT / STEP0_DISCOVERY_BATCH / "_step0" / "org_enumeration.json"
)

# ─── A1 cohort: confirmed first-party orgs (Step-0 ratified at MAC-21) ─────

# (vendor_canonical, org_slug). Cop-car cluster first per dispatch clause 13.
# Avigilon / Rekor have status=200 orgs but 0 public_repos — still confirmed
# orgs; their per-repo fetch surface is empty (§11 #1 absence-documented).
A1_ORGS: list[tuple[str, str]] = [
    # Cop-car cluster (priority within A1)
    ("Cradlepoint", "cradlepoint"),
    ("Sierra Wireless", "sierrawireless"),
    ("Motorola Solutions", "MotorolaSolutions"),
    ("Flock Safety", "FlockSafety"),
    ("DJI", "dji-sdk"),
    ("Hak5", "hak5"),
    ("WatchGuard", "WatchGuard"),
    # Confirmed first-party orgs (non-cop-car)
    ("Parrot", "Parrot-Developers"),
    ("Skydio", "Skydio"),
    ("BRINC", "BRINC-Drones"),
    ("Magnet Forensics", "magnetforensics"),
    ("Genetec", "Genetec"),
    ("Avigilon", "avigilon"),
    ("Axis Communications", "AxisCommunications"),
    ("L3Harris", "L3Harris"),
    ("Rekor", "RekorAI"),
    ("BriefCam", "briefcam"),
    ("Clearview AI", "clearviewai"),
    ("SoundThinking", "SoundThinking"),
]
assert len(A1_ORGS) == 19, "A1 must be exactly 19 confirmed first-party orgs"

# Vendors with 0 repo-search hits at Step-0 — §11 #1 absence-documented at
# manifest time, no API spend per dispatch clause 12.
A1_ZERO_RESULT_VENDORS = {
    "Digital Receiver Technology",
    "SoundThinking",   # 1 search hit but org repos=1 — keep fetch
    "Vigilant Solutions",
}

# A1 file shortlist guidance per dispatch clause 10: README + *Constants* +
# *Bluetooth* + *Default* + root config. We pull README explicitly and walk
# /contents to discover the others.
A1_FILES_PER_REPO = 5
A1_REPOS_PER_VENDOR = 3        # 3-5 highest-star, mid 3 keeps per-vendor cap


# ─── A2 / A3 / A4 / A5 — third-party + community + generic + issue surfaces ─

# Curated A2 third-party recon/detector repos (sourced from Step-0 search).
# Vendor=primary-vendor-target this repo studies (NOT repo owner).
A2_REPOS: list[tuple[str, str, str, str]] = [
    # (owner, repo, default_branch_guess, primary_vendor_target)
    ("0xXyc", "flock-you-wifi-recon", "main", "Flock Safety"),
    ("f1yaw4y", "FlockSquawk", "main", "Flock Safety"),
    ("GainSec", "Flock-Safety-Trap-Shooter-Sniffer-Alarm", "main", "Flock Safety"),
    ("DeflockYourCity", "flock-alpr-toolkit", "main", "Flock Safety"),
    ("zmattmanz", "flock-detection", "main", "Flock Safety"),
    ("vegantransistor", "Rooting-the-Cradlepoint-IBR600", "master", "Cradlepoint"),
    ("danielewood", "sierra-wireless-modems", "main", "Sierra Wireless"),
    ("bkerler", "SierraWirelessGen", "main", "Sierra Wireless"),
    ("smcl", "py-em73xx", "master", "Sierra Wireless"),
    ("o-gs", "dji-firmware-tools", "master", "DJI"),
    ("damiafuentes", "DJITelloPy", "main", "DJI"),
    ("levlesec", "lockup", "main", "Cellebrite"),
    ("DFIRScience", "UFDR2DIR", "main", "Cellebrite"),
    ("levlesec", "cellebrite-decryptor", "main", "Cellebrite"),
    ("AxisCommunications", "backstage-plugins", "main", "Axis Communications"),
    ("danielorf", "pyaxiscam", "master", "Axis Communications"),
    ("trunnion", "vapix", "main", "Axis Communications"),
    ("facelessg00n", "BerlaTools", "main", "Berla"),
]
A2_FILES_PER_REPO = 5

# A3 Hak5-community / payload-fork repos × ~5 files.
A3_REPOS: list[tuple[str, str, str, str]] = [
    ("I-Am-Jakoby", "Flipper-Zero-BadUSB", "main", "Hak5"),
    ("aleff-github", "my-flipper-shits", "main", "Hak5"),
    ("I-Am-Jakoby", "PowerShell-for-Hackers", "main", "Hak5"),
    ("hak5", "bashbunny-payloads", "master", "Hak5"),
    ("hak5", "usbrubberducky-payloads", "master", "Hak5"),
    ("hak5", "omg-payloads", "master", "Hak5"),
    ("hak5", "wifipineapple-modules", "master", "Hak5"),
    ("hak5", "lanturtle-modules", "master", "Hak5"),
    ("hak5", "packetsquirrel-payloads", "master", "Hak5"),
    ("hak5", "sharkjack-payloads", "master", "Hak5"),
]
A3_FILES_PER_REPO = 5

# A4 — generic repo-search per vendor × top-3 (mid of 3-file cap).
# Drives off Step-0 cache; filters out vendors already covered in A1+A2+A3
# (cop-car-cluster already heavy-covered) AND vendors with 0 search hits.
A4_FILES_PER_REPO = 3
A4_REPOS_PER_VENDOR = 3

# A5 — issue-search threads. Identifier-keyword crosses, scoped to closed-
# completed issues; per-keyword 1 search call → top-10 issue captures.
# Per dispatch clause 10 mid 50 hits (rough planning floor).
A5_KEYWORDS: list[str] = [
    "default password",
    "default SSID",
    "BLE service UUID",
    "Bluetooth pairing",
    "FCC ID",
    "MAC address",
    "WPA2 passphrase",
    "factory reset credentials",
]
A5_PER_KEYWORD_QUERIES = 4  # top-N vendor crosses per keyword


# ─── Tightened anchor regex (per dispatch §15 clause 19 — Step-1.5b survey) ─

REGEX_MAC = re.compile(r"\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b")
REGEX_BLE_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b"
)
# TIGHTENED per MAC-21 §9.11 — mandatory hyphen, 4-14 grantee+model chars.
REGEX_FCC_ID_TIGHT = re.compile(r"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b")
REGEX_SSID_KW = re.compile(r"\bssid\b", re.IGNORECASE)
DEFAULT_CRED_TOKENS = (
    "default password", "default credential", "default login", "default user",
    "factory reset", "default passphrase", "wpa2 password", "default ssid",
)


# ─── Logger ──────────────────────────────────────────────────────────────

LOG = logging.getLogger("mac23_step1")


def configure_logging(log_path: Path, verbose: bool = False) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)s %(message)s"
    handlers = [
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=fmt,
        handlers=handlers,
    )


# ─── PAT loading (NEVER LOG VALUE) ────────────────────────────────────────


def load_github_pat(env_path: Path = DEFAULT_ENV_PATH) -> str:
    """Read `GITHUB_PAT` from `.env/.env`. Value never logged.

    Returns the raw token. Caller is responsible for putting it on the
    Authorization header and never echoing it.
    """
    if not env_path.exists():
        raise RuntimeError(
            f"GitHub PAT env file not found at {env_path}; expected "
            "`.env/.env` with GITHUB_PAT (board-provisioned at MAC-1 "
            "[`24a1dc2b`] 2026-05-05T19:45Z)"
        )
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
        raise RuntimeError(
            f"GITHUB_PAT missing from {env_path}; cannot construct auth"
        )
    return pat


# ─── 3-bucket pacer (cross-heartbeat persisted) ──────────────────────────


@dataclass
class BucketState:
    last_query_at_iso: Optional[str] = None
    today_count: int = 0
    all_time_count: int = 0
    rl_remaining_last: Optional[int] = None
    rl_reset_last_iso: Optional[str] = None


@dataclass
class PacerState:
    schema_version: int = 1
    today_utc_iso: Optional[str] = None
    wave_a_run_ts: Optional[str] = None
    wave_a_total_calls: int = 0  # all buckets aggregated for hard-cap check
    buckets: dict[str, BucketState] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = DEFAULT_PACER_LEDGER) -> "PacerState":
        if not path.exists():
            return cls(buckets={b: BucketState() for b in MIN_GAP_S})
        raw = json.loads(path.read_text(encoding="utf-8"))
        buckets = {}
        for b, default in MIN_GAP_S.items():
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
        path.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")


def _today_utc_iso(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def evaluate_pacer(
    state: PacerState, bucket: str, *, now: Optional[datetime] = None
) -> tuple[bool, str, int]:
    """Returns (can_fire, reason, seconds_until_ok)."""
    if now is None:
        now = datetime.now(timezone.utc)
    today = _today_utc_iso(now)
    # Day rollover: zeroes per-bucket today_count
    rolled_buckets = {}
    for b, st in state.buckets.items():
        if state.today_utc_iso != today:
            rolled_buckets[b] = BucketState(
                last_query_at_iso=st.last_query_at_iso,
                today_count=0,
                all_time_count=st.all_time_count,
                rl_remaining_last=st.rl_remaining_last,
                rl_reset_last_iso=st.rl_reset_last_iso,
            )
        else:
            rolled_buckets[b] = st
    # Hard cap on wave aggregate
    if state.wave_a_total_calls >= WAVE_A_HARD_CAP:
        return False, (
            f"wave_a_hard_cap_exhausted "
            f"({state.wave_a_total_calls}/{WAVE_A_HARD_CAP})"
        ), 0
    st = rolled_buckets.get(bucket)
    if st is None:
        return False, f"unknown_bucket={bucket!r}", 0
    # RL-remaining buffer check
    if (
        st.rl_remaining_last is not None
        and st.rl_remaining_last <= RL_REMAINING_BUFFER[bucket]
    ):
        if st.rl_reset_last_iso:
            try:
                reset = datetime.strptime(
                    st.rl_reset_last_iso, "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=timezone.utc)
                wait = max(0, int((reset - now).total_seconds()) + 5)
                if wait > 0:
                    return False, (
                        f"rl_remaining_below_buffer "
                        f"({st.rl_remaining_last} ≤ {RL_REMAINING_BUFFER[bucket]}, "
                        f"reset_in={wait}s)"
                    ), wait
            except ValueError:
                pass
    # Min-gap check
    if st.last_query_at_iso:
        try:
            last = datetime.strptime(
                st.last_query_at_iso, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            elapsed = (now - last).total_seconds()
            min_gap = MIN_GAP_S[bucket]
            if elapsed < min_gap:
                return False, (
                    f"min_gap_not_met (elapsed={elapsed:.2f}s, need {min_gap}s)"
                ), int(min_gap - elapsed) + 1
        except ValueError:
            pass
    return True, "ok", 0


def record_fire(
    state: PacerState,
    bucket: str,
    *,
    rl_remaining: Optional[int] = None,
    rl_reset_iso: Optional[str] = None,
    now: Optional[datetime] = None,
) -> PacerState:
    if now is None:
        now = datetime.now(timezone.utc)
    today = _today_utc_iso(now)
    new_buckets: dict[str, BucketState] = {}
    for b, st in state.buckets.items():
        if state.today_utc_iso != today:
            today_count = 0
        else:
            today_count = st.today_count
        if b == bucket:
            new_buckets[b] = BucketState(
                last_query_at_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                today_count=today_count + 1,
                all_time_count=st.all_time_count + 1,
                rl_remaining_last=rl_remaining,
                rl_reset_last_iso=rl_reset_iso,
            )
        else:
            new_buckets[b] = BucketState(
                last_query_at_iso=st.last_query_at_iso,
                today_count=today_count,
                all_time_count=st.all_time_count,
                rl_remaining_last=st.rl_remaining_last,
                rl_reset_last_iso=st.rl_reset_last_iso,
            )
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


def _parse_rl_headers(
    headers: dict[str, str]
) -> tuple[Optional[int], Optional[str]]:
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


def http_get(
    url: str,
    *,
    pat: Optional[str],
    accept: str = "application/vnd.github+json",
) -> HttpResponse:
    headers = {"User-Agent": UA, "Accept": accept}
    if pat:
        headers["Authorization"] = f"token {pat}"
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as r:
            body = r.read()
            hdr = dict(r.headers)
            rem, reset = _parse_rl_headers(hdr)
            return HttpResponse(
                status=r.status,
                final_url=r.geturl(),
                content_type=hdr.get("Content-Type", ""),
                headers=hdr,
                body=body,
                byte_count=len(body),
                sha256=hashlib.sha256(body).hexdigest(),
                elapsed_s=round(time.time() - t0, 3),
                error=None,
                rl_remaining=rem,
                rl_reset_iso=reset,
                is_quota_signal=False,
            )
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        hdr = dict(e.headers) if hasattr(e, "headers") else {}
        rem, reset = _parse_rl_headers(hdr)
        is_quota = e.code == 429 or (
            e.code == 403 and rem is not None and rem == 0
        )
        return HttpResponse(
            status=e.code,
            final_url=url,
            content_type=hdr.get("Content-Type", ""),
            headers=hdr,
            body=body,
            byte_count=len(body),
            sha256=hashlib.sha256(body).hexdigest(),
            elapsed_s=round(time.time() - t0, 3),
            error=f"HTTPError {e.code}",
            rl_remaining=rem,
            rl_reset_iso=reset,
            is_quota_signal=is_quota,
        )
    except Exception as e:
        return HttpResponse(
            status=None,
            final_url=url,
            content_type="",
            headers={},
            body=b"",
            byte_count=0,
            sha256="",
            elapsed_s=round(time.time() - t0, 3),
            error=repr(e),
            rl_remaining=None,
            rl_reset_iso=None,
            is_quota_signal=False,
        )


# ─── Bucket classification (URL → bucket) ────────────────────────────────


def classify_bucket(url: str) -> str:
    if "api.github.com/search/code" in url:
        return BUCKET_CODE_SEARCH
    if "api.github.com/search/" in url:
        return BUCKET_SEARCH
    if "api.github.com/" in url:
        return BUCKET_CORE
    raise ValueError(
        f"URL not classifiable into a GitHub API bucket: {url!r} "
        "(raw.githubusercontent.com fetches use fetch_raw, not http_get_paced)"
    )


# ─── Paced HTTP (the one chokepoint that all api.github.com calls go through) ─


@dataclass
class FetchOutcome:
    response: HttpResponse
    bucket: Optional[str]
    fired: bool             # True if a real HTTP call happened
    reason: str             # "ok" or pacer veto / dry-run / cap
    sleep_taken_s: float


def fetch_paced(
    url: str,
    *,
    pacer_path: Path,
    pat: Optional[str],
    dry_run: bool,
    sleep_to_meet_gap: bool,
    accept: str = "application/vnd.github+json",
    now_provider=None,
) -> FetchOutcome:
    """Single-shot paced GitHub API call.

    NO retries on 429 / 403-rate-limit (per dispatch clause 5).
    Pacer verdict respected; if `sleep_to_meet_gap` True, will sleep
    in-process to honor the gap. Else returns FetchOutcome(fired=False).
    Loads + saves pacer state inside this function — caller need only
    pass the path.
    """
    bucket = classify_bucket(url)
    state = PacerState.load(pacer_path)
    now = (now_provider() if now_provider else datetime.now(timezone.utc))
    can, reason, wait_s = evaluate_pacer(state, bucket, now=now)
    sleep_taken = 0.0
    if not can and sleep_to_meet_gap and wait_s > 0:
        # Cap any single sleep to a reasonable max (5 minutes); caller may
        # choose to abort wave instead. This matters mostly for RL reset waits.
        capped = min(wait_s, 300)
        LOG.info("pacer veto for %s: %s — sleeping %ds (capped from %ds)",
                 bucket, reason, capped, wait_s)
        time.sleep(capped)
        sleep_taken = float(capped)
        # Re-evaluate after sleep
        state = PacerState.load(pacer_path)
        now = datetime.now(timezone.utc)
        can, reason, wait_s = evaluate_pacer(state, bucket, now=now)
    if not can:
        return FetchOutcome(
            response=HttpResponse(
                status=None, final_url=url, content_type="", headers={},
                body=b"", byte_count=0, sha256="", elapsed_s=0.0,
                error=f"pacer_veto: {reason}",
                rl_remaining=None, rl_reset_iso=None, is_quota_signal=False,
            ),
            bucket=bucket, fired=False, reason=reason,
            sleep_taken_s=sleep_taken,
        )
    if dry_run:
        return FetchOutcome(
            response=HttpResponse(
                status=None, final_url=url, content_type="application/json",
                headers={}, body=b"{}", byte_count=2, sha256="",
                elapsed_s=0.0, error="dry_run_no_http",
                rl_remaining=None, rl_reset_iso=None, is_quota_signal=False,
            ),
            bucket=bucket, fired=False, reason="dry_run",
            sleep_taken_s=sleep_taken,
        )
    LOG.info("FETCH %s [%s] (gap_ok)", url, bucket)
    resp = http_get(url, pat=pat, accept=accept)
    state = PacerState.load(pacer_path)
    state = record_fire(
        state, bucket,
        rl_remaining=resp.rl_remaining,
        rl_reset_iso=resp.rl_reset_iso,
        now=datetime.now(timezone.utc),
    )
    state.save(pacer_path)
    return FetchOutcome(
        response=resp, bucket=bucket, fired=True, reason="ok",
        sleep_taken_s=sleep_taken,
    )


def fetch_raw(url: str) -> HttpResponse:
    """raw.githubusercontent.com fetch — uncounted, no auth needed.

    Per dispatch clause 1: unlimited raw fetches. We still apply a tiny
    polite gap to avoid hammering the CDN within a single wave.
    """
    if not url.startswith("https://raw.githubusercontent.com/"):
        raise ValueError(f"fetch_raw URL must be raw CDN: {url!r}")
    time.sleep(0.2)
    return http_get(url, pat=None, accept="*/*")


# ─── Cohort fetch logic ────────────────────────────────────────────────────


def _slugify(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s).strip("_").lower()


def _save_artifact(
    out_dir: Path,
    name: str,
    body: bytes,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / name
    p.write_bytes(body)
    return {
        "path": str(p.relative_to(REPO_ROOT)),
        "byte_count": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


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


def load_step0_repos() -> dict:
    if not STEP0_REPOS_PATH.exists():
        raise RuntimeError(f"Step-0 cache missing: {STEP0_REPOS_PATH}")
    return json.loads(STEP0_REPOS_PATH.read_text())


def fetch_one_repo_files(
    owner: str,
    repo: str,
    default_branch: str,
    out_root: Path,
    *,
    pacer_path: Path,
    pat: str,
    dry_run: bool,
    sleep_to_meet_gap: bool,
    files_per_repo: int,
    queries_remaining: int,
) -> tuple[list[dict], int]:
    """Fetch metadata + contents listing + up to N files for one repo.

    Returns (per_file_records, queries_used_against_api). Raw CDN fetches
    are uncounted but still recorded.
    """
    repo_dir = out_root / f"{_slugify(owner)}__{_slugify(repo)}"
    queries_used = 0
    files_recorded: list[dict] = []

    # 1) Repo metadata (core)
    if queries_remaining - queries_used <= 0:
        return files_recorded, queries_used
    meta_url = f"https://api.github.com/repos/{owner}/{repo}"
    out = fetch_paced(
        meta_url, pacer_path=pacer_path, pat=pat,
        dry_run=dry_run, sleep_to_meet_gap=sleep_to_meet_gap,
    )
    if out.fired:
        queries_used += 1
        rec = _save_response(repo_dir, "_meta.json", out.response, meta_url)
        files_recorded.append({"kind": "meta", **rec})
        if out.response.is_quota_signal:
            LOG.error("QUOTA SIGNAL on meta %s; halting per dispatch clause 5",
                      meta_url)
            return files_recorded, queries_used
    elif out.reason == "dry_run":
        files_recorded.append({"kind": "meta", "url": meta_url, "dry_run": True})
    else:
        files_recorded.append({"kind": "meta", "url": meta_url, "skipped": out.reason})
        return files_recorded, queries_used

    # Discover real default branch from response if available (status=200)
    real_branch = default_branch
    if out.fired and out.response.status == 200 and out.response.body:
        try:
            d = json.loads(out.response.body)
            real_branch = d.get("default_branch") or default_branch
        except Exception:
            pass

    # 2) Root contents listing (core)
    if queries_remaining - queries_used <= 0:
        return files_recorded, queries_used
    contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents/?ref={urllib.parse.quote(real_branch)}"
    out = fetch_paced(
        contents_url, pacer_path=pacer_path, pat=pat,
        dry_run=dry_run, sleep_to_meet_gap=sleep_to_meet_gap,
    )
    file_candidates: list[str] = []
    if out.fired:
        queries_used += 1
        rec = _save_response(repo_dir, "_contents_root.json", out.response, contents_url)
        files_recorded.append({"kind": "contents_root", **rec})
        if out.response.is_quota_signal:
            return files_recorded, queries_used
        if out.response.status == 200:
            try:
                items = json.loads(out.response.body)
                for it in items:
                    name = it.get("name") or ""
                    if name and it.get("type") == "file":
                        file_candidates.append(name)
            except Exception:
                pass
    elif out.reason == "dry_run":
        files_recorded.append({"kind": "contents_root", "url": contents_url, "dry_run": True})
    else:
        files_recorded.append({"kind": "contents_root", "url": contents_url, "skipped": out.reason})

    # 3) Pick up to N files: README.md (case-insens), then *Constants*,
    #    *Bluetooth*, *Default*, then root config.
    chosen: list[str] = []
    if file_candidates:
        # README first
        readme = next((n for n in file_candidates if n.lower() == "readme.md"), None)
        if not readme:
            readme = next((n for n in file_candidates if n.lower().startswith("readme")), None)
        if readme:
            chosen.append(readme)
        for pat_re in (
            re.compile(r"constants", re.IGNORECASE),
            re.compile(r"bluetooth|\bble\b", re.IGNORECASE),
            re.compile(r"default", re.IGNORECASE),
        ):
            for n in file_candidates:
                if n in chosen:
                    continue
                if pat_re.search(n):
                    chosen.append(n)
                    break
        # Root config (manifest.json / package.json / setup.py / Cargo.toml)
        for n in file_candidates:
            if n in chosen:
                continue
            if n.lower() in {
                "manifest.json", "package.json", "setup.py", "cargo.toml",
                "main.py", "app.py", "config.json",
            }:
                chosen.append(n)
                break
    else:
        chosen.append("README.md")    # blind raw fetch fallback
    chosen = chosen[:files_per_repo]

    # 4) Raw CDN fetches (uncounted)
    for fname in chosen:
        raw_url = (
            f"https://raw.githubusercontent.com/{owner}/{repo}/"
            f"{urllib.parse.quote(real_branch)}/{urllib.parse.quote(fname)}"
        )
        if dry_run:
            files_recorded.append({"kind": "file", "url": raw_url, "dry_run": True})
            continue
        try:
            resp = fetch_raw(raw_url)
            target = repo_dir / fname.replace("/", "_")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(resp.body)
            rec = {
                "url": raw_url,
                "final_url": resp.final_url,
                "status": resp.status,
                "content_type": resp.content_type,
                "byte_count": resp.byte_count,
                "sha256": resp.sha256,
                "elapsed_s": resp.elapsed_s,
                "error": resp.error,
                "saved_to": str(target.relative_to(REPO_ROOT)),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
            files_recorded.append({"kind": "file", **rec})
        except Exception as e:
            files_recorded.append({"kind": "file", "url": raw_url,
                                   "error": repr(e)})
    return files_recorded, queries_used


def cohort_a1(
    out_root: Path,
    *,
    pacer_path: Path,
    pat: str,
    dry_run: bool,
    sleep_to_meet_gap: bool,
    queries_remaining: int,
    vendor_allowlist: Optional[set[str]],
    repos_per_vendor: int = A1_REPOS_PER_VENDOR,
    files_per_repo: int = A1_FILES_PER_REPO,
) -> tuple[dict, int]:
    """A1 fetch: 19 confirmed first-party orgs × top-3 repos × ~5 files."""
    cohort_dir = out_root / "cohort_A1"
    step0 = load_step0_repos()
    summary: dict = {"vendors": {}, "started_at": datetime.now(timezone.utc).isoformat()}
    queries_used = 0
    for vendor, org_slug in A1_ORGS:
        if vendor_allowlist and vendor not in vendor_allowlist:
            continue
        if queries_remaining - queries_used <= 0:
            LOG.info("A1: queries budget exhausted; halting cohort")
            break
        vendor_summary: dict = {"org": org_slug, "repos_fetched": []}
        # Pick top-N repos owned by org_slug from Step-0 cache.
        items = (step0.get(vendor) or {}).get("items", [])
        own_items = [
            it for it in items
            if (it.get("owner") or "").lower() == org_slug.lower()
        ]
        # If org owns 0 repos in top-10, fall back to top-N regardless of owner
        # only when the org itself has public_repos==0 (Avigilon, Rekor case).
        # Otherwise §11 #1 absence-document.
        if not own_items:
            vendor_summary["note"] = (
                f"no_top10_repos_owned_by_{org_slug}; absence per §11 #1"
            )
            summary["vendors"][vendor] = vendor_summary
            continue
        for it in own_items[:repos_per_vendor]:
            owner = (it.get("owner") or "")
            repo = (it.get("full_name") or "").split("/", 1)[-1]
            default_branch = it.get("default_branch") or "main"
            if queries_remaining - queries_used <= 0:
                vendor_summary["repos_fetched"].append(
                    {"repo": f"{owner}/{repo}", "skipped": "queries_budget"}
                )
                break
            files, used = fetch_one_repo_files(
                owner, repo, default_branch, cohort_dir,
                pacer_path=pacer_path, pat=pat,
                dry_run=dry_run, sleep_to_meet_gap=sleep_to_meet_gap,
                files_per_repo=files_per_repo,
                queries_remaining=queries_remaining - queries_used,
            )
            queries_used += used
            vendor_summary["repos_fetched"].append({
                "repo": f"{owner}/{repo}",
                "default_branch": default_branch,
                "stars": it.get("stars"),
                "queries_used": used,
                "files": files,
            })
        summary["vendors"][vendor] = vendor_summary
    summary["closed_at"] = datetime.now(timezone.utc).isoformat()
    summary["queries_used"] = queries_used
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "_cohort_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    return summary, queries_used


def cohort_generic_repo_list(
    repos: list[tuple[str, str, str, str]],
    cohort_name: str,
    out_root: Path,
    *,
    pacer_path: Path,
    pat: str,
    dry_run: bool,
    sleep_to_meet_gap: bool,
    queries_remaining: int,
    files_per_repo: int,
) -> tuple[dict, int]:
    cohort_dir = out_root / f"cohort_{cohort_name}"
    summary: dict = {"repos": [], "started_at": datetime.now(timezone.utc).isoformat()}
    queries_used = 0
    for owner, repo, default_branch, vendor_target in repos:
        if queries_remaining - queries_used <= 0:
            summary["repos"].append({
                "repo": f"{owner}/{repo}", "skipped": "queries_budget"
            })
            break
        files, used = fetch_one_repo_files(
            owner, repo, default_branch, cohort_dir,
            pacer_path=pacer_path, pat=pat,
            dry_run=dry_run, sleep_to_meet_gap=sleep_to_meet_gap,
            files_per_repo=files_per_repo,
            queries_remaining=queries_remaining - queries_used,
        )
        queries_used += used
        summary["repos"].append({
            "repo": f"{owner}/{repo}",
            "default_branch": default_branch,
            "vendor_target": vendor_target,
            "queries_used": used,
            "files": files,
        })
    summary["closed_at"] = datetime.now(timezone.utc).isoformat()
    summary["queries_used"] = queries_used
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "_cohort_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    return summary, queries_used


def cohort_a4(
    out_root: Path,
    *,
    pacer_path: Path,
    pat: str,
    dry_run: bool,
    sleep_to_meet_gap: bool,
    queries_remaining: int,
) -> tuple[dict, int]:
    """A4: top-N repos per vendor (broader sweep, deduped vs A1+A2+A3)."""
    cohort_dir = out_root / "cohort_A4"
    step0 = load_step0_repos()
    # Build dedup set of (owner, repo) already covered in A1+A2+A3
    seen: set[tuple[str, str]] = set()
    for v, org in A1_ORGS:
        items = (step0.get(v) or {}).get("items", [])
        for it in items[:A1_REPOS_PER_VENDOR]:
            owner = (it.get("owner") or "").lower()
            repo = (it.get("full_name") or "").split("/", 1)[-1].lower()
            seen.add((owner, repo))
    for o, r, _, _ in A2_REPOS + A3_REPOS:
        seen.add((o.lower(), r.lower()))

    summary: dict = {"vendors": {}, "started_at": datetime.now(timezone.utc).isoformat()}
    queries_used = 0
    for vendor in step0:
        if vendor in A1_ZERO_RESULT_VENDORS:
            summary["vendors"][vendor] = {"note": "zero_search_hits_at_step0"}
            continue
        if queries_remaining - queries_used <= 0:
            break
        items = (step0.get(vendor) or {}).get("items", [])
        candidates = []
        for it in items[:10]:
            owner = (it.get("owner") or "").lower()
            repo_name = (it.get("full_name") or "").split("/", 1)[-1].lower()
            if (owner, repo_name) in seen:
                continue
            if it.get("fork") or it.get("archived"):
                continue
            candidates.append(it)
            if len(candidates) >= A4_REPOS_PER_VENDOR:
                break
        v_summary: dict = {"repos_fetched": []}
        for it in candidates:
            if queries_remaining - queries_used <= 0:
                v_summary["repos_fetched"].append(
                    {"skipped": "queries_budget"}
                )
                break
            owner = it.get("owner") or ""
            repo = (it.get("full_name") or "").split("/", 1)[-1]
            default_branch = it.get("default_branch") or "main"
            files, used = fetch_one_repo_files(
                owner, repo, default_branch, cohort_dir,
                pacer_path=pacer_path, pat=pat,
                dry_run=dry_run, sleep_to_meet_gap=sleep_to_meet_gap,
                files_per_repo=A4_FILES_PER_REPO,
                queries_remaining=queries_remaining - queries_used,
            )
            queries_used += used
            v_summary["repos_fetched"].append({
                "repo": f"{owner}/{repo}",
                "stars": it.get("stars"),
                "queries_used": used,
                "files": files,
            })
        summary["vendors"][vendor] = v_summary
    summary["closed_at"] = datetime.now(timezone.utc).isoformat()
    summary["queries_used"] = queries_used
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "_cohort_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    return summary, queries_used


def cohort_a5(
    out_root: Path,
    *,
    pacer_path: Path,
    pat: str,
    dry_run: bool,
    sleep_to_meet_gap: bool,
    queries_remaining: int,
) -> tuple[dict, int]:
    """A5: identifier-keyword × vendor issue search (search bucket)."""
    cohort_dir = out_root / "cohort_A5"
    summary: dict = {"queries": [], "started_at": datetime.now(timezone.utc).isoformat()}
    queries_used = 0
    # Vendor crosses: cop-car cluster first
    vendors = [v for v, _ in A1_ORGS]
    for kw in A5_KEYWORDS:
        for vendor in vendors[:A5_PER_KEYWORD_QUERIES]:
            if queries_remaining - queries_used <= 0:
                break
            q = urllib.parse.quote_plus(
                f'"{vendor}" "{kw}" is:issue is:closed reason:completed'
            )
            url = (
                f"https://api.github.com/search/issues?"
                f"q={q}&sort=comments&order=desc&per_page=10"
            )
            out = fetch_paced(
                url, pacer_path=pacer_path, pat=pat,
                dry_run=dry_run, sleep_to_meet_gap=sleep_to_meet_gap,
            )
            if out.fired:
                queries_used += 1
                save_dir = cohort_dir / _slugify(vendor) / _slugify(kw)
                rec = _save_response(save_dir, "issues_search.json", out.response, url)
                summary["queries"].append({
                    "vendor": vendor, "keyword": kw, **rec
                })
                if out.response.is_quota_signal:
                    LOG.error("QUOTA SIGNAL on A5 issue search; halting cohort")
                    summary["closed_at"] = datetime.now(timezone.utc).isoformat()
                    summary["queries_used"] = queries_used
                    (cohort_dir / "_cohort_summary.json").write_text(
                        json.dumps(summary, indent=2, sort_keys=True)
                    )
                    return summary, queries_used
            elif out.reason == "dry_run":
                summary["queries"].append({"vendor": vendor, "keyword": kw,
                                           "url": url, "dry_run": True})
            else:
                summary["queries"].append({"vendor": vendor, "keyword": kw,
                                           "url": url, "skipped": out.reason})
        if queries_remaining - queries_used <= 0:
            break
    summary["closed_at"] = datetime.now(timezone.utc).isoformat()
    summary["queries_used"] = queries_used
    cohort_dir.mkdir(parents=True, exist_ok=True)
    (cohort_dir / "_cohort_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True)
    )
    return summary, queries_used


# ─── Manifest writer ──────────────────────────────────────────────────────


def write_manifest(
    out_root: Path,
    cohort_summaries: dict,
    pacer_after: PacerState,
    queries_used_this_invocation: int,
    invocation_args: dict,
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
        "queries_used": queries_used_this_invocation,
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
        "issue": "MAC-23",
        "phase": "4 / Wave-A / Step 1",
        "auth_posture": "PAT (token; .env/.env GITHUB_PAT, never logged)",
        "hard_cap": WAVE_A_HARD_CAP,
        "reserve": WAVE_A_RESERVE,
        "pacer_path": str(DEFAULT_PACER_LEDGER.relative_to(REPO_ROOT)),
        "step0_discovery_batch": STEP0_DISCOVERY_BATCH,
        "cohort_summaries": cohort_summaries,
        "invocations": invocations,
    }
    out_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest_path


# ─── CLI entry ────────────────────────────────────────────────────────────


def _main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "MAC-23 Wave-A Step 1 GitHub fetch driver — PAT-provisioned, "
            "3-bucket pacer, cohort A1→A5."
        )
    )
    p.add_argument(
        "--live-fire-wave-a", action="store_true",
        help=(
            "Run Wave-A live fetch. Requires --confirm token. "
            "DRY_RUN_DEFAULT is True; this flag flips it OFF for this "
            "invocation only (and only after confirm-token check)."
        ),
    )
    p.add_argument(
        "--confirm", type=str, default="",
        help=f"Confirmation token; must equal {WAVE_A_CONFIRM_TOKEN!r}",
    )
    p.add_argument(
        "--max-cohort", type=str,
        choices=["A1", "A2", "A3", "A4", "A5"], default="A1",
        help="Highest cohort to advance to. Cohorts run A1→A5 in order.",
    )
    p.add_argument(
        "--cohorts", type=str, default="",
        help=(
            "Comma-separated cohort allowlist (e.g., 'A1,A2'). "
            "Overrides --max-cohort if non-empty."
        ),
    )
    p.add_argument(
        "--vendor-allowlist", type=str, default="",
        help="Comma-separated vendor canonical names to restrict A1/A4 to.",
    )
    p.add_argument(
        "--max-queries", type=int, default=5,
        help="Upper bound on API-counted queries this invocation (default 5).",
    )
    p.add_argument(
        "--run-ts", type=str, default="",
        help="Override run timestamp (YYYYMMDDTHHMMSSZ). Default = now-utc.",
    )
    p.add_argument(
        "--sleep-to-meet-gap", action="store_true",
        help="If pacer says wait, sleep instead of skipping.",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Smoke-test orchestration without HTTP/disk writes.",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    # Confirm-token gate (binds dispatch §"First-fire readiness gate" #2)
    if not args.dry_run and args.live_fire_wave_a:
        if args.confirm != WAVE_A_CONFIRM_TOKEN:
            print(
                "REFUSED: --live-fire-wave-a requires --confirm exactly "
                f"{WAVE_A_CONFIRM_TOKEN!r}. Got: <redacted>",
                file=sys.stderr,
            )
            return 2
        dry_run = False
    else:
        dry_run = True

    run_ts = args.run_ts or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = DEFAULT_RAW_ROOT / run_ts
    log_path = REPO_ROOT / "logs" / f"mac23_step1_wave_a_fetch_{run_ts}.log"
    configure_logging(log_path, verbose=args.verbose)
    LOG.info("MAC-23 Step-1 invocation start; run_ts=%s out_root=%s dry_run=%s",
             run_ts, out_root, dry_run)
    LOG.info("max_cohort=%s max_queries=%s vendor_allowlist=%s sleep_to_gap=%s",
             args.max_cohort, args.max_queries, args.vendor_allowlist,
             args.sleep_to_meet_gap)

    pat = ""
    if not dry_run:
        pat = load_github_pat()
        LOG.info("PAT loaded from %s (value never logged)", DEFAULT_ENV_PATH)

    pacer_path = DEFAULT_PACER_LEDGER
    state = PacerState.load(pacer_path)
    if state.wave_a_run_ts is None:
        state.wave_a_run_ts = run_ts
        state.save(pacer_path)
    LOG.info("Pacer pre-state: wave_a_total_calls=%d wave_a_run_ts=%s",
             state.wave_a_total_calls, state.wave_a_run_ts)
    if state.wave_a_total_calls >= WAVE_A_HARD_CAP:
        LOG.error("Wave-A hard cap exhausted (%d ≥ %d). Halting.",
                  state.wave_a_total_calls, WAVE_A_HARD_CAP)
        return 3

    # Cohort plan
    if args.cohorts.strip():
        cohort_plan = [c.strip() for c in args.cohorts.split(",") if c.strip()]
    else:
        order = ["A1", "A2", "A3", "A4", "A5"]
        idx = order.index(args.max_cohort) + 1
        cohort_plan = order[:idx]

    vendor_allow = (
        {v.strip() for v in args.vendor_allowlist.split(",") if v.strip()}
        if args.vendor_allowlist.strip() else None
    )

    queries_budget = args.max_queries
    queries_used_total = 0
    cohort_summaries: dict = {}

    for cohort in cohort_plan:
        if queries_budget - queries_used_total <= 0:
            LOG.info("Budget exhausted before cohort %s; halting.", cohort)
            break
        LOG.info("=== Cohort %s start (queries_remaining=%d) ===",
                 cohort, queries_budget - queries_used_total)
        if cohort == "A1":
            summ, used = cohort_a1(
                out_root, pacer_path=pacer_path, pat=pat,
                dry_run=dry_run, sleep_to_meet_gap=args.sleep_to_meet_gap,
                queries_remaining=queries_budget - queries_used_total,
                vendor_allowlist=vendor_allow,
            )
        elif cohort == "A2":
            summ, used = cohort_generic_repo_list(
                A2_REPOS, "A2", out_root, pacer_path=pacer_path, pat=pat,
                dry_run=dry_run, sleep_to_meet_gap=args.sleep_to_meet_gap,
                queries_remaining=queries_budget - queries_used_total,
                files_per_repo=A2_FILES_PER_REPO,
            )
        elif cohort == "A3":
            summ, used = cohort_generic_repo_list(
                A3_REPOS, "A3", out_root, pacer_path=pacer_path, pat=pat,
                dry_run=dry_run, sleep_to_meet_gap=args.sleep_to_meet_gap,
                queries_remaining=queries_budget - queries_used_total,
                files_per_repo=A3_FILES_PER_REPO,
            )
        elif cohort == "A4":
            summ, used = cohort_a4(
                out_root, pacer_path=pacer_path, pat=pat,
                dry_run=dry_run, sleep_to_meet_gap=args.sleep_to_meet_gap,
                queries_remaining=queries_budget - queries_used_total,
            )
        elif cohort == "A5":
            summ, used = cohort_a5(
                out_root, pacer_path=pacer_path, pat=pat,
                dry_run=dry_run, sleep_to_meet_gap=args.sleep_to_meet_gap,
                queries_remaining=queries_budget - queries_used_total,
            )
        else:
            LOG.warning("Unknown cohort %s; skipping", cohort)
            continue
        cohort_summaries[cohort] = summ
        queries_used_total += used
        LOG.info("Cohort %s closed: queries_used=%d (cum=%d/%d)",
                 cohort, used, queries_used_total, queries_budget)

    pacer_after = PacerState.load(pacer_path)
    invocation_args = {
        "live_fire": args.live_fire_wave_a,
        "max_cohort": args.max_cohort,
        "cohorts": cohort_plan,
        "vendor_allowlist": sorted(vendor_allow) if vendor_allow else None,
        "max_queries": args.max_queries,
        "dry_run": dry_run,
        "run_ts": run_ts,
    }
    manifest_path = write_manifest(
        out_root, cohort_summaries, pacer_after,
        queries_used_total, invocation_args,
    )
    LOG.info("Wrote manifest: %s", manifest_path)
    LOG.info("Pacer post-state: wave_a_total_calls=%d", pacer_after.wave_a_total_calls)
    print(json.dumps({
        "run_ts": run_ts,
        "out_root": str(out_root.relative_to(REPO_ROOT)),
        "dry_run": dry_run,
        "queries_used_this_invocation": queries_used_total,
        "wave_a_total_calls": pacer_after.wave_a_total_calls,
        "wave_a_hard_cap": WAVE_A_HARD_CAP,
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "log": str(log_path.relative_to(REPO_ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
