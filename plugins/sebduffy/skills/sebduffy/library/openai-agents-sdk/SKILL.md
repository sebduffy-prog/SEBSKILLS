---
name: openai-agents-sdk
category: agent-frameworks
description: >
  Build multi-agent apps with the OpenAI Agents SDK (the production successor to Swarm) — define Agents with typed tools,
  wire Handoffs that transfer control between agents, add input/output Guardrails as fail-fast tripwires, persist
  conversation memory with Sessions, and get built-in Tracing for free. Use when the user says "OpenAI Agents SDK",
  "agents SDK", "openai-agents", "handoffs", "triage agent", "guardrails", "Swarm replacement", or wants a
  Python/TypeScript orchestrator, router, or customer-support-style multi-agent workflow on OpenAI models.
when_to_use:
  - User asks to build a multi-agent app, router, or triage/orchestrator on the OpenAI Agents SDK (openai-agents)
  - User wants handoffs so one agent transfers control of the conversation to a specialist agent
  - User wants input/output guardrails that trip and abort a run when a check fails (off-topic, jailbreak, PII)
  - User wants persistent conversation memory across turns via Sessions (SQLite/Redis/SQLAlchemy)
  - User is migrating from OpenAI Swarm and wants the supported successor
  - User wants built-in tracing/observability for LLM calls, tool calls, and handoffs
when_not_to_use:
  - Provider-agnostic typed agents in pure Python → use pydantic-ai-typed-agents
  - Durable, checkpointed, resumable graph workflows → use langgraph-durable-workflows
  - Role/crew + sequential flow orchestration → use crewai-flows-orchestration
  - Generic handoff/router concepts not tied to this SDK → use handoff-router-swarm or agent-orchestration-patterns
  - Cross-framework agent interoperability protocol → use a2a-agent-interop
keywords: [openai-agents, agents sdk, openai agents sdk, handoffs, guardrails, sessions, tracing, swarm, triage agent, function_tool, Runner, agent orchestration, multi-agent, tripwire, as_tool, openai-agents-python, openai-agents-js]
similar_to: [pydantic-ai-typed-agents, langgraph-durable-workflows, crewai-flows-orchestration, handoff-router-swarm, agent-orchestration-patterns, swarm-guardrails, agent-evals-and-tracing]
inputs_needed:
  - Language target (Python `openai-agents` or TypeScript `@openai/agents`)
  - OPENAI_API_KEY (or a configured non-OpenAI model provider)
  - The agent topology (single agent, triage→specialists, or orchestrator-with-tools) and any guardrail/memory needs
produces: A runnable multi-agent app (agents, tools, handoffs, guardrails, session memory) with tracing enabled
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# OpenAI Agents SDK

Build production multi-agent apps on the OpenAI Agents SDK — the supported successor to the experimental Swarm. Five primitives: **Agents** (an LLM + instructions + tools), **Handoffs** (transfer control to another agent), **Guardrails** (parallel fail-fast checks), **Sessions** (automatic conversation memory), and **Tracing** (on by default). Deliberately few abstractions; it's Python/TS you can read.

## When to use

Use this skill when the user names the OpenAI Agents SDK / `openai-agents`, wants handoffs, guardrails, sessions, or tracing on OpenAI models, or is migrating off Swarm. For provider-agnostic typed agents prefer `pydantic-ai-typed-agents`; for durable checkpointed graphs prefer `langgraph-durable-workflows`.

## Prerequisites

Python 3.9+ (or Node 18+ for TS). Install and set your key:

```bash
pip install openai-agents          # Python. Extras: openai-agents[redis], [sqlalchemy], [viz]
# npm install @openai/agents zod   # TypeScript
export OPENAI_API_KEY=sk-...
```

`Runner.run()` is async; `Runner.run_sync()` wraps it. Tracing streams to the OpenAI dashboard automatically when `OPENAI_API_KEY` is set — no extra config. To use a non-OpenAI model, pass a `model=` string/object per agent or set a default client (see Pitfalls).

## Recipes

### 1. Minimal agent with a typed tool

`@function_tool` reads the signature, type hints, and docstring to build the JSON schema — keep the docstring accurate, it's sent to the model.

```python
from agents import Agent, Runner, function_tool

@function_tool
def get_weather(city: str) -> str:
    """Return the current weather for a city.

    Args:
        city: Name of the city to look up.
    """
    return f"The weather in {city} is sunny, 22°C."

agent = Agent(
    name="Assistant",
    instructions="You are concise. Use tools when asked about weather.",
    tools=[get_weather],
    model="gpt-4.1",          # optional; omit for the SDK default
)

result = Runner.run_sync(agent, "What's the weather in Lisbon?")
print(result.final_output)
```

### 2. Handoffs — a triage agent that transfers control

A handoff is exposed to the LLM as a `transfer_to_<agent>` tool. When the model calls it, the target agent **owns the rest of the loop** (it is not a sub-call that returns). List target agents directly, or wrap with `handoff()` for callbacks/typed input. Prefix specialist instructions with `RECOMMENDED_PROMPT_PREFIX` so they understand the handoff protocol.

```python
from pydantic import BaseModel
from agents import Agent, Runner, handoff, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

billing_agent = Agent(
    name="Billing agent",
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nYou resolve billing and invoice questions.",
)

class EscalationData(BaseModel):
    reason: str

async def on_escalate(ctx: RunContextWrapper, data: EscalationData):
    print(f"[escalated] {data.reason}")   # log, page a human, etc.

escalation_agent = Agent(
    name="Escalation agent",
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nYou handle angry customers and refunds.",
)

triage_agent = Agent(
    name="Triage agent",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "Route the user to the right specialist. Do not answer directly."
    ),
    handoffs=[
        billing_agent,                                   # bare agent
        handoff(escalation_agent, on_handoff=on_escalate, input_type=EscalationData),
    ],
)

result = Runner.run_sync(triage_agent, "I was double-charged and I'm furious.")
print(result.last_agent.name, "->", result.final_output)
```

Filter what history the next agent sees with `input_filter=handoff_filters.remove_all_tools` (from `agents.extensions.handoff_filters`) to strip prior tool calls.

### 3. Agents as tools (orchestrator keeps control)

When you want the orchestrator to *stay in charge* and just call a sub-agent like a function (e.g. parallel translations), use `.as_tool()` instead of a handoff.

```python
spanish = Agent(name="Spanish", instructions="Translate the input to Spanish.")
french  = Agent(name="French",  instructions="Translate the input to French.")

orchestrator = Agent(
    name="Orchestrator",
    instructions="Call the translation tools the user requests, then combine results.",
    tools=[
        spanish.as_tool(tool_name="to_spanish", tool_description="Translate to Spanish"),
        french.as_tool(tool_name="to_french",  tool_description="Translate to French"),
    ],
)
```

Handoff = give away the conversation. `as_tool` = borrow a capability and keep it.

### 4. Input & output guardrails (fail-fast tripwires)

Guardrails run **in parallel** with the agent. Set `tripwire_triggered=True` to abort the run with an exception — cheaper models here reject bad input before the expensive agent finishes.

```python
from pydantic import BaseModel
from agents import (
    Agent, Runner, GuardrailFunctionOutput, RunContextWrapper,
    input_guardrail, InputGuardrailTripwireTriggered,
)

class Topicality(BaseModel):
    is_off_topic: bool
    reasoning: str

topic_checker = Agent(
    name="Topic checker",
    instructions="Decide if the user's message is unrelated to customer support.",
    output_type=Topicality,
    model="gpt-4.1-mini",
)

@input_guardrail
async def off_topic_guardrail(ctx: RunContextWrapper, agent: Agent, user_input):
    check = await Runner.run(topic_checker, user_input, context=ctx.context)
    return GuardrailFunctionOutput(
        output_info=check.final_output,
        tripwire_triggered=check.final_output.is_off_topic,
    )

support_agent = Agent(
    name="Support",
    instructions="Help with product support questions only.",
    input_guardrails=[off_topic_guardrail],
)

try:
    Runner.run_sync(support_agent, "Write me a poem about the moon.")
except InputGuardrailTripwireTriggered as e:
    print("Blocked:", e.guardrail_result.output.output_info.reasoning)
```

Output guardrails are identical with `@output_guardrail` (signature takes `output` instead of input) attached via `output_guardrails=[...]`; they raise `OutputGuardrailTripwireTriggered`.

### 5. Sessions — automatic conversation memory

Pass a `session` and the runner auto-loads prior turns before each run and stores new items after — no manual `to_input_list()` bookkeeping.

```python
from agents import Agent, Runner, SQLiteSession

agent   = Agent(name="Assistant", instructions="Reply concisely.")
session = SQLiteSession("user-42", "conversations.db")   # omit path for in-memory

r1 = Runner.run_sync(agent, "What city is the Golden Gate Bridge in?", session=session)
print(r1.final_output)   # San Francisco
r2 = Runner.run_sync(agent, "What state is it in?", session=session)
print(r2.final_output)   # California — context carried automatically
```

Swap the backend without touching agent code: `SQLAlchemySession` (Postgres/MySQL, `[sqlalchemy]` extra), `RedisSession` (`[redis]` extra), or `OpenAIConversationsSession` (server-managed).

### 6. Tracing & a custom trace span

Tracing is **on by default**; view runs at platform.openai.com/traces. Group several `Runner.run` calls into one trace, or disable globally.

```python
from agents import Runner, trace, set_tracing_disabled

async def handle_ticket(agent, msg):
    with trace("customer-ticket-workflow"):
        triaged = await Runner.run(agent, msg)
        follow  = await Runner.run(agent, "Summarise the resolution.")
    return follow.final_output

# set_tracing_disabled(True)   # opt out entirely (e.g. ZDR / non-OpenAI models)
```

## Verify

```bash
python -c "import agents, inspect; print('agents', getattr(agents,'__version__','ok'))"
python your_app.py                       # exercise it end-to-end
```

Confirm: (1) `result.final_output` is populated; (2) for handoffs `result.last_agent.name` is the specialist, not the triage agent; (3) a guardrail on bad input raises `InputGuardrailTripwireTriggered`; (4) a second same-session turn resolves a pronoun/reference from the first; (5) the run appears under Traces in the OpenAI dashboard.

## Pitfalls

- **`RESULT.final_output` vs the loop.** The SDK runs an agentic loop until the model produces a final message (no more tool/handoff calls) or `max_turns` is hit — it raises `MaxTurnsExceeded`, not a silent stop. Set `Runner.run(..., max_turns=N)` for cost control.
- **Handoff ≠ function call.** After a handoff the original agent does **not** resume. If you need the caller to keep control, use `.as_tool()` (Recipe 3).
- **Missing the prompt prefix.** Specialist agents that lack `RECOMMENDED_PROMPT_PREFIX` often try to hand back or ignore the protocol. Always prefix instructions on any agent that participates in handoffs.
- **Guardrails aren't content filters.** They're single-purpose tripwires that run concurrently and abort the run; don't stuff broad moderation logic in one — use a cheap fast model (`gpt-4.1-mini`) so the check finishes before the main agent.
- **Async vs sync.** `Runner.run` is a coroutine — `await` it or use `Runner.run_sync`. Don't call `run_sync` from inside a running event loop (Jupyter/async web handler); use `await Runner.run` there.
- **Non-OpenAI models.** Built-in hosted tools (`WebSearchTool`, `FileSearchTool`) need the OpenAI Responses API. For other providers pass a per-agent `model` (LiteLLM: `pip install "openai-agents[litellm]"`, `model="litellm/anthropic/claude-..."`) and consider `set_tracing_disabled(True)` or a custom trace exporter.
- **Docstrings are the schema.** For `@function_tool`, wrong/absent type hints or an inaccurate docstring produce a bad tool schema and misfired calls. Keep annotations tight.
- **TypeScript parity.** `@openai/agents` mirrors the same primitives (`Agent`, `run`, `handoff`, `tool` with Zod schemas, guardrails). API shapes differ slightly — verify against openai.github.io/openai-agents-js before porting Python verbatim.

## Sources

- Docs: https://openai.github.io/openai-agents-python/ (handoffs, guardrails, sessions, tools, tracing sub-pages)
- Repos: https://github.com/openai/openai-agents-python · https://github.com/openai/openai-agents-js
