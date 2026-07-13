---
name: live-artifact-dashboard-builder
category: frontend-and-design
description: >
  Build Claude Cowork Live Artifacts — persistent, self-refreshing HTML dashboards
  that Claude re-queries from your connected apps (Calendar, Gmail, Slack, Linear,
  Asana, HubSpot, RSS) and local Cowork files every time you open them. Use to stand
  up a standing KPI board, campaign-performance tracker, content calendar, or pipeline
  view that lives in the Live artifacts tab and shows today's data, not the day it was
  built. Grounds against Anthropic's official Cowork Live Artifacts docs; honest about
  the desktop-only, paid-plan, not-yet-shareable beta constraints.
when_to_use:
  - You want a dashboard that reopens with fresh data instead of a one-off chat artifact
  - Standing KPI / pipeline / campaign / content-calendar views for a client or team
  - Wiring a dashboard to Calendar, Gmail, Slack, Linear, Asana, HubSpot or RSS via connectors
  - Feeding a dashboard from a scheduled task that writes a file into the Cowork folder
  - You need version history (compare/restore) on an evolving internal dashboard
when_not_to_use:
  - Building a shareable claude.ai web artifact (React/shadcn) — use web-artifacts-builder
  - You just need a static one-shot chart or dashboard artifact — use quick-dashboard
  - Designing the layout/IA of a dashboard before wiring data — use dashboard-information-architecture
  - Automating a web tool with no MCP connector — use agentic-web-automation plus schedule
keywords:
  - live artifacts
  - claude cowork
  - dashboard
  - mcp connectors
  - auto-refresh
  - persistent
  - kpi board
  - content calendar
  - pipeline view
  - refresh on open
  - claude desktop
  - scheduled task
  - version history
  - rss
  - gmail calendar slack
similar_to:
  - quick-dashboard
  - dashboard-information-architecture
  - web-artifacts-builder
  - recording-studio
inputs_needed: >
  Claude Desktop (latest) on a paid plan with Cowork; the connectors you want the
  dashboard to read approved and authenticated; a clear "one decision this supports"
  brief plus the metrics/entities to show.
produces: >
  A named Live Artifact (persistent HTML dashboard) saved in the Cowork Live artifacts
  tab that re-queries approved connectors on open, plus optional scheduled-task + file
  pipeline for non-MCP sources.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Live Artifact Dashboard Builder

Stand up a **Live Artifact** in Claude Cowork: a persistent, interactive HTML
dashboard that Claude builds once and then re-queries from your connected apps and
local files every time you open it, so the view reflects *today*, not the day it was
built. Ideal for standing KPI boards, pipeline trackers, campaign dashboards and
content calendars that a strategist or account lead reopens daily.

## When to use

Reach for this when a client or team keeps asking the same "where are we now?"
question and a one-shot chat artifact goes stale the moment it's generated. A Live
Artifact lives in its own tab, holds its own version history, and pulls fresh data on
open — no re-prompting, no hunting for the old chat.

## Prerequisites (read this — it's a constrained beta)

Live Artifacts launched in Cowork on **20 April 2026** and carry real limits. Be
honest with the user about all of these before building:

- **Desktop app only.** Live Artifacts require **Claude Desktop** (latest version).
  On Cowork web or mobile there is no "Live artifacts" tab. macOS and Windows are
  supported; **Linux is beta**.
- **Paid plans only:** Pro, Max, Team, Enterprise.
- **Local, not remote.** The artifact lives on *this* computer. It does **not**
  sync across devices — switch machines and it doesn't come with you.
- **Not shareable yet.** At launch they are for your own use only; there is no
  team-share. Don't promise a shareable link to a client.
- **Connectors are used without re-asking.** A Live Artifact can only touch the
  connectors you **approved during creation or update**, but within that set it
  queries them **without prompting each time**. Choose the connector scope
  deliberately — treat it like granting standing access.
- **Connectors must be authenticated** (Calendar, Gmail, Slack, Linear, Asana,
  HubSpot, Notion, Google Sheets/Analytics, GitHub PRs, etc.) before the dashboard
  can read them. RSS and local files in the Cowork folder also work as sources.

Honesty note: this is a young feature and Anthropic is iterating. There is **no
documented "Live toggle" switch** — "live" is the artifact *type*, and freshness comes
from automatic refresh-on-open plus a **manual refresh button in the artifact header**.
If a user asks for a toggle, explain that's the model, not a missing setting. UI
labels and behaviour may shift; confirm against the in-app UI and the official article.

## Recipes

### Recipe A — Connector-backed dashboard (the common path)

Best when every source has an MCP connector (Calendar, Gmail, Slack, Linear, Asana,
HubSpot, Notion, GitHub).

1. **Approve the connectors first.** In Claude Desktop, connect and authenticate every
   source the dashboard will read. The artifact inherits exactly this set.
2. **Frame the one decision.** Before layout, answer: *"What single decision does this
   dashboard support?"* Cluttered boards get ignored. Keep it to one job.
3. **Ask Claude in a Cowork task**, naming the sources, the layout, and the refresh
   intent explicitly. Example brief:

   > Build me a Live Artifact: a weekly client KPI board. Data sources: our Linear
   > workspace (open issues by status), the #client-acme Slack channel (this week's
   > flagged messages), my Google Calendar (this week's client meetings), and the
   > brand's RSS feed for press mentions. Layout: 4 KPI tiles (open issues, blockers,
   > meetings this week, new mentions) with week-over-week deltas, a status-by-column
   > bar chart, and a sortable table of flagged items. Use VCCP brand colours, green/red
   > performance indicators, and **refresh the data every time I open it**.

4. **Alternatively start from the tab:** open the **Live artifacts** tab → **New
   artifact** → **Chat with Claude**, then give the brief above.
5. **Verify the first render** (first-run accuracy is roughly 70–80% — expect to
   iterate). Correct wrong metrics, missing series, or misread fields in follow-up
   turns. Each iteration **saves a version** you can compare or restore.
6. **Name it** something a future-you recognises ("ACME weekly KPI board"). It now
   persists in the Live artifacts tab across sessions.

### Recipe B — Scheduled-task + file bridge (non-MCP sources)

Use when a source has **no connector** (a web-only analytics tool, YouTube Studio, a
paywalled report). The pattern: a task fetches the data on a cadence and writes a file
into the Cowork folder; the Live Artifact reads that file on open.

1. Write a small skill/prompt that fetches the data — via a Cowork connector, an API
   call, or **Claude for Chrome / claude-in-chrome** for web-only tools.
2. Have it write a normalised `data.json`/`.csv` into your **Cowork folder**.
3. Schedule it (see the `schedule` skill / cron routines) on the cadence you need
   (hourly, daily, Monday 8am).
4. Build the Live Artifact to **read from that file** instead of a live connector.
5. **Caveat to state plainly:** scheduled tasks only run **while your computer is awake
   and Claude Desktop is open**. If the machine slept, the file (and the dashboard) is
   as stale as the last successful run — surface the file's timestamp on the dashboard
   so staleness is visible.

### Recipe C — Content calendar / pipeline view

Combine Calendar (scheduled posts / go-lives) + a project tool (Linear/Asana for
production status) + Gmail or Slack for approvals. Lay it out as a week/month grid
(borrow structure from `dashboard-information-architecture`), colour cells by status,
and print the "last refreshed" time. Keep the connector set tight — only what the grid
actually reads.

## Verify

- The dashboard appears in the **Live artifacts** tab and **reopens from a fresh
  session** (close the originating chat, reopen from the tab — it should still load).
- **Refresh-on-open works:** change a source (move a calendar event, close a Linear
  issue), reopen the artifact, confirm the number moves. Use the header **refresh
  button** to force a re-query and confirm the cache isn't hiding new data.
- **Version history exists:** iterate once, then confirm you can **compare** the prior
  version and **restore** it.
- **Connector scope is right:** it reads everything it should and nothing it shouldn't —
  remember it queries the approved set without asking.
- **Staleness is legible:** a "last updated" timestamp is visible (critical for
  Recipe B file-backed boards).

## Pitfalls

- **Promising sharing.** It is not shareable at launch — a client can't open your link.
  Deliver a screenshot/export or rebuild on their machine instead.
- **Expecting cross-device sync.** It's local to one computer. Don't build a "team" board
  and expect colleagues to see it.
- **Over-scoping connectors.** Approved connectors are used silently. Don't approve your
  whole workspace for a board that needs one channel — scope tight.
- **Assuming a "Live toggle."** There isn't one; freshness = refresh-on-open + manual
  refresh button. Explain the model rather than hunting a setting.
- **Trusting the first render.** ~70–80% first-run accuracy; always sanity-check the
  numbers against source before showing a client, and validate connectors weekly —
  they break silently.
- **Scheduled tasks and sleep.** Recipe B data only refreshes while the Mac is awake and
  Desktop is open; overnight/weekend gaps are normal. Show the timestamp.
- **Clutter.** A dashboard that answers three questions answers none. Anchor every tile
  to the one decision it supports.
- **Cache confusion.** A short cache serves the last data for speed; if a number looks
  frozen, hit refresh before assuming the connector is broken.

## Sources

- Anthropic — [Use live artifacts in Claude Cowork](https://support.claude.com/en/articles/14729249-use-live-artifacts-in-claude-cowork) (authoritative)
- Practitioner walkthroughs (connector vs scheduled-task patterns, example prompts,
  first-run accuracy) — treat as community context, not spec.
