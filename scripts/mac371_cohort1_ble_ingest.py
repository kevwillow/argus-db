#!/usr/bin/env python3
"""MAC-373 / MAC-371 — Cohort 1 (BLE trackers / stalkerware) STAGED CANONICAL INGEST.

Applies the CTO-ratified candidate set (extraction_outputs/mac364_cohort1_ble/candidates.json,
sha256 b161e1c4...ad4a) into db/argus.db. STAGED write only:
  NO push, NO tag, NO export regen, NO schema migration, NO new CP. Schema stays 31.

Operations (CTO rulings D1-D5, MAC-371 ratification_proof.json):
  1. Mint 3 academic sources (USENIX first — primary source_id of behavioral[3]).
  2. Insert 41 net-new identifiers (36 ble_service_uuid / 2 ble_uuid / 3 ble_characteristic),
     all device_category='unknown'.
  3. EXCLUDE 0000fe59 (D3 — cross-vendor nRF52833 DFU constant). Recorded in exclusion ledger.
  4. Corroborate 7 already_in_db rows (no re-insert); §8.3 value-level lift to 90 ONLY for the
     2 rows with >=2 genuine independent issuers (0x004C row568, 0000fd5a row22864).
  5. Supersede live malformed tagfinder rows 22871 -> new 7dfc9000 ble_uuid, 22872 -> new
     7dfc9001 ble_characteristic.
  6. Insert 6 behavioral_signatures (field-map per D5).

Confidence (§8.2/§8.3, anchored to existing population convention):
  band default: primary_registry(SIG sid34)=85, academic=80, crowdsourced(AirGuard24/tagfinder29)=65.
  conf = min(99, max(band_defaults over genuine issuers) + (5 if >=2 genuine issuers else 0)).
  tagfinder(29) is informational/unverified-per-§7 for identifiers: NOT a genuine corroborating
  issuer (it never appears in a candidate's corroborating_sids). It IS a valid behavioral primary.

Idempotent guard: aborts if preconditions fail (e.g. already applied). One transaction.
"""
import json, sqlite3, hashlib, shutil, sys, datetime, os

DB = os.environ.get("MAC371_DB", "db/argus.db")
CANDS = "extraction_outputs/mac364_cohort1_ble/candidates.json"
CANDS_SHA = "b161e1c4200917d46d2333cff91fdd22e8440ddfcfb3a7fcb60eb3dcae36ad4a"
EXCL_VALUE = "0000fe59-0000-1000-8000-00805f9b34fb"
ISSUE = "MAC-371"          # extraction issue; ingest tracked under MAC-373
SIG_MEMBER_UUID_URL = "https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/uuids/member_uuids.yaml"
AIRGUARD_REPO = "https://github.com/seemoo-lab/AirGuard"
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def die(msg):
    print("ABORT:", msg, file=sys.stderr); sys.exit(1)

# ---- load + verify candidate set -------------------------------------------------
got = sha256_file(CANDS)
if got != CANDS_SHA:
    die(f"candidates.json sha256 mismatch: {got}")
doc = json.load(open(CANDS))
cands = doc["candidates"]
behav = doc["behavioral_signatures_candidates"]
need_sources = {s["academic_key"]: s for s in doc["_meta"]["needs_new_source_rows"]}

# ---- backup ----------------------------------------------------------------------
pre_sha = sha256_file(DB)
ts = NOW.replace(":", "").replace("-", "").split(".")[0] + "Z"
bak = f"{DB}.mac371_pre_apply_{ts}_{pre_sha[:12]}.bak"
shutil.copy2(DB, bak)
assert sha256_file(bak) == pre_sha, "backup sha mismatch"
print(f"[backup] {bak}  pre_sha={pre_sha}")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# ---- band-default confidence (§8.2) ----------------------------------------------
PRIMARY_REGISTRY, ACADEMIC, CROWD = 85, 80, 65
def band_default(sid):
    """Confidence a genuine issuer contributes per its §8.2 band."""
    if sid == 34:                      # Bluetooth SIG = primary_registry
        return PRIMARY_REGISTRY
    if isinstance(sid, str) and sid.startswith("academic:"):
        return ACADEMIC
    if sid in (24, 29):                # AirGuard / tagfinder = crowdsourced
        return CROWD
    die(f"unknown source_sid for band_default: {sid!r}")

def conf_from_issuers(issuers):
    """§8.3: min(99, max(originals) + (5 if >=2 genuine issuers else 0))."""
    bands = [band_default(s) for s in issuers]
    bonus = 5 if len(issuers) >= 2 else 0
    return min(99, max(bands) + bonus)

def merge_notes_json(existing, patch):
    """Property-merge a JSON object into existing notes JSON (NEVER text-suffix)."""
    obj = json.loads(existing) if existing else {}
    if not isinstance(obj, dict):
        die("existing notes not a JSON object")
    obj.update(patch)
    return json.dumps(obj, ensure_ascii=False)

# ---- PRECONDITIONS ---------------------------------------------------------------
def assert_schema():
    v = cur.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    if v != 31: die(f"schema_version {v} != 31")
assert_schema()

# new source rows absent
for k, s in need_sources.items():
    if cur.execute("SELECT COUNT(*) FROM sources WHERE url=?", (s["url"],)).fetchone()[0]:
        die(f"source already present: {s['url']}")

# net-new absent / already_in_db present / excluded absent
netnew, already, excluded = [], [], []
for c in cands:
    v, t = c["value"], c["identifier_type"]
    n = cur.execute("SELECT COUNT(*) FROM identifiers WHERE identifier=? AND identifier_type=?", (v, t)).fetchone()[0]
    if v == EXCL_VALUE:
        if n: die(f"excluded value present: {v}")
        excluded.append(c)
    elif c["already_in_db"]:
        if not n: die(f"already_in_db row missing: {v}/{t}")
        already.append(c)
    else:
        if n: die(f"net-new value already present: {v}/{t}")
        netnew.append(c)
assert len(netnew) == 41 and len(already) == 7 and len(excluded) == 1, \
    f"counts: netnew={len(netnew)} already={len(already)} excl={len(excluded)}"

# supersession targets exist, tagfinder-sourced, ble_service_uuid, not yet superseded
SUPERSEDE = {  # malformed_value -> (new_value, new_type)
    "7dfc9000-0000-1000-8000-00805f9b34fb": ("7dfc9000-7d1c-4951-86aa-8d9728f8d66c", "ble_uuid"),
    "7dfc9001-0000-1000-8000-00805f9b34fb": ("7dfc9001-7d1c-4951-86aa-8d9728f8d66c", "ble_characteristic"),
}
sup_rows = {}
for mal in SUPERSEDE:
    r = cur.execute("SELECT id, identifier_type, source_url, superseded_by, notes FROM identifiers "
                    "WHERE identifier=? AND identifier_type='ble_service_uuid'", (mal,)).fetchall()
    if len(r) != 1: die(f"supersession target not unique: {mal}")
    r = r[0]
    if "tagfinder" not in (r["source_url"] or ""): die(f"supersession target not tagfinder-sourced: {mal}")
    if r["superseded_by"] is not None: die(f"supersession target already superseded: {mal}")
    if r["notes"] and not json.loads(r["notes"]): pass
    sup_rows[mal] = r["id"]

# json_valid sweep BEFORE over full mutation scope (7 corrob + 2 supersede)
mut_ids = [
    cur.execute("SELECT id FROM identifiers WHERE identifier=? AND identifier_type=?",
                (c["value"], c["identifier_type"])).fetchone()[0] for c in already
] + list(sup_rows.values())
bad = [i for i in mut_ids if cur.execute(
    "SELECT CASE WHEN notes IS NULL THEN 1 WHEN json_valid(notes)=1 THEN 1 ELSE 0 END FROM identifiers WHERE id=?",
    (i,)).fetchone()[0] == 0]
if bad: die(f"non-JSON notes in mutation scope BEFORE: {bad}")
print(f"[precond] ok  netnew=41 already=7 excl=1 supersede=2  json_valid_before=clean(scope={len(mut_ids)})")

# ==================================================================================
# MUTATIONS (single transaction)
# ==================================================================================
proof = {"issue": "MAC-373", "extraction_issue": ISSUE, "applied_utc": NOW,
         "candidates_sha256": CANDS_SHA, "db_pre_sha256": pre_sha, "backup": bak,
         "source_mints": [], "inserts": [], "supersessions": [],
         "corroborations": [], "behavioral_inserts": [], "exclusion_ledger": []}
try:
    cur.execute("BEGIN")

    # 1. SOURCES — USENIX first (behavioral[3] primary). academic source_type for all 3.
    src_id = {}
    order = ["academic:usenix-2210.14702", "academic:pets-2021-0045", "academic:openhaystack-8d214aa"]
    for key in order:
        s = need_sources[key]
        notes = json.dumps({"upstream_license_posture": s["license_posture"],
                            "academic_key": key, "minted_by": "MAC-373", "minted_utc": NOW,
                            "cohort": "MAC-363 cohort1 BLE trackers"}, ensure_ascii=False)
        cur.execute("INSERT INTO sources(name,url,source_type,tier,last_fetched_at,last_status,notes) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (s["proposed_name"], s["url"], "academic", 1, NOW, "minted_mac373", notes))
        src_id[key] = cur.lastrowid
        proof["source_mints"].append({"academic_key": key, "id": cur.lastrowid,
                                       "url": s["url"], "license_posture": s["license_posture"]})

    def resolve_sid(sid):
        if isinstance(sid, str) and sid.startswith("academic:"):
            return src_id[sid]
        return sid  # 24/29/34 are live source ids

    # 2. INSERT 41 net-new identifiers
    new_row = {}  # value -> id
    for c in netnew:
        v, t = c["value"], c["identifier_type"]
        issuers = [c["source_sid"]] + list(c["corroborating_sids"])
        conf = conf_from_issuers(issuers)
        if t == "ble_service_uuid":          # SIG-anchored
            stype, surl = "primary_registry", SIG_MEMBER_UUID_URL
        else:                                 # ble_uuid / ble_characteristic — AirGuard sid24
            stype = "crowdsourced"
            rel = c["cite"]["artifact"].replace("raw/airguard/", "", 1)
            surl = f"{AIRGUARD_REPO}/blob/main/{rel}#L{c['cite']['line']}"
        excerpt = c["cite"]["excerpt"][:200]
        notes = {"stage": "mac371_ingest", "issue": "MAC-373", "applied_utc": NOW,
                 "vendor": c["vendor"], "device_product": c["device_product"],
                 "device_category_note": "§11 #13 unknown carveout; D4 export-visibility -> CEO",
                 "confidence_basis": c["confidence_basis"],
                 "source_sid": c["source_sid"], "corroborating_sids": c["corroborating_sids"],
                 "cite_artifact": c["cite"]["artifact"], "cite_line": c["cite"]["line"],
                 "sec_8_3": f"conf={conf} = min(99,max(originals)+{'5' if len(issuers)>=2 else '0'})"}
        if c.get("conflict_note"):
            notes["conflict_note"] = c["conflict_note"]
        cur.execute(
            "INSERT INTO identifiers(identifier,identifier_type,device_category,manufacturer,model,"
            "confidence,source_url,source_type,source_excerpt,first_seen,last_verified,notes) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (v, t, "unknown", c["vendor"], None, conf, surl, stype, excerpt, NOW, NOW,
             json.dumps(notes, ensure_ascii=False)))
        new_row[v] = cur.lastrowid
        proof["inserts"].append({"id": cur.lastrowid, "value": v, "type": t,
                                 "confidence": conf, "source_type": stype})

    # 3. EXCLUSION ledger (fe59) — NOT inserted
    for c in excluded:
        proof["exclusion_ledger"].append({
            "value": c["value"], "type": c["identifier_type"], "decision": "D3_EXCLUDE",
            "rationale": "cross-vendor nRF52833 Buttonless Secure DFU constant (Nordic SIG-assigned); "
                         "not a Samsung-exclusive signal",
            "precedent": "pending cross-vendor-exclusion precedent — CP44 reserved (MAC-321) / "
                         "provisional CP45 (MAC-351); NO new CP authored here — flagged to CTO",
            "conflict_note": c["conflict_note"]})

    # 5. SUPERSESSIONS (set after net-new inserted so new ids exist)
    for mal, (newv, newt) in SUPERSEDE.items():
        old_id, new_id = sup_rows[mal], new_row[newv]
        cur.execute("SELECT notes FROM identifiers WHERE id=?", (old_id,))
        patch = {"mac371_supersession": {
            "superseded_by": new_id, "by_value": newv, "by_type": newt, "applied_utc": NOW,
            "reason": "malformed tagfinder base-expansion of a 32-bit prefix as a SIG short UUID; "
                      "true 128-bit custom form is the new row (AirGuard sid24). CTO-verified (D2)."}}
        cur.execute("UPDATE identifiers SET superseded_by=?, notes=? WHERE id=?",
                    (new_id, merge_notes_json(cur.execute("SELECT notes FROM identifiers WHERE id=?", (old_id,)).fetchone()[0], patch), old_id))
        # breadcrumb on the new canonical row
        cur.execute("SELECT notes FROM identifiers WHERE id=?", (new_id,))
        nn = merge_notes_json(cur.execute("SELECT notes FROM identifiers WHERE id=?", (new_id,)).fetchone()[0],
                              {"supersedes_malformed": {"old_id": old_id, "old_value": mal}})
        cur.execute("UPDATE identifiers SET notes=? WHERE id=?", (nn, new_id))
        proof["supersessions"].append({"old_id": old_id, "old_value": mal,
                                       "new_id": new_id, "new_value": newv, "new_type": newt})

    # 4. CORROBORATION (7 already_in_db) — lift only where >=2 genuine issuers
    for c in already:
        v, t = c["value"], c["identifier_type"]
        row = cur.execute("SELECT id,confidence,notes FROM identifiers WHERE identifier=? AND identifier_type=?", (v, t)).fetchone()
        rid, cur_conf, cur_notes = row["id"], row["confidence"], row["notes"]
        issuers = [c["source_sid"]] + list(c["corroborating_sids"])  # genuine (tagfinder excluded by author)
        lift = len(issuers) >= 2
        # include existing row confidence as an "original" for the max
        new_conf = min(99, max([cur_conf] + [band_default(s) for s in issuers]) + 5) if lift else cur_conf
        patch = {"mac371_corroboration": {
            "applied_utc": NOW, "issue": "MAC-373",
            "genuine_issuers": c["source_sid"] if not c["corroborating_sids"] else
                               [c["source_sid"]] + list(c["corroborating_sids"]),
            "corroborating_sids": c["corroborating_sids"],
            "confidence_basis": c["confidence_basis"],
            "cite_artifact": c["cite"]["artifact"], "cite_line": c["cite"]["line"],
            "lift": (f"{cur_conf}->{new_conf} §8.3 min(99,max(originals)+5)" if lift
                     else f"none — {len(issuers)} genuine issuer(s); tagfinder informational per §7"),
            "reclassification_note": (None if t != "ble_service_uuid" or cur_conf != 65 or lift else
                "SIG independently lists this UUID; crowdsourced->primary_registry reclass DEFERRED "
                "(source_url points at tagfinder; needs new raw_observation per §8.2 reclass discipline)")}}
        if c.get("conflict_note"):
            patch["mac371_corroboration"]["conflict_note"] = c["conflict_note"]
        cur.execute("UPDATE identifiers SET confidence=?, last_verified=?, notes=? WHERE id=?",
                    (new_conf, NOW, merge_notes_json(cur_notes, patch), rid))
        proof["corroborations"].append({"id": rid, "value": v, "type": t,
                                        "conf_before": cur_conf, "conf_after": new_conf, "lift": lift})

    # 6. BEHAVIORAL_SIGNATURES (6)
    for b in behav:
        src = resolve_sid(b["source_sid"])
        issuers = [b["source_sid"]] + list(b["corroborating_sids"])
        conf = conf_from_issuers(issuers)
        notes = {"vendor": b["vendor"], "description": b["description"],
                 "stage": "mac371_ingest", "issue": "MAC-373", "applied_utc": NOW,
                 "source_sid": b["source_sid"], "corroborating_sids": b["corroborating_sids"],
                 "cite_artifact": b["cite"]["artifact"], "cite_excerpt": b["cite"]["excerpt"][:200],
                 "device_category_note": "§11 #13 unknown carveout; D4 -> CEO",
                 "sec_7_3_basis": f"conf={conf} (§8.2 band {'+5 §8.3 corrob' if len(issuers)>=2 else 'single-source'})"}
        cur.execute(
            "INSERT INTO behavioral_signatures(signature_name,cellular_generation,threshold_json,"
            "evidence_json,source_id,source_file_relative,source_line,confidence,device_category,notes) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (b["signature_name"], None, None, json.dumps(b["evidence_json"], ensure_ascii=False),
             src, b["source_file_relative"], b["source_line"], conf, "unknown",
             json.dumps(notes, ensure_ascii=False)))
        proof["behavioral_inserts"].append({"id": cur.lastrowid, "signature_name": b["signature_name"],
                                            "source_id": src, "confidence": conf})

    con.commit()
except Exception as e:
    con.rollback()
    die(f"transaction failed (rolled back): {e!r}")

# ==================================================================================
# POST-WRITE VERIFICATION
# ==================================================================================
assert_schema()
# json_valid sweep AFTER over full mutation scope (mutated existing + new + behavioral)
all_touched = mut_ids + list(new_row.values())
badp = [i for i in all_touched if cur.execute(
    "SELECT CASE WHEN notes IS NULL THEN 1 WHEN json_valid(notes)=1 THEN 1 ELSE 0 END FROM identifiers WHERE id=?",
    (i,)).fetchone()[0] == 0]
badb = cur.execute("SELECT COUNT(*) FROM behavioral_signatures WHERE notes IS NOT NULL AND json_valid(notes)=0 "
                   "AND id IN (SELECT id FROM behavioral_signatures ORDER BY id DESC LIMIT 6)").fetchone()[0]
if badp or badb: die(f"non-JSON notes AFTER: identifiers={badp} behavioral_bad={badb}")

post_sha = sha256_file(DB)
proof["db_post_sha256"] = post_sha
proof["counts"] = {
    "net_new_inserted": len(proof["inserts"]),
    "by_type": {t: sum(1 for x in proof["inserts"] if x["type"] == t)
                for t in ("ble_service_uuid", "ble_uuid", "ble_characteristic")},
    "conf90_inserts": sum(1 for x in proof["inserts"] if x["confidence"] == 90),
    "excluded": len(proof["exclusion_ledger"]),
    "corroborations": len(proof["corroborations"]),
    "corroboration_lifts": sum(1 for x in proof["corroborations"] if x["lift"]),
    "supersessions": len(proof["supersessions"]),
    "source_mints": len(proof["source_mints"]),
    "behavioral_inserts": len(proof["behavioral_inserts"]),
    "schema_version": 31,
    "json_valid_after": "clean",
}
proof["totals_after"] = {
    "identifiers": cur.execute("SELECT COUNT(*) FROM identifiers").fetchone()[0],
    "sources": cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
    "behavioral_signatures": cur.execute("SELECT COUNT(*) FROM behavioral_signatures").fetchone()[0],
}
con.close()

os.makedirs("operator_review/mac371_ingest", exist_ok=True)
with open("operator_review/mac371_ingest/promotion_proof.json", "w") as f:
    json.dump(proof, f, indent=2, ensure_ascii=False)
print(json.dumps(proof["counts"], indent=2))
print("totals_after:", proof["totals_after"])
print("post_sha:", post_sha)
print("proof written -> operator_review/mac371_ingest/promotion_proof.json")
