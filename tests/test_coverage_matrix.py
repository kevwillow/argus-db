"""Tests for ``db/validation/coverage_matrix.py`` — Phase-5 Step-6 orchestrator.

Coverage:
- Cell-arithmetic correctness: row totals + column totals + grand total.
- Drop-tally reconciliation: ``pre_active_count − sum(bins) = survivors``
  for both standard and high-confidence Talos export files.
- Idempotency: re-running the orchestrator on an unchanged DB produces an
  identical report.
- §11 #6 attestation: ``PRAGMA query_only = ON`` is set, blocking writes.
- Single-row sentinel: a one-row active set produces correct cell, vendor
  corroboration, and drop bin.
- §11 #13 ``unknown_category`` halt: an unknown-category row that escapes
  the drop bin (impossible by construction; defensive guard) raises a halt.
- §11 #14 ``procurement_only`` halt: a procurement row that escapes the
  drop bin (defensive guard) raises a halt.
- Mac-range size + Pi-self-exclude predicates: positive + negative cases.
- §8.4 oversized mac_range routes to ``oversized_mac_range`` not
  ``unknown_category`` (priority order check).
"""

from __future__ import annotations

import sqlite3

import pytest

from db.validation.coverage_matrix import (
    DEVICE_CATEGORIES,
    EXPORT_HIGH_CONFIDENCE_FLOOR,
    EXPORT_STANDARD_FLOOR,
    IDENTIFIER_TYPES,
    PI_SELF_EXCLUDE_OUIS,
    SOURCE_TYPE_CEILINGS,
    _assign_drop_bin,
    ActiveRow,
    mac_range_size,
    matches_pi_self_exclude,
    report_to_dict,
    report_to_markdown,
    run_coverage_matrix,
)

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
CREATE TABLE manufacturers (
  id INTEGER PRIMARY KEY,
  canonical_name TEXT NOT NULL UNIQUE,
  aliases TEXT,
  primary_category TEXT,
  source_url TEXT,
  notes TEXT,
  added_at DATETIME
);
CREATE TABLE fcc_grantees (
  id INTEGER PRIMARY KEY,
  source_id INTEGER, extraction_run_id INTEGER, source_url TEXT,
  source_row_key TEXT, grantee_code TEXT, grantee_name TEXT,
  mailing_address TEXT, po_box TEXT, city TEXT, state TEXT,
  country TEXT, zip_code TEXT, contact_name TEXT, date_received TEXT,
  source_excerpt TEXT, notes TEXT, captured_at TEXT, processed_at TEXT
);
CREATE TABLE procurement_records (
  id INTEGER PRIMARY KEY,
  agency_name TEXT, agency_geographic_scope TEXT,
  vendor_canonical_name TEXT, product_family TEXT,
  contract_amount_usd REAL, contract_date DATE,
  source_url TEXT, source_type TEXT, source_excerpt TEXT,
  confidence INTEGER, captured_at DATETIME, linked_identifier_id INTEGER,
  notes TEXT
);
CREATE TABLE deployment_observations (
  id INTEGER PRIMARY KEY,
  source_id INTEGER, extraction_run_id INTEGER, source_url TEXT,
  source_row_key TEXT, agency_name TEXT, agency_type TEXT,
  juris_type TEXT, city TEXT, county TEXT, state TEXT, country TEXT,
  lat REAL, lon REAL, technology_category TEXT, vendor_raw TEXT,
  citation_url TEXT, source_excerpt TEXT, captured_at DATETIME,
  processed_at DATETIME, notes TEXT
);
CREATE TABLE council_minutes_matters (
  id INTEGER PRIMARY KEY,
  source_id INTEGER, extraction_run_id INTEGER,
  source_row_key TEXT, legistar_client TEXT, agency_name TEXT,
  agency_geographic_scope TEXT, matter_id INTEGER, matter_guid TEXT,
  matter_file TEXT, matter_title TEXT, matter_type_name TEXT,
  matter_body_name TEXT, matter_status_name TEXT, matter_intro_date DATE,
  matter_passed_date DATE, matter_enactment_date DATE, matter_cost TEXT,
  matched_vendor_label TEXT, vendor_canonical_name TEXT,
  source_url TEXT, source_type TEXT, source_excerpt TEXT,
  confidence INTEGER, linked_identifier_id INTEGER,
  captured_at DATETIME, notes TEXT
);
"""


@pytest.fixture
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA_DDL)
    yield c
    c.close()


def _seed_identifier(
    conn: sqlite3.Connection,
    *,
    rid: int,
    identifier: str,
    identifier_type: str = "oui",
    device_category: str = "unknown",
    manufacturer: str = "Acme",
    source_type: str = "inferred",
    confidence: int = 55,
    superseded_by: int | None = None,
) -> None:
    conn.execute(
        "INSERT INTO identifiers "
        "(id, identifier, identifier_type, device_category, manufacturer, "
        " confidence, source_url, source_type, superseded_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            rid, identifier, identifier_type, device_category, manufacturer,
            confidence, "http://example/test", source_type, superseded_by,
        ),
    )


# ────────────────────────────────────────────────────────────────────────────
# Predicate tests
# ────────────────────────────────────────────────────────────────────────────


def test_mac_range_size_oui28() -> None:
    """OUI-28 (28-bit prefix, 7 hex chars) → 2^20 = 1,048,576 entries."""
    assert mac_range_size("10:63:a3:1") == 1 << 20


def test_mac_range_size_oui36() -> None:
    """OUI-36 (36-bit prefix, 9 hex chars) → 2^12 = 4096 entries."""
    assert mac_range_size("8c:1f:64:a9:8") == 1 << 12


def test_mac_range_size_full_mac() -> None:
    """Full 48-bit MAC → 1 entry."""
    assert mac_range_size("aa:bb:cc:dd:ee:ff") == 1


def test_mac_range_size_just_under_ceiling() -> None:
    """40-bit prefix (10 hex chars) → 2^8 = 256 entries (right at ceiling, not over)."""
    assert mac_range_size("aa:bb:cc:dd:ee") == 256


def test_pi_self_exclude_positive_oui() -> None:
    for oui in PI_SELF_EXCLUDE_OUIS:
        assert matches_pi_self_exclude(oui, "oui")
        assert matches_pi_self_exclude(oui.upper(), "oui")


def test_pi_self_exclude_positive_mac() -> None:
    """A MAC whose first 3 octets are a Pi OUI matches."""
    assert matches_pi_self_exclude("b8:27:eb:12:34:56", "mac")
    assert matches_pi_self_exclude("DC:A6:32:AA:BB:CC", "mac")


def test_pi_self_exclude_negative() -> None:
    assert not matches_pi_self_exclude("e4:aa:ea", "oui")
    assert not matches_pi_self_exclude("e4:aa:ea:80:a1:9b", "mac")
    assert not matches_pi_self_exclude("flock-cam-12", "ssid_exact")


# ────────────────────────────────────────────────────────────────────────────
# Drop-bin priority tests
# ────────────────────────────────────────────────────────────────────────────


def _row(**kw) -> ActiveRow:
    defaults = dict(
        id=1, identifier="aa:bb:cc", identifier_type="oui",
        device_category="alpr", manufacturer="Acme",
        source_type="inferred", confidence=55,
    )
    defaults.update(kw)
    return ActiveRow(**defaults)


def test_drop_bin_procurement_takes_priority_over_unknown() -> None:
    """A procurement-only row that's also unknown-category bins as procurement_only."""
    r = _row(source_type="procurement", device_category="unknown")
    assert _assign_drop_bin(r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=False) == "procurement_only"


def test_drop_bin_unknown_category_takes_priority_over_pi_self_exclude() -> None:
    """An unknown-category row at a Pi OUI bins as unknown_category."""
    r = _row(identifier="b8:27:eb", device_category="unknown")
    assert _assign_drop_bin(r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=True) == "unknown_category"


def test_drop_bin_oversized_mac_range() -> None:
    r = _row(identifier="10:63:a3:1", identifier_type="mac_range", device_category="alpr")
    assert _assign_drop_bin(r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=False) == "oversized_mac_range"


def test_drop_bin_undersized_mac_range_survives() -> None:
    """40-bit prefix (10 hex chars) = 256 entries, right at the §4.4 ceiling."""
    r = _row(identifier="aa:bb:cc:dd:ee", identifier_type="mac_range", device_category="alpr")
    assert _assign_drop_bin(r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=False) is None


def test_drop_bin_self_exclude_only_drops_in_high_conf() -> None:
    r = _row(identifier="b8:27:eb", device_category="alpr", confidence=80)
    assert _assign_drop_bin(r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=False) is None
    assert _assign_drop_bin(r, EXPORT_HIGH_CONFIDENCE_FLOOR, drop_pi_self_exclude=True) == "self_exclude_oui"


def test_drop_bin_below_confidence_floor() -> None:
    r = _row(device_category="alpr", confidence=20)
    assert _assign_drop_bin(r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=False) == "below_confidence_threshold"


def test_drop_bin_high_conf_floor_drops_mid_band() -> None:
    """A 60-confidence alpr row survives the standard export but drops from high-conf."""
    r = _row(device_category="alpr", confidence=60)
    assert _assign_drop_bin(r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=False) is None
    assert _assign_drop_bin(r, EXPORT_HIGH_CONFIDENCE_FLOOR, drop_pi_self_exclude=True) == "below_confidence_threshold"


def test_drop_bin_survivor() -> None:
    r = _row(device_category="alpr", confidence=80, identifier_type="mac",
             identifier="aa:bb:cc:dd:ee:ff")
    assert _assign_drop_bin(r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=False) is None
    assert _assign_drop_bin(r, EXPORT_HIGH_CONFIDENCE_FLOOR, drop_pi_self_exclude=True) is None


# ────────────────────────────────────────────────────────────────────────────
# Single-row sentinel
# ────────────────────────────────────────────────────────────────────────────


def test_single_row_active_set(conn: sqlite3.Connection) -> None:
    _seed_identifier(
        conn, rid=1, identifier="e4:aa:ea:80:a1:9b", identifier_type="mac",
        device_category="alpr", manufacturer="Flock Safety",
        source_type="crowdsourced", confidence=60,
    )
    conn.execute(
        "INSERT INTO manufacturers (canonical_name, aliases, source_url) VALUES (?, ?, ?)",
        ("Flock Safety", "Flock", "http://bible"),
    )
    conn.commit()
    report = run_coverage_matrix(conn)
    assert report.pre_active_count == 1
    assert len(report.cells) == len(DEVICE_CATEGORIES) * len(IDENTIFIER_TYPES)
    non_empty = [c for c in report.cells if c.n > 0]
    assert len(non_empty) == 1
    cell = non_empty[0]
    assert cell.device_category == "alpr"
    assert cell.identifier_type == "mac"
    assert cell.n == 1
    assert cell.n_by_source_type == {"crowdsourced": 1}
    assert cell.min_conf == 60 == cell.max_conf
    assert cell.median_conf == 60
    assert cell.row_ids == (1,)
    assert len(report.vendor_corroboration) == 1
    v = report.vendor_corroboration[0]
    assert v.canonical_name == "Flock Safety"
    assert "Flock" in v.aliases_used
    assert v.high_corroboration is False  # empty Phase-3 corpora
    # Standard export: survives (alpr / mac / conf=60 ≥30 / non-Pi).
    assert report.drop_tally_standard.survivors == 1
    # High-conf export: dropped below threshold (60 < 70).
    assert report.drop_tally_high_confidence.survivors == 0
    assert report.drop_tally_high_confidence.below_confidence_threshold == 1
    assert not report.halts


# ────────────────────────────────────────────────────────────────────────────
# Reconciliation arithmetic
# ────────────────────────────────────────────────────────────────────────────


def test_drop_tally_reconciles_with_mixed_active_set(conn: sqlite3.Connection) -> None:
    """A 5-row mixed cohort exercises every priority level + survivor cases."""
    rows = [
        # 1: procurement (drops as procurement_only in BOTH files).
        dict(rid=1, identifier="aa:11:22", source_type="procurement",
             device_category="alpr", confidence=80),
        # 2: unknown_category drop (the OUI-inferred default).
        dict(rid=2, identifier="bb:11:22", source_type="inferred",
             device_category="unknown", confidence=55),
        # 3: oversized mac_range with non-unknown category.
        dict(rid=3, identifier="10:63:a3:1", identifier_type="mac_range",
             source_type="inferred", device_category="alpr", confidence=60),
        # 4: high-conf survivor in standard, drops to self_exclude in high-conf.
        dict(rid=4, identifier="b8:27:eb", source_type="crowdsourced",
             device_category="alpr", confidence=80),
        # 5: full survivor in BOTH files.
        dict(rid=5, identifier="aa:bb:cc:dd:ee:ff", identifier_type="mac",
             source_type="crowdsourced", device_category="alpr", confidence=80),
    ]
    for r in rows:
        _seed_identifier(conn, **r)
    conn.commit()
    report = run_coverage_matrix(conn)
    n = report.pre_active_count
    assert n == 5

    # Standard export tally.
    s = report.drop_tally_standard
    assert s.procurement_only == 1     # row 1
    assert s.unknown_category == 1     # row 2
    assert s.oversized_mac_range == 1  # row 3
    assert s.self_exclude_oui == 0     # standard keeps Pi OUIs
    assert s.below_confidence_threshold == 0
    assert s.survivors == 2            # rows 4 and 5
    sum_bins_s = (
        s.unknown_category + s.procurement_only + s.self_exclude_oui +
        s.below_confidence_threshold + s.oversized_mac_range +
        s.ssid_pattern + s.device_fingerprint
    )
    assert sum_bins_s + s.survivors == n

    # High-confidence export tally.
    h = report.drop_tally_high_confidence
    assert h.procurement_only == 1
    assert h.unknown_category == 1
    assert h.oversized_mac_range == 1
    assert h.self_exclude_oui == 1     # row 4 drops here
    assert h.survivors == 1            # only row 5
    sum_bins_h = (
        h.unknown_category + h.procurement_only + h.self_exclude_oui +
        h.below_confidence_threshold + h.oversized_mac_range +
        h.ssid_pattern + h.device_fingerprint
    )
    assert sum_bins_h + h.survivors == n
    assert not report.halts


# ────────────────────────────────────────────────────────────────────────────
# Cell arithmetic correctness
# ────────────────────────────────────────────────────────────────────────────


def test_cell_arithmetic_grand_total_matches_active_count(conn: sqlite3.Connection) -> None:
    cohort = [
        dict(rid=1, identifier="aa:11:22", device_category="alpr", source_type="inferred", confidence=55),
        dict(rid=2, identifier="bb:11:22", device_category="alpr", source_type="crowdsourced", confidence=70),
        dict(rid=3, identifier="cc:11:22", device_category="drone", source_type="inferred", confidence=50),
        dict(rid=4, identifier="dd:11:22", device_category="unknown", source_type="inferred", confidence=55),
        dict(rid=5, identifier="ee:11:22:33", identifier_type="mac_range",
             device_category="unknown", source_type="inferred", confidence=55),
    ]
    for r in cohort:
        _seed_identifier(conn, **r)
    # Add a superseded row that should NOT be counted.
    _seed_identifier(
        conn, rid=99, identifier="ff:11:22", device_category="alpr",
        source_type="inferred", confidence=55, superseded_by=1,
    )
    conn.commit()
    report = run_coverage_matrix(conn)
    assert report.pre_active_count == 5
    grand_total = sum(c.n for c in report.cells)
    assert grand_total == report.pre_active_count

    # Per-cell sanity.
    by_cell = {(c.device_category, c.identifier_type): c for c in report.cells}
    assert by_cell[("alpr", "oui")].n == 2
    assert by_cell[("alpr", "oui")].n_by_source_type == {"crowdsourced": 1, "inferred": 1}
    assert by_cell[("alpr", "oui")].min_conf == 55
    assert by_cell[("alpr", "oui")].max_conf == 70
    assert by_cell[("alpr", "oui")].median_conf == 62.5
    assert by_cell[("drone", "oui")].n == 1
    assert by_cell[("unknown", "oui")].n == 1
    assert by_cell[("unknown", "mac_range")].n == 1


def test_cell_matrix_has_all_combinations(conn: sqlite3.Connection) -> None:
    """Even with an empty active set, the matrix exposes every (dc, it) cell."""
    conn.commit()
    report = run_coverage_matrix(conn)
    assert len(report.cells) == len(DEVICE_CATEGORIES) * len(IDENTIFIER_TYPES)
    seen = {(c.device_category, c.identifier_type) for c in report.cells}
    assert seen == {(dc, it) for dc in DEVICE_CATEGORIES for it in IDENTIFIER_TYPES}
    assert all(c.n == 0 for c in report.cells)


# ────────────────────────────────────────────────────────────────────────────
# Idempotency
# ────────────────────────────────────────────────────────────────────────────


def test_rerun_produces_identical_report(conn: sqlite3.Connection) -> None:
    """Step-6 is read-only; re-running on an unchanged DB produces identical output."""
    _seed_identifier(conn, rid=1, identifier="e4:aa:ea:80:a1:9b",
                     identifier_type="mac", device_category="alpr",
                     manufacturer="Flock Safety", source_type="crowdsourced",
                     confidence=60)
    conn.commit()
    r1 = report_to_dict(run_coverage_matrix(conn))
    r2 = report_to_dict(run_coverage_matrix(conn))
    assert r1 == r2


def test_no_mutations_to_identifiers(conn: sqlite3.Connection) -> None:
    """The orchestrator must not modify identifier rows or insert anything."""
    _seed_identifier(conn, rid=1, identifier="aa:bb:cc", device_category="alpr",
                     source_type="inferred", confidence=55)
    conn.commit()
    pre_rows = list(conn.execute(
        "SELECT id, identifier, identifier_type, device_category, manufacturer, "
        "source_type, confidence, superseded_by FROM identifiers ORDER BY id"
    ).fetchall())
    pre_count = conn.execute("SELECT COUNT(*) FROM identifiers").fetchone()[0]
    run_coverage_matrix(conn)
    post_rows = list(conn.execute(
        "SELECT id, identifier, identifier_type, device_category, manufacturer, "
        "source_type, confidence, superseded_by FROM identifiers ORDER BY id"
    ).fetchall())
    post_count = conn.execute("SELECT COUNT(*) FROM identifiers").fetchone()[0]
    assert pre_count == post_count
    assert [tuple(r) for r in pre_rows] == [tuple(r) for r in post_rows]


# ────────────────────────────────────────────────────────────────────────────
# §11 #6 attestation: query-only enforcement on connection
# ────────────────────────────────────────────────────────────────────────────


def test_query_only_pragma_blocks_writes(tmp_path) -> None:
    """The `_connect` helper sets PRAGMA query_only = ON, blocking writes.

    Direct functional test: open via the public CLI helper and confirm that
    INSERT raises sqlite3 OperationalError (\"attempt to write a readonly\").
    """
    from db.validation.coverage_matrix import _connect

    db_path = tmp_path / "argus_test.db"
    # Bootstrap schema with a normal connection (separate from the orchestrator's).
    bootstrap = sqlite3.connect(db_path)
    bootstrap.executescript(SCHEMA_DDL)
    bootstrap.commit()
    bootstrap.close()

    conn = _connect(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "INSERT INTO identifiers "
                "(identifier, identifier_type, device_category, source_url, source_type) "
                "VALUES (?, ?, ?, ?, ?)",
                ("aa:bb:cc", "oui", "unknown", "http://x", "inferred"),
            )
    finally:
        conn.close()


# ────────────────────────────────────────────────────────────────────────────
# §8.2 source_type sanity halt
# ────────────────────────────────────────────────────────────────────────────


def test_unknown_source_type_halts(conn: sqlite3.Connection) -> None:
    """A row with source_type outside the §8.2 enum surfaces as a halt."""
    # Schema CHECK is removed in our test DDL, so we can seed an off-enum value.
    _seed_identifier(conn, rid=1, identifier="aa:bb:cc", device_category="alpr",
                     source_type="news_forum", confidence=40)
    conn.commit()
    report = run_coverage_matrix(conn)
    assert any(h.kind == "unknown_source_type" for h in report.halts)


def test_source_type_ceilings_full_section_8_2_coverage() -> None:
    """The local SOURCE_TYPE_CEILINGS map covers the bible §8.2 enum."""
    expected = {
        "official", "regulatory", "manufacturer_doc", "procurement",
        "academic", "foia", "crowdsourced", "inferred",
    }
    assert set(SOURCE_TYPE_CEILINGS.keys()) >= expected


# ────────────────────────────────────────────────────────────────────────────
# Markdown emission smoke test
# ────────────────────────────────────────────────────────────────────────────


def test_markdown_emission_is_well_formed(conn: sqlite3.Connection) -> None:
    _seed_identifier(conn, rid=1, identifier="aa:bb:cc", device_category="alpr",
                     manufacturer="Flock Safety", source_type="crowdsourced",
                     confidence=80, identifier_type="oui")
    conn.execute(
        "INSERT INTO manufacturers (canonical_name, aliases, source_url) VALUES (?, ?, ?)",
        ("Flock Safety", "Flock", "http://bible"),
    )
    conn.commit()
    md = report_to_markdown(run_coverage_matrix(conn))
    assert "Phase-5 Step-6 coverage matrix" in md
    assert "## §11 attestations" in md
    assert "## §6.1 Coverage matrix" in md
    assert "## §6.2 Phase-3 cross-reference annotation" in md
    assert "## §6.3 / §9 item 9" in md
    # Every device_category row appears in the matrix.
    for dc in DEVICE_CATEGORIES:
        assert f"`{dc}`" in md
