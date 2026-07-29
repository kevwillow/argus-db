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
    PROPOSED_ALIAS_ONLY,
    PROPOSED_BASIS_DIFFERENTIATED,
    SHORT_MAX_LEN,
    BasisRule,
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
    assert len(ALIAS_ONLY_CANONICALS) == 2
    assert len(PROPOSED_ALIAS_ONLY) == 3
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
    """MAC-577 deliverable 3: the 10 short-single-token canonicals must not be
    applied without per-vendor sign-off. Only the 2 common words ship."""
    screen = _screen()
    short_cohort = {c for c, r in screen.items()
                    if r["recommended_action"] != "KEEP"
                    and r["is_common_word"] == "no"}
    assert len(short_cohort) == 10
    assert not (short_cohort & set(ALIAS_ONLY_CANONICALS)), (
        "a short-single-token canonical was applied without sign-off")
    assert short_cohort == set(PROPOSED_ALIAS_ONLY) | set(DEFERRED_CANONICALS)


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
