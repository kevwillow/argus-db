"""WiGLE BSSID-radius search module + prioritized anchor list builder.

Phase 3 — Tier 2, source 3/4. Argus's third Tier-2 source. Pulls WiGLE
network search results (BSSID + SSID + lat/lon) keyed off Flock-attributed
deployment anchors per board T1–T5 priority, into `raw_observations`
staging at Phase 3 — but ONLY when the DRY_RUN gate is OFF AND a CEO-
authorized live-fire window is active.

This Step-2 build delivers the module, the prioritized-anchor-list
artifact in `wigle_anchor_priority`, and DRY_RUN-only smoke tests. Live
queries do NOT fire in Step 2 — they gate on grant landing or 14d
timeout (board pitch sent 2026-05-04 from personal inbox; 14d window
ends 2026-05-18 per [MAC-1](/MAC/issues/MAC-1) board comment).

Source
──────
Endpoint:     GET https://api.wigle.net/api/v2/network/search
              (paginated by `searchAfter` cursor; default page size 100,
              site-auth max 100/page; bbox params latrange1/latrange2/
              longrange1/longrange2 all four required for radius queries)
Auth:         HTTP Basic, creds from `.env/.env`:
                  WIGLE_API_NAME = API name (the visible identifier)
                  WIGLE_API_TOKEN = API token (the secret)
License:      WiGLE EULA — https://wigle.net/eula.html
              "Interaction with the system is governed by our EULA."
              (verbatim from swagger.json `info.license`)
Public docs:  swagger v3.1 cached at `raw/wigle_docs/20260504T181515Z/`
              sha256 a66f00f9b81b63f5682f8862b9d1baec419e467c39f6c2597c7cf73d4c0388f4
              107,431 bytes, retrieved 2026-05-04T18:15:15Z

source_type:  `crowdsourced` (§4.1 enum, §8.2 50–75 band)
tier:         2 (per Bible §5)
confidence:   50 (low end of §8.2 `crowdsourced` band per CEO ratification
              at MAC-9 Step 1: "crowdsourced source class; SSID-as-attribution
              chain is weak (SSIDs are user-set); WiGLE's own caveat about
              variable crowdsourced data quality. 70 (high end) would be
              elevated and is rejected.")

────────────────────────────────────────────────────────────────────────────
Prioritized-anchor-list build (this Step 2 deliverable)
────────────────────────────────────────────────────────────────────────────
Reads Flock-attributed Atlas (source 5) + DeFlock (source 6) rows from
`deployment_observations`, derives state via the ratified Q1 method, and
writes to `wigle_anchor_priority` per the tier scheme:

  T1 = MD
  T2 = DC, NJ, PA, NY, VA
  T3 = CT, MA, RI, ME, NH, VT, DE, WV (8 states; Census northeast +
       remaining mid-Atlantic; CEO-ratified at Step 1)
  T4 = the other 38 US states by Flock-anchor density (CONUS + AK + HI)
       + US territories at T4-territory sub-rank (PR, USVI, GU, AS, MP)
  T5 = international (ISO 3166 alpha-2 country codes; flag Phase-5
       dependency on §12 `geographic_scope` open question)

`derivation_method`:
  - `atlas_state_column`     — Atlas: state from existing `state` column
                                (NB: Atlas Flock-attributed rows have
                                NULL lat/lon so are NOT WiGLE-queryable
                                in Step 2; staged here for tier-density
                                cross-source corroboration only per Q3)
  - `deflock_reverse_geocode` — DeFlock: state from `reverse_geocoder`
                                admin1 lookup (Q1 (b), pinned 1.5.1
                                in `requirements-wigle.txt`)

Intra-tier rank: 1-based within `(priority_tier, state_or_country)` by
DeFlock-count load-bearing density. Atlas state-count cited in
`tier_rationale` for cross-source corroboration but does NOT swing tier
assignment (Q3 ratified — Atlas captures vendor-mention coverage by
reporter density, not deployment density).

Atlas Flock-attributed = `vendor_raw LIKE '%Flock%'` (case-insensitive)
on source_id=5; reproduces Step 1 §2 count of 2,745.

DeFlock Flock-attributed = strict-set match against Step 1 §2-reproducing
canonical-name set (see `FLOCK_VENDOR_RAW_VALUES`). Reproduces Step 1
§2 count of 77,953 exactly. The broader `\\bFlock\\b` regex set is 51
rows wider (78,004); broadening is a separate CEO ratification not in
Step 2 scope.

────────────────────────────────────────────────────────────────────────────
Step 2 deliverable scope (CEO ratification of MAC-9 Step 1, comment ea4db5e2)
────────────────────────────────────────────────────────────────────────────
1. DDL `db/migrations/0004_wigle_anchor_priority.sql` (already applied;
   schema_version 3 -> 4).
2. This module per skeleton in worker Step 1 §5.
3. Prioritized-list build via `build_prioritized_list()` (this file):
   `reverse_geocoder` for DeFlock state derivation; Atlas `state` column
   for Atlas rows; T1–T5 ratified scheme (T3 = 8 states); intra-tier
   rank by anchor density; writes to `wigle_anchor_priority`.
4. Smoke tests at `tests/test_wigle_module.py`.
5. `requirements-wigle.txt` with pinned `reverse_geocoder==1.5.1`.

NO live WiGLE queries fire in Step 2. `DRY_RUN_DEFAULT = True`.
B-tier hooks present (sample-size config) but no execution.

────────────────────────────────────────────────────────────────────────────
Documented HTTP response codes (verbatim from swagger.json §responses)
────────────────────────────────────────────────────────────────────────────
| Code | swagger description                                           |
|-----:|---------------------------------------------------------------|
|  200 | Request succeeded                                             |
|  400 | Request body error                                            |
|  402 | Insufficient balance for commercial query                     |
|  410 | Query Failed                                                  |
|  429 | too many queries today.                                       |

Q2 ratified — header parser:
  - HTTP 429 fail-stop verbatim per swagger (sole quota-exhaustion signal).
  - Defensive Retry-After parse per RFC 7231 §7.1.3 (standard HTTP, not
    WiGLE-specific fabrication; logged but does NOT trigger retry —
    dispatch clause 3 binds: NO retries on 429 / quota-exhaustion).
  - `# TODO: extend on first live observation` marker on the parser:
    Step-2 live-fire (separately gated) will log ALL response headers
    from the FIRST live response; CEO ratifies any newly-observed
    quota-related headers before parser extension.

────────────────────────────────────────────────────────────────────────────
PII redaction (SAR-5-by-analogy, applied unconditionally)
────────────────────────────────────────────────────────────────────────────
SAR-5 (commit 598460e at 12:47Z 2026-05-04, ratified by board comment
7e827dca at 18:05Z "stands as written, no amendment") rule (5)
"default-to-redact PII like MAC-5" binds verbatim to WiGLE SSID staging.
WiGLE results' `ssid` field can carry PII shapes (home network names,
"iPhone of <Name>", etc.). The `# SAR-5` marker on the SSID-staging
path applies pattern-match redaction at staging using the same rank-
token regex from MAC-5/MAC-6/MAC-7 + name-shape regex.

This module includes the redaction primitives but they are EXERCISED only
when DRY_RUN is OFF AND results actually flow into `raw_observations`.
In Step 2 (DRY_RUN ON) the primitives are validated against mock
fixtures only.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import logging
import math
import os
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from base64 import b64encode
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable, Optional


LOG = logging.getLogger("argus.ingest.wigle")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "wigle"
DEFAULT_ENV_PATH = REPO_ROOT / ".env" / ".env"
DEFAULT_DOCS_SNAPSHOT = (
    REPO_ROOT / "raw" / "wigle_docs" / "20260504T181515Z" / "swagger.json"
)
DEFAULT_DOCS_SHA256 = (
    "a66f00f9b81b63f5682f8862b9d1baec419e467c39f6c2597c7cf73d4c0388f4"
)
DEFAULT_DOCS_RETRIEVED_AT = "2026-05-04T18:15:15Z"

API_BASE = "https://api.wigle.net"
SEARCH_ENDPOINT = f"{API_BASE}/api/v2/network/search"

SOURCE_NAME = "WiGLE.net wireless network database (api.wigle.net /api/v2/network/search)"
SOURCE_URL = SEARCH_ENDPOINT
SOURCE_TYPE = "crowdsourced"   # §4.1 enum, §8.2 50–75 band
TIER = 2                       # §5 — Tier 2 / Phase 3
CONFIDENCE = 50                # CEO ratified — low end of band per Step 1 reasoning
CONFIDENCE_BAND = "50-75"

LICENSE_NOTE = (
    "License: Interaction with the system is governed by our EULA — "
    "https://wigle.net/eula.html (verbatim from swagger.json info.license; "
    f"public-docs snapshot retrieved {DEFAULT_DOCS_RETRIEVED_AT}; "
    f"sha256 {DEFAULT_DOCS_SHA256})"
)
LICENSE_ATTRIBUTION = (
    "WiGLE.net (Wireless Geographic Logging Engine), public crowdsourced "
    "wireless network observations. EULA: https://wigle.net/eula.html. "
    "Per FAQ: 'limits for new accounts start low and increase with good "
    "behavior'; commercial licenses not currently granted."
)

REGISTRY_TAG = "wigle"

# Pagination — site-auth API default 100 results/page, max 100. (commapi
# is 25/1000; we use site-auth — see swagger §securityDefinitions.basic.)
PAGE_LIMIT = 100

# Per-request inter-call sleep. Conservative; Step-2 DRY_RUN ignores;
# Step-2-plus live-fire CEO sets at fire-time per granted quota.
REQ_INTERVAL_SECONDS = 1.0

# DRY_RUN gate (default ON; flipped only on grant landing / B-tier
# authorization per dispatch clause 5).
DRY_RUN_DEFAULT = True

# B-tier sample-size hooks (per dispatch clause 4). NOT executed in
# Step 2; only design hooks. Ceiling = live granted quota number, NOT the
# 200k planning envelope. CEO sets `BTier.max_queries` at fire-time.
@dataclass
class BTierConfig:
    """B-tier fallback knobs. Step-2 mechanical-flip; no execution."""
    max_queries: Optional[int] = None     # CEO-set at fire-time
    sample_per_tier: dict[int, int] = field(default_factory=dict)   # tier -> N
    enabled: bool = False


# ─── Flock attribution — Step-1 reproducing strict pattern ────────────────


# Reproduces Step 1 §2 DeFlock-attributed count of 77,953 EXACTLY against
# the live `deployment_observations.vendor_raw` distribution. Set is the
# closed observed list of Flock-Safety-attributable canonical strings +
# Levenshtein-1 typos + the multi-vendor combo string. The broader
# `\\bFlock\\b` regex returns 78,004 (51 rows wider, including 'Flock'
# alone, 'Flock Surveillance', 'flock', "Flock Safety's", 'FLock Safety',
# 'FLOCK SAFETY'); broadening is a separate CEO ratification not in Step 2
# scope. CEO can override later.
FLOCK_VENDOR_RAW_VALUES: tuple[str, ...] = (
    "Flock Safety",                       # 77,370 rows (canonical)
    "Flock Group Inc.",                   #    490 rows (corporate parent)
    "Flock Safety Inc",                   #     90 rows (variant)
    "Flock Safety;Motorola Solutions",    #      1 row (multi-vendor combo)
    "Flock Saftey",                       #      1 row (typo)
    "Flock Safetu",                       #      1 row (typo)
)


def _flock_clause_atlas() -> tuple[str, tuple]:
    """SQL fragment + params for Atlas Flock-attribution.

    Atlas vendor_raw is broader: includes 'Flock Safety', 'Flock Group',
    'Flock Group Inc', 'Flock Safety Inc.', etc. The Step-1 §2 count of
    2,745 reproduces with `LOWER(vendor_raw) LIKE '%flock%'` (case-
    insensitive substring; Atlas does not have the typo-tail problem
    DeFlock has). Verified at ratification-time against live DB.
    """
    return ("LOWER(vendor_raw) LIKE ?", ("%flock%",))


def _flock_clause_deflock() -> tuple[str, tuple]:
    """SQL fragment + params for DeFlock Flock-attribution (Step-1 reproducing)."""
    placeholders = ",".join("?" * len(FLOCK_VENDOR_RAW_VALUES))
    return (f"vendor_raw IN ({placeholders})", FLOCK_VENDOR_RAW_VALUES)


# ─── Tier scheme — board-locked + CEO Step-1 ratified ─────────────────────


T1_STATES: tuple[str, ...] = ("MD",)
T2_STATES: tuple[str, ...] = ("DC", "NJ", "PA", "NY", "VA")
T3_STATES: tuple[str, ...] = ("CT", "MA", "RI", "ME", "NH", "VT", "DE", "WV")

# US territory 2-letter codes for T4-territory sub-rank (Q4 ratified).
US_TERRITORY_CODES: tuple[str, ...] = ("PR", "USVI", "GU", "AS", "MP")

# All 50 US states (used to classify CONUS/AK/HI -> T4 fallback when not
# in T1/T2/T3 + the territory-fallback distinction). 'DC' is in T2.
US_50_STATES: frozenset[str] = frozenset(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN "
    "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA "
    "WA WV WI WY".split()
)

# `reverse_geocoder` admin1 -> 2-letter US postal code map (used to coerce
# the lib's 'Texas' / 'Maryland' admin1 string to 'TX' / 'MD'). Verified
# against live rg output at MAC-9 Step 2 build-time (DC point returns
# admin1='Washington, D.C.' verbatim — note comma + period).
US_ADMIN1_TO_POSTAL: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT",
    "Delaware": "DE", "Florida": "FL",
    "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY",
    "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
    # District of Columbia — verified live: rg returns admin1 with comma
    # and period for cc=US DC points. Both spellings mapped defensively.
    "Washington, D.C.": "DC",
    "District of Columbia": "DC",
}

# Reverse-geocoder `cc` for US-territory points returns the territory's
# own ISO 3166-1 alpha-2 code (PR / VI / GU / AS / MP), NOT cc='US' with
# an admin1 territory name. Verified live at MAC-9 Step 2 build:
#   PR (San Juan, 18.4655, -66.1057)   -> cc='PR', admin1='San Juan'
#   VI (Charlotte Amalie, 18.34, -64.93) -> cc='VI', admin1='Saint Thomas Island'
#   GU (Hagatna, 13.47, 144.75)        -> cc='GU', admin1='Hagatna'
# Per Q4 ratification (T4-territory sub-rank, NOT T5 international), these
# `cc` codes route to T4 with state_or_country = the canonical Argus
# territory code from `US_TERRITORY_CODES`.
RG_CC_TO_TERRITORY: dict[str, str] = {
    "PR": "PR",
    "VI": "USVI",      # ISO 3166 'VI' covers US Virgin Islands; Argus uses 'USVI' to disambiguate
    "GU": "GU",
    "AS": "AS",
    "MP": "MP",
}


def assign_tier(state_or_country: str, *, country_code: str = "US") -> int:
    """Map a state-or-country code to its T1–T5 tier per the ratified scheme.

    Inputs:
      `state_or_country` — US 2-letter state (e.g. 'MD'), US territory
                           code (PR/USVI/GU/AS/MP), or ISO 3166 alpha-2
                           country code (e.g. 'BE').
      `country_code`     — ISO 3166 alpha-2 ('US' for states/territories;
                           anything else routes to T5).
    """
    if country_code != "US":
        return 5
    if state_or_country in T1_STATES:
        return 1
    if state_or_country in T2_STATES:
        return 2
    if state_or_country in T3_STATES:
        return 3
    if state_or_country in US_50_STATES or state_or_country in US_TERRITORY_CODES:
        return 4
    # Unknown US admin1 (shouldn't happen if mapping is exhaustive); per
    # §11 #1 do NOT force into a US bucket — return 5 so the caller can
    # log + skip rather than fabricate a state.
    LOG.warning(
        "assign_tier: unknown US state_or_country=%r; routing to T5 for "
        "log-and-skip (Q1 §11 #1 stop-line)",
        state_or_country,
    )
    return 5


# ─── State derivation (Q1 ratified — reverse_geocoder PyPI) ───────────────


def _import_reverse_geocoder():
    """Lazy import so `requirements-wigle.txt` is only required at run time,
    not at module-import time (other modules + tests should be importable
    without the dep installed). Step-2 prioritized-list build always
    requires it; smoke tests gate on availability.
    """
    try:
        import reverse_geocoder  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "reverse_geocoder not installed; run "
            "`pip install -r requirements-wigle.txt` "
            "(pinned reverse_geocoder==1.5.1 per Q1 ratification)"
        ) from e
    return reverse_geocoder


@dataclass
class DerivedState:
    state_or_country: str          # 2-letter postal/territory or ISO country alpha-2
    derivation_method: str         # 'atlas_state_column' or 'deflock_reverse_geocode'
    derivation_notes: Optional[str]
    country_code: str              # 'US' or ISO 3166 alpha-2


def derive_state_atlas(atlas_state: Optional[str], atlas_country: Optional[str]) -> Optional[DerivedState]:
    """Atlas rows: read `state` column verbatim. `country` defaults 'US'.

    Returns None if `atlas_state` is NULL/blank — caller logs and skips.
    """
    if not atlas_state:
        return None
    state = atlas_state.strip().upper()
    country = (atlas_country or "US").strip().upper() or "US"
    # Q4 explicit: Atlas state='PS' (Palestinian Territories — Atlas data-
    # quality artifact, country='US' on source) "stays out-of-scope per §12;
    # flag in extraction_runs.notes for Phase-5 traceability, do not stage."
    # Generalize: any Atlas Flock-attributed row whose state column is not
    # a US-50 + DC + territory code is dropped at staging. We log + skip
    # rather than route to T5; T5 is for DeFlock lat/lon-derived
    # international, not Atlas state-column anomalies.
    if country == "US" and state not in US_50_STATES and state != "DC" \
            and state not in US_TERRITORY_CODES:
        LOG.warning(
            "atlas Flock row with country=US, state=%r is not a US-50/DC/"
            "territory code; out-of-scope per Q4 (do not stage)",
            state,
        )
        return None
    return DerivedState(
        state_or_country=state,
        derivation_method="atlas_state_column",
        derivation_notes=None,
        country_code=country if country in ("US",) or len(country) == 2 else "US",
    )


def derive_states_deflock_batch(
    points: list[tuple[int, float, float]],
) -> dict[int, Optional[DerivedState]]:
    """Batch reverse-geocode a list of `(deployment_id, lat, lon)` to
    `DerivedState` rows. Uses `reverse_geocoder.search` mode=1 (k-d-tree).

    Returns a `{deployment_id: DerivedState | None}` mapping. None entries
    are stop-and-log per §11 #1 (e.g., admin1 outside the expected US +
    international set; caller must skip + record in extraction_runs.notes).
    """
    if not points:
        return {}
    rg = _import_reverse_geocoder()
    coords = [(lat, lon) for (_id, lat, lon) in points]
    LOG.info("reverse_geocoder.search(mode=1) on %d points", len(coords))
    results = rg.search(coords, mode=1, verbose=False)
    out: dict[int, Optional[DerivedState]] = {}
    for (dep_id, _lat, _lon), r in zip(points, results):
        cc = (r.get("cc") or "").upper()
        admin1 = r.get("admin1") or ""
        city = r.get("name") or ""
        if cc == "US":
            postal = US_ADMIN1_TO_POSTAL.get(admin1)
            if not postal:
                # §11 #1 stop-line: admin1 outside the expected US 50+DC
                # set. Log + skip; do NOT force into a US bucket.
                LOG.warning(
                    "deployment_id=%d: rg returned cc=US, admin1=%r — "
                    "outside expected 50+DC set; logging and skipping "
                    "(§11 #1 stop-line)",
                    dep_id, admin1,
                )
                out[dep_id] = None
                continue
            out[dep_id] = DerivedState(
                state_or_country=postal,
                derivation_method="deflock_reverse_geocode",
                derivation_notes=f"rg: {city}, admin1={admin1}, cc=US",
                country_code="US",
            )
        elif cc in RG_CC_TO_TERRITORY:
            # Q4: US territory points -> T4-territory sub-rank.
            # reverse_geocoder returns the territory's own ISO 3166 cc
            # (PR / VI / GU / AS / MP), NOT cc=US. Route as US country
            # with the canonical Argus territory code so assign_tier
            # places them in T4.
            terr = RG_CC_TO_TERRITORY[cc]
            out[dep_id] = DerivedState(
                state_or_country=terr,
                derivation_method="deflock_reverse_geocode",
                derivation_notes=f"rg: {city}, admin1={admin1}, cc={cc} (US territory -> T4)",
                country_code="US",
            )
        elif cc and len(cc) == 2:
            out[dep_id] = DerivedState(
                state_or_country=cc,
                derivation_method="deflock_reverse_geocode",
                derivation_notes=f"rg: {city}, admin1={admin1}, cc={cc}",
                country_code=cc,
            )
        else:
            LOG.warning(
                "deployment_id=%d: rg returned no usable cc; skipping",
                dep_id,
            )
            out[dep_id] = None
    return out


# ─── Tier rationale + intra-tier rank assembly ────────────────────────────


@dataclass
class _AnchorRow:
    deployment_id: int
    source_id: int                 # 5 = Atlas, 6 = DeFlock
    state_or_country: str
    derivation_method: str
    derivation_notes: Optional[str]
    country_code: str


def assemble_priority_rows(
    atlas_rows: list[tuple[int, Optional[str], Optional[str]]],
    deflock_rows: list[tuple[int, float, float]],
) -> tuple[list[tuple], dict[str, object]]:
    """Build the full `wigle_anchor_priority` insert tuple list +
    a stats summary.

    Inputs:
      `atlas_rows`  — `(deployment_id, atlas_state, atlas_country)` for
                      Flock-attributed Atlas rows.
      `deflock_rows` — `(deployment_id, lat, lon)` for Flock-attributed
                       DeFlock rows.

    Returns:
      (insert_tuples, stats) where insert_tuples are
      (deployment_id, priority_tier, state_or_country, intra_tier_rank,
       tier_rationale, derivation_method, derivation_notes) ordered for
      a bulk INSERT into `wigle_anchor_priority`.
    """
    # 1. Per-row state derivation.
    derived: list[_AnchorRow] = []
    skipped: list[tuple[int, str]] = []   # (deployment_id, reason)

    for dep_id, atlas_state, atlas_country in atlas_rows:
        ds = derive_state_atlas(atlas_state, atlas_country)
        if ds is None:
            skipped.append((dep_id, f"atlas state column NULL/blank"))
            continue
        derived.append(
            _AnchorRow(
                deployment_id=dep_id,
                source_id=5,
                state_or_country=ds.state_or_country,
                derivation_method=ds.derivation_method,
                derivation_notes=ds.derivation_notes,
                country_code=ds.country_code,
            )
        )

    # Batch-derive DeFlock rows (k-d-tree is amortized over the whole batch).
    rg_map = derive_states_deflock_batch(deflock_rows)
    for dep_id, _lat, _lon in deflock_rows:
        ds = rg_map.get(dep_id)
        if ds is None:
            skipped.append((dep_id, "rg returned non-mappable admin1/cc"))
            continue
        derived.append(
            _AnchorRow(
                deployment_id=dep_id,
                source_id=6,
                state_or_country=ds.state_or_country,
                derivation_method=ds.derivation_method,
                derivation_notes=ds.derivation_notes,
                country_code=ds.country_code,
            )
        )

    # 2. Tier assignment.
    by_tier_state: dict[tuple[int, str], list[_AnchorRow]] = defaultdict(list)
    for r in derived:
        tier = assign_tier(r.state_or_country, country_code=r.country_code)
        by_tier_state[(tier, r.state_or_country)].append(r)

    # 3. Per-(tier, state) DeFlock-load-bearing density count for intra-tier rank.
    # `intra_tier_rank` is 1-based within (priority_tier, state_or_country)
    # but ALSO the per-state ranks are stable across the tier (cross-state
    # ordering by DeFlock-count). For the table model: keep ranks simple
    # (1..N within (tier, state)) since the index is on
    # `(priority_tier, intra_tier_rank)` for tier-iteration purposes.

    # Per-state Atlas + DeFlock counts (for tier_rationale).
    state_atlas_count: Counter[tuple[int, str]] = Counter()
    state_deflock_count: Counter[tuple[int, str]] = Counter()
    for r in derived:
        key = (assign_tier(r.state_or_country, country_code=r.country_code),
               r.state_or_country)
        if r.source_id == 5:
            state_atlas_count[key] += 1
        else:
            state_deflock_count[key] += 1

    # Per-tier state-rank by DeFlock-load-bearing density.
    by_tier: dict[int, list[str]] = defaultdict(list)
    for (tier, state), _rows in sorted(by_tier_state.items()):
        by_tier[tier].append(state)
    state_rank_in_tier: dict[tuple[int, str], int] = {}
    for tier, states in by_tier.items():
        ranked = sorted(
            states,
            key=lambda s: (-state_deflock_count[(tier, s)], s),
        )
        for i, s in enumerate(ranked, start=1):
            state_rank_in_tier[(tier, s)] = i

    # 4. Build insert tuples. intra_tier_rank = 1-based row index within
    # (tier, state); deterministic by deployment_id ascending so re-runs
    # are stable.
    insert_tuples: list[tuple] = []
    for (tier, state), rows in by_tier_state.items():
        atlas_n = state_atlas_count[(tier, state)]
        deflock_n = state_deflock_count[(tier, state)]
        s_rank = state_rank_in_tier[(tier, state)]
        rationale = (
            f"T{tier} {state}: DeFlock {deflock_n} (load-bearing) + Atlas "
            f"{atlas_n} (corroboration); state-rank #{s_rank} within T{tier}"
        )
        if tier == 4 and state in US_TERRITORY_CODES:
            rationale += "; T4-territory sub-rank (Q4)"
        for i, r in enumerate(sorted(rows, key=lambda r: r.deployment_id), start=1):
            insert_tuples.append((
                r.deployment_id,
                tier,
                r.state_or_country,
                i,
                rationale,
                r.derivation_method,
                r.derivation_notes,
            ))

    # 5. Stats summary for the deliverable + run notes.
    stats = {
        "total_anchors": len(insert_tuples),
        "skipped": len(skipped),
        "skipped_samples": skipped[:10],
        "atlas_count": sum(1 for t in insert_tuples if t[5] == "atlas_state_column"),
        "deflock_count": sum(1 for t in insert_tuples if t[5] == "deflock_reverse_geocode"),
        "by_tier": {
            t: sum(1 for it in insert_tuples if it[1] == t)
            for t in (1, 2, 3, 4, 5)
        },
        "by_tier_state": {
            f"T{t}/{s}": deflock_n
            for (t, s), deflock_n in sorted(
                state_deflock_count.items(), key=lambda kv: (kv[0][0], -kv[1])
            )
        },
        "atlas_by_tier_state": {
            f"T{t}/{s}": atlas_n
            for (t, s), atlas_n in sorted(
                state_atlas_count.items(), key=lambda kv: (kv[0][0], -kv[1])
            )
        },
    }
    return insert_tuples, stats


# ─── DB build entry ───────────────────────────────────────────────────────


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _upsert_source(
    conn: sqlite3.Connection,
    *,
    fetched_at: str,
    docs_snapshot_path: str,
    docs_sha256: str,
    docs_retrieved_at: str,
) -> int:
    """Upsert WiGLE row in `sources`. NB: this row is created at module
    install time even though no live API queries fire — it records the
    public-docs snapshot + license metadata. `last_fetched_at` reflects
    THIS docs-snapshot fetch; first live API fetch will update it."""
    notes = json.dumps(
        {
            "registry": REGISTRY_TAG,
            "license": LICENSE_NOTE,
            "license_attribution": LICENSE_ATTRIBUTION,
            "confidence_band": CONFIDENCE_BAND,
            "confidence_value": CONFIDENCE,
            "docs_snapshot_path": docs_snapshot_path,
            "docs_sha256": docs_sha256,
            "docs_retrieved_at": docs_retrieved_at,
            "endpoint": SEARCH_ENDPOINT,
            "page_limit": PAGE_LIMIT,
            "auth_kind": "HTTP Basic (RFC 7617); creds from .env/.env",
            "rate_limit_posture": (
                "HTTP 429 fail-stop verbatim per swagger (sole quota signal); "
                "defensive Retry-After parse per RFC 7231 §7.1.3 (logged "
                "but does not trigger retry; dispatch clause 3 binds NO "
                "retries on 429). TODO: extend on first live observation."
            ),
            "step": "MAC-9 Step 2 — module + prioritized-anchor-list build (DRY_RUN ON)",
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
            (SOURCE_NAME, SOURCE_TYPE, TIER, fetched_at, "docs_only", notes, sid),
        )
        return sid
    cur = conn.execute(
        "INSERT INTO sources (name, url, source_type, tier, "
        "last_fetched_at, last_status, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (SOURCE_NAME, SOURCE_URL, SOURCE_TYPE, TIER, fetched_at, "docs_only", notes),
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


def _read_flock_anchors(
    conn: sqlite3.Connection,
) -> tuple[list[tuple[int, Optional[str], Optional[str]]], list[tuple[int, float, float]]]:
    """Read Flock-attributed Atlas (source 5) + DeFlock (source 6) rows
    from `deployment_observations`.

    Returns `(atlas_rows, deflock_rows)` per `assemble_priority_rows()`
    contract.
    """
    atlas_clause, atlas_params = _flock_clause_atlas()
    atlas_rows = conn.execute(
        f"SELECT id, state, country FROM deployment_observations "
        f"WHERE source_id = 5 AND {atlas_clause}",
        atlas_params,
    ).fetchall()

    deflock_clause, deflock_params = _flock_clause_deflock()
    deflock_rows = conn.execute(
        f"SELECT id, lat, lon FROM deployment_observations "
        f"WHERE source_id = 6 AND lat IS NOT NULL AND lon IS NOT NULL "
        f"AND {deflock_clause}",
        deflock_params,
    ).fetchall()

    return list(atlas_rows), list(deflock_rows)


def build_prioritized_list(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    agent_id: str,
    docs_snapshot_path: Path = DEFAULT_DOCS_SNAPSHOT,
    docs_sha256: str = DEFAULT_DOCS_SHA256,
    docs_retrieved_at: str = DEFAULT_DOCS_RETRIEVED_AT,
) -> dict[str, object]:
    """Read Flock-attributed deployment rows, derive state, assign tier,
    and write `wigle_anchor_priority`. Idempotent: DELETE-by-extraction-run
    is not viable (we replace ALL rows since the build is global), so we
    DELETE FROM wigle_anchor_priority and bulk-insert.

    No live WiGLE queries fire. This is purely the prioritization derivation.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        sid = _upsert_source(
            conn,
            fetched_at=_utc_now(),
            docs_snapshot_path=str(docs_snapshot_path.relative_to(REPO_ROOT)),
            docs_sha256=docs_sha256,
            docs_retrieved_at=docs_retrieved_at,
        )
        run_id = _start_run(conn, agent_id=agent_id, source_id=sid)
        try:
            atlas_rows, deflock_rows = _read_flock_anchors(conn)
            insert_tuples, stats = assemble_priority_rows(atlas_rows, deflock_rows)

            conn.execute("DELETE FROM wigle_anchor_priority")
            sql = (
                "INSERT INTO wigle_anchor_priority "
                "(deployment_id, extraction_run_id, priority_tier, "
                "state_or_country, intra_tier_rank, tier_rationale, "
                "derivation_method, derivation_notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            )
            with_run_id = [
                (t[0], run_id, t[1], t[2], t[3], t[4], t[5], t[6])
                for t in insert_tuples
            ]
            conn.executemany(sql, with_run_id)

            run_notes = json.dumps(
                {
                    "registry": REGISTRY_TAG,
                    "step": "MAC-9 Step 2 — prioritized-anchor-list build",
                    "atlas_input_rows": len(atlas_rows),
                    "deflock_input_rows": len(deflock_rows),
                    "rows_staged": len(insert_tuples),
                    "skipped": stats["skipped"],
                    "skipped_samples": stats["skipped_samples"],
                    "by_tier": stats["by_tier"],
                    "deflock_attribution_pattern": (
                        "Step-1-reproducing strict 6-string canonical-name match "
                        "(includes 3 typo/combo strings: 'Flock Saftey', 'Flock "
                        "Safetu', 'Flock Safety;Motorola Solutions'). Reproduces "
                        "Step 1 §2 count of 77,953 EXACTLY. Broader \\bFlock\\b "
                        "regex set = 78,004 (51 rows wider; surfaced for CEO "
                        "review but NOT staged in Step 2)."
                    ),
                    "atlas_attribution_pattern": (
                        "LOWER(vendor_raw) LIKE '%flock%' (case-insensitive "
                        "substring). Reproduces Step 1 §2 count of 2,745 "
                        "EXACTLY against source_id=5."
                    ),
                    "state_derivation_q1": (
                        "Atlas: state column verbatim (atlas_state_column). "
                        "DeFlock: reverse_geocoder==1.5.1 admin1 -> US-postal "
                        "via US_ADMIN1_TO_POSTAL map; cc != 'US' -> ISO alpha-2 "
                        "country code (T5). Stop-and-skip on cc=US admin1 "
                        "outside expected 50+DC+territory set per §11 #1."
                    ),
                    "tier_scheme": {
                        "T1": list(T1_STATES),
                        "T2": list(T2_STATES),
                        "T3": list(T3_STATES),
                        "T4_territory_subrank": list(US_TERRITORY_CODES),
                        "T5_note": "ISO 3166 alpha-2 country codes per §12 open question",
                    },
                    "intra_tier_rank_method": (
                        "1-based within (priority_tier, state_or_country) "
                        "ordered by deployment_id ascending. Per-state rank "
                        "within tier is in tier_rationale (DeFlock-count "
                        "load-bearing density)."
                    ),
                    "phase5_reconsider_pii": (
                        "SAR-5-by-analogy rule (5) PII-redact-by-default applied "
                        "unconditionally to WiGLE SSID staging path. Marker "
                        "`# SAR-5` in code. Step-2 DRY_RUN: redaction primitives "
                        "validated against fixtures; live SSIDs not yet observed."
                    ),
                    "license": LICENSE_NOTE,
                    "license_attribution": LICENSE_ATTRIBUTION,
                },
                sort_keys=True,
            )
            _finish_run(
                conn,
                run_id,
                records_in=len(atlas_rows) + len(deflock_rows),
                records_out=len(insert_tuples),
                errors=stats["skipped"],
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
        return {
            "sources_id": sid,
            "extraction_run_id": run_id,
            "atlas_input_rows": len(atlas_rows),
            "deflock_input_rows": len(deflock_rows),
            "rows_staged": len(insert_tuples),
            "skipped": stats["skipped"],
            "by_tier": stats["by_tier"],
            "by_tier_state": stats["by_tier_state"],
            "atlas_by_tier_state": stats["atlas_by_tier_state"],
        }
    finally:
        conn.close()


# ─── HTTP — WiGLE search (gated on DRY_RUN OFF; not exercised in Step 2) ──


def _load_wigle_creds(env_path: Path = DEFAULT_ENV_PATH) -> tuple[str, str]:
    """Read `WIGLE_API_NAME` + `WIGLE_API_TOKEN` from `.env/.env`. Single
    HTTP Basic credential per swagger.json `securityDefinitions.basic`.
    """
    if not env_path.exists():
        raise RuntimeError(
            f"WiGLE creds env file not found at {env_path}; expected "
            "`.env/.env` with WIGLE_API_NAME + WIGLE_API_TOKEN per "
            "Step-0 verification"
        )
    api_name: Optional[str] = None
    api_token: Optional[str] = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k == "WIGLE_API_NAME":
            api_name = v
        elif k == "WIGLE_API_TOKEN":
            api_token = v
    if not api_name or not api_token:
        raise RuntimeError(
            "WIGLE_API_NAME or WIGLE_API_TOKEN missing from "
            f"{env_path}; cannot construct HTTP Basic auth"
        )
    return api_name, api_token


def _basic_auth_header(api_name: str, api_token: str) -> str:
    """RFC 7617 HTTP Basic. Returns the full `Authorization: Basic <b64>`
    header value. Per swagger §securityDefinitions.basic.
    """
    raw = f"{api_name}:{api_token}".encode("utf-8")
    return "Basic " + b64encode(raw).decode("ascii")


@dataclass
class QuotaSignal:
    """Parsed quota-exhaustion / rate-limit signal from a response.

    Q2 ratified — only HTTP 429 is documented. Defensive Retry-After
    parse per RFC 7231 §7.1.3 (delay-seconds OR HTTP-date). All other
    headers logged for first-live-observation extension hook.
    """
    status: int
    is_quota_exhausted: bool       # True iff status == 429
    retry_after_seconds: Optional[int]  # parsed from Retry-After if present
    raw_headers: dict[str, str]    # full header set for first-live-obs logging


def parse_quota_signal(status: int, headers: dict[str, str]) -> QuotaSignal:
    """Parse a WiGLE response for quota signals. Pure function — no I/O.

    Q2 ratified — implement only documented 429. Defensive Retry-After
    parse per RFC 7231 §7.1.3. NO retry: dispatch clause 3 binds.
    # TODO: extend on first live observation (CEO-ratifiable).
    """
    is_429 = status == 429
    retry_after: Optional[int] = None
    ra_raw = None
    for k, v in headers.items():
        if k.lower() == "retry-after":
            ra_raw = v.strip()
            break
    if ra_raw is not None:
        # RFC 7231 §7.1.3 — delay-seconds (integer) OR HTTP-date.
        try:
            retry_after = int(ra_raw)
        except ValueError:
            try:
                dt = parsedate_to_datetime(ra_raw)
                # delta from now in seconds; floor at 0
                if dt is not None:
                    delta = (dt - datetime.now(timezone.utc)).total_seconds()
                    retry_after = max(0, int(delta))
            except (TypeError, ValueError):
                LOG.warning("unparseable Retry-After=%r; ignoring", ra_raw)
                retry_after = None
    return QuotaSignal(
        status=status,
        is_quota_exhausted=is_429,
        retry_after_seconds=retry_after,
        raw_headers=dict(headers),
    )


# ─── PII redaction (SAR-5-by-analogy, exercised on SSID-staging path) ─────


# Same MAC-5/MAC-6/MAC-7/MAC-8 codified rank-token list. SSID values can
# carry rank-prefixed officer-name shapes ("Officer Smith's iPhone");
# default-to-redact per SAR-5 rule (5).
PII_RANK_TOKENS: tuple[str, ...] = (
    "Officer", "Sergeant", "Sgt", "Lieutenant", "Lt", "Captain", "Capt",
    "Major", "Colonel", "Col", "Chief", "Sheriff", "Deputy", "Detective",
    "Trooper", "Constable", "Marshal", "Mayor", "Commander", "Patrolman",
    "Corporal", "Inspector", "Commissioner",
)

PII_REGEX = re.compile(
    r"\b("
    + "|".join(re.escape(t) for t in PII_RANK_TOKENS)
    + r")\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
)

# Common PII-shape SSID patterns: "iPhone of Name", "Name's iPhone", etc.
SSID_NAME_REGEX = re.compile(
    r"(?i)\b(?:iPhone|iPad|MacBook|Galaxy|Pixel)\s+of\s+[A-Z][a-z]+"
    r"|[A-Z][a-z]+'?s\s+(?:iPhone|iPad|MacBook|Galaxy|Pixel)"
)


def redact_ssid_pii(ssid: str) -> tuple[str, list[str]]:
    """SAR-5-by-analogy redaction on a WiGLE SSID. Returns
    (redacted_ssid, hits) where hits are the matched substrings (logged
    for audit, NOT staged).

    # SAR-5: applied unconditionally on SSID-staging path per ratified
    rule (5). Default-to-redact; CEO-ratifiable Phase-5 reconsider hook.
    """
    hits: list[str] = []
    redacted = ssid
    for m in PII_REGEX.finditer(ssid):
        hits.append(m.group(0))
        redacted = redacted.replace(m.group(0), "[REDACTED-RANK-NAME]")
    for m in SSID_NAME_REGEX.finditer(ssid):
        hits.append(m.group(0))
        redacted = redacted.replace(m.group(0), "[REDACTED-PII-SSID]")
    return redacted, hits


# ─── Live-fire HTTP fetch (DRY_RUN-gated; not exercised in Step 2) ────────


def fetch_network_search(
    *,
    latrange1: float,
    latrange2: float,
    longrange1: float,
    longrange2: float,
    api_name: str,
    api_token: str,
    search_after: Optional[str] = None,
    timeout: int = 60,
) -> tuple[bytes, int, dict[str, str]]:
    """Single-shot GET to /api/v2/network/search with bbox params.

    Per swagger.json: `latrange1`/`latrange2`/`longrange1`/`longrange2` are
    all required for radius queries (lesser/greater pair each). Pagination
    via `searchAfter` cursor. Page size defaults 100, capped 100 for
    site-auth.

    Returns `(payload_bytes, status_code, headers_dict)`. Caller handles
    parsing + 429 stop-line via `parse_quota_signal`.

    NO retries (dispatch clause 3). Single-shot per query.
    """
    params = {
        "latrange1": str(latrange1),
        "latrange2": str(latrange2),
        "longrange1": str(longrange1),
        "longrange2": str(longrange2),
        "resultsPerPage": str(PAGE_LIMIT),
    }
    if search_after:
        params["searchAfter"] = search_after
    qs = urllib.parse.urlencode(params)
    url = f"{SEARCH_ENDPOINT}?{qs}"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "argus-ingest/0.1 (+contact: argus-ingest)",
            "Accept": "application/json",
            "Authorization": _basic_auth_header(api_name, api_token),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
            status = resp.getcode() or 0
            headers = {k: v for k, v in resp.getheaders()}
            return payload, status, headers
    except urllib.error.HTTPError as e:
        # 429 / 400 / 402 / 410 land here per swagger response codes.
        # Capture headers + body so caller can parse_quota_signal.
        payload = e.read() if hasattr(e, "read") else b""
        headers = {k: v for k, v in (e.headers.items() if e.headers else [])}
        return payload, e.code, headers


def run_live_query(
    *,
    latrange1: float,
    latrange2: float,
    longrange1: float,
    longrange2: float,
    dry_run: bool = DRY_RUN_DEFAULT,
    env_path: Path = DEFAULT_ENV_PATH,
) -> tuple[Optional[dict], QuotaSignal]:
    """Live-fire entry. Refuses to run if `dry_run=True` (default).

    CEO flips `dry_run=False` ONLY after WiGLE grant landing (board
    pitch sent 2026-05-04 from personal inbox; 14d window ends
    2026-05-18) OR explicit B-tier authorization. Step 2 deliverable
    does NOT call this function.
    """
    if dry_run:
        raise RuntimeError(
            "WiGLE live-fire is DRY_RUN-gated (default ON). Set "
            "dry_run=False ONLY on explicit CEO authorization "
            "(grant landing or B-tier sign-off). See module docstring."
        )
    api_name, api_token = _load_wigle_creds(env_path)
    payload, status, headers = fetch_network_search(
        latrange1=latrange1, latrange2=latrange2,
        longrange1=longrange1, longrange2=longrange2,
        api_name=api_name, api_token=api_token,
    )
    sig = parse_quota_signal(status, headers)
    if sig.is_quota_exhausted:
        # Dispatch clause 3: NO retries. Caller sees the signal and stops.
        LOG.error(
            "WiGLE quota exhausted (HTTP 429). Retry-After=%s. "
            "Dispatch clause 3 binds: NO retries. Stopping.",
            sig.retry_after_seconds,
        )
        return None, sig
    try:
        obj = json.loads(payload.decode("utf-8")) if payload else None
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"WiGLE returned non-JSON (status={status}): {e}"
        )
    return obj, sig


# ─── T1 MD live-fire (Step 1; gated on dispatch contract 251a65f3) ────────
#
# WiGLE-admin grant landed 2026-05-05 at 100 q/day; pacing 4 q/h, ~15-min
# minimum gap. Dispatch contract at MAC-9 [`251a65f3`]: T1 MD only / strict-
# set 549 anchors / no promotion / no SAR. DRY_RUN flip OFF authorized for
# T1 MD wave (CEO-class to flip back ON or transition to T2).
#
# Pacer is on-disk so cross-heartbeat enforcement holds (a single agent
# heartbeat does not see the prior heartbeat's in-memory state). Ledger
# at logs/wigle_pacer.json. Quota days roll over at UTC midnight (matches
# the implicit WiGLE quota-day convention; we will tighten on first
# observation if responses indicate otherwise).
#
# 50m bbox per anchor: a Flock camera's nearby WiFi/BSSIDs (the camera
# itself, patrol cars passing, colocated infrastructure) sit within
# ~10–50m. Larger radius dilutes attribution; smaller may miss sniffs.
# CEO-overridable via --bbox-radius-m.

WIGLE_DAILY_QUOTA = 100                # ratified at MAC-1 bd667afb #1
WIGLE_HOURLY_QUOTA = 4                 # ratified at MAC-1 bd667afb #2
WIGLE_MIN_GAP_SECONDS = 900            # ~15 min — ratified at MAC-1 bd667afb #2
DEFAULT_BBOX_RADIUS_M = 50.0           # see comment above; CEO-overridable
T1_MD_CONFIRM_TOKEN = "I-AUTHORIZE-T1-MD-LIVE-FIRE-2026-05-05"

DEFAULT_PACER_LEDGER = REPO_ROOT / "logs" / "wigle_pacer.json"
DEFAULT_T1_MD_RAW_ROOT = DEFAULT_RAW_ROOT / "t1_md"


def compute_bbox(
    lat: float, lon: float, radius_m: float = DEFAULT_BBOX_RADIUS_M
) -> tuple[float, float, float, float]:
    """Square bbox of half-side ≈ radius_m around (lat, lon).

    Returns (latrange1, latrange2, longrange1, longrange2) — WiGLE swagger
    convention: range1 = lesser, range2 = greater. Approximation:
      1° lat ≈ 111,000 m
      1° lon ≈ 111,320 × cos(lat) m
    Good to ~0.3% at typical latitudes. Refuses lat outside [-89, 89] to
    avoid cos→0 blowup.
    """
    if not -89.0 <= lat <= 89.0:
        raise ValueError(f"lat {lat!r} outside [-89, 89]; refuses bbox")
    delta_lat = radius_m / 111_000.0
    cos_lat = math.cos(math.radians(lat))
    if cos_lat < 1e-6:
        raise ValueError(f"cos(lat={lat!r}) too small; refuses bbox")
    delta_lon = radius_m / (111_320.0 * cos_lat)
    return (lat - delta_lat, lat + delta_lat, lon - delta_lon, lon + delta_lon)


@dataclass
class PacerState:
    """On-disk pacer ledger. Persisted as JSON at DEFAULT_PACER_LEDGER.

    `today_utc_iso` is YYYY-MM-DD (UTC). When today rolls over,
    today_count resets to 0. `last_query_at_iso` is the timestamp of the
    most recent successful WiGLE call (any HTTP status; quota was burned
    even on 4xx). Wave dirs are tracked per-wave so a dispatch can
    resume cleanly across heartbeats.
    """

    schema_version: int = 1
    last_query_at_iso: Optional[str] = None
    today_utc_iso: Optional[str] = None
    today_count: int = 0
    all_time_count: int = 0
    wave_dirs: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = DEFAULT_PACER_LEDGER) -> "PacerState":
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            schema_version=int(raw.get("schema_version", 1)),
            last_query_at_iso=raw.get("last_query_at_iso"),
            today_utc_iso=raw.get("today_utc_iso"),
            today_count=int(raw.get("today_count", 0)),
            all_time_count=int(raw.get("all_time_count", 0)),
            wave_dirs=dict(raw.get("wave_dirs", {})),
        )

    def save(self, path: Path = DEFAULT_PACER_LEDGER) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": self.schema_version,
                    "last_query_at_iso": self.last_query_at_iso,
                    "today_utc_iso": self.today_utc_iso,
                    "today_count": self.today_count,
                    "all_time_count": self.all_time_count,
                    "wave_dirs": self.wave_dirs,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


@dataclass
class PacerVerdict:
    can_fire: bool
    reason: str
    seconds_until_ok: int


def _today_utc_iso(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def evaluate_pacer(
    state: PacerState,
    *,
    now: Optional[datetime] = None,
    daily_quota: int = WIGLE_DAILY_QUOTA,
    min_gap_seconds: int = WIGLE_MIN_GAP_SECONDS,
) -> PacerVerdict:
    """Pure pacer decision. No I/O. Day-rollover handled here so callers
    don't accidentally treat yesterday's count as today's.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    today = _today_utc_iso(now)
    today_count = state.today_count if state.today_utc_iso == today else 0
    if today_count >= daily_quota:
        # seconds until next UTC midnight
        midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return PacerVerdict(
            can_fire=False,
            reason=f"daily_quota_exhausted ({today_count}/{daily_quota} on {today})",
            seconds_until_ok=int((midnight - now).total_seconds()),
        )
    if state.last_query_at_iso:
        last = datetime.strptime(state.last_query_at_iso, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        elapsed = (now - last).total_seconds()
        if elapsed < min_gap_seconds:
            return PacerVerdict(
                can_fire=False,
                reason=f"min_gap_not_met (elapsed={int(elapsed)}s, need {min_gap_seconds}s)",
                seconds_until_ok=int(min_gap_seconds - elapsed),
            )
    return PacerVerdict(can_fire=True, reason="ok", seconds_until_ok=0)


def record_pacer_fire(
    state: PacerState, *, now: Optional[datetime] = None
) -> PacerState:
    """Pure update: returns a new state with this fire recorded.
    Day-rollover resets today_count to 1 (this fire); else increments.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    today = _today_utc_iso(now)
    today_count = state.today_count if state.today_utc_iso == today else 0
    return PacerState(
        schema_version=state.schema_version,
        last_query_at_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        today_utc_iso=today,
        today_count=today_count + 1,
        all_time_count=state.all_time_count + 1,
        wave_dirs=dict(state.wave_dirs),
    )


def _wigle_query_url(
    latrange1: float, latrange2: float, longrange1: float, longrange2: float
) -> str:
    """Reconstruct the canonical query URL for source_url provenance.
    Uses the same param shape as fetch_network_search.
    """
    params = urllib.parse.urlencode(
        {
            "latrange1": str(latrange1),
            "latrange2": str(latrange2),
            "longrange1": str(longrange1),
            "longrange2": str(longrange2),
            "resultsPerPage": str(PAGE_LIMIT),
        }
    )
    return f"{SEARCH_ENDPOINT}?{params}"


def derive_source_row_key(*, wap_id: int, netid: str) -> str:
    """Per-result idempotency key.

    Mirrors migration 0006 precedent (sha256("doc_url|candidate_type|
    candidate_identifier")) but anchor-keyed since each WiGLE result is
    uniquely a (wap_anchor, BSSID) pair. Re-running the wave produces
    UNIQUE-violation skips for already-staged (anchor, BSSID) pairs.
    """
    payload = f"wigle|wap:{wap_id}|netid:{netid}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_t1_md_anchors(
    conn: sqlite3.Connection,
) -> list[tuple[int, int, int, float, float, str]]:
    """Returns list of (wap_id, deployment_id, intra_tier_rank, lat, lon,
    derivation_method) for T1 MD WiGLE-queryable anchors (lat/lon
    populated). Ordered by intra_tier_rank ASC. Excludes the Atlas-row
    rank-1 anchor (NULL lat/lon — known per Q3 ratification).
    """
    rows = conn.execute(
        """
        SELECT wap.id, wap.deployment_id, wap.intra_tier_rank,
               do.lat, do.lon, wap.derivation_method
          FROM wigle_anchor_priority wap
          JOIN deployment_observations do ON do.id = wap.deployment_id
         WHERE wap.priority_tier = 1
           AND wap.state_or_country = 'MD'
           AND do.lat IS NOT NULL
           AND do.lon IS NOT NULL
         ORDER BY wap.intra_tier_rank ASC
        """
    ).fetchall()
    return [(int(r[0]), int(r[1]), int(r[2]), float(r[3]), float(r[4]), str(r[5]))
            for r in rows]


def _t1_md_anchors_already_fired(
    conn: sqlite3.Connection, source_id: int
) -> set[int]:
    """Returns the set of wap_ids already fired in any prior live run.

    Detection: we encode the wap_id in the source_url's `latrange1` /
    `longrange1` derivation, but the durable signal is the raw artifact
    file at raw/wigle/t1_md/<wave>/anchor-<wap_id>.json. We can't query
    the filesystem cheaply per-anchor here, so we rely on the
    raw_observations table's source_row_key prefix `wigle|wap:<wap_id>|`
    being present for at least one row per anchor (any hit) OR the
    sentinel zero-results record (we insert one with candidate_type
    'wigle_zero_results' to mark "anchor was queried but returned
    nothing").
    """
    cur = conn.execute(
        """
        SELECT DISTINCT
               CAST(SUBSTR(notes, INSTR(notes, '"wap_id": ')+10) AS INTEGER) AS wap
          FROM raw_observations
         WHERE source_id = ?
           AND notes LIKE '%"wave": "t1_md"%'
           AND notes LIKE '%"wap_id":%'
        """,
        (source_id,),
    )
    out: set[int] = set()
    for (wap,) in cur.fetchall():
        if wap:
            out.add(int(wap))
    return out


def _wave_dir_for(state: PacerState, wave: str, raw_root: Path) -> Path:
    """Returns (and stores) a stable wave directory. New wave gets a fresh
    UTC-compact-stamped subdir; existing wave reuses prior dir.
    """
    existing = state.wave_dirs.get(wave)
    if existing:
        p = Path(existing)
        if not p.is_absolute():
            p = REPO_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p
    wave_id = _utc_now_compact()
    p = raw_root / wave_id
    p.mkdir(parents=True, exist_ok=True)
    try:
        state.wave_dirs[wave] = str(p.relative_to(REPO_ROOT))
    except ValueError:
        state.wave_dirs[wave] = str(p)
    return p


def _persist_raw_response(
    *,
    wave_dir: Path,
    wap_id: int,
    deployment_id: int,
    payload: bytes,
    status: int,
    headers: dict[str, str],
    bbox: tuple[float, float, float, float],
    fired_at_iso: str,
    query_url: str,
) -> Path:
    """Provenance-first: write the raw HTTP response to disk before any
    DB write. §11 #7 binds.
    """
    out = wave_dir / f"anchor-{wap_id}.json"
    envelope = {
        "argus_envelope": {
            "wap_id": wap_id,
            "deployment_id": deployment_id,
            "fired_at_utc": fired_at_iso,
            "http_status": status,
            "query_url": query_url,
            "bbox": {
                "latrange1": bbox[0], "latrange2": bbox[1],
                "longrange1": bbox[2], "longrange2": bbox[3],
            },
            "response_headers": headers,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "payload_byte_count": len(payload),
        },
        "wigle_response_text": payload.decode("utf-8", errors="replace"),
    }
    out.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _stage_results(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    extraction_run_id: int,
    wap_id: int,
    deployment_id: int,
    intra_tier_rank: int,
    derivation_method: str,
    query_url: str,
    raw_artifact_path: Path,
    fired_at_iso: str,
    parsed: Optional[dict],
    http_status: int,
) -> tuple[int, int, int]:
    """Insert raw_observations rows for one anchor's response. Returns
    (rows_inserted, rows_skipped_idempotent, results_observed).

    Two record shapes:
      * candidate_type='wigle_bssid' — one per result in `results[]`,
        candidate_identifier = netid (BSSID), source_excerpt carries
        ssid (PII-redacted) + lat/lon string.
      * candidate_type='wigle_zero_results' — one sentinel row when the
        response is success=true with zero results. Marks the anchor as
        "fired but empty" so re-runs don't re-query.
      * candidate_type='wigle_error' — one sentinel row when http_status
        is non-2xx (4xx/5xx). Allows audit-trail without re-firing.
    """
    rows_inserted = 0
    rows_skipped = 0
    results = []
    if parsed and parsed.get("success") and isinstance(parsed.get("results"), list):
        results = parsed["results"]

    if http_status >= 400:
        notes = json.dumps(
            {
                "wave": "t1_md",
                "wap_id": wap_id,
                "deployment_id": deployment_id,
                "intra_tier_rank": intra_tier_rank,
                "derivation_method": derivation_method,
                "fired_at_utc": fired_at_iso,
                "raw_artifact": str(raw_artifact_path.relative_to(REPO_ROOT)),
                "http_status": http_status,
                "kind": "error",
            },
            sort_keys=True,
        )
        srk = derive_source_row_key(wap_id=wap_id, netid=f"_error_{http_status}_{fired_at_iso}")
        try:
            conn.execute(
                "INSERT INTO raw_observations "
                "(source_id, extraction_run_id, source_url, raw_payload, "
                "candidate_identifier, candidate_type, source_excerpt, "
                "captured_at, notes, source_row_key) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    source_id, extraction_run_id, query_url,
                    parsed and json.dumps(parsed, sort_keys=True) or None,
                    None, "wigle_error",
                    f"WiGLE returned HTTP {http_status} for anchor {wap_id}",
                    fired_at_iso, notes, srk,
                ),
            )
            rows_inserted += 1
        except sqlite3.IntegrityError:
            rows_skipped += 1
        return rows_inserted, rows_skipped, 0

    if not results:
        notes = json.dumps(
            {
                "wave": "t1_md",
                "wap_id": wap_id,
                "deployment_id": deployment_id,
                "intra_tier_rank": intra_tier_rank,
                "derivation_method": derivation_method,
                "fired_at_utc": fired_at_iso,
                "raw_artifact": str(raw_artifact_path.relative_to(REPO_ROOT)),
                "http_status": http_status,
                "kind": "zero_results",
            },
            sort_keys=True,
        )
        srk = derive_source_row_key(wap_id=wap_id, netid="_zero_results")
        try:
            conn.execute(
                "INSERT INTO raw_observations "
                "(source_id, extraction_run_id, source_url, raw_payload, "
                "candidate_identifier, candidate_type, source_excerpt, "
                "captured_at, notes, source_row_key) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    source_id, extraction_run_id, query_url,
                    parsed and json.dumps(parsed, sort_keys=True) or None,
                    None, "wigle_zero_results",
                    f"WiGLE returned 0 results in 50m bbox around anchor {wap_id}",
                    fired_at_iso, notes, srk,
                ),
            )
            rows_inserted += 1
        except sqlite3.IntegrityError:
            rows_skipped += 1
        return rows_inserted, rows_skipped, 0

    for rec in results:
        netid = str(rec.get("netid", "")).strip()
        if not netid:
            continue
        ssid_raw = rec.get("ssid") or ""
        ssid_redacted, pii_hits = redact_ssid_pii(str(ssid_raw))
        excerpt = (
            f"BSSID={netid} SSID={ssid_redacted!r} "
            f"lat={rec.get('trilat')} lon={rec.get('trilong')} "
            f"qos={rec.get('qos')}"
        )[:200]
        notes = json.dumps(
            {
                "wave": "t1_md",
                "wap_id": wap_id,
                "deployment_id": deployment_id,
                "intra_tier_rank": intra_tier_rank,
                "derivation_method": derivation_method,
                "fired_at_utc": fired_at_iso,
                "raw_artifact": str(raw_artifact_path.relative_to(REPO_ROOT)),
                "http_status": http_status,
                "kind": "result",
                "wigle_record": rec,
                "pii_redactions": pii_hits,
            },
            sort_keys=True,
            default=str,
        )
        srk = derive_source_row_key(wap_id=wap_id, netid=netid)
        try:
            conn.execute(
                "INSERT INTO raw_observations "
                "(source_id, extraction_run_id, source_url, raw_payload, "
                "candidate_identifier, candidate_type, candidate_manufacturer, "
                "source_excerpt, captured_at, notes, source_row_key) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    source_id, extraction_run_id, query_url,
                    json.dumps(rec, sort_keys=True, default=str),
                    netid, "wigle_bssid", None,
                    excerpt, fired_at_iso, notes, srk,
                ),
            )
            rows_inserted += 1
        except sqlite3.IntegrityError:
            rows_skipped += 1
    return rows_inserted, rows_skipped, len(results)


def _upsert_source_live(conn: sqlite3.Connection, *, fetched_at: str, status: str) -> int:
    """Update the WiGLE sources row for live-fire. Status transitions
    'docs_only' → 'live_running' → 'live_partial'/'live_ok' as wave
    progresses. Notes preserved from Step 2 build (we only update the
    operational fields here).
    """
    cur = conn.execute("SELECT id FROM sources WHERE url = ?", (SOURCE_URL,))
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(
            "WiGLE sources row missing; run --build-priority-list once first"
        )
    sid = int(row[0])
    conn.execute(
        "UPDATE sources SET last_fetched_at = ?, last_status = ? WHERE id = ?",
        (fetched_at, status, sid),
    )
    return sid


@dataclass
class WaveStats:
    queries_fired: int = 0
    anchors_skipped_no_geo: int = 0
    anchors_skipped_already_fired: int = 0
    rows_inserted: int = 0
    rows_skipped_idempotent: int = 0
    results_observed: int = 0
    quota_exhausted: bool = False
    pacer_blocked_at_count: int = 0
    fires: list[dict] = field(default_factory=list)


def run_t1_md_wave(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    agent_id: str,
    confirm_token: str,
    max_queries: int = 1,
    bbox_radius_m: float = DEFAULT_BBOX_RADIUS_M,
    pacer_path: Path = DEFAULT_PACER_LEDGER,
    raw_root: Path = DEFAULT_T1_MD_RAW_ROOT,
    env_path: Path = DEFAULT_ENV_PATH,
    sleep_to_meet_gap: bool = False,
    dry_run: bool = True,
) -> dict[str, object]:
    """Drive the T1 MD live-fire wave. CEO-gated by `confirm_token`.

    `dry_run=True` (default): exercises everything except the actual HTTP
    call and the DB writes — useful for smoke-testing the driver without
    burning quota. The DRY_RUN gate on `run_live_query` is bypassed by
    this driver since the dispatch contract authorizes the flip; the
    `dry_run` arg here is a separate, finer-grained driver-level gate.

    `sleep_to_meet_gap=False`: if the pacer says wait, we exit cleanly
    rather than sleeping inside the agent's heartbeat. Set True only for
    long-running CLI invocations.

    Returns a structured stats dict (also serialized to extraction_runs.notes).
    """
    if confirm_token != T1_MD_CONFIRM_TOKEN:
        raise RuntimeError(
            "T1 MD live-fire requires --confirm "
            f"{T1_MD_CONFIRM_TOKEN!r}; refusing per dispatch contract."
        )
    if max_queries < 1:
        raise ValueError("max_queries must be >= 1")

    api_name, api_token = _load_wigle_creds(env_path)
    LOG.info("WiGLE creds loaded (HTTP Basic) — values not logged")

    pacer = PacerState.load(pacer_path)
    LOG.info(
        "pacer ledger loaded: today=%s today_count=%d all_time=%d "
        "last_query_at=%s",
        pacer.today_utc_iso, pacer.today_count, pacer.all_time_count,
        pacer.last_query_at_iso,
    )

    fetched_at_iso = _utc_now()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    stats = WaveStats()
    try:
        if dry_run:
            # Read-only path: don't mutate sources / extraction_runs / pacer
            # ledger / wave dir. We still resolve sid + simulate run_id so
            # downstream code paths exercise correctly.
            row = conn.execute(
                "SELECT id FROM sources WHERE url = ?", (SOURCE_URL,)
            ).fetchone()
            if row is None:
                raise RuntimeError(
                    "WiGLE sources row missing; run --build-priority-list once first"
                )
            sid = int(row[0])
            run_id = -1
        else:
            sid = _upsert_source_live(
                conn, fetched_at=fetched_at_iso, status="live_running",
            )
            run_id = _start_run(conn, agent_id=agent_id, source_id=sid)

        anchors = _load_t1_md_anchors(conn)
        if not anchors:
            raise RuntimeError("no T1 MD anchors with lat/lon found; aborting")
        already_fired = _t1_md_anchors_already_fired(conn, sid)
        LOG.info(
            "T1 MD anchors total=%d already_fired=%d to_process=%d",
            len(anchors), len(already_fired),
            len(anchors) - len(already_fired),
        )

        if dry_run:
            wave_dir = Path("/dev/null/dry_run_wave_dir")  # never written to
            LOG.info("[DRY_RUN] wave_dir resolution skipped")
        else:
            wave_dir = _wave_dir_for(pacer, "t1_md", raw_root)
            LOG.info("wave_dir=%s", wave_dir)

        for (wap_id, dep_id, rank, lat, lon, deriv) in anchors:
            if stats.queries_fired >= max_queries:
                break
            if wap_id in already_fired:
                stats.anchors_skipped_already_fired += 1
                continue

            verdict = evaluate_pacer(pacer)
            if not verdict.can_fire:
                stats.pacer_blocked_at_count = stats.queries_fired
                LOG.warning("pacer blocked: %s", verdict.reason)
                if sleep_to_meet_gap and verdict.reason.startswith("min_gap_not_met"):
                    LOG.info("sleeping %ds to meet pacer gap", verdict.seconds_until_ok)
                    time.sleep(verdict.seconds_until_ok + 1)
                else:
                    break

            try:
                bbox = compute_bbox(lat, lon, radius_m=bbox_radius_m)
            except ValueError as e:
                LOG.warning("anchor wap_id=%d bbox refused: %s", wap_id, e)
                stats.anchors_skipped_no_geo += 1
                continue

            query_url = _wigle_query_url(*bbox)
            fired_at_iso = _utc_now()

            if dry_run:
                LOG.info(
                    "[DRY_RUN] would fire wap_id=%d (deployment %d, rank %d) "
                    "bbox=(%.6f,%.6f,%.6f,%.6f)",
                    wap_id, dep_id, rank, *bbox,
                )
                payload = b'{"success": true, "totalResults": 0, "results": []}'
                status = 200
                headers = {"X-Argus-Dry-Run": "true"}
            else:
                LOG.info(
                    "firing wap_id=%d (deployment %d, rank %d) "
                    "bbox=(%.6f,%.6f,%.6f,%.6f)",
                    wap_id, dep_id, rank, *bbox,
                )
                payload, status, headers = fetch_network_search(
                    latrange1=bbox[0], latrange2=bbox[1],
                    longrange1=bbox[2], longrange2=bbox[3],
                    api_name=api_name, api_token=api_token,
                )

            pacer = record_pacer_fire(pacer)
            if not dry_run:
                pacer.save(pacer_path)
            stats.queries_fired += 1

            if dry_run:
                artifact_path = Path("/dev/null/dry_run_artifact.json")
            else:
                artifact_path = _persist_raw_response(
                    wave_dir=wave_dir,
                    wap_id=wap_id,
                    deployment_id=dep_id,
                    payload=payload,
                    status=status,
                    headers=headers,
                    bbox=bbox,
                    fired_at_iso=fired_at_iso,
                    query_url=query_url,
                )

            sig = parse_quota_signal(status, headers)
            if sig.is_quota_exhausted:
                LOG.error(
                    "WiGLE 429 quota-exhausted; dispatch clause 3 binds: NO retries. "
                    "Stopping wave. Retry-After=%s",
                    sig.retry_after_seconds,
                )
                stats.quota_exhausted = True
                stats.fires.append({
                    "wap_id": wap_id, "http_status": status,
                    "fired_at": fired_at_iso, "raw": str(artifact_path.relative_to(REPO_ROOT)),
                    "results_observed": 0,
                    "quota_exhausted": True,
                    "retry_after_seconds": sig.retry_after_seconds,
                })
                conn.commit()
                break

            try:
                parsed = json.loads(payload.decode("utf-8")) if payload else None
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                LOG.warning("anchor wap_id=%d non-JSON response: %s", wap_id, e)
                parsed = None

            if dry_run:
                # Simulate: a 200 with empty results would insert 1
                # zero-results sentinel; we don't actually write.
                results = (parsed or {}).get("results") or [] if isinstance(parsed, dict) else []
                inserted = 0
                skipped = 0
                observed = len(results)
            else:
                inserted, skipped, observed = _stage_results(
                    conn,
                    source_id=sid,
                    extraction_run_id=run_id,
                    wap_id=wap_id,
                    deployment_id=dep_id,
                    intra_tier_rank=rank,
                    derivation_method=deriv,
                    query_url=query_url,
                    raw_artifact_path=artifact_path,
                    fired_at_iso=fired_at_iso,
                    parsed=parsed,
                    http_status=status,
                )
            stats.rows_inserted += inserted
            stats.rows_skipped_idempotent += skipped
            stats.results_observed += observed
            try:
                raw_rel = str(artifact_path.relative_to(REPO_ROOT))
            except ValueError:
                raw_rel = str(artifact_path)
            stats.fires.append({
                "wap_id": wap_id, "deployment_id": dep_id, "rank": rank,
                "http_status": status, "fired_at": fired_at_iso,
                "raw": raw_rel,
                "results_observed": observed,
                "rows_inserted": inserted,
                "rows_skipped_idempotent": skipped,
            })
            if not dry_run:
                conn.commit()

        run_notes = json.dumps(
            {
                "registry": REGISTRY_TAG,
                "step": "MAC-9 Step 1 — T1 MD live-fire wave",
                "dispatch_contract": "MAC-9 comment 251a65f3",
                "dry_run": dry_run,
                "max_queries": max_queries,
                "bbox_radius_m": bbox_radius_m,
                "queries_fired": stats.queries_fired,
                "anchors_skipped_already_fired": stats.anchors_skipped_already_fired,
                "anchors_skipped_no_geo": stats.anchors_skipped_no_geo,
                "rows_inserted": stats.rows_inserted,
                "rows_skipped_idempotent": stats.rows_skipped_idempotent,
                "results_observed": stats.results_observed,
                "quota_exhausted": stats.quota_exhausted,
                "wave_dir": pacer.wave_dirs.get("t1_md"),
                "ratification_envelope": (
                    "100 q/day / 4 q/h / 15-min gap / T1 MD only / "
                    "strict-set 549 anchors / HTTP Basic / no promotion / no SAR. "
                    "(c) decision a4c8f80f: 51-row broadening NOT in this dispatch."
                ),
                "license": LICENSE_NOTE,
                "license_attribution": LICENSE_ATTRIBUTION,
                "fires": stats.fires,
            },
            sort_keys=True,
            default=str,
        )
        if not dry_run:
            final_status = (
                "live_quota_exhausted" if stats.quota_exhausted else "live_ok"
            )
            _upsert_source_live(conn, fetched_at=_utc_now(), status=final_status)
            _finish_run(
                conn, run_id,
                records_in=stats.queries_fired,
                records_out=stats.rows_inserted,
                errors=0 if not stats.quota_exhausted else 1,
                status="ok" if not stats.quota_exhausted else "partial",
                notes=run_notes,
            )
            conn.commit()
        else:
            conn.rollback()
    finally:
        conn.close()

    return {
        "queries_fired": stats.queries_fired,
        "rows_inserted": stats.rows_inserted,
        "rows_skipped_idempotent": stats.rows_skipped_idempotent,
        "results_observed": stats.results_observed,
        "anchors_skipped_already_fired": stats.anchors_skipped_already_fired,
        "anchors_skipped_no_geo": stats.anchors_skipped_no_geo,
        "quota_exhausted": stats.quota_exhausted,
        "wave_dir": pacer.wave_dirs.get("t1_md"),
        "fires": stats.fires,
        "pacer": {
            "today_utc_iso": pacer.today_utc_iso,
            "today_count": pacer.today_count,
            "all_time_count": pacer.all_time_count,
            "last_query_at_iso": pacer.last_query_at_iso,
        },
    }


# ─── CLI entry ────────────────────────────────────────────────────────────


def _main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="WiGLE module — Step 2 prioritized-anchor-list build")
    p.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    p.add_argument(
        "--agent-id",
        type=str,
        required=True,
        help="Paperclip agent id ingesting this run (extraction_runs.agent_id)",
    )
    p.add_argument(
        "--build-priority-list",
        action="store_true",
        help="Build the prioritized anchor list (default Step-2 deliverable).",
    )
    p.add_argument(
        "--live-fire-t1-md",
        action="store_true",
        help=(
            "Run the T1 MD live-fire wave per dispatch contract MAC-9 "
            "comment 251a65f3. Requires --confirm token. Pacer enforces "
            "100 q/day + 4 q/h + 15-min gap; honors prior wave state."
        ),
    )
    p.add_argument(
        "--confirm",
        type=str,
        default="",
        help=f"Confirmation token; must equal {T1_MD_CONFIRM_TOKEN!r}",
    )
    p.add_argument(
        "--max-queries",
        type=int,
        default=1,
        help="Max queries this invocation will fire (default 1 — first-fire).",
    )
    p.add_argument(
        "--bbox-radius-m",
        type=float,
        default=DEFAULT_BBOX_RADIUS_M,
        help=f"Half-side of square bbox per anchor (default {DEFAULT_BBOX_RADIUS_M}m)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Driver-level dry-run (smoke-test the orchestration without HTTP/DB writes).",
    )
    p.add_argument(
        "--sleep-to-meet-gap",
        action="store_true",
        help="If pacer says wait, sleep instead of exiting (long-running CLI use only).",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.build_priority_list:
        result = build_prioritized_list(
            db_path=args.db_path,
            agent_id=args.agent_id,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.live_fire_t1_md:
        result = run_t1_md_wave(
            db_path=args.db_path,
            agent_id=args.agent_id,
            confirm_token=args.confirm,
            max_queries=args.max_queries,
            bbox_radius_m=args.bbox_radius_m,
            sleep_to_meet_gap=args.sleep_to_meet_gap,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
