"""Canonical-name matching policy — MAC-577.

Problem
-------
``manufacturers.canonical_name`` values that are common English words or very
short single tokens act as FP magnets: the vendor-attribution matcher credits a
procurement row to the vendor whenever the **bare canonical** boundary-matches,
even though the row has nothing to do with the vendor. Measured on HEAD
(``db/argus.db``, 50,499 ``procurement_records``):

    Reveal   66 bare boundary-matches; 65 are REVEAL GLOBAL CONSULTING /
             REVEAL IMAGING TECHNOLOGIES / REVEAL BIOSCIENCES / REVEAL
             TECHNOLOGY. Exactly 1 is REVEAL MEDIA USA INC.
    STOP     11 bare boundary-matches; 0 are Satellite Tracking of People.
             ENGILITY LLC x3, FAXON ENGINEERING x2, HANWHA 63 CITY CO x2, ...

Both already carry precise qualified aliases. The registry data is fine; the
matcher is the problem. This module is the fix, and it is deliberately NOT a
schema change: no column, no ``query_default`` enum value, no DB write. The
flag lives in code, next to the matcher it governs.

Why the ingest-side override is not sufficient
----------------------------------------------
``db/sources/usaspending.py`` already carries ``KEYWORD_OVERRIDES`` and it was
in force during the sweep — ``extraction_runs.id=15`` notes, verbatim::

    "keyword_overrides_applied": {"Harris": "Harris Corporation",
      "Jacobs": "Jacobs Engineering", "KeyW": "KeyW Corporation",
      "Reveal": "Reveal Media"}

Reveal was therefore queried as the phrase ``Reveal Media`` — and still
returned 66 rows of which only 1 contains that phrase. USAspending's
``keywords`` filter does not honour a multi-word value as a phrase. So the
override constrains what we *ask for*, never what we *accept*: only a local
boundary check can do that. The policy below is applied locally, on the
accept side.

Screen provenance
-----------------
The flagged set is NOT re-derived here. It is the non-``KEEP`` cohort of
``operator_review/MAC-542/T2_query_default_demotion_proposal.tsv`` (commit
``e0dc82f``), which screened all 148 ``query_default='visible'`` canonicals and
carries the ``is_common_word`` column. ``tests/test_matching_policy.py`` pins
this module's sets against that TSV so the two cannot drift.

Three tiers, not a flag
-----------------------
Alias-only matching is only a refinement when the vendor's alias set can carry
the attribution on its own. Measured per vendor
(``operator_review/MAC-577/alias_only_blast_radius.json``), the 12 flagged
canonicals split three ways:

``ALIAS_ONLY_CANONICALS`` (2)  applied. The two ``is_common_word=yes`` rows.
``PROPOSED_ALIAS_ONLY``   (3)  measured safe, NOT applied — MAC-577 §3 holds
                               the short-single-token cohort for per-vendor
                               sign-off before it is applied.
``DEFERRED_CANONICALS``   (7)  measured UNSAFE. Aliases absent, non-matching,
                               or themselves short bare tokens, so alias-only
                               would delete the vendor's footprint — the
                               MAC-527 refine-not-drop failure mode in
                               reverse. Needs alias coverage first, which is
                               a canonical DB write with its own ratified plan.

Every entry carries its measured reason rather than being silently omitted.
"""

from __future__ import annotations

from typing import Iterable

from db.alias_parser import split_aliases

# MAC-542 §5 short-single-token rule, verbatim from
# ``operator_review/MAC-542/t2_select.py:57`` — kept identical on purpose so
# the audit selector and this policy cannot disagree about what "short" means.
SHORT_MAX_LEN = 6


def is_short_token(value: str) -> bool:
    """MAC-542 §5: a 'short single-token FP-magnet candidate'."""
    return len(value) <= SHORT_MAX_LEN and " " not in value


def is_qualified_alias(alias: str) -> bool:
    """An alias is *qualified* iff it is not itself a short single token.

    A bare short alias re-imports the very FP magnet the policy removes.
    ``DJI``'s alias blob literally contains ``Autel``, ``Parrot``, ``Axon``
    and ``DJI``; matching on those would be strictly worse than matching on
    the bare canonical, not better.
    """
    return not is_short_token(alias.strip())


# ── The policy ────────────────────────────────────────────────────────────
#
# ALIAS_ONLY: the bare canonical is NOT a keyword. Attribution must come from
# a qualified alias. Value = the measured justification (MAC-577 probes).
ALIAS_ONLY_CANONICALS: dict[str, str] = {
    "STOP": (
        "common word. 11 bare boundary-matches, 0 alias-confirmed — the "
        "vendor has no procurement footprint at all. Top FP vendors: "
        "ENGILITY LLC x3, FAXON ENGINEERING CO INC x2, HANWHA 63 CITY CO x2."
    ),
    "Reveal": (
        "common word. 66 bare boundary-matches, 1 alias-confirmed "
        "(REVEAL MEDIA USA INC, id=86058). The other 65 are REVEAL GLOBAL "
        "CONSULTING x34, REVEAL IMAGING TECHNOLOGIES x20, REVEAL "
        "BIOSCIENCES x6, REVEAL TECHNOLOGY x5."
    ),
}

# PROPOSED: measured safe, but NOT applied. MAC-577 deliverable 3 requires the
# short-single-token cohort to come back for per-vendor sign-off before it is
# applied — "do not apply alias-only matching to them blindly". These three
# clear the bar on evidence; promoting them is a CEO call, and the promotion
# is a one-line move of the entry into ALIAS_ONLY_CANONICALS above.
# Joint measured cost if all three are promoted: +7 rows lost, all FP
# (see operator_review/MAC-577/policy_delta.json).
PROPOSED_ALIAS_ONLY: dict[str, str] = {
    "KeyW": (
        "short single token. bare_only=0 — every row the bare canonical "
        "reaches is also reached by a qualified alias, so the substitution "
        "is a strict no-op on this corpus and pure hardening against the "
        "next sweep. Zero-risk promotion."
    ),
    "Rekor": (
        "short single token. bare_only=1 (UPSTATE WHOLESALE SUPPLY INC, an "
        "FP); 90 of 91 rows are alias-confirmed via REKOR RECOGNITION "
        "SYSTEMS, INC. / Rekor Systems / Rekor Scout."
    ),
    "Harris": (
        "short single token. 3,029 bare boundary-matches vs 2,066 "
        "alias-confirmed via 'Harris Corporation'; sole-loss is 6 rows, all "
        "FP (HARRIS FIRE PROTECTION CO INC, DEREK J HARRIS, N HARRIS "
        "COMPUTER CORPORATION, MISCELLANEOUS FOREIGN AWARDEES). Note the "
        "L3Harris footprint is unaffected: 'L3HARRIS' is a single token and "
        "never boundary-matched bare 'Harris' in the first place."
    ),
}

# DEFERRED: flagged by the MAC-542 screen, but alias-only matching would
# destroy real attribution. Not applied. Each needs alias coverage first,
# which is a canonical DB write and needs its own ratified plan.
DEFERRED_CANONICALS: dict[str, str] = {
    "Berla": (
        "aliases IS NULL. Alias-only matching would match nothing at all: "
        "154 bare matches drop to 0, and 147 of them leave the corpus "
        "entirely — including rows whose vendor is literally BERLA "
        "CORPORATION. Needs an alias before it can be flagged."
    ),
    "Getac": (
        "qualified aliases ('Getac Technology Corporation', 'Getac "
        "Technology Corp.') boundary-match 0 of 50,499 rows. 1,176 bare "
        "matches, 1,171 sole-loss. The real footprint is reseller-booked "
        "(OSI FEDERAL TECHNOLOGIES, NCS TECHNOLOGIES, LOWRY HOLDING), so "
        "the corporate-form aliases never appear."
    ),
    "Skydio": (
        "0 qualified aliases. The alias blob is a co-mention list of short "
        "bare tokens ('DJI, Skydio, Brinc, DJI, Skydio, DJI, Parrot, "
        "Skydio'), so alias-only matching is undefined. 580 sole-loss "
        "including ATLANTIC DIVING SUPPLY, INC., a real Skydio reseller."
    ),
    "Parrot": (
        "qualified aliases (PARROT FAURECIA AUTOMOTIVE SAS, PARROT DRONE "
        "SAS) boundary-match 0 rows; 226 bare matches, all 226 sole-loss."
    ),
    "DJI": (
        "alias blob is contaminated with co-mentions: 31 of 48 parsed "
        "aliases are short bare tokens including Autel, Axon, Parrot, "
        "Yuneec, BRINC, 3DR. Alias-only matching would import four other "
        "vendors' FP magnets. 636 sole-loss."
    ),
    "Axon": (
        "the loss cohort is basis-split, so a uniform rule is wrong. Of 225 "
        "bare_only rows, the 123 vendor-basis ones are clean FPs (THE AXON "
        "GROUP LTD x50, AXON MEDICAL INC x43, AXON GARY L x14, AXON CABLE "
        "INC x10) but the 102 description-basis ones contain real reseller "
        "body-cam awards — 'AARDVARK / AXON X26P TASERS', 'M. C. DEAN, INC. "
        "/ AXON SPECIAL SERVICE AGREEMENT FOR ALL BODY CAMERAS SOLUTIONS "
        "LOCATED AT PENTAGON FORCE PROTECTION AGENCY' — mixed with real FPs "
        "('AXON THERAPY SYSTEM', 'INFORMATICA AXON GOVERN LICENSE')."
    ),
    "Jacobs": (
        "75 sole-loss, and 3 of them name the vendor: JACOBS GOVERNMENT "
        "SERVICES COMPANY / JACOBS PROJECT MANAGEMENT CO. The alias list "
        "has 'JACOBS GOVERNMENT SERVICES CO' — it misses on CO vs COMPANY. "
        "An alias-coverage fix, not a matcher fix."
    ),
}


def is_alias_only(canonical: str) -> bool:
    """True iff ``canonical`` must never be matched as a bare keyword."""
    return canonical in ALIAS_ONLY_CANONICALS


def matcher_keywords_for(canonical: str, aliases_field: str | None) -> list[str]:
    """Return the keyword list the matcher may use to attribute to ``canonical``.

    Normal vendor  -> ``[canonical]``, byte-identical to today's behaviour.
    Alias-only     -> qualified aliases ONLY; the bare canonical is dropped.

    The unflagged arm deliberately does NOT gain alias keywords. Adding
    aliases for all 148 visible canonicals is a keyword-set *expansion* with
    its own FP surface — measured, it pulled in 47 unrelated rows
    (SECURITAS, JOHNSON CONTROLS, MISCELLANEOUS FOREIGN AWARDEES) and moved
    deferred DJI by +2. MAC-577 is a narrowing, not an expansion; the two
    must not be smuggled together. Alias-based recall for unflagged vendors
    is a separate question with its own evidence bar.

    An alias-only canonical with no qualified alias returns ``[]`` — it
    attributes nothing. That is why such vendors belong in
    ``DEFERRED_CANONICALS`` and not in ``ALIAS_ONLY_CANONICALS``;
    ``assert_policy_is_applicable`` enforces it.
    """
    if not is_alias_only(canonical):
        return [canonical]
    qualified = [a for a in split_aliases(aliases_field) if is_qualified_alias(a)]
    # dedupe, preserve first-seen order
    seen: set[str] = set()
    out: list[str] = []
    for k in qualified:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def assert_policy_is_applicable(rows: Iterable[tuple[str, str | None]]) -> None:
    """Guard: no ALIAS_ONLY canonical may end up with an empty keyword list.

    ``rows`` is ``(canonical_name, aliases)`` straight from ``manufacturers``.
    Flagging a vendor whose aliases cannot carry the attribution silently
    deletes that vendor from every future match — the MAC-527 refine-not-drop
    failure mode. Fail loudly instead.
    """
    empty = [
        c for c, al in rows
        if is_alias_only(c) and not matcher_keywords_for(c, al)
    ]
    if empty:
        raise AssertionError(
            "ALIAS_ONLY canonicals with no qualified alias would attribute "
            f"nothing: {sorted(empty)}. Give them a qualified alias (a "
            "canonical DB write, needs its own ratified plan) or move them "
            "to DEFERRED_CANONICALS."
        )


def assert_no_overlap() -> None:
    """The three policy tiers must be pairwise disjoint."""
    tiers = {
        "ALIAS_ONLY": set(ALIAS_ONLY_CANONICALS),
        "PROPOSED": set(PROPOSED_ALIAS_ONLY),
        "DEFERRED": set(DEFERRED_CANONICALS),
    }
    names = sorted(tiers)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            both = tiers[a] & tiers[b]
            if both:
                raise AssertionError(
                    f"canonical in both {a} and {b}: {sorted(both)}")


def flagged_canonicals() -> set[str]:
    """Every canonical the MAC-542 screen flagged, across all three tiers."""
    return (set(ALIAS_ONLY_CANONICALS) | set(PROPOSED_ALIAS_ONLY)
            | set(DEFERRED_CANONICALS))
