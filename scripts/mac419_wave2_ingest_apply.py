#!/usr/bin/env python3
"""MAC-419 — Wave-2 INGESTION (CTO-led, board-AUTHORIZED) — canonical shipped-registry write.

Applies the board-ratified wave-2 disposition slate (MAC-392 pre-ingestion-disposition
rev 2, accepted 2026-06-15 00:10) to canonical ``db/argus.db``. Gate sequence:
stage ✓ → board OK ingestion ✓ → INGEST (this script) → ship-gate regen →
gate #3 = board push approval (CEO-owned, NOT here). NO push, NO tag.

Board-approved slate applied here (and ONLY this):
  0. MINT  device_category 'smart_lock' + 'smart_home_hub' (migration 0033 / CP46,
     schema_version 32 → 33; dual-table parity).
  c4 smart locks : promote 2 oui (Kwikset 10:a4:50 / Yale b0:44:9c) + 54 GATT
                   ble_service_uuid  → smart_lock; RECAT U-tec id7200 → smart_lock.
                   HOLD 15 ambiguous + Spectrum/ASSA-GZ/Allegion + 6 BLE company-ids.
  c5 smart hubs  : promote SmartThings 24:fd:5b oui → smart_home_hub.
                   Nest 64:16:66 / 18:b4:30 = HOLD (absent; do NOT promote as new).
                   voice_assistant = HOLD (no mint).
  c6 pet/kid     : route 53 ble_service_uuid + 1 oui (E0:7C:62) + 5 ble_local_name
                   → gps_tracker + notes.subtype='pet_kid_cellular'.
  c1 spy-cams    : promote 10 clean ssid_pattern families → cctv_camera (crowdsourced
                   band + §8.3 +5 value-level lift, WiGLE-attested); 6 already-held
                   MA-M/MA-S → conflicts reason='potential_dedup_step_5' (NOT new oui
                   rows); 16 net-new SoC OUIs NOT ingested (no insert-ready provenance
                   in the staged artifacts; export-banned §8.4/§11 #13 either way).
                   HOLD 4 FP-magnet prefixes (IPCAM-/SKYEYE/HCAM/BVCAM).
  c3 BT-tracker  : promote +1 Pebblebee 0x0000FA25 ble_service_uuid → bluetooth_tracker
                   (the staged MAC-407 candidate, now authorized).
  c2 GPS / c7 wearables: ZERO promotion (wearable DEFERRED).

⚠ CTO ship-gate flag (surfaced, does NOT block ingestion): identifier_type
  'ssid_pattern' and 'ble_local_name' are §4.4 EXPORT-DROPPED (export_lynceus.py:97/115
  — "no regex in Lynceus v0.2"). So the c1 10 ssid families and the c6 5 ble_local_name
  rows are REGISTRY-INTERNAL only and reach the Lynceus FEED = 0, contrary to the
  disposition's "10 SSID families reach feed" headline. The rows are correctly
  categorized regardless; true feed deltas are reported at the regen step and decided
  at gate #3 (CEO/board).

Migration-safety: backup-first (timestamped + .sha256, gitignored); re-query live
baseline with STOP-on-out-of-band-drift; insert via AUTOINCREMENT (no explicit id →
new rows land 44502+, no collision with MAC-352 body_cam 44497-44501); fresh JSON
notes (json.dumps, never text-suffix concat); json_valid sweep over every new row;
per-cohort lookup-tuple uniqueness battery (identifier, identifier_type, source_url,
last_verified); full-column reconstruction diff vs the backup; invariant rollback.
Idempotent: schema rebuild skipped if enum already has smart_lock; every insert
skips on (identifier, identifier_type) presence; recat skips if already smart_lock;
each conflict skips if an identical (a_id, reason) row exists.

Usage:
  python3 scripts/mac419_wave2_ingest_apply.py --db <path> [--no-backup] [--expect-total N]

NO export regen here (separate ship-gate step). NO push. NO tag. db/argus.db gitignored.
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
EO = REPO / "extraction_outputs"
MIGRATION_SQL = REPO / "db" / "migrations" / "0033_cp46_device_category_smart_lock_smart_home_hub.sql"

EXPECT_TOTAL = 43683          # canonical baseline (MAC-392 rev2)
EXPECT_MAXID = 44501          # MAC-352 body_cam top id (untouched)
EXPECTED_NEW_ROWS = 127       # c1:10 + c3:1 + c4:56 + c5:1 + c6:59
EXPECTED_RECATS = 1           # c4 U-tec id7200
EXPECTED_CONFLICTS = 6        # c1 MA-M/MA-S dedup markers

IEEE_OUI_URL = "https://standards-oui.ieee.org/oui/oui.csv"
WIGLE_URL = "https://api.wigle.net/api/v2/network/search"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def trunc(s: str | None, n: int = 200) -> str | None:
    if s is None:
        return None
    return s if len(s) <= n else s[:n]


# ─────────────────────────── cohort row builders ───────────────────────────
# Each returns a list of dicts with the exact column values to INSERT.

def load(path: Path) -> dict:
    return json.loads(path.read_text())


def excerpt_of(cand: dict) -> str | None:
    if cand.get("source_excerpt"):
        return cand["source_excerpt"]
    sm = cand.get("source_markers")
    if isinstance(sm, dict) and sm.get("excerpt"):
        return sm["excerpt"]
    return None


def base_notes(cohort: str, issue: str, now: str, **extra) -> dict:
    n = {
        "stage": "mac419_wave2_ingest",
        "issue": issue,
        "applied_utc": now,
        "cohort": cohort,
        "gate": "board-AUTHORIZED ingestion (MAC-392 rev2); NO push; gate #3 = CEO",
    }
    n.update(extra)
    return n


def build_c4(now: str) -> list[dict]:
    d = load(EO / "mac393_c4_smartlock" / "candidates.json")
    rows = []
    for c in d["oui_candidates"]:
        if c.get("disposition") != "promote":
            continue
        rows.append({
            "identifier": c["identifier"], "identifier_type": "oui",
            "device_category": "smart_lock", "manufacturer": c.get("manufacturer"),
            "model": c.get("model"), "confidence": c["confidence"],
            "source_url": c["source_url"], "source_type": "primary_registry",
            "source_excerpt": trunc(excerpt_of(c)), "geographic_scope": c.get("geographic_scope", "global"),
            "notes": base_notes("MAC-393 c4 smart_lock", "MAC-419", now,
                                vendor=c.get("manufacturer"), band="primary_registry",
                                source_excerpt=excerpt_of(c),
                                lineage="MAC-397 harvest -> MAC-406 extraction (CTO-ratified) -> MAC-419 ingest",
                                extraction_notes=c.get("notes")),
        })
    for c in d["gatt_candidates"]:
        if c.get("disposition") != "promote":
            continue
        rows.append({
            "identifier": c["identifier"], "identifier_type": "ble_service_uuid",
            "device_category": "smart_lock", "manufacturer": c.get("manufacturer"),
            "model": c.get("model"), "confidence": c["confidence"],
            "source_url": c["source_url"], "source_type": "manufacturer_app",
            "source_excerpt": trunc(excerpt_of(c)), "geographic_scope": c.get("geographic_scope", "global"),
            "notes": base_notes("MAC-393 c4 smart_lock", "MAC-419", now,
                                vendor=c.get("manufacturer"), band="manufacturer_app",
                                source_excerpt=excerpt_of(c),
                                lineage="MAC-397 harvest -> MAC-406 extraction (CTO-ratified) -> MAC-419 ingest",
                                extraction_notes=c.get("notes")),
        })
    assert len(rows) == 56, f"c4 expected 56 promote rows, got {len(rows)}"
    return rows


def build_c5(now: str) -> list[dict]:
    # SmartThings 24:fd:5b — verified cite oui.csv:10918 (MAC-398 CTO-ratified).
    excerpt = 'MA-L,24FD5B,"SmartThings, Inc.",456 University Avenue Palo Alto CA US 94301'
    return [{
        "identifier": "24:fd:5b", "identifier_type": "oui",
        "device_category": "smart_home_hub", "manufacturer": "SmartThings, Inc.",
        "model": None, "confidence": 85,
        "source_url": IEEE_OUI_URL, "source_type": "primary_registry",
        "source_excerpt": trunc(excerpt), "geographic_scope": "global",
        "notes": base_notes("MAC-393 c5 smart_home_hub", "MAC-419", now,
                            vendor="SmartThings, Inc.", band="primary_registry",
                            cite="oui.csv:10918 MA-L 24FD5B 'SmartThings, Inc.'",
                            source_excerpt=excerpt,
                            disposition="pure-play smart-home-hub brand; ABSENT in DB -> net-new (MAC-398 CTO-ratified)",
                            lineage="MAC-398 harvest (CTO-ratified) -> MAC-419 ingest",
                            held_siblings="Nest 64:16:66 / 18:b4:30 HELD (absent; board: do NOT promote as new)"),
    }]


def build_c6(now: str) -> list[dict]:
    d = load(EO / "mac393_c6_petkid" / "candidates.json")
    rows = []
    for c in d["candidates"]:
        if c.get("disposition") != "promote":
            continue
        rows.append({
            "identifier": c["identifier"], "identifier_type": "ble_service_uuid",
            "device_category": "gps_tracker", "manufacturer": c.get("manufacturer"),
            "model": c.get("model"), "confidence": c["confidence"],
            "source_url": c["source_url"], "source_type": "manufacturer_app",
            "source_excerpt": trunc(excerpt_of(c)), "geographic_scope": c.get("geographic_scope", "global"),
            "notes": base_notes("MAC-393 c6 pet_kid", "MAC-419", now, subtype="pet_kid_cellular",
                                vendor=c.get("manufacturer"), band="manufacturer_app",
                                source_excerpt=excerpt_of(c),
                                lineage="MAC-399 harvest -> MAC-411 extraction (CTO-ratified) -> MAC-419 ingest",
                                routing="board: route to existing gps_tracker (route-not-mint)",
                                extraction_notes=c.get("notes")),
        })
    o = d["oui_candidate"]
    assert o.get("disposition") == "promote"
    rows.append({
        "identifier": o["identifier"], "identifier_type": "oui",
        "device_category": "gps_tracker", "manufacturer": o.get("manufacturer"),
        "model": o.get("model"), "confidence": o["confidence"],
        "source_url": o["source_url"], "source_type": "primary_registry",
        "source_excerpt": trunc(excerpt_of(o)), "geographic_scope": o.get("geographic_scope", "global"),
        "notes": base_notes("MAC-393 c6 pet_kid", "MAC-419", now, subtype="pet_kid_cellular",
                            vendor=o.get("manufacturer"), band="primary_registry",
                            source_excerpt=excerpt_of(o),
                            note="Whistle Labs OUI; present in raw_observations x2 (bulk IEEE/Wireshark, uncategorized) -> net-new vs identifiers",
                            lineage="MAC-399 harvest -> MAC-411 extraction (CTO-ratified) -> MAC-419 ingest"),
    })
    for c in d["ble_local_name_bonus"]:
        rows.append({
            "identifier": c["identifier"], "identifier_type": "ble_local_name",
            "device_category": "gps_tracker", "manufacturer": c.get("manufacturer"),
            "model": c.get("model"), "confidence": c["confidence"],
            "source_url": c["source_url"], "source_type": "manufacturer_app",
            "source_excerpt": trunc(excerpt_of(c)), "geographic_scope": c.get("geographic_scope", "global"),
            "notes": base_notes("MAC-393 c6 pet_kid", "MAC-419", now, subtype="pet_kid_cellular",
                                vendor=c.get("manufacturer"), band="manufacturer_app_behavioral",
                                disposition="bonus_low_confidence (conf 50)",
                                export="ble_local_name is §4.4 EXPORT-DROPPED -> registry-internal only",
                                source_excerpt=excerpt_of(c),
                                lineage="MAC-399 harvest -> MAC-411 extraction (CTO-ratified) -> MAC-419 ingest",
                                extraction_notes=c.get("notes")),
        })
    assert len(rows) == 59, f"c6 expected 59 rows, got {len(rows)}"
    return rows


# c1: 10 clean ssid_pattern families. Family -> (vendor, APK package, dex cite token).
C1_SSID = {
    "V380%":      ("V380 / Macrovideo", "com.macrovideo.v380pro",  "dex: V380_/V380_Pro + parseDeviceIDFormAPName"),
    "MVSPT%":     ("V380 / Macrovideo", "com.macrovideo.v380pro",  "dex: MVSPT_ vendor AP token (parseDeviceIDFormAPName)"),
    "iCSee%":     ("iCSee / Xiongmai",  "com.xm.csee",             "dex: iCSee / ICSEEHOME_NAME / XMWifiManager"),
    "CamHipro%":  ("CamHi / HiChip",    "com.hichip.campro",       "dex: CamHipro-%04d / HiGetIPCAM"),
    "HDMiniCam%": ("HDMiniCam / g_zhang","com.g_zhang.HDMiniCam",  "dex tokens + set_wifi.cgi"),
    "iMiniCam%":  ("HDMiniCam / g_zhang","com.g_zhang.HDMiniCam",  "dex ESNAPP_IMINICAM token"),
    "MATECAM%":   ("MateCam (ESNAPP)",  "com.g_zhang.HDMiniCam",   "dex ESNAPP_MATECAM enum (g_zhang white-label)"),
    "EUROSPY%":   ("EuroSpy (ESNAPP)",  "com.g_zhang.HDMiniCam",   "dex ESNAPP_EUROSPY enum (g_zhang white-label)"),
    "SPYSITE%":   ("SpySite (ESNAPP)",  "com.g_zhang.HDMiniCam",   "dex ESNAPP_SPYSITE enum (g_zhang white-label)"),
    "BLACKLENS%": ("BlackLens (ESNAPP)","com.g_zhang.HDMiniCam",   "dex ESNAPP_BLACKLENS enum (g_zhang white-label)"),
}


def build_c1(now: str) -> list[dict]:
    wig = load(EO / "mac393_c1_spycam" / "wigle_results.json")
    wild = {r["ssidlike"]: r.get("total_results_in_wild") for r in wig["results"]}
    rows = []
    for pat, (vendor, pkg, cite) in C1_SSID.items():
        w = wild.get(pat)
        excerpt = trunc(f"{cite}; WiGLE in-the-wild={w} ({pat})")
        rows.append({
            "identifier": pat, "identifier_type": "ssid_pattern",
            "device_category": "cctv_camera", "manufacturer": vendor,
            "model": None, "confidence": 70,  # crowdsourced base 65 + §8.3 +5 value-level lift
            "source_url": WIGLE_URL, "source_type": "crowdsourced",
            "source_excerpt": excerpt, "geographic_scope": "global",
            "notes": base_notes("MAC-393 c1 spy_cam", "MAC-419", now, vendor=vendor,
                                apk_package=pkg, originating_artifact=f"APK soft-AP default-SSID ({cite})",
                                wigle_attestation=f"{w} networks in the wild (LIVE pass MAC-417)",
                                confidence_basis="crowdsourced band 50-75: base 65 (WiGLE in-the-wild) "
                                "+ §8.3 +5 value-level lift (APK defines + WiGLE confirms SAME pattern value; "
                                "two independent issuers — value-level, NOT hub-and-spoke) = 70",
                                export="ssid_pattern is §4.4 EXPORT-DROPPED (no regex in Lynceus v0.2) -> "
                                "REGISTRY-INTERNAL only; reaches Lynceus feed = 0 (CTO ship-gate flag)",
                                lineage="MAC-394 harvest -> MAC-417 WiGLE -> MAC-418 Validator (all CTO-ratified) -> MAC-419 ingest"),
        })
    assert len(rows) == 10, f"c1 expected 10 ssid rows, got {len(rows)}"
    return rows


def build_c3(now: str) -> list[dict]:
    d = load(EO / "mac393_c3_bletracker" / "candidates.json")
    cands = [c for c in d["candidates"] if c.get("db_presence") == "net-new"]
    assert len(cands) == 1, f"c3 expected 1 net-new, got {len(cands)}"
    c = cands[0]
    sm = c["source_markers"]
    src_url = ("https://github.com/seemoo-lab/AirGuard/blob/main/app/src/main/java/de/seemoo/"
               "at_tracking_detection/database/models/device/types/PebbleBee.kt")
    return [{
        "identifier": c["value"], "identifier_type": c["identifier_type"],
        "device_category": c["device_category"], "manufacturer": c["manufacturer"],
        "model": None, "confidence": c["confidence"],
        "source_url": src_url, "source_type": "crowdsourced",
        "source_excerpt": trunc(sm["excerpt"]), "geographic_scope": None,
        "notes": base_notes("MAC-393 c3 bluetooth_tracker", "MAC-419", now, vendor=c["manufacturer"],
                            device_product="Pebblebee offline-finding (SOUND) service UUID",
                            source_sid=c.get("source_sid"),
                            cite_artifact=sm.get("artifact"), cite_line=sm.get("line"),
                            cite_artifact_sha256=sm.get("artifact_sha256"), source_excerpt=sm["excerpt"],
                            corroboration="SINGLE-SOURCE crowdsourced (AirGuard sid24); APK enrichment empty -> no §8.3 lift; conf 65 <= 75",
                            lineage="MAC-396 harvest -> MAC-403 extraction (CTO-ratified) -> MAC-407 staged -> MAC-419 ingest"),
    }]


# c1 dedup conflicts: 6 already-held MA-M/MA-S mac_range rows ↔ harvest SoC OUI value.
C1_CONFLICTS = [
    (5357, "6095CE6"), (7409, "F0D7AFA"), (9590, "10DCB69"),
    (11231, "8C1F64AE2"), (12437, "8C1F645F4"), (14553, "8C1F64C31"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(REPO / "db" / "argus.db"))
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--expect-total", type=int, default=EXPECT_TOTAL)
    args = ap.parse_args()
    DB = Path(args.db)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if not DB.exists():
        print(f"FATAL: DB missing at {DB}", file=sys.stderr)
        return 2

    # ---- assemble all rows from verified candidate files (cite-paste faithful) ----
    cohorts = {
        "c4_smart_lock": build_c4(now), "c5_smart_home_hub": build_c5(now),
        "c6_pet_kid": build_c6(now), "c1_spy_cam": build_c1(now), "c3_bt_tracker": build_c3(now),
    }
    all_rows = [r for rs in cohorts.values() for r in rs]
    assert len(all_rows) == EXPECTED_NEW_ROWS, f"total rows {len(all_rows)} != {EXPECTED_NEW_ROWS}"

    # ---- §11 #7 source_excerpt ceiling defensive sweep ----
    for r in all_rows:
        if r["source_excerpt"] is not None and len(r["source_excerpt"]) > 200:
            print(f"FATAL: source_excerpt > 200 for {r['identifier']}", file=sys.stderr)
            return 2

    con = sqlite3.connect(str(DB), isolation_level=None)  # manual txn control
    cur = con.cursor()

    def count(sql, a=()):
        return cur.execute(sql, a).fetchone()[0]

    # ---- baseline + STOP-on-out-of-band-drift ----
    total0 = count("SELECT COUNT(*) FROM identifiers")
    maxid0 = count("SELECT MAX(id) FROM identifiers")
    schema0 = count("SELECT MAX(version) FROM schema_version")
    body_cam = count("SELECT COUNT(*) FROM identifiers WHERE id BETWEEN 44497 AND 44501 AND device_category='body_cam'")
    already_applied = schema0 >= 33
    print(f"BASELINE total={total0} max_id={maxid0} schema={schema0} body_cam(44497-501)={body_cam} "
          f"already_applied={already_applied}")
    if body_cam != 5:
        con.close()
        print("STOP: MAC-352 body_cam anchor (44497-44501) != 5 — out-of-band drift.", file=sys.stderr)
        return 3
    if not already_applied and total0 != args.expect_total:
        con.close()
        print(f"STOP: total {total0} != expected {args.expect_total} (fresh apply) — out-of-band drift.", file=sys.stderr)
        return 3
    if already_applied and total0 not in (args.expect_total, args.expect_total + EXPECTED_NEW_ROWS):
        con.close()
        print(f"STOP: total {total0} not in fresh/applied set — drift.", file=sys.stderr)
        return 3

    # ---- backup-first ----
    pre_sha = sha256_of(DB)
    bak = None
    if not args.no_backup:
        bak = DB.with_name(f"argus.db.pre_mac419_{stamp}")
        shutil.copy2(DB, bak)
        bak.with_name(bak.name + ".sha256").write_text(f"{pre_sha}  {bak.name}\n")
        print(f"BACKUP  {bak.name}  (pre-sha {pre_sha})")
    else:
        print(f"NO-BACKUP mode (pre-sha {pre_sha})")

    # ---- PHASE A: schema mint (migration 0033) — idempotent ----
    enum_has = "smart_lock" in (cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='identifiers'").fetchone()[0])
    if enum_has:
        print("SCHEMA  smart_lock already in enum — skip rebuild (idempotent)")
    else:
        sql = MIGRATION_SQL.read_text()
        cur.executescript(sql)  # contains its own PRAGMA/BEGIN/COMMIT
        print(f"SCHEMA  applied 0033 -> schema={count('SELECT MAX(version) FROM schema_version')}")
        fkc = cur.execute("PRAGMA foreign_key_check").fetchall()
        if fkc:
            con.close()
            print(f"FATAL: foreign_key_check after 0033: {fkc[:5]}", file=sys.stderr)
            return 1

    # ---- PHASE B: data inserts + recat + conflicts (one transaction, in-txn verify) ----
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("BEGIN")
    inserted, skipped = [], []
    INS = ("INSERT INTO identifiers (identifier, identifier_type, device_category, manufacturer, "
           "model, confidence, source_url, source_type, source_excerpt, geographic_scope, "
           "first_seen, last_verified, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)")
    for r in all_rows:
        ex = cur.execute("SELECT id FROM identifiers WHERE identifier=? AND identifier_type=?",
                         (r["identifier"], r["identifier_type"])).fetchone()
        if ex:
            skipped.append((r["identifier"], r["identifier_type"], ex[0]))
            continue
        cur.execute(INS, (r["identifier"], r["identifier_type"], r["device_category"],
                          r["manufacturer"], r["model"], r["confidence"], r["source_url"],
                          r["source_type"], r["source_excerpt"], r["geographic_scope"],
                          now, now, json.dumps(r["notes"])))
        inserted.append(cur.lastrowid)

    # recat U-tec id7200 unknown -> smart_lock (property-merge notes, never text concat)
    recats = 0
    row = cur.execute("SELECT device_category, notes FROM identifiers WHERE id=7200").fetchone()
    if row and row[0] == "unknown":
        try:
            n = json.loads(row[1]) if row[1] else {}
            if not isinstance(n, dict):
                n = {"_prior_notes": row[1]}
        except Exception:
            n = {"_prior_notes": row[1]}
        n["mac419_recat"] = {"from": "unknown", "to": "smart_lock", "applied_utc": now,
                             "basis": "U-tec Group (Ultraloq, pure-play lock maker); MAC-406/MAC-397 CTO-ratified; board-approved",
                             "issue": "MAC-419"}
        cur.execute("UPDATE identifiers SET device_category='smart_lock', notes=? WHERE id=7200",
                    (json.dumps(n),))
        recats = 1
    elif row and row[0] == "smart_lock":
        print("RECAT   id7200 already smart_lock — skip (idempotent)")

    # c1 dedup conflicts (idempotent on a_id + reason)
    conflicts_added = 0
    for a_id, soc in C1_CONFLICTS:
        exists = cur.execute("SELECT COUNT(*) FROM conflicts WHERE identifier_a_id=? AND reason=?",
                             (a_id, "potential_dedup_step_5")).fetchone()[0]
        if exists:
            continue
        cur.execute("INSERT INTO conflicts (identifier_a_id, identifier_b_id, raw_observation_id, "
                    "reason, resolution_notes) VALUES (?,?,?,?,?)",
                    (a_id, None, None, "potential_dedup_step_5",
                     json.dumps({"issue": "MAC-419", "cohort": "MAC-393 c1 spy_cam OUI dedup",
                                 "applied_utc": now, "soc_oui_value": soc,
                                 "detail": f"Harvest-proposed SoC OUI {soc} already covered by existing "
                                 f"mac_range row id{a_id} (Validator 16-vs-22 correction). NOT inserted as new "
                                 f"oui row; export-neutral (both unknown). §8.4/§11 #13."})))
        conflicts_added += 1

    # ---- in-transaction verification ----
    total1 = count("SELECT COUNT(*) FROM identifiers")
    new_ids = inserted
    problems = []
    # json_valid sweep over every new row
    if new_ids:
        ph = ",".join("?" * len(new_ids))
        bad_json = count(f"SELECT COUNT(*) FROM identifiers WHERE id IN ({ph}) AND json_valid(notes)=0", new_ids)
        if bad_json:
            problems.append(f"json_valid=0 on {bad_json} new rows")
    # lookup-tuple uniqueness battery over new rows (identifier, identifier_type, source_url, last_verified)
    if new_ids:
        dups = cur.execute(
            f"SELECT identifier, identifier_type, source_url, last_verified, COUNT(*) c "
            f"FROM identifiers WHERE id IN ({ph}) "
            f"GROUP BY identifier, identifier_type, source_url, last_verified HAVING c>1", new_ids).fetchall()
        if dups:
            problems.append(f"lookup-tuple uniqueness violated: {dups[:3]}")
    # category counts
    cat = {c: count("SELECT COUNT(*) FROM identifiers WHERE device_category=?", (c,))
           for c in ("smart_lock", "smart_home_hub", "cctv_camera", "gps_tracker", "bluetooth_tracker")}
    # expected: fresh run inserts EXPECTED_NEW_ROWS; idempotent re-run inserts 0
    exp_ins = EXPECTED_NEW_ROWS if not (already_applied and not skipped == []) else len(inserted)
    if skipped and len(skipped) == EXPECTED_NEW_ROWS:
        print("IDEMPOTENT: all rows already present — 0 inserted")
    elif len(inserted) != EXPECTED_NEW_ROWS:
        problems.append(f"inserted {len(inserted)} != {EXPECTED_NEW_ROWS} (skipped {len(skipped)})")
    # ids must be > 44501 (no MAC-352 collision)
    if new_ids and min(new_ids) <= EXPECT_MAXID:
        problems.append(f"new id {min(new_ids)} <= {EXPECT_MAXID} — MAC-352 collision risk")

    # ---- reconstruction diff vs backup (full columns) ----
    if bak:
        FP = ("SELECT id, identifier, identifier_type, device_category, manufacturer, model, "
              "confidence, source_url, source_type, source_excerpt, geographic_scope, first_seen, "
              "last_verified, notes, superseded_by, paired_identifier_id, pair_kind, severity FROM identifiers")
        main_fp = {r[0]: r[1:] for r in cur.execute(FP).fetchall()}
        bcon = sqlite3.connect(f"file:{bak}?mode=ro", uri=True)
        try:
            bak_fp = {r[0]: r[1:] for r in bcon.execute(FP).fetchall()}
        finally:
            bcon.close()
        common = set(main_fp) & set(bak_fp)
        changed = sorted(i for i in common if main_fp[i] != bak_fp[i])
        new_diff = sorted(set(main_fp) - set(bak_fp))
        del_diff = sorted(set(bak_fp) - set(main_fp))
        # expected changed = recat id7200 only (fresh); new_diff = inserted ids; del = 0
        exp_changed = [7200] if recats else []
        if del_diff:
            problems.append(f"recon deleted rows: {del_diff}")
        if new_diff != sorted(new_ids):
            problems.append(f"recon new ids {new_diff} != inserted {sorted(new_ids)}")
        if changed != exp_changed:
            problems.append(f"recon changed {changed} != expected {exp_changed}")
        print(f"RECON vs backup: new={len(new_diff)} deleted={len(del_diff)} changed={changed}")

    print(f"\nCATEGORY counts: {cat}")
    print(f"INSERTED {len(inserted)}  SKIPPED {len(skipped)}  RECAT {recats}  CONFLICTS+{conflicts_added}")
    print(f"total {total0} -> {total1} (+{total1-total0})")
    if new_ids:
        print(f"new id range: {min(new_ids)}..{max(new_ids)}")

    if problems:
        cur.execute("ROLLBACK")
        con.close()
        print("\nROLLED BACK (data txn) — invariant violations:")
        for p in problems:
            print(f"   - {p}")
        if bak:
            print(f"NOTE: schema mint (0033) committed separately; restore from {bak.name} to fully revert.")
        return 1

    cur.execute("COMMIT")
    con.close()
    post_sha = sha256_of(DB)
    print(f"\nCOMMITTED. post-sha {post_sha}")
    if bak:
        print(f"backup={bak.name} pre-sha={pre_sha}")
    # machine-readable summary
    summary = {"total_before": total0, "total_after": total1, "inserted": len(inserted),
               "skipped": len(skipped), "recats": recats, "conflicts_added": conflicts_added,
               "new_id_min": min(new_ids) if new_ids else None, "new_id_max": max(new_ids) if new_ids else None,
               "category_counts": cat, "schema": count_schema(DB), "post_sha": post_sha,
               "pre_sha": pre_sha, "per_cohort": {k: len(v) for k, v in cohorts.items()}}
    print("SUMMARY_JSON " + json.dumps(summary))
    return 0


def count_schema(db: Path) -> int:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return c.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    finally:
        c.close()


if __name__ == "__main__":
    raise SystemExit(main())
