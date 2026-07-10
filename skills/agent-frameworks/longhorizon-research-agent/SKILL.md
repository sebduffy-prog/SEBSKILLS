---
name: longhorizon-research-agent
category: agent-frameworks
description: >
  Build a DeerFlow-style long-horizon "super-agent" harness that takes a deep multi-step
  brief and runs it to a finished deliverable — a lead orchestrator that PLANs, FANS OUT
  parallel research subagents (composing deep-research + firecrawl-scrape + connect-public-api),
  DEDUPES and synthesizes findings into a durable working-memory run directory
  (structured-memory-layers on disk), then BUILDS the artifact (data-driven-deck-generator or
  docx) and VERIFIES every claim (claim-verifier). Sandboxed, resumable-from-disk, and
  budget-capped. Use when asked to build a research super-agent, an autonomous "give it a brief,
  get a report/deck" harness, a long-running multi-source agent, a fan-out+synthesize pipeline,
  or a DeerFlow / deep-research-agent clone.
when_to_use:
  - "Turn a deep, open-ended brief into a finished cited report or deck without babysitting each step"
  - "Fan research out across many sources/subtopics in parallel, then merge into one synthesis"
  - "Run a long-horizon task (minutes to hours) that must survive crashes and resume from disk"
  - "Cap spend/tool-calls on an autonomous agent so it can't run away"
  - "Chain research → synthesis → build-deliverable → verify as one auditable pipeline"
  - "Clone DeerFlow / a deep-research super-agent as a Claude Code orchestration recipe"
when_not_to_use:
  - "Single-shot cited web research with no build step → use deep-research directly"
  - "Just scraping one site/domain → use firecrawl-scrape"
  - "Durable graph execution inside one framework → use langgraph-durable-workflows"
  - "Only fact-checking existing text → use claim-verifier"
  - "Generic routing/handoff topology with no research/build phases → use agent-orchestration-patterns"
keywords: [deerflow, super agent, long horizon, orchestrator, fan out, parallel subagents, working memory, resumable, budget cap, sandbox, research pipeline, synthesis, deep research, deliverable, claim verification, lead agent]
similar_to: [agent-orchestration-patterns, langgraph-durable-workflows, handoff-router-swarm, crewai-flows-orchestration]
inputs_needed:
  - "The brief: research question + required deliverable (report.docx | deck.pptx) + audience"
  - "Budget caps: max subagents, max tool-calls/subagent, wall-clock ceiling"
  - "Source config: web (firecrawl/exa keys), any private APIs (connect-public-api endpoints/keys)"
  - "A writable run directory for working memory (resumable state)"
produces: A resumable run directory (plan.json, memory/, findings/, verify/) plus the final verified, cited deliverable (docx or pptx) with a provenance log.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Long-Horizon Research Agent (DeerFlow-style super-agent harness)

A **lead orchestrator** that decomposes a brief, spawns **parallel research subagents**, folds
their results into a **durable on-disk working memory**, then **builds and verifies** a
deliverable. Ported in shape from ByteDance **DeerFlow 2.0** (MIT) — "a super-agent harness that
orchestrates sub-agents, memory, and sandboxes" — re-expressed as a Claude Code recipe that
composes existing SEBSKILLS instead of re-implementing each stage.

## When to use

Use for briefs too big for one pass: "map the UK RTD cocktail market, size the segments, and hand
me a 15-slide investor deck with sources." One `deep-research` call answers a question; this harness
runs question → parallel evidence gathering → synthesis → **built artifact** → verification, and can
be killed and resumed because all state lives on disk.

## Prerequisites

- The composed skills present in the library: `deep-research`, `firecrawl-scrape`,
  `connect-public-api`, `structured-memory-layers`, `data-driven-deck-generator` (or `docx`),
  `claim-verifier`.
- Fan-out via the **Task** tool (subagents) — each subagent gets a scoped prompt + its own tool budget.
- Web keys for firecrawl/exa; any private-API creds in env for `connect-public-api`.
- A run directory. Treat it as the sandbox — subagents only read/write inside it.

## Mechanism / Steps

The orchestrator is a loop over a **run directory** that IS the working memory. Never hold findings
only in context — write them to disk so the run is resumable and auditable.

```
runs/<slug>/
  brief.md            # frozen input brief + deliverable spec + audience
  budget.json         # caps + live counters (subagents_spawned, tool_calls, started_at)
  plan.json           # subtopics[] each: {id, question, sources[], status, subagent, findings_path}
  memory/
    core.md           # always-in-context: thesis, key numbers, open questions (structured-memory-layers L1)
    facts.jsonl       # one dedup'd claim per line {id, text, value, source_url, subtopic, confidence}
  findings/<id>.md    # raw per-subagent output (recall layer)
  verify/report.json  # claim-verifier verdicts
  deliverable.(pptx|docx)
  provenance.md       # fact_id -> source_url -> slide/section map
```

**0. Freeze & budget.** Write `brief.md`. Write `budget.json`, e.g.
`{"max_subagents":8,"max_tool_calls_per_sub":15,"wall_clock_min":45,"tool_calls":0,"subagents_spawned":0}`.
Before every spawn/tool step, check the counters; when a cap is hit, stop fanning out and move to
synthesis with what you have (graceful degrade, never overrun).

**1. Plan (decompose).** The lead writes `plan.json`: 3–8 subtopics, each a self-contained question
with a source hint (`web`, `firecrawl:<domain>`, or `api:<name>`) and `status:"pending"`. This is the
DeerFlow "lead breaks the task into sub-tasks, each sub-agent gets isolated context" step. If the
brief is underspecified, ask the user 2–3 scoping questions here — do not fan out on a vague brief.

**2. Fan out (parallel subagents).** For each `pending` subtopic, spawn a Task subagent **in
parallel** (dispatch them in one batch). Each subagent's scoped prompt:
- `web` → invoke **deep-research** on the subtopic question.
- `firecrawl:<domain>` → invoke **firecrawl-scrape** to crawl/extract that source.
- `api:<name>` → invoke **connect-public-api** to pull structured data.
Each subagent must (a) honour `max_tool_calls_per_sub`, (b) write raw output to
`findings/<id>.md`, (c) append normalized claims to `memory/facts.jsonl` with `source_url` +
`confidence`, (d) set its subtopic `status:"done"`. Subagents return a short structured summary only
— the bulk stays on disk (context offloading). Increment counters after each returns.

**3. Dedup & synthesize (working memory).** Fold `facts.jsonl` per **structured-memory-layers**:
dedup near-identical claims (keep highest-confidence, union the `source_url`s), flag contradictions as
`open questions`, and distil the thesis + load-bearing numbers into `memory/core.md` (the L1 layer
that stays in context while building). `scripts/fold_memory.py` does the mechanical dedup pass.

**4. Build the deliverable.** With `core.md` + deduped `facts.jsonl` as the ONLY inputs (so every
line traces to a source), invoke **data-driven-deck-generator** for a deck or **docx** for a report.
Write `provenance.md` mapping each fact_id to its slide/section and source_url.

**5. Verify (adversarial gate).** Run **claim-verifier** over the finished deliverable against
`facts.jsonl` → `verify/report.json`. Any claim that is unsupported or lacks a `source_url` is a
**blocker**: fix the deliverable (or spawn one more targeted subagent if budget remains) and re-verify.
Only ship when zero blockers remain.

**Resume.** On restart, re-read `budget.json` + `plan.json`: skip `done` subtopics, re-spawn only
`pending`/`failed` ones, and continue from the earliest incomplete phase. Disk is the source of truth.

## Verify

- **Resumability:** kill the run mid-fan-out, restart — it must skip completed subtopics, not redo them.
- **Budget hold:** set `max_subagents:2` on a 6-subtopic plan; confirm it stops at 2 and still produces
  a (partial, honestly-scoped) deliverable rather than overrunning.
- **Provenance:** every number in the deliverable resolves through `provenance.md` to a `source_url`.
- **Verification gate:** plant an unsupported claim; `claim-verifier` must flag it and block the ship.
- **Smoke:** `python3 scripts/fold_memory.py runs/<slug>/memory/facts.jsonl` prints deduped count and
  contradiction list without error.

## Pitfalls

- **Findings only in context, not on disk** → run isn't resumable and blows the context window. Always
  offload to `findings/` + `facts.jsonl`.
- **Serial fan-out.** Dispatch step-2 subagents in a single parallel batch; sequential defeats the
  whole point of a long-horizon harness.
- **No budget check before spawn** → an autonomous agent that runs away. Gate every spawn/tool call.
- **Vague brief, eager fan-out.** A fuzzy question wastes the whole budget on the wrong subtopics —
  scope first (step 1).
- **Building from raw findings** instead of the deduped/synthesized memory → duplicated, contradictory
  slides. Build only from `core.md` + deduped `facts.jsonl`.
- **Skipping verification** because "the sources looked fine." The `claim-verifier` gate is what makes
  the output trustable; treat unsupported claims as blockers, not warnings.
- **Subagents writing outside the run dir.** Keep the run directory the sandbox boundary; a subagent
  touching the wider filesystem breaks isolation and reproducibility.
