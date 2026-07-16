#!/usr/bin/env python3
"""
cascade_sim.py — Independent-Cascade Monte Carlo on a synthetic social graph.

The LLM (Claude) does the *semantic* work: score how likely each persona is to
adopt/forward a specific message (0..1). This script does the *combinatorial*
work: propagate that message through a network thousands of times and turn the
runs into a virality forecast (reach curve, tipping point, super-spreaders).

Diffusion model: Independent Cascade (ICM). A newly-activated node u gets ONE
chance to activate each still-inactive neighbour v, succeeding with probability
    beta * p_v * (decay ** hop)
where p_v is v's Claude-scored adoption propensity, beta is a global
transmissibility knob (message "stickiness"/channel reach), and decay models
message erosion as it travels further from the source. This is the standard
ICM of Kempe, Kleinberg & Tardos (2003), extended with per-node receptivity
and hop-decay. It is a MECHANISTIC forecast, not a calibrated prediction.

Usage:
  # 1. Build a graph and write a node list for Claude to score:
  python3 cascade_sim.py scaffold --nodes 500 --graph ba --out run/

  # 2. (Claude fills run/adoption.json: {"0":0.12,"1":0.4,...} per node)

  # 3. Forecast reach for one message + find the tipping point + top spreaders:
  python3 cascade_sim.py run --graph-file run/graph.json \
      --adoption run/adoption.json --seeds 3 --runs 2000 --out run/forecast.json

No network calls. Pure networkx + numpy. Deterministic with --seed.
"""
import argparse, json, random, sys
from pathlib import Path

try:
    import networkx as nx
    import numpy as np
except ImportError:
    sys.exit("Needs networkx + numpy:  pip install networkx numpy")


# ---------- graph construction ----------------------------------------------

def build_graph(kind: str, n: int, seed: int, k: int = 6, p: float = 0.1) -> nx.Graph:
    """Synthetic audience topologies.

    ba  = Barabasi-Albert scale-free: heavy-tailed degree -> real hubs /
          super-spreaders. Best default for "influencer-shaped" audiences.
    ws  = Watts-Strogatz small-world: high clustering + short paths, models
          tight communities with occasional bridges.
    er  = Erdos-Renyi random: null model / sanity baseline, no hubs.
    """
    if kind == "ba":
        return nx.barabasi_albert_graph(n, m=max(1, k // 2), seed=seed)
    if kind == "ws":
        return nx.watts_strogatz_graph(n, k=k, p=p, seed=seed)
    if kind == "er":
        return nx.erdos_renyi_graph(n, p=min(1.0, k / n), seed=seed)
    raise ValueError(f"unknown graph kind: {kind}")


# ---------- independent cascade ---------------------------------------------

def cascade(g: nx.Graph, seeds, adopt, beta: float, decay: float, rng) -> dict:
    """One ICM realisation. Returns per-hop newly-activated counts + total."""
    active = set(seeds)
    frontier = list(seeds)
    hop = 0
    by_hop = [len(seeds)]
    while frontier:
        hop += 1
        prob_scale = beta * (decay ** hop)
        nxt = []
        for u in frontier:
            for v in g.neighbors(u):
                if v in active:
                    continue
                if rng.random() < prob_scale * adopt.get(v, 0.0):
                    active.add(v)
                    nxt.append(v)
        by_hop.append(len(nxt))
        frontier = nxt
    return {"total": len(active), "by_hop": by_hop}


def montecarlo(g, seeds, adopt, beta, decay, runs, rng) -> dict:
    totals, curves = [], []
    for _ in range(runs):
        r = cascade(g, seeds, adopt, beta, decay, rng)
        totals.append(r["total"])
        curves.append(r["by_hop"])
    totals = np.array(totals, dtype=float)
    width = max(len(c) for c in curves)
    padded = np.array([c + [0] * (width - len(c)) for c in curves], dtype=float)
    cum = np.cumsum(padded.mean(axis=0))
    return {
        "mean_reach": round(float(totals.mean()), 2),
        "median_reach": round(float(np.median(totals)), 2),
        "p90_reach": round(float(np.percentile(totals, 90)), 2),
        "std_reach": round(float(totals.std()), 2),
        "reach_pct": round(float(totals.mean()) / g.number_of_nodes() * 100, 2),
        "fizzle_rate": round(float((totals <= len(seeds) * 1.5).mean()), 3),
        "mean_cumulative_by_hop": [round(x, 1) for x in cum.tolist()],
    }


# ---------- tipping point ----------------------------------------------------

def tipping_sweep(g, seeds, adopt, decay, runs, rng, betas) -> list:
    """Sweep transmissibility; the tipping point is the beta where reach jumps
    from a fizzle to a system-wide cascade (a phase transition)."""
    out = []
    n = g.number_of_nodes()
    for b in betas:
        totals = np.array([cascade(g, seeds, adopt, b, decay, rng)["total"]
                           for _ in range(runs)], dtype=float)
        out.append({"beta": round(b, 3),
                    "reach_pct": round(totals.mean() / n * 100, 2)})
    return out


# ---------- super-spreaders --------------------------------------------------

def superspreaders(g, adopt, beta, decay, runs, rng, top: int) -> list:
    """Rank nodes by expected single-seed cascade size (spread influence).
    For big graphs this is approximated on the highest-degree candidates only,
    since exhaustive per-node Monte Carlo is expensive."""
    deg = dict(g.degree())
    candidates = sorted(deg, key=deg.get, reverse=True)[: min(len(deg), max(top * 5, 40))]
    scored = []
    r = max(50, runs // 10)
    for node in candidates:
        totals = [cascade(g, [node], adopt, beta, decay, rng)["total"] for _ in range(r)]
        scored.append({"node": int(node), "degree": deg[node],
                       "adopt": round(adopt.get(node, 0.0), 3),
                       "exp_reach": round(float(np.mean(totals)), 2)})
    scored.sort(key=lambda d: d["exp_reach"], reverse=True)
    return scored[:top]


# ---------- CLI --------------------------------------------------------------

def cmd_scaffold(a):
    g = build_graph(a.graph, a.nodes, a.seed, a.k, a.p)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    nx.write_gml(g, out / "graph.gml")
    json.dump(nx.node_link_data(g), open(out / "graph.json", "w"))
    deg = dict(g.degree())
    nodes = [{"node": int(nd), "degree": deg[nd]} for nd in g.nodes()]
    json.dump(nodes, open(out / "nodes.json", "w"), indent=2)
    # placeholder adoption Claude will overwrite with per-persona 0..1 scores
    json.dump({str(nd): 0.15 for nd in g.nodes()},
              open(out / "adoption.json", "w"), indent=2)
    print(f"Wrote graph ({g.number_of_nodes()} nodes, {g.number_of_edges()} edges) "
          f"+ nodes.json + adoption.json placeholder to {out}/")
    print("Next: have Claude assign each node/persona an adoption probability "
          "(0..1) for THIS message, overwrite adoption.json, then `run`.")


def cmd_run(a):
    data = json.load(open(a.graph_file))
    g = nx.node_link_graph(data)
    adopt = {int(k): float(v) for k, v in json.load(open(a.adoption)).items()}
    rng = random.Random(a.seed)
    deg = dict(g.degree())
    seeds = sorted(deg, key=deg.get, reverse=True)[: a.seeds] if a.seed_hubs \
        else rng.sample(list(g.nodes()), a.seeds)

    forecast = montecarlo(g, seeds, adopt, a.beta, a.decay, a.runs, rng)
    betas = [x / 100 for x in range(5, 105, 10)]
    tip = tipping_sweep(g, seeds, adopt, a.decay, max(200, a.runs // 4), rng, betas)
    spreaders = superspreaders(g, adopt, a.beta, a.decay, a.runs, rng, a.top)

    # tipping point = first beta where mean reach crosses 15% of the network
    tp = next((r["beta"] for r in tip if r["reach_pct"] >= 15.0), None)

    result = {
        "graph": {"nodes": g.number_of_nodes(), "edges": g.number_of_edges()},
        "params": {"seeds": seeds, "seed_hubs": a.seed_hubs, "beta": a.beta,
                   "decay": a.decay, "runs": a.runs},
        "forecast": forecast,
        "tipping_point_beta": tp,
        "tipping_curve": tip,
        "super_spreaders": spreaders,
    }
    if a.out:
        json.dump(result, open(a.out, "w"), indent=2)
    print(json.dumps(result, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scaffold", help="build a synthetic graph + node list")
    s.add_argument("--nodes", type=int, default=500)
    s.add_argument("--graph", choices=["ba", "ws", "er"], default="ba")
    s.add_argument("--k", type=int, default=6, help="avg/target degree knob")
    s.add_argument("--p", type=float, default=0.1, help="rewire prob (ws only)")
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--out", default="run/")
    s.set_defaults(func=cmd_scaffold)

    r = sub.add_parser("run", help="forecast reach, tipping point, spreaders")
    r.add_argument("--graph-file", required=True)
    r.add_argument("--adoption", required=True, help="{node: 0..1} JSON from Claude")
    r.add_argument("--seeds", type=int, default=3, help="how many seed nodes")
    r.add_argument("--seed-hubs", action="store_true",
                   help="seed the highest-degree nodes (influencer launch) "
                        "instead of random accounts")
    r.add_argument("--beta", type=float, default=0.4, help="transmissibility 0..1")
    r.add_argument("--decay", type=float, default=0.85, help="per-hop message decay")
    r.add_argument("--runs", type=int, default=2000)
    r.add_argument("--top", type=int, default=10)
    r.add_argument("--seed", type=int, default=42)
    r.add_argument("--out", default=None)
    r.set_defaults(func=cmd_run)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
