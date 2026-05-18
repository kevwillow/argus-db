#!/usr/bin/env python3
"""MAC-178 Priority 4 — manufacturers product_family_taxonomy enrichments.

Applies the MAC-104 + 104b + 104d wave's ~917 upstream-mention product-family
observations as `manufacturers.notes.product_family_taxonomy[]` ADDITIVE
updates. Source-level dedup yields ~34 unique taxonomy strings across the 9
processed vendor apps.

Per CEO §3 #4: verify Hikvision + Dahua manufacturer rows. INSERT if absent
per existing manufacturer-admission convention. If present with different
canonical name → HALT for alias resolution (none observed; both absent).

Sibling new admissions: Autel Robotics + Cisco Meraki (same convention; not
explicit in §3 #4 but applies under the same rule "INSERT per existing
manufacturer-admission convention").

Idempotent: re-running adds zero new taxonomy entries (by value+source_apk_sha256).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
STAGING = REPO / "extraction_outputs" / "wave_g_v2_admission" / "per_vendor"


# Vendor-key → manufacturer canonical mapping
VENDOR_TO_MANUFACTURER = {
    "autel_explorer_0a04f118": "Autel Robotics",
    "cisco_meraki_go_d30d00bd": "Cisco Meraki",
    "dahua_dmss_d30abda0": "Dahua",
    "dji_fly_694a02f9": "DJI",
    "dji_pilot_9334b047": "DJI",
    "hikvision_hikconnect_6ee6129f": "Hikvision",
    "hikvision_ivms_2e036b01": "Hikvision",
    "motorola_wave_ptt_24b01b21": "Motorola Solutions",
    "parrot_freeflight6_a105b081": "Parrot",
}

# For NEW manufacturers admitted this cycle, the admission anchor.
NEW_MANUFACTURER_ANCHORS = {
    "Autel Robotics": {
        "primary_category": "drone",
        "source_url": "https://apkpure.com/p/com.autelrobotics.explorer",
        "aliases": "Autel",
        "admission_dispatch_ref": "MAC-104d",
        "ndaa_889_note": None,
    },
    "Cisco Meraki": {
        "primary_category": None,
        "source_url": "https://apkpure.com/p/com.meraki.go",
        "aliases": "Cisco Systems (Meraki), Meraki",
        "admission_dispatch_ref": "MAC-104b",
        "ndaa_889_note": None,
    },
    "Dahua": {
        "primary_category": None,
        "source_url": "https://apkpure.com/p/com.mm.android.DMSS",
        "aliases": "Zhejiang Dahua Technology, Dahua Technology",
        "admission_dispatch_ref": "MAC-104",
        "ndaa_889_note": (
            "NDAA Section 889 federally-restricted; state/local LE deployments "
            "persist outside the federal-procurement bar (runguide §0 scope)."
        ),
    },
    "Hikvision": {
        "primary_category": None,
        "source_url": "https://apkpure.com/p/com.hikvision.hikconnect",
        "aliases": "Hangzhou Hikvision Digital Technology, HikCentral, HikConnect",
        "admission_dispatch_ref": "MAC-104",
        "ndaa_889_note": (
            "NDAA Section 889 federally-restricted; state/local LE deployments "
            "persist outside the federal-procurement bar (runguide §0 scope)."
        ),
    },
}


def parse_existing_notes(notes_text: str | None) -> dict:
    """Notes may be a JSON dict OR plain prose. Normalize to dict."""
    if not notes_text:
        return {}
    try:
        obj = json.loads(notes_text)
        if isinstance(obj, dict):
            return obj
        # JSON but not dict — store under 'description'
        return {"description": obj}
    except (json.JSONDecodeError, ValueError):
        return {"description": notes_text}


def collect_taxonomy_observations() -> dict[str, list[dict]]:
    """vendor_canonical → [{value, occurrence_count, apk_sha256, apk_package, source_dispatch, ...}]"""
    out: dict[str, list[dict]] = {m: [] for m in set(VENDOR_TO_MANUFACTURER.values())}
    for d in sorted(STAGING.glob("*/")):
        vendor_key = d.name
        if vendor_key not in VENDOR_TO_MANUFACTURER:
            continue
        manuf = VENDOR_TO_MANUFACTURER[vendor_key]
        cand_path = d / "candidates.json"
        apk_manifest = json.loads((d / "apk_manifest.json").read_text())
        c = json.loads(cand_path.read_text())
        pf_counts: Counter = Counter()
        pf_metadata: dict[str, dict] = {}
        if isinstance(c, dict) and "candidates" in c:
            for cand in c["candidates"]:
                if cand.get("value_class") != "product_family":
                    continue
                val = cand["value"]
                pf_counts[val] += 1
                if val not in pf_metadata:
                    pf_metadata[val] = {
                        "proposed_confidence_band": cand.get("proposed_confidence_band"),
                        "source_file_relative": cand.get("source_file_relative"),
                    }
        elif isinstance(c, dict) and "product_family" in c:
            for pf in c["product_family"]:
                val = pf["value"]
                pf_counts[val] = pf.get("occurrence_count", 1)
                pf_metadata[val] = {
                    "proposed_confidence_band": pf.get("proposed_confidence_band"),
                    "source_file_relative": pf.get("source_file_relative"),
                    "role_in_codebase": pf.get("role_in_codebase"),
                    "manual_addition": pf.get("manual_addition", False),
                }
        for val, occ in pf_counts.items():
            md = pf_metadata.get(val, {})
            out[manuf].append({
                "value": val,
                "occurrence_count": occ,
                "apk_package": apk_manifest["package_name"],
                "apk_version": apk_manifest["version_name"],
                "apk_sha256": apk_manifest["apk_sha256"],
                "source_dispatch": (
                    "MAC-104"
                    + ("d" if "parrot" in vendor_key or "autel" in vendor_key or "dji" in vendor_key else "")
                    + ("b" if "motorola" in vendor_key or "meraki" in vendor_key else "")
                ),
                "integration_dispatch": "MAC-178",
                "vendor_key": vendor_key,
                **md,
            })
    return out


def main() -> int:
    print(f"DB: {DB}")
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row

    obs = collect_taxonomy_observations()
    print("\n=== taxonomy observations collected ===")
    total_mentions = 0
    total_unique = 0
    for m, items in obs.items():
        per_str = {it["value"] for it in items}
        mentions = sum(it["occurrence_count"] for it in items)
        total_mentions += mentions
        total_unique += len(per_str)
        print(f"  {m}: {len(per_str)} unique strings, {mentions} mentions")
    print(f"  TOTALS: {total_unique} unique strings, {total_mentions} mentions")

    try:
        db.execute("BEGIN")

        # Phase A: admit missing manufacturers per §3 #4
        admitted_new = []
        alias_collisions = []
        for m_name in NEW_MANUFACTURER_ANCHORS:
            existing = db.execute(
                "SELECT id, canonical_name, aliases FROM manufacturers WHERE canonical_name=?",
                (m_name,),
            ).fetchone()
            if existing:
                continue
            # Alias-collision check: does any existing row carry this name as alias?
            aliased_in = db.execute(
                "SELECT id, canonical_name, aliases FROM manufacturers WHERE aliases LIKE ?",
                (f"%{m_name}%",),
            ).fetchall()
            if aliased_in:
                alias_collisions.append({
                    "vendor_canonical": m_name,
                    "existing_canonical": [dict(r) for r in aliased_in],
                })
                print(
                    f"  ALIAS COLLISION: {m_name!r} appears in aliases of "
                    f"{[r['canonical_name'] for r in aliased_in]} — HALT for resolution"
                )
                continue
            anchor = NEW_MANUFACTURER_ANCHORS[m_name]
            notes_obj = {
                "description": f"Admitted via wave-G v2 manufacturer-app extraction ({anchor['admission_dispatch_ref']}).",
                "admission_dispatch_ref": anchor["admission_dispatch_ref"],
                "admission_integration_ref": "MAC-178",
                "admission_date_utc": "2026-05-18T15:00:00Z",
            }
            if anchor.get("ndaa_889_note"):
                notes_obj["ndaa_section_889_note"] = anchor["ndaa_889_note"]
            db.execute(
                """
                INSERT INTO manufacturers (canonical_name, primary_category, source_url, aliases, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    m_name,
                    anchor["primary_category"],
                    anchor["source_url"],
                    anchor.get("aliases"),
                    json.dumps(notes_obj, ensure_ascii=False, sort_keys=True),
                ),
            )
            new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            admitted_new.append({"id": new_id, "name": m_name, "primary_category": anchor["primary_category"]})
            print(f"  INSERTED manufacturer[{new_id}]: {m_name} (primary_category={anchor['primary_category']})")

        if alias_collisions:
            db.rollback()
            print("\n!!! HALT — alias collisions surfaced; reverted. CEO ratification needed.")
            print(json.dumps(alias_collisions, indent=2))
            return 2

        # Phase B: apply product_family_taxonomy[] additive updates
        print("\n=== applying product_family_taxonomy enrichments ===")
        enriched = 0
        skipped_already_present = 0
        for m_name, items in obs.items():
            if not items:
                continue
            row = db.execute(
                "SELECT id, canonical_name, notes FROM manufacturers WHERE canonical_name=?",
                (m_name,),
            ).fetchone()
            if not row:
                print(f"  WARN: manufacturer {m_name!r} still missing after admission phase — skipping")
                continue
            notes_obj = parse_existing_notes(row["notes"])
            existing_taxonomy = notes_obj.get("product_family_taxonomy") or []
            # Dedup-key: (value, apk_sha256) — same string from different APKs is a corroborating mention
            existing_keys = {
                (e.get("value"), e.get("apk_sha256")) for e in existing_taxonomy
            }
            additions = []
            for it in items:
                key = (it["value"], it["apk_sha256"])
                if key in existing_keys:
                    skipped_already_present += 1
                    continue
                additions.append(it)
                existing_keys.add(key)
            if not additions:
                continue
            new_taxonomy = existing_taxonomy + additions
            notes_obj["product_family_taxonomy"] = new_taxonomy
            db.execute(
                "UPDATE manufacturers SET notes=? WHERE id=?",
                (json.dumps(notes_obj, ensure_ascii=False, sort_keys=True), row["id"]),
            )
            enriched += len(additions)
            print(
                f"  {m_name} (id={row['id']}): +{len(additions)} taxonomy entries "
                f"({sorted({a['value'] for a in additions})})"
            )

        db.commit()
        print("\nCOMMIT.")

        print("\n=== Priority 4 verification ===")
        print(f"manufacturers admitted (new): {len(admitted_new)}")
        for m in admitted_new:
            print(f"  +[{m['id']}] {m['name']}")
        print(f"product_family_taxonomy[] entries added: {enriched}")
        print(f"product_family_taxonomy[] entries skipped (already present): {skipped_already_present}")
        print(
            "manufacturers count now:",
            db.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0],
        )
        print(
            "manufacturers with product_family_taxonomy[]:",
            db.execute(
                "SELECT COUNT(*) FROM manufacturers WHERE notes LIKE '%product_family_taxonomy%'"
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
