"""MAC-19 Wave-B2 Step 1 — recovery R5 (FCC PDF capture).

R4 proved the route: Cradlepoint UXX-S1A415A → fcc.report PDF works.
R5 captures PDFs for the FCC IDs already drilled (Cradlepoint additional,
Getac QYL-5127MODMIN) and re-parses Motorola/Axon/Sierra company pages
with wider regex to find additional FCC IDs and grab one PDF each.

Budget: ~10-15 calls.
"""
from __future__ import annotations
import json, re, time, hashlib, urllib.request, urllib.error, urllib.parse, sys
from pathlib import Path
import datetime as dt

ARGUS_ROOT = Path(__file__).resolve().parent.parent
BATCH_DIR = ARGUS_ROOT / "raw" / "vendor_docs" / "20260505T143454Z"
USER_AGENT = ("ArgusSourceWorker/0.1 (Phase4 Wave B2 Step 1 R5; "
              "+https://github.com/argus-project)")
HARD_CAP = 120
DELAY_S = 2.5


def http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            body = resp.read()
            return {"status": resp.status, "final_url": resp.url,
                    "headers": dict(resp.headers), "body": body,
                    "elapsed_s": round(time.time() - started, 3), "error": None}
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return {"status": e.code, "final_url": getattr(e, "url", url),
                "headers": dict(e.headers) if e.headers else {}, "body": body,
                "elapsed_s": round(time.time() - started, 3), "error": f"http_{e.code}"}
    except Exception as e:
        return {"status": None, "final_url": url, "headers": {}, "body": b"",
                "elapsed_s": round(time.time() - started, 3),
                "error": f"{type(e).__name__}: {e!s}"}


def persist(out_dir: Path, name: str, body: bytes, ct: str | None
            ) -> tuple[str, int, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = ""
    if ct:
        c = ct.lower()
        if "pdf" in c: ext = ".pdf"
        elif "html" in c: ext = ".html"
    if ext and not name.endswith(ext):
        name += ext
    p = out_dir / re.sub(r"[^a-zA-Z0-9._-]+", "_", name)[:140]
    p.write_bytes(body)
    return (str(p.relative_to(ARGUS_ROOT)), len(body),
            hashlib.sha256(body).hexdigest())


def fetch(url: str, kind: str, out_dir: Path, last_t: list[float], budget: dict, base: int) -> dict:
    if budget["used"] + base >= HARD_CAP:
        return {"kind": kind, "doc_url": url, "status": None,
                "error": "stopped_at_hard_cap"}
    w = DELAY_S - (time.time() - last_t[0])
    if w > 0: time.sleep(w)
    r = http_get(url)
    last_t[0] = time.time()
    budget["used"] += 1
    ct = (r["headers"] or {}).get("Content-Type")
    rel, bc, sha = persist(out_dir, kind, r["body"], ct)
    e = {"kind": kind, "doc_url": url, "final_url": r["final_url"],
         "status": r["status"], "byte_count": bc, "sha256": sha,
         "content_type": ct, "elapsed_s": r["elapsed_s"],
         "raw_path_relative": rel, "recovery_round": "R5"}
    if r["error"]: e["error"] = r["error"]
    print(f"  [+{budget['used']}] {kind[:30]:30s} {str(r['status']):>5s}  "
          f"{bc:>9d}B  {url[:90]}", flush=True)
    return e


# Companies whose pages are already fetched but whose grantees were not parsed
COMPANY_FILES = [
    ("motorola_solutions_apx", "YJJ",
     "raw/vendor_docs/20260505T143454Z/cohort5_fcc_pdfs/motorola_solutions_apx/company_YJJ.html"),
    ("axon", "2AGVG",
     "raw/vendor_docs/20260505T143454Z/cohort5_fcc_pdfs/axon/company_2AGVG.html"),
    ("sierra_wireless", "TWV",
     "raw/vendor_docs/20260505T143454Z/cohort5_fcc_pdfs/sierra_wireless/company_TWV.html"),
]


def main() -> int:
    manifest_path = BATCH_DIR / "_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    base_used = manifest["aggregate_stats"]["total_http_calls_used"]
    print(f"R5: starting from {base_used}/{HARD_CAP} calls used")

    new_entries = []
    budget = {"used": 0}
    last_t = [0.0]

    # Step 1: Capture PDF for Cradlepoint UXX-S1A415A — already have detail page,
    # already grabbed 1 PDF. Try grabbing 2 more to densify cohort coverage.
    cradle_detail = ARGUS_ROOT / "raw/vendor_docs/20260505T143454Z/cohort5_fcc_pdfs/cradlepoint_docs/detail_UXX-S1A415A_FCC-ID_UXX-S1A415A_.html"
    if cradle_detail.exists():
        body = cradle_detail.read_bytes()
        href_pdfs = re.findall(rb'href=[\"\']([^\"\']+\.pdf[^\"\']*)', body, re.IGNORECASE)
        # already grabbed 7170313.pdf — try 2nd
        seen = {b"7170313.pdf"}
        for h in href_pdfs:
            if any(s in h for s in seen):
                continue
            seen.add(h)
            url = h.decode("utf-8", "replace")
            if not url.startswith("http"):
                url = f"https://fcc.report{url}" if url.startswith("/") else f"https://fcc.report/{url}"
            out_dir = BATCH_DIR / "cohort5_fcc_pdfs" / "cradlepoint_docs"
            e = fetch(url, f"pdf2_UXX-S1A415A", out_dir, last_t, budget, base_used)
            e["vendor_slug"] = "cradlepoint_docs"
            e["fcc_grantee"] = "UXX"
            e["fcc_id"] = "UXX-S1A415A"
            e["cohort"] = "cohort5_fcc_pdfs"
            new_entries.append(e)
            break  # 1 more is enough

    # Step 2: Capture PDF for Getac QYL-5127MODMIN
    getac_detail = ARGUS_ROOT / "raw/vendor_docs/20260505T143454Z/cohort5_fcc_pdfs/getac/detail_QYL-5127MODMIN_FCC-ID_QYL-5127MODMIN_.html"
    if getac_detail.exists():
        body = getac_detail.read_bytes()
        href_pdfs = re.findall(rb'href=[\"\']([^\"\']+\.pdf[^\"\']*)', body, re.IGNORECASE)
        if href_pdfs:
            url = href_pdfs[0].decode("utf-8", "replace")
            if not url.startswith("http"):
                url = f"https://fcc.report{url}" if url.startswith("/") else f"https://fcc.report/{url}"
            out_dir = BATCH_DIR / "cohort5_fcc_pdfs" / "getac"
            e = fetch(url, "pdf_QYL-5127MODMIN", out_dir, last_t, budget, base_used)
            e["vendor_slug"] = "getac"
            e["fcc_grantee"] = "QYL"
            e["fcc_id"] = "QYL-5127MODMIN"
            e["cohort"] = "cohort5_fcc_pdfs"
            new_entries.append(e)
        else:
            print(f"  [Getac QYL-5127MODMIN] no PDF hrefs in detail page")

    # Step 3: Re-parse company pages with wider regex; drill 1 FCC ID per
    parsed_extra: dict[str, list[str]] = {}
    for vendor, grantee, relpath in COMPANY_FILES:
        p = ARGUS_ROOT / relpath
        if not p.exists():
            continue
        body = p.read_bytes()
        # Wider regex — any FCC ID on the company page (filter out bare grantee)
        all_ids = list(dict.fromkeys(
            i.decode() for i in re.findall(rb'/FCC-ID/([A-Z0-9][A-Za-z0-9\-_]{2,})/', body)))
        # Filter: must be at least 5 chars and not equal to the grantee code
        ids = [i for i in all_ids if i != grantee and len(i) >= 5][:3]
        parsed_extra[grantee] = ids
        print(f"  re-parse {grantee}: {len(all_ids)} total ids; top 3 picked: {ids}")

    # Step 4: Drill 1 FCC ID per vendor (Motorola, Axon, Sierra)
    for vendor, grantee, _ in COMPANY_FILES:
        ids = parsed_extra.get(grantee, [])
        if not ids or budget["used"] + base_used >= HARD_CAP:
            continue
        fid = ids[0]
        out_dir = BATCH_DIR / "cohort5_fcc_pdfs" / vendor
        d_url = f"https://fcc.report/FCC-ID/{fid}/"
        e = fetch(d_url, f"detail_{fid}", out_dir, last_t, budget, base_used)
        e["vendor_slug"] = vendor
        e["fcc_grantee"] = grantee
        e["fcc_id"] = fid
        e["cohort"] = "cohort5_fcc_pdfs"
        new_entries.append(e)
        # If detail succeeds and has PDF href, fetch it
        if e.get("status") == 200:
            try:
                body = (ARGUS_ROOT / e["raw_path_relative"]).read_bytes()
                href_pdfs = re.findall(rb'href=[\"\']([^\"\']+\.pdf[^\"\']*)', body, re.IGNORECASE)
                if href_pdfs and budget["used"] + base_used < HARD_CAP:
                    url = href_pdfs[0].decode("utf-8", "replace")
                    if not url.startswith("http"):
                        url = f"https://fcc.report{url}" if url.startswith("/") else f"https://fcc.report/{url}"
                    pdf_e = fetch(url, f"pdf_{fid}", out_dir, last_t, budget, base_used)
                    pdf_e["vendor_slug"] = vendor
                    pdf_e["fcc_grantee"] = grantee
                    pdf_e["fcc_id"] = fid
                    pdf_e["cohort"] = "cohort5_fcc_pdfs"
                    new_entries.append(pdf_e)
            except Exception as ex:
                print(f"  [WARN] {fid} parse: {ex}")

    # Persist
    manifest["cohorts"]["cohort5_fcc_pdfs"]["entries"].extend(new_entries)
    all_ents = manifest["cohorts"]["cohort5_fcc_pdfs"]["entries"]
    manifest["cohorts"]["cohort5_fcc_pdfs"]["stats"] = {
        "entries": len(all_ents),
        "status_200": sum(1 for x in all_ents if x.get("status") == 200),
        "status_non_200_or_err": sum(
            1 for x in all_ents if x.get("status") not in (200, None)
            or (x.get("error") and x.get("status") != 200)),
        "total_bytes": sum(x.get("byte_count", 0) for x in all_ents),
    }
    manifest["aggregate_stats"]["total_http_calls_used"] = base_used + budget["used"]
    manifest["aggregate_stats"]["recovery_calls_used"] = (
        manifest["aggregate_stats"].get("recovery_calls_used", 0) + budget["used"])
    manifest.setdefault("recovery_dispatch", {})
    manifest["recovery_dispatch"]["r5_fcc_pdf_capture"] = {
        "captured_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "scope": "FCC PDF capture from R4-discovered detail pages + wider company-page re-parse",
        "calls_added": budget["used"],
        "fcc_ids_re_parsed": parsed_extra,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nR5 complete: {budget['used']} new calls "
          f"(total {base_used + budget['used']}/{HARD_CAP})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
