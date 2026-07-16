---
name: excel-monte-carlo-formulas
category: data-analysis
description: >
  Run a Monte-Carlo simulation in Excel using formulas ONLY — no VBA, no @RISK, no add-ins. Draw thousands of RAND()-driven trials, sample any distribution by inverse-CDF (normal, lognormal, triangular, PERT, uniform, Bernoulli, discrete, exponential, beta, gamma), spill the whole trial grid with RANDARRAY/MAKEARRAY, then read out mean, P5/P50/P95, VaR, and probability-of-exceedance. Use when the user wants uncertainty analysis, risk modelling, "simulate this forecast", NPV/cost/schedule risk, confidence bands, or a portable spreadsheet an analyst can open without macros enabled.
when_to_use:
  - User wants a Monte-Carlo / probabilistic simulation that lives entirely in an .xlsx with no macros or paid add-ins
  - User has a deterministic model (NPV, budget, project cost, demand) and wants to make inputs uncertain and see the output distribution
  - User needs percentile outputs (P10/P50/P90), value-at-risk, or probability that an output exceeds a threshold
  - User wants to sample a named distribution (triangular, PERT, lognormal, discrete) by inverse-CDF without a stats library
  - User must share the workbook with people who cannot enable VBA (locked-down corp / Google-Sheets-imported / Excel on the web)
when_not_to_use:
  - User wants the simulation in Python/pandas/numpy rather than spreadsheet formulas → use polars-dataframes or statistical-testing
  - User wants a time-series point forecast, not uncertainty sampling → use excel-forecasting-formulas
  - User needs >100k trials, MCMC, or heavy correlated sampling that Excel recalc can't take → use a Python numpy/scipy notebook
  - User is fine with a paid add-in (@RISK, Crystal Ball) and wants its GUI → this skill deliberately avoids those
keywords:
  - excel
  - monte-carlo
  - simulation
  - rand
  - randarray
  - inverse-cdf
  - percentile
  - norm.inv
  - triangular
  - risk-analysis
  - dynamic-arrays
  - makearray
  - probability
  - var
  - no-vba
  - lambda
similar_to:
  - excel-forecasting-formulas
  - statistical-testing
  - polars-dataframes
  - synthetic-data-generation
inputs_needed:
  - The deterministic model / output formula to make probabilistic (e.g. revenue − cost, or NPV of a cashflow)
  - Which inputs are uncertain, each with a distribution + parameters (min/mode/max, mean/sd, p, etc.)
  - Number of trials (typically 1,000–10,000) and which output percentiles / thresholds matter
  - Target: Excel 365 (RANDARRAY/MAKEARRAY/LAMBDA available) or an older/Sheets version (fall back to a fill-down column + Data Table)
produces: A macro-free workbook that draws N trials per uncertain input via inverse-CDF, spills the output distribution, and reports mean, SD, P5/P50/P95, VaR, and P(output > threshold).
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Excel Monte-Carlo (formulas only)

Monte-Carlo in a spreadsheet with **zero VBA and zero add-ins**. The whole trick is: `RAND()` gives a uniform draw in [0,1); pushing that draw through a distribution's **inverse CDF** (quantile function) turns it into a sample from that distribution; do it N times, spill the results, and summarise. Because `RAND`/`RANDARRAY` are **volatile**, every recalc (any edit, or `F9`) reruns the whole simulation.

## When to use

Reach for this when someone wants risk/uncertainty analysis in a file that *must* stay portable — no macros enabled, no @RISK licence, opens fine on Excel for the web or after a Google Sheets import. If the deliverable is Python, use `polars-dataframes` + numpy instead; if it's a point forecast (trend/seasonality) not an uncertainty band, use `excel-forecasting-formulas`.

## Prerequisites

- **Excel 365 / 2021+** for the clean path (`RANDARRAY`, `MAKEARRAY`, `LAMBDA`, `SEQUENCE`, dynamic-array spill). Check by typing `=RANDARRAY(3)` — if it spills 3 numbers you're good.
- **Older Excel / Google Sheets**: no `RANDARRAY`. Use the fallback — one `RAND()`-based formula filled down a column, or a one-variable **Data Table** (What-If Analysis). Sheets has `RAND`, `NORMINV`, `PERCENTILE` but not `MAKEARRAY`.
- Nothing to install. This is all built-in worksheet functions.
- To author the file programmatically, use the **xlsx** skill (openpyxl) and write these strings into cells.

## Core idea: inverse-CDF sampling

`sample = INVERSE_CDF( RAND() , params )`. Excel ships the inverse CDF for most named distributions:

| Distribution | Formula for one draw | Notes |
|---|---|---|
| Uniform(a,b) | `=a+(b-a)*RAND()` | flat between a and b |
| Normal(μ,σ) | `=NORM.INV(RAND(),mu,sigma)` | `NORM.S.INV(RAND())` for standard |
| Lognormal(μ,σ of ln) | `=LOGNORM.INV(RAND(),mu,sigma)` | μ,σ are of the underlying normal |
| Exponential(λ) | `=-LN(1-RAND())/lambda` | mean = 1/λ; no built-in inverse |
| Bernoulli(p) | `=IF(RAND()<p,1,0)` | 1 with prob p |
| Beta(α,β) | `=BETA.INV(RAND(),alpha,beta)` | on [0,1]; add A,B args to rescale |
| Gamma(α,θ) | `=GAMMA.INV(RAND(),alpha,theta)` | shape α, scale θ |
| Triangular(a,c,b) | see below | min a, mode c, max b — no built-in |
| PERT(a,c,b) | Beta reparam — see below | smoother triangular for estimates |
| Discrete/empirical | `=INDEX(vals,MATCH(RAND(),cumP,1)+1)` | cumP = cumulative probabilities |

**Triangular** (min `a`, mode `c`, max `b`) — piecewise inverse CDF, `u=RAND()`:
```
=LET(u,RAND(), Fc,(c-a)/(b-a),
  IF(u<Fc, a+SQRT(u*(b-a)*(c-a)),
           b-SQRT((1-u)*(b-a)*(b-c))))
```
**PERT** (Beta-PERT, λ=4) — better than triangular when a,c,b are expert estimates:
```
mu    = (a + 4*c + b)/6
alpha = 6*((mu-a)/(b-a))
beta  = 6*((b-mu)/(b-a))
draw  = a + BETA.INV(RAND(), alpha, beta)*(b-a)
```

## Recipe A — spilled trial grid (Excel 365, recommended)

Say revenue = `units × price − fixedCost`, where **units** ~ Triangular(800,1000,1400) and **price** ~ Normal(50, 6). Lay it out with named ranges or fixed params, then build one **spilled column of N trial outputs**.

1. Put N in a cell, e.g. `F1 = 10000` (trials).
2. Draw N units and N prices as spilled arrays. `RANDARRAY(N)` gives N independent uniforms; wrap each in its inverse-CDF. Because triangular has no built-in inverse, drive it with `MAKEARRAY`:
```
units:  =MAKEARRAY(F1,1, LAMBDA(r,c, LET(u,RAND(), Fc,(1000-800)/(1400-800),
          IF(u<Fc, 800+SQRT(u*(1400-800)*(1000-800)),
                   1400-SQRT((1-u)*(1400-800)*(1400-1000))))))
price:  =NORM.INV(RANDARRAY(F1),50,6)        (spills N prices)
```
3. Compute the output per trial as an **array expression** referencing the two spills (`H2#` and `I2#` are spill refs):
```
output: =H2# * I2# - 20000
```
This spills N revenues in one cell. That column IS your distribution.

4. Summarise the output spill (call it `J2#`):
```
Mean      =AVERAGE(J2#)
Std dev   =STDEV.S(J2#)
P5        =PERCENTILE.INC(J2#,0.05)
Median    =PERCENTILE.INC(J2#,0.5)
P95       =PERCENTILE.INC(J2#,0.95)
VaR@95    =AVERAGE(J2#)-PERCENTILE.INC(J2#,0.05)
P(loss)   =AVERAGE(--(J2#<0))          probability output is negative
P(>25k)   =AVERAGE(--(J2#>25000))      probability of exceedance
```
`AVERAGE(--(condition))` = fraction of trials meeting the condition = a probability. Press `F9` to redraw the entire simulation.

## Recipe B — fill-down column (any Excel / Google Sheets, no dynamic arrays)

1. Column A rows 2:10001 = one output formula per trial, each with its own `RAND()`s inline, e.g.
   `=(800+ ...triangular...) * NORM.INV(RAND(),50,6) - 20000`. Fill down 10,000 rows.
2. Summary cells use ordinary range refs: `=AVERAGE(A2:A10001)`, `=PERCENTILE.INC(A2:A10001,0.05)`, `=COUNTIF(A2:A10001,"<0")/10000`.
   (Google Sheets: `PERCENTILE`, `NORMINV`, `COUNTIF` — same idea, dotless names.)

**Data Table variant:** keep a single-cell model with one `RAND()` driver, list trial indices 1..N down a column, and use *Data → What-If → Data Table* with a blank/empty column-input cell so each row forces an independent recalc. Fully macro-free and works in legacy Excel.

## Freezing a run

`RAND` reshuffles on every recalc, so charts jump. To pin one draw: select the trial spill/column → Copy → **Paste Special → Values**. Now the numbers are static and safe to chart or share. Keep the live formula version on a separate sheet to re-roll later.

## Histogram / S-curve

Select the frozen output column → Insert → **Histogram** chart (365) for the PDF shape. For a cumulative S-curve, sort the values, put `=(ROW()-1)/N` beside them as the empirical CDF, and plot value (x) vs that fraction (y) — read any percentile straight off it.

## Correlated inputs (advanced)

Independent draws overstate diversification. To induce correlation, draw a matrix of standard normals `Z = NORM.S.INV(RANDARRAY(N,k))`, and post-multiply by the transpose of the **Cholesky factor** L of the target correlation matrix: `=MMULT(Z, TRANSPOSE(L))`. Then map each correlated normal column to its target marginal via that marginal's CDF→inverse-CDF (Gaussian copula). Building L in pure formula is fiddly; for small k hard-code it, otherwise fall back to numpy — flag this to the user rather than faking it.

## Deliverable

Always ship a real `.xlsx` — never leave the simulation as chat-only prose. Author it with the **xlsx** skill (openpyxl), writing the formula strings above into actual cells so the file recalcs when opened. Default path `~/Desktop/monte_carlo_simulation.xlsx` unless the user names one. It must contain: an **Inputs** sheet (each uncertain input's distribution + params), a **Trials** sheet (the spilled/filled-down grid from Recipe A or B), and a **Summary** sheet (mean, SD, P5/P50/P95, VaR, P(threshold)) plus a histogram/S-curve.

Final check before you hand it over: the file exists on disk, opens in Excel without repair, and the Summary numbers are sane (P5 < median < P95, probabilities in [0,1], normal-draw mean ≈ its μ). If the deterministic model or the input distributions aren't supplied yet, still build and deliver the workbook scaffold — sheets, headings, and the formula skeleton in place with an "awaiting inputs" note in the parameter cells — rather than ending in conversation.

## Verify

- `=RANDARRAY(3)` spills 3 numbers → dynamic arrays available (else use Recipe B).
- Sanity-check a normal draw: `=AVERAGE(NORM.INV(RANDARRAY(50000),50,6))` ≈ 50 and `=STDEV.S(...)` ≈ 6.
- Triangular mean check: `AVERAGE` of a Triangular(800,1000,1400) column ≈ `(800+1000+1400)/3` = 1066.7.
- Increase N (1k → 10k) and confirm the P5/P95 stabilise — if they still swing a lot, you need more trials.
- `AVERAGE(--(J2#<0))` must sit in [0,1]; if it's blank you referenced the wrong spill anchor.

## Pitfalls

- **Volatility churn:** thousands of `RAND()`s recalc on *every* keystroke and can make the sheet sluggish. Set *Formulas → Calculation Options → Manual* and recalc with `F9` on demand; freeze to values before sharing.
- **Wrong inverse:** `NORM.INV(RAND(),μ,σ)` is right; `NORM.DIST` is the CDF (forward) — don't sample with it. Exponential and triangular have **no** built-in inverse, so use the closed forms above.
- **Lognormal params:** `LOGNORM.INV(p,μ,σ)` wants μ,σ of the *underlying normal* (ln-space), not the mean/sd of the lognormal itself. Convert first or your scale is wrong.
- **Correlation ignored:** independent sampling of inputs that really move together (price & cost, adjacent-year demand) understates tail risk. Note it even if you don't model it.
- **PERCENTILE.INC vs .EXC:** `.INC` includes the 0/1 ends (matches most reporting); `.EXC` excludes them and errors for k outside (0,1). Pick one and be consistent.
- **Discrete lookup off-by-one:** with `MATCH(u,cumP,1)` ensure `cumP` starts at 0 and the `INDEX` offset lands on the right value; test that each category's frequency ≈ its probability.
- **Too few trials:** 100 trials give noisy percentiles. Use ≥1,000 (≥10,000 for tail P1/P99). Report that P95 has Monte-Carlo error that shrinks ~1/√N.
- **Seeds:** Excel `RAND` has no seed. For a reproducible run, freeze to values once and keep that snapshot — you cannot reproduce a specific draw by re-seeding.
