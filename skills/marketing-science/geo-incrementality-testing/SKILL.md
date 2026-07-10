---
name: geo-incrementality-testing
category: marketing-science
description: >
  Design and analyse geo holdout / geo-lift experiments to measure the TRUE incremental
  effect of a media campaign — not correlated last-click noise. Reach for this to pick
  treatment vs control markets, run power/MDE analysis before launch, and estimate lift
  after with synthetic control or difference-in-differences causal inference. Covers Meta's
  GeoLift (R), pymc-labs CausalPy (Python Bayesian), and a zero-dependency numpy synthetic
  control estimator. Use when someone says "did this campaign actually work", "geo test",
  "matched-market", "holdout", "incrementality", "causal lift", or "how do we prove ROI".
when_to_use:
  - Designing a geo holdout before a campaign — choosing test/control markets and required test length
  - Running a power / minimum-detectable-effect (MDE) analysis to size a lift test
  - Estimating post-campaign incremental lift from a market that got media vs matched controls
  - Building a synthetic-control counterfactual for one or a few treated regions
  - Difference-in-differences when you have clean treated vs control groups and a shared shock date
  - Defending "is our media actually incremental" to a client with a causal, not correlational, method
when_not_to_use:
  - Full media-mix / spend-allocation modelling across all channels — use the marketing-mix-modelling skill
  - Individual-level RCT / A-B split-test analysis with user randomisation — use an experiment-analysis skill
  - Pure descriptive audience sizing or reach reporting with no counterfactual — use GWI/data-analysis skills
  - Forecasting future sales with no intervention to measure — use a time-series forecasting skill
keywords:
  - incrementality
  - geo-lift
  - geolift
  - synthetic-control
  - causalpy
  - difference-in-differences
  - holdout
  - matched-market
  - causal-inference
  - power-analysis
  - mde
  - counterfactual
  - att
  - lift-test
  - placebo-test
similar_to: []
inputs_needed: >
  A balanced long-format panel (location, date, KPI) with a decent pre-period (>=8, ideally
  30+ periods); the treated market(s); the treatment start date; optionally CPIC (cost per
  incremental conversion) and budget for power analysis.
produces: >
  A test design (which markets, how long, MDE at target power) and/or a post-test lift
  readout — ATT per period, cumulative incremental units, % lift, and a placebo p-value —
  plus plots of actual vs synthetic counterfactual.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Geo Incrementality Testing

Measure the *incremental* effect of media by comparing markets that got a campaign against a
counterfactual built from markets that did not. This is the causal-inference answer to "did it
actually work", replacing last-click attribution and pre/post correlation.

## When to use

Use it in two phases: **design** (before launch — pick markets, size the test, find the MDE)
and **readout** (after — estimate lift with a defensible counterfactual). Three engines:

| Engine | Language | Best for |
|--------|----------|----------|
| **GeoLift** (Meta) | R | End-to-end design + power + readout; industry-standard for geo tests |
| **CausalPy** (pymc-labs) | Python | Bayesian synthetic control & DiD with credible intervals |
| `scripts/synthetic_control.py` | Python (numpy/scipy) | Quick counterfactual + placebo p-value with zero heavy install |

## Prerequisites

- **Data**: a *balanced* panel — every location has a value for every date, long format with
  columns like `location, date, Y`. Gaps must be filled before fitting.
- **Pre-period**: aim for 30+ periods pre-treatment; the numpy helper needs >=3 (>=8 for a
  usable placebo test). Longer pre-periods = tighter counterfactual.
- **GeoLift**: R + `remotes::install_github("facebookincubator/GeoLift")`. Not on this Mac by
  default (no R) — use the Python paths locally, GeoLift on a machine with R.
- **CausalPy**: `pip install CausalPy` (pulls PyMC — heavy; a venv is wise).
- **numpy helper**: numpy + scipy only (both already present here). No R, no PyMC.

## Recipe A — Design a test with GeoLift (R)

Ground truth: `facebookincubator.github.io/GeoLift`. Load pre-period data, then let GeoLift
search market combinations and simulate power.

```r
remotes::install_github("facebookincubator/GeoLift")
library(GeoLift)

GeoTestData_PreTest <- GeoDataRead(
  data = GeoLift_PreTest, date_id = "date", location_id = "location",
  Y_id = "Y", format = "yyyy-mm-dd", summary = TRUE
)

# Search combinations of N test markets over candidate durations; returns ranked designs
MarketSelections <- GeoLiftMarketSelection(
  data = GeoTestData_PreTest,
  treatment_periods = c(10, 15),      # candidate test lengths
  N = c(2, 3, 4, 5),                  # candidate # of test markets
  effect_size = seq(0, 0.5, 0.05),    # lift grid for power sim
  Y_id = "Y", location_id = "location", time_id = "time",
  cpic = 7.50, budget = 100000, alpha = 0.1,
  fixed_effects = TRUE, side_of_test = "two_sided"
)

# Power curve + minimum detectable effect for a chosen market set
power <- GeoLiftPower(
  data = GeoTestData_PreTest, locations = c("chicago", "portland"),
  effect_size = seq(-0.25, 0.25, 0.01), treatment_periods = 15,
  cpic = 7.5, side_of_test = "two_sided"
)
plot(power, show_mde = TRUE)
```

Pick the design where power >= 0.8 at the smallest lift you can afford to detect (the MDE),
inside budget. Freeze markets and dates *before* launch — no peeking.

## Recipe B — Readout with GeoLift (R)

```r
GeoTestData_Test <- GeoDataRead(data = GeoLift_Test, date_id = "date",
  location_id = "location", Y_id = "Y", format = "yyyy-mm-dd")

GeoTest <- GeoLift(
  Y_id = "Y", data = GeoTestData_Test,
  locations = c("chicago", "portland"),
  treatment_start_time = 91, treatment_end_time = 105   # time indices, not dates
)
summary(GeoTest)          # ATT, % lift, p-value, incremental units
plot(GeoTest, type = "Lift")   # cumulative incremental
plot(GeoTest, type = "ATT")    # per-period effect
```

Add `model = "best"` to let GeoLift search the augmented-SCM specification.

## Recipe C — Synthetic control in Python (CausalPy)

Ground truth: `causalpy.readthedocs.io`. Bayesian synthetic control — a weighted blend of
control units, with credible intervals for free.

```python
import causalpy as cp

result = cp.SyntheticControl(
    df, treatment_time,
    control_units=["denver", "austin", "miami", "seattle"],
    treated_units=["chicago"],
    model=cp.pymc_models.WeightedSumFitter(
        sample_kwargs={"target_accept": 0.95, "random_seed": 42}
    ),
)
fig, ax = result.plot(plot_predictors=True)
result.summary()
stats = result.effect_summary(treated_unit="chicago",
                              cumulative=True, relative=True)
```

For a clean two-group design with a shared shock date, use **difference-in-differences**:

```python
result = cp.DifferenceInDifferences(
    df, formula="y ~ 1 + group*post_treatment",
    time_variable_name="t", group_variable_name="group",
    model=cp.pymc_models.LinearRegression(sample_kwargs={"random_seed": 42}),
)
result.summary(); result.plot()
```

The `group:post_treatment` interaction coefficient IS the causal DiD estimate.

## Recipe D — Zero-dependency estimator (numpy/scipy)

When R and PyMC are unavailable, `scripts/synthetic_control.py` fits a convex synthetic control
(non-negative weights summing to 1) on the pre-period, projects the counterfactual, and runs an
in-space placebo permutation test (Abadie et al. 2010) for significance.

```bash
python3 scripts/synthetic_control.py \
  --data panel.csv --treated chicago --treatment-start 2026-09-01
```

Output (JSON): donor weights, `att_per_period`, `cumulative_lift`, `pct_lift`, `pre_rmspe`,
and `placebo_p_value` (fraction of markets whose post/pre RMSPE ratio >= the treated market —
lower is stronger). Columns default to `location,date,Y`; override with flags.

## Verify

- `python3 -m py_compile scripts/synthetic_control.py` — syntax clean.
- Smoke test: generate a panel with a KNOWN injected lift and confirm the estimator recovers
  a positive ATT of roughly that size and names sensible donor weights.
- Sanity gate: `pre_rmspe` should be small relative to the effect. A large pre-period gap means
  the synthetic doesn't track the treated market pre-launch — the readout is not trustworthy.
- Cross-check: if GeoLift and CausalPy disagree wildly, inspect donor pools and pre-period fit
  before believing either.

## Pitfalls

- **Convex-hull limit**: classic synthetic control has no intercept — the treated unit must sit
  *inside* the range of the donor pool. If the treated market's baseline is above every donor,
  weights saturate and you get a persistent pre-period gap. Add higher-level donors or use an
  augmented/de-meaned model (GeoLift `model="best"`, CausalPy handles this Bayesianly).
- **Peeking / post-hoc market picks**: choosing treated markets *after* seeing outcomes, or
  stopping when significant, invalidates the p-value. Lock design pre-launch.
- **Too-short pre-period**: <8 pre points gives an unstable fit and a near-useless placebo test.
- **Contaminated controls**: control markets exposed to spillover (adjacent DMAs, national TV,
  PR) bias lift toward zero. Exclude bleed-over geos.
- **Unbalanced panel**: missing loc/date cells silently corrupt the weights — the helper errors
  out on purpose; fill gaps first.
- **Time index vs date**: GeoLift's `treatment_start_time` is an integer period index, not a
  calendar date. Map it via the `time` column that `GeoDataRead` creates.
- **p-value granularity**: the in-space placebo p-value is bounded below by 1/(#markets). With
  6 markets the smallest possible p is 0.17 — you need enough donors for a meaningful test.
