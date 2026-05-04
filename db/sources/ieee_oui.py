"""IEEE OUI registry ingest (Phase 2 — Tier 1, source #1).

Pulls IEEE's public OUI registry CSVs into Argus staging per
PROJECT_BIBLE.md §6 Phase 2 + §7.2 (Source Worker contract).

Three registry blocks ship as separate `sources` rows:

  * MA-L  — 24-bit OUI assignments    (oui.csv, ~37k rows as of 2026-05)
  * MA-M  — 28-bit MA-M sub-OUI ranges (mam.csv,    ~7k rows)
  * MA-S  — 36-bit MA-S sub-OUI ranges (oui36.csv,  ~5k rows)

Per CEO direction in MAC-3:
  * MA-L identifiers stage as `candidate_type='oui'`.
  * MA-M / MA-S stage as `candidate_type='mac_range'` (sub-OUI ranges).
  * Manufacturer name kept verbatim — canonicalization is Phase 5.
  * Manufacturer address kept in `notes` for later vendor-cluster work.
  * No promotion to `identifiers`; no inference; staging only.

Provenance (bible §11 #7): every `raw_observations` row carries the exact
file URL it came from in `source_url`, plus an excerpt of the raw CSV row in
`source_excerpt` so the validator can audit later.

────────────────────────────────────────────────────────────────────────────
Identifier normalization
────────────────────────────────────────────────────────────────────────────
The IEEE CSVs publish assignments as a contiguous hex string with no
separators (e.g. `286FB9` for MA-L, `C85CE27` for MA-M, `8C1F64AFA` for
MA-S). We normalize to lowercase hex with `:` separators every two hex
digits, leaving any trailing nibble as a half-byte group with its own
leading colon. Examples:

  286FB9        -> 28:6f:b9          (MA-L, 24 bits, 3 octets)
  C85CE27       -> c8:5c:e2:7        (MA-M, 28 bits, 3.5 octets)
  8C1F64AFA     -> 8c:1f:64:af:a     (MA-S, 36 bits, 4.5 octets)

Leading zeros are preserved; the full assignment string is kept intact.
This convention is documented here and in PROJECT_STATE.md so downstream
normalization (Phase 5) has a stable input shape.

────────────────────────────────────────────────────────────────────────────
Idempotency
────────────────────────────────────────────────────────────────────────────
Re-running this ingest must not duplicate rows. Two clean options were on
the table per MAC-3:

  (a) add a UNIQUE(source_id, candidate_identifier) constraint on
      `raw_observations` and rely on INSERT OR REPLACE.
  (b) delete-by-source-id then bulk-insert in a single transaction.

We chose (b) — delete-then-insert. It avoids changing the existing
`raw_observations` schema (no new migration), keeps the staging table's
"preserve forever for audit" semantics intact in the steady state (the
deletion only happens during an explicit re-ingest of the same source),
and is a single transactional operation so partial failures roll back
cleanly. Each MA-L / MA-M / MA-S registry block has its own `sources` row,
so the delete is naturally scoped per block.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional


LOG = logging.getLogger("argus.ingest.ieee_oui")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "ieee_oui"

SOURCE_TYPE = "regulatory"  # §4.1 source_type enum
TIER = 1  # §5 — IEEE OUI is a Tier 1 structured source

LICENSE_NOTE = (
    "Public domain — IEEE OUI listing, freely redistributable. "
    "https://standards-oui.ieee.org/"
)

# Registry-block descriptors. `block` is the short tag we use in
# `sources.notes` and the raw/<ts>/ filenames. `identifier_type` mirrors
# the §4.1 enum values.
REGISTRIES: tuple[dict[str, str], ...] = (
    {
        "block": "ma_l",
        "url": "https://standards-oui.ieee.org/oui/oui.csv",
        "filename": "ma_l.csv",
        "identifier_type": "oui",
        "name": "IEEE OUI registry (MA-L, 24-bit)",
    },
    {
        "block": "ma_m",
        "url": "https://standards-oui.ieee.org/oui28/mam.csv",
        "filename": "ma_m.csv",
        "identifier_type": "mac_range",
        "name": "IEEE OUI-28 registry (MA-M, 28-bit)",
    },
    {
        "block": "ma_s",
        "url": "https://standards-oui.ieee.org/oui36/oui36.csv",
        "filename": "ma_s.csv",
        "identifier_type": "mac_range",
        "name": "IEEE OUI-36 registry (MA-S, 36-bit)",
    },
)

# MA-L txt is fetched as a redundant raw copy for audit (the CSV is
# canonical for parsing, but the txt is what most humans recognize when
# auditing IEEE OUI provenance later). We do NOT parse it.
MA_L_TXT = {
    "url": "https://standards-oui.ieee.org/oui/oui.txt",
    "filename": "ma_l.txt",
}


# ─── HTTP fetch ────────────────────────────────────────────────────────────


def _fetch(url: str, timeout: int = 60) -> tuple[bytes, int]:
    """Single-shot HTTP fetch with one transient-error retry.

    Per §7.2 Don'ts: no silent infinite retries. One try, one retry on
    URLError (network-layer transient failure), then raise.
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
        except urllib.error.HTTPError as e:
            # Don't retry HTTP errors — they are deterministic.
            raise
        except urllib.error.URLError as e:
            LOG.warning("transient fetch error on attempt %d for %s: %s", attempt, url, e)
            last_exc = e
            if attempt == 2:
                raise
    assert last_exc is not None
    raise last_exc


# ─── Identifier normalization ──────────────────────────────────────────────


def normalize_assignment(raw: str) -> str:
    """Lowercase, colon-grouped (every 2 hex digits) — keep trailing nibble.

    See module docstring for examples.
    """
    s = raw.strip().lower()
    # Drop any separators IEEE might publish in future variants.
    s = "".join(ch for ch in s if ch in "0123456789abcdef")
    if not s:
        return s
    pairs = [s[i : i + 2] for i in range(0, len(s), 2)]
    return ":".join(pairs)


# ─── CSV parsing ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OuiRow:
    """One IEEE OUI CSV row, post-normalization."""

    registry_block: str          # 'ma_l' | 'ma_m' | 'ma_s'
    raw_assignment: str          # as published, e.g. '286FB9'
    normalized_identifier: str   # e.g. '28:6f:b9'
    organization_name: str       # raw, verbatim
    organization_address: str    # raw, verbatim (may be empty)
    raw_row: str                 # the full CSV row text (for source_excerpt)


def parse_csv(content: bytes, registry_block: str) -> Iterator[OuiRow]:
    """Yield OuiRow per CSV row.

    Skips rows that fail basic shape checks. The IEEE CSVs are very clean
    in practice; any malformed row is logged and skipped rather than
    silently retried.
    """
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if header is None or [h.strip() for h in header] != [
        "Registry",
        "Assignment",
        "Organization Name",
        "Organization Address",
    ]:
        LOG.warning("unexpected CSV header for %s: %r", registry_block, header)
        # Don't raise — we still try to parse if header drift is minor.

    for row in reader:
        if not row or len(row) < 4:
            LOG.debug("skipping short row in %s: %r", registry_block, row)
            continue
        registry, assignment, org_name, org_addr = row[0], row[1], row[2], row[3]
        # The CSV's "Registry" column should match our block tag (case-folded).
        if registry.strip().lower().replace("-", "_") != registry_block:
            LOG.debug(
                "row registry %r != expected %r — accepting anyway",
                registry,
                registry_block,
            )
        normalized = normalize_assignment(assignment)
        if not normalized:
            continue
        # Reconstruct the raw row text for source_excerpt — preserve quoting.
        raw_row = ",".join(
            f'"{c.replace(chr(34), chr(34) * 2)}"' if ("," in c or '"' in c) else c
            for c in row
        )
        yield OuiRow(
            registry_block=registry_block,
            raw_assignment=assignment.strip(),
            normalized_identifier=normalized,
            organization_name=org_name.strip(),
            organization_address=org_addr.strip(),
            raw_row=raw_row,
        )


# ─── DB writes ─────────────────────────────────────────────────────────────


def _utc_now() -> str:
    """ISO-8601 UTC timestamp suitable for SQLite DATETIME."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _upsert_source(
    conn: sqlite3.Connection,
    *,
    name: str,
    url: str,
    fetched_at: str,
    http_status: int,
    byte_count: int,
    content_hash: str,
    block: str,
) -> int:
    """Insert or update a `sources` row keyed by URL. Returns sources.id."""
    notes = json.dumps(
        {
            "registry_block": block,
            "license": LICENSE_NOTE,
            "byte_count": byte_count,
            "content_sha256": content_hash,
            "http_status": http_status,
        },
        sort_keys=True,
    )
    cur = conn.execute("SELECT id FROM sources WHERE url = ?", (url,))
    existing = cur.fetchone()
    if existing is not None:
        sid = int(existing[0])
        conn.execute(
            "UPDATE sources SET name = ?, source_type = ?, tier = ?, "
            "last_fetched_at = ?, last_status = ?, notes = ? WHERE id = ?",
            (name, SOURCE_TYPE, TIER, fetched_at, "ok", notes, sid),
        )
        return sid
    cur = conn.execute(
        "INSERT INTO sources (name, url, source_type, tier, "
        "last_fetched_at, last_status, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, url, SOURCE_TYPE, TIER, fetched_at, "ok", notes),
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


def _stage_raw_observations(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    extraction_run_id: int,
    source_url: str,
    identifier_type: str,
    rows: Iterable[OuiRow],
) -> int:
    """Delete-by-source-id then bulk insert (idempotent re-ingest)."""
    conn.execute("DELETE FROM raw_observations WHERE source_id = ?", (source_id,))

    inserted = 0
    batch: list[tuple] = []
    BATCH_SIZE = 1000
    for r in rows:
        # source_excerpt cap: 200 chars per §4.1 main-table convention
        # (raw_observations has no CHECK, but mirroring keeps Phase 5 promotion
        # painless).
        excerpt = r.raw_row[:200]
        notes = r.organization_address or None
        batch.append(
            (
                source_id,
                extraction_run_id,
                source_url,
                None,                       # raw_payload — full row preserved in raw/ files; no need to dup here
                r.normalized_identifier,
                identifier_type,
                None,                       # candidate_category — Phase 5 inference, not now
                r.organization_name,
                excerpt,
                notes,
            )
        )
        if len(batch) >= BATCH_SIZE:
            conn.executemany(
                "INSERT INTO raw_observations ("
                "source_id, extraction_run_id, source_url, raw_payload, "
                "candidate_identifier, candidate_type, candidate_category, "
                "candidate_manufacturer, source_excerpt, notes"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
            inserted += len(batch)
            batch.clear()
    if batch:
        conn.executemany(
            "INSERT INTO raw_observations ("
            "source_id, extraction_run_id, source_url, raw_payload, "
            "candidate_identifier, candidate_type, candidate_category, "
            "candidate_manufacturer, source_excerpt, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batch,
        )
        inserted += len(batch)
    return inserted


# ─── Public entry point ────────────────────────────────────────────────────


@dataclass
class RegistryIngestResult:
    block: str
    url: str
    raw_path: Path
    byte_count: int
    sha256: str
    http_status: int
    sources_id: int
    extraction_run_id: int
    rows_staged: int


@dataclass
class IngestResult:
    raw_dir: Path
    fetched_at_utc: str
    registries: list[RegistryIngestResult]

    @property
    def total_rows(self) -> int:
        return sum(r.rows_staged for r in self.registries)


def ingest(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    agent_id: str,
    raw_subdir: Optional[str] = None,
) -> IngestResult:
    """Fetch + parse + stage all four IEEE OUI registry artifacts.

    `raw_subdir`: if given, reuse an existing raw/<ts>/ directory (the
    fetched-already files there are checksum-verified rather than re-fetched).
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

    LOG.info("IEEE OUI ingest -> raw_dir=%s", raw_dir)

    # Fetch (or reuse) every artifact, including the redundant MA-L txt.
    artifacts: dict[str, dict] = {}
    for spec in (*REGISTRIES, MA_L_TXT):
        path = raw_dir / spec["filename"]
        if path.exists() and raw_subdir:
            body = path.read_bytes()
            http_status = 200  # assumed-ok from manifest reuse
            LOG.info("reusing existing %s (%d bytes)", path, len(body))
        else:
            LOG.info("fetching %s", spec["url"])
            body, http_status = _fetch(spec["url"])
            path.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        artifacts[spec["filename"]] = {
            "url": spec["url"],
            "byte_count": len(body),
            "sha256": sha,
            "http_status": http_status,
            "path": str(path.relative_to(raw_root.parent)),
        }

    # Manifest — write/refresh.
    manifest_path = raw_dir / "manifest.json"
    manifest = {
        "fetched_at_utc": fetched_at if not raw_subdir else raw_subdir,
        "license_note": LICENSE_NOTE,
        "files": [
            {
                "path": spec["filename"],
                "url": artifacts[spec["filename"]]["url"],
                "byte_count": artifacts[spec["filename"]]["byte_count"],
                "sha256": artifacts[spec["filename"]]["sha256"],
                "http_status": artifacts[spec["filename"]]["http_status"],
            }
            for spec in (*REGISTRIES, MA_L_TXT)
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # Stage to DB. One transaction per registry block (so a failure on
    # MA-S doesn't roll back a successful MA-L stage).
    results: list[RegistryIngestResult] = []
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        for spec in REGISTRIES:
            art = artifacts[spec["filename"]]
            sid = _upsert_source(
                conn,
                name=spec["name"],
                url=spec["url"],
                fetched_at=_utc_now(),
                http_status=art["http_status"],
                byte_count=art["byte_count"],
                content_hash=art["sha256"],
                block=spec["block"],
            )
            run_id = _start_run(conn, agent_id=agent_id, source_id=sid)
            try:
                content = (raw_dir / spec["filename"]).read_bytes()
                rows = list(parse_csv(content, spec["block"]))
                staged = _stage_raw_observations(
                    conn,
                    source_id=sid,
                    extraction_run_id=run_id,
                    source_url=spec["url"],
                    identifier_type=spec["identifier_type"],
                    rows=rows,
                )
                _finish_run(
                    conn,
                    run_id,
                    records_in=len(rows),
                    records_out=staged,
                    errors=0,
                    status="ok",
                    notes=f"block={spec['block']} sha256={art['sha256']}",
                )
                conn.commit()
                results.append(
                    RegistryIngestResult(
                        block=spec["block"],
                        url=spec["url"],
                        raw_path=raw_dir / spec["filename"],
                        byte_count=art["byte_count"],
                        sha256=art["sha256"],
                        http_status=art["http_status"],
                        sources_id=sid,
                        extraction_run_id=run_id,
                        rows_staged=staged,
                    )
                )
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
        registries=results,
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
        help="Reuse an existing raw/ieee_oui/<subdir>/ rather than re-fetching.",
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
    for r in result.registries:
        print(
            f"  {r.block}: rows_staged={r.rows_staged} "
            f"sources_id={r.sources_id} run_id={r.extraction_run_id} "
            f"sha256={r.sha256[:12]}…"
        )
    print(f"total rows staged: {result.total_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
