---
name: synthetic-focus-group
category: strategy
description: >-
  Run a synthetic focus group, brainstorm or concept-reaction session with Microsoft
  TinyTroupe LLM personas for fast, cheap, directional reactions to concepts, copy,
  naming, packaging and creative BEFORE spending on real recruit. Spins up a TinyWorld
  of defined agents, broadcasts stimulus, runs turns, and extracts structured verbatims,
  objections and votes. Trigger on "synthetic focus group", "simulate a focus group",
  "AI personas react to this", "TinyTroupe", "brainstorm with agents", "pre-test this
  concept cheaply", "what would our audience say about this ad". Directional only —
  never a substitute for real fieldwork or a sample-representative claim.
when_to_use:
  - You have a concept, tagline, name, pack or ad and want a same-hour directional read before real research
  - You need to pressure-test messaging for obvious objections, confusions or dead-on-arrival ideas
  - You want a cheap brainstorm of reactions/ideas from several distinct personas at once
  - You are prioritising which of N concepts to take into a real qual round
  - You want to rehearse a discussion guide / stimulus order before moderating live
when_not_to_use:
  - You need defensible, sample-representative numbers or a verdict — use [[qualitative-research]] or real quant
  - You only need the personas themselves defined/generated, not run in a session — use [[persona-population-builder]]
  - You are testing a single message at scale for lift/preference — use [[synthetic-audience-message-testing]]
  - You need real human verbatims for a creative team to write from — use [[qualitative-research]]
keywords:
  - synthetic focus group
  - tinytroupe
  - persona simulation
  - concept testing
  - brainstorm
  - agent based
  - message pre-test
  - directional research
  - tinyworld
  - results extractor
  - llm personas
  - creative reaction
similar_to:
  - persona-population-builder
  - synthetic-audience-message-testing
  - qualitative-research
inputs_needed: >-
  A stimulus (concept/copy/name/image-description); 3-8 persona definitions or a demography
  file; an OpenAI or Azure OpenAI API key in the environment; Python 3.10+ venv.
produces: >-
  A run transcript plus a structured extraction (JSON) of reactions, objections, standout
  verbatims and a directional vote per persona — ready to fold into a qual debrief.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Synthetic focus group (TinyTroupe)

Spin up a handful of LLM personas, put a concept in front of them, let them
talk, and pull out structured reactions — in minutes, for cents. This is a
**directional smoke test**, not research. Use it to kill dead-on-arrival ideas,
surface obvious objections, and prioritise what deserves real fieldwork.

```
DEFINE PERSONAS  →  BUILD TINYWORLD  →  BROADCAST STIMULUS  →  RUN TURNS  →  EXTRACT
```

## When to use

- A same-hour directional read on a concept / tagline / name / pack / ad
- Finding the obvious objections and confusions before a live group hears them
- Ranking N concepts to decide which 2 go into real qual
- Rehearsing stimulus order and a discussion guide before moderating

**Do not** present these outputs as representative of a real population, and do
not report percentages as if sampled. It is a hypothesis generator. Real people
still decide (see `qualitative-research`).

## Prerequisites

TinyTroupe needs Python **3.10+**. macOS system `python3` is 3.9 — use a newer
one (`brew`-free option: `python3.11` if present, or pyenv). Then:

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install "git+https://github.com/microsoft/TinyTroupe.git@main"
export OPENAI_API_KEY="sk-..."         # or AZURE_OPENAI_KEY + AZURE_OPENAI_ENDPOINT
```

TinyTroupe reads a `config.ini` if present (model, cache). Defaults call an
OpenAI model. Enable the API cache so re-runs during authoring are free:

```python
from tinytroupe import config_manager
config_manager.update("cache_api_calls", True)   # writes ./tinytroupe_cache.pickle
```

Cost: each persona-turn is one LLM call. A 5-persona, 3-turn group is ~15-25
calls — cents on a mini model. Print the tally after every run (see Verify).

## Recipe A — hand-defined focus group (most control)

Best when you know exactly who you want in the room (recruit spec from a real
screener). Define each persona explicitly, then run.

```python
from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld
from tinytroupe.extraction import ResultsExtractor
from tinytroupe import config_manager

config_manager.update("cache_api_calls", True)

def make_persona(name, age, occupation, traits, interests, context):
    p = TinyPerson(name)
    p.define("age", age)
    p.define("occupation", {"title": occupation, "description": context})
    p.define("personality", {"traits": traits})
    p.define("preferences", {"interests": interests})
    return p

maya = make_persona(
    "Maya", 34, "Primary school teacher",
    ["You are warm, practical and sceptical of hype.",
     "You mention your two kids and a tight budget."],
    ["family days out", "value for money", "healthy snacks"],
    "You shop the mid-market, distrust premium pricing, read ingredient labels.")

ade = make_persona(
    "Ade", 27, "Junior software engineer",
    ["You are early-adopter, brand-fluent and blunt.",
     "You call out anything that feels 'trying too hard'."],
    ["gaming", "energy drinks", "streetwear"],
    "You buy on vibe and social proof; price matters less than credibility.")

# 3-8 personas is the sweet spot. More than 8 and turns get expensive and muddy.
group = [maya, ade]

world = TinyWorld("Focus group room", group)
world.make_everyone_accessible()          # let personas react to each other

STIMULUS = """We're testing a new oat-milk energy drink called 'DAWN'.
Tagline: 'Fuel that gives a damn.' Can, £1.80, sold in supermarkets and gyms.
React honestly — would you buy it, what puts you off, what's confusing?"""

world.broadcast(STIMULUS)                  # every persona hears the stimulus
world.run(3)                               # 3 conversational turns
```

Then extract structured output rather than re-reading the transcript by hand:

```python
extractor = ResultsExtractor()

results = extractor.extract_results_from_agents(
    group,
    extraction_objective=(
        "For each persona summarise: their gut reaction, whether they'd buy "
        "(yes/no/maybe), the single biggest objection, and one verbatim quote."),
    situation="A synthetic focus group reacting to the DAWN energy-drink concept.",
    fields=["name", "gut_reaction", "would_buy", "biggest_objection", "verbatim"],
    fields_hints={"would_buy": "one of: yes / no / maybe"},
    verbose=True,
)

import json
print(json.dumps(results, indent=2, ensure_ascii=False))
```

`extract_results_from_agents` returns a list (one item per agent) shaped by your
`fields`. Save both the raw run and the extraction.

## Recipe B — generate the room from a demography (fast, less control)

When you don't have hand-written personas, let the factory build a plausible
population, then run the same session. Pairs with `persona-population-builder`.

```python
from tinytroupe.factory import TinyPersonFactory

factory = TinyPersonFactory.create_factory_from_demography(
    "./populations/uk.json",               # or a plain-text demography description
    population_size=6,
    context="UK grocery shoppers reacting to new-product concepts.")

group = factory.generate_people(6, parallelize=True, verbose=True)
# ...then identical TinyWorld / broadcast / run / extract as Recipe A.
```

If you have no demography file, `TinyPersonFactory(context=...).generate_person(
"a budget-conscious mum of two in Leeds")` mints one persona at a time.

## Recipe C — brainstorm (ideas, not reactions)

Same machinery, different broadcast — ask personas to *generate*, then reduce.

```python
world.broadcast(
    "Brainstorm names and 10-word ad lines for a caffeine-free oat energy "
    "drink aimed at tired parents. Build on each other's ideas.")
world.run(4)

ideas = extractor.extract_results_from_world(
    world,
    extraction_objective="A de-duplicated list of the naming and line ideas raised.",
    fields=["idea", "type", "raised_by", "why_it_could_work"],
)
```

## Verify

- **It ran end to end**: the transcript shows each persona speaking *in
  character* and reacting to the stimulus (and to each other if
  `make_everyone_accessible()` was called). Off-topic drift = weak persona
  definitions; tighten `traits`/`context`.
- **Extraction is structured**: `results` is a list with one entry per persona
  and your exact `fields` populated — not free prose.
- **Cost sanity**: print the tally so a run can't silently balloon:

  ```python
  TinyPerson.pretty_print_global_cost_stats()
  TinyWorld.pretty_print_global_cost_stats()
  ```

- **Determinism for A/B**: with `cache_api_calls` on, re-running the same
  stimulus reuses cached calls — so when you swap one concept for another the
  delta is the concept, not model noise.

## Pitfalls

1. **Treating it as real research.** These are language-model guesses at how a
   *described* person might talk — no lived experience, no real spend. Never put
   a percentage from a 6-agent room in a deck as a finding. It is a hypothesis
   engine that feeds `qualitative-research`, not a replacement for it.
2. **Sycophancy / mode-collapse.** LLM personas skew agreeable and converge on
   each other. Force dissent: give at least one persona a sceptic trait, and ask
   the extraction for "the biggest objection" so negativity is elicited, not
   optional.
3. **Thin personas → generic answers.** A persona defined only by age+job
   produces beige "as a consumer I would…" text. Add friction: budget, distrust,
   a specific ritual, how they *talk*. Reuse your real screener quotas.
4. **Python 3.9 will fail install.** TinyTroupe needs 3.10+. The macOS default
   `python3` is 3.9 — create the venv with `python3.11`/pyenv or the import
   errors are cryptic.
5. **Leading the witness.** A broadcast that says "React to our *exciting* new
   drink" primes praise. Keep stimulus neutral, exactly as you would a real
   discussion guide (mirror the rules in `qualitative-research`).
6. **Too many agents / turns.** Beyond ~8 personas or ~5 turns the conversation
   muddies and cost climbs linearly. Small rooms, short runs, multiple concepts.
7. **Stale cache masking changes.** The API cache is keyed on the call — if you
   change persona definitions but reuse cached calls you may not see the effect.
   Delete `tinytroupe_cache.pickle` when personas change materially.
8. **No stimulus provenance.** Log the exact stimulus text with each run; a
   one-word change to the concept invalidates comparison to prior runs.

## Handoffs

- **Input from** [[persona-population-builder]] (the room) and a real screener
  (recruit spec so synthetic personas mirror intended quotas).
- **Output to** [[qualitative-research]] (hypotheses + objection list to probe
  with real people), [[synthetic-audience-message-testing]] (when the winning
  concept needs single-message lift at scale), and
  [[advertising-strategy-copy]] (objections become copy to pre-empt).
- **Reality check**: any directional read here is a *hypothesis*. Confirm with
  real fieldwork before it drives spend.
