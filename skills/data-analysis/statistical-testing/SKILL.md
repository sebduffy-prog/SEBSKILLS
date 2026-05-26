---
name: statistical-testing
category: data-analysis
description: Run the correct statistical test for the user's question, check assumptions before running it, and report effect size + confidence interval alongside the p-value. Use when the user asks about significance, comparing groups, A/B test results, regression coefficients, goodness-of-fit, or correlation testing. Triggers on "is X significantly different", "p-value", "A/B test", "hypothesis test", "t-test", "chi-square", "ANOVA", "regression", "confidence interval". Anti-hallucination posture — never declare "significant" without (1) the test having been run in-session, (2) assumptions having been checked, and (3) effect size + CI reported alongside p-value.
when_to_use:
  - User asks "is A significantly different from B" / "does treatment work" / "is this effect real"
  - User wants to fit a regression and interpret coefficients
  - User wants to test goodness-of-fit or independence (chi-square)
  - User has A/B test data and wants the verdict
  - User asks about correlation significance (not just the coefficient)
  - User wants a confidence interval around an estimate
when_not_to_use:
  - User wants descriptive statistics / distributions only → use exploratory-data-analysis
  - User wants to clean / transform the data → use data-processing
  - User wants schema work → use data-schema
  - User wants Bayesian inference (this skill is frequentist; flag the choice)
  - User wants ML model fitting / cross-validation (separate concern)
similar_to:
  - exploratory-data-analysis
  - mathematical-computation
  - data-processing
keywords:
  - hypothesis-test
  - p-value
  - significance
  - t-test
  - chi-square
  - anova
  - mann-whitney
  - kruskal
  - regression
  - confidence-interval
  - effect-size
  - cohens-d
  - ab-test
  - bonferroni
inputs_needed:
  - Data (DataFrame, file path, or summary statistics)
  - The specific question — "is group A's mean different from B's", "is X associated with Y", etc.
  - Significance level (default α = 0.05; confirm if testing many hypotheses)
  - Whether one-tailed or two-tailed (default two-tailed; confirm if user has prior direction)
  - Whether tests are pre-registered or exploratory (drives multiple-comparison correction)
produces: A test report — chosen test + reason, assumption-check results, test statistic, p-value, effect size (Cohen's d / odds ratio / r² / etc.), confidence interval, and a plain-English interpretation that does NOT overclaim
---

# Statistical Testing

Run the correct frequentist test for the user's question, with assumption checks and effect-size reporting.

## Verification protocol — no claims without computation

1. **Never declare "significant" without running the test in-session.** The model must execute the test code and observe the test statistic and p-value before any interpretation.
2. **Check assumptions FIRST.** Normality (Shapiro-Wilk), equal variance (Levene), independence (study design). If violated, switch to a robust / non-parametric alternative and tell the user why.
3. **Effect size + CI alongside p-value, always.** A p-value alone is not a result. Report Cohen's d (or odds ratio / r² / R² / η²) AND its confidence interval. Statistical significance ≠ practical significance.
4. **Sample size matters.** A "non-significant" result on n=20 is not "no effect" — it is "underpowered to detect the effect we'd care about". State this.
5. **Multiple comparisons get corrected.** If running > 1 test on the same data, apply Bonferroni / Holm / Benjamini-Hochberg and report both raw and adjusted p-values. Or pre-specify which is primary.
6. **Frequentist framing is explicit.** "p = 0.03 means: assuming the null is true, we'd see data this extreme 3% of the time." Never "there's a 3% chance the null is true" — that's a Bayesian claim.
7. **Causal language is reserved for designs that support it.** A correlation in observational data does not justify "X caused Y". Use the design language the data supports (RCT → causal; observational → associated with).

## Inputs to confirm with the user

- **The question.** Not "run a t-test" but "are men's salaries higher than women's in this sample, on average". Pin down the comparison and the outcome.
- **One-tailed or two-tailed?** Default two-tailed. Only use one-tailed if the user has a pre-specified direction and would treat an opposite result as a null.
- **α (significance level)?** Default 0.05.
- **Pre-registered or exploratory?** Exploratory analyses need multiple-comparison correction.
- **Practical effect size threshold?** "What size difference would matter to you?" — helps interpret the result regardless of p.

## Test selection — full decision tree in `assets/test-selection.md`

Quick reference (always confirm by checking assumptions):

| Question | Default test | Non-parametric alt |
|---|---|---|
| One group's mean vs. a known value | 1-sample t-test | Wilcoxon signed-rank |
| Two independent groups, means | 2-sample t-test (Welch by default) | Mann-Whitney U |
| Two paired observations | Paired t-test | Wilcoxon signed-rank |
| 3+ groups, means | One-way ANOVA | Kruskal-Wallis |
| 2 categorical variables, independence | Chi-square of independence | Fisher's exact (if small expected counts) |
| Goodness-of-fit to a distribution | Chi-square / Kolmogorov-Smirnov | — |
| Correlation between two numerics | Pearson r + test | Spearman ρ |
| Linear relationship with predictors | OLS regression | Quantile / robust regression |
| Binary outcome with predictors | Logistic regression | — |
| Proportions (e.g. A/B conversion) | Two-proportion z-test or Fisher | — |

## Standard workflow

```python
import numpy as np
import pandas as pd
from scipy import stats

# 1. STATE THE QUESTION AND CHOSEN TEST
question = "Is mean conversion rate different between A and B?"
chosen_test = "two-proportion z-test"
print(f"Question: {question}")
print(f"Test: {chosen_test}")

# 2. EXTRACT THE DATA
a = df[df["group"] == "A"]["converted"]
b = df[df["group"] == "B"]["converted"]
print(f"A: n={len(a)}, successes={a.sum()}, rate={a.mean():.4f}")
print(f"B: n={len(b)}, successes={b.sum()}, rate={b.mean():.4f}")

# 3. CHECK ASSUMPTIONS (state and verify each)
#    - Independence: by design (random assignment)
#    - Sample size for normal approx: n*p >= 10 and n*(1-p) >= 10
for name, s in [("A", a), ("B", b)]:
    p_hat = s.mean()
    n = len(s)
    print(f"{name}: n*p={n*p_hat:.0f}, n*(1-p)={n*(1-p_hat):.0f} "
          f"({'OK' if n*p_hat >= 10 and n*(1-p_hat) >= 10 else 'use Fisher exact'})")

# 4. RUN THE TEST
from statsmodels.stats.proportion import proportions_ztest, proportion_confint
counts = np.array([a.sum(), b.sum()])
nobs = np.array([len(a), len(b)])
z, p = proportions_ztest(counts, nobs, alternative="two-sided")

# 5. EFFECT SIZE + CI
diff = b.mean() - a.mean()
ci_a = proportion_confint(a.sum(), len(a), method="wilson")
ci_b = proportion_confint(b.sum(), len(b), method="wilson")

# 6. REPORT (with full context)
print(f"\nz = {z:.3f}, p = {p:.4f}")
print(f"Rate difference (B - A) = {diff:+.4f}")
print(f"A 95% CI: [{ci_a[0]:.4f}, {ci_a[1]:.4f}]")
print(f"B 95% CI: [{ci_b[0]:.4f}, {ci_b[1]:.4f}]")
print(f"Interpretation: at α = 0.05, the difference is "
      f"{'statistically significant' if p < 0.05 else 'not statistically significant'}. "
      f"Practical: B's rate is {diff*100:+.2f} percentage points vs A.")
```

## Output format — the test report

```markdown
## Test report

**Question**: <one sentence the user asked>
**Test chosen**: <test name>  (reason: <why this test for this design>)

### Data summary
- Group A: n = …, mean/proportion = …
- Group B: n = …, mean/proportion = …

### Assumption checks
- Independence: <how verified or assumed>
- Normality: <Shapiro-Wilk p = … → met / violated, using <alt>>
- Equal variance: <Levene p = … → using Welch / pooled>

### Result
- Test statistic: <value>
- p-value: <value, raw + adjusted if applicable>
- Effect size: <Cohen's d / odds ratio / r / …> = <value>, 95% CI = […, …]

### Interpretation
<Plain English. State the comparison. State the magnitude. State whether
the result clears the user's practical-significance threshold (if given).
DO NOT overclaim. DO NOT use causal language unless the design warrants it.>
```

## Anti-patterns to refuse

- "p < 0.05 means the result is true / real / important." → No. State what p actually means.
- Running a test and only reporting the p-value. → Always include effect size + CI.
- Running many tests and reporting whichever was significant. → Either pre-specify a primary outcome or correct for multiplicity, and tell the user which.
- "Non-significant" → "no effect". → State the CI of the effect; an underpowered null is not a null effect.
- Causal language ("X causes Y") on observational data. → Switch to "associated with".
- Assuming normality without checking it on n < 30.
- Using a t-test when the design is paired (or vice versa) — the design dictates the test.
- "We can be 95% confident the true mean is in this CI." → That's not what a frequentist CI means; phrase as "if we repeated the experiment many times, 95% of the resulting intervals would contain the true mean".

## Escalation paths

- **User wants Bayesian inference** — flag the framework switch; this skill is frequentist. Offer to switch to a Bayesian approach with priors that the user specifies.
- **Time series / autocorrelated data** — t-test/ANOVA assume independence; for time series, use methods that account for autocorrelation (ARIMA residual tests, etc.).
- **Hierarchical / clustered data** — single-level tests overstate significance; recommend mixed-effects models.
- **Very small samples (n < 5 per group)** — most tests' assumptions break; recommend permutation tests or honest "underpowered" framing.

## Asset

`assets/test-selection.md` — full decision tree for choosing the right test based on design, outcome type, and group structure.
