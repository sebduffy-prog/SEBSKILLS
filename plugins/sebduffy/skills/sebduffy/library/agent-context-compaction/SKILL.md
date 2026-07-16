---
name: agent-context-compaction
category: context-engineering
description: >
  Keep long-running / multi-turn agents cheap AND sharp by compacting context
  before the window fills. Fire compaction at a token threshold (default ~70-85%
  of the window), write state to external memory BEFORE compressing, replace old
  turns with an anchored typed summary block, and offload heavy work to sub-agents.
  Use when an agent loops for many turns, tool outputs bloat context, cost/latency
  climb, quality "rots" late in a session, or you see "context window full" /
  auto-compact behaviour. Phrasings: "compact the context", "summarise the
  conversation", "context is too long", "agent forgets / gets dumber over time",
  "trim tool output", "checkpoint before compaction".
when_to_use:
  - An agent runs for many turns and the context window is filling up (near auto-compact)
  - Tool outputs (file reads, API JSON, logs) are bloating context and driving cost/latency up
  - Answer quality degrades late in a long session ("context rot") even though facts are present
  - You are building an agent harness/loop and need a compaction trigger + summary strategy
  - You want to preserve decisions/task state across a summarisation boundary without losing them
  - Cost per session is climbing because full history is re-sent every turn
when_not_to_use:
  - You just want layered memory (working/episodic/semantic) design — use structured-memory-layers
  - You need to measure/budget token spend per component — use context-window-budgeter
  - You want to score whether context is helping or hurting retrieval — use context-quality-evals
  - You are isolating a worker's context from the parent by spawning children — use subagent-context-isolation
  - You want a persistent scratchpad/memory file the agent reads+writes — use agent-memory-file
keywords: [context compaction, context rot, summarize conversation, auto-compact, token threshold, context window, tool output truncation, checkpoint, external memory, subagent offload, anchored summary, long-horizon agent, compression, context management, prune history, reserve tokens]
similar_to: [structured-memory-layers, context-window-budgeter, context-quality-evals, subagent-context-isolation, agent-memory-file, prompt-compression]
inputs_needed:
  - Model context window size (e.g. 200K) and where token counts come from (usage.input_tokens)
  - Whether the agent has an external memory store (file/DB) it can write to before compacting
  - What MUST survive a summary (task list, key decisions, file paths, user constraints)
produces: A compaction policy + anchored-summary prompt + tool-output caps wired into an agent loop
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Agent Context Compaction

Long-running agents fail in two ways as history grows: they get **expensive**
(full history re-sent every turn) and they get **dumber** — Chroma's *Context Rot*
study shows model reliability drops well before the window is "full" (a 200K model
degrades noticeably around 50K tokens; even a single distractor lowers accuracy;
focused ~300-token prompts beat ~113K-token full-context ones on the same task).
So: keep the working context small on purpose. Compaction is how.

## When to use

Reach for this when an agent loops many turns, tool JSON/logs/file reads bloat the
window, cost climbs, or late-session answers get vague. The goal is a **bounded
working context** — not the biggest window you can afford.

## Core model (four moves)

1. **Trigger** — fire compaction at a token threshold, not "when it errors".
2. **Checkpoint** — write durable state to external memory *before* you compress.
3. **Compress** — replace old turns with ONE anchored, typed summary block.
4. **Offload** — push heavy/parallel work to sub-agents so it never lands in the parent.

## Prerequisites

- A token count each turn. Anthropic/OpenAI SDK responses return usage
  (`response.usage.input_tokens`). For a pre-flight estimate, `chars / 4` is a cheap
  proxy; use the real count from the last response for the trigger.
- The model's context window (Claude Sonnet/Opus = 200K unless you're on the 1M beta).
- Optional but recommended: an external store (a memory file, KV, or DB) the agent
  can write to. No new keys/deps required for the file approach.

## Recipe 1 — Set the compaction trigger

Fire on a **reserve buffer** below the window, not a naive 100%. Real harnesses
(per Arize's survey) sit around 50-90%:

| Harness    | Trigger                                   |
|------------|-------------------------------------------|
| Claude Code| ~167K on a 200K window (~13K buffer, ~83%) |
| Pi         | `contextWindow − reserveTokens` (16,384)  |
| OpenClaw   | history > 50% of window (`maxHistoryShare`)|
| Letta      | usage > 90% of window                      |

Default to **~70-80%** — early enough to dodge context rot, late enough to avoid
thrashing. Encode it as a reserve so it scales with the window:

```python
WINDOW = 200_000
RESERVE = 40_000          # ~20% headroom; compaction fires at 160K
def should_compact(input_tokens: int) -> bool:
    return input_tokens > (WINDOW - RESERVE)
```

Never trigger mid tool-call/tool-result pair — see Pitfalls.

## Recipe 2 — Cap tool output BEFORE it enters context

The cheapest compaction is not admitting bloat in the first place. Cap large tool
results and persist the full thing to disk with a preview stub the agent can re-open.
Harness defaults to copy: file reads capped at **2,000 lines / ~50KB**; oversized
tool results capped ~**50K chars each**, ~200K aggregate per message.

```python
MAX_TOOL_CHARS = 50_000
def cap_tool_result(name: str, text: str, save) -> str:
    if len(text) <= MAX_TOOL_CHARS:
        return text
    path = save(text)  # write full output to disk / memory store
    head = text[:MAX_TOOL_CHARS]
    return f"{head}\n\n[TRUNCATED {len(text):,} chars → saved to {path}. Re-read that path for the rest.]"
```

## Recipe 3 — Checkpoint to external memory (write BEFORE compacting)

Summaries are lossy. Extract durable state to a memory file **each turn** (or in a
"silent turn" right before compaction) so nothing in-flight dies at the boundary.
This is the write-before-compaction pattern.

```python
def checkpoint(memory_path, state: dict):
    # append-only, immutable snapshots — never mutate prior entries
    import json, time
    entry = {"ts": time.time(), **state}
    with open(memory_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

Persist: open task list, decisions + rationale, file paths touched, user
constraints, unresolved errors. After compaction the summary can be terse because
the memory file is the source of truth the agent re-reads.

## Recipe 4 — Compress into an anchored, typed summary

Run the history through the model with a **structured** prompt and replace all prior
turns with one summary block. Claude Code uses a 9-section schema — reuse it:

```
Summarise the conversation so far into these exact sections. Be specific;
preserve identifiers, file paths, and numbers verbatim. Do not invent.

<scratchpad>...your analysis (this is STRIPPED, not kept)...</scratchpad>
<summary>
1. Primary request & intent
2. Key technical concepts
3. Files and code (paths + what changed)
4. Errors and fixes
5. Problem-solving in progress
6. All user messages (verbatim intent)
7. Pending tasks
8. Current work (exactly where we are)
9. Next step (optional)
</summary>
```

Keep only `<summary>`; drop `<scratchpad>`. Then rebuild the request as:
`[system] + [typed summary block] + [most recent N turns kept verbatim]`.
Keeping the last few real turns preserves the "live" thread the summary blurs.

Reported compression is large — a 335K-token research context folded to ~2.8K
(~120:1) on tool-heavy trajectories.

## Recipe 5 — Offload to sub-agents

If a task needs to read a lot to produce a little (search 40 files → 1 answer),
spawn a sub-agent with ONLY the task message — no parent history — and return just
its result to the parent. The exploration tokens never touch the main window. (For
the full pattern see the `subagent-context-isolation` skill.)

## Verify

- **Trigger fires:** log `input_tokens` each turn; confirm compaction runs before
  the window fills and that post-compaction `input_tokens` drops sharply.
- **Nothing lost:** after a compaction, the agent can still name the current task,
  open files, and last decision (from summary + memory file). Ask it to.
- **Pairs intact:** no orphaned tool-result blocks after trimming (API will 400 if so).
- **Quality:** re-ask a question answerable only from mid-session facts; a rotted
  context gets it wrong, a well-checkpointed one recovers it from memory.

## Pitfalls

- **Cutting mid tool-call.** Never drop a tool-result without its tool-call (or vice
  versa) — walk message boundaries and keep pairs together, or the API rejects it.
- **Summarise-only, no checkpoint.** Lossy summaries silently delete decisions.
  Always write external memory *before* compressing.
- **Summaries hide the stop signal.** LLM summaries can *lengthen* trajectories
  13-15% because the agent loses the natural "we're done" cue. Keep an explicit
  pending-task/next-step field and check it after compaction.
- **Triggering too late.** Waiting for "window full" means you already paid the
  context-rot tax for many turns. Fire on the reserve buffer (~70-85%).
- **Mutating memory.** Checkpoints are append-only immutable snapshots; never edit a
  prior entry (keeps history debuggable and safe under concurrency).
- **Bigger window ≠ safer.** A 200K/1M window still rots; compaction and small
  working context matter regardless of the max.

## Sources

- Chroma, *Context Rot: How Increasing Input Tokens Impacts LLM Performance* —
  trychroma.com/research/context-rot
- Arize, *Context management in agent harnesses: memory, files, and subagents* —
  arize.com/blog/context-management-in-agent-harnesses
