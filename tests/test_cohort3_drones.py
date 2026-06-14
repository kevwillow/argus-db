"""Tests for MAC-374 Cohort 3 (Drones) extraction.

Anti-hallucination + discipline checks (bible §7.3 / §8.2 / §8.3 / §4.4 / §11 +
MAC-366 integrity rulings 1-12). Mirrors the MAC-371/MAC-372 posture: positive +
negative assertions, ≤200-char excerpt enforcement, no-PII, determinism, the
expansion-not-greenfield (0 net-new VALUES) reality, and DB-conflict surfacing.
"""
from __future__ import annotations

import json
import re

import pytest

from db.sources import cohort3_drones as c3

RESULT = c3.build()
CANDS = RESULT["candidates"]
BEH = RESULT["behavioral_signatures"]
FAA = RESULT["faa_rid_crossrefs"]
META = RESULT["_meta"]
CONFLICTS = META["db_conflicts_for_remediation"]["fcc_grantee_misattributions"]
RECATS = META["db_conflicts_for_remediation"]["fcc_grantee_recategorizations"]


# ── structural / determinism ─────────────────────────────────────────────────
def test_json_serializable():
    json.dumps(RESULT)


def test_deterministic():
    assert json.dumps(c3.build(), sort_keys=True) == json.dumps(c3.build(), sort_keys=True)


def test_counts_match_meta():
    net_new = [c for c in CANDS if c["db_presence"] == "net-new"]
    already = [c for c in CANDS if c["db_presence"] != "net-new"]
    # EXPANSION not greenfield: 0 net-new identifier VALUES.
    assert META["counts"]["net_new_identifier_values"] == len(net_new) == 0
    assert META["counts"]["already_in_db"] == len(already) == len(CANDS)
    assert META["counts"]["behavioral_signatures"] == len(BEH) == 5
    assert META["counts"]["by_type"] == {
        "ble_manufacturer_id": 2, "ble_company_id": 1, "fcc_grantee_code": 11}


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
    out = c3._excerpt(long)
    assert len(out) == 200 and out.endswith("…")
    assert c3._excerpt("short") == "short"  # positive: no truncation


# ── anti-hallucination: cites re-greppable from disk ─────────────────────────
def test_sig_cites_regreppable():
    # build() re-greps the SIG yaml via _grep_line (raises if absent); assert values.
    ble = {c["value"]: c for c in CANDS if c["identifier_type"] == "ble_manufacturer_id"}
    assert set(ble) == {"0x08AA", "0x0043"}
    assert "DJI" in ble["0x08AA"]["cite_excerpt"]
    assert "PARROT AUTOMOTIVE SAS" in ble["0x0043"]["cite_excerpt"]


def test_grep_line_raises_on_absent():
    with pytest.raises(AssertionError):
        c3._grep_line(c3.SIG_YAML, "this_string_is_not_in_the_file_xyzzy")


# ── ruling 1: Parrot entity-split, no §8.3 hub-and-spoke lift ─────────────────
def test_parrot_entity_split_caveat():
    ble = {c["value"]: c for c in CANDS if c["identifier_type"] == "ble_manufacturer_id"}
    assert "entity-split" in ble["0x0043"]["notes"]
    assert "PARROT DRONE SAS" in ble["0x0043"]["notes"]      # the drone arm
    assert "hub-and-spoke" in ble["0x0043"]["notes"].lower()


# ── §4.4 / §7.5 export-membership reality (checked, not from memory) ──────────
def test_ble_unknown_category_export_banned():
    ble = {c["value"]: c for c in CANDS if c["identifier_type"] == "ble_manufacturer_id"}
    for v in ("0x08AA", "0x0043"):
        assert ble[v]["device_category"] == "unknown"
        assert "§11 #13" in ble[v]["export_membership"]
        assert "NOT in either feed" in ble[v]["export_membership"]


def test_fcc_grantee_export_excluded():
    for c in CANDS:
        if c["identifier_type"] == "fcc_grantee_code":
            assert "DROPPED" in c["export_membership"]
            assert "EXPORT-EXCLUDED" in c["export_membership"]
            assert c["source_lens"] == "registration"


# ── ruling 10: all drone-arm grantees already in DB; tally separate ──────────
def test_all_drone_grantees_already_in_db():
    g = {c["value"]: c for c in CANDS if c["identifier_type"] == "fcc_grantee_code"}
    expected = {"2ATQR", "2AGNT", "2AG6I", "2AHAN", "2AHAY", "2ANDR",
                "2AS9V", "2AS9W", "2AS9X", "QT9", "SS3"}
    assert set(g) == expected
    for code in expected:
        assert g[code]["db_presence"].startswith("already_in_db"), code
        assert g[code]["proposed_confidence_ceiling"] == 90  # primary_registry §8.2


# ── ruling 3/4 + DB-conflict surfacing (§11 #1/#7/#8) ────────────────────────
def test_hard_conflicts_autel_automotive():
    hard = {c["code"]: c for c in CONFLICTS if c["severity"] == "HARD"}
    assert set(hard) == {"CMJ", "WQ8", "XPR"}
    # CMJ frozen FCC = Autel Corporation (automotive), DB says drone vendor.
    assert "Autel Corporation" in hard["CMJ"]["frozen_fcc_truth"]
    assert "drone" in hard["CMJ"]["db_says"]
    assert "Autel Intelligent" in hard["WQ8"]["frozen_fcc_truth"]


def test_soft_conflicts_parrot_exclusion_fps():
    soft = {c["code"]: c for c in CONFLICTS if c["severity"] == "SOFT"}
    assert set(soft) == {"CHK", "RKU", "RKX", "XNP"}


def test_fp_correctly_absent():
    absent = {c["code"]: c for c in CONFLICTS if c["severity"] == "OK-ABSENT"}
    # ruling 4: 'DJI'=Seragen Diagnostics + HDF=Autelca correctly NOT minted as grantees.
    assert "DJI" in absent and "Seragen" in absent["DJI"]["frozen_fcc_truth"]
    assert "HDF" in absent and "Autelca" in absent["HDF"]["frozen_fcc_truth"]
    for c in absent.values():
        assert c["db_id"] is None


def test_dji_grantee_recategorizations():
    codes = {r["code"] for r in RECATS}
    assert codes == {"2AHAN", "2AHAY", "2ANDR", "2AS9V", "2AS9W", "2AS9X"}
    for r in RECATS:
        assert "unknown" in r["db_state"]
        assert "drone" in r["recommendation"]
        assert "§11 #8" in r["recommendation"]


def test_conflict_counts():
    assert META["counts"]["db_conflicts_hard"] == 3
    assert META["counts"]["db_conflicts_soft"] == 4
    assert META["counts"]["recategorizations_recommended"] == 6


# ── §11 #3 / SAR-5 PII discipline ────────────────────────────────────────────
def test_pii_redaction_count():
    # 22 grantee codes (11 drone-arm + 11 FPs), all with a suppressed contact_name.
    if META["fcc_csv_verified"]:
        assert META["pii_redaction_count"] == 22
    else:
        assert META["pii_redaction_count"] == 0  # CSV absent in CI


def test_no_pii_in_output():
    blob = json.dumps(RESULT).lower()
    # no email PII anywhere
    assert not re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", blob), "email PII leak"
    # The pii_note may NAME the suppressed columns descriptively (that's good
    # documentation, not a leak — the *values* are covered by the regex above and
    # by test_no_contact_name_pii_from_frozen_csv). Assert the suppression is
    # documented (positive) rather than banning the column words.
    assert "never read" in META["pii_note"].lower()
    assert "contact_name" in META["pii_note"]


def test_no_contact_name_pii_from_frozen_csv():
    # negative: if the SSD frozen CSV is present, no surfaced output token may match
    # any grantee's contact_name value (word-boundary, len>=4 to avoid collisions).
    if not c3.FCC_CSV.exists():
        pytest.skip("frozen FCC CSV not mounted (CI)")
    import csv as _csv
    blob = json.dumps(RESULT).lower()
    want = {code for code, *_ in c3._DRONE_GRANTEES} | {code for code, *_ in c3._EXCLUSION_FPS}
    with c3.FCC_CSV.open(newline="", encoding="utf-8", errors="replace") as f:
        for row in _csv.DictReader(f):
            if row["grantee_code"].strip() in want:
                contact = (row.get("contact_name") or "").lower()
                for tok in [t for t in re.split(r"\s+", contact) if len(t) >= 4]:
                    assert not re.search(rf"\b{re.escape(tok)}\b", blob), \
                        f"contact_name token '{tok}' leaked"


# ── behavioral signatures (§5 / behavioral_signatures shape) ─────────────────
def test_behavioral_shape():
    for b in BEH:
        assert b["device_category"] == "drone"
        assert b["cellular_generation"] is None
        assert b["evidence"] and all("locus" in e for e in b["evidence"])
        assert b["proposed_confidence_ceiling"] <= 95
        assert b["source_lens"] in ("structural", "observation")


def test_behavioral_structural_vs_app():
    by = {b["signature_name"][:20]: b for b in BEH}
    structural = [b for b in BEH if isinstance(b["source_ref"], int)]
    app = [b for b in BEH if str(b["source_ref"]).startswith("needs_new_source_row:")]
    assert len(structural) == 3  # opendroneid x2 + dji_droneid
    assert len(app) == 2         # Skydio + Autel companion apps


def test_behavioral_apk_evidence_not_missing():
    # manufacturer_app signatures: if the gitignored APK is present every locus
    # must re-grep (verified); if absent, apk_absent. Structural ones are n/a.
    for b in BEH:
        chk = b["apk_evidence_check"]
        assert chk in ("verified", "apk_absent", "n/a_structural") or chk.startswith("error:"), chk


def test_dji_droneid_is_rf_not_beacon():
    # ruling 5b: DJI legacy DroneID is an OFDM RF frame, distinct from ASTM beacon.
    dji = [b for b in BEH if "OFDM RF frame" in b["signature_name"]]
    assert len(dji) == 1
    assert "DISTINCT from the ASTM" in dji[0]["notes"]
    assert dji[0]["source_ref"] == 28


# ── ruling 5: FAA RID = attribution/cross-ref, not promoted values ───────────
def test_faa_crossref_not_promoted():
    vendors = {f["vendor"]: f for f in FAA}
    assert vendors["skydio"]["rid_doc_count"] == 8
    assert vendors["autel"]["rid_doc_count"] == 22
    assert vendors["parrot"]["rid_doc_count"] == 3
    for f in FAA:
        assert "NOT promoted" in f["disposition"]
    # no FAA modelName string leaked in as an identifier candidate value
    model_tokens = {"EVO II", "ANAFI Ai", "X2E SDR21V1", "Dragonfish Pro"}
    cand_vals = {c["value"] for c in CANDS}
    assert not (model_tokens & cand_vals)


def test_no_synthetic_prefix_promoted():
    # §11 #1: the DragonSync synthetic test fixture prefix must never be a candidate.
    cand_vals = {c["value"] for c in CANDS}
    assert "1581F6BV" not in cand_vals
    assert "1581F6BVYAHSVXLM" not in cand_vals


# ── needs-new-source rows ────────────────────────────────────────────────────
def test_needs_new_source_rows():
    nsr = META["needs_new_source_rows"]
    for k in ("app:com.skydio.r3", "app:com.skydio.enterprise", "app:com.autel.explorer"):
        assert k in nsr and nsr[k]["source_type"] == "manufacturer_app"


# ── honest absences carried forward (ruling 11) ──────────────────────────────
def test_honest_absences():
    blob = " ".join(RESULT["honest_absences"]).lower()
    for needle in ("anduril", "no bluetooth-sig", "synthetic test fixture",
                   "drill-down", "seragen"):
        assert needle in blob, needle
