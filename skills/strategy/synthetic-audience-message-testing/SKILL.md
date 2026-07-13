---
name: synthetic-audience-message-testing
category: strategy
description: >-
  Pre-flight ad copy, taglines, value props, or full creative against a
  simulated target audience BEFORE spend, and return a decision-ready readout —
  winner variant, per-message scores, and an objection log. Use to sanity-check
  messaging, rank headline/CTA variants, stress-test a claim, or de-risk a
  campaign when live qual/quant is too slow or too costly. Builds a persona
  population (TinyTroupe / persona-hub), runs a reaction harness, synthesises a
  verdict. NOT a replacement for real research — a fast directional gate.
when_to_use:
  - You have 2+ message/creative variants and need to rank them before media spend
  - A live focus group or brand-lift survey is too slow, too expensive, or too early
  - You want to stress-test a single claim/value-prop for objections and confusion
  - Someone asks to "pre-test", "message test", "copy test", or "gut-check" creative
  - You need a directional readout for a pitch, gate deck, or creative review
when_not_to_use:
  - You want an open-ended moderated discussion, not scored variant ranking — use synthetic-focus-group
  - You only need to build the personas themselves — use persona-population-builder
  - Decision is high-stakes / go-no-go on large budget — treat this as a pre-screen, then commission real research
  - You need statistically projectable market share — use a real panel; synthetic scores are directional only
keywords:
  - synthetic audience
  - message testing
  - copy testing
  - ad pre-testing
  - creative testing
  - tinytroupe
  - persona simulation
  - value proposition
  - a/b copy
  - objection mapping
  - readout
  - strategy
similar_to:
  - synthetic-focus-group
  - persona-population-builder
  - geo-answer-engine-optimization
inputs_needed: 2+ message/creative variants (text or described); a target-audience definition or demography file; OPENAI_API_KEY for live runs
produces: A ranked readout — winner variant, per-variant mean score (clarity/appeal/intent), and a top-objections log — as JSON plus a written recommendation
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Synthetic Audience Message Testing

Pre-flight creative and messaging end-to-end against a **simulated** target
audience and hand back a decision: which variant wins, how each scored, and
what people pushed back on. Three stages — **persona population → reaction
harness → synthesis** — powered by Microsoft's TinyTroupe (MIT).

Treat every output as **directional**, not projectable. Synthetic reactions are
great at surfacing confusion, objections, and relative ranking; they do not
predict real-world conversion rates. Always label the readout as a pre-screen.

## When to use

Use when you hold 2+ variants (headlines, taglines, value props, CTAs, whole
ad concepts) and need a fast, cheap, repeatable gate before committing spend or
booking real research. If you instead want an unscored moderated conversation,
use `synthetic-focus-group`; if you only need the personas, use
`persona-population-builder`.

## Prerequisites

TinyTroupe needs Python **3.10+**. macOS system `python3` is 3.9 — use a newer
one (`brew`-free option: `python3.11` if present, or pyenv). Then:

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install git+https://github.com/microsoft/TinyTroupe.git@main
export OPENAI_API_KEY=sk-...        # required for LIVE runs only
```

TinyTroupe reads model config from a `config.ini` in the working directory (or
falls back to its bundled default). A minimal override:

```ini
[OpenAI]
API_TYPE=openai
MODEL=gpt-5-mini
```

The bundled `scripts/pretest.py --selfcheck` runs with **no key and no network**,
so you can verify the scoring/synthesis path offline before spending tokens.

## Recipe A — three-stage pre-test (canonical)

### 1. Build the persona population

Generate a diverse, demographically-grounded panel. Ship a small demography
JSON (or point at TinyTroupe's `information/populations/usa.json`).

```python
from tinytroupe.factory import TinyPersonFactory

factory = TinyPersonFactory.create_factory_from_demography(
    demography_description_or_file_path="./populations/target.json",
    population_size=8,                       # 6-12 is plenty for ranking
    context="Reactions to soft-drink launch messaging, UK 18-34",
)
panel = factory.generate_people(number_of_people=8, parallelize=True)
```

For a bespoke single persona use `factory.generate_person("A 24yo Glasgow
student, price-sensitive, loves IRN-BRU, skeptical of ads")`.

### 2. Run the reaction harness

Show **each** persona **each** variant in isolation, then extract a structured
reaction. Reset the persona's prompt between variants so an earlier message
can't bias the next (immutable-per-variant, no carry-over).

```python
from tinytroupe.extraction import ResultsExtractor

variants = {
    "A": "Made in Scotland, from girders. Still.",
    "B": "The other national drink. Fearlessly orange.",
}
extractor = ResultsExtractor()
results = {}

for vid, copy in variants.items():
    reactions = []
    for person in panel:
        person.listen_and_act(
            f"You just saw this ad. React honestly as yourself:\n\n{copy}")
        reactions.append(extractor.extract_results_from_agent(
            person,
            extraction_objective=(
                "This person's honest reaction. Rate clarity, appeal and "
                "purchase-intent each 1-5, and quote their verbatim."),
            fields=["clarity", "appeal", "intent", "verbatim"],
        ))
        person.reset_prompt()          # isolate the next variant
    results[vid] = reactions
```

`fields=[...]` forces the LLM to emit those exact keys — the scoring rubric
depends on them. `situation=` and `fields_hints={...}` further constrain the
extraction if reactions drift off-format.

### 3. Synthesise the decision

Fold reactions into a ranked readout. Use the bundled helper, or inline it:

```python
from scripts.pretest import synthesise
readout = synthesise([{"id": k, "reactions": v} for k, v in results.items()])
# -> {"winner": "A", "ranking": [{variant, n, mean_score, top_objections}, ...]}
```

Then write the recommendation in plain English: name the winner, the margin,
the recurring objection to fix, and a one-line caveat that it is directional.

## Recipe B — one-command harness

Drive the whole flow from a JSON config (see `scripts/pretest.py`):

```jsonc
// pretest.config.json
{
  "context": "UK 18-34 soft-drink messaging",
  "population": { "demography": "./populations/target.json", "size": 8 },
  "variants": [
    { "id": "A", "copy": "Made in Scotland, from girders. Still." },
    { "id": "B", "copy": "The other national drink. Fearlessly orange." }
  ]
}
```

```bash
python3 scripts/pretest.py --config pretest.config.json   # live (needs key)
python3 scripts/pretest.py --selfcheck                     # offline validation
```

## Recipe C — ground the personas in real audience data

Don't invent the audience if you can source it. Pull real behavioural signal
first, then encode it into the demography file / factory context:

- **GWI Spark** (`chat_gwi`) — attitudes, media, brand affinity for the segment.
- **persona-hub** — 1B+ persona seeds (code `tencent-ailab/persona-hub`, MIT; HF dataset `proj-persona/PersonaHub`, CC BY-NC) to widen
  diversity beyond one demography sample.
- Client segmentation / TGI — map real segments to persona traits.

Fold those findings into `context=` and the demography traits so reactions
reflect the actual target, not a generic average.

## Verify

```bash
python3 scripts/pretest.py --selfcheck   # asserts winner ranking + objection log
```

A healthy live run should show: (1) every persona produced a reaction per
variant, (2) scores span a range (not all 3.0 — flat scores usually mean the
`fields` weren't emitted and the lexical backstop kicked in), (3) objections are
specific and quotable. If reactions are bland or identical, raise
`population_size`, sharpen the demography, or tighten `extraction_objective`.

## Pitfalls

- **Treating scores as market share.** They are relative and directional. State
  it in the readout; escalate high-stakes calls to real research.
- **Carry-over bias.** Forgetting `person.reset_prompt()` lets variant A colour
  variant B. Isolate every variant.
- **Homogeneous panel.** A thin demography yields near-identical reactions and a
  meaningless ranking. Diversify traits; 6-12 varied personas beat 50 clones.
- **Loose extraction.** Without explicit `fields`, the LLM returns prose and the
  rubric falls back to lexical sentiment. Always pin the fields you score on.
- **Cost drift.** Every persona × variant is an LLM call. Track spend with
  `TinyWorld.pretty_print_global_cost_stats()`; keep panels small while iterating.
- **Ethics.** TinyTroupe is research/simulation only — never present synthetic
  reactions as real human respondents, and never use them to deceive.
