"""MAC-31 Wave-D Step-1.5b byte-level survey gate (mandatory before Step-2 dispatch).

Per MAC-31 issue spec — extends MAC-28 anchors with two Wave-D-specific anchors:

Anchors:
  * ble_uuid_anchored                — UUID 8-4-4-4-12 within ±50 chars of
                                       BLE/Bluetooth/GATT/UUID keyword
  * mac_anchored                     — MAC xx:xx:xx:xx:xx:xx within ±50 chars
                                       of MAC/hardware-address/OUI keyword
  * ssid_kw                          — SSID/wifi/wi-fi/WPA[12]/probe-request count
  * default_creds_kw                 — default password/factory reset/admin count
  * fcc_id_anchored                  — \\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\\b
                                       (TIGHTENED mandatory hyphen) within ±50
                                       chars of vendor token, with FCC-grantee
                                       allowlist disambig (CVE-FP rejection)
  * foia_redaction_marker_count NEW  — (\\[REDACTED\\]|\\(b\\)\\(\\d+\\)|exemption \\(b\\)|████+)
                                       count, do NOT extrapolate behind black-bars
  * court_citation_count        NEW  — `\\d+ U\\.S\\. \\d+`, `\\d+ F\\.\\d+d \\d+`
                                       count, absence-by-design accounting

PII redaction default per §11 #3 + SAR-5: role-prefix regex (Officer/Detective/
Agent/Plaintiff/Defendant/etc) at survey time, count-not-name logging.

Vendor-proximity ±50 chars (per MAC-23 precedent + MAC-25 stingray-disambig binding).

Standing-advisory cross-source surfacing (per MAC-30 §9 #12):
  Flock Safety, Motorola APX, Axon Body/Fleet, Cradlepoint/Sierra Wireless,
  Hak5, DJI vendor mentions logged for Phase-5 Validator standing-advisory
  cross-reference. NOT for current-wave extraction.

Outputs:
  * raw/court_foia/<batch-ts>/_step1_5b_survey.json (mandatory deliverable)
  * raw/court_foia/<batch-ts>/_step1_5b_survey.txt  (human-readable)

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
RE_FCC_ID_TIGHT = re.compile(rb"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b")

# Anchor keyword classes
KW_BLE = re.compile(
    rb"(?i)\b(?:bluetooth|ble|gatt|advertising\s+packet|service\s+uuid|"
    rb"characteristic\s+uuid|peripheral|beacon|ibeacon|eddystone)\b"
)
KW_MAC = re.compile(
    rb"(?i)\b(?:mac\s+address|hardware\s+address|oui|mac-address|hw\s+addr|"
    rb"ethernet\s+address|bssid)\b"
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

# NEW: FOIA redaction markers + court citations.
# Note: the U+2588 FULL BLOCK (████) is encoded in UTF-8 as bytes E2 96 88 — we
# match it as raw bytes because the source text is decoded as UTF-8 then
# re-encoded for byte-level scanning per clean_bytes().
RE_FOIA_REDACTION = re.compile(
    rb"(?:\[REDACTED\]|\(b\)\(\d+\)|\(B\)\(\d+\)|"
    rb"[Ee]xemption\s+\(b\)\(\d+\)|[Ee]xemption\s+\(b\)|"
    rb"[Ee]xemption\s+\d+|"
    rb"(?:\xe2\x96\x88){4,})"  # ████ ≥4 (UTF-8 of U+2588 FULL BLOCK)
)
RE_COURT_USC = re.compile(rb"\b\d+\s+U\.\s?S\.\s+\d+\b")
RE_COURT_FED = re.compile(rb"\b\d+\s+F\.\s?\d+d\s+\d+\b")
RE_COURT_FED_OLD = re.compile(rb"\b\d+\s+F\.\s+\d+\b")  # F. 100 (1st cir.)
RE_COURT_FED_SUPP = re.compile(rb"\b\d+\s+F\.\s?Supp\.?\s?(?:\d+d\s+)?\d+\b")

# Vendor tokens (cop-car cluster + standing advisory; lowercased ASCII)
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
    b"hailstorm", b"perceptics", b"panasonic toughbook",
]

# Standing-advisory targets (per MAC-30 §9 #12) — log not filter
ADVISORY_TARGETS = {
    "Flock Safety":              [b"flock"],
    "Motorola APX":              [b"motorola apx", b"motorola solutions",
                                  b"motorola"],
    "Axon Body/Fleet":           [b"axon body", b"axon fleet", b"axon"],
    "Cradlepoint/Sierra":        [b"cradlepoint", b"sierra wireless",
                                  b"sierra-wireless", b"airlink"],
    "Hak5":                      [b"hak5"],
    "DJI":                       [b"dji"],
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
RE_ETAL = re.compile(rb"\bet\s+al\.?", re.IGNORECASE)

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
# PDF / HTML cleaning
# ---------------------------------------------------------------------------
TAG_STRIP = re.compile(rb"<[^>]+>")
WS_COL = re.compile(rb"\s+")


def clean_bytes(raw: bytes, content_type: str | None,
                file_path: Path) -> bytes:
    if (content_type and "pdf" in content_type.lower()) or \
            file_path.suffix.lower() == ".pdf":
        try:
            from pdfminer.high_level import extract_text
            txt = extract_text(str(file_path)) or ""
            return txt.encode("utf-8", "replace")
        except Exception as e:
            print(f"  pdfminer FAIL {file_path.name}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return raw
    if content_type and ("html" in content_type.lower() or
                         "xml" in content_type.lower()):
        return WS_COL.sub(b" ", TAG_STRIP.sub(b" ", raw))
    if file_path.suffix.lower() in (".html", ".htm", ".xml"):
        return WS_COL.sub(b" ", TAG_STRIP.sub(b" ", raw))
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

    foia_redaction_n = len(RE_FOIA_REDACTION.findall(clean))
    court_usc_n = len(RE_COURT_USC.findall(clean))
    court_fed_n = len(RE_COURT_FED.findall(clean))
    court_fed_old_n = len(RE_COURT_FED_OLD.findall(clean))
    court_fed_supp_n = len(RE_COURT_FED_SUPP.findall(clean))
    court_total = court_usc_n + court_fed_n + court_fed_old_n + court_fed_supp_n

    person_prefix_n = len(RE_PERSON_PREFIX.findall(clean))
    etal_n = len(RE_ETAL.findall(clean))

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
        # NEW: FOIA + court anchors
        "foia_redaction_marker_count": foia_redaction_n,
        "court_citation_count": court_total,
        "court_citation_breakdown": {
            "usc": court_usc_n,
            "fed_reporter_modern": court_fed_n,
            "fed_reporter_old": court_fed_old_n,
            "fed_supp": court_fed_supp_n,
        },
        # PII discipline
        "person_prefix_count": person_prefix_n,
        "et_al_count": etal_n,
        # Vendor mentions
        "vendor_mentions": vendor_mentions,
        # Examples
        "fcc_id_examples": [b.decode("ascii", "replace") for b in fcc_examples],
        "ble_uuid_examples": [b.decode("ascii", "replace") for b in ble_examples],
        "mac_examples": [b.decode("ascii", "replace") for b in mac_examples],
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def find_latest_batch() -> Optional[Path]:
    root = ARGUS_ROOT / "raw" / "court_foia"
    candidates = [p for p in root.iterdir()
                  if p.is_dir() and not p.name.startswith("_")
                  and re.match(r"\d{8}T\d{6}Z", p.name)]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def walk_cohort_files(cohort: dict) -> list[tuple[str, str, str, str]]:
    """Walk a cohort's docs_fetched / articles_fetched / embed_pdfs_fetched.

    Returns list of (cohort_label, kind, file_relpath, content_type).
    """
    out: list[tuple[str, str, str, str]] = []
    label = cohort.get("label", "?")

    def _walk(items: list, kind_prefix: str) -> None:
        for item in items or []:
            if item.get("skip"):
                continue
            ent = item.get("entry") or {}
            if ent.get("status") not in (200, None) and not ent.get("cached_skip"):
                continue
            rel = ent.get("raw_path_relative")
            if not rel:
                continue
            ct = ent.get("content_type", "")
            out.append((label, kind_prefix, rel, ct))

    _walk(cohort.get("docs_fetched", []), "doc")
    _walk(cohort.get("articles_fetched", []), "article")
    _walk(cohort.get("embed_pdfs_fetched", []), "embed_pdf")
    return out


def main(batch_dir: Optional[Path] = None) -> int:
    if batch_dir is None:
        batch_dir = find_latest_batch()
    if batch_dir is None or not batch_dir.exists():
        print("No court_foia batch found.", file=sys.stderr)
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
                    "foia_redaction_marker_count", "court_citation_count",
                    "person_prefix_count", "et_al_count")
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

    # ---- Outputs ----
    out_dir = batch_dir
    json_path = out_dir / "_step1_5b_survey.json"
    txt_path = out_dir / "_step1_5b_survey.txt"

    lines = [
        f"MAC-31 Wave-D Step 1.5b — byte-level survey "
        f"({dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')})",
        "=" * 90,
        f"Batch: {batch_dir.relative_to(ARGUS_ROOT)}",
        f"Wave HTTP calls used: {manifest.get('wave_calls_used')}/"
        f"{manifest.get('caps', {}).get('wave', '?')}",
        f"Per-host calls: {json.dumps(manifest.get('per_host_calls_used', {}))}",
        "",
        "Methodology:",
        "  * pdfminer.six text extraction for PDFs; HTML tag-strip for HTML.",
        "  * 7 anchors:",
        "      - ble_uuid_anchored: UUID ±200 chars from BLE/Bluetooth/GATT/UUID kw",
        "      - mac_anchored: MAC ±200 chars from MAC/hardware-addr/OUI/BLE kw",
        "      - ssid_kw: SSID/wifi/wi-fi/WPA[12]/probe-request kw count",
        "      - default_creds_kw: default-(pwd|user|cred|admin) etc",
        "      - fcc_id_anchored: \\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\\b ±50 chars vendor + grantee allowlist disambig",
        "      - foia_redaction_marker_count NEW: ([REDACTED]|(b)(N)|exemption (b)|████+)",
        "      - court_citation_count NEW: U.S./F./F.Supp. reporter cites",
        "  * Vendor-proximity ±50 chars (per MAC-23 precedent).",
        "  * PII redaction: role-prefix counted, NOT named (§11 #3 + SAR-5).",
        "",
        f"{'cohort':<32s}{'files':>6s}{'200':>5s}{'skip':>5s}{'rawKB':>9s}"
        f"{'cleanKB':>9s}{'ble':>5s}{'mac':>5s}{'ssid':>5s}{'cred':>5s}"
        f"{'u_anc':>7s}{'m_anc':>7s}{'f_anc':>7s}{'redact':>8s}"
        f"{'court':>7s}{'pers':>6s}{'etal':>6s}",
        "-" * 145,
    ]
    for cname, agg in cohort_results.items():
        lines.append(
            f"{cname:<32s}"
            f"{agg.get('files',0):>6d}{agg.get('files_status_200',0):>5d}"
            f"{agg.get('files_skipped',0):>5d}"
            f"{agg.get('raw_bytes',0)//1024:>9d}{agg.get('clean_bytes',0)//1024:>9d}"
            f"{agg.get('ble_kw',0):>5d}{agg.get('mac_kw',0):>5d}"
            f"{agg.get('ssid_kw',0):>5d}{agg.get('default_creds_kw',0):>5d}"
            f"{agg.get('ble_uuid_anchored',0):>7d}"
            f"{agg.get('mac_anchored',0):>7d}"
            f"{agg.get('fcc_id_anchored',0):>7d}"
            f"{agg.get('foia_redaction_marker_count',0):>8d}"
            f"{agg.get('court_citation_count',0):>7d}"
            f"{agg.get('person_prefix_count',0):>6d}"
            f"{agg.get('et_al_count',0):>6d}"
        )
    lines.append("-" * 145)
    lines.append(
        f"{'WAVE TOTAL':<32s}"
        f"{wave_agg.get('files',0):>6d}{wave_agg.get('files_status_200',0):>5d}"
        f"{wave_agg.get('files_skipped',0):>5d}"
        f"{wave_agg.get('raw_bytes',0)//1024:>9d}{wave_agg.get('clean_bytes',0)//1024:>9d}"
        f"{wave_agg.get('ble_kw',0):>5d}{wave_agg.get('mac_kw',0):>5d}"
        f"{wave_agg.get('ssid_kw',0):>5d}{wave_agg.get('default_creds_kw',0):>5d}"
        f"{wave_agg.get('ble_uuid_anchored',0):>7d}"
        f"{wave_agg.get('mac_anchored',0):>7d}"
        f"{wave_agg.get('fcc_id_anchored',0):>7d}"
        f"{wave_agg.get('foia_redaction_marker_count',0):>8d}"
        f"{wave_agg.get('court_citation_count',0):>7d}"
        f"{wave_agg.get('person_prefix_count',0):>6d}"
        f"{wave_agg.get('et_al_count',0):>6d}"
    )
    lines.append("")
    lines.append("Per-cohort vendor-gated row count + trip evaluation:")
    lines.append("-" * 90)
    for ct in cohort_trips:
        verdict = ("TRIP (0 vendor-gated)" if ct["trip"]
                   else f"OK ({ct['vendor_gated_rows']} rows)")
        lines.append(
            f"  {ct['cohort']:<32s} files={ct['files']:>3d}  "
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
    lines.append("")
    lines.append("Standing-advisory cross-source vendor mentions (count, not filter):")
    lines.append("-" * 90)
    for vendor in ADVISORY_TARGETS:
        per_c = ", ".join(f"{c}={advisory_per_cohort[c].get(vendor, 0)}"
                          for c in advisory_per_cohort)
        lines.append(
            f"  {vendor:<35s} wave_total={wave_advisory.get(vendor, 0):>5d}   "
            f"per-cohort: {per_c}"
        )
    lines.append("")
    lines.append("Wave-D-specific anchors (FOIA + court):")
    lines.append("-" * 90)
    lines.append(
        f"  FOIA redaction markers (wave): "
        f"{wave_agg.get('foia_redaction_marker_count', 0)}"
    )
    lines.append(
        f"  Court citations (wave): {wave_agg.get('court_citation_count', 0)}"
    )
    lines.append(
        "  NOTE: redaction markers absence-by-design — content behind black-bars "
        "NOT extrapolated (§11 #2)."
    )
    lines.append(
        "  NOTE: court citations absence-by-design accounting (Mitigation B; "
        "CL absence-doc'd)."
    )
    lines.append("")
    lines.append("PII redaction discipline: role-prefix counts only. NO names stored.")

    txt_path.write_text("\n".join(lines) + "\n")

    json_path.write_text(json.dumps({
        "issue": "MAC-31",
        "phase": "Phase 4 Wave-D Step 1.5b",
        "captured_at_utc": dt.datetime.now(dt.timezone.utc)
                            .strftime("%Y%m%dT%H%M%SZ"),
        "batch": str(batch_dir.relative_to(ARGUS_ROOT)),
        "mitigation": "B (CourtListener absence-doc'd; D1 dropped)",
        "wave_http_calls_used": manifest.get("wave_calls_used"),
        "wave_http_caps": manifest.get("caps", {}),
        "per_host_calls_used": manifest.get("per_host_calls_used", {}),
        "wave_aggregate": wave_agg,
        "wave_vendor_gated_rows": wave_vendor_gated,
        "sar6_3_trip": sar6_3_trip,
        "consecutive_zero_cohorts_max": max_consecutive,
        "n2_floor_trip": max_consecutive >= 2,
        "per_cohort": cohort_results,
        "per_cohort_trip_eval": cohort_trips,
        "advisory_per_cohort": advisory_per_cohort,
        "advisory_wave_total": wave_advisory,
        "per_file": file_results,
        "vendor_proximity_chars": VENDOR_PROXIMITY,
        "anchor_window_chars": 200,
        "pii_redaction_notes":
            "role-prefix patterns counted, not stored;"
            " court party names (Plaintiff/Defendant/etc) included in role-prefix"
            " regex per §11 #3 + SAR-5",
        "wave_d_specific_anchors": {
            "foia_redaction_marker_count":
                wave_agg.get("foia_redaction_marker_count", 0),
            "court_citation_count":
                wave_agg.get("court_citation_count", 0),
            "absence_by_design":
                "redaction-marker counts are absence-evidence; "
                "content behind black-bars NOT extrapolated (§11 #2)",
        },
    }, indent=2))

    print("\n".join(lines))
    print(f"\nText log: {txt_path}")
    print(f"JSON sidecar: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
