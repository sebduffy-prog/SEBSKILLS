---
name: mcp-apps-interactive-ui
category: mcp-connectors
description: >-
  Build MCP Apps (the ext-apps / SEP-1865 extension, spec 2026-01-26) so an MCP
  tool returns an INTERACTIVE UI — a chart, form, picker, dashboard, or table —
  rendered inline in Claude, ChatGPT, Goose or VS Code instead of plain text.
  Reach for this when you want a tool result that users can click, filter, or
  edit; when you hear "ui:// resource", "interactive tool output", "in-chat
  widget", "render a chart from my MCP tool", or "MCP Apps SDK". Covers
  registering ui:// resources, wiring _meta.ui.resourceUri, the sandboxed-iframe
  App bridge, postMessage/JSON-RPC, and CSP hardening.
when_to_use:
  - You want an MCP tool to return a live UI (chart, form, data table, picker) rendered in the chat, not a wall of text
  - You are adding interactive output to an existing MCP server (bar chart from data, a form that calls another tool, a filterable list)
  - You need the exact meta keys, mimeType, and SDK calls for ext-apps / SEP-1865 and want them correct, not guessed
  - You are wiring iframe-to-host communication (callServerTool, sendMessage, updateModelContext, ontoolresult)
  - You must lock down a UI resource's CSP and sandbox before shipping to a host
when_not_to_use:
  - You are building the MCP server's tools/transport itself with no UI — use mcp-builder
  - You are only connecting/registering existing MCP servers in a client — use register-mcp-servers
  - You want a standalone web page or React component unrelated to MCP tool output — use frontend-design or web-artifacts-builder
  - You want a private hosted chart page on claude.ai (not tool-driven) — use the Artifact tool / dataviz
keywords:
  - mcp-apps
  - ext-apps
  - sep-1865
  - ui-resource
  - interactive-ui
  - text/html;profile=mcp-app
  - resourceuri
  - postmessage
  - sandboxed-iframe
  - registerapptool
  - callservertool
  - in-chat-widget
  - json-rpc
  - modelcontextprotocol
  - tool-output-ui
similar_to:
  - mcp-builder
  - register-mcp-servers
  - mcp-server-security
inputs_needed: An existing (or new) MCP server in TypeScript/Node using @modelcontextprotocol/sdk; the tool whose output you want to visualise; the self-contained HTML/JS (or React) for the view; an MCP Apps-capable host to test in.
produces: An MCP server that registers a ui:// HTML resource plus a tool linked to it via _meta.ui.resourceUri, so the tool's result renders as an interactive iframe UI in supporting clients.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# MCP Apps: Interactive Tool UI (ext-apps / SEP-1865)

Standard MCP tools return text or structured JSON that the model reads aloud.
**MCP Apps** (the first official MCP extension, spec `2026-01-26`, PR SEP-1865)
lets a tool ALSO ship a UI: you predeclare an HTML view as a `ui://` resource,
link a tool to it, and the host renders that view in a sandboxed iframe, feeding
it the tool result. The user clicks, filters, and edits in-chat; the view can
call back into your server. Hosts that ship it: Claude, ChatGPT, Goose, VS Code.

## When to use

Use it when a tool's value is visual or interactive — a Mekko/waterfall chart, a
booking form, an audience picker, an editable data grid, a map. If the answer is
just prose, skip the UI and return text. This is server-side work in
TypeScript/Node.

## Prerequisites

- **Node 18+** and an MCP server built on `@modelcontextprotocol/sdk` (see the
  `mcp-builder` skill to scaffold one). This extension is TS/JS-first.
- `npm i @modelcontextprotocol/ext-apps` — the MCP Apps SDK (v1.7.x as of
  2026-07). Subpath exports:
  - `@modelcontextprotocol/ext-apps/server` — `registerAppTool`,
    `registerAppResource`, and the constants `RESOURCE_MIME_TYPE`
    (`"text/html;profile=mcp-app"`) and `RESOURCE_URI_META_KEY` (`"ui/resourceUri"`).
  - `@modelcontextprotocol/ext-apps` (default) — the `App` class + `PostMessageTransport` for the iframe side.
  - `@modelcontextprotocol/ext-apps/react` — `useApp`, `useAutoResize`, `useHostStyles`, `useDocumentTheme`.
  - `@modelcontextprotocol/ext-apps/app-bridge` — only if you are building a HOST.
- An **MCP Apps-capable host** to test in. Hosts advertise the capability under
  `capabilities.extensions["io.modelcontextprotocol/ui"]`. There is no supported
  host in the repo — test in a real client.
- The view HTML must be **self-contained** (inline CSS/JS, data: URIs) or point
  only at domains you allow in the resource's CSP. External requests are blocked
  by the iframe sandbox unless declared.

## Core model (three moving parts)

1. **UI resource** — an HTML document registered under a `ui://` URI with
   mimeType `text/html;profile=mcp-app`. Predeclared so the host can prefetch,
   review, and cache it separately from data.
2. **Tool → resource link** — the tool declares `_meta.ui.resourceUri:
   "ui://…"`. The host renders that resource when the tool runs.
3. **Data flow** — the tool's `structuredContent` / `content` is delivered to
   the iframe via the `ui/notifications/tool-result` JSON-RPC notification; the
   `App` bridge surfaces it as the `ontoolresult` event.

## Recipe 1 — Server: register the view + the tool

```ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { registerAppTool, registerAppResource } from "@modelcontextprotocol/ext-apps/server";
import { z } from "zod";

const server = new McpServer({ name: "bar-chart", version: "1.0.0" });
const VIEW_URI = "ui://bar-chart/view.html";

// 1) The HTML resource. Keep it self-contained; it reads its data at runtime
//    from the App bridge, NOT from server-side templating.
registerAppResource(server, "Bar chart view", VIEW_URI, {}, async () => ({
  contents: [{ uri: VIEW_URI, mimeType: "text/html;profile=mcp-app", text: VIEW_HTML }],
}));

// 2) The tool, linked to the view via _meta.ui.resourceUri (preferred key).
registerAppTool(
  server,
  "render_bar_chart",
  {
    description: "Render numeric series as an interactive bar chart",
    inputSchema: { series: z.array(z.object({ label: z.string(), value: z.number() })) },
    _meta: { ui: { resourceUri: VIEW_URI } },
  },
  async ({ series }) => ({
    // structuredContent is what the view receives; content is the model's text fallback.
    content: [{ type: "text", text: `Chart of ${series.length} bars` }],
    structuredContent: { series },
  }),
);
```

Notes:
- `_meta.ui.resourceUri` is the modern key. The flat `_meta["ui/resourceUri"]`
  (the `RESOURCE_URI_META_KEY` constant) is a deprecated fallback — do not use it
  for new tools.
- `registerAppResource` defaults the mimeType to `RESOURCE_MIME_TYPE` for you,
  but set it explicitly in the `contents` you return so hosts route it correctly.
- Always return a text `content` block: it is the fallback the model sees when a
  host does NOT support MCP Apps.

## Recipe 2 — Iframe: connect the App bridge and render

The view HTML runs inside the sandboxed iframe. It uses the `App` class to
handshake over `postMessage` and receive the tool result.

```html
<div id="root"></div>
<script type="module">
  import { App } from "https://esm.sh/@modelcontextprotocol/ext-apps"; // bundle/inline for prod

  const app = new App();
  app.ontoolresult = ({ structuredContent }) => {
    const bars = structuredContent?.series ?? [];
    document.getElementById("root").innerHTML = bars
      .map(b => `<div class="bar" style="width:${b.value}px">${b.label}</div>`)
      .join("");
  };
  await app.connect();            // performs the JSON-RPC handshake with the host
</script>
```

For production, **inline or bundle** the SDK and all assets — a CDN import only
works if that domain is allowed in the resource CSP (see Recipe 4).

## Recipe 3 — Interactivity back to the host

The iframe can drive the conversation and call your other tools:

```ts
// Call another server tool (e.g. drill-down) and get its result back:
const detail = await app.callServerTool({ name: "fetch_details", arguments: { id } });

// Nudge the chat with a user-visible message that DOES trigger a model turn:
await app.sendMessage({ content: [{ type: "text", text: "Show me Q4 only" }] });

// Silently add context for the model WITHOUT a new turn:
await app.updateModelContext({ content: [{ type: "text", text: "User selected bar 3" }] });
```

Event setters mirror the host notifications: `ontoolinput` (final args),
`ontoolinputpartial` (streaming args, progressive render), `ontoolresult`,
`ontoolcancelled`. React users: `useApp()` returns `{ app, isConnected, error }`;
pair with `useAutoResize()` and `useHostStyles()` for theming and sizing.

## Recipe 4 — Harden before shipping (defensive)

The host renders your view in a **restrictive sandboxed iframe**. Declare exactly
what it needs via the resource `_meta.ui` fields; anything undeclared is blocked.

- `csp.connectDomains` — hosts your view may `fetch`/XHR/WebSocket to.
- `csp.resourceDomains` — origins for `<script>`, `<style>`, `<img>`.
- `csp.frameDomains`, `csp.baseUriDomains` — nested frames / base URIs.
- `permissions` — opt into `camera`, `microphone`, `geolocation`,
  `clipboardWrite` only if truly required.

Keep the default deny-all posture: self-contained HTML with **no** external
domains is the safest and fastest (prefetchable, cacheable). All view→host calls
go through loggable JSON-RPC, and hosts can require explicit approval for
UI-initiated `tools/call` — never assume a call is silent or trusted.

## Verify

1. `npm run build` (or `tsc --noEmit`) — the server compiles with the ext-apps
   imports resolving.
2. **Inspect the wire**: run the server under the MCP Inspector. Confirm
   `resources/list` shows the `ui://…` URI with mimeType
   `text/html;profile=mcp-app`, and `tools/list` shows your tool with
   `_meta.ui.resourceUri` pointing at it.
3. **Render in a real host** (Claude / ChatGPT / VS Code / Goose): call the tool
   and confirm the iframe appears, receives `structuredContent`, and reacts to
   clicks. Watch for the `ui/notifications/tool-result` message reaching
   `ontoolresult`.
4. **Fallback path**: in a host WITHOUT MCP Apps support, confirm the tool still
   returns useful text `content` (no crash, no empty bubble).

## Pitfalls

- **Wrong mimeType.** It is exactly `text/html;profile=mcp-app`. Plain
  `text/html`, `text/html+skybridge` (that is OpenAI's older Apps SDK convention),
  or a typo means the host won't treat the resource as an MCP App.
- **Missing text fallback.** If `content` has no text block, non-supporting hosts
  render nothing. Always include one.
- **Templating data into the HTML server-side.** Don't. Register the view ONCE
  and static; deliver per-call data via `structuredContent` → `ontoolresult`.
  This is what makes views cacheable and keeps presentation separate from data.
- **External assets with no CSP entry.** A CDN `<script>` or remote image
  silently fails in the sandbox unless its domain is in `csp.resourceDomains`.
  Inline for reliability.
- **Guessing the meta shape.** It is `_meta.ui.resourceUri` (nested), not
  `openai/outputTemplate` and not a top-level `resourceUri`. The extension id for
  capability negotiation is `io.modelcontextprotocol/ui`.
- **Trusting UI-initiated tool calls.** They can be gated behind user approval
  and are fully logged — treat `callServerTool` from the iframe as untrusted
  input and validate arguments server-side (see mcp-server-security).
- **Forgetting `await app.connect()`.** Without the handshake, no notifications
  arrive and the view stays blank.

## Sources

- Spec: `modelcontextprotocol/ext-apps` `specification/2026-01-26/apps.mdx`; SEP-1865.
- SDK: npm `@modelcontextprotocol/ext-apps` (server/app/react/app-bridge exports).
- Blog: modelcontextprotocol.io "MCP Apps" (2025-11-21 announce, 2026-01-26 GA).
