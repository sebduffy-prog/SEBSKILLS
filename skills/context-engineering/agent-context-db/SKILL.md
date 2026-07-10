---
name: agent-context-db
category: context-engineering
description: >
  Give a project agent ONE self-evolving "context database" that unifies episodic memory
  (what happened), semantic RAG (docs/knowledge) and skills (how-to) behind a single store
  that updates itself as the agent works — so it accumulates brand/client/project knowledge
  across sessions instead of re-learning cold every time. Ports OpenViking (volcengine): a
  viking:// virtual filesystem with L0/L1/L2 layered loading, a recall-before-prompt + capture-
  after-task loop, and an MCP server. Use when asked for a "context database", "self-updating
  memory", "agent that gets smarter with use", "unify memory + RAG + skills", or a Claude Code
  long-term memory plugin. Lighter managed alt: Mem0.
when_to_use:
  - One agent needs memory AND document-RAG AND reusable skills behind a single retrievable store
  - The agent should accumulate client/brand/project knowledge over months, not re-learn each session
  - You want automatic capture (write on every task) plus ranked recall injected before each prompt
  - Wiring OpenViking's Claude Code memory plugin (hooks + MCP) or its server for a custom agent
  - You need layered/hierarchical loading (summaries by default, full detail on demand) to save tokens
when_not_to_use:
  - Only per-user fact recall, no RAG/skills, cheapest possible — use structured-memory-layers (Mem0/Letta/Zep)
  - A plain markdown scratchpad the agent reads each run — use agent-memory-file (CLAUDE.md/NOTES.md)
  - A knowledge layer SHARED across many agents/teams — use federated-knowledge-memory
  - Just deciding memory tiers/precedence conceptually — use structured-memory-layers
  - Compacting one overflowing transcript in place — use agent-context-compaction
keywords: [context database, self-evolving memory, openviking, viking filesystem, agent memory, semantic rag, skill memory, procedural memory, recall before prompt, capture after task, l0 l1 l2 layered loading, mcp memory server, claude code memory plugin, mem0, cross-session knowledge, hierarchical retrieval, brand memory, self-updating store]
similar_to: [structured-memory-layers, agent-memory-file, federated-knowledge-memory, agent-context-compaction, context-window-budgeter, context-quality-evals]
inputs_needed:
  - Runtime — Claude Code (use the OpenViking memory plugin) vs a custom agent (call the OpenViking MCP/CLI directly)
  - An OpenViking server (self-host on localhost:1933, or a remote URL + api_key) and an embedding + VLM provider config
  - Stable account/user identifiers to scope the store (viking://user/{user_id}/...)
  - The seed corpus to ingest as resources (repo URLs, docs, brand guidelines) plus what counts as a "skill"
produces: A single self-updating context store wired to the agent — auto-recall before prompts, auto-capture after tasks, layered retrieval over unified memory + RAG + skills
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Agent Context DB

One store, three needs, self-updating. Instead of bolting a memory library, a vector RAG index,
and a skills folder onto an agent as three disconnected systems, front all three with a single
**context database** that (a) captures what happened after every task, (b) holds ingested
knowledge as RAG, (c) stores reusable how-to skills — and (d) updates itself as the agent works.
This ports **OpenViking** (volcengine, AGPLv3 core), whose model is a `viking://` virtual
filesystem: memory, resources and skills are all just files, retrieved by a recursive
directory search, and delivered as layered summaries (L0/L1/L2) so you spend tokens only when
detail is actually needed.

## When to use

Reach for this when the ask is "the agent should get smarter about this client/brand/project the
more we work" — and that requires *three* memory kinds unified, not one:

| Need | In the store | Written by |
|------|-------------|-----------|
| Episodic — what happened, decisions, feedback, tips | `viking://user/{id}/memories/`, `viking://agent/` | auto-capture loop after each task |
| Semantic RAG — docs, repos, brand guidelines, web pages | `viking://resources/`, `viking://user/{id}/resources/` | explicit ingest (`add-resource`) |
| Procedural — reusable skills / tool recipes | `viking://user/{id}/skills/` | authored or extracted from successful runs |

If you only need one of these, stop and use the narrower sibling (see `when_not_to_use`). The
value here is the **unification + the self-update loop**, not any single tier.

## Prerequisites

- **Python 3.9+** and `pip install openviking --upgrade`. Optional Rust CLI: `npm i -g @openviking/cli`.
- An **embedding provider + a VLM** (vision-language model for parsing docs/images) configured in
  `~/.openviking/ov.conf` — set via `openviking-server init` (interactive) then `openviking-server doctor`.
- A running server: `openviking-server` (default `http://127.0.0.1:1933`; health at `/health`).
- Stable identifiers to scope the store: an `account` (team) and `user` (person/agent).
- The seed corpus to ingest (repo URLs, doc paths, brand PDFs) and a definition of what a "skill" is here.

Managed / lighter alternative: **Mem0** (`pip install mem0ai`, or Mem0 Platform) gives the
auto-extract + semantic-recall half without RAG/skills or a server — see `structured-memory-layers`.

## Mechanism / Steps

### Path A — Claude Code (fastest: the official memory plugin)

This wires the whole loop into Claude Code with hooks + an MCP proxy. Nothing to code.

1. **Start a server** (local or point at a remote one) and confirm health:
   ```bash
   openviking-server                 # or a remote deployment
   curl http://localhost:1933/health
   ```
2. **Configure the connection** in `~/.openviking/ovcli.conf`:
   ```json
   { "url": "http://127.0.0.1:1933", "api_key": "<key>", "account": "vccp", "user": "seb" }
   ```
3. **Install the plugin** from the OpenViking marketplace:
   ```bash
   claude plugin marketplace add https://raw.githubusercontent.com/volcengine/OpenViking/main/.claude-plugin/marketplace.json
   claude plugin install openviking-memory@openviking
   ```
   (Or the one-shot installer: `bash <(curl -fsSL https://raw.githubusercontent.com/volcengine/OpenViking/main/examples/memory-plugin-shared/install.sh) --harness claude`.)
4. **What it registers** (verify in `~/.claude/settings.json`):
   - `UserPromptSubmit` hook → searches the store, ranks, injects hits as `<openviking-context>` blocks (**recall**).
   - `Stop` hook → parses the transcript, pushes new turns to the session, commits when a token threshold is crossed (**capture**).
   - `SessionStart` / `SessionEnd` / `PreCompact` → archival + resume.
   - A stdio **MCP proxy** (`mcp-proxy.mjs`) exposing 9 tools: `search, read, store, add_resource, grep, glob, forget, list, health`.
5. **Tune via env** (override config): `OPENVIKING_RECALL_LIMIT=6` (max memories/turn),
   `OPENVIKING_AUTO_RECALL=true`, `OPENVIKING_AUTO_CAPTURE=true`. Skip a throwaway session with
   `OPENVIKING_BYPASS_SESSION=1 claude`.

### Path B — a custom agent (call the store directly)

Seed the RAG tier, then let the loop maintain the memory + skill tiers.

1. **Ingest the seed corpus** (semantic RAG):
   ```bash
   ov add-resource https://github.com/your-org/brand-guidelines --wait
   ov add-resource ~/clients/agbarr/tone-of-voice.pdf --wait
   ov ls   viking://resources/
   ov tree viking://user/seb/ -L 2
   ```
2. **Retrieve as ranked, layered context** — L0/L1 summaries by default, L2 full detail on demand:
   ```bash
   ov find "irn-bru tone of voice rules"      # semantic, recursive directory search
   ov grep "challenger"  --uri viking://resources/
   ```
   Programmatically, connect the agent to the **MCP server** (`/mcp` endpoint) and use `search` →
   `read` (read pulls L2 only for the node you chose), so a broad query costs summary tokens, not the corpus.
3. **Self-update loop** — at session end, trigger memory extraction: the server asynchronously
   analyses the run and writes back to `viking://user/{id}/memories/` (preferences) and
   `viking://agent/` (experiences/tips). With the bot extras this is automatic:
   ```bash
   pip install "openviking[bot]"
   openviking-server --with-bot        # ov chat drives the extract-on-finish loop
   ```
4. **Author skills** as files under `viking://user/{id}/skills/` (a tool recipe / how-to), or let a
   successful run be promoted to a skill. They retrieve through the same `find`/`search` path.

### The two things that make it a "database", not a folder

- **Layered loading (L0/L1/L2).** Every node auto-generates a one-line **L0 abstract** (~100 tok),
  an **L1 overview** (~2k tok, stored as `.abstract`/`.overview` files), and keeps **L2** full
  content for on-demand load. Retrieval returns L0/L1; you only pay L2 for what you open — the
  reported token saving is up to ~96% vs pasting corpora.
- **Directory recursive retrieval.** Not flat top-k vector search: intent analysis → vector-position
  the high-scoring directories → drill into subdirectories. This keeps related context together
  (a whole client folder), which flat RAG loses.

### Pairs with

- `federated-knowledge-memory` — when the RAG/skill tier must be **shared** across many agents/teams
  (one org-wide store), point this agent's `viking://resources/` at that shared layer.
- `structured-memory-layers` — the conceptual tier model (core / recall / archival) behind the store;
  choose Mem0/Letta/Zep if you do NOT need RAG+skills unified.
- `context-window-budgeter` — set `OPENVIKING_RECALL_LIMIT` from a real per-turn token budget.

## Verify

- `openviking-server doctor` reports OK; `curl localhost:1933/health` returns healthy.
- After `add-resource`, `ov find "<known fact>"` returns the node ranked #1 with an L1 overview, and
  `ov read <uri>` pulls the full L2 body.
- **Recall works:** in a fresh Claude Code session, ask about a fact only in the store — the reply
  cites an injected `<openviking-context>` block (confirm the `UserPromptSubmit` hook fired).
- **Capture works:** state a new preference, end the session, start a new one, ask it back — it
  persists (it was written to `viking://user/{id}/memories/`). Inspect with `ov tree viking://user/`.
- **Self-update:** run two related tasks a day apart; the second should surface a tip/experience the
  first produced under `viking://agent/`.

## Pitfalls

- **Memory pollution / self-reference loops.** The capture hook must strip injected
  `<openviking-context>` and `<system-reminder>` blocks before pushing turns, or recalled memories
  get re-captured and compound. The plugin does this; a custom capture path MUST replicate it.
- **Don't dump the whole store into context.** The point is layered loading — retrieve L0/L1, open
  L2 only for chosen nodes. Cap with `OPENVIKING_RECALL_LIMIT`; unbounded recall re-creates the
  context bloat you were escaping.
- **Scoping.** Wrong `user`/`account` splits or leaks memory across clients. One store per
  client/brand (or strict `viking://user/{id}` scoping) keeps AGBARR knowledge out of a Warner run.
- **License.** OpenViking core (the main project) is **AGPLv3** — copyleft, so do **NOT** embed it in a
  closed product; only the CLI (`crates/ov_cli`) and `examples/` are **Apache-2.0**. Check per-directory `LICENSE`.
- **Server is stateful infra.** It needs an embedding + VLM provider with quota and must stay up for
  recall/capture. For a zero-infra bolt-on with just fact recall, use Mem0 instead.
- **Capture is async and threshold-based.** Memory is committed only when token thresholds cross /
  the session ends — a crashed session before commit loses that turn. Force flush at natural checkpoints.
- **macOS/py3.9:** `openviking[bot]` may pull heavier deps; if install fails, run the server without
  `--with-bot` and trigger extraction explicitly at session end.
