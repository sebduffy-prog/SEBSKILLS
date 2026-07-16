---
name: openclaw-personal-agent-harness
category: building-agents
description: >
  Stand up and HARDEN a self-hosted OpenClaw personal-agent gateway (Steinberger's
  open-source assistant, formerly Clawdbot/Moltbot) that gives an LLM real bash, file
  read/write/edit and system access across chat channels (WhatsApp, Telegram, Slack,
  Discord, iMessage). Use to install OpenClaw, add ClawHub skills, pair a channel, or
  lock down the permission/sandbox model so the assistant is not an open remote shell.
  Teaches least-privilege harness discipline: pairing not open DMs, sandbox non-main,
  explicit skills allowlist, third-party skills as untrusted code. Ships a config
  hardening checker.
when_to_use:
  - Installing or onboarding OpenClaw and starting the gateway daemon on your own machine
  - Wiring a chat channel (WhatsApp/Telegram/Slack/Discord/iMessage) to a personal agent
  - Adding, auditing or pinning ClawHub skills/plugins and restricting which an agent can call
  - Reviewing an existing OpenClaw config for risky settings (open DMs, no sandbox, wildcard skills)
  - Explaining or enforcing least-privilege permission discipline for an agent with shell + file access
when_not_to_use:
  - You want an always-on agent LOOP with task queue, budget caps and watchdog, not a chat gateway — use `permanent-agent`
  - You are building an MCP server to expose tools to Claude/other hosts — use `mcp-builder`
  - You want a gated multi-agent self-improvement loop with external evals — use `moltbook`
  - You just need to run Claude Code with local tools in one session — use it directly, no gateway needed
keywords:
  - openclaw
  - clawdbot
  - moltbot
  - clawhub
  - personal-agent
  - self-hosted
  - gateway-daemon
  - shell-access
  - permission-model
  - sandbox
  - least-privilege
  - dm-policy
  - pairing
  - skills-allowlist
  - harness-discipline
  - steinberger
  - whatsapp-agent
  - untrusted-skills
similar_to:
  - permanent-agent
  - mcp-builder
  - moltbook
inputs_needed: Node 24 (or 22.19+) and npm; a model provider (hosted API key or a local model endpoint); at least one messaging channel to pair; optional ClawHub skill slugs; access to ~/.openclaw/openclaw.json.
produces: A running, hardened OpenClaw gateway (~/.openclaw/openclaw.json) with a paired channel, an explicit skills allowlist, non-main sandboxing, and a preflight hardening report from scripts/harden-check.sh.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# OpenClaw personal-agent harness

## When to use

OpenClaw is a self-hosted personal AI assistant (Peter Steinberger's project — shipped as
Clawdbot, renamed Moltbot, then OpenClaw). A persistent **gateway** daemon connects a model to
your chat apps and grants it real tools: `bash`, `process`, `read`, `write`, `edit`, plus
session tools. That power is the point and the danger — an unhardened gateway is a remote shell
anyone in a group chat can drive. Use this skill to install it AND to enforce a least-privilege
harness so it stays a personal assistant, not a liability.

Only harden gateways you own and are authorised to run. This skill is defensive: it locks down
your own machine, it does not attack anyone else's.

## Prerequisites (honest deps)

- **Node 24 recommended, or 22.19+** and npm/pnpm. No brew needed — install Node however you already do.
- A **model provider**: a hosted API key (e.g. an Anthropic/OpenAI key exported in env) or a local
  model endpoint. OpenClaw picks a provider/model via `agent.model` = `"<provider>/<model-id>"`.
- One **messaging channel** you can pair (WhatsApp, Telegram, Slack, Discord, Signal, iMessage, …).
- Config lives at **`~/.openclaw/openclaw.json`** (JSON5-ish; comments allowed).
- Full key reference: https://docs.openclaw.ai/gateway/configuration — treat this SKILL as the
  *discipline*; consult the live docs for the exhaustive key list, which evolves fast.

## Recipes

### 1. Install and start the gateway (daemon)

```bash
npm install -g openclaw@latest        # or: pnpm add -g openclaw@latest
openclaw onboard --install-daemon      # interactive: model, first channel, installs background daemon
openclaw gateway status                # confirm it is running
```

Debug in the foreground instead of the daemon:

```bash
openclaw gateway stop
openclaw gateway --port 18789 --verbose   # 18789 is the default gateway port
```

### 2. Pair a channel — never open the door wide

By default each channel uses **`dmPolicy="pairing"`**: an unknown sender gets a short pairing code
and their message is NOT processed until you approve it. Keep it that way.

```bash
# The bot DMs you (or a stranger) a code; you approve the specific channel+code:
openclaw pairing approve <channel> <code>
```

Do **not** set `dmPolicy="open"` with `"*"` in the allowlist unless you truly want anyone on that
channel to command your machine. `openclaw doctor` will flag risky DM policies — run it after any change.

### 3. Harden the permission model (the core of this skill)

Edit `~/.openclaw/openclaw.json`. Three levers matter most:

```json5
{
  agent: { model: "anthropic/claude-opus-4" },
  agents: {
    defaults: {
      // (a) Isolate non-primary sessions (group/channel spawns): off | non-main | all
      sandbox: { mode: "non-main" },
      // (b) LEAST PRIVILEGE: enumerate exactly which skills any agent may load.
      //     Unset here = every installed skill is exposed.
      skills: ["github", "weather"],
    },
    list: [
      // (c) Per-agent override. A NON-EMPTY list is the FINAL set — it does NOT merge
      //     with defaults. Use [] to give an agent zero skills.
      { id: "locked-down", skills: [] },
    ],
  },
}
```

Notes grounded in the docs:
- Default tools an agent can call: `bash, process, read, write, edit, sessions_list,
  sessions_history, sessions_send, sessions_spawn`. Narrowing *skills* is your main lever over
  what those tools get pointed at.
- Skill discovery is **path-contained**: only skill roots whose resolved realpath stays inside the
  configured root are loaded — do not defeat this with symlinks.
- Snapshots are created at **session start**; config/skill changes take effect on the next new
  session, giving a clean load-time audit point.

### 4. Add ClawHub skills — as untrusted code

Two equivalent paths. Prefer installing to the workspace, not global, so a skill's blast radius
is scoped:

```bash
# Native OpenClaw CLI (installs into the active workspace skills/ dir; --global for ~/.openclaw/skills)
openclaw skills install @owner/<slug>
openclaw skills install @owner/<slug> --global

# Or the ClawHub registry CLI
npm i -g clawhub
clawhub search "calendar"
clawhub info  @owner/<slug>
clawhub install "@owner/<slug>@1.2.0"    # pin a version — do not float
```

**Before enabling any third-party skill, read it.** Treat it as untrusted code that will run bash
on your machine:

```bash
openclaw skills verify @owner/<slug>          # integrity/metadata check
openclaw skills verify @owner/<slug> --card   # capability card
openclaw skills list                          # what is installed + enabled right now
# Then open the skill's SKILL.md and any scripts and READ them before adding to the allowlist.
```

### 5. Preflight audit (bundled helper)

Run the read-only checker before you expose the gateway to any channel. It flags open DMs,
disabled sandbox, and missing/wildcard skills allowlists — exit code 1 if anything is risky.

```bash
bash scripts/harden-check.sh ~/.openclaw/openclaw.json
```

### 6. Smoke-test the assistant

```bash
openclaw agent --message "summarise my day" --thinking high
openclaw message send --target +1234567890 --message "Hello from OpenClaw"
```

## Verify

- `openclaw gateway status` reports running.
- `openclaw doctor` reports **no** risky DM policies.
- `bash scripts/harden-check.sh` exits 0 (sandbox not `off`, no `dmPolicy:"open"`, explicit skills list).
- `openclaw skills list` shows only skills you have read and intended to enable.
- A message from an unpaired sender yields a pairing code, not an executed command.
- A locked-down agent (`skills: []`) refuses to run any skill.

## Pitfalls

- **`dmPolicy:"open"` = remote shell.** In a group channel this lets any member drive `bash` on your
  box. Keep `pairing`; approve explicitly.
- **Empty/unset `skills` allowlist exposes everything installed.** Enumerate; a per-agent non-empty
  list is final and does not merge with defaults — easy to accidentally grant more than intended.
- **`sandbox.mode:"off"`** removes isolation for spawned/group sessions. Use `non-main` at minimum.
- **Global skill installs** widen blast radius. Prefer workspace installs; reserve `--global` for
  skills you fully trust.
- **Third-party skills are code, not config.** A slug can ship a `scripts/` that runs on install/use.
  Read it and `verify` before enabling; pin versions — never let them float to `@latest`.
- **Secrets in `openclaw.json`.** Keep provider keys in env, not committed config; the file grants
  machine access, so treat it like an SSH key (`chmod 600`, never in a repo).
- **Config changes are lazy.** They apply on the next new session because snapshots freeze at session
  start — restart the session (or gateway) after hardening, then re-run `harden-check.sh` to confirm.
- **Docs move fast.** OpenClaw's key names evolve; if a key here is rejected, check the live
  configuration reference rather than forcing the old name.
