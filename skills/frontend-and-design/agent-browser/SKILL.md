---
name: agent-browser
description: >
  Drive a real Chrome browser from the CLI to view, test, screenshot and
  debug web pages — the visual-QA loop for any frontend work. Use whenever
  you need to actually SEE a page render (catch layout overflow/overlap,
  broken styles, console errors), click through a flow, capture screenshots,
  or run JS against a live page — local (file:// or a dev server) or a deployed
  URL (Vercel, HF Spaces). Built for AI agents: snapshot returns an
  accessibility tree with stable refs (@e1, @e2) so element selection is
  deterministic. Trigger on: "view the page", "screenshot the site", "test in
  a browser", "check the layout", "does it render", "click through the UI",
  "debug the frontend", "verify the deploy", "agent-browser", or any request to
  visually verify/interact with a web UI. Pairs with frontend-design,
  vccp-media-design, design-approval-gate and webapp-testing.
metadata:
  type: reference
category: frontend-and-design
when_to_use:
  - Needing to actually SEE a page render and catch layout overflow, overlap, or broken styles
  - Screenshotting a local (file:// or dev server) or deployed site (Vercel, HF Spaces)
  - Clicking through a UI flow deterministically using stable accessibility-tree refs
  - Running JS against a live page or reading console errors
  - Verifying a deploy renders correctly as a visual-QA loop for frontend work
when_not_to_use:
  - Writing scripted Playwright suites for a local app — use webapp-testing
  - Deep DOM/network/performance inspection via DevTools protocol — use browser-testing-with-devtools
  - Final visual sign-off before shipping — use design-approval-gate
keywords:
  - browser automation
  - chrome
  - screenshot
  - visual qa
  - accessibility tree
  - snapshot ref
  - cli
  - headless
  - deploy verification
  - console errors
  - layout overflow
  - click through
  - live page
  - dev server
  - vercel
  - hugging face spaces
similar_to:
  - webapp-testing
  - browser-qa
  - browser-testing-with-devtools
  - design-approval-gate
inputs_needed: The URL or local path to load (file://, dev server, or deployed) and what to verify or interact with.
produces: Screenshots plus an accessibility-tree snapshot with stable element refs for a visual-QA loop.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# agent-browser — browser automation CLI for visual frontend QA

[`vercel-labs/agent-browser`](https://github.com/vercel-labs/agent-browser) is a
fast native **Rust** CLI that drives Chrome for AI agents. No Node daemon (pure
Rust + direct CDP). Its killer feature for LLMs: `snapshot` returns an
accessibility tree with **deterministic refs** (`@e1`, `@e2`), so you select
elements by ref instead of guessing selectors. It can also screenshot, run JS,
intercept network, and expose an **MCP server**.

Use it to close the loop on frontend work — *actually see the page* and catch
what static code review can't: overflow, overlap, broken fonts, console errors,
empty/error states, and whether a flow actually works end to end.

## Install

Pick whichever the machine supports:

```bash
npm install -g agent-browser        # if Node is present
brew install agent-browser          # if Homebrew is present
cargo install agent-browser         # if Rust is present
```

**No package manager? Download the prebuilt binary directly** (how it was set up
on this Mac — no node/brew/cargo needed):

```bash
mkdir -p ~/.local/bin
URL=$(curl -s https://api.github.com/repos/vercel-labs/agent-browser/releases/latest \
  | grep -oE '"browser_download_url": *"[^"]*agent-browser-darwin-arm64"' \
  | grep -oE 'https://[^"]*' | head -1)            # swap -darwin-arm64 for your platform
curl -sL "$URL" -o ~/.local/bin/agent-browser && chmod +x ~/.local/bin/agent-browser
~/.local/bin/agent-browser --version
~/.local/bin/agent-browser install                 # one-time: downloads Chrome for Testing
```
Platforms in releases: `agent-browser-{darwin-arm64,darwin-x64,linux-arm64,linux-musl-arm64}` (+ x64). Linux: `agent-browser install --with-deps`.

## Core workflow (snapshot + ref)

```bash
agent-browser open <url|file://path/to/index.html>   # navigate
agent-browser snapshot -i                            # interactive elements with refs (@e1…)
agent-browser click @e1                               # act on a ref
agent-browser fill  @e2 "some text"
agent-browser screenshot out.png                     # capture (then Read the PNG to SEE it)
agent-browser eval  "document.title"                 # run JS in the page
agent-browser wait  "<css-or-text>"                  # wait for an element
agent-browser find role button click --name "Run"    # semantic locator
agent-browser chat  "fill the form and submit"       # natural-language control
```

**The visual-QA habit:** `open` → `screenshot out.png` → **Read the PNG** (image
tool) to actually look at it. For interactive checks, `snapshot -i` to get refs,
then `click`/`fill`, screenshot again, and read the console via
`eval "JSON.stringify(window.__errors||[])"` or the `debug` profile.

Other essentials: `--session <name>` (isolated instances), Chrome-profile reuse
for auth, network route/mock/block + HAR, React introspection, WebSocket
viewport streaming. Config via `agent-browser.json` or `AGENT_BROWSER_*` env.

## MCP server

```bash
agent-browser mcp        # stdio MCP server exposing typed tools
```
Profiles: `core`, `network`, `state`, `debug`, `react`, `mobile`, `all`. Add it
to an MCP client (e.g. Claude Code settings) to get approval-gated browser tools
instead of raw shell.

## How to use it for a frontend deliverable (the standard loop)
1. Build/serve the page (static `file://`, a local dev server, or the deployed URL).
2. `agent-browser open <url>` then `screenshot` at desktop AND a narrow width
   (`--viewport 390x844` or set in config) — **Read both PNGs** to confirm no
   overflow/overlap and the brand looks right.
3. `snapshot -i`, then click through the real flow (e.g. ingest → run → export);
   screenshot each state; check for empty/error/loading correctness.
4. `eval` to surface console errors / network failures.
5. Fix, repeat. Only call the UI "done" after a clean screenshot of the real flow
   (pairs with `design-approval-gate`).

## When NOT to use
Pure logic/unit testing (use the test runner), or environments with no browser
and no way to install one. For programmatic Playwright-style suites in a Node
project, `webapp-testing` may fit better; agent-browser shines for fast,
ref-based, agent-driven visual checks and one-off screenshots.
