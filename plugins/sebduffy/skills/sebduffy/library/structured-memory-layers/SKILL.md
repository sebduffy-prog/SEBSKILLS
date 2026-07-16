---
name: structured-memory-layers
category: context-engineering
description: >
  Give an agent tiered durable memory that survives across sessions — pick the right tool
  for the need and wire it in. Mem0 (mem0ai) is the lightweight bolt-on that auto-extracts
  facts and semantically retrieves them; Letta (ex-MemGPT) is the OS-style memory hierarchy
  with in-context core blocks, recall, archival vector store, self-editing memory tools, and
  sleep-time consolidation; Zep/Graphiti is a bi-temporal knowledge graph that tracks how
  facts change over time. Use when asked to add long-term memory, persistent memory, an
  agent that "remembers" users across chats, self-editing memory, memory consolidation, a
  temporal/graph memory store, or to choose between Mem0 vs Letta vs Zep/Graphiti.
when_to_use:
  - "Make an agent remember a user's facts/preferences across separate sessions"
  - "Add long-term / persistent memory to a chatbot or agent that currently forgets everything"
  - "Give an agent core (always-in-context) + recall + archival memory tiers, MemGPT-style"
  - "Let the agent self-edit its own memory (append/replace facts) and consolidate during idle time"
  - "Track how facts change over time with valid/invalid windows (temporal knowledge graph)"
  - "Decide between Mem0, Letta, and Zep/Graphiti for an agent-memory feature"
when_not_to_use:
  - "Just compacting/summarising a single long conversation transcript → use agent-context-compaction"
  - "Budgeting tokens across a fixed context window → use context-window-budgeter"
  - "A plain markdown scratchpad/notes file the agent reads each run → use agent-memory-file"
  - "Isolating context between subagents → use subagent-context-isolation"
  - "Measuring retrieval/context quality → use context-quality-evals"
  - "Retrieving documents (RAG over a corpus) rather than per-user facts → use a rag/* skill"
keywords: [agent memory, long-term memory, persistent memory, mem0, mem0ai, letta, memgpt, zep, graphiti, temporal knowledge graph, core memory, archival memory, recall memory, sleep-time compute, memory consolidation, self-editing memory, memory blocks, cross-session memory, vector memory, bi-temporal, remembers user]
similar_to: [agent-memory-file, agent-context-compaction, context-window-budgeter, subagent-context-isolation, context-quality-evals, prompt-compression]
inputs_needed:
  - "Which need: cheap semantic fact recall (Mem0), OS-style self-editing hierarchy (Letta), or temporal graph of changing facts (Zep/Graphiti)"
  - "LLM + embedding provider and API key (OPENAI_API_KEY / ANTHROPIC_API_KEY); Graphiti needs a graph DB (Neo4j 5.26+ or FalkorDB)"
  - "A stable user_id / agent_id to scope memories per user"
  - "Where memories live: managed cloud vs self-hosted vector/graph store"
produces: Working per-user tiered memory wired into an agent — add/search/consolidate calls plus a chosen backend (Mem0, Letta, or Graphiti)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Structured Memory Layers

Durable, tiered memory so an agent recalls facts across sessions instead of starting cold every turn. Three battle-tested engines, each a different point on the cost/power curve. **Pick one — do not stack all three.**

## When to use

Reach for this when "the agent should remember the user next time." First decide *which* engine:

| Need | Use | Why |
|------|-----|-----|
| Cheap, drop-in semantic fact recall over messages | **Mem0** | One `add()`/`search()` pair; auto-extracts + dedupes facts |
| OS-style hierarchy: always-in-context core blocks + overflow to archival, agent edits its own memory, idle-time consolidation | **Letta** (ex-MemGPT) | Stateful server + self-editing memory tools + sleep-time agents |
| "What was true *when*" — facts with validity windows that change over time | **Zep / Graphiti** | Bi-temporal knowledge graph, full provenance to source episodes |

## Prerequisites

- Python 3.10+ (or Node for Letta CLI/SDK).
- An LLM + embedding provider. All three default to OpenAI (`OPENAI_API_KEY`); each supports Anthropic/others via config.
- **Mem0:** `pip install mem0ai`. Optional local vector store (Qdrant/Chroma) or managed [Mem0 Platform](https://app.mem0.ai) key.
- **Letta:** self-host the server (Docker) or use Letta Cloud (`LETTA_API_KEY`). SDKs: `pip install letta-client` (Python) / `npm i @letta-ai/letta-client`.
- **Graphiti:** `pip install graphiti-core` **plus a graph DB** — Neo4j 5.26+ (`bolt://localhost:7687`) or `pip install graphiti-core[falkordb]`. Uses `asyncio` (all methods are `await`).

Honesty check: Mem0 is the only truly "just pip install" option. Letta wants a running server; Graphiti wants a graph database. Don't promise cross-session memory without standing up the backend.

## Recipe A — Mem0: lightweight semantic memory

```python
from mem0 import Memory

memory = Memory()  # reads OPENAI_API_KEY; defaults to a local vector store

# 1. Ingest a turn — Mem0's LLM extracts salient facts, dedupes, and stores them
memory.add(
    [{"role": "user", "content": "I'm vegetarian and allergic to peanuts"}],
    user_id="alice",
)

# 2. Later session: retrieve only what's relevant to the current query
hits = memory.search(query="what can Alice eat?", user_id="alice", limit=5)
context = "\n".join(f"- {m['memory']}" for m in hits["results"])

# 3. Inject `context` into your system prompt before calling the LLM
```

Config for a custom LLM / self-hosted vector store (dict passed to `Memory.from_config`):

```python
config = {
    "llm": {"provider": "anthropic", "config": {"model": "claude-sonnet-4-5"}},
    "vector_store": {"provider": "qdrant", "config": {"host": "localhost", "port": 6333}},
}
memory = Memory.from_config(config)
```

Key methods: `add(messages, user_id=...)`, `search(query=..., user_id=..., limit=...)`, `get_all(user_id=...)`, `update(memory_id, data)`, `delete(memory_id)`. Managed version: `from mem0 import MemoryClient` (needs `MEM0_API_KEY`).

## Recipe B — Letta: OS-style self-editing hierarchy

Letta gives you the MemGPT tiers: **core memory** (labelled blocks like `human`/`persona`, always in context), **recall** (searchable message history), and **archival** (external vector store for overflow). The agent calls its own memory tools — `core_memory_append`, `core_memory_replace`, `archival_memory_insert`, `archival_memory_search` — to edit what it knows. **Sleep-time agents** run in the background during idle periods to reorganise and consolidate memory.

```bash
# Self-host the server
docker run -p 8283:8283 letta/letta:latest
# or the interactive CLI:  npm install -g @letta-ai/letta-code && letta
```

```python
from letta_client import Letta

client = Letta(base_url="http://localhost:8283")  # or Letta(token=LETTA_API_KEY) for cloud

agent = client.agents.create(
    model="openai/gpt-4.1",
    embedding="openai/text-embedding-3-small",
    memory_blocks=[
        {"label": "human",   "value": "Name: Alice. Vegetarian, peanut allergy."},
        {"label": "persona", "value": "You are a helpful nutrition assistant."},
    ],
)

# The agent self-edits core/archival memory as the conversation proceeds
resp = client.agents.messages.create(
    agent_id=agent.id,
    messages=[{"role": "user", "content": "Remember I also gave up dairy this week."}],
)
# Inspect what it chose to persist:
print(client.agents.blocks.retrieve(agent_id=agent.id, block_label="human").value)
```

State lives server-side keyed by `agent_id`, so the *next* session with the same agent already has the memory loaded — no manual re-injection.

## Recipe C — Zep / Graphiti: temporal knowledge graph

Use when facts change and you need "what was true when." Graphiti ingests **episodes** (raw text/JSON), an LLM extracts entities + relationships, and each edge carries a **valid/invalid time window** — old facts are invalidated, never deleted (bi-temporal), with provenance back to the source episode.

```python
import asyncio
from datetime import datetime, timezone
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

async def main():
    graphiti = Graphiti("bolt://localhost:7687", "neo4j", "password")  # needs OPENAI_API_KEY
    await graphiti.build_indices_and_constraints()  # one-time setup

    await graphiti.add_episode(
        name="prefs-update",
        episode_body="Alice switched from Nike to Adidas running shoes.",
        source=EpisodeType.text,
        source_description="chat message",
        reference_time=datetime.now(timezone.utc),
        group_id="alice",   # scope the subgraph per user
    )

    results = await graphiti.search(query="what shoes does Alice wear?", group_id="alice")
    for edge in results:
        print(edge.fact, edge.valid_at, edge.invalid_at)

    await graphiti.close()

asyncio.run(main())
```

`add_episode` runs an async LLM extraction pipeline (slow-ish, rate-limited by `SEMAPHORE_LIMIT`, default 10). Set `GRAPHITI_TELEMETRY_ENABLED=false` to disable usage telemetry. Zep is the managed hosted product built on Graphiti if you don't want to run Neo4j.

## Verify

- **Mem0:** `add()` a fact, start a fresh process, `search()` for it — the fact comes back scoped to the right `user_id` and NOT for a different one.
- **Letta:** create the agent, send a "remember X" message, then in a new client call `blocks.retrieve` — X is present without you re-sending it.
- **Graphiti:** add two contradicting episodes over time; `search` returns the newer fact and the superseded edge shows a non-null `invalid_at`.
- Cross-cutting: confirm memory is **scoped** (user A never sees user B's memories) and **survives a process restart**.

## Pitfalls

- **Don't stack engines.** One memory system per agent. Mem0 *or* Letta *or* Graphiti — mixing them duplicates facts and confuses retrieval.
- **This is not RAG.** These store per-user/agent *facts*, not a document corpus. For document search use a `rag/*` skill.
- **Retrieval cost = latency + tokens.** `search` calls hit an LLM/embeddings; cache within a turn and cap `limit`/`top_k`. Inject only the top few memories, not everything (`get_all` is for debugging, not prompt-stuffing).
- **Scope every call.** A missing/wrong `user_id` (Mem0), `agent_id` (Letta), or `group_id` (Graphiti) leaks or loses memory. Treat these as required inputs.
- **Graphiti extraction is slow and LLM-bound.** Batch episodes; don't `add_episode` on the hot path of every keystroke. Watch rate limits via `SEMAPHORE_LIMIT`.
- **Letta legacy vs current.** The original `letta` PyPI server package is legacy; current path is the Docker server + `letta-client` SDK (or Letta Cloud). Check the exact client version's method names before shipping.
- **Fabricated memories.** The LLM extractor can hallucinate a "fact." For high-stakes data, prefer explicit writes (structured `add`) over inferring from freeform chat, and let the user correct/delete.
- **Privacy/PII.** Durable memory persists personal data. Support deletion (`delete`, group teardown) and scope retention per your data policy before turning it on.
