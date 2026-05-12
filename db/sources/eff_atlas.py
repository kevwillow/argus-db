"""EFF Atlas of Surveillance ingest (Phase 2 — Tier 1, source #3).

Pulls the EFF + UNLV Atlas of Surveillance dataset into Argus staging
per PROJECT_BIBLE.md §6 Phase 2 + §7.2 (Source Worker contract). Lands
rows in the new `deployment_observations` staging table (added by
migration `0002_deployment_observations.sql`, ratified by CP4 commit
`d81de3b`).

Source
──────
URL:    https://atlasofsurveillance.org/download.csv
Format: CSV, 28 columns (header), 15,071 data rows in 2026-05-04 snapshot.
        Column order: AOSNUMBER, NEWAOSNUMBER (ORI9), City, County, State,
        Agency, Type of LEA, Summary, Type of Juris, Technology, TECH ABV,
        Vendor, Link 1, Link 1 Snapshot, Link 1 Source, Link 1 Type,
        Link 1 Date, Link 2, Link 2 Snapshot, Link 2 Source, Link 2 Type,
        Link 2 Date, Link 3, Link 3 Snapshot, Link 3 Source, Link 3 Type,
        Link 3 Date, Other Links.

License: Creative Commons Attribution 4.0 International (CC BY 4.0).
         Verbatim from `manifest.json`. https://www.eff.org/copyright
         + https://atlasofsurveillance.org/

source_type: `crowdsourced` (CEO-ratified at MAC-5 / CP4). Atlas's own
about-page describes the process as "crowdsourcing, data journalism and
public records reporting." §8.2 confidence band 50–75 honestly reflects
single-citation deployment claims from public reporting. Aligns with
the MAC-4 Wireshark `manuf` precedent; reconsider at Phase 5 if the band
under-fits.

tier:        1 (per Bible §5).

source_url per row: the *dataset* URL
(`https://atlasofsurveillance.org/download.csv`), NOT the per-row Link 1.
Per CP4 ratification: Link 1 is Atlas's *external* journalistic citation,
structurally distinct from "the source we are attributing to." Captured
into the separate `citation_url` column.

────────────────────────────────────────────────────────────────────────────
§11 #1 — no fabrication
────────────────────────────────────────────────────────────────────────────
Atlas yields agency × technology × location × vendor metadata but **no**
MAC/OUI/SSID/UUID identifier. Identifier columns are intentionally absent
from `deployment_observations` (bible §4.2). Promotion to `identifiers`
requires a Phase 3+ inference linking a deployment to a concrete
identifier candidate (e.g. WiGLE radius queries → BSSID corroboration).

────────────────────────────────────────────────────────────────────────────
§11 #3 — PII redaction
────────────────────────────────────────────────────────────────────────────
Atlas's `Summary` field occasionally surfaces officer-name PII embedded
in journalistic prose (one confirmed case in the 2026-05-04 snapshot:
AOS001160 → "according to Mayor Gary Smith"). Per CEO ratification at
MAC-5 / CP4:

  1. Apply a `\\b(rank-token)\\s+[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)?` regex
     to the Summary text. Each match collapses to `[REDACTED-PERSON]`.
  2. The redacted Summary lands in `deployment_observations.notes` JSON.
  3. The full untouched Summary is preserved on disk verbatim in
     `raw/eff_atlas/<ts>/atlas_of_surveillance.csv` (§7.2 audit trail).
  4. Redaction count + AOSNUMBER list are logged in `extraction_runs.notes`
     so a Phase 5 reviewer can see ingest-time scrubs without grepping
     the codebase.

The regex is intentionally a wider net than the single confirmed PII —
it also collapses agency-name false positives like "Major Police and Fire
Supply" or "Constable Precinct 5". This is the worker-proposed and
CEO-ratified trade: ingest-time scrubbing prefers recall on PII over
precision on agency-name preservation. Phase 5 promotion runs a stricter
pass; the raw-on-disk preservation is the recovery path if a false
positive ever needs to be unwound.

The `Summary` field is NEVER copied verbatim into the database. Only
the redacted form lands in `notes` JSON; the `source_excerpt` column
also draws from the redacted Summary (truncated to ≤200 chars by the
existing CHECK constraint).

────────────────────────────────────────────────────────────────────────────
Idempotency
────────────────────────────────────────────────────────────────────────────
Same shape as MAC-3 / MAC-4: delete-by-`source_id` then bulk-insert in a
single transaction. The structural backstop is the
`UNIQUE(source_id, source_row_key)` index on `deployment_observations`;
re-running this ingest on the same raw_subdir produces identical row
counts and never duplicates.
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


LOG = logging.getLogger("argus.ingest.eff_atlas")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "eff_atlas"

SOURCE_NAME = "EFF Atlas of Surveillance (EFF + UNLV Reynolds School of Journalism)"
SOURCE_URL = "https://atlasofsurveillance.org/download.csv"
SOURCE_FILENAME = "atlas_of_surveillance.csv"
SOURCE_TYPE = "crowdsourced"  # §4.1 source_type enum — CEO-ratified at CP4.
TIER = 1                       # §5 — Tier 1 structured source.

LICENSE_NOTE = (
    "License: Creative Commons Attribution 4.0 International (CC BY 4.0). "
    "https://creativecommons.org/licenses/by/4.0/"
)
LICENSE_ATTRIBUTION = (
    "Atlas of Surveillance, Electronic Frontier Foundation + UNLV "
    "Reynolds School of Journalism. https://atlasofsurveillance.org/"
)

REGISTRY_TAG = "eff_atlas"


# ─── PII redaction (§11 #3, CP4-ratified) ──────────────────────────────────


# Rank tokens that introduce a likely officer/official name in journalistic
# prose. Includes `Mayor` because the one confirmed PII case in the
# 2026-05-04 snapshot is `Mayor Gary Smith`. Wide net by design — see
# module docstring for the recall-over-precision rationale.
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

# `\b(rank)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?` — rank token followed by 1-2
# capitalized words. Two-word match collapses `Mayor Gary Smith` whole; one-
# word fallback handles `Sheriff Smith`-style references. Word-boundary on
# the rank prevents collisions inside other words (e.g. `Major Crash` does
# match — that's a known false positive accepted under the CP4 trade).
PII_REGEX = re.compile(
    r"\b("
    + "|".join(re.escape(t) for t in PII_RANK_TOKENS)
    + r")\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
)

REDACTION_MARKER = "[REDACTED-PERSON]"


def redact_pii(summary: str) -> tuple[str, int]:
    """Return (redacted_text, hit_count). Empty input → ("", 0)."""
    if not summary:
        return "", 0
    hits = 0

    def _sub(_m: re.Match[str]) -> str:
        nonlocal hits
        hits += 1
        return REDACTION_MARKER

    redacted = PII_REGEX.sub(_sub, summary)
    return redacted, hits


# ─── HTTP fetch ────────────────────────────────────────────────────────────


def _fetch(url: str, timeout: int = 60) -> tuple[bytes, int]:
    """Single-shot HTTP fetch with one transient-error retry.

    Mirrors `db/sources/wireshark_manuf.py::_fetch` and
    `db/sources/ieee_oui.py::_fetch`. Per §7.2 Don'ts: no silent infinite
    retries.
    """
    last_exc: Optional[BaseException] = None
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "argus-ingest/0.1 (+https://github.com/)"},
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


# ─── Atlas CSV parsing ─────────────────────────────────────────────────────


# Column-name constants — single point of change if EFF renames a column.
COL_AOSNUMBER = "AOSNUMBER"
COL_NEWAOSNUMBER = "NEWAOSNUMBER (ORI9)"
COL_CITY = "City"
COL_COUNTY = "County"
COL_STATE = "State"
COL_AGENCY = "Agency"
COL_TYPE_OF_LEA = "Type of LEA"
COL_SUMMARY = "Summary"
COL_TYPE_OF_JURIS = "Type of Juris"
COL_TECHNOLOGY = "Technology"
COL_TECH_ABV = "TECH ABV"
COL_VENDOR = "Vendor"
COL_LINK1 = "Link 1"
COL_LINK1_SNAPSHOT = "Link 1 Snapshot"
COL_LINK1_SOURCE = "Link 1 Source"
COL_LINK1_TYPE = "Link 1 Type"
COL_LINK1_DATE = "Link 1 Date"
COL_LINK2 = "Link 2"
COL_LINK2_SNAPSHOT = "Link 2 Snapshot"
COL_LINK2_SOURCE = "Link 2 Source"
COL_LINK2_TYPE = "Link 2 Type"
COL_LINK2_DATE = "Link 2 Date"
COL_LINK3 = "Link 3"
COL_LINK3_SNAPSHOT = "Link 3 Snapshot"
COL_LINK3_SOURCE = "Link 3 Source"
COL_LINK3_TYPE = "Link 3 Type"
COL_LINK3_DATE = "Link 3 Date"
COL_OTHER_LINKS = "Other Links"

EXPECTED_HEADER = (
    COL_AOSNUMBER, COL_NEWAOSNUMBER, COL_CITY, COL_COUNTY, COL_STATE,
    COL_AGENCY, COL_TYPE_OF_LEA, COL_SUMMARY, COL_TYPE_OF_JURIS,
    COL_TECHNOLOGY, COL_TECH_ABV, COL_VENDOR,
    COL_LINK1, COL_LINK1_SNAPSHOT, COL_LINK1_SOURCE, COL_LINK1_TYPE, COL_LINK1_DATE,
    COL_LINK2, COL_LINK2_SNAPSHOT, COL_LINK2_SOURCE, COL_LINK2_TYPE, COL_LINK2_DATE,
    COL_LINK3, COL_LINK3_SNAPSHOT, COL_LINK3_SOURCE, COL_LINK3_TYPE, COL_LINK3_DATE,
    COL_OTHER_LINKS,
)


@dataclass(frozen=True)
class AtlasRow:
    """One Atlas data row, post-redaction.

    `summary_redacted` carries the §11 #3 sanitized Summary; the raw
    Summary is NEVER stored on the AtlasRow — it stays only in
    `raw/eff_atlas/<ts>/atlas_of_surveillance.csv`.
    """

    aos_number: str
    new_aos_number: str
    city: str
    county: str
    state: str
    agency: str
    type_of_lea: str
    summary_redacted: str
    redaction_hits: int
    type_of_juris: str
    technology: str
    tech_abv: str
    vendor: str
    link1: str
    link1_snapshot: str
    link1_source: str
    link1_type: str
    link1_date: str
    link2: str
    link2_snapshot: str
    link2_source: str
    link2_type: str
    link2_date: str
    link3: str
    link3_snapshot: str
    link3_source: str
    link3_type: str
    link3_date: str
    other_links: str


def parse_atlas(content: bytes) -> Iterator[AtlasRow]:
    """Yield AtlasRow per data row. Raises ValueError on header surprises.

    The raw Summary is redacted in-place during iteration; callers never
    see the unredacted text on the AtlasRow.
    """
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(text.splitlines())
    header = next(reader, None)
    if header is None:
        raise ValueError("Atlas CSV has no header row")
    header_tup = tuple(h.strip() for h in header)
    if header_tup != EXPECTED_HEADER:
        # Surface the divergence loudly. Atlas changing its column shape is
        # a stop-the-line event for the parser — Phase 2 stages don't guess.
        missing = set(EXPECTED_HEADER) - set(header_tup)
        extra = set(header_tup) - set(EXPECTED_HEADER)
        raise ValueError(
            f"Atlas CSV header divergence — missing={sorted(missing)}, "
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
        summary_raw = record[COL_SUMMARY]
        summary_redacted, hits = redact_pii(summary_raw)
        yield AtlasRow(
            aos_number=record[COL_AOSNUMBER],
            new_aos_number=record[COL_NEWAOSNUMBER],
            city=record[COL_CITY],
            county=record[COL_COUNTY],
            state=record[COL_STATE],
            agency=record[COL_AGENCY],
            type_of_lea=record[COL_TYPE_OF_LEA],
            summary_redacted=summary_redacted,
            redaction_hits=hits,
            type_of_juris=record[COL_TYPE_OF_JURIS],
            technology=record[COL_TECHNOLOGY],
            tech_abv=record[COL_TECH_ABV],
            vendor=record[COL_VENDOR],
            link1=record[COL_LINK1],
            link1_snapshot=record[COL_LINK1_SNAPSHOT],
            link1_source=record[COL_LINK1_SOURCE],
            link1_type=record[COL_LINK1_TYPE],
            link1_date=record[COL_LINK1_DATE],
            link2=record[COL_LINK2],
            link2_snapshot=record[COL_LINK2_SNAPSHOT],
            link2_source=record[COL_LINK2_SOURCE],
            link2_type=record[COL_LINK2_TYPE],
            link2_date=record[COL_LINK2_DATE],
            link3=record[COL_LINK3],
            link3_snapshot=record[COL_LINK3_SNAPSHOT],
            link3_source=record[COL_LINK3_SOURCE],
            link3_type=record[COL_LINK3_TYPE],
            link3_date=record[COL_LINK3_DATE],
            other_links=record[COL_OTHER_LINKS],
        )


# ─── DB writes ─────────────────────────────────────────────────────────────


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
    by_state: dict[str, int] = field(default_factory=dict)
    by_vendor: dict[str, int] = field(default_factory=dict)
    by_technology: dict[str, int] = field(default_factory=dict)
    by_juris: dict[str, int] = field(default_factory=dict)
    redaction_hits_total: int = 0
    redacted_aos_numbers: list[str] = field(default_factory=list)


def _stage_deployment_observations(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    extraction_run_id: int,
    rows: Iterable[AtlasRow],
) -> StagingStats:
    """Delete-by-source-id then bulk-insert. Returns aggregate stats."""
    conn.execute(
        "DELETE FROM deployment_observations WHERE source_id = ?", (source_id,)
    )

    stats = StagingStats()
    batch: list[tuple] = []
    BATCH_SIZE = 1000

    sql = (
        "INSERT INTO deployment_observations ("
        "source_id, extraction_run_id, source_url, source_row_key, "
        "agency_name, agency_type, juris_type, city, county, state, country, "
        "lat, lon, technology_category, vendor_raw, citation_url, "
        "source_excerpt, notes, license"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    def _flush() -> None:
        if not batch:
            return
        conn.executemany(sql, batch)
        stats.inserted += len(batch)
        batch.clear()

    for r in rows:
        # `source_excerpt` ≤200 char view of the redacted Summary, for
        # validator audit. Full redacted Summary lives in `notes` JSON.
        excerpt: Optional[str] = None
        if r.summary_redacted:
            excerpt = r.summary_redacted[:200]

        notes_obj: dict[str, object] = {
            "summary_redacted": r.summary_redacted,
            "redaction_hits": r.redaction_hits,
            "ori9": r.new_aos_number or None,
            "tech_abv": r.tech_abv or None,
            "links": [
                {
                    "url": r.link1 or None,
                    "snapshot": r.link1_snapshot or None,
                    "source": r.link1_source or None,
                    "type": r.link1_type or None,
                    "date": r.link1_date or None,
                },
                {
                    "url": r.link2 or None,
                    "snapshot": r.link2_snapshot or None,
                    "source": r.link2_source or None,
                    "type": r.link2_type or None,
                    "date": r.link2_date or None,
                },
                {
                    "url": r.link3 or None,
                    "snapshot": r.link3_snapshot or None,
                    "source": r.link3_source or None,
                    "type": r.link3_type or None,
                    "date": r.link3_date or None,
                },
            ],
            "other_links": r.other_links or None,
        }
        notes = json.dumps(notes_obj, sort_keys=True)

        batch.append(
            (
                source_id,
                extraction_run_id,
                SOURCE_URL,
                r.aos_number,
                r.agency or None,
                r.type_of_lea or None,
                r.type_of_juris or None,
                r.city or None,
                r.county or None,
                r.state or None,
                "US",                     # Atlas covers US deployments only.
                None,                     # lat — Atlas has no geo coords
                None,                     # lon
                r.technology or None,
                r.vendor or None,
                r.link1 or None,          # citation_url = per-row Link 1
                excerpt,
                notes,
                "CC-BY-NC-SA-4.0",        # license — EFF Atlas upstream license (migration 0016)
            )
        )

        # Aggregate stats — kept verbatim from raw fields. Canonicalization
        # is Phase 5 (§7.2 "do not normalize during ingest").
        if r.state:
            stats.by_state[r.state] = stats.by_state.get(r.state, 0) + 1
        if r.vendor:
            stats.by_vendor[r.vendor] = stats.by_vendor.get(r.vendor, 0) + 1
        if r.technology:
            stats.by_technology[r.technology] = (
                stats.by_technology.get(r.technology, 0) + 1
            )
        if r.type_of_juris:
            stats.by_juris[r.type_of_juris] = (
                stats.by_juris.get(r.type_of_juris, 0) + 1
            )
        if r.redaction_hits:
            stats.redaction_hits_total += r.redaction_hits
            stats.redacted_aos_numbers.append(r.aos_number)

        if len(batch) >= BATCH_SIZE:
            _flush()
    _flush()
    return stats


# ─── Public entry point ────────────────────────────────────────────────────


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
    rows_staged: int
    redaction_hits_total: int
    redacted_aos_numbers: list[str]
    by_state: dict[str, int]
    by_vendor: dict[str, int]
    by_technology: dict[str, int]
    by_juris: dict[str, int]


def ingest(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    agent_id: str,
    raw_subdir: Optional[str] = None,
) -> IngestResult:
    """Fetch + parse + stage the EFF Atlas CSV.

    `raw_subdir`: if given, reuse an existing raw/<ts>/ directory.
    Otherwise fetch fresh into raw/<UTC-timestamp>/.
    """
    fetched_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if raw_subdir:
        raw_dir = raw_root / raw_subdir
        if not raw_dir.exists():
            raise FileNotFoundError(f"raw_subdir {raw_dir} does not exist")
    else:
        raw_dir = raw_root / fetched_at
        raw_dir.mkdir(parents=True, exist_ok=True)

    LOG.info("EFF Atlas ingest -> raw_dir=%s", raw_dir)

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
            atlas_rows = list(parse_atlas(body))
            stats = _stage_deployment_observations(
                conn,
                source_id=sid,
                extraction_run_id=run_id,
                rows=atlas_rows,
            )
            redacted_list_str = ",".join(stats.redacted_aos_numbers)
            run_notes = (
                f"registry={REGISTRY_TAG} sha256={sha} "
                f"rows_in={len(atlas_rows)} rows_out={stats.inserted} | "
                f"§11 #3 PII redaction: hits={stats.redaction_hits_total} "
                f"across {len(stats.redacted_aos_numbers)} row(s); "
                f"AOSNUMBERs=[{redacted_list_str}]; "
                "raw Summary preserved verbatim on disk per §7.2 — "
                "redacted form lands in deployment_observations.notes only. "
                "EFF Atlas classified crowdsourced (CP4); reconsider at "
                "Phase 5 if confidence band under-fits."
            )
            _finish_run(
                conn,
                run_id,
                records_in=len(atlas_rows),
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
        rows_staged=stats.inserted,
        redaction_hits_total=stats.redaction_hits_total,
        redacted_aos_numbers=stats.redacted_aos_numbers,
        by_state=stats.by_state,
        by_vendor=stats.by_vendor,
        by_technology=stats.by_technology,
        by_juris=stats.by_juris,
    )


# ─── CLI ───────────────────────────────────────────────────────────────────


def _main() -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    p.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    p.add_argument(
        "--raw-subdir",
        type=str,
        default=None,
        help="Reuse an existing raw/eff_atlas/<subdir>/ rather than re-fetching.",
    )
    p.add_argument(
        "--agent-id",
        type=str,
        required=True,
        help="Paperclip agent id ingesting this run (for extraction_runs.agent_id).",
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
    )
    print(f"raw_dir: {result.raw_dir}")
    print(f"fetched_at_utc: {result.fetched_at_utc}")
    print(f"byte_count: {result.byte_count}")
    print(f"sha256: {result.sha256}")
    print(f"sources_id: {result.sources_id}")
    print(f"extraction_run_id: {result.extraction_run_id}")
    print(f"rows_staged: {result.rows_staged}")
    print(
        f"redaction_hits_total: {result.redaction_hits_total} "
        f"(across {len(result.redacted_aos_numbers)} rows)"
    )
    print(f"top 10 vendors:")
    for v, n in sorted(result.by_vendor.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {v}: {n}")
    print(f"top 10 technologies:")
    for t, n in sorted(result.by_technology.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {t}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
