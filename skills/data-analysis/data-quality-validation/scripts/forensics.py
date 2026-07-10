#!/usr/bin/env python3
"""Integrity-forensics screens for survey / numeric data.

No third-party deps beyond pandas (stdlib math only otherwise). Screens:
  benford   - first-digit distribution vs Benford's Law (chi-sq + MAD)
  straight  - straight-lining / non-differentiation across Likert grid columns
  duplicates- fully/near duplicate respondent rows
  speeders  - completion-time outliers (too-fast respondents)

Usage:
  python3 forensics.py benford data.csv --col amount
  python3 forensics.py straight data.csv --cols q1,q2,q3,q4,q5
  python3 forensics.py duplicates data.csv --cols q1,q2,q3
  python3 forensics.py speeders data.csv --col duration_sec --floor 0.4

Exit code is non-zero when a screen flags a problem, so it composes in CI.
"""
import argparse
import math
import sys

import pandas as pd

# Benford expected P(first digit = d) = log10(1 + 1/d)
BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
# Nigrini MAD conformity bands for first-digit test
MAD_CLOSE, MAD_ACCEPT, MAD_MARGINAL = 0.006, 0.012, 0.015


def _first_digit(x):
    x = abs(float(x))
    if x == 0 or math.isnan(x) or math.isinf(x):
        return None
    while x < 1:
        x *= 10
    while x >= 10:
        x /= 10
    return int(x)


def benford(df, col):
    digits = [d for d in (_first_digit(v) for v in df[col].dropna()) if d]
    n = len(digits)
    if n < 300:
        print(f"WARN benford: only {n} usable values (<300); result unreliable")
    counts = {d: digits.count(d) for d in range(1, 10)}
    chi = sum((counts[d] - n * BENFORD[d]) ** 2 / (n * BENFORD[d]) for d in range(1, 10))
    mad = sum(abs(counts[d] / n - BENFORD[d]) for d in range(1, 10)) / 9
    print(f"benford col={col} n={n} chi2={chi:.2f} (crit@8df=15.51) MAD={mad:.5f}")
    for d in range(1, 10):
        print(f"  {d}: obs={counts[d]/n:6.2%} exp={BENFORD[d]:6.2%}")
    verdict = ("close" if mad < MAD_CLOSE else "acceptable" if mad < MAD_ACCEPT
               else "marginal" if mad < MAD_MARGINAL else "NONCONFORMANT")
    print(f"  verdict: {verdict}")
    return verdict == "NONCONFORMANT" or chi > 15.51


def straight(df, cols):
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    flat = (sub.nunique(axis=1) == 1)
    stdev = sub.std(axis=1)
    low = stdev < 0.5
    n = len(sub)
    print(f"straight cols={cols} n={n}")
    print(f"  identical-across-row: {flat.sum()} ({flat.mean():.1%})")
    print(f"  low-variance(<0.5sd): {low.sum()} ({low.mean():.1%})")
    if flat.any():
        print(f"  flagged row indices (first 20): {list(sub.index[flat])[:20]}")
    return flat.mean() > 0.05


def duplicates(df, cols):
    key = df[cols] if cols else df
    dup = key.duplicated(keep=False)
    print(f"duplicates cols={cols or 'ALL'} n={len(df)} duplicate_rows={dup.sum()} ({dup.mean():.1%})")
    if dup.any():
        print(f"  example indices: {list(df.index[dup])[:20]}")
    return dup.any()


def speeders(df, col, floor):
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    median = s.median()
    threshold = median * floor
    fast = s < threshold
    print(f"speeders col={col} n={len(s)} median={median:.1f} threshold={threshold:.1f} "
          f"({floor:.0%} of median)")
    print(f"  speeders: {fast.sum()} ({fast.mean():.1%})")
    return fast.mean() > 0.1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("screen", choices=["benford", "straight", "duplicates", "speeders"])
    p.add_argument("path")
    p.add_argument("--col")
    p.add_argument("--cols", help="comma-separated column list")
    p.add_argument("--floor", type=float, default=0.4, help="speeder threshold as fraction of median")
    a = p.parse_args()
    df = pd.read_csv(a.path) if a.path.endswith(".csv") else pd.read_parquet(a.path)
    cols = a.cols.split(",") if a.cols else None
    if a.screen == "benford":
        bad = benford(df, a.col)
    elif a.screen == "straight":
        bad = straight(df, cols)
    elif a.screen == "duplicates":
        bad = duplicates(df, cols)
    else:
        bad = speeders(df, a.col, a.floor)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
