#!/usr/bin/env python3
"""MAC-399 cohort-6 (pet/kid cellular trackers) HARVEST scan — reproducible harness.

STAGE ONLY. No DB write, no ingest, no push. Re-derives the cite-pasted leads in
`harvest.md` / `sources.json` from the pinned source artifacts:

  * 4 companion APKs under raw/vendor_apps/<vendor>/ (gitignored, §11 #15 facts-only)
  * IEEE OUI registry  raw/ieee_oui/20260613T203034Z_oui.csv      (sha fad18e77...)
  * BT SIG registries  raw/bluetooth_sig/20260613T203034Z_*.yaml

Method (per CTO source-triage §11 cite-paste discipline):
  - dex-only string scan for 128-bit UUIDs (res/asset false-positives excluded;
    only classes*.dex are read).
  - classify each UUID: vendor-proprietary GATT family / SIG-standard / known
    cross-vendor FP magnet / framework marker.
  - IEEE exact-org grep for the four vendors.
  - DB-presence (read-only mode=ro) for every candidate value.

Run:  .venv/bin/python extraction_outputs/mac393_c6_petkid/harvest_scan.py
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import zipfile
from pathlib import Path

ROOT = Path("/home/kev/argus")
UUID_RE = re.compile(
    rb"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
SIG_BASE = "-0000-1000-8000-00805f9b34fb"  # Bluetooth SIG 16-bit base UUID

# pinned APK provenance (sha256 + version from AndroidManifest via aapt)
APKS = {
    "fi": {
        "pkg": "com.barkinglabs.fi", "ver": "3.107.0",
        "sha": "72bcbcfd9d6f481d037ae99a5a23c26d2f0755f5d8c38d7aed201a27a35ea753",
        "xapk_base": "com.barkinglabs.fi.apk",
    },
    "jiobit": {
        "pkg": "com.jiobit.app", "ver": "1.26.2",
        "sha": "767e55e406f48f235c2e9d7446beb5b4f945381cddee012a8c99446d538f76ba",
        "xapk_base": "com.jiobit.app.apk",
    },
    "angelsense": {
        "pkg": "com.angelsense.mobile", "ver": "4.2.0",
        "sha": "0a49bff48ee2a233d4e961ed5e596b43086cdb404c38085317f3e580b14a13ca",
        "xapk_base": None,
    },
    "whistle": {
        "pkg": "com.whistle.bolt", "ver": "5.11.0.7264",
        "sha": "16acee8ff4338921ede7069e112750efd7d30d04ec0518f63190b2d011f518ac",
        "xapk_base": None,
    },
}

# net-new vendor GATT families (first-segment prefix that identifies the family)
VENDOR_FAMILY = {
    "fi": [("57b4", "Fi proprietary GATT base ...-2528-d6bc-b043-b49af0ec06c1")],
    "jiobit": [
        ("d8ecdb", "Jiobit proprietary GATT base ...-ddb6-4ffd-8f65-753cb9dc2e8a"),
        ("0000db01", "Jiobit 0xDB01 short-form custom service"),
        ("4a000000-0000-1000-8000-00805f4a494f",
         "Jiobit 'JIO'-ASCII custom UUID (...00805f4a494f)"),
    ],
    # 3 GATT families unique to Whistle's dex (multi-generation: 3/GO/Switch),
    # co-located with com/whistle/bluetooth/android/WhistleCoreBleUtils
    "whistle": [
        ("00002760-08c2-11e1-9073-0e8ac72e", "Whistle GATT family A"),
        ("d7895ab1-acc7-4de3-b991-9e825c24c8", "Whistle GATT family B"),
        # 'XXc8245c-829e-91b9-...' — first byte increments; match on shared tail
    ],
    "angelsense": [],  # cellular-only; 2 UUIDs are library/unattributed (FP-triage)
}

# known false-positives to exclude (cross-vendor magnets / framework markers)
FP_EXCLUDE = {
    "258eafa5-e914-47da-95ca-c5ab0dc85b11": "cross-vendor FP magnet (c1+c2+c6)",
    "95ed6082-b8e9-46e8-a73f-ff56f00f5d9d": "androidx.work.Data internal id (not BLE)",
    "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed": "urn:uuid namespace marker (not BLE)",
    "00000000-0000-0000-0000-000000000000": "null UUID",
    "00000000-deca-fade-deca-deafdecacafe": "library placeholder UUID",
    "5eb5a37e-b458-11e3-ac11-000c2940e62c": "beacon-library example region UUID",
    "b2f7f966-d8cc-11e4-bed1-df8f05be55ba": "beacon-library example region UUID",
    "00ffffff-ffff-ffff-ffff-ffffffffffff": "all-ones mask/placeholder UUID",
}
# vendor GATT families matched by a fixed TAIL (first byte/segment varies) — Whistle
VENDOR_FAMILY_TAIL = {
    "whistle": [("c8245c-829e-91b9-e34d-c7acb15a89d7",
                 "Whistle GATT family C (XXc8245c-... first-byte-incrementing)")],
}
# cross-vendor: Tile UUIDs referenced by Jiobit (Life360 owns both) — HELD already
TILE_HELD = {"0000feec" + SIG_BASE: "Tile 0xFEEC (HELD bluetooth_tracker)",
             "0000feed" + SIG_BASE: "Tile 0xFEED (HELD bluetooth_tracker)"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def apk_path(vendor: str) -> Path:
    m = APKS[vendor]
    return ROOT / "raw/vendor_apps" / vendor / m["pkg"] / m["ver"] / f"{m['sha']}.apk"


def dex_uuids(vendor: str) -> set[str]:
    """Distinct lowercase 128-bit UUIDs across all classes*.dex of the APK."""
    m = APKS[vendor]
    found: set[str] = set()
    with zipfile.ZipFile(apk_path(vendor)) as z:
        # XAPK bundle: read base apk's dex; plain APK: read its dex directly
        if m["xapk_base"]:
            with z.open(m["xapk_base"]) as f:
                inner = zipfile.ZipFile(__import__("io").BytesIO(f.read()))
                names = [n for n in inner.namelist() if re.fullmatch(r"classes\d*\.dex", n)]
                for n in names:
                    found |= {x.decode().lower() for x in UUID_RE.findall(inner.read(n))}
        else:
            names = [n for n in z.namelist() if re.fullmatch(r"classes\d*\.dex", n)]
            for n in names:
                found |= {x.decode().lower() for x in UUID_RE.findall(z.read(n))}
    return found


def classify(vendor: str, uuids: set[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"vendor_family": [], "sig_standard": [],
                                 "fp_excluded": [], "tile_held": [], "unattributed": []}
    fams = VENDOR_FAMILY.get(vendor, [])
    tails = VENDOR_FAMILY_TAIL.get(vendor, [])
    for u in sorted(uuids):
        if u in FP_EXCLUDE:
            out["fp_excluded"].append(u)
        elif u in TILE_HELD:
            out["tile_held"].append(u)
        elif any(u.startswith(pref) for pref, _ in fams) or \
                any(u.endswith(t) for t, _ in tails):
            out["vendor_family"].append(u)
        elif u.endswith(SIG_BASE):
            out["sig_standard"].append(u)
        else:
            out["unattributed"].append(u)
    return out


def db_held(cur: sqlite3.Cursor, val: str) -> list[tuple]:
    return cur.execute(
        "SELECT id,identifier_type,device_category,manufacturer "
        "FROM identifiers WHERE lower(identifier)=lower(?)", (val,)).fetchall()


def main() -> None:
    print("== sha256 provenance pins ==")
    for v in APKS:
        p = apk_path(v)
        ok = "OK" if sha256(p) == APKS[v]["sha"] else "!!MISMATCH"
        print(f"  {v:11s} {APKS[v]['pkg']} v{APKS[v]['ver']}  {ok}")
    oui_csv = ROOT / "raw/ieee_oui/20260613T203034Z_oui.csv"
    print(f"  IEEE oui.csv sha={sha256(oui_csv)[:16]}  (expect fad18e776a33e445)")

    con = sqlite3.connect(f"file:{ROOT/'db/argus.db'}?mode=ro", uri=True)
    cur = con.cursor()

    print("\n== BLE UUID classification (dex-only) ==")
    for v in APKS:
        c = classify(v, dex_uuids(v))
        print(f"\n  [{v}] vendor_family={len(c['vendor_family'])} "
              f"sig_std={len(c['sig_standard'])} fp={len(c['fp_excluded'])} "
              f"tile_held={len(c['tile_held'])} unattributed={len(c['unattributed'])}")
        for u in c["vendor_family"]:
            held = db_held(cur, u)
            print(f"     NET-NEW vendor {u}  {'HELD'+str(held) if held else '(net-new)'}")
        for u in c["unattributed"]:
            print(f"     UNATTRIBUTED (FP-triage) {u}")
        for u in c["tile_held"]:
            print(f"     CROSS-VENDOR Tile/HELD {u} -> {db_held(cur, u)}")

    print("\n== IEEE OUI exact-org grep (4 vendors) ==")
    for ln, line in enumerate(oui_csv.read_text(errors="replace").splitlines(), 1):
        if re.search(r"Whistle Labs|Jiobit|AngelSense|Barking Labs", line, re.I):
            assign = line.split(",")[1] if "," in line else "?"
            print(f"  oui.csv:{ln}  {line.strip()}  -> "
                  f"{'HELD' if db_held(cur, assign) else 'NET-NEW'}")

    con.close()


if __name__ == "__main__":
    main()
