"""MAC-13 Wave B Step 1 — raw vendor doc fetch + manifest persistence.

Bible §7.2 SourceWorker scope:
- Always preserve raw response in raw/vendor_docs/<UTC-ts>/<slug>/ BEFORE any parsing
- Custom ArgusSourceWorker/0.1 UA (NOT ClaudeBot — DroneShield AI-UA blocks not engaged)
- 2s inter-request spacing minimum (SoundThinking 10s respected)
- Sequential, not parallel
- On non-200: log failure; preserve byte stream regardless of status; do NOT retry
- On TLS failure: log + skip; DO NOT use -k insecure bypass per SAR-4 spirit

Step 1 = pure raw-fetch + sha256 + manifest. NO parsing. NO DB writes. NO extraction.

Hard ceiling: 1,500 cumulative HTTP calls. Stops with comment-and-reassign if projected
to exceed.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ARGUS_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ARGUS_ROOT / "scripts"))

from vendor_docs_step1_targets import (  # noqa: E402
    VENDORS,
    DOCUMENTED_SKIPS,
    DEFERRED_RATIFICATION,
)

USER_AGENT = (
    "ArgusSourceWorker/0.1 (Phase4 Wave B Step 1 raw fetch; "
    "+https://github.com/argus-project)"
)
HARD_CEILING_CALLS = 1500
PER_VENDOR_CAP = 50  # SAR-6 / Item 3 ratified
TIMEOUT_S = 30.0


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_filename_from_url(url: str, kind: str, idx: int) -> str:
    """Derive a stable, audit-friendly filename from URL + kind + ordinal index."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path_seg = parsed.path.strip("/").replace("/", "_") or "root"
    if len(path_seg) > 80:
        path_seg = path_seg[:80]
    ext_map = {
        "robots": ".txt",
        "sitemap": ".xml",
        "fcc_search": ".html",
    }
    ext = ext_map.get(kind, ".html")
    return f"{idx:02d}_{kind}_{path_seg}{ext}"


def fetch_url(url: str, timeout: float = TIMEOUT_S) -> dict:
    """Fetch a URL with custom UA. Always returns dict with status, body, error.

    Never raises — failures are captured into the manifest entry.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            elapsed = time.time() - started
            return {
                "status": resp.status,
                "final_url": resp.url,
                "headers": dict(resp.headers),
                "body": body,
                "elapsed_s": round(elapsed, 3),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read() or b""
        except Exception:  # pragma: no cover
            body = b""
        elapsed = time.time() - started
        return {
            "status": e.code,
            "final_url": e.url if hasattr(e, "url") and e.url else url,
            "headers": dict(e.headers) if e.headers else {},
            "body": body,
            "elapsed_s": round(elapsed, 3),
            "error": f"http_{e.code}",
        }
    except (urllib.error.URLError, ssl.SSLError, ssl.SSLCertVerificationError) as e:
        elapsed = time.time() - started
        reason = getattr(e, "reason", str(e))
        return {
            "status": None,
            "final_url": url,
            "headers": {},
            "body": b"",
            "elapsed_s": round(elapsed, 3),
            "error": f"url_error: {reason!s}",
        }
    except (socket.timeout, TimeoutError) as e:
        elapsed = time.time() - started
        return {
            "status": None,
            "final_url": url,
            "headers": {},
            "body": b"",
            "elapsed_s": round(elapsed, 3),
            "error": f"timeout: {e!s}",
        }
    except Exception as e:  # pragma: no cover (network/unexpected)
        elapsed = time.time() - started
        return {
            "status": None,
            "final_url": url,
            "headers": {},
            "body": b"",
            "elapsed_s": round(elapsed, 3),
            "error": f"unexpected: {type(e).__name__}: {e!s}",
        }


def persist_response(
    out_dir: Path,
    fname: str,
    body: bytes,
) -> tuple[str, int, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fpath = out_dir / fname
    fpath.write_bytes(body)
    return str(fpath.relative_to(ARGUS_ROOT)), len(body), sha256_hex(body)


def fetch_vendor(vendor: dict, batch_root: Path, call_budget: dict) -> dict:
    slug = vendor["slug"]
    out_dir = batch_root / slug
    delay = float(vendor.get("crawl_delay_s", 2.0))
    entries = []

    # Build URL list: robots first, then declared URLs.
    fetch_list = [("robots", vendor["robots_url"])]
    fetch_list.extend(vendor["urls"])

    # FCC EAS GenericSearch per known grantee.
    for code in vendor.get("fcc_grantees", []) or []:
        fcc_url = (
            "https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm"
            f"?application_purpose=&grantee_code={code}&product_code=&applicant_name="
            "&grant_date_from=&grant_date_to=&comments="
        )
        fetch_list.append(("fcc_search", fcc_url))

    print(f"\n=== {slug} ({len(fetch_list)} URLs, delay={delay}s) ===", flush=True)
    vendor_calls = 0

    for idx, (kind, url) in enumerate(fetch_list):
        if call_budget["used"] >= HARD_CEILING_CALLS:
            entries.append({
                "ordinal": idx,
                "kind": kind,
                "doc_url": url,
                "status": None,
                "error": "stopped_at_hard_ceiling_1500",
                "byte_count": 0,
                "sha256": None,
            })
            print(f"  STOP: hard ceiling 1500 reached", flush=True)
            break
        if vendor_calls >= PER_VENDOR_CAP:
            entries.append({
                "ordinal": idx,
                "kind": kind,
                "doc_url": url,
                "status": None,
                "error": "stopped_at_per_vendor_cap_50",
                "byte_count": 0,
                "sha256": None,
            })
            print(f"  STOP: per-vendor cap 50 reached for {slug}", flush=True)
            break

        if idx > 0:
            time.sleep(delay)

        result = fetch_url(url)
        call_budget["used"] += 1
        vendor_calls += 1

        fname = safe_filename_from_url(result["final_url"] or url, kind, idx)
        rel_path, byte_count, sha = persist_response(out_dir, fname, result["body"])

        entry = {
            "ordinal": idx,
            "kind": kind,
            "doc_url": url,
            "final_url": result["final_url"],
            "status": result["status"],
            "byte_count": byte_count,
            "sha256": sha,
            "content_type": result["headers"].get("Content-Type") if result["headers"] else None,
            "elapsed_s": result["elapsed_s"],
            "raw_path_relative": rel_path,
        }
        if result["error"]:
            entry["error"] = result["error"]
        print(
            f"  [{call_budget['used']:4d}] {kind:18s} {result['status']!s:>5s}  "
            f"{byte_count:>9d}B  {sha[:16]}  {url[:90]}",
            flush=True,
        )
        entries.append(entry)

    return {
        "vendor_slug": slug,
        "vendor_canonical": vendor["canonical"],
        "robots_routing": vendor["robots_note"],
        "license_observation": vendor["license_observation"],
        "fcc_grantees": vendor.get("fcc_grantees", []) or [],
        "crawl_delay_s": delay,
        "calls_used": vendor_calls,
        "entries": entries,
    }


def fetch_brinc_first_attempt(deferred: dict, batch_root: Path, call_budget: dict) -> dict:
    """One-shot canonical-host probe to formally confirm TLS-broken; surfaces ratification."""
    slug = deferred["slug"]
    out_dir = batch_root / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for idx, (kind, url) in enumerate([
        ("robots", deferred["robots_url"]),
        ("primary_host_probe", deferred["primary_url"]),
    ]):
        if idx > 0:
            time.sleep(2.0)
        result = fetch_url(url)
        call_budget["used"] += 1
        fname = safe_filename_from_url(url, kind, idx)
        rel_path, byte_count, sha = persist_response(out_dir, fname, result["body"])
        entries.append({
            "ordinal": idx,
            "kind": kind,
            "doc_url": url,
            "final_url": result["final_url"],
            "status": result["status"],
            "byte_count": byte_count,
            "sha256": sha,
            "elapsed_s": result["elapsed_s"],
            "raw_path_relative": rel_path,
            "error": result["error"],
        })
        print(
            f"  [BRINC {idx}] {kind:25s} status={result['status']} "
            f"err={result['error']!s} bytes={byte_count}",
            flush=True,
        )

    return {
        "vendor_slug": slug,
        "vendor_canonical": deferred["canonical"],
        "deferred_reason": deferred["deferred_reason"],
        "first_encounter_probe": entries,
        "ratification_requested": True,
    }


def main() -> int:
    batch_ts = utc_timestamp()
    batch_root = ARGUS_ROOT / "raw" / "vendor_docs" / batch_ts
    batch_root.mkdir(parents=True, exist_ok=True)

    print(f"Batch root: {batch_root}")
    print(f"Hard ceiling: {HARD_CEILING_CALLS} HTTP calls aggregate")
    print(f"Per-vendor cap: {PER_VENDOR_CAP} calls")
    print(f"User-Agent: {USER_AGENT}")
    print(f"Vendors: {len(VENDORS)} fetch + {len(DEFERRED_RATIFICATION)} deferred + {len(DOCUMENTED_SKIPS)} skip-documented")
    print()

    started = time.time()
    call_budget = {"used": 0}
    vendor_reports = []

    for vendor in VENDORS:
        report = fetch_vendor(vendor, batch_root, call_budget)
        vendor_reports.append(report)
        if call_budget["used"] >= HARD_CEILING_CALLS:
            print(f"\nStopping further vendors — hard ceiling {HARD_CEILING_CALLS} reached.")
            break

    brinc_report = None
    if call_budget["used"] < HARD_CEILING_CALLS:
        for deferred in DEFERRED_RATIFICATION:
            print(f"\n=== {deferred['slug']} (deferred-ratification first-encounter probe) ===")
            brinc_report = fetch_brinc_first_attempt(deferred, batch_root, call_budget)

    elapsed_total_s = round(time.time() - started, 1)
    elapsed_min = round(elapsed_total_s / 60.0, 2)

    # Aggregate stats
    total_bytes = 0
    docs_count = 0
    for r in vendor_reports:
        for e in r["entries"]:
            total_bytes += e["byte_count"]
            docs_count += 1
    if brinc_report:
        for e in brinc_report["first_encounter_probe"]:
            total_bytes += e["byte_count"]
            docs_count += 1

    manifest = {
        "manifest_version": 1,
        "step": "MAC-13 Phase 4 Wave B Step 1 — raw fetch + manifest (NO parsing, NO db writes, NO extraction)",
        "captured_at_utc": batch_ts,
        "user_agent": USER_AGENT,
        "step0_predecessor_batch": "raw/vendor_docs/20260505T033814Z/",
        "vendors_fetched": vendor_reports,
        "deferred_ratification": [brinc_report] if brinc_report else [],
        "documented_skips": [
            {
                "vendor_slug": s["slug"],
                "vendor_canonical": s["canonical"],
                "skip_reason": s["skip_reason"],
                "robots_routing_evidence": s["robots_routing_evidence"],
                "fetched": s["fetched"],
            }
            for s in DOCUMENTED_SKIPS
        ],
        "aggregate_stats": {
            "vendors_fetched_count": len(vendor_reports),
            "deferred_ratification_count": 1 if brinc_report else 0,
            "documented_skips_count": len(DOCUMENTED_SKIPS),
            "total_http_calls_used": call_budget["used"],
            "hard_ceiling": HARD_CEILING_CALLS,
            "per_vendor_cap": PER_VENDOR_CAP,
            "wall_clock_seconds": elapsed_total_s,
            "wall_clock_minutes": elapsed_min,
            "total_raw_bytes_persisted": total_bytes,
            "total_docs_persisted": docs_count,
        },
        "bible_compliance": {
            "section_7_2_raw_preservation": "all bytes persisted to raw/vendor_docs/<UTC-ts>/<slug>/ BEFORE any parsing; no parsing performed",
            "section_7_2_user_agent": f"custom UA = {USER_AGENT}; NOT ClaudeBot (DroneShield AI-UA blocks not engaged)",
            "section_7_2_inter_request_spacing": "min 2s; SoundThinking 10s per Crawl-delay: 10",
            "section_7_2_sequential_not_parallel": "single-threaded urllib.request, sequential per-vendor and per-URL",
            "section_7_2_no_retry": "non-200 logged + persisted; URL-amendment is a separate manual decision (deferred to follow-up if needed)",
            "section_11_1_no_fabrication": "404/non-200/TLS failures recorded as-is; no synthetic content",
            "section_11_6_robots": "robots.txt fetched first per vendor; SAR-4 routing applied (Cradlepoint, Getac, Berla skip, BRINC deferred)",
            "section_11_2_no_authenticated_content": "Cellebrite/Magnet customer-only docs not fetched; only public marketing surface",
            "no_db_writes": "zero raw_observations rows authored; zero migration committed; zero ingest module created",
            "no_extraction": "Step 2 (Extraction Worker post-hire-approval) territory; not performed in Step 1",
        },
    }

    manifest_path = batch_root / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written: {manifest_path}")
    print(
        f"Aggregate: {len(vendor_reports)} vendors fetched, "
        f"{call_budget['used']} HTTP calls, "
        f"{total_bytes / 1024 / 1024:.2f} MiB persisted, "
        f"{elapsed_min} min wall-clock"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
