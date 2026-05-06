"""MAC-28 Wave-C Step-1.5b byte-level survey gate (mandatory deliverable).

Per MAC-28 issue spec: regex+context-anchor sweep across all fetched papers
BEFORE any Step-2 dispatch.

Anchors (5 mandatory):
  * ble_uuid_anchored  — UUID 8-4-4-4-12 hex within ±50 chars of
                          BLE/Bluetooth/GATT/UUID keyword
  * mac_anchored       — MAC xx:xx:xx:xx:xx:xx within ±50 chars of
                          MAC/hardware-address/OUI/Bluetooth keyword
  * ssid_kw            — SSID/wifi/wi-fi/WPA[12]/probe-request keyword count
  * default_creds_kw   — default password/factory reset/admin/etc keyword count
  * fcc_id_anchored    — `\\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\\b` (MANDATORY
                          HYPHEN per MAC-21 §9.11) within ±50 chars of any
                          vendor-of-interest token

Vendor-proximity windows: ±50 chars (per MAC-23 precedent).

PII redaction discipline (per §11 #3 + SAR-5):
  * Person-name proximity is COUNTED, NOT NAMED.
  * Researcher names in academic context: count-not-name default.

Outputs:
  * raw/academic/_step1_survey/<run-ts>/_byte_level_survey.txt
  * raw/academic/_step1_survey/<run-ts>/_byte_level_survey.json

NO writes to argus.db. NO LLM calls.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

ARGUS_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Regex anchors (operate on cleaned text, byte-level after .encode())
# ---------------------------------------------------------------------------
RE_MAC = re.compile(rb"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
RE_BLE_UUID = re.compile(rb"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
RE_FCC_ID_TIGHT = re.compile(rb"\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b")

KW_BLE = re.compile(
    rb"(?i)\b(?:bluetooth|ble|gatt|advertising\s+packet|service\s+uuid|characteristic\s+uuid|peripheral|beacon|ibeacon|eddystone)\b"
)
KW_MAC = re.compile(
    rb"(?i)\b(?:mac\s+address|hardware\s+address|oui|mac-address|hw\s+addr|ethernet\s+address)\b"
)
KW_SSID = re.compile(
    rb"(?i)\b(?:ssid|wifi|wi-?fi|wireless\s+network|wpa[12]?|probe\s+request|access\s+point|802\.11|esid)\b"
)
KW_CREDS = re.compile(
    rb"(?i)\b(?:default\s+(?:password|username|credential|user|admin|passphrase|ssid)|factory\s+(?:default|reset)|admin\s*[:=]|password\s*[:=]|hard-?coded\s+(?:password|credential))\b"
)

# Vendor tokens (cop-car cluster + standing advisory; lowercased ASCII)
VENDOR_TOKENS = [
    b"flock", b"motorola", b"axon", b"cradlepoint", b"sierra wireless",
    b"sierra-wireless", b"hak5", b"dji", b"watchguard", b"reveal",
    b"getac", b"parrot", b"skydio", b"brinc", b"avigilon", b"genetec",
    b"l3harris", b"cellebrite", b"clearview", b"soundthinking",
    b"shotspotter", b"vigilant", b"droneshield", b"dedrone",
    b"axis communications", b"magnet forensics", b"briefcam", b"rekor",
    b"semtech", b"flock safety", b"motorola apx", b"motorola solutions",
    b"axon body", b"axon fleet", b"sierra airlink", b"airlink",
]
# Standing advisory targets (per MAC-27 §9 #12) — log not filter
ADVISORY_TARGETS = {
    "Flock Safety": [b"flock"],
    "Motorola APX": [b"motorola apx", b"motorola solutions", b"motorola"],
    "Axon Body": [b"axon body", b"axon fleet", b"axon"],
    "Cradlepoint / Sierra Wireless": [b"cradlepoint", b"sierra wireless", b"sierra-wireless", b"airlink"],
    "Hak5": [b"hak5"],
    "DJI": [b"dji"],
}

# Person-name proximity (PII redaction count per §11 #3 + SAR-5).
# Researcher names: academic format is typically "Name, Name, and Name" — to
# avoid storing names we count occurrences of role-prefix patterns AND
# capture-only count for paragraph-level "et al." references.
RE_PERSON_PREFIX = re.compile(
    rb"\b(?:Mr|Mrs|Ms|Dr|Prof(?:essor)?|Sergeant|Sgt|Detective|Lt|Lieutenant|"
    rb"Captain|Cpt|Officer|Trooper|Chief|Major|Colonel|General|Sheriff)\.?\s+"
    rb"[A-Z][a-zA-Z\'-]{2,30}",
    re.IGNORECASE,
)
RE_ETAL = re.compile(rb"\bet\s+al\.?", re.IGNORECASE)

VENDOR_PROXIMITY = 50  # chars


# ---------------------------------------------------------------------------
# PDF / HTML cleaning
# ---------------------------------------------------------------------------
TAG_STRIP = re.compile(rb"<[^>]+>")
WS_COL = re.compile(rb"\s+")


def clean_bytes(raw: bytes, content_type: str | None, file_path: Path) -> bytes:
    if content_type and "pdf" in content_type.lower() or file_path.suffix.lower() == ".pdf":
        try:
            from pdfminer.high_level import extract_text
            txt = extract_text(str(file_path)) or ""
            return txt.encode("utf-8", "replace")
        except Exception as e:
            print(f"  pdfminer FAIL {file_path.name}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return raw
    if content_type and ("html" in content_type.lower() or "xml" in content_type.lower()):
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
    """For each match of value_re, count it if any anchor_kws appears within
    ±window chars. Returns (count, sample examples up to 3)."""
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
                            window: int = VENDOR_PROXIMITY
                            ) -> tuple[int, list[bytes]]:
    """For each match of value_re, count it if any vendor_token appears
    within ±window chars (case-insensitive). Returns (count, examples)."""
    n = 0
    examples: list[bytes] = []
    text_l = text.lower()
    for m in value_re.finditer(text):
        ws = max(0, m.start() - window)
        we = m.end() + window
        window_text = text_l[ws:we]
        if any(t in window_text for t in vendor_tokens):
            n += 1
            if len(examples) < 5:
                examples.append(m.group())
    return n, examples


def vendor_mention_counts(text: bytes) -> dict[str, int]:
    """Count each advisory-target vendor token across the text."""
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
    fcc_anch_n, fcc_examples = count_vendor_proximity(
        clean, RE_FCC_ID_TIGHT, VENDOR_TOKENS, window=VENDOR_PROXIMITY)

    ssid_kw_n = len(KW_SSID.findall(clean))
    cred_kw_n = len(KW_CREDS.findall(clean))
    ble_kw_n = len(KW_BLE.findall(clean))
    mac_kw_n = len(KW_MAC.findall(clean))

    uuid_total = len(RE_BLE_UUID.findall(clean))
    mac_total = len(RE_MAC.findall(clean))
    fcc_total = len(RE_FCC_ID_TIGHT.findall(clean))

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
        # Anchored gates (the load-bearing numbers)
        "ble_uuid_anchored": ble_anch_n,
        "mac_anchored": mac_anch_n,
        "fcc_id_anchored": fcc_anch_n,
        # PII discipline (counts only, no names)
        "person_prefix_count": person_prefix_n,
        "et_al_count": etal_n,
        # Vendor mentions (advisory targets, count only)
        "vendor_mentions": vendor_mentions,
        # Sample examples (small bytes; first 5 of FCC, first 3 of BLE/MAC)
        "fcc_id_examples": [b.decode("ascii", "replace") for b in fcc_examples],
        "ble_uuid_examples": [b.decode("ascii", "replace") for b in ble_examples],
        "mac_examples": [b.decode("ascii", "replace") for b in mac_examples],
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def find_latest_batch() -> Optional[Path]:
    root = ARGUS_ROOT / "raw" / "academic"
    candidates = [p for p in root.iterdir()
                  if p.is_dir() and not p.name.startswith("_")
                  and re.match(r"\d{8}T\d{6}Z", p.name)]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def main(batch_dir: Optional[Path] = None) -> int:
    if batch_dir is None:
        batch_dir = find_latest_batch()
    if batch_dir is None or not batch_dir.exists():
        print("No academic batch found.", file=sys.stderr)
        return 1
    manifest_path = batch_dir / "_manifest.json"
    if not manifest_path.exists():
        print(f"No manifest at {manifest_path}", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text())

    cohort_results: dict[str, dict] = {}
    file_results: list[dict] = []
    advisory_per_cohort: dict[str, dict[str, int]] = {}

    # Iterate cohorts from manifest
    for cohort in manifest.get("cohorts", []):
        cname = cohort.get("label", "?")
        # Aggregate accumulator
        agg = {"files": 0, "raw_bytes": 0, "clean_bytes": 0,
               "ble_kw": 0, "mac_kw": 0, "ssid_kw": 0, "default_creds_kw": 0,
               "uuid_total": 0, "mac_total": 0, "fcc_id_total": 0,
               "ble_uuid_anchored": 0, "mac_anchored": 0, "fcc_id_anchored": 0,
               "person_prefix_count": 0, "et_al_count": 0,
               "files_skipped": 0, "files_status_200": 0}
        adv_agg: dict[str, int] = {k: 0 for k in ADVISORY_TARGETS}

        # Walk papers in this cohort
        papers = cohort.get("papers_fetched", [])
        for paper in papers:
            # Each paper has landing_entry/abs_entry + pdf_entry
            for entry_key in ("pdf_entry", "landing_entry", "abs_entry"):
                ent = paper.get(entry_key)
                if not ent or ent.get("skip"):
                    continue
                if ent.get("status") not in (200, None) and not ent.get("cached_skip"):
                    # Status outside 200 — skip but count
                    agg["files_skipped"] += 1
                    continue
                rel = ent.get("raw_path_relative")
                if not rel:
                    agg["files_skipped"] += 1
                    continue
                fpath = ARGUS_ROOT / rel
                if not fpath.exists() or fpath.stat().st_size == 0:
                    agg["files_skipped"] += 1
                    continue
                ct = ent.get("content_type", "")
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
                for k in ("raw_bytes", "clean_bytes",
                          "ble_kw", "mac_kw", "ssid_kw", "default_creds_kw",
                          "uuid_total", "mac_total", "fcc_id_total",
                          "ble_uuid_anchored", "mac_anchored", "fcc_id_anchored",
                          "person_prefix_count", "et_al_count"):
                    agg[k] += s[k]
                for vendor, n in s["vendor_mentions"].items():
                    adv_agg[vendor] = adv_agg.get(vendor, 0) + n
                file_results.append({
                    "cohort": cname,
                    "file": rel,
                    "kind": entry_key,
                    "soi_keyword": paper.get("soi_keyword"),
                    "title": paper.get("title"),
                    "content_type": ct,
                    **{k: v for k, v in s.items()
                       if k not in ("vendor_mentions",)},
                    "vendor_mentions": s["vendor_mentions"],
                })
        cohort_results[cname] = agg
        advisory_per_cohort[cname] = adv_agg

    # Wave aggregate
    wave_agg = {k: 0 for k in next(iter(cohort_results.values())).keys()} \
               if cohort_results else {}
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
                             "files": agg.get("files", 0)})

    # N=2 consecutive zero-cohort floor
    consecutive_zero = 0
    max_consecutive = 0
    for ct in cohort_trips:
        if ct["trip"]:
            consecutive_zero += 1
            max_consecutive = max(max_consecutive, consecutive_zero)
        else:
            consecutive_zero = 0

    # SAR-6 #3 stop-line: ≤1.5 wave-aggregate vendor-gated rows = trip
    wave_vendor_gated = (wave_agg.get("ble_uuid_anchored", 0)
                         + wave_agg.get("mac_anchored", 0)
                         + wave_agg.get("fcc_id_anchored", 0))
    sar6_3_trip = wave_vendor_gated <= 1.5

    # ---- Outputs ----
    ts_now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ARGUS_ROOT / "raw" / "academic" / "_step1_survey" / ts_now
    out_dir.mkdir(parents=True, exist_ok=True)

    # Text log
    lines = [
        f"MAC-28 Wave-C Step 1.5b — byte-level survey ({ts_now})",
        "=" * 78,
        f"Batch: {batch_dir.relative_to(ARGUS_ROOT)}",
        f"Wave HTTP calls used: {manifest.get('wave_calls_used')}/{manifest.get('caps', {}).get('wave', '?')}",
        f"Per-host calls: {json.dumps(manifest.get('per_host_calls_used', {}))}",
        "",
        "Methodology:",
        "  * pdfminer.six text extraction for PDFs; HTML tag-strip for HTML.",
        "  * 5 anchors:",
        "      - ble_uuid_anchored: UUID-shape ±200 chars from BLE/Bluetooth/GATT/UUID kw",
        "      - mac_anchored: MAC-shape ±200 chars from MAC/hardware-addr/OUI/BLE kw",
        "      - ssid_kw: SSID/wifi/wi-fi/WPA[12]/probe-request kw count",
        "      - default_creds_kw: default-(pwd|user|cred|admin)/factory-default/admin[:=]/pwd[:=]/hard-coded",
        "      - fcc_id_anchored: \\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\\b ±50 chars from vendor-of-interest token",
        "  * Vendor-proximity ±50 chars (per MAC-23 precedent).",
        "  * PII redaction: person-name patterns counted, not stored.",
        "",
        f"{'cohort':<25s}{'files':>6s}{'200':>5s}{'skip':>5s}{'rawKB':>9s}"
        f"{'cleanKB':>9s}{'ble':>5s}{'mac':>5s}{'ssid':>5s}{'cred':>5s}"
        f"{'uuid':>6s}{'mac#':>6s}{'fcc#':>6s}{'u_anc':>7s}{'m_anc':>7s}{'f_anc':>7s}"
        f"{'pers':>6s}{'etal':>6s}",
        "-" * 145,
    ]
    for cname, agg in cohort_results.items():
        lines.append(
            f"{cname:<25s}"
            f"{agg.get('files',0):>6d}{agg.get('files_status_200',0):>5d}"
            f"{agg.get('files_skipped',0):>5d}"
            f"{agg.get('raw_bytes',0)//1024:>9d}{agg.get('clean_bytes',0)//1024:>9d}"
            f"{agg.get('ble_kw',0):>5d}{agg.get('mac_kw',0):>5d}"
            f"{agg.get('ssid_kw',0):>5d}{agg.get('default_creds_kw',0):>5d}"
            f"{agg.get('uuid_total',0):>6d}{agg.get('mac_total',0):>6d}"
            f"{agg.get('fcc_id_total',0):>6d}"
            f"{agg.get('ble_uuid_anchored',0):>7d}"
            f"{agg.get('mac_anchored',0):>7d}"
            f"{agg.get('fcc_id_anchored',0):>7d}"
            f"{agg.get('person_prefix_count',0):>6d}"
            f"{agg.get('et_al_count',0):>6d}"
        )
    lines.append("-" * 145)
    lines.append(
        f"{'WAVE TOTAL':<25s}"
        f"{wave_agg.get('files',0):>6d}{wave_agg.get('files_status_200',0):>5d}"
        f"{wave_agg.get('files_skipped',0):>5d}"
        f"{wave_agg.get('raw_bytes',0)//1024:>9d}{wave_agg.get('clean_bytes',0)//1024:>9d}"
        f"{wave_agg.get('ble_kw',0):>5d}{wave_agg.get('mac_kw',0):>5d}"
        f"{wave_agg.get('ssid_kw',0):>5d}{wave_agg.get('default_creds_kw',0):>5d}"
        f"{wave_agg.get('uuid_total',0):>6d}{wave_agg.get('mac_total',0):>6d}"
        f"{wave_agg.get('fcc_id_total',0):>6d}"
        f"{wave_agg.get('ble_uuid_anchored',0):>7d}"
        f"{wave_agg.get('mac_anchored',0):>7d}"
        f"{wave_agg.get('fcc_id_anchored',0):>7d}"
        f"{wave_agg.get('person_prefix_count',0):>6d}"
        f"{wave_agg.get('et_al_count',0):>6d}"
    )
    lines.append("")
    lines.append("Per-cohort vendor-gated row count + trip evaluation:")
    lines.append("-" * 78)
    for ct in cohort_trips:
        verdict = "TRIP (0 vendor-gated)" if ct["trip"] else f"OK ({ct['vendor_gated_rows']} rows)"
        lines.append(f"  {ct['cohort']:<25s} files={ct['files']:>3d}  vendor_gated={ct['vendor_gated_rows']:>3d}  {verdict}")
    lines.append("")
    lines.append(f"Wave-aggregate vendor-gated rows: {wave_vendor_gated}")
    lines.append(f"SAR-6 #3 ≤1.5 stop-line: {'TRIP' if sar6_3_trip else 'no trip'}")
    lines.append(f"N=2 consecutive zero-cohort floor: max_consecutive={max_consecutive} ({'TRIP (≥2)' if max_consecutive >= 2 else 'no trip'})")
    lines.append("")
    lines.append("Standing-advisory cross-source vendor mentions (count, not filter):")
    lines.append("-" * 78)
    for vendor in ADVISORY_TARGETS:
        per_c = ", ".join(f"{c}={advisory_per_cohort[c].get(vendor, 0)}"
                          for c in advisory_per_cohort)
        lines.append(f"  {vendor:<35s} wave_total={wave_advisory.get(vendor, 0):>5d}   per-cohort: {per_c}")
    lines.append("")
    lines.append("PII redaction discipline: person-name PREFIX counts (Mr/Dr/Sgt/Officer/etc) and"
                 " et-al counts only. NO names stored in survey output.")

    txt_path = out_dir / "_byte_level_survey.txt"
    txt_path.write_text("\n".join(lines) + "\n")

    # JSON sidecar
    json_path = out_dir / "_byte_level_survey.json"
    json_path.write_text(json.dumps({
        "issue": "MAC-28",
        "phase": "Phase 4 Wave-C Step 1.5b",
        "captured_at_utc": ts_now,
        "batch": str(batch_dir.relative_to(ARGUS_ROOT)),
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
        "pii_redaction_notes": "person-name prefix patterns counted, not stored;"
                               " researcher names: count-not-name default per §11 #3 + SAR-5",
    }, indent=2))

    print("\n".join(lines))
    print(f"\nText log: {txt_path}")
    print(f"JSON sidecar: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
