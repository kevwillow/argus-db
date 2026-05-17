"""
MAC-170 P2 — UK Companies House sources admission + Johnson Matthey PLC identifier promotion.

Scope (per MAC-168 brief §2 Priority 2 + handoff at
~/argus-internal/extraction_outputs/uk_ch_admission/HANDOFF_TO_VALIDATOR.md):

1. INSERT one `sources` row for UK Companies House (primary_registry, tier=1).
   License-into-notes folding per CP23 cycle-1 finding #1 (OGL-3.0 in notes_json).
2. INSERT one `manufacturers` row for Johnson Matthey PLC (no existing canonical row).
3. INSERT one `identifiers` row promoting raw_observations.id=228921
   (mac_range 40:f3:85:1/28, conf 85, source_type=primary_registry, source_url=IEEE).
   Sibling-shape with the 14 other 40:f3:85:N/28 MA-M rows already in identifiers.
4. UPDATE raw_observations row 228921: processed_at + promoted_identifier_id +
   notes.pii_review_disposition flip.

Confidence: 85 (primary_registry single-source band 70-85, per §8.2 + the 14
sibling rows in this same MA-M /24 block which sit at 85). UK CH is an
entity-confirmation cross-validation (different source-lens, no MAC-binding
co-observation per the observation-vs-registration source-lens memory) — does
NOT trigger §8.3 +5 corroboration uplift; confidence stays at sibling band.

§11 #8 cardinal-rule check: no confidence drift (85 = sibling band; UK CH
adds entity disambiguation, not independent MAC-attribution corroboration).

Idempotent: re-runs early-exit if the sources URL or identifier already exist.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

DB = Path(__file__).resolve().parents[2] / "db" / "argus.db"

UK_CH_NAME = "UK Companies House"
UK_CH_URL = "https://api.company-information.service.gov.uk/"
IEEE_OUI28_URL = "https://standards-oui.ieee.org/oui28/mam.csv"
RO_ID = 228921
IDENT = "40:f3:85:1/28"


def build_sources_notes() -> dict[str, Any]:
    return {
        "session_admission": "uk_companies_house_admission",
        "dispatch": "MAC-170",
        "admission_date_utc": "2026-05-16T19:00:28Z",
        "runguide_path": "new data 5.16/uk_companies_house_admission_runguide.md",
        "runguide_sha256": "3e2e2bed03c56007ca8287b3650d0c9634f790ddcd648c18079247bb336f0fa6",
        "schema_version_at_session": 19,
        "api_base": "https://api.company-information.service.gov.uk",
        "per_row_url_template": "https://find-and-update.company-information.service.gov.uk/company/{company_number}",
        "auth_shape": "HTTP Basic (api_key as username, blank password)",
        "rate_limit": "600 requests per 5-minute rolling window per API key",
        "endpoints_used": ["/search/companies", "/company/{company_number}"],
        "endpoints_explicitly_avoided_pii_7_5": [
            "/company/{company_number}/officers",
            "/company/{company_number}/persons-with-significant-control",
        ],
        "license": "OGL-3.0",
        "license_attribution": "This information is licensed under the terms of the Open Government Licence v3.0 — https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "license_posture": "OGL-3.0",
        "access_mode": "automated_api",
        "candidates_staged_strong": 1,
        "candidates_staged_weak": 0,
        "candidates_staged_probe": 0,
        "candidates_no_match": 0,
        "non_uk_routed_to_future_runs": 60,
        "ambiguous_jurisdiction_deferred": 1,
        "cross_validation_summary": {
            "fcc_grantees_overlap": 0,
            "existing_identifiers_overlap": 0,
            "existing_manufacturer_overlap": 0,
        },
    }


def build_manufacturer_notes() -> dict[str, Any]:
    return {
        "dispatch": "MAC-170",
        "session": "uk_companies_house_admission",
        "uk_companies_house_number": "00033774",
        "uk_companies_house_url": "https://find-and-update.company-information.service.gov.uk/company/00033774",
        "company_type": "plc",
        "jurisdiction": "england-wales",
        "date_of_creation": "1891-04-11",
        "registered_office_city": "London",
        "registered_office_country": "United Kingdom",
        "sic_codes": ["20590", "24410", "29320", "71121"],
        "sic_surveillance_adjacency_flagged": False,
        "sic_surveillance_adjacency_note": "SIC list (chemistry/precious metals/motor-vehicle parts/engineering design) — no overlap with §5.4 surveillance/comms-equipment SIC codes.",
        "added_via": "MAC-170 P2 (UK CH cycle-1 admission); cross-validation found 0 hits in canonical manufacturers table prior to insertion.",
    }


def build_identifier_notes() -> dict[str, Any]:
    return {
        "wave_b_phase": "ieee_expanded_registries",
        "dispatch": "MAC-170",
        "ieee_registry": "MA-M",
        "assignment_block_size_bits": 28,
        "surveillance_vendor_flag": False,
        "ieee_self_attributed": None,
        "upstream_license_posture": "OGL-3.0",
        "upstream_license_posture_rationale": "Most-restrictive of the two corroborating sources. IEEE OUI listing is PUBLIC_DOMAIN; UK CH detail is OGL-3.0. The manufacturer string 'Johnson Matthey PLC' is materially derived from the UK CH lookup (legal-entity name + suffix), so OGL-3.0 carries forward.",
        "class_b_hold_resolution": {
            "input_ieee_registrant_name": "Johnson Matthey",
            "resolution_method": "uk_companies_house_class_b_sustained_hold_resolution",
            "resolved_entity": "JOHNSON MATTHEY PLC",
            "company_number": "00033774",
            "find_and_update_url": "https://find-and-update.company-information.service.gov.uk/company/00033774",
            "url_verified_http_status": 200,
            "url_verified_at_utc": "2026-05-16T18:58:08Z",
            "company_status": "active",
            "company_type": "plc",
            "jurisdiction": "england-wales",
            "date_of_creation": "1891-04-11",
            "registered_office_city": "London",
            "registered_office_country": "United Kingdom",
            "registered_office_street_redacted_per_7_5": True,
            "sic_codes": ["20590", "24410", "29320", "71121"],
            "sic_surveillance_adjacency_flagged": False,
            "address_mismatch_note": "IEEE registration address (Materials Technology Centre, Billingham TS23 4ED) is the JM R&D operational site; UK CH registered office (London EC2V 7AD, street redacted) is the parent PLC HQ. Both are documented JM PLC UK sites — 'no address conflict' clause of runguide §5.2 applies.",
            "search_response_sha256": "dcc6e8aa8548f89aa8829fdb65e9177ef90931845f95d568a24f5a4af0f93785",
            "detail_response_sha256": "7122632a905fc61c36c170a0d0bde2ddec1105eef167a18fdcb7586e6a1c7323",
        },
        "corroboration_chain": [
            "sources.id=2 IEEE OUI registry (MA-M sub-allocation 40:f3:85:1/28) — proximate provenance for the MAC↔name binding (source_url)",
            "sources.id=<UK_CH_NEW> UK Companies House #00033774 (parent PLC, est. 1891) — entity disambiguation; no MAC-binding co-observation (different source-lens) so no §8.3 corroboration uplift",
        ],
        "confidence_rationale": "Single-source primary_registry promotion (§8.2 70-85 band) at sibling-band ceiling 85, matching the 14 other 40:f3:85:N/28 MA-M rows already in identifiers. UK CH cross-validation confirms the entity exists / is active / is the parent PLC but does NOT independently observe the MAC↔entity binding — per §11 #8 (no confidence drift), no +5 uplift applies.",
        "pre_promotion_pii_disposition": "individual_attributed_pii_sustain",
        "post_promotion_pii_disposition": "corporate_entity_confirmed_via_uk_ch",
    }


def main() -> int:
    if not DB.exists():
        print(f"FATAL: DB not found at {DB}", file=sys.stderr)
        return 2

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("BEGIN IMMEDIATE")
    try:
        # ===== §7.4 pre-flight checks =====
        existing_src = con.execute(
            "SELECT id FROM sources WHERE name=? OR url=?", (UK_CH_NAME, UK_CH_URL)
        ).fetchone()
        if existing_src is not None:
            print(f"NOOP: sources row already exists at id={existing_src['id']}; aborting (idempotent re-run path)")
            con.rollback()
            return 0

        existing_ident = con.execute(
            "SELECT id FROM identifiers WHERE identifier=?", (IDENT,)
        ).fetchone()
        if existing_ident is not None:
            print(f"NOOP: identifier {IDENT} already exists at id={existing_ident['id']}; aborting (idempotent re-run path)")
            con.rollback()
            return 0

        ro = con.execute(
            "SELECT id, source_id, source_url, source_excerpt, candidate_identifier, candidate_type, "
            "candidate_manufacturer, processed_at, promoted_identifier_id, notes "
            "FROM raw_observations WHERE id=?",
            (RO_ID,),
        ).fetchone()
        if ro is None:
            raise RuntimeError(f"FATAL: raw_observations row {RO_ID} not found")
        if ro["candidate_identifier"] != IDENT:
            raise RuntimeError(f"FATAL: ro.candidate_identifier mismatch: got {ro['candidate_identifier']!r}, expected {IDENT!r}")
        if ro["candidate_type"] != "mac_range":
            raise RuntimeError(f"FATAL: ro.candidate_type mismatch: got {ro['candidate_type']!r}, expected 'mac_range'")
        if ro["promoted_identifier_id"] is not None:
            raise RuntimeError(f"FATAL: ro {RO_ID} already promoted to identifier id={ro['promoted_identifier_id']}")

        # ===== 1. INSERT sources row =====
        sources_notes = build_sources_notes()
        cur = con.execute(
            "INSERT INTO sources (name, url, source_type, tier, last_fetched_at, last_status, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                UK_CH_NAME,
                UK_CH_URL,
                "primary_registry",
                1,
                "2026-05-16T19:00:28Z",
                "success",
                json.dumps(sources_notes, ensure_ascii=False, sort_keys=True),
            ),
        )
        new_src_id = cur.lastrowid
        print(f"INSERTed sources id={new_src_id} name={UK_CH_NAME!r} source_type=primary_registry tier=1")

        # ===== 2. INSERT manufacturers row =====
        man_notes = build_manufacturer_notes()
        cur = con.execute(
            "INSERT INTO manufacturers (canonical_name, aliases, primary_category, source_url, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "Johnson Matthey PLC",
                "Johnson Matthey",
                None,
                "https://find-and-update.company-information.service.gov.uk/company/00033774",
                json.dumps(man_notes, ensure_ascii=False, sort_keys=True),
            ),
        )
        new_man_id = cur.lastrowid
        print(f"INSERTed manufacturers id={new_man_id} canonical_name='Johnson Matthey PLC' aliases='Johnson Matthey'")

        # ===== 3. INSERT identifiers row =====
        # Mirror sibling MA-M 40:f3:85:N/28 shape from id=5554 etc.
        ident_notes = build_identifier_notes()
        cur = con.execute(
            "INSERT INTO identifiers (identifier, identifier_type, device_category, manufacturer, "
            "model, confidence, source_url, source_type, source_excerpt, geographic_scope, "
            "first_seen, last_verified, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                IDENT,
                "mac_range",
                "unknown",
                "Johnson Matthey PLC",
                None,
                85,
                IEEE_OUI28_URL,
                "primary_registry",
                ro["source_excerpt"],
                "GB",
                "2026-05-13T23:03:07Z",
                "2026-05-16T18:58:08Z",
                json.dumps(ident_notes, ensure_ascii=False, sort_keys=True),
            ),
        )
        new_ident_id = cur.lastrowid
        print(f"INSERTed identifiers id={new_ident_id} identifier={IDENT} manufacturer='Johnson Matthey PLC' confidence=85")

        # ===== 4. UPDATE raw_observations row 228921 =====
        ro_notes = json.loads(ro["notes"]) if ro["notes"] else {}
        ro_notes["pii_review_disposition"] = "corporate_entity_confirmed_via_uk_ch"
        ro_notes["pii_review_disposition_history"] = ro_notes.get("pii_review_disposition_history", []) + [
            {
                "from": "individual_attributed_pii_sustain",
                "to": "corporate_entity_confirmed_via_uk_ch",
                "at_utc": "2026-05-17T05:32:00Z",
                "dispatch": "MAC-170",
                "method": "uk_companies_house_class_b_sustained_hold_resolution",
                "company_number": "00033774",
            }
        ]
        ro_notes["promotion_dispatch"] = "MAC-170"
        ro_notes["uk_ch_corroborating_source_id"] = new_src_id

        con.execute(
            "UPDATE raw_observations SET processed_at=?, promoted_identifier_id=?, notes=? WHERE id=?",
            (
                "2026-05-17T05:32:00Z",
                new_ident_id,
                json.dumps(ro_notes, ensure_ascii=False, sort_keys=True),
                RO_ID,
            ),
        )
        print(f"UPDATEd raw_observations id={RO_ID}: promoted_identifier_id={new_ident_id}, pii_review_disposition=corporate_entity_confirmed_via_uk_ch")

        # ===== Final integrity check before commit =====
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise RuntimeError(f"FATAL: PRAGMA integrity_check returned {ok!r}; rolling back")
        print(f"PRAGMA integrity_check = {ok}")

        con.commit()
        print()
        print("=== MAC-170 P2 promotion committed ===")
        print(f"  new sources.id        = {new_src_id} (UK Companies House)")
        print(f"  new manufacturers.id  = {new_man_id} (Johnson Matthey PLC)")
        print(f"  new identifiers.id    = {new_ident_id} ({IDENT}, conf 85)")
        print(f"  raw_observations.{RO_ID} → processed/promoted/pii-disposition flipped")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
