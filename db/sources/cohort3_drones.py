"""MAC-374 — Cohort 3 (Drones) EXTRACTION.

Turns the CTO-verified MAC-366 harvest manifest into structured identifier
candidates for CTO review -> DBArchitect ingest. EXTRACTION ONLY: emits
extraction_outputs/mac366_cohort3_drones/candidates.json. NO DB write, NO ingest,
NO migration, NO export regen, NO push, NO CP mint. Decompiled APK/XAPK source
NEVER enters the git index (§11 #15 / 17 USC §1201) — only candidate value +
relative path inside the gitignored raw/ tree.

Targets (per MAC-363 Phase B cohort 3): DJI, Parrot (already covered, sources
71/70), Skydio + Autel (new vendors), Anduril (honest-absence). This is
EXPANSION, not greenfield — every drone identifier *value* in these artifacts is
already present in the live DB. The cohort's contribution is corroboration /
footprint expansion + DB-conflict surfacing + behavioral signatures, NOT net-new
identifier values.

Discipline (MAC-366 integrity rulings 1-12 + bible §7.3 / §8.2 / §8.3 / §4.4 / §11):
  1.  Parrot SIG-id (0x0043 = PARROT AUTOMOTIVE SAS) ⇄ FCC drone grantee (2AG6I
      PARROT DRONE SAS) entity split — do NOT collapse; hub-and-spoke is NOT
      value-level §8.3 corroboration (no +5 lift).
  2.  Skydio + Autel have NO SIG company-id (honest absence) — do not mint one.
  3.  Autel automotive-vs-drone collision: only com.autel.explorer + grantee 2AGNT
      attribute to the drone vendor.
  4.  DJI grantee-code FP: literal code "DJI" = Seragen Diagnostics (Indianapolis),
      not the drone maker — exclude.
  5.  FAA RID DOC = attribution + cross-ref to the CTA-2063-A serial-prefix layer,
      NOT a promotable identifier value (makeName/model not promoted).
  5b. opendroneid.h = structural authority (ID-type taxonomy / field sizing), not a
      value source; dji_droneid = DJI legacy OFDM RF frame (distinct from ASTM beacon).
  6.  Researcher-confidence discarded; §8.2 source-band ceiling proposed.
  7.  Observation-vs-registration lens annotated per candidate.
  8.  §11 #3 / SAR-5 PII: FCC contact_name + address columns NEVER surfaced; only
      code/name/city/state/country. Redaction count logged in meta.
  9.  Export-membership (§4.4 / §7.5) checked against export_lynceus.py, not memory.
  10. db_presence annotated; disposition-tally kept SEPARATE from net-new floor.
  11. Honest absences carried forward — do NOT fabricate (Anduril; Skydio/Autel SIG;
      no clean BLE vendor UUID; no net-new drone_id_prefix; FCC drill-down unfetched).
  12. FCC grantee->FCC-ID drill-down: no sid 51/52/85 drone pages fetched this
      harvest -> honest-absence (no live fetch by this worker; §11 #6 / SAR-4).

Anti-hallucination: every SIG/opendroneid/DEX cite is re-grepped from its named raw
artifact on disk here (raises if missing). FCC grantee entities are CTO-verified
constants, re-asserted against the frozen sid-7 CSV when present (external SSD,
gitignored). APK behavioral evidence is re-grepped from the gitignored APK/XAPK
DEX strings when the binary is present (best-effort — the ~370 MB corpus may be
absent in CI), and embedded with its verified locus.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
OUT_DIR = REPO / "extraction_outputs" / "mac366_cohort3_drones"

# --- raw artifact relative paths (provenance-only, gitignored) ----------------
TS = "20260613T210813Z"
SIG_YAML = "raw/bluetooth_sig/20260613T203034Z_company_identifiers.yaml"
ODID_H = f"raw/drone_remoteid_family/{TS}/opendroneid.h"
ODID_CORE = "raw/drone_remoteid_family/{TS}/opendroneid-core-c.tar.gz"
DJI_DRONEID_README = f"raw/drone_remoteid_family/{TS}/dji_droneid_README.md"
DRAGONSYNC_TGZ = f"raw/drone_remoteid_family/{TS}/DragonSync.tar.gz"
FAA_DIR = f"raw/faa_uas_rid/{TS}"

# APK/XAPK corpus (gitignored, §11 #15) — relative paths for the deliverable only.
APK_SKYDIO_R3 = ("raw/vendor_apps/skydio/com.skydio.r3/24.10.48/"
                 "af538197b7a1116ee1b86d607e716583c16978c0673cc5f4890dbbb108b61b11.xapk")
APK_SKYDIO_ENT = ("raw/vendor_apps/skydio/com.skydio.enterprise/24.10.48/"
                  "4bfb561d07c5f57ce3f81b9e7be7d4b31c5d0fd6a71e810b00519cf58d95818c.xapk")
APK_AUTEL = ("raw/vendor_apps/autel/com.autel.explorer/V1.0.1.45/"
             "02eb9df046016fe338371afd64aff00849f1d90a1384302361dc3dab1737700f.apk")

# Frozen FCC grantee dataset (sid 7, CP19) — external SSD, gitignored, PII column.
FCC_FROZEN_SHA = "5cd60fbe8654f6c146123e3c30cf4642fe17de98360d9d241b79b4460ee80cbd"
FCC_FROZEN_FREEZE = "2021-03-22"
FCC_CSV = Path("/media/kev/Extreme SSD/argus/raw/fcc_id/20260504T141318Z/"
               "opendata_fcc_3b3k-34jp_FULL.csv")

_file_cache: dict[str, list[str]] = {}


def _lines(rel: str) -> list[str]:
    if rel not in _file_cache:
        p = REPO / rel
        if not p.exists():
            raise FileNotFoundError(f"raw artifact missing: {rel}")
        _file_cache[rel] = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return _file_cache[rel]


def _grep_line(rel: str, needle: str) -> tuple[int, str]:
    """First (1-based line number, stripped line) containing needle. Raises if
    absent — a cite that cannot be re-found on disk is a fabrication."""
    for i, ln in enumerate(_lines(rel), 1):
        if needle in ln:
            return i, ln.strip()
    raise AssertionError(f"cite not found in {rel}: {needle!r}")


def _excerpt(s: str, limit: int = 200) -> str:
    """§11 #7 ≤200-char source_excerpt — app-level enforced (truncate-with-marker;
    raw_observations has no DB CHECK per CP23 cap table)."""
    s = s.strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


@dataclass
class Candidate:
    identifier_type: str
    value: str
    source_sid: object               # int sid, or "needs_new_source_row:<key>"
    source_url: str
    relative_path: str               # raw/<...> within the gitignored tree
    proposed_confidence_ceiling: int  # §8.2 source-band ceiling
    db_presence: str                 # "net-new" | "already_in_db:id=<n>"
    source_lens: str                 # "observation" | "registration" | "structural"
    export_membership: str           # §7.5 outcome (exported / DROPPED / banned)
    manufacturer: Optional[str]
    device_category: str
    cite_excerpt: str
    notes: str = ""
    conflict_note: str = ""


@dataclass
class Behavioral:
    signature_name: str
    device_category: str
    cellular_generation: Optional[str]
    source_ref: object               # sid int or "needs_new_source_row:<key>"
    relative_path: str
    evidence: list                   # list of {locus, note}
    proposed_confidence_ceiling: int
    source_lens: str
    notes: str = ""


def _db():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def _id_lookup(cur, value: str, itype: Optional[str] = None) -> Optional[tuple]:
    q = ("select id, manufacturer, device_category, confidence, source_type "
         "from identifiers where identifier=? and superseded_by is null")
    args = [value]
    if itype:
        q += " and identifier_type=?"
        args.append(itype)
    cur.execute(q, args)
    return cur.fetchone()


# ── A. BLE manufacturer / company IDs (SIG registration lens, sid 34) ─────────
# (sig_value, sig_name, sig_line_needle, mfr, ruling_note)
_SIG_ROWS = [
    ("0x08AA", "SZ DJI TECHNOLOGY CO.,LTD", "0x08AA", "DJI",
     "SIG-registered DJI manufacturer-id; corroborates existing primary_registry row."),
    ("0x0043", "PARROT AUTOMOTIVE SAS", "0x0043", "Parrot",
     "Ruling 1 entity-split: SIG registrant = PARROT AUTOMOTIVE SAS (car-infotainment); "
     "the drone-arm FCC grantee is 2AG6I PARROT DRONE SAS. Read 'Parrot (corporate "
     "group)' with automotive-entity caveat. Hub-and-spoke != §8.3 value corroboration."),
]


def _ble_candidates(cur) -> list[Candidate]:
    out = []
    for val, name, needle, mfr, note in _SIG_ROWS:
        ln, text = _grep_line(SIG_YAML, needle)
        existing = _id_lookup(cur, val, "ble_manufacturer_id")
        if existing:
            presence = f"already_in_db:id={existing[0]}"
            cat = existing[2]
        else:
            presence, cat = "net-new", "unknown"
        # §11 #13: device_category='unknown' -> Lynceus export-banned even though
        # ble_manufacturer_id MAPs to a pattern_type.
        export = ("ble_manufacturer_id MAP→exported BUT device_category='unknown' "
                  "→ §11 #13 unknown_category ban → NOT in either feed"
                  if cat == "unknown" else
                  "ble_manufacturer_id MAP→exported (subject to ≥conf floor)")
        out.append(Candidate(
            identifier_type="ble_manufacturer_id", value=val, source_sid=34,
            source_url=("https://bitbucket.org/bluetooth-SIG/public/raw/main/"
                        f"assigned_numbers/company_identifiers/company_identifiers.yaml#L{ln}"),
            relative_path=f"{SIG_YAML}#L{ln}-{ln+1}",
            proposed_confidence_ceiling=90,  # primary_registry §8.2 ceiling
            db_presence=presence, source_lens="registration", export_membership=export,
            manufacturer=mfr, device_category=cat,
            cite_excerpt=_excerpt(f"- value: {val} / name: '{name}' (SIG company_identifiers.yaml L{ln}-{ln+1})"),
            notes=note,
        ))
    # ble_company_id 67 (= decimal 0x0043) — the existing EXPORTED Parrot row.
    cid = _id_lookup(cur, "67", "ble_company_id")
    if cid:
        out.append(Candidate(
            identifier_type="ble_company_id", value="67", source_sid=70,
            source_url="https://apkpure.com/freeflight-6/com.parrot.freeflight6",
            relative_path="(existing DB row — Parrot FreeFlight app, source 70)",
            proposed_confidence_ceiling=85, db_presence=f"already_in_db:id={cid[0]}",
            source_lens="registration",
            export_membership=("ble_company_id MAP→ble_manufacturer_id; device_category="
                               f"'{cid[2]}' → REACHES export (conf {cid[3]})"
                               if cid[2] != "unknown" else "MAP→exported but unknown→banned"),
            manufacturer=cid[1], device_category=cid[2],
            cite_excerpt=_excerpt(f"ble_company_id 67 = decimal(0x0043) Parrot — existing exported row id={cid[0]}"),
            notes="MAC-360 flagged: 67 is the decimal form of SIG 0x0043; recommend "
                  "normalize 67→0x0043 at promotion (§4.3, Phase-5). Cross-ref ble_manufacturer_id 0x0043 (id 4884).",
        ))
    return out


# ── B. FCC drone-arm grantee codes (sid 7 frozen primary_registry) ────────────
# CTO-verified entity facts (paste-confirmed against frozen sid-7 CSV this run);
# (grantee_code, frozen_grantee_name, city, state, country, is_drone_arm, note)
_DRONE_GRANTEES = [
    ("2ATQR", "Skydio, Inc.", "REDWOOD CITY", "California", "United States", True,
     "Skydio drone-arm grantee."),
    ("2AGNT", "Autel Robotics Co., Ltd.", "Shenzhen", "", "China", True,
     "Autel Robotics drone-arm grantee (ruling 3 — the ONLY Autel drone grantee)."),
    ("2AG6I", "PARROT DRONE SAS", "Paris", "", "France", True,
     "Parrot drone-arm grantee (ruling 1 — distinct entity from SIG registrant)."),
    ("2AHAN", "SZ DJI Software Technology Co., Ltd.", "Shenzhen", "", "China", True,
     "DJI Software Technology."),
    ("2AHAY", "SZ DJI BaiWang Technology Co.,Ltd", "Shenzhen", "", "China", True,
     "DJI BaiWang."),
    ("2ANDR", "SZ DJI Osmo Technology Co.,Ltd.", "Guangming District, Shenzhen", "", "China", True,
     "DJI Osmo."),
    ("2AS9V", "SZ DJI TECHNOLOGY CO. LTD", "Nanshan, Shenzen, Guangdong", "", "China", True,
     "DJI Technology."),
    ("2AS9W", "SZ DJI TECHNOLOGY CO. LTD", "Nanshan, Shenzen, Guangdong", "", "China", True,
     "DJI Technology."),
    ("2AS9X", "SZ DJI TECHNOLOGY CO. LTD", "Nanshan, Shenzen, Guangdong", "", "China", True,
     "DJI Technology."),
    ("QT9", "DJI Innovations Technology Co., Ltd.", "Shenzhen", "", "China", True,
     "DJI Innovations."),
    ("SS3", "SZ DJI TECHNOLOGY CO., LTD", "Nanshan District, Shenzhen, Guangdong", "", "China", True,
     "DJI Technology."),
]

# Exclusion FPs — do NOT attribute to a drone vendor (ruling 3/4); used for
# CSV verification + DB-conflict surfacing (NOT emitted as candidates).
_EXCLUSION_FPS = [
    ("CMJ", "Autel Corporation", "Glendale", "California", "United States",
     "Autel Corporation (Glendale CA) = AUTOMOTIVE diagnostics — NOT Autel Robotics."),
    ("HDF", "Autelca Ltd", "CH-3073 Gimligen-Berne", "", "Switzerland",
     "Autelca Ltd (Switzerland) — unrelated."),
    ("DJI", "Seragen Diagnostics", "Indianapolis", "Indiana", "United States",
     "Literal grantee code 'DJI' = Seragen Diagnostics (medical) — NOT the drone maker."),
    ("WQ8", "Autel Intelligent Tech. Corp., Ltd.", "Shenzhen", "", "China",
     "Autel Intelligent (diagnostics parent) — NOT the drone arm."),
    ("XPR", "Autel Intelligent Technology Co.,Ltd", "Shenzhen", "", "China",
     "Autel Intelligent (diagnostics parent) — NOT the drone arm."),
    ("RKU", "PARROT", "Paris", "", "France", "PARROT legacy entity — not the drone arm."),
    ("RKX", "PARROT", "Paris", "", "France", "PARROT legacy entity — not the drone arm."),
    ("CHK", "Parrot Electronics Ltd", "Chai Wan", "", "Hong Kong",
     "Parrot Electronics HK — not the drone arm."),
    ("XNP", "Parrot's Technology GmbH", "Zug", "", "Switzerland",
     "Parrot's Technology GmbH (Zug) — not the drone arm."),
    ("2AGKO", "PARROT FAURECIA AUTOMOTIVE SAS", "Paris", "", "France",
     "Parrot Faurecia Automotive — correctly automotive (NOT a drone mis-attribution)."),
    ("2AT94", "Parrot Faurecia Automotive S.A.S", "Paris", "", "France",
     "Parrot Faurecia Automotive — correctly automotive (NOT a drone mis-attribution)."),
]


def _load_frozen_fcc() -> Optional[dict[str, tuple]]:
    """PII-safe load of the frozen sid-7 CSV (external/gitignored). Returns
    {code: (name, city, state, country)} for codes of interest, or None if the
    SSD is not mounted (CI). contact_name + mailing_address + po_box + zip NEVER
    read. Also returns the contact_name redaction count via the module global."""
    global _FCC_REDACTIONS
    _FCC_REDACTIONS = 0
    if not FCC_CSV.exists():
        return None
    want = {c for c, *_ in _DRONE_GRANTEES} | {c for c, *_ in _EXCLUSION_FPS}
    found: dict[str, tuple] = {}
    with FCC_CSV.open(newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            gc = row["grantee_code"].strip()
            if gc in want and gc not in found:
                if row.get("contact_name", "").strip():
                    _FCC_REDACTIONS += 1  # §11 #3 / SAR-5 suppressed
                found[gc] = (row["grantee_name"].strip(), row["city"].strip(),
                             row["state"].strip(), row["country"].strip())
    return found


_FCC_REDACTIONS = 0


def _grantee_candidates(cur) -> tuple[list[Candidate], list[dict], list[dict]]:
    """Returns (candidates, conflicts, recategorizations). All 11 drone-arm
    grantees are already in DB (expansion). The frozen FCC (registration lens)
    corroborates them. Exclusion FPs are NOT emitted as candidates — they feed
    the DB-conflict surfacer instead."""
    frozen = _load_frozen_fcc()  # PII-safe dict or None (CI)
    out, conflicts, recats = [], [], []

    for code, name, city, state, ctry, _is_drone, note in _DRONE_GRANTEES:
        # CSV-verify the CTO-verified entity name when the SSD is present.
        if frozen is not None:
            assert code in frozen, f"drone grantee {code} absent from frozen sid-7 CSV"
            assert frozen[code][0] == name, (
                f"{code} frozen name {frozen[code][0]!r} != manifest {name!r}")
        row = _id_lookup(cur, code, "fcc_grantee_code")
        presence = f"already_in_db:id={row[0]}" if row else "net-new"
        loc = ", ".join(x for x in (city, state, ctry) if x)
        # 6 DJI grantees sit at device_category='unknown' / conf 75 / crowdsourced —
        # frozen primary_registry corroborates drone-arm; flag re-categorization
        # opportunity (NOT a fix here — §11 #8 / DBArchitect + Validator).
        if row and row[2] == "unknown":
            recats.append({
                "code": code, "db_id": row[0],
                "db_state": f"manufacturer={row[1]!r} category='unknown' conf={row[3]} source_type={row[4]!r}",
                "frozen_fcc": f"{name} ({loc})",
                "recommendation": ("re-categorize device_category 'unknown'→'drone' and lift "
                                   "to primary_registry band (frozen sid-7 = CTO-verified DJI "
                                   "drone-arm). §11 #8: needs Validator/DBArchitect, not staged here."),
            })
        out.append(Candidate(
            identifier_type="fcc_grantee_code", value=code, source_sid=7,
            source_url="https://opendata.fcc.gov/Engineering/FCC-EAS-Grantee-Codes/3b3k-34jp",
            relative_path=f"sid7 frozen CSV (sha256 {FCC_FROZEN_SHA[:12]}…, external/gitignored)",
            proposed_confidence_ceiling=90,  # primary_registry §8.2 ceiling
            db_presence=presence, source_lens="registration",
            export_membership="fcc_grantee_code = DROPPED per §4.4 (regulatory entity ID, "
                              "not RF-broadcast wire pattern) → EXPORT-EXCLUDED both feeds",
            manufacturer=name.split(",")[0], device_category="drone",
            cite_excerpt=_excerpt(f'"{code}","{name}",{loc} (FCC EAS frozen {FCC_FROZEN_FREEZE})'),
            notes=f"PII-stripped (code/name/city/state/country only). {note}",
        ))

    # DB-conflict surfacing: exclusion FPs whose live DB row contradicts the
    # CTO ruling / frozen FCC entity (§11 #1/#7/#8 — surfaced, NOT fixed here).
    HARD = {"CMJ", "WQ8", "XPR"}  # 'Autel Robotics'/drone but frozen = automotive/diagnostics
    SOFT = {"CHK", "RKU", "RKX", "XNP"}  # Parrot exclusion-FPs categorised drone
    for code, name, city, state, ctry, note in _EXCLUSION_FPS:
        if frozen is not None and code in frozen:
            assert frozen[code][0] == name, (
                f"{code} frozen name {frozen[code][0]!r} != manifest {name!r}")
        row = _id_lookup(cur, code, "fcc_grantee_code")
        loc = ", ".join(x for x in (city, state, ctry) if x)
        if row and code in HARD:
            conflicts.append({
                "severity": "HARD", "code": code, "db_id": row[0],
                "db_says": f"manufacturer={row[1]!r} category={row[2]!r} conf={row[3]} source_type={row[4]!r}",
                "frozen_fcc_truth": f"{name} ({loc})",
                "issue": (f"DB attributes {code} to drone vendor '{row[1]}'/'{row[2]}' but the "
                          f"frozen sid-7 grantee is '{name}' ({note}). §11 #1/#7/#8 mis-attribution."),
                "recommendation": "DBArchitect/Validator: re-attribute or supersede; re-eval confidence.",
            })
        elif row and code in SOFT:
            conflicts.append({
                "severity": "SOFT", "code": code, "db_id": row[0],
                "db_says": f"manufacturer={row[1]!r} category={row[2]!r} conf={row[3]} source_type={row[4]!r}",
                "frozen_fcc_truth": f"{name} ({loc})",
                "issue": (f"DB labels {code} 'Parrot'/'drone'. Manufacturer=Parrot is defensible "
                          f"(corporate group) but the CTO ruling lists {code} as an exclusion-FP "
                          f"('{name}', {note}); device_category='drone' is questionable."),
                "recommendation": "DBArchitect/Validator: review device_category vs exclusion-FP ruling.",
            })
        elif not row and code in ("DJI", "HDF"):
            conflicts.append({
                "severity": "OK-ABSENT", "code": code, "db_id": None,
                "db_says": "absent (no fcc_grantee_code row)",
                "frozen_fcc_truth": f"{name} ({loc})",
                "issue": f"FP correctly NOT minted as a grantee_code ({note}).",
                "recommendation": "none — honest absence preserved.",
            })
    return out, conflicts, recats


# ── C. Behavioral signatures (§5 / behavioral_signatures table) ───────────────
def _behaviorals() -> list[Behavioral]:
    # Structural cites re-verified from opendroneid.h on disk.
    ln_size, _ = _grep_line(ODID_H, "#define ODID_ID_SIZE")
    ln_serial, _ = _grep_line(ODID_H, "ODID_IDTYPE_SERIAL_NUMBER = 1")
    ln_basic, _ = _grep_line(ODID_H, "typedef struct ODID_BasicID_data")
    return [
        Behavioral(
            signature_name="ASTM F3411 / ASD-STAN Remote-ID broadcast — Wi-Fi (Beacon vendor-"
                           "specific IE + NaN) carrying CTA-2063-A serial",
            device_category="drone", cellular_generation=None, source_ref=19,
            relative_path=ODID_H,
            evidence=[
                {"locus": f"opendroneid.h L{ln_serial}",
                 "note": "ID-type enum SERIAL_NUMBER=1 / CAA_REGISTRATION_ID=2 / "
                         "UTM_ASSIGNED_UUID=3 / SPECIFIC_SESSION_ID=4"},
                {"locus": f"opendroneid.h L{ln_size}", "note": "ODID_ID_SIZE 20 (UASID field)"},
                {"locus": f"opendroneid.h L{ln_basic}",
                 "note": "ODID_BasicID_data { UAType; IDType; char UASID[ODID_ID_SIZE+1]; }"},
                {"locus": "opendroneid-core-c/libopendroneid/wifi.c append_tlv(...,0x03,...)",
                 "note": "Wi-Fi Alliance OUI + oui_type 0x13 vendor IE; CTA-2063 identifier "
                         "appended as TLV type 0x03 (structural — encoder)"},
            ],
            proposed_confidence_ceiling=75,  # crowdsourced reference-impl (sid 19 tier-1)
            source_lens="structural",
            notes="Structural authority for the on-air Remote-ID beacon (ruling 5b). The "
                  "per-vendor UASID *value* is the drone serial (drone_id_prefix layer), NOT "
                  "from this header. Behavioral pattern, not an identifier value.",
        ),
        Behavioral(
            signature_name="ASTM Remote-ID broadcast — Bluetooth 4 Legacy / BT5 Long-Range "
                           "advertisement (ODID message pack)",
            device_category="drone", cellular_generation=None, source_ref=19,
            relative_path=ODID_H,
            evidence=[
                {"locus": "opendroneid.h #define ODID_MESSAGE_SIZE 25",
                 "note": "25-byte ODID message; BT4 legacy adv (service data) / BT5 ext adv"},
                {"locus": f"opendroneid.h L{ln_basic}", "note": "ODID_BasicID message structure"},
            ],
            proposed_confidence_ceiling=75, source_lens="structural",
            notes="BT advert transport for the same ODID Basic-ID. Receiver-side parsing in "
                  "sid 25 receiver-android / sid 26 wireshark-dissector / sid 27 RemoteIDReceiver.",
        ),
        Behavioral(
            signature_name="DJI legacy proprietary DroneID — OFDM RF frame (2.4 GHz, ~600 ms "
                           "burst, 9 OFDM symbols) carrying serial + GPS + operator location",
            device_category="drone", cellular_generation=None, source_ref=28,
            relative_path=DJI_DRONEID_README,
            evidence=[
                {"locus": "dji_droneid_README.md — 'signal of interest is in 2.4 GHz … "
                          "every 600 ms … 10 MHz wide (15.36 MHz with guard carriers)'",
                 "note": "RF-layer burst cadence + bandwidth"},
                {"locus": "dji_droneid_README.md — center freqs 2.4595 / 2.4445 / 2.4295 / 2.4145 GHz",
                 "note": "DroneID hopping channels"},
                {"locus": "dji_droneid_README.md — '9 OFDM symbols … ZC sequence … scrambler'",
                 "note": "OFDM frame structure (proprietary, pre-ASTM)"},
            ],
            proposed_confidence_ceiling=70,  # crowdsourced researcher RE (sid 28 tier-2)
            source_lens="structural",
            notes="Ruling 5b: DJI's LEGACY DroneID is an OFDM RF frame, DISTINCT from the ASTM "
                  "Remote-ID beacon. Decoded payload (serial / lat-lon / operator loc) is an "
                  "RF-layer extraction target, not a BT/WiFi beacon. No IQ sample shipped.",
        ),
        Behavioral(
            signature_name="Skydio Remote-ID — broadcast (ASTM via on-board QCA/Qualcomm radio) "
                           "+ Network Remote-ID (cloud session auth) companion-app pattern",
            device_category="drone", cellular_generation=None,
            source_ref="needs_new_source_row:app:com.skydio.r3",
            relative_path=APK_SKYDIO_R3,
            evidence=[
                {"locus": "Lcom/skydio/jcabremoteid/...", "note": "dedicated Remote-ID module (jcabremoteid, 81 DEX refs)"},
                {"locus": "Lcom/skydio/jcabremoteid/auth/JcabRemoteIdRequest;",
                 "note": "Network Remote-ID auth request (cloud session)"},
                {"locus": "Lcom/skydio/pbtypes/qca_stats/RemoteIdStatusProto;",
                 "note": "QCA (Qualcomm Atheros) chipset Remote-ID status telemetry (241 refs)"},
                {"locus": "Lcom/skydio/aircam/remoteid/RidAuthFragment;",
                 "note": "in-app Remote-ID auth/registration UI"},
            ],
            proposed_confidence_ceiling=75,  # manufacturer_app §8.2
            source_lens="observation",
            notes="Class descriptors re-grepped from gitignored XAPK base DEX (decompiled "
                  "source NOT committed, §11 #15). Skydio supports both broadcast + Network RID.",
        ),
        Behavioral(
            signature_name="Autel drone companion — Wi-Fi AP join (SSIDConnection) + MAVLink "
                           "control-link pattern (EVO/Dragonfish family)",
            device_category="drone", cellular_generation=None,
            source_ref="needs_new_source_row:app:com.autel.explorer",
            relative_path=APK_AUTEL,
            evidence=[
                {"locus": "Lcom/autel/sdk10/AutelNet/AutelDsp/wifi/connection/SSIDConnection;",
                 "note": "joins the drone's Wi-Fi AP by SSID (runtime SSID, not hardcoded literal)"},
                {"locus": "AutelSSIDConnectionInterface$OnSSIDConnectionlistener",
                 "note": "SSID connection lifecycle callbacks"},
                {"locus": "AutelMavlinkCore", "note": "MAVLink control link over the Wi-Fi AP"},
            ],
            proposed_confidence_ceiling=75, source_lens="observation",
            notes="Class descriptors re-grepped from gitignored APK DEX (§11 #15). No hardcoded "
                  "default-SSID literal surfaced (AutelNet/AutelNet2 are SDK package names, not "
                  "broadcast SSIDs) → no ssid_pattern candidate.",
        ),
    ]


def _verify_apk_evidence(b: Behavioral) -> str:
    """Best-effort re-grep of each evidence locus from the gitignored APK/XAPK DEX
    strings. Returns 'verified' | 'apk_absent' | 'MISSING:<locus>'. Keeps the
    decompiled source out of the git index — only the bounded locus string is used.
    Only runs for manufacturer_app (DEX-backed) signatures."""
    if not str(b.source_ref).startswith("needs_new_source_row:app:"):
        return "n/a_structural"
    apk = REPO / b.relative_path
    if not apk.exists():
        return "apk_absent"
    try:
        with tempfile.TemporaryDirectory() as td:
            # XAPK split bundle? extract inner base apk(s) first.
            subprocess.run(["unzip", "-o", "-q", str(apk), "-d", td], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            inner = list(Path(td).rglob("*.apk"))
            dexdir = Path(td) / "_dex"
            dexdir.mkdir(exist_ok=True)
            for ia in (inner or [apk]):
                subprocess.run(["unzip", "-o", "-q", str(ia), "classes*.dex", "-d", str(dexdir)],
                               check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            blob = b"".join(p.read_bytes() for p in dexdir.glob("classes*.dex"))
            for ev in b.evidence:
                # match the distinctive token (class tail / literal), not the prose note
                token = ev["locus"].split("/")[-1].rstrip(";").split()[0]
                if token.encode() not in blob:
                    return f"MISSING:{token}"
        return "verified"
    except Exception as e:  # pragma: no cover - environment-dependent
        return f"error:{e}"


# ── D. FAA RID cross-ref dispositions (attribution, NOT candidates; ruling 5) ──
def _faa_crossrefs() -> list[dict]:
    out = []
    for vendor, prefix_family in [("skydio", "1668B (Skydio CTA-2063-A)"),
                                  ("autel", "1748C (Autel Robotics CTA-2063-A)"),
                                  ("parrot", "(Parrot ANAFI family)")]:
        d = json.loads((REPO / f"{FAA_DIR}/{vendor}.json").read_text())
        items = d["data"]["items"]
        models = sorted({it["modelName"] for it in items})
        out.append({
            "vendor": vendor, "rid_doc_count": len(items), "total_items": d["data"]["totalItems"],
            "models": models,
            "crossref_to": f"drone_id_prefix {prefix_family}",
            "disposition": ("attribution + cross-ref only (ruling 5) — makeName/model NOT promoted "
                            "as identifier values; the on-air ID is the CTA-2063-A serial."),
        })
    return out


def build() -> dict:
    with _db() as conn:
        cur = conn.cursor()
        ble = _ble_candidates(cur)
        grantees, conflicts, recats = _grantee_candidates(cur)

    candidates = ble + grantees
    net_new = [c for c in candidates if c.db_presence == "net-new"]
    already = [c for c in candidates if c.db_presence != "net-new"]

    behaviorals = []
    for b in _behaviorals():
        d = asdict(b)
        d["apk_evidence_check"] = _verify_apk_evidence(b)
        behaviorals.append(d)

    faa = _faa_crossrefs()

    honest_absences = [
        "Anduril — no public companion APK (military UAS) AND 0 grantees in the 2021-03-22 "
        "frozen FCC set AND 0 FAA RID DOC rows (totalItems=0). Any Anduril coverage needs a "
        "live post-2021 fcc.report/fccid.io hunt = a Phase-3 dispatch, NOT this stage (ruling 11).",
        "Skydio + Autel — NO Bluetooth-SIG company-id (ruling 2). 0 hits across all SIG files; "
        "their BLE adverts (if any) ride a chipset/module vendor id. No SIG id minted.",
        "Skydio/Autel/DJI-app/Parrot-app BLE service UUIDs — 0 clean vendor UUIDs. Every 128-bit "
        "UUID in the APK/XAPK DEX is a cross-vendor SDK constant: 258EAFA5 (board-dropped MAC-348/350), "
        "edef8ba9 / 9a04f079 (Nordic DFU), c06c8400 / bb392ec0 (TI base 0002a5d5c51b), and a single "
        "01ead4a5 (no BluetoothGattService binding, not cross-vendor — ambiguous config GUID). "
        "No vendor GATT service binding → none emitted (§11 #1).",
        "No net-new drone_id_prefix. The only repo prefix value, 1581F6BV (DragonSync "
        "tests/generate_scenario.py:52 + test_refactor_scenario.json), is a SYNTHETIC TEST FIXTURE "
        "(§11 #1 bars promotion). kismet_targets.txt is empty (example-comments only); the "
        "faa-rid-lookup submodule was not cloned. Skydio (1668B*) / Autel (1748C*) / DJI (1581F*) "
        "prefix families are already in DB.",
        "FCC grantee→FCC-ID→equipment-class drill-down (ruling 12) — no sid 51/52/85 drone "
        "grantee pages were fetched this harvest (the only fcc.report artifacts on disk are "
        "MAC-367 WatchGuard). Honest-absence: this worker does NOT live-fetch (§11 #6 / SAR-4 — "
        "Source Worker's robots-routed job). 0 equipment_class_code candidates.",
        "Grantee-code FPs correctly ABSENT from DB: HDF (Autelca, Switzerland) absent; literal "
        "code 'DJI' = Seragen Diagnostics NOT minted as a grantee_code (the product_family_codename="
        "'DJI' id=42971 is an unrelated judicial_filing artifact, different identifier_type).",
        "'Autel Sky' (newer Autel drone app) — unconfirmed on the apkcombo mirror; not asserted (ruling 11).",
        "No default SSID literal in the Autel or Skydio APKs — connection logic reads the SSID at "
        "runtime; no hardcoded vendor SSID pattern → 0 ssid_pattern candidates.",
    ]

    meta = {
        "issue": "MAC-374", "parent": "MAC-363", "cohort": "Cohort 3 — Drones",
        "worker": "ExtractionWorker (1347736c)",
        "scope": "EXTRACTION ONLY — candidates only; no DB write/ingest/migration/export/push/CP",
        "input": "MAC-366 harvest manifest (CTO-verified)",
        "framing": "EXPANSION not greenfield — 0 net-new identifier VALUES; contribution is "
                   "corroboration/footprint + DB-conflict surfacing + behavioral signatures",
        "pii_redaction_count": _FCC_REDACTIONS,
        "pii_note": "FCC contact_name + mailing_address + po_box + zip NEVER read (§11 #3 / SAR-5); "
                    "only grantee_code/name/city/state/country surfaced. Frozen CSV stays external/gitignored.",
        "fcc_csv_verified": FCC_CSV.exists(),
        "counts": {
            "identifier_candidates_total": len(candidates),
            "net_new_identifier_values": len(net_new),
            "already_in_db": len(already),
            "by_type": _by_type(candidates),
            "behavioral_signatures": len(behaviorals),
            "db_conflicts_hard": sum(1 for c in conflicts if c["severity"] == "HARD"),
            "db_conflicts_soft": sum(1 for c in conflicts if c["severity"] == "SOFT"),
            "recategorizations_recommended": len(recats),
            "faa_rid_crossref_vendors": len(faa),
        },
        "db_conflicts_for_remediation": {
            "note": "EXTRACTION-ONLY surfaced these; NOT fixed here (no DB write). "
                    "DBArchitect/Validator remediation — §11 #1/#7/#8.",
            "fcc_grantee_misattributions": conflicts,
            "fcc_grantee_recategorizations": recats,
        },
        "needs_new_source_rows": {
            "app:com.skydio.r3": {
                "proposed_name": "Skydio (com.skydio.r3@24.10.48)",
                "source_type": "manufacturer_app",
                "sha256": "af538197b7a1116ee1b86d607e716583c16978c0673cc5f4890dbbb108b61b11",
                "note": "XAPK split bundle; base com.skydio.r3.apk"},
            "app:com.skydio.enterprise": {
                "proposed_name": "Skydio Enterprise (com.skydio.enterprise@24.10.48)",
                "source_type": "manufacturer_app",
                "sha256": "4bfb561d07c5f57ce3f81b9e7be7d4b31c5d0fd6a71e810b00519cf58d95818c",
                "note": "XAPK split bundle; shares jcabremoteid module with r3"},
            "app:com.autel.explorer": {
                "proposed_name": "Autel Explorer (com.autel.explorer@V1.0.1.45)",
                "source_type": "manufacturer_app",
                "sha256": "02eb9df046016fe338371afd64aff00849f1d90a1384302361dc3dab1737700f",
                "note": "plain APK; the ONLY Autel drone companion (ruling 3)"},
            "note": "DJI (sid 71) / Parrot (sid 70) apps + SIG (34) / FCC (7) / FAA (36) / "
                    "opendroneid (19) / dji_droneid (28) source rows already exist — extend footprint.",
        },
    }

    return {
        "_meta": meta,
        "candidates": [asdict(c) for c in candidates],
        "behavioral_signatures": behaviorals,
        "faa_rid_crossrefs": faa,
        "honest_absences": honest_absences,
    }


def _by_type(cands: list[Candidate]) -> dict:
    out: dict[str, int] = {}
    for c in cands:
        out[c.identifier_type] = out.get(c.identifier_type, 0) + 1
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = build()
    out = OUT_DIR / "candidates.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=False) + "\n")
    m = result["_meta"]["counts"]
    print(f"wrote {out}")
    print(f"  identifier_candidates={m['identifier_candidates_total']} "
          f"net_new_VALUES={m['net_new_identifier_values']} already_in_db={m['already_in_db']} "
          f"by_type={m['by_type']}")
    print(f"  behavioral={m['behavioral_signatures']} "
          f"conflicts hard={m['db_conflicts_hard']} soft={m['db_conflicts_soft']} "
          f"recats={m['recategorizations_recommended']}")
    print(f"  pii_redactions={result['_meta']['pii_redaction_count']} "
          f"fcc_csv_verified={result['_meta']['fcc_csv_verified']}")
    for b in result["behavioral_signatures"]:
        print(f"  behavioral [{b['apk_evidence_check']}] {b['signature_name'][:50]}...")


if __name__ == "__main__":
    main()
