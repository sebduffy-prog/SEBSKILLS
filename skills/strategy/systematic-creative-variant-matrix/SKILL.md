---
name: systematic-creative-variant-matrix
category: strategy
description: >-
  Turn a creative brief into 50+ ad variants laid out as a hypothesis-indexed
  matrix — value-prop x avatar x hook x format x style — where every variant
  differs from a named control by ONE known thing, so when pretest or Meta
  results come back you can attribute the lift to a cause instead of guessing.
  Use to plan a paid-social test slate, replace a random "make 50 ads" dump with
  a designed experiment, or produce the CSV/Sheet a generation pipeline and the
  pretesting + Meta audit loop both read. Ships a stdlib slate generator (OFAT /
  pairs / full-factorial). The design layer, not the renderer.
when_to_use:
  - Planning a batch of paid-social ad variants and you want each to test a specific hypothesis
  - Someone said "generate 50 ads" and you need to make it a designed experiment, not a random dump
  - Building the "creative slate" CSV/Sheet that a generation pipeline (Higgsfield/Firefly/Sora) fills in
  - You want pretest or Meta Ads results to attribute cleanly to value-prop vs hook vs format vs style
  - Standing up the Claude Code skill + scheduled-routine loop for a weekly creative-testing cadence
  - Deciding how many cells you can afford and which factors to hold constant as a control
when_not_to_use:
  - You need to actually render the images/video/copy — use canvas-design, frontend-design, or the media skills
  - You want to interpret a finished pretest readout into a go/refine/kill gate — use creative-pretesting-framework
  - You want to pre-screen messages against a simulated audience — use synthetic-audience-message-testing
  - You are launching/pausing/budgeting live campaigns or pulling ROAS — use paid-media-campaign-ops
  - You just need audience sizing or segments first — use audience-segmentation or the GWI Spark skills
keywords:
  - creative variant matrix
  - ad variants
  - creative slate
  - design of experiments
  - one-factor-at-a-time
  - full factorial
  - hypothesis-indexed
  - value proposition
  - avatar
  - hook
  - ad format
  - creative testing
  - paid social
  - meta ads
  - higgsfield
  - claude code skills
  - scheduled routines
  - attribution
similar_to:
  - creative-pretesting-framework
  - synthetic-audience-message-testing
  - advertising-strategy-copy
  - paid-media-campaign-ops
  - persona-population-builder
inputs_needed: A creative brief / product (value props, target avatars); the factor levels you want to test (value-prop, avatar, hook, format, style options); how many cells you can afford to generate & pretest; optional historical winners to seed the control cell.
produces: A slate CSV (variant_id, hypothesis_id, derived_from, factor_varied, one column per factor, priority, and blank status/prompt/result_url/job_id) ready to hand to a generation pipeline, plus a short read of the experiment design (control cell, factors varied, expected attribution).
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Systematic Creative Variant Matrix

Most "AI ad factory" pipelines make the same mistake: they generate 50 variants
that each differ from every other on five axes at once, run them, and then cannot
say *why* the winner won. This skill fixes the design step. It lays out the slate
as a **hypothesis-indexed matrix** so that when the [creative-pretesting-framework]
scores land — or Meta reports a CTR/ROAS delta via [paid-media-campaign-ops] — you
can attribute the lift to a single lever: this value-prop, this hook, this format.

Grounded on the MindStudio "AI Ad Creative Pipeline (Claude Code + Higgsfield)"
write-up, which builds a Google-Sheets "creative slate tab" of *"30+ variations
with priority scores, value propositions, headlines, avatar types, and video
styles"* and refills it weekly with a scheduled routine. This skill is the
missing experimental-design layer over that slate.

## When to use

You have a brief and are about to spin up a batch of paid-social variants. Use this
BEFORE any pixels are generated to decide the factors, the control, and how many
cells you can afford — then export a slate a generator fills in.

## Prerequisites

- **No API key needed for the design step.** `scripts/slate.py` is pure Python
  stdlib (works on the system python 3.9) and just emits a CSV.
- **The generation + tracking + feedback pieces are separate tools**, cited here
  honestly because the skill hands off to them — none are bundled:
  - **Higgsfield** (image/video gen) is a paid third-party product. The source
    describes a *CLI* used agentically; verify current availability and auth
    yourself before relying on it. Firefly (Adobe MCP tools in this environment),
    Sora, or Veo are drop-in substitutes for the render step.
  - **Google Sheets as the live DB** in the source uses a Workspace CLI; you can
    instead keep the CSV in the repo, or use the Google Drive MCP tools here.
  - **The Meta Ads feedback loop is aspirational in the source** — it names
    "connect your Meta Ads Manager export to the Sheet" as a natural extension
    but *gives no concrete implementation*. Do the live half with
    [paid-media-campaign-ops] (Meta Marketing API insights), and treat closed-loop
    optimisation as something you wire up, not something that exists out of the box.
- **The Claude Code loop is real and current**: reusable prompts live in
  `.claude/skills/`, and the weekly cadence is a scheduled routine — use the
  `schedule` skill (or `CronCreate`) to run "refill the slate / generate blanks".

## Recipe 1 — Design the experiment (do this first)

1. **Pick the control cell.** One level per factor, ideally your current best
   performer or safest prior (`saves-time / busy-parent / problem-agitate /
   9x16-story / ugc-selfie`). Everything is measured *against* this.
2. **List the factors and levels you actually want to learn about.** Five factors
   is plenty. Fewer, sharper levels beat many vague ones. Write them as a JSON map,
   control level FIRST in each list:

   ```json
   {
     "value_prop": ["saves-time", "saves-money", "status"],
     "avatar":     ["busy-parent", "gen-z-saver"],
     "hook":       ["problem-agitate", "bold-claim", "question"],
     "format":     ["9x16-story", "1x1-square"],
     "style":      ["ugc-selfie", "hypermotion", "unboxing"]
   }
   ```
3. **Choose a design by how much attribution you need vs how many cells you can pay
   to pretest:**
   - **`ofat`** (one-factor-at-a-time) — control + each non-control level varied
     *singly*. Cleanest attribution, smallest n (the JSON above → 9 cells). Start
     here when budget is tight and you want unambiguous reads.
   - **`pairs`** — OFAT plus every 2-factor interaction (above → 34; richer level
     sets clear 50+). Use when you suspect a hook only works for one avatar, etc.
   - **`full`** — full cartesian product, capped by `--max` (above → 108). Max
     coverage, zero attribution discipline: only when you genuinely want every cell
     and will lean on the pretest to rank, not explain.

## Recipe 2 — Generate the slate CSV

```bash
python3 scripts/slate.py factors.json --design ofat   > slate.csv
python3 scripts/slate.py factors.json --design pairs  --out slate.csv
python3 scripts/slate.py factors.json --design full   --max 60 --out slate.csv
```

Columns emitted:
`variant_id, hypothesis_id, derived_from, factor_varied, <one per factor>,
priority, status, prompt, result_url, job_id`.

- `hypothesis_id` + `factor_varied` are the attribution keys — every row says
  which single lever (or `factor+factor` pair) it moved off the control.
- `priority` auto-scores single-factor cells highest (100 control, 90 OFAT,
  60 interaction) because they yield the cleanest reads — sort by it to pick what
  to generate first when you can't afford them all.
- `status / prompt / result_url / job_id` are left **blank** on purpose: they are
  the generation pipeline's contract. A downstream routine finds blank-`status`
  rows, renders them, and writes the URL + job id back — exactly the
  Sunday-plan / Monday-generate split in the source.

## Recipe 3 — Hand off to generation, pretest, and the audit loop

1. **Generate** the blank rows (Higgsfield/Firefly/Sora), writing `result_url`
   and `job_id` back per row. Keep a hard rule in your render skill (e.g. *"always
   preserve the reference product image exactly"*) to stop hallucinated packaging.
2. **Pretest** the slate with [synthetic-audience-message-testing] for a fast
   directional cut, then [creative-pretesting-framework] for the real go/refine/kill
   gate on the survivors. Join scores back on `variant_id`.
3. **Attribute.** Group the scores by `factor_varied`: the average delta of all
   `value_prop` cells vs control estimates the value-prop effect, and so on. This
   is only valid *because* each cell moved one lever — the whole point of the matrix.
4. **Go live & close the loop.** Push winners with [paid-media-campaign-ops]; pull
   CTR/ROAS/frequency back, join on `variant_id`, and let the weekly `schedule`
   routine seed next week's control cell from the real winner. That compounding —
   *"every generation makes the next batch better"* — is the source's core mechanic.

## Verify

- `python3 scripts/slate.py factors.json --design ofat` prints a header + rows;
  stderr reports the count. The example JSON gives 9 (ofat), 34 (pairs), 108 (full).
- Exactly ONE row has `factor_varied = none` (the control) in ofat/pairs designs.
- Every non-control row changes the stated `factor_varied` column away from the
  control level and leaves all *other* factor columns at the control level (ofat)
  — spot-check two rows by eye.
- `status`, `prompt`, `result_url`, `job_id` are empty in every row of a fresh slate.
- Bad input fails loudly: `echo '{}' | ...` → a clear `ValueError`, not a silent
  empty file.

## Pitfalls

- **Confounded cells kill attribution.** If a variant differs from control on two
  axes, you cannot credit either — that is why `ofat` is the default and `full` is
  flagged as attribution-free. Do not eyeball a `full` slate and claim "the hook won".
- **Factorials explode.** 5 factors x 4 levels = 1024 cells. You cannot pretest or
  pay for that. Design for what you can *measure*, not what you can *enumerate*;
  `full` is `--max`-capped for exactly this reason.
- **"50+ variants" is a target, not a virtue.** A tight 12-cell ofat slate that
  answers "which value-prop, which hook" beats 60 confounded cells. Hit 50+ only
  when you have the pretest budget to read them.
- **The Meta closed loop is not free.** The source names it as an extension with no
  code; assume you are building the export -> join -> reseed wiring yourself via
  paid-media-campaign-ops, and don't promise a client live auto-optimisation you
  haven't wired.
- **Higgsfield/CLI specifics drift.** Third-party gen tools change auth, pricing,
  and CLI surface fast. Treat the render step as swappable and verify the current
  tool before scripting a scheduled routine around it.
- **Control must be a real prior.** A random control cell means every delta is
  measured against noise. Seed it from a historical winner or your safest bet.
