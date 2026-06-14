#!/usr/bin/env python3
"""MAC-380 — Qualcomm chipset_codename re-attribution apply (CTO-ratified, amended Part B).

Executes CP39 carry-forward (a): 39 ``chipset_codename`` rows (ids 23000-23038)
currently attributed to "Flock Safety" are silicon parts whose manufacturer is the
silicon vendor (Qualcomm), not the ALPR integrator.

CTO ratification: operator_review/MAC-380/cto_ratification.md
Validator triage:  operator_review/MAC-380/triage_report.md
Parent / CEO ruling: MAC-370 (comment 8889164d) — "no blind re-attribution".

Two parts:
  Part A — INSERT one ``manufacturers`` row ``canonical_name='Qualcomm'`` mirroring the
           sibling silicon-vendor convention (ids 313/318/322/323), category
           ``component_vendor``. Idempotent: skip if Qualcomm already present.
  Part B — UPDATE the 39 rows manufacturer 'Flock Safety' -> 'Qualcomm' AND reconstruct
           ``notes`` to valid JSON (json_valid=1) by PROPERTY-MERGE (NOT text-suffix,
           per the CTO amendment + CP40/MAC-309 precedent): fold the two ` | ` text-suffix
           markers into ``$.cp39_audit`` (content preserved verbatim in
           ``cp39_audit.source_markers``) and add the Axis-2 guard ``$.mac380_reattribution``.

HELD UNCHANGED (board-class — CP39 §7.5 prong-2 + CP40 backsweep bar):
  confidence=85, severity='high', source_type, source_url, source_excerpt,
  device_category='unknown'.

SAFETY:
  * DEFAULT = dry-run (read-only via file:...?mode=ro). NO mutation without --apply.
  * --apply: backup-first (.bak with pre-sha in the name), records pre/post sha256,
             re-queries live scope before writing, idempotency-guarded, post-write battery.
  * Schema stays 31. NO push. NO export regen (chipset_codename is export-DROPPED).

Run:
  python3 scripts/mac380_qualcomm_reattribution_apply.py            # dry-run (default)
  python3 scripts/mac380_qualcomm_reattribution_apply.py --apply    # land it (when unblocked)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("db/argus.db")
SCOPE_MIN, SCOPE_MAX, SCOPE_N = 23000, 23038, 39
OLD_MFR, NEW_MFR = "Flock Safety", "Qualcomm"
GAINSEC_URL = (
    "https://github.com/GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose/"
    "blob/1ee8e320de441e80e05c48c1410250761429d9c1/README.md#soc_chipset_support_list"
)

# Part A — Qualcomm manufacturers row (CTO ratification §4; mirrors ids 313/318/322/323).
QUALCOMM_MFR = {
    "canonical_name": "Qualcomm",
    "aliases": "Qualcomm Technologies Inc,Qualcomm Snapdragon",
    "primary_category": "component_vendor",
    "source_url": GAINSEC_URL,
    "notes": json.dumps(
        {
            "vendor_class": "silicon_supplier",
            "component_vendor": True,
            "not_end_product_oem": True,
            "admission": "MAC-380 / CP39 carry-forward (a)",
            "chipset_families": [
                "APQ — Application Processor",
                "MDM — Mobile Data Modem",
                "MSM — Mobile Station Modem (Snapdragon family)",
            ],
            "reattribution_source": "sid=42 GainSec EDL-firehose soc_chipset_support_list",
        },
        ensure_ascii=False,
    ),
    "is_arm": 0,
    "query_default": "visible",
    "parent_manufacturer_id": None,
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def reconstruct_notes(notes: str) -> str:
    """Property-merge the JSON prefix + the 2 text-suffix markers into valid JSON.

    Pure function over a single row's notes string. Deterministic. Byte-faithful: the
    two original marker strings are preserved verbatim in cp39_audit.source_markers, and
    the structured cp39_audit mirrors MAC-309's shape (CTO ratification §3).
    Idempotent: if already carrying mac380_reattribution, returns notes unchanged.
    """
    parts = notes.split(" | ")
    prefix = parts[0]
    obj = json.loads(prefix)  # raises if prefix is not valid JSON — caller treats as fallback
    if "mac380_reattribution" in obj:
        return notes  # idempotency guard

    markers = parts[1:]  # the two ` | ` text-suffix markers (verbatim)

    # Structured cp39_audit (content preserved verbatim in source_markers).
    obj["cp39_audit"] = {
        "null_mfr_attribution": "Flock Safety",
        "underlying_chipset_vendor": "Qualcomm",
        "chipset_family": "Snapdragon (APQ/MDM/MSM)",
        "attribution_basis": "board_narrow_plan_else_branch",
        "confidence_lift": {"from": 65, "to": 85, "basis": "flock_hunt_carveout"},
        "extraction_runs_id": 126,
        "source_markers": markers,  # byte-faithful preservation of the original 2 markers
    }
    obj["mac380_reattribution"] = {
        "change": "manufacturer Flock Safety->Qualcomm",
        "basis": (
            "silicon vendor per APQ/MDM/MSM part-number decoding; "
            "executes CP39 carry-forward (a)"
        ),
        "caveat": (
            "source sid=42 GainSec EDL-firehose soc_chipset_support_list is a "
            "TOOL-supported Qualcomm SoC list, NOT a per-unit Flock bill-of-materials; "
            "Flock<->specific-SoC binding UNPROVEN "
            "(cf. mapper_generic_chipset_no_product_binding=true)"
        ),
        "flock_association": (
            "retained as provenance context (preserves CP39 §7.5 prong-2 "
            "attributability), NOT a manufacturer claim"
        ),
        "ratified_by": "CTO MAC-380",
        "validator_triage": "MAC-380",
    }
    return json.dumps(obj, ensure_ascii=False)


def _connect(read_only: bool) -> sqlite3.Connection:
    if read_only:
        return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    return sqlite3.connect(str(DB_PATH))


def _assert_scope(cur: sqlite3.Cursor) -> list[tuple[int, str]]:
    """Re-query live scope; abort if it drifted from the ratified change-set."""
    cur.execute(
        "SELECT COUNT(*), MIN(id), MAX(id), COUNT(DISTINCT id) FROM identifiers "
        "WHERE identifier_type='chipset_codename' AND manufacturer=?",
        (OLD_MFR,),
    )
    cnt, lo, hi, dist = cur.fetchone()
    if not (cnt == SCOPE_N and lo == SCOPE_MIN and hi == SCOPE_MAX and dist == SCOPE_N):
        raise SystemExit(
            f"SCOPE DRIFT: got cnt={cnt} min={lo} max={hi} distinct={dist}; "
            f"expected {SCOPE_N}/{SCOPE_MIN}/{SCOPE_MAX}/{SCOPE_N}. ABORT (re-triage)."
        )
    cur.execute(
        "SELECT id, notes FROM identifiers WHERE id BETWEEN ? AND ? "
        "AND identifier_type='chipset_codename' AND manufacturer=? ORDER BY id",
        (SCOPE_MIN, SCOPE_MAX, OLD_MFR),
    )
    return cur.fetchall()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="land the write (default: dry-run)")
    args = ap.parse_args()

    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    con = _connect(read_only=not args.apply)
    cur = con.cursor()
    rows = _assert_scope(cur)

    # Validate the reconstruction over all 39 (pure, no DB write).
    reb: dict[int, str] = {}
    fallback: list[int] = []
    for rid, notes in rows:
        try:
            new_notes = reconstruct_notes(notes)
            json.loads(new_notes)  # must be valid JSON
            reb[rid] = new_notes
        except Exception as exc:  # noqa: BLE001 — degraded fallback per CTO §3
            fallback.append(rid)
            print(f"  [fallback] id={rid}: {exc} -> manufacturer-only for this row")

    valid = sum(1 for n in reb.values() if _is_json(n))
    print(f"scope: {len(rows)} rows {SCOPE_MIN}-{SCOPE_MAX}")
    print(f"reconstruction: {len(reb)} rebuilt, json_valid={valid}/{len(reb)}, "
          f"fallback={len(fallback)}")

    cur.execute("SELECT COUNT(*) FROM manufacturers WHERE canonical_name=?", (NEW_MFR,))
    qc_exists = cur.fetchone()[0]
    print(f"Part A: Qualcomm manufacturers row exists={qc_exists} "
          f"({'skip' if qc_exists else 'will INSERT'})")

    # Show one reconstructed sample for eyeballing.
    if reb:
        sample_id = min(reb)
        print(f"\n--- sample reconstructed notes (id={sample_id}) ---")
        print(json.dumps(json.loads(reb[sample_id]), indent=2, ensure_ascii=False))

    if not args.apply:
        print("\nDRY-RUN — no mutation. Re-run with --apply to land (when MAC-377/378 settle).")
        con.close()
        return 0

    # ---- APPLY PATH (backup-first) ----
    pre_sha = _sha256(DB_PATH)
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = DB_PATH.with_name(f"{DB_PATH.name}.mac380_pre_apply_{ts}_{pre_sha[:12]}.bak")
    shutil.copy2(DB_PATH, bak)
    print(f"\nbackup: {bak}  pre_sha={pre_sha[:16]}")

    # Part A
    if not qc_exists:
        cur.execute(
            "INSERT INTO manufacturers "
            "(canonical_name, aliases, primary_category, source_url, notes, "
            " parent_manufacturer_id, is_arm, query_default) "
            "VALUES (:canonical_name, :aliases, :primary_category, :source_url, :notes, "
            " :parent_manufacturer_id, :is_arm, :query_default)",
            QUALCOMM_MFR,
        )
    # Part B
    changed = 0
    for rid, new_notes in reb.items():
        cur.execute(
            "UPDATE identifiers SET manufacturer=?, notes=? WHERE id=?",
            (NEW_MFR, new_notes, rid),
        )
        changed += cur.rowcount
    for rid in fallback:
        cur.execute("UPDATE identifiers SET manufacturer=? WHERE id=?", (NEW_MFR, rid))
        changed += cur.rowcount
    con.commit()

    # Post-write battery
    post_valid = cur.execute(
        "SELECT SUM(json_valid(notes)) FROM identifiers WHERE id BETWEEN ? AND ?",
        (SCOPE_MIN, SCOPE_MAX),
    ).fetchone()[0]
    dup = cur.execute(
        "SELECT COUNT(*) FROM (SELECT identifier, identifier_type, manufacturer, COUNT(*) c "
        "FROM identifiers GROUP BY identifier, identifier_type, manufacturer HAVING c>1)"
    ).fetchone()[0]
    con.close()
    post_sha = _sha256(DB_PATH)
    print(f"applied: {changed} identifiers changed, json_valid(notes) over 39 = {post_valid} "
          f"(fallback rows excluded from json target: {len(fallback)})")
    print(f"lookup-tuple duplicate groups (global): {dup}")
    print(f"post_sha={post_sha[:16]}")
    return 0


def _is_json(s: str) -> bool:
    try:
        json.loads(s)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    sys.exit(main())
