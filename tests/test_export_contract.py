"""The export contract, enforced in the local suite as well as in CI.

CI alone is not enough: a contract that only runs in GitHub Actions is invisible
to anyone working offline, and it stops being a development tool the moment the
workflow is skipped. These tests import the SAME module the CI validator uses
(``scripts/ci/export_contract.py``), so there is exactly one place the pinned
facts live and the two can never disagree.

Everything here is marked ``public``: it reads only files tracked in git. No
canonical DB, no raw/ artifacts, no network. It must pass on a fresh clone.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.export_contract import (  # noqa: E402
    ALL_URL_SCHEMES,
    BEHAVIORAL_KEYS,
    CSV_BLANK_CONFIDENCE,
    CSV_COLUMNS,
    CSV_DISTINCT_RECORD_IDS,
    CSV_DUPLICATE_EXCESS_ROWS,
    CSV_META_PREFIX,
    CSV_PATH,
    CSV_RECORD_ID_MULTIPLICITY,
    CSV_ROW_COUNT,
    CSV_ROWS_WITH_SHARED_ID,
    CSV_SHARED_RECORD_IDS,
    CSV_ZERO_CONFIDENCE,
    DEFAULT_EXPORT_PATHS,
    FEED_KEYS,
    JSON_FEEDS,
    NON_PUBLIC_URL_ROWS,
    NON_PUBLIC_URL_SCHEMES,
    PUBLIC_URL_ROWS,
    PUBLIC_URL_SCHEMES,
    RECORD_ID_RE,
    URL_SCHEME_COUNTS,
    ExportPaths,
    read_csv_meta,
    read_csv_rows,
    read_feed,
    run_contract,
)

pytestmark = pytest.mark.public


# ---------------------------------------------------------------------------
# Fixtures. The CSV is ~26 MB; parse it once for the whole module.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def csv_data():
    fields, rows = read_csv_rows(CSV_PATH)
    return fields, rows


@pytest.fixture(scope="module")
def csv_rows(csv_data):
    return csv_data[1]


@pytest.fixture(scope="module")
def contract_report():
    return run_contract()


# ---------------------------------------------------------------------------
# The whole contract, one test per pinned fact so a failure names itself.
# ---------------------------------------------------------------------------


def _finding_ids():
    return [f.check for f in run_contract().findings]


def test_full_contract_has_no_violations(contract_report):
    """The headline assertion: every pinned fact still holds."""
    failures = [
        f"{f.check}: expected {f.expected}, measured {f.measured}"
        for f in contract_report.failures
    ]
    assert not failures, "export contract violations:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# MUTATION CONTROLS: proof the contract can actually fail.
#
# What used to stand here was `assert len(findings) >= 30`, and it was vacuous.
# The finding count is a STRUCTURAL CONSTANT -- one finding per assertion in
# check_csv/check_json_feeds -- so it is the same on the real CSV as on a CSV
# truncated to ten rows. The test therefore passed on garbage, while looking
# like it was guarding the guard.
#
# Counting assertions never proves a checker works. Only observing it FAIL on a
# known-bad input does. So: corrupt a copy of the CSV four ways and require the
# SPECIFIC check that owns each fact to go red, with a pristine round-trip as
# the positive control proving the harness itself is not what breaks it.
# ---------------------------------------------------------------------------


def _write_csv(directory: Path, meta_line: str, fieldnames, rows) -> ExportPaths:
    """Materialise an exports/ directory: a written CSV, the real JSON feeds."""
    directory.mkdir(parents=True, exist_ok=True)
    dst = directory / CSV_PATH.name
    with dst.open("w", newline="", encoding="utf-8") as fh:
        fh.write(meta_line)
        writer = csv.DictWriter(fh, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    for real in DEFAULT_EXPORT_PATHS.all_paths():
        if real == DEFAULT_EXPORT_PATHS.csv:
            continue
        link = directory / real.name
        if not link.exists():
            link.symlink_to(real)
    return ExportPaths.for_dir(directory)


@pytest.fixture(scope="module")
def csv_source():
    """(meta line, fieldnames, rows) read once for every mutation to build on."""
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        meta_line = fh.readline()
    assert meta_line.startswith(CSV_META_PREFIX)
    fields, rows = read_csv_rows(CSV_PATH)
    return meta_line, fields, rows


def _mutate_drop_a_column(fields, rows):
    dropped = "notes"
    return [f for f in fields if f != dropped], [
        {k: v for k, v in r.items() if k != dropped} for r in rows
    ]


def _mutate_break_a_confidence(fields, rows):
    rows = [dict(r) for r in rows]
    for row in rows:
        if (row["confidence"] or "").strip():
            row["confidence"] = "not-a-number"
            break
    else:
        pytest.fail("no scored row to corrupt; the mutation would be vacuous")
    return fields, rows


def _mutate_add_a_sixteenth_shared_id(fields, rows):
    """Re-point one row's id at another unique id: 15 shared ids becomes 16."""
    rows = [dict(r) for r in rows]
    counts = Counter(r["argus_record_id"] for r in rows)
    unique_rows = [r for r in rows if counts[r["argus_record_id"]] == 1]
    assert len(unique_rows) >= 2, "need two singleton ids to collide"
    donor, target = unique_rows[0], unique_rows[-1]
    donor["argus_record_id"] = target["argus_record_id"]
    return fields, rows


def _mutate_undocumented_source_url_scheme(fields, rows):
    rows = [dict(r) for r in rows]
    rows[0]["source_url"] = "ftp://example.invalid/undocumented-scheme"
    return fields, rows


MUTATIONS = [
    pytest.param(_mutate_drop_a_column, "csv.columns", id="drop-a-column"),
    pytest.param(_mutate_break_a_confidence, "csv.confidence.unparseable",
                 id="break-a-confidence-value"),
    pytest.param(_mutate_add_a_sixteenth_shared_id, "csv.record_id.shared_ids",
                 id="add-a-16th-shared-id"),
    pytest.param(_mutate_undocumented_source_url_scheme,
                 "csv.source_url.unknown_scheme", id="undocumented-url-scheme"),
]


@pytest.fixture(scope="module")
def pristine_roundtrip(tmp_path_factory, csv_source):
    meta_line, fields, rows = csv_source
    return _write_csv(tmp_path_factory.mktemp("pristine"), meta_line, fields, rows)


def test_mutation_harness_positive_control(pristine_roundtrip):
    """The control. Rewriting the CSV unchanged must still PASS.

    Without this, a mutation test proves nothing: every mutation would "fail"
    simply because the harness mangles the file on the way through.
    """
    report = run_contract(pristine_roundtrip)
    assert report.ok, (
        "the re-written but UNMUTATED csv already fails the contract, so no "
        "mutation below can be attributed to its mutation: "
        + "; ".join(f"{f.check} expected {f.expected} measured {f.measured}"
                    for f in report.failures)
    )


@pytest.mark.parametrize("mutate,expected_check", MUTATIONS)
def test_contract_fails_on_a_corrupted_csv(
    tmp_path_factory, csv_source, mutate, expected_check
):
    """Each corruption must be caught by the check that owns that fact.

    Asserting merely that *something* failed would let one over-broad check
    mask every other one. The named check has to be the one that goes red.
    """
    meta_line, fields, rows = csv_source
    m_fields, m_rows = mutate(fields, rows)
    paths = _write_csv(
        tmp_path_factory.mktemp("mutated"), meta_line, m_fields, m_rows
    )

    report = run_contract(paths)
    failed = {f.check for f in report.failures}

    assert not report.ok, (
        f"the contract PASSED on a CSV corrupted by {mutate.__name__}; it is "
        "not detecting the defect class it claims to cover"
    )
    assert expected_check in failed, (
        f"{expected_check} did not fail on {mutate.__name__}; something else "
        f"caught it instead: {sorted(failed)}"
    )


def test_finding_count_is_a_structural_constant_not_a_vacuity_signal(
    tmp_path_factory, csv_source, contract_report
):
    """Why the old `len(findings) >= 30` assertion was worthless.

    Truncating the CSV to ten rows leaves the finding COUNT untouched -- the
    contract still runs every assertion, they just measure a gutted file. The
    count is therefore not evidence of anything; the verdict is. This test pins
    that reasoning so nobody restores a count-based vacuity check.
    """
    meta_line, fields, rows = csv_source
    paths = _write_csv(
        tmp_path_factory.mktemp("truncated"), meta_line, fields, rows[:10]
    )
    truncated = run_contract(paths)

    assert len(truncated.findings) == len(contract_report.findings), (
        "the finding count is expected to be identical on a gutted file; if it "
        "is not, this rationale needs revisiting"
    )
    assert not truncated.ok, "a ten-row CSV must fail the contract"
    assert "csv.row_count" in {f.check for f in truncated.failures}


# ---------------------------------------------------------------------------
# The three traps, tested explicitly. Each has already bitten someone.
# ---------------------------------------------------------------------------


def test_csv_line_one_is_a_meta_comment_not_the_header():
    """Trap 1: csv.DictReader on the raw handle misparses the entire file."""
    with CSV_PATH.open(encoding="utf-8") as fh:
        first = fh.readline()
    assert first.startswith("# meta:"), (
        "line 1 of argus_export.csv is expected to be a '# meta:' comment; "
        "consumers that skip it would now be dropping a real data row"
    )
    meta = read_csv_meta(CSV_PATH)
    assert int(meta["record_count"]) == CSV_ROW_COUNT
    assert meta["schema_version"].isdigit()


def test_header_is_the_second_line_with_the_documented_columns(csv_data):
    fields, _rows = csv_data
    assert fields == list(CSV_COLUMNS)
    assert len(fields) == 16


def test_physical_line_count_is_not_the_row_count(csv_rows):
    """Trap 2: quoted source_excerpt fields contain embedded newlines.

    A CI step that counts rows with `wc -l` gets ~47.5k for 43,126 rows. This
    test exists so that mistake fails loudly instead of quietly re-pinning a
    wrong number.
    """
    with CSV_PATH.open("rb") as fh:
        physical_lines = sum(1 for _ in fh)
    assert len(csv_rows) == CSV_ROW_COUNT
    assert physical_lines > CSV_ROW_COUNT + 1, (
        "expected embedded newlines inside quoted fields; if this ever becomes "
        "an equality, the wc -l shortcut would start looking correct by accident"
    )


def test_argus_record_id_is_a_pattern_key_not_a_row_id(csv_rows):
    """Trap 3: argus_record_id is NOT unique. Pin the duplicate population.

    Asserting uniqueness here would be asserting a falsehood. But so is reading
    the surplus as "the number of rows that share an id" -- and that misreading
    is what shipped a false number into the README, the CHANGELOG, the user
    guide and the doc validator. The three numbers are DIFFERENT:

        43,096  distinct ids
            30  SURPLUS rows (43,126 - 43,096), rows beyond one-per-id
            15  ids that appear on more than one row
            45  rows carrying one of those 15 ids

    All of them are asserted separately, because the surplus alone is a weak
    detector: merging two 2-way collisions into one 3-way collision leaves it
    at 30 while the shared-id count and the histogram both move.
    """
    ids = [r["argus_record_id"] for r in csv_rows]
    counts = Counter(ids)
    distinct = len(counts)
    surplus = len(ids) - distinct
    shared = {i: n for i, n in counts.items() if n > 1}
    rows_with_shared_id = sum(shared.values())
    multiplicity = dict(sorted(Counter(shared.values()).items()))

    assert distinct == CSV_DISTINCT_RECORD_IDS
    assert surplus == CSV_DUPLICATE_EXCESS_ROWS, (
        f"the surplus is {surplus} rows beyond one-per-id; the pinned value is "
        f"{CSV_DUPLICATE_EXCESS_ROWS}. This is NOT the number of rows that "
        "share an id. Growth means a new identifier collision entered the "
        "export -- investigate, do not re-pin blindly."
    )
    assert len(shared) == CSV_SHARED_RECORD_IDS, (
        f"{len(shared)} ids appear on more than one row; pinned at "
        f"{CSV_SHARED_RECORD_IDS}"
    )
    assert rows_with_shared_id == CSV_ROWS_WITH_SHARED_ID, (
        f"{rows_with_shared_id} rows carry a shared argus_record_id; pinned at "
        f"{CSV_ROWS_WITH_SHARED_ID}. This is the number to quote when prose "
        "says 'rows share an id' -- never the surplus."
    )
    assert multiplicity == CSV_RECORD_ID_MULTIPLICITY, (
        f"multiplicity histogram moved: {multiplicity} vs pinned "
        f"{CSV_RECORD_ID_MULTIPLICITY}"
    )

    # The arithmetic that ties the three numbers together. If this ever fails,
    # two of them were measured against different reads of the file.
    assert surplus == rows_with_shared_id - len(shared)
    assert sum(n * c for n, c in multiplicity.items()) == rows_with_shared_id

    assert surplus > 0, (
        "the duplicate count went to zero; argus_record_id may now be row-unique, "
        "which would be a real semantic change worth documenting"
    )


# ---------------------------------------------------------------------------
# Column-level contract
# ---------------------------------------------------------------------------


def test_row_count_matches_the_meta_line(csv_rows):
    meta = read_csv_meta(CSV_PATH)
    assert len(csv_rows) == int(meta["record_count"]) == CSV_ROW_COUNT


def test_every_confidence_is_blank_or_an_int_in_range(csv_rows):
    blank = 0
    bad: list[str] = []
    for row in csv_rows:
        raw = (row["confidence"] or "").strip()
        if not raw:
            blank += 1
            continue
        if not raw.isdigit() or not (0 <= int(raw) <= 99):
            bad.append(raw)
    assert bad[:10] == [], f"{len(bad)} confidence values outside 0..99"
    assert blank == CSV_BLANK_CONFIDENCE
    zeros = sum(1 for r in csv_rows if (r["confidence"] or "").strip() == "0")
    assert zeros == CSV_ZERO_CONFIDENCE, (
        "blank confidence and an explicit 0 are different states; both counts "
        "are pinned so a coercion bug cannot move one into the other unnoticed"
    )


def test_every_argus_record_id_is_sixteen_lowercase_hex(csv_rows):
    bad = [r["argus_record_id"] for r in csv_rows if not RECORD_ID_RE.match(r["argus_record_id"])]
    assert bad[:10] == [], f"{len(bad)} malformed argus_record_id values"


def test_every_source_url_uses_a_documented_scheme(csv_rows):
    unknown = [
        r["source_url"][:80]
        for r in csv_rows
        if not (r["source_url"] or "").startswith(ALL_URL_SCHEMES)
    ]
    assert unknown[:10] == [], f"{len(unknown)} rows use an undocumented source_url scheme"


@pytest.mark.parametrize("scheme,expected", sorted(URL_SCHEME_COUNTS.items()))
def test_source_url_scheme_census_is_pinned(csv_rows, scheme, expected):
    count = sum(1 for r in csv_rows if (r["source_url"] or "").startswith(scheme))
    assert count == expected


def test_public_and_non_public_url_rows_account_for_every_row(csv_rows):
    public = sum(1 for r in csv_rows if (r["source_url"] or "").startswith(PUBLIC_URL_SCHEMES))
    non_public = sum(
        1 for r in csv_rows if (r["source_url"] or "").startswith(NON_PUBLIC_URL_SCHEMES)
    )
    assert public == PUBLIC_URL_ROWS
    assert non_public == NON_PUBLIC_URL_ROWS
    assert public + non_public == len(csv_rows) == CSV_ROW_COUNT


def test_non_public_rows_exist_so_the_url_claim_stays_honest(csv_rows):
    """865 rows have provenance but no direct URL.

    This is the measurement behind the README's false "direct URL citation"
    claim. It lives in the suite so that fixing the README cannot quietly
    un-measure the thing that made the claim false.
    """
    non_public = sum(
        1 for r in csv_rows if (r["source_url"] or "").startswith(NON_PUBLIC_URL_SCHEMES)
    )
    assert non_public == NON_PUBLIC_URL_ROWS
    assert non_public > 0


# ---------------------------------------------------------------------------
# JSON feeds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(JSON_FEEDS))
def test_feed_is_a_meta_entries_object(name):
    path, _count, _keys = JSON_FEEDS[name]
    meta, entries = read_feed(path)
    assert isinstance(entries, list), f"{name}: entries must be a list"
    assert isinstance(meta, dict) and meta, f"{name}: _meta must be a non-empty object"


@pytest.mark.parametrize("name", sorted(JSON_FEEDS))
def test_feed_record_count_matches_its_own_meta(name):
    path, expected, _keys = JSON_FEEDS[name]
    meta, entries = read_feed(path)
    assert len(entries) == expected
    assert meta.get("record_count") == expected


@pytest.mark.parametrize("name", sorted(JSON_FEEDS))
def test_feed_records_have_the_exact_documented_key_set(name):
    path, _count, expected_keys = JSON_FEEDS[name]
    _meta, entries = read_feed(path)
    key_sets = {frozenset(e.keys()) for e in entries}
    assert len(key_sets) == 1, f"{name}: records are not uniform: {len(key_sets)} key sets"
    assert next(iter(key_sets)) == expected_keys


def test_no_feed_emits_a_severity_field():
    """The README claims a `severity` field. No feed has one.

    This test pins the TRUE state. It is deliberately written so that if a
    future release actually starts emitting `severity`, this test fails and
    forces the README and the contract to be updated together -- rather than
    letting the doc and the data drift apart again in the other direction.
    """
    for name, (path, _count, _keys) in JSON_FEEDS.items():
        _meta, entries = read_feed(path)
        with_sev = [e for e in entries if "severity" in e]
        assert not with_sev, (
            f"{name}: {len(with_sev)} records now carry a `severity` field. "
            "If this is intentional, update export_contract.FEED_KEYS and the README."
        )


def test_standard_and_high_confidence_feeds_share_a_record_shape():
    assert JSON_FEEDS["argus_export.json"][2] == FEED_KEYS
    assert JSON_FEEDS["argus_export_high_confidence.json"][2] == FEED_KEYS
    assert JSON_FEEDS["argus_export_behavioral_signatures.json"][2] == BEHAVIORAL_KEYS
    assert FEED_KEYS != BEHAVIORAL_KEYS


def test_high_confidence_is_a_subset_of_the_standard_feed():
    """504 high-confidence records should all appear in the 1,014-record feed.

    Both are emitted from the same run with the same scope filter and differing
    confidence floors (>=70 vs >=30), so the strict feed must be contained in
    the looser one. A break here means the two feeds diverged.
    """
    _m1, std = read_feed(JSON_FEEDS["argus_export.json"][0])
    _m2, hc = read_feed(JSON_FEEDS["argus_export_high_confidence.json"][0])
    std_ids = {e["argus_record_id"] for e in std}
    stray = sorted({e["argus_record_id"] for e in hc} - std_ids)
    assert stray[:10] == [], (
        f"{len(stray)} high-confidence records are absent from the standard feed"
    )


@pytest.mark.parametrize("name", sorted(JSON_FEEDS))
def test_feed_ids_are_sixteen_lowercase_hex(name):
    path, _count, _keys = JSON_FEEDS[name]
    _meta, entries = read_feed(path)
    bad = [e["argus_record_id"] for e in entries
           if not RECORD_ID_RE.match(str(e["argus_record_id"]))]
    assert bad[:10] == []


def test_feed_exported_at_timestamps_are_iso8601_utc():
    for name, (path, _count, _keys) in JSON_FEEDS.items():
        meta, _entries = read_feed(path)
        stamp = meta.get("exported_at", "")
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", stamp), (
            f"{name}: exported_at {stamp!r} is not ISO-8601 UTC"
        )
