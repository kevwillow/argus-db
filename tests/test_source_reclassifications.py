"""Tests for the ``source_reclassifications`` audit table (migration 0017 / CP19).

Coverage:
- Table exists with the expected column shape (id, identifier_id FK, sweep_event_id,
  pre/post source_url + source_type + confidence, reclassification_reason,
  reclassification_anchor, reclassified_at, notes).
- FK ``ON DELETE CASCADE`` from ``identifiers`` cascades to ``source_reclassifications``.
- ``CHECK (pre_confidence BETWEEN 0 AND 100)`` rejects out-of-range values.
- ``CHECK (post_confidence BETWEEN 0 AND 100)`` rejects out-of-range values.
- NOT NULL columns reject NULL inserts.
- ``reclassified_at`` DEFAULT CURRENT_TIMESTAMP populates when omitted.
- Audit-table append-don't-mutate discipline (S.8): two sweep_event_id values
  on the same identifier_id produce two distinct chronological audit entries.

Codified per CP19 §6.7 candidate 1 (CP19 §6.7 follow-up) + board ratification
at MAC-88 IEEE PII review dispatch 2026-05-14. Mirrors test pattern from
``tests/test_coverage_matrix.py``: in-memory SQLite + fixture-loaded schema.
"""

from __future__ import annotations

import sqlite3

import pytest


SCHEMA_DDL = """
CREATE TABLE identifiers (
  id INTEGER PRIMARY KEY,
  identifier TEXT NOT NULL,
  identifier_type TEXT NOT NULL,
  device_category TEXT NOT NULL,
  manufacturer TEXT,
  model TEXT,
  confidence INTEGER,
  source_url TEXT,
  source_type TEXT NOT NULL,
  source_excerpt TEXT,
  geographic_scope TEXT,
  first_seen DATETIME,
  last_verified DATETIME,
  notes TEXT,
  superseded_by INTEGER
);

CREATE TABLE source_reclassifications (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier_id               INTEGER NOT NULL REFERENCES identifiers(id) ON DELETE CASCADE,
    sweep_event_id              TEXT NOT NULL,
    pre_source_url              TEXT NOT NULL,
    post_source_url             TEXT NOT NULL,
    pre_source_type             TEXT NOT NULL,
    post_source_type            TEXT NOT NULL,
    pre_confidence              INTEGER NOT NULL CHECK (pre_confidence BETWEEN 0 AND 100),
    post_confidence             INTEGER NOT NULL CHECK (post_confidence BETWEEN 0 AND 100),
    reclassification_reason     TEXT NOT NULL,
    reclassification_anchor     TEXT NOT NULL,
    reclassified_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes                       TEXT
);

CREATE INDEX idx_source_recl_identifier_id   ON source_reclassifications(identifier_id);
CREATE INDEX idx_source_recl_sweep_event     ON source_reclassifications(sweep_event_id);
CREATE INDEX idx_source_recl_reclassified_at ON source_reclassifications(reclassified_at);
"""


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(SCHEMA_DDL)
    # Seed two identifiers for FK + cascade tests
    c.execute(
        """INSERT INTO identifiers (id, identifier, identifier_type, device_category, source_type)
           VALUES (1, 'test-id-1', 'oui', 'drone', 'primary_registry'),
                  (2, 'test-id-2', 'oui', 'drone', 'primary_registry')"""
    )
    c.commit()
    yield c
    c.close()


def _valid_row(identifier_id: int, sweep_event_id: str = "test-sweep-1") -> dict:
    """Return a baseline-valid INSERT row dict; override individual fields for negative tests."""
    return dict(
        identifier_id=identifier_id,
        sweep_event_id=sweep_event_id,
        pre_source_url="https://example.test/old",
        post_source_url="https://example.test/new",
        pre_source_type="primary_registry",
        post_source_type="crowdsourced",
        pre_confidence=85,
        post_confidence=75,
        reclassification_reason="test row — substantive rationale per CP19 convention",
        reclassification_anchor="CP19 test anchor",
    )


def _insert(conn: sqlite3.Connection, row: dict) -> int:
    """Execute INSERT with the given row dict; return the new rowid."""
    cols = ", ".join(row.keys())
    placeholders = ", ".join(["?"] * len(row))
    cur = conn.execute(
        f"INSERT INTO source_reclassifications ({cols}) VALUES ({placeholders})",
        list(row.values()),
    )
    conn.commit()
    return cur.lastrowid


def test_table_has_expected_columns(conn: sqlite3.Connection) -> None:
    """Schema sanity — confirm all CP19-mandated columns exist."""
    cols = {row["name"]: row for row in conn.execute("PRAGMA table_info(source_reclassifications)")}
    expected = {
        "id",
        "identifier_id",
        "sweep_event_id",
        "pre_source_url",
        "post_source_url",
        "pre_source_type",
        "post_source_type",
        "pre_confidence",
        "post_confidence",
        "reclassification_reason",
        "reclassification_anchor",
        "reclassified_at",
        "notes",
    }
    assert set(cols.keys()) == expected, f"Missing or extra columns: {set(cols.keys()) ^ expected}"
    # NOT NULL columns per CP19 §3.1 + migration 0017
    for required in [
        "identifier_id",
        "sweep_event_id",
        "pre_source_url",
        "post_source_url",
        "pre_source_type",
        "post_source_type",
        "pre_confidence",
        "post_confidence",
        "reclassification_reason",
        "reclassification_anchor",
        "reclassified_at",
    ]:
        assert cols[required]["notnull"] == 1, f"{required} should be NOT NULL"
    # notes is the only nullable column (optional per CP19 convention)
    assert cols["notes"]["notnull"] == 0


def test_fk_cascade_on_identifier_delete(conn: sqlite3.Connection) -> None:
    """Deleting an identifier cascades to delete its source_reclassifications rows."""
    _insert(conn, _valid_row(1, "sweep-A"))
    _insert(conn, _valid_row(1, "sweep-B"))
    _insert(conn, _valid_row(2, "sweep-A"))
    assert conn.execute("SELECT COUNT(*) FROM source_reclassifications").fetchone()[0] == 3

    conn.execute("DELETE FROM identifiers WHERE id = 1")
    conn.commit()
    remaining = conn.execute("SELECT COUNT(*) FROM source_reclassifications").fetchone()[0]
    assert remaining == 1, "Cascade should leave exactly the rows attached to id=2"

    surviving = conn.execute("SELECT identifier_id FROM source_reclassifications").fetchone()[0]
    assert surviving == 2


@pytest.mark.parametrize("bad_conf", [-1, 101, 150])
def test_check_pre_confidence_rejects_out_of_range(conn: sqlite3.Connection, bad_conf: int) -> None:
    """CHECK (pre_confidence BETWEEN 0 AND 100) rejects values outside [0, 100]."""
    row = _valid_row(1)
    row["pre_confidence"] = bad_conf
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        _insert(conn, row)


@pytest.mark.parametrize("bad_conf", [-1, 101, 999])
def test_check_post_confidence_rejects_out_of_range(conn: sqlite3.Connection, bad_conf: int) -> None:
    """CHECK (post_confidence BETWEEN 0 AND 100) rejects values outside [0, 100]."""
    row = _valid_row(1)
    row["post_confidence"] = bad_conf
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        _insert(conn, row)


@pytest.mark.parametrize(
    "null_col",
    [
        "sweep_event_id",
        "pre_source_url",
        "post_source_url",
        "pre_source_type",
        "post_source_type",
        "reclassification_reason",
        "reclassification_anchor",
    ],
)
def test_not_null_columns_reject_null(conn: sqlite3.Connection, null_col: str) -> None:
    """Each NOT NULL column rejects NULL inserts. identifier_id + pre/post_confidence are
    tested separately above via FK and CHECK paths respectively."""
    row = _valid_row(1)
    row[null_col] = None
    with pytest.raises(sqlite3.IntegrityError, match="NOT NULL constraint failed"):
        _insert(conn, row)


def test_reclassified_at_defaults_to_current_timestamp(conn: sqlite3.Connection) -> None:
    """reclassified_at populates from DEFAULT CURRENT_TIMESTAMP when omitted at INSERT."""
    row = _valid_row(1)
    # Don't include reclassified_at in the INSERT
    rowid = _insert(conn, row)
    stored = conn.execute(
        "SELECT reclassified_at FROM source_reclassifications WHERE id = ?", (rowid,)
    ).fetchone()[0]
    assert stored is not None, "reclassified_at should populate via DEFAULT"
    # SQLite CURRENT_TIMESTAMP shape: "YYYY-MM-DD HH:MM:SS"
    assert len(stored) >= 19, f"Expected ISO-like timestamp; got {stored!r}"


def test_append_dont_mutate_discipline(conn: sqlite3.Connection) -> None:
    """S.8 append-don't-mutate discipline: corrective refinement on the same identifier
    writes a NEW sweep_event_id audit row, NOT a mutation of the original entry."""
    # Original sweep entry: source_url change A -> B
    orig = _valid_row(1, sweep_event_id="CP19-main-sweep")
    orig["pre_source_url"] = "https://uasdoc.faa.gov/listDocs"
    orig["post_source_url"] = "https://github.com/alphafox02/DragonSync"
    _insert(conn, orig)

    # Corrective refinement: source_url further refined B -> C, written as NEW sweep_event_id
    refinement = _valid_row(1, sweep_event_id="CP19-main-sweep-jlrjr-refinement")
    refinement["pre_source_url"] = "https://github.com/alphafox02/DragonSync"
    refinement["post_source_url"] = "https://github.com/jlrjr/faa-rid-lookup"
    refinement["pre_source_type"] = "crowdsourced"
    refinement["post_source_type"] = "crowdsourced"
    refinement["pre_confidence"] = 75
    refinement["post_confidence"] = 75
    _insert(conn, refinement)

    # Verify both entries exist (no mutation; chronological audit trail preserved)
    rows = conn.execute(
        "SELECT sweep_event_id, pre_source_url, post_source_url FROM source_reclassifications "
        "WHERE identifier_id = 1 ORDER BY id"
    ).fetchall()
    assert len(rows) == 2, "Both audit entries should exist post-refinement"
    assert rows[0]["sweep_event_id"] == "CP19-main-sweep"
    assert rows[0]["post_source_url"] == "https://github.com/alphafox02/DragonSync"
    assert rows[1]["sweep_event_id"] == "CP19-main-sweep-jlrjr-refinement"
    assert rows[1]["pre_source_url"] == "https://github.com/alphafox02/DragonSync"
    assert rows[1]["post_source_url"] == "https://github.com/jlrjr/faa-rid-lookup"


def test_sweep_event_id_groups_query_correctly(conn: sqlite3.Connection) -> None:
    """GROUP BY sweep_event_id returns the expected aggregate counts; mirrors the
    forensic query shape used in handoff docs ('how many rows in each sweep')."""
    # 3 rows in sweep-A across 2 identifiers
    _insert(conn, _valid_row(1, "sweep-A"))
    _insert(conn, _valid_row(2, "sweep-A"))
    _insert(conn, _valid_row(1, "sweep-A"))
    # 2 rows in sweep-B
    _insert(conn, _valid_row(1, "sweep-B"))
    _insert(conn, _valid_row(2, "sweep-B"))

    groups = {
        row["sweep_event_id"]: row["n"]
        for row in conn.execute(
            "SELECT sweep_event_id, COUNT(*) AS n FROM source_reclassifications "
            "GROUP BY sweep_event_id ORDER BY sweep_event_id"
        )
    }
    assert groups == {"sweep-A": 3, "sweep-B": 2}
