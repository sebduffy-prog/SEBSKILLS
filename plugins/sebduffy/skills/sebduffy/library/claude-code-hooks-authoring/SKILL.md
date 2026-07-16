---
name: claude-code-hooks-authoring
category: engineering-workflow
description: >-
  Author Claude Code settings.json hooks against the full 2026 event catalogue.
  Wire PreToolUse deny/ask gates, exit-code-2 feedback loops that block progress
  and hand stderr back to the model, PostToolUse updatedToolOutput rewrites,
  Stop-blocking test gates, and TeammateIdle / TaskCreated / TaskCompleted /
  Notification handlers. Reach for this whenever you want deterministic
  guardrails, matcher patterns, or want to know exactly which events honour a
  blocking exit code and which run advisory-only. Grounded on the official docs.
when_to_use:
  - Adding a PreToolUse guard that blocks or rewrites dangerous Bash/Edit calls
  - Building a Stop or PostToolBatch gate that forces tests/lint to pass before Claude finishes
  - Rewriting a tool's result with PostToolUse updatedToolOutput or injecting additionalContext
  - Reacting to agent-team lifecycle events (TeammateIdle, TaskCreated, TaskCompleted, Notification)
  - Choosing between exit-code-2 and structured JSON output for a hook decision
  - Deciding which settings scope (user, project, local, plugin, skill frontmatter) a hook belongs in
when_not_to_use:
  - Writing the SKILL.md / frontmatter of a skill itself — use skill-creator
  - Changing permissions, env vars, or non-hook settings.json keys — use update-config
  - Authoring an MCP server that a hook merely calls — use mcp-builder
  - You want a one-off recurring cloud task, not a lifecycle hook — use schedule
keywords:
  - claude-code
  - hooks
  - settings.json
  - pretooluse
  - posttooluse
  - exit-code-2
  - updatedtooloutput
  - matcher
  - permissiondecision
  - stop-hook
  - teammateidle
  - taskcreated
  - guardrails
  - additionalcontext
  - hookspecificoutput
similar_to:
  - update-config
  - mcp-builder
  - skill-creator
inputs_needed: The behaviour you want to enforce, the tool(s)/events to target, and which settings scope to install into
produces: A validated hooks block in settings.json plus any command/HTTP hook scripts, with the correct blocking semantics
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Code Hooks Authoring

Hooks are the deterministic guardrail layer under Claude Code: shell commands,
HTTP endpoints, MCP tools, or LLM prompts that fire on lifecycle events and can
**allow, deny, rewrite, or add context** to what the model does. Unlike a prompt
instruction, a hook always runs. This skill authors them accurately against the
2026 event catalogue.

## When to use

Use it when you want a rule enforced mechanically rather than hoped-for: block
`rm -rf`, force a lint pass before Claude stops, redact secrets out of a tool
result, or notify a teammate when a task completes. See the frontmatter triggers.

## Prerequisites

- Claude Code with hooks support (the event set below reflects the docs as of
  mid-2026; some fields are version-gated — e.g. `prompt_id` is v2.1.196+ and a
  few events are recent additions). **Always confirm against your installed
  version** via `claude --version` and https://code.claude.com/docs/en/hooks
  before relying on a newer event.
- `jq` for parsing hook stdin JSON in `command` hooks (any recent version).
- Decide scope up front — hooks live in `~/.claude/settings.json` (all projects,
  local only), `.claude/settings.json` (project, committable), `.claude/settings.local.json`
  (gitignored), managed policy settings (org-wide), plugin `hooks/hooks.json`, or
  skill/agent frontmatter (active only while that component is loaded).
- Security: a hook runs arbitrary code with your credentials on every matching
  event. Never put secrets in `command` strings; use `allowedEnvVars` for HTTP
  headers. Review hooks like any other executable in your repo.

## The event catalogue (30 events)

Lifecycle order: `SessionStart`, `Setup`, `UserPromptSubmit`, `UserPromptExpansion`,
`PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`,
`PostToolUseFailure`, `PostToolBatch`, `Notification`, `MessageDisplay`,
`SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`,
`StopFailure`, `TeammateIdle`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`,
`FileChanged`, `WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `PostCompact`,
`Elicitation`, `ElicitationResult`, `SessionEnd`.

## Config shape

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/guard.sh",
            "if": "Bash(rm *)",
            "timeout": 30 }
        ]
      }
    ]
  }
}
```

- `matcher` selects which occurrences fire. `"*"`, `""`, or omitted = all. Plain
  strings match the tool name exactly or as a `|`-list (`Edit|Write`); anything
  with regex metacharacters is treated as an **unanchored JS regex**
  (`mcp__memory__.*`, `^Notebook`). For non-tool events the matcher matches a
  source string instead (e.g. `Notification` matches `permission_prompt` /
  `idle_prompt`; `SessionStart` matches `startup` / `resume` / `clear`).
- `if` is a finer permission-rule filter — `Bash(git *)`, `Edit(*.ts)`. Bash
  patterns strip leading env assignments and check each `&&`/`$()` subcommand,
  and **fail open** (no match still runs) so a guard must inspect, not assume.
- Handler `type` is one of `command`, `http`, `mcp_tool`, `prompt`, `agent`.
  `${CLAUDE_PROJECT_DIR}` / `${CLAUDE_PLUGIN_ROOT}` are substituted and exported.

## Recipes

### 1. Block a dangerous command (PreToolUse, structured deny)

Hooks receive the event JSON on stdin. Emit a `permissionDecision` and exit 0:

```bash
#!/bin/bash
cmd=$(jq -r '.tool_input.command' < /dev/stdin)
if echo "$cmd" | grep -qE 'rm -rf|dd if=/dev|:\(\)\{'; then
  jq -n '{hookSpecificOutput:{hookEventName:"PreToolUse",
    permissionDecision:"deny",
    permissionDecisionReason:"Destructive command blocked by guard"}}'
fi
exit 0
```

`permissionDecision` is one of `allow`, `deny`, `ask`, `defer`. Returning
`updatedInput` instead rewrites the tool call (e.g. force `npm run lint`).

### 2. Exit-code-2 feedback loop (block + hand stderr to the model)

The terse alternative to structured JSON: **write to stderr, exit 2**. On a
blocking event the model reads that stderr and reacts. This is the core
guardrail idiom.

```bash
#!/bin/bash
file=$(jq -r '.tool_input.file_path' < /dev/stdin)
case "$file" in
  *.env|*secrets*) echo "Refuse: do not edit secret file $file" >&2; exit 2 ;;
esac
exit 0
```

**Which events honour exit 2 as blocking** (this is the trap): `PreToolUse`,
`PermissionRequest`, `UserPromptSubmit`, `UserPromptExpansion`, `Stop`,
`SubagentStop`, `PostToolBatch`, `TeammateIdle`, `TaskCreated`, `TaskCompleted`,
`ConfigChange`, `PreCompact`, `WorktreeCreate`, `Elicitation`, `ElicitationResult`.
On **`PostToolUse` / `PostToolUseFailure` exit 2 does NOT undo the tool** (it
already ran) — it only surfaces stderr. `PermissionDenied` ignores the exit code
entirely. Don't wire a "block" you think you have but don't.

### 3. Rewrite a tool result (PostToolUse updatedToolOutput)

PostToolUse cannot un-run the tool, but it can **replace what Claude sees**.
Redact secrets, or swap a noisy result for a clean summary:

```bash
#!/bin/bash
out=$(jq -r '.tool_output' < /dev/stdin)
clean=$(echo "$out" | sed -E 's/(sk-[A-Za-z0-9]{20,})/[REDACTED]/g')
jq -n --arg c "$clean" '{hookSpecificOutput:{hookEventName:"PostToolUse",
  updatedToolOutput:$c,
  additionalContext:"Secrets were redacted from this output."}}'
```

### 4. Stop gate — force tests green before Claude finishes

`Stop` fires when Claude tries to end its turn. Return `decision:"block"` with a
`reason` (or exit 2) to keep it working:

```bash
#!/bin/bash
if ! npm test --silent > /tmp/t.log 2>&1; then
  jq -n '{decision:"block",
    reason:"Tests failing — fix before finishing.",
    hookSpecificOutput:{hookEventName:"Stop",
      additionalContext:"See /tmp/t.log for failures."}}'
  exit 0
fi
exit 0
```

Guard against infinite loops: check `permission_mode` or a marker so the gate
can eventually pass.

### 5. Agent-team lifecycle (TeammateIdle / TaskCreated / TaskCompleted / Notification)

These are matcher-less (or source-matched). `TaskCompleted` and `TeammateIdle`
are **blocking** — exit 2 keeps the task/teammate active. Use `Notification`
(non-blocking) to ping Slack or emit a `terminalSequence` desktop alert:

```json
"Notification": [
  { "matcher": "idle_prompt",
    "hooks": [{ "type": "command",
      "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/ping-slack.sh" }] }
]
```

### 6. Inject context without blocking

Any event that supports `additionalContext` (SessionStart, UserPromptSubmit,
PreToolUse, PostToolUse, Stop, …) can feed Claude a fact — branch name, "this
file is generated, edit the source instead", failing-test paths — without
altering control flow. Exit 0 with the JSON; no `decision` needed.

## Verify

1. Lint the block: `python3 scripts/validate_hooks.py .claude/settings.json`
   (flags unknown event names, bad handler types, and lists which configured
   events run advisory-only so you don't expect a phantom block).
2. Dry-run a `command` hook by piping a fake event:
   `echo '{"tool_input":{"command":"rm -rf /"}}' | .claude/hooks/guard.sh; echo "exit=$?"`
   — confirm `exit=2` (or the deny JSON) for the case you meant to block.
3. In Claude Code run `/hooks` to see the registered hooks, then trigger the real
   tool and confirm the block/rewrite/context actually lands.

## Pitfalls

- **Wrong event for a block.** The #1 mistake: expecting `PostToolUse` exit 2 to
  cancel a write. It can't — the tool already ran. Use `PreToolUse` to prevent,
  `PostToolUse` to redact/annotate. See recipe 2's blocking-events list.
- **Matcher regex surprises.** `Edit.Write` is a regex (the `.` matches any
  char) and will over-match; you meant `Edit|Write`. Keep matchers to plain
  names/lists unless you truly want regex.
- **`if` fails open.** A Bash `if` pattern that doesn't match still runs the
  hook, so the script itself must decide — never treat "hook ran" as "pattern
  matched".
- **Version drift.** The 30-event catalogue and fields like `updatedToolOutput`,
  `prompt_id`, `PostToolBatch`, and agent-team events are recent; older installs
  have fewer. Confirm against your `claude --version` and the live docs before
  shipping a hook that depends on a newer one. The validator's unknown-event
  WARN is a "double-check", not proof of a typo.
- **Silent JSON errors.** Malformed hook stdout is ignored, not surfaced loudly.
  Validate your `jq` emits parseable JSON; exit 0 after emitting.
- **Timeouts and blocking.** Default command/http/mcp_tool timeout is 600s;
  a slow synchronous hook stalls the session. Use `"async": true` (or
  `asyncRewake`) for long, non-blocking work.
- **Secrets in config.** `command` strings and matchers are plaintext in
  settings. Put tokens in env vars and whitelist via HTTP `allowedEnvVars`.
- **`disableAllHooks`.** User-level `disableAllHooks:true` turns off user/project/
  local hooks but not managed-policy hooks; only managed-level can disable those.
