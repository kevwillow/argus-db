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

Corpus provenance — re-measured after MAC-580 (MAC-618)
-------------------------------------------------------
Every count quoted in this module is an **A2V** count: the alias is the
needle, ``vendor_canonical_name`` / description is the haystack, which is what
``db.entity_boundary.boundary_match(token, text)`` computes. Direction matters
here, so it is stated rather than assumed.

MAC-580 rewrote 15 ``manufacturers.aliases`` blobs into RFC-4180-lite quoted
form, which *lengthens* an alias token (``REKOR RECOGNITION SYSTEMS`` +
``INC.`` become the single ``REKOR RECOGNITION SYSTEMS, INC.``). A longer
needle can only ever match fewer rows, so MAC-618 re-ran MAC-577's probe
against the pre-apply backup and against live and diffed them::

    PYTHONPATH=. python3 operator_review/MAC-618/rerun_blast_radius.py
    PYTHONPATH=. python3 operator_review/MAC-618/alias_confirmed_15.py

Measured result, not an inference: **every A2V count below is unchanged**.
All 12 flagged canonicals hold on all six probe fields, and the A2V union
holds for all 15 changed ids. The re-measured pre-corpus reproduces
``operator_review/MAC-577/alias_only_blast_radius.json`` field-for-field, and
a positive control (an alias mutated to an unmatchable string, 90 -> 0)
confirms the harness can see a move when one exists.

Two things the re-measurement corrected, both scoping errors rather than
arithmetic:

* The ``Harris`` entry below is ``manufacturers.id=8``, whose alias blob
  MAC-580 did **not** touch. It is not L3Harris (``id=9``); ``L3Harris`` is a
  separate canonical and is not in MAC-542's flagged cohort at all.
* The lengthening mechanism is real, but it fires once and off this cohort:
  Dedrone (``id=33``) alias ``Dedrone Holdings`` matched 5 rows and
  ``Dedrone Holdings, Inc.`` matches 4 — ``procurement_records.id=51399``,
  whose excerpt reads ``DEDRONE HOLDINGS, $480,000`` and so has no ``INC``
  token to absorb. The sibling alias ``DEDRONE DEFENSE LLC`` still covers the
  row, so the union is flat at 13. A union alone would have hidden this;
  per-alias decomposition is what surfaces it
  (``operator_review/MAC-618/alias_confirmed_15.json``).

Three tiers, not a flag
-----------------------
Alias-only matching is only a refinement when the vendor's alias set can carry
the attribution on its own. Measured per vendor
(``operator_review/MAC-577/alias_only_blast_radius.json``), the 12 flagged
canonicals split three ways:

``ALIAS_ONLY_CANONICALS`` (5)  applied. The two ``is_common_word=yes`` rows,
                               plus ``KeyW``/``Rekor``/``Harris``, ratified into
                               the applied tier by the CEO on MAC-636 (decision
                               comment ``8ce463c7-75d1-4de6-ab6a-0e23512273a1``
                               on MAC-577, control staged at ``3f7a2bf``).
``PROPOSED_ALIAS_ONLY``   (0)  empty. Held the three above until MAC-636.
                               MAC-577 §3's gate is NOT withdrawn — it still
                               holds the remaining short-single-token cohort,
                               and the gate that enforces it now pins the three
                               ratified names by name (see
                               ``MAC636_RATIFIED_PROMOTIONS`` and
                               ``tests/test_matching_policy.py``).
``DEFERRED_CANONICALS``   (7)  measured UNSAFE. Aliases absent, non-matching,
                               or themselves short bare tokens, so alias-only
                               would delete the vendor's footprint — the
                               MAC-527 refine-not-drop failure mode in
                               reverse. Needs alias coverage first, which is
                               a canonical DB write with its own ratified plan.

Every entry carries its measured reason rather than being silently omitted.

A fourth shape: basis-differentiated (MAC-588)
----------------------------------------------
``Axon`` is the one flagged canonical whose loss cohort is **basis-split**, so
no uniform rule fits it. Measured on HEAD (50,499 ``procurement_records``,
``operator_review/MAC-588/measure_rules.py``): 890 bare boundary-matches, 665
alias-confirmed, 225 bare-only — and that 225 splits 123 vendor-basis / 102
description-basis with opposite verdicts. All 102 were adjudicated
exhaustively (``operator_review/MAC-588/adjudication.tsv``): 29 are real
Axon Enterprise reseller awards, 73 are FPs.

So the rule is per-basis, and on the description basis the bare canonical is
additionally gated on a product qualifier. ``BasisRule`` below expresses that;
``attributes()`` is the decision function callers should use, because it makes
the qualifier impossible to skip.

APPLIED by MAC-622 under MAC-595 sign-off
-----------------------------------------
The rule is no longer proposed. The CEO signed off ``promote`` on MAC-595
(decision comment ``6564f836-66be-4f78-a643-474f11ee1a57``), having re-derived
every number above at HEAD rather than reading the dossier's, and MAC-622
applied it. ``MAC595_RATIFIED_BASIS_PROMOTIONS`` records the decision so the
sign-off gate can tell "decided" from "any short token is fair game" — the same
shape MAC-636 used for the alias-only tier, and for the same reason.

The sign-off was explicit that the move is not the deliverable: it also names
the gate hole the move opens (MAC-577 §3 constrained the alias-only tier and
nothing else, so a second short-single-token canonical could enter THIS tier
unsigned while the gate stayed green) and the drop-cohort re-dump obligation.
Both are discharged in ``tests/test_matching_policy.py``, as executing checks
rather than as prose — the live description-basis cohort is 112, not the 102
adjudicated, and nothing recomputed that until the sign-off did.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Optional

from db.alias_parser import split_aliases
# MAC-585 single-implementation boundary matcher. Imported rather than
# re-transcribed: MAC-588's constraint is "do not invent a second normaliser",
# and db/entity_boundary.py is the verbatim transcription of
# operator_review/MAC-542/rematch.py:26-40 that exists for exactly this reason.
from db.entity_boundary import boundary_match, contiguous, tokenize

Basis = Literal["vendor", "description"]

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
    # ── promoted from PROPOSED_ALIAS_ONLY by MAC-636 ──────────────────────
    # CEO-ratified: MAC-577 decision comment
    # 8ce463c7-75d1-4de6-ab6a-0e23512273a1, on the control staged at 3f7a2bf
    # (operator_review/MAC-577/ceo_ratification_check.py).
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
    # WITHDRAWN CLAIM (MAC-636). Through 3f7a2bf this entry ended with the
    # sentence quoted below. It is quoted verbatim, and line-broken so that each
    # phrase a reader would actually grep stays contiguous on one line, because
    # a retraction that its own wrapping makes unsearchable is not a retraction
    # (MAC-580: an in-place correction can orphan its own retraction):
    #     "Note the L3Harris footprint is unaffected: 'L3HARRIS' is a single"
    #     "token and never boundary-matched bare 'Harris' in the first place."
    # That is true on the VENDOR basis and FALSE on the DESCRIPTION basis, and
    # the matcher tests both (`contiguous(ct, vt[i]) or contiguous(ct, dt[i])`).
    # Asserting it of "the footprint" generalised a one-basis measurement to a
    # two-basis matcher. Measured correction below; per-row proof in
    # operator_review/MAC-636/l3harris_reattribution.tsv.
    "Harris": (
        "short single token. 3,029 bare boundary-matches vs 2,066 "
        "alias-confirmed via 'Harris Corporation'; sole-loss is 6 rows, all "
        "FP (HARRIS FIRE PROTECTION CO INC, DEREK J HARRIS, N HARRIS "
        "COMPUTER CORPORATION, MISCELLANEOUS FOREIGN AWARDEES). L3Harris "
        "RE-ATTRIBUTES, it is not unaffected: 4 rows with vendor "
        "'L3HARRIS TECHNOLOGIES, INC.' (procurement_records.id 59770, 59854, "
        "60042, 60078) carry a bare HARRIS token in their excerpt, were "
        "asserted to Harris (manufacturers.id=8), and do lose that "
        "attribution. All 4 are retained by the bare 'L3Harris' keyword "
        "(manufacturers.id=9, outside the MAC-542 flagged cohort, so still "
        "bare) and re-attribute to the correct vendor — verified per row, "
        "both bases and the full supporting-keyword set, in "
        "operator_review/MAC-636/l3harris_reattribution.tsv."
    ),
}

# The three names MAC-636 moved, pinned against the issue that decided them.
# The MAC-577 §3 gate is enforced against THIS tuple rather than against
# "ALIAS_ONLY_CANONICALS is allowed to contain short tokens": the gate has to
# distinguish "decided" from "any short token is fair game", and a count-only
# assertion cannot. Adding a name here is the recorded decision; the gate in
# tests/test_matching_policy.py fails on a short-token promotion that is not
# listed here, and that failure is itself exercised by a simulation.
MAC636_RATIFIED_PROMOTIONS: tuple[str, ...] = ("Harris", "KeyW", "Rekor")

# COST OF THIS PROMOTION — two numbers, and they are not interchangeable.
#
#   corpus-union       +7 rows leave the corpus entirely. 71 rows lost in the
#                      applied arm, 78 in the promoted arm
#                      (operator_review/MAC-577/policy_delta.json and
#                      policy_delta_promoted.json). A row counts here only if NO
#                      keyword in the whole 155-keyword universe still reaches
#                      it. 6 of the 7 are Harris, 1 is Rekor.
#   attribution-level  964 attributions removed: Harris 3,029 -> 2,066 (963),
#                      Rekor 91 -> 90 (1), KeyW 399 -> 399 (0). 957 of those 964
#                      rows KEEP their place in the corpus under another
#                      canonical; only the 7 above leave it.
#
# The +7 is the right number for corpus retention and the wrong number for a
# matcher-policy decision, because a row can hold its place in the corpus while
# silently losing its Harris attribution. Do not quote one as the other.
#
# Of the 964, the ingest had ever asserted 10 (Harris 9, Rekor 1, KeyW 0) —
# operator_review/MAC-577/ceo_ratification_check.py. 4 of the Harris 9
# re-attribute to L3Harris (above); the remaining 5 sit inside the 6 sole-loss
# FP rows. The other 954 exist only because the harvest and the audit matcher
# are two derivations of one keyword set, which is the defect MAC-577 found.

# PROPOSED: empty. It held KeyW/Rekor/Harris until MAC-636 promoted them.
# MAC-577 deliverable 3 — "do not apply alias-only matching to them blindly" —
# is NOT withdrawn by that promotion: it still governs the remaining
# short-single-token cohort, which is now exactly DEFERRED_CANONICALS. A future
# candidate lands here first, with its measured reason, and moving it up is a
# CEO call plus a line in MAC636_RATIFIED_PROMOTIONS' successor.
PROPOSED_ALIAS_ONLY: dict[str, str] = {}

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


# ── basis-differentiated (MAC-588) ────────────────────────────────────────


@dataclass(frozen=True)
class BasisRule:
    """Alias-only on the vendor basis; bare-plus-qualifier on the description.

    ``description_qualifiers`` are boundary-matched against the SAME description
    text the bare canonical matched. A bare hit with no qualifier does not
    attribute. The set must be non-empty: an empty one silently degrades this
    rule to "alias-only on vendor, bare on description", which is a different
    (measurably worse) rule — see ``assert_basis_rules_are_sound``.
    """

    reason: str
    description_qualifiers: tuple[str, ...]


# Axon's qualifier set. Every entry is either LOAD-BEARING (its removal loses
# an adjudicated true positive) or product-line hardening with zero measured
# hits on this corpus. Leave-one-out and leave-one-family-out are in
# operator_review/MAC-588/edges.json; the zero-hit entries are labelled there
# as speculative, NOT as measured.
#
#   LOAD-BEARING  TASER(12) CAMERA(4) TASERS(1) TAZER(1) CAMERAS(1)
#                 CARTRIDGE(1)
#   redundant here, kept for the next sweep   X26 X26P CARTRIDGES HOLSTERS
#                 FLEET "AXON BODY" "AXON FLEET"
#   zero hits (speculative hardening)         TAZERS CEW BODYCAM BODYCAMS
#                 "BODY WORN" HOLSTER EVIDENCE.COM "AXON DOCK" "AXON SIGNAL"
#                 "AXON RESPOND"
_AXON_QUALIFIERS = (
    "TASER", "TASERS", "TAZER", "TAZERS", "CEW",
    "CAMERA", "CAMERAS", "BODYCAM", "BODYCAMS", "BODY WORN",
    "X26", "X26P",
    "CARTRIDGE", "CARTRIDGES", "HOLSTER", "HOLSTERS",
    "FLEET",
    "EVIDENCE.COM",
    "AXON BODY", "AXON FLEET", "AXON DOCK", "AXON SIGNAL", "AXON RESPOND",
)

# APPLIED basis-differentiated rules. MAC-588 measured Axon's rule and found it
# clean; Axon is in the MAC-542 short-single-token cohort (``is_common_word=no``,
# ``recommended_action=REFINE``), so MAC-577 §3 held it for per-vendor sign-off.
# That sign-off was given on MAC-595 and MAC-622 applied it. Axon deliberately
# STAYS in DEFERRED_CANONICALS: alias-only really is unsafe for it (it would
# delete 29 adjudicated real awards), and the two tiers describe different rules
# — see ``assert_basis_rules_are_sound``.
BASIS_DIFFERENTIATED: dict[str, BasisRule] = {
    "Axon": BasisRule(
        reason=(
            "basis-split loss cohort, so no uniform rule fits. 890 bare "
            "boundary-matches / 665 alias-confirmed / 225 bare-only = 123 "
            "vendor-basis + 102 description-basis. The 123 vendor-basis rows "
            "are 9 distinct vendors, none of them Axon Enterprise (THE AXON "
            "GROUP LTD x50, AXON MEDICAL INC x43, AXON GARY L x14, AXON CABLE "
            "INC x10, AXON CONNECTED LLC x2, AXON MEDCHEM B.V. x1, AXON "
            "INSTRUMENTS INC x1, AXON SYSTEMS INC x1, AXON GOVERNMENT & "
            "COMMERCIAL SERVICES CORP x1). All 102 description-basis rows were "
            "adjudicated: 29 real Axon Enterprise reseller awards, 73 FPs. "
            "This rule retains 29/29 TP and 0/73 FP on that cohort and drops "
            "all 123 vendor-basis rows; corpus total 890 -> 694."
        ),
        description_qualifiers=_AXON_QUALIFIERS,
    ),
}

# The name MAC-622 moved, pinned against the issue that decided it. Same
# construction as MAC636_RATIFIED_PROMOTIONS and for the same reason: the
# MAC-577 §3 gate has to distinguish "decided" from "any short token is fair
# game", and neither a count nor an emptiness check can. Adding a name here is
# the recorded decision; the gate in tests/test_matching_policy.py fails on a
# short-token basis promotion that is not listed here, and that failure is
# itself exercised by a simulation.
#
# MAC-595 decision comment 6564f836-66be-4f78-a643-474f11ee1a57, verdict
# ``promote``, re-derived at HEAD 11eaa5f rather than at the dossier's 9e4a511:
# R0 890, RB 694 (delta -196), 29/29 TP retained, 0/73 FP retained, 0
# newly-attributed rows over all 50,499 (not the shipped LIMIT 5000).
MAC595_RATIFIED_BASIS_PROMOTIONS: tuple[str, ...] = ("Axon",)

# PROPOSED: empty. It held Axon until MAC-622 applied the MAC-595 sign-off.
# MAC-577 §3 is NOT withdrawn by that promotion — it still governs every other
# short-single-token canonical, on THIS tier as well as the alias-only one. A
# future candidate lands here first, with its measured reason and its
# exhaustively adjudicated loss cohort, and moving it up is a CEO call plus a
# line in MAC595_RATIFIED_BASIS_PROMOTIONS' successor.
PROPOSED_BASIS_DIFFERENTIATED: dict[str, BasisRule] = {}


def is_basis_differentiated(canonical: str) -> bool:
    """True iff an APPLIED basis-differentiated rule governs ``canonical``."""
    return canonical in BASIS_DIFFERENTIATED


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
    return qualified_aliases_for(canonical, aliases_field)


def qualified_aliases_for(canonical: str, aliases_field: str | None) -> list[str]:
    """The vendor's qualified aliases, deduped, first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for a in split_aliases(aliases_field):
        if is_qualified_alias(a) and a not in seen:
            seen.add(a)
            out.append(a)
    return out


def matcher_keywords_for_basis(
    canonical: str, aliases_field: str | None, basis: Basis
) -> list[str]:
    """Keywords admissible on ``basis`` for ``canonical``.

    For a basis-differentiated canonical the vendor basis is alias-only (the
    bare canonical is dropped) while the description basis still offers the
    bare canonical — but a bare description hit is NOT sufficient on its own.
    ``attributes()`` applies the qualifier; call that, not this, unless you are
    implementing the qualifier yourself.
    """
    if basis not in ("vendor", "description"):
        raise ValueError(f"basis must be 'vendor' or 'description', got {basis!r}")
    if not is_basis_differentiated(canonical):
        return matcher_keywords_for(canonical, aliases_field)
    aliases = qualified_aliases_for(canonical, aliases_field)
    if basis == "vendor":
        return aliases
    return aliases + [canonical]


def attributes(
    canonical: str,
    aliases_field: str | None,
    vendor_text: str | None,
    description_text: str | None,
) -> Optional[Basis]:
    """Does this row attribute to ``canonical``, and on which basis?

    Returns ``"vendor"``, ``"description"`` or ``None``. Vendor basis wins
    when both hold, matching ``operator_review/MAC-542/rematch.py``'s
    precedence.

    This is the function callers should use. ``matcher_keywords_for_basis``
    alone cannot express the description-basis qualifier, so a caller that
    builds keyword lists and matches them itself silently gets the un-narrowed
    behaviour for a basis-differentiated canonical.
    """
    if not is_basis_differentiated(canonical):
        kws = matcher_keywords_for(canonical, aliases_field)
        if any(boundary_match(k, vendor_text) for k in kws):
            return "vendor"
        if any(boundary_match(k, description_text) for k in kws):
            return "description"
        return None

    rule = BASIS_DIFFERENTIATED[canonical]
    aliases = qualified_aliases_for(canonical, aliases_field)
    if any(boundary_match(a, vendor_text) for a in aliases):
        return "vendor"
    if any(boundary_match(a, description_text) for a in aliases):
        return "description"
    # Bare canonical on the description basis only, and only with a qualifier.
    if boundary_match(canonical, description_text) and any(
        boundary_match(q, description_text) for q in rule.description_qualifiers
    ):
        return "description"
    return None


def assert_basis_rules_are_sound() -> None:
    """Structural guards on the basis-differentiated tier.

    Deliberately NOT folded into ``assert_no_overlap``: a basis-differentiated
    canonical stays in ``DEFERRED_CANONICALS`` because alias-only really is
    unsafe for it (for Axon it would delete 29 adjudicated real awards). The
    two tiers describe different rules, so they overlap on purpose.
    """
    both = set(BASIS_DIFFERENTIATED) & set(PROPOSED_BASIS_DIFFERENTIATED)
    if both:
        raise AssertionError(
            f"canonical in both applied and proposed basis tiers: {sorted(both)}")
    clash = set(BASIS_DIFFERENTIATED) & set(ALIAS_ONLY_CANONICALS)
    if clash:
        raise AssertionError(
            f"canonical is both ALIAS_ONLY and basis-differentiated — the two "
            f"rules contradict on the description basis: {sorted(clash)}")
    for tier in (BASIS_DIFFERENTIATED, PROPOSED_BASIS_DIFFERENTIATED):
        for canonical, rule in tier.items():
            if canonical not in flagged_canonicals():
                raise AssertionError(
                    f"{canonical} is not in the MAC-542 flagged cohort; a "
                    f"basis rule for it would be a new screen, not a refinement")
            if not rule.description_qualifiers:
                raise AssertionError(
                    f"{canonical} has an empty qualifier set — that silently "
                    f"degrades the rule to bare-on-description")


def assert_basis_rules_are_applicable(
    rows: Iterable[tuple[str, str | None]]
) -> None:
    """No APPLIED basis rule may leave a vendor with an empty vendor-basis set.

    Same failure mode as ``assert_policy_is_applicable``: the vendor basis is
    alias-only, so a vendor with no qualified alias would be deleted from
    vendor-basis attribution entirely.
    """
    empty = [
        c for c, al in rows
        if is_basis_differentiated(c)
        and not matcher_keywords_for_basis(c, al, "vendor")
    ]
    if empty:
        raise AssertionError(
            "basis-differentiated canonicals with no qualified alias would "
            f"attribute nothing on the vendor basis: {sorted(empty)}")


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


# ── Proper-extension guard (MAC-598) ──────────────────────────────────────
#
# Boundary-valid is not identity-valid. ``db/entity_boundary.py`` stops
# substring-inside-token (``PLAXIS`` does not match ``AXIS``); it does nothing
# against a token-level extension. ``Axis Communications`` tokenises to
# ``[AXIS, COMMUNICATIONS]``, a contiguous sublist of
# ``[DIGITAL, AXIS, COMMUNICATIONS]``, so the row boundary-matches — and
# because that keyword is LONG, ``t2_select.py``'s ``all(k in SHORT)`` test
# never routes it to T2. It lands in T3 "boundary-clean" unadjudicated.
#
# MAC-598 swept every LONG keyword in the ``rematch.py`` KEYWORDS union (118
# of 155) against every distinct ``procurement_records.vendor_canonical_name``
# for the PROPER-extension case (vendor strictly longer than keyword):
# ``operator_review/MAC-598/t3_audit.py`` -> 86 pairs, 84 vendors, 29,874 rows.
#
# The issue proposed a two-way rule: prefix extension bad, suffix extension
# fine. The prefix half survives; the suffix half does NOT, and it is
# falsified on source-side evidence rather than on names:
#
#   KENWOOD FIRE DEPARTMENT (14 rows, canonical ``Kenwood``/police_radio)
#     "REIMBURSEMENT FOR FIRE RESPONSE ON TRUST LAND"
#   KENWOOD HEALTH CARE CORP (5)          "CNH FY 2008"
#   CLEARVIEW-ROUTH LP (7, ``Clearview AI``/face_recog)
#     "NURSING HOME SERVICES - 1ST QUARTER EXPRESS"
#   CLEARVIEW SONOGRAPHICS LLC (2)        "CRSU - ONE MONTH ULTRASOUND COVERAGE."
#   VIGILANT CYBER SYSTEMS, INC. (10, ``Vigilant Solutions``/alpr)
#     "MEDICAL RESEARCH AND DEVELOPMENT CONTRACT DHA SBIR 2021.1"
#   VIGILANT FIRE INC. (1)                "FIRE EXTINGUISHER DISPOSAL"
#
# Every one is a SUFFIX extension and a different entity. What actually
# separates the legitimate cases is not the direction of the extension but
# whether the appended tokens are *entity-neutral* — a legal form or a
# jurisdiction. ``MOTOROLA SOLUTIONS, INC.`` appends only ``INC``;
# ``KENWOOD FIRE DEPARTMENT`` appends a whole line of business.
#
# So the guard is three-way, and the residual is routed to adjudication rather
# than silently retained. That is the whole point of the defect: T3 was
# labelled adjudicated when it was not.

ExtensionVerdict = Literal["exact", "retain", "adjudicate", "block"]

# Tokens that carry no entity information. Legal forms and jurisdictions only.
# Derived from the observed tail vocabulary of the MAC-598 sweep
# (``operator_review/MAC-598/t3_audit.log``) plus the standard forms of the
# same kind; anything descriptive (SYSTEMS, SOLUTIONS, DEFENSE, MARITIME,
# TECHNOLOGIES, ...) is deliberately absent, because those are exactly the
# tokens that distinguish ``VIGILANT SOLUTIONS`` from ``VIGILANT CYBER
# SYSTEMS``.
LEGAL_FORM_TOKENS = frozenset({
    "INC", "INCORPORATED", "LLC", "LLP", "LP", "L", "P", "LTD", "LIMITED",
    "CORP", "CORPORATION", "CO", "COMPANY", "PLC", "GMBH", "AG", "SA", "SAS",
    "NV", "BV", "AB", "AS", "OY", "SPA", "SRL", "PTY", "PTE", "KK", "KG",
})

# Jurisdiction qualifiers. A national arm of a vendor is still that vendor.
GEOGRAPHIC_TOKENS = frozenset({
    "USA", "US", "AMERICA", "AMERICAS", "CANADA", "UK", "EUROPE", "EMEA",
    "APAC", "ASIA", "INTERNATIONAL", "GLOBAL", "WORLDWIDE",
})

# Tokens that may be PREPENDED without changing the entity. Articles only.
# Untriggered in the current corpus (the three observed prepends are DIGITAL,
# BLUE and 022808) — ``tests/test_matching_policy.py`` carries the positive
# control that proves this allowlist is reachable, per BRIEF_STANDARDS R7.
PREFIX_NEUTRAL_TOKENS = frozenset({"THE"})

_NEUTRAL_TAIL_TOKENS = LEGAL_FORM_TOKENS | GEOGRAPHIC_TOKENS


def extension_verdict(keyword: str, vendor_text: str | None) -> Optional[ExtensionVerdict]:
    """Classify how ``keyword`` sits inside ``vendor_text``.

    ``None``   no entity-boundary match at all.
    ``exact``  the vendor name is exactly the keyword's token sequence.
    ``retain`` proper SUFFIX extension whose appended tail is entirely
               entity-neutral (legal form / jurisdiction). Same entity.
    ``adjudicate``
               proper SUFFIX extension carrying descriptive tokens. May or may
               not be the same entity; a human must say which. This is the
               MAC-598 residue that T3 mislabelled as clean.
    ``block``  proper PREFIX extension. A prepended descriptive token changes
               the entity: ``DIGITAL AXIS COMMUNICATIONS`` is an AV integrator,
               not ``Axis Communications``.

    Callers must not treat ``adjudicate`` as ``retain``. Substituting one for
    the other reintroduces precisely the defect this function exists to catch.
    """
    need = tokenize(keyword)
    hay = tokenize(vendor_text)
    if not need or not contiguous(need, hay):
        return None
    if len(hay) == len(need):
        return "exact"

    # Offsets at which the keyword occurs as a whole-token run.
    offs = [i for i in range(len(hay) - len(need) + 1)
            if hay[i:i + len(need)] == need]
    # Prefer the earliest occurrence: it minimises the prepended tail, so a
    # vendor name that repeats the keyword is judged on its leading form.
    start = min(offs)
    head, tail = hay[:start], hay[start + len(need):]

    if head and any(t not in PREFIX_NEUTRAL_TOKENS for t in head):
        return "block"
    if tail and any(t not in _NEUTRAL_TAIL_TOKENS for t in tail):
        return "adjudicate"
    return "retain"


def extension_permits_attribution(keyword: str, vendor_text: str | None) -> bool:
    """Vendor-basis gate: may this boundary hit be credited without review?

    ``True`` only for ``exact`` and ``retain``. ``adjudicate`` is False on
    purpose — an unreviewed descriptive-suffix hit is not evidence, and
    returning True for it is the T3 mislabelling in one line of code.
    """
    return extension_verdict(keyword, vendor_text) in ("exact", "retain")
