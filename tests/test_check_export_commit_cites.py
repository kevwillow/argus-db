"""MAC-703 -- proof fixtures for ``scripts/check_export_commit_cites.py``.

The gate's job is to stop a generated export artifact from shipping a commit
cite that ``git cat-file -t`` cannot resolve. Per R9 a gate is decoration until
it is shown failing on an input it should reject, and per R7 a green result on a
corpus that turned out to be empty is not evidence. Every check here therefore
has a positive control beside the negative control it must clear -- which
matters more than usual for this gate, because the MAC-703 fix removes the only
commit cite in the corpus, so the gate's steady state is a ZERO-YIELD pass.

Argument defended in this file (in five parts):

  T1  pattern narrowness:  the scanner matches the CITE FORM (the word
      ``commit`` then an optional backticked 7-40 hex token), not bare hex.
      The fixtures assert it ignores SAR-10 ``argus_record_id`` values, BLE
      UUID fields, and the Paperclip COMMENT uuid at ``export_lynceus.py:2001``
      -- the last one is backticked hex sitting in a real generated artifact,
      so a wider pattern would fail this gate on a correct release.

  T2  resolution predicate:  a cite passes only when ``git cat-file -t`` says
      ``commit``. A sha that resolves to a blob or a tree is a FAIL, not a
      pass, because it is still not the commit the artifact claims.

  T3  verdict wiring:  dead cite -> exit 1, resolvable cite -> exit 0, no
      readable file in scope -> exit 3 (uncertified, not clean). The exit-3
      arm is the one that keeps an absent-corpus run from reading as a pass.

  T4  R7 positive control:  ``--positive-control`` plants the exact dead sha
      from the issue (``6853780``) and asserts the scanner fires; it exits 0
      only when the scanner returned 1. A second arm asserts the control
      cannot be stranded short of the scan by an argument combination --
      ``check_push_blob_sizes.py`` shipped a control that died at exit 2
      before reaching its scan (repaired at MAC-612, ``e3a5d1a``).

  T5  the shipped fix:  ``export_lynceus.py`` no longer contains the literal
      ``commit `6853780``` and the coverage-report builder takes a
      ``matrix_sha256`` content hash instead.

Fixtures build their corpus in ``tmp_path`` so the test never depends on
whether ``exports/`` has been regenerated in the running tree. MAC-612 owns the
regen; this gate must be provable before it.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "check_export_commit_cites.py"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("check_export_commit_cites", GATE)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("check_export_commit_cites", module)
    spec.loader.exec_module(module)
    return module


gate_mod = _load_gate_module()


def _run_gate(*args):
    proc = subprocess.run(
        [sys.executable, str(GATE), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# T1: pattern narrowness.
# ---------------------------------------------------------------------------


def test_t1_matches_the_cite_form():
    found = gate_mod.COMMIT_CITE_RE.findall(
        "the matrix at `x/y.md` (commit `6853780`). It is embedded verbatim."
    )
    assert found == ["6853780"]


def test_t1_matches_unbackticked_cite_form():
    assert gate_mod.COMMIT_CITE_RE.findall("see commit 817c475830793203d") == [
        "817c475830793203d"
    ]


def test_t1_ignores_bare_hex_that_is_not_a_cite():
    # SAR-10 argus_record_id (16-hex SHA-256 prefix) and a BLE UUID field --
    # coverage_report.md alone carries 999 tokens matching [0-9a-f]{7,40}.
    corpus = (
        '"argus_record_id": "3f2a91c04be7d581",\n'
        '"identifier": "0000fc6d-0000-1000-8000-00805f9b34fb",\n'
        "sha256 `1f2f212458d96dc7146e261bdaf6cf46402e5c3eef275cb9ac37942f4389a7f3`\n"
    )
    assert gate_mod.COMMIT_CITE_RE.findall(corpus) == []


def test_t1_ignores_the_paperclip_comment_uuid_at_export_lynceus_2001():
    # Real bytes from a generated artifact. Backticked hex, NOT a commit.
    corpus = (
        "Strict §8.4 binds at HB36 (board-ratified MAC-1 "
        "[`613ec532`](/MAC/issues/MAC-1#comment-613ec532-d8cb-4f0f-a35b-c811e2864d7d) "
        "2026-05-06)."
    )
    assert gate_mod.COMMIT_CITE_RE.findall(corpus) == []


# ---------------------------------------------------------------------------
# T2: resolution predicate.
# ---------------------------------------------------------------------------


def test_t2_dead_sha_does_not_resolve():
    assert gate_mod.resolves_to_commit("6853780", REPO) is False


def test_t2_head_resolves():
    head = subprocess.run(
        ("git", "-C", str(REPO), "rev-parse", "HEAD"),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert gate_mod.resolves_to_commit(head, REPO) is True


def test_t2_blob_sha_is_not_accepted_as_a_commit():
    # A tree/blob object resolves under cat-file but is not a commit.
    tree = subprocess.run(
        ("git", "-C", str(REPO), "rev-parse", "HEAD^{tree}"),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert gate_mod.resolves_to_commit(tree, REPO) is False


# ---------------------------------------------------------------------------
# T3: verdict wiring.
# ---------------------------------------------------------------------------


def test_t3_dead_cite_exits_one(tmp_path):
    art = tmp_path / "coverage_report.md"
    art.write_text("matrix at `x.md` (commit `6853780`).\n", encoding="utf-8")
    rc, out = _run_gate(str(art))
    assert rc == gate_mod.EXIT_FAIL
    assert "DOES NOT RESOLVE" in out


def test_t3_live_cite_exits_zero(tmp_path):
    head = subprocess.run(
        ("git", "-C", str(REPO), "rev-parse", "HEAD"),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    art = tmp_path / "coverage_report.md"
    art.write_text(f"generated at commit `{head}`.\n", encoding="utf-8")
    rc, out = _run_gate(str(art))
    assert rc == gate_mod.EXIT_OK
    assert "every commit cite" in out


def test_t3_absent_corpus_is_uncertified_not_clean(tmp_path):
    rc, out = _run_gate("--exports-dir", str(tmp_path / "nonexistent"))
    assert rc == gate_mod.EXIT_UNEVALUATED
    assert "uncertified" in out


def test_t3_zero_cite_pass_says_nothing_was_evaluated(tmp_path):
    art = tmp_path / "coverage_report.md"
    art.write_text("matrix at `x.md` (sha256 `deadbeefcafe`).\n", encoding="utf-8")
    rc, out = _run_gate(str(art))
    assert rc == gate_mod.EXIT_OK
    assert "nothing was evaluated" in out


# ---------------------------------------------------------------------------
# T4: R7 positive control.
# ---------------------------------------------------------------------------


def test_t4_positive_control_fires():
    rc, out = _run_gate("--positive-control")
    assert rc == gate_mod.EXIT_OK
    assert "CONTROL FIRED" in out


def test_t4_positive_control_cannot_be_stranded_before_the_scan():
    # Exit 2 is a usage error: the control never reached the scan and certifies
    # nothing. The only rejected combination is passing paths alongside it, and
    # that arm must not be reachable from the documented invocation.
    rc, _ = _run_gate("--positive-control", "some/path.md")
    assert rc == gate_mod.EXIT_USAGE
    rc_doc, out_doc = _run_gate("--positive-control")
    assert rc_doc != gate_mod.EXIT_USAGE
    assert "CONTROL FIRED" in out_doc


# ---------------------------------------------------------------------------
# T5: the shipped fix.
# ---------------------------------------------------------------------------


def test_t5_exporter_no_longer_carries_the_dead_commit_cite():
    src = (REPO / "db" / "validation" / "export_lynceus.py").read_text(encoding="utf-8")
    assert "commit `6853780`" not in src


def test_t5_coverage_report_builder_takes_a_content_hash():
    src = (REPO / "db" / "validation" / "export_lynceus.py").read_text(encoding="utf-8")
    assert "matrix_sha256: str" in src
    assert "sha256 `{matrix_sha256}`" in src
