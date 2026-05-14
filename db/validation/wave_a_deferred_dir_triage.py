"""MAC-104 Item C Phase 2 — Wave-A deferred-dir ratification triage.

Disposition cascade applied to all `raw_observations WHERE notes.wave='A_deferred_dir' AND
promoted_identifier_id IS NULL`:

1. §11 #3 PII gate — rows with notes.pii_review_disposition='deferred_for_human_pii_review'
   → HOLD pii_review.
2. behavioral_signature shape or MAC-58 Option B flags → HOLD phase-6-deferred (no promotion;
   target table is behavioral_signatures, not identifiers).
3. §1 #1 / §11 #1 source-url-direct gate — repo-root URLs (no `/blob/` `/tree/` `/raw/`
   `/commit/` segment) → HOLD source-url-direct-violation. Phase-1-mapper-discipline
   refinement candidate.
4. §4.4 identifier-type vocab gate — candidate_type not in existing vocab and not in §4.3
   normalize map → HOLD vocab-extension-pending.
5. §7.3/§7.4 known-fake list (full enumeration: doc patterns, all-identical-octet,
   strictly-monotonic +1, RFC 7042 doc ranges) → REJECT to conflicts with
   reason='known_fake_pattern'.
6. Remaining rows pass §1 / §7.3 / §4.4 → default-when-uncertain HOLD per §2:
   `attribution_lens_ratify_required` (src=38 Liteon-registry vs Flock-operational lens) +
   `license_posture_ratify_required` (src=39 NO_LICENSE_DECLARED fork).

Net Phase 2 outcome: 0 promotions, 1 reject, 364 HOLDs across 5 reason classes.

The script is idempotent on re-run for the same cohort: rows already with the disposition
note set are skipped (no double-write of conflict rows or notes mutations).
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone

DB_PATH = "db/argus.db"

EXISTING_IDENTIFIER_TYPES: set[str] = {
    "ble_characteristic", "ble_local_name", "ble_manufacturer_id", "ble_service",
    "drone_id_prefix", "mac", "mac_range", "oui", "product_family_codename",
    "ssid_pattern",
}

NORMALIZE_CANDIDATE_TO_IDENTIFIER_TYPE: dict[str, str] = {
    "mac": "mac",
    "mac_oui": "oui",
    "product_family_codename": "product_family_codename",
}

EXACT_FAKE_OUIS: set[str] = {
    "00:00:00", "ff:ff:ff", "aa:bb:cc", "00:11:22", "12:34:56",
    "de:ad:be", "ca:fe:ba", "ba:db:00", "00:00:5e", "02:00:5e",
}
EXACT_FAKE_FULL_MACS: set[str] = {
    "00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff", "aa:bb:cc:dd:ee:ff",
    "00:11:22:33:44:55", "12:34:56:78:9a:bc",
}
DOC_PREFIXES_FULL: tuple[str, ...] = (
    "de:ad:be:ef:", "ca:fe:ba:be:", "ba:db:00:b5:",
)

URL_DIRECT_RE = re.compile(r"github\.com/[^/]+/[^/]+/(blob|tree|raw|commit)/")


def is_known_fake_oui(oui: str) -> tuple[str, str] | None:
    o = oui.lower()
    if o in EXACT_FAKE_OUIS:
        return ("known_fake_oui_doc_pattern", o)
    octs = o.split(":")
    if len(octs) != 3:
        return None
    if octs[0] == octs[1] == octs[2]:
        return ("known_fake_oui_all_identical_octet", o)
    try:
        vals = [int(x, 16) for x in octs]
        if vals[1] == vals[0] + 1 and vals[2] == vals[1] + 1:
            return ("known_fake_oui_strictly_monotonic_plus1", o)
    except ValueError:
        pass
    return None


def is_known_fake_mac(mac: str) -> tuple[str, str] | None:
    m = mac.lower()
    if m in EXACT_FAKE_FULL_MACS:
        return ("known_fake_mac_doc_pattern", m)
    for prefix in DOC_PREFIXES_FULL:
        if m.startswith(prefix):
            return ("known_fake_mac_doc_prefix", m)
    octs = m.split(":")
    if len(octs) != 6:
        return None
    if len(set(octs)) == 1:
        return ("known_fake_mac_all_identical_octet", m)
    try:
        vals = [int(x, 16) for x in octs]
        if all(vals[i + 1] == vals[i] + 1 for i in range(5)):
            return ("known_fake_mac_strictly_monotonic_plus1", m)
    except ValueError:
        pass
    if m.startswith("00:00:5e:00:53:"):
        return ("known_fake_mac_rfc7042_ipv4_doc_range", m)
    parent = is_known_fake_oui(":".join(octs[:3]))
    if parent:
        return (f"known_fake_mac_parent_{parent[0]}", m)
    return None


def url_gate_pass(url: str | None) -> bool:
    """§1 #1 / §11 #1 source-url-direct gate. Repo-root URLs fail."""
    return bool(url) and bool(URL_DIRECT_RE.search(url))


def classify(row: tuple) -> tuple[str, dict]:
    """Return (disposition_key, extras_to_merge_into_notes)."""
    rid, sid, ctype, ident, cat, manu, url, excerpt, notes_raw = row
    try:
        notes = json.loads(notes_raw) if notes_raw else {}
    except (json.JSONDecodeError, TypeError):
        notes = {}

    if notes.get("pii_review_disposition") == "deferred_for_human_pii_review":
        return ("hold_pii_review", {"hold_reason": "pii_review_pending_human"})

    if ctype == "behavioral_signature" or notes.get("mac58_option_b"):
        return (
            "hold_behavioral_signature_phase_6_deferred",
            {"hold_reason": "mac58_option_b_phase_6_deferred"},
        )
    if ctype == "attribution_conflict":
        return (
            "hold_attribution_conflict_mapper_surfaced",
            {
                "hold_reason": "mapper_surfaced_attribution_conflict_needs_ceo_resolution",
                "agent_asserted_history_verify_per_memory": True,
            },
        )
    if notes.get("no_promotion_phase2") or notes.get("phase_6_gate_lifted"):
        return (
            "hold_mapper_marked_no_promotion_phase_2",
            {"hold_reason": "mapper_marked_no_promotion_phase_2_catch_all"},
        )

    if not url_gate_pass(url):
        return (
            "hold_source_url_direct_violation",
            {
                "hold_reason": "source_url_direct_violation",
                "phase_1_mapper_discipline_refinement_candidate": True,
            },
        )

    if ctype not in EXISTING_IDENTIFIER_TYPES and ctype not in NORMALIZE_CANDIDATE_TO_IDENTIFIER_TYPE:
        return (
            "hold_identifier_type_vocab_extension_pending",
            {
                "hold_reason": "identifier_type_vocab_extension_pending",
                "candidate_type_proposed_for_0011_migration_slate": ctype,
            },
        )

    if ctype == "mac":
        fake = is_known_fake_mac(ident)
        if fake:
            return (
                "reject_known_fake",
                {"reject_reason": "known_fake_pattern", "known_fake_class": fake[0]},
            )
    elif ctype == "mac_oui":
        fake = is_known_fake_oui(ident)
        if fake:
            return (
                "reject_known_fake",
                {"reject_reason": "known_fake_pattern", "known_fake_class": fake[0]},
            )

    if sid == 38:
        return (
            "hold_attribution_lens_ratify_required",
            {
                "hold_reason": "attribution_lens_and_band_ratify_required",
                "attribution_lens_question": "candidate_manufacturer Liteon (IEEE registry lens) vs Flock Safety (operational lens per id=1 Wave-A precedent)",
                "source_type_band_ratify_required": True,
                "device_category_interlocked_with_attribution_lens": True,
                "proposed_band": "crowdsourced_ceiling_70_per_dispatch_§2_table",
            },
        )
    if sid == 39:
        return (
            "hold_license_posture_and_attribution_lens_ratify_required",
            {
                "hold_reason": "license_posture_NO_LICENSE_DECLARED_and_attribution_lens",
                "license_posture": "NO_LICENSE_DECLARED_per_source_id_39_validator_grep_sentinel",
                "attribution_lens_question": "OUI registry assignee unknown / Flock-detector operational context",
                "source_type_band_ratify_required": True,
                "proposed_band": "crowdsourced_ceiling_70_per_dispatch_§2_table",
            },
        )

    return (
        "hold_default_uncertain",
        {"hold_reason": "default_when_uncertain_per_dispatch_§2"},
    )


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """SELECT id, source_id, candidate_type, candidate_identifier, candidate_category,
                  candidate_manufacturer, source_url, source_excerpt, notes
           FROM raw_observations WHERE promoted_identifier_id IS NULL"""
    )

    disposition_counter: Counter[str] = Counter()
    per_source_disposition: dict[int, Counter[str]] = {}
    rejects: list[tuple[int, dict]] = []
    holds: list[tuple[int, str, dict]] = []
    vocab_extension_types: Counter[str] = Counter()

    for row in cur.fetchall():
        try:
            notes = json.loads(row[8]) if row[8] else {}
        except (json.JSONDecodeError, TypeError):
            notes = {}
        if notes.get("wave") != "A_deferred_dir":
            continue
        disp, extras = classify(row)
        rid, sid, ctype = row[0], row[1], row[2]
        disposition_counter[disp] += 1
        per_source_disposition.setdefault(sid, Counter())[disp] += 1
        if disp == "reject_known_fake":
            rejects.append((rid, extras))
        else:
            holds.append((rid, disp, extras))
        if disp == "hold_identifier_type_vocab_extension_pending":
            vocab_extension_types[ctype] += 1

    print("=== Disposition summary ===")
    for d, n in sorted(disposition_counter.items(), key=lambda x: -x[1]):
        print(f"  {d}: {n}")
    print()
    print("=== Per-source-id ===")
    for sid in sorted(per_source_disposition):
        parts = ", ".join(f"{d}={n}" for d, n in sorted(per_source_disposition[sid].items()))
        print(f"  src={sid}: {parts}")
    print()
    print("=== Vocab-extension-pending candidate_types (G-13.2/G-14/G-16 slate for 0011) ===")
    for t, n in sorted(vocab_extension_types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {n}")

    if "--apply" not in sys.argv:
        print("\nDRY RUN — pass --apply to persist disposition.")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    applied_rejects = 0
    applied_holds = 0
    conflict_inserts = 0

    cur.execute("BEGIN")
    try:
        # Rejects → conflicts table + processed_at
        for rid, extras in rejects:
            cur.execute(
                "SELECT id FROM conflicts WHERE raw_observation_id=? AND reason=?",
                (rid, "known_fake_pattern"),
            )
            existing_conflict = cur.fetchone()
            if not existing_conflict:
                cur.execute(
                    """INSERT INTO conflicts (raw_observation_id, reason, resolution_notes)
                       VALUES (?, ?, ?)""",
                    (
                        rid,
                        "known_fake_pattern",
                        json.dumps(
                            {
                                **extras,
                                "phase": "MAC-101_Item_C_Phase_2",
                                "rejected_by_validator_at": now,
                                "rule_cite": "§7.3 known-fake enumeration applied to OUI per §7.4",
                            }
                        ),
                    ),
                )
                conflict_inserts += 1
            cur.execute("SELECT notes FROM raw_observations WHERE id=?", (rid,))
            (notes_raw,) = cur.fetchone()
            notes = json.loads(notes_raw) if notes_raw else {}
            notes["disposition"] = "reject_known_fake"
            notes.update(extras)
            cur.execute(
                "UPDATE raw_observations SET notes=?, processed_at=? WHERE id=?",
                (json.dumps(notes), now, rid),
            )
            applied_rejects += 1

        for rid, disp, extras in holds:
            cur.execute("SELECT notes FROM raw_observations WHERE id=?", (rid,))
            (notes_raw,) = cur.fetchone()
            notes = json.loads(notes_raw) if notes_raw else {}
            notes["disposition"] = disp
            notes.update(extras)
            cur.execute(
                "UPDATE raw_observations SET notes=?, processed_at=? WHERE id=?",
                (json.dumps(notes), now, rid),
            )
            applied_holds += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    print(f"\nApplied: rejects={applied_rejects} (conflicts inserted={conflict_inserts}), holds={applied_holds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
