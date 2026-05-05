"""MAC-18 Step 0 supplemental sample-fetch — high-yield PDF candidates from
Wave-B Step-1 sitemap mining.

Adds to existing run-batch raw/vendor_docs/20260505T140959Z/.
"""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "ArgusSourceWorker/0.1 (Phase4 Wave B2 Step 0 supplemental; +https://github.com/argus-project)"
MIN_SPACING_S = 2.0
TIMEOUT_S = 30
REPO_ROOT = Path("/home/kev/argus")
BATCH = "raw/vendor_docs/20260505T140959Z"
OUT_ROOT = REPO_ROOT / BATCH


def http_get(url: str) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:
            body = resp.read()
            return {"url": url, "final_url": resp.geturl(), "status": resp.status,
                    "content_type": resp.headers.get("Content-Type", ""),
                    "byte_count": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                    "elapsed_s": round(time.time() - t0, 3), "body": body, "error": None}
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return {"url": url, "final_url": getattr(e, "url", url), "status": e.code,
                "content_type": e.headers.get("Content-Type", "") if e.headers else "",
                "byte_count": len(body), "sha256": hashlib.sha256(body).hexdigest() if body else None,
                "elapsed_s": round(time.time() - t0, 3), "body": body, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"url": url, "final_url": url, "status": None, "content_type": None,
                "byte_count": 0, "sha256": None, "elapsed_s": round(time.time() - t0, 3),
                "body": b"", "error": f"{type(e).__name__}: {e}"}


def main():
    # 5 supplemental probes from Wave-B Step-1 sitemap mining
    probes = [
        ("getac", "pdf_sample", "https://www.getac.com/content/dam/getac/product-spec-data-pdf/us/Getac_B360_G3_US_Product.pdf"),
        ("sierra_wireless", "pdf_sample", "https://www.sierrawireless.com/wp-content/uploads/2024/02/ES-B-AirLink-Portfolio-Brochure-Feb2024-F.pdf"),
        ("motorola_solutions_apx", "pdf_sample", "https://www.motorolasolutions.com/content/dam/msi/docs/products/apx/apx-accessories/apx_accessories_catalog.pdf"),
        ("reveal_media", "pdf_sample", "https://reveal-media.imgix.net/PDFs/D-series-US-Datasheet.pdf"),
        # FCC.report per-filing PDF — try a known UXX (Cradlepoint) test report. Direct PDF URL pattern: /document/<filing>/<doc>
        # Fall back to landing-page extracted document IDs if needed.
        ("fcc_test_reports", "fcc_filing_pdf_sample", "https://fcc.report/FCC-ID/UXX/-AA"),
    ]

    log = []
    last_t = 0.0
    results = []
    for slug, kind, url in probes:
        wait = MIN_SPACING_S - (time.time() - last_t)
        if wait > 0:
            time.sleep(wait)
        r = http_get(url)
        last_t = time.time()
        ent = {"vendor_slug": slug, "kind": kind, "doc_url": url,
               "final_url": r.get("final_url"), "status": r.get("status"),
               "byte_count": r.get("byte_count"), "sha256": r.get("sha256"),
               "content_type": r.get("content_type"), "elapsed_s": r.get("elapsed_s"),
               "error": r.get("error")}
        if r.get("body") and r.get("status") and r["status"] < 400:
            safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", url.split("/")[-1] or "index")[:80]
            ext = ".pdf" if "pdf" in (r.get("content_type") or "") else ".html"
            if not safe.endswith(ext):
                safe += ext
            rel_dir = OUT_ROOT / slug
            rel_dir.mkdir(parents=True, exist_ok=True)
            full = rel_dir / f"{kind}_{safe}"
            full.write_bytes(r["body"])
            ent["raw_path_relative"] = str(full.relative_to(REPO_ROOT))
        results.append(ent)
        log.append(f"  {r.get('status')} {r.get('byte_count'):>9}B  {url[:90]}  ct={r.get('content_type')}")

    # Re-do byte-level sweep on all files in batch
    BLE_KW = re.compile(rb"(?i)\b(?:bluetooth|ble|gatt|advertising|peripheral|service\s+uuid)\b")
    SSID_KW = re.compile(rb"(?i)\b(?:ssid|wifi|wi-fi|wireless\s+network|default\s+network|wpa[12]?|password)\b")
    MAC_KW = re.compile(rb"(?i)\b(?:mac\s*address|hardware\s*address|oui|mac\s*range)\b")
    CRED_KW = re.compile(rb"(?i)\b(?:default\s+(?:password|username|credentials?|admin)|factory\s+(?:default|reset)|admin\s*[:=]|password\s*[:=])\b")
    UUID_PAT = re.compile(rb"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
    MAC_PAT = re.compile(rb"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
    TAG_STRIP = re.compile(rb"<[^>]+>")
    WS_COL = re.compile(rb"\s+")

    def sweep_path(p: Path, ct: str | None):
        raw = p.read_bytes()
        if ct and "pdf" in ct:
            try:
                from pdfminer.high_level import extract_text
                clean = (extract_text(str(p)) or "").encode("utf-8", "replace")
            except Exception as e:
                clean = raw
                log.append(f"    pdfminer FAIL on {p.name}: {e}")
        elif ct and "html" in ct:
            clean = WS_COL.sub(b" ", TAG_STRIP.sub(b" ", raw))
        else:
            clean = raw
        ble = len(BLE_KW.findall(clean))
        ssid = len(SSID_KW.findall(clean))
        mac = len(MAC_KW.findall(clean))
        cred = len(CRED_KW.findall(clean))
        uuids = list(UUID_PAT.finditer(clean))
        macs = list(MAC_PAT.finditer(clean))
        u_anch = sum(1 for m in uuids if BLE_KW.search(clean[max(0, m.start() - 200):m.end() + 200]) or SSID_KW.search(clean[max(0, m.start() - 200):m.end() + 200]))
        m_anch = sum(1 for m in macs if MAC_KW.search(clean[max(0, m.start() - 200):m.end() + 200]) or SSID_KW.search(clean[max(0, m.start() - 200):m.end() + 200]) or BLE_KW.search(clean[max(0, m.start() - 200):m.end() + 200]))
        return {"raw_bytes": len(raw), "clean_bytes": len(clean), "ble_kw": ble, "ssid_kw": ssid,
                "mac_kw": mac, "default_creds_kw": cred, "uuid_total": len(uuids), "mac_total": len(macs),
                "uuid_anchored": u_anch, "mac_anchored": m_anch}

    sweep_results = []
    for ent in results:
        if "raw_path_relative" not in ent:
            continue
        full = REPO_ROOT / ent["raw_path_relative"]
        s = sweep_path(full, ent.get("content_type"))
        sweep_results.append({"vendor_slug": ent["vendor_slug"], "file": ent["raw_path_relative"], **s})
        log.append(f"  [SWEEP] {ent['vendor_slug']:20s} clean={s['clean_bytes']:>8}B ble={s['ble_kw']} ssid={s['ssid_kw']} mac={s['mac_kw']} cred={s['default_creds_kw']} uuid={s['uuid_total']}({s['uuid_anchored']}anch) mac={s['mac_total']}({s['mac_anchored']}anch)")

    # Append to manifest
    manifest_path = OUT_ROOT / "_step0_discovery_manifest.json"
    m = json.loads(manifest_path.read_text())
    m["supplemental_probes"] = results
    m["supplemental_sweep"] = sweep_results
    # Update aggregate with supplemental
    agg = m["aggregate_stats"]
    for s in sweep_results:
        agg["files"] += 1
        agg["raw_bytes"] += s["raw_bytes"]
        agg["clean_bytes"] += s["clean_bytes"]
        agg["ble_kw_total"] += s["ble_kw"]
        agg["ssid_kw_total"] += s["ssid_kw"]
        agg["mac_kw_total"] += s["mac_kw"]
        agg["default_creds_kw_total"] += s["default_creds_kw"]
        agg["ble_uuid_anchored_total"] += s["uuid_anchored"]
        agg["mac_anchored_total"] += s["mac_anchored"]
    agg["calls_used"] += len(probes)
    manifest_path.write_text(json.dumps(m, indent=2))

    print("\n".join(log))
    print(f"\n=== Aggregate (post-supplemental) ===")
    print(json.dumps(agg, indent=2))


if __name__ == "__main__":
    main()
