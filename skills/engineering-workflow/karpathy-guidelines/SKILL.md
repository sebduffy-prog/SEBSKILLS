---
name: karpathy-guidelines
category: engineering-workflow
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
when_to_use:
  - Writing, reviewing, or refactoring code and wanting to avoid common LLM coding pitfalls
  - You are about to make assumptions or pick silently between interpretations — surface them instead
  - Guarding against overcomplication and speculative abstractions (simplicity first)
  - Making surgical, scoped edits that touch only what the request requires
  - Turning a vague task into verifiable success criteria you can loop against
when_not_to_use:
  - You need the ACT-vs-ASK decision itself for a task — use autonomy-policy
  - You need full house coding conventions (naming, immutability, smells) — use coding-standards
  - You want test-first discipline as a workflow — use test-driven-development
  - You are enforcing evidence before completion claims — use verification-before-completion
keywords:
  - karpathy
  - llm-coding-mistakes
  - simplicity-first
  - surgical-changes
  - surface-assumptions
  - success-criteria
  - overcomplication
  - scope-discipline
  - goal-driven
  - think-before-coding
  - behavioral-guidelines
similar_to:
  - coding-standards
  - autonomy-policy
  - incremental-implementation
inputs_needed: The coding task or code under review, and any ambiguity or assumptions that should be surfaced before implementing.
produces: Code and behavior that stays minimal, surgical, and scoped, with assumptions surfaced and verifiable success criteria defined up front.
license: MIT
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
