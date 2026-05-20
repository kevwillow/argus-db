"""MAC-192 §6.5 — apply 47-vendor cert-issuer supply-chain enrichment.

Per dispatch §6.5: populate `manufacturers.notes.cert_issuer_supply_chain` for
47 vendors per Wave I.14a sub-pass 43. Honeywell rows STAGE to
honeywell_staged_for_phase_8.md (do NOT mutate the existing MAC-178 stub row).

Apply pattern:
- For each non-Honeywell vendor in the 47-list, resolve canonical, append
  ct_log_cert_total + top_5_issuer_organizations to
  manufacturers.notes.cert_issuer_supply_chain. Idempotent: MAC-192 entry
  detected → skip.
- Honeywell vendor (1 of 47) stages.
- honeywell_acs_division_attestation (7 firmware-embedded code-signing certs)
  stages separately under §6.5 staging surface.

SAR-13.5: Honeywell-targeted attestations sourced from honeywell-firmware S3
bucket carry `attribution_status='confirmed_via_sar_13_5_bucket_audit'`.
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
LOG = Path("/home/kev/argus/_phase_6_wave_i_14a/cert_issuer_supply_chain_log.md")
HONEYWELL_STAGE = Path(
    "/home/kev/argus/_phase_6_wave_i_14a/honeywell_staged_for_phase_8.md"
)
NOW = datetime.datetime.now(datetime.UTC).isoformat()
CP_ANCHOR = "phase_6_§6.5_cert_issuer_supply_chain"


def load_canonical_map(con: sqlite3.Connection) -> dict[str, tuple[int, str]]:
    out: dict[str, tuple[int, str]] = {}
    for mid, canon, aliases in con.execute(
        "SELECT id, canonical_name, aliases FROM manufacturers"
    ):
        out[canon.lower()] = (mid, canon)
        if aliases:
            for a in aliases.split(","):
                a = a.strip()
                if a:
                    out.setdefault(a.lower(), (mid, canon))
    return out


def parse_notes(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"description": raw}


def main() -> int:
    plan = json.loads(PLAN.read_text())
    ct = plan["ct_log_alias_enrichment_proposals"]
    supply_chain = ct["issuer_supply_chain_enrichment"]
    hw_attestation = ct["honeywell_acs_division_attestation"]

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cmap = load_canonical_map(con)

    log: list[str] = []
    log.append("# §6.5 cert-issuer supply-chain enrichment log — MAC-192 Phase 6")
    log.append(f"Captured: {NOW}")
    log.append(f"Plan vendors: {len(supply_chain)}")
    log.append("")

    counts = {
        "applied": 0,
        "skipped_idempotent": 0,
        "honeywell_staged_vendor": 0,
        "honeywell_staged_attestation": 0,
        "halt_unresolved": 0,
    }

    honeywell_chunks: list[str] = []
    if HONEYWELL_STAGE.exists():
        honeywell_chunks.append(HONEYWELL_STAGE.read_text())

    cur.execute("BEGIN")
    try:
        for v in supply_chain:
            vendor_name = v["vendor"]
            value = v["value"]
            log.append(f"## {vendor_name!r}")

            if vendor_name.lower().startswith("honeywell"):
                honeywell_chunks.append(
                    "\n## §6.5 cert-issuer vendor row stage\n\n"
                    f"- vendor: {vendor_name!r}\n"
                    f"- ct_log_cert_total: {value['ct_log_cert_total']}\n"
                    f"- top_5_issuer_organizations: "
                    f"{json.dumps(value['top_5_issuer_organizations'])}\n"
                    "- attribution_status: confirmed_via_sar_13_5_bucket_audit\n"
                    "- integration_dispatch: MAC-192\n"
                    f"- cp_anchor: {CP_ANCHOR}\n"
                    "- action: APPEND to manufacturers.notes.cert_issuer_supply_chain"
                    " for Honeywell at Phase 8 (after admission finalized)\n"
                )
                counts["honeywell_staged_vendor"] += 1
                log.append("  STAGED for Phase 8")
                continue

            resolved = cmap.get(vendor_name.lower())
            if resolved is None:
                # Try light fuzzy: drop punctuation/case
                resolved = cmap.get(
                    vendor_name.replace(",", "").replace(".", "").strip().lower()
                )
            if resolved is None:
                log.append(f"  HALT: vendor {vendor_name!r} not in canonical lexicon")
                counts["halt_unresolved"] += 1
                continue
            mid, canonical = resolved

            row = cur.execute(
                "SELECT notes FROM manufacturers WHERE id = ?", (mid,)
            ).fetchone()
            notes = parse_notes(row[0])
            cisc = notes.get("cert_issuer_supply_chain", [])
            # Idempotency: any MAC-192 entry for this vendor?
            if any(
                e.get("integration_dispatch") == "MAC-192"
                for e in cisc
                if isinstance(e, dict)
            ):
                log.append(
                    f"  SKIP-IDEMPOTENT mfr={canonical!r} (id={mid}): MAC-192 entry present"
                )
                counts["skipped_idempotent"] += 1
                continue
            entry = {
                "ct_log_cert_total": value["ct_log_cert_total"],
                "top_5_issuer_organizations": value["top_5_issuer_organizations"],
                "wave_i_14a_subpass": "43",
                "integration_dispatch": "MAC-192",
                "cp_anchor": CP_ANCHOR,
                "integration_at_utc": NOW,
            }
            cisc.append(entry)
            notes["cert_issuer_supply_chain"] = cisc
            cur.execute(
                "UPDATE manufacturers SET notes = ? WHERE id = ?",
                (json.dumps(notes), mid),
            )
            counts["applied"] += 1
            log.append(
                f"  APPLY mfr={canonical!r} (id={mid}): cert_issuer_supply_chain"
                f" count={len(cisc)}"
            )

        # honeywell ACS attestation -> stage
        honeywell_chunks.append(
            "\n## §6.5 honeywell_acs_division_attestation stage\n\n"
            f"- evidence: {hw_attestation['evidence']!r}\n"
            "- manufacturers_notes_enrichment proposal:\n"
            "  ```json\n"
            f"  {json.dumps(hw_attestation['manufacturers_notes_enrichment'], indent=2)}\n"
            "  ```\n"
            "- attribution_status: confirmed_via_sar_13_5_bucket_audit\n"
            "- integration_dispatch: MAC-192\n"
            f"- cp_anchor: {CP_ANCHOR}_acs_attestation\n"
            "- action: at Phase 8, append to Honeywell.notes."
            "honeywell_acs_division_attestation as a structured entry\n"
        )
        counts["honeywell_staged_attestation"] += 1

        con.commit()
    except Exception as ex:
        con.rollback()
        log.append(f"  ROLLBACK: {ex!r}")
        raise

    # Honeywell staging file
    HONEYWELL_STAGE.write_text("\n".join(honeywell_chunks) + "\n")

    log.append("")
    log.append("## Per-outcome counts")
    for k, v in counts.items():
        log.append(f"  {k}: {v}")

    # Sample post-state readback
    log.append("")
    log.append("## Post-state sample readback (cert_issuer_supply_chain)")
    for canon in ["Autel Robotics", "Axis Communications", "Axon", "DJI", "Hikvision", "Honeywell"]:
        r = cur.execute(
            "SELECT id, json_extract(notes, '$.cert_issuer_supply_chain') FROM manufacturers WHERE canonical_name = ?",
            (canon,),
        ).fetchone()
        if r:
            ext = (r[1] or "null")[:160]
            log.append(f"  {canon} (id={r[0]}): {ext}")

    LOG.write_text("\n".join(log))
    print(f"§6.5 done. {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
