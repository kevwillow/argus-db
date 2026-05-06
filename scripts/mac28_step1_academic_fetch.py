"""MAC-28 Phase 4 Wave-C Step 1 — academic corpus fetch (8 cohorts, 400-call cap).

Bible §7.2 SourceWorker scope:
  * Always preserve raw response in raw/academic/<UTC-ts>/<surface>/<paper-id>/
    BEFORE any parsing.
  * Custom ArgusSourceWorker UA (NOT ClaudeBot).
  * Per-host pacers: USENIX 10s, NDSS 2s, arXiv 15s, S2 12s.
  * Sequential, not parallel.
  * On non-200: log failure; preserve byte stream regardless of status; do NOT retry.
  * Robots.txt re-check completed in mac28_step1_robots_recheck.py BEFORE this run.

Step 1 = catalog scan + per-paper SOI filter + per-paper landing + PDF fetch +
manifest. NO Step-1.5b survey (separate script). NO Step-2 extraction.

Hard caps (from MAC-27 ratification §9 #8):
  * Wave-aggregate: 400 HTTP calls.
  * Per-host: 50 calls.

Cohort ordering (binding from MAC-27 ratification §9 #5):
  C1: USENIX Sec 2024
  C2: USENIX Sec 2023
  C3: NDSS 2024
  C4: NDSS 2023
  C5: USENIX Sec 2022
  C6: NDSS 2022
  C7: arXiv cross-ref top-5
  C8: USENIX Sec 2020/2021 + NDSS 2020/2021

Trip lines (binding from MAC-27 §9 #2 + #4):
  * Per-cohort: 0 vendor-gated rows = trip → record + continue (will be
    surveyed at Step-1.5b; halt logic applies when survey result lands).
  * Wave-aggregate floor: N=2 consecutive cohorts at 0 = wave halt
    + reassign CEO per `feedback_per_cohort_trip_line_multi_cohort_waves.md`.

NOTE: Trip evaluation is performed at Step-1.5b survey, not Step-1 fetch.
Step-1 fetches the corpus; survey gates the Step-2 dispatch. The fetch
respects the HTTP caps; cohort yield is data-not-decision at fetch time.
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
from pathlib import Path
from typing import Any, Optional

ARGUS_ROOT = Path(__file__).resolve().parent.parent

USER_AGENT = (
    "ArgusSourceWorker/0.1 (Phase4 Wave-C Step 1 academic corpus fetch; "
    "+https://github.com/argus-project)"
)
TIMEOUT_S = 60.0
HARD_CAP_WAVE = 400
HARD_CAP_PER_HOST = 50

# Per-host pacers (from MAC-27 §9 #6 ratified)
HOST_PACERS = {
    "www.usenix.org": 10.0,
    "www.ndss-symposium.org": 2.0,
    "arxiv.org": 15.0,
    "api.semanticscholar.org": 12.0,
}
DEFAULT_PACER_S = 5.0

# SOI filter — surveillance-equipment-relevant title keywords (case-insensitive
# substring match). Cast wide — Step-1.5b survey gates yield, not Step-1.
SOI_KEYWORDS = [
    # Cop-car cluster (per MAC-27 standing advisory)
    "license plate reader", "license-plate", "alpr", "lpr",
    "body-worn camera", "body worn camera", "body-cam", "bodycam",
    "police radio", "p25 radio", "land mobile radio", "tetra ",
    "in-car camera", "dashcam", "dash cam", "patrol car",
    "flock safety", "motorola apx", "axon", "cradlepoint",
    "sierra wireless", "watchguard",
    # Cellular surveillance / IMSI-catchers
    "imsi catcher", "imsi-catcher", "stingray", "cell-site simulator",
    "cell site simulator", "rogue base station", "fake base station",
    "5g security", "lte security", "baseband",
    # WiFi / BLE fingerprinting + tracking
    "wifi fingerprint", "wi-fi fingerprint", "ssid fingerprint",
    "ble fingerprint", "bluetooth fingerprint", "device fingerprint",
    "mac address", "mac randomization", "mac-address tracking",
    "wifi tracking", "wi-fi tracking", "wireless tracking",
    "ssid tracking", "probe request",
    # Drones / UAVs
    "drone", "uav", "uas ", "remote id", "remoteid", "dji",
    "unmanned aerial",
    # Surveillance / privacy / fixed surveillance
    "surveillance", "fixed surveillance", "facial recognition",
    "video surveillance", "smart city surveillance", "iot surveillance",
    "spy camera", "hidden camera",
    # Hak5-class adversarial WiFi / pentest
    "wifi pineapple", "rubber ducky", "pentest", "adversarial wifi",
    # Police / law enforcement / mass surveillance research
    "law enforcement", "policing", "mass surveillance",
    "traffic stop", "geofence warrant",
]


# ---------------------------------------------------------------------------
# Catalog cohort definitions
# ---------------------------------------------------------------------------
USENIX_CATALOGS = {
    # year_label -> (catalog_url, prefix_for_pdfs, presentation_url_prefix)
    "usenix_sec24": (
        "https://www.usenix.org/conference/usenixsecurity24/technical-sessions",
        "/conference/usenixsecurity24/presentation/",
        "sec24",
    ),
    "usenix_sec23": (
        "https://www.usenix.org/conference/usenixsecurity23/technical-sessions",
        "/conference/usenixsecurity23/presentation/",
        "sec23",
    ),
    "usenix_sec22": (
        "https://www.usenix.org/conference/usenixsecurity22/technical-sessions",
        "/conference/usenixsecurity22/presentation/",
        "sec22",
    ),
    "usenix_sec21": (
        "https://www.usenix.org/conference/usenixsecurity21/technical-sessions",
        "/conference/usenixsecurity21/presentation/",
        "sec21",
    ),
    "usenix_sec20": (
        "https://www.usenix.org/conference/usenixsecurity20/technical-sessions",
        "/conference/usenixsecurity20/presentation/",
        "sec20",
    ),
}

NDSS_CATALOGS = {
    "ndss2024": "https://www.ndss-symposium.org/ndss2024/accepted-papers/",
    "ndss2023": "https://www.ndss-symposium.org/ndss2023/accepted-papers/",
    "ndss2022": "https://www.ndss-symposium.org/ndss2022/accepted-papers/",
    "ndss2021": "https://www.ndss-symposium.org/ndss2021/accepted-papers/",
    "ndss2020": "https://www.ndss-symposium.org/ndss2020/accepted-papers/",
}


# ---------------------------------------------------------------------------
# Pacer + budget bookkeeping
# ---------------------------------------------------------------------------
class PacerBudget:
    def __init__(self, hard_cap_wave: int, hard_cap_per_host: int):
        self.hard_cap_wave = hard_cap_wave
        self.hard_cap_per_host = hard_cap_per_host
        self.used_wave = 0
        self.used_per_host: dict[str, int] = {}
        self.last_call_per_host: dict[str, float] = {}
        # Pacer ledgers persist to disk after each call
        self.ledger_dir = ARGUS_ROOT / "logs"
        self.ledger_dir.mkdir(exist_ok=True)
        # Resume: rehydrate counters from any existing pacer ledgers in this
        # logs dir so a re-invocation respects the per-host cap that was
        # already burned in a prior crashed run.
        for h in HOST_PACERS:
            ledger_path = self.ledger_dir / f"academic_pacer_{h.replace('.', '_')}.json"
            if ledger_path.exists():
                try:
                    prior = json.loads(ledger_path.read_text())
                    self.used_per_host[h] = int(prior.get("calls_used", 0))
                except Exception:
                    pass
        # Wave counter = sum of per-host (best approximation; ledger doesn't
        # persist a global wave counter beyond the per-host snapshot)
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
        ledger_path = self.ledger_dir / f"academic_pacer_{host.replace('.', '_')}.json"
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
# HTTP helper
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
    """Fetch + persist bytes; budgets + paces; idempotent via hash_skip_path."""
    h = host_of(url)
    ok, reason = budget.allow(h)
    if not ok:
        return {"kind": kind, "url": url, "host": h, "status": None,
                "error": f"budget_block_{reason}", "byte_count": 0}
    # Hash-skip idempotency: if file already exists, skip + report
    if hash_skip_path is not None and hash_skip_path.exists() \
       and hash_skip_path.stat().st_size > 0:
        body = hash_skip_path.read_bytes()
        return {"kind": kind, "url": url, "host": h,
                "status": 200,  # synthetic; cached
                "byte_count": len(body),
                "sha256": sha256_hex(body),
                "raw_path_relative": str(hash_skip_path.relative_to(ARGUS_ROOT)),
                "cached_skip": True}
    waited = budget.wait_for_pacer(h)
    res = http_get(url)
    budget.record(h)

    out_dir.mkdir(parents=True, exist_ok=True)
    ct = (res["headers"] or {}).get("Content-Type", "") or ""
    # Extension determination
    ext = ""
    cl = ct.lower()
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
        f"  [W{budget.used_wave:3d}/{HARD_CAP_WAVE} H{h[:18]:18s} {budget.used_per_host[h]:2d}/{HARD_CAP_PER_HOST}]"
        f" {kind[:14]:14s} status={str(res['status']):>5s} bytes={len(res['body']):>9d} {url[:80]}",
        flush=True,
    )
    return entry


# ---------------------------------------------------------------------------
# Catalog parsers
# ---------------------------------------------------------------------------
USENIX_PRESENTATION_RE = re.compile(
    r'<a href="(/conference/usenixsecurity\d{2}/presentation/[^"]+)"[^>]*>\s*([^<]+?)\s*</a>'
)
NDSS_PAPER_RE = re.compile(
    r'href="(https://www\.ndss-symposium\.org/ndss-paper/[^"]+/)"[^>]*>(?:\s*<[^>]*>)*\s*([^<]{5,500}?)\s*<'
)


def parse_usenix_catalog(html: str) -> list[tuple[str, str]]:
    """Return list of (presentation_path, title)."""
    seen = set()
    out = []
    for path, title in USENIX_PRESENTATION_RE.findall(html):
        if path in seen:
            continue
        seen.add(path)
        # Decode common HTML entities
        title = (title.replace("&quot;", '"').replace("&amp;", "&")
                 .replace("&#039;", "'").replace("&apos;", "'")
                 .replace("&lt;", "<").replace("&gt;", ">"))
        out.append((path, title))
    return out


def parse_ndss_catalog(html: str) -> list[tuple[str, str]]:
    """Return list of (paper_url, title)."""
    seen = set()
    out = []
    for url, title in NDSS_PAPER_RE.findall(html):
        if url in seen:
            continue
        seen.add(url)
        title = re.sub(r"\s+", " ", title).strip()
        title = (title.replace("&quot;", '"').replace("&amp;", "&")
                 .replace("&#039;", "'").replace("&apos;", "'"))
        if len(title) < 5 or len(title) > 400:
            continue
        out.append((url, title))
    # Fallback: many NDSS pages list URLs without titles in this form. Add
    # bare URL list as title-less entries (for SOI filter on slug).
    if not out:
        for m in re.finditer(r'href="(https://www\.ndss-symposium\.org/ndss-paper/[^"]+/)"',
                             html):
            url = m.group(1)
            if url in seen:
                continue
            seen.add(url)
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            title_from_slug = slug.replace("-", " ")
            out.append((url, title_from_slug))
    return out


_SOI_PATTERNS: list[tuple[str, "re.Pattern[str]"]] = []


def _build_soi_patterns() -> None:
    if _SOI_PATTERNS:
        return
    for kw in SOI_KEYWORDS:
        # Use word-boundary regex on lowercased text. Hyphens / spaces inside
        # the keyword are matched literally; trailing space treated as
        # word-boundary marker.
        kw_norm = kw.strip()
        # Left word-boundary only (allow trailing chars: drone→drones,
        # pentest→PentestGPT). Right-side \b would miss compound nouns;
        # left-only \b kills the FP class (axon→taxonomy).
        kw_core = kw_norm.rstrip()
        pat = r"\b" + re.escape(kw_core)
        _SOI_PATTERNS.append((kw, re.compile(pat, re.IGNORECASE)))


def title_matches_soi(title: str) -> Optional[str]:
    _build_soi_patterns()
    for kw, pat in _SOI_PATTERNS:
        if pat.search(title):
            return kw
    return None


# ---------------------------------------------------------------------------
# Per-paper fetchers
# ---------------------------------------------------------------------------
USENIX_PDF_RE_ALL = re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE)


def usenix_extract_pdf_url(landing_html: bytes, base_url: str) -> Optional[str]:
    """Pick the paper PDF, NOT slides. USENIX presentation pages typically host:
    - usenixsecurityYY-<slug>.pdf or sec24fall-prepub-NNN-<slug>.pdf  → paper
    - secYY_slides_<slug>.pdf or *-slides-*.pdf                       → slides
    - usenixsecurityYY_<slug>_poster.pdf                              → poster
    Prefer paper > poster > slides > anything-else.
    """
    txt = landing_html.decode("utf-8", errors="replace")
    candidates = USENIX_PDF_RE_ALL.findall(txt)
    if not candidates:
        return None
    def rank(href: str) -> int:
        h = href.lower()
        if "_slides_" in h or "-slides-" in h or "slides_" in h:
            return 3
        if "_poster" in h or "-poster" in h:
            return 2
        if re.search(r"usenixsecurity\d{2}[-_]", h) or re.search(r"sec\d{2}[a-z]*-(?:fall-prepub|paper|prepub|interior)", h):
            return 0  # paper, highest priority
        if re.search(r"sec\d{2}[a-z_-]+\.pdf$", h):
            return 1  # ambiguous — could be paper
        return 1
    best = sorted(candidates, key=rank)[0]
    href = best
    if href.startswith("/"):
        href = "https://www.usenix.org" + href
    elif not href.startswith("http"):
        href = urllib.parse.urljoin(base_url, href)
    return href


NDSS_PDF_RE = re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE)


def ndss_extract_pdf_url(landing_html: bytes, base_url: str) -> Optional[str]:
    txt = landing_html.decode("utf-8", errors="replace")
    candidates = NDSS_PDF_RE.findall(txt)
    # Prefer NDSS-domain PDFs over anything else
    for c in candidates:
        if "ndss-symposium.org" in c.lower() and c.lower().endswith(".pdf"):
            return c if c.startswith("http") else urllib.parse.urljoin(base_url, c)
    if candidates:
        c = candidates[0]
        return c if c.startswith("http") else urllib.parse.urljoin(base_url, c)
    return None


# ---------------------------------------------------------------------------
# Cohort runner
# ---------------------------------------------------------------------------
def fetch_usenix_cohort(cohort_label: str, year_key: str, batch_root: Path,
                        budget: PacerBudget, max_papers: int = 30) -> dict:
    catalog_url, presentation_prefix, sec_prefix = USENIX_CATALOGS[year_key]
    cohort_dir = batch_root / cohort_label
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {cohort_label.upper()} === {catalog_url}")
    cat_path = cohort_dir / f"_catalog_{year_key}.html"
    cat_entry = fetch_with_persist(
        catalog_url, cohort_dir, f"_catalog_{year_key}.html",
        budget, kind="catalog",
        hash_skip_path=cat_path if cat_path.exists() else None,
    )
    if cat_entry.get("status") != 200 or not cat_entry.get("byte_count"):
        return {"label": cohort_label, "catalog_entry": cat_entry,
                "papers_fetched": [], "soi_total": 0, "papers_total": 0,
                "halt_reason": "catalog_unreachable"}
    # Parse catalog
    cat_path = ARGUS_ROOT / cat_entry["raw_path_relative"]
    html = cat_path.read_text(errors="replace")
    presentations = parse_usenix_catalog(html)
    soi_hits: list[tuple[str, str, str]] = []  # (slug, title, kw)
    for path, title in presentations:
        kw = title_matches_soi(title)
        if kw:
            slug = path.rsplit("/", 1)[-1]
            soi_hits.append((slug, title, kw))
    print(f"  catalog: {len(presentations)} papers; SOI hits: {len(soi_hits)}")
    # Cap per cohort
    soi_hits = soi_hits[:max_papers]
    papers = []
    for slug, title, kw in soi_hits:
        ok, reason = budget.allow("www.usenix.org")
        if not ok:
            papers.append({"slug": slug, "title": title, "soi_keyword": kw,
                           "skip": reason})
            break
        # Per-paper subdirectory
        paper_dir = cohort_dir / slug
        paper_dir.mkdir(exist_ok=True)
        landing_url = "https://www.usenix.org" + presentation_prefix + slug
        landing_path = paper_dir / "_landing.html"
        landing_entry = fetch_with_persist(
            landing_url, paper_dir, "_landing.html",
            budget, kind="landing",
            hash_skip_path=landing_path if landing_path.exists() else None,
        )
        # Try PDF extraction from landing
        pdf_entry = None
        pdf_url = None
        if landing_entry.get("status") == 200 and landing_entry.get("byte_count"):
            landing_body = (ARGUS_ROOT / landing_entry["raw_path_relative"]).read_bytes()
            pdf_url = usenix_extract_pdf_url(landing_body, landing_url)
            if pdf_url:
                ok2, reason2 = budget.allow(host_of(pdf_url))
                if not ok2:
                    pdf_entry = {"url": pdf_url, "skip": reason2}
                else:
                    pdf_path = paper_dir / "paper.pdf"
                    pdf_entry = fetch_with_persist(
                        pdf_url, paper_dir, "paper.pdf",
                        budget, kind="pdf",
                        hash_skip_path=pdf_path if pdf_path.exists() else None,
                    )
        papers.append({
            "slug": slug,
            "title": title,
            "soi_keyword": kw,
            "landing_entry": landing_entry,
            "pdf_url": pdf_url,
            "pdf_entry": pdf_entry,
        })
        if budget.used_wave >= HARD_CAP_WAVE:
            break
    cohort = {
        "label": cohort_label,
        "year_key": year_key,
        "catalog_url": catalog_url,
        "catalog_entry": cat_entry,
        "papers_total": len(presentations),
        "soi_total": len(soi_hits),
        "papers_fetched": papers,
    }
    # Per-cohort manifest
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


def fetch_ndss_cohort(cohort_label: str, year_key: str, batch_root: Path,
                      budget: PacerBudget, max_papers: int = 15) -> dict:
    catalog_url = NDSS_CATALOGS[year_key]
    cohort_dir = batch_root / cohort_label
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {cohort_label.upper()} === {catalog_url}")
    cat_path = cohort_dir / f"_catalog_{year_key}.html"
    cat_entry = fetch_with_persist(
        catalog_url, cohort_dir, f"_catalog_{year_key}.html",
        budget, kind="catalog",
        hash_skip_path=cat_path if cat_path.exists() else None,
    )
    if cat_entry.get("status") != 200 or not cat_entry.get("byte_count"):
        return {"label": cohort_label, "catalog_entry": cat_entry,
                "papers_fetched": [], "soi_total": 0, "papers_total": 0,
                "halt_reason": "catalog_unreachable"}
    cat_path = ARGUS_ROOT / cat_entry["raw_path_relative"]
    html = cat_path.read_text(errors="replace")
    paper_links = parse_ndss_catalog(html)
    soi_hits: list[tuple[str, str, str]] = []
    for url, title in paper_links:
        kw = title_matches_soi(title)
        if kw:
            soi_hits.append((url, title, kw))
    print(f"  catalog: {len(paper_links)} papers; SOI hits: {len(soi_hits)}")
    soi_hits = soi_hits[:max_papers]
    papers = []
    for url, title, kw in soi_hits:
        ok, reason = budget.allow("www.ndss-symposium.org")
        if not ok:
            papers.append({"url": url, "title": title, "soi_keyword": kw,
                           "skip": reason})
            break
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        paper_dir = cohort_dir / slug
        paper_dir.mkdir(exist_ok=True)
        landing_path = paper_dir / "_landing.html"
        landing_entry = fetch_with_persist(
            url, paper_dir, "_landing.html",
            budget, kind="landing",
            hash_skip_path=landing_path if landing_path.exists() else None,
        )
        pdf_entry = None
        pdf_url = None
        if landing_entry.get("status") == 200 and landing_entry.get("byte_count"):
            landing_body = (ARGUS_ROOT / landing_entry["raw_path_relative"]).read_bytes()
            pdf_url = ndss_extract_pdf_url(landing_body, url)
            if pdf_url:
                ok2, reason2 = budget.allow(host_of(pdf_url))
                if not ok2:
                    pdf_entry = {"url": pdf_url, "skip": reason2}
                else:
                    pdf_path = paper_dir / "paper.pdf"
                    pdf_entry = fetch_with_persist(
                        pdf_url, paper_dir, "paper.pdf",
                        budget, kind="pdf",
                        hash_skip_path=pdf_path if pdf_path.exists() else None,
                    )
        papers.append({
            "slug": slug,
            "url": url,
            "title": title,
            "soi_keyword": kw,
            "landing_entry": landing_entry,
            "pdf_url": pdf_url,
            "pdf_entry": pdf_entry,
        })
        if budget.used_wave >= HARD_CAP_WAVE:
            break
    cohort = {
        "label": cohort_label,
        "year_key": year_key,
        "catalog_url": catalog_url,
        "catalog_entry": cat_entry,
        "papers_total": len(paper_links),
        "soi_total": len(soi_hits),
        "papers_fetched": papers,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


def fetch_arxiv_crossref(cohort_label: str, batch_root: Path,
                         budget: PacerBudget, max_papers: int = 5) -> dict:
    """Browse arXiv /list/cs.{CR,NI,HC,CY}/recent and fetch top SOI matches."""
    cohort_dir = batch_root / cohort_label
    cohort_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {cohort_label.upper()} === arXiv recent listings")
    surfaces = ["cs.CR", "cs.NI", "cs.HC", "cs.CY"]
    catalog_entries = []
    candidates: list[tuple[str, str, str]] = []  # (arxiv_id, title, kw)
    for surf in surfaces:
        url = f"https://arxiv.org/list/{surf}/recent"
        cat_fname = f"_catalog_arxiv_{surf.replace('.', '_')}.html"
        cat_path = cohort_dir / cat_fname
        ent = fetch_with_persist(
            url, cohort_dir, cat_fname,
            budget, kind="catalog",
            hash_skip_path=cat_path if cat_path.exists() else None,
        )
        catalog_entries.append({"surface": surf, "entry": ent})
        if ent.get("status") != 200 or not ent.get("byte_count"):
            continue
        body = (ARGUS_ROOT / ent["raw_path_relative"]).read_text(errors="replace")
        # arXiv listing pages have <a href="/abs/XXXX.YYYYY">arXiv:XXXX.YYYYY</a>
        # and the title appears in nearby <span class="descriptor">Title:</span>
        # but to keep it stdlib + robust we extract by id+adjacent line.
        # Simpler: pull (id, title) pairs by ID anchors then look in surrounding text.
        ids = re.findall(r'href="/abs/(\d{4}\.\d{4,5})"', body)
        # Title block: <div class="list-title mathjax"> <span class="descriptor">Title:</span> <title text> </div>
        title_blocks = re.findall(
            r'<div class="list-title mathjax">\s*<span class="descriptor">Title:</span>\s*([^<]+?)\s*</div>',
            body,
        )
        # Pair up by position (arXiv listing is ordered)
        for aid, title in zip(ids, title_blocks):
            kw = title_matches_soi(title.strip())
            if kw:
                candidates.append((aid, title.strip(), kw))
        if budget.used_wave >= HARD_CAP_WAVE:
            break
    # Dedup arxiv ids; cap to max_papers
    seen_ids = set()
    deduped = []
    for aid, title, kw in candidates:
        if aid in seen_ids:
            continue
        seen_ids.add(aid)
        deduped.append((aid, title, kw))
        if len(deduped) >= max_papers:
            break
    papers = []
    for aid, title, kw in deduped:
        ok, reason = budget.allow("arxiv.org")
        if not ok:
            papers.append({"arxiv_id": aid, "title": title, "soi_keyword": kw,
                           "skip": reason})
            break
        paper_dir = cohort_dir / aid
        paper_dir.mkdir(exist_ok=True)
        # Abs page (provenance) + PDF
        abs_url = f"https://arxiv.org/abs/{aid}"
        abs_path = paper_dir / "_abs.html"
        abs_entry = fetch_with_persist(
            abs_url, paper_dir, "_abs.html",
            budget, kind="landing",
            hash_skip_path=abs_path if abs_path.exists() else None,
        )
        pdf_url = f"https://arxiv.org/pdf/{aid}"
        pdf_path = paper_dir / "paper.pdf"
        pdf_entry = fetch_with_persist(
            pdf_url, paper_dir, "paper.pdf",
            budget, kind="pdf",
            hash_skip_path=pdf_path if pdf_path.exists() else None,
        )
        papers.append({
            "arxiv_id": aid,
            "title": title,
            "soi_keyword": kw,
            "abs_url": abs_url,
            "pdf_url": pdf_url,
            "abs_entry": abs_entry,
            "pdf_entry": pdf_entry,
        })
        if budget.used_wave >= HARD_CAP_WAVE:
            break
    cohort = {
        "label": cohort_label,
        "surfaces": surfaces,
        "catalog_entries": catalog_entries,
        "candidates_total": len(candidates),
        "candidates_unique": len(deduped),
        "papers_fetched": papers,
    }
    (cohort_dir / "_manifest.json").write_text(json.dumps(cohort, indent=2))
    return cohort


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    # Resume support: if MAC28_BATCH_TS env var set, reuse that batch directory
    # so hash-skip idempotency rehydrates already-fetched files. Otherwise mint a
    # fresh timestamp.
    env_ts = os.environ.get("MAC28_BATCH_TS", "").strip()
    ts = env_ts or utc_timestamp()
    batch_root = ARGUS_ROOT / "raw" / "academic" / ts
    batch_root.mkdir(parents=True, exist_ok=True)
    print(f"Wave-C Step-1 fetch batch: {batch_root.relative_to(ARGUS_ROOT)}")
    budget = PacerBudget(HARD_CAP_WAVE, HARD_CAP_PER_HOST)

    cohorts: list[dict] = []
    cohort_specs = [
        ("c1_usenix_sec24", "usenix", "usenix_sec24"),
        ("c2_usenix_sec23", "usenix", "usenix_sec23"),
        ("c3_ndss2024",     "ndss",   "ndss2024"),
        ("c4_ndss2023",     "ndss",   "ndss2023"),
        ("c5_usenix_sec22", "usenix", "usenix_sec22"),
        ("c6_ndss2022",     "ndss",   "ndss2022"),
        ("c7_arxiv_recent", "arxiv",  None),
        ("c8a_usenix_sec21","usenix", "usenix_sec21"),
        ("c8b_usenix_sec20","usenix", "usenix_sec20"),
        ("c8c_ndss2021",    "ndss",   "ndss2021"),
        ("c8d_ndss2020",    "ndss",   "ndss2020"),
    ]

    for label, kind, year_key in cohort_specs:
        if budget.used_wave >= HARD_CAP_WAVE:
            print(f"WAVE CAP {HARD_CAP_WAVE} REACHED — halting at {label}")
            break
        try:
            if kind == "usenix":
                cohort = fetch_usenix_cohort(label, year_key, batch_root, budget,
                                             max_papers=30)
            elif kind == "ndss":
                cohort = fetch_ndss_cohort(label, year_key, batch_root, budget,
                                           max_papers=15)
            elif kind == "arxiv":
                cohort = fetch_arxiv_crossref(label, batch_root, budget,
                                              max_papers=5)
            else:
                continue
            cohorts.append(cohort)
        except Exception as e:
            print(f"  cohort {label} ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            cohorts.append({"label": label, "error": f"{type(e).__name__}: {e}"})

    # Wave-aggregate manifest
    manifest = {
        "issue": "MAC-28",
        "phase": "Phase 4 Wave-C Step 1",
        "run_ts": ts,
        "batch_root": str(batch_root.relative_to(ARGUS_ROOT)),
        "user_agent": USER_AGENT,
        "caps": {"wave": HARD_CAP_WAVE, "per_host": HARD_CAP_PER_HOST},
        "host_pacers_s": HOST_PACERS,
        "soi_keywords_count": len(SOI_KEYWORDS),
        "robots_recheck_run_ts": "20260506T015122Z",
        "wave_calls_used": budget.used_wave,
        "per_host_calls_used": budget.used_per_host,
        "cohorts": cohorts,
    }
    (batch_root / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n=== WAVE COMPLETE ===")
    print(f"  wave_calls_used: {budget.used_wave}/{HARD_CAP_WAVE}")
    print(f"  per_host: {budget.used_per_host}")
    print(f"  manifest: {batch_root / '_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
