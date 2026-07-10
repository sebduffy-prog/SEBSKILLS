---
name: llm-observability
category: agent-frameworks
description: >-
  Wire full production LLM/agent observability into an existing Claude or OpenAI
  app with Langfuse — trace every call and agent trajectory (inputs, outputs,
  cost, latency, tool spans), version prompts, build eval datasets from real
  traffic, and run LLM-as-judge scores in CI. Self-hostable via Docker
  (ClickHouse-backed). Reach for this when you need always-on telemetry to see,
  debug, and measure what your agents actually do in prod — not a one-off eval.
when_to_use:
  - You have a working Claude/OpenAI/agent app and now need to SEE every call in prod (inputs, outputs, token cost, latency, errors)
  - You want to debug a multi-step agent trajectory as a nested trace of spans and tool calls
  - You need prompt versioning with labels so prompt edits don't require a redeploy
  - You want to turn real production traces into eval datasets and score them with LLM-as-judge in CI
  - You need self-hosted, data-resident observability (no SaaS egress) via Docker
when_not_to_use:
  - You only need a one-off offline eval or accuracy benchmark — use agent-evals-and-tracing or swarm-evaluation-harness instead
  - You want the framework's own built-in tracing UI (LangSmith for LangGraph, OpenAI traces) and no cross-framework store — stay in that framework
  - You need input/output content moderation or jailbreak blocking, not telemetry — use llm-guardrails-injection-defense
  - The app doesn't exist yet — build it first (openai-agents-sdk, pydantic-ai-typed-agents, langgraph-durable-workflows)
keywords:
  - langfuse
  - observability
  - tracing
  - opentelemetry
  - llm-as-judge
  - prompt-versioning
  - datasets
  - evals
  - cost-tracking
  - latency
  - spans
  - self-hosting
  - clickhouse
  - agent-telemetry
  - production
similar_to:
  - agent-evals-and-tracing
  - swarm-evaluation-harness
  - prompt-optimization
inputs_needed: An existing LLM/agent app (Anthropic or OpenAI SDK, or LangGraph/OpenAI-Agents); Docker (for self-host) or a Langfuse Cloud key pair; Python 3.9+
produces: Instrumented app emitting Langfuse traces; a self-host docker-compose stack; a versioned prompt; an eval dataset seeded from prod traffic; an LLM-as-judge experiment runnable in CI
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# LLM Observability with Langfuse

Always-on production telemetry for LLM and agent apps: wrap your existing calls so
every request becomes a **trace** (nested spans with inputs, outputs, model, token
cost, latency, errors), version your prompts server-side, seed eval **datasets** from
real traffic, and run **LLM-as-judge** scores in CI. This is the production telemetry
half; the offline-eval half lives in `agent-evals-and-tracing`. They share the same
Langfuse store, so a failing prod trace becomes an eval case in one click.

## When to use

Use this once an app is live and you're flying blind — you can't answer "why did the
agent do that?", "what did this cost?", or "which prompt version was live at 3am?".
Langfuse answers all three from one trace view. Skip it for a one-shot benchmark
(that's an eval harness) or if your framework's native tracing already suffices and you
don't need a cross-framework, self-hostable store.

## Prerequisites

```bash
python3 -m pip install "langfuse>=3.0" openai anthropic
# For OpenTelemetry auto-instrumentation of raw provider SDKs:
python3 -m pip install openinference-instrumentation-anthropic openinference-instrumentation-openai
```

Three env vars drive everything (the SDK reads them automatically):

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="http://localhost:3000"   # or https://cloud.langfuse.com
```

## Mechanism / Steps

### 1. Self-host the stack (Docker, ClickHouse-backed)

```bash
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up -d          # brings up langfuse-web, langfuse-worker, ClickHouse, Postgres, Redis, MinIO
# wait ~2-3 min until `langfuse-web-1` logs "Ready", then open http://localhost:3000
```

Sign up (first user is admin), create a project, copy the `pk-lf-…` / `sk-lf-…` keys
into the env vars above. The compose file is dev/eval-grade; for prod HA/backups use the
Kubernetes Helm chart, not compose.

### 2. Instrument — pick the lightest integration that fits

**(a) Decorator — your own functions and agent steps.** `@observe` captures inputs,
outputs, timing, and exceptions with zero body changes; nested calls auto-nest as spans.

```python
from langfuse import observe, get_client

langfuse = get_client()

@observe()                                   # a SPAN
def retrieve(query: str) -> list[str]:
    return vector_store.search(query)

@observe(name="answer", as_type="generation")   # a GENERATION (model call)
def answer(query: str) -> str:
    docs = retrieve(query)                   # nests under the parent trace
    resp = client.messages.create(model="claude-haiku-4-5", max_tokens=512,
        messages=[{"role": "user", "content": f"{docs}\n\n{query}"}])
    # attach usage/model so cost + latency compute automatically:
    langfuse.update_current_generation(
        model="claude-haiku-4-5",
        usage_details={"input": resp.usage.input_tokens,
                       "output": resp.usage.output_tokens})
    return resp.content[0].text
```

Set trace-level IO and identity so traces are searchable by user/session:

```python
langfuse.update_current_trace(user_id="u_42", session_id="sess_9",
                              tags=["prod"], input=query, output=result)
```

**(b) OpenTelemetry auto-instrumentation — raw provider SDKs, no code edits.** Langfuse
v3 is an OTel backend, so any GenAI instrumentor exports straight into it:

```python
from openinference.instrumentation.anthropic import AnthropicInstrumentor
AnthropicInstrumentor().instrument()          # every Anthropic call now traced
# OpenAIInstrumentor().instrument() for the OpenAI SDK
```

**(c) LangGraph / OpenAI-Agents SDK.** Attach the callback/processor once; every node,
tool call, and handoff becomes a span under one trace — the payoff for multi-step agents.

Always flush before a short-lived process exits (CLI, Lambda) or you lose the tail:

```python
langfuse.flush()
```

### 3. Version prompts server-side (edit without redeploy)

```python
langfuse.create_prompt(name="qa-system", type="chat", labels=["production"],
    prompt=[{"role": "system", "content": "You are a {{tone}} support agent."},
            {"role": "user", "content": "{{question}}"}])

prompt = langfuse.get_prompt("qa-system", label="production")   # fetch live version
messages = prompt.compile(tone="concise", question=user_q)      # {{var}} substitution
# Passing the prompt object into the call links this generation to that prompt VERSION,
# so the trace shows exactly which prompt produced the output.
```

Editing the prompt in the UI mints a new version; move the `production` label to roll
forward/back instantly — no deploy. `get_prompt` is client-side cached with TTL.

### 4. Build a dataset from real traffic → run LLM-as-judge

Find a bad trace in the UI, click "Add to dataset" (or set `source_trace_id` via API) so
regressions become permanent test cases. Then run an experiment:

```python
from langfuse import get_client, Evaluation
langfuse = get_client()

ds = langfuse.create_dataset(name="qa-regressions")
ds.create_item(input={"question": "refund policy?"}, expected_output="30 days")

def task(*, item, **kwargs):                 # runs your real app on each item
    return answer(item["input"]["question"])

def judge(*, input, output, expected_output, **kwargs):   # LLM-as-judge
    verdict = client.messages.create(model="claude-sonnet-4-6", max_tokens=64,
        messages=[{"role": "user",
            "content": f"Q:{input['question']}\nGold:{expected_output}\n"
                       f"Answer:{output}\nReply 1 if correct else 0."}])
    score = 1.0 if "1" in verdict.content[0].text else 0.0
    return Evaluation(name="correctness", value=score)

result = langfuse.run_experiment(name="qa-nightly", data=ds,
                                 task=task, evaluators=[judge])
print(result.format())                       # per-item + aggregate scores
```

### 5. Gate CI on the aggregate score

```python
avg = sum(r.evaluations[0].value for r in result.item_results) / len(result.item_results)
raise SystemExit(0 if avg >= 0.9 else 1)     # fail the pipeline if quality regresses
```

Wire this into GitHub Actions with the three `LANGFUSE_*` secrets pointed at cloud or a
CI-spun compose stack. Traces from CI runs land beside prod traces, tagged by run.

## Verify

- `curl -s http://localhost:3000/api/public/health` returns `{"status":"OK"}` (self-host up).
- After one instrumented request, the trace appears in the UI within seconds with a
  non-zero **cost** and **latency** and the correct **model** — if cost is zero you didn't
  pass `usage_details`/`model`.
- A nested call shows child spans under the parent (trajectory captured), not flat.
- The generation's detail panel links to the exact **prompt version** used.
- `result.format()` prints scores; the same scores show on those items' traces in the UI.

## Pitfalls

- **Cost shows 0 / model "unknown".** OTel auto-instrumentors report usage for you, but
  manual `@observe` generations don't — call `update_current_generation(model=…, usage_details=…)`.
- **Lost traces in short-lived runners.** The SDK batches; always `langfuse.flush()` (or use
  the client as a context manager) before a CLI/serverless process exits.
- **Secrets leaked into traces.** Inputs/outputs are stored verbatim — mask PII/keys before
  logging, or set `LANGFUSE_TRACING_ENABLED=false` per environment.
- **v2 code on v3 SDK.** v3 is OTel-native; old `langfuse.trace()`/`generation()` chaining is
  gone. Use `@observe`, `get_client()`, `start_as_current_observation()`, `update_current_*`.
- **Compose in prod.** The docker-compose stack has no HA/backup — fine for dev/CI/self-eval,
  but use the Helm chart for real production and put ClickHouse on durable storage.
- **Double instrumentation.** Enabling both an OTel instrumentor and manual `@observe` on the
  same call nests one inside the other — pick one layer per call site.
- **Prompt cache staleness.** `get_prompt` caches; after moving a label, allow the TTL (or set
  `cache_ttl_seconds=0` in a test) before asserting the new version is live.
