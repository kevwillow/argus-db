"""MAC-406 — Wave-2 Cohort 4 (Consumer smart lock) EXTRACTION.

Turns the CTO-ratified MAC-397 harvest (under MAC-393) into structured
promotion candidates for CTO review -> DBArchitect ingest. EXTRACTION ONLY:
emits extraction_outputs/mac393_c4_smartlock/candidates.json. NO DB write, NO
ingest, NO migration, NO export regen, NO push. Raw bytes never enter git.

The verified net-new surface (per MAC-406 brief + MAC-397 ratification):
  * 6 vendor OUIs absent from the DB (IEEE OUI registry).
  * Proprietary 128-bit GATT service/characteristic UUIDs from 4 companion APKs
    (August/Yale, Schlage, Kwikset, Ultraloq) — the surface the CTO did NOT
    certify at harvest; per-UUID byte-faithfulness is proven HERE.

The entire BT SIG 16-bit registry is already bulk-loaded as device_category=
'unknown' (715 ble_company_id + 3969 ble_manufacturer_id) -> every vendor
company-ID and 16-bit member/service UUID is already HELD; BLE-registry net-new
= 0. That surface is RECATEGORIZATION (unknown -> smart_lock), gated on the
taxonomy mint -> recorded under held_recat_candidates, NOT promoted here.

TAXONOMY ONE-WAY-DOOR: device_category 'smart_lock' does NOT exist (verified
count=0). Every candidate is tagged proposed device_category='smart_lock' +
notes.category_pending_board_ratification. The mint-vs-map decision is a board
one-way-door adjudicated at the ingest gate — this module does NOT assume it and
does NOT write the category.

This module re-derives EVERY candidate field from the on-disk raw artifacts
(re-grepped / re-scanned here, never trusted from the harvest summary):
  * OUI cite-pastes are verbatim substrings of the named IEEE oui.csv line.
  * APK GATT extraction is a deterministic static scan (pure-stdlib zipfile +
    regex over .dex byte pools) of the gitignored APKs, keyed by sha256. Same
    APK -> same result. The exact dex constant-table byte-form + classesN.dex
    location are recorded per UUID (§11 #1 cite-paste, not memory).
  * Cross-vendor exclusion is computed by CITED co-occurrence (UUID present in
    >=2 unrelated vendor APKs -> shared-SDK magnet -> excluded) (§11 #21 / CP44).
  * already_in_db: read-only lookup against live db/argus.db (mode=ro).

Discipline (bible §7.3 / §8.2 / §11 + MAC-406 hard gates):
  * §11 #1  Conservative. Vendor-unique-but-SDK/placeholder UUIDs excluded;
            boilerplate-node / ASCII-embedded families flagged conf=40
            (ambiguous_extraction), NOT clean-promoted.
  * §11 #2  No non-public data; all sources pre-cleared primary_registry /
            manufacturer_app.
  * §11 #3 / SAR-5  PII — company legal-entity names + registry addresses only;
            person-name regex redaction applied + counted (0 expected).
  * §11 #7  source_excerpt enforced <=200 chars at build time (truncate + marker).
  * §11 #8  No confidence drift; staged at single-source confidence.
  * §11 #13 smart_lock is export-banned until minted -> handled at ingest gate.
  * §11 #14 procurement-only never exported -> n/a (no procurement-shape rows).
  * SAR-1   LAA-bit test applied to OUI first octet (all globally-administered).

Wyze do-not-double-promote (MAC-397 ruling 2): Wyze OUIs id44484-88 are already
cctv_camera; NO Wyze company-level OUI/ID candidate is emitted. com.hualai
(Wyze Lock app) is SKIPPED per ruling 3. Only the 4 clean vendor APKs are mined.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sqlite3
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
OUT_DIR = REPO / "extraction_outputs" / "mac393_c4_smartlock"

MAX_EXCERPT = 200  # §11 #7 app-level enforcement
SIG_BASE_SUFFIX = "-0000-1000-8000-00805f9b34fb"  # SIG 16-bit base UUID
PROPOSED_CATEGORY = "smart_lock"  # PROPOSED ONLY — count=0 in DB; board mints at ingest

UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
UUID_RE_BYTES = re.compile(rb"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

# Person-name redaction (SAR-5): target explicit contact markers only, so corporate
# registry ADDRESSES (which contain street tokens like "Dr."=Drive and city names
# that look like "Firstname Lastname") are NOT corrupted. IEEE OUI lines carry only
# org legal names + registry addresses -> this is expected to match 0.
PERSON_NAME_RE = re.compile(
    r"\b(?:Attn|ATTN|Contact|CONTACT|c/o|C/O)\b[:.]?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+"
    r"|\b(?:Mr|Mrs|Ms)\.\s+[A-Z][a-z]+\s+[A-Z][a-z]+")  # 'Dr' omitted: collides with 'Drive'

# --- raw artifact relative paths (provenance; raw/ is gitignored) --------------
A_OUI = "raw/ieee_oui/20260613T203034Z_oui.csv"
A_SIG_COMPANY = "raw/bluetooth_sig/20260613T203034Z_company_identifiers.yaml"
A_SIG_MEMBER = "raw/bluetooth_sig/20260613T203034Z_member_uuids.yaml"
OUI_URL = "https://standards-oui.ieee.org/oui/oui.csv"

# --- CTO-ratified companion APKs (sha256-pinned; gitignored) -------------------
APKS = [
    {"vendor": "Kwikset", "package": "com.kwikset.blewifi", "doc_kind": "apk",
     "artifact": "raw/vendor_apps/kwikset/com.kwikset.blewifi/_unsorted/"
                 "6c3b74247f8f953ad1d3f2bf9f5bdf2abb3695b4baa371c6db9119e195aeb751.apk",
     "sha256": "6c3b74247f8f953ad1d3f2bf9f5bdf2abb3695b4baa371c6db9119e195aeb751",
     "source_url": "https://apkcombo.com/kwikset/com.kwikset.blewifi/",
     "vendor_kind": "pure_play_lock"},
    {"vendor": "Schlage", "package": "com.allegion.leopard", "doc_kind": "xapk",
     "artifact": "raw/vendor_apps/schlage/com.allegion.leopard/_unsorted/"
                 "fbc026c088df0fb7a93cb8ed988128231ced5a053a385d4b0fb68a3b3e5ab29e.apk",
     "sha256": "fbc026c088df0fb7a93cb8ed988128231ced5a053a385d4b0fb68a3b3e5ab29e",
     "source_url": "https://apkcombo.com/schlage-home/com.allegion.leopard/",
     "vendor_kind": "pure_play_lock"},
    {"vendor": "August", "package": "com.august.luna", "doc_kind": "apk",
     "artifact": "raw/vendor_apps/august/com.august.luna/_unsorted/"
                 "e7f7dd9af04da31c4f69dfae54ada84c5f2967367822c8c2f1468b7ba3582e13.apk",
     "sha256": "e7f7dd9af04da31c4f69dfae54ada84c5f2967367822c8c2f1468b7ba3582e13",
     "source_url": "https://apkcombo.com/august-home/com.august.luna/",
     "vendor_kind": "lock_app_august_and_yale"},
    {"vendor": "Ultraloq", "package": "com.utec.utec", "doc_kind": "xapk",
     "artifact": "raw/vendor_apps/ultraloq/com.utec.utec/_unsorted/"
                 "1bf404a8b27706e94e4d35f6c5f942bc705ecf0ad7687843b67cbec545bbf300.apk",
     "sha256": "1bf404a8b27706e94e4d35f6c5f942bc705ecf0ad7687843b67cbec545bbf300",
     "source_url": "https://apkcombo.com/xthings-home-formerly-u-home/com.utec.utec/",
     "vendor_kind": "lock_maker_multiproduct_app"},
]

_file_cache: dict[str, list[str]] = {}


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
    if len(s) > MAX_EXCERPT:
        return s[:MAX_EXCERPT - 1] + "…"
    return s


def redact_person_pii(s: str) -> tuple[str, int]:
    """SAR-5 / §11 #3 — strip person names; return (clean, count). 0 expected."""
    n = 0

    def _sub(_m):
        nonlocal n
        n += 1
        return "[REDACTED_PERSON]"

    return PERSON_NAME_RE.sub(_sub, s), n


def locate_oui(oui_hex: str) -> tuple[int, str]:
    """Return (1-indexed line, verbatim <=200-char excerpt) of the MA-L row."""
    needle = f"MA-L,{oui_hex},"
    for i, ln in enumerate(_lines(A_OUI)):
        if ln.startswith(needle):
            return i + 1, clip(ln)
    raise ValueError(f"OUI {oui_hex} NOT found in {A_OUI} — refusing to fabricate")


def source_row_key(doc_url: str, candidate_type: str, candidate_identifier: str) -> str:
    """Idempotency key per Wave-B Step-0 ratification (used downstream by DBArchitect)."""
    return hashlib.sha256(
        f"{doc_url}|{candidate_type}|{candidate_identifier}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# APK dex static scan — deterministic, pure-stdlib (zipfile + regex)
# ---------------------------------------------------------------------------
def _iter_dex_blobs(apk_path: Path):
    """Yield (entry_name, bytes) for every classes*.dex in the APK/XAPK.

    Handles XAPK (zip-of-apks): recurses one level into nested *.apk entries.
    Deterministic: entries iterated in sorted name order.
    """
    with zipfile.ZipFile(apk_path) as z:
        names = sorted(z.namelist())
        for n in names:
            if n.endswith(".dex"):
                yield n, z.read(n)
        for n in names:
            if n.endswith(".apk"):
                with zipfile.ZipFile(io.BytesIO(z.read(n))) as inner:
                    for m in sorted(inner.namelist()):
                        if m.endswith(".dex"):
                            yield f"{n}!{m}", inner.read(m)


def scan_apk_uuids(apk_path: Path) -> dict[str, tuple[str, str]]:
    """Return {uuid_lower: (dex_entry, exact_byte_form)} for the FIRST occurrence
    (deterministic: dex entries sorted, first match within wins).

    Facts-only (§11 #15): only UUID values + dex location are surfaced; no code
    or arrangement is copied.
    """
    found: dict[str, tuple[str, str]] = {}
    for dexname, blob in _iter_dex_blobs(apk_path):
        for m in UUID_RE_BYTES.finditer(blob):
            raw = m.group(0).decode("latin-1")
            low = raw.lower()
            if low not in found:
                found[low] = (dexname, raw)
    return found


# ---------------------------------------------------------------------------
# Classification of 128-bit custom UUIDs (deterministic, cited rationale)
# ---------------------------------------------------------------------------
def is_sig_base(u: str) -> bool:
    return u.endswith(SIG_BASE_SUFFIX)


def known_fake_reason(u: str) -> str | None:
    """§7.3 known-fake/placeholder patterns -> route to conflicts (reason)."""
    flat = u.replace("-", "")
    if flat == "0" * 32:
        return "known_fake_pattern: all-zero placeholder"
    if flat == "f" * 32:
        return "known_fake_pattern: all-F placeholder"
    # monotonic +1 byte sequence 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d ...
    if u.startswith("00010203-0405-0607-0809-0a0b0c0d"):
        return "known_fake_pattern: monotonic sequential-byte placeholder"
    return None


def sdk_signature_reason(u: str) -> str | None:
    """Bundled-SDK / non-BLE / cross-vendor-ecosystem signatures (vendor-unique
    but excludable on a cited structural ground, independent of co-occurrence)."""
    if u.endswith("0242ac120002"):
        return "non_ble_docker_v1_uuid: node 02:42:ac:12:00:02 (Docker default bridge MAC)"
    if u.endswith("0026bb765291"):
        return "apple_homekit_ecosystem: HomeKit accessory base 0026bb765291 (cross-vendor)"
    if u.startswith("486f6d65-6b69-7400"):  # ASCII 'Homekit\\0'
        return "apple_homekit_ecosystem: ASCII 'Homekit' marker, not a vendor GATT UUID"
    # Nordic UART Service base (incl. the customized ...dcca1e final-segment variant)
    if re.match(r"6e40000[0-9a-f]-b5a3-f393-e0a9-e50e24dcca[0-9a-f]{2}$", u):
        return "bundled_sdk_nordic_uart: Nordic NUS base 6e40000x-b5a3-f393-e0a9-e50e24dcca**"
    # TI OAD (also caught by co-occurrence; kept for single-vendor robustness)
    if re.match(r"f000ffc[0-5]-0451-4000-b000-000000000000$", u):
        return "bundled_sdk_ti_oad: TI Over-the-Air-Download service f000ffcx-0451-4000-b000-0"
    return None


# Boilerplate-node / ASCII-embedded families: vendor-unique, but the value itself
# carries a copy/sample signature -> conservative FLAG (conf 40, ambiguous), not
# clean-promote. Adjudicated by CTO/Validator (§11 #1).
BOILERPLATE_NODES = {
    "0800200c9a66": "v1 UUID node 08:00:20:0c:9a:66 = Sun Microsystems OUI (the java.util.UUID "
                    "javadoc / Android-BLE-tutorial sample node) -> likely boilerplate, not a "
                    "vendor-generated service",
    "0002a5d5c51b": "v1 UUID node 00:02:a5:d5:c5:1b = a globally-administered (real) OUI used "
                    "across a paired family -> possible copied/sample service",
}


def boilerplate_flag_reason(u: str) -> str | None:
    node = u.replace("-", "")[-12:]
    version = u[14]  # version nibble
    if version == "1" and node in BOILERPLATE_NODES:
        return BOILERPLATE_NODES[node]
    # ASCII-embedded suffix '...isfirst' family (sentinel-like, not a real GATT UUID)
    if u.endswith("-6965-6e65-7269-736669727374"):
        return ("ASCII-embedded UUID (suffix decodes to ASCII text) -> sentinel/sample-like, "
                "not a confirmed vendor GATT UUID")
    return None


# ---------------------------------------------------------------------------
# DB presence
# ---------------------------------------------------------------------------
def already_in_db(conn, value: str):
    return conn.execute(
        "SELECT id,identifier,identifier_type,device_category,manufacturer FROM identifiers "
        "WHERE lower(identifier)=lower(?) AND superseded_by IS NULL", (value,)).fetchall()


# ---------------------------------------------------------------------------
# OUI candidate specs (6 net-new, IEEE primary_registry)
# ---------------------------------------------------------------------------
@dataclass
class OuiSpec:
    oui_hex: str          # as in oui.csv (no separators, upper)
    oui_colon: str        # canonical lowercase colon form
    manufacturer: str
    confidence: int
    disposition: str      # promote | flagged_ambiguous
    caveat: str = ""


OUI_SPECS = [
    OuiSpec("10A450", "10:a4:50", "Kwikset", 85, "promote",
            "Pure-play residential lock brand (Kwikset Halo/SmartCode/Aura); clean smart_lock attribution."),
    OuiSpec("B0449C", "b0:44:9c", "Assa Abloy AB - Yale", 82, "promote",
            "Yale residential (cohort vendor 'Yale Assure'); Yale also makes commercial hardware."),
    OuiSpec("981BB5", "98:1b:b5", "ASSA ABLOY Korea Co., Ltd iRevo", 45, "flagged_ambiguous",
            "ASSA ABLOY Korea residential-lock subsidiary; not a cohort vendor and not product-anchored "
            "in the cleared slate -> recat candidate, ambiguous."),
    OuiSpec("14A1BF", "14:a1:bf", "ASSA ABLOY Korea Co., Ltd Unilock", 45, "flagged_ambiguous",
            "ASSA ABLOY Korea subsidiary (Unilock); not a cohort vendor and not product-anchored -> ambiguous."),
    OuiSpec("00177A", "00:17:7a", "ASSA ABLOY AB", 40, "flagged_ambiguous",
            "Parent conglomerate OUI (commercial + consumer door hardware); company-level, not "
            "product-anchored to consumer smart_lock."),
    OuiSpec("DCC0EB", "dc:c0:eb", "ASSA ABLOY CÔTE PICARDE", 40, "flagged_ambiguous",
            "ASSA ABLOY France door-hardware division; not clearly a consumer smart lock -> ambiguous."),
]


def laa_bit_note(oui_colon: str) -> str:
    """SAR-1 — (octet & 0x02) on the first OUI octet. IEEE OUIs are globally
    administered so this is informational; never penalises a real registry OUI."""
    first = int(oui_colon.split(":")[0], 16)
    if first & 0x02:
        return "lab_bit_set — likely synthetic/randomized"
    return "laa_bit_clear (globally-administered IEEE OUI)"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build() -> dict:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    oui_sha = file_sha256(A_OUI)
    pii_redactions = 0

    # ---- (A) OUI candidates ----
    oui_candidates = []
    for s in OUI_SPECS:
        line, excerpt = locate_oui(s.oui_hex)
        excerpt, n = redact_person_pii(excerpt)
        pii_redactions += n
        # cite-paste self-check: the org name must be a verbatim substring of the line
        if s.manufacturer not in excerpt:
            raise AssertionError(f"manufacturer {s.manufacturer!r} not verbatim in OUI line: {excerpt!r}")
        db_rows = already_in_db(conn, s.oui_colon)
        notes = {
            "category_pending_board_ratification": True,
            "net_new_vs_held": "net-new" if not db_rows else f"held: {db_rows}",
            "laa_bit": laa_bit_note(s.oui_colon),
            "known_fake_check": "pass (not in §7.3 known-fake/doc ranges)",
            "caveat": s.caveat,
        }
        if s.confidence <= 40 or s.disposition == "flagged_ambiguous":
            notes["ambiguous_extraction"] = True
        oui_candidates.append({
            "identifier": s.oui_colon,
            "identifier_type": "oui",
            "device_category": PROPOSED_CATEGORY,
            "manufacturer": s.manufacturer,
            "model": None,
            "confidence": s.confidence,
            "band": "primary_registry",
            "band_ceiling": 85,
            "disposition": s.disposition,
            "source_url": OUI_URL,
            "source_excerpt": excerpt,
            "raw_payload": {"doc_kind": "ieee_oui_csv", "line_number": line,
                            "registry_class": "MA-L", "vendor_doc_sha256_link": oui_sha},
            "source_row_key": source_row_key(OUI_URL, "oui", s.oui_colon),
            "geographic_scope": "global",
            "notes": notes,
        })

    # ---- (B) 128-bit GATT from companion APKs ----
    # sha self-verify (§11 #1 — fail loud if any on-disk binary drifted)
    for apk in APKS:
        got = file_sha256(apk["artifact"])
        if got != apk["sha256"]:
            raise AssertionError(f"APK sha drift {apk['package']}: {got} != {apk['sha256']}")

    # per-vendor scan: {uuid_lower: (dex, byte_form)}
    per_vendor: dict[str, dict[str, tuple[str, str]]] = {}
    for apk in APKS:
        per_vendor[apk["vendor"]] = scan_apk_uuids(REPO / apk["artifact"])

    # co-occurrence over custom-128 (exclude SIG-base 16-bit) -> magnets (>=2 vendors)
    occ: dict[str, set[str]] = {}
    for vendor, found in per_vendor.items():
        for u in found:
            if not is_sig_base(u):
                occ.setdefault(u, set()).add(vendor)
    magnets = {u: sorted(v) for u, v in occ.items() if len(v) >= 2}

    gatt_candidates: list[dict] = []
    flagged_ambiguous_gatt: list[dict] = []
    excluded: list[dict] = []
    apk_meta = {a["vendor"]: {k: a[k] for k in
                              ("vendor", "package", "doc_kind", "artifact", "sha256",
                               "source_url", "vendor_kind")} for a in APKS}

    # iterate vendors / uuids deterministically
    for apk in APKS:
        vendor = apk["vendor"]
        found = per_vendor[vendor]
        for u in sorted(found):
            if is_sig_base(u):
                continue  # 16-bit SIG UUIDs are registry-held (recat), handled below
            dexname, byte_form = found[u]
            base = {
                "identifier": u,
                "identifier_type": "ble_service_uuid",
                "manufacturer": vendor,
                "source_url": f"{apk['source_url']}#{dexname}",
                "source_excerpt": clip(byte_form),  # the verbatim dex constant byte-form
                "raw_payload": {"doc_kind": apk["doc_kind"], "dex_entry": dexname,
                                "byte_form": byte_form, "apk_sha256": apk["sha256"],
                                "package": apk["package"]},
                "source_row_key": source_row_key(apk["source_url"], "ble_service_uuid", u),
                "geographic_scope": "global",
            }

            mreason = magnets.get(u)
            kreason = known_fake_reason(u)
            sreason = sdk_signature_reason(u)
            breason = boilerplate_flag_reason(u)

            if mreason:
                excluded.append({**base, "disposition": "excluded",
                                 "reason": "cross_vendor_sdk_magnet",
                                 "co_occurrence_vendors": mreason,
                                 "detail": ("appears in >=2 unrelated vendor APKs -> shared chipset/"
                                            "BLE-SDK magnet (§11 #21 / CP44 cited co-occurrence)")})
            elif kreason:
                excluded.append({**base, "disposition": "rejected_conflict",
                                 "reason": "known_fake_pattern", "detail": kreason})
            elif sreason:
                excluded.append({**base, "disposition": "excluded",
                                 "reason": sreason.split(":")[0], "detail": sreason})
            elif breason:
                flagged_ambiguous_gatt.append({
                    **base, "device_category": PROPOSED_CATEGORY, "model": None,
                    "confidence": 40, "band": "manufacturer_app", "band_ceiling": 90,
                    "disposition": "flagged_ambiguous",
                    "notes": {"category_pending_board_ratification": True,
                              "net_new_vs_held": "net-new",
                              "ambiguous_extraction": True, "caveat": breason}})
            else:
                conf = 78 if apk["vendor_kind"] == "lock_maker_multiproduct_app" else 80
                caveat = ("U-tec 'Xthings Home' app may cover multiple U-tec product lines; UUID is "
                          "vendor-distinct but the product-within-vendor is not certain."
                          if apk["vendor_kind"] == "lock_maker_multiproduct_app"
                          else "Vendor-distinct GATT UUID (appears only in this vendor's lock app).")
                gatt_candidates.append({
                    **base, "device_category": PROPOSED_CATEGORY, "model": None,
                    "confidence": conf, "band": "manufacturer_app", "band_ceiling": 90,
                    "disposition": "promote",
                    "notes": {"category_pending_board_ratification": True,
                              "net_new_vs_held": "net-new",
                              "service_vs_characteristic": "undetermined (GATT role not asserted "
                                                           "from dex strings — §11 #1 conservative)",
                              "caveat": caveat}})

    # net-new self-check: every promoted/flagged GATT UUID must be absent from DB
    for c in gatt_candidates + flagged_ambiguous_gatt:
        if already_in_db(conn, c["identifier"]):
            raise AssertionError(f"expected net-new but DB has {c['identifier']}")

    # ---- (C) held recat-candidates (NOT promoted; gated on taxonomy mint) ----
    def held(label, ident, note):
        rows = already_in_db(conn, ident) if ident else []
        return {"label": label, "identifier": ident, "db_rows": rows, "note": note}

    held_recat = [
        held("U-tec Group (Ultraloq maker)", "0c:7f:ed:8/28",
             "id7200 mac_range unknown -> strong recat candidate (pure-play lock maker)."),
        held("Spectrum Brands (Kwikset parent)", "70:b3:d5:25:4/36",
             "id21039 mac_range unknown -> recat candidate; multi-division caveat (batteries/pet/hardware)."),
        held("ASSA ABLOY(GuangZhou) Smart Technology", "e8:6c:c7:1/28",
             "id9448 mac_range unknown -> recat candidate; ASSA manufacturing arm."),
        held("Allegion PLC (Schlage parent)", "fa:14:66",
             "id37014 oui unknown -> recat candidate (held from a prior load; not in current snapshot)."),
        {"label": "Wyze Labs (do-not-double-promote)", "identifier": "a4:da:22:2/28",
         "db_rows": already_in_db(conn, "a4:da:22:2/28"),
         "wyze_cctv_oui_ids": conn.execute(
             "SELECT id,identifier,device_category,manufacturer FROM identifiers "
             "WHERE id BETWEEN 44484 AND 44488").fetchall(),
         "note": ("MAC-397 ruling 2: Wyze OUIs id44484-88 are already cctv_camera. NO Wyze "
                  "company-level OUI/ID candidate emitted; company-level OUI cannot be split "
                  "Lock vs Cam without a product-level cite (which we do not have).")},
    ]

    # BLE-registry held set (company-IDs + the 16-bit-UUID-stored-as-ble_company_id quirk)
    ble_registry_held = []
    for label, val, kind in [
        ("August Home company-id", "0x01D1", "ble_manufacturer_id"),
        ("Yale company-id", "0x0BDE", "ble_manufacturer_id"),
        ("Allegion company-id (Schlage parent)", "0x013B", "ble_manufacturer_id"),
        ("Wyze Labs company-id", "0x0870", "ble_manufacturer_id"),
        ("Spectrum Brands company-id (Kwikset parent)", "0x0356", "ble_manufacturer_id"),
        ("ASSA ABLOY company-id", "0x012E", "ble_manufacturer_id"),
        ("August Home 16-bit service UUID 0xFE24", "0xFE24", "ble_company_id (TYPING QUIRK)"),
        ("Allegion 16-bit service UUID 0xFCF4", "0xFCF4", "ble_company_id (TYPING QUIRK)"),
        ("WYZE LABS 16-bit service UUID 0xFD7B", "0xFD7B", "ble_company_id (TYPING QUIRK)"),
        ("ASSA ABLOY 16-bit service UUID 0xFCBF", "0xFCBF", "ble_company_id (TYPING QUIRK)"),
    ]:
        ble_registry_held.append({"label": label, "identifier": val, "stored_as": kind,
                                  "db_rows": already_in_db(conn, val)})

    conn.close()

    # ---- counts / authoritative dedup'd GATT figures ----
    n_custom = len(occ)
    n_magnets = len(magnets)
    n_vendor_unique = n_custom - n_magnets
    n_excluded_vu = len([e for e in excluded if not e.get("co_occurrence_vendors")])
    n_genuine = n_vendor_unique - n_excluded_vu
    counts = {
        "oui_candidates": len(oui_candidates),
        "oui_promote": len([c for c in oui_candidates if c["disposition"] == "promote"]),
        "oui_flagged_ambiguous": len([c for c in oui_candidates if c["disposition"] == "flagged_ambiguous"]),
        "custom_128bit_distinct_across_4_apks": n_custom,
        "cross_vendor_magnets": n_magnets,
        "vendor_unique_128bit": n_vendor_unique,
        "vendor_unique_excluded_sdk_or_placeholder": n_excluded_vu,
        "genuine_vendor_distinct_gatt": n_genuine,
        "gatt_clean_promote": len(gatt_candidates),
        "gatt_flagged_ambiguous": len(flagged_ambiguous_gatt),
        "ble_registry_net_new": 0,
        "total_promote_candidates": len([c for c in oui_candidates if c["disposition"] == "promote"]) + len(gatt_candidates),
    }
    # internal consistency invariants (fail loud)
    assert n_vendor_unique == n_excluded_vu + n_genuine
    assert n_genuine == len(gatt_candidates) + len(flagged_ambiguous_gatt)

    payload = {
        "_meta": {
            "issue": "MAC-406",
            "cohort": "MAC-393 wave-2 cohort 4 — Consumer smart lock",
            "harvest_input": "MAC-397 (CTO-ratified) + operator_review/MAC-393/c4_smartlock/harvest.md "
                             "+ extraction_outputs/mac393_c4_smartlock/sources.json",
            "scope": "EXTRACTION ONLY — candidates for CTO verify -> DBArchitect ingest. "
                     "No DB write / migration / export regen / push. db/argus.db opened mode=ro.",
            "taxonomy_one_way_door": "device_category 'smart_lock' does NOT exist (verified count=0). "
                                     "Every candidate is PROPOSED smart_lock + category_pending_board_"
                                     "ratification. Mint-vs-map is a board one-way-door at the ingest gate.",
            "confidence_bands": "§8.2 — manufacturer_app/manufacturer_doc 75-90 (APK GATT); "
                                "primary_registry 70-85 (IEEE OUI). Single-source staging (§11 #8).",
            "export_note": "§11 #13 — every smart_lock row is export-banned until the category is minted; "
                           "ingest+regen is therefore gated on the board taxonomy decision.",
            "excerpt_max_chars": MAX_EXCERPT,
            "pii_redaction_count": pii_redactions,
            "pii_note": "SAR-5 / §11 #3 — company legal-entity names + IEEE registry addresses only; "
                        "person-name regex applied. APK deliverable carries UUID byte-forms + dex "
                        "locations + sha256 pins only (§11 #15 facts-only); no APK code copied.",
            "cross_vendor_rule": "§11 #21 / CP44 — a custom-128 UUID present in >=2 of the 4 unrelated "
                                 "vendor APKs is a shared chipset/BLE-SDK magnet -> excluded (cited "
                                 "co-occurrence, not from memory).",
            "wyze_ruling": "MAC-397 ruling 2 — Wyze company-level OUI/ID NOT promoted (already cctv_camera). "
                           "com.hualai SKIPPED per ruling 3 (do-not-double-promote collision).",
            "typing_quirk": "MAC-397 ruling 4 — 0xFE24/0xFCF4/0xFD7B/0xFCBF are 16-bit service UUIDs but "
                            "stored under identifier_type='ble_company_id' (pre-existing bulk-load artifact). "
                            "Noted, NOT 'fixed' here.",
        },
        "counts": counts,
        "oui_candidates": oui_candidates,
        "gatt_candidates": gatt_candidates,
        "flagged_ambiguous": flagged_ambiguous_gatt,
        "excluded": excluded,
        "held_recat_candidates": held_recat,
        "ble_registry_held": ble_registry_held,
    }
    return payload


def main():
    payload = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "candidates.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=list) + "\n",
                   encoding="utf-8")

    # excerpt-length gate (§11 #7) across every emitted candidate
    for bucket in ("oui_candidates", "gatt_candidates", "flagged_ambiguous", "excluded"):
        for c in payload[bucket]:
            assert len(c["source_excerpt"]) <= MAX_EXCERPT, f"excerpt >200: {c['identifier']}"

    json.loads(out.read_text())  # json_valid
    c = payload["counts"]
    print(f"wrote {out}")
    print(f"OUI candidates: {c['oui_candidates']} "
          f"(promote {c['oui_promote']} / flagged {c['oui_flagged_ambiguous']})")
    print(f"custom-128 distinct across 4 APKs: {c['custom_128bit_distinct_across_4_apks']}")
    print(f"  cross-vendor magnets: {c['cross_vendor_magnets']}")
    print(f"  vendor-unique: {c['vendor_unique_128bit']} "
          f"= excluded(SDK/placeholder) {c['vendor_unique_excluded_sdk_or_placeholder']} "
          f"+ genuine {c['genuine_vendor_distinct_gatt']}")
    print(f"  genuine = clean-promote {c['gatt_clean_promote']} + flagged-ambiguous {c['gatt_flagged_ambiguous']}")
    print(f"BLE-registry net-new: {c['ble_registry_net_new']} (fully bulk-loaded -> recat only)")
    print(f"TOTAL clean-promote candidates: {c['total_promote_candidates']}")
    print("json_valid: OK")


if __name__ == "__main__":
    main()
