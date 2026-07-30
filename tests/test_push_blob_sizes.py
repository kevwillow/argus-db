"""MAC-635 — mutation fixtures for ``scripts/check_push_blob_sizes.py``.

Deliverable 2 of MAC-635, filed out of MAC-610. Companion to
``tests/test_staged_paths.py`` and written to the same bar: per R7 an instrument that
has never been shown firing cannot support a green result, so every check has a
positive control — a stack it MUST reject — beside the negative control it clears.

This script's whole reason to exist is that ``check_staged_paths.py`` C4 is blind to
history. C4 reads the index; once ``git commit`` runs the index is empty and every
subsequent C4 is green over a stack that already carries the blob. ``db/argus.db`` at
329,711,616 bytes was re-committed at ``8e905cf`` and ``4b1e0d9`` after entering at
``ceff54f``, and a per-commit index check would have said nothing about any of the
three stacks. The load-bearing fixture is therefore
``test_a_blob_deleted_later_in_the_range_is_still_reported``: deleting the file in a
follow-up commit removes it from the tip tree and changes nothing about what the push
sends, so a sweep that reported on the tip alone would certify an unpushable stack.

Every fixture runs in a throwaway repo under ``tmp_path``, never this repository — the
real ``origin/main`` moves under concurrent agent runs and a test pinned to it would
report on whatever the last operator hand-push left behind.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SWEEP = REPO / "scripts" / "check_push_blob_sizes.py"
STAGED_GATE = REPO / "scripts" / "check_staged_paths.py"

# Pinned as a wire contract, not imported from the script under test. A push gate reads
# these; importing the script's own constants would make every assertion agree with
# whatever it happens to return, including 2, which is already usage error.
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_UNEVALUATED = 3

CEILING = 100_000_000
WARN = 50_000_000


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_git(cwd, *args):
    proc = subprocess.run(
        ("git",) + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )
    assert proc.returncode == 0, "git %s failed: %s" % (" ".join(args), proc.stderr)
    return proc.stdout


def run_sweep(cwd, *args):
    proc = subprocess.run(
        [sys.executable, str(SWEEP)] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, proc.stdout + proc.stderr


def sparse(root, relpath, size, fill=b""):
    """A `size`-byte file that costs ~no disk. `fill` makes two same-size blobs distinct.

    MAC-610's three blobs were all 329,711,616 bytes and all at `db/argus.db`, so
    same-size-different-content is the case that has to work, not an edge case.
    """
    dest = root / relpath
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as fh:
        fh.truncate(size)
        if fill:
            fh.seek(0)
            fh.write(fill)
    return dest


@pytest.fixture
def stack(tmp_path):
    """A throwaway repo where branch `base` stands in for `origin/main`."""
    root = tmp_path / "stack"
    root.mkdir()
    run_git(root, "init", "-q", "-b", "main")
    run_git(root, "config", "user.email", "test@example.invalid")
    run_git(root, "config", "user.name", "test")
    (root / "README.md").write_text("base\n", encoding="utf-8")
    run_git(root, "add", "README.md")
    run_git(root, "commit", "-q", "-m", "base")
    run_git(root, "branch", "base")
    return root


def commit(root, relpath, size, message, fill=b""):
    sparse(root, relpath, size, fill)
    run_git(root, "add", "--force", relpath)
    run_git(root, "commit", "-q", "-m", message)
    return run_git(root, "rev-parse", "--short", "HEAD").strip()


# --------------------------------------------------------------------------
# Negative controls — stacks the sweep must clear
# --------------------------------------------------------------------------


def test_pass_on_a_range_carrying_nothing_large(stack):
    commit(stack, "notes.md", 1024, "small change")

    code, out = run_sweep(stack, "--base", "base", "--head", "main")
    assert code == EXIT_OK, out
    assert out.startswith("PASS  base..main"), out
    # The prefixed detail lines, not the bare words: the threshold summary line legitimately
    # contains "warn", and asserting on that would make this control pass for a typo.
    assert "    FAIL  " not in out and "    warn  " not in out, out


def test_a_blob_already_in_the_base_is_not_reported(stack):
    """The question is what THIS push adds. A pre-receive hook only inspects incoming
    objects, so re-reporting what the remote already holds would be a permanent false FAIL."""
    commit(stack, "big.bin", CEILING + 1, "big, but already upstream")
    run_git(stack, "branch", "-f", "base", "main")
    commit(stack, "notes.md", 10, "small change on top")

    code, out = run_sweep(stack, "--base", "base", "--head", "main")
    assert code == EXIT_OK, out
    assert out.startswith("PASS"), out
    assert "big.bin" not in out, out


# --------------------------------------------------------------------------
# Positive controls — stacks the sweep must reject
# --------------------------------------------------------------------------


def test_fails_on_a_blob_over_the_ceiling_and_names_the_adding_commit(stack):
    sha = commit(stack, "db/argus.db", CEILING + 1, "data(MAC-523): ingest")

    code, out = run_sweep(stack, "--base", "base", "--head", "main")
    assert code == EXIT_FAIL, out
    assert out.startswith("FAIL  base..main"), out
    assert "db/argus.db  100000001 bytes" in out, out
    assert "added by %s data(MAC-523): ingest" % sha in out, out
    assert "largest blob 100000001 bytes; ceiling 100000000; warn 50000000" in out, out


def test_attributes_a_re_committed_blob_to_the_commit_that_introduced_it(stack):
    """MAC-610's shape: one path, three commits, blobs of identical size.

    `--reverse` is what makes this hold. Attributing to the last commit that touched the
    path would name `4b1e0d9` for a blob `ceff54f` introduced, and send the remedy at the
    wrong commit.
    """
    first = commit(stack, "db/argus.db", CEILING + 1, "data(MAC-523): ingest", fill=b"A")
    commit(stack, "db/argus.db", CEILING + 1, "fix(MAC-580): aliases", fill=b"B")
    commit(stack, "db/argus.db", CEILING + 1, "feat(MAC-614): harvest", fill=b"A")

    code, out = run_sweep(stack, "--base", "base", "--head", "main")
    assert code == EXIT_FAIL, out
    # Two distinct blobs, both oversize, both reported — a count of 1 would mean the sweep
    # deduplicated by path and hid a second copy the push would still send.
    assert out.count("db/argus.db  100000001 bytes") == 2, out
    assert "added by %s data(MAC-523): ingest" % first in out, out


def test_a_blob_deleted_later_in_the_range_is_still_reported(stack):
    """The load-bearing fixture. Deleting the file does not un-send it.

    `rev-list --objects base..main` reaches every intermediate tree, so the blob is still
    in the object set the push transmits and still meets the pre-receive hook. A sweep that
    inspected only the tip tree would certify this stack green and the push would still be
    rejected — the exact conflation this script exists to remove.
    """
    sha = commit(stack, "db/argus.db", CEILING + 1, "data(MAC-523): ingest")
    run_git(stack, "rm", "-q", "db/argus.db")
    run_git(stack, "commit", "-q", "-m", "chore: remove the database")

    assert "db/argus.db" not in run_git(stack, "ls-tree", "-r", "--name-only", "main")

    code, out = run_sweep(stack, "--base", "base", "--head", "main")
    assert code == EXIT_FAIL, out
    assert "db/argus.db  100000001 bytes" in out, out
    assert "added by %s" % sha in out, out


def test_positive_control_the_same_clean_range_fails_when_only_the_ceiling_moves(stack):
    """Anti-vacuity. A zero-yield sweep is evidence only once it has been shown firing.

    Same repo, same range, same objects — one input flipped. If the ceiling moves below a
    real blob and the verdict stays PASS, the sweep is reading a constant, not the graph.
    """
    commit(stack, "notes.md", 40_000, "small change")

    clean, clean_out = run_sweep(stack, "--base", "base", "--head", "main")
    fired, fired_out = run_sweep(
        stack, "--base", "base", "--head", "main", "--max-bytes", "39999", "--warn-bytes", "100"
    )

    assert clean == EXIT_OK, clean_out
    assert clean_out.startswith("PASS"), clean_out
    assert fired == EXIT_FAIL, fired_out
    assert "notes.md  40000 bytes" in fired_out, fired_out


def test_warn_between_the_thresholds_exits_zero(stack):
    """51 MB. GitHub warns here and so does this; a build artifact is allowed to grow."""
    commit(stack, "exports/argus_export.csv", 51_000_000, "regen exports")

    code, out = run_sweep(stack, "--base", "base", "--head", "main")
    assert code == EXIT_OK, out
    assert out.startswith("WARN  base..main"), out
    assert "exports/argus_export.csv  51000000 bytes" in out, out
    assert "    FAIL  " not in out, out


def test_the_real_export_artifact_size_passes_with_no_warning(stack):
    """Non-regression: `exports/argus_export.csv` at its real 26,401,006 bytes.

    `git cat-file -s 14e33cc3cf9a7a54c0075c7f00d277b4c53cda2a` -> 26401006. MAC-612 treats
    `exports/` as a committed build artifact; a sweep that blocks it blocks the deliverable.
    """
    commit(stack, "exports/argus_export.csv", 26_401_006, "regen exports")

    code, out = run_sweep(stack, "--base", "base", "--head", "main")
    assert code == EXIT_OK, out
    assert out.startswith("PASS"), out
    assert "argus_export.csv" not in out, out


# --------------------------------------------------------------------------
# Un-evaluated, and the exit-code contract
# --------------------------------------------------------------------------


def test_an_unresolvable_base_is_skipped_not_pass(stack):
    """A range that was never enumerated is uncertified, not clean.

    This is the realistic failure: a fresh clone or a renamed remote leaves `origin/main`
    absent, `rev-list` over an empty range returns nothing, and a naive sweep prints PASS
    over zero objects — a green light sourced from having looked at nothing.
    """
    code, out = run_sweep(stack, "--base", "origin/main", "--head", "main")
    assert code == EXIT_UNEVALUATED, out
    assert out.startswith("SKIPPED"), out
    assert not out.startswith("PASS"), out
    assert "does not resolve to a commit" in out, out
    assert "NOT enumerated" in out, out


def test_exit_codes_are_mutually_distinct(stack):
    """Four outcomes, four codes — checked against each other, where a collision lives."""
    commit(stack, "big.bin", CEILING + 1, "the defect")

    fail, _ = run_sweep(stack, "--base", "base", "--head", "main")
    unevaluated, _ = run_sweep(stack, "--base", "origin/main", "--head", "main")
    usage, _ = run_sweep(stack, "--base", "base", "--max-bytes", "100", "--warn-bytes", "100")
    argparse_err, _ = run_sweep(stack, "--nonsense")
    ok, _ = run_sweep(stack, "--base", "base", "--head", "base")

    assert (ok, fail, usage, argparse_err, unevaluated) == (
        EXIT_OK,
        EXIT_FAIL,
        EXIT_USAGE,
        EXIT_USAGE,
        EXIT_UNEVALUATED,
    )
    assert len({ok, fail, usage, unevaluated}) == 4


def test_warn_threshold_at_or_above_the_ceiling_is_a_usage_error(stack):
    """With WARN >= FAIL every oversize blob is caught by the `else` and downgraded to a
    warning that exits 0. The sweep would still print and still pass what it must reject."""
    code, out = run_sweep(
        stack, "--base", "base", "--head", "main", "--max-bytes", "1000", "--warn-bytes", "1000"
    )
    assert code == EXIT_USAGE, out
    assert "must be below --max-bytes" in out, out


def test_the_report_states_the_base_sha_and_that_it_was_not_refreshed(stack):
    """An operator hand-push moves remote `main` out of band between ratifications.

    A sweep that did not say which base it compared against is an attestation about an
    unnamed range. The resolved sha and the fetch status both go in the report.
    """
    commit(stack, "notes.md", 10, "small change")
    base_sha = run_git(stack, "rev-parse", "base").strip()

    code, out = run_sweep(stack, "--base", "base", "--head", "main")
    assert code == EXIT_OK, out
    assert "base base = %s  (NOT fetched this run)" % base_sha[:12] in out, out


def test_the_two_gates_agree_on_the_ceiling(stack):
    """A stack-level ceiling looser than the per-commit one would let a blob through the
    gate that runs first and stop it at the gate that runs last, after it is unfixable
    without a rewrite. Two independent files, so this is not a comparison with itself."""
    sweep_mod = _load(SWEEP, "check_push_blob_sizes")
    gate_mod = _load(STAGED_GATE, "check_staged_paths")

    assert sweep_mod.DEFAULT_MAX_BLOB_BYTES == gate_mod.DEFAULT_MAX_BLOB_BYTES == CEILING
    assert sweep_mod.DEFAULT_WARN_BLOB_BYTES == gate_mod.DEFAULT_WARN_BLOB_BYTES == WARN
