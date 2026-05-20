"""
Phase 7 §7.3 — fccid.io stub-page documented absence.

1 row from Wave I.14c `EXTRACTION_PLAN_V3.fccid_io_extended_stub_documented_absences[]`:
  fcc_id      = 2AG6IWCH01  (grantee_code_3char=2AG => Parrot Drone SAS)
  url         = https://fccid.io/2AG6IWCH01
  reason      = undersized body
  html_bytes  = 15

Stage into `manufacturers.notes.fcc_grantee_documented_absences[]` for
canonical row Parrot (id=25), mirroring the Phase 5 §5.5 FCC absences
pattern.

Dispatch ref: MAC-194 §7.3.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path("/home/kev/argus/db/argus.db")
PLAN_PATH = Path("/home/kev/argus-internal/wave_i_pre_v1/wave_i_14c_unfreeze/EXTRACTION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json")
LOG_PATH = Path("/home/kev/argus/_phase_7_fccid_attestations/stub_absence_log.md")

CANONICAL_MFR = "Parrot"  # 2AG = Parrot Drone SAS (FCC EAS grantee)


def main() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    absences = plan["fccid_io_extended_stub_documented_absences"]
    assert len(absences) == 1, f"expected 1 stub absence, got {len(absences)}"
    stub = absences[0]

    new_entry = {
        "fcc_id": stub["fcc_id"],
        "url": stub["url"],
        "reason": stub["reason"],
        "html_bytes": stub["html_bytes"],
        "absence_basis": "fccid_io_stub_page",
        "source_dispatch": "MAC-194",
        "wave": "wave_i_14c_unfreeze",
        "captured_at_utc": "2026-05-20T00:00:00Z",
        "deep_mine_status": "v1_5_0_pending",
        "grantee_code_3char_inferred": stub["fcc_id"][:3],
        "grantee_name_inferred": "PARROT DRONE SAS",
    }

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id, canonical_name, notes FROM manufacturers WHERE canonical_name=?", (CANONICAL_MFR,))
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"HALT: manufacturers.canonical_name='{CANONICAL_MFR}' not found")
    mfr_id, mfr_name, mfr_notes_text = row

    notes = json.loads(mfr_notes_text) if mfr_notes_text else {}
    absences_list = notes.get("fcc_grantee_documented_absences", [])

    # Idempotency
    for existing in absences_list:
        if existing.get("fcc_id") == new_entry["fcc_id"] and existing.get("source_dispatch") == "MAC-194":
            msg = f"HALT-IDEMPOTENT: stub absence for {new_entry['fcc_id']} already on Parrot.notes (MAC-194)"
            print(msg)
            LOG_PATH.write_text(msg + "\n", encoding="utf-8")
            return

    absences_list.append(new_entry)
    notes["fcc_grantee_documented_absences"] = absences_list

    try:
        cur.execute("BEGIN")
        cur.execute("UPDATE manufacturers SET notes=? WHERE id=?", (json.dumps(notes), mfr_id))
        cur.execute("COMMIT")
    except sqlite3.Error as exc:
        cur.execute("ROLLBACK")
        raise SystemExit(f"§7.3 transaction failed: {exc}")

    log_lines = [
        "# Phase 7 §7.3 — Wave I.14c stub-page documented absence",
        "",
        "**Dispatch ref:** [MAC-194](/MAC/issues/MAC-194) §7.3",
        f"**Plan source:** `{PLAN_PATH}` → `fccid_io_extended_stub_documented_absences[0]`",
        f"**Manufacturer:** Parrot (id={mfr_id}) — selected via grantee_code_3char `2AG` → PARROT DRONE SAS canonical mapping",
        "**Pattern:** Phase 5 §5.5 FCC absences (json_set on `manufacturers.notes.fcc_grantee_documented_absences[]`)",
        "",
        "## Entry applied",
        "",
        "```json",
        json.dumps(new_entry, indent=2),
        "```",
        "",
        "## §11 discipline",
        "",
        "- §11 #1 (no fabrication) — plan-input data preserved verbatim.",
        "- §11 #7 (provenance) — fcc_id + url + reason chained to plan dispatch ref.",
        "- §11 #8 (no confidence drift) — no identifier promoted; no confidence assigned.",
        "",
    ]
    LOG_PATH.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"§7.3 OK: Parrot.notes.fcc_grantee_documented_absences[] += 1 (fcc_id={new_entry['fcc_id']})")


if __name__ == "__main__":
    main()
