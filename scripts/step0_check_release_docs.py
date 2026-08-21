import csv, datetime, io, json, re, subprocess, sys

def at_head(path):
    r = subprocess.run(['git', 'show', f'HEAD:{path}'], capture_output=True)
    if r.returncode != 0:
        print(f"FAIL cannot read {path} at HEAD: {r.stderr.decode().strip()}")
        sys.exit(1)
    return r.stdout.decode('utf-8', 'replace')

head = subprocess.run(['git','rev-parse','--short','HEAD'],
                      capture_output=True, text=True).stdout.strip()
print(f"validating the COMMIT, not the working tree.  HEAD = {head}\n")

# The one pin.  Every version-scoped arm below derives from it, so a release bump is
# this line and nothing else (MAC-760).  Deliberately NOT derived from the CHANGELOG's
# top heading: a gate that reads its own subject cannot fail, and the whole point of
# this arm is to catch docs that did not move with the release.
RELEASE = '1.8.0'
fail = []

rows = [r for r in csv.reader(io.StringIO(at_head('exports/argus_export.csv')))
        if r and not r[0].startswith('#')]
active = len(rows) - 1
def n(p):
    d = json.loads(at_head(p))
    return len(d.get('entries', d) if isinstance(d, dict) else d)
std, high = n('exports/argus_export.json'), n('exports/argus_export_high_confidence.json')
print(f"artifacts at HEAD:  active={active:,}  standard={std:,}  high-confidence={high:,}\n")

readme = at_head('README.md')

for path, truth in sorted({'exports/argus_export.csv': active,
                           'exports/argus_export_high_confidence.json': high,
                           'exports/argus_export.json': std}.items(),
                          key=lambda kv: -len(kv[0])):
    m = re.search(r'^\|\s*`' + re.escape(path) + r'`\s*\|\s*([\d,]+)\s*\|', readme, re.M)
    if not m:
        fail.append(f"README exports table has no row for `{path}`"); continue
    claim = int(m.group(1).replace(',', ''))
    print(f"{'ok  ' if claim==truth else 'FAIL'} exports table `{path}`: README {claim:,} vs artifact {truth:,}")
    if claim != truth:
        fail.append(f"exports table `{path}`: README {claim:,} != artifact {truth:,}")

m = re.search(r'\*\*([\d,]+) active canonical identifiers\*\*', readme)
if not m:
    fail.append("README headline bullet 'N active canonical identifiers' not found")
else:
    claim = int(m.group(1).replace(',', ''))
    print(f"{'ok  ' if claim==active else 'FAIL'} headline bullet: README {claim:,} vs artifact {active:,}")
    if claim != active:
        fail.append(f"headline bullet: README {claim:,} != artifact {active:,}")

# docs/USER_GUIDE.md states each artifact's count in its own section heading.
# Scope to the release-version headings: line 148 says "41,508 active identifiers at
# v1.6.2 ship", which is correct history and must survive.
guide = at_head('docs/USER_GUIDE.md')
for path, truth in sorted({'exports/argus_export.csv': active,
                           'exports/argus_export_high_confidence.json': high,
                           'exports/argus_export.json': std}.items(),
                          key=lambda kv: -len(kv[0])):
    m = re.search(r'^###\s+`' + re.escape(path)
                  + r'`\s*\(([\d,]+)\s+(?:data\s+)?rows at v([\d.]+)\)', guide, re.M)
    if not m:
        fail.append(f"USER_GUIDE has no '### `{path}` (N rows at vX)' heading"); continue
    claim, ver = int(m.group(1).replace(',', '')), m.group(2)
    ok = claim == truth and ver == RELEASE
    print(f"{'ok  ' if ok else 'FAIL'} USER_GUIDE `{path}`: says {claim:,} at v{ver}, "
          f"artifact has {truth:,} at v{RELEASE}")
    if not ok:
        fail.append(f"USER_GUIDE `{path}`: {claim:,} at v{ver} != {truth:,} at v{RELEASE}")

# This arm used to compare against '2026-07-28', the v1.7.0 drafting placeholder.  A
# literal like that is dead the moment the release moves and the arm goes vacuous
# silently, so the floor is derived instead: a release cannot honestly be dated earlier
# than the artifacts it ships.  `exported_at` is read from the export _meta at HEAD, so
# this arm re-points itself every release and cannot go stale (MAC-760).
stamp = json.loads(at_head('exports/argus_export.json'))['_meta']['exported_at'][:10]
m = re.search(r'^##\s*v' + re.escape(RELEASE) + r'\s*-\s*(\S+)', at_head('CHANGELOG.md'), re.M)
if not m:
    fail.append(f"CHANGELOG has no '## v{RELEASE} - <date>' heading")
else:
    d = m.group(1)
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d):
        why = 'is not an ISO-8601 YYYY-MM-DD date'
    else:
        try:
            why = ('' if datetime.date.fromisoformat(d) >= datetime.date.fromisoformat(stamp)
                   else f'predates the exports it ships (exported_at {stamp})')
        except ValueError:
            why = 'is not a real calendar date'
    print(f"{'ok  ' if not why else 'FAIL'} CHANGELOG v{RELEASE} dated {d}"
          + ('' if not why else f'  ({why})'))
    if why:
        fail.append(f"CHANGELOG v{RELEASE} dated {d} {why}")

# the release's own regen commit broke this tree-wide guard (CTO, MAC-612, 22:40Z).
# capture the real exit code: this script prints its verdict and exits non-zero, and
# piping it to `tail` would hand you tail's status instead of the guard's.
g = subprocess.run(['python3', 'scripts/check_commit_cites.py'],
                   capture_output=True, text=True, timeout=600)
print(f"{'ok  ' if g.returncode==0 else 'FAIL'} check_commit_cites.py (MAC-704) exit {g.returncode}")
if g.returncode != 0:
    for l in g.stdout.splitlines():
        if re.search(r'^\s+[A-Z]:\s', l): print("       ", l.strip())
    fail.append(f"check_commit_cites.py exits {g.returncode}, tree-wide guard is red")

dirty = subprocess.run(['git','status','--porcelain','--untracked-files=no','--',
                        'README.md','CHANGELOG.md','docs/USER_GUIDE.md','exports/'],
                       capture_output=True, text=True).stdout.strip()
if dirty:
    print("\nFAIL release content is modified but NOT committed:")
    for l in dirty.splitlines(): print("   ", l)
    fail.append("uncommitted release content: the fix is in the worktree, not in the commit you would tag")

print()
if fail:
    print(f"STEP 0 FAILED ({len(fail)}):")
    for x in fail: print("  -", x)
    print("\nDo not push or tag. Tell the CEO which lines failed.")
    sys.exit(1)
print("STEP 0 PASSED. The commit at HEAD is self-consistent. Continue to step 1.")
