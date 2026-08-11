"""MAC-634 — mutation fixtures for ``scripts/check_measurement_fingerprint.py`` (R11).

The fixtures are the deliverable, not the prose. R10 was ratified because its C2 SWEEP
check reached its own founding incident where a path-set check alone did not; R11 is held
to the same bar, and a rule whose check passes on C1 or C2 below is refused on arrival.

C1 and C2 are TERM-ABLATION fixtures, and each asserts BOTH arms:

  * the weakened fold is SILENT across the mutation — the digest a build with that term
    removed would produce does not move, so such a build passes the control; and
  * the full fold FIRES on the same mutation.

Either arm alone is vacuous. A fires-only test passes for a weakened build whose digest
happens to move for an unrelated reason, and a silent-only test passes for a gate that
never fires at all. ``test_omit_rejects_an_unknown_term_name`` guards the ablation hook
itself: if ``omit=`` silently ignored a misspelled term, every ablation below would be
folding all three terms and asserting the full gate against itself — a fixture certifying
the defect its own name denies.

T1 and T2 get the same treatment in the other direction. ``test_head_term_is_load_bearing``
and ``test_porcelain_term_is_load_bearing`` each build a mutation the CONTENT term cannot
see, so the file proves all three terms earn their place rather than asserting it.

Every fixture runs in a throwaway repo under ``tmp_path``. This repo's own worktree is
shared with concurrent agent runs, and a test that wrote into it would move a peer's
measurement while asserting that peers must not move each other's measurements.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "check_measurement_fingerprint.py"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("check_measurement_fingerprint", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate_mod = _load_gate_module()

# Deliberately literals, not imports from the gate. Importing the gate's own constants
# would make every assertion below agree with whatever the gate happens to return, which
# is a post-condition mirroring its transform. These are the wire contract a caller reads.
EXIT_VERIFIED = 0
EXIT_UNVERIFIED = 1
EXIT_USAGE = 2
EXIT_SKIPPED = 3


def run_git(cwd, *args, input_text=None):
    proc = subprocess.run(
        ("git",) + args,
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
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


def terms(root, excluded=()):
    return gate_mod.compute_terms(str(root), set(excluded))[0]


@pytest.fixture
def repo(tmp_path):
    """The card's own control repo, built exactly as the CEO specified it."""
    root = tmp_path / "ctl"
    root.mkdir()
    run_git(root, "init", "-q", ".")
    run_git(root, "config", "user.email", "t@t")
    run_git(root, "config", "user.name", "t")
    (root / "operator_review" / "MAC-542").mkdir(parents=True)
    (root / "operator_review" / "MAC-542" / "derived.csv").write_text("row,a\n1,x\n")
    (root / "mod.py").write_text("print(1)\n")
    run_git(root, "add", "-A")
    run_git(root, "commit", "-qm", "base")
    return root


# --------------------------------------------------------------------------------------
# C1 and C2 — the two controls the card refuses the rule without.
# --------------------------------------------------------------------------------------


def test_c1_head_only_ablation_is_silent_on_a_sibling_worktree_write(repo):
    """C1: a sibling re-deriving MAC-542 moves no ref, so a HEAD-only check never fires.

    This is the founding incident of MAC-584 and the reason its proposed wording — 're-read
    HEAD before and after' — was refused. A worktree write is invisible to every ref.
    """
    derived = repo / "operator_review" / "MAC-542" / "derived.csv"
    before = terms(repo)

    derived.write_text("row,a\n1,x\n2,y\n")  # the sibling lane re-derives
    after = terms(repo)

    assert before["head"] == after["head"], "control is broken: the write moved HEAD"

    head_only_before = gate_mod.fold(before, omit=("porcelain", "content"))
    head_only_after = gate_mod.fold(after, omit=("porcelain", "content"))
    assert head_only_before == head_only_after, (
        "arm 1 failed: a HEAD-only build was expected to be SILENT here. If this fires, "
        "the ablation is not actually removing the other two terms."
    )

    assert gate_mod.fold(before) != gate_mod.fold(after), (
        "arm 2 failed: the full fingerprint did not move on a sibling worktree write. "
        "This is the defect R11 exists to catch."
    )


def test_c2_porcelain_only_ablation_is_silent_on_a_rederive_of_a_dirty_path(repo):
    """C2: the second write onto an already-dirty path leaves the porcelain byte-identical.

    Not a corner case. 'Re-deriving' means repeated writes to the same paths, so by the
    second write the path is already ` M`, and the status string stops moving while the
    bytes underneath keep changing.
    """
    derived = repo / "operator_review" / "MAC-542" / "derived.csv"
    derived.write_text("row,a\n1,x\n2,y\n")  # first write: clean -> dirty

    before = terms(repo)
    derived.write_text("row,a\n1,x\n2,y\n3,z\n")  # second write: dirty -> dirty
    after = terms(repo)

    assert before["porcelain"] == after["porcelain"], (
        "control is broken: the re-derive moved the porcelain string, so this is not the "
        "already-dirty case the card describes"
    )
    assert before["head"] == after["head"]

    weakened_before = gate_mod.fold(before, omit=("content",))
    weakened_after = gate_mod.fold(after, omit=("content",))
    assert weakened_before == weakened_after, (
        "arm 1 failed: a HEAD+porcelain build was expected to be SILENT here"
    )

    assert gate_mod.fold(before) != gate_mod.fold(after), (
        "arm 2 failed: the full fingerprint did not move when the bytes did"
    )
    assert before["content"] != after["content"]


def test_c1_end_to_end_through_the_cli_reports_unverified(repo):
    code, out = run_gate(repo, "before", "--label", "MAC-634")
    assert code == EXIT_VERIFIED, out

    (repo / "operator_review" / "MAC-542" / "derived.csv").write_text("row,a\n1,x\n2,y\n")

    code, out = run_gate(repo, "after", "--label", "MAC-634")
    assert code == EXIT_UNVERIFIED, out
    assert "UNVERIFIED" in out
    assert "operator_review/MAC-542/derived.csv" in out, out


def test_c2_end_to_end_through_the_cli_reports_unverified(repo):
    (repo / "operator_review" / "MAC-542" / "derived.csv").write_text("row,a\n1,x\n2,y\n")

    code, out = run_gate(repo, "before", "--label", "MAC-634")
    assert code == EXIT_VERIFIED, out

    (repo / "operator_review" / "MAC-542" / "derived.csv").write_text("row,a\n1,x\n2,y\n3,z\n")

    code, out = run_gate(repo, "after", "--label", "MAC-634")
    assert code == EXIT_UNVERIFIED, out
    assert "content" in out, out


# --------------------------------------------------------------------------------------
# The ablation hook itself, and the negative control.
# --------------------------------------------------------------------------------------


def test_omit_rejects_an_unknown_term_name(repo):
    """A silently-ignored misspelling would make every ablation above fold all three terms."""
    before = terms(repo)
    with pytest.raises(ValueError):
        gate_mod.fold(before, omit=("conten",))
    with pytest.raises(ValueError):
        gate_mod.fold(before, omit=("HEAD",))


def test_negative_control_a_still_tree_verifies(repo):
    """R7: the gate must be shown NOT firing, or UNVERIFIED means nothing."""
    code, out = run_gate(repo, "before", "--label", "MAC-634")
    assert code == EXIT_VERIFIED, out

    code, out = run_gate(repo, "after", "--label", "MAC-634")
    assert code == EXIT_VERIFIED, out
    assert "VERIFIED" in out and "UNVERIFIED" not in out, out


def test_negative_control_a_still_dirty_tree_verifies(repo):
    """A tree that was already dirty and stayed still is VERIFIED, not UNVERIFIED.

    Without this, R11 would refuse every measurement taken in the argus worktree, which is
    permanently dirty by ` M db/argus.db`.
    """
    (repo / "operator_review" / "MAC-542" / "derived.csv").write_text("row,a\n1,x\n2,y\n")
    (repo / "untracked_scratch.txt").write_text("scratch\n")

    code, out = run_gate(repo, "before", "--label", "MAC-634")
    assert code == EXIT_VERIFIED, out
    code, out = run_gate(repo, "after", "--label", "MAC-634")
    assert code == EXIT_VERIFIED, out


# --------------------------------------------------------------------------------------
# T1 and T2 earn their place: mutations the CONTENT term alone cannot see.
# --------------------------------------------------------------------------------------


def test_head_term_is_load_bearing(repo):
    """A commit that moves no worktree byte and no status line is HEAD-only.

    An empty commit is the minimal isolation of the term rather than an exaggeration of it:
    a sibling's ordinary commit also clears its own status lines, so it would fire T2 as
    well and prove nothing about T1. What it shares with this fixture is the part that
    matters to a measurement reading committed bytes — `git show HEAD:<path>` answers
    differently afterwards while the worktree view is untouched.
    """
    before = terms(repo)

    run_git(repo, "commit", "-q", "--allow-empty", "-m", "sibling commit")
    after = terms(repo)

    assert gate_mod.fold(before, omit=("head",)) == gate_mod.fold(after, omit=("head",)), (
        "arm 1 failed: porcelain and content were both expected to be SILENT, so this "
        "mutation does not isolate T1"
    )
    assert before["head"] != after["head"]
    assert gate_mod.fold(before) != gate_mod.fold(after), "arm 2 failed: T1 did not fire"


def test_porcelain_term_is_load_bearing(repo):
    """A sibling partially staging a dirty path moves the index and no worktree byte.

    This is the operation R10 itself mandates. `git add -p` is interactive and unavailable
    in this harness, so R10 sends a lane holding a dirty shared path to
    ``git apply --cached``, which writes the INDEX only. Status goes ` M` -> `MM` while
    ``git ls-files -m`` returns the same path with the same bytes, so the content term is
    structurally blind to it. ``update-index --cacheinfo`` reproduces that index write
    deterministically, without depending on a patch applying cleanly.
    """
    (repo / "mod.py").write_text("print(3)\n")  # this lane's dirty worktree copy
    before = terms(repo)

    blob = run_git(repo, "hash-object", "-w", "--stdin", input_text="print(2)\n").strip()
    run_git(repo, "update-index", "--cacheinfo", "100644,%s,mod.py" % blob)
    after = terms(repo)

    assert before["head"] == after["head"]
    assert before["content"] == after["content"], (
        "arm 1 failed: the content term was expected to be SILENT on an index-only write"
    )
    assert (before["porcelain"], after["porcelain"]) == (" M mod.py", "MM mod.py")
    assert gate_mod.fold(before) != gate_mod.fold(after), "arm 2 failed: T2 did not fire"


def test_a_repointed_symlink_fires(repo):
    """Hashing the referent would miss a swap that changes what the measurement reads."""
    (repo / "a.txt").write_text("A\n")
    (repo / "b.txt").write_text("B\n")
    link = repo / "current.txt"
    link.symlink_to("a.txt")
    before = terms(repo)

    link.unlink()
    link.symlink_to("b.txt")
    after = terms(repo)

    assert gate_mod.fold(before) != gate_mod.fold(after)
    assert before["content"]["current.txt"] != after["content"]["current.txt"]


# --------------------------------------------------------------------------------------
# Un-evaluated must never read as VERIFIED.
# --------------------------------------------------------------------------------------


def test_after_with_no_before_record_is_skipped_not_verified(repo):
    code, out = run_gate(repo, "after", "--label", "MAC-634")
    assert code == EXIT_SKIPPED, out
    assert "SKIPPED" in out and "VERIFIED" not in out, out


def test_skipped_exit_code_is_distinct_from_unverified_and_usage(repo):
    """Three distinct not-VERIFIED outcomes; collapsing any two loses a remedy."""
    no_record, _ = run_gate(repo, "after", "--label", "MAC-634")

    run_gate(repo, "before", "--label", "MAC-634")
    (repo / "mod.py").write_text("print(3)\n")
    moved, _ = run_gate(repo, "after", "--label", "MAC-634")

    bad_mode, _ = run_gate(repo, "sideways", "--label", "MAC-634")

    assert (no_record, moved, bad_mode) == (EXIT_SKIPPED, EXIT_UNVERIFIED, EXIT_USAGE)
    assert len({no_record, moved, bad_mode}) == 3


def test_a_vanished_path_git_does_not_call_deleted_is_unevaluated(repo, monkeypatch):
    """A path that disappears mid-walk is un-evaluated, not absent.

    ``deleted_paths`` is stubbed empty to reproduce the race deterministically: the path is
    listed by ``ls-files -m`` and is gone from disk, but git does not vouch for the deletion.
    """
    monkeypatch.setattr(gate_mod, "deleted_paths", lambda root: set())
    (repo / "mod.py").unlink()

    manifest, unevaluated = gate_mod.content_manifest(str(repo), set())
    assert manifest["mod.py"] == gate_mod.UNREADABLE
    assert unevaluated, "a vanished path produced no un-evaluated note"


def test_a_genuinely_deleted_path_is_determinate_not_unevaluated(repo):
    """git vouching for the deletion makes it a known state, so a still tree still VERIFIES."""
    (repo / "mod.py").unlink()

    manifest, unevaluated = gate_mod.content_manifest(str(repo), set())
    assert manifest["mod.py"] == "deleted"
    assert unevaluated == []

    code, out = run_gate(repo, "before", "--label", "MAC-634")
    assert code == EXIT_VERIFIED, out
    code, out = run_gate(repo, "after", "--label", "MAC-634")
    assert code == EXIT_VERIFIED, out


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses the permission bit")
def test_an_unreadable_path_is_skipped_rather_than_verified(repo):
    secret = repo / "unreadable.txt"
    secret.write_text("x\n")
    secret.chmod(0o000)
    try:
        code, out = run_gate(repo, "before", "--label", "MAC-634")
        assert code == EXIT_VERIFIED, out
        code, out = run_gate(repo, "after", "--label", "MAC-634")
        assert code == EXIT_SKIPPED, out
        assert "SKIP" in out, out
    finally:
        secret.chmod(0o644)


# --------------------------------------------------------------------------------------
# --writes: the exclusion must be usable without becoming a way to launder a green.
# --------------------------------------------------------------------------------------


def test_writes_excludes_the_measurements_own_output(repo):
    out_path = repo / "operator_review" / "MAC-634"
    out_path.mkdir(parents=True)

    code, out = run_gate(
        repo, "before", "--label", "MAC-634", "--writes", "operator_review/MAC-634/rows.csv"
    )
    assert code == EXIT_VERIFIED, out
    assert "excluded" in out, out

    (out_path / "rows.csv").write_text("count\n43089\n")  # the measurement writes its artifact

    code, out = run_gate(repo, "after", "--label", "MAC-634")
    assert code == EXIT_VERIFIED, out


def test_writes_does_not_mask_a_sibling_write_to_another_path(repo):
    code, out = run_gate(
        repo, "before", "--label", "MAC-634", "--writes", "operator_review/MAC-634/rows.csv"
    )
    assert code == EXIT_VERIFIED, out

    (repo / "operator_review" / "MAC-542" / "derived.csv").write_text("row,a\n1,x\n2,y\n")

    code, out = run_gate(repo, "after", "--label", "MAC-634")
    assert code == EXIT_UNVERIFIED, out


def test_writes_is_counted_in_the_verdict_line(repo):
    """An over-broad exclusion has to be visible to the ratifier, not silent."""
    code, out = run_gate(
        repo, "before", "--label", "MAC-634", "--writes", "a.csv", "b.csv", "c.csv"
    )
    assert code == EXIT_VERIFIED, out
    assert "3 excluded" in out, out

    code, out = run_gate(repo, "after", "--label", "MAC-634")
    assert "3 excluded" in out, out


def test_writes_on_after_is_a_usage_error(repo):
    """Accepting it twice would let an after-run exclude a path the before-run hashed."""
    run_gate(repo, "before", "--label", "MAC-634")
    (repo / "operator_review" / "MAC-542" / "derived.csv").write_text("row,a\n1,x\n2,y\n")

    code, out = run_gate(
        repo, "after", "--label", "MAC-634", "--writes", "operator_review/MAC-542/derived.csv"
    )
    assert code == EXIT_USAGE, out


def test_docstring_promise_names_the_exit_codes_it_returns(repo):
    """R9: the usage text is part of the gate. A drifted promise is an unratified change."""
    text = GATE.read_text()
    for phrase in (
        "Exit 0 = VERIFIED",
        "Exit 1 = UNVERIFIED",
        "Exit 2 = usage",
        "Exit 3 = SKIPPED",
    ):
        assert phrase in text, "the docstring no longer promises: %s" % phrase
