---
name: gradient-boosting-tabular
category: ml
description: >
  Build a strong tabular ML model with gradient-boosted trees (XGBoost / LightGBM / CatBoost) for churn,
  propensity, lead-scoring, conversion and pricing — the workhorse that beats deep learning on most business
  tables — with proper validation, class-imbalance handling, categorical features, early stopping, and SHAP
  explanations. Use this whenever someone says "predict churn / conversion / propensity", "which customers will
  X", "score my leads", "feature importance", "XGBoost / LightGBM / CatBoost", or has a CSV of rows+label and
  wants a predictive model they can trust and explain. Reach for it for any "predict a column from the others".
when_to_use:
  - You have a tabular dataset (CSV/DataFrame) with a target column and want to predict it
  - Churn, propensity, lead-scoring, conversion, fraud, pricing, or risk models
  - You need SHAP feature importance / explanations for stakeholders
  - Baseline that reliably beats neural nets on structured business data
when_not_to_use:
  - Tiny dataset (<1k rows) where a foundation model wins → use tabular-foundation-model
  - You need calibrated prediction intervals / guaranteed coverage → use conformal-prediction
  - Forecasting a time series → use time-series-forecasting
  - Deep learning on images/text/graphs → use neural-net-from-scratch or build-train-gnn
keywords: [xgboost, lightgbm, catboost, gradient boosting, tabular, churn, propensity, lead scoring, classification, regression, shap, feature importance, class imbalance, early stopping, gbdt, predictive model]
similar_to: [tabular-foundation-model, conformal-prediction, ml-model-eval, statistical-testing, data-quality-validation]
inputs_needed:
  - The dataset (CSV/DataFrame) and which column is the target
  - Task type (binary/multiclass classification or regression) and the metric that matters
  - Any known categorical columns and whether classes are imbalanced
  - Whether stakeholders need SHAP explanations
produces: A trained, validated gradient-boosting model + metrics + SHAP explanation plots/values
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Gradient-boosting for tabular data

Gradient-boosted trees are still the best default for business tables. This gets you a validated, explainable
model without over-engineering.

## When to use

Any "predict this column from the others" on structured data. For <1k rows try `tabular-foundation-model`; for
guaranteed-coverage intervals wrap it with `conformal-prediction`.

## Prerequisites

```bash
python3 -m pip install --user xgboost lightgbm catboost scikit-learn shap pandas
```
All three boosters work on py3.9. Pick one: **LightGBM** (fast, big data), **CatBoost** (best with many
categoricals, no encoding needed), **XGBoost** (ubiquitous, robust).

## Train (LightGBM, binary churn example)

```python
import lightgbm as lgb, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score

df = pd.read_csv("customers.csv")
y = df.pop("churned")
X = df
# mark categoricals so LightGBM/CatBoost handle them natively (no one-hot)
for c in X.select_dtypes("object"): X[c] = X[c].astype("category")

Xtr, Xva, ytr, yva = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
model = lgb.LGBMClassifier(
    n_estimators=2000, learning_rate=0.03, num_leaves=31,
    subsample=0.8, colsample_bytree=0.8,
    class_weight="balanced",          # handle imbalance
    random_state=42)
model.fit(Xtr, ytr, eval_set=[(Xva, yva)], eval_metric="auc",
          callbacks=[lgb.early_stopping(100), lgb.log_evaluation(0)])

p = model.predict_proba(Xva)[:, 1]
print("AUC", round(roc_auc_score(yva, p), 4), "| PR-AUC", round(average_precision_score(yva, p), 4))
```

**Validation that isn't kidding itself:** stratified split (or `StratifiedKFold` for small data); never fit any
transform on the full set before splitting (leakage). For imbalanced targets report **PR-AUC**, not just
accuracy. Use **early stopping** on a validation set — don't hand-pick `n_estimators`.

## Explain with SHAP

```python
import shap
expl = shap.TreeExplainer(model)
sv = expl.shap_values(Xva)
shap.summary_plot(sv, Xva)                 # global feature importance + direction
shap.plots.waterfall(shap.Explanation(sv[0], expl.expected_value, Xva.iloc[0]))  # one customer
```
SHAP gives per-prediction, signed contributions — far more trustworthy for stakeholders than the built-in
`feature_importances_`.

## Verify

- AUC/PR-AUC on the held-out set is materially above a majority-class baseline.
- SHAP summary makes business sense (top drivers are plausible, not an ID/leak column).
- Re-run with a different seed → metrics stable (no lucky split).

## Pitfalls

- **Leakage** — a feature that encodes the future (e.g. `cancellation_date`) inflates AUC to ~1.0. Audit top SHAP drivers.
- **Accuracy on imbalanced data lies** — a 97%-no-churn set scores 97% by predicting "no". Use PR-AUC / recall at a threshold.
- **Categoricals** — don't one-hot high-cardinality columns; let LightGBM/CatBoost handle them natively.
- **Calibration** — raw scores aren't probabilities; wrap with `CalibratedClassifierCV` or `conformal-prediction` if you need true probabilities/intervals.
- **Tuning** — start with the defaults above; only reach for Optuna if the baseline isn't good enough.
