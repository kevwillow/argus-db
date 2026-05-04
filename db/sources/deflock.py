"""DeFlock ingest (Phase 2 — Tier 1, source #4).

Pulls the DeFlock-via-CDN ALPR camera dataset into Argus staging per
PROJECT_BIBLE.md §6 Phase 2 + §7.2. Lands rows in `deployment_observations`
(migration 0002 / CP4 commit `d81de3b`). No new migration.

Source — CEO-ratified at MAC-6 (2026-05-04):
──────────────────────────────────────────────────────────────────────
URL:    https://cdn.deflock.me/regions/index.json (manifest)
        https://cdn.deflock.me/regions/{lat}/{lon}.json (per-tile, 20°)
Format: JSON. Manifest carries `regions: [...]` list of `{lat}/{lon}` keys
        + `tile_url` template + `tile_size_degrees=20` + `expiration_utc`.
        Each tile is a JSON array of `{id: int, lat: float, lon: float,
        tags: {...}}` objects. Tags are tag-whitelisted upstream by
        DeFlock's `serverless/alpr_cache/src/alpr_cache.py` lambda to
        9 keys: operator, manufacturer, brand, direction,
        camera:direction, surveillance:{brand,operator,manufacturer},
        wikimedia_commons.

Discovery & Path B (CDN) rationale (MAC-6 ratification, comment
[ed4a5465-…](/MAC/issues/MAC-6#comment-ed4a5465)):

  * Path A (`deflock.org/api/`) is dead under §11 #6 — robots.txt
    `User-agent: * / Disallow: /api/`.
  * Path B (`cdn.deflock.me`) is the licit, DeFlock-hosted endpoint
    that DeFlock's own frontend reads from. No robots restriction
    applies. Whitelist-as-PII-mitigation is a structural advantage
    over Path C (Overpass direct) — DeFlock's lambda strips freetext
    fields like `description`/`note` upstream of the CDN.
  * Path C (`overpass-api.de`) is technically defensible but loses
    DeFlock attribution and adds the freetext PII surface for no
    offsetting benefit.

Underlying data: OpenStreetMap, ODbL 1.0. DeFlock's MIT covers the
frontend repo only. Per CEO ratification (decision 7), the ODbL
attribution `"© OpenStreetMap contributors. ODbL 1.0."` is captured
verbatim in `sources.notes.license_attribution`; Phase-5 export must
carry that string downstream (Export Worker dispatch will state this
explicitly).

source_type:   `crowdsourced` (CEO-ratified at MAC-6 decision 2;
               same precedent as MAC-4/MAC-5; §8.2 50–75 band; OSM/ODbL
               nuance noted but not enum-extending — Phase 5 reconsider
               marker logged in `extraction_runs.notes`).

tier:          1 (per Bible §5).

source_url:    `https://cdn.deflock.me/regions/index.json` (dataset URL
               per CEO ratification decision 3; per-tile URL captured in
               `notes.tile_url`; mirrors MAC-5 dataset-URL pattern).

source_row_key: `str(osm_id)` (CEO ratification decision 4; 0 collisions
                on the 101,597-node 2026-05-04 snapshot; OSM IDs
                globally unique by spec).

────────────────────────────────────────────────────────────────────────
§11 #1 — no fabrication
────────────────────────────────────────────────────────────────────────
Every row in this dataset is selected by DeFlock's upstream Overpass
query `node["man_made"="surveillance"]["surveillance:type"="ALPR"]; out
body;`. The whole dataset is ALPR by source-construction predicate.
Encoding `technology_category="ALPR"` is therefore not §11 #1
fabrication — it is the predicate by which the source was built. CEO
ratification decision 6 logs this rationale; Phase 5 inference may
re-derive category from observed tags if the predicate ever broadens.

Identifier columns (MAC/OUI/SSID/UUID) are absent from
`deployment_observations` per §11 #1 / §4.2 / CP4. DeFlock yields
geolocation + agency + vendor metadata; no identifier promotion at
ingest.

────────────────────────────────────────────────────────────────────────
§11 #3 — PII redaction (CEO ratification decision 5)
────────────────────────────────────────────────────────────────────────
The CDN whitelist already strips freetext fields (`description`,
`note`) upstream — those are the natural carriers of officer-name PII.
Inside the 9 whitelisted keys, the only fields that could plausibly
carry person names are `operator` / `surveillance:operator` and (rarely)
`manufacturer` / `brand`. We apply the same rank-token person regex
shape as MAC-5 / EFF Atlas — recall over precision per CP4 — and
collapse matches to `[REDACTED-PERSON]` in both `notes` JSON and the
top-level `agency_name` / `vendor_raw` columns.

Plate regex is intentionally NOT applied. Decision 5 rationale: the
structured `direction` field is a compass-bearing string (e.g.
`"165-235"`, `"180;160;170"`) that pattern-matches a plate regex with
3,731 false-positives and 0 true positives on the 2026-05-04 snapshot.
Applying it would scramble legitimate data with no PII benefit. The
CDN whitelist makes Path B structurally safer than Path C on this
axis. **Phase-5 reconsider trigger** (decision 5 tightening):
revalidate plate regex if upstream `alpr_cache.py` whitelist changes
(e.g. `description` / `note` keys propagated). Logged in
`extraction_runs.notes`.

The full untouched raw response for every tile is preserved verbatim
in `raw/deflock/<ts>/regions/<lat>_<lon>.json` (§7.2 audit trail).
Redacted form is what lands in DB.

────────────────────────────────────────────────────────────────────────
Idempotency
────────────────────────────────────────────────────────────────────────
Same shape as MAC-3 / MAC-4 / MAC-5: delete-by-`source_id` then
bulk-insert in a single transaction. The `UNIQUE(source_id,
source_row_key)` index on `deployment_observations` is the structural
backstop; re-running this ingest on the same `--raw-subdir` produces
identical row counts and never duplicates.
"""

from __future__ import annotations

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


LOG = logging.getLogger("argus.ingest.deflock")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "deflock"

SOURCE_NAME = "DeFlock (OSM-mirrored ALPR camera locations via cdn.deflock.me)"
SOURCE_URL = "https://cdn.deflock.me/regions/index.json"
SOURCE_INDEX_FILENAME = "regions-index.json"
SOURCE_TILES_DIRNAME = "regions"
SOURCE_TYPE = "crowdsourced"  # §4.1 enum — CEO-ratified at MAC-6 decision 2.
TIER = 1                       # §5 — Tier 1 structured source.

LICENSE_NOTE = (
    "Underlying data: OpenStreetMap, ODbL 1.0 "
    "(https://opendatacommons.org/licenses/odbl/1-0/) — DeFlock is a "
    "thin frontend that writes to + reads from OSM; cdn.deflock.me serves "
    "a tag-whitelisted reprojection of OSM Overpass results. DeFlock's "
    "own license metadata: MIT (frontend repo), but the data layer is "
    "OSM/ODbL."
)
LICENSE_ATTRIBUTION = (
    "© OpenStreetMap contributors. Data available under the Open Database "
    "License (ODbL) 1.0. https://www.openstreetmap.org/copyright — "
    "Reflected through DeFlock's CDN at cdn.deflock.me, refreshed hourly "
    "by the FoggedLens/deflock alpr_cache lambda."
)

REGISTRY_TAG = "deflock"

# Constant technology category — every node selected by the upstream
# Overpass filter `surveillance:type=ALPR` (CEO decision 6).
TECHNOLOGY_CATEGORY = "ALPR"

# DeFlock CDN tag whitelist (FoggedLens/deflock
# `serverless/alpr_cache/src/alpr_cache.py`). Verified on 2026-05-04 snapshot
# — every observed key on disk is one of these 9.
WHITELISTED_TAGS = (
    "operator",
    "manufacturer",
    "brand",
    "direction",
    "camera:direction",
    "surveillance:brand",
    "surveillance:operator",
    "surveillance:manufacturer",
    "wikimedia_commons",
)


# ─── PII redaction (§11 #3, CEO decision 5) ───────────────────────────────


# Mirrors MAC-5 / EFF Atlas regex — recall-first per CP4. Applied to
# whitelisted-tag VALUES across all 9 keys; the raw payload on disk is
# untouched. See module docstring for the Phase-5 reconsider trigger.
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

REDACTION_MARKER = "[REDACTED-PERSON]"


def redact_pii(value: str) -> tuple[str, int]:
    """Return (redacted_text, hit_count). Empty input → ("", 0)."""
    if not value:
        return value or "", 0
    hits = 0

    def _sub(_m: re.Match[str]) -> str:
        nonlocal hits
        hits += 1
        return REDACTION_MARKER

    redacted = PII_REGEX.sub(_sub, value)
    return redacted, hits


# ─── HTTP fetch ────────────────────────────────────────────────────────────


def _fetch(url: str, timeout: int = 60) -> tuple[bytes, int]:
    """Single-shot HTTP fetch with one transient-error retry.

    Mirrors `eff_atlas._fetch`. Per §7.2 Don'ts: no silent infinite retries.
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


# ─── DeFlock JSON parsing ──────────────────────────────────────────────────


@dataclass(frozen=True)
class DeflockNode:
    """One DeFlock CDN node, post-redaction.

    Tag values are PII-redacted before landing on the dataclass. The raw
    untouched payload remains on disk in `raw/deflock/<ts>/regions/...`.
    """

    osm_id: int
    lat: float
    lon: float
    tile: str  # e.g. "40/-100"
    tags_redacted: dict[str, str]
    redaction_hits: int
    # Convenience extractions (raw values, post-redaction).
    operator: Optional[str]
    vendor: Optional[str]
    direction: Optional[str]


def _pick_first(tags: dict[str, str], keys: Iterable[str]) -> Optional[str]:
    """First non-empty tag value across `keys`, in order."""
    for k in keys:
        v = tags.get(k)
        if v:
            return v
    return None


def parse_index(index_bytes: bytes) -> tuple[list[str], str, int]:
    """Return (regions, tile_url_template, tile_size_degrees)."""
    obj = json.loads(index_bytes.decode("utf-8"))
    regions = obj.get("regions") or []
    tile_url = obj.get("tile_url") or ""
    tile_size = int(obj.get("tile_size_degrees") or 20)
    if not isinstance(regions, list) or not all(isinstance(r, str) for r in regions):
        raise ValueError("DeFlock index 'regions' must be list[str]")
    return regions, tile_url, tile_size


def parse_tile(tile_bytes: bytes, tile_key: str) -> Iterator[DeflockNode]:
    """Yield DeflockNode per node. Skips malformed entries with a warning."""
    obj = json.loads(tile_bytes.decode("utf-8"))
    if not isinstance(obj, list):
        raise ValueError(f"DeFlock tile {tile_key} must be a JSON array")
    for entry in obj:
        if not isinstance(entry, dict):
            LOG.warning("skipping non-dict entry in tile %s", tile_key)
            continue
        try:
            osm_id = int(entry["id"])
            lat = float(entry["lat"])
            lon = float(entry["lon"])
        except (KeyError, TypeError, ValueError):
            LOG.warning("skipping malformed entry in tile %s: %r", tile_key, entry)
            continue
        raw_tags = entry.get("tags") or {}
        if not isinstance(raw_tags, dict):
            raw_tags = {}
        # Redact every tag value; surface unknown keys for monitoring but
        # preserve them (the upstream whitelist is the structural guarantee,
        # not our re-filter).
        redacted_tags: dict[str, str] = {}
        total_hits = 0
        for k, v in raw_tags.items():
            if not isinstance(v, str):
                v = "" if v is None else str(v)
            r, hits = redact_pii(v)
            redacted_tags[k] = r
            total_hits += hits
            if k not in WHITELISTED_TAGS:
                LOG.warning(
                    "tile %s node %d carries non-whitelisted tag key %r — "
                    "preserved verbatim, surface for Phase-5 reconsider",
                    tile_key,
                    osm_id,
                    k,
                )
        operator = _pick_first(
            redacted_tags, ("operator", "surveillance:operator")
        )
        vendor = _pick_first(
            redacted_tags,
            (
                "manufacturer",
                "surveillance:manufacturer",
                "brand",
                "surveillance:brand",
            ),
        )
        direction = _pick_first(
            redacted_tags, ("direction", "camera:direction")
        )
        yield DeflockNode(
            osm_id=osm_id,
            lat=lat,
            lon=lon,
            tile=tile_key,
            tags_redacted=redacted_tags,
            redaction_hits=total_hits,
            operator=operator,
            vendor=vendor,
            direction=direction,
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
    tile_url_template: str,
    tile_size_degrees: int,
    region_count: int,
    node_count: int,
) -> int:
    notes = json.dumps(
        {
            "registry": REGISTRY_TAG,
            "license": LICENSE_NOTE,
            "license_attribution": LICENSE_ATTRIBUTION,
            "byte_count": byte_count,        # index byte_count
            "content_sha256": content_hash,  # index sha256
            "http_status": http_status,
            "tile_url_template": tile_url_template,
            "tile_size_degrees": tile_size_degrees,
            "region_count": region_count,
            "node_count": node_count,
            "phase5_reconsider": (
                "if upstream cdn.deflock.me alpr_cache.py whitelist changes "
                "(e.g. description/note keys propagated), revalidate plate "
                "regex; revalidate source_type='crowdsourced' band fit"
            ),
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
    by_vendor: dict[str, int] = field(default_factory=dict)
    by_operator: dict[str, int] = field(default_factory=dict)
    nodes_with_operator: int = 0
    nodes_with_vendor: int = 0
    redaction_hits_total: int = 0
    redacted_osm_ids: list[str] = field(default_factory=list)
    nontags_keys_seen: set[str] = field(default_factory=set)


def _stage_deployment_observations(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    extraction_run_id: int,
    tile_url_template: str,
    nodes: Iterable[DeflockNode],
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
        "source_excerpt, notes"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    def _flush() -> None:
        if not batch:
            return
        conn.executemany(sql, batch)
        stats.inserted += len(batch)
        batch.clear()

    for n in nodes:
        # Per-tile URL captured in notes (decision 3); no per-row external
        # citation in the CDN payload (decision: citation_url stays NULL,
        # mirroring MAC-5 dataset-URL pattern).
        lat_str, lon_str = n.tile.split("/", 1)
        per_tile_url = (
            tile_url_template.replace("{lat}", lat_str).replace("{lon}", lon_str)
            if tile_url_template
            else None
        )

        notes_obj: dict[str, object] = {
            "tile": n.tile,
            "tile_url": per_tile_url,
            "tags_redacted": n.tags_redacted,
            "redaction_hits": n.redaction_hits,
            "direction": n.direction,
        }
        notes = json.dumps(notes_obj, sort_keys=True)

        batch.append(
            (
                source_id,
                extraction_run_id,
                SOURCE_URL,                # dataset URL per decision 3
                str(n.osm_id),             # source_row_key per decision 4
                n.operator,                # agency_name (post-redaction)
                None,                      # agency_type — no equivalent in DeFlock
                None,                      # juris_type — no equivalent
                None,                      # city — DeFlock only has lat/lon
                None,                      # county
                None,                      # state
                None,                      # country — §7.2 do not normalize
                n.lat,
                n.lon,
                TECHNOLOGY_CATEGORY,       # constant per decision 6
                n.vendor,                  # vendor_raw (post-redaction)
                None,                      # citation_url — no per-row citation
                None,                      # source_excerpt — no narrative text
                notes,
            )
        )

        if n.operator:
            stats.nodes_with_operator += 1
            stats.by_operator[n.operator] = stats.by_operator.get(n.operator, 0) + 1
        if n.vendor:
            stats.nodes_with_vendor += 1
            stats.by_vendor[n.vendor] = stats.by_vendor.get(n.vendor, 0) + 1
        if n.redaction_hits:
            stats.redaction_hits_total += n.redaction_hits
            stats.redacted_osm_ids.append(str(n.osm_id))
        for k in n.tags_redacted:
            if k not in WHITELISTED_TAGS:
                stats.nontags_keys_seen.add(k)

        if len(batch) >= BATCH_SIZE:
            _flush()
    _flush()
    return stats


# ─── Public entry point ────────────────────────────────────────────────────


@dataclass
class IngestResult:
    raw_dir: Path
    fetched_at_utc: str
    index_path: Path
    index_byte_count: int
    index_sha256: str
    index_http_status: int
    region_count: int
    tile_url_template: str
    tile_size_degrees: int
    sources_id: int
    extraction_run_id: int
    rows_staged: int
    redaction_hits_total: int
    redacted_osm_ids: list[str]
    nodes_with_operator: int
    nodes_with_vendor: int
    by_vendor: dict[str, int]
    by_operator: dict[str, int]
    nontags_keys_seen: set[str]


def _read_or_fetch_index(
    raw_dir: Path, raw_subdir: Optional[str]
) -> tuple[bytes, int, str]:
    index_path = raw_dir / SOURCE_INDEX_FILENAME
    if index_path.exists() and raw_subdir:
        body = index_path.read_bytes()
        return body, 200, SOURCE_URL
    LOG.info("fetching %s", SOURCE_URL)
    body, http_status = _fetch(SOURCE_URL)
    index_path.write_bytes(body)
    return body, http_status, SOURCE_URL


def _read_or_fetch_tile(
    *,
    raw_dir: Path,
    raw_subdir: Optional[str],
    tile_url_template: str,
    region: str,
) -> tuple[bytes, int]:
    """Return (body, http_status). `region` is e.g. '40/-100'."""
    lat_part, lon_part = region.split("/", 1)
    tile_path = raw_dir / SOURCE_TILES_DIRNAME / f"{lat_part}_{lon_part}.json"
    if tile_path.exists() and raw_subdir:
        return tile_path.read_bytes(), 200
    if not tile_url_template:
        raise ValueError("tile_url_template is empty; cannot fetch tile")
    url = tile_url_template.replace("{lat}", lat_part).replace("{lon}", lon_part)
    body, http_status = _fetch(url)
    tile_path.parent.mkdir(parents=True, exist_ok=True)
    tile_path.write_bytes(body)
    return body, http_status


def ingest(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    agent_id: str,
    raw_subdir: Optional[str] = None,
) -> IngestResult:
    """Fetch + parse + stage the DeFlock CDN dataset.

    `raw_subdir`: if given, reuse an existing raw/<ts>/ directory.
    Otherwise fetch fresh into raw/<UTC-timestamp>/. Per CEO ratification
    at MAC-6, the in-flight invocation passes
    `raw_subdir='20260504T052752Z'` to reuse the pre-staged snapshot
    (no re-fetch).
    """
    fetched_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if raw_subdir:
        raw_dir = raw_root / raw_subdir
        if not raw_dir.exists():
            raise FileNotFoundError(f"raw_subdir {raw_dir} does not exist")
    else:
        raw_dir = raw_root / fetched_at
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / SOURCE_TILES_DIRNAME).mkdir(parents=True, exist_ok=True)

    LOG.info("DeFlock ingest -> raw_dir=%s", raw_dir)

    index_body, index_status, _ = _read_or_fetch_index(raw_dir, raw_subdir)
    index_sha = hashlib.sha256(index_body).hexdigest()
    regions, tile_url_template, tile_size_degrees = parse_index(index_body)

    LOG.info(
        "index ok: %d regions, tile_url=%s, tile_size=%d°",
        len(regions),
        tile_url_template,
        tile_size_degrees,
    )

    # Iterate tiles → nodes; pre-load all nodes into memory (101,597 small
    # dicts on the 2026-05-04 snapshot is well below any sane memory cap).
    all_nodes: list[DeflockNode] = []
    for region in regions:
        tile_body, _status = _read_or_fetch_tile(
            raw_dir=raw_dir,
            raw_subdir=raw_subdir,
            tile_url_template=tile_url_template,
            region=region,
        )
        tile_nodes = list(parse_tile(tile_body, region))
        all_nodes.extend(tile_nodes)

    # Stable sort by osm_id for deterministic insert order across re-runs.
    all_nodes.sort(key=lambda n: n.osm_id)
    LOG.info("parsed %d nodes across %d tiles", len(all_nodes), len(regions))

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        sid = _upsert_source(
            conn,
            fetched_at=_utc_now(),
            http_status=index_status,
            byte_count=len(index_body),
            content_hash=index_sha,
            tile_url_template=tile_url_template,
            tile_size_degrees=tile_size_degrees,
            region_count=len(regions),
            node_count=len(all_nodes),
        )
        run_id = _start_run(conn, agent_id=agent_id, source_id=sid)
        try:
            stats = _stage_deployment_observations(
                conn,
                source_id=sid,
                extraction_run_id=run_id,
                tile_url_template=tile_url_template,
                nodes=all_nodes,
            )
            redacted_list_str = ",".join(stats.redacted_osm_ids)
            run_notes = (
                f"registry={REGISTRY_TAG} index_sha256={index_sha} "
                f"regions={len(regions)} nodes_in={len(all_nodes)} "
                f"rows_out={stats.inserted} | "
                f"§11 #3 PII redaction (person regex only): "
                f"hits={stats.redaction_hits_total} across "
                f"{len(stats.redacted_osm_ids)} node(s); "
                f"osm_ids=[{redacted_list_str}]; "
                "raw payloads preserved verbatim on disk per §7.2 — "
                "redacted form lands in deployment_observations.notes only. "
                "Plate regex deliberately skipped on Path B per CEO MAC-6 "
                "decision 5 (CDN whitelist excludes freetext fields; "
                "direction-string false-positive scrambling has 0 PII benefit). "
                "Phase-5 reconsider if upstream alpr_cache.py whitelist changes. "
                "DeFlock classified crowdsourced (decision 2 / MAC-4/MAC-5 "
                "precedent); reconsider band fit at Phase 5. "
                "technology_category=ALPR constant per decision 6 — Overpass "
                "predicate surveillance:type=ALPR is the source-construction "
                "filter, not §11 #1 fabrication."
            )
            _finish_run(
                conn,
                run_id,
                records_in=len(all_nodes),
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
        index_path=raw_dir / SOURCE_INDEX_FILENAME,
        index_byte_count=len(index_body),
        index_sha256=index_sha,
        index_http_status=index_status,
        region_count=len(regions),
        tile_url_template=tile_url_template,
        tile_size_degrees=tile_size_degrees,
        sources_id=sid,
        extraction_run_id=run_id,
        rows_staged=stats.inserted,
        redaction_hits_total=stats.redaction_hits_total,
        redacted_osm_ids=stats.redacted_osm_ids,
        nodes_with_operator=stats.nodes_with_operator,
        nodes_with_vendor=stats.nodes_with_vendor,
        by_vendor=stats.by_vendor,
        by_operator=stats.by_operator,
        nontags_keys_seen=stats.nontags_keys_seen,
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
        help="Reuse an existing raw/deflock/<subdir>/ rather than re-fetching.",
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
    print(f"index_byte_count: {result.index_byte_count}")
    print(f"index_sha256: {result.index_sha256}")
    print(f"region_count: {result.region_count}")
    print(f"tile_url_template: {result.tile_url_template}")
    print(f"tile_size_degrees: {result.tile_size_degrees}")
    print(f"sources_id: {result.sources_id}")
    print(f"extraction_run_id: {result.extraction_run_id}")
    print(f"rows_staged: {result.rows_staged}")
    print(
        f"redaction_hits_total: {result.redaction_hits_total} "
        f"(across {len(result.redacted_osm_ids)} nodes)"
    )
    print(
        f"nodes_with_operator: {result.nodes_with_operator} | "
        f"nodes_with_vendor: {result.nodes_with_vendor}"
    )
    if result.nontags_keys_seen:
        print(f"non-whitelisted tag keys observed: {sorted(result.nontags_keys_seen)}")
    print("top 10 vendors (post-redaction, raw labels):")
    for v, n in sorted(result.by_vendor.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {v}: {n}")
    print("top 10 operators (post-redaction, raw labels):")
    for v, n in sorted(result.by_operator.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {v}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
