#!/usr/bin/env python3
"""Rake a synthetic persona sample onto real-world marginal quotas.

Iterative Proportional Fitting (IPF / "raking"): you have a pool of
synthetic personas each tagged with categorical attributes (age band,
gender, region, ...). You know the TRUE marginal share of each attribute
from census / TGI / GWI. Raking assigns a weight to every persona so the
weighted marginals match every target marginal simultaneously — without
needing the full joint distribution (which surveys rarely publish).

Pure stdlib. python3.9 compatible. No numpy, no pandas.

Input  : JSON on stdin  { "personas": [ {attr: value, ...}, ... ],
                          "targets":  { attr: { value: share, ... }, ... } }
         shares per attribute must sum to ~1.0.
Output : JSON on stdout { "weights": [w0, w1, ...],
                          "achieved": { attr: {value: weighted_share} },
                          "iterations": n, "max_error": e }

Usage  : cat sample.json | python3 rake_quotas.py [--max-iter 50] [--tol 1e-6]
"""
import json
import sys
from collections import defaultdict


def rake(personas, targets, max_iter=50, tol=1e-6):
    n = len(personas)
    if n == 0:
        raise ValueError("no personas to rake")
    weights = [1.0] * n

    # Pre-index which personas fall in each (attr, value) cell.
    cells = {attr: defaultdict(list) for attr in targets}
    for i, p in enumerate(personas):
        for attr in targets:
            if attr in p:
                cells[attr][p[attr]].append(i)

    last_err = None
    for it in range(1, max_iter + 1):
        max_err = 0.0
        for attr, dist in targets.items():
            total = sum(weights)
            for value, share in dist.items():
                idx = cells[attr].get(value, [])
                current = sum(weights[i] for i in idx)
                current_share = current / total if total else 0.0
                if current == 0:
                    # No sample in a targeted cell — can't rake it. Flag loudly.
                    if share > 0:
                        max_err = max(max_err, share)
                    continue
                factor = (share * total) / current
                for i in idx:
                    weights[i] *= factor
                max_err = max(max_err, abs(current_share - share))
        last_err = max_err
        if max_err < tol:
            break

    # Report achieved marginals under final weights.
    total = sum(weights)
    achieved = {}
    for attr, dist in targets.items():
        achieved[attr] = {}
        for value in dist:
            idx = cells[attr].get(value, [])
            achieved[attr][value] = (sum(weights[i] for i in idx) / total) if total else 0.0

    return weights, achieved, it, last_err


def main():
    args = sys.argv[1:]
    max_iter = int(args[args.index("--max-iter") + 1]) if "--max-iter" in args else 50
    tol = float(args[args.index("--tol") + 1]) if "--tol" in args else 1e-6

    payload = json.load(sys.stdin)
    personas = payload["personas"]
    targets = payload["targets"]

    # Boundary validation: each target marginal should sum to ~1.
    for attr, dist in targets.items():
        s = sum(dist.values())
        if abs(s - 1.0) > 0.02:
            sys.stderr.write(f"warning: target '{attr}' shares sum to {s:.3f}, not 1.0\n")

    weights, achieved, iters, err = rake(personas, targets, max_iter, tol)
    json.dump({"weights": weights, "achieved": achieved,
               "iterations": iters, "max_error": err}, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
