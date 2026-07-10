---
name: time-series-forecasting
category: data-analysis
description: >
  Forecast a time series in Python with Nixtla StatsForecast (AutoARIMA, AutoETS,
  AutoTheta, MSTL) or TimeGPT — backtest with rolling cross-validation, produce
  calibrated prediction intervals, and pick a winner by MAE/RMSE/MAPE. Reach for
  this whenever someone wants to project sales, spend, impressions, traffic, or KPIs
  forward, needs confidence bands, or asks "what will X be next month/quarter" beyond
  an Excel trendline. Handles many series at once and seasonality.
when_to_use:
  - Projecting a metric (sales, media spend, impressions, sessions, signups) forward N periods
  - Need prediction intervals / confidence bands, not just a point line
  - Backtesting model accuracy with rolling-origin cross-validation before trusting a forecast
  - Forecasting many series at once (per campaign, per SKU, per region) in one pass
  - Seasonal or multi-seasonal data (weekly + yearly) where a trendline is inadequate
  - Comparing several models (ARIMA vs ETS vs Theta vs TimeGPT) on the same holdout
when_not_to_use:
  - Simple single-cell trend/FORECAST in a spreadsheet — use excel-forecasting-formulas
  - Monte-Carlo scenario simulation in a workbook — use excel-monte-carlo-formulas
  - Hypothesis tests / significance on static samples — use statistical-testing
  - Generic dataframe wrangling with no forecasting — use polars-dataframes or exploratory-data-analysis
keywords:
  - forecasting
  - time-series
  - statsforecast
  - nixtla
  - autoarima
  - timegpt
  - prediction-intervals
  - cross-validation
  - backtesting
  - seasonality
  - mape
  - rmse
  - ets
  - theta
  - demand-forecast
similar_to:
  - excel-forecasting-formulas
  - excel-monte-carlo-formulas
  - statistical-testing
  - exploratory-data-analysis
inputs_needed: A CSV/dataframe with a date column and a numeric value column (optionally a series-id column for many series). Python 3.9+. For TimeGPT: a NIXTLA_API_KEY.
produces: A forecast dataframe (point forecast + interval columns), a cross-validation accuracy table ranking models by MAE/RMSE/MAPE, and an optional plot.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Time-Series Forecasting (StatsForecast / TimeGPT)

Statistical and foundation-model forecasting in Python. StatsForecast gives fast,
battle-tested classical models (AutoARIMA, AutoETS, AutoTheta, MSTL) with proper
prediction intervals and rolling backtests. TimeGPT (Nixtla's hosted foundation
model) is an optional zero-shot alternative when you have little history or many
series and don't want to tune.

## When to use

Use when the deliverable is a real forward projection with uncertainty — "how many
impressions next quarter", "project weekly sales for the next 13 weeks with a 90%
band", "which model best predicts this KPI". If the answer is one spreadsheet cell,
use `excel-forecasting-formulas` instead.

## Prerequisites

- **Python 3.9+** (this Mac ships 3.9). Install into a venv to avoid touching system Python.
- **Packages** (real, verified names/versions):
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install "statsforecast>=2.0" "utilsforecast>=0.2" pandas
  # optional plotting: pip install matplotlib
  # optional foundation model: pip install "nixtla>=0.7"
  ```
  `statsforecast` pulls `numba` (JIT) — first import is slow while it compiles, then fast.
- **TimeGPT only**: a Nixtla API key. `export NIXTLA_API_KEY=nixak-...` (get one at dashboard.nixtla.io). No key = skip the TimeGPT recipe; StatsForecast is fully local and free.

### The data contract (non-negotiable)

Every Nixtla API wants a **long** dataframe with exactly these column names:

| column      | meaning                          |
|-------------|----------------------------------|
| `unique_id` | series identifier (use a constant like `"series_1"` if you have one series) |
| `ds`        | timestamp (`datetime64`, evenly spaced) |
| `y`         | numeric value to forecast        |

Rename your columns to these before doing anything. Gaps in the date index must be
filled (0 or interpolate) — the models assume a regular grid at the given `freq`.

## Recipes

### 1. Load and shape your data

```python
import pandas as pd

raw = pd.read_csv("sales.csv")                       # e.g. date, revenue columns
df = raw.rename(columns={"date": "ds", "revenue": "y"})
df["ds"] = pd.to_datetime(df["ds"])
df["unique_id"] = "revenue"                           # one series
df = df[["unique_id", "ds", "y"]].sort_values("ds")
```

Pick a pandas `freq` string that matches your cadence and pass it everywhere:
`"D"` daily, `"W"` weekly, `"ME"` month-end, `"MS"` month-start, `"QE"` quarter-end,
`"h"` hourly. **This must match your actual spacing** or intervals will be wrong.
Set `season_length` to the number of steps in one seasonal cycle: 12 for monthly-yearly,
7 for daily-weekly, 52 for weekly-yearly.

### 2. Fit and forecast with intervals

```python
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS, AutoTheta

sf = StatsForecast(
    models=[AutoARIMA(season_length=12), AutoETS(season_length=12), AutoTheta(season_length=12)],
    freq="MS",
    n_jobs=-1,                       # all cores; models run in parallel
)
# forecast() fits + predicts in one call and returns a dataframe:
fcst = sf.forecast(df=df, h=12, level=[80, 95])
print(fcst.head())
# columns: unique_id, ds, AutoARIMA, AutoARIMA-lo-95, AutoARIMA-hi-95,
#          AutoARIMA-lo-80, AutoARIMA-hi-80, AutoETS, AutoETS-lo-95, ...
```

`level=[80, 95]` yields 80% and 95% intervals as `<Model>-lo-<L>` / `<Model>-hi-<L>`
columns. Prefer `sf.forecast(df=df, ...)` (stateless, returns df) over `sf.fit(df)` +
`sf.predict(h=...)` unless you specifically need to reuse a fitted object.

### 3. Backtest with rolling cross-validation (the important part)

Never trust a forecast you haven't backtested. `cross_validation` walks a rolling
origin through history, forecasting `h` steps from each cutoff:

```python
cv = sf.cross_validation(
    df=df,
    h=12,            # forecast horizon per window
    n_windows=4,     # number of rolling backtests
    step_size=12,    # advance the cutoff by this many steps between windows
    level=[95],
)
# cv columns: unique_id, ds, cutoff, y (actual), AutoARIMA, AutoETS, AutoTheta, + intervals
```

Then score each model on the held-out actuals and rank them:

```python
from utilsforecast.evaluation import evaluate
from utilsforecast.losses import mae, rmse, mape

model_cols = ["AutoARIMA", "AutoETS", "AutoTheta"]
scores = evaluate(cv.drop(columns="cutoff"), metrics=[mae, rmse, mape], models=model_cols)
# average across windows/series to get a leaderboard:
leaderboard = scores.drop(columns="unique_id").groupby("metric").mean()
print(leaderboard)   # lower is better; pick the winning column per metric
```

Pick the model with the lowest RMSE/MAE (or MAPE for a scale-free view), then refit
that single model on all data for the production forecast. `scripts/backtest.py`
does exactly this end-to-end on your CSV.

### 4. Multiple series at once

Already handled: give each series a distinct `unique_id` and stack them in the same
long dataframe. `forecast`/`cross_validation` fit every series in parallel and return
all of them — one call for 5 campaigns or 5,000 SKUs. No loop needed.

### 5. Multi-seasonal data (e.g. hourly with daily + weekly cycles)

```python
from statsforecast.models import MSTL, AutoARIMA
sf = StatsForecast(
    models=[MSTL(season_length=[24, 24*7], trend_forecaster=AutoARIMA())],
    freq="h",
)
fcst = sf.forecast(df=df, h=48, level=[90])
```

### 6. Optional — TimeGPT (hosted foundation model)

Zero-shot, no tuning, good when history is short or you have many heterogeneous series.
Needs the API key and sends data to Nixtla's API (mind data governance for client data).

```python
from nixtla import NixtlaClient
client = NixtlaClient()                       # reads NIXTLA_API_KEY from env
fcst = client.forecast(df=df, h=12, freq="MS", level=[80, 95])
cv   = client.cross_validation(df=df, h=12, n_windows=4, freq="MS")
```

Compare its cross-validation scores against StatsForecast on the same windows before
choosing — a well-specified AutoETS often matches or beats it on clean single series.

## Verify

Sanity checks before you ship a number:

- **Interval columns exist and widen with horizon.** `-lo-95`/`-hi-95` present; the band
  should generally get wider further out. A flat/absent band = you forgot `level=`.
- **Backtest beats naive.** Compare your winner's MAE against `SeasonalNaive(season_length=…)`
  in the same `cross_validation` call. If a classical model can't beat naive, don't forecast — say so.
- **Point forecast is plausible.** Plot history + forecast: `StatsForecast.plot(df, fcst)`
  (needs matplotlib). Look for level shifts, exploded trends, or negative values on a
  strictly-positive metric.
- **Freq matches reality.** `df["ds"].diff().value_counts()` should show one dominant spacing
  equal to your `freq`.

Smoke-test the helper without any data:
```bash
python3 -m py_compile scripts/backtest.py && echo OK
python3 scripts/backtest.py --demo        # runs on built-in AirPassengers if statsforecast is installed
```

## Pitfalls

- **Wrong `freq` or `season_length`.** The single most common mistake. Monthly data with
  `season_length=7` produces garbage seasonality. Weekly = 52, daily-with-weekly = 7,
  monthly-with-yearly = 12, hourly-with-daily = 24.
- **Irregular / gappy dates.** Models assume a complete grid. Reindex to a full date range
  and fill missing periods before fitting: `df.set_index("ds").reindex(full_range).fillna(0)`.
- **Forecasting without backtesting.** A point line with no cross-validated error is a guess.
  Always run recipe 3 and report the holdout MAE/MAPE alongside the forecast.
- **Reading `predict` state.** `sf.predict()` only works after `sf.fit()`; `sf.forecast()` is
  self-contained. Mixing them causes "not fitted" errors.
- **Negative or zero-floor metrics.** ARIMA/ETS can predict below zero. For counts/revenue,
  clip at 0 (`fcst[col].clip(lower=0)`) or model `log1p(y)` and `expm1` the output.
- **numba first-run latency.** The first `import`/`fit` JIT-compiles (10–30s). It's not hung.
- **MAPE blows up near zero.** If `y` has zeros, MAPE → inf; use MAE/RMSE or `mase` instead.
- **TimeGPT data residency.** It uploads your series to Nixtla's servers. For confidential
  client data, prefer the fully-local StatsForecast path.
