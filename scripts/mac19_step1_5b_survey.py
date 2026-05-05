"""MAC-19 Wave-B2 Step 1.5b byte-level survey gate.

Runs anchored regex sweep over the Step-1 fetched corpus to project Step-2
extraction yield BEFORE dispatching extraction. Per CEO ratification at
MAC-18: this is a GATE, not advisory — Step-2 dispatch waits for CEO
ratification of this survey.

Methodology mirrors MAC-16 (corpus survey) and MAC-18 (Step-0 sample survey):
  * For each persisted file: pdfminer.six text extraction (PDFs) or HTML tag-strip
  * 4 anchored signals:
      - ble_uuid_anchored: UUID-shape (8-4-4-4-12 hex) ±200 chars from
        BLE/Bluetooth/GATT/service-uuid keyword
      - mac_anchored: MAC-shape (xx:xx:xx:xx:xx:xx) ±200 chars from
        MAC-address/hardware-address/OUI keyword
      - ssid_kw_total: SSID/wifi/wi-fi/wireless-network/WPA[12]/password keyword
      - default_creds_kw: default-(password|username|credentials|admin) /
        factory-(default|reset) / admin[:=] / password[:=]

Output: logs/mac19_step1.5b_byte_level_survey_<run-timestamp>.txt + JSON sidecar
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

ARGUS_ROOT = Path(__file__).resolve().parent.parent
BATCH_DIR = ARGUS_ROOT / "raw" / "vendor_docs" / "20260505T143454Z"

BLE_KW = re.compile(rb"(?i)\b(?:bluetooth|ble|gatt|advertising|peripheral|service\s+uuid)\b")
SSID_KW = re.compile(rb"(?i)\b(?:ssid|wifi|wi-fi|wireless\s+network|default\s+network|wpa[12]?|password)\b")
MAC_KW = re.compile(rb"(?i)\b(?:mac\s*address|hardware\s*address|oui|mac\s*range)\b")
CRED_KW = re.compile(rb"(?i)\b(?:default\s+(?:password|username|credentials?|admin)|factory\s+(?:default|reset)|admin\s*[:=]|password\s*[:=])\b")
UUID_PAT = re.compile(rb"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
MAC_PAT = re.compile(rb"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
TAG_STRIP = re.compile(rb"<[^>]+>")
WS_COL = re.compile(rb"\s+")


def clean_bytes(raw: bytes, content_type: str | None, file_path: Path) -> bytes:
    """Extract text from PDF or strip HTML tags. Returns bytes."""
    if content_type and "pdf" in content_type.lower():
        try:
            from pdfminer.high_level import extract_text
            txt = extract_text(str(file_path)) or ""
            return txt.encode("utf-8", "replace")
        except Exception as e:
            print(f"  pdfminer FAIL on {file_path.name}: {e}", file=sys.stderr)
            return raw
    if content_type and ("html" in content_type.lower()
                        or "xml" in content_type.lower()):
        return WS_COL.sub(b" ", TAG_STRIP.sub(b" ", raw))
    # Fall back to raw — may include JSON / plain text
    return raw


def sweep_file(file_path: Path, content_type: str | None) -> dict:
    raw = file_path.read_bytes()
    clean = clean_bytes(raw, content_type, file_path)
    ble = len(BLE_KW.findall(clean))
    ssid = len(SSID_KW.findall(clean))
    mac = len(MAC_KW.findall(clean))
    cred = len(CRED_KW.findall(clean))
    uuids = list(UUID_PAT.finditer(clean))
    macs = list(MAC_PAT.finditer(clean))
    u_anch = sum(1 for m in uuids
                 if BLE_KW.search(clean[max(0, m.start()-200):m.end()+200])
                 or SSID_KW.search(clean[max(0, m.start()-200):m.end()+200]))
    m_anch = sum(1 for m in macs
                 if MAC_KW.search(clean[max(0, m.start()-200):m.end()+200])
                 or SSID_KW.search(clean[max(0, m.start()-200):m.end()+200])
                 or BLE_KW.search(clean[max(0, m.start()-200):m.end()+200]))
    return {"raw_bytes": len(raw), "clean_bytes": len(clean),
            "ble_kw": ble, "ssid_kw": ssid, "mac_kw": mac,
            "default_creds_kw": cred,
            "uuid_total": len(uuids), "mac_total": len(macs),
            "ble_uuid_anchored": u_anch, "mac_anchored": m_anch}


def main() -> int:
    manifest_path = BATCH_DIR / "_manifest.json"
    manifest = json.loads(manifest_path.read_text())

    cohort_results: dict[str, dict] = {}
    file_results: list[dict] = []

    for cohort_key, cohort_data in manifest["cohorts"].items():
        cohort_agg = {"files": 0, "raw_bytes": 0, "clean_bytes": 0,
                      "ble_kw": 0, "ssid_kw": 0, "mac_kw": 0,
                      "default_creds_kw": 0, "uuid_total": 0, "mac_total": 0,
                      "ble_uuid_anchored": 0, "mac_anchored": 0,
                      "files_status_200": 0, "files_skipped": 0}
        for ent in cohort_data["entries"]:
            if ent.get("status") != 200:
                cohort_agg["files_skipped"] += 1
                continue
            rel = ent.get("raw_path_relative")
            if not rel:
                cohort_agg["files_skipped"] += 1
                continue
            file_path = ARGUS_ROOT / rel
            if not file_path.exists() or file_path.stat().st_size == 0:
                cohort_agg["files_skipped"] += 1
                continue
            ct = ent.get("content_type", "")
            try:
                s = sweep_file(file_path, ct)
            except Exception as e:
                print(f"  sweep FAIL {file_path}: {e}", file=sys.stderr)
                cohort_agg["files_skipped"] += 1
                continue
            cohort_agg["files"] += 1
            cohort_agg["files_status_200"] += 1
            for k in ("raw_bytes", "clean_bytes", "ble_kw", "ssid_kw",
                      "mac_kw", "default_creds_kw", "uuid_total", "mac_total",
                      "ble_uuid_anchored", "mac_anchored"):
                cohort_agg[k] += s[k]
            file_results.append({
                "cohort": cohort_key, "file": rel,
                "vendor_slug": ent.get("vendor_slug"),
                "fcc_grantee": ent.get("fcc_grantee"),
                "content_type": ct, **s,
            })
        cohort_results[cohort_key] = cohort_agg

    # Wave aggregate
    wave_agg = {k: 0 for k in cohort_results[next(iter(cohort_results))].keys()}
    for c in cohort_results.values():
        for k, v in c.items():
            wave_agg[k] += v

    # ---- text log ----
    ts_now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = ARGUS_ROOT / f"logs/mac19_step1.5b_byte_level_survey_{ts_now}.txt"
    lines = [
        f"MAC-19 Wave-B2 Step 1.5b — byte-level survey ({ts_now})",
        "=" * 78,
        f"Batch: {BATCH_DIR.relative_to(ARGUS_ROOT)}",
        f"Total HTTP calls used: {manifest['aggregate_stats']['total_http_calls_used']}/120",
        "",
        "Methodology mirrors MAC-16 (corpus survey) + MAC-18 (Step-0 sample):",
        "  * pdfminer.six text extraction for PDFs; HTML tag-strip for HTML.",
        "  * 4 anchored signals:",
        "      - ble_uuid_anchored: UUID-shape ±200 chars from BLE/Bluetooth/GATT keyword",
        "      - mac_anchored: MAC-shape ±200 chars from MAC/hardware-address/OUI keyword",
        "      - ssid_kw_total: SSID/wifi/wi-fi/WPA[12]/password keyword",
        "      - default_creds_kw: default-(pwd|user|cred|admin)/factory-default/admin[:=]/password[:=]",
        "",
        f"{'cohort':<35s}{'files':>6s}{'200':>5s}{'skip':>5s}{'raw_KB':>9s}"
        f"{'clean_KB':>9s}{'ble':>5s}{'ssid':>5s}{'mac':>5s}{'cred':>5s}"
        f"{'uuid':>6s}{'mac#':>6s}{'u_anc':>7s}{'m_anc':>7s}",
        "-" * 110,
    ]
    for cohort_key in ["cohort1_dam_pdfs", "cohort2_droneshield_wayback",
                       "cohort3_hak5_wayback", "cohort4_cradlepoint_wayback",
                       "cohort5_fcc_pdfs", "cohort6_dji_sdk"]:
        c = cohort_results.get(cohort_key, {})
        if not c:
            continue
        lines.append(
            f"{cohort_key:<35s}"
            f"{c.get('files',0):>6d}{c.get('files_status_200',0):>5d}"
            f"{c.get('files_skipped',0):>5d}"
            f"{c.get('raw_bytes',0)//1024:>9d}{c.get('clean_bytes',0)//1024:>9d}"
            f"{c.get('ble_kw',0):>5d}{c.get('ssid_kw',0):>5d}"
            f"{c.get('mac_kw',0):>5d}{c.get('default_creds_kw',0):>5d}"
            f"{c.get('uuid_total',0):>6d}{c.get('mac_total',0):>6d}"
            f"{c.get('ble_uuid_anchored',0):>7d}{c.get('mac_anchored',0):>7d}"
        )
    lines.append("-" * 110)
    lines.append(
        f"{'WAVE TOTAL':<35s}"
        f"{wave_agg.get('files',0):>6d}{wave_agg.get('files_status_200',0):>5d}"
        f"{wave_agg.get('files_skipped',0):>5d}"
        f"{wave_agg.get('raw_bytes',0)//1024:>9d}{wave_agg.get('clean_bytes',0)//1024:>9d}"
        f"{wave_agg.get('ble_kw',0):>5d}{wave_agg.get('ssid_kw',0):>5d}"
        f"{wave_agg.get('mac_kw',0):>5d}{wave_agg.get('default_creds_kw',0):>5d}"
        f"{wave_agg.get('uuid_total',0):>6d}{wave_agg.get('mac_total',0):>6d}"
        f"{wave_agg.get('ble_uuid_anchored',0):>7d}{wave_agg.get('mac_anchored',0):>7d}"
    )
    lines.append("")
    lines.append("Per-cohort yield projection (Step-2 candidate rows):")
    lines.append("-" * 78)
    for cohort_key in ["cohort1_dam_pdfs", "cohort2_droneshield_wayback",
                       "cohort3_hak5_wayback", "cohort4_cradlepoint_wayback",
                       "cohort5_fcc_pdfs", "cohort6_dji_sdk"]:
        c = cohort_results.get(cohort_key, {})
        if not c:
            continue
        u = c.get("ble_uuid_anchored", 0)
        m = c.get("mac_anchored", 0)
        # Yield projection: anchored rows are the strongest signal; cred/ssid kw
        # presence may indicate tabular spec content but needs Step-2 confirmation.
        rows = u + m
        verdict = (
            "HIGH-yield (anchored UUID/MAC present)" if rows >= 5
            else "LOW-yield (no anchored UUID/MAC; absence-documented per §11 #1)"
            if rows == 0 else f"MARGINAL ({rows} anchored)"
        )
        lines.append(f"  {cohort_key:<35s} anchored_total={rows:>3d}   {verdict}")
    lines.append("")
    lines.append("Wave-aggregate projection vs Step-0 baseline:")
    lines.append(f"  Step-0 baseline (28 calls, 13 files): "
                 f"ble_kw=23, ssid_kw=19, ble_uuid_anchored=0, mac_anchored=0")
    lines.append(
        f"  Step-1 wave  ({wave_agg.get('files',0)} files): "
        f"ble_kw={wave_agg.get('ble_kw',0)}, "
        f"ssid_kw={wave_agg.get('ssid_kw',0)}, "
        f"ble_uuid_anchored={wave_agg.get('ble_uuid_anchored',0)}, "
        f"mac_anchored={wave_agg.get('mac_anchored',0)}"
    )
    lines.append("")
    lines.append("Stop-the-line evaluation (per CEO ratification at MAC-18):")
    lines.append("  Per-cohort SAR-6 #3 ~50% trip-line evaluated independently.")
    lines.append(
        f"  Two-consecutive-cohort wave-aggregate floor: "
        f"{'NO TRIP' if wave_agg.get('ble_uuid_anchored',0) + wave_agg.get('mac_anchored',0) >= 5 else 'NEEDS-CEO-EVAL'}"
    )

    log_path.write_text("\n".join(lines) + "\n")

    # ---- JSON sidecar ----
    json_path = ARGUS_ROOT / f"logs/mac19_step1.5b_byte_level_survey_{ts_now}.json"
    json_path.write_text(json.dumps({
        "captured_at_utc": ts_now,
        "batch": str(BATCH_DIR.relative_to(ARGUS_ROOT)),
        "total_http_calls_used": manifest["aggregate_stats"]["total_http_calls_used"],
        "wave_aggregate": wave_agg,
        "per_cohort": cohort_results,
        "per_file": file_results,
    }, indent=2))

    print("\n".join(lines))
    print(f"\nText log: {log_path}")
    print(f"JSON sidecar: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
