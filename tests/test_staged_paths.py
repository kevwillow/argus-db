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
import json
import subprocess
import sys
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parents[1] / "scripts" / "check_staged_paths.py"

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
