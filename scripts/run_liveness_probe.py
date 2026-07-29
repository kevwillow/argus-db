#!/usr/bin/env python3
"""Classify Paperclip heartbeat runs as live, stalled, or re-adopted orphans.

Ratified on MAC-572. Replaces the ad-hoc "is that agent dead?" eyeball check that
produced two contradictory answers in one hour.

NEVER USE `agents.lastHeartbeatAt`. It does not advance while a run is in flight, so a
busy agent looks progressively deader the longer it works -- the signal inverts. This
script does not read that field at all.

The load-bearing check is ORPHAN: `lastOutputAt < startedAt` is an impossible ordering.
A run cannot emit output before it starts. When it appears, the supervisor has re-adopted
a pre-existing process onto a fresh run record and overwritten `startedAt` -- the record
now describes a process it did not spawn. Measured on MAC-572 against 200 runs: 5 true
positives (all inside a 1.05s supervisor recovery sweep at 2026-07-29T02:38:23-24Z,
spanning CTO/CEO/DBArchitect/Validator), 0 false positives against 5 concurrently
healthy running runs.

ORPHAN is pure API arithmetic -- no filesystem, no `ps`. Prefer it. `logRef` mtime is NOT
a safe substitute: the re-adoption rewrites the head of the existing ndjson in place, so
run a3312a6f held a line at byte 0 timestamped 64 minutes NEWER than its own last line,
and the file mtime described the previous incarnation.

PID_MISMATCH is the local cross-check when /proc is readable: compare `processStartedAt`
against the real start time of `processPid`. On a3312a6f these differed by ~4 hours.

Usage:  python3 scripts/run_liveness_probe.py [--stall-minutes N] [--limit N]
Env:    PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID
Exit 0 = no ORPHAN and no STALL. Exit 1 = at least one run needs a board cancel.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_STALL_MINUTES = 20
LIVE = ("running", "queued")


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


def parse_ts(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pid_start(pid):
    """Real start time of a live PID, or None if it is gone / unreadable."""
    if not pid:
        return None
    try:
        out = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    stamp = out.stdout.strip()
    if not stamp:
        return None
    try:
        naive = datetime.strptime(stamp, "%a %b %d %H:%M:%S %Y")
    except ValueError:
        return None
    return naive.astimezone()


def classify(run, now, stall_minutes):
    """Return (verdict, detail). Verdicts: ORPHAN, STALL, PID_MISMATCH, OK, IDLE."""
    status = run.get("status")
    started = parse_ts(run.get("startedAt"))
    last_out = parse_ts(run.get("lastOutputAt"))

    if started and last_out and last_out < started:
        gap = (started - last_out).total_seconds() / 60.0
        return "ORPHAN", "lastOutputAt precedes startedAt by %.1f min -- re-adopted process" % gap

    if status != "running":
        return "IDLE", status

    real = pid_start(run.get("processPid"))
    recorded = parse_ts(run.get("processStartedAt"))
    if real and recorded:
        skew = abs((real - recorded).total_seconds())
        if skew > 120:
            return "PID_MISMATCH", "pid %s really started %.0f min from processStartedAt" % (
                run.get("processPid"), skew / 60.0)

    if last_out:
        quiet = (now - last_out).total_seconds() / 60.0
        if quiet > stall_minutes:
            return "STALL", "no output for %.1f min (threshold %d)" % (quiet, stall_minutes)
        return "OK", "last output %.1f min ago, seq=%s" % (quiet, run.get("lastOutputSeq"))

    return "STALL", "running with no output recorded at all"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stall-minutes", type=int, default=DEFAULT_STALL_MINUTES)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--all", action="store_true", help="include finished runs")
    args = ap.parse_args()

    company = os.environ["PAPERCLIP_COMPANY_ID"]
    payload = api("/api/companies/%s/heartbeat-runs?limit=%d" % (company, args.limit))
    runs = payload if isinstance(payload, list) else payload.get("runs", [])

    names = {}
    agents = api("/api/companies/%s/agents" % company)
    for agent in (agents if isinstance(agents, list) else agents.get("agents", [])):
        names[agent.get("id")] = agent.get("name")

    now = datetime.now(timezone.utc)
    bad = []
    for run in runs:
        if not args.all and run.get("status") not in LIVE:
            # An ORPHAN that already resolved is history, not an incident.
            started, last_out = parse_ts(run.get("startedAt")), parse_ts(run.get("lastOutputAt"))
            if not (started and last_out and last_out < started):
                continue
        verdict, detail = classify(run, now, args.stall_minutes)
        live = run.get("status") in LIVE
        if verdict in ("OK", "IDLE") and not args.all:
            print("  OK    %-16s %s  %s" % (names.get(run.get("agentId"), "?"), run.get("id"), detail))
            continue
        # A run that already reached a terminal status is history, not an open incident.
        label = verdict if live else verdict + "(resolved)"
        line = "%-19s %-16s %s  %s" % (label, names.get(run.get("agentId"), "?"), run.get("id"), detail)
        print(("! " + line) if live else ("  " + line))
        if verdict in ("ORPHAN", "STALL", "PID_MISMATCH") and live:
            bad.append((verdict, run))

    if not bad:
        print("\nAll live runs healthy.")
        return 0

    print("\n%d live run(s) need a board cancel -- agents get 403 on"
          " POST /api/heartbeat-runs/{id}/cancel:" % len(bad))
    for verdict, run in bad:
        print("  %s  %s  (agent %s)" % (verdict, run.get("id"), names.get(run.get("agentId"), "?")))
    return 1


if __name__ == "__main__":
    sys.exit(main())
