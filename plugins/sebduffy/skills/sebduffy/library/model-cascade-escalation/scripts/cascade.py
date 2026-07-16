#!/usr/bin/env python3
"""Provider-agnostic model CASCADE with escalation.

Run the cheapest tier first. A *gate* inspects its answer and decides accept
vs escalate. Only on escalate do you pay for the next (stronger, often
different-vendor) tier. This is run-then-check (FrugalGPT-style), the
complement to RouteLLM's predict-upfront routing.

Zero third-party deps. You supply each tier's `call` (any callable that maps a
messages list -> answer string; wrap your OpenAI/Anthropic/etc SDK there) and a
`gate`. Callables keep this SDK- and vendor-neutral.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Callable, Optional


Messages = list  # list[{"role","content"}]
CallFn = Callable[[Messages], str]
# gate(tier, answer, messages) -> True to ACCEPT, False to ESCALATE
GateFn = Callable[["Tier", str, Messages], bool]


@dataclass
class Tier:
    name: str
    call: CallFn
    cost: float = 1.0          # relative $ per call, cheapest first
    gate: Optional[GateFn] = None  # per-tier override; last tier's gate is ignored


@dataclass
class Result:
    answer: str
    tier: str
    escalations: int
    total_cost: float
    trace: list = field(default_factory=list)  # [{tier, accepted, cost, answer}]


def cascade(messages: Messages, tiers: list[Tier], gate: Optional[GateFn] = None) -> Result:
    """Try tiers in order; stop at the first whose gate accepts. The final tier
    is always accepted (nowhere left to escalate)."""
    if not tiers:
        raise ValueError("cascade needs at least one tier")
    total = 0.0
    trace: list = []
    for i, tier in enumerate(tiers):
        answer = tier.call(messages)
        total += tier.cost
        is_last = i == len(tiers) - 1
        g = tier.gate or gate
        accepted = True if (is_last or g is None) else bool(g(tier, answer, messages))
        trace.append({"tier": tier.name, "accepted": accepted,
                      "cost": tier.cost, "answer": answer})
        if accepted:
            return Result(answer, tier.name, i, total, trace)
    # unreachable (last tier always accepts) but keep the type checker happy
    last = trace[-1]
    return Result(last["answer"], last["tier"], len(tiers) - 1, total, trace)


# ----- ready-made gates (accept == "good enough, don't escalate") -----

def min_length(n: int) -> GateFn:
    return lambda t, a, m: len(a.strip()) >= n


def no_refusal(markers=("i can't", "i cannot", "as an ai", "i'm unable",
                        "i am unable", "i don't have")) -> GateFn:
    def g(t, a, m):
        low = a.lower()
        return not any(mk in low for mk in markers)
    return g


def must_match(pattern: str) -> GateFn:
    rx = re.compile(pattern, re.S)
    return lambda t, a, m: rx.search(a) is not None


def self_confidence(threshold: float = 0.75,
                    rx: str = r"confidence[:=]\s*([0-9]*\.?[0-9]+)") -> GateFn:
    """Accept when the model's self-reported confidence >= threshold.
    Prompt the weak tier to append e.g. 'Confidence: 0.9'. Absent/unparseable
    score -> escalate (fail safe toward quality)."""
    cx = re.compile(rx, re.I)
    def g(t, a, m):
        mt = cx.search(a)
        if not mt:
            return False
        v = float(mt.group(1))
        if v > 1.0:  # tolerate a 0-100 scale
            v /= 100.0
        return v >= threshold
    return g


def judge_gate(judge_call: CallFn, threshold: int = 7,
               rx: str = r"([0-9]{1,2})") -> GateFn:
    """LLM-as-judge on a 1-10 scale. `judge_call` is any model callable (ideally
    a cheap, *different-vendor* model so the judge isn't grading itself).
    Accept when score >= threshold; unparseable -> escalate."""
    cx = re.compile(rx)
    def g(t, a, m):
        user = next((x["content"] for x in reversed(m) if x["role"] == "user"), "")
        prompt = [{"role": "user", "content":
                   "Rate how well this answer resolves the question, 1-10. "
                   "Reply with ONLY the number.\n\n"
                   f"Question:\n{user}\n\nAnswer:\n{a}"}]
        mt = cx.search(judge_call(prompt))
        return bool(mt) and int(mt.group(1)) >= threshold
    return g


def all_of(*gates: GateFn) -> GateFn:
    return lambda t, a, m: all(g(t, a, m) for g in gates)


if __name__ == "__main__":
    # Self-test with mock models — no network.
    def weak(msgs):   # refuses hard questions, low confidence
        q = msgs[-1]["content"]
        if "integral" in q:
            return "I can't. Confidence: 0.2"
        return "Paris. Confidence: 0.95"

    def strong(msgs):
        return "The integral evaluates to x^2/2 + C. Confidence: 0.98"

    tiers = [Tier("haiku", weak, cost=1.0), Tier("opus", strong, cost=15.0)]
    gate = all_of(no_refusal(), self_confidence(0.75))

    easy = cascade([{"role": "user", "content": "Capital of France?"}], tiers, gate)
    hard = cascade([{"role": "user", "content": "Compute the integral of x."}], tiers, gate)

    assert easy.tier == "haiku" and easy.escalations == 0 and easy.total_cost == 1.0, easy
    assert hard.tier == "opus" and hard.escalations == 1 and hard.total_cost == 16.0, hard
    saved = (2 * 16.0 - (easy.total_cost + hard.total_cost)) / (2 * 16.0)
    print(f"OK  easy->{easy.tier} (${easy.total_cost})  "
          f"hard->{hard.tier} (${hard.total_cost})  "
          f"vs always-strong: {saved:.0%} cheaper")
