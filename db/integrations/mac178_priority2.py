#!/usr/bin/env python3
"""MAC-178 Priority 2 — ingest 671 MAC-101 discovery rows into raw_observations.

Each row is a fccid.io-anchored discovery half of a dual-citation pair. The
citation half (FCC.gov regulatory) is deferred per `fcc_citation_deferred_queue`.
No promotion to `identifiers` — strict `crowdsourced` 50-75 band staging only
per brief §1.4 / §6.

Discipline:
- §11 #1 no fabrication: source_url + source_excerpt verbatim from staging
- §11 #3 no PII: `pii_strip_pass_version='pc1_8_b'` sentinel + harness re-run
- §11 #7 provenance: dual-citation pair_id wires this row to the queue entry
- §11 #8 no confidence drift: no `identifiers` writes; raw_observations only
- Idempotent: re-running yields 0 new rows (source_row_key UNIQUE).

source_row_key shape: `mac178:fccid_io:{fcc_id}` for scoped UPDATE/DELETE.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
STAGING = REPO / "extraction_outputs" / "fccid_io_admission" / "per_fcc_id"

FCCID_IO_SOURCE_ID = 51  # asserted from Priority 1 INSERT (verified at runtime)

PII_REGEXES = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "us_phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "person_name_in_signature_block": re.compile(
        r"(?:signed|signature|engineer|director|manager|technician|prepared by|reviewed by)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        re.IGNORECASE,
    ),
}
PII_ALLOWLIST = {
    "kev@example.com",
    "argus-research@example.com",
}


def scan_for_pii(text: str, context: str) -> list[dict]:
    findings = []
    if not text:
        return findings
    for kind, rx in PII_REGEXES.items():
        for m in rx.finditer(text):
            hit = m.group(0)
            if hit.lower() in {a.lower() for a in PII_ALLOWLIST}:
                continue
            snippet = text[max(0, m.start() - 40) : m.end() + 40].replace("\n", " ")[:200]
            findings.append(
                {"kind": kind, "value": hit, "snippet": snippet, "context": context}
            )
    return findings


def find_source_id(db: sqlite3.Connection, name: str, url: str) -> int:
    r = db.execute("SELECT id FROM sources WHERE url=? AND name=?", (url, name)).fetchone()
    if r is None:
        raise RuntimeError(f"source not found: name={name!r} url={url!r}")
    return r[0]


def get_queue_id(db: sqlite3.Connection, fcc_id: str) -> int:
    r = db.execute(
        "SELECT id FROM fcc_citation_deferred_queue WHERE fcc_id=?", (fcc_id,)
    ).fetchone()
    if r is None:
        raise RuntimeError(f"deferred queue entry missing for fcc_id={fcc_id!r}")
    return r[0]


def make_source_row_key(fcc_id: str) -> str:
    return f"mac178:fccid_io:{fcc_id}"


def make_source_excerpt(prov: dict) -> str:
    fcc = prov["fcc_id"]
    grantee = prov.get("grantee_code", "")
    product = prov.get("product_code", "")
    return (
        f"FCC ID: {fcc} (grantee={grantee}, product={product}); "
        f"fccid.io discovery row, FCC.gov citation deferred"
    )


def main() -> int:
    print(f"DB: {DB}")
    print(f"Staging dir: {STAGING}")

    provs = sorted(STAGING.glob("*/section_3_provenance.json"))
    print(f"provenance files discovered: {len(provs)}")

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    try:
        # Resolve fccid.io source id (verify Priority 1's id=51)
        fccid_io_id = find_source_id(db, "fccid.io", "https://fccid.io/")
        if fccid_io_id != FCCID_IO_SOURCE_ID:
            print(f"  WARN: fccid.io source_id={fccid_io_id} != expected {FCCID_IO_SOURCE_ID}; using observed")
        else:
            print(f"  fccid.io source_id verified = {fccid_io_id}")

        # PII harness: scan source_excerpt + source_url + raw_payload for each row
        pii_findings_total: list[dict] = []
        inserted = 0
        skipped_existing = 0
        skipped_no_queue = 0

        db.execute("BEGIN")
        for p in provs:
            prov = json.loads(p.read_text())
            fcc_id = prov["fcc_id"]
            source_row_key = make_source_row_key(fcc_id)

            existing = db.execute(
                "SELECT id FROM raw_observations WHERE source_row_key=?",
                (source_row_key,),
            ).fetchone()
            if existing:
                skipped_existing += 1
                continue

            try:
                queue_id = get_queue_id(db, fcc_id)
            except RuntimeError as e:
                print(f"  SKIP no queue entry: {e}")
                skipped_no_queue += 1
                continue

            source_url = prov["fccid_io_source_url"]
            source_excerpt = make_source_excerpt(prov)

            # PII harness pass
            findings = []
            findings.extend(scan_for_pii(source_url, f"source_url:{fcc_id}"))
            findings.extend(scan_for_pii(source_excerpt, f"source_excerpt:{fcc_id}"))
            findings.extend(scan_for_pii(json.dumps(prov), f"raw_payload:{fcc_id}"))
            if findings:
                pii_findings_total.extend(findings)
                # Per discipline: do NOT silently ingest; flag and skip
                print(f"  PII HIT on {fcc_id}: {findings}")
                skipped_no_queue += 1
                continue

            grant_ids = prov.get("opportunistic_enrichment_grant_ids") or []
            notes_obj = {
                "dual_citation_pair_id": queue_id,
                "fcc_citation_deferred_queue_id": queue_id,
                "fcc_grant_ids": grant_ids,
                "pii_strip_pass_version": "pc1_8_b",
                "degraded_mode": "degraded_b_deferred_citation",
                "fccid_io_html_sha256": prov.get("fccid_io_html_sha256"),
                "grantee_code": prov.get("grantee_code"),
                "product_code": prov.get("product_code"),
                "view_on_fcc_link_present": prov.get("view_on_fcc_link_present", False),
                "processed_at_utc_upstream": prov.get("processed_at_utc"),
                "admission_dispatch_ref": "MAC-101",
                "integration_dispatch_ref": "MAC-178",
            }
            if grant_ids:
                notes_obj["multi_grant_filing"] = len(grant_ids) > 1
                notes_obj["multi_grant_disambiguation_required"] = len(grant_ids) > 1

            db.execute(
                """
                INSERT INTO raw_observations (
                    source_id, source_url, raw_payload, candidate_identifier,
                    candidate_type, candidate_category, candidate_manufacturer,
                    source_excerpt, source_row_key, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fccid_io_id,
                    source_url,
                    json.dumps(prov, sort_keys=True),
                    fcc_id,
                    "fcc_id",
                    None,  # candidate_category — unknown until citation half resolves
                    None,  # candidate_manufacturer — grantee→canonical is §3 inference
                    source_excerpt,
                    source_row_key,
                    json.dumps(notes_obj, ensure_ascii=False, sort_keys=True),
                ),
            )
            new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Backfill the queue row's discovery_row_provisional_ids
            cur_ids_json = db.execute(
                "SELECT discovery_row_provisional_ids FROM fcc_citation_deferred_queue WHERE id=?",
                (queue_id,),
            ).fetchone()[0]
            cur_ids = json.loads(cur_ids_json) if cur_ids_json else []
            if new_id not in cur_ids:
                cur_ids.append(new_id)
                db.execute(
                    "UPDATE fcc_citation_deferred_queue SET discovery_row_provisional_ids=? WHERE id=?",
                    (json.dumps(cur_ids), queue_id),
                )

            inserted += 1

        db.commit()
        print("\nCOMMIT.")

        print("\n=== Priority 2 verification ===")
        print(f"raw_observations rows INSERTED: {inserted}")
        print(f"raw_observations rows SKIPPED (already present): {skipped_existing}")
        print(f"raw_observations rows SKIPPED (other): {skipped_no_queue}")
        print(f"PII findings (expected 0): {len(pii_findings_total)}")

        total_obs = db.execute(
            "SELECT COUNT(*) FROM raw_observations WHERE source_id=?",
            (fccid_io_id,),
        ).fetchone()[0]
        print(f"total raw_observations for fccid.io source: {total_obs}")
        rows_with_queue_link = db.execute(
            "SELECT COUNT(*) FROM fcc_citation_deferred_queue WHERE json_array_length(discovery_row_provisional_ids) > 0"
        ).fetchone()[0]
        print(f"queue rows now linked to discovery rows: {rows_with_queue_link}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
