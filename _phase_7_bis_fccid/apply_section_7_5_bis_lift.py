"""
MAC-201 §7.5-bis 14-row 75→85 lift — applies the CP32-pending structural-anchor
sub-rule (anchor_conf=80) ratified by CEO at MAC-201 comment 2af00858.

Sub-rule (paste-not-cite from ratification):
  When a §8.3 lift candidate is corroborated by a primary-registry structural
  anchor (registry table with code + canonical-name but no behavioral
  attestation), the anchor enters §8.3 at anchor_conf=80 (mid-band
  primary_registry). Behavioral attestation enters at anchor_conf=85
  (top-of-band). Formula: §8.3 = min(99, max(75, anchor_conf) + 5).

  Structural anchor here = fcc_grantees (sid=7) holding (grantee_code,
  grantee_name) pairs for all 14 candidates → anchor_conf=80 → lift 75 → 85.

14 codes (no behavioral attestation today):
  ABY, ABZ, ARQ, MKM (Motorola Solutions);
  N7N, LL9, PNF, QQL, TWV (Sierra Wireless);
  EL5, NK7 (Harris); UXX (Cradlepoint); X4G (Axon); YJV (WatchGuard).

3 codes excluded (no fcc_grantees anchor): 2AG, 2AH, 2AL — stay at 75.
0 lifts on equipment_class_code (no structural anchor table).

Idempotent: WHERE confidence=75 guard prevents double-application.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "argus.db"

LIFT_CANDIDATES = (
    "ABY", "ABZ", "ARQ", "MKM",
    "N7N", "LL9", "PNF", "QQL", "TWV",
    "EL5", "NK7", "UXX", "X4G", "YJV",
)


def apply_lift(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in LIFT_CANDIDATES)
    sql = f"""
        UPDATE identifiers
        SET confidence = 85,
            notes = json_set(
              COALESCE(notes, '{{}}'),
              '$.section_8_3_lift', json_object(
                'lift_at_utc',         CURRENT_TIMESTAMP,
                'pre_conf',            75,
                'post_conf',           85,
                'anchor_table',        'fcc_grantees',
                'anchor_source_id',    7,
                'anchor_grantee_code', identifier,
                'anchor_grantee_name', (
                  SELECT grantee_name FROM fcc_grantees
                  WHERE grantee_code = identifiers.identifier LIMIT 1
                ),
                'sub_rule',            'structural_anchor (anchor_conf=80)',
                'cp_anchor',           'CP32-pending',
                'ratification_issue',  'MAC-201',
                'precedent_class',     'first_section_7_5_bis_lift'
              )
            )
        WHERE identifier_type = 'fcc_grantee_code'
          AND identifier IN ({placeholders})
          AND confidence = 75
          AND superseded_by IS NULL
    """
    cur.execute(sql, LIFT_CANDIDATES)
    return cur.rowcount


def verify(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    cur.execute(
        "SELECT identifier, confidence FROM identifiers "
        "WHERE identifier_type='fcc_grantee_code' AND superseded_by IS NULL "
        "ORDER BY confidence DESC, identifier"
    )
    rows = cur.fetchall()
    n85 = sum(1 for _, c in rows if c == 85)
    n75 = sum(1 for _, c in rows if c == 75)

    cur.execute(
        "SELECT COUNT(*) FROM identifiers "
        "WHERE identifier_type='fcc_grantee_code' AND confidence=85 "
        "AND superseded_by IS NULL "
        "AND json_extract(notes,'$.section_8_3_lift.anchor_table')='fcc_grantees'"
    )
    audited = cur.fetchone()[0]

    return {"rows": rows, "n85": n85, "n75": n75, "audited": audited}


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("BEGIN")
        updated = apply_lift(conn)
        result = verify(conn)
        assert result["n85"] == 14, f"expected 14 @ 85, got {result['n85']}"
        assert result["n75"] == 3, f"expected 3 @ 75, got {result['n75']}"
        assert result["audited"] == 14, f"expected 14 audited, got {result['audited']}"
        conn.commit()
        print(json.dumps({
            "updated": updated,
            "n85_post": result["n85"],
            "n75_post": result["n75"],
            "audited_post": result["audited"],
            "rows": result["rows"],
        }, indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
