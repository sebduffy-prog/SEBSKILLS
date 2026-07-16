---
name: category-entry-points-mental-availability
category: strategy
description: >
  Map a brand for growth the Ehrenberg-Bass way: elicit Category
  Entry Points (CEPs) with the 7 W's, score mental availability
  (mental market share, penetration, network size), audit
  distinctive brand assets on Romaniuk's Fame x Uniqueness grid.
  Turns How Brands Grow
  / Ehrenberg-Bass theory into brief inputs: a ranked CEP list,
  a mental-availability gap read, and asset keep/build/retire
  calls. Trigger on "category entry
  points", "CEPs", "mental availability", "distinctive brand
  assets", "DBA grid", "Byron Sharp", "Romaniuk", "How Brands
  Grow", "grow penetration", or "which assets do we protect".
when_to_use:
  - A growth brief needs a penetration-first, CEP-led strategic frame rather than a loyalty/segmentation frame
  - Building or refreshing a brand-tracking survey and you need the CEP + mental-availability question battery
  - Auditing distinctive brand assets to decide which logo/colour/character/sound to protect, build, or retire
  - Diagnosing why a well-known brand is not growing (famous but low mental market share or thin CEP network)
  - Prepping the strategic foundation before a creative or media brief so the work targets real buying situations
  - Translating How Brands Grow / Ehrenberg-Bass theory into agency-usable inputs for a specific client
when_not_to_use:
  - You already have the CEP/asset inputs and need the proposition and creative platform — use advertising-strategy
  - Auditing a live brand's current comms and equity end to end — use brand-audit (this feeds it)
  - Sizing or profiling audiences by attitude/demographics — use audience-segmentation or audience-insight
  - Search-velocity or share-of-search evidence specifically — use share-of-search
  - Reading GWI/survey data for buying behaviour without the Ehrenberg-Bass frame — use audience-insight
keywords:
  - category entry points
  - ceps
  - mental availability
  - physical availability
  - distinctive brand assets
  - dba grid
  - byron sharp
  - jenni romaniuk
  - how brands grow
  - ehrenberg-bass
  - mental market share
  - penetration
  - salience
  - buying situations
  - 7 ws
  - fame and uniqueness
similar_to:
  - advertising-strategy
  - brand-audit
  - audience-insight
  - audience-segmentation
  - share-of-search
inputs_needed: >
  Category and brand; ideally a CEP tracking export or qual on
  buying situations; distinctive-asset survey scores (fame +
  uniqueness) if auditing assets; a competitor set. Absent data,
  scaffold with an "awaiting data" state and elicit CEPs from qual.
produces: >
  A ranked CEP list mapped to the 7 W's; a mental-availability
  read (mental market share, network size, penetration gap vs
  competitors); a Fame x Uniqueness asset grid with keep/build/
  retire verdicts; a physical-availability checklist; and a
  short set of CEP + asset targets to hand to the brief.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Category Entry Points & Mental Availability

Turn Ehrenberg-Bass growth theory (Byron Sharp's *How Brands Grow*, Jenni
Romaniuk's *Building Distinctive Brand Assets* and *How Brands Grow Part 2*)
into concrete brief inputs. The through-line: **brands grow mainly by
increasing penetration — getting more category buyers to think of you in more
buying situations — not by chasing loyalty.** Two jobs make that happen:

- **Mental availability** — the propensity of the brand to be *thought of* in
  buying situations. Built by linking the brand to many **Category Entry
  Points (CEPs)** via **distinctive brand assets**.
- **Physical availability** — the ease of *finding and buying* the brand.
  Presence, prominence, and portfolio (range/relevance).

## When to use

Use this **before** the proposition is written, whenever the brief is about
growth, salience, penetration, or "which assets do we protect". It grounds the
strategy in evidence; `advertising-strategy` then turns the CEP and asset
targets into a proposition and platform, and `brand-audit` consumes this as its
mental-availability section.

## Prerequisites

- Honest data check. Ideal inputs: a **CEP tracking export** (buyers x CEP
  associations by brand), and a **distinctive-asset survey** giving each asset a
  *fame* and *uniqueness* score. Common reality: neither exists.
- If data is missing, **do not block** — scaffold the framework now with an
  "awaiting data" state, elicit CEPs from qual / category knowledge, and mark
  every quantified cell as an assumption to be validated. Never fabricate
  tracking numbers.
- `scripts/dba_grid.py` (pure python3.9 stdlib, no deps) classifies assets on
  the Fame x Uniqueness grid and computes mental-availability metrics from
  association counts.

## The frameworks (get these right)

### CEPs and the 7 W's
A CEP is a **moment when a buyer mentally enters the category** — the cue that
triggers brand recall. Elicit the full set with Romaniuk's **7 W's** so you
cover the real buying-situation space, not just occasions you already advertise:

| W | Prompt | Example (soft drinks) |
|---|--------|-----------------------|
| **Why** | motivation / need | "need an energy lift" |
| **When** | time of day / week | "mid-afternoon slump" |
| **Where** | location | "at my desk", "on the go" |
| **While** | concurrent activity | "watching a match" |
| **With whom** | social context | "with the kids" |
| **With what** | pairing / complement | "with a takeaway" |
| **How feeling** | emotional state | "want to treat myself" |

Good CEPs are **relevant** (real buyers, real volume), **specific**
(actionable), and **differentiating where possible**. Rank them by size x how
winnable they are for this brand.

### Mental availability metrics
From CEP tracking, three metrics matter (see `scripts/dba_grid.py`):

- **Mental market share** — the brand's share of *all* brand-CEP associations
  in the category. The headline mental-availability number; it tracks market
  share closely.
- **Mental penetration** — % of category buyers with *at least one* CEP link to
  the brand. Growth usually means widening this.
- **Network size** — average number of CEPs the brand is linked to, per buyer.
  Grow the network, not the depth in a few CEPs.

Diagnose the gap: a brand can be **famous but not grow** if it has high
awareness yet thin mental market share (linked to few CEPs) — the fix is more
CEPs, not more shouting.

### Distinctive Brand Assets — the Fame x Uniqueness grid
Assets (colour, logo, character, tagline, sound, shape, celebrity) are the
memory hooks that attach the brand to CEPs. Score each on two axes and plot:

- **Fame (Y)** — % of category buyers who link the asset to the brand.
- **Uniqueness (X)** — of those who link it to any brand, % who link it to
  *yours only* (not shared with competitors).

| | Low uniqueness | High uniqueness |
|---|---|---|
| **High fame** | **Avoid** — famous but shared; misattribution risk | **Solid gold** — protect + lead with it |
| **Low fame** | **Ignore** — retire / don't invest | **Investment potential** — yours alone; build fame |

Consistency compounds these; restyling resets them. Never casually change a
solid-gold asset.

### Physical availability — the 3 P's
Mental availability wins the mind; physical availability closes the sale.
Pressure-test: **Presence** (in the places/channels buyers shop), **Prominence**
(easy to spot at the point of purchase / findable online), **Portfolio** (range
covers the relevant CEPs and buyer needs).

## Recipes

### Recipe A — Growth diagnosis for a brand
1. List category CEPs via the 7 W's (from tracking, or elicit from qual).
2. Pull the brand's mental market share, network size, and penetration; compare
   to the biggest competitor. Where's the gap — few links, or weak links?
3. Audit distinctive assets on the grid (Recipe C).
4. Check physical availability (3 P's).
5. Output: 3-5 target CEPs to build, asset keep/build/retire verdicts, and one
   line on the mechanism ("grow penetration by linking to X, Y, Z via [asset]").

### Recipe B — Build the CEP tracking battery
For a survey: pick the ~15-30 most relevant CEPs (7 W's coverage), ask *"When
you think of [CEP], which brands come to mind?"* (free or aided), per brand per
CEP. From the responses compute the three metrics. Keep CEP wording buyer-natural.

### Recipe C — Distinctive-asset audit with the helper
```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
from dba_grid import dba_grid
# {asset: (fame %, uniqueness %)} from your survey
assets = {"Colour": (78, 71), "Character": (34, 82),
          "Jingle": (61, 38), "Tagline": (25, 22)}
for name, r in dba_grid(assets).items():
    print(f"{name:10} {r['quadrant']:20} {r['action']}")
PY
```
Then: protect *solid gold*, invest to build fame on *investment potential*,
handle *avoid* assets with care (never solo), retire *ignore*.

### Recipe D — Compute mental market share
```bash
python3 - <<'PY'
import sys; sys.path.insert(0, "scripts")
from dba_grid import mental_metrics
print(mental_metrics(
    brand_links={"on the go": 300, "afternoon slump": 210, "with kids": 140},
    category_total_links=3200, n_buyers=1000))
PY
```

## Verify

- Every CEP is a **buying situation a real buyer would recognise**, not a
  product feature or a demographic. Read them aloud — "when I..." should fit.
- The 7 W's are all represented; you have not only listed occasions you already
  own.
- Asset scores map to the correct quadrant: sanity-check with the helper's demo
  (`python3 scripts/dba_grid.py`) — Solid gold requires *both* axes high.
- The recommendation is **penetration-led** (more buyers, more CEPs), not a
  loyalty/retention plan dressed up.
- Any quantified claim is backed by data or explicitly flagged as an assumption.

## Pitfalls

- **Loyalty trap.** Defaulting to "deepen relationships with our fans" — the
  evidence says growth comes from light and non-buyers. Lead with penetration.
- **CEPs as segments.** CEPs are *situations*, not people. One buyer occupies
  many CEPs across a week; do not collapse them into personas.
- **Famous ≠ available.** High awareness with low mental market share means the
  brand is linked to too few CEPs. Fame is necessary, not sufficient.
- **Restyling solid-gold assets.** Rebrands that discard high-fame/high-unique
  assets throw away the memory structures that do the work. Change with extreme
  care.
- **Uniqueness without fame.** A striking asset nobody links to the brand yet is
  *investment potential*, not a win — it needs consistent fame-building before
  it can carry attribution.
- **Mental penetration in the helper is a floor.** True mental penetration needs
  *unique-buyer* counts (a buyer linked to 3 CEPs counts once). `mental_metrics`
  returns a conservative floor from single-CEP data; use real dedup counts when
  available.
- **Ignoring physical availability.** Perfect mental availability still fails if
  the brand isn't present, prominent, and range-relevant at the point of buying.
