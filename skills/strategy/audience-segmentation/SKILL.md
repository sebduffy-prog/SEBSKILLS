---
name: audience-segmentation
description: |
  Build, name, profile, and *use* audience segmentations —
  behavioural, attitudinal, need-state, value-based, and
  occasion-based. Covers both creating segmentations from
  survey / panel / first-party data (k-means, latent class /
  finite mixture, hierarchical, RFM, decision trees) and the
  much-more-common job of *interpreting and deploying* a
  segmentation a client already owns. Use when an audience needs
  to be split into useful sub-groups for strategy, planning or
  media activation. Trigger on phrases like "build a
  segmentation", "rebuild this segmentation", "name these
  segments", "profile the segments", "size the segments",
  "find the bullseye", "who's the priority audience", "k-means",
  "latent class", "cluster analysis", "RFM", "needs-based
  segmentation", "attitudinal segmentation", "behavioural
  segmentation", "occasions / category-entry points", "CEPs",
  "Persona". Trigger when the user has a segmentation deck
  they can't make sense of, or wants to *use* an existing
  segmentation in a brief. Pairs with [[audience-insight]] (one
  insight per useful segment), [[data-analyst]] (the modelling),
  [[raw-data-research]] (data prep), and [[advertising-strategy]]
  (deploying the chosen segment).
---

# Audience segmentation

A segmentation is only as good as the **decisions it changes**.
The most common segmentation failure is technical-success-
strategic-uselessness: six statistically distinct clusters that
nobody can name, brief, target, or remember.

This skill is built for both halves of the job:

- **Build / rebuild** a segmentation from data
- **Interpret and deploy** a segmentation the client already owns

The second job is more common, and more often done badly.

## When to use

- A client wants their audience cut into useful groups
- An existing segmentation has landed and the planner needs to
  pick a target
- A creative team needs a *person*, not five percentages
- A pitch needs an audience POV that isn't a copy-paste from
  TGI
- A new campaign needs a primary, secondary, and *not* audience

**Don't use this skill** for: pure persona writing without
data behind it (that's storytelling), or for one-off audience
portraits where one audience will do (use [[advertising-strategy]]
direct).

## Five kinds of segmentation — pick deliberately

| Type | What it splits on | Best for |
|---|---|---|
| **Behavioural** | What they do — purchases, visits, frequency, recency, basket | Activation, CRM, retail; most actionable |
| **Attitudinal** | What they believe / feel / value | Brand-building, positioning, comms |
| **Need-state / occasion** | What they're trying to do *in this moment* (Jobs-to-be-Done, Category-Entry Points) | FMCG / QSR / service categories with multiple use occasions |
| **Demographic / firmographic** | Age, life-stage, role, company-size | B2B; weak for advertising on its own |
| **Value-based / RFM** | Spend / loyalty / margin contribution | DR / DTC / loyalty programmes |

A good segmentation is usually **hybrid** — attitudinal +
behavioural backbone, demographic profile *over* the top so the
media team can buy it.

**Most planner-useful default in 2026:** a needs / CEP backbone
profiled with attitudinal modifiers and an addressability layer
for media (see Ehrenberg-Bass on Category Entry Points;
Christensen on JTBD). It moves the conversation from "who is
the buyer" to "what is the buyer trying to do".

## Building a segmentation (when you have to)

### Step 1 — Define the purpose

Write one sentence:

```
This segmentation exists to help us [decision] by separating
[audience] into groups that differ on [the dimension(s) we
will act on].
```

If "the dimension we will act on" is "all of them", the
segmentation will fail. Pick.

### Step 2 — Choose the dimensionality

A 7-segment model is harder to deploy than a 3-segment one.
Optimum is usually **3–5 segments**. Anything beyond 6 is
academic — the agency can't brief it, the client can't
remember it, the media team can't buy it.

### Step 3 — Build the variables list

Variables go into the model only if **all three** of:

- They are theoretically linked to the decision the
  segmentation is for
- They are measurable (in the data we have, or can plausibly
  acquire)
- They are *not* downstream of the segments themselves
  (avoid circular variables)

Strip out variables that load entirely on demographics — they
will swamp the signal.

### Step 4 — Pick a method

| Method | When to use |
|---|---|
| **K-means / k-medoids** | Continuous variables, large n, fast iteration, easy to explain. Default for first-pass clustering. |
| **Latent Class / Finite Mixture** | Mostly categorical / Likert variables; you want probabilistic membership, fit statistics (BIC, entropy), and academic defensibility. Default for attitudinal segmentations. |
| **Hierarchical (Ward)** | Small n; you want a dendrogram to choose k visually |
| **HDBSCAN / Density-based** | When clusters have varied density and some respondents should be "noise" rather than forced into a cluster |
| **Decision tree (CHAID / CART)** on a target variable | When the segmentation must predict a known outcome (purchase, churn) — produces interpretable splits |
| **Self-organising maps / archetypal analysis** | When you want extreme exemplars, not centroids — useful for archetype work |

For most attitudinal work: **latent class with 3–5 classes,
informed by BIC + interpretability + segment size balance**.

### Step 5 — Decide on k

Don't pick k by elbow plot alone. Combine:

1. **Statistical** — gap statistic, BIC, silhouette, AIC
2. **Balance** — no segment < 8% (too small to find / buy),
   no segment > 50% (the segmentation collapsed)
3. **Interpretability** — can you name each segment in 3 words?
   If not, you're over-fit
4. **Stability** — re-run on a random 80% subsample; how many
   respondents change cluster? <15% is good

Pick a k that wins on **at least three of the four**.

### Step 6 — Profile every segment

For every segment, build:

```
- Size (% of universe, n)
- Behavioural signature (top 5 over-indexed behaviours)
- Attitudinal signature (top 5 over-indexed attitudes)
- Demographic profile (age, gender, region, life-stage,
  income — for the media plan)
- Category context (penetration, frequency, share of category
  spend)
- Brand context (current relationship to client + competitors)
- A representative quote (verbatim from the survey open-end
  or a paired qual session)
```

The "representative quote" is the difference between a
segmentation report and a usable one.

### Step 7 — Name the segments

Naming rules:

- **Three words max.** *"Anxious Aspirers"* — not *"Time-Pressed
  Aspirational Mid-Income Households With Children"*.
- **Active verb or distinctive adjective + noun** — describing
  what they *do* or *believe*, not their demographics
- **Memorable from first hearing.** Test: read the names out
  loud to someone who's never seen the deck. Can they repeat
  them an hour later?
- **No client-team in-jokes.** "The Karens" might be funny in
  the workshop and offensive in the deck.
- **Stable** — once named, the names don't change between
  decks. Inconsistency makes the segmentation seem unstable.

### Step 8 — Address each segment

For each, write down:

- **Where they are** — channels, dayparts, environments where
  they over-index (TGI / Touchpoints / GWI / first-party
  matches)
- **Buyable proxy** — the spec a media team can actually buy
  (custom audience, lookalike, third-party seg)
- **Friction with the brief** — what makes this segment hard /
  expensive / risky to reach
- **Activation cost-per-reach** — order of magnitude

A segment that can't be addressed is interesting; one that can
is useful.

## Using an existing segmentation (the more common job)

When a client hands over a segmentation, run this audit:

### Audit step 1 — Provenance

Who built it, when, on what data, with what method? A four-year-
old segmentation built on pre-pandemic behaviour is suspect.

### Audit step 2 — Decision history

What decisions has it actually been used for? Segmentations
that have never driven a decision are usually un-deployable.

### Audit step 3 — Memorability check

Can the marketing team name the segments without the cheat
sheet? If not, the segmentation will not live outside the deck.

### Audit step 4 — Behavioural validation

Pull recent first-party data (CRM, sales, app, web). Does the
segment membership predict actual behaviour today? If not, the
segmentation is decorative.

### Audit step 5 — Buyability

For each segment, what does the media team actually buy? If
the answer is "a generic ABC1 25–54 buy", the segmentation is
not deployed.

### Audit step 6 — Re-pick the bullseye

Even if the segmentation is intact, the *primary segment* may
need re-choosing for this brief. Use the **size × growth
potential × strategic fit** triangle:

```
Size:               How many of them are there?
Growth potential:   How under-indexed is the brand vs the segment's
                    category share? (Big gap = big upside.)
Strategic fit:      Can the brand credibly serve this need-state?
```

Pick the segment with the largest gap × largest credible fit.
*Not* the largest segment.

## Output template

Whether you built it or interpreted an existing one:

```
SEGMENTATION — [audience / brief]
Date / version
Source: [study, n, fieldwork dates, method]

The segments (size, share of category spend)
1. [Name] — NN%, £NN value
2. [Name] — NN%, £NN value
3. …

For each segment, one card:
  WHO   — 2 lines, demographics + life-stage
  DOES  — 3 over-indexed behaviours, with evidence
  FEELS — 2 over-indexed attitudes, with verbatim
  CONTEXT — where they meet the category, where they meet us
  WHERE — addressable channels / buys
  VERBATIM — a quote that makes them recognisable

Recommended primary audience: [name]
Recommended secondary audience: [name]
"Not for" audience: [name]
  Reasoning: size × growth × fit
  Insight (the human truth): [from [[audience-insight]]]
  Sample size / confidence: [WE KNOW / WE THINK / WE'RE WATCHING]
```

## Common mistakes to avoid

1. **Statistically clean, strategically useless.** Six clusters
   nobody can name. Fewer, sharper segments win.
2. **Demographic-only segmentations.** *"ABC1 25–54"* is a
   media-buyable spec, not a strategic segmentation.
3. **Bullseye = biggest segment.** The biggest segment is often
   the brand's mass already, not its growth.
4. **Personalities ≠ segments.** "The Adventurer", "The
   Worrier" — without underlying data, this is novel-writing.
5. **No "not for".** Strategy is what you say no to. A segment
   you've ruled out is part of the strategy.
6. **One segment, one campaign.** Most brands need a primary
   audience + a defending audience + the existing base.
7. **Segments without a verbatim.** Strategy without a verbatim
   becomes brand-on description.
8. **Re-segmenting every brief.** Inconsistent segmentation
   erodes institutional memory. Tweak only when the data has
   moved.
9. **Treating a segmentation as the strategy.** It's an input,
   not an output.
10. **Ignoring buyability.** A segment the media team can't
    target is, in practice, a description.

## Useful frameworks to keep handy

- **Category-Entry Points (Romaniuk / Ehrenberg-Bass)** — split
  on *moments of demand* rather than *types of person*
- **Jobs-to-be-Done (Christensen / Wunker)** — split on what
  the audience hired the category to do
- **VALS / TGI psychographic typologies** — useful as a
  cross-reference, not as a deployable segmentation
- **RFM (Recency, Frequency, Monetary)** — for CRM / DR /
  loyalty splits on first-party data
- **CDJ / NPS by stage** — when the question is *where in the
  funnel* people are, more than *who* they are

## Tooling

- Python: `scikit-learn` (k-means, GaussianMixture), `pomegranate`
  / `pyLCA` (latent class), `hdbscan`, `statsmodels`
- R: `poLCA` (canonical latent class), `flexmix`, `cluster`
- For very high-dim (>100 vars), pre-reduce with `factor analysis`
  / PCA, then cluster on factor scores
- Visualise with PCA + cluster colouring; profile with parallel
  coordinates or radial plots
- For deck output, hand to [[vccp-media-design]] (radial /
  parallel plots ok; pie charts banned)

## Handoffs

- For the *insight* inside each segment, use
  [[audience-insight]]
- For the *strategy* deploying the chosen segment, use
  [[advertising-strategy]]
- For media planning around the addressable spec, use
  [[media-strategy]]
- For the data prep, [[raw-data-research]]; for the modelling,
  [[data-analyst]]
- For the deck flow, [[deck-flow-structure]]
