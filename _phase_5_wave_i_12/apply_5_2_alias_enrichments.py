"""MAC-191 §5.2 — Apply alias enrichments (304 proposals).

Pipeline per dispatch §5.2:
1. Filter §5.4 DEFER entries out of the conditional set (operator_review_required=true).
2. For each remaining proposal:
   a. Look up manufacturer by id; halt-and-surface if not found.
   b. Verify canonical_name match (sanity check vs plan).
   c. Split current aliases on ',' (trim, case-insensitive); skip if duplicate.
   d. UPDATE aliases via append-pattern.
3. Per-manufacturer batch transaction.
4. Log every action.

§11 #1: no fabrication. Halt-surface on canonical-lexicon miss.
§11 #7: provenance — alias addition is corporate-name metadata. No identifier rows touched.
§11 #8: no confidence drift. Aliases are not identifier rows.
"""
from __future__ import annotations

import datetime
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

DB = Path("/home/kev/argus/db/argus.db")
PLAN = Path(
    "/home/kev/argus-internal/wave_i_pre_v1/wave_i_12_reconciliation_v2/RECONCILIATION_PLAN_V2_FOR_PAPERCLIP_V1_4_1.json"
)
LOG = Path("/home/kev/argus/_phase_5_wave_i_12/alias_enrichment_log.md")
NOW = datetime.datetime.now(datetime.UTC).isoformat()

# Conditional PROMOTE list from §5.4 review (per conditional_review_log.md).
# Keyed by (manufacturer_id, axis, proposed_alias_value).
CONDITIONAL_PROMOTES: set[tuple[int, str, str]] = {
    # FCC
    (15, "fcc_grantees", "Axon Enterprise, Inc"),
    (25, "fcc_grantees", "PARROT DRONE SAS"),
    # USAspending
    (15, "usaspending", "AXON ENTERPRISE, INC."),
    # Deployment observations
    (1, "deployment_observations_variants", "Flock Group Inc."),
    (15, "deployment_observations_variants", "Axon Enterprise"),
    (8, "deployment_observations_variants", "Harris Corp."),
    (1, "deployment_observations_variants", "Flock Surveillance"),
    (15, "deployment_observations_variants", "Axon Body-2"),
    (15, "deployment_observations_variants", "Axon Flex"),
    (1, "deployment_observations_variants", "Flock Safetu"),
    (1, "deployment_observations_variants", "Flock Saftey"),
}


def main() -> int:
    plan = json.loads(PLAN.read_text())
    by_axis = plan["manufacturer_aliases_enrichment_proposals"]["by_axis"]

    # Flatten all proposals annotated with axis
    proposals: list[dict] = []
    for axis, payload in by_axis.items():
        for p in payload["proposals"]:
            p_copy = dict(p)
            p_copy["_axis"] = axis
            proposals.append(p_copy)

    # Filter: keep all high-confidence + only the 11 conditional PROMOTEs
    kept: list[dict] = []
    deferred_count = 0
    for p in proposals:
        if p["operator_review_required"]:
            key = (p["manufacturer_id"], p["_axis"], p["proposed_alias_value"])
            if key in CONDITIONAL_PROMOTES:
                kept.append(p)
            else:
                deferred_count += 1
        else:
            kept.append(p)

    log: list[str] = []
    log.append("# §5.2 Alias enrichment log — MAC-191 Phase 5")
    log.append(f"Captured: {NOW}")
    log.append("")
    log.append("## Pipeline counts")
    log.append(f"  total plan proposals: {len(proposals)}")
    log.append(f"  high-confidence + PROMOTE: {len(kept)}")
    log.append(f"  §5.4 DEFER (skipped): {deferred_count}")
    log.append("")

    # Group by manufacturer_id for batched transaction
    by_mid: dict[int, list[dict]] = defaultdict(list)
    for p in kept:
        by_mid[p["manufacturer_id"]].append(p)

    con = sqlite3.connect(DB)
    cur = con.cursor()

    applied = 0
    duplicates = 0
    identity_with_canonical = 0
    halted = 0
    halts: list[dict] = []

    for mid in sorted(by_mid.keys()):
        # Per-manufacturer atomic transaction
        cur.execute("BEGIN")
        try:
            row = cur.execute(
                "SELECT id, canonical_name, aliases FROM manufacturers WHERE id = ?",
                (mid,),
            ).fetchone()
            if row is None:
                halts.append(
                    {
                        "manufacturer_id": mid,
                        "reason": "not_found_in_canonical_lexicon",
                        "first_proposal": by_mid[mid][0],
                    }
                )
                halted += len(by_mid[mid])
                con.rollback()
                continue

            current_id, canonical_name, aliases_csv = row
            current_aliases = (
                [a.strip() for a in (aliases_csv or "").split(",") if a.strip()]
                if aliases_csv
                else []
            )
            seen_lower = {a.lower() for a in current_aliases}
            seen_lower.add(canonical_name.lower())  # canonical-name redundancy guard

            log.append(f"## id={current_id} \"{canonical_name}\"")
            log.append(f"  current_aliases (n={len(current_aliases)}): {current_aliases}")

            for p in by_mid[mid]:
                proposed = p["proposed_alias_value"]
                axis = p["_axis"]
                # Sanity check: plan canonical_name matches actual
                if p["canonical_name"] != canonical_name:
                    log.append(
                        f"  - HALT-CANONICAL-MISMATCH: plan='{p['canonical_name']}' vs db='{canonical_name}' alias={proposed!r} axis={axis}"
                    )
                    halts.append(
                        {
                            "manufacturer_id": mid,
                            "reason": "canonical_name_mismatch",
                            "plan_name": p["canonical_name"],
                            "db_name": canonical_name,
                            "proposed_alias": proposed,
                            "axis": axis,
                        }
                    )
                    halted += 1
                    continue

                proposed_lower = proposed.strip().lower()
                # Skip if duplicate (matches existing alias OR matches canonical_name)
                if proposed_lower in seen_lower:
                    if proposed_lower == canonical_name.lower():
                        identity_with_canonical += 1
                        log.append(
                            f"  - SKIP-IDENTITY-CANONICAL: alias={proposed!r} matches canonical_name (axis={axis} tier={p['match_tier']})"
                        )
                    else:
                        duplicates += 1
                        log.append(
                            f"  - SKIP-DUPLICATE-CSV: alias={proposed!r} already in aliases (axis={axis} tier={p['match_tier']})"
                        )
                    continue

                # Apply append-pattern
                cur.execute(
                    """
                    UPDATE manufacturers
                    SET aliases = CASE
                        WHEN aliases IS NULL OR aliases = '' THEN ?
                        ELSE aliases || ',' || ?
                    END
                    WHERE id = ?
                    """,
                    (proposed, proposed, mid),
                )
                assert cur.rowcount == 1
                current_aliases.append(proposed)
                seen_lower.add(proposed_lower)
                applied += 1
                ev = (
                    p.get("fcc_grantee_evidence")
                    or p.get("procurement_evidence")
                    or p.get("deployment_evidence")
                    or {}
                )
                conditional = " [conditional-PROMOTE]" if p.get("operator_review_required") else ""
                log.append(
                    f"  - APPLY: alias={proposed!r} axis={axis} tier={p['match_tier']} ev={json.dumps(ev)[:120]}{conditional}"
                )
            con.commit()
        except Exception as ex:
            con.rollback()
            log.append(f"  ROLLBACK on mid={mid}: {ex!r}")
            raise

    # Halts summary
    if halts:
        log.append("")
        log.append("## HALTS")
        for h in halts:
            log.append(f"  - {json.dumps(h)}")

    # Post-state spot-check
    log.append("")
    log.append("## Post-state spot-check")
    spot = cur.execute(
        "SELECT id, canonical_name, aliases FROM manufacturers WHERE id IN (1,2,4,7,8,15,25,29,32) ORDER BY id"
    ).fetchall()
    for r in spot:
        log.append(f"  id={r[0]} \"{r[1]}\": aliases={r[2]!r}")

    log.append("")
    log.append("## Totals")
    log.append(f"  applied = {applied}")
    log.append(f"  skip-duplicate-CSV = {duplicates}")
    log.append(f"  skip-identity-canonical = {identity_with_canonical}")
    log.append(f"  §5.4 deferred = {deferred_count}")
    log.append(f"  halted = {halted}")

    LOG.write_text("\n".join(log))
    print(f"Wrote {LOG}")
    print(
        f"  applied={applied} dup={duplicates} ident-canonical={identity_with_canonical} "
        f"§5.4 deferred={deferred_count} halted={halted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
