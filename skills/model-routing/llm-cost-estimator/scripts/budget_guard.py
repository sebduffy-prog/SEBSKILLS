#!/usr/bin/env python3
"""Pre-flight LLM cost estimation + hard budget cap.

Prices a prompt BEFORE it is sent, and refuses (or warns) when the estimated
spend would breach a cap. Backed by AgentOps-AI/tokencost (Decimal USD pricing
for 400+ models, sourced from the LiteLLM model_prices JSON).

    pip install tokencost

Usage (CLI):
    python budget_guard.py --model gpt-4o --max-usd 0.05 --prompt-file req.txt \\
        --expected-output-tokens 800

Usage (library):
    from budget_guard import estimate, guard
    est = estimate(messages, model="claude-sonnet-4-5", expected_output_tokens=1000)
    guard(est, max_usd=0.02)   # raises BudgetExceeded if over cap
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import List, Dict, Union

Messages = Union[str, List[Dict[str, str]]]


class BudgetExceeded(RuntimeError):
    """Raised when an estimated call would breach the configured cap."""


@dataclass
class Estimate:
    model: str
    prompt_tokens: int
    expected_output_tokens: int
    prompt_cost_usd: str      # str(Decimal) — keep full precision, JSON-safe
    output_cost_usd: str
    total_usd: str

    def total(self) -> Decimal:
        return Decimal(self.total_usd)


def estimate(messages: Messages, model: str, expected_output_tokens: int = 0) -> Estimate:
    """Price a prompt + an assumed output length without making any API call."""
    # Imported lazily so `--help` works without the dep installed.
    from tokencost import (
        count_message_tokens,
        count_string_tokens,
        calculate_prompt_cost,
        calculate_cost_by_tokens,
    )

    if isinstance(messages, str):
        prompt_tokens = count_string_tokens(prompt=messages, model=model)
    else:
        prompt_tokens = count_message_tokens(messages=messages, model=model)

    prompt_cost: Decimal = calculate_prompt_cost(messages, model)
    # Output isn't generated yet — price the *assumed* completion length directly.
    output_cost: Decimal = (
        calculate_cost_by_tokens(expected_output_tokens, model, "output")
        if expected_output_tokens
        else Decimal(0)
    )
    total = prompt_cost + output_cost
    return Estimate(
        model=model,
        prompt_tokens=prompt_tokens,
        expected_output_tokens=expected_output_tokens,
        prompt_cost_usd=str(prompt_cost),
        output_cost_usd=str(output_cost),
        total_usd=str(total),
    )


def guard(est: Estimate, max_usd: float, warn_only: bool = False) -> Estimate:
    """Enforce a hard cap. Raises BudgetExceeded (or warns) when over budget."""
    cap = Decimal(str(max_usd))
    if est.total() > cap:
        msg = (
            f"Estimated ${est.total():.6f} for {est.model} exceeds cap ${cap:.6f} "
            f"({est.prompt_tokens} prompt + {est.expected_output_tokens} output tokens)"
        )
        if warn_only:
            print(f"WARNING: {msg}", file=sys.stderr)
        else:
            raise BudgetExceeded(msg)
    return est


def _read_messages(args) -> Messages:
    raw = sys.stdin.read() if args.prompt_file == "-" else open(args.prompt_file).read()
    raw = raw.strip()
    if raw.startswith("[") or raw.startswith("{"):
        try:
            return json.loads(raw)  # ChatML messages array
        except json.JSONDecodeError:
            pass
    return raw  # plain string prompt


def main() -> int:
    p = argparse.ArgumentParser(description="Pre-flight LLM cost estimate + budget cap.")
    p.add_argument("--model", required=True, help="e.g. gpt-4o, claude-sonnet-4-5")
    p.add_argument("--prompt-file", default="-", help="path to prompt (text or JSON messages); - for stdin")
    p.add_argument("--expected-output-tokens", type=int, default=0)
    p.add_argument("--max-usd", type=float, default=None, help="hard cap; non-zero exit if exceeded")
    p.add_argument("--warn-only", action="store_true", help="warn instead of failing on cap breach")
    args = p.parse_args()

    est = estimate(_read_messages(args), args.model, args.expected_output_tokens)
    print(json.dumps(asdict(est), indent=2))
    if args.max_usd is not None:
        try:
            guard(est, args.max_usd, warn_only=args.warn_only)
        except BudgetExceeded as e:
            print(f"BUDGET EXCEEDED: {e}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
