#!/usr/bin/env python3
"""MAC-178 Priority 5 — documented_absence entries.

Applies the wave's 22 documented_absence findings as
`manufacturers.notes.documented_absence[]` entries per brief §1.3 + §2
Priority 5 shape:

  {
    "investigation_date_utc": ...,
    "investigation_dispatch_ref": MAC-104 / 104b / 104c / 104d,
    "channel_probed": "google_play_store" / "apk-pure" / "huawei-app-gallery",
    "outcome": "categorical_absent",
    "rationale": "LE_only_distribution / vendor_direct_NDA / federal_enterprise_managed / controlled_distribution"
  }

10 NEW manufacturer stubs admitted for absences-only-known vendors
(Verkada / Honeywell / Lenel / BluePoint Alert / PIPS Technology /
Wolfcom / Utility Inc / Coban Technologies / Digital Ally / Aerodome).
Each carries `notes.admission_basis = 'documented_absence_only'` so the
admission posture is transparent to CEO post-hoc ratification.

Reveal Media → existing Reveal (id=16): alias-backfill (CEO surface).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
STAGING = REPO / "extraction_outputs" / "wave_g_v2_admission"


# Vendor name normalization for matching against `manufacturers.canonical_name`.
# Map staging-JSON `vendor_canonical` → DB canonical name.
VENDOR_NORMALIZATION = {
    "Honeywell Pro-Watch": "Honeywell",
    "Lenel OnGuard": "Lenel",
    "PIPS Technology / Neology": "PIPS Technology",
    "Reveal Media": "Reveal",  # alias-backfill on existing Reveal (id=16)
    "WatchGuard Video (legacy)": "WatchGuard",
    "Coban Technologies": "Coban Technologies",
    "Utility BodyWorn": "Utility Inc",
}

# NEW manufacturer stubs admitted for documented_absence-only vendors.
NEW_STUB_ANCHORS = {
    "Verkada": {
        "primary_category": None,
        "aliases": "Verkada Command, Verkada Inc",
        "source_url": "https://apkpure.com/p/com.verkada.command",
        "admission_dispatch_ref": "MAC-104",
    },
    "Honeywell": {
        "primary_category": None,
        "aliases": "Honeywell Pro-Watch, Honeywell International, Honeywell Building Technologies",
        "source_url": "https://apkpure.com/p/com.honeywell.prowatch.mobile",
        "admission_dispatch_ref": "MAC-104b",
    },
    "Lenel": {
        "primary_category": None,
        "aliases": "Lenel OnGuard, LenelS2, Lenel-Carrier, LenelS2 (Honeywell-Carrier)",
        "source_url": "https://apkpure.com/p/com.lenel.onguardmobile",
        "admission_dispatch_ref": "MAC-104b",
    },
    "BluePoint Alert": {
        "primary_category": None,
        "aliases": "BluePoint Alert Solutions",
        "source_url": "https://apkpure.com/p/com.bluepointalert",
        "admission_dispatch_ref": "MAC-104b",
    },
    "PIPS Technology": {
        "primary_category": "alpr",
        "aliases": "PIPS Technology / Neology, Neology, AutoVu (legacy), 3M (legacy)",
        "source_url": "https://apkpure.com/p/com.pipstechnology.allgomobile",
        "admission_dispatch_ref": "MAC-104c",
    },
    "Wolfcom": {
        "primary_category": "body_cam",
        "aliases": "Wolfcom Enterprises",
        "source_url": "https://apkpure.com/p/com.wolfcom.companion",
        "admission_dispatch_ref": "MAC-104c",
    },
    "Utility Inc": {
        "primary_category": "body_cam",
        "aliases": "Utility BodyWorn, Utility Inc Body-Worn",
        "source_url": "https://apkpure.com/p/com.utility.bodyworn.mobile",
        "admission_dispatch_ref": "MAC-104c",
    },
    "Coban Technologies": {
        "primary_category": "body_cam",
        "aliases": "Coban Tech",
        "source_url": "https://apkpure.com/p/com.coban.tech.companion",
        "admission_dispatch_ref": "MAC-104c",
    },
    "Digital Ally": {
        "primary_category": "body_cam",
        "aliases": "Digital Ally Inc, FleetVU, BodyVU",
        "source_url": "https://apkpure.com/p/com.digitalallymobile.fleetmobile",
        "admission_dispatch_ref": "MAC-104c",
    },
    "Aerodome": {
        "primary_category": "drone",
        "aliases": "Aerodome DFR",
        "source_url": "https://apkpure.com/p/com.aerodome.responder",
        "admission_dispatch_ref": "MAC-104d",
    },
}


def parse_existing_notes(notes_text: str | None) -> dict:
    if not notes_text:
        return {}
    try:
        obj = json.loads(notes_text)
        if isinstance(obj, dict):
            return obj
        return {"description": obj}
    except (json.JSONDecodeError, ValueError):
        return {"description": notes_text}


def normalize_absences() -> list[dict]:
    """Return a flat list of {db_canonical, staging_canonical, packages, dispatch_ref, channels, rationale, recommended_followup}."""
    out: list[dict] = []
    # 104 + 104b file (list shape)
    a1 = json.loads((STAGING / "documented_absences.json").read_text())
    # 104c file (dict with 'absences' list)
    a2 = json.loads((STAGING / "documented_absences_104c.json").read_text())["absences"]
    # 104d file (list shape)
    a3 = json.loads((STAGING / "documented_absences_104d.json").read_text())

    def normalize_one(e: dict, file_dispatch: str) -> dict:
        staging_canon = e.get("vendor_canonical")
        db_canon = VENDOR_NORMALIZATION.get(staging_canon, staging_canon)
        pkg = e.get("package_name")
        if pkg:
            packages = [pkg] if isinstance(pkg, str) else list(pkg)
        else:
            packages = [p.get("package") for p in e.get("packages_probed", []) if p.get("package")]
        channels = list((e.get("probed_channels") or {}).keys()) if e.get("probed_channels") else ["apk-pure", "apk-mirror"]
        # Decide effective dispatch — file is the default
        dispatch = e.get("dispatch_ref") or file_dispatch
        return {
            "db_canonical": db_canon,
            "staging_canonical": staging_canon,
            "packages_probed": packages,
            "channels_probed": channels,
            "investigation_dispatch_ref": dispatch,
            "rationale_prose": e.get("rationale", ""),
            "recommended_followup": e.get("recommended_followup", ""),
        }

    for e in a1:
        # The mixed file has both 104 (Verkada/Dahua) and 104b entries; tag
        # by vendor (Verkada/Dahua are 104; everything else is 104b).
        staging = e.get("vendor_canonical", "")
        file_dispatch = "MAC-104" if staging in {"Verkada", "Dahua"} else "MAC-104b"
        out.append(normalize_one(e, file_dispatch))
    for e in a2:
        out.append(normalize_one(e, "MAC-104c"))
    for e in a3:
        out.append(normalize_one(e, "MAC-104d"))
    return out


def map_rationale(prose: str, recommended_followup: str = "") -> str:
    """Map free-text rationale to one of the brief's canonical buckets."""
    p = (prose + " " + recommended_followup).lower()
    if "itar" in p or "c-uas" in p or "controlled" in p or "arms-export" in p:
        return "controlled_distribution"
    if "le-only" in p or "le only" in p or "law enforcement only" in p or "agency portal" in p or "vendor-direct" in p and "le" in p:
        return "LE_only_distribution"
    if "nda" in p or "private mdm" in p:
        return "vendor_direct_NDA"
    if "enterprise" in p or "managed-distribution" in p or "managed distribution" in p:
        return "federal_enterprise_managed"
    if "retired" in p or "deprecated" in p or "legacy" in p:
        return "vendor_direct_NDA"  # default for retired apps
    return "federal_enterprise_managed"


def main() -> int:
    print(f"DB: {DB}")
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    absences = normalize_absences()
    print(f"\nabsences parsed: {len(absences)}")

    try:
        db.execute("BEGIN")

        # Phase A: admit stub manufacturers
        admitted_stubs = []
        for m_name in NEW_STUB_ANCHORS:
            existing = db.execute(
                "SELECT id FROM manufacturers WHERE canonical_name=?", (m_name,)
            ).fetchone()
            if existing:
                continue
            anchor = NEW_STUB_ANCHORS[m_name]
            notes_obj = {
                "description": (
                    f"Stub admission for documented-absence intelligence "
                    f"({anchor['admission_dispatch_ref']}). Vendor identity confirmed "
                    "via public probing; no positive identifier extraction this wave."
                ),
                "admission_basis": "documented_absence_only",
                "admission_dispatch_ref": anchor["admission_dispatch_ref"],
                "admission_integration_ref": "MAC-178",
                "admission_date_utc": "2026-05-18T15:00:00Z",
            }
            db.execute(
                "INSERT INTO manufacturers (canonical_name, primary_category, source_url, aliases, notes) VALUES (?, ?, ?, ?, ?)",
                (
                    m_name,
                    anchor["primary_category"],
                    anchor["source_url"],
                    anchor.get("aliases"),
                    json.dumps(notes_obj, ensure_ascii=False, sort_keys=True),
                ),
            )
            new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            admitted_stubs.append({"id": new_id, "name": m_name, "category": anchor["primary_category"]})
            print(f"  STUB INSERTED: [{new_id}] {m_name} (primary_category={anchor['primary_category']})")

        # Phase B: alias backfill for renamed-vendor matches
        alias_backfills = []
        # Reveal Media → Reveal (id=16)
        for staging_canon, db_canon in VENDOR_NORMALIZATION.items():
            if staging_canon == db_canon:
                continue  # same canonical; no rename
            row = db.execute(
                "SELECT id, canonical_name, aliases FROM manufacturers WHERE canonical_name=?",
                (db_canon,),
            ).fetchone()
            if not row:
                continue
            existing_aliases = row["aliases"] or ""
            if staging_canon in existing_aliases:
                continue
            new_aliases = (
                f"{existing_aliases}, {staging_canon}".strip(", ")
                if existing_aliases
                else staging_canon
            )
            db.execute(
                "UPDATE manufacturers SET aliases=? WHERE id=?", (new_aliases, row["id"])
            )
            alias_backfills.append({
                "manufacturer_id": row["id"],
                "canonical_name": row["canonical_name"],
                "alias_added": staging_canon,
            })
            print(f"  ALIAS BACKFILL: [{row['id']}] {row['canonical_name']} += {staging_canon!r}")

        # Phase C: apply documented_absence entries
        print("\n=== applying documented_absence entries ===")
        appended = 0
        skipped_already_present = 0
        for ab in absences:
            row = db.execute(
                "SELECT id, canonical_name, notes FROM manufacturers WHERE canonical_name=?",
                (ab["db_canonical"],),
            ).fetchone()
            if not row:
                print(f"  WARN: manufacturer {ab['db_canonical']!r} not found — staging entry skipped")
                continue
            notes_obj = parse_existing_notes(row["notes"])
            existing_absences = notes_obj.get("documented_absence") or []
            # Dedup-key: (investigation_dispatch_ref, primary_package)
            primary_pkg = ab["packages_probed"][0] if ab["packages_probed"] else None
            key = (ab["investigation_dispatch_ref"], primary_pkg)
            existing_keys = {
                (e.get("investigation_dispatch_ref"), (e.get("packages_probed") or [None])[0])
                for e in existing_absences
            }
            if key in existing_keys:
                skipped_already_present += 1
                continue
            entry = {
                "investigation_date_utc": "2026-05-17",
                "investigation_dispatch_ref": ab["investigation_dispatch_ref"],
                "integration_dispatch_ref": "MAC-178",
                "channels_probed": ab["channels_probed"] or ["apk-pure", "apk-mirror"],
                "outcome": "categorical_absent",
                "packages_probed": ab["packages_probed"],
                "rationale": map_rationale(ab["rationale_prose"], ab["recommended_followup"]),
                "rationale_prose": ab["rationale_prose"][:500],
                "recommended_followup": ab["recommended_followup"][:300] if ab["recommended_followup"] else None,
                "staging_vendor_canonical": ab["staging_canonical"],
            }
            existing_absences.append(entry)
            notes_obj["documented_absence"] = existing_absences
            db.execute(
                "UPDATE manufacturers SET notes=? WHERE id=?",
                (json.dumps(notes_obj, ensure_ascii=False, sort_keys=True), row["id"]),
            )
            appended += 1
            print(f"  {row['canonical_name']:<25} [{row['id']:>3}] += {ab['investigation_dispatch_ref']} → pkg={primary_pkg}, rationale={entry['rationale']}")

        db.commit()
        print("\nCOMMIT.")

        print("\n=== Priority 5 verification ===")
        print(f"manufacturer stubs admitted (documented_absence_only): {len(admitted_stubs)}")
        print(f"alias backfills: {len(alias_backfills)}")
        print(f"documented_absence entries appended: {appended}")
        print(f"documented_absence entries skipped (already present): {skipped_already_present}")
        print(
            "manufacturers count now:",
            db.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0],
        )
        print(
            "manufacturers with documented_absence:",
            db.execute(
                "SELECT COUNT(*) FROM manufacturers WHERE notes LIKE '%documented_absence%'"
            ).fetchone()[0],
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
