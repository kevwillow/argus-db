"""MAC-27 Phase 4 Wave-C Step 0 — academic corpus discovery probe.

Discovery + scope ratification only (per §7.1 + SAR-6 #1):
  - NO writes to db/argus.db
  - NO `raw_observations` rows
  - NO LLM calls (sample-verification is regex+keyword sweep at Step-1.5b shape)

Surfaces probed (post-robots-recheck):
  1. Semantic Scholar Graph API (api.semanticscholar.org) — robots-permissive
     (404 on /robots.txt = no published rules). Primary discovery surface for
     vendor × device-class × identifier-pattern crosses.
  2. arXiv abstract/PDF host (arxiv.org) — `/abs`, `/pdf` ALLOWED with
     Crawl-delay: 15s. Used for paper PDF fetch ONLY; discovery via
     Semantic Scholar (which indexes arXiv preprints) — export.arxiv.org
     `Disallow: /` rules out direct API use per §11 #6 + SAR-4.
  3. USENIX Security open-access HTML proceedings (www.usenix.org) — disallows
     `/publications/proceedings` (proceedings landing) but per-paper pages at
     `/conference/{conf}/presentation/{slug}` and PDFs at `/system/files/...`
     not in disallow list. Catalog scan = static URL enumeration.
  4. NDSS Symposium open-access PDFs (www.ndss-symposium.org) — robots-permissive.
  5. DSpace MIT institutional repo (dspace.mit.edu) — `/handle/...` allowed.

Vendor × device-class probe matrix:
  - Vendors (full 34 manufacturers anchor universe; subsetted to 6 for Step-0
    coverage projection — A-tier: Flock Safety / Motorola Solutions / DJI /
    Hak5 / Cradlepoint / Axon — exact mapping to §2.1 priorities)
  - Device-class keywords (§2.1): "ALPR", "license plate reader",
    "body-worn camera", "IMSI catcher", "cell-site simulator", "police drone",
    "in-vehicle router", "WiFi pineapple"
  - Identifier-pattern keywords ("BSSID", "BLE service UUID", "MAC address",
    "SSID pattern") — present in queries to bias toward methods/measurement
    papers vs purely qualitative

NO writes outside raw/academic/<run-ts>/_step0/. Paginates Semantic Scholar
hits at ≤100/query (free-tier safe). Per §11 #6 + SAR-4: respects each host's
crawl-delay (Semantic Scholar = 1.0s between calls; arxiv.org = 15s when
fetching; USENIX = 10s).

Output:
  raw/academic/<run-ts>/_step0/semantic_scholar_probe.json
  raw/academic/<run-ts>/_step0/usenix_proceedings_probe.json
  raw/academic/<run-ts>/_step0/ndss_proceedings_probe.json
  raw/academic/<run-ts>/_step0/_manifest.json
  logs/mac27_step0_discovery_<run-ts>.log
"""
from __future__ import annotations

import hashlib
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "ArgusSourceWorker/0.1 (Phase4 Wave-C Step 0 discovery; +https://github.com/argus-project)"
TIMEOUT_S = 30
S2_SPACING_S = 1.2  # free tier ~1 RPS; conservative
ARXIV_SPACING_S = 15.0  # robots Crawl-delay
USENIX_SPACING_S = 10.0  # robots Crawl-delay

REPO_ROOT = Path("/home/kev/argus")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = REPO_ROOT / "raw" / "academic" / TS / "_step0"
OUT.mkdir(parents=True, exist_ok=True)
LOG = REPO_ROOT / "logs" / f"mac27_step0_discovery_{TS}.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

# A-tier vendors (Step-0 coverage projection subset, NOT a Wave-C scope cap;
# Wave-C Step-1 dispatch will use full 34-vendor anchor universe consistent
# with MAC-21/23 patterns). Picked for §2.1 priority density: ALPR (Flock,
# Motorola), drone (DJI), hacking (Hak5), in-vehicle router (Cradlepoint),
# body-cam (Axon).
VENDORS_A_TIER = [
    "Flock Safety",
    "Motorola Solutions",
    "DJI",
    "Hak5",
    "Cradlepoint",
    "Axon",
]

# Device-class keywords (anchored to §2.1)
DEVICE_KEYWORDS = [
    "license plate reader",
    "body-worn camera",
    "IMSI catcher",
    "cell-site simulator",
    "police drone",
    "WiFi pineapple",
]

# Identifier-bias keywords — bias S2 retrieval toward methods/measurement papers
ID_BIAS_KEYWORDS = ["BSSID", "BLE service UUID", "MAC address", "SSID"]

logfh = open(LOG, "a", encoding="utf-8")


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
    print(line, flush=True)
    logfh.write(line + "\n")
    logfh.flush()


def http_get(url: str, headers: dict | None = None) -> tuple[int, bytes, dict, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    ctx = ssl.create_default_context()
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:
            body = resp.read()
            return resp.status, body, dict(resp.headers), resp.url
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return e.code, body, dict(e.headers or {}), url
    except urllib.error.URLError as e:
        return 0, b"", {"_url_error": str(e.reason)}, url
    finally:
        log(f"HTTP {url} elapsed={round(time.monotonic() - t0, 3)}s")


def s2_search(query: str, limit: int = 10) -> dict:
    """Semantic Scholar Graph API: relevance-search papers.

    Uses the public free-tier endpoint (no API key); fields tightened to what
    Step-0 actually needs (titles, abstracts, year, venue, openAccessPdf,
    arXiv externalIds for cross-reference fetch).
    """
    fields = "title,abstract,year,venue,openAccessPdf,externalIds,authors.name,citationCount"
    qs = urllib.parse.urlencode({
        "query": query,
        "limit": str(limit),
        "fields": fields,
    })
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?{qs}"
    status, body, headers, _ = http_get(url)
    rec = {
        "query": query,
        "url": url,
        "status": status,
        "byte_count": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "rate_limit_remaining": headers.get("x-ratelimit-remaining"),
        "rate_limit_used": headers.get("x-ratelimit-used"),
    }
    if status == 200:
        try:
            payload = json.loads(body.decode("utf-8"))
            rec["total"] = payload.get("total")
            rec["returned"] = len(payload.get("data", []))
            # Truncate per-record to discovery-relevant slice (no full abstract
            # in manifest; full body persisted to file).
            rec["sample"] = [
                {
                    "paperId": p.get("paperId"),
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "venue": p.get("venue"),
                    "citationCount": p.get("citationCount"),
                    "arxivId": (p.get("externalIds") or {}).get("ArXiv"),
                    "doi": (p.get("externalIds") or {}).get("DOI"),
                    "openAccessPdf": (p.get("openAccessPdf") or {}).get("url"),
                }
                for p in payload.get("data", [])[:5]
            ]
            rec["payload"] = payload
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            rec["parse_error"] = str(e)
    else:
        rec["body_excerpt"] = body[:200].decode("utf-8", errors="replace")
    return rec


def main() -> int:
    manifest: dict = {
        "run_ts": TS,
        "user_agent": UA,
        "robots_recheck_run": "20260506T012607Z",
        "surfaces": {},
    }

    # ----- Surface 1: Semantic Scholar (primary discovery) -----
    log("=== Semantic Scholar Graph API probe ===")
    s2_results = []
    queries = []
    # Vendor × device-class crosses (12 = 6 vendors × 2 device-class top hits)
    for vendor in VENDORS_A_TIER:
        for device in DEVICE_KEYWORDS[:2]:  # top-2 device-class per vendor
            queries.append(f"{vendor} {device}")
    # Vendor × identifier-bias crosses (6 = 6 vendors × 1 ID kw — most discriminating)
    for vendor in VENDORS_A_TIER:
        queries.append(f"{vendor} BSSID OR \"BLE UUID\" OR \"MAC address\"")

    for i, q in enumerate(queries):
        if i > 0:
            time.sleep(S2_SPACING_S)
        rec = s2_search(q, limit=20)
        log(
            f"S2 q={q!r} status={rec['status']} total={rec.get('total')} "
            f"returned={rec.get('returned')} ratelimit_remaining={rec.get('rate_limit_remaining')}"
        )
        s2_results.append(rec)

    s2_path = OUT / "semantic_scholar_probe.json"
    s2_path.write_text(json.dumps({
        "run_ts": TS,
        "queries": queries,
        "results": s2_results,
    }, indent=2))
    manifest["surfaces"]["semantic_scholar"] = {
        "queries": len(queries),
        "successes": sum(1 for r in s2_results if r["status"] == 200),
        "totals_sum": sum((r.get("total") or 0) for r in s2_results if r["status"] == 200),
        "file": str(s2_path.relative_to(REPO_ROOT)),
    }

    # ----- Surface 2: arXiv abs-page metadata probe (single fetch via /abs) -----
    # This is a smoke probe to confirm /abs is fetchable under crawl-delay; we
    # do NOT use export.arxiv.org. Pick top-1 arxiv-cross-reffed paper from S2
    # results if any.
    log("=== arXiv /abs smoke probe ===")
    arxiv_probe: dict = {"performed": False, "reason": ""}
    arxiv_id = None
    for rec in s2_results:
        for sample in rec.get("sample", []):
            if sample.get("arxivId"):
                arxiv_id = sample["arxivId"]
                arxiv_probe["seed_query"] = rec["query"]
                arxiv_probe["seed_paperId"] = sample["paperId"]
                arxiv_probe["seed_title"] = sample["title"]
                break
        if arxiv_id:
            break
    if arxiv_id:
        time.sleep(ARXIV_SPACING_S)
        url = f"https://arxiv.org/abs/{arxiv_id}"
        status, body, _headers, _final = http_get(url)
        arxiv_probe.update({
            "performed": True,
            "url": url,
            "status": status,
            "byte_count": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        })
    else:
        arxiv_probe["reason"] = "no S2 hit included an ArXiv externalId"
    (OUT / "arxiv_probe.json").write_text(json.dumps(arxiv_probe, indent=2))
    manifest["surfaces"]["arxiv_abs_probe"] = arxiv_probe

    # ----- Surface 3: USENIX proceedings catalog scan (single conference page) -----
    # USENIX Security 2024 catalog page; proceedings landing per /publications/
    # proceedings is Disallowed but conference-specific page at /conference/...
    # is NOT in disallow list.
    log("=== USENIX Security 2024 catalog probe ===")
    usenix_url = "https://www.usenix.org/conference/usenixsecurity24/technical-sessions"
    time.sleep(USENIX_SPACING_S)
    status, body, _h, _u = http_get(usenix_url)
    usenix_probe = {
        "url": usenix_url,
        "status": status,
        "byte_count": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    if status == 200:
        text = body.decode("utf-8", errors="replace")
        usenix_probe["paper_link_count"] = text.count("/conference/usenixsecurity24/presentation/")
        usenix_probe["pdf_link_count"] = text.lower().count(".pdf")
        # Co-occurrence count for vendor names — quick density signal
        usenix_probe["vendor_mentions"] = {
            v: text.lower().count(v.lower()) for v in VENDORS_A_TIER
        }
    (OUT / "usenix_proceedings_probe.json").write_text(json.dumps(usenix_probe, indent=2))
    (OUT / "usenix_sec24_proceedings.html").write_bytes(body)
    manifest["surfaces"]["usenix_sec24"] = {
        "status": status,
        "byte_count": len(body),
        "paper_link_count": usenix_probe.get("paper_link_count"),
        "vendor_mentions": usenix_probe.get("vendor_mentions"),
    }

    # ----- Surface 4: NDSS proceedings catalog scan -----
    log("=== NDSS Symposium 2024 catalog probe ===")
    time.sleep(2.0)  # NDSS is permissive; 2s is courtesy
    ndss_url = "https://www.ndss-symposium.org/ndss2024/accepted-papers/"
    status, body, _h, _u = http_get(ndss_url)
    ndss_probe = {
        "url": ndss_url,
        "status": status,
        "byte_count": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    if status == 200:
        text = body.decode("utf-8", errors="replace")
        ndss_probe["pdf_link_count"] = text.lower().count(".pdf")
        ndss_probe["paper_link_count"] = text.count("ndss2024-paper")
        ndss_probe["vendor_mentions"] = {
            v: text.lower().count(v.lower()) for v in VENDORS_A_TIER
        }
    (OUT / "ndss_proceedings_probe.json").write_text(json.dumps(ndss_probe, indent=2))
    (OUT / "ndss2024_accepted.html").write_bytes(body)
    manifest["surfaces"]["ndss2024"] = {
        "status": status,
        "byte_count": len(body),
        "paper_link_count": ndss_probe.get("paper_link_count"),
        "vendor_mentions": ndss_probe.get("vendor_mentions"),
    }

    (OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    log(f"DONE manifest={OUT / '_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
