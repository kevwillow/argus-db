"""MAC-192 §6.3 — apply 74 retroactive behavioral_signatures absorptions.

Per dispatch §6.3:
- 9 academic candidates (sid=41 GainSec Raven ESP32 + sid=43 DroneSecurity DJI)
- 65 community candidates (sids 22/23/24/28/30/31/32)
- INSERT into behavioral_signatures with full provenance from plan
- UPDATE raw_observations.notes with absorbed_to: 'behavioral_signatures.id=N'
- Wrap in transaction
- Halt if schema differs from plan-input shape

Schema-binding (verified at preflight):
  behavioral_signatures(id, signature_name, cellular_generation, threshold_json,
                        evidence_json, source_id, source_file_relative,
                        source_line, confidence, device_category, notes,
                        created_at, updated_at)
  UNIQUE(signature_name, source_id, cellular_generation)

Confidence: proposed_confidence_band upper bound (no drift, §11 #8).
device_category: from plan candidate (all in the 12-value enum verified at preflight).
cellular_generation: NULL (no 2G/3G/4G/5G_NSA hints in this batch).
"""

from __future__ import annotations

import datetime
import json
import re
import sqlite3
from pathlib import Path

DB = Path("/home/kev/argus/db/argus.db")
PLAN = Path(
    "/home/kev/argus-internal/wave_i_pre_v1/wave_i_14a_canonical_remine/"
    "RECONCILIATION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json"
)
LOG = Path("/home/kev/argus/_phase_6_wave_i_14a/behavioral_absorption_log.md")

NOW = datetime.datetime.now(datetime.UTC).isoformat()
CP_ANCHOR = "phase_6_wave_i_14a_behavioral_absorption"

# Pattern to extract "path:line" or "path:line-line" from evidence_excerpt
FILE_LINE_RE = re.compile(r"([\w./\-]+\.[a-zA-Z]+):(\d+)(?:-\d+)?")


def extract_file_line(excerpt: str | None) -> tuple[str | None, int | None]:
    if not excerpt:
        return (None, None)
    m = FILE_LINE_RE.search(excerpt)
    if m:
        try:
            return (m.group(1), int(m.group(2)))
        except ValueError:
            return (m.group(1), None)
    return (None, None)


def signature_name_from(candidate: dict) -> str:
    """Resolve signature_name from plan candidate (academic vs. community shape)."""
    return (
        candidate.get("proposed_signature_name")
        or candidate.get("candidate_signature_name")
        or candidate.get("candidate")
        or "<UNNAMED>"
    )


def main() -> int:
    plan = json.loads(PLAN.read_text())
    arc = plan["academic_remine_promotion_candidates"]
    crc = plan["community_repo_remine_promotion_candidates"]
    candidates: list[tuple[dict, str]] = []
    for c in arc["behavioral_signatures_table_candidates"]:
        candidates.append((c, "academic_subpass_41"))
    for c in crc["behavioral_signatures_table_candidates"]:
        candidates.append((c, "community_subpass_42"))

    con = sqlite3.connect(DB)
    cur = con.cursor()

    log: list[str] = []
    log.append("# §6.3 behavioral_signatures absorption log — MAC-192 Phase 6")
    log.append(f"Captured: {NOW}")
    log.append(f"Candidates: {len(candidates)} (expect 74)")
    log.append("")

    counts = {
        "inserted": 0,
        "skip_unique_conflict": 0,
        "skip_missing_raw_obs": 0,
        "skip_invalid_category": 0,
    }
    inserted_ids: list[int] = []

    # Valid device_category 12-value enum (shared with identifiers)
    VALID_CAT = {
        "alpr", "imsi_catcher", "body_cam", "police_radio", "drone",
        "gunshot_detect", "hacking_tool", "covert_cam", "gps_tracker",
        "face_recog", "drone_detect", "unknown",
    }

    cur.execute("BEGIN")
    try:
        for c, origin in candidates:
            raw_id = c["raw_obs_id"]
            sig_name = signature_name_from(c)
            sid = c["source_id"]
            cat = c["device_category"]
            band = c["proposed_confidence_band"]
            conf = band[1]
            excerpt = c.get("evidence_excerpt", "")
            mfr_hint = c.get("proposed_manufacturer_hint") or c.get(
                "manufacturer_hint"
            )

            if cat not in VALID_CAT:
                log.append(
                    f"  SKIP raw_obs={raw_id} sig={sig_name!r}: invalid cat={cat!r}"
                )
                counts["skip_invalid_category"] += 1
                continue

            # raw_obs sanity
            row = cur.execute(
                "SELECT id FROM raw_observations WHERE id = ?", (raw_id,)
            ).fetchone()
            if row is None:
                log.append(f"  SKIP raw_obs={raw_id}: missing")
                counts["skip_missing_raw_obs"] += 1
                continue

            # UNIQUE pre-check (signature_name, source_id, cellular_generation=NULL)
            existing = cur.execute(
                """SELECT id FROM behavioral_signatures
                   WHERE signature_name = ? AND source_id = ?
                     AND cellular_generation IS NULL""",
                (sig_name, sid),
            ).fetchone()
            if existing:
                log.append(
                    f"  SKIP raw_obs={raw_id} sig={sig_name!r}: UNIQUE conflict"
                    f" with id={existing[0]}"
                )
                counts["skip_unique_conflict"] += 1
                continue

            file_rel, line = extract_file_line(excerpt)
            evidence_json = json.dumps({
                "evidence_excerpt": excerpt,
                "rationale": c.get("rationale"),
                "raw_observation_id": raw_id,
                "class": c.get("class"),
                "candidate_source": origin,
                "manufacturer_hint": mfr_hint,
            })
            notes_payload = {
                "integration_dispatch": "MAC-192",
                "cp_anchor": CP_ANCHOR,
                "integration_at_utc": NOW,
                "plan_confidence_band": band,
                "wave_i_14a_subpass": (
                    "41" if origin == "academic_subpass_41" else "42"
                ),
            }

            cur.execute(
                """INSERT INTO behavioral_signatures (
                       signature_name, cellular_generation, threshold_json,
                       evidence_json, source_id, source_file_relative,
                       source_line, confidence, device_category, notes,
                       created_at, updated_at
                   ) VALUES (?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sig_name,
                    evidence_json,
                    sid,
                    file_rel,
                    line,
                    conf,
                    cat,
                    json.dumps(notes_payload),
                    NOW,
                    NOW,
                ),
            )
            new_id = cur.lastrowid
            inserted_ids.append(new_id)
            counts["inserted"] += 1

            # Chain raw_observations.notes
            raw_notes_row = cur.execute(
                "SELECT notes FROM raw_observations WHERE id = ?", (raw_id,)
            ).fetchone()
            raw_notes = {}
            if raw_notes_row and raw_notes_row[0]:
                try:
                    raw_notes = json.loads(raw_notes_row[0])
                except Exception:
                    raw_notes = {"description": raw_notes_row[0]}
            raw_notes.setdefault("mac192_absorbed_to", []).append(
                f"behavioral_signatures.id={new_id}"
            )
            cur.execute(
                "UPDATE raw_observations SET notes = ? WHERE id = ?",
                (json.dumps(raw_notes), raw_id),
            )

        con.commit()
    except Exception:
        con.rollback()
        raise

    # Post-state readback
    cur.execute("SELECT COUNT(*) FROM behavioral_signatures")
    bs_total = cur.fetchone()[0]
    log.append("")
    log.append("## Per-outcome counts")
    for k, v in counts.items():
        log.append(f"  {k}: {v}")
    log.append(f"\n## Post-state behavioral_signatures total: {bs_total} (expect 131+{counts['inserted']}={131+counts['inserted']})")
    log.append(f"## New row id range: {inserted_ids[0] if inserted_ids else 'n/a'}-{inserted_ids[-1] if inserted_ids else 'n/a'}")

    LOG.write_text("\n".join(log))
    print(f"§6.3 done. {counts} bs_total={bs_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
