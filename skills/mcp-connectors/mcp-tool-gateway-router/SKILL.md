---
name: mcp-tool-gateway-router
category: mcp-connectors
description: >
  Fight MCP tool sprawl and context bloat when a session aggregates many servers (GitHub + Slack + Sentry + DB + Adobe = 200+ tools, ~55k tokens before any work). Use when Claude picks the wrong tool, /context shows tool defs eating the window, or you hit tool-use limits. Configures Claude Code tool search (ENABLE_TOOL_SEARCH, alwaysLoad), builds an Anthropic API request with defer_loading + tool_search_tool, or wires a RAG-over-tools gateway that retrieves only the 3-5 relevant tools per turn.
when_to_use:
  - "A session aggregates many MCP servers and tool definitions dominate the context window (check /context)"
  - "Claude selects the wrong tool or misfires once the toolset exceeds ~30-50 tools"
  - "You want on-demand tool discovery: defer most tools, load only what a task needs"
  - "Tuning Claude Code's ENABLE_TOOL_SEARCH / alwaysLoad, or diagnosing why ToolSearch finds nothing"
  - "Building an API app or proxy that does RAG/BM25/regex retrieval over hundreds of tools before calling Claude"
when_not_to_use:
  - "Adding, scoping, or authenticating a single MCP server — use register-mcp-servers"
  - "Authoring the MCP server itself (FastMCP / TS SDK, tool schemas) — use mcp-builder"
  - "Wiring one specific server end-to-end (GitHub, Postgres, Playwright, fetch) — use connect-github-mcp, connect-database-mcp, connect-playwright-mcp, connect-web-fetch-scrape-mcp"
  - "Under ~10 tools that all get used every request — plain tool calling is simpler; skip this"
keywords: [mcp, tool search, tool sprawl, context bloat, defer_loading, tool_reference, tool_search_tool_regex, tool_search_tool_bm25, enable_tool_search, alwaysload, rag-mcp, tool gating, dynamic tool discovery, tool router, gateway, list_changed, tool selection accuracy, claude code]
similar_to: [register-mcp-servers, mcp-builder, connect-github-mcp, connect-web-fetch-scrape-mcp]
inputs_needed:
  - "Surface: Claude Code CLI, or a custom app/agent calling the Anthropic Messages API directly"
  - "How many servers/tools are connected, and which 3-5 are 'hot' (used most turns)"
  - "For custom gateways: your tool catalog as JSON, and an ANTHROPIC_API_KEY"
produces: A tool-search config (env + .mcp.json) or a Messages API request body that defers the long tail of tools and loads only the few needed per turn, cutting tool-definition tokens by ~85%.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# MCP Tool Gateway & Router

Scale from a handful of tools to hundreds without drowning the context window or
wrecking tool-selection accuracy. Two failure modes appear past ~30-50 tools:
**context bloat** (a GitHub+Slack+Sentry+Grafana+Splunk setup burns ~55k tokens
in definitions before any work) and **selection rot** (tools blur together, the
model grabs the wrong one). The fix is just-in-time retrieval of tools: keep a
small hot set loaded, defer the long tail, and search for the rest on demand.

Grounded against the Claude Code MCP docs (`ENABLE_TOOL_SEARCH`, `alwaysLoad`),
the Anthropic tool-search tool (GA `2025-11-19`), and the MCP spec.

## When to use

Reach for this when the problem is *too many tools*, not *no tools*. Symptoms:
`/context` shows MCP/tool definitions eating a large slice of the window; Claude
calls the wrong tool or hallucinates arguments; you aggregate several MCP
servers; or you're building an app over a large tool catalog. For adding or
authing one server, use **register-mcp-servers**; for writing a server, use
**mcp-builder**.

## Prerequisites

- **Claude Code** v2.1.121+ for `alwaysLoad`; tool search is on by default and
  needs a model with `tool_reference` support (Sonnet 4.5+/Opus 4.5+; **Haiku
  does not support it**).
- **Custom API path**: an `ANTHROPIC_API_KEY` and a supported model
  (`claude-opus-4-8`, `claude-sonnet-4-6`, etc.). Tool search is generally
  available on the Claude API — no beta header required.
- The bundled `scripts/build_router_request.py` is stdlib-only (macOS py3.9 OK)
  and only *prints* a request body; it never calls the API.

## Recipe A — Claude Code: tune the built-in tool search (no code)

Claude Code already defers MCP tools by default: only tool names + server
instructions load at session start, and Claude calls `ToolSearch` to pull the
3-5 it needs. You mostly *tune* it.

1. **Confirm it's on.** Run `/context` — if MCP tools are a small line, search is
   working. If definitions dominate, tool search is disabled (Haiku model, a
   non-first-party `ANTHROPIC_BASE_URL` proxy, or `ENABLE_TOOL_SEARCH=false`).

2. **Set the mode** via env or `settings.json` `env`:

   | `ENABLE_TOOL_SEARCH` | Behavior |
   |---|---|
   | *(unset)* | All MCP tools deferred, loaded on demand (the default) |
   | `true` | Force-defer even through proxies / Agent Platform |
   | `auto` | Threshold: load upfront if defs fit within 10% of the window, else defer |
   | `auto:N` | Threshold at N% (0-100), e.g. `auto:5` |
   | `false` | Load every tool upfront (old behavior) |

   ```bash
   ENABLE_TOOL_SEARCH=auto:5 claude      # only defer once defs exceed 5% of window
   ENABLE_TOOL_SEARCH=false claude        # opt out entirely
   ```

3. **Exempt your hot servers** so their tools skip the search step. In
   `.mcp.json` set `alwaysLoad: true` — every tool from that server loads at
   startup regardless of `ENABLE_TOOL_SEARCH`:

   ```json
   {
     "mcpServers": {
       "core-tools": { "type": "http", "url": "https://mcp.example.com/mcp", "alwaysLoad": true }
     }
   }
   ```

   Keep this list tiny — each upfront tool is context you don't get back. A
   single tool can opt in via `"anthropic/alwaysLoad": true` in its `_meta`.

4. **Namespace for discoverability.** Search matches tool *names, descriptions,
   argument names, and argument descriptions*. Consistent prefixes
   (`github_`, `slack_`) let one query surface a whole group. If `ToolSearch`
   returns nothing for a task, the tool's text lacks the keywords the model
   searched — enrich the description, don't force `alwaysLoad`.

## Recipe B — Custom API app: defer_loading + tool_search_tool

When you call the Messages API yourself, you own the router. Send **every** tool
definition on every request (the server needs them to run the search), but mark
the long tail `defer_loading: true` so they never enter context until discovered.

1. Put your catalog in a JSON array and build the request body:

   ```bash
   python3 scripts/build_router_request.py catalog.json \
       --hot get_weather,search_files --variant regex \
       --model claude-opus-4-8 --prompt "What's the weather in SF?" > body.json
   ```

   Rules the script enforces (matching the API): the search tool itself is
   **never** deferred (all-deferred → 400), and every discoverable tool must have
   a full definition present (a `tool_reference` to a missing tool → 400).

2. The body includes a search tool plus your tools. Two variants:
   - `tool_search_tool_regex_20251119` — Claude writes Python `re.search()`
     patterns (≤200 chars, case-insensitive), e.g. `get_.*_data`.
   - `tool_search_tool_bm25_20251119` — natural-language queries (≤500 chars).

3. POST it and run the normal tool loop:

   ```bash
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" \
     -H "content-type: application/json" --data @body.json
   ```

   The response contains a `server_tool_use` (the search — **never** return a
   `tool_result` for its `srvtoolu_...` id) and a `tool_search_tool_result` whose
   `tool_references` the API auto-expands into full definitions. Then a normal
   `tool_use` you execute and answer with a `tool_result`. On the next turn pass
   the assistant content back unchanged and resend the same `tools` array.

4. **MCP connector users**: don't set `defer_loading` per tool — set it once on
   the `mcp_toolset` `default_config` (or per tool in `configs`) for the server.

Limits: up to 10,000 deferred tools/request; 5 results per search by default. A
deferred tool can't also carry `cache_control` (400) — put your cache breakpoint
on a non-deferred tool; deferral otherwise preserves prompt caching.

## Recipe C — RAG-over-tools gateway (embedding retrieval)

For a semantic router beyond regex/BM25 (the RAG-MCP / MCP-Zero pattern:
retrieve candidate tools by embedding similarity *before* the model sees them),
use a **client-side** search tool. Expose one custom tool; when Claude calls it,
run your own vector search and return the winners as `tool_reference` blocks:

```json
{ "type": "tool_result", "tool_use_id": "toolu_...",
  "content": [ { "type": "tool_reference", "tool_name": "discovered_tool" } ] }
```

Every referenced tool still needs a `defer_loading: true` definition in the
top-level `tools` array; the API expands the references the same way. This lets
you plug in embeddings, reranking, or a token-budget gate. Existing building
blocks to port rather than reinvent: **tool-gating-mcp** (MIT — a proxy exposing
`POST /api/tools/discover` for semantic search and `/api/tools/provision` for
budget-enforced selection across many servers), and the RAG-MCP paper's index +
retriever design. Aggregating servers behind one endpoint is also what
`mcp_toolset` deferral achieves without a separate proxy — reach for a custom
gateway only when you need retrieval logic the built-in variants can't express.

## Verify

- **Claude Code:** `/context` before vs after — MCP tool defs should shrink to a
  thin line; ask a task that needs an obscure tool and confirm a `ToolSearch`
  call precedes the tool_use. Anthropic reports ~85% fewer tool-definition
  tokens; RAG-MCP measured tool-selection accuracy roughly tripling.
- **Script:** `python3 -c "import ast; ast.parse(open('scripts/build_router_request.py').read())"`
  parses clean; the run in Recipe B prints a body whose `tools[0]` is the search
  tool and where non-hot tools carry `defer_loading: true` (stderr shows the
  deferred/upfront tally).
- **API:** a well-formed body returns `stop_reason: "tool_use"` with a
  `server_tool_use` block, not a 400.

## Pitfalls

- **All-deferred 400.** At least one tool (normally the search tool) must have
  `defer_loading` unset/false. The script guarantees this.
- **Haiku / proxy silently disables search.** Tool search needs `tool_reference`
  support; on Haiku or a non-first-party `ANTHROPIC_BASE_URL` Claude Code falls
  back to loading everything upfront. Set `ENABLE_TOOL_SEARCH=true` to force it
  where supported, or accept upfront loading.
- **Over-using `alwaysLoad`.** Marking many servers always-loaded recreates the
  sprawl you're fixing (and blocks startup until each connects, ~5s cap). Reserve
  it for the 3-5 tools needed every turn.
- **Undiscoverable tools.** Search only sees names/descriptions/arg text. Vague
  descriptions or missing keywords → empty `ToolSearch` results and a model that
  reports "no tool available". Fix the metadata, not the config.
- **Mishandling the search blocks.** Never send a `tool_result` for the
  `srvtoolu_...` id, and never expand `tool_reference` blocks yourself — the API
  does it. Pass the search blocks back unchanged in history.
- **Wrong regex mental model.** The regex variant is Python `re.search`, not glob
  or natural language; the BM25 variant is natural language. Don't cross them.

## References

- Tool search tool — platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
- Claude Code MCP + `ENABLE_TOOL_SEARCH` / `alwaysLoad` — code.claude.com/docs/en/mcp
- Advanced tool use — anthropic.com/engineering/advanced-tool-use
- RAG-MCP (arXiv 2505.03275), MCP-Zero (arXiv 2506.01056), tool-gating-mcp (MIT)
