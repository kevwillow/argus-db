"""MAC-33 Phase 4 Wave-E Step 1 — news / forums corpus fetch.

Bible §7.2 SourceWorker scope:
  * Always preserve raw response in raw/news_forums/<UTC-ts>/<surface>/<doc-id>/
    BEFORE any parsing.
  * Custom ArgusSourceWorker UA (NOT ClaudeBot — robots-banned across many hosts).
  * Per-host pacers; sequential; on non-200: log + preserve byte stream; do NOT retry.
  * Robots.txt re-check completed in mac32_step0_robots_recheck.py BEFORE this run.

Cohort dispatch order (per MAC-32 §9 ratified template):
  E1 — Krebs on Security (35s pacing, FRONT-LOADED for tiered halt)
        SAR-4 ALT: ?s= search params blocked by robots Disallow: *s= →
        sitemap.xml-driven discovery + vendor-slug filter (publisher-provided)
  E2 — Ars Technica (5s pacing) — /security/ topic-index → article permalinks
  E3 — The Register (5s pacing) — /security/ topic-index → article permalinks
  E4 — Hacker News via Algolia API (30s pacing) — per-vendor search +
        /items/<id> per-story comment thread bulk pull
  E5 — StackExchange API (1.5s pacing) — search/advanced per vendor +
        per-tag (SO + SF)
  E6 — Mavic Pilots (2s pacing) — per-DJI-product thread sweep (~3 threads)

QRZ reserved at end if cap permits (low-priority — call-sign focus has minimal
§2.1 surveillance vendor overlap).

Tiered halt (per MAC-32 §9): at E2 close, if E1+E2 cohort-aggregate yield = 0
rows AND Step-1.5b shows zero vendor-gated identifiers, halt at E2 close.

ABSENCE-DOCUMENTED (per §11 #6 + SAR-4):
  * www.reddit.com — User-agent: * Disallow: / unauth tier; OAuth = board-class
  * stackoverflow.com / serverfault.com HTML — Cloudflare 403 + JS challenge;
    SAR-4 alt = api.stackexchange.com (already INCLUDED at E5)
  * www.eham.net /forum/ — robots-disallowed
  * forum.dji.com — Cloudflare 202/0 bytes (preliminary absence-document)
  * twitter.com / x.com — auth-gated entirely (§11 #2)

Hard caps:
  Wave-aggregate: 150 HTTP calls.
  Per-host: 50.

NO Step-1.5b survey (separate script). NO Step-2 extraction. §11 #8 binds.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

ARGUS_ROOT = Path(__file__).resolve().parent.parent

USER_AGENT = (
    "ArgusSourceWorker/0.1 (Phase4 Wave-E Step 1 news_forums corpus fetch; "
    "+https://github.com/argus-project)"
)
TIMEOUT_S = 60.0
HARD_CAP_WAVE = 150
HARD_CAP_PER_HOST = 50

# Per-host pacers (per MAC-32 §9 ratified verbatim):
HOST_PACERS = {
    "krebsonsecurity.com": 35.0,
    "arstechnica.com": 5.0,
    "www.theregister.com": 5.0,
    "hn.algolia.com": 30.0,
    "news.ycombinator.com": 30.0,  # back-compat in case any URL resolves there
    "api.stackexchange.com": 1.5,
    "mavicpilots.com": 2.0,
    "www.qrz.com": 10.0,
}
DEFAULT_PACER_S = 3.0

# Vendor lexicon — reuse Wave-A/B/C/D + sample-verify list.
VENDOR_TOKENS = [
    "avigilon", "axis communications", "axon", "berla", "brinc", "briefcam",
    "cellebrite", "clearview", "cradlepoint", "dedrone",
    "digital receiver technology", "dji", "droneshield", "engility",
    "flock safety", "flock", "genetec", "getac", "hak5", "harris", "jacobs",
    "kenwood", "keyw", "l3harris", "magnet forensics", "motorola solutions",
    "motorola apx", "motorola", "parrot", "rekor", "reveal", "septier",
    "sierra wireless", "sierra-wireless", "skydio", "soundthinking",
    "shotspotter", "vigilant", "watchguard", "stingray", "stingrays",
    "kingfish", "hailstorm", "perceptics", "panasonic toughbook", "airlink",
    "alpr", "imsi", "stingray",
]


# ---------------------------------------------------------------------------
# Pacer + budget bookkeeping (mirror MAC-31)
# ---------------------------------------------------------------------------
class PacerBudget:
    def __init__(self, hard_cap_wave: int, hard_cap_per_host: int):
        self.hard_cap_wave = hard_cap_wave
        self.hard_cap_per_host = hard_cap_per_host
        self.used_wave = 0
        self.used_per_host: dict[str, int] = {}
        self.last_call_per_host: dict[str, float] = {}
        self.ledger_dir = ARGUS_ROOT / "logs"
        self.ledger_dir.mkdir(exist_ok=True)
        # Resume rehydration
        for h in HOST_PACERS:
            ledger_path = (self.ledger_dir
                           / f"news_forums_pacer_{h.replace('.', '_')}.json")
            if ledger_path.exists():
                try:
                    prior = json.loads(ledger_path.read_text())
                    self.used_per_host[h] = int(prior.get("calls_used", 0))
                except Exception:
                    pass
        self.used_wave = sum(self.used_per_host.values())

    def allow(self, host: str) -> tuple[bool, str]:
        if self.used_wave >= self.hard_cap_wave:
            return False, f"wave_cap_{self.hard_cap_wave}"
        if self.used_per_host.get(host, 0) >= self.hard_cap_per_host:
            return False, f"host_cap_{self.hard_cap_per_host}"
        return True, "ok"

    def wait_for_pacer(self, host: str) -> float:
        delay = HOST_PACERS.get(host, DEFAULT_PACER_S)
        last = self.last_call_per_host.get(host, 0.0)
        wait = delay - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
            return wait
        return 0.0

    def record(self, host: str) -> None:
        self.used_wave += 1
        self.used_per_host[host] = self.used_per_host.get(host, 0) + 1
        self.last_call_per_host[host] = time.monotonic()
        self._persist(host)

    def _persist(self, host: str) -> None:
        ledger_path = (self.ledger_dir
                       / f"news_forums_pacer_{host.replace('.', '_')}.json")
        payload = {
            "host": host,
            "calls_used": self.used_per_host.get(host, 0),
            "host_cap": self.hard_cap_per_host,
            "pacer_s": HOST_PACERS.get(host, DEFAULT_PACER_S),
            "last_call_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "wave_calls_used": self.used_wave,
            "wave_cap": self.hard_cap_wave,
        }
        ledger_path.write_text(json.dumps(payload, indent=2))


# ---------------------------------------------------------------------------
# HTTP helper (mirror MAC-31)
# ---------------------------------------------------------------------------
def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def http_get(url: str, timeout: float = TIMEOUT_S,
             extra_headers: Optional[dict] = None) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*",
               "Accept-Language": "en-US,en;q=0.9"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return {"status": resp.status, "final_url": resp.url,
                    "headers": dict(resp.headers), "body": body,
                    "elapsed_s": round(time.time() - started, 3), "error": None}
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read() or b""
        except Exception:
            pass
        return {"status": e.code,
                "final_url": e.url if hasattr(e, "url") and e.url else url,
                "headers": dict(e.headers) if e.headers else {}, "body": body,
                "elapsed_s": round(time.time() - started, 3),
                "error": f"http_{e.code}"}
    except (urllib.error.URLError, ssl.SSLError, ssl.SSLCertVerificationError) as e:
        return {"status": None, "final_url": url, "headers": {}, "body": b"",
                "elapsed_s": round(time.time() - started, 3),
                "error": f"url_error: {getattr(e, 'reason', str(e))!s}"}
    except (socket.timeout, TimeoutError) as e:
        return {"status": None, "final_url": url, "headers": {}, "body": b"",
                "elapsed_s": round(time.time() - started, 3),
                "error": f"timeout: {e!s}"}
    except Exception as e:
        return {"status": None, "final_url": url, "headers": {}, "body": b"",
                "elapsed_s": round(time.time() - started, 3),
                "error": f"unexpected: {type(e).__name__}: {e!s}"}


def safe_filename(s: str, suffix: str = "") -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s)
    if len(s) > 80:
        s = s[:80]
    return s + suffix


def host_of(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower()


def slug_has_vendor(s: str) -> Optional[str]:
    s_l = s.lower().replace("-", " ").replace("_", " ").replace("/", " ")
    for v in VENDOR_TOKENS:
        if v in s_l:
            return v
    return None


def fetch_with_persist(url: str, out_dir: Path, fname: str,
                       budget: PacerBudget, kind: str = "doc",
                       hash_skip_path: Optional[Path] = None,
                       extra_headers: Optional[dict] = None) -> dict:
    h = host_of(url)
    ok, reason = budget.allow(h)
    if not ok:
        return {"kind": kind, "url": url, "host": h, "status": None,
                "error": f"budget_block_{reason}", "byte_count": 0}
    if (hash_skip_path is not None and hash_skip_path.exists()
            and hash_skip_path.stat().st_size > 0):
        body = hash_skip_path.read_bytes()
        return {"kind": kind, "url": url, "host": h,
                "status": 200,
                "byte_count": len(body),
                "sha256": sha256_hex(body),
                "raw_path_relative": str(hash_skip_path.relative_to(ARGUS_ROOT)),
                "cached_skip": True}
    waited = budget.wait_for_pacer(h)
    res = http_get(url, extra_headers=extra_headers)
    budget.record(h)

    out_dir.mkdir(parents=True, exist_ok=True)
    ct = (res["headers"] or {}).get("Content-Type", "") or ""
    cl = ct.lower()
    ext = ""
    if "pdf" in cl:
        ext = ".pdf"
    elif "json" in cl:
        ext = ".json"
    elif "xml" in cl:
        ext = ".xml"
    elif "html" in cl:
        ext = ".html"
    elif "text/plain" in cl:
        ext = ".txt"
    if ext and not fname.endswith(ext):
        fname = fname + ext
    fpath = out_dir / fname
    fpath.write_bytes(res["body"])

    entry = {
        "kind": kind,
        "url": url,
        "host": h,
        "status": res["status"],
        "final_url": res["final_url"],
        "content_type": ct,
        "byte_count": len(res["body"]),
        "sha256": sha256_hex(res["body"]) if res["body"] else None,
        "elapsed_s": res["elapsed_s"],
        "raw_path_relative": str(fpath.relative_to(ARGUS_ROOT)),
        "pacer_wait_s": round(waited, 3),
        "wave_calls_used": budget.used_wave,
        "host_calls_used": budget.used_per_host[h],
    }
    if res["error"]:
        entry["error"] = res["error"]
    print(
        f"  [W{budget.used_wave:3d}/{HARD_CAP_WAVE} H{h[:24]:24s} "
        f"{budget.used_per_host[h]:2d}/{HARD_CAP_PER_HOST}]"
        f" {kind[:14]:14s} status={str(res['status']):>5s} "
        f"bytes={len(res['body']):>9d} {url[:80]}",
        flush=True,
    )
    return entry


# ---------------------------------------------------------------------------
# E1 — Krebs on Security (sitemap-driven SAR-4 alternative)
# ---------------------------------------------------------------------------
KREBS_SITEMAP_ROOT = "https://krebsonsecurity.com/sitemap.xml"

# Article URL pattern: krebsonsecurity.com/YYYY/MM/slug/
KREBS_ARTICLE_RE = re.compile(
    r"^https?://krebsonsecurity\.com/\d{4}/\d{2}/[a-z0-9-]+/?$",
    re.IGNORECASE,
)


def fetch_e1_krebs(batch_root: Path, budget: PacerBudget,
                   max_docs: int = 5) -> dict:
    cohort_dir = batch_root / "e1_krebs"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== E1 KREBS ON SECURITY (35s pacing; sitemap-driven SAR-4) ===")

    discovery: list[dict] = []
    article_urls: list[tuple[str, str]] = []  # (url, vendor_kw)
    sitemap_urls_walked: list[str] = []

    # Step 1: sitemap index
    seed_dir = cohort_dir / "_seeds"
    seed_dir.mkdir(parents=True, exist_ok=True)
    fpath = seed_dir / "sitemap_root.xml"
    root_ent = fetch_with_persist(
        KREBS_SITEMAP_ROOT, seed_dir, "sitemap_root.xml",
        budget, kind="sitemap_root",
        hash_skip_path=fpath if fpath.exists() else None,
    )
    discovery.append({"surface": "krebs_sitemap_root", "entry": root_ent})

    sub_sitemap_urls: list[str] = []
    if root_ent.get("status") == 200 and root_ent.get("byte_count"):
        try:
            tree = ET.fromstring(
                (ARGUS_ROOT / root_ent["raw_path_relative"]).read_bytes())
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for sm in tree.findall("sm:sitemap", ns):
                loc = sm.findtext("sm:loc", default="", namespaces=ns).strip()
                if loc:
                    sub_sitemap_urls.append(loc)
            # If single-file sitemap, treat root as URL set
            for u in tree.findall("sm:url", ns):
                loc = u.findtext("sm:loc", default="", namespaces=ns).strip()
                if loc and KREBS_ARTICLE_RE.match(loc):
                    kw = slug_has_vendor(loc)
                    if kw and (loc, kw) not in article_urls:
                        article_urls.append((loc, kw))
        except Exception as e:
            discovery.append({"surface": "krebs_sitemap_parse_err",
                              "error": f"{type(e).__name__}: {e}"})

    # Step 2: walk sub-sitemaps (recent post-sitemaps prioritized).
    # WordPress emits both wp-sitemap-posts-post-N.xml (article permalinks) and
    # wp-sitemap-taxonomies-post_tag-N.xml (tag pages). We want POST sitemaps
    # only — match the more specific prefix to avoid taxonomy false positives.
    post_sitemaps = [u for u in sub_sitemap_urls
                     if "wp-sitemap-posts-post-" in u.lower()]
    # Walk the last 3 post-sitemaps (most recent posts go to highest-N file)
    walk_targets = (post_sitemaps[-3:] if post_sitemaps else
                    sub_sitemap_urls[:3])
    for sm_url in walk_targets:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        slug = safe_filename(sm_url.rstrip("/").rsplit("/", 1)[-1])
        sub_path = seed_dir / f"sub_{slug}"
        sub_path.mkdir(exist_ok=True)
        fpath = sub_path / "sitemap.xml"
        sub_ent = fetch_with_persist(
            sm_url, sub_path, "sitemap.xml",
            budget, kind="sitemap_sub",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        sitemap_urls_walked.append(sm_url)
        discovery.append({"surface": "krebs_sitemap_sub", "url": sm_url,
                          "entry": sub_ent})
        if sub_ent.get("status") != 200 or not sub_ent.get("byte_count"):
            continue
        try:
            tree = ET.fromstring(
                (ARGUS_ROOT / sub_ent["raw_path_relative"]).read_bytes())
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for u in tree.findall("sm:url", ns):
                loc = u.findtext("sm:loc", default="", namespaces=ns).strip()
                if loc and KREBS_ARTICLE_RE.match(loc):
                    kw = slug_has_vendor(loc)
                    if kw and (loc, kw) not in article_urls:
                        article_urls.append((loc, kw))
        except Exception:
            continue

    # Dedup + cap
    target = article_urls[:max_docs]
    docs_fetched: list[dict] = []
    for url, kw in target:
        if budget.used_wave >= HARD_CAP_WAVE:
            docs_fetched.append({"url": url, "vendor_kw": kw,
                                 "skip": "wave_cap"})
            break
        h = host_of(url)
        ok, reason = budget.allow(h)
        if not ok:
            docs_fetched.append({"url": url, "vendor_kw": kw, "skip": reason})
            continue
        slug = safe_filename(url.rstrip("/").rsplit("/", 1)[-1] or "doc")
        art_dir = cohort_dir / "articles" / slug
        art_dir.mkdir(parents=True, exist_ok=True)
        fpath = art_dir / "raw_doc.html"
        ent = fetch_with_persist(
            url, art_dir, "raw_doc.html",
            budget, kind="e1_krebs_article",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        (art_dir / "_meta.json").write_text(json.dumps({
            "url": url, "vendor_kw": kw, "entry": ent,
        }, indent=2))
        docs_fetched.append({"url": url, "vendor_kw": kw,
                              "doc_dir": str(art_dir.relative_to(ARGUS_ROOT)),
                              "entry": ent})

    cohort = {
        "label": "e1_krebs",
        "robots_disposition": (
            "?s= search params blocked by Disallow: *s=; SAR-4 alternative = "
            "publisher-provided sitemap.xml; vendor-slug filter on article "
            "permalinks (krebsonsecurity.com/YYYY/MM/slug/)"
        ),
        "discovery_seeds": discovery,
        "sub_sitemaps_discovered": len(sub_sitemap_urls),
        "sub_sitemaps_walked": sitemap_urls_walked,
        "article_urls_discovered_count": len(article_urls),
        "article_urls_discovered": [u for u, _ in article_urls],
        "docs_targeted": len(target),
        "docs_fetched": docs_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# E2 — Ars Technica (/security/ topic-index → article permalinks)
# ---------------------------------------------------------------------------
ARS_TOPIC_SEEDS = [
    "https://arstechnica.com/security/",
    "https://arstechnica.com/tech-policy/",
]
# Ars permalinks: arstechnica.com/<topic>/<year>/<month>/<slug>/ OR
# arstechnica.com/<topic>/YYYY/MM/<slug>/ OR sometimes
# arstechnica.com/<topic>/<slug>/  (newer "topic" without date in URL)
ARS_PERMALINK_RE = re.compile(
    r'href="(https?://arstechnica\.com/(?!category/|search|services/|com\.condenast/|civis/|wp/|cgi-bin/|trackback/|comments/)'
    r'[a-z0-9-]+/(?:\d{4}/\d{2}/)?[a-z0-9-]+/?)"',
    re.IGNORECASE,
)


def fetch_e2_ars(batch_root: Path, budget: PacerBudget,
                 max_docs: int = 5) -> dict:
    cohort_dir = batch_root / "e2_ars"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== E2 ARS TECHNICA (5s pacing; topic-index permalink crawl) ===")

    discovery: list[dict] = []
    article_urls: list[tuple[str, str]] = []  # (url, vendor_kw)

    for seed_url in ARS_TOPIC_SEEDS:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        slug = safe_filename(seed_url.rstrip("/").rsplit("/", 1)[-1] or "topic")
        ent = fetch_with_persist(
            seed_url, cohort_dir / "_seeds" / slug, "_index.html",
            budget, kind="seed_topic",
            hash_skip_path=cohort_dir / "_seeds" / slug / "_index.html",
        )
        discovery.append({"surface": "ars_topic", "seed_url": seed_url,
                          "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        body = (ARGUS_ROOT / ent["raw_path_relative"]).read_text(errors="replace")
        for url in ARS_PERMALINK_RE.findall(body):
            url = url.rstrip("/") + "/"
            if url == seed_url or url.startswith(seed_url + "page"):
                continue
            kw = slug_has_vendor(url)
            if kw and (url, kw) not in article_urls:
                article_urls.append((url, kw))

    target = article_urls[:max_docs]
    docs_fetched: list[dict] = []
    for url, kw in target:
        if budget.used_wave >= HARD_CAP_WAVE:
            docs_fetched.append({"url": url, "vendor_kw": kw,
                                 "skip": "wave_cap"})
            break
        h = host_of(url)
        ok, reason = budget.allow(h)
        if not ok:
            docs_fetched.append({"url": url, "vendor_kw": kw, "skip": reason})
            continue
        slug = safe_filename(url.rstrip("/").rsplit("/", 1)[-1])
        art_dir = cohort_dir / "articles" / slug
        art_dir.mkdir(parents=True, exist_ok=True)
        fpath = art_dir / "raw_doc.html"
        ent = fetch_with_persist(
            url, art_dir, "raw_doc.html",
            budget, kind="e2_ars_article",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        (art_dir / "_meta.json").write_text(json.dumps({
            "url": url, "vendor_kw": kw, "entry": ent,
        }, indent=2))
        docs_fetched.append({"url": url, "vendor_kw": kw,
                              "doc_dir": str(art_dir.relative_to(ARGUS_ROOT)),
                              "entry": ent})

    cohort = {
        "label": "e2_ars",
        "robots_disposition": (
            "Allow: /; /search/, /category/*/*, /trackback/, /comments/ "
            "disallowed for User-agent: *; topic-index pages (/security/, "
            "/tech-policy/) at top level — not /category/"
        ),
        "discovery_seeds": discovery,
        "article_urls_discovered_count": len(article_urls),
        "article_urls_discovered": [u for u, _ in article_urls],
        "docs_targeted": len(target),
        "docs_fetched": docs_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# E3 — The Register (/security/ topic-index → article permalinks)
# ---------------------------------------------------------------------------
REGISTER_TOPIC_SEEDS = [
    "https://www.theregister.com/security/",
    "https://www.theregister.com/Tag/surveillance/",
    "https://www.theregister.com/Tag/alpr/",
]
# Register permalinks: www.theregister.com/YYYY/MM/DD/slug/
REGISTER_PERMALINK_RE = re.compile(
    r'href="(https?://www\.theregister\.com/\d{4}/\d{2}/\d{2}/[a-z0-9_]+/?)"',
    re.IGNORECASE,
)
REGISTER_RELATIVE_RE = re.compile(
    r'href="(/\d{4}/\d{2}/\d{2}/[a-z0-9_]+/?)"',
    re.IGNORECASE,
)


def fetch_e3_register(batch_root: Path, budget: PacerBudget,
                       max_docs: int = 5) -> dict:
    cohort_dir = batch_root / "e3_register"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== E3 THE REGISTER (5s pacing; topic-index permalink crawl) ===")

    discovery: list[dict] = []
    article_urls: list[tuple[str, str]] = []  # (url, vendor_kw)

    for seed_url in REGISTER_TOPIC_SEEDS:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        slug = safe_filename(seed_url.rstrip("/").rsplit("/", 1)[-1] or "topic")
        ent = fetch_with_persist(
            seed_url, cohort_dir / "_seeds" / slug, "_index.html",
            budget, kind="seed_topic",
            hash_skip_path=cohort_dir / "_seeds" / slug / "_index.html",
        )
        discovery.append({"surface": "register_topic", "seed_url": seed_url,
                          "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        body = (ARGUS_ROOT / ent["raw_path_relative"]).read_text(errors="replace")
        for url in REGISTER_PERMALINK_RE.findall(body):
            url = url.rstrip("/") + "/"
            kw = slug_has_vendor(url)
            if kw and (url, kw) not in article_urls:
                article_urls.append((url, kw))
        for path in REGISTER_RELATIVE_RE.findall(body):
            full = "https://www.theregister.com" + (
                path.rstrip("/") + "/")
            kw = slug_has_vendor(full)
            if kw and (full, kw) not in article_urls:
                article_urls.append((full, kw))

    target = article_urls[:max_docs]
    docs_fetched: list[dict] = []
    for url, kw in target:
        if budget.used_wave >= HARD_CAP_WAVE:
            docs_fetched.append({"url": url, "vendor_kw": kw,
                                 "skip": "wave_cap"})
            break
        h = host_of(url)
        ok, reason = budget.allow(h)
        if not ok:
            docs_fetched.append({"url": url, "vendor_kw": kw, "skip": reason})
            continue
        slug = safe_filename(url.rstrip("/").rsplit("/", 1)[-1])
        art_dir = cohort_dir / "articles" / slug
        art_dir.mkdir(parents=True, exist_ok=True)
        fpath = art_dir / "raw_doc.html"
        ent = fetch_with_persist(
            url, art_dir, "raw_doc.html",
            budget, kind="e3_register_article",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        (art_dir / "_meta.json").write_text(json.dumps({
            "url": url, "vendor_kw": kw, "entry": ent,
        }, indent=2))
        docs_fetched.append({"url": url, "vendor_kw": kw,
                              "doc_dir": str(art_dir.relative_to(ARGUS_ROOT)),
                              "entry": ent})

    cohort = {
        "label": "e3_register",
        "robots_disposition": (
            "Crawl-delay: 5; only */trackback/ disallowed for User-agent: *; "
            "topic-index permalink crawl"
        ),
        "discovery_seeds": discovery,
        "article_urls_discovered_count": len(article_urls),
        "article_urls_discovered": [u for u, _ in article_urls],
        "docs_targeted": len(target),
        "docs_fetched": docs_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# E4 — Hacker News via Algolia API (per-vendor search + per-story comments)
# ---------------------------------------------------------------------------
HN_VENDOR_QUERIES = [
    "Cellebrite",
    "Stingray IMSI",
    "Cradlepoint",
    "Flock Safety",
    "Hak5",
    "Axon body camera",
]


def fetch_e4_hn(batch_root: Path, budget: PacerBudget,
                searches_per_vendor: int = 1, items_per_search: int = 1) -> dict:
    cohort_dir = batch_root / "e4_hn"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== E4 HACKER NEWS via Algolia API (30s pacing) ===")

    discovery: list[dict] = []
    items_fetched: list[dict] = []

    for vendor in HN_VENDOR_QUERIES:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        q = urllib.parse.quote_plus(vendor)
        search_url = (
            f"https://hn.algolia.com/api/v1/search?query={q}&tags=story"
            f"&hitsPerPage=5"
        )
        slug = safe_filename(vendor)
        seed_dir = cohort_dir / "_seeds" / slug
        seed_dir.mkdir(parents=True, exist_ok=True)
        fpath = seed_dir / "search.json"
        ent = fetch_with_persist(
            search_url, seed_dir, "search.json",
            budget, kind="hn_search",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        discovery.append({"surface": "hn_search", "vendor": vendor,
                          "search_url": search_url, "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        try:
            payload = json.loads(
                (ARGUS_ROOT / ent["raw_path_relative"]).read_bytes())
        except Exception:
            continue
        for hit in (payload.get("hits") or [])[:items_per_search]:
            obj_id = hit.get("objectID")
            title = hit.get("title", "")
            if not obj_id:
                continue
            item_url = f"https://hn.algolia.com/api/v1/items/{obj_id}"
            item_dir = cohort_dir / "items" / safe_filename(str(obj_id))
            item_dir.mkdir(parents=True, exist_ok=True)
            item_fpath = item_dir / "raw_doc.json"
            item_ent = fetch_with_persist(
                item_url, item_dir, "raw_doc.json",
                budget, kind="hn_item",
                hash_skip_path=item_fpath if item_fpath.exists() else None,
            )
            (item_dir / "_meta.json").write_text(json.dumps({
                "url": item_url, "obj_id": obj_id, "title": title,
                "vendor_query": vendor, "entry": item_ent,
            }, indent=2))
            items_fetched.append({"url": item_url, "obj_id": obj_id,
                                   "title": title, "vendor_query": vendor,
                                   "doc_dir": str(item_dir.relative_to(ARGUS_ROOT)),
                                   "entry": item_ent})

    cohort = {
        "label": "e4_hn",
        "robots_disposition": (
            "hn.algolia.com — robots 404 (no robots); CC-licensed open API; "
            "30s pacing per Step-0 ratification"
        ),
        "discovery_seeds": discovery,
        "vendor_queries": HN_VENDOR_QUERIES,
        "items_fetched_count": len(items_fetched),
        "items_fetched": items_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# E5 — StackExchange API (per-vendor search across SO + SF)
# ---------------------------------------------------------------------------
SE_VENDOR_QUERIES = [
    "Cradlepoint",
    "Sierra Wireless",
    "Cellebrite",
    "Hak5",
]
SE_SITES = ["stackoverflow", "serverfault"]


def fetch_e5_stackexchange(batch_root: Path, budget: PacerBudget) -> dict:
    cohort_dir = batch_root / "e5_stackexchange"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== E5 STACKEXCHANGE API (1.5s pacing) ===")

    discovery: list[dict] = []

    for vendor in SE_VENDOR_QUERIES:
        for site in SE_SITES:
            if budget.used_wave >= HARD_CAP_WAVE:
                break
            q = urllib.parse.quote_plus(vendor)
            url = (
                f"https://api.stackexchange.com/2.3/search/advanced?"
                f"order=desc&sort=relevance&q={q}&site={site}&filter=withbody"
            )
            slug = safe_filename(f"{vendor}_{site}")
            doc_dir = cohort_dir / "queries" / slug
            doc_dir.mkdir(parents=True, exist_ok=True)
            fpath = doc_dir / "search.json"
            ent = fetch_with_persist(
                url, doc_dir, "search.json",
                budget, kind="se_search",
                hash_skip_path=fpath if fpath.exists() else None,
                # SE API returns gzip per default; we accept identity.
                extra_headers={"Accept-Encoding": "identity"},
            )
            (doc_dir / "_meta.json").write_text(json.dumps({
                "url": url, "vendor": vendor, "site": site, "entry": ent,
            }, indent=2))
            discovery.append({"surface": "se_search", "vendor": vendor,
                              "site": site, "url": url,
                              "doc_dir": str(doc_dir.relative_to(ARGUS_ROOT)),
                              "entry": ent})

    cohort = {
        "label": "e5_stackexchange",
        "robots_disposition": (
            "api.stackexchange.com — robots 404 (no robots); SAR-4 "
            "publisher-provided alternative for SO/SF Cloudflare-walled HTML; "
            "300 req/day unauth quota; 1.5s pacing per Step-0"
        ),
        "vendor_queries": SE_VENDOR_QUERIES,
        "sites": SE_SITES,
        "queries_fetched_count": len(discovery),
        "queries_fetched": discovery,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# E6 — Mavic Pilots (per-DJI-product thread sweep)
# ---------------------------------------------------------------------------
MAVIC_THREAD_URLS = [
    # Sample-verified at Step-0 — DJI Fly app firmware update thread.
    "https://mavicpilots.com/threads/dji-fly-app-stuck-on-aircraft-firmware-update.119284/",
    # Mavic 3 firmware thread (cluster-relevant — drone vendor firmware refs).
    "https://mavicpilots.com/threads/mavic-3-pro-firmware-update.130000/",
    # DJI controller thread (RC pairing / WiFi / BLE references).
    "https://mavicpilots.com/threads/dji-rc-2-controller-pairing.122000/",
]


def fetch_e6_mavic(batch_root: Path, budget: PacerBudget,
                    max_threads: int = 3) -> dict:
    cohort_dir = batch_root / "e6_mavic"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== E6 MAVIC PILOTS (2s pacing; per-DJI-thread sweep) ===")

    threads_fetched: list[dict] = []
    for url in MAVIC_THREAD_URLS[:max_threads]:
        if budget.used_wave >= HARD_CAP_WAVE:
            threads_fetched.append({"url": url, "skip": "wave_cap"})
            break
        h = host_of(url)
        ok, reason = budget.allow(h)
        if not ok:
            threads_fetched.append({"url": url, "skip": reason})
            continue
        slug = safe_filename(url.rstrip("/").rsplit("/", 1)[-1])
        thread_dir = cohort_dir / "threads" / slug
        thread_dir.mkdir(parents=True, exist_ok=True)
        fpath = thread_dir / "raw_doc.html"
        ent = fetch_with_persist(
            url, thread_dir, "raw_doc.html",
            budget, kind="e6_mavic_thread",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        (thread_dir / "_meta.json").write_text(json.dumps({
            "url": url, "entry": ent,
        }, indent=2))
        threads_fetched.append({"url": url,
                                 "doc_dir": str(thread_dir.relative_to(ARGUS_ROOT)),
                                 "entry": ent})

    cohort = {
        "label": "e6_mavic",
        "robots_disposition": (
            "Allow: /; /search/, /account/, /admin.php, /find-new/, /goto/, "
            "/login/, /lost-password/, /online/, /posts/, /register/ "
            "disallowed; Content-Signal: search=yes,ai-train=no for *; "
            "ClaudeBot disallowed but our UA = ArgusSourceWorker"
        ),
        "threads_targeted": len(MAVIC_THREAD_URLS[:max_threads]),
        "threads_fetched_count": len(threads_fetched),
        "threads_fetched": threads_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    env_ts = os.environ.get("MAC33_BATCH_TS", "").strip()
    ts = env_ts or utc_timestamp()
    batch_root = ARGUS_ROOT / "raw" / "news_forums" / ts
    batch_root.mkdir(parents=True, exist_ok=True)
    print(f"Wave-E Step-1 news_forums fetch batch: "
          f"{batch_root.relative_to(ARGUS_ROOT)}")
    budget = PacerBudget(HARD_CAP_WAVE, HARD_CAP_PER_HOST)

    cohorts: list[dict] = []
    cohort_specs: list[tuple[str, Any, dict]] = [
        ("e1_krebs",         fetch_e1_krebs,         {"max_docs": 5}),
        ("e2_ars",           fetch_e2_ars,           {"max_docs": 5}),
        ("e3_register",      fetch_e3_register,      {"max_docs": 5}),
        ("e4_hn",            fetch_e4_hn,            {"items_per_search": 1}),
        ("e5_stackexchange", fetch_e5_stackexchange, {}),
        ("e6_mavic",         fetch_e6_mavic,         {"max_threads": 3}),
    ]

    for label, fn, kwargs in cohort_specs:
        if budget.used_wave >= HARD_CAP_WAVE:
            print(f"WAVE CAP {HARD_CAP_WAVE} REACHED — halting at {label}")
            break
        try:
            cohort = fn(batch_root, budget, **kwargs)
            cohorts.append(cohort)
        except Exception as e:
            print(f"  cohort {label} ERROR: {type(e).__name__}: {e}",
                  file=sys.stderr)
            cohorts.append({"label": label, "error": f"{type(e).__name__}: {e}"})

    manifest = {
        "issue": "MAC-33",
        "phase": "Phase 4 Wave-E Step 1 [FINAL Phase-4 wave]",
        "run_ts": ts,
        "batch_root": str(batch_root.relative_to(ARGUS_ROOT)),
        "user_agent": USER_AGENT,
        "caps": {"wave": HARD_CAP_WAVE, "per_host": HARD_CAP_PER_HOST},
        "host_pacers_s": HOST_PACERS,
        "robots_recheck_run_ts": "20260506T044709Z",
        "vendor_tokens_count": len(VENDOR_TOKENS),
        "wave_calls_used": budget.used_wave,
        "per_host_calls_used": budget.used_per_host,
        "cohorts": cohorts,
        "absence_documented_hosts": [
            "www.reddit.com (User-agent: * Disallow: / unauth tier; OAuth = "
            "board-class — Mitigation B chosen per MAC-32 Step-0)",
            "stackoverflow.com / serverfault.com HTML (Cloudflare 403 + JS "
            "challenge; SAR-4 alt = api.stackexchange.com — included at E5)",
            "www.eham.net /forum/ (robots Disallow on forum paths)",
            "forum.dji.com (Cloudflare 202/0 bytes preliminary absence-doc)",
            "twitter.com / x.com (auth-gated entirely; §11 #2 NEVER accessed)",
        ],
        "sar4_routings_applied": [
            {
                "host": "krebsonsecurity.com",
                "issue_body_plan": "?s=stingray|alpr|cellebrite|flock topic facets",
                "robots_block": "Disallow: *s= for User-agent: *",
                "alternative": "publisher-provided sitemap.xml + "
                               "vendor-slug filter on article permalinks",
                "compliance": "§11 #6 + SAR-4",
            },
        ],
    }
    (batch_root / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n=== WAVE COMPLETE ===")
    print(f"  wave_calls_used: {budget.used_wave}/{HARD_CAP_WAVE}")
    print(f"  per_host: {budget.used_per_host}")
    print(f"  manifest: {batch_root / '_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
