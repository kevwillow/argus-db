"""MAC-14 Wave B Step 1.5 — BRINC Wayback fallback raw fetch + manifest append.

Bible §7.2 SourceWorker scope; SAR-4 spirit (legitimate alt-routing for TLS-broken
primary host, NOT a robots.txt bypass).

Hard cap: 6 calls (1 Wayback robots.txt + 3 product snapshots + up to 2 amends).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ARGUS_ROOT = Path(__file__).resolve().parent.parent
BATCH_DIR = ARGUS_ROOT / "raw" / "vendor_docs" / "20260505T040929Z"
BRINC_DIR = BATCH_DIR / "brinc"
MANIFEST_PATH = BATCH_DIR / "_manifest.json"
LOG_PATH = ARGUS_ROOT / "logs" / "mac14_brinc_wayback.log"

USER_AGENT = (
    "ArgusSourceWorker/0.1 (Phase4 Wave B Step 1.5 BRINC Wayback fallback; "
    "+https://github.com/argus-project)"
)
SPACING_S = 2.0
TIMEOUT_S = 30.0
HARD_CAP = 6

WAYBACK_PREFIX = "https://web.archive.org/web/2024/"

# Ratified targets per MAC-14 dispatch.
TARGETS = [
    {
        "kind": "robots",
        "original_url": "https://web.archive.org/robots.txt",
        "wayback_url": "https://web.archive.org/robots.txt",
        "is_wayback_self": True,
    },
    {
        "kind": "product_landing",
        "original_url": "https://www.brinc.com/lemur",
        "wayback_url": WAYBACK_PREFIX + "https://www.brinc.com/lemur",
        "is_wayback_self": False,
    },
    {
        "kind": "product_landing",
        "original_url": "https://www.brinc.com/responder",
        "wayback_url": WAYBACK_PREFIX + "https://www.brinc.com/responder",
        "is_wayback_self": False,
    },
    {
        "kind": "homepage",
        "original_url": "https://www.brinc.com/",
        "wayback_url": WAYBACK_PREFIX + "https://www.brinc.com/",
        "is_wayback_self": False,
    },
]


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def log_line(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{utc_now_iso()} {msg}\n")
    print(msg, flush=True)


def fetch_url(url: str, timeout: float = TIMEOUT_S) -> dict:
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
        except Exception:
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
    except Exception as e:
        elapsed = time.time() - started
        return {
            "status": None,
            "final_url": url,
            "headers": {},
            "body": b"",
            "elapsed_s": round(elapsed, 3),
            "error": f"unexpected: {type(e).__name__}: {e!s}",
        }


def filename_for(idx: int, kind: str, original_url: str, is_wayback_self: bool) -> str:
    parsed = urlparse(original_url)
    if is_wayback_self:
        path_seg = "wayback_robots"
        ext = ".txt"
    else:
        path_seg = parsed.path.strip("/").replace("/", "_") or "root"
        if len(path_seg) > 80:
            path_seg = path_seg[:80]
        ext = ".html" if kind != "robots" else ".txt"
    return f"{idx:02d}_{kind}_{path_seg}{ext}"


def detect_wayback_snapshot_timestamp(final_url: str, headers: dict) -> str | None:
    """Wayback redirects /web/2024/<url> to /web/<YYYYMMDDhhmmss>/<url>.
    Extract that 14-digit code from the final_url path.
    """
    if "web.archive.org" not in final_url:
        return None
    parsed = urlparse(final_url)
    parts = parsed.path.strip("/").split("/")
    # path like: web/20240517123045/https://www.brinc.com/lemur
    if len(parts) >= 2 and parts[0] == "web" and parts[1].isdigit() and len(parts[1]) >= 8:
        return parts[1]
    # X-Archive-Orig-* / Memento-Datetime header fallback
    memento = headers.get("Memento-Datetime") or headers.get("X-Archive-Orig-Date")
    return memento


def main() -> int:
    if not BATCH_DIR.exists():
        log_line(f"FATAL: batch dir missing: {BATCH_DIR}")
        return 2
    if not MANIFEST_PATH.exists():
        log_line(f"FATAL: manifest missing: {MANIFEST_PATH}")
        return 2

    BRINC_DIR.mkdir(parents=True, exist_ok=True)

    # First call: Wayback robots.txt — must inspect before any /web/ snapshot fetch.
    log_line("MAC-14 BRINC Wayback fallback starting.")
    log_line(f"User-Agent: {USER_AGENT}")
    log_line(f"Hard cap: {HARD_CAP} calls. Spacing: {SPACING_S}s.")

    calls_used = 0
    entries: list[dict] = []
    aborted_reason: str | None = None

    # Existing TLS-probe stubs occupy ordinals 0 and 1; new entries start at 2.
    starting_ordinal = 2

    for i, target in enumerate(TARGETS):
        if calls_used >= HARD_CAP:
            aborted_reason = "hard_cap_reached"
            break

        ordinal = starting_ordinal + i

        if i > 0:
            time.sleep(SPACING_S)

        url = target["wayback_url"]
        log_line(f"[{ordinal}] GET {url}")
        resp = fetch_url(url)
        calls_used += 1

        # Stop-line: captcha / 429 / 403 on first request → abort.
        if i == 0 and resp["status"] in (429, 403):
            aborted_reason = f"wayback_robots_blocked_status={resp['status']}"
            log_line(f"STOP-LINE: {aborted_reason}")
            entry = build_entry(ordinal, target, resp, None)
            entries.append(entry)
            break

        snap_ts = (
            detect_wayback_snapshot_timestamp(resp["final_url"], resp["headers"])
            if not target["is_wayback_self"]
            else None
        )
        entry = build_entry(ordinal, target, resp, snap_ts)
        entries.append(entry)

        # Persist body regardless of status (audit trail), even on 404 / blackhole.
        fname = filename_for(
            ordinal, target["kind"], target["original_url"], target["is_wayback_self"]
        )
        out_path = BRINC_DIR / fname
        out_path.write_bytes(resp["body"])
        entry["raw_path_relative"] = str(out_path.relative_to(ARGUS_ROOT))
        entry["byte_count"] = len(resp["body"])
        entry["sha256"] = sha256_hex(resp["body"])
        log_line(
            f"    status={resp['status']} bytes={entry['byte_count']} "
            f"sha256={entry['sha256'][:12]}... snap={snap_ts}"
        )

        # If wayback robots returns 200 and contains "Disallow: /web/", we MUST stop.
        if i == 0 and resp["status"] == 200:
            txt = resp["body"].decode("utf-8", errors="replace")
            entry["robots_body_excerpt"] = txt[:500]
            if "Disallow: /web/" in txt:
                aborted_reason = "wayback_robots_disallows_/web/"
                log_line(f"STOP-LINE: {aborted_reason}")
                break

    # Append BRINC vendor entry to manifest.
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    brinc_vendor_entry = {
        "vendor_slug": "brinc",
        "vendor_canonical": "BRINC",
        "robots_routing": (
            "Primary host www.brinc.com TLS-broken (cert verify failed at MAC-13 "
            "Step 1, see 01_primary_host_probe_lemur.html — 0 bytes captured "
            "during failure). Wayback Machine used as legitimate alt-routing for "
            "TLS-broken primary (SAR-4 spirit: alt-routing applies to genuine "
            "delivery failure, NOT robots.txt circumvention). Wayback own "
            "robots.txt fetched first (entry ordinal 02); see robots_body_excerpt "
            "for verbatim posture."
        ),
        "license_observation": (
            "Wayback Machine preserves source license. BRINC original copyright "
            "text (if present in archived snapshots) noted per-entry; Wayback "
            "itself is Internet Archive's archive infrastructure (CC-style "
            "preservation, source content remains under origin license)."
        ),
        "fcc_grantees": [],
        "crawl_delay_s": SPACING_S,
        "calls_used": calls_used,
        "wayback_fallback": True,
        "step1_5_ratification": "MAC-14",
        "step1_5_predecessor": "MAC-13 §3.4 (TLS-broken primary host probe)",
        "tls_probe_artifacts": [
            "raw/vendor_docs/20260505T040929Z/brinc/00_robots_robots.txt.txt",
            "raw/vendor_docs/20260505T040929Z/brinc/01_primary_host_probe_lemur.html",
        ],
        "aborted_reason": aborted_reason,
        "entries": entries,
    }

    # Avoid duplicate insertion if re-run: replace existing brinc entry if present.
    existing_idx = next(
        (j for j, v in enumerate(manifest["vendors_fetched"]) if v.get("vendor_slug") == "brinc"),
        None,
    )
    if existing_idx is not None:
        manifest["vendors_fetched"][existing_idx] = brinc_vendor_entry
    else:
        manifest["vendors_fetched"].append(brinc_vendor_entry)

    # Update aggregate_stats if present.
    agg = manifest.get("aggregate_stats")
    if isinstance(agg, dict):
        agg["mac14_step1_5_brinc_calls"] = calls_used
        agg["mac14_step1_5_brinc_entries"] = len(entries)

    # Stamp a step1_5 metadata block.
    manifest.setdefault("step1_5_appendices", []).append(
        {
            "ratification": "MAC-14",
            "vendor_slug": "brinc",
            "captured_at_utc": utc_now_iso(),
            "calls_used": calls_used,
            "aborted_reason": aborted_reason,
        }
    )

    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=False)
        f.write("\n")

    log_line(f"BRINC entry appended. calls_used={calls_used} aborted={aborted_reason}")
    print(json.dumps({"calls_used": calls_used, "entries_n": len(entries), "aborted_reason": aborted_reason}))
    return 0


def build_entry(ordinal: int, target: dict, resp: dict, snap_ts: str | None) -> dict:
    return {
        "ordinal": ordinal,
        "kind": target["kind"],
        "original_url": target["original_url"],
        "wayback_url": target["wayback_url"],
        "wayback_fallback": not target["is_wayback_self"],
        "is_wayback_self": target["is_wayback_self"],
        "doc_url": target["wayback_url"],
        "final_url": resp["final_url"],
        "wayback_snapshot_timestamp": snap_ts,
        "status": resp["status"],
        "elapsed_s": resp["elapsed_s"],
        "content_type": resp["headers"].get("Content-Type", ""),
        "error": resp["error"],
    }


if __name__ == "__main__":
    sys.exit(main())
