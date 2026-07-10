---
name: blender-mcp-setup
category: 3d
description: >-
  Install and wire up the ahujasid/blender-mcp add-on so Claude can drive Blender end-to-end.
  Use when the blender tools are missing, disconnected, or throwing "connection refused" / socket
  errors — installs uv, drops addon.py into Blender, enables "Interface: Blender MCP", starts the
  port-9876 socket server from the N-panel, registers the MCP client (Claude Code / Desktop / Cursor),
  and verifies the round-trip. Start here before any blender-mcp scene, render, or asset work.
when_to_use:
  - The mcp__blender__* tools are absent, greyed out, or a call errors with connection refused / broken pipe
  - Setting up Blender + Claude for the first time on a machine
  - Blender restarted or the add-on's socket server was stopped and needs reconnecting
  - Deciding which MCP client config (Claude Code, Claude Desktop, Cursor) to register the server in
when_not_to_use:
  - Add-on is already connected and tools respond — go straight to blender-mcp-scene-building or blender-mcp-scene-inspection
  - Writing bpy code against a live connection — use blender-mcp-bpy-api-navigator
  - Importing PolyHaven/Sketchfab/Hyper3D assets — use blender-mcp-asset-import (setup must already be green)
  - Diagnosing a render that looks wrong rather than a dead socket — use blender-mcp-render-review-loop
keywords:
  - blender
  - mcp
  - blender-mcp
  - ahujasid
  - addon
  - uv
  - uvx
  - socket
  - port-9876
  - n-panel
  - claude-desktop
  - cursor
  - connection-refused
  - setup
  - 3d
similar_to:
  - blender-mcp-scene-building
  - blender-mcp-scene-inspection
  - blender-mcp-render-review-loop
  - blender-mcp-asset-import
  - blender-mcp-procedural-generation
  - blender-mcp-bpy-api-navigator
inputs_needed: Blender 3.0+ installed; a terminal with uv/uvx; the target MCP client (Claude Code, Claude Desktop, or Cursor); addon.py from the blender-mcp repo
produces: A live Blender <-> Claude MCP connection on socket port 9876, a registered MCP client entry, and a verified round-trip via execute_blender_code
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Blender MCP Setup

Get the [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp) add-on installed and connected so
Claude can inspect and drive a live Blender session. The server is two halves that must both be running:
a **Blender-side add-on** exposing a socket on port **9876**, and a **stdio MCP server** (`uvx blender-mcp`)
that your client launches. If either half is missing, tool calls fail with connection errors.

## When to use

Use this the moment `mcp__blender__*` tools are unavailable or a call throws a socket/connection error.
It is the prerequisite for every other `3d/blender-mcp-*` skill — none of them work until the round-trip
here is green.

## Prerequisites

- **Blender 3.0 or newer** (check `Blender > About`). The add-on targets 3.0+.
- **Python 3.10+** for the `uvx` server (bundled by uv — you do NOT need a system 3.10; uv fetches one).
- **uv** installed and on PATH (provides `uvx`). See install below.
- One MCP client: **Claude Code** CLI, **Claude Desktop**, or **Cursor**.
- Network egress to PyPI on first run (uv downloads the `blender-mcp` package into a cache).

> macOS-without-brew note: the README suggests `brew install uv`, but the standalone installer works with
> no brew: `curl -LsSf https://astral.sh/uv/install.sh | sh`. Restart the shell (or `source ~/.zshrc`)
> so `uv`/`uvx` land on PATH.

## Steps

### 1. Install uv

```bash
# macOS / Linux (no brew required)
curl -LsSf https://astral.sh/uv/install.sh | sh
# macOS with Homebrew, if you have it
brew install uv
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify it resolves:

```bash
uv --version && uvx --version
```

### 2. Install the Blender add-on

1. Download `addon.py` from the repo (raw file):
   ```bash
   curl -L -o ~/Downloads/addon.py \
     https://raw.githubusercontent.com/ahujasid/blender-mcp/main/addon.py
   ```
2. Launch Blender.
3. `Edit > Preferences > Add-ons`.
4. Click **Install...** (top-right; in Blender 4.2+ it's the ▾ dropdown → *Install from Disk*), pick
   `~/Downloads/addon.py`.
5. Tick the checkbox on the entry labeled **"Interface: Blender MCP"** to enable it.

### 3. Start the socket server from the N-panel

1. Hover the 3D viewport and press **N** to open the sidebar.
2. Open the **"BlenderMCP"** tab.
3. Click **"Connect to MCP server"** (older add-on builds label this button **"Connect to Claude"** —
   same action). The status flips to *listening* / *connected*. The socket binds **`localhost:9876`**.

Leave Blender open. This socket is the live channel — closing Blender or clicking *Disconnect* kills it.

### 4. Register the MCP client

Pick the client you actually use. All three launch the same `uvx blender-mcp` stdio server, which then
dials the port-9876 socket.

**Claude Code (CLI):**
```bash
claude mcp add blender -- uvx blender-mcp
# confirm it registered
claude mcp list
```

**Claude Desktop** — edit `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "blender": { "command": "uvx", "args": ["blender-mcp"] }
  }
}
```

**Cursor** — Settings → MCP, or `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "blender": { "command": "uvx", "args": ["blender-mcp"] }
  }
}
```
On Windows wrap it: `"command": "cmd", "args": ["/c", "uvx", "blender-mcp"]`.

Restart the client (or reconnect the MCP server) so it spawns `uvx blender-mcp`.

### 5. Smoke-test the server binary (optional, isolates PyPI/uv issues)

```bash
uvx blender-mcp   # should start and wait on stdio; Ctrl-C to exit
```
If this hangs waiting for input with no traceback, uv + the package are fine and the problem (if any)
is on the Blender socket side.

## Verify

With Blender open, add-on enabled, "Connect to MCP server" clicked, and the client restarted, run a
minimal round-trip from Claude:

```
execute_blender_code:
  code: |
    import bpy
    print("BLENDER_MCP_OK", bpy.app.version_string, len(bpy.data.objects))
```

A successful reply echoes `BLENDER_MCP_OK 4.x.x <n>`. As a second check, `get_objects_summary` should
list the default scene objects (e.g. `Cube`, `Camera`, `Light`). If both return, setup is complete —
move on to `blender-mcp-scene-inspection` or `blender-mcp-scene-building`.

## Pitfalls

- **Connection refused / broken pipe on the FIRST call.** Almost always the add-on socket isn't running.
  Re-open the N-panel BlenderMCP tab and click *Connect to MCP server*. Retry — the README notes the
  first attempt sometimes fails and the next succeeds.
- **Two `uvx blender-mcp` at once.** Do not run the uvx command in a second terminal while a client also
  spawns it. Only one process may own the stdio pipe; the second corrupts the connection.
- **Port 9876 already in use.** A stale Blender or leftover process holds the socket. Fully quit Blender
  (check `lsof -i :9876`), reopen, reconnect.
- **`uvx: command not found`.** uv installed but PATH not refreshed. Restart the terminal, or source your
  shell rc; uv installs to `~/.local/bin`.
- **Add-on enabled but no "BlenderMCP" tab.** The N-panel is context-sensitive — make sure you pressed
  **N** with the cursor over the 3D **viewport**, not another editor. Confirm the add-on checkbox is
  actually ticked (enabling can silently fail if a Python version mismatch logged an error in the console).
- **Tools still missing in the client after config edit.** The client only reads MCP config at launch —
  fully restart Claude Desktop / Cursor, or in Claude Code re-run `claude mcp list` to confirm the entry.
- **Nothing works after a Blender restart.** Enabling the add-on does not auto-start the socket. You must
  click *Connect to MCP server* again every session (or in add-on preferences enable auto-start if your
  build supports it).
