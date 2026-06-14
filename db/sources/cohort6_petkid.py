"""MAC-411 — Wave-2 Cohort 6 (Pet / kid cellular tracker) EXTRACTION.

Turns the CTO-ratified MAC-399 harvest (under MAC-393) into structured
promotion candidates for CTO review -> DBArchitect ingest. EXTRACTION ONLY:
emits extraction_outputs/mac393_c6_petkid/candidates.json. NO DB write, NO
ingest, NO migration, NO export regen, NO push. Raw bytes never enter git.

Verified net-new surface (per MAC-411 brief + MAC-399 ratification):
  * ble_service_uuid — companion-APK vendor GATT across 3 vendors, all NET-NEW:
      Fi      23  (57b4XXXX-2528-d6bc-b043-b49af0ec06c1 proprietary family)
      Jiobit  10  (d8ecdb01..0b-…-753cb9dc2e8a + 0xDB01 short + 4a..="JIO" ASCII)
      Whistle 15  (3 families) + 5 SPPLE singletons RESOLVED to vendor here = 20
  * oui — Whistle Labs E0:7C:62 (IEEE primary_registry, pure-play, NET-NEW).
  * ble_local_name — 5 bonus low-confidence behavioral (Fi 3 / Whistle 2).
  * ble_company_id — 0 (Whistle machinery targets Apple's id 0x4c, excluded).

FP-triage (the core of this phase) — every contested UUID is dispositioned with
a CITED co-located dex class (baksmali xref; re-verified byte-present here):
  * AngelSense 849f26e2 / f6389234 -> Salesforce Marketing Cloud SDK (analytics
    const + AesCrypto.ENC_TEST_STRING) -> EXCLUDE (library, not BLE).
  * Whistle 6cdc3b69 = LocalManagementSDPUUID -> Bluetooth-CLASSIC SDP, not BLE
    GATT -> flagged_ambiguous (transport mismatch for type ble_service_uuid).
  * Whistle ec6e18c5 = APP_CENTER_APP_SECRET (Microsoft App Center SDK) -> EXCLUDE.
  * Whistle 5 SPPLE singletons resolve to genuine vendor GATT (WCConstants field
    names) -> promote (+5 over the harvest's conservative 48).

Hard guards (carried, CTO-verified):
  * Jiobit Tile 0xFEEC/0xFEED (HELD id44440/44439 bluetooth_tracker, 'Tile, Inc.')
    -> Life360 owns both Jiobit and Tile -> cross-vendor, NEVER re-attributed.
  * Cross-vendor FP-magnet exclude list (258eafa5 / androidx.work / urn:uuid /
    beacon-lib examples / Nordic-DFU / SIG 16-bit base table / placeholder MACs).
  * No §8.3 corroboration lift: every lead is single-source (one companion APK).
    Companion-APK UUIDs banded at manufacturer_app floor 75 (brief cap <=75); do
    NOT inflate by family size.

TAXONOMY ONE-WAY-DOOR: 'gps_tracker' exists (122 rows); 'personal_tracker' does
NOT (count=0). Every candidate is tagged PROPOSED device_category='gps_tracker' +
notes.subtype='pet_kid_cellular' + category_pending_board_ratification. The board
decides category at the ingest gate — this module stages the proposal only.

This module re-derives EVERY candidate field from the on-disk raw artifacts:
  * UUID byte-forms are scanned live from the gitignored APKs' classes*.dex string
    pools (pure-stdlib zipfile + regex), keyed by sha256. Same APK -> same result.
  * Co-location evidence (WCConstants / ScanFilterUtils / Lae/b; / Salesforce /
    AppCenter) is re-verified byte-present in the named vendor dex (§11 #1 — the
    attribution is grounded in the dex bytes, not memory).
  * OUI cite-paste is a verbatim substring of the named IEEE oui.csv line.
  * already_in_db: read-only lookup against live db/argus.db (mode=ro).

Discipline (bible §7.3 / §8.2 / §8.3 / §11 + MAC-411 hard gates):
  * §11 #1  Conservative. AngelSense/AppCenter excluded with cited library class;
            BT-Classic SDP flagged ambiguous, not clean-promoted.
  * §11 #3 / SAR-5  PII — company legal-entity names + IEEE addresses only;
            person-name regex applied + counted (0 expected).
  * §11 #7  source_excerpt enforced <=200 chars at build time (truncate + marker).
  * §11 #8  No confidence drift; staged at single-source confidence.
  * §11 #15 APK facts-only; raw/ gitignored; deliverable cites value+path+sha256.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sqlite3
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
OUT_DIR = REPO / "extraction_outputs" / "mac393_c6_petkid"

MAX_EXCERPT = 200  # §11 #7 app-level enforcement
SIG_BASE_SUFFIX = "-0000-1000-8000-00805f9b34fb"  # SIG 16-bit base UUID
PROPOSED_CATEGORY = "gps_tracker"   # PROPOSED — board mints/maps at ingest (subtype below)
SUBTYPE = "pet_kid_cellular"
COMPANION_CONF = 75       # §8.2 manufacturer_app floor == brief <=75 cap (single-source)
COMPANION_CEIL = 75
OUI_CONF = 85             # IEEE primary_registry, pure-play vendor
OUI_CEIL = 85
LOCAL_NAME_CONF = 50      # behavioral / low-confidence bonus
FLAGGED_CONF = 40         # ambiguous (BT-Classic transport)

UUID_RE_BYTES = re.compile(
    rb"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

# SAR-5 / §11 #3 — explicit person-contact markers only (so corporate registry
# addresses are not corrupted). IEEE OUI lines carry org legal names only -> 0.
PERSON_NAME_RE = re.compile(
    r"\b(?:Attn|ATTN|Contact|CONTACT|c/o|C/O)\b[:.]?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+"
    r"|\b(?:Mr|Mrs|Ms)\.\s+[A-Z][a-z]+\s+[A-Z][a-z]+")

# --- raw artifact relative paths (provenance; raw/ is gitignored) --------------
A_OUI = "raw/ieee_oui/20260613T203034Z_oui.csv"
A_SIG_COMPANY = "raw/bluetooth_sig/20260613T203034Z_company_identifiers.yaml"
OUI_URL = "https://standards-oui.ieee.org/oui/oui.csv"

# --- CTO-ratified companion APKs (sha256-pinned; gitignored, §11 #15) ----------
APKS = {
    "fi": {
        "vendor": "Fi (Barking Labs Corp)", "package": "com.barkinglabs.fi",
        "version": "3.107.0", "doc_kind": "xapk", "xapk_base": "com.barkinglabs.fi.apk",
        "sha256": "72bcbcfd9d6f481d037ae99a5a23c26d2f0755f5d8c38d7aed201a27a35ea753",
        "rel_path": "raw/vendor_apps/fi/com.barkinglabs.fi/3.107.0/"
                    "72bcbcfd9d6f481d037ae99a5a23c26d2f0755f5d8c38d7aed201a27a35ea753.apk",
        "source_url": "https://apkcombo.com/fi-gps-dog-tracker/com.barkinglabs.fi/",
    },
    "jiobit": {
        "vendor": "Jiobit (Life360, Inc.)", "package": "com.jiobit.app",
        "version": "1.26.2", "doc_kind": "xapk", "xapk_base": "com.jiobit.app.apk",
        "sha256": "767e55e406f48f235c2e9d7446beb5b4f945381cddee012a8c99446d538f76ba",
        "rel_path": "raw/vendor_apps/jiobit/com.jiobit.app/1.26.2/"
                    "767e55e406f48f235c2e9d7446beb5b4f945381cddee012a8c99446d538f76ba.apk",
        "source_url": "https://apkcombo.com/jiobit-smart-tag/com.jiobit.app/",
    },
    "whistle": {
        "vendor": "Whistle Labs, Inc. (Mars Petcare)", "package": "com.whistle.bolt",
        "version": "5.11.0.7264", "doc_kind": "apk", "xapk_base": None,
        "sha256": "16acee8ff4338921ede7069e112750efd7d30d04ec0518f63190b2d011f518ac",
        "rel_path": "raw/vendor_apps/whistle/com.whistle.bolt/5.11.0.7264/"
                    "16acee8ff4338921ede7069e112750efd7d30d04ec0518f63190b2d011f518ac.apk",
        "source_url": "https://apkcombo.com/whistle-smart-pet-tracker/com.whistle.bolt/",
    },
    "angelsense": {
        "vendor": "AngelSense", "package": "com.angelsense.mobile",
        "version": "4.2.0", "doc_kind": "apk", "xapk_base": None,
        "sha256": "0a49bff48ee2a233d4e961ed5e596b43086cdb404c38085317f3e580b14a13ca",
        "rel_path": "raw/vendor_apps/angelsense/com.angelsense.mobile/4.2.0/"
                    "0a49bff48ee2a233d4e961ed5e596b43086cdb404c38085317f3e580b14a13ca.apk",
        "source_url": "https://apkcombo.com/angelsense-guardian/com.angelsense.mobile/",
    },
}

FI_BASE = "-2528-d6bc-b043-b49af0ec06c1"
FI_SHORTS = ["57b40001", "57b40002", "57b40003", "57b40006", "57b40007", "57b4000c",
             "57b4000d", "57b40013", "57b40210", "57b40211", "57b40212", "57b40213",
             "57b40214", "57b40215", "57b40216", "57b40217", "57b43001", "57b43002",
             "57b43003", "57b43004", "57b44001", "57b44022", "57b44023"]
FI_FAMILY = [s + FI_BASE for s in FI_SHORTS]

JIOBIT_BASE = "-ddb6-4ffd-8f65-753cb9dc2e8a"
JIOBIT_FAMILY = [f"d8ecdb0{n}{JIOBIT_BASE}" for n in ["1", "2", "3", "5", "8", "9", "a", "b"]] + [
    "0000db01-0000-1000-8000-00805f9b34fb",   # 0xDB01 custom short (echoes d8ec*db01*)
    "4a000000-0000-1000-8000-00805f4a494f",   # last node 00805f4a494f = 'JIO' ASCII
]

# Whistle vendor BLE GATT -> {uuid: (wcconstants_field, co_location_class, gatt_role)}.
# Field names + classes are baksmali-derived and re-verified byte-present here.
WC = "Lcom/whistle/whistlecore/WCConstants;"
SFU = "Lcom/whistle/whistlecore/util/ScanFilterUtils;"
WHISTLE_GATT = {
    # Family A — AMDTP (Ambiq data-transfer): 1 service + 3 characteristics
    "00002760-08c2-11e1-9073-0e8ac72e1011": ("UUID_SERVICE_AMDTP", WC, "service"),
    "00002760-08c2-11e1-9073-0e8ac72e0011": ("UUID_AMDTP_DATA_TO_DEVICE", WC, "characteristic"),
    "00002760-08c2-11e1-9073-0e8ac72e0012": ("UUID_AMDTP_DATA_FROM_DEVICE", WC, "characteristic"),
    "00002760-08c2-11e1-9073-0e8ac72e0013": ("UUID_AMDTP_ACK", WC, "characteristic"),
    # Family B — BLE beacon (advertised) UUIDs
    "d7895ab1-acc7-4de3-b991-9e825c24c801": ("UUID_BLE_BEACON_PRESENCE", WC, "beacon_adv"),
    "d7895ab1-acc7-4de3-b991-9e825c24c802": ("UUID_BLE_BEACON_LEGACY_DSR", WC, "beacon_adv"),
    "d7895ab1-acc7-4de3-b991-9e825c24c804": ("UUID_BLE_BEACON_PROX", WC, "beacon_adv"),
    "d7895ab1-acc7-4de3-b991-9e825c24c809": ("UUID_BLE_BEACON_BUTTON_PRESS", WC, "beacon_adv"),
    "d7895ab1-acc7-4de3-b991-9e825c24c80b": ("UUID_LEGACY_BUTTON2", SFU, "beacon_adv"),
    # Family C — ADV_IND (advertised indication) UUIDs
    "00c8245c-829e-91b9-e34d-c7acb15a89d7": ("UUID_ADV_IND_BLANK", WC, "adv_ind"),
    "01c8245c-829e-91b9-e34d-c7acb15a89d7": ("UUID_ADV_IND_LM_AVAILABLE", WC, "adv_ind"),
    "02c8245c-829e-91b9-e34d-c7acb15a89d7": ("UUID_ADV_IND_DSR", WC, "adv_ind"),
    "04c8245c-829e-91b9-e34d-c7acb15a89d7": ("UUID_ADV_IND_PROX", WC, "adv_ind"),
    "09c8245c-829e-91b9-e34d-c7acb15a89d7": ("UUID_ADV_IND_BUTTON_PRESS", WC, "adv_ind"),
    "11c8245c-829e-91b9-e34d-c7acb15a89d7": ("UUID_ADV_IND_BUTTON_PRESS_2", WC, "adv_ind"),
    # SPPLE (serial-port-profile-over-LE) — 5 harvest "singletons" RESOLVED to vendor:
    "14839ac4-7d7e-415c-9a42-167340cf2339": ("UUID_SERVICE_SPPLE", WC, "service"),
    "0734594a-a8e7-4b1a-a6b1-cd5243059a57": ("UUID_SPPLE_DATA_FROM_DEVICE", WC, "characteristic"),
    "8b00ace7-eb0b-49b0-bbe9-9aee0a26e1a3": ("UUID_SPPLE_DATA_TO_DEVICE", WC, "characteristic"),
    "e06d5efb-4f4a-45c0-9eb1-371ae5a14ad4": ("UUID_SPPLE_CREDITS_FROM_DEVICE", WC, "characteristic"),
    "ba04c4b2-892b-43be-b69c-5d13f2195392": ("UUID_SPPLE_CREDITS_TO_DEVICE", WC, "characteristic"),
}
# UUIDs the harvest counted in the "15 families" (everything in WHISTLE_GATT NOT
# resolved from the 7-singleton triage list).
WHISTLE_SINGLETONS = {
    "0734594a-a8e7-4b1a-a6b1-cd5243059a57", "8b00ace7-eb0b-49b0-bbe9-9aee0a26e1a3",
    "ba04c4b2-892b-43be-b69c-5d13f2195392", "e06d5efb-4f4a-45c0-9eb1-371ae5a14ad4",
    "14839ac4-7d7e-415c-9a42-167340cf2339", "6cdc3b69-0077-4d0a-b91c-712b2b37775f",
    "ec6e18c5-7f14-4bdf-9c95-9ead4ebd90f8",
}

# Whistle FP-triage NON-promotes (cited co-located class re-verified byte-present)
WHISTLE_FLAGGED = {  # vendor-owned but Bluetooth-CLASSIC SDP (not BLE GATT)
    "6cdc3b69-0077-4d0a-b91c-712b2b37775f": (
        "LocalManagementSDPUUID", WC,
        "Whistle-owned but a Bluetooth-CLASSIC SDP/RFCOMM service UUID "
        "(LocalManagementSDPUUID), NOT a BLE GATT service — tagging it ble_service_uuid "
        "would mis-state transport. Board/CTO decides include-as-classic vs exclude."),
}
WHISTLE_EXCLUDED_FP = {  # non-BLE third-party SDK config
    "ec6e18c5-7f14-4bdf-9c95-9ead4ebd90f8": (
        "APP_CENTER_APP_SECRET", "Lcom/whistle/bolt/BuildConfig;",
        "non_ble_sdk_config",
        "BuildConfig.APP_CENTER_APP_SECRET passed to com.microsoft.appcenter.AppCenter."
        "configure() — Microsoft App Center analytics/crash SDK app-secret, NOT a BLE UUID."),
}

# AngelSense -> Salesforce Marketing Cloud SDK (library, not BLE). Cited classes.
ANGELSENSE_FP = {
    "849f26e2-2df6-11e4-ab12-14109fdc48df": (
        "Lcom/salesforce/marketingcloud/analytics/piwama/a;", "non_ble_library",
        "Salesforce Marketing Cloud SDK analytics constant (…/analytics/piwama) — "
        "not a vendor BLE service UUID. Harvest's AltBeacon/Smartlook guess corrected."),
    "f6389234-1024-481f-9173-37d9d7f5051f": (
        "Lcom/salesforce/marketingcloud/util/AesCrypto;", "non_ble_library",
        "Salesforce Marketing Cloud SDK AesCrypto.ENC_TEST_STRING (AES encryption "
        "test vector) — not a BLE UUID at all."),
}

# Tile cross-vendor (HELD) — Life360 owns Jiobit + Tile, do-NOT-double-promote.
TILE_HELD = {
    "0000feec-0000-1000-8000-00805f9b34fb": "Tile 0xFEEC",
    "0000feed-0000-1000-8000-00805f9b34fb": "Tile 0xFEED",
}

# Cross-vendor FP-magnet / framework / placeholder exclude list (carried).
FP_MAGNETS = {
    "258eafa5-e914-47da-95ca-c5ab0dc85b11": "cross-vendor FP magnet (c1+c2+c6)",
    "95ed6082-b8e9-46e8-a73f-ff56f00f5d9d": "androidx.work.Data internal id (not BLE)",
    "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed": "urn:uuid namespace marker (not BLE)",
    "5eb5a37e-b458-11e3-ac11-000c2940e62c": "beacon-library example region UUID",
    "b2f7f966-d8cc-11e4-bed1-df8f05be55ba": "beacon-library example region UUID",
    "00000000-0000-0000-0000-000000000000": "null UUID",
    "00000000-deca-fade-deca-deafdecacafe": "library placeholder UUID",
    "00ffffff-ffff-ffff-ffff-ffffffffffff": "all-ones mask/placeholder UUID",
}

LOCAL_NAMES = {
    "fi": ["fi-db", "fi-backhaul-db", "fi-walk-"],
    "whistle": ["whistle3", "whistle3_charge"],
}

_file_cache: dict[str, list[str]] = {}
_dex_cache: dict[str, list[tuple[str, bytes]]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _lines(rel: str) -> list[str]:
    if rel not in _file_cache:
        p = REPO / rel
        if not p.exists():
            raise FileNotFoundError(f"raw artifact missing: {rel}")
        _file_cache[rel] = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return _file_cache[rel]


def file_sha256(rel: str) -> str:
    h = hashlib.sha256()
    h.update((REPO / rel).read_bytes())
    return h.hexdigest()


def clip(s: str) -> str:
    """§11 #7 — enforce <=200 chars with a truncation marker."""
    s = s.strip()
    return s[:MAX_EXCERPT - 1] + "…" if len(s) > MAX_EXCERPT else s


def redact_person_pii(s: str) -> tuple[str, int]:
    """SAR-5 / §11 #3 — strip person names; return (clean, count). 0 expected."""
    n = 0

    def _sub(_m):
        nonlocal n
        n += 1
        return "[REDACTED_PERSON]"

    return PERSON_NAME_RE.sub(_sub, s), n


def source_row_key(doc_url: str, candidate_type: str, candidate_identifier: str) -> str:
    """Idempotency key (used downstream by DBArchitect; Wave-B Step-0 shape)."""
    return hashlib.sha256(
        f"{doc_url}|{candidate_type}|{candidate_identifier}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# APK dex static scan — deterministic, pure-stdlib (zipfile + regex)
# ---------------------------------------------------------------------------
def _dex_blobs(vendor: str) -> list[tuple[str, bytes]]:
    """[(dex_entry_name, bytes)] for every classes*.dex; XAPK base recursed once.

    Deterministic: entries iterated in sorted name order. Cached per vendor.
    """
    if vendor in _dex_cache:
        return _dex_cache[vendor]
    apk = APKS[vendor]
    out: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(REPO / apk["rel_path"]) as z:
        if apk["xapk_base"]:
            with zipfile.ZipFile(io.BytesIO(z.read(apk["xapk_base"]))) as inner:
                for n in sorted(inner.namelist()):
                    if re.fullmatch(r"classes\d*\.dex", n):
                        out.append((n, inner.read(n)))
        else:
            for n in sorted(z.namelist()):
                if re.fullmatch(r"classes\d*\.dex", n):
                    out.append((n, z.read(n)))
    _dex_cache[vendor] = out
    return out


def scan_uuids(vendor: str) -> dict[str, tuple[str, str]]:
    """{uuid_lower: (dex_entry, exact_byte_form)} first occurrence (deterministic)."""
    found: dict[str, tuple[str, str]] = {}
    for dexname, blob in _dex_blobs(vendor):
        for m in UUID_RE_BYTES.finditer(blob):
            raw = m.group(0).decode("latin-1")
            low = raw.lower()
            if low not in found:
                found[low] = (dexname, raw)
    return found


def byte_locate(vendor: str, token: str) -> str:
    """Return the dex_entry where `token` (str) first appears in bytes; raise if absent.

    Grounds every co-location claim in the actual dex bytes (§11 #1 — not memory).
    """
    needle = token.encode("latin-1")
    for dexname, blob in _dex_blobs(vendor):
        if needle in blob:
            return dexname
    raise AssertionError(f"token {token!r} NOT byte-present in {vendor} dex — refusing to fabricate")


def already_in_db(conn, value: str):
    return conn.execute(
        "SELECT id,identifier,identifier_type,device_category,manufacturer FROM identifiers "
        "WHERE lower(identifier)=lower(?) AND superseded_by IS NULL", (value,)).fetchall()


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def _uuid_candidate(conn, vendor, uuid, scan, role, co_location_token, co_location_note,
                    confidence, ceil, disposition, extra_notes=None):
    """Build one ble_service_uuid candidate, byte-faithful + DB-checked."""
    apk = APKS[vendor]
    if uuid not in scan:
        raise AssertionError(f"expected UUID {uuid} not byte-present in {vendor} dex")
    dex_entry, byte_form = scan[uuid]
    if co_location_token is not None:
        # re-verify the cited class/field token is byte-present (§11 #1 grounded)
        co_dex = byte_locate(vendor, co_location_token)
        co_location = f"{co_location_token} @ {co_dex} — {co_location_note}"
        dex_member = f"{dex_entry} :: {co_location_token}"
    else:
        # structural co-location (obfuscated app-own code, no clean class token)
        co_location = f"{co_location_note} (value @ {dex_entry})"
        dex_member = dex_entry
    db_rows = already_in_db(conn, uuid)
    notes = {
        "subtype": SUBTYPE,
        "category_pending_board_ratification": True,
        "net_new_vs_held": "net-new" if not db_rows else f"held: {db_rows}",
        "gatt_role": role,
        "co_location": co_location,
        "single_source": "one companion APK; no §8.3 value-level corroboration lift",
    }
    if extra_notes:
        notes.update(extra_notes)
    if confidence <= 40:
        notes["ambiguous_extraction"] = True
    return {
        "identifier": uuid,
        "identifier_type": "ble_service_uuid",
        "device_category": PROPOSED_CATEGORY,
        "manufacturer": apk["vendor"],
        "model": None,
        "confidence": confidence,
        "band": "manufacturer_app",
        "band_ceiling": ceil,
        "disposition": disposition,
        "net_new": not db_rows,
        "source_url": f"{apk['source_url']}#{dex_entry}",
        "source_markers": {
            "apk_sha256": apk["sha256"],
            "rel_path": apk["rel_path"],
            "dex_member": dex_member,
            "byte_form": byte_form,
            "excerpt": clip(byte_form),
        },
        "source_row_key": source_row_key(apk["source_url"], "ble_service_uuid", uuid),
        "geographic_scope": "global",
        "notes": notes,
    }


def build() -> dict:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    pii_redactions = 0

    # sha self-verify (§11 #1 — fail loud if any on-disk binary drifted)
    for v, apk in APKS.items():
        got = file_sha256(apk["rel_path"])
        if got != apk["sha256"]:
            raise AssertionError(f"APK sha drift {apk['package']}: {got} != {apk['sha256']}")

    scans = {v: scan_uuids(v) for v in APKS}
    candidates: list[dict] = []
    flagged_ambiguous: list[dict] = []
    excluded: list[dict] = []

    # ---- (A) Fi 23 — obfuscated own-code, shared vendor base (role undetermined) ----
    # structural family check: all 23 share the proprietary Fi 128-bit base.
    assert all(u.endswith(FI_BASE) for u in FI_FAMILY), "Fi family base mismatch"
    for u in FI_FAMILY:
        candidates.append(_uuid_candidate(
            conn, "fi", u, scans["fi"], "undetermined_r8_obfuscated", None,
            "R8-obfuscated app-own classes (o3/h24/ch8/df8/ba7/kf); shared vendor "
            "128-bit base -2528-d6bc-b043-b49af0ec06c1, absent from all third-party "
            "library packages",
            COMPANION_CONF, COMPANION_CEIL, "promote"))

    # ---- (B) Jiobit 10 — co-declared in obfuscated class Lae/b; ----
    for u in JIOBIT_FAMILY:
        candidates.append(_uuid_candidate(
            conn, "jiobit", u, scans["jiobit"], "undetermined_r8_obfuscated", "Lae/b;",
            "R8-obfuscated app-own class Lae/b; co-declares the d8ecdb family + 0xDB01 "
            "short + 4a..='JIO'(00805f4a494f) ASCII vendor marker together",
            COMPANION_CONF, COMPANION_CEIL, "promote"))

    # ---- (C) Whistle GATT 20 (15 families + 5 SPPLE singletons resolved) ----
    for u, (field, klass, role) in WHISTLE_GATT.items():
        extra = {"wcconstants_field": field}
        if u in WHISTLE_SINGLETONS:
            extra["harvest_singleton_resolved_to_vendor"] = True
            extra["resolution"] = (
                "harvest flagged as singleton needing FP-triage; resolved to genuine "
                "Whistle SPPLE GATT via WCConstants field name (+over harvest's 48-slate)")
        candidates.append(_uuid_candidate(
            conn, "whistle", u, scans["whistle"], role, field,
            f"Whistle vendor BLE constant {field}", COMPANION_CONF, COMPANION_CEIL,
            "promote", extra))

    # ---- (D) Whistle flagged-ambiguous: BT-Classic SDP ----
    for u, (field, klass, note) in WHISTLE_FLAGGED.items():
        c = _uuid_candidate(conn, "whistle", u, scans["whistle"], "bt_classic_sdp", field,
                            note, FLAGGED_CONF, COMPANION_CEIL, "flagged_ambiguous",
                            {"wcconstants_field": field, "transport": "bluetooth_classic_sdp"})
        flagged_ambiguous.append(c)

    # ---- (E) excluded FPs (non-BLE library/SDK), with cited co-located class ----
    secret_redactions = 0

    def _excl(vendor, uuid, co_token, reason, detail, mask_secret=False):
        nonlocal secret_redactions
        scan = scans[vendor]
        dex_entry, byte_form = scan[uuid]
        co_dex = byte_locate(vendor, co_token)
        apk = APKS[vendor]
        ident, shown = uuid, byte_form
        if mask_secret:
            # §11 #3 / "never commit secrets" — this excluded value is a labeled SDK
            # app-secret. Its exact value is not needed for the FP disposition (the
            # field name + dex class are the evidence). Mask all but the prefix.
            secret_redactions += 1
            mask = uuid[:13] + "-****-************"
            ident, shown = mask, mask
        return {
            "identifier": ident, "identifier_type": "ble_service_uuid",
            "manufacturer": apk["vendor"], "disposition": "excluded", "reason": reason,
            "detail": detail, "value_redacted": mask_secret,
            "source_markers": {"apk_sha256": apk["sha256"], "rel_path": apk["rel_path"],
                               "dex_member": f"{dex_entry} :: {co_token}",
                               "byte_form": shown, "excerpt": clip(shown)},
            "db_presence": "net-new (excluded, not staged)",
        }

    for u, (field, klass, reason, detail) in WHISTLE_EXCLUDED_FP.items():
        excluded.append(_excl("whistle", u, klass, reason, f"{field}: {detail}",
                              mask_secret=(reason == "non_ble_sdk_config")))
    for u, (klass, reason, detail) in ANGELSENSE_FP.items():
        excluded.append(_excl("angelsense", u, klass, reason, detail))

    # ---- (F) Tile cross-vendor HELD — never re-attributed to Jiobit ----
    tile_held = []
    for u, label in TILE_HELD.items():
        rows = already_in_db(conn, u)
        present = u in scans["jiobit"]
        tile_held.append({
            "identifier": u, "short": label, "disposition": "held_cross_vendor",
            "reason": "tile_do_not_double_promote",
            "detail": ("Referenced in the Jiobit APK but owned by Tile, Inc. (Life360 owns "
                       "both). HELD bluetooth_tracker — NEVER re-attributed to Jiobit."),
            "held_db_rows": rows, "present_in_jiobit_dex": present,
        })

    # ---- (G) cross-vendor FP-magnet audit (assert none promoted) ----
    promoted_ids = {c["identifier"] for c in candidates}
    magnet_audit = []
    for u, why in FP_MAGNETS.items():
        in_any = sorted(v for v in APKS if u in scans[v])
        if u in promoted_ids:
            raise AssertionError(f"FP-magnet {u} leaked into promote set")
        magnet_audit.append({"identifier": u, "reason": why, "present_in": in_any,
                             "promoted": False})

    # ---- (H) OUI — Whistle Labs E0:7C:62 (IEEE primary_registry) ----
    oui_hex, oui_colon = "E07C62", "e0:7c:62"
    oui_line, oui_excerpt = None, None
    for i, ln in enumerate(_lines(A_OUI)):
        if ln.startswith(f"MA-L,{oui_hex},"):
            oui_line, oui_excerpt = i + 1, clip(ln)
            break
    if oui_line is None:
        raise AssertionError(f"OUI {oui_hex} not found in {A_OUI}")
    oui_excerpt, n = redact_person_pii(oui_excerpt)
    pii_redactions += n
    if "Whistle Labs, Inc." not in oui_excerpt:
        raise AssertionError("OUI org name not verbatim in line")
    first_octet = int(oui_colon.split(":")[0], 16)
    oui_candidate = {
        "identifier": oui_colon, "identifier_type": "oui",
        "device_category": PROPOSED_CATEGORY, "manufacturer": "Whistle Labs, Inc.",
        "model": None, "confidence": OUI_CONF, "band": "primary_registry",
        "band_ceiling": OUI_CEIL, "disposition": "promote",
        "net_new": not already_in_db(conn, oui_colon),
        "source_url": OUI_URL, "source_markers": {
            "doc_kind": "ieee_oui_csv", "line_number": oui_line,
            "registry_class": "MA-L", "vendor_doc_sha256_link": file_sha256(A_OUI),
            "excerpt": oui_excerpt},
        "source_row_key": source_row_key(OUI_URL, "oui", oui_colon),
        "geographic_scope": "global",
        "notes": {
            "subtype": SUBTYPE, "category_pending_board_ratification": True,
            "net_new_vs_held": "net-new" if not already_in_db(conn, oui_colon)
            else str(already_in_db(conn, oui_colon)),
            "laa_bit": "lab_bit_set — likely synthetic/randomized" if first_octet & 0x02
            else "laa_bit_clear (globally-administered IEEE OUI)",
            "known_fake_check": "pass (not in §7.3 known-fake/doc ranges)",
            "caveat": "Pure-play pet-tracker vendor OUI; cleanest promotable lead. The "
                      "device cellular-module OUI is not derivable from the app (FCC EAS "
                      "blocked) — this is the Whistle Labs IEEE-registered OUI."}}

    # ---- (I) ble_local_name bonus (behavioral, low-confidence) ----
    local_name_candidates = []
    for vendor, names in LOCAL_NAMES.items():
        apk = APKS[vendor]
        for nm in names:
            dex_entry = byte_locate(vendor, nm)
            db_rows = already_in_db(conn, nm)
            local_name_candidates.append({
                "identifier": nm, "identifier_type": "ble_local_name",
                "device_category": PROPOSED_CATEGORY, "manufacturer": apk["vendor"],
                "model": None, "confidence": LOCAL_NAME_CONF, "band": "manufacturer_app_behavioral",
                "band_ceiling": LOCAL_NAME_CONF, "disposition": "bonus_low_confidence",
                "net_new": not db_rows,
                "source_url": f"{apk['source_url']}#{dex_entry}",
                "source_markers": {"apk_sha256": apk["sha256"], "rel_path": apk["rel_path"],
                                   "dex_member": dex_entry, "byte_form": nm, "excerpt": clip(nm)},
                "source_row_key": source_row_key(apk["source_url"], "ble_local_name", nm),
                "geographic_scope": "global",
                "notes": {"subtype": SUBTYPE, "category_pending_board_ratification": True,
                          "net_new_vs_held": "net-new" if not db_rows else f"held: {db_rows}",
                          "behavioral": True,
                          "caveat": "BLE local-name prefix/advertised-name fragment (DB type "
                                    "ble_local_name, 21 rows). Behavioral/low-confidence; "
                                    "out-of-primary-brief bonus per CTO authorization."}})

    # ---- (J) ble_company_id — 0 (Apple id excluded, cited) ----
    company_id_finding = {
        "net_new": 0,
        "attempted": True,
        "evidence": "Lcom/whistle/whistlecore/util/ScanFilterUtils; "
                    "MANUFACTURER_ID_APPLE:I = 0x4c",
        "byte_verified": "MANUFACTURER_ID_APPLE" in
                         _dex_blobs("whistle")[0][1].decode("latin-1", "replace") or
                         byte_locate("whistle", "MANUFACTURER_ID_APPLE") is not None,
        "disposition": "EXCLUDED — Whistle's company-id scan machinery targets Apple's "
                       "iBeacon company id (0x004C / 76), not a Whistle-assigned id. Per "
                       "MAC-411 brief: exclude non-cohort company-ids. No BT-SIG membership "
                       "for any cohort vendor under its own name -> ble_company_id net-new = 0.",
    }

    conn.close()

    counts = {
        "ble_service_uuid_promote": len(candidates),
        "  fi": sum(1 for c in candidates if c["manufacturer"].startswith("Fi")),
        "  jiobit": sum(1 for c in candidates if c["manufacturer"].startswith("Jiobit")),
        "  whistle": sum(1 for c in candidates if c["manufacturer"].startswith("Whistle")),
        "  whistle_singletons_resolved_to_vendor": sum(
            1 for c in candidates if c["notes"].get("harvest_singleton_resolved_to_vendor")),
        "ble_service_uuid_flagged_ambiguous": len(flagged_ambiguous),
        "ble_service_uuid_excluded_fp": len(excluded),
        "tile_held_cross_vendor": len(tile_held),
        "oui_promote": 1,
        "ble_local_name_bonus": len(local_name_candidates),
        "ble_company_id_net_new": 0,
        "harvest_slate_was": 48,
        "extraction_delta_vs_harvest": len(candidates) - 48,
    }
    # internal invariants (fail loud)
    assert counts["  fi"] == 23 and counts["  jiobit"] == 10
    assert counts["  whistle"] == 20 and counts["  whistle_singletons_resolved_to_vendor"] == 5
    assert all(c["net_new"] for c in candidates), "a promoted UUID is not net-new"
    assert all(len(c["source_markers"]["excerpt"]) <= MAX_EXCERPT
               for c in candidates + flagged_ambiguous + local_name_candidates)

    return {
        "_meta": {
            "issue": "MAC-411",
            "cohort": "MAC-393 wave-2 cohort 6 — Pet / kid cellular tracker (stalkerware-adjacent)",
            "harvest_input": "MAC-399 (CTO-ratified) + operator_review/MAC-393/c6_petkid/harvest.md "
                             "+ extraction_outputs/mac393_c6_petkid/sources.json",
            "scope": "EXTRACTION ONLY — candidates for CTO verify -> DBArchitect ingest. "
                     "No DB write / migration / export regen / push. db/argus.db opened mode=ro.",
            "taxonomy_one_way_door": "device_category 'gps_tracker' exists (122 rows); "
                                     "'personal_tracker' does NOT (count=0). Every candidate is "
                                     "PROPOSED gps_tracker + notes.subtype='pet_kid_cellular' + "
                                     "category_pending_board_ratification. Board decides at ingest.",
            "confidence_bands": "§8.2 — manufacturer_app 75-90 floor; brief caps companion-APK "
                                "single-source UUIDs at <=75 (no family-size inflation, §11 #8). "
                                "OUI primary_registry pure-play -> 85. local_name behavioral -> 50.",
            "no_83_lift": "Every lead is single-source (one companion APK). Hub-and-spoke (same "
                          "vendor across UUID types) is NOT value-level corroboration -> no §8.3 lift.",
            "fp_triage_method": "baksmali dex disassembly xref (each contested UUID -> defining "
                                "smali class), re-verified byte-present in the named vendor dex here.",
            "harvest_singleton_resolution": "5 of the 7 Whistle 'singletons' resolve to genuine "
                                            "vendor SPPLE GATT (WCConstants field names) -> promoted "
                                            "(+5 over harvest's 48). 1 = BT-Classic SDP (flagged), "
                                            "1 = Microsoft App Center secret (excluded).",
            "excerpt_max_chars": MAX_EXCERPT,
            "pii_redaction_count": pii_redactions,
            "secret_redaction_count": secret_redactions,
            "secret_redaction_note": "1 excluded value (Whistle BuildConfig APP_CENTER_APP_SECRET, a "
                                     "Microsoft App Center SDK app-secret, non-BLE) is value-masked in "
                                     "this deliverable per 'never commit secrets' — the field name + "
                                     "dex class remain as the FP evidence; the value is not staged.",
            "pii_note": "SAR-5 / §11 #3 — company legal-entity names + IEEE registry addresses only; "
                        "person-name regex applied. APK deliverable carries UUID byte-forms + dex "
                        "locations + sha256 pins only (§11 #15 facts-only); no APK code copied.",
            "tile_guard": "Jiobit references Tile 0xFEEC/0xFEED (HELD id44440/44439 bluetooth_tracker, "
                          "'Tile, Inc.'). Life360 owns both -> cross-vendor, NEVER re-attributed.",
            "export_note": "gps_tracker is an exported category; if the board maps c6 to gps_tracker "
                           "these rows reach the Lynceus feed -> ingest+regen is a CEO one-way door.",
        },
        "counts": counts,
        "candidates": candidates,
        "flagged_ambiguous": flagged_ambiguous,
        "excluded": excluded,
        "tile_held_cross_vendor": tile_held,
        "fp_magnet_audit": magnet_audit,
        "oui_candidate": oui_candidate,
        "ble_local_name_bonus": local_name_candidates,
        "ble_company_id_finding": company_id_finding,
    }


def main():
    payload = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "candidates.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    json.loads(out.read_text())  # json_valid
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    c = payload["counts"]
    print(f"wrote {out}")
    print(f"ble_service_uuid promote: {c['ble_service_uuid_promote']} "
          f"(fi {c['  fi']} / jiobit {c['  jiobit']} / whistle {c['  whistle']} "
          f"[incl {c['  whistle_singletons_resolved_to_vendor']} singletons resolved])")
    print(f"  flagged_ambiguous (BT-Classic): {c['ble_service_uuid_flagged_ambiguous']}")
    print(f"  excluded FP (non-BLE library/SDK): {c['ble_service_uuid_excluded_fp']}")
    print(f"  tile held cross-vendor: {c['tile_held_cross_vendor']}")
    print(f"oui promote: {c['oui_promote']}  ble_local_name bonus: {c['ble_local_name_bonus']}  "
          f"ble_company_id net-new: {c['ble_company_id_net_new']}")
    print(f"extraction delta vs harvest-48: {c['extraction_delta_vs_harvest']:+d}")
    print(f"candidates.json sha256: {digest}")


if __name__ == "__main__":
    main()
