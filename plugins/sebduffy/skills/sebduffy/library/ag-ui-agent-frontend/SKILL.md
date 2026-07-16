---
name: ag-ui-agent-frontend
category: frontend-and-design
description: >
  Wire an AG-UI-speaking agent backend into a React/Next.js frontend with CopilotKit —
  stream agent events (text, tool calls, shared state, reasoning) into a live chat panel
  and render generative UI. Use it whenever an agent (LangGraph, CrewAI, Mastra, ADK,
  Pydantic AI, or a custom SSE endpoint) needs a real user-facing app: token-streaming
  chat, tool-call cards, human-in-the-loop approvals, shared agent<->UI state, and
  frontend actions the agent can call. Grounds every package, import, event type and
  route handler against the real AG-UI + CopilotKit v2 API so it compiles.
when_to_use:
  - Connecting an existing agent backend (LangGraph, CrewAI, Mastra, ADK, Pydantic AI, custom) to a web UI over the AG-UI protocol
  - Rendering an agent's streamed events — text deltas, tool calls, reasoning, state — in a React chat surface (CopilotChat / CopilotSidebar / CopilotPopup)
  - Adding generative UI — the agent picks a React component and fills it with data (static generative UI via useCopilotAction render)
  - Building human-in-the-loop approval steps (renderAndWaitForResponse) before an agent action commits
  - Sharing bidirectional state between agent and UI (useCoAgent) so both see the same document/plan
  - Exposing frontend actions and readable context the agent can call/read (useCopilotAction handler + useCopilotReadable)
  - Emitting spec-correct AG-UI SSE events from a custom (non-framework) agent endpoint
when_not_to_use:
  - Building a chatbot on the Vercel AI SDK v7 (useChat/streamText), not an AG-UI agent — use generative-ui-chat-interface
  - Exposing tools to Claude Desktop / an MCP host rather than a web frontend — use mcp-builder or mcp-connectors
  - Net-new visual/brand direction for the page rather than agent wiring — use frontend-design
  - Authoring the agent's backend logic/graph itself rather than its UI — use building-agents or agent-frameworks
keywords:
  - ag-ui
  - copilotkit
  - generative-ui
  - agent-frontend
  - streaming-events
  - useCopilotAction
  - useCoAgent
  - human-in-the-loop
  - copilot-runtime
  - httpagent
  - sse
  - shared-state
  - langgraph
  - react
  - tool-calls
similar_to:
  - generative-ui-chat-interface
  - building-agents
  - frontend-ui-engineering
  - mcp-connectors
inputs_needed: A running AG-UI-compatible agent endpoint (or a framework adapter URL), a React/Next.js App Router app, Node 18+, and the agent's tool/state shape.
produces: A Next.js /api/copilotkit runtime route plus provider-wrapped React UI that streams agent events, renders generative-UI components, shares state, and runs human-in-the-loop approvals.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# AG-UI Agent Frontend (CopilotKit)

Connect an **agentic backend** to a **web frontend** over **AG-UI** — the open, event-based
protocol that standardises how agents stream to user-facing apps — and render the stream with
**CopilotKit**, the first-party AG-UI client (React/Next.js). This is the missing link between an
agent that *runs* and an app a user can *see and steer*. Distinct from MCP Apps (which surface
tools to an MCP host like Claude Desktop): AG-UI targets your own web UI.

## When to use

Reach for this when an agent already runs (LangGraph, CrewAI, Mastra, Google ADK, Pydantic AI,
Microsoft Agent Framework, or a hand-rolled SSE endpoint) and you need it inside a real app:
streaming chat, tool-call cards, shared state, approvals, and generative UI. If you only need a
plain streaming chatbot on the Vercel AI SDK, use `generative-ui-chat-interface` instead.

## Prerequisites (honest deps)

- **Node 18+** and a **Next.js App Router** app (`app/` dir). CopilotKit also supports Angular/React Router; this skill uses Next.js.
- An **AG-UI-compatible agent URL**. Framework adapters exist (`@ag-ui/langgraph`, `@ag-ui/crewai`, `@ag-ui/mastra`, `@ag-ui/pydantic-ai`, etc.); or any endpoint that emits AG-UI SSE.
- npm packages (verify latest with `npm view <pkg> version`):
  - Frontend: `@copilotkit/react-core` `@copilotkit/react-ui`
  - Runtime (server route): `@copilotkit/runtime`
  - AG-UI client for direct/dev connections: `@ag-ui/client`
  - Custom backend emitter (optional): `@ag-ui/core` `@ag-ui/encoder`
- **No API key needed for CopilotKit's OSS runtime** when your agent does the LLM calls. CopilotKit Cloud (`publicApiKey`) is optional.

```bash
npm install @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime @ag-ui/client
```

## AG-UI event model (what streams over the wire)

AG-UI events are a typed, event-sourced stream (SSE by default). The `EventType` enum in
`@ag-ui/core` uses SCREAMING_SNAKE_CASE values. The ones you will render:

- Lifecycle: `RUN_STARTED` `RUN_FINISHED` `RUN_ERROR` `STEP_STARTED` `STEP_FINISHED`
- Text: `TEXT_MESSAGE_START` `TEXT_MESSAGE_CONTENT` `TEXT_MESSAGE_END` `TEXT_MESSAGE_CHUNK`
- Tools: `TOOL_CALL_START` `TOOL_CALL_ARGS` `TOOL_CALL_END` `TOOL_CALL_RESULT` `TOOL_CALL_CHUNK`
- State (bidirectional): `STATE_SNAPSHOT` `STATE_DELTA` (JSON-Patch RFC 6902) `MESSAGES_SNAPSHOT`
- Reasoning: `REASONING_START` `REASONING_MESSAGE_CONTENT` `REASONING_END`; escape hatches `RAW` `CUSTOM`

CopilotKit consumes these for you — you rarely touch raw events unless you write a custom backend (Recipe D).

## Recipe A — Production runtime route (recommended)

The runtime runs in your trusted server. Create `app/api/copilotkit/route.ts`:

```typescript
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

// EmptyAdapter: your agent already does the LLM calls, so no provider adapter needed.
const serviceAdapter = new ExperimentalEmptyAdapter();

const runtime = new CopilotRuntime({
  agents: {
    // key = agent name you reference from the UI
    myAgent: new HttpAgent({ url: process.env.AGENT_URL! }), // e.g. http://localhost:8000/
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
```

Wrap your app (root layout or a client component). Point `runtimeUrl` at the route and name the agent:

```tsx
"use client";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="myAgent">
      {children}
      <CopilotSidebar labels={{ title: "Assistant", initial: "How can I help?" }} />
    </CopilotKit>
  );
}
```

`CopilotChat`, `CopilotPopup`, and `CopilotSidebar` are the three prebuilt surfaces — all consume the same runtime and render streamed text, tool calls, and reasoning automatically.

## Recipe B — Frontend action + generative UI

`useCopilotAction` both (a) gives the agent a **frontend tool** it can call and (b) lets you
**render a React component** for that call — this is *static generative UI*: the agent picks the
component and fills the args, the frontend owns the look.

```tsx
"use client";
import { useCopilotAction } from "@copilotkit/react-core";

function FlightPanel() {
  useCopilotAction({
    name: "showFlight",
    description: "Display a flight option to the user.",
    parameters: [
      { name: "airline", type: "string", required: true },
      { name: "price", type: "number", required: true },
      { name: "depart", type: "string", description: "ISO datetime" },
    ],
    // render is called on every streamed arg update; status: "inProgress" | "complete"
    render: ({ status, args }) => (
      <div className="rounded-xl border p-4">
        <strong>{args.airline ?? "…"}</strong> — £{args.price ?? "…"}
        {status !== "complete" && <span> (streaming…)</span>}
      </div>
    ),
  });
  return null;
}
```

Give the agent **read-only context** with `useCopilotReadable({ description: "Current cart", value: cart })`.

## Recipe C — Human-in-the-loop approval

Use `renderAndWaitForResponse` to pause the agent until the user decides. The promise resolves
with your `respond(...)` value, which is fed back to the agent as the tool result.

```tsx
useCopilotAction({
  name: "sendEmail",
  parameters: [{ name: "to", type: "string" }, { name: "body", type: "string" }],
  renderAndWaitForResponse: ({ args, respond, status }) => (
    <div className="rounded-xl border p-4">
      <p>Send to {args.to}?</p>
      <button disabled={status === "complete"} onClick={() => respond?.("approved")}>Send</button>
      <button disabled={status === "complete"} onClick={() => respond?.("rejected")}>Cancel</button>
    </div>
  ),
});
```

## Recipe D — Custom AG-UI backend (no framework adapter)

If you own the agent and want to emit AG-UI directly, stream spec-correct SSE. Minimal shape of a
single assistant message run (Node/Express):

```typescript
import { EventEncoder } from "@ag-ui/encoder";
import { EventType } from "@ag-ui/core";

app.post("/", (req, res) => {
  const enc = new EventEncoder();
  res.setHeader("Content-Type", "text/event-stream");
  const send = (e: any) => res.write(enc.encode(e));
  const threadId = req.body.threadId, runId = crypto.randomUUID(), messageId = crypto.randomUUID();

  send({ type: EventType.RUN_STARTED, threadId, runId });
  send({ type: EventType.TEXT_MESSAGE_START, messageId, role: "assistant" });
  for (const chunk of ["Hello", " from", " AG-UI"]) {
    send({ type: EventType.TEXT_MESSAGE_CONTENT, messageId, delta: chunk });
  }
  send({ type: EventType.TEXT_MESSAGE_END, messageId });
  send({ type: EventType.RUN_FINISHED, threadId, runId });
  res.end();
});
```

Point the runtime's `HttpAgent({ url })` at this endpoint. `EventEncoder` handles SSE framing
(`data: …\n\n`); do not hand-format if you can encode.

## Recipe E — Shared agent state (`useCoAgent`)

For LangGraph/CrewAI-style agents that stream `STATE_SNAPSHOT`/`STATE_DELTA`, bind the agent's
state to React so UI and agent stay in sync bidirectionally:

```tsx
import { useCoAgent } from "@copilotkit/react-core";
const { state, setState } = useCoAgent<{ plan: string[] }>({
  name: "myAgent",
  initialState: { plan: [] },
});
// state.plan updates live as the agent emits deltas; setState pushes UI edits back to the agent.
```

## Verify

1. **Types/build**: `npx tsc --noEmit` and `npm run build` — catches wrong imports (e.g. `@copilotkit/react-core` vs `/v2`) and missing `styles.css`.
2. **Route alive**: `curl -N -X POST localhost:3000/api/copilotkit -H 'content-type: application/json' -d '{}'` should return a streaming response, not 404/500.
3. **Agent reachable**: `curl -N -X POST "$AGENT_URL" -d '{"threadId":"t1","runId":"r1","messages":[]}'` — expect `data:` SSE lines beginning with a `RUN_STARTED` event.
4. **In-app**: open the chat surface, send a prompt, confirm tokens stream in and any tool-call `render` mounts. If a tool call never renders, the `name` in `useCopilotAction` must match the tool the agent emits.

## Pitfalls

- **v2 import split**: some newer CopilotKit docs import `CopilotKit` from `@copilotkit/react-core/v2`. Pick ONE version consistently across provider, hooks, and runtime — mixing v1 and v2 imports silently breaks context. Check which your installed version exposes (`npm ls @copilotkit/react-core`).
- **Forgot the stylesheet**: without `import "@copilotkit/react-ui/styles.css"` the chat renders unstyled/broken. Import it once, high in the tree.
- **`agents__unsafe_dev_only` in production**: the direct `HttpAgent` connection on the provider bypasses the server runtime's auth/middleware. Fine for local prototyping only — route through `CopilotRuntime` for anything shipped.
- **Agent-name mismatch**: the `agents` key in `CopilotRuntime`, the `agent="…"` prop, and `useCoAgent({ name })` must all use the same string.
- **Missing `RUN_STARTED`/`RUN_FINISHED`**: a custom backend that streams text without lifecycle events leaves the UI spinning forever. Always open with `RUN_STARTED` and close with `RUN_FINISHED` (or `RUN_ERROR`).
- **State deltas are JSON-Patch**: `STATE_DELTA` payloads are RFC 6902 patch arrays, not partial objects — build them with a JSON-Patch helper, don't hand-diff.
- **CORS**: the runtime calls the agent server-to-server (no CORS); the dev-only direct connection is browser-to-agent and WILL need CORS headers on the agent.
- **This is not MCP Apps**: to expose tools/UI to an MCP host (Claude Desktop), AG-UI is the wrong layer — use `mcp-builder`.
