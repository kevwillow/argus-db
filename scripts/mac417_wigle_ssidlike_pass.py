#!/usr/bin/env python3
"""MAC-417 — Cohort-1 bounded WiGLE confirmation pass (spy-cam default-SSID slice).

SourceWorker, STAGE ONLY. Board-approved bounded WiGLE pass under MAC-393 §10.
Does NOT write to db/argus.db. Does NOT extract structured candidates. The only
mutation outside this script's deliverable files is the shared quota ledger
`wigle/pacer.json` (required by source-triage §10 so the daily 100 q/day cap
stays honest across the geo-anchor wave and this ssidlike pass).

What this is (and is NOT)
─────────────────────────
This is a *confirmation* pass: for each cite-pasted spy-cam default-SSID family
(CTO-verified GREEN at MAC-394), it asks WiGLE "does this SSID pattern actually
appear in the wild, and roughly how often?" via one `ssidlike=<prefix>%` query.
It is NOT brute enumeration and NOT geolocation harvesting.

Query mode vs the existing module
─────────────────────────────────
`db/sources/wigle.py` implements the *bbox/anchor* query mode (Flock T1 MD geo
wave, MAC-9). This pass needs the *ssidlike* mode, which that module does not
expose. We reuse its credential loader, on-disk pacer ledger, quota-signal
parser, and SAR-5 SSID redaction primitive — but add ssidlike fetch + PII-scrub
+ file-only outputs here.

Pacing
──────
- §10 hard ceiling: ≤30 queries for the whole bounded pass (paging absorbed).
- Daily cap: 100 q/day (pacer ledger, rollover-aware).
- The 15-min inter-query gap / 4 q-per-hour pacing was the *geo wave's* dispatch
  pacing (MAC-9 251a65f3 / MAC-1 bd667afb #2). §10's ssidlike plan states no
  per-query gap and contemplates ~15-20 queries in a *single* pass, so the gap
  is intentionally NOT applied here. We are still a good API citizen via a short
  inter-request delay and a single page per pattern by default.

PII (§11 #3 — absolute) reconciliation with provenance (§11 #7)
──────────────────────────────────────────────────────────────
WiGLE ssidlike results carry raw `netid` (BSSID) + `trilat`/`trilong` +
street-level fields — exactly the "raw individual BSSID+geolocation tuple that
could locate a person's home camera" the brief forbids. So:
  * We NEVER persist netid, trilat, trilong, housenumber, road, city, postalcode.
  * We persist only aggregates: total wild-count, page result count, redacted
    distinct-SSID samples (proof the matches are camera-class, not coincidental),
    and a coarse country distribution (non-home-locating).
  * For tamper-evident provenance we record the sha256 + byte-count of the FULL
    raw response, and the exact query URL + UTC timestamp. The on-disk raw
    envelope under wigle/raw/mac393/ (gitignored) stores only the PII-scrubbed
    per-record subset — never the locating tuple.

Idempotency
───────────
Re-running is a no-op for any (ssidlike pattern) already fired on the same UTC
day (detected from the spend log) unless --force is given — so an accidental
re-run never double-spends quota.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Import the audited primitives from the canonical WiGLE module.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from db.sources.wigle import (  # noqa: E402
    DEFAULT_ENV_PATH,
    DEFAULT_PACER_LEDGER,
    SEARCH_ENDPOINT,
    WIGLE_DAILY_QUOTA,
    PacerState,
    _basic_auth_header,
    _load_wigle_creds,
    parse_quota_signal,
    record_pacer_fire,
    redact_ssid_pii,
)

# ── Pass governance constants ────────────────────────────────────────────────
MAC393_PASS_CEILING = 30          # source-triage §10 hard ceiling for THIS pass
MAX_PAGES_PER_PATTERN = 3         # §10: ≤3 pages each; only paged when saturated
RESULTS_PER_PAGE = 100            # WiGLE site-auth max
POLITE_DELAY_S = 2.0              # good-citizen inter-request delay (NOT the 15m gap)
HTTP_TIMEOUT = 60

RAW_ROOT = REPO_ROOT / "wigle" / "raw" / "mac393"
OUT_DIR = REPO_ROOT / "extraction_outputs" / "mac393_c1_spycam"
SPEND_LOG = OUT_DIR / "wigle_spend_log.jsonl"
RESULTS_JSON = OUT_DIR / "wigle_results.json"

# Per-record fields we are willing to keep (everything else, incl. netid + all
# precise geo, is dropped before anything touches disk). SSID is redacted on top.
SAFE_RECORD_FIELDS = ("type", "encryption", "channel", "freenet", "country", "region")

# ── Deduped, high-yield ssidlike query list (spy-cam default-SSID slice ONLY) ─
# Each entry traces to a CTO-verified cite-paste in ssid_pattern_family.json /
# MAC-394 cto_verify_gate.md (claim D). `ssidlike` is the SQL-LIKE prefix.
QUERIES: list[dict] = [
    # ── 4 core companion-APK families ──
    {"family": "V380", "ssidlike": "V380%",
     "trace": "V380 Pro APK com.macrovideo.v380pro dex: V380_/V380_Pro (MAC-394 claim D)"},
    {"family": "V380 (vendor AP token)", "ssidlike": "MVSPT%",
     "trace": "V380 dex MVSPT_/parseDeviceIDFormAPName; precise form of broad 'MV%' alt "
              "(bare MV% dropped: 2-char prefix, near-zero precision for confirmation)"},
    {"family": "iCSee/Xiongmai", "ssidlike": "iCSee%",
     "trace": "iCSee APK com.xm.csee dex: iCSee/ICSEEHOME_NAME (broad 'XM%' device-id alt "
              "dropped: 2-char prefix, near-zero precision; iCSee% covers the family)"},
    {"family": "CamHi/HiChip", "ssidlike": "IPCAM-%",
     "trace": "CamHi Pro APK com.hichip.campro dex: IPCAM- (hyphen anchors precision)"},
    {"family": "CamHi/HiChip (alt)", "ssidlike": "CamHipro%",
     "trace": "CamHi Pro dex: CamHipro-%04d"},
    {"family": "HDMiniCam", "ssidlike": "HDMiniCam%",
     "trace": "HDMiniCam APK com.g_zhang.HDMiniCam dex tokens + set_wifi.cgi"},
    {"family": "HDMiniCam (HHMiniCam)", "ssidlike": "HHMiniCam%",
     "trace": "HDMiniCam ESNAPP_* enum sibling HHMINICAM"},
    {"family": "HDMiniCam (iMiniCam)", "ssidlike": "iMiniCam%",
     "trace": "HDMiniCam ESNAPP_* enum sibling IMINICAM"},
    {"family": "HDMiniCam (HCAM)", "ssidlike": "HCAM%",
     "trace": "HDMiniCam family HCAM prefix"},
    # ── high-signal ESNAPP white-label brands (per issue hard bound) ──
    {"family": "ESNAPP MATECAM", "ssidlike": "MATECAM%",
     "trace": "ESNAPP_* enum brand MATECAM (HDMiniCam/g_zhang)"},
    {"family": "ESNAPP EUROSPY", "ssidlike": "EUROSPY%",
     "trace": "ESNAPP_* enum brand EUROSPY"},
    {"family": "ESNAPP BVCAM", "ssidlike": "BVCAM%",
     "trace": "ESNAPP_* enum brand BVCAM"},
    {"family": "ESNAPP SPYSITE", "ssidlike": "SPYSITE%",
     "trace": "ESNAPP_* enum brand SPYSITE"},
    {"family": "ESNAPP SKYEYE", "ssidlike": "SKYEYE%",
     "trace": "ESNAPP_* enum brand SKYEYE"},
    {"family": "ESNAPP BLACKLENS", "ssidlike": "BLACKLENS%",
     "trace": "ESNAPP_* enum brand BLACKLENS"},
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_name(ssidlike: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in ssidlike).strip("_")


def fetch_ssidlike(
    *, ssidlike: str, api_name: str, api_token: str,
    search_after: Optional[str] = None,
) -> tuple[bytes, int, dict[str, str]]:
    """Single GET to /api/v2/network/search?ssidlike=<pattern>. No retries."""
    params = {"ssidlike": ssidlike, "resultsPerPage": str(RESULTS_PER_PAGE)}
    if search_after:
        params["searchAfter"] = search_after
    url = f"{SEARCH_ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, method="GET",
        headers={
            "User-Agent": "argus-ingest/0.1 (+contact: argus-ingest)",
            "Accept": "application/json",
            "Authorization": _basic_auth_header(api_name, api_token),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return resp.read(), (resp.getcode() or 0), dict(resp.getheaders())
    except urllib.error.HTTPError as e:
        payload = e.read() if hasattr(e, "read") else b""
        headers = dict(e.headers.items()) if e.headers else {}
        return payload, e.code, headers


def _scrub_record(rec: dict) -> dict:
    """Keep only SAFE_RECORD_FIELDS + redacted ssid. Drops netid + all precise geo."""
    ssid_raw = str(rec.get("ssid") or "")
    ssid_red, _hits = redact_ssid_pii(ssid_raw)
    out = {"ssid_redacted": ssid_red}
    for f in SAFE_RECORD_FIELDS:
        if f in rec and rec[f] is not None:
            out[f] = rec[f]
    return out


def _query_url(ssidlike: str) -> str:
    return f"{SEARCH_ENDPOINT}?" + urllib.parse.urlencode(
        {"ssidlike": ssidlike, "resultsPerPage": str(RESULTS_PER_PAGE)}
    )


def _completed_patterns_today(day_iso: str) -> set[str]:
    """Idempotency: ssidlike values already fired (page 1) on this UTC day."""
    done: set[str] = set()
    if not SPEND_LOG.exists():
        return done
    for line in SPEND_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = str(row.get("ts", ""))
        if ts[:10] == day_iso and row.get("kind") == "query":
            done.add(str(row.get("ssidlike")))
    return done


def main() -> int:
    ap = argparse.ArgumentParser(description="MAC-417 bounded WiGLE ssidlike confirmation pass")
    ap.add_argument("--force", action="store_true",
                    help="Re-fire patterns already done today (default: skip — no double-spend).")
    ap.add_argument("--max-pages", type=int, default=1,
                    help="Pages per pattern (default 1; ≤3 allowed; only pages when saturated).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Exercise everything except the HTTP call + ledger/disk writes.")
    args = ap.parse_args()
    max_pages = max(1, min(args.max_pages, MAX_PAGES_PER_PATTERN))

    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    api_name, api_token = ("DRYRUN", "DRYRUN")
    if not args.dry_run:
        api_name, api_token = _load_wigle_creds(DEFAULT_ENV_PATH)
        print("WiGLE creds loaded (HTTP Basic) — values not logged", file=sys.stderr)

    pacer = PacerState.load(DEFAULT_PACER_LEDGER)
    now = datetime.now(timezone.utc)
    day_iso = now.strftime("%Y-%m-%d")
    today_count = pacer.today_count if pacer.today_utc_iso == day_iso else 0
    print(f"pacer: today={day_iso} today_count={today_count} all_time={pacer.all_time_count} "
          f"daily_quota={WIGLE_DAILY_QUOTA}", file=sys.stderr)

    done_today = set() if args.force else _completed_patterns_today(day_iso)
    if done_today:
        print(f"idempotency: {len(done_today)} pattern(s) already fired today — skipping", file=sys.stderr)

    pass_queries_fired = 0
    results_out: list[dict] = []

    for q in QUERIES:
        ssidlike = q["ssidlike"]
        if ssidlike in done_today:
            print(f"skip (already done today): {ssidlike}", file=sys.stderr)
            continue

        # Ceiling + daily-quota guards (check BEFORE firing).
        if pass_queries_fired >= MAC393_PASS_CEILING:
            print(f"STOP: pass ceiling {MAC393_PASS_CEILING} reached", file=sys.stderr)
            break
        if today_count >= WIGLE_DAILY_QUOTA:
            print(f"STOP: daily quota {WIGLE_DAILY_QUOTA} reached", file=sys.stderr)
            break

        agg_ssid: Counter = Counter()
        agg_country: Counter = Counter()
        agg_type: Counter = Counter()
        total_results: Optional[int] = None
        page_result_counts: list[int] = []
        http_statuses: list[int] = []
        quota_hit = False
        search_after: Optional[str] = None

        for page in range(1, max_pages + 1):
            if today_count >= WIGLE_DAILY_QUOTA or pass_queries_fired >= MAC393_PASS_CEILING:
                break
            fired_at = _utc_now_iso()

            if args.dry_run:
                payload = b'{"success": true, "totalResults": 0, "results": []}'
                status, headers = 200, {"X-Argus-Dry-Run": "true"}
            else:
                payload, status, headers = fetch_ssidlike(
                    ssidlike=ssidlike, api_name=api_name, api_token=api_token,
                    search_after=search_after,
                )

            # Quota ledger: a query was issued — burn it (even on 4xx).
            today_count += 1
            pass_queries_fired += 1
            if not args.dry_run:
                pacer = record_pacer_fire(pacer, now=datetime.now(timezone.utc))
                pacer.save(DEFAULT_PACER_LEDGER)

            sha = hashlib.sha256(payload).hexdigest()
            byte_count = len(payload)
            http_statuses.append(status)

            sig = parse_quota_signal(status, headers)
            parsed = None
            try:
                parsed = json.loads(payload.decode("utf-8")) if payload else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                parsed = None

            page_results = []
            if isinstance(parsed, dict):
                if total_results is None:
                    tr = parsed.get("totalResults", parsed.get("resultCount"))
                    total_results = int(tr) if isinstance(tr, (int, float)) else None
                if isinstance(parsed.get("results"), list):
                    page_results = parsed["results"]
                search_after = parsed.get("searchAfter") or parsed.get("search_after")

            page_result_counts.append(len(page_results))
            scrubbed_records = []
            for rec in page_results:
                sr = _scrub_record(rec)
                scrubbed_records.append(sr)
                agg_ssid[sr["ssid_redacted"]] += 1
                if sr.get("country"):
                    agg_country[str(sr["country"])] += 1
                if sr.get("type"):
                    agg_type[str(sr["type"])] += 1

            # Provenance-first: write PII-SCRUBBED raw envelope (gitignored).
            if not args.dry_run:
                env = {
                    "argus_envelope": {
                        "pass": "MAC-417 cohort-1 spy-cam ssidlike",
                        "ssidlike": ssidlike, "family": q["family"], "page": page,
                        "fired_at_utc": fired_at, "http_status": status,
                        "query_url": _query_url(ssidlike),
                        "full_response_sha256": sha,
                        "full_response_byte_count": byte_count,
                        "totalResults": total_results,
                        "page_result_count": len(page_results),
                        "pii_posture": "netid + trilat/trilong + street-level fields "
                                       "DROPPED pre-disk; ssid redacted (SAR-5).",
                        "response_headers": headers,
                    },
                    "scrubbed_records": scrubbed_records,
                }
                (RAW_ROOT / f"{_safe_name(ssidlike)}-p{page}.json").write_text(
                    json.dumps(env, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            # Spend-log line (per query/page) — issue-required.
            spend_row = {
                "kind": "query", "ts": fired_at, "ssidlike": ssidlike,
                "family": q["family"], "page": page, "http_status": status,
                "results_count": len(page_results), "totalResults": total_results,
                "full_response_sha256": sha, "byte_count": byte_count,
                "pass_queries_fired": pass_queries_fired,
                "today_count": today_count, "daily_quota": WIGLE_DAILY_QUOTA,
            }
            if not args.dry_run:
                with SPEND_LOG.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(spend_row, sort_keys=True) + "\n")

            if sig.is_quota_exhausted:
                print(f"WiGLE 429 quota-exhausted on {ssidlike} p{page}; NO retries; stopping.",
                      file=sys.stderr)
                quota_hit = True
                break

            # Page only if saturated (a full page AND a cursor AND more remain).
            saturated = (len(page_results) >= RESULTS_PER_PAGE and bool(search_after)
                         and (total_results is None or total_results > sum(page_result_counts)))
            if not saturated:
                break
            time.sleep(POLITE_DELAY_S)

        observed = sum(page_result_counts)
        confirmed = bool((total_results or 0) > 0 or observed > 0)
        results_out.append({
            "family": q["family"], "ssidlike": ssidlike, "trace": q["trace"],
            "confirmed": confirmed,
            "total_results_in_wild": total_results,
            "observed_results_fetched": observed,
            "pages_fetched": len(page_result_counts),
            "http_statuses": http_statuses,
            "quota_exhausted": quota_hit,
            "band": "crowdsourced", "band_range": "50-75",
            "device_category_target": "cctv_camera",
            "ssid_samples_redacted": [
                {"ssid": s, "count": c} for s, c in agg_ssid.most_common(20)
            ],
            "country_distribution": dict(agg_country.most_common(15)),
            "type_distribution": dict(agg_type),
        })

        if not args.dry_run:
            time.sleep(POLITE_DELAY_S)
        if quota_hit:
            break

    # Machine-readable results deliverable.
    summary = {
        "pass": "MAC-417 cohort-1 spy-cam default-SSID WiGLE bounded confirmation",
        "generated_at_utc": _utc_now_iso(),
        "governance": "source-triage §10 (≤30 ceiling) + MAC-417 hard bounds; STAGE ONLY",
        "wigle_status": "LIVE" if not args.dry_run else "DRY_RUN",
        "source": SEARCH_ENDPOINT,
        "source_type": "crowdsourced", "confidence_band": "50-75",
        "pass_ceiling": MAC393_PASS_CEILING,
        "queries_fired_this_pass": pass_queries_fired,
        "daily_quota": WIGLE_DAILY_QUOTA,
        "pacer_today_count_after": today_count,
        "patterns_total": len(QUERIES),
        "patterns_confirmed": sum(1 for r in results_out if r["confirmed"]),
        "patterns_unconfirmed": sum(1 for r in results_out if not r["confirmed"]),
        "pii_posture": "Aggregate counts + redacted SSID samples only. No netid, "
                       "no trilat/trilong, no street-level fields persisted (§11 #3).",
        "lift_disposition": (
            "WiGLE confirms presence-in-wild; the APK/teardown remains the originating "
            "artifact (ssid_pattern for cctv_camera). §8.3 value-level +5 lift is NOT "
            "auto-claimed: it applies ONLY if the SAME ssid_pattern is independently "
            "attested at value level. Hub-and-spoke vendor overlap does NOT qualify. "
            "Disposition deferred to Validator battery + CTO."
        ),
        "results": results_out,
    }
    if not args.dry_run:
        RESULTS_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "wigle_status": summary["wigle_status"],
        "queries_fired_this_pass": pass_queries_fired,
        "pass_ceiling": MAC393_PASS_CEILING,
        "patterns_confirmed": summary["patterns_confirmed"],
        "patterns_unconfirmed": summary["patterns_unconfirmed"],
        "pacer_today_count_after": today_count,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
