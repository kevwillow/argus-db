"""MAC-27 Phase 4 Wave-C Step 0 — per-host robots.txt re-check.

Per §11 #6 + SAR-4 + MAC-19 precedent: re-check robots.txt for each host
before any new fetch. Output mirrors MAC-21 `_step0_robots_recheck/` shape.

Hosts (from MAC-27 issue):
  - arxiv.org                  (PDF host + abstract pages)
  - export.arxiv.org           (search API)
  - api.semanticscholar.org    (graph API)
  - www.usenix.org             (USENIX Security open-access proceedings)
  - www.ndss-symposium.org     (NDSS open-access proceedings)
  - dl.acm.org                 (ACM Digital Library; expect stricter policy)
  - www.scs.stanford.edu       (institutional repo precedent host; surface-class)
  - dspace.mit.edu             (institutional repo precedent host; surface-class)

NO writes to argus.db. NO LLM. Discovery + provenance only.
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

UA = "ArgusSourceWorker/0.1 (Phase4 Wave-C Step 0 robots recheck; +https://github.com/argus-project)"
TIMEOUT_S = 30
SPACING_S = 1.5

HOSTS = [
    "https://arxiv.org/robots.txt",
    "https://export.arxiv.org/robots.txt",
    "https://api.semanticscholar.org/robots.txt",
    "https://www.usenix.org/robots.txt",
    "https://www.ndss-symposium.org/robots.txt",
    "https://dl.acm.org/robots.txt",
    "https://www.scs.stanford.edu/robots.txt",
    "https://dspace.mit.edu/robots.txt",
]

REPO_ROOT = Path("/home/kev/argus")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = REPO_ROOT / "raw" / "academic" / "_step0_robots_recheck" / TS
OUT.mkdir(parents=True, exist_ok=True)


def fetch(url: str) -> dict:
    started = datetime.now(timezone.utc)
    rec: dict = {
        "url": url,
        "fetched_at": started.isoformat(),
    }
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


def main() -> int:
    records = []
    for i, url in enumerate(HOSTS):
        if i > 0:
            time.sleep(SPACING_S)
        rec = fetch(url)
        print(
            f"{rec['url']}: status={rec.get('status')} bytes={rec['byte_count']} "
            f"sha256={rec['sha256'][:12]}",
            flush=True,
        )
        records.append(rec)
    manifest = {
        "run_ts": TS,
        "hosts": records,
        "user_agent": UA,
    }
    (OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest: {OUT / '_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
