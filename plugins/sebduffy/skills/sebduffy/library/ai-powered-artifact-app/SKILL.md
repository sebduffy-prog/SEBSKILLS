---
name: ai-powered-artifact-app
category: frontend-and-design
description: >
  Build a shareable Claude Artifact that calls Claude from INSIDE the running app via
  window.claude.complete, so recipients use your AI tool with zero API keys and zero cost
  to you — usage is billed to each viewer's own Claude subscription. Add persistent state
  with window.storage and live data via MCP. Reach for this whenever you want to ship a
  no-key, viewer-billed AI micro-app (client pitch tool, brief generator, tagline machine,
  audience quiz) as a link, not a deployment. Grounded in claude.com/blog/claude-powered-artifacts.
when_to_use:
  - You want to hand a client or colleague an AI tool as a link with no API keys, no login-to-your-account, and no hosting bill
  - Building a self-contained AI micro-app (brief writer, tagline generator, campaign quiz, copy grader) that reasons at runtime
  - You need each recipient's Claude usage billed to THEM (viewer-billed) instead of paying for everyone
  - The app must remember state across sessions (journals, trackers, saved briefs) via persistent storage
  - You want a prototype that pulls real data or triggers real actions (Google Calendar, Gmail, Slack, Asana) through MCP
when_not_to_use:
  - You need a production web app with a real backend, database, or custom domain — use frontend-design plus a real deploy (Vercel/Railway)
  - You are calling Claude from your own server or CLI with an API key you control — use claude-api
  - You just want a static component/effect with no AI at runtime — use web-artifacts-builder or frontend-design
  - You want a chat UI pattern rather than the artifact distribution model — use generative-ui-chat-interface
  - The deliverable is a one-off internal script or dashboard, not a shared link — use quick-tool
keywords:
  - claude artifacts
  - window.claude.complete
  - window.storage
  - viewer-billed
  - no api key
  - persistent storage
  - mcp integration
  - shareable ai app
  - live artifacts
  - client tool
  - react artifact
  - beta
similar_to:
  - web-artifacts-builder
  - artifact-design
  - frontend-design
  - generative-ui-chat-interface
  - quick-tool
inputs_needed: The app idea and its I/O; a Claude account (Free/Pro/Max/Team/Enterprise) to author and publish; paid plan (Pro+) if you need persistent storage or MCP.
produces: A single-file React or HTML artifact that calls Claude at runtime, published as a shareable claude.ai link that recipients run with their own account and billing.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# AI-Powered Artifact App (viewer-billed, no-key distribution)

Ship an AI tool as a **link**, not a deployment. The artifact calls Claude from inside itself; whoever
opens it signs into *their* Claude account and *their* subscription is billed. You pay nothing for their
usage and never share an API key. This is a genuinely novel distribution model — treat it as the fastest
way to get an AI micro-tool into a client's or planner's hands.

## When to use

Reach for this when the win is **distribution**: a tagline machine for a pitch, a brief-quality grader for
the account team, a campaign-idea quiz for a client microsite. If the value is a real product with a
backend, this is the wrong tool (see `when_not_to_use`).

## Prerequisites (read the honesty notes)

- **A Claude account** to author + publish. Artifacts with runtime AI work on Free, Pro, Max, Team and
  Enterprise. This feature launched in **beta (July 2025)** — API surface below can change.
- **Recipients need their own Claude account.** On first AI call the viewer is prompted to sign in so the
  prompt bills to them. No account = the AI features don't run. Plan around this for external clients.
- **Persistent storage and MCP are paid + published-only.** `window.storage` and MCP connectors require
  **Pro / Max / Team / Enterprise** and only work in a **published** artifact — during preview/dev they
  fail *silently* (no error). Free plans can build AI artifacts but have limited publish/storage.
- **Sandbox is strict.** The artifact runs in a sandboxed iframe (CSP). **No `fetch()` to external hosts,
  no CDN, no `localStorage`/`sessionStorage`.** All AI goes through `window.claude.complete`; all persistence
  through `window.storage`. Single file, React or HTML.
- **`window.claude.complete` takes a string and returns a string.** No streaming, no system-prompt param,
  no model selector are publicly documented. Code inside the artifact is invisible to the chat model —
  runtime errors do **not** round-trip back to Claude, so debug in the published artifact.
- Authoring path: describe the app to Claude in the **claude.ai chat / desktop app** and it builds a native
  artifact with these globals available, or author the HTML yourself and publish it. The `window.claude` /
  `window.storage` globals are injected by the **claude.ai artifact runtime** — verify they exist in a
  *published* artifact (see Verify) before promising them to a client.

## Recipe 1 — Minimal runtime AI call

The whole model in three lines. `await` it; it resolves to the completion text.

```js
async function generate(brief) {
  const reply = await window.claude.complete(
    `You are a senior copywriter. Write 5 punchy taglines for this brief:\n\n${brief}`
  );
  return reply; // plain string
}
```

Wire it to a textarea + button in React/HTML. No key, no fetch, no server.

## Recipe 2 — Structured (JSON) output

There is no `response_format`, so **force JSON in the prompt** and parse defensively — the completion is
just text.

```js
const raw = await window.claude.complete(
  `Score this ad headline 0-100 on clarity, distinctiveness, and brand fit.
Return ONLY valid JSON, no prose, shaped exactly:
{"clarity":0,"distinct":0,"brandFit":0,"note":"..."}
Headline: "${headline}"`
);
let data;
try { data = JSON.parse(raw.trim()); }
catch { data = JSON.parse(raw.slice(raw.indexOf("{"), raw.lastIndexOf("}") + 1)); }
```

## Recipe 3 — Conversation memory (no chat state)

Each call is stateless. To fake a conversation, **serialize prior turns into the next prompt** yourself.

```js
const history = turns.map(t => `${t.role}: ${t.text}`).join("\n");
const reply = await window.claude.complete(
  `Continue this planning conversation. Stay in character as a media strategist.\n${history}\nuser: ${input}\nassistant:`
);
```

## Recipe 4 — Persistent, stateful app (`window.storage`)

Turns a tool into a saved journal / tracker / shared board. **Async, text/JSON only, ~20 MB per artifact,
published-only.** Third arg `shared` = false → per-viewer private (default), true → visible to all viewers.
Method names below match community docs; if in doubt, let Claude generate the storage code in-chat and keep
these semantics.

```js
// save (personal by default)
await window.storage.set("brief:" + id, JSON.stringify(brief));
// read
const res = await window.storage.get("brief:" + id);
const brief = res?.value ? JSON.parse(res.value) : null;
// list + delete
const keys = await window.storage.list("brief:");   // prefix filter
await window.storage.delete("brief:" + id);
// shared board visible to every viewer:
await window.storage.set("board:pinned", JSON.stringify(items), true);
```

Rules that bite: keys < 200 chars (no spaces/slashes/quotes), values ~5 MB each, last-write-wins, and
**unpublishing deletes all storage** (personal + shared) permanently.

## Recipe 5 — Live data via MCP

Pro+/published artifacts can call MCP connectors (Google Calendar, Gmail, Slack, Asana, etc.) so a prototype
pulls real data or triggers real actions. The **viewer approves access on first use**; the preference then
persists for that artifact. Build the app to describe the tool it needs and let Claude wire the MCP call —
do not hand-invent transport. Treat MCP as beta and gate the UI on an approval/empty state.

## Recipe 6 — Publish and hand off

1. Get the app working as an artifact (chat: "build this as an artifact"; or paste your HTML).
2. **Publish** it (share menu). Publishing is what enables the shareable link, `window.storage`, and MCP.
3. Send the link. Recipients open it, hit an AI feature, sign into their own Claude account, and go.
4. Anyone can **fork/customize** a shared artifact — expect that for internal tools.

## Verify

- **AI call works published:** open the *published* link (not preview) in a fresh browser profile, trigger
  a completion, confirm the sign-in prompt bills the viewer and text returns.
- **Storage persists:** save something, reload the published link, confirm it's still there. Then confirm it
  does **nothing** in preview (proving you didn't accidentally rely on preview state).
- **No sandbox violations:** open devtools console — no CSP errors, no blocked `fetch`, no `localStorage`.
- **JSON path:** feed a weird input and confirm the `JSON.parse` fallback still yields a valid object.
- **Viewer-billed reality check:** ask a colleague on their own account to use it and confirm no cost lands
  on you.

## Pitfalls

- **Silent storage failure in dev.** `window.storage` returns nothing useful until published. If saves
  "don't work," you're almost certainly testing in preview. Publish, then test.
- **Assuming a key or a backend.** No `ANTHROPIC_API_KEY`, no env vars, no server — the whole point is
  viewer billing. If you need *your* key/backend, this is the wrong model (use `claude-api` + a real deploy).
- **External requests.** CSP blocks CDNs and third-party APIs. Inline everything; route "external data"
  through MCP, not `fetch`.
- **No streaming / no system role.** Bake persona and format into the single string prompt; the UI must
  handle a multi-second wait with a spinner.
- **Recipient friction.** External clients without a Claude account can't use the AI features. For a cold
  external audience, a normal hosted app with your own key may convert better — decide up front.
- **Beta drift.** `window.claude.complete` (string→string) is the stable, documented surface; `window.storage`
  method names and MCP are newer/beta and may shift. Re-verify against Claude's in-product `artifact-design` /
  `web-artifacts-builder` guidance before shipping to a paying client.
- **Fork/leak.** Shared artifacts are viewable, forkable, and their code readable — never embed secrets,
  private prompts you consider IP, or client-confidential data in the source.

Source: https://claude.com/blog/claude-powered-artifacts (plus Claude Help Center + Simon Willison's write-up).
