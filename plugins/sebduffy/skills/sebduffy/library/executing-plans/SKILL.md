---
name: executing-plans
category: engineering-workflow
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
when_to_use:
  - You have a written implementation plan file and need to execute its tasks in order
  - You want to review the plan critically first, then work task-by-task with verifications
  - You are running inline (batch) execution with checkpoints rather than a fresh subagent per task
  - The platform lacks subagent support, so you execute the plan directly in this session
  - You need a disciplined stop-and-ask flow when hitting blockers or unclear instructions
when_not_to_use:
  - Subagents are available and you want a fresh subagent per task with two-stage review — use subagent-driven-development
  - You have no written plan yet — create one with writing-plans (after brainstorming)
  - The work is complete and you need to merge/PR/clean up — use finishing-a-development-branch
  - You need an isolated workspace before starting — use using-git-worktrees
keywords:
  - executing-plans
  - implementation-plan
  - task-execution
  - review-checkpoints
  - todowrite
  - inline-execution
  - batch-execution
  - blockers
  - verification
  - plan-review
  - superpowers
similar_to:
  - subagent-driven-development
  - writing-plans
  - finishing-a-development-branch
inputs_needed: A written plan file to execute, an isolated worktree/branch, and the project's verification commands.
produces: The plan's tasks implemented and verified in order, with a handoff to finishing-a-development-branch when complete.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Note:** Tell your human partner that Superpowers works much better with access to subagents. The quality of its work will be significantly higher if run on a platform with subagent support (such as Claude Code or Codex). If subagents are available, use superpowers:subagent-driven-development instead of this skill.

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with your human partner before starting
4. If no concerns: Create TodoWrite and proceed

### Step 2: Execute Tasks

For each task:
1. Mark as in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Mark as completed

### Step 3: Complete Development

After all tasks complete and verified:
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
- Follow that skill to verify tests, present options, execute choice

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Stop when blocked, don't guess
- Never start implementation on main/master branch without explicit user consent

## Integration

**Required workflow skills:**
- **superpowers:using-git-worktrees** - REQUIRED: Set up isolated workspace before starting
- **superpowers:writing-plans** - Creates the plan this skill executes
- **superpowers:finishing-a-development-branch** - Complete development after all tasks
