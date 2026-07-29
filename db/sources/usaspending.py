"""USAspending.gov procurement award ingest (Phase 3 — Tier 2, source 2/4).

Pulls federal contract awards mentioning canonical surveillance vendors
(`manufacturers.canonical_name`) into the `procurement_records` staging
table per PROJECT_BIBLE.md §6 Phase 3 + §4.5 procurement-only carveout
+ §7.2 (Source Worker contract). Ratified by CEO at MAC-8 Step 1
([4816dd57-3a40-4dcc-98bf-c7df357cbec8](/MAC/issues/MAC-8#comment-4816dd57)).

Source
──────
Dataset URL:  https://api.usaspending.gov/api/v2/search/spending_by_award/
              (POST, paginated, keyword-by-vendor)
Per-row URL:  https://www.usaspending.gov/award/<generated_internal_id>
              (canonical award page; lands in procurement_records.source_url)

Format:       JSON. POST body filters on `keywords`, `award_type_codes`,
              `time_period`. `fields` array selects 17 columns including
              `Place of Performance State Code`, `PSC Code`, `NAICS Code`,
              `Awarding Sub Agency`, `recipient_id`, `generated_internal_id`.

License:      USGOV_WORKS / Public Domain U.S. Government — 17 U.S.C. §105
              (https://www.usa.gov/government-works). Same regime as
              MAC-7 (Decision 1) and SAR-4 routing not needed (canonical
              published bulk path).

source_type:  `procurement` (§4.1 enum, matches existing CHECK on
              procurement_records.source_type).
tier:         2 (per Bible §5; structured federal procurement).

confidence:   85 (top of §8.2 procurement band 70-85 — CEO correction at
              MAC-8 Step 1 ratification, vs worker's proposed 90 which
              cited "§8.2 official band" in error). The §8.2 cap is
              structural ("proves *purchase*, not *deployment*") and
              binds regardless of upstream Treasury data quality.

────────────────────────────────────────────────────────────────────────────
Vendor sweep — keyword set
────────────────────────────────────────────────────────────────────────────
Q6 ratification: full ~24-vendor list, no trimming. Worker-proposed list
covers MAC-7 Group A + Group B union (effectively the whole §2.1 enum =
`manufacturers.canonical_name` table). Keyword matching is API-side
case-insensitive over `Recipient Name` and `Description` fields. Resellers
(Atlantic Diving Supply, RedHawk IT, COMSONICS, SAF Technologies,
Convergint) surface vendor-mentioning awards via Description; we stage
the reseller's `Recipient Name` verbatim per §4.3 (raw is raw, no
canonicalization at staging) and record the matched-keyword set in
`notes.keyword_match[]` so Phase 5 can disambiguate vendor-via-description
vs vendor-as-recipient.

The vendor list is read from `manufacturers.canonical_name` at run time
so a future Correction Pass that adds/removes vendors auto-syncs without
a code edit.

────────────────────────────────────────────────────────────────────────────
Filters (Q4 + Q5 ratification)
────────────────────────────────────────────────────────────────────────────
Q4: `award_type_codes = ['A','B','C','D']`. Definitive contract types
only — IDV umbrellas (`IDV_*`) excluded to avoid double-counting parent
vehicles + child orders.

Q5: time_period 2007-10-01 → 2026-05-04 (search API earliest is
2007-10-01 per `messages` field in test response). Covers Flock 2017+,
body-cam 2014+, partial federal Stingray 2007+. Bulk_download pre-2007
backfill is Phase 4 territory if ever needed.

────────────────────────────────────────────────────────────────────────────
Schema-fit + idempotency
────────────────────────────────────────────────────────────────────────────
`procurement_records` (DDL `db/migrations/0001_initial.sql:205-220`)
fits cleanly. NO migration this round — the existing CHECK accepts
`source_type='procurement'`; the schema has no `source_id`/
`source_row_key`/`extraction_run_id` columns by design (§4.5 carveout
predates the Phase-2 staging-table convention).

Idempotency: structural backstop is `DELETE FROM procurement_records
WHERE source_url LIKE 'https://www.usaspending.gov/award/%'` at the
start of each run. Within-run, multi-vendor keyword overlap is
de-duplicated by `generated_internal_id` (Q3 ratification — USAspending's
stable per-award canonical key, present on every search response;
PIID alone collides across agencies). All matched keywords for a given
award are accumulated into `notes.keyword_match[]` so a single award
hit by both `Cradlepoint` and `Sierra Wireless` queries is staged once
with both keywords recorded.

────────────────────────────────────────────────────────────────────────────
Q1 — vendor_canonical_name = raw verbatim (CEO Option A)
────────────────────────────────────────────────────────────────────────────
The DDL column name `vendor_canonical_name` is misleading vs §4.3
"no canonicalization at staging." Per CEO Option A: stage `Recipient
Name` verbatim into `vendor_canonical_name`; the staging-as-raw choice
is documented in `extraction_runs.notes`. Mirrors MAC-3/4/5/7
staging-as-raw precedent — no Phase-2/3 ingest ever canonicalized at
staging. Cosmetic Option B (additive `vendor_raw` column, bumping the
0004_*.sql slot) was rejected as not load-bearing.

────────────────────────────────────────────────────────────────────────────
Q2 — agency_geographic_scope (CEO Option b)
────────────────────────────────────────────────────────────────────────────
agency_geographic_scope = `Place of Performance State Code` (e.g. `US-DC`
for Flock USPP award). Subnational join axis is the load-bearing
cross-source-overlap signal with DeFlock geolocation. Fallback `'US-FED'`
only when state_code is null. Bible §4.1 sample is `US-CA`; we conform
to the `US-<2-letter>` shape. Mechanical award-side `'US-FED'` was
rejected — would discard the most useful join axis.

────────────────────────────────────────────────────────────────────────────
§11 #3 — PII posture (stage-as-is, ratified)
────────────────────────────────────────────────────────────────────────────
Empirical Step-1 finding: `/api/v2/search/spending_by_award/` and
per-award detail (`/api/v2/awards/<id>/`) return ZERO contracting-officer-
shape keys. `executive_details.officers` block in detail is recipient
corporate execs (not contracting officers) and Flock Group Inc has all 5
slots `null`. Person-regex sweep on Step-1 sample (23 records) returned
0 hits.

Per CEO ratification: no redaction needed at staging. Phase-5 reconsider
hook logged in `extraction_runs.notes` — stop-the-line ONLY if Step-2
pagination surfaces a contracting-officer-shape field absent from the
search/detail surface (e.g. if FPDS NG raw transactions or
`bulk_download` CSVs ever land additional columns). Mirrors MAC-7
contact_name corporate-comms read (CP6 ride-along context, NOT a new
SAR).

────────────────────────────────────────────────────────────────────────────
recipient_uei — search-API-only deferral
────────────────────────────────────────────────────────────────────────────
`recipient_uei` is only populated by the per-award detail endpoint
(`/api/v2/awards/<generated_internal_id>/`), not by search. Q5 ratifies
search-API-only at Step 2. Per-award detail at scale would multiply
HTTP calls by the per-vendor result count (24 × N pages = potentially
hundreds of detail calls). We leave `recipient_uei = null` in
`notes.raw_row` at staging; Phase 5 vendor-side UEI/CAGE-code
disambiguation joins (already deferred to Phase 5 per CEO source decision)
own the detail-pass if/when it lands. Search-side `recipient_id`
(opaque hash per recipient) IS captured.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import logging
import re
import socket
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional


LOG = logging.getLogger("argus.ingest.usaspending")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "sam_gov"

API_BASE = "https://api.usaspending.gov"
SEARCH_ENDPOINT = f"{API_BASE}/api/v2/search/spending_by_award/"
WEB_AWARD_BASE = "https://www.usaspending.gov/award/"

SOURCE_NAME = "USAspending.gov public award API (api.usaspending.gov spending_by_award)"
SOURCE_URL = SEARCH_ENDPOINT
SOURCE_TYPE = "procurement"  # §4.1 enum.
TIER = 2                     # §5 — structured federal procurement.
CONFIDENCE = 85              # CEO correction — §8.2 procurement band 70–85, top.
CONFIDENCE_BAND = "70-85"

LICENSE_NOTE = (
    "License: USGOV_WORKS / Public Domain U.S. Government — "
    "https://www.usa.gov/government-works (17 U.S.C. §105)"
)
LICENSE_ATTRIBUTION = (
    "Public Domain U.S. Government — https://www.usa.gov/government-works "
    "(USAspending.gov / U.S. Department of the Treasury Bureau of the "
    "Fiscal Service public bulk; 17 U.S.C. §105)"
)

# Q4 ratification — definitive contract types only.
AWARD_TYPE_CODES = ("A", "B", "C", "D")

# Q5 ratification — search-API-only window, 2007-10-01 → 2026-05-04.
TIME_PERIOD_START = "2007-10-01"
TIME_PERIOD_END = "2026-05-04"

# Pagination — USAspending search API page-size cap.
PAGE_LIMIT = 100

# Rate-limit (CEO ratified — public bulk, NOT a Checkpoint-3a-class question).
REQ_INTERVAL_SECONDS = 1.0

# 17 fields requested per Step-1 vendor-probe responses (verified shape).
SEARCH_FIELDS = [
    "Award ID",
    "Recipient Name",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Award Amount",
    "Description",
    "Period of Performance Start Date",
    "Period of Performance Current End Date",
    "Last Modified Date",
    "NAICS Code",
    "PSC Code",
    "recipient_id",
    "Place of Performance State Code",
    "awarding_agency_id",
    "agency_slug",
    "generated_internal_id",
]

REGISTRY_TAG = "usaspending"

PHASE5_RECONSIDER_PII = (
    "USAspending search/detail surfaces returned ZERO contracting-officer-"
    "shape keys at MAC-8 Step 1 (CEO-ratified stage-as-is). Reconsider at "
    "Phase 5 if cross-source name match utility shifts toward consolidated "
    "people-data redaction across all sources, OR if a future ingest pulls "
    "FPDS NG raw transactions / bulk_download CSVs that surface additional "
    "contracting-officer-shape columns absent from search/detail."
)

RESELLER_PATTERN_NOTE = (
    "Recipient Name staged verbatim (raw is raw, §4.3) per Q1 Option A. "
    "When Recipient Name ≠ vendor (e.g. Atlantic Diving Supply / RedHawk IT "
    "/ COMSONICS / SAF Technologies / Convergint), the matched vendor "
    "keyword is recorded in notes.keyword_match[] so Phase 5 can "
    "disambiguate vendor-via-description vs vendor-as-recipient."
)


# ─── PII person regex (audit-only — Q4 stage-as-is per CEO ratification) ──


# Same MAC-5/MAC-6/MAC-7 codified rank-token list. Audit-only on
# USAspending: we count + log hits across `Description`, `Recipient Name`,
# and composed `Awarding Agency / Sub Agency`; never redact. Per Step-1
# evidence, expected hit count is ~0.
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


def count_pii_hits(value: Optional[str]) -> tuple[int, list[str]]:
    """Audit-only person-regex sweep. Returns (hit_count, matched_strings)."""
    if not value:
        return 0, []
    matches = [m.group(0) for m in PII_REGEX.finditer(value)]
    return len(matches), matches


# ─── HTTP fetch ────────────────────────────────────────────────────────────


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_post(
    url: str,
    body: dict,
    *,
    timeout: int = 60,
) -> tuple[bytes, int]:
    """Single-shot POST with JSON body and one transient-error retry.

    Mirrors `db/sources/eff_atlas.py::_fetch` shape. Per §7.2 Don'ts: no
    silent infinite retries. Per CEO ratification: 1 req/s + single-shot
    transient retry, NOT a Checkpoint-3a-class budget question (public
    bulk endpoint, no observed throttling).
    """
    body_bytes = json.dumps(body).encode("utf-8")
    last_exc: Optional[BaseException] = None
    # Transient errors that warrant a one-shot retry. Beyond URLError we
    # also see RemoteDisconnected / ConnectionResetError under load on
    # USAspending — observed in MAC-8 Step 2 fresh-fetch run.
    transient_excs: tuple[type[BaseException], ...] = (
        urllib.error.URLError,
        http.client.RemoteDisconnected,
        http.client.IncompleteRead,
        http.client.BadStatusLine,
        ConnectionResetError,
        ConnectionAbortedError,
        TimeoutError,
        socket.timeout,
    )
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(
                url,
                data=body_bytes,
                method="POST",
                headers={
                    "User-Agent": "argus-ingest/0.1 (+contact: argus-ingest)",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = resp.read()
                status = resp.getcode()
                return payload, status
        except urllib.error.HTTPError:
            raise
        except transient_excs as e:
            LOG.warning(
                "transient fetch error on attempt %d for %s: %s (%s)",
                attempt, url, type(e).__name__, e,
            )
            last_exc = e
            if attempt == 2:
                raise
            # Brief back-off before the second attempt.
            time.sleep(2.0)
    assert last_exc is not None
    raise last_exc


# ─── Vendor list (read from manufacturers seed at run time) ───────────────


# Per-vendor keyword overrides for known-noisy single-token canonical names.
# USAspending's `keywords` filter matches against `Recipient Name` and
# `Description` fields; single common-word labels return tens of thousands
# of FPs (BMO Harris Bank, Harris County, Major-prefix mil descriptions,
# etc.). The override is a more-specific phrase pulled from the row's
# `aliases` column or, where none exists, from MAC-7's documented
# corp-disambig finding (PROJECT_STATE.md line 46: `\bHarris\b` 21 split as
# 13 Harris Corporation + 5 GE Harris JV + 2 BMO/Bmoh Harris Bank FP +
# 1 Harris 3M JV). Phase 5 disambig pass owns finer-grained vendor↔award
# pairing.
#
# The ratified Q6 contract is "full ~24-vendor list, no trimming"; the
# vendor universe is unchanged. This override only affects the search
# *keyword* phrasing within each vendor's query, not the vendor's
# inclusion. The override choice is logged in extraction_runs.notes.
#
# MAC-577 — this table is the ASK side and it is NOT a control.
# `extraction_runs.id=15` notes record `keyword_overrides_applied` with
# `"Reveal": "Reveal Media"`, i.e. the override below WAS in force for the
# sweep. Reveal still returned 66 rows, of which exactly 1 contains the
# phrase "Reveal Media" (the other 65 are REVEAL GLOBAL CONSULTING, REVEAL
# IMAGING TECHNOLOGIES, REVEAL BIOSCIENCES, REVEAL TECHNOLOGY). USAspending's
# `keywords` filter does not honour a multi-word value as a phrase, so this
# table constrains what we ask for and never what we accept.
# The ACCEPT-side control is `db/matching_policy.py`; that is where a
# common-word / short-single-token canonical is actually stopped from
# attributing on its bare name. Keep the two in the same direction: a
# canonical in `matching_policy.ALIAS_ONLY_CANONICALS` should also have an
# entry here. `STOP` and `Rekor` are currently accept-side-only — deliberate,
# so this freeze does not change what a live sweep queries.
KEYWORD_OVERRIDES: dict[str, str] = {
    "Harris": "Harris Corporation",            # alias; pre-2019 IMSI legacy entity
    "Jacobs": "Jacobs Engineering",            # alias; pre-2019 acquirer of Engility
    "KeyW": "KeyW Corporation",                # alias; more specific
    "Reveal": "Reveal Media",                  # alias; body-cam vendor
}


def load_vendor_keywords(
    conn: sqlite3.Connection,
) -> list[tuple[str, str]]:
    """Return [(canonical_name, keyword_used)] pairs from manufacturers.

    `canonical_name` is the row's primary label and is what gets recorded
    against the vendor in stats. `keyword_used` is the actual API search
    string — usually the canonical_name verbatim, but overridden for
    known-noisy single-token labels (see `KEYWORD_OVERRIDES`).

    Reading at run time means a future Correction Pass that adds/removes
    a vendor auto-syncs without a code edit.
    """
    # CP31 (migration 0025) — only fire USAspending API queries for hub
    # canonicals; arms participate through their hub's procurement footprint.
    rows = conn.execute(
        "SELECT canonical_name FROM manufacturers "
        "WHERE query_default = 'visible' "
        "ORDER BY canonical_name"
    ).fetchall()
    pairs: list[tuple[str, str]] = []
    for (canonical,) in rows:
        keyword = KEYWORD_OVERRIDES.get(canonical, canonical)
        pairs.append((canonical, keyword))
    return pairs


# ─── Per-vendor pagination ─────────────────────────────────────────────────


@dataclass
class VendorFetchStats:
    canonical_name: str
    keyword: str
    pages_fetched: int = 0
    raw_results_total: int = 0
    raw_filename: str = ""
    raw_sha256: str = ""
    raw_byte_count: int = 0
    has_zero_results: bool = False
    last_http_status: int = 0
    page_cap_hit: bool = False


def _build_search_body(keyword: str, page: int) -> dict:
    return {
        "filters": {
            "keywords": [keyword],
            "award_type_codes": list(AWARD_TYPE_CODES),
            "time_period": [
                {"start_date": TIME_PERIOD_START, "end_date": TIME_PERIOD_END}
            ],
        },
        "fields": SEARCH_FIELDS,
        "page": page,
        "limit": PAGE_LIMIT,
        "sort": "Award Amount",
        "order": "desc",
    }


PAGE_CAP = 100  # Self-imposed deep-paging guardrail (10K records per vendor max).


def _vendor_slug(canonical_name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", canonical_name.lower()).strip("_")
    return s or "unknown"


def fetch_vendor(
    canonical_name: str,
    keyword: str,
    *,
    raw_dir: Path,
    sleep_seconds: float = REQ_INTERVAL_SECONDS,
) -> tuple[list[dict], VendorFetchStats]:
    """Paginate one keyword query until hasNext=false. Persist each page
    to disk under `raw_dir/vendor_<slug>_pageN.json` (slug from
    canonical_name) and return aggregate results + per-vendor stats.

    Returns the full results list and the per-vendor archive SHA256
    (over the concatenated page bodies in fetch order) for the manifest.
    """
    slug = _vendor_slug(canonical_name)
    stats = VendorFetchStats(canonical_name=canonical_name, keyword=keyword)
    all_results: list[dict] = []
    archive_hash = hashlib.sha256()
    page = 1
    while True:
        body = _build_search_body(keyword, page=page)
        if page > 1:
            time.sleep(sleep_seconds)
        LOG.info(
            "vendor=%s keyword=%s page=%d fetching",
            canonical_name, keyword, page,
        )
        payload, http_status = _fetch_post(SEARCH_ENDPOINT, body)
        stats.last_http_status = http_status
        archive_hash.update(payload)
        # Persist each page verbatim per §7.2 (preserve raw before parse).
        page_path = raw_dir / f"vendor_{slug}_page{page}.json"
        page_path.write_bytes(payload)
        try:
            obj = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"USAspending returned non-JSON for canonical={canonical_name!r} "
                f"keyword={keyword!r} page={page}: {e}"
            )
        results = obj.get("results", []) or []
        all_results.extend(results)
        stats.pages_fetched += 1
        stats.raw_results_total += len(results)
        page_meta = obj.get("page_metadata") or {}
        if not page_meta.get("hasNext"):
            break
        page += 1
        # Self-imposed guardrail. Surface explicitly if hit so coverage is
        # honest: a vendor at the cap is a structural noise-prone keyword
        # whose disambig is Phase 5 work, not a silent truncation.
        if page > PAGE_CAP:
            LOG.warning(
                "vendor=%s keyword=%s hit PAGE_CAP=%d (10K record ceiling); "
                "remaining matches deferred to Phase 5 disambig",
                canonical_name, keyword, PAGE_CAP,
            )
            stats.page_cap_hit = True
            break
    stats.raw_filename = f"vendor_{slug}_pageN.json"
    stats.raw_sha256 = archive_hash.hexdigest()
    stats.raw_byte_count = sum(
        (raw_dir / f"vendor_{slug}_page{p}.json").stat().st_size
        for p in range(1, stats.pages_fetched + 1)
    )
    stats.has_zero_results = stats.raw_results_total == 0
    LOG.info(
        "vendor=%s keyword=%s pages=%d raw_results=%d sha256=%s",
        canonical_name, keyword, stats.pages_fetched, stats.raw_results_total,
        stats.raw_sha256,
    )
    return all_results, stats


# ─── Per-award accumulation (multi-vendor de-dup) ─────────────────────────


@dataclass
class AwardRow:
    """One USAspending award, accumulated across vendor-keyword overlap."""

    generated_internal_id: str
    award_id: Optional[str]                # PIID
    recipient_name: Optional[str]
    awarding_agency: Optional[str]
    awarding_sub_agency: Optional[str]
    award_amount: Optional[float]
    description: Optional[str]
    last_modified_date: Optional[str]
    naics_code: Optional[str]
    psc_code: Optional[str]
    recipient_id: Optional[str]
    place_of_performance_state_code: Optional[str]
    period_of_performance_start: Optional[str]
    period_of_performance_end: Optional[str]
    awarding_agency_id: Optional[int]
    agency_slug: Optional[str]
    keyword_matches: list[str] = field(default_factory=list)

    @classmethod
    def from_search_result(cls, r: dict, canonical_name: str) -> "AwardRow":
        return cls(
            generated_internal_id=str(r.get("generated_internal_id") or ""),
            award_id=r.get("Award ID"),
            recipient_name=r.get("Recipient Name"),
            awarding_agency=r.get("Awarding Agency"),
            awarding_sub_agency=r.get("Awarding Sub Agency"),
            award_amount=(
                float(r["Award Amount"])
                if r.get("Award Amount") is not None
                else None
            ),
            description=r.get("Description"),
            last_modified_date=r.get("Last Modified Date"),
            naics_code=r.get("NAICS Code"),
            psc_code=r.get("PSC Code"),
            recipient_id=r.get("recipient_id"),
            place_of_performance_state_code=r.get("Place of Performance State Code"),
            period_of_performance_start=r.get("Period of Performance Start Date"),
            period_of_performance_end=r.get("Period of Performance Current End Date"),
            awarding_agency_id=r.get("awarding_agency_id"),
            agency_slug=r.get("agency_slug"),
            keyword_matches=[canonical_name],
        )


def merge_awards(
    by_id: dict[str, AwardRow],
    results: list[dict],
    canonical_name: str,
) -> tuple[int, int]:
    """Fold a vendor's results into the keyed dict. Returns (new, dup).

    `canonical_name` (not `keyword_used`) is what gets recorded in
    `keyword_match[]` — Phase 5 disambig wants the vendor universe label,
    not the noise-prone API keyword phrasing. The keyword phrasing is
    captured at the run level in extraction_runs.notes.
    """
    new = 0
    dup = 0
    for r in results:
        gid = r.get("generated_internal_id")
        if not gid:
            LOG.warning("skipping result without generated_internal_id: %r", r)
            continue
        if gid in by_id:
            existing = by_id[gid]
            if canonical_name not in existing.keyword_matches:
                existing.keyword_matches.append(canonical_name)
            dup += 1
        else:
            by_id[gid] = AwardRow.from_search_result(r, canonical_name)
            new += 1
    return new, dup


# ─── DB writes ─────────────────────────────────────────────────────────────


def _upsert_source(
    conn: sqlite3.Connection,
    *,
    fetched_at: str,
    archive_sha256: str,
    archive_byte_count: int,
    vendor_count: int,
    raw_subdir: str,
) -> int:
    notes = json.dumps(
        {
            "registry": REGISTRY_TAG,
            "license": LICENSE_NOTE,
            "license_attribution": LICENSE_ATTRIBUTION,
            "byte_count": archive_byte_count,
            "content_sha256": archive_sha256,
            "confidence_band": CONFIDENCE_BAND,
            "vendor_count": vendor_count,
            "raw_subdir": raw_subdir,
            "time_period_start": TIME_PERIOD_START,
            "time_period_end": TIME_PERIOD_END,
            "award_type_codes": list(AWARD_TYPE_CODES),
            "freshness_note": (
                "Treasury bulk; refreshed daily upstream. content_sha256 is "
                "the archive sha256 (concatenated per-vendor page bodies in "
                "deterministic order) — captures the exact raw set staged "
                "this run."
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


def _maybe_null(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _compose_agency(award: AwardRow) -> str:
    """`Awarding Agency / Awarding Sub Agency` (composed). agency_name is
    NOT NULL on procurement_records — fall back to a placeholder if both
    are missing (which Step-1 evidence shows never happens, but be safe).
    """
    parts = [
        _maybe_null(award.awarding_agency),
        _maybe_null(award.awarding_sub_agency),
    ]
    composed = " / ".join(p for p in parts if p)
    return composed or "(unknown)"


def _compose_geographic_scope(award: AwardRow) -> str:
    """Q2 (b): Place of Performance State Code → `US-<2-letter>`; fallback
    `US-FED` only when state_code is null."""
    sc = _maybe_null(award.place_of_performance_state_code)
    if sc:
        return f"US-{sc.upper()}"
    return "US-FED"


def _compose_product_family(award: AwardRow) -> Optional[str]:
    """`PSC Code / NAICS Code` composed; None when both missing."""
    psc = _maybe_null(award.psc_code)
    naics = _maybe_null(award.naics_code)
    if psc and naics:
        return f"PSC:{psc} / NAICS:{naics}"
    if psc:
        return f"PSC:{psc}"
    if naics:
        return f"NAICS:{naics}"
    return None


def _compose_excerpt(award: AwardRow) -> Optional[str]:
    """≤200 chars of Description for validator audit."""
    desc = _maybe_null(award.description)
    if not desc:
        return None
    return desc[:200]


def _award_to_notes_json(award: AwardRow, source_id: int) -> str:
    notes_obj: dict[str, object] = {
        "award_id": award.award_id,
        "piid": award.award_id,  # USAspending Award ID == PIID for contracts
        "generated_unique_award_id": award.generated_internal_id,
        "recipient_uei": None,    # search-API-only; see module docstring
        "recipient_id": award.recipient_id,
        "psc_code": award.psc_code,
        "naics_code": award.naics_code,
        "place_of_performance": {
            "state_code": award.place_of_performance_state_code,
            "country_code": "USA",  # search response does not return per-row country; awards in scope are federal-domestic
        },
        "keyword_match": sorted(award.keyword_matches),
        "awarding_agency_id": award.awarding_agency_id,
        "agency_slug": award.agency_slug,
        "awarding_sub_agency": award.awarding_sub_agency,
        "last_modified_date": award.last_modified_date,
        "period_of_performance": {
            "start_date": award.period_of_performance_start,
            "end_date": award.period_of_performance_end,
        },
        "source_id": source_id,
        "registry": REGISTRY_TAG,
    }
    return json.dumps(notes_obj, sort_keys=True)


def _normalize_contract_date(raw: Optional[str]) -> Optional[str]:
    """USAspending `Last Modified Date` is `YYYY-MM-DD HH:MM:SS`; coerce to
    `YYYY-MM-DD` for the DATE column."""
    s = _maybe_null(raw)
    if not s:
        return None
    # Take the date-prefix; SQLite DATE is text-flexible but we keep clean.
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    return s


@dataclass
class StagingStats:
    inserted: int = 0
    by_agency: dict[str, int] = field(default_factory=dict)
    by_vendor: dict[str, int] = field(default_factory=dict)  # raw recipient_name
    by_state: dict[str, int] = field(default_factory=dict)
    by_keyword: dict[str, int] = field(default_factory=dict)
    pii_hits_total: int = 0
    pii_hit_samples: list[tuple[str, str]] = field(default_factory=list)
    null_state_count: int = 0


def _stage_procurement_records(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    awards_by_id: dict[str, AwardRow],
) -> StagingStats:
    """Idempotent stage. DELETE WHERE source_url LIKE 'https://www.usaspending.gov/award/%'
    (procurement_records has no source_id column by design — see module docstring)
    then bulk-insert.
    """
    conn.execute(
        "DELETE FROM procurement_records WHERE source_url LIKE ?",
        (WEB_AWARD_BASE + "%",),
    )

    stats = StagingStats()
    batch: list[tuple] = []
    BATCH_SIZE = 1000

    sql = (
        "INSERT INTO procurement_records ("
        "agency_name, agency_geographic_scope, vendor_canonical_name, "
        "product_family, contract_amount_usd, contract_date, "
        "source_url, source_type, source_excerpt, confidence, "
        "linked_identifier_id, notes"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    def _flush() -> None:
        if not batch:
            return
        conn.executemany(sql, batch)
        stats.inserted += len(batch)
        batch.clear()

    for gid, award in awards_by_id.items():
        agency = _compose_agency(award)
        scope = _compose_geographic_scope(award)
        product_family = _compose_product_family(award)
        excerpt = _compose_excerpt(award)
        contract_date = _normalize_contract_date(award.last_modified_date)
        notes = _award_to_notes_json(award, source_id)
        per_row_url = f"{WEB_AWARD_BASE}{gid}"

        # Audit-only PII sweep across plausible text surfaces.
        for surface, val in (
            ("description", award.description),
            ("recipient_name", award.recipient_name),
            ("agency", agency),
        ):
            n, samples = count_pii_hits(val)
            if n:
                stats.pii_hits_total += n
                for s in samples[:3]:
                    stats.pii_hit_samples.append((surface, s))

        batch.append(
            (
                agency,
                scope,
                _maybe_null(award.recipient_name) or "(unknown)",
                product_family,
                award.award_amount,
                contract_date,
                per_row_url,
                SOURCE_TYPE,
                excerpt,
                CONFIDENCE,
                None,            # linked_identifier_id (§11 #8)
                notes,
            )
        )

        # Aggregate stats — verbatim raw fields, no canonicalization.
        agency_short = _maybe_null(award.awarding_agency) or agency
        stats.by_agency[agency_short] = stats.by_agency.get(agency_short, 0) + 1
        recipient = _maybe_null(award.recipient_name) or "(unknown)"
        stats.by_vendor[recipient] = stats.by_vendor.get(recipient, 0) + 1
        sc = _maybe_null(award.place_of_performance_state_code)
        if sc:
            stats.by_state[sc] = stats.by_state.get(sc, 0) + 1
        else:
            stats.null_state_count += 1
        for kw in award.keyword_matches:
            stats.by_keyword[kw] = stats.by_keyword.get(kw, 0) + 1

        if len(batch) >= BATCH_SIZE:
            _flush()
    _flush()
    return stats


# ─── Public entry point ────────────────────────────────────────────────────


@dataclass
class IngestResult:
    raw_dir: Path
    fetched_at_utc: str
    archive_sha256: str
    archive_byte_count: int
    sources_id: int
    extraction_run_id: int
    rows_staged: int
    raw_results_total: int
    unique_awards: int
    vendors_with_zero_results: list[str]
    by_agency: dict[str, int]
    by_vendor: dict[str, int]
    by_state: dict[str, int]
    by_keyword: dict[str, int]
    null_state_count: int
    pii_hits_total: int
    pii_hit_samples: list[tuple[str, str]]


def ingest(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    agent_id: str,
    raw_subdir: Optional[str] = None,
    sleep_seconds: float = REQ_INTERVAL_SECONDS,
    vendor_keywords: Optional[list[tuple[str, str]]] = None,
) -> IngestResult:
    """Fetch + parse + stage USAspending awards across the §2.1 vendor list.

    `raw_subdir`: if given, reuse an existing raw/sam_gov/<ts>/ directory
    (re-reads each `vendor_<slug>_page*.json` rather than refetching).
    Otherwise fetch fresh into raw/sam_gov/<UTC-timestamp>/.
    """
    fetched_at_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if raw_subdir:
        raw_dir = raw_root / raw_subdir
        if not raw_dir.exists():
            raise FileNotFoundError(f"raw_subdir {raw_dir} does not exist")
    else:
        raw_dir = raw_root / fetched_at_utc
        raw_dir.mkdir(parents=True, exist_ok=True)
    LOG.info("USAspending ingest -> raw_dir=%s", raw_dir)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        if vendor_keywords is None:
            vendor_keywords = load_vendor_keywords(conn)
        if not vendor_keywords:
            raise RuntimeError(
                "no vendor keywords found in `manufacturers` table — "
                "expected MAC-2 / Phase 1 seed (34 entries)."
            )
        LOG.info("vendor sweep across %d (canonical, keyword) pairs", len(vendor_keywords))

        # ── 1. Per-vendor fetch + dedup ────────────────────────────────
        awards_by_id: dict[str, AwardRow] = {}
        per_vendor_stats: list[VendorFetchStats] = []
        raw_results_total = 0
        if raw_subdir:
            # Reuse mode: read existing per-vendor pages from disk.
            for canonical, keyword in vendor_keywords:
                slug = _vendor_slug(canonical)
                page = 1
                pages_fetched = 0
                vstats = VendorFetchStats(canonical_name=canonical, keyword=keyword)
                vhash = hashlib.sha256()
                while True:
                    page_path = raw_dir / f"vendor_{slug}_page{page}.json"
                    if not page_path.exists():
                        break
                    payload = page_path.read_bytes()
                    vhash.update(payload)
                    obj = json.loads(payload.decode("utf-8"))
                    results = obj.get("results", []) or []
                    raw_results_total += len(results)
                    merge_awards(awards_by_id, results, canonical)
                    pages_fetched += 1
                    vstats.raw_results_total += len(results)
                    page_meta = obj.get("page_metadata") or {}
                    if not page_meta.get("hasNext"):
                        page += 1
                        break
                    page += 1
                vstats.pages_fetched = pages_fetched
                vstats.raw_filename = f"vendor_{slug}_pageN.json"
                vstats.raw_sha256 = vhash.hexdigest()
                vstats.raw_byte_count = sum(
                    (raw_dir / f"vendor_{slug}_page{p}.json").stat().st_size
                    for p in range(1, pages_fetched + 1)
                )
                vstats.has_zero_results = vstats.raw_results_total == 0
                per_vendor_stats.append(vstats)
                LOG.info(
                    "[reuse] vendor=%s keyword=%s pages=%d raw_results=%d",
                    canonical, keyword, vstats.pages_fetched, vstats.raw_results_total,
                )
        else:
            # Fresh mode: actually paginate across the API.
            for i, (canonical, keyword) in enumerate(vendor_keywords):
                if i > 0:
                    time.sleep(sleep_seconds)
                results, vstats = fetch_vendor(
                    canonical, keyword,
                    raw_dir=raw_dir, sleep_seconds=sleep_seconds,
                )
                raw_results_total += len(results)
                merge_awards(awards_by_id, results, canonical)
                per_vendor_stats.append(vstats)

        # ── 2. Manifest ─────────────────────────────────────────────────
        manifest_path = raw_dir / "manifest_step2.json"
        manifest = {
            "fetched_at_utc": fetched_at_utc if not raw_subdir else raw_subdir,
            "step": "MAC-8 Step 2 — bulk vendor sweep ingest",
            "license_note": LICENSE_NOTE,
            "license_attribution": LICENSE_ATTRIBUTION,
            "endpoint": SEARCH_ENDPOINT,
            "time_period": {
                "start_date": TIME_PERIOD_START,
                "end_date": TIME_PERIOD_END,
            },
            "award_type_codes": list(AWARD_TYPE_CODES),
            "page_limit": PAGE_LIMIT,
            "vendor_count": len(vendor_keywords),
            "raw_results_total": raw_results_total,
            "unique_awards": len(awards_by_id),
            "vendors": [
                {
                    "canonical_name": s.canonical_name,
                    "keyword_used": s.keyword,
                    "pages_fetched": s.pages_fetched,
                    "raw_results_total": s.raw_results_total,
                    "raw_archive_filename_pattern": s.raw_filename,
                    "raw_archive_sha256": s.raw_sha256,
                    "raw_archive_byte_count": s.raw_byte_count,
                    "has_zero_results": s.has_zero_results,
                    "page_cap_hit": s.page_cap_hit,
                }
                for s in per_vendor_stats
            ],
            "keyword_overrides_applied": KEYWORD_OVERRIDES,
        }
        # Archive sha256 = sha256 of concatenated per-vendor sha256s in
        # canonical (alpha-by-canonical-name) order. Stable across re-fetches.
        master_hash = hashlib.sha256()
        for s in sorted(per_vendor_stats, key=lambda s: s.canonical_name):
            master_hash.update(s.raw_sha256.encode("ascii"))
        archive_sha256 = master_hash.hexdigest()
        archive_byte_count = sum(s.raw_byte_count for s in per_vendor_stats)
        manifest["archive_sha256_over_vendor_sha256s"] = archive_sha256
        manifest["archive_byte_count"] = archive_byte_count
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

        # ── 3. sources + extraction_runs + stage ───────────────────────
        sid = _upsert_source(
            conn,
            fetched_at=_utc_now(),
            archive_sha256=archive_sha256,
            archive_byte_count=archive_byte_count,
            vendor_count=len(vendor_keywords),
            raw_subdir=fetched_at_utc if not raw_subdir else raw_subdir,
        )
        run_id = _start_run(conn, agent_id=agent_id, source_id=sid)
        try:
            stats = _stage_procurement_records(
                conn,
                source_id=sid,
                awards_by_id=awards_by_id,
            )
            zero_vendors = sorted(
                s.canonical_name for s in per_vendor_stats if s.has_zero_results
            )
            page_cap_vendors = sorted(
                s.canonical_name for s in per_vendor_stats if s.page_cap_hit
            )
            run_notes_obj: dict[str, object] = {
                "registry": REGISTRY_TAG,
                "raw_subdir": fetched_at_utc if not raw_subdir else raw_subdir,
                "archive_sha256_over_vendor_sha256s": archive_sha256,
                "archive_byte_count": archive_byte_count,
                "vendor_count": len(vendor_keywords),
                "raw_results_total": raw_results_total,
                "unique_awards": len(awards_by_id),
                "vendors_with_zero_results": zero_vendors,
                "vendors_at_page_cap": page_cap_vendors,
                "keyword_overrides_applied": KEYWORD_OVERRIDES,
                "vendor_keyword_phrasing_note": (
                    "Single-token canonical names whose keyword match is "
                    "noise-prone (Harris, Jacobs, KeyW, Reveal) use a more "
                    "specific alias as the API search keyword. The canonical "
                    "name is what gets recorded in notes.keyword_match[]; "
                    "the override only affects the search phrasing within "
                    "the vendor's query, not vendor inclusion. Q6 'no "
                    "trimming' contract preserved — full vendor universe "
                    "queried."
                ),
                "case_fold": (
                    "API-side keyword matching is case-insensitive over "
                    "Recipient Name + Description fields. Documented per "
                    "MAC-7 forward-precision lesson."
                ),
                "staging_as_raw_choice_q1": (
                    "Recipient Name staged verbatim into "
                    "vendor_canonical_name per Q1 Option A. No "
                    "canonicalization at staging (§4.3)."
                ),
                "geographic_scope_choice_q2": (
                    "agency_geographic_scope = `US-<state_code>` from "
                    "place_of_performance.state_code; fallback `US-FED` "
                    "when state_code null. Q2 Option (b)."
                ),
                "source_row_key_choice_q3": (
                    "generated_internal_id used as in-process dedup key "
                    "for multi-vendor keyword overlap. procurement_records "
                    "has no source_row_key column by §4.5 design; "
                    "structural backstop is "
                    "DELETE WHERE source_url LIKE 'https://www.usaspending.gov/award/%'."
                ),
                "award_type_codes_q4": list(AWARD_TYPE_CODES),
                "time_period_q5": {
                    "start_date": TIME_PERIOD_START,
                    "end_date": TIME_PERIOD_END,
                },
                "vendor_list_q6": (
                    "Read from manufacturers.canonical_name at run time. "
                    "Currently 34 entries (post-CP3 with Cradlepoint + "
                    "Sierra Wireless). Q6 ratification: no trimming."
                ),
                "confidence_band": CONFIDENCE_BAND,
                "confidence_value": CONFIDENCE,
                "confidence_band_correction": (
                    "CEO correction at MAC-8 Step 1: §8.2 procurement band "
                    "is 70–85 (top), NOT 90 (which is `official` band). "
                    "Confidence=85 reflects USAspending's gold-standard "
                    "Treasury provenance within the procurement source-type "
                    "ceiling. The §8.2 cap is structural (proves *purchase*, "
                    "not *deployment*) and binds regardless of upstream "
                    "data quality."
                ),
                "phase5_reconsider_pii": PHASE5_RECONSIDER_PII,
                "reseller_pattern_note": RESELLER_PATTERN_NOTE,
                "pii_hits_total": stats.pii_hits_total,
                "pii_hit_samples": stats.pii_hit_samples[:10],
                "null_place_of_performance_state_count": stats.null_state_count,
                "rate_limit_posture": (
                    "1 req/s + single-shot transient retry. NOT a "
                    "Checkpoint-3a-class question (public bulk endpoint, "
                    "no observed throttling, structurally distinct from "
                    "WiGLE)."
                ),
                "license": LICENSE_NOTE,
                "license_attribution": LICENSE_ATTRIBUTION,
            }
            run_notes = json.dumps(run_notes_obj, sort_keys=True)
            _finish_run(
                conn,
                run_id,
                records_in=raw_results_total,
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
        fetched_at_utc=fetched_at_utc if not raw_subdir else raw_subdir,
        archive_sha256=archive_sha256,
        archive_byte_count=archive_byte_count,
        sources_id=sid,
        extraction_run_id=run_id,
        rows_staged=stats.inserted,
        raw_results_total=raw_results_total,
        unique_awards=len(awards_by_id),
        vendors_with_zero_results=sorted(
            s.canonical_name for s in per_vendor_stats if s.has_zero_results
        ),
        by_agency=stats.by_agency,
        by_vendor=stats.by_vendor,
        by_state=stats.by_state,
        by_keyword=stats.by_keyword,
        null_state_count=stats.null_state_count,
        pii_hits_total=stats.pii_hits_total,
        pii_hit_samples=stats.pii_hit_samples,
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
        help=(
            "Reuse an existing raw/sam_gov/<subdir>/ rather than re-fetching "
            "(idempotency mode)."
        ),
    )
    p.add_argument(
        "--agent-id",
        type=str,
        required=True,
        help="Paperclip agent id ingesting this run (extraction_runs.agent_id).",
    )
    p.add_argument(
        "--sleep-seconds",
        type=float,
        default=REQ_INTERVAL_SECONDS,
        help=(
            "Per-request sleep (default 1.0s — CEO-ratified at MAC-8 Step 1)."
        ),
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
        sleep_seconds=args.sleep_seconds,
    )
    print(f"raw_dir: {result.raw_dir}")
    print(f"fetched_at_utc: {result.fetched_at_utc}")
    print(f"archive_sha256: {result.archive_sha256}")
    print(f"archive_byte_count: {result.archive_byte_count}")
    print(f"sources_id: {result.sources_id}")
    print(f"extraction_run_id: {result.extraction_run_id}")
    print(f"raw_results_total: {result.raw_results_total}")
    print(f"unique_awards: {result.unique_awards}")
    print(f"rows_staged: {result.rows_staged}")
    print(
        f"vendors_with_zero_results ({len(result.vendors_with_zero_results)}): "
        f"{result.vendors_with_zero_results}"
    )
    print(f"PII hits (audit-only): {result.pii_hits_total}")
    print(f"top 10 agencies:")
    for a, n in sorted(result.by_agency.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {a}: {n}")
    print(f"top 15 vendors (raw recipient_name):")
    for v, n in sorted(result.by_vendor.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {v}: {n}")
    print(f"top 10 states:")
    for s, n in sorted(result.by_state.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {s}: {n}")
    print(f"by keyword:")
    for k, n in sorted(result.by_keyword.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
