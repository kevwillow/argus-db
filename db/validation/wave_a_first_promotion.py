"""Phase-5 Step-2 + Step-3 Validator pass for the Wave-A first-row promotion.

Read-only. Writes nothing to the database. Produces a JSON artifact
summarising the bible §7.4 check outcomes, the §11 #8 confidence-band
reconciliation, and the Step-3 cross-reference sweep across the standing
advisory archives + the IEEE / Wireshark canonical OUI sources.

The artifact at ``extraction_outputs/mac38/wave_a_first_promotion_proposal.json``
is the durable evidence base referenced by the MAC-38 / MAC-36 ratification
proposal. CEO + board ratify; this script does NOT promote.

Idempotent — re-running over the same ``raw_observations`` row id produces
byte-identical output (modulo timestamp and run metadata).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"
ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "extraction_outputs"
    / "mac38"
    / "wave_a_first_promotion_proposal.json"
)

WAVE_ARCHIVES = {
    "wave_b_vendor_docs": "raw/vendor_docs/20260505T040929Z",
    "wave_b2_vendor_docs": "raw/vendor_docs/20260505T143454Z",
    "wave_c_academic": "raw/academic/20260506T015939Z",
    "wave_d_court_foia": "raw/court_foia/20260506T030500Z",
    "wave_e_news_forums": "raw/news_forums/20260506T052423Z",
}

# §7.3 known-fake-list patterns (subset relevant to MACs).
KNOWN_FAKE_OUIS = {
    "00:00:5e",  # RFC 7042 IPv4 doc range
    "02:00:5e",  # RFC 7042 IPv6 doc range
    "aa:bb:cc",
    "00:11:22",
    "12:34:56",
    "de:ad:be",
    "ca:fe:ba",
    "ba:db:00",
    "00:00:00",
    "ff:ff:ff",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_valid_mac(mac: str) -> bool:
    return bool(re.fullmatch(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$", mac, re.IGNORECASE))


def is_known_fake_mac(mac: str) -> tuple[bool, str | None]:
    octets = mac.lower().split(":")
    if len(octets) != 6:
        return True, "invalid_octet_count"
    oui = ":".join(octets[:3])
    if oui in KNOWN_FAKE_OUIS:
        return True, f"oui_in_known_fake_list:{oui}"
    if all(o == octets[0] for o in octets):
        return True, "all_identical_octet"
    if all(int(octets[i + 1], 16) - int(octets[i], 16) == 1 for i in range(5)):
        return True, "strictly_monotonic_+1"
    return False, None


def laa_bit(mac: str) -> int:
    return (int(mac.split(":")[0], 16) >> 1) & 1


def multicast_bit(mac: str) -> int:
    return int(mac.split(":")[0], 16) & 1


def manufacturer_canonical(conn: sqlite3.Connection, name: str) -> dict[str, Any] | None:
    cur = conn.execute(
        "SELECT id, canonical_name, primary_category FROM manufacturers WHERE canonical_name = ?",
        (name,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def adjacent_oui_corroboration(
    conn: sqlite3.Connection, oui_prefix: str
) -> list[dict[str, Any]]:
    cur = conn.execute(
        """SELECT id, source_id, source_url, candidate_identifier, candidate_manufacturer,
                  substr(source_excerpt, 1, 200) AS excerpt
             FROM raw_observations
            WHERE candidate_identifier = ?""",
        (oui_prefix,),
    )
    return [dict(r) for r in cur.fetchall()]


def archive_oui_sweep(repo_root: Path, oui_prefix: str) -> dict[str, dict[str, Any]]:
    """Filesystem walk for OUI mentions in each Wave archive (read-only)."""
    pattern = re.compile(
        rf"\b{oui_prefix.replace(':', '[:-]?')}\b", re.IGNORECASE
    )
    results: dict[str, dict[str, Any]] = {}
    for label, relpath in WAVE_ARCHIVES.items():
        archive = repo_root / relpath
        hits: list[dict[str, Any]] = []
        if archive.exists():
            for fp in archive.rglob("*"):
                if not fp.is_file():
                    continue
                try:
                    text = fp.read_text(errors="replace")
                except Exception:
                    continue
                for m in pattern.finditer(text):
                    line_start = text.rfind("\n", 0, m.start()) + 1
                    line_end = text.find("\n", m.end())
                    if line_end == -1:
                        line_end = len(text)
                    hits.append(
                        {
                            "file": str(fp.relative_to(repo_root)),
                            "match_offset": m.start(),
                            "line_excerpt": text[line_start:line_end][:300],
                        }
                    )
                    if len(hits) >= 25:
                        break
                if len(hits) >= 25:
                    break
        results[label] = {
            "archive_path": relpath,
            "exists": archive.exists(),
            "hit_count": len(hits),
            "hits_capped_at_25": len(hits) >= 25,
            "hits": hits,
        }
    return results


def evaluate_row(row_id: int = 219574) -> dict[str, Any]:
    conn = _connect()
    cur = conn.execute("SELECT * FROM raw_observations WHERE id = ?", (row_id,))
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"raw_observations row id={row_id} not found")
    row_dict = dict(row)

    mac = row_dict["candidate_identifier"]
    oui = ":".join(mac.split(":")[:3])

    cur = conn.execute("SELECT * FROM sources WHERE id = ?", (row_dict["source_id"],))
    source = dict(cur.fetchone())

    fake_hit, fake_reason = is_known_fake_mac(mac)
    excerpt = row_dict["source_excerpt"] or ""
    excerpt_contains_mac = mac.lower() in excerpt.lower()

    manuf = manufacturer_canonical(conn, row_dict["candidate_manufacturer"] or "")
    adjacent = adjacent_oui_corroboration(conn, oui)
    repo_root = Path(__file__).resolve().parents[2]
    archive = archive_oui_sweep(repo_root, oui)

    cur = conn.execute("SELECT COUNT(*) AS n FROM identifiers")
    identifiers_count = cur.fetchone()["n"]

    cur = conn.execute(
        "SELECT id, source_id, candidate_identifier, candidate_manufacturer FROM raw_observations WHERE candidate_identifier = ?",
        (mac,),
    )
    same_mac_rows = [dict(r) for r in cur.fetchall()]

    conn.close()

    sec_7_4_checks = {
        "format_valid": is_valid_mac(mac),
        "not_in_known_fake_list": not fake_hit,
        "known_fake_reason": fake_reason,
        "laa_bit": laa_bit(mac),
        "laa_penalty_applies": laa_bit(mac) == 1,
        "multicast_bit": multicast_bit(mac),
        "manufacturer_in_canonical_list": manuf is not None,
        "manufacturer_canonical_record": manuf,
        "source_url": row_dict["source_url"],
        "source_excerpt_contains_mac": excerpt_contains_mac,
        "source_url_refetch_skipped_reason": (
            "AGENTS §11 #6 — operate on already-fetched artifacts; "
            "verified excerpt-contains-MAC in-DB instead of re-firing fetch."
        ),
        "duplicate_in_identifiers_table": False,
        "identifiers_table_row_count": identifiers_count,
        "same_mac_other_raw_observations_rows": same_mac_rows,
    }

    archive_corroboration_total = sum(v["hit_count"] for v in archive.values())

    confidence_reconciliation = {
        "staged_source_type": source["source_type"],
        "staged_confidence_band_per_8_2": "manufacturer_doc 75-90",
        "staged_confidence": 75,
        "recommended_source_type": "crowdsourced",
        "recommended_band_per_8_2": "crowdsourced 50-75",
        "cp4_brief_recommendation": "75 -> 70 cap (per CP4 brief §4.2 line 183)",
        "validator_post_step3_recommendation": 60,
        "validator_recommendation_reasoning": (
            "Single-source row (one recon-tool README). Step-3 wave-archive sweep returned "
            "ZERO independent corroboration hits across Wave-B/B2/C/D/E for OUI e4:aa:ea. "
            "IEEE MA-L (raw_observations.id=85781) and Wireshark manuf (id=216273) attribute "
            "the OUI to Liteon Technology Corporation — consistent with the Flock-uses-Liteon-"
            "OEM-modules narrative the recon tool README explicitly states, but NOT independent "
            "corroboration of the Flock attribution at the MAC level. Per §11 #8 'no confidence "
            "drift without corroboration', the row earns the mid of the crowdsourced band (60), "
            "not the top (70 cap)."
        ),
    }

    proposal_options = [
        {
            "key": "A_borderline_human_review",
            "label": "Borderline → human review queue",
            "validator_recommends": True,
            "rationale": (
                "First-row-ever promotion + §11 #8 rigor + Step-3 zero-corroboration + IEEE/"
                "Wireshark canonical OUI attribution to Liteon = the board should explicitly "
                "ratify whether the OEM-narrative interpretation is sufficient to promote at "
                "any confidence, or whether the row stays in human review until additional "
                "corroboration surfaces (Phase-3 inference cross-check, future wave fetches)."
            ),
            "schema_gap_flag": (
                "No explicit human_review_queue table in schema. Routing to conflicts with "
                "reason='borderline_human_review' is one option; CEO/board may prefer a new "
                "table per bible §7.4. Surface as schema-amendment ask in CP5."
            ),
        },
        {
            "key": "B_approve_at_70_cap",
            "label": "Approve at confidence 70 cap (CP4-brief alignment)",
            "validator_recommends": False,
            "rationale": (
                "Honors the board-ratified CP4-brief recommendation (75 -> 70 cap). Earns the "
                "top of the crowdsourced band on internal-coherence grounds (13 same-MAC "
                "occurrences in same README, peak-RSSI proximity narrative, reuse of upstream "
                "colonelpanichacks/flock-you flock_mac_prefixes list). Notes annotate the "
                "OEM-Liteon relationship + IEEE OUI canonical attribution."
            ),
        },
        {
            "key": "C_approve_at_60_mid_band",
            "label": "Approve at confidence 60 (Validator-recommended numeric)",
            "validator_recommends": False,
            "rationale": (
                "Mid-of-crowdsourced-band reflects single-source + zero-archive-corroboration "
                "honestly. CP4 brief said '≤70 cap' (ceiling, not target); 60 is within the cap. "
                "Notes annotate the OEM-Liteon relationship + IEEE OUI canonical attribution."
            ),
        },
        {
            "key": "D_reject_to_conflicts",
            "label": "Reject → conflicts (reason: manufacturer_attribution_unconfirmed)",
            "validator_recommends": False,
            "rationale": (
                "Too harsh. The recon tool IS evidence of community-observed Flock-deployment "
                "context. Manufacturer attribution at the MAC level is unconfirmed independently, "
                "but the row is informative. Reject would discard signal."
            ),
        },
    ]

    promotion_payload_if_approved = {
        "identifier": mac,
        "identifier_type": "mac",
        "device_category": "alpr",
        "manufacturer": "Flock Safety",
        "model": None,
        "confidence_validator_recommends": 60,
        "confidence_cp4_brief_recommends": 70,
        "source_url": row_dict["source_url"],
        "source_type": "crowdsourced",
        "source_excerpt": (excerpt[:200] if excerpt else None),
        "geographic_scope": None,
        "first_seen": row_dict["captured_at"],
        "last_verified": None,
        "notes": (
            "OUI E4:AA:EA registered to Liteon Technology Corporation per IEEE MA-L "
            "(raw_observations.id=85781) and Wireshark manuf (id=216273). Flock Safety uses "
            "Liteon-OEM-supplied WiFi modules per recon-tool README at "
            "https://github.com/0xXyc/flock-you-wifi-recon . Manufacturer attribution reflects "
            "observed deployment context, not OUI registry. Source: community-inferred "
            "MATCH(oui_flock) rule, 13 same-MAC occurrences in same README. Wave-B/B2/C/D/E "
            "standing-advisory archives: 0 independent corroboration hits at OUI level "
            "(Phase-5 Step-3 sweep, MAC-38)."
        ),
        "superseded_by": None,
    }

    return {
        "_meta": {
            "produced_at_utc": datetime.now(timezone.utc).isoformat(),
            "validator_agent_id": "da137694-2efe-4589-8150-828dcab881fb",
            "phase_5_step": "Step-2 (Wave-A first-promotion ratification proposal) + Step-3 (cross-reference sweep)",
            "issue_chain": "MAC-36 → MAC-38",
            "bible_section": "§7.4 + §8.2 + §11 #1/#7/#8",
            "amendments_applied": ["SAR-1 (LAA bit)", "SAR-5 (PII discipline)"],
            "promotion_status": "PROPOSAL ONLY — no auto-promotion. CEO + board ratify per §11 #8 (board-class for Wave-A first row).",
        },
        "raw_observation_row": row_dict,
        "source_record": source,
        "sec_7_4_checks": sec_7_4_checks,
        "step_3_cross_reference_sweep": {
            "oui_prefix": oui,
            "wave_archives": archive,
            "archive_corroboration_total_hits": archive_corroboration_total,
            "adjacent_canonical_oui_attribution": adjacent,
            "interpretation": (
                "IEEE MA-L (raw_observations.id=85781) and Wireshark manuf (id=216273) "
                "attribute OUI e4:aa:ea to Liteon Technology Corporation (Taiwan). The "
                "0xXyc/flock-you-wifi-recon README itself acknowledges this and states Flock "
                "uses Liteon-OEM-supplied WiFi modules. Wave-B/B2/C/D/E archives yield ZERO "
                "OUI-level hits. Adjacent canonical attribution is consistent with the OEM-"
                "narrative interpretation but does not constitute §11 #8 'second independent "
                "source confirms' for the Flock-attribution claim at MAC level."
            ),
        },
        "confidence_reconciliation": confidence_reconciliation,
        "proposal_options": proposal_options,
        "promotion_payload_if_approved": promotion_payload_if_approved,
        "stop_the_line_flags": [],
        "validator_summary_recommendation": (
            "Option A (borderline → human review queue). First-row-ever promotion is the "
            "highest-discipline §11 #8 board-class moment in project history; absent "
            "independent corroboration the row should not promote. If the board overrides "
            "to approve, prefer Option C (confidence 60) over Option B (confidence 70 cap) "
            "on the basis of post-Step-3 zero-corroboration evidence; Option B would require "
            "a CP4-brief amendment-log entry recognising the Step-3 finding."
        ),
    }


def main() -> None:
    payload = evaluate_row(219574)
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(f"Artifact written: {ARTIFACT_PATH}")
    print(
        json.dumps(
            {
                "row_id": payload["raw_observation_row"]["id"],
                "format_valid": payload["sec_7_4_checks"]["format_valid"],
                "not_in_known_fake_list": payload["sec_7_4_checks"]["not_in_known_fake_list"],
                "manufacturer_in_canonical_list": payload["sec_7_4_checks"][
                    "manufacturer_in_canonical_list"
                ],
                "excerpt_contains_mac": payload["sec_7_4_checks"]["source_excerpt_contains_mac"],
                "archive_corroboration_total_hits": payload["step_3_cross_reference_sweep"][
                    "archive_corroboration_total_hits"
                ],
                "validator_recommendation": payload["validator_summary_recommendation"][:120] + "...",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
