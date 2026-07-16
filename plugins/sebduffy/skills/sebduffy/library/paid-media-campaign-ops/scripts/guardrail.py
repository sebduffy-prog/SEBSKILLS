#!/usr/bin/env python3
"""Pre-flight guardrails for paid-media budget + frequency changes.

Runs anywhere with stdlib only (Python 3.9+). Use BEFORE any live budget
mutation (`meta ads budget ... --live`, Google Ads mutate) so a fat-fingered
figure or a fatigued audience never reaches the platform.

Two independent checks:

  budget   Validate a proposed daily-budget change against an absolute cap
           and a max single-step % increase. Amounts are MINOR UNITS (cents /
           pence) to match Meta's daily_budget / --daily-budget convention.

  freq     Read a Meta insights JSON blob (`meta ads insights get --format json`)
           and block if average frequency exceeds a ceiling (fatigue guard).

Exit code 0 = ALLOW, 1 = BLOCK, 2 = usage error. Wire the exit code into CI
or a shell `&&` chain so a BLOCK halts the pipeline.
"""
import argparse
import json
import sys


def check_budget(current_minor: int, proposed_minor: int, cap_minor: int,
                 max_step_pct: float) -> int:
    if proposed_minor <= 0:
        print(f"BLOCK: proposed budget {proposed_minor} must be > 0")
        return 1
    if proposed_minor > cap_minor:
        print(f"BLOCK: proposed {proposed_minor} exceeds cap {cap_minor} "
              f"(minor units)")
        return 1
    if current_minor > 0:
        step_pct = (proposed_minor - current_minor) / current_minor * 100.0
        if step_pct > max_step_pct:
            print(f"BLOCK: {step_pct:.1f}% step exceeds max {max_step_pct:.1f}% "
                  f"({current_minor} -> {proposed_minor}). Ramp gradually.")
            return 1
        print(f"ALLOW: {step_pct:+.1f}% step, {proposed_minor} within cap "
              f"{cap_minor}")
    else:
        print(f"ALLOW: initial budget {proposed_minor} within cap {cap_minor}")
    return 0


def check_frequency(insights_path: str, ceiling: float) -> int:
    try:
        with open(insights_path) as fh:
            data = json.load(fh)
    except (OSError, ValueError) as err:
        print(f"BLOCK: cannot read insights JSON: {err}")
        return 1
    rows = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        rows = [rows]
    worst = None
    for row in rows:
        # Meta returns "frequency" directly, or derive from impressions/reach.
        freq = row.get("frequency")
        if freq is None:
            reach = float(row.get("reach") or 0)
            impr = float(row.get("impressions") or 0)
            freq = impr / reach if reach else 0.0
        freq = float(freq)
        label = row.get("campaign_id") or row.get("adset_id") or "row"
        if worst is None or freq > worst[1]:
            worst = (label, freq)
        flag = "BLOCK" if freq > ceiling else "ok"
        print(f"  {label}: frequency={freq:.2f} [{flag}]")
    if worst and worst[1] > ceiling:
        print(f"BLOCK: {worst[0]} frequency {worst[1]:.2f} > ceiling {ceiling}")
        return 1
    print(f"ALLOW: all frequencies <= ceiling {ceiling}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Paid-media pre-flight guardrails")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("budget", help="validate a budget change (minor units)")
    b.add_argument("--current", type=int, required=True)
    b.add_argument("--proposed", type=int, required=True)
    b.add_argument("--cap", type=int, required=True)
    b.add_argument("--max-step-pct", type=float, default=20.0)

    f = sub.add_parser("freq", help="frequency ceiling from insights JSON")
    f.add_argument("--insights", required=True, help="path to insights JSON")
    f.add_argument("--ceiling", type=float, default=3.0)

    args = p.parse_args()
    if args.cmd == "budget":
        return check_budget(args.current, args.proposed, args.cap,
                            args.max_step_pct)
    return check_frequency(args.insights, args.ceiling)


if __name__ == "__main__":
    sys.exit(main())
