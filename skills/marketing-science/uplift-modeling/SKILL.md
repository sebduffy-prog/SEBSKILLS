---
name: uplift-modeling
category: marketing-science
description: >
  Model who a campaign actually CHANGES — not who converts anyway — with uplift /
  heterogeneous-treatment-effect models, then target the persuadables and stop wasting
  spend on sure-things, lost-causes and sleeping-dogs. Reach for this on "who should we
  target", "propensity wastes budget", "incremental conversions per person",
  "persuadables", "uplift model", "CATE", "meta-learner", "S/T/X/R-learner", "uplift tree",
  "Qini curve", "AUUC", or "retention offer for churners". Grounds on Uber's causalml
  (Apache-2.0): meta-learners, uplift forests, Qini/AUUC eval, plus a numpy Qini scorer.
when_to_use:
  - Deciding WHO to target with an offer/email/ad so budget goes to persuadables only
  - You ran (or can run) a randomised holdout and want per-person incremental effect (CATE)
  - Comparing uplift models fairly with Qini curve / AUUC instead of accuracy or AUC
  - Retention: find churners a save-offer actually rescues, not ones who stay anyway
  - Segmenting a population into persuadables / sure-things / lost-causes / sleeping-dogs
  - Explaining why a propensity/lookalike model over-spends on people who convert regardless
when_not_to_use:
  - Measuring total campaign ROI or one aggregate lift number, not per-person — use the geo-incrementality-testing skill
  - Full channel spend decomposition and budget curves — use the marketing-mix-modeling skill
  - Crediting conversions across touchpoints in a funnel — use the multi-touch-attribution skill
  - No treatment/control randomisation exists at all — get an experiment first (geo-incrementality-testing)
keywords:
  - uplift-modeling
  - causal-inference
  - heterogeneous-treatment-effect
  - cate
  - meta-learner
  - s-learner
  - t-learner
  - x-learner
  - r-learner
  - uplift-tree
  - qini
  - auuc
  - persuadables
  - causalml
  - targeting
  - incrementality
similar_to:
  - geo-incrementality-testing
  - marketing-mix-modeling
  - multi-touch-attribution
inputs_needed: >
  Individual-level data from a randomised experiment: a treatment flag (0/1), a binary or
  continuous outcome (converted, retained, spend), and pre-treatment feature columns X. A
  known/estimable propensity e for X/R-learners (0.5 if a clean 50/50 A/B). Python 3.8+.
produces: >
  A fitted CATE / uplift model, per-person predicted uplift scores (tau_hat), a Qini curve
  + AUUC comparison across models, a targeting cut (top-k% by uplift), and a persuadable /
  sure-thing / lost-cause / sleeping-dog segmentation.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Uplift Modeling — target who the campaign actually changes

## When to use

Propensity and lookalike models answer "who is likely to convert?" — and then you spend
your budget on people who would have converted **anyway** (sure-things) and people who
never will (lost-causes). Uplift modeling answers the money question: **"who converts
*because* we contacted them?"** — the persuadables. It also flags **sleeping-dogs**:
people a contact actively annoys into *not* converting (unsubscribing, churning). You need
this whenever you have a randomised treatment/control holdout and a per-person action to
allocate (email, offer, ad, save-call).

The four segments (Kane/Lo quadrants), by control outcome × treatment outcome:

| | Buys if treated | Doesn't buy if treated |
|---|---|---|
| **Buys if control** | Sure-thing (waste) | Sleeping-dog (harm) |
| **Doesn't buy if control** | **Persuadable (target!)** | Lost-cause (waste) |

## Prerequisites

- **Randomisation is mandatory.** Uplift = E[Y|X,treat] − E[Y|X,control]. Without a
  randomised (or propensity-corrected) holdout, that difference is confounded and the
  model learns selection bias, not causal effect. If you have no experiment, stop and run
  one (geo-incrementality-testing / a proper A/B) first.
- **causalml** (Apache-2.0, Uber). Python 3.8+. It compiles Cython, so:
  ```bash
  pip install causalml            # brings numpy, scipy, scikit-learn, xgboost, cython
  # if the build fails, install numpy+cython FIRST, then causalml:
  pip install numpy cython && pip install causalml --no-build-isolation
  ```
  On this Mac (no brew, py3.9) the wheel usually installs cleanly; a source build needs
  Xcode command-line tools. If causalml won't install, you can still evaluate any
  externally-scored model with `scripts/qini.py` (numpy only).
- Data as a pandas DataFrame with feature columns `X`, a treatment array, and an outcome.

## Recipes

### 1. Meta-learners (start here) — model-agnostic, wrap any sklearn regressor

Meta-learners turn CATE estimation into ordinary supervised learning. Pick by data size
and treatment/control balance:

- **S-learner** — one model with treatment as a feature. Simplest; can under-fit uplift
  when the base model ignores the treatment column. Good baseline.
- **T-learner** — two separate models (treated, control); subtract. Robust with plenty of
  data in both arms; noisy when one arm is small.
- **X-learner** — imputes uplift and re-fits, weighting by propensity. **Best when
  treatment/control are imbalanced** (e.g. 10% treated). Usually the strongest default.
- **R-learner / DR-learner** — residualise outcome & treatment (Robinson); needs a good
  propensity model but is efficient and doubly-robust.

```python
from causalml.inference.meta import (
    BaseSRegressor, BaseTRegressor, BaseXRegressor, BaseRRegressor,
)
from xgboost import XGBRegressor

# X = features (n, p); treatment = array of labels; y = outcome; e = propensity
xl = BaseXRegressor(learner=XGBRegressor(max_depth=4, n_estimators=300, random_state=42))

# Aggregate ATE with confidence bounds (sanity check the experiment worked):
ate, lb, ub = xl.estimate_ate(X, treatment, y, p=e)
print(f"ATE {ate[0]:.4f}  95% CI [{lb[0]:.4f}, {ub[0]:.4f}]")

# Per-person uplift scores — THIS is what you target on:
tau_hat = xl.fit_predict(X, treatment, y, p=e)   # shape (n, 1)
```

`treatment` may be string labels; for the binary case use `control_name='control'` and a
single treatment label. `p`/`e` is the propensity (use a constant 0.5 array for a clean
50/50 A/B; estimate it with a classifier otherwise).

### 2. Uplift trees / forests — split directly on the treatment-effect gain

Tree models optimise a distributional-divergence split criterion (KL, Euclidean, or
Chi-squared) that maximises the *difference* in outcome between arms — so they carve out
persuadable segments directly and are naturally interpretable.

```python
from causalml.inference.tree import UpliftRandomForestClassifier
import pandas as pd

uf = UpliftRandomForestClassifier(
    n_estimators=100, max_depth=6, min_samples_leaf=100,
    evaluationFunction='KL', control_name='control', random_state=42,
)
uf.fit(X_df.values, treatment=treatment_str, y=y)   # treatment_str: 'control'/'treatment'
tau_hat = uf.predict(X_df.values)                    # per-person uplift
```

Use `UpliftTreeClassifier` for a single readable tree you can show a client; the forest
for accuracy. `min_samples_leaf` must be generous (each leaf needs enough treated AND
control rows to estimate a difference).

### 3. Evaluate with Qini / AUUC — NEVER accuracy or AUC

Classification metrics are meaningless here (you never observe an individual's true
uplift). Rank everyone by predicted uplift, then measure cumulative *incremental* outcome
vs random targeting. Bigger area (AUUC / Qini coefficient) = better ranking.

```python
from causalml.metrics import auuc_score, qini_score, plot_qini
import pandas as pd

df = pd.DataFrame({'y': y, 'w': treatment_binary})
df['xlearner'] = tau_hat_x
df['tlearner'] = tau_hat_t
df['random']   = np.random.rand(len(df))

print(qini_score(df, outcome_col='y', treatment_col='w'))   # one score per model column
print(auuc_score(df, outcome_col='y', treatment_col='w'))
plot_qini(df, outcome_col='y', treatment_col='w')           # visual model comparison
```

`qini_score` / `auuc_score` take a DataFrame whose non-`y`/`w` columns are each a model's
scores; they return a Series ranking the models. Always include a `random` column as the
floor. Signatures: `qini_score(df, outcome_col='y', treatment_col='w', treatment_effect_col='tau', normalize=True)`.

### 4. Quick model-free Qini check (no causalml) — `scripts/qini.py`

To sanity-check scores from ANY source (a vendor model, a spreadsheet) with numpy only:

```bash
python3 scripts/qini.py scored.csv --treatment w --outcome y --uplift tau_hat
python3 scripts/qini.py --selftest     # proves a good scorer beats a random one
```

It prints a normalized AUUC (model area minus random-diagonal area) and the Qini curve
points. Positive and well above 0 = the ranking finds real persuadables; near 0 = no
better than random targeting.

### 5. Turn scores into a targeting decision

```python
# Target the top-k% by predicted uplift, or everyone with uplift above a cost threshold.
k = 0.30
cutoff = np.quantile(tau_hat, 1 - k)
target = tau_hat.ravel() >= cutoff

# Segment for the client deck:
seg = np.where(tau_hat.ravel() > cost_of_contact, 'persuadable',
        np.where(tau_hat.ravel() < 0, 'sleeping_dog', 'do_not_contact'))
```

Only contact where **predicted uplift > cost/margin of the contact** — that is the actual
profit-max rule, not a fixed top-k. Negative-uplift people (sleeping-dogs) must be
*excluded*, which is uplift's biggest, most defensible win over propensity.

## Verify

- `python3 scripts/qini.py --selftest` prints `SELFTEST PASSED` (good scorer AUUC ≫ random).
- `estimate_ate` CI should exclude 0 if your experiment had a real average effect — if it
  straddles 0, there may be no signal to model; re-check the experiment before trusting CATE.
- On a **held-out test fold**, your model's `qini_score` must beat the `random` column. If
  it doesn't, uplift is unlearnable from these features — do not deploy.
- Cross-check segments: persuadables should show the largest treated−control gap when you
  bin by predicted uplift decile (a monotonic uplift-by-decile bar chart is the money slide).

## Pitfalls

- **No randomisation → garbage.** The #1 failure. Observational data makes the model learn
  who-was-selected, not who-is-persuaded. Correct with propensity (X/R-learner) only if
  treatment assignment is fully explained by observed X; otherwise you need an experiment.
- **Optimising AUC/accuracy instead of Qini.** A model can predict *conversion* perfectly
  and be useless for *uplift*. Rank and score on Qini/AUUC exclusively.
- **Tiny leaves / thin arms.** Uplift needs both treated and control in every segment.
  Small samples make CATE estimates wildly noisy — keep `min_samples_leaf` high and don't
  over-interpret narrow segments.
- **Ignoring sleeping-dogs.** If you only rank by "highest uplift" and blast the top decile,
  you still email the annoyed. Explicitly exclude negative-uplift people.
- **X-learner without a propensity for imbalanced data.** If treated ≠ 50%, pass a real
  estimated `p`; a constant 0.5 will bias the imputation.
- **Extrapolating the offer/period.** CATE is estimated for the tested offer, audience and
  window. A different discount or season is a new experiment, not a re-score.
- **Class imbalance in rare outcomes** (e.g. 1% conversion). Uplift signal is tiny; you
  need large samples and should report Qini confidence via bootstrap before acting.
