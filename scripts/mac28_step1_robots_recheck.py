"""MAC-28 Phase 4 Wave-C Step 1 — per-host robots.txt re-check (mandatory artifact).

Per §11 #6 + SAR-4 + MAC-27 issue spec: re-check robots.txt for each host
BEFORE any new fetch. Output mirrors MAC-27 `_step0_robots_recheck/` shape.

Hosts (Step-1 fetch surface, narrowed from Step-0 8-host set):
  - arxiv.org                  (PDF host + abstract pages)
  - api.semanticscholar.org    (graph API; opportunistic 12s spacing)
  - www.usenix.org             (USENIX Security open-access proceedings)
  - www.ndss-symposium.org     (NDSS open-access proceedings)

Excluded:
  - export.arxiv.org           (robots Disallow blanket — MAC-27 §1; NO fetch)
  - dl.acm.org                 (robots-hostile per MAC-27 §2.5; NO bulk fetch)
  - www.scs.stanford.edu       (Step-0 surface-class only; not in Step-1 fetch surface)
  - dspace.mit.edu             (Step-0 surface-class only; not in Step-1 fetch surface)

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

UA = "ArgusSourceWorker/0.1 (Phase4 Wave-C Step 1 robots recheck; +https://github.com/argus-project)"
TIMEOUT_S = 30
SPACING_S = 1.5

HOSTS = [
    "https://arxiv.org/robots.txt",
    "https://api.semanticscholar.org/robots.txt",
    "https://www.usenix.org/robots.txt",
    "https://www.ndss-symposium.org/robots.txt",
]

REPO_ROOT = Path("/home/kev/argus")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = REPO_ROOT / "raw" / "academic" / "_step1_robots_recheck" / TS
OUT.mkdir(parents=True, exist_ok=True)


def fetch(url: str) -> dict:
    started = datetime.now(timezone.utc)
    rec: dict = {"url": url, "fetched_at": started.isoformat()}
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:
            body = resp.read()
            rec["status"] = resp.status
            rec["final_url"] = resp.url
            rec["content_type"] = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        rec["status"] = e.code
        rec["final_url"] = url
        rec["content_type"] = e.headers.get("Content-Type", "") if e.headers else ""
        rec["http_error"] = f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        body = b""
        rec["status"] = None
        rec["url_error"] = str(e.reason)
    rec["elapsed_s"] = round(time.monotonic() - t0, 3)
    rec["byte_count"] = len(body)
    rec["sha256"] = hashlib.sha256(body).hexdigest()
    host = url.split("//", 1)[1].split("/", 1)[0]
    fname = f"{host}.robots.txt"
    (OUT / fname).write_bytes(body)
    return rec


def compare_to_step0(rec: dict, step0_manifest: dict) -> dict:
    """Return delta vs MAC-27 Step-0 robots-recheck for the same URL."""
    for s0 in step0_manifest.get("hosts", []):
        if s0.get("url") == rec["url"]:
            return {
                "step0_sha256": s0.get("sha256"),
                "step0_status": s0.get("status"),
                "step0_byte_count": s0.get("byte_count"),
                "delta_changed": s0.get("sha256") != rec["sha256"]
                                 or s0.get("status") != rec.get("status"),
            }
    return {"step0_match": False, "delta_changed": None}


def main() -> int:
    # Load Step-0 manifest for delta comparison
    step0_root = REPO_ROOT / "raw" / "academic" / "_step0_robots_recheck"
    step0_manifest = {}
    if step0_root.exists():
        runs = sorted([p for p in step0_root.iterdir() if p.is_dir()])
        if runs:
            mf = runs[-1] / "_manifest.json"
            if mf.exists():
                step0_manifest = json.loads(mf.read_text())

    records = []
    for i, url in enumerate(HOSTS):
        if i > 0:
            time.sleep(SPACING_S)
        rec = fetch(url)
        rec["step0_delta"] = compare_to_step0(rec, step0_manifest)
        print(
            f"{rec['url']}: status={rec.get('status')} bytes={rec['byte_count']} "
            f"sha256={rec['sha256'][:12]} "
            f"delta_vs_step0={rec['step0_delta'].get('delta_changed')}",
            flush=True,
        )
        records.append(rec)
    manifest = {
        "run_ts": TS,
        "issue": "MAC-28",
        "hosts": records,
        "user_agent": UA,
        "step0_recheck_run": step0_manifest.get("run_ts"),
        "purpose": "Phase 4 Wave-C Step 1 mandatory robots.txt re-check before any new fetch (§11 #6 + SAR-4)",
    }
    (OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest: {OUT / '_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
