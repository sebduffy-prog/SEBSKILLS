---
name: conformal-prediction
category: ml
description: >
  Wrap ANY trained model (sklearn, XGBoost, TabPFN, even an API model) with conformal prediction to get
  distribution-free, calibrated uncertainty — prediction intervals for regression with guaranteed coverage (e.g.
  "90% of true values fall inside"), or prediction SETS for classification — using MAPIE. Use this whenever
  someone says "prediction intervals", "how confident is the model", "calibrated uncertainty", "coverage
  guarantee", "error bars on predictions", "conformal", or needs to ship a model whose uncertainty stakeholders
  can trust. Reach for it to turn point predictions into honest ranges.
when_to_use:
  - You have a trained model and need prediction intervals or sets with a coverage guarantee
  - Stakeholders ask "how sure is it?" and you need a defensible answer, not a raw score
  - Regression where a range matters more than a single number (forecasts, pricing, estimates)
  - Classification where you want a set of plausible labels at a confidence level, and to flag "not sure"
when_not_to_use:
  - You just need the point prediction → use gradient-boosting-tabular / tabular-foundation-model
  - Bayesian posterior/credible intervals specifically → use a Bayesian model
  - Time-series intervals from the forecaster itself → use time-series-forecasting
  - Validating an A/B test result → use experiment-validity-audit
keywords: [conformal prediction, mapie, prediction intervals, coverage, calibrated uncertainty, distribution-free, prediction sets, error bars, confidence, split conformal, cqr, uncertainty quantification]
similar_to: [gradient-boosting-tabular, tabular-foundation-model, ml-model-eval, time-series-forecasting]
inputs_needed:
  - A trained model (or training data to fit one) and a held-out calibration set
  - Target coverage level (e.g. 90%)
  - Task type — regression (intervals) or classification (sets)
produces: Calibrated prediction intervals (regression) or prediction sets (classification) with verified coverage
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Conformal prediction (MAPIE)

Conformal prediction converts any model's outputs into intervals/sets with a **finite-sample coverage
guarantee** — no distributional assumptions. Held-out calibration data does the work, so it wraps models you
didn't train (including API models) as long as you can score a calibration set.

## When to use

Whenever a point prediction isn't enough and "how confident?" needs a defensible answer.

## Prerequisites

```bash
python3 -m pip install --user mapie scikit-learn
```

## Regression — intervals with guaranteed coverage

```python
from mapie.regression import MapieRegressor
from sklearn.ensemble import RandomForestRegressor
import numpy as np

# X_train/y_train, X_cal/y_cal (calibration), X_test
mapie = MapieRegressor(estimator=RandomForestRegressor(), method="plus", cv="split")
mapie.fit(X_train, y_train)                      # (or prefit=an already-trained model)
y_pred, y_pis = mapie.predict(X_test, alpha=0.1) # alpha=0.1 -> 90% target coverage
lower, upper = y_pis[:, 0, 0], y_pis[:, 1, 0]
# empirical coverage on a labelled test set:
cov = np.mean((y_test >= lower) & (y_test <= upper))
print("target 90%  | empirical", round(cov*100, 1), "%  | mean width", round(np.mean(upper-lower), 2))
```
For heteroskedastic data use **CQR** (`method="quantile"`) so interval width varies with difficulty.

## Classification — prediction sets

```python
from mapie.classification import MapieClassifier
mc = MapieClassifier(estimator=clf, method="lac", cv="prefit")
mc.fit(X_cal, y_cal)
_, y_sets = mc.predict(X_test, alpha=0.1)   # 90% coverage
# y_sets[i] is a boolean mask of plausible labels; a big set = "model unsure"
```

## Verify

- **Empirical coverage ≈ target** on a fresh labelled set (e.g. ~90% for alpha=0.1). This is the whole point — check it.
- Intervals are as **narrow** as possible for that coverage (tighter = more useful); CQR narrows easy cases.
- Classification sets shrink to 1 label when confident, grow when ambiguous.

## Pitfalls

- **Exchangeability** — coverage holds if calibration and test data are exchangeable; it breaks under distribution shift (retime/re-calibrate).
- **Coverage is marginal**, not per-group — check coverage within important segments too (conditional coverage).
- **Calibration set must be held out** — never reuse training rows, or coverage is optimistic.
- **Width matters** — a 100%-coverage interval that's infinitely wide is useless; report coverage AND width together.
