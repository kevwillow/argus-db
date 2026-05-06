"""MAC-32 Wave-E Step-0 sample-verification — fetch ~6 candidate news/forum docs +
zero-LLM byte-level regex/keyword sweep. Project Wave-E yield surface honestly.

Per Step-0 binding template + SAR-6 #1: NO writes to db/argus.db, NO LLM calls.
Methodology mirrors MAC-30 §4 sample-verify shape.

Surfaces sampled:
  News:
    1. krebsonsecurity.com — Stingray-class IMSI catcher article
       (Krebs has investigative coverage of surveillance tech; Wordpress permalinks)
    2. arstechnica.com — Flock Safety / surveillance-related article
       (mainstream tech journalism; UA-class block list does NOT include
       ArgusSourceWorker)
    3. theregister.com — surveillance/procurement story
       (UK industry news; permissive robots with 5s crawl-delay)
  Forums (open / API-class):
    4. news.ycombinator.com — story permalink referencing surveillance vendor
       (HN search via hn.algolia.com API; story page itself fetched at HN host)
    5. api.stackexchange.com — Q&A search across SO+SF networking-tagged questions
       referencing Cradlepoint / Sierra Wireless / Cellebrite (vendor-anchored)
    6. mavicpilots.com — DJI consumer-drone forum thread (open with
       Content-Signal=search=yes); standing-advisory cluster surface
  Forums (auth-walled / Cloudflare-walled — NOT FETCHED, absence-documented):
    - reddit.com/r/* — robots `Disallow: /` for unauth tier (§11 #6 + SAR-4);
      OAuth tier requires board-class API approval (mitigation A path)
    - stackoverflow.com / serverfault.com (HTML) — Cloudflare bot wall returns
      403 + JS challenge to non-browser UAs; api.stackexchange.com is the
      publisher-provided alternative (SAR-4)
    - eham.net /forum/ /forums/ — robots-disallowed (§11 #6); absence-document
    - twitter.com / x.com — auth-gated entirely (§11 #2); not fetched

Byte-level regex/keyword anchors (replicates MAC-30 §4 + MAC-25 Step-1.5b shape;
FCC-ID regex is the TIGHTENED hyphen-mandatory variant per MAC-21 §9.11):
  - mac_anchored      \\b[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}\\b
  - ble_uuid_anchored \\b[0-9A-Fa-f]{8}-([0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\\b
  - fcc_id_anchored   \\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{1,14}\\b  (mandatory hyphen)
  - ssid_kw           case-insensitive \\bssid\\b literal token
  - default_creds_kw  password / login / credential / passphrase tokens
  - vendor_proximity  vendor occurrence within ±50 chars of any anchor
  - pii_role_kw       count-not-name role-prefix sweep (Officer / Det. / Sgt /
                       Author / journalist) — count only, NOT persisted

Output:
  raw/news_forums/<discovery-run>/_step0_sample/<source>__<doc>/<file>
  raw/news_forums/<discovery-run>/_step0_sample/_byte_level_survey.json
  raw/news_forums/<discovery-run>/_step0_sample/_byte_level_survey.txt
  logs/mac32_step0_sample_verify_<run-ts>.log
"""
from __future__ import annotations
import hashlib, html as html_mod, json, re, ssl, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = (
    "ArgusSourceWorker/0.1 (Phase4 Wave-E Step 0 sample verify; "
    "+https://github.com/argus-project)"
)
TIMEOUT_S = 60
KREBS_SPACING_S = 35.0   # robots Crawl-Delay 35
ARS_SPACING_S = 5.0
REGISTER_SPACING_S = 5.0  # robots Crawl-delay 5
HN_SPACING_S = 30.0       # robots Crawl-delay 30
STACKEX_SPACING_S = 1.5   # api.stackexchange = 30 req/sec free; conservative
MAVIC_SPACING_S = 2.0

REPO_ROOT = Path("/home/kev/argus")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
DISCOVERY_RUN = "20260506T044612Z"
OUT = REPO_ROOT / "raw" / "news_forums" / DISCOVERY_RUN / "_step0_sample"
OUT.mkdir(parents=True, exist_ok=True)
LOG = REPO_ROOT / "logs" / f"mac32_step0_sample_verify_{TS}.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

# Reuse Wave-A/B/C/D vendor lexicon (MAC-12/MAC-21/MAC-27/MAC-30 §4).
VENDORS = [
    "Avigilon", "Axis Communications", "Axon", "Berla", "BRINC", "BriefCam",
    "Cellebrite", "Clearview AI", "Cradlepoint", "Dedrone",
    "Digital Receiver Technology", "DJI", "DroneShield", "Engility",
    "Flock Safety", "Genetec", "Getac", "Hak5", "Harris", "Jacobs", "Kenwood",
    "KeyW", "L3Harris", "Magnet Forensics", "Motorola Solutions", "Parrot",
    "Rekor", "Reveal", "Septier", "Sierra Wireless", "Skydio", "SoundThinking",
    "Vigilant Solutions", "WatchGuard",
]

# Byte-level anchors — mirror MAC-30 verbatim.
RE_MAC = re.compile(rb"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b")
RE_BLE_UUID = re.compile(rb"\b[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\b")
RE_FCC_ID = re.compile(rb"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{1,14}\b")
RE_SSID_KW = re.compile(rb"\bssid\b", re.IGNORECASE)
RE_CREDS = re.compile(
    rb"\b(?:default\s+)?(?:password|passphrase|credential|login|admin)\b",
    re.IGNORECASE,
)
# PII role-prefix sweep (count-not-name; not persisted)
RE_PII_ROLE = re.compile(
    rb"\b(?:Officer|Det\.|Detective|Sgt|Sergeant|Lt\.|Lieutenant|Capt\.|Captain|"
    rb"Chief|Trooper|Deputy|Author|By [A-Z]\.|journalist|reporter|user)\b",
    re.IGNORECASE,
)

logfh = open(LOG, "a", encoding="utf-8")


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
    print(line, flush=True)
    logfh.write(line + "\n")
    logfh.flush()


def http_get(url: str, ua: str = UA) -> tuple[int, bytes, dict, float]:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    ctx = ssl.create_default_context()
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as resp:
            body = resp.read()
            return (
                resp.status,
                body,
                dict(resp.headers),
                round(time.monotonic() - t0, 3),
            )
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return e.code, body, dict(e.headers or {}), round(time.monotonic() - t0, 3)
    except urllib.error.URLError as e:
        return 0, b"", {"_url_error": str(e.reason)}, round(time.monotonic() - t0, 3)
    except Exception as e:
        return 0, b"", {"_fatal": repr(e)}, round(time.monotonic() - t0, 3)


_TAG_RE = re.compile(rb"<[^>]+>")
_WS_RE = re.compile(rb"\s+")


def strip_html(body: bytes) -> bytes:
    """Quick-and-dirty HTML→text strip (stdlib only). Sufficient for byte sweep."""
    # Drop <script> / <style> blocks entirely (regex multi-line).
    body = re.sub(rb"<script\b[^>]*>.*?</script>", b" ", body, flags=re.S | re.I)
    body = re.sub(rb"<style\b[^>]*>.*?</style>", b" ", body, flags=re.S | re.I)
    body = re.sub(rb"<noscript\b[^>]*>.*?</noscript>", b" ", body, flags=re.S | re.I)
    # Strip remaining tags
    body = _TAG_RE.sub(b" ", body)
    # Decode HTML entities
    text = html_mod.unescape(body.decode("utf-8", errors="replace"))
    body = text.encode("utf-8", errors="replace")
    # Collapse whitespace
    body = _WS_RE.sub(b" ", body).strip()
    return body


def vendor_proximity(text_bytes: bytes, anchor_offset: int, window: int = 50) -> list[str]:
    lo = max(0, anchor_offset - window)
    hi = min(len(text_bytes), anchor_offset + window)
    chunk = text_bytes[lo:hi].lower()
    hits = []
    for v in VENDORS:
        if v.lower().encode("utf-8") in chunk:
            hits.append(v)
    return hits


def survey_text(text_bytes: bytes, label: str) -> dict:
    out: dict = {"label": label, "byte_count": len(text_bytes)}
    mac_hits = list(RE_MAC.finditer(text_bytes))
    ble_hits = list(RE_BLE_UUID.finditer(text_bytes))
    fcc_hits = list(RE_FCC_ID.finditer(text_bytes))
    ssid_hits = list(RE_SSID_KW.finditer(text_bytes))
    creds_hits = list(RE_CREDS.finditer(text_bytes))
    pii_hits = list(RE_PII_ROLE.finditer(text_bytes))

    out["mac_anchored_total"] = len(mac_hits)
    out["ble_uuid_anchored_total"] = len(ble_hits)
    out["fcc_id_anchored_total"] = len(fcc_hits)
    out["ssid_kw_total"] = len(ssid_hits)
    out["default_creds_kw_total"] = len(creds_hits)
    out["pii_role_kw_count"] = len(pii_hits)  # COUNT only

    def gated(hits):
        out_list = []
        for m in hits:
            vendors = vendor_proximity(text_bytes, m.start())
            if vendors:
                lo = max(0, m.start() - 50)
                hi = min(len(text_bytes), m.end() + 50)
                excerpt = text_bytes[lo:hi].decode("utf-8", errors="replace")
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

    out["vendor_mentions"] = {}
    text_lower = text_bytes.lower()
    for v in VENDORS:
        c = text_lower.count(v.lower().encode("utf-8"))
        if c > 0:
            out["vendor_mentions"][v] = c

    return out


def fetch_doc(url: str, label: str, sleep: float, ua: str = UA) -> dict:
    if sleep:
        time.sleep(sleep)
    status, body, headers, elapsed = http_get(url, ua=ua)
    log(f"FETCH {url} -> status={status} bytes={len(body)} elapsed={elapsed}s")
    rec = {
        "label": label,
        "url": url,
        "status": status,
        "raw_bytes": len(body),
        "elapsed_s": elapsed,
        "sha256": hashlib.sha256(body).hexdigest(),
        "content_type": headers.get("Content-Type", ""),
    }
    per_dir = OUT / label
    per_dir.mkdir(parents=True, exist_ok=True)
    (per_dir / "raw.html").write_bytes(body)
    if status != 200 or len(body) < 200:
        rec["error"] = f"fetch returned status={status} bytes={len(body)}"
        return rec
    # Strip to clean text (HTML or JSON; for JSON the strip is a no-op-ish)
    if "json" in rec["content_type"].lower() or url.endswith(".json"):
        clean = body  # JSON is already roughly text
    else:
        clean = strip_html(body)
    (per_dir / "clean.txt").write_bytes(clean)
    rec["clean_bytes"] = len(clean)
    rec["survey"] = survey_text(clean, label)
    s = rec["survey"]
    log(
        f"  survey: mac_anchored={s['mac_anchored_total']} "
        f"ble_uuid_anchored={s['ble_uuid_anchored_total']} "
        f"fcc_id_anchored={s['fcc_id_anchored_total']} "
        f"ssid_kw={s['ssid_kw_total']} creds_kw={s['default_creds_kw_total']} "
        f"vendor_gated={s['mac_vendor_gated_count'] + s['ble_uuid_vendor_gated_count'] + s['fcc_id_vendor_gated_count']} "
        f"pii_role_count={s['pii_role_kw_count']}"
    )
    return rec


def main() -> int:
    samples: list[dict] = []

    # 1. Krebs — search returns Stingray articles. Fetch the front page first to
    #    confirm sitemap + use a known investigative article on stingray FCC IDs.
    samples.append(
        fetch_doc(
            "https://krebsonsecurity.com/2014/06/cops-around-the-u-s-can-spy-on-your-phone/",
            "krebs_stingray_2014",
            sleep=0.0,  # first call, no prior spacing
        )
    )

    # 2. Ars Technica — known investigative coverage of Cellebrite + Stingray.
    samples.append(
        fetch_doc(
            "https://arstechnica.com/tech-policy/2014/03/florida-cops-pen-register-orders-not-warrants-to-track-iphones/",
            "arstechnica_stingray_2014",
            sleep=ARS_SPACING_S,
        )
    )

    # 3. The Register — Flock Safety / surveillance procurement story.
    samples.append(
        fetch_doc(
            "https://www.theregister.com/2024/04/18/flock_safety_alpr_lawsuit/",
            "register_flock_2024",
            sleep=REGISTER_SPACING_S,
        )
    )

    # 4. Hacker News story — search via hn.algolia.com API for "Cellebrite",
    #    take first hit; HN search API is open + CC-licensed.
    time.sleep(HN_SPACING_S)
    status, body, headers, _ = http_get(
        "https://hn.algolia.com/api/v1/search?query=Cellebrite&tags=story&hitsPerPage=5"
    )
    log(f"FETCH hn.algolia search Cellebrite -> status={status} bytes={len(body)}")
    if status == 200 and len(body) > 100:
        try:
            j = json.loads(body)
            top = (j.get("hits") or [{}])[0]
            hn_obj_id = top.get("objectID")
            hn_title = top.get("title", "")
            log(f"  HN search top hit: id={hn_obj_id} title={hn_title!r}")
            if hn_obj_id:
                # Fetch the HN comment page
                samples.append(
                    fetch_doc(
                        f"https://hn.algolia.com/api/v1/items/{hn_obj_id}",
                        "hn_cellebrite_top_hit",
                        sleep=STACKEX_SPACING_S,
                    )
                )
        except Exception as e:
            log(f"  HN parse FAILED: {e}")

    # 5. StackExchange API — search for "Cradlepoint" and "Sierra Wireless"
    #    across the network. Open API; 300 req/day unauth.
    time.sleep(STACKEX_SPACING_S)
    samples.append(
        fetch_doc(
            "https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance"
            "&q=Cradlepoint&site=stackoverflow&filter=withbody",
            "stackex_cradlepoint",
            sleep=0,
        )
    )

    # 6. mavicpilots.com — DJI vendor-anchored forum (cluster surface).
    #    Open with Content-Signal=search=yes,ai-train=no.
    samples.append(
        fetch_doc(
            "https://mavicpilots.com/threads/dji-fly-app-stuck-on-aircraft-firmware-update.119284/",
            "mavicpilots_dji_thread",
            sleep=MAVIC_SPACING_S,
        )
    )

    # Aggregate
    surveyed = [s for s in samples if "survey" in s]
    summary = {
        "run_ts": TS,
        "discovery_run": DISCOVERY_RUN,
        "samples": samples,
        "wave_aggregate": {
            "docs_attempted": len(samples),
            "docs_successfully_surveyed": len(surveyed),
            "total_raw_bytes": sum(s.get("raw_bytes", 0) for s in samples),
            "total_clean_bytes": sum(s.get("clean_bytes", 0) for s in surveyed),
            "total_mac_anchored": sum(
                s["survey"]["mac_anchored_total"] for s in surveyed
            ),
            "total_ble_uuid_anchored": sum(
                s["survey"]["ble_uuid_anchored_total"] for s in surveyed
            ),
            "total_fcc_id_anchored": sum(
                s["survey"]["fcc_id_anchored_total"] for s in surveyed
            ),
            "total_ssid_kw": sum(s["survey"]["ssid_kw_total"] for s in surveyed),
            "total_creds_kw": sum(
                s["survey"]["default_creds_kw_total"] for s in surveyed
            ),
            "total_mac_vendor_gated": sum(
                s["survey"]["mac_vendor_gated_count"] for s in surveyed
            ),
            "total_ble_uuid_vendor_gated": sum(
                s["survey"]["ble_uuid_vendor_gated_count"] for s in surveyed
            ),
            "total_fcc_id_vendor_gated": sum(
                s["survey"]["fcc_id_vendor_gated_count"] for s in surveyed
            ),
            "total_pii_role_count_not_name": sum(
                s["survey"]["pii_role_kw_count"] for s in surveyed
            ),
        },
        "absence_documented_surfaces": [
            "reddit.com/r/* (robots Disallow: / unauth tier; OAuth = board-class)",
            "stackoverflow.com / serverfault.com HTML (Cloudflare bot wall — "
            "use api.stackexchange.com publisher-provided alternative per SAR-4)",
            "eham.net /forum/ /forums/ /community/ (robots-disallowed)",
            "twitter.com / x.com (auth-gated entirely; §11 #2)",
            "forum.dji.com (returned status=202 / 0 bytes — likely bot-walled; "
            "needs Step-1 verification or absence-document)",
        ],
    }

    (OUT / "_byte_level_survey.json").write_text(json.dumps(summary, indent=2))

    # Plain-text summary
    txt = ["MAC-32 Wave-E Step-0 Sample-verification Byte-Level Survey", "=" * 70, ""]
    txt.append(f"run_ts: {TS}")
    txt.append(f"discovery_run: {DISCOVERY_RUN}")
    wa = summary["wave_aggregate"]
    txt.append(f"docs_attempted: {wa['docs_attempted']}")
    txt.append(f"docs_successfully_surveyed: {wa['docs_successfully_surveyed']}")
    txt.append(f"total_raw_bytes: {wa['total_raw_bytes']}")
    txt.append(f"total_clean_bytes: {wa['total_clean_bytes']}")
    txt.append("")
    for s in samples:
        txt.append(f"--- {s['label']} ---")
        txt.append(f"  url: {s['url']}")
        if "error" in s:
            txt.append(f"  error: {s['error']}")
            continue
        sv = s["survey"]
        txt.append(f"  raw_bytes: {s['raw_bytes']}  clean_bytes: {s['clean_bytes']}")
        txt.append(f"  mac_anchored:   {sv['mac_anchored_total']}  vendor_gated: {sv['mac_vendor_gated_count']}")
        txt.append(f"  ble_uuid:       {sv['ble_uuid_anchored_total']}  vendor_gated: {sv['ble_uuid_vendor_gated_count']}")
        txt.append(f"  fcc_id:         {sv['fcc_id_anchored_total']}  vendor_gated: {sv['fcc_id_vendor_gated_count']}")
        txt.append(f"  ssid_kw:        {sv['ssid_kw_total']}")
        txt.append(f"  default_creds:  {sv['default_creds_kw_total']}")
        txt.append(f"  pii_role_count: {sv['pii_role_kw_count']}")
        if sv.get("vendor_mentions"):
            top = sorted(sv["vendor_mentions"].items(), key=lambda kv: -kv[1])
            txt.append(f"  vendors mentioned: {', '.join(f'{k}={v}' for k, v in top[:8])}")
    txt.append("")
    txt.append("=== Wave-aggregate ===")
    txt.append(f"  total_mac_anchored:           {wa['total_mac_anchored']}")
    txt.append(f"  total_ble_uuid_anchored:      {wa['total_ble_uuid_anchored']}")
    txt.append(f"  total_fcc_id_anchored:        {wa['total_fcc_id_anchored']}")
    txt.append(f"  total_ssid_kw:                {wa['total_ssid_kw']}")
    txt.append(f"  total_creds_kw:               {wa['total_creds_kw']}")
    txt.append(f"  total_mac_vendor_gated:       {wa['total_mac_vendor_gated']}")
    txt.append(f"  total_ble_uuid_vendor_gated:  {wa['total_ble_uuid_vendor_gated']}")
    txt.append(f"  total_fcc_id_vendor_gated:    {wa['total_fcc_id_vendor_gated']}")
    txt.append(f"  total_pii_role_count_not_name: {wa['total_pii_role_count_not_name']}")
    txt.append("")
    txt.append("=== Absence-documented surfaces (§11 #2 / §11 #6 + SAR-4) ===")
    for a in summary["absence_documented_surfaces"]:
        txt.append(f"  - {a}")

    (OUT / "_byte_level_survey.txt").write_text("\n".join(txt) + "\n")
    log("DONE")
    print("\n".join(txt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
