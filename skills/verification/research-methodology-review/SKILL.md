---
name: research-methodology-review
category: verification
description: >
  Appraise the METHODOLOGY behind a study, survey or research claim before you trust or cite it — match it to the
  right reporting guideline (CONSORT for trials, PRISMA for reviews, STROBE for observational, AAPOR for surveys),
  assess risk of bias, and flag confounding, underpowering, non-representative sampling and overreach. Use this
  whenever someone says "is this study any good", "can we trust this research", "appraise this paper", "critique
  the methodology", "is this survey representative", or is about to build a case on external research. Reach for it
  before a finding becomes a slide.
when_to_use:
  - Deciding whether a study/survey is robust enough to cite or act on
  - Critiquing sampling, design, controls, or generalisability of a piece of research
  - Screening a paper for risk of bias against the right checklist
  - Judging whether a headline finding is supported by its own method
when_not_to_use:
  - Recomputing/consistency-checking the numbers themselves → use stat-check-review
  - Verifying that cited sources exist and say what's claimed → use citation-integrity-check
  - Grading source outlet reliability/bias (not study design) → use source-credibility-audit
  - Designing your own study/analysis → use statistical-testing
keywords: [methodology, research quality, risk of bias, consort, prisma, strobe, aapor, sampling, confounding, generalisability, external validity, study design, appraisal, representative, underpowered, peer review]
similar_to: [stat-check-review, source-credibility-audit, citation-integrity-check, claim-verifier]
inputs_needed:
  - The study/paper/survey (or its abstract + methods section)
  - Study type (RCT, observational, systematic review, survey, qualitative)
  - What decision or claim rests on it (so overreach vs the evidence is visible)
produces: A methodology appraisal — study type, matched checklist, risk-of-bias rating per domain, and a trust verdict
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Research methodology review

Judge whether a piece of research is actually strong enough to build on — the design, not just the numbers. Match
it to the discipline's own reporting standard and rate the risk of bias.

## When to use

Before you cite, headline, or make a decision on external research. Pairs with `stat-check-review` (the numbers)
and `source-credibility-audit` (the outlet).

## Step 1 — classify the study, pick the checklist

| Study type | Reporting guideline | Risk-of-bias tool |
|---|---|---|
| Randomised controlled trial | **CONSORT** | Cochrane **RoB 2** |
| Cohort / case-control / cross-sectional | **STROBE** | **ROBINS-I** |
| Systematic review / meta-analysis | **PRISMA** | **AMSTAR-2** |
| Survey / polling | **AAPOR** disclosure standards | representativeness + weighting |
| Qualitative | **COREQ / SRQR** | reflexivity + saturation |
| Diagnostic accuracy | **STARD** | **QUADAS-2** |

Guidelines are indexed at the EQUATOR Network — match, don't guess.

## Step 2 — risk of bias by domain

Score each **low / some concerns / high**, with a one-line reason:

- **Selection / sampling** — how were subjects chosen? Representative of the target population, or convenience/self-selected? For surveys: sample frame, response rate, weighting to known quotas (census/TGI/GWI).
- **Measurement** — validated instrument? Blinded? Self-report bias? Leading questions?
- **Confounding** — what else could explain the result? Were the obvious confounders measured and adjusted for?
- **Attrition / missing data** — dropout rate and how missingness was handled (ignoring it inflates effects).
- **Reporting** — pre-registered? Outcome-switching? Only significant results shown?
- **Analysis fit** — right test for the design and data (defer the recompute to `stat-check-review`).

## Step 3 — the questions that catch most weak research

- **Power / n:** is the sample big enough to detect the claimed effect, or is it underpowered (noise)?
- **Correlation ≠ causation:** does an observational design support the causal language used?
- **Generalisability:** does the sample's population match the one the claim is applied to? (A US Gen-Z panel ≠ UK adults.)
- **Effect size vs significance:** is the effect *meaningful*, or just statistically significant on a huge n?
- **Cui bono:** who funded/ran it, and does the design favour the desired answer? (Then use `source-credibility-audit`.)
- **Single study:** is this replicated, or one unreplicated finding being treated as settled?

## Step 4 — verdict

Summarise: study type, matched checklist, per-domain risk, and a **trust verdict** — *robust / usable with caveats /
directional only / do not rely on* — plus the single biggest weakness and how much the headline overreaches its method.

## Verify

- Given a convenience-sample survey claiming to represent a national population → flags selection bias + generalisability.
- Given an observational study with causal wording → flags correlation≠causation.
- Given an underpowered RCT → flags power/n and false-null risk.

## Pitfalls

- **Don't over-penalise** good research for not being an RCT — the right standard depends on the question; some things can't be randomised.
- **Absence of detail ≠ absence of rigour**, but unreported methods must be treated as unknown risk, not assumed fine.
- Keep this separate from recomputing numbers (`stat-check-review`) and from grading the publisher (`source-credibility-audit`) — three different lenses.
