---
name: skill-marketplace-packager
category: meta-router
description: >
  Package SEBSKILLS skills as portable, harness-agnostic bundles so the library installs
  beyond Claude Code — into Codex CLI, Cursor, OpenCode, GitHub Copilot and Gemini CLI —
  from one shared manifest. Reach for this on "make my skills work in Cursor/Codex/Copilot",
  "port the library to another agent", "publish as a plugin marketplace", or "export SKILL.md
  to .mdc/.toml". Maps each SKILL.md to every target's native format, emits per-harness
  install trees + a manifest.json catalog, and keeps the router (catalog + picker) portable.
  Complements skill-adder and /sebduffy (the Claude front door).
when_to_use:
  - You want the SEBSKILLS library usable in a non-Claude harness (Cursor, Codex, Copilot, OpenCode, Gemini)
  - Teammates are on mixed tools and you need one source of truth that emits every tool's native config
  - You're publishing skills as an installable plugin/marketplace others can pull
  - You changed a SKILL.md and need to re-emit all downstream harness bundles from the shared manifest
  - You want a build step that turns the whole skills/ tree into per-harness install directories
when_not_to_use:
  - You're authoring or iterating a single skill's content — use skill-creator
  - You're landing a NEW skill into the library with audit gates — use skill-adder (intake) first, then pack
  - You need to PICK which skill handles a request inside Claude — use automatic-skill-decision / the /sebduffy router
  - You're chaining several skills for one compound task — use skill-chaining-composer
keywords: [skill packaging, harness agnostic, portable skills, cursor rules, mdc, codex cli, opencode agent, copilot prompts, gemini cli, toml commands, agents.md, plugin marketplace, cross-tool, manifest, per-harness bundle, install command, skill export, interop]
similar_to: [skill-adder, skill-chaining-composer, automatic-skill-decision, skill-creator, skill-gap-detector]
inputs_needed:
  - One or more SKILL.md files (or the skills/ root) with valid frontmatter — at minimum non-empty name + description
  - A list of target harnesses to emit (default: all six — claude, cursor, opencode, copilot, codex, gemini)
  - An output directory for the emitted bundles (defaults to a dist/ tree)
produces: A dist/ tree with one native install bundle per target harness (Cursor .mdc rules, OpenCode agents, Copilot prompts, Codex prompts, Gemini TOML commands, Claude skills/plugin) plus a shared manifest.json catalog, and copy-paste install commands per target.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Skill Marketplace Packager

One SKILL.md, many homes. This skill compiles the SEBSKILLS library into a **native install
bundle for each major coding harness** from a single shared manifest, so the same capability
triggers whether a teammate is on Claude Code, Codex CLI, Cursor, OpenCode, GitHub Copilot or
Gemini CLI. It preserves the router idea — a catalog plus a picker — but makes it portable
instead of Claude-only.

## When to use

Reach for this once a skill's *content* is settled (authored via `skill-creator`, landed via
`skill-adder`) and the job is **distribution**: getting it into another agent's config format,
or re-emitting all bundles after an edit. It is the build/publish step, not the authoring or
intake step.

## Prerequisites

- `python3` (macOS system 3.9 is fine — the emitter is dependency-free, no YAML lib needed).
- The bundled emitter: `scripts/pack.py`.
- SKILL.md files whose frontmatter has at least a non-empty `name` and `description`
  (the two fields every target needs). Everything else degrades gracefully.

## Format map (the shared design)

Every SKILL.md is `frontmatter + markdown body`. The body is the instruction payload; only
`name` and `description` are lifted from the frontmatter. Each target gets its **native**
container — verified against each tool's current docs:

| Target | Emitted path | Container / trigger field |
|--------|--------------|---------------------------|
| claude | `claude/skills/<name>/SKILL.md` | native skill (frontmatter round-trips verbatim) |
| cursor | `cursor/.cursor/rules/<name>.mdc` | MDC rule — `description` + `globs` + `alwaysApply` |
| opencode | `opencode/.opencode/agents/<name>.md` | agent — `description` + `mode: subagent` |
| copilot | `copilot/.github/prompts/<name>.prompt.md` | prompt file — `mode: agent` + `description` |
| codex | `codex/.codex/prompts/<name>.md` | custom prompt — `description` + `argument-hint` |
| gemini | `gemini/.gemini/commands/<name>.toml` | TOML command — `description` + `prompt` |

Cursor's `description`/`globs`/`alwaysApply` drives its agent-requested vs auto-attach modes;
Gemini commands are TOML with a required `prompt` string; Codex scans only top-level `.md`
files in `~/.codex/prompts/`; OpenCode's filename becomes the agent id. For always-on context
(not a slash trigger) any target can also read a root **AGENTS.md** — the cross-tool standard —
which you can generate by concatenating the catalog (see Pitfalls).

## Mechanism / Steps

### Step 1 — Point the emitter at your skills

Pack a single skill, a few, or the whole tree. Inputs may be SKILL.md files or directories
(walked recursively for `SKILL.md`):

```bash
cd /Users/seb.duffy/Documents/GitHub/SEBSKILLS
python3 skills/meta-router/skill-marketplace-packager/scripts/pack.py \
  --skills skills/ \
  --out dist/
```

Restrict targets when you only care about some harnesses:

```bash
python3 .../pack.py --skills skills/meta-router --out dist/ \
  --targets cursor,codex,gemini
```

The emitter reads each SKILL.md, collapses the folded `description` to one line, writes the
six (or chosen) native files, and emits `dist/manifest.json` — the portable catalog
(`name`, `category`, `description`, `keywords`, `source`, `targets`) that any external picker
or marketplace index can consume. It exits non-zero and lists offenders if any SKILL.md is
missing `name`/`description`, so a broken frontmatter fails the build loudly.

### Step 2 — Inspect the bundle

```bash
find dist -maxdepth 3 -type d | sort
python3 -c "import json;m=json.load(open('dist/manifest.json'));print(len(m['skills']),'skills')"
```

Confirm each target dir contains the expected native container (`.mdc`, `.md`, `.toml`).

### Step 3 — Install into a target project

Each bundle is already shaped like the harness expects — copy the inner dotfolder to the
consuming repo (or `~` for user-global scope):

```bash
# Cursor (project-scoped rules)
cp -R dist/cursor/.cursor  /path/to/repo/
# Codex CLI (user-global prompts)
cp -R dist/codex/.codex    ~/
# Gemini CLI (user-global commands)
cp -R dist/gemini/.gemini  ~/
# OpenCode (project agents)
cp -R dist/opencode/.opencode /path/to/repo/
# Copilot (repo prompts)
cp -R dist/copilot/.github     /path/to/repo/
# Claude Code (native skills)
cp -R dist/claude/skills/*     /path/to/repo/.claude/skills/
```

### Step 4 — Publish as a marketplace (optional, Claude plugin)

To distribute the Claude bundle as an installable plugin, add a `.claude-plugin/plugin.json`
manifest referencing the emitted `skills/` dir, and a repo-root `.claude-plugin/marketplace.json`
listing the plugin. Users then `/plugin marketplace add <owner>/<repo>` and install. The
`manifest.json` this skill emits is the neutral catalog those wrappers point at — one source
of truth, many install fronts.

### Step 5 — Re-emit on change

Packing is idempotent and cheap. After editing any SKILL.md, re-run Step 1 to regenerate every
downstream bundle so no harness drifts from the source. Wire it into CI or a pre-publish hook.

## Verify

```bash
# 1. Round-trip a known skill through all targets and assert one file per harness.
OUT=$(mktemp -d)
python3 skills/meta-router/skill-marketplace-packager/scripts/pack.py \
  --skills skills/meta-router/skill-adder --out "$OUT"
test -f "$OUT/cursor/.cursor/rules/skill-adder.mdc"          && echo "cursor OK"
test -f "$OUT/gemini/.gemini/commands/skill-adder.toml"      && echo "gemini OK"
test -f "$OUT/codex/.codex/prompts/skill-adder.md"           && echo "codex OK"
test -f "$OUT/claude/skills/skill-adder/SKILL.md"            && echo "claude OK"
python3 -c "import json;print('manifest', len(json.load(open('$OUT/manifest.json'))['skills']))"

# 2. Broken frontmatter must fail the build (non-zero exit).
BAD=$(mktemp -d)/SKILL.md; printf -- '---\nname: x\n---\nbody\n' > "$BAD"
python3 .../pack.py --skills "$(dirname "$BAD")" --out "$(mktemp -d)"; echo "exit=$?  (expect 1)"
```

Green means: every requested target produced its native file, the catalog counted the skills,
and a `description`-less skill halted the build instead of shipping a hollow bundle.

## Pitfalls

- **Description is the trigger everywhere.** Cursor agent-requested activation, Codex/Gemini
  `/help` listings and Copilot prompt discovery all lean on `description`. A vague one that
  triggers in Claude may never fire elsewhere — tune it in the source SKILL.md (see
  `skill-creator`), not per-bundle, or you lose single-source-of-truth.
- **`references/` and `scripts/` don't travel.** The emitter ships the SKILL.md body only.
  Skills that shell out to bundled assets need those files copied alongside, or the paths
  rewritten to a fetchable location — flag such skills before packing.
- **Body assumes Claude tools.** Instructions mentioning Claude-only tool names won't have
  equivalents in Gemini/Codex. Keep bodies tool-agnostic where portability matters, or gate
  tool-specific steps behind an "if your harness has X" clause.
- **Scope differs per tool.** Cursor/OpenCode/Copilot are project-scoped (dotfolder in the
  repo); Codex/Gemini prompts are user-global by default. Decide scope per target at install
  (Step 3), don't assume one placement fits all.
- **Codex deprecation drift.** Codex now nudges "skills" over custom prompts; the prompt
  emitter still works today but re-verify against current Codex docs before a big publish.
- **Always-on vs slash.** These bundles are invocable (slash/agent-requested). For passive
  always-loaded guidance, generate a root `AGENTS.md` from the catalog instead — it's the
  cross-tool standard read by Codex, Cursor, Copilot, OpenCode and Claude alike.
