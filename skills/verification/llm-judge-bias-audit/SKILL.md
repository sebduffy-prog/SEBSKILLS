---
name: llm-judge-bias-audit
category: verification
description: >
  Audit and debias an LLM-as-judge before you trust its scores. Measures the three
  headline biases — position (favours whichever answer is shown first), verbosity/length
  (favours longer answers), and self-preference (over-rates its own model family) — and
  grades judge-vs-human agreement with Cohen's kappa. Ports AlpacaEval's length-controlled
  (LC) win rate so you can quote a length-neutral number. Use when a judge ranking looks
  suspicious, before shipping an eval leaderboard, or when validating a judge model. A
  cross-vendor judge panel gives scores; this tells you if those scores are honest.
when_to_use:
  - You are using an LLM to grade or rank other LLM outputs (pairwise or scored) and need to know if the ranking is trustworthy
  - A judged win rate jumped and you suspect the winner just wrote longer / bulleted answers
  - You must justify a judge model choice or a leaderboard to a client and need a bias + human-agreement number
  - You have a slice of human/gold preference labels and want to calibrate the judge against them (kappa)
  - You want a length-controlled win rate (AlpacaEval LC) instead of a gameable raw win rate
when_not_to_use:
  - You just want the judgments themselves from several vendors — run the cross-vendor judge panel first, then audit here
  - You are checking factual truth of one answer, not judge fairness — use claim-verifier
  - You are screening one model's output for hallucination with no judge involved — use self-consistency-check
  - You need a full retrieval/answer eval harness with faithfulness metrics — use llm-rag-eval-harness (rag)
  - The concern is a single statistic's math, not judging — use stat-check-review
keywords: [llm-as-judge, judge bias, position bias, verbosity bias, length bias, self-preference, self-enhancement, length-controlled, lc win rate, alpacaeval, cohen kappa, human agreement, pairwise, eval, calibration, leaderboard, debias]
similar_to: [self-consistency-check, claim-verifier, stat-check-review, research-methodology-review, adversarial-argument-review]
inputs_needed: >
  A set of the judge's pairwise decisions as JSONL (one comparison per line) with, per record,
  judge_winner (candidate|baseline) and the two output lengths. Optional fields unlock more metrics:
  candidate_first (position bias), human_winner (agreement/kappa), same_family (self-preference).
  No API keys. Human/gold labels are optional but needed for self-preference and kappa.
produces: >
  A five-block report: raw win rate, length-controlled (LC) win rate + verbosity coefficient,
  position-bias P(first wins) + order-consistency, self-preference gap (own vs other family vs humans),
  and human agreement + Cohen's kappa. Plus verdicts flagging which biases are material.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# LLM-Judge Bias Audit

An LLM-as-judge is cheap and fast, but it is not neutral. The literature is consistent
(Zheng et al. *MT-Bench/Chatbot Arena* 2023; Dubois et al. *Length-Controlled AlpacaEval*
2024): judges systematically prefer the answer shown **first** (position bias), the **longer**
answer (verbosity bias), and answers from **their own model family** (self-preference /
self-enhancement). If you rank models with a raw judge win rate, you may be ranking prompt
length and answer order, not quality. This skill quantifies each bias against a slice of human
labels and gives you a length-controlled number you can defend.

## When to use

Reach for this the moment a judge produces a ranking that matters — a client leaderboard, a
"which model should we buy" decision, a model-routing gate. Also use it whenever a win rate
moves and you suspect gaming (someone told a model to "answer in maximum detail" and it jumped
from 50% to 64% — that is the documented verbosity exploit, not a better model). It is the
audit layer that sits *after* you have collected judgments (e.g. from a cross-vendor judge panel).

## Prerequisites

- **Python 3.9+, numpy, scipy** — all preinstalled here (`python3 -c "import numpy, scipy"`).
  The helper implements the logistic fit itself, so no statsmodels/sklearn needed.
- **The judge's decisions**, exported as JSONL. Each line is one candidate-vs-baseline comparison.
- **Optional but high-value:** a slice of **human/gold preferences** (even 50-100 pairs) — without
  them you can still measure position and verbosity bias, but not self-preference or agreement.
- For position bias you ideally judged **each pair in both orders** (A/B and B/A). If you only have
  one order, the script still estimates P(first wins) from the `candidate_first` flag.

## Input schema

One JSON object per line. Required: `judge_winner`, `len_candidate`, `len_baseline`.

```json
{"id": 42, "judge_winner": "candidate", "len_candidate": 340, "len_baseline": 120,
 "candidate_first": true, "human_winner": "baseline", "same_family": false}
```

| field | required | meaning |
|-------|----------|---------|
| `judge_winner` | yes | content-level winner the judge picked: `candidate` or `baseline` |
| `len_candidate` / `len_baseline` | yes | length of each output (chars or tokens — be consistent) |
| `id` | no | pair id; if the same id appears in both orders you get an order-consistency score |
| `candidate_first` | no | was the candidate shown first — unlocks position bias |
| `human_winner` | no | gold label — unlocks agreement, kappa, self-preference |
| `same_family` | no | is the candidate from the judge's own model family — unlocks self-preference |

Lengths are the mediator variable AlpacaEval controls for. Measure the *rendered answer* length,
not the prompt. Use one unit (characters is fine) across every row.

## Recipe — run the audit

```bash
python3 scripts/judge_bias_audit.py judgments.jsonl
```

Output blocks and how to read them:

1. **Raw candidate win rate** — the naive, gameable number.
2. **Length / verbosity bias** — the **length-controlled (LC) win rate** is the raw win rate
   re-predicted at *zero* length difference (verbosity removed), exactly AlpacaEval's construction:
   fit `P(candidate wins) ~ intercept + β·Δlen`, then read the intercept. A large `raw − LC gap`
   means length was inflating the score. `β > 0` = judge rewards longer answers.
3. **Position bias** — `P(first-shown output wins)`; 0.50 is unbiased. If you judged both orders,
   `order-consistency` is the fraction of pairs where the judge picked the same *content* winner
   regardless of order — low consistency is the smoking gun.
4. **Self-preference** — compares how much the judge over-scores candidates **relative to humans**
   for its own family vs other families. A positive **self-preference gap** means the judge inflates
   its own family beyond what humans do.
5. **Human agreement** — raw agreement and **Cohen's kappa** (chance-corrected). Below ~0.4 the
   judge barely beats coin-flipping and should not drive a leaderboard alone.

## Debiasing — what to do with the findings

- **Verbosity:** report the **LC win rate**, not raw. AlpacaEval's LC cut length-gameability from
  ~21% to ~6% (a 3× reduction). Also cap or normalise answer length in the judge prompt.
- **Position:** *always* judge every pair in **both orders and average** (or randomise order per
  pair). This is the single most effective, zero-cost fix — do it by default.
- **Self-preference:** use a **judge from a different vendor/family** than any model being ranked,
  or a panel of judges from multiple families and take the majority. Never let a model be sole judge
  of its own family in a competitive eval.
- **Low kappa:** tighten the rubric, add few-shot judge examples, or fall back to human review for
  the contested slice. A judge that disagrees with humans is measuring the wrong thing.

## Verify

- **Null control:** feed the script judgments where `judge_winner` is randomised — every bias should
  read ~50% / β≈0 / kappa≈0. If a bias fires on noise, your input mapping is wrong.
- **Planted bias:** hand-write ~5 synthetic JSONL rows (`judge_winner`, `len_candidate`,
  `len_baseline`, plus `id` + `candidate_first` on swapped pairs) and run
  `python3 scripts/judge_bias_audit.py sample.jsonl` — the order-consistency line should match what
  you planted: 100% when swapped pairs agree, dropping toward 50% as you flip winners by order.
- **Both-orders sanity:** if you have swapped pairs, order-consistency should be high (>90%) for a
  good judge; if it is near 50% the judge is essentially flipping a coin on presentation order.

## Pitfalls

- **LC ≈ raw is not a bug.** If the two systems have similar length distributions, LC and raw match —
  LC only diverges when one system is systematically longer. The gap is the point; a small gap means
  length was not the story here.
- **Length must be the answer, not the prompt.** Measuring prompt length or including system scaffolding
  pollutes the mediator and the LC number becomes meaningless.
- **Position bias needs order metadata.** Without `candidate_first` the script silently skips block 3 —
  it cannot infer order after the fact. Log presentation order at judging time.
- **Self-preference needs honest `same_family` tags.** Fine-tunes, distillations, and API aliases blur
  "family"; mislabel them and the gap is noise. When unsure, treat shared base model as same family.
- **Kappa punishes class imbalance.** If humans pick candidate 95% of the time, high agreement can still
  give low kappa — read agreement and kappa together, not kappa alone.
- **This audits the judge, not the models.** A clean bias profile means the *ranking method* is fair; it
  does not tell you the winning model is good. Pair with a real task eval.
- **Consistency ≠ correctness.** A judge can be unbiased and consistently agree with humans who are
  themselves wrong. For factual grading, escalate to claim-verifier.
