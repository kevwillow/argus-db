"""MAC-191 §5.5 — Document 27 FCC absences.

For each of the 27 FCC absence canonicals, append entry to
`manufacturers.notes.fcc_grantee_absence[]` per dispatch §5.5 mechanic.

Entry shape per dispatch:
  {absence_basis: 'subsidiary_filing_name_pattern',
   notes: 'see v1.5.0 follow-up',
   plan_audit_match_count: <from plan>}

Plus integration provenance:
  integration_dispatch: 'MAC-191', cp_anchor: 'phase_5_§5.5_fcc_grantee_absence',
  integration_at_utc: <NOW>.

Discipline:
- 12 of 27 targets have text-shape notes — apply text-wrap migration (matches §5.3 mechanic).
- 5 of 27 targets (Vigilant, Magnet Forensics, Clearview AI, Digital Ally, Aerodome) also
  received §5.3 neither-axis resolutions; that mutation already wrapped their notes.
  §5.5 mutation is additive on top of §5.3.
- Idempotent: if absence_basis+manufacturer_id already in fcc_grantee_absence[], skip.
- Some manufacturers already have prior `documented_absence` entries (e.g., Genetec id=4
  from earlier waves). §5.5 entry stored separately under `fcc_grantee_absence` per
  dispatch's explicit key naming.
"""
from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

DB = Path("/home/kev/argus/db/argus.db")
PLAN = Path(
    "/home/kev/argus-internal/wave_i_pre_v1/wave_i_12_reconciliation_v2/RECONCILIATION_PLAN_V2_FOR_PAPERCLIP_V1_4_1.json"
)
LOG = Path("/home/kev/argus/_phase_5_wave_i_12/fcc_absences_log.md")
NOW = datetime.datetime.now(datetime.UTC).isoformat()


def parse_or_wrap_notes(raw: str | None) -> tuple[dict, bool]:
    if not raw:
        return {}, False
    try:
        return json.loads(raw), False
    except Exception:
        return {"description": raw}, True


def main() -> int:
    plan = json.loads(PLAN.read_text())
    absences = plan["fcc_grantees_documented_absences"]

    con = sqlite3.connect(DB)
    cur = con.cursor()

    log: list[str] = []
    log.append("# §5.5 FCC absences log — MAC-191 Phase 5")
    log.append(f"Captured: {NOW}")
    log.append(f"Plan entries: {len(absences)}")
    log.append("")
    log.append("## Stage 2 carry-forward: subsidiary-filing-name pattern hypothesis")
    log.append("Per dispatch §5.5: the subsidiary-filing-name pattern hypothesis is recorded as the")
    log.append("absence_basis for v1.5.0 deep-mine investigation. None of these 27 canonicals have FCC")
    log.append("EAS grantees under any current canonical_name/alias substring; possible explanations:")
    log.append("(1) subsidiary brand for FCC filings, (2) equipment falls under exemption category,")
    log.append("(3) vendor sources hardware from FCC-filing third party (no own filing).")
    log.append("")
    log.append("## §11 #11 text-wrap migration discipline")
    log.append("Same as §5.3: text-shape notes wrapped into {description: <prior-text>} atomically.")
    log.append("")

    applied = 0
    wrapped = 0
    skipped_idempotent = 0
    halted = 0

    for a in absences:
        mid = a["manufacturer_id"]
        canon = a["canonical_name"]

        cur.execute("BEGIN")
        try:
            row = cur.execute(
                "SELECT id, canonical_name, notes FROM manufacturers WHERE id = ?",
                (mid,),
            ).fetchone()
            if row is None:
                log.append(f"## HALT id={mid} \"{canon}\" — not in canonical lexicon")
                halted += 1
                con.rollback()
                continue
            if row[1] != canon:
                log.append(
                    f"## HALT id={mid} canonical mismatch: db='{row[1]}' plan='{canon}'"
                )
                halted += 1
                con.rollback()
                continue

            notes_dict, did_wrap = parse_or_wrap_notes(row[2])
            log.append(f"## id={mid} \"{canon}\" (cat={a.get('primary_category')})")
            log.append(f"  plan audit_match_count: {a['audit_match_count_for_review']}")
            if did_wrap:
                log.append(f"  TEXT-WRAP MIGRATION: prior text-notes wrapped into description field")
                wrapped += 1

            entry = {
                "absence_basis": "subsidiary_filing_name_pattern",
                "notes": "see v1.5.0 follow-up",
                "plan_audit_match_count": a["audit_match_count_for_review"],
                "plan_interpretation_brief": a["interpretation"][:200] if a.get("interpretation") else None,
                "integration_dispatch": "MAC-191",
                "cp_anchor": "phase_5_§5.5_fcc_grantee_absence",
                "integration_at_utc": NOW,
            }
            existing = notes_dict.get("fcc_grantee_absence", [])
            # Idempotent: skip if same absence_basis already present under MAC-191
            if any(
                e.get("absence_basis") == entry["absence_basis"]
                and e.get("integration_dispatch") == "MAC-191"
                for e in existing
            ):
                log.append(f"  SKIP-IDEMPOTENT: MAC-191 entry already present")
                skipped_idempotent += 1
                con.rollback()
                continue
            existing.append(entry)
            notes_dict["fcc_grantee_absence"] = existing
            new_notes = json.dumps(notes_dict)
            cur.execute(
                "UPDATE manufacturers SET notes = ? WHERE id = ?",
                (new_notes, mid),
            )
            assert cur.rowcount == 1
            applied += 1
            log.append(f"  APPLY: appended fcc_grantee_absence entry")
            log.append(f"  post: fcc_grantee_absence[] count = {len(existing)}")
            con.commit()
        except Exception as ex:
            con.rollback()
            log.append(f"  ROLLBACK on id={mid}: {ex!r}")
            raise

    # Post readback (sample of 10 spread across the 27)
    log.append("")
    log.append("## Post-state readback (sample)")
    for sample_id in [1, 4, 9, 24, 27, 28, 32, 205, 219, 221]:
        row = cur.execute(
            "SELECT id, canonical_name, json_extract(notes, '$.fcc_grantee_absence') FROM manufacturers WHERE id = ?",
            (sample_id,),
        ).fetchone()
        if row:
            ext = row[2] or "null"
            if len(ext) > 220:
                ext = ext[:220] + "..."
            log.append(f"  id={sample_id} \"{row[1]}\": fcc_grantee_absence = {ext}")

    log.append("")
    log.append("## Totals")
    log.append(f"  applied = {applied}")
    log.append(f"  text-wrap migrations = {wrapped}")
    log.append(f"  skipped-idempotent = {skipped_idempotent}")
    log.append(f"  halted = {halted}")

    LOG.write_text("\n".join(log))
    print(
        f"§5.5 applied={applied} wrapped={wrapped} skipped={skipped_idempotent} halted={halted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
