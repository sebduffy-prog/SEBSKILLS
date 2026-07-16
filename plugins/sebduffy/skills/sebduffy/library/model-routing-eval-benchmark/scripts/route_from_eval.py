#!/usr/bin/env python3
"""Turn a promptfoo `export` JSON into a per-task-type routing decision table.

Reads promptfoo results, buckets each test by the `type` var (fallback: "all"),
and for each bucket picks the CHEAPEST provider whose mean pass rate is within
--tolerance of the best provider on that bucket. That is your routing rule:
send this task type to this vendor.

Usage:
    promptfoo eval -c promptfooconfig.yaml -o results.json
    python3 route_from_eval.py results.json --tolerance 0.03

Works with promptfoo's `export -o file.json` / `eval -o file.json` schema
(results.results[] rows carry .provider, .vars, .success, .score, .cost, .latencyMs).
No third-party deps.
"""
import argparse
import json
import sys
from collections import defaultdict


def load_rows(path):
    with open(path) as f:
        data = json.load(f)
    # promptfoo nests under results.results (v0.x/1.x); tolerate a bare list too.
    res = data.get("results", data)
    rows = res.get("results", res) if isinstance(res, dict) else res
    if not isinstance(rows, list):
        raise ValueError("Could not find a results array in the JSON")
    return rows


def provider_id(row):
    p = row.get("provider")
    if isinstance(p, dict):
        return p.get("id") or p.get("label") or str(p)
    return str(p)


def bucket_of(row, key):
    return str((row.get("vars") or {}).get(key, "all"))


def summarize(rows, bucket_key):
    # stats[bucket][provider] = {n, pass, cost, latency}
    stats = defaultdict(lambda: defaultdict(lambda: {"n": 0, "pass": 0.0, "cost": 0.0, "lat": 0.0}))
    for r in rows:
        b = bucket_of(r, bucket_key)
        p = provider_id(r)
        s = stats[b][p]
        s["n"] += 1
        s["pass"] += 1.0 if r.get("success") else 0.0
        s["cost"] += float(r.get("cost") or 0.0)
        s["lat"] += float(r.get("latencyMs") or r.get("latency") or 0.0)
    return stats


def decide(stats, tolerance):
    table = []
    for bucket in sorted(stats):
        provs = []
        for p, s in stats[bucket].items():
            n = max(s["n"], 1)
            provs.append({
                "provider": p,
                "pass_rate": s["pass"] / n,
                "avg_cost": s["cost"] / n,
                "avg_latency_ms": s["lat"] / n,
                "n": s["n"],
            })
        if not provs:
            continue
        best = max(p["pass_rate"] for p in provs)
        eligible = [p for p in provs if p["pass_rate"] >= best - tolerance]
        winner = min(eligible, key=lambda p: (p["avg_cost"], p["avg_latency_ms"]))
        table.append({"task_type": bucket, "route_to": winner["provider"],
                      "winner": winner, "all": sorted(provs, key=lambda x: -x["pass_rate"])})
    return table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_json")
    ap.add_argument("--bucket-var", default="type",
                    help="test var name to bucket by (default: type)")
    ap.add_argument("--tolerance", type=float, default=0.03,
                    help="max pass-rate gap from best that still counts as 'good enough' (default 0.03)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    rows = load_rows(args.results_json)
    stats = summarize(rows, args.bucket_var)
    table = decide(stats, args.tolerance)

    if args.json:
        print(json.dumps([{"task_type": t["task_type"], "route_to": t["route_to"],
                           "pass_rate": t["winner"]["pass_rate"],
                           "avg_cost": t["winner"]["avg_cost"]} for t in table], indent=2))
        return

    for t in table:
        w = t["winner"]
        print(f"\n### {t['task_type']}  ->  route to: {t['route_to']}")
        print(f"    winner pass={w['pass_rate']:.2%}  cost=${w['avg_cost']:.5f}  "
              f"lat={w['avg_latency_ms']:.0f}ms  n={w['n']}")
        for p in t["all"]:
            flag = " *" if p["provider"] == t["route_to"] else "  "
            print(f"   {flag} {p['provider']:<32} pass={p['pass_rate']:.2%} "
                  f"cost=${p['avg_cost']:.5f} lat={p['avg_latency_ms']:.0f}ms")
    if not table:
        print("No rows found — check the JSON path and schema.", file=sys.stderr)


if __name__ == "__main__":
    main()
