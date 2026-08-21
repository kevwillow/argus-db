#!/usr/bin/env python3
"""MAC-779 -- resolve ``§N`` section citations against real heading inventories.

WHAT THIS GATE SETTLES
======================

A ``§N`` citation is a claim that a numbered section N exists in some document.
Nothing in ``scripts/`` checked that claim before this gate. ``check_doc_anchors.py``
does not and says so in its own ``--coverage`` output::

    NOT COVERED, and not made covered by any flag:
      * section (§N) anchors, cross-references, headings, links

This gate settles a cite against a heading inventory. It deliberately does NOT
live inside ``check_doc_anchors.py``: that gate settles an integer against a
settling query, and putting two settling models behind one exit code is how a
gate starts meaning less than its rc suggests (declined in MAC-777, recorded in
that file's docstring).

WHICH DOCUMENTS' INVENTORIES IT RESOLVES AGAINST  (scope item 2)
================================================================

RESOLVED AGAINST -- the three documents in ``DOCUMENTS`` below:

  * ``docs/engineering/PROJECT_BIBLE.md``    headings read ``## 4. Data Schema``
  * ``docs/engineering/DATA_DICTIONARY.md``  headings read ``## §4. Tables``
  * ``docs/engineering/METHODOLOGY.md``      headings read ``## §5. Confidence model``

The two syntaxes are not cosmetic: the bible numbers its headings WITHOUT the
sigil and the other two number theirs WITH it. ``HEADING_RE`` accepts both, and
``test_check_section_anchors.py`` pins one live heading of each shape so a
one-syntax regex cannot pass.

These three are safe to resolve against because in each of them a section number
is declared exactly once, so a cite has exactly one referent. T1 pins that.

NOT RESOLVED AGAINST, on purpose:

  * ``docs/engineering/BIBLE_AMENDMENTS.md`` -- it DOES carry ``§N`` headings,
    but they are per-Correction-Pass LOCAL numbering that restarts in every
    pass: ``### §1 - The rule``, ``### §2 - Case study`` recur over and over
    down the file. A section number is therefore not unique within it, and
    resolving a cite against that inventory would be meaningless. A further
    subset (``### §12 Open Questions impact``) names a BIBLE section rather
    than declaring one of its own. It is scanned as a CITING file, never used
    as a cited inventory. ``test_t1_bible_amendments_...`` pins the
    non-uniqueness so this stated reason cannot quietly become false.
  * ``CHANGELOG.md``, ``README.md``, ``docs/USER_GUIDE.md`` -- no numbered-section
    convention; they cite, they are not cited by ``§N``.
  * Anything under a path in ``EXCLUDED_PREFIXES`` (operator scratch, extraction
    output). Those are working notes, not the shipping surface.

WHAT IT DOES NOT CHECK, stated so no one reads the rc as broader than it is
==========================================================================

  1. UNATTRIBUTED cites. A bare ``§4.4`` on a line that names no registered
     document is reported and NOT failed. Attribution is deliberately
     conservative -- see ATTRIBUTION below -- because a false attribution turns
     this gate into a generator of fake findings.
  2. Non-numeric section tokens: ``§-procurement_records`` names a section by
     slug, not number. Counted under ``NON_NUMERIC`` and not resolved.
  3. Item-level depth: ``§11 #11`` resolves ``§11``. Whether item 11 exists
     inside it is not checked.
  4. Line anchors: ``PROJECT_BIBLE.md:279`` is a line cite, not a section cite.
     A ``§N`` gate is structurally blind to it; ``check_commit_cites.py`` and the
     bible's own line-anchor discipline are the instruments there.
  5. Anchor links (``[text](FILE.md#heading)``) and heading UNIQUENESS in the
     citing direction. A duplicated section number in a registered document is
     caught by the test suite, not by this gate's rc.

ATTRIBUTION
===========

A cite is attributed to document D when D's name appears on the SAME line, before
the ``§`` (or in the trailing ``§N of the <doc>`` form), with no barrier token
between the name and the sigil. Barriers exist because prose re-scopes mid-line::

    CHANGELOG.md:1176
      ... a new bible subsection requiring every runguide to ship a `§3.0`
      verification-probe section that completes CLEAN POSITIVE ...

That ``§3.0`` is a section of a RUNGUIDE, not of the bible. The untracked
MAC-773 instrument attributed it to the bible and emitted a finding for it;
``runguide`` as a barrier is what makes this gate not repeat that.

For the same reason ``METHODOLOGY`` and ``DATA_DICTIONARY`` are matched
CASE-SENSITIVELY (the filename form), while ``bible`` is matched
case-insensitively -- there is no common English noun "bible" in this corpus
that is not the project bible, but "methodology" as a plain noun is everywhere.

Every barrier token below was kept only after measuring it against the tree: a
token that widens attribution without preventing a false finding is coverage
thrown away for nothing, and was dropped. ``correction pass`` was dropped on
exactly that evidence (+7 cites attributed, 0 new findings).

NO SELF-RESOLUTION
==================

A bare ``§N`` inside a registered document does NOT resolve against that
document. ``docs/engineering/DATA_DICTIONARY.md:84`` reads::

    | `procurement_records` | analytical-only (never exported to Lynceus per
      §11 #14); ...

That ``§11`` is the BIBLE's §11 (Critical Don'ts), not DATA_DICTIONARY's. Self-
resolution was implemented first and produced 125 unresolved cites, nearly all
of them this one false attribution; removing it left 9.

EXIT STATUS
===========

0 -- every attributed cite resolves.
1 -- at least one attributed cite names a section its document does not have.
2 -- the gate could not run (a registered document is missing or unreadable).

Usage::

    python3 scripts/check_section_anchors.py                 # working tree
    python3 scripts/check_section_anchors.py --rev HEAD      # a git rev
    python3 scripts/check_section_anchors.py --coverage      # scope, no checks
    python3 scripts/check_section_anchors.py --list          # every cite, resolved too
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# The document registry. This IS the coverage contract -- `--coverage` prints
# it, and the test suite binds the printed scope to the scanned scope so it
# cannot drift into a dead constant (the MAC-777 defect).
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Document:
    key: str
    path: str
    # Regex matching this document's name in prose. Grouped, no captures.
    name_re: str
    # re.IGNORECASE for this name, or 0 for case-sensitive.
    name_flags: int
    why: str


DOCUMENTS: tuple[Document, ...] = (
    Document(
        key="PROJECT_BIBLE",
        path="docs/engineering/PROJECT_BIBLE.md",
        name_re=r"PROJECT_BIBLE(?:\.md)?|\bbibles?\b",
        name_flags=re.IGNORECASE,
        why="the contract; §6/§7 alone carry hundreds of cites",
    ),
    Document(
        key="DATA_DICTIONARY",
        path="docs/engineering/DATA_DICTIONARY.md",
        # Case-sensitive: the filename form only. "data dictionary" as an
        # English phrase must not pull a § into this document's inventory.
        name_re=r"DATA_DICTIONARY(?:\.md)?",
        name_flags=0,
        why="schema reference; cited by §N from migrations and CHANGELOG",
    ),
    Document(
        key="METHODOLOGY",
        path="docs/engineering/METHODOLOGY.md",
        # Case-sensitive for the same reason, and more urgently: "methodology"
        # is a common noun in this corpus.
        name_re=r"METHODOLOGY(?:\.md)?",
        name_flags=0,
        why="confidence model and provenance discipline; cited by §N widely",
    ),
)

NOT_AN_INVENTORY: tuple[tuple[str, str], ...] = (
    (
        "docs/engineering/BIBLE_AMENDMENTS.md",
        "its §N headings are per-Correction-Pass LOCAL numbering that restarts "
        "in every pass -- `### §1 - The rule` recurs many times over -- so a "
        "section number is not unique within the file and resolving against it "
        "would be meaningless. Others (`### §12 Open Questions impact`) name a "
        "BIBLE section rather than declaring one. Scanned as a citing file.",
    ),
    (
        "CHANGELOG.md",
        "no numbered-section convention; cites but is not cited by §N",
    ),
    (
        "README.md",
        "no numbered-section convention; cites but is not cited by §N",
    ),
)

# Working notes, not the shipping surface. `operator_review/` is untracked as of
# 2864473 (MAC-763) and so is absent from a fresh clone anyway; the prefix is
# kept so a working-tree run agrees with a `--rev` run.
EXCLUDED_PREFIXES: tuple[str, ...] = (
    "operator_review/",
    "extraction_outputs/",
    "scratch/",
    "scratch_",
)

# --------------------------------------------------------------------------
# Lexing
# --------------------------------------------------------------------------

# Accepts BOTH heading shapes:
#   "## 4. Data Schema"        (PROJECT_BIBLE)
#   "### §4.1. `identifiers`"  (DATA_DICTIONARY, METHODOLOGY)
HEADING_RE = re.compile(r"^\s{0,3}(#{2,6})\s+(?:§\s*)?(\d+(?:\.\d+)*)\.?(?:\s|$)")

# A numeric section cite. `§4.4`, `§ 4.4`, `§§4.4` all count once per number.
CITE_RE = re.compile(r"§\s*(\d+(?:\.\d+)*)")

# A § followed by something that is not a number -- `§-procurement_records`.
NON_NUMERIC_RE = re.compile(r"§\s*(?!\d)")

# The trailing form: "§7.5 of the bible", "§5 of METHODOLOGY.md".
TRAILING_SCOPE_WINDOW = 40

# How far back from the § a document name may sit and still bind it.
LOOKBACK_WINDOW = 90

# Tokens that re-scope a section cite away from a document named earlier on the
# same line. Every one is drawn from a real line in the tree AND was measured to
# prevent at least one false finding; see ATTRIBUTION in the module docstring.
#
# `MAC-\d+` is here because an issue identifier immediately before a § scopes
# that § to the issue's own brief, not to a document named earlier in the line:
#
#   db/validation/export_lynceus.py:156
#     # (PROJECT_BIBLE.md:279, board e246a32a, MAC-101 §2.5). Un-held at MAC-360
#
# Without the barrier the leading `PROJECT_BIBLE.md` binds `§2.5` and the gate
# emits a finding against a cite that was never a bible cite.
BARRIER_RE = re.compile(
    r"\b(?:dispatch|dispatches|brief|briefs|runguide|runguides"
    r"|amendment|amendments|this\s+issue|the\s+issue"
    r"|per\s+S\.\d|checkpoint|MAC-\d+)\b",
    re.IGNORECASE,
)

# A document name in `NAME.md:279` form is a LINE cite, a different citation
# form entirely. It must not scope a `§N` later on the same line.
LINE_CITE_SUFFIX_RE = re.compile(r"^(?:\.md)?:\d+")


@dataclass(frozen=True)
class Cite:
    file: str
    line: int
    section: str
    doc_key: str | None  # None => UNATTRIBUTED
    text: str


@dataclass(frozen=True)
class Unresolved:
    cite: Cite
    doc_path: str


# --------------------------------------------------------------------------
# Source access -- a git rev or a directory on disk. Both, so the release gate
# can read a rev and the positive-control test can mutate a scratch tree.
# --------------------------------------------------------------------------


class Tree:
    """A readable source tree: either a git rev or a plain directory."""

    def __init__(self, root: Path, rev: str | None = None) -> None:
        self.root = root
        self.rev = rev

    def read(self, rel: str) -> str | None:
        if self.rev:
            proc = subprocess.run(
                ["git", "-C", str(self.root), "show", f"{self.rev}:{rel}"],
                capture_output=True,
            )
            if proc.returncode != 0:
                return None
            raw = proc.stdout
        else:
            path = self.root / rel
            if not path.is_file():
                return None
            raw = path.read_bytes()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

    def files(self) -> list[str]:
        """Every candidate file, excluding EXCLUDED_PREFIXES."""
        if self.rev:
            out = subprocess.run(
                ["git", "-C", str(self.root), "ls-tree", "-r", "--name-only", self.rev],
                capture_output=True, text=True, check=True,
            ).stdout
            names = [f for f in out.split("\n") if f]
        else:
            proc = subprocess.run(
                ["git", "-C", str(self.root), "ls-files"],
                capture_output=True, text=True,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                names = [f for f in proc.stdout.split("\n") if f]
            else:
                # Not a git repo (the test scratch trees are not, and neither is
                # a `git archive` cleanroom). Walk it rather than going
                # vacuously green on an empty file list.
                names = []
                for dirpath, dirnames, filenames in os.walk(self.root):
                    dirnames[:] = [d for d in dirnames if d != ".git"]
                    for fn in filenames:
                        names.append(
                            str((Path(dirpath) / fn).relative_to(self.root))
                        )
        return sorted(
            f for f in names if not f.startswith(EXCLUDED_PREFIXES)
        )


# --------------------------------------------------------------------------
# Inventory + attribution
# --------------------------------------------------------------------------


def heading_inventory(text: str) -> set[str]:
    """Every numbered section this document actually declares."""
    return {
        m.group(2)
        for line in text.split("\n")
        if (m := HEADING_RE.match(line))
    }


def _name_spans(line: str) -> list[tuple[int, int, str]]:
    """(start, end, doc_key) for every registered document name on the line.

    A name in `NAME.md:279` line-cite form is skipped: it cites a line, not a
    section, and must not scope a `§N` appearing later in the same line.
    """
    spans: list[tuple[int, int, str]] = []
    for doc in DOCUMENTS:
        for m in re.finditer(doc.name_re, line, doc.name_flags):
            if LINE_CITE_SUFFIX_RE.match(line[m.end():]):
                continue
            spans.append((m.start(), m.end(), doc.key))
    return spans


def attribute(line: str, cite_start: int) -> str | None:
    """Which document owns the ``§`` at ``cite_start``? None => unattributed.

    Nearest preceding name within LOOKBACK_WINDOW wins, unless a barrier token
    sits between that name and the sigil. Then the trailing ``of the <doc>``
    form. Otherwise unattributed -- see NO SELF-RESOLUTION in the module
    docstring for why "inside document D, a bare §N means D" is false here.
    """
    spans = _name_spans(line)
    candidates = [
        s for s in spans
        if s[1] <= cite_start and cite_start - s[1] <= LOOKBACK_WINDOW
    ]
    if candidates:
        _start, end, key = max(candidates, key=lambda s: s[1])
        if not BARRIER_RE.search(line[end:cite_start]):
            return key

    tail = line[cite_start:cite_start + TRAILING_SCOPE_WINDOW]
    for tstart, _tend, key in _name_spans(tail):
        # "§7.5 of the bible" -- require an "of" between the § and the name so
        # "§5. Confidence model ... METHODOLOGY rules" does not bind backwards.
        if re.search(r"\bof\b", tail[:tstart], re.IGNORECASE):
            return key

    return None


# --------------------------------------------------------------------------
# Scan
# --------------------------------------------------------------------------


def scan(tree: Tree) -> tuple[list[Cite], dict[str, set[str]], int, list[str]]:
    """Return (cites, inventories, non_numeric_count, missing_docs)."""
    inventories: dict[str, set[str]] = {}
    missing: list[str] = []
    for doc in DOCUMENTS:
        text = tree.read(doc.path)
        if text is None:
            missing.append(doc.path)
            continue
        inventories[doc.key] = heading_inventory(text)

    cites: list[Cite] = []
    non_numeric = 0
    for rel in tree.files():
        text = tree.read(rel)
        if text is None or "§" not in text:
            continue
        for lineno, line in enumerate(text.split("\n"), 1):
            if "§" not in line:
                continue
            non_numeric += len(NON_NUMERIC_RE.findall(line))
            for m in CITE_RE.finditer(line):
                cites.append(
                    Cite(
                        file=rel,
                        line=lineno,
                        section=m.group(1),
                        doc_key=attribute(line, m.start()),
                        text=line.strip(),
                    )
                )
    return cites, inventories, non_numeric, missing


def unresolved(cites: list[Cite], inventories: dict[str, set[str]]) -> list[Unresolved]:
    by_key = {doc.key: doc.path for doc in DOCUMENTS}
    out: list[Unresolved] = []
    for c in cites:
        if c.doc_key is None:
            continue
        inv = inventories.get(c.doc_key)
        if inv is None:
            continue  # missing doc -> reported as a run failure, not a finding
        if c.section not in inv:
            out.append(Unresolved(cite=c, doc_path=by_key[c.doc_key]))
    return out


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def resolved_against() -> tuple[str, ...]:
    return tuple(doc.path for doc in DOCUMENTS)


def format_coverage_report() -> str:
    lines = ["check_section_anchors.py -- what this gate resolves §N cites against:"]
    lines.append("")
    lines.append("  RESOLVED AGAINST (a failure here exits 1):")
    for doc in DOCUMENTS:
        lines.append(f"    {doc.path}  -- {doc.why}")
    lines.append("")
    lines.append("  NOT AN INVENTORY, on purpose:")
    for path, why in NOT_AN_INVENTORY:
        lines.append(f"    {path}")
        lines.append(f"        {why}")
    lines.append("")
    lines.append("  NOT COVERED, and not made covered by any flag:")
    lines.append("    * cites naming no registered document (reported UNATTRIBUTED)")
    lines.append("    * non-numeric section tokens, e.g. `§-procurement_records`")
    lines.append("    * item depth inside a section, e.g. the `#11` in `§11 #11`")
    lines.append("    * line anchors, e.g. `PROJECT_BIBLE.md:279` -- not a §N cite")
    lines.append("    * markdown anchor links and heading-number UNIQUENESS")
    lines.append("")
    lines.append("  NOT SCANNED (working notes, not the shipping surface):")
    for prefix in EXCLUDED_PREFIXES:
        lines.append(f"    {prefix}")
    return "\n".join(lines)


def coverage_line() -> str:
    return "resolved against: " + ", ".join(resolved_against())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="tree root (default: cwd)")
    ap.add_argument("--rev", default=None, help="read from this git rev instead of disk")
    ap.add_argument("--coverage", action="store_true", help="print scope, run no checks")
    ap.add_argument("--list", action="store_true", help="list every attributed cite")
    args = ap.parse_args(argv)

    if args.coverage:
        print(format_coverage_report())
        return 0

    tree = Tree(Path(args.root).resolve(), args.rev)
    cites, inventories, non_numeric, missing = scan(tree)

    if missing:
        for path in missing:
            print(f"ERROR: registered document not readable: {path}", file=sys.stderr)
        print(
            "The gate cannot resolve cites against a document it cannot read. "
            "This is a run failure (rc=2), not a clean pass.",
            file=sys.stderr,
        )
        return 2

    bad = unresolved(cites, inventories)
    bad_ids = {id(u.cite) for u in bad}
    attributed = [c for c in cites if c.doc_key is not None]
    unattributed = len(cites) - len(attributed)

    scope = f"@{args.rev}" if args.rev else f"{tree.root}"
    print(f"check_section_anchors {scope}")
    print(f"  {coverage_line()}")
    for doc in DOCUMENTS:
        inv = inventories[doc.key]
        n = sum(1 for c in attributed if c.doc_key == doc.key)
        print(
            f"    {doc.path}: {len(inv)} numbered headings, "
            f"{n} cite(s) attributed to it"
        )
    print(f"  numeric §N cites found: {len(cites)}")
    print(f"    ATTRIBUTED: {len(attributed)}   UNATTRIBUTED (not checked): {unattributed}")
    print(f"    non-numeric § tokens (not checked): {non_numeric}")
    print(f"  RESOLVED: {len(attributed) - len(bad)}   UNRESOLVED: {len(bad)}")

    if args.list:
        for c in sorted(attributed, key=lambda c: (c.file, c.line, c.section)):
            status = "UNRESOLVED" if id(c) in bad_ids else "OK"
            print(f"    {status:<10} §{c.section:<8} {c.doc_key:<16} {c.file}:{c.line}")

    for u in bad:
        c = u.cite
        print(
            f"    UNRESOLVED §{c.section} -> {u.doc_path}   "
            f"{c.file}:{c.line}\n        {c.text[:150]}"
        )

    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
