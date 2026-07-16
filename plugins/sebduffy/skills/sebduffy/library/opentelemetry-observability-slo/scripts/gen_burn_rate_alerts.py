#!/usr/bin/env python3
"""Generate Google-SRE multiwindow multi-burn-rate Prometheus alert rules.

Emits a Prometheus rules YAML implementing the 4-alert burn-rate scheme from
the SRE Workbook (chapter "Alerting on SLOs"). Burn rate = fraction of the
30-day error budget consumed per hour, normalised to 1.0 = budget exactly
exhausted at the window horizon.

Requires an SLI ratio recording rule that yields the *error* ratio over a
window, named like  job:slo_errors:ratio_rate1h  (0.0 = perfect, 1.0 = all bad).
You provide the metric prefix; this script wires the windows and thresholds.

Usage:
    python3 gen_burn_rate_alerts.py --service checkout --objective 99.9 \
        --sli-prefix job:slo_errors:ratio_rate

No third-party deps (stdlib only) so it runs anywhere python3 does.
"""
import argparse
import sys

# (long_window, short_window, budget-consumed fraction that defines the tier,
#  hours_to_exhaustion, severity). Burn rate is derived from budget fraction.
# Per SRE Workbook table for a 30-day (720h) SLO window.
TIERS = [
    # long, short, budget_fraction, severity
    ("1h", "5m", 0.02, "page"),   # 14.4x
    ("6h", "30m", 0.05, "page"),  # 6x
    ("3d", "6h", 0.10, "ticket"),  # 1x
]
SLO_WINDOW_HOURS = 720  # 30 days


def burn_rate(budget_fraction: str, long_window_hours: float) -> float:
    return round((budget_fraction * SLO_WINDOW_HOURS) / long_window_hours, 4)


def hours(window: str) -> float:
    unit = window[-1]
    n = float(window[:-1])
    return {"m": n / 60, "h": n, "d": n * 24}[unit]


def make_rules(service: str, objective: float, prefix: str) -> str:
    budget = round(1 - objective / 100, 6)  # e.g. 99.9 -> 0.001
    out = [
        "groups:",
        f"  - name: {service}-slo-burn-rate",
        "    rules:",
    ]
    for long_w, short_w, frac, sev in TIERS:
        br = burn_rate(frac, hours(long_w))
        threshold = round(br * budget, 8)
        # Alert fires only when BOTH windows exceed the threshold.
        out += [
            f"      - alert: {service}_ErrorBudgetBurn_{long_w}",
            f"        expr: |",
            f"          {prefix}{long_w}{{service=\"{service}\"}} > {threshold}",
            f"          and",
            f"          {prefix}{short_w}{{service=\"{service}\"}} > {threshold}",
            f"        for: 2m",
            f"        labels:",
            f"          severity: {sev}",
            f"          service: {service}",
            f"        annotations:",
            f"          summary: \"{service} burning error budget at {br}x (budget {frac*100:.0f}% in {long_w})\"",
            f"          description: \"SLO {objective}% — long window {long_w} and short window {short_w} both exceed {threshold}.\"",
        ]
    return "\n".join(out) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--service", required=True)
    p.add_argument("--objective", type=float, required=True, help="e.g. 99.9")
    p.add_argument("--sli-prefix", default="job:slo_errors:ratio_rate",
                   help="recording-rule prefix; window suffix appended (…rate1h)")
    a = p.parse_args()
    if not 0 < a.objective < 100:
        print("objective must be between 0 and 100", file=sys.stderr)
        return 2
    sys.stdout.write(make_rules(a.service, a.objective, a.sli_prefix))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
