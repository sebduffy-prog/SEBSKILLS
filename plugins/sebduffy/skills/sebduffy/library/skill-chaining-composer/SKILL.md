---
name: skill-chaining-composer
category: meta-router
description: >
  Turn ONE compound request into an ordered chain of skills: decompose the job into sub-tasks,
  map each sub-task to the right skill, order them by artifact dependency, and pass the output
  of each step as the input of the next. Reach for this when a task obviously needs several
  skills in sequence — "extract this PDF then chart it then put it in a deck", "scrape, clean,
  analyse, visualise", "research then write then format", "build the app then deploy it then
  screenshot it". Produces a numbered execution plan (which skill, what it consumes, what it
  produces) plus a dependency check that catches cycles and missing handoff artifacts BEFORE
  you run anything.
when_to_use:
  - "A single request clearly spans multiple skills run back-to-back (extract → clean → chart → deck)"
  - "One step's output is the next step's input and you need the handoff order right"
  - "You're unsure whether to do it in one skill or split it across several, and in what order"
  - "A multi-stage pipeline keeps stalling because a later skill is missing an artifact an earlier one should have made"
  - "You want a written plan of the whole chain before committing tool calls / edits"
  - "Composing a user-invoked orchestrator that fans out to several model-invoked skills"
when_not_to_use:
  - "The task is a single capability — just let the one matching skill trigger, or use automatic-skill-decision to pick it"
  - "You don't yet know which skill fits a sub-task → skill-gap-detector (is there even a skill?) or automatic-skill-decision (which one?)"
  - "The request is vague / underspecified — pin down requirements first with requirement-elicitation, THEN chain"
  - "Independent tasks with no shared artifacts and no ordering → dispatching-parallel-agents (run them concurrently, don't chain)"
  - "Executing an already-written multi-step implementation plan in code → executing-plans / subagent-driven-development"
keywords: [skill chaining, compose skills, chain skills, skill orchestration, sequence skills, multi-skill, pipeline, decompose task, dependency order, topological, artifact handoff, sub-tasks, workflow composition, meta router, skill pipeline, orchestrator, daisy chain, skill composition]
similar_to: [automatic-skill-decision, requirement-elicitation, skill-gap-detector, dispatching-parallel-agents]
inputs_needed:
  - "The full compound request in the user's own words (all the things they want, end to end)"
  - "The final deliverable / artifact they actually want out the other end"
  - "Any inputs that already exist (files, URLs, data) vs. things a step must produce"
  - "Whether steps are truly sequential (output feeds input) or actually independent (parallelisable)"
produces: A numbered, dependency-ordered skill chain — per step the skill, its consumed inputs and produced artifact — validated against cycles and missing handoffs
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Skill-Chaining Composer

Some requests are one skill. Many are **several skills in a row**, where each step hands an
artifact to the next: *"pull the tables out of this PDF, clean them, chart the trend, and drop
it into a deck"* is `pdf → xlsx → dataviz → pptx`. This skill decomposes the job, assigns a
skill per sub-task, **orders them by what-produces-what**, and checks the chain is buildable
before a single tool call runs.

Core discipline (from the way skills compose): sequence **deliberately by data dependency**,
not by arbitrary chaining. An orchestrating (user-invoked) skill may call reusable
(model-invoked) skills, but keep each link doing one job and passing a concrete artifact
forward.

## When to use

The moment a request contains **"then" / "and then" / "after that"**, or names an input format
and a different output format (PDF in, deck out), you're chaining. If it's one capability, skip
this and let that skill fire (or use `automatic-skill-decision` to pick it). If the sub-tasks
don't feed each other, don't chain them — fan them out with `dispatching-parallel-agents`.

## The five-step method

1. **Decompose.** Break the request into the smallest sub-tasks that each map to *one*
   capability. Write them as verbs: *extract, clean, analyse, visualise, assemble, deploy,
   screenshot*. Don't stop at the headline task — surface the implicit steps (a deck needs a
   chart; a chart needs clean data; clean data needs extraction).
2. **Map skill → sub-task.** For each sub-task, name the skill that owns it. Use the available
   skills list. If none fits a sub-task, that's a **gap** → `skill-gap-detector`; if two could
   fit, pick with `automatic-skill-decision`. A sub-task with no skill and no gap-fill is done
   inline.
3. **Declare artifacts.** For every step write what it **needs** (input artifact keys) and what
   it **produces** (output artifact keys). This is the contract between links. The next step's
   `needs` must match some earlier step's `produces` (or a pre-existing input).
4. **Order by dependency.** A step can only run once every artifact it `needs` exists. Sort so
   producers come before consumers. Run `scripts/chain_plan.py` to get the order and to catch
   **cycles** (A needs B needs A) and **duplicate producers** automatically.
5. **Run link-by-link, verifying each handoff.** Execute in order. After each step, confirm the
   promised artifact actually exists and is well-formed before invoking the next skill — a
   broken handoff is the #1 cause of stalled chains. Carry only the artifact forward, not the
   whole prior context.

## Recipe — plan a chain, then run it

Write the chain as JSON (id, skill, needs, produces) and let the planner order + validate it:

```bash
cd skills/meta-router/skill-chaining-composer
cat > /tmp/chain.json <<'JSON'
[
  {"id":"extract", "skill":"pdf",     "needs":[],              "produces":["rows.csv"]},
  {"id":"clean",   "skill":"xlsx",    "needs":["rows.csv"],    "produces":["clean.xlsx"]},
  {"id":"chart",   "skill":"dataviz", "needs":["clean.xlsx"],  "produces":["fig.svg"]},
  {"id":"deck",    "skill":"pptx",    "needs":["fig.svg"],     "produces":["out.pptx"]}
]
JSON
python3 scripts/chain_plan.py /tmp/chain.json
```

Output is the runnable order plus any **pre-existing inputs** you must supply (artifacts no step
produces). Then invoke each skill in that order via the `Skill` tool, passing the produced
artifact of step *n* into step *n+1*.

The planner is order-insensitive — list steps in any order; it topologically sorts them and
exits non-zero with a precise reason if the chain can't be built (cycle / two steps claiming the
same artifact). Fix the plan until it's clean, *then* execute.

## Common chains (patterns)

- **Document pipeline** — `pdf` (extract) → `xlsx` (clean/compute) → `dataviz` (chart) →
  `pptx`/`docx` (assemble). Formats change; the shape is extract → transform → visualise → package.
- **Research → deliverable** — `deep-research` (cited findings) → `doc-coauthoring`/`internal-comms`
  (draft) → `theme-factory`/`brand-guidelines` (style) → `docx`/`pptx` (final file).
- **Build → ship → prove** — `frontend-design` (build UI) → `design-approval-gate` (preview +
  sign-off) → `use-railway`/Vercel (deploy) → `webapp-testing` (screenshot / verify live).
- **Data story** — scrape/connector MCP → `data-analysis` → `dataviz` → artifact. Each link's
  output is the next's input; nothing runs before its data exists.

## Sequential vs. parallel (decide before you order)

Chain **only** when output feeds input. If sub-tasks share no artifacts (e.g. "audit auth" +
"review the cache" + "typecheck utils"), they're independent — hand them to
`dispatching-parallel-agents` and run concurrently. Mixed jobs: parallelise the independent
front, then chain the dependent tail. The planner's dependency graph makes the split obvious —
steps with `indeg 0` that share no downstream can go in parallel.

## Verify

- `python3 scripts/chain_plan.py /tmp/chain.json` exits **0** and prints a full order covering
  every step (no step dropped = no cycle).
- Every `needs` artifact is either produced by an earlier step or listed under "pre-existing
  inputs" — no dangling handoff.
- Dry-run the first link; confirm it emits exactly the artifact its `produces` promises before
  wiring the rest.
- After each real step, the next skill's precondition (its input file/URL/data) is present.

## Pitfalls

- **Chaining independent tasks.** If B doesn't consume A's output, you've serialised for no
  reason — parallelise instead. Look for a real artifact on every edge; if there isn't one, it's
  not a chain.
- **Skipping decomposition.** Jumping straight to "which skills" misses implicit steps (the deck
  silently needs a chart that needs clean data). Enumerate sub-tasks first, map second.
- **Vague artifacts.** "the data" / "the stuff" breaks handoffs. Name concrete artifacts
  (`clean.xlsx`, `fig.svg`) so step *n+1* knows exactly what it's receiving.
- **Two steps producing the same artifact.** Ambiguous ownership — the planner rejects it. One
  producer per artifact.
- **Hidden cycle.** A needs B, B needs A (often via a shared file). The planner catches it; the
  fix is usually a missing extraction/prep step that breaks the loop.
- **Context bleed between links.** Passing the whole prior transcript instead of just the
  artifact bloats context and confuses the next skill. Hand forward the artifact, not the story.
- **Chaining before requirements are clear.** If the request is underspecified, you'll build the
  wrong chain fast — run `requirement-elicitation` first, then compose.
- **A missing link.** If a sub-task has no owning skill, don't fake it silently — flag the gap
  (`skill-gap-detector`) or do that step inline and note it in the plan.
