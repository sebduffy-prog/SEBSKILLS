#!/usr/bin/env python3
"""Marginal-return budget allocation across multiple Retail Media Networks (RMNs).

Each RMN is modelled with a diminishing-returns saturation curve:

    incremental_sales(spend) = ceiling * (1 - exp(-spend / halfpoint))

where `ceiling` is the max incremental sales the network can drive at that
funnel stage, and `halfpoint` is the spend that reaches ~63% of the ceiling.
Marginal incremental return at spend s is the curve's derivative:

    dSales/dSpend = (ceiling / halfpoint) * exp(-s / halfpoint)

The optimiser pours budget in small steps into whichever eligible network has
the highest *marginal* incremental return, honouring per-network min/max caps.
This is a planning heuristic, not a substitute for a fitted MMM or a clean-room
incrementality test — feed it curves derived from those.

Input JSON (list of networks):
[
  {"name": "Amazon (Sponsored Products)", "ceiling": 900000, "halfpoint": 120000,
   "min": 50000, "max": 400000},
  {"name": "Walmart Connect (onsite)",    "ceiling": 500000, "halfpoint": 90000},
  {"name": "Walmart DSP (offsite CTV)",   "ceiling": 350000, "halfpoint": 140000}
]

Usage:
  python3 allocate.py --budget 600000 --plan networks.json
  python3 allocate.py --budget 600000 --plan networks.json --step 5000 --json
"""
import argparse
import json
import math
import sys


def incremental_sales(spend, ceiling, halfpoint):
    """Total incremental sales driven by `spend` on one network."""
    if halfpoint <= 0:
        raise ValueError("halfpoint must be > 0")
    return ceiling * (1.0 - math.exp(-spend / halfpoint))


def marginal_return(spend, ceiling, halfpoint):
    """Incremental sales per next dollar at current `spend` (the derivative)."""
    return (ceiling / halfpoint) * math.exp(-spend / halfpoint)


def validate(networks):
    """Fail fast on malformed plans — never trust external JSON."""
    if not isinstance(networks, list) or not networks:
        raise ValueError("plan must be a non-empty JSON list of networks")
    seen = set()
    for n in networks:
        name = n.get("name")
        if not name:
            raise ValueError("every network needs a 'name'")
        if name in seen:
            raise ValueError(f"duplicate network name: {name}")
        seen.add(name)
        for key in ("ceiling", "halfpoint"):
            if not isinstance(n.get(key), (int, float)) or n[key] <= 0:
                raise ValueError(f"{name}: '{key}' must be a positive number")
        if n.get("min", 0) > n.get("max", float("inf")):
            raise ValueError(f"{name}: min exceeds max")


def allocate(networks, budget, step):
    """Greedy marginal allocation. Returns new list; never mutates input."""
    if budget <= 0:
        raise ValueError("budget must be > 0")
    if step <= 0:
        raise ValueError("step must be > 0")

    spend = {n["name"]: float(n.get("min", 0.0)) for n in networks}
    committed = sum(spend.values())
    if committed > budget:
        raise ValueError("sum of per-network minimums exceeds total budget")

    remaining = budget - committed
    by_name = {n["name"]: n for n in networks}

    while remaining > 1e-9:
        chunk = min(step, remaining)
        best, best_mr = None, -1.0
        for name, n in by_name.items():
            cap = n.get("max", float("inf"))
            if spend[name] + chunk > cap + 1e-9:
                continue
            mr = marginal_return(spend[name], n["ceiling"], n["halfpoint"])
            if mr > best_mr:
                best, best_mr = name, mr
        if best is None:  # every network at its cap
            break
        spend[best] += chunk
        remaining -= chunk

    rows = []
    for n in networks:
        s = spend[n["name"]]
        sales = incremental_sales(s, n["ceiling"], n["halfpoint"])
        rows.append({
            "name": n["name"],
            "spend": round(s, 2),
            "incremental_sales": round(sales, 2),
            "iroas": round(sales / s, 2) if s > 0 else 0.0,
            "marginal_iroas": round(
                marginal_return(s, n["ceiling"], n["halfpoint"]), 3),
        })
    return rows, round(budget - remaining, 2), round(remaining, 2)


def main():
    p = argparse.ArgumentParser(description="Multi-RMN budget allocator")
    p.add_argument("--budget", type=float, required=True, help="total budget")
    p.add_argument("--plan", required=True, help="path to networks JSON")
    p.add_argument("--step", type=float, default=1000.0,
                   help="allocation granularity (default 1000)")
    p.add_argument("--json", action="store_true", help="emit JSON not a table")
    args = p.parse_args()

    with open(args.plan) as f:
        networks = json.load(f)
    validate(networks)
    rows, spent, unspent = allocate(networks, args.budget, args.step)

    if args.json:
        print(json.dumps({"allocation": rows, "spent": spent,
                          "unallocated": unspent}, indent=2))
        return

    total_sales = sum(r["incremental_sales"] for r in rows)
    print(f"{'Network':<34}{'Spend':>13}{'Inc.Sales':>14}{'iROAS':>8}{'mgROAS':>9}")
    print("-" * 78)
    for r in rows:
        print(f"{r['name']:<34}{r['spend']:>13,.0f}{r['incremental_sales']:>14,.0f}"
              f"{r['iroas']:>8.2f}{r['marginal_iroas']:>9.3f}")
    print("-" * 78)
    blended = total_sales / spent if spent else 0.0
    print(f"{'TOTAL':<34}{spent:>13,.0f}{total_sales:>14,.0f}{blended:>8.2f}")
    if unspent > 0:
        print(f"\nUnallocated (all networks hit max caps): {unspent:,.0f}")


if __name__ == "__main__":
    main()
