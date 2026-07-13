---
name: claude-tag-slack-agent
category: agent-frameworks
description: >
  Design and operate Claude Tag — Anthropic's shared @Claude teammate inside Slack channels
  (an evolution of Claude Code). Covers per-channel scoping and the three memory tiers, opt-in
  ambient/proactive mode, stage-by-stage autonomous task execution with an in-thread checklist,
  self-scheduling, multiplayer hand-off (one Claude per channel that anyone can pick up), the
  tools/MCP-connector grants, three-level spend caps, and the 30-day legacy-Claude-in-Slack
  migration checklist. Use when a VCCP team wants an @Claude teammate wired into client or
  internal Slack channels, when planning the Enterprise/Team beta rollout, or when auditing
  what an ambient Slack agent can see and spend.
when_to_use:
  - "A team wants an @Claude teammate embedded in a Slack channel to run tasks async and post results in-thread"
  - "Planning the rollout: which channels, what tools/data each Claude can touch, and per-channel spend caps"
  - "Deciding whether to enable ambient/proactive mode in a given channel (and understanding the risk)"
  - "Migrating off the legacy 'Claude in Slack' app before the 30-day window closes"
  - "Auditing or scoping what an ambient agent remembers, can access, and can spend across channels"
  - "Designing a multiplayer hand-off flow where colleagues pick up a task Claude started"
when_not_to_use:
  - "Building a Slack app/bot from scratch against Slack's own API — that is bespoke engineering, not Claude Tag"
  - "Writing programmatic agents against the Anthropic API/SDK — use claude-api or an agent-SDK skill (openai-agents-sdk, pydantic-ai-typed-agents)"
  - "Building a custom MCP connector for Claude to use — use mcp-builder"
  - "Human approval gates inside a coding agent loop — use human-in-the-loop-approval"
keywords:
  - claude tag
  - slack
  - ambient mode
  - claude code
  - multiplayer agent
  - channel memory
  - spend limit
  - mcp connector
  - enterprise
  - migration
  - proactive agent
  - self-scheduling
  - team teammate
  - beta
similar_to:
  - agent-orchestration-patterns
  - human-in-the-loop-approval
  - computer-use-agent
inputs_needed: >
  Claude Enterprise or Team plan with a Primary Owner/Owner able to run setup; a Slack workspace
  to pair; the list of channels to scope; the tools/data sources/repos to grant (GitHub, Gmail,
  DBs, MCP connectors); a monthly org spend budget.
produces: >
  A rollout plan and operating playbook: channel-scope matrix, tool-grant list, three-level spend
  caps, ambient-mode decisions per channel, a migration checklist off the legacy Slack app, and
  hand-off/audit conventions the team follows.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Tag — the shared @Claude teammate in Slack

Claude Tag is Anthropic's Slack-native teammate, framed as an evolution of Claude Code.
You tag `@Claude` in a channel; it breaks the task into stages, posts a checklist in the
thread, and works through the stages in view using the tools it's been granted. It is a
*shared* agent — one Claude per channel that everyone works with — not a per-user chatbot.

This skill is an operating playbook, not code: how to scope, wire, budget, and roll it out
safely, plus the migration off the legacy app.

## When to use

Use this when a VCCP team (client channel, internal squad, IRN-BRU/AGBARR workstream, etc.)
wants an @Claude teammate that runs work asynchronously and leaves an auditable trail in the
Slack thread — and when you need to make the scoping/spend/ambient decisions deliberately
rather than clicking through the setup blind.

## Prerequisites (read the honest bits)

- **Beta, Enterprise/Team only.** Claude Tag launched **23 June 2026** in **beta** for Claude
  **Enterprise** and **Team** customers. It is not on Pro/Free. Exact UI, limits, and pricing
  can change during beta — treat every number below as "verify in-product."
- **Who can set it up.** Only a **Primary Owner or Owner** in the Claude organization can run
  setup. The **Admin** role cannot. (Reported by press coverage; confirm in your admin console.)
- **Billing model.** Metered at **API rates**, not bundled into a per-seat fee. **Channel work
  bills to the organization; DMs bill to each user's own account.** This is the key governance
  fact — an ambient agent left running in busy channels spends real money.
- **It replaces the old app.** Claude Tag supersedes the legacy "Claude in Slack" app. There is
  a **~30-day migration window** from launch; press coverage cites an **~3 Aug 2026** cutover
  after which the old app stops and the switch becomes automatic. Confirm your org's exact date.
- **Launch credits.** Anthropic issued introductory credits to eligible orgs (press reports
  ~$25,000 Enterprise / ~$2,500 Team). Treat as press-sourced, not a guarantee — check your
  billing page.
- **What Anthropic officially states vs. press.** The four setup steps, multiplayer model,
  ambient mode being opt-in, per-channel scoping of memory, stage-based execution, and
  self-scheduling come straight from Anthropic's announcement. Finer numbers (credit amounts,
  the exact cutover date, the 75%/95% spend alerts, the three named memory tiers) come from
  press write-ups — flag them as "verify" when briefing stakeholders.

## The four-step setup (Anthropic's official flow)

Run these as a Primary Owner/Owner:

1. **Pair Claude Tag with your Slack workspace.**
2. **Grant the tools, data sources, and repositories** Claude will need (GitHub, Gmail, databases,
   MCP connectors). Grant the minimum each channel actually needs — see the scope matrix below.
3. **Set a monthly spend limit for your organization.** Then set per-channel caps (below).
4. **Test in a private channel** before rolling out broadly. Validate integrations and governance
   here, not in a live client channel.

## Recipe 1 — Build the channel-scope matrix (do this first)

Memory and access are **scoped to channels defined by admins**. Reported as three tiers:

- **Channel memory** — context accumulated inside that one channel. *What Claude learns in a
  private channel stays there.*
- **Workspace memory** — context pulled from other channels/data sources, **only where an admin
  granted it**.
- **Organizational knowledge** — connected systems (GitHub, DBs) within configured parameters.

Before wiring anything, write a matrix — one row per channel:

| Channel | Purpose | Tools granted | Workspace-memory reach | Ambient? | Per-channel cap |
|---|---|---|---|---|---|
| #irn-bru-brief | brief drafting | GDrive (read) | none | off | £X/mo |
| #eng-web | PR work | GitHub (write) | #eng-* read | off | £Y/mo |
| #ambient-ops | monitoring | Gmail (read) | broad | on | £Z/mo |

Principle: **least privilege per channel.** A client-facing channel should not inherit GitHub
write or another client's memory. Different Claudes stay isolated by organizational function.

## Recipe 2 — Decide ambient mode per channel (deliberately)

Ambient (proactive) mode is **opt-in** because "an unsolicited AI agent works better in some
channels than others." When on, Claude will, without being tagged:

- **pursue a project autonomously over hours or days**,
- **follow up on threads that have gone quiet**,
- **flag what's relevant from across its channels and tools**,
- **schedule tasks for itself** (e.g., watch a connected Gmail inbox and ping in Slack when an
  important email lands).

Enable ambient **only** where proactive nudges are wanted (ops/monitoring channels), and keep it
**off** in client-facing or high-stakes channels where an unbidden post would be awkward or leak
context. Because channel work bills to the org, ambient mode also has a direct cost — pair every
ambient-on channel with a firm per-channel cap.

## Recipe 3 — Stage-by-stage execution and multiplayer hand-off

- When tagged, Claude **posts a checklist in the thread, then works the stages in view** (press
  describes a multi-item checklist tracking each stage). This transparency is the point — the work
  is legible to everyone in the channel.
- **One Claude per channel; everyone works with the same one.** Anyone can see what it's doing and
  **pick up the conversation from where the last person left off** — true multiplayer hand-off.
- **Everything stays in the Slack thread**, so nothing happens outside channel history. External
  actions carry a link back: a **GitHub PR carries a link to the Slack thread that triggered it**.

Hand-off convention to adopt: keep one task per thread; when you take over someone's task, reply in
that thread so Claude's context and the audit trail stay intact. Don't DM Claude to continue channel
work — DMs bill to you personally and lose the shared context.

## Recipe 4 — Spend governance (three levels)

Reported spend controls:

- **Org-wide monthly cap**, **per-channel limits**, and a **default that new channels inherit**.
- Admin **alerts at ~75% and again at ~95%** of any limit (press-sourced — verify).
- **A task that would push past the limit is declined outright, not silently truncated.** Good:
  no surprise half-done work, but it means a too-tight cap will visibly refuse tasks.

Set the org cap to your real monthly budget, set a sensible inherited default so new channels
can't run away, and raise caps deliberately on channels that earn it.

## Recipe 5 — Migrate off the legacy "Claude in Slack" app

The old app was **session-based**, with **no shared channel memory** and **per-user permissions
and billing**. Claude Tag is a **shared, persistent agent**: channel memory that builds over time,
an org-level identity, org billing for channel work, plus ambient mode and scheduling.

Checklist:

- [ ] Confirm your plan is Enterprise or Team and identify a Primary Owner/Owner to run setup.
- [ ] Note your org's migration deadline (press cites ~3 Aug 2026); after it, the switch is automatic.
- [ ] Run the four-step setup in a **private test channel** first.
- [ ] Rebuild per-user expectations as **channel** conventions (shared identity, org billing).
- [ ] Set org + per-channel + default spend caps before broad rollout.
- [ ] Decide ambient on/off per channel; default off.
- [ ] Roll out channel-by-channel, starting low-risk.

## Verify

- Setup succeeds only as Primary Owner/Owner — if the option is greyed out, you're on Admin, not Owner.
- In the test channel, tag `@Claude` with a small task and confirm it **posts a stage checklist**
  and works in-thread.
- Confirm private-channel memory does **not** leak: ask in another channel about something only said
  in the private one — it should not know.
- Trip a low per-channel cap and confirm the next task is **declined**, not half-done.
- Confirm an external action (e.g., a test GitHub PR) **links back to the originating Slack thread**.
- Use the admin memory tools to **view/edit/delete** channel and workspace memory and confirm the change.

## Pitfalls

- **Ambient-on in a client channel** → unbidden posts that surprise clients or surface cross-context
  info. Default ambient **off**; opt in per channel.
- **Over-granting tools** → a channel with GitHub write or DB access can open PRs and run queries.
  Grant per channel, least privilege; audit the scope matrix.
- **Assuming per-user billing** → channel work bills to the **org**; only DMs bill to individuals.
  Busy channels + ambient mode = real spend. Cap everything.
- **No per-channel/default cap** → one runaway channel drains the org budget. Always set an inherited
  default.
- **Missing the migration window** → the legacy app stops and cutover becomes automatic; plan before
  the ~30-day deadline rather than being switched over mid-workstream.
- **Quoting press numbers as fact** → credit amounts, the exact cutover date, and the 75%/95% alerts
  are press-sourced during beta. Say "verify in-product" when briefing VCCP stakeholders or clients.
- **Treating it like the Anthropic API** — Claude Tag is a Slack product surface, not the SDK. For
  programmatic agents use claude-api / an agent-SDK skill; for custom connectors use mcp-builder.

## Source

Anthropic, "Introducing Claude Tag" — https://www.anthropic.com/news/introducing-claude-tag
(launched 23 June 2026, beta for Enterprise/Team). Corroborating detail from press coverage
(DataCamp, Salesforce Ben, Neowin, TechRepublic, Engadget); numeric specifics flagged inline as
press-sourced and "verify in-product."
