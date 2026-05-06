"""FCC grantee-prefix allowlist (Ratification 1, MAC-23 close).

Surface: cross-reference `fcc_id_anchored` regex hits against the Phase-3
`fcc_grantees` lexicon (50,153 rows in argus.db at schema_version=6). Only
count a hit when the matched grantee-prefix exists in `fcc_grantees`.

Plus stop-list of patterns that masquerade as the FCC-ID shape:
    \\bCVE-\\d{4}-\\d{4,7}\\b   (CVE security-advisory IDs)
    \\bCWE-\\d{1,4}\\b           (CWE weakness IDs)
    NIST NVD pattern             (e.g., NVD-2025-…)

Wave-A Step-1.5b survey surfaced 2 fcc_id_unique FP hits (`CVE-2025`,
`NON-INFRINGEMENT`) — the stop-list catches CVE; the allowlist catches
`NON-INFRINGEMENT` (since `NON` is not a real grantee prefix).

Phase-5 reuse: any future regex pass that produces a `fcc_id_anchored`
candidate MUST flow through `validate_fcc_id_match()` before staging.

§7.3 / §11 #1: a regex hit is a candidate, NOT an extracted record. The
allowlist gate is the line between "candidate" and "stageable hit".
"""
from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Iterable

DB_PATH_DEFAULT = Path("/home/kev/argus/db/argus.db")

# FCC-ID shape per Wave-A tightened regex (MAC-21 §9.11): mandatory hyphen,
# grantee prefix + 4-14-char product code. We re-parse the matched string
# to extract the grantee prefix.
#
# Grantee prefix length per §1.6.7 of FCC OET KDB ruleset:
#   - 3 chars (legacy applicants, `[A-Z]{3}`-shape — A-Z only)
#   - 5 chars (post-2013 applicants, `2[A-Z0-9]{4}`-shape — first char `2`)
# Verified against argus.db `fcc_grantees` (50,153 rows, schema_version=6):
#   first-char distribution = 21,396 rows start with `2` + 28,757 rows start
#   with `A-Z`; no codes start with `0`/`1`/`3-9`. Length distribution =
#   28,757 rows length=3 + 21,396 rows length=5; no length-4 codes.
# Regex keeps prefix permissive ([A-Z0-9]{3} or {5}); allowlist gate
# drops anything not actually present.
FCC_ID_RE = re.compile(r"^([A-Z0-9]{3}|[A-Z0-9]{5})-([A-Z0-9]{4,14})$")

# Stop-list: shapes that pass FCC_ID_RE but are categorically other things.
STOP_LIST_PATTERNS = (
    re.compile(r"^CVE-\d{4}$"),               # truncated CVE
    re.compile(r"^CVE-\d{4}-\d{4,7}$"),       # full CVE
    re.compile(r"^CWE-\d{1,4}$"),             # CWE
    re.compile(r"^NVD-\d{4}-\d+$"),           # NIST NVD
    re.compile(r"^NIST-\d+$"),                # generic NIST
    re.compile(r"^IEEE-\d+$"),                # IEEE standards
    re.compile(r"^RFC-\d+$"),                 # RFC ID
    re.compile(r"^ISO-\d+$"),                 # ISO standard
    re.compile(r"^SP-\d+$"),                  # NIST SP
    re.compile(r"^FIPS-\d+$"),                # FIPS
)


def _is_stop_listed(matched_id: str) -> tuple[bool, str]:
    upper = matched_id.upper()
    for pat in STOP_LIST_PATTERNS:
        if pat.match(upper):
            return True, f"stop_list:{pat.pattern}"
    # Generic English-compound stop-list: if the part after the hyphen is
    # an English word (not a typical SKU shape), reject.
    m = FCC_ID_RE.match(upper)
    if m:
        post = m.group(2)
        # SKUs typically have at least one digit; pure-alpha post-hyphen
        # is almost always a compound English phrase (e.g.
        # "NON-INFRINGEMENT", "OPT-OUT", "PRE-RELEASE").
        if post.isalpha():
            return True, "stop_list:pure_alpha_post_hyphen"
    return False, ""


@lru_cache(maxsize=1)
def _grantee_prefix_set(db_path: str) -> frozenset[str]:
    """Load the unique grantee_code set from argus.db (cached)."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT grantee_code FROM fcc_grantees")
        return frozenset(
            row[0].upper() for row in cur.fetchall() if row[0]
        )
    finally:
        conn.close()


def grantee_prefixes(db_path: Path = DB_PATH_DEFAULT) -> frozenset[str]:
    """Public accessor. Returns the cached frozenset."""
    return _grantee_prefix_set(str(db_path))


def validate_fcc_id_match(
    matched_id: str,
    *,
    db_path: Path = DB_PATH_DEFAULT,
) -> tuple[bool, str]:
    """Return (is_valid, reason).

    is_valid=True  → matched_id passed both the stop-list AND the
                     fcc_grantees allowlist; safe to stage as a candidate.
    is_valid=False → reject. `reason` names the rule that fired.
    """
    if not matched_id:
        return False, "empty"
    upper = matched_id.upper()
    stopped, why = _is_stop_listed(upper)
    if stopped:
        return False, why
    m = FCC_ID_RE.match(upper)
    if not m:
        return False, "shape_mismatch"
    prefix = m.group(1)
    allowlist = _grantee_prefix_set(str(db_path))
    if prefix not in allowlist:
        return False, f"prefix_not_in_fcc_grantees:{prefix}"
    return True, f"ok:prefix={prefix}"


def filter_fcc_id_hits(
    hits: Iterable[str],
    *,
    db_path: Path = DB_PATH_DEFAULT,
) -> tuple[list[str], list[tuple[str, str]]]:
    """Bulk-filter helper. Returns (kept, dropped_with_reason)."""
    kept: list[str] = []
    dropped: list[tuple[str, str]] = []
    for h in hits:
        ok, reason = validate_fcc_id_match(h, db_path=db_path)
        if ok:
            kept.append(h)
        else:
            dropped.append((h, reason))
    return kept, dropped


# ─── Smoke tests (run via `python -m db.extraction.fcc_grantees_allowlist`) ─

def _self_test() -> None:
    cases: list[tuple[str, bool, str]] = [
        ("CVE-2025", False, "stop_list"),
        ("CVE-2025-59409", False, "stop_list"),
        ("CWE-89", False, "stop_list"),
        ("NON-INFRINGEMENT", False, "pure_alpha"),
        ("OPT-OUT", False, "pure_alpha"),
        # Real FCC grantees from argus.db (verified by direct query):
        ("2AA22-RX1234", True, "allowlist_hit"),
        ("2AA23-FOOBAR2", True, "allowlist_hit"),
        ("ZZZ-MODELX1", True, "allowlist_hit"),  # ZZZ = XTREME TELECOM (real)
        # Fake but shape-correct prefixes not in fcc_grantees (verified):
        ("0AA00-FAKE12", False, "prefix_not_in_allowlist"),
        ("9ZZ99-FAKE12", False, "prefix_not_in_allowlist"),
        # Malformed:
        ("", False, "empty"),
        ("NOTANID", False, "shape_mismatch"),
    ]
    fails = 0
    for matched, expect_ok, label in cases:
        ok, reason = validate_fcc_id_match(matched)
        status = "PASS" if ok == expect_ok else "FAIL"
        if ok != expect_ok:
            fails += 1
        print(f"{status:4s} {matched!r:25s} expect_ok={expect_ok} got_ok={ok}  ({reason})  [{label}]")
    print(f"--- {len(cases) - fails}/{len(cases)} pass ---")
    raise SystemExit(0 if fails == 0 else 1)


if __name__ == "__main__":
    _self_test()
