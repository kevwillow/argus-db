"""Phase-5 Step-4 follow-on (MAC-41) bulk-stage executor.

Reads the SAR-8-wired ``extraction_outputs/mac39/phase3_inference_candidates.json``
artifact and bulk-stages every strict-clean accept row into ``identifiers`` at
``device_category='unknown'`` (strict-§8.4 binding) under
``source_type='inferred'``. Confidence per §8.2 inferred band (baseline 50,
−10 LAA-bit penalty per SAR-1).

Idempotent — guards on ``raw_observations.promoted_identifier_id IS NULL`` per
the wave_a_promote.py pattern. Re-running yields zero new ``identifiers`` rows
on the second pass.

§11 attestations applied at insert time:
- #1 no fabrication — every staged row anchored to a real raw_observations.id.
- #6 no live fetches — operates on already-staged data.
- #7 provenance — source_url + source_excerpt carry verbatim.
- #8 no confidence drift — single-source ``inferred`` band; no uplift.
- #12 Pi self-exclude — guards against b8:27:eb / dc:a6:32 / e4:5f:01 /
  28:cd:c1 OUI prefixes.
- #13 unknown-category Talos ban — pre-flagged at staging via
  device_category='unknown'.
- #14 procurement-only Talos ban — N/A here (this script stages
  source_type='inferred' rows from Phase-2 OUI/MAC-range observations only).

Authority chain:
- Bible §5 Tier 4 (inferential records).
- Bible §6 Phase 5 (Phase-5 contract).
- Bible §7.4 (Validator contract).
- Bible §8.2 (`inferred` 30–70 capped).
- Bible §8.4 (multi-purpose / OUI-only-→-unknown / Pi self-exclude).
- Bible §11 #1/#6/#7/#8/#12/#13/#14.
- BIBLE_AMENDMENTS.md SAR-1 (LAA penalty), SAR-7 (CVE/DJI-Djibouti/news-FP),
  SAR-8 (vendor-name-disambig).
- MAC-41 dispatch.
- Board ratification at MAC-1 ``613ec532`` 2026-05-06T17:08:16Z (option (a)+(c);
  strict-§8.4 binding; flag-for-review separate artifact).
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db.extraction.vendor_name_disambig import vendor_match_disposition

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"
ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "extraction_outputs"
    / "mac39"
    / "phase3_inference_candidates.json"
)
DELIVERABLE_PATH = (
    Path(__file__).resolve().parents[2]
    / "extraction_outputs"
    / "mac41"
    / "sar8_bulk_stage_deliverable.json"
)

VALIDATOR_AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"
RATIFIED_BY_BOARD_APPROVAL_COMMENT = (
    "MAC-1 [`613ec532`](/MAC/issues/MAC-1#comment-613ec532-d8cb-4f0f-a35b-c811e2864d7d)"
)
RATIFIED_AT_UTC = "2026-05-06T17:08:16Z"

# §11 #12 Pi self-exclude OUI list (Raspberry Pi hardware running Talos).
PI_SELF_EXCLUDE_OUIS = frozenset({
    "b8:27:eb",
    "dc:a6:32",
    "e4:5f:01",
    "28:cd:c1",
})

# §7.3 known-fake-list — enforced at staging-time as a belt-and-suspenders
# guard even though the SAR-8 sweep already filters these out upstream.
KNOWN_FAKE_OUIS = frozenset({
    "00:00:5e", "02:00:5e", "aa:bb:cc", "00:11:22", "12:34:56",
    "de:ad:be", "ca:fe:ba", "ba:db:00", "00:00:00", "ff:ff:ff",
})

WAVE_A_OUI = "e4:aa:ea"
WAVE_A_MAC = "e4:aa:ea:80:a1:9b"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _laa_bit(first_octet_hex: str) -> int:
    """Bit 1 of first octet — 1 ⇒ locally-administered (SAR-1 penalty)."""
    if not re.fullmatch(r"[0-9a-f]{2}", first_octet_hex.lower()):
        return 0
    return (int(first_octet_hex, 16) >> 1) & 1


def _is_pi_self_exclude(oui_prefix: str) -> bool:
    return oui_prefix.lower()[:8] in PI_SELF_EXCLUDE_OUIS


def _is_known_fake_oui(oui_prefix: str) -> tuple[bool, str | None]:
    if not oui_prefix or len(oui_prefix) < 8:
        return False, None
    p = oui_prefix.lower()[:8]
    if p in KNOWN_FAKE_OUIS:
        return True, f"oui_in_known_fake_list:{p}"
    octets = p.split(":")[:3]
    if len(octets) == 3 and all(o == octets[0] for o in octets):
        return True, "all_identical_octet"
    return False, None


def _build_lexicon(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT canonical_name, aliases, primary_category FROM manufacturers"
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        cn = r["canonical_name"]
        alias_strings = [cn] + [
            a.strip() for a in (r["aliases"] or "").split(",") if a.strip()
        ]
        out.append(
            {
                "canonical_name": cn,
                "primary_category": r["primary_category"],
                "alias_strings": alias_strings,
            }
        )
    return out


def _classify(
    candidate_manufacturer: str, lexicon: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Return SAR-8 accept hit or None."""
    for entry in lexicon:
        cn = entry["canonical_name"]
        for alias in entry["alias_strings"]:
            if vendor_match_disposition(candidate_manufacturer, alias) == "accept":
                return {
                    "canonical_name": cn,
                    "primary_category": entry["primary_category"],
                    "alias_used": alias,
                }
    return None


def _compute_confidence(oui_prefix: str) -> tuple[int, list[str]]:
    """§8.2 inferred 30–70 baseline 50; SAR-1 -10 if LAA bit set."""
    flags: list[str] = []
    confidence = 50
    octets = oui_prefix.lower().split(":")
    if octets and re.fullmatch(r"[0-9a-f]{2}", octets[0]):
        if _laa_bit(octets[0]) == 1:
            flags.append("SAR-1_laa_bit_set")
            confidence -= 10
    return confidence, flags


def _make_notes(
    raw_obs_id: int,
    candidate_manufacturer_raw: str,
    matched_alias: str,
    sar8_disposition: str,
    flags: list[str],
) -> str:
    flag_str = "+".join(flags) if flags else "none"
    return (
        f"Phase-5 Step-4 follow-on (MAC-41). raw_observations.id={raw_obs_id}. "
        f"SAR-8 disposition={sar8_disposition} via alias={matched_alias!r}. "
        f"candidate_manufacturer (raw)={candidate_manufacturer_raw!r}. "
        f"§8.2 inferred 30–70; baseline 50; adjustments={flag_str}. "
        f"§8.4 strict — device_category='unknown' for OUI-level inference. "
        f"§11 #13 — Talos-export-banned at staging. "
        f"Board ratification {RATIFIED_BY_BOARD_APPROVAL_COMMENT} {RATIFIED_AT_UTC}."
    )


def _make_excerpt(
    candidate_identifier: str, candidate_manufacturer_raw: str, alias: str
) -> str:
    """≤200-char source_excerpt per the identifiers schema CHECK."""
    excerpt = (
        f"OUI {candidate_identifier} attributed to {candidate_manufacturer_raw} "
        f"(SAR-8 alias→{alias})."
    )
    if len(excerpt) > 200:
        excerpt = excerpt[:197] + "..."
    return excerpt


def _stage_one_row(
    conn: sqlite3.Connection,
    raw_obs: sqlite3.Row,
    hit: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    oui_prefix = ":".join(raw_obs["candidate_identifier"].split(":")[:3]).lower()

    fake_hit, fake_reason = _is_known_fake_oui(oui_prefix)
    if fake_hit:
        return {"status": "skipped_known_fake", "reason": fake_reason}
    if _is_pi_self_exclude(oui_prefix):
        return {"status": "skipped_pi_self_exclude"}

    # Idempotency: skip if this raw_observation already promoted.
    if raw_obs["promoted_identifier_id"] is not None:
        return {
            "status": "skipped_already_promoted",
            "existing_identifier_id": raw_obs["promoted_identifier_id"],
        }

    confidence, flags = _compute_confidence(oui_prefix)
    notes = _make_notes(
        raw_obs["id"],
        raw_obs["candidate_manufacturer"],
        hit["alias_used"],
        "accept",
        flags,
    )
    excerpt = (
        raw_obs["source_excerpt"]
        if raw_obs["source_excerpt"]
        else _make_excerpt(
            raw_obs["candidate_identifier"],
            raw_obs["candidate_manufacturer"],
            hit["alias_used"],
        )
    )

    payload = {
        "identifier": raw_obs["candidate_identifier"],
        "identifier_type": raw_obs["candidate_type"],
        "device_category": "unknown",  # strict §8.4
        "manufacturer": hit["canonical_name"],
        "model": None,
        "confidence": confidence,
        "source_url": raw_obs["source_url"],
        "source_type": "inferred",
        "source_excerpt": excerpt,
        "geographic_scope": None,
        "first_seen": None,
        "last_verified": None,
        "notes": notes,
        "superseded_by": None,
    }

    if dry_run:
        return {
            "status": "dry_run_would_insert",
            "payload": payload,
            "raw_obs_id": raw_obs["id"],
            "flags": flags,
        }

    cur = conn.execute(
        """INSERT INTO identifiers
             (identifier, identifier_type, device_category, manufacturer, model,
              confidence, source_url, source_type, source_excerpt,
              geographic_scope, first_seen, last_verified, notes, superseded_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            payload["identifier"],
            payload["identifier_type"],
            payload["device_category"],
            payload["manufacturer"],
            payload["model"],
            payload["confidence"],
            payload["source_url"],
            payload["source_type"],
            payload["source_excerpt"],
            payload["geographic_scope"],
            payload["first_seen"],
            payload["last_verified"],
            payload["notes"],
            payload["superseded_by"],
        ),
    )
    identifier_id = cur.lastrowid

    conn.execute(
        "UPDATE raw_observations SET promoted_identifier_id = ?, "
        "processed_at = CURRENT_TIMESTAMP "
        "WHERE id = ? AND promoted_identifier_id IS NULL",
        (identifier_id, raw_obs["id"]),
    )

    return {
        "status": "inserted",
        "identifier_id": identifier_id,
        "raw_obs_id": raw_obs["id"],
        "manufacturer": payload["manufacturer"],
        "confidence": confidence,
        "flags": flags,
    }


def bulk_stage(*, dry_run: bool = False) -> dict[str, Any]:
    conn = _connect()
    try:
        lexicon = _build_lexicon(conn)

        # Re-derive accept set from raw_observations under SAR-8 (don't trust
        # the JSON artifact's row list — derive from DB so we stay idempotent
        # against intermediate DB state).
        cur = conn.execute(
            """SELECT id, source_id, source_url, candidate_identifier,
                      candidate_type, candidate_manufacturer, source_excerpt,
                      promoted_identifier_id
                 FROM raw_observations
                WHERE candidate_type IN ('oui','mac_range')
                  AND candidate_manufacturer IS NOT NULL"""
        )
        raw_rows = cur.fetchall()

        result_rows: list[dict[str, Any]] = []
        per_status: dict[str, int] = {}
        per_vendor: dict[str, int] = {}
        wave_a_collisions: list[int] = []
        ledger_run_id: int | None = None

        ledger_started_at = datetime.now(timezone.utc).isoformat()

        for raw in raw_rows:
            hit = _classify(raw["candidate_manufacturer"], lexicon)
            if hit is None:
                continue
            # Wave-A OUI collision halt-the-line.
            if (
                raw["candidate_identifier"]
                .lower()
                .startswith(WAVE_A_OUI)
            ):
                wave_a_collisions.append(raw["id"])
                continue

            staged = _stage_one_row(conn, raw, hit, dry_run=dry_run)
            staged["sar8_alias_used"] = hit["alias_used"]
            staged["matched_canonical_name"] = hit["canonical_name"]
            result_rows.append(staged)
            per_status[staged["status"]] = per_status.get(staged["status"], 0) + 1
            if staged["status"] in ("inserted", "dry_run_would_insert"):
                cn = hit["canonical_name"]
                per_vendor[cn] = per_vendor.get(cn, 0) + 1

        # Write a single extraction_runs ledger row for the pass.
        post_count = conn.execute(
            "SELECT COUNT(*) AS n FROM identifiers"
        ).fetchone()["n"]
        if not dry_run and (
            per_status.get("inserted", 0) > 0
            or per_status.get("skipped_already_promoted", 0) > 0
        ):
            cur = conn.execute(
                """INSERT INTO extraction_runs
                     (agent_id, source_id, started_at, finished_at,
                      records_in, records_out, errors, status, notes)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)""",
                (
                    VALIDATOR_AGENT_ID,
                    None,
                    ledger_started_at,
                    len(raw_rows),
                    per_status.get("inserted", 0),
                    0,
                    "ok",
                    (
                        f"MAC-41 SAR-8 bulk-stage: "
                        f"inserted={per_status.get('inserted', 0)}, "
                        f"skipped_already_promoted={per_status.get('skipped_already_promoted', 0)}, "
                        f"skipped_pi_self_exclude={per_status.get('skipped_pi_self_exclude', 0)}, "
                        f"skipped_known_fake={per_status.get('skipped_known_fake', 0)}, "
                        f"wave_a_collisions={len(wave_a_collisions)}. "
                        f"Board ratification {RATIFIED_BY_BOARD_APPROVAL_COMMENT} "
                        f"{RATIFIED_AT_UTC}. §11 attestations: #1 #6 #7 #8 #12 #13 #14."
                    ),
                ),
            )
            ledger_run_id = cur.lastrowid

        if not dry_run:
            conn.commit()

        return {
            "_meta": {
                "produced_at_utc": datetime.now(timezone.utc).isoformat(),
                "validator_agent_id": VALIDATOR_AGENT_ID,
                "phase_5_step": "Step-4 follow-on (MAC-41) — SAR-8 bulk-stage",
                "issue_chain": "MAC-36 → MAC-39 → MAC-41",
                "amendments_applied": [
                    "SAR-1 (LAA-bit penalty)",
                    "SAR-7 #1/#2/#3 (codified upstream; not invoked here)",
                    "SAR-8 (vendor-name-disambig + alias allowlist + geo-prefix)",
                ],
                "board_ratification_comment": RATIFIED_BY_BOARD_APPROVAL_COMMENT,
                "board_ratification_at_utc": RATIFIED_AT_UTC,
                "dry_run": dry_run,
                "ledger_run_id": ledger_run_id,
                "promotion_class": "Validator-execution under board ratification",
            },
            "summary": {
                "raw_observations_evaluated": len(raw_rows),
                "sar8_accept_total": sum(
                    per_status.get(k, 0)
                    for k in ("inserted", "dry_run_would_insert", "skipped_already_promoted")
                ),
                "inserted": per_status.get("inserted", 0),
                "dry_run_would_insert": per_status.get("dry_run_would_insert", 0),
                "skipped_already_promoted": per_status.get(
                    "skipped_already_promoted", 0
                ),
                "skipped_pi_self_exclude": per_status.get(
                    "skipped_pi_self_exclude", 0
                ),
                "skipped_known_fake": per_status.get("skipped_known_fake", 0),
                "wave_a_oui_collisions_halted": len(wave_a_collisions),
                "identifiers_table_post_count": post_count,
                "per_vendor_distribution": dict(
                    sorted(per_vendor.items(), key=lambda x: -x[1])
                ),
            },
            "section_11_attestations": {
                "#1_no_fabrication": (
                    "Every staged row anchored to a real raw_observations.id; "
                    "no synthetic identifiers."
                ),
                "#6_no_live_fetches": (
                    "Operates on already-staged Phase-2 raw_observations only."
                ),
                "#7_provenance": (
                    "source_url + source_excerpt carried verbatim per row "
                    "(or computed-excerpt if raw row had none)."
                ),
                "#8_no_confidence_drift": (
                    "Single-source 'inferred' band per §8.2 (baseline 50, "
                    "−10 LAA-bit penalty per SAR-1). No uplift at this step."
                ),
                "#12_pi_self_exclude": (
                    f"Pi OUIs ({sorted(PI_SELF_EXCLUDE_OUIS)}) skipped at "
                    f"staging-time guard."
                ),
                "#13_unknown_category_talos_ban": (
                    "device_category='unknown' for ALL staged rows — pre-flagged "
                    "Talos-export-banned at staging time. Reconciled at Step-6 "
                    "export design via dropped_in_export.unknown_category tally."
                ),
                "#14_procurement_only_talos_ban": (
                    "N/A — this script stages source_type='inferred' from "
                    "Phase-2 OUI/MAC-range raw_observations only, not "
                    "procurement records."
                ),
                "wave_a_collision_halt_line": (
                    f"{len(wave_a_collisions)} candidates at OUI {WAVE_A_OUI} "
                    f"halted-not-staged (Wave-A canonical row stays "
                    f"identifiers.id=1 at MAC-level {WAVE_A_MAC})."
                ),
            },
        }
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be staged without writing.",
    )
    args = parser.parse_args(argv)
    result = bulk_stage(dry_run=args.dry_run)
    DELIVERABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DELIVERABLE_PATH.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(f"Deliverable artifact written: {DELIVERABLE_PATH}")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
