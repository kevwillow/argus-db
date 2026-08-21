"""Tests for scripts/check_mac781_anchor_clause.py.

Locks the gate's behaviour at three failure modes and the happy path:

* anchor missing (0 lines)         -> gate FAILs with the anchor diagnostic
* anchor present + clause drifted  -> gate FAILs with the clause diagnostic
* anchor present + clause match    -> gate PASSes (skips db in positive-control mode)

The db-check arm is exercised via the integration harness under
operator_review/MAC-781/post_migration_check.sh after the migration is
applied to the post-MAC-764 canonical. Unit tests stay positive-control-only
so they do not depend on canonical state.

Stubs:
* ``scratch_doc_with_anchor`` -- a tiny markdown file with one matching
  anchor and one matching clause.
* ``scratch_doc_drifted`` -- same anchor, clause text altered.
* ``scratch_doc_no_anchor`` -- anchor tag removed.

Run with ``pytest tests/test_check_mac781_anchor_clause.py``.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / "scripts" / "check_mac781_anchor_clause.py"

EXPECTED_CLAUSE = "Distinguishes general-purpose CCTV from existing `covert_cam`"
ANCHOR_ID = "mac781-cp33-s2-1-cctv_camera"


def _write_scratch(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "scratch_doc.md"
    p.write_text(body, encoding="utf-8")
    return p


@pytest.fixture
def scratch_doc_with_anchor(tmp_path: Path) -> Path:
    return _write_scratch(
        tmp_path,
        f"# scratch\n\n"
        f"Some prose.\n\n"
        f"| `cctv_camera` <a id=\"{ANCHOR_ID}\"></a> | cell | {EXPECTED_CLAUSE} | ... |\n\n"
        f"More prose.\n",
    )


@pytest.fixture
def scratch_doc_drifted(tmp_path: Path) -> Path:
    # Same anchor; clause text altered -> drift detection must fire.
    return _write_scratch(
        tmp_path,
        f"# scratch\n\n"
        f"| `cctv_camera` <a id=\"{ANCHOR_ID}\"></a> | cell | "
        f"Smokescreens the prose entirely | ... |\n\n",
    )


@pytest.fixture
def scratch_doc_no_anchor(tmp_path: Path) -> Path:
    return _write_scratch(
        tmp_path,
        f"# scratch\n\nNo anchor placed.\n",
    )


@pytest.fixture
def scratch_doc_two_anchors(tmp_path: Path) -> Path:
    # Same anchor id on two different lines -> ambiguity, gate must refuse.
    return _write_scratch(
        tmp_path,
        f"# scratch\n\n"
        f"| row a <a id=\"{ANCHOR_ID}\"></a> | {EXPECTED_CLAUSE} |\n"
        f"| row b <a id=\"{ANCHOR_ID}\"></a> | {EXPECTED_CLAUSE} |\n",
    )


def _run_gate(scratch: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--expected-clause", EXPECTED_CLAUSE,
            "--positive-control", str(scratch),
        ],
        capture_output=True,
        text=True,
    )


def test_gate_passes_on_clean_doc(scratch_doc_with_anchor: Path) -> None:
    proc = _run_gate(scratch_doc_with_anchor)
    assert proc.returncode == 0, (
        f"expected PASS; got rc={proc.returncode}\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    assert "OVERALL: PASS" in proc.stdout


def test_gate_fails_on_clause_drift(scratch_doc_drifted: Path) -> None:
    proc = _run_gate(scratch_doc_drifted)
    assert proc.returncode == 1
    assert "FAIL clause" in proc.stdout
    assert "OVERALL: FAIL" in proc.stdout


def test_gate_fails_when_anchor_missing(scratch_doc_no_anchor: Path) -> None:
    proc = _run_gate(scratch_doc_no_anchor)
    assert proc.returncode == 1
    assert "resolves to 0 lines" in proc.stdout
    assert "OVERALL: FAIL" in proc.stdout


def test_gate_fails_when_anchor_ambiguous(scratch_doc_two_anchors: Path) -> None:
    proc = _run_gate(scratch_doc_two_anchors)
    assert proc.returncode == 1
    assert "ambiguous" in proc.stdout
    assert "OVERALL: FAIL" in proc.stdout


def test_gate_canonical_anchor_resolves_to_one_line() -> None:
    """Run the gate against the canonical BIBLE_AMENDMENTS.md. The HTML
    anchor was added by the MAC-781 commit, so this is the happy-path
    doc-side check (db arm skipped because the migration has not landed
    yet at the time these unit tests run)."""
    canonical = REPO_ROOT / "docs" / "engineering" / "BIBLE_AMENDMENTS.md"
    assert canonical.exists()
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--expected-clause", EXPECTED_CLAUSE,
            # --positive-control reuses --doc machinery but skips db check;
            # the canonical doc is the same one the default --doc points at.
            "--doc", str(canonical),
        ],
        capture_output=True,
        text=True,
    )
    # db check fails (migration not applied) -> overall FAIL, but anchor
    # and clause PASS. We only assert the doc-side arms here.
    assert "anchor resolves to 1 line" in proc.stdout
    assert "clause match: PASS" in proc.stdout
    assert "FAIL db" in proc.stdout
    assert proc.returncode == 1