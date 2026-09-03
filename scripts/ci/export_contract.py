"""The Argus export contract: the shape the shipped artifacts actually have.

This module is the single source of truth for the pinned facts. Both the CI
validator (``scripts/ci/check_export_contract.py``) and the local test
(``tests/test_export_contract.py``) import it, so the contract can never drift
between "what CI checks" and "what the suite checks".

Everything here is measurable from files that are TRACKED IN GIT. No canonical
DB, no raw/ artifacts, no network. That is deliberate: this contract is exactly
the part of Argus a stranger with a fresh clone can re-verify for themselves.

Four traps are encoded here because every one of them has already bitten:

1. ``exports/argus_export.csv`` line 1 is a ``# meta:`` COMMENT, not the header.
   ``csv.DictReader`` on the raw handle misparses the whole file. Always read
   through :func:`read_csv_rows`, which consumes the meta line first.

2. ``wc -l`` is NOT the row count. Quoted ``source_excerpt`` fields contain
   embedded newlines, so the file has ~47.5k physical lines for 43,126 rows.
   Count with the ``csv`` module or the number is wrong.

3. ``argus_record_id`` is NOT row-unique. It is a content-derived pattern key
   (a SHA-256 prefix over ``{identifier_type}|{normalized_identifier}``), so
   rows that share a normalized identifier share an id. We pin the duplicate
   population instead of asserting uniqueness, which would be a false claim.

4. The duplicate population has THREE different numbers and they are routinely
   confused. Measured at HEAD 9b32212 over ``exports/argus_export.csv``:

     43,126  data rows
     43,096  distinct argus_record_id values
         15  ids that appear on more than one row
         45  rows carrying one of those 15 ids
         30  SURPLUS rows (43,126 - 43,096), i.e. rows beyond one-per-id

   30 is the surplus, NOT "the number of rows that share an id". That
   conflation shipped into the README, the CHANGELOG, the user guide and the
   doc validator. All five numbers are pinned below so the mistake cannot be
   made again by reading one of them and inferring the others.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORTS_DIR = REPO_ROOT / "exports"

CSV_NAME = "argus_export.csv"
STANDARD_NAME = "argus_export.json"
HIGH_CONF_NAME = "argus_export_high_confidence.json"
BEHAVIORAL_NAME = "argus_export_behavioral_signatures.json"

CSV_PATH = EXPORTS_DIR / CSV_NAME
STANDARD_JSON = EXPORTS_DIR / STANDARD_NAME
HIGH_CONF_JSON = EXPORTS_DIR / HIGH_CONF_NAME
BEHAVIORAL_JSON = EXPORTS_DIR / BEHAVIORAL_NAME

CSV_META_PREFIX = "# meta:"


@dataclass(frozen=True)
class ExportPaths:
    """Where the four export artifacts live.

    Every reader takes one of these rather than reaching for the module-level
    constants, so the contract can be pointed at a fixture directory. A
    validator that can only ever read the real artifacts cannot be tested:
    there is no way to show it FAILS on a corrupted input, and a check whose
    failure has never been observed is not known to work.
    """

    csv: Path
    standard: Path
    high_conf: Path
    behavioral: Path

    @classmethod
    def for_dir(cls, directory: Path | str) -> "ExportPaths":
        d = Path(directory)
        return cls(
            csv=d / CSV_NAME,
            standard=d / STANDARD_NAME,
            high_conf=d / HIGH_CONF_NAME,
            behavioral=d / BEHAVIORAL_NAME,
        )

    def all_paths(self) -> list[Path]:
        return [self.csv, self.standard, self.high_conf, self.behavioral]

    def feed(self, name: str) -> Path:
        return getattr(self, FEED_ATTRS[name])


FEED_ATTRS = {
    STANDARD_NAME: "standard",
    HIGH_CONF_NAME: "high_conf",
    BEHAVIORAL_NAME: "behavioral",
}

DEFAULT_EXPORT_PATHS = ExportPaths.for_dir(EXPORTS_DIR)

# ---------------------------------------------------------------------------
# Pinned facts. Measured at HEAD 9b32212. A change here must be a deliberate
# release decision, never a convenience edit to make a red job go green.
# ---------------------------------------------------------------------------

CSV_COLUMNS = (
    "argus_record_id",
    "id",
    "identifier",
    "identifier_type",
    "device_category",
    "manufacturer",
    "model",
    "confidence",
    "source_type",
    "source_url",
    "source_excerpt",
    "geographic_scope",
    "description",
    "first_seen",
    "last_verified",
    "notes",
)

CSV_ROW_COUNT = 43_126
CSV_BLANK_CONFIDENCE = 174
CSV_ZERO_CONFIDENCE = 262

# --- the argus_record_id duplicate population; see trap 4 in the docstring ---
CSV_DISTINCT_RECORD_IDS = 43_096
# Rows beyond one-per-id: 43,126 - 43,096. This is a SURPLUS, and it is NOT the
# number of rows that share an id -- that is CSV_ROWS_WITH_SHARED_ID, below.
CSV_DUPLICATE_EXCESS_ROWS = 30
# Ids that appear on more than one row.
CSV_SHARED_RECORD_IDS = 15
# Rows carrying one of those 15 ids. 8*2 + 2*3 + 3*4 + 1*5 + 1*6 = 45.
CSV_ROWS_WITH_SHARED_ID = 45
# How many ids appear on exactly N rows, for every N > 1. This is the strongest
# drift detector of the three: a collision that swaps one 3-way group for three
# 2-way groups leaves the surplus unchanged but moves this histogram.
CSV_RECORD_ID_MULTIPLICITY = {2: 8, 3: 2, 4: 3, 5: 1, 6: 1}

# The single approved sentence for describing the duplication in prose. The doc
# validator builds its extraction regex from these same constants, so a doc and
# the contract cannot state different numbers without the gate going red.
DUPLICATION_SENTENCE = (
    f"{CSV_DISTINCT_RECORD_IDS:,} distinct `argus_record_id` values across "
    f"{CSV_ROW_COUNT:,} rows: {CSV_SHARED_RECORD_IDS} ids are shared by more "
    f"than one row, covering {CSV_ROWS_WITH_SHARED_ID} rows in total."
)

CONFIDENCE_MIN = 0
CONFIDENCE_MAX = 99

RECORD_ID_RE = re.compile(r"^[0-9a-f]{16}$")

# Every source_url starts with one of these. The five non-public schemes are
# documented provenance forms, not URLs -- which is precisely why the README's
# "direct URL citation" claim is checked separately in check_doc_claims.py.
PUBLIC_URL_SCHEMES = ("https://", "http://")
NON_PUBLIC_URL_SCHEMES = (
    "wave_i_aggregate:",
    "apkcombo:",
    "APK extract:",
    "argus-internal:",
    "manufacturer_app:",
)
ALL_URL_SCHEMES = PUBLIC_URL_SCHEMES + NON_PUBLIC_URL_SCHEMES

URL_SCHEME_COUNTS = {
    "https://": 42_201,
    "http://": 60,
    "wave_i_aggregate:": 660,
    "apkcombo:": 188,
    "APK extract:": 12,
    "argus-internal:": 3,
    "manufacturer_app:": 2,
}
PUBLIC_URL_ROWS = 42_261
NON_PUBLIC_URL_ROWS = 865

# The three JSON feeds. Each is an OBJECT of shape {"_meta": {...},
# "entries": [...]} -- never a bare array. Records live under "entries".
FEED_KEYS = frozenset({"argus_record_id", "description", "pattern", "pattern_type"})
BEHAVIORAL_KEYS = frozenset(
    {
        "argus_record_id",
        "cellular_generation",
        "confidence",
        "signature_name",
        "threshold_json",
    }
)

JSON_FEEDS = {
    "argus_export.json": (STANDARD_JSON, 1_014, FEED_KEYS),
    "argus_export_high_confidence.json": (HIGH_CONF_JSON, 504, FEED_KEYS),
    "argus_export_behavioral_signatures.json": (BEHAVIORAL_JSON, 132, BEHAVIORAL_KEYS),
}


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """One contract assertion and its measured outcome."""

    check: str
    expected: str
    measured: str
    ok: bool
    detail: str = ""

    @property
    def verdict(self) -> str:
        return "PASS" if self.ok else "FAIL"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def add(self, check, expected, measured, ok, detail=""):
        self.findings.append(
            Finding(check, str(expected), str(measured), bool(ok), detail)
        )

    def eq(self, check, expected, measured, detail=""):
        """Assert equality and record the comparison either way."""
        self.add(check, expected, measured, expected == measured, detail)

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if not f.ok]

    @property
    def ok(self) -> bool:
        return not self.failures


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------


def read_csv_meta(path: Path = CSV_PATH) -> dict[str, str]:
    """Parse the leading ``# meta:`` comment line into a dict.

    Raises if line 1 is not the meta comment -- that shape change is itself a
    contract break and must not be silently tolerated.
    """
    with path.open(newline="", encoding="utf-8") as fh:
        first = fh.readline()
    if not first.startswith(CSV_META_PREFIX):
        raise ValueError(
            f"{path.name}: line 1 is not a '{CSV_META_PREFIX}' comment; "
            f"got {first[:80]!r}"
        )
    body = first[len(CSV_META_PREFIX) :].strip()
    out: dict[str, str] = {}
    for part in body.split(","):
        if "=" in part:
            k, _, v = part.partition("=")
            out[k.strip()] = v.strip()
    return out


def read_csv_rows(path: Path = CSV_PATH) -> tuple[list[str], list[dict[str, str]]]:
    """Return ``(fieldnames, rows)`` with the meta line correctly skipped."""
    with path.open(newline="", encoding="utf-8") as fh:
        first = fh.readline()
        if not first.startswith(CSV_META_PREFIX):
            # Not the expected shape: rewind so we at least parse honestly.
            fh.seek(0)
        reader = csv.DictReader(fh)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    return fields, rows


def read_feed(path: Path) -> tuple[dict, list[dict]]:
    """Return ``(_meta, entries)`` for a JSON feed, enforcing the wrapper shape."""
    with path.open(encoding="utf-8") as fh:
        doc = json.load(fh)
    if not isinstance(doc, dict):
        raise ValueError(f"{path.name}: expected a JSON object, got {type(doc).__name__}")
    if "entries" not in doc:
        raise ValueError(f"{path.name}: missing top-level 'entries' key")
    return doc.get("_meta", {}), doc["entries"]


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------


def check_csv(report: Report, path: Path | None = None) -> None:
    path = CSV_PATH if path is None else path
    meta = read_csv_meta(path)
    fields, rows = read_csv_rows(path)

    report.eq("csv.columns", list(CSV_COLUMNS), fields,
              "16 columns in the documented order")
    report.eq("csv.row_count", CSV_ROW_COUNT, len(rows),
              "parsed with the csv module, NOT wc -l")

    meta_count = int(meta.get("record_count", -1))
    report.eq("csv.meta.record_count", CSV_ROW_COUNT, meta_count,
              "the meta line's own self-report")
    report.eq("csv.meta_matches_parsed", len(rows), meta_count,
              "meta record_count must equal the parsed data-row count")

    # --- confidence -------------------------------------------------------
    blank = 0
    zero = 0
    out_of_range: list[str] = []
    unparseable: list[str] = []
    for row in rows:
        raw = (row.get("confidence") or "").strip()
        if not raw:
            blank += 1
            continue
        try:
            val = int(raw)
        except ValueError:
            unparseable.append(raw)
            continue
        if val == 0:
            zero += 1
        if not (CONFIDENCE_MIN <= val <= CONFIDENCE_MAX):
            out_of_range.append(raw)

    report.eq("csv.confidence.blank", CSV_BLANK_CONFIDENCE, blank,
              "blank means UNSCORED; a distinct state from an explicit 0")
    report.eq("csv.confidence.explicit_zero", CSV_ZERO_CONFIDENCE, zero,
              "rows that really do carry 0, which blank must not be coerced to")
    report.eq("csv.confidence.unparseable", 0, len(unparseable),
              f"samples={unparseable[:5]}" if unparseable else "")
    report.eq("csv.confidence.out_of_range", 0, len(out_of_range),
              f"must be {CONFIDENCE_MIN}..{CONFIDENCE_MAX}; "
              f"samples={out_of_range[:5]}" if out_of_range else
              f"every value blank or {CONFIDENCE_MIN}..{CONFIDENCE_MAX}")

    # --- argus_record_id --------------------------------------------------
    ids = [r.get("argus_record_id", "") for r in rows]
    malformed = [i for i in ids if not RECORD_ID_RE.match(i)]
    report.eq("csv.record_id.format", 0, len(malformed),
              f"every id matches /^[0-9a-f]{{16}}$/; samples={malformed[:5]}"
              if malformed else "every id matches /^[0-9a-f]{16}$/")

    counts = Counter(ids)
    distinct = len(counts)
    excess = len(ids) - distinct
    shared = {i: n for i, n in counts.items() if n > 1}
    rows_with_shared_id = sum(shared.values())
    multiplicity = dict(sorted(Counter(shared.values()).items()))

    report.eq("csv.record_id.distinct", CSV_DISTINCT_RECORD_IDS, distinct)
    # NOT a uniqueness assertion. argus_record_id is a pattern key; pinning the
    # duplicate population catches drift without pretending the key is a row id.
    #
    # Three distinct numbers, pinned separately on purpose. The surplus alone is
    # a weak detector: merging two 2-way collisions into one 3-way collision
    # leaves it at 30 while both the shared-id count and the histogram move.
    direction = ""
    if excess > CSV_DUPLICATE_EXCESS_ROWS:
        direction = (f"surplus GREW by {excess - CSV_DUPLICATE_EXCESS_ROWS}; "
                     "a new identifier collision entered the export")
    elif excess < CSV_DUPLICATE_EXCESS_ROWS:
        direction = (f"surplus SHRANK by {CSV_DUPLICATE_EXCESS_ROWS - excess}; "
                     "rows were removed or the key changed")
    report.eq("csv.record_id.duplicate_excess_rows", CSV_DUPLICATE_EXCESS_ROWS, excess,
              direction or f"rows beyond one-per-id ({len(ids)} - {distinct}); a "
                           "SURPLUS, not the number of rows that share an id")
    report.eq("csv.record_id.shared_ids", CSV_SHARED_RECORD_IDS, len(shared),
              "ids appearing on more than one row")
    report.eq("csv.record_id.rows_with_shared_id", CSV_ROWS_WITH_SHARED_ID,
              rows_with_shared_id, "rows carrying one of those ids")
    report.eq("csv.record_id.multiplicity", CSV_RECORD_ID_MULTIPLICITY, multiplicity,
              "how many ids appear on exactly N rows, for each N > 1")
    report.eq("csv.record_id.arithmetic_holds", excess,
              rows_with_shared_id - len(shared),
              "surplus must equal (rows carrying a shared id) - (shared ids); "
              "if these ever disagree the three numbers came from different reads")

    # --- source_url -------------------------------------------------------
    scheme_counts = dict.fromkeys(URL_SCHEME_COUNTS, 0)
    unknown: list[str] = []
    for row in rows:
        url = row.get("source_url") or ""
        for scheme in ALL_URL_SCHEMES:
            if url.startswith(scheme):
                scheme_counts[scheme] += 1
                break
        else:
            unknown.append(url[:60])

    report.eq("csv.source_url.unknown_scheme", 0, len(unknown),
              f"samples={unknown[:5]}" if unknown else
              "every source_url is http(s) or one of the 5 documented schemes")
    for scheme, expected in URL_SCHEME_COUNTS.items():
        report.eq(f"csv.source_url.scheme[{scheme}]", expected, scheme_counts[scheme])

    public = sum(scheme_counts[s] for s in PUBLIC_URL_SCHEMES)
    non_public = sum(scheme_counts[s] for s in NON_PUBLIC_URL_SCHEMES)
    report.eq("csv.source_url.public_rows", PUBLIC_URL_ROWS, public)
    report.eq("csv.source_url.non_public_rows", NON_PUBLIC_URL_ROWS, non_public,
              "these rows have provenance but NOT a direct URL citation")
    report.eq("csv.source_url.total", CSV_ROW_COUNT, public + non_public,
              "scheme census must account for every row")


def check_json_feeds(report: Report, paths: ExportPaths | None = None) -> None:
    paths = DEFAULT_EXPORT_PATHS if paths is None else paths
    for name, (_default_path, expected_count, expected_keys) in JSON_FEEDS.items():
        path = paths.feed(name)
        meta, entries = read_feed(path)

        report.eq(f"{name}.record_count", expected_count, len(entries))
        report.eq(f"{name}.meta.record_count", expected_count,
                  meta.get("record_count"),
                  "the feed's own _meta self-report")
        report.eq(f"{name}.meta_matches_entries", len(entries),
                  meta.get("record_count"))

        key_sets = {frozenset(e.keys()) for e in entries}
        if len(key_sets) == 1:
            actual = next(iter(key_sets))
            report.eq(f"{name}.record_keys", sorted(expected_keys), sorted(actual),
                      f"{len(expected_keys)} keys, uniform across all records")
        else:
            report.add(
                f"{name}.record_keys",
                sorted(expected_keys),
                f"{len(key_sets)} DIFFERENT key sets across records",
                False,
                "records are not uniform; "
                + "; ".join(sorted(str(sorted(k)) for k in list(key_sets)[:3])),
            )

        malformed = [
            e.get("argus_record_id")
            for e in entries
            if not RECORD_ID_RE.match(str(e.get("argus_record_id", "")))
        ]
        report.eq(f"{name}.record_id.format", 0, len(malformed),
                  f"samples={malformed[:5]}" if malformed else
                  "every id matches /^[0-9a-f]{16}$/")


def run_contract(paths: ExportPaths | None = None) -> Report:
    """Run every pinned assertion against ``paths`` (the real exports by default).

    Accepting a path set is what makes the contract testable: the mutation
    controls in tests/test_export_contract.py point it at deliberately corrupted
    copies and require it to FAIL. A validator only ever run on a known-good
    input has never demonstrated that it can detect anything.
    """
    paths = DEFAULT_EXPORT_PATHS if paths is None else paths
    report = Report()
    check_csv(report, paths.csv)
    check_json_feeds(report, paths)
    return report


def format_report(report: Report, stream=sys.stdout) -> None:
    width_c = max([len(f.check) for f in report.findings] + [5])
    width_e = min(max([len(f.expected) for f in report.findings] + [8]), 46)
    width_m = min(max([len(f.measured) for f in report.findings] + [8]), 46)

    def trunc(s, w):
        return s if len(s) <= w else s[: w - 1] + "…"

    print(f"{'CHECK'.ljust(width_c)}  {'EXPECTED'.ljust(width_e)}  "
          f"{'MEASURED'.ljust(width_m)}  VERDICT", file=stream)
    print("-" * (width_c + width_e + width_m + 14), file=stream)
    for f in report.findings:
        print(f"{f.check.ljust(width_c)}  {trunc(f.expected, width_e).ljust(width_e)}  "
              f"{trunc(f.measured, width_m).ljust(width_m)}  {f.verdict}", file=stream)
        if not f.ok and f.detail:
            print(f"{' ' * width_c}  -> {f.detail}", file=stream)
