---
name: data-analyst
description: |
  Proper data analyst workflow — exploratory data analysis (EDA),
  hypothesis testing, segmentation, cohort analysis, time-series
  decomposition, regression, lift / incrementality testing,
  bootstrap intervals, A/B testing, confidence calibration. Deeper
  than [[data-cut-headline-stats]] (which is editorial output);
  this is the analytic substrate that headline stats and
  strategic reads sit on top of. Use when the user needs the
  data understood properly — not just summarised. Trigger on
  phrases like "analyse this data properly", "do an EDA",
  "run the stats", "is this significant", "build a model",
  "regress this on that", "cohort analysis", "time series",
  "decompose this", "seasonality", "trend test", "A/B test",
  "lift test", "incrementality", "bootstrap this", "confidence
  interval", "p-value", "correlation matrix", "regression",
  "logistic regression", "control for", "uplift modelling",
  "panel data", "longitudinal", "fixed effects", "stat test
  please", "is this real", "noise or signal". Trigger when a user
  hands over a CSV/XLSX and asks "do the actual analysis, not
  just the cut". Pairs with [[raw-data-research]] (pipeline
  before), [[data-cut-headline-stats]] (editorial output after),
  [[strategy-analyst]] (interpretation), and [[vccp-media-design]]
  (charts).
---

# Data analyst

The job is to **make the data answer a question reliably** — not
to summarise the data, not to find a story in it. Reliability
comes from a deliberate workflow: profile, plan the test, run
it, check assumptions, report effect + uncertainty + caveats.

This skill is paired with — but distinct from —
[[data-cut-headline-stats]]. Headline stats are editorial outputs
designed for a deck; data-analyst is the analytic substrate the
deck rests on. A planner uses both.

## When to use

- A claim needs a defensible statistical backing ("are these
  groups really different?")
- A campaign needs an effect size, not just a vibe ("did
  awareness move because of us?")
- Sales / panel / tracker data needs decomposition (trend +
  seasonality + residual)
- A test was run and someone needs the read with proper
  uncertainty
- A segmentation / cohort / regression is needed as part of a
  strategy or effectiveness case
- The user explicitly asks for "stats", "the maths", "the
  proper analysis"

**Don't use this skill** for: pure descriptive cuts (use
[[data-cut-headline-stats]]), large-file pipeline work (use
[[raw-data-research]]), or full MMM (a separate modelling
discipline — but the [[strategy-analyst]] skill knows how to
*read* MMM output).

## The discipline

### 1. Plan the analysis before opening the file

Write down, in order:

```
The question:       [the specific question one sentence]
The decision:       [what choice depends on this]
The data we have:   [source, granularity, time window]
The right test:     [the statistical method]
The assumptions:    [what has to hold for the test to be valid]
The minimum signal: [the effect size that would matter]
```

The "minimum signal" line is the one most analyses skip and the
one that decides whether a result matters. A 0.3pt awareness
shift can be significant *and* irrelevant.

### 2. Profile every dataset before touching it

```python
import pandas as pd
df = pd.read_csv(path)

# Shape and types
print(df.shape, df.dtypes, sep="\n")

# Range, central tendency, dispersion
print(df.describe(include="all").T)

# Cardinality (categoricals)
print({c: df[c].nunique() for c in df.select_dtypes("object")})

# Missingness pattern
print(df.isna().mean().sort_values(ascending=False).head(20))

# Duplicates on the natural key
print(df.duplicated(subset=["id"]).sum())

# Outliers (z > 3 or IQR-based)
from scipy.stats import zscore
z = df.select_dtypes("number").apply(zscore).abs()
print((z > 3).sum())
```

Then **plot the distributions** before any statistical test.
Histograms and ECDFs reveal more in 30 seconds than five
descriptive tables.

### 3. Pick the right test (cheat sheet)

| Situation | Test |
|---|---|
| Compare a single mean to a known value | one-sample t |
| Compare two independent group means | Welch's t (don't assume equal var) |
| Compare two means, paired (same units, before/after) | paired t |
| Compare proportions between two groups | two-proportion z, or Fisher's exact (small n) |
| Compare >2 group means | one-way ANOVA + Tukey HSD |
| Compare distributions (no normality assumption) | Mann-Whitney U / Kruskal-Wallis |
| Test association of two categoricals | chi-squared (n>5 per cell), Fisher's exact (small) |
| Correlation between two continuous | Pearson (linear, normal-ish) or Spearman (rank) |
| Predict continuous outcome | linear regression / OLS |
| Predict binary outcome | logistic regression |
| Time series — does the trend exist | Mann-Kendall, ADF for stationarity |
| Time series decomposition | STL / classical |
| Treatment effect (with control) | difference-in-differences, synthetic control, geo-lift |
| Causal effect (RCT-like) | t/proportion test on the holdout |
| Small sample, no parametric assumption | bootstrap percentile CI |

**Default to non-parametric tests when n<30 per group** or when
distributions are obviously skewed. Default to **bootstrap** for
unusual statistics (medians, ratios, attention-weighted reach,
etc.) where the closed-form CI doesn't exist or isn't trusted.

### 4. Check assumptions, don't assume them

For any parametric test, run the assumption checks:

```python
# Normality (visually first, then test only if n is small)
import scipy.stats as stats
stats.shapiro(x)              # if n<50
import matplotlib.pyplot as plt
stats.probplot(x, plot=plt)   # QQ-plot

# Equal variance
stats.levene(group_a, group_b)

# Independence — design check, not statistical (think about it)

# For regression: residual plots (homoscedasticity), DW for autocorrelation
import statsmodels.api as sm
fit = sm.OLS(y, sm.add_constant(X)).fit()
print(fit.summary())
sm.graphics.plot_regress_exog(fit, "x1")
```

When assumptions fail, switch to the non-parametric counterpart
or to a robust standard-error variant (HC3, clustered).

### 5. Report effect, uncertainty, and a caveat

Every result the skill emits must carry **all three**:

```
Effect:       +4.2 percentage points (group A vs group B)
Uncertainty:  95% CI [1.8, 6.6]; Welch t = 3.4, n_a=412, n_b=389,
              p = 0.0007
Caveat:       Sample is recruited via online panel — under-represents
              over-65s; effect may not generalise.
```

A "p < 0.05" with no effect size is not a result, it's a hedge.

### 6. Multiple testing — discipline it

Whenever you run >5 tests, control for false positives:

- Pre-register the small set of primary tests
- Apply Bonferroni (strict) or Benjamini-Hochberg (less strict)
  correction on the rest
- Treat anything that survives only on uncorrected p < 0.05 as
  "we're watching" (per [[strategy-analyst]]'s confidence register)

### 7. For time series — decompose first

Brand tracker, sales, search, social — all are time series.
Before testing for a campaign effect, decompose:

```python
from statsmodels.tsa.seasonal import STL
res = STL(series, period=52, robust=True).fit()
res.plot()
# components: trend, seasonal, residual
```

Then the question becomes: did the residual move at the moment
of the campaign? — which is a much cleaner test than "did the
raw series move".

### 8. For experiments (A/B, lift, geo) — design first, then analyse

A test designed badly cannot be analysed well. The strategy-side
checklist:

- **Pre-registered hypothesis** (what would falsify it)
- **Pre-registered primary metric** (one — not three)
- **Power calculation** (minimum detectable effect at the budget
  and timeline available)
- **Allocation** (random, stratified, geo-matched)
- **Run-in / wash-out** (account for trends pre-test)
- **Stopping rule** (no peeking)
- **Decision rule** (what we'll do at each outcome)

For geo-lift / matched-market, prefer **synthetic control** or
**difference-in-differences** with parallel-trends checks over
naive treatment-vs-control comparisons. For digital A/B, run the
test long enough to cover a full weekly cycle.

## Common analyses, working code

### Two-group comparison (clean)

```python
from scipy.stats import ttest_ind
import numpy as np

t, p = ttest_ind(a, b, equal_var=False)  # Welch
mean_diff = a.mean() - b.mean()
se_diff = np.sqrt(a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b))
ci = (mean_diff - 1.96*se_diff, mean_diff + 1.96*se_diff)
print(f"Δ = {mean_diff:.3f}, 95% CI {ci}, t={t:.2f}, p={p:.4f}")
```

### Two-proportion comparison

```python
from statsmodels.stats.proportion import proportions_ztest
count = [successes_a, successes_b]
nobs  = [n_a, n_b]
z, p = proportions_ztest(count, nobs)
```

### Bootstrap CI on any statistic

```python
import numpy as np
rng = np.random.default_rng(42)
def boot_ci(x, stat=np.mean, B=10000, alpha=0.05):
    boots = [stat(rng.choice(x, size=len(x), replace=True)) for _ in range(B)]
    lo, hi = np.percentile(boots, [100*alpha/2, 100*(1-alpha/2)])
    return stat(x), lo, hi
```

### Linear regression with robust SE

```python
import statsmodels.api as sm
X = sm.add_constant(df[["spend", "season", "comp_spend"]])
fit = sm.OLS(df["sales"], X).fit(cov_type="HC3")
print(fit.summary())
```

### Diff-in-diff (geo-lift)

```python
import statsmodels.formula.api as smf
panel["treated"] = (panel["geo"].isin(treat_geos)).astype(int)
panel["post"]    = (panel["date"] >= treatment_start).astype(int)
fit = smf.ols("y ~ treated*post + C(geo) + C(date)", data=panel)\
        .fit(cov_type="cluster", cov_kwds={"groups": panel["geo"]})
print(fit.summary())
# the interaction (treated:post) is the lift
```

### STL decomposition + intervention test

```python
from statsmodels.tsa.seasonal import STL
res = STL(series, period=52, robust=True).fit()
# Test whether residual mean differs pre/post campaign
pre  = res.resid[:campaign_start]
post = res.resid[campaign_start:campaign_end]
print(ttest_ind(post, pre, equal_var=False))
```

### Cohort analysis

```python
df["cohort"]   = df.groupby("user_id")["date"].transform("min").dt.to_period("M")
df["age_mo"]   = ((df["date"] - df.groupby("user_id")["date"].transform("min"))
                  .dt.days // 30)
retention = df.groupby(["cohort", "age_mo"])["user_id"].nunique().unstack(0)
retention = retention.div(retention.iloc[0])  # normalise to month 0
```

## Output format

For any deliverable to the strategy team:

```
ANALYSIS — [question]
Data: [source, n, time window]
Method: [test / model + why this method]

Result:
  Effect:      [value, units]
  Uncertainty: [CI, test stat, p]

Visual: [one chart — the chart that shows the effect, with comparator]

What this means:
  [one sentence of plain-English interpretation]

What this does NOT mean:
  [one sentence of what people might wrongly read]

Caveats:
  [one or two lines — sample, design, generalisability]

Confidence register: WE KNOW / WE THINK / WE'RE WATCHING
```

Then hand the result to [[strategy-analyst]] for the read-out
or [[data-cut-headline-stats]] for the headline-stat form.

## Common analytic traps to avoid

1. **Significance theatre.** Quoting p-values without effect
   sizes. p says "real", not "big".
2. **Comparing without a comparator.** "Awareness rose to 47%" —
   vs what?
3. **Mean-only reporting.** Means hide distributions. Show
   median + IQR or a histogram alongside.
4. **Pseudo-replication.** Treating dependent observations
   (same user, multiple sessions) as independent inflates n and
   significance. Cluster the SEs.
5. **Reverse causation.** "People who saw the ad bought more" —
   maybe people about to buy were more likely to be served the ad.
6. **Survivorship.** Analyses run only on users who stayed are
   biased by who left.
7. **Post-hoc subgroup hunting.** Finding the cell that worked
   *after* the test ran is not a test, it's a hypothesis for
   next time.
8. **Anchoring on point estimates.** A point estimate with a CI
   crossing zero is the same as "we don't know".
9. **Ignoring practical significance.** Effects can be
   significant and immaterial; report both.
10. **Reusing a tracker baseline that has drifted.** Last year's
    "category norm" isn't necessarily this year's.

## Tools

- **Python** with `pandas`, `numpy`, `scipy`, `statsmodels`,
  `matplotlib`, optionally `pymc` or `numpyro` for bayesian work
- **DuckDB** for >1M-row CSVs/parquet — query without loading
  into pandas
- **R** when you're inheriting a brand-research / mr-team codebase
- **Causalimpact / synthdid / fixest** for time-series
  interventions
- For the VCCP chart style on outputs, use the matplotlib config
  in [[vccp-media-design]] (`vccp_charts.py`)

## Handoffs

- **Before analysis** — pipeline / parsing work belongs to
  [[raw-data-research]]
- **After analysis** — for the editorial output, hand to
  [[data-cut-headline-stats]]; for the strategic read, hand to
  [[strategy-analyst]]; for the deck, hand to
  [[deck-flow-structure]]; for the visual, [[vccp-media-design]]
