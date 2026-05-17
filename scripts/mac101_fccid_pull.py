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
    """GET with UA + rate-limit + 30s timeout. Returns the Response object; caller checks .status_code.

    §6 #4 enforcement: on 429 / 503 with Retry-After, sleep the indicated duration (capped at 60s)
    and retry once before returning the response to caller.

    PC1.8.A: ReadTimeout / ConnectionError now trigger capped exponential backoff (5s, 15s, 45s).
    If all 3 attempts fail, raise the final exception for the caller to handle (typically
    treated as a documented_absence at the grantee level rather than a run-wide halt).
    """
    time.sleep(sleep_sec)
    backoffs = [5.0, 15.0, 45.0]
    last_exc: Exception | None = None
    for attempt in range(len(backoffs) + 1):  # 1 initial + 3 retries
        try:
            r = session.get(url, headers={'User-Agent': UA}, timeout=timeout)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError,
                requests.exceptions.ChunkedEncodingError) as e:
            last_exc = e
            if attempt >= len(backoffs):
                logging.error(f'polite_get final failure for {url}: {type(e).__name__}: {e}')
                raise
            sleep_for = backoffs[attempt]
            logging.warning(f'polite_get {type(e).__name__} on {url} (attempt {attempt+1}/{len(backoffs)+1}); backoff {sleep_for}s')
            time.sleep(sleep_for)
            continue
        # 429 / 503 Retry-After path
        if r.status_code in (429, 503):
            retry_after = r.headers.get('Retry-After', '').strip()
            backoff = 5.0
            if retry_after.isdigit():
                backoff = min(float(retry_after), 60.0)
            logging.warning(f'§6 #4 backoff: http={r.status_code} Retry-After={retry_after!r} sleep={backoff}s url={url}')
            time.sleep(backoff)
            r = session.get(url, headers={'User-Agent': UA}, timeout=timeout)
        return r
    # Should not reach here (loop either returns or raises)
    raise last_exc if last_exc else RuntimeError(f'polite_get exhausted retries for {url}')


# §6 #8 PII surfacing detector — runs on fccid.io HTML index pages we capture.
# Attachment PDFs are NOT scanned in §3 (they stay raw; §4 does extract+PII-strip).
PII_REGEXES = {
    'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    'us_phone': re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    # Naive person-name pattern; many false positives — used only in conjunction with high-risk context
    'person_name_in_signature_block': re.compile(
        r'(?:signed|signature|engineer|director|manager|technician|prepared by|reviewed by)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        re.IGNORECASE
    ),
}
PII_ALLOWLIST = {
    'kev@example.com',                  # our own UA
    'argus-research@example.com',
    'argus-research/1.0',
}


def scan_for_pii(text: str, context: str) -> list[dict]:
    """Return list of PII findings: [{kind, snippet, context}]. Empty list → no PII surfaced."""
    findings = []
    for kind, rx in PII_REGEXES.items():
        for m in rx.finditer(text):
            hit = m.group(0)
            if hit.lower() in {a.lower() for a in PII_ALLOWLIST}:
                continue
            snippet = text[max(0, m.start() - 40): m.end() + 40].replace('\n', ' ')[:200]
            findings.append({'kind': kind, 'value': hit, 'snippet': snippet, 'context': context})
    return findings


def append_pii_finding(findings: list[dict]):
    """§6 #8 PII surface — append to pii_surface_audit.json and signal halt to caller."""
    if not findings:
        return
    path = WORK_DIR / 'pii_surface_audit.json'
    current = {'manifest_ref': 'extraction_outputs/fccid_io_admission/manifest.json', 'findings': []}
    if path.exists():
        try:
            current = json.loads(path.read_text())
        except Exception:
            pass
    current['findings'].extend([{'detected_at_utc': utc_now(), **f} for f in findings])
    current['last_updated_utc'] = utc_now()
    path.write_text(json.dumps(current, indent=2))


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
        # PC1.8.A: accept BOTH hyphenated (UXX-S1A415A, 2AO3N-TH39P6ERPI, WLI-L3ALV900)
        # AND no-hyphen (JAAPW1008, JAA8401-800, JAA2074800 — Motorola Solutions Canada-style)
        # FCC ID formats. First char after grantee must be hyphen OR alphanumeric (excludes
        # period to skip .rss, excludes slash to skip /JAA/Internal-Photos/file attachment paths).
        m = re.match(
            rf'^(?:https?://fccid\.io)?/({re.escape(grantee_code)}(?:-|[A-Za-z0-9])[A-Za-z0-9\-_]*)/?$',
            href, re.IGNORECASE,
        )
        if m:
            full_code = m.group(1).upper()
            if full_code in seen_codes:
                continue
            seen_codes.add(full_code)
            # Strip optional leading hyphen from the product code portion
            after_grantee = full_code[len(grantee_code):]
            product_code = after_grantee[1:] if after_grantee.startswith('-') else after_grantee
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

# ============================================================
# Stream B — fccid.io grantee-name search
# ============================================================

STREAM_B_VENDORS = [
    'BRINC', 'Berla', 'BriefCam', 'Cellebrite', 'Clearview AI', 'DroneShield',
    'Engility', 'Genetec', 'Hak5', 'Magnet Forensics', 'Rekor', 'Septier',
    'SoundThinking', 'Vigilant Solutions',
]


def search_fccid_grantee_name(session: requests.Session, vendor: str) -> list[str]:
    """§2.7 Stream B: search fccid.io's grantee-code-by-name interface; return list of grantee codes.

    Halt-criterion per §2.7.1: > 20 candidate grantee codes triggers defensive disambig (caller handles).
    """
    url = f'https://fccid.io/grantee-code/?search={urllib.parse.quote(vendor)}'
    logging.info(f'Stream B search vendor={vendor!r}: GET {url}')
    r = polite_get(session, url)
    if r.status_code != 200:
        logging.warning(f'  vendor {vendor!r}: http={r.status_code}; treating as 0 results')
        return []
    soup = BeautifulSoup(r.content, 'html.parser')
    # Grantee codes on fccid.io are formatted as 3-5 char alphanumeric prefixes,
    # surfaced via /{grantee_code} links. Parse all unique hrefs that match.
    codes = []
    seen = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        m = re.match(r'^(?:https?://fccid\.io)?/([A-Z0-9]{3,5})/?$', href, re.IGNORECASE)
        if m:
            code = m.group(1).upper()
            if code in seen or code in {'API', 'FAQ', 'DMCA', 'BLOG', 'HOME', 'TYPES', 'CHARTS'}:
                continue
            seen.add(code)
            codes.append(code)
    logging.info(f'  vendor {vendor!r}: {len(codes)} grantee codes found')
    return codes


# ============================================================
# Bulk run halt-criteria + progress
# ============================================================

# §6 #10 wall-clock hard cap. Original 4h soft / 6h hard for §3 minus PC1.7 cost = 4h 43m hard.
BULK_HARD_CAP_MIN = 283
BULK_SOFT_CAP_MIN = 163  # 2h 43m soft target (informational)
CANARY_AT_MIN = 120
CANARY_MIN_COMPLETION_PCT = 40
PROGRESS_CHECKPOINT_EVERY = 25
STREAM_B_PER_VENDOR_HALT = 20  # >20 triggers defensive disambig per §2.7.1


class HaltError(Exception):
    """Raised when a §6 halt-criterion fires; caller logs + writes STOP_THE_LINE and exits."""


def check_halt_criteria(start_ts: float, manifest: dict, processed_count: int,
                        expected_total: int, deferred_queue: list,
                        progress_path: Path):
    """Composite halt-criteria check. Raises HaltError on any trip."""
    elapsed_min = (time.time() - start_ts) / 60.0

    # §6 #10 wall-clock hard cap
    if elapsed_min >= BULK_HARD_CAP_MIN:
        raise HaltError(f'§6 #10 wall-clock hard cap reached: {elapsed_min:.1f} min ≥ {BULK_HARD_CAP_MIN}')

    # 2h canary
    if elapsed_min >= CANARY_AT_MIN and expected_total > 0:
        pct = 100.0 * processed_count / expected_total
        if pct < CANARY_MIN_COMPLETION_PCT:
            raise HaltError(f'2h canary tripped: {pct:.1f}% completion < {CANARY_MIN_COMPLETION_PCT}% at {elapsed_min:.1f} min')

    # Storage soft gate
    storage_ok, storage_msg = check_storage_gates(manifest)
    if not storage_ok:
        raise HaltError(f'storage gate halt: {storage_msg}')


def write_progress(progress_path: Path, processed_count: int, expected_total: int,
                   in_flight_grantee: str | None, last_completed_fcc_id: str | None,
                   start_ts: float, manifest: dict, deferred_queue_depth: int):
    elapsed_min = (time.time() - start_ts) / 60.0
    storage_gb = disk_usage_gb(RAW_FCCID) + disk_usage_gb(RAW_FCC_EAS)
    payload = {
        'updated_at_utc': utc_now(),
        'processed_count': processed_count,
        'expected_total': expected_total,
        'completion_pct': (100.0 * processed_count / expected_total) if expected_total > 0 else None,
        'in_flight_grantee': in_flight_grantee,
        'last_completed_fcc_id': last_completed_fcc_id,
        'current_storage_gb': round(storage_gb, 4),
        'storage_soft_gb': manifest['storage_gate']['soft_gb'],
        'storage_hard_gb': manifest['storage_gate']['hard_gb'],
        'elapsed_wall_clock_min': round(elapsed_min, 2),
        'bulk_hard_cap_min': BULK_HARD_CAP_MIN,
        'canary_at_min': CANARY_AT_MIN,
        'canary_min_completion_pct': CANARY_MIN_COMPLETION_PCT,
        'deferred_queue_depth': deferred_queue_depth,
    }
    progress_path.write_text(json.dumps(payload, indent=2))


def write_stop_the_line(reason: str, processed_count: int, expected_total: int,
                        in_flight_grantee: str | None, last_completed_fcc_id: str | None,
                        deferred_queue: list):
    path = WORK_DIR / 'BULK_STOP_THE_LINE.md'
    body = f"""# MAC-101 BULK RUN — STOP THE LINE

**Reason:** {reason}
**Detected at:** {utc_now()}
**Processed:** {processed_count} / {expected_total} ({100.0 * processed_count / expected_total if expected_total else 0:.1f}%)
**In-flight grantee:** {in_flight_grantee!r}
**Last completed FCC ID:** {last_completed_fcc_id!r}
**Deferred queue depth:** {len(deferred_queue)}

State preserved on disk for resume:
- progress.json — latest checkpoint
- fcc_citation_deferred_queue.json — cumulative queue (all entries persist)
- raw/fccid_io/ — all fetched HTML + attachments + sha256s
- bulk_run.log — full request log

CC idle. Awaiting CEO disposition for resume vs partial-deliverable.
"""
    path.write_text(body)


# ============================================================
# Bulk run driver
# ============================================================

def process_one_filing(session: requests.Session, filing: dict, manifest: dict,
                       deferred_queue: list, borderline_log: list,
                       provisional_id_counter: list) -> dict:
    """Run §3.2 → §3.3 → §3.4.1 for one FCC ID. Returns status dict."""
    fcc_id = filing['fcc_id']

    # §3.1 enumeration-time borderline skip
    if is_borderline_for_skip(filing.get('description_excerpt', '')):
        borderline_log.append({'fcc_id': fcc_id, 'description': filing.get('description_excerpt'),
                               'reason': 'consumer_electronics_pattern_match'})
        return {'fcc_id': fcc_id, 'skipped': 'borderline_consumer_electronics'}

    # §3.2
    am = enumerate_filing_attachments(session, fcc_id)
    if am['http_code'] != 200:
        return {'fcc_id': fcc_id, 'skipped': f'filing_page_http_{am["http_code"]}'}

    # §6 #3 attachment-count surface — if a single FCC ID has > 10 attachments matching priority filter, halt
    if len(am['attachments']) > PER_FCC_ID_ATTACHMENT_HALT:
        logging.warning(f'§3.3 high attachment count {len(am["attachments"])} for {fcc_id} — may be chipset re-cert')
        # Surface but don't halt unilaterally; let CEO surface_at_handoff catch
        am['high_attachment_count_flag'] = True

    # §6 #8 PII scan on fccid.io HTML
    fccid_html_path = RAW_FCCID / fcc_id / 'index.html'
    fccid_html = fccid_html_path.read_bytes()
    pii_hits = scan_for_pii(fccid_html.decode('utf-8', errors='ignore'), context=f'fccid_io_html:{fcc_id}')
    if pii_hits:
        append_pii_finding(pii_hits)
        raise HaltError(f'§6 #8 PII surfaced on fccid.io HTML for {fcc_id}: {len(pii_hits)} hit(s); see pii_surface_audit.json')

    # §3.3 — fetch attachments up to per-FCC-ID cap
    fetched_count = 0
    for att in am['attachments'][:PER_FCC_ID_DOWNLOAD_CAP]:
        rec = fetch_attachment(session, fcc_id, att)
        if 'sha256' in rec:
            fetched_count += 1

    # §3.4.1 — queue
    fccid_html_sha256 = sha256_bytes(fccid_html)
    fccid_io_source_url = f'https://fccid.io/{fcc_id}'
    provisional_id = provisional_id_counter[0]
    provisional_id_counter[0] += 1

    branch_result = handle_fcc_gov_branch(
        session, fcc_id, fccid_io_source_url, fccid_html, fccid_html_sha256,
        manifest, deferred_queue, [provisional_id],
    )

    # Per-FCC-ID provenance file
    prov_path = WORK_DIR / 'per_fcc_id' / fcc_id / 'section_3_provenance.json'
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    prov_path.write_text(json.dumps({
        'fcc_id': fcc_id,
        'grantee_code': filing.get('grantee_code'),
        'product_code': filing.get('product_code'),
        'fccid_io_source_url': fccid_io_source_url,
        'fccid_io_html_sha256': fccid_html_sha256,
        'attachments_fetched': fetched_count,
        'attachments_total_priority': len(am['attachments']),
        'view_on_fcc_link_present': am['view_on_fcc_link'] is not None,
        'opportunistic_enrichment_grant_ids': branch_result.get('fcc_grant_ids', []),
        'processed_at_utc': utc_now(),
    }, indent=2))

    return {'fcc_id': fcc_id, 'fetched': fetched_count, 'attachments_total': len(am['attachments']),
            'enrichment_present': branch_result.get('enrichment_present', False)}


def run_bulk():
    """Bulk dispatch: Stream A (48 codes) + Stream B (14 vendors). Halt-criteria per runguide §6."""
    setup_logging(smoke_test=False)
    start_ts = time.time()
    logging.info('=== BULK RUN start (PC1.7 Step 6) ===')

    manifest = load_manifest()
    manifest['bulk_run_started_at_utc'] = utc_now()
    save_manifest(manifest)

    session = requests.Session()

    progress_path = WORK_DIR / 'progress.json'
    deferred_queue: list = []
    borderline_log: list = []
    provisional_id_counter = [10000]  # placeholder IDs; validator re-IDs at promotion
    all_filings: list = []
    last_completed_fcc_id: str | None = None
    in_flight_grantee: str | None = None
    processed_count = 0
    expected_total = 0  # known after enumeration

    try:
        # ============================================================
        # Phase 1: Stream A grantee enumeration → FCC ID collection
        # ============================================================
        stream_a_codes = load_stream_a_targets()
        logging.info(f'Phase 1: Stream A enumeration ({len(stream_a_codes)} grantees)')
        for gc in stream_a_codes:
            in_flight_grantee = gc
            check_halt_criteria(start_ts, manifest, processed_count, expected_total, deferred_queue, progress_path)
            filings = enumerate_grantee_filings(session, gc)
            all_filings.extend(filings)
            logging.info(f'  Stream A {gc}: +{len(filings)} FCC IDs (cumulative {len(all_filings)})')

        # ============================================================
        # Phase 2: Stream B grantee-name search → grantee codes → FCC IDs
        # ============================================================
        stream_b_grantees_resolved: list[str] = []
        stream_b_documented_absences: list[str] = []
        stream_b_oversize_halts: list[tuple[str, int]] = []
        logging.info(f'Phase 2: Stream B fan-out ({len(STREAM_B_VENDORS)} vendors)')
        for vendor in STREAM_B_VENDORS:
            in_flight_grantee = f'stream_b:{vendor}'
            check_halt_criteria(start_ts, manifest, processed_count, expected_total, deferred_queue, progress_path)
            codes = search_fccid_grantee_name(session, vendor)
            if not codes:
                stream_b_documented_absences.append(vendor)
                continue
            if len(codes) > STREAM_B_PER_VENDOR_HALT:
                logging.warning(f'  Stream B {vendor}: {len(codes)} > {STREAM_B_PER_VENDOR_HALT} '
                                f'— skipping per §2.7.1 (defensive: needs disambig before include)')
                stream_b_oversize_halts.append((vendor, len(codes)))
                continue
            stream_b_grantees_resolved.extend(codes)
        # Dedupe Stream B codes (some vendors may share grantees with Stream A)
        stream_a_set = set(stream_a_codes)
        stream_b_unique = [c for c in stream_b_grantees_resolved if c not in stream_a_set]
        seen_b = set()
        stream_b_unique = [c for c in stream_b_unique if not (c in seen_b or seen_b.add(c))]
        logging.info(f'  Stream B resolved: {len(stream_b_grantees_resolved)} raw → {len(stream_b_unique)} unique '
                     f'(excluding Stream A overlap)')

        for gc in stream_b_unique:
            in_flight_grantee = gc
            check_halt_criteria(start_ts, manifest, processed_count, expected_total, deferred_queue, progress_path)
            filings = enumerate_grantee_filings(session, gc)
            all_filings.extend(filings)
            logging.info(f'  Stream B {gc}: +{len(filings)} FCC IDs (cumulative {len(all_filings)})')

        # Deduplicate filings by fcc_id (some grantee enumerations can collide)
        seen_fcc = set()
        deduped_filings = []
        for f in all_filings:
            if f['fcc_id'] in seen_fcc:
                continue
            seen_fcc.add(f['fcc_id'])
            deduped_filings.append(f)
        all_filings = deduped_filings
        expected_total = len(all_filings)
        logging.info(f'Phase 1+2 complete: {expected_total} unique FCC IDs in scope')

        write_progress(progress_path, processed_count, expected_total, in_flight_grantee,
                       last_completed_fcc_id, start_ts, manifest, len(deferred_queue))

        # ============================================================
        # Phase 3: per-FCC-ID §3.2 → §3.3 → §3.4.1 loop
        # ============================================================
        logging.info(f'Phase 3: per-FCC-ID processing (target {expected_total})')
        for filing in all_filings:
            in_flight_grantee = filing.get('grantee_code')
            check_halt_criteria(start_ts, manifest, processed_count, expected_total, deferred_queue, progress_path)

            try:
                result = process_one_filing(session, filing, manifest, deferred_queue,
                                            borderline_log, provisional_id_counter)
                if 'skipped' not in result:
                    last_completed_fcc_id = filing['fcc_id']
                processed_count += 1
            except HaltError:
                raise
            except Exception as e:
                logging.error(f'  process error for {filing["fcc_id"]}: {e}; continuing')
                processed_count += 1
                continue

            # Periodic queue persist + progress checkpoint
            if processed_count % PROGRESS_CHECKPOINT_EVERY == 0:
                persist_deferred_queue(deferred_queue)
                write_progress(progress_path, processed_count, expected_total,
                               in_flight_grantee, last_completed_fcc_id,
                               start_ts, manifest, len(deferred_queue))
                logging.info(f'  checkpoint @ {processed_count}/{expected_total} '
                             f'({100*processed_count/expected_total:.1f}%) '
                             f'queue_depth={len(deferred_queue)} '
                             f'elapsed={(time.time()-start_ts)/60:.1f}min')

        # ============================================================
        # Phase 4: final persist + handoff stubs
        # ============================================================
        persist_deferred_queue(deferred_queue)
        write_progress(progress_path, processed_count, expected_total, None,
                       last_completed_fcc_id, start_ts, manifest, len(deferred_queue))

        # Borderline log
        if borderline_log:
            (WORK_DIR / 'borderline_fcc_ids.json').write_text(
                json.dumps({'borderline_filings': borderline_log, 'count': len(borderline_log)}, indent=2)
            )

        # Stream B audit
        (WORK_DIR / 'stream_b_audit.json').write_text(json.dumps({
            'documented_absences': stream_b_documented_absences,
            'oversize_halts_deferred_to_disambig': [{'vendor': v, 'count': n} for v, n in stream_b_oversize_halts],
            'resolved_unique_grantees': stream_b_unique,
        }, indent=2))

        elapsed_min = (time.time() - start_ts) / 60.0
        logging.info(f'=== BULK RUN complete: {processed_count}/{expected_total} '
                     f'queue_depth={len(deferred_queue)} elapsed={elapsed_min:.1f}min ===')
        logging.info(f'§3 complete. Halting per kickoff for §3→§4 CEO check-in.')
        return 0

    except HaltError as halt:
        elapsed_min = (time.time() - start_ts) / 60.0
        logging.error(f'BULK RUN HALT at {elapsed_min:.1f}min: {halt}')
        persist_deferred_queue(deferred_queue)
        write_progress(progress_path, processed_count, expected_total, in_flight_grantee,
                       last_completed_fcc_id, start_ts, manifest, len(deferred_queue))
        write_stop_the_line(str(halt), processed_count, expected_total,
                            in_flight_grantee, last_completed_fcc_id, deferred_queue)
        return 4

    except KeyboardInterrupt:
        logging.error('BULK RUN interrupted (KeyboardInterrupt); preserving state')
        persist_deferred_queue(deferred_queue)
        write_progress(progress_path, processed_count, expected_total, in_flight_grantee,
                       last_completed_fcc_id, start_ts, manifest, len(deferred_queue))
        write_stop_the_line('KeyboardInterrupt', processed_count, expected_total,
                            in_flight_grantee, last_completed_fcc_id, deferred_queue)
        return 5

    except Exception as e:
        # PC1.8.A: catch-all to preserve state on unhandled crashes (e.g. uncaught network
        # exception that bypassed polite_get retry chain). Without this, the script dies
        # with traceback and the operator never gets a BULK_STOP_THE_LINE.md.
        elapsed_min = (time.time() - start_ts) / 60.0
        reason = f'unhandled {type(e).__name__}: {e}'
        logging.exception(f'BULK RUN unhandled exception at {elapsed_min:.1f}min: {reason}')
        try:
            persist_deferred_queue(deferred_queue)
            write_progress(progress_path, processed_count, expected_total, in_flight_grantee,
                           last_completed_fcc_id, start_ts, manifest, len(deferred_queue))
            write_stop_the_line(reason, processed_count, expected_total,
                                in_flight_grantee, last_completed_fcc_id, deferred_queue)
        except Exception as inner:
            logging.error(f'state-preservation also failed: {type(inner).__name__}: {inner}')
        return 6


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
