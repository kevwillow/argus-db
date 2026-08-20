"""MAC-755 — provenance gate on the frozen extraction-time canonical snapshots.

The cohort tests are only as trustworthy as the snapshot they read.  If someone
regenerates that fixture from today's ``db/argus.db``, every net-new assertion in
the seven cohort files silently goes vacuous and the suite stays green — which is
exactly the failure mode MAC-755 exists to kill.  These tests make that loud.

They prove, from git rather than from assertion:

1. Each fixture is byte-identical to the pinned ``exports/argus_export.csv``
   blob projected onto the carried columns.
2. Each epoch boundary holds on BOTH arms — the cohort's probe identifier is
   absent at the pinned epoch and present at the next published export.  A
   one-sided check would pass against any epoch old enough.
3. The snapshot really is pre-promotion: identifiers that live canonical holds
   today are absent from it.  This is the counterfactual that fails the moment
   the fixture is re-baselined against live state.
4. No PII rides in the fcc_grantees subset.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from cohort_frozen_db import (  # noqa: E402
    COHORT_EPOCH, EPOCHS, GRANTEES_CSV, _fixture, freeze_cohort_db)

import mac755_build_frozen_snapshot as builder  # noqa: E402

HAS_GIT = shutil.which("git") is not None and (REPO / ".git").exists()
needs_git = pytest.mark.skipif(not HAS_GIT, reason="git or .git absent; cannot re-derive provenance")
LIVE_DB = REPO / "db" / "argus.db"


# --- 1. fixture integrity (no git needed) ------------------------------------
@pytest.mark.parametrize("epoch", sorted(EPOCHS))
def test_fixture_sha256_and_rowcount(epoch):
    spec = EPOCHS[epoch]
    raw = gzip.decompress(_fixture(epoch).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == spec["sha256"]
    assert len(list(csv.DictReader(raw.decode("utf-8").splitlines()))) == spec["rows"]


def test_every_cohort_is_mapped_to_an_epoch():
    assert set(COHORT_EPOCH.values()) <= set(EPOCHS)
    assert len(COHORT_EPOCH) == 7, "all seven cohort extractors must be repointed"


# --- 2. the fixture is a faithful projection of the pinned git blob ----------
@needs_git
@pytest.mark.parametrize("epoch", sorted(EPOCHS))
def test_fixture_reproduces_from_pinned_git_blob(epoch):
    ep = next(e for e in builder.EPOCHS if e.key == epoch)
    # the pin itself: commit -> blob -> sha256
    blob_id = subprocess.run(["git", "-C", str(REPO), "rev-parse",
                              f"{ep.commit}:{builder.PIN_PATH}"],
                             capture_output=True, text=True, check=True).stdout.strip()
    assert blob_id == ep.blob, f"pinned blob moved: {blob_id} != {ep.blob}"
    raw = subprocess.run(["git", "-C", str(REPO), "cat-file", "blob", ep.blob],
                         capture_output=True, check=True).stdout
    assert hashlib.sha256(raw).hexdigest() == ep.sha256

    # re-project and byte-compare against the committed fixture
    lines = raw.decode("utf-8", errors="replace").split("\n")
    assert lines[0].startswith("# meta:")
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[1:]))))
    assert len(rows) == ep.rows
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=builder.ID_COLS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: r[c] for c in builder.ID_COLS})
    rederived = buf.getvalue().encode("utf-8")
    committed = gzip.decompress(_fixture(epoch).read_bytes())
    assert rederived == committed, (
        f"fixture '{epoch}' is NOT the pinned export projection — it has been "
        "hand-edited or re-baselined")


# --- 3. the epoch boundary holds on both arms -------------------------------
@needs_git
@pytest.mark.parametrize("epoch", sorted(EPOCHS))
def test_epoch_boundary_both_arms(epoch):
    ep = next(e for e in builder.EPOCHS if e.key == epoch)
    here = {(r["identifier"] or "").lower() for r in builder.read_export(ep.commit)}
    nxt = {(r["identifier"] or "").lower() for r in builder.read_export(ep.next_commit)}
    probe = ep.probe.lower()
    assert probe not in here, (
        f"{ep.probe} already in {ep.commit} — epoch is post-promotion, so the "
        "cohort's net-new assertions are vacuous")
    assert probe in nxt, (
        f"{ep.probe} still absent at {ep.next_commit} — epoch is needlessly "
        "early; a newer pre-promotion export exists")


# --- 4. counterfactual: the snapshot is genuinely pre-promotion --------------
@pytest.mark.skipif(not LIVE_DB.exists(), reason="live db/argus.db absent")
@pytest.mark.parametrize("epoch", sorted(EPOCHS))
def test_snapshot_is_not_a_live_rebaseline(epoch):
    """The probe must be HELD in live canonical but ABSENT from the snapshot.

    If the fixture is ever regenerated from today's DB this fails immediately,
    instead of silently turning all seven cohort files into change-detectors.
    """
    ep = next(e for e in builder.EPOCHS if e.key == epoch)
    conn = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    live = conn.execute(
        "SELECT COUNT(*) FROM identifiers WHERE lower(identifier)=lower(?) "
        "AND superseded_by IS NULL", (ep.probe,)).fetchone()[0]
    conn.close()
    assert live > 0, (
        f"{ep.probe} is no longer held in live canonical — it was withdrawn or "
        "retyped, so this counterfactual needs a new probe (do NOT delete it)")

    snap = {(r["identifier"] or "").lower()
            for r in csv.DictReader(
                gzip.decompress(_fixture(epoch).read_bytes()).decode("utf-8").splitlines())}
    assert ep.probe.lower() not in snap, (
        f"{ep.probe} is in the '{epoch}' snapshot AND in live canonical — the "
        "fixture has been re-baselined against live state and every net-new "
        "assertion that reads it is now vacuous")


# --- 5. no PII in the committed grantee subset -------------------------------
def test_grantee_subset_carries_no_contact_pii():
    with GRANTEES_CSV.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "grantee subset is empty"
    for r in rows:
        assert r["contact_name"] in ("", builder.CONTACT_SENTINEL), (
            f"real contact_name committed for {r['grantee_code']} — this column "
            "is PII and must never leave the DB")


def test_snapshot_materialises_and_is_readonly():
    paths = freeze_cohort_db()
    assert set(paths) == set(COHORT_EPOCH)
    for mod_name, path in paths.items():
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        n = conn.execute("SELECT COUNT(*) FROM identifiers").fetchone()[0]
        g = conn.execute("SELECT COUNT(*) FROM fcc_grantees").fetchone()[0]
        conn.close()
        assert n == EPOCHS[COHORT_EPOCH[mod_name]]["rows"]
        assert g == 19, "all 19 referenced grantee codes must be present"
