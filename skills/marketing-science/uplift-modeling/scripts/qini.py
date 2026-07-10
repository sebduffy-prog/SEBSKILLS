#!/usr/bin/env python3
"""Zero-dependency (numpy-only) Qini curve + AUUC for a scored uplift model.

Use this to sanity-check any uplift model WITHOUT installing causalml — pass a
CSV that has a treatment flag (0/1), a binary outcome (0/1), and a per-row
predicted uplift score (tau_hat). It ranks rows by predicted uplift, then walks
the population from most- to least-persuadable, accumulating the incremental
outcome vs a random-targeting baseline.

Qini value at fraction f (Radcliffe 2007):
    Q(f) = Y_t(f) - Y_c(f) * N_t(f)/N_c(f)
where Y_t/Y_c are cumulative positive outcomes in treatment/control among the
top-f ranked rows, and N_t/N_c are the cumulative counts. AUUC is the area
under this curve (trapezoid), normalized by the overall treatment lift so 1.0 ==
perfect ranking-vs-random separation is comparable across datasets.

Usage:
    python3 qini.py data.csv --treatment w --outcome y --uplift tau_hat
    python3 qini.py --selftest
"""
import argparse
import csv
import sys

import numpy as np

# numpy renamed trapz -> trapezoid in 2.0; support both.
_trapz = getattr(np, "trapezoid", None) or np.trapz


def qini_curve(treatment, outcome, uplift, n_bins=100):
    """Return (fractions, qini_values, auuc_normalized).

    treatment, outcome, uplift: 1-D arrays of equal length.
    """
    treatment = np.asarray(treatment, dtype=float)
    outcome = np.asarray(outcome, dtype=float)
    uplift = np.asarray(uplift, dtype=float)
    n = len(uplift)
    if n == 0:
        raise ValueError("empty input")

    order = np.argsort(-uplift, kind="mergesort")  # stable, high uplift first
    t = treatment[order]
    y = outcome[order]

    cum_t = np.cumsum(t)                    # treated seen so far
    cum_c = np.cumsum(1.0 - t)              # control seen so far
    cum_yt = np.cumsum(y * t)              # positive outcomes among treated
    cum_yc = np.cumsum(y * (1.0 - t))     # positive outcomes among control

    # Qini: incremental gain vs scaled control response.
    with np.errstate(divide="ignore", invalid="ignore"):
        scaled_ctrl = np.where(cum_c > 0, cum_yc * cum_t / cum_c, 0.0)
    qini = cum_yt - scaled_ctrl

    fractions = np.arange(1, n + 1) / n

    # Random baseline: straight line to the endpoint value.
    end = qini[-1]
    random_line = fractions * end
    # Area between model curve and random diagonal (trapezoid), normalized.
    area_model = _trapz(qini, fractions)
    area_random = _trapz(random_line, fractions)
    denom = abs(area_random) if area_random != 0 else 1.0
    auuc_norm = (area_model - area_random) / denom

    # Downsample to n_bins points for a compact returned curve.
    if n > n_bins:
        idx = np.linspace(0, n - 1, n_bins).astype(int)
        return fractions[idx], qini[idx], float(auuc_norm)
    return fractions, qini, float(auuc_norm)


def _load_csv(path, treatment_col, outcome_col, uplift_col):
    t, y, u = [], [], []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for col in (treatment_col, outcome_col, uplift_col):
            if col not in reader.fieldnames:
                raise SystemExit(f"column '{col}' not in {reader.fieldnames}")
        for row in reader:
            t.append(float(row[treatment_col]))
            y.append(float(row[outcome_col]))
            u.append(float(row[uplift_col]))
    return np.array(t), np.array(y), np.array(u)


def _selftest():
    rng = np.random.default_rng(0)
    n = 4000
    t = rng.integers(0, 2, n).astype(float)
    # True uplift only for a "persuadable" 25% of the population.
    persuadable = rng.random(n) < 0.25
    base = 0.10
    p = base + 0.30 * persuadable * t
    y = (rng.random(n) < p).astype(float)
    tau_hat = persuadable.astype(float) + rng.normal(0, 0.05, n)  # good scorer
    _, _, auuc_good = qini_curve(t, y, tau_hat)
    _, _, auuc_rand = qini_curve(t, y, rng.random(n))  # random scorer
    print(f"good-scorer normalized AUUC: {auuc_good:.3f}")
    print(f"random-scorer normalized AUUC: {auuc_rand:.3f}")
    assert auuc_good > auuc_rand, "good scorer must beat random"
    assert auuc_good > 0.1, "good scorer should show clear positive lift"
    print("SELFTEST PASSED")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", nargs="?", help="input CSV")
    ap.add_argument("--treatment", default="w")
    ap.add_argument("--outcome", default="y")
    ap.add_argument("--uplift", default="tau_hat")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        _selftest()
        return
    if not args.csv:
        ap.error("provide a CSV path or --selftest")

    t, y, u = _load_csv(args.csv, args.treatment, args.outcome, args.uplift)
    fractions, qini, auuc = qini_curve(t, y, u)
    print(f"rows={len(t)} normalized_AUUC={auuc:.4f}")
    print("fraction,qini")
    for f, q in zip(fractions, qini):
        print(f"{f:.3f},{q:.3f}")


if __name__ == "__main__":
    main()
