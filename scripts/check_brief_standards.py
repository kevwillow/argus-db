#!/usr/bin/env python3
"""Gate a worker brief against the mechanically-checkable rules in
operator_review/BRIEF_STANDARDS.md (R1-R3, R6, R7).

Standing rules ratified by CEO on MAC-558 comment 6b298929. R6 and R7 are also STANDING: the CEO
ratified R6 on MAC-573 and R7 on MAC-551, both 2026-07-29. Every rule this gate enforces is now
ratified.

Usage:  python3 scripts/check_brief_standards.py <brief.md> [<brief.md> ...]
Exit 0 = all briefs pass. Exit 1 = at least one FAIL.
"""
import re
import sys
from pathlib import Path

STANDARDS = "operator_review/BRIEF_STANDARDS.md"
# A brief one directory down cites `../BRIEF_STANDARDS.md`, which is a correct path citation.
# R0 asks that the file be cited rather than restated, so match the basename with any prefix.
STANDARDS_CITE = re.compile(r"(^|[`'\"(\s/])(?:[\w./-]*/)?BRIEF_STANDARDS\.md")

# R1: a brief that can produce a negative finding must say what a negative finding costs.
R1_EVIDENCE = [r"HTTP status", r"byte count", r"fetch command"]
R1_TRIGGER = [r"not retriev", r"negative finding", r"zero[- ]yield", r"exhaust"]

# R2: the output file set is enumerated once. Count sections that enumerate artifacts.
ARTIFACT = re.compile(r"\b(screen|adjudication|secondary)\.jsonl\b")
HEADING = re.compile(r"^#{1,4}\s+(.*)$", re.M)

# R3: a key mandated to hold a FIXED value must print that value as a literal.
# Free-prose keys (notes.reasoning) are out of scope -- they have no fixed value to pin.
KEY_REF = re.compile(r"`notes\.([A-Za-z_][A-Za-z0-9_]*)`")
FIXED_VALUE_MARKER = re.compile(
    r"(value exactly|exactly\s*[`\"]|must (be|equal)|==|mandatory on every|is mandatory)", re.I
)
QUOTED_LITERAL = re.compile(r"[`\"][A-Za-z0-9_\-]+[`\"]")
WINDOW = 200

# R6 (MAC-573): liveness is `lastOutputAt < startedAt`. Two signals are banned as evidence of
# it -- lastHeartbeatAt stamps at run dispatch so it inverts, and logRef mtime describes the
# incarnation the re-adoption overwrote. Naming either is fine; INFERRING liveness from it is not.
R6_BANNED = re.compile(
    r"lastHeartbeatAt|logRef[^\n]{0,60}\bmtimes?\b|\bmtimes?\b[^\n]{0,60}logRef", re.I
)
R6_LIVENESS = re.compile(
    r"\b(dark|dead|alive|liveness|stalled?|hung|hang|zombie|stuck|orphan|reaped|"
    r"no output|not running|still running)\b",
    re.I,
)
# A brief may cite the banned signal in order to strike or forbid it. That is the rule working.
R6_EXEMPT = re.compile(
    r"~~|never use|not a liveness|no liveness|must not|do not infer|banned|struck|"
    r"is not a substitute|inverts",
    re.I,
)
# Raw evidence and quoted prose are citations, not the brief's own inference. A brief that
# documents the MAC-547 defect must quote `"and dark since"` to name it; MAC-547 itself asserted
# it unquoted. Strip fenced blocks, inline code and quoted spans before testing for the claim.
CITATION_SPAN = re.compile(r"```.*?```|`[^`\n]*`|\"[^\"\n]*\"|“[^”\n]*”", re.S)
# The document that DEFINES R6 must name both banned fields in order to forbid them, and must
# quote the precedent that misused them. Briefs cite that document rather than restating it
# (R0), so this heading never appears in a brief.
R6_DEFINITION = re.compile(r"^#{1,4}\s*R6\s*[-—–]", re.M)

# R7 (MAC-551): a zero needs a positive control, and format is decided by `content_type`.
# Re-running the same instrument re-derives the same number from the same instrument; only a
# known-positive fed through the REAL extraction path separates a channel zero from a
# capability zero. Triggered by the same admission R1 keys off -- a brief that concedes it may
# return nothing.
R7_POSITIVE_CONTROL = re.compile(
    r"positive[- ]control|known[- ]positive|synthetic\s+\w*\s*positive|"
    r"canary\s+(input|document|row)",
    re.I,
)
R7_ZERO_KIND = re.compile(r"channel\s+zero|capability\s+zero|channel[- ]vs[- ]capability", re.I)
# Format dispatch. Naming the filename route to FORBID it is the rule working, so the presence
# of `content_type` anywhere in the brief clears this check.
R7_FILENAME_DISPATCH = re.compile(
    r"\b(?:file\s?name|filename|suffix|extension|url\s+path)\b[^\n]{0,80}"
    r"\b(?:pdf|html|parse|parser|extract|dispatch|decide|route)\b|"
    r"\b(?:pdf|html|parse|parser|extract|dispatch|decide|route)\w*\b[^\n]{0,80}"
    r"\b(?:file\s?name|filename|suffix|extension|url\s+path)\b",
    re.I,
)
R7_CONTENT_TYPE = re.compile(r"content[-_ ]type", re.I)
# The document that DEFINES R7 must state the banned filename route in order to forbid it.
R7_DEFINITION = re.compile(r"^#{1,4}\s*R7\s*[-—–]", re.M)


def paragraph_at(text, pos):
    """The blank-line-delimited paragraph containing `pos`.

    R6 asks whether the brief infers liveness FROM the banned field. That inference lives in
    the same paragraph as the field; a fixed character window straddles paragraphs and fires
    on unrelated prose (MAC-547, where `reaped` in the previous paragraph tripped a correction
    that was itself compliant).
    """
    start = text.rfind("\n\n", 0, pos)
    start = 0 if start < 0 else start + 2
    end = text.find("\n\n", pos)
    return text[start: end if end >= 0 else len(text)]


def sections(text):
    """Split into (heading, body) pairs so we can count artifact enumerations per section."""
    marks = [(m.start(), m.group(1).strip()) for m in HEADING.finditer(text)]
    if not marks:
        return [("<root>", text)]
    out = []
    for i, (pos, title) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out.append((title, text[pos:end]))
    return out


def check(path):
    text = Path(path).read_text(encoding="utf-8")
    fails, warns = [], []

    # --- R0: the brief must cite the standards file rather than restate it.
    if not STANDARDS_CITE.search(text):
        fails.append(f"R0 brief does not cite {STANDARDS}; rules must be inherited, not restated")

    # --- R1 negative-finding clause
    if any(re.search(p, text, re.I) for p in R1_TRIGGER):
        missing = [p for p in R1_EVIDENCE if not re.search(p, text, re.I)]
        if missing:
            fails.append(
                "R1 brief admits a negative finding but omits scan-artifact requirements: "
                + ", ".join(missing)
            )
        if not re.search(r"assert on the (response )?body|200 is not reachab", text, re.I):
            warns.append("R1 no HTTP-200-is-not-reachability clause (a 200 can be a bot wall)")

    # --- R2 single output contract
    enumerating = [t for t, body in sections(text) if len(set(ARTIFACT.findall(body))) >= 2]
    if len(enumerating) > 1:
        fails.append(
            "R2 output artifacts enumerated in %d sections (%s); name the set in exactly one"
            % (len(enumerating), "; ".join(enumerating[:4]))
        )

    # --- R3 literal keys. A key is in scope only where the brief mandates a FIXED value
    # for it; free-prose keys such as notes.reasoning have no literal to pin.
    fixed_keys, unpinned = set(), set()
    for m in KEY_REF.finditer(text):
        near = text[max(0, m.start() - WINDOW): m.end() + WINDOW]
        if not FIXED_VALUE_MARKER.search(near):
            continue
        fixed_keys.add(m.group(1))
        # the literal must sit after the key reference, not merely somewhere in the window
        if not QUOTED_LITERAL.search(text[m.end(): m.end() + WINDOW]):
            unpinned.add(m.group(1))
    for key in sorted(unpinned):
        fails.append(
            f"R3 `notes.{key}` is mandated with a fixed value but that value is not pinned as a "
            "quoted literal; a described key drifts (binding_level vs category_binding_level, "
            "MAC-558)"
        )
    if fixed_keys and not re.search(r"assert |post-check|before handback", text, re.I):
        warns.append(
            "R3 fixed-key contract (%s) has no post-check assertion required of the worker"
            % ", ".join(sorted(fixed_keys))
        )

    # --- R6 banned liveness signals. Flag only where the banned field sits next to a liveness
    # claim and is not being struck -- naming the field to forbid it must stay legal.
    for m in [] if R6_DEFINITION.search(text) else R6_BANNED.finditer(text):
        # Scope to the containing paragraph, not a raw character window: a ±200-char window
        # crosses paragraph boundaries and picks up liveness words from unrelated sentences.
        near = paragraph_at(text, m.start())
        if R6_EXEMPT.search(near):
            continue
        if not R6_LIVENESS.search(CITATION_SPAN.sub(" ", near)):
            continue
        fails.append(
            "R6 liveness inferred from `%s`; that signal inverts (lastHeartbeatAt stamps at run "
            "dispatch) or describes a superseded incarnation (logRef mtime). Use "
            "`lastOutputAt < startedAt` -- scripts/run_liveness_probe.py (MAC-547 validator_gate, "
            "MAC-573)" % m.group(0).strip()
        )
        break

    # --- R7 positive control on a zero, and content_type dispatch. Scoped to briefs that admit
    # they may return nothing -- the same admission R1 keys off.
    if not R7_DEFINITION.search(text) and any(re.search(p, text, re.I) for p in R1_TRIGGER):
        if not R7_POSITIVE_CONTROL.search(text):
            fails.append(
                "R7 brief admits its deliverable may be zero but mandates no positive control; "
                "re-running the same instrument re-derives the same number from the same "
                "instrument. Require a synthetic known-positive through the real extraction "
                "path (MAC-551 ctf_nonvacuity_probe.py, 6/6 fired)"
            )
        if not R7_ZERO_KIND.search(text):
            warns.append(
                "R7 zero is not qualified as a channel zero (source class carries nothing) vs a "
                "capability zero (instrument could not see it)"
            )
        m = R7_FILENAME_DISPATCH.search(text)
        if m and not R7_CONTENT_TYPE.search(text):
            fails.append(
                "R7 extraction format dispatched on filename/suffix/URL path (`%s`) with no "
                "`content_type` route; the failure is silent -- the parser raises, `except` "
                "returns \"\", and a 527KB HTML page scores 0 chars "
                "(138669b:extraction_outputs/MAC-547/scripts/scan_all.py:163)"
                % " ".join(m.group(0).split())[:60]
            )

    return fails, warns


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    worst = 0
    for path in argv[1:]:
        fails, warns = check(path)
        status = "FAIL" if fails else ("WARN" if warns else "PASS")
        worst = max(worst, 1 if fails else 0)
        print(f"{status}  {path}")
        for f in fails:
            print(f"    FAIL  {f}")
        for w in warns:
            print(f"    warn  {w}")
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv))
