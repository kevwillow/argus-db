"""MAC-376 — Cohort 5 (Consumer surveillance) extraction tests.

Locks the integrity catches + cite-paste counts against the raw artifacts and a
frozen extraction-time canonical snapshot (MAC-755 — NOT live canonical; the 26
net-new OUIs have since been promoted). Skips cleanly if the raw artifacts are
absent (CI without the gitignored raw/ tree).
"""
from __future__ import annotations

import sqlite3

import pytest

# MAC-755: read frozen extraction-time canonical, not live db/argus.db. A live
# read makes db_presence_oui() report every one of the 26 net-new OUIs as
# already-held, collapsing the tallies to 0. See tests/cohort_frozen_db.py.
from cohort_frozen_db import freeze_cohort_db

freeze_cohort_db()

from db.sources import cohort5_consumer as c5  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (c5.OUI_FILES["MA-L"].exists() and c5.SIG_YAML.exists()
         and c5.FCC_JSON.exists() and c5.DB.exists()),
    reason="raw artifacts / DB absent (gitignored)",
)


@pytest.fixture(scope="module")
def result():
    conn = sqlite3.connect(f"file:{c5.DB}?mode=ro", uri=True)
    try:
        return c5.build_candidates(conn)
    finally:
        conn.close()


# --- exact-match OUI counts (cite-paste, not memory) ---

def test_ring_exact_13_blocks(result):
    assert result["tally"]["pure_play"]["Ring"]["total_blocks"] == 13
    assert result["tally"]["pure_play"]["Ring"]["net_new_oui"] == 13


def test_wyze_6_blocks_5_net_new(result):
    # 6 exact blocks but MA-M A4DA222 already in DB as mac_range -> 5 net-new
    t = result["tally"]["pure_play"]["Wyze Labs"]
    assert t["total_blocks"] == 6
    assert t["net_new_oui"] == 5


def test_arlo_is_3_not_4(result):
    # Integrity catch: CTO headline said 4; exact org-name match = 3.
    assert result["tally"]["pure_play"]["Arlo Technologies"]["total_blocks"] == 3


def test_blink_amazon_subbrand_5(result):
    # Integrity finding: Blink = pure-play surveillance sub-brand inside Amazon.
    assert result["tally"]["pure_play"]["Blink (Amazon)"]["total_blocks"] == 5
    assert result["tally"]["pure_play"]["Blink (Amazon)"]["net_new_oui"] == 5


def test_net_new_oui_total_26(result):
    assert result["net_new_oui_total"] == 26


# --- anti-fabrication / honest-absence ---

def test_no_eufy_or_anker_oui_candidate(result):
    # 70B3D5C4B = ANKER-EAST (RU), NOT eufy/Anker Innovations. eufy has 0 own OUI.
    vendors = {c["manufacturer"] for c in result["candidates"]}
    assert "eufy" not in vendors
    assert "Anker" not in vendors
    assert not any("70B3D5C4B" in c["value"] for c in result["candidates"])


def test_mixed_use_zero_tied_to_sku(result):
    # No FCC-ID exhibit fetched -> 0 mixed-use OUIs tie to a surveillance SKU.
    for v in result["tally"]["mixed_use"].values():
        assert v["tied_to_surveillance_sku"] == 0
        assert v["unscoped"] == v["total_blocks"]


# --- enum / schema conformance ---

VALID_DEVCAT = {
    "alpr", "imsi_catcher", "body_cam", "police_radio", "drone", "gunshot_detect",
    "hacking_tool", "covert_cam", "gps_tracker", "face_recog", "drone_detect",
    "unknown", "automotive_telematics", "cctv_camera", "persistent_surveillance",
    "through_wall_radar", "network_surveillance",
}


def test_no_doorbell_invalid_category(result):
    # `doorbell` is NOT in the §2.1 enum -> must map to cctv_camera.
    for c in result["candidates"]:
        assert c["device_category"] in VALID_DEVCAT
        assert c["device_category"] != "doorbell"


def test_all_oui_candidates_primary_registry_ceiling(result):
    for c in result["candidates"]:
        if c["identifier_type"] == "oui":
            assert c["proposed_confidence_ceiling"] == 85  # §8.2 single-source
            assert c["source_lens"] == "registration"


# --- already-in-db reference (NOT net-new) ---

def test_eight_sig_ids_already_in_db(result):
    refs = result["sig_company_id_reference"]
    assert len(refs) == 8
    for r in refs:
        assert r["db_presence"].startswith("already_in_db:")
        assert "device_category=unknown" in r["db_presence"]


def test_fcc_grantee_codes_already_loaded(result):
    refs = result["fcc_grantee_reference"]
    assert refs and all(r["db_presence"] == "already_in_fcc_grantees" for r in refs)


def test_play_404s_are_honest_absence(result):
    pkgs = {p["package_id"] for p in result["play_listing_404"]}
    assert pkgs == {"com.obsidian.v4", "com.netgear.android"}


# --- idempotency / determinism ---

def test_idempotent_rebuild(result):
    conn = sqlite3.connect(f"file:{c5.DB}?mode=ro", uri=True)
    try:
        again = c5.build_candidates(conn)
    finally:
        conn.close()
    assert again["candidates"] == result["candidates"]
    assert again["net_new_oui_total"] == result["net_new_oui_total"]
