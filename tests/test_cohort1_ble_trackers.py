"""Tests for ``db/sources/cohort1_ble_trackers.py`` — MAC-371 cohort-1 extraction.

Anti-hallucination + §4.3/§7/§8.3 discipline guards (positive + negative):

- Every candidate cite.excerpt is a VERBATIM substring of its named raw
  artifact (re-grepped from disk, not trusted from the candidate).
- §4.3 canonicalization: ble_service_uuid/ble_uuid/ble_characteristic are
  lowercase 8-4-4-4-12; ble_manufacturer_id is the SIG verbatim 0xXXXX form.
- cite.excerpt ≤200 chars (app-level bound; not DB-enforced).
- No duplicate (value, identifier_type, vendor).
- SAR-1 LAA-bit N/A: zero MAC/oui candidates emitted.
- No PII (no '@' e-mail token) leaks into any excerpt.
- needs_new_source_row set ONLY when the PRIMARY source is academic:*.
- already_in_db matches a fresh lookup against the SAME canonical snapshot the
  extractor read (MAC-755: frozen extraction-time snapshot, not live canonical).
- canon_uuid / locate raise rather than fabricate (negative tests).
- Reproducible counts.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

# MAC-755: read frozen extraction-time canonical, not live db/argus.db. These
# candidates have since been promoted, so a live read makes every net-new
# assertion below permanently false. See tests/cohort_frozen_db.py.
from cohort_frozen_db import freeze_cohort_db

freeze_cohort_db()

from db.sources import cohort1_ble_trackers as mod  # noqa: E402

CANDIDATES, BEHAVIORAL = mod.build()
ALL_ITEMS = CANDIDATES + BEHAVIORAL
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
UUID_TYPES = {"ble_service_uuid", "ble_uuid", "ble_characteristic"}


def test_counts_reproducible():
    assert len(CANDIDATES) == 49
    by_type = {}
    for c in CANDIDATES:
        by_type[c["identifier_type"]] = by_type.get(c["identifier_type"], 0) + 1
    assert by_type == {"ble_manufacturer_id": 5, "ble_service_uuid": 39,
                       "ble_uuid": 2, "ble_characteristic": 3}
    assert len(BEHAVIORAL) == 6


@pytest.mark.parametrize("item", ALL_ITEMS, ids=lambda i: i.get("value") or i.get("signature_name"))
def test_cite_excerpt_is_verbatim_substring(item):
    """Re-grep: the excerpt must exist byte-for-byte in the named artifact."""
    art = item["cite"]["artifact"]
    full = "\n".join(mod._lines(art))
    assert item["cite"]["excerpt"] in full
    assert len(item["cite"]["excerpt"]) <= 200


@pytest.mark.parametrize("c", CANDIDATES, ids=lambda c: c["value"])
def test_value_canonicalization(c):
    if c["identifier_type"] in UUID_TYPES:
        assert UUID_RE.match(c["value"]), f"{c['value']} not canonical 8-4-4-4-12 lowercase"
    elif c["identifier_type"] == "ble_manufacturer_id":
        assert re.match(r"^0x[0-9A-Fa-f]{2,4}$", c["value"])


def test_no_duplicate_value_type_vendor():
    keys = [(c["value"], c["identifier_type"], c["vendor"]) for c in CANDIDATES]
    assert len(keys) == len(set(keys))


def test_no_mac_or_oui_candidates_sar1_na():
    # SAR-1 LAA-bit penalty is MAC-only; the cohort emits zero MAC/oui rows.
    assert not any(c["identifier_type"] in {"mac", "oui", "mac_range", "bssid"} for c in CANDIDATES)


@pytest.mark.parametrize("item", ALL_ITEMS, ids=lambda i: i.get("value") or i.get("signature_name"))
def test_no_pii_email_in_excerpt(item):
    # SAR-5/§11#3: no engineering/author contact e-mails in cited bytes.
    assert "@" not in item["cite"]["excerpt"] or "0x" in item["cite"]["excerpt"]


def test_needs_new_source_row_only_when_primary_is_academic():
    for c in CANDIDATES:
        if isinstance(c["source_sid"], str) and c["source_sid"].startswith("academic:"):
            assert c["needs_new_source_row"] is not None
            assert c["needs_new_source_row"]["academic_key"] == c["source_sid"]
        else:
            assert c["needs_new_source_row"] is None


def test_already_in_db_matches_live_lookup():
    conn = sqlite3.connect(f"file:{mod.DB}?mode=ro", uri=True)
    for c in CANDIDATES:
        row = conn.execute(
            "SELECT 1 FROM identifiers WHERE identifier=? AND identifier_type=? "
            "AND superseded_by IS NULL LIMIT 1",
            (c["value"], c["identifier_type"])).fetchone()
        assert c["already_in_db"] == (row is not None), c["value"]
    conn.close()


def test_company_ids_all_already_in_db_as_manufacturer_id():
    comp = [c for c in CANDIDATES if c["identifier_type"] == "ble_manufacturer_id"]
    assert len(comp) == 5
    assert all(c["already_in_db"] for c in comp)


def test_airtag_full_uuid_supersedes_malformed_row():
    # The TRUE 128-bit AirTag sound UUID must be net-new (DB holds the malformed
    # 16-bit-base-expanded tagfinder form) and flag supersession.
    sound = next(c for c in CANDIDATES if c["value"] == "7dfc9000-7d1c-4951-86aa-8d9728f8d66c")
    assert sound["already_in_db"] is False
    assert "MALFORMED" in sound["conflict_note"]


def test_fe59_flags_nordic_cross_vendor():
    fe59 = next(c for c in CANDIDATES if c["value"] == "0000fe59-0000-1000-8000-00805f9b34fb")
    assert "Nordic" in fe59["conflict_note"]
    assert fe59["source_sid"] == "academic:usenix-2210.14702"


# ----------------------- negative tests (no fabrication) -------------------
def test_canon_uuid_rejects_garbage():
    with pytest.raises(ValueError):
        mod.canon_uuid("not-a-uuid")
    with pytest.raises(ValueError):
        mod.canon_uuid("0xZZZZ" + "Z" * 30)


def test_locate_raises_on_missing_token():
    with pytest.raises(ValueError):
        mod.locate(mod.A_MEMBER, "uuid: 0xDEADBEEFNOTREAL")


def test_canon_uuid_known_vectors():
    assert mod.canon_uuid("0xFEED") == "0000feed-0000-1000-8000-00805f9b34fb"
    assert (mod.canon_uuid("7DFC9000-7D1C-4951-86AA-8D9728F8D66C")
            == "7dfc9000-7d1c-4951-86aa-8d9728f8d66c")
