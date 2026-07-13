#!/usr/bin/env python3
"""Build a hypothesis-indexed creative variant matrix (a "slate").

Stdlib only. Reads a factors JSON, emits a slate CSV where every variant is
tagged with the ONE thing that makes it differ from the control cell, so a
downstream pretest / Meta audit can attribute a score to a cause.

factors JSON shape (each factor is a named list, first entry = control level):
{
  "value_prop": ["saves-time", "saves-money", "status"],
  "avatar":     ["busy-parent", "gen-z-saver"],
  "hook":       ["problem-agitate", "bold-claim", "question"],
  "format":     ["9x16-story", "1x1-square"],
  "style":      ["ugc-selfie", "hypermotion", "unboxing"]
}

Designs:
  ofat   (default) one-factor-at-a-time: control + each non-control level of
         each factor, varied singly. Clean attribution, small n.
  pairs  control + every OFAT variant + all 2-factor interaction cells built
         from non-control levels. Bigger, tests interactions.
  full   full cartesian product (capped by --max). Max coverage, no attribution
         discipline — use only when you truly want every cell.
"""
import argparse
import csv
import itertools
import json
import sys


def load_factors(path):
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict) or not data:
        raise ValueError("factors JSON must be a non-empty object of name -> [levels]")
    for name, levels in data.items():
        if not isinstance(levels, list) or len(levels) < 1:
            raise ValueError("factor '%s' must be a non-empty list of levels" % name)
    return data


def control_cell(factors):
    return {name: levels[0] for name, levels in factors.items()}


def ofat_rows(factors):
    """Control, then vary exactly one factor to each of its non-control levels."""
    control = control_cell(factors)
    rows = [(dict(control), "H000-control", "control", "none")]
    hyp = 0
    for name, levels in factors.items():
        for level in levels[1:]:
            hyp += 1
            cell = dict(control)
            cell[name] = level
            rows.append((cell, "H%03d" % hyp, "H000-control", name))
    return rows


def pair_rows(factors):
    """OFAT rows plus every 2-factor interaction of non-control levels."""
    rows = ofat_rows(factors)
    control = control_cell(factors)
    names = list(factors.keys())
    hyp = len([r for r in rows if r[3] != "none"])
    for a, b in itertools.combinations(names, 2):
        for la in factors[a][1:]:
            for lb in factors[b][1:]:
                hyp += 1
                cell = dict(control)
                cell[a], cell[b] = la, lb
                rows.append((cell, "H%03d" % hyp, "H000-control", "%s+%s" % (a, b)))
    return rows


def full_rows(factors, cap):
    names = list(factors.keys())
    combos = itertools.product(*[factors[n] for n in names])
    control = control_cell(factors)
    rows = []
    for i, combo in enumerate(combos):
        if i >= cap:
            sys.stderr.write("full: capped at %d cells (raise --max to see more)\n" % cap)
            break
        cell = dict(zip(names, combo))
        varied = [n for n in names if cell[n] != control[n]]
        tag = "none" if not varied else "+".join(varied)
        rows.append((cell, "H%03d" % i, "H000-control", tag))
    return rows


def priority(factor_varied):
    # single-factor cells score highest: they yield clean, attributable reads
    if factor_varied == "none":
        return 100
    return 90 if "+" not in factor_varied else 60


def build(factors, design, cap):
    if design == "ofat":
        return ofat_rows(factors)
    if design == "pairs":
        return pair_rows(factors)
    if design == "full":
        return full_rows(factors, cap)
    raise ValueError("design must be ofat|pairs|full")


def write_csv(rows, factor_names, out):
    cols = (["variant_id", "hypothesis_id", "derived_from", "factor_varied"]
            + list(factor_names)
            + ["priority", "status", "prompt", "result_url", "job_id"])
    w = csv.writer(out)
    w.writerow(cols)
    for n, (cell, hyp, derived, varied) in enumerate(rows, start=1):
        base = ["V%03d" % n, hyp, derived, varied]
        levels = [cell[name] for name in factor_names]
        tail = [priority(varied), "", "", "", ""]  # status/prompt/url/job blank
        w.writerow(base + levels + tail)


def main():
    ap = argparse.ArgumentParser(description="Build a hypothesis-indexed creative slate CSV")
    ap.add_argument("factors", help="path to factors JSON")
    ap.add_argument("--design", default="ofat", choices=["ofat", "pairs", "full"])
    ap.add_argument("--max", type=int, default=300, help="cell cap for --design full")
    ap.add_argument("--out", default="-", help="output CSV path (default stdout)")
    a = ap.parse_args()

    factors = load_factors(a.factors)
    rows = build(factors, a.design, a.max)
    factor_names = list(factors.keys())

    if a.out == "-":
        write_csv(rows, factor_names, sys.stdout)
    else:
        with open(a.out, "w", newline="") as f:
            write_csv(rows, factor_names, f)
    sys.stderr.write("%d variants written (design=%s)\n" % (len(rows), a.design))


if __name__ == "__main__":
    main()
