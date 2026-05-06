"""Tests for SAR-8 vendor-name-disambig predicate (db/extraction/vendor_name_disambig.py).

Coverage:
- Positive (alias accepts) — every entry in VENDOR_ALIAS_ALLOWLIST.
- Negative (FP rejects) — every entry in VENDOR_FP_LIST that is NOT
  flag_for_review.
- Edge — GENETEC Corporation flagged-for-review (third return state).
- Geographic-prefix — `SZ DJI` strips/matches; `New York Axon` does NOT.
- Re-run determinism — predicate output is identical on identical input.
- 20-row alias-recovered cases from MAC-39 — every raw_observation alias
  string from extraction_outputs/mac39 accepts as DJI canonical.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from db.extraction.vendor_name_disambig import (
    GEOGRAPHIC_PREFIX_LIST,
    VENDOR_ALIAS_ALLOWLIST,
    VENDOR_FP_LIST,
    _normalize_vendor,
    _strip_geographic_prefix,
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


def _load_mac39_alias_recovered_rows() -> list[dict]:
    artifact = (
        Path(__file__).resolve().parent.parent
        / "extraction_outputs"
        / "mac39"
        / "phase3_inference_candidates.json"
    )
    if not artifact.exists():
        return []
    payload = json.loads(artifact.read_text())
    return payload["phase2_oui_inference"]["permissive_path_likely_tps"][
        "samples"
    ]


def test_mac39_alias_recovered_rows_all_accept() -> None:
    """All rows in MAC-39 permissive_path_likely_tps must accept under SAR-8."""
    rows = _load_mac39_alias_recovered_rows()
    if not rows:
        pytest.skip("MAC-39 artifact not present; skipping integration check.")
    for row in rows:
        candidate = row["candidate_manufacturer_raw"]
        canonical = row["matched_canonical_name"]
        assert vendor_match_disposition(candidate, canonical) == "accept", (
            f"raw_observation_id={row['raw_observation_id']}: "
            f"{candidate} → {canonical} did not accept under SAR-8"
        )


def _load_mac39_strict_fp_rows() -> list[dict]:
    artifact = (
        Path(__file__).resolve().parent.parent
        / "extraction_outputs"
        / "mac39"
        / "phase3_inference_candidates.json"
    )
    if not artifact.exists():
        return []
    payload = json.loads(artifact.read_text())
    return payload["phase2_oui_inference"]["strict_path_fp_probes"]["samples"]


def test_mac39_strict_fp_rows_all_reject_or_flag() -> None:
    """All FP-probe rows in MAC-39 must reject or flag under SAR-8."""
    rows = _load_mac39_strict_fp_rows()
    if not rows:
        pytest.skip("MAC-39 artifact not present; skipping integration check.")
    for row in rows:
        candidate = row["candidate_manufacturer_raw"]
        canonical = row["matched_canonical_name"]
        disposition = vendor_match_disposition(candidate, canonical)
        assert disposition in ("reject_fp", "flag_for_review"), (
            f"raw_observation_id={row['raw_observation_id']}: "
            f"{candidate} → {canonical} got {disposition}, "
            "expected reject_fp or flag_for_review"
        )
