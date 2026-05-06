"""MAC-33 Wave-E Step-1.5b byte-level survey gate (mandatory before Step-2 dispatch).

Per MAC-33 issue spec — 5 anchors per Step-0 ratification + Wave-E-specific
community-discussion vendor-mention-density tracking (count-only, NOT
row-yielding):

Anchors:
  * mac_anchored                   — \\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\\b
                                     within ±200 chars of MAC/hardware-addr/OUI/
                                     BLE/WiFi keyword
  * ble_uuid_anchored              — UUID 8-4-4-4-12 within ±200 chars of
                                     BLE/Bluetooth/GATT/UUID keyword
  * fcc_id_anchored                — TIGHTENED \\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{1,14}\\b
                                     (mandatory hyphen per MAC-21 §9.11) within
                                     ±50 chars of vendor token, with FCC-grantee
                                     allowlist disambig (MAC-25 module)
  * ssid_kw                        — vendor SSID patterns from lexicon
                                     (SSID/wifi/wi-fi/WPA[12]/probe-request)
  * default_creds_kw               — admin/admin / root/<vendor> patterns
                                     (default password/factory reset/admin)

Wave-E specific:
  * cluster_vendor_mention_density — community-discussion mention counts for
                                     standing-advisory cluster (Flock Safety /
                                     Motorola APX / Axon Body|Fleet /
                                     Cradlepoint|Sierra / Hak5 / DJI). COUNT
                                     ONLY — does NOT contribute to vendor-gated
                                     row total. Logged for Phase-5 Validator
                                     standing-advisory cross-reference per
                                     autonomous-mode framework.

PII redaction default per §11 #3 + SAR-5: role-prefix regex (Officer/Detective/
Sgt/journalist/reporter/user/etc) + author-byline regex at survey time,
count-not-name logging.

Vendor-proximity ±50 chars (per MAC-23 precedent + MAC-25 stingray-disambig
binding).

NEWS-PROSE FP CLASS NOTE: Wave-E surfaces are typified by news prose where
random hex-string / UUID-like IDs may appear (CDN URLs, tracking IDs). The
fcc_id_anchored grantee-allowlist disambig mitigates FCC-ID false positives;
ble_uuid_anchored requires BLE/UUID anchor keywords nearby (filters out CDN
UUIDs); mac_anchored requires MAC/hardware-address/BSSID keyword within window.
News-prose-FP-class extension to stop-list = Step-2.0 deliverable (NOT Step-1).

Outputs:
  * raw/news_forums/<batch-ts>/_step1_5b_survey.json (mandatory deliverable)
  * raw/news_forums/<batch-ts>/_step1_5b_survey.txt  (human-readable)
  * raw/news_forums/<batch-ts>/_step1_5b/_byte_level_survey.json (per Wave-E
    issue body convention)

NO writes to argus.db. NO LLM calls.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Optional

ARGUS_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Identifier-shape regexes
# ---------------------------------------------------------------------------
RE_MAC = re.compile(rb"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
RE_BLE_UUID = re.compile(
    rb"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    rb"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
RE_FCC_ID_TIGHT = re.compile(rb"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{1,14}\b")

# Anchor keyword classes
KW_BLE = re.compile(
    rb"(?i)\b(?:bluetooth|ble|gatt|advertising\s+packet|service\s+uuid|"
    rb"characteristic\s+uuid|peripheral|beacon|ibeacon|eddystone)\b"
)
KW_MAC = re.compile(
    rb"(?i)\b(?:mac\s+address|hardware\s+address|oui|mac-address|hw\s+addr|"
    rb"ethernet\s+address|bssid|burned-in\s+address)\b"
)
KW_SSID = re.compile(
    rb"(?i)\b(?:ssid|wifi|wi-?fi|wireless\s+network|wpa[12]?|"
    rb"probe\s+request|access\s+point|802\.11|esid|hotspot)\b"
)
KW_CREDS = re.compile(
    rb"(?i)\b(?:default\s+(?:password|username|credential|user|admin|passphrase|ssid)|"
    rb"factory\s+(?:default|reset)|admin\s*[:=]|password\s*[:=]|"
    rb"hard-?coded\s+(?:password|credential))\b"
)

# Vendor tokens (full surveillance + cop-car cluster + standing advisory)
VENDOR_TOKENS = [
    b"flock", b"motorola", b"axon", b"cradlepoint", b"sierra wireless",
    b"sierra-wireless", b"hak5", b"dji", b"watchguard", b"reveal",
    b"getac", b"parrot", b"skydio", b"brinc", b"avigilon", b"genetec",
    b"l3harris", b"l-3 harris", b"cellebrite", b"clearview", b"soundthinking",
    b"shotspotter", b"vigilant", b"droneshield", b"dedrone",
    b"axis communications", b"magnet forensics", b"briefcam", b"rekor",
    b"semtech", b"flock safety", b"motorola apx", b"motorola solutions",
    b"axon body", b"axon fleet", b"sierra airlink", b"airlink",
    b"harris corp", b"harris corporation", b"stingray", b"kingfish",
    b"hailstorm", b"perceptics", b"panasonic toughbook", b"alpr",
]

# Standing-advisory targets (per MAC-32 + autonomous-mode framework)
ADVISORY_TARGETS = {
    "Flock Safety":              [b"flock"],
    "Motorola APX":              [b"motorola apx", b"motorola solutions",
                                  b"motorola"],
    "Axon Body/Fleet":           [b"axon body", b"axon fleet", b"axon"],
    "Cradlepoint/Sierra":        [b"cradlepoint", b"sierra wireless",
                                  b"sierra-wireless", b"airlink"],
    "Hak5":                      [b"hak5"],
    "DJI":                       [b"dji"],
    "Cellebrite":                [b"cellebrite"],
    "Stingray/IMSI":             [b"stingray", b"kingfish", b"hailstorm",
                                  b"imsi catcher", b"imsi-catcher"],
}

# PII role-prefix patterns (count-not-name per §11 #3 + SAR-5)
RE_PERSON_PREFIX = re.compile(
    rb"\b(?:Mr|Mrs|Ms|Dr|Prof(?:essor)?|Sergeant|Sgt|Detective|Det|"
    rb"Lt|Lieutenant|Captain|Cpt|Capt|Officer|Trooper|Chief|Major|Colonel|"
    rb"Col|General|Sheriff|Deputy|Marshal|Mayor|Commander|Patrolman|"
    rb"Corporal|Inspector|Commissioner|Agent|Special\s+Agent|"
    rb"Plaintiff|Defendant|Petitioner|Respondent|Appellant|Appellee|"
    rb"Magistrate|Judge|Justice|Hon\.|Honorable)\.?\s+"
    rb"[A-Z][a-zA-Z\'-]{2,30}",
    re.IGNORECASE,
)
# Author byline pattern (news prose) — count-only
RE_AUTHOR_BYLINE = re.compile(
    rb"(?i)\b(?:By|written\s+by|posted\s+by|author|reporter|journalist|"
    rb"correspondent)\s+[A-Z][a-zA-Z\'-]{2,30}",
)
# Forum username pattern (e.g., "user_handle wrote", "@<handle>")
RE_FORUM_HANDLE = re.compile(
    rb"\b(?:user|member|poster|@)[\s_-]*[A-Za-z][A-Za-z0-9_-]{2,30}",
)

VENDOR_PROXIMITY = 50

# ---------------------------------------------------------------------------
# FCC-grantee allowlist (MAC-28 disambig binding)
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, str(ARGUS_ROOT))
    from db.extraction.fcc_grantees_allowlist import validate_fcc_id_match  # type: ignore
except Exception:
    def validate_fcc_id_match(matched_id: str, *, db_path=None) -> tuple[bool, str]:  # type: ignore
        return False, "module_unavailable"

# ---------------------------------------------------------------------------
# HTML cleaning
# ---------------------------------------------------------------------------
TAG_STRIP = re.compile(rb"<[^>]+>")
WS_COL = re.compile(rb"\s+")
SCRIPT_STRIP = re.compile(rb"<script\b[^>]*>.*?</script>", re.S | re.I)
STYLE_STRIP = re.compile(rb"<style\b[^>]*>.*?</style>", re.S | re.I)


def clean_bytes(raw: bytes, content_type: str | None,
                file_path: Path) -> bytes:
    """Wave-E cleaning: HTML tag-strip; JSON pass-through (HN/SE API)."""
    ct = (content_type or "").lower()
    suffix = file_path.suffix.lower()
    if "json" in ct or suffix == ".json":
        return raw
    if "xml" in ct or suffix == ".xml":
        return WS_COL.sub(b" ", TAG_STRIP.sub(b" ", raw))
    if "html" in ct or suffix in (".html", ".htm"):
        body = SCRIPT_STRIP.sub(b" ", raw)
        body = STYLE_STRIP.sub(b" ", body)
        body = TAG_STRIP.sub(b" ", body)
        body = WS_COL.sub(b" ", body)
        return body
    return raw


# ---------------------------------------------------------------------------
# Anchored counters
# ---------------------------------------------------------------------------
def count_anchored(text: bytes, value_re: "re.Pattern[bytes]",
                   anchor_kws: list["re.Pattern[bytes]"],
                   window: int = 200) -> tuple[int, list[bytes]]:
    n = 0
    examples: list[bytes] = []
    for m in value_re.finditer(text):
        ws = max(0, m.start() - window)
        we = m.end() + window
        window_text = text[ws:we]
        if any(kw.search(window_text) for kw in anchor_kws):
            n += 1
            if len(examples) < 3:
                examples.append(m.group())
    return n, examples


def count_vendor_proximity(text: bytes, value_re: "re.Pattern[bytes]",
                           vendor_tokens: list[bytes],
                           window: int = VENDOR_PROXIMITY,
                           apply_grantee_allowlist: bool = False
                           ) -> tuple[int, int, list[bytes]]:
    """For each match within vendor proximity, optionally apply FCC-grantee
    allowlist disambig. Returns (passed, allowlist_drops, examples)."""
    passed = 0
    drops = 0
    examples: list[bytes] = []
    text_l = text.lower()
    for m in value_re.finditer(text):
        ws = max(0, m.start() - window)
        we = m.end() + window
        window_text = text_l[ws:we]
        if any(t in window_text for t in vendor_tokens):
            if apply_grantee_allowlist:
                matched = m.group().decode("ascii", "replace")
                ok, _why = validate_fcc_id_match(matched)
                if not ok:
                    drops += 1
                    continue
            passed += 1
            if len(examples) < 5:
                examples.append(m.group())
    return passed, drops, examples


def vendor_mention_counts(text: bytes) -> dict[str, int]:
    text_l = text.lower()
    out: dict[str, int] = {}
    for vendor, tokens in ADVISORY_TARGETS.items():
        c = 0
        for tok in tokens:
            c += text_l.count(tok)
        out[vendor] = c
    return out


# ---------------------------------------------------------------------------
# Per-file sweep
# ---------------------------------------------------------------------------
def sweep_file(file_path: Path, content_type: str | None) -> dict:
    raw = file_path.read_bytes()
    if not raw:
        return {"raw_bytes": 0, "clean_bytes": 0, "skip": "empty_file"}
    clean = clean_bytes(raw, content_type, file_path)

    ble_anch_n, ble_examples = count_anchored(
        clean, RE_BLE_UUID, [KW_BLE, KW_SSID, KW_MAC])
    mac_anch_n, mac_examples = count_anchored(
        clean, RE_MAC, [KW_MAC, KW_BLE, KW_SSID])
    fcc_passed, fcc_dropped, fcc_examples = count_vendor_proximity(
        clean, RE_FCC_ID_TIGHT, VENDOR_TOKENS,
        window=VENDOR_PROXIMITY, apply_grantee_allowlist=True)

    ssid_kw_n = len(KW_SSID.findall(clean))
    cred_kw_n = len(KW_CREDS.findall(clean))
    ble_kw_n = len(KW_BLE.findall(clean))
    mac_kw_n = len(KW_MAC.findall(clean))

    uuid_total = len(RE_BLE_UUID.findall(clean))
    mac_total = len(RE_MAC.findall(clean))
    fcc_total = len(RE_FCC_ID_TIGHT.findall(clean))

    person_prefix_n = len(RE_PERSON_PREFIX.findall(clean))
    author_byline_n = len(RE_AUTHOR_BYLINE.findall(clean))
    forum_handle_n = len(RE_FORUM_HANDLE.findall(clean))

    vendor_mentions = vendor_mention_counts(clean)

    return {
        "raw_bytes": len(raw),
        "clean_bytes": len(clean),
        # Keyword totals
        "ble_kw": ble_kw_n,
        "mac_kw": mac_kw_n,
        "ssid_kw": ssid_kw_n,
        "default_creds_kw": cred_kw_n,
        # Identifier-shape totals
        "uuid_total": uuid_total,
        "mac_total": mac_total,
        "fcc_id_total": fcc_total,
        # Anchored gates
        "ble_uuid_anchored": ble_anch_n,
        "mac_anchored": mac_anch_n,
        "fcc_id_anchored": fcc_passed,
        "fcc_id_grantee_allowlist_drops": fcc_dropped,
        # PII discipline (count-not-name)
        "person_prefix_count": person_prefix_n,
        "author_byline_count": author_byline_n,
        "forum_handle_count": forum_handle_n,
        # Vendor mentions (cluster-density tracker)
        "vendor_mentions": vendor_mentions,
        # Examples (raw bytes -> ascii)
        "fcc_id_examples": [b.decode("ascii", "replace") for b in fcc_examples],
        "ble_uuid_examples": [b.decode("ascii", "replace") for b in ble_examples],
        "mac_examples": [b.decode("ascii", "replace") for b in mac_examples],
    }


# ---------------------------------------------------------------------------
# Driver helpers
# ---------------------------------------------------------------------------
def find_latest_batch() -> Optional[Path]:
    root = ARGUS_ROOT / "raw" / "news_forums"
    if not root.exists():
        return None
    candidates = [p for p in root.iterdir()
                  if p.is_dir() and not p.name.startswith("_")
                  and re.match(r"\d{8}T\d{6}Z", p.name)]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def walk_cohort_files(cohort: dict) -> list[tuple[str, str, str, str]]:
    """Walk a cohort's docs_fetched / items_fetched / threads_fetched /
    queries_fetched. Returns (cohort_label, kind, file_relpath, content_type)."""
    out: list[tuple[str, str, str, str]] = []
    label = cohort.get("label", "?")

    def _walk(items: list, kind_prefix: str) -> None:
        for item in items or []:
            if item.get("skip"):
                continue
            ent = item.get("entry") or {}
            if (ent.get("status") not in (200, None)
                    and not ent.get("cached_skip")):
                continue
            rel = ent.get("raw_path_relative")
            if not rel:
                continue
            ct = ent.get("content_type", "")
            out.append((label, kind_prefix, rel, ct))

    _walk(cohort.get("docs_fetched", []), "doc")
    _walk(cohort.get("items_fetched", []), "hn_item")
    _walk(cohort.get("threads_fetched", []), "forum_thread")
    _walk(cohort.get("queries_fetched", []), "se_query")
    return out


def main(batch_dir: Optional[Path] = None) -> int:
    if batch_dir is None:
        batch_dir = find_latest_batch()
    if batch_dir is None or not batch_dir.exists():
        print("No news_forums batch found.", file=sys.stderr)
        return 1
    manifest_path = batch_dir / "_manifest.json"
    if not manifest_path.exists():
        print(f"No manifest at {manifest_path}", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text())

    cohort_results: dict[str, dict] = {}
    file_results: list[dict] = []
    advisory_per_cohort: dict[str, dict[str, int]] = {}

    for cohort in manifest.get("cohorts", []):
        cname = cohort.get("label", "?")
        agg_keys = ("raw_bytes", "clean_bytes",
                    "ble_kw", "mac_kw", "ssid_kw", "default_creds_kw",
                    "uuid_total", "mac_total", "fcc_id_total",
                    "ble_uuid_anchored", "mac_anchored", "fcc_id_anchored",
                    "fcc_id_grantee_allowlist_drops",
                    "person_prefix_count", "author_byline_count",
                    "forum_handle_count")
        agg: dict = {k: 0 for k in agg_keys}
        agg["files"] = 0
        agg["files_skipped"] = 0
        agg["files_status_200"] = 0
        adv_agg: dict[str, int] = {k: 0 for k in ADVISORY_TARGETS}

        for cohort_lbl, kind, rel, ct in walk_cohort_files(cohort):
            fpath = ARGUS_ROOT / rel
            if not fpath.exists() or fpath.stat().st_size == 0:
                agg["files_skipped"] += 1
                continue
            try:
                s = sweep_file(fpath, ct)
            except Exception as e:
                print(f"  sweep FAIL {fpath}: {type(e).__name__}: {e}",
                      file=sys.stderr)
                agg["files_skipped"] += 1
                continue
            if s.get("skip"):
                agg["files_skipped"] += 1
                continue
            agg["files"] += 1
            agg["files_status_200"] += 1
            for k in agg_keys:
                agg[k] += s[k]
            for vendor, n in s["vendor_mentions"].items():
                adv_agg[vendor] = adv_agg.get(vendor, 0) + n
            file_results.append({
                "cohort": cname, "kind": kind, "file": rel,
                "content_type": ct,
                **{k: v for k, v in s.items()
                   if k not in ("vendor_mentions",)},
                "vendor_mentions": s["vendor_mentions"],
            })
        cohort_results[cname] = agg
        advisory_per_cohort[cname] = adv_agg

    # Wave aggregate
    wave_agg: dict = {}
    if cohort_results:
        for c in cohort_results.values():
            for k, v in c.items():
                wave_agg[k] = wave_agg.get(k, 0) + v
    wave_advisory: dict[str, int] = {k: 0 for k in ADVISORY_TARGETS}
    for c in advisory_per_cohort.values():
        for v, n in c.items():
            wave_advisory[v] = wave_advisory.get(v, 0) + n

    # Trip-line evaluation
    cohort_trips = []
    for cname, agg in cohort_results.items():
        vendor_gated = (agg.get("ble_uuid_anchored", 0)
                        + agg.get("mac_anchored", 0)
                        + agg.get("fcc_id_anchored", 0))
        cohort_trips.append({"cohort": cname, "vendor_gated_rows": vendor_gated,
                             "trip": vendor_gated == 0,
                             "files": agg.get("files", 0),
                             "files_skipped": agg.get("files_skipped", 0)})

    consecutive_zero = 0
    max_consecutive = 0
    for ct in cohort_trips:
        if ct["trip"]:
            consecutive_zero += 1
            max_consecutive = max(max_consecutive, consecutive_zero)
        else:
            consecutive_zero = 0

    wave_vendor_gated = (wave_agg.get("ble_uuid_anchored", 0)
                         + wave_agg.get("mac_anchored", 0)
                         + wave_agg.get("fcc_id_anchored", 0))
    sar6_3_trip = wave_vendor_gated <= 1.5

    # Tiered halt evaluation: E1+E2 cohort-aggregate yield = 0
    e1_e2_yield = 0
    for cname in ("e1_krebs", "e2_ars"):
        a = cohort_results.get(cname, {})
        e1_e2_yield += (a.get("ble_uuid_anchored", 0)
                        + a.get("mac_anchored", 0)
                        + a.get("fcc_id_anchored", 0))
    tiered_halt_e1_e2_zero = e1_e2_yield == 0

    # ---- Outputs ----
    out_dir = batch_dir
    json_path = out_dir / "_step1_5b_survey.json"
    txt_path = out_dir / "_step1_5b_survey.txt"
    # Per-issue-body convention path
    legacy_dir = out_dir / "_step1_5b"
    legacy_dir.mkdir(exist_ok=True)
    legacy_json_path = legacy_dir / "_byte_level_survey.json"

    lines = [
        f"MAC-33 Wave-E Step 1.5b — byte-level survey "
        f"({dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')})",
        "=" * 90,
        f"Batch: {batch_dir.relative_to(ARGUS_ROOT)}",
        f"Wave HTTP calls used: {manifest.get('wave_calls_used')}/"
        f"{manifest.get('caps', {}).get('wave', '?')}",
        f"Per-host calls: {json.dumps(manifest.get('per_host_calls_used', {}))}",
        "",
        "Methodology:",
        "  * HTML tag-strip + script/style strip; JSON pass-through (HN/SE API).",
        "  * 5 anchors per Step-0 ratification:",
        "      - mac_anchored: MAC ±200 chars from MAC/hardware-addr/OUI/BLE/WiFi kw",
        "      - ble_uuid_anchored: UUID ±200 chars from BLE/Bluetooth/GATT/UUID kw",
        "      - fcc_id_anchored: \\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{1,14}\\b ±50 chars vendor + grantee allowlist disambig (TIGHTENED hyphen-mandatory per MAC-21 §9.11)",
        "      - ssid_kw: SSID/wifi/wi-fi/WPA[12]/probe-request kw count",
        "      - default_creds_kw: default-(pwd|user|cred|admin) etc",
        "  * Vendor-proximity ±50 chars (per MAC-23 precedent + MAC-25 stingray-disambig).",
        "  * Wave-E specific: cluster-mention-density count-only (NOT row-yielding).",
        "  * PII redaction: role-prefix + author-byline + forum-handle counted, NOT named (§11 #3 + SAR-5).",
        "",
        f"{'cohort':<22s}{'files':>6s}{'200':>5s}{'skip':>5s}{'rawKB':>9s}"
        f"{'cleanKB':>9s}{'ble':>5s}{'mac':>5s}{'ssid':>5s}{'cred':>5s}"
        f"{'u_anc':>7s}{'m_anc':>7s}{'f_anc':>7s}"
        f"{'pers':>6s}{'auth':>6s}{'hand':>6s}",
        "-" * 130,
    ]
    for cname, agg in cohort_results.items():
        lines.append(
            f"{cname:<22s}"
            f"{agg.get('files',0):>6d}{agg.get('files_status_200',0):>5d}"
            f"{agg.get('files_skipped',0):>5d}"
            f"{agg.get('raw_bytes',0)//1024:>9d}{agg.get('clean_bytes',0)//1024:>9d}"
            f"{agg.get('ble_kw',0):>5d}{agg.get('mac_kw',0):>5d}"
            f"{agg.get('ssid_kw',0):>5d}{agg.get('default_creds_kw',0):>5d}"
            f"{agg.get('ble_uuid_anchored',0):>7d}"
            f"{agg.get('mac_anchored',0):>7d}"
            f"{agg.get('fcc_id_anchored',0):>7d}"
            f"{agg.get('person_prefix_count',0):>6d}"
            f"{agg.get('author_byline_count',0):>6d}"
            f"{agg.get('forum_handle_count',0):>6d}"
        )
    lines.append("-" * 130)
    lines.append(
        f"{'WAVE TOTAL':<22s}"
        f"{wave_agg.get('files',0):>6d}{wave_agg.get('files_status_200',0):>5d}"
        f"{wave_agg.get('files_skipped',0):>5d}"
        f"{wave_agg.get('raw_bytes',0)//1024:>9d}{wave_agg.get('clean_bytes',0)//1024:>9d}"
        f"{wave_agg.get('ble_kw',0):>5d}{wave_agg.get('mac_kw',0):>5d}"
        f"{wave_agg.get('ssid_kw',0):>5d}{wave_agg.get('default_creds_kw',0):>5d}"
        f"{wave_agg.get('ble_uuid_anchored',0):>7d}"
        f"{wave_agg.get('mac_anchored',0):>7d}"
        f"{wave_agg.get('fcc_id_anchored',0):>7d}"
        f"{wave_agg.get('person_prefix_count',0):>6d}"
        f"{wave_agg.get('author_byline_count',0):>6d}"
        f"{wave_agg.get('forum_handle_count',0):>6d}"
    )
    lines.append("")
    lines.append("Per-cohort vendor-gated row count + trip evaluation:")
    lines.append("-" * 90)
    for ct in cohort_trips:
        verdict = ("TRIP (0 vendor-gated)" if ct["trip"]
                   else f"OK ({ct['vendor_gated_rows']} rows)")
        lines.append(
            f"  {ct['cohort']:<22s} files={ct['files']:>3d}  "
            f"vendor_gated={ct['vendor_gated_rows']:>3d}  {verdict}"
        )
    lines.append("")
    lines.append(f"Wave-aggregate vendor-gated rows: {wave_vendor_gated}")
    lines.append(f"SAR-6 #3 ≤1.5 stop-line: "
                 f"{'TRIP' if sar6_3_trip else 'no trip'}")
    lines.append(
        f"N=2 consecutive zero-cohort floor: max_consecutive={max_consecutive} "
        f"({'TRIP (≥2)' if max_consecutive >= 2 else 'no trip'})"
    )
    lines.append(
        f"Tiered halt (E1+E2 yield = 0): "
        f"{'TRIP' if tiered_halt_e1_e2_zero else 'no trip'} "
        f"(E1+E2 vendor-gated = {e1_e2_yield})"
    )
    lines.append("")
    lines.append("Wave-E cluster-mention-density (count-only, NOT row-yielding):")
    lines.append("-" * 90)
    for vendor in ADVISORY_TARGETS:
        per_c = ", ".join(f"{c}={advisory_per_cohort[c].get(vendor, 0)}"
                          for c in advisory_per_cohort)
        lines.append(
            f"  {vendor:<25s} wave_total={wave_advisory.get(vendor, 0):>5d}   "
            f"per-cohort: {per_c}"
        )
    lines.append("")
    lines.append("PII redaction discipline: role-prefix + author-byline + "
                 "forum-handle counts only. NO names stored.")
    lines.append("")
    lines.append("FCC-ID FP-class news-prose extension diagnostics:")
    lines.append("-" * 90)
    lines.append(
        f"  fcc_id_total (raw matches): {wave_agg.get('fcc_id_total', 0)}"
    )
    lines.append(
        f"  fcc_id_anchored (vendor + grantee allowlist passed): "
        f"{wave_agg.get('fcc_id_anchored', 0)}"
    )
    lines.append(
        f"  fcc_id_grantee_allowlist_drops: "
        f"{wave_agg.get('fcc_id_grantee_allowlist_drops', 0)}"
    )
    lines.append(
        "  News-prose-FP-class extension to stop-list = Step-2.0 deliverable "
        "(NOT Step-1)."
    )

    txt_path.write_text("\n".join(lines) + "\n")

    survey_payload = {
        "issue": "MAC-33",
        "phase": "Phase 4 Wave-E Step 1.5b [FINAL Phase-4 wave]",
        "captured_at_utc": dt.datetime.now(dt.timezone.utc)
                            .strftime("%Y%m%dT%H%M%SZ"),
        "batch": str(batch_dir.relative_to(ARGUS_ROOT)),
        "mitigation": "B (Reddit unauth absence-doc'd; OAuth board-class)",
        "wave_http_calls_used": manifest.get("wave_calls_used"),
        "wave_http_caps": manifest.get("caps", {}),
        "per_host_calls_used": manifest.get("per_host_calls_used", {}),
        "wave_aggregate": wave_agg,
        "wave_vendor_gated_rows": wave_vendor_gated,
        "sar6_3_trip": sar6_3_trip,
        "consecutive_zero_cohorts_max": max_consecutive,
        "n2_floor_trip": max_consecutive >= 2,
        "tiered_halt_e1_e2_zero_trip": tiered_halt_e1_e2_zero,
        "e1_e2_aggregate_yield": e1_e2_yield,
        "per_cohort": cohort_results,
        "per_cohort_trip_eval": cohort_trips,
        "advisory_per_cohort": advisory_per_cohort,
        "advisory_wave_total": wave_advisory,
        "per_file": file_results,
        "vendor_proximity_chars": VENDOR_PROXIMITY,
        "anchor_window_chars": 200,
        "pii_redaction_notes":
            "role-prefix + author-byline + forum-handle patterns counted, not "
            "stored; news prose by-line + forum @handles included per §11 #3 "
            "+ SAR-5",
        "wave_e_specific_addition":
            "community-discussion vendor-mention-density (count-only, NOT "
            "row-yielding) for standing-advisory archive value at cop-car "
            "cluster (per MAC-1 user direction + autonomous-mode framework)",
        "absence_documented_hosts": manifest.get("absence_documented_hosts", []),
        "sar4_routings_applied": manifest.get("sar4_routings_applied", []),
    }
    json_path.write_text(json.dumps(survey_payload, indent=2))
    legacy_json_path.write_text(json.dumps(survey_payload, indent=2))

    print("\n".join(lines))
    print(f"\nText log: {txt_path}")
    print(f"JSON sidecar: {json_path}")
    print(f"Legacy convention path: {legacy_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
