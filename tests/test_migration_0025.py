"""Tests for migration 0025 — CP31 FCC EAS identifier_type cluster +
manufacturers hub-and-spoke + Parrot conversion.

Per MAC-198 dispatch §Tests:
  - pre/post row count assertion
  - PRAGMA integrity_check assertion
  - CHECK enum value list verification
  - Parrot Automotive arm row INSERTed correctly with parent_manufacturer_id=25

Strategy: apply migrations 0001..0024 to a fresh in-memory DB, seed the bare
minimum state the migration exercises (Parrot row at id=25 + a couple of
representative identifier rows), then apply 0025 and validate the post-state.

This isolates the schema/data transformation from the production canon
(34,910-row corpus) so tests stay deterministic and fast.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"


def _apply_migrations_through(conn: sqlite3.Connection, last_version: int) -> None:
    """Apply 0001..last_version in lexical order."""
    files = sorted(
        p for p in MIGRATIONS_DIR.glob("*.sql")
        if p.name[:4].isdigit() and int(p.name[:4]) <= last_version
    )
    for f in files:
        conn.executescript(f.read_text())


@pytest.fixture()
def db_post_0024(tmp_path: Path) -> sqlite3.Connection:
    """A fresh in-memory DB with migrations 0001..0024 applied.

    The 0001 initial migration seeds the canonical manufacturers list per
    §2.1 — Parrot lands at id=25 deterministically. Migration 0025 then
    relies on that pre-existing id when binding the arm row.
    """
    conn = sqlite3.connect(":memory:")
    _apply_migrations_through(conn, 24)
    parrot_id = conn.execute(
        "SELECT id FROM manufacturers WHERE canonical_name='Parrot'"
    ).fetchone()[0]
    assert parrot_id == 25, f"test-fixture invariant: Parrot id={parrot_id}"
    return conn


def test_pre_migration_baselines(db_post_0024: sqlite3.Connection) -> None:
    """Confirm fixture state before 0025 applies."""
    conn = db_post_0024
    assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 24


def test_migration_0025_applies_cleanly(db_post_0024: sqlite3.Connection) -> None:
    conn = db_post_0024
    pre_ids = conn.execute("SELECT COUNT(*) FROM identifiers").fetchone()[0]
    pre_mfr = conn.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]

    sql = (MIGRATIONS_DIR / "0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql").read_text()
    conn.executescript(sql)

    # identifiers count preserved (schema-only change for that table)
    assert conn.execute("SELECT COUNT(*) FROM identifiers").fetchone()[0] == pre_ids
    # manufacturers gains exactly one row (Parrot Automotive arm)
    assert conn.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0] == pre_mfr + 1

    # PRAGMA integrity_check + foreign_key_check
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    # Schema version bumped
    assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 25


def test_identifier_type_check_extended(db_post_0024: sqlite3.Connection) -> None:
    """Both new identifier_type values are admitted; an unrelated junk value is rejected."""
    conn = db_post_0024
    conn.executescript(
        (MIGRATIONS_DIR / "0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql").read_text()
    )

    # Accept fcc_grantee_code
    conn.execute(
        "INSERT INTO identifiers (identifier, identifier_type, device_category, "
        "source_url, source_type) VALUES (?, ?, ?, ?, ?)",
        ("BCG", "fcc_grantee_code", "unknown", "https://fcc.example", "regulatory"),
    )
    # Accept equipment_class_code
    conn.execute(
        "INSERT INTO identifiers (identifier, identifier_type, device_category, "
        "source_url, source_type) VALUES (?, ?, ?, ?, ?)",
        ("A1234", "equipment_class_code", "unknown", "https://fcc.example", "regulatory"),
    )
    # Reject a non-enumerated value
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO identifiers (identifier, identifier_type, device_category, "
            "source_url, source_type) VALUES (?, ?, ?, ?, ?)",
            ("zzz", "totally_made_up_type", "unknown", "https://x", "regulatory"),
        )


def test_pair_kind_check_extended(db_post_0024: sqlite3.Connection) -> None:
    """fcc_grantee_equipment_class is admitted; junk pair_kind is rejected."""
    conn = db_post_0024
    conn.executescript(
        (MIGRATIONS_DIR / "0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql").read_text()
    )

    cur = conn.execute(
        "INSERT INTO identifiers (identifier, identifier_type, device_category, "
        "source_url, source_type) VALUES (?, ?, ?, ?, ?)",
        ("BCG", "fcc_grantee_code", "unknown", "https://fcc.example", "regulatory"),
    )
    grantee_id = cur.lastrowid
    cur = conn.execute(
        "INSERT INTO identifiers (identifier, identifier_type, device_category, "
        "source_url, source_type, paired_identifier_id, pair_kind) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("A1234", "equipment_class_code", "unknown", "https://fcc.example",
         "regulatory", grantee_id, "fcc_grantee_equipment_class"),
    )
    assert cur.lastrowid is not None

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO identifiers (identifier, identifier_type, device_category, "
            "source_url, source_type, pair_kind) VALUES (?, ?, ?, ?, ?, ?)",
            ("foo", "mac", "unknown", "https://x", "regulatory", "made_up_pair"),
        )


def test_parrot_arm_inserted_with_parent_25(db_post_0024: sqlite3.Connection) -> None:
    """Parrot Automotive arm row exists with parent_manufacturer_id=25,
    is_arm=1, query_default='hidden_arm', primary_category='automotive_telematics'."""
    conn = db_post_0024
    conn.executescript(
        (MIGRATIONS_DIR / "0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql").read_text()
    )

    row = conn.execute(
        "SELECT canonical_name, primary_category, is_arm, query_default, "
        "parent_manufacturer_id "
        "FROM manufacturers WHERE canonical_name = 'Parrot Automotive'"
    ).fetchone()
    assert row is not None, "Parrot Automotive arm row was not inserted"
    canonical_name, primary_category, is_arm, query_default, parent_id = row
    assert canonical_name == "Parrot Automotive"
    assert primary_category == "automotive_telematics"
    assert is_arm == 1
    assert query_default == "hidden_arm"
    assert parent_id == 25

    # Parrot hub stays a hub
    hub = conn.execute(
        "SELECT is_arm, query_default, parent_manufacturer_id "
        "FROM manufacturers WHERE id = 25"
    ).fetchone()
    assert hub == (0, "visible", None)


def test_query_default_check_constraint(db_post_0024: sqlite3.Connection) -> None:
    """query_default rejects values outside the 2-element enum."""
    conn = db_post_0024
    conn.executescript(
        (MIGRATIONS_DIR / "0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql").read_text()
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO manufacturers (canonical_name, source_url, query_default) "
            "VALUES (?, ?, ?)",
            ("BadValue", "https://x", "neither_visible_nor_hidden"),
        )


def test_hub_and_spoke_default_filter(db_post_0024: sqlite3.Connection) -> None:
    """Default `WHERE query_default = 'visible'` filter surfaces hubs only."""
    conn = db_post_0024
    conn.executescript(
        (MIGRATIONS_DIR / "0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql").read_text()
    )
    visible_count = conn.execute(
        "SELECT COUNT(*) FROM manufacturers WHERE query_default = 'visible'"
    ).fetchone()[0]
    hidden_count = conn.execute(
        "SELECT COUNT(*) FROM manufacturers WHERE query_default = 'hidden_arm'"
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
    assert visible_count + hidden_count == total
    assert hidden_count == 1  # exactly the Parrot Automotive arm row
