"""Canonical ``manufacturers.aliases`` parser — MAC-569 / MAC-535 §6.2 tokenization.

The ``manufacturers.aliases`` column stores a comma-separated list of vendor
alias strings. As of MAC-569 the canonical wire format is **RFC-4180-lite**:
alias values that themselves contain a comma are wrapped in double quotes;
plain alias values are bare. Pre-MAC-569 data was unquoted and contains
bare comma-bearing values that produce phantom tokens when naively split on
",". The migration ``db/migrations/0043_mac569_alias_rfc4180_quote_normalize.sql``
re-encodes every affected row to the quoted form; this module is the canonical
parser every consumer SHOULD use instead of splitting on "," directly.

Storage discipline (canonical reference):
    ``manufacturers.aliases``  ::=  ``alias ("," alias)*``     ; bare form, no commas in values
                              |    ``alias ("," alias)*``     ; quoted form, "..." allowed in values
    ``alias``                 ::=  ``DQUOTE *<no-DQUOTE> DQUOTE``   ; quoted variant
                              |    ``*<no-comma>``                 ; bare variant (no `,` allowed)
    ``no-DQUOTE``             ::=  any char except ``"``
    ``no-comma``              ::=  any char except ``,``

Whitespace surrounding an alias is stripped on read. Empty / None yields
``[]``. A quoted alias value may legitimately contain a comma, so it is the
escape mechanism for the otherwise-flat comma-separated representation.

Lookup discipline (verbatim from PROJECT_BIBLE.md §4 — vendor match sub-clause):
    ``WHERE aliases LIKE '%term%' OR LOWER(canonical_name) = LOWER(?)``
This still works against the quoted form because the unquoted alias text is a
substring of the quoted form (``"Foo, Inc."`` contains ``Foo, Inc.``).

This module also exposes the MAC-535 §6.2 tokenization defense constants so
consumers that need to drop bogus tokens (e.g. the §6.2 corroboration pass)
can do so without re-importing the private internals of ``coverage_matrix``.
"""

from __future__ import annotations

import re
from typing import Iterable

# MAC-535 §6.2 tokenization defense (Finding 2 of MAC-533 §cto_ratification.md).
# Catalogue copied verbatim; do not edit without a sibling amendment-log entry.
_CORP_SUFFIX_STOPLIST: frozenset[str] = frozenset({
    "ltd", "ltd.", "inc", "inc.", "llc", "co.", "co", "the",
})
_ALIAS_TOKEN_MIN_LEN = 4

# Pattern: a token that is a pure corporate-suffix fragment. Such a token is
# *evidence* that a comma-bearing alias value was stored bare (pre-MAC-569)
# and got split on the internal comma. The migration's recombine step uses
# this to decide whether to merge the fragment with its predecessor.
_FRAGMENT_SUFFIX_PATTERN = re.compile(
    r"^(?:"
    r"Ltd\.?|Inc\.?|Corp\.?|Co\.?|LLC|L\.?P\.?|LP|PTY|GmbH|"
    r"S\.A\.?|S\.r\.l\.?|S\.p\.A\.?|AB|AG|SA|BV|PLC|AS"
    r")$",
    re.IGNORECASE,
)

# Pattern: a token that ends in a corporate-suffix-like word boundary. Used
# in the recombine pass to decide whether the *predecessor* token is the
# left half of a comma-bearing alias that was split.
_TRAILING_CORP_SUFFIX = re.compile(
    r"\b(?:"
    r"Ltd\.?|Inc\.?|Corp\.?|Co\.?|LLC|L\.?P\.?|LP|PTY|GmbH|"
    r"S\.A\.?|S\.r\.l\.?|S\.p\.A\.?|AB|AG|SA|BV|PLC|AS"
    r")\.?\s*$",
    re.IGNORECASE,
)


def split_aliases(aliases_field: str | None) -> list[str]:
    """Parse a ``manufacturers.aliases`` blob into individual alias strings.

    Storage convention (canonical reference, MAC-102 baseline + MAC-569
    RFC-4180-lite refinement): comma-separated. Alias values that contain
    a comma are wrapped in double quotes. Empty / None yields ``[]``.
    Whitespace surrounding each alias is stripped.

    Quoting rules:
      * A ``"`` opens a quoted phrase that ends at the next ``"``.
      * Inside a quoted phrase, ``,`` is literal (not a separator).
      * An unterminated quote is defensive: the rest of the blob is
        treated as one bare token. This is not expected on canonical
        data (the migration guarantees terminated quotes) but the
        parser must not crash on partial input.
    """
    if not aliases_field:
        return []
    out: list[str] = []
    i = 0
    n = len(aliases_field)
    while i < n:
        # Skip inter-token whitespace and commas.
        while i < n and aliases_field[i] in (",", " "):
            i += 1
        if i >= n:
            break
        if aliases_field[i] == '"':
            # Quoted phrase — read until matching close-quote.
            j = aliases_field.find('"', i + 1)
            if j == -1:
                # Unterminated quote — defensive fallback (canonical data
                # never has this shape after MAC-569 normalize).
                out.append(aliases_field[i + 1:].strip())
                break
            out.append(aliases_field[i + 1:j].strip())
            i = j + 1
        else:
            # Bare token — read until next top-level comma.
            j = aliases_field.find(",", i)
            if j == -1:
                out.append(aliases_field[i:].strip())
                break
            out.append(aliases_field[i:j].strip())
            i = j + 1
    return [t for t in out if t]


def is_bogus_token(tok: str) -> bool:
    """Return True iff ``tok`` is a MAC-535 §6.2 bogus token.

    Two independent predicates — drop if either fires:
      1. Length below the min-length floor (catches future short-token
         false positives; "THE"/"L3" are caught here as a defense).
      2. Sits on the corporate-suffix stop-list (case-insensitive,
         verbatim catalogue from ``cto_ratification.md §Finding 2``).
    """
    s = tok.strip()
    if len(s) < _ALIAS_TOKEN_MIN_LEN:
        return True
    return s.lower() in _CORP_SUFFIX_STOPLIST


def filter_bogus_tokens(tokens: Iterable[str]) -> list[str]:
    """Drop MAC-535 §6.2 bogus tokens from an alias-token iterable.

    Convenience wrapper for consumers (e.g. ``coverage_matrix._alias_tokens_for_vendor``)
    that want the layer-2/3 defense without re-implementing the predicate.
    """
    return [t for t in tokens if not is_bogus_token(t)]


def _is_pure_fragment(tok: str) -> bool:
    """Return True iff ``tok`` is a bare corporate-suffix fragment.

    Used by ``recombine_and_quote_normalize`` to decide whether a token
    produced by naive comma-split is the right half of a comma-bearing
    alias value (and should be merged back with its predecessor).
    """
    return bool(_FRAGMENT_SUFFIX_PATTERN.match(tok.strip()))


def _ends_with_corp_suffix(tok: str) -> bool:
    """Return True iff ``tok`` ends in a corporate-suffix-like word boundary.

    Used by ``recombine_and_quote_normalize`` to detect the left half of a
    comma-bearing alias that was split. E.g. ``"Hangzhou ... Digital
    Technology Co."`` returns True; ``"Hangzhou Hikvision Digital
    Technology"`` returns False.
    """
    return bool(_TRAILING_CORP_SUFFIX.search(tok))


def standalone_corp_suffix_tokens(blob: str | None) -> list[str]:
    """Return every smart-parsed token that is a pure corporate suffix."""
    return [token for token in split_aliases(blob) if _is_pure_fragment(token)]


def recombine_and_quote_normalize(blob: str | None) -> tuple[str, int]:
    """Reconstruct the canonical RFC-4180-lite alias blob from raw input.

    Used by the MAC-569 migration to normalize pre-existing bare-comma data
    into the canonical quoted form. Pure function — no DB access.

    Algorithm:
      1. Parse with ``split_aliases`` (quote-aware; handles already-quoted
         input correctly so the migration is safe on partially-migrated DBs).
      2. Walk the parsed tokens. If a token is a pure corporate-suffix
         fragment, merge it back into its immediate predecessor with
         ``", "`` join. Corporate suffixes are never valid standalone aliases;
         cross-vendor pairs remain separate because neither token is a pure
         suffix.
      3. For every resulting string that contains a comma, wrap it in
         double quotes. This is the "quote normalize" pass — it brings
         the blob into the canonical RFC-4180-lite form so future
         consumers see exactly one token per alias.

    Returns:
        ``(new_blob, phantom_count)`` where ``phantom_count`` is the
        number of fragment tokens that were merged back (i.e., the count
        of phantom tokens removed from the blob).
    """
    if not blob:
        return ("", 0)
    tokens = split_aliases(blob)
    merged: list[str] = []
    phantom_count = 0
    for tok in tokens:
        if merged and _is_pure_fragment(tok):
            merged[-1] = merged[-1] + ", " + tok.strip()
            phantom_count += 1
        else:
            merged.append(tok)
    encoded: list[str] = []
    for s in merged:
        if "," in s:
            encoded.append(f'"{s}"')
        else:
            encoded.append(s)
    return (", ".join(encoded), phantom_count)


# Public re-exports for callers that prefer module-level access.
CORP_SUFFIX_STOPLIST = _CORP_SUFFIX_STOPLIST
ALIAS_TOKEN_MIN_LEN = _ALIAS_TOKEN_MIN_LEN
FRAGMENT_SUFFIX_PATTERN = _FRAGMENT_SUFFIX_PATTERN
TRAILING_CORP_SUFFIX = _TRAILING_CORP_SUFFIX
