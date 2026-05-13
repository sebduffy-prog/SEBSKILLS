---
name: share-of-search
description: |
  Compute, interpret, and present share of search (SoS) as a
  leading indicator of brand health and a competitive lens —
  the Les Binet / James Hankins technique. Covers picking the
  competitive set, pulling Google Trends data correctly,
  normalising it, smoothing seasonal effects, computing SoS,
  comparing against share-of-market (SoM) and share-of-voice
  (SOV), spotting lead/lag, and translating the result into a
  strategic recommendation. Use when the brief needs a search-
  led read on brand momentum without waiting for tracker waves.
  Trigger on phrases like "share of search", "SoS", "Google
  Trends analysis", "search-led brand health", "Binet share of
  search", "James Hankins method", "search vs market share",
  "search velocity", "brand search trend", "leading indicator",
  "search-share leading indicator", "do a SoS pull". Pairs with
  [[brand-audit]], [[competitive-comms-audit]], [[strategy-analyst]],
  and [[raw-data-research]] (the pull pipeline).
---

# Share of search

**Share of search** (SoS) is a brand's share of organic search
interest within a defined competitive set, computed from Google
Trends. It is one of the cheapest, fastest, and most defensible
brand-health metrics available — and an empirical **leading
indicator** of share of market by ~6–12 months (per Les Binet
and James Hankins' original work).

Used well, it lets a planner spot momentum shifts long before
the tracker catches them — and gives a CMO a number they can
read every Monday morning without buying anything.

## When to use

- A brand-health view is needed between tracker waves
- A competitive review needs a quantitative momentum read
- A strategy doc needs evidence of where the brand sits in
  audience consideration
- A campaign needs an in-flight indicator (search lifts often
  appear within weeks)
- A new-business pitch needs a fast, defensible read on the
  prospect's brand momentum vs competitors

**Don't use this skill** for: causal-effect claims ("the
campaign caused this lift" needs a holdout / MMM / lift test —
see [[data-analyst]]), or absolute volume claims (Trends is
relative, not absolute).

## What SoS is — and what it isn't

| It is | It isn't |
|---|---|
| Relative share of search interest in a defined set | An absolute count of searches |
| A leading indicator of SoM (typically by 6–12 months) | A causal measurement |
| Useful at category and brand level | A substitute for tracker / panel data |
| Stable across markets when normalised correctly | Comparable across categories without re-normalising |

Used out of context, SoS can mislead — most commonly when the
competitive set is poorly defined, or when a brand's name is
ambiguous (a homonym, a common word).

## Workflow

### Step 1 — Define the competitive set

Three rules:

1. **3–8 brands.** Fewer than 3 isn't a comparison; more than 8
   loses signal in the noise.
2. **Same category, same audience.** Don't mix challenger banks
   with retail banks; don't mix luxury automotive with mass.
3. **Stable across the time window.** Don't add or remove
   brands mid-series — the share recalculates and breaks the
   chart.

For an audit, include 1–2 *reference* brands the audience may
search adjacent to — these are useful baselines.

### Step 2 — Disambiguate brand names

Google Trends is literal. *"Sport"* is not the sportswear brand.
*"Apple"* spans fruit and tech. Solutions:

- Use the **"Topic" suggestion** in Trends when one exists
  (Trends groups searches under a knowledge-graph entity, not
  the literal string)
- For ambiguous brands, use a **disambiguating phrase** that's
  still common: *"Tesla cars"*, *"Apple iPhone"*. Apply the
  same disambiguator across the time window.
- Avoid extremely common words. If the brand's name is a verb,
  consider using the brand + product or brand + category.

### Step 3 — Pick the geography and time window

- **Geography:** the country / region the audit is in. UK only,
  not UK + worldwide.
- **Time window:** at least **3 years** for trend reads, **5
  years** for full leading-indicator analysis. The Binet/Hankins
  6–12 month lead-lag only shows up across multi-year horizons.

### Step 4 — Pull the data

Two acceptable pipelines:

**A. Manual (Trends UI):**

1. Open trends.google.com
2. Add up to 5 terms (use Topic where available)
3. Select country, time window
4. Download CSV
5. Repeat for the next batch of 5 if your set is larger

**B. Programmatic (`pytrends`, scriptable):**

```python
from pytrends.request import TrendReq
pytrends = TrendReq(hl="en-GB", tz=0)

brands = ["Monzo", "Revolut", "Starling Bank", "Chase UK", "Wise"]
pytrends.build_payload(brands, cat=0, timeframe="2020-01-01 2026-01-01", geo="GB")
df = pytrends.interest_over_time().drop(columns=["isPartial"], errors="ignore")
```

For sets >5, you must **chain pulls** because Trends caps each
request at 5 terms. Use the technique known as **rebasing**:

1. Pull terms 1–5; note the average of a stable anchor brand
   (often the category leader)
2. Pull terms 5–9 with the **same anchor** as term 5
3. Re-scale 5–9 by the ratio between the anchor in the two
   pulls

```python
# pseudocode
anchor = "Barclays"
pull_a = pytrends.build_payload(["Barclays","NatWest","Lloyds","Monzo","Revolut"], ...)
pull_b = pytrends.build_payload(["Barclays","Starling","Chase","Wise","HSBC"], ...)
scale = pull_a[anchor].mean() / pull_b[anchor].mean()
combined = pd.concat([pull_a, pull_b.drop(columns=[anchor]) * scale], axis=1)
```

This is the single most error-prone step. Always sanity-check
by plotting the anchor series across both pulls and confirming
they overlap after rescaling.

### Step 5 — Smooth and compute SoS

```python
# Smoothing — Trends weekly data is noisy; smooth with a
# trailing or centered MA
df_smooth = df.rolling(window=4, min_periods=1).mean()

# Compute share
df_share = df_smooth.div(df_smooth.sum(axis=1), axis=0) * 100
```

For seasonal categories (Christmas retail, summer travel),
also compute a **YoY-detrended** view:

```python
df_yoy = df_smooth.pct_change(periods=52)  # weekly data
```

### Step 6 — Compare against SoM and SOV

The strongest read comes from triangulating three series:

```
SoM (share of market) — from sales / panel data
SOV (share of voice)  — from ad intel
SoS (share of search) — computed above
```

Plot all three over time. The patterns to look for:

| Pattern | What it suggests |
|---|---|
| SoS up, SoM flat | Audience interest is building — SoM may follow in 6–12 months |
| SoS up, SOV flat | Brand is earning interest without paying for it — distinctive comms / earned momentum |
| SoS down, SOV up | Money is being spent without earning attention — creative or media problem |
| SoS up, SoM up, SOV flat | Most efficient — brand pulling without proportional push |
| SoS flat, SOV up sharply | Likely wear-out or wrong audience — flag as risk |
| SoS spike, then crash | Often a fad or PR moment — single-spike noise, not trend |

### Step 7 — Run the leading-indicator test

For a 3-year+ series, compute the **cross-correlation** between
SoS and SoM at various lags:

```python
import numpy as np
def crosscorr(x, y, max_lag=12):
    out = {}
    for lag in range(-max_lag, max_lag+1):
        shifted = y.shift(lag)
        out[lag] = np.corrcoef(x[shifted.notna()], shifted.dropna())[0,1]
    return out
```

The lag with the highest correlation is the "lead" (or "lag")
of SoS relative to SoM. A 6–12 month positive lag is the
canonical Binet/Hankins finding, but it varies — verify on the
specific brand and category.

### Step 8 — Translate into a strategic read

A SoS chart with no read is just a chart. Translate:

```
HEADLINE READ
  In the last 12 months, [brand] has gained NN percentage points
  of category share of search, moving from rank [N] to rank [N].

EVIDENCE OF DIRECTION
  [The pattern across SoS, SoM, SOV — which scenario above]

EXPECTATION
  Based on the historical SoS → SoM lead of [X] months for this
  category, we'd expect SoM to [direction] in the next [period].

CAVEATS
  Brand name ambiguity, anchor disambiguator used, seasonal
  smoothing, time window.

RECOMMENDATION
  [What this changes in the plan — keep doing X, watch Y, re-plan if Z]
```

## Output template

```
SHARE OF SEARCH — [category, market, window]
Date / version
Brands in set: [list, with disambiguators if used]
Method: Google Trends weekly, [pull date], [smoothing],
        [rescaling if multiple pulls were chained]

THE HEADLINE
  [one sentence — the direction of travel and the rank movement]

THE CHART
  SoS over time, all brands in the set, smoothed
  Annotate notable inflections (launches, campaigns, news moments)

SoS vs SOV vs SoM
  Triangulated chart for [brand] and 2 key competitors

LEAD/LAG ANALYSIS
  Cross-correlation of SoS and SoM, lag in months, correlation
  at peak

THE READ
  Pattern + interpretation + caveat

RECOMMENDATION
  Plan implication, with confidence register

APPENDIX
  Disambiguators used, anchor brand, rescaling factor,
  raw data link
```

For the visual, use [[vccp-media-design]]'s matplotlib config —
mustard primary line, teal-deep for competitors, ink hairline
zero baseline, no red/green.

## Common mistakes to avoid

1. **Adding / removing brands mid-window.** Recomputes every
   share. Lock the set before pulling.
2. **Forgetting to rescale.** Pulling >5 brands without a
   shared anchor produces non-comparable scales.
3. **Using the literal string for ambiguous brands.** Always
   prefer the Topic suggestion or a stable disambiguator.
4. **Daily granularity for long windows.** Use weekly for
   anything over 12 months — daily Trends data is noisier and
   API-throttled.
5. **Smoothing too aggressively.** 4-week rolling is the
   default; longer hides real moves.
6. **Treating SoS as causal.** A SoS lift coincident with a
   campaign is *consistent with* the campaign working, not
   *proof*. Triangulate with MMM / lift / tracker.
7. **Ignoring news / PR spikes.** A scandal or product launch
   spike is usually not strategic; annotate and discount.
8. **Cross-category comparisons.** SoS shares are not
   comparable between categories without re-normalising.
9. **Ignoring the universe.** Trends gives *relative* shares
   within the set — say so in every output, every time.
10. **No lead-lag analysis.** The leading-indicator point only
    earns its place when you've actually run the correlation
    on the specific brand and category.

## Useful references

- **Les Binet** — *Share of Search* (IPA / WARC, 2020 onward)
- **James Hankins** — *Predictive Marketing* and the original
  share-of-search papers (johnnyhankins.com)
- **Faris Yakob / IPA / WARC** — case studies extending the
  method

## Tooling

- `pytrends` (Python) — the most common scripted pull
- Trends UI — for one-off pulls
- `glimpse.ai`, `exploding-topics.com` — paid wrappers with
  better normalisation and longer histories
- `google-trends-api` (JS) — for web tools
- Plot with [[vccp-media-design]] matplotlib config
- Pipeline / cataloguing via [[raw-data-research]]

## Handoffs

- **Inputs from** [[raw-data-research]] (data pipeline),
  [[data-analyst]] (statistical tests on the time series)
- **Outputs to** [[brand-audit]] (the search slice),
  [[competitive-comms-audit]] (competitive view),
  [[strategy-analyst]] (the read), [[advertising-strategy]] /
  [[media-strategy]] (the plan implication)
