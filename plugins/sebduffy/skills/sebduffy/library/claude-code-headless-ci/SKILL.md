---
name: claude-code-headless-ci
category: devops
description: >-
  Run Claude Code unattended in pipelines — `claude -p` (print/headless mode) scoped with
  `--allowedTools`, locked down with `--permission-mode dontAsk`, parsed via
  `--output-format json` + `jq`, and wired into anthropics/claude-code-action@v1 for
  @claude PR mentions, per-PR review/fix jobs, and nightly cron. Budget against the
  separate Agent-SDK credit pool Anthropic announced for headless/CI usage (paused as of
  July 2026 — verify before you rely on it). Reach for this when someone says "review every
  PR with Claude", "run Claude in CI", "claude -p in a GitHub Action", "nightly Claude
  triage", or "keep bot runs off my interactive quota".
when_to_use:
  - Adding a Claude reviewer or auto-fixer that runs on every pull request without a human at the keyboard
  - Scripting `claude -p` in CI/cron and needing to scope tools, suppress permission prompts, and parse JSON output
  - Wiring anthropics/claude-code-action@v1 for @claude mentions, scheduled jobs, or code review
  - Capturing cost/turns/session-id from each run to fail the build, budget spend, or chain follow-ups
  - Separating unattended bot token spend from your interactive Pro/Max subscription usage
when_not_to_use:
  - Authoring the surrounding matrix/caching/OIDC pipeline mechanics — use github-actions-pipelines
  - Building a long-running Python/TypeScript agent with callbacks and native message objects — use claude-api (Agent SDK)
  - Interactive local pair-programming in the terminal — just run `claude` without `-p`
keywords:
  - claude-code
  - headless
  - claude -p
  - ci-cd
  - github-actions
  - allowedtools
  - output-format-json
  - permission-mode
  - agent-sdk
  - pr-review
  - cron
  - non-interactive
  - jq
  - token-budget
  - dontask
similar_to:
  - github-actions-pipelines
  - incident-response-and-postmortem
inputs_needed: A repo with CI (GitHub Actions or similar); an ANTHROPIC_API_KEY secret; Claude Code v2.1+ on the runner (or the SDK-bundled binary); the task prompt and the exact tools it needs.
produces: A headless `claude -p` command or `claude-code-action@v1` workflow, tool-scoped and permission-locked, that reviews/fixes/triages on PR or cron and emits parseable JSON (result, cost, turns, session_id).
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Code headless in CI

Run Claude Code as a non-interactive step in a pipeline: no TTY, no approval prompts, one
prompt in, one machine-readable result out. The two doors are the raw CLI (`claude -p`) and
the packaged GitHub Action (`anthropics/claude-code-action@v1`). This skill covers scoping,
locking down permissions, parsing output, triggers, and budget.

## When to use

Reach for this the moment a bot — not a person — should drive Claude: a reviewer on every
PR, a nightly triager, a `git diff | claude -p` linter in `package.json`, or a "@claude fix
this" responder on issues. If a human is watching the terminal, you don't need it — just run
`claude`.

## Prerequisites

- **Claude Code CLI v2.1+** on the runner, or the TypeScript Agent SDK (`@anthropic-ai/claude-agent-sdk`), which bundles a native binary. The Python SDK (`claude-agent-sdk`) needs Python **3.10+** — this Mac's system `python3` is 3.9, so use a runner image or a newer interpreter, not the stock macOS one.
- **Auth via API key.** Headless runs should use `ANTHROPIC_API_KEY` (a GitHub secret), or a provider: `CLAUDE_CODE_USE_BEDROCK=1` / `CLAUDE_CODE_USE_VERTEX=1` with cloud creds. `--bare` mode skips OAuth/keychain entirely and *requires* `ANTHROPIC_API_KEY` or an `apiKeyHelper`. Note: Anthropic does not permit third-party products to resell claude.ai login for SDK/headless use.
- **Billing reality (verify — this shifts).** In mid-2026 Anthropic *announced* that `claude -p`, the Agent SDK, and the GitHub Action would stop drawing on your interactive Pro/Max subscription and instead bill from a separate monthly **Agent SDK credit pool** at standard API rates (proposed ~$20 Pro / ~$100 Max 5x / ~$200 Max 20x). **That change was paused before taking effect** — as of July 2026 headless usage still draws on existing subscription limits, and Anthropic said it would rework the plan with advance notice. Design for the split (keep bot spend separable, track cost per run) but check the current [pricing](https://claude.com/platform/api) / [costs](https://code.claude.com/docs/en/costs) docs before you assume which pool you're spending.
- On GitHub-hosted runners you also pay **Actions minutes** (compute), separate from Claude tokens.

## Recipes

### 1. The minimal locked-down headless call

Scope tools explicitly and never prompt. `-p` (`--print`) is non-interactive; it reads stdin
and writes the result to stdout.

```bash
claude -p "Run the test suite and fix any failures" \
  --allowedTools "Bash(npm test),Read,Edit" \
  --permission-mode dontAsk \
  --max-turns 15 \
  --output-format json
```

- `--allowedTools` uses **permission-rule syntax**: `Read`, `Edit`, or scoped `Bash(npm test)` / `Bash(git diff *)`. The trailing space before `*` matters — `Bash(git diff *)` prefix-matches any `git diff …`, while `Bash(git diff*)` would also swallow `git diff-index`. Comma-separated, quote the whole list.
- `--permission-mode dontAsk` denies anything not in your allow rules or the built-in read-only set — the right baseline for a locked CI run. `acceptEdits` is looser (auto-writes files plus `mkdir/touch/mv/cp`). Without either, a tool not on the allowlist aborts the run rather than hanging.
- `--max-turns` caps the agent loop so a stuck run can't burn budget forever.
- Prefer **piping the diff in** over granting Bash: `git diff main | claude -p "review this"` needs no Bash permission at all. (stdin is capped at 10MB; write huge inputs to a file and reference the path.)

### 2. Parse the JSON result

`--output-format json` emits one final result object. Typical fields: `type: "result"`,
`subtype` (`success` / `error_max_turns` / `error_during_execution`), `is_error`, `result`
(the text answer), `session_id`, `num_turns`, `duration_ms`, `total_cost_usd`, and a `usage`
/ per-model cost breakdown. Pull what you need with `jq`:

```bash
out=$(claude -p "Summarize this PR's risk" --output-format json --permission-mode dontAsk)
echo "$out" | jq -r '.result'                       # the text
echo "$out" | jq -r '.total_cost_usd'               # spend this run
echo "$out" | jq -e '.is_error == false' >/dev/null || exit 1   # fail the job on error
```

For a **typed** answer, add `--json-schema '<JSON Schema>'`; the structured value lands in a
`structured_output` field (invalid schema → non-zero exit with `Error: --json-schema is not
a valid JSON Schema`). `format` keywords are accepted but not enforced.

For live logs use `--output-format stream-json --verbose` (newline-delimited events;
`--include-partial-messages` for token deltas). Watch for `system` `api_retry` subtypes to
surface throttling.

### 3. Faster, reproducible CI runs with `--bare`

`--bare` skips auto-discovery of hooks, skills, plugins, MCP servers, auto-memory and
CLAUDE.md — so a teammate's `~/.claude` hook or a stray `.mcp.json` can't change the result.
It's the recommended mode for scripted/CI calls (and is slated to become the `-p` default).
Load only what you pass explicitly:

```bash
claude --bare -p "Lint this diff for typos" \
  --allowedTools "Read" \
  --append-system-prompt "You are a terse typo linter." \
  --mcp-config ./ci.mcp.json \
  --model claude-sonnet-5
```

### 4. Reviewer on every PR (the packaged Action)

`anthropics/claude-code-action@v1` auto-detects tag mode (@claude mentions) vs automation
mode (a `prompt` runs immediately). CLI flags go through **`claude_args`**.

```yaml
name: Claude PR Review
on:
  pull_request:
    types: [opened, synchronize]
permissions:
  contents: read
  pull-requests: write
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Review this PR for correctness and security. Comment inline; do not push commits."
          claude_args: |
            --max-turns 12
            --model claude-sonnet-5
            --allowedTools "Read,Grep,Glob"
```

Read-only tools (`Read,Grep,Glob`) keep a reviewer from editing. For the maintained review
skill instead of a hand-written prompt, install the plugin and invoke its skill:

```yaml
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          plugin_marketplaces: "https://github.com/anthropics/claude-code.git"
          plugins: "code-review@claude-code-plugins"
          prompt: "/code-review:code-review ${{ github.repository }}/pull/${{ github.event.pull_request.number }}"
```

### 5. @claude mention responder + nightly cron

Mention mode (omit `prompt`; Claude answers when a comment contains the trigger phrase):

```yaml
on:
  issue_comment: { types: [created] }
  pull_request_review_comment: { types: [created] }
jobs:
  claude:
    if: contains(github.event.comment.body, '@claude')
    runs-on: ubuntu-latest
    permissions: { contents: write, pull-requests: write, issues: write }
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Nightly triage on a schedule:

```yaml
on:
  schedule:
    - cron: "0 8 * * *"
jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: "Summarize yesterday's merged PRs and label any stale open issues."
          claude_args: "--max-turns 8 --model claude-opus-5"
```

Set `trigger_phrase` to change `@claude`; `use_bedrock: "true"` / `use_vertex: "true"` +
`github_token` for cloud providers. Migrating from `@beta`: bump to `@v1`, drop `mode:`,
rename `direct_prompt`→`prompt`, and move `max_turns`/`model`/`allowed_tools` into
`claude_args`.

### 6. Chain runs with sessions

Capture `session_id` from JSON and `--resume` it (same working directory), or `--continue`
the most recent conversation:

```bash
sid=$(claude -p "Start a review" --output-format json | jq -r '.session_id')
claude -p "Now focus on the DB queries" --resume "$sid"
```

## Verify

- **Dry-run locally first:** `claude -p "echo hello via a tool" --allowedTools "Bash(echo *)" --permission-mode dontAsk --output-format json | jq -r '.result'` — confirms auth, tool scoping, and JSON shape before it ever hits CI.
- **Exit code + `is_error`:** headless exits non-zero on hard failure; also assert `jq -e '.is_error == false'` and check `subtype != "error_max_turns"` so a truncated run fails the job loudly.
- **Permission scoping actually bites:** temporarily ask Claude to do something outside the allowlist (e.g. `curl`) and confirm the run aborts rather than performing it.
- **Cost tracking:** sum `total_cost_usd` across runs; alert if a single PR run exceeds your ceiling.
- **Action wiring:** open a test PR / post `@claude` and confirm the job triggers, the App has Contents/Issues/PR read-write, and comments appear.

## Pitfalls

- **The token-pool split is announced-then-paused.** Do not tell stakeholders headless "won't touch your subscription" as settled fact — as of July 2026 it still does, and the separate Agent-SDK credit pool was pulled before launch. Re-check the docs; treat any credit figures as provisional.
- **No prompt-mode = it hangs or aborts, never asks.** In `-p` there is no human to approve. A tool that isn't allow-listed under `dontAsk` aborts the run. Scope tools deliberately; prefer piping data in over granting `Bash`.
- **`--allowedTools` glob spacing.** `Bash(git diff *)` (space) ≠ `Bash(git diff*)` — the latter also matches `git diff-index`. Over-broad `Bash(*)` hands the runner a shell; scope to the exact commands.
- **Local config leaks into "reproducible" runs.** Without `--bare`, `claude -p` loads hooks, MCP servers, CLAUDE.md and skills from the project and `~/.claude`, so results differ per machine. Use `--bare` and pass context via explicit flags for deterministic CI.
- **`--dangerously-skip-permissions` is not a CI shortcut.** It disables every guardrail; a prompt-injected PR diff could then run arbitrary commands with your secrets. Prefer `--permission-mode dontAsk` + a tight allowlist. Give the workflow least-privilege `permissions:` and never echo `ANTHROPIC_API_KEY`.
- **Beta→v1 breaking changes.** `mode:`, `direct_prompt`, `custom_instructions`, and top-level `max_turns`/`model`/`allowed_tools` are gone in `claude-code-action@v1`; everything CLI-ish moves into `claude_args`. Old workflows silently misbehave until migrated.
- **Runaway loops cost money.** Always set `--max-turns` and a workflow-level `timeout-minutes`; add `concurrency` to cancel superseded PR runs. Background dev-server shells started mid-run are killed ~5s after the final result; background subagents are waited on (capped ~10min via `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`).
- **Model IDs differ by provider.** Direct API uses names like `claude-sonnet-5`; Bedrock needs a region prefix (`us.anthropic.claude-sonnet-4-6`); Vertex uses `name@date`. A wrong ID surfaces as `model_not_found` in retry events.
