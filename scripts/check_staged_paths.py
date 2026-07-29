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

Paid for by MAC-573 `cf9031a`, which staged three paths it had every right to stage and
swept the MAC-579 lane's uncommitted `marker = last_out or started` fix out of
`scripts/run_liveness_probe.py` along the way. MAC-579's own commit `9fad501` landed six
minutes later carrying only `tests/test_run_liveness_probe.py` -- the test for a fix that
was no longer in the tree. Disclosed at `8082d32`, not repaired.

Usage:
    python3 scripts/check_staged_paths.py baseline --label MAC-592 <path> [<path> ...]
    python3 scripts/check_staged_paths.py check    --label MAC-592 <path> [<path> ...]

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
import json
import os
import subprocess
import sys

BASELINE_DIR = "argus_stage_baseline"
DIFF_PREVIEW_CHARS = 4000

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


def cmd_check(root, label, declared):
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
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv[1:])

    root = repo_root()
    declared = [rel(p, root) for p in args.paths]
    if len(set(declared)) != len(declared):
        print("usage error: duplicate declared path", file=sys.stderr)
        return EXIT_USAGE

    if args.mode == "baseline":
        return cmd_baseline(root, args.label, declared)
    return cmd_check(root, args.label, declared)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
