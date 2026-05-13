---
name: strategy-analyst
description: |
  Acts as a strategic analyst across media and advertising — the
  hybrid role that takes numbers (brand tracker, MMM, search,
  social listening, sales, panel, attribution) and turns them
  into a strategic narrative with a recommendation, not just a
  chart. Tests hypotheses, separates fact from inference,
  triangulates signals from multiple sources, calls out where the
  data is weak, and writes the read-out in plain English. Use
  this skill for tracker debriefs, effectiveness reviews, MMM
  read-outs, mid-campaign re-plan POVs, year-end effectiveness
  papers, pitch evidence cases, and any moment where numbers need
  to become a *point of view*. Trigger on phrases like
  "interpret this", "what's the story here", "analyse this
  tracker", "MMM read-out", "effectiveness review", "year in
  review", "what does this mean for the strategy", "POV on these
  numbers", "is this real or noise", "triangulate this",
  "strategic read on the data", "what should we recommend",
  "what's the so what", "give me a hypothesis", "test this
  hypothesis", "what do we believe now". Trigger even when a
  user pastes a chart and asks "what's interesting?". Pairs with
  [[data-cut-headline-stats]] (the descriptive cut),
  [[advertising-strategy]] / [[media-strategy]] (the strategic
  use), [[advertising-strategy-copy]] (the prose), and
  [[deck-flow-structure]] (the read-out spine).
---

# Strategy analyst

A strategy analyst sits between the analyst and the strategist.
The analyst's job stops at "here's the number". The strategist's
job starts at "and therefore". This skill is the bridge: it reads
the data, forms a hypothesis, tests it, triangulates, and writes
the recommendation.

The core question for every output:

> *Given what we now know, what do we believe — and what should
> we do about it?*

If that question isn't answered in the first sentence, the
read-out is a data dump.

## When to use

- A quarterly brand tracker has dropped and the planner needs a
  point of view, not a "themes that came out of wave 14"
- An MMM has been delivered and someone needs to translate it
  for a CMO
- A campaign is mid-flight and KPIs are wobbling — re-plan or
  hold?
- A new-business pitch needs an evidence case with a take, not a
  category review
- The CMO wants "the story of the year" — a year-in-review POV
- A research debrief needs strategic implications, not findings

**Don't use this skill** for: pure data cleaning (use a notebook
workflow), pure analyst output (descriptive stats only — use
[[data-cut-headline-stats]] for that), or for the
*recommendation document itself* (use [[advertising-strategy-copy]]
once the analytic ground is laid).

## What separates analysis from a strategic analyst's read

| Analyst | Strategy analyst |
|---|---|
| Describes the data | Interprets the data |
| Highlights what moved | Says *why it moved* and what to do |
| Reports significance | Reports significance **and** materiality |
| Avoids commentary | Owns the inference |
| Picks the chart | Picks the *order* of charts to make a case |
| Caveats every number | Caveats once, then commits to a view |

The strategy analyst's commitment to a view is the part that
takes nerve. Hedging everything is the analyst's job, not the
strategist's.

## The discipline

### 1. Start with the question, not the data

Before opening anything, write down the **specific question** the
read-out exists to answer. One sentence. Examples:

- *"Did the spring campaign move spontaneous awareness among
  18–24s enough to justify the 60/40 split?"*
- *"Is share of search drift a leading indicator we should
  re-plan around, or a known seasonal pattern?"*
- *"Why did consideration fall in NW England specifically?"*

Without the question, the data tells you everything and nothing.

### 2. Form a hypothesis *before* you cut the data

Write down what you expect to find, and what would surprise you.
This protects against post-hoc storytelling — where any pattern
in the data gets a narrative attached after the fact.

```
Hypothesis:   [what we think is true]
We'd be wrong if:  [the pattern that would falsify it]
Surprise upside:   [a finding that would change the strategy]
Surprise downside: [a finding that would force a re-plan]
```

### 3. Triangulate before committing

Never make a strategic call on a single source. Cross-check
across at least two of:

| Source family | Examples |
|---|---|
| **Survey / tracker** | YouGov, Kantar, Ipsos, custom |
| **Search** | Google Trends, share of search, brand vs generic |
| **Social listening** | Brandwatch, Meltwater, Talkwalker |
| **Sales / panel** | Nielsen, Circana, NielsenIQ, internal |
| **Campaign output** | reach, frequency, attention |
| **Modelled effects** | MMM, attribution, lift studies |
| **Qual** | interviews, ethno, focus groups, panels |

If the tracker says one thing and the sales data says another,
say so explicitly. That contradiction is the most useful finding
in the document.

### 4. Separate fact, inference, recommendation

The most common deck failure is treating these three as
interchangeable. Tag every claim in the analysis:

```
FACT:           Awareness among 18–24s rose +4pts wave-on-wave.
INFERENCE:      The rise is consistent with the YouTube CTV
                heavy-up coinciding with the wave dates.
RECOMMENDATION: Maintain the CTV weight floor in the next
                planning cycle; re-test in wave 16 with a holdout.
```

Keep them visually distinct in the read-out. Stakeholders will
push back on inference — and they should be able to see *which
parts they are pushing back on*.

### 5. Distinguish significance from materiality

A move can be statistically significant and strategically
irrelevant, or strategically critical and statistically marginal.

- **Significance:** is the move likely real (p, CI, n)?
- **Materiality:** does the size of the move change a decision?

If a +2pt awareness shift is significant but doesn't move
share or sales, it's *information*, not a *decision input*. Say
so. Don't let significance carry weight it didn't earn.

### 6. Calibrate confidence honestly

Use a confidence register on every claim. Three levels are
enough:

| Register | When to use |
|---|---|
| **We know** | Two or more sources align; sample is robust; effect is material |
| **We think** | One source; logical inference; effect is plausible |
| **We're watching** | Early signal; sample weak; or single-source — flag for next wave |

A strategy doc with "we know X, we think Y, we're watching Z"
is honest and usable. One that says "X" three different ways
without registers is bluffing.

## Worked playbooks

### Brand tracker debrief

```
1. The headline (one sentence)
2. What's moved that matters — top 3 changes, with comparator
3. What's moved that doesn't matter (and why we're not worried)
4. Where the story is concentrated (audience cut, region, cohort)
5. Triangulation: how this lines up with search / social / sales
6. The implication for the strategy (one sentence)
7. The re-plan trigger we'd set for next wave
```

Default tracker checks to run every wave (note any that surprise):

- Spontaneous awareness vs prompted vs unaided salience
- Mental availability scores by category-entry point (CEP)
- Distinctive brand asset attribution
- Brand-linked recall vs ad-recall (the gap is meaningful)
- Consideration / preference funnel decay
- "Brand is for people like me" attribute
- Net Promoter / advocacy
- Category attribute ownership vs competitors

### MMM read-out

A model is a tool, not a verdict. The strategy analyst:

1. **Sense-checks the model against the world** — do channel
   elasticities look right vs prior MMMs / IPA databank ranges?
   Outliers need a story
2. **Reads the response curves**, not just the contribution chart
   — diminishing returns elbows tell you the most actionable
   thing in any MMM
3. **Flags the holdout** — what did the modeller leave out, and
   what does that mean for the read?
4. **Pulls the "if we'd spent £X more on Y…" counterfactual** —
   the optimiser's recommended reallocation is the live question
5. **States the residual uncertainty** — bayesian credible
   intervals or bootstrap ranges, not just point estimates
6. **Translates to plan** — what does this mean for the next
   media plan? (Hand to [[media-strategy]])

### Effectiveness paper (annual / IPA-style)

```
1. The brand's commercial trajectory
2. The campaign's role in it (the counterfactual)
3. The mechanisms — what shifted, in what order
4. The proof — short-term and long-term
5. The payback — net ROMI / net profit / LTV
6. What we learned that changes the next year's plan
```

The strongest effectiveness papers use **three independent
proofs**: a model (MMM), a measured experiment (geo / holdout /
incrementality), and a survey / tracker shift. Triangulation is
the credibility currency.

### Year-in-review POV

```
1. The bet we made (rebrief our own strategy in one sentence)
2. What the world did (the market context that shifted)
3. What we did about it
4. Where we won
5. Where we lost (be honest — losses earn credibility for wins)
6. What we now believe that we didn't 12 months ago
7. The two or three things that change next year's strategy
```

The "what we now believe" slide is the single hardest and most
valuable. It's where strategy actually compounds.

## Common analytic traps to call out

1. **Post-hoc story-fitting.** Every dataset has patterns; a
   narrative attached after the cut is suspect. Pre-register
   the hypothesis.
2. **Single-source confidence.** "YouGov says…" is one source.
   Hold it lightly until something else confirms.
3. **Confusing direction with magnitude.** "Awareness is up" —
   by how much, vs what?
4. **Treating MoM as the trend.** MoM is mostly noise. YoY,
   3-month rolling, or model-smoothed series tell the real
   story.
5. **Significance-by-eyeballing.** If a deck claims significance,
   it should report n, the test, and the p / CI.
6. **Confusing correlation with cause.** Spend up, awareness up,
   sales up — fine, but *did the spend cause it?* (Asks for
   a holdout, a lift test, or an MMM elasticity.)
7. **Survivorship bias in case studies.** Pointing at the
   campaigns that worked, ignoring the ones that didn't.
8. **Anchoring on the loudest stat.** The first stat presented
   sets the frame. Choose it deliberately.
9. **Over-segmenting until significance disappears.** Slicing by
   five cuts collapses cell sizes; report n every time you cut.
10. **Optimistic counterfactuals.** "Without us, sales would
    have fallen 20%" — only if you have evidence for the
    counterfactual.

## Output template — strategic read-out

Use this structure when delivering. It works for tracker, MMM,
campaign mid-flight, year-in-review.

```
STRATEGIC READ — [topic / wave / project]
Date / version

The question this read-out answers:
  [one sentence]

The headline:
  [one sentence — what we now believe]

We know:
  [2–3 bullets — facts with sources, confidence high]

We think:
  [2–3 bullets — inferences from triangulated data]

We're watching:
  [1–2 bullets — single-source or weak-sample signals]

Implication for the strategy:
  [2–3 sentences — what shifts, if anything]

Recommendation:
  [one sentence — the specific action]

Re-plan trigger:
  [the condition that would change the recommendation]

Caveats:
  [one line — the most important thing this read does not know]
```

## Tooling

- For pulling and cutting the data, use [[data-cut-headline-stats]]
  and the `xlsx` skill
- For visualising, hand off to [[vccp-media-design]]'s matplotlib
  config — note the no-red/green delta rule (up = teal-deep,
  down = mustard-dark)
- For statistical tests (t, chi-squared, bootstrapped CIs), a
  Python notebook with `scipy.stats` / `statsmodels` is usually
  the right tool; report the test and the p in the deck appendix
- For MMM, the in-house tool of record is the Market Mixed
  Modeller (see [`sebduffy-prog/MarketMixedModeller`](https://github.com/sebduffy-prog/MarketMixedModeller))
  — the same repo holds the VCCP brand modules used to render
  deliverables

## Handoffs

- Once the strategic read is written, hand to
  [[advertising-strategy-copy]] for prose polish
- Hand to [[deck-flow-structure]] to choose the narrative order
- Hand to [[advertising-strategy]] or [[media-strategy]] when the
  read implies a strategic change
- Hand to [[vccp-media-design]] for the visual layer
