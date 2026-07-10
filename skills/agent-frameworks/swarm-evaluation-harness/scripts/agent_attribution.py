#!/usr/bin/env python3
"""Per-agent cost / latency / handoff attribution from a flat list of trace spans.

Framework-agnostic. Feed it spans you pulled from ANY tracer (DeepEval, OTel,
LangSmith, your own logger). Each span is a dict:

    {
      "span_id":   "s3",              # unique
      "parent_id": "s1" | None,       # None => root
      "agent":     "planner",         # which agent owns this span (required)
      "type":      "agent"|"llm"|"tool",
      "cost_usd":  0.0021,            # optional, defaults 0
      "latency_ms": 812,             # optional, defaults 0
    }

Outputs a per-agent rollup and the handoff edge list (agent A -> agent B when a
child span's agent differs from its parent's agent). Pure stdlib.

    python3 agent_attribution.py spans.json
    cat spans.json | python3 agent_attribution.py -
"""
import json
import sys
from collections import defaultdict


def attribute(spans):
    if not isinstance(spans, list):
        raise ValueError("spans must be a JSON array of span objects")
    by_id = {}
    for s in spans:
        sid = s.get("span_id")
        if not sid:
            raise ValueError(f"span missing span_id: {s!r}")
        if not s.get("agent"):
            raise ValueError(f"span {sid} missing 'agent'")
        by_id[sid] = s

    rollup = defaultdict(lambda: {"spans": 0, "cost_usd": 0.0, "latency_ms": 0})
    handoffs = defaultdict(int)

    for s in spans:
        agent = s["agent"]
        r = rollup[agent]
        r["spans"] += 1
        r["cost_usd"] += float(s.get("cost_usd") or 0)
        r["latency_ms"] += float(s.get("latency_ms") or 0)
        parent = by_id.get(s.get("parent_id"))
        if parent and parent["agent"] != agent:
            handoffs[(parent["agent"], agent)] += 1

    total_cost = sum(r["cost_usd"] for r in rollup.values())
    out = {
        "agents": {
            a: {
                **{k: round(v, 6) if isinstance(v, float) else v for k, v in r.items()},
                "cost_pct": round(100 * r["cost_usd"] / total_cost, 1) if total_cost else 0.0,
            }
            for a, r in sorted(rollup.items(), key=lambda kv: -kv[1]["cost_usd"])
        },
        "handoffs": [
            {"from": a, "to": b, "count": n}
            for (a, b), n in sorted(handoffs.items(), key=lambda kv: -kv[1])
        ],
        "total_cost_usd": round(total_cost, 6),
    }
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    raw = sys.stdin.read() if src == "-" else open(src).read()
    print(json.dumps(attribute(json.loads(raw)), indent=2))


if __name__ == "__main__":
    main()
