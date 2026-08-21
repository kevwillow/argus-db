#!/usr/bin/env python3
"""MAC-773 anchor-resolution instrument.

check_doc_anchors.py does NOT resolve section anchors -- its TIER_1 tuple is a
dead constant and it holds zero PROJECT_BIBLE claim sites. This is the instrument
that actually answers "did the redaction orphan a citation".

Resolves every explicitly-bible-scoped section citation in the shipping tree
against the heading inventory of PROJECT_BIBLE.md at a given rev.

Usage: anchor_resolve.py <rev> [--bible-from <path>]
Exit 1 if any explicitly-bible-scoped cite fails to resolve.

RELOCATION (MAC-781). This script was originally at
`operator_review/MAC-773/anchor_resolve.py` (purge-scoped under MAC-764). It was
copied here to `scripts/anchor_resolve.py` BEFORE the MAC-764 history rewrite so
downstream lanes (notably the MAC-781 anchor+clause gate) can keep the same
resolution primitive without depending on a path MAC-764 is about to delete.
Source of truth is this copy; the operator_review copy is a relic of the lane
that wrote it and will be removed by the MAC-764 purge.
"""
import re
import subprocess
import sys
from collections import defaultdict

REV = sys.argv[1]
OVERRIDE = None
if "--bible-from" in sys.argv:
    OVERRIDE = sys.argv[sys.argv.index("--bible-from") + 1]

BIBLE = "docs/engineering/PROJECT_BIBLE.md"
SELF = {BIBLE, "docs/engineering/BIBLE_AMENDMENTS.md", "BIBLE_AMENDMENTS.md"}


def blob(rev, path):
    try:
        raw = subprocess.run(["git", "show", f"{rev}:{path}"],
                             capture_output=True, check=True).stdout
    except subprocess.CalledProcessError:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


bible_text = open(OVERRIDE).read() if OVERRIDE else blob(REV, BIBLE)
sections = set()
for line in bible_text.split("\n"):
    m = re.match(r"^(#{2,3})\s+(\d+(?:\.\d+)*)\.?\s+", line)
    if m:
        sections.add(m.group(2))

# Only cites that NAME the bible on the same line. Conservative in the other
# direction from the census: zero false attribution, so a failure is real.
BIBLE_SCOPED = re.compile(
    r"(?:PROJECT_BIBLE(?:\.md)?|\bbible\b|\bBible\b)[^\n]{0,80}?§\s*(\d+(?:\.\d+)*)"
    r"|§\s*(\d+(?:\.\d+)*)[^\n]{0,40}?\bof the bible\b", re.I)

files = [f for f in subprocess.run(["git", "ls-tree", "-r", "--name-only", REV],
                                   capture_output=True, text=True,
                                   check=True).stdout.split("\n") if f]
ok, bad = 0, []
per_sec = defaultdict(int)
for rel in files:
    if rel in SELF:
        continue
    text = blob(REV, rel)
    if text is None or "§" not in text:
        continue
    for i, line in enumerate(text.split("\n"), 1):
        for m in BIBLE_SCOPED.finditer(line):
            num = m.group(1) or m.group(2)
            per_sec[num] += 1
            if num in sections:
                ok += 1
            else:
                bad.append((rel, i, num, line.strip()[:110]))

print(f"anchor_resolve @ {REV}"
      f"{' (bible from ' + OVERRIDE + ')' if OVERRIDE else ''}")
print(f"  bible headings: {len(sections)}")
print(f"  explicitly bible-scoped cites in the shipping tree: {ok + len(bad)}")
print(f"  RESOLVED: {ok}   UNRESOLVED: {len(bad)}")
print("  per-section: " + " ".join(
    f"§{k}={v}" for k, v in sorted(per_sec.items(),
                                   key=lambda kv: [int(x) for x in kv[0].split(".")])))
for rel, i, num, line in bad[:25]:
    print(f"    UNRESOLVED §{num}  {rel}:{i}  {line}")
sys.exit(1 if bad else 0)
