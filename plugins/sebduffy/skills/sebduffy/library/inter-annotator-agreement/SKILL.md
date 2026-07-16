---
name: inter-annotator-agreement
category: verification
description: >-
  Measure how much your human labellers (or LLM judges) actually agree, using
  Cohen's kappa, Fleiss' kappa, and Krippendorff's alpha — then route the
  disagreements to a human adjudication queue. Trigger when validating a gold
  set, calibrating an LLM judge against humans, checking rater reliability
  before training/eval, computing kappa/alpha, or deciding whether labels are
  trustworthy. Turns "we labelled some data" into a defensible reliability
  number with a confidence interval and a fix-list.
when_to_use:
  - Validating a hand-labelled gold/eval set before you trust or ship it
  - Checking whether an LLM judge is calibrated against human annotators
  - Two raters, one confusion matrix — need Cohen's kappa (weighted for ordinal)
  - Many raters or missing labels — need Fleiss' kappa or Krippendorff's alpha
  - Building an adjudication queue of the items annotators disagreed on
  - Reporting a reliability figure with a bootstrap confidence interval
when_not_to_use:
  - Auditing whether an LLM judge is systematically biased (position/verbosity/self-preference) — use llm-judge-bias-audit
  - Curating or cleaning the eval dataset itself rather than scoring rater agreement — use eval-dataset-curation
  - Checking a single statistical claim's arithmetic/p-value — use stat-check-review
  - Plain accuracy vs a known ground truth (no multiple raters) — just use a confusion matrix / sklearn.metrics
keywords:
  - inter-annotator agreement
  - inter-rater reliability
  - cohens kappa
  - fleiss kappa
  - krippendorff alpha
  - weighted kappa
  - annotation
  - adjudication
  - gold set
  - llm judge calibration
  - reliability
  - statsmodels
  - krippendorff
  - kappa
  - ordinal
  - bootstrap ci
similar_to:
  - eval-dataset-curation
  - llm-judge-bias-audit
  - stat-check-review
  - self-consistency-check
  - claim-verifier
inputs_needed: >-
  Per-item labels from 2+ raters. Ideal: a long CSV with columns unit,rater,label
  (one row per rating). A rater may be a human or an LLM judge. Ordinal scales
  need their category order.
produces: >-
  Krippendorff's alpha (+ bootstrap 95% CI), Fleiss' kappa, mean pairwise
  Cohen's kappa, a plain-English reliability verdict, and an adjudication-queue
  CSV of the disagreed items with vote breakdowns.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Inter-Annotator Agreement

Raw percent-agreement lies: if 90% of items are one class, two raters who guess
that class agree 81% of the time by chance alone. Chance-corrected metrics
(kappa, alpha) tell you how much agreement is *real*. This skill computes them
correctly, attaches a confidence interval, and turns the leftover disagreement
into a concrete human-adjudication task.

## When to use

Reach for this whenever a labelled dataset underpins a decision — a gold eval
set, a training corpus, a survey coding, or an LLM judge you want to trust like
a human. If only one person labelled it, you have no reliability signal; get a
second (or third) rater on at least a sample first.

## Prerequisites

- **Python 3.9+** with `numpy`, `pandas`, `statsmodels`, `krippendorff`.

  ```bash
  python3 -m pip install numpy pandas statsmodels krippendorff
  ```

  Verified against: statsmodels 0.14.6, krippendorff 0.8.1, numpy 2.0.
- **Labels from ≥2 raters on overlapping items.** For Fleiss/alpha you want the
  same items rated by all raters (alpha tolerates missing cells; Fleiss does not).
- **Know your measurement level:** `nominal` (unordered classes like
  topic/intent), `ordinal` (ranked like low/med/high, 1–5 sentiment), or
  `interval`/`ratio` (true numeric). This changes alpha and picks weighted vs
  unweighted kappa — getting it wrong understates real agreement.

## Which metric

| Situation | Use | Why |
|---|---|---|
| Exactly 2 raters, nominal classes | Cohen's κ | Classic pairwise, gives z/p and CI |
| 2 raters, **ordinal** scale | Cohen's κ, **weighted** (`wt='linear'` or `'quadratic'`) | Near-misses (2 vs 3) count as partial agreement |
| 3+ raters, all rate every item, nominal | Fleiss' κ | Handles many raters, fixed count per item |
| 3+ raters, **missing labels**, or ordinal/interval | **Krippendorff's α** | Only one that handles missing data + any level; report this as the headline |

Rule of thumb (Krippendorff): **α ≥ 0.80 = reliable**, 0.667–0.80 = tentative
(draw only cautious conclusions), **< 0.667 = do not trust** — revise the
guidelines and re-annotate. Kappa's old "Landis–Koch" bands (0.6–0.8 = substantial)
are looser and prevalence-sensitive; prefer alpha's stricter cutoffs for eval work.

## Recipes

### 1. One command, long-format CSV (recommended)

The helper does all metrics + the adjudication queue. CSV columns default to
`unit,rater,label`.

```bash
python3 scripts/iaa.py labels.csv --level nominal --queue adjudicate.csv
# ordinal scale — fix the order so weighting/α are correct:
python3 scripts/iaa.py labels.csv --level ordinal --order neg,neu,pos
# custom column names (e.g. an LLM judge run):
python3 scripts/iaa.py runs.csv --unit item_id --rater judge --label verdict
```

Output:

```
units=12  raters=3  level=nominal
Krippendorff alpha = 0.657  95% CI [0.360, 0.912]  -> unreliable — revise guidelines / retrain
Fleiss kappa       = 0.629  (over 11 fully-rated units)
Mean pairwise Cohen kappa = 0.636
Adjudication queue : 4 of 12 units disagree
```

The CI is a percentile bootstrap over resampled **units** — a wide CI (as above,
on tiny n) means "you need more data before believing this number", which is
itself a finding.

### 2. Cohen's kappa by hand (two raters)

```python
import numpy as np, pandas as pd
from statsmodels.stats.inter_rater import cohens_kappa

a = np.array([1,1,0,2,1,0,2,2,1,0])   # rater A
b = np.array([1,0,0,2,1,0,2,1,1,0])   # rater B
cats = sorted(set(a) | set(b))
table = pd.crosstab(pd.Categorical(a, cats),
                    pd.Categorical(b, cats), dropna=False).to_numpy()

r = cohens_kappa(table)               # unweighted (nominal)
print(r.kappa, r.z_value, r.pvalue_two_sided, r.kappa_low, r.kappa_upp)
# ordinal? weight near-misses:
print(cohens_kappa(table, wt='linear').kappa)     # linear
print(cohens_kappa(table, wt='quadratic').kappa)  # quadratic (== ICC-like)
```

`cohens_kappa` returns a `KappaResults` with `.kappa`, `.std_kappa`,
`.z_value`, `.pvalue_two_sided`, `.kappa_low`/`.kappa_upp` (95% CI).

### 3. Fleiss' kappa (many raters, one item = one row of ratings)

```python
import numpy as np
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa
# rows = items, cols = raters, cells = the label each rater gave
data = np.array([[1,1,1,0],[2,2,2,2],[0,0,1,0],[1,1,1,1]])
table, cats = aggregate_raters(data)   # -> items x categories count matrix
print(fleiss_kappa(table))             # 'fleiss' method by default
```

`aggregate_raters` needs the **same number of raters per item** — drop or
impute incomplete rows first (the helper does this automatically).

### 4. Krippendorff's alpha (missing data / any level)

Input is a **raters × units** matrix; use `np.nan` for a rating a rater
didn't give.

```python
import numpy as np, krippendorff
rel = np.array([[1,1,np.nan,2,1,0],
                [1,0,0,   2,1,0],
                [1,1,0,   2,np.nan,0]])
krippendorff.alpha(reliability_data=rel, level_of_measurement='nominal')  # 0.815
krippendorff.alpha(reliability_data=rel, level_of_measurement='ordinal')  # 0.865
```

### 5. Adjudicate → build the gold label

Agreement isn't the goal; a trustworthy label set is. Take the queue CSV
(`unit, n_labels, distinct, majority, tie, votes`), have a senior annotator
resolve the flagged items, fold the resolved labels back in, then **re-run the
IAA** on the clean set to confirm the fix and record the final number for your
methods section. For LLM-judge calibration, treat the human consensus as truth
and report the judge-vs-human alpha specifically.

## Verify

```bash
# helper compiles and runs on the bundled shape:
python3 -c "import py_compile; py_compile.compile('scripts/iaa.py', doraise=True)"
python3 scripts/iaa.py labels.csv --level nominal   # prints alpha/kappa + queue
```

Sanity checks on any real result:
- **Perfect agreement → κ = α = 1.0.** Chance-level agreement → ≈ 0. Systematic
  disagreement can go **negative** — that's real, usually a flipped/miscoded rater.
- Alpha and Fleiss should be in the same ballpark on complete nominal data; a
  big gap means missing-data handling or level is doing something — investigate.
- Switching `--level nominal` → `ordinal` on a genuine scale should **raise**
  the score (near-misses now count). If it doesn't, your `--order` is wrong.

## Pitfalls

- **Reporting raw % agreement.** Always chance-correct; high prevalence inflates
  raw agreement massively.
- **Wrong measurement level.** Nominal alpha on a 1–5 scale throws away the
  ordering and understates agreement. Set `--level ordinal` + `--order`.
- **The kappa/alpha paradox.** With very skewed class prevalence, kappa can be
  low even at 95% raw agreement. Report prevalence alongside the coefficient;
  prefer alpha, and consider weighted kappa or per-class agreement.
- **Too few items.** Any single coefficient on <~30 items is noisy — that's why
  the helper bootstraps a CI. A CI spanning 0.4 means "collect more", not "0.66".
- **Fleiss with unequal raters per item.** `aggregate_raters` silently needs a
  fixed rater count; use Krippendorff's alpha when coverage is ragged.
- **Judge = human, unchecked.** High judge-vs-judge consistency is not
  calibration. Compute alpha of the judge **against the human consensus**, and
  run llm-judge-bias-audit for systematic tilt.
- **`weights=` vs `wt=` in statsmodels.** Weighted kappa uses `wt='linear'`/
  `'quadratic'`; passing `weights='linear'` raises a ValueError.
