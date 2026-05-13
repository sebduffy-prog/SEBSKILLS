---
name: data-cut-headline-stats
description: |
  Cut and interrogate raw data (CSV, XLSX, brand tracker exports,
  media plan returns, campaign performance, sales data, social
  listening, search trends, panel data, segmentation surveys) and
  pull out headline statistics suitable for a client-facing
  strategy deck, board paper, planner POV, or new-business
  pitch. The skill knows what makes a stat a headline — size of
  effect, direction of travel vs benchmark, segment outperformance,
  surprise relative to prior — versus what is just noise. Trigger
  on phrases like "cut this data", "pull out the headlines",
  "what's the story in this data", "stats for the deck",
  "interrogate this tracker", "what stands out", "summarise this
  for the planner", "find the headline stat", "anything punchy in
  here", "make this client-ready", "give me the top numbers",
  "data audit", "first cut", "stat-bank", "killer stats". Also
  trigger when the user drops a spreadsheet or CSV and asks any
  variant of "what do you see" or "anything interesting". Pairs
  with [[strategy-analyst]] for interpretation, [[advertising-strategy]]
  /[[media-strategy]] for downstream use, and [[vccp-media-design]]
  for presentation styling.
---

# Data cut → headline stats

Take raw data and pull out the **three to seven stats** a strategist
or planner would actually put on a slide. Most "data summaries"
fail because they tell the reader *what's in the data* instead of
*what's worth knowing*. This skill is biased toward the latter.

## When to use

- A client has dropped a brand tracker / panel export / campaign
  return / sales file and the planner needs ammunition
- New-business pitch and you have one afternoon to find the punchy
  numbers
- Writing the "context" section of a strategy doc
- Annotating a chart for a deck
- Pre-reading for a workshop — what's worth flagging up-front
- Any moment where the user says "give me the stats" and means
  "the *interesting* stats"

**Don't use this skill** when the user wants a full statistical
analysis (regression, MMM, causal inference) — use a statistical
workflow instead. Headline stats are descriptive and editorial.

## What makes a stat a *headline* stat

Score every candidate stat against these. Anything that doesn't
hit at least two is filler.

| Signal | What to look for |
|---|---|
| **Size** | Is the effect large in absolute and relative terms? "+0.3pts" is rarely a headline. "+11 points vs category average" is. |
| **Direction** | Is it moving against trend, or with a trend the client doesn't yet know about? |
| **Surprise** | Does it contradict the brief, the prior, or what the client believes about themselves? |
| **Concentration** | Is the effect coming from one segment, region, SKU, or daypart? "70% of growth came from 25–34 ABC1 women in London" is a stat. "Growth across the board" is not. |
| **Comparability** | Is it benchmarked? Stats without a comparator are not headlines, they are numbers. Use category average, prior period YoY, competitor, or an external norm. |
| **Single sentence** | If the stat needs two clauses to explain *what it means*, you haven't cut it tightly enough. |

## The process

### 1. Read the brief before the data

Before opening the file, write down (in one line each):

- What is the client trying to know?
- What is the strategic question on the table?
- What would a *useful* answer look like vs an unsurprising one?

Stats are only headlines relative to a question. Without the
question, you are just listing columns.

### 2. Profile the data fast

For any tabular file:

```python
import pandas as pd
df = pd.read_excel(path)          # or read_csv
print(df.shape)
print(df.dtypes)
print(df.head(20))
print(df.describe(include="all"))
print({c: df[c].nunique() for c in df.columns})  # dimensionality
print(df.isna().mean().sort_values(ascending=False).head())  # missingness
```

For brand tracker exports specifically — the columns are usually
`wave / period`, `brand`, `metric`, `audience`, `value`. Pivot
into a wide format keyed on wave so changes over time are visible
at a glance.

### 3. Define the cuts

Don't slice everything by everything. Pick **2–4 axes** the
strategic question depends on. Typical strategist cuts:

- **Audience** — demographic, attitudinal, behavioural segment
- **Geography** — region, city, market
- **Time** — pre/post launch, YoY, period over period, day-part
- **Brand** — vs own historic baseline, vs each competitor, vs
  category average
- **Funnel stage** — awareness → consideration → preference →
  purchase → loyalty
- **Channel / touchpoint** — TV, social, search, OOH, in-store
- **Product / SKU** — hero line vs portfolio
- **Creative / campaign** — pre/post, treatment vs control

### 4. For each cut, compute four things

```
absolute value  →  what is the number
delta           →  vs same audience prior period
share           →  this segment's share of total
index           →  this segment vs the all-respondent base = 100
```

The `index` view is what turns "30% of women aged 25–34 are aware"
(unremarkable) into "+18 vs the audience average" (a headline).

### 5. Rank candidates by editorial weight

For every candidate stat, ask:

1. **Does it answer the strategic question, or change it?**
2. **Is it true at sample-size?** (n<100, treat as anecdote, not
   stat — flag it explicitly in the caveat line)
3. **Will a CMO repeat this number out loud?** If the sentence
   doesn't land in one breath, rework it.

Cull to the top **3–7**. Resist the urge to keep more. A deck
with twelve "headline" stats has zero headlines.

### 6. Write each stat as a one-liner

Template:

```
[NUMBER] [UNIT] of [WHO / WHAT], [COMPARED TO WHAT], [SO WHAT].
```

Examples:

- **"45% of category buyers can't name a brand they prefer — 11
  points more than three years ago, and the highest indifference
  score in any FMCG category we track."**
- **"Search interest for [brand] grew 38% YoY, but only on mobile
  — desktop searches fell 6%. The audience is now researching
  on-the-go."**
- **"Two regions (NW and Midlands) drove 62% of unit growth in
  Q3, while London — historically the strongest market —
  contributed 4%."**

Every stat carries the comparator inside the sentence. The
"so what" is the part most planners leave off; it's the part the
client cares about.

### 7. Caveat honestly, briefly

Below each stat, one line:

```
Source: [provider], [field period], n=[sample], [audience definition].
Caveat: [the one thing that could undermine this read].
```

A caveat doesn't kill a stat; it makes it trustworthy. Stats
without caveats die in the Q&A.

## Output format

When delivering, structure as:

```
HEADLINE STATS — [topic / client / brief]
Source files: [list]
Strategic question: [one line]

1. [One-line stat]
   Source / caveat: [one line]
   Why it matters: [one line — link to the strategic question]

2. [One-line stat]
   …
```

Then a one-paragraph **summary read** that turns the stats into a
narrative direction (one or two sentences — not a recommendation).

## Common mistakes to avoid

1. **Reporting averages without distribution.** "Average awareness
   is 62%" hides the segment that drives the strategy.
2. **Y-axis manipulation.** Quoting "growth of 200%" off a base
   of three is not a headline, it's a number trick.
3. **Stat-stacking without a story.** Five numbers in a row with
   no through-line is a data dump, not a cut.
4. **Indices > 1000 with no caveat.** Almost always small sample.
   Treat with suspicion, flag the n.
5. **Burying the comparator.** "Awareness rose to 47%" is not a
   headline. "Awareness rose 14 points, the largest jump in the
   category" is.
6. **Mixing data sources without saying so.** If the awareness
   number is from YouGov and the consideration number is from a
   custom panel, say so — readers will ask.
7. **Confusing share with growth.** "We grew share to 12%" can
   mean the category shrank. State both.
8. **Quoting a benchmark you didn't check.** Category averages
   change. Don't reuse last year's benchmark in this year's stat
   without re-pulling it.

## Tooling notes

- For XLSX/CSV work, lean on the `xlsx` and `pdf` skills for I/O
- For visualisation in a VCCP deck, hand off to `vccp-media-design`
  — its matplotlib config in `vccp_charts.py` is the right base
- For larger panels (>1M rows), use `pandas` chunked reads or
  `duckdb` to query the file directly
- For brand tracker dashboards (Kantar, YouGov, Ipsos, Savanta),
  the API exports tend to be wide; pivot to long for cut-friendly
  manipulation, pivot back to wide for client view

## Quick checklist before declaring "done"

- [ ] Each stat answers (or reshapes) the strategic question
- [ ] Each stat carries a comparator inside the sentence
- [ ] Each stat has a source + sample + caveat line
- [ ] Top 3–7 only — no padding
- [ ] One-paragraph through-line at the end
- [ ] No stat reads as "interesting but irrelevant"
- [ ] Numbers checked against the source file (typos kill credibility)
