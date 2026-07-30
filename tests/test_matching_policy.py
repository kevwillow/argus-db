"""MAC-577 — tests for db/matching_policy.py.

Two jobs:
  1. Pin the policy sets against the MAC-542 screen of record so the two
     cannot drift (the issue's rule: reuse that screen, do not redo it).
  2. Pin the measured behaviour, so a future edit that quietly re-widens the
     matcher or drops a real vendor fails here instead of in the registry.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from db.matching_policy import (
    ALIAS_ONLY_CANONICALS,
    BASIS_DIFFERENTIATED,
    DEFERRED_CANONICALS,
    MAC636_RATIFIED_PROMOTIONS,
    PROPOSED_ALIAS_ONLY,
    PROPOSED_BASIS_DIFFERENTIATED,
    SHORT_MAX_LEN,
    BasisRule,
    PREFIX_NEUTRAL_TOKENS,
    extension_permits_attribution,
    extension_verdict,
    assert_basis_rules_are_applicable,
    assert_basis_rules_are_sound,
    assert_no_overlap,
    assert_policy_is_applicable,
    attributes,
    is_alias_only,
    is_basis_differentiated,
    is_qualified_alias,
    is_short_token,
    flagged_canonicals,
    matcher_keywords_for,
    matcher_keywords_for_basis,
)

REPO = Path(__file__).resolve().parents[1]
T2_TSV = REPO / "operator_review/MAC-542/T2_query_default_demotion_proposal.tsv"
ADJ_TSV = REPO / "operator_review/MAC-588/adjudication.tsv"
DB = REPO / "db/argus.db"


def _screen():
    """The MAC-542 screen of record: canonical -> recommended_action."""
    with T2_TSV.open() as f:
        return {r["canonical_name"]: r for r in csv.DictReader(f, delimiter="\t")}


# ── 1. provenance: the policy is the MAC-542 screen, not a new screen ─────

def test_policy_partitions_exactly_the_flagged_cohort():
    screen = _screen()
    flagged = {c for c, r in screen.items() if r["recommended_action"] != "KEEP"}
    assert flagged == flagged_canonicals()
    assert len(flagged) == 12


def test_tiers_are_pairwise_disjoint():
    assert_no_overlap()
    # MAC-636 inverted these two pins rather than relaxing them: the promotion
    # moved 3 entries, so the counts move 2->5 and 3->0. A count that stopped
    # being asserted would let the next promotion in silently.
    assert len(ALIAS_ONLY_CANONICALS) == 5
    assert len(PROPOSED_ALIAS_ONLY) == 0
    assert len(DEFERRED_CANONICALS) == 7


def test_no_unflagged_canonical_is_alias_only():
    """A KEEP canonical must never be flagged — that would be a new screen."""
    screen = _screen()
    keeps = {c for c, r in screen.items() if r["recommended_action"] == "KEEP"}
    assert not (keeps & flagged_canonicals())


def test_both_common_words_are_applied_not_deferred():
    """STOP and Reveal are the two is_common_word=yes rows; both must land."""
    screen = _screen()
    common = {c for c, r in screen.items() if r["is_common_word"] == "yes"}
    assert common == {"STOP", "Reveal"}
    assert common <= set(ALIAS_ONLY_CANONICALS)


def test_every_policy_entry_carries_a_measured_reason():
    for table in (ALIAS_ONLY_CANONICALS, PROPOSED_ALIAS_ONLY,
                  DEFERRED_CANONICALS):
        for canonical, reason in table.items():
            assert len(reason) > 40, f"{canonical} reason is not evidence"
            assert any(ch.isdigit() for ch in reason), (
                f"{canonical} reason cites no measured count")


# ── 2. predicates ─────────────────────────────────────────────────────────

def test_short_token_rule_matches_mac542_verbatim():
    assert SHORT_MAX_LEN == 6
    assert is_short_token("STOP")
    assert is_short_token("Reveal")      # 6 chars, single token
    assert not is_short_token("Skydio ")  # trailing space -> not single token
    assert not is_short_token("Reveal Media")


def test_qualified_alias_rejects_bare_short_tokens():
    # DJI's alias blob literally contains these; matching on them would
    # re-import four other vendors' FP magnets.
    for junk in ("Autel", "Parrot", "Axon", "DJI", "3DR", "BRINC"):
        assert not is_qualified_alias(junk)
    for good in ("Reveal Media", "Harris Corporation", "STOP LLC",
                 "Satellite Tracking of People"):
        assert is_qualified_alias(good)


# ── 3. the narrowing is a narrowing ───────────────────────────────────────

def test_unflagged_canonical_keyword_set_is_unchanged():
    """MAC-577 narrows; it must not smuggle in an alias-based expansion.

    Regression pin: an earlier draft returned canonical + qualified aliases
    for every vendor. That pulled 47 unrelated rows into the corpus and moved
    deferred DJI by +2.
    """
    assert matcher_keywords_for("Flock Safety", "Flock, Flock Safety Inc") == [
        "Flock Safety"]
    assert matcher_keywords_for("Getac", "Getac Technology Corporation") == ["Getac"]


def test_alias_only_canonical_drops_the_bare_name():
    kws = matcher_keywords_for("Reveal", "Reveal Media, Reveal Media Limited")
    assert "Reveal" not in kws
    assert kws == ["Reveal Media", "Reveal Media Limited"]


def test_alias_only_stop_uses_both_qualified_aliases():
    kws = matcher_keywords_for("STOP", "Satellite Tracking of People, STOP LLC")
    assert "STOP" not in kws
    assert set(kws) == {"Satellite Tracking of People", "STOP LLC"}


def test_unapplied_canonicals_keep_their_bare_name():
    """Un-applied means un-applied — proposed and deferred both still match bare."""
    for c in set(PROPOSED_ALIAS_ONLY) | set(DEFERRED_CANONICALS):
        assert not is_alias_only(c)
        assert matcher_keywords_for(c, "Some Qualified Alias") == [c]


def test_short_single_token_cohort_is_gated_not_applied():
    """MAC-577 §3, repointed by MAC-636 — NOT deleted.

    The original form asserted the cohort intersects the applied tier in
    NOTHING. That is the correct gate right up until the first ratified
    promotion, at which point it fails by design and the tempting repair is to
    delete it. Deleting it would leave the remaining 7 deferred canonicals —
    Skydio and Axon among them — promotable by anyone who edits one dict.

    So the gate becomes an EQUALITY against a named set instead of an
    emptiness check. "Decided" and "any short token is fair game" are different
    states and only equality separates them: an 8th short-token canonical in
    the applied tier fails here whether or not it was moved cleanly out of
    DEFERRED_CANONICALS.

    That this gate is not hollow is proved, not asserted — see
    ``test_cohort_gate_fires_on_an_unratified_promotion`` below, which performs
    the promotion and requires this function to raise.
    """
    screen = _screen()
    short_cohort = {c for c, r in screen.items()
                    if r["recommended_action"] != "KEEP"
                    and r["is_common_word"] == "no"}
    assert len(short_cohort) == 10

    applied_short = short_cohort & set(ALIAS_ONLY_CANONICALS)
    assert applied_short == set(MAC636_RATIFIED_PROMOTIONS), (
        "the set of short-single-token canonicals in ALIAS_ONLY_CANONICALS is "
        f"{sorted(applied_short)}, but the only ratified promotions are "
        f"{sorted(MAC636_RATIFIED_PROMOTIONS)} (MAC-636, CEO comment "
        "8ce463c7-75d1-4de6-ab6a-0e23512273a1). A short-single-token canonical "
        "was applied without a recorded decision, or a ratified one was "
        "reverted without updating MAC636_RATIFIED_PROMOTIONS.")

    # The cohort is still fully accounted for: 3 ratified + 0 proposed + 7
    # deferred. Nothing fell out of the taxonomy on the way through.
    assert short_cohort == (set(MAC636_RATIFIED_PROMOTIONS)
                            | set(PROPOSED_ALIAS_ONLY)
                            | set(DEFERRED_CANONICALS))
    # And every ratified name really is a short single token — the gate would be
    # trivially satisfiable by listing a long canonical here.
    assert all(is_short_token(c) for c in MAC636_RATIFIED_PROMOTIONS)


@pytest.mark.parametrize("intruder", ["Skydio", "Axon"])
@pytest.mark.parametrize("clean_move", [False, True])
def test_cohort_gate_fires_on_an_unratified_promotion(intruder, clean_move):
    """Simulate an 8th promotion and require the gate above to FAIL.

    A gate that passes on an unauthorised promotion is worse than the broken
    one it replaced, so the failure is exercised rather than reasoned about.

    Both shapes of the mistake are covered, and ``clean_move=True`` is the one
    that matters:

    ``clean_move=False``  the entry is copied into ALIAS_ONLY_CANONICALS and
                          left in DEFERRED_CANONICALS. ``assert_no_overlap``
                          also catches this, so it does not on its own show the
                          cohort gate is doing any work.
    ``clean_move=True``   the entry is MOVED — added to the applied tier and
                          deleted from DEFERRED_CANONICALS. This is what a real
                          promotion edit looks like, the tiers stay disjoint,
                          ``assert_no_overlap`` PASSES (asserted below), and the
                          cohort gate is then the only thing standing between a
                          deferred canonical and the applied tier.

    Skydio and Axon are the two the issue names: Skydio has 0 qualified aliases
    (580 sole-loss rows, alias-only is undefined for it) and Axon's loss cohort
    is basis-split with 29 adjudicated true positives inside it.
    """
    import db.matching_policy as mp

    assert intruder in DEFERRED_CANONICALS
    assert intruder not in MAC636_RATIFIED_PROMOTIONS
    assert is_short_token(intruder), "the intruder must be in the short cohort"

    saved_deferred = dict(mp.DEFERRED_CANONICALS)
    mp.ALIAS_ONLY_CANONICALS[intruder] = saved_deferred[intruder]
    if clean_move:
        del mp.DEFERRED_CANONICALS[intruder]
    try:
        if clean_move:
            # The tiers are still disjoint, so the disjointness gate is happy.
            # Whatever fails next is the cohort gate, not a bookkeeping check.
            assert_no_overlap()
        with pytest.raises(AssertionError) as exc:
            test_short_single_token_cohort_is_gated_not_applied()
        assert intruder in str(exc.value), (
            "the gate failed, but not about the intruder — the failure must "
            "name what was promoted or it is not diagnostic")
    finally:
        mp.ALIAS_ONLY_CANONICALS.pop(intruder, None)
        mp.DEFERRED_CANONICALS.clear()
        mp.DEFERRED_CANONICALS.update(saved_deferred)

    # Teardown restored the tiers, so the real gate passes again. Without this
    # the parametrised runs would mask each other's leakage.
    assert_no_overlap()
    test_short_single_token_cohort_is_gated_not_applied()


def test_ratified_promotions_are_actually_applied():
    """The pin is a claim about ALIAS_ONLY_CANONICALS, so check the direction
    the gate above cannot: every ratified name must really be in the applied
    tier. A name listed here but never moved would make the gate pass while
    the promotion silently did not happen."""
    assert len(MAC636_RATIFIED_PROMOTIONS) == 3
    assert set(MAC636_RATIFIED_PROMOTIONS) == {"Harris", "KeyW", "Rekor"}
    for c in MAC636_RATIFIED_PROMOTIONS:
        assert c in ALIAS_ONLY_CANONICALS, f"{c} is ratified but not applied"
        assert is_alias_only(c), f"{c} is in the dict but is_alias_only says no"
        assert c not in PROPOSED_ALIAS_ONLY and c not in DEFERRED_CANONICALS
    # Axon is explicitly NOT among them — MAC-588 owns it (out of MAC-636 scope).
    assert "Axon" not in MAC636_RATIFIED_PROMOTIONS


# ── 4. the guard that prevents a silent vendor drop ───────────────────────

def test_guard_fires_when_alias_only_vendor_has_no_qualified_alias():
    """Berla-shaped input: flagged with aliases IS NULL -> must fail loudly."""
    rows = [("Reveal", None)]  # Reveal is ALIAS_ONLY; NULL aliases
    with pytest.raises(AssertionError, match="attribute nothing"):
        assert_policy_is_applicable(rows)


def test_guard_fires_on_short_only_alias_blob():
    """Skydio-shaped input: aliases exist but every token is short/bare."""
    rows = [("STOP", "DJI, Brinc, Axon")]
    with pytest.raises(AssertionError, match="attribute nothing"):
        assert_policy_is_applicable(rows)


def test_guard_passes_on_real_registry_state():
    if not DB.exists():
        pytest.skip("db/argus.db not present")
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT canonical_name, aliases FROM manufacturers "
        "WHERE query_default='visible'").fetchall()
    assert_policy_is_applicable(rows)


# ── 5. measured behaviour against HEAD registry state ─────────────────────

def test_deferred_vendors_would_lose_their_footprint():
    """The reason the deferred seven are deferred, asserted not narrated."""
    if not DB.exists():
        pytest.skip("db/argus.db not present")
    con = sqlite3.connect(DB)

    def aliases(name):
        r = con.execute(
            "SELECT aliases FROM manufacturers WHERE canonical_name=?",
            (name,)).fetchone()
        return r[0] if r else None

    from db.alias_parser import split_aliases
    # Berla has no aliases at all -> alias-only would match nothing.
    assert split_aliases(aliases("Berla")) == []
    # Skydio's aliases are all short bare co-mention tokens.
    assert not [a for a in split_aliases(aliases("Skydio")) if is_qualified_alias(a)]
    # DJI's blob is majority short bare tokens.
    dji = split_aliases(aliases("DJI"))
    assert len([a for a in dji if not is_qualified_alias(a)]) > len(dji) / 2


def test_applied_vendors_all_have_a_qualified_alias():
    if not DB.exists():
        pytest.skip("db/argus.db not present")
    con = sqlite3.connect(DB)
    for c in ALIAS_ONLY_CANONICALS:
        r = con.execute(
            "SELECT aliases FROM manufacturers WHERE canonical_name=?",
            (c,)).fetchone()
        assert r is not None, f"{c} not in manufacturers"
        assert matcher_keywords_for(c, r[0]), f"{c} would attribute nothing"


# ── 6. basis-differentiated tier (MAC-588) ────────────────────────────────

# Verbatim from HEAD: SELECT aliases FROM manufacturers WHERE canonical_name='Axon'
# (note the quoting — a hand-built comma-join does NOT round-trip through
# split_aliases, it shatters "Axon Enterprise, Inc" into two aliases).
AXON_ALIASES = ('TASER International (legacy), "Axon Enterprise, Inc", '
                '"AXON ENTERPRISE, INC.", Axon Enterprise, Axon Body-2, Axon Flex')


def _adjudication():
    """MAC-588's exhaustive verdict on the 102 description-basis rows."""
    with ADJ_TSV.open() as f:
        return {int(r["id"]): r["verdict"] for r in csv.DictReader(f, delimiter="\t")}


def test_basis_rules_are_structurally_sound():
    assert_basis_rules_are_sound()


def test_axon_is_proposed_not_applied():
    """MAC-577's standing gate: the short-single-token cohort needs per-vendor
    sign-off. MAC-588 supplies the dossier; it does not grant the sign-off."""
    assert set(BASIS_DIFFERENTIATED) == set()
    assert set(PROPOSED_BASIS_DIFFERENTIATED) == {"Axon"}
    assert not is_basis_differentiated("Axon")
    # un-applied means un-applied: Axon still matches bare, on both bases.
    assert matcher_keywords_for("Axon", AXON_ALIASES) == ["Axon"]
    assert matcher_keywords_for_basis("Axon", AXON_ALIASES, "vendor") == ["Axon"]


def test_axon_stays_in_deferred_because_alias_only_is_still_unsafe():
    """The tiers overlap on purpose — they describe different rules."""
    assert "Axon" in DEFERRED_CANONICALS
    assert "Axon" not in ALIAS_ONLY_CANONICALS


def test_basis_rule_reason_is_evidence():
    for canonical, rule in {**BASIS_DIFFERENTIATED,
                            **PROPOSED_BASIS_DIFFERENTIATED}.items():
        assert isinstance(rule, BasisRule)
        assert len(rule.reason) > 40, f"{canonical} reason is not evidence"
        assert any(ch.isdigit() for ch in rule.reason), (
            f"{canonical} reason cites no measured count")


def test_empty_qualifier_set_is_rejected():
    """A rule with no qualifiers silently degrades to bare-on-description."""
    import db.matching_policy as mp
    saved = dict(mp.PROPOSED_BASIS_DIFFERENTIATED)
    mp.PROPOSED_BASIS_DIFFERENTIATED["Axon"] = BasisRule(
        reason="x" * 50 + " 1 count", description_qualifiers=())
    try:
        with pytest.raises(AssertionError, match="empty qualifier set"):
            assert_basis_rules_are_sound()
    finally:
        mp.PROPOSED_BASIS_DIFFERENTIATED.clear()
        mp.PROPOSED_BASIS_DIFFERENTIATED.update(saved)


def test_unflagged_canonical_cannot_get_a_basis_rule():
    """A basis rule for a KEEP canonical would be a new screen."""
    import db.matching_policy as mp
    saved = dict(mp.PROPOSED_BASIS_DIFFERENTIATED)
    mp.PROPOSED_BASIS_DIFFERENTIATED["Flock Safety"] = BasisRule(
        reason="x" * 50 + " 1 count", description_qualifiers=("ALPR",))
    try:
        with pytest.raises(AssertionError, match="not in the MAC-542 flagged"):
            assert_basis_rules_are_sound()
    finally:
        mp.PROPOSED_BASIS_DIFFERENTIATED.clear()
        mp.PROPOSED_BASIS_DIFFERENTIATED.update(saved)


def _with_axon_applied():
    """Context: promote Axon, i.e. exactly the one-line move the CEO signs off."""
    import contextlib
    import db.matching_policy as mp

    @contextlib.contextmanager
    def ctx():
        mp.BASIS_DIFFERENTIATED["Axon"] = mp.PROPOSED_BASIS_DIFFERENTIATED["Axon"]
        try:
            yield
        finally:
            mp.BASIS_DIFFERENTIATED.pop("Axon", None)

    return ctx()


def test_promoted_rule_separates_the_measured_examples():
    """The mechanism, exercised on the rows MAC-588 adjudicated by hand."""
    with _with_axon_applied():
        assert is_basis_differentiated("Axon")
        # vendor basis is alias-only: the bare canonical is gone.
        assert matcher_keywords_for_basis("Axon", AXON_ALIASES, "vendor") == [
            "TASER International (legacy)", "Axon Enterprise, Inc",
            "AXON ENTERPRISE, INC.", "Axon Enterprise", "Axon Body-2",
            "Axon Flex"]
        assert "Axon" in matcher_keywords_for_basis(
            "Axon", AXON_ALIASES, "description")

        # vendor-basis FPs: dropped (id=43627-shaped rows keep matching via
        # the alias, so the real vendor is never at risk).
        assert attributes("Axon", AXON_ALIASES, "THE AXON GROUP, LTD", None) is None
        assert attributes("Axon", AXON_ALIASES, "AXON MEDICAL INC", None) is None
        assert attributes("Axon", AXON_ALIASES, "AXON, GARY L", None) is None
        assert attributes(
            "Axon", AXON_ALIASES, "AXON ENTERPRISE, INC.",
            "AWARD OF IDVRS-BODY WORN CAMERAS") == "vendor"

        # description-basis TPs: retained.
        for excerpt in ("AXON X26P TASERS",
                        "AXON SPECIAL SERVICE AGREEMENT FOR ALL BODY CAMERAS "
                        "SOLUTIONS LOCATED AT PENTAGON FORCE PROTECTION AGENCY.",
                        "POLICE&SECURITY IN-CAR CAMERA RECORDING SYSTEM (AXON)",
                        "BLRI AXON FLEET 2 INSTALL - SOUTH",
                        "G:ESTAR, 2019 AXON CARTRIDGE ORDER",
                        "SUPPLIES, TAZER AXON 2 FOR NPS, MARTIN LUTHER KING JR."):
            assert attributes("Axon", AXON_ALIASES, "AARDVARK", excerpt) == \
                "description", excerpt

        # description-basis FPs: dropped.
        for excerpt in ("AXON THERAPY SYSTEM",
                        "INFORMATICA AXON GOVERN LICENSE",
                        "4514387007!AXON INSTRUMENT AND TI IMPLANT SET",
                        "AXON TUBE ADAPTER",
                        "AXON GENEPIX PERSONAL 4100A SCANNER",
                        "AXON 920-1 TPC FEMTOSECOND LASER SYSTEM"):
            assert attributes(
                "Axon", AXON_ALIASES, "SOME RESELLER LLC", excerpt) is None, excerpt


def test_promotion_would_not_lose_a_single_adjudicated_true_positive():
    """The load-bearing claim, asserted against HEAD rather than narrated.

    Pins MAC-588's measurement: over all 102 adjudicated description-basis
    rows the promoted rule retains 29/29 TP and 0/73 FP. A qualifier deleted
    from the set fails here, not in the registry.
    """
    if not DB.exists():
        pytest.skip("db/argus.db not present")
    verdicts = _adjudication()
    assert len(verdicts) == 102
    assert sum(v == "TP" for v in verdicts.values()) == 29
    assert sum(v == "FP" for v in verdicts.values()) == 73

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, vendor_canonical_name, product_family, source_excerpt "
        "FROM procurement_records WHERE id IN "
        f"({','.join('?' * len(verdicts))})", tuple(verdicts)).fetchall()
    assert len(rows) == 102

    with _with_axon_applied():
        kept_tp = kept_fp = 0
        for r in rows:
            desc = " ".join(filter(None, [r["product_family"],
                                          r["source_excerpt"]]))
            got = attributes("Axon", AXON_ALIASES,
                             r["vendor_canonical_name"], desc)
            if verdicts[r["id"]] == "TP":
                assert got == "description", (
                    f"id={r['id']} is an adjudicated TP and would be LOST: {desc!r}")
                kept_tp += 1
            else:
                assert got is None, (
                    f"id={r['id']} is an adjudicated FP and would be KEPT: {desc!r}")
                kept_fp += 1
    assert (kept_tp, kept_fp) == (29, 73)


def test_basis_guard_fires_when_vendor_basis_would_be_emptied():
    """Berla-shaped input for the basis tier: no qualified alias -> loud fail."""
    with _with_axon_applied():
        with pytest.raises(AssertionError, match="attribute nothing"):
            assert_basis_rules_are_applicable([("Axon", None)])
        # short bare co-mentions are not qualified aliases either
        with pytest.raises(AssertionError, match="attribute nothing"):
            assert_basis_rules_are_applicable([("Axon", "DJI, Brinc, Axon")])
        assert_basis_rules_are_applicable([("Axon", AXON_ALIASES)])


def test_basis_rule_is_inert_while_unapplied():
    """With Axon un-applied, attributes() must reproduce today's bare match."""
    assert attributes("Axon", AXON_ALIASES, "THE AXON GROUP, LTD", None) == "vendor"
    assert attributes("Axon", AXON_ALIASES, "SOME RESELLER LLC",
                      "AXON THERAPY SYSTEM") == "description"


def test_basis_differentiation_is_a_narrowing_not_an_expansion():
    """Every row the promoted rule attributes must already match today."""
    if not DB.exists():
        pytest.skip("db/argus.db not present")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT vendor_canonical_name, product_family, source_excerpt "
        "FROM procurement_records LIMIT 5000").fetchall()
    for r in rows:
        desc = " ".join(filter(None, [r["product_family"], r["source_excerpt"]]))
        before = attributes("Axon", AXON_ALIASES, r["vendor_canonical_name"], desc)
        with _with_axon_applied():
            after = attributes("Axon", AXON_ALIASES,
                               r["vendor_canonical_name"], desc)
        assert not (after and not before), (
            f"promoted rule ADDED a row: {r['vendor_canonical_name']!r} {desc!r}")


# ── MAC-598: proper-extension guard ───────────────────────────────────────

def test_prefix_extension_is_blocked():
    """The finding of record: DIGITAL AXIS COMMUNICATIONS is not Axis."""
    assert extension_verdict("Axis Communications",
                             "DIGITAL AXIS COMMUNICATIONS") == "block"
    assert not extension_permits_attribution("Axis Communications",
                                             "DIGITAL AXIS COMMUNICATIONS")
    # The same shape on a long SINGLE-token keyword, which MAC-598's opening
    # sweep did not cover. Both rows are real: t3_audit.log "PREFIX
    # extensions (LONG SINGLE-token kw)".
    assert extension_verdict("Kenwood", "BLUE-KENWOOD LLC") == "block"
    assert extension_verdict("Kenwood", "022808 KENWOOD LLC") == "block"


def test_exact_and_neutral_suffix_are_retained():
    assert extension_verdict("Axis Communications",
                             "AXIS COMMUNICATIONS") == "exact"
    assert extension_verdict("Axis Communications",
                             "AXIS COMMUNICATIONS INC") == "retain"
    assert extension_verdict("Motorola Solutions",
                             "MOTOROLA SOLUTIONS, INC.") == "retain"
    assert extension_verdict("Magnet Forensics",
                             "MAGNET FORENSICS USA INC") == "retain"
    assert extension_verdict("Sierra Wireless",
                             "SIERRA WIRELESS AMERICA, INC") == "retain"
    assert extension_verdict("Lockheed Martin",
                             "LOCKHEED MARTIN CORPORATION") == "retain"
    for v in ("AXIS COMMUNICATIONS", "AXIS COMMUNICATIONS INC"):
        assert extension_permits_attribution("Axis Communications", v)


def test_descriptive_suffix_routes_to_adjudication_not_retention():
    """The half of the issue's proposed rule that the evidence refutes.

    Each of these is a SUFFIX extension AND a different entity, proven from
    the source excerpt, not from the name. A rule that retained every suffix
    extension would credit all of them to a surveillance vendor.
    """
    for keyword, vendor in [
        ("Kenwood", "KENWOOD FIRE DEPARTMENT"),        # fire response, trust land
        ("Kenwood", "KENWOOD HEALTH CARE CORP"),       # community nursing home
        ("Kenwood", "KENWOOD KITCHENS INC"),           # kitchen renovation
        ("Clearview", "CLEARVIEW-ROUTH LP"),           # nursing home services
        ("Clearview", "CLEARVIEW SONOGRAPHICS LLC"),   # ultrasound coverage
        ("Clearview", "CLEARVIEW CLEANING LLC"),       # janitorial services
        ("Vigilant", "VIGILANT CYBER SYSTEMS, INC."),  # DHA SBIR medical R&D
        ("Vigilant", "VIGILANT FIRE INC."),            # fire extinguisher disposal
        ("Vigilant Solutions", "VIGILANT SOLUTIONS LLC INTEGRATION GROUP"),
    ]:
        assert extension_verdict(keyword, vendor) == "adjudicate", (keyword, vendor)
        assert not extension_permits_attribution(keyword, vendor), (keyword, vendor)


def test_prefix_neutral_allowlist_is_reachable():
    """BRIEF_STANDARDS R7 positive control.

    PREFIX_NEUTRAL_TOKENS is untriggered by the live corpus, so a caller
    could not otherwise tell an empty-by-design allowlist from a dead branch.
    This asserts the branch is reachable and that removing THE from the set
    changes the verdict — i.e. the allowlist is load-bearing, not decorative.
    """
    assert PREFIX_NEUTRAL_TOKENS == {"THE"}
    # Corpus-grounded, not synthetic: procurement_records carries
    # 'THE KEYW CORPORATION' (ids 45097/45098/45134/45183, ...) and
    # 'THE KEYW HOLDING CORPORATION'. KeyW is short so it routes to T2 by the
    # MAC-542 §5 screen, but the TOKEN SHAPE the allowlist exists for is real.
    assert extension_verdict("KeyW", "THE KEYW CORPORATION") == "retain"
    assert extension_verdict("Axis Communications",
                             "THE AXIS COMMUNICATIONS COMPANY") == "retain"
    import db.matching_policy as mp
    saved = mp.PREFIX_NEUTRAL_TOKENS
    try:
        mp.PREFIX_NEUTRAL_TOKENS = frozenset()
        assert mp.extension_verdict("KeyW", "THE KEYW CORPORATION") == "block"
        assert mp.extension_verdict("Axis Communications",
                                    "THE AXIS COMMUNICATIONS COMPANY") == "block"
    finally:
        mp.PREFIX_NEUTRAL_TOKENS = saved


def test_prefix_neutral_shape_occurs_in_the_live_corpus():
    """The allowlist is not hypothetical — assert the shape exists in the DB."""
    if not DB.exists():
        pytest.skip("db/argus.db not present")
    con = sqlite3.connect(DB)
    n = con.execute(
        "SELECT COUNT(*) FROM procurement_records "
        "WHERE vendor_canonical_name LIKE 'THE %'").fetchone()[0]
    assert n > 0, "no 'THE <name>' vendor rows: PREFIX_NEUTRAL_TOKENS is dead code"


def test_non_match_and_substring_are_distinguished():
    assert extension_verdict("Axis Communications", "MOTOROLA SOLUTIONS, INC.") is None
    # Entity-boundary still holds: substring-inside-token is not a match.
    assert extension_verdict("Axis", "PLAXIS BV") is None
    assert extension_verdict("Axis", None) is None


def test_guard_verdicts_over_the_live_corpus_are_stable():
    """Pin the measured blast radius on the keywords that actually reach T3.

    Scoped to LONG keywords on purpose. The guard fires on short keywords too
    (BAKER JACOBS JV, DEREK J HARRIS, PRI/DJI A RECONSTRUCTION JV), but those
    already route to T2 and were adjudicated there — the guard complements the
    MAC-542 §5 short screen, it does not replace it. The never-adjudicated
    class is exactly the long half, so that is what this pins.
    """
    if not DB.exists():
        pytest.skip("db/argus.db not present")
    con = sqlite3.connect(DB)
    universe = sorted({r[0] for r in con.execute(
        "SELECT canonical_name FROM manufacturers WHERE query_default='visible'")})
    long_kw = [k for k in universe if not is_short_token(k)]
    vendors = con.execute(
        "SELECT vendor_canonical_name, COUNT(*) FROM procurement_records "
        "GROUP BY vendor_canonical_name").fetchall()
    blocked, blocked_rows = set(), 0
    for vendor, n in vendors:
        if any(extension_verdict(k, vendor) == "block" for k in long_kw):
            blocked.add(vendor)
            blocked_rows += n
    assert blocked == {"DIGITAL AXIS COMMUNICATIONS", "BLUE-KENWOOD LLC",
                       "022808 KENWOOD LLC"}, sorted(blocked)
    assert blocked_rows == 6, blocked_rows
