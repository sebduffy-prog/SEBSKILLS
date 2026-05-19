# Diagram types: how to read each kind

Different flow-shaped diagrams encode different things. The same arrow can
mean very different things depending on what kind of diagram you're reading.

## Site map / UI flow

**What it is:** Pages of a website or app, connected by navigation.

**Reading rules:**
- Arrow direction is **suggestive, not authoritative.** A child page drawn below its parent will usually have an arrow pointing down, but a child drawn above will have an arrow pointing up — both are "child of parent." Use layout, edge style, and labels to decide hierarchy, not arrows alone.
- Edge style encodes UX intent (primary nav vs. modal vs. toggle vs. secondary link).
- "Pages" can include modals, drawers, and toasts — read notes to disambiguate.
- Hubs are common and expected (Landing → many sub-pages).
- Back-routes are often implicit (every page has a way back to its parent).

**What to look for in critique:**
- Dead ends: terminal pages with no way out
- Orphans: pages reachable from nowhere
- Hub overload: too many children under one parent with no grouping
- Missing standard pages: 404, settings, profile, search, auth flow

**What to produce for build:**
- Route file (Next.js `app/` directory, React Router config, etc.)
- A component stub per page using notes as placeholder content
- Layout components for hubs (tabs / vertical scroll based on notes)

## User journey

**What it is:** A user's path through an experience, often with branches, emotions, or touchpoints across channels.

**Reading rules:**
- Direction is real — a journey moves through time.
- Branches usually represent user choices or system responses.
- Nodes are often phases or moments, not screens.
- Channel context matters: a "node" might be an email, an app screen, an in-store moment.

**What to look for in critique:**
- Friction points: phases with many backwards arrows or branches to abandonment
- Cross-channel handoffs that aren't smooth
- Emotional dips not addressed by the experience

**What to produce for build:**
- A journey timeline / Gantt-style doc, not code
- A research brief listing the moments to instrument or test

## State machine

**What it is:** A system with discrete states and transitions between them, triggered by events.

**Reading rules:**
- Direction is **strictly real.** An arrow from A to B means "from state A, on event X, transition to state B."
- Labels are events/triggers/guards, not just descriptions. `[on click]`, `[if valid]`, `[timeout]`.
- Self-loops are valid (state stays the same but processes an event).
- Initial states are marked explicitly (or are the only state with no incoming edges).
- Final states are marked explicitly (or are leaves).
- No "duplicate scoped" interpretation: every state is unique.

**What to look for in critique:**
- Unreachable states (no incoming transitions)
- States with no outgoing transitions when they should have them (no exit from "loading")
- Missing error/recovery transitions
- Race conditions: two transitions on the same event from the same state

**What to produce for build:**
- XState config, or framework-equivalent (Stately, Robot, etc.)
- TypeScript types for the state union and event union
- A visualisation link if XState

## Agent graph / workflow

**What it is:** A set of agents/nodes (often LLM-powered) connected by data flow or control flow. Common in LangGraph, n8n, Zapier, Temporal.

**Reading rules:**
- Direction is real and represents data/control flow.
- Nodes are typically agents, tools, or processing steps.
- Edges can be conditional (route based on output) or unconditional.
- Labels on edges often describe the routing condition or the data shape.
- Cycles are valid and common (loops with exit conditions).

**What to look for in critique:**
- Unbounded loops (no exit condition)
- Nodes with no clear inputs or outputs
- Missing error handlers
- Single points of failure

**What to produce for build:**
- LangGraph (Python) or LangGraph.js code
- Or a framework-appropriate orchestration config

## System architecture

**What it is:** Components of a software system and how they communicate.

**Reading rules:**
- Direction often means "calls" or "depends on."
- Bidirectional usually means request/response.
- Edge labels describe protocols (HTTP, gRPC, WebSocket, Kafka topic name).
- Node groupings (services, layers) matter — read containment/proximity.
- Dashed lines often mean async or optional dependencies.

**What to look for in critique:**
- Tight coupling (one component depended on by everything)
- Missing redundancy or failover
- Synchronous chains that could fail
- Unbounded retry loops

**What to produce for build:**
- A docker-compose / k8s manifest scaffold
- Or an interface/protocol contract per edge

## How to tell which kind you're reading

| Signal | Likely type |
|--------|-------------|
| Node titles are page names (Landing, Settings, Dashboard) | Site map |
| Node titles are user phases (Discovery, Purchase, Onboarding) | User journey |
| Node titles are states (idle, loading, error, success) | State machine |
| Node titles are agent/tool names (Researcher, Writer, Editor) | Agent graph |
| Node titles are services (API Gateway, Auth Service, DB) | System architecture |
| Edge labels are events ([on click], [timeout]) | State machine |
| Edge labels are user actions (clicks "Sign up") | Site map or journey |
| Cycles present | State machine or agent graph (not site map) |

If you're unsure, ask. Don't assume.
