"""MAC-755 — point the Wave-2 cohort extractors at frozen extraction-time canonical.

Why this exists
---------------
``db/sources/cohort*.py`` annotate each candidate with its presence in canonical
and, in several cohorts, *abort* when a candidate they expect to be net-new is
already held.  They read the LIVE ``db/argus.db``.  Those candidates have since
been promoted, so from that moment the cohort tests asserted something
permanently false — precisely *because* the extraction lane succeeded.

That is a self-destroying gate: green only in the window before its own cohort
lands, red forever after, and unable to certify anything post-promotion.

The subject under test is the **extractor's output** — which UUIDs it pulls out
of a pinned dex, whether its excerpts are byte-faithful, which magnets it
excludes — not the contents of canonical today.  So the tests read a frozen,
git-committed snapshot of canonical as it stood at extraction time instead.

What this is NOT
----------------
It is not a re-baseline against today's DB.  Each snapshot is derived from
``exports/argus_export.csv`` **as committed at a pinned release commit that
predates the cohort's own promotion**, an artifact independent of the candidate
lists, so it cannot be a restatement of the expectations it checks.
``scripts/mac755_build_frozen_snapshot.py`` regenerates the fixtures and
re-proves each epoch boundary from canonical's published history;
``tests/test_cohort_frozen_db.py`` re-proves the provenance from git.

Two epochs, because the cohorts promoted in two waves
-----------------------------------------------------
``v167``  — ``d4d16563d413288b2a8bc90ca4ca91d69e04aef4``, exported 2026-06-12T14:46:32Z, 43,213 rows.
            Last published export before the MAC-364/365/366/368 wave landed.
            Cohorts 1, 2, 3-drones, 5.
``wave2`` — ``65a9c976954d39b986d22007143d9b0fc2c97e64``, exported 2026-06-14T05:32:23Z, 43,123 rows.
            Last published export before the MAC-419 Wave-2 ingestion.
            Cohorts 3-bletracker, 4, 6.

Usage — call before the cohort module's ``build()`` runs.  Several cohort test
modules call ``build()`` at import time, so the call goes above that import::

    from cohort_frozen_db import freeze_cohort_db
    freeze_cohort_db()
    from db.sources import cohort4_smartlock as c4  # noqa: E402
"""
from __future__ import annotations

import atexit
import csv
import gzip
import hashlib
import importlib
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GRANTEES_CSV = FIXTURES / "fcc_grantees_cohort_subset.csv"

# sha256 of each DECOMPRESSED identifiers CSV, and its row count. A corrupted or
# silently re-baselined fixture must fail loudly rather than quietly weaken
# every net-new assertion that reads it.
EPOCHS = {
    "v167": {
        "sha256": "8d9a3cba59d4322270cf614587d9ac89d29d002ec9992da35ea93ced729a67e4",
        "rows": 43213,
        "commit": "d4d16563d413288b2a8bc90ca4ca91d69e04aef4",  # v1.6.7 tag; byte-identical to the former da74f43 pin, which is not an ancestor of main and so is unresolvable in a public clone
        "exported_at": "2026-06-12T14:46:32Z",
    },
    "wave2": {
        "sha256": "206c8a4ead6e2bf9b2f2830f971e8dc7537aea9b5db87de1f5b721d02c443899",
        "rows": 43123,
        "commit": "65a9c976954d39b986d22007143d9b0fc2c97e64",  # v1.6.9 tag; byte-identical to the former 58648b7 pin, which is not an ancestor of main and so is unresolvable in a public clone
        "exported_at": "2026-06-14T05:32:23Z",
    },
}

# Which pre-promotion epoch each cohort extractor must read.
COHORT_EPOCH = {
    "db.sources.cohort1_ble_trackers": "v167",
    "db.sources.cohort2_alpr_copcar": "v167",
    "db.sources.cohort3_drones": "v167",
    "db.sources.cohort5_consumer": "v167",
    "db.sources.cohort3_bletracker": "wave2",
    "db.sources.cohort4_smartlock": "wave2",
    "db.sources.cohort6_petkid": "wave2",
}

# Exactly the columns the cohort modules SELECT. A query that reaches for
# anything else should fail loudly ("no such column"), not read a stale default.
_SCHEMA = """
CREATE TABLE identifiers (
    id              INTEGER PRIMARY KEY,
    identifier      TEXT,
    identifier_type TEXT,
    device_category TEXT,
    manufacturer    TEXT,
    confidence      INTEGER,
    source_type     TEXT,
    superseded_by   INTEGER
);
CREATE INDEX idx_identifiers_identifier ON identifiers(identifier);
CREATE INDEX idx_identifiers_lower      ON identifiers(lower(identifier));
CREATE INDEX idx_identifiers_type       ON identifiers(identifier_type);
CREATE TABLE fcc_grantees (
    grantee_code TEXT PRIMARY KEY,
    grantee_name TEXT,
    city         TEXT,
    state        TEXT,
    country      TEXT,
    contact_name TEXT
);
"""

_built: dict[str, Path] = {}
_tmpdir: tempfile.TemporaryDirectory | None = None


def _fixture(epoch: str) -> Path:
    return FIXTURES / f"canonical_identifiers_{epoch}.csv.gz"


def _load_identifiers(epoch: str) -> list[dict]:
    spec = EPOCHS[epoch]
    raw = gzip.decompress(_fixture(epoch).read_bytes())
    got = hashlib.sha256(raw).hexdigest()
    if got != spec["sha256"]:
        raise AssertionError(
            f"frozen canonical snapshot '{epoch}' has moved: sha256 {got} != "
            f"{spec['sha256']}. Regenerate with "
            "scripts/mac755_build_frozen_snapshot.py and re-ratify — do NOT "
            "re-baseline it against today's db/argus.db.")
    rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
    if len(rows) != spec["rows"]:
        raise AssertionError(
            f"frozen snapshot '{epoch}' row count {len(rows)} != {spec['rows']}")
    return rows


def _materialise(epoch: str) -> Path:
    """Build one epoch's snapshot SQLite DB once per process, in a temp dir."""
    global _tmpdir
    if epoch in _built:
        return _built[epoch]
    rows = _load_identifiers(epoch)
    if _tmpdir is None:
        _tmpdir = tempfile.TemporaryDirectory(prefix="mac755-frozen-canonical-")
        atexit.register(_tmpdir.cleanup)
    path = Path(_tmpdir.name) / f"canonical_{epoch}.db"
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    # CSV cannot represent SQL NULL, so "" round-trips back to NULL. That is
    # exact, not a guess: canonical holds 0 empty-string values in every column
    # carried here (verified by mac755_build_frozen_snapshot.verify_null_mapping).
    def nz(v):
        return v if v else None
    # The export publishes only active rows, and every cohort query filters on
    # `superseded_by IS NULL`, so the column is uniformly NULL by construction.
    conn.executemany(
        "INSERT INTO identifiers "
        "(id, identifier, identifier_type, device_category, manufacturer, "
        " confidence, source_type, superseded_by) VALUES (?,?,?,?,?,?,?,NULL)",
        [(int(r["id"]), nz(r["identifier"]), nz(r["identifier_type"]),
          nz(r["device_category"]), nz(r["manufacturer"]),
          int(r["confidence"]) if r["confidence"] else None,
          nz(r["source_type"])) for r in rows])
    with GRANTEES_CSV.open(encoding="utf-8") as fh:
        conn.executemany(
            "INSERT INTO fcc_grantees "
            "(grantee_code, grantee_name, city, state, country, contact_name) "
            "VALUES (?,?,?,?,?,?)",
            [(g["grantee_code"], nz(g["grantee_name"]), nz(g["city"]),
              nz(g["state"]), nz(g["country"]), nz(g["contact_name"]))
             for g in csv.DictReader(fh)])
    conn.commit()
    conn.close()
    path.chmod(0o444)  # the cohorts open mode=ro; make that structural
    _built[epoch] = path
    return path


def freeze_cohort_db() -> dict[str, Path]:
    """Repoint every cohort extractor's ``DB`` at its pre-promotion snapshot.

    Idempotent. Returns ``{module_name: snapshot_path}``.
    """
    out = {}
    for name, epoch in COHORT_EPOCH.items():
        path = _materialise(epoch)
        mod = sys.modules.get(name) or importlib.import_module(name)
        mod.DB = path
        out[name] = path
    return out
