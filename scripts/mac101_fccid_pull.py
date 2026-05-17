#!/usr/bin/env python3
"""
MAC-101 fccid.io + FCC EAS Filings pull procedure.

Implements §3.1-§3.4 of fccid_io_admission_runguide.md (post Patch Cycle 1+1.6).
Run-mode branches on manifest.run_mode:
  - full_dual_citation:        §3.4 dual-fetch (fccid.io + FCC.gov)
  - degraded_b_deferred_citation: §3.4.1 Option B (fccid.io only + deferred citation queue)

The §3.4.1 branch is the §7.4-faithful pattern that preserves the third-party-citation-lineage
boundary by emitting only crowdsourced-band rows during this run; the regulator citations
defer to the validator's async re-citation pass.

Usage:
    python3 scripts/mac101_fccid_pull.py --smoke-test     # one grantee, one FCC ID, end-to-end
    python3 scripts/mac101_fccid_pull.py --bulk           # full Stream A + Stream B dispatch
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ARGUS_ROOT = Path('/home/kev/argus-internal/argus')
WORK_DIR = ARGUS_ROOT / 'extraction_outputs' / 'fccid_io_admission'
RAW_FCCID = ARGUS_ROOT / 'raw' / 'fccid_io'
RAW_FCC_EAS = ARGUS_ROOT / 'raw' / 'fcc_eas_filings'

UA = 'argus-research/1.0 (kev@example.com)'
FCCID_RATE_LIMIT_SEC = 1.0
FCC_GOV_RATE_LIMIT_SEC = 0.5

PRIORITY_DOC_TYPES = ['Internal Photos', 'Test Report', 'Users Manual', 'Operational Description']
PER_FCC_ID_DOWNLOAD_CAP = 5
PER_FCC_ID_ATTACHMENT_HALT = 10  # halt threshold; surface borderline above this

PII_PATTERNS = [
    re.compile(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'),  # naive person-name FIRST LAST (advisory; full strip handled in per-context filter)
    re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),  # emails
]

VIEW_ON_FCC_RE = re.compile(r'application_id=(\d+)[^"\'>]*?fcc_id=([A-Za-z0-9\-]+)', re.IGNORECASE)
# PC1.7 Step 2 finding: FCC Grant IDs (EA######) extractable from <td class="grant-bold-content"><strong>EA######</strong></td>.
# EA# is FCC Grant ID, NOT application_id. See path_c_investigation.md.
GRANT_BOLD_EA_RE = re.compile(r'<td[^>]*class=["\']?[^"\'>]*grant-bold-content[^"\'>]*["\']?[^>]*>(?:(?!</td>).)*?<strong>(EA\d{6,9})</strong>',
                              re.IGNORECASE | re.DOTALL)
PATH_C_VERIFIED_FILINGS = ['UXX-S1A415A', '2AO3N-TH39P6ERPI', 'WLI-L3ALV900']
PATH_C_VERIFIED_AT_UTC = '2026-05-17T20:55:00Z'  # PC1.7 Step 2 completion timestamp


def setup_logging(smoke_test: bool):
    log_path = WORK_DIR / ('smoke_test.log' if smoke_test else 'bulk_run.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(log_path)],
    )


def load_manifest() -> dict:
    with open(WORK_DIR / 'manifest.json') as fh:
        return json.load(fh)


def save_manifest(m: dict):
    with open(WORK_DIR / 'manifest.json', 'w') as fh:
        json.dump(m, fh, indent=2)


def utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z')


def polite_get(session: requests.Session, url: str, sleep_sec: float = FCCID_RATE_LIMIT_SEC, timeout: int = 30) -> requests.Response:
    """GET with UA + rate-limit + 30s timeout. Returns the Response object; caller checks .status_code."""
    time.sleep(sleep_sec)
    return session.get(url, headers={'User-Agent': UA}, timeout=timeout)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_with_sha(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    sha = sha256_bytes(data)
    (path.parent / (path.name + '.sha256')).write_text(sha + '\n')
    return sha


def disk_usage_gb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = 0
    for p in path.rglob('*'):
        if p.is_file():
            total += p.stat().st_size
    return total / 1024**3


def check_storage_gates(manifest: dict) -> tuple[bool, str]:
    used_gb = disk_usage_gb(RAW_FCCID) + disk_usage_gb(RAW_FCC_EAS)
    soft = manifest['storage_gate']['soft_gb']
    hard = manifest['storage_gate']['hard_gb']
    if used_gb >= hard:
        return False, f'HARD HALT: storage used {used_gb:.2f} GB ≥ hard {hard} GB'
    if used_gb >= soft:
        return True, f'SOFT ALERT: storage used {used_gb:.2f} GB ≥ soft {soft} GB (continuing)'
    return True, f'storage_used={used_gb:.3f}GB ({100*used_gb/hard:.1f}% of hard)'


# ============================================================
# §3.1 — Per-grantee enumeration
# ============================================================

def enumerate_grantee_filings(session: requests.Session, grantee_code: str) -> list[dict]:
    """GET fccid.io/{grantee_code}; return list of {fcc_id, full_code, page_url, description}."""
    url = f'https://fccid.io/{grantee_code}'
    logging.info(f'§3.1 enumerate grantee {grantee_code}: GET {url}')
    r = polite_get(session, url)
    if r.status_code != 200:
        logging.warning(f'  grantee {grantee_code}: http={r.status_code} (skip; surface)')
        return []

    # Capture raw HTML
    grantee_index_path = RAW_FCCID / f'{grantee_code}_index.html'
    sha = write_with_sha(grantee_index_path, r.content)
    logging.info(f'  saved {grantee_index_path.name} sha={sha[:12]}...')

    soup = BeautifulSoup(r.content, 'html.parser')
    filings = []
    # fccid.io grantee pages list FCC IDs as <a> elements pointing to /{grantee}-{product}
    seen_codes = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Match /{GRANTEE}-{PRODUCT} but only for this grantee
        # Patterns observed: href="/{GRANTEE}-{PRODUCT}" or absolute URL
        m = re.match(rf'^(?:https?://fccid\.io)?/({re.escape(grantee_code)}-[A-Za-z0-9\-_]+)/?$', href, re.IGNORECASE)
        if m:
            full_code = m.group(1).upper()
            if full_code in seen_codes:
                continue
            seen_codes.add(full_code)
            product_code = full_code[len(grantee_code) + 1:]
            description = a.get_text(strip=True)[:200]
            filings.append({
                'fcc_id': full_code,
                'grantee_code': grantee_code,
                'product_code': product_code,
                'page_url': f'https://fccid.io/{full_code}',
                'description_excerpt': description,
            })
    logging.info(f'  enumerated {len(filings)} FCC IDs under {grantee_code}')
    return filings


# ============================================================
# §3.2 — Per-FCC-ID enumeration
# ============================================================

CONSUMER_SKIP_PATTERNS = [
    re.compile(r'\baudio receiver\b', re.IGNORECASE),
    re.compile(r'\bgarage door\b', re.IGNORECASE),
    re.compile(r'\bremote control\b', re.IGNORECASE),
    re.compile(r'\btoy\b', re.IGNORECASE),
    re.compile(r'\bkitchen appliance\b', re.IGNORECASE),
]


def is_borderline_for_skip(description: str) -> bool:
    for pat in CONSUMER_SKIP_PATTERNS:
        if pat.search(description):
            return True
    return False


def enumerate_filing_attachments(session: requests.Session, fcc_id: str) -> dict:
    """GET fccid.io/{fcc_id}; return parsed attachment list + view-on-fcc link metadata."""
    url = f'https://fccid.io/{fcc_id}'
    logging.info(f'§3.2 enumerate filing {fcc_id}: GET {url}')
    r = polite_get(session, url)
    result = {'fcc_id': fcc_id, 'page_url': url, 'http_code': r.status_code,
              'attachments': [], 'view_on_fcc_link': None, 'sha256': None}
    if r.status_code != 200:
        logging.warning(f'  filing {fcc_id}: http={r.status_code}')
        return result

    page_dir = RAW_FCCID / fcc_id
    sha = write_with_sha(page_dir / 'index.html', r.content)
    result['sha256'] = sha

    soup = BeautifulSoup(r.content, 'html.parser')

    # Find View on FCC website link (§3.4 / §3.4.1 deferred citation construction)
    for a in soup.find_all('a', href=True):
        href = a['href']
        link_text = a.get_text(strip=True).lower()
        m = VIEW_ON_FCC_RE.search(href)
        if m or 'fcc website' in link_text or 'view on fcc' in link_text:
            # Try to extract app_id + fcc_id query params
            if m:
                result['view_on_fcc_link'] = {
                    'href': href,
                    'application_id': m.group(1),
                    'fcc_id_param': m.group(2),
                    'method': 'regex_extract',
                }
            else:
                result['view_on_fcc_link'] = {'href': href, 'method': 'link_text_match_only'}
            break

    # Find attachment links per priority doc types
    # Heuristic: links to /{fcc_id}/{doc_type}/{filename} or similar
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        if not href:
            continue
        # Match attachment-style URLs
        m = re.match(rf'^(?:https?://fccid\.io)?/{re.escape(fcc_id)}/([^/]+)/([^?#]+)$', href, re.IGNORECASE)
        if m:
            doc_type_raw = m.group(1).replace('_', ' ').strip()
            filename = m.group(2)
            # Classify into priority doc types via fuzzy match
            doc_type_normalized = None
            for prio in PRIORITY_DOC_TYPES:
                if prio.lower().replace(' ', '') in doc_type_raw.lower().replace(' ', '').replace('-', ''):
                    doc_type_normalized = prio
                    break
            if doc_type_normalized is None:
                continue  # skip non-priority types
            result['attachments'].append({
                'doc_type': doc_type_normalized,
                'doc_type_raw': doc_type_raw,
                'filename': filename,
                'href': href if href.startswith('http') else f'https://fccid.io{href}',
                'link_text': text[:100],
            })

    # De-dup attachments by (doc_type, filename)
    seen = set()
    unique = []
    for att in result['attachments']:
        key = (att['doc_type'], att['filename'])
        if key not in seen:
            seen.add(key)
            unique.append(att)
    result['attachments'] = unique

    logging.info(f'  filing {fcc_id}: {len(result["attachments"])} priority attachments; '
                 f'view_on_fcc={"yes" if result["view_on_fcc_link"] else "NO"}')
    return result


# ============================================================
# §3.3 — Per-attachment fetch (fccid.io path)
# ============================================================

def fetch_attachment(session: requests.Session, fcc_id: str, attachment: dict) -> dict:
    """Download one attachment to raw/fccid_io/{fcc_id}/{doc_type}/{filename}; return manifest entry."""
    url = attachment['href']
    logging.info(f'§3.3 fetch {fcc_id}/{attachment["doc_type"]}/{attachment["filename"]}: GET {url}')
    r = polite_get(session, url, timeout=120)
    entry = {
        'fcc_id': fcc_id,
        'doc_type': attachment['doc_type'],
        'filename': attachment['filename'],
        'fccid_io_url': url,
        'http_code': r.status_code,
        'fetched_at_utc': utc_now(),
    }
    if r.status_code != 200:
        entry['error'] = f'http={r.status_code}'
        return entry

    # Slot directory by doc_type
    doc_dir_safe = attachment['doc_type'].replace(' ', '_').lower()
    dest = RAW_FCCID / fcc_id / doc_dir_safe / attachment['filename']
    sha = write_with_sha(dest, r.content)
    entry['sha256'] = sha
    entry['size_bytes'] = len(r.content)
    entry['stored_at'] = str(dest.relative_to(ARGUS_ROOT))
    return entry


# ============================================================
# §3.4 / §3.4.1 — FCC.gov branch (run_mode-aware)
# ============================================================
# PC1.7 amendments: URL construction deferred to validator; minimal queue shape
# captures only what is empirically reliable from fccid.io HTML (FCC ID + source
# URL + sha256). Patch 1.7.D.1: opportunistic_enrichment populated with
# grant_bold_content_ea_pattern findings (FCC Grant IDs, NOT application_id).


def extract_fcc_grant_ids(html: bytes) -> list[str]:
    """Scrape FCC Grant IDs (EA######) from <td class="grant-bold-content"><strong>...</strong></td> markup.

    Per PC1.7 Step 2 Path C investigation Item 5: stable mechanism across the verified trio.
    Returns deduplicated list of EA codes in HTML source order.
    """
    text = html.decode('utf-8', errors='ignore')
    found = []
    seen = set()
    for m in GRANT_BOLD_EA_RE.finditer(text):
        code = m.group(1).upper()
        if code not in seen:
            seen.add(code)
            found.append(code)
    return found


def build_opportunistic_enrichment(html: bytes) -> dict | None:
    """Build the opportunistic_enrichment block per Patch 1.7.D + 1.7.D.1 shape.

    Returns None if no Grant IDs found (queue entry stays minimal).
    """
    grant_ids = extract_fcc_grant_ids(html)
    if not grant_ids:
        return None
    multi = len(grant_ids) > 1
    return {
        'extraction_method': 'grant_bold_content_ea_pattern',
        'extraction_regex': r'<strong>(EA\d{6,9})</strong>',
        'context_selector': 'td.grant-bold-content',
        'application_id_value': None,  # reserved per Patch 1.7.D.1; EA# is Grant ID, not application_id
        'fcc_grant_ids': grant_ids,
        'fcc_grant_ids_count': len(grant_ids),
        'multi_grant_filing': multi,
        'multi_grant_disambiguation_required': multi,
        'verified_on_filings': PATH_C_VERIFIED_FILINGS,
        'verified_at_utc': PATH_C_VERIFIED_AT_UTC,
    }


# §6 #5e queue integrity halt — validate every queue write against required schema.
_QUEUE_REQUIRED_FIELDS = {'fcc_id', 'fccid_io_source_url', 'fccid_io_html_sha256',
                          'fcc_gov_unreachable_reason', 'deferred_at_utc',
                          'discovery_row_provisional_ids', 'expected_citation_row_emission',
                          'opportunistic_enrichment'}
_SHA256_RE = re.compile(r'^[0-9a-f]{64}$')


def validate_queue_entry(entry: dict) -> None:
    """§6 #5e: raise on malformed JSON / missing required fields / sha256 format mismatch.

    Raises ValueError on integrity violation; caller should halt the run.
    """
    missing = _QUEUE_REQUIRED_FIELDS - set(entry.keys())
    if missing:
        raise ValueError(f'§6 #5e queue integrity halt: missing required fields {sorted(missing)} in entry for {entry.get("fcc_id", "<no fcc_id>")}')
    if not isinstance(entry['fcc_id'], str) or not entry['fcc_id']:
        raise ValueError(f'§6 #5e queue integrity halt: fcc_id must be non-empty string; got {entry.get("fcc_id")!r}')
    if not entry['fccid_io_source_url'].startswith('https://fccid.io/'):
        raise ValueError(f'§6 #5e queue integrity halt: fccid_io_source_url malformed for {entry["fcc_id"]}: {entry["fccid_io_source_url"]!r}')
    if not _SHA256_RE.match(entry['fccid_io_html_sha256']):
        raise ValueError(f'§6 #5e queue integrity halt: fccid_io_html_sha256 format invalid for {entry["fcc_id"]}: {entry["fccid_io_html_sha256"]!r}')
    if not isinstance(entry['discovery_row_provisional_ids'], list):
        raise ValueError(f'§6 #5e queue integrity halt: discovery_row_provisional_ids must be a list for {entry["fcc_id"]}')
    # opportunistic_enrichment may be None or a dict; if dict, verify its shape minimally
    enr = entry['opportunistic_enrichment']
    if enr is not None:
        if not isinstance(enr, dict) or 'extraction_method' not in enr or 'fcc_grant_ids' not in enr:
            raise ValueError(f'§6 #5e queue integrity halt: opportunistic_enrichment malformed for {entry["fcc_id"]}')
    # Also: round-trip-JSON to catch any non-serializable types early
    try:
        json.dumps(entry)
    except (TypeError, ValueError) as e:
        raise ValueError(f'§6 #5e queue integrity halt: entry not JSON-serializable for {entry["fcc_id"]}: {e}')


def handle_fcc_gov_branch(session: requests.Session, fcc_id: str, fccid_io_source_url: str,
                          fccid_io_html: bytes, fccid_io_html_sha256: str,
                          manifest: dict, deferred_queue: list,
                          discovery_row_ids: list) -> dict:
    """Branch on manifest.run_mode per §3.4 vs §3.4.1 (PC1.7 minimal-queue shape).

    For the degraded run_mode (this MAC-101 run): construct minimal queue entry per Patch 1.7.D;
    populate opportunistic_enrichment per Patch 1.7.D.1 if Grant IDs scrapeable from HTML.
    """
    run_mode = manifest['run_mode']
    out: dict = {'fcc_id': fcc_id, 'run_mode': run_mode}

    if run_mode == 'full_dual_citation':
        # §3.4 — fetch FCC.gov direct (NOT taken in this MAC-101 run; egress unreachable)
        # Path A defers URL construction even in full mode (Patch 1.7.A) — but in full mode
        # the validator can be invoked synchronously by appending to a "synchronous resolution"
        # queue rather than the deferred queue. This code path is not exercised in MAC-101.
        out['note'] = 'full_dual_citation path not exercised in MAC-101 (FCC.gov unreachable)'
        return out

    if run_mode != 'degraded_b_deferred_citation':
        raise RuntimeError(f'unknown run_mode {run_mode!r} — runguide-implementation bug per §6 #9')

    # §3.4.1 — minimal queue entry per Patch 1.7.D (+ opportunistic enrichment per 1.7.D.1)
    enrichment = build_opportunistic_enrichment(fccid_io_html)
    deferred_entry = {
        'fcc_id': fcc_id,
        'fccid_io_source_url': fccid_io_source_url,
        'fccid_io_html_sha256': fccid_io_html_sha256,
        'fcc_gov_unreachable_reason': manifest['fcc_gov_egress_reprobe']['fcc_gov_unreachable_reason'],
        'deferred_at_utc': utc_now(),
        'discovery_row_provisional_ids': discovery_row_ids,
        'expected_citation_row_emission': 'validator_async_re_citation_pass_via_fcc_id_navigation',
        'opportunistic_enrichment': enrichment,
    }

    # §6 #5e integrity check — halt on any malformed entry BEFORE appending
    validate_queue_entry(deferred_entry)

    deferred_queue.append(deferred_entry)
    out['deferred_queue_entry'] = deferred_entry
    out['enrichment_present'] = enrichment is not None
    if enrichment is not None:
        out['fcc_grant_ids'] = enrichment['fcc_grant_ids']
        out['multi_grant_filing'] = enrichment['multi_grant_filing']
    return out


def persist_deferred_queue(deferred_queue: list) -> Path:
    """Write the cumulative deferred queue to disk. Caller should re-validate via §6 #5e on read-back."""
    path = WORK_DIR / 'fcc_citation_deferred_queue.json'
    payload = {
        'manifest_ref': str((WORK_DIR / 'manifest.json').relative_to(ARGUS_ROOT)),
        'schema_version': 'pc1.7.d.1',
        'written_at_utc': utc_now(),
        'entry_count': len(deferred_queue),
        'entries': deferred_queue,
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


# ============================================================
# Stream A driver
# ============================================================

def load_stream_a_targets() -> list[str]:
    """Return the flat list of grantee codes to dispatch, applying Axon + Harris disambig + YJV dedup."""
    with open(WORK_DIR / 'stream_a_targets.json') as fh:
        targets = json.load(fh)

    codes: list[str] = []
    seen = set()
    for v in targets['stream_a_vendors']:
        # Use whitelisted_grantees_for_dispatch if disambig was applied; else all grantees
        if 'whitelisted_grantees_for_dispatch' in v:
            wanted = v['whitelisted_grantees_for_dispatch']
        else:
            wanted = [g['grantee_code'] for g in v['grantees']]
        for code in wanted:
            if code not in seen:
                seen.add(code)
                codes.append(code)
    return codes


# ============================================================
# Smoke test
# ============================================================

def run_smoke_test():
    """One grantee → one FCC ID end-to-end. Verifies §3.1→§3.2→§3.3→§3.4.1 chain.

    PC1.7 Step 4: smoke target is 2AO3N (Dedrone) per dispatch — initial certifications,
    NOT Change-in-ID. Verifies queue-population correctness + opportunistic_enrichment
    populates with fcc_grant_ids array per Patch 1.7.D.1.
    """
    setup_logging(smoke_test=True)
    logging.info('=== SMOKE TEST start (PC1.7 Step 4) ===')

    manifest = load_manifest()
    if manifest['run_mode'] != 'degraded_b_deferred_citation':
        logging.warning(f'run_mode is {manifest["run_mode"]}; smoke test expects degraded_b_deferred_citation')

    session = requests.Session()

    # PC1.7 Step 4: switch to Dedrone (2AO3N) per dispatch — initial cert, richer attachments
    # than the Change-in-ID UXX-S1A415A used in PC1 Step E.a.
    smoke_grantee = '2AO3N'
    logging.info(f'smoke test grantee: {smoke_grantee} (Dedrone — initial cert)')

    # §3.1
    filings = enumerate_grantee_filings(session, smoke_grantee)
    if not filings:
        logging.error('§3.1 returned 0 filings — smoke test FAILED at enumeration')
        return 1
    logging.info(f'§3.1 OK: {len(filings)} FCC IDs')

    # Prefer 2AO3N-TH39P6ERPI (per dispatch recommendation) if enumerated; else first non-borderline
    target_fcc_id = '2AO3N-TH39P6ERPI'
    smoke_fcc_id = next((f['fcc_id'] for f in filings if f['fcc_id'] == target_fcc_id), None)
    if smoke_fcc_id is None:
        for f in filings[:5]:
            if not is_borderline_for_skip(f['description_excerpt']):
                smoke_fcc_id = f['fcc_id']
                break
    if smoke_fcc_id is None:
        smoke_fcc_id = filings[0]['fcc_id']
    logging.info(f'smoke test FCC ID: {smoke_fcc_id}')

    # §3.2
    attachments_meta = enumerate_filing_attachments(session, smoke_fcc_id)
    logging.info(f'§3.2 attachments: {len(attachments_meta["attachments"])}')

    # §3.3 — fetch up to 2 attachments for smoke (cap reduced from 5 for speed)
    attachment_records = []
    for att in attachments_meta['attachments'][:2]:
        rec = fetch_attachment(session, smoke_fcc_id, att)
        attachment_records.append(rec)
    logging.info(f'§3.3 fetched: {len([r for r in attachment_records if "sha256" in r])} attachments')

    # §3.4.1 — minimal-queue degraded branch (PC1.7 Step 3 amendments)
    # Read the cached fccid.io HTML to extract Grant IDs for opportunistic_enrichment.
    fccid_html_path = RAW_FCCID / smoke_fcc_id / 'index.html'
    fccid_html = fccid_html_path.read_bytes()
    fccid_html_sha256 = sha256_bytes(fccid_html)
    fccid_io_source_url = f'https://fccid.io/{smoke_fcc_id}'

    deferred_queue = []
    discovery_row_ids = [-1]  # smoke placeholder; bulk run uses provisional raw_observations IDs

    branch_result = handle_fcc_gov_branch(
        session, smoke_fcc_id, fccid_io_source_url, fccid_html, fccid_html_sha256,
        manifest, deferred_queue, discovery_row_ids,
    )
    logging.info(f'§3.4.1 branch: {branch_result.get("run_mode")} '
                 f'queue_appended={len(deferred_queue)} '
                 f'enrichment_present={branch_result.get("enrichment_present")} '
                 f'grant_ids={branch_result.get("fcc_grant_ids", [])} '
                 f'multi_grant={branch_result.get("multi_grant_filing")}')

    # Persist queue to disk (re-validated via §6 #5e on write per validate_queue_entry call inside handle_fcc_gov_branch)
    queue_path = persist_deferred_queue(deferred_queue)
    logging.info(f'queue persisted: {queue_path.relative_to(ARGUS_ROOT)}')

    # Verify queue on disk parses back cleanly + sha256 matches HTML on disk
    on_disk = json.loads(queue_path.read_text())
    queue_roundtrip_ok = (on_disk['entry_count'] == 1
                          and on_disk['entries'][0]['fcc_id'] == smoke_fcc_id
                          and on_disk['entries'][0]['fccid_io_html_sha256'] == fccid_html_sha256
                          and on_disk['entries'][0]['fccid_io_html_sha256'] == sha256_bytes(fccid_html_path.read_bytes()))

    # Write smoke test result
    smoke_path = WORK_DIR / 'smoke_test_result.json'
    smoke_payload = {
        'smoke_test_at_utc': utc_now(),
        'pc1_7_step': 4,
        'grantee_code': smoke_grantee,
        'fcc_id': smoke_fcc_id,
        'enumerated_filings_count': len(filings),
        'attachments_meta': attachments_meta,
        'attachment_records': attachment_records,
        'fcc_gov_branch_result': branch_result,
        'deferred_queue_after_smoke': deferred_queue,
        'queue_roundtrip_verified': queue_roundtrip_ok,
        'verdict': {
            'section_3_1_passed': len(filings) > 0,
            'section_3_2_passed': len(attachments_meta['attachments']) > 0 or attachments_meta['http_code'] == 200,
            'section_3_3_passed': any('sha256' in r for r in attachment_records),
            'section_3_4_1_minimal_queue_passed': branch_result.get('run_mode') == 'degraded_b_deferred_citation'
                                                  and len(deferred_queue) == 1,
            'queue_integrity_§6_5e_passed': queue_roundtrip_ok,
            'opportunistic_enrichment_populated': branch_result.get('enrichment_present', False),
            'fcc_grant_ids_extracted_count': len(branch_result.get('fcc_grant_ids', [])),
        },
    }
    smoke_path.write_text(json.dumps(smoke_payload, indent=2, default=str))

    storage_ok, storage_msg = check_storage_gates(manifest)
    logging.info(f'storage: {storage_msg}')

    # Verdict
    v = smoke_payload['verdict']
    all_pass = all([v['section_3_1_passed'], v['section_3_3_passed'],
                    v['section_3_4_1_minimal_queue_passed'], v['queue_integrity_§6_5e_passed']])
    logging.info(f'=== SMOKE TEST {"PASSED" if all_pass else "FAILED (review verdict)"} ===')
    logging.info(f'result file: {smoke_path.relative_to(ARGUS_ROOT)}')
    return 0 if all_pass else 2


# ============================================================
# Bulk run (post-smoke; not invoked in this commit)
# ============================================================

def run_bulk():
    """Stream A + Stream B bulk dispatch. Halt-criteria per runguide §6.

    NOT IMPLEMENTED IN THIS COMMIT — pending CEO ack of smoke-test result.
    Skeleton intentionally left for the next iteration.
    """
    setup_logging(smoke_test=False)
    logging.error('bulk run NOT implemented in this commit; smoke-test first')
    return 3


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--smoke-test', action='store_true', help='Run §3.1→§3.4.1 chain for one grantee/FCC ID')
    p.add_argument('--bulk', action='store_true', help='Full Stream A + Stream B dispatch (after smoke passes)')
    args = p.parse_args()

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    if args.smoke_test:
        sys.exit(run_smoke_test())
    elif args.bulk:
        sys.exit(run_bulk())
    else:
        p.error('one of --smoke-test or --bulk required')


if __name__ == '__main__':
    main()
