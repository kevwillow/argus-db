"""MAC-579 — regression fixtures for ``scripts/run_liveness_probe.py``.

This probe shipped on MAC-572 with a "5 true positives, 0 false positives against
200 runs" record and **no test file at all**. That record is an operator-run
attestation: one person ran the tool once and read the output. It is not a suite,
and it did not survive contact with an input it had not seen. This file is the
suite.

Every timestamp, run id, and agent id below is a verbatim value read off the
Paperclip API during the 2026-07-29 incidents:

  ORPHAN   MAC-572  run a3312a6f re-adopted at 02:38:24 onto a process whose last
                    output was 01:34:00 — 64.4 minutes of impossible ordering.
  T4       MAC-576  CEO run 0c94aa41 flipped to ``running`` at 03:39:44.892Z and
                    stamped its first ``lastOutputAt`` at 03:39:47.250Z.

T4 is the load-bearing negative, and it is the same defect the sibling probe hit
one function over: inside that 2.4-second window ``lastOutputAt`` is still None,
and the pre-MAC-579 code returned STALL unconditionally on that branch. The
prescribed response to a dead run is a kill, so a probe that reads a two-second-old
run as a corpse is not a noisy probe — it is a probe that kills live work.

The negative control (``test_t4_silence_is_measured_from_startedAt...``) is what
stops the fix from degrading into "never STALL when lastOutputAt is missing".
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _ROOT / "scripts" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


probe_mod = _load("run_liveness_probe")
lock_mod = _load("issue_lock_probe")

CEO = "62a86779-651b-4c59-8773-cee9e0f53334"
VALIDATOR = "da137694-2efe-4589-8150-828dcab881fb"

STALL_MINUTES = 20


def _run(rid, agent, status, started=None, last_out=None, seq=0):
    """A run record with no ``processPid``, so the PID_MISMATCH probe is inert.

    ``pid_start(None)`` returns None without shelling out, which keeps every
    fixture below hermetic — no ``ps``, no /proc, no live process on the box.
    """
    return {"id": rid, "agentId": agent, "status": status,
            "startedAt": started, "lastOutputAt": last_out, "lastOutputSeq": seq,
            "processPid": None, "processStartedAt": None}


def classify(run, now, stall_minutes=STALL_MINUTES):
    return probe_mod.classify(run, probe_mod.parse_ts(now), stall_minutes)


# ── ORPHAN: the load-bearing check, untouched by MAC-579 ─────────────────────

RUN_ORPHAN = _run("a3312a6f-1619-4df4-bbf1-5a5806767713", VALIDATOR, "running",
                  "2026-07-29T02:38:24.719Z", "2026-07-29T01:34:00.950Z", 1557)


def test_orphan_impossible_ordering_is_flagged():
    """A run cannot emit output before it starts. 64.4 min of it here."""
    verdict, detail = classify(RUN_ORPHAN, "2026-07-29T03:20:00Z")
    assert verdict == "ORPHAN"
    assert "64.4 min" in detail


def test_orphan_is_detected_before_the_status_gate():
    """main() reports resolved ORPHANs as history, which requires classify() to
    reach the ORPHAN branch on a terminal record too."""
    assert classify(dict(RUN_ORPHAN, status="succeeded"), "2026-07-29T03:31:22Z")[0] == "ORPHAN"


def test_orphan_outranks_stall_on_an_ancient_corpse():
    """An orphan that is ALSO long silent stays ORPHAN — the more specific
    diagnosis. MAC-579 changed the STALL branch; this pins that it did not
    reorder the two."""
    assert classify(RUN_ORPHAN, "2026-07-29T09:00:00Z")[0] == "ORPHAN"


# ── T4: the just-started run (MAC-576's false positive) ──────────────────────

RUN_JUST_STARTED = _run("0c94aa41-6b87-4689-867f-e6dc5c18d0b1", CEO, "running",
                        "2026-07-29T03:39:44.892Z", None, 0)
RUN_SPEAKING = _run("0c94aa41-6b87-4689-867f-e6dc5c18d0b1", CEO, "running",
                    "2026-07-29T03:39:44.892Z", "2026-07-29T03:39:47.250Z", 1)


def test_t4_just_started_run_is_not_a_corpse():
    """Probed at 03:39:46Z — 1.1 s after start, 1.3 s before the first output
    line. The pre-MAC-579 code returned STALL here."""
    verdict, detail = classify(RUN_JUST_STARTED, "2026-07-29T03:39:46Z")
    assert verdict == "OK"
    assert "no output yet" in detail


def test_t4_same_run_after_its_first_output_still_ok():
    """90 s later, unchanged by any intervention. The two must agree."""
    assert classify(RUN_SPEAKING, "2026-07-29T03:41:14Z")[0] == "OK"


def test_t4_the_2_4_second_window_never_flips_verdict():
    """Sweep the whole window between startedAt and the first lastOutputAt. No
    instant inside it may read as anything but OK."""
    for now in ("2026-07-29T03:39:44.892Z", "2026-07-29T03:39:45.500Z",
                "2026-07-29T03:39:47.249Z", "2026-07-29T03:39:47.250Z"):
        assert classify(RUN_JUST_STARTED, now)[0] == "OK", now


def test_t4_silence_is_measured_from_startedAt_when_output_never_lands():
    """NEGATIVE CONTROL. The branch must not become unconditionally safe: a run
    that started an hour ago and never emitted anything IS stalled, measured
    from startedAt."""
    verdict, detail = classify(RUN_JUST_STARTED, "2026-07-29T04:39:44Z")
    assert verdict == "STALL"
    assert "since start" in detail
    assert "60.0 min" in detail  # 03:39:44.892 -> 04:39:44.000 == 59.985 min


def test_t4_running_record_with_no_timestamps_is_mid_dispatch_not_dead():
    """Neither timestamp means there is no window to measure. Absence of a
    measurable window is not evidence of death."""
    mid_dispatch = _run("0c94aa41-6b87-4689-867f-e6dc5c18d0b1", CEO, "running", None, None, 0)
    verdict, detail = classify(mid_dispatch, "2026-07-29T04:39:44Z")
    assert verdict == "OK"
    assert "mid-dispatch" in detail


# ── ordinary STALL / OK / IDLE ───────────────────────────────────────────────

def test_running_and_silent_past_threshold_is_stall():
    quiet = _run("cafe0001-0000-0000-0000-000000000000", VALIDATOR, "running",
                 "2026-07-29T02:00:00.000Z", "2026-07-29T02:05:00.000Z", 7)
    verdict, detail = classify(quiet, "2026-07-29T03:31:22Z")
    assert verdict == "STALL"
    assert "86.4 min" in detail


def test_healthy_running_run_is_ok():
    """a2342219 at 03:31:22Z, seq=290 — the concurrently-healthy control from
    the MAC-572 sweep."""
    live = _run("a2342219-653e-4c55-8503-fea365b453da", VALIDATOR, "running",
                "2026-07-29T03:22:01.336Z", "2026-07-29T03:31:22.000Z", 290)
    verdict, detail = classify(live, "2026-07-29T03:31:22Z")
    assert verdict == "OK"
    assert "seq=290" in detail


@pytest.mark.parametrize("threshold_edge,expected", [
    ("2026-07-29T02:25:00.000Z", "OK"),     # exactly 20.0 min — strict >, not >=
    ("2026-07-29T02:25:00.001Z", "STALL"),  # one millisecond past
])
def test_stall_threshold_is_strictly_greater_than(threshold_edge, expected):
    quiet = _run("cafe0002-0000-0000-0000-000000000000", VALIDATOR, "running",
                 "2026-07-29T02:00:00.000Z", "2026-07-29T02:05:00.000Z", 7)
    assert classify(quiet, threshold_edge)[0] == expected


@pytest.mark.parametrize("status", ["queued", "succeeded", "failed", "cancelled"])
def test_non_running_statuses_are_idle(status):
    """Only a `running` record can be a corpse. A queued run has no process."""
    idle = _run("beef0001-0000-0000-0000-000000000000", CEO, status,
                None if status == "queued" else "2026-07-29T02:00:00.000Z", None, 0)
    assert classify(idle, "2026-07-29T09:00:00Z") == ("IDLE", status)


# ── the two probes must not drift apart again ────────────────────────────────

@pytest.mark.parametrize("run,now", [
    (RUN_JUST_STARTED, "2026-07-29T03:39:46Z"),
    (RUN_SPEAKING, "2026-07-29T03:41:14Z"),
    (RUN_JUST_STARTED, "2026-07-29T04:39:44Z"),
    (_run("cafe0003-0000-0000-0000-000000000000", CEO, "running", None, None, 0),
     "2026-07-29T04:39:44Z"),
    (_run("cafe0004-0000-0000-0000-000000000000", VALIDATOR, "running",
          "2026-07-29T02:00:00.000Z", "2026-07-29T02:05:00.000Z", 7),
     "2026-07-29T03:31:22Z"),
])
def test_both_probes_agree_on_liveness(run, now):
    """MAC-579 exists because the MAC-576 fix landed on one probe and not the
    other. `issue_lock_probe.is_stalled` and `run_liveness_probe.classify` are
    two copies of the same judgement; pin them together so the next divergence
    fails here instead of in production. Orphans are excluded: that ordering is
    diagnosed separately by `is_orphan` in the sibling."""
    now_dt = probe_mod.parse_ts(now)
    assert not lock_mod.is_orphan(run), "fixture must be non-orphan"
    sibling_says_stalled = lock_mod.is_stalled(run, now_dt, STALL_MINUTES)
    assert (classify(run, now)[0] == "STALL") == sibling_says_stalled
