---
name: a2a-agent-interop
category: agent-frameworks
description: >
  Make agents from different frameworks or vendors talk to each other over Google's Agent2Agent (A2A) protocol —
  publish a discoverable Agent Card at /.well-known/agent-card.json, expose your agent as an A2A server with
  AgentSkills and a task lifecycle, and call remote agents as an A2A client. Use when the user says "A2A",
  "agent2agent", "agent-to-agent protocol", "agent card", "make my agent callable by other agents", "cross-framework
  agent interop", "let LangGraph/CrewAI/ADK agents talk", or asks how A2A relates to MCP. Produces a runnable
  a2a-sdk server plus a client that discovers and messages it.
when_to_use:
  - User wants their agent discoverable and callable by agents built in other frameworks (LangGraph, CrewAI, ADK, custom)
  - User asks to publish or consume an Agent Card / .well-known/agent-card.json
  - User wants to call a remote agent as a client and track its task through submitted → working → completed
  - User asks how A2A (agent-to-agent) differs from or complements MCP (agent-to-tools)
  - User is building a multi-vendor or multi-team agent mesh and needs a standard wire protocol
  - User mentions streaming updates, push notifications, or extended (authenticated) agent cards
when_not_to_use:
  - Connecting an agent to tools/data sources, not other agents → build an MCP server with mcp-builder
  - Orchestrating agents inside ONE framework/process → openai-agents-sdk, crewai-flows-orchestration, langgraph-durable-workflows
  - In-process handoff/router/swarm patterns with no network protocol → handoff-router-swarm or agent-orchestration-patterns
  - Typed single-framework agents in pure Python → pydantic-ai-typed-agents
keywords: [a2a, agent2agent, agent-to-agent, a2a-sdk, agent card, agentcard, well-known, agent-card.json, cross-framework interop, agent mesh, agentexecutor, task lifecycle, jsonrpc agent, a2a vs mcp, remote agent, agntcy, linux foundation a2a]
similar_to: [openai-agents-sdk, crewai-flows-orchestration, langgraph-durable-workflows, agent-orchestration-patterns, handoff-router-swarm, pydantic-ai-typed-agents]
inputs_needed:
  - What the agent does (its one or more AgentSkills) and its base URL/port
  - Whether you are the SERVER (exposing an agent), the CLIENT (calling one), or both
  - Auth needs (public card only, or an authenticated extended card / security schemes)
produces: A runnable A2A server exposing an Agent Card + a client that discovers it and sends a message through the task lifecycle
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# A2A Agent Interop

Agent2Agent (A2A) is an open protocol (originally Google, now Linux Foundation) that lets an agent expose itself as a networked service other agents can **discover, call, and collaborate with** — regardless of framework or vendor. It is the peer layer to MCP: **MCP connects an agent to tools/data; A2A connects an agent to other agents.** Both coexist.

Three primitives:
- **Agent Card** — a JSON "business card" at `/.well-known/agent-card.json` listing identity, `capabilities`, and `skills`.
- **Task** — a stateful unit of work with a lifecycle: `submitted → working → (input_required) → completed | failed | canceled`.
- **Message / Part** — a turn (role `user`/`agent`) made of typed Parts (text, file, or structured data), plus result **Artifacts**.

## When to use

When two or more agents need a standard wire protocol to talk across process/framework/org boundaries. If you only need to hand off *inside one framework*, use that framework's orchestration skill instead. If you need to give an agent *tools*, build an MCP server (`mcp-builder`), not an A2A server.

## Prerequisites

Python 3.10+. The SDK is versioned 1.x (matches the current spec; the Agent Card path was renamed from the legacy `/.well-known/agent.json` to `/.well-known/agent-card.json` in v0.3+).

```bash
pip install a2a-sdk uvicorn httpx
# Extras as needed: a2a-sdk[grpc]  a2a-sdk[sql]  a2a-sdk[telemetry]  a2a-sdk[encryption]
python -c "import a2a, importlib.metadata as m; print('a2a-sdk', m.version('a2a-sdk'))"  # expect >= 1.1.0
```

No API key for the protocol itself. If your agent wraps an LLM (via any framework), that framework keeps its own keys — A2A only wraps the interface.

## Recipes

### 1. Define the agent's skills and Agent Card

The card is what the world discovers. Each `AgentSkill` advertises one capability; `capabilities` declares protocol features (streaming, push, extended card).

```python
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, AgentInterface

skill = AgentSkill(
    id="echo_bot",
    name="Echo Bot",
    description="Acknowledges a request and replies with a Hello World message.",
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    tags=["a2a", "echo-example"],
    examples=["hi", "how are you"],
)

public_card = AgentCard(
    name="Hello World Agent",
    description="Just a hello world agent",
    version="0.0.1",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True, extended_agent_card=True),
    supported_interfaces=[
        AgentInterface(protocol_binding="JSONRPC", url="http://127.0.0.1:9999", protocol_version="1.0"),
    ],
    skills=[skill],
)
```

### 2. Implement the AgentExecutor (the server-side brain)

`execute()` receives a `RequestContext` and an `EventQueue`; you drive the task through its states and emit artifacts. Swap the `invoke` body for a call into any framework (LangGraph, CrewAI, pydantic-ai, a bare LLM call).

```python
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.helpers import new_task_from_user_message, get_message_text, new_text_message, new_text_part
from a2a.types import TaskState

class HelloWorldExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task_from_user_message(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue=event_queue, task_id=task.id, context_id=task.context_id)
        await updater.update_status(TaskState.TASK_STATE_WORKING, message=new_text_message("Processing request..."))

        query = get_message_text(context.message) or ""
        result = f"Hello, World! I received: {query}"   # <- plug your real agent in here

        await updater.add_artifact(parts=[new_text_part(text=result, media_type="text/plain")])
        await updater.update_status(TaskState.TASK_STATE_COMPLETED, message=new_text_message("Done"))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancel not supported.")
```

### 3. Serve it (Agent Card + JSON-RPC routes)

`DefaultRequestHandler` wires the executor to a task store; helper route factories mount the well-known card and the JSON-RPC endpoint. Alternative bindings: `GRPC`, `HTTP_JSON`.

```python
import uvicorn
from starlette.applications import Starlette
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore

handler = DefaultRequestHandler(
    agent_executor=HelloWorldExecutor(),
    task_store=InMemoryTaskStore(),        # swap for a SQL/Redis store in prod (a2a-sdk[sql])
    agent_card=public_card,
)

routes = []
routes.extend(create_agent_card_routes(public_card))   # serves /.well-known/agent-card.json
routes.extend(create_jsonrpc_routes(handler, "/"))     # serves the JSON-RPC message endpoint
app = Starlette(routes=routes)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9999)
```

### 4. Discover + call it as a client

Resolve the card first, then let the SDK client pick the interface and speak the protocol for you. `send_message` yields task/message chunks as they arrive.

```python
import asyncio, httpx
from a2a.client import A2ACardResolver, create_client, ClientConfig
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest

async def main():
    async with httpx.AsyncClient() as http:
        card = await A2ACardResolver(httpx_client=http, base_url="http://127.0.0.1:9999").get_agent_card()

    client = await create_client(agent=card, client_config=ClientConfig(streaming=False))
    req = SendMessageRequest(message=new_text_message("Why is the sky blue?", role=Role.ROLE_USER))
    async for chunk in client.send_message(req):
        print(chunk)
    await client.close()

asyncio.run(main())
```

Set `ClientConfig(streaming=True)` to get incremental status/artifact updates over SSE (requires `capabilities.streaming=True` on the card).

### 5. Bridging another framework

You do NOT rewrite your agent — you wrap it. In `execute()`, call your existing agent and forward its output as artifacts:

```python
# LangGraph:   result = await my_graph.ainvoke({"messages": [("user", query)]})
# CrewAI:      result = my_crew.kickoff(inputs={"q": query})
# pydantic-ai: result = (await my_agent.run(query)).output
await updater.add_artifact(parts=[new_text_part(text=str(result))])
```

Google's ADK ships first-class A2A helpers (`to_a2a(...)`), but any framework works via the executor wrapper above.

## Verify

```bash
# 1. Card is discoverable and well-formed (plain GET — no auth on the public card):
curl -s http://127.0.0.1:9999/.well-known/agent-card.json | python3 -m json.tool | head -30
# expect: name, version, capabilities, skills[] present

# 2. Round-trip a message with the client (recipe 4) and confirm you see
#    a task transition to TASK_STATE_COMPLETED and an artifact carrying your text.
```

Sanity checklist: card lists your skill; a message returns a task that reaches `completed`; streaming client receives >1 chunk when `streaming=True`.

## Pitfalls

- **A2A ≠ MCP.** A2A is agent↔agent (delegate a task to a peer). MCP is agent↔tools (call a function, read a resource). If the counterpart is a tool/data source, build an MCP server instead — don't force it through A2A.
- **Wrong well-known path.** v0.3+ serves `/.well-known/agent-card.json`. Old tutorials use `/.well-known/agent.json`; a client pointed at the legacy path 404s. Let `A2ACardResolver` use its default path unless you deliberately moved it.
- **API churn between majors.** The 0.2.x API (`A2AStarletteApplication`, `Message(parts=[Part(root=TextPart(...))])`, `message/send`) differs from the 1.x API shown here (`create_agent_card_routes` / `create_jsonrpc_routes`, `new_text_message`, `Role.ROLE_USER`, `TaskState.TASK_STATE_*`). Pin your version and match its docs; don't mix snippets across majors.
- **Executor must move the task or the client hangs.** Always `enqueue_event(task)` for a new task, then update status to a terminal state (`COMPLETED`/`FAILED`). Emitting artifacts without a terminal status leaves the client waiting.
- **`InMemoryTaskStore` is dev-only.** It loses tasks on restart and won't scale across replicas — use a persistent store (`a2a-sdk[sql]`) in production.
- **Card is a public attack surface.** Only advertise real skills; put sensitive skills on the authenticated **extended card** (`extended_agent_card=...` on the handler, fetched via `get_extended_agent_card`) behind a `securityScheme`. Never leak internal endpoints in the public `supported_interfaces`.
- **Streaming claims must be honest.** Setting `capabilities.streaming=True` but never emitting intermediate `update_status` events makes streaming clients look stalled. Advertise only what the executor actually does.

## Ecosystem note

A2A is now under the Linux Foundation with SDKs in Python (`a2a-sdk`), JS/TS, Java, .NET and Go. Related efforts: **AGNTCY / Internet of Agents** (agent identity + directory + ACP messaging) tackle discovery and identity at internet scale and can layer over A2A. For a full mesh: MCP for tools, A2A for peer tasks, AGNTCY/registry for discovery.
