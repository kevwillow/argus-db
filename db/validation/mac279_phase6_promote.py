"""MAC-279 Phase 6 promotion script.

Applies the ratified `operator_review/MAC-279/correction/validated_promotion_set.json`
to `db/argus.db` in a single transaction:

- 116 INSERT (`disposition='promote_new'`)
- 8 UPDATE  (`disposition='promote_lift'`)
    * 2 confidence-changing PASS lifts (id=29328 90→95, id=27468 85→90)
    * 6 provenance-only appends (4 wave_n_apks INDEPENDENCE_FAIL + YJV/AZ4)
- 1 INSERT into `extraction_runs` tagged `MAC-279 Phase 6`

Wake dispatch: MAC-288 (ratified comment `4dbd292a` on MAC-279,
2026-05-29T01:50:35Z). Bible HEAD `69a9355`. Operator backup baseline
`db/argus.db.pre_minimax_revert.20260528T144524Z.bak`
(sha256 `c5644b94d16b9c2bd7ee76502909dd7f9c003dae14df2d2ceb640824ecbfe8b7`).

The 2 over-length source_excerpts (wave_s_google_dorking/{0,8}) are truncated
to the 200-char schema CHECK using the canonical idiom from
`db/validation/wave_a_first_promotion.py:291`; the full pre-clip excerpt is
preserved in `notes.source_excerpt_full_pre_clip` per §11 #7 provenance
fidelity.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "argus.db"
PROMOTION_JSON = REPO_ROOT / "operator_review" / "MAC-279" / "correction" / "validated_promotion_set.json"

AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"
DISPATCH_ISSUE = "MAC-288"
PARENT_ISSUE = "MAC-279"
RATIFICATION_COMMENT = "4dbd292a"
BIBLE_HEAD = "69a9355"
BACKUP_FILE = "db/argus.db.pre_minimax_revert.20260528T144524Z.bak"
BACKUP_SHA256 = "c5644b94d16b9c2bd7ee76502909dd7f9c003dae14df2d2ceb640824ecbfe8b7"

# Lifts whose target row's confidence must change at promote time.
# All other lifts are provenance-only appends (no confidence write).
CONF_CHANGING_LIFTS = {
    29328: 95,  # wave_n_apks/11 — Hikvision enpinfodata, §8.3 PASS
    27468: 90,  # wave_n_apks/14 — Dahua mobile.easy4ipcloud feedback, §8.3 PASS
}


def _truncate_excerpt(excerpt: str | None) -> str | None:
    if not excerpt:
        return None
    return excerpt[:200]


def _build_insert_notes(entry: dict) -> str:
    payload = {
        "mac279_phase6": {
            "candidate_uid": entry["candidate_uid"],
            "ratified_at_issue": DISPATCH_ISSUE,
            "ratified_at_comment": RATIFICATION_COMMENT,
            "bible_head": BIBLE_HEAD,
            "operator_backup": BACKUP_FILE,
            "operator_backup_sha256": BACKUP_SHA256,
            "disposition": entry["disposition"],
            "disposition_reason": entry["disposition_reason"],
            "rule_anchors": entry["rule_anchors"],
            "dedup_classification": entry["dedup_classification"],
            "notes_proposed": entry["notes_proposed"],
        }
    }
    original = entry.get("source_excerpt") or ""
    if len(original) > 200:
        payload["mac279_phase6"]["source_excerpt_full_pre_clip"] = original
    return json.dumps(payload, ensure_ascii=False)


def _build_corroboration_payload(entry: dict) -> dict:
    return {
        "candidate_uid": entry["candidate_uid"],
        "ratified_at_issue": DISPATCH_ISSUE,
        "ratified_at_comment": RATIFICATION_COMMENT,
        "bible_head": BIBLE_HEAD,
        "disposition": entry["disposition"],
        "disposition_reason": entry["disposition_reason"],
        "rule_anchors": entry["rule_anchors"],
        "source_url": entry["source_url"],
        "source_excerpt": entry.get("source_excerpt"),
        "final_confidence_at_lift_time": entry["final_confidence"],
    }


def _load_promotion_set() -> list[dict]:
    with PROMOTION_JSON.open() as f:
        return json.load(f)


def _preflight(conn: sqlite3.Connection, entries: list[dict]) -> None:
    """Verify implicit terms hold against live DB before any write."""
    cur = conn.cursor()
    issues: list[str] = []

    # 1. Lift targets exist + match the expected current confidence values from
    # the dispatch's implicit terms.
    expected_current_conf = {
        29328: 90,  # PASS lift to 95
        27468: 85,  # PASS lift to 90
        36628: 85,  # FAIL provenance-only @ 85
        23046: 92,  # FAIL provenance-only HELD @ 92 (CEO-implicit)
        36589: 85,  # FAIL provenance-only @ 85
        36590: 85,  # FAIL provenance-only @ 85
        35737: 85,  # YJV provenance-only @ 85
        37277: 75,  # AZ4 provenance-only @ 75
    }
    for tid, expected_conf in expected_current_conf.items():
        cur.execute(
            "SELECT confidence, superseded_by FROM identifiers WHERE id=?",
            (tid,),
        )
        row = cur.fetchone()
        if row is None:
            issues.append(f"lift target id={tid} NOT FOUND in identifiers")
            continue
        if row[1] is not None:
            issues.append(f"lift target id={tid} is superseded (superseded_by={row[1]})")
        if row[0] != expected_conf:
            issues.append(
                f"lift target id={tid} confidence={row[0]} but implicit term expects {expected_conf}"
            )

    # 2. None of the 116 promote_new (identifier, identifier_type) already exist.
    promote_new = [e for e in entries if e["disposition"] == "promote_new"]
    for entry in promote_new:
        cur.execute(
            "SELECT id FROM identifiers WHERE identifier=? AND identifier_type=? AND superseded_by IS NULL",
            (entry["identifier"], entry["identifier_type"]),
        )
        if cur.fetchone():
            issues.append(
                f"promote_new candidate {entry['candidate_uid']} already exists "
                f"in identifiers ({entry['identifier_type']}={entry['identifier']!r})"
            )

    # 3. Disposition count matches dispatch.
    n_new = sum(1 for e in entries if e["disposition"] == "promote_new")
    n_lift = sum(1 for e in entries if e["disposition"] == "promote_lift")
    if n_new != 116:
        issues.append(f"promote_new count {n_new} != 116")
    if n_lift != 8:
        issues.append(f"promote_lift count {n_lift} != 8")

    if issues:
        raise SystemExit(
            "PREFLIGHT FAILED — STOP_THE_LINE:\n  - "
            + "\n  - ".join(issues)
        )


def _insert_promote_new(conn: sqlite3.Connection, entry: dict, ts: str) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO identifiers (
            identifier, identifier_type, device_category, manufacturer, model,
            confidence, source_url, source_type, source_excerpt,
            geographic_scope, first_seen, last_verified, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry["identifier"],
            entry["identifier_type"],
            entry["device_category"],
            entry.get("manufacturer"),
            entry.get("model"),
            entry["final_confidence"],
            entry["source_url"],
            entry["source_type"],
            _truncate_excerpt(entry.get("source_excerpt")),
            None,
            ts,
            ts,
            _build_insert_notes(entry),
        ),
    )
    return cur.lastrowid


def _apply_lift(conn: sqlite3.Connection, entry: dict, ts: str) -> dict:
    """Apply a single promote_lift entry. Returns disposition record."""
    cur = conn.cursor()
    target_id = entry["target_canonical_id_for_lift"]
    final_conf = entry["final_confidence"]

    cur.execute(
        "SELECT confidence, notes FROM identifiers WHERE id=?",
        (target_id,),
    )
    row = cur.fetchone()
    pre_conf = row[0]
    pre_notes_raw = row[1] or "{}"
    try:
        notes_obj = json.loads(pre_notes_raw)
        if not isinstance(notes_obj, dict):
            notes_obj = {"_legacy_notes_value": notes_obj}
    except json.JSONDecodeError:
        notes_obj = {"_parse_error": True, "_raw": pre_notes_raw}

    corroborations = notes_obj.setdefault("corroborations", [])
    if not isinstance(corroborations, list):
        notes_obj["corroborations_pre_mac279"] = corroborations
        corroborations = []
        notes_obj["corroborations"] = corroborations

    mac279_entry = _build_corroboration_payload(entry)
    if not any(
        isinstance(c, dict)
        and c.get("candidate_uid") == entry["candidate_uid"]
        and c.get("ratified_at_issue") == DISPATCH_ISSUE
        for c in corroborations
    ):
        corroborations.append(mac279_entry)

    is_conf_change = target_id in CONF_CHANGING_LIFTS and pre_conf != final_conf
    if is_conf_change:
        notes_obj.setdefault("confidence_history", []).append(
            {
                "date": ts,
                "reason": (
                    f"MAC-279 Phase 6 §8.3 corroboration lift "
                    f"(ratified comment {RATIFICATION_COMMENT}); "
                    f"{entry['disposition_reason'][:160]}"
                ),
                "value": final_conf,
                "prior_value": pre_conf,
            }
        )

    new_notes = json.dumps(notes_obj, ensure_ascii=False)

    if is_conf_change:
        cur.execute(
            "UPDATE identifiers SET confidence=?, last_verified=?, notes=? WHERE id=?",
            (final_conf, ts, new_notes, target_id),
        )
        change_kind = "confidence_change"
    else:
        cur.execute(
            "UPDATE identifiers SET last_verified=?, notes=? WHERE id=?",
            (ts, new_notes, target_id),
        )
        change_kind = "provenance_only"

    return {
        "candidate_uid": entry["candidate_uid"],
        "target_id": target_id,
        "pre_confidence": pre_conf,
        "post_confidence": final_conf if is_conf_change else pre_conf,
        "change_kind": change_kind,
    }


def _insert_extraction_run(conn: sqlite3.Connection, ts: str, summary: dict) -> int:
    cur = conn.cursor()
    notes_payload = {
        "dispatch": DISPATCH_ISSUE,
        "parent": PARENT_ISSUE,
        "ratification_comment": RATIFICATION_COMMENT,
        "bible_head": BIBLE_HEAD,
        "operator_backup": BACKUP_FILE,
        "operator_backup_sha256": BACKUP_SHA256,
        "promotion_set": str(
            PROMOTION_JSON.relative_to(REPO_ROOT)
        ),
        "summary": summary,
    }
    cur.execute(
        """
        INSERT INTO extraction_runs (
            agent_id, source_id, started_at, finished_at,
            records_in, records_out, errors, status, notes
        ) VALUES (?, NULL, ?, ?, ?, ?, 0, 'completed', ?)
        """,
        (
            AGENT_ID,
            ts,
            ts,
            summary["records_in"],
            summary["records_out"],
            json.dumps(notes_payload, ensure_ascii=False),
        ),
    )
    return cur.lastrowid


def main() -> int:
    entries = _load_promotion_set()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        _preflight(conn, entries)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        conn.execute("BEGIN")

        pre_active = conn.execute(
            "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
        ).fetchone()[0]

        new_ids = []
        for entry in (e for e in entries if e["disposition"] == "promote_new"):
            new_ids.append(_insert_promote_new(conn, entry, ts))

        lift_results = []
        for entry in (e for e in entries if e["disposition"] == "promote_lift"):
            lift_results.append(_apply_lift(conn, entry, ts))

        post_active = conn.execute(
            "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
        ).fetchone()[0]

        summary = {
            "records_in": len(entries),
            "records_out": len(new_ids) + len(lift_results),
            "promote_new_inserted": len(new_ids),
            "promote_new_id_range": [min(new_ids), max(new_ids)] if new_ids else None,
            "promote_lifts": lift_results,
            "pre_active_count": pre_active,
            "post_active_count": post_active,
            "delta_active": post_active - pre_active,
        }
        run_id = _insert_extraction_run(conn, ts, summary)
        summary["extraction_runs_id"] = run_id

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
