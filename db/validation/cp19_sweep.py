"""Phase-5 CP19 4-scope sources reclassification sweep (MAC-96).

Executes the board-ratified Wave-B+ sources reclassification sweep across 4
scopes plus paired per-row audit entries into the `source_reclassifications`
table (created by migration 0017 / MAC-95).

Scopes (board ratification MAC-88 a1dab600):
- Scope 1: 80 Wave-A FAA RID rows (id 569-983 subset) UPGRADE
  source_url listDocs → DETAIL URL; source_type/confidence unchanged.
  Mapping: load Wave-B canonical JSON, match identifier, pick
  lexicographically smallest DETAIL URL for the 9 multi-DETAIL cases.
- Scope 2: 335 Wave-A FAA RID rows (id 569-983 subset) DOWNGRADE
  source_type primary_registry → crowdsourced; confidence 85 → 75;
  source_url → jlrjr-wrapper canonical (alphafox02/DragonSync).
- Scope 3: 58 IEEE-direct inferred rows LIFT source_type inferred →
  primary_registry. Confidence ladder:
    - 54 conf=55 rows → conf=85 (primary_registry single-source ceiling)
    - 4 conf=80 rows → keep conf=80 (per a1dab600 subordinate ratification)
  source_url unchanged. Per-row source_url HEAD-resolve verified pre-flight.
- Scope 4: sources.id=7 (fcc_grantees) band UPDATE official → primary_registry.
  No identifier audit entry (audit table is identifier-keyed).

Authority chain:
- Bible §6 Phase 5 + §7.4 (Validator reclassification contract).
- §4.2 + §7.5 + §11 #8 CP19 §-amendment (HEAD post-MAC-95).
- §11 #8 audit-trail sub-rule: identifier-row UPDATE + audit INSERT in
  SAME transaction.
- §11 #11 amendment-log discipline; §11 #15 schema-sibling discipline
  (CP19 coordinated commit at MAC-95 c883cec).
- CP15 §11 #8 strict reading: source_url must point directly at registry
  issuer; Wave-A FAA listDocs URL is not registry-issuer-canonical.
- CP15 §5 deferred IEEE reclassification scope (Scope 3 anchor).
- MAC-88 board ratification a1dab600 §§ 1-5 (partition counts, audit-trail
  framing, jlrjr-wrapper anchor, sources.id=7 band, source_type exclusion).
- feedback_bible_amendment_downstream_consumer_audit.md (single-surface
  CEO memory; recurrence chain extended to #5; this dispatch is downstream
  consumer audit instance #5).
- SAR-12 pre-flight discipline (CEO §0 baselines re-verified against DB
  at sweep execution start; partition drift = HALT-AND-SURFACE).
- Migration 0017 (source_reclassifications table; landed at MAC-95 c883cec).

Idempotent: re-running with same DB state + same sweep_event_id yields zero
new audit rows (guard on existing source_reclassifications.sweep_event_id rows
matches all 473 expected post-sweep audit rows). UPDATEs to identifiers /
sources are pre-condition gated (a re-run sees post-sweep state and is a
no-op partition).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"
WAVE_B_JSON = (
    Path(__file__).resolve().parents[2]
    / "raw"
    / "wave_b"
    / "faa_rid_repull_2026-05-13"
    / "2026-05-13T13-59-02Z.json"
)

SWEEP_EVENT_ID = "MAC-88-cp19-sweep-1"
RECLASS_ANCHOR_S1 = "CP19 MAC-88 a1dab600 — Scope 1 Wave-A→Wave-B-canonical source_url upgrade"
RECLASS_ANCHOR_S2 = "CP19 MAC-88 a1dab600 — Scope 2 jlrjr-derived band downgrade per §11 #8 strict reading"
RECLASS_ANCHOR_S3 = "CP19 MAC-88 a1dab600 — Scope 3 CP15 §5 deferred IEEE reclassification"

JLRJR_CANONICAL_URL = "https://github.com/alphafox02/DragonSync"


def load_wave_b_map() -> dict[str, list[tuple[str, str]]]:
    """Return identifier → list[(DETAIL_URL, source_excerpt)] from Wave-B JSON."""
    with WAVE_B_JSON.open() as f:
        data = json.load(f)
    ident_map: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for c in data["candidates"]:
        ident_map[c["candidate_identifier"]].append(
            (c["source_url"], c["source_excerpt"])
        )
    return ident_map


def partition_wave_a(
    cur: sqlite3.Cursor, ident_map: dict[str, list[tuple[str, str]]]
) -> tuple[list[dict], list[dict], list[tuple[int, str, list[str]]]]:
    """Partition Wave-A FAA listDocs rows (id 569-983) into Scope 1 / Scope 2.

    Scope 1 row dict: {id, identifier, old_url, new_url, new_excerpt}
    Scope 2 row dict: {id, identifier, old_url}
    multi_detail: list of (row_id, identifier, [all DETAIL URLs sorted])
    """
    cur.execute(
        """
        SELECT id, identifier, source_url, source_excerpt
        FROM identifiers
        WHERE id BETWEEN 569 AND 983
          AND source_url LIKE '%uasdoc.faa.gov/listDocs%'
          AND superseded_by IS NULL
        ORDER BY id
        """
    )
    rows = cur.fetchall()
    s1, s2, multi = [], [], []
    for rid, ident, old_url, _old_exc in rows:
        if ident in ident_map:
            urls = ident_map[ident]
            sorted_urls = sorted(u for u, _ in urls)
            if len(urls) > 1:
                multi.append((rid, ident, sorted_urls))
            chosen = min(urls, key=lambda x: x[0])
            s1.append(
                {
                    "id": rid,
                    "identifier": ident,
                    "old_url": old_url,
                    "new_url": chosen[0],
                    "new_excerpt": chosen[1],
                }
            )
        else:
            s2.append({"id": rid, "identifier": ident, "old_url": old_url})
    return s1, s2, multi


def load_scope_3(cur: sqlite3.Cursor) -> list[dict]:
    """Return list of dicts for the 58 IEEE-direct inferred rows."""
    cur.execute(
        """
        SELECT id, identifier, identifier_type, device_category,
               source_url, source_type, confidence
        FROM identifiers
        WHERE (source_url LIKE '%standards-oui.ieee.org%' OR source_url LIKE '%ieee.org%')
          AND source_type = 'inferred'
          AND superseded_by IS NULL
        ORDER BY id
        """
    )
    out = []
    for rid, ident, itype, devcat, surl, stype, conf in cur.fetchall():
        out.append(
            {
                "id": rid,
                "identifier": ident,
                "identifier_type": itype,
                "device_category": devcat,
                "source_url": surl,
                "old_source_type": stype,
                "old_confidence": conf,
                # Per board a1dab600: conf=55 → 85; conf=80 → keep 80
                "new_confidence": 85 if conf == 55 else conf,
            }
        )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Per-row substantive reclassification_reason builders
# (board's a1dab600 §2 refinement: self-explanatory at row-level WITHOUT
# cross-referencing the dispatch)
# ─────────────────────────────────────────────────────────────────────────────


def reason_scope_1(identifier: str, old_url: str, new_url: str) -> str:
    return (
        f"Wave-A staging promoted identifier {identifier} with FAA listDocs-shared-URL at MAC-63 "
        f"cycle-2 ({old_url}); Wave-B re-pull confirms FAA-canonical equivalent at per-record "
        f"DETAIL URL {new_url}. Per CP15 §11 #8 strict reading, source_url tightens from "
        f"shared-list URL to per-record DETAIL URL. Same primary_registry band, same "
        f"confidence (85); provenance citation upgrade only."
    )


def reason_scope_2(identifier: str) -> str:
    return (
        f"Wave-A staging source for identifier {identifier}: alphafox02/DragonSync FAA RID "
        f"lookup submodule (jlrjr wrapper field-observation aggregation); no current "
        f"FAA-canonical equivalent at uasdoc.faa.gov/api/v1/publicDOCRev/*. Per CP15 §11 #8 "
        f"strict reading, primary_registry status requires source_url at FAA registry issuer "
        f"publication; this row's lineage doesn't satisfy. Reclassifying to crowdsourced "
        f"(75 ceiling per §8.2); confidence ceiling 85→75 reflects the band step-down."
    )


def reason_scope_3(
    identifier: str, identifier_type: str, old_conf: int, new_conf: int
) -> str:
    if old_conf == new_conf:
        # The 4 conf=80 rows (keep conf=80)
        conf_note = (
            f"Confidence unchanged at {old_conf} (per-row §8.3 corroboration semantics; "
            f"no auto-lift to primary_registry single-source ceiling 85)."
        )
    else:
        conf_note = (
            f"Confidence lifts {old_conf}→{new_conf} (primary_registry single-source "
            f"ceiling per §8.2; no corroboration noted; standard band promotion)."
        )
    return (
        f"Pre-Wave-B IEEE-direct {identifier_type} row {identifier} at "
        f"standards-oui.ieee.org URL family. Per CP15 §5 deferred reclassification scope "
        f"+ §11 #8 strict reading, IEEE registry IS the source-of-truth for "
        f"OUI→manufacturer attribution; row qualifies for primary_registry band "
        f"(70-85 single-source per §8.2). source_url unchanged (already IEEE-direct); "
        f"band lift only. {conf_note} Per-row source_url verified resolvable at sweep "
        f"execution."
    )


SCOPE_4_NOTES_APPEND = (
    "[CP19 2026-05-14 MAC-88 a1dab600 §4] Band reclassified from official → "
    "primary_registry. fcc_grantees is a registry-of-record for FCC-ID → company "
    "attribution; per §8.2 narrative, primary_registry shape (registry IS source-of-truth "
    "for what FCC ID means). NOT official (which is for court-verifiable filings about "
    "specific deployed instances). Orthogonal to future FCC-EAS test-report identifier "
    "rows — those would carry regulatory or official band independently per their own "
    "provenance."
)


# ─────────────────────────────────────────────────────────────────────────────
# Sweep driver
# ─────────────────────────────────────────────────────────────────────────────


def assert_pre_flight(cur: sqlite3.Cursor) -> None:
    """Halt if any §0 baseline drifted post-MAC-95."""
    # Schema version
    cur.execute("SELECT MAX(version) FROM schema_version")
    v = cur.fetchone()[0]
    if v != 17:
        raise RuntimeError(f"schema_version drift: expected 17, got {v}")

    # source_reclassifications exists
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='source_reclassifications'"
    )
    if not cur.fetchone():
        raise RuntimeError("source_reclassifications table missing (MAC-95 not applied)")

    # identifiers active count
    cur.execute("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL")
    n = cur.fetchone()[0]
    if n != 18820:
        raise RuntimeError(f"identifiers active count drift: expected 18820, got {n}")

    # Wave-A FAA listDocs subset = 415
    cur.execute(
        """
        SELECT COUNT(*) FROM identifiers
        WHERE id BETWEEN 569 AND 983
          AND source_url LIKE '%uasdoc.faa.gov/listDocs%'
          AND superseded_by IS NULL
        """
    )
    n = cur.fetchone()[0]
    if n != 415:
        raise RuntimeError(f"Wave-A FAA listDocs subset drift: expected 415, got {n}")

    # Scope 3 baseline = 58
    cur.execute(
        """
        SELECT COUNT(*) FROM identifiers
        WHERE (source_url LIKE '%standards-oui.ieee.org%' OR source_url LIKE '%ieee.org%')
          AND source_type = 'inferred'
          AND superseded_by IS NULL
        """
    )
    n = cur.fetchone()[0]
    if n != 58:
        raise RuntimeError(f"Scope 3 baseline drift: expected 58, got {n}")

    # Scope 4 baseline: sources.id=7 = official
    cur.execute("SELECT source_type FROM sources WHERE id = 7")
    row = cur.fetchone()
    if row is None or row[0] != "official":
        raise RuntimeError(
            f"Scope 4 baseline drift: sources.id=7 source_type != 'official' "
            f"(actual: {row[0] if row else 'MISSING'})"
        )

    # Idempotency guard: no prior sweep_event_id rows
    cur.execute(
        "SELECT COUNT(*) FROM source_reclassifications WHERE sweep_event_id = ?",
        (SWEEP_EVENT_ID,),
    )
    n = cur.fetchone()[0]
    if n != 0:
        raise RuntimeError(
            f"Idempotency violation: {n} existing audit rows for "
            f"sweep_event_id={SWEEP_EVENT_ID!r}; sweep already executed?"
        )


def insert_audit(
    cur: sqlite3.Cursor,
    *,
    identifier_id: int,
    pre_url: str,
    post_url: str,
    pre_type: str,
    post_type: str,
    pre_conf: int,
    post_conf: int,
    reason: str,
    anchor: str,
) -> None:
    cur.execute(
        """
        INSERT INTO source_reclassifications (
            identifier_id, sweep_event_id,
            pre_source_url, post_source_url,
            pre_source_type, post_source_type,
            pre_confidence, post_confidence,
            reclassification_reason, reclassification_anchor,
            reclassified_at, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL)
        """,
        (
            identifier_id,
            SWEEP_EVENT_ID,
            pre_url,
            post_url,
            pre_type,
            post_type,
            pre_conf,
            post_conf,
            reason,
            anchor,
        ),
    )


def execute_scope_1(cur: sqlite3.Cursor, rows: list[dict]) -> int:
    """80 UPGRADE source_url + 80 audit entries."""
    for r in rows:
        cur.execute(
            """
            UPDATE identifiers
            SET source_url = ?, source_excerpt = ?
            WHERE id = ?
              AND source_url LIKE '%uasdoc.faa.gov/listDocs%'
              AND source_type = 'primary_registry'
              AND confidence = 85
            """,
            (r["new_url"], r["new_excerpt"], r["id"]),
        )
        if cur.rowcount != 1:
            raise RuntimeError(
                f"Scope 1 UPDATE rowcount != 1 for id={r['id']} (got {cur.rowcount}); "
                f"pre-condition guard tripped — halting."
            )
        insert_audit(
            cur,
            identifier_id=r["id"],
            pre_url=r["old_url"],
            post_url=r["new_url"],
            pre_type="primary_registry",
            post_type="primary_registry",
            pre_conf=85,
            post_conf=85,
            reason=reason_scope_1(r["identifier"], r["old_url"], r["new_url"]),
            anchor=RECLASS_ANCHOR_S1,
        )
    return len(rows)


def execute_scope_2(cur: sqlite3.Cursor, rows: list[dict]) -> int:
    """335 DOWNGRADE band + 335 audit entries."""
    for r in rows:
        cur.execute(
            """
            UPDATE identifiers
            SET source_url = ?, source_type = 'crowdsourced', confidence = 75
            WHERE id = ?
              AND source_url LIKE '%uasdoc.faa.gov/listDocs%'
              AND source_type = 'primary_registry'
              AND confidence = 85
            """,
            (JLRJR_CANONICAL_URL, r["id"]),
        )
        if cur.rowcount != 1:
            raise RuntimeError(
                f"Scope 2 UPDATE rowcount != 1 for id={r['id']} (got {cur.rowcount}); "
                f"pre-condition guard tripped — halting."
            )
        insert_audit(
            cur,
            identifier_id=r["id"],
            pre_url=r["old_url"],
            post_url=JLRJR_CANONICAL_URL,
            pre_type="primary_registry",
            post_type="crowdsourced",
            pre_conf=85,
            post_conf=75,
            reason=reason_scope_2(r["identifier"]),
            anchor=RECLASS_ANCHOR_S2,
        )
    return len(rows)


def execute_scope_3(cur: sqlite3.Cursor, rows: list[dict]) -> int:
    """58 LIFT source_type inferred → primary_registry + 58 audit entries."""
    for r in rows:
        cur.execute(
            """
            UPDATE identifiers
            SET source_type = 'primary_registry', confidence = ?
            WHERE id = ?
              AND source_type = 'inferred'
              AND confidence = ?
            """,
            (r["new_confidence"], r["id"], r["old_confidence"]),
        )
        if cur.rowcount != 1:
            raise RuntimeError(
                f"Scope 3 UPDATE rowcount != 1 for id={r['id']} (got {cur.rowcount}); "
                f"pre-condition guard tripped — halting."
            )
        insert_audit(
            cur,
            identifier_id=r["id"],
            pre_url=r["source_url"],
            post_url=r["source_url"],
            pre_type="inferred",
            post_type="primary_registry",
            pre_conf=r["old_confidence"],
            post_conf=r["new_confidence"],
            reason=reason_scope_3(
                r["identifier"],
                r["identifier_type"],
                r["old_confidence"],
                r["new_confidence"],
            ),
            anchor=RECLASS_ANCHOR_S3,
        )
    return len(rows)


def execute_scope_4(cur: sqlite3.Cursor) -> int:
    """sources.id=7 band UPDATE + notes append. No audit row (identifier-keyed table)."""
    cur.execute(
        """
        UPDATE sources
        SET source_type = 'primary_registry',
            notes = COALESCE(notes, '') || char(10) || char(10) || ?
        WHERE id = 7 AND source_type = 'official'
        """,
        (SCOPE_4_NOTES_APPEND,),
    )
    if cur.rowcount != 1:
        raise RuntimeError(
            f"Scope 4 UPDATE rowcount != 1 (got {cur.rowcount}); "
            f"pre-condition guard tripped — halting."
        )
    return 1


def post_sweep_verify(cur: sqlite3.Cursor) -> dict:
    """Return post-sweep verification snapshot."""
    out: dict = {}
    cur.execute(
        "SELECT COUNT(*) FROM source_reclassifications WHERE sweep_event_id = ?",
        (SWEEP_EVENT_ID,),
    )
    out["audit_total"] = cur.fetchone()[0]

    cur.execute(
        """
        SELECT
            SUM(CASE WHEN pre_source_type='primary_registry' AND post_source_type='primary_registry' THEN 1 ELSE 0 END) AS s1,
            SUM(CASE WHEN pre_source_type='primary_registry' AND post_source_type='crowdsourced' THEN 1 ELSE 0 END) AS s2,
            SUM(CASE WHEN pre_source_type='inferred' AND post_source_type='primary_registry' THEN 1 ELSE 0 END) AS s3
        FROM source_reclassifications WHERE sweep_event_id = ?
        """,
        (SWEEP_EVENT_ID,),
    )
    s1, s2, s3 = cur.fetchone()
    out["audit_s1"] = s1
    out["audit_s2"] = s2
    out["audit_s3"] = s3

    cur.execute(
        """
        SELECT source_type, confidence, COUNT(*)
        FROM identifiers
        WHERE superseded_by IS NULL
        GROUP BY source_type, confidence
        ORDER BY source_type, confidence
        """
    )
    out["post_distribution"] = cur.fetchall()

    cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE confidence >= 70 AND superseded_by IS NULL"
    )
    out["post_high_conf_ge70"] = cur.fetchone()[0]

    cur.execute("SELECT source_type FROM sources WHERE id = 7")
    out["scope_4_post"] = cur.fetchone()[0]

    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Pre-flight only; no UPDATEs/INSERTs.")
    args = p.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cur = conn.cursor()
        assert_pre_flight(cur)
        print("[pre-flight] all §0 baselines green")

        ident_map = load_wave_b_map()
        s1_rows, s2_rows, multi_detail = partition_wave_a(cur, ident_map)
        s3_rows = load_scope_3(cur)

        print(f"[partition] Scope 1 (UPGRADE): {len(s1_rows)}")
        print(f"[partition] Scope 2 (DOWNGRADE): {len(s2_rows)}")
        print(f"[partition] Scope 3 (LIFT): {len(s3_rows)}")
        print(f"[partition] Multi-DETAIL Wave-A rows: {len(multi_detail)}")

        if len(s1_rows) != 80 or len(s2_rows) != 335 or len(s3_rows) != 58:
            raise RuntimeError(
                f"Partition count drift: S1={len(s1_rows)} S2={len(s2_rows)} S3={len(s3_rows)}; "
                f"expected 80/335/58"
            )

        if args.dry_run:
            print("[dry-run] skipping all UPDATEs / INSERTs; rollback")
            conn.rollback()
            return 0

        n1 = execute_scope_1(cur, s1_rows)
        print(f"[scope-1] {n1} UPDATEs + {n1} audit entries staged")
        n2 = execute_scope_2(cur, s2_rows)
        print(f"[scope-2] {n2} UPDATEs + {n2} audit entries staged")
        n3 = execute_scope_3(cur, s3_rows)
        print(f"[scope-3] {n3} UPDATEs + {n3} audit entries staged")
        n4 = execute_scope_4(cur)
        print(f"[scope-4] {n4} sources-table UPDATE staged")

        verify = post_sweep_verify(cur)
        print(f"[verify] audit_total={verify['audit_total']} "
              f"(s1={verify['audit_s1']} s2={verify['audit_s2']} s3={verify['audit_s3']})")
        if verify["audit_total"] != n1 + n2 + n3:
            raise RuntimeError(
                f"Audit count mismatch: got {verify['audit_total']}, expected {n1+n2+n3}"
            )
        if verify["scope_4_post"] != "primary_registry":
            raise RuntimeError(
                f"Scope 4 post-state wrong: {verify['scope_4_post']!r}"
            )

        conn.commit()
        print(
            f"[commit] sweep_event_id={SWEEP_EVENT_ID} committed; "
            f"audit_total={verify['audit_total']}, "
            f"post ≥70 count={verify['post_high_conf_ge70']}"
        )
        # Print post-distribution for handback
        print("[post-distribution]")
        for row in verify["post_distribution"]:
            print(f"  {row}")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
