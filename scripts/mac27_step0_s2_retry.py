"""MAC-27 Step-0 retry — Semantic Scholar at 10s spacing (free-tier safe).

Empirical retry to confirm whether sustained S2 free-tier access is feasible
without API key. Per `feedback_approval_request_deviation_justification.md`,
before proposing a key request we exhaust the unauth tier.

Also probes arxiv.org/list/cs.CR/recent for a robots-permissive alternative
discovery surface (arxiv.org allows /list with Crawl-delay 15s).
"""
from __future__ import annotations
import hashlib, json, ssl, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "ArgusSourceWorker/0.1 (Phase4 Wave-C Step 0 retry; +https://github.com/argus-project)"
TIMEOUT_S = 30
S2_SPACING_S = 10.0
ARXIV_SPACING_S = 15.0

REPO_ROOT = Path("/home/kev/argus")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = REPO_ROOT / "raw" / "academic" / "_step0_retry" / TS
OUT.mkdir(parents=True, exist_ok=True)


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:
            return resp.status, resp.read(), dict(resp.headers), resp.url, round(time.monotonic() - t0, 3)
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return e.code, body, dict(e.headers or {}), url, round(time.monotonic() - t0, 3)
    except urllib.error.URLError as e:
        return 0, b"", {"_url_error": str(e.reason)}, url, round(time.monotonic() - t0, 3)


def s2(q, limit=20):
    fields = "title,abstract,year,venue,openAccessPdf,externalIds,citationCount"
    qs = urllib.parse.urlencode({"query": q, "limit": str(limit), "fields": fields})
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{qs}"
    status, body, headers, _, elapsed = http_get(url)
    rec = {
        "query": q, "url": url, "status": status, "elapsed_s": elapsed,
        "byte_count": len(body), "sha256": hashlib.sha256(body).hexdigest(),
    }
    if status == 200:
        try:
            payload = json.loads(body.decode("utf-8"))
            rec["total"] = payload.get("total")
            rec["returned"] = len(payload.get("data", []))
            rec["sample"] = [
                {
                    "paperId": p.get("paperId"),
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "venue": p.get("venue"),
                    "arxivId": (p.get("externalIds") or {}).get("ArXiv"),
                    "doi": (p.get("externalIds") or {}).get("DOI"),
                    "openAccessPdf": (p.get("openAccessPdf") or {}).get("url"),
                    "citationCount": p.get("citationCount"),
                }
                for p in payload.get("data", [])[:5]
            ]
        except Exception as e:
            rec["parse_error"] = str(e)
    else:
        rec["body_excerpt"] = body[:300].decode("utf-8", errors="replace")
    return rec


queries = [
    "Flock Safety license plate reader",
    "DJI drone BLE",
    "ALPR fingerprint surveillance",
    "body-worn camera identifier privacy",
    "WiFi pineapple Hak5 attack",
    "IMSI catcher detection",
]

s2_results = []
for i, q in enumerate(queries):
    if i > 0:
        time.sleep(S2_SPACING_S)
    rec = s2(q, limit=20)
    print(f"S2 q={q!r} status={rec['status']} elapsed={rec['elapsed_s']}s "
          f"total={rec.get('total')} returned={rec.get('returned')}", flush=True)
    s2_results.append(rec)

# arXiv list probe — cs.CR/recent (permissive)
print("--- arXiv /list/cs.CR/recent probe ---", flush=True)
time.sleep(ARXIV_SPACING_S)
status, body, headers, _, elapsed = http_get("https://arxiv.org/list/cs.CR/recent")
arxiv_list = {
    "url": "https://arxiv.org/list/cs.CR/recent",
    "status": status, "elapsed_s": elapsed,
    "byte_count": len(body),
    "sha256": hashlib.sha256(body).hexdigest(),
}
if status == 200:
    text = body.decode("utf-8", errors="replace")
    arxiv_list["arxiv_id_link_count"] = text.count("/abs/")
    arxiv_list["pdf_link_count"] = text.count("/pdf/")
    (OUT / "arxiv_cs_cr_recent.html").write_bytes(body)
print(f"arxiv list: status={status} elapsed={elapsed}s arxiv_ids="
      f"{arxiv_list.get('arxiv_id_link_count')}", flush=True)

result = {
    "run_ts": TS,
    "s2_spacing_s": S2_SPACING_S,
    "s2_results": s2_results,
    "s2_success_rate": sum(1 for r in s2_results if r["status"] == 200) / len(s2_results),
    "arxiv_list_probe": arxiv_list,
}
(OUT / "_retry_manifest.json").write_text(json.dumps(result, indent=2))
print(f"\nDONE manifest={OUT / '_retry_manifest.json'}", flush=True)
print(f"S2 success rate: {result['s2_success_rate']:.0%} ({sum(1 for r in s2_results if r['status'] == 200)}/{len(s2_results)})")
