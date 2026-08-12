#!/usr/bin/env python3
"""MAC-711 — no producing script may write a dead SHA into a canonical ``notes`` payload.

Why this gate exists as a separate instrument from ``scripts/check_commit_cites.py``.

That gate's selector is ``commit [`(]?<hex>``: the literal lowercase word *commit*,
then hex. It is the right shape for *prose* cites, and it is structurally blind to the
shape this gate covers — a SHA held in a Python constant and emitted as a JSON **value**::

    BIBLE_COMMIT = "0aa89a0"                 # no lowercase "commit " before the hex
    ...
    "bible_commit": BIBLE_COMMIT,            # the hex is not on this line at all

Measured at MAC-711: **zero** of the six defect sites the issue filed matched either
MAC-704 pattern. ``check_commit_cites.py`` printed ``PASS  (0 dead)`` before the repair
and prints it after, so it could not witness the fix in either direction. A green line
from an instrument that cannot see the defect is not evidence, and quoting it as though
it were is the failure this file exists to prevent.

What is checked, per producing script:

1. The payload the script actually builds — obtained by **calling** its audit-row writer
   against a scratch DB, never by re-implementing the dict here. A re-implementation
   would drift from the thing it claims to measure and pass while the real writer regressed.
2. ``json_valid`` on the emitted bytes.
3. No banned ``*_commit`` key survives in the payload.
4. No known dead SHA appears anywhere in the emitted bytes, at any nesting depth.
5. No ``commit <hex>`` form appears in the emitted bytes — i.e. the script cannot mint a
   cite that the MAC-704 gate *would* read as live and that resolves to nothing.
6. The durable anchor (amendment number / dispatch cite) is present and non-empty. Dropping
   a dead handle without leaving a live one is not a repair, it is an erasure.

R7 positive control. The assertions above are all *absence* claims, and an absence claim
over an instrument that cannot see is indistinguishable from a pass. So the same assertion
function is run against **inline synthetic fixtures** carrying the pre-repair shape, and
this gate fails at exit 2 if they do not trip it.

The fixtures are inline and synthetic on purpose. The obvious control — diff against the
pre-fix blob at ``HEAD`` — is self-erasing: it works exactly once, and goes permanently
inert the moment the repair commit lands, at which point this gate would print a green
line backed by a control that no longer evaluates anything.

Exit codes: ``0`` all payloads clean and the control fired; ``1`` a producing script emits
a dead SHA or lost its durable anchor; ``2`` the instrument could not evaluate (canonical
DB absent, a target script moved or its writer was renamed, or the positive control went
inert). Exit 2 is never a pass — an unevaluated check must not print PASS.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB_PATH = REPO / "db" / "argus.db"

# The MAC-704 selector, duplicated deliberately: this gate asserts a property *about* that
# selector (that a payload cannot match it), so it must hold its own copy rather than
# import one and silently follow a future retuning of it.
FILED_RE = re.compile(r"commit [`(]?([0-9a-f]{7,40})")

# Dead by the pre-v1.0.0 history rewrite (MAC-610). Not an allowlist whose staleness would
# change the answer — check 5 below rejects *any* `commit <hex>` form, and check 1 rejects
# the key shape regardless of value. This set only sharpens the failure message.
# dead-cite exemplar — quoted as test data, not asserted as a live argus cite.
DEAD_SHAS = ("0aa89a0", "90132fa", "8de7309")

BANNED_KEY_SUFFIX = "_commit"


def _load(rel: str, name: str):
    path = REPO / rel
    if not path.exists():
        raise FileNotFoundError(rel)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def audit_payload(con, label: str, notes: str, durable: list[str]) -> list[str]:
    """Run every assertion over one emitted payload. Returns a list of failure strings."""
    bad: list[str] = []
    if con.execute("SELECT json_valid(?)", (notes,)).fetchone()[0] != 1:
        return [f"{label}: emitted notes is not valid JSON"]
    obj = json.loads(notes)

    for key in obj:
        if key.endswith(BANNED_KEY_SUFFIX):
            bad.append(f"{label}: payload still carries a `*{BANNED_KEY_SUFFIX}` key: {key}={obj[key]!r}")
    for sha in DEAD_SHAS:
        if sha in notes:
            bad.append(f"{label}: emitted bytes carry dead sha {sha}")
    m = FILED_RE.search(notes)
    if m:
        bad.append(f"{label}: emitted bytes match the MAC-704 selector -> commit {m.group(1)}")
    for key in durable:
        if not obj.get(key):
            bad.append(f"{label}: durable anchor `{key}` missing or empty — dropped a handle without leaving one")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"check_mac711_payload_sha: CANNOT EVALUATE  ({DB_PATH.relative_to(REPO)} absent; "
              f"it is untracked and never ships in a clone). Not a pass.", file=sys.stderr)
        return 2

    ddl_row = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True).execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='extraction_runs'").fetchone()
    if not ddl_row:
        print("check_mac711_payload_sha: CANNOT EVALUATE  (extraction_runs not in canonical)", file=sys.stderr)
        return 2

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        con = sqlite3.connect(Path(td) / "scratch.db")
        con.execute(ddl_row[0])

        # ---- 1. cp7_cp10_v01_cutover.py -------------------------------------------
        try:
            cut = _load("db/validation/cp7_cp10_v01_cutover.py", "_m711_cut")
            spot = {"cat_flips_total": 17, "cat_flips_by_vendor": {"DJI": 13},
                    "scope_backfills_total": 4, "scope_backfills_us_count": 3,
                    "scope_backfills_global_count": 1, "post_active_rows": 121,
                    "post_total_rows": 121}
            rid = cut._insert_audit_row(con, spot_check=spot, no_op=False,
                                        started_at_iso="1970-01-01T00:00:00Z",
                                        finished_at_iso="1970-01-01T00:00:00Z")
            notes = con.execute("SELECT notes FROM extraction_runs WHERE id=?", (rid,)).fetchone()[0]
            failures += audit_payload(con, "cp7_cp10_v01_cutover", notes, ["amendments_applied"])
        except (FileNotFoundError, AttributeError, TypeError) as exc:
            print(f"check_mac711_payload_sha: CANNOT EVALUATE  cp7_cp10_v01_cutover ({exc})", file=sys.stderr)
            return 2

        # ---- 2. migration_0009_verify.py ------------------------------------------
        try:
            ver = _load("db/validation/migration_0009_verify.py", "_m711_009")
            snap = ver.TableSnapshot(row_count=10, indexes=("ix",), check_sql="CREATE TABLE x(id)")
            rid = ver._insert_audit_row(con, pre_identifiers=snap, pre_sources=snap,
                                        post_identifiers=snap, post_sources=snap,
                                        canary_results={"ok": True},
                                        started_at_iso="1970-01-01T00:00:00Z",
                                        finished_at_iso="1970-01-01T00:00:00Z")
            notes = con.execute("SELECT notes FROM extraction_runs WHERE id=?", (rid,)).fetchone()[0]
            failures += audit_payload(con, "migration_0009_verify", notes,
                                      ["amendments_landed", "amendments_referenced"])
        except (FileNotFoundError, AttributeError, TypeError) as exc:
            print(f"check_mac711_payload_sha: CANNOT EVALUATE  migration_0009_verify ({exc})", file=sys.stderr)
            return 2

        # ---- 3. mac110_close_out.py -----------------------------------------------
        # This one writes its payloads through inline INSERTs rather than one audit-row
        # helper, so the checkable surface is the module-level anchor string it emits —
        # which was also the only site in the three scripts whose rendered bytes matched
        # the MAC-704 selector at all.
        try:
            closeout = _load("db/validation/mac110_close_out.py", "_m711_110")
            anchor = closeout.RECLASS_ANCHOR
        except (FileNotFoundError, AttributeError) as exc:
            print(f"check_mac711_payload_sha: CANNOT EVALUATE  mac110_close_out ({exc})", file=sys.stderr)
            return 2
        for sha in DEAD_SHAS:
            if sha in anchor:
                failures.append(f"mac110_close_out.RECLASS_ANCHOR: carries dead sha {sha}")
        if FILED_RE.search(anchor):
            failures.append(f"mac110_close_out.RECLASS_ANCHOR: matches the MAC-704 selector -> {anchor!r}")
        if closeout.RATIFIED_AT_MAC not in anchor:
            failures.append("mac110_close_out.RECLASS_ANCHOR: durable anchor RATIFIED_AT_MAC missing")
        for const in ("RATIFIED_AT_COMMIT",):
            if hasattr(closeout, const):
                failures.append(f"mac110_close_out: dead-sha constant {const} reintroduced")
        for mod, const in ((cut, "BIBLE_COMMIT"), (ver, "BIBLE_COMMIT_PRE")):
            if hasattr(mod, const):
                failures.append(f"{mod.__name__}: dead-sha constant {const} reintroduced")

        # ---- R7 positive control ---------------------------------------------------
        # Synthetic pre-repair payloads. If these do NOT trip audit_payload, the checks
        # above are inert and their silence means nothing.
        # The `dead-cite exemplar` marker sits on each citing line, not above the block:
        # check_commit_cites.py reads the fence off the citing line only, so a marker on a
        # neighbouring line fences nothing. Learned the hard way at 7273a12, which staged
        # this file with the marker one line up and took the gate to exit 1.
        controls = {
            "ctrl_key": (json.dumps({"amendments_applied": ["CP7"], "bible_commit": "0aa89a0"}),  # dead-cite exemplar
                         ["amendments_applied"]),
            "ctrl_prose": (json.dumps({"amendments_applied": ["CP7"],
                                       "anchor": "MAC-104 + bible commit 8de7309"}),  # dead-cite exemplar
                           ["amendments_applied"]),
            "ctrl_no_anchor": (json.dumps({"stage": "x"}), ["amendments_applied"]),
        }
        inert = [name for name, (payload, durable) in controls.items()
                 if not audit_payload(con, name, payload, durable)]
        if inert:
            print(f"check_mac711_payload_sha: POSITIVE CONTROL INERT {inert} — the assertions "
                  f"cannot see the pre-repair defect, so their PASS is vacuous.", file=sys.stderr)
            return 2

    if args.json:
        print(json.dumps({"gate": "check_mac711_payload_sha", "failures": failures,
                          "ok": not failures, "controls_fired": True}, indent=2))
    if failures:
        for f in failures:
            print(f"  DEFECT  {f}")
        print(f"check_mac711_payload_sha: FAIL  MAC-711  ({len(failures)} defect(s), 3/3 controls fired)")
        return 1
    print("check_mac711_payload_sha: PASS  MAC-711  "
          "(3 producing scripts clean, 0 dead-sha payload keys, 3/3 controls fired)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
