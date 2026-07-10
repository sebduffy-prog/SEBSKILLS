---
name: retail-media-network-strategy
category: strategy
description: >
  Build a retail media network (RMN) plan: split budget across Amazon Ads,
  Walmart Connect, Kroger, Instacart and others by marginal incremental return;
  map on-site, off-site (DSP/CTV) and in-store inventory to funnel stages; and
  stand up clean-room measurement (Amazon Marketing Cloud, Walmart Luminate/
  Scintilla) for closed-loop, incrementality-based proof. Use for RMN budget
  allocation, commerce-media planning, iROAS/incrementality measurement design,
  and multi-retailer trade/shopper-media recommendations.
when_to_use:
  - Splitting a shopper/commerce-media budget across two or more retail media networks
  - Deciding on-site search vs off-site DSP/CTV vs in-store screen inventory by funnel stage
  - Designing closed-loop measurement with a retailer clean room (AMC, Luminate/Scintilla)
  - Setting iROAS / incrementality targets instead of vanity platform ROAS
  - Reallocating spend when one RMN saturates and marginal returns fall
  - Writing an RMN section of a media plan or client commerce-media recommendation
when_not_to_use:
  - Generic paid-media channel planning across TV/social/search — use media-strategy
  - Pure Amazon Sponsored Products bid/keyword tactics with no cross-network view — that is a platform PPC task, not this strategy skill
  - Audience sizing or segment definition — use audience-segmentation or audience-insight
  - Marketing-mix / econometric modelling build — that is an MMM engineering task, not this planning heuristic
keywords:
  - retail media
  - rmn
  - amazon ads
  - walmart connect
  - amazon marketing cloud
  - clean room
  - iroas
  - incrementality
  - commerce media
  - shopper marketing
  - onsite offsite
  - in-store retail media
  - closed-loop measurement
  - budget allocation
  - luminate
  - dsp
similar_to:
  - media-strategy
  - advertising-strategy
  - audience-segmentation
inputs_needed: >
  Total commerce-media budget and flight; list of in-scope retailers/RMNs;
  campaign objective per retailer (awareness vs consideration vs conversion);
  any historical ROAS/iROAS or MMM curves; retailer clean-room access
  (AMC / Luminate seats) if measurement is in scope.
produces: >
  A budget allocation table across RMNs by marginal incremental return, an
  inventory-to-funnel map (on-site / off-site / in-store), a clean-room
  measurement plan with iROAS and incrementality KPIs, and a reallocation trigger.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Retail Media Network Strategy

Plan and measure across **retail media networks** (RMNs) — the ad businesses that
sit on retailers' first-party purchase data. The three moves that matter: allocate
budget by *marginal incremental return* (not headline ROAS), map inventory to funnel
stage, and prove it with a retailer **clean room**. `media-strategy` covers the wider
channel mix; this skill is the commerce-media specialist.

## When to use

Reach for this when a brief involves splitting money across Amazon Ads, Walmart
Connect, Kroger Precision Marketing, Instacart, Target Roundel, Tesco/dunnhumby or
similar — or when someone asks "what's our real return, not the platform's inflated
ROAS?" See `when_not_to_use` for the platform-tactics and MMM boundaries.

## Prerequisites (be honest about these)

- **No API keys are required to *plan*.** The allocation helper is pure `python3`
  (stdlib only, works on the system 3.9). You supply the response curves.
- **Activation and measurement need real accounts** you must have already:
  - Amazon: an Advertising console + DSP seat; **Amazon Marketing Cloud (AMC)** for
    the clean room. As of Sept 2025 AMC is free to all Sponsored Ads advertisers and
    runs on AWS Clean Rooms; the purchase-signal lookback now reaches up to 5 years
    and ad-traffic lookback is 25 months.
  - Walmart: **Walmart Connect** for on-site, **Walmart DSP** (built with The Trade
    Desk) for off-site/CTV, and **Walmart Luminate** (rebranding to *Scintilla*) as
    the insights/clean-room layer with multi-touch attribution across on-site,
    off-site and in-club.
  - Others use LiveRamp/Habu or AWS/Snowflake clean rooms (e.g. Kroger via 84.51°).
- **Curves are your responsibility.** The optimiser is only as good as the `ceiling`
  and `halfpoint` you feed it — derive them from prior iROAS tests or an MMM, never
  from a platform's self-reported ROAS.

## Recipe 1 — Allocate budget across RMNs by marginal return

Retail media obeys diminishing returns: the 10th £1k on Amazon search does far less
than the 1st. The right split equalises the *marginal* incremental return across
networks (the equimarginal principle), subject to min commitments and saturation caps.

1. For each RMN, estimate a saturation curve: `ceiling` = max incremental sales at
   that funnel role, `halfpoint` = spend reaching ~63% of ceiling. Add optional
   `min`/`max` caps (contractual minimums, inventory ceilings).
2. Write the plan as JSON and run the helper:

```bash
cat > networks.json <<'JSON'
[
  {"name": "Amazon (Sponsored Products)", "ceiling": 900000, "halfpoint": 120000, "min": 50000, "max": 400000},
  {"name": "Walmart Connect (onsite)",    "ceiling": 500000, "halfpoint": 90000},
  {"name": "Walmart DSP (offsite CTV)",   "ceiling": 350000, "halfpoint": 140000}
]
JSON
python3 scripts/allocate.py --budget 600000 --plan networks.json --step 5000
```

3. Read the output. When the **`mgROAS`** (marginal iROAS) column is roughly equal
   across networks, the split is efficient — a network with a much higher marginal
   value is starved and should get more. The `iROAS` column is the *average* return;
   the marginal column is what governs the next dollar.
4. Sensitivity-check: re-run with the `halfpoint` you are least sure of moved ±30%.
   If the recommended split swings hard, flag the assumption rather than over-trusting
   a point estimate.

## Recipe 2 — Map inventory to the funnel (on-site / off-site / in-store)

Every RMN now sells three inventory types; don't buy them for the same job.

| Inventory | Examples | Funnel role | Primary KPI |
|-----------|----------|-------------|-------------|
| **On-site search** | Sponsored Products/Brands, Walmart Connect search | Lower — high intent, harvest demand | iROAS, new-to-brand % |
| **On-site display** | PDP/browse display, Sponsored Display | Mid — consideration on-platform | Detail-page views, ATC rate |
| **Off-site / DSP + CTV** | Amazon DSP, Walmart DSP (Trade Desk), Roundel off-site | Upper/mid — reach non-shoppers, drive store visits | Incremental reach, iROAS, halo to search |
| **In-store** | Screens, audio, sampling, self-checkout | Upper/lower at shelf — presence at point of purchase | Store sales lift, penetration |

Rules of thumb: fund **on-site search first** (it converts existing demand), then use
**off-site/DSP** to create *new* demand and feed the search funnel, and treat
**in-store** as reach against light/lapsed buyers. The clean room is what lets you see
the off-site → on-site → purchase path instead of crediting each silo separately.

## Recipe 3 — Stand up clean-room measurement (closed-loop, incremental)

1. **Pick the metric.** Demote platform ROAS (double-counts organic and last-click).
   Set **iROAS** (incremental return on ad spend) as the north star, measured via a
   holdout/ghost-bid or geo test, plus **new-to-brand rate** and **incremental
   penetration**.
2. **Choose the clean room** per retailer: AMC for Amazon, Luminate/Scintilla for
   Walmart, LiveRamp/Habu or 84.51° for others. Confirm you have seats before promising
   measurement in a plan.
3. **Design the incrementality test** *before* launch: define exposed vs holdout,
   ensure sufficient reach/power, and pick the lookback window (AMC now supports up to
   25 months of ad traffic and 5 years of purchase signal — use a window that captures
   your real purchase cycle, e.g. 90 days for CPG replenishment).
4. **Run the standard AMC pattern** for path analysis: query overlap between ad-exposed
   and converted audiences, compute reach/frequency-to-conversion, and isolate the
   incremental cohort. Start from AMC's instructional/no-code templates, then customise
   the SQL rather than hand-rolling from scratch.
5. **Feed results back into Recipe 1.** The measured iROAS by network *is* the input
   that reshapes next flight's `ceiling`/`halfpoint`. This closes the loop.

## Verify

- `python3 scripts/allocate.py --budget 600000 --plan networks.json --step 5000` prints
  a table whose `TOTAL` spend equals the budget (unless every network hit its max cap,
  which the script reports explicitly).
- The `mgROAS` values should be close across un-capped networks — that is the signal the
  allocation converged. Wildly different marginal values mean a cap is binding.
- Malformed plans fail fast: a negative `ceiling`, missing `name`, duplicate name, or
  minimums exceeding budget all raise a clear `ValueError` instead of silent garbage.
- Sanity gut-check: on-site search should rarely get less than off-site DSP unless
  search is genuinely saturated (very low `halfpoint`).

## Pitfalls

- **Platform ROAS is not iROAS.** Every RMN reports last-touch ROAS that flatters
  itself by claiming organic and cross-network sales. If a plan cites "8x ROAS" with no
  holdout, treat it as a vanity number and rebuild on incrementality.
- **Double-counting across networks.** Amazon and Walmart each claim the same converter.
  Only a clean room (or an MMM) deconflicts overlap — don't sum network-reported sales.
- **Curves from last-click.** Fitting `halfpoint`/`ceiling` to last-click ROAS bakes the
  bias into the optimiser. Fit to *incrementality-tested* returns.
- **In-store measurement is the weakest link.** Store lift often relies on modelled/
  panel data, not deterministic loyalty matches — state the confidence level, don't
  present it as closed-loop.
- **Chasing marginal parity too literally.** The helper is a planning heuristic on
  assumed curves, not a fitted model. Use it to structure the argument and spot obvious
  misallocation, then pressure-test with real test-and-learn budget.
- **Terminology drift.** RMNs rename fast (Luminate → Scintilla; new DSP partners
  quarterly). Verify current product names against the retailer's own site before a
  client-facing deliverable.
