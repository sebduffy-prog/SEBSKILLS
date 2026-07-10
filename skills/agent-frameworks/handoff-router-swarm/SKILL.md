---
name: handoff-router-swarm
category: agent-frameworks
description: >
  Build handoff-based agent swarms where specialists transfer control directly to each other — no central
  supervisor. The active agent is tracked in shared state and persists across turns, so the conversation resumes
  with whoever was last active. Covers the two production libraries: OpenAI Agents SDK handoffs (transfer_to_*
  tools) and langgraph-swarm (create_swarm + create_handoff_tool + SwarmState.active_agent). Use when the user
  says "swarm", "agent handoff", "agents that route to each other", "decentralized multi-agent", "active_agent",
  "transfer control between agents", "Alice hands off to Bob", or wants specialists that pass the baton without a router in the middle.
when_to_use:
  - User wants agents that hand control to each other peer-to-peer instead of routing through one supervisor
  - User wants the conversation to remember which agent was last active and resume there on the next turn
  - User asks for a "swarm", "handoff", "transfer_to", "active_agent", or the OpenAI-Swarm-style pattern
  - User is building a customer-support / triage flow where a specialist can bounce the user to another specialist
  - User wants langgraph-swarm's create_swarm/create_handoff_tool or OpenAI Agents SDK handoffs specifically
when_not_to_use:
  - One central LLM router picks a specialist per request, specialists never talk to each other → classifier-agent-routing
  - You want the full OpenAI Agents SDK surface (guardrails, sessions, tracing), not just handoffs → openai-agents-sdk
  - Durable checkpointed graph workflows with explicit edges/branches → langgraph-durable-workflows
  - Framework-agnostic discussion of orchestration topologies → agent-orchestration-patterns
  - Typed provider-agnostic single agents → pydantic-ai-typed-agents
keywords: [swarm, handoff, active_agent, transfer_to, langgraph-swarm, create_swarm, create_handoff_tool, openai agents handoffs, decentralized agents, peer handoff, multi-agent routing, agent baton pass, SwarmState, Command handoff, triage swarm, openai swarm successor]
similar_to: [openai-agents-sdk, classifier-agent-routing, agent-orchestration-patterns, langgraph-durable-workflows, crewai-flows-orchestration, swarm-guardrails, a2a-agent-interop]
inputs_needed:
  - Library target — OpenAI Agents SDK (openai-agents) or langgraph-swarm
  - API key for the model provider (OPENAI_API_KEY, or another via LiteLLM / a LangChain chat model)
  - The specialist agents and which agents each may hand off to (the handoff graph), plus the default/entry agent
produces: A runnable handoff swarm — specialist agents that transfer control to each other with active-agent state persisted across turns
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Handoff Router Swarm

A **swarm** is a decentralized multi-agent topology: specialists **hand off control directly to one another**, with no supervisor sitting in the middle. Two things define it:

1. **Handoff tools** — each agent exposes tools like `transfer_to_<agent>`; calling one transfers ownership of the loop to that agent (it does not return like a normal function).
2. **Active-agent state** — the currently-active agent is stored in shared, checkpointed state, so the *next* user turn resumes with whoever was last active instead of restarting at the entry agent.

This is the pattern OpenAI's experimental `Swarm` popularized. Two supported libraries implement it today: the **OpenAI Agents SDK** (Swarm's successor) and **langgraph-swarm**. Pick one below.

## When to use

Use this when specialists must **route to each other peer-to-peer** and the system must **remember the last-active agent across turns**. If instead one central classifier picks a specialist per request and specialists never talk, use `classifier-agent-routing`. For the full OpenAI Agents SDK (guardrails/sessions/tracing), use `openai-agents-sdk`; this skill is the focused swarm/handoff slice plus the langgraph implementation.

## Prerequisites

```bash
# Option A — OpenAI Agents SDK
pip install openai-agents
export OPENAI_API_KEY=sk-...

# Option B — langgraph-swarm
pip install langgraph-swarm langchain-openai
export OPENAI_API_KEY=sk-...
```

Both are Python 3.9+ (Agents SDK also has a TS port, `@openai/agents`). Any provider works — the Agents SDK via a per-agent `model=` (LiteLLM), langgraph-swarm via any LangChain chat model.

## Recipes

### 1. langgraph-swarm — active_agent persisted in shared state

`create_handoff_tool` returns a tool that issues a LangGraph `Command` updating `SwarmState.active_agent`. `create_swarm` wires the agents into one graph; **compile with a checkpointer** or the active agent won't survive between `.invoke()` calls. The `thread_id` in config keys the persisted state.

```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent          # or `from langchain.agents import create_agent` (v1)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph_swarm import create_handoff_tool, create_swarm

model = ChatOpenAI(model="gpt-4o")

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

alice = create_react_agent(
    model,
    tools=[add, create_handoff_tool(agent_name="Bob", description="Transfer to Bob, the pirate.")],
    prompt="You are Alice, an addition expert.",
    name="Alice",
)
bob = create_react_agent(
    model,
    tools=[create_handoff_tool(agent_name="Alice", description="Transfer to Alice for any math.")],
    prompt="You are Bob, you speak like a pirate.",
    name="Bob",
)

app = create_swarm([alice, bob], default_active_agent="Alice").compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "1"}}
t1 = app.invoke({"messages": [{"role": "user", "content": "i'd like to speak to Bob"}]}, config)
t2 = app.invoke({"messages": [{"role": "user", "content": "what's 5 + 7?"}]}, config)  # starts at Bob, who hands back to Alice
print(t2["active_agent"])   # -> "Alice"
```

> On langchain/langgraph 1.0 use `create_agent` from `langchain.agents` with `system_prompt=` instead of `create_react_agent`/`prompt=`. Both work with `langgraph_swarm`; check which is installed (`pip show langgraph`).

### 2. langgraph-swarm — a custom handoff tool that passes a summary

The default handoff forwards full message history. To hand off with a **curated context** (e.g. a task summary) rather than the raw transcript, write your own tool returning a `Command`.

```python
from typing import Annotated
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.prebuilt import InjectedState

def make_handoff(agent_name: str):
    @tool(f"transfer_to_{agent_name}", description=f"Hand off to {agent_name} with a task summary.")
    def _handoff(task_summary: str,
                 state: Annotated[dict, InjectedState],
                 tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        tool_msg = ToolMessage(content=f"Handed off to {agent_name}", tool_call_id=tool_call_id)
        return Command(
            goto=agent_name,                                   # jump to that agent's node
            graph=Command.PARENT,                              # navigate the parent swarm graph
            update={"messages": state["messages"] + [tool_msg],
                    "active_agent": agent_name,
                    "task": task_summary},                     # extra state the next agent reads
        )
    return _handoff
```

### 3. OpenAI Agents SDK — handoffs as `transfer_to_*` tools

A handoff is surfaced to the model as a `transfer_to_<agent>` tool; when called, the **target agent owns the rest of the loop** (not a sub-call that returns). List bare agents, or wrap with `handoff()` for a callback / typed input. Prefix every participant's instructions with `RECOMMENDED_PROMPT_PREFIX` so it understands the protocol. For a two-way swarm, give each specialist a handoff back.

```python
from pydantic import BaseModel
from agents import Agent, Runner, handoff, RunContextWrapper
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

class EscalationData(BaseModel):
    reason: str

async def on_escalate(ctx: RunContextWrapper, data: EscalationData):
    print(f"[escalated] {data.reason}")          # log / page a human

billing = Agent(name="Billing", instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nResolve billing questions.")
escalation = Agent(name="Escalation", instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nHandle refunds and angry customers.")

triage = Agent(
    name="Triage",
    instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nRoute to a specialist; don't answer directly.",
    handoffs=[billing, handoff(escalation, on_handoff=on_escalate, input_type=EscalationData)],
)
# Make it a true swarm: let specialists bounce back or to each other.
billing.handoffs = [triage, escalation]

result = Runner.run_sync(triage, "I was double-charged and I'm furious.")
print(result.last_agent.name, "->", result.final_output)   # last_agent = who ended the run
```

### 4. OpenAI Agents SDK — persist the active agent across turns

The Agents SDK does **not** auto-persist the active agent between separate `Runner.run` calls. To get swarm-style "resume with the last agent", carry `result.last_agent` yourself (and feed history back via `result.to_input_list()` or a `Session`).

```python
current = triage
history = "I was double-charged."
while True:
    result = Runner.run_sync(current, history)
    print(result.last_agent.name, ":", result.final_output)
    nxt = input("> ")
    if not nxt: break
    current = result.last_agent                      # <-- resume with whoever is now active
    history = result.to_input_list() + [{"role": "user", "content": nxt}]
```

### 5. Filter what the next agent inherits (Agents SDK)

Strip prior tool calls from the handed-off history so a specialist starts clean:

```python
from agents import handoff
from agents.extensions import handoff_filters

handoff(billing, input_filter=handoff_filters.remove_all_tools)
```

## Verify

```bash
# langgraph-swarm
python -c "import langgraph_swarm; print('swarm ok')"
# OpenAI Agents SDK
python -c "import agents; print('agents', getattr(agents,'__version__','ok'))"
```

Behavioural checks: (1) after a handoff, the response comes from the **target** specialist, not the entry agent; (2) langgraph — `app.invoke(...)["active_agent"]` reflects the last agent AND a second `.invoke()` on the same `thread_id` starts there; (3) Agents SDK — `result.last_agent.name` is the specialist, and your loop resumes with it; (4) a cyclic handoff (A→B→A) terminates and doesn't ping-pong forever.

## Pitfalls

- **No checkpointer = no memory (langgraph).** Without `.compile(checkpointer=...)` `active_agent` resets to `default_active_agent` every turn — the defining swarm behaviour silently vanishes. Always compile with a saver and pass a stable `thread_id`.
- **Handoff ≠ function call.** In both libraries the target agent takes over the loop; the caller does **not** resume afterward. If you need the caller to keep control and just borrow a capability, use the Agents SDK `.as_tool()` (agents-as-tools), not a handoff — that's `openai-agents-sdk` territory.
- **Agents SDK doesn't auto-persist the active agent** across `Runner.run` calls — you must carry `result.last_agent` yourself (Recipe 4). langgraph-swarm does persist it (in state).
- **Missing `RECOMMENDED_PROMPT_PREFIX` (Agents SDK).** Specialists without it often ignore the handoff protocol or refuse to transfer. Prefix every participating agent.
- **Ping-pong loops.** Two agents that each think the other should handle it can bounce forever. Give agents clear ownership in their prompts, cap turns (`Runner.run(..., max_turns=N)` raises `MaxTurnsExceeded`; add a recursion/step guard in langgraph), and make one agent authoritative.
- **`create_react_agent` vs `create_agent`.** langgraph-swarm examples drift between the legacy `langgraph.prebuilt.create_react_agent(prompt=)` and the v1 `langchain.agents.create_agent(system_prompt=)`. Match the API to your installed versions or you'll get `TypeError` on the prompt kwarg.
- **Swarm vs supervisor.** If specialists never hand off to each other and one node always decides routing, you want a **supervisor/classifier** (`classifier-agent-routing` or `langgraph-supervisor`), not a swarm. Swarm = decentralized peer handoffs.

## Sources

- OpenAI Agents SDK handoffs: https://openai.github.io/openai-agents-python/handoffs/
- langgraph-swarm: https://github.com/langchain-ai/langgraph-swarm-py · https://reference.langchain.com/python/langgraph-swarm
- Original pattern: https://github.com/openai/swarm (experimental; superseded by the Agents SDK)
