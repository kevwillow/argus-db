"""MAC-403 — Wave-2 Cohort 3 (Bluetooth tracker) EXTRACTION.

Turns the CTO-ratified MAC-396 harvest (under MAC-393) into structured
promotion candidates for CTO review -> DBArchitect ingest. EXTRACTION ONLY:
emits extraction_outputs/mac393_c3_bletracker/candidates.json. NO DB write, NO
ingest, NO migration, NO export regen, NO push. Raw bytes never enter git.

Verified net-new surface (per MAC-403 brief + MAC-396 ratification):
  * Pebblebee ble_service_uuid 0xFA25 (0000fa25-...) — single-source crowdsourced
    (AirGuard sid24, <=75). The ONLY clean vendor-distinct net-new identifier.
  * Cube 0x03EE 'CUBE TECHNOLOGIES' — already held (id4010); recat only if the
    Cube APK ties 0x03EE to the Cube *tracker* product.

Scoped, CTO-authorized APK enrichment (exactly two named apps, bounded):
  (a) Pebblebee app (com.pebblebee.pebblebeeplus) -> corroborate 0xFA25
      => §8.3 value-level lift if a 2nd independent collector carries the value.
  (b) Cube app (com.blueskyhomesales.cube) -> verify 0x03EE == Cube tracker +
      surface any Cube-distinct GATT service UUID.
Atuvos/Nutale/KeySmart APKs NOT authorized (Apple-piggyback cross-vendor).

This module re-derives EVERY candidate field from the on-disk raw artifacts
(re-grepped / re-scanned here, never trusted from the harvest):
  * SIG yaml + AirGuard .kt cite-pastes are verbatim substrings of the named file.
  * APK enrichment is a deterministic static scan (pure-stdlib zipfile + regex over
    .dex byte pools) of the gitignored APKs, keyed by sha256. Same APK -> same result.
  * already_in_db: read-only lookup against live db/argus.db (mode=ro).

Discipline (bible §7.3 / §8.2 / §8.3 / §11 + MAC-403 hard gates):
  * §11 #1  Conservative. 0xFA25 stays single-source when the app lacks it.
            No Cube candidate emitted (0x03EE absent + ambiguous bundled-SDK UUIDs).
  * §11 #15 APK facts-only; raw/ gitignored; deliverable cites value+path+sha256 only.
  * §11 #3  No PII; only company legal-entity names + class/UUID facts.
  * §11 #7  source_excerpt enforced <=200 chars at build time (assert + truncate).
  * §11 #8  No confidence drift; staged at single-source confidence.
  * tagfinder (sid29) company-id table is FABRICATED -> rejected, never a corroborator.
  * Cross-vendor ecosystem UUIDs (FEAA/FD44/004C/FE59) excluded (already held).
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
OUT_DIR = REPO / "extraction_outputs" / "mac393_c3_bletracker"

SIG_BASE_SUFFIX = "-0000-1000-8000-00805f9b34fb"  # SIG 16-bit base UUID
MAX_EXCERPT = 200  # §11 #7 app-level enforcement

# --- raw artifact relative paths (provenance-only; raw/ is gitignored) --------
A_AIRGUARD_PB = ("raw/airguard/app/src/main/java/de/seemoo/at_tracking_detection/"
                 "database/models/device/types/PebbleBee.kt")
A_AIRGUARD_GFM = ("raw/airguard/app/src/main/java/de/seemoo/at_tracking_detection/"
                  "database/models/device/types/GoogleFindMyNetwork.kt")
A_SIG_COMPANY = "raw/bluetooth_sig/20260613T203034Z_company_identifiers.yaml"
A_SIG_CHAR = "raw/bluetooth_sig/20260613T203034Z_characteristic_uuids.yaml"
A_SIG_MEMBER = "raw/bluetooth_sig/20260613T203034Z_member_uuids.yaml"
A_TAGFINDER = "raw/tagfinder/20260613T203034Z_tagfinder.py"

# --- CTO-authorized companion APKs (sha256-pinned; gitignored) -----------------
APK_PEBBLEBEE = {
    "vendor": "Pebblebee",
    "package": "com.pebblebee.pebblebeeplus",
    "version": "2.2.3",
    "artifact": "raw/vendor_apps/pebblebee/com.pebblebee.pebblebeeplus/2.2.3/pebblebee.xapk",
    "sha256": "76b587956b610911652dd5d0602252d733a6834cbf75d3d2a8d2ad0ff02bc855",
    "doc_kind": "xapk",
    "source_url": "https://apkcombo.com/pebblebee/com.pebblebee.pebblebeeplus/download/apk",
}
APK_CUBE = {
    "vendor": "Cube",
    "package": "com.blueskyhomesales.cube",
    "version": "latest",
    "artifact": "raw/vendor_apps/cube/com.blueskyhomesales.cube/latest/cube.xapk",
    "sha256": "af6e7ce474ce1a0b00ba226d6d84cb447e16f88ab5c378c567b5797c2d158e63",
    "doc_kind": "apk",
    "source_url": "https://apkcombo.com/cube-tracker/com.blueskyhomesales.cube/download/apk",
}

_file_cache: dict[str, list[str]] = {}

UUID_FULL_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SIG16_RE = re.compile(r"0000([0-9a-f]{4})" + re.escape(SIG_BASE_SUFFIX))


def _lines(rel: str) -> list[str]:
    if rel not in _file_cache:
        p = REPO / rel
        if not p.exists():
            raise FileNotFoundError(f"raw artifact missing: {rel}")
        _file_cache[rel] = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return _file_cache[rel]


def locate(rel: str, token: str) -> tuple[int, str]:
    """Return (1-indexed line number, verbatim <=200-char excerpt) of first match.

    Raises if the token is absent — no fabrication (§11 #1). Excerpt is enforced
    <=200 chars (§11 #7) with a truncation marker.
    """
    for i, ln in enumerate(_lines(rel)):
        if token in ln:
            excerpt = ln.strip()
            if len(excerpt) > MAX_EXCERPT:
                excerpt = excerpt[:MAX_EXCERPT - 1] + "…"
            return i + 1, excerpt
    raise ValueError(f"token {token!r} NOT found in {rel} — refusing to fabricate")


def canon_uuid(raw: str) -> str:
    """§4.3 canonical lowercase 8-4-4-4-12. 16-bit '0xFA25' -> SIG-base form."""
    s = raw.strip()
    if s.lower().startswith("0x"):
        s = s[2:]
    s = s.replace("-", "").lower()
    if not s or any(ch not in "0123456789abcdef" for ch in s):
        raise ValueError(f"non-hex UUID-like value: {raw!r}")
    if len(s) == 4:
        s = "0000" + s
    if len(s) == 8:
        return s + SIG_BASE_SUFFIX
    if len(s) == 32:
        return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"
    raise ValueError(f"cannot canonicalize UUID-like value: {raw!r} (len {len(s)})")


# ---------------------------------------------------------------------------
# APK static enrichment — deterministic, pure-stdlib (zipfile + regex)
# ---------------------------------------------------------------------------
def _iter_dex_blobs(apk_path: Path):
    """Yield (entry_name, bytes) for every classes*.dex found in the APK/XAPK.

    Handles XAPK (zip-of-apks): recurses one level into nested *.apk entries.
    Deterministic: zip entries iterated in archive order, sorted by name.
    """
    with zipfile.ZipFile(apk_path) as z:
        names = sorted(z.namelist())
        for n in names:
            if n.endswith(".dex"):
                yield n, z.read(n)
        for n in names:
            if n.endswith(".apk"):
                with zipfile.ZipFile(__import__("io").BytesIO(z.read(n))) as inner:
                    for m in sorted(inner.namelist()):
                        if m.endswith(".dex"):
                            yield f"{n}!{m}", inner.read(m)


def apk_scan(apk_path: Path) -> dict:
    """Deterministic static scan of an APK's dex string pools (§11 #15 facts-only).

    Returns sorted UUID inventories + presence booleans. No code/arrangement
    copied; only UUID facts + token presence are surfaced.
    """
    sig16: set[str] = set()
    custom128: set[str] = set()
    raw = b""
    for _, blob in _iter_dex_blobs(apk_path):
        raw += blob
    text = raw.decode("latin-1").lower()
    for m in UUID_FULL_RE.finditer(text):
        u = m.group(0)
        if u.endswith(SIG_BASE_SUFFIX):
            sig16.add(u)
        elif not (set(u) <= set("0-f") and u.replace("-", "") in ("0" * 32, "f" * 32)):
            custom128.add(u)
    return {
        "sig16_service_uuids": sorted(sig16),
        "custom_128bit_uuids": sorted(custom128),
        "fa25_present": canon_uuid("0xFA25") in sig16 or '"fa25"' in text,
        "uuid_2c02_present": canon_uuid("0x2C02") in sig16,
        "company_03ee_present": bool(re.search(r"(^|[^0-9a-f])03ee([^0-9a-f]|$)", text))
        or "0x03ee" in text,
        "cube_tracker_namespace": "com/cubetracker" in text or "blueskyhomesales/cube" in text,
        "nordic_nbtracker_profile": "nordic_nbtracker_profile" in text or "nordic nbtracker" in text,
    }


def file_sha256(rel: str) -> str:
    h = hashlib.sha256()
    h.update((REPO / rel).read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Promotion-candidate / record specs
# ---------------------------------------------------------------------------
@dataclass
class Cand:
    value_raw: str
    identifier_type: str
    device_category: str
    vendor: str
    band: str
    confidence: int
    band_ceiling: int
    source_sid: object
    artifact: str
    token: str
    corroboration: str
    caveats: list = field(default_factory=list)
    is_company: bool = False


def already_in_db(conn, value: str, identifier_type: str | None = None):
    if identifier_type is None:
        rows = conn.execute(
            "SELECT id,identifier_type,device_category,manufacturer FROM identifiers "
            "WHERE lower(identifier)=lower(?) AND superseded_by IS NULL", (value,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT id,identifier_type,device_category,manufacturer FROM identifiers "
            "WHERE lower(identifier)=lower(?) AND identifier_type=? AND superseded_by IS NULL",
            (value, identifier_type)).fetchall()
    return rows


# The ONE clean net-new promotion candidate.
PROMOTION_CANDIDATES = [
    Cand(
        value_raw="0xFA25", identifier_type="ble_service_uuid",
        device_category="bluetooth_tracker", vendor="Pebblebee",
        band="crowdsourced", confidence=65, band_ceiling=75,
        source_sid=24, artifact=A_AIRGUARD_PB,
        token='offlineFindingServiceUUID: ParcelUuid = ParcelUuid.fromString("0000FA25-0000-1000-8000-00805F9B34FB")',
        corroboration=(
            "SINGLE-SOURCE (AirGuard sid24, crowdsourced). NOT SIG-registered (absent from "
            "member_uuids.yaml -> Pebblebee-proprietary 16-bit UUID). CTO-authorized Pebblebee "
            "APK enrichment ATTEMPTED (com.pebblebee.pebblebeeplus v2.2.3, sha 76b5879...) -> 0xFA25 "
            "NOT present in app dex -> NO §8.3 value-level lift. Stays single-source <=75 (honest outcome)."),
        caveats=[
            "Connectable SOUND / offline-finding GATT service (AirGuard ScanFilter serviceUuid at "
            "PebbleBee.kt:197-200) -> advertised by offline-finding units but observed on CONNECT, "
            "not guaranteed in passive adv.",
            "Paired char 0x2C02 (PebbleBee.kt:190) is SIG-standard 'UGT Features' "
            "(characteristic_uuids.yaml:1377) -> NOT vendor-distinct; explicitly NOT promoted.",
            "Pebble Technology (smartwatch) rows id4624/id9839/id37761 are a DIFFERENT company; do not conflate.",
        ],
    ),
]

# Rejected fabrications (tagfinder) — recorded, never promoted (§11 #1).
REJECTED = [
    {"value": "0x0183", "claimed_vendor": "Pebblebee", "identifier_type": "ble_company_id",
     "artifact": A_TAGFINDER, "token": '0x0183: "PEBBLEBEE"',
     "reason": "FABRICATED — authoritative SIG company_identifiers.yaml 0x0183='Walt Disney'.",
     "sig_contradiction_token": "value: 0x0183"},
    {"value": "0x022A", "claimed_vendor": "Nutale", "identifier_type": "ble_company_id",
     "artifact": A_TAGFINDER, "token": '0x022A: "Nutale"',
     "reason": "FABRICATED — authoritative SIG company_identifiers.yaml 0x022A='Stamer Musikanlagen GMBH'.",
     "sig_contradiction_token": "value: 0x022A"},
]

# Cross-vendor ecosystem UUIDs — excluded (already held), per wave-1 ruling.
EXCLUDED_CROSS_VENDOR = [
    {"value": "0xFEAA", "vendor": "Google FMD / Eddystone", "artifact": A_AIRGUARD_GFM,
     "token": '0000FEAA-0000-1000-8000-00805F9B34FB', "held_as": "ble_company_id id37808 (Google LLC)"},
    {"value": "0xFD44", "vendor": "Apple Find My", "artifact": None,
     "token": None, "held_as": "ble_service_uuid id22876 (bluetooth_tracker) / id38159 ble_company_id"},
    {"value": "0x004C", "vendor": "Apple", "artifact": None,
     "token": None, "held_as": "ble_company_id id568 / id22842"},
    {"value": "0xFE59", "vendor": "Nordic Semiconductor (DFU)", "artifact": None,
     "token": None, "held_as": "wave-1 excluded cross-vendor chipset DFU service"},
]


def build():
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    # ---- promotion candidates (SIG/AirGuard, re-grepped) ----
    candidates = []
    for c in PROMOTION_CANDIDATES:
        value = c.value_raw if c.is_company else canon_uuid(c.value_raw)
        line, excerpt = locate(c.artifact, c.token)
        full = "\n".join(_lines(c.artifact))
        if excerpt.rstrip("…") not in full:
            raise AssertionError(f"excerpt not greppable in {c.artifact}: {excerpt!r}")
        db_rows = already_in_db(conn, value, c.identifier_type)
        candidates.append({
            "value": value,
            "identifier_type": c.identifier_type,
            "device_category": c.device_category,
            "manufacturer": c.vendor,
            "band": c.band,
            "confidence": c.confidence,
            "band_ceiling": c.band_ceiling,
            "source_sid": c.source_sid,
            "source_markers": {"artifact": c.artifact, "line": line, "excerpt": excerpt,
                               "artifact_sha256": file_sha256(c.artifact)},
            "db_presence": "net-new" if not db_rows else f"held: {db_rows}",
            "corroboration": c.corroboration,
            "caveats": c.caveats,
        })

    # ---- rejected fabrications (cite + SIG contradiction, both re-grepped) ----
    rejected = []
    for r in REJECTED:
        line, excerpt = locate(r["artifact"], r["token"])
        sig_line, sig_excerpt = locate(A_SIG_COMPANY, r["sig_contradiction_token"])
        rejected.append({
            "value": r["value"], "claimed_vendor": r["claimed_vendor"],
            "identifier_type": r["identifier_type"], "disposition": "REJECTED (not staged)",
            "reason": r["reason"],
            "source_markers": {"artifact": r["artifact"], "line": line, "excerpt": excerpt},
            "sig_authority": {"artifact": A_SIG_COMPANY, "line": sig_line, "excerpt": sig_excerpt},
        })

    # ---- excluded cross-vendor (held) ----
    excluded = []
    for e in EXCLUDED_CROSS_VENDOR:
        value = canon_uuid(e["value"])
        marker = None
        if e["artifact"] and e["token"]:
            line, excerpt = locate(e["artifact"], e["token"])
            marker = {"artifact": e["artifact"], "line": line, "excerpt": excerpt}
        excluded.append({
            "value": value, "short": e["value"], "vendor": e["vendor"],
            "disposition": "EXCLUDED — cross-vendor ecosystem service, already held (wave-1 ruling)",
            "held_as": e["held_as"], "source_markers": marker,
            "db_presence": str(already_in_db(conn, value)),
        })

    # ---- APK enrichment (deterministic static scan of the two authorized apps) ----
    pb_scan = apk_scan(REPO / APK_PEBBLEBEE["artifact"])
    cube_scan = apk_scan(REPO / APK_CUBE["artifact"])
    # sha self-verify against pins (§11 #1 — fail loud if the on-disk binary drifted)
    for spec in (APK_PEBBLEBEE, APK_CUBE):
        got = file_sha256(spec["artifact"])
        if got != spec["sha256"]:
            raise AssertionError(f"APK sha256 drift {spec['package']}: {got} != pinned {spec['sha256']}")

    apk_enrichment = {
        "pebblebee": {
            **{k: APK_PEBBLEBEE[k] for k in ("vendor", "package", "version", "artifact", "sha256",
                                             "doc_kind", "source_url")},
            "fetch_method": "apkcombo->pureapk XAPK via headless chromium (Cloudflare-gated); facts-only",
            "target": "corroborate Pebblebee ble_service_uuid 0xFA25",
            "fa25_present_in_app_dex": pb_scan["fa25_present"],
            "uuid_2c02_present_in_app_dex": pb_scan["uuid_2c02_present"],
            "outcome": (
                "NOT CORROBORATED — 0xFA25 absent from app dex string pool. App uses standard SIG "
                "services + 11 custom 128-bit GATT UUIDs (Nordic BLE-library provisioning/config). "
                "0xFA25 stays SINGLE-SOURCE <=75; no §8.3 lift. Valid honest outcome per MAC-403 brief."),
            "sig16_service_uuids_in_app": pb_scan["sig16_service_uuids"],
            "custom_128bit_uuids_in_app": pb_scan["custom_128bit_uuids"],
        },
        "cube": {
            **{k: APK_CUBE[k] for k in ("vendor", "package", "version", "artifact", "sha256",
                                        "doc_kind", "source_url")},
            "fetch_method": "apkcombo->pureapk APK via headless chromium (Cloudflare-gated); facts-only",
            "target": "verify 0x03EE=='CUBE TECHNOLOGIES' tracker + surface Cube-distinct GATT service UUID",
            "is_cube_tracker_product": cube_scan["cube_tracker_namespace"],
            "is_nbiot_cellular_tracker": cube_scan["nordic_nbtracker_profile"],
            "company_id_03ee_present_in_app": cube_scan["company_03ee_present"],
            "outcome": (
                "0x03EE NOT present in Cube app (company-id 1006 hits are dex bytecode offsets, not "
                "manufacturer company-ids) -> 'CUBE TECHNOLOGIES' (id4010) NOT demonstrably the Cube "
                "tracker -> NO 0x03EE recat. Product is an NB-IoT CELLULAR GPS tracker "
                "(NORDIC_NBTRACKER_PROFILE); BLE is local-config only. BLE UUID surface is bundled-SDK "
                "(Nordic DFU + TI-OAD 0xF000 range + SIG-standard) -> no clean Cube-distinct advertised "
                "service UUID -> NO candidate (§11 #1 conservative)."),
            "sig16_service_uuids_in_app": cube_scan["sig16_service_uuids"],
            "custom_128bit_uuids_in_app": cube_scan["custom_128bit_uuids"],
        },
    }

    # ---- flagged for CTO (transparency; NOT promoted this dispatch) ----
    flagged_for_cto = [
        {"flag": "pebblebee_custom_gatt_uuids_not_authorized",
         "detail": ("Pebblebee app carries 11 custom 128-bit GATT UUIDs (config/provisioning via Nordic "
                    "BLE library). The MAC-403 Pebblebee APK authorization was CORROBORATION-ONLY (0xFA25); "
                    "harvesting these as new identifiers would expand scope. Surfaced for potential future "
                    "CTO authorization. Connectable services (not passive adv); DB-presence unchecked."),
         "values": apk_enrichment["pebblebee"]["custom_128bit_uuids_in_app"]},
        {"flag": "cube_is_nbiot_cellular_gps_tracker",
         "detail": ("Cube (cube.tech / com.blueskyhomesales.cube) is an NB-IoT cellular GPS tracker, NOT a "
                    "BLE Find-My beacon. Mirrors the cohort-2 GPS-tracker finding (~0 RF/BLE export surface). "
                    "No vendor-distinct BLE identifier; 0x03EE link unproven and stays held@unknown.")},
    ]

    conn.close()
    payload = {
        "_meta": {
            "issue": "MAC-403",
            "cohort": "MAC-393 wave-2 cohort 3 — Bluetooth tracker",
            "harvest_input": "MAC-396 (CTO-ratified) + extraction_outputs/mac393_c3_bletracker/{leads,sources}.json",
            "scope": "EXTRACTION ONLY — candidates for CTO review -> DBArchitect ingest. "
                     "No DB write / migration / export regen / push. db/argus.db opened mode=ro.",
            "device_category": "bluetooth_tracker (exported category; promotion is a CEO one-way door at ship gate)",
            "apk_enrichment_authorization": "CTO-authorized exactly two apps (Pebblebee + Cube); "
                                            "Atuvos/Nutale/KeySmart NOT authorized (Apple-piggyback cross-vendor).",
            "excerpt_max_chars": MAX_EXCERPT,
            "pii_redaction_count": 0,
            "pii_note": "No person-PII surfaced. Deliverable carries UUID values + company legal-entity "
                        "names + class/UUID facts + sha256 pins only (§11 #3 / §11 #15). No APK code copied.",
            "tagfinder_note": "tagfinder (sid29) company-id table is FABRICATED (every contested mapping "
                              "collides with an unrelated SIG name) -> behavioral-only, never an identifier corroborator.",
            "export_meaningfulness": "A promoted Pebblebee 0xFA25 row WOULD reach the Lynceus feed "
                                     "(bluetooth_tracker is exported, wave-1 MAC-387/388) -> ingest+regen is a "
                                     "CEO one-way door (mirrors cohort-1 MAC-373).",
        },
        "candidates": candidates,
        "rejected_fabrications": rejected,
        "excluded_cross_vendor": excluded,
        "apk_enrichment": apk_enrichment,
        "flagged_for_cto": flagged_for_cto,
    }
    return payload


def main():
    payload = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "candidates.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # excerpt-length gate (§11 #7)
    for c in payload["candidates"]:
        assert len(c["source_markers"]["excerpt"]) <= MAX_EXCERPT, "excerpt > 200 chars"

    print(f"wrote {out}")
    print(f"promotion candidates: {len(payload['candidates'])}")
    for c in payload["candidates"]:
        print(f"  {c['identifier_type']} {c['value']} ({c['manufacturer']}) "
              f"conf={c['confidence']} db_presence={c['db_presence'][:20]}")
    print(f"rejected fabrications: {len(payload['rejected_fabrications'])}")
    print(f"excluded cross-vendor: {len(payload['excluded_cross_vendor'])}")
    pb = payload["apk_enrichment"]["pebblebee"]
    cb = payload["apk_enrichment"]["cube"]
    print(f"APK pebblebee: 0xFA25 present={pb['fa25_present_in_app_dex']} -> {('LIFT' if pb['fa25_present_in_app_dex'] else 'no lift')}")
    print(f"APK cube: 0x03EE present={cb['company_id_03ee_present_in_app']} nbiot={cb['is_nbiot_cellular_tracker']} -> no recat")
    json.loads(out.read_text())
    print("json_valid: OK")


if __name__ == "__main__":
    main()
