#!/usr/bin/env python3
"""Assemble an Anthropic Messages API request body that uses the server-side
tool-search tool to fight tool sprawl: keep a small "hot" set loaded and defer
the rest with defer_loading=true so only 3-5 tools ever enter context per turn.

Stdlib only. Works on macOS system python3 (3.9). Does NOT call the API — it
prints a ready-to-POST JSON body you can pipe to curl or an SDK.

Usage:
  python3 build_router_request.py TOOLS.json --hot get_weather,search_files \\
      --variant regex --model claude-opus-4-8 --prompt "weather in SF?"

TOOLS.json is a JSON array of standard tool definitions:
  [{"name": "...", "description": "...", "input_schema": {...}}, ...]
Tools whose name is in --hot load upfront; every other tool is deferred.
"""
import argparse
import json
import sys

# Server-side tool-search tool types (GA 2025-11-19). Regex => Python re.search
# patterns; bm25 => natural-language queries. See platform.claude.com tool-search.
SEARCH_TYPES = {
    "regex": "tool_search_tool_regex_20251119",
    "bm25": "tool_search_tool_bm25_20251119",
}
MAX_DEFERRED = 10000  # hard API limit on defer_loading:true tools per request


def build_body(tools, hot_names, variant, model, prompt, max_tokens):
    if variant not in SEARCH_TYPES:
        raise ValueError(f"variant must be one of {sorted(SEARCH_TYPES)}")
    if not isinstance(tools, list) or not tools:
        raise ValueError("TOOLS.json must be a non-empty JSON array of tool defs")

    hot = set(hot_names)
    known = {t.get("name") for t in tools}
    missing = hot - known
    if missing:
        raise ValueError(f"--hot names not present in TOOLS.json: {sorted(missing)}")

    # Search tool must never be deferred (API 400: "at least one tool must have
    # defer_loading=false"). Build it first, non-deferred.
    out_tools = [{"type": SEARCH_TYPES[variant], "name": SEARCH_TYPES[variant].rsplit("_", 1)[0]}]

    deferred = 0
    for t in tools:
        # Never mutate the caller's dict — emit a fresh copy (immutable style).
        entry = dict(t)
        if entry.get("name") in hot:
            entry.pop("defer_loading", None)  # hot => stays in context
        else:
            entry["defer_loading"] = True
            deferred += 1
        out_tools.append(entry)

    if deferred > MAX_DEFERRED:
        raise ValueError(f"{deferred} deferred tools exceeds API limit {MAX_DEFERRED}")
    if len(out_tools) == 1:
        raise ValueError("no real tools supplied alongside the search tool")

    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "tools": out_tools,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Build a tool-search Messages request body.")
    p.add_argument("tools_file", help="Path to JSON array of tool definitions")
    p.add_argument("--hot", default="", help="Comma-separated tool names to load upfront (non-deferred)")
    p.add_argument("--variant", default="regex", choices=sorted(SEARCH_TYPES))
    p.add_argument("--model", default="claude-opus-4-8")
    p.add_argument("--prompt", default="", help="User message text")
    p.add_argument("--max-tokens", type=int, default=2048)
    args = p.parse_args(argv)

    try:
        with open(args.tools_file, "r", encoding="utf-8") as fh:
            tools = json.load(fh)
        hot = [n.strip() for n in args.hot.split(",") if n.strip()]
        body = build_body(tools, hot, args.variant, args.model, args.prompt, args.max_tokens)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    json.dump(body, sys.stdout, indent=2)
    print()
    n_def = sum(1 for t in body["tools"] if t.get("defer_loading"))
    print(f"# {len(body['tools'])} tools total, {n_def} deferred, "
          f"{len(body['tools']) - n_def} loaded upfront (incl. search tool)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
