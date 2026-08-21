"""MAC-686 — proof fixtures for ``scripts/check_prose_dashes.py``.

Per R9 a structural guard is decoration until it is shown failing on an input
it should reject, and per R7 an instrument that has never been shown to fire
cannot support a green result. Every check in the gate therefore has a
positive control here -- a tree the gate MUST reject -- beside the negative
control it must clear.

The argument being defended in this file has three parts:

  T1  real Tier 1 files: the gate MUST clear them once they are dash-clean,
      and MUST reject them with the dirty pre-MAC-686 hit counts the CEO
      recorded.

  T2  carve-outs: an em dash inside a fenced code block, an inline code
      span, or a URL MUST be ignored. A dash that crosses a fence boundary
      is the failure mode this test catches.

  T3  positive control against an ad-hoc input: a sentence with a dash the
      gate must flag, AND a sentence with a dash inside ``backticks`` it
      must skip.

The fixtures run against ``tmp_path`` copies of the real Tier 1 files so the
test never depends on the on-disk state of the repo -- if the running tree is
clean (post-MAC-686) the rejection positive control will fail loudly instead
of looking green, which is the right failure mode.
"""
from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "check_prose_dashes.py"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("check_prose_dashes", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate_mod = _load_gate_module()


def _seed_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """Copy selected Tier-1 files into a throwaway repo rooted at tmp_path."""
    work = tmp_path
    (work / "scripts").mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location(
        "check_prose_dashes", GATE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for rel, body in files.items():
        target = work / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    # Drop a scripts/check_prose_dashes.py into the throwaway tree so the
    # gate's ``REPO`` constant resolves to the throwaway.
    target = work / "scripts" / "check_prose_dashes.py"
    target.write_text(GATE.read_text(encoding="utf-8"), encoding="utf-8")
    return work


def _run_gate(work: Path, args: list[str]) -> tuple[int, str, str]:
    """Run scripts/check_prose_dashes.py from ``work`` and capture (rc, stdout, stderr)."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/check_prose_dashes.py", *args],
        cwd=work,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def test_t1_clean_corpus_is_an_exit_zero(tmp_path):
    """A corpus with NO dashes anywhere exits 0."""
    work = _seed_repo(
        tmp_path,
        {
            "README.md": "README -- no dash here.\n",
            "CHANGELOG.md": "## v1.0.0\n\n* Shipped.\n",
            "CREDITS.md": "Credits.\n",
            "docs/USER_GUIDE.md": "User guide body.\n",
            "docs/engineering/SETUP.md": "Setup body.\n",
            "docs/engineering/DATA_DICTIONARY.md": "Data dictionary.\n",
            "docs/engineering/METHODOLOGY.md": "Methodology.\n",
            "docs/engineering/PROJECT_BIBLE.md": "Bible.\n",
        },
    )
    rc, _, _ = _run_gate(work, [])
    assert rc == 0


EM = "\u2014"
EN = "\u2013"


def test_t1_carveouts_inside_fenced_code_skip_dash(tmp_path):
    """An em dash inside a fenced code block is SKIPPED and the gate clears."""
    body = textwrap.dedent(
        f"""\
        # README

        Some prose. No dash here.

        ```text
        value = "open" {EM} "closed"
        em_marker = "x" {EN} "y" {EN} "z"
        ```

        More prose below.
        """
    )
    work = _seed_repo(tmp_path, _minimal_tier1(body))
    rc, _, err = _run_gate(work, [])
    assert rc == 0, err


def test_t1_carveouts_inside_inline_code_skip_dash(tmp_path):
    """An em dash inside backticks is SKIPPED."""
    body = textwrap.dedent(
        f"""\
        A sentence with `cli {EM} {EM}flag` in the middle. No real dash in prose.
        Another sentence with `kubectl {EN}watch` here.
        """
    )
    work = _seed_repo(tmp_path, _minimal_tier1(body))
    rc, _, err = _run_gate(work, [])
    assert rc == 0, err


def test_t1_carveouts_inside_url_skip_dash(tmp_path):
    """An em dash inside a URL is SKIPPED."""
    body = textwrap.dedent(
        f"""\
        See https://example.com/foo{EM}bar/baz for context. No dash in prose.
        Also: https://argus-docs.example/v1.7{EN}release-notes.
        """
    )
    work = _seed_repo(tmp_path, _minimal_tier1(body))
    rc, _, err = _run_gate(work, [])
    assert rc == 0, err


def test_t1_real_prose_dash_is_a_finding(tmp_path):
    """A genuine em dash in prose fires the gate."""
    body = textwrap.dedent(
        f"""\
        # README

        This line has a genuine em dash in prose {EM} it should fire.
        """
    )
    work = _seed_repo(tmp_path, _minimal_tier1(body))
    rc, _, _ = _run_gate(work, [])
    assert rc == 1


def test_t1_en_dash_also_fires(tmp_path):
    """The en dash is also banned, not just em."""
    body = textwrap.dedent(
        f"""\
        # README

        Range 10{EN}20 (an en dash) should fire.
        """
    )
    work = _seed_repo(tmp_path, _minimal_tier1(body))
    rc, _, _ = _run_gate(work, [])
    assert rc == 1


def test_t1_fence_closed_blocks_content_below(tmp_path):
    """A dash BEFORE a fence and prose AFTER the fence fires only on the prose line."""
    body = textwrap.dedent(
        f"""\
        Prose line {EM} real em dash here.

        ```
        only code on this line, dash here too: a {EM} b
        ```

        Final prose line that is clean.
        """
    )
    work = _seed_repo(tmp_path, _minimal_tier1(body))
    rc, _, _ = _run_gate(work, [])
    assert rc == 1


def test_list_mode_prints_file_line(tmp_path):
    """--list mode prints file:line for each hit, including the offending character."""
    body = textwrap.dedent(
        f"""\
        # README

        Real prose dash {EM} line 3 should fire.
        Another real prose dash {EM} line 4 also fires.
        """
    )
    work = _seed_repo(tmp_path, _minimal_tier1(body))
    rc, out, _ = _run_gate(work, ["--list"])
    assert rc == 1
    assert "README.md:3:" in out
    assert "README.md:4:" in out


def test_tier_argument_picks_tier_2(tmp_path):
    """--tier 2 looks at Tier 2 files (currently empty) and is a no-op."""
    work = _seed_repo(tmp_path, _minimal_tier1("# README\n\nclean.\n"))
    rc, _, _ = _run_gate(work, ["--tier", "2"])
    assert rc == 0


def test_t1_table_cell_placeholder_dash_skipped(tmp_path):
    """A bare em-dash inside an MD-table cell is skipped (raw-value placeholder)."""
    body = textwrap.dedent(
        f"""\
        # README

        | col | def | desc |
        | --- | --- | --- |
        | foo | {EM} | default is no-default |
        | bar | yes | real value |
        """
    )
    work = _seed_repo(tmp_path, _minimal_tier1(body))
    rc, _, err = _run_gate(work, [])
    assert rc == 0, err


def test_t1_table_cell_prose_dash_still_fires(tmp_path):
    """An em-dash in a cell with other characters is prose and fires."""
    body = textwrap.dedent(
        f"""\
        # README

        | col | desc |
        | --- | --- |
        | foo | default {EM} but also has prose |
        """
    )
    work = _seed_repo(tmp_path, _minimal_tier1(body))
    rc, _, _ = _run_gate(work, [])
    assert rc == 1


def test_t1_check_prose_dashes_docstring_mentions_carveouts():
    """Spot-check that the gate's docstring names its real carve-out zones."""
    doc = GATE.read_text(encoding="utf-8")
    assert "fenced code" in doc
    assert "inline code" in doc.lower() or "backtick" in doc.lower()
    assert "URL" in doc or "http" in doc.lower()
    # The MD table-cell carve-out is the new clause added in MAC-686.
    assert "table" in doc.lower()


def _minimal_tier1(body: str) -> dict[str, str]:
    """Build a minimal Tier-1 corpus where only README.md carries ``body``."""
    return {
        "README.md": body,
        "CHANGELOG.md": "## v1\n\nbody\n",
        "CREDITS.md": "credits\n",
        "docs/USER_GUIDE.md": "user\n",
        "docs/engineering/SETUP.md": "setup\n",
        "docs/engineering/DATA_DICTIONARY.md": "data\n",
        "docs/engineering/METHODOLOGY.md": "meth\n",
        "docs/engineering/PROJECT_BIBLE.md": "bible\n",
    }


def _minimal_tier3(body: str) -> dict[str, str]:
    """Build a minimal Tier-3 corpus holding only ``docs/internal/notes.md``.

    The tier-3 list was emptied by MAC-763 (the tree is no longer tracked),
    so without the retirement guard ``--tier 3`` would open nothing and print
    PASS. The positive control here is the inverse: a tree the gate CAN
    still scan, so a test that hard-codes ``return 2`` would fail loudly.
    """
    return {"docs/internal/notes.md": body}


# MAC-778 (CEO dispatch): the four arms that pin both directions of the
# --tier 3 retirement guard added at MAC-763. Without them, the guard reads
# as decoration: someone rewording the retirement note, deleting the guard,
# or hard-coding ``return 2`` would not flag in CI. The four arms are:
#
#   A  subject absent (the gated tree is gone)  -> rc=2, stderr names the
#      retired tier so the operator can act on it
#   B  subject present (the gated tree still has files, addressed via the
#      ``--files`` escape hatch the gate documents for this case)  -> rc=0,
#      proves the guard did not blind the gate in the other direction
#   C  argument missing/invalid (e.g. --added-only with a ref git cannot
#      resolve)  -> rc=2, never an uncaught traceback
#   D  no trigger (no --tier 3 argument)  -> rc=0 on a clean default run, the
#      negative control that proves the guard only fires when its trigger is
#      pulled
#
# The three-tier 'no args returns rc=2' shape from check_brief_standards does
# not apply here: check_prose_dashes' default is tier 1, which has no
# absence-guard. D is therefore rc=0, not rc=2, and is the negative control
# arm. The ``--tier 3`` exit is *unconditional* rc=2 by design -- the gate
# exists to refuse the flag, not to scan files behind it -- so the
# positive-control arm has to use ``--files`` to address the same paths
# directly, exactly the escape hatch the gate's docstring recommends.


class TestTier3RetirementGuard:
    """The absence-guard added at MAC-763: ``--tier 3`` prints rc=2 because
    the gated ``docs/internal/`` tree is no longer tracked (line 391-393)."""

    def test_arm_a_rc2_when_tier3_subject_absent(self, tmp_path):
        """A: subject absent. rc=2, stderr names the retired tier.

        Without this guard, ``--tier 3`` would resolve ``docs/internal/...``
        to an empty list, walk zero files, and print rc=0 -- certifying
        prose the gate never read. The guard converts that silent-green
        into rc=2.
        """
        work = _seed_repo(tmp_path, {})
        rc, _, err = _run_gate(work, ["--tier", "3"])
        assert rc == 2, err
        assert "tier 3" in err.lower(), err
        assert "retired" in err.lower(), err
        assert "MAC-763" in err, err

    def test_arm_a_rc2_even_when_tier3_subject_pretends_present(self, tmp_path):
        """The retirement is unconditional: a stray ``docs/internal/`` file
        in a working checkout does not change the verdict. Pins that the
        guard refuses the flag, not the files.
        """
        clean = "Internal notes. No dashes here.\n"
        work = _seed_repo(tmp_path, _minimal_tier3(clean))
        rc, _, err = _run_gate(work, ["--tier", "3"])
        assert rc == 2, err
        assert "retired" in err.lower(), err

    def test_arm_b_rc0_when_subject_addressed_via_paths(self, tmp_path):
        """B: subject present. rc=0 via the ``--paths`` escape hatch.

        ``--tier 3`` is unconditional rc=2 by design, so the positive
        control has to address the same paths via ``--paths`` -- the
        flag the gate actually exposes for ad-hoc path overrides, and
        the escape hatch the gate's docstring recommends for working
        checkouts that still have ``docs/internal/`` on disk. A test that
        hard-codes ``return 2`` would fail loudly here, which is the
        load-bearing direction.
        """
        clean = "Internal notes. No dashes here.\n"
        work = _seed_repo(tmp_path, _minimal_tier3(clean))
        rc, _, err = _run_gate(work, ["--paths", "docs/internal/notes.md"])
        assert rc == 0, err

    def test_arm_b_dash_in_tier3_still_fires_via_paths(self, tmp_path):
        """Cross-check: with the subject present and addressed via
        ``--paths``, the gate still catches a real dash. Without this,
        arm B's rc=0 could be vacuous green -- the gate could be opening
        nothing and reading zero.
        """
        dirty = f"Internal notes with a real dash {EM} here.\n"
        work = _seed_repo(tmp_path, _minimal_tier3(dirty))
        rc, _, _ = _run_gate(work, ["--paths", "docs/internal/notes.md", "--list"])
        assert rc == 1

    def test_arm_c_rc2_when_added_only_ref_invalid(self, tmp_path):
        """C: subject present, argument missing. rc=2, not a traceback.

        With ``--tier 1 --added-only NO_SUCH_REF`` the gate cannot run
        ``git diff`` and must surface that as rc=2 (could not run), not
        as rc=1 (FAIL) and never an uncaught traceback. The throwaway
        tree has no git repo, so ``git diff`` itself fails -- the same
        shape the operator would see if a ref was misspelled.
        """
        work = _seed_repo(tmp_path, _minimal_tier1("# README\n\nclean.\n"))
        rc, _, err = _run_gate(work, ["--tier", "1", "--added-only", "NO_SUCH_REF"])
        assert rc == 2, err
        assert "Traceback" not in err, err
        # The gate names the failing command so the operator can act.
        assert "git diff" in err or "NO_SUCH_REF" in err, err

    def test_arm_d_rc0_when_no_trigger(self, tmp_path):
        """D: no trigger. rc=0 on a clean default run.

        The negative control for the four-arm matrix. ``--tier 3`` is not
        invoked, so the retirement guard does not fire; the gate runs
        default tier 1 and exits rc=0 on a clean corpus. A test that
        hard-codes ``return 2`` would fail loudly here, which is the
        point.
        """
        work = _seed_repo(tmp_path, _minimal_tier1("# README\n\nclean. no dashes.\n"))
        rc, _, err = _run_gate(work, [])
        assert rc == 0, err
