"""Vendor-name normalization for procurement_records.vendor_canonical_normalized.

Deterministic alias-collapse key per CP23 §-procurement_records contract
(BIBLE_AMENDMENTS.md CP23; migration 0021_procurement_vendor_canonical_normalized).

The function is pure: callable from migration backfill, validator
cross-validation, and tests without DB state. The algorithm prose lives in
DATA_DICTIONARY.md §-procurement_records (downstream-consumer audit
reference).
"""

from __future__ import annotations

import re

# Suffix tokens stripped at end-of-string (whole-word; matched after the
# punctuation strip so leading commas are already gone). Order does not
# affect the result because the matcher iterates until no terminal suffix
# remains.
SUFFIX_TOKENS: tuple[str, ...] = (
    "incorporated",
    "corporation",
    "company",
    "limited",
    "gmbh",
    "llc",
    "l l c",
    "ltd",
    "plc",
    "inc",
    "corp",
    "co",
    "lp",
    "llp",
    "ag",
    "sa",
    "pty",
    "bv",
)

_PUNCTUATION = re.compile(r"[.,;:'\"()\[\]{}/\\`~!@#$%^&*+=|<>?]")
_WHITESPACE = re.compile(r"\s+")
_SUFFIX_BOUNDARY = re.compile(r"(?<=\s)")


def normalize_vendor_name(value: str | None) -> str:
    """Return the deterministic alias-collapse key for a vendor name.

    Steps applied in order (CP23 §-procurement_records contract):
      1. LOWER()
      2. Strip all punctuation in {. , ; : ' " ( ) [ ] { } / \\ ` ~ ! @ # $ % ^ & * + = | < > ?}
      3. Collapse runs of whitespace to a single space
      4. Strip leading/trailing whitespace
      5. Repeatedly strip trailing whole-word suffix tokens
      6. Re-strip whitespace
      7. Empty result returns '' (column is NOT NULL DEFAULT '')

    NULL / empty input returns ''.
    """
    if not value:
        return ""

    s = value.lower()
    s = _PUNCTUATION.sub(" ", s)
    s = _WHITESPACE.sub(" ", s).strip()

    while True:
        stripped = _strip_terminal_suffix(s)
        if stripped == s:
            break
        s = stripped

    return _WHITESPACE.sub(" ", s).strip()


def _strip_terminal_suffix(s: str) -> str:
    for token in SUFFIX_TOKENS:
        if s == token:
            return ""
        suffix = " " + token
        if s.endswith(suffix):
            return s[: -len(suffix)].rstrip()
    return s
