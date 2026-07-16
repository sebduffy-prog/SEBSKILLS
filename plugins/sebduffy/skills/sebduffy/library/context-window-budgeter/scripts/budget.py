#!/usr/bin/env python3
"""Priority-based context-window budgeter.

Given a token budget and a list of context sources (each with a priority and,
optionally, degrade steps), find the highest priority cutoff whose surviving
sources fit the budget -- then optionally degrade the cheapest survivors to
reclaim more room. Same idea as anysphere/priompt's priority-cutoff render,
but source-agnostic and dependency-light.

Token counting uses tiktoken when installed; otherwise a ~4-chars/token
heuristic. Reserve headroom for the model's own generation with --reserve.

Input JSON (stdin or file): a list of sources, e.g.
  [
    {"id": "system",       "priority": 100, "text": "..."},
    {"id": "tool_result",  "priority": 40,  "text": "...",
       "degrade": ["...short summary...", "(omitted)"]},
    {"id": "old_turn",     "priority": 10,  "text": "..."}
  ]

Higher priority = keep first. `degrade` is an ordered list of progressively
cheaper replacements tried (in order) when the full text does not fit.

Usage:
  python3 budget.py --budget 8000 --reserve 1500 sources.json
  cat sources.json | python3 budget.py --budget 8000 --model gpt-4o
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

CHARS_PER_TOKEN = 4  # fallback heuristic when tiktoken is absent


def make_counter(model: str):
    """Return a fn(str)->int token counter. Prefer tiktoken, else heuristic."""
    try:
        import tiktoken

        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return lambda s: len(enc.encode(s or ""))
    except ImportError:
        return lambda s: (len(s or "") + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def validate(sources: Any) -> list[dict]:
    if not isinstance(sources, list):
        raise ValueError("input must be a JSON list of source objects")
    out = []
    for i, s in enumerate(sources):
        if not isinstance(s, dict):
            raise ValueError(f"source[{i}] is not an object")
        if "text" not in s or not isinstance(s["text"], str):
            raise ValueError(f"source[{i}] missing string 'text'")
        s.setdefault("id", f"src{i}")
        s.setdefault("priority", 0)
        if not isinstance(s["priority"], (int, float)):
            raise ValueError(f"source[{i}].priority must be a number")
        degrade = s.get("degrade", [])
        if not isinstance(degrade, list) or any(not isinstance(d, str) for d in degrade):
            raise ValueError(f"source[{i}].degrade must be a list of strings")
        out.append(s)
    return out


def variants(source: dict) -> list[str]:
    """Full text, then each degrade step, then empty (drop)."""
    return [source["text"], *source.get("degrade", []), ""]


def budget(sources: list[dict], limit: int, count) -> dict:
    """Greedy by descending priority: for each source pick the richest
    variant that still fits the remaining budget. Deterministic and O(n)."""
    kept, used = [], 0
    ordered = sorted(sources, key=lambda s: (-s["priority"], sources.index(s)))
    for s in ordered:
        remaining = limit - used
        chosen, chosen_tokens, level = None, 0, 0
        for lvl, text in enumerate(variants(s)):
            t = count(text)
            if t <= remaining:
                chosen, chosen_tokens, level = text, t, lvl
                break
        if chosen and chosen != "":
            used += chosen_tokens
            kept.append(
                {"id": s["id"], "priority": s["priority"], "level": level,
                 "tokens": chosen_tokens, "text": chosen,
                 "degraded": level > 0}
            )
        else:
            kept.append(
                {"id": s["id"], "priority": s["priority"], "level": -1,
                 "tokens": 0, "text": "", "dropped": True}
            )
    kept.sort(key=lambda k: (-k["priority"], sources.index(next(s for s in sources if s["id"] == k["id"]))))
    return {"limit": limit, "used": used, "free": limit - used, "sources": kept}


def main() -> int:
    ap = argparse.ArgumentParser(description="Priority-based context budgeter")
    ap.add_argument("file", nargs="?", help="sources JSON file (default: stdin)")
    ap.add_argument("--budget", type=int, required=True, help="total token budget")
    ap.add_argument("--reserve", type=int, default=0, help="tokens to hold back for generation")
    ap.add_argument("--model", default="gpt-4o", help="model name for tiktoken encoding")
    ap.add_argument("--assemble", action="store_true", help="print the assembled context text only")
    args = ap.parse_args()

    raw = open(args.file).read() if args.file else sys.stdin.read()
    try:
        sources = validate(json.loads(raw))
    except (json.JSONDecodeError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    limit = args.budget - args.reserve
    if limit <= 0:
        print("error: budget minus reserve must be > 0", file=sys.stderr)
        return 1

    result = budget(sources, limit, make_counter(args.model))

    if args.assemble:
        print("\n\n".join(s["text"] for s in result["sources"] if s.get("text")))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
