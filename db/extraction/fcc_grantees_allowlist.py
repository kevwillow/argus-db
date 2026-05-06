"""FCC grantee-prefix allowlist + SAR-7 disambig predicates.

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

SAR-7 (BIBLE_AMENDMENTS.md, commit `2c41e2b`) bundles three disambig sub-rules
into this module:
    #1  CVE/CWE/NIST stop-list (already implemented `aed1e96`; codified here).
    #2  is_country_jurisdiction_context_fp(vendor, context_text) — vendor-name
        vs. country/jurisdiction-token disambig (DJI vs. Djibouti class).
    #3  is_commercial_model_name_fp(match, context_text) — news/forum-prose
        commercial-model-name FP class (Cradlepoint MBR-1200 in prose, where
        `MBR` is the Esselte Dymo grantee prefix, not a Cradlepoint FCC ID).

Phase-5 reuse: any future regex pass that produces a `fcc_id_anchored`
candidate MUST flow through `validate_fcc_id_match()` before staging. Pass
`context_text` (±50-char window around the match) when the source is
unstructured prose so SAR-7 #3 can fire.

§7.3 / §7.4 / §11 #1: a regex hit is a candidate, NOT an extracted record.
The allowlist gate plus the SAR-7 predicates are the line between
"candidate" and "stageable hit".
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


@lru_cache(maxsize=1024)
def _grantee_name_for_prefix(db_path: str, prefix: str) -> str | None:
    """Return canonical `grantee_name` for `prefix`, or None if absent.

    Used by SAR-7 #3 to compare grantee-of-record against the vendor named
    in the surrounding prose context.
    """
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT grantee_name FROM fcc_grantees WHERE grantee_code = ? LIMIT 1",
            (prefix.upper(),),
        )
        row = cur.fetchone()
        return row[0] if row and row[0] else None
    finally:
        conn.close()


def grantee_name_for_prefix(
    prefix: str, *, db_path: Path = DB_PATH_DEFAULT,
) -> str | None:
    """Public accessor for the grantee_name of a given prefix."""
    return _grantee_name_for_prefix(str(db_path), prefix.upper())


# ─── SAR-7 #2 — country/jurisdiction-context FP for vendor-mention scoring ──

# Canonical 24-vendor lexicon (mirrors `VENDOR_TOKENS` in
# scripts/mac33_step1_5b_survey.py, scripts/mac31_step1_court_foia_fetch.py,
# and prior MAC-7/MAC-8/MAC-11/MAC-21 anchors). Lowercase for case-insensitive
# membership tests. SAR-7 #3 reads from this set; SAR-7 #2 takes the vendor as
# an explicit argument so callers can target a specific vendor token.
CANONICAL_VENDOR_LEXICON: tuple[str, ...] = (
    "flock",
    "flock safety",
    "motorola",
    "motorola apx",
    "motorola solutions",
    "axon",
    "axon body",
    "axon fleet",
    "cradlepoint",
    "sierra wireless",
    "sierra airlink",
    "airlink",
    "hak5",
    "dji",
    "watchguard",
    "reveal",
    "getac",
    "parrot",
    "skydio",
    "brinc",
    "avigilon",
    "genetec",
    "l3harris",
    "l-3 harris",
    "harris corp",
    "harris corporation",
    "cellebrite",
    "clearview",
    "soundthinking",
    "shotspotter",
    "vigilant",
    "droneshield",
    "dedrone",
    "axis communications",
    "magnet forensics",
    "briefcam",
    "rekor",
    "semtech",
    "stingray",
    "kingfish",
    "hailstorm",
    "perceptics",
    "panasonic toughbook",
)

# Country/jurisdiction-context cue templates. {v} expands to the vendor token
# (lowercased + regex-escaped) at predicate-call time. The templates cover:
#   - ISO 3166-1 alpha-3 country code position cues
#   - Court-filing jurisdictional context
#   - FOIA-released document jurisdictional metadata blocks
#
# SAR-7 #2 explicitly notes the `DJI vs. Djibouti` collision motivates the
# rule, but generalizes to any vendor token colliding with a country/jurisdiction
# token. The {v} templating makes the rule vendor-agnostic.
_COUNTRY_JURISDICTION_CUES: tuple[tuple[str, str], ...] = (
    (r"republic\s+of\s+{v}\b", "iso_alpha3_republic_of"),
    (r"\bcountry\s*[:=]\s*{v}\b", "iso_alpha3_country_label"),
    (r"\bcountry\s+code\s*[:=]?\s*{v}\b", "iso_alpha3_country_code_label"),
    (r"\bjurisdiction\s+code\s+{v}\b", "iso_alpha3_jurisdiction_code"),
    (r"\biso[\s-]?3166[^.]{0,40}{v}\b", "iso_3166_metadata_block"),
    (r"\bdistrict\s+of\s+{v}\b", "court_district_of"),
    (r"\bcase\s+venue\s+{v}\b", "court_case_venue"),
    (r"\bcourt\s+of\s+{v}\b", "court_of"),
    (r"\bvenue\s*[:=]\s*{v}\b", "court_venue_label"),
    (r"\bagency\s*[:=]\s*{v}\b", "foia_agency_label"),
    (r"\bnation\s+of\s+{v}\b", "foia_nation_of"),
    # Djibouti spelled-out forms (the SAR-7 #2 seed case): always counts as
    # country/jurisdiction context regardless of which vendor is being tested,
    # since the prose is about the country, not the drone vendor.
    (r"\bdjibouti\b", "djibouti_spelled_out"),
)


def is_country_jurisdiction_context_fp(
    vendor: str, context_text: str,
) -> tuple[bool, str]:
    """SAR-7 #2 — return (is_fp, reason).

    is_fp=True  → the vendor mention sits inside country/jurisdiction prose
                  (e.g. `DJI` near `Republic of Djibouti`); the count should
                  be excluded from vendor-mention density scoring.
    is_fp=False → no country/jurisdiction cue near the vendor; vendor mention
                  is presumed to refer to the §2.1 vendor entity.

    `context_text` is the ±50-char window around the vendor occurrence (or a
    larger window — the predicate matches anywhere in the supplied text). The
    rule generalizes beyond DJI/Djibouti: any vendor token can collide with a
    country/jurisdiction token, and the same cue templates apply.
    """
    if not vendor or not context_text:
        return False, "empty"
    vendor_re = re.escape(vendor.strip().lower())
    ctx_l = context_text.lower()
    for tmpl, tag in _COUNTRY_JURISDICTION_CUES:
        # `{{0,40}}` in the ISO-3166 cue is a literal `{0,40}` after .format().
        pattern = tmpl.replace("{v}", vendor_re)
        if re.search(pattern, ctx_l):
            return True, f"country_jurisdiction_fp:{tag}"
    return False, ""


# ─── SAR-7 #3 — commercial-model-name FP for news/forum-prose FCC-ID hits ───

# Vendor-token aliases for grantee-name vs. context-vendor matching. SAR-7 #3
# item 3 requires comparing `fcc_grantees.grantee_name` against the vendor
# token in the surrounding prose; the grantee_name is rarely a verbatim copy
# (e.g. `Motorola Solutions Inc` vs. context token `motorola`). We normalize
# both sides to lowercase and do substring-style alias matching.
_VENDOR_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    "flock": ("flock",),
    "flock safety": ("flock",),
    "motorola": ("motorola",),
    "motorola apx": ("motorola",),
    "motorola solutions": ("motorola",),
    "axon": ("axon",),
    "axon body": ("axon",),
    "axon fleet": ("axon",),
    "cradlepoint": ("cradlepoint",),
    "sierra wireless": ("sierra wireless", "sierra"),
    "sierra airlink": ("sierra wireless", "sierra", "airlink"),
    "airlink": ("airlink", "sierra"),
    "hak5": ("hak5",),
    "dji": ("dji",),
    "cellebrite": ("cellebrite",),
    # Sibling/defensive coverage from SAR-7 #3:
    "watchguard": ("watchguard",),
    "axis communications": ("axis communications",),
    "panasonic toughbook": ("panasonic",),
}


def _vendor_name_matches_grantee(
    context_vendor: str, grantee_name: str,
) -> bool:
    """SAR-7 #3 item 3 — does the grantee_name correspond to the vendor token?

    Substring match in either direction with alias expansion. Returns True
    when the grantee appears to be the same entity as the prose vendor; False
    when they're different entities (the FP signal).
    """
    if not context_vendor or not grantee_name:
        return False
    cv = context_vendor.lower().strip()
    gn = grantee_name.lower()
    aliases = _VENDOR_NAME_ALIASES.get(cv, (cv,))
    for alias in aliases:
        if alias in gn:
            return True
    return False


def is_commercial_model_name_fp(
    matched_id: str,
    context_text: str,
    *,
    db_path: Path = DB_PATH_DEFAULT,
) -> tuple[bool, str]:
    """SAR-7 #3 — return (is_fp, reason).

    Three conjoined conditions per SAR-7 #3:
      1. ±50-char context contains a vendor token from the canonical 24-vendor
         lexicon.
      2. Post-hyphen segment of the FCC-ID match is 3-4 digits (commercial
         model-name shape; FCC product codes range 4-14 chars and are rarely
         pure-digit 3-4-len).
      3. The matched grantee prefix's `fcc_grantees.grantee_name` does NOT
         match the vendor token in the surrounding context.

    All three must hold for the predicate to fire. The classic case:
      - matched_id: `MBR-1200`
      - context_text: `... Cradlepoint MBR-1200 router ...`
      - Item 1: `cradlepoint` ∈ context ✓
      - Item 2: post-hyphen `1200` is 4 digits ✓
      - Item 3: `MBR` → `Esselte Dymo N V` (label printers), no Cradlepoint
        alias match ✓
      → is_fp=True, reason=`commercial_model_name_fp:...`

    Sibling-vendor coverage: Cradlepoint IBR-N family (`IBR` → ACK
    Technologies), Motorola APX-6000/7000/8000 (`APX` → Morse Electro
    Products / Montgomery Ward), Sierra Wireless GX-/RV-/MG-series, Cisco/
    Juniper router model nomenclature.

    False-negative leaning: a real Cradlepoint FCC filing under a 5-char
    post-2013 grantee prefix (e.g. `2AABC-XYZ12345`) would not match — the
    post-hyphen is 8 chars, fails item 2. A real 3-char Cradlepoint legacy
    grantee filing would pass item 3 (grantee_name aligns with vendor).
    """
    if not matched_id:
        return False, "empty_match"
    if not context_text:
        return False, "empty_context"
    upper = matched_id.upper()
    m = FCC_ID_RE.match(upper)
    if not m:
        return False, "shape_mismatch"
    prefix = m.group(1)
    post = m.group(2)
    # Item 2: post-hyphen is 3-4 digits, pure-numeric.
    if not (3 <= len(post) <= 4 and post.isdigit()):
        return False, "post_hyphen_not_3_4_digits"
    # Item 1: a canonical-lexicon vendor token appears in context. Prefer the
    # longest-matching token so `motorola apx` wins over bare `motorola`,
    # giving more precise alias resolution downstream.
    ctx_l = context_text.lower()
    ctx_vendor: str | None = None
    for v in sorted(CANONICAL_VENDOR_LEXICON, key=len, reverse=True):
        if v in ctx_l:
            ctx_vendor = v
            break
    if ctx_vendor is None:
        return False, "no_canonical_vendor_in_context"
    # Item 3: grantee_name does not match the context vendor.
    grantee_name = grantee_name_for_prefix(prefix, db_path=db_path)
    if grantee_name is None:
        # Prefix not in fcc_grantees — that's a different drop class
        # (handled by the existing allowlist gate). Don't claim a SAR-7 #3
        # FP; let the allowlist do its job.
        return False, "prefix_not_in_fcc_grantees"
    if _vendor_name_matches_grantee(ctx_vendor, grantee_name):
        return False, "grantee_name_matches_context_vendor"
    return True, (
        f"commercial_model_name_fp:context_vendor={ctx_vendor}|"
        f"grantee_name={grantee_name}|prefix={prefix}|post={post}"
    )


def validate_fcc_id_match(
    matched_id: str,
    *,
    context_text: str | None = None,
    db_path: Path = DB_PATH_DEFAULT,
) -> tuple[bool, str]:
    """Return (is_valid, reason).

    is_valid=True  → matched_id passed the stop-list, the SAR-7 #3
                     commercial-model-name FP predicate (when context
                     supplied), AND the fcc_grantees allowlist; safe to
                     stage as a candidate.
    is_valid=False → reject. `reason` names the rule that fired.

    Gate order (cheapest first, per SAR-7 #3 directive):
      1. empty / shape sanity
      2. STOP_LIST_PATTERNS (CVE / CWE / NIST / IEEE / RFC / ISO / FIPS)
      3. SAR-7 #3 commercial-model-name FP (only if `context_text` provided)
      4. fcc_grantees allowlist

    Callers handling unstructured prose (Wave-D court/FOIA, Wave-E news/forum)
    SHOULD pass `context_text`; structured callers (FCC EAS, manufacturer doc)
    can omit it.
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
    if context_text is not None:
        is_fp, fp_reason = is_commercial_model_name_fp(
            upper, context_text, db_path=db_path,
        )
        if is_fp:
            return False, fp_reason
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
    cases: list[tuple[str, bool, str, str | None]] = [
        # SAR-7 #1 — CVE / CWE / NIST stop-list (existing).
        ("CVE-2025", False, "stop_list", None),
        ("CVE-2025-59409", False, "stop_list", None),
        ("CWE-89", False, "stop_list", None),
        ("NVD-2025-12345", False, "stop_list", None),
        ("NON-INFRINGEMENT", False, "pure_alpha", None),
        ("OPT-OUT", False, "pure_alpha", None),
        # Real FCC grantees from argus.db (verified by direct query):
        ("2AA22-RX1234", True, "allowlist_hit", None),
        ("2AA23-FOOBAR2", True, "allowlist_hit", None),
        ("ZZZ-MODELX1", True, "allowlist_hit", None),  # ZZZ = XTREME TELECOM
        # Fake but shape-correct prefixes not in fcc_grantees (verified):
        ("0AA00-FAKE12", False, "prefix_not_in_allowlist", None),
        ("9ZZ99-FAKE12", False, "prefix_not_in_allowlist", None),
        # Malformed:
        ("", False, "empty", None),
        ("NOTANID", False, "shape_mismatch", None),
        # SAR-7 #3 — commercial-model-name FP (context required).
        # Cradlepoint MBR-1200 in news prose: MBR → Esselte Dymo, vendor mismatch.
        ("MBR-1200", False, "sar7_3_cradlepoint_mbr_fp",
         "the cradlepoint mbr-1200 router supports failover"),
        ("MBR-1000", False, "sar7_3_cradlepoint_mbr_fp",
         "we deployed cradlepoint mbr-1000 units in the field"),
        # No vendor in context → SAR-7 #3 doesn't fire; allowlist still passes.
        ("MBR-1200", True, "sar7_3_no_vendor_context",
         "model number 1200 was specified in the spec"),
    ]
    fails = 0
    for matched, expect_ok, label, ctx in cases:
        ok, reason = validate_fcc_id_match(matched, context_text=ctx)
        status = "PASS" if ok == expect_ok else "FAIL"
        if ok != expect_ok:
            fails += 1
        print(
            f"{status:4s} {matched!r:18s} ctx={'yes' if ctx else 'no '}  "
            f"expect_ok={expect_ok} got_ok={ok}  ({reason})  [{label}]"
        )
    # SAR-7 #2 smoke (separate predicate).
    print("--- SAR-7 #2 smoke ---")
    sar7_2_cases: list[tuple[str, str, bool, str]] = [
        ("DJI", "republic of dji declared independence", True,
         "djibouti_iso_alpha3"),
        ("DJI", "case venue dji district court", True, "court_venue"),
        ("DJI", "the dji mavic 3 quadcopter is a popular drone", False,
         "real_vendor_mention"),
        ("DJI", "djibouti national archive document", True,
         "djibouti_spelled_out"),
        ("DJI", "country code: dji", True, "iso_country_code_label"),
        ("MOTOROLA", "motorola apx 6000 radio handset", False,
         "real_motorola_mention"),
    ]
    for vendor, ctx, expect_fp, label in sar7_2_cases:
        is_fp, reason = is_country_jurisdiction_context_fp(vendor, ctx)
        status = "PASS" if is_fp == expect_fp else "FAIL"
        if is_fp != expect_fp:
            fails += 1
        print(
            f"{status:4s} vendor={vendor!r:10s} expect_fp={expect_fp} "
            f"got_fp={is_fp}  ({reason})  [{label}]"
        )
    total = len(cases) + len(sar7_2_cases)
    print(f"--- {total - fails}/{total} pass ---")
    raise SystemExit(0 if fails == 0 else 1)


if __name__ == "__main__":
    _self_test()
