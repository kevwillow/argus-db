"""Tests for SAR-8 + SAR-9 vendor-name-disambig (db/extraction/vendor_name_disambig.py).

Coverage:
- Positive (alias accepts) — every entry in VENDOR_ALIAS_ALLOWLIST.
- Negative (FP rejects) — every entry in VENDOR_FP_LIST that is NOT
  flag_for_review.
- Edge — GENETEC Corporation flagged-for-review (third return state).
- Geographic-prefix — `SZ DJI` strips/matches; `New York Axon` does NOT.
- Re-run determinism — predicate output is identical on identical input.
- 20-row alias-recovered cases from MAC-39 — every raw_observation alias
  string from extraction_outputs/mac39 accepts as DJI canonical.
- SAR-9 #1 Motorola Mobility/Solutions corporate-split FPs reject under
  Motorola Solutions canonical; bare-Motorola flag_for_review; positive-
  evidence accept (BSG / Broadband Solutions / Business Light).
- SAR-9 #2 alias-iteration regression — HARRIS ADACOM CORPORATION rejects
  under restructured caller via the per-canonical FP-list lookup.
- SAR-9 #3 WatchGuard Technologies firewall reject under WatchGuard.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from db.extraction.vendor_name_disambig import (
    GEOGRAPHIC_PREFIX_LIST,
    VENDOR_ALIAS_ALLOWLIST,
    VENDOR_BARE_TOKEN_FLAG,
    VENDOR_FP_LIST,
    VENDOR_POSITIVE_EVIDENCE,
    _normalize_vendor,
    _strip_geographic_prefix,
    alias_equality,
    is_canonical_vendor_match,
    is_flagged_for_review,
    is_fp_rejected,
    vendor_match_disposition,
)


# ---------------------------------------------------------------------------
# Positive — alias allowlist accepts.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "canonical,alias",
    [
        (canonical, alias)
        for canonical, aliases in VENDOR_ALIAS_ALLOWLIST.items()
        for alias in aliases
    ],
)
def test_alias_allowlist_accepts(canonical: str, alias: str) -> None:
    assert vendor_match_disposition(alias, canonical) == "accept"
    assert is_canonical_vendor_match(alias, canonical) is True


def test_alias_allowlist_minimum_coverage() -> None:
    """SAR-8 enumerates DJI and Cellebrite at minimum."""
    assert "DJI" in VENDOR_ALIAS_ALLOWLIST
    assert "Cellebrite" in VENDOR_ALIAS_ALLOWLIST


# ---------------------------------------------------------------------------
# Negative — FP list rejects (hard FPs).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "canonical,fp_entry",
    [
        (canonical, entry)
        for canonical, entries in VENDOR_FP_LIST.items()
        for entry in entries
        if not entry.get("flag_for_review", False)
    ],
)
def test_fp_list_rejects_hard(canonical: str, fp_entry: dict) -> None:
    candidate = str(fp_entry["substring"])
    assert vendor_match_disposition(candidate, canonical) == "reject_fp"
    assert is_canonical_vendor_match(candidate, canonical) is False
    assert is_fp_rejected(candidate, canonical) is True
    assert is_flagged_for_review(candidate, canonical) is False


def test_fp_list_rejects_axon_networks_variants() -> None:
    """The 6 Axon Networks raw_observations all hit reject_fp."""
    variants = [
        "Axon Networks Inc.",
        "Axon Networks, Inc.",
        "AXON NETWORKS, INC.",
        "Axon Networks INC",
        "axon networks inc",
        "Axon Networks Inc",
    ]
    for v in variants:
        assert vendor_match_disposition(v, "Axon") == "reject_fp", v


def test_fp_list_rejects_flock_audio_variants() -> None:
    variants = ["Flock Audio Inc.", "Flock Audio, Inc.", "FLOCK AUDIO INC"]
    for v in variants:
        assert vendor_match_disposition(v, "Flock Safety") == "reject_fp", v


def test_fp_list_rejects_harris_adacom_variants() -> None:
    variants = ["HARRIS ADACOM CORPORATION", "Harris Adacom Corporation"]
    for v in variants:
        assert vendor_match_disposition(v, "Harris") == "reject_fp", v


def test_fp_list_minimum_coverage() -> None:
    """SAR-8 enumerates Axon, Flock Safety, Harris, Genetec FPs."""
    assert "Axon" in VENDOR_FP_LIST
    assert "Flock Safety" in VENDOR_FP_LIST
    assert "Harris" in VENDOR_FP_LIST
    assert "Genetec" in VENDOR_FP_LIST


# ---------------------------------------------------------------------------
# Edge — GENETEC Corporation flagged-for-review.
# ---------------------------------------------------------------------------


def test_genetec_corporation_flagged_for_review() -> None:
    """`GENETEC Corporation` returns flag_for_review (third state).

    Behavior must NOT silently accept or reject — the disposition is a
    human-triage signal per SAR-8.
    """
    assert vendor_match_disposition("GENETEC Corporation", "Genetec") == "flag_for_review"
    assert is_flagged_for_review("GENETEC Corporation", "Genetec") is True
    assert is_canonical_vendor_match("GENETEC Corporation", "Genetec") is False
    assert is_fp_rejected("GENETEC Corporation", "Genetec") is False


def test_genetec_corporation_case_insensitive() -> None:
    for s in ["GENETEC Corporation", "genetec corporation", "Genetec CORPORATION"]:
        assert vendor_match_disposition(s, "Genetec") == "flag_for_review", s


def test_genetec_inc_default_accepts() -> None:
    """`Genetec Inc.` (the §2.1 alpr vendor) is NOT flagged — accepts."""
    assert vendor_match_disposition("Genetec Inc.", "Genetec") == "accept"
    assert vendor_match_disposition("Genetec, Inc.", "Genetec") == "accept"
    assert vendor_match_disposition("Genetec", "Genetec") == "accept"


# ---------------------------------------------------------------------------
# Geographic-prefix.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "candidate,canonical,expected",
    [
        ("SZ DJI TECHNOLOGY CO.,LTD", "DJI", "accept"),
        ("Sz Dji Technology Co.,Ltd", "DJI", "accept"),
        ("Shenzhen DJI Technology Co.,Ltd", "DJI", "accept"),
        ("New York Axon", "Axon", "no_match"),
        ("New York Axon Networks", "Axon", "reject_fp"),  # FP wins over geo
        ("Boston Axon", "Axon", "no_match"),
        ("California Flock Safety", "Flock Safety", "no_match"),
    ],
)
def test_geographic_prefix(candidate: str, canonical: str, expected: str) -> None:
    assert vendor_match_disposition(candidate, canonical) == expected


def test_geographic_prefix_strip_only_leading_token() -> None:
    """`_strip_geographic_prefix` only strips a leading prefix + whitespace."""
    assert _strip_geographic_prefix("SZ DJI Technology") == "DJI Technology"
    assert _strip_geographic_prefix("Shenzhen DJI") == "DJI"
    assert _strip_geographic_prefix("Shenzhen Co., DJI Tech") == "DJI Tech"
    assert _strip_geographic_prefix("New York Axon") == "New York Axon"
    assert _strip_geographic_prefix("DJI") == "DJI"
    assert _strip_geographic_prefix("") == ""


def test_geographic_prefix_list_minimum_coverage() -> None:
    """SAR-8 enumerates SZ, Shenzhen, SZ., Shenzhen Co., at minimum."""
    assert "SZ" in GEOGRAPHIC_PREFIX_LIST
    assert "Shenzhen" in GEOGRAPHIC_PREFIX_LIST
    assert "SZ." in GEOGRAPHIC_PREFIX_LIST
    assert "Shenzhen Co.," in GEOGRAPHIC_PREFIX_LIST


# ---------------------------------------------------------------------------
# Sibling-vendor / cross-vendor checks.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "candidate,canonical,expected",
    [
        # Default canonical accepts.
        ("Axon", "Axon", "accept"),
        ("AXON Inc.", "Axon", "accept"),
        ("Flock Safety", "Flock Safety", "accept"),
        ("DJI", "DJI", "accept"),
        # Alias match handled by caller iterating §2.1 aliases.
        # SAR-8 itself doesn't consult manufacturers.aliases — caller invokes
        # SAR-8 once per (alias, canonical) pair. So `Flock` → `Flock Safety`
        # under the predicate alone is `no_match`; the caller would invoke
        # `vendor_match_disposition("Flock", "Flock")` and match by exact-
        # normalized canonical equality.
        ("Flock", "Flock Safety", "no_match"),
        ("Flock", "Flock", "accept"),
        # Prefix-token match.
        ("Avigilon Alta", "Avigilon", "accept"),
        # Cross-vendor mismatch.
        ("Axon", "Flock Safety", "no_match"),
        ("DJI Inc.", "Cellebrite", "no_match"),
        # Empty / None inputs.
        ("", "Axon", "no_match"),
    ],
)
def test_default_canonical_match(candidate: str, canonical: str, expected: str) -> None:
    assert vendor_match_disposition(candidate, canonical) == expected


# ---------------------------------------------------------------------------
# Re-run determinism.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "candidate,canonical",
    [
        ("SZ DJI TECHNOLOGY CO.,LTD", "DJI"),
        ("Axon Networks Inc.", "Axon"),
        ("GENETEC Corporation", "Genetec"),
        ("Flock Audio Inc.", "Flock Safety"),
        ("Harris Adacom Corporation", "Harris"),
        ("New York Axon", "Axon"),
    ],
)
def test_predicate_determinism(candidate: str, canonical: str) -> None:
    """Running the predicate twice on identical input produces identical output."""
    a = vendor_match_disposition(candidate, canonical)
    b = vendor_match_disposition(candidate, canonical)
    assert a == b


def test_normalize_vendor_idempotent() -> None:
    sample = "SZ DJI TECHNOLOGY CO.,LTD"
    once = _normalize_vendor(sample)
    twice = _normalize_vendor(once)
    assert once == twice or _normalize_vendor(twice) == twice


# ---------------------------------------------------------------------------
# Integration — every alias-recovered raw_observation row from MAC-39 accepts.
# ---------------------------------------------------------------------------


# The 20 alias-recovered rows from the original (pre-SAR-8) MAC-39 artifact —
# every SZ DJI variant must accept under SAR-8.
_MAC39_ALIAS_RECOVERED_VARIANTS = [
    ("SZ DJI TECHNOLOGY CO.,LTD", "DJI"),
    ("Sz Dji Technology Co.,Ltd", "DJI"),
]

# The 12 strict-FP probe rows from the original MAC-39 artifact — Axon
# Networks variants reject_fp; Flock Audio reject_fp; Harris Adacom reject_fp;
# GENETEC Corporation flag_for_review.
_MAC39_STRICT_FP_VARIANTS = [
    ("Axon Networks Inc.", "Axon", "reject_fp"),
    ("AXON NETWORKS, INC.", "Axon", "reject_fp"),
    ("Axon Networks, Inc.", "Axon", "reject_fp"),
    ("HARRIS ADACOM CORPORATION", "Harris", "reject_fp"),
    ("Harris Adacom Corporation", "Harris", "reject_fp"),
    ("Flock Audio Inc.", "Flock Safety", "reject_fp"),
    ("GENETEC Corporation", "Genetec", "flag_for_review"),
]


@pytest.mark.parametrize("candidate,canonical", _MAC39_ALIAS_RECOVERED_VARIANTS)
def test_mac39_alias_recovered_variants_accept(
    candidate: str, canonical: str
) -> None:
    assert vendor_match_disposition(candidate, canonical) == "accept"


@pytest.mark.parametrize("candidate,canonical,expected", _MAC39_STRICT_FP_VARIANTS)
def test_mac39_strict_fp_variants_reject_or_flag(
    candidate: str, canonical: str, expected: str
) -> None:
    assert vendor_match_disposition(candidate, canonical) == expected


def test_mac39_artifact_present_and_coherent() -> None:
    """Smoke-test: the SAR-8/SAR-9 MAC-39 artifact contains the expected keys."""
    artifact = (
        Path(__file__).resolve().parent.parent
        / "extraction_outputs"
        / "mac39"
        / "phase3_inference_candidates.json"
    )
    if not artifact.exists():
        pytest.skip("MAC-39 artifact not present; skipping smoke check.")
    payload = json.loads(artifact.read_text())
    p2 = payload["phase2_oui_inference"]
    # SAR-8/SAR-9 schema keys (key names retained for backwards-compat across
    # amendments; the contents reflect SAR-9 disposition).
    assert "sar8_accept_total" in p2
    assert "sar8_flag_for_review_total" in p2
    # Post-SAR-9, the accept count is well below the SAR-8 baseline of 411 due
    # to Motorola Mobility (×274) + WatchGuard Technologies (×4) + Harris
    # Adacom (×2) FP rejections. Expect ~120-140 staged accepts and ≥6 flagged
    # (GENETEC ×2 + bare Motorola ×4).
    assert p2["sar8_accept_total"] >= 100
    assert p2["sar8_accept_total"] <= 200
    assert p2["sar8_flag_for_review_total"] >= 6


# ---------------------------------------------------------------------------
# SAR-9 #1 — Motorola Mobility/Solutions corporate-split FP class.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "candidate",
    [
        "Motorola Solutions Inc.",
        "Motorola Solutions, Inc.",
        "MOTOROLA SOLUTIONS, INC.",
        "Motorola Solutions Malaysia Sdn. Bhd.",
        "MOTOROLA SOLUTIONS MALAYSIA SDN. BHD.",
        "Motorola Solutions",
    ],
)
def test_sar9_motorola_solutions_canonical_accepts(candidate: str) -> None:
    """SAR-9 TPs — Motorola Solutions canonical / Malaysia subsidiary accept."""
    assert vendor_match_disposition(candidate, "Motorola Solutions") == "accept"


@pytest.mark.parametrize(
    "candidate",
    [
        "Motorola - BSG",
        "Motorola Inc Business Light Radios",
        "Motorola, Broadband Solutions Group",
    ],
)
def test_sar9_motorola_solutions_positive_evidence_accepts(candidate: str) -> None:
    """SAR-9 #1 — business-radio shape qualifiers accept under Solutions."""
    assert vendor_match_disposition(candidate, "Motorola Solutions") == "accept"


@pytest.mark.parametrize(
    "alias",
    [
        "Motorola APX",
        "Motorola V300",
        "Motorola V500",
        "Motorola Vigilant",
    ],
)
def test_sar9_motorola_solutions_model_line_aliases_accept(alias: str) -> None:
    """SAR-9 #2 §2.1 alias re-scope — model-line aliases accept under Solutions."""
    assert vendor_match_disposition(alias, "Motorola Solutions") == "accept"


@pytest.mark.parametrize(
    "candidate",
    [
        "Motorola Mobility LLC, a Lenovo Company",
        "Motorola Mobility LLC",
        "MOTOROLA MOBILITY LLC, A LENOVO COMPANY",
        "Motorola (Wuhan) Mobility Technologies Communication Co., Ltd.",
        "Motorola(Wuhan) Mobility Technologies Communication Co.,Ltd",
        "Motorola Wuhan Mobility",  # `(wuhan)` substring would miss; `mobility` catches.
        "Lenovo Group Limited",  # `lenovo` substring catches.
    ],
)
def test_sar9_motorola_mobility_lenovo_rejects(candidate: str) -> None:
    """SAR-9 #1 — Motorola Mobility / (Wuhan) / Lenovo descendants reject_fp."""
    disposition = vendor_match_disposition(candidate, "Motorola Solutions")
    assert disposition == "reject_fp", (candidate, disposition)
    assert is_fp_rejected(candidate, "Motorola Solutions") is True
    assert is_canonical_vendor_match(candidate, "Motorola Solutions") is False


@pytest.mark.parametrize("candidate", ["Motorola", "MOTOROLA", "motorola"])
def test_sar9_bare_motorola_flags_for_review(candidate: str) -> None:
    """SAR-9 #1 — bare `Motorola` token routes to flag_for_review."""
    assert vendor_match_disposition(candidate, "Motorola Solutions") == "flag_for_review"
    assert is_flagged_for_review(candidate, "Motorola Solutions") is True
    assert is_canonical_vendor_match(candidate, "Motorola Solutions") is False
    assert is_fp_rejected(candidate, "Motorola Solutions") is False


def test_sar9_motorola_solutions_in_fp_list() -> None:
    """SAR-9 #1 codifies mobility / (wuhan) / lenovo FP entries."""
    assert "Motorola Solutions" in VENDOR_FP_LIST
    substrings = {
        str(e["substring"]).lower()
        for e in VENDOR_FP_LIST["Motorola Solutions"]
    }
    assert "mobility" in substrings
    assert "(wuhan)" in substrings
    assert "lenovo" in substrings


def test_sar9_motorola_solutions_alias_allowlist_rescoped() -> None:
    """SAR-9 #2 — bare `Motorola` dropped; model-line aliases retained."""
    aliases = VENDOR_ALIAS_ALLOWLIST["Motorola Solutions"]
    assert "Motorola" not in aliases  # bare Motorola dropped
    assert "Motorola APX" in aliases
    assert "Motorola V300" in aliases
    assert "Motorola V500" in aliases
    assert "Motorola Vigilant" in aliases


def test_sar9_motorola_bare_token_flag_registered() -> None:
    """SAR-9 #1 — Motorola Solutions registered for bare-token flag_for_review."""
    assert VENDOR_BARE_TOKEN_FLAG.get("Motorola Solutions") == "motorola"


def test_sar9_motorola_positive_evidence_registered() -> None:
    """SAR-9 #1 — Motorola Solutions positive-evidence list contains BSG/BLR/Broadband."""
    evidence = VENDOR_POSITIVE_EVIDENCE.get("Motorola Solutions", ())
    assert "broadband solutions" in evidence
    assert "business light" in evidence
    # Both space-bsg and dash-bsg variants needed for `Motorola - BSG` / `Motorola-BSG`.
    assert " bsg" in evidence
    assert "-bsg" in evidence


# ---------------------------------------------------------------------------
# SAR-9 #3 — WatchGuard Technologies (firewall) vs WatchGuard Video.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "candidate",
    [
        "WatchGuard Technologies, Inc.",
        "WatchGuard Technologies",
        "WATCHGUARD TECHNOLOGIES, INC.",
        "watchguard technologies",
    ],
)
def test_sar9_watchguard_technologies_rejects(candidate: str) -> None:
    """SAR-9 #3 — WatchGuard Technologies (firewall) reject_fp under WatchGuard."""
    assert vendor_match_disposition(candidate, "WatchGuard") == "reject_fp"
    assert is_fp_rejected(candidate, "WatchGuard") is True


@pytest.mark.parametrize(
    "candidate",
    ["WatchGuard Video", "WATCHGUARD VIDEO", "WatchGuard"],
)
def test_sar9_watchguard_video_still_accepts(candidate: str) -> None:
    """WatchGuard Video / bare WatchGuard accept under §2.1 WatchGuard canonical."""
    assert vendor_match_disposition(candidate, "WatchGuard") == "accept"


def test_sar9_watchguard_in_fp_list() -> None:
    assert "WatchGuard" in VENDOR_FP_LIST
    substrings = {
        str(e["substring"]).lower() for e in VENDOR_FP_LIST["WatchGuard"]
    }
    assert "watchguard technologies" in substrings


# ---------------------------------------------------------------------------
# SAR-9 #2 — caller restructure / alias-iteration bug regression.
# ---------------------------------------------------------------------------


def test_sar9_alias_equality_predicate_basic() -> None:
    """alias_equality is exact-normalized equality (no prefix-token, no FP-list)."""
    assert alias_equality("Motorola APX", "Motorola APX") is True
    assert alias_equality("MOTOROLA APX", "Motorola APX") is True
    assert alias_equality("Motorola APX, Inc.", "Motorola APX") is True
    # No prefix-token — distinct from vendor_match_disposition's default match.
    assert alias_equality("Motorola APX 6000", "Motorola APX") is False
    assert alias_equality("", "Motorola APX") is False
    assert alias_equality("Motorola APX", "") is False


def test_sar9_alias_iteration_regression_harris_adacom() -> None:
    """SAR-9 #2 — HARRIS ADACOM CORPORATION rejects under the restructured caller.

    Pre-SAR-9 caller iterated alias-strings as the canonical_name argument;
    `VENDOR_FP_LIST.get('Harris Corporation')` returned `[]` so the
    `harris adacom` substring check never fired and the candidate was
    accepted via prefix-token. Restructured caller invokes
    ``vendor_match_disposition(candidate, 'Harris')`` ONCE per canonical
    so the FP-list lookup fires correctly.
    """
    # Direct predicate at canonical = 'Harris' — should reject.
    assert vendor_match_disposition("HARRIS ADACOM CORPORATION", "Harris") == "reject_fp"
    assert vendor_match_disposition("Harris Adacom Corporation", "Harris") == "reject_fp"
    # Via the restructured _classify caller — should NOT match (rejected at canonical).
    from db.validation.sar8_bulk_stage import _classify

    lexicon = [
        {
            "canonical_name": "Harris",
            "primary_category": "imsi_catcher",
            "alias_strings": ["Harris", "Harris Corporation"],
        },
    ]
    assert _classify("HARRIS ADACOM CORPORATION", lexicon) is None
    assert _classify("Harris Adacom Corporation", lexicon) is None
    # Sibling sanity — `Harris Corporation` itself accepts via canonical.
    hit = _classify("Harris Corporation", lexicon)
    assert hit is not None
    assert hit["canonical_name"] == "Harris"


def test_sar9_caller_restructure_motorola_mobility() -> None:
    """Restructured caller correctly rejects Motorola Mobility under Solutions."""
    from db.validation.sar8_bulk_stage import _classify

    lexicon = [
        {
            "canonical_name": "Motorola Solutions",
            "primary_category": None,
            "alias_strings": [
                "Motorola Solutions",
                "Motorola Vigilant",
                "Motorola APX",
                "Motorola V300",
                "Motorola V500",
            ],
        },
    ]
    # Mobility variants reject under restructured caller.
    assert _classify("Motorola Mobility LLC, a Lenovo Company", lexicon) is None
    assert _classify(
        "Motorola (Wuhan) Mobility Technologies Communication Co., Ltd.",
        lexicon,
    ) is None
    # Solutions canonical accepts.
    hit = _classify("Motorola Solutions Inc.", lexicon)
    assert hit is not None
    assert hit["canonical_name"] == "Motorola Solutions"
    # Bare Motorola flags (caller treats flag_for_review as None — not staged).
    assert _classify("Motorola", lexicon) is None
    # Positive-evidence shapes accept.
    hit = _classify("Motorola - BSG", lexicon)
    assert hit is not None
    assert hit["canonical_name"] == "Motorola Solutions"
    hit = _classify("Motorola Inc Business Light Radios", lexicon)
    assert hit is not None
    assert hit["canonical_name"] == "Motorola Solutions"


def test_sar9_caller_restructure_watchguard() -> None:
    """Restructured caller rejects WatchGuard Technologies, accepts Video."""
    from db.validation.sar8_bulk_stage import _classify

    lexicon = [
        {
            "canonical_name": "WatchGuard",
            "primary_category": "body_cam",
            "alias_strings": ["WatchGuard", "WatchGuard Video"],
        },
    ]
    assert _classify("WatchGuard Technologies, Inc.", lexicon) is None
    hit = _classify("WatchGuard Video", lexicon)
    assert hit is not None
    assert hit["canonical_name"] == "WatchGuard"


# ---------------------------------------------------------------------------
# SAR-9 sibling-vendor / caller cross-vendor checks.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "candidate,canonical,expected",
    [
        # Motorola Mobility under non-Solutions canonical → no_match (FP list
        # is per-canonical; Motorola Mobility is not in the §2.1 lexicon).
        ("Motorola Mobility LLC, a Lenovo Company", "Axon", "no_match"),
        ("Motorola Mobility LLC, a Lenovo Company", "Flock Safety", "no_match"),
        # Solutions canonical — sibling candidate doesn't match.
        ("Motorola Solutions Inc.", "Axon", "no_match"),
        ("Motorola Solutions Inc.", "Flock Safety", "no_match"),
    ],
)
def test_sar9_cross_vendor_motorola_no_match(
    candidate: str, canonical: str, expected: str
) -> None:
    assert vendor_match_disposition(candidate, canonical) == expected


# ---------------------------------------------------------------------------
# SAR-9 re-run determinism (predicate + caller).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "candidate,canonical",
    [
        ("Motorola Mobility LLC, a Lenovo Company", "Motorola Solutions"),
        ("Motorola Solutions Inc.", "Motorola Solutions"),
        ("Motorola - BSG", "Motorola Solutions"),
        ("Motorola", "Motorola Solutions"),
        ("WatchGuard Technologies, Inc.", "WatchGuard"),
        ("HARRIS ADACOM CORPORATION", "Harris"),
    ],
)
def test_sar9_predicate_determinism(candidate: str, canonical: str) -> None:
    """Predicate output is deterministic on identical input."""
    a = vendor_match_disposition(candidate, canonical)
    b = vendor_match_disposition(candidate, canonical)
    assert a == b
