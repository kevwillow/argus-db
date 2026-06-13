#!/usr/bin/env python3
"""MAC-375 / MAC-372 — Cohort 2 (ALPR / cop-car) STAGED CANONICAL INGEST + remediation.

Applies the CTO-ratified candidate set (extraction_outputs/mac365_cohort2_alpr/
candidates.json, sha256 70aea2d0…3817) into db/argus.db. STAGED write only:
  NO push, NO tag, NO export regen, NO schema migration, NO new CP. Schema stays 31.

Parent MAC-363 Phase B. Sibling of MAC-373 (cohort-1 ingest, landed 7f1e966). Mirrors
that ratified pattern: direct identifiers INSERT with full provenance (source_url NOT
NULL + structured notes JSON); no raw_observations predecessors created (matching the
ratified sibling — §11 #17 backfill question flagged to CTO, not resolved here).

WORK ITEM A — promote 14 net-new (16 candidates − 2 held) + 2 behavioral + 2 sources:
  6 ssid_pattern   crowdsourced  conf 75  (§8.2 crowdsourced ceiling; §4.4 export-DROPPED)
  5 fcc_grantee    primary_registry conf 85  (§8.2 primary_registry single-source; sid7 frozen)
  3 equipment_cls  regulatory    conf 75  (sid85 fcc.report; FCC-IDs WebFetch-confirmed to
                                           resolve 2026-06-13; grant-exhibit honest-absent →
                                           CTO caveat: anchored to established equip band 75,
                                           NOT the proposed 90 ceiling which tops the whole type)
  2 behavioral     manufacturer_app conf 80 (Vigilant LEARN + Rekor/OpenALPR; DEX-verified)
  HELD (NOT promoted): (?i)^penguin… / (?i)^pigvision… (ruling #8 weak sourcing, conf 40,
                       2nd independent source required) — left as candidates.

WORK ITEM B — remediate 5 already-shipped rows the IEEE registry (sid1) contradicts:
  4 oui  WITHDRAW (superseded_by self-loop, MAC-217 mechanic) — corrected IEEE vendor has no
         surveillance nexus → row should not exist. Export delta flagged for CTO push-gate.
  1 NCV grantee  RE-ATTRIBUTE manufacturer Vigilant Solutions→Vigilant Systems Inc,
         device_category alpr→unknown (frozen FCC sid7 = a different entity, Klamath Falls OR).
  +1 soft lineage note on id 35588 (00:14:3E AirLink→Sierra 2007; NOT a mis-attribution).
  No source_reclassifications entries: none of these touch source_type/confidence/source_url
  (the CP19 §11 #8 triggers); precedent MAC-217 self-loop withdrawals logged none either.

Idempotent guard: aborts if any precondition fails (e.g. already applied). One transaction.
"""
import json, sqlite3, hashlib, shutil, sys, datetime, os

DB = os.environ.get("MAC372_DB", "db/argus.db")
CANDS = "extraction_outputs/mac365_cohort2_alpr/candidates.json"
CANDS_SHA = "70aea2d03deedec1e8afb0ee09f8f4b6de96e52166a3872c33198b6309563817"
ISSUE = "MAC-375"            # ingest issue; extraction tracked under MAC-372
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

HELD_SSID = {"(?i)^penguin[_-]?.*", "(?i)^pigvision[_-]?.*"}   # ruling #8 — do NOT promote

# Confidence bands (§8.2). equip is anchored to the established equipment_class_code
# band per the CTO honest-absent caveat (see module docstring).
CONF = {"ssid_pattern": 75, "fcc_grantee_code": 85, "equipment_class_code": 75}
STYPE = {"ssid_pattern": "crowdsourced", "fcc_grantee_code": "primary_registry",
         "equipment_class_code": "regulatory"}
BEHAVIORAL_CONF = 80

# WORK ITEM B — OUI withdrawals: id -> (oui, db_says_manufacturer, ieee_ground_truth)
OUI_WITHDRAW = {
    35586: ("00:0E:8E", "Sierra Wireless", "SparkLAN Communications, Inc."),
    35587: ("00:11:75", "Sierra Wireless", "Intel Corporation"),
    35589: ("00:10:8B", "Cradlepoint", "LASERANIMATION SOLLINGER GMBH"),
    35590: ("EC:F4:51", "Cradlepoint", "Arcadyan Corporation"),
}
NCV_ID = 42948
LINEAGE_ID = 35588          # 00:14:3E AirLink→Sierra (soft note only)

# FCC-ID resolution confirmations (WebFetch 2026-06-13, CTO caveat satisfied).
FCC_ID_CONFIRM = {
    "VTFADM3":  "fcc.report/FCC-ID/VTF/ADM3 resolves; grantee VTF = Remington Elsag Law "
                "Enforcement Systems; filing 2009-11-25 NEW DEVICE. WebFetch 2026-06-13.",
    "N7NRC76B": "fcc.report/FCC-ID/N7N/RC76B resolves; grantee N7N = Sierra Wireless Inc.; "
                "filing 2020-02-05 NEW DEVICE. WebFetch 2026-06-13.",
    "N7NRC76C": "fcc.report/FCC-ID/N7N/RC76C resolves; grantee N7N = Sierra Wireless Inc.; "
                "filing 2022-06-30 NEW DEVICE. WebFetch 2026-06-13.",
}
# §11 #7 pairing — equip FCC-ID -> its grantee_code (resolved to grantee identifier id at write).
EQUIP_GRANTEE = {"VTFADM3": "VTF", "N7NRC76B": "N7N", "N7NRC76C": "N7N"}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def die(msg):
    print("ABORT:", msg, file=sys.stderr); sys.exit(1)


def merge_notes_json(existing, patch):
    """Property-merge a JSON object into existing notes JSON (NEVER text-suffix — CP39)."""
    obj = json.loads(existing) if existing else {}
    if not isinstance(obj, dict):
        die("existing notes not a JSON object")
    obj.update(patch)
    return json.dumps(obj, ensure_ascii=False)


# ---- load + verify candidate set -------------------------------------------------
got = sha256_file(CANDS)
if got != CANDS_SHA:
    die(f"candidates.json sha256 mismatch: {got}")
doc = json.load(open(CANDS))
cands = doc["candidates"]
behav = doc["behavioral_signatures"]
need_sources = doc["_meta"]["needs_new_source_rows"]
oui_disp = {d["oui"]: d for d in doc["oui_dispositions"]}

# partition Work Item A candidates
net_new = [c for c in cands if c["db_presence"] == "net-new" and c["value"] not in HELD_SSID]
held = [c for c in cands if c["value"] in HELD_SSID]
ssid = [c for c in net_new if c["identifier_type"] == "ssid_pattern"]
grantee = [c for c in net_new if c["identifier_type"] == "fcc_grantee_code"]
equip = [c for c in net_new if c["identifier_type"] == "equipment_class_code"]
assert len(net_new) == 14 and len(ssid) == 6 and len(grantee) == 5 and len(equip) == 3, \
    f"partition: net_new={len(net_new)} ssid={len(ssid)} grantee={len(grantee)} equip={len(equip)}"
assert len(held) == 2, f"held={len(held)}"
assert len(behav) == 2, f"behavioral={len(behav)}"

# ---- backup ----------------------------------------------------------------------
pre_sha = sha256_file(DB)
ts = NOW.replace(":", "").replace("-", "").split(".")[0] + "Z"
bak = f"{DB}.mac372_pre_apply_{ts}_{pre_sha[:12]}.bak"
shutil.copy2(DB, bak)
assert sha256_file(bak) == pre_sha, "backup sha mismatch"
print(f"[backup] {bak}  pre_sha={pre_sha}")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()


def one(q, *a):
    return cur.execute(q, a).fetchone()


# ---- PRECONDITIONS ---------------------------------------------------------------
v = one("SELECT MAX(version) FROM schema_version")[0]
if v != 31:
    die(f"schema_version {v} != 31")

# new app sources absent (by url)
SRC_URL = {
    "app:com.vigilant.solutions.mobilecompanion":
        "argus-internal://mac365_cohort2_alpr/vendor_apps/com.vigilant.solutions."
        "mobilecompanion/1.1.180312.1100/"
        "a627e3fa9191689c42e3e688c9600440a2bb3360e8beba26981c65fa4b0fad44.apk",
    "app:ai.rekor.rekorblue":
        "argus-internal://mac365_cohort2_alpr/vendor_apps/ai.rekor.rekorblue/1.5.92.0/"
        "5993cfff6c90e0f1e4a8f1e2e4a332f2e6e687117a303bdb5b6afe54ebca88cb.apk",
}
for key, url in SRC_URL.items():
    if one("SELECT COUNT(*) FROM sources WHERE url=?", url)[0]:
        die(f"source already present: {url}")
    # also guard against a pre-existing source for the same package by sha in notes
    pkg = key.split(":", 1)[1]
    if one("SELECT COUNT(*) FROM sources WHERE name LIKE ?", f"%{pkg}%")[0]:
        die(f"a source naming package {pkg} already exists — investigate before mint")

# 14 net-new absent
for c in net_new:
    if one("SELECT COUNT(*) FROM identifiers WHERE identifier=? AND identifier_type=?",
           c["value"], c["identifier_type"])[0]:
        die(f"net-new already present: {c['value']}/{c['identifier_type']}")
# 2 held absent (sanity — they are net-new too, just not promoted)
for c in held:
    if one("SELECT COUNT(*) FROM identifiers WHERE identifier=? AND identifier_type='ssid_pattern'",
           c["value"])[0]:
        die(f"held value unexpectedly present: {c['value']}")

# grantee pairing anchors that are already_in_db (N7N) must exist
n7n = one("SELECT id FROM identifiers WHERE identifier='N7N' AND identifier_type='fcc_grantee_code' "
          "AND superseded_by IS NULL")
if not n7n:
    die("N7N grantee (pairing anchor) absent")
N7N_ID = n7n[0]

# Work Item B preconditions — exact current state
for rid, (oui, db_says, _ieee) in OUI_WITHDRAW.items():
    r = one("SELECT identifier, manufacturer, identifier_type, superseded_by FROM identifiers WHERE id=?", rid)
    if not r: die(f"OUI row {rid} absent")
    if r["identifier"] != oui: die(f"OUI {rid} identifier {r['identifier']} != {oui}")
    if r["identifier_type"] != "oui": die(f"OUI {rid} not type oui")
    if r["manufacturer"] != db_says: die(f"OUI {rid} manufacturer {r['manufacturer']} != {db_says}")
    if r["superseded_by"] is not None: die(f"OUI {rid} already superseded")
ncv = one("SELECT identifier, manufacturer, device_category, source_type, source_url, confidence FROM "
          "identifiers WHERE id=?", NCV_ID)
if not ncv or ncv["identifier"] != "NCV": die("NCV row 42948 not as expected")
if ncv["manufacturer"] != "Vigilant Solutions" or ncv["device_category"] != "alpr":
    die(f"NCV preconditions changed: mfr={ncv['manufacturer']} cat={ncv['device_category']}")
lin = one("SELECT identifier, manufacturer FROM identifiers WHERE id=?", LINEAGE_ID)
if not lin or lin["identifier"] != "00:14:3E": die("lineage row 35588 not as expected")

# json_valid sweep BEFORE over Work-Item-B mutation scope (the 6 existing rows we edit)
b_scope = list(OUI_WITHDRAW) + [NCV_ID, LINEAGE_ID]
bad = [i for i in b_scope if one(
    "SELECT CASE WHEN notes IS NULL THEN 1 WHEN json_valid(notes)=1 THEN 1 ELSE 0 END "
    "FROM identifiers WHERE id=?", i)[0] == 0]
if bad:
    die(f"non-JSON notes in Work-Item-B scope BEFORE: {bad}")
print(f"[precond] ok  net_new=14 (ssid6/grantee5/equip3) held=2 behavioral=2  "
      f"workB_scope={len(b_scope)} json_valid_before=clean  N7N_id={N7N_ID}")

# ==================================================================================
# MUTATIONS (single transaction)
# ==================================================================================
proof = {"issue": ISSUE, "extraction_issue": "MAC-372", "parent": "MAC-363",
         "applied_utc": NOW, "candidates_sha256": CANDS_SHA, "db_pre_sha256": pre_sha,
         "backup": bak, "source_mints": [], "inserts": [], "behavioral_inserts": [],
         "pairings": [], "held": [], "oui_withdrawals": [], "ncv_reattribution": {},
         "lineage_note": {}}
INS = ("INSERT INTO identifiers(identifier,identifier_type,device_category,manufacturer,model,"
       "confidence,source_url,source_type,source_excerpt,first_seen,last_verified,notes,"
       "paired_identifier_id,pair_kind) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
try:
    cur.execute("BEGIN")

    # A. mint 2 manufacturer_app sources
    src_id = {}
    for key, s in need_sources.items():
        apk_rel = SRC_URL[key].replace(
            "argus-internal://mac365_cohort2_alpr/vendor_apps/", "raw/vendor_apps/")
        notes = json.dumps({"package": key.split(":", 1)[1], "sha256": s["sha256"],
                            "apk_relative_path": apk_rel,
                            "harvest": "MAC-365 apkcombo/playwright fetch (per MAC-349)",
                            "decompiled_source_committed": False, "policy": "§11 #15 — APK binary "
                            "gitignored at raw/vendor_apps/…; decompiled source never in git index",
                            "minted_by": ISSUE, "minted_utc": NOW,
                            "cohort": "MAC-363 cohort2 ALPR/cop-car"}, ensure_ascii=False)
        cur.execute("INSERT INTO sources(name,url,source_type,tier,last_fetched_at,last_status,notes) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (s["proposed_name"], SRC_URL[key], "manufacturer_app", 3, NOW,
                     "minted_mac375", notes))
        src_id[key] = cur.lastrowid
        proof["source_mints"].append({"key": key, "id": cur.lastrowid, "url": SRC_URL[key],
                                      "source_type": "manufacturer_app", "tier": 3})

    new_id = {}  # (type,value) -> id

    def insert_identifier(c, conf, stype, extra_notes, paired=None, pair_kind=None):
        notes = {"stage": "mac372_ingest", "issue": ISSUE, "extraction_issue": "MAC-372",
                 "applied_utc": NOW, "source_sid": c["source_sid"], "source_lens": c["source_lens"],
                 "device_category": c["device_category"], "proposed_ceiling": c["proposed_confidence_ceiling"],
                 "confidence_basis": f"§8.2 {stype} band -> {conf}", "candidate_notes": c["notes"]}
        if c.get("conflict_note"):
            notes["conflict_note"] = c["conflict_note"]
        notes.update(extra_notes)
        cur.execute(INS, (c["value"], c["identifier_type"], c["device_category"],
                          c["manufacturer"], None, conf, c["source_url"], stype,
                          (c["cite_excerpt"] or "")[:200], NOW, NOW,
                          json.dumps(notes, ensure_ascii=False), paired, pair_kind))
        rid = cur.lastrowid
        new_id[(c["identifier_type"], c["value"])] = rid
        proof["inserts"].append({"id": rid, "type": c["identifier_type"], "value": c["value"],
                                 "confidence": conf, "source_type": stype,
                                 "device_category": c["device_category"]})
        return rid

    # B. grantees (primary_registry @85)
    for c in grantee:
        insert_identifier(c, CONF["fcc_grantee_code"], STYPE["fcc_grantee_code"],
                          {"registry": "FCC EAS frozen sid7 (sha 5cd60fbe…)",
                           "pii": "PII-stripped per §11 #3 — code/name/city/state only"})

    # C. equipment_class_code (regulatory @75, anchored band per CTO caveat)
    for c in equip:
        gcode = EQUIP_GRANTEE[c["value"]]
        # resolve grantee identifier id for §11#7 pairing
        if gcode in (g["value"] for g in grantee):
            gid = new_id[("fcc_grantee_code", gcode)]
        else:                                   # N7N already_in_db
            gid = N7N_ID
        rid = insert_identifier(
            c, CONF["equipment_class_code"], STYPE["equipment_class_code"],
            {"fcc_id_resolution": FCC_ID_CONFIRM[c["value"]],
             "band_rationale": "CTO honest-absent caveat: grant-exhibit/frequency-band not "
                               "fetched; sid85 fcc.report is a live (not frozen) third-party "
                               "mirror; confidence anchored to established equipment_class_code "
                               "band (75) — NOT the proposed 90 which exceeds the entire type.",
             "paired_grantee": gcode, "section_11_7": "fcc_grantee_equipment_class pairing"},
            paired=gid, pair_kind="fcc_grantee_equipment_class")
        proof["pairings"].append({"equip_id": rid, "equip": c["value"], "grantee_code": gcode,
                                  "grantee_id": gid, "pair_kind": "fcc_grantee_equipment_class"})

    # D. back-reference: VTF grantee -> VTFADM3 equip (both new). N7N left untouched (already_in_db).
    vtf_id = new_id.get(("fcc_grantee_code", "VTF"))
    vtfadm3_id = new_id.get(("equipment_class_code", "VTFADM3"))
    if vtf_id and vtfadm3_id:
        gn = one("SELECT notes FROM identifiers WHERE id=?", vtf_id)["notes"]
        cur.execute("UPDATE identifiers SET paired_identifier_id=?, pair_kind=?, notes=? WHERE id=?",
                    (vtfadm3_id, "fcc_grantee_equipment_class",
                     merge_notes_json(gn, {"paired_equipment_class": "VTFADM3",
                                           "section_11_7": "fcc_grantee_equipment_class pairing"}),
                     vtf_id))
        proof["pairings"].append({"grantee_id": vtf_id, "grantee": "VTF", "equip_id": vtfadm3_id,
                                  "equip": "VTFADM3", "pair_kind": "fcc_grantee_equipment_class",
                                  "direction": "grantee->equip back-ref"})

    # E. ssid_pattern (crowdsourced @75; §11#16 facts-only, NO_LICENSE_DECLARED verified on disk)
    for c in ssid:
        insert_identifier(c, CONF["ssid_pattern"], STYPE["ssid_pattern"],
                          {"upstream_license_posture": "NO_LICENSE_DECLARED",
                           "license_basis": "§11 #16 Feist facts-only; MaxwellDPS/Flock-You-Android "
                                            "extract has no LICENSE file (verified on disk 2026-06-13)",
                           "export": "§4.4 ssid_pattern DROPPED from both Lynceus exports (no regex v0.2)"})

    # F. behavioral_signatures (manufacturer_app @80)
    for b in behav:
        key = b["source_ref"].replace("needs_new_source_row:", "", 1)
        sid = src_id[key]
        notes = {"stage": "mac372_ingest", "issue": ISSUE, "applied_utc": NOW,
                 "apk_relative_path": b["relative_path"], "apk_evidence_check": b["apk_evidence_check"],
                 "confidence_basis": f"§8.2 manufacturer_app band -> {BEHAVIORAL_CONF}",
                 "candidate_notes": b["notes"],
                 "policy": "§11 #15 — DEX class descriptors only; decompiled source not committed"}
        cur.execute(
            "INSERT INTO behavioral_signatures(signature_name,cellular_generation,threshold_json,"
            "evidence_json,source_id,source_file_relative,source_line,confidence,device_category,notes) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (b["signature_name"], None, None, json.dumps(b["evidence"], ensure_ascii=False),
             sid, b["relative_path"], None, BEHAVIORAL_CONF, b["device_category"],
             json.dumps(notes, ensure_ascii=False)))
        proof["behavioral_inserts"].append({"id": cur.lastrowid, "signature_name": b["signature_name"],
                                            "source_id": sid, "confidence": BEHAVIORAL_CONF,
                                            "device_category": b["device_category"]})

    # held — record only (NOT promoted)
    for c in held:
        proof["held"].append({"type": c["identifier_type"], "value": c["value"],
                              "recommend_confidence": c["recommend_confidence"],
                              "reason": "ruling #8 weak/uncited repo sourcing — 2nd independent "
                                        "source required before promotion"})

    # ── WORK ITEM B ───────────────────────────────────────────────────────────────
    # 4 OUI withdrawals (superseded_by self-loop; MAC-217 mechanic). manufacturer/confidence/
    # source_type/source_url UNCHANGED (preserve audit trail; notes carry the disposition).
    for rid, (oui, db_says, ieee) in OUI_WITHDRAW.items():
        ex = one("SELECT notes, device_category, confidence FROM identifiers WHERE id=?", rid)
        patch = {"mac375_withdrawal": {
            "applied_utc": NOW, "issue": ISSUE, "mechanic": "superseded_by_self_loop",
            "reason": "oui_misattribution_vs_ieee",
            "db_said": db_says, "ieee_ground_truth": ieee,
            "ieee_source": "raw/ieee_oui/20260613T203034Z_oui.csv (sid1, authoritative)",
            "rationale": "OUI-not-bulk (ruling #1): vendor came from flock-you bundled hardcoded "
                         "list, which Argus's own IEEE registry contradicts. Corrected vendor has "
                         "no surveillance nexus → withdraw rather than re-attribute.",
            "export_note": ("device_category='unknown' → already §11#13-excluded; zero export delta"
                            if ex["device_category"] == "unknown"
                            else "device_category!=unknown → export-eligible; withdrawal removes from "
                                 "standard Lynceus export (oui type exported). Flag CTO push-gate."),
            "validator_confirm_requested": True}}
        cur.execute("UPDATE identifiers SET superseded_by=?, last_verified=?, notes=? WHERE id=?",
                    (rid, NOW, merge_notes_json(ex["notes"], patch), rid))
        proof["oui_withdrawals"].append({"id": rid, "oui": oui, "db_said": db_says,
                                         "ieee": ieee, "device_category": ex["device_category"],
                                         "confidence": ex["confidence"],
                                         "export_eligible_before": ex["device_category"] != "unknown"})

    # NCV re-attribution (manufacturer + device_category only; band/conf/url untouched →
    # no source_reclassifications entry, and pre_confidence is NULL so one is impossible anyway).
    ex = one("SELECT notes FROM identifiers WHERE id=?", NCV_ID)
    patch = {"mac375_reattribution": {
        "applied_utc": NOW, "issue": ISSUE,
        "manufacturer_change": {"from": "Vigilant Solutions", "to": "Vigilant Systems Inc"},
        "device_category_change": {"from": "alpr", "to": "unknown"},
        "reason": "frozen FCC sid7 grantee NCV = 'Vigilant Systems Inc' (Klamath Falls OR, reg "
                  "1998) — a DIFFERENT entity from the Vigilant Solutions ALPR vendor. Not a "
                  "confirmed ALPR maker → device_category alpr→unknown.",
        "fields_unchanged": "source_type/source_url/confidence (confidence is NULL; pre-existing — "
                            "flagged for Validator, out of scope here)",
        "validator_confirm_requested": True}}
    cur.execute("UPDATE identifiers SET manufacturer=?, device_category=?, last_verified=?, notes=? "
                "WHERE id=?", ("Vigilant Systems Inc", "unknown", NOW,
                               merge_notes_json(ex["notes"], patch), NCV_ID))
    proof["ncv_reattribution"] = {"id": NCV_ID, "manufacturer": "Vigilant Solutions->Vigilant Systems Inc",
                                  "device_category": "alpr->unknown"}

    # 35588 soft lineage note (no field change)
    ex = one("SELECT notes FROM identifiers WHERE id=?", LINEAGE_ID)
    patch = {"mac375_lineage_note": {
        "applied_utc": NOW, "issue": ISSUE,
        "note": "IEEE registrant for 00:14:3E is 'AirLink Communications, Inc.', acquired by "
                "Sierra Wireless (2007) → Sierra Wireless AirLink product line. DB label 'Sierra "
                "Wireless' is defensible lineage. NOT a mis-attribution; kept as-is."}}
    cur.execute("UPDATE identifiers SET notes=? WHERE id=?",
                (merge_notes_json(ex["notes"], patch), LINEAGE_ID))
    proof["lineage_note"] = {"id": LINEAGE_ID, "oui": "00:14:3E", "action": "lineage note added; no field change"}

    con.commit()
except Exception as e:
    con.rollback()
    die(f"transaction failed (rolled back): {e!r}")

# ==================================================================================
# POST-WRITE VERIFICATION
# ==================================================================================
if one("SELECT MAX(version) FROM schema_version")[0] != 31:
    die("schema_version drifted from 31")

# json_valid sweep AFTER over full mutation scope (14 new + 6 Work-B + 2 grantee back-ref subset)
all_ident = [r["id"] for r in proof["inserts"]] + b_scope + ([vtf_id] if vtf_id else [])
all_ident = sorted(set(all_ident))
badp = [i for i in all_ident if one(
    "SELECT CASE WHEN notes IS NULL THEN 1 WHEN json_valid(notes)=1 THEN 1 ELSE 0 END "
    "FROM identifiers WHERE id=?", i)[0] == 0]
beh_ids = [b["id"] for b in proof["behavioral_inserts"]]
badb = [i for i in beh_ids if one(
    "SELECT CASE WHEN notes IS NULL THEN 1 WHEN json_valid(notes)=1 THEN 1 ELSE 0 END "
    "FROM behavioral_signatures WHERE id=?", i)[0] == 0]
if badp or badb:
    die(f"non-JSON notes AFTER: identifiers={badp} behavioral={badb}")

post_sha = sha256_file(DB)
proof["db_post_sha256"] = post_sha
proof["counts"] = {
    "net_new_inserted": len(proof["inserts"]),
    "by_type": {t: sum(1 for x in proof["inserts"] if x["type"] == t)
                for t in ("ssid_pattern", "fcc_grantee_code", "equipment_class_code")},
    "behavioral_inserts": len(proof["behavioral_inserts"]),
    "source_mints": len(proof["source_mints"]),
    "held_not_promoted": len(proof["held"]),
    "oui_withdrawals": len(proof["oui_withdrawals"]),
    "oui_withdrawals_export_eligible": sum(1 for x in proof["oui_withdrawals"]
                                           if x["export_eligible_before"]),
    "ncv_reattributed": 1, "lineage_notes": 1,
    "pairings": len(proof["pairings"]),
    "schema_version": 31, "json_valid_after": "clean",
}
proof["totals_after"] = {
    "identifiers_total": one("SELECT COUNT(*) FROM identifiers")[0],
    "identifiers_active": one("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL")[0],
    "sources": one("SELECT COUNT(*) FROM sources")[0],
    "behavioral_signatures": one("SELECT COUNT(*) FROM behavioral_signatures")[0],
}
con.close()

os.makedirs("operator_review/MAC-375", exist_ok=True)
with open("operator_review/MAC-375/promotion_proof.json", "w") as f:
    json.dump(proof, f, indent=2, ensure_ascii=False)
print(json.dumps(proof["counts"], indent=2))
print("totals_after:", proof["totals_after"])
print("post_sha:", post_sha)
print("proof -> operator_review/MAC-375/promotion_proof.json")
