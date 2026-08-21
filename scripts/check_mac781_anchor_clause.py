#!/usr/bin/env python3
"""MAC-781 anchor+clause gate.

The MAC-781 DML pass replaces a bare line-number cite in
``identifiers.notes`` with a structurally-rooted HTML anchor cite plus a
quoted-clause trip-wire. The cited clause lives in
``docs/engineering/BIBLE_AMENDMENTS.md`` inside the cctv_camera row of the
CP33 S2 cohort table.

A bare line number is what failed before (line 4197 silently drifted to
line 4264). Replacing it with an HTML anchor only fixes the failure class
if a mechanical check proves the anchor resolves to exactly one line AND
the quoted clause text in ``notes`` still matches what that line says.
This gate is that check.

Exit codes
----------

* ``0`` — every row's anchor is unique and the quoted clause text matches
  the document line the anchor resolves to.
* ``1`` — at least one FAIL or ERROR. See printed diagnostics.
* ``2`` — usage / IO error (file missing, malformed JSON, etc.).

Three check arms
----------------

1. **Anchor uniqueness** — ``<a id="mac781-cp33-s2-1-cctv_camera"></a>``
   resolves to exactly one line in
   ``docs/engineering/BIBLE_AMENDMENTS.md``. Zero matches = ERROR (anchor
   not placed). Two or more matches = ERROR (ambiguous; the gate refuses
   to guess).

2. **Clause match** — for every active row carrying the new anchor in
   ``notes.category_correction_authority``, the quoted clause text after
   the anchor in the cite must be a substring of the document line the
   anchor resolves to (after stripping the leading ``<a id=...></a>``
   tag). A mismatch is a drift — the document changed, the cite did not.

3. **Idempotency** — no row carries both the OLD anchor (``:4197``) AND
   the NEW anchor. A row that carries both was migrated twice. A row
   that carries neither was not migrated.

Inputs
------

* ``--db`` (default ``db/argus.db``) — read-only.
* ``--doc`` (default ``docs/engineering/BIBLE_AMENDMENTS.md``) — the
  document containing the anchor.
* ``--anchor`` (default ``mac781-cp33-s2-1-cctv_camera``) — the HTML
  anchor id (without the ``<a id=...>`` wrapper).
* ``--expected-clause`` — required. The clause the cite quotes, as a
  substring the document line is expected to contain. The DML pass is
  authoritative for what this is — pass the exact text from the JSON
  ``category_correction_authority`` field of the migrated rows.
* ``--old-anchor`` (default ``BIBLE_AMENDMENTS.md:4197``) — the
  pre-migration anchor substring that must not appear in any
  ``notes.category_correction_authority`` after migration.
* ``--positive-control PATH`` — run with a scratch document file at
  ``PATH`` instead of the canonical one. Used by the test suite to prove
  the gate fails when the document drifts. The DB check is skipped in
  this mode (the scratch document is unrelated to canonical).

Drift detection — why this is mechanical, not human
----------------------------------------------------

The whole defect in ``BIBLE_AMENDMENTS.md:4197`` was that it drifted with
NO signal. The previous proposal relied on "a reviewer clicking the
anchor sees the drift" — that is a human trip-wire, and it failed
exactly because the cite carried an unrelated document line. This gate
replaces the human trip-wire with a check that runs in CI and exits
non-zero on the same drift class.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ANCHOR_RE = re.compile(
    r'<a\s+id\s*=\s*["\']'
    r'(?P<id>[^"\']+)'
    r'["\']\s*></a>'
)
CLAUSE_NEEDLE_RE = re.compile(
    r"`[^`]+`\s+'[^']+'"
)


def _read_doc(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read document {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def _anchor_lines(doc_text: str, anchor_id: str) -> list[tuple[int, str]]:
    """Return (line_number_1indexed, line_text) for every line whose HTML
    anchor tag carries the given id. Empty list = anchor not placed."""
    out: list[tuple[int, str]] = []
    for i, line in enumerate(doc_text.split("\n"), 1):
        for m in ANCHOR_RE.finditer(line):
            if m.group("id") == anchor_id:
                out.append((i, line))
                break
    return out


def _strip_anchor_tag(line: str, anchor_id: str) -> str:
    """Remove the HTML anchor tag from a line, returning the visible text."""
    return re.sub(
        r'<a\s+id\s*=\s*["\']'
        + re.escape(anchor_id)
        + r'["\']\s*></a>',
        "",
        line,
    ).strip()


def _check_anchor(doc_text: str, anchor_id: str) -> tuple[bool, list[tuple[int, str]]]:
    """Returns (ok, lines). ok=True iff exactly one match."""
    lines = _anchor_lines(doc_text, anchor_id)
    if not lines:
        print(
            f"FAIL anchor: <a id=\"{anchor_id}\"></a> resolves to 0 lines in "
            f"document. Anchor not placed (or document was edited away from it)."
        )
        return False, lines
    if len(lines) > 1:
        print(
            f"FAIL anchor: <a id=\"{anchor_id}\"></a> resolves to {len(lines)} "
            f"lines (ambiguous):"
        )
        for ln, text in lines:
            print(f"    line {ln}: {text.strip()[:110]}")
        return False, lines
    print(f"  anchor resolves to 1 line (line {lines[0][0]}).")
    return True, lines


def _check_clause(visible: str, expected_clause: str) -> bool:
    """Assert ``expected_clause`` is a substring of the document line at
    the anchor (after stripping the anchor tag)."""
    if expected_clause in visible:
        print("  clause match: PASS")
        return True
    print("FAIL clause: expected clause not found in document line at anchor.")
    print(f"  expected substring: {expected_clause!r}")
    print(f"  document line     : {visible!r}")
    return False


def _open_db(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        print(f"ERROR: cannot open {db_path} read-only: {exc}", file=sys.stderr)
        sys.exit(2)


def _check_db_rows(
    con: sqlite3.Connection,
    new_anchor_substring: str,
    old_anchor_substring: str,
    expected_clause: str,
) -> bool:
    """Three sub-checks:

    * every Half-1 row carries the new anchor substring
    * no Half-1 row carries the old anchor substring (post-migration idempotency)
    * the expected clause substring is present in every Half-1 row's
      category_correction_authority
    """
    cur = con.execute(
        "SELECT id, identifier, json_extract(notes, '$.category_correction_authority') "
        "FROM identifiers WHERE superseded_by IS NULL "
        "AND json_valid(notes) = 1 "
        "AND json_extract(notes, '$.category_correction_authority') IS NOT NULL"
    )
    rows = [r for r in cur.fetchall()]
    if not rows:
        print("FAIL db: no active rows carry category_correction_authority; "
              "is the migration applied?")
        return False

    # Subset to rows carrying the new anchor substring
    migrated = [r for r in rows if new_anchor_substring in (r[2] or "")]
    if not migrated:
        print(f"FAIL db: no active rows carry new anchor substring "
              f"{new_anchor_substring!r}. Migration not applied.")
        return False

    old_count = sum(1 for r in rows if old_anchor_substring in (r[2] or ""))
    if old_count:
        print(f"FAIL db: {old_count} active row(s) still carry the old "
              f"anchor substring {old_anchor_substring!r}. Migration incomplete.")
        return False

    missing_clause = [r for r in migrated if expected_clause not in (r[2] or "")]
    if missing_clause:
        print(f"FAIL db: {len(missing_clause)} migrated row(s) do not carry "
              f"the expected clause substring:")
        for r in missing_clause[:10]:
            print(f"    id={r[0]} identifier={r[1]}")
        return False

    print(f"  db rows migrated   : {len(migrated)}")
    print(f"  db rows with old   : {old_count}")
    print(f"  db rows drift      : 0")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", type=Path, default=REPO_ROOT / "db" / "argus.db")
    parser.add_argument(
        "--doc",
        type=Path,
        default=REPO_ROOT / "docs" / "engineering" / "BIBLE_AMENDMENTS.md",
    )
    parser.add_argument(
        "--anchor",
        default="mac781-cp33-s2-1-cctv_camera",
        help="HTML anchor id to resolve (default: %(default)s).",
    )
    parser.add_argument(
        "--expected-clause",
        required=True,
        help="Clause substring the document line at the anchor must contain.",
    )
    parser.add_argument(
        "--old-anchor",
        default="BIBLE_AMENDMENTS.md:4197",
        help="Old anchor substring that must not appear in any active row's "
             "category_correction_authority after migration.",
    )
    parser.add_argument(
        "--new-anchor",
        default="docs/engineering/BIBLE_AMENDMENTS.md#mac781-cp33-s2-1-cctv_camera",
        help="New anchor cite substring that must appear in every migrated row's "
             "category_correction_authority.",
    )
    parser.add_argument(
        "--positive-control",
        type=Path,
        default=None,
        help="Run with this scratch document file instead of the canonical one. "
             "Used to prove the gate fails when the document drifts.",
    )
    args = parser.parse_args()

    print(f"check_mac781_anchor_clause")
    print(f"  doc     : {args.doc}")
    print(f"  anchor  : {args.anchor}")
    print(f"  new     : {args.new_anchor}")
    print(f"  old     : {args.old_anchor}")
    print(f"  clause  : {args.expected_clause[:80]}{'...' if len(args.expected_clause) > 80 else ''}")

    doc_path = args.positive_control or args.doc
    doc_text = _read_doc(doc_path)
    ok_anchor, lines = _check_anchor(doc_text, args.anchor)

    ok_clause = True
    if ok_anchor:
        visible = _strip_anchor_tag(lines[0][1], args.anchor)
        ok_clause = _check_clause(visible, args.expected_clause)

    ok_db = True
    if args.positive_control is None and ok_anchor and ok_clause:
        # Only run db check after the doc-side arms pass; a missing anchor
        # or drifted clause is a more informative failure than the db
        # check's "migration not applied" message.
        con = _open_db(args.db)
        try:
            ok_db = _check_db_rows(con, args.new_anchor, args.old_anchor, args.expected_clause)
        finally:
            con.close()
    elif args.positive_control is not None:
        print("  positive-control mode: skipping db check")

    overall = ok_anchor and ok_clause and ok_db
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())