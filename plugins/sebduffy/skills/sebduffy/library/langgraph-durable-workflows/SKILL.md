---
name: langgraph-durable-workflows
category: agent-frameworks
description: >
  Build stateful, durable, multi-agent systems with LangGraph — StateGraph with typed state
  and reducers, supervisor and orchestrator-worker topologies (fan-out with Send()),
  checkpointers (InMemory/SQLite/Postgres) for crash-durable state, interrupt() +
  Command(resume=) human-in-the-loop approval gates, and time-travel replay via
  get_state_history. Use when asked to build a LangGraph agent, a durable/resumable agent
  workflow, an approval-gated agent, a multi-agent supervisor, a map-reduce agent graph,
  or to add checkpointing / persistence / human-in-the-loop to an existing LangGraph app.
when_to_use:
  - "Build a LangGraph agent or multi-node StateGraph from scratch"
  - "Make an agent workflow durable/resumable so it survives crashes and restarts (checkpointer)"
  - "Add a human approval gate that pauses the agent and waits for a yes/no (interrupt)"
  - "Coordinate multiple specialist agents under a supervisor that routes work"
  - "Fan out work across N parallel workers and gather results (orchestrator-worker / map-reduce)"
  - "Rewind an agent run to an earlier checkpoint and replay (time-travel debugging)"
when_not_to_use:
  - "Single OpenAI Agents SDK agent with handoffs → use openai-agents-sdk"
  - "CrewAI Flow / crew orchestration specifically → use crewai-flows-orchestration"
  - "Typed Pydantic-first agents with dependency injection → use pydantic-ai-typed-agents"
  - "Generic routing/handoff/swarm patterns not tied to LangGraph → use agent-orchestration-patterns or handoff-router-swarm"
  - "Evaluating/tracing agents rather than building them → use agent-evals-and-tracing"
keywords: [langgraph, stategraph, checkpointer, interrupt, command resume, human-in-the-loop, supervisor, create_supervisor, send api, map-reduce, orchestrator-worker, time-travel, durable execution, langchain agents, add_messages, thread_id, persistence, langraph]
similar_to: [openai-agents-sdk, crewai-flows-orchestration, pydantic-ai-typed-agents, agent-orchestration-patterns, handoff-router-swarm]
inputs_needed:
  - "LLM provider + model (e.g. OpenAI gpt-4o, Anthropic) and the matching API key env var"
  - "Persistence target: ephemeral (InMemory), local dev (SQLite file), or production (Postgres URL)"
  - "Topology: single graph, supervisor+specialists, or orchestrator+parallel workers"
  - "Whether a human approval / pause step is required, and what it gates"
produces: Runnable Python LangGraph app (StateGraph + checkpointer) with durable state, optional supervisor/fan-out, and interrupt-based human-in-the-loop.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# LangGraph Durable Workflows

Build agent systems as a **graph of nodes over shared typed state**, persisted by a
**checkpointer** so any run is durable, resumable, pauseable for a human, and rewindable.

## When to use

Reach for this when a workflow needs more than a single prompt→response: shared-state steps,
jobs that must survive a crash, approval gates, parallel workers, or replay from a past
checkpoint. One agent with tool calls and no persistence? A plain `create_react_agent` is
enough — but the moment you say "resumable", "approval", "supervisor", or "fan-out", use the
full graph below.

## Prerequisites

```bash
pip install langgraph langgraph-supervisor langchain "langchain[openai]"
# persistence backends (install what you use):
pip install langgraph-checkpoint-sqlite      # SqliteSaver
pip install langgraph-checkpoint-postgres psycopg   # PostgresSaver
export OPENAI_API_KEY=sk-...    # or ANTHROPIC_API_KEY, etc.
```

Python ≥ 3.10. Versions move fast — pin what you ship (`pip freeze | grep langgraph`).
Core imports live in `langgraph.graph`, `langgraph.types`, `langgraph.prebuilt`, and the
`langgraph.checkpoint.*` packages.

## Recipe 1 — StateGraph with typed state + reducers

State is a `TypedDict`. `Annotated[..., reducer]` tells LangGraph how to merge each node's
partial return into the running state (append vs overwrite). `add_messages` appends and
dedups chat messages by id.

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]   # appended
    topic: str                                # overwritten
    draft: str

def plan(state: State) -> dict:
    return {"draft": f"outline about {state['topic']}"}

def write(state: State) -> dict:
    return {"messages": [{"role": "assistant", "content": state["draft"]}]}

builder = StateGraph(State)
builder.add_node("plan", plan)
builder.add_node("write", write)
builder.add_edge(START, "plan")
builder.add_edge("plan", "write")
builder.add_edge("write", END)
graph = builder.compile()

print(graph.invoke({"messages": [], "topic": "durable agents", "draft": ""}))
```

**Conditional routing** — a router returns the *name* of the next node:
`builder.add_conditional_edges("write", lambda s: "plan" if len(s["draft"]) < 20 else END)`.

## Recipe 2 — Durability with a checkpointer

Compile with a checkpointer and pass a `thread_id`. Every super-step is persisted, so a
process can die and resume from the last checkpoint. The `thread_id` is the conversation /
run key (keep it < 255 chars for Postgres).

```python
from langgraph.checkpoint.memory import InMemorySaver   # ephemeral / tests
graph = builder.compile(checkpointer=InMemorySaver())

config = {"configurable": {"thread_id": "run-42"}}
graph.invoke({"messages": [], "topic": "x", "draft": ""}, config)
# later, same thread_id resumes with accumulated state:
graph.invoke({"messages": [{"role": "user", "content": "expand it"}]}, config)
```

Swap the backend for real durability:

```python
# local dev — a single file on disk
from langgraph.checkpoint.sqlite import SqliteSaver
with SqliteSaver.from_conn_string("checkpoints.sqlite") as cp:
    graph = builder.compile(checkpointer=cp)

# production — Postgres (call setup() once to create tables)
from langgraph.checkpoint.postgres import PostgresSaver
with PostgresSaver.from_conn_string("postgresql://user:pw@host/db") as cp:
    cp.setup()
    graph = builder.compile(checkpointer=cp)
```

**Durability modes** (control how much you flush per step; pass to `invoke`/`stream`):
`durability="sync"` (safest, write before proceeding), `"async"` (default-ish, write in
background), `"exit"` (only persist at the end — fastest, least durable).

```python
graph.invoke(inputs, config, durability="sync")
```

## Recipe 3 — Human-in-the-loop with interrupt()

`interrupt(payload)` pauses the graph, persists state, and surfaces `payload` to your code.
You resume by re-invoking with `Command(resume=value)`; that `value` becomes the return of
`interrupt()` inside the node. **Requires a checkpointer** — the pause is a saved checkpoint.

```python
from langgraph.types import interrupt, Command

def approval(state: State) -> dict:
    decision = interrupt({"question": "Publish this draft?", "draft": state["draft"]})
    if decision != "approve":
        return {"draft": ""}          # rejected → clear
    return {"messages": [{"role": "assistant", "content": "published"}]}

builder.add_node("approval", approval)
# ... wire edges, compile with a checkpointer ...

config = {"configurable": {"thread_id": "run-99"}}
result = graph.invoke(initial_state, config)
if "__interrupt__" in result:                 # graph paused for a human
    print(result["__interrupt__"][0].value)   # your payload → show to the user
    graph.invoke(Command(resume="approve"), config)   # resume with their answer
```

The graph re-runs the interrupting node from its start on resume, so keep side effects
*after* the `interrupt()` call, not before it.

## Recipe 4 — Supervisor multi-agent (prebuilt)

`create_supervisor` builds a StateGraph where a supervisor LLM delegates to named
specialist agents via tool-based handoffs. Each specialist is a `create_react_agent`.

```python
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

model = init_chat_model("openai:gpt-4o")

def web_search(query: str) -> str:
    """Search the web."""
    return "Netflix has 14,000 employees."

research = create_react_agent(model=model, tools=[web_search],
    name="research_expert", prompt="You are a researcher. Do no math.")
math = create_react_agent(model=model, tools=[lambda a: a],  # real math tools here
    name="math_expert", prompt="You are a math expert.")

supervisor = create_supervisor(
    [research, math], model=model,
    prompt="You manage a research expert and a math expert. Route each request."
).compile(checkpointer=InMemorySaver())   # checkpointer optional but recommended

supervisor.invoke({"messages": [{"role": "user", "content": "Netflix headcount?"}]},
                  {"configurable": {"thread_id": "t1"}})
```

Note: the LangChain team now often recommends hand-rolling the supervisor as plain
tool-calls for finer context control, but `create_supervisor` is the fastest correct start.

## Recipe 5 — Orchestrator-worker fan-out with Send()

`Send(node, state)` dispatches a dynamic number of parallel worker invocations, each with
its own slice of state. A reducer on the collecting field merges the results (map-reduce).

```python
import operator
from langgraph.types import Send

class MapState(TypedDict):
    items: list[str]
    results: Annotated[list, operator.add]   # reducer gathers worker outputs

def fan_out(state: MapState):                # returns a list of Send objects
    return [Send("worker", {"item": it}) for it in state["items"]]

def worker(state: dict) -> dict:
    return {"results": [state["item"].upper()]}

b = StateGraph(MapState)
b.add_node("worker", worker)
b.add_conditional_edges(START, fan_out, ["worker"])
b.add_edge("worker", END)
mr = b.compile()
print(mr.invoke({"items": ["a", "b", "c"], "results": []}))   # -> {'results': ['A','B','C'], ...}
```

## Recipe 6 — Time-travel replay

Every checkpoint is inspectable and resumable. Walk history, pick a past checkpoint, and
re-invoke from it (optionally editing state first) to explore a different branch.

```python
config = {"configurable": {"thread_id": "run-42"}}
for snap in graph.get_state_history(config):
    print(snap.config["configurable"]["checkpoint_id"], snap.next, snap.values)

# resume from a specific earlier checkpoint (optionally fork with edited state first):
past = {"configurable": {"thread_id": "run-42", "checkpoint_id": "<id-from-above>"}}
graph.update_state(past, {"topic": "new angle"})   # optional edit
graph.invoke(None, past)                            # replays forward from that point
```

## Verify

```bash
python your_graph.py            # Recipe 1 prints accumulated messages/draft
```
- **Durable**: kill the process mid-run, re-invoke with the same `thread_id` → it resumes,
  not restarts. `list(graph.get_state_history(config))` is non-empty.
- **HITL**: first `invoke` returns a dict containing `"__interrupt__"`; the run only
  finishes after `Command(resume=...)`.
- **Fan-out**: `results` length equals `len(items)` (proves the reducer merged all workers).
- Visualize the topology to confirm wiring: `graph.get_graph().draw_mermaid()`.

## Pitfalls

- **interrupt without a checkpointer** raises / silently no-ops — the pause *is* a saved
  checkpoint. Always compile with one for HITL.
- **Side effects before interrupt()** run twice: the node restarts from the top on resume.
  Put API calls, writes, and emails *after* the `interrupt()` line.
- **Missing thread_id** with a checkpointer errors — the `configurable.thread_id` is the
  persistence key; generate a stable one per conversation/run.
- **No reducer on a fan-out field** means parallel workers overwrite each other. Use
  `Annotated[list, operator.add]` (or `add_messages`) on anything multiple nodes write.
- **Node returns full state**: return only the *changed* keys as a dict; the reducer merges.
  Returning the whole state can clobber concurrent updates.
- **Postgres**: call `cp.setup()` once before first use, and keep `thread_id` < 255 chars.
- **InMemorySaver is not durable** across restarts — dev/tests only; use SQLite/Postgres for
  anything that must survive a crash. Import paths and `durability=` semantics shift across
  releases — ground against the installed version's docs, not old blog snippets. Pin versions.
