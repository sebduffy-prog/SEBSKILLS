#!/usr/bin/env python3
"""Score-distribution drift monitor. Pure stdlib (py3.9+).

Compares a LIVE sample of scores against a GOLDEN/baseline distribution and
flags drift via PSI (Population Stability Index), a two-sample KS statistic,
and mean shift. Exits non-zero when drift breaches thresholds so it can gate
CI or trigger an alert.

Inputs are JSON files: either a flat list of numbers, or a list of trace
objects from which --field extracts the score.

Usage:
  drift.py --baseline golden.json --live live.json [--field score] \
           [--psi-warn 0.1] [--psi-alert 0.25] [--ks-alert 0.2] [--bins 10] \
           [--metric faithfulness]

Reference thresholds (industry convention):
  PSI < 0.10  stable | 0.10-0.25 moderate drift | > 0.25 significant drift.
"""
import argparse
import json
import math
import sys

EPS = 1e-6  # avoids log(0) / divide-by-zero in PSI


def load_scores(path, field):
    with open(path) as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(data).__name__}")
    out = []
    for i, row in enumerate(data):
        if isinstance(row, (int, float)):
            out.append(float(row))
        elif isinstance(row, dict):
            if field not in row:
                raise ValueError(f"{path}[{i}]: no field '{field}' (have {list(row)})")
            out.append(float(row[field]))
        else:
            raise ValueError(f"{path}[{i}]: unsupported element type {type(row).__name__}")
    if not out:
        raise ValueError(f"{path}: no scores found")
    return out


def edges(values, bins):
    lo, hi = min(values), max(values)
    if hi == lo:
        hi = lo + 1.0  # degenerate: single-value baseline
    step = (hi - lo) / bins
    return [lo + step * k for k in range(bins + 1)]


def hist(values, bin_edges):
    counts = [0] * (len(bin_edges) - 1)
    last = len(counts) - 1
    for v in values:
        idx = int((v - bin_edges[0]) / (bin_edges[-1] - bin_edges[0]) * len(counts))
        idx = min(max(idx, 0), last)  # clamp out-of-range into end bins
        counts[idx] += 1
    total = sum(counts) or 1
    return [c / total for c in counts]


def psi(base, live, bins):
    e = edges(base, bins)
    b, l = hist(base, e), hist(live, e)
    total = 0.0
    for pb, pl in zip(b, l):
        pb, pl = max(pb, EPS), max(pl, EPS)
        total += (pl - pb) * math.log(pl / pb)
    return total


def ks_statistic(base, live):
    """Two-sample Kolmogorov-Smirnov D: max gap between empirical CDFs."""
    sb, sl = sorted(base), sorted(live)
    grid = sorted(set(sb) | set(sl))
    nb, nl = len(sb), len(sl)

    def cdf(sorted_vals, n, x):
        # count of values <= x, via linear scan (grid is modest)
        return sum(1 for v in sorted_vals if v <= x) / n

    return max(abs(cdf(sb, nb, x) - cdf(sl, nl, x)) for x in grid)


def mean(xs):
    return sum(xs) / len(xs)


def main():
    ap = argparse.ArgumentParser(description="Score-distribution drift monitor")
    ap.add_argument("--baseline", required=True, help="Golden/reference scores JSON")
    ap.add_argument("--live", required=True, help="Live-sample scores JSON")
    ap.add_argument("--field", default="score", help="Field to extract from objects")
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--psi-warn", type=float, default=0.10)
    ap.add_argument("--psi-alert", type=float, default=0.25)
    ap.add_argument("--ks-alert", type=float, default=0.20)
    ap.add_argument("--metric", default="score", help="Metric label for the report")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = ap.parse_args()

    try:
        base = load_scores(args.baseline, args.field)
        live = load_scores(args.live, args.field)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    p = psi(base, live, args.bins)
    d = ks_statistic(base, live)
    shift = mean(live) - mean(base)

    if p >= args.psi_alert or d >= args.ks_alert:
        status, code = "ALERT", 1
    elif p >= args.psi_warn:
        status, code = "WARN", 0
    else:
        status, code = "STABLE", 0

    report = {
        "metric": args.metric,
        "status": status,
        "psi": round(p, 4),
        "ks": round(d, 4),
        "mean_shift": round(shift, 4),
        "baseline_mean": round(mean(base), 4),
        "live_mean": round(mean(live), 4),
        "n_baseline": len(base),
        "n_live": len(live),
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"[{status}] metric={args.metric}  PSI={p:.4f}  KS={d:.4f}  "
              f"mean {mean(base):.3f} -> {mean(live):.3f} (Δ{shift:+.3f})  "
              f"n={len(base)}/{len(live)}")
    return code


if __name__ == "__main__":
    sys.exit(main())
