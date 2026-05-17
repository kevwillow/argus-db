"""
MAC-173 P5 — US state SoS sources admission (DE / CA / TX).

Scope (per MAC-168 brief §2 Priority 5 + CEO decision memo
2026-05-17T05:00:31Z; handoffs at
~/argus-internal/extraction_outputs/us_state_sos_admission/HANDOFF_TO_VALIDATOR.md +
~/argus-internal/new data 5.16/state_sos_access_mode_admission_addendum.md):

  INSERT 3 `sources` rows for Delaware Division of Corporations,
  California SoS Bizfile, Texas SoS SOSDirect — each with:

    source_type   = 'primary_registry'
    tier          = 1
    last_status   = 'admitted_pending_operator_manual_queue'
    notes_json    = { license: US_STATE_PUBLIC_RECORDS (cycle-1 fold per CP23),
                      access_mode: 'operator_manual_only' (CEO ruling #3),
                      ... handoff-observed access-control state ... }

  NO per-candidate identifier promotion. Operator-manual queue
  (11 US-shaped Class B candidates: 1 DE / 3 CA / 1 TX routable + 6 long-tail)
  is post-integration follow-on, not paperclip scope this dispatch.

§11 hard-rule discipline:
  §11 #1  no fabrication: all metadata derived from staged handoff +
          addendum docs. No new identifier values minted.
  §11 #7  no main-table promotion without provenance: this dispatch is
          sources-admission only; zero `identifiers` row writes.
  §11 #8  no confidence drift: no confidence-column writes. License
          posture is US_STATE_PUBLIC_RECORDS (sources-tier only); §8.2
          confidence bands bind on the eventual identifier-row source_type
          (which is primary_registry, 70-85 band) when operator-manual
          findings are integrated in a future cycle.
  §11 #11 amendment-log discipline: CP23 already registers the
          `access_mode` notes_json convention (cycle-3 addendum §6 +
          BIBLE_AMENDMENTS CP23). This script ships the first
          `operator_manual_only` rows under that convention.

Reconciliation note (for CEO awareness; surfaced in dispatch comment):
  Handoff `source_admission_metadata.json` and addendum §3.x agree on
  DE + CA URLs verbatim. TX diverges:
    - Handoff URL: https://mycpa.cpa.state.tx.us/coa/search.do (Texas
                   Comptroller of Public Accounts — different
                   constitutional officer than the SoS)
    - Addendum URL: https://direct.sos.state.tx.us/ (Texas SoS
                    SOSDirect — actual SoS body, matches admission scope)
  Admission scope per dispatch title is "State SoS"; this script uses the
  addendum's canonical SoS URL and records the handoff's probed
  Comptroller URL inside `notes.handoff_probed_alternate_url` for audit.

Idempotent: per-row pre-check on UNIQUE(url). Re-run is a no-op.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

DB = Path(__file__).resolve().parents[2] / "db" / "argus.db"

DISPATCH = "MAC-173"
SESSION = "us_state_sos_admission"
ADMISSION_DATE_UTC = "2026-05-16T23:57:07Z"  # post-run timestamp from manifest.json
RUNGUIDE_PATH = "new data 5.16/us_state_sos_admission_runguide.md"
SCHEMA_VERSION_AT_SESSION = 21
LAST_STATUS = "admitted_pending_operator_manual_queue"
LICENSE_POSTURE = "US_STATE_PUBLIC_RECORDS"


def _base_notes() -> dict[str, Any]:
    return {
        "dispatch": DISPATCH,
        "session_admission": SESSION,
        "admission_date_utc": ADMISSION_DATE_UTC,
        "runguide_path": RUNGUIDE_PATH,
        "schema_version_at_session": SCHEMA_VERSION_AT_SESSION,
        "license": LICENSE_POSTURE,
        "license_posture": LICENSE_POSTURE,
        "access_mode": "operator_manual_only",
        "candidates_processed_via_automated_extraction": 0,
        "candidates_staged_strong": 0,
        "candidates_staged_weak": 0,
        "candidates_staged_probe": 0,
        "candidates_no_match": 0,
        "operator_manual_queue_file": "extraction_outputs/us_state_sos_admission/operator_manual_queue.json",
        "endpoints_used": [],
        "endpoints_explicitly_avoided": [
            "registered_agent_lookup",
            "officer_director_search",
            "shareholder_member_search",
        ],
    }


# ────────────────────────────────────────────────────────────────────────
# Per-state admission specs
# ────────────────────────────────────────────────────────────────────────

DE = {
    "name": "Delaware Division of Corporations",
    "url": "https://icis.corp.delaware.gov/Ecorp/EntitySearch/NameSearch.aspx",
    "extra_notes": {
        "license_statute_citation": "Delaware Code Title 8 §374; Delaware Code Title 29 Chapter 100 (Delaware FOIA)",
        "license_attribution": "Delaware public corporate records under Title 8 of the Delaware Code; public records under the Delaware Freedom of Information Act (Title 29 Chapter 100). No license-restricted reuse.",
        "access_mode_reason": "ICIS public name-search form requires CAPTCHA (pnlCaptcha + captchaDiv visible in NameSearch.aspx HTML as of 2026-05-16); automated extraction structurally blocked.",
        "access_control_observed": "CAPTCHA on search form (pnlCaptcha + captchaDiv visible in NameSearch.aspx HTML)",
        "automated_access_disposition": "BLOCKED",
        "auth_shape": "no auth (public records); CAPTCHA required for search submission",
        "per_row_url_template": "https://icis.corp.delaware.gov/Ecorp/EntitySearch/Details.aspx?FileNumber={file_number}",
        "candidates_routed_to_this_state": 1,
        "candidates_routed_to_operator_manual": 1,
    },
}

CA = {
    "name": "California Secretary of State — Bizfile",
    "url": "https://bizfileonline.sos.ca.gov/search/business",
    "extra_notes": {
        "license_statute_citation": "California Government Code §6253 (California Public Records Act)",
        "license_attribution": "California public corporate records under Government Code §6253 (California Public Records Act). No license-restricted reuse.",
        "access_mode_reason": "Bizfile JSON API and HTML search are both behind Incapsula (Imperva) anti-bot wall as of 2026-05-16; CEO ratified access_mode=operator_manual_only (decision memo 2026-05-17). Per addendum §3.2, posture may relax under registered API-key access (CA_BIZFILE_API_KEY) — re-evaluate access_mode at that time.",
        "access_control_observed": "Incapsula bot-challenge (212-byte sentinel response with /_Incapsula_Resource redirect; no JSON returned to anonymous curl)",
        "automated_access_disposition": "BLOCKED",
        "auth_shape": "no auth (public records); Incapsula anti-bot wall on automated access; optional CA_BIZFILE_API_KEY documented in runguide §2.4 (not provided this session)",
        "automated_retry_conditions": "If CA SoS publishes a developer-portal credential mechanism, re-evaluate access_mode at that time.",
        "per_row_url_template": "https://bizfileonline.sos.ca.gov/search/business?filter%5Bentity_number%5D={entity_number}",
        "candidates_routed_to_this_state": 3,
        "candidates_routed_to_operator_manual": 3,
    },
}

TX = {
    "name": "Texas Secretary of State SOSDirect",
    # Per addendum §3.3 — canonical SoS URL (Texas SoS body, matches
    # "State SoS admissions" dispatch scope). Handoff's probed URL
    # (mycpa.cpa.state.tx.us/coa/search.do) targets the Texas Comptroller
    # of Public Accounts which is a different constitutional officer;
    # captured as handoff_probed_alternate_url below for audit.
    "url": "https://direct.sos.state.tx.us/",
    "extra_notes": {
        "license_statute_citation": "Texas Business Organizations Code Chapter 22 (corporate disclosure); Texas Government Code §552 (Public Information Act)",
        "license_attribution": "Texas public business records under Business Organizations Code Chapter 22; public records under the Texas Government Code §552 (Public Information Act). No license-restricted reuse.",
        "access_mode_reason": "SOSDirect returns 302 redirect to session-establishment gate; basic free entity search requires interactive cookie acceptance + per-search fee acknowledgment for some lookups, structurally blocking anonymous automation as of 2026-05-16. CEO ratified access_mode=operator_manual_only (decision memo 2026-05-17).",
        "access_control_observed": "302 redirect on anonymous GET (session-dependent; SOSDirect paid tier likely required for non-trivial queries)",
        "automated_access_disposition": "BLOCKED",
        "auth_shape": "no auth for basic search (interactive session required); paid SOSDirect tier for deeper lookups (out of scope per runguide §2.6)",
        "per_row_url_template": "TBD-discover-at-first-manual-lookup (TX SoS does not appear to expose stable per-entity URLs; operator captures search-result-detail URL at lookup time)",
        "candidates_routed_to_this_state": 1,
        "candidates_routed_to_operator_manual": 1,
        "handoff_probed_alternate_url": "https://mycpa.cpa.state.tx.us/coa/search.do",
        "handoff_probed_alternate_url_note": "Handoff source_admission_metadata.json recorded the Texas Comptroller of Public Accounts (mycpa.cpa.state.tx.us) as the actually-probed URL (302-blocked). Texas Comptroller is a different constitutional officer than the Secretary of State; this admission row uses the canonical SoS URL (direct.sos.state.tx.us) matching the dispatch admission scope. Comptroller-COA captured here for audit only.",
    },
}


def _build_notes(spec: dict[str, Any]) -> dict[str, Any]:
    notes = _base_notes()
    notes.update(spec["extra_notes"])
    return notes


def main() -> int:
    if not DB.exists():
        print(f"FATAL: DB not found at {DB}", file=sys.stderr)
        return 2

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("BEGIN IMMEDIATE")
    try:
        # Pre-flight: confirm schema_version=21
        sv = con.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0]
        if sv != SCHEMA_VERSION_AT_SESSION:
            raise RuntimeError(
                f"FATAL: schema_version mismatch — expected {SCHEMA_VERSION_AT_SESSION}, got {sv}"
            )

        inserted = []
        skipped = []
        for spec in (DE, CA, TX):
            existing = con.execute(
                "SELECT id, name FROM sources WHERE url = ?", (spec["url"],)
            ).fetchone()
            if existing is not None:
                skipped.append((existing["id"], existing["name"], spec["url"]))
                print(
                    f"NOOP: sources url already present at id={existing['id']} "
                    f"name={existing['name']!r}"
                )
                continue

            notes = _build_notes(spec)
            cur = con.execute(
                "INSERT INTO sources "
                "(name, url, source_type, tier, last_fetched_at, last_status, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    spec["name"],
                    spec["url"],
                    "primary_registry",
                    1,
                    ADMISSION_DATE_UTC,
                    LAST_STATUS,
                    json.dumps(notes, ensure_ascii=False, sort_keys=True),
                ),
            )
            new_id = cur.lastrowid
            inserted.append((new_id, spec["name"], spec["url"]))
            print(
                f"INSERTed sources id={new_id} name={spec['name']!r} "
                f"source_type=primary_registry tier=1 "
                f"last_status={LAST_STATUS} access_mode=operator_manual_only"
            )

        # Integrity check
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise RuntimeError(f"FATAL: PRAGMA integrity_check returned {ok!r}")
        print(f"PRAGMA integrity_check = {ok}")

        # FK check
        fkv = con.execute("PRAGMA foreign_key_check").fetchall()
        if fkv:
            raise RuntimeError(f"FATAL: PRAGMA foreign_key_check failed: {fkv!r}")
        print("PRAGMA foreign_key_check = ok (no violations)")

        con.commit()
        print()
        print("=== MAC-173 P5 state SoS admission committed ===")
        print(f"  inserted: {len(inserted)} row(s)")
        for row_id, name, url in inserted:
            print(f"    sources.id={row_id}  {name}  ({url})")
        if skipped:
            print(f"  skipped (already present): {len(skipped)}")
            for row_id, name, url in skipped:
                print(f"    sources.id={row_id}  {name}  ({url})")
        print()
        print("§11 #7 provenance: 3 sources rows admitted with US_STATE_PUBLIC_RECORDS license posture")
        print("§11 #8 confidence: zero identifier writes (sources-only admission)")
        print("Operator-manual queue (11 candidates) is post-integration follow-on, not this dispatch.")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
