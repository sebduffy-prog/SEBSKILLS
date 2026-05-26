---
name: exploratory-data-analysis
category: data-analysis
description: Produce rigorous exploratory analysis of a dataset — distributions, central tendency, dispersion, correlations, outliers — with every reported statistic computed from the data and cited. Use when the user asks "what does this data look like", wants a summary report, wants to understand a dataset before modeling, or asks "are these two columns related" / "are there outliers". Triggers on "EDA", "summary statistics", "explore this data", "describe the data", "any outliers", "distributions", "correlations", "pairwise". Anti-hallucination posture — every number in the response is computed in-session; no central-limit-theorem hand-waving; no asserted relationships without correlation coefficients or test statistics.
when_to_use:
  - User asks "what does this data look like" or wants a summary
  - User wants distributions, percentiles, central tendency, dispersion characterized
  - User wants pairwise correlations between numeric columns
  - User wants outlier detection (IQR, z-score, isolation forest)
  - User wants to compare distributions across groups (descriptive, not inferential)
  - User is preparing data for modeling and needs to characterize it first
when_not_to_use:
  - User wants to test a specific hypothesis ("is A significantly larger than B") → use statistical-testing
  - User wants to clean / transform the data → use data-processing
  - User just wants the schema, not the distributions → use data-schema
  - User wants to fit a model (regression, classification) → use statistical-testing for regression, or a future ML skill
similar_to:
  - data-schema
  - statistical-testing
  - data-processing
keywords:
  - eda
  - exploratory
  - summary
  - describe
  - distribution
  - correlation
  - quantile
  - percentile
  - outlier
  - histogram
  - pairwise
  - profile
inputs_needed:
  - DataFrame or file path
  - Which columns to focus on (or "all" — default)
  - Optional grouping column for within-group statistics
  - Whether the user wants plots in addition to numerical output (default: numbers only)
produces: A structured EDA report — shape, dtypes, per-column summary stats (count, mean, std, min, quartiles, max, skew), correlation matrix, outlier counts. All numbers computed in-session.
---

# Exploratory Data Analysis

Produce rigorous summary statistics, distributions, correlations, and outlier detection for tabular data — with every reported number cited from a computation.

## Verification protocol — no claims without computation

1. **Every reported statistic is computed.** "The mean is 42.3" only after running `df['col'].mean()` and observing 42.3 (rounded as appropriate).
2. **Distributions are characterized with five numbers, not adjectives.** "Right-skewed" is supported by computed skewness and the mean-vs-median delta, not visual intuition.
3. **Correlations cite both the coefficient AND the n.** A correlation on 5 rows is reported with `n=5` so the user can judge its weight.
4. **Outlier counts use a defined rule.** State the rule before counting (IQR×1.5, |z| > 3, etc.). Don't call values "outliers" without applying a rule.
5. **Relationships are correlations, not causations.** EDA never claims A causes B. State the coefficient and stop.
6. **"All columns look normal" requires computation.** Use Shapiro-Wilk or visual QQ; don't eyeball.

## Inputs to confirm with the user

- **Scope.** All columns, or a subset? (Default: numeric columns only for stats; add categoricals for cardinality.)
- **Grouping?** Within-group statistics by a categorical (e.g. by country, by cohort)?
- **Plots?** Default is numerical-only output. If the user wants plots, ask which kinds (histogram, box, scatter matrix).
- **Outlier definition?** IQR×1.5 (Tukey) is the default. Z-score, modified z, or isolation forest if requested.
- **Sampling?** If dataset is huge, propose a reproducible sample with `random_state` set.

## Standard workflow

```python
import pandas as pd
import numpy as np

df = pd.read_csv(path)

# 1. SHAPE + DTYPES
print("shape:", df.shape)
print("memory MB:", df.memory_usage(deep=True).sum() / 1e6)
print(df.dtypes)

# 2. NUMERIC SUMMARY (with skew + kurtosis)
num = df.select_dtypes(include="number")
summary = num.describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T
summary["skew"] = num.skew()
summary["kurt"] = num.kurt()
summary["null_pct"] = num.isna().mean() * 100
print(summary)

# 3. CATEGORICAL SUMMARY
for col in df.select_dtypes(include=["object", "category"]).columns:
    vc = df[col].value_counts(dropna=False)
    print(f"\n{col}: {df[col].nunique(dropna=True)} unique, top 5:")
    print(vc.head())

# 4. CORRELATIONS (Pearson + Spearman)
if num.shape[1] >= 2:
    print("\nPearson correlations:")
    print(num.corr().round(3))
    print("\nSpearman (rank, robust to monotone non-linearity):")
    print(num.corr(method="spearman").round(3))

# 5. OUTLIERS by IQR×1.5 (state the rule)
print("\nOutliers (IQR × 1.5):")
for col in num.columns:
    q1, q3 = num[col].quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    n_out = ((num[col] < lo) | (num[col] > hi)).sum()
    print(f"  {col}: {n_out} outliers (rule: < {lo:.2f} or > {hi:.2f})")
```

A more complete template is in `assets/eda-template.py`.

## Output format

Produce a structured Markdown report with these sections:

```markdown
## EDA report — <dataset name>

**Shape**: 12,345 rows × 27 columns  •  **Memory**: 8.4 MB

### Per-column summary

| Column | Dtype | n | null% | mean | std | min | p25 | p50 | p75 | max | skew |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| age | int | 12,345 | 0.0 | 34.2 | 12.4 | 18 | 25 | 33 | 42 | 89 | 0.45 |

### Correlations (Pearson, numeric columns)

|   | age | income | tenure |
|---|---:|---:|---:|
| age | 1.00 | 0.42 | 0.61 |
| income | 0.42 | 1.00 | 0.38 |
| tenure | 0.61 | 0.38 | 1.00 |

### Outliers (IQR × 1.5)

- `age`: 23 outliers (< 8 or > 65)
- `income`: 412 outliers (< -15,000 or > 180,000) — note negative LB is structural, only upper applies
```

## Anti-patterns to refuse

- "The data is roughly normally distributed" without computing skew, kurtosis, or running Shapiro-Wilk.
- "Age and income are strongly correlated" without citing the coefficient.
- "There are a few outliers" without a rule and an exact count.
- "This looks like a customer dataset" — that's a domain claim, not a statistical one. Stop and ask the user about domain meaning.
- Reporting a correlation on data with high null rates without first reporting how `corr()` handles those (`.corr()` does pairwise complete).
- Recommending modeling decisions ("you should log-transform income") from EDA alone — that's a modeling judgment that depends on the downstream task; surface the option, don't prescribe.

## Escalation paths

- Dataset > 10M rows → propose a stratified sample with fixed `random_state` and report results on the sample, clearly labeled.
- Highly mixed dtypes / messy data → run `data-schema` first to characterize the shape, then EDA.
- User asks "is X significantly different across groups" → that's inferential, switch to `statistical-testing`.

## Asset

`assets/eda-template.py` — a runnable script that emits the report above for any CSV input.
