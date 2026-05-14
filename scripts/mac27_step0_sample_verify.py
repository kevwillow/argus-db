"""MAC-27 Step-0 sample-verification — fetch 5 candidate papers + zero-LLM
byte-level regex/keyword sweep. Project Wave-C yield surface honestly.

Per Step-0 binding template: NO writes to db/argus.db, NO LLM calls.
Methodology mirrors MAC-23 Step-1.5b survey shape.

Targets chosen for representativeness across §2.1 device classes:
  1. USENIX Sec 2024 — Eye of Sauron (spy camera EM detection)
  2. USENIX Sec 2024 — Diffie-Hellman Picture Show (VoWiFi commercial)
  3. USENIX Sec 2024 — Logic Gone Astray (5G baseband; cellular)
  4. NDSS 2024 — first DJI-mentioning paper found in the catalog HTML
  5. arXiv abs: 2504.20007 (AI-driven policing; from S2 successful hit)

Byte-level regex/keyword anchors (replicates MAC-23 / MAC-25 Step-1.5b shape;
FCC-ID regex is the TIGHTENED hyphen-mandatory variant per MAC-21 §9.11):
  - mac_anchored      \\b[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}\\b
  - ble_uuid_anchored \\b[0-9A-Fa-f]{8}-([0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\\b
  - fcc_id_anchored   \\b[A-Z0-9]{3}-[A-Z0-9]{1,14}\\b  (mandatory hyphen)
  - ssid_kw           case-insensitive \\bssid\\b literal token
  - default_creds_kw  password / login / credential / passphrase tokens
  - vendor_proximity  vendor occurrence within ±50 chars of any anchor

Output:
  raw/academic/<run-ts>/_step0_sample/<source>__<paper>/<file>
  raw/academic/<run-ts>/_step0_sample/_byte_level_survey.json
  raw/academic/<run-ts>/_step0_sample/_byte_level_survey.txt
  logs/mac27_step0_sample_verify_<run-ts>.log
"""
from __future__ import annotations
import hashlib, json, re, ssl, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from pdfminer.high_level import extract_text

UA = "ArgusSourceWorker/0.1 (Phase4 Wave-C Step 0 sample verify; +https://github.com/argus-project)"
TIMEOUT_S = 60
ARXIV_SPACING_S = 15.0
USENIX_SPACING_S = 10.0
NDSS_SPACING_S = 2.0

REPO_ROOT = Path(__file__).resolve().parents[1]
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
DISCOVERY_RUN = "20260506T012828Z"
OUT = REPO_ROOT / "raw" / "academic" / DISCOVERY_RUN / "_step0_sample"
OUT.mkdir(parents=True, exist_ok=True)
LOG = REPO_ROOT / "logs" / f"mac27_step0_sample_verify_{TS}.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

VENDORS = [
    "Avigilon", "Axis Communications", "Axon", "Berla", "BRINC", "BriefCam",
    "Cellebrite", "Clearview AI", "Cradlepoint", "Dedrone",
    "Digital Receiver Technology", "DJI", "DroneShield", "Engility",
    "Flock Safety", "Genetec", "Getac", "Hak5", "Harris", "Jacobs", "Kenwood",
    "KeyW", "L3Harris", "Magnet Forensics", "Motorola Solutions", "Parrot",
    "Rekor", "Reveal", "Septier", "Sierra Wireless", "Skydio", "SoundThinking",
    "Vigilant Solutions", "WatchGuard",
]

# Byte-level anchors. Hex literals, plus mandatory-hyphen FCC ID.
RE_MAC = re.compile(rb"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b")
RE_BLE_UUID = re.compile(rb"\b[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\b")
RE_FCC_ID = re.compile(rb"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{1,14}\b")
RE_SSID_KW = re.compile(rb"\bssid\b", re.IGNORECASE)
RE_CREDS = re.compile(rb"\b(?:default\s+)?(?:password|passphrase|credential|login|admin)\b", re.IGNORECASE)

logfh = open(LOG, "a", encoding="utf-8")


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
    print(line, flush=True)
    logfh.write(line + "\n")
    logfh.flush()


def http_get(url: str) -> tuple[int, bytes, dict, float]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:
            body = resp.read()
            return resp.status, body, dict(resp.headers), round(time.monotonic() - t0, 3)
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return e.code, body, dict(e.headers or {}), round(time.monotonic() - t0, 3)
    except urllib.error.URLError as e:
        return 0, b"", {"_url_error": str(e.reason)}, round(time.monotonic() - t0, 3)


def vendor_proximity(text_bytes: bytes, anchor_offset: int, window: int = 50) -> list[str]:
    """Return vendor names appearing within ±window bytes of anchor_offset."""
    lo = max(0, anchor_offset - window)
    hi = min(len(text_bytes), anchor_offset + window)
    chunk = text_bytes[lo:hi].lower()
    hits = []
    for v in VENDORS:
        if v.lower().encode("utf-8") in chunk:
            hits.append(v)
    return hits


def survey_text(text_bytes: bytes, label: str) -> dict:
    """Run the 5 byte-level anchors + vendor-proximity gating."""
    out: dict = {"label": label, "byte_count": len(text_bytes)}
    # Anchored counts
    mac_hits = list(RE_MAC.finditer(text_bytes))
    ble_hits = list(RE_BLE_UUID.finditer(text_bytes))
    fcc_hits = list(RE_FCC_ID.finditer(text_bytes))
    ssid_hits = list(RE_SSID_KW.finditer(text_bytes))
    creds_hits = list(RE_CREDS.finditer(text_bytes))

    out["mac_anchored_total"] = len(mac_hits)
    out["ble_uuid_anchored_total"] = len(ble_hits)
    out["fcc_id_anchored_total"] = len(fcc_hits)
    out["ssid_kw_total"] = len(ssid_hits)
    out["default_creds_kw_total"] = len(creds_hits)

    # Vendor-proximity gated counts (±50 chars)
    def gated(hits):
        out_list = []
        for m in hits:
            vendors = vendor_proximity(text_bytes, m.start())
            if vendors:
                excerpt = text_bytes[max(0, m.start() - 50):min(len(text_bytes), m.end() + 50)].decode("utf-8", errors="replace")
                out_list.append({
                    "match": m.group().decode("utf-8", errors="replace"),
                    "offset": m.start(),
                    "vendors_in_window": vendors,
                    "excerpt": excerpt,
                })
        return out_list

    out["mac_vendor_gated"] = gated(mac_hits)
    out["ble_uuid_vendor_gated"] = gated(ble_hits)
    out["fcc_id_vendor_gated"] = gated(fcc_hits)
    out["mac_vendor_gated_count"] = len(out["mac_vendor_gated"])
    out["ble_uuid_vendor_gated_count"] = len(out["ble_uuid_vendor_gated"])
    out["fcc_id_vendor_gated_count"] = len(out["fcc_id_vendor_gated"])

    # Per-vendor mention counts (case-insensitive substring; not anchored)
    out["vendor_mentions"] = {}
    text_lower = text_bytes.lower()
    for v in VENDORS:
        c = text_lower.count(v.lower().encode("utf-8"))
        if c > 0:
            out["vendor_mentions"][v] = c

    return out


def fetch_pdf(url: str, sleep: float = 0.0) -> tuple[int, bytes, dict]:
    if sleep:
        time.sleep(sleep)
    status, body, headers, elapsed = http_get(url)
    log(f"FETCH {url} -> status={status} bytes={len(body)} elapsed={elapsed}s")
    return status, body, headers


def pdf_to_text(body: bytes) -> str:
    try:
        return extract_text(BytesIO(body)) or ""
    except Exception as e:
        log(f"  pdfminer FAILED: {e}")
        return ""


def find_ndss_dji_paper(catalog_html_path: Path) -> str | None:
    text = catalog_html_path.read_text(errors="replace")
    # Look for hrefs near a 'DJI' mention
    for m in re.finditer(r"DJI", text):
        # Find nearest preceding href
        before = text[max(0, m.start() - 1500):m.start()]
        hrefs = re.findall(r'href="([^"]+(?:\.pdf|/papers?/[^"]+))"', before)
        if hrefs:
            return hrefs[-1]
    # Fallback: find any /wp-content/uploads/...pdf link
    pdfs = re.findall(r'href="([^"]+\.pdf)"', text)
    return pdfs[0] if pdfs else None


def main() -> int:
    catalog_dir = REPO_ROOT / "raw" / "academic" / DISCOVERY_RUN / "_step0"
    targets = []

    # 1. USENIX Sec 2024 Eye of Sauron — fetch the presentation page first to find the PDF link
    targets.append({
        "label": "usenix_sec24_eye_of_sauron",
        "presentation_url": "https://www.usenix.org/conference/usenixsecurity24/presentation/zhang-qibo",
        "kind": "usenix_html_to_pdf",
    })
    # 2. USENIX Sec 2024 Diffie-Hellman Picture Show
    targets.append({
        "label": "usenix_sec24_dh_picture_show",
        "presentation_url": "https://www.usenix.org/conference/usenixsecurity24/presentation/gegenhuber",
        "kind": "usenix_html_to_pdf",
    })
    # 3. USENIX Sec 2024 Logic Gone Astray
    targets.append({
        "label": "usenix_sec24_logic_gone_astray",
        "presentation_url": "https://www.usenix.org/conference/usenixsecurity24/presentation/tu",
        "kind": "usenix_html_to_pdf",
    })
    # 4. NDSS 2024 — AAKA cellular anti-tracking paper (likely contains
    #    cellular identifiers + WiFi BSSIDs in measurement section).
    targets.append({
        "label": "ndss2024_aaka_cellular_antitrack",
        "presentation_url": "https://www.ndss-symposium.org/ndss-paper/aaka-an-anti-tracking-cellular-authentication-scheme-leveraging-anonymous-credentials/",
        "kind": "ndss_html_to_pdf",
    })
    # 5. arXiv preprint 2504.20007 (Towards AI-Driven Policing)
    targets.append({
        "label": "arxiv_2504_20007_ai_policing",
        "pdf_url": "https://arxiv.org/pdf/2504.20007",
        "kind": "arxiv_pdf",
    })

    survey_results = []
    for tgt in targets:
        log(f"=== {tgt['label']} kind={tgt['kind']} ===")
        per_target_dir = OUT / tgt["label"]
        per_target_dir.mkdir(parents=True, exist_ok=True)
        result: dict = {"target": tgt["label"], "kind": tgt["kind"]}

        # Resolve PDF URL
        pdf_url = tgt.get("pdf_url")
        if tgt["kind"] in ("usenix_html_to_pdf", "ndss_html_to_pdf"):
            time.sleep(USENIX_SPACING_S if tgt["kind"] == "usenix_html_to_pdf" else NDSS_SPACING_S)
            status, body, _ = fetch_pdf(tgt["presentation_url"])
            (per_target_dir / "presentation.html").write_bytes(body)
            result["presentation_status"] = status
            result["presentation_bytes"] = len(body)
            if status != 200:
                result["error"] = "presentation page fetch failed"
                survey_results.append(result)
                continue
            # Find the openaccess PDF link (USENIX uses absolute URLs)
            html = body.decode("utf-8", errors="replace")
            # Prefer the camera-ready (usenixsecurity24-...) over the prepub
            if tgt["kind"] == "usenix_html_to_pdf":
                cands = re.findall(
                    r'href="(https?://www\.usenix\.org/system/files/[^"]+\.pdf)"', html
                )
                cr = [u for u in cands if "usenixsecurity24" in u]
                pdf_url = (cr or cands or [None])[0]
            else:  # ndss_html_to_pdf
                # NDSS papers under wp-content/uploads
                cands = re.findall(
                    r'href="(https?://www\.ndss-symposium\.org/wp-content/uploads/[^"]+\.pdf)"',
                    html,
                )
                pdf_url = cands[0] if cands else None

        if not pdf_url:
            result["error"] = "no PDF URL resolved"
            survey_results.append(result)
            continue
        result["pdf_url"] = pdf_url

        # Pace
        if tgt["kind"] == "usenix_html_to_pdf":
            time.sleep(USENIX_SPACING_S)
        elif tgt["kind"] == "ndss_html_to_pdf":
            time.sleep(NDSS_SPACING_S)
        elif tgt["kind"] == "arxiv_pdf":
            time.sleep(ARXIV_SPACING_S)
        elif tgt["kind"] == "ndss_pdf":
            time.sleep(NDSS_SPACING_S)

        status, body, _ = fetch_pdf(pdf_url)
        result["pdf_status"] = status
        result["pdf_bytes"] = len(body)
        result["pdf_sha256"] = hashlib.sha256(body).hexdigest()
        if status != 200 or len(body) < 1000:
            result["error"] = f"pdf fetch failed status={status} bytes={len(body)}"
            survey_results.append(result)
            continue
        (per_target_dir / "paper.pdf").write_bytes(body)

        # Extract text
        text = pdf_to_text(body)
        text_bytes = text.encode("utf-8", errors="replace")
        (per_target_dir / "paper.txt").write_bytes(text_bytes)
        result["clean_text_bytes"] = len(text_bytes)
        result["pdf_pages_extracted"] = text.count("\f") + 1 if text else 0

        # Run survey
        survey = survey_text(text_bytes, tgt["label"])
        result["survey"] = survey
        log(
            f"  survey: mac_anchored={survey['mac_anchored_total']} "
            f"ble_uuid_anchored={survey['ble_uuid_anchored_total']} "
            f"fcc_id_anchored={survey['fcc_id_anchored_total']} "
            f"ssid_kw={survey['ssid_kw_total']} "
            f"creds_kw={survey['default_creds_kw_total']} "
            f"vendor_gated_total={survey['mac_vendor_gated_count'] + survey['ble_uuid_vendor_gated_count'] + survey['fcc_id_vendor_gated_count']}"
        )
        survey_results.append(result)

    summary = {
        "run_ts": TS,
        "discovery_run": DISCOVERY_RUN,
        "targets": survey_results,
        "wave_aggregate": {
            "papers_attempted": len(survey_results),
            "papers_successfully_surveyed": sum(1 for r in survey_results if "survey" in r),
            "total_clean_bytes": sum(r.get("clean_text_bytes", 0) for r in survey_results),
            "total_mac_anchored": sum(r.get("survey", {}).get("mac_anchored_total", 0) for r in survey_results),
            "total_ble_uuid_anchored": sum(r.get("survey", {}).get("ble_uuid_anchored_total", 0) for r in survey_results),
            "total_fcc_id_anchored": sum(r.get("survey", {}).get("fcc_id_anchored_total", 0) for r in survey_results),
            "total_ssid_kw": sum(r.get("survey", {}).get("ssid_kw_total", 0) for r in survey_results),
            "total_creds_kw": sum(r.get("survey", {}).get("default_creds_kw_total", 0) for r in survey_results),
            "total_mac_vendor_gated": sum(r.get("survey", {}).get("mac_vendor_gated_count", 0) for r in survey_results),
            "total_ble_uuid_vendor_gated": sum(r.get("survey", {}).get("ble_uuid_vendor_gated_count", 0) for r in survey_results),
            "total_fcc_id_vendor_gated": sum(r.get("survey", {}).get("fcc_id_vendor_gated_count", 0) for r in survey_results),
        },
    }

    (OUT / "_byte_level_survey.json").write_text(json.dumps(summary, indent=2))
    # Plain-text summary
    txt = ["MAC-27 Step-0 Sample-verification Byte-Level Survey", "=" * 60, ""]
    txt.append(f"run_ts: {TS}")
    txt.append(f"discovery_run: {DISCOVERY_RUN}")
    txt.append(f"papers_attempted: {summary['wave_aggregate']['papers_attempted']}")
    txt.append(f"papers_successfully_surveyed: {summary['wave_aggregate']['papers_successfully_surveyed']}")
    txt.append(f"total_clean_text_bytes: {summary['wave_aggregate']['total_clean_bytes']}")
    txt.append("")
    for r in survey_results:
        txt.append(f"--- {r['target']} ---")
        if "error" in r:
            txt.append(f"  error: {r['error']}")
            continue
        s = r["survey"]
        txt.append(f"  pdf: {r['pdf_url']}")
        txt.append(f"  clean_text_bytes: {r['clean_text_bytes']}")
        txt.append(f"  mac_anchored:   {s['mac_anchored_total']}  vendor_gated: {s['mac_vendor_gated_count']}")
        txt.append(f"  ble_uuid:       {s['ble_uuid_anchored_total']}  vendor_gated: {s['ble_uuid_vendor_gated_count']}")
        txt.append(f"  fcc_id:         {s['fcc_id_anchored_total']}  vendor_gated: {s['fcc_id_vendor_gated_count']}")
        txt.append(f"  ssid_kw:        {s['ssid_kw_total']}")
        txt.append(f"  default_creds:  {s['default_creds_kw_total']}")
        if s.get("vendor_mentions"):
            top = sorted(s["vendor_mentions"].items(), key=lambda kv: -kv[1])
            txt.append(f"  vendors mentioned: {', '.join(f'{k}={v}' for k, v in top[:8])}")
    txt.append("")
    txt.append("=== Wave-aggregate ===")
    wa = summary["wave_aggregate"]
    txt.append(f"  total_mac_anchored:           {wa['total_mac_anchored']}")
    txt.append(f"  total_ble_uuid_anchored:      {wa['total_ble_uuid_anchored']}")
    txt.append(f"  total_fcc_id_anchored:        {wa['total_fcc_id_anchored']}")
    txt.append(f"  total_ssid_kw:                {wa['total_ssid_kw']}")
    txt.append(f"  total_creds_kw:               {wa['total_creds_kw']}")
    txt.append(f"  total_mac_vendor_gated:       {wa['total_mac_vendor_gated']}")
    txt.append(f"  total_ble_uuid_vendor_gated:  {wa['total_ble_uuid_vendor_gated']}")
    txt.append(f"  total_fcc_id_vendor_gated:    {wa['total_fcc_id_vendor_gated']}")

    (OUT / "_byte_level_survey.txt").write_text("\n".join(txt) + "\n")
    log("DONE")
    print("\n".join(txt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
