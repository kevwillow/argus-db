"""MAC-191 §5.3 — Apply 5 neither-axis resolutions.

Append per-resolution evidence to manufacturers.notes.neither_axis_resolution[] for:
- Vigilant Solutions (id=2)  via USAspending sub-pass B  — 56 procurement rows, $2.9M + 133 deployments
- Magnet Forensics (id=29)   via USAspending sub-pass B  — 308 procurement rows, $58.3M
- Clearview AI (id=32)       via USAspending sub-pass B  — 20 procurement rows, $8.3M
- Digital Ally (id=218)      via deployment_observations sub-pass E — 11 deployments
- Aerodome (id=219)          via deployment_observations sub-pass E — 1 deployment

Discipline:
- SAR-15 GENERIC_RISK_CANONICALS guard: 4 of 5 targets are GENERIC_RISK_CANONICALS
  (Vigilant Solutions, Magnet Forensics, Clearview AI, Digital Ally). Evidence is
  direct-citation (USAspending vendor_canonical_normalized OR deployment_observations vendor_raw),
  NOT substring-tier matches.
- NO new identifier rows; NO new manufacturer rows.
- Notes text-wrap migration applies for Magnet Forensics + Clearview AI (text-shape notes).
"""
from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

DB = Path("/home/kev/argus/db/argus.db")
LOG = Path("/home/kev/argus/_phase_5_wave_i_12/neither_axis_resolutions_log.md")
NOW = datetime.datetime.now(datetime.UTC).isoformat()

RESOLUTIONS = [
    {
        "manufacturer_id": 2,
        "canonical_name": "Vigilant Solutions",
        "resolved_via": "USAspending sub-pass B",
        "axis": "procurement+deployment",
        "evidence_text": "56 procurement rows, $2.9M + 133 deployments",
        "evidence_fields": {
            "usaspending_procurement_rows": 56,
            "usaspending_total_award_usd_approx": 2_900_000.0,
            "deployment_observations_count": 133,
        },
    },
    {
        "manufacturer_id": 29,
        "canonical_name": "Magnet Forensics",
        "resolved_via": "USAspending sub-pass B",
        "axis": "procurement",
        "evidence_text": "308 procurement rows, $58.3M",
        "evidence_fields": {
            "usaspending_procurement_rows": 308,
            "usaspending_total_award_usd_approx": 58_300_000.0,
        },
    },
    {
        "manufacturer_id": 32,
        "canonical_name": "Clearview AI",
        "resolved_via": "USAspending sub-pass B",
        "axis": "procurement",
        "evidence_text": "20 procurement rows, $8.3M",
        "evidence_fields": {
            "usaspending_procurement_rows": 20,
            "usaspending_total_award_usd_approx": 8_300_000.0,
        },
    },
    {
        "manufacturer_id": 218,
        "canonical_name": "Digital Ally",
        "resolved_via": "deployment_observations sub-pass E",
        "axis": "deployment",
        "evidence_text": "11 deployments",
        "evidence_fields": {"deployment_observations_count": 11},
    },
    {
        "manufacturer_id": 219,
        "canonical_name": "Aerodome",
        "resolved_via": "deployment_observations sub-pass E",
        "axis": "deployment",
        "evidence_text": "1 deployment",
        "evidence_fields": {"deployment_observations_count": 1},
    },
]

GENERIC_RISK_CANONICALS = {
    "Harris", "Dahua", "Axis Communications", "Flock Safety", "Rhombus Systems",
    "Parrot", "Reveal", "Lenel", "Axon", "Vigilant Solutions", "Clearview AI",
    "Magnet Forensics", "Engility", "Digital Ally",
}


def parse_or_wrap_notes(raw: str | None, canonical_name: str) -> tuple[dict, bool]:
    """Return (notes_dict, did_wrap_text).

    If raw is None/empty: return ({}, False).
    If raw is JSON-shape: return (parsed, False).
    If raw is text-shape: wrap into {"description": raw} per established schema
    convention (matches id=2,3,4,5,6 description-field pattern) and return
    (wrapped, True).
    """
    if not raw:
        return {}, False
    try:
        return json.loads(raw), False
    except Exception:
        # Text-shape: wrap into description field
        return {"description": raw}, True


def main() -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()

    log: list[str] = []
    log.append("# §5.3 Neither-axis resolutions log — MAC-191 Phase 5")
    log.append(f"Captured: {NOW}")
    log.append("")
    log.append("## SAR-15 evidence-direction discipline")
    log.append("All 5 resolutions are direct-citation (procurement_records.vendor_canonical_normalized or")
    log.append("deployment_observations.vendor_raw); NOT substring-tier matches.")
    log.append("")
    log.append("## §11 #11 text-wrap migration discipline")
    log.append("manufacturers.notes is mixed-shape across the 51-row table (30 JSON / 21 text-shape).")
    log.append("Dispatch §5.5 SQL template `COALESCE(notes, '{}')` assumes JSON shape; text-shape rows")
    log.append("would fail `json_set`. Conservative discipline: text-shape rows get wrapped into")
    log.append("`{\"description\": <prior-text>}` (matching established schema convention id=2,3,4,5,6 etc.)")
    log.append("atomically as part of the same UPDATE. Text content is preserved verbatim. Wrap-migrations")
    log.append("are flagged in per-row log entries.")
    log.append("")

    applied = 0
    halted = 0
    wrapped = 0

    for r in RESOLUTIONS:
        mid = r["manufacturer_id"]
        canon = r["canonical_name"]

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

            notes_dict, did_wrap = parse_or_wrap_notes(row[2], canon)
            log.append(f"## id={mid} \"{canon}\"")
            log.append(f"  resolved_via: {r['resolved_via']}")
            log.append(f"  axis: {r['axis']}")
            log.append(f"  evidence: {r['evidence_text']}")
            log.append(f"  GENERIC_RISK_CANONICAL: {canon in GENERIC_RISK_CANONICALS}")
            if did_wrap:
                log.append(
                    f"  TEXT-WRAP MIGRATION: prior text-notes wrapped into description field"
                )
                wrapped += 1

            entry = {
                "resolved_via": r["resolved_via"],
                "axis": r["axis"],
                "evidence_text": r["evidence_text"],
                "evidence_fields": r["evidence_fields"],
                "sar_15_evidence_direction": "direct_citation_not_substring",
                "integration_dispatch": "MAC-191",
                "cp_anchor": "phase_5_§5.3_neither_axis_resolution",
                "integration_at_utc": NOW,
            }
            existing = notes_dict.get("neither_axis_resolution", [])
            # Idempotent check
            if any(
                e.get("resolved_via") == entry["resolved_via"]
                and e.get("axis") == entry["axis"]
                and e.get("evidence_text") == entry["evidence_text"]
                for e in existing
            ):
                log.append(f"  SKIP-IDEMPOTENT: identical entry already present")
                con.rollback()
                continue
            existing.append(entry)
            notes_dict["neither_axis_resolution"] = existing
            new_notes = json.dumps(notes_dict)
            cur.execute(
                "UPDATE manufacturers SET notes = ? WHERE id = ?",
                (new_notes, mid),
            )
            assert cur.rowcount == 1
            applied += 1
            log.append(f"  APPLY: appended neither_axis_resolution entry")
            log.append(f"  post: notes.neither_axis_resolution[] count = {len(existing)}")
            con.commit()
        except Exception as ex:
            con.rollback()
            log.append(f"  ROLLBACK on id={mid}: {ex!r}")
            raise

    # Post readback
    log.append("")
    log.append("## Post-state readback")
    for r in RESOLUTIONS:
        mid = r["manufacturer_id"]
        row = cur.execute(
            "SELECT id, canonical_name, json_extract(notes, '$.neither_axis_resolution') FROM manufacturers WHERE id = ?",
            (mid,),
        ).fetchone()
        ext = row[2] or "null"
        if len(ext) > 200:
            ext = ext[:200] + "..."
        log.append(f"  id={mid} \"{row[1]}\": neither_axis_resolution = {ext}")

    log.append("")
    log.append("## Totals")
    log.append(f"  applied = {applied}")
    log.append(f"  text-wrap migrations = {wrapped}")
    log.append(f"  halted = {halted}")

    LOG.write_text("\n".join(log))
    print(
        f"§5.3 applied={applied} wrapped={wrapped} halted={halted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
