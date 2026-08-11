#!/usr/bin/env python3
"""MAC-612 -- delta control for the MAC-45 drop-assignment map re-derive.

MAC-696 ratified "re-derive the map from live state" as the disposition for
the export halt. Re-deriving re-arms a change-detector at a new baseline,
which means it silently absorbs every canonical change since the last cut.
The CEO's binding acceptance condition on MAC-612 therefore requires that
the absorbed set be proven to be the authorized set before ``exports/`` is
written. This gate mechanises that requirement.

Run it at the final v1.7.0 SHA, before the exporter writes.

Four traps this encodes
-----------------------

Trap 1 (the re-derive destroys its own baseline).  ``coverage_matrix.py``
lines 1471-1477 write ``coverage_matrix.md`` and ``coverage_matrix_report``
``.json`` into ``--out-dir`` unconditionally, and ``--out-dir`` defaults to
``extraction_outputs/mac45`` -- the very file the delta is measured against.
Running the acceptance condition's step 1 in the obvious way overwrites the
step 2 baseline before step 2 reads it. This gate always re-derives into a
scratch directory and takes the baseline from git (``git show REV:PATH``),
so the comparison is against an immutable object rather than a file that
the previous command just clobbered. Before MAC-703 committed the map at
``7759b2a`` there was no git copy at all and the baseline was unrecoverable.

Trap 2 (an empty delta is UNEVALUATED, not PASS).  Measured 2026-08-11: the
tracked baseline at ``7759b2a`` is byte-identical to a fresh re-derive from
canonical ``5e0d3ce4`` (both sha256 ``59306900...``), so the changed-id set
is empty and the authorized set is empty, and a naive ``changed ==
authorized`` prints PASS while exercising nothing. The 12 ids the CEO cited
were already absorbed into that baseline. An empty delta therefore exits 2
(UNEVALUATED) unless ``--allow-empty-delta`` is passed to say so out loud.
A gate that cannot distinguish "nothing moved" from "the differ is broken"
is not a gate; ``--self-test`` supplies the positive control.

Trap 3 (two arms, different populations).  ``drop_assignments`` is nested
under each tally (``export_lynceus.py:645``), not at the top level, and the
two arms hold different row counts -- live 42,115 standard against 42,512
high-confidence. A row can move bins in the high-confidence arm only. This
gate unions both arms; checking ``drop_tally_standard`` alone misses the
difference.

Trap 4 (the relation is containment, never equality).  The acceptance
condition asks that the changed-id set *equal* the set of ids touched by
authorized migrations. The CEO's own reference numbers refute that reading:
the run yielded 12 changed ids while mig-0054 touched 11 rows
(``0054...sql:146``, ``WHERE id BETWEEN 42986 AND 42996``) and mig-0055
touched a 62-row scope plus id 35700 (``0055...sql:330``, ``<> 62``). 12 is
not 74. Most authorized writes change a column that no bin keys on --
mig-0055 set ``surveillance_vendor_flag`` on 62 rows and moved exactly one
bin -- so ``touched - changed`` is large and benign. The load-bearing
direction is ``changed - authorized``: a bin that moved with no authorized
migration behind it. That set alone triggers the escalation in step 4.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = "extraction_outputs/mac45/coverage_matrix_report.json"
ARMS = ("drop_tally_standard", "drop_tally_high_confidence")


def _assignments(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Pull the per-arm id -> bin maps, failing loudly on a shape change."""
    out: dict[str, dict[str, str]] = {}
    for arm in ARMS:
        if arm not in payload:
            raise SystemExit(f"map is missing arm {arm!r} -- shape changed, refusing to guess")
        tally = payload[arm]
        if "drop_assignments" not in tally:
            raise SystemExit(
                f"{arm} has no 'drop_assignments' (keys: {sorted(tally)}) -- shape changed"
            )
        out[arm] = tally["drop_assignments"]
    return out


def _load_baseline(rev: str | None, path: Path | None) -> dict[str, dict[str, str]]:
    if path is not None:
        return _assignments(json.loads(path.read_text(encoding="utf-8")))
    proc = subprocess.run(
        ["git", "show", f"{rev}:{MAP_PATH}"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"cannot read baseline {rev}:{MAP_PATH} -- {proc.stderr.strip()}\n"
            "The map must be tracked for the delta to have a fixed baseline (MAC-703)."
        )
    return _assignments(json.loads(proc.stdout))


def _rederive(db: Path, scratch: Path) -> dict[str, dict[str, str]]:
    """Re-derive into scratch. Never point --out-dir at the tracked path (Trap 1)."""
    scratch.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, "-m", "db.validation.coverage_matrix",
         "--db", str(db), "--out-dir", str(scratch)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    written = scratch / "coverage_matrix_report.json"
    # Verdict on the artifact, not on rc: a zero rc that wrote nothing is a failure.
    if not written.exists():
        raise SystemExit(
            f"re-derive wrote no report (rc={proc.returncode})\n{proc.stderr.strip()}"
        )
    return _assignments(json.loads(written.read_text(encoding="utf-8")))


def _changed_ids(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> set[str]:
    """Union across both arms of ids whose bin moved, entered, or left (Trap 3)."""
    changed: set[str] = set()
    for arm in ARMS:
        a, b = before[arm], after[arm]
        ka, kb = set(a), set(b)
        changed |= {i for i in ka & kb if a[i] != b[i]}
        changed |= ka ^ kb
    return changed


def _read_authorized(inline: str | None, from_file: Path | None) -> set[str]:
    ids: set[str] = set()
    if inline:
        ids |= {t.strip() for t in inline.replace(",", " ").split() if t.strip()}
    if from_file:
        for line in from_file.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                ids.add(line)
    return ids


def _self_test() -> int:
    """Positive control: a differ that cannot see a planted move proves nothing."""
    base = {arm: {"1": "below_confidence_floor", "2": "unknown_category", "3": "procurement_only"}
            for arm in ARMS}
    after = {arm: dict(base[arm]) for arm in ARMS}
    after["drop_tally_standard"]["1"] = "unknown_category"   # bin moved
    del after["drop_tally_high_confidence"]["3"]             # left the map
    after["drop_tally_standard"]["9"] = "unknown_category"   # entered the map
    got = _changed_ids(base, after)
    want = {"1", "3", "9"}
    if got != want:
        print(f"SELF-TEST FAIL: planted {sorted(want)}, detected {sorted(got)}")
        return 1
    if not _changed_ids(base, {arm: dict(base[arm]) for arm in ARMS}) == set():
        print("SELF-TEST FAIL: identical maps reported a delta")
        return 1
    print(f"SELF-TEST PASS: detected planted moves {sorted(want)} across both arms")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=str(REPO_ROOT / "db" / "argus.db"))
    parser.add_argument("--baseline-rev", default="HEAD",
                        help="git rev holding the previous map cut (default HEAD)")
    parser.add_argument("--baseline-file", type=Path,
                        help="read the baseline from a file instead of git")
    parser.add_argument("--scratch-dir", type=Path,
                        help="where to re-derive (default: a temp dir; never the tracked path)")
    parser.add_argument("--authorized-ids", help="comma/space separated row ids")
    parser.add_argument("--authorized-ids-file", type=Path,
                        help="one id per line, '#' comments allowed")
    parser.add_argument("--allow-empty-delta", action="store_true",
                        help="accept an empty changed-id set as PASS rather than UNEVALUATED")
    parser.add_argument("--self-test", action="store_true",
                        help="run the positive control and exit")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    baseline = _load_baseline(args.baseline_rev, args.baseline_file)
    scratch = args.scratch_dir or Path(tempfile.mkdtemp(prefix="mac612_rederive_"))
    if scratch.resolve() == (REPO_ROOT / "extraction_outputs" / "mac45").resolve():
        raise SystemExit("refusing to re-derive over the tracked baseline (Trap 1)")
    fresh = _rederive(Path(args.db), scratch)

    changed = _changed_ids(baseline, fresh)
    authorized = _read_authorized(args.authorized_ids, args.authorized_ids_file)
    unexplained = changed - authorized
    unmoved = authorized - changed

    src = args.baseline_file or f"{args.baseline_rev}:{MAP_PATH}"
    print(f"baseline:   {src}")
    print(f"re-derived: {scratch}")
    for arm in ARMS:
        print(f"  {arm}: baseline={len(baseline[arm])} rederived={len(fresh[arm])}")
    print(f"changed-id set    ({len(changed)}): {sorted(changed)}")
    print(f"authorized-id set ({len(authorized)}): {sorted(authorized)}")
    print(f"changed - authorized ({len(unexplained)}): {sorted(unexplained)}   <-- escalation set")
    print(f"authorized - changed ({len(unmoved)}): {sorted(unmoved)}   <-- benign, see Trap 4")

    if unexplained:
        print("\nFAIL: a bin moved with no authorized migration behind it.")
        print("Do NOT re-derive over it -- re-deriving erases the only evidence "
              "that an unauthorized write reached canonical (acceptance step 4).")
        return 1
    if not changed and not args.allow_empty_delta:
        # Two verdicts hide in an empty delta; keep them apart.
        print("\nSTALENESS CHECK PASS: the baseline map is current with canonical. "
              "Nothing has moved since the cut, so the map shipped against this "
              "baseline will not halt the exporter.")
        print("AUTHORIZATION CHECK UNEXERCISED: with no bin moves there is nothing "
              "to attribute, and 'changed == authorized' would compare {} to {} and "
              "print PASS while testing nothing. That is why this exits 2 and not 0.")
        print("Confirm the differ is alive with --self-test, then pass "
              "--allow-empty-delta to record the empty result deliberately.")
        return 2
    print("\nPASS: every bin move is attributable to an authorized migration.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
