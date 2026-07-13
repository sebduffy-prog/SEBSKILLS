---
name: unattended-longrun-envelope
category: building-agents
description: >-
  Pre-flight and safety-wrap any hours-to-days unattended Claude Code run — a dynamic
  workflow (ultracode), an agent team, or a scheduled cloud routine — so nothing prompts
  mid-run and nothing goes rogue. Allowlist every shell / WebFetch / MCP tool the agents
  need, deny-gate destructive commands (force-push, rm -rf, DROP), set a size guideline
  and watch the Large-workflow threshold, plan around resume-within-session limits, and
  fire a Stop / SessionEnd webhook on completion. Reach for it before you walk away from a
  long autonomous run and want it to finish safely without babysitting.
when_to_use:
  - Before kicking off a dynamic workflow (ultracode) or long agent-team run you will not babysit
  - Starting a codebase-wide migration or audit that fans out dozens to hundreds of subagents
  - Scheduling an unattended cloud routine that must not stall on a permission prompt overnight
  - Wiring a webhook or Slack ping to fire when a background run finishes or grows too large
  - Hardening an autonomous run so it physically cannot force-push, drop a table, or rm -rf
  - Choosing size guideline, agent caps, and model before an expensive multi-agent run
when_not_to_use:
  - Setting up the agent team itself — roles, mailbox, worktrees, exit-2 gates — use claude-code-agent-teams
  - Creating or managing the cron schedule for a cloud routine — use the schedule skill
  - A short interactive task you will supervise turn-by-turn — no envelope needed, just run it
  - Writing raw Anthropic SDK or Managed Agents server code — use claude-api or managed-agents-outcomes
  - General settings.json hook / permission editing mechanics — use update-config
keywords:
  - ultracode
  - dynamic workflows
  - unattended
  - long-running
  - tool allowlist
  - permissions
  - deny rules
  - destructive gate
  - large workflow
  - size guideline
  - checkpoint
  - resume
  - webhook
  - stop hook
  - sessionend
  - agent caps
  - headless
  - autonomous
similar_to:
  - claude-code-agent-teams
  - permanent-agent
  - agent-code-sandbox
  - claude-api
  - managed-agents-outcomes
inputs_needed: A concrete long-running task (workflow / agent team / scheduled routine), write access to the project or user settings.json, and the list of shell commands, domains, and MCP tools the run will need. A webhook URL is optional.
produces: A pre-flight allowlist plus deny-gate in settings.json, a chosen size guideline / model, a completion-and-warning notification hook, and a documented resume plan — so the run finishes unattended without prompting or destructive mistakes.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Unattended Long-Run Envelope

A checklist you run *before* you walk away from a multi-hour or multi-day autonomous Claude Code
run. It closes the three ways a long run goes wrong: it **stalls** on a permission prompt with
nobody there, it does something **destructive**, or it **balloons** in cost. The envelope wraps
whichever primitive you're using — a dynamic workflow (`ultracode`), an [agent team](../claude-code-agent-teams/SKILL.md),
or a scheduled cloud routine.

## When to use

Use it when a run will keep going while you're not watching: an overnight migration, a
codebase-wide audit that spawns hundreds of subagents, a scheduled routine that runs at 3am. If
you'll be at the keyboard answering prompts, you don't need this.

## Prerequisites — read the honest bits

- **Terminology.** The background-orchestration feature is **dynamic workflows**, triggered by the
  `ultracode` keyword or `/effort ultracode`. There is no `/goal` command — if you've seen that
  name it isn't the current one. "Routines" here means **scheduled cloud agents** (the `schedule`
  skill / `/schedule`), which run on a cron in Anthropic's cloud, not on your Mac.
- **Versions.** Dynamic workflows need Claude Code **v2.1.154+** (on Pro, enable the *Dynamic
  workflows* row in `/config`). `/effort ultracode` needs **v2.1.203+**; the size guideline needs
  **v2.1.202+**; the *Large workflow* warning needs **v2.1.203+**. Check `claude --version`.
- **Resume is weak.** A dynamic workflow is resumable **only within the same session** — completed
  agents return cached results, the rest run live. If you **exit Claude Code, the next session
  starts the workflow fresh.** For a days-long run this is the single biggest gotcha: plan around
  it (below), don't assume durable checkpoints.
- **Availability.** Workflows run on all paid plans, Anthropic API, Bedrock, Vertex/Agent Platform,
  and Foundry. Some flags are version-gated as noted; features can still change.

## Recipe 1 — Pre-flight the tool allowlist so nothing prompts mid-run

This is the step that most often saves a run. Per the workflows docs: subagents a workflow spawns
**always run in `acceptEdits` mode and inherit your tool allowlist**, so **file edits auto-approve**
— but **shell commands, web fetches, and MCP tools that aren't in your allowlist still prompt you
mid-run.** With nobody there, the run wedges.

Walk the task and list every tool the agents will actually call, then add each to
`permissions.allow` in `.claude/settings.json` (project) or `~/.claude/settings.json` (user). Use
the real rule syntax — grounded from the permissions reference:

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(npx tsc *)",
      "Bash(git commit *)",
      "Bash(git add *)",
      "WebFetch(domain:docs.anthropic.com)",
      "WebFetch(domain:*.github.com)",
      "mcp__github__get_*",
      "mcp__railway__*"
    ]
  }
}
```

Syntax notes that bite people:
- A trailing ` *` (space then star) enforces a word boundary: `Bash(npm run *)` matches `npm run build`
  but not `npm runx`. `Bash(ls:*)` is the equivalent `:*` shorthand for a trailing wildcard only.
- Claude Code is shell-operator aware: a rule must match **each subcommand** of a compound command
  independently, so `Bash(safe *)` will **not** auto-approve `safe && rm -rf .`.
- MCP allow-globs must keep the server segment literal: `mcp__github__get_*` is fine,
  `mcp__*` as an *allow* rule is skipped with a warning.
- WebFetch matches on hostname: `WebFetch(domain:*.example.com)` covers subdomains but **not**
  `example.com` itself — add both if you need the apex.

Verify by running the task on a **tiny slice first** (one directory, one file) and watching whether
any prompt appears. Every prompt you clear during that dry run is one you must add to the allowlist
before the real run.

## Recipe 2 — Deny-gate destructive operations (circuit breakers)

For unattended runs, don't rely on *ask* rules — an ask still needs a human. Use **deny** rules,
which win by precedence (evaluation order is **deny → ask → allow**, first match wins, and a deny
in any scope beats an allow in any other). A scoped deny leaves the tool usable but blocks the
dangerous shape:

```json
{
  "permissions": {
    "deny": [
      "Bash(git push --force*)",
      "Bash(git push -f*)",
      "Bash(git reset --hard*)",
      "Bash(rm -rf *)",
      "Bash(* DROP *)",
      "Bash(* TRUNCATE *)",
      "Bash(psql *)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)"
    ]
  }
}
```

Honest limits to state in your run notes:
- Argument-pattern denies are **fragile** — `Bash(rm -rf *)` won't catch `find . -delete`,
  `xargs rm`, or a script that deletes files itself. For a true boundary, run the whole thing in a
  **sandbox / container** (see agent-code-sandbox) or enable [sandboxing](https://code.claude.com/docs/en/sandboxing),
  which enforces filesystem/network limits at the OS level regardless of what the model tries.
- `Bash(command:rm *)` (the `command:` param form) is **ignored with a startup warning** — use the
  plain `Bash(rm *)` shape.
- A PreToolUse hook that exits code 2 is the stronger gate: it blocks the call before permission
  rules even run. Use one when a deny pattern is too coarse.
- Never reach for `bypassPermissions` on a machine that isn't disposable. It's only safe inside a
  container/VM; even then `rm -rf /` and `rm -rf ~` still prompt as a last-resort circuit breaker.

## Recipe 3 — Size + cost guardrails

- **Runtime caps are automatic:** up to **16 concurrent agents** (fewer on low-core machines) and
  **1,000 agents total per run**. These bound a runaway loop but not spend.
- **Set a size guideline** in `/config` (v2.1.202+): `small` = aim <5 agents, `medium` = <15,
  `large` = <50, `unrestricted` = default. It's advice sent to Claude, so a prompt that explicitly
  demands more still overrides it — but it keeps casual runs small.
- **Large-workflow warning:** when a run schedules **more than 25 agents** *or* its projected token
  total passes **1.5 million**, the task-panel progress line shows a `Large workflow` warning
  pointing you to `/workflows` to stop it (v2.1.203+). Setting a size guideline replaces the
  25-agent threshold with the guideline's count. The warning is **advisory only** — it does not
  pause the run — and `ultracode` sessions suppress it entirely.
- **Cost hygiene:** gauge spend on a one-directory slice first, and check `/model` before a big run
  if you usually work on a smaller model. Ask Claude to route non-critical stages to a cheaper model.

## Recipe 4 — Fire a webhook on completion (and act on the warning)

There is **no dedicated hook event for the Large-workflow warning** — treat that as a
*watch-`/workflows`* signal, or cap it away with a size guideline. For "the run finished, ping me,"
use a completion hook. The cleanest is an HTTP hook on `Stop` (Claude finished responding) and/or
`SessionEnd`, which POSTs the event JSON automatically:

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ {
        "type": "http",
        "url": "https://hooks.example.com/claude-run-done",
        "headers": { "Content-Type": "application/json" },
        "timeout": 10
      } ] }
    ],
    "SessionEnd": [
      { "hooks": [ {
        "type": "command",
        "command": "curl -sS -X POST https://hooks.example.com/session-end -H 'Content-Type: application/json' -d @-"
      } ] }
    ]
  }
}
```

Notes: HTTP-hook failures (non-2xx, timeout) are **non-blocking**, so a dead webhook won't wedge the
run. The `Notification` event fires when Claude needs attention or goes idle — hook it too if you
want a ping the moment a prompt *would* have appeared (a sign your allowlist missed something). For a
Slack post specifically, POST to an incoming-webhook URL with a `{"text": "..."}` body via the
`command` form.

## Recipe 5 — Plan around the resume limit

Because a workflow only resumes **within the same session**, design a days-long job so an interruption
is cheap:

- **Chunk it.** The docs are explicit: "For sign-off between stages, run each stage as its own
  workflow." Break the job into stages that each finish in one sitting; persist state to **files or
  a shared task list** between stages, not to context.
- **Prefer an agent team for durable state.** An agent team's **shared task list** survives a
  teammate restart, so long multi-day coordination is more robust there than in a single workflow.
- **For scheduled cron work, keep each run idempotent and self-contained** — a routine re-runs from
  scratch each fire; write progress to a file/issue the next run reads.
- Keep the session alive if you can (don't quit Claude Code) so mid-run resume via `/workflows` → `p`
  stays available.

## Verify

Before you walk away, confirm all five:
1. **Dry-run a slice** — one file/dir. Zero permission prompts appeared → allowlist is complete.
2. `/permissions` shows your deny rules present, and a deliberate `git push --force` attempt is blocked.
3. `/config` shows the size guideline you chose (or you accepted `unrestricted` knowingly).
4. Trigger the webhook once (finish a trivial task) and confirm the POST landed.
5. You've written down the resume story: how state persists and what happens if the session dies.

## Pitfalls

- **Assuming resume is durable.** It isn't across session exit — the workflow restarts fresh. This
  is the #1 surprise; chunk the work.
- **Using `ask` where you meant `deny`.** An `ask` rule pauses an unattended run forever. For
  circuit breakers, use `deny`.
- **Trusting argument-pattern denies as a security boundary.** They're best-effort. For real
  isolation, sandbox or containerize.
- **Forgetting MCP + WebFetch in the allowlist.** File edits auto-approve inside workflows, so
  people over-focus on Bash and get wedged on the first uncached MCP call.
- **Expecting the Large-workflow warning to stop the run.** It's advisory and doesn't pause
  anything; ultracode sessions don't even show it. Cap with a size guideline instead.
- **Relying on natural-language ambiguity.** Pre-v2.1.160 the literal trigger was `workflow`, now
  it's `ultracode`; if your keyword doesn't highlight, check the version and the `/config` toggle.
- **Workspace trust.** Project `allow` rules only take effect after you accept the workspace-trust
  dialog; in headless `-p` mode with an untrusted workspace they're silently ignored.
