---
name: brand-health-tracker-design
category: strategy
description: >
  Design an ONGOING brand health tracker, not a one-off audit: pick the
  metric spine (funnel + equity pillars), set wave cadence and base sizes,
  write the questionnaire, define significance rules so noise isn't reported
  as movement, and build the wave-on-wave readout dashboard. Grounds the
  metric set against Kantar BrandZ / MDS (Meaningful, Different, Salient ->
  Demand/Pricing/Future Power) and BAV (Differentiation, Relevance, Esteem,
  Knowledge -> Brand Strength vs Brand Stature), plus a classic purchase
  funnel (awareness -> familiarity -> consideration -> preference -> usage ->
  advocacy). Ships a two-proportion z-test helper so every wave delta is
  labelled significant / directional / noise. Use when the brief is "set up a
  brand tracker", "continuous brand health", "brand funnel over time", "how do
  we measure the brand each quarter", "wave-on-wave", "is this move real",
  "tracking study design", "KPI dashboard for the brand". Pairs with
  brand-audit (the point-in-time cousin) and share-of-search (the free
  always-on proxy).
when_to_use:
  - A client or CMO wants a continuous read on brand health, not a single audit
  - You must decide which metrics to track, at what cadence, and on what base size
  - Setting up wave-on-wave reporting and need rules for what counts as a real move
  - Building or specifying a brand-tracker dashboard / KPI scorecard for the agency
  - Deciding between (or blending) a funnel view, BrandZ/MDS, and BAV pillars
  - Auditing an existing tracker that reports every wobble as if it were a trend
when_not_to_use:
  - You need a one-time current-state diagnosis of comms and equity -> use brand-audit
  - You only want a free, always-on demand proxy with no survey -> use share-of-search
  - You are sizing category entry points / mental availability specifically -> use category-entry-points-mental-availability
  - You need audience profiling or segmentation, not brand KPIs -> use audience-insight or audience-segmentation
keywords:
  - brand tracker
  - brand health
  - brand equity
  - purchase funnel
  - wave analysis
  - significance testing
  - brandz
  - kantar mds
  - bav
  - meaningful different salient
  - brand strength
  - tracking study
  - kpi dashboard
  - base size
  - net promoter
similar_to:
  - brand-audit
  - share-of-search
  - competitive-comms-audit
  - attention-planning-metrics
  - effectiveness-case
inputs_needed: >
  Brand + key competitors to track; the business question (defend / grow /
  reposition); any existing tracker data or waves; target cadence and rough
  budget; whether a survey vendor (Kantar, YouGov, Savanta, panel) is already
  in place or the tracker is being designed from scratch.
produces: >
  A tracker design doc: metric spine mapped to a framework, questionnaire
  blueprint, cadence + base-size plan, significance/reporting rules, and a
  wave-on-wave scorecard spec -- plus per-metric significance verdicts from
  the z-test helper.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Brand Health Tracker Design

Design an **ongoing** measurement system for a brand. A tracker differs from an
audit in one word: **time**. An audit is a photograph; a tracker is the heart
monitor. The whole value is in reading *movement* correctly wave after wave, so
the two hardest jobs are (1) picking a small, stable metric spine you will not
change, and (2) never reporting sampling noise as a trend.

## When to use

Use this when the deliverable is a repeating measurement, not a single verdict.
If someone says "brand audit", "one-off health check", or "current state" -> that
is `brand-audit`. If they say "each quarter", "continuous", "wave", "over time",
"dashboard", "is the move real" -> you are here.

## Prerequisites

- No paid tools required to *design* a tracker. To *field* one you need a survey
  vendor and sample (Kantar, YouGov, Savanta, Attest, or a panel via a research
  partner). Note honestly to the client that fielding costs money per wave.
- `python3` (stock macOS 3.9 is fine) for `scripts/wave_sig.py` -- no pip installs.
- BrandZ/MDS and BAV are proprietary *frameworks* you can design toward; you do
  not need a Kantar or VML licence to borrow the *thinking* (funnel + emotional
  equity + salience). Only Kantar's actual BrandZ scores/valuations are licensed.
- `share-of-search` (Google Trends) gives a free, always-on demand proxy to run
  *alongside* the survey tracker -- cheap early-warning between waves.

## Recipe: design the tracker in 6 steps

### 1. Anchor to the business question
One of three, and it changes what you over-index on:
- **Defend** a leader -> salience, mental availability, distinctiveness, penetration.
- **Grow** a challenger -> awareness -> consideration conversion, differentiation, meaning.
- **Reposition** -> attribute ownership, the specific attributes you want to shift.

### 2. Pick the metric spine (keep it small: ~10-15 tracked metrics)
Blend three lenses. Do not track all of everything -- pick the layer that fits.

**A. The purchase funnel (the universal spine):**
awareness (spontaneous + prompted) -> familiarity -> consideration ->
preference -> trial/usage -> repeat/loyalty -> advocacy (NPS). Track
*conversion rates between steps*, not just the levels -- the leak in the funnel
is the story, not the top number.

**B. Kantar BrandZ / MDS (the equity layer):** the three predisposition
dimensions -- **Meaningful** (meets functional + emotional needs), **Different**
(sets trends / distinctive), **Salient** (comes to mind at the moment of need)
-- which drive the three outcome "powers": **Demand Power** (volume), **Pricing
Power** (premium), **Future Power** (growth potential). Great for justifying
price premium and predicting share.

**C. BAV (the leading-vs-lagging layer):** four pillars --
**Differentiation** and **Relevance** combine into **Brand Strength** (a
*leading* indicator of future value); **Esteem** and **Knowledge** combine into
**Brand Stature** (a *current/lagging* readout). Watching Strength move ahead of
Stature is the early signal of a brand on the way up (or down).

Then add **category-specific attribute batteries** (5-10 image statements you
want to own) and one or two **behavioural** metrics (past-4-week usage, switching).

### 3. Set cadence and base size (this is where most trackers fail)
- **Cadence:** continuous (always-on, rolling) for big spenders; quarterly for
  most; wave-based around campaign bursts (pre / mid / post) for the budget-light.
  Continuous rolling data lets you read a 3-wave moving average and cut noise.
- **Base size:** aim for **n>=300** per brand per wave for total sample; **n>=150**
  is the floor for a subgroup cut you intend to report. Below that, moves have to
  be huge to be significant (see step 5 / the helper).
- **Consistency is sacred:** same questions, same order, same sample frame,
  same weighting every wave. Change one thing and you have broken the trend line.
  Keep a locked "tracking core" and quarantine any experimental questions.

### 4. Write the questionnaire blueprint
- Lead with **spontaneous/unaided** awareness *before* you show any brand list
  (prompting contaminates unaided recall -- order matters).
- Randomise brand and attribute order; hold the *randomisation scheme* constant.
- Keep scales identical across waves (e.g. consistent 5- or 7-point, or a
  consistent binary "associate / don't associate"). Never switch scale mid-tracker.
- Capture the funnel as nested filters so you can compute step conversion.
- Add distinctive-asset prompts (logo/colour/character/sonic recognition) if
  distinctiveness is a KPI.

### 5. Define significance & reporting rules BEFORE you see data
The cardinal sin of trackers is calling a random wobble a "recovery". Pre-commit:
- Every wave delta gets tested. A two-proportion z-test (95% -> report; 90% ->
  flag as directional; else -> noise) — run it with the helper below.
- Prefer **3-wave moving averages** or wave-vs-same-wave-last-year for seasonal
  categories over raw wave-to-wave.
- Apply a **design effect** for weighted/panel data (effective n = n / deff;
  typical deff 1.2-2.0) so you don't overstate certainty.
- Report the *conversion leaks* and the significant movers -- resist a wall of 40
  numbers. A good readout is 1 headline + 3-5 significant, decision-relevant moves.

Run the test:
```bash
# did prompted awareness really move 42% -> 47% at n~500?
python3 scripts/wave_sig.py --p1 0.42 --n1 500 --p2 0.47 --n2 512
#   -> z=+1.60  p=0.1096  NOT SIGNIFICANT (do not report as a change)

# weighted panel data: apply a design effect
python3 scripts/wave_sig.py --x1 210 --n1 500 --x2 240 --n2 512 --deff 1.5
```
The +5pt example is deliberately sobering: at n=500 a 5-point jump is *not*
significant. This is the single most useful gut-check in tracker readouts.

### 6. Spec the wave-on-wave scorecard
- One row per KPI; columns = latest wave, prior wave, YoY, arrow + sig-flag.
- Colour = significance, not raw direction (grey = noise even if the arrow is up).
- A funnel visual (levels + conversion %) and a Strength-vs-Stature or MDS quadrant.
- Always show competitor lines on the same axis -- brand health is relative.
- If you are building the dashboard as a deck or web page, hand off to `pptx`,
  `dataviz`, or `frontend-design`; this skill defines *what* goes on it.

## Verify

- Metric spine maps cleanly to ONE anchored business question (step 1).
- Every reported "move" has passed `wave_sig.py` at >=90%; noise is greyed out.
- Base sizes are stated on every cut; no reported subgroup under n=150.
- The tracking core is documented as locked -- anyone can confirm wave-to-wave
  comparability.
- Competitors appear on the same charts; the readout is relative, not absolute.
- Smoke-test the helper: `python3 scripts/wave_sig.py --p1 .42 --n1 500 --p2 .47 --n2 512`.

## Pitfalls

- **Reporting noise as trend.** The number-one failure. n=500 needs ~6-7 points
  of movement to be significant. Test before you narrate. Use moving averages.
- **Changing the questionnaire.** Any wording/order/scale change breaks the trend;
  you cannot compare across the break. Lock the core; version experimental items.
- **Too many KPIs.** A 40-metric tracker gets ignored. A tight spine of ~12 that
  ties to the business question gets acted on.
- **Absolute, not relative.** A rising number in a rising category can still be
  losing share. Always track competitors on the same base.
- **Ignoring the design effect.** Weighted online panels are not simple random
  samples; without a deff you will over-declare significance. Default to 1.5 if unsure.
- **No leading indicator.** Awareness/esteem are lagging. Pair with BAV Brand
  Strength, MDS "Different", distinctiveness, and share-of-search for early warning.
- **Confusing this with an audit.** If it does not repeat on a cadence, it is a
  `brand-audit`, not a tracker.
