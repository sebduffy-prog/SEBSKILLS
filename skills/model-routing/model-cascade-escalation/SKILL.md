---
name: model-cascade-escalation
category: model-routing
description: >
  Run a cheap/small model first and escalate to a stronger (often different-vendor) model ONLY when
  a gate — self-reported confidence, an LLM judge, a verifier, a schema/regex check, or a refusal
  detector — says the cheap answer isn't good enough. FrugalGPT-style run-then-check cascade that
  cuts LLM spend 50-85% without dropping quality. Use when you say "try the cheap model first",
  "escalate to GPT-4/Opus only if needed", "fall back to a bigger model", "confidence-based routing",
  "cascade of models", "RouteLLM", "don't pay for the big model every call", or "verify then upgrade".
when_to_use:
  - "Most of your traffic is easy and a small model handles it, but a minority needs a frontier model"
  - "You want to pay frontier prices only on the queries that actually need it, decided per-response"
  - "You can cheaply check an answer (judge, verifier, unit test, schema, self-confidence) before trusting it"
  - "You want a cheap model to attempt first and a different-vendor stronger model as the escalation tier"
  - "You need a deterministic, auditable trace of which tier answered and why it escalated"
  - "You're chasing the RouteLLM-style ~85% MT-Bench cost cut but want run-then-check, not upfront prediction"
when_not_to_use:
  - "You want to pick the model BEFORE running (predict difficulty upfront) — use model-triage-router"
  - "You just need one API endpoint that fans out to many providers — use cross-provider-gateway"
  - "You want several models to answer and merge/vote every time — use mixture-of-models-ensemble"
  - "The only job is scoring one answer with a second-vendor model — use cross-vendor-llm-judge"
  - "You need automatic retry on a provider outage/timeout, not quality escalation — use provider-failover-reliability"
  - "Each pipeline STEP needs its own fixed best model — use best-model-per-step-pipeline"
keywords: [model cascade, escalation, routellm, frugalgpt, confidence routing, llm judge, fallback model, cheap model first, escalate to gpt-4, tiered models, run then check, verifier gate, self-consistency, cost reduction, weak strong model, cascade routing, model tiers, quality gate, routllm]
similar_to: [model-triage-router, cross-provider-gateway, mixture-of-models-ensemble, cross-vendor-llm-judge, provider-failover-reliability, best-model-per-step-pipeline, model-routing-eval-benchmark, llm-cost-estimator]
inputs_needed:
  - "Your ordered tiers cheapest->strongest, each with a callable that maps messages -> answer text"
  - "A gate signal you can compute cheaply: self-confidence, judge score, verifier/test, schema/regex, or refusal check"
  - "The accept threshold (e.g. judge >= 7/10, confidence >= 0.75) and how failures should fail (safe = escalate)"
  - "Optional: per-tier relative $ cost so the trace reports realised savings"
produces: A provider-agnostic cascade runner (scripts/cascade.py) that returns the accepted answer, the tier that gave it, an escalation trace, and realised cost — plus ready-made confidence/judge/verifier/refusal gates
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Model Cascade & Escalation

Paying frontier prices on every request is how you burn budget on questions a small model already
nails. Instead, run the **cheap tier first**, then let a **gate** decide accept-vs-escalate. You only
pay for the stronger (often different-vendor) tier on the fraction of queries that fail the gate.
This is the **FrugalGPT** run-then-check cascade — the complement to **RouteLLM's** predict-upfront
routing. On MT-Bench, RouteLLM-style routing hit **95% of GPT-4 quality at ~85% lower cost** by
sending only ~14% of queries to the strong model; a cascade gets similar wins whenever your gate is
a good proxy for quality.

## When to use

Reach for a cascade when traffic is **mostly easy with a hard minority**, and you can **cheaply check
an answer** before trusting it (a judge, a verifier, a unit test, a JSON-schema parse, or a
self-reported confidence). If instead you want to decide the model **before** spending any tokens —
predicting difficulty from the prompt alone — that's upfront routing (`model-triage-router` or the
RouteLLM library). Cascade trades a little extra latency/cost on hard queries (you ran the cheap tier
too) for not needing a trained difficulty predictor.

## Cascade vs upfront routing (pick deliberately)

| | Cascade (this skill) | Upfront routing (RouteLLM / model-triage-router) |
|---|---|---|
| Decides | *after* seeing the cheap answer | *before* any call, from the prompt |
| Needs | a cheap quality gate | a trained/heuristic difficulty predictor |
| Wasted spend | cheap call on hard queries | strong call on misrouted easy queries |
| Best when | answers are cheap to check | prompts are cheap to classify |

They compose: route upfront to skip the cheap tier on obviously-hard prompts, then cascade the rest.

## The gate is everything

The cascade is only as good as the signal that decides "good enough". Pick the cheapest signal that
correlates with quality for your task:

- **Verifier / deterministic check (best when available):** code compiles & tests pass, JSON parses
  against a schema, math answer re-derives, tool call is well-formed. Near-zero cost, near-perfect
  precision. Escalate on failure.
- **LLM-as-judge:** a *cheap, different-vendor* model scores the answer 1-10 (don't let a model grade
  its own family). See `cross-vendor-llm-judge`.
- **Self-reported confidence:** ask the weak tier to append `Confidence: 0.0-1.0`. Cheap but models
  are often over-confident — calibrate the threshold on real data, don't trust 0.9 blindly.
- **Self-consistency:** sample the weak tier N times; escalate if answers disagree (variance = "this
  is hard"). Costs N cheap calls but no judge.
- **Refusal / hedge detection:** escalate when the cheap answer says "I can't", "as an AI", is empty,
  or is suspiciously short. Cheap backstop, pair it with a stronger signal.

**Fail safe = escalate.** If the gate errors or can't parse a score, send it up a tier — spend a
little more rather than ship a bad answer.

## Prerequisites

- **Python 3.9+** for `scripts/cascade.py`. **Zero third-party deps** — you wrap your own SDK.
- **Two+ model tiers** with credentials, cheapest first. Good pairings put a *different vendor* on the
  strong tier so a whole-provider weakness or outage doesn't sink both:
  - Anthropic Haiku -> Anthropic Opus, or Haiku -> OpenAI GPT-4-class
  - `gpt-4o-mini` -> `gpt-4o`/`o3`, or a local/Groq Llama -> a frontier API
- **A gate signal** you can compute cheaply (see above). A judge gate needs one more cheap model call.
- The RouteLLM library (`pip install "routellm[serve,eval]"`) is the right tool if you want
  *upfront* routing with a trained `mf`/`bert`/`causal_llm` router instead of a cascade — see the
  last recipe.

## Recipe 1 — wrap your SDKs as tiers

A tier is just `name + call(messages)->str + cost`. Wrap any provider:

```python
from anthropic import Anthropic
from openai import OpenAI
from scripts.cascade import Tier, cascade, all_of, no_refusal, self_confidence

anthropic, openai = Anthropic(), OpenAI()

def haiku(msgs):   # cheap tier — ask it to self-rate
    r = anthropic.messages.create(model="claude-haiku-4-5", max_tokens=1024,
        system="Answer, then on a new line write 'Confidence: X' (0.0-1.0).",
        messages=msgs)
    return r.content[0].text

def opus(msgs):    # strong escalation tier
    r = anthropic.messages.create(model="claude-opus-4-6", max_tokens=2048, messages=msgs)
    return r.content[0].text

tiers = [Tier("haiku", haiku, cost=1.0), Tier("opus", opus, cost=15.0)]
gate  = all_of(no_refusal(), self_confidence(threshold=0.75))

res = cascade([{"role": "user", "content": "…"}], tiers, gate)
print(res.tier, res.total_cost)      # which model answered + relative $
print(res.answer)
for step in res.trace:               # audit: each attempt + accept/escalate
    print(step["tier"], "accepted" if step["accepted"] else "ESCALATED")
```

`cascade()` runs tiers in order and stops at the first the gate accepts; the **last tier is always
accepted** (nowhere left to go). It returns the answer, the winning tier, the escalation count, the
realised cost, and a full trace.

## Recipe 2 — judge gate with a different-vendor grader

Grade the cheap answer with a cheap model from *another* vendor, escalate below the bar:

```python
from scripts.cascade import Tier, cascade, judge_gate

def gpt_mini_judge(msgs):            # cheap, different family than the tiers
    r = openai.chat.completions.create(model="gpt-4o-mini", messages=msgs)
    return r.choices[0].message.content

gate = judge_gate(gpt_mini_judge, threshold=7)   # accept if score >= 7/10
res  = cascade(messages, tiers, gate)
```

## Recipe 3 — verifier gate (the strongest signal)

When you can *check* the answer deterministically, do that instead of judging it. Escalate only when
the check fails:

```python
import json, jsonschema
from scripts.cascade import must_match  # or write your own gate

SCHEMA = {...}
def schema_ok(tier, answer, msgs):
    try:
        jsonschema.validate(json.loads(answer), SCHEMA)
        return True                    # valid -> accept cheap answer
    except Exception:
        return False                   # invalid -> escalate

res = cascade(messages, tiers, schema_ok)
```

For code, run the tests; for extraction, check required fields are present; for tool calls, validate
the arguments. A passing verifier is far more trustworthy than any judge score.

## Recipe 4 — self-consistency gate (no judge, no self-rating)

Sample the weak tier a few times; escalate when it can't agree with itself:

```python
from collections import Counter
def consistent(tier, answer, msgs, n=3):
    votes = Counter(tier.call(msgs).strip() for _ in range(n - 1))
    votes[answer.strip()] += 1
    top, count = votes.most_common(1)[0]
    return count >= (n // 2 + 1)       # majority agrees -> accept
```

Use for tasks with a canonical short answer (classification, extraction, arithmetic). Costs N cheap
calls; still far cheaper than a frontier call if the small model is, say, 15x cheaper.

## Recipe 5 — three-tier ladder

Tiers can be any depth; the gate is evaluated after every non-final tier:

```python
tiers = [Tier("mini", mini, 1.0), Tier("mid", mid, 5.0), Tier("frontier", frontier, 20.0)]
res = cascade(messages, tiers, gate)   # mini -> mid -> frontier, stops when gate accepts
```

Per-tier overrides let a stricter gate guard the jump to the most expensive tier:
`Tier("frontier", frontier, 20.0, gate=all_of(no_refusal(), judge_gate(judge, threshold=8)))`.

## Recipe 6 — upfront routing instead (RouteLLM)

If prompts are cheaper to classify than answers are to check, skip the cascade and route upfront with
RouteLLM's trained router:

```bash
pip install "routellm[serve,eval]"
```
```python
from routellm.controller import Controller
client = Controller(routers=["mf"],                       # matrix-factorization router
    strong_model="gpt-4-1106-preview",
    weak_model="anyscale/mistralai/Mixtral-8x7B-Instruct-v0.1")
# threshold 0.11593 ~ calibrated so a target % goes to the strong model
resp = client.chat.completions.create(model="router-mf-0.11593",
    messages=[{"role": "user", "content": "Hello!"}])
```
Calibrate the threshold to your desired strong-model share:
```bash
python -m routellm.calibrate_threshold --routers mf --strong-model-pct 0.5 --config config.example.yaml
```
Or run it as an OpenAI-compatible drop-in server (`python -m routellm.openai_server --routers mf …`,
listens on `:6060`). RouteLLM decides *before* calling; this skill decides *after*. Measure both on
your traffic with `model-routing-eval-benchmark`.

## Verify

```bash
# Runs the built-in mock-model self-test: easy query stays on the cheap tier,
# hard query escalates, and it prints realised savings vs always-strong.
python3 scripts/cascade.py
# expect: OK  easy->haiku ($1.0)  hard->opus ($16.0)  vs always-strong: 47% cheaper
```

Then, on **your** traffic, log `res.tier` and `res.total_cost` per request and track two numbers:
**escalation rate** (what % hit the strong tier) and **quality on a held-out set** vs always-strong.
If escalation is ~100%, your gate is too strict (or the task is genuinely hard) and you're paying
*more* than always-strong; if quality dropped, the gate is too lax. Tune the threshold against a
labelled eval, not vibes.

## Pitfalls

- **A lax gate ships cheap-but-wrong answers.** The cascade can only be as good as its check. Prefer
  a verifier > judge > self-consistency > self-confidence, in that order of trust.
- **Over-confident self-scores.** Models say "0.95" on answers they got wrong. Calibrate the
  threshold on real labelled data; never trust raw self-confidence as the *only* gate.
- **Escalation rate too high = negative savings.** If most queries escalate you pay the cheap call
  *plus* the strong call. Measure the rate; if it's high, switch to upfront routing or a bigger weak
  model. Break-even ≈ escalation_rate < 1 − (weak_cost / strong_cost).
- **Judge grading its own family.** A model tends to like answers from its own vendor. Use a
  *different-vendor* cheap judge (`cross-vendor-llm-judge`).
- **Same-vendor tiers share failure modes.** If Haiku can't do it, Opus sometimes can't either, and a
  vendor outage takes both down. A cross-vendor strong tier hedges capability *and* availability.
- **Latency, not just cost.** Escalated queries pay two round-trips; if p99 matters, cap depth or
  route obviously-hard prompts straight to strong. **Fail-open gates** (returning True on their own
  exception) silently disable escalation — fail *safe*. And **log the `trace`**: without it you can't
  debug a cost spike or quality regression.

## Credits

Cascade / run-then-check pattern follows **FrugalGPT** (Chen, Zaharia, Zou, 2023). Upfront-routing
recipe and the ~85% MT-Bench cost figure are from **lm-sys/RouteLLM** (Apache-2.0, ICLR 2025,
<https://github.com/lm-sys/RouteLLM>). `scripts/cascade.py` is original, dependency-free code.
