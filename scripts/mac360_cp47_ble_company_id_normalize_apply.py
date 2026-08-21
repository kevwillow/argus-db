#!/usr/bin/env python3
"""
MAC-360 / CP47 — normalize `ble_company_id` id=23052 value '67' -> '0x0043'
(§4.3 canonical-form data correction; schema_version stays 32).

WHY
---
MAC-360 implements the §4.4 CP21 alias-collapse `ble_company_id ->
ble_manufacturer_id` in the export writer (symmetric to the ratified MAC-359
`ble_service_uuid -> ble_uuid`). FP-triage of the 715-row active
`ble_company_id` bulk found a single FEED-AFFECTING malformed value:

  id=23052  identifier='67'  manufacturer='Parrot'  device_category='drone'
            source_type='manufacturer_app'  confidence=85

'67' is the DECIMAL literal lifted verbatim from the Parrot FreeFlight 6 APK
(`ScanFilter.Builder().setManufacturerData(67, ...)` in
ArsdkBleDiscovery.java:204). The row's own source_excerpt documents the
canonical value: "BT SIG company ID 67 (0x0043) = Parrot SA". The Bluetooth-SIG
2-byte company ID is canonically `0x0043`. Shipped under the CP21 MAP, Lynceus
parses a 2-byte hex SIG company ID; the wire value is `0x0043`, NOT the decimal
string "67" -> a guaranteed non-match. This corrects the representation only;
the signature is real.

id4884 IS DELIBERATELY NOT TOUCHED
----------------------------------
id4884 (`ble_manufacturer_id`, '0x0043', Parrot, device_category='unknown',
primary_registry) is the SIG-registry company-level assignment. It is a
DIFFERENT `identifier_type` from id23052 (`ble_company_id`), so per §8.3 /
db/dedup.py::is_duplicate (which keys on identical `identifier` AND
`identifier_type`) the two rows are NOT duplicates and MUST NOT be merged.
They alias only in the EXPORT (both map to pattern_type `ble_manufacturer_id`).
No feed duplicate results: id4884 is `device_category='unknown'` -> §11 #13
unknown-category export ban (export_lynceus.py:616) -> it never emits a Talos
entry. So after this normalize + the CP21 MAP un-hold, the feed carries exactly
ONE `ble_manufacturer_id`/`0x0043` entry (from id23052/drone). id4884 stays
active in the canonical DB, analytical-only, unchanged.

The other 6 non-canonical `ble_company_id` values (id 22841 '0x4C', 22842
'0x004C', 22866 '0x010C', 22868 '0x022B', 22869 '0x022A', 22870 '0x02FF') are
ALL `device_category='unknown'` -> §11 #13 export-banned -> export-invisible ->
ZERO feed impact. They are DEFERRED to a separate §4.3 canonical-form hygiene
sweep (MAC-358 precedent) to keep this external-contract (Lynceus) release
minimal. Note: normalizing id22841 '0x4C' would collide with id22842 (both ->
'0x004c', same identifier_type) and force a §8.3 intra-type supersession; that
is hygiene, not feed-correctness, and is intentionally out of scope here.

SAFETY
------
backup-first (sha256 recorded), strict precondition assert on exact current
row state, idempotent (re-run after apply = clean no-op), single transaction,
in-transaction self-checks (exactly 1 row changed, no field drift except the
identifier value + JSON-property-merged notes, no new active dup, id4884
untouched, active counts unchanged, schema_version unchanged), ROLLBACK on any
failed check. value/type/category/source/confidence/timestamps are UNCHANGED
except `identifier` (the normalize) and `notes` (JSON property-merge only — the
CP39/CP40 lesson: never text-suffix concat).

Usage:
  python3 scripts/mac360_cp47_ble_company_id_normalize_apply.py [DB_PATH] [--check]

  DB_PATH defaults to db/argus.db. For VERIFICATION, pass a throwaway copy so
  the canonical DB is never mutated. --check runs a read-only precondition /
  idempotency report and writes NO changes.

DB mutation of the canonical db/argus.db requires explicit CEO authorization
(one-way-door export-contract change; hold-and-stack with the CP21 MAP un-hold
at the next board-authorized Lynceus release). Do NOT run against canonical
without that authorization.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

CANONICAL_DB = "db/argus.db"

ROW_ID = 23052
IDENT_TYPE = "ble_company_id"
PRE_IDENTIFIER = "67"
NEW_IDENTIFIER = "0x0043"
EXPECT_MFR = "Parrot"
EXPECT_CAT = "drone"
EXPECT_CONF = 85

# Fields that MUST be byte-identical before/after (only `identifier` + `notes` change).
INVARIANT_FIELDS = (
    "identifier_type",
    "device_category",
    "manufacturer",
    "model",
    "confidence",
    "source_type",
    "source_url",
    "source_excerpt",
    "geographic_scope",
    "first_seen",
    "last_verified",
    "superseded_by",
)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _row(con: sqlite3.Connection, row_id: int) -> dict | None:
    con.row_factory = sqlite3.Row
    r = con.execute("SELECT * FROM identifiers WHERE id=?", (row_id,)).fetchone()
    return dict(r) if r else None


def _active_counts(con: sqlite3.Connection) -> dict:
    return {
        "total_active": con.execute(
            "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
        ).fetchone()[0],
        "active_ble_company_id": con.execute(
            "SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_company_id' "
            "AND superseded_by IS NULL"
        ).fetchone()[0],
        "active_bcid_0x0043": con.execute(
            "SELECT COUNT(*) FROM identifiers WHERE identifier_type='ble_company_id' "
            "AND identifier='0x0043' AND superseded_by IS NULL"
        ).fetchone()[0],
    }


def _schema_version(con: sqlite3.Connection) -> int:
    return int(con.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])


def _merge_notes(raw: str | None, applied_utc: str) -> str:
    obj = json.loads(raw) if raw else {}
    obj["mac360_cp47"] = {
        "action": "ble_company_id canonical-form normalize",
        "old_value": PRE_IDENTIFIER,
        "new_value": NEW_IDENTIFIER,
        "rationale": (
            "decimal SIG company-id literal '67' from Parrot FreeFlight 6 APK "
            "normalized to canonical 2-byte hex 0x0043 (= Parrot SA) for the "
            "CP21 §4.4 ble_company_id->ble_manufacturer_id Lynceus MAP; wire "
            "value is 0x0043 not the decimal string '67'"
        ),
        "source_evidence": "ArsdkBleDiscovery.java:204 setManufacturerData(67,...) — BT SIG company ID 67 (0x0043) = Parrot SA",
        "id4884_disposition": (
            "KEPT AS-IS — distinct ble_manufacturer_id SIG-registry row; not a "
            "§8.3 duplicate (different identifier_type); unknown-banned so no feed dup"
        ),
        "schema_version_unchanged": True,
        "applied_utc": applied_utc,
    }
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def run_check(db_path: str) -> int:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    row = _row(con, ROW_ID)
    print(f"[check] db={db_path} sha256={sha256(db_path)}")
    if row is None:
        print(f"[check] FAIL — id={ROW_ID} not found")
        return 2
    print(f"[check] id={ROW_ID} identifier={row['identifier']!r} "
          f"type={row['identifier_type']!r} mfr={row['manufacturer']!r} "
          f"cat={row['device_category']!r} conf={row['confidence']} "
          f"superseded_by={row['superseded_by']}")
    if row["identifier"] == NEW_IDENTIFIER and row["identifier_type"] == IDENT_TYPE:
        print("[check] ALREADY APPLIED (idempotent no-op on apply)")
        return 0
    ok = (
        row["identifier"] == PRE_IDENTIFIER
        and row["identifier_type"] == IDENT_TYPE
        and row["manufacturer"] == EXPECT_MFR
        and row["device_category"] == EXPECT_CAT
        and row["confidence"] == EXPECT_CONF
        and row["superseded_by"] is None
    )
    print(f"[check] precondition for apply: {'MET' if ok else 'NOT MET'}")
    counts = _active_counts(con)
    print(f"[check] active counts: {counts}")
    id4884 = _row(con, 4884)
    print(f"[check] id4884: identifier={id4884['identifier']!r} "
          f"type={id4884['identifier_type']!r} cat={id4884['device_category']!r} "
          f"superseded_by={id4884['superseded_by']}")
    return 0 if ok else 2


def run_apply(db_path: str) -> int:
    applied_utc = datetime.now(timezone.utc).isoformat()
    is_canonical = db_path == CANONICAL_DB

    # Idempotency / precondition (read-only first).
    ro = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    before = _row(ro, ROW_ID)
    if before is None:
        print(f"[abort] id={ROW_ID} not found in {db_path}")
        return 2
    if before["identifier"] == NEW_IDENTIFIER and before["identifier_type"] == IDENT_TYPE:
        print(f"[idempotent] id={ROW_ID} already '{NEW_IDENTIFIER}' — no-op, no write")
        return 0
    pre = {f: before[f] for f in INVARIANT_FIELDS}
    if not (
        before["identifier"] == PRE_IDENTIFIER
        and before["identifier_type"] == IDENT_TYPE
        and before["manufacturer"] == EXPECT_MFR
        and before["device_category"] == EXPECT_CAT
        and before["confidence"] == EXPECT_CONF
        and before["superseded_by"] is None
    ):
        print(f"[abort] precondition mismatch for id={ROW_ID}: {dict(before)}")
        return 2
    counts_before = _active_counts(ro)
    sv_before = _schema_version(ro)
    id4884_before = _row(ro, 4884)
    ro.close()

    if counts_before["active_bcid_0x0043"] != 0:
        print("[abort] an active ble_company_id row already holds 0x0043 — "
              "normalize would create a §8.3 intra-type duplicate")
        return 2

    pre_sha = sha256(db_path)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = f"{db_path}.mac360_cp47_pre_apply_{ts}.bak"
    shutil.copy2(db_path, bak)
    print(f"[backup] pre-sha256={pre_sha}")
    print(f"[backup] {db_path} -> {bak}")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        con.execute("BEGIN")
        new_notes = _merge_notes(before["notes"], applied_utc)
        cur = con.execute(
            "UPDATE identifiers SET identifier=?, notes=? WHERE id=? "
            "AND identifier=? AND identifier_type=?",
            (NEW_IDENTIFIER, new_notes, ROW_ID, PRE_IDENTIFIER, IDENT_TYPE),
        )
        if cur.rowcount != 1:
            raise RuntimeError(f"expected 1 row updated, got {cur.rowcount}")

        after = dict(con.execute("SELECT * FROM identifiers WHERE id=?", (ROW_ID,)).fetchone())
        # value changed
        if after["identifier"] != NEW_IDENTIFIER:
            raise RuntimeError("post-update identifier mismatch")
        # invariants held
        for f in INVARIANT_FIELDS:
            if after[f] != pre[f]:
                raise RuntimeError(f"invariant field drifted: {f} {pre[f]!r} -> {after[f]!r}")
        # notes still valid JSON, superset of pre keys
        pre_keys = set(json.loads(before["notes"]).keys()) if before["notes"] else set()
        post_obj = json.loads(after["notes"])
        if not pre_keys.issubset(post_obj.keys()):
            raise RuntimeError("notes property-merge dropped pre-existing keys")
        if "mac360_cp47" not in post_obj:
            raise RuntimeError("notes missing mac360_cp47 audit key")
        # counts unchanged (value normalize, not active-status change)
        counts_after = _active_counts(con)
        if counts_after["total_active"] != counts_before["total_active"]:
            raise RuntimeError("total_active drifted")
        if counts_after["active_ble_company_id"] != counts_before["active_ble_company_id"]:
            raise RuntimeError("active_ble_company_id drifted")
        if counts_after["active_bcid_0x0043"] != 1:
            raise RuntimeError(f"expected exactly 1 active ble_company_id=0x0043, got "
                               f"{counts_after['active_bcid_0x0043']}")
        # id4884 untouched
        id4884_after = dict(con.execute("SELECT * FROM identifiers WHERE id=4884").fetchone())
        if {k: id4884_after[k] for k in INVARIANT_FIELDS + ("identifier",)} != {
            k: id4884_before[k] for k in INVARIANT_FIELDS + ("identifier",)
        }:
            raise RuntimeError("id4884 drifted — must be untouched")
        # schema_version unchanged
        if _schema_version(con) != sv_before:
            raise RuntimeError("schema_version drifted")

        con.commit()
    except Exception as exc:  # noqa: BLE001
        con.rollback()
        con.close()
        print(f"[ROLLBACK] {exc}")
        print(f"[ROLLBACK] DB restored to pre-state; backup retained at {bak}")
        return 3
    con.close()

    post_sha = sha256(db_path)
    proof = {
        "issue": "MAC-360",
        "correction_pass": "CP47",
        "action": "ble_company_id canonical-form normalize (single feed-affecting row)",
        "db_path": db_path,
        "is_canonical_db": is_canonical,
        "applied_utc": applied_utc,
        "schema_version": sv_before,
        "schema_version_unchanged": True,
        "backup": {"path": bak, "pre_sha256": pre_sha},
        "post_sha256": post_sha,
        "row": {
            "id": ROW_ID,
            "before": {"identifier": PRE_IDENTIFIER, "identifier_type": IDENT_TYPE},
            "after": {"identifier": NEW_IDENTIFIER, "identifier_type": IDENT_TYPE},
            "invariant_fields_unchanged": list(INVARIANT_FIELDS),
            "notes_change": "JSON property-merge only (key mac360_cp47 added)",
        },
        "id4884_disposition": "kept as-is (distinct ble_manufacturer_id row; not a §8.3 dup; unknown-banned)",
        "reconcile": {
            "total_active_before": counts_before["total_active"],
            "total_active_after": counts_before["total_active"],
            "active_ble_company_id_before": counts_before["active_ble_company_id"],
            "active_ble_company_id_after": counts_before["active_ble_company_id"],
            "active_ble_company_id_eq_0x0043_after": 1,
        },
    }
    suffix = "" if is_canonical else "_VERIFY"
    proof_path = f"operator_review/mac360/mac360_cp47_normalize_proof{suffix}.json"
    # MAC-763 untracked operator_review/, so a fresh clone has no directory to
    # write into and this open() raised FileNotFoundError AFTER the DB mutation
    # had already committed -- the apply succeeded and lost its proof artifact.
    os.makedirs(os.path.dirname(proof_path), exist_ok=True)
    with open(proof_path, "w", encoding="utf-8") as f:
        json.dump(proof, f, indent=2, ensure_ascii=False)
    print(f"[ok] applied. post-sha256={post_sha}")
    print(f"[ok] proof -> {proof_path}")
    return 0


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--check"]
    check = "--check" in argv[1:]
    db_path = args[0] if args else CANONICAL_DB
    if check:
        return run_check(db_path)
    return run_apply(db_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
