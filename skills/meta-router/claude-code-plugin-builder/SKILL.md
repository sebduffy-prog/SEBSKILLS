---
name: claude-code-plugin-builder
category: meta-router
description: >
  Scaffold, wire and ship a multi-component Claude Code plugin — one versioned
  bundle of skills, subagents, slash commands, hooks, output styles and MCP/LSP
  servers behind a single .claude-plugin/plugin.json — then publish it via a
  git-based or PRIVATE org marketplace.json that auto-installs to targeted user
  groups through managed settings. Reach for this on "package my skills as a
  plugin", "build a Claude Code marketplace", "distribute agents/hooks to my team",
  or "private plugin marketplace". Grounded on the live plugin docs so paths,
  manifest fields and CLI flags are real.
when_to_use:
  - You have skills/agents/hooks/MCP config and want them as ONE installable, versioned unit
  - You need to distribute a standard toolset to a team with private/org-only hosting
  - You want managed settings to force-enable specific plugins for a user group (stable vs latest channels)
  - You're converting a personal .claude/ setup into a shareable plugin + marketplace
  - You need a validated plugin skeleton (all component dirs) plus a marketplace catalog in one shot
when_not_to_use:
  - Authoring the CONTENT of a single SKILL.md — use skill-creator
  - Porting the library to non-Claude harnesses (Cursor, Codex, Copilot) — use skill-marketplace-packager
  - Building a standalone MCP server itself (tools/schemas/transport) — use mcp-builder
  - One-off personal config in .claude/ that never needs sharing — just edit .claude/ directly
keywords:
  - claude-code
  - plugin
  - plugin.json
  - marketplace
  - marketplace.json
  - subagents
  - hooks
  - mcp
  - output-styles
  - managed-settings
  - private-marketplace
  - enabledplugins
  - claude-plugin-init
  - versioning
  - distribution
similar_to:
  - skill-marketplace-packager
  - skill-adder
  - mcp-builder
inputs_needed: >
  A set of components to bundle (skills/, agents/, hooks/, .mcp.json, output-styles/);
  a plugin name and marketplace name (kebab-case); a git host for distribution
  (GitHub/GitLab/Bitbucket, public or private); optionally managed-settings access
  for org-wide auto-install.
produces: >
  A plugin tree with .claude-plugin/plugin.json + component dirs, a
  .claude-plugin/marketplace.json catalog, install/enable commands, and (optional)
  managed-settings JSON snippets for group targeting.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Code Plugin Builder

Turn loose skills, subagents, hooks, output styles and MCP/LSP servers into **one
versioned plugin**, catalog it in a **marketplace**, and distribute it — publicly,
or privately to your VCCP team via a private repo + managed settings.

## When to use

When the unit of work is *distribution*: you have the pieces (or can write them) and
now need them installable, updatable and pinned. To write one skill's body, use
`skill-creator` instead.

## Prerequisites

- **Claude Code** recent enough to have `/plugin` and the `claude plugin` CLI.
  Features are version-gated: `displayName` v2.1.143+, `defaultEnabled` v2.1.154+,
  `renames` v2.1.193+, `.zip` `--plugin-dir` v2.1.128+. Run `claude --version`; if
  `/plugin` is missing, upgrade. The surface is stable but evolving — re-check
  https://code.claude.com/docs/en/plugins-reference before relying on newer fields.
- **A git host** for the marketplace (GitHub `owner/repo` shorthand is the smoothest).
  Private repos work; see auth notes in Pitfalls.
- **Managed settings access** (`managed-settings.json`) is only needed for org-wide
  auto-install / channel targeting. Team-scope `.claude/settings.json` covers most
  cases without admin rights.
- `python3` (3.9 ok) if you use the bundled scaffolder.

## Core structure (ground truth)

A **plugin** is a directory. The manifest lives at `.claude-plugin/plugin.json`.
**Everything else sits at the plugin ROOT, never inside `.claude-plugin/`:**

```
my-plugin/
├── .claude-plugin/plugin.json   # manifest (name is the only required field)
├── skills/<name>/SKILL.md       # model-invoked skills
├── commands/<name>.md           # flat slash-command files (legacy; prefer skills/)
├── agents/<name>.md             # subagents
├── hooks/hooks.json             # event handlers
├── .mcp.json                    # MCP servers   (.lsp.json = language servers)
├── output-styles/<name>.md      # output styles
├── monitors/monitors.json       # background monitors (experimental)
└── bin/                         # executables added to PATH while enabled
```

A **marketplace** is a separate catalog at `.claude-plugin/marketplace.json` that
lists one or more plugins and where to fetch each (`source`). Plugin skills are
**namespaced**: `/my-plugin:hello`, not `/hello`.

## Recipes

### 1. Scaffold plugin + marketplace in one shot

The built-in `claude plugin init <name>` scaffolds a single plugin into
`~/.claude/skills/` but does **not** write a `marketplace.json`. Use the bundled
helper when you want a distributable tree (marketplace catalog + all component dirs):

```bash
python3 scripts/scaffold_plugin.py \
  --root ~/plugins --marketplace vccp-tools --plugin deploy-kit \
  --description "VCCP deploy helpers" --author "seb.duffy" \
  --with skills,agents,hooks,mcp,output-style
```

This emits `vccp-tools/.claude-plugin/marketplace.json` plus
`vccp-tools/plugins/deploy-kit/` with a valid `plugin.json` and starter files per
component. Edit the starters with your real content. For a single-purpose plugin you
won't distribute yet, `claude plugin init deploy-kit --with skills hooks` auto-loads
next session with no install step.

### 2. plugin.json — the minimum, plus what matters

```json
{
  "name": "deploy-kit",
  "displayName": "Deploy Kit",
  "description": "One-command deploy helpers for VCCP repos",
  "version": "1.0.0",
  "author": { "name": "seb.duffy", "email": "seb.duffy@vccp.com" },
  "license": "MIT",
  "keywords": ["deploy", "ci-cd"]
}
```

`name` is the **only** required field and is the namespace prefix. Component path
fields (`skills`, `agents`, `hooks`, `mcpServers`, `outputStyles`, `lspServers`)
are optional — omit them and Claude Code auto-discovers the default dirs above.

**Versioning is the trap.** If you set `version`, users only get updates when you
bump that string — push commits without bumping and existing installs stay stale.
Omit `version` (git-hosted) and every commit counts as a new version. Never set
`version` in both `plugin.json` and the marketplace entry — `plugin.json` silently
wins.

### 3. Reference bundled files correctly

Plugins are **copied to a cache** on install (`~/.claude/plugins/cache`), so `../`
paths break. In hooks/MCP/monitor commands use `${CLAUDE_PLUGIN_ROOT}` for bundled
files, and `${CLAUDE_PLUGIN_DATA}` for state that must survive updates (node_modules,
venvs, caches):

```json
{ "hooks": { "PostToolUse": [ { "matcher": "Write|Edit", "hooks": [
  { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/lint.sh" } ] } ] } }
```

### 4. marketplace.json — the catalog

```json
{
  "name": "vccp-tools",
  "owner": { "name": "VCCP DevTools", "email": "devtools@vccp.com" },
  "plugins": [
    { "name": "deploy-kit", "source": "./plugins/deploy-kit",
      "description": "Deploy helpers", "category": "productivity" },
    { "name": "brand-lint", "source": { "source": "github", "repo": "vccp/brand-lint" } }
  ]
}
```

`source` can be a `./relative` path (git-hosted marketplaces only — URL-hosted
catalogs don't copy plugin files), or an object: `github` (`repo`/`ref`/`sha`),
`url` (git URL), `git-subdir` (monorepo subdir, sparse clone), or `npm`. Pin an
exact commit with a full 40-char `sha`. Marketplace `name` must be kebab-case and
avoid the reserved Anthropic names (`claude-plugins-official`, `anthropic-plugins`,
etc. — the validator rejects them).

### 5. Install locally, then from the marketplace

```bash
claude --plugin-dir ./plugins/deploy-kit          # test in-place, no install
/plugin marketplace add ./vccp-tools              # add the catalog (local path)
/plugin install deploy-kit@vccp-tools             # install by name@marketplace
/plugin marketplace add vccp/vccp-tools           # or from GitHub owner/repo
```

`/reload-plugins` picks up edits without a restart (skills reload live; hooks,
`.mcp.json`, agents, output-styles need reload or restart).

### 6. Private / org distribution + group targeting

Host the marketplace in a **private git repo** — Claude Code reuses your git
credential helpers (`gh auth login`, keychain) for manual installs. For background
auto-updates at startup, set a token env var (`GITHUB_TOKEN`/`GH_TOKEN`,
`GITLAB_TOKEN`, `BITBUCKET_TOKEN`).

Auto-prompt a team to add the marketplace via project `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "vccp-tools": { "source": { "source": "github", "repo": "vccp/vccp-tools" } }
  },
  "enabledPlugins": { "deploy-kit@vccp-tools": true }
}
```

For **org-wide, non-optional** rollout and **channel targeting** (stable vs latest
per group), put `extraKnownMarketplaces` + `enabledPlugins` in the read-only
`managed-settings.json`, giving each group a marketplace pinned to a different
`ref`/`sha`. Lock down additions with `strictKnownMarketplaces` (`[]` = lockdown; a
list/`hostPattern` = allowlist). Ship opt-in-cost plugins `defaultEnabled: false`.

### 7. Convert an existing .claude/ into a plugin

`mkdir -p my-plugin/.claude-plugin`; write `plugin.json`; `cp -r .claude/skills
.claude/agents my-plugin/`; move the `hooks` object from `.claude/settings.json`
into `my-plugin/hooks/hooks.json` (same format). Then remove the originals from
`.claude/` — project `.claude/agents/` override same-named plugin agents.

## Verify

```bash
# schema + frontmatter + hooks JSON, per plugin and per marketplace
claude plugin validate ./vccp-tools
claude plugin validate ./vccp-tools/plugins/deploy-kit --strict   # warnings->errors, for CI
```

Then load it and confirm the components appear:
- `/help` lists the namespaced skill (`/deploy-kit:hello`).
- `/context` shows the subagent under Custom Agents.
- Trigger a matched tool call and confirm the hook fires.
- `/plugin` → Installed tab shows the plugin, its Skills section and enabled state.

## Pitfalls

- **`.claude-plugin/` holds ONLY `plugin.json`.** Putting `skills/`, `agents/`,
  `hooks/` inside it is the #1 mistake — they must be at the plugin root. There is
  no `~/.claude/.mcp.json`; `.mcp.json` lives at the *plugin* root.
- **Stale installs from a pinned `version`.** Bump `version` every release, or omit
  it entirely and let the commit SHA drive updates. Don't set it in two places.
- **Relative paths break after install** (copied to cache). Use
  `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_DATA}`, never `../`.
- **URL-hosted marketplaces don't copy plugin files** — `./relative` sources fail
  with "path not found". Use a git-hosted marketplace, or `github`/`npm`/`url`
  sources for each plugin.
- **Reserved marketplace names** (impersonating Anthropic) are rejected at load, even
  retroactively — pick a clearly-yours kebab-case name.
- **Managed settings are read-only to Claude Code** — a rename or force-enable there
  needs an admin edit; managed marketplaces are also non-removable by users.
- **Version-gated fields.** Old clients silently ignore `defaultEnabled`,
  `displayName`, `renames` — state a minimum Claude Code version in your README.
- **Private-repo auto-update needs a token env var**, not just an interactive login
  (startup can't prompt). Missing token = silent no auto-update.
