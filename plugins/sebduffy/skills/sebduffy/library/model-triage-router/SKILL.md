---
name: model-triage-router
category: model-routing
description: >
  Route each request cheap-first inside ONE vendor's tier ladder (Anthropic
  Haiku -> Sonnet -> Opus, or OpenAI mini -> full) using a difficulty score
  plus confidence-gated cascade escalation, cutting spend 40-85% with no quality
  loss. Score prompt hardness up front, send the easy long tail to the cheap
  model, and only climb tiers when the cheap answer's self-rated confidence is
  low. Use when someone says "route to the cheapest model that can handle it",
  "auto-pick Haiku vs Sonnet vs Opus", "escalate to a bigger model only if
  needed", "cut my LLM bill without hurting quality", "difficulty-based
  routing", "cascade / fallback to a stronger model", or "RouteLLM for Claude".
when_to_use:
  - "You want each request served by the cheapest tier that can still get it right"
  - "Most traffic is easy but a hard minority needs the frontier model"
  - "Your bill is dominated by sending everything to Opus/GPT-full by default"
  - "You want a calibrated threshold that targets 'X% of traffic to the strong model'"
  - "You want automatic escalation when the small model is unsure, not a fixed rule"
  - "You're porting lm-sys/RouteLLM's strong/weak routing to Anthropic's 3 tiers"
when_not_to_use:
  - "Routing across DIFFERENT vendors/APIs behind one endpoint -> cross-provider-gateway"
  - "You only need blind try-cheap-then-retry-bigger with no scorer -> model-cascade-escalation"
  - "You want to fan out to several models and merge/vote -> mixture-of-models-ensemble"
  - "You need a model to grade another model's output -> cross-vendor-llm-judge"
  - "The goal is uptime/failover when a provider is down -> provider-failover-reliability"
  - "You want to measure which router config actually wins on a dataset -> model-routing-eval-benchmark"
keywords: [model routing, routellm, cheap first, difficulty routing, cascade, escalation, haiku sonnet opus, tier ladder, confidence gate, win rate, threshold calibration, cost saving, strong weak model, router-mf, adaptive routing, llm cost cut, prompt hardness, fallback model]
similar_to: [cross-provider-gateway, model-cascade-escalation, mixture-of-models-ensemble, cross-vendor-llm-judge, provider-failover-reliability, best-model-per-step-pipeline, model-routing-eval-benchmark, llm-cost-estimator]
inputs_needed:
  - "The vendor + tier ladder to route across (default: Anthropic haiku-4-5 / sonnet-4-6 / opus-4-6)"
  - "Target: a fixed strong-model % (calibrated router) OR a confidence floor (cascade)"
  - "A sample of ~50-500 real prompts if you want a calibrated threshold rather than a heuristic"
  - "API key for the vendor (ANTHROPIC_API_KEY or OPENAI_API_KEY)"
produces: A drop-in router that picks the cheapest capable tier per request (calibrated RouteLLM threshold and/or confidence-gated cascade), plus a cost/quality trace per call.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Model Triage Router

Serve each request on the cheapest tier that can get it right, and only climb to
a stronger (pricier) model when the cheap one is genuinely out of its depth. Two
complementary strategies — use one or stack them:

- **A. Calibrated pre-routing (RouteLLM).** Score prompt difficulty *before*
  calling any model; pick strong vs weak from a threshold you calibrate to hit a
  target strong-model %. One call per request, deterministic cost.
- **B. Confidence-gated cascade.** Call the cheapest tier, have it self-rate
  confidence, escalate only on low confidence. Catches the cases a static score
  misses. Costs 1-N calls; N only on the hard tail.

Both are "cheap-first within one vendor" — not cross-vendor gateways.

## When to use

- Traffic is mostly easy with a hard minority (the classic 80/20 that makes
  cheap-first pay off).
- You default everything to Opus / GPT-full and the bill hurts.
- You want a knob ("send ~30% to the strong model") or a safety net ("escalate
  if unsure"), not a hand-written if/else per prompt type.

## Prerequisites

Pick your approach:

**B (cascade) — zero extra infra**, just the vendor SDK:

```bash
pip install anthropic          # or: pip install openai
export ANTHROPIC_API_KEY=sk-ant-...
```

**A (calibrated RouteLLM) — a trained router + a calibration set:**

```bash
pip install "routellm[serve,eval]"
```

RouteLLM ships pretrained routers (`mf` matrix-factorization is the recommended
default; also `bert`, `causal_llm`, `sw_ranking`, `random`). It routes between
exactly **two** models — a `strong_model` and a `weak_model` — using an
OpenAI-compatible client, so it drops onto Anthropic via LiteLLM model strings.
For a 3-tier ladder, chain two RouteLLM stages (weak/mid, then mid/strong) or
use the difficulty score as a feature and route yourself.

Honest caveats: RouteLLM's routers were trained on general chat preference data
(Chatbot Arena). On a narrow domain, **recalibrate on your own prompts** or the
threshold's target % will drift. The `mf` model download is a few hundred MB.

## Recipes

### 1. Cheapest infra: confidence-gated cascade (approach B)

`scripts/cascade_route.py` tries Haiku, asks it for a calibrated `CONFIDENCE:
0-1`, and escalates to Sonnet then Opus only when confidence is below a floor.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/cascade_route.py --floor 0.75 "What is the capital of France?"
# -> served by claude-haiku-4-5, escalations: 0

python3 scripts/cascade_route.py --floor 0.75 \
  "Prove that the sum of two independent Poisson variables is Poisson."
# -> likely climbs to sonnet/opus, escalations: 1-2
```

Override the ladder without touching code:

```bash
CASCADE_TIERS="claude-haiku-4-5,claude-opus-4-6" \
  python3 scripts/cascade_route.py "…"     # skip the middle tier
```

Output is JSON: chosen `model`, `confidence`, `escalations`, and a per-tier
`trace` so you can audit where spend went.

**Tuning the floor** is the whole game: higher floor = more escalations = more
quality + more cost. Start at 0.7, watch the escalation rate and your quality
metric, adjust. A floor that escalates ~15-25% of traffic is a common sweet spot.

### 2. Calibrated pre-routing with RouteLLM (approach A)

Calibrate a threshold so a target fraction of traffic hits the strong model.
This is the RouteLLM `mf` router; the printed threshold goes straight into the
model string:

```bash
# Target: ~50% of queries routed to the strong model.
python -m routellm.calibrate_threshold \
  --routers mf --strong-model-pct 0.5 --config config.example.yaml
# prints e.g.  For 50.0% strong model calls, threshold = 0.11593
```

Use it from Python. Point `strong_model` / `weak_model` at Anthropic tiers via
LiteLLM-style names (`anthropic/<model-id>`):

```python
from routellm.controller import Controller

client = Controller(
    routers=["mf"],
    strong_model="anthropic/claude-opus-4-6",
    weak_model="anthropic/claude-haiku-4-5",
)

resp = client.chat.completions.create(
    # router-<name>-<threshold> from the calibrate step above
    model="router-mf-0.11593",
    messages=[{"role": "user", "content": "Summarise this refund policy…"}],
)
```

Below-threshold win-rate for the strong model -> weak model answers; above -> strong.
Raise the threshold to push MORE traffic to the cheap model (bigger savings,
lower ceiling); lower it to protect quality.

Or run it as an OpenAI-compatible server and point any existing client at it:

```bash
python -m routellm.openai_server \
  --routers mf \
  --strong-model anthropic/claude-opus-4-6 \
  --weak-model anthropic/claude-haiku-4-5
# then call http://localhost:6060/v1 with model="router-mf-0.11593"
```

### 3. Stack A then B (recommended for production)

Pre-route with the calibrated score to pick the *starting* tier, then let the
cascade escalate from there. The score handles the obvious cases in one call;
the confidence gate catches the score's mistakes. Keep the trace from both so
you can attribute every dollar.

### 4. No-dependency heuristic scorer (when you can't add RouteLLM)

When a full router is overkill, a transparent difficulty score routes the
starting tier. Treat these as *inputs to a threshold you calibrate on your data*
— they are a starting point, not physics:

- length / token count of the prompt + attachments,
- presence of code, math, multi-step or "prove/derive/plan" verbs,
- tool-use or long-context requirement,
- explicit user stakes ("draft" vs "final client-facing").

Map a weighted score to a starting tier, then wrap with recipe 1's cascade so a
mis-scored hard prompt still escalates. Keep it immutable: score -> tier is a
pure function, no hidden state.

## Verify

- **Savings are real:** log tier per request and compute blended cost vs
  all-Opus baseline. Target 40-85% reduction; if you're not near that, your
  threshold/floor is too conservative or your traffic isn't actually easy.
- **Quality held:** on a labelled eval set, quality of the routed system should
  match top-tier within noise. If not, lower the RouteLLM threshold / raise the
  cascade floor. Use `model-routing-eval-benchmark` to measure this properly.
- **Escalation rate sanity:** cascade escalations should track prompt hardness,
  not fire on everything (floor too high) or never (floor too low / model
  overconfident).

```bash
# Quick smoke: an easy prompt should NOT escalate.
python3 scripts/cascade_route.py --floor 0.7 "2+2?" | grep '"escalations": 0'
```

## Pitfalls

- **Routing is not free.** Approach A adds one scorer pass (cheap for `mf`, a
  real model call for `causal_llm`); approach B pays for every failed cheap
  attempt before it escalates. If a domain is uniformly hard, cheap-first *loses*
  — measure before shipping.
- **Overconfident small models.** Haiku will happily claim high confidence on a
  wrong answer. Confidence self-rating is a weak signal; back it with a real
  check (a judge model, unit tests, schema validation) for high-stakes flows —
  see `cross-vendor-llm-judge`.
- **Calibration drift.** RouteLLM thresholds are calibrated on a sample; if your
  traffic mix shifts, the target % drifts. Recalibrate on fresh prompts
  periodically.
- **Wrong tool for cross-vendor.** This skill routes tiers within one vendor. To
  route across OpenAI/Anthropic/Google behind one endpoint use
  `cross-provider-gateway`; for uptime failover use `provider-failover-reliability`.
- **Model IDs go stale.** The tier IDs here (`claude-haiku-4-5`,
  `claude-sonnet-4-6`, `claude-opus-4-6`) are current as of 2026-07; confirm the
  latest IDs in the vendor docs and update `CASCADE_TIERS` / the Controller args.
- **Don't cache confidence across prompts.** Each request re-scores; a stale
  routing decision reused on a different prompt is a silent quality bug.
