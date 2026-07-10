---
name: pydantic-ai-typed-agents
category: agent-frameworks
description: >
  Build type-safe Python LLM agents with PydanticAI — a typed deps_type for dependency
  injection via RunContext, a Pydantic output_type for structured/validated results, tools
  (@agent.tool / @agent.tool_plain), async output_validator with ModelRetry reflection, dynamic
  instructions, and optional Temporal durable execution. Use when someone says "pydantic ai",
  "pydantic-ai agent", "type-safe agent", "structured agent output", "RunContext deps", "output
  validator retry", "agent tools with typed dependencies", or "durable pydantic agent".
when_to_use:
  - "You want a Python agent whose output is a validated Pydantic model, not free text"
  - "You need dependency injection (DB conn, API client, http session) passed to tools via RunContext"
  - "You want the model to self-correct with ModelRetry when output/tool validation fails"
  - "You're wiring tools that need typed context and want static type-checking of the whole agent"
  - "You need durable, crash-resilient agent runs via Temporal (TemporalAgent)"
  - "You said 'use pydantic-ai' or are already importing pydantic_ai"
when_not_to_use:
  - "You want graph/state-machine durable workflows with checkpoints — use langgraph-durable-workflows"
  - "You're standardising on OpenAI's own runner/handoffs — use openai-agents-sdk"
  - "You want multi-agent crews with role/flow orchestration — use crewai-flows-orchestration"
  - "You only need structured extraction from one LLM call, no agent loop — use instructor-structured-outputs or baml-structured-prompts"
  - "You're optimizing prompts/programs via compilation — use dspy-program-optimization or prompt-optimization"
keywords: [pydantic-ai, pydantic_ai, typed agents, run_context, runcontext, deps_type, output_type, output_validator, modelretry, agent.tool, tool_plain, structured output, dependency injection, temporal, durable execution, pydantic agent, type-safe llm, instructions]
similar_to: [openai-agents-sdk, langgraph-durable-workflows, crewai-flows-orchestration, instructor-structured-outputs, baml-structured-prompts]
inputs_needed:
  - "Which model provider/string (e.g. anthropic:claude-sonnet-4-6, openai:gpt-5.2) and its API key env var"
  - "The output shape you want (a Pydantic model or union) and what deps tools need (DB, http client, keys)"
  - "Whether you need durable execution (Temporal) or a plain in-process agent"
produces: A runnable Python module defining a typed Agent (deps_type + output_type + tools + validator) with a run entrypoint
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# PydanticAI Typed Agents

Build agents where **dependencies and outputs are typed**. `deps_type` gives tools/instructions a
type-checked `RunContext`; `output_type` forces a validated Pydantic result; `output_validator` +
`ModelRetry` let the model self-correct. Grounded against pydantic-ai **v2.x** (`requires_python
>=3.10`; docs now live at `pydantic.dev/docs/ai`).

## When to use

Reach for this when you want a real agent loop (tool calls + reflection) but refuse to hand back
unvalidated free text, and you want the whole agent statically type-checked. If you just need one
structured extraction with no tools, prefer `instructor-structured-outputs`.

## Prerequisites

```bash
pip install pydantic-ai          # full install, all provider extras
# or slim + one provider:
pip install "pydantic-ai-slim[anthropic]"   # or [openai], [google], ...
```

Set the provider key the model string implies (no key = auth error at first run):

```bash
export ANTHROPIC_API_KEY=sk-ant-...     # for anthropic:...
export OPENAI_API_KEY=sk-...            # for openai:...
```

Model strings are `provider:model`, e.g. `anthropic:claude-sonnet-4-6`, `openai:gpt-5.2`,
`google:gemini-2.5-pro`. You can also pass a model instance (e.g. `AnthropicModel(...)`).

## Recipe 1 — Minimal typed agent

```python
from pydantic_ai import Agent

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    instructions='Be concise, reply with one sentence.',
)
result = agent.run_sync('Where does "hello world" come from?')
print(result.output)          # str
print(result.usage())         # token usage
```

`agent.run(...)` is the async form; `run_sync` wraps it. Never define the agent inside a hot loop —
create it once at module scope.

## Recipe 2 — Structured output_type

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class Invoice(BaseModel):
    vendor: str
    total_cents: int = Field(ge=0)
    currency: str = Field(pattern=r'^[A-Z]{3}$')

agent = Agent('openai:gpt-5.2', output_type=Invoice)
inv = agent.run_sync('Acme charged us $42.50 USD.').output
assert isinstance(inv, Invoice)   # validated, typed
```

`output_type` accepts a `BaseModel`, a union (`Invoice | Refusal`), a `list[...]`, `TypedDict`, or a
plain function (an "output function"). The current parameter is `output_type` — older tutorials say
`result_type`; use `output_type`.

## Recipe 3 — Typed deps + RunContext + tools

Pass the **type** to `deps_type` (for static checking) and an **instance** to `deps=` at run time.
Tools that need context take `RunContext[YourDeps]` as their first parameter.

```python
from dataclasses import dataclass
import httpx
from pydantic_ai import Agent, RunContext

@dataclass
class Deps:
    http: httpx.AsyncClient
    api_key: str

agent = Agent('anthropic:claude-sonnet-4-6', deps_type=Deps, output_type=str)

# Dynamic instructions can read deps too:
@agent.instructions
def with_context(ctx: RunContext[Deps]) -> str:
    return f'You have {len(ctx.deps.api_key)} chars of credentials available.'

# Context tool — first param is RunContext[Deps]:
@agent.tool
async def get_rate(ctx: RunContext[Deps], base: str, quote: str) -> float:
    """Fetch an FX rate for base->quote."""
    r = await ctx.deps.http.get(
        'https://api.example.com/fx',
        params={'base': base, 'quote': quote},
        headers={'Authorization': f'Bearer {ctx.deps.api_key}'},
    )
    r.raise_for_status()
    return r.json()['rate']

# Context-free tool — no RunContext:
@agent.tool_plain
def today() -> str:
    """Return today's date (UTC, ISO)."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).date().isoformat()

async def main() -> None:
    async with httpx.AsyncClient() as http:
        deps = Deps(http=http, api_key='...')
        out = await agent.run('Convert 100 GBP to USD at today\'s rate.', deps=deps)
        print(out.output)
```

Rules: `@agent.tool` = needs `RunContext`; `@agent.tool_plain` = no context. Docstrings become the
tool description; typed params become the JSON schema.

## Recipe 4 — output_validator + ModelRetry (reflection)

For async/IO validation Pydantic can't express, validate after generation and raise `ModelRetry` to
make the model try again with your feedback.

```python
from pydantic_ai import Agent, RunContext, ModelRetry

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    deps_type=Deps,
    output_type=str,
    retries={'output': 2},      # output-retry budget (default 1)
)

@agent.output_validator
async def validate_sql(ctx: RunContext[Deps], sql: str) -> str:
    try:
        await ctx.deps.http.post('/explain', json={'sql': sql})
    except Exception as e:
        raise ModelRetry(f'Invalid SQL, fix it: {e}') from e
    return sql
```

Each `ModelRetry` consumes one unit of the output-retry budget. Set it via
`Agent(retries={'output': N})`, per run `agent.run(..., retries={'output': N})`, or per output tool.
Inside a tool, raise `ModelRetry` the same way to ask the model to re-call with better args.

## Recipe 5 — Durable execution with Temporal (optional)

Wrap any agent in `TemporalAgent` so model requests, tool calls, and MCP I/O run as replayable
Temporal activities — the run survives worker crashes.

```bash
pip install "pydantic-ai-slim[temporal]"   # + a running Temporal server
```

```python
from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import TemporalAgent, PydanticAIPlugin

agent = Agent('openai:gpt-5.2', name='billing')   # name is REQUIRED for Temporal
temporal_agent = TemporalAgent(agent)             # use inside a @workflow.defn
```

Must-knows: the agent `name` and each toolset `id` are **required and must not change** after
deploy (they key the activities); define `TemporalAgent` at module top level (workflow needs it at
import); register it via `PydanticAIPlugin` on the worker (or `AgentPlugin`); deps must be
Pydantic-serializable; model **instances** must be pre-registered via `TemporalAgent(models={...})`
(model strings work as-is).

## Verify

```bash
python -c "import pydantic_ai; print(pydantic_ai.__version__)"   # expect 2.x
```

- Run the agent once and assert `isinstance(result.output, YourModel)`.
- Type-check the whole thing: `pyright your_agent.py` (or `mypy`) — deps/output mismatches surface
  here, which is the entire point of pydantic-ai.
- Force a validation failure and confirm `ModelRetry` fires (watch `result.usage()` request count
  climb, or inspect `result.all_messages()`).

## Pitfalls

- **`deps_type` takes the type, `deps=` takes the instance.** Passing an instance to `deps_type`
  (or forgetting `deps=` at run time) is the #1 mistake.
- **`output_type`, not `result_type`.** The `result_*` names are legacy; new code uses `output`.
- **Tool decorator mismatch:** `@agent.tool` requires `RunContext` as the first arg; `@agent.tool_plain`
  must NOT take one. Mixing them up raises at registration.
- **Retry budget is small:** default output retries = 1. Bump `retries={'output': N}` before relying
  on `ModelRetry` loops, or the run errors out after one correction.
- **Don't recreate the Agent per request** — it's designed to be a module-level singleton; construct
  once, pass `deps` per run.
- **Temporal determinism:** never do raw I/O or read wall-clock time directly in a workflow; let the
  `TemporalAgent` offload it. Unset/renamed `name`/`id` breaks in-flight workflows.
- **API keys:** a missing provider key fails only at first `run`, not at construction — set env vars up front.

## References

- Docs: https://pydantic.dev/docs/ai/overview/ (agents, dependencies, tools, output, durable_execution/temporal)
- Repo: https://github.com/pydantic/pydantic-ai
