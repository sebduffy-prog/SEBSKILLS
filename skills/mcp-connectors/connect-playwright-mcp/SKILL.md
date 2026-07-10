---
name: connect-playwright-mcp
category: mcp-connectors
description: >
  Register and drive a real browser over MCP with Microsoft's Playwright MCP server (@playwright/mcp).
  Navigate, click, fill forms, and read pages via the structured accessibility tree (not screenshots),
  reuse logged-in sessions with storage-state auth, scrape data, run E2E-style flows, save screenshots/PDFs/traces.
  Use when the user says "browser automation", "control a browser", "Playwright MCP", "scrape a site",
  "log in and click through", "fill this form on a page", "automate a web workflow", or "snapshot the DOM".
when_to_use:
  - "User wants Claude to drive a live browser: navigate, click, type, submit forms, extract data"
  - "User asks to install/configure the Playwright MCP server for Claude Code or Claude Desktop"
  - "A task needs an authenticated session reused (log in once, save storage state, replay it)"
  - "User wants structured accessibility-tree snapshots or refs instead of pixel screenshots"
  - "Scraping / crawling JS-heavy pages that plain HTTP fetch can't render"
  - "Recording a browser flow to a trace, screenshot, or PDF for evidence"
when_not_to_use:
  - "Static HTML / JSON with no JS or login → use connect-web-fetch-scrape-mcp (lighter, no browser)"
  - "Calling a documented REST/GraphQL endpoint directly → use connect-public-api"
  - "Wiring/registering ANY MCP server generically (transport, scopes) → use register-mcp-servers"
  - "GitHub repo/PR/issue automation → use connect-github-mcp"
  - "Writing Playwright test files locally (not via MCP) → use the webapp-testing skill"
keywords: [playwright, playwright-mcp, browser automation, headless browser, accessibility tree, browser_snapshot, browser_click, storage state, scraping, e2e, chromium, webkit, firefox, mcp server, session auth, screenshot, form fill, playright, puppeteer alternative]
similar_to: [connect-web-fetch-scrape-mcp, register-mcp-servers, connect-github-mcp, connect-database-mcp, connect-public-api]
inputs_needed:
  - "Target URL(s) and the goal (scrape which fields, click which flow, fill which form)"
  - "Whether login is required — if so, how to authenticate (interactive once, or an existing storage-state file)"
  - "Headless vs headed, and which browser (chrome/chromium default, firefox, webkit, msedge)"
  - "Where output (screenshots/PDF/trace/storage-state) should be written"
produces: A registered playwright MCP server plus a working browser-automation recipe (navigate → snapshot → act → extract), with reusable storage-state auth.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Connect Playwright MCP

Drive a real Chromium/Firefox/WebKit browser from Claude over MCP using Microsoft's
[`@playwright/mcp`](https://github.com/microsoft/playwright-mcp). It exposes structured
**accessibility-tree snapshots** (with element `ref`s) rather than pixels, so the model acts
through concise, deterministic references — fast, cheap, and robust versus screenshot-clicking.

## When to use

Use for anything needing a live, JS-executing browser: authenticated scraping, multi-step
form flows, click-throughs, DOM extraction, or capturing screenshots/PDFs/traces. If the page
is static HTML or a plain API, prefer the lighter fetch/API skills (see `when_not_to_use`).

## Prerequisites

- **Node.js 18+** and `npx` on PATH. The server is pulled on first run via `npx @playwright/mcp@latest`.
- Browser binaries download automatically on first launch. If a corporate proxy blocks that,
  pre-install: `npx playwright install chrome` (or `chromium`/`firefox`/`webkit`).
- No API key. Auth to *target sites* is handled by browser session state, not the server.
- Verify Claude Code sees MCP servers: `claude mcp list`.

## Register the server

Pick ONE transport. Default (persistent profile, headed) is fine for interactive login work.

```bash
# Claude Code — simplest
claude mcp add playwright npx @playwright/mcp@latest

# Headless + isolated + preloaded auth (good for automation/CI)
claude mcp add playwright -- npx @playwright/mcp@latest \
  --headless --isolated --storage-state=/abs/path/auth.json \
  --output-dir=/abs/path/pw-out
```

Or edit config JSON directly (`~/.claude.json` project block, or Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--headless", "--isolated",
               "--storage-state=/abs/path/auth.json"]
    }
  }
}
```

Restart / reconnect, then confirm: `claude mcp list` should show `playwright` as connected.
For deep scope/transport questions (user vs project vs local, SSE/HTTP), use `register-mcp-servers`.

### Flags that matter

| Flag | Why |
|------|-----|
| `--headless` | No visible window (default is headed). Use headed for one-time interactive login. |
| `--browser chrome\|chromium\|firefox\|webkit\|msedge` | Engine choice; `chrome` is default. |
| `--isolated` | Fresh in-memory profile per session; combine with `--storage-state` to seed auth. |
| `--storage-state=<path>` | Load cookies + localStorage from a saved auth file into an isolated context. |
| `--user-data-dir=<path>` | Persistent profile (auth survives across sessions). One instance at a time. |
| `--device "iPhone 15"` | Emulate a device profile. |
| `--viewport-size "1280,720"` | Fixed viewport. |
| `--save-session` / `--save-trace` | Persist the MCP session / a Playwright trace to `--output-dir`. |
| `--output-dir=<path>` | Where screenshots, PDFs, traces, storage dumps land. |
| `--caps vision,pdf,devtools,network,storage,testing` | Opt-in extra tool groups (see below). |
| `--allowed-origins` / `--blocked-origins` | Restrict which hosts the browser may hit. |

## Core tools (always available)

`browser_navigate`, `browser_navigate_back`, `browser_snapshot` (accessibility tree — **use this, not screenshots, to find element `ref`s**), `browser_click`, `browser_type`, `browser_fill_form`, `browser_hover`, `browser_press_key`, `browser_select_option`, `browser_drag`, `browser_file_upload`, `browser_wait_for`, `browser_take_screenshot`, `browser_evaluate` (run JS in page), `browser_console_messages`, `browser_network_requests`, `browser_handle_dialog`, `browser_tabs`, `browser_resize`, `browser_close`.

Opt-in groups via `--caps`: **storage** (`browser_storage_state`, `browser_set_storage_state`, cookie/localStorage/sessionStorage get/set), **vision** (coordinate clicks `browser_mouse_click_xy`), **pdf** (`browser_pdf_save`), **devtools**, **network** (`browser_route`/`browser_unroute`), **testing** (`browser_verify_text_visible`, `browser_verify_element_visible`, etc.).

## Recipe 1 — Navigate, snapshot, act, extract

The disciplined loop: **snapshot to see the page → act on a `ref` from that snapshot → re-snapshot**.

```
1. browser_navigate  { url: "https://example.com/search" }
2. browser_snapshot                          # returns roles + text + ref= handles
3. browser_type      { ref: "<ref of search box>", text: "playwright mcp", submit: true }
4. browser_snapshot                          # read results
5. browser_click     { ref: "<ref of first result link>" }
6. browser_evaluate  { function: "() => document.querySelector('h1')?.innerText" }   # extract
```

Never guess a `ref` — always take it from the latest `browser_snapshot`. If content is
async, insert `browser_wait_for { text: "…" }` (or `{ time: N }`) before acting.

## Recipe 2 — Log in once, reuse the session (storage-state auth)

This is the key pattern for authenticated scraping. Do the login **headed** once, dump state,
then run automation **headless + isolated** off that file.

```
# One-time (headed server, no --storage-state):
1. browser_navigate  { url: "https://app.example.com/login" }
2. # let the user log in interactively in the visible window (or type creds via browser_type)
3. browser_storage_state { filename: "auth.json" }   # writes to --output-dir  (needs --caps=storage)
```

Then reconfigure the server with `--headless --isolated --storage-state=/abs/.../auth.json`.
Every future session starts already logged in. Treat `auth.json` as a **secret** (cookies/tokens):
keep it out of git, restrict perms (`chmod 600`), and refresh when sessions expire.

If you can't add `--caps=storage`, alternatively persist auth with `--user-data-dir=/abs/profile`
— the whole profile (including login) survives across runs.

## Recipe 3 — Fill and submit a form

```
1. browser_navigate  { url: "…/contact" }
2. browser_snapshot
3. browser_fill_form { fields: [
     { ref: "<name>",  value: "Ada Lovelace" },
     { ref: "<email>", value: "ada@example.com" },
     { ref: "<msg>",   value: "Hello" } ] }
4. browser_click     { ref: "<submit button ref>" }
5. browser_wait_for  { text: "Thanks" }      # confirm success
```

## Verify

- `claude mcp list` → `playwright` connected; tools like `browser_navigate` appear.
- Smoke test: `browser_navigate` to `https://example.com`, then `browser_snapshot` — you
  should get an accessibility tree containing "Example Domain".
- Auth test: with `--storage-state` set, navigate to a members-only URL and snapshot —
  you should see logged-in chrome (account name), not the login form.
- Screenshot proof: `browser_take_screenshot` writes a PNG under `--output-dir`.

## Pitfalls

- **Persistent-profile lock**: a `--user-data-dir` profile allows only one browser at a time.
  Run parallel clients with `--isolated` (each with its own `--storage-state`) instead.
- **Stale refs**: `ref`s are valid for the snapshot they came from. After any navigation or
  DOM change, re-run `browser_snapshot` before clicking, or you'll target the wrong node.
- **Snapshot > screenshot**: default to `browser_snapshot`. Only use vision/coordinate tools
  (`--caps=vision`) for canvas/pixel UIs the a11y tree can't describe.
- **First-run download**: initial `npx` fetch + browser binary download can take a minute and
  needs network; behind a proxy, pre-run `npx playwright install`.
- **Secrets leak**: storage-state files and `--user-data-dir` contain live session tokens.
  Never commit them; pass credentials via `--secrets`/env, not inline in shared config.
- **Origin scope**: for untrusted scraping, set `--allowed-origins`/`--blocked-origins` so the
  agent can't wander to arbitrary hosts.
- **`browser_evaluate`/`browser_run_code_unsafe`** run arbitrary JS in the page — only on
  trusted targets; don't paste untrusted script.
- **`@latest` drift**: pin a version (`@playwright/mcp@0.x`) in CI so tool names/flags don't
  shift under you between runs.

## Source

Grounded against microsoft/playwright-mcp README (July 2026). Authored fresh for SEBSKILLS.
