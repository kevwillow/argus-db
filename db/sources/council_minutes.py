"""Argus ingest — Granicus Legistar Web API council-minutes vendor sweep.

Phase 3 source 4/4 — MAC-11 Step 2. Stages council-resolution / ordinance
attestations naming any of the 24 canonical surveillance-vendor labels
(MAC-8 Group A + Group B union, per SAR-5 Rule 3) into
`council_minutes_matters` (DDL `db/migrations/0005_council_minutes_matters.sql`).

────────────────────────────────────────────────────────────────────────────
Source: Granicus Legistar Web API — `https://webapi.legistar.com/v1/{client}/Matters`
────────────────────────────────────────────────────────────────────────────
- Single-host structured JSON API; per-client subdomain inferred via the
  `{Client}` URL parameter (e.g. `chicago`, `sfgov`).
- OData `$filter=substringof('{label}',MatterTitle)` (case-insensitive
  server-side).
- `$top` cap = 1000 per query (per /Help); we use the cap directly.
- No robots.txt at API host (HTTP 404). No published rate limit. Most
  clients token-free; some (NYC `nyc`) require API token (HTTP 403). Step-2
  scope is 5 token-free clients only — chicago, sfgov, detroit, hampton,
  cabq.

────────────────────────────────────────────────────────────────────────────
CEO ratification anchor (MAC-11 Step 1)
────────────────────────────────────────────────────────────────────────────
- Step-1 ratification comment `bbb58e70` 2026-05-04T18:56Z. Items (a)–(g)
  ratified.
- Migration-slot correction comment `633421cc` 2026-05-04T19:01Z:
  council_minutes_matters lands at `0005_*.sql` (4→5 schema bump);
  DBArchitect device_category CHECK extension bumps to `0006_*.sql`.
- Stop-line check passed with margin (40% PDF, 50–60% Granicus). Worker-
  derived 50% thresholds are derived from SAR-5 Rules 2+6 spirit, NOT
  verbatim text — captured as audit-trail framing note in
  `feedback_sar_threshold_framing.md`.

────────────────────────────────────────────────────────────────────────────
Vendor sweep (24 canonical labels — SAR-5 Rule 3 verbatim, NO overrides)
────────────────────────────────────────────────────────────────────────────
Group A (8): Flock Safety, Motorola Solutions, Axon Enterprise,
             Cradlepoint, Sierra Wireless, L3Harris, Genetec,
             Vigilant Solutions.
Group B (16): Avigilon Alta, Rekor, Reveal, WatchGuard Video, Getac,
              Skydio, BRINC, DJI, Parrot, SoundThinking, Hak5, Cellebrite,
              Magnet Forensics, Berla, Dedrone, DroneShield.

Per-vendor HTTP call (NOT OR-combined) for explicit `matched_vendor_label`
attribution per MAC-8 precedent. Word-boundary `\b{label}\b` case-
insensitive regex POST-filter applied client-side to drop English-word
false positives that OData `substringof` cannot exclude (validated at
Step-1: bare `Flock` hits "Christian Fellowship Flock" / "Wild Parrots ...
flock"; full canonical `Flock Safety` is the right discipline). Some
canonicals (Reveal, Parrot, BRINC, DJI) remain noise-prone — Phase-5
disambig owns the recall fix; cap-hits logged in
`extraction_runs.notes.cap_hits[]`.

────────────────────────────────────────────────────────────────────────────
Stage filter + confidence sub-grading (item (e) + item (f))
────────────────────────────────────────────────────────────────────────────
- Stage `MatterStatusName='Passed'` only per §11 #1 (no fabrication of
  attestation that didn't materialize). Failed/Withdrawn/mention-only
  NOT staged.
- Confidence sub-grading per ratified item (f):
    80 = passed Resolution + named vendor + numeric `MatterCost`
    75 = passed Resolution + named vendor without cost
    70 = authorize-negotiations-only matters
- Detection heuristic for (70):
    title contains `\b(negotiate|negotiations?)\b` (case-insensitive)
    AND no parseable numeric cost.
- Below MAC-8 USAspending top-of-band (85) per worker rationale (council
  attestation < executed contract).

────────────────────────────────────────────────────────────────────────────
PII redaction (item (d) — three-regex stack at staging time)
────────────────────────────────────────────────────────────────────────────
- Rank-token leader (existing MAC-3/4/5/7/8 codified list, re-used).
- Title-prefix (Mr/Mrs/Ms/Dr/Hon/Honorable + Cap-Cap).
- Public-comment attribution (Cap-Cap + said/stated/asked/...).
- Replacement: `[REDACTED PII]`.
- Counts + sanitized site descriptors logged to
  `extraction_runs.notes.pii_redaction_counts` /
  `.ambiguous_pii_samples[]`. Never raw redacted strings.
- Raw artifacts preserved un-redacted under
  `raw/council_minutes/<UTC-ts>/legistar/<client>/matters_<vendor-slug>.json`
  (§7.2 audit trail). Never exported per §11 #14.
- Per board comment `7e827dca` "stands as written, no amendment, sub-clause:
  any human name in council-minutes context = redact-by-default regardless
  of role; ambiguous → CEO; better to over-redact than to leak."

────────────────────────────────────────────────────────────────────────────
Idempotency
────────────────────────────────────────────────────────────────────────────
- `(source_id, source_row_key)` UNIQUE per migration 0005.
- `source_row_key=f"{client}:{matter_id}"`.
- Structural backstop: `DELETE FROM council_minutes_matters WHERE source_id = ?`
  before bulk-insert.
- Re-run with same `--raw-subdir` reuses on-disk per-(client,vendor).json
  files (no re-fetch).

────────────────────────────────────────────────────────────────────────────
Stop-the-line ground rules (CEO Step-2 contract — comment `bbb58e70`)
────────────────────────────────────────────────────────────────────────────
- Stop ONLY if: (i) jurisdiction surfaces a structurally new field shape
  not seen at Step-1; (ii) all-zero-hits jurisdiction reveals previously-
  unknown vendor-label format we should pre-emptively codify; (iii)
  cap_hit_vendor fires and worker uncertain on Phase-5 ratchet wording.
- Otherwise: ground-rule "raw is raw, stage what title surfaces, Phase-5
  owns recall fix" applies.
- DO NOT fan out beyond 5 starting-batch clients in Step-2 (fan-out is a
  Step-3 dispatch decision after CEO reviews Step-2 yield-per-effort).
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import logging
import re
import socket
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


LOG = logging.getLogger("argus.ingest.council_minutes")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"
DEFAULT_RAW_ROOT = REPO_ROOT / "raw" / "council_minutes"

API_BASE = "https://webapi.legistar.com"
SOURCE_NAME = (
    "Granicus Legistar Web API — council/legislative matters across the "
    "5 token-free starting-batch clients (chicago, sfgov, detroit, hampton, cabq)"
)
SOURCE_URL = f"{API_BASE}/v1/"
SOURCE_TYPE = "procurement"  # §4.1 enum (per item (g) ratification).
TIER = 2                     # §5 — structured public records.
CONFIDENCE_BAND = "70-80-subgraded"
REGISTRY_TAG = "legistar"

# Step-2 starting-batch token-free Legistar clients (CEO-ratified).
STEP2_CLIENTS = ("chicago", "sfgov", "detroit", "hampton", "cabq")

# Token-gated / PDF-routed jurisdictions — logged in run notes only.
TOKEN_GATED_SKIPPED = ("nyc",)
FORMAT_FIT_PHASE4_ROUTED = ("sandiego", "norfolk", "lasvegas", "irvine")

# Per-client display name + ISO geographic scope.
JURISDICTION_INFO: dict[str, tuple[str, str]] = {
    "chicago":  ("City of Chicago",                  "US-IL"),
    "sfgov":    ("City and County of San Francisco", "US-CA"),
    "detroit":  ("City of Detroit",                  "US-MI"),
    "hampton":  ("City of Hampton",                  "US-VA"),
    "cabq":     ("City of Albuquerque",              "US-NM"),
}

# Per-client license attribution (state public-records law verbatim).
LICENSE_PER_CLIENT: dict[str, str] = {
    "chicago":  "Chicago City Council legislative records — Illinois Freedom of Information Act (5 ILCS 140/) public records. Published via Granicus Legistar SaaS.",
    "sfgov":    "San Francisco Board of Supervisors legislative records — California Public Records Act (Cal. Gov. Code § 7920 et seq.) public records. Published via Granicus Legistar SaaS.",
    "detroit":  "Detroit City Council records — Michigan Freedom of Information Act (MCL 15.231 et seq.) public records. Published via Granicus Legistar SaaS.",
    "hampton":  "Hampton (VA) City Council Legislative Session records — Virginia Freedom of Information Act (Va. Code § 2.2-3700 et seq.) public records. Published via Granicus Legistar SaaS.",
    "cabq":     "City of Albuquerque legislative records — New Mexico Inspection of Public Records Act (NMSA § 14-2-1 et seq.) public records. Published via Granicus Legistar SaaS.",
}

# 24-vendor MAC-8 Group A + Group B canonical-label list verbatim
# (SAR-5 Rule 3). NO keyword overrides — preserve verbatim labels for
# both OData query AND `matched_vendor_label` row.
GROUP_A_VENDORS = (
    "Flock Safety",
    "Motorola Solutions",
    "Axon Enterprise",
    "Cradlepoint",
    "Sierra Wireless",
    "L3Harris",
    "Genetec",
    "Vigilant Solutions",
)
GROUP_B_VENDORS = (
    "Avigilon Alta",
    "Rekor",
    "Reveal",
    "WatchGuard Video",
    "Getac",
    "Skydio",
    "BRINC",
    "DJI",
    "Parrot",
    "SoundThinking",
    "Hak5",
    "Cellebrite",
    "Magnet Forensics",
    "Berla",
    "Dedrone",
    "DroneShield",
)
CANONICAL_LABELS = GROUP_A_VENDORS + GROUP_B_VENDORS

# OData `$top` hard cap per Legistar /Help. We request at the cap to
# minimize calls; cap-hits are logged.
ODATA_TOP_CAP = 1000

# Per-call sleep (CEO-ratified MAC-8 standard, mirrors Step-2 contract).
REQ_INTERVAL_SECONDS = 1.0

# Wall-clock budget per jurisdiction (item (c)).
WALL_CLOCK_BUDGET_SECONDS_PER_CLIENT = 600.0  # 10 min


# ─── PII regex stack (item (d) — three-regex default-redact) ─────────────


# Rank-token leader (existing MAC-3/4/5/7/8 codified list, re-used).
PII_RANK_TOKENS = (
    "Officer", "Sergeant", "Sgt", "Lieutenant", "Lt", "Captain", "Capt",
    "Major", "Colonel", "Col", "Chief", "Sheriff", "Deputy", "Detective",
    "Trooper", "Constable", "Marshal", "Mayor", "Commander", "Patrolman",
    "Corporal", "Inspector", "Commissioner",
)
PII_RANK_REGEX = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in PII_RANK_TOKENS) + r")"
    r"\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
)

# Title-prefix leader (Mr/Mrs/Ms/Dr/Hon/Honorable + Cap-Cap).
PII_TITLE_REGEX = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Hon|Honorable)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
)

# Public-comment attribution (Cap-Cap + verb).
PII_PUBLIC_COMMENT_REGEX = re.compile(
    r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\s+"
    r"(?:said|stated|asked|commented|spoke|addressed|presented|testified|"
    r"objected|supported|opposed|requested|inquired)\b",
    re.IGNORECASE,
)

REDACTION_TOKEN = "[REDACTED PII]"


def redact_text(value: Optional[str]) -> tuple[Optional[str], dict[str, int]]:
    """Apply three-regex stack; return (redacted, per-regex-hit-counts).

    Counts are per regex variant, never raw redacted strings.
    """
    counts = {"rank": 0, "title": 0, "public_comment": 0}
    if value is None:
        return None, counts
    text = str(value)
    if not text:
        return text, counts
    text, counts["rank"] = PII_RANK_REGEX.subn(REDACTION_TOKEN, text)
    text, counts["title"] = PII_TITLE_REGEX.subn(REDACTION_TOKEN, text)
    text, counts["public_comment"] = PII_PUBLIC_COMMENT_REGEX.subn(REDACTION_TOKEN, text)
    return text, counts


# ─── Vendor-canonical word-boundary post-filter ──────────────────────────


def _word_boundary_match(label: str, text: Optional[str]) -> bool:
    """Case-insensitive `\b{label}\b` post-filter (MAC-5/MAC-6/MAC-8 standard)."""
    if not text:
        return False
    pattern = r"\b" + re.escape(label) + r"\b"
    return re.search(pattern, text, re.IGNORECASE) is not None


# ─── HTTP fetch ──────────────────────────────────────────────────────────


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _vendor_slug(label: str) -> str:
    """Filesystem-safe slug for per-vendor raw filenames."""
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def _build_legistar_url(client: str, label: str) -> str:
    """Build Matters substring-search URL for one (client, label) pair."""
    odata_filter = f"substringof('{label}',MatterTitle)"
    qs = urllib.parse.urlencode({
        "$top": ODATA_TOP_CAP,
        "$filter": odata_filter,
    }, safe="$()',")
    return f"{API_BASE}/v1/{client}/Matters?{qs}"


def _fetch_get(url: str, *, timeout: int = 60) -> tuple[bytes, int]:
    """Single-shot GET with one transient-error retry. Mirrors MAC-8 shape."""
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
    last_exc: Optional[BaseException] = None
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(
                url,
                method="GET",
                headers={
                    "User-Agent": "Argus/0.1 (council-minutes ingest; +contact via repo)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return body, resp.status
        except urllib.error.HTTPError as e:
            # Non-transient HTTP errors (e.g. 403 token-gate) — return immediately.
            try:
                body = e.read()
            except Exception:
                body = b""
            return body, e.code
        except transient_excs as e:
            last_exc = e
            if attempt == 1:
                LOG.warning("transient %s on %s — single-shot retry", type(e).__name__, url)
                time.sleep(0.5)
                continue
            raise
    raise RuntimeError(f"unreachable: {last_exc}")


# ─── Per-(client,vendor) fetch + parse ───────────────────────────────────


@dataclass
class FetchStats:
    client: str
    vendor_label: str
    raw_filename: str
    raw_sha256: str
    raw_byte_count: int
    http_status: int
    raw_results_total: int = 0
    word_boundary_kept: int = 0
    word_boundary_dropped: int = 0
    cap_hit: bool = False
    fetched_url: str = ""


def fetch_one(
    client: str, label: str,
    *,
    raw_dir: Path,
    sleep_seconds: float,
) -> tuple[list[dict], FetchStats]:
    """Fetch matters for (client, label); persist raw before parsing."""
    url = _build_legistar_url(client, label)
    body, status = _fetch_get(url)

    client_dir = raw_dir / "legistar" / client
    client_dir.mkdir(parents=True, exist_ok=True)
    slug = _vendor_slug(label)
    raw_path = client_dir / f"matters_{slug}.json"
    raw_path.write_bytes(body)

    sha = hashlib.sha256(body).hexdigest()
    stats = FetchStats(
        client=client, vendor_label=label,
        raw_filename=str(raw_path.relative_to(raw_dir)),
        raw_sha256=sha, raw_byte_count=len(body),
        http_status=status, fetched_url=url,
    )

    if status != 200:
        LOG.warning("non-200 %d on %s/%s — staging zero", status, client, label)
        time.sleep(sleep_seconds)
        return [], stats

    try:
        results = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        LOG.warning("JSON decode error %s on %s/%s — staging zero", e, client, label)
        time.sleep(sleep_seconds)
        return [], stats

    if not isinstance(results, list):
        results = []

    stats.raw_results_total = len(results)
    if len(results) >= ODATA_TOP_CAP:
        stats.cap_hit = True
        LOG.warning("$top cap hit (%d) for %s/%s", ODATA_TOP_CAP, client, label)

    time.sleep(sleep_seconds)
    return results, stats


def fetch_one_reuse(
    client: str, label: str,
    *,
    raw_dir: Path,
) -> tuple[list[dict], FetchStats]:
    """Reuse mode: read existing per-(client,vendor) JSON from disk."""
    client_dir = raw_dir / "legistar" / client
    slug = _vendor_slug(label)
    raw_path = client_dir / f"matters_{slug}.json"
    if not raw_path.exists():
        # Mark as 0-result with a synthetic stats; reuse is best-effort.
        stats = FetchStats(
            client=client, vendor_label=label,
            raw_filename=str(raw_path.relative_to(raw_dir)),
            raw_sha256="", raw_byte_count=0,
            http_status=0, fetched_url="(reused-from-disk; missing)",
        )
        return [], stats

    body = raw_path.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    stats = FetchStats(
        client=client, vendor_label=label,
        raw_filename=str(raw_path.relative_to(raw_dir)),
        raw_sha256=sha, raw_byte_count=len(body),
        # Recover http_status from raw size: 200 if non-empty JSON array,
        # otherwise tolerate (no .headers companion in council_minutes layout).
        http_status=200 if body and body.startswith(b"[") else 0,
        fetched_url="(reused-from-disk)",
    )
    try:
        results = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return [], stats
    if not isinstance(results, list):
        results = []
    stats.raw_results_total = len(results)
    stats.cap_hit = len(results) >= ODATA_TOP_CAP
    return results, stats


# ─── Confidence sub-grading + cost detection (item (f)) ──────────────────


_NEGOTIATION_REGEX = re.compile(r"\b(?:negotiate|negotiations?)\b", re.IGNORECASE)
_DIGIT_REGEX = re.compile(r"\d")


def _has_numeric_cost(matter_cost: Optional[str]) -> bool:
    """Heuristic: any digit in MatterCost (e.g. '$1,234.56', '1234567')."""
    if matter_cost is None:
        return False
    s = str(matter_cost).strip()
    if not s:
        return False
    return bool(_DIGIT_REGEX.search(s))


def _grade_confidence(matter_title: str, matter_cost: Optional[str]) -> int:
    """80/75/70 sub-grading per item (f).

    Per CEO ratification:
      80 = passed Resolution + named vendor + numeric MatterCost
      75 = passed Resolution + named vendor without cost
      70 = authorize-negotiations-only matters (negotiate/negotiations
           in title) AND no numeric cost
    """
    has_cost = _has_numeric_cost(matter_cost)
    if has_cost:
        return 80
    if _NEGOTIATION_REGEX.search(matter_title or ""):
        return 70
    return 75


# ─── Source / extraction_runs row helpers ────────────────────────────────


def _upsert_source(
    conn: sqlite3.Connection,
    *,
    fetched_at: str,
    archive_sha256: str,
    archive_byte_count: int,
    raw_subdir: str,
    licenses: dict[str, str],
) -> int:
    notes = json.dumps(
        {
            "registry": REGISTRY_TAG,
            "license_per_client": licenses,
            "byte_count": archive_byte_count,
            "content_sha256": archive_sha256,
            "confidence_band": CONFIDENCE_BAND,
            "raw_subdir": raw_subdir,
            "legistar_clients": list(STEP2_CLIENTS),
            "token_gated_skipped": list(TOKEN_GATED_SKIPPED),
            "format_fit_phase4_routed": list(FORMAT_FIT_PHASE4_ROUTED),
            "freshness_note": (
                "Granicus Legistar SaaS; jurisdictions update on their own "
                "cadence (typically per council meeting). content_sha256 is "
                "the archive sha256 (concatenated per-(client,vendor) raw "
                "sha256s in deterministic order) — captures the exact raw "
                "set staged this run."
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


# ─── Staging ─────────────────────────────────────────────────────────────


@dataclass
class StagingStats:
    inserted: int = 0
    by_client: dict[str, int] = field(default_factory=dict)
    by_vendor: dict[str, int] = field(default_factory=dict)
    by_confidence: dict[int, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    matters_seen_total: int = 0
    word_boundary_dropped_total: int = 0
    not_passed_dropped_total: int = 0
    pii_redaction_counts: dict[str, int] = field(default_factory=dict)
    ambiguous_pii_samples: list[dict] = field(default_factory=list)


def _matter_to_url(client: str, matter_id: int) -> str:
    """Canonical per-matter Legistar UI URL.

    Pattern verified against per-client subdomain. NYC's UI host is
    `legistar.council.nyc.gov`; the 5 token-free clients use
    `<client>.legistar.com`.
    """
    return f"https://{client}.legistar.com/LegislationDetail.aspx?ID={matter_id}"


def _stage_matter(
    conn: sqlite3.Connection,
    sql: str,
    *,
    source_id: int,
    extraction_run_id: int,
    client: str,
    matter: dict,
    matched_label: str,
    redacted_title: str,
    redaction_counts: dict[str, int],
) -> tuple[int, dict]:
    """Compose a council_minutes_matters row + returned (confidence, notes_obj).

    Caller writes via `conn.executemany(sql, batch)`.
    """
    matter_id = int(matter["MatterId"])
    agency_name, geo = JURISDICTION_INFO[client]

    matter_status = matter.get("MatterStatusName") or ""
    matter_cost = matter.get("MatterCost")
    confidence = _grade_confidence(redacted_title, matter_cost)

    excerpt = redacted_title[:200] if redacted_title else None
    source_url = _matter_to_url(client, matter_id)

    # Also redact PII in long-form fields stored in notes JSON.
    long_fields_redacted: dict[str, object] = {}
    long_fields_counts_total = {"rank": 0, "title": 0, "public_comment": 0}
    for fname in (
        "MatterText1", "MatterText2", "MatterText3", "MatterText4", "MatterText5",
        "MatterNotes", "MatterRequester", "MatterName",
    ):
        v = matter.get(fname)
        red, c = redact_text(v if isinstance(v, str) else None)
        long_fields_redacted[fname] = red
        for k in c:
            long_fields_counts_total[k] += c[k]

    notes_obj = {
        "registry": REGISTRY_TAG,
        "client": client,
        "matter_file": matter.get("MatterFile"),
        "matter_guid": matter.get("MatterGuid"),
        "matter_type_name": matter.get("MatterTypeName"),
        "matter_body_name": matter.get("MatterBodyName"),
        "matter_status_name": matter_status,
        "matter_intro_date": matter.get("MatterIntroDate"),
        "matter_passed_date": matter.get("MatterPassedDate"),
        "matter_enactment_date": matter.get("MatterEnactmentDate"),
        "matter_cost": matter_cost,
        "matched_vendor_label": matched_label,
        "matter_title_redacted": redacted_title,
        "matter_long_fields_redacted": long_fields_redacted,
        "pii_redaction_counts_title": redaction_counts,
        "pii_redaction_counts_long_fields": long_fields_counts_total,
        "matter_id": matter_id,
        "confidence_grade_reasoning": (
            "80=has-cost; 75=no-cost-no-negotiate; 70=authorize-negotiations-only"
        ),
    }

    return confidence, notes_obj, agency_name, geo, source_url, excerpt, matter_status, matter_cost


def _stage_council_minutes_matters(
    conn: sqlite3.Connection,
    *,
    source_id: int,
    extraction_run_id: int,
    raw_results: list[tuple[str, str, list[dict]]],
) -> StagingStats:
    """Idempotent stage. DELETE WHERE source_id = ? then bulk-insert.

    `raw_results` is an ordered list of (client, vendor_label, matters[]) tuples.
    Word-boundary post-filter + PII redaction + confidence sub-grading
    applied per-matter at staging time.
    """
    conn.execute(
        "DELETE FROM council_minutes_matters WHERE source_id = ?",
        (source_id,),
    )

    stats = StagingStats()
    stats.pii_redaction_counts = {"rank": 0, "title": 0, "public_comment": 0}

    seen_keys: set[tuple[int, str]] = set()  # (source_id, source_row_key)
    batch: list[tuple] = []
    BATCH_SIZE = 500

    sql = (
        "INSERT INTO council_minutes_matters ("
        "source_id, extraction_run_id, source_row_key, "
        "legistar_client, agency_name, agency_geographic_scope, "
        "matter_id, matter_guid, matter_file, matter_title, "
        "matter_type_name, matter_body_name, matter_status_name, "
        "matter_intro_date, matter_passed_date, matter_enactment_date, matter_cost, "
        "matched_vendor_label, vendor_canonical_name, "
        "source_url, source_type, source_excerpt, confidence, "
        "linked_identifier_id, notes"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    def _flush() -> None:
        if not batch:
            return
        conn.executemany(sql, batch)
        stats.inserted += len(batch)
        batch.clear()

    for client, label, matters in raw_results:
        for matter in matters:
            stats.matters_seen_total += 1
            stats.by_status[matter.get("MatterStatusName") or ""] = stats.by_status.get(matter.get("MatterStatusName") or "", 0) + 1

            matter_title_raw = matter.get("MatterTitle") or ""
            # Word-boundary post-filter (case-insensitive).
            if not _word_boundary_match(label, matter_title_raw):
                stats.word_boundary_dropped_total += 1
                continue

            # §11 #1 stage filter: passed only.
            matter_status = matter.get("MatterStatusName") or ""
            if matter_status != "Passed":
                stats.not_passed_dropped_total += 1
                continue

            matter_id = int(matter["MatterId"])
            row_key = f"{client}:{matter_id}"
            if (source_id, row_key) in seen_keys:
                # Multi-vendor keyword overlap — keep first (per per-vendor
                # iteration order). matched_vendor_label reflects the
                # first-seen label.
                continue
            seen_keys.add((source_id, row_key))

            # PII redaction on title.
            redacted_title, title_counts = redact_text(matter_title_raw)
            for k, v in title_counts.items():
                stats.pii_redaction_counts[k] = stats.pii_redaction_counts.get(k, 0) + v
                # Track ambiguous samples (rank-token redactions in matter
                # titles that ALSO contain the matched vendor label —
                # surface to CEO).
                if k == "rank" and v > 0:
                    sample = {
                        "client": client,
                        "matter_id": matter_id,
                        "regex_variant": "rank_token",
                        "field": "MatterTitle",
                        "matched_vendor_label": label,
                        "redacted_span_first_3_chars": (
                            (matter_title_raw[:3] if matter_title_raw else "") + "…"
                        ),
                        "matter_title_redacted": redacted_title,
                    }
                    if len(stats.ambiguous_pii_samples) < 50:
                        stats.ambiguous_pii_samples.append(sample)

            (
                confidence, notes_obj, agency_name, geo, source_url,
                excerpt, matter_status, matter_cost,
            ) = _stage_matter(
                conn, sql,
                source_id=source_id, extraction_run_id=extraction_run_id,
                client=client, matter=matter, matched_label=label,
                redacted_title=redacted_title or "",
                redaction_counts=title_counts,
            )

            # Long-fields redaction counts roll up too.
            long_counts = notes_obj.get("pii_redaction_counts_long_fields") or {}
            for k, v in long_counts.items():
                stats.pii_redaction_counts[k] = stats.pii_redaction_counts.get(k, 0) + int(v)

            notes_json = json.dumps(notes_obj, sort_keys=True)

            batch.append((
                source_id,
                extraction_run_id,
                row_key,
                client,
                agency_name,
                geo,
                matter_id,
                matter.get("MatterGuid"),
                matter.get("MatterFile"),
                redacted_title or "",
                matter.get("MatterTypeName"),
                matter.get("MatterBodyName"),
                matter_status,
                _normalize_date(matter.get("MatterIntroDate")),
                _normalize_date(matter.get("MatterPassedDate")),
                _normalize_date(matter.get("MatterEnactmentDate")),
                matter_cost if matter_cost is None else str(matter_cost),
                label,                # matched_vendor_label
                label,                # vendor_canonical_name (same as matched per Legistar matter shape)
                source_url,
                SOURCE_TYPE,
                excerpt,
                confidence,
                None,                 # linked_identifier_id (§11 #7)
                notes_json,
            ))

            stats.by_client[client] = stats.by_client.get(client, 0) + 1
            stats.by_vendor[label] = stats.by_vendor.get(label, 0) + 1
            stats.by_confidence[confidence] = stats.by_confidence.get(confidence, 0) + 1

            if len(batch) >= BATCH_SIZE:
                _flush()
    _flush()
    return stats


def _normalize_date(raw: Optional[str]) -> Optional[str]:
    """Legistar dates are `YYYY-MM-DDTHH:MM:SS`; coerce to `YYYY-MM-DD`."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    return s


# ─── Public entry point ──────────────────────────────────────────────────


@dataclass
class IngestResult:
    raw_dir: Path
    fetched_at_utc: str
    archive_sha256: str
    archive_byte_count: int
    sources_id: int
    extraction_run_id: int
    rows_staged: int
    matters_seen_total: int
    word_boundary_dropped_total: int
    not_passed_dropped_total: int
    by_client: dict[str, int]
    by_vendor: dict[str, int]
    by_confidence: dict[int, int]
    by_status: dict[str, int]
    cap_hits: list[dict]
    fetch_failures: list[dict]
    wall_clock_exceedances: list[dict]
    zero_hits_jurisdictions: list[str]
    pii_redaction_counts: dict[str, int]
    ambiguous_pii_samples: list[dict]


def ingest(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    raw_root: Path = DEFAULT_RAW_ROOT,
    agent_id: str,
    raw_subdir: Optional[str] = None,
    sleep_seconds: float = REQ_INTERVAL_SECONDS,
    clients: Optional[Iterable[str]] = None,
    vendor_labels: Optional[Iterable[str]] = None,
) -> IngestResult:
    """Fetch + parse + stage council-resolution matters across the 5
    token-free Legistar starting-batch clients.

    `raw_subdir`: if given, reuse an existing
    `raw/council_minutes/<ts>/legistar/<client>/matters_<slug>.json` rather
    than re-fetching. Otherwise fetch fresh into a new
    `raw/council_minutes/<UTC-timestamp>/`.
    """
    fetched_at_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if raw_subdir:
        raw_dir = raw_root / raw_subdir
        if not raw_dir.exists():
            raise FileNotFoundError(f"raw_subdir {raw_dir} does not exist")
    else:
        raw_dir = raw_root / fetched_at_utc
        raw_dir.mkdir(parents=True, exist_ok=True)
    LOG.info("council-minutes ingest -> raw_dir=%s", raw_dir)

    clients = tuple(clients) if clients is not None else STEP2_CLIENTS
    vendor_labels = tuple(vendor_labels) if vendor_labels is not None else CANONICAL_LABELS

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        # ── 1. Per-(client, vendor) fetch ──────────────────────────────
        raw_results: list[tuple[str, str, list[dict]]] = []
        per_call_stats: list[FetchStats] = []
        wall_clock_exceedances: list[dict] = []
        cap_hits: list[dict] = []
        fetch_failures: list[dict] = []
        zero_hits_jurisdictions: list[str] = []

        for client in clients:
            client_started_at = time.monotonic()
            client_total_results = 0
            for label in vendor_labels:
                if not raw_subdir:
                    if (time.monotonic() - client_started_at) > WALL_CLOCK_BUDGET_SECONDS_PER_CLIENT:
                        wall_clock_exceedances.append({
                            "client": client,
                            "vendor_label_at_exceed": label,
                            "elapsed_seconds": round(time.monotonic() - client_started_at, 2),
                        })
                        LOG.warning(
                            "wall-clock budget exceeded for %s; skipping remaining vendors",
                            client,
                        )
                        break
                    matters, stats = fetch_one(
                        client, label,
                        raw_dir=raw_dir,
                        sleep_seconds=sleep_seconds,
                    )
                else:
                    matters, stats = fetch_one_reuse(client, label, raw_dir=raw_dir)

                per_call_stats.append(stats)
                raw_results.append((client, label, matters))
                client_total_results += len(matters)

                if stats.cap_hit:
                    cap_hits.append({
                        "client": client,
                        "vendor_label": label,
                        "ratchet_proposed": "phase_5_pagination",
                    })
                if stats.http_status not in (200, 0):
                    fetch_failures.append({
                        "client": client,
                        "vendor_label": label,
                        "http_status": stats.http_status,
                    })

            if client_total_results == 0:
                zero_hits_jurisdictions.append(client)

        # ── 2. Manifest ─────────────────────────────────────────────────
        manifest_path = raw_dir / "manifest_step2.json"
        manifest = {
            "fetched_at_utc": fetched_at_utc if not raw_subdir else raw_subdir,
            "step": "MAC-11 Step 2 — Legistar Web API council-minutes vendor sweep ingest",
            "license_per_client": dict(LICENSE_PER_CLIENT),
            "endpoint_pattern": f"{API_BASE}/v1/{{client}}/Matters",
            "step2_clients": list(STEP2_CLIENTS),
            "token_gated_skipped": list(TOKEN_GATED_SKIPPED),
            "format_fit_phase4_routed": list(FORMAT_FIT_PHASE4_ROUTED),
            "vendor_labels_swept": list(vendor_labels),
            "case_fold": "case_insensitive",
            "word_boundary_post_filter": "applied (\\b{label}\\b case-insensitive)",
            "odata_top_cap": ODATA_TOP_CAP,
            "raw_results_total_per_call": [
                {
                    "client": s.client,
                    "vendor_label": s.vendor_label,
                    "raw_filename": s.raw_filename,
                    "http_status": s.http_status,
                    "raw_byte_count": s.raw_byte_count,
                    "raw_sha256": s.raw_sha256,
                    "raw_results_total": s.raw_results_total,
                    "cap_hit": s.cap_hit,
                }
                for s in per_call_stats
            ],
        }

        # Archive sha256 = sha256 of concatenated per-call sha256s in
        # deterministic order (client asc, vendor_label asc).
        master = hashlib.sha256()
        for s in sorted(per_call_stats, key=lambda s: (s.client, s.vendor_label)):
            master.update(s.raw_sha256.encode("ascii"))
        archive_sha256 = master.hexdigest()
        archive_byte_count = sum(s.raw_byte_count for s in per_call_stats)
        manifest["archive_sha256_over_per_call_sha256s"] = archive_sha256
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
            raw_subdir=fetched_at_utc if not raw_subdir else raw_subdir,
            licenses=dict(LICENSE_PER_CLIENT),
        )
        run_id = _start_run(conn, agent_id=agent_id, source_id=sid)
        try:
            stats = _stage_council_minutes_matters(
                conn,
                source_id=sid,
                extraction_run_id=run_id,
                raw_results=raw_results,
            )
            run_notes_obj: dict[str, object] = {
                "registry": REGISTRY_TAG,
                "raw_subdir": fetched_at_utc if not raw_subdir else raw_subdir,
                "archive_sha256_over_per_call_sha256s": archive_sha256,
                "archive_byte_count": archive_byte_count,
                "starting_batch_attempted": list(STEP2_CLIENTS),
                "format_fit_phase4_routed": list(FORMAT_FIT_PHASE4_ROUTED),
                "token_gated_skipped": list(TOKEN_GATED_SKIPPED),
                "vendor_labels_swept": list(vendor_labels),
                "case_fold": "case_insensitive",
                "word_boundary_post_filter": "applied (\\b{label}\\b case-insensitive)",
                "matters_seen_total": stats.matters_seen_total,
                "word_boundary_dropped_total": stats.word_boundary_dropped_total,
                "not_passed_dropped_total": stats.not_passed_dropped_total,
                "rows_staged": stats.inserted,
                "by_client": dict(stats.by_client),
                "by_vendor": dict(stats.by_vendor),
                "by_confidence": {str(k): v for k, v in stats.by_confidence.items()},
                "by_status_pre_filter": dict(stats.by_status),
                "zero_hits_jurisdictions": zero_hits_jurisdictions,
                "cap_hits": cap_hits,
                "fetch_failures": fetch_failures,
                "wall_clock_exceedances": wall_clock_exceedances,
                "pii_redaction_counts": dict(stats.pii_redaction_counts),
                "ambiguous_pii_samples": stats.ambiguous_pii_samples[:25],
                "confidence_band": CONFIDENCE_BAND,
                "confidence_grading_rule": (
                    "80=passed Resolution + named vendor + numeric MatterCost; "
                    "75=passed Resolution + named vendor without cost; "
                    "70=authorize-negotiations-only matter (negotiate/negotiations "
                    "in title) AND no numeric cost. Failed/Withdrawn/mention-only "
                    "NOT staged per §11 #1 + word-boundary post-filter."
                ),
                "vendor_keyword_phrasing_note": (
                    "24-vendor canonical labels staged verbatim per SAR-5 Rule 3. "
                    "NO keyword overrides applied (Phase-3 council minutes) — "
                    "differs from MAC-8 USAspending which used Harris→Harris "
                    "Corporation / Reveal→Reveal Media etc. for noise reduction. "
                    "Word-boundary `\\b{label}\\b` post-filter is the single noise "
                    "filter; bare-`Flock` validated at Step-1 to hit bird-flock "
                    "false positives, full-canonical-label `Flock Safety` is the "
                    "load-bearing discipline."
                ),
                "stage_filter_q11_1": (
                    "MatterStatusName='Passed' only. Failed/Withdrawn/mention-only "
                    "matters NOT staged per §11 #1 (no fabrication of attestation "
                    "that didn't materialize)."
                ),
                "rate_limit_posture": (
                    "1 req/s + single-shot transient retry. NOT a Checkpoint-3a-"
                    "class question (public structured-records API; webapi.legistar.com "
                    "has no robots.txt and no published per-second rate limit; "
                    "no token-gate observed for the 5 starting-batch clients)."
                ),
                "license_per_client": dict(LICENSE_PER_CLIENT),
                "phase5_reconsider_pii": (
                    "Phase-5 reconcile reviews `ambiguous_pii_samples[]` for "
                    "redactions that strip vendor-attribution context (e.g. "
                    "rank-token in MatterTitle that also contains the matched "
                    "vendor label). Per board comment `7e827dca`: ambiguous → "
                    "CEO ratification, not worker guess."
                ),
                "phase5_reconsider_recall": (
                    "Phase-5 attachment-PDF OCR (Phase-4 worker) covers recall "
                    "for vendor procurements titled without naming the vendor "
                    "(e.g. ABQ 'Police Radio Modernization' with Motorola in "
                    "the attached PDF but not in MatterTitle). Phase-3 stages "
                    "what title surfaces."
                ),
            }
            run_notes = json.dumps(run_notes_obj, sort_keys=True)
            _finish_run(
                conn,
                run_id,
                records_in=stats.matters_seen_total,
                records_out=stats.inserted,
                errors=len(fetch_failures),
                status="ok",
                notes=run_notes,
            )
            conn.commit()
        except Exception as e:
            _finish_run(
                conn,
                run_id,
                records_in=0, records_out=0, errors=1,
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
        matters_seen_total=stats.matters_seen_total,
        word_boundary_dropped_total=stats.word_boundary_dropped_total,
        not_passed_dropped_total=stats.not_passed_dropped_total,
        by_client=dict(stats.by_client),
        by_vendor=dict(stats.by_vendor),
        by_confidence=dict(stats.by_confidence),
        by_status=dict(stats.by_status),
        cap_hits=cap_hits,
        fetch_failures=fetch_failures,
        wall_clock_exceedances=wall_clock_exceedances,
        zero_hits_jurisdictions=zero_hits_jurisdictions,
        pii_redaction_counts=dict(stats.pii_redaction_counts),
        ambiguous_pii_samples=list(stats.ambiguous_pii_samples),
    )


# ─── CLI ─────────────────────────────────────────────────────────────────


def _main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    p.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    p.add_argument(
        "--raw-subdir",
        type=str,
        default=None,
        help=(
            "Reuse an existing raw/council_minutes/<subdir>/ rather than "
            "re-fetching (idempotency mode)."
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
        help="Per-request sleep (default 1.0s — CEO-ratified MAC-8 standard).",
    )
    p.add_argument(
        "--client",
        action="append",
        default=None,
        help=(
            "Restrict to one client (repeatable). Default: all 5 token-free "
            f"clients ({','.join(STEP2_CLIENTS)})."
        ),
    )
    p.add_argument(
        "--vendor-label",
        action="append",
        default=None,
        help=(
            "Restrict to one canonical vendor label (repeatable). Default: "
            "all 24 SAR-5 Rule 3 verbatim labels."
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
        clients=args.client,
        vendor_labels=args.vendor_label,
    )
    print(f"raw_dir: {result.raw_dir}")
    print(f"fetched_at_utc: {result.fetched_at_utc}")
    print(f"archive_sha256: {result.archive_sha256}")
    print(f"archive_byte_count: {result.archive_byte_count}")
    print(f"sources_id: {result.sources_id}")
    print(f"extraction_run_id: {result.extraction_run_id}")
    print(f"rows_staged: {result.rows_staged}")
    print(f"matters_seen_total: {result.matters_seen_total}")
    print(f"word_boundary_dropped_total: {result.word_boundary_dropped_total}")
    print(f"not_passed_dropped_total: {result.not_passed_dropped_total}")
    print(f"zero_hits_jurisdictions: {result.zero_hits_jurisdictions}")
    print(f"cap_hits: {len(result.cap_hits)}")
    print(f"fetch_failures: {len(result.fetch_failures)}")
    print(f"wall_clock_exceedances: {len(result.wall_clock_exceedances)}")
    print("by_client:")
    for c, n in sorted(result.by_client.items(), key=lambda kv: -kv[1]):
        print(f"  {c}: {n}")
    print("by_vendor:")
    for v, n in sorted(result.by_vendor.items(), key=lambda kv: -kv[1]):
        print(f"  {v}: {n}")
    print("by_confidence:")
    for c, n in sorted(result.by_confidence.items(), key=lambda kv: -kv[0]):
        print(f"  {c}: {n}")
    print(f"PII redaction counts: {result.pii_redaction_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
