#!/usr/bin/env python3
"""Refuse a push whose stack carries an object GitHub's pre-receive hook will reject.

BRIEF_STANDARDS.md R10, size dimension. STAGED, not standing -- MAC-635, filed out of
MAC-610. Companion to `scripts/check_staged_paths.py`, and deliberately a SEPARATE script
rather than another C-check inside it, because the two answer different questions:

  check_staged_paths.py C4/C5   what is in the index RIGHT NOW.
  this script                   what is already in the stack.

C4 is blind to history by construction. Once `git commit` runs, the index is empty and C4
has nothing left to look at -- the blob is in the object graph and every subsequent C4 is
green. `db/argus.db` at 329,711,616 bytes entered at `ceff54f`, was re-committed at
`8e905cf` and `4b1e0d9`, and a per-commit index check run before any of the three would have
caught the first and said nothing about a stack already carrying it. This is the instrument
that answers "is the stack pushable", and it is the one the push gate must run.

`git push --dry-run` does not substitute. It validates the local side only; the 100 MiB
limit lives in a GitHub pre-receive hook that fires on a real push, at which point the blob
is in history and the remedy is a rewrite rather than a `git rm --cached`.

Usage:
    python3 scripts/check_push_blob_sizes.py
    python3 scripts/check_push_blob_sizes.py --fetch
    python3 scripts/check_push_blob_sizes.py --base origin/main --head HEAD
    python3 scripts/check_push_blob_sizes.py --max-bytes 20000000 --warn-bytes 10000000  # positive control

The base is NOT refreshed unless `--fetch` is given, and the resolved base sha is printed
either way. An operator hand-push can move remote `main` out of band between one ratification
and the next, so a stale `origin/main` silently narrows the object set this sweeps.

R7 positive control: this check reports zero on a clean stack, and a zero-yield check that
has never been shown firing is not evidence. `--max-bytes` exists so the ceiling can be
dropped onto the same range until it fires. Do that before quoting a zero.

Drop `--warn-bytes` with it. The warn default (50000000) must stay below the ceiling, so
lowering `--max-bytes` alone below that default exits 2 (usage error), not 1 — the control
never reaches the blob scan and certifies nothing. Exit 2 is not a firing instrument.

Exit 0 = PASS or WARN. Exit 1 = at least one blob over the ceiling. Exit 2 = usage error.
Exit 3 = SKIPPED: the range could not be resolved, so the stack is uncertified, not clean.
Same four codes and the same meanings as `check_staged_paths.py`; a push gate that had to
remember two exit-code dialects would eventually read one as the other.
"""
import argparse
import subprocess
import sys

DEFAULT_BASE = "origin/main"
DEFAULT_HEAD = "HEAD"

# Identical to check_staged_paths.py, and identical on purpose: a stack-level ceiling looser
# than the per-commit one would let a blob through the gate that ran first and stop it at the
# gate that runs last, after it is already unfixable without a rewrite.
DEFAULT_MAX_BLOB_BYTES = 100_000_000
DEFAULT_WARN_BLOB_BYTES = 50_000_000

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_UNEVALUATED = 3

assert len({EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_UNEVALUATED}) == 4, "exit codes collide"
assert DEFAULT_WARN_BLOB_BYTES < DEFAULT_MAX_BLOB_BYTES, "warn threshold not below ceiling"


def git(*args, check=True):
    proc = subprocess.run(
        ("git",) + args, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            "git %s failed (%d): %s" % (" ".join(args), proc.returncode, proc.stderr.strip())
        )
    return proc.stdout


def repo_root():
    return git("rev-parse", "--show-toplevel").strip()


def resolve(root, ref):
    """Commit sha for `ref`, or None when the ref does not exist."""
    proc = subprocess.run(
        ("git", "-C", root, "rev-parse", "--verify", "--quiet", ref + "^{commit}"),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.stdout.strip() or None


def range_objects(root, base, head):
    """[(sha, path)] for every object reachable from head and NOT from base.

    `rev-list --objects <base>..<head>` already excludes objects reachable from base, so a
    blob that origin/main already carries is not re-reported here. That matters: the question
    is what THIS push would add, and a pre-receive hook only inspects incoming objects.
    """
    out = git("-C", root, "rev-list", "--objects", "%s..%s" % (base, head))
    objs = []
    for line in out.splitlines():
        if not line:
            continue
        sha, _, path = line.partition(" ")
        objs.append((sha, path))
    return objs


def batch_check(root, objs):
    """[(sha, type, size, path)] via one `cat-file --batch-check`, plus the unresolved shas.

    `%(rest)` is required in the format: without it `cat-file --batch-check` treats the whole
    input line as an object spec, and `rev-list --objects` emits `<sha> <path>`, so every
    line with a path would come back `missing`.
    """
    if not objs:
        return [], []
    payload = "".join("%s %s\n" % (sha, path) for sha, path in objs)
    proc = subprocess.run(
        (
            "git",
            "-C",
            root,
            "cat-file",
            "--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)",
        ),
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    resolved, unresolved = [], []
    for line in proc.stdout.splitlines():
        parts = line.split(" ", 3)
        if len(parts) < 3 or parts[1] in ("missing", "ambiguous"):
            unresolved.append(line)
            continue
        resolved.append((parts[0], parts[1], int(parts[2]), parts[3] if len(parts) > 3 else ""))
    return resolved, unresolved


def adding_commit(root, base, head, path, sha):
    """The earliest commit in the range whose tree holds `sha` at `path`, or None.

    Walks `--reverse` and stops at the first hit, so a blob re-committed three times is
    attributed to the commit that introduced it rather than the one that touched it last.
    """
    if not path:
        return None
    out = git("-C", root, "rev-list", "--reverse", "%s..%s" % (base, head), "--", path)
    for commit in out.split():
        got = git(
            "-C", root, "rev-parse", "--verify", "--quiet", "%s:%s" % (commit, path), check=False
        ).strip()
        if got == sha:
            return commit
    return None


def describe(root, commit):
    return git("-C", root, "log", "-1", "--format=%h %s", commit).strip()


def main(argv):
    parser = argparse.ArgumentParser(prog="check_push_blob_sizes.py", add_help=True)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--head", default=DEFAULT_HEAD)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BLOB_BYTES)
    parser.add_argument("--warn-bytes", type=int, default=DEFAULT_WARN_BLOB_BYTES)
    parser.add_argument(
        "--fetch", action="store_true", help="refresh the base ref before comparing"
    )
    args = parser.parse_args(argv[1:])

    if args.warn_bytes >= args.max_bytes:
        print(
            "usage error: --warn-bytes (%d) must be below --max-bytes (%d)"
            % (args.warn_bytes, args.max_bytes),
            file=sys.stderr,
        )
        return EXIT_USAGE

    root = repo_root()

    fetched = False
    if args.fetch:
        remote = args.base.split("/")[0] if "/" in args.base else "origin"
        proc = subprocess.run(
            ("git", "-C", root, "fetch", remote), capture_output=True, text=True
        )
        fetched = proc.returncode == 0
        if not fetched:
            print("    note  `git fetch %s` failed; comparing against the base as it stands" % remote)

    base_sha = resolve(root, args.base)
    head_sha = resolve(root, args.head)
    if base_sha is None or head_sha is None:
        missing = args.base if base_sha is None else args.head
        print(
            "SKIPPED  %s..%s  (0 objects, 0 blobs)\n"
            "    SKIP  ref %r does not resolve to a commit. The range was NOT enumerated, so "
            "this stack is uncertified for object size, not clear of it. `git fetch` first, or "
            "name the base with --base." % (args.base, args.head, missing)
        )
        return EXIT_UNEVALUATED

    objs = range_objects(root, base_sha, head_sha)
    resolved, unresolved = batch_check(root, objs)
    blobs = [(sha, size, path) for sha, otype, size, path in resolved if otype == "blob"]

    fails, warns, unevaluated = [], [], []
    if unresolved:
        unevaluated.append(
            "%d object(s) in the range did not resolve to a size: %s. Size was NOT evaluated "
            "over the whole range." % (len(unresolved), "; ".join(unresolved[:3]))
        )

    for sha, size, path in sorted(blobs, key=lambda b: -b[1]):
        if size <= args.warn_bytes:
            continue
        commit = adding_commit(root, base_sha, head_sha, path, sha)
        where = describe(root, commit) if commit else "(no commit in range holds it at this path)"
        if size > args.max_bytes:
            fails.append(
                "%s  %d bytes  blob %s\n"
                "          added by %s\n"
                "          over the %d-byte ceiling; GitHub's pre-receive hook rejects at "
                "104857600 and `git push --dry-run` will not tell you."
                % (path or "(no path)", size, sha[:12], where, args.max_bytes)
            )
        else:
            warns.append(
                "%s  %d bytes  blob %s\n          added by %s"
                % (path or "(no path)", size, sha[:12], where)
            )

    if fails:
        status, code = "FAIL", EXIT_FAIL
    elif unevaluated:
        status, code = "SKIPPED", EXIT_UNEVALUATED
    elif warns:
        status, code = "WARN", EXIT_OK
    else:
        status, code = "PASS", EXIT_OK

    largest = max((b[1] for b in blobs), default=0)
    print(
        "%s  %s..%s  (%d objects, %d blobs)"
        % (status, args.base, args.head, len(objs), len(blobs))
    )
    print(
        "    base %s = %s%s"
        % (args.base, base_sha[:12], "  (fetched)" if fetched else "  (NOT fetched this run)")
    )
    print("    head %s = %s" % (args.head, head_sha[:12]))
    print(
        "    largest blob %d bytes; ceiling %d; warn %d"
        % (largest, args.max_bytes, args.warn_bytes)
    )
    for note in unevaluated:
        print("    SKIP  %s" % note)
    for f in fails:
        print("    FAIL  %s" % f)
    for w in warns:
        print("    warn  %s" % w)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
