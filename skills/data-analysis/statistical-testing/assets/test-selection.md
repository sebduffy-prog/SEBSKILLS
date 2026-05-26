# Test selection decision tree

Use this to pick the right frequentist test before any code runs. The shape
of the question (paired vs independent, continuous vs categorical, 2-group
vs N-group) dictates the test — not "what feels familiar".

## Step 1 — What is the outcome variable?

- **Continuous / numeric** → §2 (means / medians)
- **Binary / proportion** → §3 (rates)
- **Categorical (3+ levels)** → §4 (contingency)
- **Count** (Poisson-distributed) → §5
- **Time-to-event** → §6 (survival)

---

## §2 Continuous outcome

| Design | Default test | Assumptions | Non-parametric alternative |
|---|---|---|---|
| One group vs known value | 1-sample t-test | Approx normal, or n ≥ 30 | Wilcoxon signed-rank |
| Two independent groups | Welch's t-test | Approx normal per group, or n ≥ 30 per group | Mann-Whitney U |
| Two paired observations | Paired t-test | Differences approx normal | Wilcoxon signed-rank |
| 3+ independent groups | One-way ANOVA | Approx normal, equal variance (Levene) | Kruskal-Wallis |
| 3+ within-subject repeated | Repeated-measures ANOVA | Sphericity (Mauchly) | Friedman |
| Two factors crossed | Two-way ANOVA | Approx normal, equal variance | Aligned-rank transform |

Post-hoc on ANOVA: Tukey HSD (equal n) or Games-Howell (unequal variance).

---

## §3 Binary outcome

| Design | Default test | Notes |
|---|---|---|
| One proportion vs known value | One-proportion z-test or exact binomial | Use exact if `n*p < 10` |
| Two independent proportions | Two-proportion z-test | Use Fisher exact if any expected cell < 5 |
| Two paired proportions | McNemar's test | Tests change in the discordant pairs |
| 2×K independent | Chi-square of independence | Or Fisher exact for small samples |

Effect size: difference in proportions (with Wilson CI), or odds ratio.

---

## §4 Categorical outcome (3+ levels)

| Design | Test |
|---|---|
| Independence of two categoricals | Chi-square of independence |
| Goodness-of-fit to expected distribution | Chi-square goodness-of-fit |
| Ordered categorical outcome by group | Mann-Whitney / Kruskal-Wallis on the rank |
| Symmetry of an R×R table | Bowker / extended McNemar |

Effect size: Cramér's V (for chi-square independence).

---

## §5 Count outcome

| Design | Default model | Use when… |
|---|---|---|
| Single rate vs known | Poisson exact test | Counts of events in fixed exposure |
| Count outcome with predictors | Poisson regression | Mean ≈ variance |
| Overdispersed counts | Negative binomial regression | Variance > mean |
| Excess zeros | Zero-inflated NB | Many structural zeros |

---

## §6 Time-to-event

| Question | Method |
|---|---|
| Compare survival curves between groups | Kaplan-Meier + log-rank test |
| Effect of predictors on hazard | Cox proportional hazards (check PH assumption) |

---

## Step 2 — How many tests am I running?

- **One** → no correction needed; report raw p.
- **Pre-specified small family (≤ ~5)** → Bonferroni acceptable, or Holm for less conservatism.
- **Many exploratory tests** → Benjamini-Hochberg (FDR control). Report both raw and adjusted.
- **One pre-registered primary + secondary** → report primary with α, secondaries as exploratory.

## Step 3 — What's my effect size?

p-values without effect sizes are not a result.

| Test | Effect size | Cohen's "small / medium / large" |
|---|---|---|
| t-test, ANOVA | Cohen's d | 0.2 / 0.5 / 0.8 |
| ANOVA (overall) | η² (eta-squared) | 0.01 / 0.06 / 0.14 |
| Correlation | Pearson r | 0.1 / 0.3 / 0.5 |
| Chi-square (2×2) | φ (= sqrt(χ²/n)) | 0.1 / 0.3 / 0.5 |
| Chi-square (R×C) | Cramér's V | 0.1 / 0.3 / 0.5 |
| Logistic / two proportions | Odds ratio, risk difference | Context-dependent |
| Linear regression | R², standardized β | Context-dependent |

Always report the effect size's 95% CI alongside the point estimate.

## Step 4 — Honest interpretation

Before writing the result paragraph, complete these sentences:

1. The test answers the question: ___ (restate in plain English)
2. The result was: ___ (statistic, p, effect, CI)
3. At α = 0.05, this is statistically ___ (significant / not significant)
4. Practically, the magnitude is ___ (cite the effect size; compare to any threshold the user named)
5. The design supports ___ language only (causal if RCT, associational otherwise)
6. Limitations: ___ (sample size, multiple testing, assumption violations, etc.)

If any of these is "I don't know" — go back and find out before reporting.
