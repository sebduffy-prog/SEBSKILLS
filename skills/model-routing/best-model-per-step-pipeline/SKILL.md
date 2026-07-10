---
name: best-model-per-step-pipeline
category: model-routing
description: >
  Assign each STEP of a multi-step task to the model+vendor best at that step
  (deep reasoning on one, coding on another, vision on another, cheap-bulk on a
  fourth) and hand typed, schema-validated state between steps. A fixed pipeline
  where step->model is a config map you can re-route without touching logic — not
  cheapest-tier routing of one request. Use when someone says "use the best model
  for each stage", "reasoning model plans then a coding model implements", "route
  each step to a different LLM", "different model per pipeline stage", "GPT for
  code, Claude for reasoning, Gemini for vision", "typed handoff between model
  steps", or "orchestrate a chain across multiple providers".
when_to_use:
  - "A task splits into stages (plan, implement, review, summarize) each with a different sweet-spot model"
  - "You want a reasoning model to plan, a coding model to build, and a cheap model to do bulk formatting"
  - "A step needs vision/audio a text model can't do, so it must go to a specific multimodal model"
  - "You want the step->model mapping in config so you can re-route a stage without rewriting it"
  - "State passed between steps must be typed and validated so a bad handoff fails loudly, not silently"
  - "You're chaining OpenAI + Anthropic + Gemini into one deterministic workflow"
when_not_to_use:
  - "Routing ONE request to the cheapest capable tier of one vendor -> model-triage-router"
  - "One request, retry a bigger model only if the cheap one fails -> model-cascade-escalation"
  - "Fan the SAME task to several models and vote/merge the answers -> mixture-of-models-ensemble"
  - "Just a unified transport/endpoint over many providers (no per-step logic) -> cross-provider-gateway"
  - "One model grading another's output -> cross-vendor-llm-judge"
  - "Uptime failover when a provider is down -> provider-failover-reliability"
keywords: [per-step routing, best model per step, multi-model pipeline, model orchestration, typed handoff, structured output, reasoning model, coding model, vision model, litellm, vercel ai sdk, pydantic, zod, generateObject, multi-provider chain, stage routing, cross-vendor pipeline, model per stage]
similar_to: [model-triage-router, cross-provider-gateway, model-cascade-escalation, mixture-of-models-ensemble, cross-vendor-llm-judge, provider-failover-reliability]
inputs_needed:
  - "The stages of your task and the model you want for each (default map: opus=plan, gpt=code, sonnet=review, haiku=summarize)"
  - "The typed schema of the state each step passes to the next (Pydantic or Zod)"
  - "API keys for every vendor a step uses (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY)"
  - "Language: Python (litellm) or TypeScript (Vercel AI SDK)"
produces: A step->model routed pipeline where each stage runs on its best model and hands schema-validated typed state to the next, with a per-step routing/timing trace.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Best Model Per Step Pipeline

Different steps of a task have different sweet-spot models. A reasoning model
plans best; a coding model implements best; a multimodal model reads the
screenshot; a cheap model does the bulk formatting. This skill wires them into
**one fixed pipeline** where:

1. **step -> model** is a config map (route a stage elsewhere by editing one line), and
2. the state passed **between** steps is a **typed schema**, validated at the seam
   so a malformed handoff fails loudly instead of poisoning the next step.

This is orchestration, not triage. It always runs the same stages; it does not
pick "the cheapest tier that can handle this request" (that's
`model-triage-router`) nor vote across models on one task
(`mixture-of-models-ensemble`).

## When to use

- Your task is naturally staged and the stages differ in what they need
  (reasoning depth vs code quality vs vision vs raw cheap throughput).
- You want to change which model owns a stage from config, and have a typed
  contract catch the moment one stage returns something the next can't use.

## Prerequisites

**Python** — one vendor-agnostic call path via litellm:

```bash
pip install "litellm>=1.0" pydantic
export ANTHROPIC_API_KEY=sk-ant-...      # + OPENAI_API_KEY / GEMINI_API_KEY per step
```

litellm routes by model-string prefix: `anthropic/claude-...`, `openai/gpt-...`,
`gemini/gemini-...`, `bedrock/...`, etc. — so every step goes through the same
`litellm.completion(...)` call regardless of vendor.

**TypeScript** — Vercel AI SDK, one `generateObject` per step:

```bash
npm i ai zod @ai-sdk/anthropic @ai-sdk/openai @ai-sdk/google
```

Be honest about cost: this pattern makes **N model calls** (one per step), and
each hop pays for the previous step's output as input. It wins when the per-step
model fit genuinely beats one model doing everything — not for a trivial task.

## Recipes

### 1. Python: typed step->model pipeline (drop-in)

`scripts/pipeline.py` runs a 4-stage pipeline — `plan` (reasoning model) ->
`code` (coding model) -> `review` (mid model) -> `summarize` (cheap model) —
where each stage's Pydantic output is the next stage's typed input.

```bash
export ANTHROPIC_API_KEY=... OPENAI_API_KEY=...
python3 scripts/pipeline.py "Build a function that dedupes a CSV by email column"
```

Re-route any stage from the environment — no code change:

```bash
STEP_MODEL_code=gemini/gemini-2.5-pro \
STEP_MODEL_plan=anthropic/claude-opus-4-6 \
  python3 scripts/pipeline.py "..."
```

Output is JSON: the typed `plan` / `code` / `review` / `summary` objects plus the
`routing` map actually used. stderr carries a per-step `model ok (Xs)` trace so
you can see which model owned each stage and how long it took.

The core is a single `run_step(step, schema, system, user)` that (a) looks up the
step's model, (b) requests JSON, (c) **validates into the Pydantic schema**, and
(d) on a validation miss re-asks the *same* model with the error so it
self-corrects. State is only ever passed forward after it validates.

### 2. The routing map is the whole design

Keep step->model in one immutable dict (or config file). This is the knob you
tune, and it documents intent:

```python
STEP_MODELS = {
    "plan":      "anthropic/claude-opus-4-6",   # deepest reasoning
    "code":      "openai/gpt-5.1",              # best coding
    "vision":    "gemini/gemini-2.5-pro",       # cheap strong multimodal
    "summarize": "anthropic/claude-haiku-4-5",  # cheap high-volume
}
```

Never hardcode a model inside step logic — a stage should be re-routable by
editing this map alone. That separation is what distinguishes this from a
hand-wired chain.

### 3. TypeScript: `generateObject` per step (Vercel AI SDK)

Each step calls `generateObject` with a Zod schema against its assigned model;
the parsed `.object` (typed) feeds the next step. The SDK auto-retries malformed
output and gives you an `object` typed by your Zod schema.

```ts
import { generateObject } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";

const STEP_MODELS = {
  plan: anthropic("claude-opus-4-6"),
  code: openai("gpt-5.1"),
} as const;

const { object: plan } = await generateObject({
  model: STEP_MODELS.plan,
  schema: z.object({ approach: z.string(), steps: z.array(z.string()) }),
  prompt: `Plan: ${task}`,
});

const { object: code } = await generateObject({
  model: STEP_MODELS.code,                    // different vendor, same seam
  schema: z.object({ language: z.string(), source: z.string() }),
  prompt: `Implement exactly this plan: ${JSON.stringify(plan)}`,
});
```

The Zod schema at each boundary is the typed handoff — a stage that returns the
wrong shape throws at the seam, not three steps later.

### 4. A vision/multimodal step in the middle

When one stage needs an image a text model can't read, route just that stage to a
multimodal model and keep the rest text. In litellm, pass image content on that
one `run_step` call (`{"type":"image_url","image_url":{"url": ...}}`); its typed
output (e.g. extracted fields) hands off to the next text step unchanged. The
pipeline shape doesn't change — only that step's entry in `STEP_MODELS`.

## Verify

- **Every seam is typed:** force a bad step output (e.g. temporarily point a step
  at a weak model or corrupt the schema) and confirm it raises at that seam with
  the validation error — not silently downstream.
- **Routing is honoured:** the `routing` block in the output must match your map;
  flip `STEP_MODEL_code` and confirm the code stage's trace shows the new model.
- **Per-step fit pays off:** compare the pipeline's end quality/cost against one
  strong model doing all steps. If a single model matches it, you don't need this
  — collapse the pipeline. Use `model-routing-eval-benchmark` to measure.

```bash
# Smoke: no API keys needed, just that it parses and imports.
python3 -c "import ast; ast.parse(open('scripts/pipeline.py').read()); print('ok')"
```

## Pitfalls

- **Error propagation.** A confidently-wrong plan poisons every later step. Type
  validation catches malformed handoffs, not *wrong-but-well-formed* ones — add a
  `review`/judge step (`cross-vendor-llm-judge`) for stages that gate on quality.
- **This isn't triage.** It runs the full pipeline every time. If you actually
  want "serve this one request as cheaply as possible", use
  `model-triage-router`; if you want "retry a bigger model only on failure",
  `model-cascade-escalation`.
- **Vendor key sprawl.** A step routed to Gemini needs `GEMINI_API_KEY` set or it
  fails at that seam with an auth error — provision every vendor a stage uses.
- **Model IDs go stale.** `claude-opus-4-6`, `gpt-5.1`, `gemini-2.5-pro` are
  current as of 2026-07 — confirm live IDs in each vendor's docs and update
  `STEP_MODELS`. litellm requires the vendor prefix (`anthropic/`, `openai/`,
  `gemini/`); a bare id may route to the wrong provider.
- **Latency stacks.** Steps are sequential by construction (each needs the prior
  output). Only parallelise steps that are genuinely independent; a linear
  reasoning->code->review chain cannot be.
- **Keep state immutable.** Each step returns a *new* typed object; never mutate a
  prior step's state in place — a reused/mutated handoff is a silent correctness
  bug and defeats the whole point of the typed seam.
- **Don't over-stage.** Two steps that the same model does equally well should be
  one step. Splitting for its own sake just doubles cost and latency (KISS).

Sources: [litellm providers](https://docs.litellm.ai/docs/providers/anthropic),
[Vercel AI SDK — generating structured data](https://ai-sdk.dev/docs/ai-sdk-core/generating-structured-data).
