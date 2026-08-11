#!/usr/bin/env python3
"""MAC-612 -- three-way acceptance diff for the v1.7.0 export regen.

The acceptance gate on this issue is three assertions, not an entry count:

  1. ADDED    is exactly the ratified v1.7.0 rows, named row by row.
  2. REMOVED  is 0.
  3. CONTENT-CHANGED on surviving entries is 0.

Two traps this encodes.

Trap A (the key is not unique).  The gate names the key
``(pattern_type, pattern, argus_record_id)``.  That triple does NOT identify
an entry: the committed feed ships repeated triples, because several
canonical ``(identifier_type, identifier)`` groups carry more than one ACTIVE
row and each emits its own entry under a shared key.  Differencing as a SET
silently collapses those repeats, so a fold that removes a duplicate emitter
reads as "no change" -- which is exactly the change mig-0049 makes.  Every
comparison here is therefore a MULTISET (``collections.Counter``) and the
ADDED/REMOVED counts are multiplicity deltas, not set deltas.

Trap B (content drift hides under a stable key).  An entry can keep its key
and change its payload.  Assertion 3 is measured over the keys present on
BOTH sides, comparing the full entry dict minus the key fields, so a
confidence bump or a category retype surfaces instead of cancelling.

On-disk key names are ``entries`` / ``pattern`` / ``pattern_type``
(NOT ``type`` / ``value``); a reader that guesses the latter finds nothing
and reports a clean diff over an empty set.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

KEY_FIELDS = ("pattern_type", "pattern", "argus_record_id")


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


def key_of(entry: dict) -> tuple:
    return tuple(entry.get(f) for f in KEY_FIELDS)


def payload_of(entry: dict) -> str:
    """Stable serialisation of everything that is NOT the key."""
    rest = {k: v for k, v in entry.items() if k not in KEY_FIELDS}
    return json.dumps(rest, sort_keys=True, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="committed exports/ JSON")
    ap.add_argument("--regenerated", required=True, help="freshly regenerated JSON")
    ap.add_argument("--label", default="argus_export.json")
    ap.add_argument(
        "--expect-added-records",
        default="",
        help="comma-separated argus_record_id values ADDED is asserted to equal",
    )
    args = ap.parse_args()

    base = load_entries(Path(args.baseline))
    regen = load_entries(Path(args.regenerated))

    bkeys = Counter(key_of(e) for e in base)
    rkeys = Counter(key_of(e) for e in regen)

    # Multiset difference: multiplicity-aware in both directions.
    added = rkeys - bkeys
    removed = bkeys - rkeys

    print(f"### {args.label}")
    print(f"  baseline entries    : {len(base)}")
    print(f"  regenerated entries : {len(regen)}")
    print(f"  net entry delta     : {len(regen) - len(base):+d}")
    print(f"  distinct keys       : baseline={len(bkeys)} regenerated={len(rkeys)}")
    dup_base = sum(c - 1 for c in bkeys.values() if c > 1)
    dup_regen = sum(c - 1 for c in rkeys.values() if c > 1)
    print(f"  repeated-key excess : baseline={dup_base} regenerated={dup_regen}")
    print()

    n_added = sum(added.values())
    n_removed = sum(removed.values())
    print(f"  ADDED   (multiset): {n_added}")
    for k, c in sorted(added.items(), key=lambda kv: str(kv[0])):
        print(f"    + {k}" + (f"  x{c}" if c > 1 else ""))
    print(f"  REMOVED (multiset): {n_removed}")
    for k, c in sorted(removed.items(), key=lambda kv: str(kv[0])):
        print(f"    - {k}" + (f"  x{c}" if c > 1 else ""))
    print()

    # Assertion 3: content drift on keys present on BOTH sides.
    shared = set(bkeys) & set(rkeys)
    bpay: dict[tuple, Counter] = {}
    rpay: dict[tuple, Counter] = {}
    for e in base:
        k = key_of(e)
        if k in shared:
            bpay.setdefault(k, Counter())[payload_of(e)] += 1
    for e in regen:
        k = key_of(e)
        if k in shared:
            rpay.setdefault(k, Counter())[payload_of(e)] += 1

    changed = []
    for k in shared:
        if bpay.get(k) != rpay.get(k):
            changed.append(k)
    print(f"  CONTENT-CHANGED on surviving keys: {len(changed)}")
    for k in sorted(changed, key=str)[:40]:
        print(f"    ~ {k}")
        b_only = bpay[k] - rpay[k]
        r_only = rpay[k] - bpay[k]
        for p in b_only:
            print(f"        baseline : {p[:400]}")
        for p in r_only:
            print(f"        regen    : {p[:400]}")
    if len(changed) > 40:
        print(f"    ... {len(changed) - 40} more")
    print()

    ok = True
    if n_removed != 0:
        print(f"  ASSERTION 2 FAIL: REMOVED is {n_removed}, gate requires 0")
        ok = False
    if len(changed) != 0:
        print(f"  ASSERTION 3 FAIL: CONTENT-CHANGED is {len(changed)}, gate requires 0")
        ok = False

    if args.expect_added_records:
        expected = [s.strip() for s in args.expect_added_records.split(",") if s.strip()]
        got = Counter()
        for k, c in added.items():
            got[str(k[KEY_FIELDS.index("argus_record_id")])] += c
        exp_c = Counter(expected)
        if got != exp_c:
            print("  ASSERTION 1 FAIL: ADDED record-id multiset != expected")
            print(f"    unexpected in ADDED : {sorted((got - exp_c).elements())}")
            print(f"    missing from ADDED  : {sorted((exp_c - got).elements())}")
            ok = False
        else:
            print(f"  ASSERTION 1 PASS: ADDED is exactly the {len(expected)} expected records")

    print(f"  RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
