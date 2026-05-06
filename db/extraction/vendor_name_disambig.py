"""SAR-8 — vendor-name disambig predicate (alias allowlist + geographic-prefix).

Codifies the BIBLE_AMENDMENTS.md SAR-8 entry (commit ``811b4de``). Provides the
shared ``_normalize_vendor`` predicate (moved from
``db/validation/phase3_inference_candidates.py``) plus an allowlist-driven
``is_canonical_vendor_match`` / ``vendor_match_disposition`` pair that:

1. **Rejects prefix-token false-positives** (`Axon Networks Inc.` ≠ Axon
   Enterprise, `Flock Audio Inc.` ≠ Flock Safety, `Harris Adacom Corp` ≠ Harris
   Corp).
2. **Recovers canonical-name matches** under geographic-prefix variations
   (`SZ DJI TECHNOLOGY CO.,LTD` → `dji`).
3. **Maintains a per-vendor alias allowlist** keyed by canonical §2.1 name.
4. **Strips a narrow geographic-prefix set** (`SZ`, `Shenzhen`, `SZ.`,
   `Shenzhen Co.,`) before normalization. US state/city prefixes (`New York
   Axon`) are intentionally NOT stripped — they carry separate legal-entity
   meaning.

A third disposition state — ``flag_for_review`` — surfaces the
``GENETEC Corporation`` case (early-2000s OUI registration with Tokyo address;
may be distinct from Genetec Inc., the §2.1 alpr vendor). Surfaces require
human / CEO triage rather than a silent accept-or-reject.

Authority chain:
- BIBLE_AMENDMENTS.md SAR-8 (commit ``811b4de``).
- Bible §2.1 canonical-vendor list.
- Bible §7.3 Extraction Worker contract.
- Bible §7.4 Validator contract.
- MAC-39 halt-flag #1 surface 2026-05-06; MAC-1 board ratification
  ``613ec532`` 2026-05-06T17:08:16Z.
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
}


# ---------------------------------------------------------------------------
# Match disposition predicate.
# ---------------------------------------------------------------------------

_DISPOSITION_ACCEPT: Final[str] = "accept"
_DISPOSITION_REJECT_FP: Final[str] = "reject_fp"
_DISPOSITION_FLAG_REVIEW: Final[str] = "flag_for_review"
_DISPOSITION_NO_MATCH: Final[str] = "no_match"


def vendor_match_disposition(candidate: str, vendor_canonical: str) -> str:
    """Return the SAR-8 disposition for ``candidate`` against ``vendor_canonical``.

    Returns one of:
    - ``"accept"`` — canonical match (exact-normalized, alias-allowlist hit, or
      prefix-token match like ``Avigilon Alta`` against ``Avigilon``).
    - ``"reject_fp"`` — the candidate matches a known false-positive substring
      enumerated in ``VENDOR_FP_LIST`` (``Axon Networks Inc.`` against
      ``Axon``, etc.).
    - ``"flag_for_review"`` — the candidate matches an FP entry marked with
      ``flag_for_review=True`` (``GENETEC Corporation`` against ``Genetec``).
      Caller should route to a human/CEO triage queue rather than accepting
      or rejecting silently.
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

    # Step 3 — alias allowlist (after geographic-prefix-strip + normalization).
    for alias in VENDOR_ALIAS_ALLOWLIST.get(vendor_canonical, []):
        alias_norm = _normalize_vendor(_strip_geographic_prefix(alias))
        if alias_norm and alias_norm == candidate_norm:
            return _DISPOSITION_ACCEPT

    # Step 4 — default canonical match: exact-normalized OR prefix-token.
    if candidate_norm == canonical_norm:
        return _DISPOSITION_ACCEPT
    if candidate_norm.startswith(canonical_norm + " "):
        return _DISPOSITION_ACCEPT

    return _DISPOSITION_NO_MATCH


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
