"""Tests for ``db/validation/dedup_pass.py`` — Phase-5 Step-5 orchestrator.

Coverage:
- Positive: cross-source corroboration uplifts confidence per §8.3.
- Negative: same-source cluster merges provenance + supersedes WITHOUT uplift
  per §11 #8 ("second independent source").
- Edge: MAC-within-OUI strict-subset detection drives a cluster.
- Hard rule: §8.2 ceiling breach halts the pass without writing.
- Hard rule: Wave-A (id=1) supersession halts the pass without writing.
- No-op: a clean active set (no clusters) returns zero mutations.
- Idempotency: a second run finds no clusters since losers carry
  ``superseded_by``.
- §11 #8 sentinel: same-source merge_cluster directly holds confidence
  at ``max(originals)`` instead of uplifting.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from db.dedup import IdentifierRow, merge_cluster
from db.validation.dedup_pass import (
    SOURCE_TYPE_CEILINGS,
    WAVE_A_CANONICAL_ID,
    run_dedup,
)


SCHEMA_DDL = """
CREATE TABLE identifiers (
  id INTEGER PRIMARY KEY,
  identifier TEXT NOT NULL,
  identifier_type TEXT NOT NULL,
  device_category TEXT,
  manufacturer TEXT,
  model TEXT,
  confidence INTEGER NOT NULL,
  source_url TEXT,
  source_type TEXT,
  source_excerpt TEXT,
  geographic_scope TEXT,
  first_seen DATETIME,
  last_verified DATETIME,
  notes TEXT,
  superseded_by INTEGER
);
CREATE TABLE raw_observations (
  id INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL,
  extraction_run_id INTEGER,
  source_url TEXT,
  raw_payload TEXT,
  candidate_identifier TEXT,
  candidate_type TEXT,
  candidate_category TEXT,
  candidate_manufacturer TEXT,
  source_excerpt TEXT,
  captured_at DATETIME,
  processed_at DATETIME,
  promoted_identifier_id INTEGER,
  notes TEXT,
  source_row_key TEXT
);
CREATE TABLE extraction_runs (
  id INTEGER PRIMARY KEY,
  agent_id TEXT,
  source_id INTEGER,
  started_at DATETIME,
  finished_at DATETIME,
  records_in INTEGER,
  records_out INTEGER,
  errors INTEGER,
  status TEXT,
  notes TEXT
);
"""


def _fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_DDL)
    return conn


def _ins_id(
    conn: sqlite3.Connection,
    *,
    id_: int,
    identifier: str,
    identifier_type: str,
    confidence: int,
    source_url: str,
    source_type: str,
    source_excerpt: str | None = None,
    notes: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO identifiers (id, identifier, identifier_type, confidence, "
        "source_url, source_type, source_excerpt, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (id_, identifier, identifier_type, confidence, source_url, source_type,
         source_excerpt, notes),
    )


def _ins_raw(
    conn: sqlite3.Connection,
    *,
    id_: int,
    source_id: int,
    promoted_identifier_id: int | None = None,
) -> None:
    conn.execute(
        "INSERT INTO raw_observations (id, source_id, promoted_identifier_id) "
        "VALUES (?, ?, ?)",
        (id_, source_id, promoted_identifier_id),
    )


# ─── Pure-module §11 #8 toggle ─────────────────────────────────────────────


def test_merge_cluster_same_source_holds_confidence():
    """§11 #8: when corroboration is NOT independent, hold at max(originals)."""
    a = IdentifierRow(id=1, identifier="aa:bb:cc", identifier_type="oui",
                      confidence=70, source_url="https://x/")
    b = IdentifierRow(id=2, identifier="aa:bb:cc", identifier_type="oui",
                      confidence=60, source_url="https://x/")
    result = merge_cluster([a, b], independent_corroboration=False)
    assert result.canonical.id == 1
    assert result.canonical.confidence == 70  # NO uplift
    assert result.superseded[0].id == 2
    assert result.superseded[0].superseded_by == 1
    # provenance still combined into notes
    assert result.canonical.notes is not None
    assert "merged_from_id=2" in result.canonical.notes


def test_merge_cluster_cross_source_uplifts_by_default():
    a = IdentifierRow(id=1, identifier="aa:bb:cc", identifier_type="oui",
                      confidence=70, source_url="https://x/")
    b = IdentifierRow(id=2, identifier="aa:bb:cc", identifier_type="oui",
                      confidence=60, source_url="https://y/")
    result = merge_cluster([a, b])  # default independent_corroboration=True
    assert result.canonical.confidence == 75  # min(99, 70 + 5)


# ─── Orchestrator: positive cross-source uplift ────────────────────────────


def test_dedup_pass_cross_source_corroboration_uplifts():
    conn = _fresh_conn()
    _ins_id(conn, id_=1, identifier="aa:bb:cc", identifier_type="oui",
            confidence=60, source_url="https://ieee/", source_type="regulatory")
    _ins_id(conn, id_=2, identifier="aa:bb:cc", identifier_type="oui",
            confidence=55, source_url="https://wireshark/", source_type="crowdsourced")
    _ins_raw(conn, id_=100, source_id=1, promoted_identifier_id=1)
    _ins_raw(conn, id_=101, source_id=4, promoted_identifier_id=2)
    conn.commit()

    report = run_dedup(conn, write_ledger=False)

    assert not report.halts
    assert report.clusters_detected == 1
    assert report.rows_superseded == 1
    assert report.rows_uplifted == 1
    assert report.rows_no_uplift_same_source == 0

    # Canonical is id=1 (higher conf), uplifted to 65 = min(99, 60+5)
    canonical = conn.execute(
        "SELECT confidence, superseded_by FROM identifiers WHERE id = 1"
    ).fetchone()
    assert canonical["confidence"] == 65
    assert canonical["superseded_by"] is None

    loser = conn.execute(
        "SELECT confidence, superseded_by FROM identifiers WHERE id = 2"
    ).fetchone()
    assert loser["superseded_by"] == 1


# ─── Orchestrator: negative same-source NO uplift ──────────────────────────


def test_dedup_pass_same_source_does_not_uplift():
    conn = _fresh_conn()
    _ins_id(conn, id_=1, identifier="aa:bb:cc", identifier_type="oui",
            confidence=50, source_url="https://ieee/", source_type="inferred")
    _ins_id(conn, id_=2, identifier="aa:bb:cc", identifier_type="oui",
            confidence=50, source_url="https://ieee/", source_type="inferred")
    # Both rows trace to source_id=1.
    _ins_raw(conn, id_=100, source_id=1, promoted_identifier_id=1)
    _ins_raw(conn, id_=101, source_id=1, promoted_identifier_id=2)
    conn.commit()

    report = run_dedup(conn, write_ledger=False)

    assert not report.halts
    assert report.clusters_detected == 1
    assert report.rows_superseded == 1
    assert report.rows_uplifted == 0
    assert report.rows_no_uplift_same_source == 1

    canonical = conn.execute(
        "SELECT confidence FROM identifiers WHERE id = 1"
    ).fetchone()
    assert canonical["confidence"] == 50  # held at max(originals), no uplift


# ─── Orchestrator: MAC-within-OUI strict-subset edge ───────────────────────


def test_dedup_pass_mac_within_oui_subset_clusters_and_uplifts():
    conn = _fresh_conn()
    # OUI-level inferred row + MAC-level crowdsourced row, different sources.
    _ins_id(conn, id_=1, identifier="aa:bb:cc:dd:ee:ff", identifier_type="mac",
            confidence=60, source_url="https://wigle/",
            source_type="crowdsourced")
    _ins_id(conn, id_=2, identifier="aa:bb:cc", identifier_type="oui",
            confidence=50, source_url="https://ieee/", source_type="inferred")
    _ins_raw(conn, id_=100, source_id=9, promoted_identifier_id=1)
    _ins_raw(conn, id_=101, source_id=1, promoted_identifier_id=2)
    conn.commit()

    report = run_dedup(conn, write_ledger=False)

    assert not report.halts
    assert report.clusters_detected == 1
    decision = report.cluster_decisions[0]
    assert decision.dedup_class == "strict_subset"
    assert decision.canonical_id == 1  # MAC has higher confidence
    assert decision.canonical_post_confidence == 65  # min(99, 60+5)
    assert decision.uplifted is True

    # Loser id=2 (OUI) is superseded by id=1 (MAC).
    loser = conn.execute(
        "SELECT superseded_by FROM identifiers WHERE id = 2"
    ).fetchone()
    assert loser["superseded_by"] == 1


# ─── Orchestrator: §8.2 ceiling breach halts ───────────────────────────────


def test_dedup_pass_ceiling_breach_halts_and_rolls_back():
    conn = _fresh_conn()
    # Crowdsourced ceiling = 75. Two rows at 75 across distinct sources
    # would uplift to 80 → breach.
    _ins_id(conn, id_=1, identifier="aa:bb:cc", identifier_type="oui",
            confidence=75, source_url="https://atlas/",
            source_type="crowdsourced")
    _ins_id(conn, id_=2, identifier="aa:bb:cc", identifier_type="oui",
            confidence=70, source_url="https://wigle/",
            source_type="crowdsourced")
    _ins_raw(conn, id_=100, source_id=5, promoted_identifier_id=1)
    _ins_raw(conn, id_=101, source_id=9, promoted_identifier_id=2)
    conn.commit()

    report = run_dedup(conn, write_ledger=False)

    assert len(report.halts) == 1
    halt = report.halts[0]
    assert halt.kind == "ceiling_breach"
    assert "ceiling=75" in halt.detail

    # Nothing persisted — both rows still in active set.
    n_active = conn.execute(
        "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
    ).fetchone()[0]
    assert n_active == 2
    confidences = {
        r["id"]: r["confidence"]
        for r in conn.execute("SELECT id, confidence FROM identifiers")
    }
    assert confidences == {1: 75, 2: 70}


# ─── Orchestrator: Wave-A supersession halts ───────────────────────────────


def test_dedup_pass_wave_a_supersession_halts():
    conn = _fresh_conn()
    # Wave-A canonical at id=1 (MAC, crowdsourced, conf=60).
    # A higher-confidence regulatory MAC row would supersede it.
    _ins_id(conn, id_=WAVE_A_CANONICAL_ID, identifier="e4:aa:ea:80:a1:9b",
            identifier_type="mac", confidence=60, source_url="https://github/",
            source_type="crowdsourced")
    _ins_id(conn, id_=2, identifier="e4:aa:ea:80:a1:9b",
            identifier_type="mac", confidence=85, source_url="https://fcc/",
            source_type="regulatory")
    _ins_raw(conn, id_=100, source_id=12,
             promoted_identifier_id=WAVE_A_CANONICAL_ID)
    _ins_raw(conn, id_=101, source_id=7, promoted_identifier_id=2)
    conn.commit()

    report = run_dedup(conn, write_ledger=False)

    assert len(report.halts) == 1
    assert report.halts[0].kind == "wave_a_supersession"
    # Nothing persisted — Wave-A still canonical.
    wave_a = conn.execute(
        "SELECT superseded_by FROM identifiers WHERE id = ?",
        (WAVE_A_CANONICAL_ID,),
    ).fetchone()
    assert wave_a["superseded_by"] is None


# ─── Orchestrator: no-op clean run ─────────────────────────────────────────


def test_dedup_pass_no_clusters_is_clean_noop():
    conn = _fresh_conn()
    _ins_id(conn, id_=1, identifier="aa:bb:cc", identifier_type="oui",
            confidence=50, source_url="https://ieee/", source_type="inferred")
    _ins_id(conn, id_=2, identifier="11:22:33", identifier_type="oui",
            confidence=50, source_url="https://ieee/", source_type="inferred")
    _ins_raw(conn, id_=100, source_id=1, promoted_identifier_id=1)
    _ins_raw(conn, id_=101, source_id=1, promoted_identifier_id=2)
    conn.commit()

    report = run_dedup(conn, write_ledger=False)

    assert not report.halts
    assert report.clusters_detected == 0
    assert report.rows_superseded == 0
    assert report.pre_active_count == 2
    assert report.post_active_count == 2


# ─── Orchestrator: idempotency on rerun ────────────────────────────────────


def test_dedup_pass_is_idempotent_on_rerun():
    conn = _fresh_conn()
    _ins_id(conn, id_=1, identifier="aa:bb:cc", identifier_type="oui",
            confidence=60, source_url="https://ieee/", source_type="regulatory")
    _ins_id(conn, id_=2, identifier="aa:bb:cc", identifier_type="oui",
            confidence=55, source_url="https://wireshark/",
            source_type="crowdsourced")
    _ins_raw(conn, id_=100, source_id=1, promoted_identifier_id=1)
    _ins_raw(conn, id_=101, source_id=4, promoted_identifier_id=2)
    conn.commit()

    first = run_dedup(conn, write_ledger=False)
    assert first.rows_superseded == 1
    assert first.rows_uplifted == 1

    # Rerun should find no active duplicates — loser already carries
    # superseded_by, falling out of the active set on load.
    second = run_dedup(conn, write_ledger=False)
    assert second.clusters_detected == 0
    assert second.rows_superseded == 0
    assert second.pre_active_count == 1  # only the canonical remains active

    # Canonical confidence didn't double-uplift.
    canonical_conf = conn.execute(
        "SELECT confidence FROM identifiers WHERE id = 1"
    ).fetchone()["confidence"]
    assert canonical_conf == 65


# ─── Orchestrator: dry-run does not mutate ─────────────────────────────────


def test_dedup_pass_dry_run_does_not_mutate():
    conn = _fresh_conn()
    _ins_id(conn, id_=1, identifier="aa:bb:cc", identifier_type="oui",
            confidence=60, source_url="https://ieee/", source_type="regulatory")
    _ins_id(conn, id_=2, identifier="aa:bb:cc", identifier_type="oui",
            confidence=55, source_url="https://wireshark/",
            source_type="crowdsourced")
    _ins_raw(conn, id_=100, source_id=1, promoted_identifier_id=1)
    _ins_raw(conn, id_=101, source_id=4, promoted_identifier_id=2)
    conn.commit()

    report = run_dedup(conn, dry_run=True, write_ledger=False)
    assert report.dry_run is True
    assert report.clusters_detected == 1
    assert report.rows_uplifted == 1

    # No DB mutations.
    rows = conn.execute(
        "SELECT id, confidence, superseded_by FROM identifiers ORDER BY id"
    ).fetchall()
    assert [dict(r) for r in rows] == [
        {"id": 1, "confidence": 60, "superseded_by": None},
        {"id": 2, "confidence": 55, "superseded_by": None},
    ]


# ─── Orchestrator: §8.2 ceilings table sanity ──────────────────────────────


def test_source_type_ceilings_match_bible_8_2_max_columns():
    """Spot-check ceilings table aligns with §8.2 right-column maxes."""
    assert SOURCE_TYPE_CEILINGS["official"] == 100
    assert SOURCE_TYPE_CEILINGS["regulatory"] == 95
    assert SOURCE_TYPE_CEILINGS["manufacturer_doc"] == 90
    assert SOURCE_TYPE_CEILINGS["procurement"] == 85
    assert SOURCE_TYPE_CEILINGS["academic"] == 90
    assert SOURCE_TYPE_CEILINGS["foia"] == 85
    assert SOURCE_TYPE_CEILINGS["crowdsourced"] == 75
    assert SOURCE_TYPE_CEILINGS["inferred"] == 70
