"""
MAC-174 P6 — CourtListener / RECAP (Free Law Project) source admission.

Scope (per MAC-168 brief §2 Priority 6 + MAC-169 P1 outputs;
handoff at
~/argus-internal/extraction_outputs/courtlistener_admission/HANDOFF_TO_VALIDATOR.md):

  INSERT 1 `sources` row for CourtListener / RECAP at
    source_type   = 'judicial_filing'    (CP23 §1 enum extension)
    tier          = 1
    last_status   = 'admitted_no_promotions_this_dispatch'
    notes_json    = { license: CC0, access_mode: automated_with_auth,
                      session_admission, runguide_path,
                      auth_shape (Bearer token mandatory; anonymous tier
                      revoked 2026-05-16 per handoff halt history),
                      rate_limit, endpoints_used, endpoints_explicitly_avoided,
                      disambiguation_outcomes (3 STRONG-class rejections
                      with rationale), filings_catalog_audit_only_path,
                      v3_to_v4_migration audit trail }

  ZERO promotions of staged STRONG-class candidates this dispatch.
  All 9 candidate rows reject for §7.4-class disqualification:

    A. Berla STRONG (n=3 same docket — extractor emitted per text-pool field;
       docket 68243982 = "Berla Kay Strong and Thomas Wesley Strong"
       Missouri Eastern Bankruptcy Court 24-10050, 2024-02-12).
       Reject reason: berla_first_name_not_vendor.
       Pre-ratified by CP23 §10 short-vendor-name disambiguation discipline
       + cycle-4 §1 #6 explicit Berla case-study + MAC-174 dispatch
       mandatory-disambig directive. party_list_verbatim = ["Berla Kay
       Strong", "Thomas Wesley Strong"] (two natural persons; no corporate
       Berla entity present).

    B. BRINC named_gov STRONG (n=3 same docket — docket 69901794 =
       "Patrzalek v. United States Department of Defense" Western District
       Oklahoma 5:25-cv-00439, 2025-04-16). Pro-se RICO complaint listing
       57+ co-defendants including Donald J Trump, Benjamin Netanyahu,
       Marco Rubio, "Bored Ape Yacht Club", "Individuals Named in the
       Epstein Files", AeroVironment, Northrop Grumman, Lockheed Martin,
       etc. BRINC Drones Inc and US Department of Defense both appear in
       the same `party` array as co-defendants under plaintiff's RICO
       theory — this is NOT a vendor/customer relationship and the
       source_excerpt does not support the proposed
       "BRINC → DoD named_gov_customer" claim.
       Reject reason: rico_co_defendant_not_customer_relationship.
       Surfaces a new disambiguation FP-class for CEO consideration
       (parallel to CP23 §10 Berla short-vendor-name discipline; vexatious
       pro-se RICO complaints generate party-list co-occurrence noise that
       text-pool STRONG-match scoring cannot distinguish from genuine
       commercial relationships).

    C. BRINC contract_value STRONG (n=3 same docket — docket 69812039 =
       "Vortical Systems LLC v. Brinc Drones, Inc." Delaware District
       1:25-cv-00388-UNA, 2025-03-28). Patent infringement complaint.
       value_text_verbatim "$ 405," is extracted from the docket entry
       "COMPLAINT for Patent Infringement with Jury Demand against Brinc
       Drones, Inc. (Filing fee $ 405, receipt number ADEDC-4648720)".
       This is the federal court complaint filing fee (28 USC §1914 +
       JCUS-fee schedule), NOT a contract value or procurement-relevant
       dollar amount.
       Reject reason: court_filing_fee_not_contract_value.
       Surfaces a new disambiguation FP-class for CEO consideration
       (RECAP docket-entry text routinely contains filing-fee /
       receipt-number / sanctions-amount / discovery-cost-shifting dollar
       amounts that text-pool regex matches but that are not contract
       values; cycle-4 §1 #6 disambiguation discipline should extend to
       monetary-amount contextualization).

  391-filing audit catalog stays at
    extraction_outputs/courtlistener_admission/all_filings_catalog.json
  as audit-trail (referenced from notes; not promoted; not staged into
  raw_observations this dispatch).

§11 hard-rule discipline:
  §11 #1  no fabrication: all metadata derived from staged handoff +
          per-search-page raw captures
          (raw/courtlistener/search_<vendor>_p<n>.json verified for
          all 9 STRONG-class rejections).
  §11 #7  no promotion without provenance: this dispatch is sources-
          admission only; zero identifier OR procurement_records writes.
  §11 #8  no confidence drift: zero confidence-column writes. The
          handoff's `proposed_confidence_at_promotion` values (80/70/65)
          are NOT applied — all 9 STRONG-class candidates reject before
          promotion per §7.4.
  §11 #11 amendment-log: CP23 §10 short-vendor-name disambiguation
          (Berla case-study) is the ratifying amendment for the n=3
          Berla rejection. The two new disambig FP-classes (RICO pro-se
          co-defendant + filing-fee-not-contract-value) surface to CEO
          as candidate findings for a future CP / SAR (not authored by
          Validator per §11 #11 discipline).

Idempotent: per-row pre-check on UNIQUE(url). Re-run is a no-op.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

DB = Path(__file__).resolve().parents[2] / "db" / "argus.db"

DISPATCH = "MAC-174"
SESSION = "courtlistener_admission"
ADMISSION_DATE_UTC = "2026-05-17T03:55:52Z"  # handoff timestamp
RUNGUIDE_PATH = "new data 5.16/courtlistener_admission_runguide.md"
SCHEMA_VERSION_AT_SESSION = 21
LAST_STATUS = "admitted_no_promotions_this_dispatch"
LICENSE_POSTURE = "CC0"

CL = {
    "name": "CourtListener / RECAP (Free Law Project)",
    "url": "https://www.courtlistener.com/api/rest/v4/",
    "source_type": "judicial_filing",
    "tier": 1,
    "notes": {
        "dispatch": DISPATCH,
        "session_admission": SESSION,
        "admission_date_utc": ADMISSION_DATE_UTC,
        "runguide_path": RUNGUIDE_PATH,
        "schema_version_at_session": SCHEMA_VERSION_AT_SESSION,
        "license": LICENSE_POSTURE,
        "license_posture": LICENSE_POSTURE,
        "license_attribution": (
            "Free Law Project releases CourtListener metadata under CC0-1.0. "
            "Underlying federal court filings are public records "
            "(Feist + 17 USC §105 for US government works)."
        ),
        "access_mode": "automated_with_auth",
        "auth_shape": (
            "Bearer token mandatory (anonymous tier revoked 2026-05-16 "
            "per handoff halt history STOP_THE_LINE_anonymous_access_"
            "revoked_RESOLVED.md)"
        ),
        "auth_value_handling": (
            "Loaded from argus/.env/.env; value never logged in extraction "
            "outputs or stdout; verified by length-only check "
            "(len=40 for CourtListener tokens)"
        ),
        "rate_limit_observed": (
            "/search/: 5 req per 60s window (authenticated tier); "
            "other endpoints have higher unstated ceilings; "
            "self-paced at 13s/search-call"
        ),
        "endpoints_used": [
            "/api/rest/v4/courts/                  (probe verify only)",
            "/api/rest/v4/search/?type=r&q=...     (per-vendor party search)",
        ],
        "endpoints_explicitly_avoided": [
            "/api/rest/v4/people/",
            "/api/rest/v4/judges/",
            "/api/rest/v4/audio/",
            "/api/rest/v4/dockets/{id}/  (deferred — per-filing fetch)",
            "/api/rest/v4/recap-documents/{id}/  (deferred — per-filing fetch)",
        ],
        "v3_to_v4_migration": (
            "V3 deprecated for new tokens 2026-05-16; migrated mid-session. "
            "See handoff STOP_THE_LINE_v3_deprecated_RESOLVED.md + "
            "v3_v4_count_comparison.json for the audit trail."
        ),
        "session_extraction_summary": {
            "vendors_searched": 34,
            "vendors_with_at_least_one_strong_match": 5,
            "vendors_with_strong_plus_cross_corroboration": 0,
            "total_filings_extracted": 391,
            "strong_count": 23,
            "weak_count": 15,
            "none_count": 353,
            "api_search_calls_used": 47,
            "api_other_calls_used": 1,
        },
        "promotion_outcome_this_dispatch": {
            "identifiers_promoted": 0,
            "procurement_records_promoted": 0,
            "named_gov_customer_promotions": 0,
            "contract_value_promotions": 0,
        },
        "disambiguation_outcomes": {
            "berla_short_vendor_name_rejection": {
                "candidate_count": 3,
                "unique_docket_count": 1,
                "docket_id": 68243982,
                "case_name_verbatim": "Berla Kay Strong and Thomas Wesley Strong",
                "court_id": "moeb",
                "court_name": "United States Bankruptcy Court, E.D. Missouri",
                "docket_number": "24-10050",
                "date_filed": "2024-02-12",
                "absolute_url": (
                    "https://www.courtlistener.com/docket/68243982/"
                    "berla-kay-strong-and-thomas-wesley-strong/"
                ),
                "party_list_verbatim": [
                    "Berla Kay Strong",
                    "Thomas Wesley Strong",
                ],
                "reject_reason": "berla_first_name_not_vendor",
                "ratifying_amendment": (
                    "CP23 §10 short-vendor-name disambiguation "
                    "discipline + cycle-4 §1 finding #6 explicit "
                    "Berla case-study"
                ),
                "manufacturer_target_in_argus": "Berla Corporation (id=30)",
            },
            "brinc_named_gov_rico_co_defendant_rejection": {
                "candidate_count": 3,
                "unique_docket_count": 1,
                "docket_id": 69901794,
                "case_name_verbatim": (
                    "Patrzalek v. United States Department of Defense"
                ),
                "court_id": "okwd",
                "docket_number": "5:25-cv-00439",
                "date_filed": "2025-04-16",
                "absolute_url": (
                    "https://www.courtlistener.com/docket/69901794/"
                    "patrzalek-v-united-states-department-of-defense/"
                ),
                "party_list_summary": (
                    "57-entity defendant list including Donald J Trump, "
                    "Benjamin Netanyahu, Marco Rubio, Matt Gaetz, JD Vance, "
                    "AeroVironment, Northrop Grumman, Lockheed Martin, "
                    "BRINC Drones Inc, US Department of Defense, "
                    "Bored Ape Yacht Club, Individuals Named in the "
                    "Epstein Files, NATO, Tesla Corporation"
                ),
                "claimed_customer_relationship": (
                    "BRINC → United States Department of Defense"
                ),
                "reject_reason": "rico_co_defendant_not_customer_relationship",
                "rationale": (
                    "Pro-se RICO complaint listing BRINC and DoD as "
                    "co-defendants under plaintiff's RICO theory. "
                    "Party-list co-occurrence is not evidence of "
                    "vendor/customer relationship. source_excerpt does "
                    "not support the proposed named_gov_customer claim."
                ),
                "ratifying_amendment": (
                    "§7.4 source_excerpt-must-support-claim check "
                    "(direct §7.4 application; no prior CP precedent for "
                    "this specific FP class — surfaced to CEO as "
                    "candidate finding for future CP/SAR)"
                ),
                "manufacturer_target_in_argus": "BRINC (id=24)",
            },
            "brinc_contract_value_filing_fee_rejection": {
                "candidate_count": 3,
                "unique_docket_count": 1,
                "docket_id": 69812039,
                "case_name_verbatim": (
                    "Vortical Systems LLC v. Brinc Drones, Inc."
                ),
                "court_id": "ded",
                "docket_number": "1:25-cv-00388-UNA",
                "date_filed": "2025-03-28",
                "absolute_url": (
                    "https://www.courtlistener.com/docket/69812039/"
                    "vortical-systems-llc-v-brinc-drones-inc/"
                ),
                "value_text_verbatim": "$ 405,",
                "context_verbatim": (
                    "COMPLAINT for Patent Infringement with Jury Demand "
                    "against Brinc Drones, Inc. (Filing fee $ 405, "
                    "receipt number ADEDC-4648720) - filed by Vortical "
                    "Systems LLC."
                ),
                "reject_reason": "court_filing_fee_not_contract_value",
                "rationale": (
                    "$405 verbatim extraction is the federal court "
                    "complaint filing fee per 28 USC §1914 + JCUS-fee "
                    "schedule. Not a contract value or "
                    "procurement-relevant dollar amount. "
                    "Patent-infringement litigation between two "
                    "commercial parties (Vortical Systems v. Brinc); "
                    "no procurement relationship."
                ),
                "ratifying_amendment": (
                    "§7.4 source_excerpt-must-support-claim check "
                    "(direct §7.4 application; no prior CP precedent for "
                    "this specific FP class — surfaced to CEO as "
                    "candidate finding for future CP/SAR; sibling to the "
                    "RICO co-defendant FP class above and to the CP23 §10 "
                    "short-vendor-name discipline)"
                ),
                "manufacturer_target_in_argus": "BRINC (id=24)",
            },
        },
        "candidate_findings_for_future_cp_or_sar": [
            {
                "fp_class": "rico_co_defendant_not_customer_relationship",
                "description": (
                    "Vexatious pro-se RICO complaints generate party-list "
                    "co-occurrence noise that text-pool STRONG-match "
                    "scoring cannot distinguish from genuine "
                    "vendor/customer relationships. Disambiguation "
                    "options: (a) cap party_list_count threshold (e.g. "
                    "reject named_gov_customer claims where party_list "
                    "length exceeds N, signaling a multi-defendant suit); "
                    "(b) require nature-of-suit code filter "
                    "(e.g. exclude '890 Other Statutory Actions' + "
                    "'18:1961 Racketeering (RICO) Act'); (c) require "
                    "case_name structure to match a procurement-relevant "
                    "shape (US v. <vendor> or <agency> v. <vendor>) "
                    "rather than co-defendant adjacency."
                ),
                "first_observed_at": "MAC-174 P6 (this dispatch)",
            },
            {
                "fp_class": "court_filing_fee_not_contract_value",
                "description": (
                    "RECAP docket-entry text routinely contains "
                    "filing-fee, receipt-number, sanctions-amount, and "
                    "discovery-cost-shifting dollar amounts that text-pool "
                    "regex matches but that are not contract values. "
                    "Disambiguation options: (a) context-window blacklist "
                    "(reject value mentions where ±50-char context "
                    "contains 'filing fee', 'receipt number', 'sanctions', "
                    "'costs', 'fee schedule'); (b) require minimum "
                    "value threshold (e.g. ≥$10,000 to filter out "
                    "court-fee-shape amounts); (c) require explicit "
                    "contract-language co-occurrence ('contract', "
                    "'purchase order', 'award', 'procurement') in the "
                    "same docket entry."
                ),
                "first_observed_at": "MAC-174 P6 (this dispatch)",
            },
        ],
        "filings_catalog_audit_only_path": (
            "extraction_outputs/courtlistener_admission/"
            "all_filings_catalog.json"
        ),
        "filings_catalog_disposition": (
            "Audit-only this dispatch; not staged into raw_observations. "
            "Available for future RECAP-revisit per MAC-168 brief §2 "
            "Priority 6 action #4."
        ),
        "halt_history": [
            {
                "halt": "anonymous_access_revoked",
                "resolution": (
                    "Operator wrote COURTLISTENER_API_TOKEN to "
                    "argus/.env/.env at session 2 kickoff"
                ),
            },
            {
                "halt": "manufacturers_aliases_schema_drift",
                "resolution": (
                    "Operator chose Option 1: parse "
                    "manufacturers.aliases comma-string (session 1)"
                ),
            },
            {
                "halt": "search_rate_ceiling_5_per_min",
                "resolution": (
                    "Self-paced to 13s/search-call "
                    "(12s minimum + 1s safety); no operator action"
                ),
            },
            {
                "halt": "v3_deprecated_for_new_tokens",
                "resolution": (
                    "Operator chose Option 3 (session 2 in-run): "
                    "migrate to V4, re-extract all 34 vendors, capture "
                    "V3↔V4 count comparison"
                ),
            },
        ],
    },
}


def main() -> int:
    if not DB.exists():
        print(f"FATAL: DB not found at {DB}", file=sys.stderr)
        return 2

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("BEGIN IMMEDIATE")
    try:
        sv = con.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0]
        if sv != SCHEMA_VERSION_AT_SESSION:
            raise RuntimeError(
                f"FATAL: schema_version mismatch — expected "
                f"{SCHEMA_VERSION_AT_SESSION}, got {sv}"
            )

        existing = con.execute(
            "SELECT id, name FROM sources WHERE url = ?", (CL["url"],)
        ).fetchone()
        if existing is not None:
            print(
                f"NOOP: sources url already present at id={existing['id']} "
                f"name={existing['name']!r}"
            )
            inserted_id = None
        else:
            cur = con.execute(
                "INSERT INTO sources "
                "(name, url, source_type, tier, last_fetched_at, "
                " last_status, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    CL["name"],
                    CL["url"],
                    CL["source_type"],
                    CL["tier"],
                    ADMISSION_DATE_UTC,
                    LAST_STATUS,
                    json.dumps(CL["notes"], ensure_ascii=False, sort_keys=True),
                ),
            )
            inserted_id = cur.lastrowid
            print(
                f"INSERTed sources id={inserted_id} name={CL['name']!r} "
                f"source_type=judicial_filing tier=1 "
                f"last_status={LAST_STATUS} license=CC0 "
                f"access_mode=automated_with_auth"
            )

        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise RuntimeError(
                f"FATAL: PRAGMA integrity_check returned {ok!r}"
            )
        print(f"PRAGMA integrity_check = {ok}")

        fkv = con.execute("PRAGMA foreign_key_check").fetchall()
        if fkv:
            raise RuntimeError(
                f"FATAL: PRAGMA foreign_key_check failed: {fkv!r}"
            )
        print("PRAGMA foreign_key_check = ok (no violations)")

        con.commit()
        print()
        print("=== MAC-174 P6 CourtListener admission committed ===")
        if inserted_id is not None:
            print(
                f"  inserted: sources.id={inserted_id} "
                f"{CL['name']} ({CL['url']})"
            )
        else:
            print("  inserted: 0 (idempotent re-run; already present)")
        print()
        print("§7.4 promotion outcomes (all 9 STRONG-class candidates rejected):")
        print("  Berla n=3       → reject berla_first_name_not_vendor (CP23 §10)")
        print(
            "  BRINC named_gov n=3   → reject "
            "rico_co_defendant_not_customer_relationship (§7.4)"
        )
        print(
            "  BRINC contract_value n=3 → reject "
            "court_filing_fee_not_contract_value (§7.4)"
        )
        print()
        print("§11 #7 provenance: 1 sources row admitted with CC0 license posture")
        print(
            "§11 #8 confidence: zero identifier OR procurement_records writes"
        )
        print(
            "§11 #11 amendment-log: 2 candidate FP-classes surfaced "
            "to CEO for future CP/SAR consideration"
        )
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
