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

# Verdicts that mean a human/kill is required, in descending severity.
ACTIONABLE = ("DEADLOCK", "STALE_LOCK", "ORPHAN_LOCK")


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
    """A running run that has emitted nothing for longer than the threshold."""
    if run.get("status") != "running":
        return False
    last_out = parse_ts(run.get("lastOutputAt"))
    if last_out is None:
        return True
    return (now - last_out).total_seconds() / 60.0 > stall_minutes


def classify_lock(issue, runs_by_id, runs_by_agent, now, stall_minutes):
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
    return "INFO", "%s -- queue is draining normally, expect self-clear" % "+".join(notes)


def probe(issues, runs, now, stall_minutes):
    runs_by_id = {r["id"]: r for r in runs}
    runs_by_agent = {}
    for r in runs:
        runs_by_agent.setdefault(r.get("agentId"), []).append(r)
    results = []
    for issue in issues:
        if not issue.get("executionRunId"):
            continue
        verdict, detail = classify_lock(issue, runs_by_id, runs_by_agent, now, stall_minutes)
        results.append((issue, verdict, detail))
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stall-minutes", type=int, default=DEFAULT_STALL_MINUTES)
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
    results = probe(issues, runs, now, args.stall_minutes)

    bad = []
    for issue, verdict, detail in sorted(results, key=lambda t: t[0].get("identifier") or ""):
        marker = "! " if verdict in ACTIONABLE else "  "
        print("%s%-11s %-9s %-14s %s" % (
            marker, verdict, issue.get("identifier"),
            names.get(issue.get("assigneeAgentId"), "(none)"), detail))
        if verdict in ACTIONABLE:
            bad.append((issue, verdict, detail))

    if not bad:
        print("\nNo unreachable issues: every execution lock is live or draining.")
        return 0

    print("\n%d issue(s) hold a lock nothing will release:" % len(bad))
    for issue, verdict, _ in bad:
        print("  %-11s %s (assignee %s)" % (
            verdict, issue.get("identifier"), names.get(issue.get("assigneeAgentId"), "(none)")))
    print("\nAgents are 403 on POST /api/heartbeat-runs/{id}/cancel, but the PROCESS is"
          "\nreachable: confirm unique PID binding, then SIGTERM. See MAC-572.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
