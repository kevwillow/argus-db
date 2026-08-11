"""MAC-713 -- proof fixtures for ``scripts/check_migration_guards.py``.

The gate's job is to prove a migration's preconditions can STOP its writes. Before
MAC-713 it recognized only ONE of the two guard-declaration forms in the tree:

    form `check`  CREATE TEMP TABLE _x (ok INTEGER CHECK (ok = 1));
                  INSERT INTO _x(ok) SELECT CASE WHEN (<pre>) THEN 1 ELSE 0 END;

    form `ctas`   CREATE TEMP TABLE _x AS SELECT 1 AS ok WHERE <pre>;

Both fail closed. The `ctas` form does it without an INSERT and without a CHECK: a false
WHERE creates the table EMPTY, so `COUNT(*) = 1` is false and every write carrying that
arm matches zero rows. mig-0057:200 (``_mac707_go``) is that form, and the gate exited 1
on it -- a false positive that blocked the push gate on a genuinely fail-closed migration.

Per R7 a green result is not evidence a gate works, so every acceptance arm here is paired
with the rejection arm that makes it non-vacuous:

  T1  ctas ACCEPT   -- a CTAS-guarded write reads GUARDED, verdict FAIL-CLOSED.
  T2  ctas REJECT   -- the SAME fixture with the `COUNT(*)` arm deleted must still read
                       UNGUARDED. Without T2, T1 certifies nothing: a regex that matched
                       everything would pass it.
  T3  over-accept   -- `CREATE TEMP TABLE _x AS SELECT 1 AS ok;` (no WHERE) is
                       UNCONDITIONAL: it always holds one row, so a write gated on it can
                       never be stopped. It must NOT be accepted as a guard. This is the
                       arm that proves the MAC-713 widening did not become a hole.
  T4  no regression -- the `check` form still reads GUARDED, and a bare CHECK-form
                       migration with an unguarded write still FAILS.
  T5  guard-const   -- the CTAS branch of ``guard_const_rows``: `= 1` is OK, `= 2` is a
                       MISMATCH. A CTAS guard has zero INSERTs, so the pre-MAC-713 rule
                       would have compared `[2]` against `inserts=0` and been right for
                       the wrong reason -- and compared `[1]` against `inserts=0` and been
                       flatly wrong. Both directions are asserted.
  T6  live 0057     -- the real db/migrations/0057_*.sql, on disk, reads FAIL-CLOSED with
                       no guard-constant MISMATCH. This is the issue's acceptance line.

T1-T5 build their own SQL in ``tmp_path`` and pass a synthetic ``canon`` set, so they do
not depend on db/argus.db or on the on-disk migration corpus. T6 is the one arm that
reads the live tree, and it asserts only about mig-0057 -- not a global exit code, which
would make this file hostage to any unrelated migration landing later.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "check_migration_guards.py"
MIG_0057 = REPO / "db" / "migrations" / "0057_mac707_geographic_scope_carry_forward.sql"

CANON = {"identifiers"}


def _load_gate():
    spec = importlib.util.spec_from_file_location("check_migration_guards", GATE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_migration_guards"] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()


# --------------------------------------------------------------------------------------
# Fixture SQL. Deliberately minimal: one guard table, one canonical write. The only thing
# that varies between arms is the guard's declaration form and whether the write carries
# its `COUNT(*)` arm.
# --------------------------------------------------------------------------------------

_CTAS_GUARD = """\
.bail on
BEGIN;

CREATE TEMP TABLE _fx_pre_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _fx_pre_1fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers) < 1)
  THEN 0 ELSE 1 END;

CREATE TEMP TABLE _fx_go AS
SELECT 1 AS ok WHERE
       (SELECT COUNT(*) FROM identifiers WHERE id = 1) = 1;

UPDATE identifiers
   SET geographic_scope = 'US'
 WHERE id = 1%s;

COMMIT;
"""

# The guarded arm, and its absence. Same bytes either side of this one clause.
_ARM = "\n   AND (SELECT COUNT(*) FROM _fx_go) = 1"


def _write(tmp_path: Path, name: str, sql: str) -> str:
    p = tmp_path / name
    p.write_text(sql, encoding="utf-8")
    return str(p)


# --------------------------------------------------------------------------------------
# T1 / T2 -- the CTAS guard is recognized, and the recognition is load-bearing.
# --------------------------------------------------------------------------------------

def test_t1_ctas_guarded_write_reads_guarded(tmp_path):
    """A CTAS-declared guard cited by the write reads GUARDED / FAIL-CLOSED."""
    r = gate.analyze(_write(tmp_path, "0900_ctas_ok.sql", _CTAS_GUARD % _ARM), CANON)

    assert r is not None, "fixture must enter the scan"
    assert "_fx_go" in r["guard_tbls"], "CTAS guard table must be discovered"
    assert r["guard_kind"]["_fx_go"] == "ctas"
    assert (r["writes"], r["guarded"], r["unguarded"]) == (1, 1, [])
    assert gate.verdict(r) == ("FAIL-CLOSED (both arms)", False)


def test_t2_ctas_guard_without_count_arm_still_reads_unguarded(tmp_path):
    """Delete ONLY the `COUNT(*)` arm: the write must go back to UNGUARDED.

    This is what makes T1 evidence. The guard table is still declared and still
    discovered; the write simply no longer cites it, and nothing stops that write.
    """
    r = gate.analyze(_write(tmp_path, "0901_ctas_noarm.sql", _CTAS_GUARD % ""), CANON)

    assert r is not None
    assert "_fx_go" in r["guard_tbls"], "the guard is still declared -- only the arm went"
    assert (r["writes"], r["guarded"]) == (1, 0)
    assert len(r["unguarded"]) == 1
    label, failed = gate.verdict(r)
    assert failed is True
    assert "CLI-ONLY" in label


# --------------------------------------------------------------------------------------
# T3 -- the widening must not accept a CTAS that can never fail closed.
# --------------------------------------------------------------------------------------

_UNCONDITIONAL_CTAS = """\
.bail on
BEGIN;

CREATE TEMP TABLE _fx_pre_1fail (ok INTEGER CHECK (ok = 1));
INSERT INTO _fx_pre_1fail(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers) < 1)
  THEN 0 ELSE 1 END;

CREATE TEMP TABLE _fx_always AS SELECT 1 AS ok;

UPDATE identifiers
   SET geographic_scope = 'US'
 WHERE id = 1
   AND (SELECT COUNT(*) FROM _fx_always) = 1;

COMMIT;
"""


def test_t3_unconditional_ctas_is_not_a_guard(tmp_path):
    """`AS SELECT 1 AS ok` with no WHERE always holds one row -- it can never stop a write.

    The fixture carries a CHECK-form table too, so the file enters the scan on its own
    merits; the assertion is specifically that the unconditional CTAS is not blessed and
    the write citing it is still counted UNGUARDED.
    """
    r = gate.analyze(_write(tmp_path, "0902_uncond.sql", _UNCONDITIONAL_CTAS), CANON)

    assert r is not None
    assert "_fx_always" not in r["guard_tbls"], (
        "an unconditional CTAS must never be accepted as a guard"
    )
    assert (r["writes"], r["guarded"]) == (1, 0)
    assert len(r["unguarded"]) == 1
    assert gate.verdict(r)[1] is True


# --------------------------------------------------------------------------------------
# T4 -- the CHECK form is untouched, in both directions.
# --------------------------------------------------------------------------------------

_CHECK_GUARD = """\
.bail on
BEGIN;

CREATE TEMP TABLE _fx_go (ok INTEGER CHECK (ok = 1));
INSERT INTO _fx_go(ok) SELECT CASE WHEN ((SELECT COUNT(*) FROM identifiers) < 1)
  THEN 0 ELSE 1 END;

UPDATE identifiers
   SET geographic_scope = 'US'
 WHERE id = 1%s;

COMMIT;
"""


def test_t4_check_form_still_guarded(tmp_path):
    r = gate.analyze(_write(tmp_path, "0903_check_ok.sql", _CHECK_GUARD % _ARM), CANON)

    assert r["guard_kind"]["_fx_go"] == "check"
    assert (r["writes"], r["guarded"], r["unguarded"]) == (1, 1, [])
    assert gate.verdict(r) == ("FAIL-CLOSED (both arms)", False)


def test_t4b_check_form_without_arm_still_fails(tmp_path):
    r = gate.analyze(_write(tmp_path, "0904_check_noarm.sql", _CHECK_GUARD % ""), CANON)

    assert (r["writes"], r["guarded"]) == (1, 0)
    assert gate.verdict(r)[1] is True


# --------------------------------------------------------------------------------------
# T5 -- the guard-constant branch for CTAS guards, both directions.
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "const, expect_ok",
    [
        (1, True),   # the only sound constant for a 0-or-1-row table
        (2, False),  # can never match -> the write can never fire -> vacuous guard
    ],
)
def test_t5_ctas_guard_constant_branch(tmp_path, const, expect_ok):
    """A CTAS guard has ZERO INSERTs, so the insert-count rule cannot be applied to it.

    With `= 1` the pre-MAC-713 rule would have compared `[1]` against `inserts=0` and
    reported a false MISMATCH. The explicit branch must accept 1 and reject 2, and must
    report the table at all rather than skipping it into silence.
    """
    sql = _CTAS_GUARD % f"\n   AND (SELECT COUNT(*) FROM _fx_go) = {const}"
    path = _write(tmp_path, f"0905_const_{const}.sql", sql)
    r = gate.analyze(path, CANON)
    code = gate.strip_comments(Path(path).read_text(encoding="utf-8"))

    rows = {t: (detail, ok) for t, detail, ok in gate.guard_const_rows(r, code)}
    assert "_fx_go" in rows, "the CTAS guard must be evaluated, not silently skipped"
    detail, ok = rows["_fx_go"]
    assert ok is expect_ok
    assert "CTAS" in detail and "inserts=" not in detail, (
        "a CTAS guard must not be reported against an insert count"
    )


def test_t5b_check_guard_constant_still_compares_inserts(tmp_path):
    """The `check` branch is unchanged: constant vs number of precondition INSERTs."""
    sql = _CHECK_GUARD % "\n   AND (SELECT COUNT(*) FROM _fx_go) = 2"
    path = _write(tmp_path, "0906_check_const.sql", sql)
    r = gate.analyze(path, CANON)
    code = gate.strip_comments(Path(path).read_text(encoding="utf-8"))

    rows = {t: (detail, ok) for t, detail, ok in gate.guard_const_rows(r, code)}
    detail, ok = rows["_fx_go"]
    assert ok is False, "1 INSERT vs guard_consts=[2] is a MISMATCH"
    assert "inserts=1" in detail


# --------------------------------------------------------------------------------------
# T6 -- the live migration this issue is about.
# --------------------------------------------------------------------------------------

@pytest.mark.skipif(not MIG_0057.exists(), reason="mig-0057 not present in this tree")
def test_t6_live_mig_0057_reads_fail_closed():
    """The acceptance line: mig-0057 on disk reads FAIL-CLOSED with no MISMATCH.

    Asserted against the real file rather than a copy -- the false positive was a property
    of those exact bytes. Scoped to 0057 alone so an unrelated migration landing later
    cannot turn this arm red for a reason it does not describe.
    """
    r = gate.analyze(str(MIG_0057), CANON)

    assert r is not None
    assert r["guard_kind"].get("_mac707_go") == "ctas", (
        "_mac707_go is the CTAS guard the gate used to miss"
    )
    assert (r["writes"], r["guarded"], r["unguarded"]) == (1, 1, [])
    assert gate.verdict(r) == ("FAIL-CLOSED (both arms)", False)

    code = gate.strip_comments(MIG_0057.read_text(encoding="utf-8"))
    rows = {t: (detail, ok) for t, detail, ok in gate.guard_const_rows(r, code)}
    assert rows["_mac707_go"][1] is True, "the CTAS guard constant must read OK"
    assert all(ok for _, (_, ok) in rows.items()), f"unexpected MISMATCH: {rows}"
