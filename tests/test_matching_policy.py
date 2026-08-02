"""MAC-577 — tests for db/matching_policy.py.

Two jobs:
  1. Pin the policy sets against the MAC-542 screen of record so the two
     cannot drift (the issue's rule: reuse that screen, do not redo it).
  2. Pin the measured behaviour, so a future edit that quietly re-widens the
     matcher or drops a real vendor fails here instead of in the registry.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

import pytest

from db.entity_boundary import boundary_match
from db.matching_policy import (
    ALIAS_ONLY_CANONICALS,
    BASIS_DIFFERENTIATED,
    DEFERRED_CANONICALS,
    MAC595_RATIFIED_BASIS_PROMOTIONS,
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
    qualified_aliases_for,
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
    """MAC-577 §3, repointed by MAC-636 and WIDENED to the basis tier by MAC-622.

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

    MAC-622 closes the other half of the hole. Through MAC-636 this gate read
    ``ALIAS_ONLY_CANONICALS`` and nothing else, so MAC-577 §3 constrained the
    alias-only tier alone — and ``BASIS_DIFFERENTIATED`` is a second applied
    tier reachable by the same cohort. Under MAC-595's simulated promotion of
    Axon this gate PASSED, which is the defect: the next short-single-token
    canonical could enter the basis tier with no sign-off at all and the gate
    would stay green. Both applied tiers are now gated, each against its own
    named decision set.

    That this gate is not hollow is proved, not asserted — see
    ``test_cohort_gate_fires_on_an_unratified_promotion`` and
    ``test_cohort_gate_fires_on_an_unratified_basis_promotion`` below, which
    perform the promotion and require this function to raise.
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

    # Same rule, second applied tier. Axon is the only signed-off entry.
    basis_short = short_cohort & set(BASIS_DIFFERENTIATED)
    assert basis_short == set(MAC595_RATIFIED_BASIS_PROMOTIONS), (
        "the set of short-single-token canonicals in BASIS_DIFFERENTIATED is "
        f"{sorted(basis_short)}, but the only ratified basis promotions are "
        f"{sorted(MAC595_RATIFIED_BASIS_PROMOTIONS)} (MAC-595, CEO comment "
        "6564f836-66be-4f78-a643-474f11ee1a57). A short-single-token canonical "
        "was given an APPLIED basis rule without a recorded decision, or a "
        "ratified one was reverted without updating "
        "MAC595_RATIFIED_BASIS_PROMOTIONS.")

    # The cohort is still fully accounted for: 3 ratified + 0 proposed + 7
    # deferred. Nothing fell out of the taxonomy on the way through. Axon is
    # counted here under DEFERRED, where it still belongs — a basis rule is not
    # an alias-only rule, and the tiers overlap on purpose.
    assert short_cohort == (set(MAC636_RATIFIED_PROMOTIONS)
                            | set(PROPOSED_ALIAS_ONLY)
                            | set(DEFERRED_CANONICALS))
    # And every ratified name really is a short single token — the gate would be
    # trivially satisfiable by listing a long canonical here.
    assert all(is_short_token(c) for c in MAC636_RATIFIED_PROMOTIONS)
    assert all(is_short_token(c) for c in MAC595_RATIFIED_BASIS_PROMOTIONS)


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
    # Axon is explicitly NOT among them — it is an alias-only promotion set, and
    # Axon's sign-off (MAC-595) applied a BASIS rule instead. Different tier,
    # different decision set; alias-only is still measured unsafe for Axon.
    assert "Axon" not in MAC636_RATIFIED_PROMOTIONS
    assert "Axon" not in ALIAS_ONLY_CANONICALS


@pytest.mark.parametrize("intruder", ["Skydio", "Getac"])
def test_cohort_gate_fires_on_an_unratified_basis_promotion(intruder):
    """MAC-622: simulate an unsigned SECOND basis promotion, require a FAIL.

    This is the criterion the MAC-595 sign-off called the real deliverable. The
    hole it names is specific: a basis promotion legitimately leaves its entry
    in ``DEFERRED_CANONICALS`` (Axon does), so none of the bookkeeping checks
    move at all when a second one is added. This test proves that:

    * ``assert_no_overlap`` PASSES — it only knows the three alias tiers.
    * ``assert_basis_rules_are_sound`` PASSES — the intruder is in the flagged
      cohort and its rule has a non-empty qualifier set, so it is structurally
      valid. Structural validity is not authorisation.

    ...and then requires the cohort gate to raise anyway, naming the intruder.
    Without the basis-tier arm added by MAC-622 this test cannot pass, which is
    what makes that arm load-bearing rather than decorative.
    """
    import db.matching_policy as mp

    assert intruder in DEFERRED_CANONICALS
    assert intruder not in MAC595_RATIFIED_BASIS_PROMOTIONS
    assert is_short_token(intruder), "the intruder must be in the short cohort"

    mp.BASIS_DIFFERENTIATED[intruder] = BasisRule(
        reason=f"simulated unsigned promotion of {intruder} — 1 count",
        description_qualifiers=("DRONE",))
    try:
        # Neither structural gate objects: the promotion is well-formed, it is
        # merely unauthorised. So whatever fails next is the sign-off gate.
        assert_no_overlap()
        assert_basis_rules_are_sound()
        with pytest.raises(AssertionError) as exc:
            test_short_single_token_cohort_is_gated_not_applied()
        assert intruder in str(exc.value), (
            "the gate failed, but not about the intruder — the failure must "
            "name what was promoted or it is not diagnostic")
    finally:
        mp.BASIS_DIFFERENTIATED.pop(intruder, None)

    # Teardown restored the tier, so the real gate passes again with Axon alone.
    assert set(BASIS_DIFFERENTIATED) == {"Axon"}
    assert_basis_rules_are_sound()
    test_short_single_token_cohort_is_gated_not_applied()


def test_ratified_basis_promotion_is_actually_applied():
    """The direction the gate above cannot check: every name recorded as a
    ratified basis promotion must really be in the applied tier. A name listed
    in MAC595_RATIFIED_BASIS_PROMOTIONS but never moved would make the gate
    pass while the promotion silently did not happen."""
    assert MAC595_RATIFIED_BASIS_PROMOTIONS == ("Axon",)
    for c in MAC595_RATIFIED_BASIS_PROMOTIONS:
        assert c in BASIS_DIFFERENTIATED, f"{c} is ratified but not applied"
        assert is_basis_differentiated(c), (
            f"{c} is in the dict but is_basis_differentiated says no")
        assert c not in PROPOSED_BASIS_DIFFERENTIATED
    # The proposed tier is empty and the applied tier is exactly the decided set:
    # nothing is awaiting sign-off, and nothing was applied without one.
    assert PROPOSED_BASIS_DIFFERENTIATED == {}
    assert set(BASIS_DIFFERENTIATED) == set(MAC595_RATIFIED_BASIS_PROMOTIONS)


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


def test_axon_is_applied_not_proposed():
    """INVERTED by MAC-622, not deleted (MAC-595 sign-off condition 2).

    This pinned the un-applied state through MAC-588: MAC-577 §3 held the
    short-single-token cohort for per-vendor sign-off, and MAC-588 supplied the
    dossier without granting it. MAC-595 granted it. The pin now reads the other
    way, and it is still a pin in both directions — a revert that empties
    BASIS_DIFFERENTIATED fails here, and so does a re-proposal.
    """
    assert set(BASIS_DIFFERENTIATED) == {"Axon"}
    assert set(PROPOSED_BASIS_DIFFERENTIATED) == set()
    assert is_basis_differentiated("Axon")
    # applied means applied: the bare canonical is gone from the vendor basis.
    assert "Axon" not in matcher_keywords_for_basis(
        "Axon", AXON_ALIASES, "vendor")
    # ...but the ALIAS-only tier is untouched, so the plain keyword helper — which
    # only knows that tier — still returns the bare name. That is not a leak: it
    # is why callers must use attributes()/matcher_keywords_for_basis(), and the
    # docstring on matcher_keywords_for_basis says so.
    assert matcher_keywords_for("Axon", AXON_ALIASES) == ["Axon"]


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
    """A rule with no qualifiers silently degrades to bare-on-description.

    Repointed at the APPLIED tier by MAC-622: with Axon applied, planting a
    same-named entry in the proposed tier trips the both-tiers check first and
    the assertion under test never runs. Mutating the tier Axon actually lives
    in keeps this exercising the qualifier guard.
    """
    import db.matching_policy as mp
    saved = dict(mp.BASIS_DIFFERENTIATED)
    mp.BASIS_DIFFERENTIATED["Axon"] = BasisRule(
        reason="x" * 50 + " 1 count", description_qualifiers=())
    try:
        with pytest.raises(AssertionError, match="empty qualifier set"):
            assert_basis_rules_are_sound()
    finally:
        mp.BASIS_DIFFERENTIATED.clear()
        mp.BASIS_DIFFERENTIATED.update(saved)
    # The restore really restored: the live rule still has its qualifiers.
    assert BASIS_DIFFERENTIATED["Axon"].description_qualifiers
    assert_basis_rules_are_sound()


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
    """REPOINTED at the applied tier by MAC-622 (MAC-595 sign-off condition 1).

    Through MAC-588 this context performed the promotion, reading the entry out
    of ``PROPOSED_BASIS_DIFFERENTIATED``. That read is a ``KeyError`` now that
    the entry has moved, and the tempting repair — swap in a no-op
    ``nullcontext`` — is the trap the sign-off called out: every 29/29 and 0/73
    assertion below would keep executing and keep passing, against whatever
    state happened to be live, proving nothing about the rule.

    So the context asserts the applied state rather than creating it. The proofs
    that use it only run while the rule they prove is genuinely in force, and a
    revert makes them fail here instead of quietly going vacuous.
    """
    import contextlib
    import db.matching_policy as mp

    @contextlib.contextmanager
    def ctx():
        rule = mp.BASIS_DIFFERENTIATED.get("Axon")
        assert rule is not None, (
            "Axon is not in BASIS_DIFFERENTIATED, so the proof that follows "
            "would measure the un-applied matcher while claiming to measure the "
            "promoted rule. MAC-595 applied this rule; if it was reverted, "
            "revert these proofs too rather than letting them pass vacuously.")
        assert rule.description_qualifiers, (
            "the applied rule has an empty qualifier set — it has degraded to "
            "bare-on-description and the proof below would not detect it")
        yield
        assert mp.BASIS_DIFFERENTIATED.get("Axon") is rule, (
            "the applied rule changed identity mid-proof")

    return ctx()


def _with_axon_unapplied():
    """The pre-promotion baseline: temporarily un-apply the ratified rule.

    Needed by the narrowing measurement, which has to compare the promoted arm
    against the status quo it replaced. ``pop`` without a default is deliberate
    — if Axon is not applied there is no baseline to establish and this raises
    ``KeyError`` rather than yielding a context that measures the same arm twice.
    """
    import contextlib
    import db.matching_policy as mp

    @contextlib.contextmanager
    def ctx():
        rule = mp.BASIS_DIFFERENTIATED.pop("Axon")
        try:
            assert not mp.is_basis_differentiated("Axon")
            yield
        finally:
            mp.BASIS_DIFFERENTIATED["Axon"] = rule

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


def test_basis_rule_is_live_and_pins_what_the_promotion_removed():
    """INVERTED by MAC-622, not deleted (MAC-595 sign-off condition 2).

    This pinned inertness: while Axon was un-applied, ``attributes()`` had to
    reproduce the plain bare match. Inverting it means pinning that those two
    rows are now DROPPED — but an assertion that they are gone, on its own, is
    weak evidence: it would also pass if ``attributes()`` had broken and started
    returning ``None`` for everything.

    So the pin runs in both directions off one pair of rows. The un-applied arm
    reproduces the exact pre-promotion verdicts (the old assertions, kept
    verbatim), the applied arm shows both gone, and the difference between the
    two arms IS the promotion. That is also the smallest honest statement of
    what MAC-595 authorised.
    """
    fp_vendor = ("THE AXON GROUP, LTD", None)
    fp_desc = ("SOME RESELLER LLC", "AXON THERAPY SYSTEM")

    with _with_axon_unapplied():
        assert attributes("Axon", AXON_ALIASES, *fp_vendor) == "vendor"
        assert attributes("Axon", AXON_ALIASES, *fp_desc) == "description"

    with _with_axon_applied():
        assert attributes("Axon", AXON_ALIASES, *fp_vendor) is None
        assert attributes("Axon", AXON_ALIASES, *fp_desc) is None
        # ...and the rule is a narrowing, not a break: a real TP on the same
        # description basis still attributes. Without this the two Nones above
        # would be satisfied by an attributes() that had stopped working.
        assert attributes("Axon", AXON_ALIASES, "AARDVARK",
                          "AXON X26P TASERS") == "description"


def test_basis_differentiation_is_a_narrowing_not_an_expansion():
    """Every row the applied rule attributes must already have matched before.

    Widened by MAC-622 from ``LIMIT 5000`` to all 50,499 rows. The MAC-595
    sign-off re-ran the full corpus and found the subset property holds exactly,
    making the shipped claim stronger than the one filed; a sampled test cannot
    carry that claim, so the sample is gone.

    The measured arms are pinned as well as the property, because "no row was
    added" is also true of a rule that dropped everything. R0 890 -> RB 694,
    delta -196 = 123 vendor-basis FPs + 73 adjudicated description-basis FPs.
    """
    if not DB.exists():
        pytest.skip("db/argus.db not present")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, vendor_canonical_name, product_family, source_excerpt "
        "FROM procurement_records").fetchall()
    assert len(rows) == 50499, f"corpus moved: {len(rows)} rows"

    texts = [(r["id"], r["vendor_canonical_name"],
              " ".join(filter(None, [r["product_family"], r["source_excerpt"]])))
             for r in rows]

    # R0: the status quo the promotion replaced. Measured, not quoted.
    with _with_axon_unapplied():
        r0 = {i for i, v, d in texts
              if attributes("Axon", AXON_ALIASES, v, d) is not None}
    # RB: the applied basis-differentiated rule.
    with _with_axon_applied():
        rb = {i for i, v, d in texts
              if attributes("Axon", AXON_ALIASES, v, d) is not None}

    added = rb - r0
    assert added == set(), (
        f"applied rule ADDED {len(added)} rows that did not match before: "
        f"{sorted(added)[:10]}")
    assert len(r0) == 890, f"R0 moved: {len(r0)}"
    assert len(rb) == 694, f"RB moved: {len(rb)}"
    assert len(rb) - len(r0) == -196


def test_description_basis_drop_cohort_is_recomputed_and_reconciles():
    """MAC-622 discharges the MAC-595 sweep obligation AS CODE, not as prose.

    The obligation exists because of what the sign-off found: the adjudication
    covers 102 rows, but the live description-basis cohort is **112**. The
    cohort had moved and nothing recomputed it. It was benign this time — and
    "benign this time" is exactly the state that stops being true silently, so
    the re-dump runs on every sweep of this suite rather than living in a
    runbook step somebody has to remember.

    What it recomputes, from the live DB and via the single-implementation
    matcher (``db.entity_boundary``, imported by the policy — no second
    normaliser is invented here):

        bare_only        225 = 123 vendor + 102 description   <- adjudicated
        alias_confirmed  665 = 655 vendor +  10 description   <- the gap
                         890 total

    and then requires the 10-row gap to be benign for the stated reason rather
    than by assumption: every one alias-confirmed on a real Axon Enterprise
    alias, and every one RETAINED under the applied rule. If a future harvest
    moves a row from the gap into the un-adjudicated bare-only set, the identity
    assertion against ``cohort.json`` fails and the adjudication gets re-run.
    """
    if not DB.exists():
        pytest.skip("db/argus.db not present")
    cohort = json.loads((REPO / "operator_review/MAC-588/cohort.json").read_text())

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    # Re-query the alias blob rather than trusting the module constant: the
    # cohort is a function of live registry state, and MAC-580 rewrote these
    # blobs once already.
    live_aliases = con.execute(
        "SELECT aliases FROM manufacturers WHERE canonical_name='Axon'"
    ).fetchone()["aliases"]
    assert live_aliases == AXON_ALIASES, (
        "manufacturers.aliases for Axon has drifted from the constant this "
        "suite pins; re-derive the cohort before trusting any count below")
    qualified = qualified_aliases_for("Axon", live_aliases)
    assert qualified == cohort["qualified_aliases"]

    rows = con.execute(
        "SELECT id, vendor_canonical_name, product_family, source_excerpt "
        "FROM procurement_records").fetchall()
    assert len(rows) == cohort["n_rows"] == 50499

    bare_v, bare_d, alias_hit = set(), set(), set()
    text = {}
    for r in rows:
        i = r["id"]
        vendor = r["vendor_canonical_name"]
        desc = " ".join(filter(None, [r["product_family"], r["source_excerpt"]]))
        text[i] = (vendor, desc)
        if boundary_match("Axon", vendor):
            bare_v.add(i)
        if boundary_match("Axon", desc):
            bare_d.add(i)
        if any(boundary_match(a, vendor) or boundary_match(a, desc)
               for a in qualified):
            alias_hit.add(i)

    bare = bare_v | bare_d
    bare_only = bare - alias_hit
    alias_confirmed = bare & alias_hit

    # The three totals of record.
    assert len(bare) == cohort["bare"] == 890
    assert len(bare_only) == cohort["bare_only"] == 225
    assert len(alias_confirmed) == cohort["alias_confirmed"] == 665

    # bare_only splits 123 vendor + 102 description...
    assert len(bare_only & bare_v) == cohort["vendor_basis"] == 123
    bare_only_desc = bare_only - bare_v
    assert len(bare_only_desc) == cohort["description_basis"] == 102
    # ...and the description half is IDENTICALLY the adjudicated set, not merely
    # the same size. A same-size different-membership cohort is the failure this
    # obligation exists to catch.
    assert bare_only_desc == set(cohort["description_basis_ids"])
    assert bare_only_desc == set(_adjudication())

    # alias_confirmed splits 655 vendor + 10 description — the 10 are the gap
    # between the live description-basis cohort (112) and the adjudicated 102.
    assert len(alias_confirmed & bare_v) == 655
    gap = alias_confirmed - bare_v
    assert len(gap) == 10
    assert len(bare_d - bare_v) == 112 == len(bare_only_desc) + len(gap)

    # The gap is benign for a stated reason, so assert the reason.
    gap_vendors = {text[i][0] for i in gap}
    assert gap_vendors == {"AARDVARK", "CARAHSOFT TECHNOLOGY CORP"}, gap_vendors
    with _with_axon_applied():
        for i in gap:
            vendor, desc = text[i]
            hits = [a for a in qualified
                    if boundary_match(a, vendor) or boundary_match(a, desc)]
            assert hits, f"id={i} is in the alias-confirmed gap with no alias hit"
            assert attributes("Axon", live_aliases, vendor, desc) is not None, (
                f"id={i} is an un-adjudicated alias-confirmed row and the "
                f"applied rule DROPS it — the gap is no longer benign")


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
