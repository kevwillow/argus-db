#!/usr/bin/env python3
"""MAC-274 STAGED reconciliation — 14 pre-existing FlockYou crowdsourced ssid_patterns.

Applies the Step-2.3 ruling (origin MAC-273) UNIFORMLY to the 14 pre-existing rows
(ids 35591-35604, landed MAC-192) that share the identical source class as the 5
Wave-K rows already demoted in Phase H:

    crowdsourced detection-app `ssid_pattern`s are third-party, NOT vendor-published
    defaults  ->  source_type='inferred', confidence=50,
                  notes.fp_class='crowdsourced_detection_app_not_vendor_default'

Verified pre-condition (MAC-274 enumeration): NONE of the 14 carries an independent
vendor-default corroboration row anywhere in `identifiers`; all 14 are purely
crowdsourced-app-derived (single source_url = github.com/MaxwellDPS/Flock-You-Android,
candidate_source='community_subpass_42').

  *** STAGED — does NOT write unless --commit is passed AFTER CEO ratification. ***
  Dry-run (default, PRAGMA query_only=ON): prints exact before/after per row.

  Apply procedure (only after MAC-274 CEO ratification):
    cp db/argus.db db/argus.db.pre_mac274_$(date -u +%Y%m%dT%H%M%SZ)
    python3 db/migrations/_drafts/mac274_flockyou_ssid_reconcile_STAGED.py --commit

Idempotent: rows already at inferred/50 are SKIPPED (guard on conf==85 & st=='crowdsourced').
Provenance (§11 #7): source_url is NEVER touched; existing notes JSON preserved verbatim,
only additive keys (confidence_history[], source_type_history[], fp_class, reconciliation).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone

TARGET_LO, TARGET_HI = 35591, 35604  # inclusive, 14 rows
FP_CLASS = "crowdsourced_detection_app_not_vendor_default"
DISPATCH = "MAC-274"
PARENT = "MAC-273"
CP_ANCHOR = "CP38_step_2_3_crowdsourced_detection_app_uniform_sweep"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="db/argus.db")
    ap.add_argument("--commit", action="store_true",
                    help="apply writes (only AFTER CEO ratification + DB backup)")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    if not args.commit:
        con.execute("PRAGMA query_only = ON;")
    now = datetime.now(timezone.utc).isoformat()

    rows = con.execute(
        "SELECT id, identifier, manufacturer, confidence, source_type, notes "
        "FROM identifiers WHERE id BETWEEN ? AND ? ORDER BY id",
        (TARGET_LO, TARGET_HI),
    ).fetchall()
    assert len(rows) == 14, f"expected 14 target rows, got {len(rows)}"

    staged = 0
    for r in rows:
        if r["confidence"] != 85 or r["source_type"] != "crowdsourced":
            print(f"SKIP  id={r['id']:>5} already reconciled "
                  f"(conf={r['confidence']} source_type={r['source_type']})")
            continue
        notes = json.loads(r["notes"]) if r["notes"] else {}
        notes.setdefault("confidence_history", []).append({
            "at_utc": now, "from": 85, "to": 50,
            "rationale": "step_2_3_crowdsourced_detection_app_not_vendor_default_uniform_sweep",
            "dispatch": DISPATCH, "cp_anchor": CP_ANCHOR,
        })
        notes.setdefault("source_type_history", []).append({
            "at_utc": now, "from": "crowdsourced", "to": "inferred",
            "rationale": "step_2_3_band_reclass_detection_app_inference_not_field_observation",
            "dispatch": DISPATCH, "cp_anchor": CP_ANCHOR,
        })
        notes["fp_class"] = FP_CLASS
        notes["reconciliation"] = {
            "dispatch": DISPATCH, "parent": PARENT, "policy": "step_2_3",
            "at_utc": now,
        }
        new_notes = json.dumps(notes, ensure_ascii=False)
        if args.commit:
            con.execute(
                "UPDATE identifiers SET confidence=50, source_type='inferred', notes=? "
                "WHERE id=?",
                (new_notes, r["id"]),
            )
        staged += 1
        print(f"STAGE id={r['id']:>5} {r['manufacturer']:<16} "
              f"conf 85->50 | source_type crowdsourced->inferred | "
              f"+fp_class +confidence_history +source_type_history")

    if args.commit:
        con.commit()
        print(f"\nCOMMITTED {staged} rows. Run PRAGMA integrity_check + foreign_key_check next.")
    else:
        print(f"\nDRY-RUN: {staged} rows would change. "
              f"Re-run with --commit ONLY after MAC-274 CEO ratification + DB backup.")
    con.close()


if __name__ == "__main__":
    main()
