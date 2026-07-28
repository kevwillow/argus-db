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
