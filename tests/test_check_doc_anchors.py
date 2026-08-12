"""MAC-699 / MAC-717 -- proof fixtures for ``scripts/check_doc_anchors.py``.

The gate's job is to make the v1.7.0 doc surface's headline numeric claims
mechanically checkable, the way ``scripts/check_prose_dashes.py`` made the
em-dash ban mechanical. Per R9 the gate is decoration until it is shown
failing on an input it should reject, and per R7 a green result is not
evidence the gate works. Every check therefore has a positive control
beside the negative control it must clear.

Argument defended in this file (in seven parts):

  T1  bundle shape:  a frozen bundle of 13 settling queries keyed by metric,
      with one CHECK-parsing key per enum cardinality and ``is_arm=1`` for
      the OEM arm count (NOT ``parent_manufacturer_id IS NOT NULL``, which
      over-reports by 2 -- Trap 2). Plus the 4 settling ARTIFACTS, and the
      structural guarantee that no feed count is settled by SQL (Trap 4).

  T2  settling queries run read-only:  the runner opens ``db/argus.db`` via
      ``file:...?mode=ro`` and never executes an INSERT / UPDATE / DELETE /
      COMMIT. The fixture asserts the SQLite connection is read-only by
      catching a ``sqlite3.OperationalError`` on a probe write.

  T3  claim registry and extraction:  every Class A site carries a content
      anchor (never a line number -- MAC-717) and a regex that extracts the
      claimed integer. Each fixture gives the regex a representative line
      and asserts the extracted integer.

  T4  artifact counters:  the JSON entry counter and the CSV data-row
      counter, each checked against a known-good input AND against the
      naive instruments that get it wrong (``len(rows) - 1``, physical
      line count, ``#``-prefix filtering).

  T5  resolution semantics:  a content anchor resolves only when it matches
      exactly one line in its window. Zero matches and two-or-more matches
      are both ERROR. The section scope is load-bearing: the CHANGELOG's
      per-release line formats repeat verbatim across every prior release,
      so an unscoped anchor would bind to a historical section.

  T6  per-site positive control:  for EVERY settleable Class A site,
      perturb that site's number in a scratch copy of the real doc surface
      and assert the gate reports FAIL *at that site*. This is what makes
      the MAC-717 re-pin a fix rather than a relocation of the blindness --
      a re-pin that points at a line the gate cannot fail on has moved the
      blind spot, not removed it.

  T7  artifact-side positive control:  perturb the emitted artifact and
      leave the docs untouched. The doc sites bound to that artifact must
      go red, and the sites bound to canonical must NOT -- which is also
      the proof that the two settling instruments are genuinely distinct
      rather than two readings of the same number.

The scratch repo is a copy of the LIVE doc surface, not a synthetic one, so
these controls exercise the real anchors against the real prose. The 26 MB
CSV is symlinked rather than copied; no test writes through the link.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "check_doc_anchors.py"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("check_doc_anchors", GATE)
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules before exec_module so dataclass / typing
    # helpers that look up the module's __dict__ via sys.modules find it.
    sys.modules.setdefault("check_doc_anchors", module)
    spec.loader.exec_module(module)
    return module


gate_mod = _load_gate_module()


# ---------------------------------------------------------------------------
# T1: bundle shape -- the 13 settling queries, the 4 settling artifacts, the
# CHECK-parsing keys (Trap 1), the `is_arm=1` discipline (Trap 2), and the
# structural ban on settling a feed count with SQL (Trap 4).
# ---------------------------------------------------------------------------


def test_t1_bundle_has_thirteen_settling_queries():
    """The bundle holds exactly 13 settling-query entries, frozen."""
    bundle = gate_mod.SETTLE_QUERIES
    assert len(bundle) == 13, (
        f"Bundle should hold exactly 13 settling queries; got {len(bundle)}: "
        f"{sorted(bundle.keys())}"
    )


def test_t1_bundle_keys_are_the_brief_keys():
    """Each settling-query key in the bundle matches the brief verbatim."""
    expected = {
        "identifiers_active",
        "identifiers_total",
        "manufacturers",
        "manufacturers_arms",
        "sources",
        "schema_version",
        "behavioral_signatures",
        "raw_observations",
        "extraction_runs",
        "deployment_observations",
        "procurement_records",
        "device_category_enum",
        "identifier_type_enum",
    }
    assert set(gate_mod.SETTLE_QUERIES.keys()) == expected


def test_t1_arm_count_uses_is_arm_not_parent_link():
    """Trap 2: arm count uses `is_arm=1`, not `parent_manufacturer_id IS NOT NULL`.

    `parent_manufacturer_id IS NOT NULL` over-reports by 2 -- the Amcrest and
    Lorex to Dahua alias links carry a parent link without being arms. The
    bundle must use `is_arm=1`.
    """
    arms_q = gate_mod.SETTLE_QUERIES["manufacturers_arms"]
    assert "is_arm=1" in arms_q
    assert "parent_manufacturer_id" not in arms_q


def test_t1_enum_cardinality_uses_check_constraint_not_distinct():
    """Trap 1: enum cardinality parses the CHECK constraint, never COUNT(DISTINCT).

    The README device-category and identifier-type claims are correct as
    CHECK-enum cardinality. COUNT(DISTINCT) would yield 19 and 51 on the live
    DB and would confidently propose regressions. The bundle entries for the
    two enum-cardinality keys must NOT be plain `SELECT COUNT(DISTINCT ...)`
    queries -- they must invoke the CHECK parser.
    """
    cat_key = gate_mod.SETTLE_QUERIES["device_category_enum"]
    type_key = gate_mod.SETTLE_QUERIES["identifier_type_enum"]
    assert "COUNT(DISTINCT" not in cat_key, (
        f"device_category_enum must not use COUNT(DISTINCT); got {cat_key!r}"
    )
    assert "COUNT(DISTINCT" not in type_key, (
        f"identifier_type_enum must not use COUNT(DISTINCT); got {type_key!r}"
    )
    assert cat_key.startswith("PARSE_CHECK:")
    assert type_key.startswith("PARSE_CHECK:")


def test_t1_settle_artifacts_shape():
    """The 4 settling artifacts: three feeds by JSON entry count, CSV by rows."""
    arts = gate_mod.SETTLE_ARTIFACTS
    assert set(arts) == {
        "feed_standard",
        "feed_high_confidence",
        "feed_behavioral",
        "csv_data_rows",
    }
    for key in ("feed_standard", "feed_high_confidence", "feed_behavioral"):
        relpath, kind = arts[key]
        assert kind == "json_entries", f"{key} must settle by JSON entry count"
        assert relpath.startswith("exports/")
    assert arts["csv_data_rows"] == ("exports/argus_export.csv", "csv_data_rows")


def test_t1_no_feed_count_is_settled_by_sql():
    """Trap 4: a feed count has no DB-side answer, so no SQL may claim to give one.

    A row can clear the confidence floor and still bin out before the feed
    (`device_category='unknown'` bins out first; `geographic_scope IS NULL`
    passes the standard feed and fails high-confidence). Any query that
    resembles the export predicate disagrees with the product. The structural
    guarantee is that the feed keys live in SETTLE_ARTIFACTS and nowhere in
    SETTLE_QUERIES.
    """
    feed_keys = {"feed_standard", "feed_high_confidence", "feed_behavioral"}
    assert not (feed_keys & set(gate_mod.SETTLE_QUERIES)), (
        "a feed count must never be settled by a SQL query"
    )
    # And every claim printing a feed count must reference an artifact key.
    for claim in gate_mod.CLASS_A_CLAIMS:
        if "feed" in claim["description"] or "export rows" in claim["description"]:
            assert claim["settle_key"] not in gate_mod.SETTLE_QUERIES, (
                f"{claim['description']!r} settles a feed count against SQL"
            )


# ---------------------------------------------------------------------------
# T2: settling queries run read-only against db/argus.db via the URI form.
# ---------------------------------------------------------------------------


def test_t2_settling_runner_opens_db_read_only():
    """The runner opens `db/argus.db` via the `file:...?mode=ro` URI form.

    A probe write inside the same connection must raise OperationalError.
    This is the load-bearing assertion that the gate is read-only against
    canonical -- no INSERT / UPDATE / DELETE / commit anywhere.
    """
    db_path = REPO / "db" / "argus.db"
    con = gate_mod._open_db_ro(db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            con.execute("UPDATE identifiers SET confidence = 0 WHERE id = 1")
    finally:
        con.close()


def test_t2_gate_source_contains_no_sql_write_ops():
    """The gate's source has no INSERT/UPDATE/DELETE/COMMIT outside docstrings.

    The brief explicitly forbids writes. A reviewer grepping for SQL write
    operations should find only docstring mentions. We strip comments and
    docstrings before grepping so this remains a load-bearing structural
    invariant rather than a comment-policing test.
    """
    src = GATE.read_text(encoding="utf-8")
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    src = "\n".join(
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    )
    assert "INSERT" not in src, "gate source contains INSERT"
    assert "DELETE" not in src, "gate source contains DELETE"
    assert "UPDATE" not in src, "gate source contains UPDATE"
    assert ".commit(" not in src, "gate source contains .commit()"
    assert "executemany" not in src, "gate source contains executemany"


def test_t2_settling_runner_returns_expected_keys():
    """The runner returns a dict keyed by every bundle key, including the
    two CHECK-parsing entries. Each CHECK-parsing entry's value is the int
    cardinality of the parsed CHECK clause.
    """
    results = gate_mod.run_settling_queries(REPO / "db" / "argus.db")
    for k in gate_mod.SETTLE_QUERIES:
        assert k in results, f"missing result for settling-query key {k!r}"
    assert isinstance(results["device_category_enum"], int)
    assert isinstance(results["identifier_type_enum"], int)


def test_t2_artifact_runner_returns_every_key_with_no_problems():
    """Against the live tree, every settling artifact parses cleanly."""
    results, problems = gate_mod.run_settling_artifacts(REPO)
    assert problems == {}, f"unreadable settling artifacts: {problems}"
    assert set(results) == set(gate_mod.SETTLE_ARTIFACTS)
    for key, value in results.items():
        assert isinstance(value, int) and value > 0, f"{key} settled to {value!r}"


# ---------------------------------------------------------------------------
# T3: claim registry shape and extraction regexes.
# ---------------------------------------------------------------------------


def test_t3_every_class_a_claim_is_content_anchored():
    """Every Class A site carries a content anchor and NO line number.

    MAC-717: positional pins slid off their claim sites when MAC-708
    renumbered CHANGELOG.md. A `line` key reappearing here is the
    regression this test exists to catch.
    """
    settleable = set(gate_mod.SETTLE_QUERIES) | set(gate_mod.SETTLE_ARTIFACTS)
    for claim in gate_mod.CLASS_A_CLAIMS:
        assert "file" in claim
        assert "description" in claim
        assert "extract_pattern" in claim
        assert claim.get("anchor"), f"{claim['description']!r} has no content anchor"
        assert "line" not in claim, (
            f"{claim['description']!r} carries a positional pin; MAC-717 removed these"
        )
        sk = claim.get("settle_key")
        assert sk in settleable or sk == gate_mod.NO_SETTLING_QUERY, (
            f"claim {claim['description']!r} has settle_key={sk!r}, which is "
            f"neither a settling key nor NO_SETTLING_QUERY"
        )


def test_t3_class_b_and_c_carry_no_line_numbers():
    """Skip-list entries are described by content locator, not line number.

    A skip-list that points at the wrong line is a skip nobody can audit.
    Four of the seven original Class B pins had already slid onto unrelated
    text by HEAD 7b0d8f9.
    """
    for site in list(gate_mod.CLASS_B_SITES) + list(gate_mod.CLASS_C_SITES):
        assert "line" not in site, f"{site} carries a positional pin"
        assert site.get("locator"), f"{site} has no content locator"
        assert site.get("reason"), f"{site} has no skip reason"


def test_t3_class_a_descriptions_are_unique_per_file():
    """(file, description) identifies a claim site -- the tests key on it."""
    seen = set()
    for claim in gate_mod.CLASS_A_CLAIMS:
        key = (claim["file"], claim["description"])
        assert key not in seen, f"duplicate claim site {key}"
        seen.add(key)


# One representative line per Class A site, and the integer its regex must
# pull out. Shared by the extraction fixtures and by the coverage test that
# forbids adding a Class A site without one.
_EXTRACT_FIXTURES = [
        (
            "README.md", "active canonical identifiers",
            "- **43,116 active canonical identifiers**, the things you query against",
            43116,
        ),
        (
            "README.md", "total manufacturers",
            "- **240 manufacturers**, surveillance vendors classified by what they make",
            240,
        ),
        (
            "README.md", "OEM arms (first)",
            "92 of those are OEM arms, the rebadging brands a parent vendor sells through",
            92,
        ),
        (
            "README.md", "vendors",
            "Argus lists 240 vendors, 92 of them OEM arms that exist to attribute",
            240,
        ),
        (
            "README.md", "OEM arms (second)",
            "Argus lists 240 vendors, 92 of them OEM arms that exist to attribute",
            92,
        ),
        (
            "README.md", "CSV export row count",
            "| `exports/argus_export.csv` | 43,116 | Bulk import, analysis, or re-derivation. |",
            43116,
        ),
        (
            "README.md", "high-conf feed",
            "| `exports/argus_export_high_confidence.json` | 481 | Runtime scanners (Lynceus). |",
            481,
        ),
        (
            "README.md", "standard feed",
            "| `exports/argus_export.json` | 981 | Broader scanner watchlists. |",
            981,
        ),
        (
            "README.md", "behavioral feed",
            "| `exports/argus_export_behavioral_signatures.json` | 132 | Cellular-band scanners. |",
            132,
        ),
        (
            "CHANGELOG.md", "standard feed (CHANGELOG feed-totals)",
            "**Feed totals.** Standard 977 to **983**, high-confidence 481 to **501**, behavioral **132** unchanged.",
            983,
        ),
        (
            "CHANGELOG.md", "high-conf feed (CHANGELOG feed-totals)",
            "**Feed totals.** Standard 977 to **983**, high-confidence 481 to **501**, behavioral **132** unchanged.",
            501,
        ),
        (
            "CHANGELOG.md", "behavioral feed (CHANGELOG feed-totals)",
            "**Feed totals.** Standard 977 to **983**, high-confidence 481 to **501**, behavioral **132** unchanged.",
            132,
        ),
        (
            "CHANGELOG.md", "standard feed (CHANGELOG data line)",
            "- **Lynceus standard feed:** 977 → **983** (+43 / −37). **high-confidence feed:** 481 → **501** (+25 / −5). **behavioral-signatures feed:** **132**. **CSV:** **43,088** rows.",
            983,
        ),
        (
            "CHANGELOG.md", "high-conf feed (CHANGELOG data line)",
            "- **Lynceus standard feed:** 977 → **983** (+43 / −37). **high-confidence feed:** 481 → **501** (+25 / −5). **behavioral-signatures feed:** **132**. **CSV:** **43,088** rows.",
            501,
        ),
        (
            "CHANGELOG.md", "behavioral feed (CHANGELOG data line)",
            "- **Lynceus standard feed:** 977 → **983** (+43 / −37). **high-confidence feed:** 481 → **501** (+25 / −5). **behavioral-signatures feed:** **132**. **CSV:** **43,088** rows.",
            132,
        ),
        (
            "CHANGELOG.md", "CSV row count (CHANGELOG)",
            "- **Lynceus standard feed:** 977 → **983** (+43 / −37). **high-confidence feed:** 481 → **501** (+25 / −5). **behavioral-signatures feed:** **132**. **CSV:** **43,088** rows.",
            43088,
        ),
        (
            "CHANGELOG.md", "halts",
            "- None. `coverage_matrix` `_reconcile` halts: **0**. The CSV reconciles to canonical active, 43,088 = 43,088.",
            0,
        ),
        (
            "CHANGELOG.md", "reconciliation, CSV side",
            "- None. `coverage_matrix` `_reconcile` halts: **0**. The CSV reconciles to canonical active, 43,088 = 43,090.",
            43088,
        ),
        (
            "CHANGELOG.md", "reconciliation, canonical side",
            "- None. `coverage_matrix` `_reconcile` halts: **0**. The CSV reconciles to canonical active, 43,088 = 43,090.",
            43090,
        ),
        (
            "docs/USER_GUIDE.md", "high-conf export rows (USER_GUIDE)",
            "### `exports/argus_export_high_confidence.json` (501 rows at v1.7.0)",
            501,
        ),
        (
            "docs/USER_GUIDE.md", "standard export rows (USER_GUIDE)",
            "### `exports/argus_export.json` (983 rows at v1.7.0)",
            983,
        ),
        (
            "docs/USER_GUIDE.md", "CSV data rows (USER_GUIDE)",
            "### `exports/argus_export.csv` (43,088 data rows at v1.7.0)",
            43088,
        ),
]


@pytest.mark.parametrize("file, description, text, expected", _EXTRACT_FIXTURES)
def test_t3_extract(file, description, text, expected):
    """Each Class A regex pulls the right integer out of a representative line.

    The two reconciliation cases use DIFFERENT operands (43,088 = 43,090) on
    purpose: a pattern that captured the wrong side would still look correct
    against the real line, where both operands are equal.
    """
    claim = _find_claim(file, description)
    assert gate_mod.extract_claim(claim, text) == expected


def test_t3_every_class_a_site_is_covered_by_an_extract_fixture():
    """No Class A site may be added without an extraction fixture beside it."""
    covered = {(file, description) for file, description, _, _ in _EXTRACT_FIXTURES}
    registered = {(c["file"], c["description"]) for c in gate_mod.CLASS_A_CLAIMS}
    assert registered <= covered, f"Class A sites with no extract fixture: {registered - covered}"


# ---------------------------------------------------------------------------
# T4: artifact counters, each against a known-good AND a known-bad instrument.
# ---------------------------------------------------------------------------


def test_t4_json_entry_counter(tmp_path):
    """The counter reads the `entries` key (the on-disk shape), not `_meta`."""
    path = tmp_path / "feed.json"
    path.write_text(
        json.dumps(
            {
                "_meta": {"record_count": 999},
                "entries": [
                    {"pattern": "a", "pattern_type": "oui"},
                    {"pattern": "b", "pattern_type": "oui"},
                ],
            }
        ),
        encoding="utf-8",
    )
    # Known-good: two entries. Known-bad: the artifact's own `record_count`
    # meta field says 999, which is exactly the number the CHANGELOG's
    # reconciliation line says not to trust.
    assert gate_mod.count_json_entries(path) == 2


def test_t4_csv_data_row_counter_skips_meta_and_header(tmp_path):
    """Known-good vs the three naive instruments that get this wrong.

    The real CSV opens with a `# meta:` provenance comment (row 0), then the
    column header (row 1). Some `source_excerpt` values contain embedded
    newlines, so physical lines outnumber records and a wrapped line can
    itself begin with `#`.
    """
    path = tmp_path / "argus_export.csv"
    path.write_text(
        "# meta: schema_version=35, record_count=3\n"
        "argus_record_id,identifier,source_excerpt\n"
        "aaa,00:11:22,plain\n"
        'bbb,33:44:55,"wrapped excerpt\n'
        '# this continuation line begins with a hash"\n'
        "ccc,66:77:88,plain\n",
        encoding="utf-8",
    )
    assert gate_mod.count_csv_data_rows(path) == 3

    # Known-bad instrument 1: physical line count (over-counts the wrap).
    physical = len(path.read_text(encoding="utf-8").splitlines())
    assert physical == 6 and physical != 3

    # Known-bad instrument 2: `len(rows) - 1` treats the meta row as the
    # header and double-counts one row.
    import csv as _csv
    with path.open(newline="", encoding="utf-8") as fh:
        naive = len(list(_csv.reader(fh))) - 1
    assert naive == 4 and naive != 3

    # Known-bad instrument 3: dropping every line that starts with `#`
    # eats the wrapped excerpt continuation and corrupts the parse.
    hash_filtered = [
        ln for ln in path.read_text(encoding="utf-8").splitlines()
        if not ln.startswith("#")
    ]
    assert len(hash_filtered) == 4  # header + 3 -- right count, corrupted data


def test_t4_artifact_runner_reports_missing_artifact_without_raising(tmp_path):
    """A missing export lands in `problems`, never as a traceback."""
    results, problems = gate_mod.run_settling_artifacts(tmp_path)
    assert results == {}
    assert set(problems) == set(gate_mod.SETTLE_ARTIFACTS)


# ---------------------------------------------------------------------------
# T4b: comparator -- extracted int vs settled value.
# ---------------------------------------------------------------------------


def test_t4_comparator_passes_on_match():
    res = gate_mod.compare_claim(
        {"file": "TEST.md", "description": "test", "settle_key": "sources"},
        extracted=98,
        settle_results={"sources": 98},
    )
    assert res.status == "PASS"
    assert res.settle_value == 98


def test_t4_comparator_fails_on_mismatch():
    res = gate_mod.compare_claim(
        {"file": "TEST.md", "description": "test", "settle_key": "sources"},
        extracted=42,
        settle_results={"sources": 98},
    )
    assert res.status == "FAIL"
    assert res.extracted == 42
    assert res.settle_value == 98


def test_t4_comparator_errors_when_settling_key_is_absent():
    """An unreadable artifact must surface as ERROR, not as a silent PASS."""
    res = gate_mod.compare_claim(
        {"file": "TEST.md", "description": "test", "settle_key": "feed_standard"},
        extracted=983,
        settle_results={},
    )
    assert res.status == "ERROR"


def test_t4_comparator_unsettled_never_fails():
    """A NO_SETTLING_QUERY claim is reported but must not FAIL the gate."""
    res = gate_mod.compare_claim(
        {
            "file": "CHANGELOG.md",
            "description": "halts",
            "settle_key": gate_mod.NO_SETTLING_QUERY,
        },
        extracted=0,
        settle_results={"sources": 98},
    )
    assert res.status == "UNSETTLED"


# ---------------------------------------------------------------------------
# T5: resolution semantics -- unique, missing, ambiguous, section-scoped.
# ---------------------------------------------------------------------------


def test_t5_unique_anchor_resolves():
    claim = gate_mod._claim("F.md", "d", "sources", r"count (\d+)")
    res = gate_mod.resolve_claim_site(claim, ["alpha", "count 98", "omega"])
    assert (res.line, res.error) == (2, "")


def test_t5_missing_anchor_is_an_error():
    claim = gate_mod._claim("F.md", "d", "sources", r"count (\d+)")
    res = gate_mod.resolve_claim_site(claim, ["alpha", "omega"])
    assert res.line is None and "matched no line" in res.error


def test_t5_ambiguous_anchor_is_an_error_not_a_first_match():
    """Two matches must ERROR. Taking the first would move the blindness."""
    claim = gate_mod._claim("F.md", "d", "sources", r"count (\d+)")
    res = gate_mod.resolve_claim_site(claim, ["count 98", "count 42"])
    assert res.line is None
    assert "ambiguous" in res.error and "1, 2" in res.error


def test_t5_section_scope_disambiguates_repeated_release_formats():
    """The load-bearing case: the same line format in every release section.

    Unscoped, this anchor matches both releases and must ERROR. Scoped to
    v1.7.0 it resolves to the current release's line and nothing else.
    """
    lines = [
        "## v1.7.0 - 2026-08-11",
        "- **Lynceus standard feed:** 977 → **983**",
        "## v1.6.14 - 2026-07-21",
        "- **Lynceus standard feed:** 945 → **977**",
    ]
    pattern = r"\*\*Lynceus standard feed:\*\*\s*[\d,]+\s*→\s*\*\*([\d,]+)\*\*"

    unscoped = gate_mod._claim("CHANGELOG.md", "d", "feed_standard", pattern)
    assert "ambiguous" in gate_mod.resolve_claim_site(unscoped, lines).error

    scoped = gate_mod._claim(
        "CHANGELOG.md", "d", "feed_standard", pattern, section=gate_mod.SECTION_V170
    )
    res = gate_mod.resolve_claim_site(scoped, lines)
    assert res.line == 2
    assert gate_mod.extract_claim(scoped, res.text) == 983


def test_t5_missing_section_heading_is_an_error():
    """If the release block is renamed, the gate says so instead of passing."""
    claim = gate_mod._claim(
        "CHANGELOG.md", "d", "feed_standard", r"feed (\d+)", section=gate_mod.SECTION_V170
    )
    res = gate_mod.resolve_claim_site(claim, ["## v1.6.14", "feed 977"])
    assert res.line is None and "matched 0 headings" in res.error


def test_t5_section_window_stops_at_the_next_h2_not_at_an_h3():
    """An `### ` subheading inside a release must not truncate the window."""
    lines = ["## v1.7.0", "### Data", "feed 983", "## v1.6.14", "feed 977"]
    claim = gate_mod._claim(
        "CHANGELOG.md", "d", "feed_standard", r"feed (\d+)", section=gate_mod.SECTION_V170
    )
    res = gate_mod.resolve_claim_site(claim, lines)
    assert res.line == 3


def test_t5_live_tree_resolves_every_class_a_site_uniquely():
    """Against the real doc surface, all 22 anchors resolve with no ERROR."""
    results = gate_mod.scan_docs(_live_settle(), REPO)
    errors = [r for r in results if r.status == "ERROR"]
    assert not errors, "\n".join(gate_mod._format_result(r) for r in errors)


# ---------------------------------------------------------------------------
# T6 / T7: positive controls against a scratch copy of the LIVE doc surface.
# ---------------------------------------------------------------------------


_DOC_FILES = sorted({c["file"] for c in gate_mod.CLASS_A_CLAIMS})


def _scratch_repo(tmp_path: Path) -> Path:
    """Copy the live doc surface + gate into ``tmp_path``; symlink exports.

    The exports are symlinked because ``argus_export.csv`` is 26 MB. No test
    writes through a link -- the artifact-perturbation control replaces the
    link with a real file first.
    """
    work = tmp_path / "repo"
    (work / "scripts").mkdir(parents=True)
    (work / "exports").mkdir(parents=True)
    for rel in _DOC_FILES:
        dst = work / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((REPO / rel).read_bytes())
    for relpath, _kind in gate_mod.SETTLE_ARTIFACTS.values():
        (work / relpath).symlink_to(REPO / relpath)
    (work / "scripts" / "check_doc_anchors.py").write_bytes(GATE.read_bytes())
    return work


def _run_gate(work: Path) -> tuple[int, str, str]:
    import subprocess
    result = subprocess.run(
        [
            sys.executable, "scripts/check_doc_anchors.py", "--list",
            "--db-path", str(REPO / "db" / "argus.db"),
        ],
        cwd=work,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def _status_of(stdout: str, claim: dict) -> str:
    """Pull the reported status for one claim site out of `--list` output."""
    for line in stdout.splitlines():
        status, _, rest = line.partition("  ")
        if rest.strip().startswith(f"{claim['file']}:") and claim["description"] in rest:
            return status.strip()
    raise AssertionError(
        f"no report line for {claim['file']}:{claim['description']!r}\n{stdout}"
    )


def _perturb_site(work: Path, claim: dict) -> tuple[int, int]:
    """Change the integer at ``claim``'s resolved site by +1, in place."""
    path = work / claim["file"]
    lines = path.read_text(encoding="utf-8").split("\n")
    res = gate_mod.resolve_claim_site(claim, lines)
    assert res.error == "", res.error
    m = re.search(claim["extract_pattern"], res.text)
    assert m, f"pattern did not match resolved line for {claim['description']!r}"
    group = next(i for i in range(1, (m.lastindex or 0) + 1) if m.group(i) is not None)
    raw = m.group(group)
    original = int(raw.replace(",", ""))
    mutated = original + 1
    rendered = f"{mutated:,}" if "," in raw else str(mutated)
    start, end = m.span(group)
    lines[res.line - 1] = res.text[:start] + rendered + res.text[end:]
    path.write_text("\n".join(lines), encoding="utf-8")
    return original, mutated


def _live_settle() -> dict:
    settle = gate_mod.run_settling_queries(REPO / "db" / "argus.db")
    artifacts, problems = gate_mod.run_settling_artifacts(REPO)
    assert problems == {}, problems
    settle.update(artifacts)
    return settle


_SETTLEABLE = [
    c for c in gate_mod.CLASS_A_CLAIMS if c["settle_key"] != gate_mod.NO_SETTLING_QUERY
]


def test_t6_negative_control_unperturbed_scratch_copy_is_green(tmp_path):
    """The scratch copy of the live docs exits 0 -- so a red arm means the
    perturbation, not the copy."""
    rc, out, err = _run_gate(_scratch_repo(tmp_path))
    assert rc == 0, f"stdout={out}\nstderr={err}"
    assert "0 ERROR" in out or "0 ERROR" in err


@pytest.mark.parametrize(
    "claim", _SETTLEABLE, ids=[f"{c['file']}::{c['description']}" for c in _SETTLEABLE]
)
def test_t6_every_settleable_site_goes_red_when_perturbed(claim, tmp_path):
    """Per-site positive control (MAC-717 acceptance #4).

    Perturb this site's number in a scratch copy of the real doc surface and
    require the gate to report FAIL *at this site*. A site that cannot be
    made to fail is a blind spot wearing a PASS.
    """
    work = _scratch_repo(tmp_path)
    original, mutated = _perturb_site(work, claim)
    rc, out, err = _run_gate(work)
    assert rc != 0, f"gate stayed green after {original} -> {mutated}\n{out}\n{err}"
    assert _status_of(out, claim) == "FAIL", (
        f"perturbing {original} -> {mutated} did not fail its own site\n{out}"
    )


def test_t6_halts_is_the_only_unsettleable_site(tmp_path):
    """The one remaining hole, pinned so a future site cannot quietly join it.

    The `_reconcile` halt tally has no settling instrument: the export path
    emits no machine-readable halt count, and the only tallies on disk are
    two HB-numbered prose lines in exports/coverage_report.md. Perturbing it
    therefore cannot go red -- which is exactly why it reports UNSETTLED and
    not PASS.
    """
    unsettleable = [
        c for c in gate_mod.CLASS_A_CLAIMS
        if c["settle_key"] == gate_mod.NO_SETTLING_QUERY
    ]
    assert [c["description"] for c in unsettleable] == ["halts"]

    work = _scratch_repo(tmp_path)
    claim = unsettleable[0]
    _perturb_site(work, claim)
    rc, out, _ = _run_gate(work)
    assert rc == 0
    assert _status_of(out, claim) == "UNSETTLED"


def test_t7_perturbing_the_standard_feed_artifact_reddens_its_doc_sites(tmp_path):
    """Artifact-side positive control: docs untouched, artifact moved.

    Proves the feed settling actually reads the emitted artifact. Without
    this arm, a PASS could come from an instrument that never opened the
    export at all.
    """
    work = _scratch_repo(tmp_path)
    relpath = gate_mod.SETTLE_ARTIFACTS["feed_standard"][0]
    doc = json.loads((REPO / relpath).read_text(encoding="utf-8"))
    doc["entries"] = doc["entries"][:-1]  # drop one entry
    (work / relpath).unlink()
    (work / relpath).write_text(json.dumps(doc), encoding="utf-8")

    rc, out, err = _run_gate(work)
    assert rc != 0, f"{out}\n{err}"
    bound = [c for c in gate_mod.CLASS_A_CLAIMS if c["settle_key"] == "feed_standard"]
    assert len(bound) == 4, [c["description"] for c in bound]
    for claim in bound:
        assert _status_of(out, claim) == "FAIL", claim["description"]


def test_t7_csv_and_canonical_are_distinct_instruments(tmp_path):
    """Perturbing the CSV artifact must NOT move the canonical-settled sites.

    README's CSV row is settled against canonical ("All active rows"); the
    CHANGELOG CSV sites are settled against the emitted file. If both were
    reading the same number, this arm could not distinguish them -- which is
    the whole point of settling the reconciliation sentence on both sides.
    """
    work = _scratch_repo(tmp_path)
    relpath = gate_mod.SETTLE_ARTIFACTS["csv_data_rows"][0]
    (work / relpath).unlink()
    (work / relpath).write_text(
        "# meta: schema_version=35, record_count=3\n"
        "argus_record_id,identifier\n"
        "aaa,00:11:22\n"
        "bbb,33:44:55\n"
        "ccc,66:77:88\n",
        encoding="utf-8",
    )
    rc, out, err = _run_gate(work)
    assert rc != 0, f"{out}\n{err}"

    for claim in gate_mod.CLASS_A_CLAIMS:
        expected = "FAIL" if claim["settle_key"] == "csv_data_rows" else None
        if expected:
            assert _status_of(out, claim) == "FAIL", claim["description"]
    readme_csv = _find_claim("README.md", "CSV export row count")
    assert _status_of(out, readme_csv) == "PASS", (
        "README's CSV row is settled against canonical and must be unmoved "
        "by an artifact-only perturbation"
    )


def test_t7_missing_artifact_errors_rather_than_crashing(tmp_path):
    """A deleted export names the claims it could not settle, exit 1, no traceback."""
    work = _scratch_repo(tmp_path)
    (work / gate_mod.SETTLE_ARTIFACTS["feed_behavioral"][0]).unlink()
    rc, out, err = _run_gate(work)
    assert rc == 1
    assert "Traceback" not in err
    assert "feed_behavioral" in err
    claim = _find_claim("README.md", "behavioral feed")
    assert _status_of(out, claim) == "ERROR"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _find_claim(file, description):
    """Find a Class A claim by file + description; raise if not found."""
    for c in gate_mod.CLASS_A_CLAIMS:
        if c["file"] == file and c["description"] == description:
            return c
    raise KeyError(f"no Class A claim for {(file, description)}")


def test_gate_module_imports():
    assert gate_mod is not None
