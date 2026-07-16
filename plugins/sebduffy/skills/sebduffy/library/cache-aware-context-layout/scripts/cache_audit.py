#!/usr/bin/env python3
"""Audit a request payload for prompt-cache friendliness.

Reads a JSON file describing an Anthropic (or OpenAI-shaped) request and reports
whether the layout maximises provider prompt-cache hit rate: static content up
front, one volatile suffix, no cache breakpoint on a block that changes per call.

Usage:
  python3 cache_audit.py request.json [--min-tokens 1024]

Input shapes accepted:
  {"system": <str|list>, "tools": [...], "messages": [...]}   # Anthropic
  {"messages": [...]}                                          # OpenAI/chat

Exit code 0 = cache-friendly, 1 = issues found. Pure stdlib; no network calls.
"""
import argparse, json, re, sys

# Tokens ~= chars/4 is the standard rough estimate; good enough for a layout audit.
CHARS_PER_TOKEN = 4
# Substrings that signal per-call volatile content sitting in a would-be static prefix.
VOLATILE_HINTS = re.compile(
    r"\{\{|\}\}|<[A-Za-z_]+>|timestamp|current_time|datetime|uuid|request_id|"
    r"session_id|\bnow\b|\btoday\b|random|nonce",
    re.IGNORECASE,
)


def block_text(block):
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        return block.get("text") or block.get("content") or ""
    if isinstance(block, list):
        return "".join(block_text(b) for b in block)
    return ""


def est_tokens(text):
    return len(text) // CHARS_PER_TOKEN


def has_breakpoint(block):
    return isinstance(block, dict) and "cache_control" in block


def audit(payload, min_tokens):
    issues, notes = [], []

    # Flatten the logical prefix in provider order: tools -> system -> messages.
    segments = []  # (label, text, block)
    for tool in payload.get("tools", []) or []:
        segments.append(("tools", json.dumps(tool, sort_keys=True), tool))
    sysv = payload.get("system")
    if isinstance(sysv, list):
        for b in sysv:
            segments.append(("system", block_text(b), b))
    elif sysv:
        segments.append(("system", block_text(sysv), sysv))
    for m in payload.get("messages", []) or []:
        c = m.get("content")
        blocks = c if isinstance(c, list) else [c]
        for b in blocks:
            segments.append((f"messages[{m.get('role','?')}]", block_text(b), b))

    if not segments:
        return ["empty payload: nothing to cache"], []

    total = sum(est_tokens(t) for _, l, _ in [(s[0], s[1], s[2]) for s in segments] for t in [l])
    notes.append(f"~{total} prefix tokens across {len(segments)} block(s)")

    # 1. Static prefix must clear the model minimum, or no breakpoint ever hits.
    if total < min_tokens:
        issues.append(
            f"prefix is ~{total} tok < {min_tokens} min: too small to cache on this model")

    # 2. Volatile content in the front third defeats the shared prefix for every caller.
    running = 0
    front_cut = total // 3 or 1
    for label, text, _ in segments:
        running += est_tokens(text)
        if running <= front_cut and VOLATILE_HINTS.search(text):
            hit = VOLATILE_HINTS.search(text).group(0)
            issues.append(
                f"volatile token ({hit!r}) in {label} inside the static prefix: "
                "move per-call/dynamic data to the SUFFIX (end of messages)")

    # 3. A cache breakpoint sitting on the last (volatile) block never gets reused.
    bp_positions = [i for i, (_, _, b) in enumerate(segments) if has_breakpoint(b)]
    if bp_positions:
        notes.append(f"explicit breakpoints at block index {bp_positions}")
        if len(bp_positions) > 4:
            issues.append(f"{len(bp_positions)} breakpoints > 4 max allowed per request")
        if bp_positions[-1] == len(segments) - 1 and len(segments) > 1:
            last_txt = segments[-1][1]
            if VOLATILE_HINTS.search(last_txt) or est_tokens(last_txt) < min_tokens:
                issues.append(
                    "last breakpoint is on the final block: place it on the last STATIC "
                    "shared block so the next request reads it instead of re-writing")
    else:
        notes.append("no explicit cache_control found (relying on automatic caching)")

    return issues, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--min-tokens", type=int, default=1024,
                    help="model minimum cacheable tokens (1024 default; 2048 Haiku 3.5)")
    a = ap.parse_args()
    with open(a.path) as f:
        payload = json.load(f)
    issues, notes = audit(payload, a.min_tokens)
    for n in notes:
        print(f"  note: {n}")
    if issues:
        print(f"\n{len(issues)} cache issue(s):")
        for i in issues:
            print(f"  ✘ {i}")
        sys.exit(1)
    print("\n✓ layout is cache-friendly")


if __name__ == "__main__":
    main()
