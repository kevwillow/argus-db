"""MAC-19 Wave-B2 Step 1 — recovery dispatch.

Adds to existing batch raw/vendor_docs/20260505T143454Z/.

Recovery scope (within 35-call recovery reserve):
  R1. Wayback retry (12 URLs) with 5s spacing — DroneShield (2 None) + Hak5 (10 None) + Cradlepoint CDX (1 None)
  R2. Apps.fcc.gov EAS GenericSearch alt-route (~5 grantees)
  R3. FCC detail-pages for product codes parsed from GenericSearch HTML (~5)

Total recovery target: ~23 calls (well within 48 remaining; total cap 120).
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
BATCH_DIR = ARGUS_ROOT / "raw" / "vendor_docs" / "20260505T143454Z"

USER_AGENT = ("ArgusSourceWorker/0.1 (Phase4 Wave B2 Step 1 recovery; "
              "+https://github.com/argus-project)")
HARD_CAP_CALLS = 120
TIMEOUT_S = 45.0
WAYBACK_RECOVERY_DELAY_S = 6.0  # was 1.5s — clearly hit rate limit
FCC_DELAY_S = 2.0


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def http_get(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*",
                 "Accept-Language": "en-US,en;q=0.9"},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
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
    except Exception as e:
        return {"status": None, "final_url": url, "headers": {}, "body": b"",
                "elapsed_s": round(time.time() - started, 3),
                "error": f"{type(e).__name__}: {e!s}"}


def safe_filename(url: str, kind: str) -> str:
    parsed = urllib.parse.urlparse(url)
    seg = parsed.path.strip("/").replace("/", "_") or "root"
    seg = re.sub(r"[^a-zA-Z0-9._-]+", "_", seg)
    return f"{kind}__{seg[:100]}"


def persist(out_dir: Path, fname: str, body: bytes,
            content_type: str | None) -> tuple[str, int, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
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
    return (str(fpath.relative_to(ARGUS_ROOT)), len(body),
            hashlib.sha256(body).hexdigest())


def fetch_persist(url: str, kind: str, out_dir: Path, delay_s: float,
                  last_call_t: list[float], call_budget: dict,
                  current_total_used: int) -> dict:
    if call_budget["used"] + current_total_used >= HARD_CAP_CALLS:
        return {"kind": kind, "doc_url": url, "status": None, "byte_count": 0,
                "sha256": None,
                "error": f"stopped_at_hard_cap_{HARD_CAP_CALLS}"}
    wait = delay_s - (time.time() - last_call_t[0])
    if wait > 0:
        time.sleep(wait)
    res = http_get(url)
    last_call_t[0] = time.time()
    call_budget["used"] += 1
    ct = (res["headers"] or {}).get("Content-Type")
    rel_path, byte_count, sha = persist(out_dir, safe_filename(url, kind),
                                         res["body"], ct)
    ent = {"ordinal": current_total_used + call_budget["used"], "kind": kind,
           "doc_url": url, "final_url": res["final_url"],
           "status": res["status"], "byte_count": byte_count, "sha256": sha,
           "content_type": ct, "elapsed_s": res["elapsed_s"],
           "raw_path_relative": rel_path}
    if res["error"]:
        ent["error"] = res["error"]
    print(f"  [+{call_budget['used']:2d}] {kind[:18]:18s} "
          f"{str(res['status']):>5s}  {byte_count:>9d}B  "
          f"{sha[:16]}  {url[:90]}", flush=True)
    return ent


# Wayback retry list — pulled from initial run's failures
WAYBACK_RETRY = [
    ("cohort2_droneshield_wayback", "droneshield_wayback", "product_rfone-mkii",
     "https://web.archive.org/web/2024/https://www.droneshield.com/products/rfone-mkii"),
    ("cohort2_droneshield_wayback", "droneshield_wayback", "product_dronenode",
     "https://web.archive.org/web/2024/https://www.droneshield.com/products/dronenode"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_wifi_pineapple",
     "https://web.archive.org/web/2024/https://docs.hak5.org/wifi-pineapple"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_bash_bunny",
     "https://web.archive.org/web/2024/https://docs.hak5.org/bash-bunny"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_usb_rubber_ducky",
     "https://web.archive.org/web/2024/https://docs.hak5.org/usb-rubber-ducky"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_cloud_c2",
     "https://web.archive.org/web/2024/https://docs.hak5.org/cloud-c2"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_lan_turtle",
     "https://web.archive.org/web/2024/https://docs.hak5.org/lan-turtle"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_packet_squirrel",
     "https://web.archive.org/web/2024/https://docs.hak5.org/packet-squirrel"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_key_croc",
     "https://web.archive.org/web/2024/https://docs.hak5.org/key-croc"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_shark_jack",
     "https://web.archive.org/web/2024/https://docs.hak5.org/shark-jack"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_screen_crab",
     "https://web.archive.org/web/2024/https://docs.hak5.org/screen-crab"),
    ("cohort3_hak5_wayback", "hak5_docs_wayback", "product_omg_cable",
     "https://web.archive.org/web/2024/https://docs.hak5.org/omg-cable"),
    ("cohort4_cradlepoint_wayback", "cradlepoint_customer", "cdx_search",
     "https://web.archive.org/cdx/search/cdx?url=customer.cradlepoint.com/s/article*"
     "&matchType=prefix&limit=200&filter=statuscode:200&output=json&collapse=urlkey"),
]

# FCC EAS GenericSearch alt-route — apps.fcc.gov (5 high-priority grantees)
FCC_GENERIC_SEARCH = [
    ("motorola_solutions_apx", "YJJ"),
    ("sierra_wireless",        "TWV"),
    ("axon",                   "2AGVG"),
    ("getac",                  "QYL"),
    ("cradlepoint_docs",       "UXX"),
]


def main() -> int:
    if not BATCH_DIR.exists():
        print(f"FATAL: batch dir missing: {BATCH_DIR}")
        return 1

    # Read original manifest, count current calls used
    manifest_path = BATCH_DIR / "_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    current_used = manifest["aggregate_stats"]["total_http_calls_used"]
    print(f"Recovery: starting from {current_used}/{HARD_CAP_CALLS} calls used")

    if current_used >= HARD_CAP_CALLS:
        print("Already at cap; aborting.")
        return 1

    started = time.time()
    call_budget = {"used": 0}
    last_call_t = [0.0]
    new_entries_by_cohort: dict[str, list[dict]] = {}

    # ---------- R1: Wayback retry ----------
    print(f"\n=== R1: Wayback retry ({len(WAYBACK_RETRY)} URLs, "
          f"{WAYBACK_RECOVERY_DELAY_S}s spacing) ===")
    for cohort_key, vendor, label, url in WAYBACK_RETRY:
        sub = "cohort2_droneshield_wayback" if cohort_key.startswith("cohort2") \
              else ("cohort3_hak5_wayback" if cohort_key.startswith("cohort3")
                    else "cohort4_cradlepoint_wayback")
        out_dir = BATCH_DIR / sub
        ent = fetch_persist(url, label, out_dir, WAYBACK_RECOVERY_DELAY_S,
                            last_call_t, call_budget, current_used)
        ent["vendor_slug"] = vendor
        ent["cohort"] = cohort_key
        ent["recovery_round"] = "R1"
        new_entries_by_cohort.setdefault(cohort_key, []).append(ent)
        if call_budget["used"] + current_used >= HARD_CAP_CALLS:
            break

    # ---------- R1b: If Cradlepoint CDX recovered, fetch up to 7 articles ----------
    cdx_ent = None
    for e in new_entries_by_cohort.get("cohort4_cradlepoint_wayback", []):
        if e.get("kind") == "cdx_search" and e.get("status") == 200:
            cdx_ent = e
            break
    if cdx_ent:
        print(f"\n=== R1b: Cradlepoint KB articles ===")
        try:
            body = (ARGUS_ROOT / cdx_ent["raw_path_relative"]).read_bytes()
            rows = json.loads(body)
            seen = set()
            targets = []
            for row in rows[1:] if rows else []:
                if len(row) < 7:
                    continue
                ts, orig = row[1], row[2]
                m = re.search(r"customer\.cradlepoint\.com/s/article/([^/?#]+)", orig)
                if not m:
                    continue
                slug = m.group(1)
                if slug in seen:
                    continue
                seen.add(slug)
                targets.append((slug, f"https://web.archive.org/web/{ts}/{orig}"))
                if len(targets) >= 7:
                    break
            for slug, url in targets:
                if call_budget["used"] + current_used >= HARD_CAP_CALLS:
                    break
                ent = fetch_persist(url, f"kb_{slug[:60]}",
                                    BATCH_DIR / "cohort4_cradlepoint_wayback",
                                    WAYBACK_RECOVERY_DELAY_S, last_call_t,
                                    call_budget, current_used)
                ent["vendor_slug"] = "cradlepoint_customer"
                ent["cohort"] = "cohort4_cradlepoint_wayback"
                ent["recovery_round"] = "R1b"
                new_entries_by_cohort["cohort4_cradlepoint_wayback"].append(ent)
        except Exception as e:
            print(f"  [WARN] CDX parse: {e}", flush=True)

    # ---------- R2: Apps.fcc.gov EAS GenericSearch ----------
    print(f"\n=== R2: apps.fcc.gov EAS GenericSearch ({len(FCC_GENERIC_SEARCH)} grantees) ===")
    fcc_ids_by_grantee = {}
    for vendor, grantee in FCC_GENERIC_SEARCH:
        if call_budget["used"] + current_used >= HARD_CAP_CALLS:
            break
        url = ("https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm"
               f"?application_purpose=&grantee_code={grantee}&product_code="
               "&applicant_name=&grant_date_from=&grant_date_to=&comments=")
        out_dir = BATCH_DIR / "cohort5_fcc_pdfs" / vendor
        ent = fetch_persist(url, f"eas_search_{grantee}", out_dir,
                            FCC_DELAY_S, last_call_t, call_budget, current_used)
        ent["vendor_slug"] = vendor
        ent["fcc_grantee"] = grantee
        ent["cohort"] = "cohort5_fcc_pdfs"
        ent["recovery_round"] = "R2"
        new_entries_by_cohort.setdefault("cohort5_fcc_pdfs", []).append(ent)
        # Parse FCC IDs (rows in EAS results — ID format: <grantee><product_code>)
        if ent.get("status") == 200:
            try:
                body = (ARGUS_ROOT / ent["raw_path_relative"]).read_bytes()
                pat = re.compile(rf'\b{re.escape(grantee)}[A-Z0-9_\-]+\b'.encode(),
                                 re.IGNORECASE)
                ids = list(dict.fromkeys(m.group(0).decode("ascii", "replace")
                                         for m in pat.finditer(body)))
                # Filter to those that aren't just the grantee code itself
                ids = [i for i in ids if i != grantee and len(i) > len(grantee)]
                fcc_ids_by_grantee[(vendor, grantee)] = ids[:3]
                print(f"    [{grantee}] parsed {len(ids)} FCC IDs; top: {ids[:3]}")
            except Exception as e:
                print(f"  [WARN] EAS parse {grantee}: {e}", flush=True)

    # ---------- R3: FCC detail page per grantee (top 1 product code) ----------
    print(f"\n=== R3: FCC detail page per grantee (top product code) ===")
    for (vendor, grantee), ids in fcc_ids_by_grantee.items():
        if not ids or call_budget["used"] + current_used >= HARD_CAP_CALLS:
            continue
        fid = ids[0]
        # fcc.report uses /FCC-ID/<grantee>-<product> format per Step-0 evidence
        # (UXX-AA pattern). Try the exact ID found in EAS first.
        url = f"https://fcc.report/FCC-ID/{fid}/"
        out_dir = BATCH_DIR / "cohort5_fcc_pdfs" / vendor
        ent = fetch_persist(url, f"detail_{fid}", out_dir, FCC_DELAY_S,
                            last_call_t, call_budget, current_used)
        ent["vendor_slug"] = vendor
        ent["fcc_grantee"] = grantee
        ent["fcc_id"] = fid
        ent["cohort"] = "cohort5_fcc_pdfs"
        ent["recovery_round"] = "R3"
        new_entries_by_cohort["cohort5_fcc_pdfs"].append(ent)
        # Parse PDF doc URLs from detail page
        if ent.get("status") == 200:
            try:
                body = (ARGUS_ROOT / ent["raw_path_relative"]).read_bytes()
                pdf_pat = re.compile(rb'/document/([0-9a-fA-F\-]+)/([0-9a-fA-F\-]+)\.pdf',
                                      re.IGNORECASE)
                matches = pdf_pat.findall(body)
                if matches and call_budget["used"] + current_used < HARD_CAP_CALLS:
                    filing, doc = matches[0]
                    pdf_url = (f"https://fcc.report/document/"
                               f"{filing.decode()}/{doc.decode()}.pdf")
                    pdf_ent = fetch_persist(pdf_url, f"pdf_{fid}", out_dir,
                                            FCC_DELAY_S, last_call_t,
                                            call_budget, current_used)
                    pdf_ent["vendor_slug"] = vendor
                    pdf_ent["fcc_grantee"] = grantee
                    pdf_ent["fcc_id"] = fid
                    pdf_ent["cohort"] = "cohort5_fcc_pdfs"
                    pdf_ent["recovery_round"] = "R3-pdf"
                    new_entries_by_cohort["cohort5_fcc_pdfs"].append(pdf_ent)
                else:
                    print(f"    [{fid}] no PDF docs found in detail page",
                          flush=True)
            except Exception as e:
                print(f"  [WARN] detail parse {fid}: {e}", flush=True)

    # ---------- Persist updated manifest ----------
    elapsed_s = round(time.time() - started, 1)
    # Append new entries to existing cohort entry lists
    for cohort_key, entries in new_entries_by_cohort.items():
        manifest["cohorts"][cohort_key]["entries"].extend(entries)
        # Recompute stats
        all_ents = manifest["cohorts"][cohort_key]["entries"]
        manifest["cohorts"][cohort_key]["stats"] = {
            "entries": len(all_ents),
            "status_200": sum(1 for e in all_ents if e.get("status") == 200),
            "status_non_200_or_err": sum(
                1 for e in all_ents if e.get("status") not in (200, None)
                or (e.get("error") and e.get("status") != 200)),
            "total_bytes": sum(e.get("byte_count", 0) for e in all_ents),
        }
    new_total = current_used + call_budget["used"]
    manifest["aggregate_stats"]["total_http_calls_used"] = new_total
    manifest["aggregate_stats"]["recovery_calls_used"] = call_budget["used"]
    manifest["aggregate_stats"]["recovery_wall_clock_s"] = elapsed_s
    manifest["recovery_dispatch"] = {
        "captured_at_utc": utc_timestamp(),
        "rounds": ["R1 Wayback retry (6s spacing)", "R1b CDX-discovered Cradlepoint articles",
                   "R2 apps.fcc.gov EAS GenericSearch alt-route",
                   "R3 fcc.report detail per grantee + top PDF"],
        "recovery_calls_added": call_budget["used"],
        "fcc_ids_parsed": {f"{v}/{g}": ids for (v, g), ids in fcc_ids_by_grantee.items()},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nRecovery complete: {call_budget['used']} new calls "
          f"(total {new_total}/{HARD_CAP_CALLS}). Wall-clock: {elapsed_s}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
