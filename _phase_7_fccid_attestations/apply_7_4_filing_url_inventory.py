"""
Phase 7 §7.4 — 947 fccid.io filing URL inventory hand-off (v1.5.0 deep-mine).

709 (V2 Wave I.14b) + 238 (V3 Wave I.14c) = 947 fccid.io filing-document URLs
catalogued but NOT promoted. Each row goes to
`manufacturers.notes.v1_5_0_filing_url_inventory[]` for the canonical
manufacturer mapped from the FCC EAS grantee_name.

Per-entry payload (per dispatch §7.4):
  {filing_url, filing_id, grantee_code, equipment_class, captured_at_utc,
   source_dispatch='MAC-194', deep_mine_status='v1_5_0_pending'}

Single transaction; per-manufacturer UPDATE.

Dispatch ref: MAC-194 §7.4. Informational only at Stage 1.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DB_PATH = Path("/home/kev/argus/db/argus.db")
V2_INV_PATH = Path("/home/kev/argus-internal/wave_i_pre_v1/wave_i_14b_external_remine/diagnostic_outputs/fccid_io_filing_url_inventory.json")
V3_PLAN_PATH = Path("/home/kev/argus-internal/wave_i_pre_v1/wave_i_14c_unfreeze/EXTRACTION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json")
LOG_PATH = Path("/home/kev/argus/_phase_7_fccid_attestations/filing_url_inventory_log.md")

CAPTURED_AT_UTC = "2026-05-20T00:00:00Z"
SOURCE_DISPATCH = "MAC-194"

GRANTEE_TO_CANONICAL = {
    "Motorola Solutions, Inc.": "Motorola Solutions",
    "Sierra Wireless Inc.": "Sierra Wireless",
    "Sierra Wireless Inc": "Sierra Wireless",
    "Sierra Wireless, Inc.": "Sierra Wireless",
    "Sierra Wireless, Inc": "Sierra Wireless",
    "PARROT DRONE SAS": "Parrot",
    "SZ DJI BaiWang Technology Co.,Ltd": "DJI",
    "Cradlepoint, Inc.": "Cradlepoint",
    "Axon Enterprise, Inc": "Axon",
    "Harris Corporation": "Harris",
}


def extract_filing_id(filing_url: str) -> str | None:
    """Pull filing_id from fccid.io URL. Two known shapes:
    1) https://fccid.io/document.php?id=3250396  -> id=3250396
    2) https://fccid.io/<FCC_ID>/<DocType>/<Slug-<digits>>  -> trailing digits
    """
    try:
        parsed = urlparse(filing_url)
        qs = parse_qs(parsed.query)
        if "id" in qs and qs["id"]:
            return qs["id"][0]
        m = re.search(r"-(\d{6,})$", parsed.path)
        if m:
            return m.group(1)
    except Exception:
        return None
    return None


def main() -> None:
    v2_data = json.loads(V2_INV_PATH.read_text(encoding="utf-8"))
    v2_inv = v2_data["inventory"]
    assert v2_data.get("total_filing_urls") == len(v2_inv) == 709, f"V2 count mismatch: {v2_data.get('total_filing_urls')} / {len(v2_inv)}"

    v3 = json.loads(V3_PLAN_PATH.read_text(encoding="utf-8"))
    v3_inv = v3["fccid_io_extended_filing_url_inventory_for_v1_5_0"]
    assert len(v3_inv) == 238, f"V3 count mismatch: {len(v3_inv)}"

    # Build per-canonical-manufacturer entry list
    per_mfr: dict[str, list[dict]] = defaultdict(list)
    unmapped: list[dict] = []

    for source_wave, rows in [("wave_i_14b", v2_inv), ("wave_i_14c", v3_inv)]:
        for row in rows:
            gname = row["grantee_name"]
            canonical = GRANTEE_TO_CANONICAL.get(gname)
            if not canonical:
                unmapped.append({"source_wave": source_wave, "grantee_name": gname, "fcc_id": row.get("fcc_id"), "filing_url": row.get("filing_url")})
                continue
            entry = {
                "filing_url": row["filing_url"],
                "filing_id": extract_filing_id(row["filing_url"]),
                "grantee_code": row.get("grantee_code_3char"),
                "grantee_name": gname,
                "equipment_class": row.get("equipment_class_code"),
                "fcc_id": row.get("fcc_id"),
                "application_name": row.get("application_name"),
                "filing_anchor_label": row.get("filing_anchor_label"),
                "captured_at_utc": CAPTURED_AT_UTC,
                "source_dispatch": SOURCE_DISPATCH,
                "source_wave": source_wave,
                "deep_mine_status": "v1_5_0_pending",
            }
            per_mfr[canonical].append(entry)

    if unmapped:
        raise SystemExit(f"HALT: {len(unmapped)} URL inventory rows have grantee_name not in GRANTEE_TO_CANONICAL — {unmapped[:5]}")

    total_attached = sum(len(v) for v in per_mfr.values())
    assert total_attached == 947, f"total attached={total_attached} != 947"

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    per_mfr_summary: dict[str, dict] = {}

    try:
        cur.execute("BEGIN")
        for canonical_name, entries in sorted(per_mfr.items()):
            cur.execute("SELECT id, notes FROM manufacturers WHERE canonical_name=?", (canonical_name,))
            row = cur.fetchone()
            if not row:
                raise sqlite3.IntegrityError(f"HALT: manufacturers.canonical_name='{canonical_name}' not found")
            mfr_id, mfr_notes_text = row
            notes = json.loads(mfr_notes_text) if mfr_notes_text else {}

            existing_inv = notes.get("v1_5_0_filing_url_inventory", [])

            # Idempotency: skip entries already present (key on filing_url + source_dispatch)
            existing_keys = {(e.get("filing_url"), e.get("source_dispatch")) for e in existing_inv}
            new_entries = [e for e in entries if (e["filing_url"], e["source_dispatch"]) not in existing_keys]

            existing_inv.extend(new_entries)
            notes["v1_5_0_filing_url_inventory"] = existing_inv

            cur.execute("UPDATE manufacturers SET notes=? WHERE id=?", (json.dumps(notes), mfr_id))

            per_mfr_summary[canonical_name] = {
                "mfr_id": mfr_id,
                "v2_count": sum(1 for e in entries if e["source_wave"] == "wave_i_14b"),
                "v3_count": sum(1 for e in entries if e["source_wave"] == "wave_i_14c"),
                "total_in_payload": len(entries),
                "newly_appended": len(new_entries),
                "total_after_apply": len(existing_inv),
            }
        cur.execute("COMMIT")
    except sqlite3.Error as exc:
        cur.execute("ROLLBACK")
        raise SystemExit(f"§7.4 transaction failed: {exc}")

    log_lines = [
        "# Phase 7 §7.4 — fccid.io filing URL inventory hand-off log",
        "",
        "**Dispatch ref:** [MAC-194](/MAC/issues/MAC-194) §7.4",
        f"**Total URLs catalogued:** {total_attached} (Wave I.14b 709 + Wave I.14c 238)",
        "**Promoted to identifiers:** 0 (URL inventory is INFORMATIONAL only — feeds v1.5.0 deep-mine)",
        "**Stage shape:** `manufacturers.notes.v1_5_0_filing_url_inventory[]`",
        "",
        "## Per-manufacturer breakdown",
        "",
        "| canonical_name | mfr_id | V2 (I.14b) | V3 (I.14c) | newly_appended | total_after_apply |",
        "|---------------|-------:|-----------:|-----------:|---------------:|-----------------:|",
    ]
    for cname, s in sorted(per_mfr_summary.items()):
        log_lines.append(
            f"| {cname} | {s['mfr_id']} | {s['v2_count']} | {s['v3_count']} | {s['newly_appended']} | {s['total_after_apply']} |"
        )

    log_lines += [
        "",
        "## Grantee → canonical mapping table",
        "",
        "| FCC EAS grantee_name | canonical_name |",
        "|----------------------|----------------|",
    ]
    for g, c in sorted(GRANTEE_TO_CANONICAL.items()):
        log_lines.append(f"| {g} | {c} |")

    log_lines += [
        "",
        "## §11 discipline",
        "",
        "- §11 #1 (no fabrication) — plan-input data preserved; filing_id extracted from filing_url where parseable, else None.",
        "- §11 #7 (provenance) — each entry chains to dispatch + source_wave; URLs are first-party fccid.io links.",
        "- §11 #8 (no confidence drift) — no identifier promoted; no confidence assigned. URL inventory is informational scaffolding for v1.5.0.",
        "- §11 #14 — applies at v1.5.0 deep-mine time, not now.",
        "- SAR-13.5 — these are direct fccid.io scrape, no bucket-payload extraction; attribution_status not needed at this layer.",
        "",
    ]
    LOG_PATH.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"§7.4 OK: {total_attached} URLs attached across {len(per_mfr_summary)} manufacturers; log={LOG_PATH}")
    for cname, s in sorted(per_mfr_summary.items()):
        print(f"  {cname}: V2={s['v2_count']} V3={s['v3_count']} new={s['newly_appended']}")


if __name__ == "__main__":
    main()
