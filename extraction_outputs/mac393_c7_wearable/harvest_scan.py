#!/usr/bin/env python3
"""MAC-400 cohort-7 (continuous-broadcast wearables) — reproducible harvest scan.

STAGE ONLY. Read-only. Re-verifies:
  1. sha256 of the two pinned BT SIG registry files.
  2. Every vendor lead is a literal cite-paste from the pinned file (with line no.).
  3. Fitbit / Whoop genuine absence (grep == 0).
  4. DB-presence (db/argus.db mode=ro) for every lead — confirms net-new == 0.

Run:  .venv/bin/python extraction_outputs/mac393_c7_wearable/harvest_scan.py
No DB write, no ingest, no push. Bible §7.2 / §11 #1 / source-triage §11.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "extraction_outputs" / "mac393_c7_wearable" / "sources.json"
DB = ROOT / "db" / "argus.db"

PINS = {
    "raw/bluetooth_sig/20260613T203034Z_company_identifiers.yaml":
        "51b1ea7ddf98906df1538af7406dd7bea7c905a7d2f5cebcf4eb63c72447b5a0",
    "raw/bluetooth_sig/20260613T203034Z_member_uuids.yaml":
        "42478df3da88f890d80d2a4ac46e01657c9515434c3ebae8ad72e8d921b55bf2",
}


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    fails: list[str] = []
    src = json.loads(SRC.read_text())

    # 1. sha pins
    print("== sha256 pins ==")
    for rel, want in PINS.items():
        got = sha256(ROOT / rel)
        ok = got == want
        fails += [] if ok else [f"sha mismatch {rel}"]
        print(f"  [{'OK' if ok else 'FAIL'}] {rel}")

    # 2. cite-faithfulness — each lead excerpt is a literal substring at its line
    print("== cite-paste (literal substring @ pinned line) ==")
    file_lines = {rel: (ROOT / rel).read_text().splitlines() for rel in PINS}
    leads = []
    for typ in ("ble_company_id", "ble_service_uuid"):
        leads += src["leads"][typ]["items"]
    for ld in leads:
        rel = ld["source_file"]
        ln = ld["source_line"]
        line = file_lines[rel][ln - 1]  # 1-indexed
        name_ok = ld["source_excerpt"] in line
        # value excerpt lives one line above the name line in both yaml shapes
        val_line = file_lines[rel][ln - 2]
        val_ok = ld["value_excerpt"] in val_line
        ok = name_ok and val_ok
        fails += [] if ok else [f"cite fail {ld['vendor']} {ld['value']}"]
        print(f"  [{'OK' if ok else 'FAIL'}] {ld['vendor']:<28} {ld['value']:<8} L{ln}")

    # 3. Fitbit / Whoop genuine absence
    print("== absent-vendor grep (must be 0) ==")
    blob = "\n".join("\n".join(v) for v in file_lines.values()).lower()
    for v in ("fitbit", "whoop"):
        cnt = blob.count(v)
        ok = cnt == 0
        fails += [] if ok else [f"{v} unexpectedly present ({cnt})"]
        print(f"  [{'OK' if ok else 'FAIL'}] {v} hits={cnt}")

    # 4. DB-presence — every lead already held (net-new == 0)
    print("== DB-presence (mode=ro) — all leads ALREADY_HELD, net-new==0 ==")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = con.cursor()
    net_new = 0
    for ld in leads:
        v = ld["value"].lower()
        forms = [v]
        if v.startswith("0x") and len(v) == 6:  # member uuid short -> also 128-bit
            forms.append(f"0000{v[2:]}-0000-1000-8000-00805f9b34fb")
        rows = cur.execute(
            "SELECT COUNT(*) FROM identifiers WHERE lower(identifier) IN (%s)"
            % ",".join("?" * len(forms)),
            forms,
        ).fetchone()[0]
        held = rows > 0
        if not held:
            net_new += 1
        fails += [] if held else [f"lead unexpectedly net-new {ld['value']}"]
        print(f"  [{'HELD' if held else 'NET-NEW'}] {ld['vendor']:<28} {ld['value']}")
    con.close()
    print(f"  -> net_new count = {net_new} (expected 0)")
    if net_new != 0:
        fails.append(f"net_new={net_new} != 0")

    print()
    if fails:
        print("RESULT: FAIL")
        for f in fails:
            print("  -", f)
        return 1
    print("RESULT: PASS — all pins, cite-paste, absences, and DB-presence verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
