#!/usr/bin/env python3
"""Wave-over-wave significance for brand tracker metrics (two-proportion z-test).

Answers the one question every tracker readout must answer honestly:
"Did this metric REALLY move, or is it sampling noise?"

No external deps (math + argparse only) so it runs on the stock macOS
python3 (3.9). For a % metric measured on two independent samples (e.g.
prompted awareness this wave vs last wave), it returns the z-score, a
two-sided p-value, and a plain-English verdict at 95% and 90% confidence.

Usage:
  python3 wave_sig.py --p1 0.42 --n1 500 --p2 0.47 --n2 512
  python3 wave_sig.py --x1 210 --n1 500 --x2 240 --n2 512   # counts, not rates
  python3 wave_sig.py --p1 0.42 --n1 500 --p2 0.47 --n2 512 --deff 1.5  # weighted

--deff applies a design effect (variance inflation from weighting/clustering);
effective n = n / deff. Typical online-panel DEFF is 1.2-2.0. If in doubt,
use 1.5 rather than pretending weighted data is a simple random sample.
"""
import argparse
import math


def two_proportion_z(x1, n1, x2, n2, deff=1.0):
    """Return (p1, p2, diff, z, p_value) for wave1 vs wave2 (pooled z-test)."""
    if n1 <= 0 or n2 <= 0:
        raise ValueError("sample sizes must be > 0")
    n1_eff, n2_eff = n1 / deff, n2 / deff
    p1, p2 = x1 / n1, x2 / n2
    if not (0 <= p1 <= 1 and 0 <= p2 <= 1):
        raise ValueError("proportions must be within [0, 1]")
    pooled = (x1 + x2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1_eff + 1 / n2_eff))
    if se == 0:
        return p1, p2, p2 - p1, 0.0, 1.0
    z = (p2 - p1) / se
    # two-sided p-value from the normal CDF via erf
    p_value = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return p1, p2, p2 - p1, z, p_value


def verdict(p_value):
    if p_value < 0.05:
        return "SIGNIFICANT at 95% -- report the move as real"
    if p_value < 0.10:
        return "DIRECTIONAL at 90% -- flag as a soft signal, watch next wave"
    return "NOT SIGNIFICANT -- within sampling noise, do NOT call it a change"


def main():
    ap = argparse.ArgumentParser(description="Wave-over-wave two-proportion z-test")
    ap.add_argument("--p1", type=float, help="wave-1 proportion (0-1)")
    ap.add_argument("--p2", type=float, help="wave-2 proportion (0-1)")
    ap.add_argument("--x1", type=float, help="wave-1 success count (alt to --p1)")
    ap.add_argument("--x2", type=float, help="wave-2 success count (alt to --p2)")
    ap.add_argument("--n1", type=float, required=True, help="wave-1 base size")
    ap.add_argument("--n2", type=float, required=True, help="wave-2 base size")
    ap.add_argument("--deff", type=float, default=1.0, help="design effect (default 1.0)")
    a = ap.parse_args()

    x1 = a.x1 if a.x1 is not None else (a.p1 * a.n1 if a.p1 is not None else None)
    x2 = a.x2 if a.x2 is not None else (a.p2 * a.n2 if a.p2 is not None else None)
    if x1 is None or x2 is None:
        ap.error("provide --p1/--p2 (rates) or --x1/--x2 (counts)")

    p1, p2, diff, z, pv = two_proportion_z(x1, a.n1, x2, a.n2, a.deff)
    print(f"Wave 1: {p1*100:.1f}%  (n={a.n1:.0f})")
    print(f"Wave 2: {p2*100:.1f}%  (n={a.n2:.0f})")
    print(f"Change: {diff*100:+.1f} pts   z={z:+.2f}   p={pv:.4f}   deff={a.deff}")
    print(verdict(pv))


if __name__ == "__main__":
    main()
