"""MAC-172 §11 #8 strict-reading rollback — undo the 180-row +5 lift.

CEO ratification at MAC-172 [`8db00702`](<TRACKER_URL>issues/MAC-172#comment-8db00702-c710-49de-ac3f-d4d054d3dba8)
ruled Read B canon: within-source re-extraction (USAspending v1.0.0 admission
vs deep-extension session, same upstream API at two times with different
filter windows) is **not** a "second independent source" for §8.3 +5 lift
purposes. Provenance enrichment is genuinely useful and stays; the
confidence lift rolls back.

Single transaction. PK-scoped UPDATE on the 180 rows currently at conf=90:

  1. ``UPDATE procurement_records SET confidence=85 WHERE confidence=90``
     — pre-count verified == 180 inside the transaction; abort if not.
  2. Per-row ``notes.confidence_history[]`` append documenting the 90→85
     reason / dispatch / cp_anchor.
  3. ``notes.corroborations[]`` + ``notes.corroboration_sessions[]``
     preserved (pure provenance — correct under both reads).

Idempotency: skip rows whose latest ``confidence_history[]`` entry already
carries ``dispatch=MAC-172``. Re-runs after first apply produce zero net
change.

Run from repo root::

    python3 -m db.validation.usaspending_deep_admission.rollback_lift \\
        --dry-run    # default — write nothing, emit counts
        --commit     # write to argus.db; idempotent on re-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

DB_PATH = _REPO_ROOT / "db" / "argus.db"
EXPECTED_LIFT_ROW_COUNT = 180
LIFTED_FROM = 90
ROLLBACK_TO = 85
DISPATCH_TAG = "MAC-172"
CP_ANCHOR = "CP24-pending"  # bible amendment bundled in the same commit set
ROLLBACK_RATIONALE = (
    "MAC-172 §11 #8 strict-reading rollback: within-source re-extraction "
    "(USAspending v1.0.0 admission vs deep-extension session) is provenance "
    "enrichment, not corroboration. +5 lift requires independent collector "
    "per §11 #8 + §8.2. Evidence in notes.corroborations[] preserved."
)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _already_rolled_back(history: list[dict[str, Any]]) -> bool:
    if not history:
        return False
    return history[-1].get("dispatch") == DISPATCH_TAG


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument(
        "--report-path",
        type=Path,
        default=_REPO_ROOT
        / "extraction_outputs"
        / "mac172"
        / "rollback_report.json",
    )
    args = parser.parse_args(argv)

    conn = _connect()

    # Pre-state snapshot.
    pre_total = conn.execute(
        "SELECT COUNT(*) FROM procurement_records"
    ).fetchone()[0]
    pre_at_lifted = conn.execute(
        "SELECT COUNT(*) FROM procurement_records WHERE confidence = ?",
        (LIFTED_FROM,),
    ).fetchone()[0]
    pre_at_target = conn.execute(
        "SELECT COUNT(*) FROM procurement_records WHERE confidence = ?",
        (ROLLBACK_TO,),
    ).fetchone()[0]

    # Identify candidate rows.
    rows = conn.execute(
        "SELECT id, confidence, notes FROM procurement_records "
        "WHERE confidence = ?",
        (LIFTED_FROM,),
    ).fetchall()

    # Idempotency partition.
    apply_rows: list[tuple[int, dict[str, Any]]] = []
    skipped_rows: list[int] = []
    for r in rows:
        notes = json.loads(r["notes"] or "{}")
        history = notes.get("confidence_history", [])
        if _already_rolled_back(history):
            skipped_rows.append(r["id"])
            continue
        apply_rows.append((r["id"], notes))

    # Defensive: at first run, exactly EXPECTED_LIFT_ROW_COUNT rows must
    # be at the lifted confidence. After idempotent re-run there should
    # be zero (because they'd have been rolled back to 85 already), so
    # the strict-count check only applies if we have rows to apply AND
    # no rows were previously rolled back via the audit marker on
    # confidence=85 rows (which we don't query here — the at-confidence
    # filter already partitioned them out).
    if apply_rows and pre_at_lifted != EXPECTED_LIFT_ROW_COUNT:
        raise RuntimeError(
            f"Pre-count check failed: expected {EXPECTED_LIFT_ROW_COUNT} rows "
            f"at confidence={LIFTED_FROM}, found {pre_at_lifted}. Aborting."
        )

    band_changes: list[tuple[int, int, int]] = []
    if args.commit:
        conn.execute("BEGIN")
    try:
        for rid, notes in apply_rows:
            history = notes.setdefault("confidence_history", [])
            entry = {
                "at_utc": _now_iso(),
                "from": LIFTED_FROM,
                "to": ROLLBACK_TO,
                "rationale": ROLLBACK_RATIONALE,
                "dispatch": DISPATCH_TAG,
                "cp_anchor": CP_ANCHOR,
            }
            history.append(entry)
            band_changes.append((rid, LIFTED_FROM, ROLLBACK_TO))
            if args.commit:
                conn.execute(
                    "UPDATE procurement_records "
                    "SET confidence = ?, notes = ? "
                    "WHERE id = ? AND confidence = ?",
                    (
                        ROLLBACK_TO,
                        json.dumps(notes, sort_keys=True),
                        rid,
                        LIFTED_FROM,
                    ),
                )
    except Exception:
        if args.commit:
            conn.rollback()
        raise
    if args.commit:
        conn.commit()

    # Post-state snapshot.
    post_total = conn.execute(
        "SELECT COUNT(*) FROM procurement_records"
    ).fetchone()[0]
    post_at_lifted = conn.execute(
        "SELECT COUNT(*) FROM procurement_records WHERE confidence = ?",
        (LIFTED_FROM,),
    ).fetchone()[0]
    post_at_target = conn.execute(
        "SELECT COUNT(*) FROM procurement_records WHERE confidence = ?",
        (ROLLBACK_TO,),
    ).fetchone()[0]

    # Provenance preservation audit on a sample of the rolled-back rows.
    preserve_sample_ids = [rid for rid, *_ in band_changes[:3]] + skipped_rows[:3]
    preservation_audit = []
    for rid in preserve_sample_ids:
        row = conn.execute(
            "SELECT confidence, notes FROM procurement_records WHERE id = ?",
            (rid,),
        ).fetchone()
        if row is None:
            continue
        notes = json.loads(row["notes"] or "{}")
        preservation_audit.append(
            {
                "id": rid,
                "confidence": row["confidence"],
                "corroborations_count": len(notes.get("corroborations", [])),
                "corroboration_sessions": notes.get("corroboration_sessions", []),
                "confidence_history_count": len(
                    notes.get("confidence_history", [])
                ),
                "last_confidence_history_dispatch": (
                    notes.get("confidence_history", [{}])[-1].get("dispatch")
                    if notes.get("confidence_history")
                    else None
                ),
            }
        )

    report = {
        "run_at_utc": _now_iso(),
        "mode": "commit" if args.commit else "dry_run",
        "dispatch": DISPATCH_TAG,
        "cp_anchor": CP_ANCHOR,
        "pre_state": {
            "total": pre_total,
            f"at_conf_{LIFTED_FROM}": pre_at_lifted,
            f"at_conf_{ROLLBACK_TO}": pre_at_target,
        },
        "applied": len(band_changes) if args.commit else 0,
        "skipped_idempotent": len(skipped_rows),
        "proposed": len(apply_rows),
        "post_state": {
            "total": post_total,
            f"at_conf_{LIFTED_FROM}": post_at_lifted,
            f"at_conf_{ROLLBACK_TO}": post_at_target,
        },
        "preservation_audit": preservation_audit,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
