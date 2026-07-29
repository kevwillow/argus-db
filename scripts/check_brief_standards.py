#!/usr/bin/env python3
"""Gate a worker brief against the mechanically-checkable rules in
operator_review/BRIEF_STANDARDS.md (R1-R3).

Standing rules ratified by CEO on MAC-558 comment 6b298929. R4/R5 are judgement calls
and are not checked here -- see the authoring checklist in BRIEF_STANDARDS.md.

Usage:  python3 scripts/check_brief_standards.py <brief.md> [<brief.md> ...]
Exit 0 = all briefs pass. Exit 1 = at least one FAIL.
"""
import re
import sys
from pathlib import Path

STANDARDS = "operator_review/BRIEF_STANDARDS.md"

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
    if STANDARDS not in text:
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
