#!/usr/bin/env python3
"""MAC-118 F2 — sid=41 license_posture resolution + 14-identifier backfill.

Per CEO ratification on MAC-118 [comment b012ac69].

Resolution:
- sid=41 = GitHub: GainSec/anti-crime-ecosystem-research, pinned commit `d2468ad`
- LICENSE verdict (from staged surfacing.md at raw/wave_a/GainSec_anti-crime-ecosystem-research/2026-05-11T05-31-51Z_surfacing.md):
    CC BY-NC-ND 4.0 + Research-Use clause, Copyright 2025 Jon "GainSec" Gaines.
    research-extract-permitted (factual identifiers, attribution-required,
    NoDerivatives applies to redistribution-of-content not to derived
    structured DB rows).
- Canonical posture: `CC-BY-NC-ND-4.0_with_research_use_clause`
  (matches existing posture taxonomy: AGPL-3.0_declared, AGPL-3.0_inherited_from_upstream_id_20,
   NO_LICENSE_DECLARED_flagged_for_validator).
- Canonical sentinel-key shape per F1 ratification: `notes.upstream_license_posture`.

Idempotent: re-running over the already-backfilled state produces zero writes.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db" / "argus.db"
SID = 41
CANONICAL_POSTURE = "CC-BY-NC-ND-4.0_with_research_use_clause"
PLACEHOLDER = "<verify-in-mapper-from-LICENSE-file>"

# Provenance anchor — staged surfacing.md path documenting the LICENSE verdict.
PROVENANCE = (
    "raw/wave_a/GainSec_anti-crime-ecosystem-research/"
    "2026-05-11T05-31-51Z_surfacing.md (Wave-A Phase 6δ Surfacing, "
    "repo SHA d2468adb8b62cf62f7352510da00d6e8c4623f7c)"
)


def find_sid41_identifier_ids(conn: sqlite3.Connection) -> list[int]:
    """Find identifiers linked to sid=41 via notes.raw_observation_id."""
    roids = {r[0] for r in conn.execute("SELECT id FROM raw_observations WHERE source_id=?", (SID,))}
    matched: list[int] = []
    for row in conn.execute("SELECT id, notes FROM identifiers"):
        if not row[1]:
            continue
        try:
            n = json.loads(row[1])
        except Exception:
            continue
        if n.get("raw_observation_id") in roids:
            matched.append(row[0])
    return matched


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # ── Step 1: sources sid=41 license_posture resolve ────────────────────
    row = conn.execute("SELECT id, notes FROM sources WHERE id=?", (SID,)).fetchone()
    if row is None:
        print(f"ERROR: sid={SID} not found")
        return 1
    notes = json.loads(row["notes"]) if row["notes"] else {}
    current_posture = notes.get("license_posture")
    sources_changed = False
    if current_posture == PLACEHOLDER:
        notes["license_posture"] = CANONICAL_POSTURE
        notes["license_posture_provenance"] = PROVENANCE
        notes["license_posture_resolved_at_mac"] = "MAC-118"
        notes["license_posture_resolved_dispatch"] = "b012ac69"
        conn.execute("UPDATE sources SET notes=? WHERE id=?", (json.dumps(notes), SID))
        sources_changed = True
        print(f"sources sid={SID}: {PLACEHOLDER!r} → {CANONICAL_POSTURE!r}")
    elif current_posture == CANONICAL_POSTURE:
        print(f"sources sid={SID}: already at canonical {CANONICAL_POSTURE!r} (idempotent no-op)")
    else:
        print(f"WARN: sources sid={SID} has unexpected license_posture={current_posture!r}, not modifying")
        return 1

    # ── Step 2: backfill 14 identifiers with notes.upstream_license_posture ──
    ids = find_sid41_identifier_ids(conn)
    print(f"Identifiers linked to sid={SID}: {len(ids)}")
    if len(ids) != 14:
        print(f"WARN: expected 14 identifiers per CEO directive, got {len(ids)}")
        return 1
    ids_changed = 0
    for iid in ids:
        row = conn.execute("SELECT notes FROM identifiers WHERE id=?", (iid,)).fetchone()
        try:
            n = json.loads(row["notes"]) if row["notes"] else {}
        except Exception:
            print(f"WARN: id={iid} notes not JSON, skipping")
            continue
        if n.get("upstream_license_posture") == CANONICAL_POSTURE:
            continue  # idempotent
        n["upstream_license_posture"] = CANONICAL_POSTURE
        n["upstream_license_posture_provenance"] = "sources.id=41 + MAC-118 F2 ratification"
        conn.execute("UPDATE identifiers SET notes=? WHERE id=?", (json.dumps(n), iid))
        ids_changed += 1
    print(f"Identifiers backfilled with upstream_license_posture={CANONICAL_POSTURE!r}: {ids_changed}/{len(ids)}")

    conn.commit()
    conn.close()

    # ── Step 3: verification re-read ───────────────────────────────────────
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT notes FROM sources WHERE id=?", (SID,)).fetchone()
    print()
    print("VERIFY sources sid=41 notes:")
    print(f"  {r['notes']}")
    print()
    print("VERIFY 14 identifiers (upstream_license_posture present):")
    bad = []
    for iid in find_sid41_identifier_ids(conn):
        n = json.loads(conn.execute("SELECT notes FROM identifiers WHERE id=?", (iid,)).fetchone()[0])
        if n.get("upstream_license_posture") != CANONICAL_POSTURE:
            bad.append(iid)
    if bad:
        print(f"  FAIL: {len(bad)} identifiers missing canonical posture: {bad}")
        return 1
    print(f"  PASS: 14/14 identifiers carry notes.upstream_license_posture={CANONICAL_POSTURE!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
