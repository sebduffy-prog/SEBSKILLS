# Building Agents

**Claude API apps, MCP servers, and new skills.**

These skills are for when you are *building the things that Claude uses* — either another agent, a tool Claude calls, or a reusable skill for Claude itself.

## Index

| Skill | Use when |
|---|---|
| [`claude-api`](claude-api) | Writing or tuning Anthropic SDK code. Covers prompt caching, extended thinking, tool use, batch API, files, citations, memory, model migrations (4.5 → 4.6 → 4.7). **Triggers automatically** when a file imports `anthropic` / `@anthropic-ai/sdk`. |
| [`mcp-builder`](mcp-builder) | Building a Model Context Protocol server — Python (FastMCP) or Node/TypeScript (MCP SDK). Covers tool design, auth, schema, error handling. |
| [`skill-creator`](skill-creator) | Creating a new skill from scratch, editing existing skills, running evals against them, optimizing descriptions for trigger accuracy. |
| [`writing-skills`](writing-skills) | Authoring and verifying skills — the craft side: what to put in `SKILL.md`, how to design triggers, testing with subagents. Pairs with `skill-creator`. |

## Workflows

**"I want to wrap an external API as a Claude tool"**
→ `mcp-builder` (it guides API surface design, auth, FastMCP/SDK boilerplate)

**"I keep repeating this prompt pattern across sessions"**
→ `skill-creator` + `writing-skills` — turn it into a durable skill

**"My Anthropic SDK call is slow / expensive"**
→ `claude-api` — prompt caching, batch API, model selection

**"Migrate my app from Claude 4.5 to 4.7"**
→ `claude-api` (migration path is built into the skill)

## Attribution

All four skills originate from [`anthropics/skills`](https://github.com/anthropics/skills) or [`obra/superpowers`](https://github.com/obra/superpowers).
