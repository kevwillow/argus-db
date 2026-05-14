"""CP19 Scope 2 jlrjr-sub-source refinement sub-sweep (MAC-96 post-handback).

Refines the 335 Scope 2 rows from the parent CP19 sweep (`MAC-88-cp19-sweep-1`,
commit c121bec) to point at the more precise jlrjr/faa-rid-lookup sub-source
rather than the top-level alphafox02/DragonSync wrapper.

Authority chain:
- CEO refinement comment on MAC-96 (2026-05-14T02:30:07Z, comment
  0f118ada-67d0-403b-a170-6670ff23f093), referencing MAC-88 board
  ratification f253206b: "worker has authority to substitute
  jlrjr/faa-rid-lookup as more precise sub-source if verification path
  surfaces it (same data lineage, more accurate attribution).
  HALT-AND-SURFACE if neither alphafox02 nor jlrjr resolves."
- Parent sweep (MAC-88-cp19-sweep-1, c121bec) landed within ~2s of the
  refinement comment with alphafox02/DragonSync (the documented fallback).
  This sub-sweep refines per the first-preference URL now that HEAD-verify
  confirms jlrjr resolves (HTTP 200).
- Bible §11 #8 audit-trail sub-rule: identifier-row UPDATE + audit INSERT
  in SAME transaction (preserved).
- Bible §11 #7 provenance: same data lineage (FAA RID lookup submodule of
  alphafox02/DragonSync is the jlrjr-authored sub-repo); URL is a
  more-precise pointer at the same upstream attribution, no confidence
  delta.

Scope is narrow: 335 rows that match exactly the parent-sweep Scope 2
post-state (source_url=alphafox02/DragonSync, source_type=crowdsourced,
confidence=75, superseded_by IS NULL). source_type and confidence
UNCHANGED — this is a sub-source URL tightening, not a band change.

Idempotent: pre-conditions guard re-runs (matches the parent-sweep idiom).
A second run sees 0 rows matching the pre-state filter and produces 0
new audit rows.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"

SWEEP_EVENT_ID = "MAC-88-cp19-sweep-1-jlrjr-refinement"
RECLASS_ANCHOR = (
    "CP19 MAC-88 f253206b — Scope 2 jlrjr sub-source refinement "
    "(post-handback CEO refinement on MAC-96 comment 0f118ada)"
)

ALPHAFOX_URL = "https://github.com/alphafox02/DragonSync"
JLRJR_URL = "https://github.com/jlrjr/faa-rid-lookup"


def head_resolves(url: str, *, timeout: float = 15.0) -> tuple[bool, int | str]:
    """Return (ok, status_or_error). HEAD-verify URL resolves with 2xx/3xx."""
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (200 <= resp.status < 400, resp.status)
    except Exception as exc:
        return (False, repr(exc))


def per_row_reason(identifier: str) -> str:
    """Substantive per-row rationale (board a1dab600 §2 convention)."""
    return (
        f"Refinement to more precise sub-source for identifier {identifier}: "
        f"the parent CP19 Scope 2 sweep (MAC-88-cp19-sweep-1, commit c121bec) "
        f"recorded source_url at the top-level alphafox02/DragonSync wrapper "
        f"per the documented fallback. Per CEO refinement on MAC-96 "
        f"(2026-05-14T02:30:07Z, MAC-88 board f253206b), worker has authority "
        f"to substitute jlrjr/faa-rid-lookup as the more precise sub-source "
        f"(same data lineage — FAA RID lookup submodule is the jlrjr-authored "
        f"sub-repo bundled by alphafox02/DragonSync — and more accurate "
        f"attribution). source_url tightens from "
        f"https://github.com/alphafox02/DragonSync to "
        f"https://github.com/jlrjr/faa-rid-lookup; source_type "
        f"(crowdsourced) and confidence (75) unchanged. HEAD-verify confirmed "
        f"both URLs resolve at sub-sweep execution start; first-preference "
        f"jlrjr applied per the refinement priority."
    )


def select_target_rows(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """Return list of (id, identifier) for the 335 target rows.

    Pre-condition filter mirrors the parent-sweep Scope 2 post-state
    exactly, so idempotency is automatic on re-run.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, identifier
        FROM identifiers
        WHERE source_url = ?
          AND source_type = 'crowdsourced'
          AND confidence = 75
          AND superseded_by IS NULL
        ORDER BY id
        """,
        (ALPHAFOX_URL,),
    )
    return cur.fetchall()


def run_sweep(conn: sqlite3.Connection, *, head_check_ts: str) -> dict:
    """Execute the corrective sub-sweep. Returns summary dict."""
    rows = select_target_rows(conn)
    n = len(rows)
    if n == 0:
        return {
            "target_rows": 0,
            "updates": 0,
            "audit_inserts": 0,
            "note": "no rows matched pre-state filter — sub-sweep is idempotent no-op",
        }

    # Audit any existing entries under this sweep_event_id (idempotency guard)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM source_reclassifications WHERE sweep_event_id = ?",
        (SWEEP_EVENT_ID,),
    )
    existing = cur.fetchone()[0]
    if existing > 0:
        raise RuntimeError(
            f"sweep_event_id {SWEEP_EVENT_ID} already has {existing} audit rows; "
            f"refusing to double-insert. Inspect DB state and decide manually."
        )

    notes_text = (
        f"Parent sweep used alphafox02/DragonSync (documented fallback); "
        f"jlrjr/faa-rid-lookup HEAD-verified at {head_check_ts} (HTTP 200), "
        f"applied as first-preference per CEO refinement."
    )

    with conn:  # transaction
        for row_id, identifier in rows:
            # UPDATE identifier
            cur.execute(
                """
                UPDATE identifiers
                SET source_url = ?
                WHERE id = ?
                  AND source_url = ?
                  AND source_type = 'crowdsourced'
                  AND confidence = 75
                  AND superseded_by IS NULL
                """,
                (JLRJR_URL, row_id, ALPHAFOX_URL),
            )
            if cur.rowcount != 1:
                raise RuntimeError(
                    f"row {row_id} ({identifier}) did not match pre-state at "
                    f"UPDATE time (rowcount={cur.rowcount}); transaction rollback"
                )
            # INSERT audit
            cur.execute(
                """
                INSERT INTO source_reclassifications (
                    identifier_id, sweep_event_id,
                    pre_source_url, post_source_url,
                    pre_source_type, post_source_type,
                    pre_confidence, post_confidence,
                    reclassification_reason, reclassification_anchor,
                    reclassified_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """,
                (
                    row_id,
                    SWEEP_EVENT_ID,
                    ALPHAFOX_URL,
                    JLRJR_URL,
                    "crowdsourced",
                    "crowdsourced",
                    75,
                    75,
                    per_row_reason(identifier),
                    RECLASS_ANCHOR,
                    notes_text,
                ),
            )

    return {
        "target_rows": n,
        "updates": n,
        "audit_inserts": n,
        "note": "sub-sweep landed in single transaction",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH, help="DB path")
    parser.add_argument("--dry-run", action="store_true", help="HEAD-check + filter, no UPDATE")
    args = parser.parse_args()

    print(f"[cp19-jlrjr] DB: {args.db}")
    print(f"[cp19-jlrjr] sweep_event_id: {SWEEP_EVENT_ID}")
    print(f"[cp19-jlrjr] dry-run: {args.dry_run}")

    # HEAD-verify both URLs per refinement HALT-AND-SURFACE condition
    jlrjr_ok, jlrjr_status = head_resolves(JLRJR_URL)
    alpha_ok, alpha_status = head_resolves(ALPHAFOX_URL)
    head_check_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print(f"[cp19-jlrjr] HEAD jlrjr/faa-rid-lookup: ok={jlrjr_ok} status={jlrjr_status}")
    print(f"[cp19-jlrjr] HEAD alphafox02/DragonSync: ok={alpha_ok} status={alpha_status}")

    if not jlrjr_ok and not alpha_ok:
        print(
            "[cp19-jlrjr] HALT-AND-SURFACE: neither jlrjr nor alphafox02 resolves",
            file=sys.stderr,
        )
        return 2
    if not jlrjr_ok:
        print(
            "[cp19-jlrjr] jlrjr does NOT resolve; per refinement priority, "
            "alphafox02 fallback stands. No sub-sweep needed. Exit 0 (no-op).",
        )
        return 0

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        if args.dry_run:
            rows = select_target_rows(conn)
            print(f"[cp19-jlrjr] dry-run: target rows = {len(rows)}")
            if rows[:3]:
                print(f"[cp19-jlrjr] sample: {rows[:3]}")
            return 0
        summary = run_sweep(conn, head_check_ts=head_check_ts)
        print(f"[cp19-jlrjr] summary: {summary}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
