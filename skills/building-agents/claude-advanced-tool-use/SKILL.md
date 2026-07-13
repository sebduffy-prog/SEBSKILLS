---
name: claude-advanced-tool-use
category: building-agents
description: >
  Cut multi-tool / multi-MCP agent overhead by wiring Anthropic's Tool Search Tool
  plus `defer_loading` and `input_examples` into an SDK app. Mark bulky and MCP
  tools `defer_loading: true` so only 3-5 relevant tools ever enter context, add
  a `tool_search_tool_regex_20251119` or `tool_search_tool_bm25_20251119` search
  tool, and attach schema-validated example invocations for accuracy — Anthropic
  reports ~85% tool-definition token cut and large tool-selection accuracy gains.
  Use when an agent aggregates 10+ tools or 200+ MCP tools, tool defs blow past
  10k tokens, or Claude picks the wrong tool as the catalog grows. Handles
  regex-vs-BM25 choice, response wiring, MCP toolset config, and pitfalls.
when_to_use:
  - "Your agent exposes 10+ tools, or aggregates several MCP servers (200+ tools), and tool definitions dominate the context window"
  - "Tool-selection accuracy degrades as the catalog grows past ~30-50 tools and Claude calls the wrong one"
  - "You want to keep a few hot tools always-loaded but discover the long tail on demand via a search tool"
  - "You have a complex tool with nested / format-sensitive inputs and Claude keeps mis-shaping the arguments"
  - "You're deciding between regex and BM25 tool search, or wiring the server_tool_use / tool_search_tool_result response blocks correctly"
when_not_to_use:
  - "You have fewer than 10 small tools all used every request — plain tool use is cheaper (see claude-api)"
  - "You're authoring the MCP server itself rather than the agent that consumes it — use mcp-builder"
  - "You want a rubric/eval gate on agent output, not tool-catalog scaling — use managed-agents-outcomes"
  - "You need Claude Code subagent orchestration, not raw SDK tool wiring — use claude-code-agent-teams"
keywords:
  - tool search tool
  - defer_loading
  - input_examples
  - tool use examples
  - regex tool search
  - bm25 tool search
  - tool_reference
  - mcp toolset
  - context bloat
  - deferred tools
  - anthropic sdk
  - tool selection accuracy
  - server_tool_use
  - advanced tool use
  - prompt caching
similar_to:
  - claude-api
  - mcp-builder
  - managed-agents-outcomes
  - claude-code-agent-teams
inputs_needed: "An Anthropic API key; an agent with 10+ tool definitions or one or more MCP servers; a supported model (Opus/Sonnet/Haiku 4.5 or newer)."
produces: "A tools array with a tool search tool + deferred definitions, a working search→discover→call loop, and optional input_examples — cutting tool-def tokens ~85%."
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Advanced Tool Use: Tool Search, defer_loading, input_examples

## When to use

Reach for this when an agent's **tool definitions**, not its work, are eating the
context window. A typical GitHub + Slack + Sentry + Grafana + Splunk stack burns
~55k tokens in definitions before Claude does anything, and selection accuracy
falls once you pass ~30-50 tools. The Tool Search Tool loads only the 3-5 tools
Claude needs per request (Anthropic reports **>85% token reduction** and, e.g.,
Opus 4.5 tool-selection accuracy rising 79.5% → 88.1%). `input_examples` is the
orthogonal lever: schema-validated sample calls that fix argument-shaping on
complex/nested inputs.

## Prerequisites

- **Availability (grounded, 2026-07):** Tool search is **generally available** on
  the Claude API — no beta header needed. It first shipped in the
  `advanced-tool-use-2025-11-20` beta; if you follow older blog code you'll see
  `betas=["advanced-tool-use-2025-11-20"]` on `client.beta.messages.create(...)`.
  On GA you can use the standard `client.messages.create(...)` with
  `anthropic-version: 2023-06-01`. `input_examples` is also GA (plain field on the
  tool definition). Confirm against the current docs before shipping — surfaces move.
- **Models:** both search variants work on Claude Haiku/Sonnet/Opus 4.5 and every
  newer model (Sonnet 4.6, Opus 4.6/4.7/4.8, Fable 5, Mythos 5). Opus 4.1 and
  earlier **do not** support tool search.
- **SDK:** `pip install anthropic` (works on this Mac's python3.9) or
  `@anthropic-ai/sdk`. Set `ANTHROPIC_API_KEY`.
- **Bedrock caveat:** server-side tool search is InvokeModel-only, not the Converse API.

## The three levers

| Lever | Field | What it does |
|-------|-------|--------------|
| Tool Search Tool | `{"type":"tool_search_tool_regex_20251119", ...}` in `tools` | lets Claude discover tools on demand |
| Deferred loading | `"defer_loading": true` on a tool | keeps its definition out of the prompt until discovered |
| Tool use examples | `"input_examples": [ {...}, ... ]` on a tool | shows concrete valid calls to fix arg-shaping |

## Recipe 1 — Wire the Tool Search Tool

You still **send every tool definition on every request** (the API needs them
server-side to run the search and expand references). `defer_loading` only controls
what enters Claude's context.

```python
import anthropic
client = anthropic.Anthropic()

resp = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=2048,
    messages=[{"role": "user", "content": "What's the weather in San Francisco?"}],
    tools=[
        # 1. The search tool itself — NEVER deferred. At least one tool must be non-deferred.
        {"type": "tool_search_tool_regex_20251119", "name": "tool_search_tool_regex"},

        # 2. Your long tail — deferred so their defs stay out of context until found.
        {
            "name": "get_weather",
            "description": "Get the weather at a specific location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
            "defer_loading": True,
        },
        # ...up to 10,000 deferred tools per request
    ],
)
print(resp.stop_reason)  # -> "tool_use"
```

Keep your **3-5 hottest tools non-deferred** so Claude calls them without a search
round-trip.

## Recipe 2 — regex vs BM25

Pick the variant by how you want Claude to query the catalog. Both search tool
**names, descriptions, argument names, and argument descriptions** (case-insensitive).

- **Regex** `tool_search_tool_regex_20251119` (name `tool_search_tool_regex`):
  Claude writes Python `re.search()` patterns (e.g. `"get_.*_data"`,
  `"database.*query|query.*database"`). **Max 200 chars.** Best when your tools use
  consistent namespacing (`github_`, `slack_`) — one pattern grabs a whole group.
- **BM25** `tool_search_tool_bm25_20251119` (name `tool_search_tool_bm25`): Claude
  uses natural-language queries. **Max 500 chars.** Best when tool names are less
  regular and descriptions carry the meaning.

Start with regex if you namespace by service; switch to BM25 if discovery misses.

## Recipe 3 — Handle the response loop

A search turn returns extra block types. Execute the **discovered** tool as usual;
never return a result for the search tool's `srvtoolu_...` id.

```
assistant content:
  text                       -> "I'll search for a weather tool."
  server_tool_use            -> id srvtoolu_..., input {"pattern": "weather"}   (runs on Anthropic's servers)
  tool_search_tool_result    -> nested tool_search_tool_search_result.tool_references: [{tool_name: get_weather}]
  text
  tool_use                   -> id toolu_..., name get_weather, input {...}      (YOU execute this)
stop_reason: "tool_use"
```

To continue: pass the assistant content back **unchanged** (including
`server_tool_use` and `tool_search_tool_result`), add your `tool_result` for the
`toolu_...` id in a user message, and resend the **same** tools array. The API
re-expands `tool_reference` blocks across history, so discovered tools stay callable
in later turns without re-searching. An empty `tool_references` array means "no
match", not an error.

## Recipe 4 — MCP toolsets

If tools come via the MCP connector, **do not** set `defer_loading` on individual
tools. Set it once on the `mcp_toolset` entry's `default_config` (whole server), or
per-tool under its `configs`:

```json
{ "type": "mcp_toolset", "mcp_server_name": "google-drive",
  "default_config": { "defer_loading": true } }
```

This is the highest-leverage use: a single toggle defers a whole 200-tool server
behind the search tool.

## Recipe 5 — input_examples (orthogonal, and it composes)

Add schema-valid sample calls to a complex tool. Each example **must validate
against `input_schema`** or the request 400s. They cost ~20-50 tokens (simple) to
~100-200 (nested).

```python
{
  "name": "get_weather",
  "description": "Get the current weather in a given location",
  "input_schema": { "...": "..." },
  "input_examples": [
      {"location": "San Francisco, CA", "unit": "fahrenheit"},
      {"location": "Tokyo, Japan", "unit": "celsius"},
      {"location": "New York, NY"}          # shows 'unit' is optional
  ]
}
```

Examples and tool search **compose**: when Claude discovers a deferred tool, the API
expands its `input_examples` alongside its definition — so you get accuracy on
exactly the tools that just entered context. `input_examples` is **not** supported
on server tools (web search, code execution).

## Verify

- **Token win:** compare `usage.input_tokens` with vs without `defer_loading`. With
  a large catalog you should see the deferred definitions drop out of the baseline.
  Tool search is **not** metered separately — discovered defs count as normal input
  tokens; there's no tool-search field in `usage.server_tool_use`.
- **Discovery works:** log the `server_tool_use.input` (the pattern/query) and the
  `tool_references` returned. If empty, test your own regex:
  `import re; re.search(r"pattern", "tool_name", re.IGNORECASE)`.
- **Caching intact:** `defer_loading` excludes deferred tools from the system-prompt
  prefix, so prompt caching is preserved. Verify `usage.cache_read_input_tokens > 0`
  across turns.

## Pitfalls

- **All tools deferred → 400** `"At least one tool must have defer_loading=false."`
  Never defer the search tool itself; keep 3-5 hot tools loaded.
- **Missing definition → 400** `"Tool reference 'x' not found in available tools"`.
  Every discoverable tool needs its full definition in the `tools` array *every*
  request, deferred or not.
- **`defer_loading` + `cache_control` on the same tool → 400.** Put the cache
  breakpoint on a **non-deferred** tool.
- **Don't answer the search tool.** Never send a `tool_result` for the
  `srvtoolu_...` id — the API rejects it. Only answer the discovered `toolu_...` call.
- **Limits:** ≤10,000 deferred tools/request; ≤5 results per search; regex ≤200
  chars, BM25 ≤500 chars.
- **Invalid `input_examples` 400s the whole request.** Validate each example against
  the schema first. Not usable on server tools.
- **Discovery relies on searchable text.** If a tool's name/description lacks the
  keywords users use, Claude won't find it. Namespace names (`slack_`, `github_`),
  and add a system-prompt line naming tool categories: "You can search for tools to
  interact with Slack, GitHub, and Jira."
- **Beta vs GA drift.** Old snippets use `client.beta.messages.create` +
  `betas=["advanced-tool-use-2025-11-20"]`. On GA that header is unnecessary for
  tool search — but Anthropic can change surfaces, so check the live docs before
  shipping and treat any newer feature you bolt on (e.g. programmatic tool calling
  via `allowed_callers` / code execution) as separate and possibly still beta.
