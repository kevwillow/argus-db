#!/usr/bin/env python3
"""Detect issue execution locks that will never be released.

Companion to ``scripts/run_liveness_probe.py``. That script answers "is this RUN
alive?"; this one answers "is this ISSUE reachable?" -- the failure MAC-572 hit,
where three Validator gates were assigned, awake, and willing, and every one of
them was locked out.

WHAT IS NORMAL AND MUST NOT BE ALERTED ON
-----------------------------------------
Paperclip pre-allocates an issue's execution lock to a run while that run is
still ``queued``. Two consequences look alarming and are not:

  * LOCK_BY_QUEUED_RUN   -- a queued run holds the lock. Routine FIFO
                            pre-allocation. It clears the moment the run starts.
  * LOCK_AGENT_MISMATCH  -- the lock-holding run belongs to a different agent
                            than the current assignee. Happens whenever an issue
                            is reassigned after its lock was stamped.

Measured on MAC-572 at 2026-07-29T03:31:22Z, all three Validator gates showed
both conditions at once, and all three cleared on their own within 115 seconds
once the queue could drain. A detector that fires on either condition alone is a
false-positive machine. They are reported as INFO.

That 115-second measurement was taken on a SHALLOW queue, and the INFO line used
to assert "expect self-clear" unconditionally -- a prediction printed as a
finding, with no arithmetic behind it. On MAC-573 the same INFO fired on MAC-537
(the v1.7.0 critical path) while its lock was held by a CEO run sitting 11 deep
in a queue serialized at 1, unstarted for 30 minutes, with arrivals at 1/2.0 min
against a 9.6 min median service time. That queue diverges: the holder was ~115
minutes away, not "draining normally". Self-clear is now MEASURED, never
asserted -- see STARVED.

WHAT IS ACTUALLY BROKEN
-----------------------
  * DEADLOCK      -- the lock is held by a QUEUED run whose agent's run slot is
                     occupied by a run that is itself dead (ORPHAN or STALL).
                     The lock waits on a run that waits on a corpse. Nothing in
                     the system will break this cycle; it needs a kill or a
                     board cancel. This is the conjunction, not either half.
  * STALE_LOCK    -- the lock is held by a run that already reached a terminal
                     status (succeeded/failed/cancelled). Nobody is coming back
                     to release it.
  * ORPHAN_LOCK   -- the lock is held by a RUNNING run that ORPHAN-flags
                     (``lastOutputAt < startedAt``: the supervisor re-adopted a
                     pre-existing process onto a fresh run record).
  * STARVED       -- the lock is held by a QUEUED run whose projected wait
                     exceeds the threshold: nothing is dead, the queue is simply
                     saturated. Distinct remedy -- there is no corpse to SIGTERM,
                     so this needs a capacity or routing decision, not a kill.
                     Never claimed without a measured service time.

The MAC-572 incident in these terms: run ``a3312a6f`` (Validator) was ORPHAN and
held Validator's only slot; queued run ``f748727e`` held MAC-565's lock behind
it; MAC-565 was assigned to Validator2, which correctly 409'd and stopped. Exit
verdict DEADLOCK. After ``a3312a6f`` was killed at 03:22:00.738Z the whole chain
drained without further intervention -- ``f748727e`` started 03:32:35.942Z and
Validator2 held MAC-565's lock by 03:33:16.966Z.

NEVER USE ``agents.lastHeartbeatAt`` -- see run_liveness_probe.py. Not read here.

Usage:  python3 scripts/issue_lock_probe.py [--stall-minutes N]
        python3 scripts/issue_lock_probe.py --replay <snapshot.json>
Env:    PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID
Exit 0 = no DEADLOCK / STALE_LOCK / ORPHAN_LOCK. Exit 1 = at least one.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_STALL_MINUTES = 20
OPEN_STATUSES = "todo,in_progress,in_review,blocked"
TERMINAL = ("succeeded", "failed", "cancelled")

# Projected wait beyond which "expect self-clear" stops being a claim this probe
# can make. A heartbeat is minutes; an hour-plus wait on an assigned issue is a
# capacity fact the caller needs, not routine FIFO churn.
DEFAULT_STARVE_MINUTES = 45
# How many of an agent's finished runs to measure service time over.
SERVICE_SAMPLE = 12

# Verdicts that mean a human/kill is required, in descending severity.
ACTIONABLE = ("DEADLOCK", "STALE_LOCK", "ORPHAN_LOCK")
# Saturation, not death. Exits non-zero like ACTIONABLE, but the remedy differs:
# SIGTERM is the wrong advice when nothing is dead.
CAPACITY = ("STARVED",)


def api(path):
    base = os.environ["PAPERCLIP_API_URL"].rstrip("/")
    req = urllib.request.Request(base + path, method="GET")
    req.add_header("Authorization", "Bearer " + os.environ["PAPERCLIP_API_KEY"])
    run_id = os.environ.get("PAPERCLIP_RUN_ID")
    if run_id:
        req.add_header("X-Paperclip-Run-Id", run_id)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        sys.exit("API %s on %s: %s" % (exc.code, path, exc.read().decode()[:300]))


def unwrap(payload, key):
    return payload if isinstance(payload, list) else payload.get(key, [])


def parse_ts(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_orphan(run):
    """``lastOutputAt < startedAt`` -- an impossible ordering. See MAC-572."""
    started, last_out = parse_ts(run.get("startedAt")), parse_ts(run.get("lastOutputAt"))
    return bool(started and last_out and last_out < started)


def is_stalled(run, now, stall_minutes):
    """A running run that has emitted nothing for longer than the threshold.

    Silence is measured from the last output if there is one, and otherwise from
    ``startedAt``. A run that has just been handed a process has not emitted
    anything yet, and "no output yet" is not "no output for 20 minutes".

    Paid for by the probe's own first live actionable verdict (MAC-576). CEO run
    ``0c94aa41`` flipped to ``running`` at 03:39:44.892Z and did not stamp its
    first ``lastOutputAt`` until 03:39:47.250Z. Inside that 2.4-second window the
    old ``last_out is None -> True`` branch called it a corpse, which escalated
    MAC-575's routine queued lock to DEADLOCK. Re-probed 90 s later with no
    intervention: INFO. That is precisely the false positive the T2 test exists
    to forbid, arriving through the one input T2 did not cover.

    A ``running`` record carrying neither timestamp is a record mid-dispatch, not
    evidence of a corpse; there is no window to measure, so it is not stalled.
    The impossible-ordering case stays with ``is_orphan``.
    """
    if run.get("status") != "running":
        return False
    marker = parse_ts(run.get("lastOutputAt")) or parse_ts(run.get("startedAt"))
    if marker is None:
        return False
    return (now - marker).total_seconds() / 60.0 > stall_minutes


def service_minutes(agent_runs):
    """Median wall-clock of this agent's most recent finished runs, or None.

    None means unmeasured, and an unmeasured drain rate must never be reported as
    a drain rate. The caller degrades to "position known, wait unmeasured" rather
    than inventing a number -- an unevaluated prediction is the defect STARVED
    exists to remove, so it must not reappear as a default.
    """
    done = [r for r in agent_runs if parse_ts(r.get("startedAt")) and parse_ts(r.get("finishedAt"))]
    done.sort(key=lambda r: r.get("finishedAt") or "")
    durations = sorted(
        (parse_ts(r["finishedAt"]) - parse_ts(r["startedAt"])).total_seconds() / 60.0
        for r in done[-SERVICE_SAMPLE:]
    )
    if not durations:
        return None
    return durations[len(durations) // 2]


def queue_position(run, agent_runs):
    """(queued runs created before this one, runs currently occupying a slot)."""
    created = parse_ts(run.get("createdAt"))
    ahead = 0
    for other in agent_runs:
        if other.get("id") == run.get("id") or other.get("status") != "queued":
            continue
        other_created = parse_ts(other.get("createdAt"))
        if created and other_created and other_created < created:
            ahead += 1
    running = sum(1 for r in agent_runs if r.get("status") == "running")
    return ahead, running


def classify_lock(issue, runs_by_id, runs_by_agent, now, stall_minutes,
                  starve_minutes=DEFAULT_STARVE_MINUTES):
    """Return (verdict, detail) for one locked issue."""
    run_id = issue.get("executionRunId")
    run = runs_by_id.get(run_id)
    if run is None:
        return "STALE_LOCK", "lock references run %s, which is not in the run list" % (run_id or "?")

    status = run.get("status")
    if status in TERMINAL:
        return "STALE_LOCK", "lock held by %s run %s -- nothing will release it" % (status, run_id[:8])

    if status == "running":
        if is_orphan(run):
            gap = (parse_ts(run["startedAt"]) - parse_ts(run["lastOutputAt"])).total_seconds() / 60.0
            return "ORPHAN_LOCK", "lock held by ORPHAN run %s (lastOutputAt precedes startedAt by %.1f min)" % (
                run_id[:8], gap)
        if is_stalled(run, now, stall_minutes):
            return "ORPHAN_LOCK", "lock held by STALLed run %s (no output for >%d min)" % (
                run_id[:8], stall_minutes)
        return "OK", "lock held by live run %s (seq=%s)" % (run_id[:8], run.get("lastOutputSeq"))

    # status == "queued": routine FIFO pre-allocation UNLESS the holder's agent
    # slot is occupied by a dead run. That conjunction is the deadlock.
    blockers = [
        r for r in runs_by_agent.get(run.get("agentId"), [])
        if r.get("status") == "running" and (is_orphan(r) or is_stalled(r, now, stall_minutes))
    ]
    if blockers:
        return "DEADLOCK", (
            "queued run %s holds the lock; its agent's slot is held by dead run %s -- "
            "the lock waits on a run that waits on a corpse" % (run_id[:8], blockers[0]["id"][:8]))

    notes = ["LOCK_BY_QUEUED_RUN"]
    if run.get("agentId") and issue.get("assigneeAgentId") and run["agentId"] != issue["assigneeAgentId"]:
        notes.append("LOCK_AGENT_MISMATCH")
    label = "+".join(notes)

    # "Expect self-clear" is a prediction. Measure it or do not make it.
    agent_runs = runs_by_agent.get(run.get("agentId"), [])
    ahead, running = queue_position(run, agent_runs)
    service = service_minutes(agent_runs)
    if service is None:
        return "INFO", "%s -- %d queued ahead, %d in flight; drain rate unmeasured " \
            "(no finished run recorded for this agent)" % (label, ahead, running)

    lanes = max(1, running)
    wait = ((ahead + running) / float(lanes)) * service
    shape = "%d queued ahead, %d in flight, %.1f min median service -> ~%.0f min projected wait" % (
        ahead, running, service, wait)
    if wait > starve_minutes:
        return "STARVED", "%s -- %s (threshold %d min). Nothing is dead; the queue is saturated" % (
            label, shape, starve_minutes)
    return "INFO", "%s -- %s, under the %d min threshold" % (label, shape, starve_minutes)


def probe(issues, runs, now, stall_minutes, starve_minutes=DEFAULT_STARVE_MINUTES):
    runs_by_id = {r["id"]: r for r in runs}
    runs_by_agent = {}
    for r in runs:
        runs_by_agent.setdefault(r.get("agentId"), []).append(r)
    results = []
    for issue in issues:
        if not issue.get("executionRunId"):
            continue
        verdict, detail = classify_lock(
            issue, runs_by_id, runs_by_agent, now, stall_minutes, starve_minutes)
        results.append((issue, verdict, detail))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stall-minutes", type=int, default=DEFAULT_STALL_MINUTES)
    ap.add_argument("--starve-minutes", type=int, default=DEFAULT_STARVE_MINUTES,
                    help="projected queue wait above which a queued lock is STARVED")
    ap.add_argument("--replay", help="JSON snapshot {now, issues[], runs[], agents[]} instead of the API")
    args = ap.parse_args()

    if args.replay:
        with open(args.replay) as fh:
            snap = json.load(fh)
        issues, runs = snap["issues"], snap["runs"]
        agents = snap.get("agents", [])
        now = parse_ts(snap["now"])
    else:
        company = os.environ["PAPERCLIP_COMPANY_ID"]
        issues = unwrap(api("/api/companies/%s/issues?status=%s&limit=200" % (company, OPEN_STATUSES)), "issues")
        runs = unwrap(api("/api/companies/%s/heartbeat-runs?limit=200" % company), "runs")
        agents = unwrap(api("/api/companies/%s/agents" % company), "agents")
        now = datetime.now(timezone.utc)

    names = {a.get("id"): a.get("name") for a in agents}
    results = probe(issues, runs, now, args.stall_minutes, args.starve_minutes)

    bad, starved = [], []
    for issue, verdict, detail in sorted(results, key=lambda t: t[0].get("identifier") or ""):
        marker = "! " if verdict in ACTIONABLE + CAPACITY else "  "
        print("%s%-11s %-9s %-14s %s" % (
            marker, verdict, issue.get("identifier"),
            names.get(issue.get("assigneeAgentId"), "(none)"), detail))
        if verdict in ACTIONABLE:
            bad.append((issue, verdict, detail))
        elif verdict in CAPACITY:
            starved.append((issue, verdict, detail))

    if not bad and not starved:
        print("\nNo unreachable issues: every execution lock is live or draining.")
        return 0

    if bad:
        print("\n%d issue(s) hold a lock nothing will release:" % len(bad))
        for issue, verdict, _ in bad:
            print("  %-11s %s (assignee %s)" % (
                verdict, issue.get("identifier"), names.get(issue.get("assigneeAgentId"), "(none)")))
        print("\nAgents are 403 on POST /api/heartbeat-runs/{id}/cancel, but the PROCESS is"
              "\nreachable: confirm unique PID binding, then SIGTERM. See MAC-572.")

    if starved:
        print("\n%d issue(s) are locked behind a saturated queue:" % len(starved))
        for issue, verdict, _ in starved:
            print("  %-11s %s (assignee %s)" % (
                verdict, issue.get("identifier"), names.get(issue.get("assigneeAgentId"), "(none)")))
        print("\nDo NOT SIGTERM these -- nothing is dead, and killing a healthy run to"
              "\njump a queue destroys work. The remedy is a capacity or routing decision:"
              "\nraise the holder agent's concurrency, or re-stamp the lock onto the"
              "\nassignee's own queue. See MAC-573.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
