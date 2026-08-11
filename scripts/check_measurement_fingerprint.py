#!/usr/bin/env python3
"""Fingerprint the worktree before and after a measurement whose number will be cited.

BRIEF_STANDARDS.md R11. Every agent shares one worktree, so a sibling lane re-deriving its
artifacts while you are counting rows changes the bytes under your measurement. The number
you cite then describes a tree that no longer exists, and nothing in the commit graph
records that it happened.

Three terms, folded into one digest. The third is the one that reaches the proof.

  T1 HEAD       `git rev-parse HEAD`.
                Catches a sibling COMMITTING mid-measurement. Blind to every worktree
                write, which is the founding incident: a lane re-deriving
                `operator_review/MAC-542` moves no ref at all.

  T2 PORCELAIN  `git status --porcelain=v1 -z`.
                Catches a path CHANGING STATE -- clean to dirty, absent to untracked, and
                index-only writes a worktree diff cannot see. Blind to a write that leaves
                the state string alone, which is the live case rather than a corner:
                "re-deriving" means repeated writes to the SAME paths, so the second write
                onto an already-dirty path leaves ` M path` byte-identical.

  T3 CONTENT    sha256 of every modified or untracked path, as a manifest.
                The only term that survives both controls. T1 and T2 are kept because each
                covers a case T3 alone does not -- a commit that restores identical bytes,
                and a staged-only write -- not because either is sufficient.

Both C1 and C2 below are reproduced cold in `tests/test_measurement_fingerprint.py` as
TERM-ABLATION fixtures: each asserts the weakened fold is SILENT across the mutation and
the full fold FIRES. One arm alone proves nothing -- an ablated fold that moves for an
unrelated reason would pass a fires-only test, and a full fold that never moves would pass
a silent-only test.

Verdict for a moved fingerprint is UNVERIFIED, not void. Void throws away a measurement
that may be entirely unaffected -- a sibling touching `extraction_outputs/` while you count
rows in `db/argus.db` moved the tree and not your number -- and R5 bars inventing a bar
stricter than the registry's own law. UNVERIFIED forces a re-run before the number is
cited and costs nothing when the tree was still.

SCOPE. This binds a measurement whose number leaves the run that produced it -- a board
comment, a brief, a commit message, `operator_review/`, a report handed up. A number that
never leaves its own run does not need it, and neither does an ordinary `pytest`
invocation. Applying it to every subprocess would buy nothing and get the rule ignored.

WHAT THIS COSTS. The content term reads every modified and untracked path in full. In the
argus worktree at `ce48388` that is 455 paths / 789.2 MiB and takes 12.9s per fingerprint,
so 26s per measurement, dominated by two 329,711,616-byte copies of `db/argus.db`. That is
the honest price of the term that reaches the proof. There is deliberately NO flag to
narrow the walk: a `--scope` that shrinks T3 would let a lane trade the only load-bearing
term for wall-clock and still print a verdict, which is the swept-scope-narrower-than-the-
defect-class defect installed as a feature.

`--writes` is not that flag. It names paths THIS measurement is expected to write, so a
lane emitting its own artifact does not fire the gate on itself. Excluded paths are
recorded in the before-record and COUNTED IN THE VERDICT LINE, so an over-broad exclusion
is visible to the ratifier rather than silent. Without it the read-only case works exactly
as specified and every artifact-producing measurement self-reports UNVERIFIED, which is the
shape that gets a rule ignored.

Usage:
    python3 scripts/check_measurement_fingerprint.py before --label MAC-634
    <run the measurement>
    python3 scripts/check_measurement_fingerprint.py after  --label MAC-634

    python3 scripts/check_measurement_fingerprint.py before --label MAC-634 \
        --writes operator_review/MAC-634/rows.csv

Exit 0 = VERIFIED. Exit 1 = UNVERIFIED, re-run before citing the number. Exit 2 = usage
error. Exit 3 = SKIPPED: a term could not be evaluated, so the measurement is uncertified.

Same four codes with the same meanings as `check_staged_paths.py` and
`check_push_blob_sizes.py`. A gate chain whose members spoke different dialects would
eventually have one read as the other.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

BEFORE_DIR = "argus_measurement_fingerprint"
READ_CHUNK = 1 << 20
MAX_REPORTED_PATHS = 20

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2  # also argparse's own hard-coded exit for a malformed argv
EXIT_UNEVALUATED = 3

assert len({EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_UNEVALUATED}) == 4, "exit codes collide"

# The three terms, in fold order. Named so a test can ablate one by name rather than by
# reaching into the fold, and so an ablation cannot silently misspell a term into a no-op.
TERMS = ("head", "porcelain", "content")

# A content entry that could not be read. Distinct from a determinate `deleted:` entry:
# a path git itself reports as deleted is a KNOWN state, while a path that vanished or
# refused a read mid-walk is an un-evaluated one, and the two must not fold alike.
UNREADABLE = "unreadable"


def git(*args):
    return subprocess.run(
        args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).stdout.decode("utf-8", "surrogateescape")


def repo_root():
    return git("git", "rev-parse", "--show-toplevel").strip()


def git_dir(root):
    out = git("git", "-C", root, "rev-parse", "--absolute-git-dir").strip()
    return out


def rel(path, root):
    return os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")


def _zsplit(blob):
    return [p for p in blob.split("\0") if p]


def parse_porcelain(root):
    """[(xy, path, operand)] from `git status --porcelain=v1 -z`.

    -z is NUL-separated and a rename or copy entry carries a second NUL-separated operand
    holding the source path, so the fields cannot simply be zipped with the entries.
    """
    # --untracked-files=all, not the default `normal`. The default collapses an untracked
    # directory to a single `?? dir/` entry, which breaks the --writes filter path-for-path
    # and makes the term blind to a second file appearing in a directory already listed.
    fields = _zsplit(
        git("git", "-C", root, "status", "--porcelain=v1", "--untracked-files=all", "-z")
    )
    entries, index = [], 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if len(field) < 4:
            continue
        xy, path, operand = field[:2], field[3:], None
        if xy[0] in ("R", "C") and index < len(fields):
            operand = fields[index]
            index += 1
        entries.append((xy, path, operand))
    return entries


def deleted_paths(root):
    """Paths git itself calls deleted -- a determinate state, not an unreadable one."""
    return {path for xy, path, _ in parse_porcelain(root) if "D" in xy}


def porcelain_term(root, excluded):
    """The status string, minus the paths this measurement declared it would write.

    The exclusion has to reach this term as well as the content term. A measurement that
    CREATES its artifact adds a `?? path` line, so a content-only exclusion would still
    fire the gate on the lane's own output -- which is the artifact-producing case, the
    common one. Filtering here and hashing the remainder keeps the exclusion honest: the
    lines for every other path are still folded byte-for-byte.
    """
    kept = []
    for xy, path, operand in parse_porcelain(root):
        if path in excluded or (operand is not None and operand in excluded):
            continue
        kept.append("%s %s%s" % (xy, path, "" if operand is None else " <- " + operand))
    return "\n".join(kept)


def hash_file(abs_path):
    digest = hashlib.sha256()
    with open(abs_path, "rb") as handle:
        while True:
            chunk = handle.read(READ_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def content_manifest(root, excluded):
    """path -> digest for every modified or untracked path, minus the declared writes.

    `git ls-files -m` compares worktree to index and `-o` lists untracked files, so the
    union is every path whose bytes can move without a commit. A path present in both is
    listed once.
    """
    listed = sorted(set(_zsplit(git("git", "-C", root, "ls-files", "-mo", "--exclude-standard", "-z"))))
    gone = deleted_paths(root)
    manifest, unevaluated = {}, []
    for path in listed:
        if path in excluded:
            continue
        abs_path = os.path.join(root, path)
        try:
            if os.path.islink(abs_path):
                # Hash the link target, not the referent: repointing a symlink changes what
                # a measurement reads while leaving the referent's own bytes untouched.
                manifest[path] = "symlink:" + hashlib.sha256(
                    os.readlink(abs_path).encode("utf-8", "surrogateescape")
                ).hexdigest()
            elif not os.path.exists(abs_path):
                # Determinate only if git agrees it is deleted. Otherwise it vanished
                # under the walk, which is the race this gate exists to catch.
                manifest[path] = "deleted" if path in gone else UNREADABLE
            elif not os.path.isfile(abs_path):
                manifest[path] = "nonfile"
            else:
                manifest[path] = hash_file(abs_path)
        except OSError as exc:
            manifest[path] = UNREADABLE
            unevaluated.append("%s could not be read (%s)" % (path, exc.__class__.__name__))
    for path, value in manifest.items():
        if value == UNREADABLE and not any(path in note for note in unevaluated):
            unevaluated.append("%s vanished mid-walk and git does not call it deleted" % path)
    return manifest, unevaluated


def compute_terms(root, excluded):
    """The three terms, unfolded. Kept separate so a test can ablate one by name."""
    manifest, unevaluated = content_manifest(root, excluded)
    terms = {
        "head": git("git", "-C", root, "rev-parse", "HEAD").strip(),
        "porcelain": porcelain_term(root, excluded),
        "content": manifest,
    }
    return terms, unevaluated


def fold(terms, omit=()):
    """Fold the terms into one digest, optionally omitting some -- the ablation hook.

    A weakened build is exactly `fold(terms, omit=('content',))`. The mutation fixtures
    assert such a fold stays CONSTANT across C1/C2 while the full fold moves, which is the
    property "a build that passes with either term removed is the defect" needs to be
    tested against.
    """
    unknown = set(omit) - set(TERMS)
    if unknown:
        raise ValueError("omit names no such term: %s" % ", ".join(sorted(unknown)))
    kept = {name: terms[name] for name in TERMS if name not in omit}
    canonical = json.dumps(kept, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8", "surrogateescape")).hexdigest()


def before_path(root, label):
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in label)
    return os.path.join(git_dir(root), BEFORE_DIR, safe + ".json")


def cmd_before(root, label, excluded):
    terms, unevaluated = compute_terms(root, excluded)
    record = {
        "label": label,
        "excluded": sorted(excluded),
        "terms": terms,
        "fingerprint": fold(terms),
        "unevaluated": unevaluated,
    }
    dest = before_path(root, label)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)

    print(
        "before  %s  (%d paths hashed, %d excluded, fp %s)"
        % (label, len(terms["content"]), len(excluded), record["fingerprint"][:16])
    )
    for note in unevaluated:
        print("    SKIP  %s" % note)
    for path in sorted(excluded):
        print("    excluded  %s  <-- declared write; a sibling touching it is invisible" % path)
    return EXIT_OK


def cmd_after(root, label):
    src = before_path(root, label)
    if not os.path.exists(src):
        print("SKIPPED  %s  (no before-record at %s)" % (label, src))
        print(
            "    SKIP  the measurement was never fingerprinted, so it is uncertified rather "
            "than clean. Take the before-record first; an after with nothing to compare "
            "against must not read as a still tree."
        )
        return EXIT_UNEVALUATED

    with open(src, encoding="utf-8") as handle:
        record = json.load(handle)
    excluded = set(record.get("excluded", []))

    terms, unevaluated = compute_terms(root, excluded)
    unevaluated = list(record.get("unevaluated", [])) + unevaluated
    now = fold(terms)
    then = record["fingerprint"]

    moved = [name for name in TERMS if terms[name] != record["terms"][name]]

    if now != then:
        status, code = "UNVERIFIED", EXIT_FAIL
    elif unevaluated:
        status, code = "SKIPPED", EXIT_UNEVALUATED
    else:
        status, code = "VERIFIED", EXIT_OK

    print(
        "%s  %s  (%d paths hashed, %d excluded, fp %s -> %s)"
        % (status, label, len(terms["content"]), len(excluded), then[:16], now[:16])
    )
    for note in unevaluated:
        print("    SKIP  %s" % note)

    if code == EXIT_FAIL:
        print(
            "    UNVERIFIED  terms that moved: %s. The tree changed under the measurement, "
            "so the number is not citable as taken. Re-run it; do not discard it -- the "
            "move may not have touched what you measured." % ", ".join(moved)
        )
        before_content = record["terms"]["content"]
        changed = sorted(
            set(before_content) ^ set(terms["content"])
            | {p for p in set(before_content) & set(terms["content"]) if before_content[p] != terms["content"][p]}
        )
        for path in changed[:MAX_REPORTED_PATHS]:
            was = before_content.get(path, "absent")
            now_value = terms["content"].get(path, "absent")
            print("        %s  %s -> %s" % (path, was[:23], now_value[:23]))
        if len(changed) > MAX_REPORTED_PATHS:
            print("        ... and %d more" % (len(changed) - MAX_REPORTED_PATHS))
        if not changed and "content" not in moved:
            print(
                "        no content path moved; %s alone did. A commit or an index-only "
                "write landed under the measurement." % " and ".join(moved)
            )
    return code


def main(argv):
    parser = argparse.ArgumentParser(prog="check_measurement_fingerprint.py", add_help=True)
    parser.add_argument("mode", choices=("before", "after"))
    parser.add_argument("--label", required=True, help="lane label, e.g. the issue id")
    parser.add_argument(
        "--writes",
        nargs="*",
        default=[],
        help="paths THIS measurement is expected to write; excluded from the content term "
        "and counted in the verdict line. `after` reuses the before-record's set.",
    )
    args = parser.parse_args(argv[1:])

    root = repo_root()
    if args.mode == "after" and args.writes:
        print(
            "usage error: --writes belongs on `before` only. The exclusion set is read back "
            "from the before-record, so accepting it again here would let an after-run "
            "exclude a path the before-run hashed and call the difference a still tree.",
            file=sys.stderr,
        )
        return EXIT_USAGE

    excluded = {rel(p, root) for p in args.writes}
    if args.mode == "before":
        return cmd_before(root, args.label, excluded)
    return cmd_after(root, args.label)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
