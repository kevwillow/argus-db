"""Mutation fixtures for `scripts/check_commit_cites.py` (MAC-704, MAC-710).

BRIEF_STANDARDS.md R9 requires the producing script to carry a structural guard and
that the guard be shown failing on an input it should reject. The script's own
`--selftest` is that demonstration; these tests pin it in CI so it cannot rot into
decoration, and add the negative cases that matter most.

The four that pay for themselves:

* **fence removal must poison.** If deleting a marker left the SHA exempt, the fence
  would be inert and the gate would be certifying whatever the last annotator felt
  like exempting.
* **the ledger pattern must be load-bearing.** `**Commit:** \\`sha\\`` is invisible to
  the filed selector. If `LEDGER_RE` regressed, the six repaired CP1–CP6 headers
  would read as clean because nothing looked at them.
* **a substring match must not resolve a subject** (MAC-710). `--fixed-strings --grep`
  matches anywhere in the whole message. Without the `%s` equality filter behind it, a
  truncated or reworded anchor resolves to whatever commit happens to mention it and a
  rotted handle reads as live — the false pass the arm exists to prevent.
* **an ambiguous subject must fail like a rotted one** (MAC-710). A subject naming two
  commits retrieves neither. Treating "found something" as success would license
  exactly the anchors that cannot do the one job a citation has.
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

    # MAC-763 emptied REPAIR_EXCLUSIONS -- both carved trees stopped shipping. These
    # two arms used to read the production dict, so an empty dict made the first
    # unfirable and the second vacuously true. They inject their own carve-out now, so
    # arm D keeps a real positive control no matter what the production config holds.
    STALE = {"synthetic/stale-carve-out/": "fixture: matches no path, by design"}

    def test_arm_d_fires_on_stale_carve_out(self):
        """A carve-out matching nothing narrows nothing while looking like it does."""
        failures = cc.assert_selector_covers_hits(
            [], {}, {"some/other/path.md"}, exclusions=self.STALE
        )
        assert any(f.startswith("D:") for f in failures)

    def test_arm_d_silent_when_carve_outs_all_match(self):
        live_paths = {p + "x.md" for p in self.STALE}
        failures = cc.assert_selector_covers_hits(
            [], {}, live_paths, exclusions=self.STALE
        )
        assert not any(f.startswith("D:") for f in failures)

    def test_arm_d_still_reads_production_config_by_default(self):
        """The injection point must not detach the guard from the real config."""
        failures = cc.assert_selector_covers_hits([], {}, {"some/other/path.md"})
        expected = [f"D: repair carve-out {p!r} matches no path in the full scope"
                    for p in cc.REPAIR_EXCLUSIONS]
        assert [f for f in failures if f.startswith("D:")] == expected

    def test_arm_a_tolerates_a_subject_only_line(self):
        """MAC-710 widened arm A. A ledger header citing a subject carries no sha, and
        before the widening all six repaired CP1-CP6 headers would have failed arm A."""
        line = "**Commit:** subject `whatever the wording is`"
        assert cc.extract(line) == []
        failures = cc.assert_selector_covers_hits([("x.md", 1, line)], {}, set())
        assert not any(f.startswith("A:") for f in failures)


def _tally():
    return cc._subject_tally()


def _a_unique_subject() -> str:
    return sorted(s for s, n in _tally().items() if n == 1)[0]


def _a_duplicate_subject() -> str:
    return sorted(s for s, n in _tally().items() if n > 1)[0]


class TestSubjectAnchors:
    """MAC-710 — the arm that did not exist while the ledger already depended on it."""

    def test_anchor_pattern_is_line_anchored(self):
        """Only a header is a citation. A line that merely discusses the form -- this
        file, the gate's own fixtures, the ledger's policy prose -- is not one."""
        assert cc.extract_subjects("**Commit:** subject `x`") == ["x"]
        assert cc.extract_subjects("    **Commit:** subject `x`") == []
        assert cc.extract_subjects("see **Commit:** subject `x` for the form") == []

    def test_unique_subject_classifies_unique(self):
        subject = _a_unique_subject()
        got = cc.classify_subjects([("x.md", 1, f"**Commit:** subject `{subject}`")])
        assert got[subject]["status"] == "unique"
        assert len(got[subject]["matches"]) == 1

    def test_zero_match_subject_classifies_rotted(self):
        subject = cc.ROTTED_SUBJECT_FIXTURE
        got = cc.classify_subjects([("x.md", 1, f"**Commit:** subject `{subject}`")])
        assert got[subject]["status"] == "rotted"
        assert got[subject]["matches"] == []

    def test_duplicate_subject_classifies_ambiguous(self):
        """A handle that resolves to a set is not a handle."""
        subject = _a_duplicate_subject()
        got = cc.classify_subjects([("x.md", 1, f"**Commit:** subject `{subject}`")])
        assert got[subject]["status"] == "ambiguous"
        assert len(got[subject]["matches"]) >= 2

    def test_substring_match_alone_does_not_resolve(self):
        """The equality filter is load-bearing, not belt-and-braces.

        A truncated anchor is still a substring of the real message, so
        `--fixed-strings --grep` finds the commit. Only `%s` equality rejects it. Drop
        that filter and every truncated or reworded anchor reads as live.
        """
        full = next(
            s for s in sorted(v for v, n in _tally().items() if n == 1) if len(s) > 24
        )
        truncated = full[:16]
        raw = subprocess.run(
            ["git", "log", "--all", "--format=%H", "--fixed-strings", "--grep", truncated],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.split()
        assert raw, "fixture is not a substring of any commit message; test proves nothing"
        assert cc.resolve_subject(full) != ()
        assert cc.resolve_subject(truncated) == ()

    def test_fence_exempts_a_quoted_subject(self):
        subject = cc.FENCED_SUBJECT_FIXTURE
        got = cc.classify_subjects(
            [("x.md", 1, f"**Commit:** subject `{subject}` ({cc.EXEMPLAR_MARKER})")]
        )
        assert got[subject]["status"] == "exemplar"

    def test_removing_the_fence_poisons_a_subject(self):
        """Same unanimity rule as the sha arm: one unfenced site re-arms the defect."""
        subject = cc.POISON_SUBJECT_FIXTURE
        got = cc.classify_subjects(
            [
                ("a.md", 1, f"**Commit:** subject `{subject}` ({cc.EXEMPLAR_MARKER})"),
                ("b.md", 1, f"**Commit:** subject `{subject}`"),
            ]
        )
        assert got[subject]["status"] == "rotted"

    def test_every_ledger_anchor_at_head_is_unique(self):
        """The acceptance condition itself, read off the live tree rather than asserted."""
        hits = cc.grep_lines()
        got = cc.classify_subjects(hits)
        assert got, "no subject anchors found; the selector lost the ledger"
        broken = {s: e["status"] for s, e in got.items() if e["status"] in cc.SUBJECT_BROKEN}
        assert broken == {}, broken


class TestLedgerHeaderGuard:
    """Arm E — the anti-vacuity guard. Without it, rewording the six headers into a form
    the subject pattern misses would drop the tally to zero and print PASS."""

    def test_arm_e_fires_on_a_header_with_no_handle(self):
        failures = cc.assert_selector_covers_hits(
            [], {}, {p + "x.md" for p in cc.REPAIR_EXCLUSIONS},
            headers=[("x.md", 1, "**Commit:** landed sometime last spring")],
        )
        assert any(f.startswith("E:") for f in failures)

    def test_arm_e_silent_on_each_accepted_form(self):
        paths = {p + "x.md" for p in cc.REPAIR_EXCLUSIONS}
        accepted = [
            "**Commit:** `b2a8dac` — `docs(bible): correction pass 5`",  # dead-cite exemplar
            "**Commit:** subject `docs(bible): correction pass 5`",
            f"**Commit:** landed at `{cc.SELF_REF_PLACEHOLDER}`",
            f"**Commit:** the form is illustrated here ({cc.EXEMPLAR_MARKER})",
        ]
        for line in accepted:
            failures = cc.assert_selector_covers_hits([], {}, paths, headers=[("x.md", 1, line)])
            assert not any(f.startswith("E:") for f in failures), line

    def test_arm_e_covers_every_header_at_head(self):
        """Non-vacuity: the arm has a real denominator in this repo, not zero rows."""
        headers = cc.ledger_header_lines()
        assert len(headers) >= 6, headers
        failures = cc.assert_selector_covers_hits(
            [], {}, {p + "x.md" for p in cc.REPAIR_EXCLUSIONS}, headers=headers
        )
        assert not any(f.startswith("E:") for f in failures), failures

    def test_arm_f_fires_on_unclassified_subject(self):
        rigged = {"s": {"subject": "s", "sites": [], "marked_sites": 0, "matches": [], "status": "?"}}
        failures = cc.assert_selector_covers_hits(
            [], {}, {p + "x.md" for p in cc.REPAIR_EXCLUSIONS}, by_subject=rigged
        )
        assert any(f.startswith("F:") for f in failures)


class TestCarveOutDisclosure:
    """MAC-710 deliverable 3 — a green gate must not read as full coverage."""

    def test_disclosure_names_every_carve_out_and_counts_what_it_holds(self):
        # Injected fixture, not the production config: MAC-763 emptied the real dict,
        # and a disclosure asserted against an empty config asserts nothing. The
        # invariant under test -- names every carve-out, counts what it holds, hides
        # what this scope does not report -- is unchanged.
        carved = {"synthetic/carved/": "fixture: ratified prose, not repairable in place"}
        hits = [
            ("synthetic/carved/doc.md", 1, "landed at commit `0aa89a0` per the ledger"),  # dead-cite exemplar
        ]
        disc = cc.carve_out_disclosure(hits, set(), exclusions=carved)
        assert [r["prefix"] for r in disc["carve_outs"]] == list(carved)
        assert disc["held"], "carve-outs hold nothing; the disclosure would be vacuous"
        # Nothing is reported in scope, so everything held is hidden from it.
        assert disc["hidden_from_this_scope"] == disc["held"]

    def test_disclosure_matches_production_config(self):
        """Default path still reflects the real config, empty or not."""
        disc = cc.carve_out_disclosure(cc.grep_lines(), set())
        assert [r["prefix"] for r in disc["carve_outs"]] == list(cc.REPAIR_EXCLUSIONS)

    def test_hidden_shrinks_when_the_scope_already_reports_it(self):
        """`hidden` is a set difference against what this scope shows, not a constant."""
        hits = cc.grep_lines()
        held = cc.carve_out_disclosure(hits, set())["held"]
        disc = cc.carve_out_disclosure(hits, set(held))
        assert disc["held"] == held
        assert disc["hidden_from_this_scope"] == []

    def test_both_scopes_print_the_carve_outs(self):
        for scope in ("repair", "full"):
            proc = subprocess.run(
                [sys.executable, "scripts/check_commit_cites.py", "--scope", scope],
                cwd=REPO, capture_output=True, text=True,
            )
            out = proc.stdout
            assert "repair-scope carve-outs:" in out, out
            for prefix in cc.REPAIR_EXCLUSIONS:
                assert f"carve-out  {prefix}" in out, (scope, prefix)
