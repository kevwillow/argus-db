#!/usr/bin/env python3
"""MAC-490 — Wave-3 CONSOLIDATED INGEST (CTO-led, board-AUTHORIZED) — canonical write.

Applies the board-ratified Wave-3 consolidated ingest slate (MAC-456 board go,
comment abc20255) to canonical ``db/argus.db``. Gate sequence:
per-lane ratify ✓ -> CEO roll-up ✓ -> board OK (MAC-456) ✓ -> INGEST (this script) ->
export regen (separate step) -> board PUSH (CEO/board-owned, NOT here). NO push, NO tag.

Board-approved slate applied here (DB-mutation half only — the CP47 §4.4 export-MAP
un-hold + the ble_local_name literal MAP are CODE changes applied to export_lynceus.py /
coverage_matrix.py, NOT here):

  Track A / CP47 (data-normalize half):
    - id23052 ble_company_id '67' -> '0x0043' (Parrot APK manufacturer-data filter).
      Couples with the held export-MAP un-hold patch; together = +2 std / +1 hc.

  Per-lane net-new admits (19 INSERT rows):
    B1 drones (4)  : 0000fffa-... ASTM Remote ID ble_service_uuid (drone);
                     org.opendroneid.remoteid wifi_aware_service_name (drone);
                     b0:30:c8 Teal oui (drone); 54:6f:71 uAvionix oui (drone).
                     NOTE: 0xFFFA is a Service-Data 16-bit UUID (BluetoothScanner.java:119
                     UUID.fromString("0000fffa-...")) -> ble_service_uuid. The MAC-458
                     "DONE" comment's 'ble_manufacturer_id' typing is a label-swap error,
                     corrected here per the source + the earlier detailed ratification.
    B2 cameras (1) : 30:f0:28 Bosch Sicherheitssysteme GmbH oui (cctv_camera).
    B3 LE/gov (3)  : 00:09:bc + 00:16:ed Utility, Inc oui (body_cam);
                     00003000-... Flock Raven svc ble_service_uuid (gunshot_detect).
    B4 locks (5)   : 78:9c:85 August; 00:17:7a ASSA ABLOY; 98:1b:b5 iRevo;
                     14:a1:bf Unilock; dc:c0:eb COTE PICARDE -> oui (smart_lock).
    B5 cam/door (5): 18:b4:30 + 64:16:66 Nest; 18:c2:3c + 54:ef:44 Lumi;
                     f8:51:28 SimpliSafe -> oui (unknown; §11#13 export-banned).
    B6 trackers (1): 15190001-... Google FMDN sound svc ble_service_uuid (bluetooth_tracker).
    B7 mesh        : DECLINE (ingest NOTHING — board ethics ruling).

  HOLD (NOT ingested here): 2 Lumi already in B5 as unknown (no double-count); ssid_pattern
  (Lynceus regex gap); B4 C1/C2/C3 recat/retype recommendations (separate board call, NOT in
  MAC-490 admit set); MAC-477 MSAL -8 (own gate).

Migration-safety: backup-first (timestamped + .sha256, gitignored db/argus.db*.bak);
re-query live baseline with STOP-on-out-of-band-drift; insert via AUTOINCREMENT (no explicit
id); fresh JSON notes (json.dumps, never text-suffix concat); json_valid sweep over every new
row; per-row lookup uniqueness (idempotent skip on (identifier, identifier_type)); full-column
reconstruction diff vs the backup; invariant rollback. Idempotent: re-run skips present rows;
CP47 normalize skips if id23052 already '0x0043'.

Usage:
  python3 scripts/mac490_wave3_ingest_apply.py --db <path> [--no-backup]
                                               [--expect-total N] [--expect-active N] [--force]

NO export regen here (separate step). NO push. NO tag. db/argus.db is gitignored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXPECT_TOTAL = 43810   # canonical baseline (post wave-2 mig 0033, schema 33)
EXPECT_ACTIVE = 43255  # active (superseded_by IS NULL)
EXPECT_SCHEMA = 33
ISSUE = "MAC-490"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
IEEE_URL = "https://standards-oui.ieee.org/oui/oui.txt"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def trunc(s, n=200):
    if s is None:
        return None
    return s if len(s) <= n else s[:n]


# ── CP47 normalize ────────────────────────────────────────────────────────────
CP47_ID = 23052
CP47_FROM = "67"
CP47_TO = "0x0043"

# ── 19 per-lane admit rows (cite-paste source_excerpt = exact bytes verified at author time) ──
def N(**extra):
    d = {"wave": "wave3", "ingest_issue": ISSUE, "applied_utc": NOW}
    d.update(extra)
    return json.dumps(d, ensure_ascii=False)


ROWS = [
    # B1 Drone Remote ID (MAC-458) — drone
    dict(identifier="0000fffa-0000-1000-8000-00805f9b34fb", identifier_type="ble_service_uuid",
         device_category="drone", manufacturer="Open Drone ID (ASTM F3411)", confidence=85,
         source_url="https://github.com/opendroneid/receiver-android",
         source_type="official", geographic_scope=None,
         source_excerpt='private static final UUID SERVICE_UUID = UUID.fromString("0000fffa-0000-1000-8000-00805f9b34fb"); // ASTM Remote ID (BluetoothScanner.java:119)',
         notes=N(lane="B1", issue="MAC-458", basis="ASTM F3411 spec-mandated Service-Data 16-bit UUID; vendor-agnostic", type_correction="MAC-458 DONE-comment 'ble_manufacturer_id' label-swap corrected to ble_service_uuid per source")),
    dict(identifier="org.opendroneid.remoteid", identifier_type="wifi_aware_service_name",
         device_category="drone", manufacturer="Open Drone ID (ASTM F3411)", confidence=85,
         source_url="https://github.com/opendroneid/receiver-android",
         source_type="official", geographic_scope=None,
         source_excerpt='new SubscribeConfig.Builder().setServiceName("org.opendroneid.remoteid").build(); // WiFiNaNScanner.java:94-96 (NAN service name)',
         notes=N(lane="B1", issue="MAC-458", basis="WiFi NAN service name; vendor-agnostic; first row of wifi_aware_service_name", retype="from worker ssid_pattern -> wifi_aware_service_name")),
    dict(identifier="b0:30:c8", identifier_type="oui",
         device_category="drone", manufacturer="Teal Drones, Inc.", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt='MA-L,B030C8,"Teal Drones, Inc.",5200 South Highland Drive Holladay  UT US 84117',
         notes=N(lane="B1", issue="MAC-458", basis="IEEE MA-L; drone-specific manufacturer; no OUI-share risk")),
    dict(identifier="54:6f:71", identifier_type="oui",
         device_category="drone", manufacturer="uAvionix Corporation", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt="MA-L,546F71,uAvionix Corporation,300 Pine Needle Lane Bigfork MT US 59911",
         notes=N(lane="B1", issue="MAC-458", basis="IEEE MA-L; drone transponder/ADS-B specialist; no OUI-share risk")),
    # B2 Fixed/cloud cameras (MAC-459) — cctv_camera
    dict(identifier="30:f0:28", identifier_type="oui",
         device_category="cctv_camera", manufacturer="Bosch Sicherheitssysteme GmbH", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt="MA-L,30F028,Bosch Sicherheitssysteme GmbH,Fritz-Schaffer-Strasse 9 Munich  DE 81737",
         notes=N(lane="B2", issue="MAC-459", basis="Bosch security-systems/camera subsidiary; surveillance-specific; Building-Automation+Access-Systems EXCLUDED/HELD")),
    # B3 LE/gov gear (MAC-460) — body_cam + gunshot_detect
    dict(identifier="00:09:bc", identifier_type="oui",
         device_category="body_cam", manufacturer="Utility, Inc", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt='MA-L,0009BC,"Utility, Inc",250 E Ponce de Leon Ave Suite 700 Decatur GA US 30030',
         notes=N(lane="B3", issue="MAC-460", basis="IEEE MA-L; Utility/BodyWorn BWC vendor (Decatur GA)")),
    dict(identifier="00:16:ed", identifier_type="oui",
         device_category="body_cam", manufacturer="Utility, Inc", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt='MA-L,0016ED,"Utility, Inc",250 E Ponce de Leon Ave Suite 700 Decatur GA US 30030',
         notes=N(lane="B3", issue="MAC-460", basis="IEEE MA-L; same Utility org block")),
    dict(identifier="00003000-0000-1000-8000-00805f9b34fb", identifier_type="ble_service_uuid",
         device_category="gunshot_detect", manufacturer="Flock Safety", confidence=75,
         source_url="https://github.com/colonelpanichacks/flock-you/blob/main/datasets/raven_configurations.json",
         source_type="crowdsourced", geographic_scope="US",
         source_excerpt='raven_configurations.json: 00003000-0000-1000-8000-00805f9b34fb = Raven device-info service (fw1.2.0+; Part/Serial/MAC chars)',
         notes=N(lane="B3", issue="MAC-460", basis="Flock Raven custom GATT service; single-source -> conf floor 75 per §8.3; sibling family 00003100/200/300 = ids 554/555/556")),
    # B4 Smart locks (MAC-461) — smart_lock
    dict(identifier="78:9c:85", identifier_type="oui",
         device_category="smart_lock", manufacturer="August Home, Inc.", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt='MA-L,789C85,"August Home, Inc.",657 Bryant Street San Francisco California US 94107',
         notes=N(lane="B4", issue="MAC-461", basis="Pure-play lock/doorbell vendor; wave-2 precedent (Kwikset/Yale oui smart_lock)")),
    dict(identifier="00:17:7a", identifier_type="oui",
         device_category="smart_lock", manufacturer="ASSA ABLOY AB", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt="MA-L,00177A,ASSA ABLOY AB,Theres Svenssons gata 15 Goteborg  SE 41755",
         notes=N(lane="B4", issue="MAC-461", basis="Access-control parent (Aperio/Hi-O); entire business is locks/access-control")),
    dict(identifier="98:1b:b5", identifier_type="oui",
         device_category="smart_lock", manufacturer="ASSA ABLOY Korea Co., Ltd iRevo", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt='MA-L,981BB5,"ASSA ABLOY Korea Co., Ltd iRevo",10F of JEI PLATZ Bldg., 186, Gasandigital-ro, Geumcheon-gu Seoul KR 08502',
         notes=N(lane="B4", issue="MAC-461", basis="Korean lock subsidiary (Gateman)")),
    dict(identifier="14:a1:bf", identifier_type="oui",
         device_category="smart_lock", manufacturer="ASSA ABLOY Korea Co., Ltd Unilock", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt='MA-L,14A1BF,"ASSA ABLOY Korea Co., Ltd Unilock",10f of JEI PLATZ Bldg., 186, Gasandigital 1-ro Geumcheon-gu Seoul KR 08502',
         notes=N(lane="B4", issue="MAC-461", basis="Same JEI PLATZ address as iRevo = Assa Abloy Korea lock op, NOT the paving brand")),
    dict(identifier="dc:c0:eb", identifier_type="oui",
         device_category="smart_lock", manufacturer="ASSA ABLOY COTE PICARDE", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt="MA-L,DCC0EB,ASSA ABLOY COTE PICARDE,rue Alexandre Fichet Oust-Marest  FR 80460",
         notes=N(lane="B4", issue="MAC-461", basis="VingCard/elSAFE hospitality access-control; residential-vs-hospitality subtype caveat")),
    # B5 Consumer cam/doorbell (MAC-462) — unknown (§11#13 export-banned)
    dict(identifier="18:b4:30", identifier_type="oui",
         device_category="unknown", manufacturer="Nest Labs Inc.", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt="MA-L,18B430,Nest Labs Inc.,3400 Hillview Ave. Palo Alto CA US 94304",
         notes=N(lane="B5", issue="MAC-462", basis="OUI->unknown default; export-suppressed; recat target=smart_home_hub if board sweep")),
    dict(identifier="64:16:66", identifier_type="oui",
         device_category="unknown", manufacturer="Nest Labs Inc.", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt="MA-L,641666,Nest Labs Inc.,3400 Hillview Ave. Palo Alto CA US 94304",
         notes=N(lane="B5", issue="MAC-462", basis="OUI->unknown default; export-suppressed")),
    dict(identifier="18:c2:3c", identifier_type="oui",
         device_category="unknown", manufacturer="Lumi United Technology Co., Ltd", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt='MA-L,18C23C,"Lumi United Technology Co., Ltd",JinQi Wisdom Valley LinXian Ave Nanshan ShenZhen CN 518055',
         notes=N(lane="B5", issue="MAC-462", basis="Aqara; B4 ruling = do NOT recat to smart_lock (camera/hub-dominant); single admission as unknown")),
    dict(identifier="54:ef:44", identifier_type="oui",
         device_category="unknown", manufacturer="Lumi United Technology Co., Ltd", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt='MA-L,54EF44,"Lumi United Technology Co., Ltd",JinQi Wisdom Valley LinXian Ave Nanshan ShenZhen CN 518055',
         notes=N(lane="B5", issue="MAC-462", basis="Aqara; do NOT recat to smart_lock; single admission as unknown")),
    dict(identifier="f8:51:28", identifier_type="oui",
         device_category="unknown", manufacturer="SimpliSafe", confidence=75,
         source_url=IEEE_URL, source_type="primary_registry", geographic_scope=None,
         source_excerpt="MA-L,F85128,SimpliSafe,294 Washington St Boston MA US 02108",
         notes=N(lane="B5", issue="MAC-462", basis="security-system parent; OUI->unknown; export-suppressed")),
    # B6 Personal trackers (MAC-463) — bluetooth_tracker
    dict(identifier="15190001-12f4-c226-88ed-2ac5579f2a85", identifier_type="ble_service_uuid",
         device_category="bluetooth_tracker", manufacturer="Google", confidence=85,
         source_url="https://github.com/seemoo-lab/AirGuard",
         source_type="academic", geographic_scope=None,
         source_excerpt="GoogleFindMyNetwork.kt::GOOGLE_SOUND_SERVICE_UUID = 15190001-12F4-C226-88ED-2AC5579F2A85 (FMDN anti-stalking sound service)",
         notes=N(lane="B6", issue="MAC-463", basis="Google Find My Device network sound service; first-party 128-bit; low FP; pro-safety countersurveillance")),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--expect-total", type=int, default=EXPECT_TOTAL)
    ap.add_argument("--expect-active", type=int, default=EXPECT_ACTIVE)
    ap.add_argument("--force", action="store_true", help="proceed despite baseline drift")
    args = ap.parse_args()
    DB: Path = args.db
    if not DB.exists():
        print(f"FATAL: db not found {DB}")
        return 2

    con = sqlite3.connect(str(DB), isolation_level=None)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    def one(sql, a=()):
        return cur.execute(sql, a).fetchone()[0]

    # ---- preconditions (STOP on out-of-band drift) ----
    schema = one("SELECT MAX(version) FROM schema_version")
    total = one("SELECT COUNT(*) FROM identifiers")
    active = one("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL")
    maxid = one("SELECT MAX(id) FROM identifiers")
    print(f"baseline: schema={schema} total={total} active={active} maxid={maxid}")
    drift = []
    if schema != EXPECT_SCHEMA:
        drift.append(f"schema {schema}!={EXPECT_SCHEMA}")
    if total != args.expect_total:
        drift.append(f"total {total}!={args.expect_total}")
    if active != args.expect_active:
        drift.append(f"active {active}!={args.expect_active}")
    if drift and not args.force:
        print(f"STOP: baseline drift {drift} (use --force to override)")
        return 3

    # ---- backup-first ----
    pre_sha = sha256_of(DB)
    print(f"pre-sha {pre_sha}")
    bak = None
    if not args.no_backup:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = DB.with_name(DB.name + f".mac490_pre_apply_{stamp}.bak")
        shutil.copy2(DB, bak)
        bak.with_name(bak.name + ".sha256").write_text(f"{pre_sha}  {bak.name}\n")
        print(f"backup -> {bak.name}")

    cur.execute("BEGIN")
    try:
        # ---- CP47 normalize (id23052 '67' -> '0x0043') ----
        r = cur.execute("SELECT identifier, identifier_type FROM identifiers WHERE id=?", (CP47_ID,)).fetchone()
        cp47 = "skip"
        if r is None:
            raise RuntimeError(f"CP47 precondition fail: id{CP47_ID} absent")
        if r["identifier_type"] != "ble_company_id":
            raise RuntimeError(f"CP47 precondition fail: id{CP47_ID} type={r['identifier_type']} != ble_company_id")
        if r["identifier"] == CP47_FROM:
            cur.execute("UPDATE identifiers SET identifier=? WHERE id=? AND identifier=? AND identifier_type='ble_company_id'",
                        (CP47_TO, CP47_ID, CP47_FROM))
            cp47 = "normalized 67->0x0043"
        elif r["identifier"] == CP47_TO:
            cp47 = "already 0x0043 (idempotent skip)"
        else:
            raise RuntimeError(f"CP47 precondition fail: id{CP47_ID} identifier={r['identifier']!r} not in (67,0x0043)")
        print(f"CP47 id{CP47_ID}: {cp47}")

        # ---- 19 lane INSERTs (idempotent on (identifier, identifier_type)) ----
        INS = ("INSERT INTO identifiers (identifier, identifier_type, device_category, manufacturer, "
               "confidence, source_url, source_type, source_excerpt, geographic_scope, first_seen, "
               "last_verified, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)")
        inserted, skipped, new_ids = [], [], []
        for row in ROWS:
            exists = cur.execute(
                "SELECT id FROM identifiers WHERE identifier=? AND identifier_type=?",
                (row["identifier"], row["identifier_type"])).fetchone()
            if exists:
                skipped.append((row["identifier"], row["identifier_type"], exists["id"]))
                continue
            cur.execute(INS, (
                row["identifier"], row["identifier_type"], row["device_category"], row["manufacturer"],
                row["confidence"], row["source_url"], row["source_type"], trunc(row["source_excerpt"]),
                row["geographic_scope"], NOW, NOW, row["notes"]))
            new_ids.append(cur.lastrowid)
            inserted.append((row["identifier"], row["identifier_type"], row["device_category"], cur.lastrowid))

        # ---- json_valid sweep over new rows ----
        if new_ids:
            ph = ",".join("?" * len(new_ids))
            bad = one(f"SELECT COUNT(*) FROM identifiers WHERE id IN ({ph}) AND json_valid(notes)=0", new_ids)
            if bad:
                raise RuntimeError(f"json_valid=0 on {bad} new rows")
            # source_excerpt length invariant (<=200 schema CHECK; belt-and-suspenders)
            longx = one(f"SELECT COUNT(*) FROM identifiers WHERE id IN ({ph}) AND length(source_excerpt)>200", new_ids)
            if longx:
                raise RuntimeError(f"source_excerpt>200 on {longx} new rows")
            # all new rows land above prior maxid (no id reuse)
            minnew = one(f"SELECT MIN(id) FROM identifiers WHERE id IN ({ph})", new_ids)
            if minnew <= maxid:
                raise RuntimeError(f"new id {minnew} collides with prior maxid {maxid}")

        # ---- reconstruction diff vs backup (only the intended deltas) ----
        recon_ok = True
        if bak is not None:
            bcon = sqlite3.connect(f"file:{bak}?mode=ro", uri=True)
            bcon.row_factory = sqlite3.Row
            pre_ids = {x[0] for x in bcon.execute("SELECT id FROM identifiers").fetchall()}
            post_ids = {x[0] for x in cur.execute("SELECT id FROM identifiers").fetchall()}
            added = post_ids - pre_ids
            deleted = pre_ids - post_ids
            # only changed row allowed = id23052 (CP47) when it was '67'
            pre_23052 = bcon.execute("SELECT identifier FROM identifiers WHERE id=?", (CP47_ID,)).fetchone()
            post_23052 = cur.execute("SELECT identifier FROM identifiers WHERE id=?", (CP47_ID,)).fetchone()
            bcon.close()
            changed_cp47 = (pre_23052["identifier"] != post_23052["identifier"])
            print(f"RECON vs backup: added={len(added)} deleted={len(deleted)} "
                  f"cp47_changed={changed_cp47} (pre={pre_23052['identifier']!r} post={post_23052['identifier']!r})")
            if deleted:
                recon_ok = False
                print(f"  FAIL: {len(deleted)} rows deleted (expected 0)")
            if added != set(new_ids):
                recon_ok = False
                print(f"  FAIL: added set != new_ids ({len(added)} vs {len(new_ids)})")

        print(f"\nINSERTED {len(inserted)}  SKIPPED {len(skipped)}  CP47 {cp47}")
        for t in inserted:
            print(f"  + id{t[3]:<6} {t[1]:<24} {t[2]:<16} {t[0]}")
        for s in skipped:
            print(f"  = SKIP (exists id{s[2]}) {s[1]:<24} {s[0]}")

        if not recon_ok:
            cur.execute("ROLLBACK")
            print("\nROLLED BACK (reconstruction invariant failed).")
            return 4

        cur.execute("COMMIT")
    except Exception as e:
        cur.execute("ROLLBACK")
        print(f"\nROLLED BACK: {e}")
        return 5

    post_sha = sha256_of(DB)
    post_total = one("SELECT COUNT(*) FROM identifiers")
    post_active = one("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL")
    print(f"\nCOMMITTED. post-sha {post_sha}")
    print(f"post: total={post_total} (+{post_total-total}) active={post_active} (+{post_active-active})")
    if bak is not None:
        print(f"backup={bak.name} pre-sha={pre_sha}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
