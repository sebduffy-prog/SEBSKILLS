---
name: claude-code-agent-teams
category: building-agents
description: >-
  Set up and drive Claude Code agent teams end-to-end: enable the experimental
  flag, spawn reusable teammate roles from subagent definitions, pick a display
  mode (in-process vs tmux/iTerm2 split panes), enforce TeammateIdle/TaskCreated/
  TaskCompleted exit-2 quality gates, isolate parallel edits with git worktrees,
  and fire proven spawn prompts (parallel PR review, adversarial-debug debate). Use
  when one Claude session should coordinate several that message each other, claim a
  shared task list, and challenge each other's findings.
when_to_use:
  - Coordinating multiple Claude Code sessions that must message each other, not just report back to a lead
  - Running a parallel code review where security, performance, and test-coverage each get a dedicated reviewer
  - Debugging with competing hypotheses via an adversarial "scientific debate" between teammates
  - Cross-layer feature work where frontend, backend, and tests are each owned by a different teammate
  - Defining a reusable teammate role once (as a subagent definition) and reusing it across sessions
  - Wiring exit-code-2 hooks so teammates cannot go idle or close tasks until a lint/test/policy gate passes
when_not_to_use:
  - Focused fan-out where only the result matters and workers never talk to each other — use dispatching-parallel-agents (subagents) instead
  - Sequential tasks, same-file edits, or heavy dependency chains — a single session is cheaper and safer
  - Building an MCP server to expose tools to Claude — use mcp-builder
  - Writing raw Anthropic SDK / Managed Agents code — use claude-api
  - Pure file isolation without coordination — just run separate `claude --worktree` sessions
keywords:
  - agent teams
  - claude code
  - teammates
  - subagents
  - tmux
  - iterm2 split panes
  - teammateidle
  - taskcompleted hook
  - exit code 2 gate
  - git worktree
  - sendmessage
  - shared task list
  - parallel review
  - adversarial debug
similar_to:
  - mcp-builder
  - claude-api
  - agent-code-sandbox
  - permanent-agent
inputs_needed: A git repo (for worktree isolation), Claude Code v2.1.178+ with the experimental flag enabled, and a task that genuinely benefits from parallel exploration (review, research, debugging, cross-layer feature).
produces: A running agent team — a lead session plus named teammates sharing a task list and mailbox — plus reusable subagent role definitions and settings.json hooks that gate idle/task transitions.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Code Agent Teams

Drive a **team** of Claude Code sessions: one lead coordinates, teammates work in
their own context windows, claim a shared task list, and message each other directly.
Unlike subagents (which only report back to the caller), teammates can challenge each
other's findings — what makes parallel review and adversarial debugging pay off.

## When to use

Reach for a team when workers must *talk to each other*: parallel PR review across
independent lenses, competing-hypothesis debugging, or a cross-layer feature where each
teammate owns a different slice of files. If workers only fan out and report a result,
use subagents (`dispatching-parallel-agents`) — teams cost far more tokens because every
teammate is a full, separate Claude instance.

## Prerequisites (read the honesty notes)

- **Experimental, off by default.** Gated behind the
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env var — without it no team forms and Claude
  won't spawn teammates. Everything below is documented as of **Claude Code v2.1.178+**
  and is still changing release-to-release — verify against
  https://code.claude.com/docs/en/agent-teams for your version.
- **Version churn.** `TeamCreate`/`TeamDelete` were removed in v2.1.178; teams now form
  automatically when the first teammate spawns and clean up on session exit. The `team_name`
  input on the Agent tool is accepted but ignored; the `team_name` hook field is deprecated.
- **Split panes need tmux or iTerm2.** In-process mode works anywhere; split panes are
  **not** supported in VS Code's integrated terminal, Windows Terminal, or Ghostty. `tmux`
  works best on macOS (`tmux -CC` in iTerm2 is the suggested entrypoint). iTerm2 native
  panes need the [`it2` CLI](https://github.com/mkusaka/it2) plus **iTerm2 → Settings →
  General → Magic → Enable Python API**.
- **Known limitations:** `/resume` and `/rewind` don't restore in-process teammates; task
  status can lag (teammates forget to mark complete, blocking dependents); one team per
  session; no nested teams; the lead is fixed for the session's lifetime.

Enable it in `~/.claude/settings.json`: `{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }` (or export the var in your shell), then restart Claude Code.

## Recipe 1 — Spin up a team and choose a display mode

1. Pick a display mode. Default is `"in-process"` (all teammates in your main terminal;
   up/down arrows select, Enter opens a teammate's transcript, Esc interrupts, `x` stops,
   Ctrl+T toggles the task list). Set `teammateMode` in `~/.claude/settings.json` for
   split panes — `"auto"` (split only if already in tmux **or** iTerm2+`it2`, else
   in-process), `"tmux"` (force split, auto-detect tmux vs iTerm2), `"iterm2"` (native
   panes, v2.1.186+, needs `it2`). Override per session with `claude --teammate-mode auto`.
2. Describe the work and teammates in natural language. Claude spawns only after you
   confirm:

   ```text
   I'm designing a CLI that tracks TODO comments across a codebase. Spawn three
   teammates to explore this from different angles: one on UX, one on technical
   architecture, one playing devil's advocate. Name them ux, arch, and skeptic.
   ```

   Naming teammates gives you stable handles to address later.

## Recipe 2 — Reusable teammate roles from subagent definitions

Define a role once and reuse it as both a delegated subagent and a team teammate. Any
subagent scope works (project, user, plugin, CLI-defined). Example at
`~/.claude/agents/security-reviewer.md`:

```markdown
---
name: security-reviewer
description: Audits code for security vulnerabilities.
tools: Read, Grep, Glob, Bash
model: sonnet
---
You are a security reviewer. Focus on token handling, session management, input
validation, injection, authz. Report issues with severity ratings.
```

Spawn it by name: `Spawn a teammate using the security-reviewer agent type to audit
src/auth/.` Honest caveats about what carries over:

- Honors the definition's `tools` allowlist and `model`; the body is **appended** to
  (not replacing) the teammate's system prompt. Team-coordination tools (`SendMessage`,
  the task tools) are **always** available even if `tools` restricts everything else.
- The `skills` and `mcpServers` frontmatter fields are **not** applied to a teammate —
  teammates load skills/MCP from your project/user settings and read `CLAUDE.md` from
  their working directory, like a normal session.
- Teammates don't inherit the lead's `/model` unless you set **Default teammate model →
  Default (leader's model)** in `/config`; they do inherit the lead's effort level.

## Recipe 3 — Exit-2 quality gates with hooks

Three team-lifecycle hook events can **block** a transition when the hook exits with
code 2; the hook's **stderr** is fed back to Claude as the reason. None of these events
support a `matcher` — they always fire.

| Event | Fires when | Exit 2 effect |
| :-- | :-- | :-- |
| `TeammateIdle` | a teammate is about to go idle | keeps the teammate working, feedback via stderr |
| `TaskCreated` | a task is being created | rolls back creation |
| `TaskCompleted` | a task is being marked complete | prevents completion |

Wire a gate in `~/.claude/settings.json` (no `matcher` key — it's silently ignored;
add a `TeammateIdle` block the same way):

```json
{
  "hooks": {
    "TaskCompleted": [
      { "hooks": [ { "type": "command", "command": "/abs/path/scripts/gate.sh" } ] }
    ]
  }
}
```

Hooks receive the common stdin fields (`session_id`, `transcript_path`, `cwd`,
`permission_mode`, `hook_event_name`, plus `agent_id`/`agent_type` inside a teammate).
**Honesty note:** event-specific payload fields (task id/description) are not documented
for these three events — don't hard-code field names you haven't seen. A robust gate runs
a project check and only exit-2s on failure:

```bash
#!/usr/bin/env bash
# scripts/gate.sh — block completion/idle until tests + lint pass.
set -euo pipefail
cat >/dev/null   # drain stdin; don't rely on undocumented fields
if ! npm test --silent >/tmp/gate.log 2>&1; then
  echo "Tests failing — fix before closing this task/going idle. See /tmp/gate.log" >&2
  exit 2
fi
exit 0
```

An alternative JSON control on stdout, `{"continue": false, "stopReason": "..."}`, stops
the teammate/task action entirely and shows `stopReason` to the user.

## Recipe 4 — Isolate parallel edits with git worktrees

Teams coordinate the *work*; worktrees isolate the *files*. The documented team
isolation strategy is **file ownership** — "break the work so each teammate owns a
different set of files" — because two teammates editing one file overwrite each other.
For stronger physical isolation, combine teams with worktrees:

- Start an isolated session per stream: `claude --worktree feature-auth` (creates
  `.claude/worktrees/feature-auth/` on branch `worktree-feature-auth`; add
  `.claude/worktrees/` to `.gitignore`). Base defaults to `origin/HEAD`; set
  `{"worktree": {"baseRef": "head"}}` to branch from local HEAD instead.
- Copy gitignored env files in with a `.worktreeinclude` file (`.gitignore` syntax).
- Subagent-level: add `isolation: worktree` frontmatter — each gets a temp worktree
  removed when it finishes clean. Whether a *teammate* inherits it is undocumented; don't
  assume it — prefer file ownership or per-stream `--worktree` sessions.
- Clean up orphans: `git worktree list`, then `git worktree remove <path>` (`--force`
  for uncommitted changes).

## Recipe 5 — Proven spawn prompts

**Parallel PR review (independent lenses):**

```text
Spawn three teammates to review PR #142:
- one focused on security implications
- one checking performance impact
- one validating test coverage
Have each review and report findings; then synthesize across all three.
```

**Adversarial-debug debate (competing hypotheses):**

```text
Users report the app exits after one message instead of staying connected.
Spawn 5 teammates to investigate different hypotheses. Have them talk to each
other to try to disprove each other's theories, like a scientific debate.
Update the findings doc with whatever consensus emerges.
```

**Require plan approval for risky work** (teammate stays in read-only plan mode until
the lead approves — it approves/rejects autonomously, so steer it with criteria):

```text
Spawn an architect teammate to refactor the auth module. Require plan approval
before they make any changes. Only approve plans that include test coverage.
```

## Verify

- `echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` prints `1` (or it's in settings `env`).
- After spawning, teammates appear in the agent panel (in-process) or as panes (split);
  `which tmux` and, for iTerm2, the `it2` CLI must resolve for split panes.
- Team/task state lands under `~/.claude/teams/session-XXXXXXXX/config.json` and
  `~/.claude/tasks/session-XXXXXXXX/` (name = `session-` + first 8 chars of the session
  id). The team config is removed on exit; the task dir persists per `cleanupPeriodDays`.
- Test a gate hook: make the check fail on purpose and confirm the teammate refuses to go
  idle / the task refuses to complete, with your stderr message shown.
- Orphaned tmux after exit? `tmux ls` then `tmux kill-session -t <name>`.

## Pitfalls

- **Don't pre-author `config.json`.** It holds live runtime state (session/pane IDs) and
  is overwritten on the next update. No recognized project-level `teams.json` exists.
- **Lead does the work itself / shuts down early.** Say "Wait for your teammates to
  complete their tasks before proceeding," or tell it to keep going — and check task
  status hasn't silently lagged (a common way dependents get stuck).
- **File conflicts.** Two teammates on one file = overwrites. Assign disjoint file sets
  or give each a worktree.
- **Token blowup.** Cost scales linearly with active teammates; start with 3–5 and ~5–6
  tasks each. Three focused teammates beat five scattered ones.
- **Permissions bubble to the lead.** A teammate can't approve prompts or relay consent
  on your behalf — approve at the lead. `--dangerously-skip-permissions` on the lead
  propagates to every teammate.
- **No resume for in-process teammates.** After `/resume`, the lead may message teammates
  that no longer exist — tell it to spawn fresh ones.
- **Idle rows hide, they don't stop.** An idle row hides ~30s after the whole panel goes
  idle (collapsing into `N idle agents` past three); the teammate stays running — message
  it by name to bring the row back.
