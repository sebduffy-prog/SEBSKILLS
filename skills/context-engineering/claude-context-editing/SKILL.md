---
name: claude-context-editing
category: context-engineering
description: >
  Configure Anthropic's SERVER-SIDE context editing so heavy tool-use agents self-prune
  cache-safely instead of you hand-rolling compaction. Wire clear_tool_uses_20250919
  (drop stale tool results at a token/tool-use trigger, keep the last N pairs) and
  clear_thinking_20251015 (drop old thinking blocks), gate with clear_at_least so a clear
  is worth the cache-write cost, exclude_tools to protect memory/web_search, and hand off
  to the memory tool before results vanish. Use when tool JSON bloats context, cost/latency
  climb on long agent loops, or you want API-level GC. Phrasings: "context editing",
  "clear tool results", "context-management beta", "server-side compaction", "keep recent
  tool uses", "clear_tool_uses", "thinking block clearing".
when_to_use:
  - A tool-heavy agent (search, code, browser, MCP) fills the window with stale tool-result JSON
  - You want the API to prune context server-side instead of maintaining your own compaction loop
  - Cost/latency climb because every turn re-sends bloated old tool outputs
  - You are pairing the memory tool with clearing so state survives before results are dropped
  - You want cache-safe GC — clear only when it clears enough tokens to beat the cache-write cost
  - Extended-thinking agents accumulate old thinking blocks you want dropped past N turns
when_not_to_use:
  - You want a client-side summary+checkpoint compaction loop you fully control — use agent-context-compaction
  - You need the model to persist/recall durable state across sessions — use managed-agent-memory
  - You just want to measure/budget token spend per component — use context-window-budgeter
  - You are isolating a worker's context from the parent by spawning children — use subagent-context-isolation
  - You want to score whether context is helping vs hurting retrieval — use context-quality-evals
keywords: [context editing, context management, clear_tool_uses_20250919, clear_thinking_20251015, context-management-2025-06-27, server-side compaction, tool result clearing, keep recent, clear_at_least, exclude_tools, memory tool, prompt caching, beta header, applied_edits, token trigger, agent loop]
similar_to: [agent-context-compaction, managed-agent-memory, context-window-budgeter, subagent-context-isolation, structured-memory-layers, prompt-compression]
inputs_needed:
  - Anthropic API key + a model on the Claude API (SDK or raw HTTP); the beta header enabled
  - The agent's tool set and which tools produce bloat vs which must never be cleared (memory, web_search)
  - A token/tool-use threshold to trigger clearing and how many recent tool pairs to keep
produces: A context_management block (edits + trigger/keep/clear_at_least/exclude_tools) wired into the Messages call, plus optional memory-tool handoff and a verify loop on applied_edits
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Context Editing (server-side context management)

Anthropic's **context editing** lets the API prune your conversation *server-side,
before the prompt reaches Claude*, so a tool-heavy agent stays cheap and sharp without
you writing a compaction loop. You keep the full history locally; you pass a
`context_management` block; the API strips stale tool results (and optionally old
thinking blocks) and tells you what it removed. This is API-level garbage collection —
it replaces hand-rolled truncation for many agents.

## When to use

Reach for this when a loop hammers tools (web search, code execution, browser, MCP) and
the window fills with old tool-result JSON that no longer earns its tokens. If instead
you want a client-side summarise+checkpoint loop you fully own, use
`agent-context-compaction`; the two compose (clear cheaply server-side, summarise as a
backstop).

## Prerequisites (honest about beta)

- **Beta.** Send the header `context-management-2025-06-27`. Field names, edit-type
  suffixes, and defaults can change while it's beta — pin the version string and re-check
  the docs before shipping: platform.claude.com/docs/en/build-with-claude/context-editing
- **Models.** Documented as supported on all current Claude models. `clear_thinking_20251015`
  only matters when extended thinking is on, and its *default* keep-behaviour is
  model-class dependent (newer Opus/Sonnet keep all prior thinking; older models keep only
  the last turn).
- **You still hold history.** Editing is applied server-side only for that request; your
  client keeps the full, unmodified transcript. No client/server state sync needed.
- **ZDR-eligible.** Works under a Zero Data Retention arrangement.
- Two edit types exist today: `clear_tool_uses_20250919` (tool results) and
  `clear_thinking_20251015` (thinking blocks).

## Recipe 1 — Minimal: let the API clear stale tool results

Defaults: trigger at **100,000 input tokens**, keep the **last 3 tool-use/result pairs**,
clear only results (not the tool-call inputs).

```python
import anthropic
client = anthropic.Anthropic()

resp = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    betas=["context-management-2025-06-27"],
    tools=[...],
    messages=conversation,          # your FULL local history
    context_management={
        "edits": [{"type": "clear_tool_uses_20250919"}],
    },
)
```

Raw HTTP: add header `anthropic-beta: context-management-2025-06-27` and put the same
`context_management` object in the JSON body.

## Recipe 2 — Tuned trigger, keep, and cache-safe floor

Fire earlier, keep more live pairs, and — critically — only clear when it clears **enough**
to be worth the cache invalidation (`clear_at_least`). If it can't hit that floor, the edit
is skipped, so you don't burn a cache-write to reclaim a handful of tokens.

```python
context_management={
    "edits": [{
        "type": "clear_tool_uses_20250919",
        "trigger": {"type": "input_tokens", "value": 30000},   # or {"type":"tool_uses","value":N}
        "keep": {"type": "tool_uses", "value": 3},             # recent pairs preserved verbatim
        "clear_at_least": {"type": "input_tokens", "value": 5000},
        "exclude_tools": ["web_search", "memory"],             # never clear these results
        "clear_tool_inputs": False,                            # True also strips the tool-call args
    }],
}
```

- `trigger` — when clearing activates: by cumulative `input_tokens` or by `tool_uses` count.
- `keep` — how many recent tool-use/result pairs to leave untouched.
- `clear_at_least` — minimum tokens the clear must free, else it doesn't apply (cache guard).
- `exclude_tools` — tool names whose results are never cleared.
- `clear_tool_inputs` — `False` clears only results; `True` also removes the tool-call
  parameters (frees more, but the model loses what it asked for).

## Recipe 3 — Memory-tool handoff (don't lose state to a clear)

Pair clearing with the memory tool (`type: "memory_20250818"`). Before results are cleared,
Claude receives an automatic warning and can write anything important to a memory file
first — so durable facts survive the GC. Exclude `memory` from clearing so the handoff
itself never gets pruned.

```python
resp = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=2048,
    betas=["context-management-2025-06-27"],
    tools=[{"type": "memory_20250818", "name": "memory"}, *other_tools],
    messages=conversation,
    context_management={
        "edits": [{
            "type": "clear_tool_uses_20250919",
            "exclude_tools": ["memory"],
        }],
    },
)
```

This is the clean division of labour: **context editing frees the window; the memory tool
preserves what mattered.** For a broader persistent-state design, see `managed-agent-memory`.

## Recipe 4 — Clear old thinking blocks (extended-thinking agents)

When combining both edits, **list `clear_thinking_20251015` first** in the array.

```python
context_management={
    "edits": [
        {"type": "clear_thinking_20251015",
         "keep": {"type": "thinking_turns", "value": 2}},   # or "all" to maximise cache hits
        {"type": "clear_tool_uses_20250919",
         "trigger": {"type": "input_tokens", "value": 50000},
         "keep": {"type": "tool_uses", "value": 5}},
    ],
}
```

`keep: "all"` preserves every thinking block (best cache reuse, more tokens);
`{"type": "thinking_turns", "value": N}` keeps thinking from the last N assistant turns (N > 0).

## Recipe 5 — Preview the effect before you rely on it

`count_tokens` accepts the same block and reports before/after, so you can validate a config
offline without spending output tokens.

```python
ct = client.beta.messages.count_tokens(
    model="claude-opus-4-8",
    betas=["context-management-2025-06-27"],
    messages=conversation,
    context_management={"edits": [{"type": "clear_tool_uses_20250919"}]},
)
# ct.context_management.original_input_tokens  -> before editing
# ct.input_tokens                              -> after editing
```

## Verify

- **It actually cleared.** Read `resp.context_management.applied_edits`. Each entry reports
  e.g. `cleared_tool_uses`, `cleared_input_tokens` (and `cleared_thinking_turns` for the
  thinking edit). Empty `applied_edits` = nothing fired (trigger not hit, or `clear_at_least`
  not met). Streaming: the block arrives on the final `message_delta`.
- **Tokens dropped.** Compare `count_tokens` original vs after (Recipe 5), or watch
  `usage.input_tokens` fall on the next turn.
- **State survived.** After a clear, ask the agent to name the current task / open files —
  it should recover them from memory files, not from the pruned tool results.
- **Cache still hits.** Check `usage.cache_read_input_tokens`; if it collapses to 0 every
  turn your trigger is thrashing the cache (see Pitfalls).

## Pitfalls

- **Cache thrash.** Clearing invalidates the cached prefix and forces a cache-write. If you
  clear a little, often, you pay writes for tiny gains. Use `clear_at_least` as a floor and a
  `trigger` that fires in chunks, not every turn.
- **Beta drift.** This is beta — the `-2025-06-27` header, edit-type date suffixes, and
  defaults can change. Pin the version and re-read the doc before a production ship.
- **Losing state silently.** Clearing is lossy by design. Without the memory-tool handoff (or
  a client-side checkpoint), decisions buried in old tool results are gone. Wire memory and
  `exclude_tools: ["memory"]`.
- **Over-clearing inputs.** `clear_tool_inputs: True` removes the tool-call arguments too; the
  model then can't see what it previously asked a tool. Leave it `False` unless the args are
  genuinely dead weight.
- **Edit ordering.** With both edits present, `clear_thinking_20251015` must come first in the
  `edits` array or the config is malformed.
- **Excluding the wrong tools.** Never clear `web_search` results you still cite, or the
  memory tool — put them in `exclude_tools`.
- **Assuming it replaces memory.** Context editing frees the window; it does not remember
  anything. Durable recall is the memory tool's job (`managed-agent-memory`).
- **Forgetting the header.** Omit `context-management-2025-06-27` and the `context_management`
  field is ignored (or errors); nothing clears and you won't get `applied_edits`.

## Sources

- Anthropic, *Context editing* — platform.claude.com/docs/en/build-with-claude/context-editing
- Anthropic, *Memory tool* (`memory_20250818`) — platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
