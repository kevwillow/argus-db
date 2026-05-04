"""Wireshark `manuf` ingest (Phase 2 — Tier 1, source #2).

Pulls the Wireshark community-maintained `manuf` file into Argus staging
per PROJECT_BIBLE.md §6 Phase 2 + §7.2 (Source Worker contract). Same
dispatch shape as `db/sources/ieee_oui.py` (MAC-3) — one new module here.

Source
──────
URL:    https://www.wireshark.org/download/automated/data/manuf
Format: plain text. Comment lines start with `#`. Each data line is
        tab-separated fields:

            address<TAB>short_name<TAB>long_name[<TAB>comment]

        Address column uses Wireshark's mask notation:
          * full 24-bit OUI:       `00:00:01`
          * /28 (28-bit prefix):   `00:55:DA:00/28`
          * /36 (36-bit prefix):   `00:1B:C5:00:00/36`

License: GPL-2.0-or-later (Wireshark community-maintained file).
         https://www.wireshark.org/

source_type: `crowdsourced` (NOT `regulatory` — IEEE is the
regulatory authority; Wireshark is community-curated). Per CEO
decision on MAC-4 (2026-05-04): Wireshark `manuf` lands under
the existing §4.1 `crowdsourced` enum (alongside WiGLE/DeFlock,
§8.2 confidence band 50–75) rather than introducing a new
`community` enum. Reconsider at Phase 5 if the band under-fits.
tier:        1 (per Bible §5).

────────────────────────────────────────────────────────────────────────────
Identifier normalization
────────────────────────────────────────────────────────────────────────────
Same convention as MAC-3 / `ieee_oui.py`: lowercase hex, `:` separators
every two hex digits, trailing nibble preserved as a half-byte group.
Phase 5 canonicalization happens elsewhere; this stage just gives Phase 5
a stable input shape.

Worked examples for the three Wireshark mask shapes:

    00:00:01            -> 00:00:01            (24-bit OUI, 6 hex digits)
    00:55:DA:00/28      -> 00:55:da:0          (28-bit prefix, 7 hex digits)
    00:1B:C5:00:00/36   -> 00:1b:c5:00:0       (36-bit prefix, 9 hex digits)

Mechanically: strip the `/N` suffix, take all hex chars (lowercased),
truncate to ceil(N/4) hex chars (24→6, 28→7, 36→9), then re-group every
two hex chars with `:` separators, leaving any trailing odd nibble alone.

Wireshark's /28 and /36 entries are written with a full byte for the
prefix's tail (e.g. `00:55:DA:00/28` rather than `00:55:DA:0/28`); the low
nibble of the tail byte is always zero in the published file. This is the
opposite shape from IEEE's MA-M / MA-S CSVs (`C85CE27` is already 7 hex
digits), but the normalized output is identical: `00:55:da:0` matches the
IEEE `c8:5c:e2:7` style. Documented here so the validator can audit the
fold.

────────────────────────────────────────────────────────────────────────────
Identifier type mapping
────────────────────────────────────────────────────────────────────────────
    no `/N` suffix   -> candidate_type = 'oui'        (24-bit OUI)
    /28              -> candidate_type = 'mac_range'  (sub-OUI range)
    /36              -> candidate_type = 'mac_range'  (sub-OUI range)

────────────────────────────────────────────────────────────────────────────
Idempotency
────────────────────────────────────────────────────────────────────────────
Mirrors MAC-3: delete-by-`source_id` then bulk-insert in a single
transaction. Re-running this ingest produces a stable row count and does
not duplicate `raw_observations`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional


LOG = logging.getLogger("argus.ingest.wireshark_manuf")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "wireshark_manuf"

SOURCE_NAME = "Wireshark manuf (community-maintained OUI file)"
SOURCE_URL = "https://www.wireshark.org/download/automated/data/manuf"
SOURCE_FILENAME = "manuf"
SOURCE_TYPE = "crowdsourced"  # §4.1 source_type enum — NOT regulatory.
TIER = 1                   # §5 — Tier 1 structured source.

LICENSE_NOTE = (
    "License: GPL-2.0-or-later (Wireshark community-maintained manuf "
    "file). https://www.wireshark.org/"
)

REGISTRY_TAG = "wireshark_manuf"


# ─── HTTP fetch ────────────────────────────────────────────────────────────


def _fetch(url: str, timeout: int = 60) -> tuple[bytes, int]:
    """Single-shot HTTP fetch with one transient-error retry.

    Per §7.2 Don'ts: no silent infinite retries. One try, one retry on
    URLError (network-layer transient failure), then raise. Mirrors the
    IEEE OUI ingest's `_fetch`.
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
            LOG.warning("transient fetch error on attempt %d for %s: %s", attempt, url, e)
            last_exc = e
            if attempt == 2:
                raise
    assert last_exc is not None
    raise last_exc


# ─── Identifier normalization ──────────────────────────────────────────────


def normalize_address(raw: str) -> tuple[str, str]:
    """Return (normalized_identifier, candidate_type) for a Wireshark address.

    Drops the `/N` suffix, lowercases, strips non-hex, truncates to the
    bit-width's worth of hex digits, and re-groups every two hex chars with
    `:` separators. Trailing nibble (odd hex char) is preserved as a
    half-byte group.

    Raises ValueError on anything outside the documented shapes (24 / 28 /
    36 bits) — Phase 2 ingest stops on shape surprises rather than
    inventing a representation.
    """
    s = raw.strip()
    if "/" in s:
        prefix, _, mask_str = s.partition("/")
        try:
            mask_bits = int(mask_str.strip())
        except ValueError as e:
            raise ValueError(f"non-integer mask in address {raw!r}") from e
    else:
        prefix = s
        mask_bits = 24
    hex_chars = "".join(ch for ch in prefix.lower() if ch in "0123456789abcdef")
    if mask_bits not in (24, 28, 36):
        raise ValueError(
            f"unexpected mask width /{mask_bits} in address {raw!r}; "
            "supported widths are 24, 28, 36"
        )
    needed = (mask_bits + 3) // 4  # ceil(mask_bits/4)
    if len(hex_chars) < needed:
        raise ValueError(
            f"short hex prefix in address {raw!r}: have {len(hex_chars)}, "
            f"need {needed} for /{mask_bits}"
        )
    hex_chars = hex_chars[:needed]
    pairs = [hex_chars[i : i + 2] for i in range(0, len(hex_chars), 2)]
    normalized = ":".join(pairs)
    candidate_type = "oui" if mask_bits == 24 else "mac_range"
    return normalized, candidate_type


# ─── manuf parsing ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ManufRow:
    """One Wireshark manuf data line, post-normalization."""

    raw_address: str
    normalized_identifier: str
    candidate_type: str          # 'oui' | 'mac_range'
    short_name: str
    long_name: str               # may be empty
    comment: str                 # may be empty (4th field, rare)
    raw_line: str                # full original line (for source_excerpt)


def parse_manuf(content: bytes) -> Iterator[ManufRow]:
    """Yield ManufRow per non-comment data line in a manuf file.

    Skips blank lines and `#`-prefixed comment lines (the file's header
    block). Lines that fail address-shape validation are logged at WARNING
    and skipped — Wireshark's file is curated, so a malformed line is a
    surprise we want to see in the logs but not a reason to abort the rest.
    """
    text = content.decode("utf-8", errors="replace")
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        # Wireshark's `manuf` is tab-separated; the field count in the
        # current snapshot is uniformly 3, but the format documents an
        # optional 4th `comment` field. Parse defensively for both.
        if len(fields) < 2:
            LOG.debug("skipping under-fielded line: %r", line)
            continue
        address = fields[0].strip()
        short_name = fields[1].strip()
        long_name = fields[2].strip() if len(fields) >= 3 else ""
        comment = fields[3].strip() if len(fields) >= 4 else ""
        try:
            normalized, candidate_type = normalize_address(address)
        except ValueError as e:
            LOG.warning("skipping line with bad address: %s — %r", e, line)
            continue
        yield ManufRow(
            raw_address=address,
            normalized_identifier=normalized,
            candidate_type=candidate_type,
            short_name=short_name,
            long_name=long_name,
            comment=comment,
            raw_line=line,
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


def _stage_raw_observations(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    extraction_run_id: int,
    rows: Iterable[ManufRow],
) -> tuple[int, dict[str, int]]:
    """Delete-by-source-id then bulk-insert. Returns (inserted, by_type)."""
    conn.execute("DELETE FROM raw_observations WHERE source_id = ?", (source_id,))

    by_type: dict[str, int] = {"oui": 0, "mac_range": 0}
    inserted = 0
    batch: list[tuple] = []
    BATCH_SIZE = 1000

    for r in rows:
        manufacturer = r.long_name or r.short_name
        excerpt = r.raw_line[:200]
        notes_obj: dict[str, str] = {"short_name": r.short_name}
        if r.comment:
            notes_obj["comment"] = r.comment
        notes = json.dumps(notes_obj, sort_keys=True)
        batch.append(
            (
                source_id,
                extraction_run_id,
                SOURCE_URL,
                None,                          # raw_payload — full file in raw/
                r.normalized_identifier,
                r.candidate_type,
                None,                          # candidate_category — Phase 5
                manufacturer,
                excerpt,
                notes,
            )
        )
        by_type[r.candidate_type] = by_type.get(r.candidate_type, 0) + 1
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
    return inserted, by_type


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
    by_type: dict[str, int]


def ingest(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    agent_id: str,
    raw_subdir: Optional[str] = None,
) -> IngestResult:
    """Fetch + parse + stage the Wireshark `manuf` file.

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

    LOG.info("Wireshark manuf ingest -> raw_dir=%s", raw_dir)

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
    manifest = {
        "fetched_at_utc": fetched_at if not raw_subdir else raw_subdir,
        "license_note": LICENSE_NOTE,
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
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

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
            rows = list(parse_manuf(body))
            staged, by_type = _stage_raw_observations(
                conn,
                source_id=sid,
                extraction_run_id=run_id,
                rows=rows,
            )
            _finish_run(
                conn,
                run_id,
                records_in=len(rows),
                records_out=staged,
                errors=0,
                status="ok",
                notes=(
                    f"registry={REGISTRY_TAG} sha256={sha} "
                    f"oui={by_type.get('oui', 0)} "
                    f"mac_range={by_type.get('mac_range', 0)} | "
                    "Wireshark manuf classified crowdsourced; "
                    "reconsider at Phase 5 if confidence band under-fits."
                ),
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
        rows_staged=staged,
        by_type=by_type,
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
        help="Reuse an existing raw/wireshark_manuf/<subdir>/ rather than re-fetching.",
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
    print(f"  by_type: {result.by_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
