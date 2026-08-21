"""MAC-101 Item A — multi-registry positive-evidence xcheck for Class B clearance.

Per CEO ratification (option β) at MAC-102 [`ad5a564d`](<TRACKER_URL>issues/MAC-102#comment-ad5a564d)
2026-05-14: re-triage the 75 ``individual_attributed_pii_sustain`` Class B
``raw_observations`` rows against ``manufacturers`` (§2.1 lexicon) +
``fcc_grantees.grantee_name`` (50,153 rows) for corporate-entity
confirmation. Matches promote to ``identifiers`` at conf=85,
``source_type='primary_registry'`` (CP15 single-source ceiling for IEEE-
anchored allocations). Non-matches sustain Class B; all 75 rows get
``notes.registry_xcheck_attempted=true`` (S.7 cumulative-full-enum
discipline).

Authority chain
---------------
- Bible §7.4 Validator contract — §7.4 check list applied row-wise.
- Bible §11 #3 — "uncertainty toward HOLD" remains binding; predicate is
  positive-evidence-only.
- Bible §11 #7 — provenance preserved (source_url + source_excerpt
  threaded into the promoted identifiers row).
- Bible §11 #8 — single-source rows stay at single-source 85; no
  confidence drift upward without corroboration. CP19 sub-rule scope
  bounds row-level reclassifications of EXISTING ``identifiers`` rows —
  this runner produces only INSERTs from ``raw_observations`` promotion,
  so no ``source_reclassifications`` audit entry binds.
- Bible §11 #13 — ``device_category='unknown'`` Lynceus-export carveout
  applies; high-conf export unaffected by these promotions.
- BIBLE_AMENDMENTS.md CP15 §8.2 ``primary_registry`` band — 85 single-
  source ceiling for IEEE allocations.
- BIBLE_AMENDMENTS.md SAR-9 — alias-iteration discipline preserved
  through :mod:`db.extraction.vendor_name_disambig`
  (``alias_equality`` predicate, once per canonical).
- BIBLE_AMENDMENTS.md SAR-12 dispatch-preamble live-state verification —
  baselines checked against DB at entry (75 / 22,266 / 34 / 50,153).
- MAC-99 Stream 1 promotion shape (``db/validation/mac99_ieee_pii_review_triage.py``) —
  identifiers row format mirrored verbatim for cross-dispatch consistency.

Idempotency
-----------
Two-pass guard:

1. ``extraction_runs.notes`` carries ``MAC-101-item-a`` idempotency key
   — re-running detects the prior dispatch and exits ``noop_idempotent``.
2. Per-row ``raw_observations.notes.registry_xcheck_attempted=true``
   marks every Class B row touched. A future predicate-refinement re-entry
   that wants to retry the SAME predicate version exits naturally on the
   extraction_runs guard. A future re-entry under a NEW predicate version
   would set a different idempotency key and re-process only rows whose
   ``registry_xcheck_attempted`` flag is absent (newly-staged Class B).

Single-transaction batch
------------------------
All ~N promotions + all 75 raw_observations updates land in a single
``BEGIN; ...; COMMIT;``. Mirror of MAC-99 Stream 1 batch pattern.
Rollback on any row-level exception.

CLI
---
``python3 -m db.validation.mac101_item_a_registry_xcheck`` to apply.
``--dry-run`` to classify only (no DB writes; full classification +
counts surfaced for surface-back).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from db.extraction.vendor_name_disambig import (
    REGISTRY_SOURCE_FCC_GRANTEES,
    REGISTRY_SOURCE_MANUFACTURERS,
    registry_xcheck_disposition,
)

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"

VALIDATOR_AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"
DISPATCH_IDEMPOTENCY_KEY = "MAC-101-item-a"
PARENT_DISPATCH = "MAC-91-wave-b-promotion-cycle-3"

# IEEE Wave-B first_seen — match the MAC-99 Stream 1 convention so the new
# promotions carry a consistent first_seen anchor with the rest of the
# Wave-B IEEE primary_registry cohort.
IEEE_WAVE_B_FIRST_SEEN = "2026-05-13T23:03:07Z"

NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# §0 live-state baselines (paste-verified at MAC-101 decomposition + MAC-102
# CEO ratification; SAR-12 §0 discipline).
EXPECTED_CLASS_B_COUNT = 75
EXPECTED_MANUFACTURERS_COUNT = 34
EXPECTED_FCC_GRANTEES_DISTINCT_MIN = 40_000  # 48,832 distinct grantees from 50,153 rows; allow drift below


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _existing_dispatch_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Idempotency guard: detect prior MAC-101 Item A run."""
    return conn.execute(
        "SELECT id, source_id, records_in, records_out, status, notes "
        "FROM extraction_runs WHERE notes LIKE ? ORDER BY id LIMIT 1",
        (f"%{DISPATCH_IDEMPOTENCY_KEY}%",),
    ).fetchone()


def _load_class_b_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Load the 75 Class B (individual_attributed_pii_sustain) rows."""
    return conn.execute(
        """
        SELECT id, source_id, source_url, candidate_identifier, candidate_type,
               candidate_manufacturer, source_excerpt, notes,
               promoted_identifier_id
        FROM raw_observations
        WHERE json_valid(notes)
          AND json_extract(notes,'$.pii_review_disposition')
              = 'individual_attributed_pii_sustain'
        ORDER BY id
        """
    ).fetchall()


def _load_manufacturers(conn: sqlite3.Connection) -> list[tuple[str, str | None]]:
    """Load the §2.1 lexicon rows.

    CP31 (migration 0025) — hub-only: §2.1 lexicon reflects the visible
    canonical set; arm rows are queried separately by FK when needed.
    """
    return [
        (r["canonical_name"], r["aliases"])
        for r in conn.execute(
            "SELECT canonical_name, aliases FROM manufacturers "
            "WHERE query_default = 'visible' "
            "ORDER BY id"
        )
    ]


def _load_fcc_grantee_names(conn: sqlite3.Connection) -> list[str]:
    """Load distinct ``fcc_grantees.grantee_name`` values."""
    return [
        r["grantee_name"]
        for r in conn.execute(
            "SELECT DISTINCT grantee_name FROM fcc_grantees "
            "WHERE grantee_name IS NOT NULL AND grantee_name != ''"
        )
    ]


def _parse_notes(notes_json: str | None) -> dict:
    if not notes_json:
        return {}
    try:
        return json.loads(notes_json)
    except json.JSONDecodeError:
        return {}


def classify_rows(
    rows: list[sqlite3.Row],
    manufacturers_rows: list[tuple[str, str | None]],
    fcc_grantee_names: list[str],
) -> list[dict]:
    """Apply the multi-registry xcheck predicate to each Class B row."""
    classifications: list[dict] = []
    for r in rows:
        notes = _parse_notes(r["notes"])
        match = registry_xcheck_disposition(
            r["candidate_manufacturer"],
            manufacturers_rows=manufacturers_rows,
            fcc_grantee_names=fcc_grantee_names,
        )
        classifications.append({
            "row_id": r["id"],
            "source_id": r["source_id"],
            "source_url": r["source_url"],
            "candidate_identifier": r["candidate_identifier"],
            "candidate_manufacturer": r["candidate_manufacturer"],
            "source_excerpt": r["source_excerpt"],
            "notes_obj": notes,
            "ieee_registry": notes.get("ieee_registry", ""),
            "assignment_hex": notes.get("ieee_assignment_raw_hex", ""),
            "extraction_run_id": notes.get("extraction_run_id"),
            "already_promoted": r["promoted_identifier_id"],
            "match": match,
        })
    return classifications


def run(
    *,
    dry_run: bool = False,
    db_path: Path | None = None,
) -> dict:
    """Execute the predicate sweep + Class A promotions."""
    if db_path is None:
        db_path = DB_PATH

    conn = _connect(db_path)
    try:
        existing = _existing_dispatch_run(conn)
        if existing is not None and not dry_run:
            return {
                "status": "noop_idempotent",
                "existing_run_id": existing["id"],
                "existing_run_notes": existing["notes"],
            }

        rows = _load_class_b_rows(conn)
        if len(rows) != EXPECTED_CLASS_B_COUNT:
            raise RuntimeError(
                f"Class B cohort drift: expected {EXPECTED_CLASS_B_COUNT} rows, "
                f"got {len(rows)}. SAR-12 §0 baseline-guard halt."
            )

        manufacturers_rows = _load_manufacturers(conn)
        if len(manufacturers_rows) != EXPECTED_MANUFACTURERS_COUNT:
            raise RuntimeError(
                f"manufacturers cohort drift: expected "
                f"{EXPECTED_MANUFACTURERS_COUNT}, got {len(manufacturers_rows)}."
            )

        fcc_grantee_names = _load_fcc_grantee_names(conn)
        if len(fcc_grantee_names) < EXPECTED_FCC_GRANTEES_DISTINCT_MIN:
            raise RuntimeError(
                f"fcc_grantees cohort under floor: expected "
                f"≥{EXPECTED_FCC_GRANTEES_DISTINCT_MIN} distinct grantee_name, "
                f"got {len(fcc_grantee_names)}."
            )

        classifications = classify_rows(
            rows, manufacturers_rows, fcc_grantee_names
        )

        # Count per-source + per-match-kind.
        per_source = Counter()
        per_match_kind = Counter()
        cleared_examples: list[dict] = []
        sustained_examples: list[dict] = []
        for c in classifications:
            if c["match"] is not None:
                per_source[c["match"]["match_source"]] += 1
                per_match_kind[c["match"]["match_kind"]] += 1
                if len(cleared_examples) < 10:
                    cleared_examples.append({
                        "row_id": c["row_id"],
                        "candidate": c["candidate_manufacturer"],
                        "match": c["match"],
                    })
            else:
                if len(sustained_examples) < 10:
                    sustained_examples.append({
                        "row_id": c["row_id"],
                        "candidate": c["candidate_manufacturer"],
                    })

        cleared_count = sum(per_source.values())
        sustained_count = len(classifications) - cleared_count

        if dry_run:
            return {
                "status": "dry_run",
                "class_b_total": len(classifications),
                "cleared_count": cleared_count,
                "sustained_count": sustained_count,
                "per_source": dict(per_source),
                "per_match_kind": dict(per_match_kind),
                "cleared_examples": cleared_examples,
                "sustained_examples": sustained_examples,
                "classifications": classifications,
            }

        # ------ APPLY: single transaction ------
        cur = conn.cursor()
        cur.execute("BEGIN")
        try:
            run_notes = json.dumps({
                "dispatch": DISPATCH_IDEMPOTENCY_KEY,
                "scope": (
                    "MAC-101 Item A multi-registry positive-evidence xcheck "
                    "for Class B clearance (manufacturers + fcc_grantees)"
                ),
                "class_b_total": len(classifications),
                "cleared_count": cleared_count,
                "sustained_count": sustained_count,
                "per_source": dict(per_source),
                "per_match_kind": dict(per_match_kind),
                "validator_agent_id": VALIDATOR_AGENT_ID,
                "validated_at": NOW_UTC,
                "predicate_module": (
                    "db.extraction.vendor_name_disambig.registry_xcheck_disposition"
                ),
                "procurement_records_skipped_reason": (
                    "CEO directive named procurement_records.recipient_name "
                    "(MAC-102 ad5a564d); actual column on d91b7b6 is "
                    "vendor_canonical_name. Gate #5 drop per ratification."
                ),
            }, separators=(",", ":"))
            cur.execute(
                """
                INSERT INTO extraction_runs
                  (agent_id, source_id, started_at, finished_at,
                   records_in, records_out, errors, status, notes)
                VALUES (?, NULL, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    VALIDATOR_AGENT_ID,
                    NOW_UTC,
                    NOW_UTC,
                    len(classifications),
                    cleared_count,
                    "ok",
                    run_notes,
                ),
            )
            extraction_run_id = cur.lastrowid

            promoted_count = 0
            sustained_count_actual = 0
            for c in classifications:
                notes_obj = c["notes_obj"]
                notes_obj["registry_xcheck_attempted"] = True
                notes_obj["registry_xcheck_dispatch"] = DISPATCH_IDEMPOTENCY_KEY
                notes_obj["registry_xcheck_validated_at"] = NOW_UTC

                if c["match"] is not None:
                    notes_obj["pii_review_disposition"] = (
                        "corporate_validated_via_registry_xcheck"
                    )
                    notes_obj["registry_xcheck_match"] = (
                        c["match"]["match_canonical"]
                    )
                    notes_obj["registry_xcheck_match_kind"] = (
                        c["match"]["match_kind"]
                    )
                    notes_obj["registry_xcheck_match_source"] = (
                        c["match"]["match_source"]
                    )

                    ident_notes = json.dumps({
                        "wave_b_phase": "ieee_expanded_registries",
                        "dispatch": DISPATCH_IDEMPOTENCY_KEY,
                        "parent_dispatch": PARENT_DISPATCH,
                        "ieee_registry": c["ieee_registry"],
                        "ieee_assignment_raw_hex": c["assignment_hex"],
                        "pii_review_disposition": (
                            "corporate_validated_via_registry_xcheck"
                        ),
                        "registry_xcheck_match": c["match"]["match_canonical"],
                        "registry_xcheck_match_kind": c["match"]["match_kind"],
                        "registry_xcheck_match_source": (
                            c["match"]["match_source"]
                        ),
                        "promoted_by": "MAC-101 Item A",
                        "source_runs": (
                            [c["extraction_run_id"]]
                            if c["extraction_run_id"] is not None
                            else []
                        ),
                        "raw_observation_id": c["row_id"],
                    }, separators=(",", ":"))
                    cur.execute(
                        """
                        INSERT INTO identifiers
                          (identifier, identifier_type, device_category,
                           manufacturer, model, confidence, source_url,
                           source_type, source_excerpt, geographic_scope,
                           first_seen, last_verified, notes)
                        VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            c["candidate_identifier"],
                            "mac_range",
                            "unknown",
                            c["candidate_manufacturer"],
                            85,
                            c["source_url"],
                            "primary_registry",
                            c["source_excerpt"],
                            "global",
                            IEEE_WAVE_B_FIRST_SEEN,
                            NOW_UTC,
                            ident_notes,
                        ),
                    )
                    new_ident_id = cur.lastrowid
                    cur.execute(
                        """
                        UPDATE raw_observations
                        SET notes = ?, promoted_identifier_id = ?,
                            processed_at = ?
                        WHERE id = ?
                        """,
                        (
                            json.dumps(notes_obj, separators=(",", ":")),
                            new_ident_id,
                            NOW_UTC,
                            c["row_id"],
                        ),
                    )
                    promoted_count += 1
                else:
                    # Sustain Class B — disposition unchanged; just mark
                    # attempted=true so S.7 self-check passes.
                    cur.execute(
                        """
                        UPDATE raw_observations
                        SET notes = ?, processed_at = ?
                        WHERE id = ?
                        """,
                        (
                            json.dumps(notes_obj, separators=(",", ":")),
                            NOW_UTC,
                            c["row_id"],
                        ),
                    )
                    sustained_count_actual += 1

            # S.7 cumulative-full-enum self-check inside the same transaction.
            unattempted = cur.execute(
                """
                SELECT COUNT(*) FROM raw_observations
                WHERE json_valid(notes)
                  AND json_extract(notes,'$.pii_review_disposition')
                      IN ('individual_attributed_pii_sustain',
                          'corporate_validated_via_registry_xcheck')
                  AND json_extract(notes,'$.registry_xcheck_attempted') IS NULL
                """
            ).fetchone()[0]
            if unattempted != 0:
                raise RuntimeError(
                    f"S.7 self-check failed: {unattempted} Class B rows "
                    f"lack registry_xcheck_attempted=true. Rolling back."
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise

        return {
            "status": "applied",
            "extraction_run_id": extraction_run_id,
            "class_b_total": len(classifications),
            "promoted_count": promoted_count,
            "sustained_count": sustained_count_actual,
            "per_source": dict(per_source),
            "per_match_kind": dict(per_match_kind),
            "cleared_examples": cleared_examples,
            "sustained_examples": sustained_examples,
            "classifications": classifications,
        }
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Classify only; no DB writes")
    ap.add_argument("--db", type=Path, default=None, help="Override DB path")
    args = ap.parse_args()

    result = run(dry_run=args.dry_run, db_path=args.db)
    print(f"status: {result['status']}")
    if result["status"] == "noop_idempotent":
        print(f"existing_run_id: {result['existing_run_id']}")
        return
    print(f"class_b_total:    {result['class_b_total']}")
    print(f"cleared_count:    {result.get('cleared_count', result.get('promoted_count'))}")
    print(f"sustained_count:  {result['sustained_count']}")
    print(f"per_source:       {result['per_source']}")
    print(f"per_match_kind:   {result['per_match_kind']}")
    if result["status"] == "applied":
        print(f"extraction_run_id: {result['extraction_run_id']}")
    print("cleared_examples:")
    for ex in result["cleared_examples"]:
        print(f"  {ex}")


if __name__ == "__main__":
    main()
