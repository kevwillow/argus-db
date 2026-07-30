"""MAC-592 — mutation fixtures for ``scripts/check_staged_paths.py`` (BRIEF_STANDARDS R10).

Per R9 a structural guard is decoration until it is shown failing on an input it
should reject, and per R7 an instrument that has never been shown to fire cannot
support a green result. Every check in the gate therefore has a positive control
here — a tree the gate MUST reject — beside the negative control it must clear.

The load-bearing fixture is ``test_c2_fires_on_the_cf9031a_reconstruction``. It
rebuilds the real 2026-07-28 failure: MAC-573 staged three paths it had every
right to stage and swept the MAC-579 lane's uncommitted ``classify()`` fix out of
``scripts/run_liveness_probe.py`` along the way. That test asserts BOTH halves —
that the path-set check C1 sees nothing wrong, and that C2 fires anyway. If C1
alone were the gate, cf9031a would have passed it, which is precisely why R10 is
not a restatement of R8's second paragraph.

Every fixture runs in a throwaway repo under ``tmp_path``. The gate shells out to
``git`` in the current working directory, and this repo's own index is shared with
concurrent agent runs — a test that staged into it would corrupt a peer's commit
while asserting that peers must not corrupt each other's commits.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "check_staged_paths.py"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("check_staged_paths", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate_mod = _load_gate_module()

# Deliberately a literal, not an import from the gate. Importing the gate's own
# constant would make every assertion below agree with whatever the gate happens
# to return -- including 2, which is already usage error. A post-condition that
# mirrors its transform is vacuous, and this is the exit code a pre-commit hook
# reads, so it is pinned as a wire contract.
EXIT_UNEVALUATED = 3

# Verbatim from `git show cf9031a -- scripts/run_liveness_probe.py`, the hunk the
# MAC-579 lane had uncommitted in the shared worktree when MAC-573 ran `git add`.
MAC579_UNCOMMITTED_FIX = "    marker = last_out or started\n"


def run_git(cwd, *args):
    proc = subprocess.run(
        ("git",) + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8"
    )
    assert proc.returncode == 0, "git %s failed: %s" % (" ".join(args), proc.stderr)
    return proc.stdout


def run_gate(cwd, *args):
    """Invoke the gate as a subprocess and return (exit_code, combined_output)."""
    proc = subprocess.run(
        [sys.executable, str(GATE)] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, proc.stdout + proc.stderr


@pytest.fixture
def repo(tmp_path):
    """A throwaway git repo with one commit, never this repository."""
    root = tmp_path / "worktree"
    root.mkdir()
    run_git(root, "init", "-q", "-b", "main")
    run_git(root, "config", "user.email", "test@example.invalid")
    run_git(root, "config", "user.name", "test")
    (root / "scripts").mkdir()
    (root / "probe.py").write_text("def classify():\n    return last_out\n", encoding="utf-8")
    (root / "standards.md").write_text("# standards\n\nR1\n", encoding="utf-8")
    run_git(root, "add", "probe.py", "standards.md")
    run_git(root, "commit", "-q", "-m", "base")
    return root


# --------------------------------------------------------------------------
# C1 — staged path set vs declared path set
# --------------------------------------------------------------------------


def test_c1_negative_control_exact_match_passes(repo):
    """A commit that stages exactly what it declared clears the gate.

    The declaration is deliberately given in a different order from the one git
    reports, since a set comparison that quietly depended on ordering would pass
    every fixture written by the person who wrote the gate.
    """
    run_gate(repo, "baseline", "--label", "L", "standards.md", "probe.py")
    (repo / "standards.md").write_text("# standards\n\nR1\nR10\n", encoding="utf-8")
    (repo / "probe.py").write_text("def classify():\n    return 3\n", encoding="utf-8")
    run_git(repo, "add", "standards.md", "probe.py")

    code, out = run_gate(repo, "check", "--label", "L", "standards.md", "probe.py")
    assert code == 0, out
    assert out.startswith("PASS  L  (2 declared, 2 staged)"), out


def test_c1_fires_on_an_undeclared_staged_path(repo):
    """Positive control: a path in the index that the lane never declared."""
    (repo / "standards.md").write_text("# standards\n\nR10\n", encoding="utf-8")
    (repo / "probe.py").write_text("def classify():\n    return started\n", encoding="utf-8")
    run_git(repo, "add", "standards.md", "probe.py")

    code, out = run_gate(repo, "check", "--label", "L", "standards.md")
    assert code == 1, out
    assert "C1 1 staged path(s) were never declared: probe.py" in out, out


def test_c1_fires_on_a_declared_path_that_was_not_staged(repo):
    """A declaration that overstates the commit is not a check."""
    (repo / "standards.md").write_text("# standards\n\nR10\n", encoding="utf-8")
    run_git(repo, "add", "standards.md")

    code, out = run_gate(repo, "check", "--label", "L", "standards.md", "probe.py")
    assert code == 1, out
    assert "C1 1 declared path(s) are not staged: probe.py" in out, out


def test_c1_counts_both_sides_of_a_rename(repo):
    """`--no-renames` keeps the vacated path in the set the gate compares.

    With rename detection on, `git diff --cached --name-only` reports only the new
    name, so a lane could move a peer's file and declare one path for a two-path
    change.
    """
    run_git(repo, "mv", "probe.py", "probe2.py")
    code, out = run_gate(repo, "check", "--label", "L", "probe2.py")
    assert code == 1, out
    assert "never declared: probe.py" in out, out


# --------------------------------------------------------------------------
# C2 — the cf9031a sweep class, which C1 is structurally blind to
# --------------------------------------------------------------------------


def test_c2_fires_on_the_cf9031a_reconstruction(repo):
    """The real 2026-07-28 failure, and the reason R10 is not R8 restated.

    Lane B (MAC-579) holds an uncommitted fix in ``probe.py``. Lane A (MAC-573)
    also has real work in ``probe.py`` plus ``standards.md``, declares exactly
    those two paths, and stages them. C1 sees a perfect match. C2 must still fire.
    """
    # Lane A takes its baseline before its first write — but lane B is already dirty.
    (repo / "probe.py").write_text(
        "def classify():\n" + MAC579_UNCOMMITTED_FIX + "    return marker\n", encoding="utf-8"
    )
    run_gate(repo, "baseline", "--label", "MAC-573", "probe.py", "standards.md")

    # Lane A now does its own legitimate work in both declared paths.
    (repo / "probe.py").write_text(
        '"""Adopted as R6 on MAC-573."""\n\n'
        "def classify():\n" + MAC579_UNCOMMITTED_FIX + "    return marker\n",
        encoding="utf-8",
    )
    (repo / "standards.md").write_text("# standards\n\nR6\n", encoding="utf-8")
    run_git(repo, "add", "probe.py", "standards.md")

    code, out = run_gate(repo, "check", "--label", "MAC-573", "probe.py", "standards.md")

    # The half R10 exists to prove: the path set is immaculate.
    assert "C1" not in out, "C1 must be silent here; the declared set matched exactly\n" + out
    # The half that catches the defect.
    assert code == 1, out
    assert "C2 probe.py was already dirty when this lane began" in out, out
    # The remedy must be actionable, not a scolding.
    assert "git apply --cached" in out, out
    # The swept bytes must be shown, so the author sees what they are about to take.
    assert "marker = last_out or started" in out, out


def test_c2_negative_control_clean_baseline_passes(repo):
    """Same shape, but the lane took its baseline on a genuinely clean tree."""
    run_gate(repo, "baseline", "--label", "MAC-573", "probe.py", "standards.md")
    (repo / "probe.py").write_text('"""R6."""\n\ndef classify():\n    return 1\n', encoding="utf-8")
    (repo / "standards.md").write_text("# standards\n\nR6\n", encoding="utf-8")
    run_git(repo, "add", "probe.py", "standards.md")

    code, out = run_gate(repo, "check", "--label", "MAC-573", "probe.py", "standards.md")
    assert code == 0, out
    assert out.startswith("PASS"), out


def test_c2_fires_on_a_path_untracked_at_baseline(repo):
    """An untracked artifact in the shared tree at baseline is a peer's, not yours."""
    (repo / "scratch.md").write_text("peer's notes\n", encoding="utf-8")
    run_gate(repo, "baseline", "--label", "L", "scratch.md")
    run_git(repo, "add", "scratch.md")

    code, out = run_gate(repo, "check", "--label", "L", "scratch.md")
    assert code == 1, out
    assert "C2 scratch.md was already untracked when this lane began" in out, out


def test_c2_fires_on_a_declared_path_missing_from_the_baseline(repo):
    """An unbaselined path is unevaluated, not clean."""
    run_gate(repo, "baseline", "--label", "L", "standards.md")
    (repo / "standards.md").write_text("# standards\n\nR10\n", encoding="utf-8")
    (repo / "probe.py").write_text("def classify():\n    return 2\n", encoding="utf-8")
    run_git(repo, "add", "standards.md", "probe.py")

    code, out = run_gate(repo, "check", "--label", "L", "standards.md", "probe.py")
    assert code == 1, out
    assert "C2 1 declared path(s) absent from the baseline: probe.py" in out, out


def test_c2_structural_guard_rejects_an_unknown_baseline_state(repo):
    """The guard that fails loudly instead of accepting a state it does not model.

    A baseline written by a different version of the gate, or hand-edited, must not
    fall through the ``dirty``/``untracked`` test and read as clean.
    """
    run_gate(repo, "baseline", "--label", "L", "standards.md")
    bfile = repo / ".git" / "argus_stage_baseline" / "L.json"
    record = json.loads(bfile.read_text(encoding="utf-8"))
    record["paths"]["standards.md"]["state"] = "probably_fine"
    bfile.write_text(json.dumps(record), encoding="utf-8")

    (repo / "standards.md").write_text("# standards\n\nR10\n", encoding="utf-8")
    run_git(repo, "add", "standards.md")

    code, out = run_gate(repo, "check", "--label", "L", "standards.md")
    assert code == 1, out
    assert "unknown state 'probably_fine'" in out, out


def test_c2_reports_skipped_rather_than_passing_with_no_baseline(repo):
    """A check that did not run must never read as a check that passed.

    This is the vacuity control: without it, the whole sweep class silently
    evaporates for any lane that forgets the baseline step.

    MAC-599: the first version of this fixture asserted ``code == 0`` under this
    exact name, so it certified the defect it is named for. The note in the body
    is prose; the exit code is the machine-readable verdict, and it is the one a
    hook or a habituated operator reads. Both are asserted here.
    """
    (repo / "standards.md").write_text("# standards\n\nR10\n", encoding="utf-8")
    run_git(repo, "add", "standards.md")

    code, out = run_gate(repo, "check", "--label", "never-baselined", "standards.md")
    assert code == EXIT_UNEVALUATED, out
    assert out.startswith("SKIPPED  never-baselined  (1 declared, 1 staged)"), out
    assert not out.startswith("PASS"), out
    assert "C2 SKIPPED" in out, out
    assert "was NOT evaluated" in out, out


def test_unevaluated_exit_code_is_distinct_from_usage_error(repo):
    """``2`` was already spent, so unevaluated cannot be spelled ``2``.

    ``main`` returns 2 for a duplicate declared path and argparse exits 2 of its
    own accord on a malformed argv. Reusing 2 would make "the sweep class was not
    evaluated" indistinguishable from "you typed the command wrong" — which is
    the same conflation, one exit code further along. This asserts the three
    non-PASS outcomes are mutually distinct rather than merely non-zero.
    """
    (repo / "standards.md").write_text("# standards\n\nR10\n", encoding="utf-8")
    run_git(repo, "add", "standards.md")

    unevaluated, _ = run_gate(repo, "check", "--label", "never-baselined", "standards.md")
    usage, _ = run_gate(repo, "check", "--label", "L", "standards.md", "./standards.md")
    argparse_err, _ = run_gate(repo, "check", "standards.md")

    run_gate(repo, "baseline", "--label", "F", "standards.md")
    (repo / "probe.py").write_text("undeclared\n", encoding="utf-8")
    run_git(repo, "add", "probe.py")
    real_fail, _ = run_gate(repo, "check", "--label", "F", "standards.md")

    assert (unevaluated, usage, argparse_err, real_fail) == (EXIT_UNEVALUATED, 2, 2, 1)
    assert len({unevaluated, usage, real_fail, 0}) == 4


def test_a_real_failure_outranks_an_unevaluated_c2(repo):
    """FAIL must not be downgraded to SKIPPED by the absence of a baseline.

    A lane that skipped the baseline AND staged an undeclared path has a proven
    defect, not merely an unevaluated one. Exit 1 has to survive.
    """
    (repo / "standards.md").write_text("# standards\n\nR10\n", encoding="utf-8")
    (repo / "probe.py").write_text("def classify():\n    return 9\n", encoding="utf-8")
    run_git(repo, "add", "standards.md", "probe.py")

    code, out = run_gate(repo, "check", "--label", "never-baselined", "standards.md")
    assert code == 1, out
    assert out.startswith("FAIL"), out
    assert "C2 SKIPPED" in out, out


def test_unevaluated_outranks_a_c3_warning(repo):
    """WARN exits 0, so a WARN headline would re-hide the unevaluated sweep."""
    (repo / "standards.md").write_text("# standards\n\nR10\n", encoding="utf-8")
    run_git(repo, "add", "standards.md")
    (repo / "standards.md").write_text("# standards\n\nR10\npeer line\n", encoding="utf-8")

    code, out = run_gate(repo, "check", "--label", "never-baselined", "standards.md")
    assert code == EXIT_UNEVALUATED, out
    assert out.startswith("SKIPPED"), out
    assert "C3 1 declared path(s) have unstaged changes" in out, out


def test_docstring_promise_names_the_exit_code_it_returns(repo):
    """R9: the header that states the contract must be checkable against the code.

    MAC-599 exists because ``check_staged_paths.py:15`` promised SKIPPED-never-PASS
    while the verdict expression had no ``notes`` term. A prose promise nothing
    reads is how that divergence survived review, so the promise is pinned here.
    """
    header = GATE.read_text(encoding="utf-8").split('"""')[1]
    assert "With no baseline this reports SKIPPED, never PASS" in header, header
    assert "Exit %d" % EXIT_UNEVALUATED in header, header


# --------------------------------------------------------------------------
# C3 — the file moved under you between `git add` and `git commit`
# --------------------------------------------------------------------------


def test_c3_warns_on_unstaged_residue_on_a_declared_path(repo):
    run_gate(repo, "baseline", "--label", "L", "standards.md")
    (repo / "standards.md").write_text("# standards\n\nR10\n", encoding="utf-8")
    run_git(repo, "add", "standards.md")
    # A peer writes to the same file after the `git add`.
    (repo / "standards.md").write_text("# standards\n\nR10\npeer line\n", encoding="utf-8")

    code, out = run_gate(repo, "check", "--label", "L", "standards.md")
    assert code == 0, out
    assert out.startswith("WARN"), out
    assert "C3 1 declared path(s) have unstaged changes" in out, out


# --------------------------------------------------------------------------
# Baseline recording
# --------------------------------------------------------------------------


def test_baseline_records_the_four_states(repo):
    (repo / "probe.py").write_text("dirty\n", encoding="utf-8")
    (repo / "scratch.md").write_text("untracked\n", encoding="utf-8")

    code, out = run_gate(
        repo, "baseline", "--label", "L", "probe.py", "standards.md", "scratch.md", "new.md"
    )
    assert code == 0, out

    record = json.loads(
        (repo / ".git" / "argus_stage_baseline" / "L.json").read_text(encoding="utf-8")
    )
    states = {p: e["state"] for p, e in record["paths"].items()}
    assert states == {
        "probe.py": "dirty",
        "standards.md": "clean",
        "scratch.md": "untracked",
        "new.md": "absent",
    }, states
    assert "dirty" in record["paths"]["probe.py"]["pre_existing_diff"]


def test_duplicate_declared_path_is_a_usage_error(repo):
    code, out = run_gate(repo, "check", "--label", "L", "standards.md", "./standards.md")
    assert code == 2, out


# --------------------------------------------------------------------------
# C4 / C5 — MAC-635. The size dimension, STAGED not standing.
#
# C1-C3 are structurally size-blind. `db/argus.db` at 329,711,616 bytes cleared all
# three at `ceff54f`, `8e905cf` and `4b1e0d9` — a declared path, staged deliberately,
# on a clean baseline. Every fixture below is paired: the tree the check must reject
# beside the tree it must clear, because a size check that has never been shown
# failing cannot support a green result (R7).
# --------------------------------------------------------------------------

CEILING = 100_000_000
WARN = 50_000_000

# The real byte count of `exports/argus_export.csv` at HEAD, verified with
# `git cat-file -s 14e33cc3cf9a7a54c0075c7f00d277b4c53cda2a` -> 26401006. MAC-612 treats
# `exports/` as a committed build artifact rather than a view, so a gate that blocks it is
# wrong, and this is the non-regression anchor for that.
ARGUS_EXPORT_CSV_BYTES = 26_401_006

# `git cat-file -s 41abd2863ec3300cf48ed3376e85ad523e2f250c` at HEAD -> 329711616. The blob
# `ceff54f` introduced, still an ancestor of HEAD.
CEFF54F_DB_BLOB = "41abd2863ec3300cf48ed3376e85ad523e2f250c"
CEFF54F_DB_BYTES = 329_711_616


def sparse(root, relpath, size):
    """Write a `size`-byte sparse file. git hashes the full length; the disk holds ~nothing.

    A 100 MB fixture that cost 100 MB of disk would not get written, and the boundary cases
    are exactly where a size check is worth testing.
    """
    dest = root / relpath
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as fh:
        fh.truncate(size)
    return dest


def stage_only(repo, label, relpath, size):
    """Baseline, THEN create and stage, so C1/C2/C3 are all silent and only C4/C5 can speak.

    Order matters and is not incidental: R10 requires the baseline before the first write, and
    a fixture that wrote first would trip C2 and pass for the wrong reason — green on the size
    dimension it never reached. That is the vacuity this file exists to refuse.
    """
    run_gate(repo, "baseline", "--label", label, relpath)
    sparse(repo, relpath, size)
    run_git(repo, "add", "--force", relpath)


def test_c4_fires_on_a_blob_over_the_ceiling(repo):
    """100,000,001 bytes. One byte over, and the only thing wrong with the commit."""
    stage_only(repo, "L", "big.bin", CEILING + 1)

    code, out = run_gate(repo, "check", "--label", "L", "big.bin")
    assert code == 1, out
    assert out.startswith("FAIL"), out
    assert "C4 big.bin is 100000001 bytes staged, over the 100000000-byte ceiling" in out, out
    # Independence: `big.bin` matches no large-artifact pattern, so C5 must stay silent.
    assert "C5" not in out, out
    # And the other three checks had nothing to say — this commit is clean by R10-as-ratified.
    assert "C1" not in out and "C2" not in out and "C3" not in out, out


def test_c4_negative_control_at_exactly_the_ceiling_passes(repo):
    """The comparison is `>`, not `>=`. A ceiling you cannot reach is a different ceiling."""
    stage_only(repo, "L", "big.bin", CEILING)

    code, out = run_gate(repo, "check", "--label", "L", "big.bin")
    assert code == 0, out
    assert out.startswith("WARN"), out  # over 50 MB, so it warns; it does not fail
    assert "over the 100000000-byte ceiling" not in out, out


def test_c4_49mb_passes_with_no_warning(repo):
    stage_only(repo, "L", "mid.bin", 49_000_000)

    code, out = run_gate(repo, "check", "--label", "L", "mid.bin")
    assert code == 0, out
    assert out.startswith("PASS"), out
    assert "C4" not in out, out


def test_c4_51mb_passes_with_a_warning(repo):
    """GitHub's own warning threshold. A WARN exits 0 — approaching the wall is not hitting it."""
    stage_only(repo, "L", "mid.bin", 51_000_000)

    code, out = run_gate(repo, "check", "--label", "L", "mid.bin")
    assert code == 0, out
    assert out.startswith("WARN"), out
    assert "C4 mid.bin is 51000000 bytes staged, over the 50000000-byte warning threshold" in out


def test_c4_non_regression_the_committed_export_artifact_passes(repo):
    """`exports/argus_export.csv` at its real 26,401,006 bytes must clear the gate silently.

    MAC-612 treats `exports/` as a committed build artifact. A gate that blocks the
    deliverable is not a gate, it is an outage.
    """
    stage_only(repo, "L", "exports/argus_export.csv", ARGUS_EXPORT_CSV_BYTES)

    code, out = run_gate(repo, "check", "--label", "L", "exports/argus_export.csv")
    assert code == 0, out
    assert out.startswith("PASS"), out
    assert "C4" not in out and "C5" not in out, out


def test_c4_anti_vacuity_the_same_index_fails_when_only_the_ceiling_moves(repo):
    """The control `cf9031a` teaches: show the check failing on its own counterexample.

    `cf9031a` staged exactly the three paths it declared and passed a path-set check while
    being defective — green because the check could not see the defect, not because there
    was none. Same shape here: the fixture above is green, so flip ONE input, the ceiling,
    one byte below the staged blob and nothing else. If it stays green the check is reading
    a constant rather than the object.
    """
    stage_only(repo, "L", "exports/argus_export.csv", ARGUS_EXPORT_CSV_BYTES)

    passing, _ = run_gate(repo, "check", "--label", "L", "exports/argus_export.csv")
    code, out = run_gate(
        repo,
        "check",
        "--label",
        "L",
        "--max-bytes",
        str(ARGUS_EXPORT_CSV_BYTES - 1),
        "--warn-bytes",
        "1000",
        "exports/argus_export.csv",
    )

    assert passing == 0
    assert code == 1, out
    assert (
        "C4 exports/argus_export.csv is 26401006 bytes staged, over the 26401005-byte ceiling"
        in out
    ), out


def test_c4_ignores_a_staged_deletion_of_an_oversize_blob(repo):
    """Staging the REMOVAL of a 100 MB blob is the remedy. A gate that blocked its own fix
    would leave MAC-610 permanently unfixable."""
    sparse(repo, "big.bin", CEILING + 1)
    run_git(repo, "add", "--force", "big.bin")
    run_git(repo, "commit", "-q", "-m", "the defect")

    run_gate(repo, "baseline", "--label", "L", "big.bin")
    run_git(repo, "rm", "-q", "big.bin")

    code, out = run_gate(repo, "check", "--label", "L", "big.bin")
    assert code == 0, out
    assert out.startswith("PASS"), out
    assert "C4" not in out, out


def test_c4_reports_unevaluated_rather_than_passing_on_an_unreadable_size(repo):
    """A size the gate could not read is not a size under the ceiling.

    Staged here as a blob-mode entry pointing at a TREE object: the object exists, so git
    stages it happily, but `cat-file --batch-check` reports type `tree` and there is no blob
    size to compare. That must surface as SKIPPED at exit 3, not fall through to PASS —
    the same rule C2 already obeys, applied to the new dimension.
    """
    tree_sha = run_git(repo, "rev-parse", "HEAD^{tree}").strip()
    run_gate(repo, "baseline", "--label", "L", "ghost.bin")
    run_git(repo, "update-index", "--add", "--cacheinfo", "100644,%s,ghost.bin" % tree_sha)

    code, out = run_gate(repo, "check", "--label", "L", "ghost.bin")
    assert code == 3, out
    assert out.startswith("SKIPPED"), out
    assert not out.startswith("PASS"), out
    assert "C4 SKIPPED -- no object size resolved for 1 staged path(s): ghost.bin" in out, out
    assert "NOT evaluated" in out, out


def test_c4_fail_outranks_an_unevaluated_c2(repo):
    """A proven oversize blob is a defect, not merely an unevaluated one. Exit 1 survives."""
    sparse(repo, "big.bin", CEILING + 1)
    run_git(repo, "add", "--force", "big.bin")

    code, out = run_gate(repo, "check", "--label", "never-baselined", "big.bin")
    assert code == 1, out
    assert out.startswith("FAIL"), out
    assert "C2 SKIPPED" in out, out
    assert "over the 100000000-byte ceiling" in out, out


def test_c5_fires_on_db_argus_db_at_three_bytes(repo):
    """Pattern and size are INDEPENDENT triggers, not one trigger with two spellings.

    A tracked path escaping gitignore is the MAC-610 failure exactly, and it is that failure
    at 3 bytes as much as at 329 MB — the file only grows afterwards.
    """
    run_gate(repo, "baseline", "--label", "L", "db/argus.db")
    (repo / "db").mkdir()
    (repo / "db" / "argus.db").write_bytes(b"SQL")
    run_git(repo, "add", "--force", "db/argus.db")

    code, out = run_gate(repo, "check", "--label", "L", "db/argus.db")
    assert code == 1, out
    assert "C5 1 staged path(s) match a .gitignore large-artifact pattern" in out, out
    assert "db/argus.db [db/*.db]" in out, out
    # The size trigger must be silent, or the two triggers are not shown to be independent.
    assert "C4" not in out, out


@pytest.mark.parametrize("pattern", gate_mod.LARGE_ARTIFACT_PATTERNS)
def test_c5_fires_on_every_declared_large_artifact_pattern(repo, pattern):
    """Derived from the gate's own tuple, not a retyped list.

    Not vacuous: the assertion is that each declared pattern is actually WIRED to a FAIL,
    which a list comparison against itself would not show. A pattern can sit in the tuple
    and reach no branch.
    """
    path = pattern.replace("*", "x")
    run_gate(repo, "baseline", "--label", "L", path)
    (repo / "db").mkdir(exist_ok=True)
    (repo / path).write_bytes(b"x")
    run_git(repo, "add", "--force", path)

    code, out = run_gate(repo, "check", "--label", "L", path)
    assert code == 1, out
    assert "%s [%s]" % (path, pattern) in out, out


def test_c5_patterns_are_the_ones_gitignore_already_declares(repo):
    """Anti-drift against an independent file, which is what makes this check non-circular.

    `.gitignore` is where these patterns were declared and where they failed to bind, since
    gitignore does not reach an already-tracked path. If someone widens that block and not
    this tuple, the gate silently stops covering the new pattern.
    """
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    missing = [p for p in gate_mod.LARGE_ARTIFACT_PATTERNS if p not in gitignore]
    assert missing == [], "patterns absent from .gitignore: %s" % missing


def test_c5_ignores_a_staged_deletion_of_a_barred_path(repo):
    """Removing `db/argus.db` from the index is the MAC-610 remedy. It must not be blocked."""
    (repo / "db").mkdir()
    (repo / "db" / "argus.db").write_bytes(b"SQL")
    run_git(repo, "add", "--force", "db/argus.db")
    run_git(repo, "commit", "-q", "-m", "the defect")

    run_gate(repo, "baseline", "--label", "L", "db/argus.db")
    run_git(repo, "rm", "-q", "db/argus.db")

    code, out = run_gate(repo, "check", "--label", "L", "db/argus.db")
    assert code == 0, out
    assert out.startswith("PASS"), out
    assert "C5" not in out, out


def test_warn_threshold_at_or_above_the_ceiling_is_a_usage_error(repo):
    """The structural guard, shown failing.

    With WARN >= FAIL every oversize blob is classified by the `elif` and downgraded to a
    warning that exits 0. The gate would still print, still look configured, and pass the
    exact input it exists to reject.
    """
    stage_only(repo, "L", "big.bin", CEILING + 1)

    code, out = run_gate(
        repo, "check", "--label", "L", "--max-bytes", "1000", "--warn-bytes", "1000", "big.bin"
    )
    assert code == 2, out
    assert "must be below --max-bytes" in out, out
    assert gate_mod.DEFAULT_WARN_BLOB_BYTES < gate_mod.DEFAULT_MAX_BLOB_BYTES


@pytest.mark.skipif(
    subprocess.run(
        ("git", "-C", str(REPO), "cat-file", "-e", CEFF54F_DB_BLOB), capture_output=True
    ).returncode
    != 0,
    reason="ceff54f's db/argus.db blob is not present in this clone",
)
def test_c4_positive_control_on_the_real_ceff54f_blob(repo):
    """The commit that caused this issue, replayed. If the gate cannot fail on it, it is not a gate.

    The blob is borrowed through `objects/info/alternates` rather than copied: 329,711,616
    real bytes, the real path, the real object name from real history, and zero bytes of disk.
    `git add db/argus.db` at that tree produces exactly this index entry, and the index is all
    the gate reads.
    """
    (repo / ".git" / "objects" / "info").mkdir(parents=True, exist_ok=True)
    (repo / ".git" / "objects" / "info" / "alternates").write_text(
        str(REPO / ".git" / "objects") + "\n", encoding="utf-8"
    )
    assert (
        run_git(repo, "cat-file", "-s", CEFF54F_DB_BLOB).strip() == str(CEFF54F_DB_BYTES)
    ), "borrowed blob is not the 329,711,616-byte object ceff54f introduced"

    run_gate(repo, "baseline", "--label", "MAC-523", "db/argus.db")
    run_git(repo, "update-index", "--add", "--cacheinfo", "100644,%s,db/argus.db" % CEFF54F_DB_BLOB)

    code, out = run_gate(repo, "check", "--label", "MAC-523", "db/argus.db")
    assert code == 1, out
    assert "C4 db/argus.db is 329711616 bytes staged, over the 100000000-byte ceiling" in out, out
    assert "C5 1 staged path(s) match a .gitignore large-artifact pattern" in out, out
    # C1 and C2 stay silent: `ceff54f` declared this path and had every right to stage it.
    # That is the whole point — R10-as-ratified was green on the commit that broke the push.
    assert "C1" not in out and "C2" not in out, out
