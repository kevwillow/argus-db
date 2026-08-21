"""MAC-779 -- proof fixtures for ``scripts/check_section_anchors.py``.

The gate resolves a ``§N`` citation against a real heading inventory. Nothing in
``scripts/`` did that before: ``check_doc_anchors.py --coverage`` lists
"section (§N) anchors, cross-references, headings, links" under NOT COVERED, and
the instrument that could do it (``operator_review/MAC-773/anchor_resolve.py``)
was untracked by ``2864473`` and is absent from a fresh clone.

Per R9 a gate is decoration until it is shown failing on an input it should
reject, and per R7 a green result is not evidence the gate works. Every arm here
carries the control that makes its verdict non-vacuous.

Argument defended in this file:

  T1  coverage contract:  the registry IS the advertised scope. ``--coverage``
      names every resolved-against document and every known hole, the advertised
      scope equals the scanned scope, and no dead doc-path constant may grow
      back (the MAC-777 defect, reproduced here with its own positive control).
      T1 also pins the property that makes the three registered documents safe
      to resolve against -- unique section numbers -- and the property that
      disqualifies BIBLE_AMENDMENTS -- numbering that restarts every pass.

  T2  heading inventory, BOTH syntaxes:  the bible numbers headings WITHOUT the
      sigil (``## 4. Data Schema``); DATA_DICTIONARY and METHODOLOGY number
      theirs WITH it (``## §4. Tables``). A one-syntax regex would silently
      read an empty inventory for two of the three documents and then resolve
      nothing -- so T2 pins a live heading of each shape AND proves the
      sigil-less regex genuinely loses the other two.

  T3  attribution:  which document a ``§N`` belongs to. Conservative by design --
      a false attribution makes this gate a generator of fake findings. Each arm
      is drawn from a real line in the tree: the barrier case, the
      case-sensitivity case, the line-cite case, and the no-self-resolution case.

  T4  end-to-end positive control (scope item 3):  delete a cited heading from a
      scratch copy of the REAL document and require the gate to go red AT THAT
      CITE -- once per resolved-against document, so none of the three is
      decoration. Plus the absence control: a registered document that cannot be
      read must exit 2, never 0. A gate whose target is deleted must not go
      green -- ``2864473`` untracked this gate's ancestor and that is precisely
      how the instrument went missing in the first place.

  T5  live-tree baseline:  the unresolved set at HEAD, pinned by (file, section)
      rather than by line number, because CHANGELOG.md is a hot file and a line
      pin slides off it. Findings are expected; the pin is what makes a NEW one
      visible.
"""
from __future__ import annotations

import ast
import collections
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "check_section_anchors.py"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("check_section_anchors", GATE)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("check_section_anchors", module)
    spec.loader.exec_module(module)
    return module


gate = _load_gate_module()


# ---------------------------------------------------------------------------
# T1: the coverage contract.
# ---------------------------------------------------------------------------


def test_t1_every_registered_document_exists_in_the_tree():
    """A registry naming a path that is not there is a coverage claim with
    nothing behind it."""
    for doc in gate.DOCUMENTS:
        assert (REPO / doc.path).is_file(), f"registered but absent: {doc.path}"


def test_t1_coverage_report_names_every_resolved_against_document():
    report = gate.format_coverage_report()
    for doc in gate.DOCUMENTS:
        assert doc.path in report, f"{doc.path} missing from --coverage"
        assert doc.why in report


def test_t1_coverage_report_states_what_is_not_covered():
    """Scope item 2: the file must STATE which inventories it does not resolve
    against, and the rc must not read as broader than the check."""
    report = gate.format_coverage_report()
    assert "NOT COVERED" in report
    assert "NOT AN INVENTORY" in report
    for path, _why in gate.NOT_AN_INVENTORY:
        assert path in report, f"{path} not declared as a non-inventory"
    # The named holes, each of which a reader could otherwise assume is checked.
    assert "UNATTRIBUTED" in report
    assert "non-numeric" in report
    assert "line anchors" in report
    for prefix in gate.EXCLUDED_PREFIXES:
        assert prefix in report


def test_t1_bible_amendments_is_declared_a_non_inventory_not_silently_omitted():
    """Omitting it silently would leave a reader unable to tell "decided
    against" from "forgotten" -- so the registry must declare it AND the stated
    reason must be true.

    The reason is NOT "it has no §N headings". It has plenty. They are
    per-Correction-Pass LOCAL numbering that restarts in every pass, so the same
    section number is declared by many different headings and resolving a cite
    against that inventory would be meaningless. This arm pins the
    non-uniqueness, because that is the load-bearing half of the claim.
    """
    rel = "docs/engineering/BIBLE_AMENDMENTS.md"
    assert rel in {path for path, _ in gate.NOT_AN_INVENTORY}
    assert rel not in {d.path for d in gate.DOCUMENTS}

    text = (REPO / rel).read_text(encoding="utf-8")
    declared = collections.Counter()
    for line in text.split("\n"):
        for section in gate.heading_inventory(line):
            declared[section] += 1
    repeated = {s: n for s, n in declared.items() if n > 1}
    assert repeated, (
        "BIBLE_AMENDMENTS.md's section numbers are now unique, so the "
        "registry's stated reason for excluding it as an inventory is false"
    )
    assert declared["1"] > 1, declared


def test_t1_the_resolved_against_documents_have_UNIQUE_section_numbers():
    """The complement of the arm above, and the reason the three registered
    documents are safe to resolve against at all: in each of them a section
    number is declared exactly once, so a cite has one referent."""
    for doc in gate.DOCUMENTS:
        declared = collections.Counter()
        for line in (REPO / doc.path).read_text(encoding="utf-8").split("\n"):
            for section in gate.heading_inventory(line):
                declared[section] += 1
        dupes = {s: n for s, n in declared.items() if n > 1}
        assert not dupes, f"{doc.path} declares {dupes} more than once"


def test_t1_advertised_scope_equals_scanned_scope():
    """`resolved_against()` must be the surface, not a claim about the surface."""
    assert gate.resolved_against() == tuple(d.path for d in gate.DOCUMENTS)
    for path in gate.resolved_against():
        assert path in gate.coverage_line()


def test_t1_coverage_mode_runs_no_checks_and_needs_no_tree(tmp_path):
    """`--coverage` answers "what does this cover" without scanning anything."""
    assert gate.main(["--coverage", "--root", str(tmp_path)]) == 0


def _dead_doc_path_constants(source: str) -> dict:
    """Module-level tuples/lists of ``.md`` paths that nothing ever reads.

    Lifted from ``tests/test_check_doc_anchors.py``. ``TIER_1`` was one for its
    whole life and made ``check_doc_anchors.py`` read as the bible's instrument
    when it never opened the file.
    """
    tree = ast.parse(source)
    suspects: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
            node.targets[0], ast.Name
        ):
            name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
            name, value = node.target.id, node.value
        else:
            continue
        if not isinstance(value, (ast.Tuple, ast.List)) or not value.elts:
            continue
        strings = [e.value for e in value.elts
                   if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        if len(strings) == len(value.elts) and any(s.endswith(".md") for s in strings):
            suspects[name] = node.lineno
    loads = collections.Counter(
        n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    )
    return {n: ln for n, ln in suspects.items() if loads[n] == 0}


def test_t1_dead_constant_detector_goes_red_on_a_real_one():
    """Positive control (R7): the guard below is green on an empty set, so it is
    worthless unless this arm shows it red on a genuine dead constant."""
    dead = _dead_doc_path_constants(
        'TIER_1 = (\n    "README.md",\n    "docs/engineering/PROJECT_BIBLE.md",\n)\n'
        'LIVE = ("CHANGELOG.md",)\nprint(LIVE)\n'
    )
    assert dead == {"TIER_1": 1}, dead


def test_t1_no_dead_doc_path_constant_in_this_gate():
    """MAC-777: a doc-path list nothing reads is a false coverage signal."""
    dead = _dead_doc_path_constants(GATE.read_text(encoding="utf-8"))
    assert not dead, f"unreferenced doc-path constant(s) {dead} -- wire it or delete it"


# ---------------------------------------------------------------------------
# T2: heading inventory -- both numbering syntaxes.
# ---------------------------------------------------------------------------


# One live heading of each shape, pasted from the tree.
_HEADING_FIXTURES = [
    # PROJECT_BIBLE.md numbers WITHOUT the sigil.
    ("## 4. Data Schema", "4"),
    ("### 4.1 Main table: `identifiers`", "4.1"),
    ("## 0. How to Read This Document", "0"),
    ("### 8.3 Dedup logic", "8.3"),
    # DATA_DICTIONARY.md / METHODOLOGY.md number WITH the sigil.
    ("## §4. Tables", "4"),
    ("### §4.1. `identifiers` (Layer 1 canonical)", "4.1"),
    ("### §3.4.1 Live row counts", "3.4.1"),
    ("## §5. Confidence model", "5"),
    ("### §5.5 Export thresholds", "5.5"),
]


@pytest.mark.parametrize("line, expected", _HEADING_FIXTURES)
def test_t2_heading_regex_accepts_both_numbering_syntaxes(line, expected):
    assert gate.heading_inventory(line) == {expected}


@pytest.mark.parametrize(
    "line",
    [
        "# Argus: Surveillance Identifier Intelligence Database",  # h1, unnumbered
        "## TL;DR",
        "#### Columns",
        "### Tier 1: Structured (highest priority, machine-readable)",
        "### Phase 0: Bootstrap",
        "not a heading at all, mentions §4.4",
        "## §-procurement_records",  # slug section, not numbered
    ],
)
def test_t2_heading_regex_rejects_unnumbered_and_non_headings(line):
    assert gate.heading_inventory(line) == set()


def test_t2_live_inventories_are_all_non_empty():
    """An empty inventory would make every cite to that document UNRESOLVED --
    a gate failing loudly rather than silently, but still a broken gate."""
    for doc in gate.DOCUMENTS:
        inv = gate.heading_inventory((REPO / doc.path).read_text(encoding="utf-8"))
        assert len(inv) >= 10, f"{doc.path} inventory is {len(inv)} headings: {inv}"


def test_t2_a_sigil_less_regex_genuinely_loses_two_of_the_three_documents():
    """Proves the dual syntax is load-bearing, not a defensive flourish.

    Without this arm, T2's fixtures could pass against a regex that happened to
    be over-permissive, and no one would know whether the `§` alternative was
    doing anything.
    """
    sigil_less = re.compile(r"^\s{0,3}(#{2,6})\s+(\d+(?:\.\d+)*)\.?(?:\s|$)")

    def naive(text: str) -> set[str]:
        return {m.group(2) for line in text.split("\n") if (m := sigil_less.match(line))}

    by_key = {d.key: d for d in gate.DOCUMENTS}
    bible_text = (REPO / by_key["PROJECT_BIBLE"].path).read_text(encoding="utf-8")
    assert naive(bible_text) == gate.heading_inventory(bible_text), (
        "the bible's headings carry no sigil, so both regexes must agree on it"
    )
    for key in ("DATA_DICTIONARY", "METHODOLOGY"):
        text = (REPO / by_key[key].path).read_text(encoding="utf-8")
        assert naive(text) == set(), f"{key} unexpectedly has sigil-less headings"
        assert len(gate.heading_inventory(text)) >= 10, key


# ---------------------------------------------------------------------------
# T3: attribution. Every arm is a real line, or a minimal reduction of one.
# ---------------------------------------------------------------------------


_ATTRIBUTION_FIXTURES = [
    # (line, expected doc key for the FIRST § on the line, note)
    (
        "4. Read [DATA_DICTIONARY.md §6.2](DATA_DICTIONARY.md) (confidence-shape divergence)",
        "DATA_DICTIONARY",
        "filename form, immediately before the sigil",
    ),
    (
        "3. Read [METHODOLOGY.md §5](METHODOLOGY.md) (confidence model) before threshold-filtering",
        "METHODOLOGY",
        "filename form",
    ),
    (
        "eligible for Lynceus export (subject to confidence >=85 per METHODOLOGY §5).",
        "METHODOLOGY",
        "bare uppercase name",
    ),
    (
        "Sibling commits to PROJECT_BIBLE §4 (notes_json conventions block)",
        "PROJECT_BIBLE",
        "PROJECT_BIBLE without the extension",
    ),
    (
        "per bible §11 #14, analytical-only rows are never exported",
        "PROJECT_BIBLE",
        "the lowercase word `bible` is unambiguous in this corpus",
    ),
    (
        "hub-and-spoke is not the §8.3 of the bible",
        "PROJECT_BIBLE",
        "trailing `of the <doc>` form",
    ),
]


@pytest.mark.parametrize(
    "line, expected, note",
    _ATTRIBUTION_FIXTURES,
    ids=[n for _, _, n in _ATTRIBUTION_FIXTURES],
)
def test_t3_attributes_a_named_document(line, expected, note):
    m = gate.CITE_RE.search(line)
    assert m, line
    assert gate.attribute(line, m.start()) == expected


def test_t3_lowercase_methodology_the_noun_does_not_attribute():
    """The case-sensitivity arm, from a real line.

    ``docs/engineering/BIBLE_AMENDMENTS.md:4050``::

        1. **Wave I.13 DOUBLE-FALSIFICATION methodology** already established
           all 73 as DROP-default per dispatch §11.2 (sub-pass 41+42 ...)

    ``methodology`` is the English noun and ``§11.2`` belongs to a dispatch. If
    METHODOLOGY were matched case-insensitively this line would generate a
    finding against a document it never cited.
    """
    line = (
        "1. **Wave I.13 DOUBLE-FALSIFICATION methodology** already established "
        "all 73 as DROP-default per dispatch §11.2 (sub-pass 41+42 + sub-pass 44)."
    )
    m = gate.CITE_RE.search(line)
    assert gate.attribute(line, m.start()) is None


def test_t3_a_barrier_token_breaks_attribution():
    """Same line shape, but with the document genuinely named. The barrier, not
    the case rule, is what must stop it -- so this arm uses the uppercase form."""
    line = "METHODOLOGY defines the bands, but per dispatch §11.2 the wave used DROP-default"
    m = gate.CITE_RE.search(line)
    assert gate.attribute(line, m.start()) is None, (
        "a `dispatch` between the document name and the sigil re-scopes the cite"
    )


def test_t3_barrier_positive_control_same_line_without_the_barrier():
    """R7: the barrier arm above is an assertion that something is None, which a
    totally broken `attribute()` would also satisfy. This is its control."""
    line = "METHODOLOGY defines the bands, and per §11.2 the wave used DROP-default"
    m = gate.CITE_RE.search(line)
    assert gate.attribute(line, m.start()) == "METHODOLOGY"


def test_t3_a_runguide_section_is_not_a_bible_section():
    """``CHANGELOG.md:1176``, the false positive this gate must NOT reproduce.

        ... a new bible subsection requiring every runguide to ship a `§3.0`
        verification-probe section that completes CLEAN POSITIVE ...

    ``§3.0`` is a section of a RUNGUIDE. The untracked MAC-773 instrument
    attributed it to the bible -- "bible" is 60-odd characters earlier on the
    line -- and reported it as one of its four findings. It is not a finding.
    """
    line = (
        "**`Correction Pass 27`, `§2.4 Empirical-Premise Verification "
        "Precondition`**: a new bible subsection requiring every runguide to "
        "ship a `§3.0` verification-probe section that completes CLEAN POSITIVE"
    )
    hits = list(gate.CITE_RE.finditer(line))
    section_30 = next(m for m in hits if m.group(1) == "3.0")
    assert gate.attribute(line, section_30.start()) is None


def test_t3_an_issue_identifier_rescopes_the_cite():
    """``db/validation/export_lynceus.py:156``::

        # (PROJECT_BIBLE.md:279, board e246a32a, MAC-101 §2.5). Un-held at MAC-360

    ``§2.5`` is scoped to MAC-101's brief. Before the ``MAC-\\d+`` barrier and the
    line-cite rule this produced a finding against a cite that was never a bible
    section cite -- it was the second of MAC-773's four.
    """
    line = "# (PROJECT_BIBLE.md:279, board e246a32a, MAC-101 §2.5). Un-held at MAC-360 /"
    m = gate.CITE_RE.search(line)
    assert gate.attribute(line, m.start()) is None


def test_t3_a_line_cite_does_not_scope_a_later_section_cite():
    """`PROJECT_BIBLE.md:279` cites a LINE. It is a different citation form and
    must not bind a `§N` later on the same line."""
    line = "see PROJECT_BIBLE.md:279 and also §4.4 elsewhere"
    m = gate.CITE_RE.search(line)
    assert gate.attribute(line, m.start()) is None


def test_t3_line_cite_positive_control_without_the_line_suffix():
    """R7 control for the arm above: drop `:279` and the same line attributes."""
    line = "see PROJECT_BIBLE.md and also §4.4 elsewhere"
    m = gate.CITE_RE.search(line)
    assert gate.attribute(line, m.start()) == "PROJECT_BIBLE"


def test_t3_no_self_resolution_inside_a_registered_document():
    """A bare ``§N`` does NOT mean "this document's §N", even inside one.

    ``docs/engineering/DATA_DICTIONARY.md:84``::

        | `procurement_records` | **50,492** | analytical-only (never exported
          to Lynceus per §11 #14); ...

    That ``§11`` is the BIBLE's §11 (Critical Don'ts), not DATA_DICTIONARY's.
    Self-resolution was implemented first and produced 125 unresolved cites,
    almost all of them this false attribution; removing it left 9.
    """
    line = "| `procurement_records` | analytical-only (never exported to Lynceus per §11 #14)"
    m = gate.CITE_RE.search(line)
    assert gate.attribute(line, m.start()) is None


def test_t3_a_distant_document_name_does_not_reach_the_cite():
    """The lookback window is bounded, so a name at the far end of a long prose
    line cannot drag an unrelated § into its inventory."""
    line = "PROJECT_BIBLE.md " + ("filler word " * 12) + "§4.4"
    m = gate.CITE_RE.search(line)
    assert len(line) - m.start() < 200  # sanity: the fixture is the shape we think
    assert gate.attribute(line, m.start()) is None


def test_t3_nearest_name_wins_when_two_documents_share_a_line():
    line = "PROJECT_BIBLE.md restates what METHODOLOGY §5 already says"
    m = gate.CITE_RE.search(line)
    assert gate.attribute(line, m.start()) == "METHODOLOGY"


def test_t3_non_numeric_section_tokens_are_not_cites():
    """``DATA_DICTIONARY.md §-procurement_records`` names a section by slug.
    It must not parse as a numeric cite, and it must be counted as a known hole."""
    line = "-- also documented in DATA_DICTIONARY.md §-procurement_records."
    assert gate.CITE_RE.search(line) is None
    assert gate.NON_NUMERIC_RE.search(line) is not None


def test_t3_every_barrier_token_is_load_bearing():
    """A barrier that prevents no false finding is coverage thrown away.

    Each token must, when removed, either widen attribution onto a cite that
    does NOT resolve (a false finding it was preventing) or change nothing at
    all -- in which case it does not belong. `correction pass` was dropped on
    exactly this measurement: +7 cites attributed, 0 new findings.
    """
    pattern = gate.BARRIER_RE.pattern
    assert "correction" not in pattern, (
        "`correction pass` was measured to buy nothing (+7 attributed, 0 new "
        "findings) and was removed; re-adding it needs a fresh measurement"
    )
    for token in ("dispatch", "runguide", "MAC-", "brief"):
        assert token in pattern, f"barrier token {token!r} went missing"


# ---------------------------------------------------------------------------
# T4: end-to-end, against scratch copies of the REAL documents.
# ---------------------------------------------------------------------------


# (document key, a section that document really has, the citing line to plant)
_CONTROL_CITES = {
    "PROJECT_BIBLE": ("8.3", "-- dedup logic per PROJECT_BIBLE.md §8.3 applies here"),
    "DATA_DICTIONARY": ("4.3", "-- vocabulary per DATA_DICTIONARY.md §4.3 applies here"),
    "METHODOLOGY": ("5.5", "-- export shapes per METHODOLOGY.md §5.5 applies here"),
}

# The bible states the CP24 citation-hygiene rule by QUOTING the miscite it
# bans, so the real file carries two unresolved §5.2 cites of its own (T5 pins
# them). The scratch tree drops that one line so a perturbation's effect is
# unambiguous -- otherwise every arm below would have to subtract a constant.
_PREEXISTING_FINDING_MARKER = '"§5.2 +5 boost" is a miscite'


def _scratch_tree(tmp_path: Path) -> Path:
    """The three real documents plus one synthetic citing file.

    Real documents, not synthetic ones, so the controls exercise real headings.
    The citing file is synthetic so the controls are not entangled with the
    tree's own findings (which T5 pins separately).
    """
    work = tmp_path / "tree"
    stripped = 0
    for doc in gate.DOCUMENTS:
        dst = work / doc.path
        dst.parent.mkdir(parents=True, exist_ok=True)
        lines = (REPO / doc.path).read_text(encoding="utf-8").split("\n")
        kept = [ln for ln in lines if _PREEXISTING_FINDING_MARKER not in ln]
        stripped += len(lines) - len(kept)
        dst.write_text("\n".join(kept), encoding="utf-8")
    # Non-vacuous: if the marker stops matching, the strip becomes a no-op and
    # the negative control below would fail confusingly instead of here.
    assert stripped == 1, (
        f"expected to strip exactly one pre-existing-finding line, stripped "
        f"{stripped}; update _PREEXISTING_FINDING_MARKER"
    )
    cites = work / "CITES.md"
    cites.write_text(
        "# citing file\n\n"
        + "\n".join(line for _sec, line in _CONTROL_CITES.values())
        + "\n",
        encoding="utf-8",
    )
    return work


def _run(work: Path, *extra: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(GATE), "--root", str(work), *extra],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_t4_negative_control_unperturbed_scratch_tree_is_green(tmp_path):
    """So a red arm below means the perturbation, not the scratch tree."""
    rc, out, err = _run(_scratch_tree(tmp_path))
    assert rc == 0, f"stdout={out}\nstderr={err}"
    assert "UNRESOLVED: 0" in out, out


def test_t4_negative_control_is_not_green_because_nothing_was_checked(tmp_path):
    """The green above must come from resolving cites, not from finding none.

    The scratch tree carries more than the three planted cites: the real
    documents cite each other and themselves. What matters is that every
    resolved-against document has cites attributed to it and none is a
    registered path with nothing behind it.
    """
    rc, out, _ = _run(_scratch_tree(tmp_path))
    assert rc == 0
    assert "UNRESOLVED: 0" in out, out
    for doc in gate.DOCUMENTS:
        m = re.search(
            rf"{re.escape(doc.path)}: \d+ numbered headings, (\d+) cite", out
        )
        assert m, out
        assert int(m.group(1)) > 0, f"no cite attributed to {doc.path}\n{out}"


@pytest.mark.parametrize("key", sorted(_CONTROL_CITES))
def test_t4_deleting_a_cited_heading_turns_the_gate_red_at_that_cite(key, tmp_path):
    """Scope item 3, the R9 arm -- once per resolved-against document.

    Delete the heading a planted cite points at, and the gate must name that
    cite. Parametrised so DATA_DICTIONARY and METHODOLOGY are genuinely wired
    and not carried by the bible.
    """
    work = _scratch_tree(tmp_path)
    doc = next(d for d in gate.DOCUMENTS if d.key == key)
    section, _line = _CONTROL_CITES[key]

    path = work / doc.path
    lines = path.read_text(encoding="utf-8").split("\n")
    kept = [ln for ln in lines if gate.heading_inventory(ln) != {section}]
    assert len(kept) == len(lines) - 1, (
        f"expected exactly one heading line for §{section} in {doc.path}; "
        f"removed {len(lines) - len(kept)}"
    )
    path.write_text("\n".join(kept), encoding="utf-8")

    rc, out, err = _run(work)
    assert rc == 1, f"gate stayed green after deleting §{section} from {doc.path}\n{out}\n{err}"
    assert f"UNRESOLVED §{section} -> {doc.path}" in out, out
    assert "CITES.md" in out, out


def test_t4_deleting_an_UNcited_heading_does_not_turn_the_gate_red(tmp_path):
    """The complement of the arm above. Without it, "red after deletion" could
    come from a gate that reddens on any edit at all."""
    work = _scratch_tree(tmp_path)
    doc = next(d for d in gate.DOCUMENTS if d.key == "PROJECT_BIBLE")
    path = work / doc.path
    lines = path.read_text(encoding="utf-8").split("\n")
    cited = {sec for sec, _ in _CONTROL_CITES.values()}
    victim = next(
        ln for ln in lines
        if (inv := gate.heading_inventory(ln)) and not (inv & cited)
    )
    path.write_text("\n".join(ln for ln in lines if ln != victim), encoding="utf-8")

    rc, out, _ = _run(work)
    assert rc == 0, f"deleting the uncited heading {victim!r} reddened the gate\n{out}"


def test_t4_a_missing_registered_document_exits_2_not_0(tmp_path):
    """The absence control.

    ``2864473`` untracked ``operator_review/`` and with it this gate's ancestor;
    the general shape is that a gate reading a path that is no longer there
    returns an empty finding list and goes silently green. Here it must exit 2.
    """
    work = _scratch_tree(tmp_path)
    (work / gate.DOCUMENTS[0].path).unlink()
    rc, out, err = _run(work)
    assert rc == 2, f"rc={rc}\n{out}\n{err}"
    assert gate.DOCUMENTS[0].path in err
    assert "Traceback" not in err


def test_t4_an_empty_registered_document_exits_1_with_findings(tmp_path):
    """Gutted rather than deleted: readable, but with no inventory at all. Every
    cite to it must go UNRESOLVED rather than vacuously pass."""
    work = _scratch_tree(tmp_path)
    doc = gate.DOCUMENTS[0]
    (work / doc.path).write_text("# gutted\n", encoding="utf-8")
    rc, out, _ = _run(work)
    assert rc == 1, out
    section, _ = _CONTROL_CITES[doc.key]
    assert f"UNRESOLVED §{section} -> {doc.path}" in out, out


def test_t4_list_mode_reports_resolved_cites_too(tmp_path):
    rc, out, _ = _run(_scratch_tree(tmp_path), "--list")
    assert rc == 0
    for key, (section, _line) in _CONTROL_CITES.items():
        assert re.search(rf"OK\s+§{re.escape(section)}\s+{key}\b", out), (out, key)


def test_t4_gate_works_without_a_git_directory(tmp_path):
    """A `git archive` cleanroom has no `.git`. A gate that enumerates its scan
    targets with `git ls-files` and does not fall back would see an empty file
    list there and go VACUOUSLY green."""
    work = _scratch_tree(tmp_path)
    assert not (work / ".git").exists()
    rc, out, _ = _run(work)
    assert rc == 0
    m = re.search(r"numeric §N cites found: (\d+)", out)
    assert m and int(m.group(1)) > 100, out


# ---------------------------------------------------------------------------
# T5: the live-tree baseline.
# ---------------------------------------------------------------------------


# Pinned by (file, section) and NOT by line number: CHANGELOG.md is a hot file
# and a line pin slides off it. Counts are multiplicities -- a line carrying the
# same unresolved cite twice counts twice.
#
# Baseline taken at HEAD 1903c24. Each entry is a real finding, not an
# exemption: the gate exits 1 on this tree and is meant to.
_BASELINE_UNRESOLVED = {
    # `bible §179` is a LINE number wearing a section sigil. PROJECT_BIBLE.md
    # line 179 is the SSID normalization rule, which lives in §4.3.
    ("CHANGELOG.md", "179"): 1,
    ("scripts/fp_magnet_verify.py", "179"): 1,
    # The CP24 citation-hygiene rule, which says in so many words that §5.2 is a
    # miscite and the bible has no §5.2. The gate rediscovers the board's own
    # ratified finding from the heading inventory alone.
    ("docs/engineering/BIBLE_AMENDMENTS.md", "5.2"): 3,
    ("docs/engineering/PROJECT_BIBLE.md", "5.2"): 2,
}


def _live_unresolved() -> collections.Counter:
    tree = gate.Tree(REPO)
    cites, inventories, _non_numeric, missing = gate.scan(tree)
    assert not missing, missing
    return collections.Counter(
        (u.cite.file, u.cite.section) for u in gate.unresolved(cites, inventories)
    )


def test_t5_live_unresolved_set_matches_the_pinned_baseline():
    """A NEW unresolved cite must be visible immediately.

    This is expected to fail once MAC-773 lands -- it moves bible headings, and
    a baseline taken before it does not survive it. That failure is the
    sequencing constraint made mechanical, not a flaky test: re-derive the
    baseline at the new HEAD and record why each entry moved.
    """
    live = _live_unresolved()
    expected = collections.Counter(_BASELINE_UNRESOLVED)
    assert live == expected, (
        f"unresolved set moved.\n"
        f"  new:  {sorted((live - expected).elements())}\n"
        f"  gone: {sorted((expected - live).elements())}"
    )


def test_t5_the_live_tree_check_is_not_vacuous():
    """R7. The baseline arm asserts an equality that would also hold if the
    scanner silently found nothing. This arm proves it is scanning a real
    corpus and resolving the overwhelming majority of it."""
    tree = gate.Tree(REPO)
    cites, inventories, non_numeric, missing = gate.scan(tree)
    assert not missing
    attributed = [c for c in cites if c.doc_key is not None]
    assert len(attributed) >= 500, f"only {len(attributed)} attributed cites"
    assert len(cites) >= 5000, f"only {len(cites)} numeric §N cites seen"
    assert non_numeric > 0
    # Every resolved-against document must actually carry attributed cites, or
    # it is registered scope with nothing behind it.
    per_doc = collections.Counter(c.doc_key for c in attributed)
    for doc in gate.DOCUMENTS:
        assert per_doc[doc.key] > 0, f"no cite attributed to {doc.path}"


def test_t5_gate_exits_1_on_the_live_tree_and_names_its_findings():
    """The findings are the point. The gate must not be quietly green here."""
    rc, out, err = _run(REPO)
    assert rc == 1, f"rc={rc}\n{out}\n{err}"
    for (rel, section), _count in _BASELINE_UNRESOLVED.items():
        assert f"UNRESOLVED §{section}" in out
        assert rel in out, rel


def test_gate_module_imports():
    assert gate is not None
