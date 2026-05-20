"""MAC-192 §6.4 — apply 3 alias enrichments.

Per dispatch §6.4 + Phase 5 §5.2 alias-append pattern with SAR-15
GENERIC_RISK_CANONICALS guard (these are tier-2/3 substring matches with
industry-domain context per dispatch, so guard passes):

  - 'Verkada Inc' (tier-2)        → manufacturers.aliases for Verkada
  - 'Cellebrite DI LTD' (tier-3)  → manufacturers.aliases for Cellebrite
  - 'HoneywellSecurityGroup' (tier-3) → STAGE for Phase 8

Idempotent: skip if alias already present (case-insensitive substring).
Honeywell-targeted alias stays in `honeywell_staged_for_phase_8.md`.
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

DB = Path("/home/kev/argus/db/argus.db")
PLAN = Path(
    "/home/kev/argus-internal/wave_i_pre_v1/wave_i_14a_canonical_remine/"
    "RECONCILIATION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json"
)
LOG = Path("/home/kev/argus/_phase_6_wave_i_14a/alias_enrichment_log.md")
HONEYWELL_STAGE = Path(
    "/home/kev/argus/_phase_6_wave_i_14a/honeywell_staged_for_phase_8.md"
)

NOW = datetime.datetime.now(datetime.UTC).isoformat()


def _normalize(s: str) -> str:
    # Aliases are comma-separated. Internal commas in a candidate would break
    # parsing, so for matching/storage purposes we strip them and collapse
    # whitespace. "Verkada, Inc" -> "verkada inc" matches existing "Verkada Inc".
    return " ".join(s.replace(",", " ").split()).lower()


def alias_present(aliases: str | None, candidate: str) -> bool:
    if not aliases:
        return False
    parts = [_normalize(a) for a in aliases.split(",")]
    return _normalize(candidate) in parts


def sanitize_for_storage(candidate: str) -> str:
    # Strip internal commas (alias list is comma-delimited).
    return " ".join(candidate.replace(",", " ").split())


def append_alias(aliases: str | None, candidate: str) -> str:
    candidate = sanitize_for_storage(candidate)
    if not aliases:
        return candidate
    return aliases + "," + candidate


def main() -> int:
    plan = json.loads(PLAN.read_text())
    proposals = plan["ct_log_alias_enrichment_proposals"][
        "ct_log_alias_enrichment_proposals"
    ]

    con = sqlite3.connect(DB)
    cur = con.cursor()

    log: list[str] = []
    log.append("# §6.4 alias enrichment log — MAC-192 Phase 6")
    log.append(f"Captured: {NOW}")
    log.append(f"Proposals: {len(proposals)}")
    log.append("")
    log.append("SAR-15 GENERIC_RISK_CANONICALS guard: tier-2/3 candidates with")
    log.append("industry-domain context per dispatch §6.4 — guard passes.")
    log.append("")

    counts = {"applied": 0, "skipped_idempotent": 0, "honeywell_staged": 0, "halt": 0}
    honeywell_log: list[str] = []
    if HONEYWELL_STAGE.exists():
        honeywell_log.append(HONEYWELL_STAGE.read_text())

    for p in proposals:
        ct_cn = p["ct_log_common_name"]
        target_canonical = p["matched_canonical"]
        tier = p["tier"]
        log.append(f"## {ct_cn!r} → {target_canonical!r} (tier-{tier})")

        if target_canonical == "Honeywell":
            honeywell_log.append(
                f"\n## §6.4 alias enrichment stage\n\n"
                f"- ct_log_common_name: {ct_cn!r}\n"
                f"- matched_canonical: {target_canonical!r}\n"
                f"- tier: {tier}\n"
                f"- action: APPEND to manufacturers.aliases for Honeywell (after"
                " Phase 8 finalizes admission)\n"
                f"- integration_dispatch: MAC-192\n"
                f"- cp_anchor: phase_6_§6.4_alias_enrichment_honeywell_staged\n"
            )
            counts["honeywell_staged"] += 1
            log.append("  STAGED for Phase 8 (no Phase-6 mutation of Honeywell row)")
            continue

        cur.execute("BEGIN")
        try:
            row = cur.execute(
                "SELECT id, canonical_name, aliases FROM manufacturers"
                " WHERE canonical_name = ?",
                (target_canonical,),
            ).fetchone()
            if row is None:
                log.append(
                    f"  HALT: canonical {target_canonical!r} not in lexicon"
                )
                counts["halt"] += 1
                con.rollback()
                continue
            mid, canon, aliases = row
            if alias_present(aliases, ct_cn):
                log.append(
                    f"  SKIP-IDEMPOTENT: alias already present in"
                    f" {target_canonical!r}.aliases"
                )
                counts["skipped_idempotent"] += 1
                con.rollback()
                continue
            new_aliases = append_alias(aliases, ct_cn)
            cur.execute(
                "UPDATE manufacturers SET aliases = ? WHERE id = ?",
                (new_aliases, mid),
            )
            # Annotate via notes (provenance)
            notes_row = cur.execute(
                "SELECT notes FROM manufacturers WHERE id = ?", (mid,)
            ).fetchone()
            notes_obj = {}
            if notes_row and notes_row[0]:
                try:
                    notes_obj = json.loads(notes_row[0])
                except Exception:
                    notes_obj = {"description": notes_row[0]}
            entries = notes_obj.setdefault("mac192_alias_enrichment", [])
            entries.append(
                {
                    "appended_alias": ct_cn,
                    "tier": tier,
                    "source_vendor_dir": p.get("source_vendor_dir"),
                    "integration_dispatch": "MAC-192",
                    "cp_anchor": "phase_6_§6.4_alias_enrichment_ct_log",
                    "integration_at_utc": NOW,
                }
            )
            cur.execute(
                "UPDATE manufacturers SET notes = ? WHERE id = ?",
                (json.dumps(notes_obj), mid),
            )
            counts["applied"] += 1
            log.append(
                f"  APPLY: aliases now '{new_aliases}'; mac192_alias_enrichment"
                f" count={len(entries)}"
            )
            con.commit()
        except Exception as ex:
            con.rollback()
            log.append(f"  ROLLBACK: {ex!r}")
            raise

    # Honeywell staging file (preserve any prior content)
    HONEYWELL_STAGE.write_text("\n".join(honeywell_log) + "\n")

    # Post-state readback
    for canon in ["Verkada", "Cellebrite", "Honeywell"]:
        row = cur.execute(
            "SELECT id, canonical_name, aliases FROM manufacturers WHERE canonical_name = ?",
            (canon,),
        ).fetchone()
        if row:
            log.append(f"\n## post-state {canon}: {row[2]}")

    log.append("")
    log.append("## Per-outcome counts")
    for k, v in counts.items():
        log.append(f"  {k}: {v}")

    LOG.write_text("\n".join(log))
    print(f"§6.4 done. {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
