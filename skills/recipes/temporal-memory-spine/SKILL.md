---
name: temporal-memory-spine
category: recipes
description: >
  Recreate a persistent, self-evolving agent-memory backbone — the Graphiti / OpenViking shape —
  as a COMBO of proven SEBSKILLS. Stand up tiered durable memory that survives sessions
  (structured-memory-layers), fold it into ONE self-updating context store the agent writes on every
  task (agent-context-db), promote hard-won facts into a shared, provenance-tracked, verification-gated
  layer every agent and model reads (federated-knowledge-memory), and keep the whole thing lean under
  a token budget (agent-context-compaction). Use to clone a temporal knowledge-graph memory, a
  "memory that gets smarter with use" spine, or a shared bi-temporal agent-memory service — instead of
  wiring one memory step alone.
when_to_use:
  - "You want a full agent-memory backbone (Graphiti / OpenViking style) that persists, evolves AND is shared, not just one memory step"
  - "An agent should accumulate client/brand/project knowledge over months and never re-learn cold each session"
  - "Multiple agents or model providers must compound ONE common memory, with a trust gate before a fact goes library-wide"
  - "You need bi-temporal + provenance-tracked facts (who/which model/when, valid/invalid windows) that survive across runs"
  - "Long-running agents keep blowing the context window and you need the memory spine to stay lean automatically"
  - "Chain persist → self-evolve → share+verify → compact as one reproducible memory recipe"
when_not_to_use:
  - "You only need per-user fact recall across sessions, cheapest possible → use structured-memory-layers (Mem0/Letta/Zep) directly"
  - "You only need ONE agent's self-updating context store (memory+RAG+skills) → use agent-context-db directly"
  - "You only need the shared, verified, provenance layer for a fleet → use federated-knowledge-memory directly"
  - "You only need to trim/compact a bloated context window → use agent-context-compaction directly"
  - "Single-agent scratch memory for one run → a plain JSON file is enough, skip the whole combo"
keywords: [temporal memory, graphiti, openviking, knowledge graph memory, bi-temporal, agent memory, persistent memory, self-evolving memory, federated memory, provenance, context store, memory spine, compaction, shared memory, recipe, combo]
similar_to: [structured-memory-layers, agent-context-db, federated-knowledge-memory, agent-context-compaction]
inputs_needed:
  - "Scope: which agent(s)/fleet share the spine, and the client/brand/project it accumulates knowledge for"
  - "A durable store choice for the tiers: Mem0 (managed) OR Letta OR Zep/Graphiti (temporal graph) — picked in step 1"
  - "A writable store location: the agent-context-db viking:// root and the federated SQLite store path"
  - "A promotion policy: what makes a CANDIDATE fact TRUSTED (cross-provider quorum / steward sign-off / execution / evidence)"
  - "A compaction threshold (default ~70-85% of the window) and an LLM API key for extraction/summarisation"
produces: A running memory backbone — tiered durable store + one self-evolving viking:// context DB that captures on every task and recalls before every prompt + a shared bi-temporal, provenance-tracked, verification-gated federated layer — all kept under a token budget by compaction. Resumable and inspectable on disk.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Temporal Memory Spine (persistent evolving agent memory, recreated as a combo)

A recipe that recreates a **persistent, self-evolving agent-memory backbone** — the
Graphiti / OpenViking shape — by chaining memory skills that already live in this library.
It gives an agent (or a whole fleet) a memory that persists across sessions, updates itself
as work happens, shares verified truth across models, and stays lean under a token budget.

## What it recreates

The behaviour of **Zep/Graphiti** (a bi-temporal knowledge-graph memory that tracks how facts
change over time) fused with **OpenViking** (volcengine's self-evolving `viking://` context
database with recall-before-prompt + capture-after-task). Those products are hosted memory
services; this recipe reproduces the same backbone locally by stitching sibling skills together,
so you own every tier — persistence, self-evolution, sharing, and provenance — and can inspect
the store on disk.

## Feasibility

**GREEN — fully reproducible locally.** Every link in the chain is a proven SEBSKILLS skill that
runs on this machine. No GPU and no proprietary memory product is required. `federated-knowledge-memory`
ships a stdlib SQLite store adapter you can run today, and `agent-context-db` ports OpenViking's
layered store. The **only** external dependency is an **LLM API key** for the fact-extraction and
compaction-summarisation steps (any capable model) — the same key the underlying memory skills
already use. There is no amber or red step. Honesty note: this reproduces the *tiers, the
capture/recall loop, and the trust+provenance guarantees* — not a hosted graph index. If you pick
Zep/Graphiti as the tier-1 store in step 1, its temporal-graph engine is doing that specific work;
the recipe's job is to wire persistence, self-evolution, sharing and leanness into one spine.

## The combo

Ordered pipeline — each step is an existing skill invoked by name:

1. **structured-memory-layers** — the durable foundation. Picks and stands up the tiered store that
   survives sessions: Mem0 (lightweight auto-extract), Letta (MemGPT-style core/recall/archival), or
   Zep/Graphiti (bi-temporal knowledge graph). This is where "remembers across chats" and, if you
   choose Graphiti, "facts have valid/invalid time windows" actually live.
2. **agent-context-db** — the self-evolving layer on top. Wraps the tiers from step 1 behind ONE
   `viking://` context database that unifies episodic memory + RAG + skills, with L0/L1/L2 layered
   loading, a **recall-before-prompt** injection and a **capture-after-task** write. This is what makes
   the memory *get smarter with use* instead of being a passive store.
3. **federated-knowledge-memory** — the shared, verified layer. Any agent/model writes CANDIDATE
   facts; a verification gate (cross-provider quorum / steward sign-off / execution / evidence)
   promotes them to TRUSTED; every skill reads ranked trusted context. Adds bi-temporal + W3C-PROV
   provenance (who / which model / when / source) so the spine is shared and auditable, not per-agent.
4. **agent-context-compaction** — the leanness governor. Fires at a token threshold (~70-85% of the
   window), writes state to the memory above BEFORE compressing, and replaces old turns with an
   anchored typed summary. Keeps the ever-growing spine from blowing the context window or the bill.

## Prerequisites

- The four sibling skills above, available to `/sebduffy` in this library.
- An LLM API key for fact-extraction (steps 1-2) and summarisation (step 4).
- A tier-1 store decision from step 1 (Mem0 vs Letta vs Zep/Graphiti) — Graphiti if you specifically
  need temporal-graph semantics.
- A writable location: the `agent-context-db` `viking://` root and the `federated-knowledge-memory`
  SQLite store path.
- A promotion policy for the federated gate (what turns CANDIDATE into TRUSTED).
- A compaction threshold and the target context-window size for step 4.

## Run it

1. **Lay the foundation.** Invoke **structured-memory-layers**; choose the tier store for the need
   (Graphiti for temporal facts, Letta for OS-style hierarchy, Mem0 for a light bolt-on) and stand it
   up so facts survive across sessions.
2. **Make it self-evolving.** Invoke **agent-context-db**; mount the step-1 store under a `viking://`
   root, wire the **capture-after-task** write and **recall-before-prompt** injection, and enable
   L0/L1/L2 layered loading so summaries load by default and full detail only on demand.
3. **Share and verify.** Invoke **federated-knowledge-memory**; point contributors' writes at the
   SQLite store as CANDIDATE facts, set the promotion gate, and have skills read the ranked TRUSTED
   context. Provenance and bi-temporal windows attach on every fact.
4. **Keep it lean.** Invoke **agent-context-compaction**; set the token threshold, and on every fire
   flush live state into the spine (steps 2-3) BEFORE summarising, then replace old turns with the
   anchored summary block. The memory keeps the durable facts; the window keeps only the anchor.
5. **Loop.** Each task: recall (2) → work → capture (2) → promote what's durable (3) → compact when
   the window fills (4). Over sessions the spine accumulates, verifies, and stays inspectable on disk.

## Verify

- **Persistence:** start a fresh session with zero context; the agent recalls a fact learned in a
  prior session. If it re-learns cold, step 1/2 wiring is wrong.
- **Self-evolution:** run a task, then confirm a new entry was written by **capture-after-task** and
  that the next prompt's **recall-before-prompt** surfaced it. No write = not evolving.
- **Sharing + trust gate:** write a fact as one model; confirm it lands as CANDIDATE, is NOT read as
  truth until the gate promotes it, then IS read as TRUSTED by a different agent afterwards.
- **Provenance + bi-temporal:** pick a stored fact; confirm it carries who/which-model/when/source and
  a valid-from window (and, on Graphiti, an invalid-from when superseded).
- **Leanness:** run past the compaction threshold; confirm state was flushed to memory BEFORE the
  summary replaced old turns, and that no durable fact was lost in the fold.
- **Resumability:** kill mid-run and restart pointed at the same store; the spine picks up from disk.

## Pitfalls

- **Compacting before flushing.** If step 4 summarises before writing live state into steps 2-3, you
  lose exactly the facts you meant to keep. Always flush to memory BEFORE compressing — the whole
  point of the ordering.
- **Skipping the trust gate.** Letting any model's CANDIDATE fact read as TRUSTED collapses this back
  to unverified per-agent memory. Keep the promotion gate; that shared+verified layer is the
  differentiator versus a single-agent store.
- **Losing provenance in the self-evolve write.** If `agent-context-db` captures facts without their
  source/model/time, `federated-knowledge-memory` can't do bi-temporal or conflict-preserving reads.
  Keep attribution on every captured fact.
- **Using all four when one would do.** If you only need per-user recall, or only compaction, invoke
  that single skill — this combo is for when you genuinely need persist + evolve + share + lean.
- **Overselling it as a hosted graph service.** This reproduces the tiers and guarantees, not a
  proprietary hosted index. If you need true temporal-graph semantics, that work lives in the
  Zep/Graphiti store you chose in step 1 — say so to the user.
- **No compaction threshold.** An ever-growing spine with no leanness governor will blow the window
  and the bill. Always set the step-4 threshold; the spine is designed to grow, so it MUST be capped.
