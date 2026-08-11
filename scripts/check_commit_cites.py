#!/usr/bin/env python3
"""MAC-704 — measure commit-SHA citations in tracked code and docs.

A SHA cited in prose is a coordinate into a history that can be rewritten. When it
is, the cite dangles and the reader loses the only handle they had on *why* a rule
exists. This script is the producing selector for that measurement, per
``operator_review/BRIEF_STANDARDS.md`` R9 — the number is not quotable unless the
script that emits it is committed and carries a structural guard.

Four classifications, and the distinctions past the first two are the whole point:

``live``      the token resolves to a ``commit`` object in this repository.
``dead``      the token does not resolve, and the citing line claims it is an
              argus commit. This is the defect.
``foreign``   the token does not resolve *and never could*, because the citing line
              says so: it pins a commit in someone else's repository. Counting these
              as dead inflates the defect and sends the next reader chasing an object
              that was never supposed to be here.
``exemplar``  the token is quoted rather than asserted — this script's own fixtures,
              a gate's docstring showing the bytes it catches, a verbatim quotation
              of someone's historical prose.

The exemptions are read off the citing line, never off a list inside this file. R9
bans a literal set where a dropped member would change the answer, and a hard-coded
allowlist of exempt SHAs is exactly that shape: it goes stale the moment someone adds
a sixteenth upstream pin. The line carries the marker; the scanner reads it. And the
exemption is **unanimous or it does not apply** — one undeclared argus-context cite
keeps the SHA in the defect set no matter how many other sites are fenced.

Two scopes, because the defect class is wider than what any one lane may repair:

``full``     the MAC-704 selector as filed. This is the honest denominator.
``repair``   ``full`` minus the paths this lane must not rewrite — append-only
             heartbeat logs, ratified operator artifacts, generated exports.
             Narrowing is stated, never silent: ``--scope full`` reports every
             carve-out and its reason, and guard arm D fails if one goes stale.

Usage::

    python3 scripts/check_commit_cites.py                     # repair scope, human report
    python3 scripts/check_commit_cites.py --scope full        # full defect class
    python3 scripts/check_commit_cites.py --selftest          # R7 positive control
    python3 scripts/check_commit_cites.py --json              # machine-readable

Exit codes: ``0`` no dead cites in scope, ``1`` dead cites remain, ``2`` the
structural guard or the positive control failed (the instrument is untrustworthy;
its zero means nothing).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The selector as filed on MAC-704. Anchored on the literal word "commit" so that
# bare hex — overwhelmingly BLE service UUIDs like 0000fc6d — is not swept in.
FILED_RE = re.compile(r"commit [`(]?([0-9a-f]{7,40})")

# A second cite class the filed selector structurally cannot see, and the one that
# mattered most. `BIBLE_AMENDMENTS.md` records each amendment under a header of the
# form "**Commit:** `<sha>` — `<subject>`". That is a capital C followed by a colon,
# so no amount of tuning the filed pattern reaches it. Measured at MAC-704: 12
# distinct shas in this form, 6 of them dead — CP1 through CP6.
#
# This is why the after-count is reported against BOTH patterns. Repairing only what
# the filed selector could see would have left the ledger's own primary cite
# mechanism half dead while the gate printed PASS.
LEDGER_RE = re.compile(r"\*\*Commit:\*\* +`?([0-9a-f]{7,40})")

CITE_PATTERNS = (FILED_RE, LEDGER_RE)


def extract(text: str) -> list[str]:
    """Every SHA cited on one line, across all cite classes."""
    out: list[str] = []
    for pat in CITE_PATTERNS:
        out.extend(pat.findall(text))
    return out

# R3 — markers are literal strings, printed here and in the citing line verbatim. A
# described marker is a marker that drifts.
#
# Two ways a non-resolving SHA can be legitimate, and they are not the same thing:
#
#   FOREIGN_MARKER   the SHA names a commit in someone else's repository. It never
#                    resolved here and never will. Repairing it would be wrong.
#   EXEMPLAR_MARKER  the SHA is quoted rather than asserted — a gate's docstring
#                    showing the bytes it was built to catch, or a verbatim
#                    quotation of someone's historical prose. Deleting it would
#                    delete the explanation or falsify the quote. This is the fence
#                    a scanner needs when its corpus includes write-ups about
#                    itself: without it, documenting a dead cite is
#                    indistinguishable from making one.
#
# A marker must sit on the SAME LINE as the sha it exempts. Allowing it to apply
# from a neighbouring line would let one annotation silently fence whatever cite
# happened to be nearby, which is the blast radius a fence exists to bound. It costs
# a slightly longer line and buys an exemption you can read without scrolling.
FOREIGN_MARKER = "foreign-repo SHA"
EXEMPLAR_MARKER = "dead-cite exemplar"
MARKERS = {"foreign": FOREIGN_MARKER, "exemplar": EXEMPLAR_MARKER}

# Excluded from the FILED selector itself, per the MAC-704 issue body.
FILED_EXCLUSIONS = ("operator_review/MAC-541",)

# Excluded from the REPAIR scope only. Each entry names why the lane may not write
# there; the reason is carried so that a later reader does not mistake a deliberate
# carve-out for an oversight. Guard arm D fails if any prefix here matches nothing,
# because a carve-out that narrows nothing still reads as though it narrowed something.
#
# NOT listed, deliberately: `db/validation/export_lynceus.py`. The MAC-45 provenance
# lane holds it dirty and its line 1596 discusses `6853780`, but it writes the sha
# double-backticked (``6853780``) so the selector never matches it. Adding a carve-out
# for a path the selector cannot reach is the stale-carve-out defect arm D exists to
# catch — it was tried here first, and arm D rejected it.
REPAIR_EXCLUSIONS = {
    "docs/internal/": "append-only heartbeat log; ratified verbatim prose is not edited in place",
    "operator_review/": "ratified operator artifacts; verbatim prose is not edited in place",
    "exports/": "generated artifact; owned by check_export_commit_cites.py (MAC-703), not hand-edited",
}


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    )
    return proc.stdout


def grep_lines() -> list[tuple[str, int, str]]:
    """Run the filed selector and return (path, lineno, text) for every hit."""
    argv = ["grep", "-nE"]
    for pat in CITE_PATTERNS:
        argv += ["-e", pat.pattern]
    raw = _git(*argv, "--", "*.py", "*.md")
    hits: list[tuple[str, int, str]] = []
    for line in raw.splitlines():
        path, _, rest = line.partition(":")
        lineno, _, text = rest.partition(":")
        if not lineno.isdigit():
            continue
        if any(path.startswith(x) for x in FILED_EXCLUSIONS):
            continue
        hits.append((path, int(lineno), text))
    return hits


def in_repair_scope(path: str) -> str | None:
    """Return the carve-out reason if ``path`` is outside the repair scope."""
    for prefix, reason in REPAIR_EXCLUSIONS.items():
        if path.startswith(prefix):
            return reason
    return None


def resolves(sha: str) -> bool:
    """True when ``sha`` names a commit object in this repository."""
    proc = subprocess.run(
        ["git", "cat-file", "-t", sha],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() == "commit"


def classify(hits: list[tuple[str, int, str]]) -> dict[str, dict]:
    """Group hits by SHA and classify each.

    An exemption is **unanimous or it does not apply**: a SHA is ``foreign`` or
    ``exemplar`` only when *every* line citing it carries that marker. One
    undeclared argus-context cite keeps it in the defect set. The alternative —
    exempting on any single annotated site — would let one fenced line silence the
    same dead SHA everywhere else in the tree, which is the defect wearing the
    fix's clothes.
    """
    by_sha: dict[str, dict] = {}
    for path, lineno, text in hits:
        for sha in extract(text):
            entry = by_sha.setdefault(
                sha,
                {"sha": sha, "sites": [], "marked": {k: 0 for k in MARKERS}, "marked_sites": 0},
            )
            entry["sites"].append({"path": path, "line": lineno, "text": text.strip()})
            hit = False
            for kind, marker in MARKERS.items():
                if marker in text:
                    entry["marked"][kind] += 1
                    hit = True
            entry["marked_sites"] += 1 if hit else 0
    for entry in by_sha.values():
        n = len(entry["sites"])
        if resolves(entry["sha"]):
            entry["status"] = "live"
            continue
        # Unanimity is about COVERAGE, not about agreeing on a class. A sha can be a
        # foreign pin where it is used and an exemplar in this script's own fixtures;
        # both sites are exempt, and demanding one label would wrongly re-arm it.
        # What must hold is that no site is left unmarked.
        entry["status"] = "dead"
        if entry["marked_sites"] == n and n:
            entry["status"] = max(MARKERS, key=lambda k: entry["marked"][k])
    return by_sha


def assert_selector_covers_hits(
    hits: list[tuple[str, int, str]], by_sha: dict[str, dict], all_paths: set[str]
) -> list[str]:
    """Structural guard, per R9 — a post-condition, not an inspection note.

    Each arm fails on a state that would otherwise let this script print a clean
    number it did not earn:

    A. **No hit is silently dropped.** ``git grep`` matched the line, so the line
       contains a cite; if ``CITE_RE`` then extracts nothing from it, the grep
       pattern and the Python pattern have diverged and every count below is
       under-reported.

    B. **Classification is total.** Every SHA is exactly one of live/dead/foreign.
       An unclassified SHA would vanish from all three tallies and the totals would
       still look self-consistent.

    C. **``foreign`` is unanimous.** A SHA is only exempt when *every* citing line
       declares it foreign. One undeclared argus-context cite must keep it in the
       defect set, otherwise a single annotation anywhere silences a real defect
       everywhere.

    D. **No carve-out is stale.** A repair-scope exclusion that matches no path in
       the full scope narrows nothing while reading as though it narrows something.
       That is the silent-cap shape: the scope looks deliberately bounded and is in
       fact bounded by a typo.

    Deliberately NOT an arm: re-sweeping for backtick-wrapped hex without the word
    ``commit``. ``scripts/check_export_commit_cites.py`` (MAC-703) already ruled on
    that widening — ``coverage_report.md`` alone carries 999 bare-hex tokens that are
    ``argus_record_id`` values and BLE UUIDs, and a gate flagging those gets switched
    off within a day. The blind spot is real and is disclosed in the report rather
    than converted into a gate that cries wolf.
    """
    failures: list[str] = []

    for path, lineno, text in hits:  # arm A
        if not extract(text):
            failures.append(f"A: grep matched but no pattern extracted a sha at {path}:{lineno}")

    for sha, entry in sorted(by_sha.items()):  # arms B, C
        status = entry.get("status")
        if status not in {"live", "dead", *MARKERS}:
            failures.append(f"B: {sha} unclassified (status={status!r})")
        if status in MARKERS and entry["marked_sites"] != len(entry["sites"]):
            failures.append(
                f"C: {sha} exempted as {status} but only "
                f"{entry['marked_sites']}/{len(entry['sites'])} sites carry a marker"
            )

    for prefix in REPAIR_EXCLUSIONS:  # arm D
        if not any(p.startswith(prefix) for p in all_paths):
            failures.append(f"D: repair carve-out {prefix!r} matches no path in the full scope")

    return failures


def selftest() -> int:
    """R7 positive control — show the instrument firing on both arms.

    A zero from a scanner that was never shown to fire is a capability zero
    wearing a channel zero's clothes. Both arms run through the real ``classify``
    path, not a re-implementation of it.
    """
    head = _git("rev-parse", "HEAD").strip()
    synthetic = [
        # arm A: a known-live SHA must classify live
        ("synthetic/live.md", 1, f"landed at commit `{head[:7]}` in this repo"),
        # arm B: a known-dead SHA must classify dead
        ("synthetic/dead.md", 1, "landed at commit `0aa89a0` per the ledger"),  # dead-cite exemplar
        # arm C: a declared foreign pin must NOT count as dead
        (
            "synthetic/foreign.md",
            1,
            f"upstream pinned commit `d2468ad` ({FOREIGN_MARKER}; not an argus object)",  # dead-cite exemplar
        ),
        # arm D: a fenced exemplar must NOT count as dead
        (
            "synthetic/exemplar.md",
            1,
            f"the gate exists because a doc wrote commit `598460e` ({EXEMPLAR_MARKER})",  # dead-cite exemplar
        ),
        # arm E: the SAME sha unfenced must poison the exemption — a fence that can be
        # removed without consequence is not a fence.
        ("synthetic/unfenced.md", 1, "landed at commit `8850ca6` per the ledger"),  # dead-cite exemplar
        ("synthetic/fenced.md", 1, f"quoted as commit `8850ca6` ({EXEMPLAR_MARKER})"),  # dead-cite exemplar
        # arm F: the ledger header class, which FILED_RE structurally cannot see.
        # Without LEDGER_RE this line yields nothing and the sha reads as repaired.
        ("synthetic/ledger.md", 1, "**Commit:** `b2a8dac` — `docs(bible): correction pass 5`"),  # dead-cite exemplar
    ]
    got = classify(synthetic)
    expected = {
        head[:7]: "live",
        "0aa89a0": "dead",
        "d2468ad": "foreign",
        "598460e": "exemplar",
        "8850ca6": "dead",
        "b2a8dac": "dead",
    }
    failures = []
    for sha, want in expected.items():
        have = got.get(sha, {}).get("status")
        status = "PASS" if have == want else "FAIL"
        print(f"  {status}  {sha}  expected={want} got={have}")
        if have != want:
            failures.append(sha)

    # The guard must fail on an input it should reject, or it is decoration.
    mutated = assert_selector_covers_hits(
        [("synthetic/nocite.md", 1, "no cite token here")],
        {"zzzz": {"sha": "zzzz", "sites": [], "marked": {k: 0 for k in MARKERS}, "marked_sites": 0, "status": "bogus"}},
        set(),
    )
    fired = {f.split(":", 1)[0] for f in mutated}
    want_arms = {"A", "B", "D"}
    print(
        f"  {'PASS' if want_arms <= fired else 'FAIL'}  guard mutation fired arms "
        f"{sorted(fired)} (expected superset of {sorted(want_arms)})"
    )
    if not want_arms <= fired:
        failures.append("guard-mutation")

    if failures:
        print(f"selftest FAIL  MAC-704  ({len(failures)} arm(s) did not fire)")
        return 2
    print(f"selftest PASS  MAC-704  ({len(expected) + 1}/{len(expected) + 1} arms fired)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scope", choices=("repair", "full"), default="repair")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    all_hits = grep_lines()
    all_paths = {p for p, _, _ in all_hits}
    hits = all_hits
    if args.scope == "repair":
        hits = [h for h in hits if in_repair_scope(h[0]) is None]
    by_sha = classify(hits)

    # Arm D needs the FULL path set: a carve-out is stale if it matches nothing in
    # the whole selector, and it matches nothing in the repair scope by construction.
    missed = assert_selector_covers_hits(hits, by_sha, all_paths)

    live = sorted(s for s, e in by_sha.items() if e["status"] == "live")
    dead = sorted(s for s, e in by_sha.items() if e["status"] == "dead")
    foreign = sorted(s for s, e in by_sha.items() if e["status"] == "foreign")
    exemplar = sorted(s for s, e in by_sha.items() if e["status"] == "exemplar")

    if args.json:
        print(
            json.dumps(
                {
                    "scope": args.scope,
                    "head": _git("rev-parse", "HEAD").strip(),
                    "distinct": len(by_sha),
                    "live": live,
                    "dead": dead,
                    "foreign": foreign,
                    "exemplar": exemplar,
                    "guard_missed": missed,
                    "detail": by_sha,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"scope={args.scope}  head={_git('rev-parse', '--short', 'HEAD').strip()}")
        print(
            f"  distinct SHA tokens : {len(by_sha)}"
            f"   live={len(live)}  dead={len(dead)}"
            f"  foreign={len(foreign)}  exemplar={len(exemplar)}"
        )
        for label, group in (("DEAD", dead), ("FOREIGN", foreign), ("EXEMPLAR", exemplar)):
            for sha in group:
                first = by_sha[sha]["sites"][0]
                print(f"    {label:<8} {sha}  {first['path']}:{first['line']}")
        if args.scope == "full":
            residual = sorted(p for p in all_paths if in_repair_scope(p) is not None)
            print(f"  paths carved out of the repair scope: {len(residual)}")
            for prefix, reason in REPAIR_EXCLUSIONS.items():
                print(f"    carve-out  {prefix}  — {reason}")
        if missed:
            print(f"  GUARD: {len(missed)} structural failure(s):")
            for m in missed:
                print(f"    {m}")

    if missed:
        print(f"check_commit_cites: GUARD FAIL  MAC-704  ({len(missed)} structural failure(s))")
        return 2
    tally = (
        f"({{}} dead, {len(live)} live, {len(foreign)} foreign, "
        f"{len(exemplar)} exemplar, scope={args.scope})"
    )
    if dead:
        print(f"check_commit_cites: FAIL  MAC-704  {tally.format(len(dead))}")
        return 1
    print(f"check_commit_cites: PASS  MAC-704  {tally.format(0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
