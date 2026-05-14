"""MAC-105 / MAC-108 — Phase-1 mapper URL-template rerun under SAR-13 §S.2.

Rewrites `raw_observations.source_url` for the 199-row source-url-direct-violation
cohort from the bare-repo + JSON-key-anchor form to the SAR-13 §S.2 mandatory
`/blob/<sha>/<path>#<anchor>` form. Commit SHAs are recovered from preserved
artifact manifests under `raw/wave_a/<slug>/<run-timestamp>.json` (the dispatch
description's claim that `notes.source_commit_sha` was already populated is
inaccurate — actual `notes` rows have no such key; SHA truth lives in the
artifact manifest captured at extraction time).

Per-source transactions mirror MAC-103 / MAC-99 / MAC-102 batching. Idempotent:
re-running after success leaves the cohort at 0 affected rows.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "db" / "argus.db"

DISPATCH = "MAC-105"

SOURCES = {
    27: {
        "repo_url": "https://github.com/cyber-defence-campus/RemoteIDReceiver",
        "sha": "6db79e69ee1e3da3862d954cc86ad5c310fbc9e4",
        "sha_provenance": "raw/wave_a/cyber-defence-campus_RemoteIDReceiver/2026-05-11T01-21-41.json::target.head_sha",
    },
    41: {
        "repo_url": "https://github.com/GainSec/anti-crime-ecosystem-research",
        "sha": "d2468adb8b62cf62f7352510da00d6e8c4623f7c",
        "sha_provenance": "raw/wave_a/GainSec_anti-crime-ecosystem-research/2026-05-11T05-31-51Z.json::run_metadata.commit_sha",
    },
    42: {
        "repo_url": "https://github.com/GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose",
        "sha": "1ee8e320de441e80e05c48c1410250761429d9c1",
        "sha_provenance": "raw/wave_a/GainSec_flock-safety-falcon-sparrow-alpr-edl-firehose/20260511T053109Z.json::run_metadata.commit_sha",
    },
    43: {
        "repo_url": "https://github.com/RUB-SysSec/DroneSecurity",
        "sha": "9ff819843bee48fb140a0704ec78aff757896dea",
        "sha_provenance": "raw/wave_a/RUB-SysSec_DroneSecurity/2026-05-11T05-21-38Z.json::source.head_sha",
    },
}

HOLD_REASON_VALUE = "source_url_direct_violation"
HOLD_DISPOSITION_VALUE = "hold_source_url_direct_violation"
RETRIAGE_DISPOSITION_VALUE = "pending_validator_retriage_mac107"


def rewrite_url(existing_url: str, repo_url: str, sha: str) -> str:
    """Splice the existing fragment (if any) into `<repo>/blob/<sha>/README.md#<frag>`.

    Per SAR-13 §S.2: mandatory `/blob/<sha>/<path>#<anchor>` template. None of the
    cohort URLs are code-line-anchored (no `L<digits>` fragments), so all map to
    the README.md content target. Bare repo URLs (src=43) map to README.md with
    no anchor — still §S.2-compliant because the template's anchor segment is
    optional when no original anchor exists.
    """
    parts = urlsplit(existing_url)
    fragment = parts.fragment
    base = f"{repo_url}/blob/{sha}/README.md"
    if fragment:
        return f"{base}#{fragment}"
    return base


def update_one_source(conn: sqlite3.Connection, source_id: int, meta: dict, ts_iso: str) -> int:
    repo_url = meta["repo_url"]
    sha = meta["sha"]
    sha_provenance = meta["sha_provenance"]
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, source_url, notes FROM raw_observations WHERE source_id = ?",
        (source_id,),
    ).fetchall()
    blob_prefix = f"{repo_url}/blob/{sha}/"
    n_updated = 0
    for rid, source_url, notes_str in rows:
        notes = json.loads(notes_str)
        needs_work = (
            notes.get("hold_reason") == HOLD_REASON_VALUE
            or notes.get("disposition") == HOLD_DISPOSITION_VALUE
        )
        if not needs_work:
            continue
        if not source_url.startswith(blob_prefix):
            new_url = rewrite_url(source_url, repo_url, sha)
        else:
            new_url = source_url
        notes.pop("hold_reason", None)
        if notes.get("disposition") == HOLD_DISPOSITION_VALUE:
            notes["disposition"] = RETRIAGE_DISPOSITION_VALUE
        notes["mapper_rerun_at"] = ts_iso
        notes["mapper_rerun_dispatch"] = DISPATCH
        notes["source_commit_sha"] = sha
        notes["source_commit_sha_provenance"] = sha_provenance
        cur.execute(
            "UPDATE raw_observations SET source_url = ?, notes = ? WHERE id = ?",
            (new_url, json.dumps(notes), rid),
        )
        n_updated += 1
    return n_updated


def main() -> int:
    if not DB_PATH.exists():
        print(f"FATAL: {DB_PATH} not found", file=sys.stderr)
        return 2
    ts_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = sqlite3.connect(DB_PATH)
    try:
        pre_total = conn.execute(
            "SELECT COUNT(*) FROM raw_observations WHERE notes LIKE ?",
            (f"%{HOLD_REASON_VALUE}%",),
        ).fetchone()[0]
        print(f"pre_rerun_violation_count: {pre_total}")
        grand_total = 0
        for source_id in sorted(SOURCES):
            meta = SOURCES[source_id]
            conn.execute("BEGIN")
            try:
                n = update_one_source(conn, source_id, meta, ts_iso)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            grand_total += n
            print(f"source_id={source_id}: rewrote {n} rows (sha={meta['sha'][:12]}...)")
        post_total = conn.execute(
            "SELECT COUNT(*) FROM raw_observations WHERE notes LIKE ?",
            (f"%{HOLD_REASON_VALUE}%",),
        ).fetchone()[0]
        print(f"post_rerun_violation_count: {post_total}")
        print(f"grand_total_rewritten: {grand_total}")
        if post_total != 0:
            print("FATAL: post_rerun_violation_count != 0", file=sys.stderr)
            return 3
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
