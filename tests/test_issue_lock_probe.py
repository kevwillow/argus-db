"""MAC-572 — regression fixtures for ``scripts/issue_lock_probe.py``.

Every timestamp, run id, and agent id below is a verbatim value read off the
Paperclip API during the 2026-07-29 Validator-queue incident. The three
snapshots are the same three issues at three points in the same 26 minutes:

  T1  03:07:46Z  deadlocked   -- ORPHAN run a3312a6f holds Validator's slot
  T2  03:31:22Z  draining     -- a3312a6f killed; queued run still holds a lock
  T3  03:33:17Z  resolved     -- every lock held by its own assignee's live run

T2 is the load-bearing negative. A queued run holding a lock on an issue
assigned to a *different* agent looks exactly like T1 and is completely benign;
it self-cleared 115 seconds later with no intervention. A detector that cannot
tell T1 from T2 is worse than no detector.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "issue_lock_probe",
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "issue_lock_probe.py",
)
probe_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(probe_mod)

VALIDATOR = "da137694-2efe-4589-8150-828dcab881fb"
VALIDATOR2 = "256a926b-4e74-468a-9036-51ab11d9226a"
VALIDATOR3 = "664d8aa9-599a-41fd-ab2c-7842d3349270"

# The corpse: re-adopted by the supervisor sweep at 02:38:24, so its recorded
# startedAt is 64.4 minutes NEWER than its own last output.
RUN_ORPHAN = {
    "id": "a3312a6f-1619-4df4-bbf1-5a5806767713",
    "agentId": VALIDATOR,
    "status": "running",
    "startedAt": "2026-07-29T02:38:24.719Z",
    "lastOutputAt": "2026-07-29T01:34:00.950Z",
    "lastOutputSeq": 1557,
}
# The ghost: created 00:25:46, still queued at T1 and T2, started 03:32:35.
RUN_GHOST_QUEUED = {
    "id": "f748727e-f37e-4f38-a62a-73e2df947870",
    "agentId": VALIDATOR,
    "status": "queued",
    "createdAt": "2026-07-29T00:25:46.242Z",
    "startedAt": None,
    "lastOutputAt": None,
    "lastOutputSeq": 0,
}


def _run(rid, agent, status, started=None, last_out=None, seq=0):
    return {"id": rid, "agentId": agent, "status": status,
            "startedAt": started, "lastOutputAt": last_out, "lastOutputSeq": seq}


def _issue(ident, assignee, run_id, locked_at):
    return {"identifier": ident, "assigneeAgentId": assignee,
            "executionRunId": run_id, "executionLockedAt": locked_at}


def verdicts(issues, runs, now):
    now_dt = probe_mod.parse_ts(now)
    return {i["identifier"]: (v, d) for i, v, d in probe_mod.probe(issues, runs, now_dt, 20)}


# ── T1: the real deadlock ────────────────────────────────────────────────────

def test_t1_queued_lock_behind_orphan_is_deadlock():
    """MAC-565: assigned to Validator2, locked by Validator's queued ghost,
    whose agent slot is held by an ORPHAN. Validator2 409'd and stopped."""
    got = verdicts(
        [_issue("MAC-565", VALIDATOR2, RUN_GHOST_QUEUED["id"], "2026-07-29T03:07:46.000Z")],
        [RUN_ORPHAN, RUN_GHOST_QUEUED],
        "2026-07-29T03:20:00Z",
    )
    verdict, detail = got["MAC-565"]
    assert verdict == "DEADLOCK"
    assert "a3312a6f" in detail and "f748727e" in detail


def test_t1_orphan_holding_its_own_lock_is_orphan_lock():
    """The corpse holding a lock directly is ORPHAN_LOCK, not DEADLOCK."""
    got = verdicts(
        [_issue("MAC-570", VALIDATOR, RUN_ORPHAN["id"], "2026-07-29T03:08:43.280Z")],
        [RUN_ORPHAN],
        "2026-07-29T03:20:00Z",
    )
    assert got["MAC-570"][0] == "ORPHAN_LOCK"
    assert "64.4 min" in got["MAC-570"][1]


# ── T2: the benign look-alike that must NOT alert ────────────────────────────

def test_t2_queued_lock_with_healthy_slot_is_info_only():
    """03:31:22Z. a3312a6f is dead and gone; a2342219 is live at seq=290. The
    ghost still holds MAC-565's lock and still belongs to the wrong agent --
    both MAC-572 alarm bells -- yet it cleared on its own 115s later."""
    live = _run("a2342219-653e-4c55-8503-fea365b453da", VALIDATOR, "running",
                "2026-07-29T03:22:01.336Z", "2026-07-29T03:31:22.000Z", 290)
    dead_but_finished = dict(RUN_ORPHAN, status="succeeded")
    got = verdicts(
        [_issue("MAC-565", VALIDATOR2, RUN_GHOST_QUEUED["id"], "2026-07-29T03:22:33.063Z")],
        [dead_but_finished, RUN_GHOST_QUEUED, live],
        "2026-07-29T03:31:22Z",
    )
    verdict, detail = got["MAC-565"]
    assert verdict == "INFO"
    assert "LOCK_BY_QUEUED_RUN" in detail and "LOCK_AGENT_MISMATCH" in detail


def test_t2_agent_mismatch_alone_never_escalates():
    """Reassignment after the lock was stamped is routine, not a fault."""
    live = _run("11111111-0000-0000-0000-000000000000", VALIDATOR, "running",
                "2026-07-29T03:22:01.336Z", "2026-07-29T03:31:00.000Z", 12)
    got = verdicts(
        [_issue("MAC-551", VALIDATOR3, RUN_GHOST_QUEUED["id"], "2026-07-29T03:19:47.166Z")],
        [RUN_GHOST_QUEUED, live],
        "2026-07-29T03:31:22Z",
    )
    assert got["MAC-551"][0] == "INFO"


# ── T3: fully resolved ───────────────────────────────────────────────────────

@pytest.mark.parametrize("ident,assignee,rid", [
    ("MAC-551", VALIDATOR3, "1621ae3b-0000-0000-0000-000000000000"),
    ("MAC-565", VALIDATOR2, "55d1576c-0000-0000-0000-000000000000"),
    ("MAC-570", VALIDATOR, "4d5e49a0-e1a4-4cc8-bb65-a1390d6e14e0"),
])
def test_t3_every_gate_locked_by_its_own_live_run_is_ok(ident, assignee, rid):
    """03:33:17Z — all three gates running on their intended agent."""
    live = _run(rid, assignee, "running", "2026-07-29T03:33:00.000Z",
                "2026-07-29T03:33:17.000Z", 3)
    got = verdicts([_issue(ident, assignee, rid, "2026-07-29T03:33:17.000Z")],
                   [live], "2026-07-29T03:33:20Z")
    assert got[ident][0] == "OK"


# ── other locks nothing will ever release ────────────────────────────────────

def test_finished_run_holding_a_lock_is_stale():
    done = _run("2ff2b1bf-460b-4423-a6fb-f63e1afeeef0", VALIDATOR, "succeeded",
                "2026-07-29T02:21:27.188Z", "2026-07-29T03:21:06.754Z", 533)
    got = verdicts([_issue("MAC-569", VALIDATOR, done["id"], "2026-07-29T02:21:27.188Z")],
                   [done], "2026-07-29T03:31:22Z")
    assert got["MAC-569"][0] == "STALE_LOCK"


def test_lock_referencing_an_unknown_run_is_stale():
    got = verdicts([_issue("MAC-999", VALIDATOR, "deadbeef-0000-0000-0000-000000000000", "x")],
                   [], "2026-07-29T03:31:22Z")
    assert got["MAC-999"][0] == "STALE_LOCK"


def test_running_but_silent_past_threshold_is_orphan_lock():
    quiet = _run("cafe0001-0000-0000-0000-000000000000", VALIDATOR, "running",
                 "2026-07-29T02:00:00.000Z", "2026-07-29T02:05:00.000Z", 7)
    got = verdicts([_issue("MAC-998", VALIDATOR, quiet["id"], "2026-07-29T02:00:00.000Z")],
                   [quiet], "2026-07-29T03:31:22Z")
    assert got["MAC-998"][0] == "ORPHAN_LOCK"


# ── T4: the just-started slot-holder (the probe's own first live FP) ─────────
#
# Verbatim API values from MAC-576. CEO run 0c94aa41 held the CEO's slot; queued
# CEO run 318a23e9 held MAC-575's lock. 0c94aa41 started 03:39:44.892Z and stamped
# its first lastOutputAt at 03:39:47.250Z. Probed inside that 2.4 s window the old
# code called it a corpse and escalated MAC-575 to DEADLOCK; probed 90 s later,
# same issue and same lock-holder, INFO. Load-bearing like T2: T2 covers a healthy
# slot-holder that has already spoken, T4 covers one that has not spoken YET.
CEO = "62a86779-651b-4c59-8773-cee9e0f53334"
DBARCHITECT = "6c93a466-d498-49e0-b7af-3fc0d08eb2b0"
RUN_CEO_QUEUED = _run("318a23e9-b4d1-4415-a45e-fd27ffe29b7e", CEO, "queued")
ISSUE_MAC575 = _issue("MAC-575", DBARCHITECT, RUN_CEO_QUEUED["id"], "2026-07-29T03:38:35.209Z")


def test_t4_just_started_slot_holder_is_not_a_corpse():
    """Before the first output line lands: lastOutputAt is still None."""
    just_started = _run("0c94aa41-6b87-4689-867f-e6dc5c18d0b1", CEO, "running",
                        "2026-07-29T03:39:44.892Z", None, 0)
    got = verdicts([ISSUE_MAC575], [RUN_CEO_QUEUED, just_started], "2026-07-29T03:39:46Z")
    assert got["MAC-575"][0] == "INFO"
    assert "LOCK_BY_QUEUED_RUN" in got["MAC-575"][1]


def test_t4_same_pair_after_first_output_still_info():
    """90 s later, unchanged by any intervention. The two must agree."""
    speaking = _run("0c94aa41-6b87-4689-867f-e6dc5c18d0b1", CEO, "running",
                    "2026-07-29T03:39:44.892Z", "2026-07-29T03:39:47.250Z", 1)
    got = verdicts([ISSUE_MAC575], [RUN_CEO_QUEUED, speaking], "2026-07-29T03:41:14Z")
    assert got["MAC-575"][0] == "INFO"


def test_t4_silence_is_measured_from_startedAt_when_output_never_lands():
    """The branch must not become unconditionally safe: a run that started long
    ago and never emitted anything IS stalled, measured from startedAt."""
    never_spoke = _run("0c94aa41-6b87-4689-867f-e6dc5c18d0b1", CEO, "running",
                       "2026-07-29T03:39:44.892Z", None, 0)
    got = verdicts([ISSUE_MAC575], [RUN_CEO_QUEUED, never_spoke], "2026-07-29T04:39:44Z")
    assert got["MAC-575"][0] == "DEADLOCK"


def test_t4_running_record_with_no_timestamps_is_mid_dispatch_not_dead():
    mid_dispatch = _run("0c94aa41-6b87-4689-867f-e6dc5c18d0b1", CEO, "running", None, None, 0)
    got = verdicts([ISSUE_MAC575], [RUN_CEO_QUEUED, mid_dispatch], "2026-07-29T04:39:44Z")
    assert got["MAC-575"][0] == "INFO"


def test_unlocked_issues_are_not_reported():
    assert verdicts([_issue("MAC-500", VALIDATOR, None, None)], [], "2026-07-29T03:31:22Z") == {}
