# SEBSKILLS — The Ultimate Claude Code / Claude Code Web Skills Framework

A curated, deduplicated, and categorized library of **Agent Skills** for [Claude Code](https://docs.claude.com/claude-code) (CLI, Desktop, Web, and IDE extensions). Drop this repo into any project and Claude gains a set of reusable superpowers for building, designing, debugging, and shipping.

> **What is a Skill?** A folder with a `SKILL.md` file. The YAML frontmatter (`name`, `description`) tells Claude when to invoke it; the body tells Claude what to do. Claude loads the description for every skill at session start and pulls in the full body only when the task matches. See the official spec: <https://agentskills.io/specification>.

---

## ⚡ Quick start — one file, `/sebduffy`, every LLM

Install **one file** and get all **436 skills**, fetched live from this public repo. Full guide: **[SETUP.md](SETUP.md)**.

**Claude Code (CLI / IDE):**
```bash
curl -fsSL https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/install-sebduffy.sh | bash
```
Then type `/sebduffy <what you want>` — e.g. `/sebduffy make a bento grid`, `/sebduffy list`, `/sebduffy media`.

**Any other LLM (ChatGPT, Gemini, Cursor, Codex…)** — paste this once:
> You have access to the SEBSKILLS library, indexed at `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/manifest.json`. For each task: fetch the manifest, pick the best skill by its keywords/description, fetch that skill from `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/` + its `path`, and follow it.

No server, no hosting — the **public repo is the network**, `raw.githubusercontent.com` is the CDN. New skills appear automatically. See **[SETUP.md](SETUP.md)** for Desktop, Web, API, and offline setups.

---

## TL;DR — install the full library (symlinks)

All three use the bundled installer. It creates symlinks to this repo; nothing is copied, so pulling new skills is a `git pull` away.

### 1. Shared user-level library (every Claude Code session)
```bash
git clone https://github.com/sebduffy-prog/sebskills ~/.claude/skills-lib
cd ~/.claude/skills-lib
./install.sh user
```
Every skill is now discoverable in every Claude Code session on this machine.

### 2. Project-local (only this project)
```bash
# from the root of your project
git clone https://github.com/sebduffy-prog/sebskills ../sebskills   # or submodule
../sebskills/install.sh project .
```
Skills are linked into `./.claude/skills/`; commit them if you want teammates to pick them up.

### 3. Claude Code Web (connect this repo as a second repo)
Add SEBSKILLS as a git submodule or connect it as a secondary repo in [claude.ai/code](https://claude.ai/code):
```bash
cd my-app
git submodule add https://github.com/sebduffy-prog/sebskills .claude/skills-lib
git commit -m "Add SEBSKILLS"
```
Push, then open the project on Claude Code Web. The web harness recursively discovers every directory containing a `SKILL.md` in any connected repo — no install step needed.

> For Windows or restricted environments where symlinks don't work, run `./install.sh web` to get the copy-based alternative.

---

## The catalogue

**436 skills across 31 categories.** The full, always-current list is in **[CATALOG.md](CATALOG.md)** — auto-generated from `manifest.json` by `scripts/build_manifest.py`, so it never drifts.

You rarely need to read it: just `/sebduffy <what you want>` routes to the right skill and does the task. To browse: `/sebduffy list` or `/sebduffy <category>`.

**Categories:** `3d` · `adtech-ops` · `agent-frameworks` · `agent-simulation` · `building-agents` · `commerce` · `compliance` · `context-engineering` · `data-analysis` · `devops` · `documents` · `engineering-workflow` · `finance-ops` · `frontend-and-design` · `marketing-science` · `mcp-connectors` · `media` · `meta` · `meta-router` · `ml` · `mobile` · `model-routing` · `product` · `rag` · `recipes` · `sales-crm` · `security` · `strategy` · `ui-effects` · `verification` · `voice-agents`

```
skills/<category>/<name>/SKILL.md      # one folder per skill, 10-field frontmatter
scripts/build_manifest.py              # regenerates manifest.json + CATALOG.md + REPORT.md + the /sebduffy index
skills/meta/sebduffy/SKILL.md          # the one-file router
```

## How to add your own project + use these skills

This repo is designed to sit **next to** or **inside** your project. Three patterns:

### Pattern A — sibling library (recommended for teams)
```
my-org/
├── my-app/                 # Your project
│   └── .claude/
│       └── skills/         # symlinks created by ../sebskills/install.sh project .
└── sebskills/              # This repo, cloned once, shared
```
```bash
cd my-app && ../sebskills/install.sh project .
```

### Pattern B — submodule (recommended for solo dev + Claude Code Web)
```bash
cd my-app
git submodule add https://github.com/sebduffy-prog/sebskills .claude/skills-lib
git commit -m "Add SEBSKILLS"
.claude/skills-lib/install.sh project .
```
For Claude Code Web, the submodule alone is enough — the web harness recursively discovers every `SKILL.md` in any connected repo. The `install.sh` step is only needed for the CLI / desktop / IDE versions.

### Pattern C — user-global (recommended for solo dev, one machine)
```bash
git clone https://github.com/sebduffy-prog/sebskills ~/.claude/skills-lib
~/.claude/skills-lib/install.sh user
```
Every project on this machine picks up every skill automatically. No per-project setup.

In all patterns, Claude Code discovers `SKILL.md` files at session start. To ship a subset instead of all 49, run the installer and then `rm` the symlinks you don't want — the originals stay in `skills/`.

---

## Adding a new skill

1. Pick a category folder in `skills/`.
2. Create `skills/<category>/<your-skill>/SKILL.md`:
   ```markdown
   ---
   name: your-skill
   description: One-paragraph trigger description. What it does, when to use it, example phrasings.
   ---

   # Your Skill

   ## When to use
   ## What to produce
   ## Implementation notes
   ```
3. (Optional) Add `assets/`, `examples/`, or scripts alongside.
4. Add a row to the category's `README.md` index.
5. Add a row to this README's quick index.

Full guidance: [`skills/building-agents/skill-creator`](skills/building-agents/skill-creator).

---

## Sources & attribution

This framework is a curated remix. Original authors and licenses are preserved within each skill directory.

| Source | Upstream | Covers |
|---|---|---|
| Anthropic official Skills | [`anthropics/skills`](https://github.com/anthropics/skills) | Most `frontend-and-design`, `documents`, `building-agents`, `media` skills |
| Obra Superpowers | [`obra/superpowers`](https://github.com/obra/superpowers) | Most `engineering-workflow` skills |
| Karpathy Guidelines | [`forrestchang/andrej-karpathy-skills`](https://github.com/forrestchang/andrej-karpathy-skills) | `karpathy-guidelines`, root `CLAUDE.md` |
| Framer UI Effects | Framer modules, re-implemented standalone | All `ui-effects/*` |
| Awesome catalog (inspiration) | [`VoltAgent/awesome-agent-skills`](https://github.com/VoltAgent/awesome-agent-skills) | Directory-layout inspiration |
| Native to this framework | — | `autonomy-policy`, `design-approval-gate` (MIT) |

Each skill retains its original `SKILL.md` and license file where included.

---

## License

This repository is a collection; each skill carries its own license. The repo structure, organizing READMEs, and index are MIT.
