# Contributing to SEBSKILLS

Thanks for adding to the framework. A few ground rules so the library stays useful.

## Anatomy of a skill

Every skill is a directory containing at least:

```
skills/<category>/<your-skill>/
├── SKILL.md                # required — frontmatter + instructions
├── assets/                 # optional — images, .tsx files, templates
├── examples/               # optional — usage examples
└── scripts/                # optional — helper scripts
```

`SKILL.md` frontmatter:

```markdown
---
name: kebab-case-name
description: One paragraph. What the skill does, when to trigger it, example phrasings users might say. The description is what Claude reads to decide whether to load the full skill — write it for triggering, not for humans.
---

# Title

## When to use
## What to produce
## Implementation notes
```

## Writing a good description

The `description` field is the trigger surface. Good descriptions:

- **Lead with the action** — *"Build a React component that…"*, *"Create a PDF with…"*
- **List trigger phrases users actually say** — *"shatter effect"*, *"back button that looks glassy"*
- **Mention adjacent/fuzzy cases** — *"trigger even if the user just says 'make the hero pop'"*
- **Explicitly state skip conditions** when they matter — *"SKIP: file imports `openai`"*

See [`skills/building-agents/writing-skills`](skills/building-agents/writing-skills) for deep guidance.

## Before opening a PR

1. Confirm the `SKILL.md` frontmatter parses — no missing fields
2. Add a row to the category's `README.md`
3. Add a row to the root [`README.md`](README.md) quick index
4. Preserve original license if the skill is derived from another source
5. Test it once in a live Claude Code session — does it actually trigger when you expect?

## Categorization rule of thumb

| If the skill… | Goes in |
|---|---|
| shapes how Claude works (plans, debugs, reviews) | `engineering-workflow/` |
| builds tools Claude uses (API, MCP, other skills) | `building-agents/` |
| produces web UI, pages, artifacts, themes, design | `frontend-and-design/` |
| is a drop-in visual effect component | `ui-effects/` |
| produces a .docx/.pdf/.pptx/.xlsx/comms | `documents/` |
| is media-specific tooling | `media/` |

If it fits two categories, pick the primary use case. Don't duplicate.

## Licensing

The repo scaffolding (READMEs, organization) is MIT. Each skill carries the license of its upstream source — preserve any `LICENSE.txt` inside the skill directory.
