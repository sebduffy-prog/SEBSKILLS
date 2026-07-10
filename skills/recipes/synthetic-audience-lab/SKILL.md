---
name: synthetic-audience-lab
category: recipes
description: >
  Recreate a silicon-sampling / synthetic-persona message-testing lab (the
  "ask an AI audience before you spend" capability behind tools like Synthetic
  Users or Yabble Nexus) as a COMBO of proven SEBSKILLS. Builds a
  census/TGI/GWI-weighted persona population (persona-population-builder), runs an
  open moderated session (synthetic-focus-group), scores ranked variants
  (synthetic-audience-message-testing), then folds both into a defensible
  readout (qualitative-research). Use to clone an AI-persona panel or
  pre-flight copy before real fieldwork. Directional qual only, never a survey
  statistic.
when_to_use:
  - "You want a full silicon-sampling lab — build audience, run qual, score messages, write it up — not just one step"
  - "Pre-flight taglines, value props, concepts or full creative against a grounded AI audience before commissioning real research"
  - "You need the personas to reflect a REAL population (census, TGI, GWI, or a client segmentation), not 3-5 hand-written archetypes"
  - "You want both open reactions AND ranked variant scores from the same defensible cast, then one combined narrative"
  - "Standing up a reusable, versioned synthetic-audience panel other studies can draw from"
when_not_to_use:
  - "You only need the weighted persona cast → use persona-population-builder directly"
  - "You only want an open moderated discussion, no scoring → use synthetic-focus-group directly"
  - "You only want ranked variant scores + objection log → use synthetic-audience-message-testing directly"
  - "You only need to structure/write findings you already have → use qualitative-research directly"
  - "You need statistically projectable market share → commission a real panel; this recipe is directional only"
keywords: [silicon sampling, synthetic personas, synthetic audience, ai persona panel, message testing, copy pretesting, tinytroupe, persona hub, census weighting, tgi, gwi, brand24, focus group simulation, qualitative readout, directional research, recipe, combo]
similar_to: [persona-population-builder, synthetic-focus-group, synthetic-audience-message-testing]
inputs_needed:
  - "Audience definition + real marginals to weight to (census / TGI / GWI export / client segmentation)"
  - "Stimulus: concepts, taglines, value props, or 2+ message/creative variants to test"
  - "A discussion guide / stimulus order for the moderated session"
  - "Grounding data for reactions where available (GWI Spark pulls, Brand24 verbatims) so reactions cite real behaviour, not invention"
  - "OPENAI_API_KEY (or equivalent capable LLM key) — the one hard external dependency for the persona runs"
produces: A versioned run directory — weighted persona pool (JSONL) + raking report, moderated-session verbatims/objections/votes, a ranked message readout (winner, per-variant scores, objection log), and a combined qualitative writeup explicitly labelled directional/pre-screen with its grounding sources logged.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Synthetic Audience Lab (silicon-sampling panel, recreated as a combo)

A recipe that recreates a **silicon-sampling / synthetic-persona message-testing lab** by
chaining four skills already in this library. Give it an audience definition and some stimulus;
it builds a grounded cast, runs an open session, scores your variants, and hands back one
defensible qualitative readout.

## What it recreates

The capability behind AI-audience products like **Synthetic Users**, **Yabble Nexus**, and
**Fairing/quant-flavoured "AI panel"** tools — and the academic **"silicon sampling"** idea
(Argyle et al.): stand up LLM personas conditioned on a real population, put stimulus in front of
them, and read the reactions before spending on live recruit. Those products wrap a hosted model
+ persona store + reaction harness; this recipe reproduces the same loop locally by stitching
sibling skills together, so you own the cast, the transcripts, and the grounding.

## Feasibility

**AMBER.** Reproducible on this machine EXCEPT that the persona reactions need an external LLM
(the **`synthetic-focus-group`** and **`synthetic-audience-message-testing`** steps call
TinyTroupe/OpenAI — that is the amber link: it needs an API key and cannot run fully offline).
Everything else — building and raking the persona pool, and the qualitative readout — is local.

Honesty gate on the OUTPUT:

- **AMBER — ship as grounded QUALITATIVE direction.** Verbatims, objections, and relative
  variant ranking, presented as a directional pre-screen and labelled as such.
- **RED — do NOT ship** the same numbers as survey statistics, projectable share, or "% of the
  market". Synthetic scores are not a sample. Never fabricate percentages; ground reactions on
  real **GWI** / **Brand24** behaviour where you have it, and where you don't, say so.

## The combo

An ordered chain — each step is an exact sibling skill:

1. **`persona-population-builder`** — build the cast. Scaffold on PersonaHub and re-weight /
   quota-sample it to your REAL marginals (census, TGI, GWI, or a client segmentation). Output: a
   weighted JSONL persona pool + a raking report proving the marginals match.
2. **`synthetic-focus-group`** — run the open session. Spin up a TinyWorld from the pool,
   broadcast the discussion guide/stimulus, run turns, and extract structured verbatims,
   objections, and votes. This is the qualitative "why".
3. **`synthetic-audience-message-testing`** — score the variants. Run the reaction harness over
   your 2+ message/creative variants and return a ranked readout: winner, per-variant
   clarity/appeal/intent means, and an objection log. This is the directional "which".
4. **`qualitative-research`** — the readout. Fold the open reactions and the scored ranking into
   ONE structured, defensible narrative with the directional/pre-screen caveats and grounding
   sources baked in. (Optionally hand to `data-cut-headline-stats` or `insight-to-deck-autopilot`
   only for presentation — never to re-cast direction as statistics.)

## Prerequisites

- The four sibling skills above installed (they are — strategy category).
- `OPENAI_API_KEY` (or equivalent) for steps 2-3; TinyTroupe/persona-hub dependencies per those skills.
- Real marginals to weight to (a census/TGI/GWI table or a client segmentation file).
- OPTIONAL but recommended grounding connectors: **GWI Agent Spark** and **Brand24** MCP, so
  reactions can be anchored to real audience behaviour and real social verbatims.
- A writable run directory to version pool, transcripts, scores, and the writeup.

## Run it

1. **Define the audience + quotas.** Write down the target and its marginals (age × gender ×
   region × segment share). Pull supporting behaviour from GWI Spark / Brand24 now so the
   personas and their reactions can cite it later.
2. **Build the pool** — invoke **`persona-population-builder`** with those marginals. Check the
   raking report: marginals must match before you proceed. Save `personas.jsonl`.
3. **Run the open session** — invoke **`synthetic-focus-group`** on a sample drawn from the pool,
   feeding your discussion guide and stimulus order. Capture verbatims, objections, votes.
4. **Score the variants** — invoke **`synthetic-audience-message-testing`** with the same pool and
   your 2+ variants. Capture the ranked readout JSON (winner, per-variant means, objection log).
5. **Write the readout** — invoke **`qualitative-research`** to synthesise steps 3-4 into one
   narrative: what personas said, which message won and why, the objection map, and the explicit
   directional caveat. Log every grounding source (GWI/Brand24 pulls) alongside claims.
6. **Deliver** — hand the writeup on as-is, or pass to a deck skill for presentation. Keep the
   run directory so the study is reproducible and auditable.

## Verify

- **Pool is representative:** the raking report from step 2 shows post-weight marginals within
  tolerance of the target. If not, do not run the sessions.
- **Reactions are grounded, not invented:** spot-check verbatims against the GWI/Brand24 evidence
  you pulled; any reaction that asserts a behaviour with no backing gets flagged, not shipped.
- **No fabricated statistics:** grep the readout for stray percentages. Every number is either a
  variant score labelled "directional (synthetic)" or a real data point with a cited source.
- **Caveat present:** the deliverable states, up front, that it is a synthetic pre-screen and not
  sample-representative.
- **Reproducible:** re-running from the saved pool + seeds reproduces the same cast and comparable
  reactions.

## Pitfalls

- **Silicon sampling ≠ a survey.** The single biggest failure is dressing directional scores as
  projectable stats. Keep the RED line: rank and read, never quote as share.
- **Ungrounded personas hallucinate.** Without census/TGI/GWI weighting in step 1 you get generic
  LLM opinion, not audience signal — always rake first, always ground reactions.
- **Fabricated percentages.** LLM personas will happily emit "73% of us would buy this." Strip
  invented numbers; only real GWI/Brand24 figures survive into the readout.
- **Same pool for both sessions.** Draw steps 3 and 4 from the SAME weighted pool so the qual and
  the scoring describe one audience, not two different casts.
- **Amber step offline.** Steps 2-3 need the LLM key; if it is missing, the lab cannot run —
  don't silently skip to a fabricated readout.
- **High-stakes calls.** For go/no-go on large budgets, treat this as a pre-screen and escalate to
  real fieldwork; say so in the deliverable.
