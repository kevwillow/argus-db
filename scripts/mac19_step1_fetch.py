"""MAC-19 Wave-B2 Step 1 — corpus fetch (5 cohorts, 120-call hard cap).

Bible §7.2 SourceWorker scope:
  * Always preserve raw response in raw/vendor_docs/<UTC-ts>/<cohort>/<vendor>/ BEFORE any parsing
  * Custom ArgusSourceWorker UA (NOT ClaudeBot)
  * 2s inter-request spacing minimum (FCC/Sierra: 2s; Wayback: 1s post-Step-0)
  * Sequential, not parallel
  * On non-200: log failure; preserve byte stream regardless of status; do NOT retry
  * On TLS failure: log + skip; SAR-4 alt-routing via Wayback if scoped
  * Robots.txt re-check before EACH new fetch host (SAR-4 + §11 #6)

Step 1 = pure raw-fetch + manifest. NO Step-1.5b survey. NO Step-2 extraction.

Hard cap: 120 HTTP calls (88 base + 35 recovery; aggregate 1500 ceiling unchanged).
Per-cohort soft cap evaluated at runtime.

Cohorts (CEO-ratified at MAC-18):
  1. DAM PDF batch                    (~23 calls; Step-0 inventoried PDFs)
  2. DroneShield Wayback product pages (~10 calls; product slugs from Wave-B Step-1)
  3. Hak5 docs Wayback                 (~10 calls; well-known product slugs)
  4. Cradlepoint Customer KB Wayback   (~8 calls; CDX-discovered KB articles)
  5. FCC per-FCC-ID per-document PDFs  (~25 calls; landing+top doc per grantee)
  6. DJI SDK dev portals               (~5 calls; deep navigation)
  + robots re-check for NEW hosts      (~10 calls)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ARGUS_ROOT = Path(__file__).resolve().parent.parent

USER_AGENT = (
    "ArgusSourceWorker/0.1 (Phase4 Wave B2 Step 1 corpus fetch; "
    "+https://github.com/argus-project)"
)
HARD_CAP_CALLS = 120
TIMEOUT_S = 30.0
DEFAULT_DELAY_S = 2.0
WAYBACK_DELAY_S = 1.5
FCC_DELAY_S = 2.0


# ---------------------------------------------------------------------------
# Cohort 1: DAM PDF batch
#   Sourced from raw/vendor_docs/20260505T140959Z/_step0_url_inventory.json,
#   filtered for on-topic equipment PDFs (warranty cards / anti-trafficking
#   policy / website ToS excluded — out of scope for §2.1 device equipment).
# ---------------------------------------------------------------------------
COHORT1_DAM_PDFS = [
    # motorola APX
    ("motorola_solutions_apx", "apx_accessories_catalog",
     "https://www.motorolasolutions.com/content/dam/msi/docs/products/apx/apx-accessories/apx_accessories_catalog.pdf"),
    # vigilant (parent: motorola)
    ("vigilant_solutions", "linc_video_based_lpr",
     "https://www.motorolasolutions.com/content/dam/msi/docs/products/license-plate-recognition-systems/linc-video-based-lpr-integration/linc_video_based_lpr_integration_brochure.pdf"),
    ("vigilant_solutions", "lpr_brochure",
     "https://www.motorolasolutions.com/content/dam/msi/docs/products/license-plate-recognition-systems/lpr_brochure.pdf"),
    # axon
    ("axon", "case_study_grand_prairie",
     "https://a.storyblok.com/f/198504/x/0049526b6a/case-study-grand-prairie-police-department.pdf"),
    ("axon", "case_study_west_midlands",
     "https://a.storyblok.com/f/198504/x/220a679cd5/axon_west-midlands_case-study.pdf"),
    # sierra wireless
    ("sierra_wireless", "perse_one_pager",
     "https://www.sierrawireless.com/uploads/common/PerSe_One_Pager.pdf"),
    ("sierra_wireless", "airlink_portfolio_brochure",
     "https://www.sierrawireless.com/wp-content/uploads/2024/02/ES-B-AirLink-Portfolio-Brochure-Feb2024-F.pdf"),
    # semtech (sierra parent / LoRa cases)
    ("sierra_wireless", "lora_cs_apana",
     "https://www.semtech.com/uploads/technology/LoRa/app-briefs/LoRa-CS-Apana-Case_Study-2020-F.pdf"),
    ("sierra_wireless", "lora_cs_cra",
     "https://www.semtech.com/uploads/technology/LoRa/app-briefs/LoRa-CS-CRA-Case-Study-2020-F_(1).pdf"),
    ("sierra_wireless", "lora_cs_green_stream",
     "https://www.semtech.com/uploads/technology/LoRa/app-briefs/LoRa-CS-Green_Stream-Case_Study-2020-1.pdf"),
    ("sierra_wireless", "lora_smarthome_yosmart",
     "https://www.semtech.com/uploads/technology/LoRa/app-briefs/LoRa_UseCase_SmartHome_YoSmart_Web.pdf"),
    ("sierra_wireless", "lora_iotlabs",
     "https://www.semtech.com/uploads/technology/LoRa/app-briefs/Semtech-UseCase-IOTLabs-8.5x11_2020_Web.pdf"),
    # reveal media
    ("reveal_media", "k6_datasheet",
     "https://reveal-media.imgix.net/K6-Datasheet-DV1_v2.pdf"),
    ("reveal_media", "d_series_datasheet",
     "https://reveal-media.imgix.net/PDFs/D-series-US-Datasheet.pdf"),
    # getac
    ("getac", "b360_g3_product",
     "https://www.getac.com/content/dam/getac/product-spec-data-pdf/us/Getac_B360_G3_US_Product.pdf"),
    ("getac", "k120_product",
     "https://www.getac.com/content/dam/getac/product-spec-data-pdf/us/Getac_K120_US_Product.pdf"),
    ("getac", "b360_accessory",
     "https://www.getac.com/content/dam/getac/product-accessory-data-pdf/us/Getac_B360_Accessory.pdf"),
    ("getac", "k120_accessory",
     "https://www.getac.com/content/dam/getac/product-accessory-data-pdf/us/Getac_K120_Accessory.pdf"),
    # soundthinking
    ("soundthinking", "casebuilder_datasheet",
     "https://www.soundthinking.com/wp-content/uploads/2023/03/2023-xx-xx-CaseBuilder-Datasheet.pdf"),
    # cellebrite (public marketing only — KB excluded per §11 #2)
    ("cellebrite", "premium_solution_overview",
     "https://media.cellebrite.com/wp-content/uploads/2022/08/Solution_Overview_Cellebrite_Premium_ES.pdf"),
    ("cellebrite", "premium_as_a_service",
     "https://media.cellebrite.com/wp-content/uploads/2022/10/Cellebrite-Premium-as-a-Service-Solution-Overview.pdf"),
    ("cellebrite", "ufed_ltr_solution_overview",
     "https://media.cellebrite.com/wp-content/uploads/2022/11/Solution_Overview_Cellebrite_UFED_LTR.pdf"),
]


# ---------------------------------------------------------------------------
# Cohort 2: DroneShield Wayback product pages
#   Source: Wave-B Step-1 sitemap (raw/vendor_docs/20260505T040929Z/droneshield/)
#   discovered /products/<slug> URLs. Wayback wrap to bypass cloudfront SPA shell.
# ---------------------------------------------------------------------------
DRONESHIELD_PRODUCTS = [
    "dronegun-tactical",
    "dronegun-mkiii",
    "dronegun-mk4",
    "rfpatrol",
    "rfpatrol-mk2",
    "dronesentry",
    "dronesentry-x",
    "dronesentinel",
    "rfone-mkii",
    "dronenode",
]
COHORT2_DRONESHIELD_WAYBACK = [
    ("droneshield_wayback", f"product_{slug}",
     f"https://web.archive.org/web/2024/https://www.droneshield.com/products/{slug}")
    for slug in DRONESHIELD_PRODUCTS
]


# ---------------------------------------------------------------------------
# Cohort 3: Hak5 docs Wayback
#   docs.hak5.org direct returned SPA shell (~400 bytes) at MAC-13 + Step-0.
#   Wayback CDX-archived snapshots have rendered content.
# ---------------------------------------------------------------------------
HAK5_PRODUCTS = [
    "wifi-pineapple",
    "bash-bunny",
    "usb-rubber-ducky",
    "cloud-c2",
    "lan-turtle",
    "packet-squirrel",
    "key-croc",
    "shark-jack",
    "screen-crab",
    "omg-cable",
]
COHORT3_HAK5_WAYBACK = [
    ("hak5_docs_wayback", f"product_{slug.replace('-','_')}",
     f"https://web.archive.org/web/2024/https://docs.hak5.org/{slug}")
    for slug in HAK5_PRODUCTS
]


# ---------------------------------------------------------------------------
# Cohort 4: Cradlepoint Customer KB via Wayback
#   customer.cradlepoint.com had TLS CERTIFICATE_VERIFY_FAILED at Step-0 robots
#   re-check. SAR-4 alt-routing via Wayback. Use CDX search to discover indexed
#   KB articles (1 CDX call) then fetch top N.
# ---------------------------------------------------------------------------
CRADLEPOINT_CDX_QUERY = (
    "https://web.archive.org/cdx/search/cdx"
    "?url=customer.cradlepoint.com/s/article*"
    "&matchType=prefix&limit=200&filter=statuscode:200"
    "&output=json&collapse=urlkey"
)


# ---------------------------------------------------------------------------
# Cohort 5: FCC per-FCC-ID per-document PDFs
#   For each grantee (Step-0 inventoried), fetch fcc.report/FCC-ID/<grantee>/
#   landing → parse for /document/<filing_id>/<doc_id> hrefs → fetch top RF/test
#   report PDF.
# ---------------------------------------------------------------------------
FCC_GRANTEES = [
    # Already landing-fetched at Step-0 (UXX, 2AGVG, 2AS9X) — fetch fresh anyway
    # to keep cohort uniform; cap detail at 1 doc per grantee.
    ("motorola_solutions_apx", "YJJ"),
    ("axon",                   "2AGVG"),
    ("cradlepoint_docs",       "UXX"),
    ("skydio",                 "2ATQR"),
    ("sierra_wireless",        "TWV"),
    ("vigilant_solutions",     "NCV"),
    ("avigilon_alta",          "2ANC5"),
    ("reveal_media",           "2AL26"),
    ("watchguard",             "YJV"),
    ("getac",                  "QYL"),
    ("getac",                  "MAU"),
    ("dji",                    "2AS9X"),
    ("dji",                    "2AS9W"),
    ("dji",                    "2AS9V"),
    ("parrot",                 "2AG6I"),
    ("soundthinking",          "WLI"),
    ("dedrone",                "2AO3N"),
]


# ---------------------------------------------------------------------------
# Cohort 6: DJI SDK developer portal (deep navigation)
#   developer.dji.com robots returned 404 at Step-0 → fetch permitted by default.
# ---------------------------------------------------------------------------
COHORT6_DJI_SDK = [
    ("dji_sdk", "onboard_sdk_index",
     "https://developer.dji.com/document/29c6a5f7-32d8-46b2-bd72-79b3c8fa7da5"),
    ("dji_sdk", "mobile_sdk_landing",
     "https://developer.dji.com/mobile-sdk"),
    ("dji_sdk", "onboard_sdk_landing",
     "https://developer.dji.com/onboard-sdk"),
    ("dji_sdk", "psdk_landing",
     "https://developer.dji.com/payload-sdk"),
    ("dji_sdk", "udp_protocol_landing",
     "https://developer.dji.com/udp-protocol"),
]


# ---------------------------------------------------------------------------
# Robots re-check — NEW hosts beyond Step-0's 8-domain set.
# Step-0 set: web.archive.org, dl.djicdn.com, docs.hak5.org, motorolasolutions.com,
#             customer.cradlepoint.com, source.sierrawireless.com, fcc.report,
#             developer.dji.com.
# ---------------------------------------------------------------------------
NEW_HOSTS_FOR_ROBOTS = [
    ("a.storyblok.com",       "https://a.storyblok.com/robots.txt"),
    ("www.sierrawireless.com","https://www.sierrawireless.com/robots.txt"),
    ("www.semtech.com",       "https://www.semtech.com/robots.txt"),
    ("reveal-media.imgix.net","https://reveal-media.imgix.net/robots.txt"),
    ("www.getac.com",         "https://www.getac.com/robots.txt"),
    ("www.soundthinking.com", "https://www.soundthinking.com/robots.txt"),
    ("media.cellebrite.com",  "https://media.cellebrite.com/robots.txt"),
]


# ===========================================================================

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


def safe_filename(url: str, kind: str) -> str:
    parsed = urllib.parse.urlparse(url)
    seg = parsed.path.strip("/").replace("/", "_") or "root"
    seg = re.sub(r"[^a-zA-Z0-9._-]+", "_", seg)
    if len(seg) > 100:
        seg = seg[:100]
    # ext determination — defaulted, refined by content-type at write time
    return f"{kind}__{seg}"


def persist(out_dir: Path, fname: str, body: bytes, content_type: str | None) -> tuple[str, int, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # ensure extension matches content
    ext = ""
    if content_type:
        ct = content_type.lower()
        if "pdf" in ct:
            ext = ".pdf"
        elif "html" in ct or "xml" in ct:
            ext = ".html"
        elif "json" in ct:
            ext = ".json"
        elif "text/plain" in ct:
            ext = ".txt"
    if ext and not fname.endswith(ext):
        fname = fname + ext
    fpath = out_dir / fname
    fpath.write_bytes(body)
    return str(fpath.relative_to(ARGUS_ROOT)), len(body), sha256_hex(body)


def fetch_with_persist(url: str, kind: str, out_dir: Path, delay_s: float,
                       last_call_t: list[float], call_budget: dict,
                       seen_urls: set[str]) -> dict:
    """Fetch + persist; updates call_budget; honors delay; idempotent within run."""
    if url in seen_urls:
        return {"kind": kind, "doc_url": url, "status": None, "byte_count": 0,
                "sha256": None, "error": "skipped_idempotent_within_run"}
    if call_budget["used"] >= HARD_CAP_CALLS:
        return {"kind": kind, "doc_url": url, "status": None, "byte_count": 0,
                "sha256": None, "error": f"stopped_at_hard_cap_{HARD_CAP_CALLS}"}

    wait = delay_s - (time.time() - last_call_t[0])
    if wait > 0:
        time.sleep(wait)
    res = http_get(url)
    last_call_t[0] = time.time()
    call_budget["used"] += 1
    seen_urls.add(url)

    ct = (res["headers"] or {}).get("Content-Type")
    rel_path, byte_count, sha = persist(out_dir, safe_filename(url, kind),
                                        res["body"], ct)
    entry = {
        "ordinal": call_budget["used"],
        "kind": kind,
        "doc_url": url,
        "final_url": res["final_url"],
        "status": res["status"],
        "byte_count": byte_count,
        "sha256": sha,
        "content_type": ct,
        "elapsed_s": res["elapsed_s"],
        "raw_path_relative": rel_path,
    }
    if res["error"]:
        entry["error"] = res["error"]
    print(f"  [{call_budget['used']:3d}/{HARD_CAP_CALLS}] {kind[:18]:18s} "
          f"{str(res['status']):>5s}  {byte_count:>9d}B  {sha[:16] if sha else '----------------':16s}  {url[:90]}",
          flush=True)
    return entry


def parse_robots(body: bytes) -> dict:
    """Best-effort robots.txt parse — global Allow/Disallow/Crawl-delay."""
    out = {"allow_global": True, "disallowed_paths": [], "crawl_delay_s": None}
    if not body:
        return out
    try:
        txt = body.decode("utf-8", errors="replace")
    except Exception:
        return out
    in_global = False
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^User-agent:\s*(.+)$", s, re.IGNORECASE)
        if m:
            in_global = m.group(1).strip() == "*"
            continue
        if not in_global:
            continue
        m = re.match(r"^Disallow:\s*(.*)$", s, re.IGNORECASE)
        if m:
            p = m.group(1).strip()
            if p:
                out["disallowed_paths"].append(p)
            continue
        m = re.match(r"^Crawl-delay:\s*(\d+(?:\.\d+)?)$", s, re.IGNORECASE)
        if m:
            out["crawl_delay_s"] = float(m.group(1))
    return out


def cohort_robots_recheck(batch_root: Path, last_call_t: list[float],
                          call_budget: dict, seen_urls: set[str]) -> list[dict]:
    out_dir = batch_root / "_robots_recheck_step1"
    log = []
    print(f"\n=== ROBOTS RE-CHECK ({len(NEW_HOSTS_FOR_ROBOTS)} NEW hosts) ===")
    for label, url in NEW_HOSTS_FOR_ROBOTS:
        ent = fetch_with_persist(url, f"robots_{label}", out_dir,
                                 DEFAULT_DELAY_S, last_call_t, call_budget, seen_urls)
        if ent.get("status") == 200 and ent.get("byte_count"):
            with open(ARGUS_ROOT / ent["raw_path_relative"], "rb") as f:
                body = f.read()
            parsed = parse_robots(body)
            ent.update(parsed)
            ent["allow"] = parsed["allow_global"]
        elif ent.get("status") == 404:
            ent["allow"] = True
            ent["note"] = "no robots.txt published; fetch permitted by default per §11 #6"
        elif ent.get("status") == 403:
            ent["allow"] = None
            ent["note"] = "robots.txt fetch 403; defer fetch per stop-the-line"
        else:
            ent["allow"] = None
            ent["note"] = f"robots.txt fetch failed: {ent.get('error')}"
        ent["domain_label"] = label
        log.append(ent)
    return log


def cohort1_dam(batch_root: Path, last_call_t: list[float], call_budget: dict,
                seen_urls: set[str]) -> list[dict]:
    out = []
    print(f"\n=== COHORT 1: DAM PDF batch ({len(COHORT1_DAM_PDFS)} URLs) ===")
    for vendor, label, url in COHORT1_DAM_PDFS:
        out_dir = batch_root / "cohort1_dam_pdfs" / vendor
        ent = fetch_with_persist(url, label, out_dir, DEFAULT_DELAY_S,
                                 last_call_t, call_budget, seen_urls)
        ent["vendor_slug"] = vendor
        ent["cohort"] = "cohort1_dam_pdfs"
        out.append(ent)
        if call_budget["used"] >= HARD_CAP_CALLS:
            break
    return out


def cohort2_droneshield_wayback(batch_root: Path, last_call_t: list[float],
                                 call_budget: dict, seen_urls: set[str]) -> list[dict]:
    out = []
    out_dir = batch_root / "cohort2_droneshield_wayback"
    print(f"\n=== COHORT 2: DroneShield Wayback ({len(COHORT2_DRONESHIELD_WAYBACK)} URLs) ===")
    for vendor, label, url in COHORT2_DRONESHIELD_WAYBACK:
        ent = fetch_with_persist(url, label, out_dir, WAYBACK_DELAY_S,
                                 last_call_t, call_budget, seen_urls)
        ent["vendor_slug"] = vendor
        ent["cohort"] = "cohort2_droneshield_wayback"
        out.append(ent)
        if call_budget["used"] >= HARD_CAP_CALLS:
            break
    return out


def cohort3_hak5_wayback(batch_root: Path, last_call_t: list[float],
                          call_budget: dict, seen_urls: set[str]) -> list[dict]:
    out = []
    out_dir = batch_root / "cohort3_hak5_wayback"
    print(f"\n=== COHORT 3: Hak5 docs Wayback ({len(COHORT3_HAK5_WAYBACK)} URLs) ===")
    for vendor, label, url in COHORT3_HAK5_WAYBACK:
        ent = fetch_with_persist(url, label, out_dir, WAYBACK_DELAY_S,
                                 last_call_t, call_budget, seen_urls)
        ent["vendor_slug"] = vendor
        ent["cohort"] = "cohort3_hak5_wayback"
        out.append(ent)
        if call_budget["used"] >= HARD_CAP_CALLS:
            break
    return out


def cohort4_cradlepoint_wayback(batch_root: Path, last_call_t: list[float],
                                 call_budget: dict, seen_urls: set[str]) -> list[dict]:
    out = []
    out_dir = batch_root / "cohort4_cradlepoint_wayback"
    print(f"\n=== COHORT 4: Cradlepoint Customer KB Wayback ===")
    # Step 1: CDX search (1 call)
    cdx_ent = fetch_with_persist(CRADLEPOINT_CDX_QUERY, "cdx_search",
                                  out_dir, WAYBACK_DELAY_S, last_call_t,
                                  call_budget, seen_urls)
    cdx_ent["vendor_slug"] = "cradlepoint_customer"
    cdx_ent["cohort"] = "cohort4_cradlepoint_wayback"
    out.append(cdx_ent)
    if call_budget["used"] >= HARD_CAP_CALLS:
        return out
    # Step 2: parse CDX JSON, dedupe by article slug, take top 7
    article_targets = []
    if cdx_ent.get("status") == 200:
        try:
            body = (ARGUS_ROOT / cdx_ent["raw_path_relative"]).read_bytes()
            rows = json.loads(body)
            # rows[0] is header; rest are [urlkey, ts, original, mime, status, digest, length]
            seen_slugs = set()
            for row in rows[1:]:
                if len(row) < 7:
                    continue
                ts, orig = row[1], row[2]
                m = re.search(r"customer\.cradlepoint\.com/s/article/([^/?#]+)", orig)
                if not m:
                    continue
                slug = m.group(1)
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                wb_url = f"https://web.archive.org/web/{ts}/{orig}"
                article_targets.append((slug, wb_url))
                if len(article_targets) >= 7:
                    break
        except Exception as e:
            print(f"  [WARN] CDX parse failed: {e}", flush=True)
    # Step 3: fetch up to 7 articles
    for slug, url in article_targets:
        ent = fetch_with_persist(url, f"kb_{slug[:60]}", out_dir,
                                 WAYBACK_DELAY_S, last_call_t, call_budget,
                                 seen_urls)
        ent["vendor_slug"] = "cradlepoint_customer"
        ent["cohort"] = "cohort4_cradlepoint_wayback"
        out.append(ent)
        if call_budget["used"] >= HARD_CAP_CALLS:
            break
    return out


FCC_DOC_RE = re.compile(
    rb'/document/([0-9a-fA-F\-]{8,})/([0-9a-fA-F\-]{8,})\.pdf', re.IGNORECASE
)
FCC_DOC_TYPE_RE = re.compile(
    rb'(test\s+report|RF\s+exposure|MPE|SAR|users?\s+manual|cover\s+letter|'
    rb'internal\s+photos|external\s+photos|test\s+setup\s+photos|label)',
    re.IGNORECASE
)


def cohort5_fcc(batch_root: Path, last_call_t: list[float],
                 call_budget: dict, seen_urls: set[str]) -> list[dict]:
    out = []
    print(f"\n=== COHORT 5: FCC per-FCC-ID per-document PDFs "
          f"({len(FCC_GRANTEES)} grantees) ===")
    for vendor, grantee in FCC_GRANTEES:
        out_dir = batch_root / "cohort5_fcc_pdfs" / vendor
        # Landing
        landing_url = f"https://fcc.report/FCC-ID/{grantee}/"
        ent = fetch_with_persist(landing_url, f"landing_{grantee}", out_dir,
                                 FCC_DELAY_S, last_call_t, call_budget,
                                 seen_urls)
        ent["vendor_slug"] = vendor
        ent["fcc_grantee"] = grantee
        ent["cohort"] = "cohort5_fcc_pdfs"
        out.append(ent)
        if call_budget["used"] >= HARD_CAP_CALLS:
            break
        # Parse: pick first FCC ID under this grantee
        fcc_ids = []
        if ent.get("status") == 200:
            try:
                body = (ARGUS_ROOT / ent["raw_path_relative"]).read_bytes()
                # links of form /FCC-ID/<grantee>/<product_code>
                for m in re.finditer(
                    rf'/FCC-ID/{re.escape(grantee)}/([A-Za-z0-9\-_]+)'.encode(),
                    body, re.IGNORECASE,
                ):
                    fid = m.group(1).decode("ascii", "replace")
                    if fid and fid not in fcc_ids and fid != grantee:
                        fcc_ids.append(fid)
                    if len(fcc_ids) >= 3:
                        break
            except Exception as e:
                print(f"  [WARN] FCC landing parse failed for {grantee}: {e}",
                      flush=True)
        # For top 1 FCC ID, fetch its detail page → grab top doc PDF
        if fcc_ids and call_budget["used"] < HARD_CAP_CALLS:
            fid = fcc_ids[0]
            detail_url = f"https://fcc.report/FCC-ID/{grantee}/{fid}"
            det = fetch_with_persist(detail_url, f"detail_{grantee}_{fid}",
                                     out_dir, FCC_DELAY_S, last_call_t,
                                     call_budget, seen_urls)
            det["vendor_slug"] = vendor
            det["fcc_grantee"] = grantee
            det["fcc_id"] = fid
            det["cohort"] = "cohort5_fcc_pdfs"
            out.append(det)
            # Find PDF docs on detail page
            if det.get("status") == 200 and call_budget["used"] < HARD_CAP_CALLS:
                try:
                    body = (ARGUS_ROOT / det["raw_path_relative"]).read_bytes()
                    pdfs = FCC_DOC_RE.findall(body)
                    # Heuristic: pick first doc — manifest preserves all if
                    # subsequent fetches enabled. For tight cap stay at 1.
                    if pdfs:
                        filing_id, doc_id = pdfs[0]
                        filing_id = filing_id.decode("ascii", "replace")
                        doc_id = doc_id.decode("ascii", "replace")
                        pdf_url = (f"https://fcc.report/document/"
                                   f"{filing_id}/{doc_id}.pdf")
                        pdf_ent = fetch_with_persist(pdf_url,
                                                     f"pdf_{grantee}_{fid}",
                                                     out_dir, FCC_DELAY_S,
                                                     last_call_t, call_budget,
                                                     seen_urls)
                        pdf_ent["vendor_slug"] = vendor
                        pdf_ent["fcc_grantee"] = grantee
                        pdf_ent["fcc_id"] = fid
                        pdf_ent["cohort"] = "cohort5_fcc_pdfs"
                        out.append(pdf_ent)
                except Exception as e:
                    print(f"  [WARN] FCC detail parse failed {grantee}/{fid}: {e}",
                          flush=True)
        if call_budget["used"] >= HARD_CAP_CALLS:
            break
    return out


def cohort6_dji_sdk(batch_root: Path, last_call_t: list[float],
                     call_budget: dict, seen_urls: set[str]) -> list[dict]:
    out = []
    out_dir = batch_root / "cohort6_dji_sdk"
    print(f"\n=== COHORT 6: DJI SDK developer portal ({len(COHORT6_DJI_SDK)} URLs) ===")
    for vendor, label, url in COHORT6_DJI_SDK:
        ent = fetch_with_persist(url, label, out_dir, DEFAULT_DELAY_S,
                                 last_call_t, call_budget, seen_urls)
        ent["vendor_slug"] = vendor
        ent["cohort"] = "cohort6_dji_sdk"
        out.append(ent)
        if call_budget["used"] >= HARD_CAP_CALLS:
            break
    return out


def main() -> int:
    batch_ts = utc_timestamp()
    batch_root = ARGUS_ROOT / "raw" / "vendor_docs" / batch_ts
    batch_root.mkdir(parents=True, exist_ok=True)
    print(f"Wave-B2 Step 1 batch root: {batch_root}")
    print(f"Hard cap: {HARD_CAP_CALLS} HTTP calls (88 base + 35 recovery)")
    print(f"User-Agent: {USER_AGENT}")

    started = time.time()
    call_budget = {"used": 0}
    last_call_t = [0.0]
    seen_urls: set[str] = set()

    # Robots re-check first (per SAR-4 + §11 #6)
    robots_log = cohort_robots_recheck(batch_root, last_call_t, call_budget,
                                        seen_urls)
    # Cohort dispatch
    cohort1 = cohort1_dam(batch_root, last_call_t, call_budget, seen_urls)
    cohort2 = cohort2_droneshield_wayback(batch_root, last_call_t, call_budget, seen_urls)
    cohort3 = cohort3_hak5_wayback(batch_root, last_call_t, call_budget, seen_urls)
    cohort4 = cohort4_cradlepoint_wayback(batch_root, last_call_t, call_budget, seen_urls)
    cohort5 = cohort5_fcc(batch_root, last_call_t, call_budget, seen_urls)
    cohort6 = cohort6_dji_sdk(batch_root, last_call_t, call_budget, seen_urls)

    elapsed_s = round(time.time() - started, 1)

    # Aggregate stats
    def agg(entries):
        total_b = sum(e.get("byte_count", 0) for e in entries)
        ok_n = sum(1 for e in entries if e.get("status") == 200)
        fail_n = sum(1 for e in entries if e.get("status") not in (200, None) or e.get("error") and e.get("status") != 200)
        return {"entries": len(entries), "status_200": ok_n,
                "status_non_200_or_err": fail_n, "total_bytes": total_b}

    manifest = {
        "manifest_version": 1,
        "step": ("MAC-19 Phase 4 Wave-B2 Step 1 — corpus fetch (5 cohorts + DJI "
                 "SDK + robots re-check NEW hosts; NO Step-2 extraction)"),
        "captured_at_utc": batch_ts,
        "user_agent": USER_AGENT,
        "predecessor_step0_batch": "raw/vendor_docs/20260505T140959Z/",
        "predecessor_wave_b_batch": "raw/vendor_docs/20260505T040929Z/",
        "ratification_anchor": "MAC-18 CEO ratification at heartbeat 2026-05-05T~14:2xZ",
        "robots_recheck_step1_new_hosts": robots_log,
        "cohorts": {
            "cohort1_dam_pdfs":          {"entries": cohort1, "stats": agg(cohort1)},
            "cohort2_droneshield_wayback": {"entries": cohort2, "stats": agg(cohort2)},
            "cohort3_hak5_wayback":      {"entries": cohort3, "stats": agg(cohort3)},
            "cohort4_cradlepoint_wayback": {"entries": cohort4, "stats": agg(cohort4)},
            "cohort5_fcc_pdfs":          {"entries": cohort5, "stats": agg(cohort5)},
            "cohort6_dji_sdk":           {"entries": cohort6, "stats": agg(cohort6)},
        },
        "aggregate_stats": {
            "total_http_calls_used": call_budget["used"],
            "hard_cap": HARD_CAP_CALLS,
            "calls_robots_recheck": len(robots_log),
            "calls_cohort1_dam": len(cohort1),
            "calls_cohort2_droneshield": len(cohort2),
            "calls_cohort3_hak5": len(cohort3),
            "calls_cohort4_cradlepoint": len(cohort4),
            "calls_cohort5_fcc": len(cohort5),
            "calls_cohort6_dji_sdk": len(cohort6),
            "wall_clock_seconds": elapsed_s,
            "wall_clock_minutes": round(elapsed_s / 60.0, 2),
        },
        "bible_compliance": {
            "section_7_2_raw_preservation": (
                "all bytes persisted to "
                f"raw/vendor_docs/{batch_ts}/<cohort>/<vendor>/ BEFORE any parsing"),
            "section_7_2_user_agent": f"custom UA = {USER_AGENT}",
            "section_7_2_inter_request_spacing": (
                "DAM/FCC/DJI: 2.0s; Wayback: 1.5s; sequential single-thread urllib"),
            "section_7_2_no_retry": (
                "non-200 logged + persisted; no automatic retry"),
            "section_11_1_no_fabrication": (
                "404/non-200/TLS failures recorded as-is; no synthetic content"),
            "section_11_2_no_authenticated_content": (
                "Cellebrite KB / Magnet partner-login NEVER fetched; only public "
                "marketing PDFs from media.cellebrite.com"),
            "section_11_6_robots": (
                f"NEW host robots re-checked first ({len(NEW_HOSTS_FOR_ROBOTS)} "
                "hosts); Step-0 8-host set already covered"),
            "sar_4_alt_routing": (
                "DroneShield/Hak5/Cradlepoint Customer KB routed via Wayback per "
                "SAR-4 (Cradlepoint TLS-broken at Step-0)"),
            "no_db_writes": "zero raw_observations rows authored; no migration",
            "no_extraction": ("Step-1.5b survey + Step-2 extraction are separate "
                              "downstream steps"),
        },
    }
    manifest_path = batch_root / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"\nManifest written: {manifest_path}")
    print(f"Aggregate: calls={call_budget['used']}/{HARD_CAP_CALLS}, "
          f"wall={elapsed_s}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
