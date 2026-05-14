"""MAC-99 Stream 1 classifier unit tests.

Exercises `classify_row()` over positive + negative + edge-case rows that mirror
the shapes observed in the live 3,521 + 133 pii_review_hold cohort. The bar is
not "every well-known corporate brand resolves to Class A" — that requires a
manufacturers-table dictionary that doesn't exist yet. The bar is:

1. Strong corporate / institutional / industry signals resolve to Class A.
2. IEEE Private placeholder rows resolve to Class C deterministically.
3. Pure FirstName-LastName person-name shapes with no corporate signal resolve
   to Class B (default-to-HOLD per §11 #3 PII discipline).
4. The classifier is deterministic — same input → same class.
5. Non-ASCII corp suffixes (OÜ, A.Ş, ООО) resolve to Class A.
"""

from __future__ import annotations

import pytest

from db.validation.mac99_ieee_pii_review_triage import classify_row


# -------- Class C: IEEE Private placeholder --------

def test_class_c_ieee_private_placeholder():
    cls, _ = classify_row("Private", "", ieee_private_registrant=True)
    assert cls == "C"


def test_class_c_priority_over_other_signals():
    # Even if the name has corp-suffix shape, ieee_private_registrant wins.
    cls, _ = classify_row("Some Inc.", "", ieee_private_registrant=True)
    assert cls == "C"


# -------- Class A: corporate suffix --------

@pytest.mark.parametrize("name,addr", [
    ("STMICROELECTRONICS S.r.l", "Via Tolomeo 1 Cornaredo IT"),
    ("Quercus Technologies, S.L.", "Av. Onze de Setembre 19 Reus ES"),
    ("Mecco LLC", "290 Executive Drive Cranberry Township PA US"),
    ("ACME Corp", ""),
    ("Foo Inc.", ""),
    ("Mahindra Group", ""),
    ("Some Co., Ltd", ""),
    ("Vendor Holdings", ""),
])
def test_class_a_corp_suffix(name, addr):
    cls, why = classify_row(name, addr, ieee_private_registrant=False)
    assert cls == "A", f"{name!r} expected A, got {cls} ({why})"


def test_class_a_non_ascii_corp_suffix_estonian():
    cls, _ = classify_row("Wayren OÜ", "Tallinn EE", ieee_private_registrant=False)
    assert cls == "A"


def test_class_a_non_ascii_corp_suffix_turkish():
    cls, _ = classify_row("LITUM A.Ş", "Izmir TR", ieee_private_registrant=False)
    assert cls == "A"


def test_class_a_cyrillic_corp_suffix():
    cls, _ = classify_row('ООО "РОНЕКС"', "Москва RU", ieee_private_registrant=False)
    assert cls == "A"


def test_class_a_swiss_sarl():
    cls, _ = classify_row("Weble Sàrl", "Bussigny CH", ieee_private_registrant=False)
    assert cls == "A"


# -------- Class A: government / academic --------

@pytest.mark.parametrize("name,addr", [
    ("CALIFORNIA STATE UNIV", "Sacramento CA US"),
    ("U S DEPARTMENT OF DEFENSE", "Arlington VA US"),
    ("STATE OF FLORIDA DEPT OF TRANSPORTATION", "Tallahassee FL US"),
    ("INSTITUTE OF MARINE ENGINEERING", "London UK"),
    ("National Research Laboratory", "Tokyo JP"),
])
def test_class_a_gov_academic(name, addr):
    cls, why = classify_row(name, addr, ieee_private_registrant=False)
    assert cls == "A", f"{name!r} expected A, got {cls} ({why})"


# -------- Class A: industry / product noun --------

@pytest.mark.parametrize("name", [
    "Atlas Aerospace", "Cyon Drones", "Hale Products", "Eclipse Security",
    "Greenwave Scientific", "Spark Biomedical", "Cheetah Medical",
    "Boston Dynamics", "Spectrum Brands", "General Motors", "Smiths Detection",
    "Leica Biosystems", "Korea Bus Broadcasting", "Cambridge Pixel",
])
def test_class_a_industry_noun(name):
    cls, why = classify_row(name, "", ieee_private_registrant=False)
    # Some of these may match by 3-token rule rather than industry noun, but
    # they all must resolve to Class A.
    assert cls == "A", f"{name!r} expected A, got {cls} ({why})"


# -------- Class A: business-address indicator --------

def test_class_a_business_address_suite():
    cls, _ = classify_row(
        "Pelco", "5005 Industrial Way Suite 100 Clovis CA US 93612",
        ieee_private_registrant=False,
    )
    assert cls == "A"


def test_class_a_business_address_building():
    cls, _ = classify_row(
        "Mavica", "Building 11, Industrial Park Shenzhen CN 518112",
        ieee_private_registrant=False,
    )
    assert cls == "A"


# -------- Class A: stylized brand markers --------

@pytest.mark.parametrize("name", [
    "MAHINDR & MAHINDRA", "DAYOUPLUS", "iREA System Industry",
    "care.ai", "TechArgos", "4D Sistem", "JT", "JBF", "Canal +",
])
def test_class_a_stylized_brand(name):
    cls, why = classify_row(name, "", ieee_private_registrant=False)
    assert cls == "A", f"{name!r} expected A, got {cls} ({why})"


# -------- Class A: lowercase-first-letter (brand stylization) --------

def test_class_a_lowercase_first_letter():
    cls, _ = classify_row(
        "robert juliat", "32 route de beaumont fresnoy en thelle FR",
        ieee_private_registrant=False,
    )
    assert cls == "A"


def test_class_a_lowercase_non_leading_token():
    cls, _ = classify_row(
        "Alias ip", "300 ROUTE DES CRETES SOPHIA ANTIPOLIS FR",
        ieee_private_registrant=False,
    )
    assert cls == "A"


# -------- Class A: single-word brand --------

@pytest.mark.parametrize("name", [
    "IBM", "Wattsense", "Zaptec", "RADAR", "OUTFORM", "ddcpersia",
])
def test_class_a_single_word(name):
    cls, why = classify_row(name, "", ieee_private_registrant=False)
    assert cls == "A", f"{name!r} expected A, got {cls} ({why})"


# -------- Class A: ≥3-token compound name --------

@pytest.mark.parametrize("name", [
    "Shanghai Dahua Scale Factory", "Active Brains Co Japan",
    "Hyundai Heavy Industries Group",
])
def test_class_a_three_or_more_tokens(name):
    cls, why = classify_row(name, "", ieee_private_registrant=False)
    assert cls == "A", f"{name!r} expected A, got {cls} ({why})"


# -------- Class B: FirstName LastName with no corporate signal --------

@pytest.mark.parametrize("name", [
    "Yuval Fichman", "Rudy Tellert", "Walter Grotkasten",
])
def test_class_b_person_name_individual(name):
    # Use an address with no ADDR_BIZ keyword (Street/Building/etc would
    # incorrectly trigger Class A on the address-signal rule).
    cls, _ = classify_row(name, "Hometown", ieee_private_registrant=False)
    assert cls == "B"


def test_class_b_no_corporate_signal_in_address():
    # A 2-token Title-Case name with no business-address indicator and no
    # corp-suffix anywhere → Class B (default-to-HOLD per §11 #3).
    cls, _ = classify_row(
        "Anonymous Person", "Hometown",
        ieee_private_registrant=False,
    )
    assert cls == "B"


def test_class_b_default_to_hold_for_ambiguous_corporate():
    # "Becton Dickinson" looks like FirstName LastName but is actually a major
    # corporation. Without a manufacturers dictionary, the classifier holds it.
    # Per §11 #3 this is the policy-safe outcome.
    cls, why = classify_row(
        "Becton Dickinson", "7 Loveton Circle Sparks MD US 21152",
        ieee_private_registrant=False,
    )
    assert cls == "B"
    assert "§11 #3" in why or "default-to-HOLD" in why


# -------- Class D: ambiguous --------

def test_class_d_empty_name():
    cls, _ = classify_row(None, "", ieee_private_registrant=False)
    assert cls == "D"

    cls, _ = classify_row("", "", ieee_private_registrant=False)
    assert cls == "D"


def test_class_d_mangled_encoding():
    # "Watts A\S" — Danish A/S corporate form mangled by source encoding.
    # The classifier cannot recognize the backslashed variant; escalate to CEO.
    cls, _ = classify_row("Watts A\\S", "Brogade 19D Køge DK", ieee_private_registrant=False)
    assert cls == "D"


# -------- Determinism --------

def test_classifier_deterministic():
    for _ in range(3):
        cls1, _ = classify_row("Atlas Copco", "Antwerpen BE", ieee_private_registrant=False)
        cls2, _ = classify_row("Atlas Copco", "Antwerpen BE", ieee_private_registrant=False)
        assert cls1 == cls2
