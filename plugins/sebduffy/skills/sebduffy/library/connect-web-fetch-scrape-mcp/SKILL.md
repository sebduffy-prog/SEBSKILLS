---
name: connect-web-fetch-scrape-mcp
category: mcp-connectors
description: >
  Wire up an MCP server to pull web content into Claude — the lightweight Fetch
  server (URL -> markdown, no key) vs Firecrawl (JS-rendered pages, crawl a whole
  site, structured LLM extraction, web search). Registers the server with `claude
  mcp add`, sets the API key, and picks the right tool per job. Use when the user
  says "let Claude read a webpage", "scrape this site", "crawl the docs", "fetch a
  URL into markdown", "add a web scraping MCP", "Firecrawl setup", "extract data
  from these pages", or "why can't Claude open that link".
when_to_use:
  - "User wants Claude to read/summarize a specific public URL and the built-in fetch isn't available or is blocked"
  - "User needs a JavaScript-heavy / SPA page rendered before scraping (React site, infinite scroll, login-gated preview)"
  - "User wants to crawl an entire site or docs section into markdown for RAG"
  - "User wants structured data (prices, contacts, tables) extracted from many URLs into JSON"
  - "User asks to add a web-scraping or web-search MCP server to Claude Code / Desktop"
  - "User asks which to pick: cheap Fetch vs full Firecrawl"
when_not_to_use:
  - "Driving a live browser (clicks, forms, screenshots, auth flows) — use connect-playwright-mcp"
  - "Registering/troubleshooting MCP servers in general (scopes, env, listing) — use register-mcp-servers"
  - "Hitting a documented REST/GraphQL API with a key — use connect-public-api"
  - "Querying GitHub repos/issues/PRs — use connect-github-mcp"
  - "One-off fetch inside this session where the native WebFetch/WebSearch tools already exist — just use those"
keywords: [fetch, firecrawl, web scraping, scrape, crawl, mcp-server-fetch, firecrawl-mcp, url to markdown, extract, spider, headless, robots.txt, web search mcp, firecrawl_scrape, firecrawl_crawl, screenscrape, webfetch]
similar_to: [connect-playwright-mcp, connect-public-api, register-mcp-servers, connect-github-mcp, connect-database-mcp]
inputs_needed:
  - "Which job: read one URL, render a JS page, crawl a site, or extract structured data?"
  - "Client to register with (Claude Code CLI, Claude Desktop, Cursor)"
  - "For Firecrawl: an API key (free tier works keyless for scrape/search) — get one at firecrawl.dev/app/api-keys"
produces: A registered Fetch and/or Firecrawl MCP server + the decision rule and tool-call recipes for pulling web content into Claude
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Connect Web Fetch / Scrape MCP

Two servers, two jobs. Register the smallest one that does the job.

| Need | Use | Key? | Cost |
|------|-----|------|------|
| Grab one static URL as markdown | **Fetch** (`mcp-server-fetch`) | No | Free, local, Python |
| JS-rendered page, site crawl, LLM extraction, web search | **Firecrawl** (`firecrawl-mcp`) | Free tier keyless; key for volume | API/credits |

Rule of thumb: reach for **Fetch** first (it is free and local). Escalate to **Firecrawl**
only when the page needs a real browser, you need many pages, or you want structured JSON out.

## When to use

- Claude needs to read a public webpage and the native WebFetch is unavailable/blocked.
- The page is a SPA / renders content with JS (Fetch returns an empty shell → switch to Firecrawl).
- You want to crawl a docs site or blog into markdown for a knowledge base.
- You want prices / contacts / tables pulled from a list of URLs into typed JSON.

## Prerequisites

- **Fetch server:** Python 3.10+ and `pip` (or `uvx`, bundled with [uv](https://docs.astral.sh/uv/)). No account, no key.
- **Firecrawl server:** Node 18+ (`npx`). Free tier: `firecrawl_scrape`, `firecrawl_search`,
  `firecrawl_interact` work keyless but rate-limited. For crawl/extract/volume, get a key at
  <https://www.firecrawl.dev/app/api-keys> (`fc-...`). Self-hosters set `FIRECRAWL_API_URL`.
- An MCP client: Claude Code CLI (`claude mcp add`), Claude Desktop, or Cursor.

## Recipe 1 — Register the Fetch server (no key)

`uvx` (no install step, recommended):

```bash
claude mcp add fetch -- uvx mcp-server-fetch
```

Or via pip:

```bash
pip install mcp-server-fetch
claude mcp add fetch -- python -m mcp_server_fetch
```

Useful launch flags (append after the server command):

- `--ignore-robots-txt` — the server obeys robots.txt for model-initiated fetches by default; pass this to disable.
- `--user-agent="MyBot/1.0"` — override the UA string.
- `--proxy-url=http://host:port` — route through a proxy.

Claude Desktop equivalent (`claude_desktop_config.json`):

```json
{ "mcpServers": { "fetch": { "command": "uvx", "args": ["mcp-server-fetch"] } } }
```

The one tool it exposes — **`fetch`**:

| Param | Type | Default | Note |
|-------|------|---------|------|
| `url` | string | — | required |
| `max_length` | int | 5000 | chars returned |
| `start_index` | int | 0 | resume long pages by paging the index forward |
| `raw` | bool | false | skip markdown conversion (raw HTML) |

Long page? Loop `start_index` up by `max_length` until the returned chunk is short.

## Recipe 2 — Register Firecrawl (JS render / crawl / extract / search)

CLI one-liner (with key):

```bash
claude mcp add firecrawl -e FIRECRAWL_API_KEY=fc-YOUR_KEY -- npx -y firecrawl-mcp
```

Keyless free tier (scrape/search/interact only):

```bash
claude mcp add firecrawl -- npx -y firecrawl-mcp
```

Remote hosted MCP (no local Node) — add as an HTTP/SSE server:

```bash
# keyless free tier
claude mcp add --transport http firecrawl-remote https://mcp.firecrawl.dev/v2/mcp
# with key (key lives in the URL path)
claude mcp add --transport http firecrawl-remote https://mcp.firecrawl.dev/fc-YOUR_KEY/v2/mcp
```

Claude Desktop / Cursor JSON:

```json
{ "mcpServers": { "firecrawl": {
  "command": "npx", "args": ["-y", "firecrawl-mcp"],
  "env": { "FIRECRAWL_API_KEY": "fc-YOUR_KEY" } } } }
```

### Firecrawl tools you'll actually use

- **`firecrawl_scrape`** — one URL, rendered. Params: `url`, `formats` (`["markdown"]`,
  `["json"]`, `["screenshot"]`…), `onlyMainContent` (strip nav/footer), `waitFor` (ms for JS),
  `maxAge` (serve cached if page younger than N ms — big speedup), `mobile`, `actions`, `schema`
  (+ `redactPII`). Start here for any single page.
- **`firecrawl_map`** — discover all URLs on a site (fast sitemap). Use before a crawl to scope it.
- **`firecrawl_crawl`** — many pages under a path. Params: `url`, `limit` (cap pages — always set it),
  `maxDiscoveryDepth`, `allowExternalLinks`, `deduplicateSimilarURLs`. Async → poll
  **`firecrawl_check_crawl_status`**.
- **`firecrawl_extract`** — structured JSON from one or many URLs against a `schema`; LLM does the pulling.
- **`firecrawl_search`** — web search, optionally scraping each result. Fetch's job but with a query.

## Recipe 3 — Pick the tool, in-session

Once registered, drive it in natural language; Claude routes to the tool:

- "Read <url> and summarize" → `fetch` (or `firecrawl_scrape` if it came back empty).
- "This React page is blank when fetched" → `firecrawl_scrape` with `waitFor: 3000`, `onlyMainContent: true`.
- "Crawl docs.example.com into markdown, max 50 pages" → `firecrawl_map` then `firecrawl_crawl` with `limit: 50`.
- "Pull name + price + SKU from these 20 product URLs as JSON" → `firecrawl_extract` with a schema.

## Verify

```bash
claude mcp list                       # server shows "connected"
```

Smoke test inside Claude: ask *"Use the fetch tool to read https://example.com and give me the H1."*
It should return "Example Domain". For Firecrawl, ask it to `firecrawl_scrape`
<https://firecrawl.dev> and confirm rendered markdown (not an empty JS shell) comes back.

## Pitfalls

- **Fetch returns an empty/near-empty body on a real site** → the page is JS-rendered. Switch to
  `firecrawl_scrape` (Fetch does not run a browser).
- **Firecrawl crawl runs forever / burns credits** — always set `limit`, and `firecrawl_map` first
  to see scope. Crawl is async: you must poll `firecrawl_check_crawl_status`, not wait inline.
- **Free tier limits** — keyless Firecrawl is rate-limited and excludes `crawl`/`extract`. Add a key for those.
- **robots.txt blocks model fetches** on the Fetch server by default. Only pass `--ignore-robots-txt`
  where you have the right to scrape; respect terms of service and rate limits either way.
- **Never hardcode `FIRECRAWL_API_KEY`** in committed config. Use the `-e`/`env` mechanism or a
  secrets manager; the remote-MCP form puts the key in the URL, so treat that URL as a secret.
- **Wrong tool for auth/interaction** — logins, clicking through flows, screenshots of stateful pages
  belong to Playwright, not these. Firecrawl `actions`/`interact` handles light interactions only.
- **Truncated long pages** on Fetch — it caps at `max_length` (5000). Page `start_index` forward to
  read the rest, or use `firecrawl_scrape` which returns the full page.

## Sources

- Fetch: <https://github.com/modelcontextprotocol/servers/tree/main/src/fetch>
- Firecrawl: <https://github.com/firecrawl/firecrawl-mcp-server>
