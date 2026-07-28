"""MAC-523 Phase 1 — Shodan UPnP OUI harvest, oui-only, UPnP-module-only.

Per PHASE0_REPORT.md §9 recommendation: oui-only, UPnP-module-only.
Phase 1 budget: 40 query credits (89-12 = 77 remaining pre-work; per-issue cap is 40).
Each query = 100 results/page = 1 credit on the dev plan.
Total records accessible: 4000.

Reuses Phase 0's proven query patterns. Avoids the four HTTP-banner queries
that yielded 0/400 records. Targets camera/DVR/NVR/ALPR-bearing UPnP responses
to maximise yield per credit (Phase 0 measurement: 9 net-new OUIs from 500 records).

NEVER echo SHODAN_API_KEY. Reuses the redacting pattern from Phase 0 shodan_sample.py.
"""
import os, json, urllib.request, urllib.parse, urllib.error, pathlib, sys, time

SH = os.environ.get("SHODAN_API_KEY", "")
OUT = pathlib.Path("extraction_outputs/mac523_phase1/shodan_raw")
OUT.mkdir(parents=True, exist_ok=True)
LOG = pathlib.Path("extraction_outputs/mac523_phase1/run_log.md")

# Phase 1 query design — 40 credits, 40 distinct slices of camera/DVR/NVR/ALPR
# UPnP responses. Each query targets a specific product/manufacturer/module
# combination that Phase 0 proved contained surveillance-grade identifiers.
# Pacing: each query runs sequentially (avoids rate-limit surprises); 0.2s pause
# between queries is gentle.
QUERIES = [
    # A. Camera-ODM and IP-camera product filters (broad surveillance categories)
    ("A1_port1900_ipcam",          'port:1900 product:"IP Camera"'),
    ("A2_port1900_dvr",            'port:1900 product:"DVR"'),
    ("A3_port1900_nvr",            'port:1900 product:"NVR"'),
    ("A4_port1900_ptz",            'port:1900 product:"PTZ"'),
    ("A5_port1900_networkcam",     'port:1900 product:"Network Camera"'),
    # B. Major ODM/brand-anchored UPnP slices (avoid the four HTTP-banner queries
    #    that yielded 0/400 in Phase 0 — those are HTTP not UPnP)
    ("B1_port1900_hikvision",      'port:1900 hikvision'),
    ("B2_port1900_dahua",           'port:1900 dahua'),
    ("B3_port1900_axis",            'port:1900 axis'),
    ("B4_port1900_vivotek",         'port:1900 vivotek'),
    ("B5_port1900_uniview",         'port:1900 uniview'),
    ("B6_port1900_hanwha",          'port:1900 hanwha'),
    ("B7_port1900_bosch",           'port:1900 bosch'),
    ("B8_port1900_avigilon",        'port:1900 avigilon'),
    ("B9_port1900_pelco",           'port:1900 pelco'),
    ("B10_port1900_geovision",      'port:1900 geovision'),
    # C. Broader UPnP slices (Phase 0 proved these have yield)
    ("C1_port1900_has_screenshot_t", 'port:1900 has_screenshot:true'),
    ("C2_port1900_no_screenshot",  'port:1900 -has_screenshot'),
    ("C3_port1900_stunnel",        'port:1900 stunnel'),
    # D. Geographic slice (US — primary deployment scope per Bible §11 #2)
    ("D1_port1900_country_us",     'port:1900 country:"US"'),
    # E. Surveillance-class product strings broader than camera
    ("E1_port1900_alpr",           'port:1900 alpr'),
    ("E2_port1900_surveillance",   'port:1900 surveillance'),
    ("E3_port1900_dome",           'port:1900 dome'),
    ("E4_port1900_bullet",         'port:1900 bullet'),
    # F. UPnP-DSM and HTTP-presentation variants observed in Phase 0 modules
    ("F1_upnp_module",             'upnp'),
    ("F2_port1900_product_camera", 'port:1900 product:camera'),
    # G. Camera-firmware specific (Phase 0 found these in UPnP manufacturer fields)
    ("G1_port1900_xm",             'port:1900 xm'),
    ("G2_port1900_jovision",       'port:1900 jovision'),
    ("G3_port1900_ens",            'port:1900 ens'),
    ("G4_port1900_wansview",       'port:1900 wansview'),
    ("G5_port1900_sannce",         'port:1900 sannce'),
    ("G6_port1900_annke",          'port:1900 annke'),
    ("G7_port1900_zavio",          'port:1900 zavio'),
    ("G8_port1900_arecont",        'port:1900 arecont'),
    # H. DVR/NVR firmware strings (broader search to find more)
    ("H1_port1900_h264",           'port:1900 h264'),
    ("H2_port1900_h265",           'port:1900 h265'),
    ("H3_port1900_onvif",          'port:1900 onvif'),
    ("H4_port1900_rtsp",           'port:1900 rtsp'),
    # I. ALPR / ITS-specific slices
    ("I1_port1900_genetec",        'port:1900 genetec'),
    # J. High-priority user-interest vendors per MAC-1 advisory
    #     (Flock Safety = primary Argus coverage target; Verkada = major CCTV vendor)
    ("J1_port1900_flock",          'port:1900 flock'),
    ("J2_port1900_verkada",        'port:1900 verkada'),
]

# 40 queries × 100 results/page = 4000 records accessible.
assert len(QUERIES) == 40, f"Expected 40 queries for Phase 1 budget, got {len(QUERIES)}"


def search(q, page=1):
    url = "https://api.shodan.io/shodan/host/search?" + urllib.parse.urlencode(
        {"key": SH, "query": q, "page": page})
    req = urllib.request.Request(url, headers={"User-Agent": "argus-mac523-phase1/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace").replace(SH, "<REDACTED>")}
    except Exception as e:
        return -1, {"error": repr(e).replace(SH, "<REDACTED>") if SH else repr(e)}


def api_info():
    url = "https://api.shodan.io/api-info?" + urllib.parse.urlencode({"key": SH})
    req = urllib.request.Request(url, headers={"User-Agent": "argus-mac523-phase1/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"error": repr(e).replace(SH, "<REDACTED>") if SH else repr(e)}


def main():
    if not SH:
        sys.exit("FATAL: SHODAN_API_KEY not set in env. Aborting.")

    pre = api_info()
    pre_credits = pre.get("query_credits") if isinstance(pre, dict) else None
    print(f"[pre] query_credits={pre_credits}  plan={pre.get('plan') if isinstance(pre, dict) else '?'}")

    started = time.time()
    summary = {"pre_credits": pre_credits, "queries": []}
    credits_consumed = 0

    for i, (name, q) in enumerate(QUERIES, 1):
        st, body = search(q)
        n = len(body.get("matches", [])) if isinstance(body, dict) else 0
        total = body.get("total") if isinstance(body, dict) else None
        err = body.get("error") if isinstance(body, dict) else None
        summary["queries"].append({
            "name": name, "query": q, "http": st,
            "returned": n, "total": total, "error": err
        })
        if err is None:
            credits_consumed += 1
        (OUT / f"{name}.json").write_text(json.dumps(body, indent=1))
        print(f"[{i:2d}/40] {name:30s} HTTP {st}  returned={n:4d}  total={total}  {err or ''}"[:200])
        if err is None and st != 200:
            print(f"  WARN: non-200 HTTP status, will not credit this query against budget")
        if i >= 40:
            break
        time.sleep(0.25)  # gentle pacing

    post = api_info()
    post_credits = post.get("query_credits") if isinstance(post, dict) else None
    summary["post_credits"] = post_credits
    summary["credits_consumed_observed"] = (pre_credits or 0) - (post_credits or 0)
    summary["duration_s"] = round(time.time() - started, 1)
    (OUT / "_summary.json").write_text(json.dumps(summary, indent=1))

    print(f"\n[post] query_credits={post_credits}  observed_consumed={summary['credits_consumed_observed']}  duration={summary['duration_s']}s")


if __name__ == "__main__":
    main()
