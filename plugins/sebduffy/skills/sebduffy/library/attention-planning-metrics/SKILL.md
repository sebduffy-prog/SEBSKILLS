---
name: attention-planning-metrics
category: strategy
description: >-
  Plan and measure media with attention metrics — Adelaide AU, Lumen APM/aCPM,
  Amplified Intelligence active/passive seconds, TVision eyes-on-screen — and map
  each to funnel stage. Trigger when a brief asks to set attention KPIs, compare
  vendors, build attention floors/thresholds, convert CPM to cost-per-attentive-
  second, or defend "attention" in a media plan or QBR. Turns vendor jargon into
  a planable, comparable currency instead of hand-waving.
when_to_use:
  - A media plan or RFP asks for an attention KPI, attention floor, or attention benchmark
  - You must compare Adelaide, Lumen, Amplified Intelligence and TVision and pick one
  - Converting CPM into aCPM / cost-per-attentive-second to compare placements on value
  - Mapping attention thresholds to funnel objectives (awareness vs consideration vs conversion)
  - Writing an attention section for a strategy deck, QBR, or effectiveness case
  - A client says "we bought attention data — what do we actually do with it?"
when_not_to_use:
  - Pure audience sizing or profiling with survey data — use audience-insight or share-of-search
  - Full MMM / econometric attribution of sales to spend — use media-strategy plus an MMM tool
  - Creative pre-testing of an ad's stopping power (System1/Amplified creative) — use synthetic-audience-message-testing
  - General channel/budget planning with no attention layer — use media-strategy
keywords:
  - attention
  - adelaide
  - lumen
  - amplified intelligence
  - tvision
  - attention unit
  - acpm
  - attentive seconds
  - eyes on screen
  - active attention
  - passive attention
  - funnel
  - media planning
  - viewability
  - attention economy
similar_to:
  - media-strategy
  - audience-insight
  - effectiveness-case
  - share-of-search
inputs_needed: >-
  The brief's objective and funnel stage(s); which attention vendor(s) the client
  has (if any); a media plan or placement list with CPMs; and any vendor export
  (%viewed, view time, AU scores, active/passive seconds).
produces: >-
  An attention KPI framework mapped to the funnel, a vendor recommendation, and a
  ranked placement table on aCPM / cost-per-attentive-second with defensible floors.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Attention Planning & Metrics

Turn attention data into a **planable currency**: pick the right vendor, set
thresholds by funnel stage, and rank placements on attention value — not on
viewability or CPM alone. Grounded against the Adelaide 2026 Outcomes Guide,
Lumen, Amplified Intelligence, and TVision methodology.

## When to use

Reach for this whenever "attention" appears in a brief, plan, or QBR and someone
needs it to be *operational* — a number you can plan against and defend — rather
than a slide of buzzwords. It sits **between** audience strategy (who) and media
planning (where): it decides how much attention a plan should buy and how you
prove it landed.

## Prerequisites

- No API keys required for the framework and math. The Python helper is
  dependency-free (Python 3.9+, macOS system `python3` is fine).
- **Vendor data is client-supplied.** Adelaide (AU), Lumen, Amplified
  Intelligence (attentionPROVE), and TVision are paid platforms. You cannot pull
  live scores without the client's seat/exports — plan around what they give you.
- Attention metrics are **modelled or panel-based**, not census. Treat them as
  directional planning inputs, not deterministic truth.

## The four vendors at a glance

Different vendors measure different things. Do not average across them — they are
not the same currency.

| Vendor | Core metric | What it measures | Best for |
|---|---|---|---|
| **Adelaide** | **AU** (Attention Unit), 0–100 predictive score | Modelled likelihood a placement earns attention *and* drives outcomes; trained on full-funnel outcome data | Programmatic/digital planning + activation; setting quality floors |
| **Lumen** | **%viewed, avg view time, APM, aCPM** | Eye-tracking panel (webcam, 37 markets) → attentive seconds | Comparing placements/formats on cost-per-attentive-second value |
| **Amplified Intelligence** | **Active / passive / inactive attention seconds** (attentionPROVE) | Sub-second, impression-level active vs passive attention from ~100 markers | Distinguishing *active* attention (recall, purchase) from *passive* reach |
| **TVision** | **Eyes-on-screen** (2s+ threshold), co-viewing | Person-level, second-by-second computer-vision + ACR on TV/CTV | Linear TV & CTV attention and true co-viewing counts |

Key distinctions to hold onto:
- **AU is predictive** (a planning score you can target pre-bid); **Lumen/Amplified/TVision are measurement** (what actually happened). Adelaide is the one you can most easily *activate* against (custom bidding, PMPs, pre-bid targeting).
- **Active vs passive** (Amplified) is the single most useful conceptual split: active attention correlates with recall and purchase; passive attention reinforces awareness at scale.
- **TVision is the TV/CTV specialist** — do not use Lumen/Adelaide digital benchmarks to judge a CTV buy.

## Recipes

### Recipe 1 — Map attention to the funnel (the core deliverable)

Attention is not one KPI; the *type* and *threshold* change by objective. Use this
mapping as the spine of any attention plan:

| Funnel stage | Objective | Attention emphasis | Planable KPI |
|---|---|---|---|
| **Upper — Awareness** | Reach + memory encoding | Volume of attention; passive acceptable | High **%viewed / reach**; minimum attentive-seconds floor; Adelaide **AU floor** set low-but-present |
| **Mid — Consideration** | Engagement, message take-out | Rising **active** attention | Higher **avg view time** / **active seconds**; mid AU floor |
| **Lower — Conversion** | Action, response | **Active** attention concentrated on high-intent placements | Top-decile **AU**; highest active-seconds; tight aCPM |

Rule of thumb: **as you move down the funnel, raise the attention floor and shift
from passive to active.** Adelaide's 2026 Outcomes Guide reported attention-powered
campaigns averaging **+33% on upper-funnel KPIs and +53% on lower-funnel impact** —
lower funnel is where high attention pays back hardest, so guard it with the
strictest floors.

### Recipe 2 — Convert CPM into attention value (aCPM)

CPM tells you what a thousand *impressions* cost; it says nothing about attention.
Convert to **cost per thousand attentive seconds** so placements compare on value:

```
APM  = %viewed × avg_view_time(s) × 1000     # attentive seconds / 000 impressions
aCPM = CPM ÷ APM × 1000                       # cost per 1000 attentive seconds
```

Run the ranked comparison with the bundled helper:

```bash
cd skills/strategy/attention-planning-metrics
python3 scripts/attention_math.py
```

Edit the `demo` list (name, CPM, %viewed 0–1, avg view time in seconds) with the
client's Lumen export. A cheap-CPM placement with low %viewed and sub-second dwell
often loses to a "pricey" video unit once ranked on aCPM — that inversion is the
whole point, and the single most persuasive slide in an attention deck.

### Recipe 3 — Set defensible attention floors

1. Pull the vendor's benchmark for the channel/format (Adelaide publishes AU
   benchmarks by channel; Lumen publishes typical dwell of 1–2s per format).
2. Set the **floor at or above the channel median**, then tighten by funnel stage
   (Recipe 1). Adelaide calls these **KPI-specific AU floors** — floors vary by
   objective, not one blanket number.
3. Write the floor into the IO / PMP deal terms so it is enforced, not aspirational.
4. Activate: exclude sub-floor inventory pre-bid, and weight custom bidding toward
   above-floor placements.

### Recipe 4 — Structure the attention slide for a deck/QBR

Say, in order: (1) the objective and its funnel stage; (2) the one vendor +
metric you are holding the plan to, and why; (3) the floor and where it came from;
(4) the aCPM ranking table; (5) the outcome you expect (tie to the +33%/+53%
direction, not a fabricated precise number). Keep it to one metric per objective —
mixing vendors on one chart is the fastest way to lose the room.

## Verify

- Run `python3 scripts/attention_math.py` — it prints three placements ranked by
  aCPM (display MPU wins on value in the demo despite the lowest attentive volume).
- Sanity-check each KPI answers "planable and enforceable?": can you set it as a
  floor in a deal, and exclude inventory that misses it? If not, it is a reporting
  metric, not a planning KPI.
- Confirm you have **not** mixed vendors within one comparison table.

## Pitfalls

- **Attention ≠ viewability.** Viewability says the ad *could* be seen; attention
  says it *was* looked at. Never present viewability as attention.
- **Don't average vendors.** AU (0–100 predictive) and attentive-seconds (measured
  duration) are different units. Pick one currency per decision.
- **Passive attention is not free reach quality.** It reinforces awareness but
  underperforms active attention on recall/conversion — do not bank lower-funnel
  outcomes on passive numbers.
- **CTV needs TVision-grade data.** Judging a TV/CTV buy on digital-panel dwell
  understates co-viewing and eyes-on-screen. Match the vendor to the channel.
- **Modelled, not census.** AU and panel metrics are directional. Present ranges
  and floors, not false-precision single figures.
- **More attention isn't always the goal.** Upper-funnel reach can rationally
  accept lower attention at scale; over-indexing on active-attention floors there
  starves reach. Optimise attention *to the objective*, not to the maximum.

## Sources

- Adelaide 2026 Outcomes Guide — adelaidemetrics.com/blog/adelaide-releases-2026-outcomes-guide
- Lumen attention metrics (%viewed, APM, aCPM) — lumen-research.com
- Amplified Intelligence attentionPROVE (active/passive seconds) — amplifiedintelligence.com.au
- TVision eyes-on-screen methodology — tvisioninsights.com/resources/tvision-methodology-overview
