#!/usr/bin/env python3
"""MAC-699 -- mechanical gate for the current-release doc-surface numeric claims.

The v1.7.0 doc surface drifts from canonical and it took a CEO-directed
manual sweep (MAC-516) plus a hand-built inventory to find it. That does
not scale and it goes stale within the hour. This gate makes the headline
totals mechanically checkable, the way ``scripts/check_prose_dashes.py``
made the em-dash ban mechanical.

How it works
------------

Two settling instruments run read-only:

* A frozen bundle of 13 settling *queries* against ``db/argus.db`` (URI
  ``file:...?mode=ro``) -- canonical row counts and enum cardinalities.
* A bundle of 4 settling *artifacts* -- the emitted exports under
  ``exports/``, counted by parsing the artifact itself.

For each Class A claim site the gate resolves the claim's line, extracts
the integer the doc actually prints, and compares it to the settled
value. Equal -> PASS. Not equal -> FAIL. Unresolvable -> ERROR. Exit
non-zero on any FAIL or ERROR.

Anchors are resolved by CONTENT, not by line number (MAC-717)
-------------------------------------------------------------

The gate originally pinned each Class A site to a hard-coded line
number. MAC-708's docs pass renumbered ``CHANGELOG.md`` and every pin
slid off its claim: the CSV row-count pin landed on a blank line and the
reconciliation pin landed on prose about Defense Logistics Agency
alprazolam repackaging. A positional pin silently re-breaks on the next
prose edit, so each site now carries an ``anchor`` regex and the gate
searches for it.

Resolution is deliberately strict, because a loose anchor moves the
blindness rather than removing it:

* the anchor must match **exactly one** line in its search window;
* zero matches -> ERROR (the claim was deleted or reworded);
* two or more matches -> ERROR (ambiguous; the gate refuses to guess).

The window matters. ``**Lynceus standard feed:**`` appears on 7 lines of
``CHANGELOG.md`` -- every prior release repeats the format -- so a bare
content anchor would bind to a historical release and pass against the
wrong numbers. CHANGELOG claims therefore carry a ``section`` regex that
scopes the search to the current release block (from its ``## vX.Y.Z``
heading to the next ``## `` heading). The section regex must itself
match exactly one heading. That pin moves at every release; see
``SECTION_CURRENT_RELEASE``.

Class B (delta and provenance lines anchored to a named migration) and
Class C (historical pins to a past release) are listed in the source for
explicit-skipped reasoning but never checked; rewriting them to live values
would silently break their internal arithmetic. Their ``locator`` fields
are descriptive text for a human reader -- the gate never resolves them,
so they carry no line numbers to rot. Making them machine-resolvable is
tracked as follow-up, not done here.

Four traps the bundles encode
-----------------------------

Trap 1 (enum cardinality is not populated cardinality).  ``device_category``
and ``identifier_type`` CHECK-enum cardinality is parsed from
``sqlite_master`` rather than measured via ``COUNT(DISTINCT)`` (which
yields 19 and 51 and would confidently propose regressions). The two
corresponding bundle entries invoke the CHECK parser.

Trap 2 (``is_arm``, never ``parent_manufacturer_id``).  The OEM arm count
uses ``WHERE is_arm=1`` (cross-confirmed by ``query_default = 'hidden_arm'``).
``WHERE parent_manufacturer_id IS NOT NULL`` returns two more -- the Amcrest
and Lorex to Dahua alias links carry a parent link without being arms.
Picking the wrong column silently over-reports by 2.

Trap 3 (three claim classes, and only one of them is checkable).  Class A
sites are checked; Class B and Class C sites are listed in the source but
skipped. The class assignment per claim site is explicit in the source
(not implied) and any site the gate author could not classify is named
in the closing comment rather than guessed.

Trap 4 (feed entry counts have no DB-side answer -- MAC-717).  A row can
clear the confidence floor and still bin out before the feed:
``device_category='unknown'`` bins out first, and ``geographic_scope IS
NULL`` passes the standard feed while failing high-confidence. Any query
that merely *resembles* the export predicate will disagree with the
product. The settling rule for a feed count is therefore to count the
emitted artifact -- ``len(json.load(...)["entries"])`` -- never to
re-implement the export in SQL.

The CSV carries its own two traps, both called out in the doc surface it
verifies (``docs/USER_GUIDE.md`` section 2, ``docs/engineering/SETUP.md``
section 3): row 0 is a ``# meta:`` provenance comment rather than the
column header, and ``source_excerpt`` values contain embedded newlines.
``len(rows) - 1`` double-counts, and any line-oriented count (``wc -l``,
``grep -vc '^#'``) overstates. Only a real CSV parse that skips the meta
row and the header is correct.

Usage
-----

    python3 scripts/check_doc_anchors.py            # exit 0 on all-pass, 1 on any FAIL/ERROR
    python3 scripts/check_doc_anchors.py --list     # per-claim PASS/FAIL/UNSETTLED detail

Capture the exit code on a bare invocation. Piping through ``tail``
reports ``tail``'s exit code, not the gate's.

Exit codes
----------

    0   no Class A FAIL and no ERROR
    1   at least one Class A FAIL, or a claim site that could not be resolved
    2   usage error
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Sentinel for Class A sites that have no settling instrument (the
# `_reconcile` halt tally). They are listed in the report so the closing
# comment can name them, but they don't fail the gate.
NO_SETTLING_QUERY = "__no_settling_query__"

# Scopes a CHANGELOG claim to the CURRENT release block. Required: the
# per-release line formats repeat verbatim across every prior release,
# so an unscoped content anchor would bind to a historical section.
#
# This pin MOVES at every release. The current release block carries the
# live headline totals; every prior release block is historical record
# and is Class C by the rationale above. Re-point it when you cut a tag.
SECTION_CURRENT_RELEASE = r"^## v1\.8\.0\b"

# ---------------------------------------------------------------------------
# Frozen bundle of 13 settling queries. Shapes are frozen; targets are
# derived at run time against the live db/argus.db. No canonical sha or
# row count is pinned in this file -- a comment asserting a DB invariant
# is attestation, and canonical moves between heartbeats.
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
# Settling artifacts (MAC-717). The three feed counts and the CSV row
# count settle against the emitted artifact, because no DB query answers
# them (Trap 4). Paths are repo-relative; the counter kind selects the
# parser.
# ---------------------------------------------------------------------------

SETTLE_ARTIFACTS: dict[str, tuple[str, str]] = {
    "feed_standard": ("exports/argus_export.json", "json_entries"),
    "feed_high_confidence": ("exports/argus_export_high_confidence.json", "json_entries"),
    "feed_behavioral": ("exports/argus_export_behavioral_signatures.json", "json_entries"),
    "csv_data_rows": ("exports/argus_export.csv", "csv_data_rows"),
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
# Claim-site registry. Each Class A site is explicit: file, an anchor that
# locates the claim line by content, the pattern that pulls the integer
# out of that line, and the settling key (or NO_SETTLING_QUERY). Class B
# and Class C sites are listed for explicit-skipped reasoning.
#
# The class assignment is per the brief:
#   Class A  headline totals describing the shipped artifact. These are
#            what the gate checks.
#   Class B  delta and provenance lines anchored to a named migration.
#            Correct as of their migration; never rewritten to live values.
#   Class C  historical pins to a past release (v1.6.2 verify block,
#            DATA_DICTIONARY v1.6.5 row-count snapshot). Back-entry SHAs
#            and pinned release counts are historical record.
# ---------------------------------------------------------------------------


def _claim(
    file: str,
    description: str,
    settle_key: str,
    pattern: str,
    anchor: str | None = None,
    section: str | None = None,
) -> dict:
    """Build a Class A claim site.

    ``anchor`` defaults to ``pattern`` -- for most sites the extraction
    regex is itself a unique content marker. Pass an explicit anchor when
    several claims share one physical line, or when the extraction regex
    is too generic to identify the line on its own.
    """
    return {
        "file": file,
        "description": description,
        "settle_key": settle_key,
        "extract_pattern": pattern,
        "anchor": pattern if anchor is None else anchor,
        "section": section,
    }


# Anchors that identify a whole line shared by several claims.
_A_README_EXPORT_TABLE_HC = r"exports/argus_export_high_confidence\.json"
_A_README_EXPORT_TABLE_STD = r"exports/argus_export\.json"
_A_README_EXPORT_TABLE_CSV = r"exports/argus_export\.csv"
_A_README_EXPORT_TABLE_BEH = r"exports/argus_export_behavioral_signatures\.json"
_A_README_VENDORS = r"Argus lists \d+ vendors"
_A_CL_FEED_TOTALS = r"\*\*Feed totals\.\*\*"
_A_CL_DATA_FEEDS = r"\*\*Lynceus standard feed:\*\*"
_A_CL_RECONCILE = r"The CSV reconciles to canonical active"


CLASS_A_CLAIMS: list[dict] = [
    # --- README.md headline totals ---
    _claim(
        "README.md", "active canonical identifiers", "identifiers_active",
        r"\*\*([\d,]+)\s+active\s+canonical\s+identifiers",
    ),
    _claim(
        "README.md", "total manufacturers", "manufacturers",
        r"\*\*(\d+)\s+manufacturers\*\*",
    ),
    _claim(
        "README.md", "OEM arms (first)", "manufacturers_arms",
        r"(\d+)\s+of\s+those\s+are\s+OEM\s+arms",
    ),
    # The four export-table rows. Each row's artifact path is the anchor;
    # the Records column is the extracted integer.
    _claim(
        "README.md", "high-conf feed", "feed_high_confidence",
        r"argus_export_high_confidence\.json[^\n]*\|\s+([\d,]+)\s+\|",
        anchor=_A_README_EXPORT_TABLE_HC,
    ),
    _claim(
        "README.md", "standard feed", "feed_standard",
        r"argus_export\.json[^\n]*\|\s+([\d,]+)\s+\|",
        anchor=_A_README_EXPORT_TABLE_STD,
    ),
    # The CSV row keeps a canonical-side settling: its prose promise is
    # "All active rows". The artifact-vs-canonical equality is asserted
    # once, at the CHANGELOG reconciliation site below.
    _claim(
        "README.md", "CSV export row count", "identifiers_active",
        r"argus_export\.csv[^\n]*\|\s+([\d,]+)\s+\|",
        anchor=_A_README_EXPORT_TABLE_CSV,
    ),
    _claim(
        "README.md", "behavioral feed", "feed_behavioral",
        r"argus_export_behavioral_signatures\.json[^\n]*\|\s+([\d,]+)\s+\|",
        anchor=_A_README_EXPORT_TABLE_BEH,
    ),
    _claim(
        "README.md", "vendors", "manufacturers",
        r"Argus\s+lists\s+(\d+)\s+vendors",
        anchor=_A_README_VENDORS,
    ),
    _claim(
        "README.md", "OEM arms (second)", "manufacturers_arms",
        r"(\d+)\s+of\s+them\s+OEM\s+arms",
        anchor=_A_README_VENDORS,
    ),
    # --- CHANGELOG.md "Feed totals." summary line (current release section) ---
    _claim(
        "CHANGELOG.md", "standard feed (CHANGELOG feed-totals)", "feed_standard",
        r"Standard\s+[\d,]+\s+to\s+\*\*([\d,]+)\*\*",
        anchor=_A_CL_FEED_TOTALS, section=SECTION_CURRENT_RELEASE,
    ),
    _claim(
        "CHANGELOG.md", "high-conf feed (CHANGELOG feed-totals)", "feed_high_confidence",
        r"high-confidence\s+[\d,]+\s+to\s+\*\*([\d,]+)\*\*",
        anchor=_A_CL_FEED_TOTALS, section=SECTION_CURRENT_RELEASE,
    ),
    _claim(
        "CHANGELOG.md", "behavioral feed (CHANGELOG feed-totals)", "feed_behavioral",
        r"behavioral\s+\*\*([\d,]+)\*\*\s+unchanged",
        anchor=_A_CL_FEED_TOTALS, section=SECTION_CURRENT_RELEASE,
    ),
    # --- CHANGELOG.md Data-section feed line (current release section) ---
    # All four claims below live on one physical line, so they share an
    # anchor. Capture the AFTER value of each arrow; the BEFORE value is
    # Class B / delta territory.
    _claim(
        "CHANGELOG.md", "standard feed (CHANGELOG data line)", "feed_standard",
        r"\*\*Lynceus standard feed:\*\*\s*[\d,]+\s*→\s*\*\*([\d,]+)\*\*",
        anchor=_A_CL_DATA_FEEDS, section=SECTION_CURRENT_RELEASE,
    ),
    _claim(
        "CHANGELOG.md", "high-conf feed (CHANGELOG data line)", "feed_high_confidence",
        r"\*\*high-confidence feed:\*\*\s*[\d,]+\s*→\s*\*\*([\d,]+)\*\*",
        anchor=_A_CL_DATA_FEEDS, section=SECTION_CURRENT_RELEASE,
    ),
    _claim(
        "CHANGELOG.md", "behavioral feed (CHANGELOG data line)", "feed_behavioral",
        r"\*\*behavioral-signatures feed:\*\*\s*\*\*([\d,]+)\*\*",
        anchor=_A_CL_DATA_FEEDS, section=SECTION_CURRENT_RELEASE,
    ),
    _claim(
        "CHANGELOG.md", "CSV row count (CHANGELOG)", "csv_data_rows",
        r"\*\*CSV:\*\*\s*\*\*([\d,]+)\*\*",
        anchor=_A_CL_DATA_FEEDS, section=SECTION_CURRENT_RELEASE,
    ),
    # --- CHANGELOG.md "Halts encountered" (current release section) ---
    _claim(
        "CHANGELOG.md", "halts", NO_SETTLING_QUERY,
        r"halts:\s*\*\*([\d,]+)\*\*",
        anchor=_A_CL_RECONCILE, section=SECTION_CURRENT_RELEASE,
    ),
    # The reconciliation sentence asserts CSV-rows == canonical-active.
    # Settle each side against the instrument it names: the left operand
    # against the emitted CSV, the right against canonical. Checking only
    # one side would pass on two identical printed digits that both
    # disagree with reality.
    _claim(
        "CHANGELOG.md", "reconciliation, CSV side", "csv_data_rows",
        r"canonical active,\s*([\d,]+)\s*=\s*[\d,]+",
        anchor=_A_CL_RECONCILE, section=SECTION_CURRENT_RELEASE,
    ),
    _claim(
        "CHANGELOG.md", "reconciliation, canonical side", "identifiers_active",
        r"canonical active,\s*[\d,]+\s*=\s*([\d,]+)",
        anchor=_A_CL_RECONCILE, section=SECTION_CURRENT_RELEASE,
    ),
    # --- docs/USER_GUIDE.md section 2 export headings ---
    # Promoted from Class C at MAC-717. The Class C entries described
    # these as "pinned to v1.6.2 by design" (146 / 592 / 41,508). At HEAD
    # they print live v1.7.0 values, so the historical-pin rationale is
    # false and three live headline claims were being skipped.
    _claim(
        "docs/USER_GUIDE.md", "high-conf export rows (USER_GUIDE)", "feed_high_confidence",
        r"argus_export_high_confidence\.json`\s*\(([\d,]+)\s+rows",
        anchor=r"^### `exports/argus_export_high_confidence\.json`",
    ),
    _claim(
        "docs/USER_GUIDE.md", "standard export rows (USER_GUIDE)", "feed_standard",
        r"argus_export\.json`\s*\(([\d,]+)\s+rows",
        anchor=r"^### `exports/argus_export\.json`",
    ),
    _claim(
        "docs/USER_GUIDE.md", "CSV data rows (USER_GUIDE)", "csv_data_rows",
        r"argus_export\.csv`\s*\(([\d,]+)\s+data\s+rows",
        anchor=r"^### `exports/argus_export\.csv`",
    ),
]


# Class B / Class C sites are never resolved by the gate. Their `locator`
# is descriptive text for a human reader, deliberately NOT a line number:
# the whole reason MAC-717 exists is that positional pins rot silently,
# and a skip-list that points at the wrong line is a skip nobody can audit.
CLASS_B_SITES: list[dict] = [
    {"file": "CHANGELOG.md", "locator": "**Three new sources**, 95 to 98",
     "description": "three new sources (95 to 98)",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "CHANGELOG.md", "locator": "**`identifiers` active:**",
     "description": "identifiers active 43,134 -> 43,088 (net -46)",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "CHANGELOG.md", "locator": "**`identifiers` total:**",
     "description": "identifiers total 43,840 -> 43,892 (+52)",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "CHANGELOG.md", "locator": "**`manufacturers`:** 156 ->",
     "description": "manufacturers 156 -> 260; sources 95 -> 98; behavioral 214; category enum 20",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "CHANGELOG.md", "locator": "Counted as distinct wire values rather than rows",
     "description": "wire values 42,996 -> 43,028 (net +32) and its stated reduction",
     "reason": "delta pair valid only alongside the reduction that produced it"},
    {"file": "README.md", "locator": "Active moves 43,134 -> 43,088 (second clause of the active-identifiers bullet)",
     "description": "Active moves 43,134 -> 43,088, standard feed 977 -> 983, high-confidence 481 -> 501",
     "reason": "delta and provenance line anchored to v1.7.0 migration"},
    {"file": "README.md", "locator": "The rest: **8 new identifiers**",
     "description": "8 new identifiers / 44 more OUIs / three new sources / 84 OEM camera brands",
     "reason": "delta and provenance lines anchored to v1.7.0 migration"},
    {"file": "README.md", "locator": "Active identifiers move 43,134 ->",
     "description": "active 43,134 -> 43,088; standard feed 977 -> 983; high-confidence 481 -> 501; behavioral holds at 132; schema_version 33 -> 35",
     "reason": "delta and provenance lines anchored to v1.7.0 migration"},
]


CLASS_C_SITES: list[dict] = [
    # SETUP.md's expected-output block is a dated snapshot of a v1.6.2-era
    # database, kept as historical record.
    {"file": "docs/engineering/SETUP.md",
     "locator": "expected-output block under 'Once you have supplied a database'",
     "description": "v1.6.2 verify block (Schema version 30 / 41508 active / 41890 total / manufacturers 126)",
     "reason": "dated verify block retained as historical record"},
    # DATA_DICTIONARY.md's row-count table carries its own provenance line
    # ("Verified against db/argus.db 2026-05-29 at HEAD def7b95"), which is
    # what makes it a snapshot rather than a live claim.
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `identifiers` |",
     "description": "identifiers 41,716 active + 342 chained-superseded + 40 self-loop",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `raw_observations` |",
     "description": "raw_observations 147,421",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `sources` |",
     "description": "sources 74",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `manufacturers` |",
     "description": "manufacturers 126 (8 arms)",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `deployment_observations` |",
     "description": "deployment_observations 116,774",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `procurement_records` |",
     "description": "procurement_records 50,492",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `fcc_grantees` |",
     "description": "fcc_grantees 50,153",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `council_minutes_matters` |",
     "description": "council_minutes_matters 3",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `wigle_anchor_priority` |",
     "description": "wigle_anchor_priority 80,697",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `behavioral_signatures` |",
     "description": "behavioral_signatures 201",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `conflicts` |",
     "description": "conflicts 36",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `extraction_runs` |",
     "description": "extraction_runs 121 / MAX(id)=126",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `source_reclassifications` |",
     "description": "source_reclassifications 809",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `fcc_citation_deferred_queue` |",
     "description": "fcc_citation_deferred_queue 671",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
    {"file": "docs/engineering/DATA_DICTIONARY.md", "locator": "| `schema_version` |",
     "description": "schema_version 30",
     "reason": "DATA_DICTIONARY v1.6.5 row-count snapshot, pinned by design"},
]


# ---------------------------------------------------------------------------
# DB access (read-only).
# ---------------------------------------------------------------------------


def _open_db_ro(db_path: Path) -> sqlite3.Connection:
    """Open ``db_path`` via the URI form in read-only mode.

    A probe write inside this connection must raise
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
# Settling artifacts (read-only).
# ---------------------------------------------------------------------------


def count_json_entries(path: Path) -> int:
    """Count entries in an emitted Lynceus feed.

    The on-disk key is ``entries`` (each member carries ``pattern`` and
    ``pattern_type``). This is the ONLY sound settling rule for a feed
    count -- see Trap 4 in the module docstring.
    """
    doc = json.loads(path.read_text(encoding="utf-8"))
    return len(doc["entries"])


def count_csv_data_rows(path: Path) -> int:
    """Count data rows in the emitted CSV.

    Row 0 is a ``# meta:`` provenance comment, NOT the column header;
    row 1 is the header. ``len(rows) - 1`` double-counts one row.

    ``source_excerpt`` values contain embedded newlines, so the file has
    materially more physical lines than records: ``wc -l`` overstates,
    and stripping every line that begins with ``#`` corrupts the parse
    because some wrapped excerpt lines begin with ``#`` too. Only a real
    CSV parse counts records. The meta row is skipped by position (it can
    only be row 0), never by a global ``#`` filter.
    """
    n = 0
    header_seen = False
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if not row:
                continue
            if not header_seen:
                if row[0].startswith("# meta:"):
                    continue
                header_seen = True
                continue
            n += 1
    return n


_ARTIFACT_COUNTERS = {
    "json_entries": count_json_entries,
    "csv_data_rows": count_csv_data_rows,
}


def run_settling_artifacts(repo_root: Path) -> tuple[dict[str, int], dict[str, str]]:
    """Count every entry in SETTLE_ARTIFACTS under ``repo_root``.

    Returns ``(results, problems)``. A missing or unparseable artifact
    lands in ``problems`` and is simply absent from ``results``, which
    turns every claim settling against it into an ERROR rather than a
    traceback -- a gate that dies on a missing export tells the operator
    less than one that names the claim it could not settle.
    """
    results: dict[str, int] = {}
    problems: dict[str, str] = {}
    for key, (relpath, kind) in SETTLE_ARTIFACTS.items():
        path = repo_root / relpath
        try:
            results[key] = _ARTIFACT_COUNTERS[kind](path)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            problems[key] = f"{relpath}: {type(exc).__name__}: {exc}"
    return results, problems


# ---------------------------------------------------------------------------
# Claim-site resolution (by content, not by line number).
# ---------------------------------------------------------------------------


@dataclass
class Resolution:
    line: int | None
    text: str | None
    error: str = ""


def _section_window(lines: list[str], section_pat: str) -> tuple[int, int] | str:
    """Return the [lo, hi) index window for ``section_pat``, or an error string.

    The window runs from the matched heading to the next ``## `` heading
    (exclusive), or to end-of-file. The section regex must match exactly
    one heading: zero means the release block was renamed, more than one
    means the gate cannot tell which release a claim belongs to. Both are
    errors rather than a guess.
    """
    starts = [i for i, line in enumerate(lines) if re.search(section_pat, line)]
    if len(starts) != 1:
        return (
            f"section {section_pat!r} matched {len(starts)} headings (need exactly 1)"
        )
    lo = starts[0]
    hi = len(lines)
    for j in range(lo + 1, len(lines)):
        if re.match(r"^## ", lines[j]):
            hi = j
            break
    return (lo, hi)


def resolve_claim_site(claim: dict, lines: list[str] | None) -> Resolution:
    """Locate a claim's line by content.

    Exactly one anchor match in the search window resolves the site.
    Zero matches or more than one are both errors -- an anchor that
    silently takes the first of several matches has moved the blindness
    rather than removed it.
    """
    if lines is None:
        return Resolution(None, None, f"file not found: {claim['file']}")

    lo, hi = 0, len(lines)
    scope = ""
    section = claim.get("section")
    if section:
        window = _section_window(lines, section)
        if isinstance(window, str):
            return Resolution(None, None, window)
        lo, hi = window
        scope = f" within section (lines {lo + 1}-{hi})"

    anchor = claim["anchor"]
    hits = [i for i in range(lo, hi) if re.search(anchor, lines[i])]
    if not hits:
        return Resolution(None, None, f"anchor {anchor!r} matched no line{scope}")
    if len(hits) > 1:
        located = ", ".join(str(h + 1) for h in hits)
        return Resolution(
            None, None, f"anchor {anchor!r} is ambiguous, matched lines {located}{scope}"
        )
    return Resolution(hits[0] + 1, lines[hits[0]], "")


# ---------------------------------------------------------------------------
# Claim extraction and comparison.
# ---------------------------------------------------------------------------


@dataclass
class CompareResult:
    file: str
    line: int | None
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
    """Compare the extracted integer to the settled value."""
    settle_key = claim["settle_key"]
    base = CompareResult(
        file=claim["file"],
        line=claim.get("line"),
        description=claim["description"],
        settle_key=settle_key,
        extracted=extracted,
        settle_value=settle_results.get(settle_key) if settle_key != NO_SETTLING_QUERY else None,
        status="",
    )
    if settle_key == NO_SETTLING_QUERY:
        if extracted is None:
            base.status = "UNSETTLED"
            base.note = "no settling instrument; regex did not match the doc line either"
        else:
            base.status = "UNSETTLED"
            base.note = f"no settling instrument; doc prints {extracted}"
        return base
    if extracted is None:
        base.status = "ERROR"
        base.note = "extract_pattern did not match the resolved doc line"
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


def _read_lines(path: Path) -> list[str] | None:
    """Return the file's lines, or None if it does not exist."""
    try:
        return path.read_text(encoding="utf-8").split("\n")
    except FileNotFoundError:
        return None


def scan_docs(
    settle_results: dict[str, int],
    repo_root: Path | None = None,
) -> list[CompareResult]:
    """Resolve, extract and compare every Class A claim site."""
    root = REPO if repo_root is None else repo_root
    out: list[CompareResult] = []
    cache: dict[str, list[str] | None] = {}
    for claim in CLASS_A_CLAIMS:
        rel = claim["file"]
        if rel not in cache:
            cache[rel] = _read_lines(root / rel)
        resolution = resolve_claim_site(claim, cache[rel])
        if resolution.error:
            out.append(
                CompareResult(
                    file=rel,
                    line=None,
                    description=claim["description"],
                    settle_key=claim["settle_key"],
                    extracted=None,
                    settle_value=None,
                    status="ERROR",
                    note=resolution.error,
                )
            )
            continue
        result = compare_claim(claim, extract_claim(claim, resolution.text), settle_results)
        result.line = resolution.line
        out.append(result)
    return out


def _at(r: CompareResult) -> str:
    return f"{r.file}:{r.line}" if r.line is not None else f"{r.file}:?"


def _format_result(r: CompareResult) -> str:
    if r.status == "PASS":
        return (
            f"PASS  {_at(r)}  {r.description}  "
            f"({r.extracted:,} == settle[{r.settle_key}] = {r.settle_value:,})"
        )
    if r.status == "FAIL":
        return (
            f"FAIL  {_at(r)}  {r.description}  "
            f"(doc says {r.extracted:,}, settle[{r.settle_key}] = {r.settle_value:,})"
        )
    if r.status == "UNSETTLED":
        return f"UNSETTLED  {_at(r)}  {r.description}  ({r.note})"
    if r.status == "ERROR":
        return f"ERROR  {_at(r)}  {r.description}  ({r.note})"
    return f"UNKNOWN  {_at(r)}  {r.description}  ({r.note})"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Argus doc-anchor gate (MAC-699). Read-only against db/argus.db and exports/."
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
    artifact_results, artifact_problems = run_settling_artifacts(REPO)
    settle_results.update(artifact_results)
    for key, problem in sorted(artifact_problems.items()):
        print(f"ERROR  settling artifact {key!r} unreadable: {problem}", file=sys.stderr)
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


# Remaining UNSETTLED, named rather than silenced (MAC-717 acceptance #3):
#
#   CHANGELOG.md  "halts"  -- the `coverage_matrix` `_reconcile` halt tally.
#       No settling instrument exists. The export run emits no machine-readable
#       halt count, and the only halt tallies on disk are the two HB-numbered
#       prose lines in `exports/coverage_report.md` (HB35 and HB36), which are
#       narrative for different heartbeats rather than a per-release counter.
#       Settling this needs the export path to emit a halt tally as data; until
#       it does, a query would be inventing a number rather than reading one.
#
# Deliberately not registered as claim sites (would need new instruments):
#   CHANGELOG.md  canonical `db/argus.db` sha256 and the two `argus_run_id`
#       UUIDs in the fingerprint line. The sha is mechanically checkable and
#       is a reasonable follow-up; the run ids have no per-cycle invariant.

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
