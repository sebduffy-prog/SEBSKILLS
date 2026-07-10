#!/usr/bin/env python3
"""Cheap-first cascade router for a single vendor (Anthropic tiers).

Escalation loop: try the cheapest model, ask it to self-rate confidence, and
only escalate to the next tier when confidence is below a floor. Cuts spend by
serving the long tail of easy requests on Haiku while hard ones climb to Opus.

Usage:
    ANTHROPIC_API_KEY=... python3 cascade_route.py "your prompt here"
    ANTHROPIC_API_KEY=... python3 cascade_route.py --floor 0.75 "prompt"

Env knobs:
    ANTHROPIC_API_KEY   required
    CASCADE_TIERS       comma list, cheap->expensive (default below)
    CASCADE_FLOOR       confidence floor 0..1 to accept a tier (default 0.7)
"""
import argparse
import json
import os
import re
import sys

# Cheap -> expensive. Override with CASCADE_TIERS. Use current Anthropic IDs.
DEFAULT_TIERS = [
    "claude-haiku-4-5",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
]

RATED_SUFFIX = (
    "\n\nAfter your answer, on a final separate line output exactly:\n"
    'CONFIDENCE: <float 0.0-1.0>\n'
    "where the float is your calibrated probability that the answer above is "
    "fully correct and complete. Be honest; a low score triggers escalation to "
    "a stronger model."
)

CONF_RE = re.compile(r"CONFIDENCE:\s*([01](?:\.\d+)?)", re.IGNORECASE)


def parse_confidence(text: str) -> float:
    """Pull the trailing CONFIDENCE float; default low so unknowns escalate."""
    matches = CONF_RE.findall(text or "")
    if not matches:
        return 0.0
    try:
        return max(0.0, min(1.0, float(matches[-1])))
    except ValueError:
        return 0.0


def strip_confidence(text: str) -> str:
    return CONF_RE.sub("", text or "").rstrip()


def run_tier(client, model: str, prompt: str, max_tokens: int):
    """Call one model; return (clean_answer, confidence). Never raises upward
    without context so the caller can decide to escalate or fail."""
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt + RATED_SUFFIX}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    return strip_confidence(raw), parse_confidence(raw)


def cascade(prompt: str, tiers, floor: float, max_tokens: int) -> dict:
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit("pip install anthropic")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY")

    client = Anthropic()
    trace = []
    for tier in tiers:
        try:
            answer, conf = run_tier(client, tier, prompt, max_tokens)
        except Exception as exc:  # noqa: BLE001 - surface, then try next tier
            trace.append({"model": tier, "error": str(exc)})
            continue
        trace.append({"model": tier, "confidence": conf})
        if conf >= floor:
            return {"model": tier, "confidence": conf, "answer": answer,
                    "escalations": len(trace) - 1, "trace": trace}
    # Exhausted tiers: return the strongest attempt we have, if any.
    last = next((t for t in reversed(trace) if "error" not in t), None)
    return {"model": tiers[-1], "confidence": last["confidence"] if last else 0.0,
            "answer": answer if "answer" in dir() else "",
            "escalations": len(tiers) - 1, "trace": trace,
            "note": "floor never met; returning top-tier answer"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--floor", type=float,
                    default=float(os.environ.get("CASCADE_FLOOR", "0.7")))
    ap.add_argument("--max-tokens", type=int, default=1024)
    args = ap.parse_args()

    tiers = os.environ.get("CASCADE_TIERS")
    tiers = [t.strip() for t in tiers.split(",")] if tiers else DEFAULT_TIERS

    result = cascade(args.prompt, tiers, args.floor, args.max_tokens)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
