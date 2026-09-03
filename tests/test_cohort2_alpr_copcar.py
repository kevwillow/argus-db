"""Tests for MAC-372 Cohort 2 (ALPR / cop-car) extraction.

Anti-hallucination + discipline checks (bible §7.3 / §8.2 / §4.4 / §11 + MAC-365
integrity rulings). Mirrors the MAC-371 cohort-1 test posture: positive + negative
assertions, ≤200-char excerpt enforcement, no-PII, determinism, OUI-not-bulk.
"""
from __future__ import annotations

import json
import re

import pytest

# The undistributed inputs are read during module-body execution (c2.build()
# below), before pytest ever looks at a marker, so the guard has to run here --
# above the import that raises.
#
# It probes EVERY input this module cannot degrade without, not just raw/. That
# distinction is load-bearing: cohort2 also reads
# extraction_outputs/mac321_v166/raw/fcc_grantee_full.json
# (db/sources/cohort2_alpr_copcar.py:53 A_FCC_JSON, read at line 217), which is
# gitignored by the same raw/ rule and undistributed for the same reason. A
# guard that only asked "is raw/ there?" passed on a tree that had raw/ but not
# that file, and the module then raised FileNotFoundError at import: pytest
# reported "Interrupted: 1 error during collection" and the ENTIRE session
# aborted, taking every unrelated test with it.
#
# ARGUS_REQUIRE_ALL=1 deliberately lets the import proceed so the real
# FileNotFoundError still surfaces instead of being papered over by a skip.
import os  # noqa: E402

from conftest import (  # noqa: E402
    have_module_artifacts,
    module_artifacts_skip_reason,
)

_C2 = "db.sources.cohort2_alpr_copcar"

pytestmark = pytest.mark.raw_artifacts

if not have_module_artifacts(_C2) and os.environ.get("ARGUS_REQUIRE_ALL") != "1":
    pytest.skip(module_artifacts_skip_reason(_C2), allow_module_level=True)


# MAC-755: read frozen extraction-time canonical, not live db/argus.db. These
# candidates have since been promoted, so a live read makes every net-new
# assertion below permanently false. See tests/cohort_frozen_db.py.
from cohort_frozen_db import freeze_cohort_db

freeze_cohort_db()

from db.sources import cohort2_alpr_copcar as c2  # noqa: E402

RESULT = c2.build()
CANDS = RESULT["candidates"]
BEH = RESULT["behavioral_signatures"]
OUI = RESULT["oui_dispositions"]
META = RESULT["_meta"]


# ── structural / determinism ─────────────────────────────────────────────────
def test_json_serializable():
    json.dumps(RESULT)  # raises if not serializable


def test_deterministic():
    assert json.dumps(c2.build(), sort_keys=True) == json.dumps(c2.build(), sort_keys=True)


def test_counts_match_meta():
    net_new = [c for c in CANDS if c["db_presence"] == "net-new"]
    already = [c for c in CANDS if c["db_presence"] != "net-new"]
    assert META["counts"]["net_new"] == len(net_new) == 16
    assert META["counts"]["already_in_db"] == len(already) == 5
    assert META["counts"]["behavioral_signatures"] == len(BEH) == 2
    assert META["counts"]["by_type_net_new"] == {
        "ssid_pattern": 8, "fcc_grantee_code": 5, "equipment_class_code": 3}


def test_no_duplicate_value_type():
    seen = set()
    for c in CANDS:
        key = (c["value"], c["identifier_type"])
        assert key not in seen, f"duplicate {key}"
        seen.add(key)


# ── §11 #7 ≤200-char source_excerpt (app-level enforced) ─────────────────────
def test_all_excerpts_within_200():
    for c in CANDS:
        assert len(c["cite_excerpt"]) <= 200, f"{c['value']} excerpt {len(c['cite_excerpt'])}>200"


def test_excerpt_truncation_negative():
    long = "x" * 500
    out = c2._excerpt(long)
    assert len(out) == 200 and out.endswith("…")
    assert c2._excerpt("short") == "short"  # positive: no truncation


# ── anti-hallucination: every ssid cite re-greppable from disk ───────────────
def test_ssid_cites_regreppable():
    # build() already re-greps via _grep_line (raises if absent); assert values.
    vals = {c["value"] for c in CANDS if c["identifier_type"] == "ssid_pattern"}
    for must in ["(?i)^vigilant[_-]?.*", "(?i)^genetec[_-]?.*", "(?i)^autovu[_-]?.*",
                 "(?i)^elsag.*", "(?i)^alpr[_-]?.*", "(?i)^lpr[_-]?cam.*"]:
        assert must in vals


def test_grep_line_raises_on_absent():
    with pytest.raises(AssertionError):
        c2._grep_line(c2.A_SSID, "this_string_is_not_in_the_file_xyzzy")


# ── §4.4 export reality + device_category ────────────────────────────────────
def test_ssid_export_dropped_noted():
    for c in CANDS:
        if c["identifier_type"] == "ssid_pattern":
            assert "Export-DROPPED" in c["notes"] or "DROPPED" in c["notes"]
            assert c["source_lens"] == "observation"


def test_alpr_ssid_categories():
    cats = {c["value"]: c["device_category"] for c in CANDS
            if c["identifier_type"] == "ssid_pattern"}
    assert cats["(?i)^vigilant[_-]?.*"] == "alpr"
    assert cats["(?i)^genetec[_-]?.*"] == "alpr"
    assert cats["(?i)^elsag.*"] == "alpr"
    # ruling #8: unverified -> unknown
    assert cats["(?i)^penguin[_-]?.*"] == "unknown"
    assert cats["(?i)^pigvision[_-]?.*"] == "unknown"


# ── ruling #8: Penguin / Pigvision unverified, recommend ≤40 ──────────────────
def test_penguin_pigvision_unverified():
    for c in CANDS:
        if c["value"] in ("(?i)^penguin[_-]?.*", "(?i)^pigvision[_-]?.*"):
            assert c["recommend_confidence"] == 40
            assert "UNVERIFIED" in c["notes"]
            assert c["conflict_note"]


# ── ruling #1: OUI-not-bulk + DB mis-attribution detection ───────────────────
def test_oui_apple_not_nordic():
    by = {o["oui"]: o for o in OUI}
    assert by["C0:A5:3E"]["ieee_authoritative"].startswith("Apple")
    assert by["F0:5C:D5"]["ieee_authoritative"].startswith("Apple")
    assert by["C0:A5:3E"]["repo_matches_ieee"] is False
    assert "repo_flag" in by["C0:A5:3E"]


def test_db_oui_misattributions():
    mis = [o for o in OUI if "DB_MIS_ATTRIBUTION" in o]
    ouis = {o["oui"] for o in mis}
    assert ouis == {"00:0E:8E", "00:11:75", "00:10:8B", "EC:F4:51"}
    assert META["counts"]["db_oui_misattributions"] == 4
    # the 00:14:3E AirLink->Sierra acquisition is NOT a mis-attribution
    by = {o["oui"]: o for o in OUI}
    assert "DB_MIS_ATTRIBUTION" not in by["00:14:3E"]
    assert "lineage_note" in by["00:14:3E"]


def test_oui_correct_ones_not_flagged():
    by = {o["oui"]: o for o in OUI}
    for ok in ("00:A0:D5", "00:30:44", "F4:CE:36"):
        assert "DB_MIS_ATTRIBUTION" not in by[ok]
        assert by[ok]["repo_matches_ieee"] is True


def test_no_oui_emitted_as_candidate():
    # ruling #1: OUIs are dispositions/annotations, never crowdsourced candidates.
    assert not any(c["identifier_type"] == "oui" for c in CANDS)


# ── FCC grantees + IDs ───────────────────────────────────────────────────────
def test_grantee_net_new_and_alpr():
    g = {c["value"]: c for c in CANDS if c["identifier_type"] == "fcc_grantee_code"}
    assert g["VTF"]["db_presence"] == "net-new"
    assert g["VTF"]["device_category"] == "alpr"
    assert g["VTF"]["manufacturer"] == "Remington Elsag"
    assert g["VTF"]["source_lens"] == "registration"
    for code in ("VTF", "2AKB2", "2ATWB", "2ANPO", "WCB"):
        assert g[code]["db_presence"] == "net-new"
    for code in ("2ANC5", "ABZ", "N7N", "UXX", "NCV"):
        assert g[code]["db_presence"].startswith("already_in_db")


def test_ncv_conflict_flagged():
    g = {c["value"]: c for c in CANDS if c["identifier_type"] == "fcc_grantee_code"}
    assert "MIS-ATTRIBUTION" in g["NCV"]["conflict_note"]
    assert "Vigilant Systems Inc" in g["NCV"]["conflict_note"]


def test_fcc_id_candidates():
    e = {c["value"]: c for c in CANDS if c["identifier_type"] == "equipment_class_code"}
    assert e["VTFADM3"]["device_category"] == "alpr"
    assert e["N7NRC76B"]["device_category"] == "unknown"  # §11#10 multi-purpose module
    assert "HONEST-ABSENCE" in e["VTFADM3"]["notes"]


# ── §11 #3 / SAR-5 PII discipline ────────────────────────────────────────────
def test_pii_redaction_count():
    assert META["pii_redaction_count"] == 10


def test_no_contact_name_pii_in_output():
    # negative: the frozen FCC CSV's contact_name VALUES must never surface, and
    # no email PII anywhere. ("contact_name" as a descriptive word in our own
    # pii_note is fine — we assert the actual officer-name values are absent.)
    import sqlite3
    blob = json.dumps(RESULT).lower()
    assert not re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", blob), "email PII leak"
    g = sqlite3.connect(f"file:{c2.DB}?mode=ro", uri=True)
    cur = g.cursor()
    for code, *_ in c2._GRANTEES:
        cur.execute("select contact_name from fcc_grantees where grantee_code=?", (code,))
        row = cur.fetchone()
        contact = (row[0] if row else None) or ""
        for tok in [t for t in re.split(r"\s+", contact.lower()) if len(t) >= 4]:
            # word-boundary match (avoid benign substring collisions e.g. 'chin'<-'china')
            assert not re.search(rf"\b{re.escape(tok)}\b", blob), \
                f"contact_name token '{tok}' ({code}) leaked into output"
    g.close()


# ── behavioral signatures (§5 / migration 0010 shape) ────────────────────────
def test_behavioral_shape():
    for b in BEH:
        assert b["device_category"] == "alpr"
        assert b["cellular_generation"] is None
        assert b["source_ref"].startswith("needs_new_source_row:")
        assert b["evidence"] and all("locus" in e for e in b["evidence"])
        assert b["proposed_confidence_ceiling"] <= 95  # manufacturer_app band


def test_behavioral_apk_evidence_not_missing():
    # If the gitignored APK is present, every evidence locus must re-grep from its
    # DEX (verified); if absent, apk_absent is acceptable. Never MISSING.
    for b in BEH:
        chk = b["apk_evidence_check"]
        assert chk in ("verified", "apk_absent") or chk.startswith("error:"), chk


def test_needs_new_source_rows():
    nsr = META["needs_new_source_rows"]
    assert "app:com.vigilant.solutions.mobilecompanion" in nsr
    assert "app:ai.rekor.rekorblue" in nsr
    for v in nsr.values():
        assert v["source_type"] == "manufacturer_app"
