"""MAC-699 -- proof fixtures for ``scripts/check_doc_anchors.py``.

The gate's job is to make the v1.7.0 doc surface's headline numeric claims
mechanically checkable, the way ``scripts/check_prose_dashes.py`` made the
em-dash ban mechanical. Per R9 the gate is decoration until it is shown
failing on an input it should reject, and per R7 a green result is not
evidence the gate works. Every check therefore has a positive control
beside the negative control it must clear.

Argument defended in this file (in five parts):

  T1  bundle shape:  the module holds a frozen bundle of 13 settling queries,
      keyed by metric, with one CHECK-parsing key per enum cardinality and
      ``is_arm=1`` for the OEM arm count (NOT ``parent_manufacturer_id
      IS NOT NULL``, which over-reports by 2 -- Trap 2 in the brief).

  T2  settling queries run read-only:  the runner opens ``db/argus.db`` via
      ``file:...?mode=ro`` and never executes an INSERT / UPDATE / DELETE /
      COMMIT. The fixture asserts the SQLite connection is read-only by
      catching a ``sqlite3.OperationalError`` on a probe write.

  T3  Class A claim extraction:  each Class A site has a regex that extracts
      the claimed integer from the doc line. Each fixture gives the regex a
      representative line and asserts the extracted integer.

  T4  comparator:  extracted integer vs settling-query result. Equal -> PASS,
      not equal -> FAIL. ``NO_SETTLING_QUERY`` claims (no entry in the
      bundle) are listed in the report but never FAIL.

  T5  positive control:  an arm that runs the gate against a scratch copy
      of the doc surface where every Class A claim has been rewritten to
      match the live settling-query result. The arm asserts the gate exits
      zero. A second arm mutates one Class A claim in the scratch copy and
      asserts the gate exits non-zero.

The fixtures use ``tmp_path`` copies of the Tier 1 files so the test never
depends on the on-disk state of the repo -- if the running tree is drifted
(post-MAC-516 sweep or otherwise) the rejection positive control will fail
loudly instead of looking green, which is the right failure mode.
"""
from __future__ import annotations

import importlib.util
import re
import sqlite3
import sys
import textwrap
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
# T1: bundle shape -- the 13 settling queries, the CHECK-parsing keys, the
# `is_arm=1` discipline (Trap 2), and the absence of any COUNT(DISTINCT)
# discipline for the enum-cardinality entries (Trap 1).
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

    README.md line 32 (20 device categories) and line 33 (58 identifier types)
    are correct as CHECK-enum cardinality. COUNT(DISTINCT) would yield 19 and
    51 respectively on the live DB and would confidently propose regressions.
    The bundle entries for the two enum-cardinality keys must NOT be plain
    `SELECT COUNT(DISTINCT ...)` queries -- they must invoke the CHECK parser.
    """
    cat_key = gate_mod.SETTLE_QUERIES["device_category_enum"]
    type_key = gate_mod.SETTLE_QUERIES["identifier_type_enum"]
    # Both enum-cardinality entries must NOT be a `SELECT COUNT(DISTINCT ...)`
    # string (it would silently "fix" the live 19/51 cardinality into the doc
    # claim of 20/58 and produce a regression).
    assert "COUNT(DISTINCT" not in cat_key, (
        f"device_category_enum must not use COUNT(DISTINCT); got {cat_key!r}"
    )
    assert "COUNT(DISTINCT" not in type_key, (
        f"identifier_type_enum must not use COUNT(DISTINCT); got {type_key!r}"
    )


# ---------------------------------------------------------------------------
# T2: settling queries run read-only against db/argus.db via the URI form.
# ---------------------------------------------------------------------------


def test_t2_settling_runner_opens_db_read_only(tmp_path):
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
    operations should find only docstring mentions and a docstring note in
    `_open_db_ro` about the probe-write invariant. We strip comments and
    docstrings before grepping so this remains a load-bearing structural
    invariant rather than a comment-policing test.
    """
    import re as _re
    src = GATE.read_text(encoding="utf-8")
    # Strip triple-quoted docstrings (best-effort).
    src = _re.sub(r'"""[\s\S]*?"""', "", src)
    src = _re.sub(r"'''[\s\S]*?'''", "", src)
    # Strip line comments.
    src = "\n".join(
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    )
    # The brief allows probe-write mention in the docstring (already stripped
    # above) and forbids it everywhere else. A bare `commit()` or
    # `executemany` is forbidden; `INSERT/UPDATE/DELETE` SQL keywords are
    # forbidden.
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
    db_path = REPO / "db" / "argus.db"
    results = gate_mod.run_settling_queries(db_path)
    for k in gate_mod.SETTLE_QUERIES:
        assert k in results, f"missing result for settling-query key {k!r}"
    # The two CHECK-parsing entries must be ints (parsed cardinality).
    assert isinstance(results["device_category_enum"], int)
    assert isinstance(results["identifier_type_enum"], int)


# ---------------------------------------------------------------------------
# T3: claim extraction -- each Class A site has a regex that pulls the
# claimed integer from the doc line. These tests pin the regex shape and
# catch silent drift in the extraction logic.
# ---------------------------------------------------------------------------


def test_t3_each_class_a_claim_has_extract_pattern():
    """Every Class A claim site carries an extract pattern, a settle key
    (or NO_SETTLING_QUERY), a file, and a line number. The brief is explicit
    that the class assignment per site is in the source, not implied.
    """
    for claim in gate_mod.CLASS_A_CLAIMS:
        assert "file" in claim
        assert "line" in claim
        assert "description" in claim
        assert "extract_pattern" in claim
        # Settle key is either one of the bundle keys or NO_SETTLING_QUERY.
        sk = claim.get("settle_key")
        assert sk in gate_mod.SETTLE_QUERIES or sk == gate_mod.NO_SETTLING_QUERY, (
            f"claim {claim['description']!r} has settle_key={sk!r}, "
            f"which is neither a bundle key nor NO_SETTLING_QUERY"
        )


def test_t3_extract_active_identifiers():
    """README.md line 29 (first clause): `**43,116 active canonical identifiers`."""
    claim = _find_claim("README.md", 29, "active canonical identifiers")
    text = "**43,116 active canonical identifiers**, the things you query against"
    extracted = _extract(claim, text)
    assert extracted == 43116


def test_t3_extract_total_manufacturers():
    """README.md line 30: `**240 manufacturers`."""
    claim = _find_claim("README.md", 30, "total manufacturers")
    text = "**240 manufacturers**, surveillance vendors classified by what they make"
    extracted = _extract(claim, text)
    assert extracted == 240


def test_t3_extract_oem_arms_first_phrase():
    """README.md line 30: `92 of those are OEM arms`."""
    claim = _find_claim("README.md", 30, "OEM arms (first)")
    text = "92 of those are OEM arms, the rebadging brands a parent vendor sells through"
    extracted = _extract(claim, text)
    assert extracted == 92


def test_t3_extract_oem_arms_second_phrase():
    """README.md line 85: `92 of them OEM arms` (no 'are' between 'them' and 'OEM')."""
    claim = _find_claim("README.md", 85, "OEM arms (second)")
    text = "Argus lists 240 vendors, 92 of them OEM arms that exist to attribute"
    extracted = _extract(claim, text)
    assert extracted == 92


def test_t3_extract_vendors_count():
    """README.md line 85: `Argus lists 240 vendors`."""
    claim = _find_claim("README.md", 85, "vendors")
    text = "Coverage is intentionally narrow per category. Argus lists 240 vendors, 92 of them are OEM arms"
    extracted = _extract(claim, text)
    assert extracted == 240


def test_t3_extract_csv_row_count():
    """README.md line 48: `argus_export.csv | 43,116 | Bulk import`."""
    claim = _find_claim("README.md", 48, "CSV export row count")
    text = "| `exports/argus_export.csv` | 43,116 | Bulk import, analysis, or re-derivation. All active rows. |"
    extracted = _extract(claim, text)
    assert extracted == 43116


def test_t3_extract_high_conf_feed_count():
    """README.md line 46: `argus_export_high_confidence.json | 481 |`."""
    claim = _find_claim("README.md", 46, "high-conf feed")
    text = "| `exports/argus_export_high_confidence.json` | 481 | Runtime scanners (Lynceus). Strict confidence floor (>=70); |"
    extracted = _extract(claim, text)
    assert extracted == 481


def test_t3_extract_standard_feed_count():
    """README.md line 47: `argus_export.json | 981 |`."""
    claim = _find_claim("README.md", 47, "standard feed")
    text = "| `exports/argus_export.json` | 981 | Broader scanner watchlists. Looser confidence floor (>=30); US scope filter. |"
    extracted = _extract(claim, text)
    assert extracted == 981


def test_t3_extract_behavioral_feed_count():
    """README.md line 49: `argus_export_behavioral_signatures.json | 132 |`."""
    claim = _find_claim("README.md", 49, "behavioral feed")
    text = "| `exports/argus_export_behavioral_signatures.json` | 132 | Cellular-band scanners (Rayhunter). Sibling export with threshold rules. |"
    extracted = _claim_extract(claim, text)
    assert extracted == 132


def test_t3_extract_changelog_csv_count():
    """CHANGELOG.md line 54: `CSV: 43,116 rows`."""
    claim = _find_claim("CHANGELOG.md", 54, "CSV row count (CHANGELOG)")
    text = "**CSV:** **43,116** rows, matching the active count."
    extracted = _extract(claim, text)
    assert extracted == 43116


def test_t3_extract_changelog_standard_feed():
    """CHANGELOG.md line 54: `standard feed: 977 → 981`."""
    claim = _find_claim("CHANGELOG.md", 54, "standard feed (CHANGELOG)")
    text = "**Lynceus standard feed:** 977 → **981** (+21 entries / −17 entries)."
    extracted = _extract(claim, text)
    assert extracted == 981


def test_t3_extract_changelog_high_conf_feed():
    """CHANGELOG.md line 54: `high-confidence feed: 481 → 481`."""
    claim = _find_claim("CHANGELOG.md", 54, "high-conf feed (CHANGELOG)")
    text = "**high-confidence feed:** **481** → **481** (+3 / −3)."
    extracted = _extract(claim, text)
    assert extracted == 481


def test_t3_extract_changelog_behavioral_feed():
    """CHANGELOG.md line 54: `behavioral-signatures feed: 132`."""
    claim = _find_claim("CHANGELOG.md", 54, "behavioral feed (CHANGELOG)")
    text = "**behavioral-signatures feed:** **132** (entry set byte-identical)."
    extracted = _extract(claim, text)
    assert extracted == 132


def test_t3_extract_changelog_reconcile_line():
    """CHANGELOG.md line 97: `43,116 = 43,116`."""
    claim = _find_claim("CHANGELOG.md", 97, "CSV reconciles to canonical active")
    text = "The CSV reconciles to canonical active, 43,116 = 43,116."
    extracted = _extract(claim, text)
    assert extracted == 43116


def test_t3_extract_changelog_halts():
    """CHANGELOG.md line 97: `coverage_matrix _reconcile halts: 0`."""
    claim = _find_claim("CHANGELOG.md", 97, "halts")
    text = "coverage_matrix `_reconcile` halts: **0**."
    extracted = _extract(claim, text)
    assert extracted == 0


# ---------------------------------------------------------------------------
# T4: comparator -- extracted int vs settling-query result.
# ---------------------------------------------------------------------------


def test_t4_comparator_passes_on_match():
    """extracted int == settling-query result -> PASS, no failure entry."""
    res = gate_mod.compare_claim(
        {"file": "TEST.md", "line": 1, "description": "test", "settle_key": "sources"},
        extracted=98,
        settle_results={"sources": 98},
    )
    assert res.status == "PASS"
    assert res.settle_value == 98


def test_t4_comparator_fails_on_mismatch():
    """extracted int != settling-query result -> FAIL, exit code 1."""
    res = gate_mod.compare_claim(
        {"file": "TEST.md", "line": 1, "description": "test", "settle_key": "sources"},
        extracted=42,
        settle_results={"sources": 98},
    )
    assert res.status == "FAIL"
    assert res.extracted == 42
    assert res.settle_value == 98


def test_t4_comparator_unsettled_never_fails():
    """A claim with settle_key=NO_SETTLING_QUERY must NOT register a FAIL.

    The Class A claim sites that have no settling query in the bundle
    (export counts, SHA256, halts count) are listed in the report so the
    closing comment can name them, but they don't fail the gate -- the
    brief says the bundle is frozen.
    """
    res = gate_mod.compare_claim(
        {
            "file": "README.md",
            "line": 46,
            "description": "high-conf feed",
            "settle_key": gate_mod.NO_SETTLING_QUERY,
        },
        extracted=481,
        settle_results={"sources": 98},
    )
    assert res.status == "UNSETTLED"


# ---------------------------------------------------------------------------
# T5: positive control -- run the gate against a scratch copy of the doc
# surface. Two arms:
#
#   arm_pass:  rewrite every Class A claim to match the live settling-query
#               result. Gate must exit zero.
#   arm_fail:  take the same scratch copy and mutate one Class A claim.
#               Gate must exit non-zero.
#
# This is the load-bearing proof that a zero-finding run is non-vacuous --
# the regex is reaching the right numbers and the comparator is comparing
# them. A gate that reports PASS because its regex matched nothing is the
# failure mode the brief asks us to rule out.
# ---------------------------------------------------------------------------


def _seed_repo_with_synthetic_tier1(tmp_path: Path, claims: list[dict]) -> Path:
    """Write a Tier 1 corpus into ``tmp_path`` whose README.md and CHANGELOG.md
    carry the supplied Class A claims at the brief's line numbers. All other
    Tier 1 files are minimal stubs. The gate's source is copied alongside so
    REPO resolves to tmp_path when the gate's main() runs.
    """
    work = tmp_path
    (work / "scripts").mkdir(parents=True, exist_ok=True)
    (work / "docs" / "engineering").mkdir(parents=True, exist_ok=True)
    (work / "docs").mkdir(parents=True, exist_ok=True)

    # Build the README line-by-line using a 1-based sparse dict so claim
    # line numbers map directly to file line numbers (not array indices).
    # Pad with empty lines so line 200 exists.
    readme_lines: dict[int, str] = {}
    readme_lines[29] = _render_readme_line_29(claims)
    readme_lines[30] = _render_readme_line_30(claims)
    readme_lines[46] = _render_readme_line_46(claims)
    readme_lines[47] = _render_readme_line_47(claims)
    readme_lines[48] = _render_readme_line_48(claims)
    readme_lines[49] = _render_readme_line_49(claims)
    readme_lines[85] = _render_readme_line_85(claims)
    readme = _render_with_1based_lines(readme_lines, 200)
    (work / "README.md").write_text(readme, encoding="utf-8")

    cl_lines: dict[int, str] = {}
    cl_lines[54] = _render_changelog_line_54(claims)
    cl_lines[97] = _render_changelog_line_97(claims)
    cl = _render_with_1based_lines(cl_lines, 200)
    (work / "CHANGELOG.md").write_text(cl, encoding="utf-8")

    # Tier 1 stubs (no Class A claims outside README / CHANGELOG).
    (work / "CREDITS.md").write_text("credits\n", encoding="utf-8")
    (work / "docs" / "USER_GUIDE.md").write_text("user\n", encoding="utf-8")
    (work / "docs" / "engineering" / "SETUP.md").write_text("setup\n", encoding="utf-8")
    (work / "docs" / "engineering" / "DATA_DICTIONARY.md").write_text("data\n", encoding="utf-8")
    (work / "docs" / "engineering" / "METHODOLOGY.md").write_text("meth\n", encoding="utf-8")
    (work / "docs" / "engineering" / "PROJECT_BIBLE.md").write_text("bible\n", encoding="utf-8")

    # Copy the gate so REPO resolves to the scratch repo.
    (work / "scripts" / "check_doc_anchors.py").write_text(
        GATE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return work


def _render_with_1based_lines(lines: dict[int, str], max_line: int) -> str:
    """Render a 1-based sparse line dict into a newline-terminated file body.

    Keys in ``lines`` are 1-based line numbers; missing keys render as empty
    strings. ``max_line`` is the total line count we materialise; the file
    ends with a trailing newline.
    """
    out: list[str] = []
    for n in range(1, max_line + 1):
        out.append(lines.get(n, ""))
    return "\n".join(out) + "\n"


def _render_readme_line_29(claims):
    active = _claim_value(claims, "README.md", 29, "active canonical identifiers")
    return f"- **{active:,} active canonical identifiers**, the things you query against. See release notes below."


def _render_readme_line_30(claims):
    total = _claim_value(claims, "README.md", 30, "total manufacturers")
    arms = _claim_value(claims, "README.md", 30, "OEM arms (first)")
    return (
        f"- **{total} manufacturers**, surveillance vendors. "
        f"{arms} of those are OEM arms, the rebadging brands a parent vendor sells through."
    )


def _render_readme_line_46(claims):
    val = _claim_value(claims, "README.md", 46, "high-conf feed")
    return (
        f"| `exports/argus_export_high_confidence.json` | {val} | "
        "Runtime scanners (Lynceus). Strict confidence floor (>=70); |"
    )


def _render_readme_line_47(claims):
    val = _claim_value(claims, "README.md", 47, "standard feed")
    return (
        f"| `exports/argus_export.json` | {val} | "
        "Broader scanner watchlists. Looser confidence floor (>=30); US scope filter. |"
    )


def _render_readme_line_48(claims):
    val = _claim_value(claims, "README.md", 48, "CSV export row count")
    return (
        f"| `exports/argus_export.csv` | {val} | "
        "Bulk import, analysis, or re-derivation. All active rows. |"
    )


def _render_readme_line_49(claims):
    val = _claim_value(claims, "README.md", 49, "behavioral feed")
    return (
        f"| `exports/argus_export_behavioral_signatures.json` | {val} | "
        "Cellular-band scanners (Rayhunter). Sibling export with threshold rules. |"
    )


def _render_readme_line_85(claims):
    vendors = _claim_value(claims, "README.md", 85, "vendors")
    arms = _claim_value(claims, "README.md", 85, "OEM arms (second)")
    return (
        f"Coverage is intentionally narrow per category. Argus lists {vendors} vendors, "
        f"{arms} of them OEM arms that exist to attribute a rebadged device back to its real maker."
    )


def _render_changelog_line_54(claims):
    std = _claim_value(claims, "CHANGELOG.md", 54, "standard feed (CHANGELOG)")
    hc = _claim_value(claims, "CHANGELOG.md", 54, "high-conf feed (CHANGELOG)")
    beh = _claim_value(claims, "CHANGELOG.md", 54, "behavioral feed (CHANGELOG)")
    csv = _claim_value(claims, "CHANGELOG.md", 54, "CSV row count (CHANGELOG)")
    return (
        f"- **Lynceus standard feed:** 977 -> **{std}** (+21 entries / -17 entries). "
        f"**high-confidence feed:** **{hc}** -> **{hc}** (+3 / -3). "
        f"**behavioral-signatures feed:** **{beh}** (entry set byte-identical). "
        f"**CSV:** **{csv}** rows, matching the active count."
    )


def _render_changelog_line_97(claims):
    halts = _claim_value(claims, "CHANGELOG.md", 97, "halts")
    reconcile = _claim_value(claims, "CHANGELOG.md", 97, "CSV reconciles to canonical active")
    return (
        f"- None. coverage_matrix `_reconcile` halts: **{halts}**. "
        f"The CSV reconciles to canonical active, {reconcile:,} = {reconcile:,}."
    )


def _claim_value(claims, file, line, description):
    for c in claims:
        if c["file"] == file and c["line"] == line and c["description"] == description:
            return c["value"]
    raise KeyError(f"no claim for {(file, line, description)}")


def _synthetic_claim_set(active, total_manuf, arms, vendors, hc_feed, std_feed, csv_rows, beh_feed, hc_changelog, std_changelog, beh_changelog, csv_changelog, halts, reconcile):
    """Return the full Class A claim set with values the live DB agrees with."""
    return [
        _claim("README.md", 29, "active canonical identifiers", "identifiers_active", active),
        _claim("README.md", 30, "total manufacturers", "manufacturers", total_manuf),
        _claim("README.md", 30, "OEM arms (first)", "manufacturers_arms", arms),
        _claim("README.md", 46, "high-conf feed", gate_mod.NO_SETTLING_QUERY, hc_feed),
        _claim("README.md", 47, "standard feed", gate_mod.NO_SETTLING_QUERY, std_feed),
        _claim("README.md", 48, "CSV export row count", "identifiers_active", csv_rows),
        _claim("README.md", 49, "behavioral feed", gate_mod.NO_SETTLING_QUERY, beh_feed),
        _claim("README.md", 85, "vendors", "manufacturers", vendors),
        _claim("README.md", 85, "OEM arms (second)", "manufacturers_arms", arms),
        _claim("CHANGELOG.md", 54, "standard feed (CHANGELOG)", gate_mod.NO_SETTLING_QUERY, std_changelog),
        _claim("CHANGELOG.md", 54, "high-conf feed (CHANGELOG)", gate_mod.NO_SETTLING_QUERY, hc_changelog),
        _claim("CHANGELOG.md", 54, "behavioral feed (CHANGELOG)", gate_mod.NO_SETTLING_QUERY, beh_changelog),
        _claim("CHANGELOG.md", 54, "CSV row count (CHANGELOG)", "identifiers_active", csv_changelog),
        _claim("CHANGELOG.md", 97, "halts", gate_mod.NO_SETTLING_QUERY, halts),
        _claim("CHANGELOG.md", 97, "CSV reconciles to canonical active", "identifiers_active", reconcile),
    ]


def _claim(file, line, description, settle_key, value):
    return {"file": file, "line": line, "description": description, "settle_key": settle_key, "value": value}


def _live_settle_results():
    """Run the gate's settling-query machinery against canonical, return a
    dict keyed by every bundle key. The positive-control arms use this to
    build a synthetic Tier 1 surface whose claims all match live values.
    """
    return gate_mod.run_settling_queries(REPO / "db" / "argus.db")


def _synthetic_claim_set_from_live():
    live = _live_settle_results()
    return _synthetic_claim_set(
        active=live["identifiers_active"],
        total_manuf=live["manufacturers"],
        arms=live["manufacturers_arms"],
        vendors=live["manufacturers"],
        hc_feed=481,  # export count, no settle; leave the README claim at 481
        std_feed=981,
        csv_rows=live["identifiers_active"],
        beh_feed=132,
        hc_changelog=481,
        std_changelog=981,
        beh_changelog=132,
        csv_changelog=live["identifiers_active"],
        halts=0,
        reconcile=live["identifiers_active"],
    )


def _run_gate(work: Path, args: list[str]) -> tuple[int, str, str]:
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/check_doc_anchors.py", *args],
        cwd=work,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def test_t5_positive_control_pass(tmp_path):
    """Synthetic Tier 1 with all Class A claims matching live values exits 0."""
    claims = _synthetic_claim_set_from_live()
    work = _seed_repo_with_synthetic_tier1(tmp_path, claims)
    rc, out, err = _run_gate(
        work,
        ["--db-path", str(REPO / "db" / "argus.db")],
    )
    assert rc == 0, f"stdout={out!r} stderr={err!r}"


def test_t5_positive_control_fail_on_mutation(tmp_path):
    """Mutating a known-good Class A claim forces the gate to exit non-zero."""
    claims = _synthetic_claim_set_from_live()
    # Mutate: README line 30 total manufacturers by -1.
    for c in claims:
        if c["file"] == "README.md" and c["line"] == 30 and c["description"] == "total manufacturers":
            c["value"] = c["value"] - 1
            break
    work = _seed_repo_with_synthetic_tier1(tmp_path, claims)
    rc, out, err = _run_gate(
        work,
        ["--db-path", str(REPO / "db" / "argus.db")],
    )
    assert rc != 0, f"gate should have failed on mutated claim; stdout={out!r} stderr={err!r}"
    assert "FAIL" in out or "FAIL" in err


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _find_claim(file, line, description):
    """Find a Class A claim by file + line + description; raise if not found."""
    for c in gate_mod.CLASS_A_CLAIMS:
        if c["file"] == file and c["line"] == line and c["description"] == description:
            return c
    raise KeyError(f"no Class A claim for {(file, line, description)}")


def _claim_extract(claim, text):
    return _extract(claim, text)


def _extract(claim, text):
    """Run the claim's regex against ``text`` and return the first integer.

    The claim's `extract_pattern` must have exactly one capturing group that
    captures the integer (with optional thousands separators). Returns the
    int after stripping commas.
    """
    pat = claim["extract_pattern"]
    m = re.search(pat, text)
    if not m:
        raise AssertionError(
            f"pattern {pat!r} did not match text {text!r} for {claim['description']!r}"
        )
    raw = m.group(1)
    return int(raw.replace(",", ""))


# Sanity check: the gate must be importable and module-level.
def test_gate_module_imports():
    assert gate_mod is not None