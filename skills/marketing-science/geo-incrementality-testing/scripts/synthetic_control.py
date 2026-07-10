#!/usr/bin/env python3
"""Synthetic-control geo-lift estimator (no R, no PyMC required).

Fits a convex synthetic control (non-negative weights that sum to 1) on the
pre-treatment window, projects the counterfactual through the treatment window,
and reports ATT / cumulative lift / % lift. Ships an in-space placebo
permutation test that yields an exact-style p-value from the treated unit's
rank among control units by post/pre RMSPE ratio (Abadie et al. 2010).

Deps: numpy + scipy only. Input is a LONG-format panel CSV.

Usage:
  python3 synthetic_control.py --data panel.csv \
      --treated "chicago" --treatment-start 2026-04-01 \
      [--location-col location] [--date-col date] [--y-col Y]

Emits a JSON summary to stdout.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict

import numpy as np
from scipy.optimize import minimize


def load_panel(path, loc_col, date_col, y_col):
    """Read long CSV -> (locations, sorted_dates, Y matrix [n_loc x n_date])."""
    series = defaultdict(dict)  # location -> {date: value}
    dates = set()
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for req in (loc_col, date_col, y_col):
            if req not in reader.fieldnames:
                raise SystemExit(f"ERROR: column '{req}' not in {reader.fieldnames}")
        for row in reader:
            loc = row[loc_col].strip()
            date = row[date_col].strip()
            try:
                val = float(row[y_col])
            except ValueError:
                raise SystemExit(f"ERROR: non-numeric {y_col}={row[y_col]!r} at {loc}/{date}")
            series[loc][date] = val
            dates.add(date)
    sorted_dates = sorted(dates)
    locations = sorted(series)
    matrix = np.full((len(locations), len(sorted_dates)), np.nan)
    for i, loc in enumerate(locations):
        for j, date in enumerate(sorted_dates):
            if date in series[loc]:
                matrix[i, j] = series[loc][date]
    if np.isnan(matrix).any():
        raise SystemExit("ERROR: panel is unbalanced (missing loc/date cells). Fill gaps first.")
    return locations, sorted_dates, matrix


def fit_weights(treated_pre, donors_pre):
    """Convex weights w>=0, sum(w)=1 minimising pre-period RMSE. donors_pre: [n_donor x T_pre]."""
    n = donors_pre.shape[0]

    def loss(w):
        return np.sqrt(np.mean((treated_pre - w @ donors_pre) ** 2))

    w0 = np.full(n, 1.0 / n)
    bounds = [(0.0, 1.0)] * n
    cons = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    res = minimize(loss, w0, method="SLSQP", bounds=bounds, constraints=cons,
                   options={"maxiter": 500, "ftol": 1e-10})
    return res.x


def rmspe(actual, synth):
    return float(np.sqrt(np.mean((actual - synth) ** 2)))


def estimate(matrix, locations, treated_idx, split):
    """Fit SC for treated_idx, return dict of effect stats. split = first post index."""
    treated = matrix[treated_idx]
    donor_idx = [i for i in range(len(locations)) if i != treated_idx]
    donors = matrix[donor_idx]
    w = fit_weights(treated[:split], donors[:, :split])
    synth = w @ donors
    gap = treated - synth
    pre_rmspe = rmspe(treated[:split], synth[:split])
    post_rmspe = rmspe(treated[split:], synth[split:])
    att = float(np.mean(gap[split:]))
    cumulative = float(np.sum(gap[split:]))
    pct = float(cumulative / np.sum(synth[split:])) if np.sum(synth[split:]) else float("nan")
    ratio = post_rmspe / pre_rmspe if pre_rmspe > 0 else float("inf")
    return {
        "weights": {locations[donor_idx[k]]: round(float(w[k]), 4)
                    for k in range(len(donor_idx)) if w[k] > 1e-3},
        "att": att, "cumulative_lift": cumulative, "pct_lift": pct,
        "pre_rmspe": pre_rmspe, "post_rmspe": post_rmspe, "rmspe_ratio": ratio,
        "gap": gap.tolist(),
    }


def main():
    ap = argparse.ArgumentParser(description="Synthetic-control geo-lift estimator")
    ap.add_argument("--data", required=True)
    ap.add_argument("--treated", required=True, help="treated location name")
    ap.add_argument("--treatment-start", required=True, help="first treated date (in date col)")
    ap.add_argument("--location-col", default="location")
    ap.add_argument("--date-col", default="date")
    ap.add_argument("--y-col", default="Y")
    args = ap.parse_args()

    locations, dates, matrix = load_panel(args.data, args.location_col, args.date_col, args.y_col)
    if args.treated not in locations:
        raise SystemExit(f"ERROR: treated '{args.treated}' not in {locations}")
    if args.treatment_start not in dates:
        raise SystemExit(f"ERROR: treatment-start '{args.treatment_start}' not in date range "
                         f"{dates[0]}..{dates[-1]}")
    split = dates.index(args.treatment_start)
    if split < 3:
        raise SystemExit("ERROR: need >=3 pre-period points to fit a stable synthetic control")

    treated_idx = locations.index(args.treated)
    main_fit = estimate(matrix, locations, treated_idx, split)

    # In-space placebo: refit treating each donor as if treated; rank by RMSPE ratio.
    ratios = {args.treated: main_fit["rmspe_ratio"]}
    for i, loc in enumerate(locations):
        if i == treated_idx:
            continue
        try:
            ratios[loc] = estimate(matrix, locations, i, split)["rmspe_ratio"]
        except Exception:
            ratios[loc] = 0.0
    ranked = sorted(ratios.values(), reverse=True)
    rank = ranked.index(main_fit["rmspe_ratio"]) + 1
    p_value = rank / len(ratios)  # fraction of placebos with ratio >= treated

    out = {
        "treated": args.treated,
        "treatment_start": args.treatment_start,
        "pre_periods": split,
        "post_periods": len(dates) - split,
        "donor_weights": main_fit["weights"],
        "att_per_period": round(main_fit["att"], 4),
        "cumulative_lift": round(main_fit["cumulative_lift"], 4),
        "pct_lift": round(main_fit["pct_lift"], 4),
        "pre_rmspe": round(main_fit["pre_rmspe"], 4),
        "placebo_p_value": round(p_value, 4),
        "placebo_rank": f"{rank}/{len(ratios)}",
        "note": "pct_lift is cumulative gap / cumulative synthetic in post-window. "
                "p_value is in-space placebo rank (lower = more significant).",
    }
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
