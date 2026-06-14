#!/usr/bin/env python3
"""MAC-378 — Cohort 5 (Consumer surveillance) INGEST — staged shipped-registry write.

Lands the CTO-ratified (MAC-376) net-new deliverable from
``extraction_outputs/mac368_cohort5_consumer/candidates.json``:

  26 net-new ``oui`` rows (IEEE MA-L registry-of-record, source_sid=1):
      Ring (13) · Wyze Labs (5) · Arlo Technologies (3) · Blink/Amazon (5).
  All:  identifier_type='oui' · source_type='primary_registry' · confidence=85
        (§8.2 single-source ceiling) · device_category='cctv_camera'
        (§2.1 — `doorbell` enum absent, CEO flag) · geographic_scope='global'.

What is deliberately NOT written (ratification flags 1-4):
  * ``A4DA222`` — the one already_in_db candidate (mac_range a4:da:22:2/28 id 9748);
    filtered out here because its db_presence != 'net-new'. A duplicate oui row would
    be a type-collision. Guarded by an explicit exclusion assert.
  * 8 SIG ble_manufacturer_id rows (already @ device_category=unknown, export-banned).
  * 9 FCC grantee codes (already in fcc_grantees). Reference/attribution only.
  * The SoftAP behavioral signature + any ssid_pattern (export-excluded / §4.4-dropped).
  * 382 mixed-use OUIs (Amazon/Google/Netgear/Nest) — tally only, unscoped.

The canonical OUI storage form (re-queried: 652/688 existing rows match the
``XX:XX:XX`` lowercase colon-separated form, e.g. ``b8:a4:4f``) is applied:
the candidate raw value ``00B463`` is stored as ``00:b4:63``.

Migration-safety: backup-first (.bak with pre-sha), schema stays 31, notes are a
fresh JSON object (json.dumps) with a json_valid sweep pre/post. Reconstruction
diff vs the .bak confirms exactly +26 oui / 0 deleted / 0 unintended changes.
Idempotent: re-running skips any (identifier, identifier_type='oui') already present.

NO export regen. NO push. NO schema migration. NO CP mint.
See operator_review/MAC-378/ingest_proof.md.
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
CANDIDATES = REPO / "extraction_outputs" / "mac368_cohort5_consumer" / "candidates.json"

# Ratification flag 1 — this candidate value must NEVER be written as an oui row
# (already present as mac_range a4:da:22:2/28 id 9748). Explicit guard.
EXCLUDED_RAW = {"A4DA222"}

INGEST_DATE = "2026-06-13"  # raw oui.csv harvest stamp 20260613T203034Z


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_canonical_oui(raw: str) -> str:
    """``00B463`` -> ``00:b4:63`` (canonical lowercase colon-separated MA-L form)."""
    s = raw.strip().lower()
    if len(s) != 6 or any(ch not in "0123456789abcdef" for ch in s):
        raise ValueError(f"non-MA-L / malformed oui value: {raw!r}")
    return f"{s[0:2]}:{s[2:4]}:{s[4:6]}"


def parse_registrant(cite_excerpt: str, raw: str) -> str:
    """'MA-L,00B463,Ring LLC (IEEE MA-L registry)' -> 'Ring LLC'."""
    parts = cite_excerpt.split(",", 2)
    if len(parts) == 3:
        org = parts[2]
        # strip the trailing ' (IEEE MA-L registry)' annotation if present
        idx = org.rfind(" (IEEE")
        if idx != -1:
            org = org[:idx]
        return org.strip()
    return raw  # defensive fallback


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f%z")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if not DB.exists():
        print(f"FATAL: DB missing at {DB}", file=sys.stderr)
        return 2
    candidates = json.loads(CANDIDATES.read_text())

    # ---- select the 26 net-new oui candidates (A4DA222 filtered by db_presence) --
    netnew = [c for c in candidates["candidates"] if c["db_presence"] == "net-new"]
    declared = candidates["net_new_oui_total"]
    if len(netnew) != declared:
        print(f"FATAL: net-new count {len(netnew)} != declared {declared}", file=sys.stderr)
        return 2
    # Exclusion guard — A4DA222 must not be in the net-new set.
    for c in netnew:
        if c["value"] in EXCLUDED_RAW:
            print(f"FATAL: excluded value {c['value']} present in net-new set", file=sys.stderr)
            return 2
        if c["identifier_type"] != "oui":
            print(f"FATAL: non-oui candidate in net-new set: {c['value']}", file=sys.stderr)
            return 2

    # Build the row plan (transform + canonical-form de-dup self-check).
    plan = []
    seen = set()
    for c in netnew:
        canon = to_canonical_oui(c["value"])
        if canon in seen:
            print(f"FATAL: duplicate canonical oui within candidate set: {canon}", file=sys.stderr)
            return 2
        seen.add(canon)
        plan.append((canon, c))
    print(f"row plan: {len(plan)} net-new oui (A4DA222 excluded; declared net_new={declared})")

    # ---- backup-first ------------------------------------------------------------
    pre_sha = sha256_of(DB)
    bak = DB.with_name(f"argus.db.mac378_pre_apply_{stamp}_{pre_sha[:12]}.bak")
    shutil.copy2(DB, bak)
    print(f"BACKUP  {bak.name}  (pre-sha {pre_sha})")

    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys=ON")
    cur = con.cursor()

    def count(sql: str, args=()) -> int:
        return cur.execute(sql, args).fetchone()[0]

    before = {
        "ident_total": count("SELECT COUNT(*) FROM identifiers"),
        "ident_active": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"),
        "oui": count("SELECT COUNT(*) FROM identifiers WHERE identifier_type='oui'"),
        "mfrs": count("SELECT COUNT(*) FROM manufacturers"),
        "sources": count("SELECT COUNT(*) FROM sources"),
        "schema_max": count("SELECT MAX(version) FROM schema_version"),
        "user_version": count("PRAGMA user_version"),
    }
    print(f"\nBEFORE  ident_total={before['ident_total']} ident_active={before['ident_active']} "
          f"oui={before['oui']} mfrs={before['mfrs']} sources={before['sources']} "
          f"schema_max={before['schema_max']}")

    # ---- verify source sid 1 is the IEEE OUI registry (no new source row needed) -
    src1 = cur.execute("SELECT id, source_type, url FROM sources WHERE id=1").fetchone()
    if not src1 or "standards-oui.ieee.org" not in (src1[2] or ""):
        print(f"FATAL: source sid 1 not IEEE OUI registry: {src1}", file=sys.stderr)
        con.close()
        return 2

    cur.execute("BEGIN")

    new_ids = []
    skipped = []
    for canon, c in plan:
        existing = cur.execute(
            "SELECT id FROM identifiers WHERE identifier=? AND identifier_type='oui'",
            (canon,),
        ).fetchone()
        if existing:
            skipped.append((canon, existing[0]))
            print(f"  oui SKIP (exists id={existing[0]}) {canon}")
            continue
        registrant = parse_registrant(c["cite_excerpt"], c["value"])
        source_excerpt = f"MA-L {c['value']} {registrant}"[:200]
        notes = {
            "stage": "mac376_extraction_ingest",
            "issue": "MAC-378",
            "applied_utc": now,
            "cohort": "MAC-363 cohort5 consumer surveillance",
            "manufacturer_brand": c["manufacturer"],
            "matched_registrant": registrant,
            "registry": "MA-L",
            "source_lens": c["source_lens"],
            "raw_value": c["value"],
            "relative_path": c["relative_path"],
            "cite_excerpt": c["cite_excerpt"],
            "confidence_basis": "§8.2 primary_registry single-source ceiling = 85 "
            "(IEEE OUI registry-of-record; researcher/vendor confidence discarded)",
            "no_83_lift": "§8.3 hub-and-spoke (same vendor across id-types) is NOT "
            "value-level corroboration; FCC grantee corroborates vendor not OUI value "
            "-> no +5 lift, stays at 85.",
            "taxonomy_flag": "device_category=cctv_camera placeholder; `doorbell` absent "
            "from §2.1 enum (Ring/Blink video doorbells). CEO flag at push-gate "
            "(mirrors MAC-371 D4); reversible retype, no migration this stage.",
            "candidate_notes": c["notes"],
            "ratified_at": "MAC-376 (operator_review/MAC-376/ratification_proof.md)",
            "export_membership": "reaches Lynceus standard feed on regen "
            "(oui exported / primary_registry / cctv_camera / 85 / global all pass gates)",
        }
        cur.execute(
            "INSERT INTO identifiers "
            "(identifier, identifier_type, device_category, manufacturer, model, confidence, "
            " source_url, source_type, source_excerpt, geographic_scope, first_seen, "
            " last_verified, notes) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                canon,
                "oui",
                "cctv_camera",
                c["manufacturer"],
                None,
                85,
                c["source_url"],
                "primary_registry",
                source_excerpt,
                "global",
                INGEST_DATE,
                INGEST_DATE,
                json.dumps(notes),
            ),
        )
        nid = cur.lastrowid
        new_ids.append(nid)
        print(f"  oui INSERT id={nid} {canon}  ({c['manufacturer']})")

    # ---- AFTER snapshot ----------------------------------------------------------
    after = {
        "ident_total": count("SELECT COUNT(*) FROM identifiers"),
        "ident_active": count("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"),
        "oui": count("SELECT COUNT(*) FROM identifiers WHERE identifier_type='oui'"),
        "mfrs": count("SELECT COUNT(*) FROM manufacturers"),
        "sources": count("SELECT COUNT(*) FROM sources"),
        "schema_max": count("SELECT MAX(version) FROM schema_version"),
        "user_version": count("PRAGMA user_version"),
    }

    # json_valid sweep over the rows just written
    jv_new = 0
    if new_ids:
        qm = ",".join("?" * len(new_ids))
        jv_new = count(
            f"SELECT COUNT(*) FROM identifiers WHERE id IN ({qm}) AND json_valid(notes)=1",
            new_ids,
        )

    # set-equality: the 26 planned canonical OUIs must all be present as MAC-378 rows.
    # CASE-guard the json_extract — 92 legacy oui rows carry NULL/non-JSON notes and
    # an unguarded json_extract over the whole type raises "malformed JSON". CASE is
    # guaranteed to short-circuit in SQLite, so json_extract only runs on valid JSON.
    planned_set = {canon for canon, _ in plan}
    written_rows = cur.execute(
        "SELECT identifier FROM identifiers WHERE identifier_type='oui' AND "
        "CASE WHEN json_valid(notes)=1 THEN json_extract(notes,'$.issue') ELSE NULL END "
        "= 'MAC-378'"
    ).fetchall()
    written_set = {r[0] for r in written_rows}

    # ---- reconstruction diff vs .bak ---------------------------------------------
    # Compare every column over the full id set, in Python. Read the .bak via a
    # SEPARATE read-only connection (NOT ATTACH inside this open write transaction —
    # ATTACH holds a cross-db lock that can't be released until commit). The main
    # side is read from the in-transaction cursor so it reflects the pending inserts.
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
    new_vs_bak = len(new_ids_diff)
    deleted_vs_bak = len(deleted_ids_diff)
    # identifier_type is index 1 of the value tuple (cols after id)
    new_vs_bak_oui = sum(1 for i in new_ids_diff if main_fp[i][1] == "oui")

    # ---- invariants --------------------------------------------------------------
    problems = []
    if after["schema_max"] != 31 or after["user_version"] != before["user_version"]:
        problems.append(f"schema drift: {before['schema_max']}/{before['user_version']} -> "
                        f"{after['schema_max']}/{after['user_version']}")
    if after["ident_total"] != before["ident_total"] + len(new_ids):
        problems.append(f"ident_total delta != +{len(new_ids)}")
    if after["oui"] != before["oui"] + len(new_ids):
        problems.append(f"oui delta != +{len(new_ids)}")
    if after["ident_active"] != before["ident_active"] + len(new_ids):
        problems.append(f"ident_active delta != +{len(new_ids)} (new rows must be active)")
    if after["mfrs"] != before["mfrs"]:
        problems.append("manufacturers count changed (none expected)")
    if after["sources"] != before["sources"]:
        problems.append("sources count changed (none expected)")
    if new_ids and jv_new != len(new_ids):
        problems.append(f"json_valid notes regressed: {jv_new}/{len(new_ids)}")
    if written_set != planned_set:
        problems.append(f"set-equality fail: written {len(written_set)} != planned {len(planned_set)}; "
                        f"missing={planned_set - written_set} extra={written_set - planned_set}")
    if new_vs_bak != len(new_ids) or new_vs_bak_oui != len(new_ids):
        problems.append(f"recon new-row count: total={new_vs_bak} oui={new_vs_bak_oui} != {len(new_ids)}")
    if deleted_vs_bak != 0 or deleted_ids_diff:
        problems.append(f"recon deleted rows != 0: {deleted_vs_bak} ids={deleted_ids_diff}")
    if changed != 0:
        problems.append(f"recon changed common rows != 0: {changed}")
    if sorted(new_ids) != new_ids_diff:
        problems.append(f"recon new ids mismatch: insert={sorted(new_ids)} diff={new_ids_diff}")

    print("\n=== RECON ===")
    print(f"  ident_total  {before['ident_total']} -> {after['ident_total']}  (+{after['ident_total']-before['ident_total']})")
    print(f"  ident_active {before['ident_active']} -> {after['ident_active']}  (+{after['ident_active']-before['ident_active']})")
    print(f"  oui          {before['oui']} -> {after['oui']}  (+{after['oui']-before['oui']})")
    print(f"  mfrs         {before['mfrs']} -> {after['mfrs']}  (+0)")
    print(f"  sources      {before['sources']} -> {after['sources']}  (+0)")
    print(f"  inserted ids = {new_ids}")
    print(f"  skipped (idempotent) = {skipped}")
    print(f"  json_valid notes = {jv_new}/{len(new_ids)}")
    print(f"  set-equality written==planned : {written_set == planned_set} ({len(written_set)} rows)")
    print(f"  recon vs .bak: new={new_vs_bak} (oui={new_vs_bak_oui}) deleted={deleted_vs_bak} changed_common={changed}")
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
    print(f"\nCOMMITTED. post-sha {post_sha}")
    print(f"backup={bak.name} pre-sha={pre_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
