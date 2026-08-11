"""Mutation fixtures for `scripts/check_commit_cites.py` (MAC-704).

BRIEF_STANDARDS.md R9 requires the producing script to carry a structural guard and
that the guard be shown failing on an input it should reject. The script's own
`--selftest` is that demonstration; these tests pin it in CI so it cannot rot into
decoration, and add the negative cases that matter most.

The two that pay for themselves:

* **fence removal must poison.** If deleting a marker left the SHA exempt, the fence
  would be inert and the gate would be certifying whatever the last annotator felt
  like exempting.
* **the ledger pattern must be load-bearing.** `**Commit:** \\`sha\\`` is invisible to
  the filed selector. If `LEDGER_RE` regressed, the six repaired CP1–CP6 headers
  would read as clean because nothing looked at them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import check_commit_cites as cc  # noqa: E402


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout.strip()


class TestSelfTest:
    def test_selftest_exits_zero(self):
        """The R7 positive control must fire on every arm."""
        proc = subprocess.run(
            [sys.executable, "scripts/check_commit_cites.py", "--selftest"],
            cwd=REPO, capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "selftest PASS" in proc.stdout


class TestClassification:
    def test_live_sha_classifies_live(self):
        got = cc.classify([("x.md", 1, f"landed at commit `{_head()}`")])
        assert got[_head()]["status"] == "live"

    def test_dead_sha_classifies_dead(self):
        got = cc.classify([("x.md", 1, "landed at commit `0aa89a0`")])  # dead-cite exemplar
        assert got["0aa89a0"]["status"] == "dead"

    def test_foreign_marker_exempts(self):
        got = cc.classify(
            [("x.md", 1, f"pinned commit `d2468ad` ({cc.FOREIGN_MARKER})")]  # dead-cite exemplar
        )
        assert got["d2468ad"]["status"] == "foreign"

    def test_exemplar_marker_exempts(self):
        got = cc.classify(
            [("x.md", 1, f"quoted commit `0aa89a0` ({cc.EXEMPLAR_MARKER})")]  # dead-cite exemplar
        )
        assert got["0aa89a0"]["status"] == "exemplar"

    def test_removing_the_fence_poisons(self):
        """Arm B of the fence rule: an unfenced line must re-arm the defect."""
        got = cc.classify([("x.md", 1, "quoted commit `0aa89a0` with no marker")])  # dead-cite exemplar
        assert got["0aa89a0"]["status"] == "dead"

    def test_exemption_requires_unanimity(self):
        """One undeclared argus-context cite outvotes any number of fenced ones."""
        got = cc.classify(
            [
                ("a.md", 1, f"quoted commit `0aa89a0` ({cc.EXEMPLAR_MARKER})"),  # dead-cite exemplar
                ("b.md", 1, f"quoted commit `0aa89a0` ({cc.EXEMPLAR_MARKER})"),  # dead-cite exemplar
                ("c.md", 1, "landed at commit `0aa89a0`"),  # dead-cite exemplar
            ]
        )
        assert got["0aa89a0"]["status"] == "dead"

    def test_marker_does_not_reach_across_lines(self):
        """A fence is same-line only; otherwise its blast radius is unbounded."""
        got = cc.classify(
            [
                ("x.md", 1, "landed at commit `0aa89a0`"),  # dead-cite exemplar
                ("x.md", 2, f"...which is a {cc.EXEMPLAR_MARKER}"),
            ]
        )
        assert got["0aa89a0"]["status"] == "dead"


class TestLedgerPattern:
    def test_ledger_header_is_seen(self):
        """`**Commit:** <sha>` is invisible to the filed pattern by construction."""
        line = "**Commit:** `b2a8dac` — `docs(bible): correction pass 5`"  # dead-cite exemplar
        assert cc.FILED_RE.findall(line) == []
        assert cc.LEDGER_RE.findall(line) == ["b2a8dac"]
        assert cc.extract(line) == ["b2a8dac"]

    def test_bare_hex_is_not_a_cite(self):
        """BLE UUIDs and record ids must never be swept in."""
        assert cc.extract("service uuid `0000fc6d` and id 419374de3affb62b") == []


class TestStructuralGuard:
    def test_guard_is_clean_on_wellformed_input(self):
        hits = [("x.md", 1, "landed at commit `0aa89a0`")]  # dead-cite exemplar
        by_sha = cc.classify(hits)
        # Arm D reads the FULL path set, so a well-formed call has to supply one in
        # which every carve-out still matches something.
        paths = {"x.md", *(p + "x.md" for p in cc.REPAIR_EXCLUSIONS)}
        assert cc.assert_selector_covers_hits(hits, by_sha, paths) == []

    def test_arm_a_fires_when_extraction_yields_nothing(self):
        failures = cc.assert_selector_covers_hits(
            [("x.md", 1, "no cite token here")], {}, set()
        )
        assert any(f.startswith("A:") for f in failures)

    def test_arm_b_fires_on_unclassified_sha(self):
        bogus = {"z": {"sha": "z", "sites": [], "marked": {k: 0 for k in cc.MARKERS}, "marked_sites": 0, "status": "?"}}
        failures = cc.assert_selector_covers_hits([], bogus, set())
        assert any(f.startswith("B:") for f in failures)

    def test_arm_c_fires_on_non_unanimous_exemption(self):
        rigged = {
            "z": {
                "sha": "z",
                "sites": [{"path": "a", "line": 1, "text": ""}, {"path": "b", "line": 1, "text": ""}],
                "marked": {"foreign": 1, "exemplar": 0},
                "marked_sites": 1,
                "status": "foreign",
            }
        }
        failures = cc.assert_selector_covers_hits([], rigged, {"a"})
        assert any(f.startswith("C:") for f in failures)

    def test_arm_d_fires_on_stale_carve_out(self):
        """A carve-out matching nothing narrows nothing while looking like it does."""
        failures = cc.assert_selector_covers_hits([], {}, {"some/other/path.md"})
        assert any(f.startswith("D:") for f in failures)

    def test_arm_d_silent_when_carve_outs_all_match(self):
        live_paths = {p + "x.md" for p in cc.REPAIR_EXCLUSIONS}
        failures = cc.assert_selector_covers_hits([], {}, live_paths)
        assert not any(f.startswith("D:") for f in failures)
