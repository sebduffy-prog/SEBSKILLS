---
name: dynamic-workflow-authoring
category: agent-frameworks
description: >
  Author, run, and save Claude Code dynamic-workflow scripts that move the plan out of the
  context window into JavaScript and fan out dozens-to-hundreds of subagents. Use to trigger
  a workflow (ultracode keyword), read the meta + agent()/pipeline() shape Claude generates,
  add adversarial cross-check stages, route stages to cheaper/stronger models, wire structured-
  output schemas, and save the run as a reusable /command. Grounds hard against the real
  Claude Code workflows docs — honest about version gates, the 16-concurrent / 1,000-agent
  caps, and which options are public vs SDK-only.
when_to_use:
  - A task needs more agents than one conversation can hold — codebase-wide audit, 500-file migration, multi-source research
  - You want the orchestration codified as a script you can read, diff, edit, and rerun
  - You need an adversarial verify stage so findings are cross-checked before they reach you
  - You want to route expensive reasoning to Opus and cheap fan-out to Haiku in one run
  - You want to save a repeatable review/triage as a project /command for the whole team
  - You are explaining or debugging a workflow script Claude already generated
when_not_to_use:
  - A few delegated tasks that fit one turn — use plain subagents or dispatching-parallel-agents instead
  - Long-running peer sessions with a shared task list — use agent teams (agent-orchestration-patterns) instead
  - Non-Claude-Code orchestration (LangGraph, CrewAI) — use langgraph-durable-workflows or crewai-flows-orchestration
  - Steps that need human sign-off mid-run — workflows take no mid-run input; use human-in-the-loop-approval
keywords:
  - dynamic-workflows
  - ultracode
  - claude-code
  - subagent-orchestration
  - agent
  - pipeline
  - fan-out
  - adversarial-verification
  - model-routing
  - effort
  - deep-research
  - meta-block
  - structured-output-schema
  - worktree-isolation
  - resumable
similar_to:
  - agent-orchestration-patterns
  - langgraph-durable-workflows
  - classifier-agent-routing
  - longhorizon-research-agent
  - crewai-flows-orchestration
inputs_needed: A task big enough to warrant fan-out; Claude Code v2.1.154+ on a paid plan (or API/Bedrock/Vertex/Foundry); tool allowlist for whatever the agents will run.
produces: A JavaScript workflow script (meta + agent()/pipeline() body) that runs in the background, a cited/verified result in-session, and optionally a saved /command in .claude/workflows/.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Dynamic Workflow Authoring

Dynamic workflows are the biggest orchestration primitive in Claude Code: Claude writes a
JavaScript script that spawns subagents at scale, a runtime executes it in the background, and
**only the final answer lands in your context** — every intermediate result stays in script
variables. This skill is how you drive that: trigger it, read the script it writes, shape it
(verify stages, model routing, schemas), and save it as a `/command`.

## When to use

Reach for a workflow when the task is bigger than one conversation can coordinate, or when you
want the orchestration codified so you can rerun it. Canonical shapes: a repo-wide bug/auth
sweep (one agent per file), a 500-file migration (each file in isolation), research that must be
cross-checked across sources, or a hard plan drafted from several angles before you commit.
For a VCCP power-user: audit every deck/data file in a project for a claim, fan a competitor
scan across many sources, or run the same review on every changed file of a build.

## Prerequisites (read the honest bits)

- **Version + plan.** Requires Claude Code **v2.1.154+**. Available on all paid plans, with
  Anthropic API access, and on Amazon Bedrock, Google Cloud's Agent Platform, and Microsoft
  Foundry. On **Pro**, turn it on from the *Dynamic workflows* row in `/config`. Run
  `claude update` if the `ultracode` keyword does nothing.
- **You rarely hand-write these.** The intended interface is: describe the task, Claude writes
  the script, you approve and (optionally) save it. Hand-editing is supported but the *full*
  option set for `agent()`/`pipeline()` lives in the **Workflow tool** entry of the Agent SDK
  reference and can change. The options confirmed in the public docs are `schema`, `label`, and
  `isolation: 'worktree'`; per-stage `model`/`effort` routing is documented as a capability
  ("route a stage to a different model") but the exact option surface is SDK-level — treat it as
  real but verify against the SDK ref before pinning a script to it.
- **Caps are hard.** Up to **16 concurrent agents** (fewer on limited CPU cores) and **1,000
  agents total per run**. A run over 25 agents or a projected 1.5M tokens shows a *Large
  workflow* warning (advisory only, v2.1.203+).
- **No mid-run input.** Only agent permission prompts can pause a run. For sign-off between
  stages, run each stage as its own workflow. The script itself has **no direct filesystem or
  shell access** — the *agents* read/write/run; the script only coordinates.
- **Permissions.** Spawned agents always run in `acceptEdits` and inherit your tool allowlist.
  Shell/web/MCP calls outside the allowlist can still prompt mid-run — add them before a long run.
- **Cost.** Every agent uses your session model unless a stage routes elsewhere; a run can burn
  far more tokens than a conversation. Check `/model` first; test on one directory before the repo.

## Recipes

### 1. Trigger a workflow for one task
Put `ultracode` in your prompt (Claude Code highlights it), or just ask in words — "use a
workflow" / "run a workflow" is the same opt-in. Before v2.1.160 the literal keyword was
`workflow`; natural language works in both.

```text
ultracode: audit every route handler under src/routes/ for missing auth checks,
and adversarially verify each finding before reporting it
```

Dismiss an unwanted highlight with `Option+W` (macOS) / `Alt+W`. Approve at the plan prompt
(**Yes, run it** / view raw script with `Ctrl+G` / edit the prompt with `Tab`).

### 2. Let Claude decide for the whole session
`ultracode` effort = `xhigh` reasoning **plus** automatic workflow orchestration on every
substantive task. One request can become several workflows (understand → change → verify).

```text
/effort ultracode          # this session; resets on new session
claude --effort ultracode  # start with it on (v2.1.203+)
```
Drop back with `/effort high` for routine work. Only offered on models that support `xhigh`.

### 3. Read the script Claude generated
Every run writes its script under your session dir in `~/.claude/projects/`; ask Claude for the
path to open/diff/edit it. The shape (from the docs) — a `meta` block then a plain-JS body with
top-level `await`:

```javascript
export const meta = {
  name: 'audit-routes',
  description: 'Audit every route handler for missing auth checks',
}

// agent(prompt, opts) spawns ONE subagent.
// Returns its final text — or a validated object when you pass a schema.
const found = await agent('List every .ts file under src/routes/.', {
  schema: {
    type: 'object',
    required: ['files'],
    properties: { files: { type: 'array', items: { type: 'string' } } },
  },
})

// pipeline(items, ...stages) runs ONE agent per item, per stage,
// with NO barrier between stages (item A can be in stage 3 while B is in stage 1).
const audits = await pipeline(found.files, file =>
  agent(`Audit ${file} for missing authentication checks.`, { label: file }),
)

return audits.filter(Boolean)
```

Key mechanics: `agent()` returns text or (with `schema`) a retried, validated object — always
pass a schema when a later stage consumes the result, so you get clean data not prose to parse.
`pipeline()` fans one agent per list item. `label` names agents in the `/workflows` progress view.

### 4. Add an adversarial cross-check stage
The whole point of moving the plan into code is a *repeatable quality pattern*, not just more
agents. Have an independent agent try to **refute** each finding against a rubric before it's
reported — this is exactly how bundled `/deep-research` votes on claims and filters those that
don't survive. Ask for it explicitly:

```text
ultracode: review every file changed in this PR for correctness bugs; for each finding,
spawn a separate agent whose only job is to refute it against a rubric, then merge the
survivors into one ranked, deduplicated summary
```

As of v2.1.196, when verifier agents *can't* check a claim (rate limit / API error) it's
reported as **unverified** rather than counted as refuted.

### 5. Route stages to cheaper/stronger models
Every agent uses your session model unless a stage routes elsewhere. In your prompt, say which
work is cheap fan-out vs deep reasoning:

```text
ultracode: classify each of these 200 tickets (use a fast/cheap model for the per-ticket
pass), then have one strong Opus-level agent synthesize the themes and priorities
```
Model aliases you can name: `haiku` (cheap fan-out), `sonnet` (default coding), `opus`
(deep reasoning), plus `sonnet[1m]`/`opus[1m]` for huge context. Check `/model` before a big run.

### 6. Migrate many files without edit conflicts
Ask for **isolation** so each agent edits its own copy (`isolation: 'worktree'` in the script):

```text
ultracode: migrate every component under src/components/ from styled-components to Tailwind,
working on each file in its own isolated copy, and verify each result compiles
```

### 7. Save and reuse as a /command
Run `/workflows`, arrow to the run, press `s`. `Tab` toggles the save location; `Enter` saves:
- `.claude/workflows/` — shared with everyone who clones the repo (in a monorepo it writes to the
  closest existing `.claude/workflows/` up to the repo root).
- `~/.claude/workflows/` — every project, only you.

It then runs as `/<name>` and appears in `/` autocomplete beside `/deep-research`. Project
workflows win over personal ones of the same name. Pass input via the `args` global:

```text
Run /triage-issues on issues 1024, 1025, and 1030
```
Claude passes structured data, so the script calls array/object methods on `args` directly.
If omitted, `args` is `undefined`.

## Verify

- **It actually launched as a workflow**, not turn-by-turn: the keyword highlights, and you get a
  plan-approval prompt listing phases. Then `/workflows` lists the running run.
- **Watch it**: `/workflows` → select → `Enter` drills into phases → agents (prompt, tool calls,
  result). `p` pause/resume, `x` stop, `r` restart an agent, `s` save, `f` filter by status.
- **Structured hand-off works**: stages that consume upstream results were given a `schema`
  (no brittle text parsing between phases).
- **Cost sanity**: token totals per agent are visible live; a *Large workflow* warning means
  >25 agents or >1.5M projected tokens — stop from `/workflows` if unintended.
- **Resume**: within the same session, a paused run resumes with completed agents cached. Exiting
  Claude Code loses that — the next session starts fresh.

## Pitfalls

- **Expecting mid-run prompts.** There's no interactive input during a run; only permission
  prompts pause it. Design multi-approval flows as separate sequential workflows.
- **No schema between stages.** Without `schema`, downstream stages parse prose and drift. If you
  can't define what each phase hands the next, the task probably belongs in one conversation.
- **Runaway fan-out.** The 1,000-agent cap bounds damage, but a bad `pipeline()` over a huge glob
  still burns tokens fast. Test on one directory; set *Dynamic workflow size* in `/config`
  (`small` <5, `medium` <15, `large` <50 agents) to keep generated scripts modest (v2.1.202+).
- **Assuming the script can touch files.** It can't — only agents do. Coordination logic lives in
  the script; all IO is delegated.
- **Pinning to undocumented options.** `schema`/`label`/`isolation` are public; the full
  `agent()`/`pipeline()` option surface (per-stage `model`, `effort`, concurrency) is SDK-level
  and may shift — prefer describing intent in the prompt over hand-coding fragile options.
- **Disabled in your org.** If `ultracode` does nothing: check `/config` (Dynamic workflows /
  Ultracode keyword trigger), `disableWorkflows` in settings, or `CLAUDE_CODE_DISABLE_WORKFLOWS`,
  and confirm v2.1.154+.
- **`/deep-research` needs WebSearch.** The bundled research workflow requires the WebSearch tool
  to be available in your allowlist.
