"""MAC-31 Phase 4 Wave-D Step 1 — per-host robots.txt re-check (mandatory artifact).

§11 #6 + SAR-4 + MAC-30 ratification: re-check robots.txt for each host
BEFORE any new fetch wave. Persist robots bodies + meta sidecar; compare against
MAC-30 Step-0 robots-recheck (20260505T023704Z) to catch newly-Disallowed paths.

Hosts re-checked (Mitigation-B form):
  In-scope (will fetch):
    - www.muckrock.com               — D2 host (5s crawl-delay binds)
    - www.documentcloud.org          — D2 host (5s crawl-delay binds)
    - www.eff.org                    — D3 host (30s crawl-delay binds)
    - theintercept.com               — D4 host
    - www.propublica.org             — D5 host (sitemap-driven)
    - www.justice.gov                — D6 host

  Absence-documented (NOT fetched, recheck for compliance audit):
    - www.courtlistener.com          — Mitigation-B absence-doc'd
    - vault.fbi.gov                  — Cloudflare bot-wall absence-doc'd
    - www.aclu.org                   — /foia-document/ + /foia-collections/ disallow

NO writes to argus.db. NO LLM. Provenance + recheck only.
"""
from __future__ import annotations

import hashlib
import json
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = ("ArgusSourceWorker/0.1 (Phase4 Wave-D Step 1 robots recheck; "
      "+https://github.com/argus-project)")
TIMEOUT_S = 30
SPACING_S = 1.5

HOSTS = [
    "https://www.muckrock.com/robots.txt",
    "https://www.documentcloud.org/robots.txt",
    "https://www.eff.org/robots.txt",
    "https://theintercept.com/robots.txt",
    "https://www.propublica.org/robots.txt",
    "https://www.justice.gov/robots.txt",
    "https://www.courtlistener.com/robots.txt",
    "https://vault.fbi.gov/robots.txt",
    "https://www.aclu.org/robots.txt",
]

REPO_ROOT = Path("/home/kev/argus")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = REPO_ROOT / "raw" / "court_foia" / TS / "_step1_robots_recheck"
OUT.mkdir(parents=True, exist_ok=True)


def fetch(url: str) -> dict:
    started = datetime.now(timezone.utc)
    rec: dict = {"url": url, "fetched_at": started.isoformat()}
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    t0 = time.monotonic()
    body = b""
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:
            body = resp.read()
            rec["status"] = resp.status
            rec["final_url"] = resp.url
            rec["content_type"] = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        try:
            body = e.read() if hasattr(e, "read") else b""
        except Exception:
            body = b""
        rec["status"] = e.code
        rec["final_url"] = url
        rec["content_type"] = (e.headers.get("Content-Type", "")
                               if e.headers else "")
        rec["http_error"] = f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        rec["status"] = None
        rec["url_error"] = str(e.reason)
    rec["elapsed_s"] = round(time.monotonic() - t0, 3)
    rec["byte_count"] = len(body)
    rec["sha256"] = hashlib.sha256(body).hexdigest()
    host = url.split("//", 1)[1].split("/", 1)[0]
    host_dir = OUT / host
    host_dir.mkdir(exist_ok=True)
    (host_dir / "robots.txt").write_bytes(body)
    (host_dir / "_meta.json").write_text(json.dumps(rec, indent=2))
    return rec


def compare_to_step0(rec: dict, step0_manifest: dict) -> dict:
    """Compare to MAC-30 Step-0 robots-recheck for the same URL.

    Step-0 stored body in <host>.robots.txt — no sha256 in meta. Recompute
    sha256 from saved Step-0 body for delta comparison.
    """
    step0_dir = REPO_ROOT / "raw" / "court_foia" / "_step0_robots_recheck" / "20260505T023704Z"
    # Step-0 host -> filename mapping (from manifest hosts list):
    host = rec["url"].split("//", 1)[1].split("/", 1)[0]
    name_map = {
        "www.muckrock.com": "muckrock",
        "www.documentcloud.org": "muckrock_doc",  # legacy filename quirk
        "www.eff.org": "eff",
        "theintercept.com": "intercept",
        "www.propublica.org": "propublica",
        "www.justice.gov": "doj",
        "www.courtlistener.com": "courtlistener",
        "vault.fbi.gov": "fbi_vault",
        "www.aclu.org": "aclu",
    }
    fname = name_map.get(host)
    if not fname:
        return {"step0_match": False, "delta_changed": None}
    step0_body = step0_dir / f"{fname}.robots.txt"
    step0_meta = step0_dir / f"{fname}.meta.txt"
    if not step0_body.exists():
        return {"step0_match": False, "delta_changed": None}
    s0_sha = hashlib.sha256(step0_body.read_bytes()).hexdigest()
    s0_meta_text = step0_meta.read_text() if step0_meta.exists() else ""
    s0_status = None
    if s0_meta_text:
        for tok in s0_meta_text.split():
            if tok.startswith("HTTP="):
                try:
                    s0_status = int(tok.split("=", 1)[1])
                except Exception:
                    pass
    return {
        "step0_sha256": s0_sha,
        "step0_status": s0_status,
        "step0_byte_count": step0_body.stat().st_size,
        "delta_changed": (s0_sha != rec["sha256"]
                          or s0_status != rec.get("status")),
    }


def main() -> int:
    records = []
    for i, url in enumerate(HOSTS):
        if i > 0:
            time.sleep(SPACING_S)
        rec = fetch(url)
        rec["step0_delta"] = compare_to_step0(rec, {})
        print(
            f"{rec['url']}: status={rec.get('status')} bytes={rec['byte_count']} "
            f"sha256={rec['sha256'][:12]} "
            f"delta_vs_step0={rec['step0_delta'].get('delta_changed')}",
            flush=True,
        )
        records.append(rec)
    manifest = {
        "run_ts": TS,
        "issue": "MAC-31",
        "phase": "Phase 4 Wave-D Step 1 robots-recheck",
        "hosts": records,
        "user_agent": UA,
        "step0_recheck_run": "20260505T023704Z",
        "purpose": ("§11 #6 + SAR-4 mandatory robots.txt re-check before "
                    "any new fetch wave"),
        "newly_disallowed_paths_detected": [
            r for r in records if r.get("step0_delta", {}).get("delta_changed")
        ],
    }
    (OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest: {OUT / '_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
