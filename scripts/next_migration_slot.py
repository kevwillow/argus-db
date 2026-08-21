#!/usr/bin/env python3
"""Derive the next free migration slot from BOTH the filesystem and the reservation layer.

Four lanes in a row picked a colliding slot number (MAC-537 -> 0043, MAC-523 -> 0043,
MAC-537 -> 0045, and the CEO's "0046 or higher" on 2026-07-29). Every one of them was a correct
`ls db/migrations/` read. The number is claimed at *dispatch* and only becomes a file at *apply*,
so between those two moments the slot is invisible on disk — a filesystem read is necessary and
never sufficient.

MAC-674: the first version of this tool floored its own claim scan at `max(applied files)` on the
premise that "below the highest file every slot is already a committed file, so a mention there is
history, not a claim". That premise is false whenever an apply lands out of order, which is the
exact situation the tool exists to handle. On 2026-08-11 slots 0046/0047/0050 were live claims
sitting in the gap below file 0052, the scan skipped all three, and the tool told MAC-574, MAC-598
and MAC-608 — each already holding a distinct slot — that they held nothing and should all take
0053. It was not a weak detector, it was a collision generator. The window is gone: the scan now
covers the full range and a gap below the highest file is CONTESTED, not history.

Three kinds of text mention a slot and only one of them reserves it:

    CLAIM     "MAC-598 reserves `0047`"                        <- reserves
    ECHO      "MAC-608 holds no slot yet; claim 0050 ..."      <- this tool's own stdout, pasted
    NEGATIVE  "0051 FREE  MAC-606 ... ruled 'allocate nothing yet'"

Attributing an ECHO or a NEGATIVE is how a proof artifact poisons the next lane's scan, so both are
classified out of the claim set (and counted in the report — suppression is never silent).

MAC-684: the tool could express a claim but not a RELEASE, so a slot that a ruling freed kept
reading `CONTESTED unresolved` forever. See the release-pragma block below `NEGATIVE_RE` for why
the prose layer is structurally incapable of fixing that, and what the pragma does instead.

    python3 scripts/next_migration_slot.py                     # full-range claim report
    python3 scripts/next_migration_slot.py --claim MAC-608     # ... and reconcile one issue
    python3 scripts/next_migration_slot.py --claim MAC-700 --slot 0046   # assert a specific slot
    python3 scripts/next_migration_slot.py --selftest          # positive control, see below

Exit codes (a bitmask):
    0  the proposed slot is free and the issue holds nothing else
    1  the named issue ALREADY HOLDS a slot -- use it or release it, do not take a new one
    2  the proposed slot is HELD BY SOMEONE ELSE
    4  a `slot-release:` pragma did NOT take effect (unmatched, refused or malformed). This bit is
       OR'd in on a plain report run too, with no `--claim`: a release that failed silently leaves
       a slot contested that somebody has already been told is free.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "db" / "migrations"
DRAFTS = MIGRATIONS / "_drafts"
# Prose layers where a slot is reserved before the file exists.
SCAN_DIRS = ["operator_review", "docs"]
PROSE_GLOBS = ["*.md"]
# A CEILING, never a floor. Slots are allocated densely and nobody claims 20 ahead, so a
# 4-digit number far above the highest file is a line cite or a row id, not a slot. Read the
# MAC-674 note above before touching this: the defect was a FLOOR at the highest applied file,
# which hid claims sitting BELOW it. Dropping the ceiling only adds noise; adding a floor
# re-opens the collision. Every mention the ceiling drops is counted in the report.
LOOKAHEAD = 20

ISSUE_RE = re.compile(r"\bMAC[-_ ]?(\d{3,4})\b", re.I)
# A slot in migration-filename form binds slot <-> issue with no ambiguity: `0046_mac574_....sql`.
FILENAME_RE = re.compile(r"\b(\d{4})_mac(\d{3,4})_[a-z0-9_]*\.sql\b", re.I)
# A slot behind an explicit migration word.
ANCHORED_RE = re.compile(
    r"\b(?:mig-|migrations/|migration\s+(?:number|slot)\s+`?|slots?\s+`?)(\d{4})\b", re.I)
# A bare 4-digit number counts as a slot mention only on a line that is already talking about
# migration slots. Without this guard "0046 CLAIMED MAC-574" is invisible; with it, arbitrary
# 4-digit numbers elsewhere in the corpus are not swept in.
BARE_RE = re.compile(r"(?<![\w.-])(\d{4})(?![\w.-])")
SLOT_CONTEXT_RE = re.compile(
    r"\b(?:slot|migration|mig-|db/migrations|CLAIMED|RESERVED|APPLIED|STAGED|DRAFT)\b", re.I)

# Verbatim signatures of this tool's own stdout. A pasted report is not a reservation. Only
# strings this tool emits and prose never contains -- "MAC-574 already holds 0046" is a sentence
# a human writes, so it stays a claim.
ECHO_RE = re.compile(
    r"naive next \(WRONG\)|next free slot|highest file on disk|holds no slot yet|"
    r"already appears at slot|reconcile before writing|claim \d{4} in a committed file|"
    r"FULL-RANGE claim scan|python3 scripts/next_migration_slot\.py|"
    r"scripts/next_migration_slot\.py --claim|mentions dropped|POSITIVE CONTROL|"
    r"no-collision:|-> do NOT take|-> CONFIRMED:|is NOT free:|"
    r"gaps below the highest applied file|"
    # MAC-684 release-report signatures. `slot release ledger` is deliberately three words: bare
    # "release ledger" already appears twice in the corpus meaning CHANGELOG.md, and swallowing
    # those lines would be a silent scope change. `[release]` prefixes every ledger row so a
    # pasted ledger cannot mint a PATH-tier claim out of the slot number it is reporting on.
    r"slot release ledger|slot releases\s*:|\[release\]|slot-release\s*:", re.I)
# A file may declare itself non-authoritative. A post-hoc analysis that QUOTES a claim -- a
# ratification, a defect write-up, this issue's own proof -- is not making one, and regexes cannot
# tell the difference reliably: MAC-674's proof narrated a wrong verdict ("the tool reported
# `0053 CLAIMED MAC-663`") and thereby recreated it. Fenced files are named in the report, so the
# fence can never hide a claim silently.
#
# It is a HEADER pragma, matched only in FENCE_LINES. Matching it anywhere re-runs the same
# quoting-vs-asserting bug one level up: a document that merely DESCRIBES the fence fences itself,
# which is how MAC-674's own non-vacuity control first came back vacuous.
FENCE_RE = re.compile(r"slot-scan:\s*ignore", re.I)
FENCE_LINES = 5
# A line asserting a slot is NOT taken, or that a lane deliberately took nothing.
NEGATIVE_RE = re.compile(
    r"\b(?:is|are|was|were)\s+free\b|\bFREE\b(?!\w)|\bunclaimed\b|\bno\s+(?:other\s+)?claim(?:ant)?s?\b|"
    r"\bnot\s+claimed\b|\ballocate\s+nothing\b|\breturned\s+none\b|\bholds\s+no\s+slot\b|"
    r"\bnothing\s+claimed\b|\bavailable\b", re.I)
# A line that binds a slot to an issue with a reservation verb.
DECLARATIVE_RE = re.compile(
    r"\b(?:reserv\w*|claim(?:s|ed|ing)?|holds?|held|takes?|taken|owns?|allocat\w*|"
    r"assigned?|moves?\s+to|moved\s+to)\b", re.I)

# --- the release pragma (MAC-684) ---------------------------------------------------------
# There was a verb for claiming a slot and none for releasing one, so a slot a ruling freed read
# `CONTESTED unresolved` forever. The prose layer cannot close this and no amount of wording will:
# `scan_prose()` drops a NEGATIVE line BEFORE it creates evidence, so a negative sentence
# suppresses its own line and nothing else, and `resolve()` aggregates every `Ev` without ever
# seeing a retraction. A co-mention on a ratified line therefore outlives any correction that does
# not edit that line -- and editing it is exactly what the amend ban forbids. Only code closes it.
#
#     <!-- slot-scan: ignore -->
#     <!-- slot-release: 0053 MAC-663 operator_review/MAC-663/CEO_RATIFICATION.md:179 "deliberately skipped" -->
#
# A release retracts exactly ONE cited piece of evidence. It can never free a slot by assertion,
# which is the failure that would be worse than the phantom it fixes:
#
#   * It names the slot, the issue whose mention it retracts, the exact `path:line`, AND a verbatim
#     substring of that line. Writing one requires having READ the claim -- cite-paste, not cite.
#     A stale line number fails CLOSED: the release goes UNMATCHED, the slot stays contested, and
#     the ledger says which cite went stale.
#   * It can never reach APPLIED or DRAFT evidence. A file on disk is released by deleting or
#     renaming the file, never by prose. This is what stops a release from stealing a live claim:
#     MAC-608 holds `0050` as a draft file, and no pragma anywhere can move it.
#   * It retracts one `Ev`. A slot held by three mentions needs three cited releases, each one its
#     own ledger row. There is no blanket "0053 is free".
#   * It is honored only from the cited claim's OWN issue directory, so a release lands beside the
#     claim it retracts and the next reader of that directory cannot miss it.
#   * It is a HEADER pragma, matched only in FENCE_LINES, for the same reason `slot-scan: ignore`
#     is: matched anywhere, a document that merely DESCRIBES a release would perform one.
#   * The release document must ALSO carry `slot-scan: ignore`. A release document is not a claim
#     document, and auto-fencing it would quietly make `slot-release:` a second way to silence a
#     file's claims. One fencing verb, declared out loud.
#
# Every release appears in the ledger with its disposition -- HONORED, UNMATCHED, REFUSED,
# MALFORMED -- and a fully released slot keeps its own report line and its own state. Silent
# absence would read identical to "never mentioned", and no silent caps is the standing rule.
#
# A RELEASED slot does NOT re-enter the auto-handout path. It becomes an ordinary gap under the
# rule this tool already prints: reclaiming a gap is a deliberate, named decision.
RELEASE_ANY_RE = re.compile(r"slot-release\s*:", re.I)
RELEASE_RE = re.compile(
    r"slot-release\s*:\s*(\d{4})\s+(MAC[-_ ]?\d{3,4})\s+(\S+?)(?::(\d+))?\s+\"([^\"]+)\"", re.I)

# Evidence strength. Only STRONG tiers name a holder; WEAK tiers only make a slot contested.
APPLIED, DRAFT, FILENAME, DECLARATIVE, COMENTION, PATH, UNATTRIBUTED = (
    "APPLIED", "DRAFT", "FILENAME", "DECLARATIVE", "CO-MENTION", "PATH", "UNATTRIBUTED")
STRONG = (APPLIED, DRAFT, FILENAME, DECLARATIVE)
RANK = {APPLIED: 0, DRAFT: 1, FILENAME: 2, DECLARATIVE: 3, COMENTION: 4, PATH: 5, UNATTRIBUTED: 6}


class Ev:
    """One piece of evidence that a slot is spoken for."""

    def __init__(self, slot, tier, issue, where, text, full=None):
        self.slot, self.tier, self.issue, self.where, self.text = slot, tier, issue, where, text
        # `text` is truncated for display; `full` is what a release anchor is matched against, so
        # an anchor past column 100 still verifies.
        self.full = text if full is None else full
        self.released = None  # set to the Release that retracted this mention

    @property
    def strong(self):
        return self.tier in STRONG


class Release:
    """One `slot-release:` header pragma: a targeted retraction of ONE cited claim."""

    def __init__(self, doc, line_no, raw, slot=None, issue=None, path=None, line=None, anchor=None):
        self.doc, self.line_no, self.raw = doc, line_no, raw
        self.slot, self.issue, self.path, self.line, self.anchor = slot, issue, path, line, anchor
        self.where = (f"{path}:{line}" if line else path) if path else None
        self.disposition, self.detail, self.retracted = "PENDING", "", []

    @property
    def took_effect(self):
        return self.disposition == "HONORED"


def parse_release(doc, line_no, raw):
    """A header line mentioning the pragma always yields a Release, even when it does not parse.
    A pragma that is silently ignored is the one failure mode a release must never have."""
    m = RELEASE_RE.search(raw)
    if not m:
        r = Release(doc, line_no, raw)
        r.disposition = "MALFORMED"
        r.detail = ('expected `slot-release: NNNN MAC-NNN path:line "verbatim anchor"` -- got '
                    f'{raw.strip()[:90]}')
        return r
    return Release(doc, line_no, raw, slot=int(m.group(1)), issue=norm(ISSUE_RE.search(
        m.group(2)).group(1)), path=m.group(3), line=int(m.group(4)) if m.group(4) else None,
        anchor=m.group(5))


def apply_releases(releases, evidence, fenced):
    """Match every release against the full evidence pool and mark what it retracts.

    Fail-closed at each step: anything short of an exact match retracts nothing and is reported.
    The order of the checks is the order of the guarantees -- a release is refused for WHERE it
    was declared before it is ever allowed to look at what it targets, so a cross-lane pragma
    cannot even probe another lane's evidence by watching the disposition change."""
    for r in releases:
        if r.disposition == "MALFORMED":
            continue
        if r.doc not in fenced:
            r.disposition = "REFUSED"
            r.detail = ("the release document must also carry `slot-scan: ignore` in its header; "
                        "a release document is not a claim document")
            continue
        home = path_issue(r.path) or r.issue
        if path_issue(r.doc) != home:
            r.disposition = "REFUSED"
            r.detail = (f"cross-lane: a mention living in {home}'s document is released from "
                        f"{home}'s own directory, not from {r.doc}")
            continue
        exact = [e for e in evidence
                 if e.slot == r.slot and e.issue == r.issue and e.where == r.where]
        onfile = [e for e in exact if e.tier in (APPLIED, DRAFT)]
        if onfile:
            r.disposition = "REFUSED"
            r.detail = (f"[{onfile[0].tier}] {onfile[0].where} is a file on disk -- release it by "
                        "deleting or renaming the file; prose can never retract it")
            continue
        anchored = [e for e in exact if r.anchor in e.full]
        if not anchored:
            r.disposition = "UNMATCHED"
            r.detail = (f"nothing at {r.where} claims {r.slot:04d} for {r.issue}"
                        if not exact else
                        f"the cite matches, but the anchor {r.anchor!r} is not a substring of "
                        "that line -- the line moved or was rewritten")
            continue
        for e in anchored:
            e.released = r
        r.disposition = "HONORED"
        r.detail = f"{len(anchored)} mention(s) of {r.slot:04d} retracted at {r.where}"


def norm(num):
    return f"MAC-{int(num)}"


def path_issue(rel):
    """The issue key a path is filed under, e.g. operator_review/MAC-574/... -> MAC-574."""
    m = ISSUE_RE.search(str(rel))
    return norm(m.group(1)) if m else None


def slots_on_line(line):
    """Every slot number on one line: those bound to an issue by filename form, and the rest
    with the column they appear at (needed to decide which slot a reservation verb governs)."""
    bound, loose = {}, {}
    for m in FILENAME_RE.finditer(line):
        bound[int(m.group(1))] = norm(m.group(2))
    for m in ANCHORED_RE.finditer(line):
        loose.setdefault(int(m.group(1)), m.start(1))
    if SLOT_CONTEXT_RE.search(line):
        for m in BARE_RE.finditer(line):
            loose.setdefault(int(m.group(1)), m.start(1))
    return bound, {s: p for s, p in loose.items() if s not in bound}


def verb_governs(line, loose):
    """Which slots a reservation verb actually reserves.

    'MAC-663 is hereby dispatch-claimed slot `0054`. `0053` is deliberately skipped' names two
    slots and one issue. Treating the verb as governing the whole line reserves 0053 to MAC-663,
    which is the opposite of what the sentence says. A verb governs the slot nearest to it."""
    verbs = [m.start() for m in DECLARATIVE_RE.finditer(line)]
    if not verbs or not loose:
        return set()
    governed = set()
    for v in verbs:
        governed.add(min(loose, key=lambda s: (abs(loose[s] - v), s)))
    return governed


def scan_files():
    """Layer 1+2: applied files and drafts. A filename is the one claim that cannot be misread."""
    ev = []
    for f in sorted(MIGRATIONS.glob("*.sql")):
        m = re.match(r"^(\d{4})_(?:mac(\d{3,4})_)?", f.name)
        if m:
            issue = norm(m.group(2)) if m.group(2) else None
            ev.append(Ev(int(m.group(1)), APPLIED, issue, f"db/migrations/{f.name}", f.name))
    if DRAFTS.is_dir():
        for f in sorted(DRAFTS.glob("*.sql.draft")):
            m = re.match(r"^(\d{4})_(?:mac(\d{3,4})_)?", f.name)
            if m:
                issue = norm(m.group(2)) if m.group(2) else None
                ev.append(Ev(int(m.group(1)), DRAFT, issue,
                             f"db/migrations/_drafts/{f.name}", f.name))
    return ev


def prose_files():
    for d in SCAN_DIRS:
        base = ROOT / d
        if base.is_dir():
            for g in PROSE_GLOBS:
                yield from sorted(base.rglob(g))
    # Migration headers carry the richest claim tables in the repo; drafts hold claims by
    # definition. Both are prose for scanning purposes.
    yield from sorted(MIGRATIONS.glob("*.sql"))
    if DRAFTS.is_dir():
        yield from sorted(DRAFTS.glob("*.sql.draft"))


def scan_prose():
    """Layer 3: reservation prose. Returns (evidence, echoes, negatives, fenced, releases)."""
    ev, echoes, negatives, fenced, releases = [], 0, 0, [], []
    for f in prose_files():
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = f.relative_to(ROOT)
        header = text.splitlines()[:FENCE_LINES]
        # Header pragmas are read from every file, fenced or not: a release document is required
        # to be fenced, so reading its pragma only after the fence check would never find one.
        for n, raw in enumerate(header, 1):
            if RELEASE_ANY_RE.search(raw):
                releases.append(parse_release(str(rel), n, raw))
        if FENCE_RE.search("\n".join(header)):
            fenced.append(str(rel))
            continue
        owner = path_issue(rel)
        for line_no, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            bound, loose = slots_on_line(line)
            if not bound and not loose:
                continue
            if ECHO_RE.search(line):
                echoes += 1
                continue
            if NEGATIVE_RE.search(line):
                negatives += 1
                continue
            where = f"{rel}:{line_no}"
            snippet = line[:100]
            issues = [norm(m.group(1)) for m in ISSUE_RE.finditer(line)]
            governed = verb_governs(line, loose)
            for slot, issue in bound.items():
                ev.append(Ev(slot, FILENAME, issue, where, snippet, line))
            for slot in loose:
                if len(issues) == 1 and slot in governed:
                    ev.append(Ev(slot, DECLARATIVE, issues[0], where, snippet, line))
                elif issues:
                    for issue in issues:
                        ev.append(Ev(slot, COMENTION, issue, where, snippet, line))
                elif owner:
                    ev.append(Ev(slot, PATH, owner, where, snippet, line))
                else:
                    ev.append(Ev(slot, UNATTRIBUTED, None, where, snippet, line))
    return ev, echoes, negatives, fenced, releases


def resolve(ev):
    """Per slot: the strongest LIVE evidence wins the holder. Weak-only -> contested, no holder.

    Retracted mentions are kept in `ev` and excluded from `live`, never dropped. A slot whose every
    mention was retracted resolves to RELEASED and stays in the map -- deleting it would make the
    slot read identical to one nobody ever mentioned, and would hand it straight back to the
    auto-handout loop in `report()`, which skips any slot present here."""
    by_slot = {}
    for e in ev:
        by_slot.setdefault(e.slot, []).append(e)
    out = {}
    for slot, items in sorted(by_slot.items()):
        # Within a tier, prefer the claim filed in the claimant's own directory: a lane
        # declaring its own slot IS the reservation; a third party quoting it is a report.
        items.sort(key=lambda e: (RANK[e.tier],
                                  0 if e.issue and e.issue in e.where else 1,
                                  e.where))
        live = [e for e in items if e.released is None]
        strong = [e for e in live if e.strong and e.issue]
        holders = []
        if strong:
            best = RANK[strong[0].tier]
            holders = sorted({e.issue for e in strong if RANK[e.tier] == best})
        holder = holders[0] if len(holders) == 1 else None
        if any(e.tier == APPLIED for e in live):
            state = "APPLIED"
        elif len(holders) > 1:
            state = "DISPUTED"
        elif holder:
            state = "CLAIMED"
        elif live:
            state = "CONTESTED"
        else:
            state = "RELEASED"
        out[slot] = {"state": state, "holder": holder, "ev": items, "live": live,
                     "holders": holders}
    return out


def held_by(slots, issue):
    """Slots this issue holds, split by evidence strength. Weak hits still block; a false
    'you are clear' is the failure this tool exists to prevent, a false 'go reconcile' is a read.

    A file on disk supersedes prose. Without that rule a lane that publicly moved off a slot
    ("the original MAC-608 draft claimed slot 0049") keeps holding the slot forever, and the
    lane that actually landed the file is not the one credited."""
    strong, weak = [], []
    for slot, info in slots.items():
        live = info["live"]  # a retracted mention is not a hold
        onfile = [e for e in live if e.tier in (APPLIED, DRAFT)]
        if onfile:
            if any(e.issue == issue for e in onfile):
                strong.append((slot, next(e for e in onfile if e.issue == issue)))
            continue  # the file names someone else -- prose cannot outvote it
        s = [e for e in live if e.strong and e.issue == issue]
        w = [e for e in live if not e.strong and e.issue == issue]
        if s:
            strong.append((slot, s[0]))
        elif w:
            weak.append((slot, w[0]))
    return sorted(strong), sorted(weak)


def holder_label(info):
    if info["state"] == "RELEASED":
        # Never "unresolved": a released slot is resolved, and resolved to nobody.
        return "-- retracted, see the slot release ledger"
    return info["holder"] or ("/".join(info["holders"]) if info["holders"] else "unresolved")


def release_ledger(releases):
    """Every pragma, honored or not, with the cite it targeted. A release that vanished from the
    report would be indistinguishable from one that was never written."""
    tally = {k: sum(1 for r in releases if r.disposition == k)
             for k in ("HONORED", "UNMATCHED", "REFUSED", "MALFORMED")}
    print(f"slot releases        : {tally['HONORED']} honored, {tally['UNMATCHED']} unmatched, "
          f"{tally['REFUSED']} refused, {tally['MALFORMED']} malformed")
    return tally


def print_ledger(releases):
    print("\nslot release ledger (a release retracts ONE cited mention; a file on disk is never "
          "releasable):")
    if not releases:
        print("  [release] (none)")
        return
    for r in sorted(releases, key=lambda r: (r.doc, r.line_no)):
        head = f"{r.slot:04d} {r.issue}" if r.slot else "(unparsed)"
        print(f"  [release] {r.disposition:<9} {head}  targets {r.where or '-'}")
        print(f"  [release]           declared at {r.doc}:{r.line_no}")
        print(f"  [release]           {r.detail}")


def report(slots, echoes, negatives, out_of_range, ceiling, fenced, releases, verbose=False):
    applied = sorted(s for s, i in slots.items() if i["state"] == "APPLIED")
    highest_file = max(applied)
    # MAC-763 untracked ``operator_review/``, one of SCAN_DIRS. The headline answer
    # (next free slot) is unaffected -- verified identical, 0063, in a scrubbed and an
    # unscrubbed clone -- but ATTRIBUTION degrades silently at rc=0: honored slot
    # releases drop 1 -> 0, and gaps 0047/0058 fall back from ``CLAIMED <owner>`` to
    # ``CONTESTED unresolved``. Reclaiming a gap is meant to be a deliberate NAMED
    # decision, so a reader must be told the tool can no longer name the holder rather
    # than inferring the holder never existed. Disclose, do not fail: picking a slot in
    # a fresh clone must keep working.
    absent = [d for d in SCAN_DIRS if not (ROOT / d).exists()]
    if absent:
        print(f"scan scope INCOMPLETE  : {', '.join(absent)} not present in this tree; "
              f"slot attribution below is partial -- a gap may read CONTESTED because its "
              f"claiming document is not shipped, not because no one claimed it")
    print(f"highest file on disk : {highest_file:04d}")
    print(f"naive next (WRONG)   : {highest_file + 1:04d}   <- what `ls db/migrations/` tells you")
    print(f"mentions dropped     : {echoes} echo, {negatives} negative, "
          f"{out_of_range} above the {ceiling:04d} ceiling (not reservations)")
    tally = release_ledger(releases)
    if fenced:
        print(f"fenced files         : {len(fenced)} self-declared non-authoritative "
              f"(slot-scan: ignore) -- {', '.join(fenced)}")
    print_ledger(releases)
    print()

    print(f"FULL-RANGE claim scan 0001..{ceiling:04d} "
          f"(no floor -- a gap below the highest file is CONTESTED, not history):")
    for slot, info in sorted(slots.items()):
        if info["state"] == "APPLIED" and not verbose:
            continue
        print(f"  {slot:04d}  {info['state']:<9} {holder_label(info)}")
        shown = info["ev"] if verbose else [e for e in info["ev"][:3]]
        for e in shown:
            tag = f"  [release] RETRACTED by {e.released.doc}" if e.released else ""
            print(f"          [{e.tier}] {e.where}{tag}")
            print(f"          {e.text}")
        if not verbose and len(info["ev"]) > len(shown):
            print(f"          ... {len(info['ev']) - len(shown)} more (--verbose)")

    gaps = [s for s in range(min(applied), highest_file) if s not in applied]
    print("\ngaps below the highest applied file:")
    if not gaps:
        print("  (none)")
    for s in gaps:
        info = slots.get(s)
        who = holder_label(info) if info else "-"
        print(f"  {s:04d}  {info['state'] if info else 'NO EVIDENCE'}  {who}")
    print("  a gap is NOT auto-reused -- reclaiming one is a deliberate, named decision")
    print("  a RELEASED slot is a gap like any other: freed, never auto-handed-out")

    free = highest_file + 1
    while free in slots:
        free += 1
    print(f"\nnext free slot       : {free:04d}")
    return free, tally


class Scan:
    """One full read of the repo. Named so the selftest can build a second one with releases
    switched off and compare -- a release fixture that cannot be poisoned proves nothing."""

    def __init__(self, lookahead=LOOKAHEAD, honor_releases=True):
        files = scan_files()
        ev, self.echoes, self.negatives, self.fenced, self.releases = scan_prose()
        self.pool = files + ev
        if honor_releases:
            apply_releases(self.releases, self.pool, set(self.fenced))
        self.ceiling = max(e.slot for e in files if e.tier == APPLIED) + lookahead
        in_range = [e for e in self.pool if 1 <= e.slot <= self.ceiling]
        self.out_of_range = len(self.pool) - len(in_range)
        self.slots = resolve(in_range)

    def free(self):
        f = max(s for s, i in self.slots.items() if i["state"] == "APPLIED") + 1
        while f in self.slots:
            f += 1
        return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claim", help="issue key that wants a slot, e.g. MAC-537")
    ap.add_argument("--slot", help="the slot that issue proposes to take, e.g. 0046")
    ap.add_argument("--verbose", action="store_true", help="every evidence line, incl. applied")
    ap.add_argument("--lookahead", type=int, default=LOOKAHEAD,
                    help=f"slots above highest_file+N are not slots (default {LOOKAHEAD})")
    ap.add_argument("--selftest", action="store_true",
                    help="positive control: assert the MAC-674 collision incident is detected")
    args = ap.parse_args()

    if not MIGRATIONS.is_dir() or not any(MIGRATIONS.glob("*.sql")):
        print("no migrations found -- check the path", file=sys.stderr)
        return 1

    if args.selftest:
        return selftest(args.lookahead)

    scan = Scan(args.lookahead)
    slots = scan.slots
    free, tally = report(slots, scan.echoes, scan.negatives, scan.out_of_range, scan.ceiling,
                         scan.fenced, scan.releases, args.verbose)

    # A release that failed is louder than a release that worked: somebody is acting on a slot the
    # scanner still holds contested, or on a retraction that never happened.
    rc = 4 if sum(tally.values()) - tally["HONORED"] else 0
    if args.claim:
        claim = norm(ISSUE_RE.search(args.claim).group(1)) if ISSUE_RE.search(args.claim) \
            else args.claim.upper()
        strong, weak = held_by(slots, claim)
        want = int(args.slot) if args.slot else free
        print()
        if strong:
            for slot, e in strong:
                print(f"{claim} ALREADY HOLDS slot {slot:04d}  [{e.tier}] {e.where}")
                print(f"    {e.text}")
            if args.slot and want in [s for s, _ in strong]:
                # Non-zero is still correct here -- a hold exists. It is a confirmation, not a
                # collision, and the caller should proceed with the slot they already hold.
                print(f"  -> CONFIRMED: {want:04d} is yours. Non-zero exit means a hold exists, "
                      f"not that the slot is contested.")
            else:
                print(f"  -> do NOT take {want:04d}. Use the slot you hold, or release it with a "
                      f"`slot-release:` header pragma under that issue's own directory (grammar "
                      f"and rules: the release block in this script's source).")
            rc |= 1
        elif weak:
            for slot, e in weak:
                print(f"{claim} MAY HOLD slot {slot:04d}  [{e.tier}] {e.where}")
                print(f"    {e.text}")
            print("  -> weak evidence only; read the line above and confirm by hand before "
                  "taking a new slot.")
            rc |= 1
        else:
            print(f"{claim} holds no slot")

        info = slots.get(want)
        if info and not (info["holder"] == claim and info["state"] != "APPLIED"):
            who = info["holder"] or "unresolved"
            print(f"proposed slot {want:04d} is NOT free: {info['state']} {who} "
                  f"[{info['ev'][0].tier}] {info['ev'][0].where}")
            rc |= 2
        elif not info and not rc:
            print(f"proposed slot {want:04d} is free; claim it in a COMMITTED file "
                  f"(a draft under db/migrations/_drafts/ counts) before dispatch")
        elif not info:
            print(f"slot {want:04d} is free, but do not take it until the hold above is "
                  f"reconciled")
    return rc


# --- positive control -------------------------------------------------------------------
# BRIEF_STANDARDS R7: a zero-yield gate needs a positive control. This one is pinned to the
# live five-collision incident of 2026-08-11 (MAC-674), not to a synthetic fixture. Each pair
# below is bound by a filename or a reservation sentence that survives the slot being applied,
# so this stays true after 0046/0047/0050 land as files. If a lane legitimately renumbers,
# update the pair here and say so in the commit -- do not delete the control.
INCIDENT = [("MAC-574", 46), ("MAC-598", 47), ("MAC-608", 50)]

# MAC-683/MAC-684 release fixture, pinned to the live ruling, not to a synthetic file. `0053` was
# skipped by MAC-663 §8 on a line the amend ban keeps verbatim, the CEO released it at `197e0e9`,
# and the scanner went on printing `0053 CONTESTED unresolved` because there was no release verb.
RELEASE_FIXTURE = {"slot": 53, "issue": "MAC-663", "keeps": 54,
                   "doc": "operator_review/MAC-663/SLOT_RELEASE.md",
                   "cite": "operator_review/MAC-663/CEO_RATIFICATION.md:179"}
# The theft control. MAC-608 holds 0050 as a DRAFT FILE, so no pragma may move it. Anchored to the
# draft's own filename so the control stays live if the draft is renamed under the same slot.
THEFT = {"slot": 50, "issue": "MAC-608",
         "cite": "db/migrations/_drafts/0050_mac608_watchguard_alias_entity_conflation.sql.draft",
         "anchor": "0050_mac608"}


def check(fails, name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)
    return ok


def synthetic(scan, doc, slot, issue, cite, anchor, fenced=True):
    """Run one hand-built pragma through the real matcher against a fresh scan. The controls below
    must exercise `apply_releases`, not a paraphrase of it, or they certify nothing."""
    line = cite.rsplit(":", 1)
    path, num = (line[0], line[1]) if len(line) == 2 and line[1].isdigit() else (cite, None)
    r = Release(doc, 1, "<synthetic>", slot=slot, issue=issue, path=path,
                line=int(num) if num else None, anchor=anchor)
    apply_releases([r], scan.pool, set(scan.fenced) | ({doc} if fenced else set()))
    return r


def selftest(lookahead=LOOKAHEAD):
    fails = []
    live, unreleased = Scan(lookahead), Scan(lookahead, honor_releases=False)
    slots = live.slots

    print("POSITIVE CONTROL A -- MAC-674 live collision incident (2026-08-11)")
    for issue, want in INCIDENT:
        strong, _ = held_by(slots, issue)
        got = [s for s, _ in strong]
        src = next((e.where for s, e in strong if s == want), "-")
        check(fails, f"{issue} holds {want:04d}", want in got,
              f"got {[f'{s:04d}' for s in got] or 'NONE'}  {src}")
    # The incident was not just a miss: all three were handed the SAME slot.
    collided = [i for i, _ in INCIDENT if not held_by(slots, i)[0]]
    check(fails, f"no-collision: {live.free():04d} handed to 0 of {len(INCIDENT)} incident issues",
          not collided, f"collided={collided}")

    f = RELEASE_FIXTURE
    slot, issue, keeps = f["slot"], f["issue"], f["keeps"]
    print(f"\nPOSITIVE CONTROL B -- MAC-683 slot release ({slot:04d} freed by ruling, 2026-08-11)")
    info = slots.get(slot)
    check(fails, f"{slot:04d} resolves RELEASED", bool(info) and info["state"] == "RELEASED",
          f"got {info['state'] if info else 'ABSENT'}")
    check(fails, f"{slot:04d} names no holder", bool(info) and not info["holder"],
          f"got {info['holder'] if info else '-'}")
    check(fails, f"{issue} holds neither strongly nor weakly at {slot:04d}",
          slot not in [s for s, _ in held_by(slots, issue)[0] + held_by(slots, issue)[1]])
    # The ask was explicit: freed, NOT auto-reused. Both halves, or the fix overshoots.
    check(fails, f"{slot:04d} is not auto-handed-out", live.free() != slot,
          f"next free slot = {live.free():04d}")
    check(fails, f"{slot:04d} still listed (a freed gap is reported, not erased)", slot in slots)
    kinfo = slots.get(keeps)
    check(fails, f"{keeps:04d} still resolves to {issue} (same line, other slot untouched)",
          bool(kinfo) and kinfo["holder"] == issue, f"got {kinfo['holder'] if kinfo else '-'}")
    check(fails, "the release itself is HONORED in the ledger",
          any(r.took_effect and r.slot == slot and r.doc == f["doc"] for r in live.releases))

    print("\nNON-VACUITY -- remove the release and the phantom must come back")
    uinfo = unreleased.slots.get(slot)
    check(fails, f"unreleased: {slot:04d} reads CONTESTED", bool(uinfo) and
          uinfo["state"] == "CONTESTED", f"got {uinfo['state'] if uinfo else 'ABSENT'}")
    check(fails, f"unreleased: {issue} weakly holds {slot:04d}",
          slot in [s for s, _ in held_by(unreleased.slots, issue)[1]])

    print("\nTHEFT CONTROLS -- a release must not be able to void a live claim")
    t = synthetic(live, f"operator_review/{THEFT['issue']}/x.md", THEFT["slot"], THEFT["issue"],
                  THEFT["cite"], THEFT["anchor"])
    check(fails, f"a pragma targeting {THEFT['issue']}'s DRAFT FILE {THEFT['slot']:04d} is REFUSED",
          t.disposition == "REFUSED", f"got {t.disposition}: {t.detail}")
    check(fails, f"{THEFT['slot']:04d} still held by {THEFT['issue']} after the attempt",
          Scan(lookahead).slots[THEFT["slot"]]["holder"] == THEFT["issue"])
    bad = synthetic(Scan(lookahead), f["doc"], slot, issue, f["cite"], "no such bytes on that line")
    check(fails, "a wrong anchor is UNMATCHED (the cite-paste is load-bearing)",
          bad.disposition == "UNMATCHED", f"got {bad.disposition}: {bad.detail}")
    far = synthetic(Scan(lookahead), "operator_review/MAC-999/steal.md", slot, issue, f["cite"],
                    "deliberately skipped")
    check(fails, "the same release from a foreign directory is REFUSED cross-lane",
          far.disposition == "REFUSED", f"got {far.disposition}: {far.detail}")
    # A doc in the right directory but NOT carrying `slot-scan: ignore`. Reusing f["doc"] would be
    # vacuous: that file really is fenced on disk, so the flag could not switch anything off.
    unf = synthetic(Scan(lookahead), "operator_review/MAC-663/unfenced_release.md", slot, issue,
                    f["cite"], "deliberately skipped", fenced=False)
    check(fails, "an unfenced release document is REFUSED (one fencing verb, declared out loud)",
          unf.disposition == "REFUSED", f"got {unf.disposition}: {unf.detail}")

    print("\nREADER CONTROLS -- a pragma the reader must never act on")
    junk = parse_release(f["doc"], 1, "<!-- slot-release: 0053 is free now -->")
    apply_releases([junk], live.pool, set(live.fenced))
    check(fails, "a pragma that does not parse is MALFORMED and retracts nothing",
          junk.disposition == "MALFORMED" and not junk.retracted, f"got {junk.disposition}")
    # SLOT_RELEASE.md carries a second, byte-identical copy of its own pragma in its BODY. If the
    # header rule ever broke, this count goes to 2 -- the MAC-674 quoting-vs-asserting bug, one
    # level up: a document that merely SHOWS a release would perform one.
    own = [r for r in live.releases if r.doc == f["doc"]]
    check(fails, "the body copy of the pragma is invisible (a release is a HEADER pragma)",
          len(own) == 1 and own[0].line_no <= FENCE_LINES,
          f"got {len(own)} at lines {[r.line_no for r in own]}")

    print("PASS" if not fails else "FAIL: " + "; ".join(fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
