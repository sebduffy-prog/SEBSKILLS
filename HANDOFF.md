# SEBSKILLS — Handover / Ownership Guide

**What this is:** a library of 436 Claude skills reachable through one router skill, `/sebduffy`.
It is **just Markdown files in a GitHub repo** served over GitHub's free raw CDN. There is
**no server, no database, and nothing to deploy or pay for.** Upkeep is essentially zero.

**What depends on the owner's account:** every install path (the router, the plugin marketplace,
and the raw URLs baked into some skill bodies) points at the GitHub repo. So the only thing that
can break the library is the **repo disappearing or moving without repointing**. Handover = move
the repo to an account that will outlast any one person, then repoint.

---

## Handover in 3 steps

1. **Fork / transfer** this repo to the new home (a VCCP org account is ideal, or a colleague's
   account). Clone it locally.
2. **Repoint everything to the new account** (one command):
   ```bash
   ./scripts/repoint.sh <new-owner> [new-repo]     # e.g. ./scripts/repoint.sh vccp-media
   ```
   This rewrites all references (install scripts, docs, router, and raw URLs inside skill bodies),
   regenerates the manifest/catalogue/router/mirrors, and runs the validation gate.
3. **Commit & push:**
   ```bash
   git add -A && git commit -m "chore: repoint to <new-owner>" && git push
   ```
   Done. From now on nothing references the old account.

---

## How anyone gets the library (per environment)

Each Claude surface has its own skill store — there is **no single upload that lights up all of
them**, but onboarding within each is one action. Full detail in **[SETUP.md](SETUP.md)**; summary:

| Environment | One-time action | Invoked as |
|---|---|---|
| Claude Code CLI / desktop | `curl -fsSL <raw>/install-sebduffy.sh \| bash` | `/sebduffy` |
| Claude Code **web** (per repo) | commit `.claude/skills/sebduffy/SKILL.md` into the repo they open | `/sebduffy` |
| Claude Code **web** (per user, all repos) | `/plugin marketplace add <owner>/<repo>` → `/plugin install sebduffy@sebskills` | `/sebduffy:sebduffy` |
| Whole team | commit the `.claude/settings.json` marketplace+enabledPlugins snippet (SETUP §3C) | auto on trust |
| Claude API / SDK | paste the router into the system prompt + give a fetch tool | your call |

**In every case the framework needs Claude to be able to fetch from the internet** (the router
pulls skill bodies on demand). If a locked-down environment blocks that, commit the full library
into the repo instead (SETUP §3, "whole library" option) so no fetching is needed.

---

## Maintaining it (rarely needed)

- **Add or edit a skill:** create/edit `skills/<category>/<name>/SKILL.md` (copy an existing one as
  a template — 10-field frontmatter), then run `python3 scripts/build_manifest.py`. That regenerates
  `manifest.json`, `CATALOG.md`, `REPORT.md`, the `/sebduffy` catalogue, and the `.claude/skills` +
  plugin mirrors. Commit and push. New skills appear to everyone automatically.
- **Safety gate (run in CI or before pushing):** `python3 scripts/build_manifest.py --check` — fails
  if any skill's frontmatter is malformed or if the generated files/mirrors have drifted.
- **No server, no secrets, no scheduled jobs.** If nobody touches it, it keeps working.
