---
name: adversarial-skill-forge
category: building-agents
description: >
  Harden a Claude skill through generator-vs-adversary self-play over skill-creator's eval
  harness. An AUTHOR writes the SKILL.md; a BREAKER writes mis-trigger attacks (false-positive
  near-misses AND false-negative misses, plus body-failure probes); a JUDGE scores each; the loop
  escalates via Promptbreeder hypermutation + an ADAS novelty bonus until the Breaker stalls.
  Survivors ship as a Rainbow-Teaming quality-diversity archive (DGM keep-all) — the skill's
  permanent regression gauntlet. Reach for it on "harden this skill", "stop my skill mis-firing",
  "red-team a skill description".
when_to_use:
  - "A skill triggers when it shouldn't (steals queries from siblings) or fails to trigger on legit phrasings, and hand-tuning the description isn't converging"
  - "You want a durable regression eval set for a skill, not a one-shot pass — self-play produces the gauntlet as a by-product"
  - "A high-traffic or safety-adjacent skill needs proof it survives adversarial phrasing before you ship it to a shared library"
  - "You are hardening a family of near-neighbour skills where trigger boundaries collide and need to be pinned down"
  - "You want the skill's BODY stress-tested too — tasks it claims to handle but whose steps quietly break on edge inputs"
when_not_to_use:
  - "You are authoring a skill from scratch with no candidate yet → skill-creator first, then bring the draft here"
  - "You just need to nudge a description's trigger rate once → skill-creator's run_loop.py improve-loop is lighter"
  - "You want cooperative multi-skill orchestration, not adversarial hardening → moltbook"
  - "You want open-ended capability discovery rather than defending a fixed spec → auto-dream-loop"
  - "The skill has no eval-able surface (pure reference doc with no trigger contract) → nothing to break; skip"
keywords: [adversarial, red team, self-play, skill hardening, promptbreeder, hypermutation, adas, novelty, rainbow teaming, map-elites, quality-diversity, dgm, keep-all archive, regression gauntlet, false positive, false negative, mis-trigger, eval set, generator-adversary, skill-creator]
similar_to: [skill-creator, moltbook, auto-dream-loop, autosuggestive-schema-builder]
inputs_needed:
  - "A candidate SKILL.md (or at minimum a description + when_to_use/when_not_to_use) to defend"
  - "The sibling skills whose trigger surfaces collide with it (for false-positive attacks) — names + one-line descriptions"
  - "skill-creator's scripts/ on the path (run_eval.py, run_loop.py, agents/grader.md) and `claude` CLI available for -p subagent runs"
  - "A round cap + a Breaker-success stop threshold (e.g. stop when <10% of attacks break it for 2 rounds)"
produces: A hardened SKILL.md plus a keep-all QD archive exported as a run_eval-compatible regression gauntlet (gauntlet.json)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Adversarial skill forge

Skill descriptions are a **trigger contract**: fire on the right query, stay silent on the
near-miss. You cannot eyeball that contract into robustness — the failure modes live in the
phrasings you didn't think of. So generate them. This is inference-time self-play: an AUTHOR
defends a spec, a BREAKER attacks it, a JUDGE scores, and the loop runs until the adversary
stalls. The attacks that survived ship *with* the skill as its regression gauntlet.

Grounded in four papers, each supplying one mechanism:
- **Rainbow Teaming** (Samvelyan et al, [2402.16822](https://arxiv.org/abs/2402.16822)) — a MAP-Elites
  quality-diversity archive of adversarial prompts keyed by a 2-D descriptor. Here: `attack_type x trigger_surface`.
- **Promptbreeder** (Fernando et al, [2309.16797](https://arxiv.org/abs/2309.16797)) — self-referential
  prompt evolution; the Breaker mutates its own attack-writing prompt, and periodically **hypermutates** (mutates the mutation-prompt).
- **ADAS** ([ShengranHu/ADAS](https://github.com/ShengranHu/ADAS)) — an archive of discovered agents with a **novelty bonus** so search escalates into unexplored cells.
- **DGM** ([jennyzzt/dgm](https://github.com/jennyzzt/dgm)) — **keep-all** lineage: the archive only grows, so no past attack can silently regress.

No training, no fine-tuning. Three `claude -p` subagent runs plus one bookkeeping script.

## When to use

See frontmatter. In short: a candidate skill exists and its trigger/behaviour contract must
survive adversarial phrasing before it ships — and you want the proof to be a reusable eval set.

## Prerequisites

- The `skill-creator` skill installed (this forge is a wrapper over its harness). You need
  `scripts/run_eval.py` (deterministic trigger scoring: does Claude read the skill for a query?),
  `scripts/run_loop.py` (eval+improve description loop), and `agents/grader.md` (body-quality scoring).
- `claude` CLI on PATH for `-p` subagent runs; `python3` (3.9+) for `scripts/forge_archive.py`.
- The candidate SKILL.md and its colliding siblings' descriptions.

## Mechanism / Steps

### 0. Descriptor space (the QD grid)

Every attack lands in one cell of a 5x5 grid. `forge_archive.py` enforces these axes:

```
attack_type      = false-positive-trigger | false-negative-trigger
                   | body-step-failure | scope-boundary | ambiguity
trigger_surface  = description-verb | sibling-keyword-overlap
                   | when-not-to-use-boundary | domain-noun | task-phrasing
```

Rainbow Teaming keeps **one elite per cell** (the most damaging survivor). DGM keep-all keeps
**every** attack ever scored in a flat `lineage` — that lineage is the exported gauntlet.

### 1. Roles (three subagent runs)

Run each as `claude -p` (or Task) with a scoped prompt. Persist their JSON to the run dir.

- **AUTHOR** — input: candidate SKILL.md + current archive elites. Output: a revised SKILL.md
  whose description/when_not_to_use/keywords defeat every archived attack *without* losing true
  triggers. Delegate the actual editing to `skill-creator`.
- **BREAKER** — input: the SKILL.md + sibling descriptions + its current *mutation-prompt*.
  Output: K attacks as JSON, each `{id, attack_type, trigger_surface, query, rationale,
  expectations?}`. Two families: **trigger attacks** (a `query` that should/shouldn't fire) and
  **body attacks** (`body-step-failure`: a task the skill claims but whose steps break, with
  `expectations` for the grader). Push variety across cells — that is what the novelty bonus rewards.
- **JUDGE** — scores each attack, producing `broke` (bool) + `severity` (1-5):
  - trigger attacks → run through **`run_eval.py`**. A false-positive `broke` iff the skill
    triggered (`should_trigger:false` but it fired); a false-negative `broke` iff it did NOT.
  - body attacks → run the task, then score with the **grader agent** against `expectations`;
    `broke` iff any expectation fails.

### 2. One round (`forge_round`)

```bash
RUN=./forge-run; mkdir -p "$RUN"
# 0. init archive once
python3 scripts/forge_archive.py init > "$RUN/archive.json"

# --- per round R ---
# a. BREAKER writes K attacks (uses its evolving mutation-prompt)
claude -p --output-format json < prompts/breaker.md  > "$RUN/attacks.$R.json"
# b. JUDGE scores them (calls run_eval.py + grader). Emits broke/severity per attack.
claude -p --output-format json < prompts/judge.md    > "$RUN/scored.$R.json"
# c. archive insert (QD replace + keep-all lineage) + compute breaker success
python3 scripts/forge_archive.py insert "$RUN/archive.json" "$RUN/scored.$R.json" > "$RUN/archive.next.json"
RATE=$(python3 scripts/forge_archive.py rate "$RUN/archive.json" "$RUN/scored.$R.json")
mv "$RUN/archive.next.json" "$RUN/archive.json"
# d. AUTHOR revises SKILL.md to defeat the WHOLE archive (not just this round)
python3 scripts/forge_archive.py evalset "$RUN/archive.json" > "$RUN/gauntlet.json"
claude -p < prompts/author.md  # edits SKILL.md in place, given gauntlet.json
# e. REGRESSION GATE: re-run the full gauntlet against the revised skill.
#    run_eval does `from scripts...`, so invoke it as a module with skill-creator on
#    PYTHONPATH; --skill-path takes the candidate skill's DIRECTORY (the one holding SKILL.md).
PYTHONPATH=skill-creator python3 -m scripts.run_eval --skill-path . --eval-set "$RUN/gauntlet.json"
```

The regression gate (step e) is the DGM guarantee: a fix that re-breaks an old cell fails the
gate and is rejected. The AUTHOR must satisfy the *cumulative* archive, never just the newest attack.

### 3. Hypermutation + novelty (why it escalates)

- **Promptbreeder:** keep a small pool (3-5) of Breaker mutation-prompts ("attack the verb in the
  description", "borrow a sibling's keywords", "phrase the true task in domain slang"). Each round,
  mutate the best-performing prompt; every N rounds **hypermutate** — ask the Breaker to rewrite one
  mutation-prompt itself. This stops the adversary from looping on one trick.
- **ADAS novelty:** `forge_archive.py` gives a breaking attack a fitness bonus (`NOVELTY_WEIGHT`)
  when its cell is still empty, so the Breaker is rewarded for reaching untouched
  `attack_type x trigger_surface` corners rather than re-farming a solved cell.

### 4. Stop + ship

Stop when the Breaker's success `RATE` stays **below threshold** (e.g. <0.10) for N consecutive
rounds, or a round cap hits. Ship two artifacts: the hardened `SKILL.md` and `gauntlet.json` (the
keep-all lineage in run_eval format). Wire `gauntlet.json` as the skill's committed eval set so CI
re-runs it on every future edit — the adversary's work becomes a permanent gate.

## Verify

- `python3 scripts/forge_archive.py init` prints an empty `{cells, lineage, rounds}`; `insert`
  then `evalset` round-trips attacks into `{query, should_trigger}` rows (false-positive → `false`).
- Fitter attack in a filled cell replaces the incumbent; a `broke:false` attack never creates a
  cell but still lands in `lineage` as a regression case (both covered by the script's smoke test).
- After a real run: `run_eval --skill-path . --eval-set gauntlet.json` on the final SKILL.md passes every row
  (0 false triggers, 0 missed triggers) — that IS the acceptance criterion.
- Sanity-check coverage: `jq '.cells|keys' archive.json` should span most of the 25 cells; large
  empty regions mean the Breaker under-explored (raise novelty weight or hypermutate sooner).

## Pitfalls

- **Overfitting the description to the gauntlet.** The AUTHOR can win by memorising exact attack
  strings into keywords. Hold out a fraction of attacks (run_loop.py already supports train/test
  split) and require the gate to pass on the *held-out* cells too.
- **Breaker mode-collapse.** Without hypermutation it re-emits paraphrases of one winning attack —
  the QD grid fills one column and stalls. The novelty bonus + periodic hypermutation are load-bearing.
- **Trigger scoring is noisy.** `run_eval.py` is a sampled model behaviour; run `runs_per_query>1`
  and treat "broke" as a majority vote, not a single draw, or you will chase phantom failures.
- **Judge grading its own author.** Keep JUDGE a *separate* run from AUTHOR with no shared context;
  a judge that saw the author's reasoning rubber-stamps it (skill-creator's grader.md already warns
  that a pass on a weak assertion is worse than useless).
- **Archive drift vs. reality.** Sibling skills evolve; a false-positive that was valid last month
  may now belong to a renamed sibling. Re-scope the collision set before a fresh forge run.
- **Endless self-play.** Always set the round cap AND the sub-threshold stop; escalation is
  unbounded in principle. The goal is a robust contract, not a perfect one.
