"""Entity-boundary matching — the single implementation.

MAC-585. The MAC-542 re-match established that bare containment
(``LIKE '%token%'``) is not a vendor-name match: it fires on ``DJI`` inside
``DJIBOUTI``, ``ALPR`` inside ``ALPRAZOLAM``, ``AXON`` inside ``FAXON``,
``MAGNET`` inside ``MAGNETIKA``. Three separate call sites have now been found
carrying that defect, each with its own private matcher. This module exists so
there is exactly one, on the ``db/alias_parser.py`` single-parser precedent
(MAC-569).

The predicate is transcribed verbatim from the MAC-542 reference
implementation, ``operator_review/MAC-542/rematch.py:26-40`` at HEAD
``8e905cf``::

    TOKEN_RE = re.compile(r"[^A-Z0-9]+")

    def toks(s):
        if not s:
            return []
        return TOKEN_RE.sub(" ", s.upper()).split()

    def contiguous(needle, hay):
        n, h = len(needle), len(hay)
        if n == 0 or n > h:
            return False
        for i in range(h - n + 1):
            if hay[i:i + n] == needle:
                return True
        return False

Semantics: uppercase, split on any run of non-alphanumerics, then require the
needle's token sequence to appear as a *contiguous* run of whole tokens in the
haystack. This is strictly stronger than a ``\\b...\\b`` regex for multi-word
needles, because ``\\b`` would let ``Flock Safety`` match across an intervening
token, and it is equivalent to ``\\b`` for single-token needles.

WHAT THIS PREDICATE DOES NOT DO
-------------------------------
Boundary is necessary but not sufficient. A short single-token vendor name
(``Axis``, ``Flock``, ``Harris``, ``Jacobs``, ``Parrot``, ``DRT``) boundary-
matches surnames, county names and ordinary English usage exactly as often as
it matches the vendor. Callers that gate a promotion or ship rows MUST also
apply the MAC-542 §5 short-single-token (T2) screen — see
``is_short_single_token`` below — and adjudicate those clusters. Substituting
this module for that adjudication reintroduces the defect one layer up.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Iterable, Optional, Sequence

# Verbatim from operator_review/MAC-542/rematch.py:26.
TOKEN_RE = re.compile(r"[^A-Z0-9]+")

# MAC-542 §5: "a short single-token FP-magnet candidate".
# Verbatim from operator_review/MAC-542/t2_select.py: SHORT_MAX_LEN = 6.
SHORT_MAX_LEN = 6


def tokenize(value: Optional[str]) -> list[str]:
    """Uppercase and split on runs of non-alphanumerics (MAC-542 ``toks``)."""
    if not value:
        return []
    return TOKEN_RE.sub(" ", value.upper()).split()


def contiguous(needle: Sequence[str], haystack: Sequence[str]) -> bool:
    """True if ``needle`` appears as a contiguous token run in ``haystack``."""
    n, h = len(needle), len(haystack)
    if n == 0 or n > h:
        return False
    for i in range(h - n + 1):
        if list(haystack[i : i + n]) == list(needle):
            return True
    return False


def boundary_match(token: str, text: Optional[str]) -> bool:
    """True if ``token`` entity-boundary-matches ``text``."""
    return contiguous(tokenize(token), tokenize(text))


def any_boundary_match(tokens: Iterable[str], text: Optional[str]) -> bool:
    """True if ANY of ``tokens`` entity-boundary-matches ``text`` (OR-semantics)."""
    hay = tokenize(text)
    return any(contiguous(tokenize(t), hay) for t in tokens)


def is_short_single_token(token: str) -> bool:
    """MAC-542 §5 T2 screen: a short, single-token FP-magnet candidate.

    Applied to the RAW token as stored (``Axis``, ``Flock``), matching
    ``operator_review/MAC-542/t2_select.py::is_short``.
    """
    return len(token) <= SHORT_MAX_LEN and " " not in token


class BoundaryCorpus:
    """A ``(table, column)`` corpus indexed for entity-boundary counting.

    Bare ``LIKE '%t%'`` can be pushed into SQLite; the boundary predicate
    cannot, so the corpus is tokenized once and served from an inverted index.
    Distinct values are indexed with their row frequency, so ``count`` returns
    a ROW count identical in shape to the ``COUNT(*)`` it replaces (each row
    counted at most once regardless of how many tokens hit it).

    NULL column values tokenize to ``[]`` and therefore never match, which
    preserves the SQL semantics of ``NULL LIKE '%t%'`` -> NULL -> not counted.
    """

    __slots__ = ("table", "column", "_freq", "_tokens", "_postings")

    def __init__(self, conn: sqlite3.Connection, table: str, column: str) -> None:
        self.table = table
        self.column = column
        self._freq: list[int] = []
        self._tokens: list[list[str]] = []
        # First-token -> value indices. Candidates are then verified with the
        # full contiguous check, so the index is a filter, never the predicate.
        self._postings: dict[str, set[int]] = {}
        cur = conn.execute(
            f"SELECT {column} AS v, COUNT(*) AS n FROM {table} GROUP BY {column}"
        )
        for value, n in cur.fetchall():
            toks = tokenize(value)
            if not toks:
                continue
            idx = len(self._freq)
            self._freq.append(n)
            self._tokens.append(toks)
            for tok in set(toks):
                self._postings.setdefault(tok, set()).add(idx)

    def count(self, tokens: list[str]) -> int:
        """Rows where ANY of ``tokens`` entity-boundary-matches the column."""
        if not tokens:
            return 0
        hits: set[int] = set()
        for tok in tokens:
            needle = tokenize(tok)
            if not needle:
                continue
            for idx in self._postings.get(needle[0], ()):
                if idx not in hits and contiguous(needle, self._tokens[idx]):
                    hits.add(idx)
        return sum(self._freq[i] for i in hits)
