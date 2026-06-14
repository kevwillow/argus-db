"""MAC-371 — Cohort 1 (BLE trackers / stalkerware) EXTRACTION.

Turns the CTO-verified MAC-364 harvest manifest into structured identifier
candidates for CTO review -> DBArchitect ingest. EXTRACTION ONLY: emits
extraction_outputs/mac364_cohort1_ble/candidates.json. NO DB write, NO ingest,
NO migration, NO export regen, NO push. Raw bytes never enter the git index.

Targets: AirTag, Tile, Samsung SmartTag/SmartTag2, Chipolo.

Discipline (per MAC-371 + bible §7.3 / §8.2 / §8.3 / §4.3 / §11):
  * Anti-hallucination: every candidate carries a cite.excerpt that is a
    verbatim substring of its named raw artifact (re-grepped here, not trusted).
  * §4.3 canonicalization of ble_service_uuid / ble_uuid / ble_characteristic to
    lowercase 8-4-4-4-12. Company-IDs kept as SIG-registry verbatim (0x004C).
  * already_in_db: read-only lookup against live db/argus.db identifiers.
  * §7 conflicts (SIG wins, tagfinder unverified) recorded as conflict_note, not
    as separate rows and not as corroboration.
  * No duplicate (value, identifier_type, vendor).
  * SAR-1 LAA-bit: N/A — no MAC candidates are emitted (OUI/MAC lens out of scope
    per the MAC-371 ruling; trackers broadcast rotating private addresses).
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
OUT_DIR = REPO / "extraction_outputs" / "mac364_cohort1_ble"

SIG_BASE_SUFFIX = "-0000-1000-8000-00805f9b34fb"  # SIG 16-bit base UUID

# --- raw artifact relative paths (provenance-only, gitignored) ---------------
A_COMPANY = "raw/bluetooth_sig/20260613T203034Z_company_identifiers.yaml"
A_MEMBER = "raw/bluetooth_sig/20260613T203034Z_member_uuids.yaml"
A_AIRTAG = ("raw/airguard/app/src/main/java/de/seemoo/at_tracking_detection/"
            "database/models/device/types/AirTag.kt")
A_APPLEFM = ("raw/airguard/app/src/main/java/de/seemoo/at_tracking_detection/"
             "database/models/device/types/AppleFindMy.kt")
A_TILE = ("raw/airguard/app/src/main/java/de/seemoo/at_tracking_detection/"
          "database/models/device/types/Tile.kt")
A_CHIPOLO = ("raw/airguard/app/src/main/java/de/seemoo/at_tracking_detection/"
             "database/models/device/types/Chipolo.kt")
A_SAMSUNG = ("raw/airguard/app/src/main/java/de/seemoo/at_tracking_detection/"
             "database/models/device/types/SamsungTracker.kt")
A_USENIX = "raw/find_my_papers/20260613T203034Z_samsung.txt"
A_PETS = "raw/find_my_papers/20260613T203034Z_popets-2021-0045.txt"
A_OPENHAYSTACK = "raw/openhaystack/20260613T203034Z_openhaystack_main.c"
A_TAGFINDER = "raw/tagfinder/20260613T203034Z_tagfinder.py"

# academic-class sources with no own sources-row yet (DBArchitect mints at ingest).
# Keyed by the corroborating_sids token form "academic:<key>". A per-candidate
# needs_new_source_row is set ONLY when the candidate's PRIMARY source_sid is one
# of these strings (the issue's own FD5A example keeps it null because SIG-34 is
# primary). The full set actually referenced anywhere is aggregated at manifest level.
ACADEMIC_SOURCES = {
    "academic:usenix-2210.14702": {
        "academic_key": "academic:usenix-2210.14702",
        "proposed_name": "USENIX Security '24 — Samsung OF analysis (Yu/Henderson/Tiu/Haines, ANU)",
        "url": "https://arxiv.org/abs/2210.14702", "license_posture": "academic"},
    "academic:pets-2021-0045": {
        "academic_key": "academic:pets-2021-0045",
        "proposed_name": "PETS 2021 — Who Can Find My Devices? (Heinrich/Stute/Kornhuber/Hollick)",
        "url": "https://doi.org/10.2478/popets-2021-0045", "license_posture": "CC-BY"},
    "academic:openhaystack-8d214aa": {
        "academic_key": "academic:openhaystack-8d214aa",
        "proposed_name": "seemoo-lab/openhaystack firmware @ 8d214aa",
        "url": "https://github.com/seemoo-lab/openhaystack/tree/8d214aa",
        "license_posture": "AGPL-3.0_declared"},
}
NSR_USENIX = "academic:usenix-2210.14702"
NSR_PETS = "academic:pets-2021-0045"
NSR_OPENHAYSTACK = "academic:openhaystack-8d214aa"

_file_cache: dict[str, list[str]] = {}


def _lines(rel: str) -> list[str]:
    if rel not in _file_cache:
        p = REPO / rel
        if not p.exists():
            raise FileNotFoundError(f"raw artifact missing: {rel}")
        _file_cache[rel] = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return _file_cache[rel]


def locate(rel: str, token: str, want_next_name: bool = False) -> tuple[int, str]:
    """Return (1-indexed line number, verbatim excerpt) of first line with token.

    Raises if not found — no fabrication. want_next_name appends the following
    line when it is a yaml `name:` row, so company/uuid->vendor binding is auditable.
    """
    lines = _lines(rel)
    for i, ln in enumerate(lines):
        if token in ln:
            excerpt = ln.rstrip("\n")
            if want_next_name and i + 1 < len(lines) and "name:" in lines[i + 1]:
                excerpt = excerpt + "\n" + lines[i + 1].rstrip("\n")
            if len(excerpt) > 200:  # keep excerpts auditable / bounded
                excerpt = excerpt[:200]
            return i + 1, excerpt
    raise ValueError(f"token {token!r} NOT found in {rel} — refusing to fabricate")


def canon_uuid(raw: str) -> str:
    """§4.3 canonical: lowercase hyphenated 8-4-4-4-12.

    16-bit '0xFEED' -> '0000feed-0000-1000-8000-00805f9b34fb'.
    128-bit hyphenated form -> lowercased verbatim.
    """
    s = raw.strip()
    if s.lower().startswith("0x"):
        s = s[2:]
    s = s.replace("-", "").lower()
    if not s or any(ch not in "0123456789abcdef" for ch in s):
        raise ValueError(f"non-hex UUID-like value: {raw!r}")
    if len(s) == 4:  # 16-bit short UUID
        s = "0000" + s
    if len(s) == 8:  # 32-bit / 16-bit-padded -> attach SIG base
        return s + SIG_BASE_SUFFIX
    if len(s) == 32:
        return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"
    raise ValueError(f"cannot canonicalize UUID-like value: {raw!r} (len {len(s)})")


@dataclass
class Spec:
    value_raw: str
    identifier_type: str       # ble_manufacturer_id | ble_service_uuid | ble_uuid | ble_characteristic
    vendor: str
    device_product: str
    source_sid: object         # int sid or "academic:<key>"
    artifact: str
    token: str
    corroborating_sids: list = field(default_factory=list)
    confidence_basis: str = ""
    conflict_note: Optional[str] = None
    needs_new_source_row: Optional[dict] = None
    want_next_name: bool = False
    is_company: bool = False    # keep SIG verbatim form (no UUID canonicalization)


# ---------------------------------------------------------------------------
# 1) SIG company identifiers (ble_manufacturer_id) — sid 34, primary_registry
# ---------------------------------------------------------------------------
COMPANY_SPECS = [
    Spec("0x004C", "ble_manufacturer_id", "Apple, Inc.", "AirTag / Find My ecosystem", 34,
         A_COMPANY, "value: 0x004C", corroborating_sids=[24], want_next_name=True, is_company=True,
         confidence_basis="SIG company_identifiers.yaml (primary_registry, §8.2 70-85; existing canonical row conf 85). "
                          "AirGuard (sid 24) uses equivalent short company 0x4C in AirTag/AppleDevice/AppleFindMy scan filters. "
                          "tagfinder(29) also maps 0x004C->Apple but flagged unverified per §7 (informational, not +5)."),
    Spec("0x067C", "ble_manufacturer_id", "Tile, Inc.", "Tile tracker", 34,
         A_COMPANY, "value: 0x067C", want_next_name=True, is_company=True,
         conflict_note="tagfinder TRACKING_DEVICE_TYPES['TILE'].company_id=0x02D0 (unverified; tagfinder's own table maps "
                       "0x02D0->'Tile' but SIG assigns 0x02D0 elsewhere). SIG 0x067C wins per §7.",
         confidence_basis="SIG company_identifiers.yaml (primary_registry). Single SIG issuer; AirGuard filters Tile by "
                          "serviceData not company-id, so no company-id corroboration."),
    Spec("0x08C3", "ble_manufacturer_id", "CHIPOLO d.o.o.", "Chipolo tracker", 34,
         A_COMPANY, "value: 0x08C3", want_next_name=True, is_company=True,
         conflict_note="tagfinder TRACKING_DEVICE_TYPES['CHIPOLO'].company_id=0x0131 (unverified; tagfinder's own "
                       "COMPANY_IDENTIFIERS maps 0x0131->'Cypress Semiconductor', confirming unreliability). SIG 0x08C3 wins per §7.",
         confidence_basis="SIG company_identifiers.yaml (primary_registry). Single SIG issuer."),
    Spec("0x0075", "ble_manufacturer_id", "Samsung Electronics Co. Ltd.", "Galaxy SmartTag / SmartTag2", 34,
         A_COMPANY, "value: 0x0075", want_next_name=True, is_company=True,
         confidence_basis="SIG company_identifiers.yaml (primary_registry). tagfinder(29) agrees 0x0075->Samsung "
                          "(informational only, tagfinder unverified per §7). AirGuard filters Samsung by serviceData 0xFD5A."),
    Spec("0x02DE", "ble_manufacturer_id", "Samsung SDS Co., Ltd.", "Samsung SDS (secondary Samsung entity)", 34,
         A_COMPANY, "value: 0x02DE", want_next_name=True, is_company=True,
         confidence_basis="SIG company_identifiers.yaml (primary_registry). Secondary Samsung corporate entity; single SIG issuer."),
]

# ---------------------------------------------------------------------------
# 2) SIG member service UUIDs (ble_service_uuid) — sid 34
# ---------------------------------------------------------------------------
APPLE_SIG_UUIDS = ["0xFED4", "0xFED3", "0xFED2", "0xFED1", "0xFED0", "0xFECF", "0xFECE",
                   "0xFECD", "0xFECC", "0xFECB", "0xFECA", "0xFEC9", "0xFEC8", "0xFEC7",
                   "0xFE8B", "0xFE8A", "0xFE25", "0xFD6F", "0xFE13", "0xFD44", "0xFD43",
                   "0xFCB2", "0xFCA0", "0xFC94"]
SAMSUNG_SIG_UUIDS = ["0xFDDB", "0xFD7E", "0xFD6C", "0xFD69", "0xFD5A", "0xFD59",
                     "0xFD4B", "0xFD1D", "0xFC91"]

SERVICE_SPECS: list[Spec] = []

for u in APPLE_SIG_UUIDS:
    extra = {}
    if u == "0xFD44":
        extra = dict(
            confidence_basis="SIG member_uuids.yaml Apple service UUID (primary_registry). tagfinder(29) also lists "
                             "0000FD44 'Apple Nearby' / Find-My UUID set (informational, unverified per §7).",
        )
    else:
        extra = dict(
            confidence_basis="SIG member_uuids.yaml Apple-assigned service UUID (primary_registry, §8.2 70-85). "
                             "Full Apple SIG member set per ratified §B.2 scope; not all are AirTag-specific.",
        )
    SERVICE_SPECS.append(Spec(u, "ble_service_uuid", "Apple, Inc.", "Apple BLE service namespace", 34,
                              A_MEMBER, f"uuid: {u}", want_next_name=True, **extra))

# Tile SIG ×3
SERVICE_SPECS += [
    Spec("0xFEED", "ble_service_uuid", "Tile, Inc.", "Tile offline-finding service", 34,
         A_MEMBER, "uuid: 0xFEED", want_next_name=True, corroborating_sids=[24],
         confidence_basis="SIG member_uuids.yaml + AirGuard Tile.kt offlineFindingServiceUUID 0xFEED (value-level §8.3, 2 issuers). "
                          "tagfinder also lists FEED (informational)."),
    Spec("0xFEEC", "ble_service_uuid", "Tile, Inc.", "Tile service", 34,
         A_MEMBER, "uuid: 0xFEEC", want_next_name=True,
         confidence_basis="SIG member_uuids.yaml Tile-assigned service UUID (primary_registry). Single SIG issuer."),
    Spec("0xFD84", "ble_service_uuid", "Tile, Inc.", "Tile service", 34,
         A_MEMBER, "uuid: 0xFD84", want_next_name=True,
         confidence_basis="SIG member_uuids.yaml Tile-assigned service UUID (primary_registry). Single SIG issuer."),
]
# Chipolo SIG ×2
SERVICE_SPECS += [
    Spec("0xFE33", "ble_service_uuid", "CHIPOLO d.o.o.", "Chipolo offline-finding service", 34,
         A_MEMBER, "uuid: 0xFE33", want_next_name=True, corroborating_sids=[24],
         conflict_note="tagfinder maps Chipolo service-UUID to FEE1/FEE0 (unverified, not in SIG/AirGuard). SIG+AirGuard 0xFE33 wins per §7.",
         confidence_basis="SIG member_uuids.yaml + AirGuard Chipolo.kt offlineFindingServiceUUID 0xFE33 (value-level §8.3, 2 issuers)."),
    Spec("0xFE65", "ble_service_uuid", "CHIPOLO d.o.o.", "Chipolo service", 34,
         A_MEMBER, "uuid: 0xFE65", want_next_name=True,
         confidence_basis="SIG member_uuids.yaml Chipolo-assigned service UUID (primary_registry). Single SIG issuer."),
]
# Samsung SIG ×9 (FD5A + FD59 carry academic corroboration)
for u in SAMSUNG_SIG_UUIDS:
    extra = dict(confidence_basis="SIG member_uuids.yaml Samsung-assigned service UUID (primary_registry). Single SIG issuer.")
    corr: list = []
    nsr = None
    cnote = None
    if u == "0xFD5A":
        corr = [24, "academic:usenix-2210.14702"]
        nsr = NSR_USENIX
        extra = dict(confidence_basis="SIG member_uuids.yaml + AirGuard SamsungTracker.kt offlineFindingServiceUUID 0xFD5A + "
                                      "USENIX'24 'FD5A for registered tags' / Command Service (value-level §8.3, 3 independent issuers).")
    elif u == "0xFD59":
        corr = ["academic:usenix-2210.14702"]
        nsr = NSR_USENIX
        extra = dict(confidence_basis="SIG member_uuids.yaml + USENIX'24 'FD59 for non-registered tags' / Onboarding Service "
                                      "(value-level §8.3, 2 independent issuers).")
    SERVICE_SPECS.append(Spec(u, "ble_service_uuid", "Samsung Electronics Co., Ltd.", "Galaxy SmartTag / SmartTag2", 34,
                              A_MEMBER, f"uuid: {u}", want_next_name=True, corroborating_sids=corr,
                              needs_new_source_row=nsr, conflict_note=cnote, **extra))

# Samsung DFU service FE59 — USENIX-sourced; SIG assigns it to Nordic (cross-vendor chipset)
SERVICE_SPECS.append(
    Spec("FE59", "ble_service_uuid", "Samsung Electronics Co., Ltd.", "SmartTag DFU service (firmware update)",
         "academic:usenix-2210.14702", A_USENIX, "Service UUID FE59",
         needs_new_source_row=NSR_USENIX,
         conflict_note="0xFE59 is assigned in SIG member_uuids.yaml to 'Nordic Semiconductor ASA' — the nRF52833 Buttonless "
                       "Secure DFU service shared across ALL nRF52833 devices, NOT a Samsung-exclusive signal. USENIX'24 "
                       "describes the SmartTag USING this service (the tag runs on nRF52833). Cross-vendor chipset constant; "
                       "Validator should decide attribution (chipset signal vs Samsung-SmartTag).",
         confidence_basis="USENIX'24 §E.3 'DFU Service Service UUID FE59 is a part of the nRF52833 Buttonless Secure DFU service'. "
                          "Single academic issuer; cross-vendor (Nordic) per conflict_note."))

# ---------------------------------------------------------------------------
# 3) 128-bit custom service UUIDs (ble_uuid) — AirGuard sid 24
# ---------------------------------------------------------------------------
BLE_UUID_SPECS = [
    Spec("7DFC9000-7D1C-4951-86AA-8D9728F8D66C", "ble_uuid", "Apple, Inc.", "AirTag sound service", 24,
         A_AIRTAG, "7DFC9000-7D1C-4951-86AA-8D9728F8D66C",
         conflict_note="Live DB has MALFORMED tagfinder-sourced row '7dfc9000-0000-1000-8000-00805f9b34fb' (sid 29, conf 65): "
                       "the 32-bit prefix 7DFC9000 was wrongly base-expanded as if a SIG short UUID. The TRUE 128-bit custom "
                       "UUID is this value. Recommend DBArchitect supersede the malformed row. (Same defect on 7dfc9001/9002/9003.)",
         confidence_basis="AirGuard AirTag.kt AIR_TAG_SOUND_SERVICE (crowdsourced sid 24, §8.2 50-75). tagfinder(29) lists "
                          "truncated '7DFC9000' (prefix agreement, informational)."),
    Spec("87290102-3C51-43B1-A1A9-11B9DC38478B", "ble_uuid", "Apple, Inc.", "Apple Find My accessory — generic-access service", 24,
         A_APPLEFM, "87290102-3C51-43B1-A1A9-11B9DC38478B",
         confidence_basis="AirGuard AppleFindMy.kt GATT_GENERIC_ACCESS_SERVICE (crowdsourced sid 24). Third-party Find My accessory custom service UUID."),
]

# ---------------------------------------------------------------------------
# 4) 128-bit custom GATT characteristics (ble_characteristic) — AirGuard sid 24
#    NOTE: ble_characteristic is export-DROPPED (CP13, analytical-only).
# ---------------------------------------------------------------------------
CHAR_SPECS = [
    Spec("7DFC9001-7D1C-4951-86AA-8D9728F8D66C", "ble_characteristic", "Apple, Inc.", "AirTag sound characteristic", 24,
         A_AIRTAG, "7DFC9001-7D1C-4951-86AA-8D9728F8D66C",
         conflict_note="Live DB has MALFORMED tagfinder row '7dfc9001-0000-1000-8000-00805f9b34fb' (sid 29). True 128-bit form is this. Recommend supersession.",
         confidence_basis="AirGuard AirTag.kt sound characteristic (crowdsourced sid 24). ble_characteristic is analytical-only (export-DROPPED per CP13)."),
    Spec("4F860003-943B-49EF-BED4-2F730304427A", "ble_characteristic", "Apple, Inc.", "Apple Find My accessory — sound characteristic", 24,
         A_APPLEFM, "4F860003-943B-49EF-BED4-2F730304427A",
         confidence_basis="AirGuard AppleFindMy.kt sound characteristic (crowdsourced sid 24). Analytical-only (CP13)."),
    Spec("6AA50003-6352-4D57-A7B4-003A416FBB0B", "ble_characteristic", "Apple, Inc.", "Apple Find My accessory — device-name characteristic", 24,
         A_APPLEFM, "6AA50003-6352-4D57-A7B4-003A416FBB0B",
         confidence_basis="AirGuard AppleFindMy.kt GATT_DEVICE_NAME_CHARACTERISTIC (crowdsourced sid 24). Analytical-only (CP13)."),
]

ALL_SPECS = COMPANY_SPECS + SERVICE_SPECS + BLE_UUID_SPECS + CHAR_SPECS


# ---------------------------------------------------------------------------
# behavioral_signatures candidates (§5 table — NOT (type,value)). CTO to confirm shape.
# ---------------------------------------------------------------------------
@dataclass
class BehavSpec:
    signature_name: str
    description: str
    vendor: str
    source_sid: object
    artifact: str
    token: str
    evidence_json: dict
    corroborating_sids: list = field(default_factory=list)
    needs_new_source_row: Optional[dict] = None


BEHAV_SPECS = [
    BehavSpec(
        "apple_offline_finding_adv_filter",
        "Apple Offline-Finding manufacturer-data scan filter: company 0x4C, data prefix 0x12 0x19 0x10 / mask 0xFF 0x00 0x18 (all Apple devices); offline-only mask 0xFF 0xFF 0x18.",
        "Apple, Inc.", 24, A_AIRTAG,
        "byteArrayOf((0x12).toByte(), (0x19).toByte(), (0x10).toByte())",
        {"company_id": "0x4C", "data": ["0x12", "0x19", "0x10"], "mask": ["0xFF", "0x00", "0x18"],
         "offline_only_mask": ["0xFF", "0xFF", "0x18"]},
        corroborating_sids=["academic:openhaystack-8d214aa", "academic:pets-2021-0045"],
        needs_new_source_row=NSR_OPENHAYSTACK),
    BehavSpec(
        "airtag_offline_finding_adv_layout",
        "AirTag/OF advertisement byte layout: adv_data_length 0x1E, type 0xFF, company 0x004C, OF type 0x12 (registered)/0x07 (unregistered), payload_length 0x19, status byte offset 6, public-key offset 7 (len 22-23, EC P-224), crypto counter offset 31.",
        "Apple, Inc.", 29, A_TAGFINDER, "AIRTAG_ADV_FORMAT = {",
        {"adv_data_length": "0x1E", "adv_data_type": "0xFF", "company_id": "0x004C",
         "registered_payload_type": "0x12", "unregistered_payload_type": "0x07",
         "payload_length": "0x19", "status_byte_offset": 6, "public_key_offset": 7,
         "public_key_length": 23, "crypto_counter_offset": 31},
        corroborating_sids=["academic:openhaystack-8d214aa", "academic:pets-2021-0045"],
        needs_new_source_row=NSR_OPENHAYSTACK),
    BehavSpec(
        "apple_offline_finding_status_bits",
        "AirTag manufacturer-data status byte bit semantics: 0x01 Separated from owner, 0x02 Play Sound, 0x04 Lost Mode.",
        "Apple, Inc.", 29, A_TAGFINDER, '0x01: "Separated from owner"',
        {"0x01": "Separated from owner", "0x02": "Play Sound", "0x04": "Lost Mode"}),
    BehavSpec(
        "samsung_smarttag_lostmode_status_bits",
        "Samsung SmartTag lost-mode status bits 5-7: 001 Premature lost, 010 Lost, 011 Overmature lost, 100 Paired-one, 101 Connected-one, 110 Connected-two.",
        "Samsung Electronics Co., Ltd.", "academic:usenix-2210.14702", A_USENIX,
        "Premature lost mode",
        {"001": "Premature lost", "010": "Lost", "011": "Overmature lost",
         "100": "Paired with one device", "101": "Connected to one device", "110": "Connected to two devices"},
        needs_new_source_row=NSR_USENIX),
    BehavSpec(
        "tile_offline_finding_servicedata_filter",
        "Tile offline-finding scan filter: serviceData 0x02 0x00 / mask 0xFF 0xFF on service UUID 0xFEED.",
        "Tile, Inc.", 24, A_TILE, "byteArrayOf((0x02).toByte(), (0x00).toByte())",
        {"service_uuid": "0000FEED", "service_data": ["0x02", "0x00"], "mask": ["0xFF", "0xFF"]}),
    BehavSpec(
        "samsung_smarttag_servicedata_filter",
        "Samsung SmartTag offline-finding scan filter: serviceData 0x10 / mask 0xF8 on service UUID 0xFD5A.",
        "Samsung Electronics Co., Ltd.", 24, A_SAMSUNG, "byteArrayOf((0x10).toByte())",
        {"service_uuid": "0000FD5A", "service_data": ["0x10"], "mask": ["0xF8"]}),
]


def already_in_db(conn, value: str, identifier_type: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM identifiers WHERE identifier=? AND identifier_type=? AND superseded_by IS NULL LIMIT 1",
        (value, identifier_type)).fetchone()
    return row is not None


def build():
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    candidates = []
    seen = set()
    for s in ALL_SPECS:
        value = s.value_raw if s.is_company else canon_uuid(s.value_raw)
        key = (value, s.identifier_type, s.vendor)
        if key in seen:
            raise ValueError(f"duplicate (value,type,vendor): {key}")
        seen.add(key)
        line, excerpt = locate(s.artifact, s.token, s.want_next_name)
        # integrity self-check: excerpt MUST be a verbatim substring of the artifact
        full = "\n".join(_lines(s.artifact))
        if excerpt not in full:
            raise AssertionError(f"excerpt not greppable in {s.artifact}: {excerpt!r}")
        # needs_new_source_row only when the PRIMARY source has no row (academic:* key)
        nsr = ACADEMIC_SOURCES[s.source_sid] if isinstance(s.source_sid, str) else None
        candidates.append({
            "value": value,
            "identifier_type": s.identifier_type,
            "vendor": s.vendor,
            "device_product": s.device_product,
            "source_sid": s.source_sid,
            "corroborating_sids": s.corroborating_sids,
            "confidence_basis": s.confidence_basis,
            "cite": {"artifact": s.artifact, "line": line, "excerpt": excerpt},
            "conflict_note": s.conflict_note,
            "needs_new_source_row": nsr,
            "already_in_db": already_in_db(conn, value, s.identifier_type),
        })

    behavioral = []
    bseen = set()
    for b in BEHAV_SPECS:
        if b.signature_name in bseen:
            raise ValueError(f"duplicate signature_name: {b.signature_name}")
        bseen.add(b.signature_name)
        line, excerpt = locate(b.artifact, b.token, False)
        full = "\n".join(_lines(b.artifact))
        if excerpt not in full:
            raise AssertionError(f"behav excerpt not greppable in {b.artifact}: {excerpt!r}")
        nsr = ACADEMIC_SOURCES[b.source_sid] if isinstance(b.source_sid, str) else None
        behavioral.append({
            "signature_name": b.signature_name,
            "cellular_generation": None,
            "device_category": "unknown",
            "vendor": b.vendor,
            "description": b.description,
            "evidence_json": b.evidence_json,
            "source_sid": b.source_sid,
            "source_file_relative": b.artifact,
            "source_line": line,
            "corroborating_sids": b.corroborating_sids,
            "needs_new_source_row": nsr,
            "cite": {"artifact": b.artifact, "line": line, "excerpt": excerpt},
            "cto_confirm": "behavioral_signatures table shape per §5 (migration 0010) — CTO to confirm before DBArchitect ingest",
        })
    conn.close()
    return candidates, behavioral


def academic_sources_referenced(candidates, behavioral) -> list:
    """Every academic:* source referenced as a primary OR corroborating source —
    the full set DBArchitect must mint at ingest (corroboration needs the row too)."""
    keys = set()
    for item in list(candidates) + list(behavioral):
        sid = item["source_sid"]
        if isinstance(sid, str) and sid in ACADEMIC_SOURCES:
            keys.add(sid)
        for c in item.get("corroborating_sids", []):
            if isinstance(c, str) and c in ACADEMIC_SOURCES:
                keys.add(c)
    return [ACADEMIC_SOURCES[k] for k in sorted(keys)]


def main():
    candidates, behavioral = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "_meta": {
            "issue": "MAC-371",
            "cohort": "MAC-363 cohort 1 — BLE trackers / stalkerware",
            "harvest_input": "MAC-364#document-harvest (CTO-verified)",
            "harvest_ts_utc": "20260613T203034Z",
            "scope": "EXTRACTION ONLY — candidates for CTO review -> DBArchitect ingest. No DB write/migration/export/push.",
            "targets": ["AirTag", "Tile", "Samsung SmartTag/SmartTag2", "Chipolo"],
            "device_category_note": "All cohort rows map to device_category='unknown' (§2.1 has no tracker/stalkerware value); §11 #13 Lynceus-export carveout applies. Not minted here.",
            "laa_bit_note": "SAR-1 LAA-bit N/A — zero MAC candidates (OUI/MAC lens out of scope per MAC-371 ruling; trackers use rotating private addresses).",
            "pii_redaction_count": 0,
            "pii_note": "Zero PII in candidate values. PETS author emails (lines 43/47) deliberately NOT cited per SAR-5/§11#3.",
            "needs_new_source_rows": academic_sources_referenced(candidates, behavioral),
        },
        "candidates": candidates,
        "behavioral_signatures_candidates": behavioral,
    }
    out = OUT_DIR / "candidates.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # reproducible counts
    from collections import Counter
    by_type = Counter(c["identifier_type"] for c in candidates)
    n_indb = sum(1 for c in candidates if c["already_in_db"])
    n_netnew = len(candidates) - n_indb
    print(f"wrote {out}")
    print(f"identifier candidates: {len(candidates)} | already_in_db={n_indb} net-new={n_netnew}")
    for t, n in sorted(by_type.items()):
        print(f"  {t}: {n}")
    print(f"behavioral_signatures_candidates: {len(behavioral)}")
    # json_valid
    json.loads(out.read_text())
    print("json_valid: OK")


if __name__ == "__main__":
    main()
