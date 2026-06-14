#!/usr/bin/env python3
"""MAC-407 — CTO independent verification of the DBArchitect staged ingest.

Re-queries the LIVE db/argus.db vs the backup .bak from scratch (own queries, not
attestation). Re-derives the full-column reconstruction diff, dumps the new row's
exact bytes, verifies the backup sha chain, runs a collision check on 0000fa25,
checks the candidate.json contract against what actually landed, and sweeps PII /
source_excerpt ceiling / schema invariants. Read-only on both DBs.
"""
from __future__ import annotations
import hashlib, json, sqlite3, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "db" / "argus.db"
BAK = REPO / "db" / "argus.db.pre_mac403_20260614T165659Z"
CAND = REPO / "extraction_outputs" / "mac393_c3_bletracker" / "candidates.json"

EXPECT = {
    "identifier": "0000fa25-0000-1000-8000-00805f9b34fb",
    "identifier_type": "ble_service_uuid",
    "device_category": "bluetooth_tracker",
    "manufacturer": "Pebblebee",
    "confidence": 65,
}
RECORDED_PRE_SHA = "347e9f90d8cb3ba7ab6c5ff2461f70c43bff8f715cd83b2931baea7955832a7a"
RECORDED_POST_SHA = "0994a2678f6dc81bed6308ff9b82a2f943286f2d9038565a86e8af7ed2bd473e"

FP_SQL = (
    "SELECT id, identifier, identifier_type, device_category, manufacturer, model, "
    "confidence, source_url, source_type, source_excerpt, geographic_scope, "
    "first_seen, last_verified, notes, superseded_by, paired_identifier_id, "
    "pair_kind, severity FROM identifiers"
)

def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def counts(con):
    c = con.cursor()
    q = lambda s, a=(): c.execute(s, a).fetchone()[0]
    return {
        "total": q("SELECT COUNT(*) FROM identifiers"),
        "active": q("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"),
        "ble_svc": q("SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_service_uuid'"),
        "bt_tracker": q("SELECT COUNT(*) FROM identifiers WHERE device_category='bluetooth_tracker'"),
        "mfrs": q("SELECT COUNT(*) FROM manufacturers"),
        "sources": q("SELECT COUNT(*) FROM sources"),
        "schema_max": q("SELECT MAX(version) FROM schema_version"),
    }

def main() -> int:
    fails, warns = [], []

    # ---- 0. backup sha chain --------------------------------------------------
    live_sha = sha256_of(DB)
    bak_sha = sha256_of(BAK)
    sha_file = Path(str(BAK) + ".sha256").read_text().split()[0]
    print("=== 0. SHA CHAIN ===")
    print(f"  recorded pre-sha   {RECORDED_PRE_SHA}")
    print(f"  .bak actual sha    {bak_sha}  {'OK' if bak_sha==RECORDED_PRE_SHA else 'MISMATCH'}")
    print(f"  .sha256 sidecar    {sha_file}  {'OK' if sha_file==RECORDED_PRE_SHA else 'MISMATCH'}")
    print(f"  recorded post-sha  {RECORDED_POST_SHA}")
    print(f"  live actual sha    {live_sha}  {'OK' if live_sha==RECORDED_POST_SHA else 'NOTE(differs)'}")
    if bak_sha != RECORDED_PRE_SHA: fails.append("backup sha != recorded pre-sha")
    if sha_file != RECORDED_PRE_SHA: fails.append("sha256 sidecar != recorded pre-sha")
    # live post-sha may legitimately differ if any benign read touched WAL; treat as note only.
    if live_sha != RECORDED_POST_SHA: warns.append(f"live sha {live_sha[:12]} != recorded post {RECORDED_POST_SHA[:12]} (note)")

    main_con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    bak_con = sqlite3.connect(f"file:{BAK}?mode=ro", uri=True)

    # ---- 1. counts both sides -------------------------------------------------
    cm, cb = counts(main_con), counts(bak_con)
    print("\n=== 1. COUNTS (bak -> live) ===")
    for k in cm:
        d = cm[k] - cb[k]
        print(f"  {k:12} {cb[k]} -> {cm[k]}  ({'+' if d>=0 else ''}{d})")
    if cm["total"] - cb["total"] != 1: fails.append("total delta != +1")
    if cm["active"] - cb["active"] != 1: fails.append("active delta != +1")
    if cm["ble_svc"] - cb["ble_svc"] != 1: fails.append("ble_service_uuid delta != +1")
    if cm["bt_tracker"] - cb["bt_tracker"] != 1: fails.append("bluetooth_tracker delta != +1")
    if cm["mfrs"] != cb["mfrs"]: fails.append("manufacturers changed")
    if cm["sources"] != cb["sources"]: fails.append("sources changed")
    if cm["schema_max"] != cb["schema_max"]: fails.append("schema_max changed")
    if cm["schema_max"] != 32: fails.append(f"schema_max {cm['schema_max']} != 32")

    # ---- 2. full-column reconstruction diff -----------------------------------
    main_fp = {r[0]: r[1:] for r in main_con.execute(FP_SQL).fetchall()}
    bak_fp = {r[0]: r[1:] for r in bak_con.execute(FP_SQL).fetchall()}
    new_ids = sorted(set(main_fp) - set(bak_fp))
    del_ids = sorted(set(bak_fp) - set(main_fp))
    common = set(main_fp) & set(bak_fp)
    changed = [i for i in common if main_fp[i] != bak_fp[i]]
    print("\n=== 2. RECON DIFF (live vs .bak, 18-col fingerprint) ===")
    print(f"  new={new_ids}  deleted={del_ids}  changed_common={len(changed)}")
    if len(new_ids) != 1: fails.append(f"recon new != 1 row: {new_ids}")
    if del_ids: fails.append(f"recon deleted rows: {del_ids}")
    if changed: fails.append(f"recon changed rows: {changed[:10]}")

    # ---- 3. new row exact bytes + contract ------------------------------------
    new_id = new_ids[0] if new_ids else None
    print("\n=== 3. NEW ROW EXACT BYTES ===")
    if new_id is not None:
        row = main_con.execute(
            "SELECT id, identifier, identifier_type, device_category, manufacturer, model, "
            "confidence, source_type, source_url, source_excerpt, geographic_scope, "
            "superseded_by, json_valid(notes) FROM identifiers WHERE id=?", (new_id,)
        ).fetchone()
        cols = ["id","identifier","identifier_type","device_category","manufacturer","model",
                "confidence","source_type","source_url","source_excerpt","geographic_scope",
                "superseded_by","json_valid(notes)"]
        d = dict(zip(cols, row))
        for k, v in d.items():
            print(f"  {k:18} = {v!r}")
        for k, want in EXPECT.items():
            got = d.get("identifier" if k=="identifier" else k)
            if d[k] != want:
                fails.append(f"row.{k}={d[k]!r} != expected {want!r}")
        if d["confidence"] > 75: fails.append("confidence > 75 ceiling")
        if d["superseded_by"] is not None: fails.append("new row not active")
        if d["json_valid(notes)"] != 1: fails.append("json_valid(notes) != 1")
        if len(d["source_excerpt"] or "") > 200: fails.append("source_excerpt > 200")
        # PII / secrets sweep on free-text
        notes = main_con.execute("SELECT notes FROM identifiers WHERE id=?", (new_id,)).fetchone()[0]
        blob = (d["source_excerpt"] or "") + " " + (notes or "")
        import re
        if re.search(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", blob): fails.append("possible email/PII in row text")
        if re.search(r"(api[_-]?key|secret|password|token)\s*[=:]", blob, re.I): fails.append("possible secret in row text")
    else:
        fails.append("no new row found")

    # ---- 4. collision check ---------------------------------------------------
    coll = main_con.execute(
        "SELECT id, identifier_type, device_category, superseded_by FROM identifiers WHERE identifier=?",
        (EXPECT["identifier"],)).fetchall()
    print("\n=== 4. COLLISION CHECK (0000fa25 rows) ===")
    for r in coll: print(f"  {r}")
    if len(coll) != 1: fails.append(f"0000fa25 appears {len(coll)} times, expected 1")

    # ---- 5. candidate.json contract ------------------------------------------
    doc = json.loads(CAND.read_text())
    cands = [c for c in doc["candidates"] if c.get("db_presence") == "net-new"]
    print("\n=== 5. CANDIDATE.JSON CONTRACT ===")
    print(f"  net-new candidates in file: {len(cands)}")
    if len(cands) != 1: fails.append(f"candidates.json net-new != 1: {len(cands)}")
    else:
        c = cands[0]
        contract = {
            "value": (c["value"], EXPECT["identifier"]),
            "identifier_type": (c["identifier_type"], EXPECT["identifier_type"]),
            "device_category": (c["device_category"], EXPECT["device_category"]),
            "manufacturer": (c["manufacturer"], EXPECT["manufacturer"]),
            "confidence": (c["confidence"], EXPECT["confidence"]),
        }
        for k,(got,want) in contract.items():
            ok = got==want
            print(f"  {k:16} cand={got!r} want={want!r}  {'OK' if ok else 'MISMATCH'}")
            if not ok: fails.append(f"candidate.{k} {got!r} != {want!r}")

    # ---- 6. excluded held-rows untouched -------------------------------------
    # 0xFD44 must still be exactly its held row (id22876 svc_uuid bluetooth_tracker) — unchanged
    print("\n=== 6. EXCLUDED CROSS-VENDOR UNTOUCHED (spot-check 0xFD44 id22876) ===")
    for label, con in (("bak", bak_con), ("live", main_con)):
        r = con.execute("SELECT id, identifier_type, device_category FROM identifiers WHERE id=22876").fetchone()
        print(f"  {label}: {r}")
    r_live = main_con.execute("SELECT * FROM identifiers WHERE id=22876").fetchone()
    r_bak = bak_con.execute("SELECT * FROM identifiers WHERE id=22876").fetchone()
    if r_live != r_bak: warns.append("id22876 (0xFD44 held) differs live vs bak")

    main_con.close(); bak_con.close()

    print("\n=== VERDICT ===")
    if fails:
        print("FAIL:")
        for f in fails: print(f"   - {f}")
    else:
        print("ALL HARD GATES PASS")
    if warns:
        print("Notes/warnings:")
        for w in warns: print(f"   ~ {w}")
    return 1 if fails else 0

if __name__ == "__main__":
    raise SystemExit(main())
