"""Vendor-docs Phase 4 extraction module (Wave-B / Wave-B2).

Source of truth: PROJECT_BIBLE.md §6 Phase 4 + §7.3 ExtractionWorker scope +
BIBLE_AMENDMENTS.md SAR-1, SAR-5, SAR-6.

Architecture (RATIFIED at MAC-18 Step-0, re-bound at MAC-20 Step-2):

  1. Hybrid regex-first / LLM-second. Regex pass scans cleaned text for
     identifier-bearing candidates with ±200-char anchor windows; produces
     a candidates JSON. LLM pass (caller / Phase 4 worker) classifies each
     candidate, attaches a confidence per §8.2, optionally drops false
     positives, and writes `classifications.json`. The "apply" entrypoint
     joins (candidates × classifications) and stages rows to
     `raw_observations` with the §11 #7 ≤200-char source_excerpt and SAR-5
     PII redaction enforced at insert.

  2. Tier-escalation = no-op under fixed `claude_local` model (MAC-18 #2).
     Capability-class escalation surfaces as evidence in heartbeat per
     MAC-18 #6 if observed, NOT as a silent retry.

  3. Per-row confidence values stored on each raw_observations row via
     raw_payload JSON (raw_observations has no confidence column; that's
     the identifiers-table promotion path's concern in Phase 5).

  4. Low-confidence rows escalate to Phase-5 Validator (per MAC-18 #4),
     NOT a higher-tier model. We stage them at the LLM-pass confidence;
     Phase 5 makes the keep/drop call.

  5. source_excerpt overflow → drop-with-skip-log (MAC-18 #5). Hard
     enforcement at app level — `raw_observations.source_excerpt` is
     plain TEXT in 0001 (no DB CHECK on raw_observations specifically;
     only the `identifiers` and `procurement_records` tables CHECK
     length≤200). Verified gap. App raises on overflow + records the
     drop in `extraction_runs.notes`.

  6. SAR-5 PII redaction: corporate engineering contact / installer
     name redaction via rank-token regex applied to every
     candidate-bearing source_excerpt at insert. Count-not-name
     logging into `extraction_runs.notes`.

  7. Idempotency: `source_row_key = sha256("doc_url|candidate_type|candidate_identifier")`
     per migration 0006. UNIQUE(source_id, source_row_key) WHERE
     source_row_key IS NOT NULL backstops re-runs.

§11 #8 — NO promotion to `identifiers` here. Wave-B2 Step-2 writes
`raw_observations` ONLY. Promotion is Phase-5 Validator + CEO
ratification territory.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import logging
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

LOG = logging.getLogger("argus.ingest.vendor_docs")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "db" / "argus.db"

SOURCE_TYPE = "manufacturer_doc"  # §4.1 enum (Wave-B class).
TIER = 2  # §5 — vendor docs are Tier 2 (vendor-controlled, public).

EXCERPT_MAX = 200  # §11 #7 hard cap.
ANCHOR_WINDOW = 200  # MAC-18 ratified anchor radius.

# ─── Regex passes ─────────────────────────────────────────────────────────

# Tag-strip mirrors scripts/mac19_step1_5b_survey.py — same methodology so the
# byte-level survey numbers map 1:1 to extraction inputs.
TAG_STRIP_RE = re.compile(rb"<[^>]+>")
WS_COL_RE = re.compile(rb"\s+")

# Anchor keyword classes (mirror MAC-19 Step-1.5b survey definitions).
BLE_KW_RE = re.compile(
    r"(?i)\b(?:bluetooth|ble|gatt|advertising|peripheral|service\s+uuid)\b"
)
SSID_KW_RE = re.compile(
    r"(?i)\b(?:ssid|wifi|wi-fi|wireless\s+network|default\s+network|wpa[12]?|hotspot)\b"
)
MAC_KW_RE = re.compile(
    r"(?i)\b(?:mac\s*address|hardware\s*address|oui|mac\s*range|bssid)\b"
)
CRED_KW_RE = re.compile(
    r"(?i)\b(?:default\s+(?:password|username|credentials?|admin|login)"
    r"|factory\s+(?:default|reset)"
    r"|admin\s*[:=]"
    r"|password\s*[:=]"
    r"|username\s*[:=]"
    r"|login\s*[:=]"
    r"|root\s*[:@]"
    r"|root\s+password)\b"
)

# Identifier shapes.
UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b")
# SSID-shape captures named SSID values: quoted strings, code-tagged strings,
# product-naming patterns (Pineapple_xxxx, BashBunny_xxxx, etc.), or token
# strings on a `SSID:` / `network name:` line. Cast a wide regex net at
# Pass 1; Pass 2 (LLM classifier) culls false positives.
SSID_LINE_RE = re.compile(
    r"(?i)(?:default\s+)?(?:wifi\s+)?(?:network\s+)?ssid"
    r"(?:\s+name)?\s*(?:is|=|:)\s*[\"'`]?([A-Za-z0-9][\w\-\.]{1,30})[\"'`]?"
)
SSID_PRODUCT_PATTERN_RE = re.compile(
    r"\b(Pineapple|BashBunny|Bash\s+Bunny|LANTurtle|LAN\s+Turtle|"
    r"PacketSquirrel|Packet\s+Squirrel|SharkJack|Shark\s+Jack|"
    r"KeyCroc|Key\s+Croc|ScreenCrab|Screen\s+Crab|OMG[\s\-]?Cable|"
    r"USB[\s\-]?Rubber\s+Ducky|Cloud\s*C2)"
    r"[_\-][A-Za-z0-9]{2,12}\b"
)
QUOTED_SSID_RE = re.compile(
    r"(?i)(?:connect\s+to|join|network\s+name|ssid\s+(?:of|named?))"
    r"\s+[\"'`]([A-Za-z0-9][\w\-\.\s]{1,30}?)[\"'`]"
)

# Credential value regexes — capture the value side after the keyword.
CRED_VALUE_RE = re.compile(
    r"(?i)\b(?:username|user|login|password|passphrase|admin|root)\s*[:=]\s*"
    r"[\"'`]?([A-Za-z0-9][\w\-\.@]{0,30})[\"'`]?"
)
ROOT_AT_RE = re.compile(r"\b(root@[A-Za-z0-9][\w\-]*)\b")

# ─── SAR-5 PII redaction (vendor-doc shape) ───────────────────────────────
#
# Vendor docs typically carry "engineering contact / installer / sales rep"
# names. Mirror the deflock / EFF-Atlas rank-token regex shape with vendor-
# context tokens appended. Recall over precision per CP4.

PII_RANK_TOKENS = (
    "Officer", "Sergeant", "Sgt", "Lieutenant", "Lt", "Captain", "Capt",
    "Major", "Colonel", "Col", "Chief", "Sheriff", "Deputy", "Detective",
    "Trooper", "Constable", "Marshal", "Mayor", "Commander", "Patrolman",
    "Corporal", "Inspector", "Commissioner",
    # Vendor-side roles per SAR-5 (corporate engineering contact / installer):
    "Engineer", "Installer", "Technician", "Manager", "Director", "VP",
    "President", "CEO", "CTO", "Sales", "Representative", "Rep",
    "Contact", "Author", "Reviewed\\s+by", "Approved\\s+by", "Prepared\\s+by",
    "Maintainer",
)
PII_REGEX = re.compile(
    r"\b("
    + "|".join(PII_RANK_TOKENS)
    + r")\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
)
PII_MARKER = "[REDACTED-PERSON]"


def redact_pii(value: str) -> tuple[str, int]:
    """Apply SAR-5 person-name regex. Returns (redacted, hit_count)."""
    if not value:
        return value or "", 0
    hits = 0

    def _sub(_m: re.Match[str]) -> str:
        nonlocal hits
        hits += 1
        return PII_MARKER

    return PII_REGEX.sub(_sub, value), hits


# ─── HTML / PDF cleaning ──────────────────────────────────────────────────


def clean_text(raw: bytes, content_type: str | None, file_path: Path) -> str:
    """Same shape as scripts/mac19_step1_5b_survey.clean_bytes; returns str."""
    if content_type and "pdf" in content_type.lower():
        try:
            from pdfminer.high_level import extract_text  # type: ignore

            return extract_text(str(file_path)) or ""
        except Exception as e:  # pragma: no cover — exercised only with PDFs
            LOG.warning("pdfminer FAIL on %s: %s", file_path, e)
            return raw.decode("utf-8", "replace")
    if content_type and ("html" in content_type.lower() or "xml" in content_type.lower()):
        cleaned = WS_COL_RE.sub(b" ", TAG_STRIP_RE.sub(b" ", raw))
        return cleaned.decode("utf-8", "replace")
    return raw.decode("utf-8", "replace")


# ─── Candidate dataclass ──────────────────────────────────────────────────


@dataclass
class Candidate:
    """One regex-pass candidate. LLM pass annotates + filters."""

    candidate_id: str  # stable hash for joining LLM classifications
    cohort: str
    file_relpath: str
    doc_url: str
    candidate_identifier: str  # raw extracted string (pre-normalization)
    pass_kind: str  # 'ssid_line' | 'ssid_product' | 'ssid_quoted' | 'uuid_anchored' | 'mac_anchored' | 'cred_value' | 'root_at'
    suggested_candidate_type: str  # §4.1 enum hint
    anchor_keyword: str  # the keyword that anchored it (verbatim)
    source_excerpt: str  # ≤200 chars verbatim window
    excerpt_offset: int  # byte offset into the cleaned text
    excerpt_overflow_pretrim: bool  # was the natural ±200 window >200 chars?
    pii_hits: int  # SAR-5 hits inside source_excerpt (post-redaction)


def _hash_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _trim_excerpt(text: str, center_start: int, center_end: int) -> tuple[str, int, bool]:
    """Build a source_excerpt window centered on (center_start, center_end).

    Returns (excerpt, offset, overflowed_pretrim). Excerpt is at most
    EXCERPT_MAX chars and always contains the matched span (we shrink the
    pre-context first, then the post-context, and re-include the match
    span). If the matched span itself exceeds EXCERPT_MAX, returns
    (excerpt='', offset=center_start, overflowed=True) — caller drops.
    """
    span_len = center_end - center_start
    if span_len > EXCERPT_MAX:
        return "", center_start, True
    half = (EXCERPT_MAX - span_len) // 2
    start = max(0, center_start - half)
    end = min(len(text), center_end + (EXCERPT_MAX - span_len - (center_start - start)))
    excerpt = text[start:end].strip()
    if len(excerpt) > EXCERPT_MAX:
        # Hard truncate to right-bound at EXCERPT_MAX. Caller will not see
        # this in normal operation because span_len ≤ EXCERPT_MAX; this is
        # the §11 #7 last-resort enforcement.
        excerpt = excerpt[:EXCERPT_MAX]
    overflowed = (end - start) > EXCERPT_MAX  # natural window exceeded; we trimmed
    return excerpt, start, overflowed


def _has_anchor(window: str, kind: str) -> tuple[bool, str]:
    """Return (anchored, matched_keyword)."""
    if kind == "ble":
        m = BLE_KW_RE.search(window)
    elif kind == "ssid":
        m = SSID_KW_RE.search(window)
    elif kind == "mac":
        m = MAC_KW_RE.search(window)
    elif kind == "cred":
        m = CRED_KW_RE.search(window)
    else:
        return False, ""
    if m:
        return True, m.group(0)
    return False, ""


# ─── Regex pass ───────────────────────────────────────────────────────────


def regex_pass_one_file(
    *,
    cohort: str,
    file_relpath: str,
    doc_url: str,
    text: str,
) -> tuple[list[Candidate], list[dict[str, Any]]]:
    """Yield (candidates, drop_log).

    drop_log entries: {kind, reason, file, offset, ident_preview}.
    """
    candidates: list[Candidate] = []
    drops: list[dict[str, Any]] = []

    def _make(
        *,
        ident: str,
        pass_kind: str,
        suggested_type: str,
        match_start: int,
        match_end: int,
        require_anchor: str | None,
    ) -> None:
        # Anchor window is ±ANCHOR_WINDOW around the match.
        win_start = max(0, match_start - ANCHOR_WINDOW)
        win_end = min(len(text), match_end + ANCHOR_WINDOW)
        window = text[win_start:win_end]
        anchored = True
        anchor_kw = ""
        if require_anchor:
            anchored, anchor_kw = _has_anchor(window, require_anchor)
        if not anchored:
            drops.append({
                "kind": pass_kind, "reason": "no_anchor",
                "file": file_relpath, "offset": match_start,
                "ident_preview": ident[:60],
            })
            return
        excerpt, offset, overflow = _trim_excerpt(text, match_start, match_end)
        if not excerpt:
            drops.append({
                "kind": pass_kind, "reason": "excerpt_overflow",
                "file": file_relpath, "offset": match_start,
                "ident_preview": ident[:60],
            })
            return
        # SAR-5 PII redact at extraction time. Redact the source_excerpt; the
        # candidate_identifier itself is an SSID/MAC/UUID/cred-value, so
        # redaction is excerpt-side only.
        redacted_excerpt, hits = redact_pii(excerpt)
        if len(redacted_excerpt) > EXCERPT_MAX:
            # PII marker can only ever shrink length (replaces longer name
            # token spans). This branch is defensive.
            drops.append({
                "kind": pass_kind, "reason": "post_redaction_overflow",
                "file": file_relpath, "offset": match_start,
                "ident_preview": ident[:60],
            })
            return
        cand_id = _hash_id(doc_url, pass_kind, ident, str(match_start))
        candidates.append(Candidate(
            candidate_id=cand_id,
            cohort=cohort,
            file_relpath=file_relpath,
            doc_url=doc_url,
            candidate_identifier=ident,
            pass_kind=pass_kind,
            suggested_candidate_type=suggested_type,
            anchor_keyword=anchor_kw,
            source_excerpt=redacted_excerpt,
            excerpt_offset=offset,
            excerpt_overflow_pretrim=overflow,
            pii_hits=hits,
        ))

    # 1) UUID anchored to BLE keyword → ble_uuid candidate
    for m in UUID_RE.finditer(text):
        _make(
            ident=m.group(0),
            pass_kind="uuid_anchored",
            suggested_type="ble_uuid",
            match_start=m.start(),
            match_end=m.end(),
            require_anchor="ble",
        )

    # 2) MAC anchored to MAC keyword → mac candidate
    for m in MAC_RE.finditer(text):
        _make(
            ident=m.group(0),
            pass_kind="mac_anchored",
            suggested_type="mac",
            match_start=m.start(),
            match_end=m.end(),
            require_anchor="mac",
        )

    # 3) SSID-line ("SSID is X" / "SSID: X" / "SSID = X") — context
    #    self-anchoring (the SSID keyword is in the match itself).
    for m in SSID_LINE_RE.finditer(text):
        ident = m.group(1)
        _make(
            ident=ident,
            pass_kind="ssid_line",
            suggested_type="ssid_exact",
            match_start=m.start(),
            match_end=m.end(),
            require_anchor=None,
        )

    # 4) Hak5 product naming pattern (e.g. Pineapple_X4Y2). Use ssid_pattern.
    for m in SSID_PRODUCT_PATTERN_RE.finditer(text):
        _make(
            ident=m.group(0),
            pass_kind="ssid_product",
            suggested_type="ssid_pattern",
            match_start=m.start(),
            match_end=m.end(),
            require_anchor=None,
        )

    # 5) Quoted SSID after "connect to" / "join" / "network name"
    for m in QUOTED_SSID_RE.finditer(text):
        ident = m.group(1).strip()
        _make(
            ident=ident,
            pass_kind="ssid_quoted",
            suggested_type="ssid_exact",
            match_start=m.start(1),
            match_end=m.end(1),
            require_anchor=None,
        )

    # 6) Credential value (username/password/admin/root patterns)
    for m in CRED_VALUE_RE.finditer(text):
        ident = m.group(1)
        _make(
            ident=ident,
            pass_kind="cred_value",
            suggested_type="device_fingerprint",
            match_start=m.start(),
            match_end=m.end(),
            require_anchor=None,
        )

    # 7) `root@hostname` patterns — bash prompts in setup walkthroughs
    for m in ROOT_AT_RE.finditer(text):
        _make(
            ident=m.group(1),
            pass_kind="root_at",
            suggested_type="device_fingerprint",
            match_start=m.start(),
            match_end=m.end(),
            require_anchor=None,
        )

    return candidates, drops


# ─── Manifest-driven cohort runner ────────────────────────────────────────


def run_regex_pass(
    *,
    manifest_path: Path,
    cohort_filter: str,
    out_candidates_path: Path,
    out_drops_path: Path,
) -> tuple[int, int, int]:
    """Drive regex_pass over a single cohort. Returns (files, candidates, drops)."""
    manifest = json.loads(manifest_path.read_text())
    cohort_data = manifest["cohorts"].get(cohort_filter)
    if cohort_data is None:
        raise ValueError(f"cohort {cohort_filter!r} not in manifest")

    all_candidates: list[Candidate] = []
    all_drops: list[dict[str, Any]] = []
    files_seen = 0

    for ent in cohort_data["entries"]:
        if ent.get("status") != 200:
            continue
        rel = ent.get("raw_path_relative")
        if not rel:
            continue
        file_path = REPO_ROOT / rel
        if not file_path.exists() or file_path.stat().st_size == 0:
            continue
        ct = ent.get("content_type", "")
        text = clean_text(file_path.read_bytes(), ct, file_path)
        files_seen += 1
        cands, drops = regex_pass_one_file(
            cohort=cohort_filter,
            file_relpath=rel,
            doc_url=ent.get("final_url") or ent.get("doc_url"),
            text=text,
        )
        all_candidates.extend(cands)
        all_drops.extend(drops)

    out_candidates_path.write_text(json.dumps(
        [dataclasses.asdict(c) for c in all_candidates],
        indent=2,
    ))
    out_drops_path.write_text(json.dumps(all_drops, indent=2))
    return files_seen, len(all_candidates), len(all_drops)


# ─── Apply classifications → DB ───────────────────────────────────────────


@dataclass
class Classification:
    """LLM-pass annotation for one Candidate.

    `keep=False` means LLM judged it a false positive — do not stage.
    `confidence` is per §8.2 (manufacturer_doc band: 75–90 default).
    `final_candidate_type` is the §4.1 enum the LLM landed on (may differ
    from the regex-pass suggestion — e.g. cred_value reclassified as
    not-stageable).
    """

    candidate_id: str
    keep: bool
    confidence: int  # 0–100, §8.2
    final_candidate_type: str  # §4.1 enum
    candidate_category: str  # §2.1 enum
    candidate_manufacturer: str
    notes: str = ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_source(
    conn: sqlite3.Connection, *, name: str, url: str, source_type: str, tier: int, notes: str,
) -> int:
    cur = conn.cursor()
    cur.execute("SELECT id FROM sources WHERE url = ?", (url,))
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE sources SET name=?, source_type=?, tier=?, last_fetched_at=?, last_status=?, notes=? WHERE id=?",
            (name, source_type, tier, _utc_now(), "ok", notes, row[0]),
        )
        return int(row[0])
    cur.execute(
        "INSERT INTO sources (name, url, source_type, tier, last_fetched_at, last_status, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, url, source_type, tier, _utc_now(), "ok", notes),
    )
    return int(cur.lastrowid)


def _start_run(conn: sqlite3.Connection, *, agent_id: str, source_id: int) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO extraction_runs (agent_id, source_id, started_at, status) "
        "VALUES (?, ?, ?, ?)",
        (agent_id, source_id, _utc_now(), "running"),
    )
    return int(cur.lastrowid)


def _finish_run(
    conn: sqlite3.Connection, *, run_id: int,
    records_in: int, records_out: int, errors: int,
    status: str, notes: dict[str, Any],
) -> None:
    conn.execute(
        "UPDATE extraction_runs SET finished_at=?, records_in=?, records_out=?, "
        "errors=?, status=?, notes=? WHERE id=?",
        (_utc_now(), records_in, records_out, errors, status, json.dumps(notes), run_id),
    )


def apply_classifications(
    *,
    candidates_path: Path,
    classifications_path: Path,
    db_path: Path,
    agent_id: str,
    source_name: str,
    source_url: str,
    source_notes: str,
    run_notes_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage classified candidates to raw_observations.

    Idempotency: source_row_key = sha256("doc_url|candidate_type|candidate_identifier").
    UNIQUE(source_id, source_row_key) backstops re-runs.

    Hard rules enforced at insert:
      §11 #7 source_excerpt ≤200 (drop-with-skip-log; matches MAC-18 #5)
      SAR-5 PII redaction (already applied at regex pass; counted here)
      §11 #8 raw_observations ONLY (no `identifiers` writes)
    """
    cands_raw = json.loads(candidates_path.read_text())
    classes_raw = json.loads(classifications_path.read_text())
    candidates = {c["candidate_id"]: c for c in cands_raw}
    classifications = {c["candidate_id"]: c for c in classes_raw}

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        source_id = _ensure_source(
            conn, name=source_name, url=source_url,
            source_type=SOURCE_TYPE, tier=TIER, notes=source_notes,
        )
        run_id = _start_run(conn, agent_id=agent_id, source_id=source_id)

        kept = 0
        dropped_excerpt = 0
        dropped_no_classification = 0
        dropped_llm = 0
        unique_violations = 0
        pii_hits_total = 0
        kept_by_type: dict[str, int] = {}
        kept_by_confidence: dict[str, int] = {}

        for cand_id, cand in candidates.items():
            cls = classifications.get(cand_id)
            if cls is None:
                dropped_no_classification += 1
                continue
            if not cls.get("keep", False):
                dropped_llm += 1
                continue
            excerpt = cand["source_excerpt"]
            if not excerpt or len(excerpt) > EXCERPT_MAX:
                dropped_excerpt += 1
                continue
            pii_hits_total += int(cand.get("pii_hits", 0))
            row_key = hashlib.sha256(
                f"{cand['doc_url']}|{cls['final_candidate_type']}|{cand['candidate_identifier']}".encode("utf-8")
            ).hexdigest()
            raw_payload = json.dumps({
                "doc_kind": "vendor_doc_html",
                "cohort": cand["cohort"],
                "file_relpath": cand["file_relpath"],
                "regex_pass_kind": cand["pass_kind"],
                "anchor_keyword": cand["anchor_keyword"],
                "excerpt_offset": cand["excerpt_offset"],
                "regex_suggested_type": cand["suggested_candidate_type"],
                "llm_confidence": cls["confidence"],
                "llm_notes": cls.get("notes", ""),
                "pii_redaction_hits": cand.get("pii_hits", 0),
                "extraction_module": "db.sources.vendor_docs",
                "extraction_module_run": run_id,
            })
            try:
                conn.execute(
                    "INSERT INTO raw_observations ("
                    "source_id, extraction_run_id, source_url, raw_payload, "
                    "candidate_identifier, candidate_type, candidate_category, "
                    "candidate_manufacturer, source_excerpt, source_row_key, notes"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        source_id, run_id, cand["doc_url"], raw_payload,
                        cand["candidate_identifier"],
                        cls["final_candidate_type"],
                        cls["candidate_category"],
                        cls["candidate_manufacturer"],
                        excerpt, row_key,
                        cls.get("notes", "") or None,
                    ),
                )
                kept += 1
                kept_by_type[cls["final_candidate_type"]] = (
                    kept_by_type.get(cls["final_candidate_type"], 0) + 1
                )
                bucket = _confidence_bucket(int(cls["confidence"]))
                kept_by_confidence[bucket] = kept_by_confidence.get(bucket, 0) + 1
            except sqlite3.IntegrityError as e:
                if "UNIQUE" in str(e):
                    unique_violations += 1
                else:
                    raise

        notes_obj: dict[str, Any] = {
            "wave": "B2",
            "step": "Step-2 ExtractionWorker",
            "cohort": "cohort3_hak5_wayback",
            "candidates_seen": len(candidates),
            "classifications_seen": len(classifications),
            "rows_staged": kept,
            "dropped_no_classification": dropped_no_classification,
            "dropped_llm_keep_false": dropped_llm,
            "dropped_excerpt_overflow": dropped_excerpt,
            "unique_violations": unique_violations,
            "pii_redaction_hits_total": pii_hits_total,
            "kept_by_type": kept_by_type,
            "kept_by_confidence_band": kept_by_confidence,
            "extraction_module": "db.sources.vendor_docs",
            "phase4_no_promotion_to_identifiers": True,
        }
        if run_notes_extra:
            notes_obj.update(run_notes_extra)

        _finish_run(
            conn, run_id=run_id,
            records_in=len(candidates), records_out=kept,
            errors=0, status="ok", notes=notes_obj,
        )
        conn.commit()
        return {"run_id": run_id, "source_id": source_id, **notes_obj}
    finally:
        conn.close()


def _confidence_bucket(c: int) -> str:
    """§8.2 bands (verbatim per agent-instructions) — bucketize for reporting."""
    if c >= 90:
        return "ge_90"
    if c >= 75:
        return "75_89"
    if c >= 50:
        return "50_74"
    return "lt_50"


# ─── CLI ───────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="vendor_docs", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("regex-pass", help="Run regex extraction pass over a cohort")
    pe.add_argument("--manifest", type=Path, required=True)
    pe.add_argument("--cohort", required=True)
    pe.add_argument("--out-candidates", type=Path, required=True)
    pe.add_argument("--out-drops", type=Path, required=True)

    pa = sub.add_parser("apply", help="Apply classifications and stage to raw_observations")
    pa.add_argument("--candidates", type=Path, required=True)
    pa.add_argument("--classifications", type=Path, required=True)
    pa.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    pa.add_argument("--agent-id", required=True)
    pa.add_argument("--source-name", required=True)
    pa.add_argument("--source-url", required=True)
    pa.add_argument("--source-notes", default="")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    if args.cmd == "regex-pass":
        files, cands, drops = run_regex_pass(
            manifest_path=args.manifest,
            cohort_filter=args.cohort,
            out_candidates_path=args.out_candidates,
            out_drops_path=args.out_drops,
        )
        print(json.dumps({"files_seen": files, "candidates": cands, "drops": drops}, indent=2))
        return 0
    if args.cmd == "apply":
        result = apply_classifications(
            candidates_path=args.candidates,
            classifications_path=args.classifications,
            db_path=args.db,
            agent_id=args.agent_id,
            source_name=args.source_name,
            source_url=args.source_url,
            source_notes=args.source_notes,
        )
        print(json.dumps(result, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
