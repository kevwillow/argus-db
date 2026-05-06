"""Phase-5 Step-2 promotion executor for the Wave-A first row.

Loads ``extraction_outputs/mac38/wave_a_first_promotion_proposal.json``,
promotes ``raw_observations.id=219574`` (Flock Safety MAC ``e4:aa:ea:80:a1:9b``)
into ``identifiers`` at the board-ratified confidence (Option C, conf=60), and
writes an ``extraction_runs`` ledger row citing approval
``51bc6182-9ffe-40cb-ab79-10ff028927e2``.

Idempotent — guards on ``(identifier, identifier_type)`` and on
``raw_observations.promoted_identifier_id IS NULL``. Re-running yields
``status="skipped_already_present"`` and zero new rows.

Authority chain:
- Bible §6 Phase 5 + §7.4 (Validator promotion contract).
- §11 #7 (provenance preserved in identifiers.notes + source_url + source_excerpt).
- §11 #8 (no autonomous promotion; this script is a dispatch executor under
  board approval ``51bc6182``).
- §11 #14 (source_type stays ``crowdsourced`` per CP4 brief §4.2).
- CP4 brief §4.3 (Wave-A first row = board-class moment).
- MAC-38 dispatch comment 2026-05-06T14:55:52Z.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"
PROPOSAL_PATH = (
    Path(__file__).resolve().parents[2]
    / "extraction_outputs"
    / "mac38"
    / "wave_a_first_promotion_proposal.json"
)

VALIDATOR_AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"
APPROVAL_ID = "51bc6182-9ffe-40cb-ab79-10ff028927e2"
APPROVAL_TIMESTAMP = "2026-05-06T14:54:46Z"
RATIFIED_CONFIDENCE = 60  # Option C, board-ratified
RAW_OBS_ROW_ID = 219574


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _build_promotion_row(proposal: dict[str, Any]) -> dict[str, Any]:
    payload = proposal["promotion_payload_if_approved"]
    return {
        "identifier": payload["identifier"],
        "identifier_type": payload["identifier_type"],
        "device_category": payload["device_category"],
        "manufacturer": payload["manufacturer"],
        "model": payload["model"],
        "confidence": RATIFIED_CONFIDENCE,
        "source_url": payload["source_url"],
        "source_type": payload["source_type"],
        "source_excerpt": payload["source_excerpt"],
        "geographic_scope": payload["geographic_scope"],
        "first_seen": payload["first_seen"],
        "last_verified": None,
        "notes": payload["notes"],
        "superseded_by": payload["superseded_by"],
    }


def _ledger_notes(identifier_id: int) -> str:
    return (
        f"Phase-5 Step-2 Wave-A first-promotion (MAC-38). "
        f"Board-ratified Option C confidence={RATIFIED_CONFIDENCE} via approval "
        f"{APPROVAL_ID} ({APPROVAL_TIMESTAMP}). "
        f"Promoted identifiers.id={identifier_id} from raw_observations.id={RAW_OBS_ROW_ID}. "
        f"Step-3 cross-reference sweep (MAC-38 commit 8850ca6) returned ZERO "
        f"corroboration hits across Wave-B/B2/C/D/E for OUI e4:aa:ea; IEEE MA-L "
        f"(raw_observations.id=85781) + Wireshark manuf (id=216273) attribute the "
        f"OUI to Liteon Technology Corporation, consistent with the OEM-narrative "
        f"interpretation but not §11 #8 second-independent-source corroboration. "
        f"Provenance carried per §11 #7. source_type='crowdsourced' per §11 #14 + "
        f"CP4 brief §4.2."
    )


def promote(dry_run: bool = False) -> dict[str, Any]:
    """Insert the Wave-A first row into ``identifiers`` (idempotent).

    Returns a result dict with ``status`` ∈
    {``inserted``, ``skipped_already_present``, ``dry_run_would_insert``},
    plus identifier id + ledger run id when applicable.
    """
    proposal = json.loads(PROPOSAL_PATH.read_text())
    promo = _build_promotion_row(proposal)

    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT id, confidence, source_type FROM identifiers "
            "WHERE identifier = ? AND identifier_type = ?",
            (promo["identifier"], promo["identifier_type"]),
        )
        existing = cur.fetchone()
        if existing is not None:
            return {
                "status": "skipped_already_present",
                "identifier_id": existing["id"],
                "confidence": existing["confidence"],
                "source_type": existing["source_type"],
                "approval_id": APPROVAL_ID,
            }

        if dry_run:
            return {
                "status": "dry_run_would_insert",
                "promotion_row": promo,
                "approval_id": APPROVAL_ID,
            }

        cur = conn.execute(
            """INSERT INTO identifiers
                 (identifier, identifier_type, device_category, manufacturer, model,
                  confidence, source_url, source_type, source_excerpt,
                  geographic_scope, first_seen, last_verified, notes, superseded_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                promo["identifier"],
                promo["identifier_type"],
                promo["device_category"],
                promo["manufacturer"],
                promo["model"],
                promo["confidence"],
                promo["source_url"],
                promo["source_type"],
                promo["source_excerpt"],
                promo["geographic_scope"],
                promo["first_seen"],
                promo["last_verified"],
                promo["notes"],
                promo["superseded_by"],
            ),
        )
        identifier_id = cur.lastrowid

        conn.execute(
            "UPDATE raw_observations "
            "SET promoted_identifier_id = ?, processed_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND promoted_identifier_id IS NULL",
            (identifier_id, RAW_OBS_ROW_ID),
        )

        cur = conn.execute(
            """INSERT INTO extraction_runs
                 (agent_id, source_id, finished_at,
                  records_in, records_out, errors, status, notes)
               VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)""",
            (
                VALIDATOR_AGENT_ID,
                12,
                1,
                1,
                0,
                "ok",
                _ledger_notes(identifier_id),
            ),
        )
        ledger_run_id = cur.lastrowid

        conn.commit()

        return {
            "status": "inserted",
            "identifier_id": identifier_id,
            "ledger_run_id": ledger_run_id,
            "approval_id": APPROVAL_ID,
            "confidence": RATIFIED_CONFIDENCE,
            "source_type": promo["source_type"],
            "raw_observations_row_id": RAW_OBS_ROW_ID,
        }
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be inserted without writing.",
    )
    args = parser.parse_args(argv)
    result = promote(dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
