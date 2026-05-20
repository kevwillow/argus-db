"""Tests for argus_cli.py `status` command — post-CP31 hub+arm reporting.

Per MAC-198 dispatch §Tests: assert hub+arm reporting line present in output.

The status command pulls from the live `db/argus.db` by default, but we
exercise it against a synthetic in-process DB to avoid coupling to the
production corpus row counts.
"""

from __future__ import annotations

import io
import sqlite3
from contextlib import redirect_stdout
from pathlib import Path

import pytest

import argus_cli

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"


def _build_db(db_path: Path, *, with_cp31: bool) -> None:
    """Apply migrations 0001..0024 (optionally +0025) to a file-backed DB.

    The 0001 initial migration seeds the canonical §2.1 manufacturers list;
    Parrot lands at id=25 deterministically across runs.
    """
    conn = sqlite3.connect(str(db_path))
    last = 25 if with_cp31 else 24
    files = sorted(
        p for p in MIGRATIONS_DIR.glob("*.sql")
        if p.name[:4].isdigit() and int(p.name[:4]) <= last
    )
    for f in files:
        conn.executescript(f.read_text())
    conn.close()


def _run_status(db_path: Path, state_path: Path) -> str:
    """Invoke argus_cli.cmd_status directly and capture stdout."""
    import argparse
    ns = argparse.Namespace(db_path=db_path, state_path=state_path)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = argus_cli.cmd_status(ns)
    assert rc == 0, f"cmd_status returned {rc}"
    return buf.getvalue()


def test_status_hub_arm_line_post_cp31(tmp_path: Path) -> None:
    db_path = tmp_path / "argus.db"
    state_path = tmp_path / "PROJECT_STATE.md"
    state_path.write_text("Current phase: test\n")

    _build_db(db_path, with_cp31=True)

    output = _run_status(db_path, state_path)

    # Hub+arm line shape: "Manufacturers: N visible (hub) + 1 hidden (arm) = N+1 total"
    # Fresh-migration seed yields 34 hubs + 1 Parrot Automotive arm = 35 total.
    assert "Manufacturers:" in output, output
    assert "visible (hub)" in output, output
    assert "hidden (arm)" in output, output
    assert "= 35 total" in output, output
    assert "34 visible (hub)" in output, output
    assert "1 hidden (arm)" in output, output


def test_status_omits_hub_arm_line_pre_cp31(tmp_path: Path) -> None:
    """Pre-CP31 backup DBs lack the new columns; the status command must
    degrade gracefully (no hub+arm line, no exception)."""
    db_path = tmp_path / "argus.db"
    state_path = tmp_path / "PROJECT_STATE.md"
    state_path.write_text("Current phase: test\n")

    _build_db(db_path, with_cp31=False)

    output = _run_status(db_path, state_path)

    # No hub/arm line surfaces against a pre-CP31 DB
    assert "visible (hub)" not in output, output
    assert "hidden (arm)" not in output, output
    # But the row-counts block still includes manufacturers
    assert "manufacturers:" in output, output
