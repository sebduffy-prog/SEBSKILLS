---
name: persona-population-builder
category: strategy
description: >
  Build a large, statistically-grounded synthetic persona population by
  scaffolding on PersonaHub (proj-persona/PersonaHub, 200K preview / 1B full)
  and re-weighting or quota-sampling it to match REAL marginals from census,
  TGI, GWI, or a client segmentation. Use when someone says "build a persona
  population", "generate 5,000 synthetic respondents", "make a synthetic
  audience representative of the UK", "weight personas to census", "rake to
  quota", "seed a synthetic focus group / survey", or needs a defensible cast
  of hundreds-to-thousands of personas that reflects a known population — not a
  handful of hand-written archetypes. Produces a weighted JSONL persona pool
  plus a raking report proving the marginals match.
when_to_use:
  - "You need a large cast (hundreds to thousands) of synthetic personas, not 3-5 archetypes"
  - "The population must be representative of a real audience: census, TGI, GWI, or a client segmentation"
  - "Seeding a synthetic focus group, synthetic survey, or message test with a grounded, quota-correct sample"
  - "You have marginal quotas (age x gender x region x segment share) but not the full joint distribution"
  - "You want a reusable, versioned persona pool that other synthetic-audience skills draw from"
when_not_to_use:
  - "You only need a few hand-crafted archetypes for a deck — write them directly or use audience-segmentation"
  - "You want to RUN the synthetic group/interview once personas exist — use synthetic-focus-group"
  - "You want to A/B test message variants on an audience — use synthetic-audience-message-testing"
  - "You need REAL respondents / real panel data — commission fieldwork or query GWI/Brand24, don't synthesise"
  - "You need a data-derived cluster model from survey data — use audience-segmentation (this consumes one, it doesn't build one)"
keywords: [persona, personahub, synthetic persona, persona population, synthetic audience, quota sampling, raking, iterative proportional fitting, census weighting, tgi, gwi, representative sample, persona-to-persona, text-to-persona, synthetic respondents, marginals, weighting]
similar_to: [synthetic-focus-group, synthetic-audience-message-testing, audience-segmentation]
inputs_needed: >
  A target population definition with marginal quotas (e.g. age band, gender,
  region, social grade, and/or client-segment shares — each summing to ~1.0),
  the desired pool size, and either a PersonaHub download or an LLM to expand
  seed personas. Optional: a client segmentation to overlay.
produces: >
  A weighted JSONL persona pool (one persona per line, each with attributes +
  a rake weight) and a raking report showing achieved vs target marginals, plus
  a reproducible build script.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Persona population builder

A synthetic focus group is only worth running if the cast is
**representative of a real population**. Five vivid archetypes are
storytelling; a thousand personas whose age × gender × region × segment
marginals match census/TGI/GWI is a *sample* — something you can defend in a
room and reuse across studies.

This skill builds that sample. It stands on **PersonaHub**
(`tencent-ailab/persona-hub`, HF dataset `proj-persona/PersonaHub`) for raw
persona diversity, then makes it representative two ways:

1. **Quota-sample** — draw personas so the pool's marginals match targets, or
2. **Rake** — keep the whole pool and assign each persona a *weight* (IPF /
   iterative proportional fitting) so weighted marginals match targets.

Prefer **raking** when you want every persona to appear (analysis stays on the
full pool); prefer **quota-sampling** when downstream tools cost per-persona
(LLM calls) and you want a smaller, already-balanced cast.

## When to use

- You need hundreds-to-thousands of personas, grounded in a real population.
- You have **marginal** quotas but not the joint distribution (surveys publish
  age share and region share separately — raking reconciles them).
- You're feeding [[synthetic-focus-group]] or
  [[synthetic-audience-message-testing]] and want the input cast to be honest.

Do **not** use it to write a handful of deck archetypes ([[audience-segmentation]]),
or to *run* the group once the cast exists ([[synthetic-focus-group]]).

## Prerequisites

- `python3` (3.9 is fine — the raking helper is pure stdlib).
- For downloading real personas: `pip install datasets` then pull
  `proj-persona/PersonaHub` (config `persona` for the 200K preview). For
  net-new persona text: an LLM (OpenAI key, or local vLLM for scale).
- **Licensing (read this):** PersonaHub *code* is MIT; the *data* is
  **CC BY-NC-SA 4.0 — non-commercial, share-alike**. Do not ship the raw
  PersonaHub personas inside a paid client deliverable. For commercial work,
  use PersonaHub only as a *methodology* reference and generate your own
  personas with the `text-to-persona` / `persona-to-persona` approach below.

## Recipe A — Get raw persona diversity

Two grounded routes (both from the PersonaHub paper's methodology):

**A1. Download the preview pool (fastest, non-commercial only):**

```python
from datasets import load_dataset
ds = load_dataset("proj-persona/PersonaHub", "persona", split="train")
# each row: {"persona": "a text description of one persona ..."}
personas = [r["persona"] for r in ds.select(range(20000))]
```

**A2. Generate your own (commercial-safe).** PersonaHub's two scaling methods:

- **text-to-persona** — feed any web/domain text to an LLM and ask *"who is
  likely to read / write / find this useful?"* → one persona per text. Run over
  a corpus (category articles, reviews, forum threads) to harvest breadth.
- **persona-to-persona** — for each seed persona, prompt the LLM for personas
  in *relationships* with it (colleague, patient, neighbour, supplier...). The
  paper iterates this ~6 times to reach people rarely described in raw text
  (the "nurse for the patient of the doctor..."). This is what buys diversity.

Keep the raw output as newline persona strings — that's the substrate.

## Recipe B — Tag personas with the quota attributes

Raking needs each persona labelled on the attributes you hold quotas for. Ask
an LLM to structure each free-text persona into the quota schema, e.g.:

```
For the persona below, output STRICT JSON with keys age ("18-34"|"35-54"|"55+"),
gender ("F"|"M"|"X"), region (one of <list>), grade ("ABC1"|"C2DE"). If unknown,
infer the single most likely value. Persona: {persona}
```

Batch this. The output is one JSON object per persona — your `personas` array.
(For PersonaHub's own downstream tasks, `code/prompt_templates.py` shows the
same `{persona}`-injection pattern; reuse that structure for your tagging
prompt and for any later synthesis.)

## Recipe C — Rake to real marginals (the core step)

Collect targets from census / TGI / GWI as **marginal shares** (each attribute
sums to ~1.0). You do *not* need the joint distribution — that's the point of
raking.

```bash
# personas.json = { "personas": [ {age,gender,region,grade}, ... ],
#                   "targets":   { "age": {"18-34":0.45,...}, "gender": {...}, ... } }
cat personas.json | python3 scripts/rake_quotas.py --max-iter 50 --tol 1e-6 > raked.json
```

`rake_quotas.py` (bundled, pure stdlib) runs IPF: it multiplicatively adjusts
per-persona weights until every weighted marginal matches its target, then
reports `achieved` vs target and `max_error`. Converges in a handful of
iterations for well-posed quotas. Attach `weights[i]` to `personas[i]` and
write JSONL:

```python
import json
raked = json.load(open("raked.json")); src = json.load(open("personas.json"))
with open("pool.jsonl", "w") as f:
    for p, w in zip(src["personas"], raked["weights"]):
        f.write(json.dumps({**p, "rake_weight": round(w, 4)}) + "\n")
```

## Recipe D — Quota-sample instead (smaller balanced cast)

When downstream cost scales per persona, draw a fixed-size cast weighted by the
rake weights (probability-proportional-to-weight, without replacement):

```python
import json, random
rows = [json.loads(l) for l in open("pool.jsonl")]
random.seed(42)
weights = [r["rake_weight"] for r in rows]
cast = random.choices(rows, weights=weights, k=1000)  # ~representative draw
```

`random.choices` is with-replacement; for large pools drawing a small cast that
is acceptable and keeps marginals close. For strict no-replacement, sort by
`weight * random()` (Efraimidis-Spirakis) and take the top-k.

## Verify

Prove the pool is representative before anyone relies on it:

1. **Marginals match.** `max_error` from `rake_quotas.py` should be < `tol`
   (default 1e-6). If it plateaus high, a target cell has **zero personas** —
   the script flags it; go back to Recipe A/B and generate personas for that
   cell (raking cannot invent a demographic that isn't in the pool).
2. **Quotas sum to 1.** The script warns if any target attribute's shares sum
   outside 1.0 ± 0.02 — fix the source numbers.
3. **Weight sanity.** Inspect the weight range. Extreme weights (>5× or <0.2×)
   mean the raw pool is badly skewed vs the target — regenerate more personas
   in the under-represented cells rather than leaning on huge weights.
4. **Effective sample size.** Compute `ESS = (Σw)² / Σw²`. If ESS is far below
   the pool size, weighting is doing too much work — the cast is effectively
   smaller than it looks. Quote ESS, not raw n, in the deck.
5. **Spot-read 10 personas.** Do they read as distinct, plausible humans — or
   as the same template with swapped nouns? If the latter, your Recipe A
   diversity (especially persona-to-persona iterations) was too shallow.

## Pitfalls

- **Marginals ≠ joint.** Matching age and region marginals does **not**
  guarantee the age×region cells are right. If a specific cross matters (e.g.
  young-and-rural), add it as its own target dimension or supply a joint target.
- **Raking can't create coverage.** Zero personas in a target cell → that cell
  stays empty no matter how many iterations. Fix the *pool*, not the weights.
- **Synthetic ≠ real.** A quota-correct synthetic population reproduces
  *structure*, not ground-truth *opinion*. It's a hypothesis generator and a
  stimulus-reaction sandbox, never a substitute for fieldwork on a real
  decision. Label every output "synthetic" and caveat accordingly.
- **Licence leakage.** Shipping raw `proj-persona/PersonaHub` rows in a
  commercial deliverable breaches CC BY-NC-SA 4.0. Generate-your-own for paid
  work (Recipe A2).
- **Over-weighting a tiny base.** If ESS collapses, you've stretched a small
  pool to fake a big one. Generate more personas instead of trusting the
  weights.
- **Stale quotas.** Census/TGI/GWI shares drift. Version the target file with
  its source and fieldwork date so the pool is reproducible and auditable.

## Handoffs

- Run the cast as a group / interviews → [[synthetic-focus-group]].
- Test message variants across the population → [[synthetic-audience-message-testing]].
- Build or interpret the segmentation you're overlaying → [[audience-segmentation]].
