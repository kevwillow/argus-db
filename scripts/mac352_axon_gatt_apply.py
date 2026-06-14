#!/usr/bin/env python3
"""MAC-352 WS-3 APK landing — 5 Axon body-cam BLE GATT admits (idempotent stage-only apply).

Board-ratified 2026-06-14 (confirmation 879bbc33, no conditions): admit the 5 Axon rows,
DEFER the advertised-service-data policy (-> MAC-416), confirm device_category=body_cam.
The cross-vendor exclusion CP already landed as CP44 in v1.6.8 (BIBLE_AMENDMENTS.md:5638) — this
write lands NO new CP; all 5 values pass CP44 (single-vendor com.axon.one; see mac350_uuid_struct_map.json).

Source: com.axon.one v2.2.1 (apkcombo xapk), sha256 8c50b57999258105ef8ed03707b9b6b3b51f810849feb86b65c57afbdbf5a016.
Trace (CTO-re-verified vs baksmali, MAC-352): 2 ble_service_uuid bind via client-side
BluetoothGattService.getUuid()==field-k (Lv8/d;/Lv8/c;); 3 ble_characteristic bind via
BluetoothGattCharacteristic.getUuid()==fields l/m/n (xh/d:197-225 -> v8/d ctor -> v8/c:1111).
RESOLVABLECAMFV1 (5245534f-...) DROPPED (advertised/scan-filter only -> MAC-416).

USAGE: python3 scripts/mac352_axon_gatt_apply.py [DB_PATH]
  DB_PATH default = db/argus.db (canonical). For the staged proof, pass a THROWAWAY COPY.
Idempotent: re-run after a successful apply detects all 5 present -> STOP exit 3 (no-op).
Partial presence -> ABORT exit 1. One transaction; rollback on any post-assert mismatch. NO push/tag.
"""
import json, sqlite3, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "db" / "argus.db"

# Fixed apply stamp -> deterministic byte-identical rows across re-runs on a copy.
# (Real canonical ingest at the board push-gate may restamp; idempotency holds on the
#  12 identity/provenance columns per the MAC-407 finding — only timestamps may differ.)
APPLY_UTC = "2026-06-14T21:30:00+00:00"
APK = "com.axon.one v2.2.1"
APK_SHA = "8c50b57999258105ef8ed03707b9b6b3b51f810849feb86b65c57afbdbf5a016"
DROP_UUID = "5245534f-4c56-4142-4c45-43414d465631"  # RESOLVABLECAMFV1 — must never appear

def note(decode, binding, field, trace):
    return json.dumps({
        "stage": "mac352_axon_gatt", "issue": "MAC-352", "board_ratified": "879bbc33",
        "applied_utc": APPLY_UTC, "vendor": "Axon", "ascii_decode": decode,
        "binding": binding, "gatt_field": field, "trace": trace,
        "cross_vendor_check": "single-vendor com.axon.one — passes CP44", "cp": "CP44",
        "apk": APK, "apk_sha256": APK_SHA, "device_family": "Axon body-worn camera (com.axon.aec.core)",
    })

# identifier, type, ascii, source_excerpt(<=200), notes
ROWS = [
    ("4d455452-4f50-4f4c-4953-444556494345", "ble_service_uuid", "METROPOLISDEVICE",
     'z8/d:33 const "4d455452-..."; v8/d:250 ->field k; v8/c:1045 BluetoothGattService.getUuid()==k (com.axon.one v2.2.1)',
     note("METROPOLISDEVICE", "gatt_service", "k", "v8/c:1045 getUuid()==Lv8/d;->k")),
    ("41584a41-4e55-5342-5743-444556494345", "ble_service_uuid", "AXJANUSBWCDEVICE",
     'f9/a:36 const "41584a41-..."; a9/e .super Lv8/d;; v8/c:1045 BluetoothGattService.getUuid()==k (com.axon.one v2.2.1)',
     note("AXJANUSBWCDEVICE", "gatt_service", "k", "a9/e .super Lv8/d;; v8/c:1045 getUuid()==k")),
    ("9ec5d2b8-8f51-4dea-9cd3-f3dea220b5e1", "ble_characteristic", "axon_char_1",
     'z8/d:58 const ->field E; xh/d:197-225 ->v8/d ctor p5->l; v8/c:1111 BluetoothGattCharacteristic.getUuid()==l (com.axon.one v2.2.1)',
     note("axon_char_1", "gatt_characteristic", "l", "xh/d->v8/d.l; v8/c:1144 getUuid()==l")),
    ("9ec5d2b8-8f51-4dea-9cd3-f3dea220b5e2", "ble_characteristic", "axon_char_2",
     'z8/d:79 const ->field F; xh/d:197-225 ->v8/d ctor p6->m; v8/c:1119 BluetoothGattCharacteristic.getUuid()==m (com.axon.one v2.2.1)',
     note("axon_char_2", "gatt_characteristic", "m", "xh/d->v8/d.m; v8/c:1192 getUuid()==m")),
    ("9ec5d2b8-8f51-4dea-9cd3-f3dea220b5e3", "ble_characteristic", "axon_char_3",
     'z8/d:100 const ->field G; xh/d:197-225 ->v8/d ctor p7->n; v8/c:1119 BluetoothGattCharacteristic.getUuid()==n (com.axon.one v2.2.1)',
     note("axon_char_3", "gatt_characteristic", "n", "xh/d->v8/d.n; v8/c:1168 getUuid()==n")),
]
SRC_URL = "apkcombo:com.axon.one__2.2.1__apkcombo.xapk"

def die(msg, code=1):
    print(f"ABORT: {msg}"); sys.exit(code)

for (_id, _t, _a, exc, _n) in ROWS:
    assert len(exc) <= 200, f"source_excerpt >200: {len(exc)} {exc}"

con = sqlite3.connect(str(DB)); con.execute("PRAGMA foreign_keys=ON"); cur = con.cursor()

def counts():
    return {
        "total": cur.execute("SELECT COUNT(*) FROM identifiers").fetchone()[0],
        "active": cur.execute("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL").fetchone()[0],
        "ble_service_uuid": cur.execute("SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_service_uuid'").fetchone()[0],
        "ble_characteristic": cur.execute("SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_characteristic'").fetchone()[0],
    }

pre = counts()
present = [r for r in ROWS if cur.execute(
    "SELECT 1 FROM identifiers WHERE identifier=? AND identifier_type=?", (r[0], r[1])).fetchone()]
if len(present) == len(ROWS):
    print("STOP: all 5 MAC-352 rows already present — idempotent no-op."); con.close(); sys.exit(3)
if present:
    die(f"partial presence ({len(present)}/5) — inconsistent state, human review needed")
if cur.execute("SELECT 1 FROM identifiers WHERE identifier=?", (DROP_UUID,)).fetchone():
    die("RESOLVABLECAMFV1 present in DB — must stay dropped")

try:
    cur.execute("BEGIN")
    for (ident, itype, _ascii, exc, notes) in ROWS:
        cur.execute(
            """INSERT INTO identifiers(identifier,identifier_type,device_category,manufacturer,model,
               confidence,source_url,source_type,source_excerpt,geographic_scope,first_seen,last_verified,notes)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ident, itype, "body_cam", "Axon", None, 70, SRC_URL, "manufacturer_app",
             exc, "global", APPLY_UTC, APPLY_UTC, notes))
    post = counts()
    if post["total"] != pre["total"] + 5: die(f"total {post['total']} != {pre['total']+5}")
    if post["active"] != pre["active"] + 5: die(f"active {post['active']} != {pre['active']+5}")
    if post["ble_service_uuid"] != pre["ble_service_uuid"] + 2: die("ble_service_uuid != +2")
    if post["ble_characteristic"] != pre["ble_characteristic"] + 3: die("ble_characteristic != +3")
    # key new-row checks on the stage marker (SRC_URL is shared by 7 pre-existing MAC-349 Axon rows)
    STAGE = "AND json_valid(notes) AND json_extract(notes,'$.stage')='mac352_axon_gatt'"
    n_stage = cur.execute(f"SELECT COUNT(*) FROM identifiers WHERE source_url=? {STAGE}", (SRC_URL,)).fetchone()[0]
    if n_stage != 5: die(f"json_valid+stage-marker rows: {n_stage}/5")
    ok = cur.execute(
        f"SELECT COUNT(*) FROM identifiers WHERE source_url=? {STAGE} AND manufacturer='Axon' AND confidence=70 AND device_category='body_cam'",
        (SRC_URL,)).fetchone()[0]
    if ok != 5: die(f"field invariants: {ok}/5 rows manufacturer=Axon conf=70 body_cam")
    if cur.execute("SELECT COUNT(*) FROM identifiers WHERE identifier=?", (DROP_UUID,)).fetchone()[0]:
        die("RESOLVABLECAMFV1 leaked into write")
    con.commit()
    print(json.dumps({"result": "COMMIT", "inserted": 5,
                      "pre": pre, "post": post,
                      "delta": {k: post[k]-pre[k] for k in pre}}, indent=2))
except SystemExit:
    con.rollback(); raise
except Exception as e:
    con.rollback(); die(f"exception, rolled back: {e}")
finally:
    con.close()
