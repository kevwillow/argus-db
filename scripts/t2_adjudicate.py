"""MAC-546 T2 — short-keyword procurement cluster adjudication predicates.

Per the issue spec (MAC-546):
  - 394 (keyword, vendor) clusters pass the entity-boundary check but fail
    the identity check (per MAC-542 §5 + §6a).
  - For each cluster: KEEP (real vendor), DROP (different entity), or
    UNRESOLVED (needs source).

Verdict rules, in priority order:
  1. KEEP  if vendor matches a registry alias exactly (registry = the
            manufacturers.canonical_name + known aliases for `keyword`).
  2. DROP  if vendor matches a person-suffix pattern (", GIVEN SURNAME")
            AND the vendor name does not also end with a corporate suffix.
  3. DROP  if vendor contains an exclude-token — a token that contradicts the
            registry vendor's identity by naming a different LINE OF BUSINESS,
            a non-manufacturer ENTITY FORM, or a specific known-FP ENTITY.
            The cite names which of the three it was (MAC-724).
  4. KEEP  if vendor contains the registry canonical as a whole-word
            (single-token canonical) or as a contiguous sublist of
            vendor tokens (multi-word canonical).
  5. KEEP  if basis='description' AND excerpt contains a brand-token
            (reseller selling the registry vendor's product).
  6. DROP  if basis='description' AND excerpt contains an exclude-token.
  7. KEEP  if basis='description' AND no other rule fires (reseller-of-
            registry-product default per MAC-542 §3 description-retention).
  8. UNRESOLVED otherwise (vendor-basis, no rule fired; needs source).

Cross-keyword clusters (e.g., "Berla+MSAB") are split on "+" and adjudicated
per sub-keyword; the strongest verdict wins (KEEP > UNRESOLVED > DROP).

Sentinels (e.g., STOP) are common-word FP magnets with no registry vendor;
every cluster matching them is DROP.
"""
from __future__ import annotations
from typing import Literal, Optional, Tuple
import re

Verdict = Literal["KEEP", "DROP", "UNRESOLVED"]


# Registry-vendor map: keyword -> canonical manufacturer name (and aliases).
# Anchored to the issue spec (MAC-546 KEEP table) + manufacturers table.
#
# MAC-724: the single `exclude_tokens` set is split by WHAT THE TOKEN IS, because
# Rule 3's cite asserted a class ("excluded industry") that was false for part of
# the set it described. The union of the three class sets is materialised back
# onto `exclude_tokens` below, so every existing reader keeps working.
#
#   exclude_industry_tokens — names a LINE OF BUSINESS. 'FIRE PROTECTION',
#       'CATERING', 'PROSTHETIC'. Answers *why* the vendor is excluded.
#   exclude_form_tokens     — names an ENTITY FORM, not a business and not a
#       name: 'JV', 'JOINT VENTURE'. Answers *what kind of registrant* it is.
#   exclude_entity_tokens   — names a SPECIFIC known-false-positive entity or
#       person: 'OTTO BOCK', 'DEREK J HARRIS'. Answers *which entity* it is.
#
# The test that guards this split is `tests/test_t2_adjudicate.py`, which holds a
# frozen literal of the pre-split sets and asserts set identity in both
# directions, per keyword. A reclassification that silently drops a token would
# change verdicts while looking like a relabel; that test is what stops it.
#
# MAC-756 ported this from the branch then named `v1.8.0-stage` — HISTORICAL
# name, renamed to `parked/wave-widenet-undrained` by MAC-757 on 2026-08-20 —
# where MAC-724 landed on a branch that never reached the release line. The classification below is byte-identical to
# that branch's; what is new here is that it composes with MAC-753's Rule 1 fix.
REGISTRY: dict[str, dict] = {
    "Harris": {
        "canonical": "HARRIS",
        "aliases": [
            "HARRIS CORPORATION", "HARRIS CORP", "HARRIS CORPORATION, INC.",
            "L3HARRIS TECHNOLOGIES", "L3HARRIS TECHNOLOGIES INTEGRATED SYSTEMS",
        ],
        "brand_tokens": {"TACTICAL RADIO", "L3HARRIS", "FALCON III", "HARRIS RADIO"},
        "exclude_industry_tokens": {
            "COMPUTER CORPORATION", "FIRE PROTECTION", "CONSULTING",
            "PROPERTIES LLC",
        },
        "exclude_form_tokens": set(),
        # PRYOR / PRYOR MCGINNIS: the firm Pryor McGinnis Consulting.
        # DEREK J HARRIS: a person. TELECOMM1STOP: the company Telecomm1Stop.
        "exclude_entity_tokens": {
            "TELECOMM1STOP", "PRYOR MCGINNIS", "PRYOR", "DEREK J HARRIS",
        },
    },
    "Jacobs": {
        "canonical": "JACOBS",
        "aliases": [
            "JACOBS ENGINEERING", "JACOBS ENGINEERING GROUP",
            "JACOBS TECHNOLOGY", "JACOBS PROJECT MANAGEMENT",
            "JACOBS FACILITIES", "JACOBS GOVERNMENT SERVICES",
        ],
        "brand_tokens": set(),
        "exclude_industry_tokens": {
            "TELEPHONE CONTRACTORS", "ENTERPRISE MANAGEMENT", "CATERING",
        },
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "DJI": {
        "canonical": "DJI",
        "aliases": ["SZ DJI TECHNOLOGY", "DA-JIANG INNOVATIONS"],
        "brand_tokens": {"MAVIC", "PHANTOM", "INSPIRE", "MATRICE", "AGRAS"},
        # 'A SERVICES JV' and siblings are industry tokens, not form tokens: each
        # names a line of business (services / construction / reconstruction) and
        # only then the vehicle. Bare 'JV' names no business at all, which is
        # exactly why it needs its own class.
        "exclude_industry_tokens": {
            "CONSTRUCTION", "RECONSTRUCTION", "SERVICES", "A SERVICES JV",
            "A CONSTRUCTION JV", "A RECONSTRUCTION JV",
        },
        "exclude_form_tokens": {"JV", "JOINT VENTURE"},
        # Named joint ventures whose initialism collides with the drone maker.
        "exclude_entity_tokens": {"PRI/DJI", "PRI-DJI", "KMK-DJI"},
    },
    "Axon": {
        "canonical": "AXON",
        "aliases": [
            "AXON ENTERPRISE", "AXON ENTERPRISE INC", "AXON ENTERPRISE, INC.",
            "TASER INTERNATIONAL",
        ],
        "brand_tokens": {
            "TASER", "BODY CAMERA", "BODYCAM", "AXON SIGNAL", "AXON EVIDENCE",
            "AXON FLEET", "AXON AIR",
        },
        "exclude_industry_tokens": {
            "MEDICAL", "CABLE", "THERAPY", "PROSTHETIC", "ORTHOTIC",
            "FORENSIC TOXICOLOGY",
        },
        "exclude_form_tokens": set(),
        # All five are companies: NeuraLace Medical, The Axon Group, Otto Bock
        # HealthCare, Molecular Devices, M. C. Dean.
        "exclude_entity_tokens": {
            "NEURALACE", "AXON GROUP", "OTTO BOCK", "MOLECULAR DEVICES",
            "M. C. DEAN",
        },
    },
    "Axis": {
        "canonical": "AXIS COMMUNICATIONS",
        "aliases": [
            "AXIS COMMUNICATIONS", "AXIS COMMUNICATIONS AB",
            "AXIS COMMUNICATIONS INC", "AXIS COMMUNICATIONS, INC.",
        ],
        "brand_tokens": {"AXIS CAMERA", "AXIS P", "AXIS Q", "AXIS M"},
        "exclude_industry_tokens": {
            "PROSTHETIC", "ORTHOTIC", "FORENSIC TOXICOLOGY",
            "FASTENING", "MANAGEMENT GROUP",
        },
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "DRT": {
        "canonical": "DIGITAL RECEIVER TECHNOLOGY",
        "aliases": [
            "DIGITAL RECEIVER TECHNOLOGY", "DIGITAL RECEIVER TECHNOLOGY INC",
            "DRT INC",
        ],
        "brand_tokens": {"DRT 1303B", "STINGRAY", "KINGFISH", "AMBERJACK", "DRT 1265A"},
        "exclude_industry_tokens": {"STRATEGIES"},
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": {"DRT, LLC", "BURYCHKA DRT"},
    },
    "Reveal": {
        "canonical": "REVEAL MEDIA",
        "aliases": ["REVEAL MEDIA USA", "REVEAL MEDIA USA INC"],
        "brand_tokens": {
            "REVEAL BODY CAM", "BODY WORN CAMERA", "REVEAL D5", "REVEAL D7",
            "REVEAL MEDIA",
        },
        "exclude_industry_tokens": {
            "GLOBAL CONSULTING", "CONSULTING", "BIOSCIENCE", "BIOSCIENCES",
            "IMAGING TECHNOLOGIES",
        },
        "exclude_form_tokens": set(),
        # Reveal Technology, Inc. — a distinct company, not an industry.
        "exclude_entity_tokens": {"REVEAL TECHNOLOGY"},
    },
    "Parrot": {
        "canonical": "PARROT",
        "aliases": ["PARROT SA", "PARROT DRONES", "PARROT INC"],
        "brand_tokens": {
            "ANAFI", "BEBOP", "DISCO", "PARROT DRONE", "PARROT UAS",
            "PARROT SEQUOIA",
        },
        "exclude_industry_tokens": {
            "RARE SPECIES", "CONSERVATORY", "WILDLIFE", "GAME AND FISH",
        },
        "exclude_form_tokens": set(),
        # Companies: Parrot Software LLC, Wright Tool Company, Kipper Tool
        # Company, Blue Parrot Offshore SL, J & L America Inc.
        "exclude_entity_tokens": {
            "PARROT SOFTWARE", "WRIGHT TOOL", "KIPPER TOOL", "BLUE PARROT",
            "J & L AMERICA",
        },
    },
    "Magnet": {
        "canonical": "MAGNET FORENSICS",
        "aliases": ["MAGNET FORENSICS INC", "MAGNET FORENSICS LLC"],
        "brand_tokens": {"MAGNET AXIOM", "MAGNET IEF", "MAGNET GRAYKEY", "MAGNET VERKEY"},
        "exclude_industry_tokens": {"MAGNETICS"},
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": {"MAGNET YOUR EVENT", "MAGNET SALES"},
    },
    "Skydio": {
        "canonical": "SKYDIO",
        "aliases": ["SKYDIO INC", "SKYDIO, INC"],
        "brand_tokens": {"SKYDIO X2", "SKYDIO 2", "SKYDIO R1", "SKYDIO X10"},
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "Getac": {
        "canonical": "GETAC",
        "aliases": ["GETAC INC", "GETAC TECHNOLOGY", "GETAC HOLDINGS"],
        "brand_tokens": {
            "GETAC S410", "GETAC B360", "GETAC K120", "GETAC V110",
            "GETAC F110", "GETAC T800",
        },
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "KeyW": {
        "canonical": "KEYW",
        "aliases": [
            "THE KEYW CORPORATION", "KEYW CORPORATION, THE", "KEYW HOLDING",
            "KEYW CORPORATION",
        ],
        "brand_tokens": set(),
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "Berla": {
        "canonical": "BERLA",
        "aliases": ["BERLA CORPORATION", "BERLA CORP"],
        "brand_tokens": {"IVEC", "BERLA IVE", "IVE VEHICLE FORENSIC"},
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "Rekor": {
        "canonical": "REKOR",
        "aliases": [
            "REKOR RECOGNITION SYSTEMS", "REKOR RECOGNITION SYSTEMS, INC.",
            "REKOR INC",
        ],
        "brand_tokens": {"REKOR", "REKOR RECOGNITION", "REKOR CARSPOTTER"},
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "BRINC": {
        "canonical": "BRINC",
        "aliases": ["BRINC DRONES INC", "BRINC DRONES, INC"],
        "brand_tokens": {"LEMUR", "BRINC BALL", "BRINC DRONE"},
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "Flock": {
        "canonical": "FLOCK SAFETY",
        "aliases": ["FLOCK SAFETY INC", "FLOCK GROUP"],
        "brand_tokens": {"FLOCK SAFETY", "FLOCK LP", "FLOCK ALPR"},
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": {"FLOCK OFF"},
    },
    "STOP": None,  # sentinel: not a registry vendor — common-word FP magnet
    "Lenel": {
        "canonical": "LENEL",
        "aliases": ["LENEL S2", "LENEL ONGUARD", "LENEL INTERNATIONAL"],
        "brand_tokens": {"LENEL", "ONGUARD", "LENEL S2"},
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "Lytx": {
        "canonical": "LYTX",
        "aliases": ["LYTX INC", "LYTX, INC.", "LYTX INC."],
        "brand_tokens": {"LYTX", "DC3", "DRIVE CAM"},
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
    "MSAB": {
        # cross-keyword tag helper (Berla+MSAB, Jacobs+MSAB)
        "canonical": "MSAB",
        "aliases": ["MSAB INCORPORATED", "MSAB INC", "MSAB"],
        "brand_tokens": {"XRY", "MSAB"},
        "exclude_industry_tokens": set(),
        "exclude_form_tokens": set(),
        "exclude_entity_tokens": set(),
    },
}


# Exclude-token classes, in CITE-PREFERENCE order. The rank is the point of the
# split: a cite that says *why* the vendor is excluded outranks one that says
# *which* entity it is, so 'NEURALACE MEDICAL, INC.' cites MEDICAL and not
# NEURALACE. Within a class the order is longest-first then lexicographic, so the
# whole order is still total and the artifact stays byte-reproducible.
#
# Each entry is (REGISTRY key, class name). The cite fragment per class is chosen
# by the RULE, because Rule 3 cites a vendor name and Rule 6 cites an excerpt and
# they word it differently; what they share is that the fragment must be TRUE of
# the token's own class. One label over three classes is the defect MAC-724 fixes.
_EXCLUDE_CLASSES: tuple[tuple[str, str], ...] = (
    ("exclude_industry_tokens", "industry"),
    ("exclude_form_tokens", "form"),
    ("exclude_entity_tokens", "entity"),
)

# Rule 3 — the token was found in the VENDOR NAME.
_RULE3_CITE: dict[str, str] = {
    "industry": "excluded industry for {keyword}",
    "form": "excluded entity form for {keyword}",
    "entity": "known false-positive entity for {keyword}",
}

# Rule 6 — the token was found in the description EXCERPT. The industry fragment
# is left at its pre-MAC-724 wording: it was already true of its class, and
# rewording it would churn rows this issue has no finding against.
_RULE6_CITE: dict[str, str] = {
    "industry": "different industry",
    "form": "excluded entity form for {keyword}",
    "entity": "known false-positive entity for {keyword}",
}

# Materialise the union back onto `exclude_tokens`. Readers outside this module
# (e.g. `operator_review/MAC-574/verify.py:168`) index that key directly, and the
# split must not break them. Derived, never hand-maintained: the union cannot
# drift from its parts.
for _entry in REGISTRY.values():
    if _entry is None or _entry.get("canonical") is None:
        continue
    _entry["exclude_tokens"] = frozenset().union(
        *(_entry[_set_name] for _set_name, _ in _EXCLUDE_CLASSES)
    )
del _entry


# Person-name suffix pattern: ", [SURNAME] [GIVEN-INITIAL]" — e.g., "AXON, GARY L".
# Legal suffixes (INC, LLC, LTD, CORP, etc.) are excluded to avoid false matches
# on vendor names like "AXIS COMMUNICATIONS, INC.".
_PERSON_NAME_RE = re.compile(r",\s+[A-Z][A-Z]+(?:\s+[A-Z])?\s*$")
_LEGAL_SUFFIX_TAIL_RE = re.compile(
    r",?\s*\b(INC|LLC|LTD|LP|CORP|CORPORATION|COMPANY|CO)\b\.?\s*\.?\s*$",
    re.IGNORECASE,
)

# Cache compiled word-boundary regexes (50-cluster use; sub-ms impact).
_WORD_BOUNDARY_RE_CACHE: dict[str, re.Pattern] = {}


def _word_boundary(token: str) -> re.Pattern:
    if token not in _WORD_BOUNDARY_RE_CACHE:
        _WORD_BOUNDARY_RE_CACHE[token] = re.compile(rf"\b{re.escape(token)}\b")
    return _WORD_BOUNDARY_RE_CACHE[token]


def _first_match_longest_then_lexical(tokens, haystack: str) -> Optional[str]:
    """Return the matching token under a total order of (-len, token).

    MAC-753. `brand_tokens` / `exclude_tokens` are `set`s, so a bare
    `for tok in tokens` scan returned an arbitrary member when several matched,
    varying with `PYTHONHASHSEED`. Every call site returns a fixed verdict
    literal regardless of which token matched, so the scan order never moved a
    KEEP/DROP — it only chose which of several true statements got cite-pasted
    into the evidence column. This makes that choice total and reproducible.

    MAC-756: the exclude-token call sites moved to `_ranked_exclude_tokens`,
    which ranks by CLASS before falling back to this same (-len, token) key.
    What is left here is `brand_tokens` (Rule 5), which is a single
    undifferentiated class — there is no class rank to apply, so length is the
    whole key and this name still describes the whole key.

    The sort key is literally `(-len(tok), tok)` — longest first, ties broken
    lexicographically — and the function is named after that key, not after the
    intent. The intent is "cite the most specific matching token". Length is a
    PROXY for specificity: exact when one token contains the other
    ('GLOBAL CONSULTING' > 'CONSULTING'), heuristic when two tokens match
    without containment ('SERVICES' vs 'PRI/DJI'). Where the proxy and real
    specificity diverge, the cost is a less apt citation, never a wrong verdict.

    Matching is case-insensitive on an already-uppercased `haystack`; the token
    is returned verbatim so the evidence string keeps the registry's own bytes.
    """
    for tok in sorted(tokens, key=lambda t: (-len(t.upper()), t.upper())):
        if tok.upper() in haystack:
            return tok
    return None


def _ranked_exclude_tokens(key: dict) -> list[tuple[str, str]]:
    """Exclude tokens as (token, class), sorted on `(class rank, -len, token)`.

    Class rank first (industry > form > entity), then longest-first, then
    lexicographic. Total, so the artifact is byte-reproducible under any
    PYTHONHASHSEED — the invariant MAC-753 established, preserved here because
    the class rank is a strict PREFIX of the old sort key, not a replacement for
    it. Determinism is untouched; only the tie-ordering above it is new.

    Ranking by class is what makes the cite explanatory rather than merely
    reproducible. 'NEURALACE MEDICAL, INC.' matches both MEDICAL (industry) and
    NEURALACE (entity); longest-first alone picked NEURALACE, trading the token
    that explains the exclusion for the one that merely identifies the vendor.
    Entity names run LONGER than industry words, so the flat length proxy was
    biased toward exactly the tokens that are not industries (MAC-756).
    """
    ranked = [
        (rank, tok, cls)
        for rank, (set_name, cls) in enumerate(_EXCLUDE_CLASSES)
        for tok in key[set_name]
    ]
    ranked.sort(key=lambda r: (r[0], -len(r[1]), r[1]))
    return [(tok, cls) for _rank, tok, cls in ranked]


def adjudicate_cluster(
    keyword: str,
    vendor_canonical_name: str,
    basis: str = "vendor",
    sample_excerpt: Optional[str] = None,
) -> Tuple[Verdict, str]:
    """Return (verdict, evidence) for a T2 cluster.

    See module docstring for verdict rules. Pure function: same inputs produce
    the same output. Cite-paste the returned `evidence` string in the
    adjudication TSV.
    """
    # Cross-keyword: split on "+" and adjudicate per sub-keyword.
    if "+" in keyword:
        sub_keywords = [k.strip() for k in keyword.split("+")]
        verdicts = [
            adjudicate_cluster(sk, vendor_canonical_name, basis, sample_excerpt)
            for sk in sub_keywords
        ]
        if any(v == "KEEP" for v, _ in verdicts):
            for _, ev in verdicts:
                pass
            kept_ev = next(ev for v, ev in verdicts if v == "KEEP")
            return (
                "KEEP",
                f"cross-keyword cluster {keyword!r}; one sub-keyword yields KEEP: {kept_ev}",
            )
        if all(v == "DROP" for v, _ in verdicts):
            reasons = "; ".join(ev for _, ev in verdicts)
            return (
                "DROP",
                f"cross-keyword cluster {keyword!r}; all sub-keywords DROP: {reasons}",
            )
        return (
            "UNRESOLVED",
            f"cross-keyword cluster {keyword!r}; mixed verdicts: {verdicts}",
        )

    key = REGISTRY.get(keyword)
    if key is None:
        return ("DROP", f"keyword '{keyword}' not in registry map — FP")
    if key.get("canonical") is None:
        return (
            "DROP",
            f"keyword '{keyword}' is a non-registry FP magnet — all matches are FPs",
        )

    vendor_upper = (vendor_canonical_name or "").upper()
    aliases = {a.upper() for a in key["aliases"]}

    # Rule 1: exact alias match → KEEP. Membership, not a scan: an equality
    # test can match at most one distinct string, so this is order-free.
    if vendor_upper in aliases:
        return ("KEEP", f"vendor name == registry alias '{vendor_upper}'")

    # Rule 2: person-name suffix → DROP (only if not also a corporate suffix)
    if _PERSON_NAME_RE.search(vendor_upper) and not _LEGAL_SUFFIX_TAIL_RE.search(
        vendor_upper
    ):
        return (
            "DROP",
            "vendor name matches person-suffix pattern (surname, given-initial)",
        )

    # Rule 3: exclude-token in vendor name → DROP
    #
    # MAC-724: the cite used to say "(excluded industry for X)" over every token
    # in the set, and the set was never all industries — 'DEREK J HARRIS' is a
    # person, 'OTTO BOCK' and 'M. C. DEAN' are companies, 'JV' is a legal form.
    # The verdict was right in every case and stays right; the SENTENCE was false
    # about what it had matched, on a third of the 40 rows carrying that label.
    # The token now carries its class, the class picks the wording, and class
    # outranks length — so a vendor matching both an industry token and an entity
    # token cites the industry, which is the half that explains the DROP.
    for tok, cls in _ranked_exclude_tokens(key):
        if tok.upper() in vendor_upper:
            return (
                "DROP",
                f"vendor name contains '{tok}' "
                f"({_RULE3_CITE[cls].format(keyword=keyword)})",
            )

    # Rule 4: canonical-token as whole word / contiguous sublist → KEEP
    canonical_token = key["canonical"].upper()
    canonical_tokens = canonical_token.split()
    vendor_tokens = vendor_upper.split()
    if len(canonical_tokens) == 1:
        if _word_boundary(canonical_tokens[0]).search(vendor_upper):
            return (
                "KEEP",
                f"vendor name contains registry canonical '{canonical_tokens[0]}' as whole word",
            )
    else:
        if any(
            vendor_tokens[i : i + len(canonical_tokens)] == canonical_tokens
            for i in range(len(vendor_tokens) - len(canonical_tokens) + 1)
        ):
            return (
                "KEEP",
                f"vendor name contains registry canonical '{canonical_token}' as contiguous token sequence",
            )

    # Rule 5/6/7: description-basis logic
    if basis == "description":
        excerpt = (sample_excerpt or "").upper()
        # Rule 6: exclude-token in excerpt → DROP
        #
        # MAC-724: "(different industry)" carried the same false class claim as
        # Rule 3's label — same defect, different wording, 5 more rows. Classed
        # the same way. The industry fragment is unchanged, so an industry-class
        # row here is byte-identical to its pre-MAC-724 cite.
        for tok, cls in _ranked_exclude_tokens(key):
            if tok.upper() in excerpt:
                return (
                    "DROP",
                    f"description excerpt contains '{tok}' "
                    f"({_RULE6_CITE[cls].format(keyword=keyword)})",
                )
        # Rule 5: brand-token in excerpt → KEEP (reseller selling the real product)
        tok = _first_match_longest_then_lexical(key["brand_tokens"], excerpt)
        if tok is not None:
            return (
                "KEEP",
                f"description excerpt contains '{tok}' (registry product marker for {keyword})",
            )
        # Rule 7: vendor-name exclude-token still applies.
        # This cite makes no class claim, so MAC-724 leaves its wording alone and
        # only routes the iteration through the class-ranked order. Rule 7 is
        # UNREACHABLE — it re-tests Rule 3's exact predicate later in the same
        # function — and is kept ordered anyway.
        for tok, _cls in _ranked_exclude_tokens(key):
            if tok.upper() in vendor_upper:
                return (
                    "DROP",
                    f"description-basis but vendor name contains '{tok}'",
                )
        # Rule 7 fallback: KEEP (reseller-of-registry-product default per MAC-542 §3)
        return (
            "KEEP",
            "description-basis with generic excerpt; reseller-of-registry-product default per MAC-542 §3",
        )

    # Rule 8: vendor-basis, no rule fired
    return (
        "UNRESOLVED",
        f"vendor name '{vendor_canonical_name}' does not match any KEEP / DROP rule for keyword '{keyword}'",
    )


# Short, single-token, common-English-word reference set. The named STOP magnet
# is one member; per the issue spec, this is the screen for the 148-canonical
# visible universe (any other short canonical in this set is a candidate for
# `query_default` demotion).
_SHORT_COMMON_ENGLISH: frozenset[str] = frozenset({
    # function words
    "A", "I", "AN", "AS", "AT", "BE", "BY", "DO", "GO", "HE", "IF", "IN", "IS",
    "IT", "ME", "MY", "NO", "OF", "OH", "OK", "ON", "OR", "SO", "TO", "UP",
    "US", "WE",
    # common verbs / nouns / adjectives
    "STOP", "RUN", "SET", "GET", "HIT", "LET", "SAY", "TRY", "SEE", "USE",
    "NEW", "OLD", "BIG", "LOW", "TOP", "MAN", "WAY", "DAY", "ALL", "ANY",
    "ONE", "TWO", "TEN", "OUT", "OFF", "NOW", "YES", "RED", "END", "ASK",
    "ARM", "ART", "BAD", "BED", "BOX", "BUS", "CAR", "CAT", "CUP", "CUT",
    "DIE", "DOG", "DRY", "EAR", "EAT", "EGG", "EYE", "FAR", "FEW", "FLY",
    "FOR", "FUN", "GUN", "HAD", "HAS", "HAT", "HER", "HIM", "HIS", "HOT",
    "HOW", "ICE", "ITS", "JOB", "JOY", "KEY", "LAW", "LED", "LEG", "LIE",
    "LOG", "LOT", "MAD", "MAP", "MAY", "MIX", "NET", "NOR", "NOT", "ODD",
    "OIL", "OWN", "PAY", "PEN", "PET", "PIE", "PIG", "PIN", "POP", "POT",
    "PUB", "PUT", "RAN", "RAT", "RAW", "RID", "ROD", "ROW", "RUB", "SAD",
    "SAT", "SAW", "SEA", "SIT", "SKI", "SKY", "SON", "SUN", "TAX", "TEA",
    "THE", "TIE", "TIN", "TIP", "TOE", "TOO", "TOY", "TUB", "WAR", "WET",
    "WIN", "WON", "YET", "YOU", "ZAP", "ZIP", "ZOO",
    # surveillance-industry common-vocab tokens
    "REVEAL", "WATCH", "TRACE", "TRACK", "SCAN", "VIEW", "CAPTURE", "ALERT",
    "AIM", "SPOT", "CLEAR",
})


def is_common_word_canonical(canonical: str) -> bool:
    """Predicate: True if a manufacturer canonical is a common English word (FP magnet).

    The named STOP magnet is one member. This predicate answers 'is this short
    single-token canonical a common English word, and therefore at risk of
    producing boundary-valid-but-wrong-identity matches?'.

    Per MAC-527, sole-identifier vendors get refined (query_default='hidden' +
    an override keyword) rather than dropped.
    """
    if not canonical:
        return False
    parts = canonical.strip().split()
    if len(parts) > 1:
        return False
    token = parts[0]
    if len(token) > 6:
        return False
    return token.upper() in _SHORT_COMMON_ENGLISH
