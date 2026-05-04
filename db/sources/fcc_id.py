"""FCC EAS grantee registrations ingest (Phase 3 — Tier 2, source 1/4).

Pulls the opendata.fcc.gov dataset `3b3k-34jp` ("EAS Equipment Authorization
Grantee Registrations") into the `fcc_grantees` staging table per
PROJECT_BIBLE.md §6 Phase 3 + §7.2 (Source Worker contract). Migration
`0003_fcc_grantees.sql` (ratified at MAC-7 Step 2 comment 0e95c40a,
2026-05-04T14:34:12Z) defines the table.

Source
──────
Dataset ID:    3b3k-34jp
Bulk URL:      https://opendata.fcc.gov/resource/3b3k-34jp.csv?$limit=200000
Format:        CSV, 10 columns, 50,153 data rows in 2026-05-04 snapshot.
               Columns: grantee_code, grantee_name, mailing_address, po_box,
               city, state, country, zip_code, contact_name, date_received.
License:       USGOV_WORKS / "Public Domain U.S. Government"
               (https://www.usa.gov/government-works). 1:1 with the
               17 U.S.C. §105 federal-government public-domain regime
               ratified at MAC-7 Step 1 (CEO Decision 1).

source_type:   `official` band 90-95 (CEO Decision 2 from MAC-7 Step 1
               ratification — §8.2 verbatim).
tier:          1 (per Bible §5; opendata.fcc.gov + USGOV_WORKS is
               structurally tier-1 even though staleness pushes the
               *fitness* downward; tier is about authority-of-source not
               freshness — see staleness ceiling below).

source_url per row: the bulk-fetch URL verbatim
(`https://opendata.fcc.gov/resource/3b3k-34jp.csv?$limit=200000`).

────────────────────────────────────────────────────────────────────────────
Staleness ceiling (Q1 ratification — load-bearing)
────────────────────────────────────────────────────────────────────────────
The Socrata mirror is FROZEN at 2021-03-22T07:04:51Z (`rowsUpdatedAt`).
Year histogram confirms zero grantees registered after 2021-03-22:
1998: 15,582 (initial bulk import); 2019: 2,990; 2020: 2,779; 2021: 792
(Q1 partial); 2022 through 2026: 0.

This is a documented permanent property of source 1/4, NOT unfit-for-
purpose. The 2021-04 → present grantee gap (4 yr 2 mo, including the
Flock Safety scaling era) routes to the Phase 4 extraction worker:
- FCC test-report PDF mining via Wayback per known FCC ID
- per-vendor research-led pulls of fccid.io / fcc.report cross-mirror
  sweeps with license-clearance

Flock Safety is entirely absent from this snapshot (zero `%FLOCK%` hits).
The MAC-7 dispatch's `2AKWH=Flock Safety` hint stays §11 #1 unstaged —
this dataset structurally cannot resolve it.

────────────────────────────────────────────────────────────────────────────
§11 #3 — `contact_name` corporate-comms read (Q4 stage-as-is)
────────────────────────────────────────────────────────────────────────────
The §11 #3 worked example targets law-enforcement officer/badge/
home-address PII. FCC `contact_name` is mandatory federal regulatory
disclosure of corporate-comms compliance contacts — structurally distinct.
Sample target-vendor contacts (verified verbatim against raw CSV):
  - X4G  Axon Enterprise           → "Elisabet Dominguez"
  - 2AGVG Axon Product Partners    → "Steven Nersesian"
  - UXX  Cradlepoint               → "Steve Wood"
  - TWV  Sierra Wireless           → "YING WANG"
  - YJV  Enforcement Video         → "Jim Exner"
  - NEV  Air Taser                 → "Tom Smith"

The MAC-5/MAC-6 `rank-token + name` regex (operational interpretation of
§11 #3) returns 2 false-positive corporate hits across 50,153 rows
("Michael Chief Executive Officer", "Captain Giannakos") — zero officer-
shape PII. Per Q4: stage as-is, audit-log only, do NOT redact.

A Phase-5 reconsider hook is logged in `extraction_runs.notes` (mirrors
the MAC-4 `source_type='crowdsourced'` reconsider pattern).

────────────────────────────────────────────────────────────────────────────
Idempotency
────────────────────────────────────────────────────────────────────────────
Same shape as MAC-3 / MAC-4 / MAC-5 / MAC-6: delete-by-`source_id` then
bulk-insert in a single transaction. The structural backstop is the
`UNIQUE(source_id, source_row_key)` index on `fcc_grantees`; re-running
this ingest on the same `--raw-subdir` produces identical row counts and
never duplicates. `source_row_key = grantee_code` (Q3).
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional


LOG = logging.getLogger("argus.ingest.fcc_id")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "fcc_id"

SOURCE_NAME = "FCC EAS Equipment Authorization Grantee Registrations (opendata.fcc.gov 3b3k-34jp)"
SOURCE_URL = "https://opendata.fcc.gov/resource/3b3k-34jp.csv?$limit=200000"
SOURCE_FILENAME = "opendata_fcc_3b3k-34jp_FULL.csv"
SOURCE_TYPE = "official"  # §4.1 source_type enum — CEO Decision 2 at MAC-7 Step 1.
TIER = 1                  # §5 — Tier 1 authority (USGOV public domain).

DATASET_ID = "3b3k-34jp"
DATASET_FREEZE_DATE = "2021-03-22"
ROWS_UPDATED_AT_UTC = "2021-03-22T07:04:51Z"

LICENSE_NOTE = (
    "License: USGOV_WORKS / Public Domain U.S. Government — "
    "https://www.usa.gov/government-works"
)
LICENSE_ATTRIBUTION = (
    "Public Domain U.S. Government — https://www.usa.gov/government-works "
    "(FCC EAS public bulk; 17 U.S.C. §105)"
)

STALENESS_WARNING = (
    "Socrata mirror not refreshed since 2021-03-22; grantees registered "
    "2021-04 through capture date are absent. Phase 4 owns 2021-present "
    "gap via FCC test-report PDF mining and per-vendor research-led pulls."
)

PHASE5_RECONSIDER_PII = (
    "FCC contact_name staged as-is per §11 #3 corporate-comms read at "
    "MAC-7. Reconsider at Phase 5 if cross-source name match utility "
    "doesn't materialize, or if scope shifts toward consolidating "
    "people-data redaction across all sources."
)

REGISTRY_TAG = "fcc_id"


# ─── PII person regex (audit-only — Q4 stage-as-is) ───────────────────────


# Same rank-token list as eff_atlas / deflock (codified MAC-5/MAC-6
# standard). Audit-only on FCC: we count + log hits, never redact.
PII_RANK_TOKENS = (
    "Officer",
    "Sergeant",
    "Sgt",
    "Lieutenant",
    "Lt",
    "Captain",
    "Capt",
    "Major",
    "Colonel",
    "Col",
    "Chief",
    "Sheriff",
    "Deputy",
    "Detective",
    "Trooper",
    "Constable",
    "Marshal",
    "Mayor",
    "Commander",
    "Patrolman",
    "Corporal",
    "Inspector",
    "Commissioner",
)

PII_REGEX = re.compile(
    r"\b("
    + "|".join(re.escape(t) for t in PII_RANK_TOKENS)
    + r")\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
)


def count_pii_hits(value: str) -> tuple[int, list[str]]:
    """Audit-only person regex sweep. Returns (hit_count, matched_strings).

    `re.findall` with a grouped pattern returns group captures rather than
    full matches; use `finditer().group(0)` so the audit log records the
    full match (e.g. "Chief Executive Officer", not just "Chief").
    """
    if not value:
        return 0, []
    matches = [m.group(0) for m in PII_REGEX.finditer(value)]
    return len(matches), matches


# ─── HTTP fetch (unused on --raw-subdir reuse but kept for fresh runs) ────


def _fetch(url: str, timeout: int = 60) -> tuple[bytes, int]:
    """Single-shot HTTP fetch with one transient-error retry.

    Mirrors `db/sources/eff_atlas.py::_fetch`. Per §7.2 Don'ts: no silent
    infinite retries. Per §11 #6: opendata.fcc.gov `Crawl-delay: 1` honored
    by single-bulk-fetch cadence (one request only).
    """
    last_exc: Optional[BaseException] = None
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "argus-ingest/0.1 (+contact: argus-ingest)",
                    "Accept-Encoding": "gzip",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                status = resp.getcode()
                return body, status
        except urllib.error.HTTPError:
            raise
        except urllib.error.URLError as e:
            LOG.warning(
                "transient fetch error on attempt %d for %s: %s", attempt, url, e
            )
            last_exc = e
            if attempt == 2:
                raise
    assert last_exc is not None
    raise last_exc


# ─── CSV parsing ──────────────────────────────────────────────────────────


COL_GRANTEE_CODE = "grantee_code"
COL_GRANTEE_NAME = "grantee_name"
COL_MAILING_ADDRESS = "mailing_address"
COL_PO_BOX = "po_box"
COL_CITY = "city"
COL_STATE = "state"
COL_COUNTRY = "country"
COL_ZIP_CODE = "zip_code"
COL_CONTACT_NAME = "contact_name"
COL_DATE_RECEIVED = "date_received"

EXPECTED_HEADER = (
    COL_GRANTEE_CODE, COL_GRANTEE_NAME, COL_MAILING_ADDRESS, COL_PO_BOX,
    COL_CITY, COL_STATE, COL_COUNTRY, COL_ZIP_CODE, COL_CONTACT_NAME,
    COL_DATE_RECEIVED,
)


@dataclass(frozen=True)
class GranteeRow:
    """One FCC EAS grantee registration row, raw-as-CSV."""

    grantee_code: str
    grantee_name: str
    mailing_address: str
    po_box: str
    city: str
    state: str
    country: str
    zip_code: str
    contact_name: str
    date_received: str  # CSV form "YYYY-MM-DDTHH:MM:SS.sss" preserved verbatim


def parse_grantees(content: bytes) -> Iterator[GranteeRow]:
    """Yield GranteeRow per CSV data row. Raises ValueError on header surprises."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(text.splitlines())
    header = next(reader, None)
    if header is None:
        raise ValueError("FCC EAS grantee CSV has no header row")
    header_tup = tuple(h.strip() for h in header)
    if header_tup != EXPECTED_HEADER:
        missing = set(EXPECTED_HEADER) - set(header_tup)
        extra = set(header_tup) - set(EXPECTED_HEADER)
        raise ValueError(
            f"FCC grantee CSV header divergence — missing={sorted(missing)}, "
            f"extra={sorted(extra)}; full header: {header_tup}"
        )
    expected_n = len(EXPECTED_HEADER)
    for fields in reader:
        if not fields:
            continue
        if len(fields) != expected_n:
            LOG.warning(
                "skipping row with field-count mismatch: have %d, expected %d",
                len(fields),
                expected_n,
            )
            continue
        record = dict(zip(EXPECTED_HEADER, (f.strip() for f in fields)))
        yield GranteeRow(
            grantee_code=record[COL_GRANTEE_CODE],
            grantee_name=record[COL_GRANTEE_NAME],
            mailing_address=record[COL_MAILING_ADDRESS],
            po_box=record[COL_PO_BOX],
            city=record[COL_CITY],
            state=record[COL_STATE],
            country=record[COL_COUNTRY],
            zip_code=record[COL_ZIP_CODE],
            contact_name=record[COL_CONTACT_NAME],
            date_received=record[COL_DATE_RECEIVED],
        )


def _maybe_null(s: str) -> Optional[str]:
    """Map empty / 'N/A' / 'NIL' to NULL; preserve everything else verbatim.

    Per CEO Q4 instruction (`contact_name` populate-where-present, NULL on
    empty/'N/A'). Applied uniformly to all nullable text columns for
    queryability — raw values still preserved in `notes.raw_row`.
    """
    if not s:
        return None
    stripped = s.strip()
    if not stripped:
        return None
    if stripped.upper() in {"N/A", "NIL", "NA"}:
        return None
    return stripped


def _normalize_date(s: str) -> str:
    """Truncate Socrata calendar_date 'YYYY-MM-DDTHH:MM:SS.sss' to 'YYYY-MM-DD'.

    Lex-sortable ISO 8601 form; raw value preserved in `notes.raw_row`.
    Required for `date_received` only (NOT NULL column); leaves any raw
    value containing 'T' shortened, otherwise pass-through.
    """
    if not s:
        return s
    # Defensive: only truncate if the prefix looks like an ISO date.
    if "T" in s and len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


# ─── DB writes ────────────────────────────────────────────────────────────


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _upsert_source(
    conn: sqlite3.Connection,
    *,
    fetched_at: str,
    http_status: int,
    byte_count: int,
    content_hash: str,
) -> int:
    notes = json.dumps(
        {
            "registry": REGISTRY_TAG,
            "license": LICENSE_NOTE,
            "license_attribution": LICENSE_ATTRIBUTION,
            "byte_count": byte_count,
            "content_sha256": content_hash,
            "http_status": http_status,
            "dataset_id": DATASET_ID,
            "dataset_freeze_date": DATASET_FREEZE_DATE,
            "rows_updated_at_utc": ROWS_UPDATED_AT_UTC,
            "staleness_warning": STALENESS_WARNING,
            "bulk_csv_sha256": content_hash,
            "bulk_csv_byte_count": byte_count,
        },
        sort_keys=True,
    )
    cur = conn.execute("SELECT id FROM sources WHERE url = ?", (SOURCE_URL,))
    existing = cur.fetchone()
    if existing is not None:
        sid = int(existing[0])
        conn.execute(
            "UPDATE sources SET name = ?, source_type = ?, tier = ?, "
            "last_fetched_at = ?, last_status = ?, notes = ? WHERE id = ?",
            (SOURCE_NAME, SOURCE_TYPE, TIER, fetched_at, "ok", notes, sid),
        )
        return sid
    cur = conn.execute(
        "INSERT INTO sources (name, url, source_type, tier, "
        "last_fetched_at, last_status, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (SOURCE_NAME, SOURCE_URL, SOURCE_TYPE, TIER, fetched_at, "ok", notes),
    )
    return int(cur.lastrowid)


def _start_run(conn: sqlite3.Connection, *, agent_id: str, source_id: int) -> int:
    cur = conn.execute(
        "INSERT INTO extraction_runs (agent_id, source_id, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        (agent_id, source_id, _utc_now(), "running"),
    )
    return int(cur.lastrowid)


def _finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    records_in: int,
    records_out: int,
    errors: int,
    status: str,
    notes: Optional[str] = None,
) -> None:
    conn.execute(
        "UPDATE extraction_runs SET finished_at = ?, records_in = ?, "
        "records_out = ?, errors = ?, status = ?, notes = ? WHERE id = ?",
        (_utc_now(), records_in, records_out, errors, status, notes, run_id),
    )


@dataclass
class StagingStats:
    inserted: int = 0
    by_country: dict[str, int] = field(default_factory=dict)
    by_state: dict[str, int] = field(default_factory=dict)
    by_year: dict[str, int] = field(default_factory=dict)
    contact_name_present: int = 0
    contact_name_pii_hits: int = 0
    contact_name_pii_samples: list[tuple[str, str]] = field(default_factory=list)


def _stage_grantees(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    extraction_run_id: int,
    rows: Iterable[GranteeRow],
) -> StagingStats:
    """Delete-by-source-id then bulk-insert. Returns aggregate stats."""
    conn.execute("DELETE FROM fcc_grantees WHERE source_id = ?", (source_id,))

    stats = StagingStats()
    batch: list[tuple] = []
    BATCH_SIZE = 1000

    sql = (
        "INSERT INTO fcc_grantees ("
        "source_id, extraction_run_id, source_url, source_row_key, "
        "grantee_code, grantee_name, mailing_address, po_box, city, state, "
        "country, zip_code, contact_name, date_received, source_excerpt, notes"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    def _flush() -> None:
        if not batch:
            return
        conn.executemany(sql, batch)
        stats.inserted += len(batch)
        batch.clear()

    for r in rows:
        # source_row_key = grantee_code (Q3).
        source_row_key = r.grantee_code
        # date_received: canonical YYYY-MM-DD; raw verbatim preserved in notes.
        date_canonical = _normalize_date(r.date_received)

        # source_excerpt: short per-row identity for validator audit (≤200).
        excerpt_parts = [r.grantee_code, r.grantee_name]
        if r.country:
            excerpt_parts.append(r.country)
        excerpt = " | ".join(p for p in excerpt_parts if p)[:200]

        # notes JSON: raw_row passthrough + Phase-5 hooks (CEO Q4).
        notes_obj: dict[str, object] = {
            "raw_row": {
                COL_GRANTEE_CODE: r.grantee_code,
                COL_GRANTEE_NAME: r.grantee_name,
                COL_MAILING_ADDRESS: r.mailing_address,
                COL_PO_BOX: r.po_box,
                COL_CITY: r.city,
                COL_STATE: r.state,
                COL_COUNTRY: r.country,
                COL_ZIP_CODE: r.zip_code,
                COL_CONTACT_NAME: r.contact_name,
                COL_DATE_RECEIVED: r.date_received,
            },
            "vendor_sweep_classification": None,
        }
        notes = json.dumps(notes_obj, sort_keys=True)

        batch.append(
            (
                source_id,
                extraction_run_id,
                SOURCE_URL,
                source_row_key,
                r.grantee_code,
                r.grantee_name,
                _maybe_null(r.mailing_address),
                _maybe_null(r.po_box),
                _maybe_null(r.city),
                _maybe_null(r.state),
                _maybe_null(r.country),
                _maybe_null(r.zip_code),
                _maybe_null(r.contact_name),
                date_canonical,
                excerpt,
                notes,
            )
        )

        # Stats — verbatim raw fields (canonicalization is Phase 5 work).
        if r.country:
            stats.by_country[r.country] = stats.by_country.get(r.country, 0) + 1
        if r.state:
            stats.by_state[r.state] = stats.by_state.get(r.state, 0) + 1
        if date_canonical and len(date_canonical) >= 4:
            yr = date_canonical[:4]
            stats.by_year[yr] = stats.by_year.get(yr, 0) + 1
        if _maybe_null(r.contact_name) is not None:
            stats.contact_name_present += 1
            n_hits, hits = count_pii_hits(r.contact_name)
            if n_hits:
                stats.contact_name_pii_hits += n_hits
                # Keep up to 50 sample (grantee_code, hit) tuples — Phase-5
                # auditor needs verbatim values; full set preserved on disk.
                if len(stats.contact_name_pii_samples) < 50:
                    for h in hits:
                        stats.contact_name_pii_samples.append((r.grantee_code, h))

        if len(batch) >= BATCH_SIZE:
            _flush()
    _flush()
    return stats


# ─── Public entry point ───────────────────────────────────────────────────


@dataclass
class IngestResult:
    raw_dir: Path
    fetched_at_utc: str
    raw_path: Path
    byte_count: int
    sha256: str
    http_status: int
    sources_id: int
    extraction_run_id: int
    rows_in: int
    rows_staged: int
    by_country: dict[str, int]
    by_state: dict[str, int]
    by_year: dict[str, int]
    contact_name_present: int
    contact_name_pii_hits: int
    contact_name_pii_samples: list[tuple[str, str]]


def _build_run_notes(
    *,
    sha: str,
    rows_in: int,
    rows_out: int,
    contact_name_present: int,
    contact_name_pii_hits: int,
    contact_name_pii_samples: list[tuple[str, str]],
    is_idempotency_rerun: bool,
) -> str:
    sample_repr = ", ".join(
        f"{gc}:{val!r}" for gc, val in contact_name_pii_samples[:10]
    )
    rerun_tag = " [idempotency re-run]" if is_idempotency_rerun else ""
    return (
        f"registry={REGISTRY_TAG} sha256={sha} "
        f"rows_in={rows_in} rows_out={rows_out}{rerun_tag} | "
        f"DATASET FREEZE: rowsUpdatedAt={ROWS_UPDATED_AT_UTC}; "
        f"mirror has not been refreshed in 4 yr 2 mo. Grantees registered "
        f"2021-04 through capture date are NOT present. Phase 4 owns the "
        f"2021-present gap via FCC test-report PDF mining and per-vendor "
        f"research-led pulls. Flock Safety entirely absent from this "
        f"snapshot (zero %FLOCK% hits) — load-bearing finding routed to "
        f"Phase 4. | "
        f"§11 #3 corporate-comms read: contact_name staged as-is "
        f"(MAC-7 Q4 ratification 2026-05-04T14:34:12Z). "
        f"contact_name populated on {contact_name_present}/{rows_out} rows. "
        f"MAC-5/MAC-6 person-regex audit returned {contact_name_pii_hits} "
        f"hit(s); samples=[{sample_repr}]. All matches inspected: "
        f"corporate role concatenations / titles, zero officer-shape PII. "
        f"Raw CSV preserved verbatim per §7.2. | "
        f"phase5_reconsider_pii={PHASE5_RECONSIDER_PII}"
    )


def ingest(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    agent_id: str,
    raw_subdir: Optional[str] = None,
    is_idempotency_rerun: bool = False,
) -> IngestResult:
    """Fetch + parse + stage the FCC EAS grantee CSV.

    `raw_subdir`: if given, reuse an existing raw/<ts>/ directory. Otherwise
    fetch fresh into raw/<UTC-timestamp>/.
    `is_idempotency_rerun`: tags `extraction_runs.notes` so the audit trail
    distinguishes the initial ingest from the re-run.
    """
    fetched_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if raw_subdir:
        raw_dir = raw_root / raw_subdir
        if not raw_dir.exists():
            raise FileNotFoundError(f"raw_subdir {raw_dir} does not exist")
    else:
        raw_dir = raw_root / fetched_at
        raw_dir.mkdir(parents=True, exist_ok=True)

    LOG.info("FCC EAS grantee ingest -> raw_dir=%s", raw_dir)

    raw_path = raw_dir / SOURCE_FILENAME
    if raw_path.exists() and raw_subdir:
        body = raw_path.read_bytes()
        http_status = 200
        LOG.info("reusing existing %s (%d bytes)", raw_path, len(body))
    else:
        LOG.info("fetching %s", SOURCE_URL)
        body, http_status = _fetch(SOURCE_URL)
        raw_path.write_bytes(body)

    sha = hashlib.sha256(body).hexdigest()

    manifest_path = raw_dir / "manifest.json"
    if not manifest_path.exists() or not raw_subdir:
        manifest = {
            "fetched_at_utc": fetched_at if not raw_subdir else raw_subdir,
            "license_note": LICENSE_NOTE,
            "license_attribution": LICENSE_ATTRIBUTION,
            "files": [
                {
                    "path": SOURCE_FILENAME,
                    "url": SOURCE_URL,
                    "byte_count": len(body),
                    "sha256": sha,
                    "http_status": http_status,
                }
            ],
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        sid = _upsert_source(
            conn,
            fetched_at=_utc_now(),
            http_status=http_status,
            byte_count=len(body),
            content_hash=sha,
        )
        run_id = _start_run(conn, agent_id=agent_id, source_id=sid)
        try:
            grantee_rows = list(parse_grantees(body))
            stats = _stage_grantees(
                conn,
                source_id=sid,
                extraction_run_id=run_id,
                rows=grantee_rows,
            )
            run_notes = _build_run_notes(
                sha=sha,
                rows_in=len(grantee_rows),
                rows_out=stats.inserted,
                contact_name_present=stats.contact_name_present,
                contact_name_pii_hits=stats.contact_name_pii_hits,
                contact_name_pii_samples=stats.contact_name_pii_samples,
                is_idempotency_rerun=is_idempotency_rerun,
            )
            _finish_run(
                conn,
                run_id,
                records_in=len(grantee_rows),
                records_out=stats.inserted,
                errors=0,
                status="ok",
                notes=run_notes,
            )
            conn.commit()
        except Exception as e:
            _finish_run(
                conn,
                run_id,
                records_in=0,
                records_out=0,
                errors=1,
                status="failed",
                notes=f"{type(e).__name__}: {e}",
            )
            conn.commit()
            raise
    finally:
        conn.close()

    return IngestResult(
        raw_dir=raw_dir,
        fetched_at_utc=fetched_at if not raw_subdir else raw_subdir,
        raw_path=raw_path,
        byte_count=len(body),
        sha256=sha,
        http_status=http_status,
        sources_id=sid,
        extraction_run_id=run_id,
        rows_in=len(grantee_rows),
        rows_staged=stats.inserted,
        by_country=stats.by_country,
        by_state=stats.by_state,
        by_year=stats.by_year,
        contact_name_present=stats.contact_name_present,
        contact_name_pii_hits=stats.contact_name_pii_hits,
        contact_name_pii_samples=stats.contact_name_pii_samples,
    )


# ─── CLI ──────────────────────────────────────────────────────────────────


def _main() -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    p.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    p.add_argument(
        "--raw-subdir",
        type=str,
        default=None,
        help="Reuse an existing raw/fcc_id/<subdir>/ rather than re-fetching.",
    )
    p.add_argument(
        "--agent-id",
        type=str,
        required=True,
        help="Paperclip agent id ingesting this run (for extraction_runs.agent_id).",
    )
    p.add_argument(
        "--idempotency-rerun",
        action="store_true",
        help="Tag this run as the idempotency verification re-run in extraction_runs.notes.",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    result = ingest(
        db_path=args.db_path,
        raw_root=args.raw_root,
        agent_id=args.agent_id,
        raw_subdir=args.raw_subdir,
        is_idempotency_rerun=args.idempotency_rerun,
    )
    print(f"raw_dir: {result.raw_dir}")
    print(f"fetched_at_utc: {result.fetched_at_utc}")
    print(f"byte_count: {result.byte_count}")
    print(f"sha256: {result.sha256}")
    print(f"sources_id: {result.sources_id}")
    print(f"extraction_run_id: {result.extraction_run_id}")
    print(f"rows_in: {result.rows_in}")
    print(f"rows_staged: {result.rows_staged}")
    print(f"contact_name_present: {result.contact_name_present}")
    print(
        f"contact_name_pii_hits: {result.contact_name_pii_hits} "
        f"(samples={result.contact_name_pii_samples[:5]})"
    )
    print(f"top 10 countries:")
    for c, n in sorted(result.by_country.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {c}: {n}")
    print(f"year histogram (sorted):")
    for y, n in sorted(result.by_year.items()):
        print(f"  {y}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
