#!/usr/bin/env python3
"""MAC-178 Priority 1 — apply 0022 migration, INSERT 2 sources, load deferred queue.

Idempotent on re-run: migration is INSERT OR IGNORE; sources are INSERT OR IGNORE
on URL UNIQUE; queue entries are INSERT OR IGNORE on fcc_id UNIQUE. Re-running
yields zero new rows.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
MIGRATION = REPO / "db" / "migrations" / "0022_fcc_citation_deferred_queue.sql"
QUEUE_JSON = REPO / "extraction_outputs" / "fccid_io_admission" / "fcc_citation_deferred_queue.json"

SOURCES = [
    {
        "name": "fccid.io",
        "url": "https://fccid.io/",
        "source_type": "crowdsourced",
        "tier": 2,
        "notes_obj": {
            "tier": 2,
            "license": "NO_LICENSE_DECLARED",
            "license_attribution": (
                "fccid.io is a third-party aggregator of US FCC Equipment "
                "Authorization System filings. No upstream license declared; "
                "facts extracted under Feist v. Rural Telephone (499 U.S. 340) "
                "facts-not-copyrightable doctrine. Compilation arrangement is "
                "not republished."
            ),
            "upstream_license_posture": "NO_LICENSE_DECLARED",
            "access_mode": "automated_html_parse",
            "rate_limit_self_enforced_req_per_sec": 1,
            "admission_runguide": "fccid_io_admission_runguide.md",
            "admission_dispatch_ref": "MAC-101",
            "admission_date_utc": "2026-05-18T04:27:14Z",
            "patch_cycles_applied": [1, 1.6, 1.7, "1.8.B"],
        },
    },
    {
        "name": "FCC Equipment Authorization System — Filings",
        "url": "https://apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm",
        "source_type": "regulatory",
        "tier": 1,
        "notes_obj": {
            "tier": 1,
            "license": "PUBLIC_DOMAIN",
            "license_attribution": (
                "FCC Equipment Authorization System filings are US government "
                "work product; not copyrightable per 17 USC §105."
            ),
            "upstream_license_posture": "PUBLIC_DOMAIN",
            "access_mode": "automated_html_parse",
            "rate_limit_self_enforced_req_per_sec": 2,
            "admission_runguide": "fccid_io_admission_runguide.md",
            "admission_dispatch_ref": "MAC-101",
            "admission_date_utc": "2026-05-18T04:27:14Z",
            "distinct_from": "FCC EAS grantee registrations (sources 1/2/3/7)",
            "degraded_mode_admission_posture": (
                "When FCC.gov direct is unreachable at run-time, this source "
                "row is still admitted (the source EXISTS); deferred-citation "
                "rows accumulate against it pending the validator's "
                "asynchronous re-citation pass. Wave 2026-05-17 admitted this "
                "source under degraded mode."
            ),
        },
    },
]


def apply_migration(db: sqlite3.Connection) -> int:
    current = db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    if current >= 22:
        print(f"  schema_version={current} ≥ 22 — migration already applied; skipping")
        return current
    sql = MIGRATION.read_text()
    db.executescript(sql)
    new = db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    print(f"  schema_version: {current} → {new}")
    return new


def insert_sources(db: sqlite3.Connection) -> dict[str, tuple[int, bool]]:
    """Returns {name: (source_id, was_new)} for each source row."""
    out: dict[str, tuple[int, bool]] = {}
    for s in SOURCES:
        notes_json = json.dumps(s["notes_obj"], ensure_ascii=False, sort_keys=True)
        # SQLite UNIQUE on url is the natural-key gate
        existing = db.execute(
            "SELECT id FROM sources WHERE url = ?", (s["url"],)
        ).fetchone()
        if existing:
            out[s["name"]] = (existing[0], False)
            print(f"  source already exists: {s['name']} → id={existing[0]}")
            continue
        cur = db.execute(
            """
            INSERT INTO sources (name, url, source_type, tier, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (s["name"], s["url"], s["source_type"], s["tier"], notes_json),
        )
        new_id = cur.lastrowid
        out[s["name"]] = (new_id, True)
        print(f"  INSERTED source: {s['name']} → id={new_id} ({s['source_type']})")
    return out


def load_queue(db: sqlite3.Connection) -> tuple[int, int]:
    data = json.loads(QUEUE_JSON.read_text())
    entries = data["entries"]
    inserted = 0
    skipped = 0
    for e in entries:
        existing = db.execute(
            "SELECT id FROM fcc_citation_deferred_queue WHERE fcc_id = ?",
            (e["fcc_id"],),
        ).fetchone()
        if existing:
            skipped += 1
            continue
        opp = e.get("opportunistic_enrichment") or {}
        grant_ids = opp.get("fcc_grant_ids") or []
        db.execute(
            """
            INSERT INTO fcc_citation_deferred_queue (
                fcc_id,
                fccid_io_source_url,
                fccid_io_html_sha256,
                fcc_gov_unreachable_reason,
                deferred_at_utc,
                discovery_row_provisional_ids,
                expected_citation_row_emission,
                opportunistic_enrichment,
                fcc_grant_ids_csv
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                e["fcc_id"],
                e["fccid_io_source_url"],
                e["fccid_io_html_sha256"],
                e["fcc_gov_unreachable_reason"],
                e["deferred_at_utc"],
                json.dumps(e.get("discovery_row_provisional_ids") or []),
                e.get("expected_citation_row_emission"),
                json.dumps(opp, ensure_ascii=False, sort_keys=True),
                ",".join(grant_ids) if grant_ids else None,
            ),
        )
        inserted += 1
    return inserted, skipped


def main() -> int:
    print(f"DB: {DB}")
    print(f"Migration: {MIGRATION.name}")
    print(f"Queue JSON: {QUEUE_JSON} ({QUEUE_JSON.stat().st_size:,} bytes)")

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN")
        print("\n[1] apply migration 0022_fcc_citation_deferred_queue")
        apply_migration(db)

        print("\n[2] INSERT 2 sources rows (fccid.io + FCC EAS Filings)")
        sources_map = insert_sources(db)

        print("\n[3] load fcc_citation_deferred_queue entries")
        ins, skip = load_queue(db)
        print(f"  inserted: {ins}; skipped (already present): {skip}")

        db.commit()
        print("\nCOMMIT.")

        # Post-commit verification
        print("\n=== verification ===")
        print(
            "schema_version max:",
            db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0],
        )
        print(
            "sources count:",
            db.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
        )
        for name, (sid, was_new) in sources_map.items():
            r = db.execute(
                "SELECT id, source_type, tier FROM sources WHERE id=?", (sid,)
            ).fetchone()
            print(f"  source[{r['id']}]: {name} ({r['source_type']}, tier={r['tier']}) — was_new={was_new}")
        print(
            "fcc_citation_deferred_queue rows:",
            db.execute("SELECT COUNT(*) FROM fcc_citation_deferred_queue").fetchone()[0],
        )
        print(
            "  with fcc_grant_ids:",
            db.execute(
                "SELECT COUNT(*) FROM fcc_citation_deferred_queue WHERE fcc_grant_ids_csv IS NOT NULL"
            ).fetchone()[0],
        )
        print(
            "  pending (promoted_at IS NULL):",
            db.execute(
                "SELECT COUNT(*) FROM fcc_citation_deferred_queue WHERE promoted_at IS NULL"
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
