---
name: requesting-code-review
category: engineering-workflow
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
when_to_use:
  - After completing a task in subagent-driven development, before moving to the next
  - After completing a major feature, or before merging to main
  - You want a fresh-context code-reviewer subagent to catch issues before they cascade
  - You are stuck and want an independent perspective, or want a baseline check before refactoring
  - You need a curated review prompt (base/head SHAs, what was built, requirements)
when_not_to_use:
  - You are on the receiving end of review feedback — use receiving-code-review
  - The concern is specifically security-sensitive code — use security-review
  - You just need to run verification commands yourself — use verification-before-completion
  - You want to complete/merge the branch after review passes — use finishing-a-development-branch
keywords:
  - request-review
  - code-reviewer
  - subagent-review
  - pre-merge
  - review-early
  - critical-important-minor
  - base-sha
  - head-sha
  - review-template
  - quality-gate
similar_to:
  - receiving-code-review
  - security-review
  - subagent-driven-development
inputs_needed: The completed work, base and head git SHAs, a brief description of what was implemented, and the plan/requirements it should satisfy.
produces: A dispatched code-reviewer subagent review (strengths + Critical/Important/Minor issues + assessment) to act on before proceeding.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Requesting Code Review

Dispatch superpowers:code-reviewer subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation — never your session's history. This keeps the reviewer focused on the work product, not your thought process, and preserves your own context for continued work.

**Prerequisite:** The `superpowers:code-reviewer` subagent type requires the superpowers plugin. If it's not installed, dispatch a general-purpose subagent instead, giving it the same review prompt and criteria (fill the `code-reviewer.md` template as usual).

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Dispatch code-reviewer subagent:**

Use Task tool with superpowers:code-reviewer type, fill template at `code-reviewer.md`

**Placeholders:**
- `{WHAT_WAS_IMPLEMENTED}` - What you just built
- `{PLAN_OR_REQUIREMENTS}` - What it should do
- `{BASE_SHA}` - Starting commit
- `{HEAD_SHA}` - Ending commit
- `{DESCRIPTION}` - Brief summary

**3. Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Dispatch superpowers:code-reviewer subagent]
  WHAT_WAS_IMPLEMENTED: Verification and repair functions for conversation index
  PLAN_OR_REQUIREMENTS: Task 2 from docs/superpowers/plans/deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types

[Subagent returns]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: [Fix progress indicators]
[Continue to Task 3]
```

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each batch (3 tasks)
- Get feedback, apply, continue

**Ad-Hoc Development:**
- Review before merge
- Review when stuck

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See template at: requesting-code-review/code-reviewer.md
