"""Pytest config: repo root on sys.path, plus the resource-availability markers.

Three markers say what a test needs from the environment it runs in:

  public         -- passes on a fresh public clone with no undistributed resources.
  canonical_db   -- requires db/argus.db, which is NOT distributed.
  raw_artifacts  -- requires the undistributed extraction inputs (see below).

A missing resource normally SKIPS the tests that declare it, so a public clone
runs green-with-skips instead of red. Set ``ARGUS_REQUIRE_ALL=1`` -- which the
canonical-environment CI job and any local full run do -- and a missing resource
becomes a loud collection-time failure instead. Without that escape hatch these
guards could rot into a suite that is green because it ran nothing.

Why the probes name individual FILES
------------------------------------
An earlier version answered "is raw/ available?" with ``is_dir() and
any(iterdir())``, and "is the canonical DB available?" with ``st_size > 0``.
Both are satisfiable by something that is not the resource:

  * one unrelated file dropped into ``raw/`` disarms the raw guard, and the
    failure mode is not a red test -- the three cohort modules read their
    artifacts during module-body execution, so the import raises
    ``FileNotFoundError`` and pytest reports "Interrupted: 1 error during
    collection". The WHOLE SESSION aborts, including every test that had
    nothing to do with raw/.
  * any 1-byte file at ``db/argus.db`` satisfies ``st_size > 0``, so the DB
    guard passes and every canonical_db test then fails on ``no such table``.

So each probe now checks the specific artifacts the tests actually read. The
artifact lists are derived from the cohort modules' OWN path constants (see
``_cohort_artifacts``) rather than copied, so a renamed constant raises here
instead of silently shrinking the guard.

``raw_artifacts`` covers more than the ``raw/`` tree
----------------------------------------------------
``db/sources/cohort2_alpr_copcar.py`` also reads
``extraction_outputs/mac321_v166/raw/fcc_grantee_full.json`` (line 217, via the
``A_FCC_JSON`` constant at line 53). That file is undistributed for the same
reason raw/ is -- ``.gitignore`` line 5's ``raw/`` rule matches it too -- and a
tree with raw/ present but that file absent aborted collection exactly as
described above. It is part of what ``raw_artifacts`` promises.

What is deliberately NOT probed
-------------------------------
Three inputs are read best-effort by the cohort extractors and degrade to a
recorded string instead of raising, so requiring them would skip tests that can
in fact run:

  * the APK/XAPK corpus under ``raw/vendor_apps/`` -- ``_verify_apk_evidence``
    returns ``"apk_absent"`` when the binary is missing;
  * ``/media/kev/Extreme SSD/.../opendata_fcc_3b3k-34jp_FULL.csv``
    (cohort3_drones ``FCC_CSV``) -- ``_frozen_fcc`` returns ``None`` when the
    SSD is not mounted, and the one test that reads it skips on its own
    ``FCC_CSV.exists()`` check;
  * cohort1's ``A_PETS`` / ``A_CHIPOLO`` / ``A_OPENHAYSTACK`` -- declared for
    provenance, never opened by ``build()`` and never named as a cite artifact.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent

# Pre-existing behaviour: make `db.dedup` and friends importable from the tests.
sys.path.insert(0, str(REPO_ROOT))

ARGUS_DB_PATH = Path(os.environ.get("ARGUS_DB", REPO_ROOT / "db" / "argus.db"))
ARGUS_RAW_DIR = Path(os.environ.get("ARGUS_RAW", REPO_ROOT / "raw"))

# A table every canonical DB carries. Named so the probe can tell a real
# database from an empty-but-valid SQLite file.
CANONICAL_TABLE = "identifiers"

CANONICAL_DB_SKIP_REASON = (
    "requires the canonical DB (db/argus.db), which is not distributed; "
    "see docs/engineering/SETUP.md"
)
RAW_ARTIFACTS_SKIP_REASON = (
    "requires raw source artifacts (raw/), which are not distributed; "
    "see docs/engineering/SETUP.md"
)

REQUIRE_ALL_ENV = "ARGUS_REQUIRE_ALL"


# ---------------------------------------------------------------------------
# Which undistributed artifacts each extraction module actually reads.
# ---------------------------------------------------------------------------
#
# Every path below was established by tracing the filesystem reads performed by
# that module's build(), not by reading its constant block: several declared
# constants are provenance-only and never opened.
#
# The values are CONSTANT NAMES on the module, not literal paths. Getting one
# wrong is an AttributeError at collection time, which is the point -- a guard
# that quietly stops requiring a file it can no longer name is how this class of
# defect got here.
_COHORT_ARTIFACT_CONSTANTS: dict[str, tuple[str, ...]] = {
    "db.sources.cohort1_ble_trackers": (
        "A_COMPANY", "A_MEMBER", "A_USENIX", "A_AIRTAG",
        "A_APPLEFM", "A_TAGFINDER", "A_TILE", "A_SAMSUNG",
    ),
    # A_FCC_JSON is the extraction_outputs/ artifact; it is required exactly as
    # firmly as the three raw/ ones, because _fcc_grantee_full() read_text()s it
    # unconditionally.
    "db.sources.cohort2_alpr_copcar": ("A_SSID", "A_DET", "A_FCC_JSON", "A_IEEE_OUI"),
    "db.sources.cohort3_drones": ("SIG_YAML", "ODID_H"),
}

# cohort3's FAA cross-refs are built from a directory constant plus a vendor
# loop (db/sources/cohort3_drones.py:518-521), so there is no single constant to
# name. FAA_DIR still comes from the module.
_COHORT3_FAA_VENDORS = ("skydio", "autel", "parrot")

# Test module basename -> the extraction module whose artifacts it needs. Used
# to skip precisely: a tree missing only cohort2's artifact must not skip
# cohort1 and cohort3, which can still run.
TEST_MODULE_COHORTS: dict[str, str] = {
    "test_cohort1_ble_trackers.py": "db.sources.cohort1_ble_trackers",
    "test_cohort2_alpr_copcar.py": "db.sources.cohort2_alpr_copcar",
    "test_cohort3_drones.py": "db.sources.cohort3_drones",
}

_artifact_cache: dict[str, tuple[str, ...]] = {}


def _cohort_artifacts(module_name: str) -> tuple[str, ...]:
    """Repo-relative paths ``module_name`` reads and cannot degrade without.

    Imports the extraction module (stdlib-only, no side effects, ~10ms) and
    reads its own path constants, so this list cannot drift away from the code
    it is guarding.
    """
    if module_name in _artifact_cache:
        return _artifact_cache[module_name]
    mod = __import__(module_name, fromlist=["_"])
    paths = [getattr(mod, const) for const in _COHORT_ARTIFACT_CONSTANTS[module_name]]
    if module_name == "db.sources.cohort3_drones":
        paths += [f"{mod.FAA_DIR}/{v}.json" for v in _COHORT3_FAA_VENDORS]
    out = tuple(str(p) for p in paths)
    _artifact_cache[module_name] = out
    return out


def all_raw_artifacts() -> tuple[str, ...]:
    """Every undistributed extraction artifact, across all cohort modules."""
    seen: list[str] = []
    for module_name in _COHORT_ARTIFACT_CONSTANTS:
        for rel in _cohort_artifacts(module_name):
            if rel not in seen:
                seen.append(rel)
    return tuple(seen)


def artifact_path(rel: str) -> Path:
    """Resolve a repo-relative artifact path, honouring ``ARGUS_RAW``.

    Paths inside the ``raw/`` tree are re-rooted at ``ARGUS_RAW`` so the
    override keeps working; anything else (the extraction_outputs/ artifact) is
    resolved against the repo root.
    """
    if rel.startswith("raw/"):
        return ARGUS_RAW_DIR / rel[len("raw/"):]
    return REPO_ROOT / rel


def missing_artifacts(rels) -> list[str]:
    """The repo-relative paths in ``rels`` that are absent or empty."""
    missing = []
    for rel in rels:
        try:
            p = artifact_path(rel)
            if not (p.is_file() and p.stat().st_size > 0):
                missing.append(rel)
        except OSError:
            missing.append(rel)
    return missing


def require_all() -> bool:
    """True when the caller has demanded every resource actually be present."""
    return os.environ.get(REQUIRE_ALL_ENV) == "1"


def have_canonical_db() -> bool:
    """True when db/argus.db is a real canonical database.

    Three checks, cheapest first, because each one alone is spoofable:

    1. non-empty regular file. ``db/extraction/fcc_grantees_allowlist.py``
       opens the canonical path with a read-write ``sqlite3.connect``, which
       CREATES a 0-byte file as a side effect; a bare ``exists()`` is satisfied
       by that stub and every module collected afterwards then fails on
       ``no such table``.
    2. the 16-byte SQLite magic header. Size alone is satisfied by any 1-byte
       file -- ``echo x > db/argus.db`` used to be enough to disarm this guard.
    3. the ``identifiers`` table is present. A syntactically valid but EMPTY
       SQLite file carries the header and a non-trivial size, and would still
       fail every canonical_db test on ``no such table``.

    Opened ``mode=ro`` so the probe itself can never create the stub it is
    looking for. Three syscalls and one ``sqlite_master`` lookup -- cheap enough
    to call at collection time.
    """
    try:
        if not ARGUS_DB_PATH.is_file() or ARGUS_DB_PATH.stat().st_size <= 0:
            return False
        with ARGUS_DB_PATH.open("rb") as fh:
            if fh.read(16) != b"SQLite format 3\x00":
                return False
        conn = sqlite3.connect(f"file:{ARGUS_DB_PATH}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
                (CANONICAL_TABLE,),
            ).fetchone()
        finally:
            conn.close()
        return bool(row) and row[0] > 0
    except (OSError, sqlite3.Error):
        return False


def have_raw_artifacts() -> bool:
    """True when the whole ``raw/`` extraction tree is provisioned.

    The coarse, tree-level question: does this checkout hold every raw/ artifact
    any raw_artifacts-marked module reads? Deliberately NOT "is raw/ non-empty"
    -- see the module docstring.

    Artifacts outside raw/ are excluded here on purpose, so that a tree missing
    only ``extraction_outputs/mac321_v166/raw/fcc_grantee_full.json`` does not
    skip cohort1 and cohort3, which do not read it. Use
    ``have_module_artifacts()`` for the per-module question, and
    ``missing_resources()`` for the ARGUS_REQUIRE_ALL hatch, which demands
    every artifact regardless of where it lives.
    """
    raw_only = [rel for rel in all_raw_artifacts() if rel.startswith("raw/")]
    return not missing_artifacts(raw_only)


def have_module_artifacts(module_name: str) -> bool:
    """True when every artifact ``module_name`` reads is present."""
    return not missing_artifacts(_cohort_artifacts(module_name))


def module_artifacts_skip_reason(module_name: str) -> str:
    """Skip text naming the exact files that are missing for ``module_name``."""
    missing = missing_artifacts(_cohort_artifacts(module_name))
    return (
        "requires raw source artifacts (raw/), which are not distributed; "
        f"{len(missing)} missing: " + ", ".join(missing) +
        "; see docs/engineering/SETUP.md"
    )


def missing_resources() -> list[str]:
    """The undistributed resources that are absent, in report order.

    Two entries maximum, one per resource the repo declares undistributed. The
    raw entry NAMES the individual artifacts that are missing -- including the
    one under extraction_outputs/ -- so a partially provisioned tree reports
    which files to fetch rather than "raw/ is missing" when raw/ is right there.
    """
    missing: list[str] = []
    if not have_canonical_db():
        missing.append(f"canonical DB (db/argus.db) expected at {ARGUS_DB_PATH}")
    absent = missing_artifacts(all_raw_artifacts())
    if absent:
        detail = ", ".join(absent[:4])
        if len(absent) > 4:
            detail += f", and {len(absent) - 4} more"
        missing.append(
            f"raw source artifacts (raw/) expected at {ARGUS_RAW_DIR} "
            f"-- {len(absent)} artifact(s) absent: {detail}"
        )
    return missing


def pytest_collection(session):
    """Anti-vacuous escape hatch: ARGUS_REQUIRE_ALL=1 must never skip quietly.

    Raised at collection start, before any module that hard-imports a raw
    artifact gets a chance to be imported, so the failure names the missing
    resource instead of surfacing as an opaque collection error.
    """
    if not require_all():
        return None
    missing = missing_resources()
    if missing:
        raise pytest.UsageError(
            f"{REQUIRE_ALL_ENV}=1 requires every undistributed resource to be "
            f"present, but {len(missing)} is missing: " + "; ".join(missing) + ". "
            f"Unset {REQUIRE_ALL_ENV} to run the public subset with skips, or "
            "see docs/engineering/SETUP.md to obtain the resource."
        )
    return None


def pytest_collection_modifyitems(config, items):
    """Skip items whose declared resource is absent -- unless ARGUS_REQUIRE_ALL=1.

    Also applies the ``public`` marker, which is the complement of the two
    resource markers and is therefore COMPUTED rather than hand-written. Before
    this it was declared in pytest.ini, applied to one module, read by nothing,
    and selected on by no CI job -- a label asserting "passes on a fresh public
    clone" while enforcing nothing. Computing it makes ``-m public`` name
    exactly the subset the ``public-suite`` workflow runs on a resource-free
    checkout, and makes it impossible for the label to drift out of step with
    the markers as tests are added.

    A hand-written ``public`` on an item that ALSO declares a resource marker is
    a contradiction, and is raised rather than silently overwritten.
    """
    contradictions = [
        item.nodeid
        for item in items
        if "public" in item.keywords
        and ("canonical_db" in item.keywords or "raw_artifacts" in item.keywords)
    ]
    if contradictions:
        raise pytest.UsageError(
            "these items are marked `public` -- passes on a fresh public clone "
            "-- while also declaring an undistributed resource, which is a "
            "contradiction: " + "; ".join(contradictions[:10])
        )
    public = pytest.mark.public
    for item in items:
        if "canonical_db" not in item.keywords and "raw_artifacts" not in item.keywords:
            item.add_marker(public)

    if require_all():
        return

    db_ok = have_canonical_db()
    raw_ok = have_raw_artifacts()
    skip_db = pytest.mark.skip(reason=CANONICAL_DB_SKIP_REASON)
    skip_raw = pytest.mark.skip(reason=RAW_ARTIFACTS_SKIP_REASON)

    # Per-module skips: an item in a cohort test module is skipped when THAT
    # module's own artifacts are incomplete, even if the rest of raw/ is fine.
    module_skips: dict[str, object] = {}
    for basename, cohort in TEST_MODULE_COHORTS.items():
        if not have_module_artifacts(cohort):
            module_skips[basename] = pytest.mark.skip(
                reason=module_artifacts_skip_reason(cohort)
            )

    for item in items:
        if not db_ok and "canonical_db" in item.keywords:
            item.add_marker(skip_db)
        if "raw_artifacts" in item.keywords:
            per_module = module_skips.get(Path(str(item.fspath)).name)
            if per_module is not None:
                item.add_marker(per_module)
            elif not raw_ok:
                item.add_marker(skip_raw)
