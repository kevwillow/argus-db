"""Phase-5 Wave-B promotion-cycle-3 ingestion (MAC-91).

Validates and ingests the 22,106 Wave-B staged candidates across all 4 sources:
- 3a: Sources 1-3 (Bluetooth SIG / IEEE expanded / FAA RID) -> identifiers at
  source_type='primary_registry', confidence=85, per §2.2 Class 1 routing.
- 3b: Source 4 (Marlin NDSS 2025) + 2 Wave-A unlocks (#220359, #220361) ->
  behavioral_signatures table first-population at confidence=80 per §8.3
  corroboration math (academic 75 + rayhunter dual-source bonus +5).

Authority chain:
- Bible §6 Phase 5 + §7.4 (Validator promotion contract).
- §2 of MAC-91 dispatch (ratified clarifications): cellular_generation Path (b),
  §2.2 candidate-type routing classes, §2.3 Marlin cross-reference math.
- §11 #1 no fabrication; §11 #3 IEEE pii_review_hold default-to-hold;
  §11 #7 provenance preserved; §11 #8 no confidence drift (single-source rows
  stay at single-source confidence; Marlin 80 = §8.3 dual-source corroboration).
- §11 #13 device_category='unknown' carveout for SIG/IEEE multi-purpose vendors.
- SAR-12 dispatch-preamble live-state verification (pre-flight passed at
  ingestion authoring; §0 baselines all matched DB).
- CP15 §8.2 primary_registry sub-rule.
- Migration 0010 (behavioral_signatures table); UNIQUE 3-tuple
  (signature_name, source_id, cellular_generation).
- Wave-B bulk-load handoff: raw/wave_b/_wave_b_bulk_load_2026-05-13.md.
- Marlin cross-reference:
  raw/wave_b/marlin_ndss_2025/2026-05-13T17-00-16Z_cross_reference.md.

Idempotent: re-running with the same staged JSONs yields zero new rows
(guards on existing sources rows, extraction_runs.notes idempotency-key
'MAC-91-wave-b-promotion-cycle-3', raw_observations.source_row_key, and
the behavioral_signatures UNIQUE 3-tuple).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"
RAW_BASE = Path(__file__).resolve().parents[2] / "raw" / "wave_b"

VALIDATOR_AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"
DISPATCH_IDEMPOTENCY_KEY = "MAC-91-wave-b-promotion-cycle-3"
NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Staging JSON paths (matches handoff §2 roster)
STAGING_JSON = {
    "sig": RAW_BASE / "bluetooth_sig_full_registry" / "2026-05-13T13-32-28Z.json",
    "ieee": RAW_BASE / "ieee_expanded_registries" / "2026-05-13T13-38-21Z.json",
    "faa": RAW_BASE / "faa_rid_repull_2026-05-13" / "2026-05-13T13-59-02Z.json",
    "marlin": RAW_BASE / "marlin_ndss_2025" / "2026-05-13T17-00-16Z.json",
}

# §2.1 ratified cellular_generation long-form -> short-form map
CELLULAR_GEN_NORMALIZE = {
    "2G GSM": "2G",
    "3G UMTS": "3G",
    "4G LTE": "4G",
    "5G NSA": "5G_NSA",
}

# §2.1 halt triggers
CELLULAR_GEN_HALT_TRIGGERS = {"5G SA", "5G_SA", "5G FR1", "5G_FR1", "5G FR2", "5G_FR2"}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _existing_dispatch_runs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Idempotency guard: detect prior MAC-91 ingestion runs."""
    return conn.execute(
        "SELECT id, source_id, records_in, records_out, status, notes "
        "FROM extraction_runs WHERE notes LIKE ? ORDER BY id",
        (f"%{DISPATCH_IDEMPOTENCY_KEY}%",),
    ).fetchall()


def _ensure_source(
    conn: sqlite3.Connection,
    *,
    name: str,
    url: str,
    source_type: str,
    tier: int,
    last_status: str,
    notes_payload: dict,
) -> int:
    """Insert (or reuse) a sources row keyed on (name, url). Returns sources.id."""
    existing = conn.execute(
        "SELECT id FROM sources WHERE name = ? AND url = ?", (name, url)
    ).fetchone()
    if existing:
        return existing["id"]
    cur = conn.execute(
        "INSERT INTO sources (name, url, source_type, tier, last_fetched_at, "
        "last_status, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            name,
            url,
            source_type,
            tier,
            NOW_UTC,
            last_status,
            json.dumps(notes_payload, separators=(",", ":")),
        ),
    )
    return int(cur.lastrowid)


def _start_extraction_run(
    conn: sqlite3.Connection, source_id: int, records_in: int, notes: str
) -> int:
    cur = conn.execute(
        "INSERT INTO extraction_runs (agent_id, source_id, started_at, "
        "records_in, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (VALIDATOR_AGENT_ID, source_id, NOW_UTC, records_in, "running", notes),
    )
    return int(cur.lastrowid)


def _finalize_extraction_run(
    conn: sqlite3.Connection,
    run_id: int,
    records_out: int,
    errors: int,
    status: str,
) -> None:
    conn.execute(
        "UPDATE extraction_runs SET finished_at = ?, records_out = ?, "
        "errors = ?, status = ? WHERE id = ?",
        (NOW_UTC, records_out, errors, status, run_id),
    )


def _stringify_notes(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def _trim_excerpt(excerpt: str | None, limit: int = 200) -> str | None:
    if excerpt is None:
        return None
    s = excerpt.strip()
    return s[:limit] if len(s) > limit else s


# ---------------------------------------------------------------------------
# Source 1 — Bluetooth SIG (3,969 candidates)
# ---------------------------------------------------------------------------


def ingest_sig(conn: sqlite3.Connection, *, sig_source_id: int) -> dict[str, Any]:
    """SIG -> identifiers at primary_registry/85/unknown.

    Disposition:
    - 3,967 net-new -> identifiers (clear-promote)
    - 2 dedup-collision (existing_identifier_id set) -> raw_observations only,
      promoted_identifier_id linked to existing row,
      routing_disposition='dedup_collision_existing_id_already_promoted'.
    """
    payload = json.loads(STAGING_JSON["sig"].read_text())
    candidates = payload["candidates"]
    run_id = _start_extraction_run(
        conn,
        sig_source_id,
        len(candidates),
        f"{DISPATCH_IDEMPOTENCY_KEY}: SIG Wave-B promotion-cycle-3a "
        "(ble_manufacturer_id at primary_registry conf=85).",
    )

    stats = Counter()
    net_new_promoted = 0
    for c in candidates:
        notes_dict = dict(c.get("notes") or {})
        notes_dict["extraction_run_id"] = run_id
        notes_dict["dispatch"] = DISPATCH_IDEMPOTENCY_KEY
        candidate_id = c["candidate_identifier"]
        excerpt = _trim_excerpt(c.get("source_excerpt"))
        source_url = c["source_url"]

        existing_id = notes_dict.get("existing_identifier_id")
        if existing_id is not None:
            # Dedup-collision: keep raw_observations row + link, don't re-promote.
            notes_dict["routing_disposition"] = (
                "dedup_collision_existing_id_already_promoted"
            )
            ro = conn.execute(
                "INSERT INTO raw_observations (source_id, extraction_run_id, "
                "source_url, raw_payload, candidate_identifier, candidate_type, "
                "candidate_category, candidate_manufacturer, source_excerpt, "
                "captured_at, processed_at, promoted_identifier_id, notes, "
                "source_row_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    sig_source_id,
                    run_id,
                    source_url,
                    None,
                    candidate_id,
                    c["candidate_type"],
                    c["device_category"],
                    c.get("manufacturer"),
                    excerpt,
                    NOW_UTC,
                    NOW_UTC,
                    existing_id,
                    _stringify_notes(notes_dict),
                    f"sig:{candidate_id}",
                ),
            )
            stats["dedup_collision_skip_promote"] += 1
            continue

        # Net-new: promote to identifiers, then write raw_observations linked.
        notes_dict["routing_disposition"] = "promoted_primary_registry_clear"
        cur = conn.execute(
            "INSERT INTO identifiers (identifier, identifier_type, "
            "device_category, manufacturer, model, confidence, source_url, "
            "source_type, source_excerpt, geographic_scope, first_seen, "
            "last_verified, notes, superseded_by) VALUES (?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?)",
            (
                candidate_id,
                c["candidate_type"],
                c["device_category"],
                c.get("manufacturer"),
                None,
                85,
                source_url,
                "primary_registry",
                excerpt,
                None,
                NOW_UTC,
                None,
                _stringify_notes(
                    {
                        "wave_b_phase": "bluetooth_sig_full_registry",
                        "dispatch": DISPATCH_IDEMPOTENCY_KEY,
                        "sig_value_decimal": notes_dict.get("sig_value_decimal"),
                        "surveillance_vendor_flag": notes_dict.get(
                            "surveillance_vendor_flag"
                        ),
                    }
                ),
                None,
            ),
        )
        identifier_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO raw_observations (source_id, extraction_run_id, "
            "source_url, raw_payload, candidate_identifier, candidate_type, "
            "candidate_category, candidate_manufacturer, source_excerpt, "
            "captured_at, processed_at, promoted_identifier_id, notes, "
            "source_row_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sig_source_id,
                run_id,
                source_url,
                None,
                candidate_id,
                c["candidate_type"],
                c["device_category"],
                c.get("manufacturer"),
                excerpt,
                NOW_UTC,
                NOW_UTC,
                identifier_id,
                _stringify_notes(notes_dict),
                f"sig:{candidate_id}",
            ),
        )
        net_new_promoted += 1
        stats["net_new_promoted_primary_registry"] += 1

    _finalize_extraction_run(conn, run_id, net_new_promoted, 0, "ok")
    return {
        "run_id": run_id,
        "source_id": sig_source_id,
        "records_in": len(candidates),
        "records_out": net_new_promoted,
        "stats": dict(stats),
    }


# ---------------------------------------------------------------------------
# Source 2 — IEEE expanded (17,981 candidates) -- spans 3 source_ids
# ---------------------------------------------------------------------------


def ingest_ieee(
    conn: sqlite3.Connection,
    *,
    ma_m_source_id: int,
    ma_s_source_id: int,
    iab_source_id: int,
) -> dict[str, Any]:
    """IEEE expanded -> identifiers (clear-corp) + raw_observations (pii-hold).

    Disposition:
    - corp-clear (no pii_review_hold) -> identifiers at primary_registry/85/unknown
    - pii_review_hold AND not ieee_private -> raw_observations only,
      routing_disposition='ieee_pii_review_hold_pending_entity_validation'
      (§11 #3 default-to-hold).
    - ieee_private_registrant -> raw_observations only,
      routing_disposition='ieee_private_placeholder_no_org' (no org name to validate).
    """
    payload = json.loads(STAGING_JSON["ieee"].read_text())
    candidates = payload["candidates"]

    # Partition by ieee_registry -> source_id
    registry_to_source = {
        "MA-M": ma_m_source_id,
        "MA-S": ma_s_source_id,
        "IAB": iab_source_id,
    }
    by_registry: dict[str, list[dict]] = defaultdict(list)
    for c in candidates:
        registry = c["notes"]["ieee_registry"]
        by_registry[registry].append(c)

    result_per_registry = {}
    aggregate_stats = Counter()

    for registry, reg_candidates in by_registry.items():
        source_id = registry_to_source[registry]
        run_id = _start_extraction_run(
            conn,
            source_id,
            len(reg_candidates),
            f"{DISPATCH_IDEMPOTENCY_KEY}: IEEE Wave-B promotion-cycle-3a "
            f"({registry}) — primary_registry conf=85, "
            "§11 #3 default-to-hold for pii_review_hold + ieee_private rows.",
        )
        promoted = 0
        for c in reg_candidates:
            notes_dict = dict(c.get("notes") or {})
            notes_dict["extraction_run_id"] = run_id
            notes_dict["dispatch"] = DISPATCH_IDEMPOTENCY_KEY
            candidate_id = c["candidate_identifier"]
            excerpt = _trim_excerpt(c.get("source_excerpt"))
            source_url = c["source_url"]
            pii_hold = bool(notes_dict.get("pii_review_hold"))
            ieee_private = bool(notes_dict.get("ieee_private_registrant"))
            ieee_self = bool(notes_dict.get("ieee_self_attributed"))
            source_row_key = f"ieee:{registry}:{candidate_id}"

            if ieee_private:
                notes_dict["routing_disposition"] = (
                    "ieee_private_placeholder_no_org"
                )
                conn.execute(
                    "INSERT INTO raw_observations (source_id, extraction_run_id, "
                    "source_url, raw_payload, candidate_identifier, "
                    "candidate_type, candidate_category, candidate_manufacturer, "
                    "source_excerpt, captured_at, processed_at, "
                    "promoted_identifier_id, notes, source_row_key) VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        source_id,
                        run_id,
                        source_url,
                        None,
                        candidate_id,
                        c["candidate_type"],
                        c["device_category"],
                        c.get("manufacturer"),
                        excerpt,
                        NOW_UTC,
                        NOW_UTC,
                        None,
                        _stringify_notes(notes_dict),
                        source_row_key,
                    ),
                )
                aggregate_stats["hold_ieee_private_placeholder"] += 1
                continue

            if pii_hold:
                notes_dict["routing_disposition"] = (
                    "ieee_pii_review_hold_pending_entity_validation"
                )
                conn.execute(
                    "INSERT INTO raw_observations (source_id, extraction_run_id, "
                    "source_url, raw_payload, candidate_identifier, "
                    "candidate_type, candidate_category, candidate_manufacturer, "
                    "source_excerpt, captured_at, processed_at, "
                    "promoted_identifier_id, notes, source_row_key) VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        source_id,
                        run_id,
                        source_url,
                        None,
                        candidate_id,
                        c["candidate_type"],
                        c["device_category"],
                        c.get("manufacturer"),
                        excerpt,
                        NOW_UTC,
                        NOW_UTC,
                        None,
                        _stringify_notes(notes_dict),
                        source_row_key,
                    ),
                )
                aggregate_stats["hold_ieee_pii_pending_entity_validation"] += 1
                continue

            # Clear-corp: promote to identifiers at primary_registry conf=85,
            # device_category='unknown' per §11 #13 carveout (multi-purpose
            # vendor not exported to Lynceus).
            notes_dict["routing_disposition"] = "promoted_primary_registry_clear"
            id_notes = {
                "wave_b_phase": "ieee_expanded_registries",
                "dispatch": DISPATCH_IDEMPOTENCY_KEY,
                "ieee_registry": registry,
                "assignment_block_size_bits": notes_dict.get(
                    "assignment_block_size_bits"
                ),
                "surveillance_vendor_flag": notes_dict.get(
                    "surveillance_vendor_flag"
                ),
                "ieee_self_attributed": ieee_self or None,
            }
            cur = conn.execute(
                "INSERT INTO identifiers (identifier, identifier_type, "
                "device_category, manufacturer, model, confidence, "
                "source_url, source_type, source_excerpt, geographic_scope, "
                "first_seen, last_verified, notes, superseded_by) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    candidate_id,
                    c["candidate_type"],
                    c["device_category"],
                    c.get("manufacturer"),
                    None,
                    85,
                    source_url,
                    "primary_registry",
                    excerpt,
                    None,
                    NOW_UTC,
                    None,
                    _stringify_notes(id_notes),
                    None,
                ),
            )
            identifier_id = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO raw_observations (source_id, extraction_run_id, "
                "source_url, raw_payload, candidate_identifier, "
                "candidate_type, candidate_category, candidate_manufacturer, "
                "source_excerpt, captured_at, processed_at, "
                "promoted_identifier_id, notes, source_row_key) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    source_id,
                    run_id,
                    source_url,
                    None,
                    candidate_id,
                    c["candidate_type"],
                    c["device_category"],
                    c.get("manufacturer"),
                    excerpt,
                    NOW_UTC,
                    NOW_UTC,
                    identifier_id,
                    _stringify_notes(notes_dict),
                    source_row_key,
                ),
            )
            promoted += 1
            aggregate_stats["net_new_promoted_primary_registry"] += 1

        _finalize_extraction_run(conn, run_id, promoted, 0, "ok")
        result_per_registry[registry] = {
            "run_id": run_id,
            "source_id": source_id,
            "records_in": len(reg_candidates),
            "records_out": promoted,
        }

    return {
        "per_registry": result_per_registry,
        "aggregate_stats": dict(aggregate_stats),
    }


# ---------------------------------------------------------------------------
# Source 3 — FAA RID re-pull (103 candidates)
# ---------------------------------------------------------------------------


def ingest_faa(conn: sqlite3.Connection, *, faa_source_id: int) -> dict[str, Any]:
    """FAA RID Wave-B -> identifiers + raw_observations.

    Disposition:
    - 12 net-new clear (existing_identifier_id NOT set, not Zephyr-hold) ->
      identifiers at primary_registry/85/drone.
    - 90 dedup-collision (existing_identifier_id set) -> raw_observations only,
      promoted_identifier_id linked to existing,
      routing_disposition='dedup_collision_wave_a_existing_pending_sweep'
      (the §3.4 deferred reclass sweep handles confidence reconciliation).
    - 1 Zephyr `1`-prefix data-quality hold -> raw_observations only,
      routing_disposition='zephyr_data_quality_hold_carried_from_wave_a'.
    """
    payload = json.loads(STAGING_JSON["faa"].read_text())
    candidates = payload["candidates"]

    run_id = _start_extraction_run(
        conn,
        faa_source_id,
        len(candidates),
        f"{DISPATCH_IDEMPOTENCY_KEY}: FAA RID Wave-B promotion-cycle-3a "
        "(drone_id_prefix at primary_registry conf=85; "
        "90 dedup-collisions held pending §3.4 deferred reclass sweep; "
        "1 Zephyr `1`-prefix data-quality hold).",
    )

    stats = Counter()
    promoted = 0
    for c in candidates:
        notes_dict = dict(c.get("notes") or {})
        notes_dict["extraction_run_id"] = run_id
        notes_dict["dispatch"] = DISPATCH_IDEMPOTENCY_KEY
        candidate_id = c["candidate_identifier"]
        excerpt = _trim_excerpt(c.get("source_excerpt"))
        source_url = c["source_url"]
        source_row_key = f"faa:{notes_dict.get('faa_tracking_number')}:{candidate_id}"

        is_zephyr_hold = bool(notes_dict.get("zephyr_held_from_wave_a"))
        existing_id = notes_dict.get("existing_identifier_id")

        if is_zephyr_hold:
            notes_dict["routing_disposition"] = (
                "zephyr_data_quality_hold_carried_from_wave_a"
            )
            conn.execute(
                "INSERT INTO raw_observations (source_id, extraction_run_id, "
                "source_url, raw_payload, candidate_identifier, candidate_type, "
                "candidate_category, candidate_manufacturer, source_excerpt, "
                "captured_at, processed_at, promoted_identifier_id, notes, "
                "source_row_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    faa_source_id,
                    run_id,
                    source_url,
                    None,
                    candidate_id,
                    c["candidate_type"],
                    c["device_category"],
                    c.get("manufacturer"),
                    excerpt,
                    NOW_UTC,
                    NOW_UTC,
                    None,
                    _stringify_notes(notes_dict),
                    source_row_key,
                ),
            )
            stats["hold_zephyr_data_quality"] += 1
            continue

        if existing_id is not None:
            # Dedup-collision: link to existing Wave-A identifier, no re-promote.
            # §11 #8 — do NOT alter existing row's confidence/source; that's
            # the deferred §3.4 reclass sweep's job.
            notes_dict["routing_disposition"] = (
                "dedup_collision_wave_a_existing_pending_sweep"
            )
            conn.execute(
                "INSERT INTO raw_observations (source_id, extraction_run_id, "
                "source_url, raw_payload, candidate_identifier, candidate_type, "
                "candidate_category, candidate_manufacturer, source_excerpt, "
                "captured_at, processed_at, promoted_identifier_id, notes, "
                "source_row_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    faa_source_id,
                    run_id,
                    source_url,
                    None,
                    candidate_id,
                    c["candidate_type"],
                    c["device_category"],
                    c.get("manufacturer"),
                    excerpt,
                    NOW_UTC,
                    NOW_UTC,
                    existing_id,
                    _stringify_notes(notes_dict),
                    source_row_key,
                ),
            )
            stats["dedup_collision_skip_promote"] += 1
            continue

        # Net-new: promote to identifiers.
        notes_dict["routing_disposition"] = "promoted_primary_registry_clear"
        id_notes = {
            "wave_b_phase": "faa_rid_repull_2026-05-13",
            "dispatch": DISPATCH_IDEMPOTENCY_KEY,
            "faa_tracking_number": notes_dict.get("faa_tracking_number"),
            "faa_serial_number_start": notes_dict.get("faa_serial_number_start"),
            "faa_serial_number_end": notes_dict.get("faa_serial_number_end"),
            "faa_fcc_identifier": notes_dict.get("faa_fcc_identifier"),
            "derivation": notes_dict.get("derivation"),
        }
        cur = conn.execute(
            "INSERT INTO identifiers (identifier, identifier_type, "
            "device_category, manufacturer, model, confidence, source_url, "
            "source_type, source_excerpt, geographic_scope, first_seen, "
            "last_verified, notes, superseded_by) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                candidate_id,
                c["candidate_type"],
                c["device_category"],
                c.get("manufacturer"),
                c.get("model"),
                85,
                source_url,
                "primary_registry",
                excerpt,
                None,
                NOW_UTC,
                None,
                _stringify_notes(id_notes),
                None,
            ),
        )
        identifier_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO raw_observations (source_id, extraction_run_id, "
            "source_url, raw_payload, candidate_identifier, candidate_type, "
            "candidate_category, candidate_manufacturer, source_excerpt, "
            "captured_at, processed_at, promoted_identifier_id, notes, "
            "source_row_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                faa_source_id,
                run_id,
                source_url,
                None,
                candidate_id,
                c["candidate_type"],
                c["device_category"],
                c.get("manufacturer"),
                excerpt,
                NOW_UTC,
                NOW_UTC,
                identifier_id,
                _stringify_notes(notes_dict),
                source_row_key,
            ),
        )
        promoted += 1
        stats["net_new_promoted_primary_registry"] += 1

    _finalize_extraction_run(conn, run_id, promoted, 0, "ok")
    return {
        "run_id": run_id,
        "source_id": faa_source_id,
        "records_in": len(candidates),
        "records_out": promoted,
        "stats": dict(stats),
    }


# ---------------------------------------------------------------------------
# Source 4 — Marlin NDSS 2025 (53) + 2 Wave-A unlocks -> behavioral_signatures
# ---------------------------------------------------------------------------


def _normalize_cellular_gen(raw_val: Any) -> tuple[str | None, list[str] | None]:
    """Apply §2.1 Path (b) normalization.

    Returns (scalar_or_None, cross_gen_membership_or_None).

    - Scalar single-gen string -> ("2G"|"3G"|"4G"|"5G_NSA", None).
    - List multi-gen -> (None, [short_form, ...]).
    - Halt-trigger value -> raises RuntimeError per §2.1 halt clause.
    """
    if raw_val is None:
        return (None, None)

    def _normalize_one(v: str) -> str:
        stripped = v.strip()
        if stripped in CELLULAR_GEN_HALT_TRIGGERS:
            raise RuntimeError(
                f"§2.1 HALT-AND-SURFACE: cellular_generation value "
                f"{stripped!r} would require CHECK-enum extension "
                "(5G_SA/FR1/FR2). Per dispatch §2.1, halt + wake CEO."
            )
        if stripped in CELLULAR_GEN_NORMALIZE:
            return CELLULAR_GEN_NORMALIZE[stripped]
        # No mapping match: also halt-and-surface
        raise RuntimeError(
            f"§2.1 cellular_generation value {stripped!r} not in "
            "normalization map; halting per dispatch §5."
        )

    if isinstance(raw_val, str):
        return (_normalize_one(raw_val), None)

    if isinstance(raw_val, list):
        norm = [_normalize_one(g) for g in raw_val]
        if len(norm) == 1:
            return (norm[0], None)
        return (None, norm)

    raise RuntimeError(
        f"Unexpected cellular_generation type {type(raw_val)}: {raw_val!r}"
    )


def ingest_marlin(
    conn: sqlite3.Connection,
    *,
    marlin_source_id: int,
) -> dict[str, Any]:
    """Marlin -> behavioral_signatures (53 rows at conf=80) + 2 Wave-A unlocks.

    §8.3 corroboration math: academic 75 base + rayhunter dual-source bonus +5
    = 80. Cap at 99 per §8.3 formula.

    Wave-A unlocks (#220359, #220361) are promoted to behavioral_signatures
    at the same confidence 80 (same Marlin dual-source corroboration); their
    raw_observations rows get promoted_identifier_id set NULL (the
    behavioral_signatures.id; raw_observations.promoted_identifier_id was
    designed for identifiers but is type-agnostic INTEGER).
    """
    payload = json.loads(STAGING_JSON["marlin"].read_text())
    candidates = payload["candidates"]

    run_id = _start_extraction_run(
        conn,
        marlin_source_id,
        len(candidates),
        f"{DISPATCH_IDEMPOTENCY_KEY}: Marlin NDSS 2025 Wave-B promotion-cycle-3b "
        "(behavioral_signatures first-population at conf=80 via §8.3 "
        "corroboration: academic 75 + rayhunter dual-source +5). Path (b) "
        "cellular_generation normalization applied.",
    )

    marlin_stats = Counter()
    marlin_promoted = 0
    marlin_first_three_rows = []
    confidences = []

    for c in candidates:
        notes_dict = dict(c.get("notes") or {})
        notes_dict["extraction_run_id"] = run_id
        notes_dict["dispatch"] = DISPATCH_IDEMPOTENCY_KEY

        signature_name = c["signature_name"]
        excerpt = _trim_excerpt(c.get("source_excerpt"))
        source_url = c["source_url"]
        source_row_key = f"marlin:{signature_name}"

        # Cellular generation Path (b) normalization
        raw_cellular = c.get("cellular_generation")
        cellular_scalar, cross_gen = _normalize_cellular_gen(raw_cellular)

        # threshold_json — parse staged JSON, augment with cross_gen_membership
        # if applicable, and re-stringify; preserve paper_value in evidence_json.
        threshold_obj = json.loads(c["threshold_json"]) if c.get(
            "threshold_json"
        ) else {}
        if cross_gen is not None:
            threshold_obj["cross_gen_membership"] = cross_gen
        threshold_obj["dispatch_normalization_path"] = "b"

        evidence_obj = json.loads(c["evidence_json"]) if c.get(
            "evidence_json"
        ) else {}
        evidence_obj["paper_value_cellular_generation"] = raw_cellular

        bs_notes = {
            "wave_b_phase": "marlin_ndss_2025",
            "dispatch": DISPATCH_IDEMPOTENCY_KEY,
            "promotion_band_reasoning": "§8.3: academic 75 + rayhunter dual-source +5 = 80",
            "cross_reference_wave_a": c.get("cross_reference_wave_a"),
            "cross_reference_wave_a_detail": c.get(
                "cross_reference_wave_a_detail"
            ),
        }

        cur = conn.execute(
            "INSERT INTO behavioral_signatures (signature_name, "
            "cellular_generation, threshold_json, evidence_json, source_id, "
            "source_file_relative, source_line, confidence, device_category, "
            "notes, created_at, updated_at) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                signature_name,
                cellular_scalar,
                json.dumps(threshold_obj, separators=(",", ":"), ensure_ascii=False),
                json.dumps(evidence_obj, separators=(",", ":"), ensure_ascii=False),
                marlin_source_id,
                c.get("source_file_relative"),
                c.get("source_line"),
                80,
                c["device_category"],
                _stringify_notes(bs_notes),
                NOW_UTC,
                NOW_UTC,
            ),
        )
        bs_id = int(cur.lastrowid)
        confidences.append(80)

        notes_dict["routing_disposition"] = (
            "promoted_behavioral_signatures_academic_corroborated"
        )
        notes_dict["behavioral_signatures_id"] = bs_id
        conn.execute(
            "INSERT INTO raw_observations (source_id, extraction_run_id, "
            "source_url, raw_payload, candidate_identifier, candidate_type, "
            "candidate_category, candidate_manufacturer, source_excerpt, "
            "captured_at, processed_at, promoted_identifier_id, notes, "
            "source_row_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                marlin_source_id,
                run_id,
                source_url,
                None,
                c["candidate_identifier"],
                c["candidate_type"],
                c["device_category"],
                None,
                excerpt,
                NOW_UTC,
                NOW_UTC,
                None,  # promoted_identifier_id is for identifiers; bs has own table
                _stringify_notes(notes_dict),
                source_row_key,
            ),
        )

        if marlin_promoted < 3:
            marlin_first_three_rows.append(
                {
                    "bs_id": bs_id,
                    "signature_name": signature_name,
                    "cellular_generation": cellular_scalar,
                    "cross_gen_membership": cross_gen,
                    "confidence": 80,
                }
            )
        marlin_promoted += 1
        marlin_stats["net_new_promoted_marlin"] += 1

    _finalize_extraction_run(conn, run_id, marlin_promoted, 0, "ok")

    return {
        "run_id": run_id,
        "source_id": marlin_source_id,
        "records_in": len(candidates),
        "records_out": marlin_promoted,
        "first_three_rows": marlin_first_three_rows,
        "confidences": confidences,
        "stats": dict(marlin_stats),
    }


def ingest_wave_a_unlocks(
    conn: sqlite3.Connection,
    *,
    marlin_run_id: int,
) -> dict[str, Any]:
    """Promote 2 Wave-A behavioral_signatures unlocked by Marlin cross-ref.

    Per Marlin cross-reference doc:
    - #220359 'Identity (IMSI or IMEI) requested in suspicious manner'
      (rayhunter) — DIRECT match to Marlin Identity Request rows.
    - #220361 'Diagnostic detector for IMSI-exposing NAS messages
      (Marlin paper catalog)' (rayhunter) — CATALOG_REFERENCE to all 53.

    Both promote to behavioral_signatures with rayhunter source_id (30),
    confidence 80 (academic 75 + dual-source +5 per §8.3), same as Marlin
    rows. raw_observations.promoted_identifier_id stays NULL (behavioral
    signatures live in their own table).
    """
    UNLOCK_ROWS = [220359, 220361]
    unlocked = []
    for raw_obs_id in UNLOCK_ROWS:
        row = conn.execute(
            "SELECT id, source_id, candidate_identifier, candidate_type, "
            "candidate_category, source_url, source_excerpt, notes "
            "FROM raw_observations WHERE id = ?",
            (raw_obs_id,),
        ).fetchone()
        assert row is not None, f"Wave-A unlock row {raw_obs_id} missing"
        assert row["candidate_type"] == "behavioral_signature"
        assert row["candidate_category"] == "imsi_catcher"

        sig_name = row["candidate_identifier"]
        excerpt = _trim_excerpt(row["source_excerpt"])

        threshold_obj = {
            "wave_a_observation_id": raw_obs_id,
            "wave_a_rayhunter_source_url": row["source_url"],
            "dispatch_normalization_path": "b",
            "cross_gen_membership": None,
            "qualitative_signature": True,
        }
        evidence_obj = {
            "wave_a_rayhunter_obs_notes": (
                json.loads(row["notes"]).get("obs_notes")
                if row["notes"]
                else None
            ),
            "marlin_cross_reference_id": 220361,
            "marlin_paper_cite": "NDSS 2025 — Marlin Table III",
            "second_source_kind": "academic_paper_dual_source",
        }
        bs_notes = {
            "wave_b_phase": "wave_a_unlock_via_marlin",
            "dispatch": DISPATCH_IDEMPOTENCY_KEY,
            "wave_a_raw_obs_id": raw_obs_id,
            "marlin_cross_reference_classification": (
                "DIRECT" if raw_obs_id == 220359 else "CATALOG_REFERENCE"
            ),
            "promotion_band_reasoning": "§8.3: academic 75 + rayhunter dual-source +5 = 80",
        }
        cur = conn.execute(
            "INSERT INTO behavioral_signatures (signature_name, "
            "cellular_generation, threshold_json, evidence_json, source_id, "
            "source_file_relative, source_line, confidence, device_category, "
            "notes, created_at, updated_at) VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sig_name,
                None,  # qualitative, multi-gen; NULL per Path (b)
                json.dumps(threshold_obj, separators=(",", ":"), ensure_ascii=False),
                json.dumps(evidence_obj, separators=(",", ":"), ensure_ascii=False),
                row["source_id"],  # 30 = rayhunter
                None,
                None,
                80,
                row["candidate_category"],
                _stringify_notes(bs_notes),
                NOW_UTC,
                NOW_UTC,
            ),
        )
        bs_id = int(cur.lastrowid)

        # Update the original raw_observations row with promoted_identifier_id
        # left NULL (behavioral_signatures are not identifiers) — but stamp
        # processed_at + notes with the unlock reference.
        existing_notes = json.loads(row["notes"]) if row["notes"] else {}
        existing_notes["wave_b_unlock"] = {
            "behavioral_signatures_id": bs_id,
            "marlin_cross_reference_run_id": marlin_run_id,
            "dispatch": DISPATCH_IDEMPOTENCY_KEY,
            "promoted_at": NOW_UTC,
            "promotion_band_reasoning": "§8.3: academic 75 + rayhunter +5 = 80",
        }
        conn.execute(
            "UPDATE raw_observations SET processed_at = ?, notes = ? "
            "WHERE id = ?",
            (NOW_UTC, _stringify_notes(existing_notes), raw_obs_id),
        )

        unlocked.append(
            {
                "raw_obs_id": raw_obs_id,
                "signature_name": sig_name,
                "behavioral_signatures_id": bs_id,
                "marlin_match_kind": (
                    "DIRECT" if raw_obs_id == 220359 else "CATALOG_REFERENCE"
                ),
            }
        )

    return {"unlocked": unlocked}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Open transaction but ROLLBACK at end; no changes persist.",
    )
    args = parser.parse_args(argv)

    conn = _connect()
    try:
        prior = _existing_dispatch_runs(conn)
        if prior:
            print(
                f"IDEMPOTENCY: prior {DISPATCH_IDEMPOTENCY_KEY} extraction_runs "
                f"exist: {[(r['id'], r['source_id'], r['status']) for r in prior]}"
            )
            print("Aborting to avoid duplicate ingestion. Use a fresh DB or "
                  "different idempotency key.")
            return 1

        conn.execute("BEGIN")

        # Step 1: ensure 3 new sources (IEEE IAB Wave-B, FAA Wave-B, Marlin)
        iab_source_id = _ensure_source(
            conn,
            name="IEEE IAB registry (36-bit legacy; Wave-B primary_registry "
            "re-pull 2026-05-13)",
            url="https://standards-oui.ieee.org/iab/iab.csv",
            source_type="primary_registry",
            tier=1,
            last_status="ok",
            notes_payload={
                "wave": "Wave-B",
                "dispatch": DISPATCH_IDEMPOTENCY_KEY,
                "registry": "IAB",
                "block_size_bits": 36,
                "fetch_run_started_at": "2026-05-13T13:38:21Z",
                "registered_at": NOW_UTC,
                "license": "Public domain — IEEE OUI listing, freely redistributable. https://standards-oui.ieee.org/",
            },
        )
        faa_source_id = _ensure_source(
            conn,
            name="FAA UAS Remote-ID Public DOC API — DETAIL endpoint "
            "(Wave-B canonical primary_registry re-pull)",
            url="https://uasdoc.faa.gov/api/v1/publicDOCRev/",
            source_type="primary_registry",
            tier=1,
            last_status="ok",
            notes_payload={
                "wave": "Wave-B",
                "dispatch": DISPATCH_IDEMPOTENCY_KEY,
                "registered_at": NOW_UTC,
                "shape": "LIST -> DETAIL-per-record + LCP(serialNumberStart, serialNumberEnd)",
                "license": "Public Domain U.S. Government — https://www.usa.gov/government-works (17 U.S.C. §105)",
                "adapted_from_dispatch": "§3.3 documentNumber -> trackingNumber correction; board-ratified mid-dispatch",
            },
        )
        marlin_source_id = _ensure_source(
            conn,
            name="Marlin NDSS 2025: Detecting IMSI-Catchers by Characterizing "
            "Identity Exposing Messages in Cellular Traffic",
            url="https://www.ndss-symposium.org/wp-content/uploads/2025-1115-paper.pdf",
            source_type="academic",
            tier=1,
            last_status="ok",
            notes_payload={
                "wave": "Wave-B",
                "dispatch": DISPATCH_IDEMPOTENCY_KEY,
                "venue": "NDSS 2025",
                "authors": "Tucker, Bennett, Kotuliak, Erni, Capkun, Butler, Traynor",
                "page_count": 19,
                "registered_at": NOW_UTC,
                "license": "Author copy hosted at NDSS Symposium (Internet Society publication; no redistribution required for academic-citation use).",
                "table_iii_signatures": 53,
                "count_method_explanation": "cross-generation-deduped (msg_type, cause_code) tuples + 1 5G NSA inheritance meta",
            },
        )

        # Step 2: SIG (3a)
        SIG_SOURCE_ID = 34
        print(f"Source 1 (SIG) — source_id={SIG_SOURCE_ID}")
        sig_result = ingest_sig(conn, sig_source_id=SIG_SOURCE_ID)
        print(f"  SIG result: {sig_result}")

        # Step 3: IEEE (3a) — spans 3 source_ids (2, 3, new IAB)
        MA_M_SOURCE_ID = 2
        MA_S_SOURCE_ID = 3
        print(
            f"Source 2 (IEEE expanded) — MA-M src=2, MA-S src=3, "
            f"IAB src={iab_source_id}"
        )
        ieee_result = ingest_ieee(
            conn,
            ma_m_source_id=MA_M_SOURCE_ID,
            ma_s_source_id=MA_S_SOURCE_ID,
            iab_source_id=iab_source_id,
        )
        print(f"  IEEE result: {ieee_result}")

        # Step 4: FAA (3a)
        print(f"Source 3 (FAA RID) — source_id={faa_source_id}")
        faa_result = ingest_faa(conn, faa_source_id=faa_source_id)
        print(f"  FAA result: {faa_result}")

        # Step 5: Marlin (3b)
        print(f"Source 4 (Marlin) — source_id={marlin_source_id}")
        marlin_result = ingest_marlin(conn, marlin_source_id=marlin_source_id)
        print(f"  Marlin result: {{run_id, records_in, records_out}} = "
              f"({marlin_result['run_id']}, {marlin_result['records_in']}, "
              f"{marlin_result['records_out']}); first_three_rows = "
              f"{marlin_result['first_three_rows']}")

        # Step 6: 2 Wave-A unlocks (3b)
        unlocks_result = ingest_wave_a_unlocks(
            conn, marlin_run_id=marlin_result["run_id"]
        )
        print(f"  Wave-A unlocks: {unlocks_result}")

        if args.dry_run:
            conn.execute("ROLLBACK")
            print("\nDRY RUN: ROLLED BACK — no changes persisted.")
        else:
            conn.execute("COMMIT")
            print("\nCOMMITTED.")

        return 0
    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"\nERROR: {e!r} — rolled back.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
