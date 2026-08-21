#!/usr/bin/env python3
"""MAC-773 option C: strip the internal-tracker URL surface from BIBLE_AMENDMENTS.md.

CEO ruling (MAC-773 comment 75904749): "Execute C as link-text-only edits, and prove it
with a line-count invariant (wc -l equal before and after, per file) plus a re-run of
anchor_resolve.py showing delta 0."

The published `exports/argus_export.csv` carries LINE anchors into this file
(BIBLE_AMENDMENTS.md:4197 x9 rows), and 13 distinct line anchors are cited tree-wide.
So the invariant this enforces is stronger than equal line COUNT: it is per-line INDEX
parity. Every edit is an in-line substitution; no line is ever added, removed or split.
A line that carries no tracker URL is guaranteed byte-identical.

Usage:
  strip_tracker_links.py <infile> <outfile>     apply
  strip_tracker_links.py <infile> --check       report only, write nothing

RELOCATION (MAC-781). This script was originally at
`operator_review/MAC-773/strip_tracker_links.py` (purge-scoped under MAC-764). It was
copied here to `scripts/strip_tracker_links.py` BEFORE the MAC-764 history rewrite so
downstream lanes (notably the MAC-781 `notes` DML pass) can reuse the link-pattern
regex bank without depending on a path MAC-764 is about to delete. Source of truth is
this copy; the operator_review copy is a relic and will be removed by the MAC-764 purge.
"""
import re
import sys

LINK = re.compile(r"\[([^\]\n]*)\]\((/MAC/[^)\s]*)\)")
COMMENT = re.compile(r"^/MAC/issues/(MAC-\d+)#comment-([0-9a-fA-F]+)")
DOCUMENT = re.compile(r"^/MAC/issues/(MAC-\d+)#document-(\S+)$")
ISSUE = re.compile(r"^/MAC/issues/(MAC-\d+)$")
APPROVAL = re.compile(r"^/MAC/approvals/(\S+)$")
AGENT = re.compile(r"^/MAC/agents/(\S+)$")


def bare(text):
    """Link text with surrounding markdown code-backticks removed."""
    return text.strip("`")


def rewrite(match, tally, prefix=""):
    """Rewrite one link. `prefix` is the already-emitted text to the left of it on
    this line, so a link whose surrounding prose ALREADY names the issue/comment is
    delinked rather than re-labelled (otherwise the edit stutters:
    'MAC-1 comment MAC-1 comment 5d75988d')."""
    text, target = match.group(1), match.group(2)
    plain = bare(text)

    m = COMMENT.match(target)
    if m:
        issue, cid = m.group(1), m.group(2)[:8]
        tally["comment"] += 1
        tail = prefix[-70:]
        if cid.lower() in plain.lower():
            # the text already carries the comment id; only the issue may be missing
            if re.search(rf"\b{re.escape(issue)}\b", plain) or \
               re.search(rf"\b{re.escape(issue)}\b", tail):
                return text
            return f"{text} ({issue})"
        if plain.lower() == cid.lower():
            # prose already says "<issue> ... comment" (or just "comment", with the
            # issue named close by) -> the id alone is unambiguous
            if re.search(rf"\b{re.escape(issue)}\b[^.]{{0,40}}\bcomments?\s*$",
                         tail, re.I):
                return text
            if re.search(r"\bcomments?\s*$", tail, re.I) and \
               re.search(rf"\b{re.escape(issue)}\b", tail):
                return text
            if re.search(rf"\b{re.escape(issue)}\b[\s(]*$", tail):
                return f"comment {text}"
            # text IS the comment id -> name the issue, keep the id verbatim
            return f"{issue} comment {text}"
        return f"{text} ({issue} comment {cid})"

    m = DOCUMENT.match(target)
    if m:
        tally["document"] += 1
        return f"{text} ({m.group(1)} document {m.group(2)})"

    m = ISSUE.match(target)
    if m:
        issue = m.group(1)
        tally["issue"] += 1
        return text if plain == issue else f"{text} ({issue})"

    if APPROVAL.match(target):
        tally["approval"] += 1
        return text

    if AGENT.match(target):
        tally["agent"] += 1
        return text

    tally["UNHANDLED"] += 1
    return match.group(0)


def main():
    src = sys.argv[1]
    check_only = "--check" in sys.argv
    with open(src, encoding="utf-8") as fh:
        before = fh.read()

    lines_in = before.split("\n")
    tally = {k: 0 for k in
             ("comment", "document", "issue", "approval", "agent", "UNHANDLED")}
    lines_out, touched = [], []
    for i, line in enumerate(lines_in, 1):
        if "/MAC/" not in line:
            lines_out.append(line)
            continue
        # incremental scan so each rewrite can see the text already emitted to its left
        new, pos = "", 0
        for m in LINK.finditer(line):
            new += line[pos:m.start()]
            new += rewrite(m, tally, prefix=new)
            pos = m.end()
        new += line[pos:]
        if new != line:
            touched.append(i)
        lines_out.append(new)
    after = "\n".join(lines_out)

    # --- invariants ---------------------------------------------------------
    errs = []
    if len(lines_out) != len(lines_in):
        errs.append(f"LINE COUNT MOVED {len(lines_in)} -> {len(lines_out)}")
    for i, (a, b) in enumerate(zip(lines_in, lines_out), 1):
        if "\n" in b:
            errs.append(f"line {i} gained a newline")
        if "/MAC/" not in a and a != b:
            errs.append(f"line {i} changed but carried no tracker URL")
    if tally["UNHANDLED"]:
        errs.append(f"{tally['UNHANDLED']} link(s) matched no rule")
    residual = after.count("/MAC/")

    print(f"input  : {src}")
    print(f"  lines in / out          : {len(lines_in)} / {len(lines_out)}")
    print(f"  /MAC/ before / after    : {before.count('/MAC/')} / {residual}")
    print(f"  lines edited            : {len(touched)}")
    print("  links rewritten by kind : " +
          ", ".join(f"{k}={v}" for k, v in tally.items() if v))
    print(f"  INVARIANTS              : {'PASS' if not errs else 'FAIL'}")
    for e in errs[:20]:
        print(f"    {e}")

    if errs:
        sys.exit(2)
    if not check_only:
        with open(sys.argv[2], "w", encoding="utf-8") as fh:
            fh.write(after)
        print(f"  wrote                   : {sys.argv[2]}")
    sys.exit(0)


if __name__ == "__main__":
    main()
