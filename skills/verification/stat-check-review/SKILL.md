---
name: stat-check-review
category: verification
description: >
  Recompute and stress-test the statistics in a report, deck or paper so a wrong number never ships — statcheck-style
  t/F/χ²/df/p consistency checks, GRIM and GRIMMER mean/SD plausibility, denominator and base-rate sanity, and
  p-hacking / selective-reporting screens. Use this whenever someone says "sense-check these stats", "does this
  percentage add up", "verify the numbers in this deck", "is this significant", "check the survey figures", or is
  about to present data-driven claims. Pushy on purpose: reach for it before any stat goes in front of a client.
when_to_use:
  - About to present percentages, significance claims, or survey figures and want them verified
  - Checking whether a reported p-value is consistent with its test statistic and df
  - Sanity-checking a mean/percentage against its sample size (is it even attainable?)
  - Auditing a deck/paper for denominator errors, base-rate slips, or cherry-picked results
when_not_to_use:
  - Verifying factual claims/quotes, not numbers → use claim-verifier
  - Checking that cited sources exist and support the point → use citation-integrity-check
  - Appraising study DESIGN/methodology quality → use research-methodology-review
  - Running the actual statistical analysis on raw data → use statistical-testing
keywords: [statcheck, grim, grimmer, p-value, significance, denominator, base rate, p-hacking, garden of forking paths, survey stats, sanity check, recompute, statistics review, effect size, confidence interval]
similar_to: [claim-verifier, citation-integrity-check, research-methodology-review, data-quality-validation, statistical-testing]
inputs_needed:
  - The statistics to check (test stat, df, p, or reported means/SDs/percentages + n)
  - The sample size / denominator behind each figure
  - What the number is claimed to show (so base-rate and denominator errors surface)
produces: A per-statistic verdict — consistent / inconsistent / implausible — with the recomputed value and the fix
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Stat-check review

Catch the wrong number before it's on a slide. This recomputes reported statistics and screens for the classic
failure modes — inconsistent p-values, impossible means, and denominator/base-rate slips.

## When to use

Any time data-driven claims are about to be presented. It complements `claim-verifier` (facts) and
`citation-integrity-check` (sources) — this one is purely the *numbers*.

## Prerequisites

Pure-Python + SciPy for the p-value recompute; everything else is arithmetic (no install needed for GRIM).
```bash
python3 -m pip install --user scipy    # only for the p-value consistency check
```

## 1. statcheck — is the p-value consistent with its test statistic?

Reported like `t(48) = 2.10, p < .01`? Recompute p from the stat + df and compare.

```python
from scipy import stats
def check_t(t, df, reported_p):
    p = 2 * stats.t.sf(abs(t), df)          # two-tailed
    return {"recomputed_p": round(p, 4), "reported_p": reported_p,
            "consistent": abs(p - reported_p) < 0.01 or
                          (reported_p in ('<.05','<.01') and p < float(reported_p[1:]))}
# check_t(2.10, 48, 0.01) -> recomputed_p 0.0409  => "p < .01" is WRONG (it's ~.04)
```
Do the same for F (`stats.f.sf`), χ² (`stats.chi2.sf`), r and z. An inconsistency means a typo — or a rounded-down
p that overstates significance.

## 2. GRIM — is the reported mean even possible?

For a mean of integer responses (Likert, counts) with sample size `n`, the mean must be a multiple of `1/n`.

```python
def grim(mean, n, decimals=2):
    # is `mean` achievable as (integer sum)/n at this rounding?
    lo, hi = round((mean - 0.5/10**decimals)*n), round((mean + 0.5/10**decimals)*n)
    return any(round(s/n, decimals) == round(mean, decimals) for s in range(lo, hi+1))
# grim(3.33, 10) -> False  => 3.33 is impossible with n=10 (only x.0..x.9 attainable)
```
GRIMMER extends this to SDs. A GRIM failure means the mean, the n, or the rounding is misreported.

## 3. Denominator & base-rate sanity (the one that bites in decks)

- **Which denominator?** "58% said X" — of *everyone*, or of the *subset who reached that question*? A % of a
  filtered base presented as a % of all respondents is the classic survey error. State the base explicitly.
- **Base rates:** a "90% accurate" test on a 1%-prevalence condition is mostly false positives — recompute with
  Bayes before repeating a headline.
- **Do parts sum?** Segments should sum to 100% (± rounding); if they exceed it, it's multi-select — label it.
- **n behind each cut:** flag any figure whose base is < ~50 as directional, not a number to headline.

## 4. p-hacking / selective-reporting screens

- Many tests, only significant ones shown → ask for the full set (garden of forking paths).
- p just under .05 clustering → suspicious; look for optional stopping / outlier removal.
- "Trending toward significance" on a null result → report it as null.

## Verify

- Feed a known-inconsistent stat (e.g. `t(48)=2.10, p<.01`) → flagged inconsistent with recomputed ~.04.
- Feed `mean=3.33, n=10` → GRIM flags impossible.
- Feed a subset percentage labelled as a total → denominator check flags it.

## Pitfalls

- **One-tailed vs two-tailed** — confirm which before calling a p-value wrong.
- **GRIM only applies to integer-item means** — not to already-continuous measures.
- **Rounding cascades** — a figure can be "off" only because an upstream number was rounded; trace it.
- This checks *internal consistency and plausibility*, not whether the underlying study was well-designed → pair with `research-methodology-review`.
