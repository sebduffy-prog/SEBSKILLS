---
name: excel-forecasting-formulas
category: data-analysis
description: >
  Build formula-only time-series forecasts inside an Excel workbook — no
  add-ins, no Python. Reach for this to project sales/traffic/demand forward
  with FORECAST.ETS (Holt-Winters triple exponential smoothing with
  auto-detected seasonality), draw prediction bands with FORECAST.ETS.CONFINT,
  fit linear/exponential trend lines with TREND/GROWTH/FORECAST.LINEAR/LINEST,
  read model accuracy (MASE/SMAPE/RMSE) via FORECAST.ETS.STAT, and lay out a
  clean monthly forecast table an analyst can audit cell by cell.
when_to_use:
  - You have a dated historical series (monthly sales, daily visits) and need N periods forecast forward using only worksheet formulas
  - The series has seasonality (weekly/monthly/yearly cycle) and you want Excel to detect and model it automatically
  - You need upper/lower confidence bounds around a forecast to shade a prediction interval on a chart
  - You want a straight-line or exponential-growth projection via regression (TREND, GROWTH, LINEST, FORECAST.LINEAR)
  - You must report forecast accuracy statistics (smoothing coefficients, RMSE, SMAPE) from the fitted model
when_not_to_use:
  - You are in Google Sheets or LibreOffice — FORECAST.ETS is Excel-2016+ only; use the xlsx or a Python/statsmodels approach instead
  - You need Monte-Carlo / stochastic simulation of outcomes — use excel-monte-carlo-formulas
  - The task is programmatic forecasting in Python (Prophet, statsmodels, sktime) — use polars-dataframes or a dedicated modelling stack, not worksheet formulas
  - You need to actually build/write the .xlsx file with these formulas embedded — pair this with the xlsx skill for file authoring
keywords:
  - excel
  - forecast
  - forecast.ets
  - holt-winters
  - exponential-smoothing
  - seasonality
  - time-series
  - confidence-interval
  - trend
  - linest
  - growth
  - regression
  - forecast.linear
  - smape
  - rmse
  - prediction-interval
similar_to:
  - excel-monte-carlo-formulas
  - statistical-testing
  - polars-dataframes
inputs_needed: Historical series (dated timeline + numeric values), how many periods to forecast, the seasonal cycle length if known (else let it auto-detect), and desired confidence level (default 95%).
produces: A set of ready-to-paste Excel formulas plus a laid-out forecast table (forecast, lower bound, upper bound, accuracy stats) the user drops into a workbook.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Excel Forecasting Formulas

Formula-only time-series forecasting in Excel. The `FORECAST.ETS` family
(Excel 2016+, Windows/Mac/365 — **not** Excel 2013, **not** Google Sheets)
runs Holt-Winters exponential triple smoothing with automatic seasonality
detection. Everything below is worksheet-native: no Analysis ToolPak, no VBA.

## When to use

Reach here when someone hands you a dated series in a workbook and wants it
projected forward with numbers they can trace. If the deliverable is the
`.xlsx` file itself, drive the file authoring with the **xlsx** skill and use
these formulas as the payload.

## Prerequisites

- **Excel 2016 or newer** (365, 2019, 2021, Mac 2016+). Check: type `=FOREC`
  and confirm `FORECAST.ETS` autocompletes. Legacy `FORECAST` (no `.ETS`)
  exists everywhere but does linear-only, no seasonality.
- A **timeline** column of dates/numbers with a *constant step* (every day,
  every month-start, etc.), no duplicates, no zero-length gaps. Missing
  *values* are fine (up to ~30%); missing *timeline points* are not.
- At least **2 full seasonal cycles** of history for `FORECAST.ETS` to detect
  seasonality (e.g. ≥24 months for a yearly cycle). Less than that → it falls
  back to non-seasonal.

## Function reference (exact signatures)

```
FORECAST.ETS(target_date, values, timeline, [seasonality], [data_completion], [aggregation])
FORECAST.ETS.CONFINT(target_date, values, timeline, [confidence_level], [seasonality], [data_completion], [aggregation])
FORECAST.ETS.SEASONALITY(values, timeline, [data_completion], [aggregation])
FORECAST.ETS.STAT(values, timeline, statistic_type, [seasonality], [data_completion], [aggregation])
FORECAST.LINEAR(x, known_ys, known_xs)
TREND(known_ys, [known_xs], [new_xs], [const])
GROWTH(known_ys, [known_xs], [new_xs], [const])
LINEST(known_ys, [known_xs], [const], [stats])
```

Optional arguments (same meaning across the ETS family):

| Arg | Default | Values |
|-----|---------|--------|
| `seasonality` | `1` = auto-detect | `0` = none (linear); positive integer = cycle length (e.g. `12` months, `7` days); max 8760 |
| `data_completion` | `1` = interpolate missing (avg of neighbours) | `0` = treat gaps as zeros |
| `aggregation` | `1` = AVERAGE | `2` COUNT, `3` COUNTA, `4` MAX, `5` MEDIAN, `6` MIN, `7` SUM — used when a timeline value repeats |
| `confidence_level` | `0.95` | 0 < x < 1 |

`FORECAST.ETS.STAT` `statistic_type`: `1` Alpha (base smoothing), `2` Beta
(trend smoothing), `3` Gamma (seasonal smoothing), `4` MASE, `5` SMAPE,
`6` MAE, `7` RMSE, `8` step size (detected season length).

## Recipe 1 — Seasonal forecast with confidence band

Layout: dates in `A2:A37` (36 months), values in `B2:B37`. Future dates you
want to forecast go in `A38:A49` (next 12 months). Then:

```
# C38 — the point forecast (auto seasonality):
=FORECAST.ETS(A38, $B$2:$B$37, $A$2:$A$37)

# D38 — the +/- half-width of the 95% interval:
=FORECAST.ETS.CONFINT(A38, $B$2:$B$37, $A$2:$A$37, 0.95)

# E38 — lower bound,  F38 — upper bound:
=C38 - D38
=C38 + D38
```

Fill `C38:F38` down through row 49. Chart `B` + `C` (history + forecast) as one
line, then add `E`/`F` as a shaded band. Force a monthly cycle instead of
auto-detect by adding `,12` as the 4th arg to both ETS calls.

## Recipe 2 — Non-seasonal (pure trend) ETS

If the series has trend but no cycle, kill seasonality so it doesn't
hallucinate one:

```
=FORECAST.ETS(A38, $B$2:$B$37, $A$2:$A$37, 0)
```

`seasonality = 0` makes it double-exponential (Holt) smoothing — level + trend
only.

## Recipe 3 — Linear regression projection

For a straight-line fit (least squares), any of these:

```
# Single point, x = new period index in A38:
=FORECAST.LINEAR(A38, $B$2:$B$37, $A$2:$A$37)

# Spill the whole future range at once (dynamic-array Excel):
=TREND($B$2:$B$37, $A$2:$A$37, A38:A49)

# Slope and intercept explicitly:
=SLOPE($B$2:$B$37,$A$2:$A$37)      # per-period change
=INTERCEPT($B$2:$B$37,$A$2:$A$37)
```

Note timeline dates work as x-values because Excel stores dates as serial
numbers. For evenly-spaced periods you can also use `1,2,3…` indices.

## Recipe 4 — Exponential growth projection

For compounding growth (revenue, users), fit `y = b·m^x`:

```
=GROWTH($B$2:$B$37, $A$2:$A$37, A38:A49)     # spills future values
```

Beware: `GROWTH` fails on zero or negative y-values (it logs them internally).

## Recipe 5 — Model diagnostics

```
=FORECAST.ETS.SEASONALITY($B$2:$B$37,$A$2:$A$37)      # season length Excel detected (0 = none)
=FORECAST.ETS.STAT($B$2:$B$37,$A$2:$A$37,5)            # SMAPE (5) — lower is better
=FORECAST.ETS.STAT($B$2:$B$37,$A$2:$A$37,7)            # RMSE (7), same units as the series
=FORECAST.ETS.STAT($B$2:$B$37,$A$2:$A$37,1)            # Alpha — near 1 = weights recent points hard
```

`FORECAST.ETS.SEASONALITY` returning `0` (or `1`) confirms Excel found no
cycle — that explains a flat-looking ETS forecast, and tells you Recipe 2/3 is
the honest model.

For a full regression readout in one shot, array-enter `LINEST` with stats on:

```
=LINEST($B$2:$B$37, $A$2:$A$37, TRUE, TRUE)
```

Spills a 2×5 block: slope & intercept (row 1), their standard errors (row 2),
then R², standard error of y, F-stat, df, and regression/residual sums of
squares. In legacy Excel select a 5-row×2-col range and press
Ctrl+Shift+Enter.

## Deliverable

Ship a real workbook, not pasted formulas in chat. Default output:
`~/Desktop/forecast_<series>.xlsx`, built with **openpyxl** — write each
formula string into its cell (`ws["C38"] = "=FORECAST.ETS(A38,$B$2:$B$37,$A$2:$A$37)"`),
lay out the history + forecast/lower/upper/stats columns, and pair with the
**xlsx** skill for authoring. Final step: confirm the file exists, reopen it
with openpyxl and spot-check that the forecast cells hold `=FORECAST.ETS…`
strings (not stale values or `#N/A`), and that the table has the expected row
count. If the historical series isn't supplied yet, still ship the workbook as
a scaffold — headers, the formula layout, and an "awaiting data" note in the
value column — never end with formulas quoted only in prose.

## Verify

- Forecast the **last known** period as if it were unknown and compare to the
  actual: `=FORECAST.ETS(A37,$B$2:$B$36,$A$2:$A$36)` vs `B37`. A wild miss
  means wrong seasonality or too little history.
- `FORECAST.ETS.STAT(...,5)` (SMAPE) should typically be well under ~0.3 for a
  usable model; if it's high, the series is noise-dominated — say so, don't
  dress it up.
- Confirm the timeline step is constant (`=A3-A2` copied down should be one
  value) — irregular steps silently corrupt ETS. `#NUM!` on the ETS calls is
  the classic symptom of duplicate or non-monotonic timeline entries.
- Sanity-check the band: `FORECAST.ETS.CONFINT` half-width should *widen* the
  further out you forecast. If it's flat, you probably passed a wrong arg
  position.

## Pitfalls

- **Wrong Excel / wrong app.** Excel 2013 and Google Sheets have only the
  legacy `FORECAST` (linear). Don't promise ETS output there — route to the
  xlsx skill or a Python forecaster.
- **`#N/A` from `FORECAST.ETS`** almost always = timeline and values arrays
  are different lengths, or the timeline has duplicates/zero step.
- **Auto-seasonality guesses too aggressively.** With noisy short series it can
  invent a cycle. If `FORECAST.ETS.SEASONALITY` returns something implausible,
  pin `seasonality` explicitly (`12`, `7`, or `0`).
- **`data_completion` default silently interpolates.** If your blanks are true
  zeros (e.g. no sales that day), pass `0` for the 5th arg or you inflate the
  forecast.
- **CONFINT is a half-width, not a bound.** You must add/subtract it from the
  `FORECAST.ETS` value yourself — it is not the upper limit on its own.
- **Dates must be real dates**, not text that looks like dates. `=ISNUMBER(A2)`
  should be `TRUE`. Text timelines throw `#VALUE!`.
- **Don't hand-roll Holt-Winters in cells.** These functions exist and are
  tested; a manual smoothing lattice is error-prone and unmaintainable (KISS).
