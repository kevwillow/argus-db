"""MAC-31 Phase 4 Wave-D Step 1 — court_foia corpus fetch (Mitigation-B form).

Bible §7.2 SourceWorker scope:
  * Always preserve raw response in raw/court_foia/<UTC-ts>/<surface>/<doc-id>/
    BEFORE any parsing.
  * Custom ArgusSourceWorker UA (NOT ClaudeBot).
  * Per-host pacers; sequential; on non-200: log + preserve byte stream; do NOT retry.
  * Robots.txt re-check completed in mac31_step1_robots_recheck.py BEFORE this run.

Cohort dispatch order (per MAC-31 / MAC-30 §9 #5, Mitigation-B form):
  D2 — MuckRock + DocumentCloud (~15 docs, 5s pacing — robots-conservative)
  D3 — EFF /deeplinks/ + /files/ (~3 docs, 30s pacing — robots-pinned)
  D4 — The Intercept Drone Papers + investigations (~3 docs, 2s pacing)
  D5 — ProPublica via sitemap.xml (~2 docs, 2s pacing — NO URL guessing)
  D6 — DOJ OIP / OIG reports (~2 docs, 1s pacing)

CourtListener (D1) DROPPED under Mitigation-B per MAC-30 ratification — see
docs/absence/court_foia/_absence_courtlistener.md. FBI Vault, ACLU FOIA paths,
PACER, sealed records all absence-documented per §11 #2 + #6 + SAR-4.

Hard caps:
  Wave-aggregate: 200 HTTP calls.
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
    "ArgusSourceWorker/0.1 (Phase4 Wave-D Step 1 court_foia corpus fetch; "
    "+https://github.com/argus-project)"
)
TIMEOUT_S = 60.0
HARD_CAP_WAVE = 200
HARD_CAP_PER_HOST = 50

# Per-host pacers (per MAC-31 issue + robots-recheck binding):
#   muckrock + documentcloud: 5s (robots-pinned step-0 binding; current robots
#     softened but conservative pacer maintains compliance)
#   eff: 30s (robots-pinned)
#   intercept: 2s (no crawl-delay)
#   propublica: 2s (no crawl-delay)
#   justice.gov: 1s (no crawl-delay)
#   ancillary embed hosts: 2s default
HOST_PACERS = {
    "www.muckrock.com": 5.0,
    "www.documentcloud.org": 5.0,
    "s3.documentcloud.org": 5.0,
    "embed.documentcloud.org": 5.0,
    "assets.documentcloud.org": 5.0,
    "d3i6fh83elv35t.cloudfront.net": 5.0,  # MuckRock CDN
    "www.eff.org": 30.0,
    "theintercept.com": 2.0,
    "www.propublica.org": 2.0,
    "www.justice.gov": 1.0,
    "media.defense.gov": 2.0,
    "www.defense.gov": 2.0,
    "www.dtic.mil": 2.0,
    "apps.dtic.mil": 2.0,
}
DEFAULT_PACER_S = 3.0

# SOI filter — mirror MAC-28 SOI keywords; tightened for FOIA/court contexts
SOI_KEYWORDS = [
    # Cellular surveillance / IMSI-catchers
    "imsi catcher", "imsi-catcher", "stingray", "stingrays",
    "cell-site simulator", "cell site simulator", "cell tracking",
    "rogue base station", "fake base station", "kingfish",
    "harris corp", "harris corporation",
    # ALPR / LPR
    "license plate reader", "license-plate", "alpr", "lpr", "vigilant",
    "flock safety", "flock cameras", "rekor", "perceptics",
    # Body cam / patrol vehicle
    "body-worn camera", "body worn camera", "body camera", "bodycam",
    "axon", "watchguard", "reveal", "getac", "panasonic toughbook",
    # Police radio / LMR
    "p25 radio", "land mobile radio", "motorola apx", "motorola solutions",
    "tetra ", "encryption key", "harris xl",
    # In-vehicle networking
    "cradlepoint", "sierra wireless", "airlink",
    # WiFi / BLE / fingerprinting
    "wifi fingerprint", "wi-fi fingerprint", "ssid fingerprint",
    "ble fingerprint", "bluetooth fingerprint", "device fingerprint",
    "mac address", "probe request", "wifi tracking", "wireless tracking",
    "ssid tracking",
    # Drones / UAVs
    "drone", "uav", "unmanned aerial", "remote id", "remoteid", "dji",
    "skydio", "parrot", "brinc",
    # Surveillance / facial-recognition / mass surveillance
    "facial recognition", "mass surveillance", "fixed surveillance",
    "video surveillance", "surveillance camera", "spy camera",
    "geofence warrant", "geofence", "gps tracker", "gps tracking",
    # FOIA / court keywords
    "foia", "freedom of information",
    # Hak5
    "wifi pineapple", "rubber ducky",
    # Cellebrite / forensic
    "cellebrite", "forensic extraction", "magnet forensics",
    # Soundsthinking / shotspotter
    "shotspotter", "soundthinking", "gunshot detection",
    # Clearview / facial DB
    "clearview",
]


# ---------------------------------------------------------------------------
# Pacer + budget bookkeeping (mirror MAC-28)
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
            ledger_path = self.ledger_dir / f"court_foia_pacer_{h.replace('.', '_')}.json"
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
        ledger_path = self.ledger_dir / f"court_foia_pacer_{host.replace('.', '_')}.json"
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
# HTTP helper (mirror MAC-28)
# ---------------------------------------------------------------------------
def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def http_get(url: str, timeout: float = TIMEOUT_S) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*",
                 "Accept-Language": "en-US,en;q=0.9"},
    )
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


def fetch_with_persist(url: str, out_dir: Path, fname: str,
                       budget: PacerBudget, kind: str = "doc",
                       hash_skip_path: Optional[Path] = None) -> dict:
    h = host_of(url)
    ok, reason = budget.allow(h)
    if not ok:
        return {"kind": kind, "url": url, "host": h, "status": None,
                "error": f"budget_block_{reason}", "byte_count": 0}
    if hash_skip_path is not None and hash_skip_path.exists() \
       and hash_skip_path.stat().st_size > 0:
        body = hash_skip_path.read_bytes()
        return {"kind": kind, "url": url, "host": h,
                "status": 200,
                "byte_count": len(body),
                "sha256": sha256_hex(body),
                "raw_path_relative": str(hash_skip_path.relative_to(ARGUS_ROOT)),
                "cached_skip": True}
    waited = budget.wait_for_pacer(h)
    res = http_get(url)
    budget.record(h)

    out_dir.mkdir(parents=True, exist_ok=True)
    ct = (res["headers"] or {}).get("Content-Type", "") or ""
    cl = ct.lower()
    ext = ""
    if "pdf" in cl:
        ext = ".pdf"
    elif "html" in cl or "xml" in cl:
        ext = ".html"
    elif "json" in cl:
        ext = ".json"
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
        f"  [W{budget.used_wave:3d}/{HARD_CAP_WAVE} H{h[:24]:24s} {budget.used_per_host[h]:2d}/{HARD_CAP_PER_HOST}]"
        f" {kind[:14]:14s} status={str(res['status']):>5s} bytes={len(res['body']):>9d} {url[:80]}",
        flush=True,
    )
    return entry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_SOI_PATTERNS: list[tuple[str, "re.Pattern[str]"]] = []


def _build_soi_patterns() -> None:
    if _SOI_PATTERNS:
        return
    for kw in SOI_KEYWORDS:
        kw_core = kw.strip().rstrip()
        pat = r"\b" + re.escape(kw_core)
        _SOI_PATTERNS.append((kw, re.compile(pat, re.IGNORECASE)))


def text_matches_soi(text: str) -> Optional[str]:
    _build_soi_patterns()
    for kw, pat in _SOI_PATTERNS:
        if pat.search(text):
            return kw
    return None


# ---------------------------------------------------------------------------
# D2 — MuckRock + DocumentCloud
# ---------------------------------------------------------------------------
# Topic-index seed URLs — MuckRock projects + DocumentCloud API queries
MUCKROCK_PROJECT_SEEDS = [
    "https://www.muckrock.com/project/the-stingray-cell-tracking-investigation-227/",
    "https://www.muckrock.com/project/parallel-construction-investigation-71/",
    "https://www.muckrock.com/project/the-spying-on-students-project-30/",
]
MUCKROCK_NEWS_TAG_SEEDS = [
    "https://www.muckrock.com/news/?q=stingray",
    "https://www.muckrock.com/news/?q=alpr",
    "https://www.muckrock.com/news/?q=flock",
]
# DocumentCloud public REST API — allows JSON queries by keyword without login
DOCUMENTCLOUD_API_QUERIES = [
    "https://api.documentcloud.org/api/documents/?q=stingray&per_page=10",
    "https://api.documentcloud.org/api/documents/?q=alpr&per_page=10",
    "https://api.documentcloud.org/api/documents/?q=imsi+catcher&per_page=10",
]

# MuckRock article / FOIA-request links (relative or absolute)
MUCKROCK_LINK_RE = re.compile(
    r'href="(/(?:foi|news)/[^"#?]+/)"',
    re.IGNORECASE,
)
# DocumentCloud-hosted PDF embed URLs in MuckRock pages
DC_PDF_RE = re.compile(
    r'https?://(?:assets|s3|www|embed)\.documentcloud\.org/[^"\s\'<>]+',
    re.IGNORECASE,
)


def fetch_d2_muckrock_documentcloud(batch_root: Path, budget: PacerBudget,
                                     max_docs: int = 15) -> dict:
    cohort_dir = batch_root / "d2_muckrock_documentcloud"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== D2 MUCKROCK + DOCUMENTCLOUD ===")

    discovery: list[dict] = []
    discovered_doc_urls: list[tuple[str, str, str]] = []  # (url, title, src_kind)

    # Phase D2-A: MuckRock project pages — discover MuckRock /foi/ + /news/ links
    for seed_url in MUCKROCK_PROJECT_SEEDS:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        slug = safe_filename(seed_url.rstrip("/").rsplit("/", 1)[-1])
        ent = fetch_with_persist(
            seed_url, cohort_dir / "_seeds" / slug, "_index.html",
            budget, kind="seed_index",
            hash_skip_path=cohort_dir / "_seeds" / slug / "_index.html",
        )
        discovery.append({"surface": "muckrock_project", "seed_url": seed_url,
                          "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        body = (ARGUS_ROOT / ent["raw_path_relative"]).read_text(errors="replace")
        # Extract /foi/ and /news/ links
        seen = set()
        for path in MUCKROCK_LINK_RE.findall(body):
            if path in seen or "/login" in path or "/account" in path \
                    or path.endswith("/category/"):
                continue
            seen.add(path)
            full = "https://www.muckrock.com" + path
            # Title: pull from anchor text near the href
            title_kw = ""
            anchor_re = re.compile(
                r'href="' + re.escape(path) + r'"[^>]*>([^<]{3,200})<',
                re.IGNORECASE,
            )
            am = anchor_re.search(body)
            title = am.group(1).strip() if am else path
            if text_matches_soi(title) or text_matches_soi(path):
                title_kw = text_matches_soi(title) or text_matches_soi(path) or ""
                discovered_doc_urls.append((full, title, "muckrock_seed"))

    # Phase D2-B: MuckRock news search — pull article links from result pages
    for seed_url in MUCKROCK_NEWS_TAG_SEEDS:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        slug = safe_filename(urllib.parse.urlparse(seed_url).query)
        ent = fetch_with_persist(
            seed_url, cohort_dir / "_seeds" / f"news_{slug}", "_index.html",
            budget, kind="seed_search",
            hash_skip_path=cohort_dir / "_seeds" / f"news_{slug}" / "_index.html",
        )
        discovery.append({"surface": "muckrock_news_search", "seed_url": seed_url,
                          "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        body = (ARGUS_ROOT / ent["raw_path_relative"]).read_text(errors="replace")
        seen = set()
        for path in MUCKROCK_LINK_RE.findall(body):
            if path in seen or "/login" in path or "/account" in path:
                continue
            seen.add(path)
            full = "https://www.muckrock.com" + path
            anchor_re = re.compile(
                r'href="' + re.escape(path) + r'"[^>]*>([^<]{3,200})<',
                re.IGNORECASE,
            )
            am = anchor_re.search(body)
            title = am.group(1).strip() if am else path
            if text_matches_soi(title) or text_matches_soi(path):
                discovered_doc_urls.append((full, title, "muckrock_news"))

    # Phase D2-C: DocumentCloud REST API queries — JSON, no login needed
    for api_url in DOCUMENTCLOUD_API_QUERIES:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        slug = safe_filename(urllib.parse.urlparse(api_url).query)
        ent = fetch_with_persist(
            api_url, cohort_dir / "_seeds" / f"dc_api_{slug}", "_query.json",
            budget, kind="seed_dc_api",
            hash_skip_path=cohort_dir / "_seeds" / f"dc_api_{slug}" / "_query.json",
        )
        discovery.append({"surface": "documentcloud_api", "seed_url": api_url,
                          "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        try:
            payload = json.loads(
                (ARGUS_ROOT / ent["raw_path_relative"]).read_text(errors="replace"))
        except Exception:
            continue
        for r in (payload.get("results") or [])[:5]:
            asset_url = r.get("asset_url") or ""
            slug_doc = r.get("slug") or ""
            doc_id = r.get("id") or ""
            title = r.get("title") or slug_doc
            # PDF URL: DocumentCloud canonical pattern
            if asset_url and slug_doc and doc_id:
                pdf_url = f"{asset_url.rstrip('/')}/documents/{doc_id}/{slug_doc}.pdf"
            else:
                pdf_url = (
                    f"https://s3.documentcloud.org/documents/{doc_id}/{slug_doc}.pdf"
                    if doc_id and slug_doc else None)
            if pdf_url and (text_matches_soi(title) or
                            text_matches_soi(slug_doc)):
                discovered_doc_urls.append((pdf_url, title, "documentcloud"))

    # Dedup + cap
    seen_urls = set()
    deduped: list[tuple[str, str, str]] = []
    for url, title, src in discovered_doc_urls:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append((url, title, src))

    # Per-cohort fetch cap
    target_docs = deduped[:max_docs]

    # Phase D2-D: per-document fetch
    docs_fetched = []
    for url, title, src in target_docs:
        if budget.used_wave >= HARD_CAP_WAVE:
            docs_fetched.append({"url": url, "title": title, "src": src,
                                  "skip": "wave_cap"})
            break
        h = host_of(url)
        ok, reason = budget.allow(h)
        if not ok:
            docs_fetched.append({"url": url, "title": title, "src": src,
                                  "skip": reason})
            continue
        slug = safe_filename(url.rstrip("/").rsplit("/", 1)[-1] or "doc")
        doc_dir = cohort_dir / src / slug
        doc_dir.mkdir(parents=True, exist_ok=True)
        # Decide filename based on URL extension
        fname = "raw_doc.pdf" if url.lower().endswith(".pdf") else "raw_doc.html"
        fpath = doc_dir / fname
        ent = fetch_with_persist(
            url, doc_dir, fname,
            budget, kind=f"d2_{src}",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        # Per-doc meta
        (doc_dir / "_meta.json").write_text(json.dumps({
            "url": url, "title": title, "src": src, "entry": ent,
        }, indent=2))
        docs_fetched.append({"url": url, "title": title, "src": src,
                              "doc_dir": str(doc_dir.relative_to(ARGUS_ROOT)),
                              "entry": ent})

    cohort = {
        "label": "d2_muckrock_documentcloud",
        "discovery_seeds": discovery,
        "discovered_count": len(deduped),
        "docs_targeted": len(target_docs),
        "docs_fetched": docs_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# D3 — EFF /deeplinks/ + /files/ (30s pacing)
# ---------------------------------------------------------------------------
EFF_TOPIC_SEEDS = [
    "https://www.eff.org/issues/cell-tracking",
    "https://www.eff.org/issues/foia",
    "https://www.eff.org/issues/cell-site-simulators-imsi-catchers",
    "https://www.eff.org/issues/automated-license-plate-readers-alpr",
]
EFF_FILE_RE = re.compile(
    r'href="(/files/[^"#?]+\.(?:pdf|PDF))"',
    re.IGNORECASE,
)
EFF_DEEPLINKS_RE = re.compile(
    r'href="(/deeplinks/\d{4}/\d{2}/[^"#?]+)"',
    re.IGNORECASE,
)


def fetch_d3_eff(batch_root: Path, budget: PacerBudget,
                 max_docs: int = 3) -> dict:
    cohort_dir = batch_root / "d3_eff"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== D3 EFF DEEPLINKS + FILES (30s pacing) ===")

    discovery: list[dict] = []
    discovered_pdfs: list[tuple[str, str]] = []  # (url, source_topic)

    for seed_url in EFF_TOPIC_SEEDS:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        slug = safe_filename(seed_url.rstrip("/").rsplit("/", 1)[-1])
        ent = fetch_with_persist(
            seed_url, cohort_dir / "_seeds" / slug, "_index.html",
            budget, kind="seed_topic",
            hash_skip_path=cohort_dir / "_seeds" / slug / "_index.html",
        )
        discovery.append({"surface": "eff_topic", "seed_url": seed_url,
                          "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        body = (ARGUS_ROOT / ent["raw_path_relative"]).read_text(errors="replace")
        # Collect /files/*.pdf direct links
        for path in EFF_FILE_RE.findall(body):
            full = "https://www.eff.org" + path
            if (full, seed_url) not in discovered_pdfs:
                discovered_pdfs.append((full, seed_url))

    # Dedup + cap
    seen = set()
    deduped: list[tuple[str, str]] = []
    for url, src in discovered_pdfs:
        if url in seen:
            continue
        seen.add(url)
        deduped.append((url, src))
    target = deduped[:max_docs]

    docs_fetched = []
    for url, src in target:
        if budget.used_wave >= HARD_CAP_WAVE:
            docs_fetched.append({"url": url, "src": src, "skip": "wave_cap"})
            break
        h = host_of(url)
        ok, reason = budget.allow(h)
        if not ok:
            docs_fetched.append({"url": url, "src": src, "skip": reason})
            continue
        slug = safe_filename(url.rstrip("/").rsplit("/", 1)[-1])
        doc_dir = cohort_dir / "files" / slug
        doc_dir.mkdir(parents=True, exist_ok=True)
        fpath = doc_dir / "raw_doc.pdf"
        ent = fetch_with_persist(
            url, doc_dir, "raw_doc.pdf",
            budget, kind="d3_eff_pdf",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        (doc_dir / "_meta.json").write_text(json.dumps({
            "url": url, "topic_src": src, "entry": ent,
        }, indent=2))
        docs_fetched.append({"url": url, "src": src,
                              "doc_dir": str(doc_dir.relative_to(ARGUS_ROOT)),
                              "entry": ent})

    cohort = {
        "label": "d3_eff",
        "discovery_seeds": discovery,
        "discovered_count": len(deduped),
        "docs_targeted": len(target),
        "docs_fetched": docs_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# D4 — The Intercept (Drone Papers + investigations)
# ---------------------------------------------------------------------------
INTERCEPT_TOPIC_SEEDS = [
    "https://theintercept.com/drone-papers/",
    "https://theintercept.com/series/the-drone-papers/",
]
# Drone Papers articles: theintercept.com/drone-papers/<slug>/
INTERCEPT_ARTICLE_RE = re.compile(
    r'href="(https://theintercept\.com/(?:drone-papers|series/[^"]+)/[^"#?]+)/"',
    re.IGNORECASE,
)
# Embedded PDFs (defense.gov / dtic.mil / s3.documentcloud.org)
EMBED_PDF_RE = re.compile(
    r'(https?://(?:[^/\s"\']+\.)?(?:defense\.gov|dtic\.mil|aspensecurityforum\.org|documentcloud\.org)/[^\s"\'<>]+\.(?:pdf|PDF))',
    re.IGNORECASE,
)


def fetch_d4_intercept(batch_root: Path, budget: PacerBudget,
                        max_docs: int = 3) -> dict:
    cohort_dir = batch_root / "d4_intercept"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== D4 THE INTERCEPT ===")

    discovery: list[dict] = []
    article_urls: list[str] = []

    for seed_url in INTERCEPT_TOPIC_SEEDS:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        slug = safe_filename(seed_url.rstrip("/").rsplit("/", 1)[-1] or "topic")
        ent = fetch_with_persist(
            seed_url, cohort_dir / "_seeds" / slug, "_index.html",
            budget, kind="seed_topic",
            hash_skip_path=cohort_dir / "_seeds" / slug / "_index.html",
        )
        discovery.append({"surface": "intercept_topic", "seed_url": seed_url,
                          "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        body = (ARGUS_ROOT / ent["raw_path_relative"]).read_text(errors="replace")
        for url in INTERCEPT_ARTICLE_RE.findall(body):
            if url not in article_urls and url not in seed_url:
                article_urls.append(url)

    # Cap article fetches
    target_articles = article_urls[:max_docs]
    docs_fetched = []
    embed_pdfs_total: list[tuple[str, str]] = []  # (pdf_url, source_article)

    for art_url in target_articles:
        if budget.used_wave >= HARD_CAP_WAVE:
            docs_fetched.append({"url": art_url, "skip": "wave_cap"})
            break
        h = host_of(art_url)
        ok, reason = budget.allow(h)
        if not ok:
            docs_fetched.append({"url": art_url, "skip": reason})
            continue
        slug = safe_filename(art_url.rstrip("/").rsplit("/", 1)[-1])
        art_dir = cohort_dir / "articles" / slug
        art_dir.mkdir(parents=True, exist_ok=True)
        fpath = art_dir / "raw_doc.html"
        art_ent = fetch_with_persist(
            art_url, art_dir, "raw_doc.html",
            budget, kind="d4_article",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        embeds: list[dict] = []
        if art_ent.get("status") == 200 and art_ent.get("byte_count"):
            body = (ARGUS_ROOT / art_ent["raw_path_relative"]).read_text(errors="replace")
            for pdf_url in EMBED_PDF_RE.findall(body):
                if (pdf_url, art_url) not in embed_pdfs_total:
                    embed_pdfs_total.append((pdf_url, art_url))
        (art_dir / "_meta.json").write_text(json.dumps({
            "url": art_url, "entry": art_ent,
        }, indent=2))
        docs_fetched.append({"url": art_url,
                              "doc_dir": str(art_dir.relative_to(ARGUS_ROOT)),
                              "entry": art_ent})

    # Embedded PDF fetches — cap to max_docs PDFs total
    embed_fetched = []
    for pdf_url, src_art in embed_pdfs_total[:max_docs]:
        if budget.used_wave >= HARD_CAP_WAVE:
            embed_fetched.append({"url": pdf_url, "src_article": src_art,
                                   "skip": "wave_cap"})
            break
        h = host_of(pdf_url)
        ok, reason = budget.allow(h)
        if not ok:
            embed_fetched.append({"url": pdf_url, "src_article": src_art,
                                   "skip": reason})
            continue
        slug = safe_filename(pdf_url.rstrip("/").rsplit("/", 1)[-1])
        pdf_dir = cohort_dir / "embed_pdfs" / slug
        pdf_dir.mkdir(parents=True, exist_ok=True)
        fpath = pdf_dir / "raw_doc.pdf"
        ent = fetch_with_persist(
            pdf_url, pdf_dir, "raw_doc.pdf",
            budget, kind="d4_embed_pdf",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        (pdf_dir / "_meta.json").write_text(json.dumps({
            "url": pdf_url, "src_article": src_art, "entry": ent,
        }, indent=2))
        embed_fetched.append({"url": pdf_url, "src_article": src_art,
                               "doc_dir": str(pdf_dir.relative_to(ARGUS_ROOT)),
                               "entry": ent})

    cohort = {
        "label": "d4_intercept",
        "discovery_seeds": discovery,
        "article_urls_discovered": len(article_urls),
        "articles_fetched": docs_fetched,
        "embed_pdfs_discovered": len(embed_pdfs_total),
        "embed_pdfs_fetched": embed_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# D5 — ProPublica via sitemap.xml (NO URL pattern guessing)
# ---------------------------------------------------------------------------
PROPUBLICA_SITEMAP_ROOT = "https://www.propublica.org/sitemap.xml"


def fetch_d5_propublica(batch_root: Path, budget: PacerBudget,
                         max_docs: int = 2) -> dict:
    cohort_dir = batch_root / "d5_propublica"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== D5 PROPUBLICA (sitemap-driven) ===")

    discovery: list[dict] = []
    article_urls: list[str] = []

    # Step 1: fetch sitemap index
    seed_dir = cohort_dir / "_seeds"
    seed_dir.mkdir(parents=True, exist_ok=True)
    fpath = seed_dir / "sitemap_root.xml"
    root_ent = fetch_with_persist(
        PROPUBLICA_SITEMAP_ROOT, seed_dir, "sitemap_root.xml",
        budget, kind="sitemap_root",
        hash_skip_path=fpath if fpath.exists() else None,
    )
    discovery.append({"surface": "sitemap_root", "entry": root_ent})

    sitemap_urls: list[str] = []
    if root_ent.get("status") == 200 and root_ent.get("byte_count"):
        try:
            tree = ET.fromstring(
                (ARGUS_ROOT / root_ent["raw_path_relative"]).read_bytes())
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for sm in tree.findall("sm:sitemap", ns):
                loc = sm.findtext("sm:loc", default="", namespaces=ns).strip()
                if loc:
                    sitemap_urls.append(loc)
        except Exception as e:
            discovery.append({"surface": "sitemap_root_parse_err",
                              "error": f"{type(e).__name__}: {e}"})

    # Step 2: pull a few sub-sitemaps. Cap at 3 sub-sitemaps to control bandwidth.
    sitemap_targets = []
    # Prefer recent (article-class) sub-sitemaps; ProPublica uses URLs like
    # /sitemap-1.xml, /sitemap-2.xml. Take the first 3.
    for sm_url in sitemap_urls[:3]:
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
        discovery.append({"surface": "sitemap_sub", "url": sm_url,
                          "entry": sub_ent})
        if sub_ent.get("status") != 200 or not sub_ent.get("byte_count"):
            continue
        try:
            tree = ET.fromstring(
                (ARGUS_ROOT / sub_ent["raw_path_relative"]).read_bytes())
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            for u in tree.findall("sm:url", ns):
                loc = u.findtext("sm:loc", default="", namespaces=ns).strip()
                if loc and "/article/" in loc:
                    article_urls.append(loc)
        except Exception:
            continue

    # SOI filter on URL slugs
    soi_articles: list[tuple[str, str]] = []  # (url, kw)
    for url in article_urls:
        slug = url.rsplit("/", 1)[-1].replace("-", " ")
        kw = text_matches_soi(slug)
        if kw:
            soi_articles.append((url, kw))

    target = soi_articles[:max_docs]
    docs_fetched = []
    for url, kw in target:
        if budget.used_wave >= HARD_CAP_WAVE:
            docs_fetched.append({"url": url, "soi_keyword": kw, "skip": "wave_cap"})
            break
        h = host_of(url)
        ok, reason = budget.allow(h)
        if not ok:
            docs_fetched.append({"url": url, "soi_keyword": kw, "skip": reason})
            continue
        slug = safe_filename(url.rstrip("/").rsplit("/", 1)[-1])
        art_dir = cohort_dir / "articles" / slug
        art_dir.mkdir(parents=True, exist_ok=True)
        fpath = art_dir / "raw_doc.html"
        ent = fetch_with_persist(
            url, art_dir, "raw_doc.html",
            budget, kind="d5_article",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        (art_dir / "_meta.json").write_text(json.dumps({
            "url": url, "soi_keyword": kw, "entry": ent,
        }, indent=2))
        docs_fetched.append({"url": url, "soi_keyword": kw,
                              "doc_dir": str(art_dir.relative_to(ARGUS_ROOT)),
                              "entry": ent})

    cohort = {
        "label": "d5_propublica",
        "discovery_seeds": discovery,
        "sitemap_root_indexed_count": len(sitemap_urls),
        "article_urls_discovered": len(article_urls),
        "soi_articles_count": len(soi_articles),
        "docs_fetched": docs_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# D6 — DOJ OIG / OIP reports
# ---------------------------------------------------------------------------
DOJ_TOPIC_SEEDS = [
    "https://oig.justice.gov/reports",
    "https://www.justice.gov/oip/foia-resources",
]
DOJ_FILE_RE = re.compile(
    r'href="((?:https?://(?:www|oig)\.justice\.gov)?/(?:file|sites/default/files/[^"]+|d9/[^"]+|opa/press-release/file/[^"]+)/[^"#?]+)"',
    re.IGNORECASE,
)
DOJ_REPORT_RE = re.compile(
    r'href="(https?://oig\.justice\.gov/reports/[^"#?]+)"',
    re.IGNORECASE,
)
DOJ_DOWNLOAD_RE = re.compile(
    r'href="(/(?:file|d9|sites/default/files|opa/press-release/file)/[^"#?]+)"',
    re.IGNORECASE,
)


def fetch_d6_doj(batch_root: Path, budget: PacerBudget,
                  max_docs: int = 2) -> dict:
    cohort_dir = batch_root / "d6_doj"
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== D6 DOJ OIG/OIP ===")

    discovery: list[dict] = []
    discovered_files: list[tuple[str, str]] = []  # (url, src_seed)

    for seed_url in DOJ_TOPIC_SEEDS:
        if budget.used_wave >= HARD_CAP_WAVE:
            break
        slug = safe_filename(seed_url.rstrip("/").rsplit("/", 1)[-1])
        ent = fetch_with_persist(
            seed_url, cohort_dir / "_seeds" / slug, "_index.html",
            budget, kind="seed_topic",
            hash_skip_path=cohort_dir / "_seeds" / slug / "_index.html",
        )
        discovery.append({"surface": "doj_topic", "seed_url": seed_url,
                          "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        body = (ARGUS_ROOT / ent["raw_path_relative"]).read_text(errors="replace")
        # OIG report-page links
        for url in DOJ_REPORT_RE.findall(body):
            if (url, seed_url) not in discovered_files:
                discovered_files.append((url, seed_url))
        # Direct file download links
        for path in DOJ_DOWNLOAD_RE.findall(body):
            full = ("https://www.justice.gov" + path
                    if path.startswith("/") else path)
            if (full, seed_url) not in discovered_files:
                discovered_files.append((full, seed_url))

    # SOI filter on URL slugs (DOJ OIG report URLs typically encode topic)
    soi_files: list[tuple[str, str, str]] = []  # (url, kw, src_seed)
    for url, src in discovered_files:
        slug = url.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ")
        kw = text_matches_soi(slug)
        if kw:
            soi_files.append((url, kw, src))

    target = soi_files[:max_docs]
    docs_fetched = []
    for url, kw, src in target:
        if budget.used_wave >= HARD_CAP_WAVE:
            docs_fetched.append({"url": url, "soi_keyword": kw,
                                  "skip": "wave_cap"})
            break
        h = host_of(url)
        ok, reason = budget.allow(h)
        if not ok:
            docs_fetched.append({"url": url, "soi_keyword": kw,
                                  "skip": reason})
            continue
        slug = safe_filename(url.rstrip("/").rsplit("/", 1)[-1] or "doc")
        doc_dir = cohort_dir / "files" / slug
        doc_dir.mkdir(parents=True, exist_ok=True)
        fname = "raw_doc.pdf" if url.lower().endswith(".pdf") else "raw_doc.html"
        fpath = doc_dir / fname
        ent = fetch_with_persist(
            url, doc_dir, fname,
            budget, kind="d6_doj",
            hash_skip_path=fpath if fpath.exists() else None,
        )
        (doc_dir / "_meta.json").write_text(json.dumps({
            "url": url, "soi_keyword": kw, "src_seed": src, "entry": ent,
        }, indent=2))
        docs_fetched.append({"url": url, "soi_keyword": kw, "src_seed": src,
                              "doc_dir": str(doc_dir.relative_to(ARGUS_ROOT)),
                              "entry": ent})

    cohort = {
        "label": "d6_doj",
        "discovery_seeds": discovery,
        "discovered_count": len(discovered_files),
        "soi_count": len(soi_files),
        "docs_fetched": docs_fetched,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    env_ts = os.environ.get("MAC31_BATCH_TS", "").strip()
    ts = env_ts or utc_timestamp()
    batch_root = ARGUS_ROOT / "raw" / "court_foia" / ts
    batch_root.mkdir(parents=True, exist_ok=True)
    print(f"Wave-D Step-1 court_foia fetch batch: {batch_root.relative_to(ARGUS_ROOT)}")
    budget = PacerBudget(HARD_CAP_WAVE, HARD_CAP_PER_HOST)

    # Cohort run
    cohorts: list[dict] = []
    cohort_specs = [
        ("d2_muckrock_documentcloud", fetch_d2_muckrock_documentcloud, {"max_docs": 15}),
        ("d3_eff",                    fetch_d3_eff,                    {"max_docs": 3}),
        ("d4_intercept",              fetch_d4_intercept,              {"max_docs": 3}),
        ("d5_propublica",             fetch_d5_propublica,             {"max_docs": 2}),
        ("d6_doj",                    fetch_d6_doj,                    {"max_docs": 2}),
    ]

    for label, fn, kwargs in cohort_specs:
        if budget.used_wave >= HARD_CAP_WAVE:
            print(f"WAVE CAP {HARD_CAP_WAVE} REACHED — halting at {label}")
            break
        try:
            cohort = fn(batch_root, budget, **kwargs)
            cohorts.append(cohort)
        except Exception as e:
            print(f"  cohort {label} ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            cohorts.append({"label": label, "error": f"{type(e).__name__}: {e}"})

    # Wave-aggregate manifest
    manifest = {
        "issue": "MAC-31",
        "phase": "Phase 4 Wave-D Step 1 (Mitigation-B)",
        "run_ts": ts,
        "batch_root": str(batch_root.relative_to(ARGUS_ROOT)),
        "user_agent": USER_AGENT,
        "caps": {"wave": HARD_CAP_WAVE, "per_host": HARD_CAP_PER_HOST},
        "host_pacers_s": HOST_PACERS,
        "soi_keywords_count": len(SOI_KEYWORDS),
        "robots_recheck_run_ts": "20260506T025916Z",
        "wave_calls_used": budget.used_wave,
        "per_host_calls_used": budget.used_per_host,
        "cohorts": cohorts,
        "absence_documented_hosts": [
            "www.courtlistener.com (Mitigation-B; D1 dropped)",
            "vault.fbi.gov (Cloudflare bot-wall)",
            "www.aclu.org (FOIA paths /foia-document/ + /foia-collections/ disallowed)",
            "PACER (§11 #2; never accessed)",
            "Sealed/restricted court records (§11 #2; absence-doc per case)",
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
