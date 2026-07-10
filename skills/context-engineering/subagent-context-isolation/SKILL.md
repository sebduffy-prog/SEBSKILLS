---
name: subagent-context-isolation
category: context-engineering
description: >
  Keep the orchestrator's context lean by delegating deep work to sub-agents with
  scoped, isolated context windows and artifact-backed hand-offs. Give each sub-agent
  a narrow task + only the inputs it needs; make it do its exploration in its own
  window (tens of thousands of tokens) and return only a condensed 1-2k-token summary
  plus file paths — never dumping raw tool output, transcripts, or full files back to
  the lead. Use when a Task/subagent returns too much, when the orchestrator's context
  bloats from delegation, when designing a research/fan-out or multi-agent pipeline, or
  when asked to "scope subagent context", "summarize before returning", or "pass results
  via files not chat".
when_to_use:
  - "A Task/subagent dumps huge raw output (file dumps, logs, transcripts) back into the main context"
  - "The orchestrator's context window is bloating every time it delegates work"
  - "Designing a research fan-out or multi-agent pipeline and deciding what each agent sees and returns"
  - "You want subagents to hand off results via artifact files + paths instead of pasting them into chat"
  - "Writing the prompt/spec for a subagent and need to bound its inputs and its return payload"
  - "A lead agent should stay strategic (plan + synthesize) while workers do the token-heavy digging"
when_not_to_use:
  - "Compacting one long single-agent conversation transcript → use agent-context-compaction"
  - "Budgeting/counting tokens across a fixed window → use context-window-budgeter"
  - "Persisting per-user facts across sessions → use structured-memory-layers or agent-memory-file"
  - "Measuring whether the retained/returned context is actually good → use context-quality-evals"
  - "Shrinking a single prompt's wording losslessly → use prompt-compression"
  - "Just running independent tasks in parallel with no context-return concern → use dispatching-parallel-agents"
keywords: [subagent, sub-agent, context isolation, orchestrator, lead agent, task tool, fan-out, multi-agent, summarize before return, artifact handoff, scoped context, clean context window, condensed summary, delegation, context pollution, research subagent, return payload, worker agent]
similar_to: [agent-context-compaction, context-window-budgeter, structured-memory-layers, context-quality-evals, agent-memory-file, prompt-compression]
inputs_needed:
  - "The delegated task and the minimal set of inputs the subagent actually needs (not the whole conversation)"
  - "A shared scratch/artifact directory both agents can read/write (for file-backed hand-offs)"
  - "The return contract: max summary size (~1-2k tokens) + which file paths/artifacts to return"
  - "Whether workers run in parallel (fan-out) or sequentially, and whether they share any state"
produces: A subagent delegation pattern — scoped worker prompts, a file-backed hand-off contract, and summarize-before-return that keeps the lead agent's context lean
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Subagent Context Isolation

Delegation only saves context if the worker's exploration **stays in the worker**. The failure mode is a subagent that reads 40k tokens of files/logs and pastes all of it back — now the lead pays for the worker's whole context *plus* its own. The fix is three disciplines: **scope what the worker sees, isolate where it does its digging, and condense what it returns.**

Grounded in Anthropic's context-engineering guidance: "specialized sub-agents can handle focused tasks with clean context windows… each subagent might explore extensively, using tens of thousands of tokens or more, but returns only a condensed, distilled summary of its work (often 1,000–2,000 tokens)." The lead agent "focuses on synthesizing and analyzing the results" while "the detailed search context remains isolated within sub-agents."

## When to use

Reach for this whenever you delegate and the return payload is the problem, not the work. Three levers, apply all three:

| Lever | Bad (context bloats) | Good (context stays lean) |
|-------|----------------------|---------------------------|
| **Scope inputs** | Forward the whole conversation / all files "for context" | Pass only the task + the specific inputs it needs |
| **Isolate work** | Worker's raw tool calls surface in the lead | Worker reads/greps/runs entirely in its own window |
| **Condense return** | Return raw file contents, logs, transcripts | Return ≤1–2k-token summary + file paths to full artifacts |

## Core pattern: scope → isolate → condense

**1. Scope.** In the subagent prompt, state the task, the exact inputs, and forbid re-deriving context. Don't paste the parent's history. If the worker needs a big input, give it a **path**, not the contents — it can read what it needs itself.

**2. Isolate.** The subagent does its token-heavy work (reading dozens of files, running searches, driving tools) in its own context window. None of that intermediate output reaches the lead. This is the whole point — a research worker can burn 50k tokens and the orchestrator never sees a byte of it.

**3. Condense (summarize-before-return).** End every subagent prompt with an explicit **return contract**. The worker's *final message* is the only thing the lead ingests, so bound it:

```
Return ONLY (≤1500 tokens, no raw file dumps):
1. A 3-6 bullet summary of what you found / did.
2. Absolute paths to any artifacts you wrote (full detail lives there, not here).
3. Open questions or blockers, if any.
Do NOT paste file contents, full logs, or your tool transcript.
```

## Recipe A — file-backed hand-off (the durable default)

The most robust isolation: the worker writes full detail to a file and returns the **path**. The lead reads the file only if/when it needs to, and can pass the same path to the next worker — the payload between agents stays tiny regardless of how big the artifact is.

Subagent prompt skeleton:

```
Task: <one specific job>.
Inputs: <paths / IDs only — do not expect prior conversation>.
Scratch dir: /abs/scratch/<run-id>/   (write your full output here)

Do your work in your own context. When done:
- Write full results to <scratch>/findings.md (or .json).
- Return ONLY: a ≤1500-token summary + the absolute path(s) you wrote.
- Never paste the file's contents back into your final message.
```

Lead-side afterward: read the summary; open `findings.md` **only** for the specific slice you need (`Read` with an offset/limit, or `grep`), not the whole file. Chaining workers? Hand worker 2 the path from worker 1 — never the file body.

Why files beat chat for hand-offs: the artifact is re-readable, greppable, survives compaction, and decouples payload size from context cost. A 200k-token report costs the lead one path.

## Recipe B — research fan-out (parallel workers, condensed merge)

Lead plans → spawns N isolated workers in parallel, each with a disjoint slice → each returns a distilled summary + path → lead synthesizes from the summaries.

```
Lead (stays strategic):
  1. Decompose into N independent subtasks (no shared state between them).
  2. For each, dispatch a subagent with: its slice + scratch path + the return contract.
  3. Collect N summaries (~1-2k tokens each), NOT N raw explorations.
  4. Synthesize. Open individual artifact files only to resolve specific conflicts.
```

Keep slices **independent** so nothing needs to pass between siblings mid-flight (if they do, they're not isolated — reconsider the split). The lead's context grows by ~N×1.5k tokens, not by N×50k. For the mechanics of dispatching independent work in parallel, pair this with `dispatching-parallel-agents`; this skill governs *what each worker returns*.

## Recipe C — tighten a worker that's already too chatty

Retrofitting an existing noisy subagent:

- Add the return contract (the ≤1–2k-token block above) to the **end** of its prompt — recency makes it stick.
- Redirect volume to a file: "write the full table/log/diff to `<path>` and return only its path + a one-line description."
- Forbid pass-through: "do not echo tool output; report conclusions, not the transcript."
- Cap enumerations: "list at most the top 5; put the rest in the file."
- If the worker must quote, quote the *load-bearing* lines only (a signature, an error), never the surrounding file.

## Verify

- **Payload check:** the subagent's final message is a summary + paths, with **no** raw file/log/transcript dumps. Skim it — if you see file contents, the contract failed.
- **Isolation check:** the lead's context did not grow by the worker's exploration size. Rough gauge: return should be «\< 5%» of what the worker read. Reading 40k → returning ~1.5k is right; returning 30k is broken.
- **Artifact check:** every path the worker returned actually exists and holds the full detail (`test -f <path>` / open it).
- **Chaining check:** downstream workers received *paths*, not pasted bodies, from upstream ones.
- **Synthesis check:** the lead could plan/answer from summaries alone, opening full files only for specific, named lookups.

## Pitfalls

- **Delegation without a return contract makes context *worse*, not better.** You pay the worker's context AND the pasted-back result. The condense step is non-negotiable — a subagent with no size bound will happily return everything it read.
- **Over-forwarding inputs.** Pasting the whole conversation "so it has context" defeats scoping. Give the task and the minimal inputs; let the worker fetch the rest from paths.
- **Returning bodies instead of paths.** A summary that inlines the 300-line file it references isn't a summary. Path + the 5 relevant lines, full detail on disk.
- **No shared scratch dir.** File hand-offs need a path both agents can reach. Agree the directory up front (this project uses a session scratchpad).
- **Faux-independent fan-out.** If siblings must exchange data mid-run, they share state and aren't isolated — either sequence them or redraw the boundaries.
- **Lead re-reads everything anyway.** Isolation is wasted if the orchestrator opens every artifact in full. Read summaries; open files surgically (`grep`/offset), only when a specific decision needs a specific fact.
- **Over-condensing drops the load-bearing detail.** A summary that omits the exact number/path/error the lead needs forces a re-run. Include decision-critical specifics (IDs, paths, counts, the one error string) in the summary; bulk goes to the file. Validate with `context-quality-evals` if return quality is uncertain.
- **Lossy hand-off, no provenance.** Always return the artifact path alongside the summary so the lead can verify a claim against the source instead of trusting a possibly-hallucinated distillation.
