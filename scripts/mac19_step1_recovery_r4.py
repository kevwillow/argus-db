"""MAC-19 Wave-B2 Step 1 — recovery R4 (FCC final attempt).

Tries fcc.report /company/ landings + per-FCC-ID drill-down for 5 priority
vendors. If company landings yield FCC IDs and per-ID pages yield /document/
PDFs, this proves the route. Otherwise, FCC cohort is absence-documented per
§11 #1 with empirical evidence.

Budget: ~10 calls.
"""
from __future__ import annotations
import json, re, time, hashlib, urllib.request, urllib.error, urllib.parse, ssl, sys
from pathlib import Path
import datetime as dt

ARGUS_ROOT = Path(__file__).resolve().parent.parent
BATCH_DIR = ARGUS_ROOT / "raw" / "vendor_docs" / "20260505T143454Z"
USER_AGENT = ("ArgusSourceWorker/0.1 (Phase4 Wave B2 Step 1 R4 FCC final; "
              "+https://github.com/argus-project)")
HARD_CAP = 120
DELAY_S = 2.5
TIMEOUT_S = 30.0


def http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                "Accept": "*/*"})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = resp.read()
            return {"status": resp.status, "final_url": resp.url,
                    "headers": dict(resp.headers), "body": body,
                    "elapsed_s": round(time.time() - started, 3),
                    "error": None}
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return {"status": e.code, "final_url": getattr(e, "url", url),
                "headers": dict(e.headers) if e.headers else {}, "body": body,
                "elapsed_s": round(time.time() - started, 3),
                "error": f"http_{e.code}"}
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
        elif "json" in c: ext = ".json"
    if ext and not name.endswith(ext):
        name = name + ext
    p = out_dir / re.sub(r"[^a-zA-Z0-9._-]+", "_", name)[:120]
    p.write_bytes(body)
    return (str(p.relative_to(ARGUS_ROOT)), len(body),
            hashlib.sha256(body).hexdigest())


def fetch(url: str, kind: str, out_dir: Path, last_t: list[float],
          budget: dict, base_used: int) -> dict:
    if budget["used"] + base_used >= HARD_CAP:
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
         "raw_path_relative": rel, "recovery_round": "R4"}
    if r["error"]: e["error"] = r["error"]
    print(f"  [+{budget['used']}] {kind[:25]:25s} {str(r['status']):>5s}  "
          f"{bc:>9d}B  {url[:90]}", flush=True)
    return e


# Per-FCC-ID drill-down candidates (any-grantee, known to exist from Step-0 evidence)
SEED_PROBES = [
    # Step-0 evidence: UXX-AA redirected to company page; try direct UXX-S1A415A
    ("cradlepoint_docs", "UXX",
     "https://fcc.report/FCC-ID/UXX-S1A415A/"),
    # Try 5 vendor /company/ landings (slug-guessed from common naming)
    ("motorola_solutions_apx", "YJJ",
     "https://fcc.report/company/Motorola-Solutions-Inc"),
    ("axon", "2AGVG",
     "https://fcc.report/company/Axon-Enterprise-Inc"),
    ("sierra_wireless", "TWV",
     "https://fcc.report/company/Sierra-Wireless-Inc"),
    ("getac", "QYL",
     "https://fcc.report/company/Getac"),
]


def main() -> int:
    manifest_path = BATCH_DIR / "_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    base_used = manifest["aggregate_stats"]["total_http_calls_used"]
    print(f"R4: starting from {base_used}/{HARD_CAP} calls used")

    new_entries = []
    budget = {"used": 0}
    last_t = [0.0]

    # R4a: Probes
    for vendor, grantee, url in SEED_PROBES:
        if budget["used"] + base_used >= HARD_CAP: break
        out_dir = BATCH_DIR / "cohort5_fcc_pdfs" / vendor
        kind = ("detail_UXX-S1A415A" if "FCC-ID" in url
                else f"company_{grantee}")
        e = fetch(url, kind, out_dir, last_t, budget, base_used)
        e["vendor_slug"] = vendor
        e["fcc_grantee"] = grantee
        e["cohort"] = "cohort5_fcc_pdfs"
        new_entries.append(e)

    # R4b: For UXX-S1A415A (if 200), look for /document/ PDFs and grab top
    pdf_pat = re.compile(rb'/document/([0-9a-fA-F\-]+)/([0-9a-fA-F\-]+)\.pdf',
                          re.IGNORECASE)
    for e in new_entries:
        if e.get("status") == 200 and "FCC-ID" in e["doc_url"] and "company" not in e["doc_url"]:
            try:
                body = (ARGUS_ROOT / e["raw_path_relative"]).read_bytes()
                # also look for any href containing .pdf
                href_pdfs = re.findall(rb'href=[\"\']([^\"\']+\.pdf[^\"\']*)',
                                        body, re.IGNORECASE)
                doc_pdfs = pdf_pat.findall(body)
                print(f"  detail page {e['fcc_grantee']}: "
                      f"href_pdfs={len(href_pdfs)} doc_pdfs={len(doc_pdfs)}")
                target = None
                if doc_pdfs:
                    f, d = doc_pdfs[0]
                    target = f"https://fcc.report/document/{f.decode()}/{d.decode()}.pdf"
                elif href_pdfs:
                    h = href_pdfs[0].decode("utf-8", "replace")
                    target = h if h.startswith("http") else f"https://fcc.report{h}"
                if target and budget["used"] + base_used < HARD_CAP:
                    out_dir = BATCH_DIR / "cohort5_fcc_pdfs" / e["vendor_slug"]
                    pdf_e = fetch(target, f"pdf_{e['fcc_grantee']}", out_dir,
                                  last_t, budget, base_used)
                    pdf_e["vendor_slug"] = e["vendor_slug"]
                    pdf_e["fcc_grantee"] = e["fcc_grantee"]
                    pdf_e["cohort"] = "cohort5_fcc_pdfs"
                    new_entries.append(pdf_e)
            except Exception as ex:
                print(f"  [WARN] parse {e['fcc_grantee']}: {ex}", flush=True)

    # R4c: For each /company/ landing (200), parse FCC IDs and drill 1
    for e in list(new_entries):
        if e.get("status") != 200 or "/company/" not in e["doc_url"]:
            continue
        try:
            body = (ARGUS_ROOT / e["raw_path_relative"]).read_bytes()
            grantee = e["fcc_grantee"]
            ids = re.findall(rf'/FCC-ID/({re.escape(grantee)}-[A-Za-z0-9_]+)/?'
                              .encode(), body)
            ids = list(dict.fromkeys(i.decode("ascii", "replace") for i in ids))
            print(f"  company {grantee}: parsed {len(ids)} FCC IDs; "
                  f"top: {ids[:3]}")
            if ids and budget["used"] + base_used < HARD_CAP:
                fid = ids[0]
                out_dir = BATCH_DIR / "cohort5_fcc_pdfs" / e["vendor_slug"]
                d_url = f"https://fcc.report/FCC-ID/{fid}/"
                d_e = fetch(d_url, f"detail_{fid}", out_dir, last_t, budget,
                            base_used)
                d_e["vendor_slug"] = e["vendor_slug"]
                d_e["fcc_grantee"] = grantee
                d_e["fcc_id"] = fid
                d_e["cohort"] = "cohort5_fcc_pdfs"
                new_entries.append(d_e)
        except Exception as ex:
            print(f"  [WARN] company parse {e.get('fcc_grantee')}: {ex}",
                  flush=True)

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
    manifest["recovery_dispatch"]["r4_fcc_final"] = {
        "captured_at_utc": dt.datetime.now(dt.timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"),
        "scope": "fcc.report /company/ landings + UXX-S1A415A drill-down",
        "calls_added": budget["used"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nR4 complete: {budget['used']} new calls "
          f"(total {base_used + budget['used']}/{HARD_CAP})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
