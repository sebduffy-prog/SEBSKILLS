# Engineering Workflow

**How Claude should think, plan, debug, review, and ship.**

These are the "discipline" skills — they don't produce artifacts, they shape *how* work happens. Load them early in any session and Claude will plan before coding, test before claiming done, and keep changes surgical.

## Recommended session flow

```
           ┌─ brainstorming ──┐
start ────►│                  ├──► writing-plans ──► executing-plans ─┐
           └─ karpathy-guid. ─┘                                       │
                                                                      ▼
                                              ┌── test-driven-development
                                              │           │
                                              │           ▼
                                              │   systematic-debugging (if stuck)
                                              │           │
                                              │           ▼
                                              └── verification-before-completion
                                                          │
                                                          ▼
                                              requesting-code-review
                                                          │
                                                          ▼
                                              finishing-a-development-branch
```

## Index

| Skill | Trigger |
|---|---|
| [`karpathy-guidelines`](karpathy-guidelines) | Always — the four principles (think, simplify, surgical, goal-driven) |
| [`brainstorming`](brainstorming) | Before creative work — intent + requirements first |
| [`writing-plans`](writing-plans) | Multi-step task — draft the plan before code |
| [`executing-plans`](executing-plans) | Execute a written plan with review checkpoints |
| [`test-driven-development`](test-driven-development) | Any feature or fix — tests first |
| [`systematic-debugging`](systematic-debugging) | Any bug or unexpected behavior |
| [`verification-before-completion`](verification-before-completion) | Before any "done" claim — evidence required |
| [`requesting-code-review`](requesting-code-review) | Before merging or finishing major work |
| [`receiving-code-review`](receiving-code-review) | When reading review feedback |
| [`finishing-a-development-branch`](finishing-a-development-branch) | Work complete — merge / PR / cleanup |
| [`using-git-worktrees`](using-git-worktrees) | Feature work that needs isolation |
| [`dispatching-parallel-agents`](dispatching-parallel-agents) | 2+ independent tasks, no shared state |
| [`subagent-driven-development`](subagent-driven-development) | Plan with independent tasks, in-session |
| [`using-superpowers`](using-superpowers) | Meta — how to find and use any skill |

## Pair them

- **Karpathy + TDD + Verification**: hardest anti-hallucination combo. Claude plans, writes a test, makes it pass, proves it passes.
- **Worktrees + Parallel Agents**: long tasks on many fronts, each isolated.
- **Systematic Debugging + TDD**: reproduce the bug as a test, then fix.

## Attribution

- [`obra/superpowers`](https://github.com/obra/superpowers) — 13 of these skills (MIT)
- [`forrestchang/andrej-karpathy-skills`](https://github.com/forrestchang/andrej-karpathy-skills) — `karpathy-guidelines` (MIT)
