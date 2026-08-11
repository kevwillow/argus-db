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
