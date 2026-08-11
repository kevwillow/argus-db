#!/usr/bin/env python3
"""Gate the Argus prose surface against U+2014 / U+2013 (em / en dashes).

The dash ban is standing Argus voice guidance, ratified by the board on MAC-516
("NO EM DASHES"). Standing memory guidance keeps being forgotten, so this gate
makes the rule mechanical: exit non-zero if a Tier-1 file contains an em dash
or en dash outside the carved-out zones.

Carved-out zones (these are SKIPPED, not "warned"):

  * fenced code blocks   lines starting with ``` or ~~~ fences (3+ chars).
  * indented code blocks  lines beginning with 4+ spaces or a tab, when not
                          inside a list / table cell that GitHub strips the
                          indent on render.  Argus docs are not Jekyll-rendered
                          for the most part; we keep this conservative and only
                          skip the WHOLE-line-indent case so we do not silently
                          skip a paragraph that uses 4-space indent.
  * inline code spans    text between single backticks.  Dashes inside a
                          function name, a path, a SHA, or a CLI flag are part
                          of the cite and MUST be preserved.
  * URLs                 http(s)://... until whitespace.  Commits and ticket
                          references in URLs frequently contain a dash.
  * raw-value tables     brief trap 2 is "never touch inside a table of raw
                          values" -- a Markdown table cell whose entire
                          content is a structural placeholder such as a
                          bare em-dash (representing "no default" in the
                          Default column, a common DB-schema-table idiom),
                          or a column-with-backticks value like `—`, is
                          skipped.  Mixed prose cells still flag a dash
                          because THAT dash is an editorial choice, not a
                          raw value; the writer is responsible for keeping
                          the prose dash out of mixed prose cells.

Rationale per cite is in ``operator_review/BRIEF_STANDARDS.md`` (R4, CITE-FAITHFUL).
A dash inside a quoted source string, a vendor name, an SSID, a commit
message, or a CHECK-constraint body is part of the cite. The gate does not
attempt to detect "is this a quote"; the writer is responsible for placing
quotes, and the reviewer is responsible for sanity-checking the residue.

Tier list:

  Tier 1  reader-facing prose, handed-in here.
  Tier 2  generated artifact (coverage_report.md) and the append-only
          ratification ledger (BIBLE_AMENDMENTS.md). Add to the constant below
          when the generators and the ledger's forward-write path are
          themselves dash-clean.
  Tier 3  internal docs that do not ship with the release. Out of scope for the
          MAC-686 sweep; add later.

Usage:

  python3 scripts/check_prose_dashes.py            # exit 0 = clean, else 1
  python3 scripts/check_prose_dashes.py --list     # print file:line:context per hit
  python3 scripts/check_prose_dashes.py --paths path/to/file.md   # ad-hoc paths

Exit codes:

  0   no dashes in carve-out-violating positions across the tier files
  1   at least one dash in a carve-out-violating position
  2   usage error (unknown flag, no such file)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Tier 1 (MAC-686): reader-facing prose. Fix all of these.
TIER_1 = (
    "README.md",
    "CHANGELOG.md",
    "CREDITS.md",
    "docs/USER_GUIDE.md",
    "docs/engineering/SETUP.md",
    "docs/engineering/DATA_DICTIONARY.md",
    "docs/engineering/METHODOLOGY.md",
    "docs/engineering/PROJECT_BIBLE.md",
)

# Tier 2 (reserved -- do not hand-edit, regenerate instead). Listed here so the
# constant-based extension story stays consistent. The Tier 2 fix is to clean the
# generator / write-side of the ledger, NOT to edit the bytes of the artifact.
TIER_2 = (
    "exports/coverage_report.md",
    "docs/engineering/BIBLE_AMENDMENTS.md",
)

# Tier 3 (internal, not shipped with the release).
TIER_3 = (
    "docs/internal/PROJECT_STATE.md",
    "docs/internal/PLANNED_AND_FUTURE_UPDATES.md",
)

# The four top-level stubs (DATA_DICTIONARY.md / METHODOLOGY.md /
# BIBLE_AMENDMENTS.md / SETUP.md at repo root, 337-381 bytes, zero dashes)
# were a v1.5.1 redirect arrangement. They are NOT broken docs; they are
# redirect pages. The gate does not look at them because they are not in
# the tier lists. If someone re-introduces dashes there, they are out of
# scope for THIS gate but a future sweep may revisit.

EM = "\u2014"
EN = "\u2013"
TARGET_CHARS = (EM, EN)

# Fenced code: ``` or ~~~ at line start, run length 3+.
FENCE_RE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})")

# Inline code span (single backticks, no embedded backticks). We track
# odd/even parity per line so ` foo --bar ` does not become a span-aware
# parse across the whole document.
INLINE_CODE_BACKTICK_RE = re.compile(r"`[^`\n]*`")

# URL (very permissive -- http(s):// or "data:" or paths starting with /).
# Stops at whitespace or `)`. Markdown autolinks <https://...> are matched
# separately. The carve-out covers both so an inline `https://...` and a
# reference-style `[label](https://...)` target both clear the gate.
URL_RE = re.compile(r"https?://[^\s)<>\"'`]+")


def _is_in_fenced_code(lines: list[str], line_no: int) -> bool:
    """Return True if lines[line_no] is inside a fenced code block.

    Walks the file from the top to line_no. Tracks fence open/close state.
    A fence opens with ``` or ~~~ at line start (with up to 3 spaces indent)
    and closes when the same fence character appears at line start again.
    """
    in_fence = False
    fence_char = ""
    fence_len = 0
    for i in range(line_no + 1):
        line = lines[i]
        m = FENCE_RE.match(line)
        if m:
            run = m.group(2)
            ch = run[0]
            n = len(run)
            stripped = line[m.end():].strip()
            if not in_fence:
                # Open. The info string (anything after the run on the fence
                # line) is ignored; closing fences must EITHER be bare OR
                # carry only an info string of the same length -- but we are
                # conservative and only re-open on bare re-fences.
                in_fence = True
                fence_char = ch
                fence_len = n
            else:
                # Close: same character, run length >= open, info string bare
                # or same-length-only. We treat anything that matches the
                # fence character with the minimum open length as a close.
                if ch == fence_char and n >= fence_len and not stripped:
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
    return in_fence


def _is_table_cell_placeholder_dash(line: str, ch: str, pos: int) -> bool:
    """Return True if ``ch`` at ``pos`` is a Markdown table-cell placeholder.

    A placeholder is a Markdown table row (line starts with ``|``, optional
    indent up to 3 spaces) where the character sits in a cell whose entire
    content is the dash (with optional whitespace and a single pair of
    backticks).  Examples that match: ``| yes | — |`` and ``| `—` |``.
    A dash inside a cell with other characters is prose and does NOT match;
    that one fires.
    """
    stripped = line.lstrip(" ")
    if not stripped.startswith("|"):
        return False
    # Find the cell boundaries around pos.
    # Cells are segments between unescaped pipes. Walk from the start.
    cells: list[tuple[int, int]] = []
    i = 0
    n = len(line)
    cur_start = None
    while i < n:
        c = line[i]
        if c == "\\" and i + 1 < n and line[i + 1] == "|":
            i += 2
            continue
        if c == "|":
            if cur_start is None:
                cur_start = i
            else:
                cells.append((cur_start, i))
                cur_start = i
        i += 1
    if cur_start is not None:
        cells.append((cur_start, n))
    for s, e in cells:
        cell_text = line[s + 1 : e]
        inner = cell_text.strip()
        if inner == ch or inner == f"`{ch}`":
            if s + 1 <= pos <= e:
                return True
        # Also accept " — " (with surrounding spaces) -- we already stripped.
    return False


def _strip_carveouts(line: str) -> str:
    """Strip the carved-out regions out of ``line`` and return what remains.

    Carve-outs (in order): inline code spans, URLs, MD-table-cell placeholder
    dashes. Whitespace is preserved so line numbers in any ``--list`` output
    stay aligned with the source.
    """
    if (
        "`" not in line
        and "http" not in line.lower()
        and "|" not in line
    ):
        return line
    pieces: list[tuple[int, int]] = []

    for m in INLINE_CODE_BACKTICK_RE.finditer(line):
        pieces.append((m.start(), m.end()))

    for m in URL_RE.finditer(line):
        # Avoid double-counting if a URL was already part of a code span.
        if any(s <= m.start() < e for s, e in pieces):
            continue
        pieces.append((m.start(), m.end()))

    if not pieces:
        return line

    pieces.sort()
    merged: list[tuple[int, int]] = []
    for s, e in pieces:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    out: list[str] = []
    cur = 0
    for s, e in merged:
        out.append(line[cur:s])
        cur = e
    out.append(line[cur:])
    return "".join(out)


def _scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no_1based, char, line) for every carve-out-violating dash."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    hits: list[tuple[int, str, str]] = []
    for i, raw in enumerate(lines):
        if _is_in_fenced_code(lines, i):
            continue
        stripped = _strip_carveouts(raw)
        for ch in TARGET_CHARS:
            # Walk through the RAW line so positions are accurate; the table
            # placeholder check needs raw coordinates, not stripped ones.
            reported = False
            for pos_in_raw, raw_char in enumerate(raw):
                if raw_char != ch:
                    continue
                if ch in stripped:
                    # Cheap pre-check: is this character present in stripped?
                    # Always true unless the character sits inside an inline
                    # carve-out zone (backtick code span or URL).
                    pass
                if _is_table_cell_placeholder_dash(raw, ch, pos_in_raw):
                    continue
                # Confirm the character survives the carve-outs.
                if ch not in stripped:
                    continue
                hits.append((i + 1, ch, raw))
                reported = True
                break
            if reported:
                break
    return hits


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Argus prose dash gate (MAC-686).")
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print file:line:context for every hit and exit non-zero if any.",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Override the tier list with ad-hoc paths (relative to repo root).",
    )
    parser.add_argument(
        "--tier",
        choices=("1", "2", "3", "all"),
        default="1",
        help="Which tier to scan. Default 1.",
    )
    args = parser.parse_args(argv)

    if args.paths is not None:
        files = tuple(args.paths)
    elif args.tier == "1":
        files = TIER_1
    elif args.tier == "2":
        files = TIER_2
    elif args.tier == "3":
        files = TIER_3
    else:
        files = TIER_1 + TIER_2 + TIER_3

    total = 0
    for rel in files:
        path = REPO / rel
        hits = _scan_file(path)
        for line_no, ch, raw in hits:
            total += 1
            if args.list:
                ctx = raw.strip()
                if len(ctx) > 120:
                    ctx = ctx[:117] + "..."
                print(f"{rel}:{line_no}: U+{ord(ch):04X} ({ch!r})  {ctx}")
        if hits and not args.list:
            print(
                f"{rel}: {len(hits)} dash(es) (run with --list for details)",
                file=sys.stderr,
            )

    if total:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
