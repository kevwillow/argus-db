#!/usr/bin/env python3
"""MAC-377 — Cohort 3 (Drones) Work-B — shipped-registry remediation.

Applies the CTO-ratified, Validator-cross-checked shipped-registry corrections from
``operator_review/MAC-377/workb_apply_brief.md`` (rulings in
``operator_review/MAC-377/cto_ratification.md`` §B). All 13 target identifier rows are
``identifier_type='fcc_grantee_code'`` = EXPORT-DROPPED → NET EXPORT DELTA = ZERO.

  #4 HARD  (CMJ 42883 / WQ8 42898 / XPR 42899) — withdraw-as-non-surveillance.
           ``superseded_by = id`` (tri-semantic self-loop = withdrawn-no-successor) +
           ``notes.mac377_workb_withdrawal`` audit key. NO mfr/cat/conf/source_* change.
           NO source_reclassifications row (no band/url/type/conf move occurs).
  #5 SOFT  (CHK 42935 / RKU 42954 / RKX 42955 / XNP 42957) — category demotion only.
           ``device_category='unknown'`` + ``notes.mac377_workb_recat`` audit key.
           KEEP manufacturer='Parrot'. KEEP confidence=NULL (do NOT synthesize a value —
           §11 #1). NO source_reclassifications row (conf=NULL + only device_category
           changes; pre_confidence is NOT NULL CHECK(0..100) so an audit row is mechanically
           impossible without a fabricated value — CTO ruling #5a). RKX gets a provenance_note.
  #6 RECAT (2AHAN 37138 / 2AHAY 37142 / 2ANDR 37173 / 2AS9V 37174 / 2AS9W 37175 /
           2AS9X 37176) — DJI drone-arm; cat unknown→drone, band crowdsourced/75 →
           primary_registry/85. Per row, ALL THREE writes in the SAME transaction:
             (1) INSERT raw_observations citing sid-7 directly (bible §8.2 L827 — third-party
                 fccid.io provenance requires a new registry-direct raw_observations row to
                 establish primary_registry; a bare relabel = §11 #8 violation).
             (2) UPDATE identifiers (cat→drone, source_type→primary_registry, conf→85,
                 source_url→opendata canonical) + ``notes.mac377_workb_recat`` audit key.
             (3) INSERT source_reclassifications (pre 75/crowdsourced/fccid.io →
                 post 85/primary_registry/opendata).
           Band target is primary_registry/85 (NOT regulatory/88 — CTO §B#6 OVERTURN;
           bible L822 ceiling 85 / L833 FCC EAS grantee→primary_registry).

Migration-safety (binding): backup-first (.bak with pre-sha), schema stays 31, notes merges
are JSON property-merge via json_set (NEVER text-suffix concat — CP39), json_valid sweep over
the FULL mutation scope pre AND post. Idempotent: skip any row already remediated.

In-TX invariants (rollback on any violation):
  - identifiers TOTAL unchanged (0 net-new values).
  - identifiers ACTIVE drops by EXACTLY 3 (the #4 self-loop withdrawals) and the 3 newly
    inactive rows are EXACTLY {42883,42898,42899}. (NB: the brief's migration-safety boilerplate
    says "active unchanged" — that is inherited from the additive Work-A apply and is
    inconsistent with #4's explicit withdrawal; the substantive ratified instruction is to
    withdraw via self-loop, which necessarily makes 3 rows inactive. Flagged in the proof.)
  - The ONLY identifier rows whose tracked columns change are the 13 targets.
  - All 13 are identifier_type='fcc_grantee_code' (export-dropped) — asserted explicitly.

NO push, NO release tag, NO CP mint. Hand back to CTO (0715773f) on completion.
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
CANDIDATES = REPO / "extraction_outputs" / "mac366_cohort3_drones" / "candidates.json"

OPENDATA_URL = "https://opendata.fcc.gov/resource/3b3k-34jp"
ANCHOR_BASE = "CTO 0715773f / Validator da137694"
FREEZE_DATE = "2021-03-22"  # FCC EAS frozen snapshot (MAC-374 proof L78 + candidates cite_excerpts)

HARD_IDS = {42883: "CMJ", 42898: "WQ8", 42899: "XPR"}                       # #4 withdraw
SOFT_IDS = {42935: "CHK", 42954: "RKU", 42955: "RKX", 42957: "XNP"}        # #5 cat→unknown
RECAT_IDS = {37138: "2AHAN", 37142: "2AHAY", 37173: "2ANDR",
             37174: "2AS9V", 37175: "2AS9W", 37176: "2AS9X"}              # #6 recat
ALL_IDS = list(HARD_IDS) + list(SOFT_IDS) + list(RECAT_IDS)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def loc_string(city: str, state: str, country: str) -> str:
    parts = [p for p in (city, state, country) if p and p.upper() != "N/A"]
    return ", ".join(parts)


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if not DB.exists():
        print(f"FATAL: DB missing at {DB}", file=sys.stderr)
        return 2

    # ---- cite_excerpt (PII-stripped, code/name/city/state/country) from ratified candidates.json
    cands = json.loads(CANDIDATES.read_text())
    excerpt_by_code: dict[str, str] = {}
    for c in cands["candidates"]:
        if c.get("identifier_type") == "fcc_grantee_code" and c.get("value") in RECAT_IDS.values():
            excerpt_by_code[c["value"]] = c["cite_excerpt"]
    missing = set(RECAT_IDS.values()) - set(excerpt_by_code)
    if missing:
        print(f"FATAL: cite_excerpt missing from candidates.json for {missing}", file=sys.stderr)
        return 2

    # ---- backup-first ------------------------------------------------------------
    pre_sha = sha256_of(DB)
    bak = DB.with_name(f"argus.db.mac377_workb_pre_apply_{stamp}_{pre_sha[:12]}.bak")
    shutil.copy2(DB, bak)
    print(f"BACKUP  {bak.name}  (pre-sha {pre_sha})")

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    cur = con.cursor()

    def one(sql: str, args=()):
        return cur.execute(sql, args).fetchone()

    def count(sql: str, args=()) -> int:
        return one(sql, args)[0]

    # ---- frozen-entity lookup from fcc_grantees (sid-7) — PII-stripped fields only
    frozen: dict[str, dict] = {}
    for code in (set(HARD_IDS.values()) | set(SOFT_IDS.values()) | set(RECAT_IDS.values())):
        row = one(
            "SELECT grantee_name, city, state, country FROM fcc_grantees "
            "WHERE source_id=7 AND grantee_code=?",
            (code,),
        )
        if not row:
            con.close()
            print(f"FATAL: no fcc_grantees(sid7) row for {code}", file=sys.stderr)
            return 2
        frozen[code] = {"name": row[0], "city": row[1], "state": row[2], "country": row[3]}

    # ---- BEFORE snapshot ---------------------------------------------------------
    before = {
        "ident_total": count("SELECT COUNT(*) FROM identifiers"),
        "ident_active": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"),
        "self_loop": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by = id"),
        "raw_obs": count("SELECT COUNT(*) FROM raw_observations"),
        "src_recl": count("SELECT COUNT(*) FROM source_reclassifications"),
        "schema_max": count("SELECT MAX(version) FROM schema_version"),
        "user_version": count("PRAGMA user_version"),
    }
    qmarks = ",".join("?" * len(ALL_IDS))
    # all 13 must be fcc_grantee_code (export-dropped) AND valid-JSON notes BEFORE we json_set
    types_before = cur.execute(
        f"SELECT id, identifier_type, json_valid(notes) FROM identifiers WHERE id IN ({qmarks})",
        ALL_IDS,
    ).fetchall()
    bad_type = [r[0] for r in types_before if r[1] != "fcc_grantee_code"]
    bad_json = [r[0] for r in types_before if r[2] != 1]
    if len(types_before) != len(ALL_IDS) or bad_type or bad_json:
        con.close()
        print(f"FATAL preflight: found={len(types_before)}/{len(ALL_IDS)} "
              f"non-fcc_grantee_code={bad_type} non-json-notes={bad_json}", file=sys.stderr)
        return 2
    print(f"BEFORE  ident_total={before['ident_total']} ident_active={before['ident_active']} "
          f"self_loop={before['self_loop']} raw_obs={before['raw_obs']} "
          f"src_recl={before['src_recl']} schema_max={before['schema_max']}")
    print(f"        preflight: 13/13 fcc_grantee_code + 13/13 json_valid(notes)  OK")

    cur.execute("BEGIN")

    new_raw_obs_ids: list[int] = []
    new_recl_ids: list[int] = []
    applied = {"hard": [], "soft": [], "recat": []}

    # ---- #4 HARD — withdraw via self-loop ---------------------------------------
    for rid, code in HARD_IDS.items():
        sup = one("SELECT superseded_by FROM identifiers WHERE id=?", (rid,))[0]
        if sup == rid:
            print(f"  #4 SKIP (already withdrawn self-loop) id={rid} {code}")
            continue
        fz = frozen[code]
        note = {
            "frozen_sid7_entity": fz["name"],
            "location": loc_string(fz["city"], fz["state"], fz["country"]),
            "rationale": ("automotive/OBD diagnostics — NOT the Autel drone arm (2AGNT/42873); "
                          "no valid §2.1 surveillance category → withdrawn-as-non-surveillance"),
            "anchor": f"MAC-377 Work-B #4 / {ANCHOR_BASE}",
        }
        cur.execute(
            "UPDATE identifiers SET superseded_by = id, "
            "notes = json_set(notes,'$.mac377_workb_withdrawal', json(?)) WHERE id=?",
            (json.dumps(note, ensure_ascii=False), rid),
        )
        applied["hard"].append(rid)
        print(f"  #4 WITHDRAW id={rid} {code} -> self-loop + withdrawal note ({fz['name']})")

    # ---- #5 SOFT — device_category drone->unknown -------------------------------
    for rid, code in SOFT_IDS.items():
        cat = one("SELECT device_category FROM identifiers WHERE id=?", (rid,))[0]
        if cat == "unknown" and one(
            "SELECT json_extract(notes,'$.mac377_workb_recat') FROM identifiers WHERE id=?", (rid,)
        )[0] is not None:
            print(f"  #5 SKIP (already recat) id={rid} {code}")
            continue
        fz = frozen[code]
        note = {
            "frozen_sid7_entity": fz["name"],
            "rationale": ("broader Parrot corporate group — not the drone SAS (2AG6I/42871); "
                          "cat 'drone'->'unknown' over-claim correction; mfr='Parrot' retained "
                          "(corporate group)"),
            "anchor": f"MAC-377 Work-B #5 / {ANCHOR_BASE}",
        }
        if rid == 42955:  # RKX — provenance inconsistency, documented not fixed
            note["provenance_note"] = (
                "row is regulatory/opendata while CHK/RKU/XNP are crowdsourced/fccid.io — "
                "provenance inconsistency noted, not fixed here (separate source-band question)"
            )
        cur.execute(
            "UPDATE identifiers SET device_category='unknown', "
            "notes = json_set(notes,'$.mac377_workb_recat', json(?)) WHERE id=?",
            (json.dumps(note, ensure_ascii=False), rid),
        )
        applied["soft"].append(rid)
        print(f"  #5 RECAT  id={rid} {code} -> cat=unknown (mfr=Parrot, conf=NULL kept)")

    # ---- #6 RECAT — raw_obs + identifiers UPDATE + source_reclassifications ------
    for rid, code in RECAT_IDS.items():
        live = one(
            "SELECT device_category, source_type, confidence, source_url FROM identifiers WHERE id=?",
            (rid,),
        )
        cat0, stype0, conf0, surl0 = live
        if cat0 == "drone" and stype0 == "primary_registry" and conf0 == 85:
            print(f"  #6 SKIP (already recat) id={rid} {code}")
            continue
        # preflight per-row: expected pre-state for a faithful reclassification audit
        if not (cat0 == "unknown" and stype0 == "crowdsourced" and conf0 == 75
                and surl0 == f"https://fccid.io/{code}"):
            con.rollback()
            con.close()
            print(f"FATAL #6 pre-state mismatch id={rid} {code}: "
                  f"cat={cat0} stype={stype0} conf={conf0} surl={surl0}", file=sys.stderr)
            return 1
        fz = frozen[code]
        excerpt = excerpt_by_code[code]
        if len(excerpt) > 200:
            con.rollback(); con.close()
            print(f"FATAL #6 source_excerpt >200 for {code}: {len(excerpt)}", file=sys.stderr)
            return 1

        # (1) raw_observations — registry-direct provenance (bible §8.2 L827)
        ro_notes = {
            "cohort": "MAC-363 cohort3 drones",
            "anchor": "MAC-377 Work-B #6",
            "basis": (f"FCC EAS frozen {FREEZE_DATE} sid-7 primary issuer — direct registry "
                      "provenance per bible §8.2 L827"),
        }
        cur.execute(
            "INSERT INTO raw_observations "
            "(source_id, source_url, candidate_identifier, candidate_type, candidate_category, "
            " candidate_manufacturer, source_excerpt, captured_at, promoted_identifier_id, notes) "
            "VALUES (7,?,?,?,?,?,?,?,?,?)",
            (OPENDATA_URL, code, "fcc_grantee_code", "drone", fz["name"], excerpt, now, rid,
             json.dumps(ro_notes, ensure_ascii=False)),
        )
        ro_id = cur.lastrowid
        new_raw_obs_ids.append(ro_id)

        # (2) identifiers UPDATE — recat + band correction + audit note
        id_note = {
            "frozen_sid7_entity": fz["name"],
            "rationale": ("DJI drone-arm per frozen sid-7 (CTO-verified MAC-374); cat unknown->drone; "
                          "band crowdsourced/75->primary_registry/85 per CP15 §8.2 strict reading "
                          "(bible L833 FCC EAS grantee->primary_registry); direct provenance "
                          "established via new raw_observations citing sid-7 in same TX (L827); "
                          "NOT a §8.3 corroboration drift"),
            "raw_observations_id": ro_id,
            "anchor": f"MAC-377 Work-B #6 / {ANCHOR_BASE} / bible §8.2 L822/827/833",
        }
        cur.execute(
            "UPDATE identifiers SET device_category='drone', source_type='primary_registry', "
            "confidence=85, source_url=?, "
            "notes = json_set(notes,'$.mac377_workb_recat', json(?)) WHERE id=?",
            (OPENDATA_URL, json.dumps(id_note, ensure_ascii=False), rid),
        )

        # (3) source_reclassifications — band-correction audit
        reason = (
            f"{code} — DJI drone-arm grantee ({fz['name']}) per frozen FCC EAS sid-7, CTO-verified "
            f"MAC-374. Band-correction crowdsourced/75 -> primary_registry/85 per CP15 §8.2 "
            f"(bible L833 names FCC EAS grantee->primary_registry; L822 ceiling 85). Direct "
            f"provenance established via new raw_observations (id={ro_id}) citing sid-7 in the same "
            f"transaction (bible L827, not a provenance shortcut). NOT a §8.3 corroboration lift."
        )
        cur.execute(
            "INSERT INTO source_reclassifications "
            "(identifier_id, sweep_event_id, pre_source_url, post_source_url, pre_source_type, "
            " post_source_type, pre_confidence, post_confidence, reclassification_reason, "
            " reclassification_anchor, notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (rid, "MAC-377-workb-6recat", surl0, OPENDATA_URL, stype0, "primary_registry",
             conf0, 85, reason,
             f"MAC-377 Work-B #6 / {ANCHOR_BASE} / bible §8.2 L822/827/833",
             json.dumps({"raw_observations_id": ro_id, "frozen_freeze_date": FREEZE_DATE},
                        ensure_ascii=False)),
        )
        rcl_id = cur.lastrowid
        new_recl_ids.append(rcl_id)
        applied["recat"].append(rid)
        print(f"  #6 RECAT  id={rid} {code} -> drone/primary_registry/85  raw_obs={ro_id} recl={rcl_id}")

    # ---- AFTER snapshot ----------------------------------------------------------
    after = {
        "ident_total": count("SELECT COUNT(*) FROM identifiers"),
        "ident_active": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"),
        "self_loop": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by = id"),
        "raw_obs": count("SELECT COUNT(*) FROM raw_observations"),
        "src_recl": count("SELECT COUNT(*) FROM source_reclassifications"),
        "schema_max": count("SELECT MAX(version) FROM schema_version"),
        "user_version": count("PRAGMA user_version"),
    }

    # newly-inactive set must be exactly the #4 HARD ids
    new_self_loops = {
        r[0] for r in cur.execute(
            f"SELECT id FROM identifiers WHERE superseded_by = id AND id IN ({qmarks})", ALL_IDS
        ).fetchall()
    }
    # json_valid sweep over full mutation scope
    jv_idents = count(
        f"SELECT COUNT(*) FROM identifiers WHERE id IN ({qmarks}) AND json_valid(notes)=1", ALL_IDS
    )
    jv_ro = 0
    if new_raw_obs_ids:
        m = ",".join("?" * len(new_raw_obs_ids))
        jv_ro = count(
            f"SELECT COUNT(*) FROM raw_observations WHERE id IN ({m}) AND json_valid(notes)=1",
            new_raw_obs_ids,
        )
    jv_rcl = 0
    if new_recl_ids:
        m = ",".join("?" * len(new_recl_ids))
        jv_rcl = count(
            f"SELECT COUNT(*) FROM source_reclassifications WHERE id IN ({m}) "
            f"AND json_valid(notes)=1 AND length(reclassification_reason)>0 "
            f"AND length(reclassification_anchor)>0",
            new_recl_ids,
        )

    n_hard = len(applied["hard"])
    n_recat = len(applied["recat"])

    problems = []
    if after["schema_max"] != 31 or after["user_version"] != before["user_version"]:
        problems.append(f"schema drift {before['schema_max']}/{before['user_version']} -> "
                        f"{after['schema_max']}/{after['user_version']}")
    if after["ident_total"] != before["ident_total"]:
        problems.append("identifiers total changed (must be 0 net-new)")
    if after["ident_active"] != before["ident_active"] - n_hard:
        problems.append(f"active delta != -{n_hard} (got {after['ident_active']-before['ident_active']})")
    if after["self_loop"] != before["self_loop"] + n_hard:
        problems.append(f"self_loop delta != +{n_hard}")
    if new_self_loops != set(applied["hard"]):
        problems.append(f"newly self-looped {new_self_loops} != #4 set {set(applied['hard'])}")
    if after["raw_obs"] != before["raw_obs"] + len(new_raw_obs_ids):
        problems.append("raw_observations count delta mismatch")
    if after["src_recl"] != before["src_recl"] + len(new_recl_ids):
        problems.append("source_reclassifications count delta mismatch")
    if jv_idents != len(ALL_IDS):
        problems.append(f"json_valid(identifiers.notes) {jv_idents}/{len(ALL_IDS)}")
    if jv_ro != len(new_raw_obs_ids):
        problems.append(f"json_valid(raw_obs.notes) {jv_ro}/{len(new_raw_obs_ids)}")
    if jv_rcl != len(new_recl_ids):
        problems.append(f"json_valid/reason/anchor(src_recl) {jv_rcl}/{len(new_recl_ids)}")

    print("\n=== RECON (in-TX, pre-commit) ===")
    print(f"  ident_total  {before['ident_total']} -> {after['ident_total']}  (must be +0)")
    print(f"  ident_active {before['ident_active']} -> {after['ident_active']}  (must be -{n_hard})")
    print(f"  self_loop    {before['self_loop']} -> {after['self_loop']}  (must be +{n_hard})")
    print(f"  newly self-looped = {sorted(new_self_loops)}  (== #4 {sorted(applied['hard'])})")
    print(f"  raw_obs      {before['raw_obs']} -> {after['raw_obs']}  new_ids={new_raw_obs_ids}")
    print(f"  src_recl     {before['src_recl']} -> {after['src_recl']}  new_ids={new_recl_ids}")
    print(f"  json_valid:  idents={jv_idents}/{len(ALL_IDS)}  raw_obs={jv_ro}/{len(new_raw_obs_ids)} "
          f" src_recl={jv_rcl}/{len(new_recl_ids)}")
    print(f"  applied: hard={applied['hard']} soft={applied['soft']} recat={applied['recat']}")

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
    print(f"\nCOMMITTED. post-sha {post_sha}")
    print(f"backup={bak.name} pre-sha={pre_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
