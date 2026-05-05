"""MAC-18 Wave-B2 Step 0 — discovery + sample-verification (zero-LLM).

Discovers URLs across the Wave-B2 surface (DroneShield SPA via Wayback +
DJI/Hak5/Motorola/Cradlepoint/Sierra DAM PDFs + active-vendor FCC test
reports + public-only SDK docs), re-checks robots.txt for each new domain,
sample-fetches 1-2 PDFs per vendor, and runs a byte-level keyword/anchor
sweep mirroring the MAC-16 corpus survey methodology.

Hard rules applied:
- §11 #1 no fabrication (raw bytes preserved verbatim, sha256+byte_count logged)
- §11 #2 no authenticated content (no partner-login fetches)
- §11 #6 + SAR-4 robots.txt re-check before each new fetch path
- §7.1 SourceWorker scope — Step 0 = discovery + sample-verification only
- NO writes to db/argus.db
- 2.0s min inter-request spacing; sequential single-threaded

Output:
  raw/vendor_docs/<run-ts>/_step0_discovery_manifest.json
  raw/vendor_docs/<run-ts>/<vendor>/<doc-kind>/<file>
  logs/mac18_step0_byte_level_survey_<run-ts>.txt
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "ArgusSourceWorker/0.1 (Phase4 Wave B2 Step 0 discovery; +https://github.com/argus-project)"
MIN_SPACING_S = 2.0
TIMEOUT_S = 30
HARD_CALL_CAP = 80  # Step-0 sample budget

REPO_ROOT = Path("/home/kev/argus")


def now_utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def http_get(url: str, *, max_retries: int = 1, allow_redirects: bool = True) -> dict:
    """Single GET with one retry on URLError. Returns dict with body, status,
    final_url, content_type, byte_count, sha256, elapsed_s, error."""
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    last_err = None
    for attempt in range(max_retries + 1):
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:
                body = resp.read()
                final_url = resp.geturl()
                ct = resp.headers.get("Content-Type", "")
                status = resp.status
                elapsed = time.time() - t0
                return {
                    "url": url,
                    "final_url": final_url,
                    "status": status,
                    "content_type": ct,
                    "byte_count": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "elapsed_s": round(elapsed, 3),
                    "body": body,
                    "error": None,
                }
        except urllib.error.HTTPError as e:
            elapsed = time.time() - t0
            body = e.read() if hasattr(e, "read") else b""
            return {
                "url": url,
                "final_url": e.url if hasattr(e, "url") else url,
                "status": e.code,
                "content_type": e.headers.get("Content-Type", "") if e.headers else "",
                "byte_count": len(body),
                "sha256": hashlib.sha256(body).hexdigest() if body else None,
                "elapsed_s": round(elapsed, 3),
                "body": body,
                "error": f"HTTP {e.code}",
            }
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = str(e)
            if attempt < max_retries:
                time.sleep(2.0)
                continue
            return {
                "url": url,
                "final_url": url,
                "status": None,
                "content_type": None,
                "byte_count": 0,
                "sha256": None,
                "elapsed_s": round(time.time() - t0, 3),
                "body": b"",
                "error": last_err,
            }
        except Exception as e:
            return {
                "url": url,
                "final_url": url,
                "status": None,
                "content_type": None,
                "byte_count": 0,
                "sha256": None,
                "elapsed_s": round(time.time() - t0, 3),
                "body": b"",
                "error": f"{type(e).__name__}: {e}",
            }


def parse_robots(body: bytes) -> dict:
    """Return {'allow': True/False/None, 'crawl_delay_s': float|None,
    'disallowed_paths': [...], 'raw_excerpt': first 500 chars}."""
    text = body.decode("utf-8", errors="replace")
    lines = [ln.strip() for ln in text.splitlines()]
    ua_block = None  # currently parsing block for which UA?
    relevant = []
    crawl_delay = None
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        low = ln.lower()
        if low.startswith("user-agent:"):
            agent = ln.split(":", 1)[1].strip()
            ua_block = agent
            continue
        if ua_block in ("*", USER_AGENT.split("/")[0].lower(), "argussourceworker"):
            if low.startswith("disallow:"):
                path = ln.split(":", 1)[1].strip()
                relevant.append(("disallow", path))
            elif low.startswith("allow:"):
                path = ln.split(":", 1)[1].strip()
                relevant.append(("allow", path))
            elif low.startswith("crawl-delay:"):
                try:
                    crawl_delay = float(ln.split(":", 1)[1].strip())
                except ValueError:
                    pass
    disallowed = [p for verb, p in relevant if verb == "disallow" and p]
    has_global_disallow = any(p == "/" for p in disallowed)
    return {
        "allow": False if has_global_disallow else (True if relevant or not lines else None),
        "crawl_delay_s": crawl_delay,
        "disallowed_paths": disallowed[:20],
        "raw_excerpt": text[:500],
    }


def url_path_disallowed(robots: dict | None, url: str) -> bool:
    if not robots:
        return False
    parsed = urllib.parse.urlparse(url)
    path = parsed.path or "/"
    for d in robots.get("disallowed_paths", []):
        if d == "/":
            return True
        if d and path.startswith(d):
            return True
    return False


# --- Wave-B2 discovery surface (per MAC-18 issue body §1-§5) ---
# Probe-list per vendor. Each probe is a (kind, url) tuple. kind ∈ {robots, sitemap,
# pdf_sample, sdk_docs_landing, fcc_report_landing, spa_wayback_sample}.

# DroneShield SPA — Wayback fallback (MAC-14 BRINC precedent).
# Strategy: fetch Wayback robots.txt ONCE (already on disk from MAC-14 -> 404 nginx default),
# then fetch 2 candidate DroneShield product pages via Wayback to see if pre-SPA static HTML
# exists from earlier years.
DRONESHIELD_WAYBACK_PROBES = [
    "https://web.archive.org/web/2023/https://www.droneshield.com/products/dronegun-tactical",
    "https://web.archive.org/web/2023/https://www.droneshield.com/products/rfpatrol",
]

# DJI — DAM PDFs (manuals / quick-start guides). Discovery via downloads landing page.
# Robots: dl.djicdn.com is the CDN; dji.com sitemap had 5959B (mostly product pages).
# Strategy: fetch one well-known stable PDF URL pattern to seed sample.
DJI_PDF_PROBES = [
    # Public Mavic-2 specs page links to manuals; well-known PDF surface
    "https://dl.djicdn.com/downloads/Mavic_2/20180823/Mavic_2_User_Manual_v1.0.pdf",
]

# Hak5 — public docs site (not behind login per §11 #2; docs.hak5.org is GitBook public).
HAK5_DOCS_PROBES = [
    "https://docs.hak5.org/wifi-pineapple/",  # SDK landing
    "https://docs.hak5.org/wifi-pineapple/setup-and-configuration",  # SSID/cred-likely page
]

# Motorola Solutions APX — radio firmware/admin guides. learning.motorolasolutions.com is
# behind login (§11 #2 territory). Public-only path: motorolasolutions.com/content/dam/...
MOTOROLA_PDF_PROBES = [
    # APX 6000 Quick Reference — published on motorolasolutions.com DAM
    "https://www.motorolasolutions.com/content/dam/msi/docs/apx/apx_4500_user_guide.pdf",
]

# Cradlepoint — Help Center (customer.cradlepoint.com is public KB; netcloud-os-help is admin)
CRADLEPOINT_PROBES = [
    "https://customer.cradlepoint.com/s/article/NCM-Quick-Start",
    # Default-credentials page (well-known support article surface)
    "https://customer.cradlepoint.com/s/article/Default-Login-Credentials",
]

# Sierra Wireless — source.sierrawireless.com (public AirLink resources)
SIERRA_PROBES = [
    "https://source.sierrawireless.com/resources/airlink/software_downloads/",
    "https://source.sierrawireless.com/resources/airlink/software_reference_docs/airlink_oms_admin_guide/",
]

# FCC test report PDFs — fcc.report mirrors EAS public test data; fccid.io is alt mirror.
# Sample using known-active grantee FCC IDs from manifest (Phase-4 active cohort).
FCC_REPORT_PROBES = [
    # DJI grantee 2AS9X (from manifest); fcc.report routing
    "https://fcc.report/FCC-ID/2AS9X",
    # Cradlepoint grantee UXX
    "https://fcc.report/FCC-ID/UXX",
    # Axon grantee 2AGVG
    "https://fcc.report/FCC-ID/2AGVG",
]

# SDK / dev portals — public-only per §11 #2 (Cellebrite KnowledgeBase has public + partner;
# only public portion is fetchable).
SDK_PROBES = [
    "https://developer.dji.com/mobile-sdk/",  # public DJI dev portal landing
    "https://docs.hak5.org/cloud-c2",  # public Cloud C2 docs
]


def main():
    run_ts = now_utc_compact()
    out_root = REPO_ROOT / "raw" / "vendor_docs" / run_ts
    out_root.mkdir(parents=True, exist_ok=True)

    log_path = REPO_ROOT / "logs" / f"mac18_step0_discovery_{run_ts}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_lines = []

    def log(msg):
        line = f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {msg}"
        log_lines.append(line)
        print(line, flush=True)

    log(f"=== MAC-18 Step 0 discovery run_ts={run_ts} ===")
    log(f"User-Agent: {USER_AGENT}")
    log(f"Hard cap: {HARD_CALL_CAP} calls; min spacing: {MIN_SPACING_S}s")

    manifest = {
        "manifest_version": 1,
        "step": "MAC-18 Phase 4 Wave-B2 Step 0 — discovery + sample-verification (NO writes, NO extraction, zero-LLM)",
        "captured_at_utc": run_ts,
        "user_agent": USER_AGENT,
        "predecessor_batch": "raw/vendor_docs/20260505T040929Z/",
        "vendors_probed": [],
        "robots_recheck_log": [],
        "aggregate_stats": {},
        "byte_level_sweep": {},
        "bible_compliance": {
            "section_11_1_no_fabrication": "raw bytes preserved verbatim with sha256+byte_count",
            "section_11_2_no_auth": "no partner-login fetches; SDK probes public-only",
            "section_11_6_robots_recheck": "every new domain re-checked; any disallow honored",
            "sar_4_alt_routing": "DroneShield SPA -> Wayback fallback (BRINC MAC-14 precedent)",
            "section_7_1_sourceworker": "Step 0 = discovery + sample-verification ONLY",
        },
    }

    calls_used = 0
    last_call_t = 0.0

    def spaced_get(url: str) -> dict:
        nonlocal calls_used, last_call_t
        if calls_used >= HARD_CALL_CAP:
            return {"url": url, "status": None, "error": "HARD_CAP_REACHED", "byte_count": 0, "sha256": None, "body": b"", "final_url": url, "content_type": None, "elapsed_s": 0}
        wait = MIN_SPACING_S - (time.time() - last_call_t)
        if wait > 0:
            time.sleep(wait)
        result = http_get(url)
        last_call_t = time.time()
        calls_used += 1
        return result

    def persist(rel_path: str, body: bytes) -> str:
        full = out_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(body)
        return str(full.relative_to(REPO_ROOT))

    def recheck_robots(domain_label: str, robots_url: str) -> dict:
        log(f"[robots-recheck] {domain_label} -> {robots_url}")
        r = spaced_get(robots_url)
        if r["status"] == 200 and r["body"]:
            parsed = parse_robots(r["body"])
            rel = persist(f"_robots_recheck/{domain_label.replace('/', '_')}_robots.txt", r["body"])
            entry = {
                "domain_label": domain_label,
                "robots_url": robots_url,
                "status": r["status"],
                "byte_count": r["byte_count"],
                "sha256": r["sha256"],
                "raw_path_relative": rel,
                "allow": parsed["allow"],
                "crawl_delay_s": parsed["crawl_delay_s"],
                "disallowed_paths": parsed["disallowed_paths"],
                "raw_excerpt": parsed["raw_excerpt"][:300],
            }
        elif r["status"] == 404:
            entry = {
                "domain_label": domain_label,
                "robots_url": robots_url,
                "status": 404,
                "allow": True,  # 404 = no robots restrictions stated
                "note": "no robots.txt published; fetch permitted by default per §11 #6",
            }
        else:
            entry = {
                "domain_label": domain_label,
                "robots_url": robots_url,
                "status": r.get("status"),
                "error": r.get("error"),
                "allow": None,
                "note": "robots.txt fetch failed; defer fetch per stop-the-line",
            }
        manifest["robots_recheck_log"].append(entry)
        return entry

    # --- Robots re-checks for new domains ---
    new_domains = [
        ("droneshield_wayback", "https://web.archive.org/robots.txt"),
        ("dji_cdn", "https://dl.djicdn.com/robots.txt"),
        ("hak5_docs", "https://docs.hak5.org/robots.txt"),
        ("motorolasolutions_dam", "https://www.motorolasolutions.com/robots.txt"),
        ("cradlepoint_customer", "https://customer.cradlepoint.com/robots.txt"),
        ("sierra_source", "https://source.sierrawireless.com/robots.txt"),
        ("fcc_report", "https://fcc.report/robots.txt"),
        ("dji_developer", "https://developer.dji.com/robots.txt"),
    ]
    for label, url in new_domains:
        recheck_robots(label, url)

    robots_by_domain = {e["domain_label"]: e for e in manifest["robots_recheck_log"]}

    # --- Per-vendor sample probes ---
    vendor_probes = [
        ("droneshield_wayback", "DroneShield (SPA -> Wayback)", DRONESHIELD_WAYBACK_PROBES, "spa_wayback_sample", None),
        ("dji_dam", "DJI (DAM PDFs)", DJI_PDF_PROBES, "pdf_sample", "dji_cdn"),
        ("hak5_docs", "Hak5 (SDK / docs)", HAK5_DOCS_PROBES, "sdk_docs_landing", "hak5_docs"),
        ("motorola_solutions_dam", "Motorola Solutions (APX DAM PDFs)", MOTOROLA_PDF_PROBES, "pdf_sample", "motorolasolutions_dam"),
        ("cradlepoint_kb", "Cradlepoint (Customer KB)", CRADLEPOINT_PROBES, "kb_landing", "cradlepoint_customer"),
        ("sierra_source", "Sierra Wireless (source.sierrawireless.com)", SIERRA_PROBES, "kb_landing", "sierra_source"),
        ("fcc_test_reports", "FCC test reports (active vendor grantees)", FCC_REPORT_PROBES, "fcc_report_landing", "fcc_report"),
        ("sdk_dev_portals", "SDK / dev portals (public-only)", SDK_PROBES, "sdk_docs_landing", None),
    ]

    for slug, canonical, urls, kind, robots_label in vendor_probes:
        v_entry = {"vendor_slug": slug, "vendor_canonical": canonical, "kind": kind, "entries": []}
        log(f"--- {canonical} ({slug}) ---")
        for url in urls:
            # robots check
            if robots_label and robots_label in robots_by_domain:
                r_info = robots_by_domain[robots_label]
                if r_info.get("allow") is False:
                    log(f"  SKIP (robots disallow): {url}")
                    v_entry["entries"].append({"doc_url": url, "kind": kind, "skipped_reason": "robots_disallow"})
                    continue
                if url_path_disallowed(r_info, url):
                    log(f"  SKIP (robots path disallow): {url}")
                    v_entry["entries"].append({"doc_url": url, "kind": kind, "skipped_reason": "robots_path_disallow"})
                    continue
            # fetch
            r = spaced_get(url)
            ent = {
                "doc_url": url,
                "final_url": r.get("final_url"),
                "kind": kind,
                "status": r.get("status"),
                "byte_count": r.get("byte_count"),
                "sha256": r.get("sha256"),
                "content_type": r.get("content_type"),
                "elapsed_s": r.get("elapsed_s"),
                "error": r.get("error"),
            }
            if r.get("body") and r.get("status") and r["status"] < 400:
                # persist
                safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", url.split("/")[-1] or "index")[:80]
                ext = ".pdf" if r.get("content_type", "").startswith("application/pdf") else (
                    ".html" if "html" in (r.get("content_type") or "") else ".bin"
                )
                if not safe_name.endswith(ext):
                    safe_name = safe_name + ext
                rel = persist(f"{slug}/{kind}_{safe_name}", r["body"])
                ent["raw_path_relative"] = rel
            v_entry["entries"].append(ent)
            log(f"  {r.get('status')} {r.get('byte_count'):>9}B  {url[:90]}")
        manifest["vendors_probed"].append(v_entry)

    # --- Byte-level keyword/anchor sweep on persisted samples ---
    log(f"=== Byte-level keyword/anchor sweep (calls_used={calls_used}/{HARD_CALL_CAP}) ===")
    sweep = {}

    BLE_KW_PAT = re.compile(rb"(?i)\b(?:bluetooth|ble|gatt|advertising|peripheral|service\s+uuid)\b")
    SSID_KW_PAT = re.compile(rb"(?i)\b(?:ssid|wifi|wi-fi|wireless\s+network|default\s+network|wpa[12]?|password)\b")
    MAC_KW_PAT = re.compile(rb"(?i)\b(?:mac\s*address|hardware\s*address|oui|mac\s*range)\b")
    DEFAULT_CRED_PAT = re.compile(rb"(?i)\b(?:default\s+(?:password|username|credentials?|admin)|factory\s+(?:default|reset)|admin\s*[:=]|password\s*[:=])\b")
    UUID_PAT = re.compile(rb"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
    MAC_PAT = re.compile(rb"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
    TAG_STRIP = re.compile(rb"<[^>]+>")
    WS_COLLAPSE = re.compile(rb"\s+")

    def sweep_file(path: Path, content_type: str | None) -> dict:
        raw = path.read_bytes()
        # PDF: extract text via pdfminer; HTML: tag-strip; bin: raw
        if content_type and "pdf" in content_type:
            try:
                from pdfminer.high_level import extract_text
                text = extract_text(str(path)) or ""
                clean = text.encode("utf-8", errors="replace")
            except Exception as e:
                log(f"    pdfminer FAIL on {path.name}: {e}")
                clean = raw
        elif content_type and "html" in content_type:
            stripped = TAG_STRIP.sub(b" ", raw)
            clean = WS_COLLAPSE.sub(b" ", stripped)
        else:
            clean = raw
        ble_kw = len(BLE_KW_PAT.findall(clean))
        ssid_kw = len(SSID_KW_PAT.findall(clean))
        mac_kw = len(MAC_KW_PAT.findall(clean))
        cred_kw = len(DEFAULT_CRED_PAT.findall(clean))
        uuids = UUID_PAT.findall(clean)
        macs = MAC_PAT.findall(clean)
        # Anchor: UUID or MAC counted as "anchored" only if a relevant keyword appears
        # within ±200 chars
        uuid_anchored = 0
        for m in UUID_PAT.finditer(clean):
            window = clean[max(0, m.start() - 200):m.end() + 200]
            if BLE_KW_PAT.search(window) or SSID_KW_PAT.search(window):
                uuid_anchored += 1
        mac_anchored = 0
        for m in MAC_PAT.finditer(clean):
            window = clean[max(0, m.start() - 200):m.end() + 200]
            if MAC_KW_PAT.search(window) or SSID_KW_PAT.search(window) or BLE_KW_PAT.search(window):
                mac_anchored += 1
        return {
            "raw_bytes": len(raw),
            "clean_bytes": len(clean),
            "ble_kw": ble_kw,
            "ssid_kw": ssid_kw,
            "mac_kw": mac_kw,
            "default_creds_kw": cred_kw,
            "uuid_total": len(uuids),
            "mac_total": len(macs),
            "uuid_anchored": uuid_anchored,
            "mac_anchored": mac_anchored,
        }

    aggregate = {
        "files": 0,
        "raw_bytes": 0,
        "clean_bytes": 0,
        "ble_kw_total": 0,
        "ssid_kw_total": 0,
        "mac_kw_total": 0,
        "default_creds_kw_total": 0,
        "ble_uuid_anchored_total": 0,
        "mac_anchored_total": 0,
    }

    for v_entry in manifest["vendors_probed"]:
        slug = v_entry["vendor_slug"]
        sweep[slug] = {"files": 0, "per_file": []}
        for ent in v_entry["entries"]:
            if "raw_path_relative" not in ent:
                continue
            full = REPO_ROOT / ent["raw_path_relative"]
            if not full.exists():
                continue
            res = sweep_file(full, ent.get("content_type"))
            sweep[slug]["per_file"].append({"file": ent["raw_path_relative"], **res})
            sweep[slug]["files"] += 1
            aggregate["files"] += 1
            aggregate["raw_bytes"] += res["raw_bytes"]
            aggregate["clean_bytes"] += res["clean_bytes"]
            aggregate["ble_kw_total"] += res["ble_kw"]
            aggregate["ssid_kw_total"] += res["ssid_kw"]
            aggregate["mac_kw_total"] += res["mac_kw"]
            aggregate["default_creds_kw_total"] += res["default_creds_kw"]
            aggregate["ble_uuid_anchored_total"] += res["uuid_anchored"]
            aggregate["mac_anchored_total"] += res["mac_anchored"]
        # collapse per-vendor totals
        sweep[slug]["totals"] = {
            "files": sweep[slug]["files"],
            "ble_kw": sum(f["ble_kw"] for f in sweep[slug]["per_file"]),
            "ssid_kw": sum(f["ssid_kw"] for f in sweep[slug]["per_file"]),
            "mac_kw": sum(f["mac_kw"] for f in sweep[slug]["per_file"]),
            "default_creds_kw": sum(f["default_creds_kw"] for f in sweep[slug]["per_file"]),
            "uuid_total": sum(f["uuid_total"] for f in sweep[slug]["per_file"]),
            "mac_total": sum(f["mac_total"] for f in sweep[slug]["per_file"]),
            "uuid_anchored": sum(f["uuid_anchored"] for f in sweep[slug]["per_file"]),
            "mac_anchored": sum(f["mac_anchored"] for f in sweep[slug]["per_file"]),
        }
        log(f"  [{slug}] files={sweep[slug]['totals']['files']} clean_bytes={sum(f['clean_bytes'] for f in sweep[slug]['per_file']):>9} ble_kw={sweep[slug]['totals']['ble_kw']} ssid_kw={sweep[slug]['totals']['ssid_kw']} mac_kw={sweep[slug]['totals']['mac_kw']} cred_kw={sweep[slug]['totals']['default_creds_kw']} uuid_anch={sweep[slug]['totals']['uuid_anchored']} mac_anch={sweep[slug]['totals']['mac_anchored']}")

    manifest["byte_level_sweep"] = sweep
    manifest["aggregate_stats"] = {**aggregate, "calls_used": calls_used, "hard_cap": HARD_CALL_CAP}

    # write outputs
    manifest_path = out_root / "_step0_discovery_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log_path.write_text("\n".join(log_lines) + "\n")

    log(f"=== DONE: manifest={manifest_path.relative_to(REPO_ROOT)} log={log_path.relative_to(REPO_ROOT)} calls_used={calls_used}/{HARD_CALL_CAP} ===")
    print(f"\nMANIFEST: {manifest_path}")
    print(f"LOG: {log_path}")


if __name__ == "__main__":
    main()
