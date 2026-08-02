#!/usr/bin/env python3
"""Report Anthropic weekly-quota refusals from the on-disk Paperclip run logs.

MAC-650. Board-approved instrument, approval `695f09f2`.

A refused run never reaches the model. It bills `total_cost_usd: 0` with 0 input and 0
output tokens and reports `"subtype": "success"`, so every cost-based view renders it as an
IDLE agent. It is the inverse: work refused before it could bill. That misreading is not
hypothetical -- MAC-643 diagnosed 929 refusals as "0-token session startup failures", and
the productivity detector minted five review tickets (MAC-643..MAC-647) in the same minute
off one outage, each costing a run to close out of the same exhausted quota.

WHY THIS IS A SCRIPT AND NOT A NOTE. The 2026-07-29 episode was re-derived by hand twice and
mis-attributed both times. A rule that lives only in a memory file is not a gate; it gets
re-litigated from scratch by whoever looks next, with whatever instrument is nearest to hand.

DO NOT SIZE THIS FROM THE API. There is no agent-facing runs endpoint -- `/api/.../runs` is
404 on every shape -- and the run window the adapter exposes is truncated. Sizing the
2026-07-29/30 episode from that window returned 100 refusals against an actual 929, because
the window opened 2026-07-30T08:31Z and the worst day is entirely before it. A 9x
under-report reads as a manageable annoyance rather than a throughput wall.

THE FILTER IS THE DELIVERABLE. A bare `grep "weekly limit"` over-counts: it also matches a
resumed transcript quoting the error, and an issue description quoting its own error bytes.
This counts a run as refused only when its RESULT frame carries `api_error_status: 429`
alongside the weekly-limit text. Both tallies are printed so the gap stays visible; when
`loose` runs far ahead of `strict`, the extra matches are echoes, not refusals.

Usage:
    python3 scripts/check_quota_refusals.py
    python3 scripts/check_quota_refusals.py --since 2026-07-29 --until 2026-07-31
    python3 scripts/check_quota_refusals.py --label 62a86779...=CEO --label 0715773f...=CTO
    python3 scripts/check_quota_refusals.py --max-rate 0     # positive control

R7 positive control: this check reports zero on a quiet week, and a zero-yield check that has
never been shown firing is not evidence. Two ways to fire it before quoting a zero --
`--max-rate 0` on any window holding a refusal, or point `--since/--until` at the known
2026-07-29..2026-07-30 episode, which MUST come back FAIL at 516 and 389.

Exit 0 = PASS or WARN. Exit 1 = refusal rate over the ceiling. Exit 2 = usage error.
Exit 3 = SKIPPED: the run-log root did not resolve or held no runs, so the lane is
uncertified for quota, not clear of it. Same four codes and meanings as
`check_push_blob_sizes.py` and `check_staged_paths.py`.
"""
import argparse
import collections
import json
import os
import sys

DEFAULT_RUN_LOG_ROOT = os.path.expanduser("~/.paperclip/instances/default/data/run-logs")

# A refusal is billed at zero, so a rate ceiling is the only meaningful gate -- an absolute
# count says nothing without the denominator it was drawn from. 5% is well clear of the
# background (a quiet week is 0.0%) and well under the 37.2% that went unnoticed.
DEFAULT_MAX_RATE = 0.05
DEFAULT_WARN_RATE = 0.01

REFUSAL_TEXT = "weekly limit"
REFUSAL_STATUS = '"api_error_status":429'

# `chunk` is a JSON string nested inside the ndjson frame, so the raw line carries the
# marker ESCAPED (`\"api_error_status\":429`). Prefiltering the raw line on the unescaped
# form matches nothing and silently zeroes the strict tally -- the check then certifies
# every lane as clean because it can no longer see the thing it exists to find. Prefilter on
# the bare token only; the parsed chunk below is what actually decides.
REFUSAL_PREFILTER = "api_error_status"

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_UNEVALUATED = 3

assert len({EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_UNEVALUATED}) == 4, "exit codes collide"
assert DEFAULT_WARN_RATE < DEFAULT_MAX_RATE, "warn threshold not below ceiling"


def scan_run(path):
    """(strict_ts, loose) for one run log.

    `strict_ts` is the timestamp of the result frame that refused, or None. `loose` is True
    when the file mentions the weekly limit at all. The two differ exactly on echoes, and
    that difference is the evidence that the strict filter is doing work.

    Reads line by line and stops at the first strict hit: these files run to tens of KB and
    a refused run's frame lands within the first dozen lines.
    """
    strict_ts, loose = None, False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if REFUSAL_TEXT not in line:
                    continue
                loose = True
                if REFUSAL_PREFILTER not in line:
                    continue
                try:
                    frame = json.loads(line)
                except ValueError:
                    continue
                chunk = frame.get("chunk", "")
                if REFUSAL_STATUS in chunk.replace(" ", "") and REFUSAL_TEXT in chunk:
                    strict_ts = frame.get("ts")
                    break
    except OSError:
        return None, False
    return strict_ts, loose


def scan_agent(agent_dir):
    """(total_runs, [(ts, path)], loose_count) for one agent directory."""
    total, strict, loose = 0, [], 0
    try:
        names = sorted(os.listdir(agent_dir))
    except OSError:
        return 0, [], 0
    for name in names:
        if not name.endswith(".ndjson"):
            continue
        total += 1
        ts, was_loose = scan_run(os.path.join(agent_dir, name))
        if was_loose:
            loose += 1
        if ts:
            strict.append((ts, name))
    return total, strict, loose


def in_window(ts, since, until):
    """`until` is INCLUSIVE of the whole day, so --until 2026-07-30 keeps 07-30T23:59Z.

    An exclusive bound here would silently drop the last day of an episode, which is the
    same class of error as the truncated API window this script exists to replace.
    """
    day = ts[:10]
    if since and day < since:
        return False
    if until and day > until:
        return False
    return True


def main(argv):
    parser = argparse.ArgumentParser(prog="check_quota_refusals.py", add_help=True)
    parser.add_argument("--run-log-root", default=DEFAULT_RUN_LOG_ROOT)
    parser.add_argument("--company", default=None, help="company id; default = every company")
    parser.add_argument("--since", default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--until", default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--max-rate", type=float, default=DEFAULT_MAX_RATE)
    parser.add_argument("--warn-rate", type=float, default=DEFAULT_WARN_RATE)
    parser.add_argument(
        "--label", action="append", default=[], metavar="AGENTID=NAME",
        help="repeatable; label an agent id in the output",
    )
    args = parser.parse_args(argv[1:])

    if args.warn_rate >= args.max_rate:
        print(
            "usage error: --warn-rate (%g) must be below --max-rate (%g)"
            % (args.warn_rate, args.max_rate),
            file=sys.stderr,
        )
        return EXIT_USAGE

    labels = {}
    for pair in args.label:
        key, sep, value = pair.partition("=")
        if not sep:
            print("usage error: --label wants AGENTID=NAME, got %r" % pair, file=sys.stderr)
            return EXIT_USAGE
        labels[key] = value

    root = args.run_log_root
    if not os.path.isdir(root):
        print(
            "SKIPPED  run-log root %s\n"
            "    SKIP  not a directory. No run was enumerated, so this lane is uncertified "
            "for quota refusals, not clear of them. Name the root with --run-log-root." % root
        )
        return EXIT_UNEVALUATED

    companies = [args.company] if args.company else sorted(os.listdir(root))

    per_agent = {}
    by_day = collections.Counter()
    for company in companies:
        cdir = os.path.join(root, company)
        if not os.path.isdir(cdir):
            continue
        for agent in sorted(os.listdir(cdir)):
            adir = os.path.join(cdir, agent)
            if not os.path.isdir(adir):
                continue
            total, strict, loose = scan_agent(adir)
            if not total:
                continue
            kept = [(ts, name) for ts, name in strict if in_window(ts, args.since, args.until)]
            for ts, _ in kept:
                by_day[ts[:10]] += 1
            name = labels.get(agent, agent[:8])
            prev = per_agent.get(name, (0, 0, 0))
            per_agent[name] = (prev[0] + total, prev[1] + len(kept), prev[2] + loose)

    total_runs = sum(v[0] for v in per_agent.values())
    total_refused = sum(v[1] for v in per_agent.values())
    total_loose = sum(v[2] for v in per_agent.values())

    if not total_runs:
        print(
            "SKIPPED  run-log root %s\n"
            "    SKIP  0 run logs found under %d company dir(s). Nothing was measured."
            % (root, len(companies))
        )
        return EXIT_UNEVALUATED

    rate = total_refused / total_runs
    offenders = sorted(
        ((n, t, r) for n, (t, r, _) in per_agent.items() if r), key=lambda x: -x[2]
    )

    # The gate fires on the WORST LANE, not on the fleet average. The quota ceiling is
    # per-subscription, so refusals concentrate in whichever agents share the exhausted
    # account -- here the two Claude agents, at 33.9% and 46.4%, while all 8 MiniMax agents
    # sat at exactly 0.0%. A fleet-average gate is diluted by every quiet agent and gets
    # weaker each time one is hired: the same 929-refusal episode reads 24.6% fleet-wide
    # against 37.2% across the lane that was actually refused. Hire enough quiet agents and
    # a fully-walled lane passes a fleet-average check while burning every run it dispatches.
    worst_rate = max((r / t for t, r, _ in per_agent.values()), default=0.0)
    gate_rate = max(rate, worst_rate)

    if gate_rate > args.max_rate:
        status, code = "FAIL", EXIT_FAIL
    elif gate_rate > args.warn_rate:
        status, code = "WARN", EXIT_OK
    else:
        status, code = "PASS", EXIT_OK

    window = "%s..%s" % (args.since or "(all)", args.until or "(all)")
    print("%s  %s  %d/%d runs refused (%.1f%% fleet-wide)" % (status, window, total_refused, total_runs, 100 * rate))
    print(
        "    ceiling %.1f%%; warn %.1f%%; gated on the WORST LANE at %.1f%%, not the fleet average"
        % (100 * args.max_rate, 100 * args.warn_rate, 100 * worst_rate)
    )
    print(
        "    strict %d (result frame carries api_error_status 429) vs loose %d (mentions the "
        "text at all); the %d-run gap is transcript echoes, not refusals"
        % (total_refused, total_loose, total_loose - total_refused)
    )

    print("    per agent:")
    for name, (t, r, _) in sorted(per_agent.items(), key=lambda kv: -kv[1][1]):
        mark = "  <-- refusals" if r else ""
        print("        %-12s %5d runs  %5d refused  %5.1f%%%s" % (name, t, r, 100 * r / t, mark))

    if by_day:
        print("    by day:")
        for day in sorted(by_day):
            print("        %s  %d" % (day, by_day[day]))

    if offenders:
        print(
            "    NOTE  a refused run bills 0 and reports subtype=success. Do not read these "
            "as idle agents or as session-startup failures."
        )
    for name, t, r in offenders:
        if r / t > args.max_rate:
            print(
                "    %s  %s at %.1f%% is over the %.1f%% ceiling. Pacing (maxConcurrentRuns) "
                "caps the burst; the weekly ceiling is account-level and every agent on the "
                "same subscription inherits it."
                % ("FAIL" if code == EXIT_FAIL else "warn", name, 100 * r / t, 100 * args.max_rate)
            )
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
