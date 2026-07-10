---
name: marketing-mix-modeling
category: marketing-science
description: >
  Build a Bayesian marketing-mix model to measure media ROI, decompose sales,
  and optimise budget. Reach for this when someone asks "what's the ROI of TV
  vs social", "how much did media drive incremental sales", "reallocate the
  budget", "MMM / econometric measurement", "adstock and saturation", "diminishing
  returns", or "triangulate MMM against a geo lift / conversion test". Grounds on
  Google Meridian and PyMC-Marketing; covers priors, adstock/saturation, ROI
  decomposition, response curves, budget optimisation, and geo-lift calibration.
when_to_use:
  - Measuring incremental ROI / ROAS per channel from weekly (or geo-weekly) spend + sales data
  - Decomposing sales into base + each media channel's contribution over time
  - Estimating adstock (carryover) and saturation (diminishing returns) curves
  - Optimising or reallocating a fixed media budget to maximise revenue/KPI
  - Calibrating an MMM against a geo lift or conversion-lift experiment (triangulation)
  - Setting informative ROI priors for a low-data or short-history brand
when_not_to_use:
  - User-level or click-path last-touch attribution — that is not MMM (use a web/MTA analytics path, not this skill)
  - Pure forecasting of a single series with no media decomposition — use a general time-series/forecasting skill
  - Designing or analysing the lift experiment itself end-to-end — use an experimentation/geo-test skill; this skill only ingests its result as a prior
  - Audience sizing or segmentation questions — use gwi-spark / audience skills, not an econometric model
keywords:
  - mmm
  - marketing-mix-modeling
  - media-mix-model
  - meridian
  - pymc-marketing
  - adstock
  - saturation
  - roi
  - roas
  - budget-optimization
  - bayesian
  - geo-lift
  - incrementality
  - response-curve
  - econometrics
  - attribution
similar_to: []
inputs_needed: >
  Weekly (or geo x weekly) CSV with date, KPI/sales (revenue or conversions),
  per-channel media spend, and per-channel impressions/clicks if available;
  optional control columns (price, seasonality, distribution, competitor);
  optional geo-lift/experiment ROI point estimate for calibration. Python 3.10+.
produces: >
  A fitted Bayesian MMM with per-channel ROI/ROAS posteriors, a sales
  decomposition (base vs media over time), adstock + saturation response
  curves, an optimised budget allocation, and a triangulation note versus any
  supplied experiment.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Marketing Mix Modeling (Bayesian MMM)

Econometric measurement of media effectiveness: regress sales on media spend
(transformed by **adstock** carryover and **saturation** diminishing returns)
plus controls, in a Bayesian framework so every ROI comes with a credible
interval. Two production libraries are covered — **Google Meridian** (geo-level,
ROI-prior-first, reach/frequency support) and **PyMC-Marketing** (flexible,
national or hierarchical). Then optimise budget and triangulate against a lift
experiment.

## When to use

Use when the question is *"what did media actually cause, and where should the
next pound go?"* at a channel level, from aggregate spend + sales — not per-user
attribution. This is VCCP Media's core measurement currency.

## Prerequisites

- **Python 3.10+** (Meridian and current PyMC-Marketing require 3.10+; this Mac's
  system `python3` is 3.9 — create a venv with a newer interpreter, e.g. `uv venv
  --python 3.11` or a `conda`/`pyenv` 3.11).
- Install one stack:
  - Meridian (TensorFlow-Probability backend, GPU optional):
    `pip install --upgrade google-meridian` (GPU: `google-meridian[and-cuda]`).
  - PyMC-Marketing (PyMC/PyTensor backend):
    `pip install pymc-marketing`.
- **Data**: ≥ ~2 years of weekly rows ideally (≥ 104 points), or fewer weeks
  across many geos. Columns: `date`, KPI, per-channel `*_spend`, ideally
  per-channel `*_impressions`, plus controls (price, promo, seasonality proxy).
- No cloud key needed — models fit locally. Sampling is CPU-heavy; a national
  weekly model fits in minutes, geo models can take longer.
- Quick sanity math (no Bayesian deps) via `scripts/transforms.py` — adstock,
  saturation, contribution shares, ROI. `python3 scripts/transforms.py --demo`.

## Recipe A — Meridian (geo-level, ROI-prior first)

Meridian's core idea: you set an **ROI prior per channel** (mean + uncertainty),
and the model updates it against the data. Great when you have a weak signal or
a prior belief/benchmark to anchor.

```python
import numpy as np, pandas as pd, tensorflow_probability as tfp
from meridian import constants
from meridian.data import load
from meridian.model import model, spec, prior_distribution
from meridian.analysis import analyzer, optimizer, visualizer, summarizer

# 1. Map your CSV columns to Meridian roles
coord = load.CoordToColumns(
    time="week",
    geo="region",                 # single-geo? use a national loader instead
    kpi="revenue",
    revenue_per_kpi=None,         # set if KPI is conversions, not revenue
    population="population",
    controls=["price_index", "seasonality"],
    media=["tv_impr", "social_impr", "search_impr"],
    media_spend=["tv_spend", "social_spend", "search_spend"],
)
loader = load.CsvDataLoader(
    csv_path="mmm_geo_weekly.csv",
    kpi_type="revenue",           # or "non_revenue"
    coord_to_columns=coord,
    media_to_channel={"tv_impr": "TV", "social_impr": "Social", "search_impr": "Search"},
    media_spend_to_channel={"tv_spend": "TV", "social_spend": "Social", "search_spend": "Search"},
)
data = loader.load()

# 2. ROI priors (LogNormal). roi_mu/roi_sigma are in log space.
roi_mu, roi_sigma = 0.2, 0.9
prior = prior_distribution.PriorDistribution(
    roi_m=tfp.distributions.LogNormal(roi_mu, roi_sigma, name=constants.ROI_M)
)
model_spec = spec.ModelSpec(prior=prior)     # defaults = geometric adstock + Hill

# 3. Fit
mmm = model.Meridian(input_data=data, model_spec=model_spec)
mmm.sample_prior(500)
mmm.sample_posterior(n_chains=4, n_adapt=2000, n_burnin=500, n_keep=1000, seed=0)

# 4. Results: ROI, decomposition, response curves
az = analyzer.Analyzer(mmm)
roi_summary = az.summary_metrics()            # per-channel ROI / incremental outcome
media_summary = visualizer.MediaSummary(mmm)  # .plot_roi_bar_chart(), response curves

# 5. Budget optimisation (fixed budget -> reallocate to maximise outcome)
opt = optimizer.BudgetOptimizer(mmm)
results = opt.optimize(fixed_budget=True)     # or target_roi=... / target_mroi=...
results.optimized_data                        # xr.Dataset: new spend per channel + lift

# 6. One-click HTML report
summarizer.Summarizer(mmm).output_model_results_summary(
    "mmm_report.html", start_date="2024-01-01", end_date="2025-12-31")
```

Notes: `optimize()` also accepts `spend_constraint_lower/upper` (per-channel
bounds), `target_roi`, `target_mroi` (flexible-budget targeting), and
`selected_geos` / `start_date`+`end_date` to scope the scenario.

## Recipe B — PyMC-Marketing (national, flexible priors)

Explicit adstock + saturation objects; clean posterior via ArviZ.

```python
import pandas as pd
from pymc_marketing.mmm import MMM, GeometricAdstock, LogisticSaturation

df = pd.read_csv("mmm_weekly.csv", parse_dates=["date_week"])
X = df[["date_week", "tv_spend", "social_spend", "search_spend", "price", "event"]]
y = df["sales"]

mmm = MMM(
    date_column="date_week",
    channel_columns=["tv_spend", "social_spend", "search_spend"],
    control_columns=["price", "event"],
    adstock=GeometricAdstock(l_max=8),        # carryover up to 8 weeks
    saturation=LogisticSaturation(),
    yearly_seasonality=2,                     # Fourier terms for seasonality
)
mmm.fit(X, y, chains=4, tune=1500, draws=1000, target_accept=0.9, random_seed=42)

# Diagnostics + contributions
mmm.plot_channel_contributions_grid(start=0, stop=1.5, num=12)   # response curves
contrib = mmm.compute_channel_contribution_original_scale()      # xarray, media by time
roas = mmm.get_ter()  # or derive ROAS = channel_contribution.sum() / channel_spend.sum()

# Budget optimisation (allocate spend to maximise expected response)
alloc = mmm.optimize_budget(budget=1_000_000, num_periods=8)     # returns optimal spend
```

Swap transforms freely: `WeibullPDFAdstock`, `DelayedAdstock`; `HillSaturation`,
`MichaelisMentenSaturation`, `TanhSaturation` — all importable from
`pymc_marketing.mmm`.

## Recipe C — Calibrate / triangulate against a geo lift

Never trust an MMM ROI in isolation. If you have a geo-lift or conversion-lift
experiment giving an incremental ROI for a channel, fold it in as a prior so the
two methods agree — this is the credible measurement story for a client.

- **Meridian**: pass the experiment's ROI as a tight per-channel `roi_m` prior
  (small `roi_sigma`) for that channel, or use Meridian's experiment-calibration
  support to anchor the posterior to the measured lift.
- **PyMC-Marketing**: use `add_lift_test_measurements(...)` with your experiment's
  spend-delta and observed lift; the likelihood then pulls the saturation curve
  toward the tested point.
- **Triangulation report**: state MMM ROI (with CI), experiment ROI (with CI),
  and the calibrated posterior. If they disagree wildly, distrust the model spec
  (missing control, collinear channels, wrong adstock length) before the data.

## Verify

- **Sanity math first**: `python3 scripts/transforms.py --demo` — confirms
  adstock conserves spend, saturation stays in [0,1), and contribution shares +
  ROI compute. Prototype curves here before a multi-minute fit.
- **Convergence**: check R-hat < 1.01 and no divergences (Meridian:
  `az.get_rhat()`; PyMC: `arviz.summary(mmm.idata)`). Bad R-hat ⇒ raise
  `n_adapt`/`tune` or `target_accept`, or reparametrise.
- **Fit quality**: posterior-predictive vs actual sales (R² / MAPE) should track;
  a decomposition where "base" is ~100% means media isn't identified.
- **Face validity**: ROIs and saturation shapes must be defensible to a client —
  negative or absurd ROIs usually signal collinear channels or a missing control.
- **Holdout**: refit on n-8 weeks, predict the last 8, compare.

## Pitfalls

- **Python 3.9 will not work.** Both libraries need 3.10+. Make a venv; do not
  `pip install` into the system interpreter on this Mac.
- **Correlation ≠ causation, and MMM is correlational.** Always-on channels with
  flat spend are barely identifiable — calibrate with an experiment (Recipe C).
- **Too few observations.** < ~2yrs weekly national data ⇒ wide intervals; go
  geo-level (Meridian) to buy statistical power from cross-section.
- **Collinear media** (channels that move together, e.g. TV + OOH bursts) split
  credit arbitrarily — merge them or add priors.
- **Adstock length matters**: `l_max` too short truncates real carryover; too
  long overfits. TV needs longer decay than search.
- **ROI units**: revenue-KPI ROI is revenue/£; conversion-KPI needs
  `revenue_per_kpi` or you get conversions/£, not ROAS. Don't mix them in one bar chart.
- **Optimiser is only as good as the curves.** A budget reallocation off a poorly
  identified saturation curve is confident nonsense — verify curves first.
- **Don't over-claim precision.** Report credible intervals, not point ROIs, to clients.
