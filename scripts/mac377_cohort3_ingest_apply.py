#!/usr/bin/env python3
"""MAC-377 — Cohort 3 (Drones) INGEST — Work-A ONLY (additive, zero export delta).

Lands the CTO-ratified (MAC-374) additive deliverables from
``extraction_outputs/mac366_cohort3_drones/candidates.json``:

  Work-A#1  3 new ``sources`` rows (source_type='manufacturer_app'), each carrying
            its CTO-verified sha256 (re-verified against the on-disk artifact here)
            and a ``notes.upstream_license_posture`` sentinel (canonical key, CP21).
  Work-A#2  5 new ``behavioral_signatures`` rows (device_category='drone'), evidence
            arrays pulled verbatim from the ratified candidates.json (cite-faithful).
  Work-A#3  Footprint corroboration on the 8 non-remediation already-in-DB identifier
            rows via a single namespaced ``notes`` property-merge (json_set) — NO §8.3
            +5 lift (hub-and-spoke same-vendor-across-types is NOT value corroboration).

Work-B (shipped-registry remediation: 3 HARD re-attributions / 4 SOFT category /
6 DJI recats) is INTENTIONALLY NOT APPLIED here. It is a row-level reclassification
(band / confidence / source_url change) that per §11 #8 / CP19 requires a
``source_reclassifications`` audit entry in the same transaction AND, per the Work-B
section header, a Validator cross-check on the FP-triage dispositions. It is held for
the CTO to route to the Validator. See operator_review/MAC-377/ingest_proof.md.

Migration-safety: backup-first (.bak with pre-sha), schema stays 31, notes merges are
JSON property-merge (json_set, never text-suffix concat — CP39 lesson), json_valid
sweep pre/post. Idempotent: re-running skips rows already present.
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

# Work-A#3 footprint scope: the already-in-DB rows that are NOT subject to Work-B
# remediation (the 6 DJI recat rows 37138/37142/37173/37174/37175/37176 are
# deliberately excluded — they will be touched in the held Work-B pass).
FOOTPRINT_IDS = [2872, 4884, 23052, 42862, 42871, 42873, 42892, 42893]

# Work-A#1 — new manufacturer_app source rows. sha256 is re-verified vs the on-disk
# artifact before any write.
NEW_SOURCES = [
    {
        "name": "Skydio (com.skydio.r3@24.10.48)",
        "package": "com.skydio.r3",
        "version": "24.10.48",
        "ext": "xapk",
        "sha256": "af538197b7a1116ee1b86d607e716583c16978c0673cc5f4890dbbb108b61b11",
        "disk_path": "raw/vendor_apps/skydio/com.skydio.r3/24.10.48/af538197b7a1116ee1b86d607e716583c16978c0673cc5f4890dbbb108b61b11.xapk",
        "note": "XAPK split bundle; base com.skydio.r3.apk. Carries jcabremoteid Remote-ID module.",
    },
    {
        "name": "Skydio Enterprise (com.skydio.enterprise@24.10.48)",
        "package": "com.skydio.enterprise",
        "version": "24.10.48",
        "ext": "xapk",
        "sha256": "4bfb561d07c5f57ce3f81b9e7be7d4b31c5d0fd6a71e810b00519cf58d95818c",
        "disk_path": "raw/vendor_apps/skydio/com.skydio.enterprise/24.10.48/4bfb561d07c5f57ce3f81b9e7be7d4b31c5d0fd6a71e810b00519cf58d95818c.xapk",
        "note": "XAPK split bundle; shares jcabremoteid module with com.skydio.r3.",
    },
    {
        "name": "Autel Explorer (com.autel.explorer@V1.0.1.45)",
        "package": "com.autel.explorer",
        "version": "V1.0.1.45",
        "ext": "apk",
        "sha256": "02eb9df046016fe338371afd64aff00849f1d90a1384302361dc3dab1737700f",
        "disk_path": "raw/vendor_apps/autel/com.autel.explorer/V1.0.1.45/02eb9df046016fe338371afd64aff00849f1d90a1384302361dc3dab1737700f.apk",
        "note": "Plain APK; the ONLY Autel drone companion (MAC-366/374 ruling 3).",
    },
]

LICENSE_POSTURE = "proprietary_vendor_app_standard_RE_clause"
# Canonical sentinel key per CP21 (notes.upstream_license_posture).
UPSTREAM_LICENSE_POSTURE = "proprietary_vendor_app_static_analysis_only"
POLICY_15 = (
    "§11 #15 — APK/XAPK binary gitignored at raw/vendor_apps/…; decompiled source never "
    "in git index; DMCA §1201 + 37 CFR §201.40(b) reverse-engineering exemption envelope"
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
    candidates = json.loads(CANDIDATES.read_text())

    # ---- sha re-verify of each on-disk artifact (provenance honesty) -------------
    for s in NEW_SOURCES:
        p = REPO / s["disk_path"]
        if not p.exists():
            print(f"FATAL: artifact missing: {p}", file=sys.stderr)
            return 2
        got = sha256_of(p)
        if got != s["sha256"]:
            print(f"FATAL: sha mismatch {s['package']}: disk={got} expected={s['sha256']}", file=sys.stderr)
            return 2
        print(f"  sha-ok  {s['package']}: {got}")

    # ---- backup-first ------------------------------------------------------------
    pre_sha = sha256_of(DB)
    bak = DB.with_name(f"argus.db.mac377_pre_apply_{stamp}_{pre_sha[:12]}.bak")
    shutil.copy2(DB, bak)
    print(f"\nBACKUP  {bak.name}  (pre-sha {pre_sha})")

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    cur = con.cursor()

    def count(sql: str, args=()) -> int:
        return cur.execute(sql, args).fetchone()[0]

    # ---- BEFORE snapshot ---------------------------------------------------------
    before = {
        "sources": count("SELECT COUNT(*) FROM sources"),
        "behavioral": count("SELECT COUNT(*) FROM behavioral_signatures"),
        "ident_total": count("SELECT COUNT(*) FROM identifiers"),
        "ident_active": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"),
        "schema_max": count("SELECT MAX(version) FROM schema_version"),
        "user_version": count("PRAGMA user_version"),
    }
    qmarks = ",".join("?" * len(FOOTPRINT_IDS))
    jv_before = count(
        f"SELECT COUNT(*) FROM identifiers WHERE id IN ({qmarks}) AND json_valid(notes)=1",
        FOOTPRINT_IDS,
    )
    print(f"\nBEFORE  sources={before['sources']} behavioral={before['behavioral']} "
          f"ident_total={before['ident_total']} ident_active={before['ident_active']} "
          f"schema_max={before['schema_max']} user_version={before['user_version']}")
    print(f"        json_valid footprint rows = {jv_before}/{len(FOOTPRINT_IDS)}")

    cur.execute("BEGIN")

    # ---- Work-A#1: sources -------------------------------------------------------
    src_id_by_pkg: dict[str, int] = {}
    new_src_ids = []
    for s in NEW_SOURCES:
        url = f"argus-internal://mac366_cohort3_drones/vendor_apps/{s['package']}/{s['version']}/{s['sha256']}.{s['ext']}"
        existing = cur.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
        if existing:
            src_id_by_pkg[s["package"]] = existing[0]
            print(f"  source SKIP (exists id={existing[0]}) {s['package']}")
            continue
        notes = {
            "package": s["package"],
            "version": s["version"],
            "sha256": s["sha256"],
            "apk_format": s["ext"],
            "apk_relative_path": s["disk_path"],
            "harvest": "MAC-366 apkcombo/playwright fetch (per MAC-349); CTO-verified MAC-374",
            "decompiled_source_committed": False,
            "license_posture": LICENSE_POSTURE,
            "upstream_license_posture": UPSTREAM_LICENSE_POSTURE,
            "eula_posture": "standard-RE-clause",
            "policy": POLICY_15,
            "minted_by": "MAC-377",
            "minted_utc": now,
            "cohort": "MAC-363 cohort3 drones",
            "note": s["note"],
        }
        cur.execute(
            "INSERT INTO sources (name, url, source_type, tier, last_fetched_at, last_status, notes) "
            "VALUES (?,?,?,?,?,?,?)",
            (s["name"], url, "manufacturer_app", 3, now, "minted_mac377", json.dumps(notes)),
        )
        sid = cur.lastrowid
        src_id_by_pkg[s["package"]] = sid
        new_src_ids.append(sid)
        print(f"  source INSERT id={sid} {s['package']}")

    # ---- Work-A#2: behavioral_signatures ----------------------------------------
    def resolve_source_id(ref) -> int:
        if isinstance(ref, int):
            return ref
        if ref == "needs_new_source_row:app:com.skydio.r3":
            return src_id_by_pkg["com.skydio.r3"]
        if ref == "needs_new_source_row:app:com.autel.explorer":
            return src_id_by_pkg["com.autel.explorer"]
        raise ValueError(f"unmapped source_ref: {ref!r}")

    new_beh_ids = []
    for b in candidates["behavioral_signatures"]:
        src_id = resolve_source_id(b["source_ref"])
        name = b["signature_name"]
        existing = cur.execute(
            "SELECT id FROM behavioral_signatures WHERE signature_name=? AND source_id=? "
            "AND cellular_generation IS NULL",
            (name, src_id),
        ).fetchone()
        if existing:
            print(f"  behavioral SKIP (exists id={existing[0]}) {name[:50]}…")
            continue
        conf = b["proposed_confidence_ceiling"]
        notes = {
            "stage": "mac374_extraction_ingest",
            "issue": "MAC-377",
            "applied_utc": now,
            "source_ref": b["source_ref"],
            "source_lens": b["source_lens"],
            "confidence_basis": f"§8.2 source-band ceiling → {conf} (researcher-confidence discarded)",
            "candidate_notes": b["notes"],
            "apk_evidence_check": b["apk_evidence_check"],
            "policy": "§11 #15 — DEX class descriptors only; decompiled source not committed"
            if b["apk_evidence_check"] == "verified"
            else "§11 #1 — structural authority; behavioral pattern, not an identifier value",
        }
        cur.execute(
            "INSERT INTO behavioral_signatures "
            "(signature_name, cellular_generation, threshold_json, evidence_json, source_id, "
            " source_file_relative, source_line, confidence, device_category, notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                name,
                None,
                None,
                json.dumps(b["evidence"]),
                src_id,
                b["relative_path"],
                None,
                conf,
                b["device_category"],
                json.dumps(notes),
            ),
        )
        bid = cur.lastrowid
        new_beh_ids.append(bid)
        print(f"  behavioral INSERT id={bid} src={src_id} conf={conf} {name[:45]}…")

    # ---- Work-A#3: footprint corroboration (notes property-merge, NO +5 lift) ----
    footprint = {
        "cohort": "MAC-363 cohort3 drones",
        "issue": "MAC-377",
        "applied_utc": now,
        "corroboration": "additive footprint only — NO §8.3 +5 lift; hub-and-spoke "
        "(same vendor across identifier types) is NOT value-level corroboration "
        "(§8.3 + §11 #8). Confidence/band/source_url unchanged.",
        "ratified_at": "MAC-374 (operator_review/MAC-374/ratification_proof.md)",
    }
    fp_changed = []
    for rid in FOOTPRINT_IDS:
        row = cur.execute(
            "SELECT json_valid(notes), json_extract(notes,'$.mac377_cohort3_footprint') "
            "FROM identifiers WHERE id=?",
            (rid,),
        ).fetchone()
        if not row or row[0] != 1:
            print(f"  footprint SKIP (notes not json) id={rid}")
            continue
        if row[1] is not None:
            print(f"  footprint SKIP (already set) id={rid}")
            continue
        cur.execute(
            "UPDATE identifiers SET notes=json_set(notes,'$.mac377_cohort3_footprint', json(?)) WHERE id=?",
            (json.dumps(footprint), rid),
        )
        fp_changed.append(rid)
    print(f"  footprint UPDATE rows={fp_changed}")

    # ---- AFTER snapshot + json_valid sweep over full mutation scope ---------------
    after = {
        "sources": count("SELECT COUNT(*) FROM sources"),
        "behavioral": count("SELECT COUNT(*) FROM behavioral_signatures"),
        "ident_total": count("SELECT COUNT(*) FROM identifiers"),
        "ident_active": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"),
        "schema_max": count("SELECT MAX(version) FROM schema_version"),
        "user_version": count("PRAGMA user_version"),
    }
    jv_after_fp = count(
        f"SELECT COUNT(*) FROM identifiers WHERE id IN ({qmarks}) AND json_valid(notes)=1",
        FOOTPRINT_IDS,
    )
    jv_new_src = count(
        "SELECT COUNT(*) FROM sources WHERE last_status='minted_mac377' AND json_valid(notes)=1"
    )
    jv_new_beh = 0
    if new_beh_ids:
        bm = ",".join("?" * len(new_beh_ids))
        jv_new_beh = count(
            f"SELECT COUNT(*) FROM behavioral_signatures WHERE id IN ({bm}) "
            f"AND json_valid(notes)=1 AND json_valid(evidence_json)=1",
            new_beh_ids,
        )

    # ---- invariants --------------------------------------------------------------
    problems = []
    if after["schema_max"] != 31 or after["user_version"] != before["user_version"]:
        problems.append(f"schema drift: {before} -> {after}")
    if after["ident_total"] != before["ident_total"]:
        problems.append("identifier row count changed (Work-A must be 0 net-new values)")
    if after["ident_active"] != before["ident_active"]:
        problems.append("identifier active count changed")
    if jv_after_fp != len(FOOTPRINT_IDS):
        problems.append(f"json_valid footprint regressed: {jv_after_fp}/{len(FOOTPRINT_IDS)}")
    if new_src_ids and jv_new_src < len(new_src_ids):
        problems.append("new source notes not all json_valid")
    if new_beh_ids and jv_new_beh < len(new_beh_ids):
        problems.append("new behavioral notes/evidence not all json_valid")

    print("\n=== RECON ===")
    print(f"  sources    {before['sources']} -> {after['sources']}  (+{after['sources']-before['sources']})  new_ids={new_src_ids}")
    print(f"  behavioral {before['behavioral']} -> {after['behavioral']}  (+{after['behavioral']-before['behavioral']})  new_ids={new_beh_ids}")
    print(f"  ident_total  {before['ident_total']} -> {after['ident_total']}  (must be +0)")
    print(f"  ident_active {before['ident_active']} -> {after['ident_active']}  (must be +0)")
    print(f"  footprint changed rows = {fp_changed}")
    print(f"  json_valid: footprint={jv_after_fp}/{len(FOOTPRINT_IDS)}  new_src={jv_new_src}/{len(new_src_ids)}  new_beh={jv_new_beh}/{len(new_beh_ids)}")
    print(f"  schema_max={after['schema_max']} user_version={after['user_version']}")

    if problems:
        con.rollback()
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
