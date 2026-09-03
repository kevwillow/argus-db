"""Tests for the argus_cli.py exports fallback (fresh-clone survivability).

A fresh public clone has `exports/` (tracked) but no `db/argus.db` (gitignored)
and no `raw/` (gitignored). Without a fallback, `status` and `query` both die
with `argus_cli: database not found ...` and exit 1. These tests pin the
fallback's contract:

  * the DEFAULT probe (no --db-path) uses the DB when present, exports/ when not
  * an EXPLICIT --db-path is a demand, not a probe: a missing one hard-fails
    exactly as it did at 9b32212, and is never degraded to exports/
  * `--source db` still hard-fails on a missing DB — no silent degradation
  * `--source exports` never opens the DB at all
  * the CSV's leading `# meta:` comment line is skipped, not read as a header
  * `status` reports the FIXTURE's meta values, never the shipped corpus's —
    the anti-fabrication property this module exists for
  * `status` reports what the exports feed cannot see as
    "unavailable (requires canonical DB)" — never as a fabricated 0
  * an exports-mode miss says the absence is relative to the EXPORT

How "no database" is simulated, and why it is not `--db-path <missing>`:

    Passing a missing path to --db-path is now a hard failure by design, so
    it can no longer stand in for "this clone has no DB". Two substitutes are
    used instead, both of which move the DEFAULT:

      fresh_clone   copies argus_cli.py into a tmp dir. REPO_ROOT is
                    `Path(__file__).resolve().parent`, so the copy's default
                    DB path is <tmp>/db/argus.db, which does not exist. This
                    is the real fresh-clone shape, exercised end to end with
                    no flags at all.
      no_default_db monkeypatches argus_cli.DEFAULT_DB_PATH for in-process
                    calls. build_parser() reads that global at call time, so
                    the patch reaches both the argparse default and
                    _resolve_source's getattr fallback.

Exit codes are measured by subprocess, not by catching SystemExit in-process:
`raise SystemExit("message")` sets `.code` to the *string*, and only the
interpreter turns that into a process rc of 1. The rc is the contract.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest

import argus_cli

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "argus_cli.py"
REAL_EXPORTS = REPO_ROOT / "exports"
REAL_DB = REPO_ROOT / "db" / "argus.db"

CSV_COLUMNS = [
    "argus_record_id", "id", "identifier", "identifier_type", "device_category",
    "manufacturer", "model", "confidence", "source_type", "source_url",
    "source_excerpt", "geographic_scope", "description", "first_seen",
    "last_verified", "notes",
]

# ─── shipped-corpus constants, and why the fixture must not reuse them ─────
#
# Measured at HEAD from exports/ (`head -1 exports/argus_export.csv`, and
# json.load()['_meta'] on each JSON feed):
#
#   argus_export.csv                          schema_version=35,
#                                             exported_at=2026-08-21T12:06:18Z
#   argus_export.json                         2026-08-21T12:06:18Z
#   argus_export_high_confidence.json         2026-08-21T12:06:18Z
#   argus_export_behavioral_signatures.json   2026-08-20T17:48:39Z
#
# These are the values a fabricating implementation would hard-code, because
# they are the values a developer sees on their own machine. If the synthetic
# fixture also carried them, every assertion below would pass against an
# implementation that ignores the file entirely and prints a constant. So the
# fixture deliberately carries values the shipped corpus does NOT have, and
# the tests assert BOTH that the fixture's values are reported AND that the
# shipped ones are absent.
SHIPPED_SCHEMA_VERSION = "35"
SHIPPED_EXPORTED_AT = "2026-08-21T12:06:18Z"
SHIPPED_BEHAVIORAL_EXPORTED_AT = "2026-08-20T17:48:39Z"

FIXTURE_SCHEMA_VERSION = "97"
FIXTURE_EXPORTED_AT = "1999-01-02T03:04:05Z"
# Per-file divergence is a real property of the shipped exports (the
# behavioral feed is stamped a day earlier than the other three), so the
# fixture reproduces the SHAPE with values of its own. There is no single
# repo-wide exported_at to print, and nothing may pretend otherwise.
FIXTURE_JSON_EXPORTED_AT = "1999-01-02T03:04:05Z"
FIXTURE_BEHAVIORAL_EXPORTED_AT = "1998-12-31T23:59:58Z"

assert FIXTURE_SCHEMA_VERSION != SHIPPED_SCHEMA_VERSION
assert FIXTURE_EXPORTED_AT != SHIPPED_EXPORTED_AT
assert FIXTURE_JSON_EXPORTED_AT != SHIPPED_EXPORTED_AT
assert FIXTURE_BEHAVIORAL_EXPORTED_AT != SHIPPED_BEHAVIORAL_EXPORTED_AT

META_LINE = (
    f"# meta: schema_version={FIXTURE_SCHEMA_VERSION}, "
    f"exported_at={FIXTURE_EXPORTED_AT}, "
    "record_count=6, confidence_threshold=0\n"
)


def _row(**kw) -> dict:
    row = {c: "" for c in CSV_COLUMNS}
    row.update(kw)
    return row


# Six rows, each earning its place:
#   1  exact MAC hit
#   2  the OUI parent of that MAC
#   3  same identifier string as the OUI parent but identifier_type != 'oui'
#      -> proves the OUI arm filters on type, as the DB path's WHERE does
#   4  an OUI row on a *different* prefix -> proves the prefix is not ignored
#   5  uppercase in the file -> proves case-folding on the CSV side
#   6  blank manufacturer/confidence + an embedded newline in `notes`
#      -> proves ""->None printing and that the reader is not line-wise
FIXTURE_ROWS = [
    _row(argus_record_id="aaaa1111", id="1", identifier="e4:aa:ea:80:a1:9b",
         identifier_type="mac", device_category="alpr",
         manufacturer="Flock Safety", confidence="70",
         source_type="crowdsourced", source_url="https://example.test/flock"),
    _row(argus_record_id="bbbb2222", id="22828", identifier="e4:aa:ea",
         identifier_type="oui", device_category="alpr",
         manufacturer="Flock Safety", confidence="85",
         source_type="crowdsourced", source_url="https://example.test/oui"),
    _row(argus_record_id="cccc3333", id="30000", identifier="e4:aa:ea",
         identifier_type="mac_range", device_category="decoy",
         manufacturer="Decoy Type Co", confidence="10",
         source_type="crowdsourced", source_url="https://example.test/decoy"),
    _row(argus_record_id="dddd4444", id="30001", identifier="00:11:22",
         identifier_type="oui", device_category="decoy",
         manufacturer="Decoy Prefix Co", confidence="10",
         source_type="crowdsourced", source_url="https://example.test/prefix"),
    _row(argus_record_id="eeee5555", id="30002", identifier="AB:CD:EF:01:02:03",
         identifier_type="mac", device_category="cctv_camera",
         manufacturer="Upper Case Co", confidence="60",
         source_type="crowdsourced", source_url="https://example.test/upper"),
    _row(argus_record_id="ffff6666", id="30003", identifier="ba:re:00:00:00:01",
         identifier_type="mac", device_category="unknown",
         manufacturer="", confidence="", source_type="crowdsourced",
         source_url="https://example.test/blank",
         notes="line one\nline two\nline three"),
]

# The four distinct manufacturer strings a naive CSV-derived count would
# produce. `status` must NOT print this as a manufacturers registry count —
# in the real corpus that mistake yields 18,748 against a true 261.
NAIVE_MANUFACTURER_COUNT = len(
    {r["manufacturer"] for r in FIXTURE_ROWS if r["manufacturer"]}
)


def _write_csv(path: Path, *, meta: bool = True, rows=None) -> None:
    rows = FIXTURE_ROWS if rows is None else rows
    with path.open("w", newline="", encoding="utf-8") as fh:
        if meta:
            fh.write(META_LINE)
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, count: int, exported_at: str,
                meta_count: int | None = None) -> None:
    """Write an export-shaped JSON feed.

    `meta_count` defaults to the true entry count. Passing a different value
    forges the disagreement between the `_meta.record_count` CLAIM and the
    measured `len(entries)` that `status` has to flag.
    """
    path.write_text(json.dumps({
        "_meta": {
            "record_count": count if meta_count is None else meta_count,
            "exported_at": exported_at,
        },
        "entries": [{"argus_record_id": f"x{i}"} for i in range(count)],
    }), encoding="utf-8")


def _populate_exports(d: Path) -> Path:
    """Write all four synthetic feeds into an existing directory."""
    _write_csv(d / "argus_export.csv")
    _write_json(d / "argus_export.json", 3, FIXTURE_JSON_EXPORTED_AT)
    _write_json(d / "argus_export_high_confidence.json", 2,
                FIXTURE_JSON_EXPORTED_AT)
    _write_json(d / "argus_export_behavioral_signatures.json", 1,
                FIXTURE_BEHAVIORAL_EXPORTED_AT)
    return d


@pytest.fixture
def fake_exports(tmp_path: Path) -> Path:
    """A synthetic exports/ directory with all four feeds."""
    d = tmp_path / "exports"
    d.mkdir()
    return _populate_exports(d)


@pytest.fixture
def missing_db(tmp_path: Path) -> Path:
    p = tmp_path / "no_such_dir" / "argus.db"
    assert not p.exists()
    return p


@pytest.fixture
def fresh_clone(tmp_path: Path) -> Path:
    """A fresh-public-clone-shaped tree: argus_cli.py + exports/, no db/.

    argus_cli.REPO_ROOT is `Path(__file__).resolve().parent`, so a copy of
    argus_cli.py living in <tmp>/clone/ makes <tmp>/clone/db/argus.db the
    DEFAULT probe path — and nothing creates it. Every flag can therefore be
    omitted, which is what a first-time user actually types.
    """
    root = tmp_path / "clone"
    root.mkdir()
    shutil.copy2(CLI, root / "argus_cli.py")
    (root / "exports").mkdir()
    _populate_exports(root / "exports")
    assert not (root / "db" / "argus.db").exists()
    return root


@pytest.fixture
def no_default_db(monkeypatch, tmp_path: Path) -> Path:
    """Move argus_cli.DEFAULT_DB_PATH somewhere that does not exist.

    For in-process calls. build_parser() evaluates DEFAULT_DB_PATH when it
    runs (inside main()), so the patch reaches the argparse default as well
    as _resolve_source's getattr fallback.
    """
    missing = tmp_path / "no_default_db_here" / "argus.db"
    assert not missing.exists()
    monkeypatch.setattr(argus_cli, "DEFAULT_DB_PATH", missing)
    return missing


def _run(*argv: str) -> subprocess.CompletedProcess:
    """Invoke the repo's CLI as a subprocess so the real process rc is measured."""
    return subprocess.run(
        [sys.executable, str(CLI), *argv],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


def _run_clone(root: Path, *argv: str) -> subprocess.CompletedProcess:
    """Invoke the fresh_clone's copy of the CLI, from inside the clone."""
    return subprocess.run(
        [sys.executable, str(root / "argus_cli.py"), *argv],
        capture_output=True, text=True, cwd=str(root),
    )


def _run_inproc(*argv: str) -> tuple[int, str, str]:
    """Invoke main() in-process, capturing stdout and stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = argus_cli.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def _line_starting(out: str, prefix: str) -> str:
    matches = [l for l in out.splitlines() if l.startswith(prefix)]
    assert len(matches) == 1, (prefix, matches)
    return matches[0]


# ─── an explicit --db-path is a demand, not a probe ────────────────────────
#
# REGRESSION GUARD. The fallback shipped inspecting only whether the DB file
# existed, so `--db-path /nope status` degraded to exports/ and returned 0.
# At 9b32212 it returned 1 with "argus_cli: database not found at /nope".
# Silently answering from a different data source than the one the operator
# named is the failure mode this whole module is supposed to prevent.


def test_explicit_missing_db_path_hard_fails_status(
    fake_exports: Path, missing_db: Path
) -> None:
    proc = _run("--db-path", str(missing_db),
                "--exports-dir", str(fake_exports), "status")
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
    assert f"argus_cli: database not found at {missing_db}" in proc.stderr, \
        proc.stderr
    assert "python3 -m db.init_db" in proc.stderr, proc.stderr
    # Not one byte of export data was served in its place.
    assert proc.stdout.strip() == "", proc.stdout
    assert "shipped exports" not in proc.stdout + proc.stderr


def test_explicit_missing_db_path_hard_fails_query(
    fake_exports: Path, missing_db: Path
) -> None:
    proc = _run("--db-path", str(missing_db),
                "--exports-dir", str(fake_exports),
                "query", "e4:aa:ea:80:a1:9b")
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
    assert "database not found at" in proc.stderr, proc.stderr
    # The identifier IS in the fixture export. Refusing it is the point.
    assert "Flock Safety" not in proc.stdout, proc.stdout


def test_explicit_missing_db_path_hard_fails_where_the_default_would_fall_back(
    fresh_clone: Path
) -> None:
    """The two arms side by side, in one tree, differing only in the flag.

    Without the control arm this test could pass in a tree where nothing
    works. The clone HAS a usable export feed and no DB: omitting --db-path
    succeeds from exports/, naming a missing DB fails. Same tree, same
    command, opposite outcomes — which is exactly the distinction
    _resolve_source now draws.
    """
    demanded = _run_clone(fresh_clone, "--db-path",
                          str(fresh_clone / "db" / "argus.db"), "status")
    assert demanded.returncode == 1, (demanded.returncode, demanded.stdout)
    assert "database not found at" in demanded.stderr, demanded.stderr
    assert demanded.stdout.strip() == "", demanded.stdout

    probed = _run_clone(fresh_clone, "status")
    assert probed.returncode == 0, (probed.stdout, probed.stderr)
    assert "Argus source: shipped exports" in probed.stdout, probed.stdout


def test_explicit_db_path_identical_to_the_default_is_still_a_demand(
    fresh_clone: Path
) -> None:
    """Typing the default path verbatim must not be downgraded to a probe.

    Kills the tempting-but-wrong implementation `args.db_path !=
    DEFAULT_DB_PATH`: the path passed here IS the default, so that check
    would call it a probe and fall back. Explicitness is a property of the
    command line, not of the value.
    """
    default_path = fresh_clone / "db" / "argus.db"
    proc = _run_clone(fresh_clone, "--db-path", str(default_path), "status")
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
    assert f"database not found at {default_path}" in proc.stderr, proc.stderr
    assert proc.stdout.strip() == "", proc.stdout


def test_explicit_db_path_is_overridden_by_an_explicit_source_exports(
    fake_exports: Path, missing_db: Path
) -> None:
    """`--source exports` outranks --db-path: the user named the source too,
    and the more specific instruction about WHERE TO READ wins. Only the
    unqualified `auto` case is ambiguous enough to need the demand rule."""
    proc = _run("--source", "exports", "--db-path", str(missing_db),
                "--exports-dir", str(fake_exports),
                "query", "e4:aa:ea:80:a1:9b")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "Flock Safety" in proc.stdout, proc.stdout


def test_default_probe_falls_back_with_no_flags_at_all(fresh_clone: Path) -> None:
    """The fresh-clone contract, typed the way a first-time user types it."""
    proc = _run_clone(fresh_clone, "query", "e4:aa:ea:80:a1:9b")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "Flock Safety" in proc.stdout, proc.stdout
    assert "canonical DB not found" in proc.stderr, proc.stderr


# ─── option abbreviation ───────────────────────────────────────────────────


def test_option_abbreviation_is_disabled() -> None:
    """Pins a DELIBERATE, BREAKING divergence from 9b32212.

    At 9b32212 the parser had two long options and `--s` was an unambiguous
    abbreviation of `--state-path`. Adding `--source` turned `--s` into
    argparse's "ambiguous option" error — a regression introduced by adding
    an option, with no change to the option that broke.

    The repair is allow_abbrev=False, which does NOT restore `--s`; it makes
    the failure deterministic and makes the accepted option surface exactly
    what --help prints, so no future option can retroactively change what an
    existing command line means. The cost is pinned here so it cannot be
    mistaken for an accident: FOUR abbreviations that worked at 9b32212 are
    now errors.
    """
    for abbrev in ("--s", "--st", "--db", "--exports"):
        proc = _run(abbrev, "status")
        assert proc.returncode == 2, (abbrev, proc.returncode, proc.stderr)
        assert f"unrecognized arguments: {abbrev}" in proc.stderr, \
            (abbrev, proc.stderr)
        # And specifically NOT the pre-fix failure mode.
        assert "ambiguous option" not in proc.stderr, (abbrev, proc.stderr)


def test_the_full_option_names_all_still_work(
    fake_exports: Path, tmp_path: Path
) -> None:
    """Non-vacuity control for the test above: the break is confined to
    abbreviations. Every canonical spelling, in both the space and `=`
    forms, is still accepted."""
    state = tmp_path / "PROJECT_STATE.md"
    state.write_text("**Current phase:** Phase 9 test.\n", encoding="utf-8")

    spaced = _run("--source", "exports", "--exports-dir", str(fake_exports),
                  "--state-path", str(state), "status")
    assert spaced.returncode == 0, (spaced.stdout, spaced.stderr)
    assert "Current phase: Phase 9 test." in spaced.stdout, spaced.stdout

    equals = _run(f"--source=exports", f"--exports-dir={fake_exports}",
                  f"--state-path={state}", "status")
    assert equals.returncode == 0, (equals.stdout, equals.stderr)
    assert equals.stdout == spaced.stdout, (equals.stdout, spaced.stdout)


# ─── exact hit ─────────────────────────────────────────────────────────────


def test_exports_mode_exact_hit(fresh_clone: Path) -> None:
    proc = _run_clone(fresh_clone, "query", "e4:aa:ea:80:a1:9b")
    assert proc.returncode == 0, proc.stderr
    assert "1 exact match(es) for e4:aa:ea:80:a1:9b:" in proc.stdout, proc.stdout
    assert "id=1 type=mac category=alpr manufacturer=Flock Safety confidence=70" \
        in proc.stdout, proc.stdout
    assert "source_url=https://example.test/flock" in proc.stdout, proc.stdout
    # The fallback announced itself rather than pretending it read the DB.
    assert "canonical DB not found" in proc.stderr, proc.stderr
    assert "exports/" in proc.stderr, proc.stderr


def test_exports_mode_exact_hit_is_case_insensitive(fresh_clone: Path) -> None:
    """Mirrors the DB path's `WHERE LOWER(identifier) = ?` on both sides:
    an uppercase needle and an uppercase stored value both fold."""
    proc = _run_clone(fresh_clone, "query", "ab:cd:ef:01:02:03")
    assert proc.returncode == 0, proc.stderr
    assert "manufacturer=Upper Case Co" in proc.stdout, proc.stdout


def test_exports_mode_blank_fields_print_as_none(
    fake_exports: Path, no_default_db: Path
) -> None:
    """A blank CSV field is a SQL NULL, and must print like one.

    174 rows of the shipped CSV have a blank confidence. Printing a bare
    `confidence=` instead of `confidence=None` diverges from the DB path.
    """
    rc, out, _ = _run_inproc(
        "--exports-dir", str(fake_exports), "query", "ba:re:00:00:00:01",
    )
    assert rc == 0
    assert "manufacturer=None" in out, out
    assert "confidence=None" in out, out


# ─── OUI-prefix hit ────────────────────────────────────────────────────────


def test_exports_mode_oui_prefix_hit(
    fake_exports: Path, no_default_db: Path
) -> None:
    rc, out, _ = _run_inproc(
        "--exports-dir", str(fake_exports), "query", "e4:aa:ea:80:a1:9b",
    )
    assert rc == 0
    assert "1 OUI parent match(es) (e4:aa:ea):" in out, out
    assert "id=22828 type=oui" in out, out
    # Type filter is live: row 3 shares the identifier string but is a
    # mac_range, and the DB path's `WHERE identifier_type = 'oui'` excludes it.
    assert "Decoy Type Co" not in out, out
    # Prefix filter is live: row 4 is an OUI on a different prefix.
    assert "Decoy Prefix Co" not in out, out


def test_oui_arm_does_not_fire_for_a_non_mac_needle(
    fake_exports: Path, no_default_db: Path
) -> None:
    """The DB path gates the OUI arm on `[0-9a-f]{2}(:[0-9a-f]{2}){5}`.

    A bare 3-octet OUI is not a 6-octet MAC, so it gets an exact hit and no
    OUI-parent block. Without the gate this would recurse on itself.
    """
    rc, out, _ = _run_inproc(
        "--exports-dir", str(fake_exports), "query", "e4:aa:ea",
    )
    assert rc == 0
    assert "exact match(es)" in out, out
    assert "OUI parent match(es)" not in out, out


# ─── clean miss: the absence is qualified ──────────────────────────────────


def test_exports_mode_clean_miss_exits_1(fresh_clone: Path) -> None:
    proc = _run_clone(fresh_clone, "query", "de:ad:be:ef:ca:fe")
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
    # Echoes the raw argument, exactly as the DB path does.
    assert proc.stdout.startswith(
        "No records for identifier: de:ad:be:ef:ca:fe"), proc.stdout


def test_exports_mode_miss_says_the_absence_is_from_the_export(
    fresh_clone: Path
) -> None:
    """An unqualified "No records for identifier: X" overstates the search.

    The export feed carries ACTIVE rows only; superseded and withdrawn
    identifiers are not in it at all. A miss therefore means "not in the
    shipped export", not "not in Argus", and exports mode has to say which.
    The DB path, which really did search the whole registry, keeps the
    unqualified wording — see the control below.
    """
    proc = _run_clone(fresh_clone, "query", "de:ad:be:ef:ca:fe")
    assert proc.returncode == 1, proc.stdout
    out = proc.stdout
    # Names the artifact actually searched.
    assert "argus_export.csv" in out, out
    # Says what the export omits, and where the full answer lives.
    assert "active rows only" in out, out
    assert "superseded" in out, out
    assert "--source db" in out, out
    # Does NOT claim the identifier is absent from the database.
    assert out.strip() != "No records for identifier: de:ad:be:ef:ca:fe", out


def test_exports_mode_miss_does_not_fabricate_a_gap_size(
    fresh_clone: Path
) -> None:
    """The message must not carry a hard-coded count of the missing rows.

    How many identifiers are in the DB but not the export is a property of
    whichever export is on disk. A number baked into the source would be a
    fabrication one regeneration from being false, which is the same defect
    class as a hard-coded schema_version.
    """
    proc = _run_clone(fresh_clone, "query", "de:ad:be:ef:ca:fe")
    note = proc.stdout.split("\n", 1)[1]
    digits = [w for w in note.replace("(", " ").replace(")", " ").split()
              if any(c.isdigit() for c in w)]
    assert digits == [], (digits, note)


def test_exports_mode_miss_echoes_the_raw_argument(
    fake_exports: Path, no_default_db: Path
) -> None:
    rc, out, _ = _run_inproc(
        "--exports-dir", str(fake_exports), "query", "  DE:AD:BE:EF:CA:FE  ",
    )
    assert rc == 1
    assert "No records for identifier:   DE:AD:BE:EF:CA:FE  " in out, out


# ─── --source db still hard-fails ──────────────────────────────────────────


def test_source_db_hard_fails_without_a_db_status(
    fake_exports: Path, missing_db: Path
) -> None:
    """No silent degradation: an explicit --source db must not fall back."""
    proc = _run("--source", "db", "--db-path", str(missing_db),
                "--exports-dir", str(fake_exports), "status")
    assert proc.returncode != 0, proc.stdout
    assert proc.returncode == 1, proc.returncode
    assert "database not found at" in proc.stderr, proc.stderr
    assert "python3 -m db.init_db" in proc.stderr, proc.stderr
    # It did not quietly serve export data instead.
    assert "shipped exports" not in proc.stdout, proc.stdout
    assert proc.stdout.strip() == "", proc.stdout


def test_source_db_hard_fails_without_a_db_query(
    fake_exports: Path, missing_db: Path
) -> None:
    proc = _run("--source", "db", "--db-path", str(missing_db),
                "--exports-dir", str(fake_exports),
                "query", "e4:aa:ea:80:a1:9b")
    assert proc.returncode == 1, (proc.returncode, proc.stdout)
    assert "database not found at" in proc.stderr, proc.stderr
    # The row exists in the fixture exports; --source db must still refuse it.
    assert "Flock Safety" not in proc.stdout, proc.stdout


def test_source_db_hard_fails_in_a_clone_with_no_db_at_all(
    fresh_clone: Path
) -> None:
    """`--source db` with no --db-path: the default probe path is missing,
    and the explicit source still refuses to degrade."""
    proc = _run_clone(fresh_clone, "--source", "db", "status")
    assert proc.returncode == 1, (proc.returncode, proc.stdout)
    assert "database not found at" in proc.stderr, proc.stderr
    assert proc.stdout.strip() == "", proc.stdout


def test_source_exports_never_opens_the_db(
    fake_exports: Path, tmp_path: Path
) -> None:
    """--source exports must not consult the DB even when a file is there.

    The db-path here is a real, existing file that is NOT a SQLite database.
    Exports mode succeeds precisely because it never opens it; the control
    arm below shows the same path is fatal under --source db.
    """
    junk_db = tmp_path / "argus.db"
    junk_db.write_text("this is not a sqlite database", encoding="utf-8")

    proc = _run("--source", "exports", "--db-path", str(junk_db),
                "--exports-dir", str(fake_exports),
                "query", "e4:aa:ea:80:a1:9b")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "Flock Safety" in proc.stdout, proc.stdout

    # Control: the same junk path IS opened (and fails) under --source db.
    control = _run("--source", "db", "--db-path", str(junk_db),
                   "query", "e4:aa:ea:80:a1:9b")
    assert control.returncode != 0, (control.stdout, control.stderr)


# ─── meta-line skipping ────────────────────────────────────────────────────


def test_meta_line_is_skipped_not_read_as_header(fake_exports: Path) -> None:
    csv_path = fake_exports / "argus_export.csv"
    rows = list(argus_cli._csv_rows(csv_path))
    assert len(rows) == len(FIXTURE_ROWS), rows
    assert list(rows[0].keys()) == CSV_COLUMNS, rows[0].keys()
    # No row overflowed into DictReader's restkey.
    assert all(None not in r for r in rows), rows


def test_naive_dictreader_misparses_proving_the_skip_is_load_bearing(
    fake_exports: Path,
) -> None:
    """Non-vacuity control for the test above.

    If the skip were removed, csv.DictReader would take the `# meta:` comment
    as the header. This asserts that failure mode is real, so the passing
    test above is evidence of something.
    """
    csv_path = fake_exports / "argus_export.csv"
    with csv_path.open(newline="", encoding="utf-8") as fh:
        naive = csv.DictReader(fh)
        fieldnames = list(naive.fieldnames or [])
        first = next(naive)
    assert fieldnames != CSV_COLUMNS
    assert fieldnames[0].startswith("# meta:"), fieldnames
    assert len(fieldnames) == 4, fieldnames
    # The 16-field data rows overflow into restkey.
    assert None in first, first


def test_meta_line_values_are_parsed(fake_exports: Path) -> None:
    meta = argus_cli._csv_meta(fake_exports / "argus_export.csv")
    assert meta == {
        "schema_version": FIXTURE_SCHEMA_VERSION,
        "exported_at": FIXTURE_EXPORTED_AT,
        "record_count": "6",
        "confidence_threshold": "0",
    }, meta


def test_csv_without_a_meta_line_still_parses(
    tmp_path: Path, fresh_clone: Path
) -> None:
    """The skip is conditional: a CSV whose line 1 is the real header must
    not lose its first data row."""
    d = tmp_path / "exports_nometa"
    d.mkdir()
    _write_csv(d / "argus_export.csv", meta=False)
    rows = list(argus_cli._csv_rows(d / "argus_export.csv"))
    assert len(rows) == len(FIXTURE_ROWS), rows
    assert list(rows[0].keys()) == CSV_COLUMNS

    proc = _run_clone(fresh_clone, "--exports-dir", str(d),
                      "query", "e4:aa:ea:80:a1:9b")
    assert proc.returncode == 0, proc.stderr
    assert "Flock Safety" in proc.stdout, proc.stdout


def test_embedded_newlines_do_not_inflate_the_row_count(
    fake_exports: Path,
) -> None:
    """`source_excerpt` and `notes` carry embedded newlines inside quoted
    fields, so `wc -l` is not a row count (47,534 lines vs 43,126 rows in the
    shipped CSV). Proves the reader goes through the csv module."""
    csv_path = fake_exports / "argus_export.csv"
    raw_lines = csv_path.read_text(encoding="utf-8").count("\n")
    parsed = len(list(argus_cli._csv_rows(csv_path)))
    assert raw_lines > parsed + 2, (raw_lines, parsed)
    assert parsed == len(FIXTURE_ROWS)


# ─── anti-fabrication: status reports the FILE, not a constant ─────────────
#
# The property this module exists for. Two mutants used to survive the whole
# suite — hard-coding schema_version="35" and exported_at="2026-08-21T12:06:18Z"
# in _status_from_exports — because every fixture carried the shipped values
# too, so a constant and a measurement were indistinguishable. The fixture now
# carries values the shipped corpus does not have, and these tests assert both
# halves: the fixture's value IS printed, and the shipped value is NOWHERE in
# the output.


def test_status_reports_the_files_schema_version_not_a_hard_coded_one(
    fake_exports: Path, no_default_db: Path
) -> None:
    rc, out, _ = _run_inproc("--exports-dir", str(fake_exports), "status")
    assert rc == 0, out
    line = _line_starting(out, "Schema version:")
    assert line.startswith(f"Schema version: {FIXTURE_SCHEMA_VERSION} "), line
    # Kills `schema_version = "35"`.
    assert SHIPPED_SCHEMA_VERSION not in line, line
    # Still says where it came from, and what it cannot know.
    assert "argus_export.csv meta line" in line, line


def test_status_reports_the_files_exported_at_not_a_hard_coded_one(
    fake_exports: Path, no_default_db: Path
) -> None:
    rc, out, _ = _run_inproc("--exports-dir", str(fake_exports), "status")
    assert rc == 0, out
    line = _line_starting(out, "Exported at:")
    assert line == f"Exported at: {FIXTURE_EXPORTED_AT} (argus_export.csv)", line
    # Kills `exported_at = "2026-08-21T12:06:18Z"` wherever it is planted:
    # the shipped stamps appear nowhere in the whole of stdout.
    assert SHIPPED_EXPORTED_AT not in out, out
    assert SHIPPED_BEHAVIORAL_EXPORTED_AT not in out, out


def test_status_reports_each_json_feeds_own_exported_at(
    fake_exports: Path, no_default_db: Path
) -> None:
    """There is no single repo-wide exported_at, so nothing may print one.

    Measured on the shipped exports: the CSV and two JSON feeds carry
    2026-08-21T12:06:18Z, but argus_export_behavioral_signatures.json carries
    2026-08-20T17:48:39Z. The fixture reproduces that divergence with its own
    values, and each feed must be stamped from its own file.
    """
    rc, out, _ = _run_inproc("--exports-dir", str(fake_exports), "status")
    assert rc == 0, out
    assert (f"  argus_export.json: 3 (exported_at {FIXTURE_JSON_EXPORTED_AT})"
            in out), out
    assert (f"  argus_export_behavioral_signatures.json: 1 "
            f"(exported_at {FIXTURE_BEHAVIORAL_EXPORTED_AT})") in out, out
    # Non-vacuity: the two stamps really are different, so "print one stamp
    # for everything" cannot pass this.
    assert FIXTURE_JSON_EXPORTED_AT != FIXTURE_BEHAVIORAL_EXPORTED_AT


def test_status_counts_the_csv_rows_rather_than_trusting_the_meta_claim(
    tmp_path: Path, no_default_db: Path
) -> None:
    """The meta line is a claim, not a measurement. Cross-check it. (CSV arm.)"""
    d = tmp_path / "exports"
    d.mkdir()
    _write_csv(d / "argus_export.csv", rows=FIXTURE_ROWS[:2])  # meta says 6
    rc, out, _ = _run_inproc("--exports-dir", str(d), "status")
    assert rc == 0
    assert "  argus_export.csv: 2" in out, out
    assert "WARNING: meta line claims record_count=6" in out, out


def test_status_flags_a_json_meta_record_count_that_disagrees(
    tmp_path: Path, no_default_db: Path
) -> None:
    """Same cross-check on the JSON arm, which was entirely untested.

    Deleting the `summary["meta_count"] != summary["count"]` branch left the
    suite fully green. `_meta.record_count` is a claim written by the export
    generator; `len(entries)` is what is actually in the file. A generator
    that writes the count before filtering rows produces exactly this skew,
    and it must be reported, not smoothed over.
    """
    d = tmp_path / "exports"
    d.mkdir()
    _write_csv(d / "argus_export.csv")
    _write_json(d / "argus_export.json", 3, FIXTURE_JSON_EXPORTED_AT,
                meta_count=99)
    _write_json(d / "argus_export_high_confidence.json", 2,
                FIXTURE_JSON_EXPORTED_AT, meta_count=0)
    _write_json(d / "argus_export_behavioral_signatures.json", 1,
                FIXTURE_BEHAVIORAL_EXPORTED_AT)

    rc, out, _ = _run_inproc("--exports-dir", str(d), "status")
    assert rc == 0, out

    forged = _line_starting(out, "  argus_export.json:")
    assert forged.startswith("  argus_export.json: 3"), forged
    assert "WARNING: meta line claims record_count=99" in forged, forged

    # record_count=0 is the nastiest case: falsy, so an `if meta_count:`
    # guard would skip it and silently under-report an empty-looking feed.
    zero = _line_starting(out, "  argus_export_high_confidence.json:")
    assert zero.startswith("  argus_export_high_confidence.json: 2"), zero
    assert "WARNING: meta line claims record_count=0" in zero, zero

    # Control, same run: the honest feed is NOT flagged, so the warning is
    # discriminating rather than unconditional.
    honest = _line_starting(out, "  argus_export_behavioral_signatures.json:")
    assert "WARNING" not in honest, honest


def test_status_does_not_warn_when_every_json_meta_count_agrees(
    fake_exports: Path, no_default_db: Path
) -> None:
    """Non-vacuity control for the test above, on a wholly consistent set."""
    rc, out, _ = _run_inproc("--exports-dir", str(fake_exports), "status")
    assert rc == 0, out
    assert "WARNING" not in out, out


@pytest.mark.skipif(not (REAL_EXPORTS / "argus_export.csv").exists(),
                    reason="shipped exports/argus_export.csv not present")
def test_the_shipped_export_still_carries_the_values_pinned_above() -> None:
    """Keeps SHIPPED_* honest.

    The anti-fabrication tests are only meaningful while SHIPPED_* really are
    the values a hard-coding implementation would reach for. If exports/ is
    regenerated and these constants are not updated, this fails loudly rather
    than letting the mutants above quietly stop being killed.
    """
    meta = argus_cli._csv_meta(REAL_EXPORTS / "argus_export.csv")
    assert meta.get("schema_version") == SHIPPED_SCHEMA_VERSION, meta
    assert meta.get("exported_at") == SHIPPED_EXPORTED_AT, meta

    behavioral = argus_cli._json_export_summary(
        REAL_EXPORTS / "argus_export_behavioral_signatures.json")
    assert behavioral is not None
    assert behavioral["exported_at"] == SHIPPED_BEHAVIORAL_EXPORTED_AT, behavioral
    # The divergence the fixture models is real, not an invention.
    assert behavioral["exported_at"] != SHIPPED_EXPORTED_AT


# ─── status honesty: no fabricated zeros ───────────────────────────────────


def test_status_exports_mode_never_prints_a_fabricated_zero(
    fake_exports: Path, no_default_db: Path
) -> None:
    rc, out, err = _run_inproc("--exports-dir", str(fake_exports), "status")
    assert rc == 0, out

    # Every DB table is declared unavailable, not counted as 0.
    block = out.split("Row counts:", 1)[1]
    for table in argus_cli.EXPECTED_TABLES:
        assert f"  {table}: unavailable (requires canonical DB)" in block, block
        assert f"  {table}: 0" not in block, block

    # No line in the row-counts block resolves to a bare number at all.
    for line in block.splitlines():
        if line.startswith("  ") and ":" in line:
            assert not line.rsplit(":", 1)[1].strip().isdigit(), line

    assert f"Manufacturers: {argus_cli.UNAVAILABLE}" in out, out
    assert f"Sources: {argus_cli.UNAVAILABLE}" in out, out
    assert "Last extraction run: unavailable (requires canonical DB)" in out, out
    assert "canonical DB not found" in err, err


def test_status_exports_mode_does_not_derive_registries_from_csv_columns(
    fake_exports: Path, no_default_db: Path
) -> None:
    """The specific wrong-but-plausible failure this guards.

    Counting distinct `manufacturer` strings in the CSV gives 18,748 against a
    true registry of 261, and distinct `source_url` gives 1,511 against 98.
    The fixture's naive count is asserted non-zero so this is not vacuous.
    """
    assert NAIVE_MANUFACTURER_COUNT > 0
    rc, out, _ = _run_inproc("--exports-dir", str(fake_exports), "status")
    assert rc == 0
    mfr_line = _line_starting(out, "Manufacturers:")
    assert str(NAIVE_MANUFACTURER_COUNT) not in mfr_line, mfr_line
    assert mfr_line == f"Manufacturers: {argus_cli.UNAVAILABLE}", mfr_line


def test_status_exports_mode_reports_all_four_record_counts(
    fake_exports: Path, no_default_db: Path
) -> None:
    rc, out, _ = _run_inproc("--exports-dir", str(fake_exports), "status")
    assert rc == 0
    assert f"  argus_export.csv: {len(FIXTURE_ROWS)}" in out, out
    assert "  argus_export.json: 3 " in out, out
    assert "  argus_export_high_confidence.json: 2 " in out, out
    assert "  argus_export_behavioral_signatures.json: 1 " in out, out


def test_status_reports_missing_json_feeds_as_unavailable_not_zero(
    tmp_path: Path, no_default_db: Path
) -> None:
    d = tmp_path / "exports"
    d.mkdir()
    _write_csv(d / "argus_export.csv")  # CSV only; no JSON feeds
    rc, out, _ = _run_inproc("--exports-dir", str(d), "status")
    assert rc == 0
    for name in argus_cli.EXPORT_JSON_NAMES:
        assert f"  {name}: unavailable (file missing or unreadable)" in out, out
        assert f"  {name}: 0" not in out, out


def test_no_db_and_no_exports_fails_loudly(fresh_clone: Path) -> None:
    """With neither source present there is nothing to serve. Fail with a
    message that names the feed, rather than emitting an empty-looking status."""
    empty = fresh_clone / "empty_exports"
    empty.mkdir()
    proc = _run_clone(fresh_clone, "--exports-dir", str(empty), "status")
    assert proc.returncode == 1, (proc.returncode, proc.stdout)
    assert "no canonical DB and no export feed" in proc.stderr, proc.stderr


# ─── the README quickstart, against the real shipped exports ───────────────
#
# exports/ is tracked, so these run in a fresh clone. They are the actual
# fresh-clone contract: the clone's own default DB path is absent, and the
# real shipped exports answer the query.


@pytest.mark.skipif(not (REAL_EXPORTS / "argus_export.csv").exists(),
                    reason="shipped exports/argus_export.csv not present")
def test_readme_quickstart_query_works_without_a_db(fresh_clone: Path) -> None:
    proc = _run_clone(fresh_clone, "--exports-dir", str(REAL_EXPORTS),
                      "query", "e4:aa:ea:80:a1:9b")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "Flock Safety" in proc.stdout, proc.stdout
    assert "type=mac category=alpr" in proc.stdout, proc.stdout


@pytest.mark.skipif(not (REAL_EXPORTS / "argus_export.csv").exists(),
                    reason="shipped exports/argus_export.csv not present")
def test_readme_quickstart_status_works_without_a_db(fresh_clone: Path) -> None:
    proc = _run_clone(fresh_clone, "--exports-dir", str(REAL_EXPORTS), "status")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "Argus source: shipped exports" in proc.stdout, proc.stdout
    assert f"Schema version: {SHIPPED_SCHEMA_VERSION} " in proc.stdout, \
        proc.stdout
    assert "unavailable (requires canonical DB)" in proc.stdout, proc.stdout


# ─── DB path unchanged ─────────────────────────────────────────────────────


@pytest.mark.canonical_db
@pytest.mark.skipif(not REAL_DB.exists(), reason="canonical db/argus.db absent")
def test_db_present_auto_does_not_fall_back() -> None:
    """auto must prefer the DB, and must print nothing on stderr doing so."""
    proc = _run("status")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith(f"Argus DB: {REAL_DB}"), proc.stdout[:200]
    assert "shipped exports" not in proc.stdout, proc.stdout
    assert "unavailable (requires canonical DB)" not in proc.stdout, proc.stdout
    assert proc.stderr == "", proc.stderr


@pytest.mark.canonical_db
@pytest.mark.skipif(not REAL_DB.exists(), reason="canonical db/argus.db absent")
def test_explicit_db_path_to_a_db_that_exists_is_served_from_the_db() -> None:
    """The demand rule must not break the case it is protecting: naming a DB
    that IS there reads that DB, silently, with no fallback chatter."""
    proc = _run("--db-path", str(REAL_DB), "status")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith(f"Argus DB: {REAL_DB}"), proc.stdout[:200]
    assert proc.stderr == "", proc.stderr


@pytest.mark.canonical_db
@pytest.mark.skipif(not REAL_DB.exists(), reason="canonical db/argus.db absent")
def test_db_path_query_output_is_unchanged() -> None:
    proc = _run("query", "e4:aa:ea:80:a1:9b")
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == "", proc.stderr
    assert "1 exact match(es) for e4:aa:ea:80:a1:9b:" in proc.stdout
    # The DB carries superseded rows the active-only export does not, so the
    # DB path legitimately returns MORE OUI parents (2) than the exports
    # path (1). id=22770 is superseded_by=22828 in the DB; the exports feed
    # omits it. This divergence is expected, not a fallback defect — and it
    # is exactly why an exports-mode miss must qualify its "No records".
    assert "2 OUI parent match(es) (e4:aa:ea):" in proc.stdout, proc.stdout
    assert "id=22770 type=oui" in proc.stdout, proc.stdout
    # ...and the CLI does not *say* 22770 is superseded: the OUI arm's SELECT
    # omits the superseded_by column, so _print_identifier_row's
    # `"superseded_by" in r.keys()` guard suppresses the line. Pinned as
    # observed behaviour of the untouched DB path.
    assert "superseded_by=" not in proc.stdout, proc.stdout


@pytest.mark.canonical_db
@pytest.mark.skipif(not REAL_DB.exists(), reason="canonical db/argus.db absent")
def test_db_path_miss_keeps_the_unqualified_wording() -> None:
    """The DB path really did search the whole registry, superseded rows
    included, so its miss message must NOT acquire the exports caveat.

    Needle choice matters. `00:00:00:00:00:00` is NOT a miss against the
    canonical DB: it has no exact row, but the OUI arm matches prefix
    `00:00:00`, which carries 15 rows, so the command exits 0. Measured at
    HEAD and at 9b32212 alike. `de:ad:be:ef:ca:fe` misses on both arms in
    both the DB and the shipped export.
    """
    proc = _run("--source", "db", "query", "de:ad:be:ef:ca:fe")
    assert proc.returncode == 1, (proc.returncode, proc.stdout)
    assert proc.stdout.strip() == \
        "No records for identifier: de:ad:be:ef:ca:fe", proc.stdout
    # Specifically: none of the exports-mode qualification leaked across.
    assert "argus_export.csv" not in proc.stdout, proc.stdout
    assert "active rows only" not in proc.stdout, proc.stdout


@pytest.mark.canonical_db
@pytest.mark.skipif(not REAL_DB.exists(), reason="canonical db/argus.db absent")
def test_cmd_status_still_accepts_a_bare_two_attribute_namespace() -> None:
    """tests/test_argus_cli_status.py builds Namespace(db_path=, state_path=)
    with no `source` and no `db_path_explicit` attribute. The resolver must
    read both via getattr and default to the auto probe rather than raising
    AttributeError."""
    ns = argparse.Namespace(db_path=REAL_DB, state_path=REPO_ROOT / "PROJECT_STATE.md")
    out = io.StringIO()
    with redirect_stdout(out):
        rc = argus_cli.cmd_status(ns)
    assert rc == 0
    assert out.getvalue().startswith(f"Argus DB: {REAL_DB}")
