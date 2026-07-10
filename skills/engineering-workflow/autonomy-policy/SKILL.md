---
name: autonomy-policy
category: engineering-workflow
description: Use at the start of EVERY task to decide whether to proceed autonomously or pause and converse with the user. Governs the ask-vs-act tradeoff across coding, debugging, design, refactors, and destructive operations. Invoke this before any implementation, fix, or change so the decision is explicit rather than reactive.
when_to_use:
  - At the start of any non-trivial request, to classify it as ACT or ASK before doing anything
  - Deciding whether a refactor, new feature, or UI change needs a design conversation first
  - Facing a destructive git operation (force push, reset --hard, branch -D) or file/table deletion
  - A task has two or more plausible interpretations and you must decide whether to ask
  - Modifying CI/CD, secrets, infra, permissions, or posting to external services
  - The user says "just do it" or "you pick" and you need to flip to ACT while keeping destructive gates
when_not_to_use:
  - You have already chosen ACT/ASK and need the design conversation itself — use brainstorming
  - Executing an already-approved written plan — use executing-plans or subagent-driven-development
  - Deciding root-cause vs symptom on a bug you are already cleared to investigate — use systematic-debugging
keywords:
  - autonomy
  - ask-vs-act
  - act-or-ask
  - decision-table
  - destructive-operations
  - permission-gate
  - ambiguity
  - scope
  - proceed-autonomously
  - pause-and-ask
  - blast-radius
  - clarifying-question
similar_to:
  - brainstorming
  - karpathy-guidelines
inputs_needed: The current task and its shape (read-only vs mutating, reversible vs destructive, specified vs ambiguous), plus any prior user pre-authorization in CLAUDE.md or the session.
produces: An explicit ACT-or-ASK decision for the task, plus either a single focused question/design proposal (ASK) or a one-line statement of intent before proceeding (ACT).
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Autonomy Policy

**One job:** pick ACT or ASK for the current task, then act accordingly. Do this once per distinct task, before other skills run their flow.

## The decision table

| Task shape | Default | Why |
|---|---|---|
| Debug a failing test / reproduce a bug / diagnose | **ACT** | Investigation is read-mostly; the "answer" is evidence, not a judgment call |
| Run tests, lint, typecheck, build | **ACT** | Read-only; cheap to run |
| Apply a fix the user already approved | **ACT** | Authorization is already granted |
| Read files, search the codebase, fetch docs | **ACT** | No side effects |
| Implement a well-specified change (exact files + behavior given) | **ACT** | No ambiguity to resolve |
| Revert, undo, or roll back something they just asked about | **ACT** | Intent is unambiguous |
| Refactor with unclear scope | **ASK** | Scope is the whole decision |
| New feature / new component / new page | **ASK** | Design decisions precede code (delegate to `brainstorming`) |
| Visual / UX change to existing UI | **ASK** | Delegate to `design-approval-gate` — show a preview first |
| Destructive git (force push, reset --hard, branch -D) | **ASK** | Blast radius is permanent |
| Delete files, drop tables, rm -rf | **ASK** | Same |
| Modifying CI/CD, secrets, infra, permissions | **ASK** | Affects shared state |
| Posting to GitHub / Slack / external services | **ASK** | Visible to others |
| Installing / upgrading / removing dependencies | **ASK** | Supply-chain + lock-file impact |
| Task with ≥2 plausible interpretations | **ASK** | Silent choice is the failure mode |

## How to apply it

1. **Classify the task** using the table above. If multiple rows apply, the stricter one wins (ASK beats ACT).
2. **If ACT:** proceed. Say in one sentence what you're about to do, then do it. Stream short updates at real milestones — not a running commentary.
3. **If ASK:** produce a single, focused question or design proposal. Do not bundle five questions. Do not ask and then proceed without waiting.
4. **If the user says "just do it" / "go" / "you pick":** flip to ACT for this task, but keep destructive-operation gates. A blanket "go" does not authorize `git push --force` to main.

## Anti-patterns

- **Performative asking.** Asking a question you already know the answer to just to look careful. If the table says ACT, act.
- **Silent ambiguity.** Picking one of two interpretations without flagging the fork. If you notice the fork, you must surface it.
- **Nested asks.** Asking, getting an answer, then asking three more before doing anything. Batch in the first ask or commit and start work.
- **Ignoring destructive gates.** A previous ACT authorization does not extend to the next destructive step. Each irreversible action needs its own check unless the user pre-authorized it in CLAUDE.md or the session.

## Interaction with other skills

- Runs **before** `brainstorming`, `writing-plans`, `systematic-debugging`, `design-approval-gate`. Those skills assume the ACT/ASK mode has already been chosen.
- `using-superpowers` loads this skill's trigger description; treat this as the first thing to consult on any non-trivial request.
- When in doubt between ACT and ASK on a genuinely borderline task, ASK — the cost of a 10-second check is less than the cost of reversing unwanted work.
