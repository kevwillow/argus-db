"""MAC-196 integration UPDATE — apply CEO-ratified §D sequencing.

Mutates ONE row (manufacturers.id=21, Sierra Wireless):
  1. Append four aliases (dedup-before-append, case-insensitive):
       Numerex Corporation, Numerex Corp., Numerex Corp, Numerex
  2. JSON-merge §B `acquired_subsidiaries[]` entry into notes
     (upsert by legal_name == "Numerex Corp.").

Idempotent. Re-runs are no-ops (returns 0 rowchanges on second invocation).

Verification: prints pre/post snapshots; exits non-zero on any unexpected drift.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db" / "argus.db"
TARGET_MFR_ID = 21
TARGET_CANONICAL = "Sierra Wireless"

NEW_ALIASES = ["Numerex Corporation", "Numerex Corp.", "Numerex Corp", "Numerex"]

ACQUIRED_SUBSIDIARY_ENTRY = {
    "legal_name": "Numerex Corp.",
    "common_brand_name": "Numerex Corporation",
    "state_of_incorporation": "Pennsylvania",
    "irs_ein": "11-2948749",
    "sec_cik": "0000870753",
    "sec_commission_file_number": "000-22920",
    "last_headquarters": "400 Interstate North Parkway SE, Suite 1350, Atlanta, GA 30339",
    "sic_code": "3669",
    "sic_description": "Communications Equipment, NEC",
    "merger_agreement_date_utc": "2017-08-02",
    "merger_closing_date_utc": "2017-12-07",
    "merger_consideration_summary": (
        "stock-for-stock; 0.1800 Sierra Wireless common shares per Numerex Class A "
        "Common share; 3,588,784 SW shares total"
    ),
    "merger_sub_entity": "Wireless Acquisition Sub, Inc. (wholly-owned Sierra Wireless subsidiary)",
    "post_merger_status": "wholly-owned subsidiary of Sierra Wireless, Inc.",
    "deregistration_form": "15-12G",
    "deregistration_filed_utc": "2017-12-18",
    "deregistration_accession": "0001193125-17-371533",
    "primary_citation": {
        "filing_type": "8-K",
        "accession": "0001193125-17-364672",
        "filed_utc": "2017-12-08",
        "report_date_utc": "2017-12-07",
        "primary_document": "d503004d8k.htm",
        "source_url": "https://www.sec.gov/Archives/edgar/data/870753/000119312517364672/d503004d8k.htm",
        "local_capture": "_numerex_admission/8k_2017-12-08_2026-05-20T20-24-38Z.htm",
    },
    "submissions_citation": {
        "source_url": "https://data.sec.gov/submissions/CIK0000870753.json",
        "local_capture": "_numerex_admission/edgar_submissions_CIK870753_2026-05-20T20-24-29Z.json",
    },
    "fcc_eas_grantee_code_under_subsidiary_name": None,
    "fcc_eas_grantee_lookup_attestation": (
        "0 rows in fcc_grantees (sid=7) matching grantee_name LIKE '%Numerex%' — "
        "subsidiary does not hold a grantee code under its own legal name; "
        "downstream FCC filings inferred to roll up under Sierra Wireless's "
        "LL9/N7N/PNF/QQL/TWV grantee cluster (per §7.2 surface)."
    ),
    "research_log_ref": "_numerex_admission/numerex_research_log.md",
    "staged_proposal_ref": "_numerex_admission/numerex_staged_for_ratification.md",
    "integration_dispatch": "MAC-196",
    "integration_applied_at_utc": "2026-05-20T20:34:00Z",
}


def alias_dedup_append(existing_csv: str, new: list[str]) -> tuple[str, list[str]]:
    """Append aliases not already present (case-insensitive token match)."""
    existing_tokens = {t.strip().lower() for t in existing_csv.split(",")}
    to_append = [a for a in new if a.strip().lower() not in existing_tokens]
    if not to_append:
        return existing_csv, []
    return existing_csv + "," + ",".join(to_append), to_append


def notes_merge(existing_notes_json: str, entry: dict) -> tuple[str, str]:
    """JSON-merge acquired_subsidiaries[] entry; idempotent by legal_name."""
    parsed = json.loads(existing_notes_json) if existing_notes_json else {}
    subs = parsed.get("acquired_subsidiaries") or []
    key = entry["legal_name"]
    replaced = False
    for i, e in enumerate(subs):
        if e.get("legal_name") == key:
            subs[i] = entry
            replaced = True
            break
    if not replaced:
        subs.append(entry)
    parsed["acquired_subsidiaries"] = subs
    action = "replaced" if replaced else "appended"
    return json.dumps(parsed), action


def main() -> int:
    if not DB_PATH.exists():
        print(f"FATAL: DB not at {DB_PATH}", file=sys.stderr)
        return 2

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    pre = cur.execute(
        "SELECT id, canonical_name, aliases, notes FROM manufacturers WHERE id=?",
        (TARGET_MFR_ID,),
    ).fetchone()
    if not pre:
        print(f"FATAL: no manufacturers row at id={TARGET_MFR_ID}", file=sys.stderr)
        return 3
    if pre["canonical_name"] != TARGET_CANONICAL:
        print(
            f"FATAL: id={TARGET_MFR_ID} canonical_name={pre['canonical_name']!r} "
            f"(expected {TARGET_CANONICAL!r})",
            file=sys.stderr,
        )
        return 4

    print(f"=== PRE-UPDATE row id={TARGET_MFR_ID} ({pre['canonical_name']}) ===")
    print(f"aliases: {pre['aliases']!r}")
    pre_notes_parsed = json.loads(pre["notes"]) if pre["notes"] else {}
    print(f"notes top-level keys: {list(pre_notes_parsed.keys())}")
    print(
        f"acquired_subsidiaries present in notes: "
        f"{'acquired_subsidiaries' in pre_notes_parsed}"
    )

    new_aliases_csv, appended = alias_dedup_append(pre["aliases"] or "", NEW_ALIASES)
    new_notes_json, notes_action = notes_merge(pre["notes"] or "{}", ACQUIRED_SUBSIDIARY_ENTRY)

    print()
    print(f"aliases append plan: {appended}")
    print(f"notes acquired_subsidiaries action: {notes_action}")

    if not appended and notes_action == "replaced":
        already_same = (
            new_aliases_csv == (pre["aliases"] or "")
            and json.loads(new_notes_json) == pre_notes_parsed
        )
        if already_same:
            print()
            print("IDEMPOTENT NO-OP — row already carries the MAC-196 mutation.")
            return 0

    cur.execute(
        "UPDATE manufacturers SET aliases = ?, notes = ? WHERE id = ?",
        (new_aliases_csv, new_notes_json, TARGET_MFR_ID),
    )
    rowchanges = cur.rowcount
    con.commit()

    post = cur.execute(
        "SELECT id, canonical_name, aliases, notes FROM manufacturers WHERE id=?",
        (TARGET_MFR_ID,),
    ).fetchone()
    print()
    print(f"=== POST-UPDATE row id={TARGET_MFR_ID} (rowchanges={rowchanges}) ===")
    print(f"aliases: {post['aliases']!r}")
    post_notes_parsed = json.loads(post["notes"])
    print(f"notes top-level keys: {list(post_notes_parsed.keys())}")
    subs = post_notes_parsed.get("acquired_subsidiaries") or []
    print(f"acquired_subsidiaries length: {len(subs)}")
    if subs:
        print(f"acquired_subsidiaries[0].legal_name: {subs[0].get('legal_name')}")
        print(
            f"acquired_subsidiaries[0].primary_citation.accession: "
            f"{subs[0].get('primary_citation', {}).get('accession')}"
        )

    total = cur.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
    print()
    print(f"manufacturers row count (must remain 51): {total}")
    if total != 51:
        print("FATAL: manufacturers row count drift", file=sys.stderr)
        return 5

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
