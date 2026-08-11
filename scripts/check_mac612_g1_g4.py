#!/usr/bin/env python3
"""MAC-612 -- G1..G4 acceptance gate for the v1.7.0 export regen.

The CEO retired the 07-29 pinned absolutes (``ADDED 8 / REMOVED 0 /
CONTENT-CHANGED 0``, comment ``4c9fe17c``) in comment ``65bcf9d4`` and
replaced them with five artifact properties. G5 is a DB-side dominance sweep
discharged separately (557 folds, clean). This gate discharges G1..G4 against
an emitted artifact pair.

  G1  The distinct ``(pattern_type, pattern)`` key set of each regenerated
      feed is a SUPERSET of the committed baseline's. Coverage-level REMOVED
      is 0 in ``argus_export.json`` AND ``argus_export_high_confidence.json``.
      Multiplicity reduction is expected and permitted; losing a pattern is not.
  G2  Every baseline entry whose multiplicity DROPS has a survivor that is no
      worse field by field. Must print ``worse = 0``. G1 alone is blind to
      content outside the key.
  G3  ADDED attributed row by row.
  G4  Every CONTENT-CHANGED entry attributed to a named migration line.

Three traps this encodes
------------------------

Trap A (two different keys, deliberately).  G1 keys on
``(pattern_type, pattern)`` -- COVERAGE, "can a scanner still match this
pattern". G3/G4 key on ``(pattern_type, pattern, argus_record_id)`` --
IDENTITY. Conflating them is the whole point of the CEO's G1 wording:
``argus_record_id`` is a content hash that several canonical rows can SHARE
(ids 565 and 35666 both emit ``a2d37fb799db170f``), so a fold that drops one
emitter reduces multiplicity WITHOUT touching coverage. Measuring G1 on the
identity key would report a spurious REMOVED; measuring G3 on the coverage
key would hide a genuine row swap.

Trap B (a multiset, never a set).  The committed feed ships repeated keys.
Differencing as a set collapses them and a fold reads as "no change" -- which
is exactly the change mig-0049 makes. Every count here is a
``collections.Counter`` delta.

Trap C (an all-pass gate that cannot fail is not a gate).  ``--self-test``
plants a lost pattern, a degraded survivor, an unattributable addition and a
content change into a copy of the regenerated artifact and asserts each gate
FAILS. A gate whose positive control is never run cannot distinguish "clean"
from "blind" (R7).

On-disk key names are ``entries`` / ``pattern`` / ``pattern_type`` (NOT
``type`` / ``value``); a reader that guesses the latter finds nothing and
reports a clean diff over an empty set.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

COVERAGE_KEY = ("pattern_type", "pattern")
IDENTITY_KEY = ("pattern_type", "pattern", "argus_record_id")


def load_entries(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        doc = json.load(fh)
    if not isinstance(doc, dict) or "entries" not in doc:
        raise SystemExit(
            f"FATAL: {path} has no top-level 'entries' key; got "
            f"{list(doc)[:8] if isinstance(doc, dict) else type(doc).__name__}. "
            "Refusing to diff an empty set and call it clean."
        )
    entries = doc["entries"]
    if not isinstance(entries, list):
        raise SystemExit(f"FATAL: {path} 'entries' is {type(entries).__name__}, not a list.")
    return entries


def key_of(entry: dict, fields: tuple) -> tuple:
    return tuple(entry.get(f) for f in fields)


def payload_of(entry: dict, fields: tuple) -> dict:
    return {k: v for k, v in entry.items() if k not in fields}


def _fmt(key: tuple) -> str:
    return " | ".join("" if k is None else str(k) for k in key)


def gate_g1(base: list[dict], regen: list[dict], label: str, out: list) -> int:
    """Coverage: regenerated distinct (pattern_type, pattern) set superset of baseline."""
    bset = {key_of(e, COVERAGE_KEY) for e in base}
    rset = {key_of(e, COVERAGE_KEY) for e in regen}
    lost = sorted(bset - rset)
    gained = sorted(rset - bset)
    out.append(f"  {label}")
    out.append(f"    distinct coverage keys: baseline={len(bset)}  regenerated={len(rset)}")
    out.append(f"    coverage-level REMOVED (lost patterns): {len(lost)}")
    for k in lost:
        out.append(f"      LOST  {_fmt(k)}")
    out.append(f"    coverage-level ADDED (new patterns):    {len(gained)}")
    for k in gained[:50]:
        out.append(f"      NEW   {_fmt(k)}")
    return len(lost)


def gate_g2(base: list[dict], regen: list[dict], label: str, out: list) -> int:
    """Dominance: every coverage key whose multiplicity drops has a no-worse survivor."""
    bmult = Counter(key_of(e, COVERAGE_KEY) for e in base)
    rmult = Counter(key_of(e, COVERAGE_KEY) for e in regen)

    bpay = defaultdict(list)
    for e in base:
        bpay[key_of(e, COVERAGE_KEY)].append(payload_of(e, COVERAGE_KEY))
    rpay = defaultdict(list)
    for e in regen:
        rpay[key_of(e, COVERAGE_KEY)].append(payload_of(e, COVERAGE_KEY))

    dropped = [k for k in bmult if rmult.get(k, 0) < bmult[k]]
    worse: list[str] = []
    for k in sorted(dropped):
        survivors = rpay.get(k, [])
        if not survivors:
            worse.append(f"      WORSE {_fmt(k)}: no survivor at all")
            continue
        # Every non-empty field value present on some baseline emitter must be
        # matched by some survivor, or the survivor is strictly worse.
        for field in sorted({f for p in bpay[k] for f in p}):
            bvals = {str(p.get(field) or "").strip() for p in bpay[k]}
            bvals.discard("")
            svals = {str(s.get(field) or "").strip() for s in survivors}
            svals.discard("")
            if bvals and not (bvals & svals):
                worse.append(
                    f"      WORSE {_fmt(k)}: field '{field}' baseline={sorted(bvals)} "
                    f"survivors={sorted(svals)}"
                )
    out.append(f"  {label}")
    out.append(f"    coverage keys with reduced multiplicity: {len(dropped)}")
    out.append(f"    worse = {len(worse)}")
    out.extend(worse)
    return len(worse)


def gate_g3_g4(base: list[dict], regen: list[dict], label: str, out: list) -> tuple[list, list, list]:
    """Identity-level multiset diff: ADDED / REMOVED / CONTENT-CHANGED."""
    bkeys = Counter(key_of(e, IDENTITY_KEY) for e in base)
    rkeys = Counter(key_of(e, IDENTITY_KEY) for e in regen)
    added = rkeys - bkeys
    removed = bkeys - rkeys

    bpay = defaultdict(list)
    for e in base:
        bpay[key_of(e, IDENTITY_KEY)].append(payload_of(e, IDENTITY_KEY))
    rpay = defaultdict(list)
    for e in regen:
        rpay[key_of(e, IDENTITY_KEY)].append(payload_of(e, IDENTITY_KEY))

    changed = []
    for k in set(bpay) & set(rpay):
        bs = sorted(json.dumps(p, sort_keys=True, ensure_ascii=False) for p in bpay[k])
        rs = sorted(json.dumps(p, sort_keys=True, ensure_ascii=False) for p in rpay[k])
        if bs != rs:
            changed.append((k, bs, rs))

    out.append(f"  {label}")
    out.append(f"    ADDED   (identity, multiplicity-aware): {sum(added.values())}")
    for k, n in sorted(added.items()):
        out.append(f"      ADD   x{n}  {_fmt(k)}")
    out.append(f"    REMOVED (identity, multiplicity-aware): {sum(removed.values())}")
    for k, n in sorted(removed.items()):
        out.append(f"      REM   x{n}  {_fmt(k)}")
    out.append(f"    CONTENT-CHANGED on surviving keys:      {len(changed)}")
    for k, bs, rs in sorted(changed):
        out.append(f"      CHG   {_fmt(k)}")
        out.append(f"              baseline: {bs}")
        out.append(f"              regen:    {rs}")
    return list(added.items()), list(removed.items()), changed


def run_feed(base_path: Path, regen_path: Path, label: str, out: list) -> dict:
    base = load_entries(base_path)
    regen = load_entries(regen_path)
    out.append("")
    out.append(f"=== {label} ===")
    out.append(f"  entries: baseline={len(base)}  regenerated={len(regen)}  delta={len(regen)-len(base):+d}")
    out.append("")
    out.append("--- G1 coverage (distinct (pattern_type, pattern)) ---")
    g1 = gate_g1(base, regen, label, out)
    out.append("")
    out.append("--- G2 dominance on multiplicity drops ---")
    g2 = gate_g2(base, regen, label, out)
    out.append("")
    out.append("--- G3/G4 identity-level multiset diff ---")
    added, removed, changed = gate_g3_g4(base, regen, label, out)
    return {
        "label": label,
        "g1_lost": g1,
        "g2_worse": g2,
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def self_test(base_path: Path, regen_path: Path) -> int:
    """R7 positive control: each gate must FAIL on a planted defect."""
    base = load_entries(base_path)
    regen = load_entries(regen_path)
    failures = []

    # Control 1: drop every emitter of one baseline pattern -> G1 must see a lost pattern.
    victim = key_of(base[0], COVERAGE_KEY)
    poisoned = [e for e in regen if key_of(e, COVERAGE_KEY) != victim]
    out: list[str] = []
    if gate_g1(base, poisoned, "self-test/G1", out) == 0:
        failures.append("G1 did NOT detect a removed pattern")

    # Control 2: degrade a survivor's description on a key whose multiplicity drops.
    bm = Counter(key_of(e, COVERAGE_KEY) for e in base)
    rm = Counter(key_of(e, COVERAGE_KEY) for e in regen)
    drop_keys = [k for k in bm if rm.get(k, 0) < bm[k]]
    out = []
    if drop_keys:
        poisoned = copy.deepcopy(regen)
        for e in poisoned:
            if key_of(e, COVERAGE_KEY) == drop_keys[0]:
                e["description"] = ""
        if gate_g2(base, poisoned, "self-test/G2", out) == 0:
            failures.append("G2 did NOT detect a degraded survivor")
    else:
        failures.append("G2 control UNEXERCISED: no multiplicity drop to degrade")

    # Control 3: plant an addition and a content change -> G3/G4 must see both.
    poisoned = copy.deepcopy(regen)
    poisoned.append({"pattern": "ZZ-PLANTED", "pattern_type": "oui",
                     "description": "planted", "argus_record_id": "deadbeefdeadbeef"})
    for e in poisoned:
        if key_of(e, IDENTITY_KEY) in {key_of(b, IDENTITY_KEY) for b in base}:
            e["description"] = str(e.get("description", "")) + " PLANTED"
            break
    out = []
    added, removed, changed = gate_g3_g4(base, poisoned, "self-test/G3G4", out)
    if not added:
        failures.append("G3 did NOT detect a planted addition")
    if not changed:
        failures.append("G4 did NOT detect a planted content change")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  " + f)
        return 1
    print("SELF-TEST PASS: G1 saw a lost pattern, G2 saw a degraded survivor, "
          "G3 saw a planted addition, G4 saw a planted content change.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-dir", type=Path, required=True)
    ap.add_argument("--regen-dir", type=Path, required=True)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    feeds = [
        ("argus_export.json", "argus_export.json (standard feed)"),
        ("argus_export_high_confidence.json", "argus_export_high_confidence.json (high-confidence feed)"),
    ]

    if args.self_test:
        return self_test(args.baseline_dir / feeds[0][0], args.regen_dir / feeds[0][0])

    out: list[str] = []
    results = []
    for fname, label in feeds:
        results.append(run_feed(args.baseline_dir / fname, args.regen_dir / fname, label, out))

    print("\n".join(out))
    print()
    print("=" * 72)
    print("VERDICT")
    print("=" * 72)
    g1_fail = sum(r["g1_lost"] for r in results)
    g2_fail = sum(r["g2_worse"] for r in results)
    for r in results:
        print(f"  {r['label']}")
        print(f"    G1 coverage REMOVED : {r['g1_lost']}   ({'PASS' if r['g1_lost']==0 else 'FAIL'})")
        print(f"    G2 worse            : {r['g2_worse']}   ({'PASS' if r['g2_worse']==0 else 'FAIL'})")
        print(f"    G3 ADDED            : {sum(n for _, n in r['added'])}  (attribution is manual, see listing)")
        print(f"    G4 CONTENT-CHANGED  : {len(r['changed'])}  (attribution is manual, see listing)")
    print()
    if g1_fail == 0 and g2_fail == 0:
        print("G1 PASS / G2 PASS. G3 and G4 require row-by-row attribution in the issue comment.")
        return 0
    print("G1 or G2 FAILED. Do not commit the regenerated exports.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
