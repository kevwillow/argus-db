#!/usr/bin/env python3
"""Derive the next free migration slot from BOTH the filesystem and the reservation layer.

Four lanes in a row have picked a colliding slot number (MAC-537 -> 0043, MAC-523 -> 0043,
MAC-537 -> 0045, and the CEO's "0046 or higher" on 2026-07-29). Every one of them was a correct
`ls db/migrations/` read. The number is claimed at *dispatch* and only becomes a file at *apply*,
so between those two moments the slot is invisible on disk — a filesystem read is necessary and
never sufficient.

This scans both layers and prints every claimant, so the collision is visible instead of inferred.

    python3 scripts/next_migration_slot.py
    python3 scripts/next_migration_slot.py --claim MAC-537   # also assert nobody else holds it

Exit 0 if a free slot was found, 1 if --claim's issue already appears to hold a different slot.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "db" / "migrations"
# Prose layers where a slot is reserved before the file exists.
SCAN_DIRS = ["operator_review", "docs"]
SLOT_RE = re.compile(r"\b(?:mig-|migrations/|migration\s+(?:number|slot)\s+`?|slot\s+`?)(\d{4})\b", re.I)
FILE_RE = re.compile(r"\b(\d{4})_([a-z0-9_]+)\.sql\b", re.I)


def on_disk():
    claims = {}
    for f in sorted(MIGRATIONS.glob("*.sql")):
        m = re.match(r"^(\d{4})_", f.name)
        if m:
            claims.setdefault(int(m.group(1)), []).append(("applied-file", f.name))
    return claims


def reserved():
    claims = {}
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for f in base.rglob("*.md"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                for m in list(SLOT_RE.finditer(line)) + list(FILE_RE.finditer(line)):
                    slot = int(m.group(1))
                    if slot > 9999:
                        continue
                    rel = f.relative_to(ROOT)
                    claims.setdefault(slot, []).append((f"{rel}:{line_no}", line.strip()[:90]))
    return claims


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claim", help="issue key that wants a slot, e.g. MAC-537")
    args = ap.parse_args()

    disk, res = on_disk(), reserved()
    if not disk:
        print("no migrations found — check the path", file=sys.stderr)
        return 1
    highest_file = max(disk)
    all_slots = sorted(set(disk) | set(res))

    print(f"highest file on disk : {highest_file:04d}")
    print(f"naive next (WRONG)   : {highest_file + 1:04d}   <- what `ls db/migrations/` tells you\n")
    print("claims above the highest applied file:")
    contested = [s for s in all_slots if s > highest_file]
    if not contested:
        print("  (none)")
    for s in contested:
        for where, what in res.get(s, []):
            print(f"  {s:04d}  RESERVED  {where}")
            print(f"        {what}")
        for kind, name in disk.get(s, []):
            print(f"  {s:04d}  {kind}  {name}")

    free = max(all_slots) + 1
    print(f"\nnext free slot       : {free:04d}")

    if args.claim:
        # Only the contested region matters. Below `highest_file` every slot is already a
        # committed file, so a mention there is history, not a claim.
        mine = sorted(s for s in contested
                      if any(args.claim.lower() in (w + t).lower() for w, t in res.get(s, []))
                      or any(args.claim.lower().replace("-", "") in n.lower() for _, n in disk.get(s, [])))
        if mine:
            print(f"{args.claim} already appears at slot(s): {[f'{s:04d}' for s in mine]}")
            if any(s != free for s in mine):
                print(f"  -> reconcile before writing {free:04d}")
                return 1
        else:
            print(f"{args.claim} holds no slot yet; claim {free:04d} in a committed file "
                  f"before dispatch so the next lane can see it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
