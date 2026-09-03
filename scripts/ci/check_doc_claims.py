#!/usr/bin/env python3
"""Re-measure every claim the README makes about the exports against the files.

This is the anti-drift job. The README is marketing copy that ages; the exports
are the product. When the two disagree, the README is wrong -- and a data
project whose selling point is verification cannot afford a false claim in its
own front page.

Every claim is EXTRACTED from the doc by regex, never hardcoded. If someone
edits the README number, the claim changes with it and the measurement decides
who is right. A hardcoded expectation would silently agree with a doctored doc.

WHY EVERY CLAIM IS MANDATORY
----------------------------
The previous revision guarded five of its nine checks with ``if m:`` -- if the
extraction pattern missed, the check produced no finding at all. Rewording a
sentence therefore DELETED its own gate, and the job stayed green while
measuring less. That happened: at HEAD 9b32212 four of the nine checks had gone
silently blind and the job still reported "15 PASS, 0 FAIL".

So there is no optional claim here. Every registered claim is one of:

  REQUIRED   the doc MUST contain the pattern. Not finding it is a FAIL
             ("claim not found -- it was reworded or deleted"), never a pass.
             A gate a rewrite can disarm is not a gate.

  FORBIDDEN  the doc must NOT contain the pattern, because that exact wording
             is known to be false. Finding it is a FAIL. This is how a
             corrected falsehood is stopped from creeping back.

  DERIVED    measured from the artifacts alone, with no doc pattern to match.

CLAIM_REGISTRY declares all of them up front, and any registered claim that
produced no finding is itself reported as a FAIL. Deleting a check block breaks
the build instead of quietly shrinking the contract.

Three verdict classes, and the distinction is load-bearing:

  PASS / FAIL   The claim was independently re-measured from a tracked file.
                This is verification.

  CONSISTENT    The claim cannot be measured from any tracked file (it needs
  / INCONSISTENT the canonical DB, which is not distributed). All we can do is
                check README against CHANGELOG. Two documents agreeing is NOT
                evidence the number is true. Reported, never counted as
                verified, and never allowed to make the job green on its own.

  UNVERIFIABLE  Cannot be checked at all from the public tree.

Exit status:
    0  every measurable claim holds
    1  at least one measurable claim is false, missing, or a doc pair is
       inconsistent
    2  a required file is missing or unreadable

Usage:
    python3 scripts/ci/check_doc_claims.py
    python3 scripts/ci/check_doc_claims.py --strict-consistency
    python3 scripts/ci/check_doc_claims.py --readme /tmp/fixture/README.md
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.export_contract import (  # noqa: E402
    CSV_DISTINCT_RECORD_IDS,
    CSV_DUPLICATE_EXCESS_ROWS,
    CSV_ROW_COUNT,
    CSV_ROWS_WITH_SHARED_ID,
    CSV_SHARED_RECORD_IDS,
    EXPORTS_DIR,
    NON_PUBLIC_URL_SCHEMES,
    PUBLIC_URL_SCHEMES,
    RECORD_ID_RE,
    REPO_ROOT,
    DEFAULT_EXPORT_PATHS,
    ExportPaths,
    read_csv_rows,
    read_feed,
)

README = REPO_ROOT / "README.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
MIGRATIONS = REPO_ROOT / "db" / "migrations"

PASS, FAIL = "PASS", "FAIL"
CONSISTENT, INCONSISTENT = "CONSISTENT", "INCONSISTENT"
UNVERIFIABLE = "UNVERIFIABLE"
MEASURED_VERDICTS = {PASS, FAIL}
BAD_VERDICTS = {FAIL, INCONSISTENT}

REQUIRED, FORBIDDEN, DERIVED, DOC_ONLY = "REQUIRED", "FORBIDDEN", "DERIVED", "DOC_ONLY"

NUMBER_WORDS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


# ---------------------------------------------------------------------------
# Claim specs. The registry is DERIVED from these tables, so a check and its
# registry entry cannot drift apart.
# ---------------------------------------------------------------------------

FEED_CLAIM_SPECS = (
    "argus_export_high_confidence.json",
    "argus_export.json",
    "argus_export.csv",
    "argus_export_behavioral_signatures.json",
)

ENUM_CLAIM_SPECS = (
    ("device categories", "device_category",
     (r"Device categories\s*\|\s*\*\*(\d+)\*\*", r"\*\*(\d+)\s+device categories\*\*")),
    ("identifier types", "identifier_type",
     (r"Identifier types\s*\|\s*\*\*(\d+)\*\*", r"\*\*(\d+)\s+identifier types\*\*")),
)

DB_ONLY_SPECS = (
    ("manufacturers", r"Manufacturers\s*\|\s*\*\*([\d,]+)\*\*",
     r"\*\*`manufacturers`:\*\*\s*[\d,]+\s*→\s*\*\*([\d,]+)\*\*",
     "SELECT COUNT(*) FROM manufacturers"),
    ("upstream sources", r"Upstream sources\s*\|\s*\*\*([\d,]+)\*\*",
     r"\*\*`sources`:\*\*\s*[\d,]+\s*→\s*\*\*([\d,]+)\*\*",
     "SELECT COUNT(*) FROM sources"),
    ("OEM arms", r"(\d+) of those are OEM arms",
     r"(\d+) of the [\d,]+ are OEM\s+arms",
     "SELECT COUNT(*) FROM manufacturers WHERE is_arm=1"),
)

# The one approved way to describe argus_record_id duplication, built from the
# contract constants so the doc, the contract and this extractor state the same
# numbers by construction. See export_contract.DUPLICATION_SENTENCE.
#
#   "43,096 distinct `argus_record_id` values across 43,126 rows: 15 ids are
#    shared by more than one row, covering 45 rows in total."
#
# The old wording said "so 30 rows share an id with another row". 30 is the
# SURPLUS (43,126 - 43,096), not the number of rows that share. It is forbidden
# below.
DUPLICATION_CLAIM_RE = (
    r"([\d,]+)\s+distinct\s+`argus_record_id`\s+values\s+across\s+([\d,]+)\s+rows:\s*"
    r"([\d,]+)\s+ids\s+are\s+shared\s+by\s+more\s+than\s+one\s+row,\s*"
    r"covering\s+([\d,]+)\s+rows\s+in\s+total"
)

FORBIDDEN_CLAIMS = (
    (
        "forbidden.readme.surplus_described_as_shared_rows",
        r"\b" + str(CSV_DUPLICATE_EXCESS_ROWS) + r"\s+rows\s+share\s+an\s+id",
        f"{CSV_DUPLICATE_EXCESS_ROWS} is the SURPLUS "
        f"({CSV_ROW_COUNT:,} rows - {CSV_DISTINCT_RECORD_IDS:,} distinct ids), NOT the "
        f"number of rows that share an id. {CSV_ROWS_WITH_SHARED_ID} rows carry one of "
        f"the {CSV_SHARED_RECORD_IDS} shared ids. This false conflation shipped into "
        "four documents; it must not come back.",
    ),
    (
        "forbidden.readme.severity_field",
        r"carries\s+a\s+`severity`\s+field",
        "no record in any feed has a `severity` key. The column exists in the DB "
        "schema (migration 0031) but is NOT emitted into any export.",
    ),
    (
        "forbidden.readme.universal_url_citation",
        r"traces\s+back\s+to\s+at\s+least\s+one\s+of\s+these\s+public\s+sources,\s+"
        r"with\s+a\s+direct\s+URL\s+citation",
        "865 rows carry a non-URL provenance token instead of a fetchable URL, so "
        "'every row has a direct URL citation' is false.",
    ),
)

STATIC_CLAIM_IDS = (
    "readme.active_identifiers.table",
    "readme.active_identifiers.prose",
    "readme.behavioral_signatures",
    "readme.hc_feed.key_set",
    "readme.hc_feed.no_severity_or_confidence",
    "readme.url_provenance.public_rows",
    "readme.url_provenance.non_public_rows",
    "readme.url_provenance.non_public_rows_restated",
    "readme.url_provenance.all_non_public_are_manufacturer_app",
    "readme.url_provenance.manufacturer_app_http_rows",
    "readme.record_id.pattern_key_not_row_id",
    "readme.record_id.hash_format",
    "readme.record_id.multiplicity",
    "readme.confidence.scale",
    "readme.confidence.blank_rows",
    "readme.confidence.explicit_zero_rows",
    "readme.confidence.blank_rows_are_url_cited",
    "readme.quickstart_mac",
)


def build_registry() -> dict[str, str]:
    """Every claim this job promises to evaluate, declared before it runs."""
    reg: dict[str, str] = {}
    for fname in FEED_CLAIM_SPECS:
        reg[f"readme.feed_count[{fname}]"] = REQUIRED
    for label, _col, patterns in ENUM_CLAIM_SPECS:
        for i in range(len(patterns)):
            reg[f"readme.enum[{label}][{i}]"] = REQUIRED
        reg[f"data.enum_subset[{label}]"] = DERIVED
    for scheme in NON_PUBLIC_URL_SCHEMES:
        reg[f"readme.url_provenance.scheme_prose[{scheme}]"] = REQUIRED
        reg[f"readme.url_provenance.scheme_table[{scheme}]"] = REQUIRED
    for cid in STATIC_CLAIM_IDS:
        reg[cid] = REQUIRED
    for cid, _pat, _why in FORBIDDEN_CLAIMS:
        reg[cid] = FORBIDDEN
    for label, _rp, _cp, _q in DB_ONLY_SPECS:
        reg[f"dbonly[{label}]"] = DOC_ONLY
    return reg


CLAIM_REGISTRY = build_registry()


@dataclass
class Claim:
    name: str
    claimed: str
    measured: str
    verdict: str
    source: str = ""
    note: str = ""


def _int(text: str | None) -> int | None:
    if text is None:
        return None
    try:
        return int(text.replace(",", "").strip())
    except ValueError:
        return None


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


class ClaimSet:
    """Collects findings and enforces that every registered claim produced one."""

    def __init__(self, registry: dict[str, str]):
        self.registry = registry
        self.items: list[Claim] = []
        self._seen: set[str] = set()

    def add(self, cid, claimed, measured, verdict, source="", note=""):
        if cid not in self.registry:
            raise KeyError(
                f"claim id {cid!r} is not in CLAIM_REGISTRY; register it so the "
                "coverage guard can tell whether it ran"
            )
        self._seen.add(cid)
        self.items.append(
            Claim(cid, str(claimed), str(measured), verdict, source, note)
        )

    def require(self, cid, pattern, text, source_name, wording=""):
        """Find a claim the doc MUST make. A miss is a FAIL, never a skip."""
        m = re.search(pattern, text)
        if m is None:
            self.add(
                cid, "(claim not found)", "not measured", FAIL, source_name,
                "the expected claim is absent from this document -- it was "
                "reworded, moved or deleted, and its check went blind. This is a "
                "FAIL by design: a gate a rewrite can silently disarm is not a "
                "gate. Restore the claim, or update the pattern deliberately."
                + (f" Expected wording: {wording}" if wording else "")
                + f" [pattern: {pattern}]",
            )
        return m

    def forbid(self, cid, pattern, text, source_name, why):
        """Assert a known-false wording has NOT come back."""
        m = re.search(pattern, text)
        if m is None:
            self.add(cid, "absent", "absent", PASS, source_name,
                     "known-false wording is absent, as required")
        else:
            self.add(
                cid, "absent", f"PRESENT at line {_line_of(text, m.start())}",
                FAIL, f"{source_name}:{_line_of(text, m.start())}",
                f"a known-false claim has reappeared: {why} Matched text: "
                f"{m.group(0)[:90]!r}",
            )

    def unrun(self) -> list[str]:
        return sorted(set(self.registry) - self._seen)


# ---------------------------------------------------------------------------
# The enum claims: parse the LAST migration that defines each CHECK constraint.
#
# Do NOT hardcode migration 0033. Later migrations reference these columns in
# WHERE clauses, and a future one could genuinely widen the enum; pinning a
# filename would go stale silently. We take the highest-numbered migration that
# contains a COLUMN DEFINITION form -- `col TEXT ... CHECK (col IN (...))` --
# which is what actually constrains the table.
# ---------------------------------------------------------------------------


def enum_from_migrations(column: str, migrations: Path = MIGRATIONS):
    pattern = re.compile(
        column + r"\s+TEXT[^,]*?CHECK\s*\(\s*" + column + r"\s+IN\s*\((.*?)\)\s*\)",
        re.DOTALL,
    )
    latest: tuple[list[str], str] | None = None
    for path in sorted(glob.glob(str(migrations / "*.sql"))):
        try:
            body = Path(path).read_text(encoding="utf-8")
        except OSError:
            continue
        for match in pattern.finditer(body):
            values = re.findall(r"'([^']*)'", match.group(1))
            if values:
                latest = (sorted(set(values)), os.path.basename(path))
    return latest


def check_claims(
    readme_path: Path = README,
    changelog_path: Path = CHANGELOG,
    paths: ExportPaths | None = None,
    migrations: Path = MIGRATIONS,
    strict_consistency: bool = False,
) -> list[Claim]:
    paths = DEFAULT_EXPORT_PATHS if paths is None else paths
    readme = readme_path.read_text(encoding="utf-8")
    rn = readme_path.name
    cs = ClaimSet(CLAIM_REGISTRY)

    def src(m) -> str:
        return f"{rn}:{_line_of(readme, m.start())}"

    # ---- measured inputs -------------------------------------------------
    _fields, rows = read_csv_rows(paths.csv)
    csv_rows = len(rows)
    _m_std, std_entries = read_feed(paths.standard)
    _m_hc, hc_entries = read_feed(paths.high_conf)
    beh_meta, beh_entries = read_feed(paths.behavioral)

    # ---- 1. export record counts, from the "How to use the exports" list --
    feed_entries = {
        "argus_export_high_confidence.json": hc_entries,
        "argus_export.json": std_entries,
        "argus_export.csv": None,
        "argus_export_behavioral_signatures.json": beh_entries,
    }
    for fname in FEED_CLAIM_SPECS:
        entries = feed_entries[fname]
        measured = csv_rows if entries is None else len(entries)
        cid = f"readme.feed_count[{fname}]"
        m = cs.require(
            cid,
            r"`exports/" + re.escape(fname) + r"`\*{0,2}\s*\(([\d,]+)\s+records\)",
            readme, rn, f"`exports/{fname}` ({measured:,} records)",
        )
        if m:
            claimed = _int(m.group(1))
            cs.add(cid, f"{claimed:,}", f"{measured:,}",
                   PASS if claimed == measured else FAIL, src(m))

    # ---- 2. "At a glance" table + prose bullets ---------------------------
    m = cs.require("readme.active_identifiers.table",
                   r"Active identifiers\s*\|\s*\*\*([\d,]+)\*\*", readme, rn)
    if m:
        claimed = _int(m.group(1))
        cs.add("readme.active_identifiers.table", f"{claimed:,}", f"{csv_rows:,}",
               PASS if claimed == csv_rows else FAIL, src(m),
               "measured as CSV data rows")

    m = cs.require("readme.active_identifiers.prose",
                   r"\*\*([\d,]+)\s+active canonical identifiers\*\*", readme, rn)
    if m:
        claimed = _int(m.group(1))
        cs.add("readme.active_identifiers.prose", f"{claimed:,}", f"{csv_rows:,}",
               PASS if claimed == csv_rows else FAIL, src(m))

    # ---- 3. enum-backed claims -------------------------------------------
    for label, column, patterns in ENUM_CLAIM_SPECS:
        parsed = enum_from_migrations(column, migrations)
        if parsed is None:
            for i in range(len(patterns)):
                cs.add(f"readme.enum[{label}][{i}]", "(various)",
                       "cannot parse CHECK enum", UNVERIFIABLE, str(migrations),
                       f"no migration defines a CHECK constraint on {column}")
            cs.add(f"data.enum_subset[{label}]", "(various)",
                   "cannot parse CHECK enum", UNVERIFIABLE, str(migrations),
                   f"no migration defines a CHECK constraint on {column}")
            continue
        values, src_file = parsed
        for i, pattern in enumerate(patterns):
            cid = f"readme.enum[{label}][{i}]"
            m = cs.require(cid, pattern, readme, rn, f"the {label} count")
            if m:
                claimed = _int(m.group(1))
                cs.add(cid, claimed, len(values),
                       PASS if claimed == len(values) else FAIL, src(m),
                       f"enum parsed from db/migrations/{src_file}; NOT "
                       "COUNT(DISTINCT) over the CSV, which under-reports "
                       "declared-but-unused values")
        # Cross-check: everything in use must be inside the declared enum.
        in_use = {(r.get(column) or "").strip() for r in rows}
        in_use.discard("")
        stray = sorted(in_use - set(values))
        cs.add(f"data.enum_subset[{label}]", "0 values outside the enum",
               f"{len(stray)} outside", PASS if not stray else FAIL,
               f"db/migrations/{src_file}",
               f"stray={stray[:5]}" if stray else
               f"{len(in_use)} in use of {len(values)} declared")

    # ---- 4. behavioral signature population ------------------------------
    m = cs.require("readme.behavioral_signatures",
                   r"\*\*(\d+)\s+behavioral signatures\*\*"
                   r"|Behavioral signatures\s*\|\s*\*\*([\d,]+)\*\*", readme, rn)
    if m:
        claimed = _int(m.group(1) or m.group(2))
        measured = beh_meta.get("source_record_count")
        cs.add("readme.behavioral_signatures", claimed, measured,
               PASS if claimed == measured else FAIL, src(m),
               "WEAK: matched against _meta.source_record_count, the emitting "
               "run's own self-report, not an independent count of the population")

    # ---- 5. STRUCTURAL: the high-confidence feed's record shape ----------
    m = cs.require(
        "readme.hc_feed.key_set",
        r"Every\s+record\s+carries\s+exactly\s+(\w+)\s+keys:\s*((?:`[a-z_]+`[,\s]*)+)",
        readme, rn,
        "Every record carries exactly four keys: `argus_record_id`, "
        "`description`, `pattern`, `pattern_type`.",
    )
    if m:
        word = m.group(1).lower()
        claimed_n = NUMBER_WORDS.get(word, _int(word))
        claimed_keys = sorted(re.findall(r"`([a-z_]+)`", m.group(2)))
        key_sets = {frozenset(e.keys()) for e in hc_entries}
        measured_keys = sorted(next(iter(key_sets))) if len(key_sets) == 1 else None
        ok = (measured_keys is not None
              and claimed_keys == measured_keys
              and claimed_n == len(measured_keys))
        cs.add("readme.hc_feed.key_set",
               f"{claimed_n} keys {claimed_keys}",
               (f"{len(measured_keys)} keys {measured_keys}" if measured_keys
                else f"{len(key_sets)} DIFFERENT key sets across records"),
               PASS if ok else FAIL, src(m),
               "key names and their count are both extracted from the README and "
               "compared against the emitted records")

    m = cs.require(
        "readme.hc_feed.no_severity_or_confidence",
        r"There\s+is\s+no\s+severity\s+field\s+and\s+no\s+per-row\s+confidence\s+"
        r"value\s+in\s+this\s+feed",
        readme, rn,
        "There is no severity field and no per-row confidence value in this feed.",
    )
    if m:
        with_sev = sum(1 for e in hc_entries if "severity" in e)
        with_conf = sum(1 for e in hc_entries if "confidence" in e)
        cs.add("readme.hc_feed.no_severity_or_confidence",
               f"0 of {len(hc_entries)} rows carry severity or confidence",
               f"{with_sev} carry severity, {with_conf} carry confidence",
               PASS if with_sev == 0 and with_conf == 0 else FAIL, src(m),
               "the `severity` column exists in the DB schema (migration 0031) "
               "but is NOT emitted into any feed; severity ranking is left to "
               "the operator")

    # ---- 6. STRUCTURAL: provenance -- who really has a URL ---------------
    public = sum(
        1 for r in rows if (r.get("source_url") or "").startswith(PUBLIC_URL_SCHEMES)
    )
    non_public_rows = [
        r for r in rows
        if (r.get("source_url") or "").startswith(NON_PUBLIC_URL_SCHEMES)
    ]
    non_public = len(non_public_rows)

    m = cs.require(
        "readme.url_provenance.public_rows",
        r"([\d,]+)\s+of\s+the\s+([\d,]+)\s+CSV\s+rows\s+cite\s+that\s+source\s+"
        r"with\s+a\s+direct\s+`http\(s\)`\s+URL",
        readme, rn,
        f"{public:,} of the {csv_rows:,} CSV rows cite that source with a "
        "direct `http(s)` URL",
    )
    if m:
        claimed, claimed_total = _int(m.group(1)), _int(m.group(2))
        cs.add("readme.url_provenance.public_rows",
               f"{claimed:,} of {claimed_total:,}", f"{public:,} of {csv_rows:,}",
               PASS if (claimed == public and claimed_total == csv_rows) else FAIL,
               src(m))

    m = cs.require(
        "readme.url_provenance.non_public_rows",
        r"The\s+remaining\s+([\d,]+)\s+cite\s+a\s+non-URL\s+provenance\s+token",
        readme, rn, f"The remaining {non_public} cite a non-URL provenance token",
    )
    if m:
        claimed = _int(m.group(1))
        cs.add("readme.url_provenance.non_public_rows", f"{claimed:,}",
               f"{non_public:,}", PASS if claimed == non_public else FAIL, src(m),
               "these rows have provenance but NOT a direct URL citation")

    m = cs.require(
        "readme.url_provenance.non_public_rows_restated",
        r"([\d,]+)\s+of\s+the\s+([\d,]+)\s+CSV\s+rows\s+carry\s+a\s+provenance\s+"
        r"token\s+in\s+`source_url`\s+instead\s+of\s+a\s+fetchable\s+URL",
        readme, rn,
        "the Provenance discipline section's restatement of the same two numbers",
    )
    if m:
        claimed, claimed_total = _int(m.group(1)), _int(m.group(2))
        cs.add("readme.url_provenance.non_public_rows_restated",
               f"{claimed:,} of {claimed_total:,}",
               f"{non_public:,} of {csv_rows:,}",
               PASS if (claimed == non_public and claimed_total == csv_rows)
               else FAIL, src(m),
               "the same pair of numbers is stated twice in the README; both "
               "sites are gated so one cannot be corrected without the other")

    m = cs.require(
        "readme.url_provenance.all_non_public_are_manufacturer_app",
        r"All\s+([\d,]+)\s+are\s+`source_type='manufacturer_app'`\s+rows",
        readme, rn,
        f"All {non_public} are `source_type='manufacturer_app'` rows",
    )
    if m:
        claimed = _int(m.group(1))
        strays = [r for r in non_public_rows
                  if (r.get("source_type") or "").strip() != "manufacturer_app"]
        cs.add("readme.url_provenance.all_non_public_are_manufacturer_app",
               f"all {claimed:,} are manufacturer_app",
               f"{non_public - len(strays):,} of {non_public:,} are "
               f"manufacturer_app",
               PASS if (claimed == non_public and not strays) else FAIL, src(m),
               f"stray source_types={sorted({(r.get('source_type') or '') for r in strays})[:5]}"
               if strays else "every non-URL row is a manufacturer_app row")

    m = cs.require(
        "readme.url_provenance.manufacturer_app_http_rows",
        r"([\d,]+)\s+of\s+the\s+([\d,]+)\s+`manufacturer_app`\s+rows\s+do\s+carry\s+"
        r"an\s+`http\(s\)`\s+URL",
        readme, rn,
        "N of the M `manufacturer_app` rows do carry an `http(s)` URL",
    )
    if m:
        claimed, claimed_total = _int(m.group(1)), _int(m.group(2))
        mfg = [r for r in rows
               if (r.get("source_type") or "").strip() == "manufacturer_app"]
        mfg_http = sum(
            1 for r in mfg if (r.get("source_url") or "").startswith(PUBLIC_URL_SCHEMES)
        )
        cs.add("readme.url_provenance.manufacturer_app_http_rows",
               f"{claimed:,} of {claimed_total:,}", f"{mfg_http:,} of {len(mfg):,}",
               PASS if (claimed == mfg_http and claimed_total == len(mfg)) else FAIL,
               src(m),
               "the prefix is not a proxy for the source band")

    # Per-scheme census, gated at BOTH sites the README states it.
    for scheme in NON_PUBLIC_URL_SCHEMES:
        measured = sum(
            1 for r in rows if (r.get("source_url") or "").startswith(scheme)
        )
        esc = re.escape(scheme)
        for site, pattern in (
            ("scheme_prose", r"`" + esc + r"`\s*\(([\d,]+)(?:\s+rows)?\)"),
            ("scheme_table", r"\|\s*`" + esc + r"`\s*\|\s*([\d,]+)\s*\|"),
        ):
            cid = f"readme.url_provenance.{site}[{scheme}]"
            m = cs.require(cid, pattern, readme, rn,
                           f"the {site.replace('_', ' ')} count for `{scheme}`")
            if m:
                claimed = _int(m.group(1))
                cs.add(cid, claimed, measured,
                       PASS if claimed == measured else FAIL, src(m))

    # ---- 7. STRUCTURAL: argus_record_id semantics ------------------------
    ids = [r.get("argus_record_id", "") for r in rows]
    counts = Counter(ids)
    distinct = len(counts)
    shared = {i: n for i, n in counts.items() if n > 1}
    rows_with_shared = sum(shared.values())
    surplus = len(ids) - distinct

    m = cs.require("readme.record_id.pattern_key_not_row_id",
                   r"`argus_record_id`\s+is\s+a\s+pattern\s+key,\s+not\s+a\s+row\s+id",
                   readme, rn,
                   "**`argus_record_id` is a pattern key, not a row id.**")
    if m:
        cs.add("readme.record_id.pattern_key_not_row_id",
               "not row-unique", f"{surplus} surplus rows over {distinct:,} ids",
               PASS if surplus > 0 else FAIL, src(m),
               "if the surplus ever reaches 0 the key HAS become row-unique and "
               "this README sentence would itself be the false claim")

    m = cs.require("readme.record_id.hash_format",
                   r"16-hex-char\s+stable\s+hash", readme, rn,
                   "It is a 16-hex-char stable hash")
    if m:
        malformed = sum(1 for i in ids if not RECORD_ID_RE.match(i))
        cs.add("readme.record_id.hash_format",
               f"all {csv_rows:,} rows match /^[0-9a-f]{{16}}$/",
               f"{csv_rows - malformed:,} match",
               PASS if malformed == 0 else FAIL, src(m))

    # THE corrected claim. The old README said "so 30 rows share an id with
    # another row" -- 30 is the surplus, not the number of sharing rows.
    m = cs.require(
        "readme.record_id.multiplicity", DUPLICATION_CLAIM_RE, readme, rn,
        f"{CSV_DISTINCT_RECORD_IDS:,} distinct `argus_record_id` values across "
        f"{CSV_ROW_COUNT:,} rows: {CSV_SHARED_RECORD_IDS} ids are shared by more "
        f"than one row, covering {CSV_ROWS_WITH_SHARED_ID} rows in total.",
    )
    if m:
        c_distinct = _int(m.group(1))
        c_total = _int(m.group(2))
        c_shared = _int(m.group(3))
        c_covered = _int(m.group(4))
        parts = [
            ("distinct ids", c_distinct, distinct),
            ("total rows", c_total, len(ids)),
            ("shared ids", c_shared, len(shared)),
            ("rows covered", c_covered, rows_with_shared),
        ]
        wrong = [f"{n}: says {c}, measured {mv}" for n, c, mv in parts if c != mv]
        cs.add("readme.record_id.multiplicity",
               f"{c_distinct:,} distinct / {c_total:,} rows / {c_shared} shared "
               f"ids / {c_covered} rows covered",
               f"{distinct:,} distinct / {len(ids):,} rows / {len(shared)} shared "
               f"ids / {rows_with_shared} rows covered",
               PASS if not wrong else FAIL, src(m),
               "; ".join(wrong) if wrong else
               f"all four numbers re-measured; surplus is {surplus} "
               "(rows beyond one-per-id), which is a DIFFERENT number from the "
               f"{rows_with_shared} rows that carry a shared id")

    # ---- 8. confidence ----------------------------------------------------
    m = cs.require("readme.confidence.scale",
                   r"confidence is on a (\d+)-(\d+) scale", readme, rn)
    if m:
        lo_c, hi_c = _int(m.group(1)), _int(m.group(2))
        vals = [
            int((r.get("confidence") or "").strip())
            for r in rows
            if (r.get("confidence") or "").strip().isdigit()
        ]
        lo_m, hi_m = (min(vals), max(vals)) if vals else (None, None)
        ok = vals and lo_m >= lo_c and hi_m <= hi_c
        cs.add("readme.confidence.scale", f"{lo_c}-{hi_c}",
               f"observed {lo_m}-{hi_m}", PASS if ok else FAIL, src(m),
               f"{len(rows) - len(vals)} rows have a blank confidence")

    blank_rows = [r for r in rows if not (r.get("confidence") or "").strip()]
    m = cs.require(
        "readme.confidence.blank_rows",
        r"([\d,]+)\s+of\s+the\s+([\d,]+)\s+CSV\s+rows\s+ship\s+an\s+empty\s+`confidence`",
        readme, rn,
        f"{len(blank_rows)} of the {csv_rows:,} CSV rows ship an empty `confidence`",
    )
    if m:
        claimed, claimed_total = _int(m.group(1)), _int(m.group(2))
        cs.add("readme.confidence.blank_rows",
               f"{claimed:,} of {claimed_total:,}",
               f"{len(blank_rows):,} of {csv_rows:,}",
               PASS if (claimed == len(blank_rows) and claimed_total == csv_rows)
               else FAIL, src(m),
               "blank means UNSCORED; coercing it to 0 or 100 misfiles attributed rows")

    m = cs.require(
        "readme.confidence.explicit_zero_rows",
        r"an\s+explicit\s+`0`,\s+which\s+([\d,]+)\s+rows\s+do\s+carry",
        readme, rn, "a distinct state from an explicit `0`, which N rows do carry",
    )
    if m:
        claimed = _int(m.group(1))
        zeros = sum(1 for r in rows if (r.get("confidence") or "").strip() == "0")
        cs.add("readme.confidence.explicit_zero_rows", f"{claimed:,}", f"{zeros:,}",
               PASS if claimed == zeros else FAIL, src(m),
               "the rows that really are scored 0, which blank rows must not be "
               "merged into")

    m = cs.require(
        "readme.confidence.blank_rows_are_url_cited",
        r"all\s+([\d,]+)\s+carry\s+an\s+`http\(s\)`\s+`source_url`",
        readme, rn, f"all {len(blank_rows)} carry an `http(s)` `source_url`",
    )
    if m:
        claimed = _int(m.group(1))
        blank_http = sum(
            1 for r in blank_rows
            if (r.get("source_url") or "").startswith(PUBLIC_URL_SCHEMES)
        )
        cs.add("readme.confidence.blank_rows_are_url_cited",
               f"all {claimed:,} URL-cited",
               f"{blank_http:,} of {len(blank_rows):,} URL-cited",
               PASS if (claimed == len(blank_rows) and blank_http == len(blank_rows))
               else FAIL, src(m),
               "unscored is not unprovenanced")

    # ---- 9. the quickstart must actually work ----------------------------
    m = cs.require("readme.quickstart_mac",
                   r"argus_cli\.py query ([0-9a-f:]{17})", readme, rn,
                   "a quickstart `argus_cli.py query <MAC>` line")
    if m:
        mac = m.group(1)
        exact = sum(1 for r in rows if (r.get("identifier") or "").strip() == mac)
        cs.add("readme.quickstart_mac", f"{mac} present", f"{exact} exact row(s)",
               PASS if exact >= 1 else FAIL, src(m),
               "an unresolvable quickstart is the first thing a new user hits")

    # ---- 10. wordings that are known to be FALSE and must not return -----
    for cid, pattern, why in FORBIDDEN_CLAIMS:
        cs.forbid(cid, pattern, readme, rn, why)

    # ---- 11. DB-only claims: consistency only, never verification --------
    changelog = (
        changelog_path.read_text(encoding="utf-8") if changelog_path.is_file() else ""
    )
    for label, readme_pat, changelog_pat, query in DB_ONLY_SPECS:
        cid = f"dbonly[{label}]"
        rm = cs.require(cid, readme_pat, readme, rn, f"the {label} count")
        if not rm:
            continue
        claimed = _int(rm.group(1))
        cm = re.search(changelog_pat, changelog)
        if cm is None:
            # --strict-consistency turns "nothing to compare against" into a
            # failure. Without it, an unechoed DB-only number is merely
            # reported; with it, the release is not allowed to ship a number
            # that no second document corroborates.
            cs.add(cid, claimed, "no CHANGELOG echo found",
                   FAIL if strict_consistency else UNVERIFIABLE, src(rm),
                   f"requires `{query}` on db/argus.db, which is NOT distributed; "
                   "no tracked file can settle this"
                   + (" (--strict-consistency: an unechoed DB-only claim is a "
                      "failure)" if strict_consistency else ""))
            continue
        echoed = _int(cm.group(1))
        cs.add(cid, claimed, f"{changelog_path.name} says {echoed}",
               CONSISTENT if claimed == echoed else INCONSISTENT, src(rm),
               f"NOT VERIFIED: this is doc-vs-doc agreement only. Settling it "
               f"needs `{query}` on the undistributed db/argus.db.")

    # ---- 12. the coverage guard: did every declared claim actually run? --
    for cid in cs.unrun():
        cs.items.append(Claim(
            cid, "(registered)", "CHECK DID NOT RUN", FAIL, "check_doc_claims.py",
            "this claim is declared in CLAIM_REGISTRY but produced no finding. "
            "Its check block was deleted, skipped or short-circuited. A contract "
            "that silently shrinks is the failure mode this job exists to catch.",
        ))

    return cs.items


def render(claims: list[Claim]) -> None:
    if not claims:
        print("(no claims evaluated)")
        return
    w_n = max([len(c.name) for c in claims] + [5])
    w_c = min(max([len(c.claimed) for c in claims] + [7]), 32)
    w_m = min(max([len(c.measured) for c in claims] + [8]), 44)

    def t(s, w):
        return s if len(s) <= w else s[: w - 1] + "…"

    print(f"{'CLAIM'.ljust(w_n)}  {'CLAIMED'.ljust(w_c)}  "
          f"{'MEASURED'.ljust(w_m)}  VERDICT")
    print("-" * (w_n + w_c + w_m + 18))
    for c in claims:
        print(f"{c.name.ljust(w_n)}  {t(c.claimed, w_c).ljust(w_c)}  "
              f"{t(c.measured, w_m).ljust(w_m)}  {c.verdict}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-consistency",
        action="store_true",
        help="also fail when a DB-only claim has no CHANGELOG echo to compare against",
    )
    parser.add_argument("--readme", type=Path, default=README, metavar="PATH",
                        help="README to validate (default: README.md)")
    parser.add_argument("--changelog", type=Path, default=CHANGELOG, metavar="PATH",
                        help="CHANGELOG for doc-vs-doc echoes (default: CHANGELOG.md)")
    parser.add_argument("--exports", type=Path, default=EXPORTS_DIR, metavar="DIR",
                        help="directory holding the export artifacts (default: exports/)")
    parser.add_argument("--migrations", type=Path, default=MIGRATIONS, metavar="DIR",
                        help="migrations directory for CHECK enums (default: db/migrations)")
    args = parser.parse_args(argv)

    paths = ExportPaths.for_dir(args.exports)

    for path in [args.readme] + paths.all_paths():
        if not path.is_file():
            print(f"check_doc_claims: FAIL — missing {path}", file=sys.stderr)
            return 2

    try:
        claims = check_claims(
            readme_path=args.readme,
            changelog_path=args.changelog,
            paths=paths,
            migrations=args.migrations,
            strict_consistency=args.strict_consistency,
        )
    except (ValueError, OSError) as exc:
        print(f"check_doc_claims: FAIL — unreadable input: {exc}", file=sys.stderr)
        return 2

    render(claims)

    measured = [c for c in claims if c.verdict in MEASURED_VERDICTS]
    failures = [c for c in claims if c.verdict in BAD_VERDICTS]
    unverifiable = [c for c in claims if c.verdict == UNVERIFIABLE]
    consistency = [c for c in claims if c.verdict in {CONSISTENT, INCONSISTENT}]

    print()
    print(
        f"check_doc_claims: {sum(1 for c in measured if c.verdict == PASS)} PASS, "
        f"{sum(1 for c in measured if c.verdict == FAIL)} FAIL "
        f"(of {len(measured)} independently measured claims); "
        f"{len(consistency)} doc-vs-doc consistency, "
        f"{len(unverifiable)} unverifiable from the public tree; "
        f"{len(CLAIM_REGISTRY)} claims registered"
    )

    if consistency:
        print()
        print("NOT VERIFICATION — these are doc-vs-doc checks only. The numbers need")
        print("the canonical DB (db/argus.db), which this repo does not distribute:")
        for c in consistency:
            print(f"  [{c.verdict}] {c.name}: README {c.claimed} vs {c.measured}")

    if unverifiable:
        print()
        print("UNVERIFIABLE from tracked files:")
        for c in unverifiable:
            print(f"  {c.name}: {c.note}")

    if failures:
        print()
        print("FALSE OR MISSING CLAIMS — the doc and the shipped files disagree:")
        for c in failures:
            print(f"\n  {c.name}")
            print(f"    site:     {c.source}")
            print(f"    claimed:  {c.claimed}")
            print(f"    measured: {c.measured}")
            if c.note:
                print(f"    why:      {c.note}")
        print()
        print(f"check_doc_claims: {len(failures)} claim(s) need correcting.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
