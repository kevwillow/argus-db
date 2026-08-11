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

    python3 scripts/next_migration_slot.py                     # full-range claim report
    python3 scripts/next_migration_slot.py --claim MAC-608     # ... and reconcile one issue
    python3 scripts/next_migration_slot.py --claim MAC-700 --slot 0046   # assert a specific slot
    python3 scripts/next_migration_slot.py --selftest          # positive control, see below

Exit codes:
    0  the proposed slot is free and the issue holds nothing else
    1  the named issue ALREADY HOLDS a slot -- use it or release it, do not take a new one
    2  the proposed slot is HELD BY SOMEONE ELSE
    3  both of the above
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
    r"gaps below the highest applied file", re.I)
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

# Evidence strength. Only STRONG tiers name a holder; WEAK tiers only make a slot contested.
APPLIED, DRAFT, FILENAME, DECLARATIVE, COMENTION, PATH, UNATTRIBUTED = (
    "APPLIED", "DRAFT", "FILENAME", "DECLARATIVE", "CO-MENTION", "PATH", "UNATTRIBUTED")
STRONG = (APPLIED, DRAFT, FILENAME, DECLARATIVE)
RANK = {APPLIED: 0, DRAFT: 1, FILENAME: 2, DECLARATIVE: 3, COMENTION: 4, PATH: 5, UNATTRIBUTED: 6}


class Ev:
    """One piece of evidence that a slot is spoken for."""

    def __init__(self, slot, tier, issue, where, text):
        self.slot, self.tier, self.issue, self.where, self.text = slot, tier, issue, where, text

    @property
    def strong(self):
        return self.tier in STRONG


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
    """Layer 3: reservation prose. Returns (evidence, echo_count, negative_count, fenced)."""
    ev, echoes, negatives, fenced = [], 0, 0, []
    for f in prose_files():
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = f.relative_to(ROOT)
        if FENCE_RE.search("\n".join(text.splitlines()[:FENCE_LINES])):
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
                ev.append(Ev(slot, FILENAME, issue, where, snippet))
            for slot in loose:
                if len(issues) == 1 and slot in governed:
                    ev.append(Ev(slot, DECLARATIVE, issues[0], where, snippet))
                elif issues:
                    for issue in issues:
                        ev.append(Ev(slot, COMENTION, issue, where, snippet))
                elif owner:
                    ev.append(Ev(slot, PATH, owner, where, snippet))
                else:
                    ev.append(Ev(slot, UNATTRIBUTED, None, where, snippet))
    return ev, echoes, negatives, fenced


def resolve(ev):
    """Per slot: the strongest evidence wins the holder. Weak-only evidence -> contested, no holder."""
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
        strong = [e for e in items if e.strong and e.issue]
        if strong:
            best = RANK[strong[0].tier]
            holders = sorted({e.issue for e in strong if RANK[e.tier] == best})
            holder = holders[0] if len(holders) == 1 else None
            disputed = len(holders) > 1
        else:
            holder, disputed = None, False
        applied = any(e.tier == APPLIED for e in items)
        state = "APPLIED" if applied else ("DISPUTED" if disputed else
                                           ("CLAIMED" if holder else "CONTESTED"))
        out[slot] = {"state": state, "holder": holder, "ev": items,
                     "holders": holders if strong else []}
    return out


def held_by(slots, issue):
    """Slots this issue holds, split by evidence strength. Weak hits still block; a false
    'you are clear' is the failure this tool exists to prevent, a false 'go reconcile' is a read.

    A file on disk supersedes prose. Without that rule a lane that publicly moved off a slot
    ("the original MAC-608 draft claimed slot 0049") keeps holding the slot forever, and the
    lane that actually landed the file is not the one credited."""
    strong, weak = [], []
    for slot, info in slots.items():
        onfile = [e for e in info["ev"] if e.tier in (APPLIED, DRAFT)]
        if onfile:
            if any(e.issue == issue for e in onfile):
                strong.append((slot, next(e for e in onfile if e.issue == issue)))
            continue  # the file names someone else -- prose cannot outvote it
        s = [e for e in info["ev"] if e.strong and e.issue == issue]
        w = [e for e in info["ev"] if not e.strong and e.issue == issue]
        if s:
            strong.append((slot, s[0]))
        elif w:
            weak.append((slot, w[0]))
    return sorted(strong), sorted(weak)


def report(slots, echoes, negatives, out_of_range, ceiling, fenced, verbose=False):
    applied = sorted(s for s, i in slots.items() if i["state"] == "APPLIED")
    highest_file = max(applied)
    print(f"highest file on disk : {highest_file:04d}")
    print(f"naive next (WRONG)   : {highest_file + 1:04d}   <- what `ls db/migrations/` tells you")
    print(f"mentions dropped     : {echoes} echo, {negatives} negative, "
          f"{out_of_range} above the {ceiling:04d} ceiling (not reservations)")
    if fenced:
        print(f"fenced files         : {len(fenced)} self-declared non-authoritative "
              f"(slot-scan: ignore) -- {', '.join(fenced)}")
    print()

    print(f"FULL-RANGE claim scan 0001..{ceiling:04d} "
          f"(no floor -- a gap below the highest file is CONTESTED, not history):")
    for slot, info in sorted(slots.items()):
        if info["state"] == "APPLIED" and not verbose:
            continue
        holder = info["holder"] or ("/".join(info["holders"]) if info["holders"] else "unresolved")
        print(f"  {slot:04d}  {info['state']:<9} {holder}")
        shown = info["ev"] if verbose else [e for e in info["ev"][:3]]
        for e in shown:
            print(f"          [{e.tier}] {e.where}")
            print(f"          {e.text}")
        if not verbose and len(info["ev"]) > len(shown):
            print(f"          ... {len(info['ev']) - len(shown)} more (--verbose)")

    gaps = [s for s in range(min(applied), highest_file) if s not in applied]
    print("\ngaps below the highest applied file:")
    if not gaps:
        print("  (none)")
    for s in gaps:
        info = slots.get(s)
        who = (info["holder"] or "unresolved") if info else "-"
        print(f"  {s:04d}  {info['state'] if info else 'NO EVIDENCE'}  {who}")
    print("  a gap is NOT auto-reused -- reclaiming one is a deliberate, named decision")

    free = highest_file + 1
    while free in slots:
        free += 1
    print(f"\nnext free slot       : {free:04d}")
    return free


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

    files = scan_files()
    ev, echoes, negatives, fenced = scan_prose()
    ceiling = max(e.slot for e in files if e.tier == APPLIED) + args.lookahead
    in_range = [e for e in files + ev if 1 <= e.slot <= ceiling]
    out_of_range = len(files) + len(ev) - len(in_range)
    slots = resolve(in_range)

    if args.selftest:
        return selftest(slots)

    free = report(slots, echoes, negatives, out_of_range, ceiling, fenced, args.verbose)

    rc = 0
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
                print(f"  -> do NOT take {want:04d}. Use the slot you hold, or release it in the "
                      f"document above first.")
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


def selftest(slots):
    print("POSITIVE CONTROL -- MAC-674 live collision incident (2026-08-11)")
    fails = []
    for issue, want in INCIDENT:
        strong, weak = held_by(slots, issue)
        got = [s for s, _ in strong]
        ok = want in got
        src = next((e.where for s, e in strong if s == want), "-")
        print(f"  {issue} -> expect {want:04d}  got {[f'{s:04d}' for s in got] or 'NONE'}  "
              f"{'PASS' if ok else 'FAIL'}  {src}")
        if not ok:
            fails.append(f"{issue} does not hold {want:04d}")
    # The incident was not just a miss: all three were handed the SAME slot.
    applied = sorted(s for s, i in slots.items() if i["state"] == "APPLIED")
    free = max(applied) + 1
    while free in slots:
        free += 1
    collided = [i for i, _ in INCIDENT if not held_by(slots, i)[0]]
    print(f"  no-collision: {free:04d} handed to {len(collided)} of {len(INCIDENT)} incident "
          f"issues  {'PASS' if not collided else 'FAIL'}")
    if collided:
        fails.append(f"{free:04d} still handed to {collided}")
    print("PASS" if not fails else "FAIL: " + "; ".join(fails))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
