"""MAC-406 — Cohort 4 (Consumer smart lock) extraction tests.

Proves candidates.json is regenerated deterministically from the on-disk raw
artifacts (IEEE oui.csv + the 4 CTO-ratified companion APKs), that every
128-bit GATT identifier BYTE-MATCHES its cited dex constant in the named
classesN.dex (the surface the CTO did NOT certify at harvest), that every OUI
cite-paste is a verbatim substring of its oui.csv line, that §11 #7 (<=200-char
excerpt) is app-enforced (positive + negative), and that the authoritative
counts + key exclusion verdicts hold.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from db.sources import cohort4_smartlock as c4  # noqa: E402

RAW_PRESENT = (REPO / c4.A_OUI).exists() and all((REPO / a["artifact"]).exists() for a in c4.APKS)
needs_raw = pytest.mark.skipif(not RAW_PRESENT, reason="gitignored raw artifacts/APKs not on disk")


@pytest.fixture(scope="module")
def payload():
    return c4.build()


# --- §11 #7 excerpt <=200 enforcement (positive + negative) ----------------
def test_clip_truncation_negative():
    long_line = "X" * 500
    out = c4.clip(long_line)
    assert len(out) <= c4.MAX_EXCERPT
    assert out.endswith("…")


def test_clip_short_positive():
    assert c4.clip("  short line  ") == "short line"
    assert len(c4.clip("short line")) <= c4.MAX_EXCERPT


@needs_raw
def test_every_excerpt_within_limit(payload):
    for bucket in ("oui_candidates", "gatt_candidates", "flagged_ambiguous", "excluded"):
        for c in payload[bucket]:
            assert len(c["source_excerpt"]) <= c4.MAX_EXCERPT, c["identifier"]


# --- SAR-5 / §11 #3 PII redaction mechanism (synthetic positive + real zero) -
def test_pii_redaction_mechanism():
    clean, n = c4.redact_person_pii("Attn: John Smith, 110 Sargent Dr. New Haven CT")
    assert n == 1 and "[REDACTED_PERSON]" in clean and "John Smith" not in clean
    # corporate address with street 'Dr.' + city must NOT be redacted
    clean2, n2 = c4.redact_person_pii("110 Sargent Dr. New Haven CT US 06511")
    assert n2 == 0 and clean2 == "110 Sargent Dr. New Haven CT US 06511"


@needs_raw
def test_real_data_pii_count_zero(payload):
    assert payload["_meta"]["pii_redaction_count"] == 0


# --- §11 #1 cite-paste, not memory: OUI verbatim --------------------------
@needs_raw
def test_oui_cite_paste_verbatim(payload):
    oui_lines = (REPO / c4.A_OUI).read_text(encoding="utf-8", errors="replace")
    for c in payload["oui_candidates"]:
        # the recorded excerpt (sans truncation marker) must be a verbatim line substring
        ex = c["source_excerpt"].rstrip("…")
        assert ex in oui_lines, f"OUI excerpt not verbatim in oui.csv: {c['identifier']}"
        # the manufacturer string must appear in its excerpt
        assert c["manufacturer"] in c["source_excerpt"]


# --- §11 #1 cite-paste: 128-bit GATT BYTE-FAITHFULNESS (CTO-uncertified) ---
@needs_raw
def test_gatt_byte_faithful_to_dex(payload):
    """Every promoted/flagged GATT UUID's recorded byte-form is actually present
    in the exact classesN.dex it cites, and lower(byte_form)==identifier."""
    # build dex blob index once per apk: {apk_sha: {dex_entry: bytes}}
    dex_index: dict[str, dict[str, bytes]] = {}
    for apk in c4.APKS:
        idx = {}
        for name, blob in c4._iter_dex_blobs(REPO / apk["artifact"]):
            idx[name] = blob
        dex_index[apk["sha256"]] = idx

    checked = 0
    for c in payload["gatt_candidates"] + payload["flagged_ambiguous"]:
        rp = c["raw_payload"]
        byte_form = rp["byte_form"]
        dex_entry = rp["dex_entry"]
        apk_sha = rp["apk_sha256"]
        blob = dex_index[apk_sha][dex_entry]
        assert byte_form.encode("latin-1") in blob, (
            f"byte-form {byte_form} absent from {dex_entry} (apk {apk_sha[:12]})")
        assert byte_form.lower() == c["identifier"], f"case/identity mismatch {byte_form}"
        assert c["source_excerpt"].rstrip("…") == byte_form  # excerpt IS the byte-paste
        checked += 1
    assert checked == 65  # 54 clean + 11 flagged genuine vendor-distinct


# --- Authoritative dedup'd counts (the harvest "~79" is approximate) -------
@needs_raw
def test_authoritative_counts(payload):
    c = payload["counts"]
    assert c["custom_128bit_distinct_across_4_apks"] == 96
    assert c["cross_vendor_magnets"] == 17           # 16 SDK + 1 all-zero placeholder
    assert c["vendor_unique_128bit"] == 79           # matches harvest "~79"
    assert c["vendor_unique_excluded_sdk_or_placeholder"] == 14
    assert c["genuine_vendor_distinct_gatt"] == 65    # CTO estimate "≈65"
    assert c["gatt_clean_promote"] == 54
    assert c["gatt_flagged_ambiguous"] == 11
    assert c["ble_registry_net_new"] == 0
    assert c["oui_candidates"] == 6
    assert c["oui_promote"] == 2                       # Kwikset + Yale
    assert c["total_promote_candidates"] == 56         # 54 GATT + 2 OUI


# --- §11 #21 cross-vendor magnet exclusion (cited co-occurrence) -----------
@needs_raw
def test_known_magnets_excluded(payload):
    excluded_ids = {e["identifier"] for e in payload["excluded"]}
    # the 16 SDK magnets the harvest named must all be excluded
    for u in [
        "258eafa5-e914-47da-95ca-c5ab0dc85b11",          # all-4 universal magnet
        "6e400001-b5a3-f393-e0a9-e50e24dcca9e",          # Nordic UART (standard)
        "1d14d6ee-fd63-4fa1-bfa4-8f47b42119f0",          # Nordic DFU
        "515d6767-01b7-49e5-8273-c8d11b0f331d",          # Nordic DFU (Kwikset+Schlage)
        "f000ffc0-0451-4000-b000-000000000000",          # TI OAD
    ]:
        assert u in excluded_ids, f"expected magnet excluded: {u}"
    # no magnet may appear among promoted/flagged candidates
    promoted_ids = {c["identifier"] for c in payload["gatt_candidates"] + payload["flagged_ambiguous"]}
    assert excluded_ids.isdisjoint(promoted_ids)


@needs_raw
def test_known_fake_placeholders_routed_to_conflict(payload):
    by_id = {e["identifier"]: e for e in payload["excluded"]}
    # monotonic sequential + all-zero/all-F placeholders -> known_fake_pattern
    assert by_id["00010203-0405-0607-0809-0a0b0c0d1910"]["reason"] == "known_fake_pattern"
    assert by_id["00000000-0000-0000-0000-000000000000"]["reason"] in ("known_fake_pattern", "cross_vendor_sdk_magnet")
    assert by_id["ffffffff-ffff-ffff-ffff-ffffffffffff"]["reason"] == "known_fake_pattern"
    # Nordic-UART ...dcca1e variant (vendor-unique) excluded as bundled SDK, not promoted
    assert "6e400001-b5a3-f393-e0a9-e50e24dcca1e" in by_id
    # Docker / HomeKit non-BLE artifacts excluded
    assert by_id["d861b25a-1edf-11eb-adc1-0242ac120002"]["reason"] == "non_ble_docker_v1_uuid"
    assert by_id["00000014-0000-1000-8000-0026bb765291"]["reason"] == "apple_homekit_ecosystem"


# --- boilerplate / ambiguous flagging (§11 #1 conservative) ----------------
@needs_raw
def test_boilerplate_node_family_flagged_not_promoted(payload):
    flagged = {c["identifier"] for c in payload["flagged_ambiguous"]}
    promoted = {c["identifier"] for c in payload["gatt_candidates"]}
    # August bd4ac61x Sun-OUI family -> flagged, never clean-promoted
    assert "bd4ac610-0b45-11e3-8ffd-0800200c9a66" in flagged
    assert "bd4ac610-0b45-11e3-8ffd-0800200c9a66" not in promoted
    # every flagged candidate carries the ambiguous_extraction marker + conf<=40
    for c in payload["flagged_ambiguous"]:
        assert c["confidence"] <= 40
        assert c["notes"].get("ambiguous_extraction") is True


@needs_raw
def test_clean_promote_families_present(payload):
    promoted = {c["identifier"] for c in payload["gatt_candidates"]}
    # the cleanest cross-checks: Kwikset profile base, Schlage single, August/Ultraloq family heads
    assert "4d050010-766c-42c4-8944-42bc98fc2d09" in promoted
    assert "d4305c76-7a89-4990-9395-9e054e1b4cd3" in promoted
    assert "ce85ad03-0f20-4aed-abe5-b7407dd7cacc" in promoted
    assert "e295c550-69d0-11e4-b116-123b93f75cba" in promoted
    assert "01ff5550-ba5e-f4ee-5ca1-eb1e5e4b1ce0" in promoted


# --- net-new + taxonomy + Wyze guard --------------------------------------
@needs_raw
def test_all_candidates_net_new_and_proposed_category(payload):
    import sqlite3
    conn = sqlite3.connect(f"file:{c4.DB}?mode=ro", uri=True)
    for c in payload["gatt_candidates"] + payload["flagged_ambiguous"] + payload["oui_candidates"]:
        assert c["device_category"] == "smart_lock"
        assert c["notes"]["category_pending_board_ratification"] is True
        rows = c4.already_in_db(conn, c["identifier"])
        assert rows == [], f"expected net-new but DB holds {c['identifier']}"
    conn.close()


@needs_raw
def test_no_wyze_candidate_emitted(payload):
    for c in payload["gatt_candidates"] + payload["flagged_ambiguous"] + payload["oui_candidates"]:
        assert "wyze" not in c["manufacturer"].lower(), "MAC-397 ruling 2: no Wyze candidate"
    # Wyze appears only in held_recat_candidates as do-not-double-promote
    labels = " ".join(h["label"] for h in payload["held_recat_candidates"])
    assert "do-not-double-promote" in labels


@needs_raw
def test_typing_quirk_recorded_not_fixed(payload):
    quirk = [h for h in payload["ble_registry_held"] if "QUIRK" in h["stored_as"]]
    assert len(quirk) == 4  # 0xFE24/0xFCF4/0xFD7B/0xFCBF stored as ble_company_id
    for h in quirk:
        # confirm the DB really stores them under ble_company_id (we do NOT rewrite it)
        assert any(r[2] == "ble_company_id" for r in h["db_rows"])


# --- determinism ----------------------------------------------------------
@needs_raw
def test_deterministic_rebuild():
    import json
    a = json.dumps(c4.build(), sort_keys=True, default=list)
    b = json.dumps(c4.build(), sort_keys=True, default=list)
    assert a == b


@needs_raw
def test_source_row_key_stable_and_unique(payload):
    keys = [c["source_row_key"] for c in
            payload["oui_candidates"] + payload["gatt_candidates"] + payload["flagged_ambiguous"]]
    assert len(keys) == len(set(keys)), "source_row_key collisions"
    # deterministic shape: sha256(doc_url|type|identifier)
    c = payload["oui_candidates"][0]
    assert c["source_row_key"] == c4.source_row_key(c["source_url"], "oui", c["identifier"])
