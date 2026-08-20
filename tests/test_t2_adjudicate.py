"""MAC-546 T2 — tests for the short-keyword procurement cluster adjudication
predicates. Adjudicates 394 (keyword, vendor) clusters that pass the entity-
boundary check but fail the identity check (per MAC-542 §5 + §6a).

Iron law: these tests are written FIRST, then the predicate module is written
to satisfy them. Do not edit the predicate module to "match" the tests — the
tests encode the issue spec.
"""
from __future__ import annotations

import sys
from pathlib import Path

# `operator_review/MAC-542/` is not a regular Python package (hyphens in path).
# Add it to sys.path so the predicate module can be imported by name.
_T2_DIR = Path(__file__).resolve().parents[1] / "operator_review" / "MAC-542"
sys.path.insert(0, str(_T2_DIR))

import t2_adjudicate  # noqa: E402


# ---- DJI: construction joint ventures ------------------------------------


def test_drop_dji_construction_services_jv() -> None:
    v, ev = t2_adjudicate.adjudicate_cluster("DJI", "PRI/DJI, A SERVICES JV")
    assert v == "DROP"
    assert "JV" in ev.upper() or "CONSTRUCTION" in ev.upper()


def test_drop_dji_construction_reconstruction_jv() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("DJI", "PRI-DJI A CONSTRUCTION JV")
    assert v == "DROP"


def test_drop_dji_reconstruction_jv() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("DJI", "PRI/DJI A RECONSTRUCTION JV")
    assert v == "DROP"


def test_drop_dji_kmk_jv() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("DJI", "KMK-DJI JV")
    assert v == "DROP"


# ---- Axis: not Axis Communications ---------------------------------------


def test_drop_axis_prosthetics_and_orthotics() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Axis", "AXIS PROSTHETICS AND ORTHOTICS"
    )
    assert v == "DROP"


def test_drop_axis_forensic_toxicology() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Axis", "AXIS FORENSIC TOXICOLOGY"
    )
    assert v == "DROP"


def test_drop_axis_management_group() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Axis", "AXIS MANAGEMENT GROUP")
    assert v == "DROP"


def test_drop_axis_fastening_systems() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Axis", "AXIS FASTENING SYSTEMS"
    )
    assert v == "DROP"


# ---- Axon: "axon" is also a nerve fibre ---------------------------------


def test_drop_axon_medical() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Axon", "AXON MEDICAL INC")
    assert v == "DROP"


def test_drop_axon_cable() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Axon", "AXON CABLE INC")
    assert v == "DROP"


def test_drop_axon_person_gary_l() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Axon", "AXON, GARY L")
    assert v == "DROP"


def test_drop_neuralace_medical_therapy_system() -> None:
    # Description-basis cluster; excerpt shows the word "AXON" but refers to
    # an "AXON THERAPY SYSTEM" medical device, NOT Axon Enterprise TASER.
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Axon",
        "NEURALACE MEDICAL, INC.",
        basis="description",
        sample_excerpt="AXON THERAPY SYSTEM NEURALACE",
    )
    assert v == "DROP"


def test_drop_axon_the_axon_group_ltd() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Axon", "THE AXON GROUP, LTD")
    assert v == "DROP"


def test_drop_axon_otto_bock_prosthetic() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Axon",
        "OTTO BOCK HEALTHCARE LP",
        basis="description",
        sample_excerpt="AXON PROSTHETIC DEVICE",
    )
    assert v == "DROP"


# ---- DRT: not Digital Receiver Technology --------------------------------


def test_drop_drt_strategies() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("DRT", "DRT STRATEGIES")
    assert v == "DROP"


# ---- Reveal: 0 of 66 are Reveal Media -----------------------------------


def test_drop_reveal_global_consulting() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Reveal", "REVEAL GLOBAL CONSULTING LLC"
    )
    assert v == "DROP"


def test_drop_reveal_biosciences() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Reveal", "REVEAL BIOSCIENCES INC")
    assert v == "DROP"


def test_drop_reveal_imaging_technologies() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Reveal", "REVEAL IMAGING TECHNOLOGIES, INC."
    )
    assert v == "DROP"


def test_keep_reveal_media_usa() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Reveal", "REVEAL MEDIA USA INC")
    assert v == "KEEP"


# ---- Parrot: actual parrots ----------------------------------------------


def test_drop_parrot_software() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Parrot", "PARROT SOFTWARE LLC")
    assert v == "DROP"


def test_drop_parrot_rare_species_conservatory() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Parrot", "RARE SPECIES CONSERVATORY FOUNDATION, INC."
    )
    assert v == "DROP"


def test_drop_parrot_wright_tool() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Parrot", "WRIGHT TOOL COMPANY, LLC"
    )
    assert v == "DROP"


# ---- Magnet: not Magnet Forensics ----------------------------------------


def test_drop_magnet_a_l_l_magnetics() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Magnet", "A-L-L MAGNETICS")
    assert v == "DROP"


def test_drop_magnet_your_event() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Magnet", "MAGNET YOUR EVENT LLC")
    assert v == "DROP"


# ---- KEEPs (named in issue spec) -----------------------------------------


def test_keep_harris_corporation() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Harris", "HARRIS CORPORATION")
    assert v == "KEEP"


def test_keep_axon_enterprise() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Axon", "AXON ENTERPRISE, INC."
    )
    assert v == "KEEP"


def test_keep_berla_corporation() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Berla", "BERLA CORPORATION")
    assert v == "KEEP"


def test_keep_skydio_inc() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Skydio", "SKYDIO, INC")
    assert v == "KEEP"


def test_keep_rekor_recognition_systems() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Rekor", "REKOR RECOGNITION SYSTEMS, INC."
    )
    assert v == "KEEP"


def test_keep_keyw_corporation() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("KeyW", "THE KEYW CORPORATION")
    assert v == "KEEP"


def test_keep_getac_inc() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("Getac", "GETAC INC")
    assert v == "KEEP"


def test_keep_brinc_drones() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster("BRINC", "BRINC DRONES, INC")
    assert v == "KEEP"


def test_keep_jacobs_engineering() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Jacobs", "JACOBS ENGINEERING GROUP INC."
    )
    assert v == "KEEP"


# ---- Description-basis resellers (issue: KEEP these) --------------------


def test_keep_atlantic_diving_supply_for_skydio() -> None:
    # reseller matched via description; the product IS Skydio
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Skydio",
        "ATLANTIC DIVING SUPPLY, INC.",
        basis="description",
        sample_excerpt="SKYDIO X2 DRONE SYSTEM",
    )
    assert v == "KEEP"


def test_keep_cdw_for_getac() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Getac",
        "CDW GOVERNMENT LLC",
        basis="description",
        sample_excerpt="GETAC S410 RUGGED LAPTOP",
    )
    assert v == "KEEP"


def test_keep_shi_for_getac() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Getac",
        "SHI INTERNATIONAL CORP",
        basis="description",
        sample_excerpt="GETAC K120 TABLET",
    )
    assert v == "KEEP"


# ---- STOP FP magnet: NO registry vendor ---------------------------------


def test_stop_keyword_cluster_is_drop_unconditionally() -> None:
    # STOP is not a registry vendor; any cluster matching it is a false positive.
    v, _ = t2_adjudicate.adjudicate_cluster(
        "STOP", "STOP ONE", basis="vendor"
    )
    assert v == "DROP"


def test_stop_description_basis_faxon_is_drop() -> None:
    # Cluster id=87504: FAXON ENGINEERING CO INC, excerpt "8510571523!VALVE,STOP-CHECK"
    v, _ = t2_adjudicate.adjudicate_cluster(
        "STOP",
        "FAXON ENGINEERING CO INC",
        basis="description",
        sample_excerpt="8510571523!VALVE,STOP-CHECK",
    )
    assert v == "DROP"


def test_stop_description_basis_hanwha_is_drop() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "STOP",
        "HANWHA 63 CITY CO., LTD.",
        basis="description",
        sample_excerpt="IGF::OT::IGF-BASE MAINTENANCE SERVICE - TOP COAT MATERIALS ONTO HYDRO-STOP TREATED ROOF SURFACE",
    )
    assert v == "DROP"


# ---- Cross-keyword clusters (Berla+MSAB, Harris+KeyW, Jacobs+MSAB) -----


def test_cross_keyword_msab_inc_is_keep() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Berla+MSAB", "MSAB INCORPORATED", basis="vendor"
    )
    assert v == "KEEP"


def test_cross_keyword_keyw_corp_is_keep() -> None:
    v, _ = t2_adjudicate.adjudicate_cluster(
        "Harris+KeyW", "THE KEYW CORPORATION", basis="vendor"
    )
    assert v == "KEEP"


# ---- Predicate: is_common_word_canonical --------------------------------


def test_stop_is_common_word_canonical() -> None:
    assert t2_adjudicate.is_common_word_canonical("STOP") is True


def test_reveal_is_common_word_canonical() -> None:
    # "Reveal" is a common English word AND a 6-char single-token canonical.
    assert t2_adjudicate.is_common_word_canonical("Reveal") is True


def test_harris_is_not_common_word_canonical() -> None:
    # Proper noun, not in the short-vocab set.
    assert t2_adjudicate.is_common_word_canonical("Harris") is False


def test_axon_is_not_common_word_canonical() -> None:
    # Biology term but not a common English vocabulary word.
    assert t2_adjudicate.is_common_word_canonical("Axon") is False


def test_wolfcom_is_not_common_word_canonical() -> None:
    # Multi-token and proper-noun.
    assert t2_adjudicate.is_common_word_canonical("Wolfcom") is False


def test_multi_token_canonical_is_not_common_word() -> None:
    # "Flock Safety" is multi-token → not a common-word canonical (no boundary issue
    # at the keyword level; the canonical itself isn't an FP magnet).
    assert t2_adjudicate.is_common_word_canonical("Flock Safety") is False


def test_long_canonical_is_not_common_word() -> None:
    # "Hanwha Vision" — 14 chars total, multi-token.
    assert t2_adjudicate.is_common_word_canonical("Hanwha Vision") is False


def test_empty_canonical_is_not_common_word() -> None:
    assert t2_adjudicate.is_common_word_canonical("") is False


def test_already_lowercase_stop_is_common_word_canonical() -> None:
    assert t2_adjudicate.is_common_word_canonical("stop") is True


# ---- MAC-753: the multi-match tiebreak is a total order ------------------
#
# `exclude_tokens` / `brand_tokens` are sets. When several members matched, the
# bare iteration that used to back these rules returned an arbitrary one, so the
# cite-pasted evidence string moved with PYTHONHASHSEED. These pin the order.


def test_multi_match_exclude_token_cites_the_longest_match() -> None:
    # "PRI/DJI, A SERVICES JV" matches four DJI exclude tokens at once:
    # 'A SERVICES JV', 'SERVICES', 'PRI/DJI', 'JV'. The longest wins.
    _, ev = t2_adjudicate.adjudicate_cluster("DJI", "PRI/DJI, A SERVICES JV")
    assert "'A SERVICES JV'" in ev


def test_multi_match_exclude_token_prefers_specific_over_substring() -> None:
    # 'BIOSCIENCES' and 'BIOSCIENCE' both match; the longer is the apter cite.
    _, ev = t2_adjudicate.adjudicate_cluster("Reveal", "REVEAL BIOSCIENCES INC")
    assert "'BIOSCIENCES'" in ev


def test_tiebreak_helper_orders_by_length_then_lexically() -> None:
    tokens = {"JV", "SERVICES", "A SERVICES JV", "PRI/DJI"}
    got = t2_adjudicate._first_match_longest_then_lexical(
        tokens, "PRI/DJI, A SERVICES JV"
    )
    assert got == "A SERVICES JV"
    # Equal length → lexicographic, so the result never depends on set order.
    assert t2_adjudicate._first_match_longest_then_lexical(
        {"BBB", "AAA"}, "XX AAA BBB XX"
    ) == "AAA"
    assert t2_adjudicate._first_match_longest_then_lexical({"ZZZ"}, "NOPE") is None


def test_verdict_is_invariant_to_which_token_matched() -> None:
    # The point of the tiebreak: it selects the citation, never the verdict.
    # Every one of these matches a different number of exclude tokens.
    for vendor in (
        "PRI/DJI, A SERVICES JV",
        "PRI-DJI A CONSTRUCTION JV",
        "PRI/DJI A RECONSTRUCTION JV",
        "KMK-DJI JV",
    ):
        assert t2_adjudicate.adjudicate_cluster("DJI", vendor)[0] == "DROP"


# ---- MAC-724 (ported by MAC-756): the exclude-token set was three classes
# ---- under one label ------------------------------------------------------
#
# Rule 3 cited every token it matched as "(excluded industry for X)". The set was
# never all industries: DEREK J HARRIS is a person, OTTO BOCK / MOLECULAR DEVICES
# / M. C. DEAN / NEURALACE / TELECOMM1STOP are companies, KMK-DJI is a named joint
# venture, JV is a legal form. Every verdict was and stays DROP; the SENTENCE was
# false about what it had matched, on 40 rows under Rule 3's label plus 5 more
# under Rule 6's "(different industry)".
#
# MAC-724 fixed this on `v1.8.0-stage`, which never reached the release line;
# MAC-753 then independently re-derived a FLAT (-len, token) order on `main`.
# Entity names are systematically longer than industry words, so the flat proxy
# promoted exactly the tokens that are not industries. MAC-756 ports the class
# rank onto `main`.
#
# The split is guarded in both directions against a frozen literal of the sets as
# they stood at c9f7e44 (`main`, pre-port) — verified equal to `v1.8.0-stage`'s
# own pre-split literal at 503ed1c. A reclassification that silently drops a token
# would change verdicts while looking like a relabel, so set identity is the first
# control, not an afterthought.

_PRE_MAC724_EXCLUDE_TOKENS: dict[str, frozenset[str]] = {
    "Harris": frozenset({
        "COMPUTER CORPORATION", "CONSULTING", "DEREK J HARRIS",
        "FIRE PROTECTION", "PROPERTIES LLC", "PRYOR", "PRYOR MCGINNIS",
        "TELECOMM1STOP"
    }),
    "Jacobs": frozenset({"CATERING", "ENTERPRISE MANAGEMENT", "TELEPHONE CONTRACTORS"}),
    "DJI": frozenset({
        "A CONSTRUCTION JV", "A RECONSTRUCTION JV", "A SERVICES JV",
        "CONSTRUCTION", "JOINT VENTURE", "JV", "KMK-DJI", "PRI-DJI",
        "PRI/DJI", "RECONSTRUCTION", "SERVICES"
    }),
    "Axon": frozenset({
        "AXON GROUP", "CABLE", "FORENSIC TOXICOLOGY", "M. C. DEAN",
        "MEDICAL", "MOLECULAR DEVICES", "NEURALACE", "ORTHOTIC", "OTTO BOCK",
        "PROSTHETIC", "THERAPY"
    }),
    "Axis": frozenset({
        "FASTENING", "FORENSIC TOXICOLOGY", "MANAGEMENT GROUP", "ORTHOTIC",
        "PROSTHETIC"
    }),
    "DRT": frozenset({"BURYCHKA DRT", "DRT, LLC", "STRATEGIES"}),
    "Reveal": frozenset({
        "BIOSCIENCE", "BIOSCIENCES", "CONSULTING", "GLOBAL CONSULTING",
        "IMAGING TECHNOLOGIES", "REVEAL TECHNOLOGY"
    }),
    "Parrot": frozenset({
        "BLUE PARROT", "CONSERVATORY", "GAME AND FISH", "J & L AMERICA",
        "KIPPER TOOL", "PARROT SOFTWARE", "RARE SPECIES", "WILDLIFE",
        "WRIGHT TOOL"
    }),
    "Magnet": frozenset({"MAGNET SALES", "MAGNET YOUR EVENT", "MAGNETICS"}),
    "Skydio": frozenset(),
    "Getac": frozenset(),
    "KeyW": frozenset(),
    "Berla": frozenset(),
    "Rekor": frozenset(),
    "BRINC": frozenset(),
    "Flock": frozenset({"FLOCK OFF"}),
    "Lenel": frozenset(),
    "Lytx": frozenset(),
    "MSAB": frozenset(),
}


def _live_registry_entries() -> list[tuple[str, dict]]:
    return [
        (kw, e)
        for kw, e in t2_adjudicate.REGISTRY.items()
        if e is not None and e.get("canonical") is not None
    ]


def test_split_covers_every_registry_keyword() -> None:
    """The frozen literal must name every live keyword, or a keyword could be
    reclassified with no control watching it at all."""
    live = {kw for kw, _ in _live_registry_entries()}
    assert live == set(_PRE_MAC724_EXCLUDE_TOKENS)


def test_split_is_set_identical_to_the_pre_split_set_per_keyword() -> None:
    """Both directions, per keyword: nothing lost, nothing invented."""
    for kw, entry in _live_registry_entries():
        before = _PRE_MAC724_EXCLUDE_TOKENS[kw]
        after = (
            set(entry["exclude_industry_tokens"])
            | set(entry["exclude_form_tokens"])
            | set(entry["exclude_entity_tokens"])
        )
        assert after - before == set(), f"{kw}: invented {sorted(after - before)}"
        assert before - after == set(), f"{kw}: dropped {sorted(before - after)}"


def test_split_classes_are_pairwise_disjoint() -> None:
    """A token in two classes makes its cite class ambiguous and its rank
    dependent on which set is visited first."""
    for kw, entry in _live_registry_entries():
        i = set(entry["exclude_industry_tokens"])
        f = set(entry["exclude_form_tokens"])
        e = set(entry["exclude_entity_tokens"])
        assert i & f == set(), f"{kw}: industry/form overlap {sorted(i & f)}"
        assert i & e == set(), f"{kw}: industry/entity overlap {sorted(i & e)}"
        assert f & e == set(), f"{kw}: form/entity overlap {sorted(f & e)}"


def test_derived_exclude_tokens_key_still_matches_the_pre_split_set() -> None:
    """`operator_review/MAC-574/verify.py:168` indexes `exclude_tokens` directly.
    The split must not break that reader."""
    for kw, entry in _live_registry_entries():
        assert set(entry["exclude_tokens"]) == set(_PRE_MAC724_EXCLUDE_TOKENS[kw])


def test_ranked_exclude_tokens_puts_class_before_length() -> None:
    """The whole point of the split: class rank is a strict PREFIX of the old
    sort key, so the order stays total and the artifact stays reproducible."""
    ranked = t2_adjudicate._ranked_exclude_tokens(t2_adjudicate.REGISTRY["Axon"])
    classes = [cls for _tok, cls in ranked]
    assert classes == sorted(classes, key=lambda c: ["industry", "form", "entity"].index(c))
    # Within a class, longest-first then lexicographic.
    industry = [tok for tok, cls in ranked if cls == "industry"]
    assert industry == sorted(industry, key=lambda t: (-len(t), t))
    # NEURALACE (9) is longer than MEDICAL (7) but is an entity, so it ranks below.
    assert industry[-1] == "CABLE"
    assert ranked[-1][1] == "entity"


def test_rule3_industry_token_outranks_a_longer_entity_token() -> None:
    """NEURALACE MEDICAL, INC. matches MEDICAL (industry, 7) and NEURALACE
    (entity, 9). Longest-first alone cited NEURALACE — which entity it is, not
    why it is excluded."""
    v, ev = t2_adjudicate.adjudicate_cluster("Axon", "NEURALACE MEDICAL, INC.")
    assert v == "DROP"
    assert ev == "vendor name contains 'MEDICAL' (excluded industry for Axon)"


def test_rule3_industry_token_outranks_a_longer_entity_token_harris() -> None:
    """PRYOR MCGINNIS CONSULTING matches CONSULTING (industry, 10) and
    PRYOR MCGINNIS (entity, 14)."""
    v, ev = t2_adjudicate.adjudicate_cluster("Harris", "PRYOR MCGINNIS CONSULTING")
    assert v == "DROP"
    assert ev == "vendor name contains 'CONSULTING' (excluded industry for Harris)"


def test_rule3_entity_only_match_is_cited_as_an_entity_not_an_industry() -> None:
    """A person is not an industry. This is the cite MAC-724 found."""
    v, ev = t2_adjudicate.adjudicate_cluster("Harris", "DEREK J HARRIS")
    assert v == "DROP"
    assert ev == (
        "vendor name contains 'DEREK J HARRIS' "
        "(known false-positive entity for Harris)"
    )
    assert "industry" not in ev


def test_rule3_form_only_match_is_cited_as_a_form_not_an_industry() -> None:
    """KMK-DJI JV matches no industry token at all: JV is a form and KMK-DJI is a
    named entity. Form outranks entity, so the cite says why, and 'JV' is never
    called an industry."""
    v, ev = t2_adjudicate.adjudicate_cluster("DJI", "KMK-DJI JV")
    assert v == "DROP"
    assert ev == "vendor name contains 'JV' (excluded entity form for DJI)"
    assert "industry" not in ev


def test_rule3_industry_bearing_jv_token_still_wins_over_bare_jv() -> None:
    """'A SERVICES JV' names a line of business and stays in the industry class,
    so the more specific cite is preserved, not undone."""
    v, ev = t2_adjudicate.adjudicate_cluster("DJI", "PRI/DJI, A SERVICES JV")
    assert v == "DROP"
    assert ev == "vendor name contains 'A SERVICES JV' (excluded industry for DJI)"


def test_rule6_industry_cite_wording_is_unchanged() -> None:
    """Rule 6's industry fragment is deliberately byte-identical to its
    pre-MAC-724 wording — it was already true of its class."""
    v, ev = t2_adjudicate.adjudicate_cluster(
        "DJI", "FLORIDA DRONE SUPPLY, INC.", basis="description",
        sample_excerpt="PRIME CONTRACT, A SERVICES JV AWARD",
    )
    assert v == "DROP"
    assert ev == "description excerpt contains 'A SERVICES JV' (different industry)"


def test_rule6_entity_token_is_not_cited_as_a_different_industry() -> None:
    """Same defect as Rule 3, different wording. An excerpt naming Otto Bock is
    not evidence of a 'different industry' — it is evidence of a known FP entity.
    The vendor carries no exclude token, so Rule 3 cannot pre-empt Rule 6."""
    v, ev = t2_adjudicate.adjudicate_cluster(
        "Axon", "FLORIDA SUPPLY, INC.", basis="description",
        sample_excerpt="RESALE OF OTTO BOCK LIMB COMPONENTS",
    )
    assert v == "DROP"
    assert ev == (
        "description excerpt contains 'OTTO BOCK' "
        "(known false-positive entity for Axon)"
    )
    assert "industry" not in ev


def test_every_exclude_class_cite_names_its_own_class() -> None:
    """Mechanical, over every token in every class: the emitted cite must carry
    the fragment for the class the token is actually in, and must not carry any
    other class's fragment. This is the control that the label is true of the
    set it describes — the thing MAC-724 found was false."""
    fragments = {
        "industry": "excluded industry for",
        "form": "excluded entity form for",
        "entity": "known false-positive entity for",
    }
    checked = 0
    for kw, entry in _live_registry_entries():
        for tok, cls in t2_adjudicate._ranked_exclude_tokens(entry):
            _v, ev = t2_adjudicate.adjudicate_cluster(kw, tok)
            if not ev.startswith("vendor name contains "):
                # A higher-priority rule (alias equality, person-suffix) or a
                # higher-ranked token pre-empted; not this control's business.
                continue
            if f"'{tok}'" not in ev:
                continue
            assert fragments[cls] in ev, f"{kw}/{tok}: class {cls} not cited in {ev!r}"
            for other, frag in fragments.items():
                if other != cls:
                    assert frag not in ev, f"{kw}/{tok}: wrong class {other} in {ev!r}"
            checked += 1
    # Non-vacuity: an empty sweep would pass silently.
    assert checked >= 40, f"control swept only {checked} tokens"


# ---- MAC-722 (ported by MAC-758): Rule 5's brand_tokens scan ---------------
#
# MAC-753 made every substring-matched set scan total, and MAC-756 put a class
# rank in front of the exclude-token scans. Both are covered above — but every
# one of those tests enters through `_ranked_exclude_tokens`, i.e. Rule 3 or
# Rule 6. Rule 5 reads `brand_tokens`, a single undifferentiated class that has
# no class rank to apply and therefore no `_ranked_exclude_tokens` test to ride
# on. It is the one substring-matched scan with no cite-order coverage.
#
# That gap is not hypothetical. MAC-722 measured the generator over all 394
# clusters under 12 PYTHONHASHSEEDs and found exactly three rows still moving
# after MAC-719's Rule 3 fix, and all three were Rule 5 `brand_tokens`:
# Berla BERLA IVE vs IVE VEHICLE FORENSIC, DJI MAVIC vs PHANTOM, Getac
# GETAC B360 vs GETAC F110. The t2 suite was green under all 12 seeds the whole
# time, because no test in it reached a multi-token match on a description-basis
# brand rule. These are those three rows, as tests.
#
# Each case matches at least TWO registry brand tokens and pins the one the
# documented order selects (-len, then lexicographic). The verdict is asserted
# alongside the cite to keep the MAC-753 invariant visible: the scan order
# chooses the citation, never the KEEP/DROP.


def test_rule5_brand_token_cite_is_the_longest_match_dji() -> None:
    # Excerpt matches brand tokens MAVIC (5) and PHANTOM (7).
    v, ev = t2_adjudicate.adjudicate_cluster(
        "DJI", "FLORIDA DRONE SUPPLY, INC.", basis="description",
        sample_excerpt="QUADCOPTER AIRFRAME KIT, MAVIC AND PHANTOM SERIES",
    )
    assert v == "KEEP"
    assert ev == "description excerpt contains 'PHANTOM' (registry product marker for DJI)"
    assert "MAVIC" not in ev


def test_rule5_brand_token_cite_is_the_longest_match_getac() -> None:
    # GETAC B360 and GETAC F110 are both 10 chars — the lexicographic tiebreak
    # is what makes this total rather than merely length-ordered. This is the
    # equal-length case for `brand_tokens` specifically; MAC-753's helper test
    # covers equal length only on a synthetic {"AAA", "BBB"} pair.
    v, ev = t2_adjudicate.adjudicate_cluster(
        "Getac", "GOVCONNECTION INC", basis="description",
        sample_excerpt="RUGGED TABLETS: GETAC B360 AND GETAC F110",
    )
    assert v == "KEEP"
    assert ev == (
        "description excerpt contains 'GETAC B360' (registry product marker for Getac)"
    )


def test_rule5_brand_token_cite_is_the_longest_match_berla() -> None:
    # One excerpt matching BERLA IVE (9) and IVE VEHICLE FORENSIC (20).
    v, ev = t2_adjudicate.adjudicate_cluster(
        "Berla", "AUGUST SCHELL ENTERPRISES, INC.", basis="description",
        sample_excerpt="BERLA IVE VEHICLE FORENSIC KIT",
    )
    assert v == "KEEP"
    assert ev == (
        "description excerpt contains 'IVE VEHICLE FORENSIC' "
        "(registry product marker for Berla)"
    )
