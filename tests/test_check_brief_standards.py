"""MAC-778 -- proof fixtures for the two absence-guards in
``scripts/check_brief_standards.py`` (lines 242, 245).

Per R9 a structural guard is decoration until it is shown failing on an input
it should reject, and per R7 an instrument that has never been shown to fire
cannot support a green result. The four arms per guard pin both directions:
absent fires, present stays silent, the missing-argument arm does not
traceback, and the no-args arm refuses to run.

The two absence-guards in this file:

  * ``standards_present()`` (line 245). MAC-763 untracked ``operator_review/``,
    so a fresh clone has no ``BRIEF_STANDARDS.md`` to read. R0 is a regex over
    the BRIEF's text saying it cites the standards; without the guard, the gate
    would print PASS while certifying inheritance from a document not in the
    checkout.
  * ``if not Path(path).is_file()`` (line 251-257). A brief named on the command
    line that is not on disk is a gate that did not run. Report it as rc=2,
    never rc=0, never rc=1.
  * the no-args guard at line 242, a sibling failure path that has always
    existed but never had a test pinning its exit code.

The load-bearing test is ``test_arm_b_*`` -- the positive control that proves
the absence-guard did not blind the gate in the other direction. A test that
only asserts rc=2 passes if someone hard-codes ``return 2`` unconditionally.

The throwaway tree owns its own standards file (and its own copy of the gate),
so a test never depends on the operator's untracked ``operator_review/`` -- a
test that only passes on the operator's disk is exactly the defect MAC-763
filed to fix.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "check_brief_standards.py"
STANDARDS_REL = "operator_review/BRIEF_STANDARDS.md"

# A minimal brief that satisfies R0 (cites the standards) and trips none of
# R1, R6, R7 -- so the only thing under test is the absence-guard. R2 / R3
# have no trigger either.
PASSING_BRIEF = "The brief cites BRIEF_STANDARDS.md, which is the rule.\n"


def _install_gate(work: Path) -> None:
    """Copy the gate source into the throwaway tree.

    The script resolves ``Path(__file__).resolve().parents[1]`` to its own
    repo root, so the throwaway tree has to own the script -- otherwise the
    standards_present() check looks at the LIVE operator_review/ instead of
    the throwaway's. Same trick ``tests/test_check_prose_dashes.py`` uses.
    """
    (work / "scripts").mkdir(parents=True, exist_ok=True)
    (work / "scripts" / "check_brief_standards.py").write_text(
        GATE.read_text(encoding="utf-8"), encoding="utf-8"
    )


def _seed_standards(work: Path) -> Path:
    """Drop a minimal standards file at the operator_review/ path."""
    target = work / STANDARDS_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Brief standards\n\nR0 cite the standards file.\n", encoding="utf-8")
    return target


def _seed_brief(work: Path, body: str = PASSING_BRIEF) -> Path:
    """Drop a brief at the throwaway root."""
    target = work / "brief.md"
    target.write_text(body, encoding="utf-8")
    return target


def _run_gate(work: Path, args: list[str]) -> tuple[int, str, str]:
    """Run scripts/check_brief_standards.py from ``work`` and capture (rc, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "scripts/check_brief_standards.py", *args],
        cwd=work,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A throwaway tree with the gate installed and no standards file."""
    _install_gate(tmp_path)
    return tmp_path


class TestStandardsPresenceGuard:
    """The absence-guard added at MAC-763: a tracked-out standards file
    converts vacuous green into rc=2 (line 243-245)."""

    def test_arm_a_rc2_when_standards_absent(self, worktree):
        """A: subject absent. rc=2, stderr names the missing path.

        Without this guard, R0 would PASS forever -- the brief cites the
        standards file by name, but the file is not on disk. The guard
        converts that silent-green into rc=2.
        """
        brief = _seed_brief(worktree)
        rc, _, err = _run_gate(worktree, [str(brief)])
        assert rc == 2, err
        # The stderr message names the missing path so an operator can act on it.
        assert STANDARDS_REL in err, err
        assert "MAC-763" in err, err

    def test_arm_b_rc0_when_standards_present_and_brief_passes(self, worktree):
        """B: subject present. rc=0 -- proves the guard did not blind.

        The load-bearing arm. A test that only asserts rc=2 passes if
        someone hard-codes ``return 2`` unconditionally. This one runs the
        gate end-to-end with both the standards file and a brief that
        cites it, and asserts rc=0.
        """
        _seed_standards(worktree)
        brief = _seed_brief(worktree)
        rc, out, err = _run_gate(worktree, [str(brief)])
        assert rc == 0, (out, err)
        assert "PASS" in out, out

    def test_arm_c_rc2_when_brief_missing_with_standards_present(self, worktree):
        """C: subject present, argument missing. rc=2, not a traceback.

        A named brief that is not on disk is a gate that did not run.
        Report it as rc=2 (could not run), not rc=1 (FAIL), and never an
        uncaught traceback. The separation is what keeps "could not run"
        from being read as a pass.
        """
        _seed_standards(worktree)
        # Brief path the gate cannot find.
        rc, _, err = _run_gate(worktree, ["briefs/does_not_exist.md"])
        assert rc == 2, err
        assert "MISSING" in err, err
        assert "Traceback" not in err, err

    def test_arm_d_rc2_when_no_args(self, worktree):
        """D: no args. rc=2.

        The gate refuses to run without at least one brief named. rc=2
        means "could not run"; rc=1 is reserved for "a brief was read and
        broke a rule". Collapsing the two is how "could not run" reads as
        a pass.
        """
        rc, _, _ = _run_gate(worktree, [])
        assert rc == 2


class TestGateSeesBothSides:
    """Cross-cutting: the gate must distinguish the THREE exit codes it owns.

    * rc=2 means "could not run" (no args, standards absent, brief missing).
    * rc=1 means "a brief was read and broke a rule".
    * rc=0 means "all briefs read and passed".

    A gate that funnels every failure into rc=2 (or every failure into rc=1)
    collapses the verifier's ability to tell "ran but failed" from "never
    ran". These two tests pin the distinction by feeding the gate a brief
    that breaks a real rule and confirming the rc=1 path still fires.
    """

    def test_rc1_still_fires_when_a_brief_breaks_r0(self, worktree):
        """A brief that does NOT cite the standards file fails R0 -> rc=1.

        This is the negative control for the absence-guard: it confirms
        that rc=2 stays reserved for "could not run" and that a real rule
        violation still surfaces as rc=1 even when the standards file is
        present.
        """
        _seed_standards(worktree)
        # Brief that triggers R0 -- no cite of BRIEF_STANDARDS.md.
        bad = _seed_brief(worktree, "This brief does not cite the standards.\n")
        rc, out, _ = _run_gate(worktree, [str(bad)])
        assert rc == 1, out
        assert "R0" in out, out

    def test_arm_b_does_not_depend_on_a_pre_existing_standards_file(self, worktree):
        """The positive control lives entirely in tmp_path.

        A test that only passes on the operator's disk is the defect MAC-763
        filed to fix. The throwaway tree owns its own standards file, so
        this test does not touch ``operator_review/``.
        """
        # The throwaway was created without the standards file. Confirm.
        assert not (worktree / STANDARDS_REL).is_file()
        _seed_standards(worktree)
        brief = _seed_brief(worktree)
        rc, _, _ = _run_gate(worktree, [str(brief)])
        assert rc == 0
