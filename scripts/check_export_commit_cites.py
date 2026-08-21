#!/usr/bin/env python3
"""Refuse a release whose generated export artifacts cite a commit that does not resolve.

BRIEF_STANDARDS.md R10, provenance dimension. STAGED, not standing -- MAC-703, filed out
of the MAC-696 ratification. Companion to `scripts/check_doc_anchors.py`, and deliberately
a SEPARATE script rather than another claim class inside it, because the two answer
different questions:

  check_doc_anchors.py    does a DOC print a number canonical disagrees with.
  this script             does a GENERATED EXPORT cite a commit git cannot resolve.

The defect this exists for: `export_lynceus.py:1859` wrote "(commit `6853780`)" -- a dead-cite exemplar --
into `exports/coverage_report.md`, which is a shipped artifact whose whole job is to document
provenance. (Quoted to document the defect, never asserted as a cite; the marker is what keeps
`scripts/check_commit_cites.py` from reading this docstring as a fresh instance of it.) `git cat-file -t 6853780` fails -- the object is not in this repo. A
correctness release shipped a provenance claim that did not resolve, and nothing
mechanical would have caught it.

Attribution corrected at MAC-704. This docstring first read "most likely dropped by the
MAC-610 history rewrite"; that is not what happened, and the correction matters because it
changes the remedy. `6853780` is absent from the `pre-filter-backup` tag (2026-05-14),
which IS an ancestor of HEAD -- so the object was already gone three months before MAC-610,
and MAC-610 cannot have dropped it. The same is true of every other dead cite in the tree:
they are pre-v1.0.0 shas, and the early-May history they name was rewritten wholesale
(`db/sources/deflock.py` was introduced by `22b6224` today, not by the `d81de3b` its own
docstring cited). Blaming a recent rewrite invites "repoint them to the new shas"; the
measured cause -- a rewrite nobody has a mapping for -- is why the content-hash remedy
below is the right one and re-pinning is not.

Why a content hash is the preferred remedy, not a fresher commit cite
---------------------------------------------------------------------
A commit cite is a claim about the object graph, and the object graph is not stable under
`filter-branch` / `filter-repo`. MAC-610 rewrote history and invalidated every pre-rewrite
sha in the tree at once -- 15 of 25 commit-context citations in tracked `*.py` / `*.md`
stopped resolving in a single operation. A sha256 of the cited bytes is a property of the
bytes and survives any rewrite. So this gate does not ask "is the cite fresh"; it asks
"does the cite resolve", and the fix for a failure is normally to replace the cite with a
content hash rather than to re-pin it.

What counts as a cite
---------------------
Only the CITE FORM is scanned: the literal word `commit` (any case) followed by an optional
backtick-quoted 7-40 char lowercase hex token. Scanning bare hex would be useless here --
`coverage_report.md` alone carries 999 tokens matching `[0-9a-f]{7,40}` and essentially all
of them are SAR-10 `argus_record_id` values (16-hex SHA-256 prefixes) and BLE UUID fields.
A gate that flagged those would be turned off within a day, which is the failure mode that
matters more than the false negatives of a narrow pattern.

Known non-cite that the narrow pattern correctly ignores: `export_lynceus.py:2001` embeds
`[`613ec532`](<TRACKER_URL>issues/MAC-1#comment-613ec532-...)`, a Paperclip COMMENT uuid prefix. It
is backticked hex and it is not a commit; it is not preceded by the word `commit`, so it
does not match. Widening the pattern to all backticked hex would fail this gate on a
correct artifact.

Scope
-----
Defaults to the five files the export writers actually generate, by name rather than by
glob, so an unrelated hand-written file dropped into `exports/` is not silently pulled into
a release gate (`exports/` also holds `v1.6.7_admission_exclusion_record.md` and a
`v1_5_2_raw_snapshot/` directory, neither of which is generated). Pass explicit paths to
scan something else.

Usage:
    python3 scripts/check_export_commit_cites.py
    python3 scripts/check_export_commit_cites.py --exports-dir /path/to/exports
    python3 scripts/check_export_commit_cites.py path/to/one.md
    python3 scripts/check_export_commit_cites.py --positive-control   # R7, see below

R7 positive control: once the MAC-703 fix lands there are ZERO commit cites left in the
generated artifacts, so the honest reading of a PASS is "nothing was evaluated", not "every
cite resolves". A zero-yield check that has never been shown firing is not evidence.
`--positive-control` writes a synthetic artifact carrying one known-dead cite (`6853780`,
the exact sha this issue was filed for) into a temp dir, scans it, and asserts the scanner
FAILS on it. It exits 0 only when the scanner fired; if the scanner passes the control, the
control exits 1 because the instrument is dead. The control runs in a temp dir and never
touches `exports/`.

The control must reach the scan to certify anything. `check_push_blob_sizes.py` shipped a
control that died at exit 2 on a usage error before the scan ran (repaired at MAC-612,
`eedd9a7`) -- exit 2 is not a firing instrument. `--positive-control` therefore takes no
other arguments and builds its own corpus, so there is no argument combination that can
strand it short of the scan.

Exit 0 = PASS (or: control fired as designed). Exit 1 = at least one cite does not resolve
(or: control did NOT fire). Exit 2 = usage error. Exit 3 = SKIPPED: no file in scope could
be read, so the release is uncertified, not clean. Same four codes and the same meanings as
`check_push_blob_sizes.py` and `check_staged_paths.py`; a push gate that had to remember
three exit-code dialects would eventually read one as the other.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# By name, not by glob -- see "Scope" in the module docstring.
GENERATED_EXPORT_ARTIFACTS = (
    "argus_export.json",
    "argus_export_high_confidence.json",
    "argus_export.csv",
    "argus_export_behavioral_signatures.json",
    "coverage_report.md",
)

# The word `commit`, then an optional backticked 7-40 hex token. Narrow on purpose.
COMMIT_CITE_RE = re.compile(r"commit\s+`?([0-9a-f]{7,40})`?", re.IGNORECASE)

# The dead sha MAC-703 was filed for. Used only to build the R7 control corpus.
CONTROL_DEAD_SHA = "6853780"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_UNEVALUATED = 3

assert len({EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_UNEVALUATED}) == 4, "exit codes collide"


def resolves_to_commit(sha: str, repo: Path) -> bool:
    """True iff `git cat-file -t <sha>` says `commit` in `repo`.

    Any other object type is a failure, not a pass: a cite that resolves to a blob or a
    tree is still not the commit it claims to be.
    """
    proc = subprocess.run(
        ("git", "-C", str(repo), "cat-file", "-t", sha),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode == 0 and proc.stdout.strip() == "commit"


def scan_file(path: Path, repo: Path):
    """Return (findings, read_ok). A finding is (line_no, sha, resolved)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"    ! unreadable: {path} ({exc})")
        return [], False

    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in COMMIT_CITE_RE.finditer(line):
            sha = match.group(1).lower()
            findings.append((line_no, sha, resolves_to_commit(sha, repo)))
    return findings, True


def run_scan(paths, repo: Path) -> int:
    total_cites = 0
    unresolved = []
    read_any = False

    for path in paths:
        if not path.exists():
            print(f"    - absent (not scanned): {path}")
            continue
        findings, read_ok = scan_file(path, repo)
        read_any = read_any or read_ok
        total_cites += len(findings)
        for line_no, sha, resolved in findings:
            status = "resolves" if resolved else "DOES NOT RESOLVE"
            print(f"    {'ok ' if resolved else 'FAIL'} {path}:{line_no} commit {sha} -- {status}")
            if not resolved:
                unresolved.append((path, line_no, sha))

    if not read_any:
        print("SKIPPED: no in-scope file could be read; release is uncertified, not clean.")
        return EXIT_UNEVALUATED

    print(f"    commit cites found: {total_cites}; unresolvable: {len(unresolved)}")
    if unresolved:
        print(
            "FAIL: a generated export artifact cites a commit this repo cannot resolve.\n"
            "      Prefer replacing the cite with a content hash of the cited bytes; a\n"
            "      commit cite does not survive a history rewrite and a content hash does."
        )
        return EXIT_FAIL

    if total_cites == 0:
        print(
            "PASS (zero cites in scope). Read this as 'nothing was evaluated', not as\n"
            "     'every cite resolves'. Run --positive-control before quoting it."
        )
    else:
        print("PASS: every commit cite in the generated export artifacts resolves.")
    return EXIT_OK


def run_positive_control(repo: Path) -> int:
    """R7: prove the scanner fires. Exits 0 only if it did."""
    print("R7 positive control: synthetic artifact with one known-dead cite "
          f"(`{CONTROL_DEAD_SHA}`).")
    if resolves_to_commit(CONTROL_DEAD_SHA, repo):
        print(
            f"    ! `{CONTROL_DEAD_SHA}` RESOLVES in this repo, so it cannot serve as a\n"
            "      dead-cite control here. Control is invalid; it certifies nothing.\n"
            "      (A control that cannot fail proves nothing in either direction.)"
        )
        return EXIT_FAIL

    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / "coverage_report.md"
        fixture.write_text(
            "# synthetic MAC-703 R7 control\n"
            "The matrix below is the MAC-45 coverage matrix at\n"
            f"`extraction_outputs/mac45/coverage_matrix.md` (commit `{CONTROL_DEAD_SHA}`).\n",
            encoding="utf-8",
        )
        rc = run_scan([fixture], repo)

    if rc == EXIT_FAIL:
        print("CONTROL FIRED: scanner returned 1 on the planted dead cite. Instrument live.")
        return EXIT_OK
    print(f"CONTROL DID NOT FIRE: scanner returned {rc} on a planted dead cite. "
          "The instrument is dead; a PASS from it means nothing.")
    return EXIT_FAIL


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Files to scan (default: generated exports).")
    parser.add_argument("--exports-dir", default=str(REPO_ROOT / "exports"))
    parser.add_argument("--repo", default=str(REPO_ROOT))
    parser.add_argument(
        "--positive-control",
        action="store_true",
        help="R7: plant a known-dead cite and assert the scanner fires. Takes no other args.",
    )
    args = parser.parse_args(argv)
    repo = Path(args.repo)

    if args.positive_control:
        if args.paths:
            print("usage: --positive-control builds its own corpus; do not pass paths.")
            return EXIT_USAGE
        return run_positive_control(repo)

    if args.paths:
        paths = [Path(p) for p in args.paths]
    else:
        exports_dir = Path(args.exports_dir)
        paths = [exports_dir / name for name in GENERATED_EXPORT_ARTIFACTS]

    print(f"Scanning {len(paths)} path(s) for unresolvable commit cites; repo {repo}")
    return run_scan(paths, repo)


if __name__ == "__main__":
    raise SystemExit(main())
