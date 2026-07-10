---
name: managed-agent-memory
category: context-engineering
description: >
  Wire a managed memory service into an agent instead of hand-rolling memory files — Mem0
  (extract/store/search facts), Zep + Graphiti (temporal knowledge-graph memory with a
  ready-made context block), or Letta (server-managed stateful agents with editable memory
  blocks). Use when the user says "give my agent long-term memory", "remember users across
  sessions", "mem0", "zep", "graphiti", "letta / MemGPT", "memory as a service", "personalise
  the assistant", or wants retrieval-backed memory without building the vector/graph store.
when_to_use:
  - You need cross-session user memory but do not want to build the store, embeddings, and retrieval yourself
  - The agent must recall preferences/facts about many distinct end-users (multi-tenant personalisation)
  - Facts change over time and you need temporal / graph memory that supersedes stale beliefs (Zep/Graphiti)
  - You want a hosted stateful agent whose memory the model edits itself (Letta / MemGPT blocks)
  - Comparing Mem0 vs Zep vs Letta before committing, and need the real APIs and trade-offs
when_not_to_use:
  - Plain files (CLAUDE.md / NOTES.md) or Anthropic's /memories tool suffice — use agent-memory-file
  - Retrieving from a document corpus rather than per-user memories — use a rag/* retrieval skill
  - Deciding which layers of memory exist and their precedence — use structured-memory-layers
  - Summarising/pruning an overflowing window in place — use agent-context-compaction
  - Storing agent state in your own DB with no memory logic — use agent-context-db
keywords: [mem0, zep, graphiti, letta, memgpt, managed memory, agent memory, long-term memory, memory as a service, memory blocks, knowledge graph memory, temporal memory, cross-session, personalization, vector memory, mem0ai, zep-cloud, letta-client]
similar_to: [agent-memory-file, structured-memory-layers, agent-context-db, agent-context-compaction]
inputs_needed:
  - Which end-user identity keys memory (a stable user_id) and whether it is multi-tenant
  - Hosting choice — managed cloud (API key) vs self-host (Docker + your own LLM/vector/graph backends)
  - An LLM + embedding provider key (OpenAI etc.) — these services still call a model to extract facts
produces: A working memory integration (add + retrieve) against Mem0, Zep, or Letta, plus a chosen-service rationale
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Managed Agent Memory

Don't hand-roll a vector store, embedding pipeline, and fact-extraction prompt when a service does
it. These platforms take raw conversation turns, extract durable facts, store them keyed by
`user_id`, and hand back a compact context string to prepend on the next turn. You keep the window
lean; they own storage and retrieval.

Three shapes, pick by need:

| Service | Model of memory | Best when | Self-host |
|---|---|---|---|
| **Mem0** | Extracted fact list, vector-searched | Simple per-user facts, minimal setup | Yes (`mem0ai`, bring Qdrant + LLM) |
| **Zep / Graphiti** | Temporal knowledge **graph** with a prebuilt context block | Facts change over time, relationships matter, low-latency retrieval | Graphiti core is OSS (needs Neo4j/FalkorDB) |
| **Letta (MemGPT)** | Stateful agent with editable **memory blocks** the LLM self-edits | You want the agent itself to manage core memory + archival recall | Yes (Docker server) |

All three still call an LLM to extract/embed — a provider key (e.g. `OPENAI_API_KEY`) is a real
dependency even on the managed tiers.

## When to use

- Cross-session recall about **many end-users** (a chatbot that remembers each customer).
- Facts that **evolve** ("moved to Bristol", "no longer vegan") and must supersede old ones — graph
  memory (Zep) handles supersession; a flat fact list can accumulate contradictions.
- You want a hosted agent whose memory the model edits itself (Letta).

If one user and one project, files are simpler — use `agent-memory-file` instead.

## Prerequisites

- **Python 3.9+** (macOS system Python is fine) or Node. Install only the SDK you chose.
- **A cloud API key** (`MEM0_API_KEY`, `ZEP_API_KEY`, or Letta cloud token) **or** Docker to self-host.
- **An LLM + embedding key** for extraction/embeddings (OpenAI default on Mem0 OSS). Managed tiers
  bundle this but you still authenticate to the memory service.
- Never hardcode keys — read from env. These stores hold end-user PII; treat `user_id` as a tenant
  boundary and keep memories namespaced per user.

## Recipe 1 — Mem0 (extracted-fact memory)

Managed platform (`MemoryClient`) — zero infra:

```python
import os
from mem0 import MemoryClient

client = MemoryClient(api_key=os.environ["MEM0_API_KEY"])

# Store: pass raw turns; Mem0 extracts the durable facts, not the whole transcript.
client.add(
    [{"role": "user", "content": "I'm allergic to peanuts and I prefer window seats."}],
    user_id="alex",
)

# Retrieve at prompt-build time: semantic search scoped to the user.
hits = client.search("dietary and travel preferences", filters={"user_id": "alex"})
memory_block = "\n".join(m["memory"] for m in hits)   # prepend to your system prompt
```

Open-source, self-hosted (no Mem0 key; needs an LLM key + local Qdrant):

```python
from mem0 import Memory                 # pip install mem0ai
m = Memory()                            # defaults: OpenAI extract/embeddings, on-disk Qdrant
m.add([{"role": "user", "content": "I use pnpm, never npm."}], user_id="alex")
m.search("package manager", filters={"user_id": "alex"})
```

The **loop**: on each turn `search` for the user's memories, inject the top few into the system
prompt, generate a reply, then `add` the new turn so future turns learn from it.

## Recipe 2 — Zep / Graphiti (temporal graph + context block)

Zep builds a per-user knowledge graph and returns a ready-to-inject **context block** in one call —
you don't assemble it yourself.

```python
import os, uuid
from zep_cloud.client import Zep       # pip install zep-cloud
from zep_cloud.types import Message

client = Zep(api_key=os.environ["ZEP_API_KEY"])

# One Zep user per end-user; identify them well (name/email aid graph resolution).
client.user.add(user_id="alex", first_name="Alex", email="alex@example.com")

# One thread per conversation.
thread_id = uuid.uuid4().hex
client.thread.create(thread_id=thread_id, user_id="alex")

# Add turns AND get the context block back in the same call (return_context avoids a round-trip).
resp = client.thread.add_messages(
    thread_id,
    messages=[Message(name="Alex", role="user", content="I just moved to Bristol.")],
    return_context=True,
)
context_block = resp.context            # temporally-aware facts; prepend to your system prompt
```

Retrieve later without adding, and ingest non-chat business data into the same graph:

```python
ctx = client.thread.get_user_context(thread_id=thread_id).context
client.graph.add(user_id="alex", type="json", data='{"plan":"pro","seats":5}')
```

Graph memory's win: when "moved to Bristol" arrives, the old location edge is marked invalid with a
timestamp rather than left to contradict — retrieval returns the current truth. The OSS engine is
`graphiti-core` (`pip install graphiti-core`), but it requires you to run Neo4j or FalkorDB.

## Recipe 3 — Letta (self-editing memory blocks)

Letta hosts the whole agent server-side. Memory lives in labelled **blocks** the model reads and
rewrites itself; long-tail facts spill to archival memory it can search.

```python
from letta_client import Letta         # pip install letta-client

client = Letta(token="LETTA_API_KEY")           # cloud
# client = Letta(base_url="http://localhost:8283")  # self-hosted Docker server

agent = client.agents.create(
    model="openai/gpt-4o-mini",
    embedding="openai/text-embedding-3-small",
    memory_blocks=[
        {"label": "human", "value": "Name: Alex. Prefers concise answers."},
        {"label": "persona", "value": "I am a helpful travel assistant."},
    ],
)

client.agents.messages.create(
    agent_id=agent.id,
    messages=[{"role": "user", "content": "Remember I'm vegan."}],
)

# State persists on the server; a later call to the same agent_id recalls it.
block = client.agents.blocks.retrieve(agent_id=agent.id, block_label="human")
```

You call the same `agent_id` across sessions — no reconstruction; the server holds state.

## Verify

- **Cross-session recall:** write a fact in one process, exit, start a fresh process, retrieve by the
  same `user_id`/`agent_id` — the fact must come back. This is the whole point; test it explicitly.
- **Scoping:** search with a *different* `user_id` and confirm you get nothing — proves tenant isolation.
- **Supersession (Zep):** add a fact, then a contradicting one; confirm the context block returns the
  new value, not both.
- **Latency budget:** time the retrieve call in your request path; if it dominates, cache the context
  block per turn rather than re-querying mid-generation.

## Pitfalls

- **Assuming "managed" means no LLM key.** Extraction/embedding still costs model calls — a provider
  key and its bill are real. Budget for it.
- **Storing raw transcripts, not facts.** `add` the turns and let the service extract; dumping whole
  histories back in-context defeats the purpose and re-bloats the window.
- **Missing / unstable `user_id`.** Memory keyed on a shifting id silently fragments — one user
  becomes many. Pin a stable identity before writing.
- **Cross-tenant leakage.** A shared or blank scope leaks one user's memory into another's prompt.
  Namespace every call and verify with a negative search.
- **Flat fact lists drift into contradictions.** If facts evolve, a plain vector list (basic Mem0
  usage) accumulates stale + new; reach for graph memory (Zep) or prune on write.
- **PII/compliance.** These stores hold personal data — honour deletion (`delete`/right-to-erasure),
  set retention, and check data residency before putting client data in a third-party cloud.
- **Retrieval in the hot path.** A slow memory query blocks the whole response; measure it and cache.
- **Vendor lock-in.** Graph/block schemas differ across services — wrap memory behind a small
  `remember()` / `recall()` interface so you can swap Mem0 ↔ Zep without touching agent logic.

## Sources

- [Mem0 platform quickstart](https://docs.mem0.ai/platform/quickstart) · [Mem0 OSS](https://docs.mem0.ai/open-source/python-quickstart)
- [Zep quick-start guide](https://help.getzep.com/quick-start-guide) · [Graphiti (getzep/graphiti)](https://github.com/getzep/graphiti)
- [Letta Python SDK](https://docs.letta.com/api/python) · [Letta memory blocks](https://docs.letta.com/guides/agents/memory-blocks/)
