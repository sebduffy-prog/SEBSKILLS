---
name: auto-dream-loop
category: building-agents
description: >
  Give an agent an idle-time "sleep and dream" self-improvement loop that only
  ships measured wins. On a cron or idle trigger it REPLAYS its own recent
  transcripts, buckets success vs fail, DISTILS reusable strategies into an
  append-only reasoning bank, PROPOSES prompt/skill edits on a shadow copy, then
  GATES every change behind a frozen held-out eval — accepting only what beats
  baseline. Use when someone asks for a self-improving / continual-learning /
  "agent that learns overnight" loop, Letta sleep-time compute, SEAL-style
  self-edits, ReasoningBank memory, or a Reflexion loop with anti-overfit guards.
when_to_use:
  - "You want an agent to improve its own prompt/skills over time without a fine-tune, from its own run history"
  - "User references Letta sleep-time compute, SEAL self-edits, STOP, Reflexion, ReasoningBank, or 'agent that dreams / learns overnight'"
  - "You have accumulating transcripts and want distilled, reusable lessons instead of a growing raw log"
  - "You need every self-modification audited and reversible, with a hard guardrail against reward hacking / overfitting"
  - "You are wiring a nightly/idle cron job that should safely edit an agent's own instructions"
when_not_to_use:
  - "You want to fine-tune weights on collected data — this loop edits prompts/skills only; use an SFT/RL pipeline instead"
  - "You just need durable memory/RAG recall across sessions, not behavior change — use a memory/RAG skill (e.g. rag/*)"
  - "One-off prompt tuning by hand — use skill-creator or edit the prompt directly; a gated loop is overkill"
  - "Red-teaming a skill to find failure cases — use adversarial-skill-forge; feed its cases here as frozen-eval tasks"
keywords: [self-improvement, sleep-time compute, dreaming, continual learning, reasoning bank, seal, stop, reflexion, frozen eval, held-out, overfit guard, prompt evolution, self-edit, idle-time, cron, letta, audit log, gate]
similar_to: [adversarial-skill-forge, moltbook]
inputs_needed:
  - "A directory of the agent's recent transcripts (JSON, each with a pass/fail verdict)"
  - "A FROZEN held-out eval set (tasks + rubrics) that the loop must never edit"
  - "The mutable target: the prompt/skill files this agent is allowed to rewrite"
  - "A trigger: cron schedule or idle hook, plus an accept margin"
produces: A gated self-improvement cycle — append-only reasoning_bank.jsonl of distilled strategies, promoted prompt/skill edits (only measured wins), and an auditable dreams/CHANGELOG.md of every proposal + eval delta + verdict
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Auto Dream Loop

An idle-time loop that lets an agent improve *itself* from its own run history —
and refuses to keep any change that isn't a measured win. Ports the core idea of
Letta **sleep-time compute** ("agent dreaming"), MIT **SEAL** self-edits, **STOP**
(self-taught optimizer), **Reflexion** verbal reinforcement, and Google's
**ReasoningBank** (distil strategies from *both* success and failure), fused with
one non-negotiable guardrail: a **frozen eval** the loop can never touch.

## When to use

Reach for this when an agent has started accumulating transcripts and you want it
to get *better on its own* between sessions — sharper prompts, new skills, fewer
repeat mistakes — without a fine-tune and without trusting the model's own
optimism. The whole design exists to answer one question honestly: *did that
self-edit actually help, on tasks it couldn't have overfit to?*

## Prerequisites

- `python3` (3.9 ok) and the `claude` CLI on PATH (headless `claude -p`); swap
  `_claude()` in the script for any provider.
- Transcripts written as JSON, one per run, each carrying a boolean `passed`
  verdict and enough trace to learn from (task, steps, tool calls, error).
- A **frozen eval set**: `evals/frozen_set.jsonl`, held-out tasks the agent's
  live traffic does *not* draw from. This is the anti-overfit spine — see Pitfalls.

## State (append-only + one mutable target)

```
.dream/
  transcripts/            # recent runs, *.json  (READ)
  memory/
    reasoning_bank.jsonl  # distilled strategies — APPEND-ONLY, wins only
  evals/
    frozen_set.jsonl      # held-out tasks — NEVER written by the loop
  target/                 # the mutable prompt/skill files (the only thing edited)
  dreams/
    CHANGELOG.md          # every proposal + eval delta + ACCEPT/REJECT verdict
```

The single mutable surface is `target/`. `frozen_set.jsonl` is sacred: if the loop
can edit the test, it will learn to cheat it. `reasoning_bank.jsonl` only ever
grows, and only with strategies from an accepted cycle.

## Mechanism / Steps

`scripts/dream_loop.py` runs one full cycle. It is deterministic where it matters
(bucketing, gating, promote, audit) and shells out to the model for the four
generative steps.

1. **Scaffold once.** `python3 scripts/dream_loop.py .dream --init` creates the
   tree above and a placeholder frozen task. Replace the frozen set with real
   held-out tasks and point `target/` at your live prompt/skill files.

2. **REPLAY.** Read the last `--replay-n` transcripts (default 20), skip any that
   fail to parse (never trust file content), and bucket into success / fail.

3. **DISTIL.** Feed both buckets to the model and get back a JSON array of
   strategy items `{title, when, do, evidence}` — *learning from failures too*,
   which is exactly what lifts ReasoningBank over success-only memory.

4. **PROPOSE.** Copy `target/` to a throwaway **shadow** dir and let the model
   edit the shadow to encode the strategies — the smallest change that could raise
   the score. The live `target/` is untouched at this stage.

5. **FROZEN EVAL (baseline vs candidate).** Score the live `target/` and the
   shadow against `frozen_set.jsonl`: run each held-out task, grade PASS/FAIL by
   rubric, take the pass rate. Same tasks, same grader, both sides.

6. **GATE.** Accept **iff** `candidate > baseline + margin`. On accept: append the
   strategies to `reasoning_bank.jsonl` (with score + ts) and **atomically
   promote** the shadow into `target/` (`os.replace`). On reject: change nothing.
   Either way, append the verdict, both scores, and the delta to `CHANGELOG.md`.

Run one gated cycle:

```bash
python3 scripts/dream_loop.py .dream --margin 0.02
# -> ACCEPTED | REJECTED   (see .dream/dreams/CHANGELOG.md for the audit line)
```

Schedule it for genuine idle time (this repo's `schedule` skill or plain cron):

```bash
# 3am nightly "dream"
0 3 * * *  cd /path/to/agent && python3 scripts/dream_loop.py .dream --margin 0.02 >> .dream/dreams/cron.log 2>&1
```

Keep the target under version control so every promote is a commit you can revert;
the CHANGELOG line and the git diff together are the full audit trail.

## Verify

- **Dry-run both verdicts** (no model, no `claude` needed):
  ```bash
  python3 scripts/dream_loop.py .dream --init
  python3 scripts/dream_loop.py .dream --dry-run          # cand 0.6 > base 0.5 -> ACCEPTED
  ```
  Confirm `CHANGELOG.md` gained an ACCEPT line and `reasoning_bank.jsonl` gained a
  row. The reject path (baseline 0.8 > candidate 0.5) must leave the bank unchanged
  — the script's `gate()` only writes on a win.
- **Guardrail check:** diff `frozen_set.jsonl` before/after a real cycle — it must
  be byte-identical. If it ever changes, the loop is contaminated; stop and rebuild
  the held-out set.
- **Ratchet check:** over many cycles, `CHANGELOG.md` baseline scores should be
  monotonically non-decreasing. A baseline that drops means something promoted
  outside the gate (manual edit, non-atomic write) — investigate.

## Pitfalls

- **Overfitting to the eval = reward hacking.** The frozen set only protects you if
  it is truly held out from live traffic and never edited by the loop. Rotate in
  fresh held-out tasks periodically (from real misses, or from
  `adversarial-skill-forge`), and keep a second *secret* eval you run manually to
  confirm gains generalize.
- **Distillation drift / bank bloat.** An ever-growing bank of near-duplicate
  strategies dilutes signal. Periodically dedupe/merge `reasoning_bank.jsonl` (by
  `title`/embedding) — but do it as an offline maintenance pass, never inside the
  gated cycle.
- **Margin too tight.** With a small frozen set, a one-task swing is noise. Set
  `--margin` above the eval's noise floor (a few points), or require the win to
  hold across two runs before promoting.
- **Non-atomic promote corrupts the agent.** Always stage in the shadow and swap
  with `os.replace`; a half-written `target/` bricks the live agent. The script
  does this — don't hand-edit `target/` mid-cycle.
- **Learning from failure needs failure signal.** If every transcript is marked
  `passed: true`, distillation has nothing to correct. Make sure your verdict
  labels are honest, or the loop only reinforces what already worked.
- **Silent generative-step failures.** `distil`/`propose` returning junk yields a
  no-op candidate that simply fails the gate — safe, but check `CHANGELOG.md` for a
  run of REJECTs with flat scores, which usually means the model step is broken,
  not that there's nothing to learn.
