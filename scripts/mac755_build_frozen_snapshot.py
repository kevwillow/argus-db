#!/usr/bin/env python3
"""MAC-755 — regenerate the frozen extraction-time canonical snapshot fixtures.

The seven Wave-2 cohort extractor modules (``db/sources/cohort*.py``) annotate
every candidate with its presence in canonical and, in several cohorts, *abort*
when a candidate they expect to be net-new is already held.  They did this by
opening the LIVE ``db/argus.db``.  Once those candidates were promoted, that
made the cohort tests self-destroying: green only in the window before their own
cohort landed, red forever after.

The subject under test is the extractor's OUTPUT, not the contents of canonical
today, so the tests are repointed at a frozen extraction-time snapshot.  This
script builds those snapshots.  It is committed so the derivation is
reproducible and auditable — the fixtures are not hand-authored.

Provenance of the ``identifiers`` snapshots
-------------------------------------------
Source: ``exports/argus_export.csv`` as committed at a pinned release commit.
That artifact is a frozen, git-committed projection of canonical taken with
``confidence_threshold=0``, i.e. the whole active identifier set rather than a
feed-filtered subset.  It is independent of the cohort candidate lists, so
deriving the snapshot from it is not circular — it cannot be a restatement of
the expectations it checks.

Two epochs are needed because the cohorts promoted in two separate waves:

* ``v167`` — ``d4d16563d413288b2a8bc90ca4ca91d69e04aef4`` (v1.6.7, exported 2026-06-12T14:46:32Z, 43,213 rows).
  The last published export *before* the MAC-364/365/366/368 cohort wave landed.
  Serves cohorts 1, 2, 3-drones and 5.
* ``wave2`` — ``65a9c976954d39b986d22007143d9b0fc2c97e64`` (v1.6.9, exported 2026-06-14T05:32:23Z, 43,123 rows).
  The last published export *before* the MAC-419 Wave-2 ingestion (``cab606c628c3ceda86746fbb449ffe97bb4176d3``,
  2026-06-15T00:47Z) landed.  Serves cohorts 3-bletracker, 4 and 6.

The epoch boundaries are derived from canonical's own published history, not
from the candidate lists: for each cohort a probe identifier is walked through
every commit that touched ``exports/argus_export.csv``, and the epoch is the
newest export in which that probe is still absent.  ``--verify`` re-proves each
boundary by asserting the probe is absent at the pinned epoch and present at the
next published export.

The export publishes only rows with ``superseded_by IS NULL``, and every cohort
query filters on ``superseded_by IS NULL``, so the snapshots materialise the
column as uniformly NULL.

CSV cannot distinguish SQL NULL from the empty string.  Measured against live
canonical, the columns carried here hold 394 NULL / 0 empty ``manufacturer`` and
174 NULL / 0 empty ``confidence``, and no empty values in any other carried
column — so mapping ``"" -> NULL`` on load is exact, not a guess.
``verify_null_mapping()`` re-measures that.

Provenance of the ``fcc_grantees`` subset
-----------------------------------------
``fcc_grantees`` is a frozen FCC EAS registry import (freeze date 2021-03-22,
50,153 rows) — static reference data, not churning canonical, so it carries no
self-destroying-gate risk.  It is not published in any export, so the subset is
read from the live table, restricted to the 19 grantee codes the cohort modules
actually reference.

``contact_name`` is PII and is NEVER copied.  The modules use it only to count
suppressions (``if contact: redactions += 1``), so the snapshot stores a
non-PII sentinel that preserves truthiness and nothing else.

Usage
-----
    python3 scripts/mac755_build_frozen_snapshot.py [--verify]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures"
PIN_PATH = "exports/argus_export.csv"


class Epoch:
    """A pinned published-export epoch.

    Both the commit and the blob id are recorded: the blob id is what is
    actually verified, so a later rewrite of the commit cannot silently
    repoint the fixture at different bytes.
    """

    def __init__(self, key, commit, blob, sha256, exported_at, rows,
                 next_commit, probe, probe_note):
        self.key = key
        self.commit = commit
        self.blob = blob
        self.sha256 = sha256
        self.exported_at = exported_at
        self.rows = rows
        # The next published export after this epoch — where the probe appears.
        self.next_commit = next_commit
        self.probe = probe
        self.probe_note = probe_note

    @property
    def fixture(self) -> Path:
        return FIXTURES / f"canonical_identifiers_{self.key}.csv.gz"


EPOCHS = [
    Epoch(
        key="v167",
        commit="d4d16563d413288b2a8bc90ca4ca91d69e04aef4",
        blob="0ac66cbe79d368d53f569324584a2ec8449b7a9e",
        sha256="320dc53623d8d241eea112038bcaba8583afd4218a371b25b1384f3a76c4d259",
        exported_at="2026-06-12T14:46:32Z",
        rows=43213,
        next_commit="4d1dde208efa980ae9ac5dbf034c466f1c1b353c",
        probe="7dfc9000-7d1c-4951-86aa-8d9728f8d66c",
        probe_note="cohort-1 true 128-bit AirTag sound UUID (MAC-364 net-new)",
    ),
    Epoch(
        key="wave2",
        commit="65a9c976954d39b986d22007143d9b0fc2c97e64",
        blob="781e83ec51f85e60ccc29efb8d7349a6cbf694fb",
        sha256="cdf486114d155705ba865f4bb5e31844d3c5027d1e3ce245eadb0ec406c96755",
        exported_at="2026-06-14T05:32:23Z",
        rows=43123,
        next_commit="cab606c628c3ceda86746fbb449ffe97bb4176d3",
        probe="4d050010-766c-42c4-8944-42bc98fc2d09",
        probe_note="cohort-4 Kwikset GATT profile base UUID (MAC-406 net-new)",
    ),
]

GRANTEES_CSV = FIXTURES / "fcc_grantees_cohort_subset.csv"

# Exactly the identifiers columns the seven cohort modules SELECT.
ID_COLS = ["id", "identifier", "identifier_type", "device_category",
           "manufacturer", "confidence", "source_type"]
GRANTEE_COLS = ["grantee_code", "grantee_name", "city", "state", "country",
                "contact_name"]

# Non-PII stand-in for a present contact_name. Preserves truthiness for the
# redaction counter; carries no personal data.
CONTACT_SENTINEL = "[REDACTED_AT_SNAPSHOT]"

# Columns that must hold zero empty-string values in canonical for the
# CSV `"" -> NULL` load mapping to be exact.
NULLABLE_CHECK_COLS = ID_COLS


def _git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, check=True).stdout


def read_export(commit: str) -> list[dict]:
    """Parse a committed export CSV, skipping its ``# meta:`` preamble line."""
    blob = _git("show", f"{commit}:{PIN_PATH}").decode("utf-8", errors="replace")
    lines = blob.split("\n")
    if not lines[0].startswith("# meta:"):
        raise SystemExit(f"{commit}:{PIN_PATH} lost its '# meta:' preamble")
    return list(csv.DictReader(io.StringIO("\n".join(lines[1:]))))


def verify_pin(ep: Epoch) -> None:
    """The pinned blob must be exactly the bytes this fixture was derived from."""
    blob_id = _git("rev-parse", f"{ep.commit}:{PIN_PATH}").decode().strip()
    if blob_id != ep.blob:
        raise SystemExit(f"[{ep.key}] pinned blob moved: {blob_id} != {ep.blob}")
    got = hashlib.sha256(_git("cat-file", "blob", ep.blob)).hexdigest()
    if got != ep.sha256:
        raise SystemExit(f"[{ep.key}] pinned blob sha256 moved: {got} != {ep.sha256}")
    print(f"  [{ep.key}] pin ok: {ep.commit}:{PIN_PATH} blob={ep.blob}")


def verify_boundary(ep: Epoch) -> None:
    """Re-prove the epoch boundary from canonical's published history.

    The probe must be ABSENT at the pinned epoch and PRESENT at the next
    published export. A one-sided check would pass against any epoch old
    enough; requiring both arms pins the boundary exactly.
    """
    here = {(r["identifier"] or "").lower() for r in read_export(ep.commit)}
    nxt = {(r["identifier"] or "").lower() for r in read_export(ep.next_commit)}
    p = ep.probe.lower()
    if p in here:
        raise SystemExit(
            f"[{ep.key}] probe {ep.probe} ALREADY in {ep.commit} — epoch is too "
            "late; the cohort had already been promoted.")
    if p not in nxt:
        raise SystemExit(
            f"[{ep.key}] probe {ep.probe} still absent at {ep.next_commit} — "
            "epoch is needlessly early; a newer pre-promotion export exists.")
    print(f"  [{ep.key}] boundary ok: {ep.probe} absent@{ep.commit} "
          f"present@{ep.next_commit} ({ep.probe_note})")


def verify_null_mapping() -> None:
    """`"" -> NULL` on load is exact only if canonical holds no empty strings."""
    live = REPO / "db" / "argus.db"
    if not live.exists():
        print("  null-mapping check SKIPPED (db/argus.db absent)")
        return
    conn = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
    bad = []
    for col in NULLABLE_CHECK_COLS:
        n = conn.execute(f"SELECT COUNT(*) FROM identifiers WHERE {col}='' "
                         "AND superseded_by IS NULL").fetchone()[0]
        if n:
            bad.append(f"{col}={n}")
    conn.close()
    if bad:
        raise SystemExit(
            "canonical holds empty-string values in " + ", ".join(bad) +
            " — the CSV `\"\" -> NULL` load mapping is no longer exact.")
    print(f"  null-mapping ok: 0 empty-string values across {len(NULLABLE_CHECK_COLS)} "
          "carried columns (so \"\" is unambiguously NULL)")


def build_identifiers(ep: Epoch) -> None:
    rows = read_export(ep.commit)
    if len(rows) != ep.rows:
        raise SystemExit(f"[{ep.key}] expected {ep.rows} export rows, got {len(rows)}")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=ID_COLS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: r[c] for c in ID_COLS})
    payload = buf.getvalue().encode("utf-8")
    FIXTURES.mkdir(parents=True, exist_ok=True)
    # mtime=0 so the fixture is byte-reproducible across regenerations.
    with gzip.GzipFile(ep.fixture, "wb", mtime=0) as fh:
        fh.write(payload)
    print(f"  [{ep.key}] wrote {ep.fixture.relative_to(REPO)} ({len(rows)} rows, "
          f"{ep.fixture.stat().st_size} bytes gz)\n"
          f"           plaintext sha256={hashlib.sha256(payload).hexdigest()}")


def referenced_grantee_codes() -> list[str]:
    sys.path.insert(0, str(REPO))
    from db.sources import cohort2_alpr_copcar as c2
    from db.sources import cohort5_consumer as c5
    codes = {g[0] for g in c2._GRANTEES}
    codes |= {c for lst in c5.FCC_VENDOR_CODES.values() for c in lst}
    return sorted(codes)


def build_grantees() -> None:
    codes = referenced_grantee_codes()
    live = REPO / "db" / "argus.db"
    if not live.exists():
        raise SystemExit(f"{live} absent — cannot read the fcc_grantees subset")
    conn = sqlite3.connect(f"file:{live}?mode=ro", uri=True)
    out = []
    for code in codes:
        row = conn.execute(
            "SELECT grantee_code, grantee_name, city, state, country, contact_name "
            "FROM fcc_grantees WHERE grantee_code=?", (code,)).fetchone()
        if row is None:
            raise SystemExit(f"grantee {code} absent from fcc_grantees")
        code_, name, city, state, ctry, contact = row
        out.append({"grantee_code": code_, "grantee_name": name, "city": city,
                    "state": state, "country": ctry,
                    # PII never leaves the DB: truthiness only.
                    "contact_name": CONTACT_SENTINEL if (contact or "").strip() else ""})
    conn.close()
    with GRANTEES_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=GRANTEE_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(f"  wrote {GRANTEES_CSV.relative_to(REPO)} ({len(out)} codes, "
          f"contact_name replaced by a sentinel in "
          f"{sum(1 for r in out if r['contact_name'])} rows)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help="check pins, epoch boundaries and the NULL mapping; write nothing")
    args = ap.parse_args()
    print("MAC-755 frozen canonical snapshots")
    for ep in EPOCHS:
        verify_pin(ep)
        verify_boundary(ep)
    verify_null_mapping()
    if args.verify:
        return 0
    for ep in EPOCHS:
        build_identifiers(ep)
    build_grantees()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
