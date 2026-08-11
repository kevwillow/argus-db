#!/usr/bin/env python3
"""MAC-699 -- mechanical gate for the v1.7.0 doc-surface numeric claims.

The v1.7.0 doc surface drifts from canonical and it took a CEO-directed
manual sweep (MAC-516) plus a hand-built inventory to find it. That does
not scale and it goes stale within the hour. This gate makes the headline
totals mechanically checkable, the way ``scripts/check_prose_dashes.py``
made the em-dash ban mechanical.

How it works
------------

A frozen bundle of 13 settling queries runs read-only against
``db/argus.db`` (URI ``file:...?mode=ro``). For each Class A claim site --
a hard-coded ``(file, line, description, settle_key, extract_pattern)``
tuple -- the gate extracts the integer the doc actually prints and
compares it to the settling-query result. Equal -> PASS. Not equal -> FAIL.
Exit non-zero on any FAIL.

Class B (delta and provenance lines anchored to a named migration) and
Class C (historical pins to a past release) are listed in the source for
explicit-skipped reasoning but never checked; rewriting them to live values
would silently break their internal arithmetic.

Three traps the bundle encodes
-----------------------------

Trap 1 (enum cardinality is not populated cardinality).  ``device_category``
and ``identifier_type`` CHECK-enum cardinality (20 and 58 on the live
schema) is parsed from ``sqlite_master`` rather than measured via
``COUNT(DISTINCT)`` (which would yield 19 and 51 and confidently propose
regressions). The two corresponding bundle entries invoke the CHECK parser.

Trap 2 (``is_arm``, never ``parent_manufacturer_id``).  The OEM arm count
uses ``WHERE is_arm=1`` (live 92, cross-confirmed by ``query_default =
'hidden_arm'`` also 92). ``WHERE parent_manufacturer_id IS NOT NULL``
returns 94 -- two rows carry a parent link without being arms (the Amcrest
and Lorex to Dahua alias links). Picking the wrong column silently
over-reports by 2.

Trap 3 (three claim classes, and only one of them is checkable).  Class A
sites are checked; Class B and Class C sites are listed in the source but
skipped. The class assignment per claim site is explicit in the source
(not implied) and any site the gate author could not classify is named
in the closing comment rather than guessed.

Usage
-----

    python3 scripts/check_doc_anchors.py            # exit 0 on all-pass, 1 on any FAIL
    python3 scripts/check_doc_anchors.py --list     # per-claim PASS/FAIL/UNSETTLED detail

Exit codes
----------

    0   no Class A FAIL (and no settling-query errors)
    1   at least one Class A FAIL
    2   usage error
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

# Sentinel for Class A sites that have no settling-query in the bundle
# (e.g., export-record counts, SHA256 fingerprints, halt counts). They
# are listed in the report so the closing comment can name them, but
# they don't fail the gate -- the brief says the bundle is frozen.
NO_SETTLING_QUERY = "__no_settling_query__"

# ---------------------------------------------------------------------------
# Frozen bundle of 13 settling queries. The CTO confirmed live at
# 2026-08-11T20:46:32Z against canonical sha256 5e0d3ce440fde05c.... The
# shapes are confirmed; the targets are derived at run time against the
# live db/argus.db.
# ---------------------------------------------------------------------------

SETTLE_QUERIES: dict[str, str] = {
    "identifiers_active": "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL",
    "identifiers_total": "SELECT COUNT(*) FROM identifiers",
    "manufacturers": "SELECT COUNT(*) FROM manufacturers",
    # Trap 2: arm count uses `is_arm=1`, never `parent_manufacturer_id IS NOT NULL`.
    # The latter over-reports by 2 (the Amcrest and Lorex to Dahua alias links
    # carry a parent link without being arms).
    "manufacturers_arms": "SELECT COUNT(*) FROM manufacturers WHERE is_arm=1",
    "sources": "SELECT COUNT(*) FROM sources",
    "schema_version": "SELECT MAX(version) FROM schema_version",
    "behavioral_signatures": "SELECT COUNT(*) FROM behavioral_signatures",
    "raw_observations": "SELECT COUNT(*) FROM raw_observations",
    "extraction_runs": "SELECT COUNT(*) FROM extraction_runs",
    "deployment_observations": "SELECT COUNT(*) FROM deployment_observations",
    "procurement_records": "SELECT COUNT(*) FROM procurement_records",
    # Trap 1: enum cardinality parses the CHECK constraint, never
    # COUNT(DISTINCT). Both entries below invoke the CHECK parser.
    "device_category_enum": "PARSE_CHECK:identifiers:device_category",
    "identifier_type_enum": "PARSE_CHECK:identifiers:identifier_type",
}


# ---------------------------------------------------------------------------
# Tier 1 doc surface. Same list as scripts/check_prose_dashes.py.
# ---------------------------------------------------------------------------

TIER_1: tuple[str, ...] = (
    "README.md",
    "CHANGELOG.md",
    "CREDITS.md",
    "docs/USER_GUIDE.md",
    "docs/engineering/SETUP.md",
    "docs/engineering/DATA_DICTIONARY.md",
    "docs/engineering/METHODOLOGY.md",
    "docs/engineering/PROJECT_BIBLE.md",
)


# ---------------------------------------------------------------------------
# Claim-site registry. Each Class A site is explicit: file, line, pattern
# that pulls the integer out of that line, and the bundle key (or
# NO_SETTLING_QUERY) it settles against. Class B and Class C sites are
# listed for explicit-skipped reasoning.
#
# The class assignment is per the brief:
#   Class A  headline totals describing the shipped artifact. These are
#            what the gate checks.
#   Class B  delta and provenance lines anchored to a named migration.
#            Correct as of their migration; never rewritten to live values.
#   Class C  historical pins to a past release (v1.6.2 verify blocks,
#            DATA_DICTIONARY v1.6.5 row counts, USER_GUIDE v1.6.2 export
#            counts). Back-entry SHAs and pinned release counts are
#            historical record.
# ---------------------------------------------------------------------------


def _claim(file: str, line: int, description: str, settle_key: str, pattern: str) -> dict:
    return {
        "file": file,
        "line": line,
        "description": description,
        "settle_key": settle_key,
        "extract_pattern": pattern,
    }


CLASS_A_CLAIMS: list[dict] = [
    # --- README.md headline totals (per brief: line 29 first clause, 30, 46-49, 85) ---
    _claim(
        "README.md", 29, "active canonical identifiers", "identifiers_active",
        r"\*\*([\d,]+)\s+active\s+canonical\s+identifiers",
    ),
    _claim(
        "README.md", 30, "total manufacturers", "manufacturers",
        r"\*\*(\d+)\s+manufacturers",
    ),
    _claim(
        "README.md", 30, "OEM arms (first)", "manufacturers_arms",
        r"(\d+)\s+of\s+those\s+are\s+OEM\s+arms",
    ),
    _claim(
        "README.md", 46, "high-conf feed", NO_SETTLING_QUERY,
        r"argus_export_high_confidence\.json[^\n]*\|\s+([\d,]+)\s+\|",
    ),
    _claim(
        "README.md", 47, "standard feed", NO_SETTLING_QUERY,
        r"argus_export\.json[^\n]*\|\s+([\d,]+)\s+\|",
    ),
    _claim(
        "README.md", 48, "CSV export row count", "identifiers_active",
        r"argus_export\.csv[^\n]*\|\s+([\d,]+)\s+\|",
    ),
    _claim(
        "README.md", 49, "behavioral feed", NO_SETTLING_QUERY,
        r"argus_export_behavioral_signatures\.json[^\n]*\|\s+([\d,]+)\s+\|",
    ),
    _claim(
        "README.md", 85, "vendors", "manufacturers",
        r"Argus\s+lists\s+(\d+)\s+vendors",
    ),
    _claim(
        "README.md", 85, "OEM arms (second)", "manufacturers_arms",
        r"(\d+)\s+of\s+them\s+OEM\s+arms",
    ),
    # --- CHANGELOG.md headline totals (per brief: line 54, 55, 97) ---
    # Line 54 carries both export-count numbers (no settling queries) and
    # the CSV row count (settled against identifiers_active -- the doc
    # explicitly says "CSV: N rows, matching the active count").
    _claim(
        "CHANGELOG.md", 54, "standard feed (CHANGELOG)", NO_SETTLING_QUERY,
        r"\*\*Lynceus standard feed:\*\*\s*[\d,]+\s*→\s*\*\*([\d,]+)\*\*",
    ),
    # high-conf feed is "**481** -> **481**" -- capture the AFTER value
    # (the headline total). The BEFORE value is Class B / delta territory.
    _claim(
        "CHANGELOG.md", 54, "high-conf feed (CHANGELOG)", NO_SETTLING_QUERY,
        r"\*\*high-confidence feed:\*\*\s*\*\*[\d,]+\*\*\s*→\s*\*\*([\d,]+)\*\*",
    ),
    _claim(
        "CHANGELOG.md", 54, "behavioral feed (CHANGELOG)", NO_SETTLING_QUERY,
        r"\*\*behavioral-signatures feed:\*\*\s*\*\*([\d,]+)\*\*",
    ),
    _claim(
        "CHANGELOG.md", 54, "CSV row count (CHANGELOG)", "identifiers_active",
        r"\*\*CSV:\*\*\s*\*\*([\d,]+)\*\*",
    ),
    # Line 55 is the SHA256 + argus_run_id fingerprint block. SHA256 has
    # no settling query in the bundle -- naming it as NO_SETTLING_QUERY
    # lets the closing comment flag it for follow-up rather than guess.
    # (The argus_run_id is a UUID with no per-cycle invariant either; both
    # are intentionally not in the bundle.)
    # Line 97 carries two halves of the reconciliation assertion.
    _claim(
        "CHANGELOG.md", 97, "halts", NO_SETTLING_QUERY,
        r"halts:\s*\*\*([\d,]+)\*\*",
    ),
    _claim(
        "CHANGELOG.md", 97, "CSV reconciles to canonical active", "identifiers_active",
        r"([\d,]+)\s*=\s*([\d,]+)",
    ),
]


CLASS_B_SITES: list[dict] = [
    # CHANGELOG.md lines 43 / 51 / 52 / 53 / and the rest of the Data
    # section are delta + provenance lines anchored to the v1.7.0
    # migration. The internal arithmetic must be preserved; never
    # rewrite to live values.
    {"file": "CHANGELOG.md", "line": 43, "description": "Three new sources (95 -> 98)",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "CHANGELOG.md", "line": 51, "description": "identifiers active 43,134 -> 43,116 (net -18)",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "CHANGELOG.md", "line": 52, "description": "identifiers total 43,840 -> 43,848",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "CHANGELOG.md", "line": 53, "description": "manufacturers 156 -> 240; sources 95 -> 98; behavioral 214; category enum 20",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "README.md", "line": 29, "description": "second clause: Active moves 43,134 -> 43,116, standard feed 977 -> 981, high-confidence holds at 481",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "README.md", "line": 93, "description": "8 new identifiers / 16 junk rows / 3 new sources / 84 OEM camera brands",
     "reason": "delta and provenance lines anchored to v1.7.0 migration"},
    {"file": "README.md", "line": 95, "description": "Active identifiers move 43,134 -> 43,116; standard Lynceus feed 977 -> 981; high-confidence holds at 481; behavioral feed holds at 132",
     "reason": "delta and provenance lines anchored to v1.7.0 migration"},
]


CLASS_C_SITES: list[dict] = [
    # USER_GUIDE.md lines 35 / 45 / 51 are pinned to v1.6.2 by design.
    {"file": "docs/USER_GUIDE.md", "line": 35, "description": "high-confidence export rows (146 at v1.6.2)",
     "reason": "historical pin anchored to v1.6.2 by design"},
    {"file": "docs/USER_GUIDE.md", "line": 45, "description": "standard export rows (592 at v1.6.2)",
     "reason": "historical pin anchored to v1.6.2 by design"},
    {"file": "docs/USER_GUIDE.md", "line": 51, "description": "CSV rows (41,508 at v1.6.2)",
     "reason": "historical pin anchored to v1.6.2 by design"},
    # SETUP.md v1.6.2 verify block.
    {"file": "docs/engineering/SETUP.md", "line": 38,
     "description": "SETUP.md v1.6.2 verify block (Schema version: 30 / 41508 active / 41890 total / manufacturers 126 / etc.)",
     "reason": "v1.6.2 verify block by design"},
    # DATA_DICTIONARY.md rows 79-93 are pinned to v1.6.5.
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 79,
     "description": "identifiers 41,716 active + 342 chained-superseded + 40 self-loop",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 80,
     "description": "raw_observations 147,421",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 81,
     "description": "sources 74",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 82,
     "description": "manufacturers 126 (8 arms)",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 83,
     "description": "deployment_observations 116,774",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 84,
     "description": "procurement_records 50,492",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 85,
     "description": "fcc_grantees 50,153",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 86,
     "description": "council_minutes_matters 3",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 87,
     "description": "wigle_anchor_priority 80,697",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 88,
     "description": "behavioral_signatures 201",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 89,
     "description": "conflicts 36",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 90,
     "description": "extraction_runs 121 / MAX(id)=126",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 91,
     "description": "source_reclassifications 809",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 92,
     "description": "fcc_citation_deferred_queue 671",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "line": 93,
     "description": "schema_version 30",
     "reason": "DATA_DICTIONARY v1.6.5 row counts pinned by design"},
]


# ---------------------------------------------------------------------------
# DB access (read-only).
# ---------------------------------------------------------------------------


def _open_db_ro(db_path: Path) -> sqlite3.Connection:
    """Open ``db_path`` via the URI form in read-only mode.

    A probe UPDATE inside this connection must raise
    ``sqlite3.OperationalError`` (the test suite pins this load-bearing
    invariant: the gate never writes to canonical).
    """
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _parse_check_constraint(sql: str, col: str) -> list[str]:
    """Parse the CHECK (col IN ( ... )) clause from a CREATE TABLE SQL.

    The CHECK body spans multiple lines in ``identifiers`` and includes
    inline comments -- we only pull single-quoted string literals.
    Raises ValueError if the clause is not found (should be impossible
    for the live schema; the test suite asserts this).
    """
    pattern = re.compile(
        rf"\b{re.escape(col)}\b\s+TEXT\s+NOT\s+NULL\s+CHECK\s*\(\s*"
        rf"{re.escape(col)}\s+IN\s*\((.*?)\)\s*\)",
        re.DOTALL,
    )
    m = pattern.search(sql)
    if not m:
        raise ValueError(f"no CHECK ({col} IN (...)) in SQL: {sql[:200]!r}")
    body = m.group(1)
    return re.findall(r"'([^']+)'", body)


def run_settling_queries(db_path: Path) -> dict[str, int]:
    """Run every entry in SETTLE_QUERIES against ``db_path`` (read-only).

    The two ``PARSE_CHECK:...`` entries are special: they pull the
    CREATE TABLE SQL for ``identifiers`` and parse the CHECK clause
    cardinality rather than running a COUNT(DISTINCT) (Trap 1).
    """
    results: dict[str, int] = {}
    con = _open_db_ro(db_path)
    try:
        identifiers_sql = con.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'identifiers'"
        ).fetchone()[0]
        for key, query in SETTLE_QUERIES.items():
            if query.startswith("PARSE_CHECK:"):
                _, table, col = query.split(":", 2)
                if table != "identifiers":
                    raise ValueError(f"unexpected CHECK target {table!r}")
                results[key] = len(_parse_check_constraint(identifiers_sql, col))
            else:
                results[key] = int(con.execute(query).fetchone()[0])
    finally:
        con.close()
    return results


# ---------------------------------------------------------------------------
# Claim extraction and comparison.
# ---------------------------------------------------------------------------


@dataclass
class CompareResult:
    file: str
    line: int
    description: str
    settle_key: str
    extracted: int | None
    settle_value: int | None
    status: str  # "PASS" | "FAIL" | "UNSETTLED" | "ERROR"
    note: str = ""


def extract_claim(claim: dict, line_text: str) -> int | None:
    """Pull the integer out of a single doc line via the claim's regex.

    The regex must have one or two capturing groups; both may include
    thousands separators (commas). The first non-None group is what gets
    parsed. Returns None if the pattern does not match.
    """
    pat = claim["extract_pattern"]
    m = re.search(pat, line_text)
    if not m:
        return None
    for grp in m.groups():
        if grp is not None:
            return int(grp.replace(",", ""))
    return None


def compare_claim(
    claim: dict,
    extracted: int | None,
    settle_results: dict[str, int],
) -> CompareResult:
    """Compare the extracted integer to the settling-query result."""
    settle_key = claim["settle_key"]
    base = CompareResult(
        file=claim["file"],
        line=claim["line"],
        description=claim["description"],
        settle_key=settle_key,
        extracted=extracted,
        settle_value=settle_results.get(settle_key) if settle_key != NO_SETTLING_QUERY else None,
        status="",
    )
    if settle_key == NO_SETTLING_QUERY:
        if extracted is None:
            base.status = "UNSETTLED"
            base.note = "no settling query in bundle; regex did not match the doc line either"
        else:
            base.status = "UNSETTLED"
            base.note = f"no settling query in bundle; doc prints {extracted}"
        return base
    if extracted is None:
        base.status = "ERROR"
        base.note = "extract_pattern did not match the doc line"
        return base
    if settle_results.get(settle_key) is None:
        base.status = "ERROR"
        base.note = f"settle_results missing key {settle_key!r}"
        return base
    if extracted == settle_results[settle_key]:
        base.status = "PASS"
        return base
    base.status = "FAIL"
    return base


# ---------------------------------------------------------------------------
# Scan / report.
# ---------------------------------------------------------------------------


def _read_line(file: Path, line_no_1based: int) -> str | None:
    """Return the (1-based) numbered line, or None if out of range."""
    try:
        text = file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    lines = text.split("\n")
    if line_no_1based < 1 or line_no_1based > len(lines):
        return None
    return lines[line_no_1based - 1]


def scan_docs(settle_results: dict[str, int]) -> list[CompareResult]:
    """Walk every Class A claim site, extract, compare, return per-site result."""
    out: list[CompareResult] = []
    for claim in CLASS_A_CLAIMS:
        line_text = _read_line(REPO / claim["file"], claim["line"])
        extracted = extract_claim(claim, line_text) if line_text is not None else None
        out.append(compare_claim(claim, extracted, settle_results))
    return out


def _format_result(r: CompareResult) -> str:
    if r.status == "PASS":
        return (
            f"PASS  {r.file}:{r.line}  {r.description}  "
            f"({r.extracted:,} == settle[{r.settle_key}] = {r.settle_value:,})"
        )
    if r.status == "FAIL":
        return (
            f"FAIL  {r.file}:{r.line}  {r.description}  "
            f"(doc says {r.extracted:,}, settle[{r.settle_key}] = {r.settle_value:,})"
        )
    if r.status == "UNSETTLED":
        return (
            f"UNSETTLED  {r.file}:{r.line}  {r.description}  "
            f"(no settling query in bundle; {r.note})"
        )
    if r.status == "ERROR":
        return (
            f"ERROR  {r.file}:{r.line}  {r.description}  ({r.note})"
        )
    return f"UNKNOWN  {r.file}:{r.line}  {r.description}  ({r.note})"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Argus doc-anchor gate (MAC-699). Read-only against db/argus.db."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print every per-claim PASS/FAIL/UNSETTLED line; exit non-zero on any FAIL.",
    )
    parser.add_argument(
        "--db-path",
        default=str(REPO / "db" / "argus.db"),
        help="Path to argus.db (read-only URI form is used).",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.db_path)
    settle_results = run_settling_queries(db_path)
    results = scan_docs(settle_results)

    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    n_unsettled = sum(1 for r in results if r.status == "UNSETTLED")
    n_error = sum(1 for r in results if r.status == "ERROR")

    if args.list:
        for r in results:
            print(_format_result(r))
    else:
        # In default mode, emit a one-line summary to stdout and any FAIL
        # / ERROR detail to stderr so a per-claim diff is visible without
        # --list. The summary line uses uppercase tokens so consumers can
        # grep for FAIL/PASS without case-tweaking.
        for r in results:
            if r.status in ("FAIL", "ERROR"):
                print(_format_result(r), file=sys.stderr)
    print(
        f"check_doc_anchors: {n_pass} PASS, {n_fail} FAIL, "
        f"{n_unsettled} UNSETTLED, {n_error} ERROR "
        f"(of {len(results)} Class A claim sites; {len(CLASS_B_SITES)} Class B "
        f"skipped, {len(CLASS_C_SITES)} Class C skipped)"
    )

    return 1 if (n_fail or n_error) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))