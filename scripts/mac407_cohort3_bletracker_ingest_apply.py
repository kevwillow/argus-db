#!/usr/bin/env python3
"""MAC-407 — Wave-2 Cohort-3 (Bluetooth tracker) INGEST — staged shipped-registry write.

Lands the single CTO-ratified (MAC-403) net-new promotion candidate from
``extraction_outputs/mac393_c3_bletracker/candidates.json``:

  1 net-new ``ble_service_uuid`` row — Pebblebee offline-finding SOUND service:
      identifier        = 0000fa25-0000-1000-8000-00805f9b34fb (canonical 8-4-4-4-12)
      identifier_type   = ble_service_uuid
      device_category   = bluetooth_tracker   (exported category, wave-1 MAC-387/388)
      manufacturer      = Pebblebee
      confidence        = 65   (§8.2 crowdsourced band, ceiling <=75 — NOT exceeded)
      source            = sid24 (AirGuard, crowdsourced/tier1) — already in `sources`
      source_type       = crowdsourced

Provenance (byte-pinned in notes):
  PebbleBee.kt:214  offlineFindingServiceUUID = "0000FA25-0000-1000-8000-00805F9B34FB"
  artifact_sha256   14100da0f7d4e33cd0c945182671276e82769e195e5de4dbfcd70d65d6ebab3c

Corroboration: SINGLE-SOURCE. CTO-authorized Pebblebee APK enrichment came up EMPTY
(com.pebblebee.pebblebeeplus v2.2.3 sha 76b5879... lacks 0xFA25 in its dex string pool)
-> NO §8.3 value-level lift. Stays single-source <=75 (honest outcome). Confidence NOT
inflated.

Explicitly NOT written (held / out of scope per brief):
  * 0x2C02 (SIG-standard "UGT Features" char) — recorded in notes, NOT a row.
  * Cube 0x03EE — link unproven (APK absent); stays held@unknown id4010. No recat.
  * Pebblebee's 11 custom 128-bit GATT UUIDs — corroboration-only scope, flagged not ingested.
  * Cross-vendor 0xFEAA / 0xFD44 / 0x004C / 0xFE59 — already held, excluded.

Migration-safety: backup-first (db/argus.db.pre_mac403_<UTC> + .sha256, gitignored),
apply-time presence re-check (STOP if a 0000fa25 row appeared out-of-band), single
INSERT inside a transaction, fresh JSON notes object (json.dumps; no text-suffix concat),
json_valid sweep over the new row, full-column reconstruction diff vs the .bak.
Schema stays 32 (no migration, no new enum, no new column). manufacturers UNTOUCHED
(cohort BLE ingest convention — MAC-373 Tile/Chipolo/Samsung rows likewise added no
manufacturers seed rows). Idempotent: re-running skips an existing (0000fa25,
ble_service_uuid) row.

Live baseline reconciled (own query, mode=ro): active 43123, bluetooth_tracker 46,
ble_service_uuid 169 (= 133 legacy + 36 MAC-373; the brief's stated 166 was stale-by-3
pre-MAC-373-tally — the active-total and bluetooth_tracker anchors both match exactly).
Expected DELTA: ble_service_uuid 169->170, bluetooth_tracker 46->47, active 43123->43124.

NO export_lynceus.py regen. NO push. NO tag. db/argus.db is gitignored+untracked.
See operator_review/MAC-403/dbarch_ingest_proof.md.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "db" / "argus.db"
CANDIDATES = REPO / "extraction_outputs" / "mac393_c3_bletracker" / "candidates.json"

EXPECT_VALUE = "0000fa25-0000-1000-8000-00805f9b34fb"
EXPECT_TYPE = "ble_service_uuid"
EXPECT_CATEGORY = "bluetooth_tracker"
EXPECT_MFR = "Pebblebee"
EXPECT_CONF = 65
BAND_CEILING = 75
SOURCE_SID = 24  # AirGuard, crowdsourced/tier1 — already in `sources`

# AirGuard (sid24) repo blob URL to the cite artifact. The exact bytes are byte-pinned
# in notes via artifact_sha256; this is the human-resolvable provenance pointer.
SOURCE_URL = (
    "https://github.com/seemoo-lab/AirGuard/blob/main/app/src/main/java/de/seemoo/"
    "at_tracking_detection/database/models/device/types/PebbleBee.kt"
)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if not DB.exists():
        print(f"FATAL: DB missing at {DB}", file=sys.stderr)
        return 2

    doc = json.loads(CANDIDATES.read_text())
    cands = [c for c in doc["candidates"] if c.get("db_presence") == "net-new"]
    if len(cands) != 1:
        print(f"FATAL: expected exactly 1 net-new candidate, got {len(cands)}", file=sys.stderr)
        return 2
    cand = cands[0]

    # ---- validate the candidate against the brief contract (defensive) -----------
    sm = cand["source_markers"]
    checks = {
        "value": cand["value"] == EXPECT_VALUE,
        "identifier_type": cand["identifier_type"] == EXPECT_TYPE,
        "device_category": cand["device_category"] == EXPECT_CATEGORY,
        "manufacturer": cand["manufacturer"] == EXPECT_MFR,
        "confidence": cand["confidence"] == EXPECT_CONF,
        "band_ceiling": cand["confidence"] <= cand.get("band_ceiling", BAND_CEILING) <= BAND_CEILING,
        "source_sid": cand["source_sid"] == SOURCE_SID,
    }
    bad = [k for k, ok in checks.items() if not ok]
    if bad:
        print(f"FATAL: candidate contract mismatch on {bad}: {cand}", file=sys.stderr)
        return 2

    excerpt = sm["excerpt"]
    if len(excerpt) > 200:  # §11 #7 source_excerpt ceiling
        print(f"FATAL: source_excerpt {len(excerpt)} > 200", file=sys.stderr)
        return 2

    notes = {
        "stage": "mac403_extraction_ingest",
        "issue": "MAC-407",
        "applied_utc": now,
        "cohort": "MAC-393 wave-2 cohort-3 bluetooth_tracker",
        "lineage": "MAC-396 harvest -> MAC-403 extraction (CTO-ratified) -> MAC-407 ingest",
        "vendor": EXPECT_MFR,
        "device_product": "Pebblebee offline-finding (SOUND) service UUID",
        "source_sid": SOURCE_SID,
        "source_origin": "AirGuard (seemoo-lab/AirGuard) multi-tracker BLE catalog, crowdsourced/tier1",
        "cite_artifact": sm["artifact"],
        "cite_line": sm["line"],
        "cite_artifact_sha256": sm["artifact_sha256"],
        "cite_excerpt": excerpt,
        "confidence_basis": "§8.2 crowdsourced single-source ceiling 75; staged at 65 "
        "(AirGuard sid24 sole issuer; NOT SIG-registered -> Pebblebee-proprietary 16-bit UUID).",
        "corroboration": "SINGLE-SOURCE crowdsourced, APK-uncorroborated. CTO-authorized "
        "Pebblebee APK (com.pebblebee.pebblebeeplus v2.2.3, sha "
        "76b587956b610911652dd5d0602252d733a6834cbf75d3d2a8d2ad0ff02bc855) lacks 0xFA25 "
        "in its dex string pool -> no §8.3 value-level lift. Stays single-source <=75.",
        "sec_8_3": "no lift (single-source); conf=65 <= 75 ceiling. Confidence NOT inflated.",
        "paired_char_2c02": "Paired char 0x2C02 (PebbleBee.kt:190) is SIG-standard "
        "'UGT Features' (characteristic_uuids.yaml) -> NOT vendor-distinct; NOT promoted.",
        "caveat": "Connectable SOUND / offline-finding GATT service (AirGuard ScanFilter "
        "serviceUuid PebbleBee.kt:197-200); advertised by offline-finding units but observed "
        "on CONNECT, not guaranteed in passive adv.",
        "not_pebble_technology": "Pebble Technology (smartwatch) rows id4624/9839/37761 are a "
        "DIFFERENT company; not conflated.",
        "ratified_at": "MAC-403 (operator_review/MAC-403/cto_extraction_ratification.md)",
        "export_membership": "reaches Lynceus standard feed on regen (ble_service_uuid exported "
        "/ bluetooth_tracker exported category / crowdsourced / conf 65). CEO one-way door at "
        "ship gate (mirrors cohort-1 MAC-373).",
    }

    # ---- backup-first ------------------------------------------------------------
    pre_sha = sha256_of(DB)
    bak = DB.with_name(f"argus.db.pre_mac403_{stamp}")
    shutil.copy2(DB, bak)
    (bak.with_name(bak.name + ".sha256")).write_text(f"{pre_sha}  {bak.name}\n")
    print(f"BACKUP  {bak.name}  (pre-sha {pre_sha})")

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    cur = con.cursor()

    def count(sql: str, args=()) -> int:
        return cur.execute(sql, args).fetchone()[0]

    before = {
        "ident_total": count("SELECT COUNT(*) FROM identifiers"),
        "ident_active": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"),
        "ble_svc": count("SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_service_uuid'"),
        "bt_tracker": count("SELECT COUNT(*) FROM identifiers WHERE device_category='bluetooth_tracker'"),
        "mfrs": count("SELECT COUNT(*) FROM manufacturers"),
        "sources": count("SELECT COUNT(*) FROM sources"),
        "schema_max": count("SELECT MAX(version) FROM schema_version"),
        "user_version": count("PRAGMA user_version"),
    }
    print(f"\nBEFORE  ident_total={before['ident_total']} ident_active={before['ident_active']} "
          f"ble_service_uuid={before['ble_svc']} bluetooth_tracker={before['bt_tracker']} "
          f"mfrs={before['mfrs']} sources={before['sources']} schema_max={before['schema_max']}")

    # ---- apply-time presence re-check (STOP on out-of-band drift) ----------------
    existing = cur.execute(
        "SELECT id, superseded_by FROM identifiers WHERE identifier=? AND identifier_type=?",
        (EXPECT_VALUE, EXPECT_TYPE),
    ).fetchone()
    if existing:
        con.close()
        print(f"STOP: ({EXPECT_VALUE}, {EXPECT_TYPE}) already present id={existing[0]} "
              f"(out-of-band drift). No double-insert. Hand back to CTO.", file=sys.stderr)
        return 3

    # ---- verify sid24 is AirGuard (no new source needed) -------------------------
    src = cur.execute("SELECT id, name, source_type, url FROM sources WHERE id=?", (SOURCE_SID,)).fetchone()
    if not src or "seemoo-lab/AirGuard" not in (src[3] or ""):
        con.close()
        print(f"FATAL: source sid {SOURCE_SID} is not AirGuard: {src}", file=sys.stderr)
        return 2

    cur.execute("BEGIN")
    cur.execute(
        "INSERT INTO identifiers "
        "(identifier, identifier_type, device_category, manufacturer, model, confidence, "
        " source_url, source_type, source_excerpt, geographic_scope, first_seen, "
        " last_verified, notes) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            EXPECT_VALUE,
            EXPECT_TYPE,
            EXPECT_CATEGORY,
            EXPECT_MFR,
            None,
            EXPECT_CONF,
            SOURCE_URL,
            "crowdsourced",
            excerpt[:200],
            None,  # geographic_scope: NULL — matches MAC-373 ble_service_uuid/bluetooth_tracker rows
            now,
            now,
            json.dumps(notes),
        ),
    )
    new_id = cur.lastrowid
    print(f"  INSERT id={new_id}  {EXPECT_VALUE}  ({EXPECT_MFR}, conf {EXPECT_CONF})")

    after = {
        "ident_total": count("SELECT COUNT(*) FROM identifiers"),
        "ident_active": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"),
        "ble_svc": count("SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_service_uuid'"),
        "bt_tracker": count("SELECT COUNT(*) FROM identifiers WHERE device_category='bluetooth_tracker'"),
        "mfrs": count("SELECT COUNT(*) FROM manufacturers"),
        "sources": count("SELECT COUNT(*) FROM sources"),
        "schema_max": count("SELECT MAX(version) FROM schema_version"),
        "user_version": count("PRAGMA user_version"),
    }
    jv_new = count("SELECT json_valid(notes) FROM identifiers WHERE id=?", (new_id,))

    # ---- reconstruction diff vs .bak (full columns, in Python) -------------------
    FP_SQL = (
        "SELECT id, identifier, identifier_type, device_category, manufacturer, model, "
        "confidence, source_url, source_type, source_excerpt, geographic_scope, "
        "first_seen, last_verified, notes, superseded_by, paired_identifier_id, "
        "pair_kind, severity FROM identifiers"
    )
    main_fp = {r[0]: r[1:] for r in cur.execute(FP_SQL).fetchall()}
    bak_con = sqlite3.connect(f"file:{bak}?mode=ro", uri=True)
    try:
        bak_fp = {r[0]: r[1:] for r in bak_con.execute(FP_SQL).fetchall()}
    finally:
        bak_con.close()

    common = set(main_fp) & set(bak_fp)
    changed = sum(1 for i in common if main_fp[i] != bak_fp[i])
    new_ids_diff = sorted(set(main_fp) - set(bak_fp))
    deleted_ids_diff = sorted(set(bak_fp) - set(main_fp))

    # ---- invariants --------------------------------------------------------------
    problems = []
    if after["schema_max"] != 32 or after["user_version"] != before["user_version"]:
        problems.append(f"schema drift: {before['schema_max']}/{before['user_version']} -> "
                        f"{after['schema_max']}/{after['user_version']}")
    if after["ident_total"] != before["ident_total"] + 1:
        problems.append("ident_total delta != +1")
    if after["ident_active"] != before["ident_active"] + 1:
        problems.append("ident_active delta != +1")
    if after["ble_svc"] != before["ble_svc"] + 1:
        problems.append("ble_service_uuid delta != +1")
    if after["bt_tracker"] != before["bt_tracker"] + 1:
        problems.append("bluetooth_tracker delta != +1")
    if after["mfrs"] != before["mfrs"]:
        problems.append("manufacturers count changed (none expected)")
    if after["sources"] != before["sources"]:
        problems.append("sources count changed (none expected)")
    if jv_new != 1:
        problems.append(f"json_valid(notes) on new row != 1: {jv_new}")
    if new_ids_diff != [new_id]:
        problems.append(f"recon new ids {new_ids_diff} != [{new_id}]")
    if deleted_ids_diff:
        problems.append(f"recon deleted rows != 0: {deleted_ids_diff}")
    if changed != 0:
        problems.append(f"recon changed common rows != 0: {changed}")

    print("\n=== RECON (own query vs .bak) ===")
    print(f"  ident_total      {before['ident_total']} -> {after['ident_total']}  (+{after['ident_total']-before['ident_total']})")
    print(f"  ident_active     {before['ident_active']} -> {after['ident_active']}  (+{after['ident_active']-before['ident_active']})")
    print(f"  ble_service_uuid {before['ble_svc']} -> {after['ble_svc']}  (+{after['ble_svc']-before['ble_svc']})")
    print(f"  bluetooth_tracker {before['bt_tracker']} -> {after['bt_tracker']}  (+{after['bt_tracker']-before['bt_tracker']})")
    print(f"  mfrs             {before['mfrs']} -> {after['mfrs']}  (+0)")
    print(f"  sources          {before['sources']} -> {after['sources']}  (+0)")
    print(f"  inserted id      = {new_id}")
    print(f"  json_valid notes = {jv_new}/1")
    print(f"  recon vs .bak: new={new_ids_diff} deleted={len(deleted_ids_diff)} changed_common={changed}")
    print(f"  schema_max={after['schema_max']} user_version={after['user_version']}")

    if problems:
        con.rollback()
        con.close()
        print("\nROLLED BACK — invariant violations:")
        for p in problems:
            print(f"   - {p}")
        return 1

    con.commit()
    con.close()
    post_sha = sha256_of(DB)
    print(f"\nCOMMITTED. new_id={new_id} post-sha {post_sha}")
    print(f"backup={bak.name} pre-sha={pre_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
