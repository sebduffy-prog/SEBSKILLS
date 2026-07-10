---
name: connect-github-mcp
category: mcp-connectors
description: >
  Wire up GitHub's OFFICIAL MCP server so Claude can drive repos, issues, PRs, code search,
  and Actions natively — no `gh` binary, no shelling out. Covers the one-line remote HTTP
  connection (api.githubcopilot.com/mcp), PAT + OAuth auth, Docker/local fallback, toolset
  scoping, and read-only lockdown. Reach for this when someone says "connect Claude to
  GitHub", "add the GitHub MCP server", "set up github mcp", "let Claude open PRs / triage
  issues / read my repo", "GitHub tools in Claude Code", or wants agentic GitHub without CLI
  scripting. Produces a working `claude mcp` connection plus the high-value tool calls.
when_to_use:
  - "You want Claude to read/create issues, open or review PRs, or search code without you running gh commands"
  - "Someone says 'add the GitHub MCP server' or 'connect Claude to my GitHub'"
  - "You need repo/Actions/Dependabot context inside Claude Code and prefer a server over ad-hoc gh calls"
  - "Setting up a read-only GitHub connection so an agent can browse but not push"
  - "Scoping which GitHub capabilities (toolsets) an agent can touch"
  - "Verifying/debugging a flaky or unauthenticated GitHub MCP connection (403/401, wrong toolset)"
when_not_to_use:
  - "One-off git/GitHub actions where a single `gh` or `git` command is simpler — just run it, no server needed"
  - "Registering/managing MANY MCP servers or editing .mcp.json broadly → register-mcp-servers"
  - "Connecting to a database over MCP → connect-database-mcp"
  - "Browser automation / scraping a GitHub web page → connect-playwright-mcp or connect-web-fetch-scrape-mcp"
  - "Wrapping some other REST API as tools → connect-public-api"
keywords: [github mcp, github-mcp-server, connect github, claude mcp add, api.githubcopilot.com, personal access token, PAT, oauth, toolsets, pull requests, issues, code search, actions, dependabot, read-only, x-mcp-toolsets, ghcr.io, mcp server github, agentic github]
similar_to: [register-mcp-servers, connect-database-mcp, connect-playwright-mcp, connect-web-fetch-scrape-mcp, connect-public-api]
inputs_needed:
  - "Remote (hosted, recommended) or local Docker? Remote needs zero infra"
  - "Auth method: OAuth browser login (local Docker) or a GitHub PAT (either mode)"
  - "If PAT: a fine-grained or classic token with the scopes you actually need (repo, read:org, workflow…)"
  - "Which toolsets to enable (default = context+repos+issues+PRs+users); read-only or read-write?"
  - "Config scope: local (this project), project (shared .mcp.json), or user (all your projects)"
produces: A live `github` MCP connection in Claude Code (verified via `claude mcp list` / `/mcp`) exposing GitHub repo/issue/PR/Actions tools
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Connect the GitHub MCP Server

GitHub ships an **official MCP server** (`github/github-mcp-server`). Connect it once and Claude
gets native tools for repos, issues, pull requests, code search, Actions, Dependabot, and more —
no `gh` shell-outs, no bespoke API glue. Two ways to run it:

- **Remote (hosted by GitHub)** — `https://api.githubcopilot.com/mcp/`. Zero infra, always
  current. **Default choice.**
- **Local (Docker)** — `ghcr.io/github/github-mcp-server`. Use for air-gapped/self-hosted
  needs, GitHub Enterprise, or when you want OAuth-in-memory tokens.

## When to use

Reach for this the moment a task involves *repeated* GitHub work — triaging issues, opening a
batch of PRs, code-searching across repos, watching a workflow run. For a single `gh pr view`
just run the command; the server earns its keep when the agent needs GitHub as an ongoing
capability, not a one-shot.

## Prerequisites

- **Claude Code CLI** (`claude`). Check version: `claude --version` — the `add-json` syntax
  below needs **2.1.1+**; older versions use the `--transport http` form (also shown).
- **A GitHub account.** Remote server also works with GitHub Enterprise Cloud.
- **Auth**, one of:
  - **PAT** — a [fine-grained or classic Personal Access Token](https://github.com/settings/personal-access-tokens).
    Grant only what you need: `repo` (or fine-grained Contents/Issues/Pull requests),
    `read:org`, `workflow` for Actions. Least privilege.
  - **OAuth** — browser login, token kept in memory (local Docker path only).
- **Docker** — only for the local path (`docker --version`).

## Recipe 1 — Remote server with a PAT (recommended)

Store the token out of shell history first:

```bash
# put GITHUB_PAT=ghp_xxx in a .env you do NOT commit
export GITHUB_PAT="$(grep '^GITHUB_PAT=' .env | cut -d '=' -f2-)"
```

**Claude Code 2.1.1+** (`add-json`):

```bash
claude mcp add-json github \
  '{"type":"http","url":"https://api.githubcopilot.com/mcp/","headers":{"Authorization":"Bearer '"$GITHUB_PAT"'"}}'
```

**Claude Code 2.1.0 or earlier** (`--transport http`; flags go BEFORE the name):

```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/ \
  -H "Authorization: Bearer $GITHUB_PAT"
```

Add `--scope user` (all your projects) or `--scope project` (shared, writes `.mcp.json`) to
either command; default is `local` (this project only). **Never commit a PAT** — with
`--scope project`, reference an env var, don't inline the secret.

## Recipe 2 — Local Docker with OAuth (browser login)

No token to manage; you approve in the browser on first use, token lives in memory only:

```bash
claude mcp add github -e GITHUB_OAUTH_CALLBACK_PORT=8085 -- \
  docker run -i --rm -p 127.0.0.1:8085:8085 -e GITHUB_OAUTH_CALLBACK_PORT \
  ghcr.io/github/github-mcp-server
```

Local Docker with a PAT instead of OAuth:

```bash
claude mcp add github -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PAT -- \
  docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN \
  ghcr.io/github/github-mcp-server
```

`GITHUB_PERSONAL_ACCESS_TOKEN` takes precedence over OAuth when both are present.

## Recipe 3 — Scope the toolsets (least tool surface)

The server groups tools into **toolsets**: `context, repos, issues, pull_requests, actions,
code_security, dependabot, discussions, gists, git, labels, notifications, orgs, projects,
secret_protection, security_advisories, stargazers, users`. Fewer enabled = fewer tools in
Claude's context = sharper behaviour.

**Remote** — set headers in the JSON (comma-separated, no spaces):

```bash
claude mcp add-json github '{
  "type":"http",
  "url":"https://api.githubcopilot.com/mcp/",
  "headers":{
    "Authorization":"Bearer '"$GITHUB_PAT"'",
    "X-MCP-Toolsets":"context,repos,issues,pull_requests",
    "X-MCP-Readonly":"false"
  }
}'
```

- `X-MCP-Readonly: true` exposes **only read tools** — the safe default for an agent that
  should browse but never push, comment, or merge. (Any value other than empty/`false`/`0`/
  `no`/`off` counts as true.)
- `X-MCP-Lockdown: true` hides issue/PR body details from users without push access (prompt-
  injection defence on public repos).

**Local Docker** — same idea via env/flags:

```bash
claude mcp add github \
  -e GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PAT \
  -e GITHUB_TOOLSETS="context,repos,issues,pull_requests" \
  -- docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN -e GITHUB_TOOLSETS \
  ghcr.io/github/github-mcp-server --read-only
```

(`--read-only` or `-e GITHUB_READ_ONLY=1` for the local read-only lockdown.)

## High-value tool calls (once connected)

Ask Claude in natural language; it picks the tool. Representative capabilities:

- **Repos** — `get_file_contents`, `search_code`, `list_commits`, `create_or_update_file`,
  `create_branch`, `push_files`. "Show me `src/auth.ts` on `main`." "Grep the org for `TODO:sec`."
- **Issues** — `list_issues`, `get_issue`, `create_issue`, `add_issue_comment`, `update_issue`.
  "Open an issue titled X on owner/repo with these labels."
- **Pull requests** — `create_pull_request`, `get_pull_request_diff`, `list_pull_requests`,
  `create_pending_pull_request_review` + `submit_pull_request_review`, `merge_pull_request`.
  "Open a PR from my branch to main and summarise the diff." "Review PR #42."
- **Actions** — `list_workflow_runs`, `get_workflow_run`, `get_job_logs`, `rerun_failed_jobs`.
  "Why did the last CI run on #42 fail?" (pulls failing-job logs directly).
- **Notifications / Dependabot / security** — triage inbox, list alerts, read advisories.

## Verify

```bash
claude mcp list          # github should show ✓ Connected
claude mcp get github     # confirms url/headers/scope (secrets redacted)
```

Inside a Claude Code session, run `/mcp` to see `github` and its tool count. Then smoke-test:
ask *"list my 5 most recently updated repos"* — a real list back means auth + toolset are live.

## Pitfalls

- **401/403 on every call** → bad or expired PAT, or missing scope. Fine-grained tokens must
  grant the specific permission (Issues, Pull requests, Contents) AND list the target repos/org.
  Regenerate and re-run `add-json`.
- **Trailing slash matters** — use `https://api.githubcopilot.com/mcp/`. Some setups 404 without it.
- **Flag ordering** — with `claude mcp add ... --transport http`, all `--flags` come **before**
  the server name; put them after and the command mis-parses.
- **Secret leakage** — never inline a PAT in a `--scope project` `.mcp.json` (it gets committed).
  Use `--scope user`/`local`, or reference an env var. Rotate any PAT that ever hit a repo.
- **Too many tools** → context bloat and worse tool selection. Trim with `X-MCP-Toolsets` /
  `GITHUB_TOOLSETS` to just what the task needs.
- **`add-json` unknown / errors** → your Claude Code is < 2.1.1. Use the `--transport http` form.
- **Remote can't reach GitHub Enterprise Server (self-hosted)** → remote hosts GitHub.com/EC only;
  for GHES use local Docker with `-e GITHUB_HOST=https://ghe.example.com`.
- **Duplicate/old entry** → `claude mcp remove github` then re-add cleanly.
