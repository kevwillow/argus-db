"""SAR-8 + SAR-9 — vendor-name disambig predicate.

Codifies BIBLE_AMENDMENTS.md SAR-8 (commit ``811b4de``) and SAR-9
(commit ``fa89dfc``). Provides the shared ``_normalize_vendor`` predicate
plus an allowlist-driven ``vendor_match_disposition`` that:

1. **Rejects prefix-token false-positives** (`Axon Networks Inc.` ≠ Axon
   Enterprise, `Flock Audio Inc.` ≠ Flock Safety, `Harris Adacom Corp` ≠ Harris
   Corp).
2. **Rejects corporate-split FPs** (SAR-9 #1: `Motorola Mobility LLC, a
   Lenovo Company` / `Motorola (Wuhan) Mobility Technologies` ≠ Motorola
   Solutions; SAR-9 #3: `WatchGuard Technologies, Inc.` ≠ WatchGuard Video).
3. **Recovers canonical-name matches** under geographic-prefix variations
   (`SZ DJI TECHNOLOGY CO.,LTD` → `dji`).
4. **Maintains a per-vendor alias allowlist** keyed by canonical §2.1 name
   (SAR-9 §2.1 re-scope: model-line aliases for Motorola Solutions —
   `Motorola APX`, `Motorola V300`, `Motorola V500`, `Motorola Vigilant`).
5. **Routes bare-token candidates to flag_for_review** (SAR-9 #1: bare
   `Motorola` token without further qualifier needs human triage between
   Solutions / Mobility / Lenovo descendants).
6. **Accepts business-radio-shape qualifiers as Solutions** (SAR-9 #1:
   `Motorola - BSG`, `Motorola Inc Business Light Radios`,
   `Motorola, Broadband Solutions Group` accept under positive-evidence
   substring set).
7. **Strips a narrow geographic-prefix set** (`SZ`, `Shenzhen`, `SZ.`,
   `Shenzhen Co.,`) before normalization. US state/city prefixes (`New York
   Axon`) are intentionally NOT stripped — they carry separate legal-entity
   meaning.

A third disposition state — ``flag_for_review`` — surfaces:
- ``GENETEC Corporation`` (SAR-8: early-2000s Tokyo-address OUI registration
  may be distinct from Genetec Inc., the §2.1 alpr vendor).
- Bare ``Motorola`` token (SAR-9: post-2011 corporate-split ambiguity).

Caller restructure (SAR-9 #2 alias-iteration bug-fix). Callers MUST invoke
``vendor_match_disposition(candidate, canonical_name)`` once per canonical
entry (not once per alias-string), then test alias-string lookups via
``alias_equality(candidate, alias)``. The prior alias-keyed iteration caused
``VENDOR_FP_LIST.get('Harris Corporation')`` to return ``[]`` so the
``harris adacom`` substring check never fired. The restructured caller
fires the FP check on canonical_name once and resolves alias-strings via
exact-normalized equality.

Authority chain:
- BIBLE_AMENDMENTS.md SAR-8 (commit ``811b4de``).
- BIBLE_AMENDMENTS.md SAR-9 (commit ``fa89dfc``).
- Bible §2.1 canonical-vendor list (SAR-9 re-scopes Motorola Solutions
  aliases column to drop bare `Motorola`; migration 0007 mirrors).
- Bible §7.3 Extraction Worker contract.
- Bible §7.4 Validator contract.
- MAC-39 halt-flag #1 surface 2026-05-06; MAC-1 board ratification
  ``613ec532`` 2026-05-06T17:08:16Z.
- MAC-41 halt-flag #1/#2/#3 surface 2026-05-06; MAC-1 board ratification
  ``234faaa7`` 2026-05-06T18:05:53Z (SAR-9 codification).
"""

from __future__ import annotations

import re
from typing import Final


# ---------------------------------------------------------------------------
# Vendor-name normalization (moved from phase3_inference_candidates.py).
# Order matters within ``_VENDOR_SUFFIX_STRIPS`` — longest variants first.
# ---------------------------------------------------------------------------

_VENDOR_SUFFIX_STRIPS: Final[tuple[str, ...]] = (
    ", inc.", ", inc", " inc.", " inc",
    ", ltd.", ", ltd", " ltd.", " ltd",
    ", llc", " llc",
    ", ulc", " ulc",
    " corporation", " corp.", " corp",
    " co.,ltd", " co., ltd", " co.,ltd.", " co., ltd.",
    " co.,ltd.", " co.ltd.", " co. ltd",
    " co., limited", ", limited", " limited",
    " technologies", " technology",
    " sa", " ag", " ab", " gmbh", " bv", " plc", " spa",
    ", s.a.", " s.a.",
    ", inc", " holdings",
)


def _normalize_vendor(name: str) -> str:
    """Strip corporate suffixes + collapse punctuation/whitespace.

    Returns lowercase, suffix-stripped, whitespace-collapsed string. Idempotent
    (running twice on the same input yields identical output). Empty / None
    input returns empty string.
    """
    if not name:
        return ""
    s = name.lower().strip()
    changed = True
    while changed:
        changed = False
        for suf in _VENDOR_SUFFIX_STRIPS:
            if s.endswith(suf):
                s = s[: -len(suf)].rstrip(" ,.;:")
                changed = True
                break
    s = re.sub(r"[,;:.]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Geographic-prefix list — narrow, leading-token-only.
# Sorted longest-first at use-time so that ``Shenzhen Co.,`` strips before
# ``Shenzhen`` strips.
# ---------------------------------------------------------------------------

GEOGRAPHIC_PREFIX_LIST: Final[tuple[str, ...]] = (
    "Shenzhen Co.,",
    "Shenzhen",
    "SZ.",
    "SZ",
)


def _strip_geographic_prefix(name: str) -> str:
    """Strip a leading geographic-prefix token if present.

    Only strips entries from ``GEOGRAPHIC_PREFIX_LIST`` when the prefix is
    followed by whitespace (token boundary). US state/city prefixes (`New York
    Axon`) are NOT stripped — they're not in the list by design. Idempotent.
    """
    if not name:
        return name or ""
    s = name.strip()
    s_lower = s.lower()
    for prefix in sorted(GEOGRAPHIC_PREFIX_LIST, key=len, reverse=True):
        plower = prefix.lower()
        if s_lower.startswith(plower + " "):
            return s[len(prefix) :].strip()
    return s


# ---------------------------------------------------------------------------
# VENDOR_FP_LIST — the 12 strict-path FP cases enumerated in SAR-8.
#
# Structure: dict[canonical_vendor, list[FpEntry]] where FpEntry is:
#   {"substring": str, "flag_for_review": bool (default False), "note": str}
#
# Substring is matched (lowercased, case-insensitive) against the lowercased
# raw candidate string. Match → reject (or flag_for_review when set).
# ---------------------------------------------------------------------------

VENDOR_FP_LIST: Final[dict[str, list[dict[str, object]]]] = {
    "Axon": [
        {
            "substring": "axon networks",
            "flag_for_review": False,
            "note": (
                "Axon Networks Inc. (network gear) is distinct from Axon "
                "Enterprise (TASER International legacy / body-cam vendor)."
            ),
        },
    ],
    "Flock Safety": [
        {
            "substring": "flock audio",
            "flag_for_review": False,
            "note": (
                "Flock Audio Inc. (Canadian audio equipment) is distinct from "
                "Flock Safety (§2.1 alpr vendor)."
            ),
        },
    ],
    "Harris": [
        {
            "substring": "harris adacom",
            "flag_for_review": False,
            "note": (
                "HARRIS ADACOM CORPORATION (1990s networking-products vendor) "
                "is distinct from Harris Corporation (§2.1 imsi_catcher vendor)."
            ),
        },
    ],
    "Genetec": [
        {
            "substring": "genetec corporation",
            "flag_for_review": True,
            "note": (
                "GENETEC Corporation (early-2000s OUI registration, address "
                "Tokyo) may be a separate Japanese entity from Genetec Inc. "
                "(Montreal, the §2.1 alpr vendor). OUI 00:0a:b1 predates "
                "Genetec Inc.'s typical FCC/IEEE-registration era. Human "
                "review required before accept/reject."
            ),
        },
    ],
    "Motorola Solutions": [
        {
            "substring": "mobility",
            "flag_for_review": False,
            "note": (
                "SAR-9 #1 — `Motorola Mobility LLC, a Lenovo Company` and the "
                "Wuhan Mobility subsidiary are post-2011 consumer-smartphone "
                "entity (Lenovo descendant), distinct from Motorola Solutions "
                "(police radios, the §2.1 imsi_catcher / police_radio vendor)."
            ),
        },
        {
            "substring": "(wuhan)",
            "flag_for_review": False,
            "note": (
                "SAR-9 #1 — Wuhan-subsidiary spelling variant. Same Mobility/"
                "Lenovo lineage; distinct from Motorola Solutions."
            ),
        },
        {
            "substring": "lenovo",
            "flag_for_review": False,
            "note": (
                "SAR-9 #1 — explicit Lenovo lineage. Mobility/Lenovo descendant; "
                "distinct from Motorola Solutions."
            ),
        },
    ],
    "WatchGuard": [
        {
            "substring": "watchguard technologies",
            "flag_for_review": False,
            "note": (
                "SAR-9 #3 — WatchGuard Technologies, Inc. is a network firewall "
                "vendor; the §2.1 'WatchGuard' canonical refers to WatchGuard "
                "Video (police body-cam vendor). Distinct corporate entities. "
                "Future-Wave caveat (recorded in SAR-9 entry): if surveillance/"
                "police-adjacency surfaces a firewall deployment, the codification "
                "needs amendment."
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# VENDOR_ALIAS_ALLOWLIST — explicit per-vendor alias variants that the
# predicate accepts as canonical-vendor matches.
#
# Structure: dict[canonical_vendor, list[alias_string]]. Aliases are matched
# case-insensitively after geographic-prefix-strip + ``_normalize_vendor``.
# ---------------------------------------------------------------------------

VENDOR_ALIAS_ALLOWLIST: Final[dict[str, list[str]]] = {
    "DJI": [
        "SZ DJI TECHNOLOGY CO.,LTD",
        "Sz Dji Technology Co.,Ltd",
        "Shenzhen DJI Technology Co.,Ltd",
        "DJI Technology Co.,Ltd",
        "Da-Jiang Innovations Science and Technology Co., Ltd",
    ],
    "Cellebrite": [
        "CelleBrite Mobile Synchronization",
        "Cellebrite Mobile Synchronization Ltd.",
    ],
    # SAR-9 #2 — Motorola Solutions model-line aliases (bare `Motorola` dropped
    # per amendment-log directive; routed to flag_for_review via
    # VENDOR_BARE_TOKEN_FLAG below). Also mirrored in §2.1 lexicon
    # (manufacturers.aliases) by migration 0007.
    "Motorola Solutions": [
        "Motorola APX",
        "Motorola V300",
        "Motorola V500",
        "Motorola Vigilant",
    ],
}


# ---------------------------------------------------------------------------
# VENDOR_BARE_TOKEN_FLAG — per-canonical bare-token → flag_for_review.
#
# When the candidate normalizes to exactly the per-canonical bare token
# (no further qualifier), the disposition is flag_for_review. SAR-9 #1
# codifies this for ``Motorola Solutions`` because bare ``Motorola`` is
# ambiguous post-2011 between Motorola Solutions (Schaumburg / police
# radios / the §2.1 vendor) and Motorola Mobility (Lenovo descendant /
# consumer smartphones).
# ---------------------------------------------------------------------------

VENDOR_BARE_TOKEN_FLAG: Final[dict[str, str]] = {
    "Motorola Solutions": "motorola",
}


# ---------------------------------------------------------------------------
# VENDOR_POSITIVE_EVIDENCE — per-canonical lowercased substrings whose
# presence in the raw candidate string promotes the disposition to ``accept``
# even when the default canonical-prefix match doesn't fire.
#
# SAR-9 #1 codifies this for ``Motorola Solutions``. The "business-radio
# shape" qualifiers (Broadband Solutions Group / Business Light Radios /
# BSG) carry sufficient evidence that the candidate is the §2.1 Motorola
# Solutions vendor (police + business radios) rather than the Motorola
# Mobility / Lenovo descendant (consumer smartphones). Substrings are
# matched case-insensitively against the raw candidate (not the normalized
# form, so dash-delimited `Motorola - BSG` is reachable via ``-bsg`` /
# `` bsg``).
# ---------------------------------------------------------------------------

VENDOR_POSITIVE_EVIDENCE: Final[dict[str, tuple[str, ...]]] = {
    "Motorola Solutions": (
        "broadband solutions",  # `Motorola, Broadband Solutions Group`
        "business light",       # `Motorola Inc Business Light Radios`
        " bsg",                 # `Motorola - BSG` (space-bsg)
        "-bsg",                 # `Motorola-BSG` (dash-bsg)
    ),
}


# ---------------------------------------------------------------------------
# Match disposition predicate.
# ---------------------------------------------------------------------------

_DISPOSITION_ACCEPT: Final[str] = "accept"
_DISPOSITION_REJECT_FP: Final[str] = "reject_fp"
_DISPOSITION_FLAG_REVIEW: Final[str] = "flag_for_review"
_DISPOSITION_NO_MATCH: Final[str] = "no_match"


def vendor_match_disposition(candidate: str, vendor_canonical: str) -> str:
    """Return the SAR-8/SAR-9 disposition for ``candidate`` against ``vendor_canonical``.

    Returns one of:
    - ``"accept"`` — canonical match (exact-normalized, alias-allowlist hit,
      prefix-token match like ``Avigilon Alta`` against ``Avigilon``, or
      SAR-9 positive-evidence substring like ``Motorola - BSG`` against
      ``Motorola Solutions``).
    - ``"reject_fp"`` — the candidate matches a known false-positive substring
      enumerated in ``VENDOR_FP_LIST`` (``Axon Networks Inc.`` against
      ``Axon``; ``Motorola Mobility LLC`` against ``Motorola Solutions``;
      ``WatchGuard Technologies, Inc.`` against ``WatchGuard``; etc.).
    - ``"flag_for_review"`` — the candidate matches an FP entry marked with
      ``flag_for_review=True`` (``GENETEC Corporation`` against ``Genetec``)
      OR the candidate normalizes to a per-canonical bare token (SAR-9 bare
      ``Motorola`` against ``Motorola Solutions``). Caller should route to
      human/CEO triage rather than accepting or rejecting silently.
    - ``"no_match"`` — neither canonical nor FP; the candidate is not a match.
    """
    if not candidate or not vendor_canonical:
        return _DISPOSITION_NO_MATCH

    candidate_lower = candidate.lower().strip()

    # Step 1 — FP rejection on raw lowercased substring (substring match
    # avoids the suffix-strip ambiguity around ``GENETEC Corporation`` →
    # ``genetec`` after suffix-strip).
    for entry in VENDOR_FP_LIST.get(vendor_canonical, []):
        substring = str(entry["substring"]).lower()
        if substring and substring in candidate_lower:
            if bool(entry.get("flag_for_review", False)):
                return _DISPOSITION_FLAG_REVIEW
            return _DISPOSITION_REJECT_FP

    # Step 2 — geographic-prefix strip + normalization for canonical comparison.
    candidate_stripped = _strip_geographic_prefix(candidate)
    candidate_norm = _normalize_vendor(candidate_stripped)
    canonical_norm = _normalize_vendor(vendor_canonical)
    if not candidate_norm or not canonical_norm:
        return _DISPOSITION_NO_MATCH

    # Step 3 — SAR-9 #1 bare-token flag_for_review. When the candidate
    # normalizes EXACTLY to the per-canonical bare token (no further
    # qualifier), the corporate-split ambiguity routes to human triage.
    bare_token = VENDOR_BARE_TOKEN_FLAG.get(vendor_canonical)
    if bare_token and candidate_norm == bare_token.lower():
        return _DISPOSITION_FLAG_REVIEW

    # Step 4 — SAR-9 #1 positive-evidence accept. Substring match against the
    # raw lowercased candidate so dash-delimited shapes (``Motorola - BSG``)
    # remain reachable. Codified for ``Motorola Solutions`` to accept the
    # business-radio shape (BSG / Broadband Solutions Group / Business Light
    # Radios) under the §2.1 Solutions canonical.
    for evidence in VENDOR_POSITIVE_EVIDENCE.get(vendor_canonical, ()):
        if evidence and evidence in candidate_lower:
            return _DISPOSITION_ACCEPT

    # Step 5 — alias allowlist (after geographic-prefix-strip + normalization).
    for alias in VENDOR_ALIAS_ALLOWLIST.get(vendor_canonical, []):
        alias_norm = _normalize_vendor(_strip_geographic_prefix(alias))
        if alias_norm and alias_norm == candidate_norm:
            return _DISPOSITION_ACCEPT

    # Step 6 — default canonical match: exact-normalized OR prefix-token.
    if candidate_norm == canonical_norm:
        return _DISPOSITION_ACCEPT
    if candidate_norm.startswith(canonical_norm + " "):
        return _DISPOSITION_ACCEPT

    return _DISPOSITION_NO_MATCH


def alias_equality(candidate: str, alias: str) -> bool:
    """SAR-9 #2 — exact-normalized alias-equality predicate.

    Returns True iff the geographic-prefix-stripped + normalized candidate
    equals the geographic-prefix-stripped + normalized alias. No prefix-token
    match, no FP-list lookup, no bare-token / positive-evidence semantics —
    pure exact-normalized equality.

    Callers iterate manufacturer alias-strings (e.g.
    ``manufacturers.aliases``) via this predicate after invoking
    :func:`vendor_match_disposition` once per canonical_name. Restructure
    is the SAR-9 #2 alias-iteration bug-fix — the prior caller iterated
    alias-strings as the ``vendor_canonical`` parameter to
    :func:`vendor_match_disposition`, which caused
    ``VENDOR_FP_LIST.get('Harris Corporation')`` to return ``[]`` and the
    ``harris adacom`` substring check never fired.
    """
    if not candidate or not alias:
        return False
    candidate_norm = _normalize_vendor(_strip_geographic_prefix(candidate))
    alias_norm = _normalize_vendor(_strip_geographic_prefix(alias))
    if not candidate_norm or not alias_norm:
        return False
    return candidate_norm == alias_norm


def is_canonical_vendor_match(candidate: str, vendor_canonical: str) -> bool:
    """Bool-shape predicate per SAR-8 directive — True only on accept.

    ``flag_for_review`` and ``reject_fp`` both return False (they are NOT
    canonical matches; flag_for_review additionally requires human triage,
    surfaced via :func:`is_flagged_for_review` or
    :func:`vendor_match_disposition`).
    """
    return vendor_match_disposition(candidate, vendor_canonical) == _DISPOSITION_ACCEPT


def is_flagged_for_review(candidate: str, vendor_canonical: str) -> bool:
    """True iff the candidate hits an FP entry marked flag_for_review."""
    return (
        vendor_match_disposition(candidate, vendor_canonical)
        == _DISPOSITION_FLAG_REVIEW
    )


def is_fp_rejected(candidate: str, vendor_canonical: str) -> bool:
    """True iff the candidate hits a non-flagged FP entry (hard reject)."""
    return (
        vendor_match_disposition(candidate, vendor_canonical)
        == _DISPOSITION_REJECT_FP
    )
