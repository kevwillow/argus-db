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
    DEFERRED_CANONICALS,
    PROPOSED_ALIAS_ONLY,
    SHORT_MAX_LEN,
    assert_no_overlap,
    assert_policy_is_applicable,
    is_alias_only,
    is_qualified_alias,
    is_short_token,
    flagged_canonicals,
    matcher_keywords_for,
)

REPO = Path(__file__).resolve().parents[1]
T2_TSV = REPO / "operator_review/MAC-542/T2_query_default_demotion_proposal.tsv"
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
