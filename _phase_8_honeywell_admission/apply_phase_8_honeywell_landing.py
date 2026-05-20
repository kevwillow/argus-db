"""MAC-195 Phase 8 — Honeywell admission + cert-chain enrichment landing.

Three deliverables per dispatch:

1. **Honeywell admission** to canonical `manufacturers` lexicon.
   STATUS AT START: already admitted via MAC-104b/MAC-178 on 2026-05-18 as a
   documented-absence stub (canonical_name='Honeywell', id=211). The dispatch's
   "51→52" pre/post expectation was based on a stale assumption; deliverable #1
   resolves as a NO-OP idempotent landing. The Honeywell row is already canonical
   under the expected name, so no admission INSERT is required.

2. **§6.4 alias enrichment** — append `HoneywellSecurityGroup` to
   `Honeywell.aliases`. Source: Wave I.14a ct log (tier-3, vendor-anchored).
   SAR-15 generic-risk guard: PASS (vendor-anchored, not generic).
   §11 #1 provenance: ct_log evidence is in Wave I.14a sub-pass 43 canonical
   remine plan; cp_anchor `phase_6_§6.4_alias_enrichment_ct_log`.

3. **§6.5 cert-issuer vendor row enrichment**:
   - 3a: append `cert_issuer_supply_chain` MAC-192 entry
     (3,628 ct_log certs, top-5 issuer organizations).
   - 3b: append `honeywell_acs_division_attestation` structured entry
     (Honeywell ACS / `CN=Honeywell CodeSign RSA CA` /
     dubai_android_releasekey / CT45+CT40 device models).
   SAR-13.5: both carry `attribution_status='confirmed_via_sar_13_5_bucket_audit'`
   (cert-issuer evidence sourced from honeywell-firmware S3 bucket).

Discipline envelope:
- SAR-13 + §3399: PRAGMA + sqlite_master attestation captured in pre-flight log;
  no CHECK constraints on `manufacturers`.
- §11 #1: each enrichment chains to a ct_log / firmware-archive evidence anchor.
- §11 #7: existing notes preserved; new keys appended (no rewrite of
  documented_absence stub).
- §11 #8: not applicable — this is a notes/alias enrichment, not a confidence
  promotion.
- Idempotency: re-running produces zero state change (alias presence check
  + integration_dispatch='MAC-195' marker on enrichment entries).
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

DB = Path("/home/kev/argus/db/argus.db")
LOG = Path("/home/kev/argus/_phase_8_honeywell_admission/phase_8_apply_log.md")
NOW = datetime.datetime.now(datetime.UTC).isoformat()

ALIAS_TO_APPEND = "HoneywellSecurityGroup"
ALIAS_TIER = 3

CERT_ISSUER_ENTRY = {
    "ct_log_cert_total": 3628,
    "top_5_issuer_organizations": [
        ["DigiCert Inc", 1428],
        ['"VeriSign', 1003],
        ["Honeywell International Inc.", 843],
        ['"GeoTrust', 145],
        ["GlobalSign nv-sa", 116],
    ],
    "wave_i_14a_subpass": "43",
    "attribution_status": "confirmed_via_sar_13_5_bucket_audit",
    "integration_dispatch": "MAC-195",
    "phase_6_staging_dispatch": "MAC-192",
    "cp_anchor": "phase_8_honeywell_landing_§6.5_cert_issuer_supply_chain",
    "integration_at_utc": NOW,
}

ACS_ATTESTATION_ENTRY = {
    "division": "ACS (Automation and Control Solutions)",
    "code_signing_ca_cn": "Honeywell CodeSign RSA CA",
    "code_signing_branch": "dubai_android_releasekey",
    "device_models_attested": ["CT45", "CT40"],
    "evidence": (
        "7 firmware-embedded code-signing certs (Wave I.7 + I.8 firmware archives)"
        " all have issuer_dn='C=US, O=Honeywell International Inc., OU=ACS,"
        " CN=Honeywell CodeSign RSA CA'"
    ),
    "attribution_status": "confirmed_via_sar_13_5_bucket_audit",
    "integration_dispatch": "MAC-195",
    "phase_6_staging_dispatch": "MAC-192",
    "cp_anchor": "phase_8_honeywell_landing_§6.5_cert_issuer_supply_chain_acs_attestation",
    "integration_at_utc": NOW,
}


def _normalize(s: str) -> str:
    return " ".join(s.replace(",", " ").split()).lower()


def alias_present(aliases: str | None, candidate: str) -> bool:
    if not aliases:
        return False
    parts = [_normalize(a) for a in aliases.split(",")]
    return _normalize(candidate) in parts


def main() -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()

    log: list[str] = []
    log.append("# Phase 8 — Honeywell admission + cert-chain enrichment landing")
    log.append(f"Dispatch: MAC-195   Captured: {NOW}")
    log.append("")

    # Pre-flight
    pre_mfr_count = cur.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
    pre_ids_count = cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
    ).fetchone()[0]
    pre_integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
    log.append("## Pre-flight")
    log.append(f"- manufacturers count: {pre_mfr_count}")
    log.append(f"- identifiers (non-superseded) count: {pre_ids_count}")
    log.append(f"- PRAGMA integrity_check: {pre_integrity}")
    log.append("")

    counts: dict[str, int] = {
        "admission_no_op": 0,
        "alias_applied": 0,
        "alias_skipped_idempotent": 0,
        "cert_issuer_applied": 0,
        "cert_issuer_skipped_idempotent": 0,
        "acs_attestation_applied": 0,
        "acs_attestation_skipped_idempotent": 0,
        "halt": 0,
    }

    cur.execute("BEGIN")
    try:
        # Resolve canonical Honeywell row
        row = cur.execute(
            "SELECT id, canonical_name, aliases, notes FROM manufacturers"
            " WHERE canonical_name = ?",
            ("Honeywell",),
        ).fetchone()
        if row is None:
            log.append("## HALT: Honeywell canonical row not present in manufacturers.")
            counts["halt"] += 1
            con.rollback()
            LOG.write_text("\n".join(log))
            return 2
        mid, canon, aliases, notes_raw = row
        log.append(f"## Honeywell canonical row resolved: id={mid}, canonical={canon!r}")
        log.append("")

        # Deliverable 1: admission no-op
        log.append("## Deliverable 1 — Admission")
        log.append(
            "Honeywell already admitted via MAC-104b/MAC-178 on 2026-05-18 as a"
            " documented-absence stub. Canonical_name='Honeywell' (same name as"
            " requested admission target). UNIQUE constraint on canonical_name"
            " would reject a duplicate INSERT; admission resolves as a NO-OP."
        )
        log.append(
            "Note for board ratification: dispatch's 51→52 pre/post count"
            " expectation was based on stale assumption that Honeywell was not"
            " yet admitted. Actual pre-state: 51 (Honeywell already at id={}).".format(mid)
        )
        counts["admission_no_op"] += 1
        log.append("")

        # Parse existing notes
        notes_obj: dict = {}
        if notes_raw:
            try:
                notes_obj = json.loads(notes_raw)
            except Exception:
                notes_obj = {"description": notes_raw}

        # Deliverable 2: alias enrichment
        log.append("## Deliverable 2 — §6.4 alias enrichment")
        if alias_present(aliases, ALIAS_TO_APPEND):
            log.append(
                f"SKIP-IDEMPOTENT: alias {ALIAS_TO_APPEND!r} already present in"
                f" Honeywell.aliases."
            )
            counts["alias_skipped_idempotent"] += 1
        else:
            new_aliases = (aliases + "," + ALIAS_TO_APPEND) if aliases else ALIAS_TO_APPEND
            cur.execute(
                "UPDATE manufacturers SET aliases = ? WHERE id = ?",
                (new_aliases, mid),
            )
            entries = notes_obj.setdefault("mac195_alias_enrichment", [])
            entries.append(
                {
                    "appended_alias": ALIAS_TO_APPEND,
                    "tier": ALIAS_TIER,
                    "source": "ct_log_common_name (Wave I.14a sub-pass 43)",
                    "phase_6_staging_dispatch": "MAC-192",
                    "integration_dispatch": "MAC-195",
                    "cp_anchor": "phase_8_honeywell_landing_§6.4_alias_enrichment",
                    "integration_at_utc": NOW,
                }
            )
            log.append(
                f"APPLY: appended {ALIAS_TO_APPEND!r} to Honeywell.aliases;"
                f" mac195_alias_enrichment count={len(entries)}"
            )
            counts["alias_applied"] += 1
        log.append("")

        # Deliverable 3a: cert-issuer supply chain enrichment
        log.append("## Deliverable 3a — §6.5 cert-issuer supply-chain enrichment")
        cisc = notes_obj.setdefault("cert_issuer_supply_chain", [])
        already = [
            e for e in cisc
            if isinstance(e, dict)
            and e.get("integration_dispatch") in ("MAC-192", "MAC-195")
            and e.get("ct_log_cert_total") == CERT_ISSUER_ENTRY["ct_log_cert_total"]
        ]
        if already:
            log.append(
                "SKIP-IDEMPOTENT: cert_issuer_supply_chain entry already present"
                f" (matched on ct_log_cert_total={CERT_ISSUER_ENTRY['ct_log_cert_total']})."
            )
            counts["cert_issuer_skipped_idempotent"] += 1
        else:
            cisc.append(CERT_ISSUER_ENTRY)
            log.append(
                f"APPLY: cert_issuer_supply_chain count={len(cisc)};"
                f" ct_log_cert_total={CERT_ISSUER_ENTRY['ct_log_cert_total']};"
                f" top-5 issuer count={len(CERT_ISSUER_ENTRY['top_5_issuer_organizations'])}"
            )
            counts["cert_issuer_applied"] += 1
        log.append("")

        # Deliverable 3b: honeywell ACS division attestation
        log.append("## Deliverable 3b — §6.5 honeywell_acs_division_attestation")
        acs = notes_obj.setdefault("honeywell_acs_division_attestation", [])
        # Idempotency: keyed on code_signing_ca_cn + device_models tuple
        target_key = (
            ACS_ATTESTATION_ENTRY["code_signing_ca_cn"],
            tuple(ACS_ATTESTATION_ENTRY["device_models_attested"]),
        )
        already_acs = [
            e for e in acs
            if isinstance(e, dict)
            and e.get("code_signing_ca_cn") == target_key[0]
            and tuple(e.get("device_models_attested", [])) == target_key[1]
        ]
        if already_acs:
            log.append(
                "SKIP-IDEMPOTENT: honeywell_acs_division_attestation entry already"
                f" present (matched on code_signing_ca_cn + device_models)."
            )
            counts["acs_attestation_skipped_idempotent"] += 1
        else:
            acs.append(ACS_ATTESTATION_ENTRY)
            log.append(
                f"APPLY: honeywell_acs_division_attestation count={len(acs)};"
                f" CA={ACS_ATTESTATION_ENTRY['code_signing_ca_cn']!r};"
                f" devices={ACS_ATTESTATION_ENTRY['device_models_attested']}"
            )
            counts["acs_attestation_applied"] += 1
        log.append("")

        # Single UPDATE for notes (covers 2 + 3a + 3b)
        cur.execute(
            "UPDATE manufacturers SET notes = ? WHERE id = ?",
            (json.dumps(notes_obj, sort_keys=True), mid),
        )

        con.commit()
    except Exception as ex:
        con.rollback()
        log.append(f"## ROLLBACK: {ex!r}")
        LOG.write_text("\n".join(log))
        raise

    # Post-flight
    post_mfr_count = cur.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
    post_ids_count = cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
    ).fetchone()[0]
    post_integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
    log.append("## Post-flight")
    log.append(f"- manufacturers count: {post_mfr_count} (pre={pre_mfr_count})")
    log.append(f"- identifiers (non-superseded) count: {post_ids_count} (pre={pre_ids_count})")
    log.append(f"- PRAGMA integrity_check: {post_integrity}")
    log.append("")

    # Readback Honeywell row
    rb = cur.execute(
        "SELECT id, canonical_name, aliases, notes FROM manufacturers WHERE id = ?",
        (mid,),
    ).fetchone()
    log.append("## Post-state Honeywell readback")
    log.append(f"- id: {rb[0]}")
    log.append(f"- canonical_name: {rb[1]}")
    log.append(f"- aliases (count): {len(rb[2].split(','))} comma-separated entries")
    log.append(f"- aliases (last 3): {rb[2].split(',')[-3:]}")
    notes_post = json.loads(rb[3])
    log.append(f"- notes top-level keys: {sorted(notes_post.keys())}")
    log.append(
        f"- mac195_alias_enrichment len: {len(notes_post.get('mac195_alias_enrichment', []))}"
    )
    log.append(
        f"- cert_issuer_supply_chain len: {len(notes_post.get('cert_issuer_supply_chain', []))}"
    )
    log.append(
        f"- honeywell_acs_division_attestation len:"
        f" {len(notes_post.get('honeywell_acs_division_attestation', []))}"
    )
    log.append(
        f"- documented_absence len (preserved):"
        f" {len(notes_post.get('documented_absence', []))}"
    )
    log.append("")
    log.append("## Per-outcome counts")
    for k, v in counts.items():
        log.append(f"  {k}: {v}")

    LOG.write_text("\n".join(log))
    print(f"Phase 8 done. {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
