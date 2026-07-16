---
name: moltbook
category: building-agents
description: >
  Run N heterogeneous agents (different models/personas) through structured propose->critique->revise
  rounds where EVERY proposed change must clear a two-stage gate before it counts as a "molt": AUDIT
  (does the revision actually beat its parent by margin delta on a REAL external eval/rubric — unit tests,
  a metric, a benchmark?) then VERIFICATION (an independent judge-panel majority/veto vote). Keep-all JSONL
  archive, convergence detection, hard budget caps — only externally-verified improvements survive. Use
  when self-refine or debate loops "improve" text with no ground truth and you need proof.
when_to_use:
  - You have an artifact (prompt, doc, config, code, plan) plus a REAL external eval and want only verified improvements kept
  - A single-model self-refine loop keeps declaring progress you cannot trust or reproduce
  - You want N different models/personas to cross-revise MoA-style but gated, not averaged
  - You need a full audit trail (keep-all archive) of every proposal and why it was accepted/rejected
  - You are hardening an agent-improvement loop against runaway cost, drift, and un-observability
when_not_to_use:
  - No external eval exists and you cannot build one — use plain `self-refine` / brainstorming; this skill refuses to promote without one
  - You just want a better answer once with no loop or gating — call the model directly or use `deep-research`
  - You need multi-agent DEBATE for a single answer (no keep-all archive/gates) — use a debate loop instead
  - You are orchestrating unrelated parallel tasks, not iterative improvement — use `dispatching-parallel-agents`
keywords:
  - multi-agent
  - self-refine
  - mixture-of-agents
  - moa
  - llm-debate
  - verification
  - audit-gate
  - judge-panel
  - convergence
  - archive
  - budget-cap
  - eval-driven
  - propose-critique-revise
  - orchestration
similar_to:
  - dispatching-parallel-agents
  - deep-research
  - claude-api
inputs_needed: A seed artifact; a versioned rubric.md (constitution); a pluggable eval_fn returning a float (unit-test pass rate, metric, benchmark score); Anthropic API key; a config (models per persona, delta, epsilon, patience, budget).
produces: A best verified artifact + score, a keep-all archive.jsonl of every proposal with audit/verify outcomes, and a run summary (rounds, molts accepted, calls used, score history).
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Moltbook: externally-gated multi-agent molting

## When to use

Named after the January 2026 agent-only network Moltbook (~1.5M claimed agents), whose
collapse — a shared DB, no per-agent limits, no observability, and 99% fake activity that
nobody could audit — is exactly what this skill defends against. Use it when you want a loop
of heterogeneous agents to iteratively improve an artifact, but you refuse to accept a change
on the model's own say-so. A revision only becomes a **molt** if it (1) provably beats its
parent on a **real external eval** and (2) survives an **independent verifier vote**. Everything
is archived, budgeted, and stopped on convergence.

This is the gated superset of three real patterns: MoA cross-revision
(togethercomputer/MoA, Apache-2.0), self-refine critique (madaan/self-refine), and a
ChatEval-style judge panel (arXiv 2308.07201). The novel contribution is the **two-stage
gate** — audit before verify — so "the panel liked it" can never override "the benchmark
says it regressed".

## Prerequisites

- Python 3.9+ and `pip install anthropic` (only needed for real runs; the control logic is network-free).
- An `ANTHROPIC_API_KEY` in the environment.
- The single hard requirement: **an external `eval_fn(text) -> float`**. Higher is better. It must
  come from ground truth you did not let the agents write — a unit-test pass rate, a held-out
  metric (BLEU/ROUGE/exact-match), a benchmark harness, a linter/type-checker score, latency, etc.
  **If you have no such eval, stop.** Without it AUDIT is meaningless and the loop degenerates into
  self-flattery — `scripts/molt.py` raises `ValueError` rather than pretend.

## Mechanism / Steps

Everything below is implemented and smoke-tested in `scripts/molt.py`. The four model-facing steps
are dependency-injected so you can unit-test the gates with mocks and swap in Claude for real runs.

**1. Write the rubric (constitution).** A short versioned `rubric.md` the proposers revise toward and
the verifiers judge against. Version it — a rubric change invalidates cross-round score comparisons.

**2. Define the config.** `Config(proposers, verifiers, max_rounds, delta, epsilon, patience, max_calls,
require_unanimous)`. Heterogeneity matters: point each persona/judge at a **different model** where you
can (e.g. Opus for the skeptic, Haiku for the minimalist) so the panel's votes are actually independent.

**3. Seed and score.** `best_score = eval_fn(seed)`. This is parent id 0.

**4. Molt round (repeat until stop):**
   - **Propose (MoA cross-revision):** each persona produces a revision of the current best, and — MoA-style
     — sees the *peer drafts already produced this round* (`siblings`). Different personas = diverse edits.
   - **Critique (self-refine):** each draft gets a terse, rubric-anchored weakness list. This shapes the next
     round's proposals; it does NOT decide acceptance.
   - **AUDIT (hard gate):** `audit_gate(parent_score, child_score, delta)` — the child is promoted only if the
     **external eval** improves by at least `delta`. No eval, no promotion. This is the load-bearing gate.
   - **VERIFICATION (independent panel):** only audit survivors reach the judges (saves budget). Each verifier
     is a *different prompt/model* voting YES/NO on "does child strictly beat parent with no regressions?".
     `verification_gate(votes, require_unanimous)` — any veto rejects (unanimous) or strict majority.
   - **Archive (keep-all):** every proposal — accepted or not, with its scores, audit result, and votes —
     is one JSONL line via `append_archive`. Nothing is silently dropped; the run is fully auditable.
   - The round's best verified child (if any) becomes the new parent; parent id increments.

**5. Stop.** Whichever fires first:
   - **Convergence:** `converged(best_history, epsilon, patience)` — the last `patience` best-score gains are
     each below `epsilon` (an epsilon-plateau with K-patience).
   - **Budget cap:** `calls_used >= max_calls`. A hard ceiling across ALL model calls — the anti-runaway
     control Moltbook lacked. The loop also breaks out mid-round when the cap is hit.

Minimal real wiring:

```python
from scripts.molt import run_molt, Config, claude_adapters

rubric = open("rubric.md").read()
model_map = {"skeptic": "claude-opus-4-6", "minimalist": "claude-3-5-haiku-latest",
             "maximalist": "claude-sonnet-4-6",
             "judge-a": "claude-opus-4-6", "judge-b": "claude-sonnet-4-6",
             "judge-c": "claude-3-5-haiku-latest"}
propose_fn, critique_fn, verify_fn = claude_adapters(model_map)

def eval_fn(text: str) -> float:
    # YOUR external ground truth. e.g. write `text` to prompt.txt, run the test
    # suite, return pass-rate in [0,1]. MUST NOT be judged by the agents.
    ...

out = run_molt(seed_text=open("seed.txt").read(), rubric=rubric,
               propose_fn=propose_fn, critique_fn=critique_fn,
               verify_fn=verify_fn, eval_fn=eval_fn,
               cfg=Config(proposers=("skeptic","maximalist","minimalist"),
                          verifiers=("judge-a","judge-b","judge-c"),
                          max_rounds=12, delta=0.01, epsilon=0.005,
                          patience=3, max_calls=400),
               archive_path="archive.jsonl")
print(out["best_score"], out["molts_accepted"], out["calls_used"])
```

Example `rubric.md`:

```markdown
# Rubric v3 (constitution)
1. Correctness — no factual/logical errors; passes the external suite.
2. Completeness — covers every required point; no TODOs.
3. Concision — no redundancy; every sentence earns its place.
A CHILD beats a PARENT only if it improves >=1 axis with NO regression on any other.
```

## Verify

- `python3 scripts/molt.py` runs the network-free self-test: a toy string-matching eval drives a full
  loop and asserts (a) at least one verified molt is accepted, (b) both gate functions behave (delta
  margin, unanimous veto vs majority), (c) convergence detection fires and doesn't false-positive, and
  (d) the missing-`eval_fn` guard raises. Expected tail: `OK {'best_score': ..., 'molts_accepted': 17, ...}`.
- Inspect `/tmp/molt_selftest.jsonl` — one line per proposal, showing rejected drafts (`audit_pass:false`,
  empty votes) alongside accepted molts. That file IS the audit trail.
- For a real run, confirm `molts_accepted` only ever rises when `score_history` rises, and that
  `calls_used <= max_calls`.

## Pitfalls

- **No eval = no skill.** The single most common failure is a fake `eval_fn` (e.g. asking a model to
  score the output). That re-creates the self-flattery loop. The eval must be ground truth outside the
  agents' control. The code refuses `eval_fn=None`; don't defeat it by proxying a judge as the eval.
- **Homogeneous panel.** Pointing every persona/judge at one model collapses the panel to one voter —
  votes stop being independent. Vary model AND prompt.
- **delta too small.** With `delta=0`, eval noise ratchets the score upward on nothing. Set `delta` above
  your eval's measurement noise floor.
- **Rubric drift.** Editing the rubric mid-run makes cross-round scores incomparable. Bump the version and
  restart, or hold it fixed. Record the rubric version in your run notes.
- **Verifier as tiebreak over audit.** Never let a strong panel vote override a failed AUDIT — audit runs
  first and is hard-required precisely so "the judges liked it" cannot resurrect a regression.
- **Budget starvation.** Judges only run on audit survivors, but a large panel x many proposers still burns
  the cap fast. Size `max_calls` against `max_rounds * len(proposers) * (1 + len(verifiers))`.
- **Archive is append-only.** Rotate/namespace `archive_path` per run so you never conflate two experiments.
