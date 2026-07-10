---
name: register-mcp-servers
category: mcp-connectors
description: >
  Install, register, and manage MCP servers in Claude Code, Claude Desktop, and remote clients. Use when a user says "add an MCP server", "connect my MCP", "set up .mcp.json", "share MCP with my team", "why won't my MCP server connect", "authenticate my MCP", "import from Claude Desktop", or "package a .mcpb bundle". Covers scopes (local/project/user), stdio vs HTTP vs SSE transports, OAuth login, env vars, headers, and connection troubleshooting.
when_to_use:
  - "User wants to add a remote or local MCP server to Claude Code (`claude mcp add`)"
  - "User asks to share MCP config with their team via a checked-in .mcp.json"
  - "An MCP server shows as failed, pending, or needs-auth in /mcp and won't connect"
  - "User needs OAuth login for a cloud MCP server (Sentry, Notion, Stripe, GitHub)"
  - "User wants to import servers already configured in Claude Desktop"
  - "User wants to package a local server as a one-click .mcpb bundle for Claude Desktop"
when_not_to_use:
  - "Building an MCP server from scratch in Python/TypeScript — use the mcp-builder skill"
  - "Wiring the specific GitHub remote server end-to-end — use connect-github-mcp"
  - "Wiring a Postgres/MySQL DB server — use connect-database-mcp"
  - "Wiring Playwright browser automation — use connect-playwright-mcp"
  - "Wiring a generic REST/OpenAPI or fetch/scrape server — use connect-public-api or connect-web-fetch-scrape-mcp"
keywords: [mcp, model context protocol, claude mcp add, .mcp.json, mcp server, register mcp, add-json, add-from-claude-desktop, mcp scope, stdio, streamable-http, sse, oauth, /mcp, mcpb, dxt, mcp-publisher, connector, mcp login, mcp connection failed, spawn enoent]
similar_to: [connect-github-mcp, connect-database-mcp, connect-playwright-mcp, connect-web-fetch-scrape-mcp, connect-public-api]
inputs_needed:
  - "Which client: Claude Code CLI, Claude Desktop, or both"
  - "The server: a remote URL (http/sse) or a local launch command (stdio, e.g. `npx -y pkg`)"
  - "Scope: private-to-you (local), shared-with-team (project), or all-your-projects (user)"
  - "Any secrets — API keys/tokens (env vars or headers), or whether the server uses OAuth"
produces: A registered, connected MCP server (in ~/.claude.json or a checked-in .mcp.json), verified via `claude mcp list` / `/mcp`
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Register & Manage MCP Servers

Add, scope, authenticate, and troubleshoot MCP servers for Claude Code and Claude Desktop.
Grounded against the current `claude mcp` CLI (code.claude.com/docs/en/mcp).

## When to use

Reach for this when the ask is about the *plumbing* of connecting a server — the `claude mcp`
commands, `.mcp.json`, scopes, OAuth, `.mcpb` bundles, or a connection that won't come up.
For wiring one *specific* named service end-to-end, prefer the matching `connect-*` sibling.

## Prerequisites

- **Claude Code CLI** installed (`claude --version`). Most commands here are `claude mcp …`.
- For **stdio** servers: the runtime the server needs on PATH — usually `node`+`npx` or
  `python`/`uv`. Verify with `which npx` / `which uvx` before adding.
- For **remote** servers: the server's HTTPS URL, and either a token (header/env) or OAuth.
- For **`.mcpb` bundles**: `npm i -g @anthropic-ai/mcpb` (the `mcpb` CLI) and Claude Desktop.
- Ask before running: **which client, which transport, which scope, what secrets** (see
  `inputs_needed`). Never hardcode a real token into a checked-in file — use `${VAR}` expansion.

## Recipes

### 1. Add a remote HTTP server (the common case)

HTTP (a.k.a. `streamable-http`) is the recommended remote transport.

```bash
# Basic: claude mcp add --transport http <name> <url>
claude mcp add --transport http notion https://mcp.notion.com/mcp

# With a static bearer token (skip if the server uses OAuth)
claude mcp add --transport http github https://api.githubcopilot.com/mcp/ \
  --header "Authorization: Bearer YOUR_GITHUB_PAT"
```

`-t` is short for `--transport`, `-H` for `--header`. Then authenticate if needed (recipe 5)
and verify with `claude mcp list`.

### 2. Add a local stdio server

Stdio servers run as a local child process. **Everything after `--` is the launch command,
passed untouched** — put Claude's own flags (`--transport`, `--env`, `--scope`) *before* `--`.

```bash
# claude mcp add [options] <name> -- <command> [args...]
claude mcp add --env AIRTABLE_API_KEY=YOUR_KEY --transport stdio airtable \
  -- npx -y airtable-mcp-server

# Example: read-only Postgres
claude mcp add --transport stdio db \
  -- npx -y @bytebase/dbhub --dsn "postgresql://readonly:pass@host:5432/db"
```

Gotcha: `--env` takes `KEY=value` pairs; put at least one other flag between the last `--env`
and the server *name*, or the CLI reads the name as another pair and rejects it.

### 3. Choose a scope (who sees the server)

Pass `-s`/`--scope`. Precedence when a name is defined twice: **local > project > user >
plugin > claude.ai connector**. The whole entry from the winning scope is used (no field merge).

| Scope | Flag | Loads in | Shared | Stored in |
|-------|------|----------|--------|-----------|
| **local** (default) | `--scope local` | current project only | no | `~/.claude.json` |
| **project** | `--scope project` | current project only | yes, via VCS | `.mcp.json` in repo root |
| **user** | `--scope user` | all your projects | no | `~/.claude.json` |

```bash
claude mcp add --transport http paypal --scope project https://mcp.paypal.com/mcp   # team-shared
claude mcp add --transport http hubspot --scope user https://mcp.hubspot.com/anthropic  # everywhere
```

### 4. Team-shared `.mcp.json` (checked into git)

`--scope project` writes/updates `.mcp.json` at the repo root. Format — **an entry with a
`url` MUST carry a `type`**, or Claude Code treats it as stdio and skips it:

```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": { "Authorization": "Bearer ${API_KEY}" }
    },
    "local-tool": {
      "command": "npx",
      "args": ["-y", "some-mcp-server"],
      "env": { "CACHE_DIR": "/tmp" }
    }
  }
}
```

- **Never commit real secrets** — use `${VAR}` / `${VAR:-default}`. Expansion works in
  `command`, `args`, `env`, `url`, and `headers`. An unset var with no default fails parsing.
- On first use Claude Code **prompts each teammate to approve** project servers; until then they
  show as `⏸ Pending approval` in `claude mcp list`. Reset approvals with
  `claude mcp reset-project-choices`. A cloned repo can't auto-approve its own servers until the
  workspace is trusted.

### 5. Authenticate a remote server (OAuth)

Many cloud servers need OAuth 2.0. Claude Code flags a server for auth when it returns `401`/`403`.

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
# then, inside a Claude Code session:
/mcp            # opens the browser login; pick the server → Authenticate
# or straight from the shell (v2.1.186+):
claude mcp login sentry
claude mcp logout sentry        # clear stored creds
claude mcp login sentry --no-browser   # SSH/headless: prints URL, paste callback back
```

- Tokens are stored in the OS keychain and auto-refresh. Use **Clear authentication** in `/mcp`
  to revoke. If you set a static `Authorization` header *and* it's rejected, Claude reports a
  hard failure instead of falling back to OAuth — drop the header to use OAuth.
- Server needs a **fixed callback port** or **pre-registered client**? Use
  `--callback-port 8080`, and `--client-id … --client-secret` (masked prompt; or
  `MCP_CLIENT_SECRET=… ` for CI). These flags apply to http/sse only.

### 6. Add from raw JSON / import from Desktop / claude.ai

```bash
# Paste a vendor's JSON snippet directly (type is required for remote entries)
claude mcp add-json weather '{"type":"http","url":"https://api.weather.com/mcp","headers":{"Authorization":"Bearer token"}}'

# WebSocket servers can only be added via JSON (no --transport ws):
claude mcp add-json events '{"type":"ws","url":"wss://mcp.example.com/socket","headers":{"Authorization":"Bearer TOKEN"}}'

# Import everything you already set up in Claude Desktop (macOS / WSL only)
claude mcp add-from-claude-desktop            # interactive multi-select
claude mcp add-from-claude-desktop --scope user
```

Servers you added at **claude.ai/customize/connectors** appear automatically in Claude Code's
`/mcp` when you're logged in with your claude.ai account (not when `ANTHROPIC_API_KEY` or a
Bedrock/Vertex provider is the active auth). Disable with `"disableClaudeAiConnectors": true`.

### 7. Package a local server as a `.mcpb` bundle (Claude Desktop one-click)

`.mcpb` (the successor to `.dxt`) is a zip of a local MCP server + `manifest.json` for one-click
install in Claude Desktop.

```bash
npm i -g @anthropic-ai/mcpb
cd my-server            # folder containing the runnable server
mcpb init               # interactive → writes manifest.json
mcpb pack               # → my-server.mcpb
# Install: open Claude Desktop → Settings → Extensions → drag the .mcpb in
```

`manifest.json` declares `name`, `version`, a `server` block (`type: "node"|"python"|"binary"`
+ entry point), and optional `user_config` fields (e.g. API keys) that Desktop prompts for and
injects at runtime. Existing `.dxt` extensions still load; use `.mcpb` for anything new.

### 8. Manage & remove

```bash
claude mcp list            # all servers + connection health / ⏸ Pending / ✗ Rejected
claude mcp get github      # one server's config + OAuth status
claude mcp remove github
claude mcp serve           # run Claude Code ITSELF as a stdio MCP server for other apps
```

## Verify

1. `claude mcp list` → the server shows **✔ Connected** (not `Failed`, `⏸ Pending approval`,
   or `needs authentication`).
2. Start `claude`, run `/mcp` → server is listed with a **tool count > 0**. A server that
   advertises tools but exposes none is flagged there.
3. Trigger a real tool call (e.g. ask a question the server answers). With tool search on (the
   default), tools surface via `ToolSearch` on demand — so "I don't see the tools" is normal
   until Claude needs them; it doesn't mean the server failed.
4. For project scope: confirm `.mcp.json` is at the repo root and teammates get the approval
   prompt on first `claude` run.

## Pitfalls

- **`url` with no `type`** → skipped as a broken stdio entry. Always set `"type": "http"`
  (or `sse`/`ws`) on remote JSON entries. (Older builds mis-reported this as
  `command: expected string, received undefined`.)
- **Flags after `--` on stdio** → swallowed by the server. Put `--transport/--env/--scope`
  *before* `--`; only the launch command goes after.
- **`spawn npx ENOENT` / `spawn claude ENOENT`** → the executable isn't on the PATH Claude
  Code sees. Use an absolute path (`which npx`, `which claude`) in `command`.
- **Secret committed to `.mcp.json`** → security incident. Use `${VAR}` expansion and keep the
  real value in your shell/CI env, never in the tracked file.
- **Project server stuck at `⏸ Pending approval`** → run `claude` interactively and accept the
  workspace-trust + server-approval dialogs; a cloned repo can't self-approve.
- **claude.ai connectors missing from `/mcp`** → your active auth isn't claude.ai. Run
  `/status`, unset `ANTHROPIC_API_KEY`/`apiKeyHelper`, then `/login` with your claude.ai account.
- **Slow / hung startup** → tune with `MCP_TIMEOUT` (startup) and a per-server `"timeout"` ms
  field (tool calls). Large outputs warn at 10k tokens; raise with `MAX_MCP_OUTPUT_TOKENS`.
- **SSE is deprecated** — prefer HTTP wherever the vendor offers it.
- **Publishing to the public registry** (namespace `io.github.user/name`, `server.json`,
  `mcp-publisher`) is a separate discovery concern — that's authoring/distribution, closer to
  the mcp-builder skill than to wiring a server into your own client.
