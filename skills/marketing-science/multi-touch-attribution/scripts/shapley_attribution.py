#!/usr/bin/env python3
"""Order-independent Shapley-value attribution over customer journeys.

Stdlib only (no pandas / numpy) so it runs anywhere python3 does.

Characteristic function: v(S) = conversions from every journey whose SET of
unique channels is a subset of coalition S (i.e. that journey could have been
produced using only channels in S). This is the standard cooperative-game
formulation used for marketing attribution (Google/Shao-Li style, made
order-independent by collapsing each journey to its channel set).

Shapley value of a channel = its average marginal contribution to v() across
all orderings of the players. Exact enumeration is O(n! ) so we use Monte-Carlo
permutation sampling, which is unbiased and converges fast. For small n
(<= exact_max) we enumerate all permutations for an exact answer.

Input CSV: two columns, `path` and `conversions`.
  path        = channels in the journey separated by `sep` (default ">")
  conversions = number of converting journeys with that path (int/float)
Non-converting paths are simply omitted (or given conversions=0).

Usage:
  python3 shapley_attribution.py journeys.csv --sep ">" --nsim 20000 --seed 0
"""
import argparse
import csv
import itertools
import random
from collections import defaultdict

EXACT_MAX = 8  # enumerate all n! orderings at/below this many channels


def load_journeys(path_csv, sep):
    """Return (coalition_value fn inputs): dict[frozenset]->conv, set of channels."""
    conv_by_set = defaultdict(float)
    channels = set()
    with open(path_csv, newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "path" not in reader.fieldnames \
                or "conversions" not in reader.fieldnames:
            raise ValueError("CSV must have header columns: path, conversions")
        for row in reader:
            raw = (row.get("path") or "").strip()
            if not raw:
                continue
            try:
                conv = float(row.get("conversions") or 0)
            except ValueError:
                raise ValueError(f"non-numeric conversions: {row.get('conversions')!r}")
            if conv <= 0:
                continue
            chans = frozenset(c.strip() for c in raw.split(sep) if c.strip())
            if not chans:
                continue
            conv_by_set[chans] += conv
            channels.update(chans)
    return dict(conv_by_set), sorted(channels)


def make_value_fn(conv_by_set):
    """v(S): total conversions of journeys whose channel-set is a subset of S."""
    items = list(conv_by_set.items())

    def v(coalition):
        s = coalition  # a set/frozenset
        return sum(conv for cset, conv in items if cset <= s)

    return v


def shapley_exact(channels, v):
    n = len(channels)
    contrib = {c: 0.0 for c in channels}
    perms = list(itertools.permutations(channels))
    for perm in perms:
        coalition = set()
        prev = 0.0
        for c in perm:
            coalition.add(c)
            cur = v(coalition)
            contrib[c] += cur - prev
            prev = cur
    for c in channels:
        contrib[c] /= len(perms)
    return contrib


def shapley_montecarlo(channels, v, nsim, seed):
    rng = random.Random(seed)
    contrib = {c: 0.0 for c in channels}
    order = list(channels)
    for _ in range(nsim):
        rng.shuffle(order)
        coalition = set()
        prev = 0.0
        for c in order:
            coalition.add(c)
            cur = v(coalition)
            contrib[c] += cur - prev
            prev = cur
    for c in channels:
        contrib[c] /= nsim
    return contrib


def attribute(path_csv, sep=">", nsim=20000, seed=0):
    conv_by_set, channels = load_journeys(path_csv, sep)
    total = sum(conv_by_set.values())
    if not channels:
        return {}, 0.0
    v = make_value_fn(conv_by_set)
    if len(channels) <= EXACT_MAX:
        shap = shapley_exact(channels, v)
        method = "exact"
    else:
        shap = shapley_montecarlo(channels, v, nsim, seed)
        method = f"montecarlo(nsim={nsim})"
    # Shapley values are efficient: they sum to v(grand coalition) = total.
    return shap, total, method


def main():
    ap = argparse.ArgumentParser(description="Shapley-value channel attribution")
    ap.add_argument("csv", help="journeys CSV with columns: path, conversions")
    ap.add_argument("--sep", default=">", help="channel separator in path (default '>')")
    ap.add_argument("--nsim", type=int, default=20000, help="MC permutations if n>8")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    shap, total, method = attribute(args.csv, args.sep, args.nsim, args.seed)
    print(f"# Shapley attribution ({method}); total conversions = {total:.2f}")
    print(f"{'channel':<20}{'conversions':>14}{'share':>10}")
    for c, val in sorted(shap.items(), key=lambda kv: -kv[1]):
        share = (val / total * 100) if total else 0
        print(f"{c:<20}{val:>14.3f}{share:>9.2f}%")
    check = sum(shap.values())
    print(f"# sum check: {check:.3f} (should equal total {total:.2f})")


if __name__ == "__main__":
    main()
