---
name: tabular-foundation-model
category: ml
description: >
  Predict on small tabular datasets with TabPFN — a pretrained transformer that does in-context tabular
  classification/regression in ONE forward pass, no training and no hyperparameter tuning, and routinely beats a
  tuned XGBoost on datasets up to a few thousand rows. Use this whenever someone has a SMALL table (hundreds to a
  few thousand rows) and wants an instant strong model, says "TabPFN", "small data prediction", "no time to tune",
  "quick baseline on this CSV", or is prototyping a churn/propensity/scoring model on limited data. Reach for it
  before hand-tuning trees when the row count is low.
when_to_use:
  - A small tabular dataset (roughly <10k rows, <500 features) needing a strong model fast
  - You want a no-training, no-tuning baseline that often beats tuned gradient boosting on small data
  - Rapid prototyping / a strong reference model to compare against
  - Few-shot tabular prediction where labelled rows are scarce
when_not_to_use:
  - Large datasets (>10k-50k rows) → use gradient-boosting-tabular
  - You need SHAP-style per-feature explanations for stakeholders → use gradient-boosting-tabular
  - Guaranteed-coverage prediction intervals → wrap with conformal-prediction
  - Time-series forecasting → use time-series-forecasting
keywords: [tabpfn, tabular foundation model, in-context learning, small data, no training, prior labs, transformer tabular, quick baseline, few-shot, classification, regression, priorlabs]
similar_to: [gradient-boosting-tabular, conformal-prediction, ml-model-eval]
inputs_needed:
  - The small dataset (CSV/DataFrame) and the target column
  - Task type (classification or regression)
  - Row/feature counts (to confirm it's in TabPFN's sweet spot)
produces: Instant predictions + probabilities from a pretrained tabular transformer, with a held-out score
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Tabular foundation model (TabPFN)

TabPFN is a transformer pretrained on synthetic tabular tasks that predicts a new dataset **in one forward pass**
— you pass train rows + test rows and it returns predictions. No fitting loop, no tuning. On small data it is a
remarkably strong, instant baseline.

## When to use

Small tables where you want a top-tier model now. Above ~10k rows switch to `gradient-boosting-tabular`.

## Prerequisites

```bash
python3 -m pip install --user tabpfn
```
Runs on CPU for small data; a GPU speeds up larger inputs. First run downloads the pretrained weights.

## Use it

```python
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from tabpfn import TabPFNClassifier          # TabPFNRegressor for regression

df = pd.read_csv("small_customers.csv")
y = df.pop("churned"); X = df
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=0)

clf = TabPFNClassifier()          # no hyperparameters to set
clf.fit(Xtr, ytr)                 # "fit" just stores the context — no training
proba = clf.predict_proba(Xte)[:, 1]
print("AUC", round(roc_auc_score(yte, proba), 4))
```

`fit` is instant (it just caches the training rows as context); the compute happens at `predict`. Compare it
head-to-head with `gradient-boosting-tabular` — on small data TabPFN often wins with zero effort.

## Verify

- It produces predictions and a held-out AUC/accuracy above a majority baseline.
- On a dataset in its sweet spot, it matches or beats a quick LightGBM baseline.
- Row/feature counts are within the supported range (very large inputs degrade or need chunking).

## Pitfalls

- **Size limits** — TabPFN targets small data; very large row/feature counts are slow or unsupported. Know the current version's caps.
- **Not a black-box explainer** — for signed per-feature stakeholder explanations use `gradient-boosting-tabular` + SHAP.
- **Preprocessing** — handle obvious NaNs/encodings; it's robust but not magic.
- **Licensing** — check TabPFN's licence for commercial use before shipping in a client product.
- **Probabilities** — for guaranteed coverage/calibration wrap with `conformal-prediction`.
