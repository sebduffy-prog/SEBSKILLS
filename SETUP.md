# SEBSKILLS — Setup Guide (`/sebduffy` for every LLM)

**The whole idea in one line:** install **one file**, type **`/sebduffy`**, and get all **333 skills** — fetched live from this public repo. No server to deploy, no per-skill install, and new skills appear automatically.

This works because every skill is just a Markdown file (`SKILL.md`) at a **public URL**. GitHub's raw CDN is the "skills network"; the `/sebduffy` router is a single file that carries the catalogue and fetches any skill on demand.

- **Repo (source of truth):** `https://github.com/sebduffy-prog/SEBSKILLS` (public, branch `main`)
- **Router file:** `skills/meta/sebduffy/SKILL.md`
- **Machine-readable index:** `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/manifest.json`

---

## 1. Claude Code (CLI or IDE extension) — fastest

**One-line install** (drops the single router file into `~/.claude/skills/sebduffy/`):

```bash
curl -fsSL https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/install-sebduffy.sh | bash
```

Then in any Claude Code session:

```
/sebduffy make a bento grid            # routes to the best skill and loads it
/sebduffy list                         # browse the whole catalogue
/sebduffy media                        # list one category
/sebduffy ffmpeg-cookbook              # load a specific skill by name
/sebduffy search audience              # show matches without auto-loading
```

**Prefer the whole library installed locally?** (faster, works offline)

```bash
git clone https://github.com/sebduffy-prog/SEBSKILLS ~/.claude/skills-lib
~/.claude/skills-lib/install.sh user      # every session, all 333 skills discoverable
# or:  install.sh one    → just the /sebduffy router
# or:  install.sh project .   → only the current project
```

`/sebduffy` uses a **local-first** fetch ladder: if a skill is installed it uses that copy; otherwise it fetches from GitHub. So the installer and the one-file router coexist.

---

## 2. Claude Desktop

1. Download the router file: `skills/meta/sebduffy/SKILL.md`
   (`curl -O https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/skills/meta/sebduffy/SKILL.md`)
2. Add it as a Skill in Desktop.
3. Ask "**/sebduffy build me a quick dashboard**" — it routes and loads the skill body over the web.

(Or clone the repo and run `./install.sh user` if your Desktop reads `~/.claude/skills/`.)

---

## 3. Claude.ai Web / Projects

- **Connect this repo** as a source in [claude.ai/code](https://claude.ai/code), *or* add it as a git submodule in your project:
  ```bash
  git submodule add https://github.com/sebduffy-prog/SEBSKILLS .claude/skills-lib
  ```
- Every `SKILL.md` becomes discoverable automatically. Say `/sebduffy <intent>` to route.

---

## 4. Claude API / Agent SDK

Give your agent the router as context, and a web-fetch (or bash) tool:

1. Fetch the router once and put it in your **system prompt** (or register it as a skill):
   `GET https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/skills/meta/sebduffy/SKILL.md`
2. When a user request comes in, the router logic ranks the embedded catalogue, picks a skill, and **fetches that skill's body** from
   `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/<path>` (the `path` is in `manifest.json`).
3. If your agent has no web tool, pre-bundle the manifest and the skills you expect to need.

---

## 5. Any other LLM (ChatGPT, Gemini, Mistral, Llama, Cursor, Codex, Copilot…)

Skills are provider-neutral Markdown at public URLs, so **any LLM can use them.**

### A. LLMs with web browsing / a fetch tool (most chat UIs, agent frameworks)
Paste this **bootstrap prompt** once at the start of a chat:

> You have access to the SEBSKILLS library. Its index is at
> `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/manifest.json`.
> When I give you a task: (1) fetch that manifest, (2) pick the best-matching skill by its `keywords`/`description`,
> (3) fetch that skill's file from `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/` + its `path`,
> and (4) follow the skill's instructions. If two skills are close, ask me which. If none fit, say so.

That reproduces `/sebduffy` behaviour on any web-capable model.

### B. LLMs with no web access (offline / air-gapped)
Open `manifest.json`, find the skill you want, and paste its raw file contents into the chat as context. (Each skill's `path` gives the URL, or just browse `skills/<category>/<name>/SKILL.md`.)

### C. Coding harnesses (Cursor, Codex CLI, GitHub Copilot, Gemini CLI)
Run the **`skill-marketplace-packager`** skill to emit native plugin bundles for each harness from the shared `manifest.json`, then install per that harness's plugin mechanism.

---

## 6. How it works (so you can trust it)

```
/sebduffy <intent>
   │  rank the embedded 333-row catalogue (no network needed to ROUTE)
   ▼
pick best skill  ── ambiguous? ask ── too vague? ask 2-3 questions (requirement-elicitation)
   │
   ▼  load the skill body — first rung that's available:
   1. local install     ~/.claude/skills/<name>/SKILL.md      (offline, fastest)
   2. web fetch          raw.githubusercontent.com/.../<path>  (the public CDN)
   3. shell              curl / gh api                         (CLI fallback)
   4. MCP resource       skill://body/<name>                   (Desktop offline)
   5. fail loud          print the URL — never invent a skill
```

No web app is deployed. The **public GitHub repo is the network**; `raw.githubusercontent.com` is the free global CDN.

---

## 7. Add your own skills

- **`/sebduffy skill-adder`** — guided intake that drafts a skill, audits it (`skill-auditor`), and registers it into `manifest.json` + the indexes — nothing lands unaudited.
- Or drop a `skills/<category>/<name>/SKILL.md` (10-field frontmatter — see `CONTRIBUTING.md`) and run:
  ```bash
  python3 scripts/build_manifest.py            # regenerate manifest + router index + REPORT.md
  python3 scripts/build_manifest.py --check    # lint gate (CI-friendly)
  ```
- Push to `main` and it's live for everyone instantly.

---

## 8. Staying up to date

Nothing to do — the router reads live `main`, so new skills appear automatically. For **repeatable installs**, pin a release tag: change `ref` / `main` in the router's raw URLs to a tag (e.g. `v1`).

---

## Quick-reference URLs

| Thing | URL |
|---|---|
| One-line installer | `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/install-sebduffy.sh` |
| Router (the one file) | `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/skills/meta/sebduffy/SKILL.md` |
| Catalogue index | `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/manifest.json` |
| Any skill | `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/skills/<category>/<name>/SKILL.md` |
| Health report | `https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/REPORT.md` |
