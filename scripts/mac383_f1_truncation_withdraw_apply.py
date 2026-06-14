#!/usr/bin/env python3
"""MAC-383 (MAC-382 Finding 1) — fcc_grantee_code §7.4 truncation withdraw.

DBArchitect write-lane. Backup-first (caller cp'd .bak). Schema 31 unchanged. NO push.

Withdraws two format-invalid 3-char grantee-code truncations as dedup against their
full-length siblings, preserving the fccid.io citation pointers via JSON property-merge
(NEVER text-suffix concat — migration-safety lens, per MAC-380 amended Part B precedent).

  35699  2AG   -> superseded_by 42871 (2AG6I, regulatory/opendata, conf88, drone)
  35704  2AH   -> superseded_by 37142 (2AHAY, primary_registry/opendata, conf85, drone
                                       — re-queried LIVE post-MAC-377 #6 recat)

§8.3: NO mechanical lift. Type fcc_grantee_code is export-DROPPED (export_lynceus.py:216)
so any +5 is registry-internal/moot; we record corroborating citations only and leave
confidence untouched on every row. The 2AHAY issuer-classification flip (37142 is now
opendata, not fccid.io, after MAC-377) is documented for CTO but NOT acted on (no lift).
"""
from __future__ import annotations

import json
import sqlite3
import sys

DB = "db/argus.db"

WITHDRAWN_ID = "MAC-383 (DBArchitect 6c93a466)"

# id -> notes property merge(s). Property-merge only; superseded_by handled separately.
NOTE_MERGES: dict[int, dict] = {
    # Withdrawn rows: record §7.4-truncation reason + supersede pointer.
    35699: {
        "mac382_f1_withdraw": {
            "reason": "§7.4 3-char truncation of 2AG6I; withdrawn-as-dedup MAC-382",
            "superseded_by": 42871,
            "full_grantee": "2AG6I",
            "applied_by": WITHDRAWN_ID,
        }
    },
    35704: {
        "mac382_f1_withdraw": {
            "reason": "§7.4 3-char truncation of 2AHAY; withdrawn-as-dedup MAC-382",
            "superseded_by": 37142,
            "full_grantee": "2AHAY",
            "applied_by": WITHDRAWN_ID,
        }
    },
    # Surviving siblings: fold withdrawn rows' source_url as corroborating citation.
    42871: {
        "mac382_f1_corroborating_citation": {
            "source_url": "https://fccid.io/2AG6I-DISCO",
            "from_withdrawn_id": 35699,
            "note": (
                "fccid.io evidence pointer preserved from withdrawn §7.4-truncation "
                "row 35699 (2AG). Cross-issuer (fccid.io vs opendata.fcc.gov) value-level "
                "§8.3 corroboration of 2AG6I, BUT NO +5 lift applied — type "
                "fcc_grantee_code is export-DROPPED (registry-internal; avoids confidence "
                "inflation on an unshipped row). Cite-record only per CTO triage."
            ),
            "applied_by": WITHDRAWN_ID,
        }
    },
    37142: {
        "mac382_f1_corroborating_citation": {
            "source_url": "https://fccid.io/2AHAY-S5121601",
            "from_withdrawn_id": 35704,
            "note": (
                "fccid.io evidence pointer preserved from withdrawn §7.4-truncation "
                "row 35704 (2AH). DEVIATION-FROM-SNAPSHOT: post-MAC-377 #6 recat, 37142's "
                "primary source_url is now opendata.fcc.gov (was fccid.io/2AHAY), so "
                "35704(fccid.io) vs 37142(opendata) is now CROSS-issuer §8.3 "
                "corroboration — the CTO triage classified it as same-issuer/not-§8.3. "
                "Disposition UNCHANGED: NO +5 lift (export-DROPPED type). Flagged to CTO; "
                "no unilateral lift applied."
            ),
            "applied_by": WITHDRAWN_ID,
        }
    },
}

SUPERSEDE = {35699: 42871, 35704: 37142}


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        cur = conn.cursor()
        # Pre-flight: every target row exists and notes is valid JSON.
        for rid in sorted(NOTE_MERGES):
            row = cur.execute(
                "SELECT notes, json_valid(notes), superseded_by FROM identifiers WHERE id=?",
                (rid,),
            ).fetchone()
            if row is None:
                print(f"ABORT: id {rid} not found", file=sys.stderr)
                return 2
            notes_raw, jv, sb = row
            if jv != 1:
                print(f"ABORT: id {rid} notes not json_valid", file=sys.stderr)
                return 2
            if rid in SUPERSEDE and sb is not None:
                print(f"ABORT: id {rid} already superseded_by {sb}", file=sys.stderr)
                return 2

        cur.execute("BEGIN")
        for rid, merge in NOTE_MERGES.items():
            notes_raw = cur.execute(
                "SELECT notes FROM identifiers WHERE id=?", (rid,)
            ).fetchone()[0]
            obj = json.loads(notes_raw) if notes_raw else {}
            for k, v in merge.items():
                if k in obj:
                    print(f"ABORT: id {rid} already has property {k!r}", file=sys.stderr)
                    conn.rollback()
                    return 3
                obj[k] = v
            new_notes = json.dumps(obj)  # ensure_ascii=True matches existing serialization
            cur.execute(
                "UPDATE identifiers SET notes=? WHERE id=?", (new_notes, rid)
            )
        for wid, full in SUPERSEDE.items():
            cur.execute(
                "UPDATE identifiers SET superseded_by=? WHERE id=?", (full, wid)
            )
        conn.commit()

        # Post-write json_valid sweep.
        bad = cur.execute(
            "SELECT id FROM identifiers WHERE id IN (35699,35704,37142,42871) "
            "AND json_valid(notes)<>1"
        ).fetchall()
        if bad:
            print(f"POST-WRITE json_valid FAIL: {bad}", file=sys.stderr)
            return 4
        print("APPLY OK: 2 superseded_by, 4 notes property-merged, json_valid 4/4")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
