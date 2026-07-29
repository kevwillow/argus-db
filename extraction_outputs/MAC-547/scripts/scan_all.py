"""MAC-547 / MAC-550 — comprehensive scan over all raw files in extraction_outputs/MAC-547/raw/.

Outputs candidates.jsonl with cite-paste verbatim quotes.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from io import BytesIO
from pathlib import Path

REPO_ROOT = Path("/home/kev/argus")
OUT_ROOT = REPO_ROOT / "extraction_outputs" / "MAC-547"
RAW_DIR = OUT_ROOT / "raw"
DB_PATH = REPO_ROOT / "db" / "argus.db"

DEVICE_CATEGORY_BY_SLUG = {
    "rekor": "alpr",
    "ekin": "alpr",
    "fusus": "network_surveillance",
    "wolfcom": "body_cam",
}

VENDOR_DISPLAY = {
    "rekor": "Rekor",
    "ekin": "Ekin",
    "fusus": "Fusus (Axon-owned)",
    "wolfcom": "Wolfcom",
}

# Pattern catalog (conservative)
RE_SSID_KW = re.compile(
    r"(?i)\b(?:default\s+ssid|ssid\s+is|ssid\s*[:=]|network\s+name\s*[:=]|"
    r"wireless\s+network\s+name|wifi\s+network\s+name|wi-fi\s+network\s+name|"
    r"wi-fi\s+name|wifi\s+name|access\s+point\s+name|hotspot\s+name|"
    r"default\s+wi-fi\s+name|default\s+wireless\s+name)\b"
)

RE_SSID_VALUE = re.compile(
    r"""(?ix)
    (?:default\s+)?(?:wifi|wi-fi|wireless|network|hotspot|access\s+point|ssid)
    (?:\s+(?:network|ssid|name))?
    \s*(?:is|:|=)
    \s*[\"'`]?
    (?P<v>[A-Za-z0-9][A-Za-z0-9 _\-\.]{1,40})
    [\"'`]?
    """
)

RE_BLE_KW = re.compile(
    r"(?i)\b(?:ble\s+name|bluetooth\s+(?:device\s+)?name|ble\s+device\s+name|"
    r"advertised\s+(?:device\s+)?name|complete\s+local\s+name|gap\s+device\s+name|"
    r"bluetooth\s+advertis(?:e|ing)\s+name|bluetooth\s+device\s+local\s+name)\b"
)

RE_BLE_VALUE = re.compile(
    r"""(?ix)
    (?:ble|bluetooth|advertised|complete\s+local|gap)
    (?:\s+device)?
    (?:\s+local)?
    \s+(?:name|device\s+name)
    \s*[:=]
    \s*[\"'`]?
    (?P<v>[A-Za-z0-9][A-Za-z0-9 _\-\.]{1,40})
    [\"'`]?
    """
)

RE_BLE_VERB = re.compile(
    r"""(?ix)
    (?:advertise|advertises|advertising|broadcast|broadcasts|broadcasting)
    \s+(?:as|with)
    \s+[\"'`]?
    (?P<v>[A-Za-z0-9][A-Za-z0-9 _\-\.]{1,40})
    [\"'`]?
    """
)

# Backtick-style code references: "`Foo` SSID", "`Bar` Bluetooth Name"
RE_CODE_SSID = re.compile(
    r"`(?P<v>[A-Za-z0-9][A-Za-z0-9 _\-\.]{1,40})`\s*(?:ssid|wifi|wireless)",
    flags=re.IGNORECASE,
)
RE_CODE_BLE = re.compile(
    r"`(?P<v>[A-Za-z0-9][A-Za-z0-9 _\-\.]{1,40})`\s*(?:ble|bluetooth|advertised)",
    flags=re.IGNORECASE,
)

TEMPLATE_CHARS = "[]()?*+|<>%"
TEMPLATE_CHAR_RE = re.compile("[" + re.escape(TEMPLATE_CHARS) + "]")


def is_template(v: str) -> bool:
    return bool(TEMPLATE_CHAR_RE.search(v))


# SAR-5 PII redaction (vendor-doc shape — corporate engineering / installer names)
PII_RANK_TOKENS = (
    "Officer", "Sergeant", "Sgt", "Lieutenant", "Lt", "Captain", "Capt",
    "Major", "Colonel", "Col", "Chief", "Sheriff", "Deputy", "Detective",
    "Engineer", "Installer", "Technician", "Manager", "Director", "VP",
    "President", "CEO", "CTO", "Sales", "Representative", "Rep",
    "Contact", "Author", "Maintainer",
)
PII_REGEX = re.compile(
    r"\b(" + "|".join(PII_RANK_TOKENS) + r")\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"
)
PII_MARKER = "[REDACTED-PERSON]"


def redact_pii(text: str) -> tuple[str, int]:
    hits = 0

    def _sub(_m):
        nonlocal hits
        hits += 1
        return PII_MARKER

    return PII_REGEX.sub(_sub, text), hits


def cite_paste(text: str, start: int, end: int, *, width: int = 200) -> str:
    span_len = end - start
    if span_len > width:
        excerpt = text[start:end]
    else:
        half = (width - span_len) // 2
        s = max(0, start - half)
        e = min(len(text), end + (width - span_len - (start - s)))
        excerpt = text[s:e]
    return re.sub(r"\s+", " ", excerpt).strip()


# ─── DB-dedupe helpers (read-only) ─────────────────────────────────────────


def existing_identifiers() -> dict[str, list[dict]]:
    """Return {identifier_value: [row, …]} for ssid_exact and ble_local_name types."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute(
        "SELECT identifier, identifier_type, manufacturer, device_category, confidence "
        "FROM identifiers WHERE superseded_by IS NULL "
        "AND identifier_type IN ('ssid_exact', 'ble_local_name')"
    )
    rows = cur.fetchall()
    conn.close()
    out: dict[str, list[dict]] = {}
    for ident, itype, manuf, cat, conf in rows:
        out.setdefault(ident.lower(), []).append({
            "identifier": ident, "identifier_type": itype,
            "manufacturer": manuf, "device_category": cat, "confidence": conf,
        })
    return out


# ─── Text extraction ───────────────────────────────────────────────────────


def extract_text_from_bytes(body: bytes, raw_path: Path) -> str:
    if raw_path.suffix == ".pdf" or "pdf" in raw_path.name:
        try:
            from pdfminer.high_level import extract_text
            return extract_text(BytesIO(body)) or ""
        except Exception:
            return ""
    # Markdown or text
    if raw_path.name.endswith(".md.bin") or raw_path.name.endswith(".txt.bin"):
        return body.decode("utf-8", "replace")
    # HTML
    from bs4 import BeautifulSoup
    return BeautifulSoup(body, "html.parser").get_text(" ", strip=True)


# ─── Scan logic ────────────────────────────────────────────────────────────


def scan_file(raw_path: Path) -> list[dict]:
    body = raw_path.read_bytes()
    text = extract_text_from_bytes(body, raw_path)
    if not text:
        return []
    # Slug is parent directory name
    slug = raw_path.parent.name
    if slug not in DEVICE_CATEGORY_BY_SLUG:
        return []
    out: list[dict] = []
    seen_in_file: set[tuple[str, int]] = set()
    # Map raw_path back to source URL (best-effort from filename).
    # Filename looks like https_docs.rekor.ai_path_to_page.bin
    fname = raw_path.name
    if fname.startswith("https_"):
        source_url = "https://" + fname[len("https_"):].rsplit(".", 1)[0].replace("_", "/")
    elif fname.startswith("http_"):
        source_url = "http://" + fname[len("http_"):].rsplit(".", 1)[0].replace("_", "/")
    else:
        source_url = "unknown://" + fname

    def emit(kind: str, m: re.Match, ident: str) -> None:
        key = (kind, m.start())
        if key in seen_in_file:
            return
        seen_in_file.add(key)
        cite = cite_paste(text, m.start("v"), m.end("v"))
        cite_red, pii_hits = redact_pii(cite)
        template = is_template(ident)
        identifier_type = "ssid_exact" if kind.startswith("ssid") else "ble_local_name"
        out.append({
            "vendor": VENDOR_DISPLAY[slug],
            "slug": slug,
            "product": "unknown",
            "identifier": ident,
            "identifier_type": identifier_type,
            "device_category": DEVICE_CATEGORY_BY_SLUG[slug],
            "device_category_justification": (
                f"Vendor's product line is {DEVICE_CATEGORY_BY_SLUG[slug]} per MAC-547 table; "
                f"cite-paste below should justify further"
            ),
            "source_url": source_url,
            "source_type": "manufacturer_doc",
            "doc_title": "",
            "page": None,
            "cite_paste": cite_red,
            "is_template": template,
            "already_in_db": False,
            "confidence_proposed": 0,
            "confidence_rationale": "",
            "match_kind": kind,
            "pii_hits": pii_hits,
        })

    # SSID patterns: RE_SSID_VALUE needs a keyword in match itself; it's
    # self-anchoring (the kw + value are in the same regex).
    for m in RE_SSID_VALUE.finditer(text):
        ident = m.group("v").strip()
        if 3 <= len(ident) <= 40:
            emit("ssid_kw_anchored", m, ident)
    # BLE patterns: same self-anchoring
    for m in RE_BLE_VALUE.finditer(text):
        ident = m.group("v").strip()
        if 3 <= len(ident) <= 40:
            emit("ble_kw_anchored", m, ident)
    # "Advertise as X" / "broadcasts as X" requires the verb in the pattern
    for m in RE_BLE_VERB.finditer(text):
        ident = m.group("v").strip()
        if 3 <= len(ident) <= 40:
            # Require a BLE keyword nearby (within 200 chars back).
            window = text[max(0, m.start() - 200):m.start()]
            if RE_BLE_KW.search(window) or re.search(r"bluetooth|ble", window, re.IGNORECASE):
                emit("ble_verb_anchored", m, ident)
    # Backtick code references
    for m in RE_CODE_SSID.finditer(text):
        ident = m.group("v").strip()
        if 3 <= len(ident) <= 40:
            emit("ssid_backtick", m, ident)
    for m in RE_CODE_BLE.finditer(text):
        ident = m.group("v").strip()
        if 3 <= len(ident) <= 40:
            emit("ble_backtick", m, ident)

    return out


# ─── Main ──────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    raw_files = sorted(RAW_DIR.rglob("*.bin"))
    print(f"Scanning {len(raw_files)} raw files…", file=sys.stderr)
    all_cands: list[dict] = []
    for raw in raw_files:
        cands = scan_file(raw)
        if cands:
            print(f"  {raw.relative_to(REPO_ROOT)}: {len(cands)} candidates", file=sys.stderr)
        all_cands.extend(cands)
    # Dedupe against existing DB rows.
    existing = existing_identifiers()
    for c in all_cands:
        existing_rows = existing.get(c["identifier"].lower(), [])
        c["already_in_db"] = bool(existing_rows)
        if existing_rows:
            ex = existing_rows[0]
            c["already_in_db_note"] = (
                f"matches existing row: {ex['identifier_type']} '{ex['identifier']}' "
                f"({ex['manufacturer']}, {ex['device_category']}, conf={ex['confidence']})"
            )
    # Save raw candidate list for review.
    (OUT_ROOT / "candidates_raw.json").write_text(json.dumps(all_cands, indent=2))
    print(f"\nTotal candidates: {len(all_cands)}", file=sys.stderr)
    # Distribution
    from collections import Counter
    by_vendor = Counter(c["vendor"] for c in all_cands)
    by_type = Counter(c["identifier_type"] for c in all_cands)
    template_count = sum(1 for c in all_cands if c["is_template"])
    db_hits = sum(1 for c in all_cands if c["already_in_db"])
    print(f"  By vendor: {dict(by_vendor)}", file=sys.stderr)
    print(f"  By type:   {dict(by_type)}", file=sys.stderr)
    print(f"  Templates: {template_count}", file=sys.stderr)
    print(f"  DB hits:   {db_hits}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))