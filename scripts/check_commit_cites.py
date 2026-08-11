#!/usr/bin/env python3
"""MAC-704 / MAC-710 — measure commit citations in tracked code and docs.

A SHA cited in prose is a coordinate into a history that can be rewritten. When it
is, the cite dangles and the reader loses the only handle they had on *why* a rule
exists. This script is the producing selector for that measurement, per
``operator_review/BRIEF_STANDARDS.md`` R9 — the number is not quotable unless the
script that emits it is committed and carries a structural guard.

Two cite classes, checked two different ways. A **sha** is resolved by lookup: it
either names an object or it does not. A **subject** is resolved by *search*, which
is why MAC-704's repair — replacing six dead ledger shas with commit subjects — could
not simply reuse the sha arm, and why for one commit it had no arm at all. MAC-710
filed that gap: the ledger's six most-read entries carried a handle nothing checked,
so the gate printed ``PASS`` over an anchor that could rot silently. Any claim that
this gate's dead count fell must read against both arms, or part of the delta is the
instrument losing sight of the thing it counts.

Four classifications for a cited SHA, and the distinctions past the first two are the
whole point:

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

Three more for a cited SUBJECT, because a search can fail in two directions where a
lookup fails in one:

``unique``    the subject matches exactly one commit. This is the only state in which
              a subject is a usable handle, and it is the state MAC-710 ratified as
              the boundary licensing a subject as a citation at all.
``rotted``    the subject matches no commit — a reword, a typo, a truncation. Same
              defect as a dead sha, reached by a different mechanism.
``ambiguous`` the subject matches two or more commits. A handle that resolves to a set
              is not a handle: the reader still cannot say which commit applied the
              amendment. Equally useless, so it fails on the same footing.

Matching is ``--fixed-strings --grep`` **followed by equality on ``%s``**. The grep
alone is a substring match over the whole message, so a subject quoted inside some
later commit's body — this gate's own commit message, for one — would satisfy it. The
equality filter is what makes the resolution mean *this commit*, not *some commit that
mentions it*.

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

Exit codes: ``0`` no broken cites in scope, ``1`` dead shas or non-unique subject
anchors remain, ``2`` the structural guard or the positive control failed (the
instrument is untrustworthy; its zero means nothing).
"""

from __future__ import annotations

import argparse
import functools
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

# MAC-710 — the third cite class, and the one MAC-704 created. The six repaired ledger
# entries carry `**Commit:** subject `<subject>`` instead of a sha. That form matches
# neither pattern above (after `**Commit:** ` comes the word `subject`, not hex), so
# before this arm existed the gate could not see it *at all*: it stopped counting those
# six as dead and printed PASS over a handle nothing checked.
#
# Anchored at line start on purpose. It is what separates a ledger *header* from a line
# that merely discusses the form — including the fixtures in this file's own selftest,
# which sit indented inside a Python tuple and therefore cannot match. A scanner whose
# corpus contains write-ups about itself needs that boundary drawn structurally, not by
# a path allowlist that goes stale.
LEDGER_SUBJECT_RE = re.compile(r"^\*\*Commit:\*\* +subject +`([^`]+)`")

# Every ledger header, whatever it carries. Guard arm E reads this: a header that yields
# no cite of any class is the drift that would make the subject arm silently vacuous.
LEDGER_HEADER_RE = re.compile(r"^\*\*Commit:\*\*")

# R3 — the established self-referential placeholder (CP31 §5 precedent). A header
# carrying it is citing the commit that introduced it and resolves via `git log <path>`.
SELF_REF_PLACEHOLDER = "<this-commit>"


def extract(text: str) -> list[str]:
    """Every SHA cited on one line, across all cite classes."""
    out: list[str] = []
    for pat in CITE_PATTERNS:
        out.extend(pat.findall(text))
    return out


def extract_subjects(text: str) -> list[str]:
    """Every commit *subject* cited on one line."""
    return LEDGER_SUBJECT_RE.findall(text)

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
# NOT listed, deliberately: `exports/`. It carried a carve-out until MAC-716, held for
# exactly one defect — the dead `6853780` commit cite at `exports/coverage_report.md:34`.
# MAC-703 repaired that at the producer rather than at the gate: `export_lynceus.py:2099`
# re-derives `matrix_sha256` from the same bytes it embeds, on every write. A commit cite
# needed an external gate because the object graph moves underneath it; a content hash
# re-derived at write time from the embedded bytes has no external object whose lifetime
# it can outlive, so the export surface is owed no carve-out. Retiring the carve-out
# widens coverage rather than narrowing it: `exports/` re-enters the repair scope, so a
# writer change that reintroduces a dead commit cite into a generated artifact is caught
# by arms A/B instead of suppressed.
#
# NOT listed, deliberately: `db/validation/export_lynceus.py`. The MAC-45 provenance
# lane holds it dirty and its line 1596 discusses `6853780`, but it writes the sha
# double-backticked (``6853780``) so the selector never matches it. Adding a carve-out
# for a path the selector cannot reach is the stale-carve-out defect arm D exists to
# catch — it was tried here first, and arm D rejected it.
REPAIR_EXCLUSIONS = {
    "docs/internal/": "append-only heartbeat log; ratified verbatim prose is not edited in place",
    "operator_review/": "ratified operator artifacts; verbatim prose is not edited in place",
}


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    )
    return proc.stdout


def _grep(*patterns: str) -> list[tuple[str, int, str]]:
    """(path, lineno, text) for every tracked ``*.py``/``*.md`` line matching any pattern."""
    argv = ["grep", "-nE"]
    for pat in patterns:
        argv += ["-e", pat]
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


def grep_lines() -> list[tuple[str, int, str]]:
    """Run the filed selector and return (path, lineno, text) for every hit."""
    return _grep(*(p.pattern for p in CITE_PATTERNS), LEDGER_SUBJECT_RE.pattern)


def ledger_header_lines() -> list[tuple[str, int, str]]:
    """Every ``**Commit:**`` header line, cited or not — guard arm E's denominator."""
    return _grep(LEDGER_HEADER_RE.pattern)


def in_repair_scope(path: str) -> str | None:
    """Return the carve-out reason if ``path`` is outside the repair scope."""
    for prefix, reason in REPAIR_EXCLUSIONS.items():
        if path.startswith(prefix):
            return reason
    return None


@functools.lru_cache(maxsize=None)
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


@functools.lru_cache(maxsize=None)
def resolve_subject(subject: str) -> tuple[str, ...]:
    """Commits whose subject line equals ``subject`` **exactly**.

    Two stages, and dropping either one breaks the check in a different direction:

    ``--fixed-strings --grep``  a literal search, so a subject full of ``§``, ``—``,
                                parentheses and ``+`` is not read as a regex. Without
                                ``-F`` a real ledger subject silently matches nothing.
    equality on ``%s``          ``--grep`` matches anywhere in the *whole message*, so
                                a subject quoted in some later commit's body — the
                                commit that landed this gate, for instance, whose
                                message pastes the selftest output — would satisfy it
                                and a rotted anchor would read as live. Only the first
                                line is the subject, so only ``%s`` equality answers
                                "which commit applied this".

    Returns every match, not a boolean: zero and two-or-more are different defects and
    the caller has to tell them apart.
    """
    out = _git("log", "--all", "--format=%H%x00%s", "--fixed-strings", "--grep", subject)
    found: list[str] = []
    for line in out.splitlines():
        sha, sep, subj = line.partition("\x00")
        if sep and subj == subject:
            found.append(sha)
    return tuple(found)


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


SUBJECT_STATUSES = ("unique", "rotted", "ambiguous")
SUBJECT_BROKEN = ("rotted", "ambiguous")


def classify_subjects(hits: list[tuple[str, int, str]]) -> dict[str, dict]:
    """Group subject anchors and classify each by how many commits it resolves to.

    ``unique`` is the only passing state. ``rotted`` (0) is the obvious failure; so is
    ``ambiguous`` (≥2), because the whole reason MAC-704 preferred a subject over a sha
    is that a reader can *retrieve* the commit from it, and a subject naming three
    commits retrieves nothing. The CEO ruling at MAC-710 makes uniqueness the property
    that licenses a subject as a citation, so both sides fail.

    The ``exemplar`` fence carries over from the sha arm unchanged, including its
    unanimity rule: a subject is exempt only when *every* line citing it is fenced. A
    doc that quotes the anchor form to explain it must not thereby silence the real
    anchor of the same subject elsewhere.
    """
    by_subject: dict[str, dict] = {}
    for path, lineno, text in hits:
        for subject in extract_subjects(text):
            entry = by_subject.setdefault(
                subject,
                {"subject": subject, "sites": [], "marked_sites": 0, "matches": []},
            )
            entry["sites"].append({"path": path, "line": lineno, "text": text.strip()})
            if EXEMPLAR_MARKER in text or FOREIGN_MARKER in text:
                entry["marked_sites"] += 1
    for entry in by_subject.values():
        n = len(entry["sites"])
        if entry["marked_sites"] == n and n:
            entry["status"] = "exemplar"
            entry["matches"] = []
            continue
        matches = resolve_subject(entry["subject"])
        entry["matches"] = list(matches)
        if len(matches) == 1:
            entry["status"] = "unique"
        elif not matches:
            entry["status"] = "rotted"
        else:
            entry["status"] = "ambiguous"
    return by_subject


def assert_selector_covers_hits(
    hits: list[tuple[str, int, str]],
    by_sha: dict[str, dict],
    all_paths: set[str],
    by_subject: dict[str, dict] | None = None,
    headers: list[tuple[str, int, str]] | None = None,
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

    E. **No ledger header is uncited** (MAC-710). Every line opening ``**Commit:**``
       must yield a sha, a subject anchor, the ``<this-commit>`` placeholder, or an
       exemplar fence. This is the arm that keeps the subject check from going
       vacuous: reword the six repaired headers into a form ``LEDGER_SUBJECT_RE`` no
       longer matches and the subject tally silently drops to zero while every other
       number stays green — a capability zero wearing a channel zero's clothes. Arm E
       fires on the header instead, because a header is a header however it is
       phrased.

    F. **Subject classification is total** (MAC-710). Every subject anchor is exactly
       one of unique/rotted/ambiguous/exemplar, for the same reason as arm B: an
       unclassified subject vanishes from all four tallies and the totals still add up.

    Deliberately NOT an arm: re-sweeping for backtick-wrapped hex without the word
    ``commit``. ``scripts/check_export_commit_cites.py`` (MAC-703) already ruled on
    that widening — ``coverage_report.md`` alone carries 999 bare-hex tokens that are
    ``argus_record_id`` values and BLE UUIDs, and a gate flagging those gets switched
    off within a day. The blind spot is real and is disclosed in the report rather
    than converted into a gate that cries wolf.
    """
    failures: list[str] = []
    by_subject = by_subject if by_subject is not None else {}

    # Arm A widened at MAC-710: the grep now also carries the subject pattern, so a
    # line that legitimately cites a subject and no sha is a hit with zero shas. Before
    # the widening this arm would have fired on all six repaired ledger headers.
    for path, lineno, text in hits:  # arm A
        if not extract(text) and not extract_subjects(text):
            failures.append(f"A: grep matched but no pattern extracted a cite at {path}:{lineno}")

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

    for path, lineno, text in headers or []:  # arm E
        cited = bool(extract(text) or extract_subjects(text))
        if not cited and SELF_REF_PLACEHOLDER not in text and EXEMPLAR_MARKER not in text:
            failures.append(
                f"E: ledger header at {path}:{lineno} carries no sha, no subject anchor "
                f"and no {SELF_REF_PLACEHOLDER} placeholder"
            )

    for subject, entry in sorted(by_subject.items()):  # arm F
        status = entry.get("status")
        if status not in {*SUBJECT_STATUSES, "exemplar"}:
            failures.append(f"F: subject {subject!r} unclassified (status={status!r})")

    return failures


# R7 fixtures for the subject arm. Literal strings, because their whole job is to name
# something the object graph does not contain — deriving "a subject that matches no
# commit" from the object graph is not possible by construction.
#
# Safe against this gate's own commit: `resolve_subject` matches on `%s` equality, so
# even though the commit landing this file pastes the selftest output — these very
# strings — into its message body, they are not its subject line and the fixtures stay
# at zero matches. That is the equality filter earning its place, not a coincidence.
ROTTED_SUBJECT_FIXTURE = "MAC-710 selftest fixture: a subject that matches no commit (xyzzy)"
FENCED_SUBJECT_FIXTURE = "MAC-710 selftest fixture: a fenced subject, quoted not asserted (xyzzy)"
POISON_SUBJECT_FIXTURE = "MAC-710 selftest fixture: a subject fenced at one site only (xyzzy)"


def _subject_tally() -> dict[str, int]:
    """How many commits carry each subject, over all refs."""
    tally: dict[str, int] = {}
    for line in _git("log", "--all", "--format=%s").splitlines():
        tally[line] = tally.get(line, 0) + 1
    return tally


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

    # ---- MAC-710: the subject arm, both directions -------------------------------
    #
    # The unique and ambiguous fixtures are DERIVED from the object graph rather than
    # written down. A literal "this subject is unique" fixture stops being true the day
    # someone reuses the wording, and R9 bans a literal set whose dropped member changes
    # the answer. `sorted()[0]` keeps the pick deterministic across runs.
    tally = _subject_tally()
    unique_subjects = sorted(s for s, n in tally.items() if n == 1)
    dup_subjects = sorted(s for s, n in tally.items() if n > 1)
    if not unique_subjects or not dup_subjects:
        # A control that cannot be constructed did not pass; it did not run. Exit 2,
        # never 0 — an unevaluated arm printing PASS is the defect this file exists for.
        print(
            "  FAIL  subject control not constructible: "
            f"{len(unique_subjects)} unique / {len(dup_subjects)} duplicate subjects in history"
        )
        print("selftest FAIL  MAC-710  (subject positive control could not be built)")
        return 2

    subject_fixtures = [
        # arm G: a subject matching exactly one commit is the only usable handle.
        ("synthetic/subject_unique.md", 1, f"**Commit:** subject `{unique_subjects[0]}`"),
        # arm H: zero matches — the rotted anchor. This is the state that passed green
        # before MAC-710, because nothing read the subject at all.
        ("synthetic/subject_rotted.md", 1, f"**Commit:** subject `{ROTTED_SUBJECT_FIXTURE}`"),
        # arm I: two or more matches — the ambiguous anchor. Equally useless as a
        # handle, so it must fail on the same footing rather than pass as "found".
        ("synthetic/subject_dup.md", 1, f"**Commit:** subject `{dup_subjects[0]}`"),
        # arm J: a fenced subject is quoted, not asserted, and must not count.
        (
            "synthetic/subject_fenced.md",
            1,
            f"**Commit:** subject `{FENCED_SUBJECT_FIXTURE}` ({EXEMPLAR_MARKER})",
        ),
        # arm K: the same subject unfenced elsewhere must poison the exemption, exactly
        # as it does on the sha arm. A fence removable without consequence is not one.
        ("synthetic/subject_poison_a.md", 1, f"**Commit:** subject `{POISON_SUBJECT_FIXTURE}`"),
        (
            "synthetic/subject_poison_b.md",
            1,
            f"**Commit:** subject `{POISON_SUBJECT_FIXTURE}` ({EXEMPLAR_MARKER})",
        ),
    ]
    got_subjects = classify_subjects(subject_fixtures)
    expected_subjects = {
        unique_subjects[0]: "unique",
        ROTTED_SUBJECT_FIXTURE: "rotted",
        dup_subjects[0]: "ambiguous",
        FENCED_SUBJECT_FIXTURE: "exemplar",
        POISON_SUBJECT_FIXTURE: "rotted",
    }
    for subject, want in expected_subjects.items():
        entry = got_subjects.get(subject, {})
        have = entry.get("status")
        status = "PASS" if have == want else "FAIL"
        print(
            f"  {status}  subject expected={want} got={have} "
            f"matches={len(entry.get('matches', []))}  {subject[:56]!r}"
        )
        if have != want:
            failures.append(f"subject:{want}")

    # An arm that cannot move the classified value proves nothing. Same classifier, two
    # cohorts: with the broken fixtures the gate has something to fail on, and with only
    # the unique fixture it has nothing. The control cohort is deliberately NON-EMPTY —
    # a counterfactual run over an empty set prints clean for the wrong reason.
    broken = [s for s, e in got_subjects.items() if e["status"] in SUBJECT_BROKEN]
    control = classify_subjects([subject_fixtures[0]])
    control_broken = [s for s, e in control.items() if e["status"] in SUBJECT_BROKEN]
    flipped = len(broken) > 0 and len(control_broken) == 0 and len(control) > 0
    print(
        f"  {'PASS' if flipped else 'FAIL'}  verdict flip: broken={len(broken)} with the "
        f"rotted+ambiguous fixtures, {len(control_broken)} over a {len(control)}-anchor "
        f"control of the unique fixture alone"
    )
    if not flipped:
        failures.append("subject-verdict-flip")

    # The guard must fail on an input it should reject, or it is decoration.
    mutated = assert_selector_covers_hits(
        [("synthetic/nocite.md", 1, "no cite token here")],
        {"zzzz": {"sha": "zzzz", "sites": [], "marked": {k: 0 for k in MARKERS}, "marked_sites": 0, "status": "bogus"}},
        set(),
        by_subject={
            "zzzz subject": {
                "subject": "zzzz subject",
                "sites": [],
                "marked_sites": 0,
                "matches": [],
                "status": "bogus",
            }
        },
        headers=[("synthetic/header.md", 1, "**Commit:** landed somewhere, no handle at all")],
    )
    fired = {f.split(":", 1)[0] for f in mutated}
    want_arms = {"A", "B", "D", "E", "F"}
    print(
        f"  {'PASS' if want_arms <= fired else 'FAIL'}  guard mutation fired arms "
        f"{sorted(fired)} (expected superset of {sorted(want_arms)})"
    )
    if not want_arms <= fired:
        failures.append("guard-mutation")

    total = len(expected) + len(expected_subjects) + 2
    if failures:
        print(f"selftest FAIL  MAC-710  ({len(failures)}/{total} arm(s) did not fire)")
        return 2
    print(f"selftest PASS  MAC-710  ({total}/{total} arms fired)")
    return 0


def carve_out_disclosure(
    all_hits: list[tuple[str, int, str]],
    scope_broken: set[str],
) -> dict:
    """What the repair carve-outs are holding — computed once, printed under EVERY scope.

    MAC-710 deliverable 3. Before it, ``--scope repair`` printed ``PASS`` and stopped,
    while 35 dead cites sat in three carved-out trees. A carve-out disclosed only in the
    scope that does not apply it is not disclosed: the reader who runs the default gets
    a green line and no way to know it is green over a subset.

    Two different numbers, both needed:

    ``held``    broken cites with at least one site under a carve-out. Answers "what is
                in there", and is the same figure at either scope.
    ``hidden``  ``held`` minus what the current scope already reports. Answers "what
                does this particular green line not cover" — zero at ``--scope full``,
                which is exactly the difference the reader is entitled to see.

    Per-carve-out counts may overlap when one cite is cited from two trees, so the
    totals are distinct unions and not the sum of the rows. Stated, because a row set
    that does not add up reads as an arithmetic error unless you say why.
    """
    full_by_sha = classify(all_hits)
    full_by_subject = classify_subjects(all_hits)
    sites_of: dict[str, list[dict]] = {}
    for key, entry in full_by_sha.items():
        if entry["status"] == "dead":
            sites_of[key] = entry["sites"]
    for key, entry in full_by_subject.items():
        if entry["status"] in SUBJECT_BROKEN:
            sites_of[key] = entry["sites"]

    rows = []
    for prefix, reason in REPAIR_EXCLUSIONS.items():
        inside = sorted(
            k for k, sites in sites_of.items() if any(s["path"].startswith(prefix) for s in sites)
        )
        dead_sha = [k for k in inside if k in full_by_sha]
        broken_subject = [k for k in inside if k in full_by_subject]
        rows.append(
            {
                "prefix": prefix,
                "reason": reason,
                "dead_sha": dead_sha,
                "broken_subject": broken_subject,
                "paths": sorted(
                    {p for p, _, _ in all_hits if p.startswith(prefix)}
                ),
            }
        )

    held = sorted(
        k for k, sites in sites_of.items() if any(in_repair_scope(s["path"]) for s in sites)
    )
    return {
        "carve_outs": rows,
        "held": held,
        "hidden_from_this_scope": sorted(set(held) - scope_broken),
    }


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
    headers = ledger_header_lines()
    hits = all_hits
    if args.scope == "repair":
        hits = [h for h in hits if in_repair_scope(h[0]) is None]
    by_sha = classify(hits)
    by_subject = classify_subjects(hits)

    # Arm D needs the FULL path set: a carve-out is stale if it matches nothing in
    # the whole selector, and it matches nothing in the repair scope by construction.
    # Arm E likewise reads every header, not the scoped subset: a header rewritten into
    # an unrecognised form inside a carve-out is still the selector losing its grip.
    missed = assert_selector_covers_hits(hits, by_sha, all_paths, by_subject, headers)

    live = sorted(s for s, e in by_sha.items() if e["status"] == "live")
    dead = sorted(s for s, e in by_sha.items() if e["status"] == "dead")
    foreign = sorted(s for s, e in by_sha.items() if e["status"] == "foreign")
    exemplar = sorted(s for s, e in by_sha.items() if e["status"] == "exemplar")

    subj = {k: sorted(s for s, e in by_subject.items() if e["status"] == k)
            for k in (*SUBJECT_STATUSES, "exemplar")}
    broken_subjects = sorted({*subj["rotted"], *subj["ambiguous"]})

    disclosure = carve_out_disclosure(all_hits, {*dead, *broken_subjects})
    held, hidden = disclosure["held"], disclosure["hidden_from_this_scope"]

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
                    "subjects": subj,
                    "subject_detail": by_subject,
                    "carve_out_disclosure": disclosure,
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
        print(
            f"  subject anchors     : {len(by_subject)}"
            f"   unique={len(subj['unique'])}  rotted={len(subj['rotted'])}"
            f"  ambiguous={len(subj['ambiguous'])}  exemplar={len(subj['exemplar'])}"
            f"   ({len(headers)} ledger headers scanned)"
        )
        for label, group in (("DEAD", dead), ("FOREIGN", foreign), ("EXEMPLAR", exemplar)):
            for sha in group:
                first = by_sha[sha]["sites"][0]
                print(f"    {label:<8} {sha}  {first['path']}:{first['line']}")
        for label, key in (("ROTTED", "rotted"), ("AMBIGUOUS", "ambiguous")):
            for subject in subj[key]:
                entry = by_subject[subject]
                first = entry["sites"][0]
                print(
                    f"    {label:<9} {first['path']}:{first['line']}  "
                    f"{len(entry['matches'])} match(es)  {subject!r}"
                )

        # Deliverable 3 — printed under EVERY scope, so a green line can never be read
        # as full coverage. `hidden` is the number the default scope was silent about.
        print(
            f"  repair-scope carve-outs: {len(REPAIR_EXCLUSIONS)} path prefixes holding "
            f"{len(held)} broken cite(s); {len(hidden)} of them invisible at scope={args.scope}"
        )
        for row in disclosure["carve_outs"]:
            print(
                f"    carve-out  {row['prefix']:<18} "
                f"{len(row['dead_sha'])} dead sha, {len(row['broken_subject'])} broken subject, "
                f"{len(row['paths'])} cited path(s)  — {row['reason']}"
            )
        print(
            "    (per-carve-out counts may overlap; the totals above are distinct unions, "
            "not row sums)"
        )
        if missed:
            print(f"  GUARD: {len(missed)} structural failure(s):")
            for m in missed:
                print(f"    {m}")

    if missed:
        print(f"check_commit_cites: GUARD FAIL  MAC-704  ({len(missed)} structural failure(s))")
        return 2
    tally = (
        f"({{}} dead, {len(live)} live, {len(foreign)} foreign, "
        f"{len(exemplar)} exemplar, {{}} broken subject, {len(subj['unique'])} unique subject, "
        f"{len(held)} carved out, scope={args.scope})"
    )
    if dead or broken_subjects:
        print(
            "check_commit_cites: FAIL  MAC-704  "
            + tally.format(len(dead), len(broken_subjects))
        )
        return 1
    print("check_commit_cites: PASS  MAC-704  " + tally.format(0, 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
