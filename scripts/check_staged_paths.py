#!/usr/bin/env python3
"""Gate a commit's staged path set against the paths the lane declared it would touch.

BRIEF_STANDARDS.md R10. Every agent shares one worktree, one index and one branch, so
`git add` reaches bytes that are not yours in two distinct ways. This gate covers both,
and reports which of them it could not evaluate rather than passing silently.

  C1 SET     `git diff --cached` path set == the declared path set.
             Catches an undeclared file riding along in the commit.

  C2 SWEEP   a declared path that was ALREADY dirty when the lane began.
             `git add <path>` stages the whole file, so a peer's uncommitted edits to a
             path you legitimately own land under your message. This is the cf9031a class
             and C1 cannot see it -- cf9031a's staged set was exactly its declared set.
             Needs a baseline. With no baseline this reports SKIPPED, never PASS.

  C3 DRIFT   a declared path carrying unstaged residue at check time.
             The file moved under you between `git add` and `git commit`.

  C4 SIZE    a staged blob over the push ceiling (default 100,000,000 bytes), or over
             GitHub's own 50 MB warning threshold.  STAGED, not standing -- MAC-635.

  C5 ARTIFACT  a staged path matching a large-artifact pattern, at any size.
             STAGED, not standing -- MAC-635.

C4/C5 are a WIDENING of R10, from path-identity to path-identity plus object size, and are
named as one rather than folded in as a clarification. Filed by MAC-635 out of MAC-610:
`db/argus.db`, 329,711,616 bytes, entered the stack at `ceff54f` and was re-committed at
`8e905cf` and `4b1e0d9` with nothing in the toolchain objecting. C1-C3 are all structurally
size-blind -- they compare path sets and dirty state, and a 329 MB database staged at a path
the lane legitimately declared clears every one of them. `.gitignore:12` carries `db/*.db`
and enforces nothing, because gitignore does not bind an already-tracked path; and
`git push --dry-run` validates only the local side, so GitHub's 100 MB pre-receive hook is
the first instrument in the chain that objects, by which point the blob is already history.

Size and pattern are two INDEPENDENT triggers, not one. A tracked path escaping gitignore is
the MAC-610 failure exactly, and it is a defect at 1 byte as much as at 329 MB.

C5 reads the same staged-entry set as C4, which excludes deletions on purpose: staging the
REMOVAL of `db/argus.db` is the remedy MAC-610 wants, and a gate that blocked its own fix
would be worse than no gate.

Paid for by MAC-573 `cf9031a`, which staged three paths it had every right to stage and
swept the MAC-579 lane's uncommitted `marker = last_out or started` fix out of
`scripts/run_liveness_probe.py` along the way. MAC-579's own commit `9fad501` landed six
minutes later carrying only `tests/test_run_liveness_probe.py` -- the test for a fix that
was no longer in the tree. Disclosed at `8082d32`, not repaired.

Usage:
    python3 scripts/check_staged_paths.py baseline --label MAC-592 <path> [<path> ...]
    python3 scripts/check_staged_paths.py check    --label MAC-592 <path> [<path> ...]
    python3 scripts/check_staged_paths.py check    --label MAC-592 --max-bytes 26401005 <path>

`--max-bytes` and `--warn-bytes` are configurable so the ceiling can be lowered onto a tree
you already have, which is how C4 gets a positive control without a 100 MB fixture: drop the
ceiling one byte below a real staged blob and the check must fire. R7 -- a size check that
has never been shown failing cannot support a green result.

Take the baseline BEFORE your first write. A path you are creating in this lane must read
`absent` at baseline; a path already `dirty` or `untracked` at baseline belongs to someone
else, and R10 sends you to `git apply --cached` rather than `git add`.

Exit 0 = PASS or WARN. Exit 1 = at least one FAIL. Exit 2 = usage error.
Exit 3 = SKIPPED: a check could not be evaluated, so this commit is uncertified.

MAC-599. Exit 3 rather than the 2 the issue proposed, because 2 was already spent three
ways -- a duplicate declared path, a missing `--label`, and a bad mode all exit 2, the
last two from argparse, which hard-codes it and cannot be retargeted. Reusing 2 would
have made "the sweep class was never evaluated" indistinguishable from "you typed the
command wrong": the same conflation this issue exists to remove, one exit code along.
Un-evaluated is kept distinct from 1 as well; a lane that skipped the baseline has an
uncertified commit, not a proven sweep, and the two want different remedies.
"""
import argparse
import fnmatch
import json
import os
import subprocess
import sys

BASELINE_DIR = "argus_stage_baseline"
DIFF_PREVIEW_CHARS = 4000

# Decimal, not binary, and deliberately below GitHub's hard 100 MiB pre-receive limit
# (104,857,600). Sitting on the boundary means the local gate and the remote hook disagree
# about the last 4.8 MB, and the one that wins that argument is the one you cannot re-run.
DEFAULT_MAX_BLOB_BYTES = 100_000_000
# GitHub's own warning threshold. A WARN exits 0: this is "you are approaching the wall",
# not "you hit it", and an exports/ build artifact is allowed to grow.
DEFAULT_WARN_BLOB_BYTES = 50_000_000

# Mirrors the large-artifact block of `.gitignore`. Deliberately a copy and not a parse of
# that file: gitignore does not bind an already-tracked path, so the file it is copied from
# is the instrument that already failed. These patterns are matched with fnmatch, whose `*`
# crosses `/` where gitignore's does not -- broader, and broader is the fail-closed
# direction for a check whose whole job is to refuse a database.
LARGE_ARTIFACT_PATTERNS = (
    "db/*.db",
    "db/*.db-wal",
    "db/*.db-shm",
    "db/*.db-journal",
    "db/argus.db*.bak",
)

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2  # also argparse's own hard-coded exit for a malformed argv
EXIT_UNEVALUATED = 3

# Structural guard, not decoration: the whole point of a separate un-evaluated code is
# that a caller can tell the four outcomes apart. Two of these constants collapsing to
# the same integer would silently restore the defect MAC-599 removed, and every fixture
# in tests/test_staged_paths.py would still pass, because each asserts its own code in
# isolation. Compare the constants to each other, where the collision actually lives.
assert len({EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_UNEVALUATED}) == 4, "exit codes collide"

# Same class of guard for the size thresholds. If WARN ever rose to or above FAIL, every
# oversize blob would be classified by the `elif` below and downgraded to a warning that
# exits 0 -- the gate would still print output, still look configured, and pass the very
# input it exists to reject. That is the post-condition-mirrors-its-transform shape.
assert DEFAULT_WARN_BLOB_BYTES < DEFAULT_MAX_BLOB_BYTES, "warn threshold not below ceiling"


def git(*args, check=True):
    """Run a git command in the repo and return stdout as text."""
    proc = subprocess.run(
        ("git",) + args, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and proc.returncode != 0:
        raise RuntimeError("git %s failed (%d): %s" % (" ".join(args), proc.returncode, proc.stderr.strip()))
    return proc.stdout


def repo_root():
    return git("rev-parse", "--show-toplevel").strip()


def git_dir(root):
    return git("-C", root, "rev-parse", "--absolute-git-dir").strip()


def rel(path, root):
    """Repo-relative, forward-slashed path for `path`, which may be relative to cwd."""
    return os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")


def porcelain(path, root):
    """`git status --porcelain` status code for one path, or "" when it reports nothing."""
    out = git("-C", root, "status", "--porcelain", "-z", "--", path)
    if not out.strip("\0"):
        return ""
    # -z records are NUL-terminated; the first 2 bytes are the XY status code.
    return out.split("\0")[0][:2]


def path_state(path, root):
    """One of: dirty (modified/staged), untracked, clean (tracked, unmodified), absent."""
    code = porcelain(path, root)
    if code == "??":
        return "untracked"
    if code:
        return "dirty"
    return "clean" if os.path.exists(os.path.join(root, path)) else "absent"


def staged_paths(root):
    """The repo-relative path set in the index.

    `--no-renames` is deliberate: with rename detection on, a rename collapses to the new
    name alone and the old path silently leaves the set this gate is comparing.
    """
    out = git("-C", root, "diff", "--cached", "--name-only", "--no-renames", "-z")
    return {p for p in out.split("\0") if p}


def staged_entries(root):
    """[(path, dst_blob_sha)] for every staged entry that LEAVES a blob in the tree.

    `--raw -z` records are `:<srcmode> <dstmode> <srcsha> <dstsha> <status>\\0<path>\\0`.

    Two kinds of entry are dropped, both on purpose:

      deletions   the destination sha is all-zero. Staging the removal of a 329 MB database
                  is the MAC-610 remedy; a size gate that blocked its own fix is worse than
                  no gate.
      gitlinks    mode 160000 is a submodule commit, not a blob, and has no object size here.

    `--abbrev=40` is load-bearing, not tidiness. `--raw` abbreviates object names by default,
    and `cat-file --batch-check` echoes back the FULL name, so keying the size lookup on an
    abbreviated sha misses every entry -- and misses SILENTLY, as an un-evaluated size rather
    than an oversize blob. Caught by the three pre-existing C1/C2/C3 negative controls in
    tests/test_staged_paths.py, which went SKIPPED on a clean two-file commit.
    """
    out = git("-C", root, "diff", "--cached", "--raw", "--no-renames", "--abbrev=40", "-z")
    fields = out.split("\0")
    entries = []
    i = 0
    while i + 1 < len(fields):
        meta = fields[i]
        if not meta.startswith(":"):
            i += 1
            continue
        parts = meta[1:].split()
        if len(parts) < 5:
            i += 1
            continue
        dstmode, dstsha, status = parts[1], parts[3], parts[4]
        path = fields[i + 1]
        i += 2
        if status.startswith("D") or set(dstsha) == {"0"} or dstmode == "160000":
            continue
        entries.append((path, dstsha))
    return entries


def blob_sizes(root, shas):
    """{sha: size} from one `cat-file --batch-check`.

    A sha that resolves to `missing`, or to a non-blob, is absent from the returned mapping
    rather than defaulted to 0. The caller reports those as un-evaluated: a size the gate
    could not read is not a size under the ceiling.
    """
    if not shas:
        return {}
    proc = subprocess.run(
        ("git", "-C", root, "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"),
        input="\n".join(shas) + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    sizes = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] == "blob":
            sizes[parts[0]] = int(parts[2])
    return sizes


def large_artifact_match(path):
    """The `.gitignore` large-artifact pattern this path matches, or None."""
    for pattern in LARGE_ARTIFACT_PATTERNS:
        if fnmatch.fnmatch(path, pattern):
            return pattern
    return None


def unstaged_paths(root):
    out = git("-C", root, "diff", "--name-only", "--no-renames", "-z")
    return {p for p in out.split("\0") if p}


def baseline_path(root, label):
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in label)
    return os.path.join(git_dir(root), BASELINE_DIR, safe + ".json")


def cmd_baseline(root, label, declared):
    record = {"label": label, "head": git("-C", root, "rev-parse", "HEAD").strip(), "paths": {}}
    for path in declared:
        state = path_state(path, root)
        entry = {"state": state}
        if state in ("dirty", "untracked"):
            if state == "dirty":
                entry["pre_existing_diff"] = git("-C", root, "diff", "HEAD", "--", path)[
                    :DIFF_PREVIEW_CHARS
                ]
        record["paths"][path] = entry

    dest = baseline_path(root, label)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)

    print("baseline  %s  (%d paths)  -> %s" % (label, len(declared), dest))
    for path in declared:
        state = record["paths"][path]["state"]
        flag = "  <-- NOT YOURS; see R10" if state in ("dirty", "untracked") else ""
        print("    %-10s %s%s" % (state, path, flag))
    return 0


def cmd_check(root, label, declared, max_bytes=DEFAULT_MAX_BLOB_BYTES, warn_bytes=DEFAULT_WARN_BLOB_BYTES):
    fails, warns, unevaluated = [], [], []
    declared_set = set(declared)

    # --- C1: staged path set == declared path set.
    staged = staged_paths(root)
    extra = sorted(staged - declared_set)
    missing = sorted(declared_set - staged)
    if extra:
        fails.append(
            "C1 %d staged path(s) were never declared: %s. An undeclared path in the index "
            "is another lane's work riding along under your commit message." % (len(extra), ", ".join(extra))
        )
    if missing:
        fails.append(
            "C1 %d declared path(s) are not staged: %s. Either stage them or drop them from "
            "the declaration -- a declaration that overstates the commit is not a check."
            % (len(missing), ", ".join(missing))
        )

    # --- C2: a declared path already dirty when the lane began. C1 is structurally blind to
    # this: the sweep happens INSIDE a path the lane legitimately declared.
    bpath = baseline_path(root, label)
    if not os.path.exists(bpath):
        unevaluated.append(
            "C2 SKIPPED -- no baseline at %s. The cf9031a sweep class was NOT evaluated. "
            "Run `check_staged_paths.py baseline --label %s <paths>` before your first write."
            % (bpath, label)
        )
    else:
        with open(bpath, encoding="utf-8") as fh:
            base = json.load(fh)
        unrecorded = sorted(declared_set - set(base["paths"]))
        if unrecorded:
            fails.append(
                "C2 %d declared path(s) absent from the baseline: %s. An unbaselined path is "
                "unevaluated, not clean." % (len(unrecorded), ", ".join(unrecorded))
            )
        for path in sorted(declared_set & set(base["paths"])):
            entry = base["paths"][path]
            state = entry["state"]
            # Structural guard: `state` is a closed enum written by cmd_baseline. A value
            # outside it means the baseline was hand-edited or written by another version,
            # and a check that silently accepts an unknown state is decoration.
            if state not in ("dirty", "untracked", "clean", "absent"):
                fails.append("C2 baseline for %s carries unknown state %r" % (path, state))
                continue
            if state in ("dirty", "untracked"):
                preview = entry.get("pre_existing_diff", "")
                head = "\n".join(preview.splitlines()[:12])
                fails.append(
                    "C2 %s was already %s when this lane began; `git add` stages the whole "
                    "file, so this commit carries another lane's uncommitted work. Stage only "
                    "your own bytes:\n"
                    "        git show HEAD:%s > /tmp/base && diff -u /tmp/base <yours> | "
                    "git apply --cached -\n"
                    "      pre-existing diff at baseline:\n%s"
                    % (path, state, path, head or "        (not recorded)")
                )

    # --- C3: unstaged residue on a declared path at check time.
    drifted = sorted(declared_set & unstaged_paths(root))
    if drifted:
        warns.append(
            "C3 %d declared path(s) have unstaged changes at check time: %s. Either you staged "
            "by hunk (intended) or the file moved under you after `git add` (not intended). "
            "Re-read `git diff --cached -- %s` before committing."
            % (len(drifted), ", ".join(drifted), drifted[0])
        )

    # --- C4/C5: object size and large-artifact pattern over the STAGED SET, not the declared
    # set. A blob is a push blocker whether or not the lane declared it, and running these on
    # `declared_set` would make them dependent on C1 already having passed.
    entries = staged_entries(root)
    sizes = blob_sizes(root, sorted({sha for _, sha in entries}))

    unsized = sorted(path for path, sha in entries if sha not in sizes)
    if unsized:
        unevaluated.append(
            "C4 SKIPPED -- no object size resolved for %d staged path(s): %s. Blob size was "
            "NOT evaluated on this commit, so it is uncertified for size, not clear of it."
            % (len(unsized), ", ".join(unsized))
        )

    for path, sha in sorted(entries):
        size = sizes.get(sha)
        if size is None:
            continue
        if size > max_bytes:
            fails.append(
                "C4 %s is %d bytes staged, over the %d-byte ceiling. GitHub rejects at "
                "104857600 in a pre-receive hook that `git push --dry-run` never invokes, so "
                "the blob would enter local history and be discovered only at push. Remove it "
                "from the index (`git rm --cached %s`) before committing."
                % (path, size, max_bytes, path)
            )
        elif size > warn_bytes:
            warns.append(
                "C4 %s is %d bytes staged, over the %d-byte warning threshold but under the "
                "%d-byte ceiling. GitHub warns here. A build artifact growing toward the wall "
                "is expected; a database arriving at it is not."
                % (path, size, warn_bytes, max_bytes)
            )

    flagged = [(p, large_artifact_match(p)) for p, _ in sorted(entries)]
    flagged = [(p, pat) for p, pat in flagged if pat]
    if flagged:
        fails.append(
            "C5 %d staged path(s) match a .gitignore large-artifact pattern and are barred at "
            "any size: %s. gitignore does not bind an already-tracked path, which is exactly "
            "how db/argus.db was re-committed three times past `.gitignore:12` (MAC-610)."
            % (len(flagged), ", ".join("%s [%s]" % (p, pat) for p, pat in flagged))
        )

    # Precedence: FAIL > SKIPPED > WARN > PASS. `unevaluated` outranks `warns` because a
    # WARN exits 0 -- letting a warning own the headline would put the un-evaluated sweep
    # class back behind a green exit code, which is the defect, relocated.
    if fails:
        status, code = "FAIL", EXIT_FAIL
    elif unevaluated:
        status, code = "SKIPPED", EXIT_UNEVALUATED
    elif warns:
        status, code = "WARN", EXIT_OK
    else:
        status, code = "PASS", EXIT_OK

    print("%s  %s  (%d declared, %d staged)" % (status, label, len(declared_set), len(staged)))
    for note in unevaluated:
        print("    SKIP  %s" % note)
    for f in fails:
        print("    FAIL  %s" % f)
    for w in warns:
        print("    warn  %s" % w)
    return code


def main(argv):
    parser = argparse.ArgumentParser(prog="check_staged_paths.py", add_help=True)
    parser.add_argument("mode", choices=("baseline", "check"))
    parser.add_argument("--label", required=True, help="lane label, e.g. the issue id")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BLOB_BYTES,
        help="C4 hard-FAIL ceiling for any staged blob (default %d)" % DEFAULT_MAX_BLOB_BYTES,
    )
    parser.add_argument(
        "--warn-bytes",
        type=int,
        default=DEFAULT_WARN_BLOB_BYTES,
        help="C4 warning threshold (default %d)" % DEFAULT_WARN_BLOB_BYTES,
    )
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv[1:])

    root = repo_root()
    declared = [rel(p, root) for p in args.paths]
    if len(set(declared)) != len(declared):
        print("usage error: duplicate declared path", file=sys.stderr)
        return EXIT_USAGE
    if args.warn_bytes >= args.max_bytes:
        print(
            "usage error: --warn-bytes (%d) must be below --max-bytes (%d); a warning "
            "threshold at or above the ceiling downgrades every oversize blob to exit 0"
            % (args.warn_bytes, args.max_bytes),
            file=sys.stderr,
        )
        return EXIT_USAGE

    if args.mode == "baseline":
        return cmd_baseline(root, args.label, declared)
    return cmd_check(root, args.label, declared, args.max_bytes, args.warn_bytes)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
