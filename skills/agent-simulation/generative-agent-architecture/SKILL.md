---
name: generative-agent-architecture
category: agent-simulation
description: >
  Give an LLM agent believable long-run behaviour with Stanford's "Generative
  Agents" (Smallville) cognitive loop: a memory stream retrieved by
  recency + importance + relevance, LLM-rated importance (poignancy), periodic
  reflection into higher-level insights, and top-down daily planning that
  decomposes into hourly then minute-level actions. Use when someone says "build
  a believable agent", "give my NPC memory", "Stanford generative agents",
  "Smallville simulation", "agents that remember and reflect", "memory stream
  retrieval", "reflection + planning loop", or "why does my agent have no
  long-term memory / consistency". Produces a runnable memory-stream + reflection
  + planning scaffold you drop onto any chat model.
when_to_use:
  - "You want an agent that remembers past events and acts consistently over many turns/days, not just within one context window"
  - "You're building NPCs / social simulacra and need the Smallville memory-stream + reflection + planning architecture"
  - "Your agent 'forgets' or contradicts itself and you need retrieval scored by recency, importance and relevance (not just vector similarity)"
  - "You need to implement importance/poignancy rating and reflection-into-insights on top of an LLM"
  - "You want top-down day → hour → minute planning that survives interruptions and reactions"
when_not_to_use:
  - "You want many agents posting on a simulated social network / feed dynamics → use oasis-social-media-simulation"
  - "You want city-scale mobility, economy or urban-policy simulation of populations → use agentsociety-urban-experiment"
  - "You just need document retrieval for a Q&A/RAG app (no agent, no time, no reflection) → use a standard rag skill"
  - "You need a general tool-using agent framework (routing, tool calls, orchestration) → use a building-agents / agent-frameworks skill"
keywords: [generative agents, smallville, memory stream, reverie, reflection, poignancy, importance rating, recency relevance importance, retrieval scoring, believable agents, simulacra, joonspk, park et al, agent memory, cognitive architecture, planning decomposition, npc memory, agent-based simulation]
similar_to: [oasis-social-media-simulation, agentsociety-urban-experiment]
inputs_needed:
  - "Which LLM + embedding model you'll use (any chat model + any embedder)"
  - "How many agents and how long a sim (one agent for a day vs. a village over weeks) — drives storage choice"
  - "Whether you want the full Reverie/Django reference sim, or just the cognitive loop wired into your own app"
  - "Persona seed(s): name, traits, background, daily rhythm"
produces: A runnable memory-stream + reflection + planning scaffold (scripts/memory_stream.py) plus the prompts/thresholds to drive believable agent behaviour on any chat model.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Generative Agent Architecture (Stanford "Smallville")

Reproduce the cognitive loop from Park et al., *Generative Agents: Interactive
Simulacra of Human Behavior* (UIST '23) — the thing that makes 25 agents throw a
Valentine's party without being told to. Three parts on top of any LLM:

1. **Memory stream** — an append-only log of observations, retrieved by a
   weighted blend of **recency + importance + relevance** (not plain cosine).
2. **Reflection** — periodically the agent asks itself high-level questions and
   synthesises answers *back into the stream* as new, higher-poignancy memories.
3. **Planning** — a top-down day plan decomposed to hourly then ~5–15-min
   actions, revised when the agent observes something worth reacting to.

Source: `joonspk-research/generative_agents` (Apache-2.0). This skill ports the
scoring math faithfully; see `scripts/memory_stream.py` for a zero-dependency,
smoke-tested implementation.

## When to use

- You need an agent consistent across days/weeks, beyond one context window.
- You're building believable NPCs / social simulacra.
- Plain vector RAG isn't enough — you need time-decay and self-rated importance.

## Prerequisites

Two ways to run it:

**A. Port the loop into your own app (recommended for most).** No install beyond
your LLM SDK + an embedder. `scripts/memory_stream.py` has *no* third-party deps
(embeddings are injected). Wire it to your model:

```bash
python3 -m pip install --user anthropic          # or openai / sentence-transformers
export ANTHROPIC_API_KEY=...                      # your chat + rating model
python3 scripts/memory_stream.py                  # smoke-test the retrieval math
```

**B. Run the original Reverie reference simulation (the Smallville village +
web frontend).** Heavier; good for studying the full system.

```bash
git clone https://github.com/joonspk-research/generative_agents
cd generative_agents
python3 -m pip install --user -r requirements.txt   # Python 3.9.12 in the paper
# Two servers, two terminals:
#   environment/frontend_server  → python manage.py runserver   (Django UI + map)
#   reverie/backend_server       → python reverie.py            (the sim brain)
# Put your OpenAI key in reverie/backend_server/utils.py; then `run <steps>` in the
# backend REPL and open http://localhost:8000/simulator_home to watch.
```

Note: the reference sim is pinned to a legacy OpenAI completion API — expect to
patch `gpt_structure.py` for a current model. For new work, prefer path A.

## Recipes

### 1. Score & retrieve memories (the core the paper is famous for)

Each memory node stores `description`, `embedding`, `importance` (1–10),
`created`, `last_accessed`. Retrieval min-max-normalises **each** of the three
components to [0,1], then takes a weighted sum:

```
recency[i]   = RECENCY_DECAY ** rank_by_last_accessed(i)     # 0.995 ** rank
importance[i]= node.importance                               # LLM poignancy 1-10
relevance[i] = cosine(query_embedding, node.embedding)

score[i] = 0.5*norm(recency)[i] + 3*norm(importance)[i] + 2*norm(relevance)[i]
```

The `[0.5, 3, 2]` weights (recency, importance, relevance) and `0.995` decay are
the repo defaults; in Reverie they live per-agent in `persona.scratch` so you can
tune curiosity vs. habit per character. Use it:

```python
from datetime import datetime
from scripts.memory_stream import MemoryStream, MemoryNode

ms = MemoryStream()
now = datetime.now()
ms.add(MemoryNode("Isabella is planning a Valentine's party", embed("..."), 8, now, now))
# retrieval refreshes last_accessed on the winners (recency is *access* recency)
for i, node, s in ms.retrieve(embed("What should I do about Feb 14?"), now, top_k=5):
    print(round(s, 2), node.description)
```

Feed the top-k descriptions into the model's context — that's the agent's working
memory for the current decision.

### 2. Rate importance (poignancy) at write time

Every observation gets a 1–10 importance score from the LLM as it's stored.
Mundane = low, life-relevant = high. Keep the prompt near-verbatim from the paper:

```
On the scale of 1 to 10, where 1 is purely mundane (e.g., brushing teeth, making
bed) and 10 is extremely poignant (e.g., a break up, college acceptance), rate
the likely poignancy of the following piece of memory.
Memory: {description}
Rating: <fill in a single integer>
```

Parse the integer, store it as `importance`. This score is what lets a
break-up outrank ten "made coffee"s at retrieval time.

### 3. Reflect when pressure builds

Track **reflection pressure** = sum of importance over recent events. When it
crosses a threshold (the paper uses ~150), run a reflection cycle:

```python
if ms.reflection_pressure(window=100) > 150:
    # a) Ask the model for the 3 most salient high-level questions given the
    #    N most recent memories.
    # b) For each question, retrieve() relevant memories, then prompt:
    #    "What 5 high-level insights can you infer? (example format:
    #     insight (because of 1, 5, 3))" — capture the cited node ids as evidence.
    # c) Store each insight as a NEW MemoryNode(kind="reflection") with its own
    #    LLM-rated importance and an `evidence` list pointing at source nodes.
```

Reflections are memories too, so they get retrieved *and* reflected upon later —
that's how agents form beliefs ("I really enjoy my research") rather than just
recalling facts. Reset/decay the pressure counter after reflecting.

### 4. Plan top-down, react bottom-up

- **Day plan:** prompt with the persona summary + yesterday's plan → a rough
  daily agenda (~5–8 broad chunks). Store it as a plan memory.
- **Decompose:** expand the current chunk into hourly, then the current hour into
  ~5–15-min actions, only as far ahead as needed (lazy decomposition).
- **React:** on each perceived event, retrieve context and ask the model "should
  {agent} react, and if so how?" If yes, regenerate the plan *from now onward*
  (keep the morning, rewrite the afternoon). This is what produces emergent
  coordination — one agent's party invite reshapes another's plan.

## Verify

```bash
python3 scripts/memory_stream.py
# Expect the Valentine's-party memory to rank #1 for a party-themed query,
# above the low-importance "out of coffee beans" node.
```

Behavioural checks that the loop actually works:

- Ask the agent an interview question ("What are you looking forward to?"); the
  answer should cite specifics only retrievable from the stream.
- Plant a high-importance event; confirm it surfaces in retrieval for days while
  low-importance noise decays out.
- Confirm reflections appear as new nodes with `evidence` ids and get retrieved
  later.

## Pitfalls

- **Don't collapse retrieval to cosine similarity.** The whole contribution is
  recency + importance *on top of* relevance. Drop recency and the agent has no
  sense of "recent"; drop importance and trivia drowns out life events.
- **Normalise per component, then weight.** Min-max each of the three to [0,1]
  *before* the weighted sum, exactly as `_minmax` does. Weighting raw cosine
  (≈0–1) against importance (1–10) and decay (≈1.0) without normalising makes
  importance dominate everything.
- **Recency is *access* recency.** `last_accessed` updates when a memory is
  retrieved, not just when created — recall reinforces. The scaffold does this;
  keep it.
- **Reflection is not summarisation.** It must produce *inferences with cited
  evidence* and write them back as first-class memories, or agents never form
  higher-level beliefs and stay reactive.
- **Cost scales fast.** Importance-rating every observation + embeddings + reflect
  + plan is many calls per agent per step. Batch importance ratings, cache
  embeddings, use a cheap model for rating/decomposition, and raise the reflection
  threshold to throttle. A full-village multi-day Reverie run is genuinely
  expensive — prototype with one agent for one day first.
- **The reference repo is pinned to a legacy OpenAI API.** `gpt_structure.py`
  targets old completion endpoints; you'll patch it for any current model. Path A
  (port the loop) sidesteps this entirely.
- **This is single-world simulacra, not a product agent framework.** For social-
  feed dynamics use oasis-social-media-simulation; for city/economy scale use
  agentsociety-urban-experiment.
