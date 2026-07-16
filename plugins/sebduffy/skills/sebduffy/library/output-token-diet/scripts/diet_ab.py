#!/usr/bin/env python3
"""A/B output-token harness: baseline vs dieted prompt, per Anthropic call.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python diet_ab.py prompts.jsonl [--model claude-sonnet-4-5] [--out-price 15]

prompts.jsonl: one JSON object per line, {"prompt": "...", "expect": "42"}
  "expect" is optional; if present the answer is checked (substring, case-insensitive).

Prints per-prompt output_tokens baseline vs dieted, the reduction %, dollars
saved (at --out-price $/1M output tokens), and a count of answers that changed.
Only trust a diet that cuts tokens AND leaves the "changed" count at 0.
"""
import argparse
import json
import sys

VERBOSE_SYSTEM = "Answer the question and show your reasoning."
DIET_SYSTEM = (
    "Think step by step, but keep each reasoning step to at most 5 words. "
    "Then output only the final answer after '####'. "
    "No preamble, no restating the question, no summary."
)


def extract(text: str) -> str:
    return text.split("####")[-1].strip() if "####" in text else text.strip()


def run(client, model: str, system: str, prompt: str, max_tokens: int):
    r = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        stop_sequences=["\n\n\n"],
    )
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    return text, r.usage.output_tokens, r.stop_reason


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompts")
    ap.add_argument("--model", default="claude-sonnet-4-5")
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--out-price", type=float, default=15.0, help="$/1M output tokens")
    args = ap.parse_args()

    try:
        import anthropic
    except ImportError:
        print("pip install anthropic", file=sys.stderr)
        return 2
    client = anthropic.Anthropic()

    rows = []
    with open(args.prompts) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    base_tot = diet_tot = 0
    changed = truncated = 0
    print(f"{'#':>3}  {'base':>6} {'diet':>6} {'cut%':>5}  answer")
    for i, row in enumerate(rows, 1):
        prompt, expect = row["prompt"], row.get("expect")
        bt, bo, _ = run(client, args.model, VERBOSE_SYSTEM, prompt, args.max_tokens)
        dt, do, dstop = run(client, args.model, DIET_SYSTEM, prompt, args.max_tokens)
        base_tot += bo
        diet_tot += do
        if dstop == "max_tokens":
            truncated += 1
        cut = 100 * (bo - do) / bo if bo else 0
        ans = extract(dt)
        ok = True
        if expect is not None:
            ok = expect.lower() in ans.lower()
            if not ok:
                changed += 1
        flag = "" if ok else "  <-- ANSWER CHANGED"
        print(f"{i:>3}  {bo:>6} {do:>6} {cut:>4.0f}%  {ans[:40]!r}{flag}")

    saved = (base_tot - diet_tot) / 1_000_000 * args.out_price
    mean_cut = 100 * (base_tot - diet_tot) / base_tot if base_tot else 0
    print(f"\nTotal output tokens: base={base_tot} diet={diet_tot} "
          f"({mean_cut:.0f}% cut)  saved=${saved:.4f} at ${args.out_price}/1M")
    print(f"Answers changed: {changed}   Truncated (raise --max-tokens): {truncated}")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
