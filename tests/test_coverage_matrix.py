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
    EXCLUDED_SOURCE_TYPES,
    EXPORT_HIGH_CONFIDENCE_FLOOR,
    EXPORT_STANDARD_FLOOR,
    IDENTIFIER_TYPES,
    PI_SELF_EXCLUDE_OUIS,
    SOURCE_TYPE_CEILINGS,
    _alias_tokens_for_vendor,
    _assign_drop_bin,
    _CORP_SUFFIX_STOPLIST,
    _is_bogus_token,
    _split_alias_blob,
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


# Updated per SAR-18 (MAC-232 Step 9, 2026-05-22): mac_range DROP is unconditional; size=256 now drops, not survives. Preserved as boundary regression guard.
def test_drop_bin_size_256_mac_range_drops_per_sar18() -> None:
    """40-bit prefix (10 hex chars) = 256 entries, right at the §4.4 ceiling.

    Pre-SAR-18 the predicate was `> MAC_RANGE_EXPANSION_CEILING` strict-greater-than,
    so a size-256 row (Eagle Eye Networks id=9404, the SAR-18 driving case) escaped
    drop. SAR-18 (MAC-232 Step 9) made the mac_range DROP unconditional in both
    classifiers; until CP34 §4.4 ships mac_range expansion in Lynceus v0.3, every
    mac_range row — including the size-256 boundary — routes to
    `oversized_mac_range`. Kept as the boundary regression guard.
    """
    r = _row(identifier="aa:bb:cc:dd:ee", identifier_type="mac_range", device_category="alpr")
    assert _assign_drop_bin(r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=False) == "oversized_mac_range"


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
# CP19 — source_type exclusion on high-conf export
# ────────────────────────────────────────────────────────────────────────────


def test_excluded_source_types_constant_is_inferred_and_crowdsourced() -> None:
    """CP19 (§7.5): the set is exactly {'inferred', 'crowdsourced'} per the
    bible amendment. Set-assertion mirrors the parallel test in
    test_export_lynceus.py; the two modules MUST classify identically."""
    assert EXCLUDED_SOURCE_TYPES == frozenset({"inferred", "crowdsourced"})


def test_drop_bin_excluded_source_type_high_conf_crowdsourced() -> None:
    """A crowdsourced row at conf=75 with all other gates passing drops to
    `excluded_source_type` in the high-conf file."""
    r = _row(device_category="alpr", confidence=75, identifier_type="mac",
             identifier="aa:bb:cc:dd:ee:ff", source_type="crowdsourced")
    assert _assign_drop_bin(
        r, EXPORT_HIGH_CONFIDENCE_FLOOR, drop_pi_self_exclude=True,
        drop_source_types=EXCLUDED_SOURCE_TYPES,
    ) == "excluded_source_type"


def test_drop_bin_excluded_source_type_high_conf_inferred() -> None:
    """Likewise `inferred` source_type drops to `excluded_source_type`."""
    r = _row(device_category="alpr", confidence=70, identifier_type="mac",
             identifier="aa:bb:cc:dd:ee:ff", source_type="inferred")
    assert _assign_drop_bin(
        r, EXPORT_HIGH_CONFIDENCE_FLOOR, drop_pi_self_exclude=True,
        drop_source_types=EXCLUDED_SOURCE_TYPES,
    ) == "excluded_source_type"


def test_drop_bin_excluded_source_type_standard_export_passes() -> None:
    """CP19 is high-conf only: standard export (empty drop_source_types)
    lets crowdsourced/inferred rows survive."""
    r = _row(device_category="alpr", confidence=75, identifier_type="mac",
             identifier="aa:bb:cc:dd:ee:ff", source_type="crowdsourced")
    assert _assign_drop_bin(
        r, EXPORT_STANDARD_FLOOR, drop_pi_self_exclude=False,
        drop_source_types=frozenset(),
    ) is None


def test_drop_bin_excluded_source_type_priority_below_confidence() -> None:
    """Priority: crowdsourced + conf<floor attributes to below_confidence_threshold
    (more specific) NOT to excluded_source_type. The CP19 bin only catches
    rows that would otherwise have survived every prior gate."""
    r = _row(device_category="alpr", confidence=50, identifier_type="mac",
             identifier="aa:bb:cc:dd:ee:ff", source_type="crowdsourced")
    assert _assign_drop_bin(
        r, EXPORT_HIGH_CONFIDENCE_FLOOR, drop_pi_self_exclude=True,
        drop_source_types=EXCLUDED_SOURCE_TYPES,
    ) == "below_confidence_threshold"


def test_drop_bin_excluded_source_type_priority_below_unknown_category() -> None:
    """A crowdsourced row with device_category='unknown' attributes to
    unknown_category (§11 #13 priority over CP19)."""
    r = _row(device_category="unknown", confidence=75, identifier_type="oui",
             identifier="aa:bb:cc", source_type="crowdsourced")
    assert _assign_drop_bin(
        r, EXPORT_HIGH_CONFIDENCE_FLOOR, drop_pi_self_exclude=True,
        drop_source_types=EXCLUDED_SOURCE_TYPES,
    ) == "unknown_category"


def test_drop_bin_excluded_source_type_default_drop_source_types_empty() -> None:
    """Default value of drop_source_types is the empty frozenset — preserves
    pre-CP19 behavior for callers that don't pass the kwarg (used in
    pre-existing tests across this file)."""
    r = _row(device_category="alpr", confidence=75, identifier_type="mac",
             identifier="aa:bb:cc:dd:ee:ff", source_type="crowdsourced")
    # No drop_source_types passed → defaults to frozenset() → survives.
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
        # 4: standard survivor, drops to self_exclude in high-conf (Pi OUI).
        dict(rid=4, identifier="b8:27:eb", source_type="crowdsourced",
             device_category="alpr", confidence=80),
        # 5: standard survivor; CP19 drops to excluded_source_type in high-conf
        # (crowdsourced source_type with no §8.3 cross-band corroboration).
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
    assert s.excluded_source_type == 0  # CP19: standard export doesn't apply CP19 filter
    assert s.survivors == 2            # rows 4 and 5
    sum_bins_s = (
        s.unknown_category + s.procurement_only + s.self_exclude_oui +
        s.below_confidence_threshold + s.oversized_mac_range +
        s.ssid_pattern + s.device_fingerprint + s.excluded_source_type
    )
    assert sum_bins_s + s.survivors == n

    # High-confidence export tally.
    h = report.drop_tally_high_confidence
    assert h.procurement_only == 1
    assert h.unknown_category == 1
    assert h.oversized_mac_range == 1
    assert h.self_exclude_oui == 1     # row 4 drops here
    assert h.excluded_source_type == 1  # CP19: row 5 (crowdsourced, conf=80) drops here
    assert h.survivors == 0            # CP19 closes the last survivor path for crowdsourced rows
    sum_bins_h = (
        h.unknown_category + h.procurement_only + h.self_exclude_oui +
        h.below_confidence_threshold + h.oversized_mac_range +
        h.ssid_pattern + h.device_fingerprint + h.excluded_source_type
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


# ────────────────────────────────────────────────────────────────────────────
# MAC-535 §6.2 alias-tokenization defense (Finding 1)
#
# The naive comma-split of manufacturers.aliases yielded corporate-suffix
# tokens ("Ltd.", "Inc.", "LLC", "THE", "Co.") that inflated per-vendor
# §6.2 corroboration counts for 17 active vendors. The 3-layer defense:
# (1) quote-aware split (structural), (2) corporate-suffix stop-list
# (defense-in-depth), (3) min-length floor (length-4 minimum).
# These tests pin all three layers + the per-vendor end-to-end on the
# affected 17 vendors.
# ────────────────────────────────────────────────────────────────────────────


def test_corp_suffix_stoplist_constant_matches_cto_catalogue() -> None:
    """The stop-list constant is exactly the catalogue cited in
    operator_review/MAC-533/cto_ratification.md §Finding 2. Sibling test
    in this file (test_alias_tokens_drop_only_stoplist_catalog) asserts
    no off-catalogue entries. If a future addition is needed, update the
    catalogue + the MAC-535 analysis doc + this constant together."""
    assert _CORP_SUFFIX_STOPLIST == frozenset({
        "ltd", "ltd.", "inc", "inc.", "llc", "co.", "co", "the",
    })


def test_is_bogus_token_corp_suffix_case_insensitive() -> None:
    """Layer 2: case-insensitive corporate-suffix match. Verifies each
    catalogued suffix in upper/lower/title case."""
    for sfx in ("Ltd", "LTD", "ltd.", "Inc", "INC", "inc.", "INC.",
                "LLC", "llc", "Co.", "CO.", "co", "Co", "THE", "the"):
        assert _is_bogus_token(sfx), f"{sfx!r} should be classified bogus"
    for keep in ("LTD Inc", "Honeywell", "Hikvision",
                 "Hangzhou Hikvision Digital Technology Co.",
                 "Numerex Corp.", "WatchGuard"):
        assert not _is_bogus_token(keep), f"{keep!r} should be kept"


def test_is_bogus_token_min_length_floor() -> None:
    """Layer 3: tokens shorter than the floor are dropped. Catalogued
    stop-list members ≤3 chars (none today; 'THE' is 3, caught by layer
    2 too) but the length floor catches future additions cleanly."""
    assert _is_bogus_token("ab")     # 2 chars
    assert _is_bogus_token("L3")     # 2 chars (WatchGuard alias — too short)
    assert _is_bogus_token("a")      # 1 char
    assert _is_bogus_token("")       # empty
    assert not _is_bogus_token("Flock")        # 5 chars, not stop-listed
    assert not _is_bogus_token("Hikvision")    # 9 chars


def test_split_alias_blob_bare_value_with_embedded_comma() -> None:
    """Layer 1, no-quote case: an unquoted value with an embedded comma
    splits into 2 tokens (current data shape). The bogus filter in
    `_alias_tokens_for_vendor` catches the bogus one; layer 1 is a
    no-op on unquoted data."""
    # Verbatim Hikvision shape from db/argus.db:
    blob = "Hangzhou Hikvision Digital Technology Co., Ltd."
    toks = _split_alias_blob(blob)
    # Naive split on a quoted-vs-bare value: this blob has NO quotes so
    # we DO split on the embedded comma. The bogus filter then drops " Ltd.".
    assert "Hangzhou Hikvision Digital Technology Co." in toks
    # " Ltd." is the raw shape (with leading space — the literal substring
    # between the comma and "Ltd."); `_alias_tokens_for_vendor` then strips
    # whitespace + drops via stop-list before exposing the token list.
    assert any("Ltd." in t for t in toks)


def test_split_alias_blob_quoted_value_with_embedded_comma() -> None:
    """Layer 1, quote case: a properly quoted value with an embedded
    comma is ONE token. Future-proofs the parser against properly-
    constructed alias rows without relying on layer 2 to clean up."""
    blob = ('Hangzhou Hikvision Digital Technology, "Hangzhou Hikvision '
            'Digital Technology Co., Ltd.",EZVIZ,HiLook')
    toks = _split_alias_blob(blob)
    # The quoted phrase survives intact as a single token.
    assert "Hangzhou Hikvision Digital Technology Co., Ltd." in toks
    # The bare comma-separated phrase also survives.
    assert "Hangzhou Hikvision Digital Technology" in toks
    # Plus the unqualified tokens.
    assert "EZVIZ" in toks
    assert "HiLook" in toks


def test_split_alias_blob_handles_trailing_and_double_commas() -> None:
    """Layer 1, edge cases: trailing comma, doubled comma, leading comma,
    whitespace-only token. None of these appear on canonical data but
    the parser must not crash."""
    toks = _split_alias_blob("a,,b, ,c,")
    # 'a', 'b', 'c' survive; empty / whitespace tokens are dropped.
    assert toks == ["a", "b", "c"]


def test_alias_tokens_for_vendor_returns_canonical_when_no_row() -> None:
    """If a manufacturer row is absent, fall back to [canonical] verbatim —
    the legacy behavior is preserved (a downstream code path that names a
    non-canonical manufacturer still gets a deterministic LIKE token)."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("""
        CREATE TABLE manufacturers (
          id INTEGER PRIMARY KEY,
          canonical_name TEXT NOT NULL UNIQUE,
          aliases TEXT,
          primary_category TEXT,
          source_url TEXT,
          notes TEXT,
          added_at DATETIME
        );
    """)
    c.commit()
    assert _alias_tokens_for_vendor(c, "Unknown Vendor") == ["Unknown Vendor"]
    c.close()


def test_alias_tokens_for_vendor_preserves_canonical_name() -> None:
    """The canonical_name is always present in the token list (it's
    added before the bogus-filter pass); it must never be filtered out
    even if it would otherwise be a stop-list match."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("""
        CREATE TABLE manufacturers (
          id INTEGER PRIMARY KEY,
          canonical_name TEXT NOT NULL UNIQUE,
          aliases TEXT,
          primary_category TEXT,
          source_url TEXT,
          notes TEXT,
          added_at DATETIME
        );
    """)
    c.execute(
        "INSERT INTO manufacturers (canonical_name, aliases, source_url) "
        "VALUES (?, ?, ?)",
        ("Test Vendor", "Flock, Ltd., Inc.", "http://x"),
    )
    c.commit()
    toks = _alias_tokens_for_vendor(c, "Test Vendor")
    assert toks[0] == "Test Vendor"
    # Bogus tokens dropped; genuine kept.
    assert "Flock" in toks
    assert "Ltd." not in toks
    assert "Inc." not in toks
    c.close()


def test_alias_tokens_drop_only_stoplist_catalog_hikvision(conn: sqlite3.Connection) -> None:
    """End-to-end on Hikvision (id=209) — the canonical §6.2 regression
    case cited in MAC-533 §cto_ratification Finding 2.

    Pre-fix tokenization included `Ltd.` (matched 8,660 bogus FCC rows).
    Post-fix drops `Ltd.`; the `Hangzhou Hikvision Digital Technology`
    token remains and matches the 1 genuine FCC grantee (see
    operator_review/MAC-535/tokenization_analysis.md).
    """
    conn.execute(
        "INSERT INTO manufacturers (canonical_name, aliases, source_url) VALUES (?, ?, ?)",
        (
            "Hikvision",
            "Hangzhou Hikvision Digital Technology, HikCentral, HikConnect,"
            "Hangzhou Hikvision Digital Technology Co., Ltd.,"
            "EZVIZ,HiLook,Hikmicro,HiWatch,Annke,LaView",
            "http://ipvm/reports/hikvision-oem-directory",
        ),
    )
    conn.commit()
    toks = _alias_tokens_for_vendor(conn, "Hikvision")
    # Bogus tokens dropped.
    assert "Ltd." not in toks
    assert "Inc." not in toks
    assert "LLC" not in toks
    assert "THE" not in toks
    # Genuine aliases preserved.
    assert "Hikvision" in toks
    assert "Hangzhou Hikvision Digital Technology" in toks
    assert "HikCentral" in toks
    assert "HikConnect" in toks
    assert "EZVIZ" in toks
    assert "HiLook" in toks
    assert "Hikmicro" in toks
    assert "HiWatch" in toks
    assert "Annke" in toks
    assert "LaView" in toks


def test_alias_tokens_drop_only_stoplist_catalog_motorola(conn: sqlite3.Connection) -> None:
    """End-to-end on Motorola Solutions — the second-largest bogus-token
    offender cited in MAC-533 §cto_ratification Finding 2 (Inc. bogus,
    5,163 FCC matches)."""
    conn.execute(
        "INSERT INTO manufacturers (canonical_name, aliases, source_url) VALUES (?, ?, ?)",
        (
            "Motorola Solutions",
            "Motorola Vigilant, Motorola APX, Motorola V300, Motorola V500,"
            "Motorola Solutions Canada Inc.,Motorola Solutions Germany GmbH,"
            "MOTOROLA SOLUTIONS CONNECTIVITY, INC.,"
            "Flock Safety, Motorola Solutions,Motorola Solutions L6Q,"
            "Axon, Motorola Solutions",
            "http://bible",
        ),
    )
    conn.commit()
    toks = _alias_tokens_for_vendor(conn, "Motorola Solutions")
    # Bogus suffix stripped (token-level, not substring):
    assert not any(t.strip().lower() == "inc." for t in toks)
    assert not any(t.strip().lower() == "inc" for t in toks)
    # Genuine aliases preserved (including "Inc." inside longer tokens —
    # substring matches aren't filtered, only whole-token matches).
    assert "Motorola Solutions Canada Inc." in toks
    assert "Motorola Solutions Germany GmbH" in toks
    assert "Motorola APX" in toks
    assert "Motorola V300" in toks
    assert "Motorola V500" in toks


def test_alias_tokens_keep_genuine_substring_matches(conn: sqlite3.Connection) -> None:
    """Defense against over-filtering: tokens that CONTAIN a stop-listed
    substring but are NOT stop-listed tokens themselves are preserved.
    E.g., 'LLC d.b.a. WatchGuard Video' is NOT a stop-listed token (the
    stop-list is exact-match, not substring), so it must survive even
    though it contains the substring 'LLC'.

    NOTE on WatchGuard data shape: the on-disk value
    `Enforcement Video, LLC (d.b.a. WatchGuard Video)` was stored without
    quote-wrapping, so it splits into 2 tokens at the inner comma. The
    resulting "LLC (d.b.a. WatchGuard Video)" survives (length-30+
    token, not on stop-list) and is highly specific (only matches rows
    with that exact phrase in the corpus). This is benign — extreme
    precision rather than extreme breadth."""
    conn.execute(
        "INSERT INTO manufacturers (canonical_name, aliases, source_url) VALUES (?, ?, ?)",
        (
            "WatchGuard",
            "WatchGuard Video, WatchGuard Video (legacy),"
            "Enforcement Video, LLC (d.b.a. WatchGuard Video),"
            "WatchGuard Technologies, Inc.,L3, WatchGuard,"
            "Motorola WatchGuard",
            "http://bible",
        ),
    )
    conn.commit()
    toks = _alias_tokens_for_vendor(conn, "WatchGuard")
    # Bare "LLC" and "Inc." tokens are dropped (whole-token match).
    assert not any(t.strip() == "LLC" for t in toks)
    assert not any(t.strip() == "Inc." for t in toks)
    # The longer phrase containing "LLC" survives (not a stop-list match).
    assert "LLC (d.b.a. WatchGuard Video)" in toks
    # "L3" is dropped by min-length floor (2 chars < 4).
    assert "L3" not in toks
    # WatchGuard Technologies is preserved (whole-token match).
    assert "WatchGuard Technologies" in toks
    assert "Motorola WatchGuard" in toks
    # Genuine aliases preserved.
    assert "WatchGuard Video" in toks
    assert "WatchGuard Video (legacy)" in toks
    assert "Enforcement Video" in toks
