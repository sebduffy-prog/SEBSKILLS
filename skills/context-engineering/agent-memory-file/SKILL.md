---
name: agent-memory-file
category: context-engineering
description: >
  Use the filesystem as durable, out-of-context memory for a Claude agent — scoped CLAUDE.md rule
  files, a NOTES.md progress ledger that survives compaction and context resets, and progressive
  disclosure of long material by reference instead of pasting. Author these files and wire the
  Anthropic memory tool (/memories, context-management-2025-06-27 beta). Use when the user says
  "remember this across sessions", "agent keeps forgetting", "notes that survive compaction",
  "persistent memory file", "CLAUDE.md rules", "memory tool", or "don't reload the whole doc".
when_to_use:
  - Agent loses track of progress on a long, multi-turn task once the window compacts or resets
  - You want facts/decisions/preferences to persist across separate sessions without re-prompting
  - A task references a huge doc/dataset and you want to load it on demand instead of pasting it all
  - You're wiring Anthropic's file-based memory tool (/memories) into an API/SDK agent
  - You want project or directory-scoped behavioral rules (CLAUDE.md) an agent auto-reads
when_not_to_use:
  - Deciding what layers of memory should exist and their precedence — use structured-memory-layers
  - Summarizing/pruning an overflowing window in place — use agent-context-compaction
  - Counting tokens and allocating a budget across sections — use context-window-budgeter
  - Measuring whether retained context is actually good — use context-quality-evals
  - Isolating scratch context inside a child agent — use subagent-context-isolation
keywords: [memory tool, claude.md, notes.md, /memories, agentic memory, note-taking, progressive disclosure, survives compaction, context management, context-management-2025-06-27, persistent memory, durable context, file-based memory, cross-session, str_replace, memory directory]
similar_to: [structured-memory-layers, agent-context-compaction, context-window-budgeter, subagent-context-isolation]
inputs_needed:
  - Runtime — Claude Code / a coding agent (uses CLAUDE.md + files) vs. an API/SDK agent (uses the memory tool)
  - Where memory should live and its scope (repo root, subdir, ~/.claude, per-user store)
  - Whether memory must persist across separate sessions or only survive compaction within one run
produces: A scoped CLAUDE.md + NOTES.md convention and/or a wired /memories memory-tool handler with a load-on-demand pattern
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Agent Memory File

Treat the filesystem as memory the model does not have to hold in its context window. Three
patterns, escalating in machinery:

1. **CLAUDE.md** — durable *rules/facts*, auto-read on session start (Claude Code).
2. **NOTES.md** — a running *progress ledger* the agent writes to as it works; survives compaction.
3. **Memory tool** (`/memories`) — API/SDK agents that persist files across sessions via six commands.

All three exploit the same idea from Anthropic's context-engineering guidance: **write notes to
disk, retrieve them by reference, and disclose long material progressively** rather than pasting it
up front. The window can reset at any moment — anything not on disk is lost.

## When to use

- The agent "forgets" earlier decisions after a long run or a `/compact`.
- You need facts/preferences to carry across *separate* sessions.
- A task cites a 200-page doc — you want a pointer + read-on-demand, not 200 pages in-context.

## Prerequisites

- **CLAUDE.md / NOTES.md patterns:** zero deps. Any agent that reads the filesystem. Claude Code
  auto-loads `CLAUDE.md`; other harnesses need you to reference the file in the system prompt.
- **Memory tool:** an Anthropic API/SDK integration. Beta header `context-management-2025-06-27`,
  the `memory` tool in your `tools` list, and a **client-side handler you implement** — Claude only
  *requests* memory ops; your code executes them against storage you control (a per-user dir, S3,
  DB rows). `/memories` is a path prefix you map, not a real folder Anthropic provides.

## Recipe 1 — Scoped CLAUDE.md rules (durable facts)

Put stable, always-true context in a `CLAUDE.md` at the scope it applies to. Precedence is
narrowest-wins: a subdir file layers on top of the repo root, which layers on top of `~/.claude/`.

```
~/.claude/CLAUDE.md          # personal defaults across every project
<repo>/CLAUDE.md             # project conventions, build/test commands, architecture
<repo>/services/api/CLAUDE.md # rules only when working inside services/api
```

Keep it **short and imperative** — it is prepended to *every* turn, so it is pure token cost when
irrelevant. Facts, commands, and hard rules; not tutorials.

```markdown
# CLAUDE.md
- Run tests with `pnpm test`, never `npm`.
- API responses use the envelope in src/lib/response.ts — reuse it, don't hand-roll.
- Migrations are irreversible in prod: never edit a shipped migration, add a new one.
- See docs/architecture.md for the module map (read it before large refactors).
```

That last line is **progressive disclosure**: a pointer, not the pasted doc. The agent opens
`docs/architecture.md` only when a task needs it.

## Recipe 2 — NOTES.md progress ledger (survives compaction)

For long, multi-step work, have the agent maintain a scratch file and update it *as it goes*, so a
compaction or reset can be recovered by re-reading one file. Seed it and instruct the agent to keep
it current:

```markdown
# NOTES.md — <task name>
## Goal
<one line>
## State (last updated <ts>)
- [x] Parsed 12/40 input files
- [ ] Next: file 13 (batch dir /data/raw)
## Decisions
- Chose streaming parse — full load OOMs at ~2GB.
## Open questions
- Confirm timezone of `created_at` (assumed UTC).
```

Rules that make this actually work:
- **Append-or-replace, never blind-append forever** — the ledger must stay small enough to re-read
  cheaply. Use `str_replace`-style edits to update the State block in place.
- **Write before you risk the reset** — record a checkpoint *before* a long tool call, not after.
- **On resume, read NOTES.md first** — make step 1 of the task "view the ledger for prior progress."

This is exactly how Claude Code's own to-do tracking and the Pokémon-playing agent kept tallies
across thousands of steps that never fit in one window.

## Recipe 3 — Wire the memory tool (/memories, cross-session)

For an API/SDK agent that must persist across sessions. Six client-side commands you implement:
`view`, `create`, `str_replace`, `insert`, `delete`, `rename`. When the tool is present, the API
auto-injects a protocol telling Claude to `view` `/memories` first and record progress there.

```python
import anthropic

client = anthropic.Anthropic()

resp = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=2048,
    betas=["context-management-2025-06-27"],
    tools=[{"type": "memory_20250818", "name": "memory"}],
    messages=[{"role": "user", "content": "Resume the migration audit."}],
)
```

The SDK ships `BetaAbstractMemoryTool` — subclass it and implement the six handlers. **You own
storage and safety:** every command carries a `/memories`-prefixed path; validate and sandbox it so
a path like `/memories/../../etc` cannot escape the store (path traversal is the #1 footgun here).
Map `/memories` to a per-user directory or key namespace so users never see each other's memory.

Pair it with **context editing** (auto-clearing stale tool results) — Anthropic reports ~39% better
agentic-search results and large token savings from the combination, because facts live on disk and
the window stays lean.

## Verify

- **CLAUDE.md:** start a fresh session, ask the agent a question answered only by the file (e.g.
  "how do I run tests here?") — it should answer without you pasting anything.
- **NOTES.md:** run the task, force a `/compact` (or start a new session), tell the agent to resume.
  It should read the ledger and continue from the last checkpoint, not restart.
- **Memory tool:** log every command your handler receives; confirm a first turn issues `view`
  `/memories`, and that a *second, separate* session sees files the first wrote.

## Pitfalls

- **Bloated CLAUDE.md.** It is on every turn — long files are permanent token tax and dilute
  attention. Keep it to rules and pointers; push detail into referenced docs.
- **Stale ledger.** If the agent stops updating NOTES.md, resume recovers a lie. Instruct explicit,
  timestamped State updates and treat the ledger as the source of truth on resume.
- **Path traversal in the memory handler.** Reject/normalize any path escaping the `/memories`
  root before touching storage. Never `open()` the raw path.
- **Pasting instead of pointing.** Dropping a whole document inline defeats progressive disclosure.
  Store it, reference it by path, let the agent read on demand.
- **Cross-user leakage.** A shared `/memories` store leaks one user's memory into another's context.
  Namespace per user.
- **Assuming persistence you didn't build.** The memory tool is *client-side* — if your handler
  doesn't write to durable storage, nothing survives. Anthropic executes nothing for you.

## Sources

- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Memory tool — Claude Docs](https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool)
- [Managing context on the Claude Developer Platform](https://www.anthropic.com/news/context-management)
