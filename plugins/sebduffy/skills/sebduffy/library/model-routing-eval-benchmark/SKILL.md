---
name: model-routing-eval-benchmark
category: model-routing
description: >
  Benchmark models ACROSS vendors on YOUR OWN data to prove which model to route
  each task type to — then turn the results into a routing table (and optionally
  train a custom cross-vendor router with RoRF or Not-Diamond). Uses promptfoo to
  run every prompt x every provider (Claude, GPT, Gemini, DeepSeek, Llama...) with
  per-call pass/cost/latency, so routing decisions are measured, not vibes. Use
  when someone says "which model is actually best for X", "benchmark GPT vs Claude
  on my prompts", "should I route this to Haiku or GPT-mini", "prove the router
  config wins", "eval models on my dataset", "A/B the vendors", "build me a router
  from real data", or "RoRF / Not-Diamond custom router".
when_to_use:
  - "You need to decide which vendor/model handles each task type, backed by data on your prompts"
  - "You want a side-by-side leaderboard of models on a dataset with cost + latency, not a public benchmark"
  - "You already have a router (triage/cascade/gateway) and want to prove a config change actually wins before shipping"
  - "You want to train a custom cross-vendor router (RoRF random forest, or Not-Diamond) from measured wins"
  - "You suspect a cheaper model is good enough for most of your traffic and want to quantify it"
  - "You need a repeatable eval you can re-run in CI whenever a new model drops"
when_not_to_use:
  - "You just want to route cheap-first inside one vendor's tiers at runtime -> model-triage-router"
  - "You need one endpoint that dispatches to many vendor APIs live -> cross-provider-gateway"
  - "You want blind try-cheap-then-escalate with no dataset -> model-cascade-escalation"
  - "You want a model to grade another model's single output -> cross-vendor-llm-judge"
  - "You only need a spend forecast, not a bake-off -> llm-cost-estimator"
keywords: [promptfoo, model benchmark, eval, bake-off, rorf, not-diamond, notdiamond, cross-vendor routing, leaderboard, gpt vs claude, llm-rubric, pass rate, cost latency, custom router, random forest router, willingness to pay, threshold, ab test models, dataset eval, which model best]
similar_to: [model-triage-router, cross-provider-gateway, model-cascade-escalation, mixture-of-models-ensemble, cross-vendor-llm-judge, best-model-per-step-pipeline, llm-cost-estimator]
inputs_needed:
  - "A dataset of ~30-500 real prompts, ideally tagged with a task `type` (e.g. classify/extract/reason/write)"
  - "The candidate models to compare (default: claude-haiku-4-5, gpt-5-mini, gemini-2.0-flash, opus-4-6)"
  - "A grader: an llm-rubric string, expected outputs, or a code assertion per task type"
  - "API keys for every vendor under test (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.)"
  - "A tolerance: how much pass-rate you'll trade for a cheaper model (default 3%)"
produces: A per-task-type routing table (which vendor wins each bucket, cost-adjusted) from a promptfoo eval, plus an optional trained RoRF/Not-Diamond router.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Model Routing Eval & Benchmark

Public leaderboards do not tell you which model to route YOUR tasks to. This skill
runs a real bake-off — every prompt against every candidate model, graded, with
cost and latency captured — then collapses the results into a routing decision per
task type. The output is evidence you can hand to `model-triage-router` /
`cross-provider-gateway`, or the training data for a learned router.

Pipeline: **(1) build an eval → (2) run it with promptfoo → (3) derive a routing
table → (4) optionally train a custom router (RoRF / Not-Diamond).** Steps 1–3 are
enough for most people; step 4 is for high-volume, per-prompt routing.

## When to use

- You keep guessing which vendor to send a task type to. Measure it once.
- You want cost + quality + latency for each model on your data, side by side.
- You need a gate: "does this router config beat the current one on my set?"

## Prerequisites

- **Node 18+** for promptfoo (`npx promptfoo@latest` — no install needed).
- **API keys** exported for every vendor you list as a provider:
  `export ANTHROPIC_API_KEY=... OPENAI_API_KEY=... GEMINI_API_KEY=...`
- **Python 3.9+** only for the routing-table helper and (step 4) RoRF: `pip install rorf`.
- A dataset. CSV, Google Sheet, or HuggingFace dataset all load directly.

## Recipe 1 — Bake-off with promptfoo (the core)

Scaffold and edit one config file. Every prompt runs against every provider.

```bash
npx promptfoo@latest init --no-interactive   # writes promptfooconfig.yaml
```

`promptfooconfig.yaml` — compare four vendors, grade with an LLM rubric, capture
cost/latency, and load rows (with a `type` column) from a CSV:

```yaml
description: cross-vendor routing bake-off

providers:
  - anthropic:messages:claude-haiku-4-5
  - anthropic:messages:claude-opus-4-6
  - openai:gpt-5-mini
  - google:gemini-2.0-flash

prompts:
  - "{{prompt}}"          # one column of the dataset is the actual prompt

# Grade + cost/latency gates apply to EVERY row/model unless a row overrides.
defaultTest:
  assert:
    - type: llm-rubric
      value: "Answer is correct and fully addresses the request"
    - type: cost
      threshold: 0.02        # fail a row if a model costs > $0.02
    - type: latency
      threshold: 4000        # ms

# Rows: each has vars.prompt, an optional vars.type bucket, and (optional) expected.
tests: file://dataset.csv
```

`dataset.csv` (the `__expected` column is promptfoo's built-in per-row assertion;
`type` is your routing bucket):

```csv
prompt,type,__expected
"Classify sentiment: 'shipping was slow'",classify,contains: negative
"Extract the invoice total from: ...",extract,llm-rubric: returns only the number
"Why does CAP theorem forbid CA under partition?",reason,llm-rubric: mentions partition tolerance tradeoff
```

Run it, watch the matrix, export JSON:

```bash
npx promptfoo@latest eval -c promptfooconfig.yaml -o results.json
npx promptfoo@latest view          # web UI: prompt x provider x test grid
```

promptfoo reports pass rate, **token cost, and latency per provider** natively and
runs providers in parallel. Use `defaultTest` to avoid repeating assertions, and
`derivedMetrics` if you want a custom score (e.g. quality-per-dollar).

## Recipe 2 — Collapse results into a routing table

The bundled helper buckets rows by `type` and, per bucket, picks the **cheapest
model within `--tolerance` pass-rate of the best** — that is your routing rule.

```bash
python3 scripts/route_from_eval.py results.json --tolerance 0.03
# classify -> route to anthropic:messages:claude-haiku-4-5  (pass 98%, $0.0002)
# reason   -> route to anthropic:messages:claude-opus-4-6   (pass 95%, $0.02)
python3 scripts/route_from_eval.py results.json --json > routing_table.json
```

Hand `routing_table.json` to `model-triage-router` or `cross-provider-gateway` as
the static routing map. Re-run the whole thing in CI whenever a new model ships —
the config is the source of truth.

## Recipe 3 — Train a custom cross-vendor router (RoRF)

For per-prompt (not per-bucket) routing between exactly **two** models, RoRF trains
a random-forest over prompt embeddings. Use a pretrained pair, or train your own on
the win/loss labels the bake-off produced.

```python
from rorf.controller import Controller

router = Controller(
    router="notdiamond/rorf-jina-llama31405b-llama3170b",  # 12 pretrained pairs exist
    model_a="llama-3.1-405b-instruct",
    model_b="llama-3.1-70b-instruct",
    threshold=0.3,   # ~30% of calls go to model_b; raise to push more to the cheap model
)
recommended = router.route("What is the meaning of life?")  # -> a model-name string
```

`threshold` is your willingness-to-pay dial: sweep it against your held-out set to
hit a target cost. For >2 models or a hosted option, **Not-Diamond**'s API routes
across many providers from the same pairwise-preference idea. Pretrained pairs ship
with the free `jina-embeddings-v3` or `voyage-large-2-instruct` (needs a key).

## Verify

- `results.json` has one row per (prompt x provider); `npx promptfoo view` shows a
  full grid with no all-error columns (all-error = missing/invalid API key).
- The routing table names a real provider for each `type` and the winner's cost is
  <= the best model's cost. Spot-check 3 rows in the web UI against the verdict.
- Sanity gate: the chosen cheap model's pass rate on its bucket is within tolerance
  of the frontier model on the SAME bucket — never compare across buckets.
- RoRF: `router.route()` returns one of your two model names; sweeping `threshold`
  0→1 monotonically shifts the split toward `model_a`.

## Pitfalls

- **A weak grader invalidates everything.** `llm-rubric` with a vague value routes
  by luck. Write a specific rubric per task type, or use exact `__expected` matches
  where you can. Consider a stronger judge model than the ones under test.
- **Too few rows.** <30 per bucket and pass-rate differences are noise. Get 50+ per
  task type before trusting a routing flip.
- **Ignoring latency/cost.** A 1% quality win at 10x cost is usually a loss — that's
  why the helper picks cheapest-within-tolerance, not the raw max.
- **Grader on the payroll.** Don't let a model grade its own outputs; it self-favours.
- **Stale results.** Models change under the same name. Re-run before you trust an
  old leaderboard; wire `promptfoo eval` into CI.
- **RoRF is 2-model only.** For 3+ vendors use per-bucket routing (Recipe 2) or
  Not-Diamond, not one RoRF router.
- **Cost data needs token accounting.** promptfoo computes cost from provider
  pricing; a custom/self-hosted provider may report `$0` — set pricing in the
  provider `config` or the cheapest-wins logic will always pick it.
