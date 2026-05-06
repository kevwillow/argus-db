"""MAC-32 Phase 4 Wave-E Step 0 — per-host robots.txt re-check.

Per §11 #6 + SAR-4 + MAC-19/MAC-23/MAC-27/MAC-28/MAC-30/MAC-31 precedent: re-check
robots.txt for each candidate Wave-E (news / forums) host before any new fetch.

Hosts (from MAC-32 issue body §discovery surfaces):
  News:
    - krebsonsecurity.com           (Wordpress; investigative security blog)
    - arstechnica.com               (tech journalism; security/policy section)
    - www.theregister.com           (UK industry news; surveillance + procurement)
  Forum / API surfaces (open):
    - hn.algolia.com                (HN search API; CC-licensed)
    - news.ycombinator.com          (HN front-of-house host; story permalinks)
    - api.stackexchange.com         (StackExchange API host)
    - stackoverflow.com             (Q&A surface via tag pages)
    - serverfault.com               (Q&A; networking-tagged)
  Forum / OAuth-class surface (Reddit):
    - www.reddit.com                (auth-tier consideration)
    - oauth.reddit.com              (OAuth authenticated tier — not fetched at Step-0)
  Industry-specific forums (worker-proposed for inclusion):
    - mavicpilots.com               (DJI consumer drone community)
    - forum.dji.com                 (DJI vendor-hosted forum)
    - www.eham.net                  (ham radio community)
    - www.qrz.com                   (ham radio call-sign + community)
  Twitter/X: AUTH-GATED ENTIRELY — NOT FETCHED (§11 #2 absence-document).

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

UA = (
    "ArgusSourceWorker/0.1 (Phase4 Wave-E Step 0 robots recheck; "
    "+https://github.com/argus-project)"
)
TIMEOUT_S = 30
SPACING_S = 1.5

HOSTS = [
    # News surfaces
    "https://krebsonsecurity.com/robots.txt",
    "https://arstechnica.com/robots.txt",
    "https://www.theregister.com/robots.txt",
    # Forum / API surfaces (open)
    "https://hn.algolia.com/robots.txt",
    "https://news.ycombinator.com/robots.txt",
    "https://api.stackexchange.com/robots.txt",
    "https://stackoverflow.com/robots.txt",
    "https://serverfault.com/robots.txt",
    # Reddit (auth-tier consideration)
    "https://www.reddit.com/robots.txt",
    "https://oauth.reddit.com/robots.txt",
    # Industry-specific forums
    "https://mavicpilots.com/robots.txt",
    "https://forum.dji.com/robots.txt",
    "https://www.eham.net/robots.txt",
    "https://www.qrz.com/robots.txt",
]

REPO_ROOT = Path("/home/kev/argus")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = REPO_ROOT / "raw" / "news_forums" / "_step0_robots_recheck" / TS
OUT.mkdir(parents=True, exist_ok=True)


def fetch(url: str, ua: str = UA) -> dict:
    started = datetime.now(timezone.utc)
    rec: dict = {
        "url": url,
        "ua": ua,
        "fetched_at": started.isoformat(),
    }
    req = urllib.request.Request(url, headers={"User-Agent": ua})
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
    except Exception as e:
        body = b""
        rec["status"] = None
        rec["fatal_error"] = repr(e)
    rec["elapsed_s"] = round(time.monotonic() - t0, 3)
    rec["byte_count"] = len(body)
    rec["sha256"] = hashlib.sha256(body).hexdigest()
    host = url.split("//", 1)[1].split("/", 1)[0]
    fname = f"{host}.robots.txt"
    (OUT / fname).write_bytes(body)
    # Save meta
    meta_lines = [
        f"url: {rec['url']}",
        f"ua: {rec['ua']}",
        f"fetched_at: {rec['fetched_at']}",
        f"status: {rec.get('status')}",
        f"byte_count: {rec['byte_count']}",
        f"sha256: {rec['sha256']}",
        f"content_type: {rec.get('content_type','')}",
    ]
    if "http_error" in rec:
        meta_lines.append(f"http_error: {rec['http_error']}")
    if "url_error" in rec:
        meta_lines.append(f"url_error: {rec['url_error']}")
    if "fatal_error" in rec:
        meta_lines.append(f"fatal_error: {rec['fatal_error']}")
    (OUT / f"{host}.meta.txt").write_text("\n".join(meta_lines) + "\n")
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
        "purpose": "MAC-32 Wave-E Step-0 robots.txt re-check per §11 #6 + SAR-4",
        "user_agent": UA,
        "hosts": records,
        "twitter_x_disposition": (
            "AUTH-GATED ENTIRELY — robots.txt not fetched; per §11 #2 + issue body §8, "
            "Twitter/X access requires API key/login; absence-documented as "
            "out-of-scope without board approval-class authorization."
        ),
    }
    (OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest: {OUT / '_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
