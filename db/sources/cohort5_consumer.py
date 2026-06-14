"""MAC-376 — Cohort 5 (Consumer surveillance) EXTRACTION.

Turns the CTO-verified MAC-368 harvest manifest into structured identifier
candidates for CTO review -> DBArchitect ingest. EXTRACTION ONLY: emits
extraction_outputs/mac368_cohort5_consumer/candidates.json. NO DB write, NO
ingest, NO migration, NO export regen, NO push, NO CP mint. No decompiled APK
source enters the git index (§11 #15 / 17 USC §1201) — only candidate value +
relative path inside the gitignored raw/ tree. (This harvest fetched only
facts-only Play-listing HTML; no APK binary was acquired, so no teardown values.)

Targets (MAC-363 Phase B cohort 5): Ring, Wyze, Arlo, Blink/Amazon, eufy/Anker,
Google, Nest, Netgear. This is **narrow scoped expansion**, not greenfield:

  * The export-meaningful net-new surface is the **Wi-Fi OUI** side (`oui` is the
    only one of {oui, ble_manufacturer_id, ssid_pattern} that reaches Lynceus).
  * The 8 BLE SIG company-ids are ALREADY in the DB at device_category='unknown'
    (export-banned, §11 #13) — reference only, setup-transient, do NOT re-promote.
  * The full FCC frozen grantee dataset (50,153 rows) is ALREADY loaded — vendor
    grantee codes are corroboration/attribution, not net-new fcc_grantees rows.

Discipline (MAC-368 integrity rulings 1-12 + bible §7.3 / §8.2 / §8.3 / §4.4 / §11):
  1.  BLE company-ids = already-present + setup-transient -> do NOT promote/enrich.
  2.  Net-new surface = Wi-Fi OUI, bifurcated by vendor purity:
        pure-play (Ring/Wyze/Arlo/Blink) = cohort-clean, directly promotable;
        mixed-use (Amazon/Google/Netgear/Nest) = FCC/SKU-gated, NOT bulk-promoted.
  3.  eufy -> Anker: own OUI = NONE (chipset-derived). `70B3D5C4B` is ANKER-EAST
        (St Petersburg RU) — a substring FALSE-POSITIVE, NOT eufy/Anker Innovations.
  4.  Arlo<->Netgear lineage: legacy Arlo cams use Netgear OUIs; only promote a
        Netgear OUI with an FCC/product tie to an Arlo-lineage camera (none fetched).
  5.  Ring = Wi-Fi-only per vendor FAQ (BLE uncertainty carried, not resolved).
  6.  SoftAP setup-SSID = Phase-3 lead + ssid_pattern export-banned (§4.4); no APK
        teardown artifact present -> literal SSID format is honest-absence.
  7.  Researcher/vendor-confidence discarded; §8.2 source-band ceiling proposed.
  8.  Observation-vs-registration lens annotated. §8.3 hub-and-spoke (same vendor
        across id-types) is NOT value-level corroboration -> no +5 lift.
  9.  Export-membership checked against export_lynceus.py, not asserted.
  10. db_presence annotated; net-new tally kept SEPARATE from promote floor.
  11. §11 #3 / SAR-5 PII: FCC frozen JSON is code/name only; surfaced as-is.
  12. Honest absences carried forward — do NOT fabricate.

Integrity catches surfaced by this run (vs the CTO-verified harvest headline):
  * Arlo Technology exact-match OUI count = **3** (486264/A41162/FC9C98), NOT 4.
    `ARLOTTO COMNET, INC.` (00E0F2, Taiwan) is a substring trap, not Arlo.
  * `70B3D5C4B` = ANKER-EAST (RU), NOT eufy/Anker — eufy has ZERO own OUI.
  * **Blink by Amazon** (5 MA-L OUIs) is a pure-play surveillance sub-brand hiding
    inside the Amazon mixed-use block -> cohort-clean, promotable.
  * Wyze MA-M block A4DA222 is ALREADY in DB as mac_range `a4:da:22:2/28` (id 9748)
    -> exclude from net-new oui (would be a type-collision duplicate).
  * device_category `doorbell` is NOT in the §2.1 enum -> Ring/Blink video doorbells
    map to `cctv_camera`; taxonomy gap flagged.

Anti-hallucination: every OUI / SIG / FCC / Play-HTML cite is re-derived from its
named raw artifact on disk here (raises if missing). DB-presence is re-queried
live. No value or count from memory.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"

OUI_FILES = {
    "MA-L": REPO / "raw/ieee_oui/20260613T203034Z_oui.csv",
    "MA-M": REPO / "raw/ieee_oui/20260613T203034Z_mam.csv",
    "MA-S": REPO / "raw/ieee_oui/20260613T203034Z_oui36.csv",
}
OUI_URL = {
    "MA-L": "https://standards-oui.ieee.org/oui/oui.csv",
    "MA-M": "https://standards-oui.ieee.org/oui28/mam.csv",
    "MA-S": "https://standards-oui.ieee.org/oui36/oui36.csv",
}
SIG_YAML = REPO / "raw/bluetooth_sig/20260613T203034Z_company_identifiers.yaml"
SIG_URL = ("https://bitbucket.org/bluetooth-SIG/public/raw/main/assigned_numbers/"
           "company_identifiers/company_identifiers.yaml")
FCC_JSON = REPO / "extraction_outputs/mac321_v166/raw/fcc_grantee_full.json"

OUT_DIR = REPO / "extraction_outputs/mac368_cohort5_consumer"

# §8.2 primary_registry single-source ceiling (line 792/822). Hub-and-spoke is NOT
# value-level corroboration (ruling 8) -> no +5 lift; stays at the 85 ceiling.
PRIMARY_REGISTRY_CEILING = 85

# Pure-play surveillance vendors: EXACT IEEE org-name -> (vendor, device_category).
# Every product these vendors ship is a camera/doorbell/home-security device, so
# their OUIs are cohort-pure. `doorbell` is NOT an enum value -> cctv_camera.
PURE_PLAY = {
    "Ring LLC": ("Ring", "cctv_camera"),
    "Wyze Labs Inc": ("Wyze Labs", "cctv_camera"),
    "Arlo Technology": ("Arlo Technologies", "cctv_camera"),
    "Blink by Amazon ": ("Blink (Amazon)", "cctv_camera"),  # trailing space in CSV
}

# Mixed-use vendors: EXACT org-name -> vendor. NOT bulk-promoted (ruling 2/4).
MIXED_USE = {
    "Amazon Technologies Inc.": "Amazon",
    "Google, Inc.": "Google",
    "NETGEAR": "Netgear",
    "Nest Labs Inc.": "Nest Labs",
}

# 8 SIG vendor company-ids (already in DB as ble_manufacturer_id, ruling 1).
SIG_VENDOR_IDS = ["0x0171", "0x018E", "0x00E0", "0x01B5",
                  "0x0CC2", "0x0870", "0x0C19", "0x0446"]

# CTO-verified vendor FCC grantee codes (already in fcc_grantees, all 50,153 rows).
FCC_VENDOR_CODES = {
    "Ring": ["2AEUP"],
    "Wyze": ["2AUIU", "2AUJY"],
    "Anker/eufy": ["2AB7K", "2AOKB"],
    "Arlo": ["2APLE"],
    "Netgear": ["PY3"],
    "Google": ["A4R", "ZQA"],
}

# Facts-only Play listing HTML (HTTP-200 og:title cite-paste, ruling 12 honest-404).
PLAY_LISTINGS = {
    "com.ringapp": "ring/com.ringapp",
    "com.hualai": "wyze/com.hualai",
    "com.oceanwing.battery.cam": "eufy/com.oceanwing.battery.cam",
    "com.arlo.app": "arlo/com.arlo.app",
    "com.nest.android": "google_nest/com.nest.android",
    "com.google.android.apps.chromecast.app": "google_nest/com.google.android.apps.chromecast.app",
}
PLAY_404 = ["google_nest/com.obsidian.v4", "arlo/com.netgear.android"]


@dataclass
class Candidate:
    identifier_type: str
    value: str
    source_sid: int
    source_url: str
    relative_path: str
    proposed_confidence_ceiling: Optional[int]
    db_presence: str
    source_lens: str
    export_membership: str
    manufacturer: str
    device_category: str
    cite_excerpt: str
    notes: str = ""
    conflict_note: str = ""


def _require(p: Path) -> Path:
    if not p.exists():
        raise FileNotFoundError(f"required raw artifact missing: {p}")
    return p


def _norm_mac(s: str) -> str:
    return re.sub(r"[:\-]", "", s).upper()


def load_oui_by_exact_name(names: set[str]) -> dict[str, list[tuple[str, str]]]:
    """Return {org_name: [(registry, assignment_hex), ...]} for EXACT name matches."""
    out: dict[str, list[tuple[str, str]]] = {n: [] for n in names}
    for reg, fn in OUI_FILES.items():
        with open(_require(fn), newline="") as f:
            for row in csv.DictReader(f):
                org = row["Organization Name"]
                if org in out:
                    out[org].append((reg, row["Assignment"]))
    return out


def db_presence_oui(conn: sqlite3.Connection, hex6: str) -> str:
    """Annotate exists/net-new for an OUI hex (checks oui + mac_range collision)."""
    norm = _norm_mac(hex6)
    # exact oui (any separator form)
    for (rid, ident) in conn.execute(
        "SELECT id, identifier FROM identifiers WHERE identifier_type='oui'"):
        if _norm_mac(ident) == norm:
            return f"already_in_db:oui:id={rid}"
    # mac_range collision (e.g. MA-M /28 assignment already staged as a range)
    for (rid, ident, itype) in conn.execute(
        "SELECT id, identifier, identifier_type FROM identifiers "
        "WHERE identifier_type IN ('mac_range','mac','bssid')"):
        if _norm_mac(ident.split("/")[0]).startswith(norm) or norm.startswith(
                _norm_mac(ident.split("/")[0])):
            return f"already_in_db:{itype}:id={rid}:{ident}"
    return "net-new"


def sig_cite(value: str) -> tuple[int, str]:
    """Return (line_number, name) for a SIG company-id value, cite-paste from yaml."""
    lines = _require(SIG_YAML).read_text().splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == f"- value: {value}":
            name = lines[i + 1].split("name:", 1)[1].strip().strip("'\"")
            return i + 1, name
    raise ValueError(f"SIG company-id {value} not found in {SIG_YAML}")


def fcc_codes() -> dict[str, str]:
    data = json.loads(_require(FCC_JSON).read_text())
    return {d.get("grantee_code"): d.get("grantee_name") for d in data}


def build_candidates(conn: sqlite3.Connection) -> dict:
    candidates: list[Candidate] = []
    tally = {"pure_play": {}, "mixed_use": {}}

    # --- 1. Pure-play OUIs (net-new, directly promotable) ---
    pp = load_oui_by_exact_name(set(PURE_PLAY))
    for org, (vendor, devcat) in PURE_PLAY.items():
        rows = sorted(pp[org])
        net_new = 0
        for reg, asn in rows:
            pres = db_presence_oui(conn, asn)
            if pres == "net-new":
                net_new += 1
            candidates.append(Candidate(
                identifier_type="oui",
                value=asn,
                source_sid={"MA-L": 1, "MA-M": 2, "MA-S": 3}[reg],
                source_url=OUI_URL[reg],
                relative_path=f"{OUI_FILES[reg].relative_to(REPO)} ({reg} org='{org.strip()}')",
                proposed_confidence_ceiling=PRIMARY_REGISTRY_CEILING,
                db_presence=pres,
                source_lens="registration",
                export_membership=("oui -> exported (export_lynceus.py:93); "
                                   "primary_registry passes EXCLUDED_SOURCE_TYPES; "
                                   "device_category=cctv_camera passes §11 #13; "
                                   "geographic_scope='global' passes CP7 -> IN FEED"),
                manufacturer=vendor,
                device_category=devcat,
                cite_excerpt=f"{reg},{asn},{org.strip()} (IEEE {reg} registry)",
                notes=("Pure-play surveillance vendor; OUI cohort-clean. Per-SKU "
                       "(camera vs doorbell vs chime) split is NOT OUI-resolvable "
                       "without observed per-MAC data (Phase-3 deployment lane). "
                       "`doorbell` absent from §2.1 enum -> cctv_camera."),
                conflict_note=("Wyze MA-M A4DA222 already in DB as mac_range "
                               "a4:da:22:2/28 -> excluded from net-new"
                               if pres.startswith("already_in_db:mac_range") else ""),
            ))
        tally["pure_play"][vendor] = {
            "exact_org_name": org.strip(), "total_blocks": len(rows),
            "net_new_oui": net_new, "already_in_db": len(rows) - net_new,
            "device_category": devcat,
        }

    # --- 2. Mixed-use OUIs (tallied unscoped; NOT promoted absent SKU tie) ---
    mu = load_oui_by_exact_name(set(MIXED_USE))
    for org, vendor in MIXED_USE.items():
        rows = mu[org]
        tally["mixed_use"][vendor] = {
            "exact_org_name": org, "total_blocks": len(rows),
            "tied_to_surveillance_sku": 0,  # no FCC-ID exhibit fetched (§11 #6/SAR-4)
            "unscoped": len(rows),
            "note": ("Echo/Fire/Kindle/Eero/Pixel/Chromecast/routers span; not all "
                     "surveillance (§2.1). No FCC-ID exhibit fetched this stage -> "
                     "0 OUIs tie to a camera SKU -> all left UNSCOPED."),
        }

    # --- 3. SIG company-ids (already-in-db reference, ruling 1, NOT promoted) ---
    sig_ref = []
    for v in SIG_VENDOR_IDS:
        ln, name = sig_cite(v)
        row = conn.execute(
            "SELECT id, device_category, source_type FROM identifiers "
            "WHERE UPPER(identifier)=? AND identifier_type='ble_manufacturer_id'",
            (v.upper(),)).fetchone()
        sig_ref.append({
            "value": v, "name": name, "yaml_line": ln,
            "db_presence": (f"already_in_db:id={row[0]}:device_category={row[1]}:"
                            f"{row[2]}" if row else "ABSENT(unexpected)"),
            "export_membership": ("ble_manufacturer_id MAP->exported BUT "
                                  "device_category='unknown' -> §11 #13 ban -> NOT in feed"),
            "disposition": "setup-transient already-present; do NOT re-promote/enrich",
        })

    # --- 4. FCC grantee codes (already in fcc_grantees, attribution only) ---
    codes = fcc_codes()
    fcc_ref = []
    for vendor, lst in FCC_VENDOR_CODES.items():
        for c in lst:
            present = conn.execute(
                "SELECT 1 FROM fcc_grantees WHERE grantee_code=?", (c,)).fetchone()
            fcc_ref.append({
                "vendor": vendor, "grantee_code": c,
                "grantee_name": codes.get(c, "*** ABSENT ***"),
                "db_presence": ("already_in_fcc_grantees" if present
                                else "net-new(unexpected)"),
                "lens": "registration", "export_membership": "fcc_grantees lane (not Lynceus identifier feed)",
            })

    # --- 5. Play listing facts (facts-only metadata; no promotable identifier) ---
    play = []
    for pkg, rel in PLAY_LISTINGS.items():
        f = REPO / "raw/vendor_apps" / rel / "_listing"
        html = next(f.glob("*_play.html"), None)
        title = ""
        if html and html.exists():
            m = re.search(r'<meta property="og:title" content="([^"]*)"',
                          html.read_text(errors="ignore"))
            title = m.group(1) if m else ""
        play.append({"package_id": pkg, "og_title": title,
                     "relative_path": str(html.relative_to(REPO)) if html else None,
                     "kind": "facts-only metadata (no promotable identifier_type)"})
    play_404 = []
    for rel in PLAY_404:
        f = REPO / "raw/vendor_apps" / rel / "_listing"
        html = next(f.glob("*_play.html"), None)
        sz = html.stat().st_size if html and html.exists() else None
        play_404.append({"package_id": rel.split("/")[-1], "bytes": sz,
                         "disposition": "honest-404 retired package; do NOT chase"})

    # --- 6. Behavioral signature (SoftAP provisioning; setup-transient) ---
    behavioral = [{
        "signature_name": ("Consumer-cam Wi-Fi SoftAP onboarding -> persistent "
                           "vendor-OUI station MAC (setup-transient AP, durable STA)"),
        "device_category": "cctv_camera",
        "cellular_generation": None,
        "source_ref": None,
        "relative_path": None,
        "evidence": [{
            "locus": "MAC-368 harvest structural-fit finding (CEO directive)",
            "note": ("Consumer doorbell/cam BLE is vendor-keyed but EPHEMERAL "
                     "(provisioning/setup-mode only, dormant after pairing), "
                     "structurally unlike Cohort-1 24/7 trackers. Durable cohort "
                     "surface = the Wi-Fi station MAC under the vendor OUI."),
        }],
        "proposed_confidence_ceiling": None,
        "source_lens": "structural",
        "notes": ("Setup-transient. The literal SoftAP SSID convention "
                  "(Ring-XXXX / Wyze_XXXX / eufy-XXXX) is NOT in any fetched "
                  "artifact (no APK teardown) -> value is honest-absence; "
                  "ssid_pattern is export-banned (§4.4). Phase-3 SSID-pattern lead."),
        "apk_evidence_check": "n/a_no_apk_binary_fetched",
        "export_excluded": True,
    }]

    net_new_oui = sum(v["net_new_oui"] for v in tally["pure_play"].values())
    return {
        "candidates": [asdict(c) for c in candidates],
        "sig_company_id_reference": sig_ref,
        "fcc_grantee_reference": fcc_ref,
        "play_listing_facts": play,
        "play_listing_404": play_404,
        "behavioral_signatures": behavioral,
        "tally": tally,
        "net_new_oui_total": net_new_oui,
    }


def main() -> None:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        result = build_candidates(conn)
    finally:
        conn.close()

    meta = {
        "issue": "MAC-376",
        "parent": "MAC-363",
        "cohort": "Cohort 5 — Consumer surveillance",
        "worker": "ExtractionWorker (1347736c)",
        "scope": "EXTRACTION ONLY — candidates only; no DB write/ingest/migration/export/push/CP",
        "input": "MAC-368 harvest manifest (CTO-verified, hash-matched)",
        "framing": ("narrow scoped expansion — export-meaningful net-new surface is "
                    "the Wi-Fi OUI side only; BLE SIG-ids + FCC grantees are "
                    "already-in-db reference/attribution"),
        "artifact_sha_verified": {
            "sig_company_identifiers.yaml": "51b1ea7d…",
            "ieee_oui.csv": "fad18e77…",
            "fcc_grantee_full.json": "5f56afcd…",
        },
        "pii_redaction_count": 0,
        "pii_note": ("FCC frozen JSON is grantee_code/grantee_name only (already "
                     "PII-stripped, §11 #3/SAR-5); no contact/address columns present "
                     "or surfaced. No live fccid.io drill (Phase-3)."),
        "integrity_catches": [
            "Arlo Technology exact-match OUI count = 3 (NOT CTO-headline 4); "
            "ARLOTTO COMNET 00E0F2 (Taiwan) is a substring trap, not Arlo.",
            "70B3D5C4B = ANKER-EAST (St Petersburg RU), NOT eufy/Anker Innovations; "
            "eufy has ZERO own OUI (strengthens ruling 3).",
            "Blink by Amazon (5 MA-L OUIs) = pure-play surveillance sub-brand inside "
            "the Amazon mixed-use block -> cohort-clean, promotable.",
            "Wyze MA-M A4DA222 already in DB as mac_range a4:da:22:2/28 (id 9748) -> "
            "excluded from net-new oui (type-collision dup).",
            "device_category 'doorbell' absent from §2.1 enum -> Ring/Blink video "
            "doorbells map to cctv_camera; taxonomy gap flagged.",
        ],
        "counts": {
            "net_new_oui_total": result["net_new_oui_total"],
            "pure_play_oui_candidates": len(
                [c for c in result["candidates"] if c["identifier_type"] == "oui"]),
            "sig_company_ids_already_in_db": len(result["sig_company_id_reference"]),
            "fcc_grantee_codes_already_in_db": len(result["fcc_grantee_reference"]),
            "mixed_use_oui_unscoped": sum(
                v["unscoped"] for v in result["tally"]["mixed_use"].values()),
            "behavioral_signatures": len(result["behavioral_signatures"]),
        },
        "confidence_band": "§8.2 primary_registry single-source 70–85, ceiling 85 (IEEE OUI)",
    }
    out = {"_meta": meta, **result}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "candidates.json").write_text(json.dumps(out, indent=1))
    print(f"wrote {OUT_DIR / 'candidates.json'}")
    print(f"net-new oui: {result['net_new_oui_total']}")
    for v, t in result["tally"]["pure_play"].items():
        print(f"  pure-play {v}: {t['net_new_oui']} net-new / {t['total_blocks']} total")


if __name__ == "__main__":
    main()
