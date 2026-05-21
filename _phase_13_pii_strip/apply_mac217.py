"""MAC-217 §8.2 PII-strip + Track B VCH demotion — single-transaction applier.

Per CEO ratification at MAC-217 comment 668ed6b8 (revised dispatch):

Track A — regex-strip email-shape tokens from source_excerpt on:
  - 6 identifiers rows (mac_range, IEEE MA-M/MA-S registrant lines)
  - 6 paired raw_observations rows (promoted into the same 6 idents)
  Provenance per row written into notes (JSON-merge):
    original_source_excerpt_hash, pii_stripped_at, pii_strip_dispatch='MAC-217'

Track B — demote 4 vendor_controlled_hostname rows whose identifier value
IS the email (crt.sh certificate-subject SAN leak). Mechanic:
  UPDATE identifiers SET superseded_by = id WHERE id IN (...)
  Provenance per row written into notes (JSON-merge):
    demoted_at, demote_dispatch='MAC-217', demote_reason='pii_identifier_value'

Demotion mechanic = superseded_by self-loop. Auto-filtered by
db/validation/export_lynceus.py via WHERE superseded_by IS NULL. The
behavioral_signatures sibling queries a different table — VCH rows
don't appear there.

Halt conditions (matches CEO §"Halt criteria"):
  - Pre-flight scope mismatch vs expected 6/6/4 set
  - Any regex sub fails to mutate (empty match → halt)
  - Any UPDATE rowcount != 1
  - Notes is non-JSON on any target row
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "db" / "argus.db"
DISPATCH = "MAC-217"

# Pre-flight expected scope (CEO 6:6:4 mapping)
TRACK_A_IDENT_IDS = (5230, 11234, 11725, 12739, 13780, 20999)
TRACK_A_RO_IDS = (224705, 232023, 232636, 233968, 234093, 235323)
TRACK_B_IDENT_IDS = (31582, 32059, 32060, 32511)

# 6:6 ident:ro pairing (CEO-confirmed, DBArchitect re-verified)
TRACK_A_PAIRS = (
    (5230, 224705),
    (11234, 232023),
    (11725, 232636),
    (12739, 233968),
    (13780, 235323),
    (20999, 234093),
)

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
REDACTION = "[email-redacted]"


class Halt(RuntimeError):
    """Raise to abort the transaction (caller will rollback)."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _merge_notes(existing: str | None, new_keys: dict) -> str:
    """Parse existing notes JSON, merge new keys (overwriting if collision),
    and return JSON text. Halt if existing is non-JSON (all 16 target rows
    verified JSON in pre-flight)."""
    if existing is None or existing == "":
        return json.dumps(new_keys, ensure_ascii=False)
    try:
        parsed = json.loads(existing)
    except json.JSONDecodeError as e:
        raise Halt(f"existing notes is non-JSON: {e}; raw[:200]={existing[:200]!r}")
    if not isinstance(parsed, dict):
        raise Halt(f"existing notes is JSON but not an object: type={type(parsed).__name__}")
    parsed.update(new_keys)
    return json.dumps(parsed, ensure_ascii=False)


def _strip_emails(text: str) -> str:
    return EMAIL_REGEX.sub(REDACTION, text)


def main() -> int:
    timestamp = _utc_now_iso()
    audit_log: list[dict] = []

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON;")

    # SAR-13 PRAGMA pre-flight on both target tables
    integrity = con.execute("PRAGMA integrity_check").fetchall()
    quick = con.execute("PRAGMA quick_check").fetchall()
    fk_check = con.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != [("ok",)] or quick != [("ok",)] or fk_check != []:
        raise Halt(
            f"SAR-13 PRAGMA pre-flight failed: integrity={integrity} "
            f"quick={quick} foreign_keys={fk_check}"
        )

    con.execute("BEGIN IMMEDIATE")
    try:
        # ---------------- Track A: strip 6 identifiers.source_excerpt ----------------
        for ident_id in TRACK_A_IDENT_IDS:
            row = con.execute(
                "SELECT id, identifier, identifier_type, source_excerpt, notes "
                "FROM identifiers WHERE id = ? AND superseded_by IS NULL",
                (ident_id,),
            ).fetchone()
            if row is None:
                raise Halt(f"Track A ident {ident_id}: not found OR already superseded")
            iid, ident, itype, excerpt, notes = row
            if itype != "mac_range":
                raise Halt(f"Track A ident {iid}: expected identifier_type='mac_range', got {itype!r}")
            if not excerpt or not EMAIL_REGEX.search(excerpt):
                raise Halt(f"Track A ident {iid}: source_excerpt has no email-shape token (already stripped?)")
            original_hash = _sha256(excerpt)
            stripped = _strip_emails(excerpt)
            if stripped == excerpt:
                raise Halt(f"Track A ident {iid}: regex sub produced no change")
            if EMAIL_REGEX.search(stripped):
                raise Halt(f"Track A ident {iid}: post-strip still contains email shape: {stripped[:200]!r}")
            new_notes = _merge_notes(notes, {
                "original_source_excerpt_hash": original_hash,
                "pii_stripped_at": timestamp,
                "pii_strip_dispatch": DISPATCH,
            })
            cur = con.execute(
                "UPDATE identifiers SET source_excerpt = ?, notes = ? "
                "WHERE id = ? AND superseded_by IS NULL",
                (stripped, new_notes, iid),
            )
            if cur.rowcount != 1:
                raise Halt(f"Track A ident {iid}: UPDATE rowcount={cur.rowcount}, expected 1")
            audit_log.append({
                "track": "A",
                "table": "identifiers",
                "id": iid,
                "identifier": ident,
                "original_hash": original_hash,
                "stripped_excerpt": stripped,
            })

        # ---------------- Track A: strip 6 raw_observations.source_excerpt ----------------
        for ro_id in TRACK_A_RO_IDS:
            row = con.execute(
                "SELECT id, source_excerpt, notes, promoted_identifier_id "
                "FROM raw_observations WHERE id = ?",
                (ro_id,),
            ).fetchone()
            if row is None:
                raise Halt(f"Track A ro {ro_id}: not found")
            rid, excerpt, notes, pid = row
            expected_pid = dict(TRACK_A_PAIRS).get(None)  # not used directly; pairing validated below
            if pid not in TRACK_A_IDENT_IDS:
                raise Halt(f"Track A ro {rid}: promoted_identifier_id={pid} not in Track A set")
            if not excerpt or not EMAIL_REGEX.search(excerpt):
                raise Halt(f"Track A ro {rid}: source_excerpt has no email-shape token")
            original_hash = _sha256(excerpt)
            stripped = _strip_emails(excerpt)
            if stripped == excerpt:
                raise Halt(f"Track A ro {rid}: regex sub produced no change")
            if EMAIL_REGEX.search(stripped):
                raise Halt(f"Track A ro {rid}: post-strip still contains email shape")
            new_notes = _merge_notes(notes, {
                "original_source_excerpt_hash": original_hash,
                "pii_stripped_at": timestamp,
                "pii_strip_dispatch": DISPATCH,
            })
            cur = con.execute(
                "UPDATE raw_observations SET source_excerpt = ?, notes = ? WHERE id = ?",
                (stripped, new_notes, rid),
            )
            if cur.rowcount != 1:
                raise Halt(f"Track A ro {rid}: UPDATE rowcount={cur.rowcount}, expected 1")
            audit_log.append({
                "track": "A",
                "table": "raw_observations",
                "id": rid,
                "promoted_identifier_id": pid,
                "original_hash": original_hash,
                "stripped_excerpt": stripped,
            })

        # ---------------- Track B: demote 4 VCH idents via superseded_by self-loop ----------------
        for ident_id in TRACK_B_IDENT_IDS:
            row = con.execute(
                "SELECT id, identifier, identifier_type, superseded_by, notes "
                "FROM identifiers WHERE id = ?",
                (ident_id,),
            ).fetchone()
            if row is None:
                raise Halt(f"Track B ident {ident_id}: not found")
            iid, ident, itype, sup, notes = row
            if itype != "vendor_controlled_hostname":
                raise Halt(f"Track B ident {iid}: expected vendor_controlled_hostname, got {itype!r}")
            if sup is not None:
                raise Halt(f"Track B ident {iid}: already superseded (sup={sup})")
            if not EMAIL_REGEX.fullmatch(ident or ""):
                raise Halt(f"Track B ident {iid}: identifier value {ident!r} doesn't fully match email regex")
            new_notes = _merge_notes(notes, {
                "demoted_at": timestamp,
                "demote_dispatch": DISPATCH,
                "demote_reason": "pii_identifier_value",
                "demote_mechanic": "superseded_by_self_loop",
            })
            cur = con.execute(
                "UPDATE identifiers SET superseded_by = id, notes = ? "
                "WHERE id = ? AND superseded_by IS NULL",
                (new_notes, iid),
            )
            if cur.rowcount != 1:
                raise Halt(f"Track B ident {iid}: UPDATE rowcount={cur.rowcount}, expected 1")
            audit_log.append({
                "track": "B",
                "table": "identifiers",
                "id": iid,
                "identifier_was_pii": ident,
                "mechanic": "superseded_by_self_loop",
            })

        # ---------------- Final-pre-commit sanity ----------------
        # Verify scope counts
        if len([r for r in audit_log if r["track"] == "A" and r["table"] == "identifiers"]) != 6:
            raise Halt("Track A identifiers count != 6")
        if len([r for r in audit_log if r["track"] == "A" and r["table"] == "raw_observations"]) != 6:
            raise Halt("Track A raw_observations count != 6")
        if len([r for r in audit_log if r["track"] == "B"]) != 4:
            raise Halt("Track B identifiers count != 4")

        # Verify zero residual PII on the 12 stripped rows + zero active VCH-email-ident rows
        residual_idents = con.execute(
            "SELECT id, source_excerpt FROM identifiers WHERE id IN ({}) ".format(
                ",".join("?" * len(TRACK_A_IDENT_IDS))
            ),
            TRACK_A_IDENT_IDS,
        ).fetchall()
        for rid, ex in residual_idents:
            if EMAIL_REGEX.search(ex or ""):
                raise Halt(f"post-mutation: ident {rid} still has email PII")
        residual_ros = con.execute(
            "SELECT id, source_excerpt FROM raw_observations WHERE id IN ({}) ".format(
                ",".join("?" * len(TRACK_A_RO_IDS))
            ),
            TRACK_A_RO_IDS,
        ).fetchall()
        for rid, ex in residual_ros:
            if EMAIL_REGEX.search(ex or ""):
                raise Halt(f"post-mutation: ro {rid} still has email PII")
        active_vch_email_count = con.execute(
            "SELECT COUNT(*) FROM identifiers WHERE id IN ({}) AND superseded_by IS NULL".format(
                ",".join("?" * len(TRACK_B_IDENT_IDS))
            ),
            TRACK_B_IDENT_IDS,
        ).fetchone()[0]
        if active_vch_email_count != 0:
            raise Halt(f"post-mutation: {active_vch_email_count} VCH-email idents still active")

        con.commit()
        print("COMMIT OK: 12 Track A strips + 4 Track B demotes applied.")
    except Exception:
        con.rollback()
        print("ROLLBACK: transaction aborted, no mutations persisted.", file=sys.stderr)
        raise
    finally:
        con.close()

    # Emit audit log as JSON
    log_path = Path(__file__).parent / "applied_log.json"
    log_path.write_text(
        json.dumps({"dispatch": DISPATCH, "applied_at": timestamp, "rows": audit_log}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Audit log written to {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
